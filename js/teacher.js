import { loadExams, teacherFetch, teacherDelete, mode } from "./store.js?v=8";
const $ = (id) => document.getElementById(id);
const C = window.CONFIG;
let exams = [], rows = [], pw = "";

$("modeNote").textContent = mode === "local" ? "目前為本機模式（localStorage），資料只存在這台電腦。請設定 Supabase 以集中全班資料。" : "";
$("lf").onsubmit = async (ev) => {
  ev.preventDefault();
  pw = $("pw").value;
  try {
    exams = await loadExams();
    rows = await teacherFetch(pw);
    $("login").classList.add("hidden");
    $("main").classList.remove("hidden");
    init();
  } catch (e) { $("err").textContent = e.message; }
};

function init() {
  $("fExam").innerHTML = '<option value="">全部試卷</option>' + exams.map((e) => `<option value="${e.id}">${e.year}年 ${e.grade}年級${e.subjectName}</option>`).join("");
  $("fCls").innerHTML = '<option value="">全部班級</option>' + C.CLASSES.map((c) => `<option>${c}</option>`).join("");
  $("fExam").onchange = $("fCls").onchange = render;
  $("reload").onclick = async () => { rows = await teacherFetch(pw); render(); };
  $("csv").onclick = exportCsv;
  render();
}

const filtered = () => rows.filter((r) => (!$("fExam").value || r.exam_id === $("fExam").value) && (!$("fCls").value || r.class === $("fCls").value));
const pct = (n, d) => (d ? Math.round((n / d) * 100) : 0);
const bar = (p) => `<div class="bar ${p < 40 ? "low" : p < 70 ? "mid" : ""}"><i style="width:${p}%"></i></div>`;
const exOf = (id) => exams.find((e) => e.id === id);
const wrongList = (r) => { const ex = exOf(r.exam_id); return ex ? r.answers.map((a, i) => (a !== ex.answers[i] ? i + 1 : 0)).filter(Boolean) : []; };

function render() {
  const f = filtered();
  const avg = f.length ? Math.round(f.reduce((s, r) => s + pct(r.score, r.total), 0) / f.length) : 0;
  $("stats").innerHTML = `<div class="stat"><b>${f.length}</b>送出份數</div><div class="stat"><b>${avg}%</b>平均答對率</div><div class="stat"><b>${new Set(f.map((r) => r.class + "-" + r.seat)).size}</b>參與學生</div>`;

  // 各題答對率：僅在選定單一試卷時有意義
  const ex = exOf($("fExam").value);
  if (!ex) $("qt").innerHTML = "<tr><td>請先選擇單一試卷以查看各題答對率</td></tr>";
  else if (!f.length) $("qt").innerHTML = "<tr><td>尚無資料</td></tr>";
  else {
    const q = ex.answers.map((key, i) => {
      const dist = [0, 0, 0, 0, 0];
      f.forEach((r) => dist[r.answers[i] || 0]++);
      return { n: i + 1, key, dist, p: pct(dist[key], f.length) };
    }).sort((a, b) => a.p - b.p);
    $("qt").innerHTML = "<tr><th>題號</th><th>正確答案</th><th>答對率</th><th></th><th>答錯人數</th><th>選項分布 ①②③④／未答</th></tr>" +
      q.map((x) => `<tr><td>第 ${x.n} 題</td><td>${"①②③④"[x.key - 1]}</td><td>${x.p}%</td><td style="width:140px">${bar(x.p)}</td><td>${f.length - x.dist[x.key]}</td><td>${x.dist.slice(1).join(" / ")} ／ ${x.dist[0]}</td></tr>`).join("");
  }

  const byC = {};
  f.forEach((r) => { (byC[r.class] ||= []).push(r); });
  $("ct").innerHTML = "<tr><th>班級</th><th>份數</th><th>平均答對率</th><th></th></tr>" +
    Object.keys(byC).sort().map((c) => { const p = Math.round(byC[c].reduce((s, r) => s + pct(r.score, r.total), 0) / byC[c].length); return `<tr><td>${c}</td><td>${byC[c].length}</td><td>${p}%</td><td style="width:140px">${bar(p)}</td></tr>`; }).join("");

  $("st").innerHTML = "<tr><th>時間</th><th>試卷</th><th>班級</th><th>座號</th><th>分數</th><th>答錯題號</th><th></th></tr>" +
    f.map((r) => { const e = exOf(r.exam_id); return `<tr><td>${new Date(r.created_at).toLocaleString("zh-TW", { hour12: false })}</td><td>${e ? `${e.year}年${e.subjectName}` : r.exam_id}</td><td>${r.class}</td><td>${r.seat}</td><td>${r.score}/${r.total}（${pct(r.score, r.total)}%）</td><td>${wrongList(r).join("、") || "—"}</td><td><button class="sec" data-del="${r.id}" style="padding:2px 8px">刪</button></td></tr>`; }).join("");
  $("st").onclick = async (ev) => {
    const id = ev.target.dataset.del;
    if (!id || !confirm("刪除這筆紀錄？")) return;
    await teacherDelete(pw, isNaN(+id) ? id : +id);
    rows = await teacherFetch(pw); render();
  };
}

function exportCsv() {
  const f = filtered();
  const lines = [["時間", "試卷", "班級", "座號", "分數", "總題數", "答錯題號"], ...f.map((r) => [r.created_at, r.exam_id, r.class, r.seat, r.score, r.total, wrongList(r).join(" ")])];
  const blob = new Blob(["\ufeff" + lines.map((l) => l.join(",")).join("\n")], { type: "text/csv" });
  const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "學力檢測成績.csv"; a.click();
}
