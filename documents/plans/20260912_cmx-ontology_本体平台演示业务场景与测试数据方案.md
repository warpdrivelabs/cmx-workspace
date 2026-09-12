# CMX 本体平台演示方案——采购供应链·元数据双落与流程闭环

> 文档信息：2026-09-12 编制 ｜ 演示时间 2026-09-13（周日）｜ 状态：已定稿待实施
> 附属产物（实施期产出，均**不提交 git**）：技能 `.agents/skills/cmx-onto-toolkit/`、cmx-flow-toolkit 修订、演示数据、走查截图
> 本文档定位：演示准备工作的唯一真源，防遗忘清单 + 实施手册 + 审查记录。

---

## 一、目标与背景

周日向业务/领导演示本体平台（cmx-ontology），需要一个真实企业业务场景贯穿全部能力。经确认：

- **业务场景**：采购供应链协同（用户拍板）。
- **数据量级**：精选演示级（~40 对象 + ~80 关系边，每条数据都有讲解意义）。
- **架构口径（用户明确）**：**单据数据不入本体平台，只有字典（主数据）数据入本体**；本体查看单据=下钻业务库；单据审批通过后由流程回调 MDM → MDM 触发数据写入字典表 → 再发送到本体平台（漏斗），本体存的是字典。北极星方案见博客 `https://blog.csdn.net/warpdrivelabs/article/details/164810238`（主数据"存"·单据"映射查"·RPT"算"；oo_ 只有两个写入者=漏斗+Action；Action 只写 oo_ 不碰业务表）。
- **完整闭环诉求**：单据可走流程引擎；在本体平台通过 action 发起流程；流程审批完成后通过副作用回写。
- **技能诉求**：新技能必须是**指导 AI 如何为任意业务场景生成本体演示数据的方法论**，而非一次性造数器；顺带完善已过时的 cmx-flow-toolkit。

覆盖能力映射：类型定义（幕③）、关系（幕③④）、函数调用（幕④）、action 调用（幕④⑥）、数据下钻（幕④）、数据关系（幕②④）、元数据双落（幕①②）、流程闭环（幕⑤⑥）。

---

## 二、关键环境信息（防遗忘清单）

### 2.1 服务拓扑（全部已运行，生效配置均为 `*-test.toml`，进程 env 覆盖各仓 .env）

| 服务 | 端口 | 数据源 | 备注 |
|---|---|---|---|
| cmx-portal-server | 8080 | primary=`192.168.137.111:5432/cmx`（IAM/菜单）；biz=**fico-db**=`192.168.137.111:5432/fico` | `[service_rpc.services]` 已含 flow/mdm/model/onto 反代 |
| cmx-model-server | 8093 | 同 portal 双库 | 元数据中心，deploy 入口 |
| cmx-mdm-server | 8095 | primary=`192.168.157.46:5432/test1`；fico-db(biz)=fico | `[mdm.flow]` definition_key=mdm_cr_approval、webhook_secret=`mdm_flow_hook_dev_secret` |
| cmx-flow-server | 8091 | fico-db（cmx_flow_* 全套在 fico 库） | **当前无任何已发布流程、事件订阅表为空；`[service_rpc.services]` 只有 mdm；无 `[service_auth]` 段** |
| cmx-onto-server | 8097 | onto_pg=`192.168.137.111:5432/cmx_onto` | **演示库，可全清**；无 `[onto]` 段、ONTO_FLOW_API_KEY 未配（action-outbox/config 实测 flowApiKeySet=false） |

**业务表（cm_*/cv_*）全部建在 fico 库（db_id="fico-db"）**。数据库账号：`postgres / Pg@Pansoft_0909`（137.111）。

### 2.2 前端页面（门户 dev http://127.0.0.1:5173，反代 :8080；登录 admin/Admin@12345）

| 路由 | 页面 | 源码 |
|---|---|---|
| `/view/onto-studio` | 本体工作室（场景画布/目录/场景管理/Inspector/双轨发布/版本中心/⌘K） | `backend/cmx-container/assets/onto/web/ui-native/onto/studio.js` |
| `/view/onto-explorer` | 对象浏览器（DAM 类型树/对象集构造器/列表/Search-Around 钻取面包屑） | 同目录 `explorer.js` |
| `/view/onto-workshop` | 对象360（类型组合框/360 关系块/动作中心带参 dry-run+执行） | 同目录 `workshop.js` |
| 门户 MDM 菜单 | 主数据列表 + 变更申请 cr-form | `backend/cmx-container/assets/mdm/web/ui-native/portal/mdm/` |
| 门户「待办中心」 | 审批（现成菜单已同步 cmx_menu） | `backend/cmx-flowengine/web/ui-native/flow/todo-center.js` |
| `portal.model.doc.doc-loader` | 通用单据查看页（props: domain/application/module/file/dbId/apiPath） | `backend/cmx-container/assets/model/web/ui-native/portal/doc/doc-loader.js`；菜单接线范例 `assets/model/data/menu-pages/fi/cmxfico/gl/explorer-menu.json:2483` |

### 2.3 API 与鉴权

- onto：`/api/onto/v1/*`；flow：`/api/flow/v1/*`；统一免登录头 `X-API-Key: cmx_sk_dev_A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6`。
- flow 办理类端点（complete/reject/claim…）需要用户身份：页面操作走登录态；curl 需 `X-Delegated-User-Token: Bearer <JWT>`（HS256，sub=用户 id，须带 exp，密钥 `a7k9m2p4x8q1w5e3r6t0y7u2i9o4p1`）。
- **审批定义 objects 的 `USER` value 必须填用户 id**（identity.rs 原样作 user id；待办按 assignee 精确相等比对）：**admin = `7503326638169403392`**。mdm_approver 角色（id=1898765432100001101）现仅 javier 在角色内，javier 密码为批量初始化 pansoft+强制改密（不可靠）→ **演示审批统一用 admin**，需给 admin 补角色（见 §八-5）。
- 服务重启走 launcher：`POST http://127.0.0.1:8100/api/services/{sid}/restart`（onto 的 sid=`cmx-ontology`，已保存 toml=onto-server-test.toml + args=--release）；日志 `GET /api/services/{sid}/logs?since=0`。

### 2.4 MDM CR 闭环现状（fico 库实测）

- `mdm_activation` 已配 `gys__create`/`gys__update` 激活映射（header_mapping: name/phone/tax_no/short_name/credit_code）；`cm_supplier` 8 行（SUP0001~）；`cv_mdm_apply` 0 行。
- CR 状态机 draft→approving→activating→activated；提交 `POST /api/mdm/change-requests/submit {crId}`（自动起流程，org_id 硬编码 org-root）；审批 `POST /api/mdm/change-requests/review {crId, action:"approve", comment}`（内含主动回写，不依赖 webhook）；审批通过**自动激活写 cm_supplier**（无需人工应用）。
- 流程部署：`bash backend/cmx-flowengine/data/deploy-mdm-flow.sh`（六步幂等：draft→validate→publish→forms/save→approval-defs/save；review 节点=ROLE mdm_approver；role 解析不受 USER id 口径影响）。

### 2.5 本体平台关键行为

- **导入**：`POST /import/dct`（参照类型 code/name + 字典项当场物化为对象，幂等）；`POST /import/doc`（**单对象模型**：整单→1 个对象类型、子层折叠为嵌套层块属性、不产关系、不导实例，cmx_origin 溯源）。
- **漏斗（funnel）**：`POST /funnel/mappings`（objectType/sourceQuery=原生 SQL/keyColumns/titleColumn/propertyMap/required）+ `POST /funnel/sync/{type}`（全量同步，违规入 oo_quarantine，返回 SyncReport{read,written,quarantined}）。**source_query 当前仅能在 onto_pg 同库执行**（FunnelStore 全部方法吃单一 db_id）→ 跨库读 fico 需 §五-2 小开发。
- **单据直连下推未实现**（ObjectTypeDef.datasource 纯占位、compile.rs 只产 oo_*/ol_edge SQL）→ 演示口径=单据**定义**入本体（溯源）+ 类型层跳转业务系统查看。
- **动作**：logic 五原子 createObject/modifyObject/deleteObject/addLink/removeLink + `$参数` 递归替换；validations 为 FEEL 谓词**但上下文只含参数**（看不到对象状态）；副作用六类，经 oe_outbox 异步，**需手动 `POST /action-outbox/dispatch`**（无 poller）。
- **函数**：FEEL / Rhai / aggregation 三运行时；`POST /functions/{api}/evaluate`（args/objects/objectSets）。
- **outbound 断链（须修复）**：`outbound.rs:15` 起流程用旧路径 `/api/flow/v1/instances`（实际 `POST /instances/start`）；`:194` 定义列表用 GET（实际 `POST /definitions/list`）；缺 flow_api_key 配置。

### 2.6 流程引擎当前契约（P0 后流程定义×审批定义完全分离）

- 流程定义：`cmx_flow_definition(_version)`，BPMN 全局 key；**BPMN 审批属性一律 warn+忽略（静态 assignee 不豁免）**。
- 审批定义：`cmx_flow_approval_def(_version)`，PK(def_key, org_id)；`POST /approval-defs/save {defKey, orgId, content:{nodes:{<bpmnId>:{inherit,mode,objects:[{kind,value}],emptyPolicy}}}}`；**发起闸对全部 userTask 节点按 (defKey×orgId) 沿组织祖先链解析，任一缺失 400 拦截**。
- 部署序列：validate→draft（key 由 process id 派生）→publish（热装载，`{key,note}`）→approval-defs/save（必做）→forms/save（可选，无 formKey 任务走待办中心通用办结 UI）。
- 发起 `POST /instances/start {definitionKey, businessKey?, orgId?, variables?, bizLink?}`；orgId 缺省回退发起人主属组织（**admin 若无主属组织会 400，见 §十-风险4**）。
- 事件订阅：`POST /event-subscribers/save {name, channel:"webhook", channelConfig:{service_key|target_url, callback_path?, secret(必填)}, rules:[{eventTypes, keyPatterns}], active}`；service_key 模式经 `[service_rpc.services]` 目录**自动注入 X-API-Key**（值=`[service_auth].outgoing_api_key`，flow toml 当前缺该段）；**target_url 直连不带任何鉴权头**；401 类 4xx 直进 DEAD 不重试。
- tasks/complete 等全 **camelCase**；`GET /definitions/{key}` 不存在（用 `POST /definitions/detail`）。

### 2.7 已知边界（演示时属正常，不算 bug）

studio 画布拉线锚点仍钉属性行（浮动锚点方案已拍板未实施）；workshop 动作执行 actor/subjects 硬编码 role:admin（真实写库，先 dry-run）；`om_maintainer` 空表=全员可编辑/发布；doc/save 不校验单据状态机（话术定位"批量初始化通道"）；`/events` SSE、403 降级等 studio 行为见工作室方案。

---

## 三、演示故事线（六幕）

| 幕 | 主题 | 演示内容 | 依赖能力 |
|---|---|---|---|
| ① | 元数据同源（业务系统） | MDM 现成字典 + 新建采购订单 DOC deploy 到 fico 业务库；doc/save 灌 10 张正式订单；psql/doc-loader 展示业务表数据 | model deploy、doc/save |
| ② | 字典入本体 | 简单字典 import/dct；供应商富属性走漏斗（源映射→sync，演示 SyncReport 与隔离区拦截违规行）——**本体只存字典** | import/dct、funnel 跨库 |
| ③ | 工作室建模治理 | 原生补齐 Warehouse/Contract、5 条关系、接口+共享属性、4 函数、8 动作、2 个场景画布；编辑态改模型→保存草稿→发布中心 diff→发布 v1→版本中心回看 | studio 全能力 |
| ④ | 数据服务 | explorer 类型树/过滤构造器/多跳下钻；workshop 对象360+动作中心带参 dry-run+执行；函数求值；采购订单单据类型溯源+「在业务系统中查看」跳 doc-loader 看**真实单据行**（类型层跳转） | 三本体页 |
| ⑤ | 主数据治理闭环 | 门户 MDM 提供应商准入 CR → 提交起流程 → **admin 在待办中心页面审批通过** → MDM 自动激活写 cm_supplier → 漏斗 sync → 本体立即可见新供应商 | MDM+flow+funnel（现成） |
| ⑥ | 本体 action 发起流程闭环 | 本体动作 submitSupplierReview → dispatch → supplier_review 实例 → 待办中心审批 → webhook 回调本体 → 供应商 reviewStatus 更新（360 立即可见） | 修复后的 outbound+flow-callback |

---

## 四、业务模型设计

### 4.1 对象类型（DAM：域 supplychain → 应用 procurement/warehouse → 模块 supplier-mgmt/execution/inventory）

| 类型 | 归属 | 主键 | 标题 | 关键属性（baseType） |
|---|---|---|---|---|
| Supplier 供应商 | supplier-mgmt | supplierCode | name | name、level(string 等级)、rating(double 评分)、riskLevel(string)、onTimeRate(double)、region、contactPerson、contactPhone、status(合作中/暂停/评审中)、**reviewStatus/lastReviewAt（Loop⑥ 落点）**、+共享属性×3 |
| Material 物料 | supplier-mgmt | materialCode | name | name、category、spec、unit、safetyStock(long)、refPrice(double)、status、+共享属性×3 |
| Warehouse 仓库 | inventory | warehouseCode | name | name、type(原料库/立体库)、address、manager、area(double)、+共享属性×3 |
| Contract 采购合同 | execution | contractNo | name | name、supplierCode、supplierName、signDate(date)、amount(double)、status、+共享属性×3 |
| Employee 员工 | execution | empNo | name | name、department、position、phone |
| Currency/UOM/PaymentTerm | 字典导入 | code | name | 仅 code/name（import/dct 参照类型形态） |
| PurchaseOrder 采购订单 | **仅定义**（import/doc，含嵌套行属性，不物化） | id | orderNo | doc_no/order_date/expected_date/status/buyer/currency/total_amount/remark + 嵌套行块（line_no/material_code/qty/unit_price/amount/received_qty） |

共享属性（接口「可治理主数据 GovernedMaster」要求，Supplier/Material/Warehouse 实现）：`lifecycleStatus`(string)、`sourceSystem`(string)、`governedBy`(string)。

### 4.2 关系（5 条，均 edge backing）

| 关系 | 端A | 端B | 基数 | 角色 |
|---|---|---|---|---|
| supplierOf 供应 | Supplier | Material | manyToMany | 供应 / 由…供应 |
| signContract 签约 | Supplier | Contract | oneToMany | 签订 / 归属供应商 |
| coverMaterial 覆盖物料 | Contract | Material | manyToMany | 覆盖 / 用于合同 |
| storeIn 存放 | Warehouse | Material | oneToMany | 存放 / 存于 |
| buyerOf 采购对接 | Employee | Supplier | oneToMany | 对接 / 对接人 |

### 4.3 函数（4）

| 函数 | 运行时/kind | 输入 | body 要点 |
|---|---|---|---|
| supplierGrade | FEEL/derivedProperty | supplier:object | `if supplier.rating >= 4.5 then "A" else if … >= 3.5 then "B" else if … >= 2.5 then "C" else "D"` |
| supplierRiskScore | Rhai/derivedProperty | supplier:object | 100 − 风险等级扣分(高40/中20) − 准时率缺口×200 − 低分扣 15，下限 0 |
| contractSpendBySupplier | aggregation | contracts:objectSet | `{groupBy:"supplierName", sum:"amount"}`（求值时顶层传 objectSet+aggregation） |
| materialFullLabel | FEEL/derivedProperty | material:object | `material.category + " / " + material.name + "（" + material.unit + "）"` |

### 4.4 动作（8；必演 5 + 备演 3）——动作参数手册

> 执行：`POST /api/onto/v1/action-types/{api}/dry-run|execute`，body `{"params":{…},"actor":"demo"}`；执行后 `POST /action-outbox/dispatch` 触发副作用投递。

| 动作 | 参数（name:type\*,必填） | logic 编排 | validations（仅参数可见） | sideEffects |
|---|---|---|---|---|
| submitSupplierReview 提交供应商评审 | supplierId:string\*（=对象 pk，如 SUP0001） | modifyObject Supplier $supplierId set{reviewStatus:"评审中", status:"评审中"} | —（参数上下文看不到对象状态） | startBusinessProcess：flowDefKey=supplier_review、businessKey=$supplierId、variables{initiator:"admin", supplierName} |
| pauseSupplier 暂停合作 | supplierId:string\*、reason:string\* | modifyObject set{status:"暂停", remark:$reason} | — | notification（模板=供应商暂停通知） |
| adjustSupplierRating 调整评级 | supplierId:string\*、newRating:double\* | modifyObject set{rating:$newRating} | newRating>=0 && newRating<=5 | — |
| createMaterial 新增物料 | materialCode:string\*、name:string\*、category:string\*、unit:string\*、supplierId:string\* | createObject Material pk=$materialCode title=$name props{category,unit,status:"启用"} + addLink supplierOf $supplierId $materialCode | — | — |
| adjustSafetyStock 调整安全库存 | materialId:string\*、newStock:long\* | modifyObject set{safetyStock:$newStock} | newStock>=0 | — |
| linkSupplier 建立供应关系 | supplierId:string\*、materialId:string\* | addLink supplierOf $supplierId $materialId | — | — |
| unlinkSupplier 解除供应关系 | supplierId:string\*、materialId:string\* | removeLink supplierOf $supplierId $materialId | — | — |
| removeDraftMaterial 删除草稿物料 | materialId:string\* | deleteObject Material $materialId | —（手册注明：执行前人工确认草稿态） | — |

### 4.5 场景视图（2 个）

「供应商主数据」（Supplier/Material/Contract/Employee + 关系）、「物料与采购协议」（Material/Warehouse/Supplier/Contract）。造数后各预置布局（POST /views/layout），并基线发布 v1（版本中心有内容可看）。

### 4.6 业务侧数据（fico 库）

- **采购订单 DOC**：新建 `assets/model/data/meta/definitions/basic/dataplatform/purchase/purchase_doc_meta_v1.json`，两层 `cv_po_order`（doc_no/doc_date/supplier_code/supplier_name/buyer/expected_date/currency/total_amount/doc_status/remark）+ `cv_po_line`（line_no/material_code/material_name/qty/unit_price/amount/received_qty，upper_id 挂头）；状态字段值域 draft/submitted/approved/partial_received/completed/closed（状态机定义仅作文档展示，保存链路不校验）。
- **灌数**：`POST http://127.0.0.1:8080/api/doc/save?domain=basic&application=dataplatform&module=purchase`，changeset 形状（inserted[{id:"T1",fields:{…}}] / 子行带 upper_id），10 张单覆盖全部状态；doc_no 直接给值（PO-2026-0001…，不走编码引擎）。
- **供应商补充**：`/api/dct/save`（dict=supplier）补 2 家正式供应商（如「杭州东华链条集团」「南京高精齿轮集团」），使漏斗 sync 后本体 Supplier=10。
- **CR 预置**：doc/save 建 2 张 `cv_mdm_apply` 草稿（doc_type=gys、cr_type=create、target_dict_code=supplier、payload 含 name/short_name/tax_no/credit_code/phone，如「温州精密锻件有限公司」），记录 crId；现场一张走页面演示、一张备用。
- **admin 补角色**（幂等模板出自 `backend/cmx-container/docs/sql/v2/platform/init_dml.sql:142-151`，勿裸 INSERT——cmx_user_role 无组合唯一约束）：按 username='admin' SELECT id + NOT EXISTS 防重，插入 (用户 id=7503326638169403392, 角色 id=1898765432100001101)。

### 4.7 演示数据清单（本体侧）

Supplier×10（漏斗）、Material×12、Warehouse×3（华东原料一库/二库/成品库）、Contract×3（2026年度钢材框架/电子元器件/包装材料采购合同）、Employee×5（王建国/李晓峰/张雅雯/刘志强/陈静）、字典 Currency×4/UOM×5/PaymentTerm×4；关系边约 80（供应 30、签约 3、覆盖 12、存放 18、对接 10）。全部正式中文企业数据。

---

## 五、代码与配置改动清单（cmx-ontology 仓为主，全部小改动）

1. **outbound 修复**（`crates/cmx-onto-app/src/outbound.rs`）：`FLOW_INSTANCES_PATH`→`/api/flow/v1/instances/start`；`list_flow_definitions` 改 `POST /definitions/list` body `{}`（执行时验证 handler 兼容，不通则前端 datalist 降级自由输入，已容错）。
2. **漏斗跨库**：`cmx-onto-model` 的 SourceMapping 增 `sourceDbId`（可空=onto_pg）；`ddl.rs` 预热追加 `ALTER TABLE om_source_mapping ADD COLUMN IF NOT EXISTS source_db_id VARCHAR(64)`（**必须，TRUNCATE 不刷表结构**）；`funnel_store.rs` upsert/load/list 三处读写新列；`run_full_sync` 读源换 source_db_id（`query_sql_with_params` 首参）、写 oo_/隔离区仍走 onto_pg（不拆双连接）；handler/映射 payload 增可选 `sourceDbId`；`onto-server-test.toml` 增 fico-db `[[databases]]` 段。改法经审查确认 ~40-80 行。
3. **新增 `POST /api/onto/v1/flow-callback`**（~80 行，handler 归 cmx-onto-app）：正常鉴权路由（鉴权靠 flow 侧注入的 X-API-Key，无需白名单）；HMAC-SHA256 验签 `x-cmx-flow-signature`（secret 与订阅一致）；仅处理 instance.completed；按 businessKey（=Supplier pk）`modify_with_optlock(type, pk, set{reviewStatus:"已通过", lastReviewAt:now}, None)`；businessKey 未知→200+`{skipped:true}`（防 DEAD 污染）。
4. **toml 改动**（走 config-sync 同步模板/手册）：onto-server-test.toml 新增 `[onto]` 段 `flow_api_key = "cmx_sk_dev_…"`；增 fico-db `[[databases]]`；**flow-server-test.toml 补两段（关键路径）**：`[service_rpc.services] onto = { url = "http://127.0.0.1:8097" }` 与 `[service_auth] outgoing_api_key = "cmx_sk_dev_…"`（与 onto api_keys 同值）。
5. **explorer.js + 门户菜单**：单据类型详情面板按 cmx_origin/docType 渲染「在业务系统中查看」→ window.open 预置工作区节点（menu-pages JSON 增 PO 查看节点挂 `portal.model.doc.doc-loader`，props 带 `dbId:"fico-db"` + domain/application/module/file）→ `scripts/sync_menu_db.py` 同步 cmx_menu。
6. **验证纪律**：cmx-ontology `cargo check` + launcher 重启 onto/flow；**双仓 check 取消**（已证实 cmx-container 对 cmx-onto-app 零依赖）；冒烟断言：`GET /action-outbox/config` flowApiKeySet=true、漏斗跨库试读 fico 行数、flow-callback 试投 `/event-subscribers/test`。

---

## 六、cmx-flow-toolkit 技能完善（先行，流程部署依赖它）

1. **scripts/create_flow_def.py**：① 停止生成 BPMN 审批属性（flowable:assignee/candidateUsers/candidateGroups、cmx:candidates/cc、multiInstanceLoopCharacteristics——编译器忽略且违反 P0 契约）；② 部署链路补 `approval-defs/save`（必做）与 `forms/save`（可选）；③ 修 publish（`/definitions/{key}/publish`→`/definitions/publish`+body key）、发起（`/instances`→`/instances/start`）、取消（→`POST /instances/cancel` body {id}）、探测（`GET /definitions/{key}`→`POST /definitions/detail`）；④ spec 增 approvalDefs 段（nodes→objects[{kind,value}]/mode/emptyPolicy，**USER value 填用户 id**）；冒烟前加 `/approval-defs/startable` 预检。
2. **references/bpmn-def-guide.md**：候选人七类改为审批定义 objects 语法；删「静态 assignee 回退」废契约（解析为空走 emptyPolicy INCIDENT/AUTO_PASS/ASSIGN）；部署契约表全面更新（含提交闸、startable/coverage、tasks/my）；claim/transfer 等 snake_case→camelCase。
3. **SKILL.md**：模式A 链路更新为 validate→draft→publish→approval-defs→forms(可选)→start→tasks/my→complete；补「P0 后发布≠可发起」；模式B manifest 补 approval_defs 提示。

---

## 七、新技能设计：`cmx-onto-toolkit`（方法论技能）

**定位**：指导 AI 为**任意企业业务场景**设计并生成本体平台演示数据的方法论+参数化工具链；采购场景仅是第一份范例（examples/procurement/）。

- **核心方法：场景规格驱动**——AI 先写「场景规格 JSON」（对象类型/属性、关系、接口/共享属性、函数、动作含参数表与 logic 编排、实例与关系边、DAM 归组、场景视图、漏斗映射、业务侧数据清单），再由工具脚本执行灌数，而非脚本写死业务。
- **SKILL.md 七步方法论**：①场景设计（业务域→类型/关系/动作提炼 + 覆盖度自查清单：增删改查动作齐、FEEL/Rhai/聚合三函数、≥2 跳下钻链、每条数据可讲解）；②元数据桥接决策树（已有 DCT/DOC？→ import/dct（简单字典）/漏斗（富属性主数据）/原生建模（本体扩展实体）；单据只入定义）；③业务侧落地（deploy+seed+doc/save）；④本体造数（规格→scripts/onto_seed.py）；⑤流程闭环（引 cmx-flow-toolkit + webhook 订阅 + 回调端点，含鉴权双段配置坑、审批人 value=用户 id 坑）；⑥验证（API 清单+浏览器走查）；⑦走查手册产出。
- **目录**：`scripts/`（onto_seed.py 规格驱动造数、onto_clean.py 清库、verify_onto.sh 闭环验证）；`references/`（ontology-api.md 接口速查、metadata-bridge.md 映射契约、scenario-spec.md 规格 schema、business-model-procurement.md 采购范例含动作参数手册）；`examples/procurement/`（本次规格+走查手册）。
- 造数过程踩坑实时写回 SKILL.md；**演示前只交骨架+可用脚本，定稿后置到演示后**（时间裁剪项）。

---

## 八、实施步骤（时间盒；关键路径=周六晚前完成 Loop⑥ 彩排，周日只走查不开发）

| # | 步骤 | 估时 | 档位 |
|---|---|---|---|
| 0 | 环境核对（launcher 查 5 服务；onto 连 cmx_onto；flow 定义/订阅空） | 0.5h | 必须 |
| 1 | `pg_dump` 备份 cmx_onto → /tmp（fico 只增不清） | 0.5h | 必须 |
| 2 | 清库：仅 cmx_onto——`TRUNCATE om_object_type, om_link_type, om_interface, om_shared_property, om_action_type, om_function, om_view, om_policy, om_source_mapping, om_version, om_maintainer, om_draft, oe_action_log, oe_outbox, oo_quarantine, ol_edge;` + `DROP` 全部 `oo_*`（pg_tables LIKE 'oo_%'） | 0.5h | 必须 |
| 3 | 完善 cmx-flow-toolkit（§六） | 3-4h | 必须 |
| 4 | 代码修复与重启（§五 1-4）→ cargo check → launcher 重启 onto+flow → 冒烟三项 | 3-4h | 必须 |
| 5 | 业务侧：PO DOC 元数据文件→deploy DCT+DOC（fico-db）→doc/save 灌 10 单→dct/save 补 2 供应商→预置 2 张 CR→admin 补 mdm_approver→PO 门户菜单节点+sync_menu_db.py | 2.5-3h | 必须 |
| 6 | 流程侧：deploy-mdm-flow.sh + 修好的 flow-toolkit 部署 supplier_review（BPMN 无审批属性；审批定义 review 节点 `{"kind":"USER","value":"7503326638169403392"}`，orgId 与发起实际 org 对齐，startable 预检通过）→ 2 条 webhook 订阅：①MDM：service_key=mdm + callback_path=/api/mdm/flow/callback + secret=mdm_flow_hook_dev_secret，eventTypes=[instance.completed, instance.terminated]；②onto：service_key=onto + callback_path=/api/onto/v1/flow-callback + secret=<新生成>，rules.keyPatterns=[supplier_review] | 1.5-2h | 必须 |
| 7 | 本体造数：import/dct→漏斗映射+sync（sourceDbId=fico-db）→原生建模→实例与边→函数/动作→场景+布局→基线发布 v1→import/doc PO 定义 | 4-5h | 必须 |
| 8 | 双闭环联调彩排：Loop⑤（提 CR→提交→待办审批→激活 cm_supplier→funnel sync→本体可见）；Loop⑥（动作 execute→dispatch→待办审批→回调→reviewStatus 更新）各端到端全通 | 2-3h | **关键路径（周六晚）** |
| 9 | 浏览器走查（control-browser 主代理亲自）：三本体页+MDM 提单+待办中心审批，全程截图，问题即修 | 1.5h | 必须 |
| 10 | cmx-onto-toolkit 骨架+本文档同步更新（定稿演示后补完） | 2h | 骨架必须 |

**Loop⑤ curl 骨架**：doc/save 建 CR 草稿（changeset cv_mdm_apply，payload 含 header_mapping 源字段）→ `POST /api/mdm/change-requests/submit {crId}` → 待办中心页面办理（打开 cr-form 审批）→ psql 查 `cm_supplier ORDER BY id DESC` 见新行 + CR=activated → `POST /api/onto/v1/funnel/sync/Supplier`（SyncReport written+1）→ explorer 查新供应商。
**Loop⑥ curl 骨架**：`POST /action-types/submitSupplierReview/execute {"params":{"supplierId":"SUP0002"}}` → `POST /action-outbox/dispatch` → flow 实例创建（`POST /instances/detail` 验证）→ 待办中心 admin 审批 → `GET /event-deliveries/query` 投递 DONE → `POST /object-sets/load`（filter reviewStatus=已通过）验证对象更新。

---

## 九、验收标准

1. cmx_onto 库只含本场景数据；六幕走查全通过。
2. 漏斗 SyncReport/隔离区可见；5 必演动作带参 dry-run+执行成功；4 函数求值正确；explorer 多跳下钻（供应商→合同→物料 ≥2 跳）。
3. PO 类型在 explorer 可见、溯源清晰、跳转 doc-loader 看到真实单据行。
4. Loop⑤⑥ 现场可复演（含待办中心页面审批、webhook 投递 DONE、对象状态更新可见）。
5. cmx-flow-toolkit 修正后一键部署新流程并可发起（supplier_review 实测）；cmx-onto-toolkit 规格驱动脚本可换场景复现。
6. 动作参数手册+演示走查手册随技能交付；方案与产物不进 git。

## 十、风险与降级预案

1. **漏斗跨库开发受阻**→降级 postgres_fdw（cmx_onto 建 FOREIGN TABLE 映射 fico.cm_supplier，零代码）；再降=影子表+脚本搬运（诚实标注）。
2. **flow-callback 开发受阻**→Loop⑥ 完成证据改 flow 投递流水（DONE+签名头）+动作 emitEvent 通知（studio SSE 可见），不阻断演示主线。
3. **`/definitions/list` POST 改造 handler 不兼容**→studio「起流程」下拉降级自由输入 flowDefKey（前端已容错），手动填 supplier_review。
4. **Loop⑥ 发起 400「缺审批定义/需显式 orgId」**→admin 主属组织缺失所致：按报错 orgId 补配审批定义；仍不通则给 outbound payload 增加可选 orgId 透传（+3 行，随 §五-1 一并改）。
5. **待办中心表单绑定问题**→supplier_review 不写 formKey（走通用办结 UI）；mdm.cr.review 绑定由 deploy 脚本负责。
6. **时间超支**→裁剪顺序：备演 3 动作→场景 2→1→explorer 跳转打磨→javier 双审批人画面（已裁）→技能定稿（已后置）。

## 十一、对抗性审查记录（第一轮，2026-09-12）

- **结论**：初审 6.5/10（有条件可演示）；3×P0+4×P1+3×P2 全部闭环如下；主智能体对 3 个 P0 独立抽查证实（identity.rs USER 原样作 id / flow toml 无 [service_auth] 段、services 仅 mdm / om_source_mapping 无 source_db_id 列且 store 单 db_id / outbound 旧路径 / cmx-container 零依赖 cmx-onto-app）。
- **P0 闭环**：①回调鉴权双断点（target_url 直连 401 且 401 直进 DEAD；service_key 模式 flow 缺出站密钥）→ §五-4 flow toml 双段+订阅改 service_key；②审批定义 USER value 必须用户 id → §2.3/§八-6；③漏斗加列需 ALTER 迁移 → §五-2。
- **P1 闭环**：[onto] 段为新增（冒烟断言 flowApiKeySet=true）；flow-callback businessKey=Supplier pk（modify_with_optlock 盲写放行）；explorer 跳转需预置门户菜单节点（menu-pages+sync_menu_db.py，props 带 dbId=fico-db）；admin 补角色用 init_dml 幂等模板；javier 不可靠不用。
- **P2 闭环**：双仓 cargo check 取消；doc/save 无状态机校验（话术规避）；PO 溯源=类型层跳转口径。
- **疑点裁决**（6 项，无遗留分歧）：①坚持 X-API-Key 注入，不临时 off onto 鉴权；②回调落字段=reviewStatus（独立属性，不与漏斗 propertyMap 冲突）；③PO 溯源不承诺对象↔行互跳；④definitions/list 改 POST 执行时验证、不通降级自由输入；⑤订阅按 keyPatterns 过滤+未知 businessKey 返 200；⑥Supplier 10=存量 8+dct/save 补 2。
- **时间评估**：净工作量 3.5-5 人日 vs 可用 2.5-3 → 三档裁剪后关键路径=§八-8（Loop⑥ 周六晚彩排）。

---

## 十二、实施记录（2026-09-12 实际执行结果）

### 12.1 代码分支与提交

- 代码改动落在 cmx-ontology 新分支 **`feat/onto-demo-flow-loop`**（自 feat/shared-props-pagination 切出）：
  - `31d6437` 演示闭环三件套：outbound 对齐 flow 新契约（/instances/start + orgId 透传 + POST definitions/list）、漏斗跨库读源（om_source_mapping.source_db_id，读源走业务库、写 oo_ 仍走本体库）、flow-callback 审批回调回写对象状态
  - `712f19a` flow-callback 审批通过顺带恢复 status=合作中
- explorer.js「在业务系统中查看」跳转（3 处）已由用户提交；新文件 `purchase_doc_meta_v1.json`、seed_po_docs.py 留存未跟踪。
- **架构变更注意**：父提交 `984de5b refactor!: 移除草稿/发布双轨，改为直改 live + 存档/回滚架构`——studio 现为「编辑直写 live + 存档检查点（POST /snapshots）+ 版本回看/对比/回滚」，幕③叙事已相应调整；draft/发布中心路由已移除。

### 12.2 流程与配置部署

- IAM（cmx@137.111）：种入根组织 `org-root`（集团总部，MDM 提交硬编码依赖）；admin（7503326638169403392）补挂 mdm_approver（幂等模板）。
- flow：supplier_review v2（BPMN 零审批属性 + 审批定义 review=USER 7503326638169403392@org-root）经修订后的 cmx-flow-toolkit 部署+冒烟全绿；mdm_cr_approval v1（deploy-mdm-flow.sh 六步）。
- 事件订阅 ×2：mdm-writeback（service_key=mdm）、onto-flow-callback（service_key=onto，keyPatterns=[supplier_review]）；试投 DONE。
- toml：onto-server-test.toml 增 `[onto]` 段 + fico-db `[[databases]]`；flow-server-test.toml 增 `[service_rpc.services].onto` + `[service_auth].outgoing_api_key`。
- 菜单：purchase-menu.json（doc-loader 挂「采购订单」查看节点）经 sync_menu_db.py 同步 cmx_menu（**顺带修复脚本 parse_url 不解码 %40 的 bug**）。

### 12.3 造数结果

- 业务库 fico：cv_po_order/cv_po_line 10 单 18 行（全状态覆盖）；cm_supplier 12 家（存量 8 + SUP0009/0010 补录）；2 张准入 CR（…032 彩排已耗 / …033 留演示）。
- 本体库 cmx_onto：共享属性 3 + 接口 GovernedMaster + 类型 9（含 3 字典参照 + PO 定义）+ 关系 5 + 函数 4 + 动作 8；漏斗 Supplier **read=12 / written=11 / quarantined=1**（SUP-BAD 隔离区拦截演示点）；Material 12 / Warehouse 3 / Contract 3 / Employee 5；边 48；场景视图 2；存档版本 v1；PurchaseOrder 定义（import/doc）。
- 验证：函数 4/4 求值通过（FEEL "A"、Rhai 93、聚合 groupSum、派生标签）；动作校验拦截/写回/复合编排/delete 全通过；三跳下钻（供应商→物料→合同反向）一条 SQL。

### 12.4 双闭环彩排实测

- **Loop⑥**：submitSupplierReview execute（effects=1）→ dispatch dispatched=1 → flow 实例 review 节点（businessKey=SUP0002）→ 委托令牌办结 → webhook 投递 → **SUP0002 reviewStatus=已通过 + lastReviewAt 回写** ✓
- **Loop⑤**：CR …032 submit（approving）→ apply 节点手动补办（API 建 CR 导致 initiator='0' 的坑，演示日走页面天然规避）→ MDM review approve（需 X-Delegated-User-Token，门户 JWT 不行）→ **CR activated + cm_supplier 铸号 SUP202609120001** → 漏斗 sync → 本体可见 ✓

### 12.5 浏览器走查（截图留档于会话工件）

- studio：场景上下文切换（供应商主数据/物料与采购协议/supplychain 域默认）、元素库 5/1/3/8/4、画布节点、Inspector（Supplier 17 属性/实现接口/DAM）✓
- explorer：DAM 类型树 9 类型、11 供应商列表、Search-Around 钻取（供应商›物料 3 行+面包屑）、PoHead 单据类型空态 +「在业务系统中查看 ↗」按钮 ✓
- workshop：360 视图（SUP0001 13 业务属性+关系块）、动作中心 8 动作、参数面板（填 pk/试算 dryRun 编辑集预演）✓
- 待办中心：页面/分组/流程概览正常（待办空=彩排任务已办结）✓

### 12.6 遗留与演示日注意

1. **演示顺序铁律**：幕⑤漏斗 sync 必须在幕⑥评审回写之前（sync 覆盖 props）。
2. CR …033 走页面创建/提交（登录态 create_by 正确）；若走 API 需先补 create_by。
3. onboarding 技能已建：`.agents/skills/cmx-onto-toolkit/`（SKILL.md 七步方法论+13 条坑表、scripts/onto_seed.py、references/scenario-spec.md + ontology-api.md、examples/procurement/ 规格+灌单脚本+walkthrough.md 走查手册）。
4. cmx-flow-toolkit 已按 P0 契约修订（停发 BPMN 审批属性、补 approval-defs/save、修 4 处路径、M1 拓扑约束坑）；sync_menu_db.py 修复 %40 解码。
5. onto/flow 等服务运行配置以 *-test.toml 为准；cmx-ontology 当前检出分支 feat/onto-demo-flow-loop。

### 12.7 演示前补强（9-12 晚）

- **DAM 中文化**：6 个类型 + 2 个场景视图 DAM 全部改为中文分组（供应链 ▸ 采购管理 ▸ 供应商管理等）；重灌口径已同步 scenario-spec.json。注意 PurchaseOrder 只是 docType.code，单据定义 apiName 是根实体 PoHead。
- **关系补强**：storeIn 显示名「存放于」→「存放」；新增 useUom（物料→计量单位，12 条）/ contractCurrency（合同→币种，3 条）/ contractPaymentTerm（合同→付款条件，3 条），三字典类型不再孤立，linkTypes 5→8、links 48→66，已存档 v6。
- **flow-toolkit 修订重做**：此前被工作区还原波及，已按 P0 契约重做并实测通过（publish v3 热装载、approval-defs/save、startable 预检、冒烟 cancel 收尾全绿）。

### 12.8 元数据真源补齐（9-12 晚）

- 对照检查：cmx-container 资产中本方案创建的未跟踪文件 = 单据元数据 purchase_doc_meta_v1.json + 采购菜单 purchase-menu.json + 门户模块 module.json 三组，与改动清单一致（explorer.js 用户已提交；vendor 画布改动与本方案无关）。
- **PoHead 无 ol_edge 关联属正常**：按口径单据定义经 import/doc 入本体（单对象模型，不导实例、不产关系），实例在业务库；单据↔主数据关联体现在业务库字段（supplier_code），本体侧用法=溯源下钻「在业务系统中查看」。
- **字典元数据补缺**：mdm seed 原有 supplier/material/employee/currency/uom/payment_term 等 22 个字典，缺仓库与采购合同——已在 dataplatform_dct_meta_v1.json 登记 cm_warehouse/cm_contract（BUSINESS 类，refDict 声明 employee/supplier/currency/payment_term 引用）+ 生成 seed/cm_warehouse.json、seed/cm_contract.json（与演示数据同码 WH-01..03、CT-2026-001..003）。本体侧关系（contractCurrency/contractPaymentTerm/useUom）即这些 refDict 的对象化表达。未 deploy 到业务库（演示不依赖；需要时走模型中心 deploy）。
