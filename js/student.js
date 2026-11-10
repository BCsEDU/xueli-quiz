import { loadExams, saveSubmission, mode } from "./store.js?v=5";
const $ = (id) => document.getElementById(id);
const C = window.CONFIG;
const SYM = ["①", "②", "③", "④"];
let exams = [], exam, ans = [], done = false;

(async function init() {
  exams = await loadExams();
  $("cls").innerHTML = C.CLASSES.map((c) => `<option>${c}</option>`).join("");
  $("seat").innerHTML = Array.from({ length: C.SEATS }, (_, i) => `<option value="${i + 1}">${i + 1} 號</option>`).join("");
  $("subject").onchange = fillYears;
  fillYears();
  $("go").onclick = start;
  ["subject", "year", "cls", "seat"].forEach((id) => $(id).addEventListener("change", refreshGo));
  refreshGo();
})();

// ---- 草稿：作答中的選項存在 localStorage，返回或重新整理都不會消失 ----
const keyOf = (id) => `xueli_draft|${id}|${$("cls").value}|${$("seat").value}`;
const loadDraft = (id, n) => {
  try {
    const d = JSON.parse(localStorage.getItem(keyOf(id)));
    return Array.isArray(d) && d.length === n ? d : null;
  } catch { return null; }
};
const saveDraft = () => localStorage.setItem(keyOf(exam.id), JSON.stringify(ans));
function refreshGo() {
  const e = exams.find((x) => x.id === $("year").value);
  $("go").textContent = e && loadDraft(e.id, e.answers.length)?.some(Boolean) ? "繼續測驗（有未完成的作答）" : "開始測驗";
}

function fillYears() {
  const ys = exams.filter((e) => e.grade == $("grade").value && e.subject === $("subject").value).sort((a, b) => b.year - a.year);
  $("year").innerHTML = ys.map((e) => `<option value="${e.id}">${e.year} 年（${e.answers.length} 題）</option>`).join("");
  if (typeof refreshGo === "function" && exams.length) refreshGo();
}

function start() {
  exam = exams.find((e) => e.id === $("year").value);
  if (!exam) return ($("err").textContent = "請選擇年份");
  ans = loadDraft(exam.id, exam.answers.length) || Array(exam.answers.length).fill(0);
  done = false;
  $("start").classList.add("hidden");
  $("exam").classList.remove("hidden");
  $("pages").innerHTML = exam.pages.map((p) => `<img loading="lazy" src="${p}">`).join("");
  $("info").textContent = `${exam.year}年 三年級${exam.subjectName}｜${$("cls").value} ${$("seat").value}號 ${$("name").value}`;
  $("qs").innerHTML = ans.map((_, i) => `<div class="q" data-i="${i}"><b>${i + 1}.</b>${SYM.map((s, k) => `<span class="o" data-k="${k + 1}">${s}</span>`).join("")}<span class="m"></span></div>`).join("");
  document.querySelectorAll(".q").forEach((row, i) => row.querySelectorAll(".o").forEach((o) => o.classList.toggle("sel", +o.dataset.k === ans[i])));
  $("back").onclick = () => { $("exam").classList.add("hidden"); $("start").classList.remove("hidden"); refreshGo(); scrollTo(0, 0); };
  scrollTo(0, 0);
  $("qs").onclick = (e) => {
    const o = e.target.closest(".o");
    if (!o || done) return;
    const i = +o.parentNode.dataset.i, k = +o.dataset.k;
    ans[i] = k;
    saveDraft();
    o.parentNode.querySelectorAll(".o").forEach((x) => x.classList.toggle("sel", +x.dataset.k === k));
  };
  $("back").classList.remove("hidden");
  $("submit").classList.remove("hidden");
  $("again").classList.add("hidden");
  $("result").classList.add("hidden");
  $("submit").onclick = submit;
  $("again").onclick = () => { $("back").classList.remove("hidden"); $("exam").classList.add("hidden"); $("start").classList.remove("hidden"); scrollTo(0, 0); };
}

async function submit() {
  const blank = ans.filter((a) => !a).length;
  if (blank && !confirm(`還有 ${blank} 題沒作答，確定要送出嗎？`)) return;
  done = true;
  localStorage.removeItem(keyOf(exam.id));
  $("back").classList.add("hidden");
  let score = 0;
  document.querySelectorAll(".q").forEach((row, i) => {
    const right = exam.answers[i];
    row.querySelectorAll(".o").forEach((o) => {
      const k = +o.dataset.k;
      o.classList.remove("sel");
      if (k === right) o.classList.add("key");
      if (k === ans[i]) o.classList.add(k === right ? "ok" : "bad");
    });
    row.querySelector(".m").textContent = ans[i] === right ? "⭕" : "❌";
    if (ans[i] === right) score++;
  });
  const total = exam.answers.length;
  const wrong = ans.map((a, i) => (a !== exam.answers[i] ? i + 1 : 0)).filter(Boolean);
  $("result").classList.remove("hidden");
  $("result").innerHTML = `<div class="big">${score} / ${total}</div>答對率 ${Math.round((score / total) * 100)}%<br><small>答錯：${wrong.join("、") || "全對 🎉"}<br>綠框＝正確答案</small>`;
  $("submit").classList.add("hidden");
  $("again").classList.remove("hidden");
  $("sheet").scrollTo(0, 0);
  try {
    await saveSubmission({ exam_id: exam.id, grade: exam.grade, subject: exam.subject, year: exam.year, class: $("cls").value, seat: +$("seat").value, name: $("name").value.trim() || null, answers: ans, score, total });
  } catch (e) {
    $("result").innerHTML += `<br><b style="color:#e74c3c">⚠ 成績上傳失敗，請告訴老師</b>`;
    console.error(e);
  }
}
