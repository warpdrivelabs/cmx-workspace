# DCT / DOC / FLC 元数据定义体系 —— 通用化 · 国际化 · 业务化 演进方案

> 目标：让模型中心三种核心元数据定义（**DCT 数据字典 / DOC 业务单据 / FLC 弹性组合**）更通用、更国际化、覆盖面更广，同时更能被**技术用户**与**业务用户**双方理解和接受。
>
> 范围：仅**定义体系（元数据 schema + 术语 + 编辑体验）**的演进方案，不动代码、不改运行时引擎。
>
> 状态：方案（草案）。日期 2026-08-24。

---

## 0. 结论先行（TL;DR）

现状比预期好——**地基是对的，缺的是"补全 + 标准化 + 换皮"**，不是推倒重来：

- **国际化的容器已存在**：所有 `caption` 都是 locale-map（`{"zh_CN": "..."}`，0 处裸字符串），但**只有 zh_CN 一种语言**（2644 处 zh_CN，0 处 en_US）。→ 缺的是"多语言值 + 全字段覆盖 + 回退链"，不是机制。
- **BI 标准语义已内建**：字段级 `dimType` = dimension（维度，435）/ attribute（属性，1095）/ measure（度量，134）/ relation（关系，10），与 SAP/dbt/Metabase 的"维度-属性-度量"三元完全对齐。→ 缺的是"语义类型再上一层（semantic type）+ 业务友好命名"。
- **DOC 已是通用实体图**：`voucherSchema` = 多层 `schema[]` + `relations`（父子）+ `aggregations`（上卷），本质是"实体关系图 + 聚合"，但被**会计/凭证术语**包裹（voucherTables/凭证批/借贷平衡）。→ 缺的是"去会计专有名词、泛化为通用单据/主子实体"。
- **三者本是一套**：DCT（引用数据/主数据）与 DOC（事务数据/业务单据）都是"实体类型"，差别在基数与角色；FLC 是"按上下文动态改列"的规则层，维度锚点 → 引用 DCT，目标列 → 落在 DOC 的主从层上。→ 可用**统一实体元模型 + 三种 profile** 表达，而非三套割裂 schema。

**四条演进主线**：
1. **国际化 I18N**：locale-map 全覆盖 + BCP 47 规范 + 回退链 + 外置翻译包（对标 SAP i18n bundle / CDM `is.localized.displayedAs`）。
2. **术语业务化 TERMS**：一套"技术名 ↔ 业务名"双轨词汇表；去会计专有词（voucher→document、借贷→通用度量）；FLC 更名。
3. **通用化 GENERALIZE**：统一实体元模型（EntityType + Field + Relation + semantic type）；DCT/DOC/FLC 收敛为其上的三个 profile；字段"结构 / 语义 / 展示"三层解耦。
4. **可理解性 UX**：双视图编辑（业务向导视图 + 技术 schema 视图）；模板库 + 示例库；渐进式披露。

---

## 1. 背景与现状（基于真实定义文件的独立核查）

### 1.1 三种定义各是什么

| 定义 | 全称 | 一句话 | 物理落地 | 顶层结构 |
|---|---|---|---|---|
| **DCT** | Data Dictionary 数据字典 | "有哪些可选值/主数据"（如会计科目表 1000+ 科目） | `cf_*` 表 | `moduleMeta` + `dictionaryTables[]` |
| **DOC** | Document 业务单据 | "要填哪些字段"（如凭证=表头+分录，多层主从） | `cv_*` 表 | `moduleMeta` + `voucherSchema` + `voucherTables[]` |
| **FLC** | Flexible Combination 弹性组合 | "按上下文动态改列"（选了应收账款→列变辅助核算） | 不落表（规则） | `moduleMeta` + scenario/anchor/columns |

> 三者共享 `baseXxxMetaRef`（引用基础字段集）+ `fieldSets`（可复用字段组）+ 字段级 `caption`/`dataType`/`dimType`。

### 1.2 已验证的真实结构片段

**DCT/DOC 字段（base_dct_meta_v1.json，真实片段）**——注意 caption 已是 locale-map，且结构/语义/展示三类属性混在一个字段对象里：
```json
{
  "id": "code", "name": "code",
  "caption": { "zh_CN": "字典项编码" },      // ← i18n 容器已在，但仅 zh_CN
  "dataType": "VARCHAR", "fieldLength": 64,  // ← 物理/结构
  "nullable": false, "required": true,
  "dimType": "attribute",                     // ← BI 语义（dimension/attribute/measure/relation）
  "edit": { "mode": "cmx-text-input", "required": true },  // ← 展示/编辑（UI 关注点）
  "display": { "mode": "text", "align": "left" },
  "width": "140px", "frozen": false
}
```

**DOC 多层实体图（cmxfico_doc_meta_v2.json，真实片段）**——这是一张通用"主子实体 + 聚合"图，却叫 voucher：
```json
"voucherSchema": {
  "schema":  [ { "id": "cv_batch", "kind": "list", "level": "L1", "levelName": "凭证批" }, … ],
  "relations": [ { "parent": "cv_batch", "child": "headers", "parentKey": "id", "childKey": "upper_id" }, … ],
  "aggregations": [ { "from": "…entered_dr", "to": "上层", "field": "entered_dr", "agg": "sum" }, … ]
},
"voucherStatusFlow": { "stateField": "doc_status", "states": [ {"code":"draft","name":"草稿"}, … ], "transitions": [ … ] },
"validationRules": [ { "code": "voucher_local_balance", "expr": "sum(account_lines.local_dr) == sum(account_lines.local_cr)", "message": "凭证本位币借贷必须平衡" } ]
```
`fieldOverrides.<col>.refDict` = 外键指向字典（DCT）；`organizationDict`/`documentTypeDict`/`keyDicts` = 语义角色标记；`codeRule` = 自动编号。

**FLC 弹性组合（account.json / cmxfico.json 真实片段）**——它是三者的"keystone"：DOC 出表树、DCT 出维度字典、FLC 决定"某锚点值下，L4 明细网格显示哪些 DOC 列（每列背后接一个 DCT 字典）"。核心是**规则表**：条件（anchor.match）→ 结果（detail 列）：
```jsonc
"docRef": { "file": "gl_md_doc_meta_v1.json", "title": "总账" },   // ← FLC 挂在哪张 DOC 上
"dimensions": {                                                    // ← 维度池（每维接一个 DCT 字典）
  "gl_account": { "dict": { "dictCode": "gl_account", "codeCol": "item_code", … }, "valueType": "dict-select" }
},
"rules": [ {
  "id": "fi-receivable", "caption": "应收账款",
  "anchor": { "dimensions": ["gl_account"], "match": { "gl_account": "2000013" } },  // ← 条件：科目=应收账款
  "detail": { "table": "cv_acc_line", "pick": [                                       // ← 结果：叠加/改列
    { "ref": "cv_aux_line.customer_id", "over": { "caption": {"zh_CN":"客户"}, "edit": {"mode":"cmx-dict-select"} } }
  ], "groups": [ { "caption": "辅助核算", "members": ["customer_id"] } ] }
} ]
```
运行时：主行选值 → anchor 变 → 引擎按 match **打分**（精确=3/属性命中≈1/兜底`match:{}`）→ 胜出规则 `detail` 编译成列 → `columnModel.setMembers(cols)` → 网格重渲染。**FLC 改"横向有哪些列"，MasterSlave 改"纵向行怎么级联/汇总"，二者经同一个 `CmxColumnModel` 实例桥接、从不直接通信。**

### 1.3 现状体检：好的、缺的、绊脚的

**✅ 已经对的（可放大）：**
- i18n 用 locale-map 容器（不是裸串）——机制正确。
- dimension/attribute/measure/relation 语义——与国际 BI/语义层标准一致。
- DOC 的主子层 + 关系 + 聚合 + 状态机 + 校验表达式——是完整的通用单据模型。
- `fieldSets` 复用、`baseXxxMetaRef` 继承——DRY，避免重复维护。
- DAM（Domain/Application/Module）三段坐标 + 版本 + `isDefault`——多租户/多版本就位。

**⚠️ 缺的 / 绊脚的：**
| 类别 | 问题 | 证据 |
|---|---|---|
| 国际化 | 只有 zh_CN 一种语言；`name`/`id` 是拼音/英文混杂但无对照；错误消息/枚举值/校验 message 多为裸中文串 | 2644×zh_CN，0×en_US；`message:"凭证本位币借贷必须平衡"` |
| 国际化-无容器 | **`caption` 只覆盖 `fields[]`**；`fields[]` 之外的 label 连 locale-map 容器都没有、是裸中文串：`dictName`/`tableAlias`/`levelName`/状态&转换 `name`/`validationRules.name`&`.message`/`enumValues.label`/`display.badgeMap.text` → 国际化这些**须改 schema，不只是补翻译** | base `doc_status.badgeMap:{draft:草稿,posted:已过账}` |
| 国际化-控制token | 中文当**控制 token**（非显示文本）：`aggregations.to:"上层"` 引擎按此字面 key 判逻辑，翻译即断 | doc voucherSchema |
| 术语 | 会计专有词硬编进"通用"层：`voucherTables`/`voucherSchema`/`凭证批`/`entered_dr`(借方)/`借贷平衡` | DOC schema 通篇 |
| 术语-base污染 | **财务/SAP 假设烧进 base（本应领域中立）**：`doc_status.badgeMap` 会计过账生命周期、`scope_type:global/acct_entity`(核算主体)、`reverse_doc_id`(红冲)、6 币借贷上卷、字段 `physicalField:MANDT/BUKRS`(SAP 列名) | base_doc + base_dct |
| 类型系统 | `dataType` **整数宽度全塌成一个 Int**（TINYINT/SMALLINT/INT/BIGINT 编译后无法区分，元数据带的宽度被丢）；未知 token **静默变 String**（不报错）；**两份不一致的 dataType→PG 映射**（compile.rs vs doc-model/meta.rs） | compile.rs map_field_type |
| 语义类型 | 只有粗粒度 dimType，缺"语义类型"（email/phone/money/percent/entity-key/foreign-key/geo…），组件与校验只能靠约定 | 无 semanticType 字段 |
| 一致性 | `relations` 用 schema 别名（`headers`）≠ 物理 `id`（`cv_header`）；`dictKind` 枚举(BUSINESS/CLASSIFY/GROUP/RELATION) 财务/MDM 形且驱动默认 fieldSet 加载；`expr` DSL 半可执行半中文散文 | doc relations / dictKind / validationRules.expr |
| 术语 | FLC "弹性组合" / ContextProfile 双名，业务用户难懂"弹性组合"指什么 | 术语表 §2 双名并存 |
| 结构 | 字段对象把"结构(dataType)+语义(dimType)+展示(edit/display/width/frozen)"三类关注点混在一起 → 元数据既给建表用又给渲染用，耦合重 | base_dct 每个 field |
| 通用化 | DCT/DOC/FLC 三套割裂顶层 schema（`dictionaryTables` vs `voucherTables` vs scenario），概念本可统一为"实体类型 + profile" | 三类文件顶层 key 不同 |
| 语义类型 | 只有粗粒度 dimType，缺"语义类型"（email/phone/money/percent/entity-key/foreign-key/geo…），组件与校验只能靠约定 | 无 semanticType 字段 |
| 可理解性 | 定义即 JSON，业务用户须懂 fieldSet/refDict/upper_id 等技术概念才能读懂一张单据 | 无业务向导视图 |
| FLC-无范式 | FLC 有**三种 detail 写法**（`use:"*"` 全取 / `pick`Overlay 叠加改 / `fields` 全内联）+ **三种维度取值源**（`dict`/`values`/`valueSourceId`）并存，无唯一范式 → 认知负担高 | account.json 三种都有 |
| FLC-裸码 | 规则 `match` 用裸 ID（`"2000013"`/`"AC004"`）无内联标签，业务用户编规则读不懂 | cmxfico.json 全规则 |
| FLC-魔串 | `columnModelId`/dot-path(`head.items.taxes`)/`pick.ref`(`"表.列"`) 全是 stringly-typed 交叉引用，拼错**静默失败** | FLC + MasterSlave |
| FLC-三名一物 | FlexibleCombination / ContextProfile / FLC 三名，且 FLC 缩写自身不一致（"Flexible Combination" vs "Flexible Logic Combination"）；"弹性组合"描述机制非价值，业务用户望名不知义 | 术语表/文档 |
| 维度歧义 | "dimension" 一词三义：顶层维度池 / 字段 `dimType` / `anchor.dimensions` | 文档 §2 自承"容易混淆" |

---

## 2. 设计原则（对标国际标准）

综合 SAP CAP/Fiori、Salesforce Translation Workbench、Microsoft Common Data Model、OData EDM、dbt 语义层、JSON Schema 的共识，六条原则：

1. **标签与定义分离**（Separate label from definition）：显示文本按 locale 外置，改翻译不动结构。（SAP i18n bundle、CDM `is.localized.displayedAs`）
2. **引用而非内联**（Reference, don't inline）：label 是指向翻译资源的键，不是字面串。
3. **结构 / 语义 / 展示 三层解耦**：一个字段 = 物理结构层（建表）+ 语义层（含义/类型/角色）+ 展示层（怎么渲染编辑）；三层可独立演进、独立复用。
4. **语义类型优先于物理类型**：先说"这是钱/邮箱/外键/实体主键"（semantic type），再由平台推导物理类型 + 默认组件 + 默认校验。（Metabase semantic types、dbt entity types）
5. **统一实体元模型 + Profile**：DCT/DOC/FLC 不是三种"东西"，是同一"实体类型"元模型的三种用途画像（reference-data / transaction-data / dynamic-composition）。
6. **双受众双视图**：同一份元数据，业务用户看"业务向导视图"，技术用户看"schema 视图"，互为投影、单一事实源。

---

## 3. 主线一：国际化（I18N）

### 3.1 现状差距
- locale-map 只有 `zh_CN`；无 `en_US` 等；无回退链；`name`/`id` 无跨语言对照；枚举值/状态名/校验 message/字典项标签大量裸中文。

### 3.2 目标形态
- **全 label 字段皆 locale-map**：`caption`/`metaName`/`moduleName`/`levelName`/状态 `name`/校验 `message`/枚举 `label`/字典项显示名——统一 `{ "<bcp47>": "<text>" }`。
- **⚠ 优先补齐"无容器"label**：现只有 `fields[].caption` 是 locale-map；`dictName`/`tableAlias`/`levelName`/状态&转换 `name`/`validationRules.name`&`.message`/`enumValues.label`/`badgeMap.text` **连容器都没有**（裸中文串）。这批是 schema 变更（加 locale-map 容器），须**先于**翻译工作做——否则"改了翻译也无处放"。
- **⚠ 分离"控制 token"与"显示文本"**：`aggregations.to:"上层"` 这类中文当**逻辑键**用，绝不能进 i18n（翻译即断）。规范要求：凡引擎按字面比较的值一律用稳定 ASCII token（如 `to:"__parent__"`），显示名另走 locale-map。审计所有"中文字面既做逻辑又做显示"的点，拆开。
- **BCP 47 规范化**：`zh-CN`/`en-US`/`ja-JP`…（现用下划线 `zh_CN`，建议兼容期双写、新写 BCP 47 连字符，对标 SAP MDK 文件名规范）。
- **回退链**：请求 locale → 平台默认 locale → `x-default` → key 本身。避免缺翻译时空白。
- **翻译外置包（可选进阶）**：结构里只放 i18n key（如 `caption.$ref: "dct.gl_account.code"`），文本落 `i18n/<locale>.json` 资源包，对标 SAP `{i18n>key}` / Salesforce Translation Workbench。**过渡策略**：先内联 locale-map（低门槛，兼容现状），再逐步抽外置包（规模化后）。

```jsonc
// 目标：内联 locale-map（第一步，兼容现状）
"caption": { "zh-CN": "科目编码", "en-US": "Account Code", "x-default": "en-US" }

// 进阶：外置引用（第二步，规模化）
"captionKey": "fi.gl.account.code"   // → i18n/en-US.json: { "fi.gl.account.code": "Account Code" }
```

### 3.3 技术名 vs 显示名彻底分离
- **`name`/`id`（技术标识）**：稳定、ASCII、蛇形（`account_code`）——建表列名、API 字段、公式引用。永不因语言变。
- **`caption`（显示名，locale-map）**：随语言变，纯 UI。
- **产物**：字典项本身（数据行）也需显示名多语言——`labelField` 指向的列建议支持"多语言列"或关联翻译表（如 `cf_gl_account_i18n`），否则字典值仍是单语言。**这是最容易被忽略的一层：结构国际化了，数据（字典项）没国际化。**

### 3.4 交付
- i18n 规范文档（locale 键格式、回退链、必译字段清单）。
- 现有 zh-CN 定义的 en-US 基线翻译（至少 base 字段集 + 通用字典）。
- 校验：定义保存时校验"必译字段是否缺 default locale"。

---

## 4. 主线二：术语业务化（TERMS）

### 4.1 去"会计专有名词"，泛化通用层
"通用"层不该出现只有会计懂的词。建立**通用词 ↔ 领域词**映射，通用层用通用词，领域包可加领域别名（`caption`/别名机制）：

| 现状（会计专有，硬编在通用层） | 建议通用词 | 说明 |
|---|---|---|
| `voucherTables` / `voucherSchema` | `documentTables` / `entitySchema` | voucher=凭证是会计专词；document/entity 通用 |
| `凭证批`（levelName） | 该层业务名放 locale-map，结构名用 `level`/`tableName` | 结构不背业务词 |
| `entered_dr` / `entered_cr`（借/贷方） | 领域字段，留在 fico 领域包，不进 base | base 只放真正通用列 |
| `借贷平衡`（校验 message） | 领域校验，message 走 locale-map | — |
| `organizationDict` / `documentTypeDict` / `keyDicts` | 保留（这些其实通用：组织维度/单据类型/关键维度） | 但文档化其语义 |
| **base 里的 `doc_status.badgeMap`**（草稿/已过账/已冲销…会计过账态） | base 只留中性 `draft/active/closed`；具体过账态入领域包 | 现每张单据都继承中文会计过账语义 |
| **base `dictionaryScopeFields.scope_type`**（global/**acct_entity 核算主体**） | base 用中性 `global/tenant/org`；核算主体入财务包 | 财务范围模型混进通用 base |
| **base `documentSourceFields.reverse_doc_id`**（红冲/冲销） | 冲销是会计概念，入财务包 | — |
| **字段 `physicalField:MANDT/BUKRS/HKONT`**（SAP 列名） | SAP 迁移映射抽独立"映射层"，不挂在通用字段上 | 元数据耦合 SAP |
| **`dictKind` 枚举**（BUSINESS/CLASSIFY/GROUP/RELATION，且驱动默认 fieldSet） | 泛化为 `entityRole`（reference/classification/relation/group）中性词 | 现枚举财务/MDM 形 |

> 原则：**base/通用 fieldSet 只放跨行业真通用列**（主键/编码/名称/状态/审计/有效期/组织范围）；任何"借贷""科目""凭证"等落到**领域包**（fi/cmxfico），通过 `baseDocMetaRef` + 领域扩展叠加。现状 base 已较克制，需审计一遍把漏进去的会计词剔除。

### 4.2 FLC 更名与释义
"弹性组合 / FlexibleCombination / ContextProfile" 三名并存，FLC 缩写自身还两种展开（Flexible Combination / Flexible Logic Combination），业务用户望名不知义。建议：
- **主名**：`情境列 / Context-Driven Columns` 或 `动态字段规则 / Dynamic Field Rules`——直白说"它做什么"（按情境改列）。
- 保留 `FlexibleCombination` 作技术类名/兼容别名；文档统一"一名为主 + 别名表"；固定 FLC 缩写唯一展开。
- 每个 FLC 定义带一句 `purpose`（locale-map）："当[维度]=[值]时，明细列变为[列集]"——业务用户读一句话就懂。
- **消歧 "dimension" 三义**：顶层"维度池"改称 `dimensionPool`/`contextVars`，字段角色留 `dimType`，规则条件留 `anchor.on`——三处各名，不再一词三义。

### 4.3 FLC 范式收敛（去三写法、码带标签、消魔串）
- **detail 唯一范式**：三种写法（`use:"*"`/`pick`Overlay/`fields`内联）收敛为 **Overlay(`pick`) 为主**（引用 DOC 列 + 只改差异，DRY 且单一事实源），`use:"*"`/`fields` 作兼容读、逐步迁移。文档已明确 Overlay 是目标方向。
- **裸码带标签**：`match` 的裸 ID 旁并存显示标签——`"match": { "gl_account": { "value": "2000013", "label": {"zh-CN":"应收账款","en-US":"AR"} } }`，业务用户编规则可读。
- **消魔串（设计期校验）**：`columnModelId`/dot-path/`pick.ref` 保存时校验"目标存在"，拼错即报错而非运行时静默失败（这是可理解性 + 健壮性双赢，属编辑器/校验层，不改运行时引擎）。
- **维度字典去重复声明**：维度 `dict` 块现**重抄** DCT 的 idCol/codeCol/... → 改为只写 `dictRef`（指向 DCT），取数配置从 DCT 继承（文档已标注此重复待重构）。

### 4.4 统一"双轨词汇表"
产出一份**术语对照总表**（技术名 · 业务名 · 英文名 · 一句话解释 · 示例），三受众（后端/前端/业务）共用；编辑器 tooltip、文档、错误提示都引它。示例：

| 技术名 | 业务名(zh) | 英文名 | 一句话 |
|---|---|---|---|
| dimType=dimension | 维度/分析轴 | Dimension | 用来"按它分组/筛选"的字段（客户、产品、期间） |
| dimType=measure | 度量/数值 | Measure | 可加总/计算的数值（金额、数量） |
| refDict | 取值来源字典 | Reference (FK) | 这列的值来自某个字典表 |
| aggregations | 自动汇总 | Rollup | 子表变了，主表自动重算合计 |
| anchor | 情境锚点 | Anchor / Context | 触发列变化的维度值组合 |

---

## 5. 主线三：通用化（统一实体元模型 + Profile）

### 5.1 核心洞察：DCT/DOC/FLC 是一套
- **DCT** = 单实体、引用/主数据角色（reference data）、通常"一张表 + 可选自分级/分类"。
- **DOC** = 多实体、事务数据角色（transaction data）、"主子多层 + 关系 + 聚合 + 状态机"。
- **FLC** = 不是实体，是**作用于实体字段的规则层**（按维度上下文重写"显示哪些列"）。

三者可用**一个实体元模型**表达（对标 OData EDM EntityType / CDM Entity / dbt semantic model）：

```
EntityType(实体类型)
 ├─ identity        主键/编码/显示名（entity-key / code / label）
 ├─ role            reference | transaction | (composition 规则不建实体)
 ├─ fields[]        Field（见 5.2 三层解耦）
 ├─ relations[]     RelationDef（parent/child/key，= DOC 的 relations，= DCT 自分级/分类）
 ├─ aggregations[]  AggRule（子→父上卷，= DOC aggregations）
 ├─ lifecycle       StatusFlow（状态机，= voucherStatusFlow）
 ├─ constraints[]   ValidationRule（表达式校验）
 ├─ identityCode    CodeRule（自动编号）
 └─ i18n/labels     locale-map
```

- **DCT profile**：role=reference，单实体（或加 self-relation=自分级、加 classification-relation=带分类）。
- **DOC profile**：role=transaction，多实体 + relations + aggregations + lifecycle。
- **FLC**：独立"规则资源"，引用某 EntityType 的字段集，声明 `when anchor(dim=val) then columns[...]`。

> **收益**：三者共享同一套字段/关系/校验/i18n 机制；学一次会三样；编辑器、校验器、文档一套；新领域扩展只填 profile 差异。**兼容策略**：顶层保留 `metaKind`（DCT/DOC/FLC/RPT）作 profile 判别，旧 `dictionaryTables`/`voucherTables` 作兼容别名映射到 `entities[]`，不破坏现有文件。

### 5.2 字段三层解耦（结构 / 语义 / 展示）
把现在混在一起的字段对象拆成三层视图（**物理仍是一个对象，逻辑分区 + 校验分区**）：

```jsonc
{
  "id": "amount", "name": "amount",              // —— 标识（稳定技术名）
  "structure": {                                  // —— 结构层（建表用）
    "dataType": "DECIMAL", "precision": 18, "scale": 2, "nullable": false
  },
  "semantic": {                                   // —— 语义层（含义/角色/类型）
    "dimType": "measure",
    "semanticType": "money",                      // ★ 新增：语义类型（见 5.3）
    "unitRef": "currency", "role": "amount"
  },
  "display": {                                    // —— 展示层（怎么渲染/编辑，纯 UI）
    "caption": { "zh-CN": "金额", "en-US": "Amount" },
    "edit": { "mode": "cmx-money-input" }, "align": "right", "width": "140px"
  }
}
```
- **建表编译器**只读 `structure`；**组件/校验**读 `semantic`；**渲染**读 `display`。互不干扰。
- 现状字段可**平滑迁移**（把 dataType→structure，dimType→semantic，edit/display/width→display），保留旧字段名做兼容读取。

### 5.3 语义类型（Semantic Type）——覆盖面的关键
在 dimType 之上加一层"语义类型"，直接表达业务含义，平台据此推导物理类型 + 默认组件 + 默认校验 + 默认格式：

| semanticType | 物理推导 | 默认组件 | 默认校验/格式 |
|---|---|---|---|
| `entity-key` | BIGINT/VARCHAR | 只读 | 唯一、非空 |
| `code` | VARCHAR | 文本 | 唯一、编码规则 |
| `label` | VARCHAR / 多语言 | 文本 | 显示名（可多语言） |
| `foreign-key`(refEntity) | 同目标键 | 下拉/查找 | 引用完整性 |
| `money`(unit) | DECIMAL(18,2) | 金额框 | 币种、千分位 |
| `quantity`(uom) | DECIMAL | 数量框 | 计量单位 |
| `percent` | DECIMAL(9,4) | 百分比框 | 0–100/0–1 |
| `email`/`phone`/`url` | VARCHAR | 对应输入 | 格式正则 |
| `date`/`datetime`/`period` | DATE/TS | 日期选择 | 会计期间/时区 |
| `enum`(options) | VARCHAR/INT | 单选 | 值域约束 |
| `boolean-flag` | SMALLINT | 开关 | 0/1 |
| `geo`/`json`/`attachment` | … | … | … |

> 覆盖面从"会计字段"扩到"任意行业实体"：只要能归到一个 semanticType，就自动获得建表+组件+校验，无需每次手配。对标 Metabase semantic types、OData EDM 的 typed properties。

**顺带修物理类型系统三处硬伤**（现状 `map_field_type`）：
- **整数宽度不再塌缩**：现 TINYINT/SMALLINT/INT/BIGINT 编译后全成一个 `Int`（元数据带的宽度被丢，DB-first 往返有损）→ 保留宽度到物理类型（int2/int4/int8）。
- **未知类型不静默**：现未知 token 静默变 String → 改为定义保存时校验/报错（未知类型是错误，不是"默认 String"）。
- **统一两份映射**：现 `compile.rs` 与 `doc-model/meta.rs` 各有一份 `dataType→PG` 且不一致（前者缺 NVARCHAR/TIMESTAMPTZ，后者缺 LONG/CLOB/NUMBER）→ 收敛为单一权威映射表，两处共用。

### 5.4 关系与层级的统一表达
- DOC 的 `relations`（主子）、DCT 的自分级（parent_id 自引用）、DCT 的带分类（分类表→字典表）+ RELATION 字典（多对多）——都是 `RelationDef { kind: composition|self-hierarchy|classification|reference|many-to-many, parent, child, keys }`。统一后"三套字典工作台（平级/自分级/带分类）"退化为**同一实体 + 不同 relation 配置**，概念与代码都收敛。
- **顺带修 relations 别名不一致**：现 `relations` 用 schema 别名（`headers`）≠ 物理 `id`（`cv_header`），易错 → 统一用稳定 id 引用。

### 5.5 一个跨行业例子：同一模型建"客户主数据"和"服务工单"（非会计）
证明通用化后**任意行业**都能建，业务用户读得懂：

**DCT profile — 客户主数据（reference data，替代硬编的会计字典）：**
```jsonc
{ "entity": "customer", "role": "reference",
  "label": { "zh-CN": "客户", "en-US": "Customer" },
  "identity": { "key": "id", "code": "customer_no", "label": "name" },
  "fields": [
    { "name": "customer_no", "semantic": { "semanticType": "code" }, "display": { "caption": {"zh-CN":"客户编号","en-US":"Customer No."} } },
    { "name": "name",     "semantic": { "semanticType": "label" },   "display": { "caption": {"zh-CN":"客户名称","en-US":"Name"} } },
    { "name": "industry", "semantic": { "semanticType": "foreign-key", "refEntity": "industry" }, "display": { "caption": {"zh-CN":"所属行业","en-US":"Industry"} } },
    { "name": "email",    "semantic": { "semanticType": "email" }, "display": { "caption": {"zh-CN":"邮箱","en-US":"Email"} } }
  ] }
```

**DOC profile — 服务工单（transaction data，主子两层，替代硬编的凭证）：**
```jsonc
{ "entity": "service_ticket", "role": "transaction",
  "label": { "zh-CN": "服务工单", "en-US": "Service Ticket" },
  "entities": [
    { "path": "ticket", "table": "st_ticket",  "level": "L1", "label": {"zh-CN":"工单","en-US":"Ticket"} },
    { "path": "ticket.items", "table": "st_item", "level": "L2", "label": {"zh-CN":"工时明细","en-US":"Work Items"}, "childKey": "ticket_id" }
  ],
  "relations": [ { "kind": "composition", "parent": "ticket", "child": "ticket.items", "parentKey": "id", "childKey": "ticket_id" } ],
  "aggregations": [ { "from": "ticket.items", "to": "ticket", "field": "hours", "toField": "total_hours", "agg": "sum" } ],
  "lifecycle": { "stateField": "status",
    "states": [ {"code":"open","label":{"zh-CN":"待处理","en-US":"Open"}}, {"code":"closed","label":{"zh-CN":"已关闭","en-US":"Closed"}} ] } }
```

同一套机制（identity / semantic field / relation / aggregation / lifecycle / i18n）——**没有一个会计词**，业务用户看 label 即懂，技术用户看 structure 即建表。这正是"更通用、更国际化、覆盖面更广"的落点。

---

## 6. 主线四：可理解性（技术 + 业务双受众）

### 6.1 双视图编辑（同一元数据，两种投影）
- **业务向导视图**（业务用户）：分步问答式——"这是什么业务对象？有哪些信息（字段）？哪些是分类轴、哪些是数值？值从哪来（字典）？要不要审批流转？"——不暴露 dataType/refDict/upper_id 等技术词，用 §4.3 业务词。产出即元数据。
- **Schema 视图**（技术用户）：直接编辑 JSON/表格化 schema，全字段可见，含 structure 层。
- 二者**同一事实源**、实时互转；业务视图是 schema 视图的"降噪投影 + 术语翻译"。

### 6.2 模板库 + 示例库（降低冷启动）
- **实体模板**：客户/供应商/物料/员工/组织/科目/币种…（reference data 常见主数据，已有 `cm_*` seed 可直接沉淀为模板）；订单/发票/凭证/入库单…（transaction data 常见单据）。
- **FLC 场景模板**：辅助核算、按类型附加字段、按地区改必填…
- 每模板带"业务说明 + 可改点标注 + 反例"，业务用户"选模板→改字段名→存"即可产出。

### 6.3 渐进式披露 + 内联释义
- 编辑器默认只显最常用字段属性（名称/类型/是否必填/取值来源），高级项（precision/frozen/aggregation）折叠。
- 每个技术概念挂 tooltip，引 §4.3 词汇表一句话解释 + 示例。

### 6.4 可读性产物
- 每份定义可一键生成**人话版说明**（"客户主数据：含 12 个字段，其中 客户编码 唯一、名称 支持中英文、所属行业 取自 行业字典…"）——供业务评审、文档、AI 问答。

---

## 7. 演进路线（分阶段，均不破坏现有文件）

| 阶段 | 内容 | 兼容策略 | 验收 |
|---|---|---|---|
| **P0 规范与词汇** | i18n 规范 + BCP47 + 必译字段清单；双轨术语总表；semanticType 目录；FLC 更名 | 纯文档，零改文件 | 三受众评审通过 |
| **P1 国际化补全** | 现有 zh-CN 定义补 en-US 基线（base+通用字典优先）；locale-map 全 label 覆盖；回退链规范 | 内联 locale-map，旧 zh_CN 兼容读 | en-US 切换无空白 |
| **P2 字段三层 + 语义类型** | 字段引入 structure/semantic/display 分区 + semanticType；建表/组件/校验按分层读取 | 旧扁平字段兼容读取（读时归一） | 一个新领域实体全走 semanticType 建成 |
| **P3 统一实体元模型** | 顶层收敛 EntityType+profile；dictionaryTables/voucherTables 作别名映射 entities[]；relation 四态统一 | metaKind 判别 profile；旧 key 兼容 | DCT/DOC/FLC 各一例迁到统一模型 |
| **P4 双视图 + 模板库** | 业务向导视图（编辑器）；实体/单据/FLC 模板库；人话版说明生成 | 与 schema 视图同源 | 业务用户独立建成一个主数据 + 一张单据 |
| **P5 数据层国际化** | 字典项（数据行）显示名多语言（i18n 列/翻译表）；枚举/状态值多语言 | 新增列/表，不改主表 | 字典值中英文切换 |

> 每阶段独立可交付、可回退；P0/P1 纯增量低风险，P3 概念收敛最大但用 profile+别名保兼容。

---

## 8. 风险与取舍

- **过度抽象风险**：统一实体元模型若做过头，会让"简单字典"也要填一堆 profile。→ 对策：profile 提供强默认（DCT profile 默认 role=reference、单实体），简单场景零额外负担。
- **迁移成本**：字段三层拆分涉及所有存量定义。→ 对策：读时归一（兼容层），不强制一次性改写；新定义走新结构，旧的按需迁。
- **翻译工作量**：全量 en-US 是人力活。→ 对策：base+通用字典优先（覆盖面最大）；领域包按需；可接 AI 预翻译 + 人工校对。
- **业务向导 vs schema 双向同步**：投影不一致会出 bug。→ 对策：schema 为唯一事实源，向导只读投影 + 受限写回，冲突以 schema 为准。
- **"弹性组合"更名**：已有文档/用户习惯。→ 对策：主名换、旧名留别名，双名过渡期并存。

---

## 9. 附：现状 vs 目标 一图对照

| 维度 | 现状 | 目标 |
|---|---|---|
| 语言 | zh_CN 单语（机制已 locale-map） | 多语 BCP47 + 回退 + 外置包 |
| 术语 | 会计专有词进通用层；FLC 三名 | 通用词 + 领域别名；FLC 一名为主 |
| 字段 | 结构/语义/展示混一体 | 三层解耦 + semanticType |
| 顶层 | DCT/DOC/FLC 三套割裂 schema | 统一 EntityType + 三 profile |
| 关系 | 平级/自分级/带分类三套工作台 | 一实体 + 四态 relation |
| 受众 | JSON 即定义，业务用户难读 | 业务向导视图 + schema 视图双投影 |
| 数据 | 字典项单语言 | 字典项多语言 |

---

## 参考（国际标准对标）

- SAP — Internationalization (i18n)：标签外置 i18n bundle、`{i18n>key}` 引用、BCP 47 文件名规范。 [SAP Help — i18n](https://help.sap.com/docs/bas/developing-sap-fiori-app-in-sap-business-application-studio/internationalization-i18n)
- Salesforce — 元数据翻译（Translation Workbench）vs 代码串（Custom Labels）分离。 [Salesforce Localization](https://better-i18n.com/en/blog/salesforce-localization/)
- Microsoft Common Data Model — 本地化 trait `is.localized.displayedAs` / `is.identifiedBy` / `is.CDM.attributeGroup`。 [CDM CustomDimensionMetadata](https://learn.microsoft.com/en-us/common-data-model/schema/core/industrycommon/sustainability/SustainabilityShared/customdimensionmetadata)
- Metabase — 语义类型（semantic types：Entity key / Foreign key…）区别于存储类型。 [Metabase semantic types](https://www.metabase.com/docs/latest/data-modeling/semantic-types)
- dbt — 语义模型 entity 类型（primary/foreign）、以 transaction 为主实体范例。 [dbt semantic models](https://docs.getdbt.com/docs/build/semantic-models)
- DataHub — schema-first 元数据建模（Entity/aspect）。 [DataHub metadata model](https://docs.datahub.com/docs/metadata-modeling/metadata-model)
