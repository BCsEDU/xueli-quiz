"""84 人同時在線並同時送出（以模擬的 Supabase REST 後端驗證前端併發與重試行為）
python tools/loadtest.py [人數]   需先啟動 8765 伺服器
"""
import asyncio, json, random, sys, time
from playwright.async_api import async_playwright
N = int(sys.argv[1]) if len(sys.argv) > 1 else 84
B = "http://127.0.0.1:8765/"; MOCK = "https://mock.supabase.co"
exams = json.load(open("data/exams.json"))
db = {}; stats = {"posts": 0, "fail503": 0, "dups": 0, "in_flight": 0, "max_in_flight": 0}
CFG = 'window.CONFIG={SUPABASE_URL:"%s",SUPABASE_ANON_KEY:"k",LOCAL_TEACHER_PASSWORD:"x",CLASSES:["4-1","4-2","4-3"],SEATS:29};' % MOCK
GIF1X1 = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"

async def mock_route(route):
    req = route.request; u = req.url
    if req.method == "OPTIONS":
        return await route.fulfill(status=204, headers={"access-control-allow-origin": "*", "access-control-allow-headers": "*", "access-control-allow-methods": "*"})
    h = {"access-control-allow-origin": "*", "content-type": "application/json"}
    if "/rest/v1/submissions" in u:
        stats["posts"] += 1
        stats["in_flight"] += 1
        stats["max_in_flight"] = max(stats["max_in_flight"], stats["in_flight"])
        try:
            if random.random() < 0.25:
                stats["fail503"] += 1
                return await route.fulfill(status=503, headers=h, body="busy")
            await asyncio.sleep(random.uniform(0.05, 0.3))
            d = json.loads(req.post_data)
            if d["client_id"] in db: stats["dups"] += 1
            else: db[d["client_id"]] = d
            return await route.fulfill(status=201, headers=h, body="")
        finally:
            stats["in_flight"] -= 1
    if "teacher_get_submissions" in u:
        pw = json.loads(req.post_data)["pw"]
        if pw != "secret": return await route.fulfill(status=400, headers=h, body="unauthorized")
        rng = req.headers.get("range", "0-999").split("-"); a, b = int(rng[0]), int(rng[1])
        return await route.fulfill(status=200, headers=h, body=json.dumps(list(db.values())[a:b + 1]))
    await route.fulfill(status=404, headers=h, body="")

async def student(br, sem, i, barrier, res):
    ctx = await br.new_context(viewport={"width": 1180, "height": 820})
    await ctx.route(B + "js/config.js*", lambda r: r.fulfill(status=200, content_type="text/javascript", body=CFG))
    await ctx.route(B + "img/**", lambda r: r.fulfill(status=200, content_type="image/gif", body=GIF1X1))
    await ctx.route(MOCK + "/**", mock_route)
    pg = await ctx.new_page()
    e = random.choice(exams); cls = ["4-1", "4-2", "4-3"][i % 3]; seat = i % 29 + 1
    async with sem:
        t0 = time.time()
        await pg.goto(B); await pg.wait_for_selector("#year option", state="attached")
        await pg.select_option("#subject", e["subject"]); await pg.select_option("#year", e["id"])
        await pg.select_option("#cls", cls); await pg.select_option("#seat", str(seat)); await pg.click("#go")
        login = time.time() - t0
        exp = 0
        for q, key in enumerate(e["answers"]):
            pick = key if random.random() < 0.6 else random.randint(1, 4)
            exp += pick == key
            await pg.click(f"#qs .q:nth-child({q+1}) .o[data-k='{pick}']")
    await barrier.wait()          # 84 個頁面同時在線，在同一瞬間全部按下送出
    t1 = time.time(); pg.once("dialog", lambda d: asyncio.ensure_future(d.accept()))
    await pg.click("#submit")
    await pg.wait_for_function("document.getElementById('up') && /✅|⚠/.test(document.getElementById('up').textContent)", timeout=60000)
    res.append({"i": i, "login": login, "submit": time.time() - t1, "ok": "✅" in await pg.inner_text("#up"), "exp": exp, "n": len(e["answers"]), "exam": e["id"], "cls": cls, "seat": seat,
                "shown": await pg.inner_text("#result .big")})
    await ctx.close()

async def main():
    async with async_playwright() as p:
        br = await p.chromium.launch(); sem = asyncio.Semaphore(28); barrier = asyncio.Barrier(N); res = []
        t0 = time.time()
        await asyncio.gather(*[student(br, sem, i, barrier, res) for i in range(N)])
        print(f"{N} 人全部在線並同時交卷完成，總耗時 {time.time()-t0:.1f}s")
        ok = sum(r["ok"] for r in res)
        print(f"單機開啟耗時 最慢 {max(r['login'] for r in res):.1f}s｜84 人同時按下送出→全數上傳完成 最慢 {max(r['submit'] for r in res):.1f}s")
        print(f"瞬間最大同時請求數: {stats['max_in_flight']}｜上傳成功 {ok}/{N}｜總請求 {stats['posts']} 次（含模擬 25% 網路失敗 {stats['fail503']} 次，全靠自動重試救回）｜重複寫入被擋 {stats['dups']}")
        print(f"後台資料庫收到 {len(db)} 筆（應為 {N}）")
        assert all(f"{r['exp']} / {r['n']}" == r["shown"] for r in res), "學生畫面分數與預期不符"
        assert all(d["score"] <= d["total"] for d in db.values())
        ctx = await br.new_context(); await ctx.route(B + "js/config.js*", lambda r: r.fulfill(status=200, content_type="text/javascript", body=CFG))
        await ctx.route(MOCK + "/**", mock_route); t = await ctx.new_page(); await t.goto(B + "teacher.html")
        await t.fill("#pw", "secret"); await t.click("#ok"); await t.wait_for_selector("#main:not(.hidden)")
        n = await t.locator("#st tr").count() - 1
        print(f"教師端列出 {n} 筆；統計列：", (await t.inner_text('#stats')).replace("\n", " "))
        assert n == N and len(db) == N and ok == N
        print("84 人併發壓測全數通過 ✅")
        await br.close()
asyncio.run(main())
