/* products 页逻辑（自 products.html 拆出，改交互只动这个小文件） */
/* def 17/18 接入时激活：
   1) fetch("/api/products?hex=...&cvd_safe=1") → render("#pres", j, r=>产品卡(r))
   2) sessionStorage["cb_pending_fill"]（def 18 填充指令）在此消费 */
