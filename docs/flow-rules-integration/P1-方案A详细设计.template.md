# P1 详细设计 · 方案A（serviceTask + RulesEngineDelegate · HTTP 默认）

> flow 调用 rules 的最小可用集成 · 零引擎核改动 · 决策仍以 rules 为系统之源
> 2026-09-02 · **四项开放决策已按推荐值定案（见 §十一）→ 实现就绪**

## 已定方向（本期基线）

| # | 决策 | 含义 |
| --- | --- | --- |
| 1 | **选 A** | 用 `serviceTask` + `RulesEngineDelegate` 调 rules；**不碰 flow 引擎核心** |
| 2 | **HTTP 默认** | 走 `POST /api/rules/v1/decisions/{key}/evaluate`，独立部署、决策热更 |
| 3 | **保留轻量兜底** | flow 内置 `businessRuleTask` + `DecisionTable`（FIRST/COLLECT）**原样保留**，作简单内联决策的兜底 |
| 4 | **暂不做 P3** | 不做设计态/前端融合；决策仍在 rules 既有设计器编写，flow 只引用 `decision_key` |

**本期范围**：只做「运行时能从流程里调用 rules 决策」这一件事，端到端跑通、可灰度、可回退。

---

## 一、组件与改动清单（诚实边界）

**新增（仅 3 处，均在 flow 侧、且可 env 关闭）：**

1. `cmx-flow-adapters` 新增 `RulesEngineDelegate`（实现 `JavaDelegate`，照 `HttpDelegate` 的样子，但打到 rules 的评估路径并做 ApiResp 解析）。
2. `cmx-flow-app/src/engine.rs` 装配处新增一段 **env 门控** 的注册逻辑（镜像现有 `FLOW_DELEGATE_MODE=http` 那段）。
3. 配置：新增 `FLOW_RULES_*` 环境变量 + `[service_rpc.services]` 里一条 rules 服务目录项。

**不动（关键）：** flow 引擎核心（`run_to_wait`、令牌语义）、`businessRuleTask` 与内置 `DecisionTable`、BPMN 编译器、flow 其它 11 个 crate、**以及 cmx-rulesengine 全部**（复用其现成 `/evaluate`，rules 侧零改动）。

> 因为不改编译器，`serviceTask` **无法携带**「decisionKey / 输入输出映射」这类节点级参数（当前 IR 只有 `delegate / is_async / external_topic`）。因此本期采用**约定优于配置**：**delegate 键即决策键**（见 §三）。节点级 I/O 裁剪需要改编译器解析 `<field>`，明确留到后续，不在本期。

---

## 二、运行时调用序列

{{FIG:a-runtime}}

一次决策 = 令牌到达 `serviceTask` → `RulesEngineDelegate` 取变量拼 `input` → 经 `cmx-service-rpc` POST 到 rules `/evaluate`（鉴权头自动带上）→ rules 评估激活版返回 `ApiResp` → 判 `code==0` 后把 `output` merge 回变量、把 `logId/trace` 写进 `__decisions` → 令牌续流。**普通决策同步、µs~ms 级**；大图/Rhai 重规则加 `flowable:async="true"` 走异步。

---

## 三、节点建模约定（BPMN 作者侧）

**一个 rules 决策 = 一个 `serviceTask`，其 `delegate` 键 = `rules:` 前缀 + 决策键。**

```xml
<!-- 同步：普通决策 -->
<serviceTask id="scoreCredit" name="信用评分"
             flowable:delegateExpression="rules:creditScoring">
  <!-- 可选：挂错误边界，捕获「业务失败」走补偿/人工路径 -->
</serviceTask>
<boundaryEvent id="onDecisionFailed" attachedToRef="scoreCredit">
  <errorEventDefinition errorRef="decisionFailed"/>
</boundaryEvent>

<!-- 异步：大图/重规则，避免阻塞令牌线程 -->
<serviceTask id="amlScreen" name="反洗钱筛查"
             flowable:delegateExpression="rules:amlScreening"
             flowable:async="true"/>
```

约定要点：
- **`delegate` 键 = `rules:<decisionKey>`**；`rules:` 前缀是「路由到规则引擎」的标记（无前缀的 delegate 走原有 Java/HTTP 逻辑，不受影响）。
- 引擎启动时**扫描已部署定义**里所有 `rules:` 前缀的 delegate 键，为每个键注册一个绑定到对应 `decisionKey` 的 `RulesEngineDelegate`（或用配置 allowlist 显式声明——具体扫描 vs 声明为实施细节）。
- **输入**：P1 默认把**全部实例变量**作为 `input`（与现有 `HttpDelegate` 传全量变量一致）；决策只用到自己声明的输入列，多余变量无害。
- **输出**：把 rules 返回的 `output` 对象**整体 merge** 回实例变量；键名冲突由决策输出列命名规避（建议决策输出加业务前缀，如 `credit_tier`）。
- **兜底仍用 `businessRuleTask`**：简单的、纯内联的两三行判断继续用内置决策表，不必上 rules（见 §六）。

---

## 四、适配器契约：RulesEngineDelegate

**接口**（复用 flow 现成 trait，无新接口）：`async fn execute(&self, ctx: &mut DelegateContext) -> Result<(), DelegateError>`。

**请求**（经 `cmx-service-rpc` 的 `ServiceRpcHandle` 发出）：

```
POST  {rules 服务目录 base}/api/rules/v1/decisions/creditScoring/evaluate
Headers（由 cmx-service-rpc 传输层自动注入）:
  X-API-Key: cmx_sk_...            # 服务身份（映射到 rules 租户）
  X-Delegated-User-Token: Bearer … # 真实办理人（若在 task_local 存在）
  X-Tenant: <flow 当前租户>          # 见 §五「租户契约」
Body:
  { "input": { …全部实例变量… },
    "options": { "trace": true, "log": true } }
```

**响应处理**（`ApiResp{ code, msg, data }`，camelCase）：

```
code == 0  → data = { output, logId, timingUs, trace?, failure? }
            ① ctx.variables.merge(output)
            ② 追加 ctx.variables["__decisions"] += { key, logId, timingUs, at }
               （trace 体量大，默认只存 logId；FLOW_RULES_TRACE_PERSIST=full 时存 trace）
code != 0  → 业务失败 → DelegateError::Bpmn{ code:"decisionFailed", message: msg }
HTTP 404   → 未知 decisionKey（部署/配置错）→ DelegateError::Generic(...)
HTTP 401   → 鉴权/租户映射错 → DelegateError::Generic(...)
超时/连接失败 → DelegateError::Generic(...)（异步模式由 job 层自动重试）
```

> **可解释性红利**：即使是 P1 的 delegate 路径，`__decisions` 里留存的 `logId`（+ 可选 trace）会随实例进入 flow 的变量历史 —— 「这个流程为什么这样判」在流程侧就能查、能审计。这是 A 方案顺带拿到的收益。

---

## 五、错误与超时处理矩阵

{{FIG:a-matrix}}

设计要点：
- **业务失败（`code≠0`）映射为 `Bpmn{code}`**，好处是流程设计者可在该 `serviceTask` 上挂**错误边界事件**优雅接住（如「评分不通过 → 转人工」），而不是一律 Incident。
- **配置/鉴权类错误（404/401）映射为 `Generic` → Incident**，交运维处理（这类是部署问题，不该走业务补偿路径）。
- **超时/连接失败**：同步 → Incident；异步 → 引擎自带 `SKIP-LOCKED` 重试（3 次 / 30s 退避）→ 死信。
- **注意引擎约定**：异步模式下 delegate 失败默认走「重试/死信」而非错误边界；若异步也想让业务失败走错误边界，需到 P2 接缝层显式路由 —— 本期不做。
- **重规则一律异步**：大 JDM 图 / Rhai 脚本可能是数十~数百 ms，用 `flowable:async="true"` 避免阻塞令牌线程；`cmx-service-rpc` 超时建议 2–5s。

---

## 六、两层决策分工（呼应「保留轻量兜底」）

| 用哪个 | 场景 | 载体 | 引擎 |
| --- | --- | --- | --- |
| **rules 决策** | 需要 11 命中策略 / 决策图 / FEEL / gap-overlap / 归因，或需集中治理与复用的业务决策 | `serviceTask` + `RulesEngineDelegate` | cmx-rulesengine（HTTP） |
| **内置兜底** | 两三行的纯内联判断、临时/局部、不值得进决策中心 | `businessRuleTask` + `DecisionTable` | flow 内置（同进程） |

两者**互不影响、可共存**：内置决策表一行不动；rules 决策是新增能力。团队按「决策是否值得进决策中心」二选一即可。

---

## 七、配置与装配

**环境变量**（默认关闭 → 不启用即零行为变化）：

```
FLOW_RULES_MODE=off | http           # 默认 off（集成禁用）；http 启用
FLOW_RULES_SERVICE=rules             # cmx-service-rpc 服务目录键
FLOW_RULES_TRACE_PERSIST=logid|full|off   # 决策 trace 回写粒度，默认 logid
# 超时/重试沿用 cmx-service-rpc 既有配置
```

**服务目录**（`flow-server*.toml`，rules 的可达地址；生产走 Nacos 发现）：

```toml
[service_rpc.services]
rules = { url = "http://127.0.0.1:8094", discovery = "cmx-rulesengine" }
```

**装配**：在 `cmx-flow-app/src/engine.rs` 现有「按 `FLOW_DELEGATE_MODE=http` 注册 HttpDelegate」那段旁边，加一段：`FLOW_RULES_MODE=http` 时，扫描定义中 `rules:` 前缀的 delegate 键，为每个键 `engine.register_delegate("rules:<k>", RulesEngineDelegate::new(rpc_handle, "<k>", cfg))`。

**租户契约（P0 必须先定）**：两侧均 db-per-tenant，rules 靠 header 定位租户库。二选一：
- **(a) off/单租户或默认租户**：rules `auth.mode=off`，flow 出站带 `X-Tenant=<flow 租户>`（须确认 `cmx-service-rpc` 传输层会转发/可注入 `X-Tenant`）。最简单，适合 P1 冒烟与单租户。
- **(b) 多租户 api-key 映射**：rules 配 `auth.api_keys="cmx_sk_x:tenantA,..."`，flow 用对应 key，key→租户由 rules 解析。适合多租户生产。

> **已定案（见 §十一）**：P1 取 **(a) rules `off` + flow 带 `X-Tenant`**；多租户/生产再切 (b)。唯一运行前置：确认 `cmx-service-rpc` 能注入/透传 `X-Tenant`（单默认租户下两侧均 `default`，可直接跑通）。

---

## 八、测试与验收

**单测（`cmx-flow-adapters`）**：`RulesEngineDelegate` 映射逻辑 —— 用假的传输/响应桩验证：`code==0` → `output` 正确 merge + `__decisions` 写入 `logId`；`code!=0` → `Bpmn{decisionFailed}`；404 → `Generic`；空 output/缺字段的健壮性。

**集成 / 真机 E2E**（flow :8091 + rules :8094，均 off 模式、`X-Tenant=default`）：
1. 在 rules 用其**现有设计器**建并发布一个决策（如 `creditScoring`：input=`amount/level` → output=`credit_tier/discount`）。
2. 部署一个流程：start →（网关设置变量）→ `serviceTask delegate="rules:creditScoring"` → 排他网关按 `credit_tier` 分支 → end。
3. 发起实例、断言：`output` 已 merge 进变量、网关按决策结果正确走向、`__decisions` 里有 `logId`。
4. 反例：`delegate="rules:notExist"` → 令牌落 **Incident**；决策业务失败 + 挂错误边界 → 走**边界路径**。
5. 异步：`flowable:async="true"` 的重决策 → `WaitingAsync` → 轮询完成；停 rules 制造超时 → 观察**重试→死信**。
6. 冒烟脚本 `flow-rules-smoke.sh`（幂等：建决策 → 部署 → 发起 → 断言 → 清理）。

**验收标准**：以上 6 项全绿；`FLOW_RULES_MODE=off` 时行为与今天完全一致（零回归）；内置 `businessRuleTask` 决策不受影响。

---

## 九、上线与回退

- **默认关闭**：`FLOW_RULES_MODE=off` 出厂，不启用即无任何行为变化、无回归风险。
- **灰度**：先在测试租户开 `http`，跑冒烟 → 单业务流试点 → 逐步放开。
- **回退**：把 `FLOW_RULES_MODE` 置回 `off`（或把节点改回 `businessRuleTask` 用内置兜底）即可，秒级、无数据迁移。
- **零核风险**：不动引擎/模型/编译器，只加一个 env 门控的适配器 —— 出问题面被限制在「一个新 delegate + 配置」。

---

## 十、明确不在本期

- **P3 设计态融合**（flow 节点选决策、跳转 rules 设计器、designer 降级）—— 已定暂不做；决策在 rules 现有设计器编写。
- **节点级输入/输出映射裁剪**（需改编译器解析 `<field>`）—— P1 传全量变量；裁剪留后续。
- **DecisionProvider 注入接缝（方案 B）** —— 作为最终形态，留 P2；A 与 B 可平滑演进、不冲突。
- **版本钉住 / 内嵌库后端 / 数据权限接入** —— 按需后续。

---

## 十一、四项决策定案（已按推荐值敲定）

开放项全部收敛，本设计进入**实现就绪**状态。

{{FIG:a-decisions}}

| # | 决策项 | 定案值 | 理由 |
| --- | --- | --- | --- |
| 1 | 租户契约 | **rules `off` 模式 + flow 出站带 `X-Tenant`** | 单/默认租户零配置即通；多租户或生产再切 `api-key→租户` 映射。实施时须确认 `cmx-service-rpc` 能注入/透传 `X-Tenant`；若暂不能，则 P1 退化为单默认租户（两侧 `default`），多租户走 api-key |
| 2 | 业务失败落点 | **`DelegateError::Bpmn{ code:"decisionFailed" }`** | 流程设计者可挂错误边界优雅接住（转人工/补偿）；未挂边界时按引擎既有路由自然回落 Incident —— 两种用法都安全 |
| 3 | decisionKey 暴露 | **随定义加载/部署自动扫描 `rules:` 前缀注册** | 免人工维护 allowlist，覆盖启动装载与运行时热部署；若无现成的定义加载钩子可挂，则退化为配置 allowlist 作为实施兜底 |
| 4 | trace 回写粒度 | **默认只存 `logId`（可 `=full` 存全量）** | rules 侧已按 `log:true` 存全量 trace 于其决策日志，flow 只需 `logId` 作指针即可回查、省快照空间；需要内联全量时置 `FLOW_RULES_TRACE_PERSIST=full` |

**配置基线（P1）**：

```
FLOW_RULES_MODE=http               # 出厂 off（零回归）；置 http 启用集成
FLOW_RULES_SERVICE=rules           # cmx-service-rpc 服务目录键
FLOW_RULES_TRACE_PERSIST=logid     # 决策 trace 回写粒度

[service_rpc.services]
rules = { url = "http://<rules-host>:8094", discovery = "cmx-rulesengine" }

# rules 侧：auth.mode=off（P1）；flow 出站附 X-Tenant=<当前租户>（+ 自动带 X-API-Key / 用户令牌）
```

**至此四项开放决策全部敲定，本设计可直接进入实现。** 改动集中在：`cmx-flow-adapters` 一个新文件（`RulesEngineDelegate`）+ `cmx-flow-app` 装配一段（env 门控注册）+ 配置；**rules 侧零改动**。唯一需在编码前落实的运行环境前置项是「§七 租户契约的 `X-Tenant` 注入验证」——非阻塞，单默认租户下可直接跑通。

---

> **说明**：本文为详细设计，不含代码改动。技术结论均来自对 `cmx-flowengine`（`JavaDelegate`/`HttpDelegate`/`DelegateContext`/async job）与 `cmx-rulesengine`（`/evaluate` 契约/`ApiResp`/鉴权/租户/版本）当前源码的逐行核对。图为自绘、内嵌 base64 SVG（`<img>`），工具链见 `docs/flow-rules-integration/assets/`。
