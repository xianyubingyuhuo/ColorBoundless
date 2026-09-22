/* ==== def 39 · 全站校色开关组件（calswitch.js） ====
   问题：校色开关原本只存在于 cvd.html 头部——切到选色/试妆/产品库页开关「消失」；
   且 uncertain 档案下配色恢复是数学边界（Machado 矩阵表无 uncertain），其他页面无任何
   解释，用户感知为「校色丢失」。本组件在所有 site-head 页面注入同一开关，语义与 cvd 页
   完全一致（def 34：开关 = 唯一启停；导入配置仍在「档案与校色」）。
   cvd.html 已有原生开关（带 calstatus 提示区），组件检测到 .cal-switch 即退出不重复注入。 */
(function () {
  if (window.__cvd_calswitch) return;
  window.__cvd_calswitch = true;
  if (document.querySelector(".cal-switch")) return;   /* cvd 页有原生开关，跳过 */

  let cal = null, busy = false, toastTm = null;

  const head = document.querySelector(".site-head");
  if (!head) return;
  const el = document.createElement("div");
  el.className = "cal-switch";
  el.title = "切换校色配色（需已完成测评）——与「色盲校验」页顶部开关同源，全站生效";
  el.innerHTML = '<span class="cal-label">校色配色</span><div class="cal-track"><div class="cal-knob"></div></div>';
  el.addEventListener("click", toggle);
  const nav = head.querySelector(".nav-x");
  head.insertBefore(el, nav || null);

  /* 轻提示：3.2s 自动消失，零圆角风格 */
  function toast(msg, isErr){
    let t = document.getElementById("cal-toast");
    if (!t){
      t = document.createElement("div");
      t.id = "cal-toast";
      t.style.cssText = "position:fixed;left:50%;bottom:26px;transform:translateX(-50%);z-index:9999;" +
        "background:rgba(24,18,32,.96);border:1px solid var(--bd);color:var(--tx);padding:9px 16px;" +
        "font-size:13px;line-height:1.7;max-width:540px;box-shadow:0 10px 30px rgba(0,0,0,.5);" +
        "pointer-events:none;transition:opacity .3s";
      document.body.appendChild(t);
    }
    t.innerHTML = msg;
    t.style.borderColor = isErr ? "rgb(from var(--ac) r g b / .7)" : "var(--bd)";
    t.style.opacity = "1";
    clearTimeout(toastTm);
    toastTm = setTimeout(() => { t.style.opacity = "0"; }, 3200);
  }

  /* def 41 · 启停 = 会话标记（sessionStorage.cvd_theme）：新会话默认 off = 原色；
     档案 enabled 仅存档。开关初始态同步可读，无需等 fetch。 */
  const isOn = () => !!(window.CVDTheme && window.CVDTheme.getSession && window.CVDTheme.getSession());
  function render(){ el.classList.toggle("on", isOn()); }

  const UNCERTAIN_NOTE = "您的档案类型校色引擎暂不支持页面补偿（类型未定时的保守口径）。试妆反解与守门功能仍正常使用档案；可到「色盲校验」页重新测评获取明确类型。";

  async function toggle(){
    if (busy) return;
    busy = true;
    const prev = (window.CVDTheme && window.CVDTheme.getSession) ? window.CVDTheme.getSession() : null;
    try{
      const turningOn = !isOn();
      if (turningOn && !cal){ toast("暂无测评档案——请先在「色盲校验」页完成 22 题测评", true); return; }
      const locked = !!window.__cvd_url_sim;
      /* def 41 · 会话标记本地先写（启停真相源），POST 仅同步档案存档；URL 演示锁下不动标记 */
      if (window.CVDTheme && window.CVDTheme.setSession && !locked){
        if (turningOn) window.CVDTheme.setSession({mode: cal.mode, kind: cal.kind, sev: cal.severity});
        else window.CVDTheme.setSession(null);
      }
      const r = await (await fetch("/api/cvd/exam/calibrate", { method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: turningOn }) })).json();
      if (!r.ok){
        if (window.CVDTheme && window.CVDTheme.setSession && !locked) window.CVDTheme.setSession(prev);  /* 失败回滚 */
        toast("[错误] " + (r.error || "请求失败"), true); return;
      }
      cal = r.results.calibration;
      render();
      if (locked){ toast("开关已切换，但页面配色当前由 URL 演示参数（?cvdsim=…）接管，保持演示态"); return; }
      if (window.CVDTheme){
        if (turningOn){
          const res = window.CVDTheme.apply(cal.mode, cal.kind, cal.severity);
          if (!res.applied && res.reason === "kind_unsupported") toast(UNCERTAIN_NOTE);
          else toast(cal.kind === "uncertain"
            ? "校色配色已开启——档案类型未定型，已启用对称红绿增强（不假定方向、亮度保持）；本会话内跨页保留，关闭浏览器后默认恢复原色"
            : "校色配色已开启——全站按校色配置上色；本会话内跨页保留，关闭浏览器后默认恢复原色");
        }else{
          window.CVDTheme.reset();
          toast("校色配色已关闭——全站恢复原色（导入的配置保留，随时可再开）");
        }
      }
    }catch(e){
      if (window.CVDTheme && window.CVDTheme.setSession) window.CVDTheme.setSession(prev);  /* 异常回滚 */
      toast("[错误] 请求失败: " + e, true);
    }
    finally{ busy = false; }
  }

  /* 初始化：开关态先按会话标记即时渲染（同步，新会话默认 off = 原色）；
     档案仅补充 toggle 所需的 kind/mode/severity，不再驱动 UI/配色（def 41）。 */
  render();
  (async () => {
    try{
      const p = await (await fetch("/api/cvd/exam/profile")).json();
      if (p.ok){
        cal = (p.results || {}).calibration || null;
        if (isOn() && cal && cal.kind === "uncertain" && !sessionStorage.getItem("cal_uncertain_note")){
          toast("已恢复本会话配色：档案类型未定型，当前为对称红绿增强（不假定方向、亮度保持）");
          sessionStorage.setItem("cal_uncertain_note", "1");
        }
      }
    }catch(e){ /* 档案服务未响应：开关仍按会话标记工作；无标记时点击会提示先测评 */ }
  })();
})();