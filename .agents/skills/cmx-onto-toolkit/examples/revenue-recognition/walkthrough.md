# 收入确认（提货贸易模式核算）本体演示走查手册

> 场景规格：`scenario-spec.json`（本目录）。数据全部梳理自 `frontend/cmx-ontology-graph/demo/收入确认本体Web原型_v1.3.3原始.html`（ONTOLOGY_OBJECTS / ONTOLOGY_RELATIONS / OBJECT_LOGIC / JUDGMENT_ROWS / BUSINESS_CHAIN_CONTEXT / EVIDENCE_LEDGER / ADJUSTMENT_ROWS / SETTLEMENT_GROUPS / CASES / ORG_HIERARCHY / RULE_DIMENSIONS）。
>
> **状态：已入库**（2026-09-19 执行，落**独立本体 `finance_rev`**「收入确认（财务域）」，与采购域 default_ontology 隔离——多本体适配（方案 20260918 M1/M2）的首个实战）。重跑/补数命令见下节。

## 一、执行方式

```bash
# 前置：onto 服务已启动（cmx-launcher 或 cd backend/cmx-ontology && ./onto.sh）
# 本体不存在先注册（全局接口，不带 ontology）：
curl -s -X POST http://127.0.0.1:8097/api/onto/v1/ontologies/create \
  -H 'X-API-Key: cmx_sk_dev_A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6' -H 'Content-Type: application/json' \
  -d '{"apiName":"finance_rev","displayName":"收入确认（财务域）","description":"收入确认演示场景——独立于采购域的第二本体，验证多本体隔离"}'
python3 .agents/skills/cmx-onto-toolkit/scripts/onto_seed.py \
  --spec .agents/skills/cmx-onto-toolkit/examples/revenue-recognition/scenario-spec.json \
  --base http://127.0.0.1:8097 --ontology finance_rev
```

- 规格**无 funnelMappings**，`--skip` 无需配置；全段 upsert 幂等可重跑。
- 执行后按技能「交付约定」补汇报四件套：对象/关系 manifest 数、4 类函数各 evaluate 一次、动作 dry-run（含 `confirmJudgment` 对 `PD-2026-0214` 的校验拦截负例）、≥2 跳对象集查询。
- Loop⑥（`submitJudgmentReview` 发起流程）为**可选闭环**：需 onto toml `[onto] flow_api_key` + flow toml `[service_rpc.services] onto`（webhook 目录模式）+ `judgment_review` 流程定义（技能 cmx-flow-toolkit 部署），且必须安排在全部造数动作之后执行。

## 二、场景建模口径

### 2.1 架构叙事

| 叙事锚 | 本场景落法 |
| --- | --- |
| 主数据"存"本体 | 法人/基地/供应商/客户/员工/协议/合同以 objects 段原生建模进 oo_*（原型来源为数据中台主数据与协议/合同系统 AI 识别，业务库无对应表，故不走漏斗） |
| 单据"映射查" | `docImports` 提货单（采销关联锚点单据）：只入定义不导实例，explorer「在业务系统中查看」跳转 |
| Action 只写 oo_ | 9 个动作全部只改本体对象/边，不碰业务表 |

### 2.2 关系 backing 决策（29 条 = 25 FK + 4 Edge）

- **25 条 oneToMany FK**：外键属性存对端主键（如 `PickupMaterialBatch.baseId → LG01`），targetProperty 缺省走 pk 半连接。其中 `adjustmentLine` 是 Palantir 式中间对象——`adjustFormsLine` / `lineAdjustsReceivable` / `lineCoversBatch` 三条一对多 FK 构成调账 M:N 闭环（对应原型「实体化M-N关系」REL-0027/0028/0029）。
- **4 条 manyToMany（平台内置 ol_edge）**：
  - `employeeAppliesToLegal` / `employeeAppliesToBase`：人员适用范围在原型中是数组属性（适用法人主体ID列表/适用基地ID列表），单值 FK 装不下，且无业务中间表——属维护型数据，不硬造连接表；
  - `purchaseSettleAggregatesBatch` / `deliveryRollsUpToSaleSettle`：原型标注「CBS/关系派生」「源系统关系」，无外键字段。
- **原型 N-N 的落地改写**：`baseAgreement 约束 base`（REL-0005，0..N→0..N）改写为协议持 `baseId` 的一对多（每份协议约束一个基地，一个基地可有多份协议），保持「凡关系必有字段关联」。
- 原型 REL-0017/0018 在 v1.3.3 中已被删除，本规格共 29 条与原型一致。

### 2.3 演示角色（讲故事的实例）

| 实例链 | 剧本 |
| --- | --- |
| `THD-2026-0219`（沿江·江北钢铁） | **净额法全闭环正面案例**：判断 PD-2026-0219 净额法 → 调账单 TZD-2026-0729-A2 审批完成 → 凭证 PZ-2026-07-00228 有效 → adjustStatus=流程已闭环 |
| `THD-2026-0188/0191/0198`（临港·华远特钢） | **三批次共用一份销售合同 XSHT-2026-0528，出库归集到同一张销售结算 XSJS-2026-0618 → 应收 CWYS-2026-0619**，均待调账（0198 已有草稿调账单） |
| `THD-2026-0214`（华北合作·北方特钢） | **证据不足负例**：销售合同缺失 → 默认建议净额法、finalMethod 为空 → `confirmJudgment` 校验拦截演示 |
| `THD-2026-0226`（华东一号·江州钢铁） | **人员风险案例**：总额法成立，但王建国（适用 LG01+HZ03）同日在 HD01 磅单签字 → EV-0226-03 疑似超出适用范围，不改变核算结论 |
| `THD-2026-0223`（临港·海润特钢） | **调账异常案例**：采购合同 CGHT-2026-0517 与销售合同货权描述冲突（识别冲突）→ 调账单被驳/凭证已作废 → 异常·待重新调账 |
| `THD-2026-0162` / `THD-2026-0228` | 自营基地总额法对照组（协议自担货权/风险，合同有自主定价权） |
| `THD-2026-0235/0238/0241` | 事中预判断进行中（0241 缺销售合同：saleContractId 为空，关系自然不出现） |

## 三、页面走查（执行后）

按 studio → explorer → workshop 顺序：

1. **studio 场景画布**：左树按 DAM 分组（参与方/契约/贸易执行/结算凭证/核算判断/调账闭环）；画布看 `PickupMaterialBatch` 为中心的 FK 关系网；Inspector 点开 `PD-2026-0219` 看判断四组属性。
2. **studio 函数试算**：`judgmentEffectiveMethod` 喂 `PD-2026-0214`（应返回"净额法（默认建议）"——finalMethod 为空回落建议值）；`judgmentRiskScore`（Rhai）喂 `PD-2026-0188`（待调账+关键证据完整 → 100-35-10=55）；`adjustmentAmountByReceivable` 传 objectSet（filter receivableId=CWYS-2026-0619 的明细，groupSum 应得 128400）；`judgmentCountByMethod` 看总额/净额分布。
3. **studio 动作试算**：`confirmJudgment` 负例选 `PD-2026-0214`（证据不足 → 拦截，看 adminDetail）；正例传 `PD-2026-0208` + finalMethod=净额法；`deleteDraftAdjustment` 负例选 `TZD-2026-0729-A2`（已审批 → 拦截），正例选 `TZD-2026-0708-D1`（草稿）。
4. **explorer**：类型树勾选「收入确认闭环视图」；从 `THD-2026-0188` ≥2 跳下钻：批次→销售结算→应收（deliveryRollsUpToSaleSettle → saleSettleGeneratesReceivable）；批次→调账明细→应收（lineCoversBatch → lineAdjustsReceivable）；提货单行「在业务系统中查看」（docImports 单据跳转）。
5. **workshop**：360 视图选 `THD-2026-0219` 看全链；动作中心「适用于 PickupMaterialBatch」分区应出现无（本场景 object 参数动作全部锚在 Judgment/AdjustmentEvent/Employee），选中 `PD-2026-0223` 看「适用于 AccountingJudgment」动作自动绑定 + dry-run diff。

## 四、覆盖度自查（全绿）

- [x] 五原子：createObject（submitRevenueAdjustment/createAdjustmentLine）/ modifyObject（confirmJudgment 等）/ deleteObject（deleteDraftAdjustment）/ addLink（assignEmployeeBaseScope 等）/ removeLink（removeEmployeeBaseScope）
- [x] FEEL×2（judgmentEffectiveMethod、evidenceFullLabel）+ Rhai×1（judgmentRiskScore，无 `let mut`）+ aggregation×2（groupSum/groupCount）
- [x] ≥2 跳下钻链：提货批次→销售结算→财务应收；批次→调账明细→应收；基地→协议（约束）；合同→批次→判断→证据
- [x] 每条关系 backing 有据：25 FK（外键存对端 pk）+ 4 Edge（数组维护数据/源系统派生，不硬造连接表）
- [x] 动作 parameters 完整，object 参数 12 个全带 objectType（派生 target_object_types，workshop 分区可用）
- [x] 6 处 validations 引用 `objects.<参数>.<属性>`（confirmJudgment 证据不足拦截、submitRevenueAdjustment 净额法/待调账拦截、createAdjustmentLine 与 deleteDraftAdjustment 草稿拦截、completeAdjustmentLoop 防重复闭环）
- [x] 实例全部正式中文企业数据且讲解意义（206 实例对应原型 8 条正式判断 + 3 条事中预判断 + 2 条剧本链）

## 五、已知边界与注意事项

1. **未执行**：本规格未 POST 到任何环境；执行前确认 onto 服务与库已就绪，最好先 `pg_dump` 备份本体库。
2. **不要后续对 Supplier/Customer 加漏斗**：漏斗 sync 会整体覆盖 objects 段造的演示实例；如需演示漏斗，另建演示类型。
3. **快照段**：`snapshot.summary` 描述 v1 基线；重复执行规格时内容一致会去重不涨版本。
4. **复核实例数**：206 = 法人1 + 基地9 + 供应商6 + 客户9 + 员工6 + 基地协议5 + 采购合同14 + 销售合同9 + 批次13 + 接收13 + 交付10 + 采购结算10 + 销售结算8 + 应付10 + 应收8 + 凭证20 + 判断13 + 证据28 + 调账单7 + 调账明细7。
5. **凭证编号冲突风险**：PZ-2026-07-00219/00228/00231 取自原型台账真实编号，其余凭证为编造；若与库里已有演示数据冲突，upsert 会覆盖同名编号，注意与其他场景共用本体库时的隔离。
6. **流程闭环**：`submitJudgmentReview` 的 `flowDefKey=judgment_review` 尚无流程定义，执行 Loop⑥ 前需先用 cmx-flow-toolkit 部署，否则动作可 dry-run 但 execute 会在发流程时报错。
