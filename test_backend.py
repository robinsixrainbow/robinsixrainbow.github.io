#!/usr/bin/env python3
# Copyright (c) 2026 Kuo-Chen Wu (吳國禎). All Rights Reserved.
"""cv_backend 驗收：發佈保真、冪等、git 提交、後台全表面稽核、預覽端點。"""
import json, os, re, shutil, subprocess, sys, time, signal, urllib.request, urllib.parse, http.cookiejar

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
PASS = []
def check(name, ok):
    PASS.append((name, bool(ok)))
    print(("ok  " if ok else "FAIL ") + name)

# ---------- 1) publisher：保真 / 冪等 / git ----------
repo = "/tmp/cvb_repo"
shutil.rmtree(repo, ignore_errors=True)
os.makedirs(repo)
shutil.copy("/home/claude/cv_bundle/index.html", repo + "/index.html")
subprocess.run(["git", "init", "-q", repo], check=True)
subprocess.run(["git", "-C", repo, "config", "user.email", "t@t"], check=True)
subprocess.run(["git", "-C", repo, "config", "user.name", "t"], check=True)
subprocess.run(["git", "-C", repo, "add", "-A"], check=True)
subprocess.run(["git", "-C", repo, "commit", "-qm", "base"], check=True)

os.environ["SITE_REPO"] = repo
from app.publisher import publish, S_I18N, S_DATA

log1 = publish(site_repo=repo, do_ots=False, do_git=True, message="test publish")
check("publish 執行（重生成）", any("重生成" in l for l in log1))
src = open(repo + "/index.html", encoding="utf-8").read()
check("哨兵標記已植入", all(m in src for m in (*S_I18N, *S_DATA)))

# 保真：發佈輸出 vs 原站資料（deep-equal）
orig = json.load(open("/tmp/cvdata.json"))
def extract(name):
    blk = src[src.index(f"const {name} = "):]
    body = blk[blk.index("{"):]
    d = 0
    for k, ch in enumerate(body):
        if ch == "{": d += 1
        elif ch == "}":
            d -= 1
            if d == 0:
                return json.loads(body[:k+1].replace("<\\/", "</"))
i18n_out, cv_out = extract("I18N"), extract("CV_DATA")
check("I18N 深度等值於原站", i18n_out == orig["I18N"])
check("CV_DATA 深度等值於原站", cv_out == orig["CV_DATA"])

# 產出的 JS 區塊語法有效（node）
open("/tmp/cvb_blocks.js", "w").write(
    src[src.index(S_I18N[0]) + len(S_I18N[0]): src.index(S_I18N[1])] + "\n" +
    src[src.index(S_DATA[0]) + len(S_DATA[0]): src.index(S_DATA[1])])
check("產出區塊 node --check", subprocess.run(["node", "--check", "/tmp/cvb_blocks.js"]).returncode == 0)

# 整頁 JS 仍有效
m = re.findall(r"<script>(.*?)</script>", src, re.S)
open("/tmp/cvb_page.js", "w").write(m[-1])
check("整頁主 script node --check", subprocess.run(["node", "--check", "/tmp/cvb_page.js"]).returncode == 0)

# 冪等：再發佈一次 → 位元組相同
publish(site_repo=repo, do_ots=False, do_git=False)
src2 = open(repo + "/index.html", encoding="utf-8").read()
check("冪等（二次發佈位元組相同）", src == src2)

# git：有 commit 且含 index.html
lg = subprocess.run(["git", "-C", repo, "log", "--oneline", "--name-only", "-1"],
                    capture_output=True, text=True).stdout
check("git commit 建立且含 index.html", "test publish" in lg and "index.html" in lg)

# ---------- 2) 伺服器：後台全表面 + 預覽 + 發佈端點 ----------
env = dict(os.environ, CV_DB="/tmp/cvb_test.db", SITE_REPO=repo)
for f in ("/tmp/cvb_test.db", "/tmp/cvb_test.db-wal", "/tmp/cvb_test.db-shm"):
    try: os.remove(f)
    except FileNotFoundError: pass
shutil.copy(os.path.join(HERE, "data", "cv.db"), "/tmp/cvb_test.db")
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8123"],
                       cwd=HERE, env=env, stdout=open("/tmp/cvb_srv.log", "w"), stderr=subprocess.STDOUT)
try:
    for _ in range(60):
        try:
            urllib.request.urlopen("http://127.0.0.1:8123/", timeout=1); break
        except Exception:
            time.sleep(0.5)

    cj = http.cookiejar.CookieJar()
    class NR(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k): return None
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op_nr = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj), NR())
    def req(url, data=None, redirects=True):
        o = op if redirects else op_nr
        body = urllib.parse.urlencode(data).encode() if data is not None else None
        try:
            return o.open("http://127.0.0.1:8123" + url, body, timeout=10).status
        except urllib.error.HTTPError as e:
            return e.code

    check("儀表板 200", req("/") == 200)
    check("裸 /admin 轉向", req("/admin", redirects=False) in (302, 303, 307))
    req("/admin/login")
    check("登入 302", req("/admin/login", {"username": "admin", "password": "planetarian"}, redirects=False) in (302, 303))

    MODELS = {
        "journal":     {"sort": "99", "q": "Q1", "authors": "a", "title": "t", "journal": "J", "vol": "1", "doi": ""},
        "conference":  {"sort": "99", "venue": "V", "meta_text": "m", "title": "t"},
        "competition": {"sort": "99", "year": "2026", "award": "a", "body": "b"},
        "patent":      {"sort": "99", "region": "tw", "pid": "X1", "date": "d", "title": "t"},
        "education":   {"sort": "99", **{f"{f}_{l}": "x" for f in ("school","degree","date","place") for l in ("en","zh","ja")}},
        "skill-group": {"sort": "99", **{f"{f}_{l}": "x" for f in ("ttl","items") for l in ("en","zh","ja")}},
        "role":        {"sort": "99", **{f"{f}_{l}": "x" for f in ("label","org") for l in ("en","zh","ja")}},
        "experience":  {"sort": "99", **{f"{f}_{l}": "x" for f in ("role","date","org","project") for l in ("en","zh","ja")},
                        **{f"star_{s}_{l}": "x" for s in "star" for l in ("en","zh","ja")},
                        **{f"star_{s}_{l}": "x" for s in ("s","t","a","r") for l in ("en","zh","ja")}},
    }
    allok = True
    for mname, payload in MODELS.items():
        c1 = req(f"/admin/{mname}/list")
        c2 = req(f"/admin/{mname}/create")
        c3 = req(f"/admin/{mname}/create", payload, redirects=False)
        c4 = req(f"/admin/{mname}/edit/1")
        c5 = req(f"/admin/{mname}/edit/1", payload, redirects=False)
        ok = c1 == 200 and c2 == 200 and c3 in (302, 303) and c4 == 200 and c5 in (302, 303)
        if not ok:
            allok = False
            print(f"    {mname}: list={c1} create={c2} POST={c3} edit={c4} editPOST={c5}")
    check("後台全表面（8 模型 × 5 面）", allok)

    check("預覽端點 200", req("/preview") == 200)
    check("發佈端點（略過 ots/git）", req("/publish", {"no_ots": "1", "no_git": "1"}) == 200)
finally:
    srv.send_signal(signal.SIGTERM); time.sleep(1)
    try: srv.kill()
    except Exception: pass

n_ok = sum(1 for _, v in PASS if v)
print(f"\nRESULT: {n_ok}/{len(PASS)}")
sys.exit(0 if n_ok == len(PASS) else 1)
