---
name: cmx-components-guide
description: 指导 cmx-data-comp 组件库的使用：97 个自定义元素（cmx-revo-grid / cmx-ui5-form / cmx-dict-select / cmx-combo-box / cmx-floating-dialog / cmx-split-pane / cmx-ignite-* 等）的配置项、API 方法、事件、slot、使用配方。当用户要求使用 / 配置 / 查询 cmx 组件、问"这个组件怎么用""有哪些参数""回调返回什么""表格怎么绑数据""字典选择怎么配""对话框怎么弹"时必用。生成页面时与 html-page-generator / native-page-generator 配合--本技能管"组件怎么用"，那两个技能管"页面怎么生成"。
---

# cmx-data-comp 组件使用手册

指导你使用 `packages/cmx-data-comp` 组件库的 97 个自定义元素。

> **范围**：本技能专管**组件怎么用**（配置项 / API / 事件 / 配方）。若需**生成整个页面**，用 `html-page-generator`（设计器页）或 `native-page-generator`（原生页）--它们会引用本技能的 references 做组件选型。

> 采用**渐进式披露**：本文件是决策入口，按需求读 1-2 个 reference，不要全读。

---

## 一、组件分类速查（97 tag = 35 个显式 define + 63 个 ignite thin 规格映射，重叠 1 个 cmx-ignite-input）

| 分类 | 组件 | 何时用 | 详细文档 |
|------|------|--------|----------|
| **表格** | `cmx-revo-grid`（首选）/ `cmx-tabulator`（树表备选）/ `cmx-ignite-grid` | 数据表格 | `references/grid-components.md` |
| **表单** | `cmx-ui5-form` / `cmx-master-slave-config` | 单行编辑表单 / 声明式主从 | `references/form-components.md` |
| **字典选择** | `cmx-dict-select` | 外键选值 + MRU + help 弹层 | `references/dict-select.md` |
| **下拉/树/网格选择** | `cmx-combo-box` | 三种弹出模式 | `references/combo-box.md` |
| **输入编辑器** | `cmx-text-input` / `cmx-number-input` / `cmx-date-input` / `cmx-datetime-input` | form/grid 字段编辑 | `references/input-editors.md` |
| **对话框/消息** | `cmx-floating-dialog` / `showCmxMessage` / `cmxConfirm` | 模态对话框 / 信息弹窗 / 确认对话框 | `references/dialog-message.md` |
| **展示组件** | `cmx-panel` / `cmx-toolbar` / `cmx-status-tag` / `cmx-empty-state` / `cmx-desc-list`(+`cmx-desc-item`) / `cmx-filter-bar` / `cmx-kpi-card` / `cmx-flow-trail` | 面板/命令栏/状态标签/空状态/键值清单/筛选条/统计卡/流程轨迹 | `references/display-components.md` |
| **布局容器** | `cmx-split-pane` / `cmx-view-tabs` / `cmx-embed-page` / `cmx-pager` | 分栏 / 标签 / 嵌入 / 分页 | `references/layout-containers.md` |
| **树** | `cmx-web-treeview` | 树形导航 | `references/treeview.md` |
| **IgniteUI** | `cmx-ignite-*`（63 薄 + 5 厚） | UI5/cmx 不满足时 | `references/ignite-thin.md` |

---

## 二、选型决策树

```
需求 -> 用哪个组件？

数据表格（虚拟滚动/编辑/聚合）
  -> cmx-revo-grid（首选）
  -> 树表/复杂分组不满足？ -> cmx-tabulator
  -> 需要 Ignite 风格？ -> cmx-ignite-grid

单行表单（字段编辑 + 校验）
  -> cmx-ui5-form

选字典/主数据（输入 + 搜索 + help 弹层）
  -> cmx-dict-select
  -> 需要下拉/树/网格三种弹出？ -> cmx-combo-box

对话框（模态 / 表单 / 左右分栏）
  -> cmx-floating-dialog

信息提示（info/warning/error）
  -> showCmxMessage / cmxWarn / cmxError / cmxInfo

确认对话框（确定/取消二选一）
  -> cmxConfirm（返回 Promise<boolean>，danger 删除/作废用红色按钮）

可折叠面板/卡片外壳（标题栏 + 内容区）
  -> cmx-panel

命令栏/工具条（增删改查按钮排成一排）
  -> cmx-toolbar（slot 透传，内部放 ui5-button）

状态徽章/标签（启用/禁用/待审核带色块）
  -> cmx-status-tag

空状态占位（暂无数据：图标 + 标题 + 副标题）
  -> cmx-empty-state

键值清单/详情描述列表（label:value 只读）
  -> cmx-desc-list（+ cmx-desc-item 子元素）

统计卡/KPI 指标卡（标签 + 大数字 + 趋势）
  -> cmx-kpi-card

流程审批轨迹（事件流：发起/审批意见/当前等待节点）
  -> cmx-flow-trail（el.trail = {instance, definition, comments} 绑数据，纯呈现不取数）

搜索/筛选条件区（input + 搜索/清空按钮）
  -> cmx-filter-bar

布局（左右/上下分栏）
  -> cmx-split-pane

标签页切换
  -> cmx-view-tabs

树形导航
  -> cmx-web-treeview

分页
  -> cmx-pager

UI5 和 cmx 都没有的控件
  -> 查 references/ignite-thin.md（63 个 IgniteUI 薄封装）
  -> 还没有？ -> div 白名单（见 `references/frontend-conventions.md` 第六节）
```

---

## 三、使用前必读

**生成任何组件代码前，先读 `references/common-mistakes.md`**--避免高频陷阱（ID 随机值、alert 滥用、escHtml 内联、EDIT_MODES 硬编码）。

涉及**跨组件复用红线 / div 自建白名单 / apiFetch 后端通信 / UI5 装载规范 / ESLint 强制项 / 展示组件迁移受阻**时，读 `references/frontend-conventions.md`（整合自原 FRONTEND_CONVENTIONS.md）。

> **组件注册机制**：`cmx-data-comp` 的 barrel（`src/index.js`）在 import 时自动注册大部分自定义元素（副作用 import）。**例外**：`<cmx-spreadsheet>` 和 `<cmx-spreadjs-sheet>`（电子表格内核，仅报表页用）是**懒注册**——首次在 DOM 出现对应标签时才动态 import 加载，不进首屏 bundle（省 6.4MB）。如需主动预加载，调用 barrel 导出的 `preloadSheetComponents()`。直接引用类用子路径：`import { CmxSpreadsheet } from 'cmx-data-comp/components/ignite/cmx-spreadsheet.js'`。

---

## 四、数据源与字典适配器

需要远程数据源（搜索 / 按 key 加载）时，读 `references/data-source-patterns.md`--复用 `createDictDataSource` 工厂或 makeDictSource 标准骨架，不要每页手写。

---

## 五、references 索引

| 文件 | 何时读 | 核心内容 |
|------|--------|----------|
| `references/common-mistakes.md` | **每次必读** | 高频陷阱清单 |
| `references/frontend-conventions.md` | 涉及复用红线/div 白名单/apiFetch/UI5 装载/ESLint 时 | 前端复用规范（整合自原 FRONTEND_CONVENTIONS.md） |
| `references/grid-components.md` | 用表格时 | cmx-revo-grid/tabulator/ignite-grid 配置手册 |
| `references/form-components.md` | 用表单时 | cmx-ui5-form/master-slave-config |
| `references/dict-select.md` | 用字典选择时 | cmx-dict-select 17 配置项 + 事件 detail |
| `references/combo-box.md` | 用下拉选择时 | cmx-combo-box 三模式 |
| `references/input-editors.md` | 用输入控件时 | text/number/date/datetime-input |
| `references/dialog-message.md` | 用对话框/消息时 | floating-dialog + showCmxMessage + cmxConfirm |
| `references/display-components.md` | 用展示组件时 | panel/toolbar/status-tag/empty-state/desc-list/filter-bar |
| `references/layout-containers.md` | 用布局容器时 | split-pane/view-tabs/embed-page/pager |
| `references/treeview.md` | 用树时 | cmx-web-treeview |
| `references/ignite-thin.md` | 用 IgniteUI 时 | 63 薄封装 + 5 厚封装速查 |
| `references/data-source-patterns.md` | 需远程数据源时 | createDictDataSource + makeDictSource 骨架 |
| `references/page-helpers.md` | **写/改原生页面（native-pages）时** | 原生页面共享微工具：escHtml/escAttr/apiJson/apiGet/apiPost（经 `globalThis.__cmxDataComp` 取用）+ toast 规范（**共享真源**，native-page-generator 引用） |
| `references/neo-theme-onboarding.md` | 新增展示类组件需要接 Neo 主题时 | 4 层叠加模型 / 皮肤文件结构 / A·B 两种写法 / 6 个 TDD 推进组件 / 双维度切换机制 |
| `references/component-catalog.md` | **页面生成技能做组件选型时** | cmx-data-comp 组件选型清单（表格/表单/输入/布局/树/对话框/ignite）+ 自研判断流程（**共享真源**，html/native-page-generator 引用） |
| `references/field-edit-display-modes.md` | **定义字段 edit/display 属性时** | edit.mode 16 规范值 + mode 专属属性 + display.mode 值域 + 三元字段全集 + 三端差异（**共享真源**，html/native-page-generator、meta-enricher 引用） |
| `references/page-style-guide.md` | **生成 HTML 布局时** | 统一根 div 骨架 / var(--sap*) 颜色 / .biz-bar .lvlbox 约定 class / Neo 皮肤（**共享真源**，html/native-page-generator 引用） |

**读取原则**：先读本文件决策树定组件 -> 必读 common-mistakes.md -> 按组件读 1 个 reference -> 需要数据源再读 data-source-patterns.md。**不要全读。**

---

## 六、相关技能

- **`html-page-generator`** -- 生成设计器业务页面（走 `__designer_meta__` / 6 大模型）。
- **`native-page-generator`** -- 生成原生代码页面（JS 模块 / HTML 片段）。
- **`meta-enricher`** -- 元数据字段属性补全（edit.mode / display.mode 值域）。

> 用户说"生成页面"-> html-page-generator / native-page-generator（它们会引用本技能做组件选型）；问"组件怎么用 / 有什么参数"-> 本技能。
