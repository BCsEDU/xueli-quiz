"""端對端測試：python tools/e2e.py （需先 python3 -m http.server 8765 --bind 127.0.0.1）"""
import json, os
from playwright.sync_api import sync_playwright
B = "http://127.0.0.1:8765/"
exams = json.load(open(os.path.join(os.path.dirname(__file__), "..", "data", "exams.json")))
fail = []
def check(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fail.append(m)
with sync_playwright() as p:
    br = p.chromium.launch(); ctx = br.new_context(viewport={"width": 1300, "height": 900}, accept_downloads=True); pg = ctx.new_page()
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("console", lambda m: m.type == "error" and errs.append(m.text))
    pg.goto(B); pg.wait_for_selector("#year option", state="attached")
    check(pg.locator("#cls option").all_inner_texts() == ["4-1", "4-2", "4-3"], "班級選項")
    check(pg.locator("#seat option").count() == 29, "座號 1~29")
    check(pg.locator("#grade option[value='4']").is_disabled(), "四年級停用")
    # 每份試卷：所有圖片可載入、年份選項正確
    for e in exams:
        pg.select_option("#subject", e["subject"])
        check(pg.locator(f"#year option[value='{e['id']}']").count() == 1, f"年份選項 {e['id']}")
    for e in exams:
        pg.goto(B); pg.wait_for_selector("#year option", state="attached"); pg.select_option("#subject", e["subject"]); pg.select_option("#year", e["id"])
        cls = ["4-1", "4-2", "4-3"][e["year"] % 3]; seat = e["year"] % 29 + 1
        pg.select_option("#cls", cls); pg.select_option("#seat", str(seat))
        pg.click("#go")
        n = len(e["answers"])
        check(pg.locator("#qs .q").count() == n, f"{e['id']} 題數 {n}")
        # 先全部捲動載入圖片
        pg.evaluate("document.querySelectorAll('#pages img').forEach(i=>i.loading='eager')"); pg.wait_for_timeout(500)
        ok = pg.evaluate("Promise.all([...document.querySelectorAll('#pages img')].map(i=>i.complete?i.naturalWidth>0:new Promise(r=>{i.onload=()=>r(true);i.onerror=()=>r(false)})))")
        check(all(ok) and len(ok) == len(e["pages"]), f"{e['id']} 圖片全載入 ({len(ok)})")
        # 作答：偶數題答對、奇數題故意答錯、第 1 題以外每 7 題留白
        exp_wrong = []; exp_score = 0
        for i, key in enumerate(e["answers"]):
            if i % 7 == 6: exp_wrong.append(i + 1); continue
            pick = key if i % 2 == 0 else key % 4 + 1
            pg.click(f"#qs .q:nth-child({i+1}) .o[data-k='{pick}']")
            if pick == key: exp_score += 1
            else: exp_wrong.append(i + 1)
        pg.once("dialog", lambda d: d.accept())
        pg.click("#submit"); pg.wait_for_timeout(300)
        txt = pg.inner_text("#result")
        check(f"{exp_score} / {n}" in txt, f"{e['id']} 分數 {exp_score}/{n}")
        check("、".join(map(str, exp_wrong)) in txt, f"{e['id']} 錯題清單")
        marks = pg.locator("#qs .m").all_inner_texts()
        check([i + 1 for i, m in enumerate(marks) if m == "❌"] == exp_wrong, f"{e['id']} ⭕❌ 標記")
        keys = pg.evaluate("[...document.querySelectorAll('.q')].map(r=>+r.querySelector('.key').dataset.k)")
        check(keys == e["answers"], f"{e['id']} 綠框=正確答案")
        check(pg.locator("#submit").is_hidden() and pg.locator("#again").is_visible(), f"{e['id']} 按鈕狀態")
        pg.click("#qs .q:nth-child(1) .o[data-k='1']")  # 送出後不可再改
        check(pg.evaluate("document.querySelectorAll('.sel').length") == 0, f"{e['id']} 送出後鎖定")
    pg.click("#again"); check(pg.locator("#start").is_visible(), "再測一次回首頁")
    # 題目區獨立縮放
    pg.goto(B); pg.wait_for_selector("#year option", state="attached"); pg.click("#go")
    sw = lambda: pg.evaluate("(()=>{const r=document.getElementById('sheet').getBoundingClientRect();return [r.width,r.height]})()")
    pw0 = pg.evaluate("document.getElementById('pages').getBoundingClientRect().width"); s0 = sw()
    pg.click("#zin"); pg.click("#zin")
    check(pg.inner_text("#zval") == "150%", "放大到 150%")
    check(pg.evaluate("document.getElementById('pages').getBoundingClientRect().width") > pw0 * 1.4, "題目區變寬")
    check(sw() == s0, "答案卡尺寸不變")
    check(not pg.evaluate("document.documentElement.scrollHeight>innerHeight+1"), "整頁不捲動")
    pg.click("#zout"); pg.click("#zout"); pg.click("#zout"); check(pg.inner_text("#zval") == "75%", "縮小到 75%")
    pg.click("#zfit"); check(pg.inner_text("#zval") == "100%", "符合寬度")
    # 返回鍵 + 草稿保留
    pg.goto(B); pg.wait_for_selector("#year option", state="attached")
    pg.select_option("#cls", "4-3"); pg.select_option("#seat", "29"); pg.click("#go")
    for i, k in [(1, 2), (2, 3), (5, 4)]: pg.click(f"#qs .q:nth-child({i}) .o[data-k='{k}']")
    pg.click("#back"); check(pg.locator("#start").is_visible() and pg.locator("#exam").is_hidden(), "返回鍵回選單")
    check("繼續" in pg.inner_text("#go"), "按鈕顯示『繼續測驗』")
    pg.click("#go")
    got = pg.evaluate("[...document.querySelectorAll('.q')].map(r=>{const s=r.querySelector('.sel');return s?+s.dataset.k:0})")
    check(got[:6] == [2, 3, 0, 0, 4, 0], f"返回後選項保留 {got[:6]}")
    pg.reload(); pg.wait_for_selector("#year option", state="attached"); pg.select_option("#cls", "4-3"); pg.select_option("#seat", "29"); pg.click("#go")
    got = pg.evaluate("[...document.querySelectorAll('.q')].map(r=>{const s=r.querySelector('.sel');return s?+s.dataset.k:0})")
    check(got[:6] == [2, 3, 0, 0, 4, 0], "重新整理後選項保留")
    pg.click("#back"); pg.select_option("#seat", "28"); pg.click("#go")
    check(pg.evaluate("document.querySelectorAll('.sel').length") == 0, "不同座號不會看到別人的草稿")
    pg.once("dialog", lambda d: d.accept()); pg.click("#submit"); pg.wait_for_timeout(300)
    check(pg.locator("#back").is_hidden(), "送出後隱藏返回鍵"); pg.click("#again")
    pg.select_option("#seat", "29"); pg.click("#go")
    check(pg.evaluate("document.querySelectorAll('.sel').length") == 3, "座號29草稿仍在")
    pg.once("dialog", lambda d: d.accept()); pg.click("#submit"); pg.wait_for_timeout(300)
    pg.click("#again"); pg.click("#go")
    check(pg.evaluate("document.querySelectorAll('.sel').length") == 0, "送出後草稿清除")
    # 教師端
    # 同 context 才共用 localStorage
    t = ctx.new_page(); t.on("pageerror", lambda e: errs.append(str(e)))
    t.goto(B + "teacher.html"); t.fill("#pw", "wrong"); t.click("#ok"); t.wait_for_timeout(300)
    check(t.locator("#main").is_hidden() and "錯誤" in t.inner_text("#err"), "錯誤密碼擋下")
    t.fill("#pw", ""); t.click("#pw"); t.keyboard.type("1234")
    check(t.input_value("#pw") == "1234", "密碼欄可用鍵盤輸入")
    t.keyboard.press("Enter"); t.wait_for_timeout(500)
    check(t.locator("#main").is_visible(), "正確密碼登入")
    check(t.locator("#st tr").count() == len(exams) + 3, "學生列")
    e = exams[0]; t.select_option("#fExam", e["id"]); t.wait_for_timeout(200)
    check("1" in t.inner_text("#stats"), "篩選後統計")
    n = len(e["answers"]); qrows = t.locator("#qt tr").count()
    check(qrows == n + 1, f"各題答對率 {n} 列")
    # 該卷 1 份：第1題(偶index→對)=100%，第 7 題留白=0%
    first = t.locator("#qt tr").nth(1).inner_text(); last = t.locator("#qt tr").nth(n).inner_text()
    check("0%" in first and "100%" in last, "答對率排序(低→高)")
    wrong_cell = t.locator("#st tr").nth(1).inner_text()
    check("7" in wrong_cell, "學生列顯示錯題")
    t.select_option("#fCls", "4-1"); t.wait_for_timeout(200)
    t.select_option("#fExam", ""); t.select_option("#fCls", ""); 
    with t.expect_download() as d: t.click("#csv")
    check(d.value.suggested_filename.endswith(".csv"), "CSV 匯出")
    t.once("dialog", lambda d: d.accept()); t.click("#st button[data-del]"); t.wait_for_timeout(300)
    check(t.locator("#st tr").count() == len(exams) + 2, "刪除一筆")
    t.click("#reload"); t.wait_for_timeout(200)
    check(not errs, f"無 JS 錯誤 {errs}")
    br.close()
print("\n失敗:", fail or "無")
