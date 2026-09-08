# cmx-combo-box 下拉选择器

> 何时读：需要下拉列表 / 树选择 / 网格选择器，或 `editMode:'combo'` 字段编辑时读。

> 源码：`packages/cmx-data-comp/src/components/cmx-combo-box.js`

---

## 一、组件概述

`<cmx-combo-box>` 是数据模型驱动的下拉/树/网格选择器，封装 `<ui5-input>` + `<ui5-popover>`，内嵌 `<cmx-revo-grid>`（list/grid 模式）或 `<cmx-web-treeview>`（tree 模式）。

- tag：`<cmx-combo-box>`
- 数据：`CmxDataSet` + `CmxColumnModel`；远端数据通过 `createPageServiceDataSource` 包装。
- 集成入口：
  1. **独立使用**：手工 `setDataSet` / `setColumnModel` + `setMode` + `setValue` / `getValue`
  2. **form / grid 编辑器**：通过 `'combo'` field-type 注册（见 `cmx-builtin-field-types.js`），读 `field.editSettings`

---

## 二、三种弹出模式

| 模式 | setMode 参数 | 内嵌组件 | 说明 |
|------|-------------|----------|------|
| list | `'list'` | `<cmx-revo-grid>` | 隐藏表头、行高 28px、单列显示（cmxLabel 拼接标题列）；标题列 ≥2 时左右对齐 |
| tree | `'tree'` | `<cmx-web-treeview>` | CmxDataSet 直传，`parentField` 决定层级；支持本地过滤 |
| grid | `'grid'` | `<cmx-revo-grid>` | 完整列显示、行高 32px、显示行号；支持分页 |

list 模式的单列拼接逻辑：
- 优先用 `CmxColumnModel.getTitleColIds()` 取标题列 ID。
- 1 个字段：整段显示为 `cmxLabel`。
- ≥2 个字段：第一个左对齐、第二个（及后续）右对齐（典型：code 左、name 右）。

tree 模式的 path 字段来源（优先级）：
1. 行自带 `path` 字段（用户的 transform 已拼好）。
2. 配了 `parentField` -> 按 id + parent 链回溯拼 path（`.` 分隔）。
3. 都没有 -> path = id（平铺成根节点）。

---

## 三、配置方法

### 3.1 核心配置

| 方法 | 签名 | 说明 |
|------|------|------|
| `setDataSet(ds)` | `(ds: CmxDataSet) -> void` | 直接灌一个 CmxDataSet（本地数据/已加载数据） |
| `setColumnModel(model)` | `(model: CmxColumnModel) -> void` | 绑定 CmxColumnModel；监听 `columns-changed` 自动刷新 |
| `setMode(mode)` | `('list'\|'tree'\|'grid') -> void` | 切弹出层形式 |
| `setDataSource(source)` | `(source: object) -> void` | 绑定远端 DataSource（含 search/loadByKeys/keyField/labelField） |
| `setField(field)` | `(field: object) -> void` | 一键绑定 field 配置（form/grid 编辑器路径用） |
| `setHost(host)` | `(host: object) -> void` | 传入页面 host（用于解析 pageService） |

### 3.2 外观与行为配置

| 方法 | 签名 | 默认值 | 说明 |
|------|------|--------|------|
| `setPlaceholder(text)` | `(text: string) -> void` | `''` | 输入框占位文本 |
| `setReadonly(b)` | `(b: boolean) -> void` | `false` | 只读模式 |
| `setSearchable(b)` | `(b: boolean) -> void` | `true` | 是否允许输入搜索 |
| `setDropdownWidth(css)` | `(css: string) -> void` | `'anchor'` | 下拉宽度：`'anchor'` 同输入框宽，或 CSS 字符串 |
| `setItemsHeight(px)` | `(px: number) -> void` | `320` | 下拉最大高度（px） |
| `setClearable(b)` | `(b: boolean) -> void` | `true` | 是否启用清除按钮（有 value 时自动可见） |
| `setExtensionButtons(list)` | `(list) -> void` | `[]` | 扩展按钮列表（下拉按钮右侧，可多个） |
| `setPaginated(b)` | `(b: boolean) -> void` | `false` | 启用分页（仅 grid 模式 + remote source） |
| `setPageSize(n)` | `(n: number) -> void` | `50` | 每页大小 |

`setExtensionButtons` 列表每项：

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `id` | `string` | `ext-{i}` | 业务标识 |
| `icon` | `string` | `'action'` | UI5 icon name |
| `tooltip` | `string` | - | 按钮 title 提示 |
| `design` | `string` | - | 保留参数 |

### 3.3 field.editSettings 配置项（form/grid 编辑器路径）

`setField(field)` 时从 `field.editSettings`（简称 `es`）读取以下配置：

| editSettings 字段 | 对应方法 / 内部状态 | 说明 |
|-------------------|---------------------|------|
| `es.dropdown` | setMode | 弹出模式 `'list'\|'tree'\|'grid'`；缺省时按 `parentField`/`dropdownColumns` 倒推 |
| `es.placeholder` / `field.placeholder` | setPlaceholder | 占位文本 |
| `es.dropdownWidth` | setDropdownWidth | 下拉宽度 |
| `es.dropdownMaxHeight` | setItemsHeight | 下拉最大高度 |
| `es.emptyText` | - | 无匹配数据时的提示文案 |
| `es.parentField` | - | tree 模式父子关系字段 |
| `es.dropdownColumns` | - | grid 模式自定义列模型；缺省复用 `setColumnModel` 传入的 |
| `es.clearable` | setClearable | 清除按钮开关 |
| `es.extensionButtons` | setExtensionButtons | 扩展按钮列表 |
| `es.paginated` | setPaginated | 分页开关 |
| `es.pageSize` | setPageSize | 每页大小 |
| `es.source` / `field.source` | setDataSource | 远端数据源配置 `{ service, keyField, labelField, queryParam, responsePath \| transform }` |
| `es.options` | - | 静态选项数组（无需远端）；每项 `{ value, label }` |

---

## 四、值操作 API

| 方法 | 签名 | 说明 |
|------|------|------|
| `setValue(id, opts)` | `(id: string\|null, opts?: {silent?, source?}) -> void` | 按 row.id 选中；找不到时调 `lookupByKey` 异步回填 |
| `getValue()` | `() -> string \| null` | 当前选中 row.id |
| `getSelectedRow()` | `() -> CmxRowSet \| null` | 当前选中行（从 knownRows / innerDs / externalDs 查找） |
| `open()` | `() -> void` | 打开下拉 |
| `close(committed)` | `(committed?: boolean) -> void` | 关闭下拉；`committed=true` 表示用户已选择 |
| `toggle()` | `() -> void` | 切换开关 |
| `isOpen()` | `() -> boolean` | 是否展开 |
| `focus()` | `() -> void` | 聚焦输入框 |

`setValue` 的 `opts`：

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `silent` | `boolean` | `false` | `true` 时不派发 `cmx-combo-value-change` |
| `source` | `string` | `'api'` | 值变更来源标记：`'click'\|'keyboard'\|'api'\|'clear'` |

---

## 五、事件

所有事件 `bubbles: true, composed: true`。

| 事件名 | detail | 触发时机 |
|--------|--------|----------|
| `cmx-combo-value-change` | `{ id, row, source }` | 选中值变化；source: `'click'\|'keyboard'\|'api'\|'clear'` |
| `cmx-combo-open` | `{ mode }` | 下拉打开 |
| `cmx-combo-close` | `{ committed: boolean }` | 下拉关闭；`committed=true` 表示用户已选择 |
| `cmx-combo-search` | `{ text }` | 用户输入搜索文本 |
| `cmx-combo-search-error` | `{ error }` | 远端搜索出错 |
| `cmx-combo-clear` | `{}` | 用户点清除按钮 |
| `cmx-combo-ext-click` | `{ id, value, row }` | 用户点扩展按钮 |

---

## 六、声明式属性

可通过 HTML 属性初始化（不调 setField 时）：

| 属性 | 说明 |
|------|------|
| `data-cmx-mode` | 弹出模式 `'list'\|'tree'\|'grid'` |
| `data-cmx-placeholder` | 占位文本 |
| `data-cmx-readonly` | `'true'` 时只读 |
| `data-cmx-searchable` | `'false'` 时禁用搜索 |
| `data-cmx-value` | 初始选中 id |
| `data-cmx-clearable` | `'false'` 时隐藏清除按钮 |
| `data-cmx-extension-buttons` | JSON 数组，扩展按钮列表 |
| `data-cmx-paginated` | `'true'` 时启用分页 |
| `data-cmx-page-size` | 每页大小 |
| `data-cmx-options` | JSON 对象，含 `dropdownWidth` / `dropdownMaxHeight` / `emptyText` |
| `data-cmx-rows` | JSON 数组，静态行数据 |

---

## 七、与 cmx-dict-select 选型对比

| 维度 | cmx-combo-box | cmx-dict-select |
|------|---------------|-----------------|
| **弹出模式** | list / tree / grid 三种可选 | 固定 list 下拉 + help 弹层 |
| **MRU** | 无 | 有（最近选过，localStorage + 后端个性化存储） |
| **help 弹层** | 无 | 有（`<cmx-floating-dialog>`，三种布局：classify / group / grid） |
| **数据源** | `CmxDataSet` + `CmxColumnModel` 或 `createPageServiceDataSource` | `dataSource: { search, loadByKeys }` + `classifyTreeSource` / `groupTreeSource` |
| **字典元数据** | 无（通用选择器） | 有（`dictCode` / `idCol` / `labelCol` / `parentCol` / `hierarchical`） |
| **分页** | 有（grid 模式 + remote source） | 无 |
| **扩展按钮** | 有（`setExtensionButtons`，可多个） | 有（slot="actions"） |
| **配置入口** | `setField(field)` 或逐个 set | `configure(cfg)` 一次性 |
| **适用场景** | 通用下拉/树/网格选择；form/grid 字段编辑器 | 字典/主数据选值；需 MRU + help 弹层的业务场景 |

**选型建议**：
- 选字典/主数据 + 需要 MRU + help 弹层 -> `cmx-dict-select`
- 需要三种弹出模式 / 分页 / 通用选择器 / form-grid 编辑器 -> `cmx-combo-box`

---

## 八、代码示例

### 8.1 独立使用 - 本地数据 + list 模式

```javascript
import 'cmx-data-comp/components/cmx-combo-box.js'
import { CmxDataSet, CmxColumnModel, CmxColumn } from 'cmx-data-comp'

const combo = document.createElement('cmx-combo-box')

// 准备数据
const ds = new CmxDataSet({ datasetId: 'depts' })
ds.addRow({ id: '1', code: 'RD', name: '研发部' })
ds.addRow({ id: '2', code: 'HR', name: '人力资源部' })
ds.addRow({ id: '3', code: 'FIN', name: '财务部' })

// 准备列模型
const cm = new CmxColumnModel({
  members: [
    new CmxColumn({ id: 'code', caption: '编码', type: 'text' }),
    new CmxColumn({ id: 'name', caption: '名称', type: 'text' }),
  ],
})

combo.setDataSet(ds)
combo.setColumnModel(cm)
combo.setMode('list')
combo.setPlaceholder('请选择部门')

document.body.appendChild(combo)

combo.addEventListener('cmx-combo-value-change', (e) => {
  console.log('选中:', e.detail.id, e.detail.row)
})
```

### 8.2 独立使用 - tree 模式

```javascript
const combo = document.createElement('cmx-combo-box')

const ds = new CmxDataSet({ datasetId: 'org-tree' })
ds.addRow({ id: '1', name: '总公司', parentId: '' })
ds.addRow({ id: '2', name: '研发中心', parentId: '1' })
ds.addRow({ id: '3', name: '前端组', parentId: '2' })

const cm = new CmxColumnModel({
  members: [new CmxColumn({ id: 'name', caption: '名称', type: 'text' })],
})

combo.setDataSet(ds)
combo.setColumnModel(cm)
combo.setMode('tree')
// parentField 通过 setField 或 editSettings 传入：
combo.setField({ editSettings: { parentField: 'parentId' } })
```

### 8.3 远端搜索 + grid 模式 + 分页

```javascript
import { createPageServiceDataSource } from 'cmx-data-comp/lib/cmx-page-service-source.js'

const combo = document.createElement('cmx-combo-box')
combo.setMode('grid')
combo.setPaginated(true)
combo.setPageSize(50)

const cm = new CmxColumnModel({
  members: [
    new CmxColumn({ id: 'code', caption: '物料编码', type: 'text' }),
    new CmxColumn({ id: 'name', caption: '物料名称', type: 'text' }),
    new CmxColumn({ id: 'spec', caption: '规格', type: 'text' }),
  ],
})
combo.setColumnModel(cm)

// 绑定远端数据源（pageService 已挂到 host 上）
const source = createPageServiceDataSource(host, {
  service: 'searchMaterial',
  keyField: 'id',
  labelField: 'name',
  queryParam: 'keyword',
  responsePath: 'data.items',
})
combo.setDataSource(source)
combo.setHost(host)
```

### 8.4 form / grid 编辑器集成

```javascript
// CmxColumnModel 列定义中设置 editMode
const col = new CmxColumn({
  id: 'deptId',
  caption: '部门',
  type: 'text',
  editMode: 'combo',
  editSettings: {
    dropdown: 'list',
    placeholder: '请选择部门',
    source: {
      service: 'searchDept',
      keyField: 'id',
      labelField: 'name',
      queryParam: 'keyword',
      responsePath: 'data',
    },
    // 或用静态选项：
    // options: [
    //   { value: '1', label: '研发部' },
    //   { value: '2', label: '人力资源部' },
    // ],
  },
})
```

### 8.5 扩展按钮

```javascript
combo.setExtensionButtons([
  { id: 'view-detail', icon: 'detail-view', tooltip: '查看详情' },
  { id: 'add-new', icon: 'add', tooltip: '新增' },
])

combo.addEventListener('cmx-combo-ext-click', (e) => {
  const { id, value, row } = e.detail
  if (id === 'view-detail') openDetail(row)
  else if (id === 'add-new') openNewForm()
})
```
