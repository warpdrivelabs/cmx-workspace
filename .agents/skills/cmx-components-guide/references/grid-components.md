# 表格组件：cmx-revo-grid / cmx-tabulator / cmx-ignite-grid

> 何时读：需要数据表格（虚拟滚动 / 编辑 / 聚合 / 树表）时；选型 cmx-revo-grid vs cmx-tabulator vs cmx-ignite-grid 时；查 setOptions 全参数 / 事件 detail / 声明式属性时。

> 源码：
> - `packages/cmx-data-comp/src/components/cmx-revo-grid.js`
> - `packages/cmx-data-comp/src/components/cmx-tabulator.js`
> - `packages/cmx-data-comp/src/components/ignite/cmx-ignite-grid.js`

---

## 一、cmx-revo-grid（首选表格）

基于 RevoGrid 的数据表格 Web Component，Shadow DOM 内嵌原生 `<revo-grid>`。列定义只能来自 `CmxColumnModel`（运行时 `setColumnModel(model)`，声明式 `data-cmx-model-id`）。

- **tag**：`<cmx-revo-grid>`
- **列定义入口**：仅 `setColumnModel(model)` / `data-cmx-model-id`（由 `init-page-models` 注入）。不提供 `setColumns` / `setHeaderGroups`。

### 1.1 setOptions(opts) 全参数表

源自 `DEFAULT_OPTIONS`，`setOptions` 增量合并。

| 参数 | 默认值 | 取值 / 说明 |
|------|--------|-------------|
| `selectionMode` | `'single'` | `'none'` \| `'single'` \| `'multi'` |
| `rowHeight` | `32` | 数据行高（px） |
| `headerRowHeight` | `null` | 表头行高；`null` = 与 `rowHeight` 一致，显式数字覆盖 |
| `viewHeight` | `300` | 非 fillHeight 时表格视口高度（px） |
| `fillHeight` | `false` | `true` 时填满父容器（flex 布局，监听 ResizeObserver） |
| `virtualScroll` | `true` | 虚拟滚动；`false` 关闭横向+纵向虚拟滚动 |
| `showRowIndex` | `true` | 显示序号列（revo-grid 原生 rowHeaders） |
| `rowIndexLabel` | `'序号'` | 序号列表头文字 |
| `rowIndexWidth` | `40` | 序号列宽度（px） |
| `showTotals` | `true` | 是否显示合计行；`true` 且未显式 `totals` 时自动汇总所有数值列 |
| `totals` | `null` | `{ label?, columns?: string[], extra?: (rows, sums) => {}, aggMap?: {[key]:'sum'\|'avg'\|'max'\|'min'\|'count'} }` |
| `readonly` | `false` | 整表只读（旧开关，优先级低于 `editable`） |
| `editable` | `false` | 编辑总开关；`true` 才允许进编辑（仍受列 `editMode='readonly'` 约束）。未显式设时回退 `!readonly` |
| `theme` | `'auto'` | `'auto'` \| `'default'` \| `'compact'` \| `'darkMaterial'` \| `'darkCompact'`；`auto` 检测暗色 |
| `range` | `false` | 区域选择；`selectionMode='multi'` 时自动开启 |
| `minRows` | `0` | 最少显示行数；不足时补占位行（`__cmxFiller`，编辑/聚焦忽略） |
| `stretch` | `true` | 列宽按比例拉伸占满视口；`false` 保留原始列宽 |
| `editTrigger` | `'dblclick'` | `'dblclick'`（双击/Enter 进编辑）\| `'click'`（单击即编辑） |
| `alternateRowColor` | `true` | 隔行换色（斑马纹）。仅影响 Neo 皮肤内置偶数行背景；非 Neo 皮肤本身无内置交替色，本选项对其无影响。`false` 时所有行同色 |
| `showRequiredMark` | `true` | 列头显示必填标识（红色 *）；只读展示页可 `setOptions({ showRequiredMark: false })` 关闭 |
| `cellTooltip` | `true` | 单元格截断悬浮提示。列宽不足导致文本被 ellipsis 裁剪时，鼠标悬浮 250ms 显示完整内容的跟随浮层。`false` 关闭。表头/序号列不提示 |
| `allowTextSelect` | `false` | 只读单元格文本选择。`true` 时数据单元格开 `user-select:text`，允许鼠标拖选文本 + Ctrl+C 复制选中部分（capture 阶段放行原生 copy，不被 revo-grid 整格复制接管）。只读展示页推荐开启；编辑态开启会与编辑器点击冲突，不建议。复制整格值不需要此选项：点单元格聚焦后 Ctrl+C 由 revo-grid 内置剪贴板支持 |
| `resize` | `false` | 手动拖动调节列宽。`true` 时表头右缘出现拖把，用户可拖动调宽。拖动过的列宽被锁定（不参与 stretch 再分配），其余列继续自适应铺满视口。列的 `width:{min,max}` 约束拖动范围。`setColumnModel` 时清空历史拖动记录 |

### 1.2 主要 API

| 方法 | 签名 | 说明 |
|------|------|------|
| `setColumnModel(model)` | `(CmxColumnModel) => void` | 设置列结构+分组表头+合计；订阅 `columns-changed` 自动重同步 |
| `setOptions(opts)` | `(Partial<DEFAULT_OPTIONS>) => void` | 增量合并运行时选项 |
| `setDataSet(dsOrRows, sel)` | `(CmxDataSet \| rows[], sel?) => void` | 绑定 CmxDataSet 或纯数组；`sel={selectedId, selectedIds, preserveScroll}` |
| `refreshLayout()` | `() => void` | 强制刷新尺寸/拉伸/视口（popover 打开、tab 切回时调） |
| `addRow(row, opts)` | `(row, {scrollIntoView=true}) => row\|null` | 追加行（需带 id）；DataSet 模式走 `ds.addRow` |
| `removeRows(ids)` | `(string[]) => row[]` | 按 id 删除行 |
| `getSelectedIds()` | `() => string[]` | 当前多选集合（按 `_rows` 顺序） |
| `getSource()` | `() => row[]` | 当前数据行浅拷贝 |
| `setEditable(flag)` | `(boolean) => this` | 编辑态总开关 |
| `isEditable()` | `() => boolean` | 当前是否可编辑 |
| `setSkinStyles(cssText, layer)` | `(string, 'neo'\|'page'\|'custom') => this` | 注入皮肤 CSS |
| `enableDictEcho(ctx, host)` | `async ({coord?, dbId?}, host?) => Promise<void>` | 字典外键回显（见 1.5） |

### 1.3 事件

| 事件名 | detail | 触发时机 |
|--------|--------|----------|
| `cmx-columns-changed` | `{ model, columns }` | 列模型变更后重同步 |
| `cmx-row-selected` | `{ id }` | 单选行变化 |
| `cmx-row-selection-change` | `{ ids }` | 多选行变化 |
| `cmx-cell-changed` | `{ id, key, value, row }` | 单元格编辑完成（含 dependents 派生） |
| `cmx-row-added` | `{ id, row, index }` | `addRow` 后 |
| `cmx-row-removed` | `{ ids, rows }` | `removeRows` 后 |
| `cmx-cell-link-click` | `{ key, rowId, actionRef }` | `display.mode='link'` / `'actions'` 单元格点击（link 用列级 `display.link.actionRef`，actions 按钮级 `data-cmx-action` 优先） |
| `cmx-cell-invalid` | `{ id, key, value, row, message }` | 编辑校验失败（不阻断写回） |

### 1.4 声明式属性

| 属性 | 形式 | 说明 |
|------|------|------|
| `data-cmx-options` | JSON | 等价 `setOptions` |
| `data-cmx-rows` | JSON | 等价 `setDataSet(rows)`（纯数组） |
| `data-cmx-fill-height` | 布尔 | 快捷 `setOptions({fillHeight:true})` |
| `data-cmx-model-id` | 字符串 | CmxColumnModel 实例 id（`init-page-models` 注入调 `setColumnModel`） |
| `data-cmx-skin` | `neo`\|`plain`\|`default`\|`none`\|`flat` | 皮肤；未设时默认 `neo`（可由 `globalThis.__cmxDefaultGridSkin` 覆盖） |
| `data-cmx-skin-tone` | `cyan`\|`azure`\|`violet`\|`mint` | Neo 强调色 |
| `data-cmx-style-id` | 字符串 | 同页 `<template>` id，注入覆盖样式 |
| `data-cmx-embed` | 布尔 | 内嵌于 combo/dict 弹层，默认不套 Neo（除非显式 `data-cmx-skin`） |
| `data-cmx-borderless` / `data-cmx-flat` | 布尔 | 无边框扁平样式 |

### 1.5 enableDictEcho（字典外键回显）

扫描列模型的 `refDict`，逐典预加载全量条目（`POST /api/dct/data/search`），给每列 `display` 挂 resolver（id->名称），再 refresh 重绘。未命中时优雅降级返回原 id，不阻断渲染。

```javascript
const grid = document.querySelector('#grid')
await grid.enableDictEcho({ coord: globalCoord, dbId: 'default' })
// coord / dbId 可省略，host 缺省用全局 fetch
```

> `dict-select` 编辑列（`edit.mode === 'cmx-dict-select'`）有独立回写路径，`enableDictEcho` 自动跳过避免冲突。

### 1.6 编辑态切换

```javascript
// 双击进编辑（默认）
grid.setOptions({ editable: true, editTrigger: 'dblclick' })

// 单击即编辑（旧默认）
grid.setOptions({ editable: true, editTrigger: 'click' })

// 运行时切只读
grid.setEditable(false)

// 列级 edit.trigger 覆盖全表：列上 edit.trigger='click' 优先于 options.editTrigger
```

### 1.7 操作列（按钮组）—— `display.mode='actions'`

一列多按钮的行级操作（编辑/删除/审批/提交/作废…），用 CmxColumn 的 `display.mode='actions'` + `display.actions[]`。**首选此模式，不要手写 cellTemplate**——`cmx-column-adapter.js` 已自动渲染圆角边框按钮组、配色、点击事件派发。

```js
// 程序化构造（cmx-revo-grid 列定义只能来自 setColumnModel）
grid.setColumnModel(new C.CmxColumnModel({ members: [
  // …数据列…
  new C.CmxColumn({ id: '_action', caption: '操作', dataType: 'VARCHAR', width: '180px',
    edit: { mode: 'readonly' },
    display: { mode: 'actions', actions: [
      { text: '编辑',  actionRef: 'edit',    icon: 'edit' },
      { text: '审批',  actionRef: 'approve', variant: 'emphasized' },
      { text: '删除',  actionRef: 'delete',  variant: 'negative' },
    ] } }),
]}))
```

#### `display.actions[]` 单按钮字段

| 字段 | 含义 | 取值 |
| --- | --- | --- |
| `text` | 按钮文字 | string（空则只显 icon） |
| `actionRef` | **必填**，业务路由标识 | 任意字符串（无则该按钮被过滤） |
| `icon` | UI5 图标名 | 如 `"edit"` / `"delete"` |
| `variant` | 视觉变体 | `""`（默认蓝文字+浅边框）/ `"emphasized"`（强调蓝填充）/ `"negative"`（红，危险/不可逆） |
| `color` | 自定义颜色（覆盖 variant） | CSS 色，建议 `var(--sap*)` |
| `visible` | **按行显隐**（程序化构造时） | `(model) => boolean`，返回假值则该行不渲染此按钮；不传则恒显示 |

> **`variant` 三档语义**：默认（普通操作：提交、查看、克隆）/ `emphasized`（主操作、正向关键动作：通过、审批）/ `negative`（危险不可逆：作废、驳回、删除）。优先级：`color` > `variant` > 默认。

#### 点击事件 `cmx-cell-link-click`

点击按钮后 grid 派发（actions 列每个按钮独立 `actionRef`，读 DOM 的 `data-cmx-action`）：

```js
grid.addEventListener('cmx-cell-link-click', (e) => {
  const { key, rowId, actionRef } = e.detail
  // rowId 是 revo-grid 内部行索引，需反查真实业务 id：
  const ds = grid._ds
  const row = ds?.rows?.[parseInt(rowId, 10)]
  const realRow = row?.toPlainObject ? row.toPlainObject() : row
  if (actionRef === 'edit')   openEdit(realRow.id)
  if (actionRef === 'delete') confirmDelete(realRow.id)
})
```

> **注意 `rowId` 是 revo-grid 行索引，不是业务主键**——必须用 `grid._ds.rows[rowId]` 反查。`link` 模式（单按钮链接列）共用本事件，但用列级 `display.link.actionRef`。

#### 按行状态显隐按钮（`visible(model)`，仅程序化 CmxColumn）

同一列按行状态显示不同按钮组（待办列表：草稿行显"提交/作废"、审批中行显"通过/驳回"），用 `display.actions[].visible(model)`。**这是声明式 jsonc 做不到的**（函数值无法序列化），只能程序化构造：

```js
const is = (s) => (m) => m.doc_status === s
new C.CmxColumn({ id: '_action', caption: '操作', dataType: 'VARCHAR', width: '180px',
  edit: { mode: 'readonly' },
  display: { mode: 'actions', actions: [
    { text: '提交',     actionRef: 'submit',  visible: is('draft') },
    { text: '作废',     actionRef: 'abort',   variant: 'negative',   visible: is('draft') },
    { text: '通过',     actionRef: 'approve', variant: 'emphasized', visible: is('approving') },
    { text: '驳回',     actionRef: 'reject',  variant: 'negative',   visible: is('approving') },
    { text: '修改重提', actionRef: 'clone',   visible: is('rejected') },
  ] } })
```

#### cellTemplate（极端自定义渲染，非按钮场景）

`display.mode='actions'` 覆盖了绝大多数"一列多按钮"场景。仅当按钮之外的渲染需求出现时（单元格内嵌进度条、图标+多行文本、行内 mini 图表等非按钮内容），才在 CmxColumn 上直接挂 `cellTemplate`：

```js
new C.CmxColumn({ id: 'progress', caption: '进度', dataType: 'INT', width: '160px',
  cellTemplate: (h, props) => {
    const v = Number(props.model?.progress ?? 0)
    return h('div', { style: { display: 'flex', alignItems: 'center', gap: '8px', height: '100%' } }, [
      h('div', { style: { flex: '1', height: '6px', background: '#e5e5e5', borderRadius: '3px' } }, [
        h('div', { style: { width: `${v}%`, height: '100%', background: '#0070f2', borderRadius: '3px' } })
      ]),
      h('span', { style: { fontSize: '0.75rem' } }, `${v}%`)
    ])
  }
})
```

> `cellTemplate` / `cellProperties` 已支持经 `new CmxColumn({...})` 直接传入（`toDescriptor()` 透传，`_leafDescriptorToRevoCol` 优先采用调用方挂的函数）。操作类需求仍应首选 `display.mode='actions'`，只有非按钮的自定义单元格才落到 cellTemplate。

### 1.8 列宽与拉伸（px / 百分比 / stretch）

`CmxColumn.width` 支持四种格式，与 `stretch` 选项（默认 `true`）协同决定最终列宽：

| width 格式 | 语义 | stretch=true 行为 |
|---|---|---|
| `'120px'` / `'100'` / `100` | 固定像素 | base size；当所有 px 列总和 < 视口时按比例放大铺满，超过视口保持原值（横向滚动） |
| `'20%'` | **相对主区视口的百分比** | 固定占 `主区宽 × percent/100`，**不参与二次拉伸**；px 列在剩余空间内 stretch |
| `'flex'` | 弹性列 | 语义等同不设 width（base 100，参与 stretch 均分） |
| `{ size, min, max }` | 对象形式 | size 作 base，min/max 夹取；同 px 列参与 stretch |

**规则要点**：
- 百分比列的目标宽 = `floor(主区宽 × percent/100)`，至少 1px。
- 混合场景：百分比列先按字面值占位，普通 px 列在 `主区 − 百分比列总和` 的剩余空间内按比例 stretch。
- 百分比之和 ≥ 100% 时，百分比列仍按字面值（允许总宽超出视口 → 横向滚动），普通列保持原 base 不放大。
- **冻结列（`frozen:'left'` / `frozen:'right'`）与 stretch 共存**：冻结列保持各自固定宽度不参与拉伸（用户拖动锁定值优先，否则取 width），主区列在 `视口宽 − 冻结列总宽` 内按上述规则 stretch。这样"右侧冻结操作列 + 主区铺满屏幕"可同时实现。需要全部列严格按 width 不拉伸时由调用方显式设 `stretch:false`。

**手动拖动列宽（resize）**：`resize:true` 开启后表头右缘出现拖把，用户可拖动调宽。用户拖动过的列宽会被**锁定**（与百分比列同等地位，不参与 stretch 再分配），其余列继续在剩余空间自适应——这是企业表格的标准行为（调过的列固定，其余自适应）。`setColumnModel` 时清空历史拖动记录。

```javascript
// 百分比示例：名称列占 40%，其余 px 列在剩余 60% 内放大
new C.CmxColumn({ id: 'name', caption: '名称', dataType: 'VARCHAR', width: '40%' })
new C.CmxColumn({ id: 'code', caption: '编码', dataType: 'VARCHAR', width: '120px' })

// 严格 px（关闭 stretch）
grid.setOptions({ stretch: false })
```

> 列宽不足导致单元格文本被 ellipsis 裁剪时，`cellTooltip`（默认 `true`）会在鼠标悬浮 250ms 后显示完整内容的跟随浮层——无需额外配置。

---

## 二、cmx-tabulator（树表备选）

基于 Tabulator 6.4 的数据表格 Web Component，内置 treegrid（`dataTree`）。API 与 revo-grid 对齐，额外提供树形操作。

- **tag**：`<cmx-tabulator>`
- **列定义**：`setColumnModel(model)` / `setColumns(columns)` / `data-cmx-columns`

### 2.1 setOptions 参数表

源自 `DEFAULT_OPTIONS`，`setOptions` 增量合并。

| 参数 | 默认值 | 取值 / 说明 |
|------|--------|-------------|
| `layout` | `'fitColumns'` | Tabulator 布局模式 |
| `height` | `'100%'` | 表格高度 |
| `selectableRows` | `1` | `false`\|`1`\|`true`（多选）；由 `selectionMode` 自动映射 |
| `selectionCheckbox` | `false` | 是否显示选择复选框列 |
| `selectionCheckboxWidth` | `36` | 复选框列宽 |
| `rowHeight` | `null` | 行高（null=Tabulator 默认） |
| `reactiveData` | `false` | 响应式数据 |
| `movableColumns` | `true` | 列可拖拽移动 |
| `resizableColumnFit` | `false` | 列宽自适应 |
| `pagination` | `false` | `false`\|`'local'`\|`'remote'`；布尔 `true` 映射为 `'local'` |
| `paginationSize` | `20` | 每页条数 |
| `placeholder` | `'暂无数据'` | 空数据占位文案 |
| `index` | `'id'` | 行唯一标识字段 |
| `autoColumns` | `false` | 自动生成列 |
| `dataTree` | `false` | **树形表格总开关** |
| `parentField` | `'parentId'` | 扁平行父键字段（flat->nested 重建层级） |
| `dataTreeChildField` | `'_children'` | 嵌套子数组字段（与 Tabulator 对齐） |
| `dataTreeChildIndent` | `14` | 每层缩进像素 |
| `treeColumn` | `null` | 展开把手所在列 id（null=第一列） |
| `treeStartExpanded` | `false` | 初始展开：`true` 全展开 / `false` 全折叠 / `number` 展开前 N 层 / `number[]` 指定层级 |

### 2.2 树操作 API

| 方法 | 说明 |
|------|------|
| `expandAll()` | 展开全部树节点；记入 `_expandedIds` 快照 |
| `collapseAll()` | 折叠全部顶层节点；清空快照 |
| `expandRow(id)` | 展开指定 id 行 |
| `collapseRow(id)` | 折叠指定 id 行 |
| `toggleRow(id)` | 切换展开/折叠态 |
| `getExpandedIds()` | 当前展开节点 id 列表（快照） |

> 刷新数据时通过 `_expandedIds` 快照保持展开态（同 `cmx-web-treeview`）。

### 2.3 事件

除与 revo-grid 共有的 `cmx-row-selected` / `cmx-row-selection-change` / `cmx-cell-changed` / `cmx-row-added` / `cmx-row-removed` 外，tabulator 专属：

| 事件名 | detail | 触发时机 |
|--------|--------|----------|
| `cmx-tree-row-expanded` | `{ id, row, level }` | 树节点展开 |
| `cmx-tree-row-collapsed` | `{ id, row, level }` | 树节点折叠 |
| `cmx-tabulator-ready` | `{ table }` | 表格构建完成 |
| `cmx-tabulator-data-changed` | `{ rows }` | 数据变化 |
| `cmx-tabulator-filtered` | `{ filters, rowCount }` | 过滤后 |
| `cmx-tabulator-sorted` | `{ sorters, rowCount }` | 排序后 |
| `cmx-tabulator-page-loaded` | `{ page }` | 分页加载 |
| `cmx-tabulator-column-moved` | `{ field, columns }` | 列移动 |
| `cmx-tabulator-cell-edited` | `{ id, key, value, row, cell }` | 单元格编辑（含原生 cell 引用） |

### 2.4 声明式属性（更多）

除 `data-cmx-options` / `data-cmx-rows` / `data-cmx-columns` / `data-cmx-model-id` / `data-cmx-master-slave-id` / `data-cmx-dataset-id` 外，树形专属：

| 属性 | 说明 |
|------|------|
| `data-cmx-tree` | 布尔，开启树形（等价 `dataTree:true`） |
| `data-cmx-parent-field` | 父键字段 |
| `data-cmx-tree-column` | 展开把手列 id |
| `data-cmx-tree-child-field` | 子数组字段 |
| `data-cmx-tree-start-expanded` | `true`\|`false`\|数字\|JSON 数组 |
| `data-cmx-icon-field` | 树列图标字段（列模型 `iconCol` 优先） |

布局类：`data-cmx-height` / `data-cmx-layout` / `data-cmx-pagination` / `data-cmx-page-size` / `data-cmx-selection-mode` / `data-cmx-placeholder` / `data-cmx-movable-columns` / `data-cmx-reactive-data` / `data-cmx-auto-columns` / `data-cmx-readonly` / `data-cmx-skin` / `data-cmx-borderless` / `data-cmx-flat`。

### 2.5 何时选 tabulator 而非 revo-grid

- 需要**树形表格**（父子层级 + 展开/折叠）。
- 需要 Tabulator 特有能力：列拖拽移动、本地/远程分页、列宽 `fitColumns` 自适应。
- revo-grid 的多级表头/虚拟滚动/编辑器注册表不满足时。

---

## 三、cmx-ignite-grid（IgniteUI 风格）

基于 Ignite UI `igc-grid` 的封装，API 与 revo-grid 对齐但能力更精简。

- **tag**：`<cmx-ignite-grid>`
- **列定义**：`setColumnModel(model)` / `setColumns(columns)`

### 3.1 setOptions 参数表

源自 `DEFAULT_OPTIONS`。

| 参数 | 默认值 | 取值 / 说明 |
|------|--------|-------------|
| `selectionMode` | `'single'` | `'none'` \| `'single'` \| `'multi'`（映射 igc `none`\|`single`\|`multiple`） |
| `rowHeight` | `36` | 行高 |
| `viewHeight` | `440` | 非 fillHeight 时高度 |
| `fillHeight` | `false` | 填满父容器 |
| `virtualScroll` | `true` | 虚拟滚动 |
| `showRowIndex` | `false` | 序号列 |
| `readonly` | `false` | 只读 |
| `totals` | `null` | 合计配置 |
| `primaryKey` | `'id'` | 主键字段（igc-grid 必需） |

### 3.2 API（与 revo-grid 对齐）

`setColumnModel(model)` / `setColumns(columns)` / `setOptions(opts)` / `setTotals(totals)` / `setDataSet(dsOrRows, sel)` / `addRow(row, opts)` / `removeRows(ids)` / `getSelectedIds()` / `getSource()`。

### 3.3 事件

`cmx-row-selected` / `cmx-row-selection-change` / `cmx-cell-changed` / `cmx-row-added` / `cmx-row-removed`（detail 结构同 revo-grid）。

### 3.4 声明式属性

`data-cmx-options` / `data-cmx-columns` / `data-cmx-rows` / `data-cmx-totals`。

### 3.5 何时选

- 页面已重度使用 IgniteUI 体系，需视觉/交互一致。
- 需要 igc-grid 原生能力（列类型 dataType、内联编辑 cellEditDone）。
- revo-grid/tabulator 不满足时。

---

## 四、三者选型对比

| 维度 | cmx-revo-grid | cmx-tabulator | cmx-ignite-grid |
|------|---------------|---------------|-----------------|
| **底层** | RevoGrid（Stencil） | Tabulator 6.4 | Ignite UI igc-grid |
| **树形表格** | ❌ | ✅ 内置 dataTree | ❌ |
| **多级表头** | ✅（含孤立叶合并修复） | ✅（children 嵌套） | ❌ |
| **虚拟滚动** | ✅ 横向+纵向 | ✅ | ✅ |
| **编辑态** | ✅ editable+editTrigger+列级 trigger | ✅（列 editor 类型映射） | ✅ cellEditDone |
| **字段编辑器注册表** | ✅ cmx-form-field-registry | ❌ 内置映射 | ❌ igc 原生 |
| **合计行** | ✅ pinnedBottom+自动汇总+aggMap | ✅ bottomCalc | ✅ totals |
| **列拉伸 stretch** | ✅ 按比例铺满 | ✅ fitColumns | ❌ |
| **字典回显 enableDictEcho** | ✅ | ❌ | ❌ |
| **Neo 皮肤** | ✅ 默认 | ❌（SAP 变量主题化） | ❌ |
| **暗色主题** | ✅ auto 检测 | ✅ SAP 变量 | 依赖 igc |
| **CmxColumnModel** | ✅ 唯一入口 | ✅ | ✅ |
| **CmxDataSet 绑定** | ✅ | ✅ | ✅ |
| **分页** | ❌ | ✅ local/remote | ❌ |
| **列拖拽移动** | ❌ | ✅ movableColumns | ❌ |
| **首选场景** | 通用数据表格 | 树表/分页/列拖拽 | IgniteUI 体系内 |

---

## 五、常见操作配方

### 5.1 绑定数据：setColumnModel + setDataSet

```javascript
const grid = document.querySelector('#grid')
// 列模型由 init-page-models 注入（data-cmx-model-id），或运行时绑定：
grid.setColumnModel(window.__pageModels.orderColumns)
// 绑定 CmxDataSet（与 form 共享同一数据源）
grid.setDataSet(window.__pageModels.orderDs, { selectedId: 'ORD-001' })
// 或纯数组
grid.setDataSet([{ id: 1, name: 'A' }, { id: 2, name: 'B' }])
```

### 5.2 行操作：addRow / removeRows / getSelectedIds

```javascript
grid.addRow({ id: 'NEW-1', name: '新行' }, { scrollIntoView: true })
grid.removeRows(grid.getSelectedIds())
const ids = grid.getSelectedIds()  // 多选
```

### 5.3 编辑态：setEditable + editTrigger + cmx-cell-changed 监听

```javascript
grid.setOptions({ editable: true, editTrigger: 'dblclick' })
grid.addEventListener('cmx-cell-changed', (e) => {
  const { id, key, value, row } = e.detail
  console.log('编辑', id, key, '=>', value)
})
// 校验失败监听
grid.addEventListener('cmx-cell-invalid', (e) => {
  console.warn('校验失败', e.detail.message)
})
```

### 5.4 导出 JSON：toJSON / toPlainRows

导出方法在 `CmxDataSet` 上（grid 通过 `setDataSet(ds)` 绑定后即可用），不在 grid 组件本身：

```javascript
const ds = window.__pageModels.orderDs
// 纯行数组（不含内部字段）
const rows = ds.toPlainRows()
// 含子表嵌套
const rowsWithChildren = ds.toPlainRows(true)
// 序列化（含列顺序、子表结构）
const json = ds.toJSON()
```

> grid 组件本身的 `getSource()` 返回当前数据行浅拷贝（含 `__cmxRowClass` 等内部字段）。

### 5.5 声明式最小示例

```html
<cmx-revo-grid
  data-cmx-model-id="orderColumns"
  data-cmx-fill-height
  data-cmx-options='{"selectionMode":"multi","showTotals":true,"editable":true}'
></cmx-revo-grid>
```

### 5.6 树表（tabulator）

```html
<cmx-tabulator
  data-cmx-tree
  data-cmx-parent-field="parentId"
  data-cmx-tree-column="name"
  data-cmx-tree-start-expanded="1"
  data-cmx-icon-field="icon"
></cmx-tabulator>
```
