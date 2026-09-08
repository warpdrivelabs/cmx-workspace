# CMX Neo 主题接入完整指引（供新增展示类 Web Component 参考）

> **目的**：为 `cmx-data-comp` 新增的 7 个展示类 Web Components 提供"如何正确接入 CMX Neo 主题"的明确、可执行指引。
> **范围**：仅 Plan 阶段研究，不修改任何文件。
> **证据规范**：每条结论附 `file:line` 证据，可直接点击跳转核对。
> **撰写日期**：2026-07-29

---

## 0. TL;DR（一页纸结论）

CMX 的 "neo 主题" **不是一套 CSS 变量，也不是一套 class 命名约定**，而是一套**由 4 个层次叠加**的视觉语言：

1. **根层（品牌 token）**：`../cmx-portal-manager` 把 `--neo-cyan` / `--neo-violet` / `--neo-mint` / `--neo-warn` / `--neo-accent` / `--neo-glass` / `--neo-border` / `--neo-glow` / `--portal-*` 注入到 `:root`；亮/暗色随 UI5 `--sap*` 自动适配。所有 cmx 组件运行在 Portal 的 `:host` 链上， **这些变量在 Shadow DOM 边界是可继承的**。
2. **组件层（皮肤注入）**：每个支持 neo 的 cmx 组件都有一份 `<lib>/cmx-<name>-neo-skin.js`，导出 `CMX_<NAME>_NEO_SKIN_CSS` 字符串，组件的 `_applySkin()` 通过 `cmx-skin-runtime.js` 的 `applyNeoSkin({...})` 一站式把它注入到自己的 `ShadowRoot`，并加激活 class `cmx-<name>-neo`。
3. **激活开关（全局默认）**：门户启动时设 `globalThis.__cmxDefaultFormSkin='neo'` / `__cmxDefaultGridSkin='neo'`，使 cmx-ui5-form / cmx-revo-grid 默认即 neo。**新组件**应设立自己的 `__cmxDefault<Name>Skin`（如 `__cmxDefaultPanelSkin='neo'`），并由门户在合适时机设置。
4. **覆盖层（page 皮肤 / 逃生舱口）**：单组件可用 `data-cmx-skin="plain|default|none|flat"` 关掉 neo；同页 `<template id="...">` 通过 `data-cmx-style-id` 注入 page 级覆盖；旧版页用 `data-neo-<name>-lane` / `data-neo-<name>-tone` 标记"已自行注入皮肤，跳过全局默认"。

**新组件接入 neo 必须做的事**（最少 4 步）：

1. 在 `packages/cmx-data-comp/src/lib/cmx-<name>-neo-skin.js` 写一份皮肤 CSS 字符串，导出 `CMX_<NAME>_NEO_SKIN_CSS`，**所有色值用 `var(--neo-*)` + `var(--sap*)` 派生**，不要硬编码。
2. 组件内 `import { applyNeoSkin, applyPageStyleId } from '../lib/cmx-skin-runtime.js'`。
3. 在 `connectedCallback` / `attributeChangedCallback` 里调用 `applyNeoSkin({ host: this, shadow: this.shadowRoot, idBase: 'cmx-<name>', neoCss: CMX_<NAME>_NEO_SKIN_CSS, globalKey: '__cmxDefault<Name>Skin' })`，并在末尾 `applyPageStyleId(this, this.shadowRoot, 'cmx-<name>')`。
4. （可选）若要在 Portal 端默认启用，让 Portal 在 `import-ui5-and-app.js` 附近追加一行 `globalThis.__cmxDefault<Name>Skin = 'neo'`。

皮肤的视觉特征 = `color-mix` 渐变 + 玻璃质感 + `ui-monospace` 等宽字体 + `inset 2-3px` 强光侧栏 + `drop-shadow` 荧光 + 圆角 6-9px。

---

## 1. Neo 主题的本质（A）

### 1.1 Neo 是什么、不是什么

**不是**：单一文件、单一变量集、单一 class 命名系统。

**是**：CMX 自研的"高科技 / 智能化"视觉语言，由 3 类产物叠加组成：

- **(a) CSS 变量集（设计令牌）** — 品牌色 / 边框 / 玻璃 / 荧光 / 渐变背景等
- **(b) 共享 CSS 片段库（PORTAL_NEO_*_STYLES）** — tab 选中条 / 分屏条 / 状态栏 / 侧栏等"事实皮肤"
- **(c) 每个组件独立的 `<name>-neo-skin.js`** — 组件内 `:host(.cmx-<name>-neo)` 作用域下的具体样式

**与 SAP UI5 `--sap*` 关系**：
- **neo 不是覆盖 sap 令牌**，而**依赖 sap 令牌**派生亮/暗。所有 neo 色值都写成 `color-mix(in srgb, var(--neo-cyan) 28%, var(--sapList_Background, #fff))` 的形式，让亮色主题下接近 cyan tint、暗色主题下自然变深。
- 证据：[portal-neo-theme.css:11-16](file:///media/yqs/工作/rustspace/cmx/CMXPortalManager/src/lib/portal-neo-theme.css#L11-L16)（`--neo-glass` / `--neo-border` / `--neo-border-subtle` / `--neo-glow` 都用 `color-mix(..., var(--sap...))`）
- 证据：[cmx-form-neo-skin.js:12](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/lib/cmx-form-neo-skin.js#L12)（`--neo-form-base: var(--sapGroup_ContentBackground, var(--sapList_Background, #f4f6f8))`）

### 1.2 完整设计令牌清单

**根级（门户全局，`portal-neo-theme.css:4-49`，注入到 `:root`）**：

| 变量 | 含义 | 派生 / 兜底 |
|---|---|---|
| `--neo-cyan` | 品牌青（主色） | `#00b4d8` |
| `--neo-violet` | 品牌紫（副色） | `#7c3aed` |
| `--neo-mint` | 品牌绿（成功 / 第三色） | `#10b981` |
| `--neo-warn` | 警告橙 | `#f59e0b` |
| `--neo-accent` | 当前强调色 | `var(--neo-cyan)` |
| `--neo-accent-2` | 第二强调色 | `var(--neo-violet)` |
| `--neo-glass` | 玻璃质感（弱） | `color-mix(in srgb, var(--sapList_Background) 88%, transparent)` |
| `--neo-glass-strong` | 玻璃质感（强） | `color-mix(in srgb, var(--sapObjectHeader_Background) 93%, transparent)` |
| `--neo-border` | 边框（强） | `color-mix(in srgb, var(--neo-cyan) 28%, var(--sapGroup_ContentBorderColor))` |
| `--neo-border-subtle` | 边框（弱） | `color-mix(in srgb, var(--neo-cyan) 12%, var(--sapGroup_TitleBorderColor))` |
| `--neo-glow` | 荧光（青） | `color-mix(in srgb, var(--neo-cyan) 20%, transparent)` |
| `--neo-glow-violet` | 荧光（紫） | `color-mix(in srgb, var(--neo-violet) 16%, transparent)` |
| `--portal-tab-row-bg` | tab 行背景 | 多 stop linear-gradient |
| `--portal-panel-bg` | 面板背景 | 165deg 紫→青 |
| `--portal-workspace-bg` | 工作区背景 | 双 radial-gradient |
| `--portal-shellbar-bg` | 顶栏背景 | 三色 radial + 102deg linear |
| `--portal-statusbar-bg` | 状态栏背景 | 90deg 紫→青 |

**组件级（在 `cmx-<name>-neo-skin.js` 内 `:host(.cmx-<name>-neo)` 作用域下定义）**：

- `--neo-form-accent` / `--neo-form-accent-2` / `--neo-form-input-h` / `--neo-form-font-size` / `--neo-form-label-size` / `--neo-form-base` / `--neo-field-accent` — 见 [cmx-form-neo-skin.js:7-12](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/lib/cmx-form-neo-skin.js#L7-L12)
- `--neo-grid-accent` / `--neo-grid-accent-2/3/4` / `--revo-grid-bg` — 见 [cmx-grid-neo-skin.js:8-16](file:///media/yqs/工作/rustspace/cmx/CMXPortalManager/src/lib/cmx-grid-neo-skin.js#L8-L16)（注：grid 的皮肤文件实际在 `packages/cmx-data-comp/src/lib/cmx-grid-neo-skin.js`，line 9-13）

> **新组件约定**：皮肤文件内应再定义**本组件专属的 `--neo-<name>-*` 局部变量**（accent / base / font-size / radius 等），让 `:host(.cmx-<name>-neo)` 自己用，不污染全局。

**页面级（独立部署的"科技风"页面，如 `voucher-neo.html`）**：
- 见 [voucher-neo.html:4-17](file:///media/yqs/工作/rustspace/cmx/cmx-container/data/html-pages/sources/fi/cmxfico/gl/voucher-neo.html#L4-L17)，额外加了 `--neo-edge-highlight` / `--neo-shadow` / `--neo-panel-bg`，并在根 `data-node-id="vn-root"` 上重新声明全套 `--neo-*` 派生块（防止脱离 Portal 时缺令牌）。

### 1.3 视觉特征（从 CSS 推断）

| 维度 | neo 风格 |
|---|---|
| **配色** | 冷色霓虹：cyan `#00b4d8` 为主，violet `#7c3aed` / mint `#10b981` / warn `#f59e0b` 为辅。`color-mix` 派生占比 4-46%。 |
| **字体** | 表头 / 标签 / 按钮常压用 `ui-monospace, system-ui, sans-serif` 或 `ui-monospace, monospace`，`font-weight: 700-800`，`letter-spacing: 0.04-0.08em`，部分大写 (`text-transform: uppercase`)。 |
| **字号** | 表单字段 `0.76rem`，表头 `0.68-0.72rem`，KPI 主值 `0.95-1.4rem`（来自 voucher-neo）。 |
| **圆角** | 表单输入框 `7px`（[form line 100](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/lib/cmx-form-neo-skin.js#L100)），表单元件 `10px`（[form line 46](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/lib/cmx-form-neo-skin.js#L46)），grid 外壳 `8px`（[grid line 38](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/lib/cmx-grid-neo-skin.js#L38)），form 容器 `9px`（[form line 16](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/lib/cmx-form-neo-skin.js#L16)）。 |
| **间距** | form-item 间距 `0.32rem`（[form line 34](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/lib/cmx-form-neo-skin.js#L34)），input 高度 `1.52rem`（[form line 9](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/lib/cmx-form-neo-skin.js#L9)），页面主间距 `10px gap`（[page-style-guide.md:25](file:///media/yqs/工作/rustspace/cmx/.agents/skills/native-page-generator/references/page-style-guide.md#L25)）。 |
| **装饰** | `inset 2-3px 0 0 <accent>` 强光左侧条（form/grid current-row）；`backdrop-filter: blur(6-8px)` 玻璃质感；`box-shadow` 多层（外发光 + 内侧高光）；`drop-shadow` 荧光（grid current-row 用 box-shadow，button hover 用 drop-shadow）；底部 1px 三色 linear-gradient 渐变高光（`PORTAL_NEO_ACCENT_LINE`，见 [portal-neo-theme.js:62-79](file:///media/yqs/工作/rustspace/cmx/CMXPortalManager/src/lib/portal-neo-theme.js#L62-L79)）。 |
| **背景图案** | 工作区 / 侧栏：双 radial-gradient（紫左上 / 青右下），叠加 1px 1px 网格 + mask 渐变（[portal-neo-theme.js:32-45](file:///media/yqs/工作/rustspace/cmx/CMXPortalManager/src/lib/portal-neo-theme.js#L32-L45)）。 |
| **明暗模式** | 不维护 dark 变体：靠 `color-mix` + `var(--sapList_Background, #fff)` / `var(--sapList_Background, #1a1f26)` 自动适配。例外：grid 在 `revo-grid[theme^="dark"]` 显式分叉（[grid line 15-17](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/lib/cmx-grid-neo-skin.js#L15-L17)、[grid line 67-72](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/lib/cmx-grid-neo-skin.js#L67-L72)）。 |

---

## 2. Neo 主题如何被应用 / 激活（B）

### 2.1 三条启用路径（按优先级）

1. **全局默认（推荐）** — 门户启动时设 `globalThis.__cmxDefaultFormSkin = 'neo'`，所有 cmx-ui5-form 实例**自动**应用 neo，无需每页声明。
   - 证据：[import-ui5-and-app.js:17-18](file:///media/yqs/工作/rustspace/cmx/CMXPortalManager/src/import-ui5-and-app.js#L17-L18)
   - 文档：[page-style-guide.md:13](file:///media/yqs/工作/rustspace/cmx/.agents/skills/native-page-generator/references/page-style-guide.md#L13)、[page-style-guide.md:164](file:///media/yqs/工作/rustspace/cmx/.agents/skills/native-page-generator/references/page-style-guide.md#L164)
2. **单组件显式** — 在组件上写 `data-cmx-skin="neo"`，覆盖全局默认（"显式优先"原则）。
3. **单组件关闭** — 在组件上写 `data-cmx-skin="plain" | "default" | "none"` 或 grid 专属的 `data-cmx-skin="flat"`，关闭 neo。

### 2.2 注入位置与作用域

- **Portal 根**：`portal-neo-theme.css` 4-49 行把全套 `--neo-*` 注入 `:root`，被 Vite 用 `@import url('./lib/portal-neo-theme.css')` 引入 [app-shell.css:4](file:///media/yqs/工作/rustspace/cmx/CMXPortalManager/src/app-shell.css#L4)。
- **JS 兜底**：`portal-neo-theme.js:565-573` 的 `initPortalNeoTheme()` 可在运行时把 `:root` 变量二次注入到 `document.head`（幂等，按 id 查重）。
- **cmx 组件 Shadow DOM**：通过 `applyNeoSkin()` 注入，**作用域为 `ShadowRoot` 内部**。`:host(.cmx-<name>-neo)` 选择器只匹配该组件自己的 host 元素，不影响其他组件。Skin 的 CSS 变量通过 `:host(.cmx-<name>-neo) { --neo-<name>-accent: ... }` 声明，由于 Shadow DOM 边界允许 `inherit` 自定义属性，所以根 `:root` 上的 `--neo-cyan` 会自动透传进 Skin 内的 `color-mix(... var(--neo-cyan) ...)` 公式。
- **业务页面 Shadow**：`page-style-guide.md:12` 明确说"业务页运行在 Portal shadow 下，自动继承这些变量"。

### 2.3 亮 / 暗 vs light theme

neo 没有"light neo"和"dark neo"两套变量。**只有一套**，通过 `color-mix(in srgb, var(--sapList_Background, #fff) 88%, transparent)` 这样的公式，**自动**随 UI5 的 `--sapList_Background` 在 light/dark 主题间切换。

- 证据：[portal-neo-theme.css:11](file:///media/yqs/工作/rustspace/cmx/CMXPortalManager/src/lib/portal-neo-theme.css#L11) `--neo-glass` 用 `var(--sapList_Background, #fff)` 作 fallback
- 证据：[grid line 15-17](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/lib/cmx-grid-neo-skin.js#L15-L17) grid 显式分叉 dark 主题：`revo-grid[theme^="dark"] { --revo-grid-bg: color-mix(in srgb, var(--neo-grid-accent) 10%, var(--sapList_Background, #1a1f26)); }`

**结论**：新组件**不需要**写 dark variant，只要在色值公式里始终引用 `--sap*` 而不是硬编码白色/黑色。

### 2.4 哪些地方启用 neo（全库搜索结果）

44 个文件命中 "neo" 关键字，主要分布：

| 用途 | 文件 | 证据 |
|---|---|---|
| Portal 全局 CSS 变量 | `../cmx-portal-manager` | 1-49 |
| Portal JS 变量 / 共享片段 | `../cmx-portal-manager` | 1-573 |
| Portal 全局默认开关 | `../cmx-portal-manager` | — |
| 组件皮肤源（form） | `packages/cmx-data-comp/src/lib/cmx-form-neo-skin.js` | 1-194 |
| 组件皮肤源（grid） | `packages/cmx-data-comp/src/lib/cmx-grid-neo-skin.js` | 1-175 |
| 皮肤运行时（共享助手） | `packages/cmx-data-comp/src/lib/cmx-skin-runtime.js` | 1-130 |
| Portal 壳层应用（shellbar / sidebar / statusbar / activity / splitter） | `portal-shellbar.js`、`portal-side-nav-shell.js`、`portal-side-nav-menu.js`、`portal-status-bar.js`、`portal-activity-bar.js`、`portal-app-shell.js`、`portal-content-area-shell.js`、`portal-log-panel.js` | 见 portal-neo-theme.js 各 `PORTAL_NEO_*_STYLES` 引用 |
| 模块主题色（侧栏字典 / 树 / 文件） | `../cmx-portal-manager` | line 65（`--neo-cyan: side.accent`） |
| 业务示范页 | `cmx-container/data/html-pages/sources/fi/cmxfico/gl/voucher-neo.html` | 4-17 派生块 |
| 设计器 Inspector | `../cmx-html-designer`（data-cmx-skin placeholder=neo） | — |
| 文档 / 规范 | `cmx-components-guide/references/frontend-conventions.md`、`page-style-guide.md`（×2）、`cmx-components-guide/references/{form,grid}-components.md` | — |

---

## 3. Neo 皮肤如何接入 Web Component（C）

### 3.1 皮肤文件结构（两个范例完全同构）

```js
// packages/cmx-data-comp/src/lib/cmx-<name>-neo-skin.js
/**
 * CMX Neo <name> 皮肤 — 一句话说明用途
 * 启用：<cmx-<name>> data-cmx-skin="neo" [data-cmx-skin-tone="..."]
 * 页面可覆盖：data-cmx-style-id 或 setSkinStyles()
 */
export const CMX_<NAME>_NEO_SKIN_CSS = `
  :host(.cmx-<name>-neo) {
    /* 本组件专属局部变量 */
    --neo-<name>-accent: #00b4d8;
    --neo-<name>-accent-2: #7c3aed;
    /* ... 字号/圆角/基础色 ... */
  }
  :host(.cmx-<name>-neo) .<inner-class> {
    /* 真实样式 */
  }
  :host(.cmx-<name>-neo) <inner-class>:hover { ... }
  /* tone 变体 */
  :host(.cmx-<name>-neo.cmx-<name>-neo--mint) { --neo-<name>-accent: #10b981; }
`
```

- form 范例：[cmx-form-neo-skin.js:1-194](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/lib/cmx-form-neo-skin.js)
- grid 范例：[cmx-grid-neo-skin.js:1-175](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/lib/cmx-grid-neo-skin.js)

### 3.2 皮肤文件**不导出任何函数或 class**，只导出 CSS 字符串

```js
export const CMX_FORM_NEO_SKIN_CSS = `:host(...) { ... }`
export const CMX_GRID_NEO_SKIN_CSS = `:host(...) { ... }`
```

没有 constructable stylesheet，没有 class 工厂，没有注册函数。**纯字符串**，由 `cmx-skin-runtime.js` 写入 ShadowRoot 的 `<style>` 节点。

### 3.3 组件内引用流程（以 cmx-ui5-form 为例）

```js
// 1. import 皮肤字符串
import { CMX_FORM_NEO_SKIN_CSS } from '../lib/cmx-form-neo-skin.js'

// 2. import 共享运行时
import { setSkinStyle, applyNeoSkin, applyPageStyleId } from '../lib/cmx-skin-runtime.js'

// 3. 在 connectedCallback / attributeChangedCallback 里调 _applySkin
_applySkin () {
  if (!this.hasAttribute('data-neo-form-lane')) {       // 逃生舱口
    applyNeoSkin({                                      // 一站式
      host: this,
      shadow: this.shadowRoot,
      idBase: 'cmx-form',
      neoCss: CMX_FORM_NEO_SKIN_CSS,
      globalKey: '__cmxDefaultFormSkin',
      fallback: 'neo',
      activeClass: 'cmx-form-neo',
      toneClass: (tone) => tone === 'mint' ? 'cmx-form-neo--mint' : null,
    })
  }
  applyPageStyleId(this, this.shadowRoot, 'cmx-form')    // page 覆盖
}
```

完整证据：[cmx-ui5-form.js:64-65](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/components/cmx-ui5-form.js#L64-L65)、[cmx-ui5-form.js:225-247](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/components/cmx-ui5-form.js#L225-L247)、[cmx-revo-grid.js:31](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/components/cmx-revo-grid.js#L31)、[cmx-revo-grid.js:334-357](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/components/cmx-revo-grid.js#L334-L357)

### 3.4 激活 class 命名约定

- 主类：`cmx-<name>-neo`（如 `cmx-form-neo` / `cmx-grid-neo`）。所有 neo 专属样式都挂在 `:host(.cmx-<name>-neo) ...` 下面。
- 色调变体：`cmx-<name>-neo--<tone>`（如 `cmx-grid-neo--mint`、`cmx-grid-neo--violet`、`cmx-grid-neo--azure`）。仅 grid 有多个 tone；form 只有 `mint` 一个（[cmx-ui5-form.js:242](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/components/cmx-ui5-form.js#L242)）。
- 通用 tone 值：`cyan`（默认，主）/ `mint` / `violet` / `azure`（grid）/ `mint`（form）。新组件至少要支持 `cyan` + `mint` 两个，否则 `data-cmx-skin-tone` 无意义。

### 3.5 注入节点的 layer 顺序

`setSkinStyle()` 按 layer 在 ShadowRoot 内 append 不同 id 的 `<style>`，CSS 后写覆盖前写：

- `cmx-<name>-skin-neo`（内置 neo）
- `cmx-<name>-skin-page`（页内 `<template id="...">` 通过 `data-cmx-style-id` 注入）
- `cmx-<name>-skin-custom`（组件内部或调用方通过 `setSkinStyles(css, 'custom')` 注入）

证据：[cmx-skin-runtime.js:14-19](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/lib/cmx-skin-runtime.js#L14-L19)

---

## 4. 组件如何"声明支持 neo 主题"（D）

### 4.1 **没有**统一的"主题注册中心"

`grep` 全库**没有** `registerNeoSkin` / `registerSkin` / `registerTheme` / `applyTheme` 这样的全局注册函数。CMX 走的是"组件 + 同名 skin 文件 + `cmx-skin-runtime.js` 共享助手"模式，没有中央注册表。

- 证据：全库搜索 `registerNeoSkin` / `applyNeoSkin` / `registerSkin` / `applySkin` 命中文件仅 [cmx-skin-runtime.js:91](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/lib/cmx-skin-runtime.js#L91)（**导出** `applyNeoSkin`，但**不是注册**——是执行）、[cmx-ui5-form.js:65](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/components/cmx-ui5-form.js#L65)、[cmx-revo-grid.js](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/components/cmx-revo-grid.js) 三处 import。
- 也就是说，`applyNeoSkin()` 是**调用入口**而不是**注册入口**。

### 4.2 走的就是上一节"3.3 组件内引用流程"那 3 步

1. 写皮肤 CSS 文件（`lib/cmx-<name>-neo-skin.js`，导出字符串常量）。
2. 在组件里 import 皮肤 + 共享助手。
3. 在 `_applySkin()` 里调 `applyNeoSkin({ ... })` + `applyPageStyleId(...)`。

### 4.3 "支持 neo 主题"在 `_css()` 里到底写什么

两种写法，**二选一**：

#### 写法 A：直接引用 `--neo-*` 变量（推荐给新组件）

`_css()` 的所有色值都用 `var(--neo-cyan)` / `var(--sapList_Background, #fff)` / `color-mix(in srgb, var(--neo-cyan) 28%, var(--sapList_Background, #fff))` 派生：

```js
_styles () {
  return `
    :host {
      display: block;
      background: var(--sapList_Background, #fff);
      color: var(--sapTextColor, #1d2d3e);
      border: 1px solid var(--neo-border-subtle, var(--sapGroup_TitleBorderColor, #ddd));
      border-radius: 8px;
      font-family: ui-monospace, var(--sapFontFamily, system-ui), monospace;
    }
    :host(:hover) {
      border-color: var(--neo-border, var(--sapGroup_ContentBorderColor, #d9d9d9));
    }
  `
}
```

neo skin 文件**只在**该变量确实需要在 neo 模式下重写时才提供（如 neon glow / strong accent），不重复基础色。

#### 写法 B：skin 文件提供完整 neo 变体（form / grid 模式）

`_css()` 只写**最朴素的 UI5 / sap 默认外观**（让 `data-cmx-skin="plain"` / `none` 时也好看），**所有 neo 美化**都集中在 skin 文件 `:host(.cmx-<name>-neo) ...` 下，靠 `applyNeoSkin` 注入。

> **新组件推荐 A 写法**：因为你 7 个组件是**展示类**（panel / toolbar / chip / card / kpi / divider / breadcrumb），用户期待它们**默认就是 neo 风格**（与 form/grid 一致），B 写法更适合"原生 vs neo 是两套完整设计"的 form/grid。

### 4.4 是否需要新建 neo 皮肤文件

**判定规则**：

| 场景 | 是否需要新皮肤文件 |
|---|---|
| 组件默认就是 neo 风格，色值直接用 `var(--neo-*)` | **否**——`_css()` 自己写完事 |
| 组件有"非 neo 替代外观"（如 `data-cmx-skin="plain"` / `compact`）需要切换 | **是**——给每个变体写一份皮肤 |
| 组件需要"四色调"（cyan / mint / violet / azure）按 `data-cmx-skin-tone` 切换 | **是**——skin 文件定义 `:host(.cmx-<name>-neo--mint) { --neo-<name>-accent: ... }` |
| 组件有 hover / focus / active 等强装饰态需要荧光 | **建议**——把发光 / drop-shadow / 渐变集中在 skin |

**对 7 个展示类组件的建议**：
- 全部走写法 A（直接引用 `var(--neo-*)`），**不建**独立 neo-skin.js。
- 唯一例外：若要做 `data-cmx-skin-tone` 切换（推荐先只支持 `mint`），可在组件 `_css()` 末尾加 `:host([data-cmx-skin-tone="mint"]) { --neo-<name>-accent: var(--neo-mint); --neo-<name>-accent-2: var(--neo-cyan); }`，**不需要单独 skin 文件**。

### 4.5 现有组件的"皮肤"行为清单

| 组件 | neo 皮肤文件 | tone 变体 | 全局默认 | 备注 |
|---|---|---|---|---|
| `cmx-ui5-form` | `cmx-form-neo-skin.js` | `mint` | `__cmxDefaultFormSkin='neo'` | 完整皮肤方案（B 写法） |
| `cmx-revo-grid` | `cmx-grid-neo-skin.js` | `mint` / `violet` / `azure` | `__cmxDefaultGridSkin='neo'` | 完整皮肤方案（B 写法），有 `flat` / `embed` 旁路 |
| `cmx-tabulator` | 无 | 无 | 无（走 A 写法） | 列头 `data-cmx-accent-color` 局部强调 |
| `cmx-web-treeview` | 无 | 无 | `data-cmx-skin="colored"` 触发局部 | A 写法 + 局部彩色 |
| `cmx-pager` / `cmx-view-tabs` / `cmx-split-pane` / `cmx-floating-dialog` / `cmx-dict-select` / `cmx-embed-page` | 无 | 无 | 各自零散 | 全部 A 写法 |

证据：全库搜索 `cmx-<name>-neo-skin` 仅命中 form/grid 两份；其他组件没有专属 neo 皮肤文件。

### 4.6 静态资源（CSS 变量）从哪里来

`var(--neo-cyan)` 等**不需要组件自己注入**，由 `portal-neo-theme.css:4-49` 在 Portal 启动时挂到 `:root`，Shadow DOM 边界允许自定义属性继承。**但**如果新组件可能被独立使用（如 `cmx-html-pages` 导出页脱离 Portal），要在组件自己 ShadowRoot 的 `<style>` 顶部复制 `PORTAL_NEO_ROOT_VARS`（来自 [portal-neo-theme.js:7-52](file:///media/yqs/工作/rustspace/cmx/CMXPortalManager/src/lib/portal-neo-theme.js#L7-L52)）作为 `:host { ... }` 兜底，参照 [voucher-neo.html:4-17](file:///media/yqs/工作/rustspace/cmx/cmx-container/data/html-pages/sources/fi/cmxfico/gl/voucher-neo.html#L4-L17) 的做法。

---

## 5. Neo 的视觉特征（E，从 CSS 反推）

### 5.1 已命名的 class / 变量（"事实皮肤"清单）

这些 class 在实际业务页里反复出现，是约定俗成的"neo 装饰条"：

| 名称 | 用途 | 证据 |
|---|---|---|
| `.neo-panel` / `.neo-panel-head` | 科技风分区容器 + 标题 | [page-style-guide.md:121-129](file:///media/yqs/工作/rustspace/cmx/.agents/skills/native-page-generator/references/page-style-guide.md#L121-L129) |
| `.neo-meta-strip` / `.neo-lane` | 品牌装饰条（白名单允许原生 div 自建） | `cmx-components-guide/references/frontend-conventions.md` 第六节 div 白名单 |
| `.neo-hero` | 大型 hero 区（voucher-neo 首页） | [voucher-neo.html:55-68](file:///media/yqs/工作/rustspace/cmx/cmx-container/data/html-pages/sources/fi/cmxfico/gl/voucher-neo.html#L55-L68) |
| `.neo-kpi` / `.neo-kpi-status` / `.neo-kpi-val` / `.neo-ok` / `.neo-warn` | KPI 卡片 | [voucher-neo-page-functions.md:358-362](file:///media/yqs/工作/rustspace/cmx/CMXPortalManager/docs/voucher-neo-page-functions.md#L358-L362) |
| `.neo-title-text` | 渐变文字标题 | [voucher-neo.html:113-117](file:///media/yqs/工作/rustspace/cmx/cmx-container/data/html-pages/sources/fi/cmxfico/gl/voucher-neo.html#L113-L117) |
| `.cmx-form-neo` / `.cmx-form-neo--mint` | form neo 激活类 | [cmx-form-neo-skin.js:6](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/lib/cmx-form-neo-skin.js#L6) / [line 20](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/lib/cmx-form-neo-skin.js#L20) |
| `.cmx-grid-neo` / `.cmx-grid-neo--{mint,violet,cyan,azure}` | grid neo 激活类 | [cmx-grid-neo-skin.js:8](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/lib/cmx-grid-neo-skin.js#L8) / [line 18-35](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/lib/cmx-grid-neo-skin.js#L18-L35) |
| `.cmx-tab-reorder-target-before/after` | 拖放目标荧光侧条 | [portal-content-area-shell.js:182-183](file:///media/yqs/工作/rustspace/cmx/CMXPortalManager/src/components/portal-content-area-shell.js#L182-L183) |
| `.cmx-current-row` | grid 当前行 | [cmx-grid-neo-skin.js:148-153](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/lib/cmx-grid-neo-skin.js#L148-L153) |

### 5.2 关键 CSS 模式（可直接复用的"neo 七招"）

从 form/grid/portal 三处源提炼：

1. **强光侧条** — `box-shadow: inset 2-3px 0 0 <accent>`（form/grid current-row，drag-target）
2. **多层外发光** — `box-shadow: 0 8px 28px <color>, 0 2px 12px <color>, inset 0 1px 0 <highlight>`
3. **drop-shadow 荧光** — `filter: drop-shadow(0 0 6px <accent-tint>)`（按钮 hover）
4. **玻璃质感** — `background: <glass-color>; backdrop-filter: blur(6-8px)`
5. **渐变边框** — `background: linear-gradient(90deg, transparent, violet, cyan, mint, transparent 85%)` 一条 1px 顶/底高光线（`PORTAL_NEO_ACCENT_LINE`，[portal-neo-theme.js:62-79](file:///media/yqs/工作/rustspace/cmx/CMXPortalManager/src/lib/portal-neo-theme.js#L62-L79)）
6. **field-level 4 色循环** — `nth-child(4n+1/2/3/0)` 换 accent，让相邻字段不同色（[form line 147-150](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/lib/cmx-form-neo-skin.js#L147-L150)）
7. **背景网格** — `linear-gradient(<cyan 10%> 1px, transparent 1px)` × 横竖 + `mask-image: linear-gradient(180deg, #000 0%, transparent 88%)`（[portal-neo-theme.js:208-218](file:///media/yqs/工作/rustspace/cmx/CMXPortalManager/src/lib/portal-neo-theme.js#L208-L218)）

---

## 6. 新组件如何支持 neo 主题（实操指引）

### 6.1 模板代码

以 `cmx-panel` 为例（**走 A 写法**）：

```js
// packages/cmx-data-comp/src/components/cmx-panel.js
import { applyNeoSkin, applyPageStyleId } from '../lib/cmx-skin-runtime.js'

const CMX_PANEL_TONE_CLASSES = [
  'cmx-panel-neo--mint', 'cmx-panel-neo--violet', 'cmx-panel-neo--cyan', 'cmx-panel-neo--azure',
]

class CmxPanel extends HTMLElement {
  static get observedAttributes () {
    return ['data-cmx-skin', 'data-cmx-skin-tone', 'data-cmx-style-id', 'collapsed']
  }

  connectedCallback () {
    if (!this.shadowRoot) {
      this.attachShadow({ mode: 'open' })
      this.shadowRoot.innerHTML = `<style>${this._styles()}</style>${this._template()}`
    }
    this._applySkin()
  }

  attributeChangedCallback (name) {
    if (name === 'data-cmx-skin' || name === 'data-cmx-skin-tone' || name === 'data-cmx-style-id') {
      this._applySkin()
    }
  }

  _styles () {
    return `
      :host {
        display: block;
        position: relative;
        box-sizing: border-box;
        background: var(--sapList_Background, #fff);
        color: var(--sapTextColor, #1d2d3e);
        border: 1px solid var(--neo-border-subtle, var(--sapGroup_TitleBorderColor, #ddd));
        border-radius: 8px;
        overflow: hidden;
        font-family: ui-monospace, var(--sapFontFamily, system-ui), monospace;
        transition: border-color 0.18s ease, box-shadow 0.18s ease;
      }
      :host(:hover) {
        border-color: var(--neo-border, var(--sapGroup_ContentBorderColor, #d9d9d9));
        box-shadow: 0 1px 10px color-mix(in srgb, var(--neo-cyan, #00b4d8) 8%, transparent);
      }
      :host([data-cmx-skin-tone="mint"]) { --neo-cyan: var(--neo-mint, #10b981); }
      :host([data-cmx-skin-tone="violet"]) { --neo-cyan: var(--neo-violet, #7c3aed); }
      :host([data-cmx-skin-tone="azure"]) { --neo-cyan: #0284c7; }
      .head {
        display: flex; align-items: center; padding: 8px 12px;
        background: var(--sapList_HeaderBackground, #f5f6f7);
        border-bottom: 1px solid var(--neo-border-subtle, #e9e9e9);
        font-weight: 800; letter-spacing: 0.04em;
        color: var(--neo-cyan, #00b4d8);
        text-shadow: 0 0 12px color-mix(in srgb, var(--neo-cyan, #00b4d8) 12%, transparent);
      }
      .body { padding: 12px; }
    `
  }

  _template () {
    return `
      <div class="head"><slot name="head"></slot></div>
      <div class="body"><slot></slot></div>
    `
  }

  /** 走 A 写法：默认就是 neo 风格；data-cmx-skin=plain/none 时回退到无装饰 */
  _applySkin () {
    const raw = (this.getAttribute('data-cmx-skin') || '').trim().toLowerCase()
    if (raw === 'plain' || raw === 'none') {
      this.classList.remove('cmx-panel-neo', ...CMX_PANEL_TONE_CLASSES)
      this.shadowRoot?.getElementById('cmx-panel-skin-neo')?.remove()
    } else {
      // 默认 / 显式 'neo'：加激活 class，css 已经引用 --neo-*，无需额外注入 skin
      this.classList.add('cmx-panel-neo')
      this.classList.remove(...CMX_PANEL_TONE_CLASSES)
      const tone = (this.getAttribute('data-cmx-skin-tone') || '').trim().toLowerCase()
      if (tone && tone !== 'default' && tone !== 'cyan') {
        this.classList.add('cmx-panel-neo--' + tone)
      }
    }
    applyPageStyleId(this, this.shadowRoot, 'cmx-panel')
  }
}

if (!customElements.get('cmx-panel')) {
  customElements.define('cmx-panel', CmxPanel)
}
export { CmxPanel }
```

### 6.2 关键要点检查清单

新组件写完后逐条核对：

- [ ] **`_styles()` 里所有色值都是 `var(--sap*)` 或 `var(--neo-*)` 派生**——零硬编码 `#xxx` 色（除 `var()` 的 fallback）
- [ ] **没有写 dark 变体**——`color-mix(in srgb, <color> X%, var(--sapList_Background, #fff))` 公式自动适配
- [ ] **`font-family` 用 `ui-monospace, var(--sapFontFamily, system-ui), monospace`**——neo 标配等宽感
- [ ] **`font-weight: 700-800` + `letter-spacing: 0.04-0.08em`**——标题 / 标签 / KPI
- [ ] **圆角 6-9px**——按层级递减：容器 9 / 卡片 8 / 按钮 7 / tag 5
- [ ] **过渡 0.18s ease**——border / background / box-shadow 都要过渡
- [ ] **保留 `data-cmx-skin="plain|none"` 关闭开关**——A 写法可只移除 class
- [ ] **`data-cmx-skin-tone` 至少支持 `mint`**——grid/form 都已支持
- [ ] **支持 `data-cmx-style-id` 页面级覆盖**——调用 `applyPageStyleId()`
- [ ] **如果新组件是 cmx 业务组件，添加到 `packages/cmx-data-comp/src/index.js` 的 import + export**
- [ ] **如果新组件要给设计器拖拽，添加到 `../cmx-html-designer` 的 components 数组**
- [ ] **如果新组件是 Portal 默认启用的，让 Portal 在 `import-ui5-and-app.js` 附近加 `globalThis.__cmxDefault<Name>Skin = 'neo'`**（A 写法不需要，因为不依赖 applyNeoSkin 的全局 key，但可以保留 API 对齐）

### 6.3 是否走 B 写法（独立 neo-skin.js）的判定

仅当满足以下**全部**条件才建 `cmx-<name>-neo-skin.js`：

1. 组件有"原生 UI5 默认外观"作为另一种合理皮肤（如 `cmx-ui5-form` 接 `ui5-form` 必须保留 UI5 视觉）
2. neo 模式下的样式**与默认有结构性差异**（不是简单换色，如 form 的 `ui5-form-item::part(root)` 重写边框/渐变/阴影）
3. 需要 page-level `<template>` 覆盖——B 写法的 layer 顺序（neo / page / custom）天然支持

否则**一律 A 写法**——更轻、更可维护、不引入新文件。

### 6.4 必须新增的文件清单（建议）

| 组件 | 走 A 还是 B | 是否新增 neo-skin.js | 是否新 `__cmxDefault<Name>Skin` |
|---|---|---|---|
| cmx-panel | A | 否 | 否（默认即 neo） |
| cmx-toolbar | A | 否 | 否 |
| cmx-chip / cmx-tag | A | 否 | 否 |
| cmx-card | A | 否 | 否 |
| cmx-kpi | A（参考 voucher-neo .neo-kpi） | 否 | 否 |
| cmx-divider | A | 否 | 否 |
| cmx-breadcrumb | A | 否 | 否 |

**结论**：7 个展示类组件**大概率全部走 A 写法，不新增任何 neo-skin.js / 全局变量**。直接继承 `var(--neo-*)` 即可。

### 6.5 必须修改的现有文件清单

| 文件 | 改动 | 必要性 |
|---|---|---|
| `packages/cmx-data-comp/src/components/cmx-<name>.js`（×7） | 新增 7 个组件 + 各自 `_applySkin()` | 必需 |
| `packages/cmx-data-comp/src/index.js` | import + export 7 个新组件 | 必需（barrel） |
| `../cmx-html-designer` | 7 个新组件元数据（tag / group / attrs） | 必需（设计器可见） |
| `packages/cmx-data-comp/package.json` | `exports` 加 7 个组件入口 | 可选（按需子路径导入） |
| `../cmx-portal-manager` | 不需要改（A 写法不依赖全局 key） | 不需要 |

---

## 7. 关键文件索引

| 用途 | 路径 | 行号 |
|---|---|---|
| Portal Neo 根 token CSS | `../cmx-portal-manager` | 4-49 |
| Portal Neo JS 变量 + 共享片段 | `../cmx-portal-manager` | 1-573 |
| Portal 引入点（@import） | `../cmx-portal-manager` | 4 |
| 全局默认开关 | `../cmx-portal-manager` | 17-18 |
| 表单 Neo 皮肤源 | `packages/cmx-data-comp/src/lib/cmx-form-neo-skin.js` | 1-194 |
| 表格 Neo 皮肤源 | `packages/cmx-data-comp/src/lib/cmx-grid-neo-skin.js` | 1-175 |
| **皮肤运行时（共享助手）** | `packages/cmx-data-comp/src/lib/cmx-skin-runtime.js` | 1-130 |
| Form 引用皮肤 | `packages/cmx-data-comp/src/components/cmx-ui5-form.js` | 64-65, 225-247 |
| Grid 引用皮肤 | `packages/cmx-data-comp/src/components/cmx-revo-grid.js` | 31, 334-357 |
| Neo 风业务页范例 | `cmx-container/data/html-pages/sources/fi/cmxfico/gl/voucher-neo.html` | 1-260 |
| 样式统一指南 | `.agents/skills/{html,native}-page-generator/references/page-style-guide.md` | 1-243 |
| 前端复用规范 | `cmx-components-guide/references/frontend-conventions.md` | 1-179 |
| 设计器组件注册 | `../cmx-html-designer` | 17-580 |
| 组件 barrel | `packages/cmx-data-comp/src/index.js` | 1-159 |

---

## 8. 常见陷阱与反模式

1. **不要在组件内 `boot()` UI5** — 由 `cmx-ui5-runtime` 统一装载（`frontend-conventions.md` 第二节 4 UI5 装载）
2. **不要硬编码色值** — 一律 `var(--sap*)` / `var(--neo-*)` 派生（[page-style-guide.md:42-50](file:///media/yqs/工作/rustspace/cmx/.agents/skills/native-page-generator/references/page-style-guide.md#L42-L50)）
3. **不要重复发明 `applyNeoSkin`** — 直接 import [cmx-skin-runtime.js](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/lib/cmx-skin-runtime.js)
4. **不要给每个组件各加一份 `__cmxDefault*Skin` 全局变量** — A 写法不需要全局 key（皮肤已内联在 `_styles()`）
5. **不要用 `alert()` / `confirm()`** — 用 `cmxInfo` / `cmxWarn` / `cmxError`（`frontend-conventions.md` 第三节红线）
6. **不要写 dark variant** — `color-mix` + `--sap*` 自带适配
7. **不要每页重定义 `--neo-*`** — 业务页要么继承 Portal 根，要么完整复制派生块（[page-style-guide.md:189](file:///media/yqs/工作/rustspace/cmx/.agents/skills/native-page-generator/references/page-style-guide.md#L189)）
8. **不要把 neo skin 字符串 split 到多个文件** — 一个组件一份 `cmx-<name>-neo-skin.js` 即可
9. **新组件的 active class 必须有，否则 `:host(.cmx-<name>-neo) ...` 选择器不会命中** — A 写法也别忘了 `this.classList.add('cmx-<name>-neo')`
10. **不要让 tone 覆盖全局 `--neo-cyan`** — tone 只应覆盖本组件的局部 `--neo-<name>-accent`，不污染根 token（参考 form 的 4 色循环是覆盖 `--neo-field-accent` 而非 `--neo-cyan`，[form line 147-150](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/lib/cmx-form-neo-skin.js#L147-L150)）

---

## 9. 验收自检

新组件写完后的最小自检（与 page-style-guide.md §9 对齐）：

- [ ] 组件运行在 Portal 中时**自动**呈现 neo 风格（亮 / 暗主题切换均正常）
- [ ] 设 `data-cmx-skin="plain"` 后变回朴素外观
- [ ] 设 `data-cmx-skin-tone="mint"` 后强调色变绿
- [ ] 同页 `<template id="my-panel-style">` + 组件 `data-cmx-style-id="my-panel-style"` 后样式被覆盖
- [ ] 写 `<cmx-panel data-cmx-skin="plain">` + `<cmx-panel>` 两个相邻面板，风格明显区分
- [ ] 在 Form / Grid 页面里嵌套新组件，视觉一致（不掉队）
- [ ] 在设计器里能拖拽新组件进页面
- [ ] 在导出页（`cmx-html-pages`，脱离 Portal）也能正常显示——若需要，复制 `PORTAL_NEO_ROOT_VARS` 到 `:host` 兜底

---

## 11. 补充章节（2026-07-29 后增）：两个维度的主题切换机制

> **本章来源**：用户提问"分页 / 输入框 / 字典等组件没接 neo 主题,为什么切主题时它们也会变?"触发的更深研究。
> **与前 1-10 章关系**:前 10 章讲"如何接入 neo 主题",本章讲"已经看到的颜色变化实际由什么机制驱动",**两条独立通路**。
> **本章节不影响前文 1-10 章的实现指引**;但能解释一个常被混淆的现象:很多没接 neo 的组件,看起来"也支持主题变化"。

### 11.1 一句话结论

CMX 主题的"颜色变化"实际上由**两个完全独立**的机制叠加:

1. **UI5 主题切换**(sap_horizon / sap_fiori_3 / 暗色 / 高对比度)—— 重定义 `:root` 上的 `--sap*` 变量,影响**所有用 `--sap*` 的组件**。
2. **Neo 皮肤切换**(cyan / mint / violet / azure)—— 通过 `data-cmx-skin-tone` 属性选择器局部重写 `--neo-<name>-accent`,**只影响 6 个有 neo skin 的组件**。

这两个机制**互不依赖**,但通过 `--sap*` **共享同一个底座**,所以视觉上"协调"。

### 11.2 维度 1:UI5 主题切换(影响所有用 `--sap*` 的元素)

**机制**:UI5 webcomponents 框架加载时,**整个主题 CSS**(`/shared/.../@ui5/webcomponents-theming/...`)被注入到 `:root`,定义数百个 `--sap*` 变量。运行时切换 UI5 主题时,框架会**卸载旧主题 CSS、加载新主题 CSS**,导致 `:root --sap*` 全部重定义,所有引用 `--sap*` 的 CSS 规则自动更新。

**关键证据**:

| 现象 | 证据 |
|---|---|
| `cmx-pager` 用了 `--sap*` | [cmx-pager.js:53-66](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/components/cmx-pager.js#L53-L66) `color: var(--sapContent_LabelColor, #6a6d70); background: var(--sapList_HeaderBackground, transparent);` |
| `cmx-text-input` 把 `<ui5-input>` 套在 Shadow DOM | [cmx-text-input.js:266-269](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/components/cmx-text-input.js#L266-L269) `const input = document.createElement('ui5-input'); this.shadowRoot.append(style, input);` |
| `cmx-floating-dialog` 把 `<ui5-button>` 套在 Shadow DOM | [cmx-floating-dialog.js:247-249](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/components/cmx-floating-dialog.js#L247-L249) `const b = document.createElement('ui5-button');` |
| UI5 主题 ID 判定 | [portal-module-theme.js:30-37](file:///media/yqs/工作/rustspace/cmx/CMXPortalManager/src/lib/portal-module-theme.js#L30-L37) `if (attr) return /(_dark|_hcb|dark|black)$/.test(attr) \|\| attr.includes('_hcb')` |
| Neo 皮肤引用 `--sapList_Background` 作 fallback | [portal-neo-theme.css:11-12](file:///media/yqs/工作/rustspace/cmx/CMXPortalManager/src/lib/portal-neo-theme.css#L11-L12) `--neo-glass: color-mix(in srgb, var(--sapList_Background, #fff) 88%, transparent);` |

**对未接 neo 组件的影响**:

- `cmx-pager` / `cmx-view-tabs` / `cmx-split-pane` / `cmx-embed-page` / `cmx-dict-select` —— 这些组件**完全不引用 `--neo-*`**,仅用 `--sap*`,所以**它们跟随的是 UI5 主题切换**(horizon / horizon_dark 等),不参与 neo 色调切换
- `cmx-text-input` / `cmx-number-input` / `cmx-date-input` / `cmx-datetime-input` / `cmx-floating-dialog` —— 这些组件**自己一行颜色都不写**,把视觉完全委托给内部 `<ui5-*>` 组件,跟随 UI5 主题

**这回答了用户的疑问**:"分页 / 输入框 / 帮助字典等组件,没有使用 neo 主题,为啥也能在切换主题时字体颜色变化" —— 因为它们跟随的是 **UI5 大主题**(不是 neo),UI5 主题切换时 `--sap*` 整体重定义,所有用 `--sap*` 的元素自动跟着变。

### 11.3 维度 2:Neo 皮肤切换(只影响 6 个有 neo skin 的组件)

**机制**:每个有 neo skin 的组件都有一份 `cmx-<name>-neo-skin.js`,里面有属性选择器:

```css
:host(.cmx-<name>-neo[data-cmx-skin-tone="violet"]) { --neo-<name>-accent: var(--neo-violet, #7c3aed); }
:host(.cmx-<name>-neo[data-cmx-skin-tone="mint"])   { --neo-<name>-accent: var(--neo-mint, #10b981); }
:host(.cmx-<name>-neo[data-cmx-skin-tone="azure"])  { --neo-<name>-accent: #0a6ed1; }
```

**作用域只在该组件自己的 host 上**,不影响外部,也不影响其他未接 neo 的组件。

**6 个有 neo skin 的组件**(TDD 推进中):

| 组件 | 皮肤文件 | 状态 |
|---|---|---|
| `cmx-ui5-form` | [cmx-form-neo-skin.js](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/lib/cmx-form-neo-skin.js) | 已发布 |
| `cmx-revo-grid` | [cmx-grid-neo-skin.js](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/lib/cmx-grid-neo-skin.js) | 已发布 |
| `cmx-status-tag` | [cmx-status-tag-neo-skin.js](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/lib/cmx-status-tag-neo-skin.js) | TDD 推进中(测试 [cmx-status-tag.test.js](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/components/__tests__/cmx-status-tag.test.js) 已存在) |
| `cmx-toolbar` | [cmx-toolbar-neo-skin.js](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/lib/cmx-toolbar-neo-skin.js) | TDD 推进中 |
| `cmx-empty-state` | [cmx-empty-state-neo-skin.js](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/lib/cmx-empty-state-neo-skin.js) | TDD 推进中 |
| `cmx-filter-bar` | [cmx-filter-bar-neo-skin.js](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/lib/cmx-filter-bar-neo-skin.js) | TDD 推进中 |

**全局默认开关**在 [import-ui5-and-app.js:19-25](file:///media/yqs/工作/rustspace/cmx/CMXPortalManager/src/import-ui5-and-app.js#L19-L25) 已集中声明,注释明确列出 7 个目标组件(包括 `cmx-desc-list` 还没找到对应 skin 文件):

```js
/** 展示类组件（panel / toolbar / status-tag / empty-state / desc-list / filter-bar）默认 Neo 皮肤 */
globalThis.__cmxDefaultPanelSkin = 'neo'
globalThis.__cmxDefaultToolbarSkin = 'neo'
globalThis.__cmxDefaultStatusTagSkin = 'neo'
globalThis.__cmxDefaultEmptyStateSkin = 'neo'
globalThis.__cmxDefaultDescListSkin = 'neo'
globalThis.__cmxDefaultFilterBarSkin = 'neo'
```

### 11.4 两个维度的对比

| 维度 | UI5 主题切换 | Neo 皮肤切换 |
|---|---|---|
| **触发方式** | 切 UI5 主题 ID(`sap_horizon` / `sap_fiori_3` / `..._dark`) | 切 `data-cmx-skin-tone="cyan\|violet\|mint\|azure"` |
| **作用域** | 全局 `:root` 上数百个 `--sap*` 变量整体重定义 | 单个组件 `:host(.cmx-<name>-neo)` 局部重写 `--neo-<name>-accent` |
| **影响范围** | **广**——所有用 `--sap*` 的组件(包括没接 neo 的) | **窄**——只影响 6 个有 neo skin 的组件 |
| **谁来加载** | UI5 webcomponents 框架自动 | 组件 `_applySkin()` 注入 |
| **变量基础** | `--sap*`(UI5 主题) | `--neo-<name>-accent`(局部)+ `--sap*` 作派生底色 |
| **跟随表现** | 切暗色 → 所有用 `--sap*` 的元素全变暗 | 切 mint → 只有 6 个 neo 组件的强调色变绿,其他不变 |
| **典型用户** | 切整站主题(浅/暗/对比度) | 切页面内单组件的强调色 |

### 11.5 为什么"看起来协调"?

**关键洞察**:neo 皮肤**用 `color-mix(in srgb, var(--neo-cyan) 28%, var(--sapList_Background, #fff))` 派生**——neo 的色值**基础仍然是 `--sap*`**!

```
neo 组件的视觉色 = color-mix(neo-cyan, sapList_Background, X%)
cmx-pager 的视觉色 = var(--sapContent_LabelColor)  ← 跟主题走
cmx-text-input 内部 = ui5-input 的 --sap*         ← 跟主题走
```

所以:
- **亮色主题下**:neo cyan 混合白底 → 浅青;`--sapContent_LabelColor` 浅灰
- **暗色主题下**:neo cyan 混合深底 → 深青;`--sapContent_LabelColor` 浅灰(可能反相)
- **三者的"底色"都来自 `--sap*`** → 自动同步亮/暗

**两者通过 `--sap*` 共享同一根**(亮的都亮,暗的都暗),所以"看起来协调",但实际上是**两条独立通路**。

### 11.6 一图流

```
                    :root (document)
                          │
                ┌─────────┴─────────┐
                ▼                   ▼
        UI5 主题 CSS              portal-neo-theme.css
   (horizon / horizon_dark)   (--neo-cyan / --violet / ...)
        │                              │
        ▼                              │
   数百个 --sap* 变量                  │  (--neo-* 通过 color-mix 引用 --sap*)
   (Background/Text/...)               │
        │                              │
        │   ┌──────────────────────────┘
        │   │
        ▼   ▼
   ┌──────────────────┐
   │  cmx-pager       │  ← 只用 --sap*,跟 UI5 主题
   │  cmx-text-input  │  ← 包 <ui5-input>,完全委托给 UI5
   │  cmx-floating-   │  ← 包 <ui5-button>/<ui5-dialog>,委托
   │    dialog        │
   │  cmx-dict-select │  ← 用 --sap*
   │  cmx-split-pane  │  ← 用 --sap*
   │  cmx-view-tabs   │  ← 用 --sap*
   │  cmx-embed-page  │  ← 用 --sap*
   └──────────────────┘
        │
        ▼  (跟随 UI5 主题切换)

   ┌──────────────────┐         ┌────────────────────────┐
   │  cmx-ui5-form    │  ──►   │ cmx-form-neo-skin.js   │ ── data-cmx-skin-tone="..."
   │  cmx-revo-grid   │  ──►   │ cmx-grid-neo-skin.js   │ ── data-cmx-skin-tone="..."
   │  cmx-status-tag  │  ──►   │ cmx-status-tag-neo-skin.js
   │  cmx-toolbar     │  ──►   │ cmx-toolbar-neo-skin.js
   │  cmx-empty-state │  ──►   │ cmx-empty-state-neo-skin.js
   │  cmx-filter-bar  │  ──►   │ cmx-filter-bar-neo-skin.js
   │  cmx-panel       │  ──►   │ (待补充 - 官方已声明全局开关)
   │  cmx-desc-list   │  ──►   │ (待补充 - 官方已声明全局开关)
   └──────────────────┘         └────────────────────────┘
        │                                       │
        ▼                                       ▼
   (跟随 UI5 主题)                          (跟随 neo tone)
              \                            /
               \                          /
                ▼                        ▼
              视觉: 协调统一(都通过 --sap* 共享底座)
```

### 11.7 常见误解澄清

| 误解 | 真相 |
|---|---|
| "接了 neo 的组件,切 UI5 主题不会变" | **错**。neo 组件通过 `color-mix` 引用 `--sap*`,UI5 主题切换会带动其底色和派生色。 |
| "没接 neo 的组件,切 neo tone 不会变" | **正确**。neo skin 作用域在 `:host(.cmx-<name>-neo)`,未接 neo 的组件没有该 host class,不受影响。 |
| "neo 主题和 UI5 主题是平级的两套" | **半对**。neo 是**叠加在 UI5 主题之上**的品牌色层,而不是平级替代。`--neo-*` 通过 `color-mix` 永远引用 `--sap*` 作底座。 |
| "只要写 `var(--neo-cyan)` 就算接 neo" | **半对**。仅写变量不够,还需要有 `cmx-<name>-neo-skin.js` 文件 + `_applySkin()` 注入 + `:host(.cmx-<name>-neo)` 激活类。否则只是"借"了根 token,无品牌语义。 |
| "全局 `__cmxDefaultXxxSkin` 必须设才能用" | **半对**。`applyNeoSkin()` 的 fallback 默认就是 'neo'([cmx-skin-runtime.js:61-69](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/lib/cmx-skin-runtime.js#L61-L69))。全局变量只是**覆盖**默认,缺省时仍然是 neo。 |

### 11.8 对新组件设计的启示

如果新组件**只想跟 UI5 主题**(不想做品牌色):
- 只需 `var(--sapList_Background, #fff)` 等,无须建 `<name>-neo-skin.js`
- 适合:纯信息展示、无强调色的辅助类组件(如分隔线 divider、面包屑 breadcrumb)

如果新组件**需要品牌强调色**(cyan/mint/violet/azure 可切):
- 走 B 写法:建 `cmx-<name>-neo-skin.js`,用属性选择器切 tone
- 在 `import-ui5-and-app.js` 加 `globalThis.__cmxDefault<Name>Skin = 'neo'`
- 适合:工具栏 toolbar、卡片 card、面板 panel、KPI、tag 等

如果新组件**需要业务色调**(success/warning/danger/info/neutral):
- 参照 `cmx-status-tag` 的双层 tone 模式(见 [cmx-status-tag-neo-skin.js:27-32](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/lib/cmx-status-tag-neo-skin.js#L27-L32))
- 适合:状态标签、徽章、告警条

### 11.9 关键文件索引(本章新增)

| 用途 | 路径 | 行号 |
|---|---|---|
| 全局默认开关(7 个 neo 组件集中声明) | `../cmx-portal-manager` | 19-25 |
| `cmx-pager` 用 `--sap*` 实证 | `packages/cmx-data-comp/src/components/cmx-pager.js` | 53-66 |
| `cmx-text-input` 委托 UI5 实证 | `packages/cmx-data-comp/src/components/cmx-text-input.js` | 266-269 |
| `cmx-floating-dialog` 委托 UI5 实证 | `packages/cmx-data-comp/src/components/cmx-floating-dialog.js` | 247-249 |
| UI5 主题暗色判定 | `../cmx-portal-manager` | 30-37 |
| `cmx-status-tag` tone+variant 模式 | `packages/cmx-data-comp/src/lib/cmx-status-tag-neo-skin.js` | 27-64 |
| `cmx-toolbar` 标准 4-tone 模式 | `packages/cmx-data-comp/src/lib/cmx-toolbar-neo-skin.js` | 5-13 |
| `applyNeoSkin` fallback='neo' 默认 | `packages/cmx-data-comp/src/lib/cmx-skin-runtime.js` | 61-69 |
