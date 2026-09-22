/* products 页逻辑（def 18a · 产品库激活）：色号查询器 / 双库浏览 / 定制申请时间线
   URL 参数 ?hex=ABCDEF&region=foundation → 自动查询（伴随 AI navigate 跳转落点，def 18 通道） */
const $ = id => document.getElementById(id);

function esc(s){
  return String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
}

async function doQuery(){
  const hex = $("qhex").value.trim();
  const region = $("qregion").value;
  $("pres").innerHTML = '<div class="meta">检索中…（CIEDE2000 逐条比对）</div>';
  const t0 = performance.now();
  try{
    const r = await (await fetch(`/api/products/match?hex=${encodeURIComponent(hex)}&region=${encodeURIComponent(region)}`)).json();
    $("qms").textContent = Math.round(performance.now() - t0) + "ms";
    if(!r.ok){ $("pres").innerHTML = `<span class="err">[错误] ${esc(r.error)}</span>`; return; }
    const n = r.results.nearest, av = r.results.available, sc = r.results.showcase_txt;
    $("pres").innerHTML = `
      <div class="match-card">
        <span class="sw" style="background:#${esc(n.hex)}"></span>
        <div style="min-width:0">
          <div><b>${esc(n.brand)}</b> · ${esc(n.product)}</div>
          <div class="meta">#${esc(n.hex)} · ΔE=${esc(n.dE)} · 阈值 ${esc(r.query.threshold_dE)}（CIEDE2000）</div>
          <div class="meta">橱窗归属：${esc(sc || "—")}</div>
          <div style="margin-top:6px">${av
            ? '<span class="badge-ok">✓ 有现货</span>'
            : '<span class="badge-no">✗ 无接近现货</span> <button onclick="customReq()">申请定制</button>'}</div>
          <div class="meta" id="custommsg" style="margin-top:6px"></div>
        </div>
      </div>`;
  }catch(e){
    $("pres").innerHTML = `<span class="err">[错误] 请求失败: ${esc(e)}</span>`;
  }
}

async function customReq(){
  const hex = $("qhex").value.trim().replace("#", "");
  const region = $("qregion").value;
  try{
    const r = await (await fetch("/api/products/custom", {method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({hex, region, note: "产品库页申请"})})).json();
    $("custommsg").innerHTML = r.ok
      ? '<span style="color:#7de0a6">✓ ' + esc(r.results.message) + '</span>'
      : '<span class="err">' + esc(r.error) + '</span>';
    if(r.ok) loadCustom();
  }catch(e){
    $("custommsg").innerHTML = '<span class="err">登记失败</span>';
  }
}

async function loadCustom(){
  try{
    const r = await (await fetch("/api/products/custom/list")).json();
    if(!r.ok || !r.results.count){
      $("customlist").innerHTML = '暂无定制申请——在试妆页遇到「无接近现货」时，可一键提交；申请记录会出现在这里。';
      return;
    }
    const RN = { lip: "唇妆", foundation: "粉底", eyeshadow: "眼影", brow: "眉妆", blush: "腮红" };
    const IMGS = { lip: "/assets/lipstick_placeholder.jpg", foundation: "/assets/foundation_placeholder.jpg",
                   eyeshadow: "/assets/eyeshadow_placeholder.jpg", blush: "/assets/blush_placeholder.jpg",
                   brow: "/assets/lipstick_placeholder.jpg" };
    $("customlist").innerHTML = '<div class="tl">' + r.results.records.map(rec => `
      <div class="tl-item">
        <img class="tl-img" src="${esc(IMGS[rec.region] || IMGS.lip)}" alt="${esc(RN[rec.region] || rec.region)}">
        <div class="tl-tx">
          <span class="tl-sw" style="background:#${esc(rec.hex)}"></span>
          <span class="tl-tag">${esc(RN[rec.region] || rec.region || "定制")}</span>
          <b>#${esc(rec.hex)}</b> <span class="meta">${esc(rec.ts)}</span>
          ${rec.note ? '<div class="meta" style="margin-top:2px">' + esc(rec.note) + '</div>' : ""}
        </div>
        <button class="tl-cancel" onclick="cancelCustom('${esc(rec.hex)}','${esc(rec.region)}','${esc(rec.ts)}')">取消</button>
      </div>`).join("") + '</div>';
  }catch(e){ $("customlist").textContent = "读取失败"; }
}

/* def 18h · 取消定制申请：调后端删除记录并重载时间线 */
async function cancelCustom(hex, region, ts){
  try{
    const r = await (await fetch(`/api/products/custom/cancel?hex=${encodeURIComponent(hex)}&region=${encodeURIComponent(region)}&ts=${encodeURIComponent(ts)}`,
      {method: "POST"})).json();
    if(!r.ok){ $("customlist").insertAdjacentHTML("beforeend", `<span class="err">${esc(r.error)}</span>`); return; }
    loadCustom();
  }catch(e){ $("customlist").insertAdjacentHTML("beforeend", '<span class="err">取消失败</span>'); }
}

/* def 18d · 商品橱窗：品类多窗口 → 详情弹层（紧凑色盘 + 配比/成分表占位） */
let CATALOG = [];

/* def 18f · 橱窗按品类分区渲染（唇妆/粉底/眼影/腮红），色库列表不再上主页面 */
const CAT_NAME = { lip: "唇妆", foundation: "粉底", eyeshadow: "眼影", blush: "腮红", brow: "眉妆" };

async function loadCatalog(){
  try{
    const r = await (await fetch("/api/products/catalog")).json();
    if(!r.ok){ $("shop").innerHTML = `<span class="err">${esc(r.error)}</span>`; return; }
    CATALOG = r.results.items;
    const groups = [];
    CATALOG.forEach(it => {
      let g = groups.find(x => x.cat === it.category);
      if(!g){ g = {cat: it.category, items: []}; groups.push(g); }
      g.items.push(it);
    });
    $("shop").innerHTML = groups.map(g => `
      <div class="shop-cat">
        <div class="shop-cat-head"><b>${esc(CAT_NAME[g.cat] || g.cat)}</b>
        <span class="meta">${esc(g.cat.toUpperCase())} · ${g.items.length} 款 · ${g.items.reduce((n, x) => n + x.count, 0)} 色</span></div>
        <div class="shopgrid">${g.items.map(it => `
          <button class="shopcard" onclick="openItem('${esc(it.id)}')">
            <span class="shopimg"><img src="${esc(it.img)}" alt="${esc(it.name)}"></span>
            <span class="shoptx"><b>${esc(it.name)}</b>
            <span class="meta">${it.count} 色</span>
            <span class="meta">${esc(it.desc)}</span></span>
          </button>`).join("")}</div>
      </div>`).join("");
  }catch(e){ $("shop").innerHTML = '<span class="err">橱窗加载失败</span>'; }
}

function openItem(id){
  const it = CATALOG.find(x => x.id === id);
  if(!it) return;
  const shades = it.shades.map(s => `<button class="swcell" style="background:#${esc(s.hex)}" data-name="${esc(s.name)} · #${esc(s.hex)}"
      onclick="pickShade('${esc(it.id)}','${esc(s.hex)}',this)"></button>`).join("");
  const selrow = `<div class="pd-selrow"><span class="meta">已选</span><b id="pd-selname" class="pd-selnone">未选择——点击右侧色盘</b></div>`;
  const foot = `<div class="pd-foot">
      <b class="pd-sec2">配比资料</b>
      <div class="meta">${esc(it.ratio)}</div>
      <b class="pd-sec2">成分表</b>
      <div class="meta">${esc(it.ingredients)}</div>
      <div class="meta" style="margin-top:10px;opacity:.85">※ v3 计划：此处接入「询问 AI 是否健康 / 成分表的作用」——基于成分表做个性化解读。</div>
    </div>`;
  $("pdbody").innerHTML = `
    <div class="pd-cols">
      <div class="pd-left"><img src="${esc(it.img)}" alt="${esc(it.name)}"></div>
      <div class="pd-right">
        <b class="pd-title">${esc(it.name)}</b>
        <div class="meta">${esc(it.desc)}</div>
        ${selrow}
        <div class="pd-sec">颜色 <span class="meta">（${it.count} 色 · 鼠标悬停查看色名）</span></div>
        <div class="shade-grid">${shades}</div>
      </div>
    </div>
    ${foot}`;
  $("pdoverlay").hidden = false;
}

function pickShade(id, hex, el){
  const it = CATALOG.find(x => x.id === id);
  const s = it.shades.find(x => x.hex.toLowerCase() === hex.toLowerCase());
  if(!s) return;
  $("pd-selname").innerHTML =
    `<span style="display:inline-block;width:13px;height:13px;border-radius:3px;vertical-align:-2px;border:1px solid rgba(255,255,255,.5);background:#${esc(hex)}"></span> ` +
    `${esc(s.name)} <span class="meta">#${esc(hex)}${s.brand ? " · " + esc(s.brand) : ""}</span>`;
  document.querySelectorAll(".swcell.cur").forEach(x => x.classList.remove("cur"));
  el.classList.add("cur");
}

function closeItem(){ $("pdoverlay").hidden = true; }
$("pdoverlay").addEventListener("click", e => { if(e.target.id === "pdoverlay") closeItem(); });

(function init(){
  $("qbtn").addEventListener("click", doQuery);
  $("qhex").addEventListener("keydown", e => { if(e.key === "Enter") doQuery(); });
  loadCatalog(); loadCustom();
  /* def 18c+ · 试妆页一键提交后跳转而来：定位定制时间线并高亮 */
  if(location.hash === "#custom"){
    const el = $("card-custom");
    if(el){ setTimeout(() => { el.scrollIntoView({behavior: "smooth"}); el.classList.add("card-flash"); }, 300); }
  }
  const q = new URLSearchParams(location.search);
  const hx = (q.get("hex") || "").trim();
  const rg = q.get("region");
  if(hx){ $("qhex").value = hx.startsWith("#") ? hx : "#" + hx; }
  if(rg === "lip" || rg === "foundation"){ $("qregion").value = rg; }
  if(hx){ doQuery(); }
})();
