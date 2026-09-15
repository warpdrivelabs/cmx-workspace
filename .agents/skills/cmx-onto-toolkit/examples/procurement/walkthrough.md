# 演示走查手册 —— 采购供应链·六幕（2026-09-13 周日）

> 环境速记：门户 dev :5173（登录 admin/Admin@12345）｜onto :8097（cmx_onto@192.168.137.111）｜flow :8091｜mdm :8095｜model :8093｜业务库 fico（db_id=fico-db）
> 免登录 API 头：`X-API-Key: cmx_sk_dev_A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6`
>
> **数据基线 v6（极简口径，2026-09-13 清库重灌；2026-09-15 backing 口径升级）**：**7 个对象类型 / 6 条关系，全部 oneToMany FK backing，零多对多、零中间表**——①每个对象带 `id` 属性=来源表 `cm_*.id` 真实主键（对象列表直接可见 id 列）；②6 条关系（signContract/buyerOf/useUom/contractCurrency/settleCurrency/managerOf）全部有 MDM 真实外键列支撑，**外键属性存对端业务主键**（如 supplierId=SUP0001、currencyId=CNY），backing 省略 `targetProperty` = 对端 pk 列严格 Palantir 语义，读侧实时编译 pk 半连接、不落边表；③**`ol_edge` 边表 0 行——凡关系必有字段关联**；④v5 裁掉 PaymentTerm（付款条件）与供应商标签，v6 进一步裁掉供应记录（SupplyRecord 类型 + supplierSupply/materialSupply 两条关系 + cm_supply_record 中间表）——图上只剩业务真实存在的一对多。⚠️ 若前端曾打开过旧版数据，先强刷 explorer 页面（关系元数据有页面缓存）。

## 演示顺序（重要约束）

**幕⑤（MDM 闭环+漏斗 sync）→ 幕⑦（双向打通）→ 幕⑥（action 发起流程）**。漏斗 sync 会整体覆盖对象 props——评审状态（reviewStatus）必须在最后一次 sync 之后产生。已彩排消耗掉的素材：CR …032（已 activated，铸号 SUP202609120001，现已带引用列 USD/李晓峰）。**演示日用 CR …033（宁波海天精工）走幕⑤页面流程；幕⑥用 SUP0009（东华链条）。**

## 幕① 元数据同源（业务系统）

- 页面：门户菜单「数据平台 ▸ 采购管理 ▸ 采购订单」（`/view/po-doc-viewer`，doc-loader 通用单据页）
- 看：cv_po_order 10 张真实单据（PO-2026-0001~0010，覆盖草稿→已提交→已审批→部分收货→已完成→已关闭→已取消全状态），主从展开 18 条订单行
- 讲：单据元数据（purchase_doc_meta_v1.json）deploy 到业务库建表；数据是业务系统的账本

## 幕② 字典入本体

- 漏斗（主菜，**七类全漏斗**）：explorer 左树 供应链 ▸ 采购管理 ▸ … 七个类型全部来自 fico 库 cm_* 表：
  Supplier 13 / Material 10 / Warehouse 3 / Contract 3 / Employee 8 / Currency 6 / Uom 14
  - `GET /funnel/pipeline-status/Supplier`：extract/map/index 三段 ready + objects=13 + quarantined=1
  - `GET /funnel/quarantine?objectType=Supplier`：SUP-BAD 行 + violations（name 缺失被拦）——数据质量闸门
  - `POST /funnel/sync/Supplier` 现场 re-sync：read=14/written=13/quarantined=1
- 讲：源是 fico 库 cm_* 主数据表（sourceDbId 跨库），SQL LEFT JOIN 派生显示列（物料分类/单位、部门/岗位）、CASE 派生评分/准时率；**类型定义与数据全部以主数据平台为真源**——MDM 元数据（DCT）deploy 建表，漏斗拉取进本体；点开任一供应商，对象列表 **id 列=cm_supplier.id 真实主键**（SUP0001→1，SUP0010→56051595943937 雪花号），这就是「MDM 主键在本体的镜像」
- ⚠️ 演示日铁律：全场只允许这一处 sync（幕⑤ Supplier），其余类型一律不再 sync、不重跑 onto_seed

## 幕③ 工作室建模治理（直改 live + 存档/回滚架构）

- 页面：`/view/onto-studio`
- 上下文切换器：「供应商主数据（手动）」场景画布（4 成员+接口 GovernedMaster）→ ⟲ 重排 → ⤢ 适配
- ⌘K 搜索「Contract」定位；点左栏「物料」→ Inspector 看共享属性挂接（lifecycleStatus 等 3 项）
- 元素库：关系 6 / 接口 1 / 共享属性 3 / 动作 7 / 函数 4
- 编辑演示：开「编辑」开关 → 给 Contract 加一属性「备注 remark」→ 即时生效（直改 live）→「存档」打版本检查点 →「版本」回看/对比/回滚
- 讲：元数据变更不占停机、存档即版本、回滚整体恢复

## 幕④ 数据服务

- explorer `/view/onto-explorer`：
  - 过滤构造器：riskLevel = 低 → 供应商列表（风险等级是 MDM 枚举标签口径）
  - **下钻主菜（三跳链）**：选 SUP0001（中信重工）→「采购对接 · 反向 → Employee」EMP0001 王建国（buyerId=EMP0001 业务键）→「主管仓库」WH-01（managerId 同款）——供应商→员工→仓库三跳全链 FK 半连接实时编译，面包屑逐级回退
  - **关系环（经共享币种）**：SUP0001 →「签订合同」CT-2026-001（supplierId=SUP0001）→「计价币种 · 反向」CNY 人民币（currencyId=CNY）→「结算币种」以人民币结算的供应商列表（SUP0002/0004/0007/0008/0009/0010…含 SUP0001 自身）——环不是拉边，是底层外键列的真实回路
  - **数据驱动关系 = FK backing，字段级真关联**（6 条 oneToMany 全部有 MDM 真实外键列——外键属性存**对端业务主键**（SUP0001/CNY/EMP0001/pcs…），backing 省略 targetProperty = 对端 pk 列严格 Palantir 语义，读侧实时编译 pk 半连接、**不落 ol_edge 边表**；`ol_edge` 全场 0 行，凡关系必有字段关联）：
    - 合同详情：**供应商ID 字段回来了**——CT-2026-001 supplierId=SUP0001（对端业务主键，直指中信重工，不再是只有供应商名称没得关联）；「计价币种 · 反向」CT-2026-002→USD（currencyId=USD）
    - 供应商 →「结算币种 · 反向 → Currency」（SUP0001→CNY 人民币，SUP0003→USD，SUP0005→EUR——**结算币种就是 cm_supplier.settle_currency_id 列的实况**）；「采购对接 · 反向 → Employee」（SUP0001→EMP0001 王建国=cm_supplier.buyer_id）
    - 物料 →「使用计量单位 · 反向 → Uom」（六角螺栓→个 pcs=cm_material.base_uom_id）；员工 →「主管仓库」（EMP0001→WH-01=cm_warehouse.manager_id）
    - **空外键对照**：SUP202609120003 引用列为空 → 结算币种/采购对接关系自然不出现——关系跟着主数据引用列走，页面补全引用列 + 一次 sync 即自动出现，无需手工补边
  - 单据溯源：切「采购订单头 PoHead」→ 共 0 个（定义入本体、实例在业务库）→ 表头**「在业务系统中查看 ↗」**跳 doc-loader 看真实单据行
- workshop `/view/onto-workshop`：
  - 选 SUP0001 → 360 关系块（采购对接·反向/签订合同/结算币种…）
  - 动作中心：「暂停合作」→ 填 reason → **试算**（dryRun 徽标+编辑集预演）→ 取消；「调整供应商评分」填 9 → 执行 → FEEL 校验拦截「评分必须在 0~5 之间」
  - 函数求值（Inspector 或 curl）：
    - supplierGrade（FEEL）：SUP0001 rating 4.6 → **"A"**
    - supplierRiskScore（Rhai）：SUP0002（低风险）→ **93**（100−(100−96.5)×2）；SUP0005（中风险）→ **56**（100−20−(100−88)×2，风险等级按 MDM 标签「中」扣 20）
    - contractSpendBySupplier（聚合）：groupSum by supplierName → 中信重工 120万 / 华胜信息 76万 / 晨光办公 58万
    - materialFullLabel（FEEL）：MAT0002 → 「钢材类 / Q235B 热轧钢板 δ10（千克）」

## 幕⑤ 主数据治理闭环（页面操作，用 CR …033 宁波海天精工）

1. 门户「主数据 ▸ 供应商」→（或直接演示 cr-form）新建变更申请：doc_type=gys、cr_type=create、填名称/税号/电话 → 保存草稿
2. 提交 → 自动发起 mdm_cr_approval 流程（提交时自动确认发起节点）
3. **待办中心** `/view/gl-flow-todo-center` → 我的待办出现「主数据审批」→ 点办理打开 cr-form 审批页 → 同意
4. 见证：CR → activated；cm_supplier 自动新增行（编码引擎 MDM_GYS 铸号，如 SUP202609120002）——`SELECT * FROM cm_supplier ORDER BY id DESC LIMIT 1`
5. 漏斗 sync → 本体 explorer 出现新供应商（ written=14；新行引用列（币种/采购员）为空 → 结算币种/采购对接无关系属正常——FK backing 关系跟着主数据引用列走，页面补全引用列后再 sync 一次即自动出现，无需手工补边）
- 兜底：webhook 丢失时 `GET /api/mdm/change-requests/flow-status?crIds=…` 读时自愈

## 幕⑦ 双向打通（本体动作 → MDM 治理 → 事件自动回流）★高光

- 前置：MDM 分发订阅已配（mdm/subscriptions → onto /funnel/push）；本体动作「新增供应商申请」已发布
- workshop（SUP0001 或任一对象）→ 动作中心 →「新增供应商申请（发起主数据治理）」→ 填名称/税号/电话 → **试算（编辑 0 条=本体不直写黄金记录）** → 执行
- 台后 dispatch → MDM webhook-create 建 CR 并提交（create_by=admin）→ **待办中心出现「发起人确认」**（页面办理：保存并提交）→ **「主数据审批」**（Javier 账号审批，或 API 委托令牌）→ 激活器铸号写 cm_supplier
- **见证自动回流：不手动 sync**——MDM Outbox 事件 → webhook → 本体 funnel/push 自动 sync → explorer/workshop **2 秒内出现新供应商**
- 台后证据：`md_event_log` 事件 / `md_dispatch_log` delivered / onto 日志 `funnel/push 200`
- 讲：动作发起的是治理申请（不绕过 MDM 唯一写入口）→ 审批 → 黄金记录 → 事件驱动秒级回流；**双向打通全程零手动集成**
- 兜底：分发投递失败自动退避重试（幂等）；极端情况手动 `POST /funnel/sync/Supplier` 兜底
- 排查（2026-09-13 实测踩坑）：订阅行 `channel_config` 是保存时的**快照**，改端点后需重存订阅才刷新——残留旧地址会投递 404 直接置 dead（不重试）。自检 `GET /api/mdm/dispatches/stats`；重投 `POST /api/mdm/dispatches/retry {"ids":[…]}`（dead 行也可重投，重投后 delivered 即通）。两动作 E2E 已当日彩排验证：submitSupplierReview（SUP0008→已通过回写）与 applyNewSupplier（CR 激活→铸号→自动回流对象出现）全链路通。

## 幕⑥ 本体 action 发起流程（用 SUP0009 东华链条）

1. workshop 动作中心 →「提交供应商评审（发起流程）」→ supplierId=SUP0009（或填 pk）→ **试算 → 执行**
2. 台后：`POST /api/onto/v1/action-outbox/dispatch`（出站发件箱手动分发）→ flow 实例创建
3. 待办中心 → admin 出现「供应商评审」待办（businessKey=SUP0009）→ 通用办结页**同意**
4. 见证三连：
   - flow 投递流水 DONE：`POST /api/flow/v1/event-deliveries/query {"definitionKey":"supplier_review"}`
   - 本体对象状态自动回写：workshop 360 中 SUP0009 → **reviewStatus=已通过 / status=启用（回调只回写 reviewStatus+lastReviewAt，不碰主数据口径的启用状态）/ lastReviewAt=刚刚**
   - oe_action_log 审计：`GET /api/onto/v1/action-logs`
- 讲：本体是业务语义层——动作在本体发起、流程在引擎审批、结果经事件回写本体对象，全链路无硬编码集成
- ⚠️ **幕⑥之后严禁再审批任何供应商 CR / 再 sync**（自动 push 会清掉回写的 reviewStatus）

## curl 备份（页面万一失灵时）

```bash
AK='X-API-Key: cmx_sk_dev_A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6'
B=http://127.0.0.1:8097/api/onto/v1
# 幕⑥ 全链
curl -s -X POST -H "$AK" -H "Content-Type: application/json" $B/action-types/submitSupplierReview/execute -d '{"params":{"supplierId":"SUP0009"},"actor":"demo"}'
curl -s -X POST -H "$AK" -H "Content-Type: application/json" $B/action-outbox/dispatch -d '{}'
# 待办审批需委托令牌（sub=admin id 7503326638169403392，密钥 a7k9m2p4x8q1w5e3r6t0y7u2i9o4p1）——见 cmx-flow-toolkit 模式A
# 幕⑤ 漏斗
curl -s -X POST -H "$AK" $B/funnel/sync/Supplier
```
