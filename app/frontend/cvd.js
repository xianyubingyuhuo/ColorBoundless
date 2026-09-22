/* cvd 页逻辑（自 cvd.html 拆出，改交互只动这个小文件） */
const $ = id => document.getElementById(id);
async function getJSON(url){const t0=performance.now();const r=await fetch(url);const j=await r.json();return{j,ms:Math.round(performance.now()-t0)}}

/* ==== 选项卡切换 + 顶部校色开关 ==== */
function showTab(name){
  ["exam","profile","verify"].forEach(n => {
    $("panel-"+n).classList.toggle("on", n === name);
    $("tab-"+n).classList.toggle("on", n === name);
  });
}

let calBusy = false;
async function toggleCalSwitch(){
  if(calBusy) return;
  const sw = $("calswitch");
  if(sw.dataset.hasProfile !== "1"){
    /* def 51 · 无档案但全站已开（未测评临时口径：对称红绿增强）→ 在此允许关闭，
       否则 calswitch 开启后到本页会「关不掉」（session 标记仍在、配色继续生效） */
    if(window.CVDTheme && window.CVDTheme.getSession && window.CVDTheme.getSession()){
      window.CVDTheme.setSession(null);
      window.CVDTheme.reset();
      syncCalSwitch(false);
      $("calstatus").innerHTML = `<span class="ms">已关闭校色配色（此前为未测评临时口径：对称红绿增强）——完成 22 题测评后可获个性化校色</span>`;
      return;
    }
    $("calstatus").innerHTML = `<span class="err">暂无测评档案——请先在"色盲测评"完成 22 题</span>`;
    showTab("exam"); return;   /* 兜底保留：真无档案仍引导去测评，但仅在首次无档案时发生 */
  }
  const on = !sw.classList.contains("on");   /* def 34 · 开关 = 唯一启停：只切 enabled，导入的配置(mode)不动 */
  calBusy = true;
  /* def 41 · 会话标记本地先写（启停真相源），POST 仅同步档案存档；演示选中时开启 = 演示生效（def 37 口径） */
  if(window.CVDTheme && window.CVDTheme.setSession && !window.__cvd_url_sim){
    if(on){
      const demoBtn = document.querySelector("[data-sim].on");
      const c = window.__cvd_cal_cache;
      if(demoBtn) window.CVDTheme.setSession({mode:"simulate", kind:demoBtn.dataset.sim,
        sev:Math.min(1, Math.max(0, parseFloat($("cvdsev").value) || 1.0))});
      else if(c && c.mode && c.mode !== "off") window.CVDTheme.setSession({mode:c.mode, kind:c.kind, sev:c.severity});
    }else{
      window.CVDTheme.setSession(null);
    }
  }
  await doCalibrate(null, on);
  calBusy = false;
}
function syncCalSwitch(on){
  $("calswitch").classList.toggle("on", !!on);
}

/* ==== def 34/37 · 校色状态统一渲染（开关 = 唯一启停，按钮 = 只导入配置） ====
   def 37 · 全站配色统一出口 applyColorState()，优先级 = URL 演示锁 > 开关总控
   （关闭 → 全站立即恢复原色，演示/配置层暂停但状态保留，重开即恢复）> 演示态
   （[data-sim].on 按钮高亮即状态源）> 配置层（开关 on 且已导入）> 原色。
   用户 2026-09-21 三次反馈定稿口径：on 时启停不清演示色；off 时一切配色必须立刻停。 */
function applyColorState(){
  if(!window.CVDTheme || window.__cvd_url_sim) return {applied:false, reason:"url_sim"};
  if(!$("calswitch").classList.contains("on")){   /* def 37 · 开关总控：off = 全站立即恢复原色 */
    window.CVDTheme.reset();
    return {applied:false, reason:"off"};
  }
  /* def 41 · 会话标记优先：用户本会话点过的状态（模拟/校色）= 配色真相源，跨页/刷新一致 */
  const sess = window.CVDTheme.getSession ? window.CVDTheme.getSession() : null;
  if(sess && sess.mode && sess.kind) return window.CVDTheme.apply(sess.mode, sess.kind, sess.sev) || {applied:false};
  const demoBtn = document.querySelector("[data-sim].on");
  if(demoBtn){
    const sev = Math.min(1, Math.max(0, parseFloat($("cvdsev").value) || 1.0));
    return window.CVDTheme.apply("simulate", demoBtn.dataset.sim, sev) || {applied:false};
  }
  const cal = window.__cvd_cal_cache;
  if(cal && cal.mode && cal.mode !== "off"){   /* def 41 · 启停由开关 DOM 总控，档案 enabled 不再参与配色 */
    return window.CVDTheme.apply(cal.mode, cal.kind, cal.severity) || {applied:false};
  }
  window.CVDTheme.reset();
  return {applied:false, reason:"off"};
}
function renderCalState(cal){
  /* def 41 · 启停 = 会话标记（toggle/simAll 本地先写，POST 仅同步存档）；档案 enabled 不再驱动 UI/配色 */
  const sess = (window.CVDTheme && window.CVDTheme.getSession) ? window.CVDTheme.getSession() : null;
  const on = !!sess;
  syncCalSwitch(on);
  window.__cvd_cal_cache = cal || null;
  const demoBtn = document.querySelector("[data-sim].on");   /* def 37 · 演示选择独立于开关：off 时暂停但不丢 */
  const viaDemo = !!demoBtn;
  let themeApplied = false, themeReason = "";
  if(window.CVDTheme && !window.__cvd_url_sim){
    const res = applyColorState();
    themeApplied = !!(res && res.applied); themeReason = (res && res.reason) || "";
  }
  const modeCN = cal.mode === "correct" ? "校色模式" : (cal.mode === "simulate" ? "模拟模式" : "");
  const kindTxt = `${cal.kind} @ severity ${cal.severity}`;
  let html;
  if(!modeCN){
    html = `<span class="meta">尚未导入校色配置——在下方选「校色模式 / 模拟模式」导入；顶部开关只负责启用 / 停用</span>`;
  }else if(!on){
    html = `<span class="ms">已导入配置：${modeCN}（${kindTxt}）</span>` +
      `<div class="meta" style="margin-top:4px">导入 ≠ 开启——页面配色由顶部「校色配色」开关统一控制，打开开关即按此配置上色。</div>`;
  }else{
    html = `<span class="ms">已启用：${modeCN}（${kindTxt}）· 顶部开关可随时停用</span>`;
    if(!viaDemo && themeApplied && cal.kind === "uncertain"){
      html += `<div class="meta" style="margin-top:4px">档案类型是「未定型（uncertain）」——页面配色走<b>对称红绿增强</b>：不假定缺陷方向，把红绿色差双向拉开（亮度保持、黄色轴不动），红色盲/绿色盲用户都能受益且不会被补错方向。这是中性增强而非类型定向校色；重测出明确类型（deutan / protan / tritan）后校色会更精准。</div>`;
    }
    if(!viaDemo && !themeApplied && themeReason === "kind_unsupported"){
      html += `<div class="meta" style="margin-top:4px">但您的档案类型是「未定型（uncertain）」——校色引擎按保守口径<b>不做页面颜色补偿</b>：类型未定时补偿方向可能出错，宁可不动（诚实边界）。这不是故障：试妆与守门功能仍会正常使用档案数据。想看到全站校色的实际效果，需要测出明确的色觉类型（deutan / protan / tritan）——可点「重新测评」。</div>`;
    }
  }
  if(viaDemo){
    const dn = SIM_CN[demoBtn.dataset.sim] || demoBtn.dataset.sim;   /* def 37 · 演示说明分两态 */
    html += on
      ? `<div class="meta" style="margin-top:4px">页面配色当前为第三部分「全站模拟」演示（${dn}），正在生效——演示跨页保留（本会话内，刷新/切页不变），点「恢复原色」或关闭顶部开关即退出。</div>`
      : `<div class="meta" style="margin-top:4px">「${dn}」全站模拟演示仍处于选中状态，但顶部开关已关闭——全站配色暂停中（含演示），重新打开开关即恢复。</div>`;
  }
  if(window.__cvd_url_sim) html += `<div class="meta" style="margin-top:4px">页面配色当前由 URL 演示参数（?cvdsim=…）临时接管，优先于档案校色；刷新或去掉参数即恢复。</div>`;
  $("calstatus").innerHTML = html;
}

/* ==== 测评状态机（前端驱动出题展示，判定在后端规则引擎） ==== */
let examId = null;
const TYPE_CN = {deutan:"绿色盲（deutan）",protan:"红色盲（protan）",tritan:"蓝黄色盲（tritan）",
                 normal:"正常色觉",uncertain:"证据矛盾 · 待复核"};

async function startExam(){
  $("exam-intro").innerHTML = '<div class="meta">测评加载中…</div>';
  try{
    const r = await (await fetch("/api/cvd/exam/start",{method:"POST"})).json();
    if(!r.ok){ $("exam-intro").innerHTML = `<span class="err">[错误] ${r.error}</span>`; return; }
    examId = r.query.exam_id;
    $("exam-intro").style.display = "none";
    renderQ(r.results);
  }catch(e){ $("exam-intro").innerHTML = `<span class="err">[错误] 请求失败: ${e}</span>`; }
}

function renderQ(res){
  const area = $("exam-area");
  if(res.done){ renderProfile(res.profile, {justFinished: true}); return; }
  const q = res.question;
  const stageCN = {ishihara:"石原分型",grid:"网格找异色",hue:"色相排列",wave:"色彩波段定位"}[q.type] || q.type;
  let body = "";
  if(q.type === "ishihara"){
    body = `<img src="data:image/png;base64,${q.img_b64}" style="max-width:320px;border:1px solid var(--bd)">` +
      `<div class="row" style="margin-top:10px"><input id="ans" type="number" min="0" max="99" placeholder="看到的数字" style="width:130px">` +
      `<button onclick="submitAnswer(document.getElementById('ans').value)">提交</button>` +
      `<span class="meta">看不清就填 0</span></div>`;
  } else if(q.type === "grid"){
    body = `<div style="position:relative;display:inline-block;cursor:crosshair">` +
      `<img src="data:image/png;base64,${q.img_b64}" style="display:block;border:1px solid var(--bd)">` +
      `<div id="goverlay" style="position:absolute;inset:0;display:grid;grid-template-columns:repeat(${q.n},1fr);grid-template-rows:repeat(${q.n},1fr)"></div></div>` +
      `<div class="meta" style="margin-top:6px">点出异色块的位置</div>`;
  } else if(q.type === "hue"){
    body = `<div class="meta">把色块拖进下方槽位（也可以先点色块再点槽位），排成你觉得最平滑的渐变：</div>` +
      `<div id="huepool" class="row" style="min-height:70px;margin-top:6px;padding:6px;border:1px dashed var(--bd);flex-wrap:nowrap;overflow-x:auto"></div>` +
      `<div class="meta" style="margin:10px 0 4px">↓ 排列槽（从左到右 = 你认为的渐变顺序）</div>` +
      `<div id="hueslots" style="display:grid;grid-template-columns:repeat(15,minmax(0,1fr));gap:4px;margin-top:4px"></div>` +
      `<div class="row" style="margin-top:10px"><button id="huesubmit" onclick="submitHue()" disabled>提交排列</button>` +
      `<button onclick="resetHue()">清空重来</button><span class="meta" id="huecount"></span></div>`;
  } else if(q.type === "wave"){
    body = `<div class="row" style="margin-top:6px;align-items:center">` +
      `<span class="meta">目标色</span>` +
      `<span style="width:64px;height:44px;background:rgb(${q.target[0]},${q.target[1]},${q.target[2]});border:1px solid var(--bd);display:inline-block"></span>` +
      `<span class="meta" style="margin:0 12px">↔ 对比 ↔</span>` +
      `<span id="wavepreview" style="width:64px;height:44px;border:1px dashed var(--bd);display:inline-block"></span>` +
      `<span class="meta">你的选择</span></div>` +
      `<div id="wavebar" style="display:flex;height:56px;margin-top:12px;cursor:ew-resize;border:1px solid var(--bd);position:relative;touch-action:none"></div>` +
      `<div class="meta" id="wavemark" style="margin-top:8px">在波段条上按住拖动滑块，左边目标色 / 右边你的选择实时对比，觉得一致就提交（有容差）</div>` +
      `<div class="row" style="margin-top:8px"><button id="wavesubmit" onclick="submitWave()" disabled>提交</button></div>`;
  }
  area.innerHTML = `<div class="meta">${stageCN} · 第 ${res.question_no}/${res.question_total} 题</div>` +
    `<div style="height:6px;background:rgba(255,255,255,.08);margin:6px 0 12px">` +
    `<div style="height:100%;width:${Math.round((res.question_no-1)/res.question_total*100)}%;background:var(--ac)"></div></div>` + body;

  if(q.type === "grid"){
    const ov = $("goverlay");
    for(let r = 0; r < q.n; r++) for(let c = 0; c < q.n; c++){
      const cell = document.createElement("div");
      cell.style.cssText = "border:1px solid transparent";
      cell.onmouseenter = () => cell.style.borderColor = "rgb(from var(--ac) r g b / .5)";
      cell.onmouseleave = () => cell.style.borderColor = "transparent";
      cell.onclick = () => submitAnswer([r, c]);
      ov.appendChild(cell);
    }
  }
  if(q.type === "hue"){
    window.__hueColors = q.colors;
    window.__hueSlots = new Array(q.colors.length).fill(null);
    window.__hueSel = null; window.__hueDone = false;
    renderHueUI();
  }
  if(q.type === "wave"){
    window.__waveSel = null;
    const bar = $("wavebar");
    q.segments.forEach((rgb) => {
      const seg = document.createElement("div");
      seg.style.cssText = `flex:1;background:rgb(${rgb[0]},${rgb[1]},${rgb[2]})`;
      bar.appendChild(seg);
    });
    const setPos = (clientX) => {
      const rect = bar.getBoundingClientRect();
      const ratio = Math.min(0.999, Math.max(0.001, (clientX - rect.left) / rect.width));
      window.__waveSel = ratio;
      let mark = document.getElementById("wavemarkline");
      if(!mark){
        mark = document.createElement("div"); mark.id = "wavemarkline";
        mark.style.cssText = "position:absolute;top:-6px;bottom:-6px;width:5px;background:var(--tx);pointer-events:none;box-shadow:0 0 10px rgba(0,0,0,.7)";
        mark.innerHTML = `<div style="position:absolute;top:-16px;left:50%;transform:translateX(-50%);width:16px;height:16px;border-radius:50%;background:var(--tx);border:3px solid #181220"></div>`;
        bar.appendChild(mark);
      }
      mark.style.left = `calc(${(ratio * 100).toFixed(2)}% - 2.5px)`;
      const segIdx = Math.min(q.segments.length - 1, Math.floor(ratio * q.segments.length));
      const c = q.segments[segIdx];
      $("wavepreview").style.background = `rgb(${c[0]},${c[1]},${c[2]})`;
      $("wavepreview").style.borderStyle = "solid";
      $("wavemark").textContent =
        `实时对比中（当前 ${(ratio * 360).toFixed(0)}°）——来回拖动，直到右边与左边看起来一致再提交`;
      $("wavesubmit").disabled = false;
    };
    bar.onpointerdown = (e) => { bar.setPointerCapture(e.pointerId); setPos(e.clientX); };
    bar.onpointermove = (e) => { if(e.buttons) setPos(e.clientX); };
  }
}

/* ==== 拖拽排列（FM100 原型交互）与波段提交 ==== */
function hueChip(rgb, idx, pos, fluid){
  const b = document.createElement("button");
  b.style.cssText = (fluid ? "width:100%;height:100%;min-width:0;" : "width:44px;height:64px;") + `background:rgb(${rgb[0]},${rgb[1]},${rgb[2]});padding:0;cursor:grab;border:2px solid transparent`;
  b.draggable = true;
  b.title = "拖到槽位，或点击选中后再点目标位置";
  b.ondragstart = (e) => e.dataTransfer.setData("text/plain", JSON.stringify({zone: pos.zone, idx, slotIdx: pos.slotIdx}));
  b.onclick = (e) => { e.stopPropagation(); selectChip({zone: pos.zone, idx, slotIdx: pos.slotIdx}); };
  return b;
}
function renderHueUI(){
  const colors = window.__hueColors, slots = window.__hueSlots;
  const poolBox = $("huepool"), slotBox = $("hueslots");
  poolBox.innerHTML = ""; slotBox.innerHTML = "";
  const bindDrop = (el, dst) => {
    el.ondragover = (e) => { e.preventDefault(); el.style.borderColor = "rgb(from var(--ac) r g b / .7)"; };
    el.ondragleave = () => { el.style.borderColor = ""; };
    el.ondrop = (e) => {
      e.preventDefault(); el.style.borderColor = "";
      try { placeChip(JSON.parse(e.dataTransfer.getData("text/plain")), dst); } catch (err) {}
    };
    el.onclick = () => selectChip(dst);
  };
  colors.map((_, i) => i).filter((i) => !slots.includes(i)).forEach((idx) => {
    const chip = hueChip(colors[idx], idx, {zone: "pool"});
    if(window.__hueSel && window.__hueSel.zone === "pool" && window.__hueSel.idx === idx)
      chip.style.borderColor = "var(--ac2)";
    poolBox.appendChild(chip);
  });
  bindDrop(poolBox, {zone: "pool"});
  slots.forEach((idx, k) => {
    const d = document.createElement("div");
    d.style.cssText = "border:1px dashed var(--bd);aspect-ratio:11/16;min-width:0;overflow:hidden;display:flex;align-items:center;justify-content:center";
    if(idx !== null) d.appendChild(hueChip(colors[idx], idx, {zone: "slot", slotIdx: k}, true));
    bindDrop(d, {zone: "slot", slotIdx: k});
    slotBox.appendChild(d);
  });
  const filled = slots.filter(v => v !== null).length;
  $("huesubmit").disabled = filled !== slots.length;
  $("huecount").textContent = `已放置 ${filled}/${slots.length}` +
    (window.__hueSel ? " · 已选中一块，点击目标位置放置" : "");
}
function selectChip(pos){
  if(window.__hueDone) return;
  if(!window.__hueSel){ window.__hueSel = pos; renderHueUI(); return; }
  placeChip(window.__hueSel, pos);
}
function placeChip(src, dst){
  const s = window.__hueSlots;
  if(src.zone === "slot" && dst.zone === "slot"){
    const tmp = s[dst.slotIdx]; s[dst.slotIdx] = s[src.slotIdx]; s[src.slotIdx] = tmp;
  } else if(src.zone === "slot" && dst.zone === "pool"){
    s[src.slotIdx] = null;
  } else if(src.zone === "pool" && dst.zone === "slot"){
    s[dst.slotIdx] = src.idx;
  } else { window.__hueSel = null; renderHueUI(); return; }
  window.__hueSel = null;
  renderHueUI();
}
function submitHue(){
  if(window.__hueDone) return;
  window.__hueDone = true;
  submitAnswer(window.__hueSlots.slice());
}
function resetHue(){
  window.__hueSlots = new Array(window.__hueColors.length).fill(null);
  window.__hueSel = null; window.__hueDone = false;
  renderHueUI();
}
function submitWave(){
  if(window.__waveSel === null) return;
  submitAnswer(window.__waveSel);
}

async function submitAnswer(ans){
  try{
    const r = await (await fetch("/api/cvd/exam/answer", {method:"POST",
      headers:{"Content-Type":"application/json"},
      body: JSON.stringify({exam_id: examId, answer: ans})})).json();
    if(!r.ok){ $("exam-area").innerHTML = `<span class="err">[错误] ${r.error}</span>`; return; }
    renderQ(r.results);
  }catch(e){ $("exam-area").innerHTML = `<span class="err">[错误] 请求失败: ${e}</span>`; }
}

/* ==== 档案渲染 / AI 总结 / 校色（含顶部开关同步） ==== */
function renderProfile(prof, opts){
  examId = null;
  $("exam-area").innerHTML = `<div class="ms">测评完成，档案已生成。</div>`;
  const ev = prof.evidence || {};
  const sevPct = Math.round((prof.severity || 0) * 100);
  $("profile-body").innerHTML =
    `<div class="item"><div><b>色觉类型：${TYPE_CN[prof.cvd_type] || prof.cvd_type}</b>` +
    `<div class="meta">severity ${prof.severity}（${sevPct}%）· 置信度 ${prof.confidence} · 分诊通道 ${prof.triage_path}</div>` +
    `<div style="height:6px;background:rgba(255,255,255,.08);margin:6px 0"><div style="height:100%;width:${sevPct}%;background:var(--ac)"></div></div>` +
    `<div class="meta">三维分辨阈值：ΔL=${prof.dL_threshold} · ΔC=${prof.dC_threshold} · ΔH=${prof.dH_threshold}（CIE 单位，越小越敏感）</div>` +
    `<div class="meta">证据：石原 ${ev.n_plates} 张 · 排列判定 ${(ev.hue_verdicts || [ev.hue_verdict]).join(" / ")} · 波段佐证 ${ev.wave ? (ev.wave.axis_hint + "·" + ev.wave.match) : "—"}</div>` +
    `<div class="meta">终档 ${JSON.stringify(ev.final_levels)} · 双证据${ev.consistent ? "一致" : "存在分歧"}</div>` +
    ((prof.prescriptions || []).length ? `<div class="meta">处方：${prof.prescriptions.join(" / ")}</div>` : "") +
    `<div class="meta">${prof.advice || ""}</div></div></div>`;

  /* 校色状态同步（def 34 · 统一走 renderCalState：开关 = 唯一启停，按钮只导入配置） */
  $("calswitch").dataset.hasProfile = "1";   /* 档案生成即解锁校色开关（修复：进页时无档案 → 测评完开关仍被当无档案踢回测评页） */
  renderCalState(prof.calibration || {mode: "off", kind: prof.cvd_type, severity: prof.severity});

  const pc = $("panel-profile");
  if(!location.hash) showTab("profile");   /* def 33 · #锚点直达优先（否则档案渲染把 #verify 抢回档案页） */
  if(opts && opts.justFinished){
    /* def 26 · 旅程自动化（用户 2026-09-20 定稿）：测评完成 → 自动导入校色配置 → AI 自动读取档案并总结，
       用户唯一动作 = 点顶部「校色配色」开关开启校色（导入 ≠ 自动开启，开关始终由用户决定） */
    setTimeout(async () => {
      let cal = null, calErr = "";
      try{
        const r = await (await fetch("/api/cvd/exam/calibrate", {method:"POST",
          headers:{"Content-Type":"application/json"}, body: JSON.stringify({mode: "correct"})})).json();
        if(r.ok){ cal = r.results.calibration; syncCalSwitch(false); }   /* def 35 · 自动导入真实配置（correct），enabled=false 导入≠开启 */
        else calErr = r.error || "未知错误";
      }catch(e){ calErr = String(e); }
      let aiNote = "";
      try{
        const sb = document.getElementById("cb-send");
        if(sb && sb.classList.contains("stop")){
          aiNote = "AI 正在回复上一条，自动总结已跳过——可稍后点「让 AI 分析档案」";
        }else if(window.CBChat){
          window.CBChat.open();
          const j = await window.CBChat.send(
            "【测评完成通知】用户刚刚完成全部色盲测评题目，色觉档案已生成。请立即调用 get_vision_profile_tool 读取档案，" +
            "然后向用户总结：一、他的色彩视觉特点（引用档案具体数字：类型/严重度/三维阈值）；二、这些差异对选色和试妆的影响；" +
            "三、告诉用户：校色配置已根据档案自动导入，只需点击页面顶部「校色配色」开关即可开启全站校色。" +
            "四、重要：若档案类型是 uncertain（未定型），必须同时如实说明——点开关后全站会启用对称红绿增强" +
            "（把红绿色差双向拉开、亮度保持，红色盲/绿色盲用户都能受益且不会补错方向），这不是类型定向校色；" +
            "重测出明确类型（deutan / protan / tritan）后校色会更精准。" +
            "不要调用导航工具——用户已经在测评页面，测完了。");
          if(j && j.error) aiNote = "AI 总结失败（" + j.error + "）——可点「让 AI 分析档案」重试";
          else if(!j) aiNote = "AI 总结未完成——可点「让 AI 分析档案」重试";
        }else{
          aiNote = "AI 窗口未就绪——可点「让 AI 分析档案」重试";
        }
      }catch(e){ aiNote = "AI 总结暂不可用——可点「让 AI 分析档案」重试"; }
      if(cal){
        $("calstatus").innerHTML =
          `<span class="ms">校色配置已根据档案自动导入（${cal.kind} @ severity ${cal.severity}）${aiNote ? " · " + aiNote : ""}</span>` +
          `<div class="meta" style="margin-top:4px">最后一步：点击页面顶部「校色配色」开关即可开启全站校色；下方按钮也可随时手动切换模式。</div>`;
      }else{
        $("calstatus").innerHTML = `<span class="err">[错误] 校色配置自动导入失败：${calErr}</span>`;
      }
    }, 600);
  }
}

function restartExam(){
  showTab("exam");
  $("exam-area").innerHTML = "";
  $("exam-intro").style.display = "";
  $("exam-intro").innerHTML =
    `<div class="meta" style="line-height:1.9;margin-top:6px">重新测评将覆盖当前档案与校色设置。流程：石原 10 → 网格 9 → 排列 2 → 波段 1。</div>` +
    `<button onclick="startExam()" style="margin-top:10px">开始测评</button>`;
  window.scrollTo({top: 0, behavior: "smooth"});
}

async function askAI(){
  const box = $("aisum");
  box.innerHTML = `<div class="meta">AI 正在读取你的档案并总结…（约 10~40s，可在右下角 AI 窗口继续追问）</div>`;
  try{
    const r = await fetch("/api/chat", {method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({message: "请根据我的色盲测评档案，总结我的色彩视觉特点，并给出选色与校色建议"})});
    const j = await r.json();
    box.innerHTML = (j.steps || []).map(s => `<div class="meta">[工具] ${s.tool} ${s.ok ? "[OK]" : "[错误]"}</div>`).join("") +
      (j.error ? `<div class="err">[错误] ${j.error}</div>`
               : `<div class="a" style="white-space:pre-wrap;line-height:1.7">${j.content ?? ""}</div>`);
  }catch(e){ box.innerHTML = `<span class="err">[错误] 请求失败: ${e}</span>`; }
}

/* def 34 · 双语义入口：doCalibrate(mode)   = 档案页按钮「只导入配置」→ POST {mode}，配色交给开关；
             doCalibrate(null, on) = 顶部开关「启停」→ POST {enabled}。
   两条路返回后统一 renderCalState：页面配色永远 = enabled ? 按 mode 上色 : 原色。 */
async function doCalibrate(mode, enabled){
  const st = $("calstatus");
  st.textContent = "提交中…";
  try{
    const body = (enabled === undefined || enabled === null) ? {mode: mode} : {enabled: !!enabled};
    const r = await (await fetch("/api/cvd/exam/calibrate", {method:"POST",
      headers:{"Content-Type":"application/json"}, body: JSON.stringify(body)})).json();
    if(!r.ok){ st.textContent = `[错误] ${r.error}`; renderCalState(window.__cvd_cal_cache || null); return; }
    renderCalState(r.results.calibration);
    /* def 41 · 导入配置（按钮路径）时若开关 on 且不在演示态，会话标记同步为新配置 */
    if(mode && window.CVDTheme && window.CVDTheme.setSession && !window.__cvd_url_sim
       && $("calswitch").classList.contains("on")){
      const cur = window.CVDTheme.getSession();
      const c = r.results.calibration;
      if((!cur || cur.mode !== "simulate") && c && c.mode && c.mode !== "off")
        window.CVDTheme.setSession({mode:c.mode, kind:c.kind, sev:c.severity});
    }
  }catch(e){ st.textContent = `[错误] 请求失败: ${e}`; renderCalState(window.__cvd_cal_cache || null); }
}

/* ==== def 14 · 色盲视角模拟/色对校验（重构时遗漏补回，2026-09-13） ==== */
function cvdVerdict(v){
  if(v==="confuse") return '<span class="err">色盲用户几乎看不出区别（ΔE&lt;5）</span>';
  if(v==="risky") return '<span style="color:#ffc46b">勉强可辨，建议加大明度差（ΔE&lt;12）</span>';
  return '<span class="ms">可清晰区分</span>';
}
async function cvd(){
  const a=$("cvda").value.trim(), b=$("cvdb").value.trim(), ty=$("cvdtype").value, sev=$("cvdsev").value;
  $("cvdsevv").textContent=parseFloat(sev).toFixed(2);
  const el=$("cvdres"); $("cvdms").textContent="";
  try{
    if(b){
      const{j,ms}=await getJSON(`/api/cvd/check?hex_a=${encodeURIComponent(a)}&hex_b=${encodeURIComponent(b)}&cvd_type=${encodeURIComponent(ty)}`);
      $("cvdms").textContent=ms+"ms · ok="+j.ok;
      if(!j.ok){el.innerHTML=`<span class="err">[错误] ${j.error||j._error||"调用失败"}</span>`;return}
      const r=j.results;
      el.innerHTML=
        `<div class="item"><span class="sw" style="background:${r.a_hex}"></span><span class="meta">→</span><span class="sw" style="background:${r.a_sim_hex}"></span><div><b>${r.a_hex} → ${r.a_sim_hex}</b><div class="meta">A 色在 ${j.query.cvd_type} 用户眼中的等效色</div></div></div>`+
        `<div class="item"><span class="sw" style="background:${r.b_hex}"></span><span class="meta">→</span><span class="sw" style="background:${r.b_sim_hex}"></span><div><b>${r.b_hex} → ${r.b_sim_hex}</b><div class="meta">B 色等效色</div></div></div>`+
        `<div class="item"><div><b>正常 ΔE=${r.dE_normal} · 模拟后 ΔE=${r.dE_sim}</b>　<span class="meta">差值收缩 ${r.contraction_pct}%</span>`+
        `<div>${cvdVerdict(r.verdict)}${r.rule_hit==="avoid"?`　<span class="err">[规则命中] ${r.rule_id} 避免并置</span>`:""}${r.rule_hit==="safe"?`　<span class="ms">[规则命中] ${r.rule_id} 安全组合</span>`:""}</div>`+
        (r.recommended_action?`<div class="meta">建议：${r.recommended_action}</div>`:"")+
        `</div></div>`;
    }else{
      const{j,ms}=await getJSON(`/api/cvd/preview?hex=${encodeURIComponent(a)}&cvd_type=${encodeURIComponent(ty)}&severity=${encodeURIComponent(sev)}`);
      $("cvdms").textContent=ms+"ms · ok="+j.ok;
      if(!j.ok){el.innerHTML=`<span class="err">[错误] ${j.error||j._error||"调用失败"}</span>`;return}
      const r=j.results;
      el.innerHTML=`<div class="item"><span class="sw" style="background:${r.original_hex}"></span><span class="meta">→</span><span class="sw" style="background:${r.simulated_hex}"></span><div><b>${r.original_hex} → ${r.simulated_hex}</b><div class="meta">${j.query.cvd_type} · 严重度 ${j.query.severity} · ΔE=${r.delta_e} · 明度 L ${r.luminance.original} → ${r.luminance.simulated}${r.luminance.drop>0?"（塌陷 "+r.luminance.drop+"）":""}</div></div></div>`;
    }
  }catch(e){el.innerHTML=`<span class="err">[错误] 请求失败: ${e}</span>`}
}

/* ==== def 33/36 · 第三部分：全站视角模拟一键开关（临时演示，不落档案，刷新即恢复） ====
   def 36 · 演示态以 [data-sim].on 按钮高亮为单一状态源：开关启停（applyColorState）
   检测到演示态会优先恢复演示色而不是 reset——关/开开关不再把演示清空。 */
const SIM_CN = {deutan:"绿色盲",protan:"红色盲",tritan:"蓝黄色盲"};
function simAll(kind){
  const st = $("simst");
  if(!window.CVDTheme){ st.innerHTML = '<span class="err">theme_cvd.js 未加载</span>'; return; }
  document.querySelectorAll("[data-sim]").forEach(b => b.classList.toggle("on", b.dataset.sim === kind));
  /* def 41 · 会话标记本地先写（URL 演示锁下不动标记）：off = 配色停（含演示）；on = 演示/回配置层 */
  if(window.CVDTheme.setSession && !window.__cvd_url_sim){
    if(!$("calswitch").classList.contains("on")){
      window.CVDTheme.setSession(null);
    }else if(kind){
      window.CVDTheme.setSession({mode:"simulate", kind,
        sev:Math.min(1, Math.max(0, parseFloat($("cvdsev").value) || 1.0))});
    }else{
      const c = window.__cvd_cal_cache;
      window.CVDTheme.setSession(c && c.mode && c.mode !== "off" ? {mode:c.mode, kind:c.kind, sev:c.severity} : null);
    }
  }
  renderCalState(window.__cvd_cal_cache || null);   /* def 41 · 统一出口：配色一次同步 */
  const on = $("calswitch").classList.contains("on");
  if(!kind){
    st.innerHTML = '<span class="ms">已退出演示 · ' + (on ? "回到配置层配色" : "顶部开关关闭中，全站原色") + '</span>';
  }else if(!on){
    st.innerHTML = `<span class="ms">已选中「${SIM_CN[kind]}」演示 · 顶部开关关闭中，全站配色暂停——打开开关即以此演示生效</span>`;
  }else{
    const sev = Math.min(1, Math.max(0, parseFloat($("cvdsev").value) || 1.0));
    st.innerHTML = `<span class="ms">全站已切换「${SIM_CN[kind]}」视角 · severity ${sev.toFixed(2)} · 演示跨页保留（本会话内，刷新/切页不变）；关闭顶部开关 = 全站原色</span>`;
  }
}

/* 页面加载：已有档案 → 跳档案与校色 tab（含校色状态恢复）；无 → 停在测评 tab */
(async () => {
  try{
    /* def 33 · #verify/#profile 锚点直达对应 tab（评委演示/分享直达第三部分） */
    const h = location.hash.replace("#","");
    if(h === "verify" || h === "profile") showTab(h);
    const p = await (await fetch("/api/cvd/exam/profile")).json();
    if(p.ok){
      renderProfile(p.results);
      $("calswitch").dataset.hasProfile = "1";
    }
  }catch(e){}
  $("calswitch").dataset.hasProfile = $("calswitch").dataset.hasProfile || "0";
  /* def 51 · 无档案但全站已开（calswitch 临时口径）→ 开关 UI 同步 on，
     否则开关显示 off 而配色实际生效，状态不符且无法从本页关断 */
  if($("calswitch").dataset.hasProfile !== "1"
     && window.CVDTheme && window.CVDTheme.getSession && window.CVDTheme.getSession()){
    syncCalSwitch(true);
    $("calstatus").innerHTML = `<span class="ms">全站校色开启中（未测评临时口径：对称红绿增强——不假定缺陷方向、亮度保持，跨页保留）——顶部开关可关闭；完成 22 题测评可获个性化校色</span>`;
  }
})();
