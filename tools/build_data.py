"""從歷屆試題 PDF/XLSX 產生網站資料：頁面圖片 + data/exams.json
用法: python tools/build_data.py  (需 pymupdf openpyxl)
"""
import glob, json, os, re
import openpyxl, pymupdf

SRC = "/Users/shiebingchen/Desktop/潮和國小/學力測驗/三年級"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SUBJ = {"math": ("數學", "數學/*/{y}年*/*題本*.pdf", "數學/*/{y}年*/*答案.xlsx"),
        "chinese": ("國語", "國語/*/{y}年*/*題本*.pdf", "國語/*/{y}年*/*答案.xlsx")}
YEARS = [111, 112, 113, 114, 115]
exams = []
for key, (name, pdfg, ang) in SUBJ.items():
    for y in YEARS:
        pdfs = [p for p in glob.glob(os.path.join(SRC, pdfg.format(y=y))) if "疑義" not in p]
        xl = glob.glob(os.path.join(SRC, ang.format(y=y)))
        if not pdfs or not xl:
            continue
        ws = openpyxl.load_workbook(xl[0]).active
        row = list(ws.iter_rows(values_only=True))[1]
        ans = [int(v) for v in row[1:] if v is not None]
        doc = pymupdf.open(pdfs[0])
        # 第一個含題號的頁面開始（跳過封面/注意事項）
        first = 0
        for i, pg in enumerate(doc):
            if re.search(r"(^|\n)\s*1\s*[\.．]", pg.get_text()) or i >= 1 and "語文知識題" in pg.get_text():
                first = i; break
        d = os.path.join(OUT, "img", "g3", key, str(y)); os.makedirs(d, exist_ok=True)
        pages = []
        for i in range(first, len(doc)):
            f = f"p{i - first + 1}.jpg"
            doc[i].get_pixmap(dpi=120).save(os.path.join(d, f), jpg_quality=72)
            pages.append(f"img/g3/{key}/{y}/{f}")
        exams.append({"grade": 3, "subject": key, "subjectName": name, "year": y,
                      "id": f"g3-{key}-{y}", "answers": ans, "pages": pages})
        print(key, y, len(ans), "題", len(pages), "頁")
os.makedirs(os.path.join(OUT, "data"), exist_ok=True)
json.dump(exams, open(os.path.join(OUT, "data", "exams.json"), "w"), ensure_ascii=False)
