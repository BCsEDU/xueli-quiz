// 資料存取層：Supabase REST（有設定）或 localStorage（沒設定）
const C = window.CONFIG;
const remote = !!(C.SUPABASE_URL && C.SUPABASE_ANON_KEY);
const LS = "xueli_submissions";
const hdr = () => ({ apikey: C.SUPABASE_ANON_KEY, Authorization: "Bearer " + C.SUPABASE_ANON_KEY, "Content-Type": "application/json" });

export const mode = remote ? "supabase" : "local";

export async function loadExams() {
  return (await fetch("data/exams.json")).json();
}

const PENDING = "xueli_pending";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const uuid = () => (crypto.randomUUID ? crypto.randomUUID() : "id-" + Date.now() + "-" + Math.random().toString(36).slice(2));

async function postOnce(s) {
  const r = await fetch(C.SUPABASE_URL + "/rest/v1/submissions?on_conflict=client_id", {
    method: "POST",
    headers: { ...hdr(), Prefer: "resolution=ignore-duplicates,return=minimal" },
    body: JSON.stringify(s),
  });
  if (!r.ok) throw new Error(r.status + " " + (await r.text()));
}

// 帶指數退避 + 隨機抖動的重試；client_id 讓重送不會產生重複資料
async function postWithRetry(s, tries = 6) {
  for (let i = 0; i < tries; i++) {
    try { return await postOnce(s); } catch (e) {
      if (i === tries - 1) throw e;
      await sleep(Math.min(8000, 500 * 2 ** i) * (0.5 + Math.random()));
    }
  }
}

const getPending = () => JSON.parse(localStorage.getItem(PENDING) || "[]");
const setPending = (a) => localStorage.setItem(PENDING, JSON.stringify(a));

/** 回傳 "ok"（已上傳）或 "queued"（暫存在本機，之後自動重送） */
export async function saveSubmission(s) {
  s = { ...s, client_id: uuid() };
  if (!remote) {
    const all = JSON.parse(localStorage.getItem(LS) || "[]");
    all.push({ ...s, id: Date.now(), created_at: new Date().toISOString() });
    localStorage.setItem(LS, JSON.stringify(all));
    return "ok";
  }
  try { await postWithRetry(s); return "ok"; } catch (e) {
    console.error(e);
    setPending([...getPending(), s]);
    return "queued";
  }
}

/** 重送先前失敗暫存的成績（頁面載入、網路恢復時呼叫） */
export async function flushPending() {
  if (!remote) return 0;
  let left = [];
  for (const s of getPending()) { try { await postWithRetry(s, 2); } catch { left.push(s); } }
  setPending(left);
  return left.length;
}
export const pendingCount = () => getPending().length;

export async function teacherFetch(pw) {
  if (!remote) {
    if (pw !== C.LOCAL_TEACHER_PASSWORD) throw new Error("密碼錯誤");
    return JSON.parse(localStorage.getItem(LS) || "[]");
  }
  const all = [];
  for (let from = 0; ; from += 1000) {
    const r = await fetch(C.SUPABASE_URL + "/rest/v1/rpc/teacher_get_submissions", { method: "POST", headers: { ...hdr(), Range: `${from}-${from + 999}`, "Range-Unit": "items" }, body: JSON.stringify({ pw }) });
    if (!r.ok) throw new Error("密碼錯誤或連線失敗");
    const part = await r.json();
    all.push(...part);
    if (part.length < 1000) return all;
  }
}

export async function teacherDelete(pw, id) {
  if (!remote) {
    const all = JSON.parse(localStorage.getItem(LS) || "[]").filter((x) => x.id !== id);
    return localStorage.setItem(LS, JSON.stringify(all));
  }
  const r = await fetch(C.SUPABASE_URL + "/rest/v1/rpc/teacher_delete_submission", { method: "POST", headers: hdr(), body: JSON.stringify({ pw, sid: id }) });
  if (!r.ok) throw new Error("刪除失敗");
}
