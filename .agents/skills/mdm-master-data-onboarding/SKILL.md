---
name: mdm-master-data-onboarding
description: 指导在 CMX MDM 模块新增一种主数据类型（客户/物料/组织/科目等），全程元数据驱动、零前端代码：DCT 字典元数据（头表 cm_* + 明细表，业务外键挂头）、复用 cv_mdm_apply CR 单据、激活映射配置、菜单节点 props 注入（dictCode/docType）、seed 数据、编码规则、模型中心 deploy。当用户要求新增主数据类型 / 加一种主数据 / 接入客户/物料/组织主数据 / 建主数据列表菜单 / 主数据字典怎么配 / 主数据 seed，或提到 master-list、master-detail、mdm_activation、dictCode props、主数据零代码复用时必用。与 menu-generator（菜单落地与 cmx_menu 同步）、meta-enricher（列 edit/display 规范）配合——本技能管"新增一种主数据类型的端到端配置"。
---

# MDM 新增主数据类型（元数据驱动，零前端代码）

指导你在 CMX MDM 模块**新增一种主数据类型**（客户/物料/组织/科目…）。列表/详情/录入/查重/管家页全是**公共页**（`master-list` / `master-detail` / `cr-form` 等），**不写任何前端代码**——差异全部由「DCT 元数据 + 激活映射配置 + 菜单 props」注入。

> **铁律**：新增主数据类型 = **改元数据 JSON + 配激活映射 + 加菜单节点 + seed**，**零 Rust、零前端 JS**。`cm_*` 只存 published（黄金记录），草稿一律走 CR 单据；激活器是 `cm_*` 唯一写入闸口。
>
> **三个最容易漏、漏了必出事的点**（见 §九 详述）：
> 1. **激活映射没配** → 列表页直接红字报错、录入表单打不开（它不在任何文件里，只在运行库）。
> 2. **菜单改了 JSON 不同步 `cmx_menu`** → 侧栏不出现新菜单。
> 3. **编码规则没 seed** → 不报错，code 静默变成占位码（如 `CUSTOM-xxxx`，前缀=dictCode 大写前 6 位）。

---

## 一、核心数据流（先理解）

```
你改/配的东西                                            生效方式
────────────────────────────────────────────────────────────────
① DCT 元数据 JSON（头+明细字典）                         文件即真源，运行时直读
   cmx-container/assets/model/data/meta/definitions/basic/dataplatform/mdm/
        dataplatform_dct_meta_v1.json
② 物理表 + seed                                         模型中心 deploy（DCT→SEED 顺序）
   seed/cm_<type>.json（文件名=物理表名）
③ 激活映射 mdm_activation（create+update 两条）      「激活映射配置器」UI 配置，写运行库
④ 菜单节点 mdm-menu.json（props 注入 dictCode/docType）  改 JSON + 同步 cmx_menu（见 §六）
⑤ 编码规则 cmx_code_rule                                 迁移 SQL seed（必做，别只 UI 配）
────────────────────────────────────────────────────────────────
复用、不用动的：
   cv_mdm_apply / cv_mdm_apply_line（CR 单据，所有主数据共用）
   master-list / master-detail / cr-form / cr-todo / duplicate-check / steward（公共页）
   cmx-mdm 后端 Rust（全按 dictCode/target_table 配置驱动）
```

> **为什么能零代码**：公共页靠菜单 `props.dictCode` 决定查哪个字典（`GET /api/dct/meta?dict=…` + `POST /api/dct/data/search?dict=…`），靠 `GET /api/mdm/activations?targetDict=…` 的 `line_mappings` 自动发现明细子表。后端按 `dictCode/target_table` 泛化，无类型特判。
>
> **数据落地链路**：`cr-form` 录入 CR（草稿）→ submit 提交 → approve 审批通过**自动触发激活器** → 写 `cm_*`（published 黄金记录）。审批前 `cm_*` 不动。

---

## 二、新增一种主数据的产物清单（总表）

以「客户 customer」为例：

| # | 产物 | 文件/位置 | 操作 | 性质 |
|---|---|---|---|---|
| 1 | DCT 字典元数据 | `cmx-container/assets/model/data/meta/definitions/basic/dataplatform/mdm/dataplatform_dct_meta_v1.json` | 改：`dictionaryTables` 追加头表 `customer` + 明细表 | 纯配置 |
| 2 | seed 示例数据 | `…/mdm/seed/cm_customer.json`（+ 明细 `cm_customer_bank.json`） | 新建 | 纯数据 |
| 3 | 菜单节点 | `cmx-container/assets/model/data/menu-pages/basic/dataplatform/mdm/mdm-menu.json` | 改：加「客户列表」workspace-node | 纯配置 |
| 4 | 编码规则 | `docs/sql/v2/biz/migrations/<日期>_<序号>_customer_code_rule.up.sql`（cmx_code_rule 在业务库） | 新建迁移 seed | 数据 |
| 5 | 查重规则（可选） | 同上迁移，或查重界面维护 | seed `md_match_config` | 数据 |
| 6 | **激活映射** | `mdm_activation`（运行库） | 「激活映射配置器」UI 配 create+update | **必配，最易漏** |
| — | DOC 单据 / 前端页 / Rust | — | **不用动**（复用） | — |

建表：`cm_customer` 等由**模型中心 deploy** 编译 DCT JSON 建表（§四），**不手写迁移 SQL**；迁移 SQL 只用于 `cmx_code_rule` / `md_match_config` 这类"不走 compile"的平台表 seed。

---

## 三、DCT 字典元数据（头表 + 明细表）

在 `dataplatform_dct_meta_v1.json` 的 `dictionaryTables[]` 追加。**头表与明细表都是独立 DCT**，明细表用**业务命名外键列**（如 `customer_id`）挂头表，**无物理 FK**。

### 3.1 头表模板

```jsonc
{
  "dictMeta": {
    "dictCode": "customer",            // 字典码 = 全局路由键（菜单 props.dictCode 用它）
    "dictName": "客户",
    "dictKind": "BUSINESS",
    "selfHierarchy": false,            // 树形主数据（科目树/组织树）才设 true
    "tableName": "cm_customer",        // 物理表名，约定 cm_ 前缀
    "idField": "id", "codeField": "code", "labelField": "name",
    "remark": "客户主数据头表(激活区,只 published)",
    "codeLength": 32,
    "codeRule": { "mode": "auto", "field": "code", "ruleCode": "MDM_KH" }  // ← 激活器铸 code 读这个
  },
  "fields": [
    // 业务字段，每列：dataType/fieldLength/nullable/id/name/caption.zh_CN/edit.mode/display.mode/width/enumValues…
    // edit.mode / display.mode 的规范值域见 meta-enricher 技能
  ],
  "baseFieldSet": "dictionaryCommonFields",        // 注入 id/code/name/sort_no/status
  "auditFieldSet": "dictionaryAuditFields",        // 注入 create_by/create_time/update_by/update_time
  "mdmGovernanceFieldSet": "mdmGovernanceFields",  // 注入 lifecycle_status/published_version/effective_date
  "permissionScope": "global",
  "codeRule": { "mode": "manual", "field": "code", "uniqueCheck": true },  // ← 表级 codeRule，见 §3.3 分工
  "uniqueKeys": [["code"]]
}
```

### 3.2 明细表模板

```jsonc
{
  "dictMeta": { "dictCode": "customer_bank", "dictName": "客户银行账户", "dictKind": "BUSINESS",
    "selfHierarchy": false, "tableName": "cm_customer_bank",
    "idField": "id", "codeField": "code", "labelField": "name",
    "codeRule": { "mode": "auto", "field": "code", "ruleCode": "MDM_KH" } },  // 照抄 supplier_bank；明细行 code 由激活器回填占位(MDM-{id})，此配置对激活无影响
  "fields": [
    // 必含一个外键列：BIGINT customer_id，edit.mode="readonly" + visible=false（隐藏，激活器回填）
    { "dataType": "BIGINT", "fieldLength": 20, "nullable": false, "id": "customer_id", "name": "customer_id",
      "caption": { "zh_CN": "所属客户ID" }, "edit": { "mode": "readonly" }, "visible": false }
    // …其余业务列：account_no / bank_name / …
  ],
  "baseFieldSet": "dictionaryCommonFields", "auditFieldSet": "dictionaryAuditFields",
  "mdmGovernanceFieldSet": "mdmGovernanceFields", "permissionScope": "global",
  "uniqueKeys": [["customer_id", "account_no"]]
}
```

> **外键列命名**：`<头表 dictCode>_id` 或与头表语义一致的业务名（supplier 用的是 `supplier_id`）。明细表**物理表名**建议 `cm_<头表>_<明细>`（如 `cm_customer_bank`）——注意 supplier 的历史命名是 `cm_bank_account`（没带 supplier），新类型按规整命名即可。

### 3.3 两层 codeRule 的分工（常见困惑，务必分清）

| 位置 | 示例 | 谁读它 | 作用 |
|---|---|---|---|
| `dictMeta.codeRule` | `{mode:"auto", ruleCode:"MDM_KH"}` | **激活器**铸 `cm_*.code` | 激活落库时自动生成主数据编码 |
| 表级 `codeRule` | `{mode:"manual", uniqueCheck:true}` | dct 直存写入路径 | 字典数据直接维护时的编码/查重；主数据走激活器，通常 manual 即可 |

新增主数据照抄 supplier：`dictMeta.codeRule` 设 auto + 你的 ruleCode，表级 codeRule 设 manual + uniqueCheck。

---

## 四、建物理表 + seed（模型中心 deploy）

**不手写建表 SQL**。`cm_*` 由模型中心编译 DCT JSON 建表，**additive-only**（已有表只加列加索引，不 DROP，增量加 customer 表安全）。

**在哪触发（常见卡点）**：门户 **shellbar →「集群数据源 / 数据库运维工作台」**（native-page `portal.datasource.cluster`，**不是常规菜单**）→ 选目标业务库（`db_id`，库须已初始化 INIT）→ 在"模块矩阵 × kind 格"勾 `mdm` 模块的 **DCT** 格 → 预览（`deploy-plan-stream`）→ 批准执行（`deploy-stream`）。SEED 同理勾 **SEED** 格。

1. **部署 DCT**（建表/加列）：后端 `POST /api/model/deploy-stream`，body `{db_id, items:[{kind:"DCT", domain:"basic", application:"dataplatform", module:"mdm", file:"dataplatform_dct_meta_v1.json"}]}` → compile → 建 `cm_customer` 等。
2. **部署 SEED**（灌示例数据）：同入口勾 SEED 格（或 items `kind:"SEED"`）→ 扫描 `seed/*.json` → 前置校验表已建（没建会报"请先部署 DCT 元定义"）→ UPSERT（冲突列按 uniqueKeys/主键推断，走 `code` 唯一索引）。
3. **顺序**：先 DCT 后 SEED。也可 DCT+SEED **同批提交**——引擎按 kind 稳定排序（DCT→DOC→RPT→SEED→MENU）自动先建表后灌数。DOC 表 `cv_mdm_apply` 已存在则无需重复部署。

**seed 文件格式**（`seed/cm_customer.json`，文件名=物理表名）：纯 JSON 数组，每行含**全部列字面值**（含注入列）：

```json
[
  { "id": 1, "code": "CUS0001", "name": "某某客户有限公司", "sort_no": 10, "status": 1,
    "create_by": null, "create_time": "2024-01-15 09:00:00", "update_by": null, "update_time": null,
    "lifecycle_status": "published", "published_version": 1, "effective_date": "2024-01-15" }
]
```
明细 seed 同理，带 `customer_id` 指向头表 id。重复部署幂等（UPSERT）。

---

## 五、激活映射配置（最容易漏，必配）

存 `mdm_activation`，**无文件 seed**，进菜单「**激活映射配置器**」（`portal.mdm.activation-mapper`）配 **create + update 两条**。漏配后果：`master-list` 启动校验直接红字"请先配置激活映射"，`cr-form` 打不开。

每条字段：

| 字段 | 值（customer 示例） | 说明 |
|---|---|---|
| `activation_code` | **自动派生，无需填** | 配置器按 `source_doc_type__cr_type` 自动生成（如 `kh__create`），输入框只读 |
| `source_doc_type` | `kh` | **必须 = 菜单 props.docType** |
| `cr_type` | `create` / `update` | 两条 |
| `target_dict` | `customer` | 目标头字典 |
| `target_table` | `cm_customer` | 选字典时自动带出 |
| `header_mapping` | `{name:"name", credit_code:"credit_code", tax_no:"tax_no", …}` | CR 源字段 → cm_* 列 |
| `subject_name_field` | `name` | 主体名提升列（查重/列表跳转用） |
| `key_fields` | `[{field:"credit_code",weight:40,kind:"Exact"},{field:"name",weight:60,kind:"EditDistance"}]` | 录入步骤①关键信息+查重；空=跳过查重 |
| `line_mappings` | `[{lineType:"bank", targetDict:"customer_bank", targetTable:"cm_customer_bank", parentIdField:"customer_id", fields:{account_no:"account_no",…}}]` | 明细映射；`parentIdField`=外键列，详情页据此自动发现子表 |
| `doc_code_rules` | 可选 `{doc_no:"MDM_KH"}` | 覆盖单据号规则；不配回退 MDM_BILL |

> ⚠️ **key_fields 约束**：每个 `field`（目标列名）必须出现在 `header_mapping` 的 value 中，否则该项被**静默丢弃**、不进录入步骤①/查重（cr-form 按 header_mapping 反查目标列）。上例的 `credit_code` 必须已在 header_mapping 映射。

> `source_doc_type`（docType）是一个**自由字符串**，激活器按 `source_doc_type + cr_type` 精确匹配定位配置；`kh`/`gys` 等取值自定，只要菜单 props 与激活映射一致即可（无 doc_type 字典强校验）。

---

## 六、菜单节点（props 注入 + 必须同步 cmx_menu）

改 `cmx-container/assets/model/data/menu-pages/basic/dataplatform/mdm/mdm-menu.json`。**菜单为职能三段式（2026-08-19 重组）**：`mdm-archives`（主数据档案，按往来单位/物料/财务/组织人事四域夹归组实体）/ `mdm-cr-all`（变更申请单，全类型聚合，**勿动**）/ `mdm-governance`（治理与分发）。**新类型只做一件事**：在对应域夹下加 1 个档案节点——**不再加配对的「XX单据列表」节点**，聚合节点 `mdm-cr-all` 的类型下拉/类型列按激活映射动态生成，新类型接入自动出现。新域无处安放时先与用户确认建新域夹。**公共页恒定 `portal.mdm.master-list`，差异全在 props**：

```jsonc
{
  "id": "mdm-customer-list",            // 必带 mdm- 前缀（cmx_menu.code 全局唯一，见 menu-generator §2.1）
  "name": "customer-list", "caption": "客户列表", "type": "workspace-node",
  "permissionId": null, "icon": "tabler-outline/...",
  "workspace": { "id": "mdm_customer_list", "content": { "caption": "客户列表", "icon": "...",
    "views": [{ "id": "mdm-customer-list-content", "tabLabel": "列表", "icon": "...",
      "type": "native_pages", "native_page": "portal.mdm.master-list", "view": "content",
      "props": {
        "dictCode": "customer",          // 必填：页面据此查 dct/meta 与 dct/data/search
        "docType": "kh",                 // 必填：须 = 激活映射 source_doc_type（档案页「新增/变更」据此打开 cr-form）
        "title": "客户列表",              // 必填：页面标题
        "entityName": "客户",             // 可选：按钮文案"新增客户"
        "icon": "customer",              // 可选
        "columns": ["code","name","credit_code","published_version"]  // 可选：列子集/顺序；缺省=dct/meta 可见列自动过滤平台列
      }}]}}
}
```

> **⚠️ 改完 JSON 必须同步 `cmx_menu` 才在侧栏生效**：运行中的门户侧栏从 `cmx_menu` 表回源（`GET /api/menu/tree`），**不是直读文件**——**勿信"改 JSON 即生效"**。同步用 menu-generator 技能的 `scripts/sync_menu_db.py`（.agents/skills/menu-generator/scripts/）（**在工作区根执行**，脚本按 domain/application/module **先删后插**、功能幂等；注意 `cmx_menu.id` 每次同步会漂移，但权限按 code/fun_code 关联、不受影响），或走模型中心 MENU kind 部署。菜单结构/id 前缀遵循 menu-generator 技能。

---

## 七、编码规则（必须 seed 到迁移 SQL）

> **教训**：supplier 的 `MDM_GYS` 只在运行库（有人 UI 手工建的），**全库无 seed**——新环境初始化后 supplier 自动铸号会退化成占位码。新类型**务必把 code 规则写进迁移 SQL**，别重蹈覆辙。

新建 `docs/sql/v2/biz/migrations/<日期>_<序号>_customer_code_rule.up.sql`（cmx_code_rule 在业务库）：

```sql
INSERT INTO cmx_code_rule (id, rule_code, rule_name, mode, segments, joiner, is_active)
VALUES (9000000000000002, 'MDM_KH', '客户主数据编码', 'auto',
        '[{"type":"const","value":"CUS"},{"type":"dateSerial","format":"YYYYMMDD","width":4,"start":1}]'::jsonb,
        '', TRUE)
ON CONFLICT (rule_code) WHERE archived = 0 DO NOTHING;
```

- `id` 用一个不与现有序列冲突的固定值（supplier/MDM_BILL 已占 `9000000000000001` 附近，往后排）。
- 字典 code 由激活器按 `dictMeta.codeRule.ruleCode` 铸号；漏配不报错但 code 变占位码。
- CR 单据号默认走 `MDM_BILL`（已有 seed），无需动；要自定义用激活映射 `doc_code_rules`。

### 可选：查重规则 seed（`md_match_config`）

参照 `docs/sql/v2/biz/migrations/20260819_001_baseline.up.sql` 中 `cmx_code_rule` 的 `INSERT…SELECT…WHERE NOT EXISTS` 写法（历史治理迁移 20260812_001 已并入该基线；id 用固定值，避开应用层 pk52 序列）：

```sql
INSERT INTO md_match_config (id, rule_name, dict_code, target_table, specs, cluster_keys, survive_fields, thresholds, is_active)
SELECT 2, '客户默认查重', 'customer', 'cm_customer',
       '[{"field":"credit_code","weight":40,"kind":"Exact"},{"field":"name","weight":60,"kind":"EditDistance"}]'::jsonb,
       '["credit_code","name"]'::jsonb,
       '["name","credit_code","phone"]'::jsonb,
       '{"auto_merge":95,"review":80}'::jsonb,
       TRUE
WHERE NOT EXISTS (SELECT 1 FROM md_match_config WHERE dict_code='customer' AND rule_name='客户默认查重');
```
也可不 seed，后续在查重界面（duplicate-check）手工维护。

---

## 八、生效方式汇总

| 产物 | 生效方式 |
|---|---|
| DCT/DOC 元数据 JSON | 文件即真源，运行时直读，改完即时生效；但建表须 deploy DCT |
| 物理表 + seed | 模型中心 deploy：DCT → SEED（顺序不可反） |
| 菜单 | 改 JSON 后 `sync_menu_db.py` 同步 cmx_menu（或 MENU deploy） |
| native-pages 公共页 | 不用改；若改了 JS，文件直读秒级生效 |
| 激活映射/编码规则/查重规则 | UI 配置即写库即生效；code 规则建议走迁移 SQL |
| Rust | 不涉及（全配置驱动） |

---

## 九、三个最容易漏的坑（RED 基线实测）

1. **激活映射没配**：它不在任何文件里（只在运行库 `mdm_activation`）。漏配 → `master-list` 红字报错、`cr-form` 打不开。**必做 §五**。
2. **菜单 JSON 改了不生效**：侧栏从 `cmx_menu` 回源，改 JSON 后必须 `sync_menu_db.py` 同步。**必做 §六末**。
3. **编码规则漏配不报错**：code 静默变占位码（如 `CUSTOM-xxxx`，前缀=dictCode 大写前 6 位）。**必做 §七 seed 到迁移**。

---

## 十、检查清单（交付前自检）

- [ ] `dictionaryTables` 加了头表（`cm_<type>`）+ 需要的明细表？外键列 `readonly`+`visible:false`？
- [ ] `dictMeta.codeRule` 设了 auto + 你的 ruleCode？`labelField`/`codeField` 对？
- [ ] 模型中心 deploy 了 DCT（建表）再 SEED（灌数），顺序没反？
- [ ] 激活映射配了 **create + update 两条**？`source_doc_type` 与菜单 props.docType 一致？`line_mappings.parentIdField` = 外键列？
- [ ] 档案节点放进 `mdm-archives` 对应域夹（非 mdm-root 直挂）？id 带 `mdm-` 前缀？props 有 dictCode/docType/title？公共页是 `portal.mdm.master-list`？**没有**另加配对「XX单据列表」节点（`mdm-cr-all` 聚合自动覆盖）？
- [ ] 菜单 `sync_menu_db.py` 同步了 cmx_menu？
- [ ] 编码规则写进迁移 SQL（`ON CONFLICT DO NOTHING`）？id 不撞？
- [ ] （可选）查重规则 `md_match_config` seed 了？

---

## 十一、常见错误

| 错误 | 原因 | 修复 |
|---|---|---|
| 新菜单侧栏不出现 | 只改了 JSON，没同步 cmx_menu | 跑 `sync_menu_db.py`（§六） |
| 列表页红字"请先配置激活映射" | 激活映射没配 | 「激活映射配置器」配 create+update（§五） |
| code 变成占位码（如 `CUSTOM-xxxx`） | 编码规则没 seed，只 UI 配或漏配 | 迁移 SQL seed cmx_code_rule（§七） |
| 详情页没有子表区 | 激活映射 line_mappings 没配/parentIdField 错 | 配 line_mappings，parentIdField=外键列 |
| 列表列一堆平台列（create_by 等） | 没配 columns 且期望精选 | props.columns 指定子集；缺省会过滤平台列但含 status 等业务列 |
| 明细表外键列显示在子表 | 元数据忘标 visible:false | 外键列设 visible:false（公共页也会无条件剔除 parentIdField） |
| 新类型录入表单字段不对 | header_mapping / key_fields 没配对 | 对照 §五 配 header_mapping、subject_name_field |
| seed 部署报"请先部署 DCT 元定义" | SEED 先于 DCT | 先 deploy DCT 再 SEED |
| docType 用了新串担心冲突 | docType 是自由串，无字典强校验 | 与激活映射 source_doc_type 一致即可 |

---

## 附：与其他技能的分工

- **menu-generator**：菜单 JSON 结构、id 前缀规范、`sync_menu_db.py` 同步 cmx_menu —— 本技能 §六 引用它。**注意边界**：menu-generator 与本技能口径一致——侧栏运行时读 `cmx_menu`，改 JSON 必须同步（menu-generator §3.4 `scripts/sync_menu_db.py`）。
- **meta-enricher**：字段 `edit.mode`/`display.mode` 规范值域 —— 写 DCT `fields` 时遵循。
- **native-page-generator**：公共页（master-list/master-detail）的运行时契约 —— 需要改公共页时才用；新增类型**不需要**。
- **cmx-components-guide**：组件用法 —— 一般不涉及（公共页已封装）。
