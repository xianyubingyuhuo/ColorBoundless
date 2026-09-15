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
    $("calstatus").innerHTML = `<span class="err">暂无测评档案——请先在"色盲测评"完成 22 题</span>`;
    showTab("exam"); return;
  }
  const mode = sw.classList.contains("on") ? "off" : "correct";
  calBusy = true;
  await doCalibrate(mode);
  calBusy = false;
}
function syncCalSwitch(mode){
  $("calswitch").classList.toggle("on", mode === "correct");
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
      `<div id="huepool" class="row" style="min-height:70px;margin-top:6px;padding:6px;border:1px dashed var(--bd)"></div>` +
      `<div class="meta" style="margin:10px 0 4px">↓ 排列槽（从左到右 = 你认为的渐变顺序）</div>` +
      `<div id="hueslots" class="row" style="min-height:70px"></div>` +
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
      cell.onmouseenter = () => cell.style.borderColor = "rgba(229,71,109,.5)";
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
function hueChip(rgb, idx, pos){
  const b = document.createElement("button");
  b.style.cssText = `width:44px;height:64px;background:rgb(${rgb[0]},${rgb[1]},${rgb[2]});padding:0;cursor:grab;border:2px solid transparent`;
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
    el.ondragover = (e) => { e.preventDefault(); el.style.borderColor = "rgba(229,71,109,.7)"; };
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
    d.style.cssText = "width:48px;height:68px;border:1px dashed var(--bd);display:flex;align-items:center;justify-content:center";
    if(idx !== null) d.appendChild(hueChip(colors[idx], idx, {zone: "slot", slotIdx: k}));
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

  /* 校色状态同步（档案自带 calibration 或默认未校色） */
  const cal = prof.calibration;
  const mode = cal ? cal.mode : "off";
  syncCalSwitch(mode);
  if(cal && cal.mode === "correct" && window.CVDTheme) window.CVDTheme.apply("correct", cal.kind, cal.severity);
  $("calstatus").innerHTML = cal
    ? `<span class="ms">当前模式：${cal.mode}（${cal.kind} @ severity ${cal.severity}）</span>`
    : `<span class="meta">尚未校色——点击上方模式按钮，或用页面顶部开关</span>`;

  const pc = $("panel-profile");
  showTab("profile");
  if(opts && opts.justFinished){
    /* 旅程自动化：弹出 AI 总结 → 校正值自动填入（correct 全站联动） */
    setTimeout(async () => {
      try{
        if(!window.CBChat) return;
        window.CBChat.open();
        await window.CBChat.send(
          "【测评完成通知】用户刚刚完成全部色盲测评题目，色觉档案已生成。请立即调用 get_vision_profile_tool " +
          "读取档案，然后向用户总结：一、他的色彩视觉特点；二、他与标准色彩视角的差异值（类型/严重度/三维阈值）；" +
          "三、这些差异对选色和试妆的影响。不要调用导航工具——用户已经在测评页面，测完了。");
        const r = await (await fetch("/api/cvd/exam/calibrate", {method:"POST",
          headers:{"Content-Type":"application/json"}, body: JSON.stringify({mode: "correct"})})).json();
        if(r.ok){
          const cal = r.results.calibration;
          if(window.CVDTheme) window.CVDTheme.apply("correct", cal.kind, cal.severity);
          syncCalSwitch("correct");
          $("calstatus").innerHTML =
            `<span class="ms">已根据测评档案自动完成校色（correct · ${cal.kind} @ severity ${cal.severity}）· 全站配色已联动 · 可手动切换模式</span>`;
        }
      }catch(e){ /* 自动化失败静默：手动按钮兜底 */ }
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

async function doCalibrate(mode){
  const st = $("calstatus");
  st.textContent = "提交中…";
  try{
    const r = await (await fetch("/api/cvd/exam/calibrate", {method:"POST",
      headers:{"Content-Type":"application/json"}, body: JSON.stringify({mode})})).json();
    if(!r.ok){ st.textContent = `[错误] ${r.error}`; return; }
    const cal = r.results.calibration;
    if(window.CVDTheme){
      if(mode === "off") window.CVDTheme.reset();
      else window.CVDTheme.apply(mode, cal.kind, cal.severity);
    }
    syncCalSwitch(mode);
    st.innerHTML = `<span class="ms">已应用：${mode}（${cal.kind} @ severity ${cal.severity}）· 全站配色已联动 · 试妆通道将按此执行</span>`;
  }catch(e){ st.textContent = `[错误] 请求失败: ${e}`; }
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
  const el=$("cvdres"); $("cvdjson").textContent=""; $("cvdms").textContent="";
  try{
    if(b){
      const{j,ms}=await getJSON(`/api/cvd/check?hex_a=${encodeURIComponent(a)}&hex_b=${encodeURIComponent(b)}&cvd_type=${encodeURIComponent(ty)}`);
      $("cvdms").textContent=ms+"ms · ok="+j.ok; $("cvdjson").textContent=JSON.stringify(j,null,2);
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
      $("cvdms").textContent=ms+"ms · ok="+j.ok; $("cvdjson").textContent=JSON.stringify(j,null,2);
      if(!j.ok){el.innerHTML=`<span class="err">[错误] ${j.error||j._error||"调用失败"}</span>`;return}
      const r=j.results;
      el.innerHTML=`<div class="item"><span class="sw" style="background:${r.original_hex}"></span><span class="meta">→</span><span class="sw" style="background:${r.simulated_hex}"></span><div><b>${r.original_hex} → ${r.simulated_hex}</b><div class="meta">${j.query.cvd_type} · 严重度 ${j.query.severity} · ΔE=${r.delta_e} · 明度 L ${r.luminance.original} → ${r.luminance.simulated}${r.luminance.drop>0?"（塌陷 "+r.luminance.drop+"）":""}</div></div></div>`;
    }
  }catch(e){el.innerHTML=`<span class="err">[错误] 请求失败: ${e}</span>`}
}

/* 页面加载：已有档案 → 跳档案与校色 tab（含校色状态恢复）；无 → 停在测评 tab */
(async () => {
  try{
    const p = await (await fetch("/api/cvd/exam/profile")).json();
    if(p.ok){
      renderProfile(p.results);
      $("calswitch").dataset.hasProfile = "1";
    }
  }catch(e){}
  $("calswitch").dataset.hasProfile = $("calswitch").dataset.hasProfile || "0";
})();
