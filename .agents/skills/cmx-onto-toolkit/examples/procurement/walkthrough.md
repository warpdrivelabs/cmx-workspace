# 演示走查手册 —— 采购供应链·六幕（2026-09-13 周日）

> 环境速记：门户 dev :5173（登录 admin/Admin@12345）｜onto :8097（cmx_onto@192.168.137.111）｜flow :8091｜mdm :8095｜model :8093｜业务库 fico（db_id=fico-db）
> 免登录 API 头：`X-API-Key: cmx_sk_dev_A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6`

## 演示顺序（重要约束）

**幕⑤（MDM 闭环+漏斗 sync）→ 幕⑥（action 发起流程）**。漏斗 sync 会整体覆盖对象 props——评审状态（reviewStatus）必须在最后一次 sync 之后产生。已彩排消耗掉的素材：CR …032（已 activated，铸号 SUP202609120001）、SUP0002（reviewStatus 已被 sync 清掉，status=合作中）。**演示日用 CR …033（宁波海天精工）走幕⑤页面流程；幕⑥用 SUP0009（东华链条）。**

## 幕① 元数据同源（业务系统）

- 页面：门户菜单「数据平台 ▸ 采购管理 ▸ 采购订单」（`/view/po-doc-viewer`，doc-loader 通用单据页）
- 看：cv_po_order 10 张真实单据（PO-2026-0001~0010，覆盖草稿→已提交→已审批→部分收货→已完成→已关闭→已取消全状态），主从展开 18 条订单行
- 讲：单据元数据（purchase_doc_meta_v1.json）deploy 到业务库建表；数据是业务系统的账本

## 幕② 字典入本体

- 简单字典：`POST /api/onto/v1/import/dct`（Currency/Uom/PaymentTerm 已导入，字典项当场物化）
- 漏斗（主菜）：explorer 左树 供应链 ▸ 采购管理 ▸ 供应商管理 ▸ 供应商（**共 11 个**）
  - `GET /funnel/pipeline-status/Supplier`：extract/map/index 三段 ready + objects=11 + quarantined=1
  - `GET /funnel/quarantine?objectType=Supplier`：SUP-BAD 行 + violations（name 缺失被拦）——数据质量闸门
  - `POST /funnel/sync/Supplier` 现场 re-sync：read=12/written=11/quarantined=1
- 讲：源是 fico 库 cm_supplier（sourceDbId 跨库），SQL CASE 派生评分/准时率；本体只存主数据

## 幕③ 工作室建模治理（直改 live + 存档/回滚架构）

- 页面：`/view/onto-studio`
- 上下文切换器：「供应商主数据（手动）」场景画布（4 成员+接口 GovernedMaster）→ ⟲ 重排 → ⤢ 适配
- ⌘K 搜索「Contract」定位；点左栏「物料」→ Inspector 看共享属性挂接（lifecycleStatus 等 3 项）
- 元素库：关系 8 / 接口 1 / 共享属性 3 / 动作 8 / 函数 4
- 编辑演示：开「编辑」开关 → 给 Contract 加一属性「备注 remark」→ 即时生效（直改 live）→「存档」打版本检查点 →「版本」回看/对比/回滚
- 讲：元数据变更不占停机、存档即版本、回滚整体恢复

## 幕④ 数据服务

- explorer `/view/onto-explorer`：
  - 过滤构造器：riskLevel = low → 供应商列表
  - **下钻主菜**：选 SUP0001 → 详情区「供应 → Material」（3 物料）→ 任选物料 →「覆盖物料 · 反向 → Contract」→ 面包屑逐级回退
  - 字典关系挂接（三个字典类型不再孤立）：任选物料 →「使用计量单位 → Uom」（如轴承 6204 → 个）；合同 →「计价币种 → Currency」（CT-2026-002 → 美元）+「付款条件 → PaymentTerm」（CT-2026-001 → 月结60天）；仓库 →「存放 → Material」
  - 单据溯源：切「采购订单头 PoHead」→ 共 0 个（定义入本体、实例在业务库）→ 表头**「在业务系统中查看 ↗」**跳 doc-loader 看真实单据行
- workshop `/view/onto-workshop`：
  - 选 SUP0001 → 360 关系块（采购对接·反向/签订合同/供应…）
  - 动作中心：「暂停合作」→ 填 reason → **试算**（dryRun 徽标+编辑集预演）→ 取消；「调整供应商评分」填 9 → 执行 → FEEL 校验拦截「评分必须在 0~5 之间」
  - 函数求值（Inspector 或 curl）：
    - supplierGrade（FEEL）：SUP0001 rating 4.6 → **"A"**
    - supplierRiskScore（Rhai）：SUP0002 → **93**（100−(100−96.5)×2）
    - contractSpendBySupplier（聚合）：groupSum by supplierCode → SUP0001 120万 / SUP0003 76万 / SUP0004 58万
    - materialFullLabel（FEEL）：GYL-001 → 「棒材 / 45号碳钢圆钢（千克）」

## 幕⑤ 主数据治理闭环（页面操作，用 CR …033 宁波海天精工）

1. 门户「主数据 ▸ 供应商」→（或直接演示 cr-form）新建变更申请：doc_type=gys、cr_type=create、填名称/税号/电话 → 保存草稿
2. 提交 → 自动发起 mdm_cr_approval 流程（提交时自动确认发起节点）
3. **待办中心** `/view/gl-flow-todo-center` → 我的待办出现「主数据审批」→ 点办理打开 cr-form 审批页 → 同意
4. 见证：CR → activated；cm_supplier 自动新增行（编码引擎 MDM_GYS 铸号，如 SUP202609120002）——`SELECT * FROM cm_supplier ORDER BY id DESC LIMIT 1`
5. 漏斗 sync → 本体 explorer 出现新供应商（ written=12）
- 兜底：webhook 丢失时 `GET /api/mdm/change-requests/flow-status?crIds=…` 读时自愈

## 幕⑥ 本体 action 发起流程（用 SUP0009 东华链条）

1. workshop 动作中心 →「提交供应商评审（发起流程）」→ supplierId=SUP0009（或填 pk）→ **试算 → 执行**
2. 台后：`POST /api/onto/v1/action-outbox/dispatch`（出站发件箱手动分发）→ flow 实例创建
3. 待办中心 → admin 出现「供应商评审」待办（businessKey=SUP0009）→ 通用办结页**同意**
4. 见证三连：
   - flow 投递流水 DONE：`POST /api/flow/v1/event-deliveries/query {"definitionKey":"supplier_review"}`
   - 本体对象状态自动回写：workshop 360 中 SUP0009 → **reviewStatus=已通过 / status=合作中 / lastReviewAt=刚刚**
   - oe_action_log 审计：`GET /api/onto/v1/action-logs`
- 讲：本体是业务语义层——动作在本体发起、流程在引擎审批、结果经事件回写本体对象，全链路无硬编码集成

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
