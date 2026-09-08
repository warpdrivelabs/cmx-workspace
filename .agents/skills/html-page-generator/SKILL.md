---
name: html-page-generator
description: 指导生成 CMX 设计器业务页面（html-pages，配置即页面）——__designer_meta__.models 数组（6 大模型：CmxDataSet / CmxColumnModel / CmxMasterSlave / CmxDCTMeta / CmxDOCMeta / FlexibleCombination）+ HTML 结构 + DOM 绑定 + pageFns / pageServices。当用户要求生成 / 设计 / 创建业务表单页、主从联动页、凭证录入页、弹性组合动态列页、字典单据定义页，或提到 CmxMasterSlave、弹性组合、主从协调、__designer_meta__、models 数组、CmxColumnModel、html-pages、设计器页面时必用。覆盖从纯表格到主从 + 弹性组合的全复杂度场景。与 native-page-generator（原生代码页）成对存在——页面需走设计器 / 用 6 大模型 / 配置化时用本技能。
---

# html-page-generator（设计器业务页面生成器）

指导你为 CMX 低代码平台**生成设计器业务页面**（html-pages）：产出可直接落库的 `__designer_meta__`（含 `models` 数组）+ HTML 结构 + DOM 绑定 + pageFns/pageServices。

> **范围**：本技能专管"配置即页面"——走 `__designer_meta__.models` + 6 大数据模型的设计器页面。若要生成**纯代码页面**（不走设计器、不用 `__designer_meta__`），用 `native-page-generator` 技能。

> 采用**渐进式披露**：本文件是决策入口，按场景复杂度按需读取 `references/` 下对应文件，不要一次性全读。

---

## 一、核心心智模型（生成前必须建立）

### 1. 设计期 vs 运行期（二元论）

| 维度 | 设计期（你产出的东西） | 运行期（用户打开页面时） |
| --- | --- | --- |
| 形态 | 纯 JSON 配置（`__designer_meta__.models`） | `initPageModels()` 按 `modelType` 实例化真实对象 |
| 位置 | 嵌在 HTML 的 `<script id="__designer_meta__">` | 实例挂到 `host.<instanceId>` |
| 你写的 props | 字段值（如 `schema: [...]`） | 变成构造函数参数 |

**关键源码链路**：你写的 `models[i].props` → 运行时 `initPageModels`（`packages/cmx-data-comp/src/lib/init-page-models.js`）按 `modelType` 分支 `new` 出实例 → 挂到 `host[instanceId]` → 可视组件通过 DOM 属性找到模型绑定。

### 2. 6 大模型速查

| 图标 | 模型（modelType） | 一句话职责 | 绑定可视组件 |
| --- | --- | --- | --- |
| 🗂 | `CmxDataSet` | 多级树形数据行容器 | grid/form/treeview |
| 📋 | `CmxColumnModel` | 表格/表单的列配方（columns + columnGroups） | grid/form |
| ⚡ | `CmxMasterSlave` | 主从协调器：多表级联 + 自动聚合 | 按 path 绑 form/grid |
| ▣ | `CmxDCTMeta` | 加载数据字典元数据（dictionaryTables） | 不直接绑（提供列定义） |
| ▤ | `CmxDOCMeta` | 加载业务单据元数据（voucherTables） | 不直接绑（提供列定义） |
| 🧭 | `FlexibleCombination` | 上下文驱动的动态列（别名 ContextProfile） | 改写目标 CmxColumnModel |

**6 大模型全部 `modelOnly: true`——不可视，只放 Models 面板，不能拖到画布。** 可视组件（`<cmx-revo-grid>` / `<cmx-form>` 等）是独立的 Web Components，通过 DOM 属性与模型绑定。

---

## 二、复杂度决策树（核心——先定该用哪些模型）

生成前，先判断业务页属于哪一级。**只选需要的模型**，不要过度设计。

```
L0 纯展示 / 录入单张表
   用：CmxDataSet + CmxColumnModel
   读：references/model-dataset.md + references/model-column-model.md

L1 主从联动 + 自动聚合（凭证头/分录、订单/明细）
   在 L0 基础上 + CmxMasterSlave
   读：+ references/model-master-slave.md（必读）+ references/page-assembly.md

L2 上下文驱动的动态列（选科目后列变化）
   在 L1 基础上 + FlexibleCombination
   读：+ references/model-flexible-combination.md（必读）

L3 需要加载后端字典 / 单据定义
   按需 + CmxDCTMeta / CmxDOCMeta
   读：+ references/model-dct-doc-meta.md
```

**判断要点**：
- 只有"一张表的数据要装进 grid" → L0
- 出现"主表选行 → 子表刷新"或"子表金额改了 → 主表自动汇总" → L1
- 出现"选了某维度值（如科目、交易类型），列要变" → L2
- 需要从后端 `/api/definitions/config` 加载字典/单据结构 → L3

---

## 三、统一生成工作流（6 步，固定顺序）

### Step 0：组件选型（前置，必做）

**生成任何 UI 前，先读 `../cmx-components-guide/references/component-catalog.md`**——选型优先级（cmx-data-comp 组件 → cmx lib 助手 → UI5 → div 白名单 → 自研须与用户确认）、常见误自研清单、自研判断流程**全部以该共享真源为准**，不在此复述。

### Step 0·5：换肤与 Neo 主题（硬性要求，新增页面默认遵循）

**所有新建页面必须支持换肤，并默认采用 Neo 主题**——用 Neo 就用 cmx 组件（原生 `<table>`/`<input>` 不会自动套 Neo），骨架层一律 `var(--sap*)`/`var(--neo-*)` 派生禁止硬编码。换肤机制全貌（`data-cmx-skin` 三级优先级 / `data-cmx-skin-tone` / `data-cmx-style-id` / 多主题共存 / `cmx-skin-changed` 事件监听）见共享真源 `../cmx-components-guide/references/page-style-guide.md` 第二、五、六节，本技能不重复维护。

### Step 0·6：时间显示转当前时区（硬性要求）

后端时间一律 UTC ISO（如 `2026-09-03T16:43:38.238813+00:00`），**显示前必须转浏览器当前时区，禁止 `slice`/`replace('T')`/`substr` 截取**（截出来是 UTC，差一个时区偏移，评审一票否决）：

- **表格/表单时间列**：列 `dataType` 置 `DATETIME`/`DATE` + display format token（`YYYY-MM-DD HH:mm:ss`），组件库（cmx-column-adapter）内部转当前时区，配置即正确；
- **pageFns 里手工拼时间串**：用 `globalThis.cmx.datetime`（`fmtDateTime`/`fmtDate`/`fmtMinute`/…），4 行标准接入片段与函数清单见共享真源 `../cmx-components-guide/references/frontend-conventions.md` §二.6。

### Step 1：厘清业务结构

向用户确认或在需求中识别：
- 有哪几张表？字段分别是什么？
- 表与表的**父子关系**？（主表→子表→孙表）
- 哪些字段需要**联动汇总**？（如分录金额汇总到表头）
- 是否有**锚点维度**驱动列变化？（如选了"应收账款"科目，列变成"客户/部门/金额"）
- 数据从哪来？（pageService / 初始静态 / 后端定义文件）

### Step 2：选模型组合 + 定 instanceId

按决策树选定要用哪些模型，并给每个实例起名。**约定俗成的 instanceId**（来自源码默认前缀）：

| 模型 | 约定 instanceId | 说明 |
| --- | --- | --- |
| CmxMasterSlave | `ms` / `voucherMS` | 协调器，通常一个页面一个 |
| CmxDataSet | `xxxDs`（如 `itemsDs`） | 多个数据集加序号 |
| CmxColumnModel | `xxxModel` / `colXxx`（如 `itemModel`、`colHeader`） | 每个绑定的 grid 一个 |
| FlexibleCombination | `xxxFC` / `detailFlexibleCombination` | 锚定目标列模型 |
| CmxDCTMeta | `xxxDct` / `glDctMeta` | |
| CmxDOCMeta | `xxxDocMeta` | |

### Step 3：读对应 reference

按决策树读取 `references/` 下文件。**只读用到的模型对应的文件**，不要全读。

### Step 4：生成 models 数组

每个模型实例结构：

```jsonc
{
  "modelType": "CmxMasterSlave",   // 6 大模型字符串之一
  "instanceId": "ms",              // 运行时 host.<instanceId>
  "props":   { /* 模型字段，见各 reference */ },
  "events":  { /* 可选：事件名 -> 脚本函数体字符串 */ }
}
```

### Step 5：生成 HTML + DOM 绑定 + pageFns + pageServices

参照 **references/page-assembly.md**（L1 及以上必读）。关键：可视组件的 DOM 属性要和模型 instanceId / schema path 对上。

**同时必读 ../cmx-components-guide/references/page-style-guide.md**——套用统一根 div 骨架、`var(--sap*)` 颜色、`.biz-bar`/`.lvlbox` 约定 class，保证跨页面风格一致。**L3（调字典/单据数据接口）额外读 references/dct-doc-api.md**——含 DCT/DOC 数据接口参数 + 真实页面案例（`voucher-doc.html` 四层凭证 / `doc-loader.js` 元数据驱动）。

---

## 四、页面组装骨架（每次生成都要用的核心知识）

### 1. `__designer_meta__` 顶层结构

整个元数据是嵌在 HTML 里的一个 JSON 块：

```html
<script type="application/json" id="__designer_meta__">
{
  "pageData":       [],          // 页面变量（$data.xxx）
  "pageFns":        [],          // 页面函数（见 references/page-assembly.md）
  "pageServices":   [],          // 页面服务调用（REST 等）
  "pageDeps":       [],          // import 声明
  "pageInterfaces": [],          // initPage / onActivate / isDirty / getState / validate
  "dataSources":    [],          // 数据源
  "dataFlow":       {            // 兼容旧配置：schema/aggregations/relations
    "schema": [], "aggregations": [], "relations": []
  },
  "models": [
    /* ← 你生成的 6 大模型实例数组，在这里 → */
  ]
}
</script>
```

> `dataFlow` 是旧位置；新代码里 CmxMasterSlave 的 schema/aggregations 写在 `models[i].props`。但 `relations`（平铺数据主外键）仍写在 `dataFlow.relations`，由 `initPageModels` 兜底读取。见 references/model-master-slave.md。

### 2. models 数组单元结构

```jsonc
{
  "modelType":  "CmxDataSet",     // 字符串，6 大模型之一
  "instanceId": "itemsDs",        // 运行时 host.<instanceId> 访问
  "props":      { /* 见各 reference 字段表 */ },
  "events":     {                 // 可选；事件名 -> 函数体字符串
    "ds-row-added": "// 函数体，运行时包装为 function(event, host){ with(host){...} }"
  }
}
```

### 3. DOM 绑定属性（真实源码核实，关键陷阱区）

可视组件与模型的桥接**完全靠 DOM 属性**，由 `initPageModels` 扫描绑定。生成 HTML 时务必对齐：

```html
<!-- 主从协调器绑定的 grid（L1+ 最常用） -->
<cmx-revo-grid
  id="itemsGrid"
  data-cmx-master-slave-id="ms"              <!-- CmxMasterSlave 的 instanceId -->
  data-cmx-dataset-id="head.items"           <!-- schema 完整路径（点分隔）-->
  data-cmx-kind="list"                       <!-- list=表格 / single=表单 -->
  data-cmx-model-id="itemModel">             <!-- CmxColumnModel 的 instanceId -->
</cmx-revo-grid>

<!-- 纯 DataSet 绑定（不走主从协调器，L0） -->
<cmx-revo-grid
  id="grid"
  data-cmx-dataset-id="itemsDs"              <!-- CmxDataSet 的 instanceId（无 master-slave-id）-->
  data-cmx-model-id="itemsModel">
</cmx-revo-grid>
```

**绑定逻辑**（来自 `init-page-models.js`，真实执行顺序）：
1. 先扫 `[data-cmx-master-slave-id]`：找到 ms 实例 → 读 `data-cmx-dataset-id` 作为 path → `data-cmx-kind` 决定 `bindForm`(single) 还是 `bindTable`(list)
2. 再扫 `[data-cmx-model-id]`：调可视组件的 `setColumnModel(model)`
3. 最后扫只有 `data-cmx-dataset-id`（无 master-slave-id）的：调 `setDataSet(ds)`（L0 纯数据集模式）

### 4. initPageModels 执行顺序（生成 pageFns 时要心里有数）

```
1. 遍历 models，按 modelType 创建实例挂到 host
2. CmxMasterSlave：schema 来自 props.schema（兜底 dataFlow.schema），relations 来自 dataFlow.relations
3. CmxColumnModel：创建后注册到 schema 中包含该 datasetId 的 MS
4. FlexibleCombination：第二轮回填——绑定目标 CmxColumnModel + 消费 props.inlineData
5. 扫 DOM：按上述三个属性绑定可视组件
6. 装载初始数据（若有 $data.cmxInitialData）
7. 调用 host.initPage()（pageInterface）
```

**含义**：你的 pageFns 里写的 `initPage` 函数会在模型实例化 + DOM 绑定之后执行，所以可以安全地 `host.ms.setFlatData(...)` 或 `host.detailFC.loadByAnchor(...)`。

### 5. 最小完整页面骨架（可直接复制改）

```html
<div style="display:flex;flex-direction:column;height:100%;box-sizing:border-box;padding:10px;gap:10px;">
  <!-- HTML 布局：可视组件带 DOM 绑定属性 -->
  <cmx-revo-grid id="itemsGrid"
    data-cmx-master-slave-id="ms"
    data-cmx-dataset-id="head.items"
    data-cmx-kind="list"
    data-cmx-model-id="itemModel"
    style="height:200px;">
  </cmx-revo-grid>
</div>

<script type="application/json" id="__designer_meta__">
{
  "pageData": [],
  "pageFns": [
    {
      "name": "initData",
      "params": "",
      "body": "var ms = host.ms; ms.setFlatData({ head:[...], items:[...] }, { relations:[...] });"
    }
  ],
  "pageServices": [],
  "pageInterfaces": [
    { "name": "initPage",   "enabled": true, "body": "if (host.initData) host.initData();" },
    { "name": "onActivate", "enabled": true, "body": "if (!host.__loaded && host.initData) host.initData();" }
  ],
  "dataSources": [],
  "dataFlow": {
    "schema": [],
    "aggregations": [],
    "relations": [
      { "parent": "head", "child": "items", "parentKey": "id", "childKey": "headId" }
    ]
  },
  "models": [
    {
      "modelType": "CmxMasterSlave",
      "instanceId": "ms",
      "props": {
        "schema": [
          { "id": "head", "children": [ { "id": "items" } ] }
        ],
        "aggregations": []
      }
    },
    {
      "modelType": "CmxColumnModel",
      "instanceId": "itemModel",
      "props": {
        "datasetId": "items",
        "columns": [
          { "id": "code", "caption": "编码", "dataType": "VARCHAR", "width": "120px" },
          { "id": "name", "caption": "名称", "dataType": "VARCHAR", "width": "180px" }
        ]
      }
    }
  ]
}
</script>
```

> 完整真实样例（凭证四层主从）见 `backend/cmx-container/assets/portal/data/html-pages/sources/fi/cmxfico/gl/erp-voucher-cnpc-ms.html`。

---

## 五、高频陷阱清单（跨模型，生成时自检）

| 陷阱 | 正确做法 | 原因 |
| --- | --- | --- |
| schema path 写成 `items` | 写完整路径 `head.items` | 协调器靠完整 path 定位父级，短名找不到 |
| ColumnModel 的 `datasetId` 写成路径 | 写**单层名**（如 `items`，不是 `head.items`） | ColumnModel 注册到 MS 时按单层 id 匹配 `_schemaById` |
| DOM 的 `data-cmx-dataset-id` 写成单层名 | 写**完整路径**（如 `head.items`） | MS 的 bindTable/Form 接收 path |
| DOC/DCT 的应用字段写成 `app` | 用 **`application`** | CmxDOCMeta/CmxDCTMeta 真实字段名是 `application` |
| FlexibleCombination 的应用字段写成 `application` | 用 **`app`** | FC 真实字段名是 `app` |
| FC 的 `columnModelId` 拼错 | 严格对齐目标 CmxColumnModel 的 instanceId | 目标不存在会静默失败（控制台 warn） |
| 给 CmxColumnModel 写事件 | 不要写 | ColumnModel 不继承 EventTarget，写了也不触发 |
| 监听 FC 事件写进 events Tab | 写进 pageFns，用 `addEventListener` | FC 事件未在设计器事件清单暴露 |
| inlineData 既无 `rule` 又无 `rules` | 至少要有其一 | 引擎 console.warn + 不派发事件，列保持原状 |
| schema 里出现同名 id | 每个 id 唯一 | 重复抛 `duplicate path` |
| aggregations 的 `to` 指向不存在的 path | 只用 schema 里定义过的 path | 抛 `unknown path` |
| 硬编码色值 `#fff` / `#1d2d3e` | `var(--sapBackgroundColor)` / `var(--neo-*)` | 见 ../cmx-components-guide/references/page-style-guide.md |
| 在页头 `<style>` 复制 Neo 皮肤源（CMX_FORM_NEO_SKIN_CSS 全文） | 用 `data-cmx-skin` / `data-cmx-skin-tone` 引用现成皮肤 | 升级必坏、占空间 |
| `data-cmx-style-id` 指向不存在的 `<style id>` | 先在页内放 `<style id>` / `<template id>` | 静默无效 |
| 写 `data-cmx-skin="default"` 关 Neo 但又用 `var(--neo-*)` 配色 | 二选一：要么走 Neo 要么不依赖 `--neo-*` | 半截页面无品牌风格 |
| UI5 dark 主题切换后页面底色不变 | 全程 `var(--sap*)` + `color-mix(... var(--sapList_Background) ...)` | Neo 公式自动适配 |

---

## 六、references 索引（按需读取）

| 文件 | 何时读 | 核心内容 |
| --- | --- | --- |
| `references/model-dataset.md` | L0 起所有需要装数据行的场景 | CmxDataSet 字段 / 3 种数据来源 / 树形子集 / 4 事件 |
| `../cmx-components-guide/references/component-catalog.md` | **生成任何 UI 前必读** | cmx-data-comp 组件选型清单（表格/表单/输入/布局/树/对话框/ignite）+ 自研判断流程 |
| `references/model-column-model.md` | 任何需要表格列/表单字段的场景 | CmxColumn 20+ 字段 / edit/display 枚举 / 字段三态 / 计算列 |
| `../cmx-components-guide/references/field-edit-display-modes.md` | **定义字段 edit/display 属性时必读** | edit.mode 16 规范值 + 每个 mode 专属属性 + display.mode 7 值（含 actions 操作列 + `cmx-cell-link-click` 事件）+ 数值类属性显隐 + 三元字段全集 + 三端差异 |
| `references/model-master-slave.md` | L1+ 主从联动 | schema 路径树 / aggregations 聚合 / relations / setFlatData |
| `references/model-dct-doc-meta.md` | L3 加载字典/单据**定义文件**（结构定义） | DCT vs DOC 模型组件 / BASE 共享字段集 / fieldSets / 4 级加载 |
| `references/model-flexible-combination.md` | L2 上下文动态列 | 锚点 / DAM / 三种来源 / 两形态 / 公式引擎 / FieldSpec |
| `references/page-assembly.md` | L1+ 组装完整页面 | pageFns 写法 / pageServices / pageInterfaces / setFlatData 模式 |
| `references/dct-doc-api.md` | **L3 及任何调字典/单据数据接口的场景** | DCT/DOC 数据接口参数 / doc/save 回存 / 真实页面案例（voucher-doc.html / doc-loader.js） |
| `../cmx-components-guide/references/page-style-guide.md` | **生成 HTML 布局时必读** | 统一根 div 骨架 / var(--sap*) 颜色 / .biz-bar .lvlbox 约定 class / Neo 皮肤 |

**读取原则**：先读 SKILL.md 决策 → **Step 0 必读 ../cmx-components-guide/references/component-catalog.md（组件选型）** → 按决策树读 1-2 个模型 reference → **定义字段时必读 ../cmx-components-guide/references/field-edit-display-modes.md（edit/display 值域）** → 生成 HTML 时**必读 ../cmx-components-guide/references/page-style-guide.md** → L1+ 额外读 page-assembly.md → L3 额外读 dct-doc-api.md。不要一次性全读。

---

## 七、生成物自检清单

交付前核对：

- [ ] **UI 优先用 cmx-data-comp 组件**（cmx-revo-grid/cmx-ui5-form/cmx-dict-select/cmx-floating-dialog/cmx-pager 等）；任何自研组件均已与用户沟通确认
- [ ] `models` 数组里每个实例都有 `modelType` + `instanceId` + `props`
- [ ] 所有 `instanceId` 不冲突，且与 DOM 属性 / pageFns 引用一致
- [ ] schema 路径树无重名 id，所有 path 用 `.` 分隔完整路径
- [ ] ColumnModel 的 `datasetId` 是单层名；DOM 的 `data-cmx-dataset-id` 是完整路径
- [ ] DOC/DCT 用 `application`；FC 用 `app`
- [ ] FC 的 `columnModelId` 指向已存在的 CmxColumnModel instanceId
- [ ] aggregations 的 `from`/`to` 都是 schema 中存在的路径
- [ ] pageFns 里的脚本符合 `function(event, host){ with(host){...} }` 语义
- [ ] L1+ 页面有 `initPage` interface 触发数据装载
- [ ] 没给 CmxColumnModel 写内置事件
- [ ] 根 div 套用标准骨架（flex column + var(--sap*)）；颜色无硬编码
- [ ] 无 `alert()`/`confirm()`/原生 `<button>`/`<select>`/手搓模态
- [ ] **换肤**：可视组件不写 `data-cmx-skin` 即走门户默认 Neo；要换色用 `data-cmx-skin-tone`，不要复制皮肤源到页内重写
- [ ] **主题跟随**：所有色值走 `var(--sap*)` / `var(--neo-*)` 派生，UI5 切 light/dark 时页面**自动跟随**，无白底闪烁
- [ ] **多主题支持**：若页面要响应用户换肤（URL `?skin=`、偏好、菜单），由 `pageFns` 通过 `host.<instanceId>` 监听皮肤变更事件或 `MutationObserver` 改 `data-cmx-skin` / `data-cmx-skin-tone`，**不要**直接 `setAttribute('style', ...)`

---

## 附：弹层 / 网格 实战陷阱（MDM 页面沉淀，生成前必读）

> 以下为本仓库业务页实测踩坑结论，违反即出现"弹框左侧一条线 / 表格不显示行 / 增行没反应"。

1. **模态优先用 `<cmx-floating-dialog>`**（框架组件，自管挂载与样式）。若确需自绘弹层：必须 `document.body.appendChild(mask)` 且 mask 内首行自带内联 `<style>`，类名加前缀（`.mdm-mask/.mdm-dlg`）防污染；**不要**把 `position:fixed` 弹层放进带 transform 的容器内（遮罩左缘会产生一条明暗分界线）。
2. **弹层内的 `cmx-revo-grid` 行可能不渲染**（初始化时序：`setDataSet/addRow` 后数据集有行但可视网格空白）。
   对策：① 弹层入 DOM 且可见后再绑数据并调 `refreshLayout()`；② **小型可编辑/只读明细（如银行账户行）直接用普通 `<table>` + 状态数组驱动**，增删即时可见、取值可靠，规避时序问题。
3. **增/删行后必须刷新可视网格**：用 `CmxDataSet.addRow/removeRow`（会触发 `_refreshSource`）或 grid `refreshLayout()`；只改数据集不刷新 = 用户点击"没反应"。

---

## 附二：页内打开并列标签页（openNode + initialContext + 单例/多开）

> 详情/新增/编辑应为**并列门户标签页**（关闭一个不影响另一个），不用弹框。pageFns 在主 realm 执行，可直达 `cmx-portal-app.openNode(node, { initialContext })`（与"列表→详情"同一模式）。

```js
// pageFns 内
function openTab (caption, nativePageOrHtmlPage, context, opts = {}) {
  const app = document.querySelector('cmx-portal-app')
  if (!app?.openNode) return
  const ctxKey = (context && (context.crId || context.id)) || ''
  const key = opts.single ? 'single' : (ctxKey || Date.now())   // 单例 vs 多开
  app.openNode({
    id: `${nativePageOrHtmlPage}-${key}`, name: nativePageOrHtmlPage, caption, type: 'workspace-node',
    workspace: { content: { caption, views: [{ type: 'native_pages' /* 或 html_pages */, native_page: nativePageOrHtmlPage, view: 'content' }] } },
  }, { initialContext: context })
}
```

- **单例/多开**（addTab 按 id 去重）：`opts.single=true` 固定 id → 重复点击复用/聚焦同一 tab（如「新增」）；默认 id 含行 id → 不同行多开（如「详情」）。
- **目标页读参**：`ctx.host?.workspace?.context?.get?.('crId')`（initialContext 注入 workspace.context）。
- 目标页须在 `index.json`（native）或菜单/设计器（html_pages）注册，可不在菜单展示。
- 范例：MDM `cr-editor.js`→`cr-form.js`/`cr-detail.js`/`supplier-detail.js`。

---

## 八、相关技能（生成页面之后）

本技能负责生成**设计器业务页面**（html-pages）。下列需求转交其它技能：

- **`native-page-generator`** —— 页面是**纯代码**（不走设计器、不用 `__designer_meta__`、JS 模块导出 render 函数）时用。典型：元数据驱动的通用页（`doc-loader.js`）、管理类页面（`notify/center.js`）。
- **`menu-generator`** —— 页面要**挂到门户菜单** / 配置工作区节点 / 给页面注入 `props` 时用（改 `menu-pages` JSON + 跑脚本重生成 `init_menu.sql`）。
- **`cmx-components-guide`** —— cmx-data-comp 组件使用手册（96 个自定义元素的配置项 / API / 事件 / slot / 使用配方）。本技能 Step 0 只做组件**选型**（用哪个组件），组件**详细用法**转交该技能。

> 用户说"加个菜单""挂到门户""配置 workspace 节点"等涉及菜单 / `menu-pages` / `init_menu.sql` 的需求 → `menu-generator`；说"不走设计器""纯代码页""native 页"→ `native-page-generator`；说"cmx-revo-grid 怎么配""cmx-dict-select 有哪些参数""cmx-pager 事件""cmx-floating-dialog 的 slot 结构"→ `cmx-components-guide`。直接调用对应技能，不要在本技能里复制其逻辑。
