/* def 20 骨架 v1 · 伴随 AI 悬浮窗（R-05：不设独立 chat 子页，悬浮窗内嵌大脑）
 * 用法：任何子页 <script src="chatbox.js"></script> 引入即生效，零配置零 CSS 依赖
 *      （样式由本组件自注入，子页只引 style.css 管页面布局）。
 * 铁律：AI 报告的所有数字均来自 /api/chat 返回的工具轨迹 j.steps，本组件只渲染不心算。
 * 扩展点（def 18/20 完整版）：j.action = {type:"navigate"|"fill", ...} —— 后端大脑
 *      未来可下发"自动跳转子页 / 自动填充表单"指令，本组件已预留 doAction() 通道；
 *      fill 的表单值经 sessionStorage 跨页转交，最终提交权始终在用户（R-05 原则）。
 */
(function () {
  if (window.__cb_chatbox) return;          // 防重复注入
  window.__cb_chatbox = true;

  /* ---- 样式自注入：与 style.css 同一套设计锚点（零圆角/毛玻璃/--ac 品牌色） ---- */
  const css = `
  #cb-fab{position:fixed;right:22px;bottom:22px;width:52px;height:52px;border:none;cursor:pointer;z-index:999;
    background:linear-gradient(145deg,rgba(229,71,109,.92),rgba(229,71,109,.75));color:#fff;font-size:13px;letter-spacing:1px;
    border:1px solid rgba(255,255,255,.25);box-shadow:0 10px 30px rgba(229,71,109,.35);backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px)}
  #cb-fab:hover{background:rgba(229,71,109,1)}
  #cb-panel{position:fixed;right:22px;bottom:84px;width:340px;max-width:calc(100vw - 44px);height:440px;max-height:calc(100vh - 120px);
    display:none;flex-direction:column;z-index:999;background:rgba(24,18,32,.92);border:1px solid var(--bd,var(--bd));
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
  <button id="cb-fab" title="ColorBoundless AI 陪伴">AI</button>
  <div id="cb-panel">
    <div id="cb-head"><b>伴随 AI · 数字由代码计算</b><button id="cb-close" title="收起">×</button></div>
    <div id="cb-log"><div class="cb-meta">我可以调用色号检索 / 全库 26 万色板 / 配色知识库为你分析，过程可见。</div></div>
    <div id="cb-inrow">
      <input id="cb-in" placeholder="例如：黄黑皮适合什么口红？">
      <button id="cb-send">发送</button>
    </div>
  </div>`;
  document.body.appendChild(wrap);

  const $ = (id) => document.getElementById(id);
  const logEl = () => $("cb-log");

  function addMsg(cls, text) {
    const d = document.createElement("div");
    d.className = "cb-" + cls;
    d.textContent = text;
    logEl().appendChild(d);
    logEl().scrollTop = logEl().scrollHeight;
    return d;
  }

  function toggle(open) {
    const p = $("cb-panel");
    p.classList.toggle("open", open === undefined ? !p.classList.contains("open") : open);
    if (p.classList.contains("open")) $("cb-in").focus();
  }

  /* ---- def 20 完整版通道（骨架预留）：后端下发的自主调度动作 ---- */
  function doAction(a) {
    if (!a || !a.type) return;
    if (a.type === "navigate" && a.page) {          // 自动跳转子页
      addMsg("meta", `[调度] 正在前往 ${a.page}${a.reason ? " · " + a.reason : ""}`);
      setTimeout(() => { location.href = a.page; }, 600);
    } else if (a.type === "fill" && a.page && a.values) {   // def 18：跨页转交表单值
      sessionStorage.setItem("cb_pending_fill", JSON.stringify(a));
      addMsg("meta", `[调度] 表单已备好，正在前往 ${a.page}…（确认权在你）`);
      setTimeout(() => { location.href = a.page; }, 600);
    }
  }

  async function send() {
    const m = $("cb-in").value.trim();
    if (!m || $("cb-in").dataset.busy === "1") return;
    addMsg("u", m);
    const th = addMsg("meta", "大脑思考中…（推理型模型约 10~40s）");
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
    logEl().scrollTop = logEl().scrollHeight;
  }

  $("cb-fab").addEventListener("click", () => toggle());
  $("cb-close").addEventListener("click", () => toggle(false));
  $("cb-send").addEventListener("click", send);
  $("cb-in").addEventListener("keydown", (e) => { if (e.key === "Enter") send(); });
})();
