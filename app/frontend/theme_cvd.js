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
    if (mode === "off" || !M_FULL[kind]) { resetTheme(); return; }
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
  }
  function resetTheme() {
    const root = document.documentElement.style;
    VARS.forEach((v) => root.removeProperty(v.name));
    document.body.style.background = "";
    document.body.style.backgroundAttachment = "";
  }

  /* 加载即恢复：档案里有校色状态且非 off → 全站自动应用（试妆/选色页同样生效） */
  (async () => {
    try {
      const p = await (await fetch("/api/cvd/exam/profile")).json();
      if (p.ok) {
        const cal = (p.results || {}).calibration;
        if (cal && cal.mode && cal.mode !== "off" && M_FULL[cal.kind]) {
          applyTheme(cal.mode, cal.kind, cal.severity);
        }
      }
    } catch (e) { /* 档案服务未响应：保持原色 */ }
  })();

  window.CVDTheme = { apply: applyTheme, reset: resetTheme };
})();
