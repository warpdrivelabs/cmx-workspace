# cmx-flowengine × cmx-rulesengine 融合方案

> 流程引擎如何调用决策/规则引擎 · 现状评估 + 集成设计 + 分阶段路线（先出方案，不动代码）
> 2026-09-02 · 结论口径为对两侧当前源码的逐行核对

---

## 结论先行

**能融合吗？—— 能，而且异常干净。** 不是「理论上可行」，而是「接缝已经对齐」：

- **flow 侧已有现成接缝**：`serviceTask` 的 `JavaDelegate`（变量进 / 变量出，可同步、可异步 SKIP-LOCKED、可外部 worker），`HttpDelegate` 经 `cmx-service-rpc` 出站时**已自动携带 `X-API-Key`（服务身份）+ `X-Delegated-User-Token`（真实办理人）**——这正是 rules `/evaluate` 端点接受的鉴权头。协议层面几乎零摩擦。
- **rules 侧完全可被调用**：既有 HTTP `POST /api/rules/v1/decisions/{key}/evaluate`，也可作**内嵌库**——`cmx-rule-model / -engine / -feel` 三个 crate 是**零 DB/infra 的 leaf**（只依赖 serde/chrono/rhai，不碰 tokio-postgres/axum），`cmx_rule_engine::evaluate(&def, &ctx)` 是**同步函数**。
- **架构同源**：两者同 Rust edition 2024、同工具链 1.97.1、共用同一套基础设施 crate（`cmx-database-pg`/`cmx-core`/`cmx-web-chassis`，均 0.1.12，跨 workspace path 完全一致）、都是「一芯多壳」、都是 db-per-tenant、都在 center_client/Nacos 拓扑内。leaf 三件套与 flow 自身的 infra 依赖是**不相交的依赖子图**，内嵌进 flow **也不会产生版本冲突**。
- **零历史包袱**：flow 与 rules 之间**今天没有任何代码级依赖**——不是要拆解耦合，而是绿地新建。

**唯一需要设计的，是一层薄薄的「映射适配」+ 一条注入接缝**，外加把决策的**系统之源**从 flow 内置的简易决策表迁到 rules。下面给出完整方案。

---

## 一、现状：两个引擎，各有决策，尚无连接

{{FIG:current}}

关键事实（均经源码核对）：

| | cmx-flowengine（:8091） | cmx-rulesengine（:8094） |
| --- | --- | --- |
| 决策载体 | `businessRuleTask` → **内置 `DecisionTable`** | `businessRuleTask` 概念之上的完整引擎 |
| 命中策略 | **仅 FIRST / COLLECT 两种** | **11 种 DMN 命中策略** |
| 决策图 | 无 | **JDM 图（Kahn 拓扑 + 防环）** |
| 完备性/可解释 | 无 gap/overlap、无归因 trace | **gap/overlap 分析 + 逐节点失败归因 trace** |
| 表达式 | 自研 `${..}` DSL（~21 内建，无时间/区间） | 自研 Pratt **S-FEEL**（25 内建，区间/成员） |
| 存储 | `cmx_flow_decision` 表 + 引擎内**硬编码** evaluate | `cmx_rule_*` 6 表（发布/版本/激活）+ 纯引擎 |
| 设计器 | 自带 decision-designer（仅 FIRST/COLLECT） | 决策表 + 决策图设计器 + 仿真台 + 审计 |

**核心判断**：flow 的内置决策是一个**「够用的玩具」**（2 策略、无图、无可解释）；rules 才是**真正的决策引擎**。融合的价值命题不是「新增决策能力」，而是**让流程把真正的决策委托给专业的决策引擎**，同时把 flow 内部那份弱决策收敛掉。

> 一个有意思的信号：flow 自己的 `decision-viewer.js` 注释已写明「**编辑应归 cmx-rulesengine，此处仅 flow 侧运维视图**」——收敛意图早已潜伏在代码里。而 flow 前端决策网格的「机制」也确实借鉴自 rules 的设计器，只是数据层各自独立。文档里「已集成 cmx-rulesengine」的说法**目前是愿景、并未接线**。

---

## 二、三条接入路径

flow 侧的接缝已经具备，问题只是「从哪个口子接」。有三条现成路径，外加一个内嵌库变体。

{{FIG:options}}

- **A · serviceTask + Delegate（零引擎改动，今天即可）**：新增一个 `RulesEngineDelegate`（照 `cmx-flow-adapters` 里 `HttpDelegate` 的样子），把实例变量 POST 给 rules 的 `/evaluate`，再把返回的 `output` merge 回变量。**不动引擎核心**，只加一个适配器 + 一个服务目录项；可同步、可异步（SKIP-LOCKED + 重试/死信）、可外部 worker。最快、最低风险，适合做 P1 的最小可用验证。**代价**：这是「服务任务」语义，节点是 `serviceTask` 而非 `businessRuleTask`，决策身份靠约定维系。
- **B · DecisionProvider 注入接缝（中等改动，语义最干净）**：在 flow 引擎唯一的决策调用点（`engine.rs` 的 businessRuleTask 分支）引入一个 `DecisionProvider` trait——**与 `AssigneeResolver`/`SubflowRouter` 完全同构的注入式接缝**。默认实现包住今天的内置 `evaluate`（100% 向后兼容），另一个实现按 `decision_key` 调 rules。保留 `businessRuleTask` 的「单节点、变量进出」语义，且让决策像其它横切关注点一样成为一等接缝。**这是最终形态。**
- **C · external-worker 按 topic（跨进程，规则自持）**：把节点写成 `serviceTask type=external-worker topic=rules-eval`，由 rules 侧起一个 worker 用 `acquire_async_jobs(topic_filter)` 拉取、评估、回调 complete/fail。适合「规则要在自己进程/自己语言里跑」的场景，可靠性最好但链路最长、延迟最高。

**变体 · 内嵌库**：A/B 的「规则后端」都可以不是 HTTP，而是 `path` 依赖 `cmx-rule-engine`（连带 model+feel）在 flow 进程内**同步求值**——µs 级、无网络、可离线。适合延迟敏感/边缘部署。

---

## 三、推荐目标架构：接缝(B) + HTTP 优先

{{FIG:target}}

**推荐组合 = B（DecisionProvider 接缝）+ HTTP 后端为默认、内嵌后端为可选。** 理由：

1. **rules 保持「决策的系统之源」**——决策的编写、发布、版本、激活、审计、gap/overlap、仿真全部留在 rules；flow 只借一个接缝去「用」决策。职责单一、不重复造决策。
2. **HTTP 优先 = 独立部署/扩缩/版本/演进**——契合两者既有的独立微服务 + 门户反代 + center_client 拓扑，不引入编译期强耦合。决策热更新（改规则不必重启 flow）天然获得。
3. **内嵌后端作为逃生舱**——对「µs 级 / 离线 / 边缘」场景，用同一个 `DecisionProvider` trait 换一个实现即可，业务无感。
4. **A 与 B 不冲突、可平滑演进**——先用 A（delegate）零风险跑通闭环（P1），再落地 B（接缝）作为最终形态（P2）；两者可长期共存（重决策走 delegate 的异步路径，普通决策走 businessRuleTask 的 provider）。

**决策的可解释性回写流程**（③）：rules 每次返回 `logId + 逐节点 trace + timingUs`。把它们随决策结果一并写入 flow 的**实例/变量历史**，于是「一个流程里为什么这样判」在流程侧就可解释、可审计、可回放——这是两个引擎融合后 **1+1>2** 的地方：**带可解释决策的流程**。

---

## 四、调用契约：flow 变量 ↔ rules facts

集成的全部技术含量，浓缩在这一层「映射适配」。好消息是两侧协议已高度对齐，只差一个转换器。

{{FIG:mapping}}

**一次往返**：`DecisionProvider`/`Delegate` 从实例变量里挑出决策所需子集作为 `input`，附上租户/身份头，`POST /api/rules/v1/decisions/{key}/evaluate`，解 `ApiResp`（**先判 `code==0`**）拿到 `data.output`，merge 回变量；`logId/trace` 另存历史。

**需要在契约里定清的四件事**（都有现成对策，均非阻塞）：

1. **表达式语言不通用**：flow 的 `${amount > 5000}` 与 rules 的 FEEL `amount > 5000 and level = "gold"` **语法不互通**（`&&`/`||` vs `and`/`or`、`==` vs `=`、三元 vs `if/then/else`、rules 独有区间 `[1..10]` 与 `in` 成员）。**但运行期天然规避**——两侧只交换 JSON 变量，各自解析各自的 DSL；作者态各用各的设计器。这不是运行时问题，只是**作者态体验**问题（见 §五 P3）。
2. **决策标识与版本**：约定 `decision_key` 的命名空间（建议带域前缀，避免与 flow 内置 key 撞）。HTTP `/evaluate` **只评「当前激活版」**（tenant 内 `active=TRUE` 的最高版本，无草稿则回退草稿）；若某流程要**钉住**特定决策版本，走内嵌库（自带 `DecisionDef` 版本）或给 rules 增一条带版本的评估路由。
3. **租户对齐**：两侧都是 **db-per-tenant**。flow 的 tenant 必须能映射到 rules 的 `X-Tenant`（或 `api_keys` 里 key→租户 的映射），否则在 rules 的租户库里查不到该 `decision_key`。这是**部署契约**，不是代码问题。
4. **失败与超时**：rules 的**业务失败是 HTTP 200 且 `code≠0`**（不是 HTTP 4xx/5xx），必须按 `code` 判；未知 key = 404；鉴权失败 = 裸 401。把这些映射为 flow 的**决策错误 → Incident 或错误边界事件**；重规则（大图/Rhai 脚本）走**异步 serviceTask / 外部 worker** 以免阻塞令牌线程，并设超时。

---

## 五、分阶段落地路线

不必一步到位。每个阶段独立可验证、可回退。

{{FIG:roadmap}}

- **P0 · 契约对齐（不写码）**：定清租户名映射、`decision_key` 命名空间、变量↔input/output 映射规则、错误/超时/回写策略；确认「HTTP 优先」。产出一份接口契约文档即可开工。
- **P1 · 最小可用（零引擎改动）**：新增 `RulesEngineDelegate` 适配器 + rules 的服务目录项，用 `serviceTask` 同步调 rules 跑通**一条真实业务链**（如「单据 → 决策定科目/定审批人 → 继续流程」）。目的是**零核风险地证明闭环**。
- **P2 · 语义化接缝（最终形态）**：引入 `DecisionProvider` trait（默认内置、向后兼容），`HttpRulesDecisionProvider` 按 `decision_key` 调 rules；把 `logId + trace` 回写实例/变量历史；**逐步弃用/降级 flow 内置决策表**（保留为简单内联决策的兜底或彻底迁走）。
- **P3 · 设计态融合（前端）**：flow 节点从 rules 的决策注册表里**选一个 `decision_key`**；决策的编写/仿真/审计归 rules 设计器；flow 自带的 decision-designer 降级为**选择器/查看器**；门户里可从 flow 节点**跳转到 rules 设计器**编辑。这一步彻底消解「两套决策表 + 两种 DSL」的作者态割裂。
- **P4 · 可选增强（按需）**：内嵌后端（µs/离线）；异步/外部 worker 跑重规则；版本钉住；决策访问接入数据权限；随信任度**灰度放开自主度**。

---

## 六、风险与开放决策

| 项 | 判断 | 对策 |
| --- | --- | --- |
| 两套决策模型并存期的一致性 | 中 | P2 起以 rules 为系统之源，flow 内置只作兜底并逐步迁移；避免同一决策两处维护 |
| 同步 HTTP 延迟进入令牌线程 | 中 | 普通决策同步（µs~ms 级可接受）；重规则走**异步 serviceTask/外部 worker**，设超时 + Incident 兜底 |
| 两种表达式 DSL 的作者困惑 | 中 | 运行期已规避；作者态经 P3 统一到 rules 设计器；长期可评估 flow 网关也改用 FEEL（可选、非必须） |
| 跨服务故障域（rules 挂了流程卡住） | 中 | 超时 + 重试（异步路径自带 SKIP-LOCKED 重试/死信）+ 决策错误路由到错误边界；关键路径可用内嵌后端消除网络依赖 |
| 租户/身份传播出错 | 低 | 协议已对齐（flow 出站头 = rules 入站头）；P0 把租户映射写死进契约 + 冒烟验证 |
| 版本不可钉住（HTTP 只评激活版） | 低 | 需钉版本用内嵌库或加带版本路由；多数审批场景「用激活版」即正确 |

**几个需要你拍板的开放决策**：
1. **接入形态**：先走 A（delegate，最快）还是直接上 B（接缝，最终形态）？（建议 A→B 演进。）
2. **默认后端**：HTTP（独立/热更）还是内嵌（µs/离线）为默认？（建议 HTTP 默认、内嵌可选。）
3. **flow 内置决策表的去留**：P2 后是彻底迁走，还是保留为「简单内联决策」的轻量兜底？
4. **作者态**：是否在本轮就做 P3（设计态融合），还是先只做运行时（P1/P2）、设计态维持双轨。

---

## 七、一句话总结

**两个引擎架构同源、协议已对齐、无历史耦合——融合不是「能不能」，而是「用哪个接缝、分几步走」。** 推荐：以 rules 为决策的系统之源，在 flow 引入 `DecisionProvider` 注入接缝、HTTP 优先调用、把决策 trace 回写流程历史；先用现成的 delegate 路径零风险跑通（P1），再落地接缝作为最终形态（P2），最后收敛设计态（P3）。产出的不是「流程 + 规则」两个工具，而是**「带可解释决策的智能流程」**这一个能力。

---

> **说明**：本方案不含任何代码改动，为设计与可行性评估。全部图表为自绘、内嵌 base64 的 SVG（`<img>` 标签），工具链见 `docs/flow-rules-integration/assets/`。技术结论均来自对 `cmx-flowengine/` 与 `cmx-rulesengine/` 当前源码的逐行核对（含 `businessRuleTask`/`DecisionTable`/`JavaDelegate`/`HttpDelegate` 与 rules `/evaluate` 契约、engine 库签名、依赖足迹、鉴权/租户/版本机制）。
