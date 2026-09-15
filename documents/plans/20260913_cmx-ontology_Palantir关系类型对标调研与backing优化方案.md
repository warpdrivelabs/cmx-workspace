# Palantir 关系类型对标调研与 backing 优化方案

> 2026-09-13 · cmx-ontology（本体平台）
> 调研来源：Palantir Foundry 官方文档 Object link types 四篇（overview / create / edit / metadata reference）。
> 目的：统一本平台关系落存储方式（`om_link_type.backing`）的口径分裂——前端只写 `{"fk":{...}}`、
> 模型层只认 `{"kind":"foreignKey",...}`、JoinTable/Intermediary 仅声明占位——并以 Palantir 为对标补齐。

---

## 一、Palantir 关系类型（Link Type）是怎么定义的

### 1.1 概念模型（link-types-overview）

- **Link Type = 关系的 schema 定义**；**Link = 该关系在两个对象间的一个实例**。类比"两张数据集的 JOIN"（类型）与"某一行与另一行的连接"（实例）。
- **双向两端**：一个 link type 恒有两个 side（每端各一个对象类型），**每端各有自己的 apiName + displayName**（如 `Flight.assignedAircraft.get()` / `aircraft.flights.all()`）——定义一次即双向可遍历，**不需要再定义反向关系**。
- **自引用**允许（Employee ↔ 自身，"直属下属 ↔ 经理"）；同一对对象类型之间允许**多条** link type（每端 apiName 在该对象类型关联的关系内唯一）。
- **跨 Ontology 的关系不支持**（建议共享本体）。
- 卡inality 枚举：one-to-one、one-to-many、many-to-one、many-to-many；**one-to-one 不强制约束**（not enforced）。

### 1.2 三种 backing（create-link-type 的"关系类型"三选一，即 join method）

| # | Palantir 名称 | 适用 cardinality | backing 语义 | 关键规则 |
| --- | --- | --- | --- | --- |
| 1 | **Object type foreign keys**（对象类型外键） | one-to-one / many-to-one | **一端对象类型上的外键属性，存另一端对象类型主键的值**（如 Flight.TailNumber ← Aircraft.TailNumber(PK)） | 自动探测外键的前提：**值匹配对端主键** 且 两侧属性类型匹配；编辑侧约束：非 many-to-many 时"其中一端的 key 必须映射到该端自己的 Primary key"（保 one 端唯一） |
| 2 | **Join table dataset**（连接表数据集） | many-to-many | 一个"主键对"数据集，两列分别映射到两端的主键 | **一列只能映射一个主键**；可一键"Generate join table"按两端主键自动建表；**写回（writeback）必须有 backing datasource**；**一个 datasource 只能背一条 link type**（复用报 `Phonograph2:DatasetAndBranchAlreadyRegistered`） |
| 3 | **Backing object type**（对象背书 / object-backed link） | many-to-one 扩展（效果上多对多+边上带元数据） | 用一个**中间对象类型**承载关系：两端各经一条既有 many-to-one 关系连到中间对象（如 Aircraft ↔ FlightManifest ↔ Flight） | 前置：两端对象类型、中间对象类型、两侧到中间对象的关系**都必须已存在**；**关系的额外元数据放在中间对象上**（如机长/副机长）；Object Explorer / Vertex / Workshop 可见，Vertex 中关系标题显示中间对象标题；支持从"外键/连接表"**转换**为 object-backed |

### 1.3 元数据模型（link-type-metadata）

| 字段 | 说明 |
| --- | --- |
| ID / RID | 平台唯一标识 / 资源 RID（报错引用） |
| **Status** | active / experimental / **新建默认 experimental** / deprecated |
| Object types | 两端对象类型 |
| **Cardinality** | 告知应用每端是一还是多（Employee→Employer：Employee 端 many） |
| **Key** | 建立连接的键：非 many-to-many = 一端外键属性 → 另一端主键；many-to-many = 连接表两列到两端主键的映射 |
| Display name | **每端一个**用户可见名 |
| **Plural display name** | 复数显示名（many 端展示列表用） |
| API name | 每端一个编程名：小写字母开头、仅字母数字、同对象类型关联的关系内唯一、1–100 字符、NFKC、非保留字 |
| **Visibility** | prominent（优先展示）/ normal（默认）/ hidden（应用中不展示） |
| Type classes | 供应用解释的附加元数据 |

### 1.4 编辑约束（edit-link-types）

- 可改：Status、**Key**（外键/列映射）、Visibility、Type classes、API name（**active 态不可改**）。
- **改 cardinality / 换外键 / 换 many-to-many backing 数据集 / 删除** → 需注销重索引，期间关系在应用中不可用（Workshop search-around 断链直至重建完成）。
- **active 态不可删除**；删除需确认并在保存后生效。
- 曾被写回过的数据集改列名/类型也需注销重注册（编辑历史在 Object Storage v1）。

---

## 二、本平台现状与差距（对标表）

本平台已有模型（`cmx-onto-model/def.rs::LinkBacking`）：`Edge`（默认，ol_edge 物化边表）、`ForeignKey{property,side}`、`JoinTable{table,leftColumn,rightColumn}`、`Intermediary{objectType,leftProperty,rightProperty}`（后两者**仅声明占位，编译回退 Edge**）。

| 维度 | Palantir | 本平台现状 | 差距定性 |
| --- | --- | --- | --- |
| backing 模式数 | 3（FK / 连接表 / 对象背书） | 4（多一个 Edge 物化边表，**超集能力**：手工语义关系、运行时边；Palantir 无物化边） | ✅ 模式齐全，✚ 我们多一个 |
| FK 语义 | 外键属性值 = **对端主键**；类型须匹配 | 引擎 `ForeignKey{property,side}` 同语义（值=对端 pk） | ✅ 一致 |
| **口径统一** | Ontology Manager 单一口径 | ❌ **分裂**：前端 designer 只写 `{"fk":{"sourceProperty","targetProperty"}}`；模型层只解析 `{"kind":...}` tagged → **前端形状静默回退 Edge**；engine 的 FK JOIN 无人写入 | 🔴 P0 主修点 |
| FK 属性对属性匹配 | 不支持（恒等于对端主键） | 前端 `targetProperty` 暗示任意属性对；引擎只支持对端 pk | 🟡 需定义：targetProperty 缺省=对端主键（Palantir 语义），非空=对端属性匹配（超集） |
| FK 侧位 | 由建模者选外键在哪端（many 端持键） | 引擎有 `side`（a/b）；**页面口径无 side** | 🟡 页面口径补可选 `side`，缺省 a（源端） |
| JoinTable 编译 | 列→两端主键映射 | 仅声明占位，编译回退 Edge | 🟡 P0 补真编译 |
| Intermediary 编译 | 中间对象两段 many-to-one | 仅声明占位，编译回退 Edge | 🟡 P0 补真编译 |
| 每端 API name / 复数名 | 每端一个 apiName + plural display name | 全局单 apiName + roleA/roleB（显示名） | 🟢 结构性差异，P1 评估（roleA/roleB 已是每端显示名雏形） |
| Visibility | prominent/normal/hidden | 无 | 🟢 P1 增强 |
| Type classes | 有 | 无（marking/constraints 另有） | 🟢 P2 |
| Status 生命周期 | active/experimental/deprecated | TypeStatus 一致 | ✅ 一致 |
| 编辑治理 | active 不可删/不可改 apiName；改 key/cardinality 需重索引 | upsert 盲写，无治理约束 | 🟢 P1 增强（先做提示性约束） |
| 连接表唯一注册 | 一数据集只背一关系 | 无 | 🟢 P2 |

---

## 三、优化方案

### P0：口径统一 + 三模式真编译（演示后立即做，改动集中在 cmx-ontology 两 crate）

0. **口径决策（已定）**：`{"fk":{"sourceProperty","targetProperty"?,"side"?}}` 页面形状为**唯一对外口径**（落库/前端/规格/人读）；`ForeignKey{...}` 枚举退为解析后的**引擎内部视图**（不再作为序列化出口）；`{"kind":...}` tagged 仅历史兼容（老数据可解析，文档不再宣传）。选择依据：前端 designer 落库/回读已是 fk 形状（零前端改动）；fk 的「源属性→目标属性」与 Palantir 建链 UI 的「外键属性→对端主键属性」两个下拉同构。
1. **`def.rs` 解析器双认**（`backing` 字段原样落库、原样回读，前端 round-trip 不失真；本枚举仅是解析后的引擎视图）：
   - 页面口径升为一等：`{"fk":{"sourceProperty","targetProperty"?,"side"?}}`、`{"joinTable":{"table","leftColumn","rightColumn"}}`、`{"intermediary":{"objectType","leftProperty","rightProperty"}}`；
   - 内部 tagged `{"kind":...}` 继续兼容（历史/工具直写）；
   - 均无法识别 → `Edge` 兜底（现状语义不变）。
2. **`ForeignKey` 增 `targetProperty`**：缺省（空）= 对端主键（`oo_<type>.pk` 列，Palantir 对齐）；非空 = 与对端 `props->>'targetProperty'` 相等（属性对属性，超集能力，喂 explorer 任意引用列场景）。
3. **FK 侧位**：页面口径 `side` 可选字段，缺省 `"a"`（源端持键——速建气泡从源对象拉线的自然语义）；spec 显式可写。
4. **`compile.rs` 三模式真编译**（SearchAround / object-sets）：
   - FK：泛化 JOIN——`side` 端表与对端表按 `对端.pk 或 对端.props->>'targetProperty'` = `side端.props->>'sourceProperty'` 连接，正反向统一；
   - JoinTable：`SELECT DISTINCT j.<对端列> FROM <table> j WHERE j.<源端列> IN (…)`；
   - Intermediary：经 `oo_<objectType>` 两属性两跳；
   - Edge / 未识别 → `ol_edge` 兜底（现状不变）。
5. **`validate()` 四模式校验**：fk.sourceProperty 必填合法标识符；joinTable 三字段、intermediary 三字段必填合法标识符。
6. **演示规格迁移**：6 个 FK 关系的 backing 从 tagged 形状改写为页面口径（与 designer 速建气泡同构），重灌后七向遍历复验。
7. **测试**：def.rs 单测补双认解析/缺省/校验拒绝用例；live 复验。

### P1：治理增强（对齐 Palantir 编辑约束与展示元数据）

1. 关系类型加 `visibility`（prominent/normal/hidden）：explorer 关系块按序展示 prominent、隐藏 hidden。
2. 编辑约束：active 态禁删/禁改 apiName；改 key（FK/joinTable 键）与 cardinality 时返回提示"已物化边需重建/重 sync"（轻量对齐"注销重索引"，不做强制重索引机制）。
3. per-side 复数显示名（pluralDisplayNameA/B，可选字段）。

### P2：可选

1. Type classes（应用侧解释性元数据）。
2. JoinTable 数据集唯一注册检查（一表只背一关系）。
3. object-backed 关系在 360 面板展示中间对象元数据（边上带属性）。

### 验证清单（P0 完成口径）

- [ ] `{"fk":{...}}` / tagged 双认单测通过；`cargo test -p cmx-onto-model`
- [ ] 演示规格 6 关系改页面口径后重灌，`om_link_type.backing` 原样存储
- [ ] 七向遍历（settleCurrency 正/反、useUom、buyerOf 反、signContract、contractCurrency 反、contractPaymentTerm 反）全部命中
- [ ] explorer UI 钻取冒烟（正/反向各一）
- [ ] Edge 兜底回归：supplierOf/coverMaterial/storeIn 三关系遍历不回归
- [ ] 前端 designer 速建气泡建一条 FK 关系 → 引擎可直接 FK 遍历（口径闭环）

---

## 四、影响面

- `backend/cmx-ontology/crates/cmx-onto-model/src/def.rs`（解析+校验+文档注释）
- `backend/cmx-ontology/crates/cmx-ontology-store-pg/src/compile.rs`（三模式编译）
- `backend/cmx-ontology/crates/cmx-onto-model/src/lib.rs`（单测）
- `.agents/skills/cmx-onto-toolkit/`（backing 模式表 + 漏斗 FK 配方 + 坑位说明）
- 演示规格 `scenario-spec.json`（6 关系 backing 改页面口径）
- 下游无 API 破坏（backing 原样透传，仅解析视图增强）；8 个下游仓无 path 引用本体模型，无需连带回归

---

## 五、P0 执行记录（2026-09-13，范围收窄为仅 ForeignKey 前后端对齐）

按用户决策缩小本轮范围：**只做 ForeignKey 前后端口径统一**；JoinTable/Intermediary 维持声明占位（后续再做）。

已落地：

1. `def.rs`：`backing_parsed` 双认——页面口径 `{"fk":{"sourceProperty","targetProperty"?,"side"?}}` 一等解析（side 缺省 a、targetProperty 缺省=对端 pk）；tagged `{"kind":"foreignKey",...}` 兼容；`ForeignKey` 枚举增 `target_property` 字段；`validate` 校验 sourceProperty 必填 + targetProperty 选填合法性。文档注释同步「页面形状=唯一对外口径」。
2. `compile.rs::fk_search_around` 泛化：targetProperty 非空时编译**属性对属性 JOIN**（side 端 `props->>'sourceProperty'` = 对端 `props->>'targetProperty'`），空时保持「值=对端 pk」原语义；正反向遍历均覆盖。
3. 单测：`cmx-onto-model` 99 过（新增 fk 页面口径解析/最小形/缺 sourceProperty 拒绝/坏 targetProperty 拒绝 4 例）。
4. 演示规格 `scenario-spec.json` 六关系全部改页面口径 fk 形状（settleCurrency/useUom/contractCurrency/contractPaymentTerm 持键在 A 端缺省；buyerOf/signContract 键在 B 端显式 `"side":"b"`），重灌落库 `om_link_type.backing` 原样存储。
5. 验证：七向遍历全通（含属性对属性 JOIN 的 signContract 正向 SUP0001→CT-2026-001、SUP0004→CT-2026-002）；Edge 兜底回归（supplierOf/storeIn）不回归；explorer UI 重载后钻取 SUP0001→settleCurrency→CNY 通过。
6. 技能文档：`cmx-onto-toolkit/references/scenario-spec.md` linkTypes 段补 backing 页面口径说明与漏斗 FK 配方。

教训记录：signContract 首次把 targetProperty 误写为持键端自己的主键（contractNo）——页面口径的语义是「相对持键端」：sourceProperty=持键端属性，targetProperty=**对端**匹配属性，两端各选一个字段。

---

## 六、演示数据重构执行记录（2026-09-13 第二轮，v3「MDM 外键真源」口径）

用户裁决：测试数据推倒重造——「一对多/多对一不是只说说」，每条关系必须有字段级关联；多对多要讲清楚靠什么属性关联、不用中间表能否实现；以 MDM 已有元数据和表数据为准。

### 6.1 病灶（v2 数据盘点）

- `cm_contract` 明明有 `supplier_id`（bigint→cm_supplier.id）、`currency_id`（→cm_currency.id）、`payment_term_code`（→cm_payment_term.code）三条真外键，但 Contract 对象类型只声明了 supplierName，漏斗还把外键**翻译成编码**塞进 supplierId（值="SUP0001"）——UI 上「有名称没 ID」，字段级关联不可见。
- 六条 FK 关系里 4 条标成 manyToMany（settleCurrency/useUom/contractCurrency/contractPaymentTerm），物理上却只有单个外键列——基数与事实不符。
- supplierOf/coverMaterial/storeIn 三条真多对多无任何字段关联，纯手填边。

### 6.2 v3 口径（铁律）

1. **每类对象带 `id` 属性 = 来源表 `cm_*.id` 真实主键**（PaymentTerm 无代理主键，以 code 自然键为锚）；外键属性存真实外键值，`targetProperty:"id"` JOIN——语义与底层库完全一致。
2. **基数跟物理走**：单外键列 = oneToMany（A=被引用端，`"side":"b"`）；真多对多才 manyToMany。10 条关系 = 7 FK（oneToMany）+ 3 Edge（manyToMany）。
3. **多对多的答案**：ol_edge 就是平台内置连接表（Edge backing）；关系型存储里 M2M 必然要一张连接表，Palantir 同理（join table / 中间对象）。supplierOf 的 15 对边改从 **cv_po_order/cv_po_line 10 张真实采购订单履约历史聚合派生**（不再手填）；coverMaterial 5 条与订单历史恰好一致；storeIn 为仓储布局语义边。含属性的 M2M 走中间对象（两条 FK 关系），无需等 Intermediary 编译。
4. 新增第 7 条 FK 关系 **managerOf**（cm_warehouse.manager_id → cm_employee.id，WH-01→王建国/WH-02→陈静/WH-03→陈磊）。

### 6.3 改动清单

- `scenario-spec.json` 整体重写（v3）：8 类对象补 `id` 属性 + Contract 补 supplierId/currencyId/paymentTermCode 声明 + Material 补 baseUomId + Supplier 补 settleCurrencyId/buyerId + Warehouse 补 managerId；10 条 linkTypes 按上述口径；8 个漏斗 sourceQuery 全部改裸列（删掉 id→code 翻译子查询）；links 段 30 条（supplierOf 15 PO 派生 + coverMaterial 5 + storeIn 10）。
- fico 库数据微调（直接 UPDATE，演示多样性）：SUP0003/SUP0006 结算币种→USD(2)、SUP0005→EUR(3)、SUP202609120002→USD+采购员李晓峰；SUP202609120003 保持 NULL 作「空外键→关系不出现」对照。
- supplierRiskScore（Rhai）风险等级比较改 MDM 标签口径（"高"/"中"——v2 比较英文枚举永不命中）。
- 清库重灌：TRUNCATE om_* + DROP oo_*（技能清库节）→ `CONFIG_FILE=onto-server-test.toml` 重启（预热 oo_quarantine）→ onto_seed 全量。

### 6.4 验证（全绿）

- 漏斗三数：Supplier read=14/written=13/quarantined=1（SUP-BAD），其余七类零隔离。
- props 抽查：oo_contract.supplierId=1/4/3、currencyId=1/2/1；oo_supplier.settleCurrencyId=1/2/3、id 含雪花号 56051595943936+；oo_warehouse.managerId=1/3/5——全部裸值。
- 10 关系双向遍历（/object-sets/load）：settleCurrency 反向 4 供应商→3 币种（003 空外键正确不出现）、正向 CNY/USD/EUR→12 供应商；signContract 正向 SUP0001/3/4→各自合同；contractCurrency CT-002→USD；contractPaymentTerm CT-001→net60；useUom 双向（pcs→4 物料）；buyerOf 反向 SUP0001→EMP0001；managerOf 双向；supplierOf SUP0001+SUP0002→6 物料；storeIn WH-02→4 物料。
- 两跳链：EMP0001 →buyerOf→ 供应商 →signContract→ CT-2026-001 ✓；CT-002 →signContract 反向→ SUP0004 →settleCurrency 反向→ CNY ✓。
- 聚合 groupSum：中信重工 120万/华胜 76万/晨光 58万 ✓；supplierGrade SUP0001→A；supplierRiskScore SUP0002→93、SUP0005→56（中风险 20+准时率 24 扣分）✓。
- explorer UI：对象列表直接可见 **id 列**（真实 MDM 主键）；SUP0001 →「结算币种 → Currency · 反向」→ CNY(id=1) ✓。

### 6.5 新坑记录

| 坑 | 正解 |
|---|---|
| 重排 propertyMap 漏掉 lifecycle_status（required）→ Supplier 14/14 全进隔离区 | 改漏斗 propertyMap 后必须逐条核对 required 字段都有映射 |
| explorer 钻取 FK 关系返回 0 条、方向标注错（「结算币种」没标「· 反向」） | 前端页面缓存了重灌前的旧关系元数据——清库重灌后必须**强刷浏览器页面**再验证 UI |
| UI 判方向依据=当前类型在 linkType 的 A/B 端；改 A/B 端序（如 settleCurrency 改 A=Currency）后，旧缓存元数据会按旧端序走 forward，JOIN 落空 | 同上；且改 A/B 端序时注意 explorer 面包屑/角色名的展示方向随之变化 |

---

## 七、演示数据重构执行记录（2026-09-13 第三轮，v4「中间表」口径）

用户裁决：业务多对多都必须有中间表支撑，没有就不要轻易做 manyToMany；只保留一个多对多且最好是无业务语义的标签类（如供应商标签）；业务多对多增加中间表拆成两条一对多。

### 7.1 v4 口径

- **供应关系 → 中间表**：fico 新建 `cm_supply_record`（合格供应商物料目录：id/code/name/supplier_id/material_id/po_count/last_po_no/last_po_date），15 行由 cv_po_order/cv_po_line 订单履约历史聚合派生（含订单次数、最近订单号真实统计列）。本体对象类型 `SupplyRecord 供应记录`（漏斗 sync，15/15 零隔离），拆两条一对多 FK 关系：
  - `supplierSupply 供货目录`：A=Supplier → B=SupplyRecord，fk{supplierId→id, side:b}
  - `materialSupply 供货来源`：A=Material → B=SupplyRecord，fk{materialId→id, side:b}
- **全场唯一 manyToMany = supplierTag 供应商标签**：新增 Tag 对象类型（本体原生 8 个标签实例）+ 14 条 ol_edge 标签边（Edge backing 缺省）。讲点：无业务语义的标签类关系，ol_edge 内置连接表承担连接表职责。
- **撤除** coverMaterial/storeIn（业务库无对应中间表，不硬造多对多）与 supplierOf（被中间表方案取代）。物料→合同链路改走三跳：物料→供货来源→记录→供货目录·反向→供应商→签订合同→合同。
- **动作改造**：linkSupplier/unlinkSupplier → `addSupplierTag/removeSupplierTag`（建边/断边原子改在标签关系上演示）；createMaterial 去掉挂关系步骤（改名「新增物料」）。

### 7.2 验证（全绿）

- 10 条关系：9×oneToMany(FK) + 1×manyToMany(supplierTag)；ol_edge 仅剩 supplierTag ×14。
- 漏斗九类：Supplier 13/1 隔离、SupplyRecord 15/0，其余零隔离。
- 遍历：SUP0001/SUP0002 →供货目录→ 7 条记录；SR0001~3 →供货来源·反向→ MAT0001/2/4；两跳 SUP0001→记录→3 物料；三跳 MAT0009→记录→华胜→CT-2026-003；标签双向（SUP0001→战略伙伴/军工配套，TAG-green→SUP0008/SUP202609120002）；旧关系 supplierOf 已删（遍历报「关系类型未定义」）。
- UI：供应记录 15 条列表（id 列可见）；SR0001 详情关系区「供货来源 → Material · 反向 / 供货目录 → Supplier · 反向」双入口，钻取 SR0001→MAT0001 实测通过。

### 7.3 最终关系全景（10 条）

| 关系 | 端 | 基数 | backing |
|---|---|---|---|
| signContract 签订合同 | Supplier→Contract | oneToMany | fk supplierId→id (b) |
| settleCurrency 结算币种 | Currency→Supplier | oneToMany | fk settleCurrencyId→id (b) |
| buyerOf 采购对接 | Employee→Supplier | oneToMany | fk buyerId→id (b) |
| useUom 使用计量单位 | Uom→Material | oneToMany | fk baseUomId→id (b) |
| contractCurrency 计价币种 | Currency→Contract | oneToMany | fk currencyId→id (b) |
| contractPaymentTerm 付款条件 | PaymentTerm→Contract | oneToMany | fk paymentTermCode→code (b) |
| managerOf 主管仓库 | Employee→Warehouse | oneToMany | fk managerId→id (b) |
| supplierSupply 供货目录 | Supplier→SupplyRecord | oneToMany | fk supplierId→id (b) |
| materialSupply 供货来源 | Material→SupplyRecord | oneToMany | fk materialId→id (b) |
| supplierTag 供应商标签 | Supplier↔Tag | manyToMany | Edge（ol_edge 内置连接表，14 边） |

---

## 八、演示数据精简执行记录（2026-09-13 第四轮，v5 终版）

用户裁决：删除付款条件、删除供应商标签，整体精简。

### 8.1 改动

- 删 PaymentTerm：对象类型、contractPaymentTerm 关系、漏斗映射全撤；Contract 同步去掉 paymentTermCode 属性（fico 的 cm_payment_term 表与 cm_contract.payment_term_code 列不动，只是不再入本体演示）。
- 删供应商标签：Tag 类型、supplierTag 关系（v4 唯一的 manyToMany）、打标签/摘标签两动作、8 个标签实例与 14 条 ol_edge 全撤。
- 结果：**8 对象类型 / 8 条关系，全部 oneToMany FK backing；ol_edge 0 行**。五种编辑原子中 addLink/removeLink 的动作演示随标签删除而移除（createObject/modifyObject/deleteObject 仍由 新增物料/暂停合作·调整评分/删除物料 覆盖）——精简优先。

### 8.2 验证（全绿）

漏斗八类 Supplier 13/1 隔离、SupplyRecord 15/0、其余零隔离；8 关系遍历抽检（供货目录/两跳到物料/结算币种·反向/签订合同·反向/三跳到合同）全通；supplierTag 遍历报「关系类型未定义」；oo_contract 无 paymentTermCode；ol_edge count=0。

---

## 九、前端 side 支持（2026-09-13 第五轮）

用户裁决：速建不加「外键在哪端」选择（前端创建的关系恒为 A 端持键），但前端必须支持 side a/b——展示按 side 归位、编辑时把存量值放回正确的端。

### 9.1 改动（assets/onto/web/ui-native/onto/studio/，静态真源直出免构建）

| 文件 | 改动 |
|---|---|
| state.js | `LINK_BACKING_FK(sourceProperty, targetProperty, side)` 增第三参，显式产出 `side`（'a' 缺省/'b'），数据自描述 |
| canvas.js | 速建气泡创建传 `side:'a'`；提示文案补「外键落在 A 端所选属性上——若外键实际在 B 端表，请反向绘制（从持键端画向被引用端）」 |
| runtime.js | 另一条关系创建路径同传 `'a'`；`saveSimple('link')` 改为 side 感知——表单字段改名 `aProperty/bProperty`（各端一个下拉），保存时按 `d.backing.fk.side` 重组回 fk 形状（side=b 时对调），side 在线不切换 |
| inspector.js | 关系详情展示按 side 归位：`Contract·supplierId → Supplier·id（外键在 B 端）`（原先硬性 sourceProperty 归 A 端，对 side=b 关系展示颠倒——正是用户误读「搞反了/字段不存在」的根源）；编辑表单加 fk 锚点提示行，存量值按 side 放回各自端下拉 |

### 9.2 语义口径（答复「sourceProperty 是不是搞反了」）

`sourceProperty` = 持键端（实际存外键值那端）的属性，`side` 声明持键端是 A 还是 B，`targetProperty` = 对端（被引用端）匹配属性。signContract：外键列在 `cm_contract.supplier_id`（Contract=B 端）→ `{sourceProperty:"supplierId", targetProperty:"id", side:"b"}`，JOIN=contract.supplierId=supplier.id 与底层库一致。等值 JOIN 对称，故两种写法读结果相同，但持键端声明错误会在写侧（回填外键）时写错列。前端旧代码从不产 side（恒缺省 a），且展示硬归 A 端——两层都已修正。

### 9.3 验证

- node --check 四文件通过；页面内实测 `LINK_BACKING_FK("supplierId","id","b")` → `{fk:{sourceProperty:"supplierId",targetProperty:"id",side:"b"}}` ✓。
- 保存回写 round-trip：GET def → POST 原样 → GET 回读 backing 逐字一致（side 保留）✓。
- in-app browser 页签连接堆积导致 UI 级点选验证未走完（Vite 代理本身 0.09s 健康，curl 代理/直连均秒回）——刷新 studio 目验：signContract 详情应显示「Contract·supplierId → Supplier·id（外键在 B 端）」，编辑态 supplierId 在 B 端下拉、id 在 A 端下拉。

---

## 十、演示数据精简执行记录（2026-09-13 第六轮，v6 极简版：删供应记录）

用户裁决「再精简下，供货记录也删掉」——v4 引入的中间表演示（SupplyRecord 类型 + supplierSupply/materialSupply 两条关系 + fico 库 cm_supply_record 表 + 漏斗映射）整体撤除。图上只剩业务真实存在的一对多。

### 10.1 v6 终态

- **7 个对象类型**（Supplier 13/Material 10/Warehouse 3/Contract 3/Employee 8/Currency 6/Uom 14）+ PoHead（幕④单据定义，docImports 注册，非漏斗主数据）。
- **6 条关系**，全部 oneToMany FK backing（side=b，持键端为「多」端）：signContract、buyerOf、useUom、contractCurrency、settleCurrency、managerOf。
- **零多对多、零中间表、`ol_edge` 0 行**、隔离区仅 SUP-BAD 1 行；fico 库 `cm_supply_record` 已 DROP。

### 10.2 改动

| 文件 | 改动 |
|---|---|
| examples/procurement/scenario-spec.json | 删 SupplyRecord 类型、supplierSupply/materialSupply 两条 linkType、SupplyRecord 漏斗映射；view-supplier-master 成员收窄为 4（Supplier/Material/Contract/Employee，描述同步去「供货目录/标签」）；_comment 与 snapshot 升 v6 |
| examples/procurement/walkthrough.md | 基线注记升 v6；幕②八类→七类计数；幕③关系 8→6；幕④下钻主菜改为「三跳链」SUP0001→EMP0001→WH-01 与「关系环」SUP0001→CT-2026-001→CNY→8 家人民币结算供应商（环=外键列真实回路）；360 关系块台词去供货目录 |

### 10.3 清库重灌与验证（2026-09-13 实测）

- 清库：TRUNCATE om_*/oe_*/ol_edge + DELETE oo_quarantine + DROP `oo_%`（保留 oo_quarantine 壳）→ 按规格重灌：7 类 sync 全绿（Supplier 13/1 隔离），视图 2、快照 v1、单据 1。
- 六条关系对象集代数全实测：buyerOf 反向（SUP0001→8 员工）、managerOf 正向（EMP0001→3 仓库）、signContract 正向（3 合同）、contractCurrency 反向（CT-2026-001→CNY）、settleCurrency 正向（CNY→8 供应商，环闭合含 SUP0001 自身）、useUom 反向（8 物料→单位）✓。

---

## 十一、Search-Around 遍历机制分析与 backing 完善方案（v2 · 2026-09-13 第七轮）

> 触发：用户疑问「现在用的 ForeignKey 实际上跟 join 差不多」——本节基于 v6 终态最新代码重新分析
> 遍历机制、论证该直觉，并给出完善优化方案。**不动 v3 铁律**（id=cm_*.id 真主键、外键存真实外键值、
> targetProperty:"id" 属性对属性 JOIN 是既定裁决，本节在此口径内优化）。

### 11.1 遍历链路（search-around 如何消费关系定义）

```
explorer/workshop
 └ POST /object-sets/load {objectSet:{op:"searchAround", source, link, direction}}
    direction 由前端按「当前对象类型在 linkType 的 A/B 端」自动判定（§6.5 新坑：改端序须强刷页面）
  ① PEP 读侧：link_resolver.ends() 读 om_link_type → (A端,B端)；终端类型=Forward?B:A → 策略/脱敏
  ② store.load：resolve_links → link→ends + link→backing（def.rs::backing_parsed 解析原始 JSON）
     → Compiler::with_backing
  ③ compile.rs emit(SearchAround)：src_end=Forward?A:B；按 backing_of(link) 分派：
     ForeignKey → fk_search_around 四分支（11.2）
     其余（Edge/JoinTable/Intermediary）→ 一律回退 ol_edge 子查询   ← ⚠ 见问题 #2
  ④ 外层：SELECT pk,title,props FROM oo_<终端类型> WHERE pk IN (③) + 分页
```

### 11.2 FK 模式编译四分支（compile.rs::fk_search_around 实装）

`prop`=sourceProperty（side 端持键属性）、`tp`=targetProperty（对端匹配属性；None=对端 pk 列）：

| # | side vs 源端 | tp | SQL 形态 | 当前演示数据 |
|---|---|---|---|---|
| 1 | =源端 | None | `SELECT DISTINCT s.props->>'prop' FROM <源表> s WHERE s.pk IN(…)` 半连接取值 | 无 |
| 2 | =源端 | Some | `…FROM <终端表> t JOIN <源表> s ON t.props->>'tp' = s.props->>'prop' WHERE s.pk IN(…)` 两表 JOIN | 无 |
| 3 | ≠源端 | Some | #2 对称形（`t.props->>'prop' = s.props->>'tp'`） | **全部 6 条**（side=b + targetProperty:"id"） |
| 4 | ≠源端 | None | `SELECT DISTINCT t.pk FROM <终端表> t WHERE t.props->>'prop' IN(…)` | 无 |

实例（settleCurrency，A=Currency 一端/B=Supplier 多端，正向）：
`SELECT DISTINCT t.pk FROM oo_supplier t JOIN oo_currency s ON t.props->>'settleCurrencyId' = s.props->>'id' WHERE s.pk IN ('CNY')`。

### 11.3 「ForeignKey 就是 join」——论证与定位

- **查询时刻四种 backing 全部归结为 join/半连接**，FK 没有指针跳转；Palantir 官方同样把 link type
  类比为"两张数据集的 JOIN"。**该直觉成立，且是正确设计而非缺陷**。
- 模式的真正区分维度是**映射数据的物理布局**：FK=摊在多端行自己的外键列（漏斗随主数据维护）、
  JoinTable=独立键对表、Edge=平台统一边表（v6 已清空）、Intermediary=中间对象的行（可带关系属性）。
  选型三角 = 写时维护成本 vs 读代价 vs 关系属性表达力。
- 因此 FK 的短板不在「像 join」，而在 **join 的物理支撑缺失**（#1 索引）与**其余模式的空洞**（#2）。

### 11.4 问题清单（逐项读码+实测核实）

| # | 级别 | 问题 | 证据 |
|---|---|---|---|
| 1 | 🔴 | **FK join 零索引**：oo_* 仅 pkey+title 两个索引；`props->>'x'` 文本抽取全表 hash join；`is_indexed` 只管搜索索引不覆盖 FK 键 | pg_indexes 实查；万级对象单次遍历 O(N) |
| 2 | 🟡 | **JoinTable/Intermediary 双空洞**：backing_parsed 只认 `fk`/`kind`（页面口径 `{"joinTable":…}` 静默变 Edge）；编译占位回退 ol_edge（v6 已 0 行）→ **声明即静默 0 结果** | def.rs 355-378、compile.rs 134-148 |
| 3 | 🟡 | **validate 无跨端校验**：sourceProperty 是否真在 side 端类型、targetProperty 是否在对端类型、FK+oneToMany 是否 side=多端，写错无警告 | def.rs validate 仅查标识符合法性 |
| 4 | 🟡 | legacy `GET /objects/{t}/{pk}/links/{l}` 硬编码 Forward，源在 B 端即错 | object_handlers.rs:239 |
| 5 | 🟢 | 文本等值比较类型约定（'01'≠'1'）——MDM 数值 id 无前导零，实际无害，需文档约定 | 分支 2/3 SQL |
| 6 | 🟢 | Palantir 元数据 parity 尾巴：visibility/plural display name/type classes/编辑治理约束 | v1 对标表 P1/P2 项 |

### 11.5 完善优化方案

**P0-A：FK join 键索引自动维护（核心，直接回应「就是 join」）**
- link type save / 服务启动时枚举全部 FK backing 关系，对**两端键属性**幂等建表达式索引：
  `CREATE INDEX IF NOT EXISTS idx_oo_<type>_<prop> ON oo_<type> ((props->>'<prop>'))`（btree）。
- 落点：`cmx-onto-store-pg`（新 ensure_link_key_indexes，挂 DDL 例程 + save_link_type 钩子）；
  删关系可选清索引。效果：反向遍历与 JOIN 内表侧从全表扫变索引探测；`EXPLAIN ANALYZE` 前后对比验收。

**P0-B：JoinTable / Intermediary 补全（决策点：补实现 or 明确拒绝）**
- 补法则：backing_parsed 增 `{"joinTable":…}`/`{"intermediary":…}` 页面口径解析；compile.rs 真编译
  （JoinTable：`SELECT DISTINCT j.<对端列> FROM <table> j WHERE j.<源端列> IN(…)`；
  Intermediary：经 `oo_<中间类型>` 两属性两跳）；validate 三字段必填合法标识符。
- 简则（若暂不做）：save 时对这两种 backing 明确报「暂不支持」，运行时不再静默回退空 ol_edge。
- **默认建议**：简则先行（v6 极简口径下暂无 M2M 演示诉求），补全排在 P1。

**P0-C：建模跨端校验**
- save_link_type 预加载两端对象类型（handler 层 IO，model 保持零依赖）：sourceProperty ∈ side 端
  属性列表、targetProperty ∈ 对端属性列表（留空=对端 pk 合法）；
- 方向规则：FK backing ⇒ `(oneToMany ∧ side=B) ∨ (manyToOne ∧ side=A) ∨ oneToOne`。

**P0-D：legacy GET 路由方向自判**——源类型 ≠ A 端自动 Reverse（或干脆标记 deprecated 指 object-sets）。

**P1：体验与治理**（沿 v1 方案 P1/P2）：visibility、active 态编辑约束、explorer 关系块 **backing 徽标**
（FK/边表/连接表/中间对象——把「关系怎么落地」变成演示可见点）、cmx-onto-toolkit 补「backing 选型」章节。

**P2**：type classes、连接表唯一注册（一表只背一关系）。

### 11.6 验证清单与影响面

- [ ] P0-A：构造万级行 EXPLAIN ANALYZE 前后对比；6 关系×正反向遍历回归
- [ ] P0-B：按所选路线验证（补全→临时关系实测两模式；简则→save 报错文案）
- [ ] P0-C：sourceProperty 写不存在属性 → save 被拒且报缺失端
- [ ] P0-D：B 端对象走 legacy GET 命中
- 影响面：cmx-onto-model/def.rs、cmx-onto-store-pg/{compile,ddl}.rs、cmx-onto-app/handlers.rs、
  技能文档；无 API 破坏（backing 原样透传），无下游 path 引用。

### 11.7 补记：ol_edge vs FK join 读性能实测（十万行级，2026-09-13）

回答「走 ol_edge 性能最高啊」——**第一梯队是事实，但不是回退理由**：

| 场景（十万行） | 计划形态 | 实测 |
|---|---|---|
| ol_edge 正向遍历（统计信息新鲜） | idx_ol_edge_fwd (link,a_pk) 复合索引探测 | **0.083 ms** |
| ol_edge 同查询（统计信息陈旧，选错 rev 索引） | 按 link 探测后过滤 99,996 行 | 32.9 ms（差 400 倍——ol_edge 也不是自动就快） |
| FK 属性对属性 JOIN（无表达式索引，分支 3） | oo_supplier 全表 Seq Scan + Hash Join | 65.6 ms |
| 同上 + P0-A 表达式索引 | Bitmap Index Scan + Nested Loop | **19.2 ms**（键选择性越高越接近索引探测；典型低扇出外键为亚毫秒级） |

结论：① ol_edge 窄表+双复合索引，读确实是第一梯队；② FK 模式补 P0-A 索引后进同一量级，
差的是常数（jsonb 表达式求值/索引体积），选择性高的外键同样亚毫秒；③ **不回退的理由不在读性能，
在维护语义**——Edge 是派生的第二真源，边须单独维护且主数据变更不跟随（v3→v6 六轮重构正是为了
消灭手填边漂移）；Palantir 同样无物化边表，走"数据派生+重索引"路线。**定论：FK（真源）+ 索引
（P0-A）为主，ol_edge 留给原生边型关系（标签/手绘/运行时动作建边）**。
