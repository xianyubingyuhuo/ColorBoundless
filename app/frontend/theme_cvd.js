/* def 17c · R-06 全站配色联动（用户 2026-09-11 定稿：双模式开关，交由用户自选）
 * 三模式：correct（校色补偿）/ simulate（模拟该用户视角）/ off（恢复原色）
 * 数据源：/api/cvd/exam/profile 的 calibration——旅程第二步"校色选择"的产物。
 * 数学与 Python 端 cvd_matrix.py 严格同源：Machado 2009 完全型矩阵 + severity 线性插值，
 * 严格作用于线性 RGB 空间（sRGB gamma 展开/压缩公式逐字一致，selftest 22/22 同源背书）。
 * 校色（correct）= 残差补偿式 daltonize：把"该用户会丢失的色差"预补偿进显示色，
 *   使 TA 看到的页面色差接近正常视觉的原始色差（最小改动近似，与试妆反解同思想）。
 * 模拟（simulate）= 正变换：让普通视觉用户看到"该用户眼中的网站"（共情演示）。
 */
(function () {
  if (window.__cvd_theme) return;
  window.__cvd_theme = true;

  /* Machado 2009 完全型矩阵（severity=1.0，线性 RGB），与 cvd_matrix._M_FULL 逐值一致 */
  const M_FULL = {
    protan: [[0.152286, 1.052583, -0.204868],
             [0.114503, 0.786281, 0.099216],
             [-0.003882, -0.048116, 1.051998]],
    deutan: [[0.367322, 0.860646, -0.227968],
             [0.280085, 0.672501, 0.047413],
             [-0.011820, 0.042940, 0.968881]],
    tritan: [[1.255528, -0.076749, -0.178779],
             [-0.078411, 0.930809, 0.147602],
             [0.004733, 0.691367, 0.303900]],
    /* def 40 · uncertain 中性增强（对称红绿轴拉伸，方向无关）：
       R'=R+0.45(R−G)，G'=G+0.2973·0.45·(G−R)（系数比 0.2126:0.7152 → Y 亮度严格恒定），黄轴不动。
       红绿色差线性域放大约 1.58 倍——不假定缺陷方向，红色盲/绿色盲双向受益，也不会补错方向。 */
    uncertain: [[1.45, -0.45, 0],
                [-0.1338, 1.1338, 0],
                [0, 0, 1]],
  };

  /* sRGB gamma（与 color_diff._srgb_to_linear/_linear_to_srgb 公式一致） */
  const s2l = (c) => { c /= 255; return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
  const l2s = (c) => { c = c <= 0.0031308 ? c * 12.92 : 1.055 * Math.pow(Math.max(c, 0), 1 / 2.4) - 0.055;
                       return Math.round(Math.min(255, Math.max(0, c * 255))); };
  const matFor = (kind, sev) => {
    const m = M_FULL[kind];
    if (!m) return null;
    const s = Math.min(1, Math.max(0, Number(sev) || 0));
    return m.map((row, i) => row.map((v, j) => (1 - s) * (i === j ? 1 : 0) + s * v));  // (1-s)I + sM
  };
  const matVec = (m, lin) => [0, 1, 2].map((i) => lin[0] * m[i][0] + lin[1] * m[i][1] + lin[2] * m[i][2]);

  function simRGB(rgb, kind, sev) {
    const m = matFor(kind, sev);
    if (!m) return rgb.slice();
    return matVec(m, rgb.map(s2l)).map(l2s);
  }
  function transformRGB(rgb, mode, kind, sev) {
    /* def 40 · uncertain 走正向中性增强：方向未知时残差补偿（2I−M）会反向缩小色差，
       必须绕开 correct 的反推式，直接正向拉开红绿轴（severity 同样插值） */
    if (kind === "uncertain") return simRGB(rgb, "uncertain", sev);
    if (mode === "simulate") return simRGB(rgb, kind, sev);
    if (mode === "correct") {
      const m = matFor(kind, sev);
      if (!m) return rgb.slice();
      const lin = rgb.map(s2l);
      const sim = matVec(m, lin);
      /* 残差补偿：corrected = linear + (linear − simulate) —— 丢失的色差预加回 */
      return [0, 1, 2].map((i) => l2s(Math.min(1, Math.max(0, lin[i] + (lin[i] - sim[i])))));
    }
    return rgb.slice();
  }

  /* 主题清单（与 style.css :root / body 背景同源；rgba 仅变换 rgb 分量，alpha 保留） */
  const VARS = [
    { name: "--ac",  css: "#e5476d" },
    { name: "--ac2", css: "#ff9ab5" },
    { name: "--tx",  css: "#ece7e4" },
    { name: "--tx2", rgb: [236, 231, 228], alpha: 0.55 },
    { name: "--bd",  rgb: [255, 255, 255], alpha: 0.11 },
    { name: "--vio", css: "#7654ff" },   /* def 31 · 紫/橙装饰色入变量池（style.css 已 var 化，校色时跟随变换） */
    { name: "--org", css: "#ff9650" },
  ];
  const BG_SPOTS = [
    { rgb: [229, 71, 109],  a: 0.30, w: 560, h: 380, at: "10% 4%",  end: "62%" },
    { rgb: [118, 84, 255],  a: 0.26, w: 640, h: 430, at: "92% 16%", end: "62%" },
    { rgb: [255, 150, 80],  a: 0.15, w: 560, h: 440, at: "50% 98%", end: "60%" },
  ];
  const BG_BASE = ["#181220", "#1e1424", "#120f1a"];

  const hexParts = (css) => { const h = css.replace("#", "");
    return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)]; };
  const toHex = (rgb) => "#" + rgb.map((v) => v.toString(16).padStart(2, "0")).join("");

  function applyTheme(mode, kind, sev) {
    /* def 30 · 返回 {applied, reason}：kind 不在矩阵表（如 uncertain）时数学上只能恒等——
       如实上报"未应用"，让调用方（cvd.js）给人话反馈，而不是默默 reset 假装成功 */
    if (mode === "off") { resetTheme(); return { applied: false, reason: "off" }; }
    if (!M_FULL[kind]) { resetTheme(); return { applied: false, reason: "kind_unsupported" }; }
    const root = document.documentElement.style;
    VARS.forEach((v) => {
      const t = transformRGB(v.rgb || hexParts(v.css), mode, kind, sev);
      root.setProperty(v.name,
        v.alpha !== undefined ? `rgba(${t[0]},${t[1]},${t[2]},${v.alpha})` : toHex(t));
    });
    const spots = BG_SPOTS.map((s) => {
      const t = transformRGB(s.rgb, mode, kind, sev);
      return `radial-gradient(${s.w}px ${s.h}px at ${s.at},rgba(${t[0]},${t[1]},${t[2]},${s.a}),transparent ${s.end}%)`;
    }).join(",");
    const base = BG_BASE.map((c) => toHex(transformRGB(hexParts(c), mode, kind, sev)));
    document.body.style.background =
      `${spots},linear-gradient(158deg,${base[0]} 0%,${base[1]} 46%,${base[2]} 100%)`;
    document.body.style.backgroundAttachment = "fixed";
    /* def 42 · 色盘/照片蒙同源矩阵滤镜（canvas 与照片像素不吃 CSS 变量） */
    const mm = mediaMatrix(mode, kind, sev);
    if(mm){
      ensureFilter(mm);
      filterOn = true;
      startObserver();
      paintMedia();
    }
    return { applied: true, reason: "" };
  }
  function resetTheme() {
    const root = document.documentElement.style;
    VARS.forEach((v) => root.removeProperty(v.name));
    document.body.style.background = "";
    document.body.style.backgroundAttachment = "";
    /* def 42 · 摘下色盘/照片滤镜，回归原色 */
    filterOn = false;
    document.querySelectorAll(MEDIA_Q).forEach((el) => { el.style.filter = ""; });
    /* def 53 · SVG 滤镜定义一并移除——复位后与"从未开启"状态完全一致（节点虽不可见，
       但残留会让自动化采样/状态判断误认为滤镜仍生效） */
    const svg = document.getElementById("cvdmat-svg");
    if(svg && svg.parentNode) svg.parentNode.removeChild(svg);
  }

  /* ==== def 42 · 色盘/照片矩阵滤镜（用户 2026-09-21：校色要覆盖色盘和上传的照片） ====
     CSS 变量重写覆盖不到 canvas 像素（色盘 #uniwall）与照片 <img>（试妆上传预览 #upzone img、
     结果图 .imgbox img）。SVG feColorMatrix（color-interpolation-filters="linearRGB"）让浏览器
     自动做 sRGB↔线性解码/编码后在线性 RGB 域乘矩阵——与 transformRGB 严格同源（Machado 同域），
     GPU 加速零逐像素成本；correct 残差补偿 2I−M 与 simulate/uncertain 都是线性矩阵，全部可表达。 */
  const MEDIA_SEL = ["#uniwall", "#upzone img", ".imgbox img"];
  const MEDIA_Q = MEDIA_SEL.join(",");
  let filterOn = false, moStarted = false;

  function mediaMatrix(mode, kind, sev){
    const m0 = M_FULL[kind];
    if(!m0) return null;
    const s = Math.min(1, Math.max(0, Number(sev) || 0));
    /* 三种语义归一为一个线性域 3x3：
       simulate / uncertain → (1−s)I + sM（正向）；correct → (1+s)I − sM（= 2I − M_sev 残差补偿展开） */
    const sign = (kind === "uncertain" || mode === "simulate") ? s : -s;
    return m0.map((row, i) => row.map((v, j) => (i === j ? 1 + sign * v : sign * v)));
  }
  function ensureFilter(m){
    let svg = document.getElementById("cvdmat-svg");
    if(!svg){
      const NS = "http://www.w3.org/2000/svg";
      svg = document.createElementNS(NS, "svg");
      svg.id = "cvdmat-svg";
      svg.setAttribute("width", "0"); svg.setAttribute("height", "0");
      svg.style.cssText = "position:absolute;width:0;height:0";
      const f = document.createElementNS(NS, "filter");
      f.id = "cvdmat";
      f.setAttribute("color-interpolation-filters", "linearRGB");   /* 线性域 = 与 transformRGB 同域 */
      const fm = document.createElementNS(NS, "feColorMatrix");
      fm.setAttribute("type", "matrix");
      fm.id = "cvdmat-fm";
      f.appendChild(fm); svg.appendChild(f);
      (document.body || document.documentElement).appendChild(svg);
    }
    const vals = [
      m[0][0], m[0][1], m[0][2], 0, 0,
      m[1][0], m[1][1], m[1][2], 0, 0,
      m[2][0], m[2][1], m[2][2], 0, 0,
      0, 0, 0, 1, 0,                                   /* alpha 恒等：照片透明度不受影响 */
    ].map((v) => +v.toFixed(6)).join(" ");
    document.getElementById("cvdmat-fm").setAttribute("values", vals);
  }
  function paintMedia(){
    document.querySelectorAll(MEDIA_Q).forEach((el) => { el.style.filter = "url(#cvdmat)"; });
  }
  function startObserver(){
    if(moStarted) return;
    moStarted = true;
    /* 试妆照片（上传预览/结果图）是后插入的动态节点—— observer 捕获新增，主题激活时自动挂滤镜；
       石原测评图、verify 模拟预览图等不在 MEDIA_SEL，刻意不蒙（测评刺激图与二次模拟图必须保持原样）。 */
    new MutationObserver((muts) => {
      if(!filterOn) return;
      muts.forEach((mu) => (mu.addedNodes || []).forEach((n) => {
        if(n.nodeType !== 1) return;
        if(n.matches && n.matches(MEDIA_Q)) n.style.filter = "url(#cvdmat)";
        if(n.querySelectorAll) n.querySelectorAll(MEDIA_Q).forEach((el) => { el.style.filter = "url(#cvdmat)"; });
      }));
    }).observe(document.body || document.documentElement, { childList: true, subtree: true });
  }

  /* ==== def 41 · 配色纯会话手动模式（用户 2026-09-21 定稿：默认进入 = 无色盲原色） ====
     会话标记 sessionStorage.cvd_theme = 用户本会话主动开启的状态（开关校色 / 模拟演示），
     是配色跨页/刷新的唯一真相源；档案 calibration 只喂试妆反解等后端管线，不再驱动页面配色。 */
  function getSession(){
    try { const s = sessionStorage.getItem("cvd_theme"); return s ? JSON.parse(s) : null; }
    catch (e) { return null; }
  }
  function setSession(state){
    try { state ? sessionStorage.setItem("cvd_theme", JSON.stringify(state)) : sessionStorage.removeItem("cvd_theme"); }
    catch (e) { /* 隐私模式等：标记失败仅影响跨页保留，本页配色不受影响 */ }
  }
  (async () => {
    try {
      const q = new URLSearchParams(location.search);
      const sim = q.get("cvdsim");           /* def 31 · ?cvdsim=deutan|protan|tritan 直达视角演示
                                                 （评委演示/调试用，优先级最高；?cvdsev=0.5 调严重度、
                                                 ?cvdmode=correct 看校色补偿态） */
      if (sim && M_FULL[sim]){
        const sev = Math.min(1, Math.max(0, parseFloat(q.get("cvdsev")) || 1.0));
        const md = q.get("cvdmode") === "correct" ? "correct" : "simulate";
        applyTheme(md, sim, sev);
        window.__cvd_url_sim = true;   /* def 33 · 演示优先锁 */
        return;
      }
      const st = getSession();
      if (st && st.mode && st.kind && M_FULL[st.kind]) applyTheme(st.mode, st.kind, st.sev);   /* 只恢复用户本会话点过的 */
      /* 无标记 → 保持原色（默认无色盲，不再读档案自动上色） */
    } catch (e) { /* 异常：保持原色 */ }
  })();

  window.CVDTheme = { apply: applyTheme, reset: resetTheme, hasKind: (k) => !!M_FULL[k],
                      getSession, setSession }; /* def 39/41 · hasKind + 会话标记 API（单一真相源） */
})();
