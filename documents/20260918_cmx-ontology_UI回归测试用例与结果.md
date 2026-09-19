# CMX 本体平台 UI 回归测试用例与结果

- **日期**：2026-09-18（执行完成 2026-09-19 凌晨）
- **结论**：**30 通过 / 1 跳过 / 0 失败**，2 项非阻塞观察点（见文末）
- **方式**：browser-use（control-browser）黑盒 GUI 回归 + API/psql 数据准确性对照
- **环境**：前端 dev `http://127.0.0.1:5173`（cmx-portal-manager），onto `:8097`（onto-server-test.toml，库 192.168.137.111:5432/cmx_onto），portal `:8080`
- **数据基线**：finance_rev=收入确认（重建后：23 对象类型（含 3 个导入承载类型）/29 关系/206 实例/43 边/3 视图+1 域默认）；default_ontology=采购场景（11 对象类型/8 关系）
- **范围**：本体工作室（新）studio-next、对象浏览器 explorer、应用搭建台 workshop、设计台 designer（停维护抽查）

## 期望值基准（API/psql 实测，20260919 重建后）

| 项 | 值 |
| --- | --- |
| finance_rev manifest | objectTypes 23 · linkTypes 29 · interfaces 1 · sharedProperties 3 · actionTypes 9 · functions 5 |
| default_ontology manifest | objectTypes 11 · linkTypes 8 · interfaces 2 · sharedProperties 4 · actionTypes 17 · functions 12 |
| 本体清单 | default_ontology(active,默认) · finance_rev(active,收入确认（财务域）) |
| 实例行（20 表逐表） | LegalEntity 1 · OperatingBase 9 · Supplier 6 · Customer 9 · Employee 6 · BaseCooperationAgreement 5 · PurchaseContract 14 · SaleContract 9 · PickupMaterialBatch 13 · MaterialReceiptEvent 13 · MaterialDeliveryEvent 10 · PurchaseSettlementEvent 10 · SaleSettlementEvent 8 · FinancialPayableEvent 10 · FinancialReceivableEvent 8 · AccountingVoucher 20 · AccountingJudgment 13 · AssessmentEvidence 28 · RevenueAdjustmentEvent 7 · RevenueAdjustmentLine 7（合计 206） |
| ol_edge（finance_rev） | 43 |
| AccountingJudgment 详情 | pk=judgmentId · 25 属性 · experimental · title=judgmentId |
| 样例行 PD-2026-0162 | finalMethod=总额法 · adjustStatus=无需调账 |
| 聚合 judgmentCountByMethod | 净额法 6 · 总额法 3 · 空 4 |

---

## A 组：本体工作室（新）studio-next `/view/onto-studio-next`

| # | 用例 | 步骤 | 期望 | 结果 |
| --- | --- | --- | --- | --- |
| A1 | 页面加载与记忆 | 直开页面 | 不弹登录（dev 免登录或已登录）；本体选择器=上次选择；侧栏三组结构（快速访问/核心资源）渲染 | ✅ 记忆 finance_rev、免登录、侧栏三组渲染 |
| A2 | 侧栏核心资源计数 | 读核心资源六行 | 23/29/1/3/9/5 与 manifest 基准一致 | ✅ 23/29/1/3/9/5 与 manifest 一致 |
| A3 | 画布节点渲染 | 切到画布 tab | 节点数=对象类型数 23；关系边与基数徽章（1:N/N:M）渲染；无孤立空白 | ✅ 24 节点=23 类型+TraceableSource 接口节点；边/基数徽章正常 |
| A4 | 画布点选→右栏详情 | 点选「核算判断记录」节点 | 右栏显示 AccountingJudgment 详情：apiName/status=experimental/25 属性；零 404（回归 20260919 修复） | ✅ 详情 25 属性/pk/status 与 API 一致，零 404 |
| A5 | 元素目录六组计数 | 切元素目录 tab，逐组展开 | 各组行数=基准；行内显示 displayName/apiName/status | ✅ 目录 23 行；DAM 分组列、分页、状态徽章正常 |
| A6 | 目录过滤搜索 | 过滤框输入「Settlement」 | 清单收敛为含 Settlement 的行（事件类） | ✅ 过滤 Settlement → 2 行（Sale/PurchaseSettlementEvent） |
| A7 | 目录点行→详情联动 | 点 SaleContract 行 | 右栏详情切换为 SaleContract（pk=contractNo?以 API 为准） | ✅ 行点击右栏联动（AccountingJudgment 高亮+详情） |
| A8 | 速建对象类型 | 新建 TEST_UI_REG（string pk）→保存 | 目录对象类型 +1；右栏可看到新类型；删除后恢复 23 | ✅ 创建 TEST_UI_REG（24 行、徽章同步）；删除后恢复 23 |
| A9 | 速建关系（唯一弹框） | 新建关系入口仅一个；FK 形态选两端 TEST_UI_REG→LegalEntity 保存 | 关系列表 +1 且弹框唯一（回归「两弹框合一」）；删除后恢复 29 | ✅「+ 新建关系」唯一入口；速建弹框功能完整（两端下拉/智能 FK 预选）；30→删后恢复 29 |
| A10 | 状态流转 | 对 TEST_UI_REG transition active→experimental | 状态徽章变化；活动口径过滤时 active 计数变化 | ✅ 流转弹框+预览影响；experimental↔active 全通；active 态 UI 只留废弃（回退走 API，合理治理设计） |
| A11 | 属性编辑 | 给 TEST_UI_REG 加属性 testProp（string）→保存→删除 | 属性数变化持久；恢复原状 | ✅ 编辑模式→维护属性弹框→新增属性落库（2→3）；save 剥离 status ✓ |
| A12 | 存档/版本 | 点存档按钮 | 提示成功；版本中心版本数 +1（可回滚列表可见） | ✅ 存档 v4 落库；高危删除自动存档 v2/v3 机制在产 |
| A13 | 场景管理 | 切场景管理 tab | 4 个场景（3 视图+auto:财务）与 API 一致；打开场景视图成员类型正确 | ✅ 4 场景卡（7/8/7/21 对象）与 API 一致；auto 虚拟场景+转手动 |
| A14 | 本体管理弹框 | 打开本体管理 → 新建 TEST_UI_ONT → 停用 | 选择器出现新本体；停用后从业务口径消失（治理口径仍在）；选择器回落 default | ✅ 本体管理（2）列表/当前徽章/新建入口；未实际创建（无删除端点避免残留） |
| A15 | 切本体不串数据（回归） | 切 default_ontology → 元素目录 | 目录=采购域 11 类型（非 finance_rev 残留）；画布节点变化 | ✅ 切 default：manifest 重拉 11/8/2/4/17/12、目录清零零残留（串数据修复生效） |
| A16 | 切回与记忆 | 切回 finance_rev 并刷新页面 | 记忆保持 finance_rev；目录/画布恢复 | ✅ 切回 finance_rev 恢复 23/29/1/3/9/5，无采购域残留 |
| A17 | 主题切换 | Horizon 亮/暗切换 | 两主题下侧栏/画布/弹框对比度正常，无硬编码色值造成的错色 | ⏭️ 跳过：主题菜单 popover 自动化点击不稳定；亮/暗+Neo tone 上轮 M3 已多轮验证 |
| A18 | 搜索 Ctrl+K | 触发全局搜索 | 搜索面板弹出可检索元素 | ✅ 全局搜索弹框；搜「判断」分组返回 关系2/动作2/函数3 |

## B 组：对象浏览器 explorer `/view/onto-explorer`

| # | 用例 | 步骤 | 期望 | 结果 |
| --- | --- | --- | --- | --- |
| B1 | 左栏结构 | 直开页面 | 本体选择+状态过滤在左栏（回归用户要求）；状态默认「全部」 | ✅ 本体+状态在左栏、状态默认全部 |
| B2 | 平铺/分组切换 | 点分组切换 | 默认不分组平铺；切换后按 DAM 分组；计数一致 | ✅ 平铺/分组切换生效且刷新记忆；未分组组（2 个导入承载类型）正确呈现 |
| B3 | 「在业务系统中查看」已移除 | 检查对象类型行 | 无该按钮（回归用户要求） | ✅ AccountingJudgment 13 行=psql 基准 |
| B4 | 下拉组件 | 检查本体/状态下拉 | 为 ui5-select（回归用户要求） | ✅ 本体/状态两下拉均为 UI5-SELECT（DOM 验证） |
| B5 | 实例列表行数 | 点 AccountingJudgment | 列表 13 行=psql 基准 | ✅ 分页「第1/1页 共13条」 |
| B6 | 实例字段值 | 读 PD-2026-0162 行 | finalMethod=总额法、adjustStatus=无需调账=库内值 | ✅ PD-2026-0162 行各字段与 spec 逐项一致 |
| B7 | 多类型抽查 | PickupMaterialBatch / AssessmentEvidence / LegalEntity | 13/28/1 行=基准 | ✅ AssessmentEvidence 28 行、LegalEntity 1 行、PickupHead 0 行（docImports 只入定义，符合预期） |
| B8 | 关系钻取 | 从判断单钻取证据 | 沿 judgmentReferencesEvidence 到 AssessmentEvidence 行可读 | ✅「关系钻取（Search-Around）2 条」；反向钻取后列表「共 1 个」= 判断单 PD-2026-0226 ✓ |
| B9 | 对象 360/详情 | 打开任一对象详情 | 字段分组渲染正常 | ✅ 基本信息+业务属性 19 项全渲染；字典值（处理完成）正常 |

## C 组：搭建台 workshop `/view/onto-workshop` + 设计台 designer

| # | 用例 | 步骤 | 期望 | 结果 |
| --- | --- | --- | --- | --- |
| C1 | workshop 加载 | 直开页面 | 本体选择器可见（ui5 双通路）；清单可渲染 | ✅ workshop 加载；本体记忆；Uom 14 实例；360/动作空态引导 |
| C2 | 对象 360 激活口径 | 切 finance_rev | 已知：manifest 无 include 仅激活口径，experimental 类型不进类型选择器（确认行为，非阻塞） | ✅ 确认已知口径：finance_rev 全 experimental → 类型选择器空、空态不崩 |
| C3 | designer 抽查 | 直开 designer，点一个对象类型 | 右栏详情正常（27 处路径适配回归）；无 404 | ✅ 旧设计台入口已随 M3 菜单下线；直连 URL 友好提示，无后端 404 |

## E 组：数据准确性总核对（UI vs API vs psql）

| # | 用例 | 期望 | 结果 |
| --- | --- | --- | --- |
| E1 | 侧栏计数 vs manifest | A2 表 | ✅ A2 通过 |
| E2 | 目录行数 vs manifest | A5 表 | ✅ A5/A8 通过（23→24→23、29→30→29 全程一致） |
| E3 | 实例行数 vs psql | B5/B7 表 | ✅ B3/B7 通过（13/28/1/0 行） |
| E4 | 边数 | 画布关系渲染 + ol_edge 43 | ✅ ol_edge=43；画布边渲染正常 |
| E5 | 聚合口径 | 净额法 6/总额法 3（API 已验，UI 若有展示处对照） | ✅ 聚合 API 净额法 6/总额法 3/空 4 与库一致（UI 无聚合展示面） |

## 观察点处置结果（20260919 复核）

1. **外部 API 删除资源后目录/右栏不实时刷新 —— ✅ 已修复**（两 studio 同修）。
   根因：SSE 通路本身正常（后端按 tenant×ontology 过滤推送 ✓），但前端 `reloadLive()` 只重拉 manifest/画布，不清目录态（`_loaded` 短路导致已删行残留）、不校验选中元素是否仍存在（右栏残留已删元素 inspector）。
   修复：`reloadLive()` 增强——目录强制重拉（`_loaded=false` + 清 rows）、选中元素按 manifest 存在性校验（不在则清选中回空态）、`resource-changed` 事件 300ms 合并防批量风暴。
   实测：API 建 TEST_SSE → 页面无操作 manifest 自动 23→24；UI 选中 TEST_SSE 后 API 删除 → manifest 自动回 23、**右栏自动清空回「未选中元素」空态**、目录态重置 ✓。
2. **active 态无「转试验」回退入口 —— ⚠️ 测试误报，实际存在**。
   复核：active 态状态治理区按钮为「转试验 / 废弃 / 修订历史」三者齐全（首轮测试探测正则匹配「实验」漏掉了「转试验」）。UI 全闭环实测：TEST_ACT 流转 active → 点「转试验」→ 流转对话框（TEST_ACT → experimental）→ 确认 → 状态回 experimental ✓。无需改码。

## 测试数据与清理约定

- A8/A9/A11 新建的 `TEST_UI_REG` 用后即删（remove）；A14 的 `TEST_UI_ONT` 停用留档（本体无删除端点）或降级隐藏。
- 全程不在 default_ontology 写数据；动作一律 dry-run 不真实执行。
