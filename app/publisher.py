# Copyright (c) 2026 Kuo-Chen Wu (吳國禎). All Rights Reserved.
"""publisher — DB → I18N/CV_DATA JS 區塊 → 置換 index.html →（可選）ots 蓋章 → git 推送。
首次執行會自動在 index.html 植入哨兵標記；之後的發佈只置換標記之間的內容。"""
import json, os, re, shutil, subprocess, datetime
from .db import SessionLocal
from . import models as M

HERE = os.path.dirname(__file__)
UI = json.load(open(os.path.join(HERE, "ui_strings.json"), encoding="utf-8"))

S_I18N = ("/*==CV_I18N_START==*/", "/*==CV_I18N_END==*/")
S_DATA = ("/*==CV_DATA_START==*/", "/*==CV_DATA_END==**/".replace("*/*", "*/"))
S_DATA = ("/*==CV_DATA_START==*/", "/*==CV_DATA_END==*/")


def _tri(row, base):
    return {lang: getattr(row, f"{base}_{lang}") for lang in ("en", "zh", "ja")}


def build_payload():
    """回傳 (I18N dict, CV_DATA dict)——與現行網站的資料形狀完全一致。"""
    db = SessionLocal()
    try:
        i18n = {lang: dict(UI[lang]) for lang in ("en", "zh", "ja")}
        edu = db.query(M.Education).order_by(M.Education.sort, M.Education.id).all()
        skl = db.query(M.SkillGroup).order_by(M.SkillGroup.sort, M.SkillGroup.id).all()
        rol = db.query(M.Role).order_by(M.Role.sort, M.Role.id).all()
        exp = db.query(M.Experience).order_by(M.Experience.sort, M.Experience.id).all()
        for lang in ("en", "zh", "ja"):
            i18n[lang]["education"] = [
                {"school": getattr(e, f"school_{lang}"), "degree": getattr(e, f"degree_{lang}"),
                 "date": getattr(e, f"date_{lang}"), "place": getattr(e, f"place_{lang}")} for e in edu]
            i18n[lang]["skills"] = [
                {"ttl": getattr(s, f"ttl_{lang}"),
                 "items": [ln for ln in getattr(s, f"items_{lang}").splitlines() if ln.strip()]} for s in skl]
            i18n[lang]["currentRoles"] = [
                {"label": getattr(r, f"label_{lang}"), "org": getattr(r, f"org_{lang}")} for r in rol]
            i18n[lang]["experience"] = [
                {"role": getattr(x, f"role_{lang}"), "date": getattr(x, f"date_{lang}"),
                 "org": getattr(x, f"org_{lang}"), "project": getattr(x, f"project_{lang}"),
                 "star": {"S": getattr(x, f"star_s_{lang}"), "T": getattr(x, f"star_t_{lang}"),
                          "A": getattr(x, f"star_a_{lang}"), "R": getattr(x, f"star_r_{lang}")}} for x in exp]
        cv = {
            "journals": [
                {"q": j.q, "authors": j.authors, "title": j.title,
                 "journal": j.journal, "vol": j.vol, "doi": j.doi}
                for j in db.query(M.Journal).order_by(M.Journal.sort, M.Journal.id)],
            "conferences": [
                ({"venue": c.venue, "meta": c.meta_text, "title": c.title} | ({"invited": True} if c.invited else {}))
                for c in db.query(M.Conference).order_by(M.Conference.sort, M.Conference.id)],
            "competition": [
                {"year": c.year, "award": c.award, "body": c.body}
                for c in db.query(M.Competition).order_by(M.Competition.sort, M.Competition.id)],
            "patents": {
                reg: [{"id": p.pid, "date": p.date, "title": p.title}
                      for p in db.query(M.Patent).filter(M.Patent.region == reg)
                                 .order_by(M.Patent.sort, M.Patent.id)]
                for reg in ("tw", "cn", "us")},
        }
        return i18n, cv
    finally:
        db.close()


def _emit(name, obj):
    js = json.dumps(obj, ensure_ascii=False, indent=1)
    js = js.replace("</", "<\\/")          # JSON-in-<script> 加固
    return f"const {name} = {js};"


def _brace_block(src, decl):
    i = src.index(decl)
    j = src.index("{", i)
    d = 0
    for k in range(j, len(src)):
        if src[k] == "{":
            d += 1
        elif src[k] == "}":
            d -= 1
            if d == 0:
                end = k + 1
                if src[end:end + 1] == ";":
                    end += 1
                return i, end
    raise ValueError(f"unbalanced braces for {decl}")


def _ensure_sentinels(src):
    changed = False
    for (a, b), decl in ((S_I18N, "const I18N = {"), (S_DATA, "const CV_DATA = {")):
        if a not in src:
            i, e = _brace_block(src, decl)
            src = src[:i] + a + "\n" + src[i:e] + "\n" + b + src[e:]
            changed = True
    return src, changed


def _replace(src, sent, payload):
    a, b = sent
    i, j = src.index(a) + len(a), src.index(b)
    return src[:i] + "\n" + payload + "\n" + src[j:]


def generate_html(site_repo):
    idx = os.path.join(site_repo, "index.html")
    src = open(idx, encoding="utf-8").read()
    src, migrated = _ensure_sentinels(src)
    i18n, cv = build_payload()
    src = _replace(src, S_I18N, _emit("I18N", i18n))
    src = _replace(src, S_DATA, _emit("CV_DATA", cv))
    # 自我驗證：抽回兩塊、JSON 往返必須等值
    for sent, name, obj in ((S_I18N, "I18N", i18n), (S_DATA, "CV_DATA", cv)):
        a, b = sent
        block = src[src.index(a) + len(a): src.index(b)]
        body = block[block.index("{"): block.rindex("}") + 1].replace("<\\/", "</")
        assert json.loads(body) == obj, f"{name} roundtrip mismatch"
    return src, migrated


def publish(site_repo=None, do_ots=True, do_git=True, message=None):
    from .settings import SITE_REPO
    site_repo = os.path.abspath(site_repo or SITE_REPO)
    log = []
    idx = os.path.join(site_repo, "index.html")
    if not os.path.exists(idx):
        return [f"✗ 找不到 {idx} — 請確認 SITE_REPO 設定"]
    html, migrated = generate_html(site_repo)
    open(idx, "w", encoding="utf-8", newline="\n").write(html)
    log.append(f"✓ index.html 已重生成（{len(html):,} bytes）" + ("，並完成哨兵標記植入" if migrated else ""))

    ots_file = idx + ".ots"
    if do_ots:
        if shutil.which("ots") is None:
            log.append("△ 找不到 ots 指令 — 跳過蓋章（安裝 opentimestamps-client 後重試）")
        else:
            # 先嘗試升級 repo 內所有 pending 印章（含舊版檔案的）
            for f in os.listdir(site_repo):
                if f.endswith(".ots"):
                    r = subprocess.run(["ots", "upgrade", f], cwd=site_repo,
                                       capture_output=True, text=True, timeout=90)
                    tag = "已固化" if r.returncode == 0 else "尚未就緒（等區塊確認）"
                    log.append(f"  · upgrade {f} → {tag}")
            if os.path.exists(ots_file):
                os.remove(ots_file)
            r = subprocess.run(["ots", "stamp", "index.html"], cwd=site_repo,
                               capture_output=True, text=True, timeout=120)
            if r.returncode == 0 and os.path.exists(ots_file):
                log.append("✓ ots stamp 完成 → index.html.ots")
            else:
                log.append("✗ ots stamp 失敗：" + (r.stderr or r.stdout).strip()[:200])

    if do_git:
        try:
            import git
            repo = git.Repo(site_repo)
            paths = ["index.html"] + (["index.html.ots"] if os.path.exists(ots_file) else [])
            repo.index.add(paths)
            msg = message or f"cv: content update {datetime.date.today().isoformat()}"
            if repo.is_dirty(index=True, working_tree=False):
                repo.index.commit(msg)
                log.append(f"✓ git commit：{msg}（{'、'.join(paths)}）")
                try:
                    repo.remote().push()
                    log.append("✓ git push 完成 — 網站部署中")
                except Exception as e:
                    log.append(f"△ push 失敗（{type(e).__name__}）— 開 GitHub Desktop 按 Push 即可")
            else:
                log.append("· 內容無變更，未建立 commit")
        except Exception as e:
            log.append(f"△ git 不可用（{type(e).__name__}）— 開 GitHub Desktop：兩個檔案已就緒，commit + push 即可")
    return log
