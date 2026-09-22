/* def 50 · 演示态缓存纪律（用户 2026-09-22）：
   ① F5 刷新 / 直接打开新标签 / 后端重启 → 清空全部本地演示缓存：
      sessionStorage（校色开关 cvd_theme · AI 回填 cb_fill · 对话展开态）+
      localStorage（AI 对话会话 · 窗口位置/大小/分隔宽度/TTS 偏好）+
      IndexedDB cb_tryon（试妆照片槽——原图 dataURL 本地缓存）
   ② 站内跳转（小标签内切换页面）→ 保留：跳转前经 cbNavKeep() 登记标记，
      目标页读到标记即跳过清理（覆盖：AI 调度跳页 / 色号回填跳试妆 / 定制申请跳时间线）
   ③ 后端重启检测：轮询 /api/health 的 boot_id，变化 → 清空 + 自动刷新回全新界面。
   本脚本必须在各页公共脚本最前加载（先清缓存，chatbox/theme_cvd 再初始化）。 */
(function () {
  const KEEPER = "cb_nav_keep";
  let keep = false;
  try {
    keep = sessionStorage.getItem(KEEPER) === "1";
    sessionStorage.removeItem(KEEPER);
  } catch (e) {}

  function wipe() {
    try { sessionStorage.clear(); } catch (e) {}
    try { localStorage.clear(); } catch (e) {}
    try { indexedDB.deleteDatabase("cb_tryon"); } catch (e) {}
  }
  if (!keep) wipe();

  /* 站内跳转登记：跳转前调一次，目标页读到标记即保留缓存 */
  window.cbNavKeep = function () {
    try { sessionStorage.setItem(KEEPER, "1"); } catch (e) {}
  };

  /* 后端重启检测：boot 基线是内存变量（不落盘）——重启必变 → wipe + reload */
  let boot = null;
  async function pollBoot() {
    try {
      const r = await fetch("/api/health", { cache: "no-store" });
      const j = await r.json();
      if (boot === null) { boot = j.boot_id; return; }   // 首次 = 建基线
      if (j.boot_id !== boot) {
        boot = j.boot_id;
        wipe();
        location.reload();                               // 回到全新界面
      }
    } catch (e) { /* 后端未就绪：静默，下轮再试 */ }
  }
  pollBoot();
  setInterval(pollBoot, 4000);
})();