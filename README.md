# 學力檢測歷屆試題練習

三年級（國語 111–114、數學 111–115）。學生選班級/座號作答 → 送出即時對答案 → 成績寫入後台，教師看答對率與錯誤題目。

- 學生：`index.html`　教師：`teacher.html`
- 重新產生題目：`python tools/build_data.py`（需 `pymupdf openpyxl`）
- 本機預覽：`python3 -m http.server`（不能直接開 file://，ES module 會被擋）
- 後端：預設 localStorage（單機）。要集中資料 → 建 Supabase 專案 → 跑 `supabase.sql`（先改教師密碼）→ 把 URL / anon key 填進 `js/config.js`
- 部署：推到 GitHub → Settings → Pages → main / root
