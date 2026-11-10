// 後端設定：留空 = 使用瀏覽器 localStorage（只能單機測試）
// 要讓全班資料集中到老師後台 → 建 Supabase 專案，跑 supabase.sql，填下面兩個值
window.CONFIG = {
  SUPABASE_URL: "", // 例: https://xxxx.supabase.co
  SUPABASE_ANON_KEY: "", // anon public key
  LOCAL_TEACHER_PASSWORD: "1234", // 僅 localStorage 模式使用；Supabase 模式密碼存在資料庫
  CLASSES: ["4-1", "4-2", "4-3"],
  SEATS: 29,
};
