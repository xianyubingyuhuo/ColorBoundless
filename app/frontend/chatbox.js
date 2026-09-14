/* def 22 · 伴随 AI 悬浮窗 v3——界面重构版（用户 2026-09-14 定稿）
 * 新增/变更：
 *   ① 用户消息右对齐圆角气泡（带边框透明底，本区域允许圆角）
 *   ② 输入区统一：语音圆标(SVG麦克风) + 输入框 + 纸飞机发送(SVG)，思考中锁定输入防串台
 *   ③ 超时可重发（90s AbortController）+ 思考中"发送"变"停止"（暂停输出）
 *   ④ 左侧对话选择栏：最多 5 个会话，新建自动顶替最早（sessionStorage 持久，刷新全清）
 *   ⑤ 语音修复：onerror 人话提示（Chrome 网络受限→建议 Edge）+ 识别超时阈值 10s
 * 保留：拖动 / 跨页对话 / 刷新清空 / TTS 朗读 / 位置持久 / CBChat 外部接口
 * 铁律不变：数字来自工具轨迹，组件只渲染不心算。
 */
(function () {
  if (window.__cb_chatbox) return;
  window.__cb_chatbox = true;

  try {

  const MAX_CONVS = 5, SEND_TIMEOUT = 90000, REC_TIMEOUT = 10000;

  const css = `
  #cb-fab{position:fixed;right:22px;bottom:22px;width:56px;height:56px;border:none;cursor:grab;z-index:999;
    border-radius:50%;padding:0;display:flex;align-items:center;justify-content:center;
    background:linear-gradient(135deg,#ff9ab5 0%,#e5476d 45%,#7654ff 100%);
    box-shadow:0 10px 28px rgba(229,71,109,.35);user-select:none;-webkit-user-select:none;touch-action:none;
    transition:transform .45s cubic-bezier(.22,1,.36,1), box-shadow .45s ease}
  #cb-fab::after{content:"";position:absolute;inset:5px;border-radius:50%;
    background:radial-gradient(circle at 35% 30%,#2b2138 0%,#1e1424 60%,#150f1d 100%)}
  #cb-fab span{position:relative;z-index:1;font-size:14px;font-weight:600;color:#fff;letter-spacing:.5px}
  #cb-fab:hover{transform:scale(1.09);box-shadow:0 12px 34px rgba(229,71,109,.5), 0 0 22px rgba(255,154,181,.4)}
  #cb-fab:active{cursor:grabbing;transform:scale(1)}
  #cb-panel{position:fixed;right:22px;bottom:84px;width:430px;max-width:calc(100vw - 44px);height:460px;max-height:calc(100vh - 120px);
    resize:both;min-width:300px;min-height:380px;overflow:hidden;
    display:flex;flex-direction:column;z-index:999;background:rgba(24,18,32,.92);border:1px solid var(--bd);
    backdrop-filter:blur(20px) saturate(150%);-webkit-backdrop-filter:blur(20px) saturate(150%);box-shadow:0 18px 50px rgba(0,0,0,.5);
    opacity:0;visibility:hidden;transform:translateY(18px) scale(.97);
    transition:opacity .38s ease, transform .45s cubic-bezier(.22,1,.36,1), visibility .38s}
  #cb-panel.open{opacity:1;visibility:visible;transform:none}
  @keyframes cbPop{0%{transform:scale(1)}35%{transform:scale(1.22)}70%{transform:scale(.94)}100%{transform:scale(1)}}
  #cb-fab.cb-pop{animation:cbPop .9s cubic-bezier(.22,1,.36,1)}
  #cb-head{padding:10px 12px;border-bottom:1px solid var(--bd);font-size:13px;color:var(--ac2);letter-spacing:1px;
    display:flex;justify-content:space-between;align-items:center}
  #cb-head b{font-weight:600}
  #cb-tts{padding:4px 8px;font-size:11px;background:rgba(255,255,255,.06);color:var(--tx2);border:1px solid var(--bd);cursor:pointer}
  #cb-tts.on{color:var(--ac2);border-color:rgba(229,71,109,.5)}
  #cb-close{cursor:pointer;color:var(--tx2);border:none;background:none;font-size:16px;padding:0 2px}
  #cb-body{flex:1;display:flex;min-height:0}
  /* 左侧对话选择栏（最多 5 会话） */
  #cb-side{width:76px;border-right:1px solid var(--bd);display:flex;flex-direction:column;padding:8px 6px;gap:6px;overflow-y:auto}
  #cb-newconv{width:100%;padding:6px 0;font-size:12px;background:rgba(229,71,109,.25);border:1px solid rgba(229,71,109,.5);color:var(--tx);cursor:pointer}
  #cb-newconv:hover{background:rgba(229,71,109,.45)}
  .cb-conv{display:flex;align-items:center;gap:4px;width:100%;padding:6px 8px;font-size:11.5px;color:var(--tx2);background:rgba(255,255,255,.04);
    border:1px solid transparent;cursor:pointer;line-height:1.4;text-align:left}
  .cb-conv > span:first-child{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .cb-conv:hover{color:var(--tx);border-color:var(--bd)}
  .cb-conv.on{color:var(--ac2);border-color:rgba(229,71,109,.6);background:rgba(229,71,109,.08)}
  .cb-del{flex:none;width:18px;height:18px;line-height:16px;text-align:center;border-radius:5px;color:var(--tx2);opacity:.55;font-size:14px}
  .cb-del:hover{opacity:1;color:#ff8a80;background:rgba(255,138,128,.12)}
  /* 聊天区 */
  #cb-main{flex:1;display:flex;flex-direction:column;min-width:0}
  #cb-log{flex:1;overflow-y:auto;padding:12px;font-size:13.5px;color:var(--tx)}
  #cb-log .cb-uwrap{display:flex;justify-content:flex-end;margin:8px 0}
  #cb-log .cb-u{max-width:80%;background:rgba(229,71,109,.13);border:1px solid rgba(255,154,181,.45);
    border-radius:14px 14px 3px 14px;padding:8px 12px;color:var(--tx);line-height:1.5;word-break:break-word}
  #cb-log .cb-a{margin:8px 0;white-space:pre-wrap;line-height:1.55;max-width:92%;
    background:rgba(255,255,255,.05);border:1px solid var(--bd);border-radius:3px 14px 14px 14px;padding:8px 12px}
  #cb-log .cb-meta{margin:6px 0;font-size:11.5px;color:var(--tx2)}
  #cb-log .cb-err{color:#ff8a80;font-size:12.5px;margin:6px 0}
  #cb-inrow{display:flex;gap:0;margin:10px;padding:4px 6px;border:1px solid var(--bd);border-radius:12px;background:rgba(255,255,255,.04);align-items:center}
  #cb-inrow.locked{opacity:.55}
  .cb-sep{width:1px;height:20px;background:var(--bd);flex:none;margin:0 5px}
  #cb-mic,#cb-send{border:none;width:34px;height:32px;padding:0;display:flex;align-items:center;justify-content:center;flex:none;border-radius:9px}
  #cb-mic svg,#cb-send svg{width:17px;height:17px;stroke:currentColor;fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
  #cb-mic{background:rgba(255,255,255,.08)}
  #cb-mic.cb-rec{background:rgba(229,71,109,1);color:#fff}
  #cb-send{background:rgba(229,71,109,.82)}
  #cb-send:hover{background:rgba(229,71,109,1)}
  #cb-send.stop{background:rgba(118,84,255,.85)}
  #cb-in{flex:1;min-width:0;background:transparent;border:none;box-shadow:none}
  #cb-in:disabled{opacity:.6}
  `;
  const st = document.createElement("style");
  st.textContent = css;
  document.head.appendChild(st);

  /* ==== DOM：fab + 面板（左对话栏 / 聊天区 / 统一输入行） ==== */
  const MIC_SVG = '<svg viewBox="0 0 24 24"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/></svg>';
  const SEND_SVG = '<svg viewBox="0 0 24 24"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>';
  const STOP_SVG = '<svg viewBox="0 0 24 24"><rect x="6" y="6" width="12" height="12"/></svg>';

  const wrap = document.createElement("div");
  wrap.innerHTML = `
  <button id="cb-fab" title="伴随 AI · 点击对话 / 按住拖动"><span>AI</span></button>
  <div id="cb-panel">
    <div id="cb-head"><b>伴随 AI · 数字由代码计算</b>` +
      `<span style="display:flex;align-items:center;gap:6px">` +
      `<button id="cb-tts" style="display:none" title="朗读 AI 回复（无障碍）">朗读:关</button>` +
      `<button id="cb-close" title="收起">×</button></span></div>
    <div id="cb-body">
      <div id="cb-side">
        <button id="cb-newconv" title="新建对话（最多 5 个，超出顶替最早）">＋ 新对话</button>
        <div id="cb-convlist" style="display:flex;flex-direction:column;gap:6px"></div>
      </div>
      <div id="cb-main">
        <div id="cb-log"></div>
        <div id="cb-inrow">
          <button id="cb-mic" style="display:none" title="点击说话（识别后自动发送）">${MIC_SVG}</button>
          <span class="cb-sep" id="cb-sep1" style="display:none"></span>
          <input id="cb-in" placeholder="例如：黄黑皮适合什么口红？">
          <span class="cb-sep"></span>
          <button id="cb-send" title="发送（思考中变为停止）">${SEND_SVG}</button>
        </div>
      </div>
    </div>
  </div>`;
  document.body.appendChild(wrap);

  /* ==== 状态：多会话（≤5，新建顶替最早）/ 刷新全清 / 位置持久 ==== */
  const SS_CONVS = "cb_convs", SS_CUR = "cb_cur", SS_OPEN = "cb_open", LS_POS = "cb_pos";
  const $ = (id) => document.getElementById(id);
  const fab = $("cb-fab"), panel = $("cb-panel"), logEl = $("cb-log"),
        input = $("cb-in"), sendBtn = $("cb-send"), micBtn = $("cb-mic");

  let convs = [];          // [{id, title, msgs:[{cls,text}]}]，≤5
  let curId = null;        // 当前会话 id
  function loadConvs(){
    try { convs = JSON.parse(sessionStorage.getItem(SS_CONVS) || "[]"); } catch(e){ convs = []; }
  }
  function saveConvs(){ try { sessionStorage.setItem(SS_CONVS, JSON.stringify(convs)); } catch(e){} }
  function curConv(){ return convs.find(c => c.id === curId); }

  function renderConvList(){
    const box = $("cb-convlist"); box.innerHTML = "";
    convs.forEach(c => {
      const d = document.createElement("div");
      d.className = "cb-conv" + (c.id === curId ? " on" : "");
      d.title = c.title || "";
      const t = document.createElement("span");
      t.textContent = c.title || "新对话";
      const x = document.createElement("span");
      x.className = "cb-del"; x.textContent = "×"; x.title = "删除此对话";
      x.onclick = (ev) => { ev.stopPropagation(); delConv(c.id); };
      d.appendChild(t); d.appendChild(x);
      d.onclick = () => { if (busy) return; switchConv(c.id); };
      box.appendChild(d);
    });
  }
  function delConv(id){
    if (busy) return;
    const i = convs.findIndex(c => c.id === id);
    if (i < 0) return;
    convs.splice(i, 1);
    if (!convs.length) convs.push({ id: Date.now().toString(36), title: "新对话", msgs: [] });
    if (curId === id || !curConv()){
      curId = convs[convs.length - 1].id;
      logEl.innerHTML = "";
      (curConv().msgs || []).forEach(m => addMsg(m.cls, m.text, false));
      sessionStorage.setItem(SS_CUR, curId);
    }
    saveConvs(); renderConvList();
  }
  function switchConv(id){
    curId = id;
    sessionStorage.setItem(SS_CUR, id);
    const c = curConv();
    logEl.innerHTML = "";
    (c ? c.msgs : []).forEach(m => addMsg(m.cls, m.text, false));
    renderConvList();
  }
  function newConv(){
    if (busy) return;
    if (convs.length >= MAX_CONVS) convs.shift();          // 顶替最早
    const c = { id: Date.now().toString(36), title: "新对话", msgs: [] };
    convs.push(c); curId = c.id;
    saveConvs(); sessionStorage.setItem(SS_CUR, curId);
    logEl.innerHTML = "";
    addMsg("meta", "我可以调用色号检索 / 全库 26 万色板 / 配色知识库为你分析，过程可见。", false);
    renderConvList();
  }
  $("cb-newconv").onclick = newConv;

  function addMsg(cls, text, keep = true){
    const d = document.createElement("div");
    if (cls === "u"){                                       // 用户消息 → 右对齐圆角气泡
      const w = document.createElement("div"); w.className = "cb-uwrap";
      const b = document.createElement("div"); b.className = "cb-u"; b.textContent = text;
      w.appendChild(b); logEl.appendChild(w);
    } else {
      const d2 = document.createElement("div");
      d2.className = "cb-" + cls; d2.textContent = text;
      logEl.appendChild(d2);
    }
    logEl.scrollTop = logEl.scrollHeight;
    if (keep){
      const c = curConv();
      if (c){ c.msgs.push({cls, text}); saveConvs();
              if (c.msgs.length === 1 && cls === "u"){ c.title = text.slice(0, 14); renderConvList(); } }
    }
    return null;
  }

  /* 启动：刷新（reload）→ 全部对话清空（用户规则）；切页跳转 → 保留恢复 */
  let navType = "navigate";
  try { navType = (performance.getEntriesByType("navigation")[0] || {}).type || "navigate"; } catch(e){}
  loadConvs();
  if (navType === "reload"){
    convs = []; curId = null;
    try { sessionStorage.removeItem(SS_CONVS); sessionStorage.removeItem(SS_CUR); sessionStorage.setItem(SS_OPEN, "0"); } catch(e){}
  }
  if (convs.length){
    curId = sessionStorage.getItem(SS_CUR) && convs.find(c => c.id === sessionStorage.getItem(SS_CUR))
            ? sessionStorage.getItem(SS_CUR) : convs[convs.length - 1].id;
    switchConv(curId);
  } else {
    curId = null;
    addMsg("meta", "我可以调用色号检索 / 全库 26 万色板 / 配色知识库为你分析，过程可见。", false);
    renderConvList();
  }

  /* ==== 拖动（保留）+ 面板锚定 ==== */
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
  function placePanel() {
    const fr = fab.getBoundingClientRect();
    const pw = panel.offsetWidth || 430, ph = panel.offsetHeight || 460;
    let left = fr.left + fr.width - pw;
    let top = fr.top - ph - 10;
    if (top < 8) top = fr.bottom + 10;
    [left, top] = clamp(left, top, pw, ph);
    panel.style.left = left + "px"; panel.style.top = top + "px";
    panel.style.right = "auto"; panel.style.bottom = "auto";
  }
  applySavedPos();

  /* def 22 · 面板大小用户可调（右下角手柄拖拽）+ 尺寸持久化，刷新后保持 */
  const LS_SIZE = "cb_panel_size";
  try {
    const s = JSON.parse(localStorage.getItem(LS_SIZE) || "null");
    if (s && s.w && s.h) { panel.style.width = s.w + "px"; panel.style.height = s.h + "px"; }
  } catch (e) {}
  if (window.ResizeObserver) {
    new ResizeObserver(() => {
      try { localStorage.setItem(LS_SIZE, JSON.stringify({ w: Math.round(panel.offsetWidth), h: Math.round(panel.offsetHeight) })); } catch (e) {}
    }).observe(panel);
  }

  let moved = false;
  fab.addEventListener("pointerdown", (e) => {
    moved = false;
    const sx = e.clientX, sy = e.clientY;
    const fr = fab.getBoundingClientRect();
    const dx = e.clientX - fr.left, dy = e.clientY - fr.top;
    const onMove = (ev) => {
      if (Math.hypot(ev.clientX - sx, ev.clientY - sy) > 5) moved = true;
      if (!moved) return;
      const [x, y] = clamp(ev.clientX - dx, ev.clientY - dy, fr.width, fr.height);
      fab.style.left = x + "px"; fab.style.top = y + "px";
      fab.style.right = "auto"; fab.style.bottom = "auto";
      if (panel.classList.contains("open")) placePanel();
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
  });
  /* 开关放 pointerup（不依赖 click——规避 pointerdown preventDefault 在部分浏览器的 click 抑制） */
  fab.addEventListener("pointerup", (e) => {
    if (moved) { moved = false; return; }
    toggle();
  });

  function toggle(open) {
    const willOpen = (open === undefined) ? !panel.classList.contains("open") : open;
    if (willOpen) placePanel();
    panel.classList.toggle("open", willOpen);
    try { sessionStorage.setItem(SS_OPEN, willOpen ? "1" : "0"); } catch (e) {}
    if (willOpen) input.focus();
  }
  $("cb-close").addEventListener("click", () => toggle(false));
  window.addEventListener("resize", () => {
    const fr = fab.getBoundingClientRect();
    const [x, y] = clamp(fr.left, fr.top, fr.width, fr.height);
    fab.style.left = x + "px"; fab.style.top = y + "px";
    fab.style.right = "auto"; fab.style.bottom = "auto";
    if (panel.classList.contains("open")) placePanel();
  });

  /* ==== def 20 · 外部调用接口（cvd 页旅程自动化用） ==== */
  window.CBChat = {
    open: () => { toggle(true); fab.classList.add("cb-pop"); setTimeout(() => fab.classList.remove("cb-pop"), 900); },
    close: () => toggle(false),
    send: async (text) => { toggle(true); return sendMessage(text); },
  };

  /* ==== 消息发送：AbortController 超时/停止 + 思考中锁定输入（防串台）+ TTS ==== */
  let busy = false;
  let aborter = null;
  function setBusy(v){
    busy = v;
    $("cb-inrow").classList.toggle("locked", v);
    input.disabled = v;
    sendBtn.classList.toggle("stop", v);
    sendBtn.innerHTML = v ? STOP_SVG : SEND_SVG;
    sendBtn.title = v ? "停止本次回答" : "发送";
  }
  function speak(text){
    if (!ttsOn() || !("speechSynthesis" in window) || !text) return;
    speechSynthesis.cancel();
    const clean = String(text).replace(/[#*`>]/g, "");
    const u = new SpeechSynthesisUtterance(clean);
    u.lang = "zh-CN"; u.rate = 1;
    speechSynthesis.speak(u);
  }
  async function sendMessage(text){
    const m = (text === undefined ? input.value : String(text)).trim();
    if (!m) return;
    if (busy){                                     // 思考中点击发送按钮 = 停止
      if (aborter) aborter.abort();
      return;
    }
    addMsg("u", m);
    input.value = "";
    setBusy(true);
    const th = addMsg("meta", "大脑思考中…（约 10~40s，可点右侧按钮停止）", false);
    aborter = new AbortController();
    const timer = setTimeout(() => aborter && aborter.abort(), SEND_TIMEOUT);
    let j = null;
    try{
      const r = await fetch("/api/chat", {method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({message: m}), signal: aborter.signal});
      j = await r.json();
      clearTimeout(timer);
      document.querySelectorAll(".cb-thinking").forEach((e) => e.remove());
      (j.steps || []).forEach((s) =>
        addMsg("meta", `[工具] ${s.tool}(${JSON.stringify(s.args)}) ${s.ok ? "[OK]" : "[错误]"}`));
      if (j.action && window.CVDThemeNav) window.CVDThemeNav(j.action);
      if (j.action && typeof window.__cbAction === "function") window.__cbAction(j.action);
      if (j.error) addMsg("err", `[错误] ${j.error}`);
      else addMsg("a", j.content ?? "");
      if (!j.error && j.content) speak(j.content);
    } catch(e){
      clearTimeout(timer);
      document.querySelectorAll(".cb-thinking").forEach((el) => el.remove());
      addMsg("err", e.name === "AbortError" ? "已超过 90 秒未响应——本次已中断，可重新发送" : `[错误] 请求失败: ${e}`);
    }
    setBusy(false);
    logEl.scrollTop = logEl.scrollHeight;
    return j;
  }

  sendBtn.addEventListener("click", () => { if (busy){ if (aborter) aborter.abort(); } else sendMessage(); });
  input.addEventListener("keydown", (e) => { if (e.key === "Enter" && !busy) sendMessage(); });

  /* ==== def 21 · TTS 开关 + 语音识别 + 导航 action ==== */
  const ttsOn = () => localStorage.getItem("cb_tts") === "1";
  if ("speechSynthesis" in window){
    const tb = $("cb-tts");
    tb.style.display = "";
    const syncT = () => { tb.textContent = ttsOn() ? "朗读:开" : "朗读:关"; tb.classList.toggle("on", ttsOn()); };
    syncT();
    tb.onclick = () => { localStorage.setItem("cb_tts", ttsOn() ? "0" : "1"); syncT(); if (!ttsOn()) speechSynthesis.cancel(); };
  }
  window.__cbAction = (a) => {
    if (!a || !a.type) return;
    if (a.type === "navigate" && a.page){
      addMsg("meta", `[调度] 正在前往 ${a.page}${a.reason ? " · " + a.reason : ""}`);
      setTimeout(() => { location.href = a.page; }, 600);
    }
  };
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SR){
    micBtn.style.display = "";
    const sep1 = $("cb-sep1"); if (sep1) sep1.style.display = "";
    const rec = new SR();
    rec.lang = "zh-CN"; rec.interimResults = false; rec.maxAlternatives = 1;
    let listening = false, recTimer = null;
    const ERR = {
      network: "语音服务网络受限（Chrome 需访问 Google 服务）——建议改用 Edge 浏览器",
      "not-allowed": "麦克风权限被拒绝——请在地址栏左侧允许麦克风后重试",
      "audio-capture": "未检测到麦克风设备",
      aborted: null
    };
    rec.onresult = (e) => {
      clearTimeout(recTimer);
      const t = e.results[0][0].transcript.trim();
      micBtn.classList.remove("cb-rec");
      if (t) sendMessage(t);
    };
    rec.onerror = (e) => {
      clearTimeout(recTimer);
      micBtn.classList.remove("cb-rec");
      const msg = ERR[e.error] || ("识别错误: " + e.error);
      if (msg) addMsg("meta", "[语音] " + msg);
    };
    rec.onend = () => { micBtn.classList.remove("cb-rec"); };
    micBtn.onclick = () => {
      if (listening){ clearTimeout(recTimer); rec.stop(); return; }
      try {
        rec.start(); listening = true;
        micBtn.classList.add("cb-rec");
        recTimer = setTimeout(() => {          // 识别超时阈值 10s（用户要求）
          if (listening){ rec.stop(); addMsg("meta", "[语音] 识别超时自动停止——请靠近麦克风重试，或改用 Edge 浏览器"); }
        }, REC_TIMEOUT);
      } catch(e){}
    };
  } else {
    micBtn.style.display = "none";
  }
  } catch (initErr) {
    /* 初始化错误可见化：不用 F12 也能看到（截图发我即可定位） */
    document.body.insertAdjacentHTML("beforeend",
      '<div style="position:fixed;top:0;left:0;right:0;background:#b71c1c;color:#fff;padding:8px 12px;z-index:99999;font-size:12px;font-family:monospace">AI 组件初始化失败: ' + String(initErr && initErr.message || initErr) + '</div>');
  }
})();