# IgniteUI 组件封装

> 何时读：需要 IgniteUI（igniteui-webcomponents）组件时查阅本文件；薄封装速查、厚封装 API、主题机制。
> 源码：`packages/cmx-data-comp/src/components/ignite/cmx-ignite-thin.js`、`cmx-ignite-factory.js`、`cmx-ignite-shared.js` 及 5 个厚封装文件

## 1. 薄封装机制

### 1.1 工厂函数

`defineThinIgnite(cmxTag, innerTag, opts)` 生成一个轻量 web component，内部包一个 `igc-*` 原生元素。

### 1.2 opts 参数

| 字段 | 类型 | 说明 |
|------|------|------|
| `attrs` | `string[]` | 透传的 attribute 名（同时作为 `observedAttributes`） |
| `events` | `string[]` | 要转发的 igc 原生事件名 |
| `valueProp` | `string` | 值属性名（`value`/`checked`/`selected`/`open`），存在时提供 `getValue()`/`setValue(v)` |
| `container` | `boolean` | 是否容器（带 slot 投影子节点），`display:block`；否则 `display:inline-block` |
| `slots` | `string[]` | 具名 slot 列表（`''` 表示默认 slot）；有值时渲染 `<slot>` 投影 light DOM |

### 1.3 事件转发

igc 原生事件转发为 `cmx-*` 自定义事件（`bubbles + composed`），规则由 `igcEventToCmx()` 实现：

| igc 事件 | cmx 事件 |
|----------|----------|
| `igcChange` | `cmx-change` |
| `igcInput` | `cmx-input` |
| `igcOpening` | `cmx-opening` |
| `igcSlideChanged` | `cmx-slide-changed` |

转换规则：去掉 `igc` 前缀，驼峰转 kebab-case，加 `cmx-` 前缀。

### 1.4 通用 API

| 方法 | 说明 |
|------|------|
| `getValue()` | 有 `valueProp` 时返回内部元素的值属性 |
| `setValue(v)` | 有 `valueProp` 时写入内部元素的值属性，返回 this |
| `focus()` | 透传到内部原生元素 |

### 1.5 注册

- `registerCmxIgniteThin()` 幂等注册全部原生 `igc-*` + 全部 `cmx-ignite-*` 薄封装。
- `import` cmx-ignite-thin.js 模块即触发注册（模块副作用）。
- **`<cmx-spreadsheet>` 是懒注册**：barrel 不静态 import 它（避免 6.4MB ignite-spreadsheet vendor 进首屏）。首次在 DOM 出现 `<cmx-spreadsheet>` 标签时才动态加载注册。报表页已知要用时可主动调 `preloadSheetComponents()` 预热。

## 2. 63 个薄封装 tag 速查表

### 2.1 输入类（14）

| cmxTag | innerTag | valueProp | 有 slot |
|--------|----------|-----------|---------|
| `cmx-ignite-input` | `igc-input` | `value` | ✓ |
| `cmx-ignite-textarea` | `igc-textarea` | `value` | ✓ |
| `cmx-ignite-mask-input` | `igc-mask-input` | `value` | ✓ |
| `cmx-ignite-date-time-input` | `igc-date-time-input` | `value` | ✓ |
| `cmx-ignite-file-input` | `igc-file-input` | `value` | ✓ |
| `cmx-ignite-checkbox` | `igc-checkbox` | `checked` | ✓ |
| `cmx-ignite-switch` | `igc-switch` | `checked` | ✓ |
| `cmx-ignite-radio` | `igc-radio` | `checked` | ✓ |
| `cmx-ignite-slider` | `igc-slider` | `value` | ✗ |
| `cmx-ignite-range-slider` | `igc-range-slider` | — | ✗ |
| `cmx-ignite-rating` | `igc-rating` | `value` | ✓ |
| `cmx-ignite-date-picker` | `igc-date-picker` | `value` | ✓ |
| `cmx-ignite-date-range-picker` | `igc-date-range-picker` | `value` | ✓ |
| `cmx-ignite-calendar` | `igc-calendar` | `value` | ✓ |

### 2.2 选择类（9）

| cmxTag | innerTag | valueProp | 有 slot |
|--------|----------|-----------|---------|
| `cmx-ignite-select` | `igc-select` | `value` | ✓ |
| `cmx-ignite-radio-group` | `igc-radio-group` | — | ✓ |
| `cmx-ignite-select-item` | `igc-select-item` | `selected` | ✓ |
| `cmx-ignite-select-group` | `igc-select-group` | — | ✓ |
| `cmx-ignite-select-header` | `igc-select-header` | — | ✓ |
| `cmx-ignite-dropdown` | `igc-dropdown` | `open` | ✓ |
| `cmx-ignite-dropdown-item` | `igc-dropdown-item` | `selected` | ✓ |
| `cmx-ignite-dropdown-group` | `igc-dropdown-group` | — | ✓ |
| `cmx-ignite-dropdown-header` | `igc-dropdown-header` | — | ✓ |

### 2.3 展示类（13）

| cmxTag | innerTag | valueProp | 有 slot |
|--------|----------|-----------|---------|
| `cmx-ignite-icon` | `igc-icon` | — | ✗ |
| `cmx-ignite-avatar` | `igc-avatar` | — | ✓ |
| `cmx-ignite-badge` | `igc-badge` | — | ✓ |
| `cmx-ignite-chip` | `igc-chip` | `selected` | ✓ |
| `cmx-ignite-divider` | `igc-divider` | — | ✗ |
| `cmx-ignite-card` | `igc-card` | — | ✓ |
| `cmx-ignite-card-header` | `igc-card-header` | — | ✓ |
| `cmx-ignite-card-content` | `igc-card-content` | — | ✓ |
| `cmx-ignite-card-media` | `igc-card-media` | — | ✓ |
| `cmx-ignite-card-actions` | `igc-card-actions` | — | ✓ |
| `cmx-ignite-linear-progress` | `igc-linear-progress` | `value` | ✓ |
| `cmx-ignite-circular-progress` | `igc-circular-progress` | `value` | ✓ |
| `cmx-ignite-rating-symbol` | `igc-rating-symbol` | — | ✓ |

### 2.4 布局类（23）

| cmxTag | innerTag | valueProp | 有 slot |
|--------|----------|-----------|---------|
| `cmx-ignite-accordion` | `igc-accordion` | — | ✓ |
| `cmx-ignite-expansion-panel` | `igc-expansion-panel` | `open` | ✓ |
| `cmx-ignite-tabs` | `igc-tabs` | — | ✓ |
| `cmx-ignite-tab` | `igc-tab` | `selected` | ✓ |
| `cmx-ignite-stepper` | `igc-stepper` | — | ✓ |
| `cmx-ignite-step` | `igc-step` | — | ✓ |
| `cmx-ignite-tree` | `igc-tree` | — | ✓ |
| `cmx-ignite-tree-item` | `igc-tree-item` | `selected` | ✓ |
| `cmx-ignite-carousel` | `igc-carousel` | — | ✓ |
| `cmx-ignite-carousel-slide` | `igc-carousel-slide` | `active` | ✓ |
| `cmx-ignite-nav-drawer` | `igc-nav-drawer` | `open` | ✓ |
| `cmx-ignite-nav-drawer-item` | `igc-nav-drawer-item` | `active` | ✓ |
| `cmx-ignite-nav-drawer-header-item` | `igc-nav-drawer-header-item` | — | ✓ |
| `cmx-ignite-navbar` | `igc-navbar` | — | ✓ |
| `cmx-ignite-button-group` | `igc-button-group` | — | ✓ |
| `cmx-ignite-splitter` | `igc-splitter` | — | ✓ |
| `cmx-ignite-tile-manager` | `igc-tile-manager` | — | ✓ |
| `cmx-ignite-tile` | `igc-tile` | — | ✓ |
| `cmx-ignite-dialog` | `igc-dialog` | `open` | ✓ |
| `cmx-ignite-chat` | `igc-chat` | — | ✓ |
| `cmx-ignite-button` | `igc-button` | — | ✓ |
| `cmx-ignite-icon-button` | `igc-icon-button` | — | ✗ |
| `cmx-ignite-toggle-button` | `igc-toggle-button` | `selected` | ✓ |

### 2.5 反馈类（4）

| cmxTag | innerTag | valueProp | 有 slot |
|--------|----------|-----------|---------|
| `cmx-ignite-banner` | `igc-banner` | `open` | ✓ |
| `cmx-ignite-snackbar` | `igc-snackbar` | `open` | ✓ |
| `cmx-ignite-toast` | `igc-toast` | `open` | ✓ |
| `cmx-ignite-tooltip` | `igc-tooltip` | `open` | ✓ |

### 2.6 薄封装使用示例

```html
<!-- 输入框：值通过 getValue/setValue 或 cmx-input 事件获取 -->
<cmx-ignite-input label="名称" placeholder="请输入"></cmx-ignite-input>

<!-- 复选框：valueProp=checked -->
<cmx-ignite-checkbox>同意条款</cmx-ignite-checkbox>

<!-- 对话框：valueProp=open，通过 setValue(true) 打开 -->
<cmx-ignite-dialog title="确认">
  <div slot="">内容</div>
  <div slot="footer">操作按钮</div>
</cmx-ignite-dialog>
```

```js
const input = document.querySelector('cmx-ignite-input')
input.setValue('hello')
console.log(input.getValue()) // 'hello'

input.addEventListener('cmx-input', (e) => {
  console.log('实时输入:', e.detail)
})
input.addEventListener('cmx-change', (e) => {
  console.log('值确认:', e.detail)
})
```

## 3. 5 个厚封装

厚封装绑定 CmxDataSet，有数据同步、字段映射、列模型适配等能力。与薄封装的区别：薄封装是纯展示/输入壳，不接 CmxDataSet。

### 3.1 cmx-ignite-combo（单选下拉）

> 源码：`cmx-ignite-combo.js`

| 方法 | 说明 |
|------|------|
| `setField(field)` | 设置字段定义；从 `field.options` 或 `field.editSettings.options` 加载选项 |
| `setItems(items)` | 设置选项列表 |
| `setColumnModel(model)` | 通过 `CmxColumnAdapter.toCmxForm(model)` 转换为 field |
| `setDataSet(dsOrRow)` | 绑定 CmxDataSet（游标同步）或直接传行对象 |
| `setValue(v, opts?)` | 设置选中值；`opts.silent` 为 true 时不派发事件 |
| `getValue()` | 读取当前标量选中值 |
| `setEditorMode(b?)` | 编辑器模式：抑制自带 label + 撑满宿主 |
| `setReadonly(b)` | 设置只读 |
| `focus()` / `open()` | 聚焦 / 展开下拉 |

| 事件 | `detail` | 说明 |
|------|----------|------|
| `cmx-value-changed` | `{ key, value, row }` | 选中值变化时派发 |

### 3.2 cmx-ignite-grid（数据表格）

> 源码：`cmx-ignite-grid.js`

| 方法 | 说明 |
|------|------|
| `setColumnModel(model)` | 通过 `CmxColumnAdapter.toIgniteGrid(model)` 转换列定义和汇总 |
| `setColumns(columns)` | 直接设置 Ignite 格式列定义 |
| `setOptions(opts)` | 设置选项（`selectionMode`/`rowHeight`/`viewHeight`/`fillHeight`/`primaryKey` 等） |
| `setTotals(totals)` | 设置汇总配置 |
| `setDataSet(dsOrRows, sel?)` | 绑定 CmxDataSet 或行数组；`sel` 可传 `{ selectedId, selectedIds }` |
| `addRow(row, opts?)` | 新增行，返回新增的行对象 |
| `removeRows(ids)` | 按 id 删除行，返回已删除行数组 |
| `getSelectedIds()` | 获取选中行 id 列表 |
| `getSource()` | 获取当前行数据副本 |

| 事件 | `detail` | 说明 |
|------|----------|------|
| `cmx-row-selected` | `{ id }` | 单选模式下选中行 |
| `cmx-row-selection-change` | `{ ids }` | 多选模式下选中变化 |
| `cmx-cell-changed` | `{ id, key, value, row }` | 单元格编辑完成 |
| `cmx-row-added` | `{ id, row, index }` | 新增行 |
| `cmx-row-removed` | `{ ids, rows }` | 删除行 |

默认选项：`selectionMode: 'single'`、`rowHeight: 36`、`viewHeight: 440`、`primaryKey: 'id'`。

### 3.3 cmx-ignite-input（字段输入框）

> 源码：`cmx-ignite-input.js`

| 方法 | 说明 |
|------|------|
| `setField(field)` | 设置字段定义（label/placeholder/type/readonly） |
| `setColumnModel(model)` | 通过 `CmxColumnAdapter.toCmxForm(model)` 转换为 field |
| `setDataSet(dsOrRow)` | 绑定 CmxDataSet（游标同步）或直接传行对象 |
| `getValue()` | 读取当前输入值 |

| 事件 | `detail` | 说明 |
|------|----------|------|
| `cmx-value-changed` | `{ key, value, row }` | 值变化时派发 |

number 类型字段自动转为数值；支持 `field.onChange` 回调。

### 3.4 cmx-ignite-list（行列表）

> 源码：`cmx-ignite-list.js`

| 方法 | 说明 |
|------|------|
| `setColumnModel(model)` | 设置标题字段（`toTitleCols`/`toTitleCol`）和副标题字段（`iconCol`） |
| `setItems(items)` | 设置静态数据 |
| `setDataSet(dsOrRows)` | 绑定 CmxDataSet 或行数组 |
| `setSkinStyles(cssText)` | 注入页面级 CSS 到组件 Shadow DOM |

| 事件 | `detail` | 说明 |
|------|----------|------|
| `cmx-row-selected` | `{ id, row, index }` | 行选中 |
| `cmx-item-selected` | `{ id, row, index }` | 项选中（同 `cmx-row-selected`） |

布局模式：`data-cmx-layout="card"` 使用自定义卡片布局；默认使用 `igc-list`。
皮肤注入：`data-cmx-style-id` 引用同根 `<template>`/`<style>` 文本，或 `setSkinStyles()` 编程注入。

### 3.5 cmx-ignite-gauge（仪表盘）

> 源码：`cmx-ignite-gauge.js`

| 方法 | 说明 |
|------|------|
| `setOptions(opts)` | 设置选项（`minimum`/`maximum`/`width`/`height`） |
| `setValue(value)` | 设置当前值 |
| `setDataSet(dsOrRow, opts?)` | 绑定 CmxDataSet 或行对象；`opts.valueField` 指定值字段 |

| 事件 | `detail` | 说明 |
|------|----------|------|
| `cmx-value-changed` | `{ value, row, field }` | 值变化时派发 |

仪表类型由 `data-cmx-gauge-type` 属性决定：`radial`（径向）、`linear`（线性）、`bullet`（子弹图）。

## 4. ensureIgniteTheme

`ensureIgniteTheme()` 确保主题就绪（幂等），所有 `register-ignite-*` 在 `defineComponents` 前调用。

| 步骤 | 说明 |
|------|------|
| 检测明暗 | 优先读 `--sapBackgroundColor` 亮度，降级到 `prefers-color-scheme` |
| 配置 variant | `configureTheme('bootstrap', dark ? 'dark' : 'light')` |
| 注入 palette CSS | 亮/暗各取一份 bootstrap palette，`?inline` 拿到 CSS 文本注入 `document.head`（id=`cmx-ignite-theme`） |
| 订阅主题切换 | 监听 `cmx-portal-theme-change` 事件，门户切换时自动重新应用 |

不注入 palette 会导致下拉透明、尺寸塌陷、文字叠加。

## 5. 何时选 IgniteUI

| 场景 | 推荐 |
|------|------|
| UI5 和 cmx 都不满足时 | IgniteUI |
| 需要 Ignite 风格的高级组件（slider/rating/stepper/carousel/gauge 等） | IgniteUI |
| 需要数据绑定（combo/grid/list/input） | 厚封装 |
| 纯展示/输入，无数据绑定 | 薄封装 |

## 6. 厚封装代码示例

```html
<!-- combo 绑定 DataSet -->
<cmx-ignite-combo></cmx-ignite-combo>
```

```js
const combo = document.querySelector('cmx-ignite-combo')
combo.setField({
  key: 'status',
  label: '状态',
  options: [
    { value: 'active', label: '启用' },
    { value: 'inactive', label: '停用' }
  ]
})
combo.setDataSet(ds)
combo.addEventListener('cmx-value-changed', (e) => {
  console.log('选中:', e.detail.value)
})
```

```html
<!-- grid 绑定 DataSet -->
<cmx-ignite-grid></cmx-ignite-grid>
```

```js
const grid = document.querySelector('cmx-ignite-grid')
grid.setColumnModel(model)
grid.setOptions({ selectionMode: 'single', fillHeight: true })
grid.setDataSet(ds)
grid.addEventListener('cmx-row-selected', (e) => {
  console.log('选中行:', e.detail.id)
})
```
