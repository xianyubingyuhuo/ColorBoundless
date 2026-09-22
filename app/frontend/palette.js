/* palette 页逻辑（自 palette.html 拆出，改交互只动这个小文件） */
const $ = id => document.getElementById(id);
async function getJSON(url){const t0=performance.now();const r=await fetch(url);const j=await r.json();return{j,ms:Math.round(performance.now()-t0)}}

async function t1(){
  const hex = encodeURIComponent($("s1hex").value), k = $("s1k").value;
  $("s1res").innerHTML = `<div class="meta">查询中（判定库 = 官方色号 + 已导入商品色）…</div>`;
  try{
    const{j, ms} = await getJSON(`/api/tools/search_shade?hex=${hex}&top_k=${k}`);
    $("s1ms").textContent = `官方库 ${ms}ms`;
    $("s1json").textContent = JSON.stringify(j, null, 2);
    if(!j.ok){
      /* 防御：把真实响应打进错误区，便于定位（正常不应触发） */
      $("s1res").innerHTML = `<span class="err">[错误] ${j.error || "后端返回异常结构（请展开下方调试信息）"}</span>` +
        `<details><summary>调试信息（点击展开，截图发我）</summary><pre>${JSON.stringify(j).slice(0, 600)}</pre></details>`;
      return;
    }

    /* 分区零：GB/T 15608 近似命名（R-07 · 现阶段标注体系） */
    const gbLine = j.query && j.query.gb_cn
      ? `<div class="item"><div><b>GB/T 15608 近似命名：${j.query.gb_cn}</b>　` +
        `<span class="meta">标号 ${j.query.gb_label}</span>` +
        `<div class="meta">（近似换算；精确标号以《中国颜色体系》国家标准样册为准）</div></div></div>` : "";

    /* 商品可提供性（def 18r · 全域恒真行已删）：有 → 命中清单；无 → 定制提示 */
    const tip = j.query.has_official ? "" :
      `<div class="item" style="border-color:rgba(255,154,181,.5)"><div><b>暂无商品色可提供</b>` +
      `<div class="meta">判定库 ${j.query.pool_size || "—"} 条（官方色号 + 已导入商品色）中无 dE≤1.0 的颜色——此色可走定制申请（口红/眼影/粉底任意色）</div></div></div>`;

    /* 只列官方命中条目（dE≤1.0）——"最近替代"与"全库精确匹配"已按需求移除（def 18j） */
    const hitList = j.results.filter(r => r.dE <= 1).map(r =>
      `<div class="item"><span class="sw" style="background:#${r.hex}"></span>` +
      `<div><b>#${r.hex}</b>　${r.name ? `<span style="color:#c4475d">${r.name}</span>` : ""}${r.tone ? `　<span class="meta">[${r.tone}]</span>` : ""}` +
      `<div class="meta">dE=${r.dE} · ${r.desc || (r.imported ? "已导入商品色" : "官方色号")}</div></div>` +
      `<span style="margin-left:auto;flex:none;font-size:12px;color:#7de0a6">商品有 ✓</span></div>`).join("");

    $("s1res").innerHTML = gbLine + tip + hitList;
    if(window.__uniSetMark) window.__uniSetMark(j.query.hex);   // def 18m · 色盘跳到查询色所在层并高亮（成功后才标记）
  }catch(e){ $("s1res").innerHTML = `<span class="err">[错误] 请求失败: ${e}</span>`; }
}

/* def 18n · 全域色盘：256×256 canvas（横轴 R/纵轴 G）+ B 通道滑轨
   —— 256 层 × 65,536 色 = 16,777,216 全部可显示；绿框标记已导入商品色；
      hover 显示商品归属；点击取色联动查询框；查询后自动跳层+高亮 */
(function(){
  const cv = $("uniwall"), sl = $("unib"), bv = $("unibv"), info = $("unipick");
  const jumpPanel = $("ujpanel"), wrap = $("uniwrap"), home = $("unihome"), fsEl = $("unifs"), zlbl = $("uzlbl");
  if(!cv || !sl || !wrap) return;
  const ctx = cv.getContext("2d");                   // def 18q 修复：此前编辑丢失的两行（img 未定义 → 色盘全黑）
  const img = ctx.createImageData(256, 256);
  let FS = false, Z = 1, TX = 0, TY = 0;             // def 18q · 全屏标志/缩放/平移（canvas CSS px）
  let CMP = null;                                   // {byHex: Map<hex, 归属文本>, byB: Map<层, [hex]>}
  function layerTip(b){
    const n = CMP ? (CMP.byB.get(b) || []).length : 0;
    let near = 0;
    if(CMP) [b - 1, b + 1, b - 2, b + 2].forEach(bb => {
      if(bb >= 0 && bb <= 255) near += (CMP.byB.get(bb) || []).length;
    });
    return "本层商品色 " + n + "（绿框）· 附近 ±2 层 " + near + "（黄框：实线=±1，虚线=±2）· 点击任意色自动查询";
  }
  function draw(){
    const b = Number(sl.value);
    bv.textContent = "B=" + b;
    const d = img.data;
    for(let g = 0; g < 256; g++){
      const row = g * 256 * 4;
      for(let r = 0; r < 256; r++){
        const i = row + r * 4;
        d[i] = r; d[i+1] = g; d[i+2] = b; d[i+3] = 255;
      }
    }
    ctx.putImageData(img, 0, 0);
    if(CMP){
      (CMP.byB.get(b) || []).forEach(hx => {        // 本层 = 绿框
        const x = parseInt(hx.slice(0,2),16), y = parseInt(hx.slice(2,4),16);
        ctx.strokeStyle = "#7de0a6"; ctx.lineWidth = 1;
        ctx.strokeRect(x - 2.5, y - 2.5, 5, 5);
      });
      [[b - 1, false], [b + 1, false], [b - 2, true], [b + 2, true]].forEach(([bb, far]) => {
        if(bb < 0 || bb > 255) return;              // 附近 ±2 层 = 黄框（虚线=±2）
        ctx.strokeStyle = "#ffd166"; ctx.lineWidth = 1;
        ctx.setLineDash(far ? [3, 3] : []);
        (CMP.byB.get(bb) || []).forEach(hx => {
          const x = parseInt(hx.slice(0,2),16), y = parseInt(hx.slice(2,4),16);
          ctx.strokeRect(x - 2.5, y - 2.5, 5, 5);
        });
      });
      ctx.setLineDash([]);
    }
    info.textContent = layerTip(b);
    if(window.__unimark) mark();
  }
  function mark(){
    const h = window.__unimark;
    if(!/^[0-9a-fA-F]{6}$/.test(h)) return;
    const x = parseInt(h.slice(0,2),16), y = parseInt(h.slice(2,4),16), b = parseInt(h.slice(4,6),16);
    if(b !== Number(sl.value)) return;              // 不在当前层不画框（层由查询自动切）
    ctx.strokeStyle = (x + y) > 255 ? "#000" : "#fff";
    ctx.lineWidth = 1.5;
    ctx.strokeRect(x - 4, y - 4, 8, 8);
  }
  function snap(b, r, g){                            // def 18r · 靠近商品色（绿框）自动吸附
    if(!CMP) return null;
    let best = null, bd = 1e9;
    (CMP.byB.get(b) || []).forEach(hx => {
      const x = parseInt(hx.slice(0,2),16), y = parseInt(hx.slice(2,4),16);
      const d2 = (x - r) * (x - r) + (y - g) * (y - g);
      if(d2 < bd){ bd = d2; best = hx; }
    });
    const R = 12;                                    // 吸附半径（色阶）
    return (best && bd <= R * R) ? best : null;
  }
  sl.addEventListener("input", draw);
  cv.addEventListener("mousemove", e => {
    if(!CMP) return;
    const rect = cv.getBoundingClientRect();
    const r = Math.min(255, Math.max(0, Math.round((e.clientX - rect.left) / rect.width * 255)));
    const g = Math.min(255, Math.max(0, Math.round((e.clientY - rect.top) / rect.height * 255)));
    const s = snap(Number(sl.value), r, g);
    if(s){
      info.textContent = "吸附 → #" + s + " · 已导入商品：" + (CMP.byHex.get(s) || "").split("\n").join(" / ");
      return;
    }
    const hx = [r, g, Number(sl.value)].map(v => v.toString(16).padStart(2, "0")).join("").toUpperCase();
    const owned = CMP.byHex.get(hx);
    info.textContent = "#" + hx + (owned ? " · 已导入商品：" + owned.split("\n").join(" / ") : "（非商品色）");
  });
  cv.addEventListener("mouseleave", () => { info.textContent = layerTip(Number(sl.value)); });
  let dragging = false, moved = 0, sx = 0, sy = 0, t0x = 0, t0y = 0;
  cv.addEventListener("mousedown", e => {            // 全屏 z>1：拖拽平移
    moved = 0;
    if(!FS || Z <= 1) return;
    dragging = true; sx = e.clientX; sy = e.clientY; t0x = TX; t0y = TY;
    e.preventDefault();
  });
  window.addEventListener("mousemove", e => {
    if(!dragging) return;
    const dx = e.clientX - sx, dy = e.clientY - sy;
    moved = Math.max(moved, Math.abs(dx) + Math.abs(dy));
    const W = cv.clientWidth || 1, H = cv.clientHeight || W;
    TX = Math.min(W - W / Z, Math.max(0, t0x - dx / Z));
    TY = Math.min(H - H / Z, Math.max(0, t0y - dy / Z));
    applyT();
  });
  window.addEventListener("mouseup", () => { dragging = false; });
  wrap.addEventListener("wheel", e => {              // 全屏：滚轮缩放（以鼠标为中心）
    if(!FS) return;
    e.preventDefault();
    const wrect = wrap.getBoundingClientRect();
    const mx = e.clientX - wrect.left, my = e.clientY - wrect.top;
    const z1 = Math.min(32, Math.max(1, Z * Math.pow(1.0015, -e.deltaY)));
    if(z1 === Z) return;
    const px = TX + mx / Z, py = TY + my / Z;
    Z = z1;
    TX = px - mx / Z; TY = py - my / Z;
    clampT(); applyT();
  }, { passive: false });
  function applyT(){
    cv.style.transform = (FS && Z > 1) ? `scale(${Z}) translate(${-TX}px, ${-TY}px)` : "";
    if(zlbl) zlbl.textContent = Math.round(Z * 100) + "%";
  }
  function clampT(){
    const W = cv.clientWidth || 1, H = cv.clientHeight || W;
    TX = Math.min(W - W / Z, Math.max(0, TX));
    TY = Math.min(H - H / Z, Math.max(0, TY));
  }
  cv.addEventListener("click", e => {
    if(moved > 4) return;                            // 拖拽平移不取色
    const rect = cv.getBoundingClientRect();
    const r = Math.min(255, Math.max(0, Math.round((e.clientX - rect.left) / rect.width * 255)));
    const g = Math.min(255, Math.max(0, Math.round((e.clientY - rect.top) / rect.height * 255)));
    const s = snap(Number(sl.value), r, g);          // def 18r · 靠近商品色自动吸附
    const hx = (s || [r, g, Number(sl.value)].map(v => v.toString(16).padStart(2, "0")).join("")).toUpperCase();
    $("s1hex").value = "#" + hx;
    if(s) info.textContent = "已吸附到商品色 #" + hx + "：" + (CMP.byHex.get(hx) || "").split("\n").join(" / ");
    t1();
  });
  jumpPanel.addEventListener("click", e => e.stopPropagation());
  window.uniStep = d => {                            // def 18p · < > 微调滑轨
    sl.value = Math.min(255, Math.max(0, Number(sl.value) + d));
    draw();
  };
  window.uniZoom = d => {                            // def 18q · 缩放按钮（中心缩放/重置）
    const W = cv.clientWidth || 1, H = cv.clientHeight || W;
    if(d === 0){ Z = 1; TX = 0; TY = 0; }
    else{
      const mx = W / 2, my = H / 2;
      const px = TX + mx / Z, py = TY + my / Z;
      Z = Math.min(32, Math.max(1, d > 0 ? Z * 1.5 : Z / 1.5));
      TX = px - mx / Z; TY = py - my / Z;
    }
    clampT(); applyT();
  };
  window.uniFs = on => {                             // def 18q · 全屏开关（色盘节点整体搬家，状态零丢失）
    FS = on;
    if(on){
      $("fsslot").appendChild(wrap);                 // 搬进全屏槽位
    }else{
      home.insertBefore(wrap, home.children[1] || null);   // 精确回位：标题行之后、滑轨行之前
    }
    fsEl.hidden = !on;
    cv.style.maxWidth = on ? "none" : "512px";
    Z = 1; TX = 0; TY = 0;
    applyT(); draw();
  };
  document.addEventListener("keydown", e => { if(e.key === "Escape" && FS) window.uniFs(false); });
  window.ujToggle = e => { e.stopPropagation(); jumpPanel.hidden = !jumpPanel.hidden; };
  document.addEventListener("click", e => {
    if(!jumpPanel.hidden && !jumpPanel.contains(e.target)) jumpPanel.hidden = true;
  });
  window.__uniSetMark = h => {
    window.__unimark = h;
    if(/^[0-9a-fA-F]{6}$/.test(h)){ sl.value = parseInt(h.slice(4,6),16); }   // 自动跳到查询色所在层
    draw();
  };
  (async () => {                                    // 已导入商品色索引（compare 端点）
    try{
      const j = await (await fetch("/api/products/compare")).json();
      if(!j.ok) return;
      const byHex = new Map(), byB = new Map();
      j.results.swatches.forEach(s => {
        byHex.set(s.hex, s.products_txt);
        const b = parseInt(s.hex.slice(4,6), 16);
        if(!byB.has(b)) byB.set(b, []);
        byB.get(b).push(s.hex);
      });
      CMP = {byHex, byB};
      jumpPanel.innerHTML = "";
      Array.from(byB.keys()).sort((a, c) => a - c).forEach(b => {
        const d = document.createElement("div");
        d.className = "ujitem";
        d.innerHTML = "<b>B=" + b + "</b><span>" + byB.get(b).length + " 色</span>";
        d.onclick = () => { sl.value = b; jumpPanel.hidden = true; draw(); };
        jumpPanel.appendChild(d);
      });
      draw();
    }catch(e){}
  })();
  draw();
})();

/* ==== def 25 · 对比库（全商品色板）浮窗——自产品库页搬入，与商品色吸附同场景 ==== */
let cmpLoaded = false;
async function cmpOpen(){
  document.getElementById("cmpfs").hidden = false;
  if (cmpLoaded) return;
  const grid = document.getElementById("cmpgrid");
  grid.innerHTML = '<span class="meta">加载中……</span>';
  try{
    const j = await (await fetch("/api/products/compare")).json();
    if(!j.ok){ grid.innerHTML = `<span style="color:#ff8a80">[错误] ${j.error}</span>`; return; }
    document.getElementById("cmpn").textContent = `· ${j.results.swatches.length} 色`;
    grid.innerHTML = j.results.swatches.map(s =>
      `<button class="cmpsw${s.official ? " cmp-off" : ""}" style="background:#${s.hex}" data-name="${(s.products_txt || "").replace(/&/g, "&amp;").replace(/"/g, "&quot;")}"></button>`).join("");
    cmpLoaded = true;
  }catch(e){ grid.innerHTML = `<span style="color:#ff8a80">[错误] 请求失败: ${e}</span>`; }
}
function cmpClose(){ document.getElementById("cmpfs").hidden = true; }
document.getElementById("cmpfs").addEventListener("click", e => { if(e.target.id === "cmpfs") cmpClose(); });
document.addEventListener("keydown", e => { if(e.key === "Escape" && !document.getElementById("cmpfs").hidden) cmpClose(); });
if(location.hash === "#cmp") cmpOpen();
