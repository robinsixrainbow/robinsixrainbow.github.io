# Copyright (c) 2026 Kuo-Chen Wu (吳國禎). All Rights Reserved.
"""cv_backend — 個人網站的本機 CMS。
編輯 → 預覽 → 一鍵發佈（重生成 index.html → ots 蓋章 → git 推送）。"""
import html as _html
import os
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from .db import engine
from .models import Base
from .admin import mount_admin
from .publisher import generate_html, publish
from .settings import SITE_REPO

Base.metadata.create_all(engine)
app = FastAPI(title="cv_backend")
mount_admin(app, engine)

# sqladmin >=0.28 相容墊片（planetarian_site 的教訓）
from fastapi.responses import RedirectResponse as _RR
@app.get("/admin", include_in_schema=False)
async def _admin_root():
    return _RR(url="/admin/", status_code=307)

PAGE = """<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="utf-8">
<title>CV 管理台</title><style>
body{{background:#0a1424;color:#eaf7f8;font:15px/1.8 "Noto Sans TC",sans-serif;
     max-width:720px;margin:48px auto;padding:0 24px}}
h1{{font-weight:300;letter-spacing:.2em;color:#28efef;font-size:20px}}
a,button{{color:#eaf7f8;border:1px solid rgba(255,255,255,.4);border-radius:18px;
  padding:8px 22px;text-decoration:none;background:none;font:inherit;cursor:pointer;
  transition:all .3s ease-out;display:inline-block;margin:6px 10px 6px 0}}
a:hover,button:hover{{background:#106060;border-color:#106060}}
pre{{background:rgba(0,0,0,.5);border:1px solid rgba(255,255,255,.18);
  border-radius:4px;padding:14px 18px;white-space:pre-wrap;font-size:13px}}
.dim{{color:rgba(255,255,255,.5);font-size:12px}}
</style></head><body>
<h1>CV 管理台 · GENTLE JENA</h1>
<p><a href="/admin/">✎ 內容編輯（後台）</a><a href="/preview" target="_blank">👁 本機預覽</a></p>
<form method="post" action="/publish">
<button type="submit">⤴ 發佈（生成 → 蓋章 → 推送）</button>
<label class="dim"><input type="checkbox" name="no_ots" value="1"> 略過 ots</label>
<label class="dim"><input type="checkbox" name="no_git" value="1"> 略過 git</label>
</form>
<p class="dim">網站 repo：{repo}</p>
{log}
</body></html>"""


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return PAGE.format(repo=_html.escape(os.path.abspath(SITE_REPO)), log="")


@app.get("/preview", response_class=HTMLResponse)
async def preview():
    html, _ = generate_html(os.path.abspath(SITE_REPO))
    return HTMLResponse(html)


@app.post("/publish", response_class=HTMLResponse)
async def do_publish(no_ots: str = Form(default=""), no_git: str = Form(default="")):
    log = publish(do_ots=not no_ots, do_git=not no_git)
    body = "<pre>" + _html.escape("\n".join(log)) + "</pre>"
    return PAGE.format(repo=_html.escape(os.path.abspath(SITE_REPO)), log=body)
