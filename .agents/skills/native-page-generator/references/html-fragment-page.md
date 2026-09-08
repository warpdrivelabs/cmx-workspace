# HTML 片段页指南（native-page 轻量形态）

> 何时读：生成 HTML 片段形态的 native-page（纯静态展示 / 简单交互 / 跨区域联动 demo）。
> 真实范例：`cmx-container/assets/portal/data/native-pages/sources/demo/product-explorer.html`（38 行）

---

## 一句话

HTML 片段页 = 一个 `.html` 文件（片段或整页），由 `cmx-native-pages-host` 宿主加载：片段挂 shadowRoot，整页走 iframe。`<script>` 由宿主包函数作用域执行（注入 `workspace/host/ctx`）。

---

## 何时选 HTML 片段（而非 JS 模块页）

| 场景 | 选 |
| --- | --- |
| 纯静态展示（说明页、帮助页） | HTML 片段 |
| 简单交互（点击选值、跨区域联动 demo） | HTML 片段 |
| 需复用 cmx-* 组件 | **JS 模块页**（片段页无 importmap） |
| 多状态 / 后端动态 / 元数据驱动 | **JS 模块页** |
| 需要 `cmx-revo-grid` / `cmx-ui5-form` | **JS 模块页** |

> **原则**：只要页要用 cmx-* 组件或 cmx 助手，就转 JS 模块页。HTML 片段页定位是"轻量纯原生"。

---

## 渲染分流（关键）

宿主 `cmx-native-pages-host` 根据返回 HTML 形态分流（源码 `workspace-native-pages.js, 198-202`）：

| HTML 内容 | 渲染方式 |
| --- | --- |
| 完整文档（含 `<!doctype>` / `<html>` / `<head>` / `<body>`） | **iframe srcdoc** 沙箱（`sandbox="allow-scripts allow-forms allow-popups allow-modals allow-same-origin"`） |
| 片段（无上述标签） | 挂进宿主 shadowRoot 的 `.native-page-root` 容器 |

**含义**：
- 片段页的 `<script>` 由宿主用 `new Function('workspace','host','ctx', code)` 包函数作用域执行——**能访问注入的 workspace/host/ctx**
- 整页的 `<script>` 在 iframe 里跑——**完全隔离**，拿不到宿主的 workspace/host

> 想跨区域联动或访问宿主 → 必须用**片段**形态，不能用整页。

---

## 片段页模板（含 script，访问 host）

```html
<!-- product-explorer.html —— 产品选择器（片段，跨区域联动） -->
<div class="px-root" style="display:flex;flex-direction:column;height:100%;box-sizing:border-box;padding:10px;gap:8px;background:var(--sapBackgroundColor,#f7f7f7);color:var(--sapTextColor,#1d2d3e);">
  <ui5-bar design="Header">
    <ui5-label slot="startContent" style="font-weight:800;">产品列表</ui5-label>
  </ui5-bar>
  <ul id="prod-list" style="list-style:none;padding:0;margin:0;overflow:auto;flex:1 1 auto;"></ul>
</div>

<script>
  // native_pages 普通脚本：框架注入 workspace / host（无需 __designer_meta__）
  var root = host.renderRoot              // ★ 指向 shadowRoot
  var list = root.querySelector('#prod-list')

  var products = [
    { code: 'P-001', name: '产品 A' },
    { code: 'P-002', name: '产品 B' },
    { code: 'P-003', name: '产品 C' }
  ]

  products.forEach(function (p) {
    var li = document.createElement('li')
    li.style.cssText = 'padding:8px 12px;border-bottom:1px solid var(--sapGroup_ContentBorderColor,#d9d9d9);cursor:pointer;'
    li.textContent = p.code + ' · ' + p.name
    li.onclick = function () {
      // ★ 跨区域联动：写入 workspace.context，其它区域的页面可读
      workspace.context.set('selectedProduct', p)
      // 高亮选中
      list.querySelectorAll('li').forEach(function (x) { x.style.background = '' })
      li.style.background = 'var(--sapInformationBackground,#eaf4ff)'
    }
    list.appendChild(li)
  })
</script>
```

> 真实范例见 `demo/product-explorer.html`。注意 `host.renderRoot` 而非 `host.shadowRoot`（二者等价，但 renderRoot 是约定别名）。

---

## 整页文档模板（iframe 沙箱，完全隔离）

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>独立演示页</title>
  <style>
    body { font-family: "Segoe UI", sans-serif; padding: 16px; }
    .card { padding: 12px; border: 1px solid #ddd; border-radius: 4px; margin-bottom: 8px; }
  </style>
</head>
<body>
  <h2>独立演示（iframe 沙箱）</h2>
  <div class="card">
    <p>计数：<span id="count">0</span></p>
    <button onclick="inc()">+1</button>
  </div>
  <script>
    // 在 iframe 里跑，拿不到宿主的 workspace/host/ctx
    var n = 0
    function inc() { n++; document.getElementById('count').textContent = n }
  </script>
</body>
</html>
```

> 真实范例见 `demo/interactive-demo.html`。整页形态**不能**跨区域联动，**不能**用 cmx-* 组件（无 importmap，无 globalThis.__cmxDataComp）。

---

## script 执行环境（片段页）

片段页的 `<script>` 由宿主 `workspace-native-pages.js` 用 `new Function` 包函数作用域执行：

```js
// 宿主内部等价于：
new Function('workspace', 'host', 'ctx', userCode)(workspace, host, ctx)
```

**注入的变量**：
- `workspace` —— 工作区 scope 对象（`workspace.context.set/get` 跨区域联动）
- `host` —— `cmx-native-pages-host` CE 实例（`host.renderRoot` 查本页 DOM）
- `ctx` —— 同 JS 模块页的 ctx（`ctx.props` 等）

> 普通脚本**不是 ES Module**——不能用 `import`。要复用 cmx 助手必须转 JS 模块页。

---

## 跨区域联动（workspace.context）

native 页可跨工作区区域联动：

```js
// 区域 A（explorer）：选行写值
workspace.context.set('selectedProduct', { code: 'P-001', name: '产品 A' })

// 区域 B（content）：监听变化
workspace.context.on('selectedProduct', function (val) {
  console.log('收到：', val)
  // 刷新本区域内容
})
```

> 真实范例 `product-explorer.html` 用 `workspace.context.set`；另一个区域用 `workspace.context.get/on` 读取。

---

## 容易踩的坑

| 坑 | 正确做法 |
| --- | --- |
| 整页 HTML 里用 cmx-* 组件 | 整页走 iframe，无 importmap/全局 cmx；要么返回片段，要么转 JS 模块页 |
| 片段里用 `import cmx-data-comp` | 片段 script 不是 ES Module；转 JS 模块页 |
| 用 `host.shadowRoot` | 用 `host.renderRoot`（约定别名，二者等价） |
| 想跨区域联动却用整页 | 整页 iframe 隔离；必须用片段形态 |
| 硬编码色值 | 用 `var(--sap*)`（见 page-style-guide.md） |
| 用 `alert()` | 用 `cmxInfo` 等（但片段页要先从 host 取，不如转 JS 模块页方便） |
