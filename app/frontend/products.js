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
    const n = r.results.nearest, av = r.results.available;
    $("pres").innerHTML = `
      <div class="match-card">
        <span class="sw" style="background:#${esc(n.hex)}"></span>
        <div style="min-width:0">
          <div><b>${esc(n.brand)}</b> · ${esc(n.product)}</div>
          <div class="meta">#${esc(n.hex)} · ΔE=${esc(n.dE)} · 阈值 ${esc(r.query.threshold_dE)}（CIEDE2000）</div>
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

async function loadLists(){
  try{
    const r = await (await fetch("/api/products/list?region=lip")).json();
    if(r.ok){
      $("lipn").textContent = r.results.count;
      $("lipgrid").innerHTML = r.results.items.map(it => `
        <div class="pitem"><span class="sw" style="background:#${esc(it.hex)}"></span>
        <div class="tx"><b>${esc(it.product)}</b><span class="meta">#${esc(it.hex)} · ${esc(it.tone || "")}</span>
        <span class="meta">${esc(it.desc || "")}</span></div></div>`).join("");
    } else { $("lipgrid").innerHTML = `<span class="err">${esc(r.error)}</span>`; }
  }catch(e){ $("lipgrid").innerHTML = '<span class="err">加载失败</span>'; }
  try{
    const r = await (await fetch("/api/products/list?region=foundation")).json();
    if(r.ok){
      $("fdn").textContent = r.results.count;
      $("fdgrid").innerHTML = r.results.items.map(it => `
        <div class="pitem"><span class="sw" style="background:#${esc(it.hex)}"></span>
        <div class="tx"><b>${esc(it.brand)}</b><span class="meta">${esc(it.product)}</span>
        <span class="meta">#${esc(it.hex)} · L${esc(it.L)}</span></div></div>`).join("");
    } else { $("fdgrid").innerHTML = `<span class="err">${esc(r.error)}</span>`; }
  }catch(e){ $("fdgrid").innerHTML = '<span class="err">加载失败</span>'; }
}

async function loadCustom(){
  try{
    const r = await (await fetch("/api/products/custom/list")).json();
    if(!r.ok || !r.results.count){
      $("customlist").innerHTML = '暂无定制申请——在上方查询器遇到「无接近现货」时，可以一键登记；申请记录会出现在这里。';
      return;
    }
    $("customlist").innerHTML = '<div class="tl">' + r.results.records.map(rec => `
      <div class="tl-item"><span style="display:inline-block;width:16px;height:16px;border-radius:4px;vertical-align:-3px;border:1px solid rgba(255,255,255,.4);background:#${esc(rec.hex)}"></span>
      <b>#${esc(rec.hex)}</b> · ${esc(rec.region)} · <span class="meta">${esc(rec.ts)}</span>
      ${rec.note ? '<div class="meta">备注：' + esc(rec.note) + '</div>' : ""}</div>`).join("") + '</div>';
  }catch(e){ $("customlist").textContent = "读取失败"; }
}

(function init(){
  $("qbtn").addEventListener("click", doQuery);
  $("qhex").addEventListener("keydown", e => { if(e.key === "Enter") doQuery(); });
  loadLists(); loadCustom();
  const q = new URLSearchParams(location.search);
  const hx = (q.get("hex") || "").trim();
  const rg = q.get("region");
  if(hx){ $("qhex").value = hx.startsWith("#") ? hx : "#" + hx; }
  if(rg === "lip" || rg === "foundation"){ $("qregion").value = rg; }
  if(hx){ doQuery(); }
})();
