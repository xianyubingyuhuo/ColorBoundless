/* def 15v5 · 试妆页逻辑（自 tryon.html 拆出，改交互只动这个小文件） */
const $ = id => document.getElementById(id);

/* def 15v2 · 上传预览淡入：选择照片 → upzone 内缩略图淡入（点击可更换） */
/* def 31 · 照片本地缓存（IndexedDB）：刷新/关页后自动恢复上次照片，免重新选文件。
   只存浏览器本地（IndexedDB 配额远大于 localStorage，可放原图 dataURL），不涉及服务器 */
const IDB_NAME = "cb_tryon", IDB_STORE = "kv";
function idbOpen(){
  return new Promise((res, rej) => {
    const rq = indexedDB.open(IDB_NAME, 1);
    rq.onupgradeneeded = () => rq.result.createObjectStore(IDB_STORE);
    rq.onsuccess = () => res(rq.result);
    rq.onerror = () => rej(rq.error);
  });
}
async function idbGet(key){
  try{
    const db = await idbOpen();
    return await new Promise((res, rej) => {
      const rq = db.transaction(IDB_STORE, "readonly").objectStore(IDB_STORE).get(key);
      rq.onsuccess = () => res(rq.result || null);
      rq.onerror = () => rej(rq.error);
    }).finally(() => db.close());
  }catch(e){ return null; }
}
async function idbSet(key, val){
  try{
    const db = await idbOpen();
    return await new Promise((res, rej) => {
      const rq = db.transaction(IDB_STORE, "readwrite").objectStore(IDB_STORE).put(val, key);
      rq.onsuccess = () => res(true);
      rq.onerror = () => rej(rq.error);
    }).finally(() => db.close());
  }catch(e){ return false; }
}
function dataURLtoBlob(u){                     /* 缓存 dataURL → Blob（提交 FormData 用） */
  const parts = u.split(","), mime = (parts[0].match(/:(.*?);/) || [])[1] || "image/jpeg";
  const bin = atob(parts[1]), arr = new Uint8Array(bin.length);
  for(let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
  return new Blob([arr], {type: mime});
}
let tyPhoto = null;                            /* {data: dataURL, name} —— 刚选的或从缓存恢复的 */

function showPhoto(data, tag){
  const z = $("upzone");
  z.classList.add("hasimg");
  z.innerHTML = `<img src="${data}" alt="preview"><span class="reup">点击更换照片${tag ? " · " + tag : ""}</span>`;
}

$("tyfile").addEventListener("change", () => {
  const f = $("tyfile").files[0];
  if(!f) return;
  const rd = new FileReader();
  rd.onload = () => {
    tyPhoto = {data: rd.result, name: f.name};
    showPhoto(tyPhoto.data, "");
    idbSet("photo", tyPhoto);                  /* def 31 · 写入本地缓存（覆盖旧照片） */
    analyzeFace();                             /* def 43 · 换照片即自动重新分析 */
  };
  rd.readAsDataURL(f);
});
/* def 31 · 页面加载即恢复上次照片（有缓存 → 免重新选文件；点 upzone 随时可换） */
(async () => {
  try{
    const saved = await idbGet("photo");
    if(saved && saved.data){
      tyPhoto = saved;
      showPhoto(saved.data, "已恢复上次照片");
      analyzeFace();                           /* def 43 · 恢复照片同样自动分析 */
    }
  }catch(e){ /* 缓存不可用：保持空状态，正常手选 */ }
})();
/* def 15v2 · 色板 / 取色器 / hex 三向联动 */
function setDot(card, hex){
  const d = card.querySelector(".p-dot");
  if(d) d.style.background = hex;
}
function pickSwatch(sw, hex){
  const card = sw.closest(".pcard");
  card.querySelector(".p-hex").value = hex.toUpperCase();
  card.querySelector(".p-color").value = hex;
  setDot(card, hex);
}
function syncFromColor(inp){
  const card = inp.closest(".pcard");
  card.querySelector(".p-hex").value = inp.value.toUpperCase();
  setDot(card, inp.value.toUpperCase());
}
function syncFromHex(inp){
  const v = inp.value.trim();
  if(/^#[0-9a-fA-F]{6}$/.test(v)){
    inp.closest(".pcard").querySelector(".p-color").value = v;
    setDot(inp.closest(".pcard"), v);
  }
}
/* def 15v14j · 浮层向左弹出：面板从工具列向左生长（单段动画，卡片同步错落淡入）；
   关闭=面板带卡缩回列宽(auto-fit 3→2→1 重排)后卡片回列依次淡入归位；防重入锁防连点。
   竖把手 #pcmore 跟随面板左缘移动（.open 与面板同步挂摘，transition 同曲线），
   箭头 ‹/› 指示展开(左)/收回(右)方向，打开时可点把手收起 */
let tyCoverTimer = null, tyCoverLock = false;
function toggleGrid(){
  if(tyCoverLock) return;
  const cover = $("pcover"), cards = $("pcards");
  const opening = !cover.classList.contains("open") && !cover.classList.contains("closing");
  clearTimeout(tyCoverTimer);
  if(opening){
    $("pcover-slot").appendChild(cards);        // 同一份 DOM 移入浮层（选色状态零同步）
    cover.style.height = $("upzone").offsetHeight + "px";   // 面板高度=照片窗口等高（不锁满右列）
    cover.classList.add("open");                // 面板向左生长 + 卡片错落入场（CSS 单段并发）
  }else{
    cover.classList.remove("open");
    cover.classList.add("closing");             // 面板带卡缩回列宽（0.38s）
    tyCoverLock = true;
    tyCoverTimer = setTimeout(() => {
      cover.classList.remove("closing");
      $("pcards-home").appendChild(cards);      // 卡片回列
      cards.classList.add("reback");            // 依次淡入归位
      setTimeout(() => cards.classList.remove("reback"), 360);
      tyCoverLock = false;
    }, 400);
  }
  const b = $("pcmore");
  b.textContent = opening ? "›" : "‹";
  b.classList.toggle("open", opening);          // 把手与面板同步：滑向面板左缘 / 滑回列左缝
  b.title = opening ? "收起工具总览" : "展开工具总览";
}
/* def 15v6 · 展开：悬停停3s自动1s动画展开(pick-slow,移出即收) / 点击立即展开(pick-open,锁定,点外部或再点收起) */
document.querySelectorAll(".pcard[data-region]").forEach(card => {
  let hoverTimer = null;
  card.addEventListener("mouseenter", () => {                 // 悬停排程：3s 后自动展开
    if(card.classList.contains("pick-open")) return;
    clearTimeout(hoverTimer);
    hoverTimer = setTimeout(() => card.classList.add("pick-slow"), 3000);
  });
  card.addEventListener("mouseleave", () => {                 // 移出：取消排程 + 收起自动展开
    if(card.contains(document.activeElement) || card.querySelector(":active")) return; // 输入/拖滑轨/取色中不收起
    clearTimeout(hoverTimer);
    card.classList.remove("pick-slow");
  });
  card.addEventListener("click", (e) => {                     // 点击：立即展开/收起（锁定）
    if(e.target.closest(".p-pick,.p-swatch,.pr,.p-en,input,button")) return; // 选色面板内操作不切换
    clearTimeout(hoverTimer);
    card.classList.remove("pick-slow");
    document.querySelectorAll(".pcard.pick-open").forEach(c => { if(c !== card) c.classList.remove("pick-open"); });
    card.classList.toggle("pick-open");
  });
});
document.addEventListener("click", (e) => {
  if(!e.target.closest(".pcard,#pcover,#pcmore")){
    document.querySelectorAll(".pcard.pick-open,.pcard.pick-slow")
      .forEach(c => c.classList.remove("pick-open", "pick-slow"));
    if($("pcover").classList.contains("open")) toggleGrid();   // 点浮层外 → 收起总览
  }
});
/* 展开期间视口尺寸变化 → 面板高度跟随照片窗口（等高关系保持） */
window.addEventListener("resize", () => {
  if($("pcover").classList.contains("open")) $("pcover").style.height = $("upzone").offsetHeight + "px";
});

/* def 18 · AI 色号回填：chatbox action 通道调用；每部位填 hex（复用三向联动）+ 强制启用。
   用户可随时用色板/取色器/滑轨改写——最终决定权在用户（R-05 原则） */
window.fillParts = function(parts){
  let n = 0;
  (parts || []).forEach((p) => {
    if (!p || !p.region || !p.hex) return;
    const card = document.querySelector('.pcard[data-region="' + p.region + '"]');
    if (!card) return;
    const hex = String(p.hex);
    if (!/^[0-9a-fA-F]{6}$/.test(hex.replace("#", ""))) return;
    const inp = card.querySelector(".p-hex");
    if (inp){ inp.value = ("#" + hex.replace("#", "")).toUpperCase(); syncFromHex(inp); }
    const on = card.querySelector(".p-on");
    if (on) on.checked = true;
    n++;
  });
  const ms = $("tyms");
  if (ms && n) ms.textContent = "AI 已回填 " + n + " 个部位——可微调后点「开始聚合试妆」（原选择已被覆盖，可用色板改回）";
  return n;
};
/* def 18 · 跨页中转消费：非 tryon 页收到 fill → chatbox 存 cb_fill → 本页加载后自动回填 */
(function consumeFill(){
  try{
    const raw = sessionStorage.getItem("cb_fill");
    if (!raw) return;
    sessionStorage.removeItem("cb_fill");
    const parts = JSON.parse(raw);
    if (Array.isArray(parts) && parts.length && typeof window.fillParts === "function"){
      setTimeout(() => { window.fillParts(parts); }, 80);
    }
  }catch(e){}
})();

(async () => {
  try {
    const p = await (await fetch("/api/cvd/exam/profile")).json();
    if (p.ok) {
      const r = p.results, cal = r.calibration;
      if (cal && cal.mode === "correct") {
        $("corstatus").innerHTML =
          `<span class="ms">校色生效中（${cal.mode} · ${cal.kind} @ severity ${cal.severity}）——` +
          `所选色号将反解为标准视觉等意色后上妆</span>`;
      } else if (cal && cal.mode === "simulate") {
        $("corstatus").innerHTML =
          `<span class="meta">模拟模式生效中（全站配色为你模拟展示）——此模式下试妆色号不做反解</span>`;
      } else {
        $("corstatus").innerHTML =
          `<span class="meta">已有测评档案但未完成校色——请去 <a href="/cvd.html" style="color:var(--ac2)">色盲校验</a> ` +
          `STEP 2 选择校色模式（旅程：测评 → 校色 → 试妆）</span>`;
      }
    } else {
      $("corstatus").innerHTML =
        `<span class="meta">暂无测评档案——先去 <a href="/cvd.html" style="color:var(--ac2)">色盲校验</a> 完成测评，` +
        `试妆颜色将自动按你的色觉特点校正。</span>`;
    }
  } catch (e) {
    $("corstatus").textContent = "校正状态未知（档案服务未响应）";
  }
})();

async function tyParts(){
  const f = $("tyfile").files[0] || (tyPhoto ? dataURLtoBlob(tyPhoto.data) : null);   /* def 31 · 新选文件优先，否则用缓存照片转 Blob */
  if(!f){ $("tyres").innerHTML = `<span class="err">[错误] 先选一张照片（jpg/png）</span>`; return; }
  const parts = [];
  document.querySelectorAll(".pcard[data-region]").forEach(card => {
    const on = card.querySelector(".p-on");
    if(!on || !on.checked) return;                                    // 未启用/无控件部位跳过
    const spec = { region: card.dataset.region,
                   hex: card.querySelector(".p-hex").value.trim(),
                   alpha: parseFloat(card.querySelector(".p-a").value) };
    const sz = card.querySelector(".p-sz");
    if(sz) spec.size = parseFloat(sz.value);          // def 18c · 范围滑轨（仅腮红/眼影卡有）
    parts.push(spec);
  });
  if(!parts.length){ $("tyres").innerHTML = `<span class="err">[错误] 至少启用一个部位</span>`; return; }
  /* def 27 · 社会视角守门：罕见色 + 色盲档案 → 确认卡（告知别人看到的 + 主流替代），执意才放行 */
  const needGate = [];
  for(const p of parts){
    if(gateKeep[p.region] === p.hex.toUpperCase()) continue;      // 同色已确认"仍要用"（改色即重新守门）
    const rv = await shadeReview(p.hex, p.region);
    if(rv.ok && rv.results && rv.results.gate) needGate.push({part: p, review: rv.results});
  }
  if(needGate.length){ renderGate(needGate); return; }   // 等待用户决策后自动重跑 tyParts
  const lip = parts.find(p => p.region === "lip") || {hex: "#C2185B", alpha: 0.75};
  const fd = new FormData();
  fd.append("file", f);
  fd.append("hex_color", lip.hex);                                   // 主色=唇（校色对象）
  fd.append("alpha", lip.alpha);
  fd.append("correct", $("cormode").value === "on" ? "true" : "false");
  fd.append("parts", JSON.stringify(parts));
  $("tyms").textContent = "";
  $("tyres").innerHTML = `<div class="meta">[等待] 聚合上妆中…（首次约 30s 加载 AI 模型，之后每次约 0.1s）</div>`;
  $("matchres").innerHTML = "";
  const t0 = performance.now();
  try{
    const r = await fetch("/api/tryon", {method:"POST", body: fd});
    const j = await r.json();
    const ms = Math.round(performance.now()-t0);
    $("tyms").textContent = ms + "ms · device=" + (j.query?.device || "?");
    if(!j.ok){ $("tyres").innerHTML = `<span class="err">[错误] ${j.error}</span>`; return; }
    const c = (j.results.correction) || {};
    const corLine = c.applied
      ? `<div class="meta">已校正（唇部主色）：${c.original_hex} → <b style="color:var(--tx)">${c.corrected_hex}</b> · 残差 ΔE=${c.delta_e_residual}</div>`
      : `<div class="meta">未校正：${c.reason || ""}</div>`;
    const applied = (j.query.applied || []).map(a =>
      `<span class="ms">${a.region}=#${a.hex}@α${a.alpha}</span>`).join(" · ");
    $("tyres").innerHTML =
      `<div class="row"><figure class="imgbox"><img src="data:image/jpeg;base64,${j.results.original_b64}"><figcaption>原图</figcaption></figure>` +
      `<figure class="imgbox"><img src="data:image/jpeg;base64,${j.results.makeup_b64}"><figcaption>聚合上妆</figcaption></figure></div>` +
      `<div class="meta">已渲染部位：${applied}</div>` + corLine;
    /* def 15d/18c+ · 商品匹配：逐部位检索并收集 → 行渲染 + 无现货自动淡入定制面板 */
    const matchResults = [];
    for(const p of parts){
      const mr = await fetchMatch(p.hex, p.region);
      matchResults.push({hex: String(p.hex).replace("#", ""), region: p.region, ok: mr.ok,
                         available: !!(mr.results && mr.results.available),
                         nearest: (mr.results && mr.results.nearest) || null,
                         candidates: (mr.results && mr.results.candidates) || []});
      renderMatchLine(p.hex, p.region, mr);
    }
    const missing = matchResults.filter(m => m.ok && !m.available);
    if(missing.length){ openCustomPanel(missing); } else { $("custompanel").hidden = true; }
  }catch(e){
    $("tyres").innerHTML = `<span class="err">[错误] 请求失败: ${e}</span>`;
  }
}

/* def 18c+ · 定制流 v2：检索与渲染分离；无现货颜色 → 淡入面板（清单+近似推荐）→ 一键提交 → 跳产品库 */
const REG_NAME = { lip: "唇妆", foundation: "粉底", eyeshadow: "眼影", brow: "眉妆", blush: "腮红" };
async function fetchMatch(hex, region){
  try{
    return await (await fetch(`/api/products/match?hex=${encodeURIComponent(hex)}&region=${encodeURIComponent(region)}`)).json();
  }catch(e){ return {ok: false, error: "请求失败"}; }
}
function renderMatchLine(hex, region, r){
  const box = $("matchres");
  const cat = REG_NAME[region] || region;
  if(!r.ok){ box.insertAdjacentHTML("beforeend", `<div class="meta">${cat} · #${hex} 匹配失败: ${r.error}</div>`); return; }
  const n = r.results.nearest, av = r.results.available;
  const sc = (r.results && r.results.showcase_txt) || "";   // def 46c · 橱窗归属（品类 · 分支 · 色号）
  const own = sc ? ` · 橱窗：${sc}` : "";
  const line = av
    ? `<span style="color:#7de0a6">✓ 有货</span> 最近商品：<b>${n.brand} ${n.product}</b>（#${n.hex} · ΔE=${n.dE}）${own}`
    : `<span style="color:#ff8a80">✗ 无接近现货</span>（近似：${n.brand} ${n.product} · #${n.hex} · ΔE=${n.dE}）——见下方定制面板${own}`;
  box.insertAdjacentHTML("beforeend", `<div class="meta" style="margin:3px 0">${cat} · #${hex} → ${line}</div>`);
}
/* def 56 · 定制申请弹窗：每颜色 → 选商品（近似候选 top5）→ 确认系列名 → 选规格 */
const SPEC_SET = {
  lip: ["单支装 3.5g", "迷你装 1.5g"],
  foundation: ["正装 30ml", "便携装 15ml"],
  eyeshadow: ["单色 2g", "四色盘 8g"],
  brow: ["单支 1g", "双头 0.8g"],
  blush: ["单色 5g", "盒装 7g"],
};
const escHtml = (s) => String(s ?? "").replace(/[&<>"']/g,
  (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));

function customModalRow(hex, region, cands){
  const list = cands && cands.length ? cands : [{brand: "ColorBoundless Official", product: "", hex: hex, dE: "—", series: ""}];
  const opts = list.map((c, i) =>
    `<option value="${i}" data-brand="${escHtml(c.brand)}" data-product="${escHtml(c.product)}" data-series="${escHtml(c.series || "")}" ${i === 0 ? "selected" : ""}>` +
    `${escHtml(c.brand)} · ${escHtml(c.product || "（无候选）")}（#${escHtml(c.hex)} · ΔE=${escHtml(c.dE)}）</option>`).join("");
  const specs = (SPEC_SET[region] || ["标准规格"]).map((s, i) =>
    `<option value="${escHtml(s)}" ${i === 0 ? "selected" : ""}>${escHtml(s)}</option>`).join("");
  return `
    <div class="citem" data-hex="${escHtml(hex)}" data-region="${escHtml(region)}">
      <span class="sw" style="background:#${escHtml(hex)}"></span>
      <div class="tx" style="flex:1;min-width:0">
        <b>${REG_NAME[region] || region} · #${escHtml(hex)}</b>
        <div class="meta">商品类型：${REG_NAME[region] || region}</div>
        <div class="crow"><label>定制商品</label>
          <select class="csel-product" onchange="this.closest('.citem').querySelector('.csel-series').value = this.options[this.selectedIndex].dataset.series || ''">${opts}</select></div>
        <div class="crow"><label>系列名</label>
          <input class="csel-series" value="${escHtml(list[0].series || "")}" placeholder="所属系列（选商品自动带出，可微调）" /></div>
        <div class="crow"><label>规格</label>
          <select class="csel-spec">${specs}</select></div>
      </div>
    </div>`;
}

function closeCustomModal(){
  const p = $("custommask");
  p.classList.remove("show");
  setTimeout(() => { p.hidden = true; }, 180);
}

function openCustomPanel(missing){
  /* def 56 · 批量无现货 → 弹窗逐项选择（商品/系列名/规格）后统一提交 */
  $("clist").innerHTML = missing.map(m => {
    let cands = m.candidates || [];
    if (!cands.length && m.nearest) cands = [m.nearest];
    return customModalRow(m.hex, m.region, cands);
  }).join("");
  const btn = $("csubmit");
  btn.disabled = false;
  btn.textContent = `一键提交 ${missing.length} 项定制申请`;
  $("cms").textContent = "";
  const p = $("custommask");
  p.hidden = false;
  requestAnimationFrame(() => p.classList.add("show"));
}
async function submitCustomAll(btn){
  btn = btn || $("csubmit");
  const rows = [...document.querySelectorAll("#clist .citem")];
  if(!rows.length) return;
  btn.disabled = true;
  const ms = $("cms");
  ms.textContent = "提交中…";
  let okN = 0;
  for(const row of rows){
    const hex = row.dataset.hex, region = row.dataset.region;
    const prodSel = row.querySelector(".csel-product");
    const opt = prodSel && prodSel.selectedOptions[0];
    const brand = (opt && opt.dataset.brand) || "";
    const series = (row.querySelector(".csel-series") || {}).value || "";
    const spec = (row.querySelector(".csel-spec") || {}).value || "";
    const product = [brand, (opt && opt.dataset.product) || ""].filter(Boolean).join(" ");
    try{
      const r = await (await fetch("/api/products/custom", {method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({hex, region, product, series, spec,
          note: "聚合试妆无现货 · 弹窗选择定制"})})).json();
      if(r.ok) okN++;
    }catch(e){}
  }
  if(okN){
    ms.textContent = `已提交 ${okN}/${rows.length} 项——正在前往产品库查看…`;
    window.cbNavKeep && window.cbNavKeep();   /* def 50 · 站内跳转标记：时间线读取依赖跳转后状态保留 */
    setTimeout(() => { location.href = "products.html#custom"; }, 900);
  } else {
    ms.textContent = "提交失败（服务未响应）——可重试";
    btn.disabled = false;
}
}

/* ==== def 27 · 社会视角守门：确认卡（别人看到的 + 社会等效色 + 在售主流替代）====
   语义（用户 2026-09-20 定稿）：罕见色必须确认；告知正常人视角 + 社会等效色 + 在售替代；
   执意原色 → 尊重（无现货走定制）；推荐色来自在售板，无现货直接定制不再二次询问。 */
const gateKeep = {};                       // region -> 已确认"仍要用"的 hex（改色即重新守门）
async function shadeReview(hex, region){
  try{
    return await (await fetch("/api/tryon/shade_review", {method:"POST",
      headers:{"Content-Type":"application/json"},
      body: JSON.stringify({hex, region})})).json();
  }catch(e){ return {ok:false, error:String(e)}; }
}
function gateSetHex(region, hex){
  const card = document.querySelector('.pcard[data-region="' + region + '"]');
  const inp = card && card.querySelector(".p-hex");
  if(inp){ inp.value = ("#" + String(hex).replace("#", "")).toUpperCase(); syncFromHex(inp); }
}
let gateData = [];
function renderGate(items){
  gateData = items;
  $("tyres").innerHTML = items.map((it, i) => {
    const r = it.review, se = r.social_equiv || {};
    const sug = (r.suggestions || []).map(s =>
      `<div class="row" style="margin:3px 0;align-items:center">` +
      `<button style="background:#${s.hex};width:34px;height:30px;border:1px solid rgba(255,255,255,.45);cursor:pointer;border-radius:6px;flex:none" title="#${s.hex}" onclick="gatePick(${i}, '${s.hex}')"></button>` +
      `<span class="meta">${s.brand ? s.brand + " " : ""}${s.name} · #${s.hex} · 你眼中 ΔE=${s.dE_sim}${s.official ? " · 官方有货" : ""}</span></div>`).join("");
    return `<div class="item" style="border:1px solid rgba(255,196,107,.5);padding:10px">` +
      `<b style="color:#ffc46b">⚠ 社会视角确认 · ${r.region_name}</b>` +
      `<div class="meta" style="margin-top:6px">你选了 <span class="sw" style="background:${r.hex}"></span> <b>${r.hex}</b>——该品类 ${r.palette_size} 个在售色中最近的 ΔE=${r.min_dE}（<b>罕见/非主流色</b>）。</div>` +
      `<div class="meta">在正常人眼里，它是「<b>${(r.seen_by_norm || {}).name}</b>」。${se.applied ? `你想要的效果，在社会正常视角下是 <span class="sw" style="background:${se.corrected_hex}"></span> <b>${se.corrected_hex}</b>「${se.seen_by_norm_name}」。` : ((se && se.note) || "")}</div>` +
      `<div class="meta" style="margin-top:6px">换成在售主流色（按你眼中相似度排序 · 别人看到的是正常妆效）：</div>` +
      `<div style="margin:4px 0">${sug || '<span class="meta">该品类暂无在售替代</span>'}</div>` +
      `<div class="row" style="margin-top:8px">` +
      `<button onclick="gateKeepConfirm(${i})">仍用这个色出门（尊重你的选择，无现货会走定制）</button>` +
      `<button onclick="gateAskAI(${i})">问 AI 这个选择合不合适</button></div>` +
      `</div>`;
  }).join("") + `<div class="meta">处理完确认卡会自动继续上妆；确认原色或换色后本次不再重复询问（改色会重新守门）。</div>`;
  const bx = document.getElementById("tyres");
  window.scrollTo({top: bx.offsetTop - 60, behavior: "smooth"});
}
function gatePick(i, hex){
  const it = gateData[i]; if(!it) return;
  gateSetHex(it.part.region, hex);
  tyParts();                                 // 推荐色来自在售板 → 主流判定通过，直接继续
}
function gateKeepConfirm(i){
  const it = gateData[i]; if(!it) return;
  gateKeep[it.part.region] = it.part.hex.toUpperCase();
  tyParts();
}
function gateAskAI(i){
  const it = gateData[i]; if(!it || !window.CBChat) return;
  const r = it.review, se = r.social_equiv || {};
  window.CBChat.open();
  window.CBChat.send(
    `用户（色觉档案：${se.cvd_type || "见档案"} severity ${se.severity || "见档案"}）在${r.region_name}选了 ${r.hex}。` +
    `代码工具 shade_review 判定：该品类 ${r.palette_size} 个在售色中最小 ΔE=${r.min_dE}（罕见/非主流）；` +
    `正常人眼里是「${(r.seen_by_norm || {}).name}」；` +
    (se.applied ? `社会正常等效色（你想要的效果）= ${se.corrected_hex}「${se.seen_by_norm_name}」；` : "") +
    `在售主流替代（按用户视角相似度）：` +
    (r.suggestions || []).map(s => `${s.brand ? s.brand + " " : ""}${s.name} #${s.hex}（用户视角 ΔE=${s.dE_sim}）`).join("、") + "。" +
    "请用人话向用户解释：一、这个颜色出门别人大概率会怎么看（诚实、不评判）；" +
    "二、替代色为什么效果接近；三、两条路都尊重——仍用原色可走定制，换推荐色点色块即可。不要调用导航工具。");
}

/* =============================================================================
   def 43 · AI 面部分析：上传/恢复照片 → 自动调 /api/face_profile
   （后端：Gray-World 白平衡校正 + BiSeNet 部位解析 + 分部位中值取色；
   肤色按 YCbCr 肤色域得分在原图/校正图间择优，防「白皮拍成黄皮」）
   → 渲染档案面板 →「AI 智能配妆」把检测事实一键注入 AI 对话上下文，
   AI 直调 recommend_shade_tool → 既有 fill 通路回填部位卡。
   省 token：AI 不看图、不反问外貌，一条结构化消息完成推荐。
   ============================================================= */
let tyProfSeq = 0, tyFaceProf = null;          /* 序号防竞态（连换照片只认最后一次） */

function fpRowHtml(label, o){
  if(!o || o.status !== "ok")
    return `<div class="fp-row fp-na"><span class="sw" style="background:#5a5a5a"></span>` +
           `<span class="meta"><b>${label}</b>：${(o && o.note) || "未检出"}</span></div>`;
  const desc = o.level ? `${o.level} · ${o.undertone}` : (o.name || "");
  const note = o.note ? ` · ${o.note}` : "";
  return `<div class="fp-row"><span class="sw" style="background:#${o.hex}" title="#${o.hex}"></span>` +
         `<span class="meta"><b>${label}</b>：#${o.hex} · ${desc}${note}</span></div>`;
}
function renderFaceProf(p){
  let html = fpRowHtml("肤色", p.skin) + fpRowHtml("发色", p.hair) + fpRowHtml("眉色", p.brow) +
             fpRowHtml("瞳色", p.eye) + fpRowHtml("唇色", p.lip);
  if(p.face_shape && p.face_shape.status === "ok")
    html += `<div class="fp-row"><span class="sw" style="background:transparent;border-style:dashed"></span>` +
            `<span class="meta"><b>脸型</b>：${p.face_shape.name} · ${p.face_shape.note}</span></div>`;
  if(p.correction && p.correction.chosen === "original")
    html += `<div class="fp-row meta">照片色偏较大：白平衡校正反而引入偏差，已按原图取色（机制自动择优）</div>`;
  $("fp-rows").innerHTML = html;
  const nOK = ["skin", "hair", "brow", "eye", "lip"].filter(k => p[k] && p[k].status === "ok").length;
  $("fp-ms").textContent = `已识别 ${nOK}/5 项 · 正在自动配色…`;
}
async function analyzeFace(){
  const seq = ++tyProfSeq;
  const f = $("tyfile").files[0] || (tyPhoto ? dataURLtoBlob(tyPhoto.data) : null);
  if(!f) return;
  $("faceprof").hidden = false;
  $("faceprof").classList.add("show");           /* def 43 · cpanel 基类默认 opacity:0，须挂 show 才可见 */
  $("fp-rows").innerHTML = `<div class="fp-row meta">面部分析中…（首次约 30s 加载解析模型，之后每次约 1~3s）</div>`;
  $("fp-ms").textContent = "";
  try{
    const fd = new FormData();
    fd.append("file", f);
    const r = await fetch("/api/face_profile", {method: "POST", body: fd});
    const j = await r.json();
    if(seq !== tyProfSeq) return;              /* 用户已换新照片：丢弃过期结果 */
    if(!j.ok){ $("fp-rows").innerHTML = `<div class="fp-row err">分析失败：${j.error}</div>`; return; }
    tyFaceProf = j.results.profile;
    renderFaceProf(tyFaceProf);
    /* def 55 · 分析完成即自动发起 AI 配妆——用户不必再手动点「AI 智能配妆」
       （序号校验防竞态：连换照片只认最后一次分析结果） */
    setTimeout(() => { if (seq === tyProfSeq) fpRecommend(); }, 400);
  }catch(e){
    if(seq === tyProfSeq) $("fp-rows").innerHTML = `<div class="fp-row err">分析服务未响应：${e}</div>`;
  }
}
function fpRecommend(){
  const p = tyFaceProf;
  if(!p || !window.CBChat) return;
  const seg = [];
  const push = (name, o, fmt) => {
    if(o && o.status === "ok") seg.push(`${name} ${fmt(o)}`);
    else seg.push(`${name}未检出（区域过小，按常规推荐即可）`);
  };
  push("肤色", p.skin, o => `#${o.hex}（${o.level}·${o.undertone}）`);
  push("发色", p.hair, o => `#${o.hex}（${o.name}）`);
  push("眉色", p.brow, o => `#${o.hex}（${o.name}）`);
  push("瞳色", p.eye, o => `#${o.hex}（${o.name}${o.note ? "；" + o.note : ""}）`);
  push("唇色", p.lip, o => `#${o.hex}（${o.name}）`);
  if(p.face_shape && p.face_shape.status === "ok") seg.push(`脸型 ${p.face_shape.name}（粗略估计）`);
  const msg =
    "我在试妆页上传了照片，平台代码已完成人脸解析（灰世界白平衡校正后自动取色，是客观检测数据）：\n" +
    seg.join("；") + "。\n" +
    "请直接基于以上事实调用 recommend_shade_tool 推荐一套完整妆容：lip、foundation、eyeshadow、brow、blush " +
    "五个部位各一项色号，并附一句话配色思路。这些数据已由代码检测完成，不要反问我的外貌；" +
    "如需了解我的色觉特点可调用 get_vision_profile_tool；不要调用导航工具。";
  /* def 55 · 注入消息静默（不上屏、不进对话档——用户只看到 AI 的推荐结果与卡片被填好）；
     AI 忙时排队等其回复完再发，避免打断用户正在进行的问答 */
  const fire = () => {
    $("fp-ms").textContent = "AI 正在按你的五官自动配色…（推荐结果见右侧对话，色号已同步到下方卡片）";
    window.CBChat.open();
    window.CBChat.send(msg, {silent: true});
  };
  if (window.CBChat.busy){
    $("fp-ms").textContent = "AI 回复中——回复结束后自动开始配色…";
    const t = setInterval(() => {
      if (!window.CBChat.busy){ clearInterval(t); fire(); }
    }, 700);
    return;
  }
  fire();
}
