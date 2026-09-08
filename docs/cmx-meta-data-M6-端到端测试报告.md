# cmx-meta-data 元数据管理重建 · M6 端到端测试报告

> 日期：2026-08-25 · 里程碑：M6（种子 + 双语翻译包 + 数据维护/i18n 前端 + E2E）
> 服务：`cmx-meta-server`（:8096，独立 workspace `presentation/cmx-meta-data`）
> 门户：`cmx-portal-server`（:8080，fresh build，经 `MetaProxyModule` 反代 `/api/meta/*` + `meta.*` 页面）

## 1. 交付物

### 后端
- **种子装载层** `cmx-meta-store::seed`
  - 递归扫 `data/seed/entitytypes/**/*.json`，以 JSON 内 `coord`+`name`+`version` 为权威落生效目录 `data/entitytypes/<d>/<a>/<m>/<file>`；复用 `defs::save` → **走完整结构校验**（违规不落，进 `rejected`）。
  - `data/seed/i18n/<locale>.json` **非破坏合并**进生效包：只补生效包中缺失/空的 key，已有值不覆盖 → **幂等**。
  - 报告结构 `SeedReport{ entitytypes[], rejected[], i18n_added{locale:count} }`。
- **端点** `POST /api/meta/seed`（app 中立核 `handlers::seed` + `routes.rs` 挂载，随 `meta_routes::<S>()` 泛型下发，门户反代零改）。

### 种子（三新范式，零会计域，覆盖三 profile 关键能力）
| 实体 | profile | 关键能力 |
|---|---|---|
| `crm/sales/core/industry` | reference | **自分级** self-hierarchy（parent_id→id） |
| `crm/sales/core/customer` | reference | **外键** foreign-key→industry + **金额** money credit_limit |
| `csm/service/core/service_ticket` | transaction | **双层**(ticket + ticket.items) + **聚合** hours→total_hours(sum) + **生命周期** open/in_progress/closed + **约束** hours_positive |

### 双语翻译包
- `data/seed/i18n/zh-CN.json` / `en-US.json`，各 **31 键**全覆盖（含 `__name__`/字段/子层/状态 state.*/动作 action.*/规则 rule.*/消息 msg.*）。
- **控制 token（enum code / transition action）恒 ASCII**，不入翻译包——翻译包只维护展示文本。

### 前端（native 联邦页，`web/ui-native/meta/`）
| 页面 id | 文件 | rev | 能力 |
|---|---|---|---|
| `meta.entity.workbench` | entity-workbench.js | `7a88cd2652bf739c` | 业务向导 ↔ 技术 schema 双视图（M4 建，M6 沿用） |
| `meta.data.maintenance` | data-maintenance.js | `7e159933132f1cbc` | 引用/主数据行维护：按字段语义渲染表格/表单 CRUD，labelKey→翻译包解析业务标题 |
| `meta.i18n.editor` | i18n-editor.js | `263c10a791939e23` | zh-CN/en-US 并排逐键编辑 + 缺译红标 + 仅看缺译过滤 + 新增键 |

## 2. 真机 E2E（16 步全绿）

服务直连 :8096：
1. **seed 装载**：`entitytypes: 3, rejected: 0, i18n_added: {en-US:31, zh-CN:29}`（zh 2 键 M3 已存 → 非破坏跳过）✅
2. 定义落生效目录：`crm/sales/core` 列出 industry/customer（reference, v1, default）✅
3. 事务实体：`csm/service/core` 列出 service_ticket（transaction, v1）✅
4. 部署 industry → `mr_industry`（physical_db=meta-biz, ledger_db=meta-primary）✅
5. 部署 customer → `mr_customer` ✅
6. 部署 service_ticket → `mx_ticket` + `mx_ticket_item`（双层）✅
7. **物理列校验**：`id`/`parent_id`/`industry_id`/`customer_id`/`ticket_id`→**bigint**（int8 宽度保真，未塌缩）；`credit_limit`→**numeric(18,2)**、`total_hours`/`hours`→**numeric(10,2)**（money/quantity 精度保真）✅
8. 数据行 upsert：industry×2（MFG/FIN）+ customer×1（华为，引用 industry_id=1，credit_limit=5000000.00）→ **雪花铸号 pk** ✅
9. 数据行 search：customer total=3，**money 精度回读 `5000000.00`** ✅
10. 缺译检查 customer@en-US：**count=0**（齐全）✅
11. 缺译检查 customer@fr-FR：**count=7**（未提供法语包 → 全缺，判别正确）✅
12. **seed 幂等**：二次装载 `i18n_added: {en-US:0, zh-CN:0}`，rejected=0 ✅
13. 三页 native 联邦：rev 各异（见上表），bytes 11621/9613/6163 ✅

门户 :8080（fresh build）→ MetaProxy → :8096：
14. `/api/meta/db-state`（entity_count=3）、`/api/meta/seed`（幂等）、`/api/meta/entitytypes` 全反代通 ✅
15. **写路径经门户**：industry upsert（RETAIL，铸号 pk）→ search 回读 3 行 ✅；i18n set（`crm.industry.retail`=Retail）→ 回读命中 ✅
16. **三页 rev 门户↔直连字节一致**：`7a88cd…` / `7e15…` / `263c…` 全 ✓ ✅

## 3. 编译

- `cargo build -p cmx-meta-store -p cmx-meta-app`：绿（65 crates）。
- `cargo build -p cmx-meta-server`：绿。
- `cargo build -p cmx-portal-server`（含 `cmx-platform-app::merge_meta`）：绿 → 真机 boot 成功。

## 4. 遇到的坑

- **既有平台库 schema 漂移**（与 meta 零关）：fresh 门户 boot 撞 baseline 迁移失败——`cmx_exclusion_rule_item.archived` 列缺失（IAM 排他规则表旧版；`CREATE TABLE IF NOT EXISTS` 遇既存旧表未补新列，后续 `COMMENT ON COLUMN` 崩）。诊断确认改动零触及该表/迁移，按迁移期望补 7 列（archived/create_time/update_time/create_by/create_name/update_by/update_name）即通。**这是平台侧存量漂移，非本次引入。**
- 停留在 :8099 的 `web-server`（pid 11765，Aug-21 旧单体二进制）非本 workspace 产物；fresh 门户 `cmx-portal-server` 实际起在 :8080，M6 验证以 :8080 为准。

## 5. 边界确认（clean-room 不变量持续成立）

- 存储：只写 `mt_*`(台账) / `mr_*`(reference 物理) / `mx_*`(transaction 物理)，落独立库 `cmx_meta` + `cmx_meta_biz`；**零触及** cmx-model 的 `cmx_model_*`/`cf_*`/`cv_*`。
- 代码：仅依赖 cmx-container 公用设施（chassis/monitor/DDL 引擎/DB 层/jsonstore/form），**零依赖 cmx-model crate**。
- 种子/翻译包组织仅为交付手段，装载后以生效目录 + 生效翻译包为唯一事实源。
