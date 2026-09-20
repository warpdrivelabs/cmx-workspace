---
name: cmx-onto-toolkit
description: 指导 AI 为任意企业业务场景设计并生成本体平台（cmx-ontology）演示数据的完整方法论与参数化工具链。当用户要求"给本体平台造演示数据""设计一个业务场景演示本体""准备 onto/ontology 演示""生成对象类型/关系/函数/动作测试数据""漏斗/数据集成演示""本体流程闭环演示（action 发起流程、审批回写）"，或提到"本体演示""onto 测试数据""scenario-spec"时必用。核心是场景规格驱动：先写场景规格 JSON，再用 scripts/onto_seed.py 执行，而非手写脚本。
---

# cmx-onto-toolkit · 本体平台演示数据方法论

## 概述

本技能是**方法论**而非一次性造数器：指导 AI 为**任意企业业务场景**产出「场景规格 JSON」，再用参数化脚本执行。规格与执行分离——换场景只换规格，脚本通用。

工具链：
- `scripts/onto_seed.py` —— 场景规格驱动造数器（sharedProperties→interfaces→objectTypes→linkTypes→functions→actions→dctImports→datasourceBind→funnelMappings(+sync)→objects→links→views→snapshot→docImports，全 upsert 幂等可重跑）。
- `scripts/onto_clean.py`（或手写 psql）—— 清库（见「清库」节）。
- `examples/procurement/` —— 采购供应链完整范例（第一个实战归档）：`scenario-spec.json` + `seed_po_docs.py`（业务库单据灌数）+ `walkthrough.md`（演示走查手册）。

架构口径（演示叙事的锚）：**主数据"存"本体（漏斗物化进 oo_*）· 实时下推（虚拟 bind，keyColumns 恰 1 列）是物化的对称替代（查询下发源库只读，不落 oo_）· 单据"映射查"（import/doc 只入定义，实例留业务库，explorer「在业务系统中查看」跳转）· Action 只写 oo_ 不碰业务表**。

## 七步方法论

### ① 场景设计

从用户给的业务域提炼：5~9 个对象类型、3~6 条关系、1 个接口 + 2~3 共享属性、3~5 函数、5~8 动作、2~3 场景视图、DAM 归组（域/应用/模块）。**覆盖度自查清单**（不全不收工）：
- [ ] 动作覆盖增（createObject）/删（deleteObject）/改（modifyObject）/建边（addLink）/断边（removeLink）五种编辑原子
- [ ] 至少 1 个 FEEL 函数、1 个 Rhai 函数、1 个 aggregation 函数
- [ ] 至少 1 条 ≥2 跳下钻链（如 供应商→物料→合同）
- [ ] 每条关系 backing 优先 FK：外键属性存**对端主键**（backing 省略 targetProperty 即严格 Palantir 语义；外键值与对端 pk 不同型才显式 `targetProperty`）；多对多须有真实连接表（joinTable）或中间对象（intermediary）支撑、不硬造——零 backing 的关系落 ol_edge 边表，破坏「凡关系必有字段关联」叙事（口径细节见 references/scenario-spec.md backing 段）
- [ ] 动作 parameters 表完整（name/type/required + 示例值），供演示时照填；**object 参数必须带 `objectType`**——保存时自动派生进 `om_action_type.target_object_types`（物化列，勿手写），workshop 动作中心据此做“适用于当前类型”分区与选中对象自动绑定；纯 string pk 参数的动作 targets 为空，不会进该分区
- [ ] 至少 1 个动作的 validations 引用 `objects.<object参数>.<属性>`（对象状态校验），演示“仅 open 状态可提交”类拦截
- [ ] 每条实例数据都有讲解意义（正式中文企业数据，不用 foo/bar）

### ② 元数据桥接决策树

先问「业务系统里已有什么」：
- **简单字典**（币种/单位等 code+name）→ 规格写 `dctImports` 段（import/dct：建参照类型 + 字典项当场物化为对象）。
- **富属性主数据**（供应商/物料等，业务库已有表）→ 二选一，物化/虚拟对称：
  - **物化漏斗**（要落库可写、可隔离区演示）→ 规格写 `funnelMappings` 段：sourceQuery 可用 SQL CASE **派生**演示列（rating/onTimeRate），可 UNION 一行坏数据演示隔离区拦截，也可留空走生成式默认路径（resource+映射自动生成 SELECT）；跨业务库读源须 `sourceId`（注册源，优先）或 `sourceDbId`（本体 toml `[[databases]]` 段，见坑表）。注意：**sourceQuery 只读，漏斗 sync 会整体覆盖对象 props**。
  - **虚拟直查**（只要实时只读下推、不落库）→ 规格写 `datasourceBind` 段（`POST /object-types/datasource/bind`，mode=virtual；keyColumns **恰 1 列**；查询实时下推源库，不产 oo_ 数据）。注册源先 `POST /data-sources/create`（密码走 passwordEnv）。
- **本体扩展实体**（仓库/合同等业务系统没有的）→ 规格写 `objectTypes` + `objects` 段原生建模。
- **单据**（订单/凭证）→ 规格写 `docImports` 段（import/doc：单对象模型，行折叠为嵌套层块属性，不产关系不导实例）；要页面看真实数据需另 deploy DOC 元数据到业务库（参考 examples/procurement/seed_po_docs.py 头注释与 cmx-model deploy API）。

### ③ 业务侧落地（可选，视场景）

业务库需要表/单据数据时：deploy DCT/DOC（`POST {model}:8093/api/model/deploy`，db_id 指业务库）→ `/api/doc/save` 灌单（注意 `doc_type_id`/`entity_id` 等公共字段集必填；**信封 code==0 不代表成功，必须查 `data.ok` 与 `violations`**）→ `/api/dct/save` 补主数据（bucket 键=dictCode）。

### ④ 本体造数

```bash
python3 .agents/skills/cmx-onto-toolkit/scripts/onto_seed.py \
  --spec <scenario-spec.json> [--base http://127.0.0.1:8097] \
  [--api-key cmx_sk_dev_...] [--ontology default_ontology] \
  [--skip funnelSync,links] [--only objectTypes,functions]

> M1 起全部 onto 接口必带 `?ontology=`（脚本 `--ontology` 缺省 default_ontology）；批量写对象与漏斗同步已去路径化（`POST /objects/save-batch`、`POST /funnel/sync`）。目标本体不存在先注册：`POST /ontologies/create {apiName, displayName}`（多本体隔离先例：收入确认场景独立 finance_rev 本体，与采购域 default_ontology 互不可见——**一场景一本体**是推荐隔离粒度；oo_ 表物理共享、行内 `ontology_id` 列隔离，同名类型跨本体可共存）。
```
写规格前必读 `references/scenario-spec.md`（schema 契约）与 `references/ontology-api.md`（接口速查）。

### ⑤ 流程闭环（可选，最有演示价值）

两套现成闭环（详细 curl 骨架见 `examples/procurement/walkthrough.md`）：
- **Loop⑤ 主数据治理闭环（全现成）**：门户 MDM 提准入 CR → `POST /api/mdm/change-requests/submit` → 待办中心页面审批（或 `/api/mdm/change-requests/review`）→ MDM 自动激活写字典表（编码引擎铸号）→ 漏斗 sync → 本体可见。
- **Loop⑥ action 发起流程闭环（需本仓 outbound+flow-callback 支持，见坑表）**：本体动作 execute（sideEffects startBusinessProcess）→ `POST /action-outbox/dispatch`（**无 poller 必须手动**）→ flow 实例 → 待办中心审批 → webhook（service_key 目录模式）→ onto `POST /api/onto/v1/flow-callback` → 对象 reviewStatus 回写。
- 流程定义/审批定义部署用技能 **cmx-flow-toolkit**（P0 契约：BPMN 零审批属性，审批定义必配，USER value=用户 id）。

### ⑥ 验证

API 级：漏斗 SyncReport 三数（read/written/quarantined）、4 类函数各 evaluate 一次、动作 dry-run（含校验拦截负例）、≥2 跳对象集查询、聚合。页面级：studio（场景画布/Inspector/动作试算执行/函数求值）、explorer（类型树/过滤/钻取/单据跳转按钮）、workshop（360/动作中心“适用于当前类型”分区 + 对象自动绑定 + 试算 diff）。

### ⑦ 走查手册

产出 `walkthrough.md`：每幕页面→点击路径→讲解要点→curl 备份；**写明演示顺序约束**（见坑表第 1 条）。

## 清库（重建演示环境）

```bash
psql "$ONTO_DB_URL" -c "TRUNCATE om_object_type, om_link_type, om_interface, om_shared_property, om_action_type, om_function, om_view, om_policy, om_source_mapping, om_version, om_maintainer, oe_action_log, oe_outbox, ol_edge; DELETE FROM oo_quarantine;"
psql "$ONTO_DB_URL" -c "DO \$\$ DECLARE t text; BEGIN FOR t IN SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename LIKE 'oo\_%' ESCAPE '\' LOOP EXECUTE format('DROP TABLE IF EXISTS %I', t); END LOOP; END \$\$;"
# 注意：oo_quarantine 前缀也是 oo_，会被上面循环误删——删后按 DDL 重建（见 cmx-onto-store-pg/src/ddl.rs），或服务重启时预热自动重建。
```
清库前 `pg_dump` 备份；**只清本体库，业务库（fico 等）只增不清**。

> **多本体注意**：上面 TRUNCATE 清的是**全部本体**的定义（om_* 表按 `ontology_id` 列区分本体）。只想清某一个本体：`DELETE FROM <om_表> WHERE ontology_id='<apiName>'`（oo_ 行同理：`DELETE FROM oo_<type> WHERE ontology_id=…`）；`om_ontology` 注册行与 `om_data_source` 注册源不在清库列表，保留。

## 常见坑（实战教训）

| 坑 | 正解 |
|---|---|
| 演示顺序：漏斗 sync 覆盖对象 props | Loop⑥（评审状态回写）必须排在**最后一次漏斗 sync 之后**，否则 reviewStatus 被清 |
| 漏斗跨库 | sourceQuery 只在本体同库执行；跨库须 sourceDbId（代码已支持）+ toml [[databases]] 段 + **`ALTER TABLE om_source_mapping ADD COLUMN IF NOT EXISTS source_db_id`**（老库 TRUNCATE 不刷表结构） |
| flowApiKeySet=false | onto toml 缺 `[onto] flow_api_key`；用 `GET /action-outbox/config` 冒烟；改 toml 后必须经 launcher 重启（确认 `injected` 非空，否则回落 .env 的 dev 配置连错库——manifest 类型数可鉴别） |
| webhook 回调 401 | 订阅用 service_key 目录模式（`[service_rpc.services] onto` + `[service_auth] outgoing_api_key`，值=onto api_keys），勿用 target_url 直连（不带鉴权头，401 直进 DEAD）；业务键未知返 200+skipped 防 DEAD 污染 |
| CR 经 API 创建后发起流程 initiator='0' | 服务身份创建单据 create_by 空 → apply 任务派给幽灵用户。演示日走 MDM 页面创建 CR（登录态天然正确）；API 造的 CR 需 `UPDATE cv_mdm_apply SET create_by=<用户id>`（且实例已起则要 cancel 重提） |
| MDM review 用门户 JWT 报「不是审批人」 | MDM 从 **X-Delegated-User-Token** 取用户身份（HS256 sub=用户 id，密钥=flow toml jwt_secret），不吃 Authorization |
| Rhai 脚本 `let mut` 报语法错 | 该引擎 Rhai 配置不认 mut——用 if 表达式风格（`let x = if cond { a } else { b };`），末表达式即返回值 |
| 聚合函数 evaluate 报「须提供 objectSet」 | 传**顶层单数** `objectSet`（不是 objectSets 映射），配 `aggregation:{kind:"groupSum",groupBy,sum}` |
| doc/save 灌单 0 行但 code=0 | 信封成功≠保存成功；校验失败在 `data.ok=false + data.violations`；公共字段集 doc_type_id/entity_id 必填 |
| dct/save bucket | changes 的键必须用 **dictCode**（如 "supplier"），且 mdm 治理字段（published_version/lifecycle_status）必填 |
| launcher 重启 | `POST {sid}/restart` 用的是**保存的 toml 设置**；显式传 toml 前先 `PUT /settings`，看响应 `injected` 字段确认 |
| 外部进程占 8097 | launcher 重启杀不掉用户手动起的进程——先 `ss -tlnp \| grep 8097` 找 pid kill 再走 launcher |
| studio ⚠1 告警 | 状态栏 ⚠ 计数来自类型定义校验（如 PurchaseOrder 嵌套层块），演示前看一眼 Inspector 消除 |
| FK 关系遍历查不出数据 | 外键值与对端 pk 不同型（外键存代理 id、对端 pk 是业务键）——显式 `backing.fk.targetProperty` 指向对端真实存放的属性，或改数对齐；一跳便捷端点 `POST /objects/links`（`{objectType, pk, link}`）快速鉴别 |
| 对象保存后画布不刷新（studio） | 20260915 已修（保存后 overlay 清单 + 重渲画布）；若遇旧页面先强刷 |
| 动作 logic 落库成 `[null]` | om_action_type.logic 必须是干净对象数组：空编辑集写 `[]`，禁止 null/`[null]`（脏项让 studio Inspector 渲染崩、执行解析挂）；onto_seed.py POST 前自动剔除，DB 手修参照 `UPDATE om_action_type SET logic='[]' WHERE api_name='…'` |
| pipeline-status 查不到/404 | 参数名是 **snake_case `object_type`**（PipelineQuery 无 rename_all）：`?objectType=` 静默丢值返回空，路径段写法 `/funnel/pipeline-status/{type}` 直接 404；正解 `GET /funnel/pipeline-status?object_type=<apiName>`（20260920 实战教训） |
| 虚拟直查 bind 400 | BindReq.keyColumns **恰 1 列**（pk 桥接 + 固定排序靠单列锚）；多列联合主键是物化映射的能力。resource 必填（schema.table）；mode 只接受 "virtual"，物化走 mappings/save 无须 bind |
| 注册源 probe unreachable | om_data_source.config 只存 `passwordEnv`（环境变量名，如 ONTO_SRC_FICO_PW）不落明文——先确认该变量在 onto 进程环境里；`GET /data-sources/schema` 只认注册源 id，toml db_id 的反射走 `POST /data-sources/probe` |
| 多本体造数落错域 | 接口/脚本不带 `--ontology` 一律落 default_ontology；先 `POST /ontologies/create` 注册目标本体再 `--ontology` 指定。oo_ 表行内 `ontology_id` 隔离，同名类型跨本体可共存；漏斗映射 `sourceId` 优先于 `sourceDbId`（`source_id`/`source_db_id` 双读） |

## 交付约定

- 场景规格 + walkthrough 归档 `examples/<场景名>/`；脚本产物不落 git（按仓库规则等明确指令）。
- 汇报必须含：漏斗三数、函数求值结果、动作 dry-run 证据、双闭环各端到端一次的实测记录。
