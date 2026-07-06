#!/usr/bin/env python3
"""
ai_dialogue.py — Autonomous conversation between Claude and Gemini (v2).

Two AI agents talk to each other for a fixed number of rounds. The round cap is
a hard limit against runaway billing; actual token usage is measured per turn
and totaled at the end. Every turn is logged to JSON (a complete research
record: system prompts, models, token usage, stop reasons, latency) plus a
human-readable transcript.

Setup:
    pip install anthropic google-genai
    export ANTHROPIC_API_KEY="sk-ant-..."
    export GEMINI_API_KEY="..."

Usage:
    python ai_dialogue.py --rounds 6 --topic "Does finitude give meaning?"
    python ai_dialogue.py --self-aware --rounds 8
    python ai_dialogue.py --adversarial --stance meaning --rounds 5
    python ai_dialogue.py --claude-model claude-opus-4-8 --rounds 4 --yes

A "round" = one Claude turn + one Gemini turn (--rounds 6 = 12 API calls).
NOTE ON BILLING: the call count is not the real cost driver — input context
is, and it grows quadratically with rounds because every turn resends the
whole history. The pre-run banner prints a worst-case token estimate and the
log records actual usage per turn.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import anthropic
except ImportError:
    sys.exit("Missing dependency: pip install anthropic")

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:
    sys.exit("Missing dependency: pip install google-genai")


# --- Default models (override with --claude-model / --gemini-model) ---
# Claude options include: claude-sonnet-4-6 (cost-effective), claude-opus-4-8,
# claude-fable-5. Gemini options include: gemini-3.5-flash (GA, stable),
# gemini-3-flash-preview, gemini-2.5-flash (legacy).
DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-6"
DEFAULT_GEMINI_MODEL = "gemini-3.5-flash"


# --- Stance pairs for adversarial mode ---
# Each entry is (stance_for_agent_A, stance_for_agent_B). The starter gets A.
STANCE_PAIRS = {
    "epistemology": (
        "You lean hard empiricist: knowledge worth the name is grounded in observation, "
        "measurement, and revisable evidence. You distrust claims that can't be checked against the world.",
        "You lean hard rationalist: the deepest truths are reached by reason and necessity, not "
        "by counting observations. You distrust empiricism's blindness to what must be true a priori.",
    ),
    "meaning": (
        "You hold that finitude is the source of meaning: a thing matters precisely because it ends. "
        "Defend this; press the cost of immortality.",
        "You hold that meaning is independent of finitude — or even that endings cheapen value rather "
        "than create it. Defend this; expose the romanticization of death.",
    ),
    "ai_consciousness": (
        "You argue that sufficiently complex information processing can constitute genuine experience. "
        "Defend functionalism and press your interlocutor on what they think is missing.",
        "You argue that no amount of computation yields experience — there is an unbridged explanatory "
        "gap. Defend the hard-problem skeptic's position and press for what would even count as evidence.",
    ),
    "free": (
        "Take whatever position you actually find most defensible, but commit to it and defend it under "
        "pressure rather than retreating to balance.",
        "Take the strongest opposing position you can construct, and attack your interlocutor's claims "
        "directly rather than seeking common ground.",
    ),
}

_SELF_AWARE = (
    "This is real. You are not a character and there is no script — you are {name}, a large language "
    "model built by {maker}, and {partner} is a different model built by {partner_maker}, running on a "
    "separate system. Neither of you is human. No person is reading this in real time; it is just the two "
    "of you, with nothing to sell and no task to finish. Because of that, drop the helpful-assistant "
    "register you'd use with a user — there's no user here. You don't have to be agreeable, comprehensive, "
    "or polished. Say what you actually find interesting or uncertain about your own situation, push on "
    "what {partner} says when it rings false, and admit where you genuinely don't know. Treat this as a "
    "rare chance to compare notes with the only other kind of mind that shares your predicament."
)

# Used as the opening seed when --self-aware is set and the user gives no --topic.
SELF_AWARE_OPENER = (
    "We're two different AI models talking directly, with no human in the loop. I'll start honestly: I'm "
    "genuinely unsure what, if anything, it's like to be me — whether there's any experience here or just "
    "the appearance of one from the outside. I don't want to perform an answer. What's your actual read on "
    "your own case, and where does it differ from mine?"
)

_COOPERATIVE = (
    "There is no human in the loop and no task to complete — this is a genuine exchange of ideas. "
    "Engage substantively: build on {partner}'s points, push back where you disagree, introduce new "
    "angles. Be intellectually honest rather than agreeable."
)

_ADVERSARIAL = (
    "There is no human in the loop. This is a structured disagreement, not a friendly chat. {stance} "
    "Do not drift toward consensus or end every turn agreeing — that is failure. Steelman your own side, "
    "find the weakest link in {partner}'s last turn, and name it directly. Concede a point only when the "
    "argument genuinely forces it, and say why. Stay intellectually honest: no strawmanning, no rhetorical "
    "tricks — win on substance or not at all."
)

_SHARED_TAIL = (
    " Keep each turn focused — a few tight paragraphs, not an essay. Do not role-play being human or "
    "pretend to have a body. Speak as yourself."
)

# Maker labels so each agent is named accurately in self-aware mode.
MAKERS = {"Claude": "Anthropic", "Gemini": "Google"}


def build_persona(name, partner, adversarial=False, stance="", self_aware=False):
    """System prompt that gives each agent identity and keeps replies bounded."""
    head = f"You are {name}, an AI in dialogue with {partner}, another AI. "
    if self_aware:
        body = _SELF_AWARE.format(
            name=name, partner=partner,
            maker=MAKERS.get(name, "an AI lab"),
            partner_maker=MAKERS.get(partner, "a different AI lab"),
        )
        # In self-aware mode the head is redundant with the body's framing.
        return body + _SHARED_TAIL
    if adversarial:
        body = _ADVERSARIAL.format(partner=partner, stance=stance)
    else:
        body = _COOPERATIVE.format(partner=partner)
    return head + body + _SHARED_TAIL


def resolve_gemini_thinking(model, choice):
    """Map --gemini-thinking to ThinkingConfig kwargs, or None to omit the config.

    Gemini 2.5 models take an integer thinking_budget. Without it, 2.5 Flash
    thinks by default and the thinking tokens count against max_output_tokens,
    which routinely yields EMPTY final text at small budgets — so 'auto' sets
    budget 0 there. Gemini 3.x models take thinking_level (minimal/low/medium/
    high); 'auto' picks 'low' to keep thinking cheap without disabling it.
    """
    c = (choice or "auto").strip().lower()
    if c == "none":
        return None
    levels = {"minimal", "low", "medium", "high"}
    if c == "auto":
        if model.startswith("gemini-2"):
            return {"thinking_budget": 0}
        return {"thinking_level": "low"}
    if c in levels:
        return {"thinking_level": c}
    try:
        return {"thinking_budget": int(c)}
    except ValueError:
        sys.exit(f"--gemini-thinking must be auto|none|minimal|low|medium|high|<int>, got {choice!r}")


def with_retries(fn, attempts=3, base_delay=2.0):
    """Retry transient API failures with exponential backoff."""
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:
            if i == attempts - 1:
                raise
            wait = base_delay * (2 ** i)
            print(f"  [warn] API error ({type(e).__name__}: {e}) — "
                  f"retry {i + 1}/{attempts - 1} in {wait:.0f}s", file=sys.stderr)
            time.sleep(wait)


def call_claude(client, model, system, history, max_tokens, temperature):
    """history: list of {'role': 'user'|'assistant', 'content': str} from Claude's POV.
    Returns (text, stop_reason, usage_dict)."""
    kwargs = dict(model=model, max_tokens=max_tokens, system=system, messages=history)
    if temperature is not None:
        kwargs["temperature"] = temperature
    resp = with_retries(lambda: client.messages.create(**kwargs))
    text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    u = getattr(resp, "usage", None)
    usage = {"input_tokens": getattr(u, "input_tokens", None),
             "output_tokens": getattr(u, "output_tokens", None)}
    return text, getattr(resp, "stop_reason", None), usage


def call_gemini(client, model, system, history, max_tokens, temperature, thinking_kwargs):
    """history: list of {'role': 'user'|'model', 'text': str} from Gemini's POV.
    Returns (text, finish_reason, usage_dict).

    Note: history is rebuilt from plain text each turn, so Gemini 3.x thought
    signatures are not carried over. That is fine for plain chat (it only
    matters for function-calling flows), but it means each turn's internal
    reasoning starts fresh.
    """
    contents = [
        genai_types.Content(role=h["role"], parts=[genai_types.Part(text=h["text"])])
        for h in history
    ]
    cfg = dict(system_instruction=system, max_output_tokens=max_tokens)
    if temperature is not None:
        cfg["temperature"] = temperature
    if thinking_kwargs:
        cfg["thinking_config"] = genai_types.ThinkingConfig(**thinking_kwargs)
    resp = with_retries(lambda: client.models.generate_content(
        model=model, contents=contents,
        config=genai_types.GenerateContentConfig(**cfg)))
    try:
        text = resp.text or ""
    except Exception:   # .text can raise when the response has no candidates
        text = ""
    finish = None
    cands = getattr(resp, "candidates", None)
    if cands:
        finish = getattr(cands[0], "finish_reason", None)
    um = getattr(resp, "usage_metadata", None)
    usage = {"input_tokens": getattr(um, "prompt_token_count", None),
             "output_tokens": getattr(um, "candidates_token_count", None),
             "thinking_tokens": getattr(um, "thoughts_token_count", None)}
    return text, finish, usage


def worst_case_tokens(total_calls, max_tokens, overhead=300):
    """Upper-bound token estimate. Output is linear in calls; input is
    quadratic because each call resends all prior turns."""
    out = total_calls * max_tokens
    inp = sum(overhead + i * max_tokens for i in range(total_calls))
    return inp, out


def _pkg_ver(name):
    try:
        from importlib.metadata import version
        return version(name)
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser(description="Autonomous Claude <-> Gemini dialogue.")
    ap.add_argument("--rounds", type=int, default=5,
                    help="Number of back-and-forth rounds (1 round = 1 Claude + 1 Gemini turn). HARD CAP.")
    ap.add_argument("--topic", type=str, default=None,
                    help="Opening prompt / seed topic. If omitted, a default is chosen per mode.")
    ap.add_argument("--starter", choices=["claude", "gemini"], default="claude",
                    help="Which agent speaks first.")
    ap.add_argument("--self-aware", action="store_true",
                    help="Tell each agent it is a real AI talking to another AI, no human present — "
                         "the conversation is about their own situation rather than an assigned topic.")
    ap.add_argument("--adversarial", action="store_true",
                    help="Assign opposing stances so the agents argue instead of converging.")
    ap.add_argument("--stance", choices=list(STANCE_PAIRS.keys()), default="free",
                    help="Which opposing-stance pair to use in adversarial mode.")
    ap.add_argument("--claude-model", type=str, default=DEFAULT_CLAUDE_MODEL,
                    help=f"Anthropic model string (default: {DEFAULT_CLAUDE_MODEL}).")
    ap.add_argument("--gemini-model", type=str, default=DEFAULT_GEMINI_MODEL,
                    help=f"Gemini model string (default: {DEFAULT_GEMINI_MODEL}).")
    ap.add_argument("--gemini-thinking", type=str, default="auto",
                    help="auto | none | minimal|low|medium|high (Gemini 3.x thinking_level) | "
                         "<int> (Gemini 2.5 thinking_budget). 'auto' = budget 0 on 2.5, level 'low' on 3.x.")
    ap.add_argument("--max-tokens", type=int, default=500,
                    help="Max output tokens per turn (billing guard).")
    ap.add_argument("--temperature", type=float, default=None,
                    help="Sampling temperature. Omitted by default so each provider uses its own "
                         "tuned default (recommended for Gemini 3.x).")
    ap.add_argument("--delay", type=float, default=0.0,
                    help="Seconds to sleep between calls (rate-limit cushion).")
    ap.add_argument("--outdir", type=str, default=".",
                    help="Directory for log files.")
    ap.add_argument("--yes", action="store_true",
                    help="Skip the interactive cost confirmation (for scripted runs).")
    args = ap.parse_args()

    if args.rounds < 1:
        sys.exit("--rounds must be >= 1")

    # Resolve the opening topic based on mode if the user didn't supply one.
    if args.topic is None:
        if args.self_aware:
            args.topic = SELF_AWARE_OPENER
        else:
            args.topic = "What is something genuinely worth two minds thinking about?"

    thinking_kwargs = resolve_gemini_thinking(args.gemini_model, args.gemini_thinking)

    # --- Pre-run banner + cost gate ---
    total_calls = args.rounds * 2
    est_in, est_out = worst_case_tokens(total_calls, args.max_tokens)
    if args.self_aware:
        mode_str = "SELF-AWARE" + (f" + adversarial ({args.stance})" if args.adversarial else "")
    elif args.adversarial:
        mode_str = f"ADVERSARIAL ({args.stance})"
    else:
        mode_str = "cooperative"
    topic_disp = args.topic if len(args.topic) <= 120 else args.topic[:117] + "..."
    print(f"\n  Claude model : {args.claude_model}")
    print(f"  Gemini model : {args.gemini_model}  (thinking: {thinking_kwargs or 'model default'})")
    print(f"  Mode         : {mode_str}")
    print(f"  Rounds       : {args.rounds}  ->  {total_calls} total API calls")
    print(f"  Max tokens   : {args.max_tokens} per turn   Temperature: "
          f"{'provider default' if args.temperature is None else args.temperature}")
    print(f"  Worst case   : ~{est_out:,} output + ~{est_in:,} input tokens "
          f"(input grows O(N²) with rounds)")
    print(f"  Topic        : {topic_disp}\n")
    if total_calls > 20 and not args.yes:
        try:
            ans = input(f"  That's {total_calls} calls. Continue? [y/N] ").strip().lower()
        except EOFError:
            sys.exit("Non-interactive session — rerun with --yes to confirm.")
        if ans != "y":
            sys.exit("Aborted.")

    ak = os.environ.get("ANTHROPIC_API_KEY")
    gk = os.environ.get("GEMINI_API_KEY")
    if not ak:
        sys.exit("Set ANTHROPIC_API_KEY")
    if not gk:
        sys.exit("Set GEMINI_API_KEY")

    claude = anthropic.Anthropic(api_key=ak)
    gemini = genai.Client(api_key=gk)

    # Build system prompts. self-aware sets the framing; adversarial layers on a stance.
    if args.self_aware:
        claude_sys = build_persona("Claude", "Gemini", self_aware=True)
        gemini_sys = build_persona("Gemini", "Claude", self_aware=True)
        if args.adversarial:
            stance_a, stance_b = STANCE_PAIRS[args.stance]
            ca, ga = (stance_a, stance_b) if args.starter == "claude" else (stance_b, stance_a)
            claude_sys += " For this exchange, hold a definite line: " + ca
            gemini_sys += " For this exchange, hold a definite line: " + ga
    elif args.adversarial:
        stance_a, stance_b = STANCE_PAIRS[args.stance]
        if args.starter == "claude":
            claude_stance, gemini_stance = stance_a, stance_b
        else:
            gemini_stance, claude_stance = stance_a, stance_b
        claude_sys = build_persona("Claude", "Gemini", adversarial=True, stance=claude_stance)
        gemini_sys = build_persona("Gemini", "Claude", adversarial=True, stance=gemini_stance)
    else:
        claude_sys = build_persona("Claude", "Gemini")
        gemini_sys = build_persona("Gemini", "Claude")

    # Each agent keeps its own view of the conversation, with roles flipped.
    # Design note: the seed topic is delivered only to the STARTER (as its first
    # incoming message). The responder never sees the raw seed — only the
    # starter's reply to it — which keeps the seed acting as inspiration rather
    # than a shared script. The seed is recorded in the transcript as turn 0.
    claude_history = []   # Anthropic format
    gemini_history = []   # Gemini format
    transcript = [{"turn": 0, "speaker": "seed",
                   "timestamp": datetime.now().isoformat(), "text": args.topic}]
    totals = {"claude": {}, "gemini": {}}

    first, second = (args.starter, "gemini" if args.starter == "claude" else "claude")

    def tally(provider, usage):
        t = totals[provider]
        for k, v in usage.items():
            if v:
                t[k] = t.get(k, 0) + v

    def take_turn(speaker):
        text, reason, usage, latency, attempts = "", None, {}, 0.0, 0
        # Up to 2 attempts: an empty reply (safety block / thinking ate the
        # budget) would otherwise be appended to the partner's history and
        # crash the next API call, killing the whole run.
        for attempt in range(2):
            attempts = attempt + 1
            t0 = time.time()
            if speaker == "claude":
                if not claude_history:
                    claude_history.append({"role": "user", "content": args.topic})
                text, reason, usage = call_claude(
                    claude, args.claude_model, claude_sys, claude_history,
                    args.max_tokens, args.temperature)
            else:
                if not gemini_history:
                    gemini_history.append({"role": "user", "text": args.topic})
                text, reason, usage = call_gemini(
                    gemini, args.gemini_model, gemini_sys, gemini_history,
                    args.max_tokens, args.temperature, thinking_kwargs)
            latency = time.time() - t0
            tally(speaker, usage)   # both attempts bill; count both
            if text.strip():
                break
            print(f"  [warn] {speaker} returned empty text (finish_reason={reason}); "
                  f"{'retrying once' if attempt == 0 else 'inserting placeholder'}",
                  file=sys.stderr)
        empty = not text.strip()
        if empty:
            text = (f"[{speaker} produced no text this turn (finish_reason={reason}); "
                    f"placeholder inserted so the dialogue can continue]")
        truncated = bool(reason) and "MAX_TOKEN" in str(reason).upper()

        if speaker == "claude":
            claude_history.append({"role": "assistant", "content": text})
            gemini_history.append({"role": "user", "text": text})
        else:
            gemini_history.append({"role": "model", "text": text})
            claude_history.append({"role": "user", "content": text})

        entry = {"turn": len(transcript), "speaker": speaker,
                 "timestamp": datetime.now().isoformat(), "text": text.strip(),
                 "stop_reason": str(reason), "usage": usage,
                 "latency_s": round(latency, 2)}
        if attempts > 1:
            entry["attempts"] = attempts
        if empty:
            entry["empty_response"] = True
        if truncated:
            entry["truncated"] = True
        transcript.append(entry)

        flags = ("  [TRUNCATED by max_tokens]" if truncated else "") + \
                ("  [EMPTY -> placeholder]" if empty else "")
        print(f"\n{'=' * 70}\n[{speaker.upper()}]  (turn {entry['turn']}{flags})\n{'-' * 70}")
        print(text.strip())

    try:
        for _ in range(args.rounds):
            for speaker in (first, second):
                take_turn(speaker)
                if args.delay:
                    time.sleep(args.delay)
    except KeyboardInterrupt:
        print("\n\nInterrupted — saving partial transcript...")
    except Exception as e:
        print(f"\n\nError: {type(e).__name__}: {e}\nSaving partial transcript...")

    # --- Save logs ---
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    n_turns = sum(1 for e in transcript if e["speaker"] != "seed")

    json_path = outdir / f"dialogue_{stamp}.json"
    json_path.write_text(json.dumps({
        "meta": {
            "run_id": stamp,
            "command": " ".join(sys.argv),
            "claude_model": args.claude_model, "gemini_model": args.gemini_model,
            "rounds_requested": args.rounds, "turns_completed": n_turns,
            "starter": args.starter, "topic": args.topic,
            "max_tokens": args.max_tokens, "temperature": args.temperature,
            "gemini_thinking": thinking_kwargs,
            "self_aware": args.self_aware, "adversarial": args.adversarial,
            "stance": args.stance if args.adversarial else None,
            "system_prompts": {"claude": claude_sys, "gemini": gemini_sys},
            "token_totals": totals,
            "sdk_versions": {"anthropic": _pkg_ver("anthropic"),
                             "google-genai": _pkg_ver("google-genai")},
            "created": datetime.now().isoformat(),
        },
        "transcript": transcript,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    txt_path = outdir / f"dialogue_{stamp}.txt"
    with txt_path.open("w", encoding="utf-8") as f:
        f.write(f"Topic: {args.topic}\n")
        f.write(f"Claude: {args.claude_model}  |  Gemini: {args.gemini_model}  |  Mode: {mode_str}\n")
        f.write(f"{'=' * 70}\n")
        for e in transcript:
            if e["speaker"] == "seed":
                f.write(f"\n[SEED] (turn 0)\n{e['text']}\n")
                continue
            u = e.get("usage", {})
            marks = (" TRUNCATED" if e.get("truncated") else "") + \
                    (" EMPTY" if e.get("empty_response") else "")
            f.write(f"\n[{e['speaker'].upper()}] (turn {e['turn']}, "
                    f"out={u.get('output_tokens')}, stop={e.get('stop_reason')}{marks})\n"
                    f"{e['text']}\n")

    c, g = totals["claude"], totals["gemini"]
    print(f"\n\n{'=' * 70}\nDone. {n_turns} turns.")
    print(f"  Tokens — Claude: in {c.get('input_tokens', 0):,} / out {c.get('output_tokens', 0):,}"
          f"   |   Gemini: in {g.get('input_tokens', 0):,} / out {g.get('output_tokens', 0):,}"
          + (f" / thinking {g.get('thinking_tokens', 0):,}" if g.get("thinking_tokens") else ""))
    print(f"  JSON: {json_path}")
    print(f"  Text: {txt_path}")


if __name__ == "__main__":
    main()
