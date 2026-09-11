/* def 20 v2 · 伴随 AI 悬浮窗（全站常驻 · 跨页连续 · 自由拖动）
 * R-05：不设独立 chat 子页，悬浮窗内嵌大脑；用户指示 2026-09-11：悬浮窗于所有页面常驻，
 *      不受标签切换影响，可自由拖动。
 * 跨页连续性（同标签跳转不丢状态）：
 *   - 对话记录 → sessionStorage["cb_log"]（[{cls,text}] 数组，切页回来逐条重放）
 *   - 展开状态 → sessionStorage["cb_open"]（切页回来自动还原展开/收起）
 *   - 拖动位置 → localStorage["cb_pos"]（像素坐标，关浏览器下次打开仍在原位）
 * 拖动交互：按住 AI 球即拖（位移 >5px 判定拖动并持久化；≤5px 视为点击开关面板）。
 * 面板展开时锚定 AI 球上方并自动防屏幕溢出——拖到哪，对话就在哪顺利打开。
 * 铁律不变：报告数字全部来自 /api/chat 的工具轨迹 j.steps，组件只渲染不心算。
 * 扩展点（def 18/20 完整版）：j.action = {type:"navigate"|"fill", ...} → doAction() 通道已预留。
 */
(function () {
  if (window.__cb_chatbox) return;          // 防重复注入
  window.__cb_chatbox = true;

  /* ---- 样式自注入：与 style.css 同一套设计锚点（零圆角/毛玻璃/--ac 品牌色） ---- */
  const css = `
  #cb-fab{position:fixed;right:22px;bottom:22px;width:52px;height:52px;border:none;cursor:grab;z-index:999;
    background:linear-gradient(145deg,rgba(229,71,109,.92),rgba(229,71,109,.75));color:#fff;font-size:13px;letter-spacing:1px;
    border:1px solid rgba(255,255,255,.25);box-shadow:0 10px 30px rgba(229,71,109,.35);backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);
    user-select:none;-webkit-user-select:none;touch-action:none}
  #cb-fab:active{cursor:grabbing}
  #cb-panel{position:fixed;right:22px;bottom:84px;width:340px;max-width:calc(100vw - 44px);height:440px;max-height:calc(100vh - 120px);
    display:none;flex-direction:column;z-index:999;background:rgba(24,18,32,.92);border:1px solid var(--bd);
    backdrop-filter:blur(20px) saturate(150%);-webkit-backdrop-filter:blur(20px) saturate(150%);box-shadow:0 18px 50px rgba(0,0,0,.5)}
  #cb-panel.open{display:flex}
  #cb-head{padding:10px 14px;border-bottom:1px solid var(--bd);font-size:13px;color:var(--ac2);letter-spacing:1px;
    display:flex;justify-content:space-between;align-items:center}
  #cb-head b{font-weight:600}
  #cb-close{cursor:pointer;color:var(--tx2);border:none;background:none;font-size:16px;padding:0 2px}
  #cb-log{flex:1;overflow-y:auto;padding:12px 14px;font-size:13.5px;color:var(--tx)}
  #cb-log .cb-u{color:var(--ac2);margin:6px 0}
  #cb-log .cb-a{margin:6px 0;white-space:pre-wrap;line-height:1.55}
  #cb-log .cb-meta{margin:5px 0;font-size:11.5px;color:var(--tx2)}
  #cb-log .cb-err{color:#ff8a80;font-size:12.5px;margin:6px 0}
  #cb-inrow{display:flex;gap:6px;padding:10px;border-top:1px solid var(--bd)}
  #cb-in{flex:1}
  #cb-send{padding:7px 14px}
  `;
  const st = document.createElement("style");
  st.textContent = css;
  document.head.appendChild(st);

  /* ---- DOM 骨架：fab 按钮 + 面板（头部/消息区/输入行） ---- */
  const wrap = document.createElement("div");
  wrap.innerHTML = `
  <button id="cb-fab" title="伴随 AI · 点击对话 / 按住拖动">AI</button>
  <div id="cb-panel">
    <div id="cb-head"><b>伴随 AI · 数字由代码计算</b><button id="cb-close" title="收起">×</button></div>
    <div id="cb-log"></div>
    <div id="cb-inrow">
      <input id="cb-in" placeholder="例如：黄黑皮适合什么口红？">
      <button id="cb-send">发送</button>
    </div>
  </div>`;
  document.body.appendChild(wrap);

  /* ==== 下半部：消息持久化 / 位置与拖动 / 对话逻辑 ==== */
  const $ = (id) => document.getElementById(id);
  const fab = $("cb-fab"), panel = $("cb-panel"), logEl = $("cb-log");

  const SS_LOG = "cb_log", SS_OPEN = "cb_open", LS_POS = "cb_pos";

  /* ---- 消息：渲染 + 持久化（thinking 等临时行不存） ---- */
  const history = (() => { try { return JSON.parse(sessionStorage.getItem(SS_LOG) || "[]"); } catch (e) { return []; } })();
  function saveLog() { try { sessionStorage.setItem(SS_LOG, JSON.stringify(history.slice(-80))); } catch (e) {} }
  function addMsg(cls, text, keep = true) {
    const d = document.createElement("div");
    d.className = "cb-" + cls;
    d.textContent = text;
    logEl.appendChild(d);
    logEl.scrollTop = logEl.scrollHeight;
    if (keep) { history.push({ cls, text }); saveLog(); }
    return d;
  }
  // 启动重放历史（切页回来对话不丢）
  if (history.length) {
    history.forEach((m) => {
      const d = document.createElement("div");
      d.className = "cb-" + m.cls;
      d.textContent = m.text;
      logEl.appendChild(d);
    });
    logEl.scrollTop = logEl.scrollHeight;
  } else {
    addMsg("meta", "我可以调用色号检索 / 全库 26 万色板 / 配色知识库为你分析，过程可见。", false);
  }

  /* ---- 位置：恢复 / 面板锚定 AI 球 / 拖动 ---- */
  function applySavedPos() {
    try {
      const p = JSON.parse(localStorage.getItem(LS_POS) || "null");
      if (p && Number.isFinite(p.x) && Number.isFinite(p.y)) {
        fab.style.left = p.x + "px"; fab.style.top = p.y + "px";
        fab.style.right = "auto"; fab.style.bottom = "auto";
      }
    } catch (e) {}
  }
  function clamp(x, y, w, h) {
    return [Math.min(Math.max(4, x), window.innerWidth - w - 4),
            Math.min(Math.max(4, y), window.innerHeight - h - 4)];
  }
  function placePanel() {                       // 面板锚定 fab 上方，防溢出
    const fr = fab.getBoundingClientRect();
    const pw = panel.offsetWidth || 340, ph = panel.offsetHeight || 440;
    let left = fr.left + fr.width - pw;         // 右对齐 fab
    let top = fr.top - ph - 10;                 // fab 上方
    if (top < 8) top = fr.bottom + 10;          // 放不下则改 fab 下方
    [left, top] = clamp(left, top, pw, ph);
    panel.style.left = left + "px"; panel.style.top = top + "px";
    panel.style.right = "auto"; panel.style.bottom = "auto";
  }
  applySavedPos();

  let moved = false;
  fab.addEventListener("pointerdown", (e) => {
    moved = false;
    const sx = e.clientX, sy = e.clientY;
    const fr = fab.getBoundingClientRect();
    const dx = e.clientX - fr.left, dy = e.clientY - fr.top;
    const onMove = (ev) => {
      if (Math.hypot(ev.clientX - sx, ev.clientY - sy) > 5) moved = true;
      if (!moved) return;                       // 位移小于 5px 不算拖动（留给点击）
      const [x, y] = clamp(ev.clientX - dx, ev.clientY - dy, fr.width, fr.height);
      fab.style.left = x + "px"; fab.style.top = y + "px";
      fab.style.right = "auto"; fab.style.bottom = "auto";
      if (panel.classList.contains("open")) placePanel();   // 展开时面板实时跟随
    };
    const onUp = () => {
      document.removeEventListener("pointermove", onMove);
      document.removeEventListener("pointerup", onUp);
      if (moved) {
        const r = fab.getBoundingClientRect();
        try { localStorage.setItem(LS_POS, JSON.stringify({ x: r.left, y: r.top })); } catch (e) {}
      }
    };
    document.addEventListener("pointermove", onMove);
    document.addEventListener("pointerup", onUp);
    e.preventDefault();
  });
  fab.addEventListener("click", () => {         // 拖动结束的松手不触发开关
    if (moved) { moved = false; return; }
    toggle();
  });

  /* ==== 续写锚点 B ==== */
  function toggle(open) {
    const willOpen = (open === undefined) ? !panel.classList.contains("open") : open;
    if (willOpen) placePanel();
    panel.classList.toggle("open", willOpen);
    try { sessionStorage.setItem(SS_OPEN, willOpen ? "1" : "0"); } catch (e) {}
    if (willOpen) $("cb-in").focus();
  }
  $("cb-close").addEventListener("click", () => toggle(false));
  window.addEventListener("resize", () => {     // 窗口变化时把 fab/panel 拉回屏幕内
    const fr = fab.getBoundingClientRect();
    const [x, y] = clamp(fr.left, fr.top, fr.width, fr.height);
    fab.style.left = x + "px"; fab.style.top = y + "px";
    fab.style.right = "auto"; fab.style.bottom = "auto";
    if (panel.classList.contains("open")) placePanel();
  });

  /* ---- def 20 完整版通道（预留）：后端下发的自主调度动作 ---- */
  function doAction(a) {
    if (!a || !a.type) return;
    if (a.type === "navigate" && a.page) {          // 自动跳转子页（切页后对话经 sessionStorage 续上）
      addMsg("meta", `[调度] 正在前往 ${a.page}${a.reason ? " · " + a.reason : ""}`);
      setTimeout(() => { location.href = a.page; }, 600);
    } else if (a.type === "fill" && a.page && a.values) {   // def 18：跨页转交表单值
      try { sessionStorage.setItem("cb_pending_fill", JSON.stringify(a)); } catch (e) {}
      addMsg("meta", `[调度] 表单已备好，正在前往 ${a.page}…（确认权在你）`);
      setTimeout(() => { location.href = a.page; }, 600);
    }
  }

  async function send() {
    const m = $("cb-in").value.trim();
    if (!m || $("cb-in").dataset.busy === "1") return;
    addMsg("u", m);
    const th = addMsg("meta", "大脑思考中…（推理型模型约 10~40s）", false);
    th.classList.add("cb-thinking");
    $("cb-in").value = "";
    $("cb-in").dataset.busy = "1";
    try {
      const r = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: m }),
      });
      const j = await r.json();
      document.querySelectorAll(".cb-thinking").forEach((e) => e.remove());
      (j.steps || []).forEach((s) =>
        addMsg("meta", `[工具] ${s.tool}(${JSON.stringify(s.args)}) ${s.ok ? "[OK]" : "[错误]"}`));
      if (j.action) doAction(j.action);             // 骨架期后端不返回 action，通道静默待命
      if (j.error) addMsg("err", `[错误] ${j.error}`);
      else addMsg("a", j.content ?? "");
    } catch (e) {
      document.querySelectorAll(".cb-thinking").forEach((el) => el.remove());
      addMsg("err", `[错误] 请求失败: ${e}`);
    }
    $("cb-in").dataset.busy = "0";
    logEl.scrollTop = logEl.scrollHeight;
  }

  $("cb-send").addEventListener("click", send);
  $("cb-in").addEventListener("keydown", (e) => { if (e.key === "Enter") send(); });

  // 初始化：切页回来时还原展开状态（对话与面板位置一并还原）
  if (sessionStorage.getItem(SS_OPEN) === "1") toggle(true);
})();

