/* index 页逻辑（自 index.html 拆出，改交互只动这个小文件） */
/* 幻灯片轮播（原生零依赖）：默认播 3 个占位帧；slides/0N.jpg 存在则动态接管对应帧 */
(function(){
  const slides = document.getElementById("slides");
  const dotsBox = document.getElementById("dots");
  let order = Array.from(slides.querySelectorAll(".slide-ph"));

  // 尝试加载真实图片：成功则插入并顶替对应占位帧，失败静默保留占位
  for (let i = 0; i < order.length; i++) {
    const im = new Image();
    im.src = `slides/0${i + 1}.jpg`;
    im.alt = `slide ${i + 1}`;
    im.addEventListener("load", () => {
      slides.insertBefore(im, order[i]);          // 叠在占位帧上层
      order[order.indexOf(order[i])] = im;        // 轮播序列换用真图
      refreshDots(); show(idx);
    });
  }

  let idx = 0;
  let dots = [];
  function refreshDots(){
    dotsBox.innerHTML = "";
    dots = order.map((_, i) => {
      const b = document.createElement("button");
      b.title = `第 ${i + 1} 帧`;
      b.addEventListener("click", () => { idx = i; show(idx); });
      dotsBox.appendChild(b);
      return b;
    });
  }
  function show(n){
    order.forEach((f, i) => f.classList.toggle("cur", i === n));
    dots.forEach((d, i) => d.classList.toggle("cur", i === n));
  }
  refreshDots(); show(0);
  setInterval(() => { idx = (idx + 1) % order.length; show(idx); }, 5000);
})();
