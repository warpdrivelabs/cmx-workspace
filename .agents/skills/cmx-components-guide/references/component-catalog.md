# cmx-data-comp 组件选型清单（双技能共享参考）

> ⚠️ **本文件是 `html-page-generator` 与 `native-page-generator` 的共享参考**。两处内容必须保持一致，改动需同步另一份。
> 何时读：**生成任何页面前必读**——先查这里有没有现成组件，避免重复造轮子。
> 源码：`packages/cmx-data-comp/src/components/`

> 🔧 **组件详细用法**（配置项 / 完整事件 / slot / 方法签名 / 使用配方）见 **`cmx-components-guide`** 技能。本清单只负责"选哪个组件"，不重复记录组件内部细节。

---

## 核心原则：优先复用，不满足才自研

**生成页面前，先按下表查 cmx-data-comp 是否已有满足需求的组件。尽可能使用已有组件，不要自行造轮子。** 只有当组件库确实不满足时才自行开发，且**自研前必须与用户沟通确认**（说明缺什么、为何现有组件不行、自研方案）。

> ⚠️ **Neo 主题只对 cmx-data-comp 组件生效**——皮肤 CSS 通过 `applyNeoSkin()` 注入到组件 ShadowRoot 内的 `:host(.cmx-<name>-neo)`，**原生 HTML 元素（`<table>` / `<ul>` / `<div>` + 手写样式）不会自动套 Neo**。因此：
> - 业务表格 → **必须 `<cmx-revo-grid>`**（`<table>` 仅限 `.cmx-kv-table` 键值展示卡 / 弹层小型明细例外，见 page-style-guide.md 第三节、SKILL.md 附录）
> - 业务表单 → **必须 `<cmx-ui5-form>` + CmxColumnModel**（不要堆 `<input>`）
> - 对话框 → **必须 `<cmx-floating-dialog>` / `<ui5-dialog>`**（不要 div 手搓模态）
> - 分页 → **必须 `<cmx-pager>`**（不要堆 button）
> - 树形 → **必须 `<cmx-web-treeview>` / `<cmx-tabulator data-cmx-tree>`**（不要 `<ul>` 嵌套）
>
> 用 Neo 主题 = 用 cmx 组件，二者绑定。原生元素既无 Neo 风格，也无法响应 `data-cmx-skin` / `data-cmx-skin-tone` 切换。

选型优先级（呼应 AGENTS.md 前端规范）：
1. **cmx-data-comp 组件**（`cmx-*` / `cmx-ignite-*`）—— 优先（**默认即 Neo 皮肤**）
2. **cmx lib 助手**（`globalThis.__cmxDataComp` 的 `cmxInfo/cmxWarn/cmxError`、`ChangeSetCollector` 等）—— 次选
3. **UI5 Web Components**（`ui5-button` / `ui5-bar` / `ui5-select` 等）—— 兜底
4. **div 白名单**（`.biz-bar` / `.lvlbox` / `.neo-panel` / `.cmx-kv-table`，见 page-style-guide.md）—— 仅布局骨架
5. **自行开发** —— **最后手段，须与用户确认**

---

## 一、表格 / 网格类

| 组件 | tag | 用途 | 关键 API |
| --- | --- | --- | --- |
| **cmx-revo-grid** | `<cmx-revo-grid>` | **主表格**——基于 RevoGrid，支持虚拟滚动/编辑/聚合/主从协调。业务表格首选 | `setColumnModel(cm)` / `setDataSet(ds)` / `setOptions({selectionMode,fillHeight,...})` |
| cmx-tabulator | `<cmx-tabulator>` | 备选表格——基于 Tabulator，适合需要树表/复杂分组但 revo-grid 不满足时 | `setColumnModel` / `setDataSet` |
| cmx-ignite-grid | `<cmx-ignite-grid>` | Ignite 数据网格——需要 Ignite 风格的高级网格功能时 | 同上 |

> **默认用 cmx-revo-grid**。只有 revo-grid 明确不满足（如特殊树表/列分组需求）才换 tabulator/ignite-grid，且与用户确认。

### cmx-revo-grid 常用配置

```html
<cmx-revo-grid
  data-cmx-master-slave-id="ms"        <!-- 主从模式 -->
  data-cmx-dataset-id="head.items"      <!-- schema 路径 -->
  data-cmx-kind="list"
  data-cmx-model-id="itemModel"
  style="height:200px;">
</cmx-revo-grid>
```

```js
grid.setOptions({
  selectionMode: 'single',   // 'none'|'single'|'multi'
  fillHeight: true,           // 填满容器
  showRowIndex: true,         // 序号列
  editable: true              // 可编辑
})
```

**事件**：`cmx-row-selected` / `cmx-row-selection-change` / `cmx-cell-changed` / `cmx-row-added` / `cmx-row-removed`

### 操作列（按钮组）—— `display.mode='actions'`

需要"编辑/删除/审批"这类一列多按钮的行级操作时，用 CmxColumn 的 `display.mode='actions'` + `display.actions[]`，**不要手写 cellTemplate**（`cmx-column-adapter.js` 已自动渲染按钮组 + 圆角边框）：

```jsonc
{
  "id": "_actions", "caption": "操作", "dataType": "VARCHAR", "width": "180px",
  "display": { "mode": "actions", "actions": [
    { "text": "编辑",  "actionRef": "edit",    "icon": "edit" },
    { "text": "审批",  "actionRef": "approve", "variant": "emphasized" },
    { "text": "删除",  "actionRef": "delete",  "variant": "negative" }
  ]}
}
```

监听 `cmx-cell-link-click` 事件路由业务：

```js
grid.addEventListener('cmx-cell-link-click', (e) => {
  const { key, rowId, actionRef } = e.detail   // actionRef 来自按钮的 data-cmx-action
  if (actionRef === 'edit')   openEdit(rowId)
  if (actionRef === 'delete') confirmDelete(rowId)
})
```

> 详细字段表（text/actionRef/icon/variant/color/visible）见 `field-edit-display-modes.md` 第三节「display.actions[] 单按钮字段」。`link` 模式（单按钮链接列）共用本事件，用 `display.link.actionRef`。

#### 按行状态显隐按钮（`visible(model)`，仅程序化 CmxColumn）

同一列按行状态显示不同按钮组（如待办列表：草稿行显"提交/作废"、审批中行显"通过/驳回"），用 `display.actions[].visible(model)`。**这是声明式 jsonc 做不到的**（函数值无法序列化），只能程序化构造：

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

#### 何时该用 cellTemplate（极端自定义渲染）

`display.mode='actions'` 覆盖了绝大多数"一列多按钮"场景——**优先用它**。仅当按钮之外的渲染需求出现时（单元格内嵌进度条、图标+多行文本、行内 mini 图表等非按钮内容），才在 CmxColumn 上直接挂 `cellTemplate`：

```js
new C.CmxColumn({ id: 'progress', caption: '进度', dataType: 'INT', width: '160px',
  // h 是 revo-grid 的 hyperscript；props.model 是行数据，props.prop 是列 id
  cellTemplate: (h, props) => {
    const v = Number(props.model?.progress ?? 0)
    return h('div', { style: { display: 'flex', alignItems: 'center', gap: '8px', height: '100%' } }, [
      h('div', { style: { flex: '1', height: '6px', background: '#e5e5e5', borderRadius: '3px' } }, [
        h('div', { style: { width: `${v}%`, height: '100%', background: 'var(--sapInformativeElementColor,#0070f2)', borderRadius: '3px' } })
      ]),
      h('span', { style: { fontSize: '0.75rem' } }, `${v}%`)
    ])
  }
})
```

> **`cellTemplate` / `cellProperties` 已支持经 `new CmxColumn({...})` 直接传入**（`CmxColumn.toDescriptor()` 会透传，`_leafDescriptorToRevoCol` 优先采用调用方挂的函数，高于 format/badge/icon/link/number/actions 等内置推断）。但操作类需求仍应首选 `display.mode='actions'`，只有非按钮的自定义单元格才落到 cellTemplate。

---

## 二、表单类

| 组件 | tag | 用途 |
| --- | --- | --- |
| **cmx-ui5-form** | `<cmx-ui5-form>` | **主表单**——基于 UI5，字段由 CmxColumnModel 驱动，支持各类编辑器、计算公式、校验。业务表单首选 |
| cmx-master-slave-config | `<cmx-master-slave-config>` | 主从协调器配置面板（设计期用，运行时少用） |

### cmx-ui5-form 常用配置

```html
<cmx-ui5-form
  data-cmx-master-slave-id="ms"
  data-cmx-dataset-id="head"
  data-cmx-kind="single"
  data-cmx-model-id="headModel"
  data-cmx-density="compact">
</cmx-ui5-form>
```

> 表单字段（文本/数字/日期/下拉/字典选择等）由 `CmxColumnModel` 的 `columns[].edit.mode` 决定，**不需要手写输入框**。

---

## 三、输入控件类（表单字段编辑器，独立使用少）

这些主要作为 form/grid 的字段编辑器，由 `CmxColumnModel.columns[].edit.mode` 触发。独立使用时可选：

| 组件 | tag | 用途 | 对应 edit.mode |
| --- | --- | --- | --- |
| cmx-text-input | `<cmx-text-input>` | 文本输入 | `text` |
| cmx-number-input | `<cmx-number-input>` | 数字输入（带格式化） | `number` |
| cmx-date-input | `<cmx-date-input>` | 日期选择 | `date` |
| cmx-datetime-input | `<cmx-datetime-input>` | 日期时间选择 | `datetime` |
| cmx-dict-select | `<cmx-dict-select>` | **字典选择**——输入框 + MRU + 搜索 + help 弹层（分类树/分组树/grid） | `ref` / `tree-ref` |
| cmx-combo-box | `<cmx-combo-box>` | **下拉/树/网格选择器**——三种弹出模式（list/grid/tree） | `combo` / `select` |

> **需要选字典/主数据时优先用 cmx-dict-select 或 cmx-combo-box**，不要手搓 input + 弹层。

---

## 四、布局 / 容器类

| 组件 | tag | 用途 |
| --- | --- | --- |
| cmx-split-pane | `<cmx-split-pane>` | **可调分栏**——horizontal/vertical，slot="first"/"second"，带 splitter |
| cmx-view-tabs | `<cmx-view-tabs>` | **Tab 切换**——slot="tabs" 放切换按钮（data-view），子元素 data-view-panel |
| cmx-embed-page | `<cmx-embed-page>` | **嵌入展示** workspace.embed 区的 html_pages 视图（多视图带 tab） |
| cmx-pager | `<cmx-pager>` | **分页栏**——双模式（独立自管 / 协作协调器），派发 page-change |

### 布局场景选型

| 需求 | 用什么 |
| --- | --- |
| 左右/上下分栏可拖拽 | `<cmx-split-pane>` |
| 多 tab 切换面板 | `<cmx-view-tabs>` |
| 分页 | `<cmx-pager>`（不要手搓"上一页/下一页"按钮） |
| 嵌入其它 html-page | `<cmx-embed-page>` |
| 树形导航 | `<cmx-web-treeview>`（见下） |

---

## 五、树形类

| 组件 | tag | 用途 |
| --- | --- | --- |
| **cmx-web-treeview** | `<cmx-web-treeview>` | 树形视图——基于 @keenmate/web-treeview，支持 CmxDataSet 直传，parentField 决定层级 |

> 需要树形展示（组织架构、科目层级、目录树）时用 cmx-web-treeview，不要用嵌套 `<ul>` 手搓。

---

## 六、对话框 / 浮层类

| 组件 | tag / 函数 | 用途 |
| --- | --- | --- |
| **cmx-floating-dialog** | `<cmx-floating-dialog>` | **业务对话框**——替代 `ui5-dialog` / 手搓模态，支持标题/工具栏/内容 slot |
| cmxInfo / cmxWarn / cmxError | `cmxInfo(msg)` 等 | **消息提示**——替代 `alert()` / `confirm()` |
| showCmxMessage | `showCmxMessage(opts)` | 通用消息（带选项） |
| presentDocError | `presentDocError(err, opts)` | 单据保存校验失败展示（含冲突处理） |

> **禁用 `alert()` / `confirm()` / `div` 手搓模态**——统一用 cmx-floating-dialog / cmxInfo 等。

> **cmx-floating-dialog 内容区布局契约（setContent 路径）**：内容自动包入 `.dlg-content` 标准容器（默认 padding 14px 16px + flex 伸展链）。生成页面时：① 内容元素**不要再手写 padding / `flex:1 1 auto;min-width:0;box-sizing:border-box` 三件套**（会双重 padding）；② 需要填满或内部滚动的元素只写 `flex:1; min-height:0`；③ grid 铺满用 `setContent(el, { padding:false })`；④ **禁止 `position:absolute; inset:0` 铺内容**。详见 cmx-components-guide `dialog-message.md` 2.2.x。

---

## 七、Ignite 高级组件（特定场景才用）

| 组件 | tag | 用途 | 何时选 |
| --- | --- | --- | --- |
| cmx-ignite-list | `<cmx-ignite-list>` | Ignite 行列表（卡片/列表布局，绑定 CmxDataSet） | 需要卡片式列表（非表格）时 |
| cmx-ignite-combo | `<cmx-ignite-combo>` | Ignite 下拉 | cmx-combo-box 不满足时 |
| cmx-ignite-input | `<cmx-ignite-input>` | Ignite 输入 | cmx-text-input 不满足时 |
| cmx-ignite-grid | `<cmx-ignite-grid>` | Ignite 网格 | cmx-revo-grid 不满足时 |
| cmx-ignite-gauge | `<cmx-ignite-gauge>` | **仪表盘**（radial/linear/bullet） | 需要 KPI 仪表盘时 |
| cmx-spreadsheet | `<cmx-spreadsheet>` | **Excel 式电子表格**——合并格/公式栏/单元格样式 | 报表表样/Excel 编辑场景 |

> Ignite 组件引入额外体积（igniteui-webcomponents），**非必要不用**。用前确认 cmx-* 主组件确实不满足。

---

## 八、cmx lib 助手（非组件，但常用）

经 `globalThis.__cmxDataComp` 取用（native-page）或 importmap（html-page）：

| 助手 | 用途 |
| --- | --- |
| `CmxMasterSlave` / `CmxDataSet` / `CmxColumnModel` | 6 大模型类（html-page 配置化用，native-page 程序化用） |
| `loadDocData` / `saveDocData` | DOC 数据装载/回存助手 |
| `ChangeSetCollector` | 变更收集器（编辑回存用） |
| `buildMasterSlaveSchema` / `buildColumnModel` | 由 doc/meta 动态构造 schema/columns |
| `CmxDictCache` / `makeDictResolver` | 字典缓存/解析 |
| `cmxInfo` / `cmxWarn` / `cmxError` | 消息提示 |
| `presentDocError` | 校验失败展示 |

---

## 九、自研判断流程（重要）

当 tempted to 自行开发组件/手写 UI 时，按此流程：

```
1. 查本清单 —— 有没有现成组件满足？
   ├─ 有 → 用现成的
   └─ 没有 ↓
2. 查 cmx-data-comp/src/components/ 实际文件 —— 清单可能滞后
   ├─ 有 → 用现成的
   └─ 没有 ↓
3. 能用 UI5 Web Components 满足吗？（ui5-button/ui5-select/ui5-dialog 等）
   ├─ 能 → 用 UI5
   └─ 不能 ↓
4. ★ 与用户沟通确认 ★
   - 说明：缺什么组件、为何 cmx-* / UI5 都不行、自研方案
   - 得到确认后再自研
```

### 常见"不必要自研"案例

| 需求 | 错误做法 | 正确做法 |
| --- | --- | --- |
| 表格 | `<table>` 手搓 | `<cmx-revo-grid>` |
| 表单 | `<input>` 堆 | `<cmx-ui5-form>` + CmxColumnModel |
| 下拉选字典 | input + 自写弹层 | `<cmx-dict-select>` |
| 弹窗 | `div` 手搓模态 | `<cmx-floating-dialog>` |
| 提示 | `alert()` | `cmxInfo()` |
| 分页 | "上/下页"按钮堆 | `<cmx-pager>` |
| 分栏 | flex 手搓 | `<cmx-split-pane>` |
| Tab 切换 | div 切换显隐 | `<cmx-view-tabs>` |
| 树形 | `<ul>` 嵌套 | `<cmx-web-treeview>` |

---

## 十、关键文件索引

| 用途 | 路径 |
| --- | --- |
| 组件源码目录 | `packages/cmx-data-comp/src/components/` |
| Ignite 组件 | `packages/cmx-data-comp/src/components/ignite/` |
| 导出契约（完整清单） | `packages/cmx-data-comp/package.json` 的 `exports` |
| barrel 导出 | `packages/cmx-data-comp/src/index.js` |
| cmx-pager 用法 | `packages/cmx-data-comp/src/components/cmx-pager.js`（文件头注释） |
| cmx-dict-select 用法 | `packages/cmx-data-comp/src/components/cmx-dict-select.js`（文件头注释） |
| cmx-combo-box 用法 | `packages/cmx-data-comp/src/components/cmx-combo-box.js`（文件头注释） |
| **组件用法手册**（配置项 / API / 事件 / slot） | **`cmx-components-guide` 技能**（`.agents/skills/cmx-components-guide/`） |
