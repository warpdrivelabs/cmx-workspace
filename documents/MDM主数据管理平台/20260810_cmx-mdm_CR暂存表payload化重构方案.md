# CR 暂存表 payload 化重构方案（V3.1 → V3.2）

> **文档性质**：设计变更方案（对 V3.1 §13.4 / §14.1 的 `cv_mdm_apply` 头表建模重构）
> **日期**：2026-08-10
> **状态**：✅ 已采纳并实现（2026-08-13 代码核查，M2.5 payload 化已落地）｜ 详见 [完成度报告](./20260813_cmx-mdm_完成度总结与后续规划.md)
> **前置文档**：`20260804_cmx-mdm_企业主数据管理平台设计方案V3_1.html`、`20260805_cmx-mdm_CR单据走标准保存链路迁移方案.md`
> **影响范围**：cmx-mdm-store-pg（cr_service / doc_accessor）、cmx-mdm-model（activation）、cmx-doc-store-pg（saver 校验）、MDM DOC 元数据定义、前端 cr-form.js

---

## 一、问题陈述

### 1.1 V3.1 当前形态

`cv_mdm_apply`（CR 头表）当前是**共享宽表 + 部分逐列展开**模式：

```
cv_mdm_apply (1 张表)
├─ 骨架列：doc_type / cr_type / target_dict_code / target_record_id / source_cr_id / effective_date / doc_status
├─ ★ 供应商业务字段逐列展开：name(REQUIRED) / tax_no / credit_code / short_name
├─ ext_attrs JSONB（扩展）
└─ field_deltas JSONB（变更 diff）
```

V3.1 §13.4 明确写道："主体关键字段逐列展开成独立列（享受 DOC 列级校验：必填/格式/唯一约束）"。

### 1.2 在 100+ 主数据场景下崩溃

CMX 定位是覆盖财务/客商/物料/组织四大域 100+ 主数据的平台。当前"逐列展开"决策只对单一主数据成立，多主数据下三死法：

| 路径 | 后果 |
|------|------|
| 全部逐列展开 | 100 主数据 × ~10 关键字段 ≈ 1000 列宽表，90% NULL，每加一种主数据要 `ALTER TABLE ADD COLUMN` |
| 只展开供应商的，其他塞 JSONB | 不公平——物料/科目凭什么不能享受列校验？且语义混乱 |
| 按域分多张 cv_*_apply | 表数膨胀（等于把暂存区做成了激活区的镜像） |

**根因**：把"变更请求的载体表"和"某种主数据的业务字段"耦合在了一起。

### 1.3 需要解决的核心矛盾

| 矛盾 | 方向 |
|------|------|
| 100+ 主数据字段膨胀 | 暂存表不能随主数据种类膨胀 → 业务字段进 JSONB |
| 列表页搜索体验 | 不能全 JSONB → 高频搜索字段保留物理列 |
| payload 不参与搜索 | 用户决策：暂存区不做业务字段搜索，业务查询走激活区 cm_* |
| 列级校验能力 | DOC 校验器基于元数据 schema，不依赖物理列 → 可扩展支持 payload 内字段校验 |

---

## 二、设计原则

1. **暂存区与激活区职责分离**：`cv_*`（暂存）只管流转（录入/审批/激活搬运），不做业务字段查询；`cm_*`（激活）才管消费（物理列 + 索引）。这是 SAP MDG Staging/Active 模型的直接落地，V3.1 已确立，本方案延续。

2. **payload 不参与 WHERE 搜索**：经评审决策，暂存区不做业务字段搜索。列表页搜索能力 = 骨架列（doc_status/time）+ 公共搜索列（subject_name/subject_code），到此为止。业务字段查询（"查税号=911 的供应商"）发生在激活区 `cm_supplier`，不在暂存区。

3. **元数据驱动校验**：DOC 的 `validate_changeset`（saver.rs:1003）基于 `layer.spec`（元数据 schema）校验，不依赖物理列约束。扩展校验器支持"按 DCT 字典定义校验 payload 内字段"，保留列级校验能力（required/类型/长度）。

4. **路由键吸收种类膨胀**：头表用 `doc_type`、行表用 `line_type` 区分主数据种类，新增主数据零 DDL，只加元数据 + 激活映射配置。

5. **双重防线不变**：暂存区（cv_*）元数据驱动前置校验（用户体验，提前报错）；激活区（cm_*）物理 NOT NULL/UNIQUE 约束兜底（数据正确性最后防线）。

---

## 三、目标表结构

### 3.1 头表 cv_mdm_apply（重构）

```sql
CREATE TABLE cv_mdm_apply (
  -- ① 骨架列（过滤/排序/连接，物理列）
  id                BIGINT PRIMARY KEY,
  doc_no            VARCHAR(64) UNIQUE NOT NULL,    -- cmx-code 铸号
  doc_type          VARCHAR(64) NOT NULL,           -- mdm_supplier_apply / mdm_material_apply ...
  doc_type_id       BIGINT NOT NULL,                -- DOC 单据类型 ID（base fieldSet nullable:false）
  target_dict_code  VARCHAR(64) NOT NULL,           -- 目标主数据字典(supplier/material...)
  target_record_id  BIGINT,                         -- 变更时指向 cm_*.id；新建时空
  source_cr_id      BIGINT,                         -- 克隆重提交留痕
  cr_type           VARCHAR(16) NOT NULL,           -- create/update/merge/block/flag_delete
  effective_date    DATE,                           -- 未来生效日
  doc_status        VARCHAR(16) NOT NULL DEFAULT 'draft',  -- 状态机：draft/approving/approved/activated/rejected
  business_status   VARCHAR(16) DEFAULT 'open',     -- DOC 业务状态
  entity_id         BIGINT NOT NULL,                -- DOC 核算主体（base fieldSet nullable:false）
  doc_date          DATE NOT NULL,                  -- DOC 单据日期（base fieldSet nullable:false）
  attach_count      INT DEFAULT 0,
  remark            VARCHAR(500),
  line_no           INT DEFAULT 0,                  -- DOC 结构列：头表固定 0（documentIdentityFields 要求存在）

  -- ② 公共搜索列（横切关注点，不随主数据种类膨胀）
  --    语义：这条 CR 改的主数据"叫什么名/什么编码"，跨所有主数据通用
  subject_name      VARCHAR(200),                   -- 主体名称（供应商名/物料名/科目名...）
  subject_code      VARCHAR(64),                    -- 主体编码（列表跳转/展示用）

  -- ③ 业务字段 payload（纯存储 + 激活搬运，不参与 WHERE）
  payload           JSONB NOT NULL DEFAULT '{}',    -- {tax_no, credit_code, short_name, ...} 按主数据种类而异
  field_deltas      JSONB,                          -- 变更 diff {field:{old,new}}；create 类为空

  -- ④ 审计列（DOC 标准）
  create_by         BIGINT NOT NULL DEFAULT 0,
  create_time       TIMESTAMPTZ NOT NULL DEFAULT now(),
  update_by         BIGINT NOT NULL DEFAULT 0,
  update_time       TIMESTAMPTZ NOT NULL DEFAULT now(),
  delete_flag       SMALLINT NOT NULL DEFAULT 0
);

-- 索引：覆盖列表页全部查询路径（CR 表万级，不需要表达式索引）
CREATE INDEX ix_cv_apply_status_time ON cv_mdm_apply(doc_status, create_time DESC);
CREATE INDEX ix_cv_apply_subject     ON cv_mdm_apply(subject_name);
CREATE INDEX ix_cv_apply_dict        ON cv_mdm_apply(target_dict_code, doc_status);
-- 无 payload 表达式索引：payload 不参与搜索（评审决策）
```

**删除的字段**：`name`、`tax_no`、`credit_code`、`short_name`、`ext_attrs` 五个逐列字段。
- `name` → 提升为公共搜索列 `subject_name`（语义不变：列表展示主体名）
- `tax_no`/`credit_code`/`short_name` → 并入 `payload` JSONB
- `ext_attrs` → 并入 `payload` JSONB（不再区分"关键"与"扩展"）

### 3.2 行表 cv_mdm_apply_line（基本不变）

行表本就是 payload 模式（`line_payload` JSONB），改动极小：

```sql
CREATE TABLE cv_mdm_apply_line (
  -- ① 骨架列（连接 + 路由 + 排序）
  id              BIGINT PRIMARY KEY,
  upper_id        BIGINT NOT NULL,                 -- 挂 cv_mdm_apply.id（核心连接键）
  line_no         INT NOT NULL,                    -- 行内排序
  line_type       VARCHAR(64) NOT NULL,            -- 路由键：bank_account/qualification/address ...
  line_action     VARCHAR(16) NOT NULL DEFAULT 'insert',  -- insert/update/delete（明细级操作）

  -- ② payload（明细业务字段，本就是 JSONB）
  line_payload    JSONB NOT NULL DEFAULT '{}',     -- {account_no, bank_name, ...} 按 line_type 而异
  line_target_id  BIGINT,                          -- update/delete 时指向 cm_*.id（明细定位）
  line_deltas     JSONB,                           -- update 明细的 {field:{old,new}}

  -- ③ 审计
  create_by       BIGINT NOT NULL DEFAULT 0,
  create_time     TIMESTAMPTZ NOT NULL DEFAULT now(),
  delete_flag     SMALLINT NOT NULL DEFAULT 0
);

-- 索引：只有这一个，覆盖"按头拉行"
CREATE INDEX ix_cv_apply_line_upper ON cv_mdm_apply_line(upper_id, line_no);
```

**新增字段**（对比 V3.1）：`line_target_id`、`line_deltas`（支持明细级 update/delete 操作的定位与 diff）。其余不变。

### 3.3 为什么行表不需要"公共搜索列"和表达式索引

头表和行表访问模式根本不同：

| 维度 | 头表 cv_mdm_apply | 行表 cv_mdm_apply_line |
|------|-------------------|------------------------|
| 过滤方式 | 跨 CR 全表 WHERE（列表页：按 status/time/subject_name） | 按 upper_id 拉一个 CR 的所有行 |
| 会跨 CR 搜字段吗 | 会（列表页搜主体名） | **不会**（没人跨 CR 搜"所有 account_no=工行的行"） |
| 路由键 | doc_type | line_type |
| 索引策略 | btree(骨架列) + btree(subject_name) | 只 btree(upper_id, line_no) |

行表永远"先定位头再拉行"，`WHERE upper_id=$1` 先把范围缩到一个 CR 的几十行，在几十行里 JSONB 解析是无感的。

### 3.4 payload 内容契约（按主数据种类）

payload 的 key 来自该主数据 DCT 字典定义的 fields（去掉已提升为公共列的 `name`/`code`）。以供应商为例：

```json
// doc_type=mdm_supplier_apply 的 payload
{
  "tax_no": "911...",
  "credit_code": "91...",
  "short_name": "A公司简称",
  "register_capital": 10000000,
  "legal_person": "张三"
}
```

```json
// doc_type=mdm_material_apply 的 payload（未来扩展）
{
  "material_spec": "Φ20×1.5",
  "unit": "KG",
  "weight": 1.5,
  "category_code": "RAW"
}
```

**新增主数据 = 定义 DCT fields + 激活映射配置，零 DDL 改 cv_* 表**。

### 3.5 三层分工速记

| 层 | 头表 | 行表 |
|----|------|------|
| 骨架 | doc_status/time/doc_no/target_dict_code | upper_id/line_no/line_type |
| 搜索 | subject_name/subject_code（物理列） | 只按 upper_id 拉（无搜索列） |
| 业务数据 | payload JSONB | line_payload JSONB |
| 变更 | field_deltas JSONB | line_deltas JSONB + line_target_id |
| 路由 | doc_type | line_type |

---

## 四、校验机制：步骤条预校验 + 查重（替代 doc/save 钩子）

> **⚠️ 本节方案已变更（第 4 轮用户决策）**：原 §4.2 的「doc_save 模块校验钩子」方案**不使用**——`/api/doc/save` 是通用接口，不应耦合 MDM 业务校验。改为前端**步骤条预校验**模式：步骤1填关键信息→调 MDM 查重接口→通过后进入步骤2完整填写。下面的 §4.2 钩子设计仅作历史记录保留，标注「不使用」。

### 4.1 现状与挂钩点分析（评审 B1 历史）

**DOC 校验器现状**（saver.rs:1003 `validate_changeset`）：基于 `layer.spec`（元数据 schema）校验，遍历 `spec.order` 对元数据定义的 NOT NULL 列检查（validation/mod.rs:322-343）。关键事实：校验器遍历的是元数据 schema 的列，不是物理表列——这个能力来自元数据，不依赖物理列。

**保存调用链现状**（第 1 轮评审 B1 指出的核心断点）：

```
前端 saveDocData → POST /api/doc/save
  → cmx-doc-api::handlers::doc_save（handlers.rs:689）
    → resolve_doc_meta（按 moduleCode 定位元数据）
    → run_validation（handlers.rs:857）         ← 仅当 meta.validation_rules 非空
        → cmx_doc_store_pg::validate（rule.rs） ← formula 表达式引擎
    → DocSaver::save（saver.rs:143）
        → validate_changeset（saver.rs:1003）   ← 元数据驱动骨架列校验
        → apply_merge（落库）
```

**评审 B1 的发现**：cr_service 不在 `/api/doc/save` 链路上。且 formula 引擎（formula.rs:115 `json_to_fvalue` 对象→Null，:419 `Node::Ident` 只做顶层 key 查找）不支持 payload 内字段访问。这排除了「validationRules 模拟」路径。

### 4.2 ~~doc_save 模块校验钩子~~ 【不使用 · 第 4 轮决策废弃】

> ⚠️ **此方案已废弃**。原因：`/api/doc/save` 是通用单据保存接口，不应耦合 MDM 业务校验逻辑。强行挂钩违反通用接口纯净性原则，且会让其他模块（会计凭证等）的保存路径增加无谓的模块路由开销。

~~原方案：在 doc_save handler 增加模块校验钩子，按 module=="mdm" 路由到 MdmPayloadValidator~~。

**废弃后的影响**：以下任务项从 §7 任务分解中移除：
- ~~T3：模块校验钩子（module_validation.rs）~~
- ~~T4：MdmPayloadValidator~~

### 4.3 【采用】步骤条预校验 + 查重（第 4 轮新设计）

**交互流程**（用户决策：2 步 + 查重一并做）：

```
┌─────────────────────────────────────────────┐
│ 步骤 1：关键信息录入                          │
│   填写：供应商名称、税号、统一信用代码 ...     │
│   [下一步] → 调 POST /api/mdm/check-key     │
│              ├─ 必填校验（关键字段非空）      │
│              └─ 查重（调 find_candidates）    │
│   ├─ 有重复 → 弹框提示"已存在相同记录"，      │
│   │           阻断，不允许进入步骤2           │
│   └─ 无重复 → 进入步骤 2                     │
├─────────────────────────────────────────────┤
│ 步骤 2：完整信息录入                          │
│   步骤 1 的关键字段只读（不可编辑）            │
│   填写其余业务字段（银行账户、资质、地址...）   │
│   [保存] → 走标准 /api/doc/save              │
└─────────────────────────────────────────────┘
```

**查重交互**（第 6 轮用户决策简化）：有重复时**直接弹框阻断，不允许继续**——不再提供"继续新建/转为变更CR"等绕过选项。用户若要修改已有记录，应走独立的"变更"流程（update 类 CR，通过列表页入口发起）。

**查重接口**（复用底层函数，非接口）：`mdm_find_duplicates`（handlers.rs:279）的 `FindDupBody.record_id` 是必填且必须命中已发布记录，新建场景无 recordId 可传，**不能直接复用接口**。改为复用其底层函数 `match_algo::find_candidates`（match_algo.rs:157）。

**关键信息校验接口**（新增）：

```
POST /api/mdm/check-key
Body: { dictCode, keyValue }          // keyValue = { name:"A公司", tax_no:"911..." }
Response 200: { exists: false }                          // 无重复，可继续
Response 200: { exists: true, id: 8001, code: "SUP001", message: "已存在相同记录：SUP001（id=8001）" }  // 有重复，前端弹框阻断
Response 422: { violations: [...] }                      // 关键字段必填校验失败
```

**实现要点**：
1. `check-key` 先做关键字段必填校验（对照 DCT fields 的 nullable==false），失败返 422 + violations。
2. 通过必填校验后，**直接调用底层函数 `match_algo::find_candidates`**（match_algo.rs:157），不调 mdm_find_duplicates 接口。具体：
   - 用 keyValue 构造**虚拟 target**：`MatchRecord { id: 0, fields: keyValue }`（id=0 表示未落库的新记录）
   - `load_published`（store 层）拉该字典的全量已发布记录作为候选集
   - 调 `find_candidates(target, all, specs, cluster_keys)` 比对，命中即 exists:true
3. **铸号无关**：步骤1不铸号，铸号仍在步骤2保存时由 `/api/doc/save` → cmx-code 完成（现有机制不变）。

> **为什么不直接复用 mdm_find_duplicates 接口**（第 5 轮 R1）：该接口的 `FindDupBody.record_id: i64` 必填，且 handlers.rs:306-310 从已发布记录 find target，找不到报错。新建场景激活区 `cm_*` 无此记录。故只能复用底层 `find_candidates` 函数（它接受任意 MatchRecord 作 target，包括虚拟的 id=0 记录）。

**步骤1关键字段在步骤2只读**：前端步骤条维护一个 `lockedFields` 集合（步骤1填过的字段名），步骤2渲染时对这些字段加 `disabled`/`readonly`。

### 4.4 校验防线（修订后，双重）

```
步骤1：POST /api/mdm/check-key（新增）
  ├─ 关键字段必填校验（对照 DCT fields）
  └─ 查重（调 find_duplicates 核心逻辑）

步骤2：POST /api/doc/save（不变）
  ├─ run_validation（validationRules，MDM 暂不用）
  ├─ DocSaver::save → validate_changeset（骨架列 NOT NULL + payload 整块存在）
  └─ 激活器激活时兜底：cm_* 物理 NOT NULL/UNIQUE 约束
```

**双重防线**：
1. MDM check-key（关键信息必填 + 查重，用户体验前置）
2. DOC validate_changeset + cm_* 物理约束（数据正确性）

---

## 五、激活器适配

### 5.1 当前激活器头表搬运逻辑（activation.rs）

```rust
// plan_create：从 cr_head 顶层字段取值
pub fn plan_create(cfg, cr_head, new_code) -> ActivationPlan {
    for (src_field, tgt_col) in &cfg.header_mapping {
        if let Some(val) = cr_head.get(src_field) {   // ← 从顶层取
            header_row.insert(tgt_col, val.clone());
        }
    }
}

// plan_update：从 field_deltas 的 new 取值
pub fn plan_update(cfg, _cr_head, field_deltas, current_version) -> ActivationPlan {
    for (src_field, tgt_col) in &cfg.header_mapping {
        if let Some(delta) = deltas.get(src_field)    // ← 从 deltas 顶层取
            && let Some(new_val) = delta.get("new") {
            header_row.insert(tgt_col, new_val.clone());
        }
    }
}
```

### 5.2 payload 化后的适配

**create 分支**：取值逻辑改为"先查 payload，再查 cr_head 顶层"的**通用回退**（不硬编码字段名，回应评审 S4/I2）：

```rust
pub fn plan_create(cfg, cr_head, new_code) -> ActivationPlan {
    let payload_obj = cr_head.get("payload").and_then(|v| v.as_object());
    for (src_field, tgt_col) in &cfg.header_mapping {
        // 通用回退：先查 payload 内，再查 cr_head 顶层（公共列 subject_name/subject_code 在顶层）
        // payload 契约禁止包含 subject_name/subject_code（见 §3.4），故无歧义
        let val = payload_obj
            .and_then(|p| p.get(src_field))
            .or_else(|| cr_head.get(src_field));
        if let Some(tgt) = tgt_col.as_str() && let Some(v) = val {
            header_row.insert(tgt.to_string(), v.clone());
        }
    }
    header_row.insert("code".into(), Value::String(new_code.to_string()));
    header_row.insert("lifecycle_status".into(), Value::String("published".to_string()));
    header_row.insert("published_version".into(), Value::Number(1.into()));
    ActivationPlan { header_row, line_rows: vec![] }
}
```

**为什么不硬编码字段名**：`payload_obj.get(src).or_else(|| cr_head.get(src))` 让 header_mapping 的 key 自由指向 payload 内字段或顶层公共列，未来增加公共列无需改激活器代码。payload 契约（§3.4）禁止 payload 内包含 `subject_name`/`subject_code` 同名字段，避免回退歧义。

**update 分支**：`field_deltas` 结构不变（仍是 `{field:{old,new}}`），field 名指 payload 内字段或公共列。`plan_update` 同样取 deltas 里该字段的 `new` 值，逻辑无需大改。

### 5.3 subject_name/subject_code 的填充责任（回应评审 I3 / 第 4 轮修订）

**问题**：谁负责填 subject_name/subject_code？不同主数据的"主体名"语义不同（供应商=公司名、物料=物料名），对应 payload/输入框不同。

**决策（第 4 轮修订：前端步骤条填充）**：步骤条改造后，步骤1「关键信息」必含主体名（供应商名/物料名）。前端 cr-form.js 在步骤1收集关键信息时，按激活映射配置的 `subjectNameField` 从关键字段取值，构造 payload 时一并填 `subject_name`。无需后端校验器回填。

在 `mdm_activation` 配置里增加两个字段（声明该 doc_type 的主体名/编码从哪来）：

```json
{
  "activationCode": "supplier_apply",
  "subjectNameField": "name",   // 前端：subject_name = 关键信息中的 name 字段值
  "subjectCodeField": null      // 供应商 code 由 codeRule 铸号，无前端字段
}
```

**填充时机**：前端 cr-form.js 步骤1「下一步」通过 check-key 后，进入步骤2时构造 payload，同时按 subjectNameField 从关键信息提取值填入 `subject_name`。保存时 subject_name 随 payload 一起提交到 /api/doc/save，列表页随时可展示。

> 注：第 2 轮 N1 的 `mdm_activation` 加 `subject_name_field/subject_code_field` DDL 仍需执行（前端读此配置决定从哪个关键信息字段取主体名），只是消费方从"后端校验器"改为"前端步骤条"。

### 5.4 激活映射配置示例（payload 适配）

```json
{
  "activationCode": "supplier_apply",
  "sourceDocType": "mdm_supplier_apply",
  "crType": "create",
  "targetDict": "supplier",
  "targetTable": "cm_supplier",
  "subjectNameField": "name",
  "subjectCodeField": null,
  "headerMapping": {
    "name": "name",            // payload.name（或顶层 subject_name）→ cm_supplier.name
    "code": "code",            // 若 subject_code 非空则取顶层，否则 codeRule 铸号覆盖
    "tax_no": "tax_no",        // payload 字段 → cm_supplier.tax_no
    "credit_code": "credit_code"
  },
  "lineMappings": [
    {
      "lineType": "bank_account",
      "targetTable": "cm_bank_account",
      "parentIdField": "supplier_id",
      "fields": { "account_no": "account_no", "bank_name": "bank_name" }
    }
  ],
  "codeRuleCode": "MDM_GYS"
}
```

**映射源字段的两类**（激活器通用回退，§5.2）：
1. **payload 字段**（`tax_no`/`credit_code`/`name`）：从 cr_head.payload 取（优先）
2. **公共搜索列**（`subject_name`/`subject_code`）：从 cr_head 顶层取（回退）

由于 subject_name 由前端步骤条按 subjectNameField 从关键信息派生（§5.3），header_mapping 里 `name` 映射源既可能命中 payload.name 也可能命中顶层 subject_name（值相同），无歧义。

### 5.5 activation-mapper.js 适配（回应评审 B4 / 第 2 轮 N3 统一）

**问题**：activation-mapper.js:51 通过 `/api/doc/meta` 读 cv_mdm_apply 的 columns 生成映射配置器的源字段下拉。payload 化后业务字段只剩 `payload`（JSONB 整块），下拉无法选到 payload 内字段。

**解决（第 2 轮 N3 修订：统一裸名 key 格式）**：activation-mapper.js 识别到 payload 是 JSONB 后，**递归展开目标 DCT 字典定义的 fields 作为可选源字段**（与 `/api/dct/meta` 联动，该页已有此调用）。下拉选项呈现为：
- 公共列：`subject_name`、`subject_code`
- payload 字段（从 DCT fields 动态生成，**显示时加 `payload.` 前缀供用户识别，存盘时 strip 前缀用裸名**）：`payload.name`、`payload.tax_no`、`payload.credit_code` ...

**header_mapping 的 key 统一用裸名**（如 `tax_no`），激活器 plan_create/plan_update 用 §5.2 的通用回退取值。下拉 UI 的 `payload.tax_no` 仅作显示，落库 header_mapping 时存 `tax_no`。这样 §5.2/§5.4/§5.5 三处 key 格式完全一致，无需点路径解析。

### 5.6 update 类 CR 的 field_deltas key 对齐（回应第 2 轮 N5）

**问题**：payload 化后，update 类 CR 的 field_deltas key 用裸名还是点路径？cr-form.js:197 当前用裸名（`deltas[f]`，f 来自 BIZ_FIELDS）。

**决策（配合 §5.5 裸名方案）**：field_deltas 的 key **统一用裸名**（与 header_mapping key 同源），不带 `payload.` 前缀。plan_update 从 `deltas.get(裸名)` 取 new 值。

前端 cr-form.js 的 deltas 生成逻辑改为：
```javascript
// cr-form.js（BIZ_FIELDS 改为 PAYLOAD_FIELDS，对应 payload 内字段）
const PAYLOAD_FIELDS = ['tax_no', 'credit_code', 'short_name']  // name 已提升为 subject_name（公共列）

function buildUpdateHead() {
  const deltas = {}
  // payload 字段 diff（裸名 key）
  for (const f of PAYLOAD_FIELDS) if ((cur[f] || '') !== (o[f] || '')) deltas[f] = { old: o[f] ?? '', new: cur[f] ?? '' }
  // subject_name diff（公共列，若改了主体名）
  if ((cur.name || '') !== (o.name || '')) deltas['subject_name'] = { old: o.name, new: cur.name }
  return { field_deltas: deltas }
}
```

**plan_update 对齐**：header_mapping key 是裸名（`tax_no`/`subject_name`），deltas key 也是裸名，`deltas.get(src_field)` 直接命中。无需点路径解析。

---

## 六、迁移影响清单

### 6.1 后端（cmx-container）

| 文件 | 改动 |
|------|------|
| `cmx-mdm-store-pg/src/cr_service.rs` | (1) `list_cr` SELECT 去掉 `name`，改 `subject_name`（见 §6.6）；(2) `clone_revise_inner` 的头表 INSERT...SELECT 重写为 26 列（见 §6.7 具体新 SQL）；(3) 行表 clone INSERT 补 `line_target_id, line_deltas` 两列（见 §6.8） |
| `cmx-mdm-store-pg/src/doc_accessor.rs` | (1) `load_cr_head` SELECT 改为新列（含 payload/subject_name/subject_code）；(2) `parse_jsonb_field` 调用列表**必须**增加 `payload`（否则激活器拿到字符串，静默丢字段——评审 B5）；(3) `load_cr_lines` SELECT 补 `line_target_id, line_deltas`（否则行表 clone 无源数据） |
| `cmx-mdm-model/src/activation.rs` | `plan_create`/`plan_update` 取值改为 payload 内查找 + 顶层公共列通用回退（见 §5.2）；增加点路径 `payload.xxx` 解析（见 §5.5） |
| `cmx-mdm-store-pg/src/activation_store.rs` | (1) 反序列化 ActivationConfig 增加 `subject_name_field`/`subject_code_field`；(2) **find_by_doc_type（:23）和 list（:74）的 SELECT 必须补这两列**（第 2 轮 N1，否则加字段也取不到值） |
| `cmx-mdm-api/src/handlers.rs` | 新增 `mdm_check_key` handler（§4.3），复用 match_algo::find_candidates；merge 相关 handlers 去 supplier 硬编码（§11A） |
| ~~`cmx-doc-api/src/handlers.rs`~~ | ~~doc_save 增加模块校验钩子~~ **【不使用，第 4 轮废弃】** |
| ~~`cmx-doc-api/src/module_validation.rs`~~ | ~~模块校验器注册表~~ **【不使用，第 4 轮废弃】** |
| ~~`MdmPayloadValidator`~~ | ~~校验 payload + 回填 subject_name~~ **【不使用，第 4 轮废弃，改前端步骤条 + check-key 接口】** |
| DDL 迁移（新 SQL 文件） | (1) `ALTER TABLE cv_mdm_apply ADD COLUMN payload JSONB NOT NULL DEFAULT '{}', ADD COLUMN subject_name VARCHAR(200), ADD COLUMN subject_code VARCHAR(64)`；(2) `ALTER TABLE cv_mdm_apply_line ADD COLUMN line_target_id BIGINT, ADD COLUMN line_deltas JSONB`；(3) **`ALTER TABLE mdm_activation ADD COLUMN subject_name_field VARCHAR(64), ADD COLUMN subject_code_field VARCHAR(64)`**（第 2 轮 N1）。然后数据搬迁，最后 DROP 旧列（见 §6.5） |
| `cmx-mdm-store-pg/src/activation_store.rs` | **`find_by_doc_type`（:23）和 list（:74）的 SELECT 补 `subject_name_field, subject_code_field` 两列**（第 2 轮 N1：当前 SELECT 只取 8 列，加了 DDL 列后必须补查询，否则反序列化取不到值） |

### 6.2 元数据定义

| 文件 | 改动 |
|------|------|
| `data/meta/definitions/basic/dataplatform/mdm/dataplatform_doc_meta_v1.json` | `cv_mdm_apply` 删除 name/tax_no/credit_code/short_name/ext_attrs 五个字段定义；新增 payload/subject_name/subject_code。**payload 的 dataType 必须写 `"JSONB"`**（评审 I1：saver.rs:622-632 的 jsonb_col_mask 按 FieldType::Json 判定加 `$n::jsonb` cast，meta.rs:719 `"JSONB"→FieldType::Json`，误写 VARCHAR 会触发 ON CONFLICT 时的 text/jsonb 类型推断 bug）|

payload 字段定义片段（必须如此）：
```json
{ "name": "payload", "dataType": "JSONB", "nullable": false, "defaultValue": "{}" }
```

### 6.3 前端

| 文件 | 改动 |
|------|------|
| `cr-form.js` | (1) 改 2 步步骤条：步骤1关键信息→调 /api/mdm/check-key 查重→步骤2完整填写（关键字段 disabled）；(2) `buildHead()` 构造 `{payload:{...}, subject_name, ...骨架列}`，subject_name 前端按 subjectNameField 配置从关键信息取值填入；(3) payload 传 JS 对象（不序列化），复用 line_payload 已验证链路 |
| `cr-detail.js` | `h.name`→`h.subject_name`；`h.tax_no`→`(h.payload\|\|{}).tax_no`；`h.credit_code`→`(h.payload\|\|{}).credit_code`（评审 B3：不改则详情页三栏空白） |
| `cr-todo.js` | **两处必改**（第 2 轮 N4，非"核查"）：(1) tableHtml（:125）`r.name`→`r.subject_name`；(2) detailHtml（:149）`h.name`→`h.subject_name`、`h.tax_no`→`(h.payload\|\|{}).tax_no`、`h.credit_code`→`(h.payload\|\|{}).credit_code`（与 cr-detail.js 同款问题） |
| `activation-mapper.js` | 源字段下拉识别 payload JSONB 后递归展开 DCT fields 作为 `payload.xxx` 选项（评审 B4：不改则映射配置器对新结构不可用） |

### 6.4 文档

| 文件 | 改动 |
|------|------|
| `20260804_cmx-mdm_企业主数据管理平台设计方案V3_1.html` §13.4 / §14.1 | 更新表结构描述：删除"逐列展开"论述，改为"骨架 + 公共搜索列 + payload JSONB"模型。注：HTML 文件手动编辑 |

### 6.5 数据迁移（cmxlocal 开发库 + 生产）

采用评审 S1 建议的两阶段（先 ADD + 搬迁，验证后 DROP）：

```sql
-- 阶段一：ADD 新列（payload 带 DEFAULT+NOT NULL，PG 11+ 不重写表，快）
ALTER TABLE cv_mdm_apply
  ADD COLUMN IF NOT EXISTS payload JSONB NOT NULL DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS subject_name VARCHAR(200),
  ADD COLUMN IF NOT EXISTS subject_code VARCHAR(64);
ALTER TABLE cv_mdm_apply_line
  ADD COLUMN IF NOT EXISTS line_target_id BIGINT,
  ADD COLUMN IF NOT EXISTS line_deltas JSONB;
-- 第 2 轮 N1：mdm_activation 也要 ADD（方案 A 落地依赖 subject_name_field）
ALTER TABLE mdm_activation
  ADD COLUMN IF NOT EXISTS subject_name_field VARCHAR(64),
  ADD COLUMN IF NOT EXISTS subject_code_field VARCHAR(64);

-- 给现有激活映射配置回填 subject_name_field（如供应商：主体名是 name）
UPDATE mdm_activation SET subject_name_field = 'name' WHERE activation_code = 'supplier_apply';

-- 数据搬迁：旧列 → payload + subject_name
-- 注：jsonb_strip_nulls 剥掉 NULL 值（NULL 表示没填，不变成 "tax_no":null）
-- 注：|| COALESCE(ext_attrs) 若 ext_attrs 与三字段同名 key 冲突，ext_attrs 覆盖（语义：扩展覆盖关键）
UPDATE cv_mdm_apply SET
  subject_name = name,
  payload = jsonb_strip_nulls(jsonb_build_object(
    'tax_no', tax_no, 'credit_code', credit_code, 'short_name', short_name
  )) || COALESCE(ext_attrs, '{}'::jsonb)
WHERE payload = '{}'::jsonb;

-- 验证无误后，阶段二：DROP 旧列
ALTER TABLE cv_mdm_apply
  DROP COLUMN IF EXISTS name, DROP COLUMN IF EXISTS tax_no,
  DROP COLUMN IF EXISTS credit_code, DROP COLUMN IF EXISTS short_name,
  DROP COLUMN IF EXISTS ext_attrs;
```

回滚：若阶段一出问题，`DROP COLUMN payload, subject_name, subject_code` 即可（旧列数据未动）。

### 6.6 list_cr SELECT 改动（可选返回 payload）

**列表页默认不返回 payload**（第 4 轮用户决策：payload 影响接口效率，列表用不到）。

`list_cr` 增加 `with_payload: bool` 参数（默认 false）：

```rust
// cr_service.rs list_cr 签名增加 with_payload 参数
pub async fn list_cr(
    mm: &DatabaseManager,
    db_id: &str,
    doc_status: Option<&str>,
    page: i64,
    page_size: i64,
    with_payload: bool,   // 第 4 轮：列表默认 false 不查 payload
) -> Result<(Vec<Value>, i64), cmx_api_types::Error> {
    // 列表 SELECT：默认不带 payload；with_payload=true 时带上
    let payload_col = if with_payload { ", payload" } else { "" };
    let sql = format!(
        "SELECT id, doc_no, subject_name, cr_type, doc_status, create_time{payload_col} \
         FROM cv_mdm_apply WHERE {where_sql} ORDER BY create_time DESC \
         LIMIT ${n+1} OFFSET ${n+2}"
    );
    ...
}
```

**API 层**（handlers.rs 的 list handler）：`?withPayload=true` query 参数控制，默认 false。

```sql
-- 列表默认 SELECT（轻量，不查 JSONB）
SELECT id, doc_no, subject_name, cr_type, doc_status, create_time
FROM cv_mdm_apply WHERE {where_sql} ORDER BY create_time DESC LIMIT $n OFFSET $n

-- withPayload=true 时 SELECT（详情预览等场景）
SELECT id, doc_no, subject_name, cr_type, doc_status, create_time, payload
FROM cv_mdm_apply WHERE {where_sql} ORDER BY create_time DESC LIMIT $n OFFSET $n
```

### 6.7 clone_revise_inner 头表 INSERT...SELECT 具体新 SQL（评审 B1）

```sql
-- 新 SQL：28 列 → 26 列（删 name/tax_no/credit_code/short_name/ext_attrs 5 列，
--                         加 payload/subject_name/subject_code 3 列）
INSERT INTO cv_mdm_apply
  (id, upper_id, line_no, doc_no, doc_type_id, doc_type, target_dict_code, target_record_id,
   source_cr_id, cr_type, effective_date, subject_name, subject_code, payload,
   field_deltas, doc_status, business_status, entity_id, doc_date, attach_count, remark,
   create_by, create_time, update_by, update_time, delete_flag)
SELECT
  $1,          -- id = new_id
  upper_id,    -- 0（头表）
  line_no,     -- 0（头表占位）
  $2,          -- doc_no = mint_cr_doc_no 新铸号
  doc_type_id, doc_type, target_dict_code, target_record_id,
  $3,          -- source_cr_id = src_cr_id（指向被驳回的旧 CR）
  cr_type, effective_date, subject_name, subject_code, payload,
  field_deltas,
  'draft',     -- doc_status 重置为 draft
  business_status, entity_id, CURRENT_DATE,  -- doc_date 取当天
  COALESCE(attach_count, 0), remark,
  $4, now(),   -- create_by = operated_by, create_time = now
  $4, now(),   -- update_by = operated_by, update_time = now
  delete_flag
FROM cv_mdm_apply WHERE id = $5;  -- src_cr_id
```

> **doc_date 业务语义**（第 2 轮 N9）：新 SQL 的 `doc_date = CURRENT_DATE` 沿用旧 SQL 行为（cr_service.rs:147 原样），即克隆 CR 的申请日重置为克隆当天。这符合"克隆重提交=新申请"的语义（驳回后基于旧 CR 克隆新建，是新的变更申请）。若后续业务要求保留原始申请日，改为 `doc_date`（沿用源行）即可。

> **迁移时序约束**（第 2 轮 N2）：clone_revise 必须在 T1（DDL 迁移 + 数据搬迁）完成后再上线。§7 任务依赖 T6（cr_service 适配）→ T1 必须显式声明：若迁移阶段一（ADD 列但旧列未 DROP）期间触发 clone，源行的 subject_name/payload 可能尚未回填（搬迁 SQL 只跑一次），会产出 payload='{}' 的新 CR。

### 6.8 clone_revise 行表 INSERT 改动（评审 B2）

```sql
-- 旧（cr_service.rs:171-174）：11 列
INSERT INTO cv_mdm_apply_line
  (id, upper_id, line_no, line_type, line_action, line_payload,
   create_by, create_time, update_by, update_time, delete_flag)

-- 新：补 line_target_id, line_deltas（13 列）
INSERT INTO cv_mdm_apply_line
  (id, upper_id, line_no, line_type, line_action, line_payload,
   line_target_id, line_deltas,
   create_by, create_time, update_by, update_time, delete_flag)
```

同步：`load_cr_lines`（doc_accessor.rs:49）的 SELECT 要补 `line_target_id, line_deltas`，否则 clone 无源数据。

### 6.9 doc_accessor load_cr_head 新 SELECT

```sql
-- 新 SELECT（去掉旧 5 列，加 payload/subject_name/subject_code）
SELECT id, doc_no, doc_type, target_dict_code, target_record_id, source_cr_id,
       cr_type, effective_date, subject_name, subject_code, payload,
       field_deltas, doc_status, create_by, create_time
FROM cv_mdm_apply WHERE id = $1
```

**parse_jsonb_field 必须调用**：`parse_jsonb_field(&mut map, "payload")` + `parse_jsonb_field(&mut map, "field_deltas")`。漏掉 payload 会导致激活器 plan_create 拿到字符串而非对象，`as_object()` 返回 None，**静默丢所有 payload 内字段**（评审 B5）。

---

## 七、任务分解

| 任务 | 说明 | 依赖 |
|------|------|------|
| **T1：DDL 迁移** | ALTER TABLE 两阶段 + 数据搬迁（cmxlocal）：(a) cv_mdm_apply 加 payload/subject_name/subject_code；(b) cv_mdm_apply_line 加 line_target_id/line_deltas；(c) **mdm_activation 加 subject_name_field/subject_code_field**（第 2 轮 N1） | 无 |
| **T2：元数据定义更新** | doc_meta_v1.json cv_mdm_apply 字段重构（payload dataType 必须 `"JSONB"`） | 无 |
| **T3：check-key 接口** | 新增 `POST /api/mdm/check-key`（关键字段必填校验 + 查重，§4.3），复用 find_duplicates 核心 | 无 |
| **T4：前端步骤条改造** | cr-form.js 改 2 步步骤条（关键信息→完整填写），步骤1调 check-key，关键字段步骤2只读 | T2/T3 |
| **T5：激活器适配** | plan_create/plan_update 取值通用回退；ActivationConfig 增 subjectNameField | T2 |
| **T6：cr_service 适配** | list_cr SELECT（可选 payload，§6.6）/ clone_revise 头表 26 列 INSERT / 行表 clone 补列（§6.6-6.8）+ activation_store SELECT 补列（§6.1） | **T1（必须 T1 完成，N2 时序约束）** |
| **T7：doc_accessor 适配** | load_cr_head 新 SELECT + parse_jsonb_field(payload) + load_cr_lines 补列（§6.9） | T1 |
| **T8：前端其他改造** | cr-detail.js / cr-todo.js（tableHtml+detailHtml 必改，N4）/ activation-mapper.js（payload. 前缀显示+裸名落库，§5.5） | T2 |
| **T9：dict_tables/load_columns 通用化** | handlers.rs 去 supplier 硬编码，改 DCT meta 驱动（§11A） | 无（可与上述并行） |
| **T10：E2E 验证** | 步骤条查重 + create/update/clone + 详情展示 全链路 | T1-T9 |
| **T11：V3.1 文档更新** | §13.4/§14.1 同步（HTML 编辑） | T1-T10 完成 |

> **注**：第 4 轮废弃了原 T3（模块校验钩子）和 T4（MdmPayloadValidator），改为 T3（check-key 接口）+ T4（前端步骤条）。subject_name 回填责任改由 check-key 接口或步骤2前端构造（前端步骤1已收集关键信息，可直接填 subject_name）。

---

## 八、接口契约

CR 保存仍走标准 `/api/doc/save`（V3.1 迁移成果，不变）。变化在 payload 结构：

### 8.1 保存请求 payload 结构（create 类 CR）

```json
{
  "saveMode": "merge",
  "changes": {
    "cv_mdm_apply": {
      "inserted": [{
        "id": "t1",
        "fields": {
          "doc_type": "mdm_supplier_apply",
          "doc_type_id": 100,
          "doc_date": "2026-08-10",
          "doc_status": "draft",
          "entity_id": 1,
          "line_no": 0,
          "target_dict_code": "supplier",
          "cr_type": "create",
          "subject_name": "A公司",
          "subject_code": "SUP001",
          "payload": {
            "tax_no": "911...",
            "credit_code": "91...",
            "short_name": "A简称"
          }
        }
      }]
    },
    "cv_mdm_apply_line": {
      "inserted": [
        { "id": "t2", "upper_id": "t1", "line_no": 1,
          "fields": { "line_type": "bank_account", "line_action": "insert",
                      "line_payload": { "account_no": "工行6222", "bank_name": "工行" } } }
      ]
    }
  },
  "tableNames": ["cv_mdm_apply", "cv_mdm_apply_line"]
}
```

### 8.2 列表查询返回（list_cr）

**默认不返回 payload**（第 4 轮决策：列表用不到，影响效率）：

```json
{
  "total": 42,
  "rows": [
    {
      "id": 8001,
      "doc_no": "GYS20260810001",
      "subject_name": "A公司",
      "cr_type": "create",
      "doc_status": "draft",
      "create_time": "2026-08-10T..."
    }
  ]
}
```

**`?withPayload=true` 时**（详情预览等场景，额外返回 payload）：
```json
{
  "total": 42,
  "rows": [
    {
      "id": 8001, "doc_no": "GYS20260810001", "subject_name": "A公司",
      "cr_type": "create", "doc_status": "draft", "create_time": "...",
      "payload": { "tax_no": "911...", "credit_code": "91..." }
    }
  ]
}
```

### 8.3 详情查询返回（get_cr_detail）

```json
{
  "head": {
    "id": 8001, "doc_no": "GYS20260810001",
    "doc_type": "mdm_supplier_apply", "cr_type": "create",
    "target_dict_code": "supplier", "doc_status": "draft",
    "subject_name": "A公司", "subject_code": "SUP001",
    "payload": { "tax_no": "911...", "credit_code": "91...", "short_name": "A简称" },
    "field_deltas": null,
    "create_time": "..."
  },
  "lines": [
    { "line_type": "bank_account", "line_action": "insert",
      "line_payload": { "account_no": "工行6222", "bank_name": "工行" } }
  ]
}
```

---

## 九、风险与回滚

### 9.1 风险

| 风险 | 等级 | 缓解 |
|------|------|------|
| payload 内字段 required 校验遗漏 | 中 | MDM 校验层 + cm_* 物理约束双重防线；E2E 覆盖必填场景 |
| 激活器 payload 取值回退逻辑边界 | 中 | 单测覆盖 plan_create/plan_update 的 payload/公共列/缺失三路径 |
| 现有测试 CR 数据迁移失败 | 低 | cmxlocal 开发库数据可清空重建；生产目前无 MDM 数据 |
| clone_revise INSERT...SELECT 列对齐 | 中 | 严格按新结构 28→新列数对齐，单测验证 |
| 前端 buildHead 漏字段 | 低 | E2E 验证 create/update 全链路 |

### 9.2 回滚

DDL 迁移采用"先 ADD 新列 + 数据搬迁，验证无误后 DROP 旧列"两步走：
1. **阶段一**：ADD payload/subject_name/subject_code，数据搬迁，新旧并存
2. **阶段二**（验证通过后）：DROP name/tax_no/credit_code/short_name/ext_attrs

若阶段一出问题：DROP 新列即可回滚（旧列数据未动）。
若阶段二出问题：从备份恢复旧列（生产无 MDM 数据，风险极低）。

---

## 十、验证检查清单

- [ ] **V1 DDL**：ALTER TABLE 两阶段成功，数据搬迁正确（payload 内容 = 旧 tax_no/credit_code/short_name + ext_attrs 合并）
- [ ] **V2 ~~模块钩子~~**：~~保存非 MDM 单据时钩子跳过~~ **【废弃，第 4 轮】**
- [ ] **V3 create CR**：前端 buildHead 产出 payload 结构，标准保存成功，payload JSONB 入库；subject_name 由前端步骤条按 subjectNameField 填入
- [ ] **V4 check-key 校验**：关键字段缺失时 check-key 返 422 + violations；字段齐全但激活区无重复返 exists:false
- [ ] **V5 create 激活**：激活器从 payload 取值搬运到 cm_*，payload.name→cm_supplier.name 映射正确；**验证 payload 被 parse_jsonb_field 解析成对象**（评审 B5）
- [ ] **V6 update CR**：field_deltas 结构不变，激活器 plan_update 正确取 new 值
- [ ] **V7 clone-revise**：头表 26 列 INSERT...SELECT 列不错位；行表 clone 保留 line_target_id/line_deltas；铸号走 cmx-code
- [ ] **V8 list_cr**：列表按 subject_name 展示，按 doc_status/time 过滤排序正常
- [ ] **V9 cr-detail**：详情页 subject_name + payload.tax_no + payload.credit_code 正常展示（评审 B3）
- [ ] **V10 activation-mapper**：源字段下拉展开 payload.tax_no 等 DCT fields 选项（显示带前缀，落库裸名），可配置映射（评审 B4 / 第 2 轮 N3）
- [ ] **V11 activation_store**：find_by_doc_type SELECT 含 subject_name_field，ActivationConfig 反序列化正确（第 2 轮 N1）
- [ ] **V12 cr-todo**：tableHtml（:125）+ detailHtml（:149）两处字段消费正确（第 2 轮 N4）
- [ ] **V13 update deltas 对齐**：update 类 CR 的 field_deltas key 用裸名，plan_update 正确取 new 值（第 2 轮 N5）
- [ ] **V14 步骤条查重**：步骤1填关键信息→下一步调 /api/mdm/check-key→必填校验 + 查重；有重复弹框阻断（不提供绕过），无重复进步骤2（第 4/6 轮）
- [ ] **V15 步骤条锁定**：步骤1关键字段在步骤2只读（disabled）（第 4 轮）
- [ ] **V16 list_cr 默认无 payload**：列表接口默认不返回 payload，withPayload=true 时返回（第 4 轮）
- [ ] **V17 dict_tables 通用化**：merge/undo 走 DCT meta 驱动，新增主数据（如物料）无需改 handlers.rs 硬编码（第 4 轮）
- [ ] **V11 clippy**：改动文件零警告

---

## 十一、与业界对比

| 维度 | SAP MDG（staging/active） | 用户提出的"三表分离"方案 | **本方案（V3.2）** |
|------|--------------------------|------------------------|-------------------|
| 暂存层结构 | 每实体一 staging 表（与 active 1:1 镜像） | 每主数据一 temp 表（镜像 active） | 单头表+单行表，payload 吸收种类 |
| 100 主数据表数 | ~300 staging 表 | ~300 temp 表 | **2 表**（cv_mdm_apply + line） |
| 明细处理 | 每明细一 staging 表 | 每明细一 temp 表 | line_type 路由 + line_payload JSONB |
| 变更 diff | 需 join active 对比 | 需 join formal 对比 | field_deltas 原生存储 |
| 审批 | 自带 staging 状态 | change_request 自带审批字段 | 复用 cmx-flow |
| 列级校验 | 物理 staging 列 | 物理 temp 列 | 元数据驱动 payload 内校验 |
| 适合场景 | 单域少实体、SAP 生态 | 单域少实体 | **多域多实体、平台化** |

**本方案定位**：CMX 是 100+ 主数据平台，暂存层不应镜像激活层（双重镜像维护成本翻倍）。用 payload + 路由键吸收种类膨胀，用公共搜索列保留列表搜索体验，用元数据驱动校验保留列级校验能力。

---

## 十一·甲、通用化改造：dict_tables / load_columns 去 supplier 硬编码（第 4 轮新增）

### 11A.1 问题

`cmx-mdm-api/src/handlers.rs` 有两处 supplier 硬编码，与 payload 化重构的"100+ 主数据零硬编码"目标冲突：

```rust
// handlers.rs:261 —— dict → 物理表/明细表映射，写死 supplier
fn dict_tables(dict_code: &str) -> Option<(String, Vec<(String, String)>)> {
    match dict_code {
        "supplier" => Some(("cm_supplier".into(),
            vec![("cm_bank_account".into(), "supplier_id".into())])),
        _ => None,
    }
}

// handlers.rs:271 —— 加载列名，写死 supplier 的 7 个字段
fn load_columns() -> Vec<&'static str> {
    vec!["id", "name", "tax_no", "credit_code", "short_name", "phone", "update_time"]
}
```

这两处被 merge/undo（handlers.rs:519/526/585）和 match_group 名称回填（handlers.rs:392-396）调用。M3 标注"M6 多域改走 DCT meta tableName"——本方案提前到当前迭代完成。

### 11A.2 替代方案：DCT meta 驱动

**dict_tables（头表 + 明细表映射）**：改为从 DCT meta 派生。

```rust
// 替代 dict_tables：从 DCT meta 解析头表名 + 明细表映射
async fn resolve_dict_tables(
    mm: &DatabaseManager, db_id: &str, dict_code: &str
) -> Option<(String, Vec<(String, String)>)> {
    // 1. 加载头字典的 DictView（复用 cmx-dct-api 的 resolve_dict_meta）
    let head_view = load_dict_view(mm, db_id, dict_code).await?;
    let head_table = head_view.table_name.clone();    // cm_supplier
    // 2. 从同域 DCT 定义找明细表：遍历同 domain 的字典，找有外键指向头表 tableName 的
    //    （供应商域：supplier_bank 的 tableName=cm_bank_account，字段 supplier_id 挂头表）
    let details = load_detail_tables(mm, db_id, &head_view).await;
    Some((head_table, details))
}

// 明细表发现逻辑：遍历同域字典，匹配 *_id 字段名指向头表
async fn load_detail_tables(mm: &DatabaseManager, db_id: &str, head: &DictView) -> Vec<(String, String)> {
    let domain_dicts = load_domain_dicts(mm, db_id, &head.dict_code).await;
    let mut out = vec![];
    for dv in domain_dicts {
        if dv.dict_code == head.dict_code { continue; }  // 跳过头表自身
        // 明细表判定：该字典有字段名以 "_id" 结尾且语义指向头表
        // （如 supplier_bank 的 supplier_id → cm_supplier）
        for col in &dv.columns {
            if col.name.ends_with("_id") && col.name != "id" {
                out.push((dv.table_name.clone(), col.name.clone()));  // (cm_bank_account, supplier_id)
            }
        }
    }
    out
}
```

**明细表发现规则**：同域 DCT 定义中，字段名以 `_id` 结尾（非 `id` 主键）的字典视为该头表的明细表，该 `_id` 字段即外键列名。这是 CMX 已有约定（V3.1 §13.3"明细表挂头表=业务命名普通外键如 supplier_id"）。

**load_columns（列名清单）**：改为从 DCT meta 的 DictView.columns 派生。

```rust
// 替代 load_columns：从 DictView 取列名
fn columns_from_view(dv: &DictView) -> Vec<String> {
    dv.columns.iter()
        .map(|c| c.name.clone())
        .collect()
    // 供应商：["id","name","short_name","tax_no","credit_code","phone", ...DCT 定义的全部]
}
```

### 11A.3 影响的调用点（handlers.rs，第 5 轮核实共 6 处）

| 行号 | 现状 | 改造 |
|------|------|------|
| :392-396 | match_group 名称回填，`match dict_code { "supplier" => "cm_supplier" }` | 改 `resolve_dict_tables` 取 head_table |
| :443 | merge_requests_create 解析 line_tables（第 5 轮补：原漏列） | 改 `resolve_dict_tables` 的明细表映射 |
| :519 | merge_request_detail 取 head_table | 改 `resolve_dict_tables` |
| :526 | merge_request_detail `load_columns()` | 改 `columns_from_view(&head_view)` |
| :585 | merge_requests_undo 取 line_tables | 改 `resolve_dict_tables` 的明细表映射 |
| :396 | 名称回填 `["id","name","code"]` 写死 | 头表必有 id/name/code，可保留或从 DCT 取 |

### 11A.4 任务项（并入 §7）

| 任务 | 说明 |
|------|------|
| **T9（原 T-11A）** | dict_tables/load_columns 改 DCT meta 驱动：新增 resolve_dict_tables（含明细表发现）+ columns_from_view；改 handlers.rs **6 处**调用点（第 5 轮修正：原写 5 处，补 :443） |

> 此改造可与 payload 化并行推进，互不阻塞。但都服务"100+ 主数据零硬编码"目标，故并入本方案。

---

## 十二、历史遗留

- V3.1 §13.4 "主体关键字段逐列展开"决策 → 本方案废弃，改为 payload 模式
- V3.1 `cv_mdm_apply` 的 `ext_attrs` 字段 → 并入 payload，不再区分"关键"与"扩展"
- V3.1 `name` 字段 → 语义提升为 `subject_name`（公共搜索列），不再绑定"供应商名"

---

## 十三、评审记录

### 第 1 轮（双智能体并行评审 → 主智能体完善）

**架构一致性评审**发现 1 个阻碍 + 4 个重要：

| 编号 | 级别 | 问题 | 主智能体响应 |
|------|------|------|-------------|
| B1 | 阻碍 | payload 校验层在 /api/doc/save 调用链中无挂钩点；cr_service 不在保存路径上；validationRules 的 formula 引擎不支持 payload 内字段访问（json_to_fvalue 对象→Null） | ✅ §4 重写：改选"doc_save 模块校验钩子"方案（选项 2 变体），新增 module_validation.rs 按 module 路由；核实 formula.rs:115/419 确认选项 3 不可行 |
| I1 | 重要 | clone_revise 行表 INSERT 漏 line_target_id/line_deltas | ✅ §6.8 补行表 INSERT 新 SQL + load_cr_lines SELECT 补列 |
| I2 | 重要 | clone_revise 缺具体新 SQL（28→26 列） | ✅ §6.7 给出完整 26 列 INSERT...SELECT 新 SQL |
| I3 | 重要 | subject_name/subject_code 填充责任未落实 | ✅ §5.3 增 subjectNameField 配置 + 校验器回填（方案 A），前端零感知 |
| I4 | 重要 | 头表 doc_type_id/entity_id NOT NULL 与 fieldSet 不一致 | ✅ §3.1 DDL 改 NOT NULL |

**落地可行性评审**发现 5 个阻碍 + 4 个重要：

| 编号 | 级别 | 问题 | 主智能体响应 |
|------|------|------|-------------|
| B1 | 阻碍 | clone_revise INSERT...SELECT 必须重写（与架构 I2 同） | ✅ §6.7（同上） |
| B2 | 阻碍 | 行表 clone 漏 line_target_id/line_deltas（与架构 I1 同） | ✅ §6.8（同上） |
| B3 | 阻碍 | 遗漏 cr-detail.js，详情页三栏空白 | ✅ §6.3 补 cr-detail.js 改动 |
| B4 | 阻碍 | activation-mapper.js 源字段下拉失效 | ✅ §5.5 补递归展开 DCT fields + 点路径方案 |
| B5 | 阻碍 | payload 必须 parse_jsonb_field，否则激活器静默丢字段 | ✅ §6.9 强调 parse_jsonb_field(payload)，V5 验证项增加此检查 |
| I1 | 重要 | payload dataType 未明确，误写 VARCHAR 触发 JSONB cast bug | ✅ §6.2 锁定 dataType:"JSONB" + 代码引用 saver.rs:622/meta.rs:719 |
| I2 | 重要 | plan_create subject_name 硬编码字段名（与架构 S4 同） | ✅ §5.2 改通用回退，去硬编码 |
| I3 | 重要 | 数据迁移 SQL 的 strip_nulls + COALESCE 语义 | ✅ §6.5 注明 strip_nulls 剥 NULL + ext_attrs 覆盖语义 |
| I4 | 重要 | list_cr 前端消费者 cr-todo.js 未核查 | ✅ §6.3 补 cr-todo.js 核查项 |

**建议改进**已采纳：S1（两阶段迁移 ADD+搬迁+DROP）、S2（DCT fields 加载复用 cmx-dct-api）、S3（required = nullable==false）、S4（去硬编码字段名）、S5（28→26 明示）。

**结论**：第 1 轮所有阻碍性问题已响应，文档修订完毕，进入第 2 轮评审。

### 第 2 轮（验证修订 + 找新问题 → 主智能体第 3 轮修订）

**第 1 轮阻碍性验证**：6 项中 5 项 ✅ 已解决，1 项（I4/cr-todo.js）⚠️ 名义响应实际未给改法 → 第 2 轮 N4 重列为阻碍。

**第 2 轮新发现 5 个阻碍 + 4 个重要**：

| 编号 | 级别 | 问题 | 主智能体第 3 轮响应 |
|------|------|------|---------------------|
| N1 | 阻碍 | mdm_activation 表无 subject_name_field 列，方案 A 落地链路断裂 | ✅ §6.1/§6.5 补 `ALTER TABLE mdm_activation ADD COLUMN subject_name_field/subject_code_field`；activation_store SELECT 补列；T1 任务补子项；§6.5 补回填 UPDATE |
| N2 | 阻碍 | clone 在迁移中途触发会产出 payload='{}' 的 CR | ✅ §6.7 加迁移时序约束说明；§7 T6 显式依赖 T1 |
| N3 | 阻碍 | §5.2/§5.4/§5.5 三处 header_mapping key 格式矛盾（裸名 vs 点路径） | ✅ §5.5 统一为**裸名方案 i**：下拉显示 `payload.tax_no` 供识别，落库 strip 前缀用裸名 `tax_no`；§5.6 明确 deltas key 也用裸名 |
| N4 | 阻碍 | cr-todo.js 被标"核查"但实际 tableHtml(:125)+detailHtml(:149) 两处必改 | ✅ §6.3 改为必改，列出两处具体改动 |
| N5 | 阻碍 | field_deltas key 与 payload key 对齐未明确，update CR 会丢 new 值 | ✅ §5.6 新增 update deltas 对齐设计：field_deltas key 统一裸名，与 header_mapping 同源；cr-form.js deltas 生成逻辑改为裸名 |
| N6 | 重要 | §4.3 伪代码 field.nullable.unwrap_or(true) 与 DictColumn.nullable:bool 不符 | ✅ §4.3 改为 `!field.nullable` |
| N7 | 重要 | 模块匹配"含 mdm"过宽 + 注释示例值错误 | ✅ §4.2 改为精确等于 `module == "mdm"`；注释更正为裸 moduleCode |
| N8 | 重要 | 钩子返回 Some([]) 边界（空 Vec 是否阻断） | ✅ §4.2 module_validation 空 Vec 返 None 不阻断 |
| N9 | 重要 | clone SQL doc_date=CURRENT_DATE 业务语义存疑 | ✅ §6.7 加说明：沿用旧行为（克隆=新申请），未来可改 |

**结论**：第 2 轮所有阻碍性问题已响应，文档修订完毕，进入第 3 轮评审。

### 第 3 轮（最终验证轮）

**结论**：N1-N9 全部 ✅ 已解决，无新阻碍。方案可进入实施阶段。

### 第 4 轮（用户决策修订：校验机制重构 + 通用化）

用户对第 1-3 轮成果提出 3 个新方向调整：

| 编号 | 决策 | 主智能体响应 |
|------|------|-------------|
| F1 | mdm 校验不应在通用 doc/save 接口做；改前端步骤条预校验：步骤1关键信息→调 MDM 查重→进步骤2完整填写（关键字段只读） | ✅ §4 重写：废弃模块校验钩子（§4.2 标注「不使用」保留历史）；新增 §4.3 步骤条预校验设计（2 步 + check-key 接口 + find_duplicates 查重）；§7 任务移除原 T3/T4，改为 T3 check-key 接口 + T4 前端步骤条；§4.4 双重防线 |
| F2 | cv_mdm_apply 列表接口可选返回 payload（列表用不到，影响效率） | ✅ §6.6 list_cr 增加 with_payload 参数（默认 false）；§8.2 契约标注默认无 payload；V16 验证项 |
| F3 | handlers.rs 的 dict_tables/load_columns 写死 supplier 不合适 | ✅ 新增 §11A 通用化改造：dict_tables 改 DCT meta 驱动（resolve_dict_tables + 明细表发现规则）+ load_columns 改 DictView.columns 派生；§7 增 T9；V17 验证项 |
| — | subject_name 填充方从"后端校验器"改为"前端步骤条"（因校验器废弃） | ✅ §5.3 修订：前端按 subjectNameField 配置从关键信息取值填 subject_name |

**结论**：第 4 轮修订完成，进入第 5 轮评审验证。

### 第 5 轮（验证 F1/F2/F3 → 修复 R1 + 清理残留）

**F1/F2/F3 验证 + R1 阻碍**：

| 编号 | 级别 | 问题 | 主智能体响应 |
|------|------|------|-------------|
| F1 | — | 步骤条设计、§7 任务替换、§5.3 subject_name 改前端填充 | ✅ 到位（详见 §4.3/§5.3/§7） |
| F1→R1 | **阻碍** | check-key 复用 find_duplicates 不成立：FindDupBody.record_id 必填且必须命中已发布记录，新建场景无 recordId | ✅ §4.3 重写：改为复用底层 `match_algo::find_candidates` 函数（非接口），check-key handler 自行构造虚拟 target（id=0, fields=keyValue）+ load_published 拉全量候选比对 |
| F2 | — | list_cr 可选 payload | ✅ §6.6/§8.2 到位 |
| F3 | — | dict_tables/load_columns 通用化 | ✅ §11A 设计可行 |
| F3 残留 | 重要 | §11A.3 调用点漏 :443（merge_requests_create 的 line_tables） | ✅ §11A.3 补 :443，改"5 处"为"6 处" |
| 文档残留 | 次要 | §5.4/§6.1/§6.3/§10 多处仍引用已废弃的"校验器回填/MdmPayloadValidator/模块钩子" | ✅ 全部清理：§5.4 改"前端步骤条派生"、§6.1 废弃行标删除线、§6.3 cr-form.js 改前端填 subject_name、§10 V2 标废弃 V3/V4 改 check-key |

**结论**：R1 已解决（check-key 改复用底层 find_candidates 函数），文档残留全部清理，§11A.3 调用点补全。方案可进入实施阶段。
