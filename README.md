# cv_backend — 個人網站管理台

本機 CMS：表單編輯履歷內容 → 本機預覽 → 一鍵發佈。
發佈 = 重生成 index.html → 自動 `ots stamp`（並順手 upgrade 舊印章）→ 自動 git commit + push。
線上維持純靜態 GitHub Pages，零成本、零攻擊面。

## 快速開始（Windows）
1. 解壓本資料夾，放在你網站 repo 的「旁邊」（例：`Documents\GitHub\cv_backend`，
   與 `robinsixrainbow.github.io` 同層）——這樣預設路徑直接生效。
2. 雙擊 `start.bat`（首次會自動安裝依賴）。
3. 瀏覽器開 http://127.0.0.1:8100
   - **內容編輯**：帳密 admin / planetarian（可用環境變數 ADMIN_USERNAME / ADMIN_PASSWORD 覆蓋）
   - **本機預覽**：發佈前先看成品
   - **發佈**：一顆按鈕，log 直接顯示每一步結果

## 發佈按鈕做的事
1. 從資料庫重生成 I18N / CV_DATA 兩個資料區塊，外科手術式置換進 repo 的 index.html
   （首次發佈會自動植入哨兵標記 `/*==CV_..._START/END==*/`，之後只動標記之間）
2. `ots upgrade` repo 內所有待固化印章 → 刪舊 `.ots` → `ots stamp index.html`
   （找不到 ots 指令時跳過並提示，不擋發佈）
3. GitPython commit（index.html ＋ 新 .ots）並 push
   （git 不可用或 push 失敗時，開 GitHub Desktop 按一下即可——檔案都已就緒）

## 設定
- 網站 repo 不在預設位置時：編輯 `start.bat` 開頭加一行
  `set SITE_REPO=C:\完整\路徑\robinsixrainbow.github.io`
- 其他：`PORT`（預設 8100）、`SECRET_KEY`

## 資料庫
`data/cv.db` 出貨時已播種目前網站的全部內容（期刊 15、研討會 5、競賽 17、專利 9、
學歷 2、技能 3、職務 4、經歷 3）。若你日後手動改了網站資料想反向同步回 DB：
`python seed_from_site.py 路徑\to\index.html`（需要 node）。

## 驗收
`python test_backend.py` — 14 項：發佈保真（與原站深度等值）、冪等、git、
後台全表面（8 模型 × 5 面）、預覽與發佈端點。

## 安全
伺服器只綁 127.0.0.1（run.py），僅本機可達；這是你一個人的管理台。
UI 措辭字串在 `app/ui_strings.json`（badge、章節標題等），要改直接編輯後重新發佈。
