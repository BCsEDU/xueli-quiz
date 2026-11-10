// 資料存取層：Supabase REST（有設定）或 localStorage（沒設定）
const C = window.CONFIG;
const remote = !!(C.SUPABASE_URL && C.SUPABASE_ANON_KEY);
const LS = "xueli_submissions";
const hdr = () => ({ apikey: C.SUPABASE_ANON_KEY, Authorization: "Bearer " + C.SUPABASE_ANON_KEY, "Content-Type": "application/json" });

export const mode = remote ? "supabase" : "local";

export async function loadExams() {
  return (await fetch("data/exams.json")).json();
}

export async function saveSubmission(s) {
  if (!remote) {
    const all = JSON.parse(localStorage.getItem(LS) || "[]");
    all.push({ ...s, id: Date.now(), created_at: new Date().toISOString() });
    localStorage.setItem(LS, JSON.stringify(all));
    return;
  }
  const r = await fetch(C.SUPABASE_URL + "/rest/v1/submissions", { method: "POST", headers: { ...hdr(), Prefer: "return=minimal" }, body: JSON.stringify(s) });
  if (!r.ok) throw new Error(await r.text());
}

export async function teacherFetch(pw) {
  if (!remote) {
    if (pw !== C.LOCAL_TEACHER_PASSWORD) throw new Error("密碼錯誤");
    return JSON.parse(localStorage.getItem(LS) || "[]");
  }
  const r = await fetch(C.SUPABASE_URL + "/rest/v1/rpc/teacher_get_submissions", { method: "POST", headers: hdr(), body: JSON.stringify({ pw }) });
  if (!r.ok) throw new Error("密碼錯誤或連線失敗");
  return r.json();
}

export async function teacherDelete(pw, id) {
  if (!remote) {
    const all = JSON.parse(localStorage.getItem(LS) || "[]").filter((x) => x.id !== id);
    return localStorage.setItem(LS, JSON.stringify(all));
  }
  const r = await fetch(C.SUPABASE_URL + "/rest/v1/rpc/teacher_delete_submission", { method: "POST", headers: hdr(), body: JSON.stringify({ pw, sid: id }) });
  if (!r.ok) throw new Error("刪除失敗");
}
