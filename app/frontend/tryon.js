/* def 15v5 · 试妆页逻辑（自 tryon.html 拆出，改交互只动这个小文件） */
const $ = id => document.getElementById(id);

/* def 15v2 · 上传预览淡入：选择照片 → upzone 内缩略图淡入（点击可更换） */
$("tyfile").addEventListener("change", () => {
  const f = $("tyfile").files[0];
  if(!f) return;
  const rd = new FileReader();
  rd.onload = () => {
    const z = $("upzone");
    z.classList.add("hasimg");
    z.innerHTML = `<img src="${rd.result}" alt="preview"><span class="reup">点击更换照片</span>`;
  };
  rd.readAsDataURL(f);
});
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
/* def 15v8 · 网格总览=浮层：把同一份 #pcards 移入/移出浮层（选色状态零同步），不改变工具列布局 */
function toggleGrid(){
  const cover = $("pcover"), cards = $("pcards");
  const open = !cover.classList.contains("open");
  if(open){ $("pcover-slot").appendChild(cards); }
  else{ $("pcards-home").appendChild(cards); }
  cover.classList.toggle("open", open);
  $("pcgridbtn").textContent = open ? "✕ 关闭" : "⊞ 网格视图";
  const b = $("pcmore");
  b.textContent = open ? "⌃" : "⌄";
  b.title = open ? "收起工具总览" : "展开工具总览";
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
  if(!e.target.closest(".pcard,#pcover,#pcgridbtn,#pcmore")){
    document.querySelectorAll(".pcard.pick-open,.pcard.pick-slow")
      .forEach(c => c.classList.remove("pick-open", "pick-slow"));
    if($("pcover").classList.contains("open")) toggleGrid();   // 点浮层外 → 收起总览
  }
});

/* def 17b · 校色联动：页面加载即查档案+校色状态，状态条可见可解释 */
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
  const f = $("tyfile").files[0];
  if(!f){ $("tyres").innerHTML = `<span class="err">[错误] 先选一张照片（jpg/png）</span>`; return; }
  const parts = [];
  document.querySelectorAll(".pcard[data-region]").forEach(card => {
    const on = card.querySelector(".p-on");
    if(!on || !on.checked) return;                                    // 未启用/无控件部位跳过
    parts.push({ region: card.dataset.region,
                 hex: card.querySelector(".p-hex").value.trim(),
                 alpha: parseFloat(card.querySelector(".p-a").value) });
  });
  if(!parts.length){ $("tyres").innerHTML = `<span class="err">[错误] 至少启用一个部位</span>`; return; }
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
    $("tyjson").textContent = JSON.stringify(j, null, 2)
      .replace(/"original_b64": "[^"]+"/, `"original_b64": "<${Math.floor((j.results?.original_b64||"").length*3/4/1024)}KB 图>"`)
      .replace(/"makeup_b64": "[^"]+"/, `"makeup_b64": "<…>"`);
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
    /* def 15d · 商品匹配：逐部位所选色 → 最近集团商品 + 有货/定制 */
    for(const p of parts){ await matchAndShow(p.hex, p.region); }
  }catch(e){
    $("tyres").innerHTML = `<span class="err">[错误] 请求失败: ${e}</span>`;
  }
}

/* def 15d · 商品匹配（所选色 → 最近集团商品，dE≤5 有货，否则可定制） */
async function matchAndShow(hex, region){
  const box = $("matchres");
  try{
    const r = await (await fetch(`/api/products/match?hex=${encodeURIComponent(hex)}&region=${encodeURIComponent(region)}`)).json();
    if(!r.ok){ box.insertAdjacentHTML("beforeend", `<div class="meta">${region} · #${hex} 匹配失败: ${r.error}</div>`); return; }
    const n = r.results.nearest, av = r.results.available;
    const line = av
      ? `<span style="color:#7de0a6">✓ 有货</span> 最近商品：<b>${n.brand} ${n.product}</b>（#${n.hex} · ΔE=${n.dE}）`
      : `<span style="color:#ff8a80">✗ 无接近现货</span>（最近 #${n.hex} · ΔE=${n.dE}） <button onclick="customReq('${hex}','${region}',this)">申请定制</button> <span class="cbh-${region}-${hex}"></span>`;
    box.insertAdjacentHTML("beforeend",
      `<div class="meta" style="margin:3px 0">${region} · #${hex} → ${line}</div>`);
  }catch(e){
    box.insertAdjacentHTML("beforeend", `<div class="meta">${region} · #${hex} 匹配请求失败</div>`);
  }
}

/* def 15d · 定制申请登记（无现货色号 → data/products/custom_requests.json） */
async function customReq(hex, region, btn){
  const note = prompt("定制备注（可写想要的质地/风格，留空即可）：", "") || "";
  btn.disabled = true; btn.textContent = "提交中…";
  try{
    const r = await (await fetch("/api/products/custom", {method:"POST",
      headers:{"Content-Type":"application/json"},
      body: JSON.stringify({hex, region, note})})).json();
    const host = btn.parentElement;
    host.innerHTML = r.ok
      ? `<span style="color:#7de0a6">✓ 定制申请已登记（#${hex}）</span>`
      : `<span class="err">登记失败: ${r.error}</span>`;
  }catch(e){
    btn.disabled = false; btn.textContent = "申请定制（重试）";
  }
}
