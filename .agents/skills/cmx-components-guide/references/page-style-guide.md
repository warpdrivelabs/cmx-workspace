# 页面样式统一指南（双技能共享参考）

> ⚠️ **本文件是 `html-page-generator` 与 `native-page-generator` 的共享参考**。两处内容必须保持一致，改动需同步另一份。
> 何时读：生成任何业务页面 HTML 布局时必读——保证跨页面风格一致。

---

## 样式统一现状（先理解为什么这么写）

CMX 的样式统一是"半约定半代码生成"，并**原生支持换肤**：

- **统一的底盘**：UI5 的 `--sap_*` 变量（sap_horizon 主题）+ Portal 注入的 `--neo-*` 品牌色 token，都挂到 `:root`。业务页运行在 Portal shadow 下，**自动继承**这些变量。UI5 在 light/dark 主题间切换时，**所有引用 `var(--sap*)` 的页面属性自动跟随**，无需额外写 dark 变体。
- **统一的组件层**：`cmx-data-comp` 组件全部 Shadow DOM 隔离，`cmx-ui5-form` / `cmx-revo-grid` / `cmx-toolbar` / `cmx-kpi-card` / `cmx-desc-list` 等默认套用内置 **Neo 皮肤**（门户启动时设 `globalThis.__cmxDefaultFormSkin='neo'` / `__cmxDefaultGridSkin='neo'`）。**所有新建页面默认必须采用 Neo**。
- **统一的换肤机制**：`packages/cmx-data-comp/src/lib/cmx-skin-runtime.js` 抽出 `resolveSkin()` / `applyNeoSkin()` / `setSkinStyle()` / `applyPageStyleId()` 四个共享助手（"同一逻辑只一份实现"），按 `data-cmx-skin`（显式）→ 全局 `__cmxDefault*Skin` → fallback 三级优先级解析皮肤，注入到 ShadowRoot 并加激活 class。
- **不统一的页面层**：业务 HTML 页面**各自在页内 `<style>` 写约定 class**（`.biz-bar` / `.lvlbox` / `.neo-panel`），没有公共 CSS 文件可 import。设计器生成的页面骨架**不注入任何 Neo 样式**，只给 box-sizing + body padding。

**结论**：生成页面时必须**主动套用本指南的骨架和约定 class**，否则页面无品牌风格、与系统其它页不一致。**新增页面默认走 Neo 主题，并保证支持换肤**（用户偏好 / URL `?skin=` / 暗色模式）。

---

## 一、根 div 标准骨架（所有页面统一）

每个页面根 `<div>` 用这套骨架（来自真实凭证页 `erp-voucher-cnpc-ms.html`）：

```html
<div style="display:flex;flex-direction:column;height:100%;box-sizing:border-box;padding:10px;gap:10px;background:var(--sapBackgroundColor,#f7f7f7);color:var(--sapTextColor,#1d2d3e);">
  <!-- 页面内容 -->
</div>
```

**要点**：
- `flex-direction:column` + `height:100%`：占满工作区，纵向布局
- `box-sizing:border-box`：padding 不撑爆
- `gap:10px`：子区块间距统一
- 颜色一律 `var(--sapBackgroundColor)` / `var(--sapTextColor)`，**禁止硬编码** `#fff` / `#000`

---

## 二、颜色铁律

### 规则：一律用 CSS 变量派生，禁止硬编码色值

```css
/* ✅ 正确 */
background: var(--sapList_Background, #fff);
border: 1px solid var(--sapGroup_ContentBorderColor, #d9d9d9);
color: var(--sapPositiveColor, #107e3e);  /* 正数绿 */

/* ❌ 错误 */
background: #ffffff;
border: 1px solid #dddddd;
```

### 常用 `--sap-*` 变量速查

| 变量 | 含义 | 兜底值 |
| --- | --- | --- |
| `--sapBackgroundColor` | 页面背景 | `#f7f7f7` |
| `--sapTextColor` | 主文字色 | `#1d2d3e` |
| `--sapList_Background` | 列表/卡片背景 | `#fff` |
| `--sapList_HeaderBackground` | 列表头/分区头背景 | `#f5f6f7` |
| `--sapGroup_ContentBorderColor` | 分区边框 | `#d9d9d9` |
| `--sapField_BorderColor` | 输入框边框 | `#b3b3b3` |
| `--sapField_Background` | 输入框背景 | `#fff` |
| `--sapInformationBackground` | 信息条背景 | `#eaf4ff` |
| `--sapInformationBorderColor` | 信息条边框 | `#bcd8f7` |
| `--sapPositiveColor` | 正向（绿） | `#107e3e` |
| `--sapNegativeColor` | 负向（红） | `#bb0000` |
| `--sapContent_LabelColor` | 次要标签色 | `#6a6d70` |

### Neo 品牌 token（门户壳专用，业务页可直接引用）

门户启动时挂到 `:root`（见 `../../../../cmx-portal-manager`）：

| 变量 | 含义 | 值 |
| --- | --- | --- |
| `--neo-cyan` | 品牌青 | `#00b4d8` |
| `--neo-violet` | 品牌紫 | `#7c3aed` |
| `--neo-mint` | 品牌绿 | `#10b981` |
| `--neo-warn` | 警告橙 | `#f59e0b` |
| `--neo-accent` / `--neo-accent-2` | 强调色 | 派生 |
| `--neo-glass` / `--neo-glass-strong` | 玻璃质感 | 88% / 92% |
| `--neo-border` / `--neo-border-subtle` | 边框 | 派生 |

> 业务页运行在 Portal shadow 下，**直接用这些变量即可**，无需重定义。

---

## 三、约定 class 速查（可复制粘贴）

这些 class 在真实业务页反复出现，是"事实标准"。生成时直接用，不要每页自创。

### `.biz-bar` —— 次级信息条（标题/筛选/状态）

```css
.biz-bar{display:flex;align-items:center;gap:8px;padding:6px 11px;
         background:var(--sapInformationBackground,#eaf4ff);
         border:1px solid var(--sapInformationBorderColor,#bcd8f7);
         border-radius:4px}
```

### `.lvlbox` + `.lvl-head` —— 多级主从分区（每层 grid 一个）

```css
.lvlbox{background:var(--sapList_Background,#fff);
        border:1px solid var(--sapGroup_ContentBorderColor,#d9d9d9);
        border-radius:4px;overflow:hidden}
.lvl-head{display:flex;align-items:center;padding:6px 10px;
          border-bottom:1px solid var(--sapGroup_ContentBorderColor,#d9d9d9);
          background:var(--sapList_HeaderBackground,#f5f6f7)}
.lvl-head ui5-title{margin:0}
```

用法：
```html
<section class="lvlbox">
  <div class="lvl-head"><ui5-title level="H6" size="H6">L1 凭证批</ui5-title></div>
  <cmx-revo-grid data-cmx-master-slave-id="ms" data-cmx-dataset-id="head" ...></cmx-revo-grid>
</section>
```

### `.neo-panel` + `.neo-panel-head` —— 科技风分区

```css
.neo-panel{background:var(--sapList_Background,#fff);
           border:1px solid var(--neo-border,#d9d9d9);
           border-radius:6px;overflow:hidden}
.neo-panel-head{display:flex;align-items:center;padding:8px 12px;
                background:var(--sapList_HeaderBackground,#f5f6f7);
                border-bottom:1px solid var(--neo-border-subtle,#e9e9e9)}
```

### `.cmx-kv-table` —— 键值展示卡（只读两列清单）

UI5 无描述列表组件，允许用 `<table>` / `<dl>`，约定 class：
```css
.cmx-kv-table{width:100%;border-collapse:collapse;font-size:0.85rem}
.cmx-kv-table td{padding:6px 10px;border-bottom:1px solid var(--sapGroup_ContentBorderColor,#d9d9d9)}
.cmx-kv-table td:first-child{color:var(--sapContent_LabelColor,#6a6d70);width:40%}
```

---

## 四、工具栏规范

### 顶部主工具栏 —— `ui5-bar`

```html
<ui5-bar design="Header">
  <ui5-label slot="startContent" style="font-weight:800;font-size:1.05rem;">页面标题</ui5-label>
  <ui5-label id="statusText" slot="endContent" style="font-size:0.8rem;color:var(--sapContent_LabelColor);">状态</ui5-label>
</ui5-bar>
```

### 行内工具栏 —— 用 `ui5-toolbar` + `ui5-toolbar-button`

**禁止** `div[role=toolbar]` + 原生 button 堆工具条（AGENTS.md 七.6 红线）。

---

## 五、cmx 组件皮肤（默认即 Neo）

> **前提：Neo 皮肤只作用于 cmx-data-comp 组件**。皮肤 CSS 经 `applyNeoSkin()` 注入到组件 **ShadowRoot** 内的 `:host(.cmx-<name>-neo)` 选择器，**原生 HTML 元素（`<table>` / `<ul>` / `<form>` / 手写 `<div>`）不会自动套 Neo**。因此"页面要 Neo 风格"等价于"页面要用 cmx 组件"——业务表格用 `<cmx-revo-grid>`、表单用 `<cmx-ui5-form>`、对话框用 `<cmx-floating-dialog>`、分页用 `<cmx-pager>`、树形用 `<cmx-web-treeview>`。原生元素除"键值展示卡 `.cmx-kv-table`"和"弹层小型明细"两个例外（见第三节、SKILL.md 附录），一律不要用。
>
> 反过来：**只要用了 cmx 组件，不写 `data-cmx-skin` 就自动是 Neo**——这是默认行为，无需额外配置。

### 1. 皮肤优先级链（`resolveSkin`，`packages/cmx-data-comp/src/lib/cmx-skin-runtime.js`）

```
1. 显式 data-cmx-skin 属性       ← 单组件覆盖（最高）
2. globalThis[globalKey]          ← 门户启动时注入的默认（次高）
3. fallback（通常 'neo'）         ← 兜底（最低）
```

> `globalKey` 是组件约定的全局默认键名：form → `__cmxDefaultFormSkin`，grid → `__cmxDefaultGridSkin`，kpi-card → `__cmxDefaultKpiCardSkin`……portal 启动时统一设为 `'neo'`（`../../../../cmx-portal-manager`）。

### 2. 表格 `cmx-revo-grid` / 表单 `cmx-ui5-form`

**默认就是 Neo 皮肤**（门户启动时设全局默认），不写 `data-cmx-skin` 即可：

```html
<cmx-revo-grid data-cmx-master-slave-id="ms" ...></cmx-revo-grid>
<cmx-ui5-form data-cmx-density="compact" ...></cmx-ui5-form>
```

### 3. 切换 tone（青/绿/紫/蓝）

需要不同色调时用 `data-cmx-skin-tone`：

```html
<cmx-revo-grid data-cmx-skin-tone="cyan" ...></cmx-revo-grid>
<cmx-revo-grid data-cmx-skin-tone="violet" ...></cmx-revo-grid>
<cmx-ui5-form   data-cmx-skin-tone="mint" ...></cmx-ui5-form>
<!-- 可选值：cyan / mint / violet / azure -->
```

> tone 仅在 `data-cmx-skin` 为 `neo` 时生效（resolveSkin 解析后由 `applyNeoSkin` 加 `cmx-<name>-neo--<tone>` 变体 class）。

### 4. `data-cmx-skin` 取值

| 值 | 含义 |
| --- | --- |
| `neo`（默认） | Neo 皮肤（科技玻璃质感 + 渐变高光 + tone 变体） |
| `plain` / `default` | 经典表格 / 表单样式（无 Neo 装饰） |
| `none` / `flat` | 关掉所有自定义皮肤（grid 专属 `flat` 还会塌缩 padding） |

### 5. 页面级覆盖：`data-cmx-style-id`

把页内 `<template id="...">` 或 `<style id="...">` 节点的 CSS 作为 `layer='page'` 注入到该组件的 ShadowRoot，**优先级低于** `data-cmx-skin`（仅在 neo 基础上叠加）：

```html
<!-- 在页面定义一份"高级"风格变体 -->
<template id="cmx-form-neo-premium">
  :host(.cmx-form-neo) ui5-form-item::part(root) {
    background: linear-gradient(135deg,
      color-mix(in srgb, var(--neo-violet) 22%, var(--sapList_Background)),
      color-mix(in srgb, var(--neo-cyan) 12%, var(--sapList_Background)));
    border-color: var(--neo-violet);
  }
</template>

<!-- 在组件上引用（按需切换） -->
<cmx-ui5-form data-cmx-skin="neo" data-cmx-style-id="cmx-form-neo-premium" ...></cmx-ui5-form>
```

### 6. 换肤 API（`setSkinStyles`）

通过 `host.setSkinStyles({ idBase, neoCss })` 在运行时**完全替换**某层皮肤 CSS（适合"用户偏好"场景的整页换肤，不破坏组件结构）。

**监听换肤事件**：页面要响应运行时切肤（用户偏好 / URL `?skin=`），监听 `cmx-skin-changed` 事件（如 `host.<instanceId>` 上 `addEventListener('cmx-skin-changed', ...)`）或用 `MutationObserver` 观察 `data-cmx-skin` 属性变化，然后改写组件的 `data-cmx-skin` / `data-cmx-skin-tone`（组件 `attributeChangedCallback` 会重新挂皮肤）。

---

## 五·五、页面级换肤集成（如何让页面真正支持换肤）

> 这一节教你怎么在**页面层**接入换肤。第五节只覆盖 cmx 组件的 4 个开关；页面骨架（根 div、`.biz-bar`、`.neo-panel`、`.lvlbox`、自写的卡片）需自行处理。

### 1. 全部色值走 CSS 变量（暗色模式自动跟随）

UI5 在 light（`sap_horizon`）和 dark（`sap_horizon_dark` / `sap_horizon_hcb`）主题间切换时，会**重新设置** `:root` 上全套 `--sap-*` 值。**只要页面色值都通过 `var(--sap*)` 派生，就自动跟随，不需要写 dark 变体**。

```css
/* ✅ 正确：跟主题走 */
.card {
  background: var(--sapList_Background, #fff);
  color: var(--sapTextColor, #1d2d3e);
  border: 1px solid var(--sapGroup_ContentBorderColor, #d9d9d9);
}
.glass {
  background: color-mix(in srgb, var(--sapList_Background) 88%, transparent);
  /* ↑ color-mix 公式里用 --sapList_Background 作基底，
     light 主题时基底是 #fff、dark 主题是 #1a1f26，公式自动给两套值。 */
}

/* ❌ 错误：硬编码 #fff → 切 dark 主题时卡片变刺眼白底 */
.card { background: #ffffff; color: #000; }
```

### 2. 品牌色用 `--neo-*` token（统一品牌 + 支持 portal 主换色）

| 变量 | 含义 | 默认值 | 适用 |
| --- | --- | --- | --- |
| `--neo-cyan` | 品牌青 | `#00b4d8` | 强调 / 链接 / 进度 |
| `--neo-violet` | 品牌紫 | `#7c3aed` | 次强调 / 装饰 |
| `--neo-mint` | 品牌绿 | `#10b981` | 正向 / 成功 |
| `--neo-warn` | 警告橙 | `#f59e0b` | 告警 |
| `--neo-accent` / `--neo-accent-2` | 强调色 | 派生（= cyan / violet）| 全局强调 |
| `--neo-glass` / `--neo-glass-strong` | 玻璃质感 | 88% / 92% | 半透明卡片 |
| `--neo-border` / `--neo-border-subtle` | 边框 | 派生 | 卡片/分区边 |
| `--neo-glow` / `--neo-glow-violet` | 发光 | 派生 | 重点元素阴影 |

```css
/* ✅ 引用 token —— 门户换色（portal-module-theme.js）时整页联动 */
.title { color: var(--neo-accent); }
.kpi   { background: var(--neo-glass); border: 1px solid var(--neo-border-subtle); }

/* ❌ 硬编码 #00b4d8 → 门户换主色后该处不变 */
.title { color: #00b4d8; }
```

### 3. 页面级换肤触发（用户偏好 / URL `?skin=`）

页面要响应外部切肤，**改组件的 `data-cmx-skin` / `data-cmx-skin-tone` 即可**——组件的 `attributeChangedCallback` 会重新走 `applyNeoSkin` 注入新皮肤。

**native-page 范例**（JS 模块页 `render(ctx)` 末尾的"应用首选项"逻辑）：

```js
export default {
  defaultView: 'content',
  views: {
    async content(ctx) {
      const props = (ctx && ctx.props) || {}
      // … 正常返回 HTML …
      return `<div class="xxx-root" style="…">…</div>`
    }
  }
}

// render 返回后挂到 host.renderRoot，再走这段：
export function onMounted(host) {
  const params = new URLSearchParams(location.search)
  const skin  = params.get('skin')        // 'neo' | 'plain' | 'default' | 'none' | 'flat'
  const tone  = params.get('tone')        // 'cyan' | 'mint' | 'violet' | 'azure'
  const root  = host.renderRoot || host.shadowRoot
  root.querySelectorAll('cmx-revo-grid, cmx-ui5-form, cmx-toolbar, cmx-kpi-card, cmx-desc-list')
    .forEach(el => {
      if (skin) el.setAttribute('data-cmx-skin', skin)
      if (tone) el.setAttribute('data-cmx-skin-tone', tone)
      // attributeChangedCallback 自动重新挂皮肤
    })
}
```

> 关键点：改 attribute → 组件自动响应。**不要**直接 `setAttribute('style', ...)`、**不要**手动调用 `host.setSkinStyles()`（除非是替换皮肤源 CSS）。

### 4. 多主题共存（深色工作区 + 浅色卡片）

不要整体关 Neo 走硬编码。改在子组件上显式 `data-cmx-skin-tone` 覆盖父容器默认：

```html
<!-- 父容器是深色工作区背景： -->
<div style="background:var(--portal-workspace-bg); padding:10px;">
  <!-- 子卡片显式指定 tone，让它在深色背景下仍可读 -->
  <cmx-revo-grid data-cmx-skin-tone="azure" ...></cmx-revo-grid>
  <cmx-ui5-form   data-cmx-skin-tone="mint"  ...></cmx-ui5-form>
</div>
```

### 5. 自写皮肤源（不推荐，仅当 Neo 不够用时）

如真要自写（如某业务有特殊行业色），按 Neo 现有结构新增一份 `<cmx>-<name>-skin.js`：

```js
// packages/cmx-data-comp/src/lib/cmx-<name>-skin.js
export const CMX_<NAME>_SKIN_CSS = `
  :host(.cmx-<name>-xxx) {
    --xxx-accent: #your-color;
    /* … */
  }
  :host(.cmx-<name>-xxx) .inner { /* … */ }
`
```

组件内 `applyNeoSkin({ neoCss: CMX_<NAME>_SKIN_CSS, ... })` 即可接入。**自写前必须与用户沟通**（已有 4 套 tone：cyan/mint/violet/azure，多数场景够用）。

---

## 六、页面级 Neo 风覆盖（科技风页面才用）

如果页面要"科技感"（深色网格背景 + 玻璃质感卡片），在页头 `<style>` 复制 Neo token 派生块（与门户根 `portal-neo-theme.css` 对齐）。参考真实范例：`cmx-container/assets/portal/data/html-pages/sources/fi/cmxfico/gl/voucher-neo.html`。

**注意**：不要每页重定义不同数值的 `--neo-*`（会造成漂移）；要么直接用继承的门户根变量，要么完整复制门户根的派生块。

---

## 七、UI5 版本对齐提醒（已知漂移）

| 位置 | 版本 |
| --- | --- |
| `../../../../cmx-html-designer`（导出页 importmap） | **`2.22.0`**（硬编码） |
| 各 `package.json`（cmx-ui5-runtime / Designer / Portal） | `^2.23.2` |

**生成时按 `2.23.2`**（与 package.json 声明一致）。若发现导出页运行时 UI5 行为异常，提示用户检查 `html-utils.js` 的 importmap 版本漂移（AGENTS.md 七.3 红线）。

---

## 八、红线（呼应 AGENTS.md 七.6，生成时自检）

| 禁止 | 用什么替代 |
| --- | --- |
| `alert()` / `confirm()` | `cmxInfo` / `cmxWarn` / `cmxError`（来自 `cmx-data-comp` 的 `cmx-message-dialog`） |
| 原生 `<button>` | `<ui5-button>` |
| 原生 `<select>` | `<ui5-select>` + `<ui5-option>` |
| `div[role=toolbar]` + 原生 button | `<ui5-toolbar>` + `<ui5-toolbar-button>` |
| `div` 手搓模态/抽屉 | `<cmx-floating-dialog>` 或 `<ui5-dialog>` |
| 复制 `.panel` div 堆面板外壳 | 用 `.neo-panel` / `.lvlbox` 约定 class 或 `<ui5-panel>` |
| 硬编码色值 | `var(--sap*)` / `var(--neo*)` |
| 业务代码 `boot()` / `import bundle.esm.js` | UI5 装载只走 `cmx-ui5-runtime`（html-page 靠 importmap，native-page 靠 Portal 已 boot） |
| 关闭 Neo 走硬编码色（`data-cmx-skin="none"` + 背景写 `#fff`） | 保持 Neo + 改 `data-cmx-skin-tone` 换色 |

---

## 九、生成自检清单

交付前核对：
- [ ] 根 div 是标准骨架（flex column + height:100% + var(--sap*) + box-sizing）
- [ ] 所有颜色用 `var(--sap*)` / `var(--neo*)`，无硬编码
- [ ] 工具栏用 `ui5-bar` / `ui5-toolbar`，无原生 button 堆
- [ ] 多级分区用 `.lvlbox` / `.neo-panel` 约定 class
- [ ] cmx 组件不写 `data-cmx-skin`（用默认 Neo）
- [ ] 无 `alert()` / `confirm()` / 原生 `<select>` / 手搓模态
- [ ] 表格用 `cmx-revo-grid`，表单用 `cmx-ui5-form`，对话框用 `cmx-floating-dialog`
- [ ] **换肤已就绪**：所有色值走 `var(--sap*)` / `var(--neo-*)`；切 UI5 dark 主题后页面**自动跟随**无白底闪烁
- [ ] **默认走 Neo**：可视组件不显式 `data-cmx-skin="plain|default|none|flat"`；要换色用 `data-cmx-skin-tone`
- [ ] **不重复造皮肤源**：没有把 `CMX_FORM_NEO_SKIN_CSS` 全文复制到页内 `<style>`（要扩展用 `data-cmx-style-id`）
- [ ] **响应式换肤**（如支持用户偏好）：通过改 `data-cmx-skin` / `data-cmx-skin-tone` 触发，不直接 `setAttribute('style', ...)`

---

## 关键文件索引

| 用途 | 路径 |
| --- | --- |
| Portal Neo 根 token | `../../../../cmx-portal-manager` |
| Portal 全页壳样式 | `../../../../cmx-portal-manager` |
| 全门户默认 Neo 皮肤开关 | `../../../../cmx-portal-manager` |
| 表单 Neo 皮肤源 | `packages/cmx-data-comp/src/lib/cmx-form-neo-skin.js` |
| 表格 Neo 皮肤源 | `packages/cmx-data-comp/src/lib/cmx-grid-neo-skin.js` |
| **皮肤运行时（共享助手：resolveSkin / applyNeoSkin / setSkinStyle / applyPageStyleId）** | `packages/cmx-data-comp/src/lib/cmx-skin-runtime.js` |
| **KPI 卡片 Neo 皮肤源** | `packages/cmx-data-comp/src/lib/cmx-kpi-card-neo-skin.js` |
| **描述列表 Neo 皮肤源** | `packages/cmx-data-comp/src/lib/cmx-desc-list-neo-skin.js` |
| 根布局骨架范例页 | `cmx-container/assets/portal/data/html-pages/sources/fi/cmxfico/gl/erp-voucher-cnpc-ms.html` |
| Neo 风范例页（页头 token） | `cmx-container/assets/portal/data/html-pages/sources/fi/cmxfico/gl/voucher-neo.html` |
| **Neo 主题完整接入指引**（接入步骤 / 皮肤源结构 / 组件清单） | `neo-theme-onboarding.md` |
| 组件规范 | `frontend-conventions.md`（本目录，前端复用规范真源） |
