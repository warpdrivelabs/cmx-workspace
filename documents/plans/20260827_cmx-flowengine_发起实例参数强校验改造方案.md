# cmx-flowengine 发起实例参数强校验改造方案

> 背景：《MDM 主数据接入流程引擎指南》§6.3.1 参数梳理结论——`POST /api/flow/instances`
> 引擎层面几乎全可选，唯一结构必填是 `bizLink.bizTable` / `bizLink.bizId`；
> 单据审批形态下业务必须的参数（definitionKey / initiator / variables.bizTable 等）
> 目前靠调用方自觉，漏传不报错、链路静默残废。本方案规划"哪些参数不能不传"如何落成
> 引擎强校验。配套文档：`documents/20260818_cmx-mdm_主数据接入流程引擎指南.md` §6.3.1。

## 一、现状与缺口（均已对源码核实）

| # | 参数 | 现状 | 漏传后果 | 核实坐标 |
|---|---|---|---|---|
| G1 | `definitionKey` | `#[serde(default)] Option<String>`，`unwrap_or_else(|| "credit_approval".to_string())` 兜底 **demo 流程** | 静默起错流程（演示实例入库），无任何报错 | `handlers.rs::start_instance` |
| G2 | `variables.initiator` | T0 从认证上下文兜底注入；**脚本裸调（无用户上下文）时就是缺** | 「我发起的」列表失联、撤回被拒 | `handlers.rs::start_instance` T0 段 |
| G3 | `variables.bizTable` / `bizId` | 自由 KV，无校验 | 待办任务点击打不开单据详情页 | `handlers.rs` tasks/my 投影 |
| G4 | `bizLink.bizTable` / `bizId` | ✅ 已是结构必填（无 serde default），DB 绑定失败自动取消实例 | ——（唯一已有硬校验处） | `handlers.rs::BizLinkReq` |
| G5 | varSchema 声明的 required 变量 | 有校验机制但**默认 lenient 只告警**，形同虚设 | 契约存在但不拦人 | `engine.rs::start_process_inner` 变量校验块（policy 默认 lenient）、`var_schema.rs::VarDecl.required` |

关键结论（两项，均已核实）：

1. **强校验基础设施已经存在**——BPMN `<extensionElements><cmx:varSchema>` 声明变量契约
   （`compiler.rs::parse_var_schema` → `Definition.var_schema` / `var_validation`，
   `ir.rs`），VarDecl 支持 `required: bool`；
2. **varSchema 校验不在 HTTP 层，而在 `engine.start_process_inner` 内部**
   （engine.rs 校验块，policy 默认 lenient 仅 warn）——消息启动（message start）、
   callActivity 子流程启动等**所有发起路径都经过同一个校验点**（worker-sdk /
   服务编排 / WASM 插件均无直调 start_process 的旁路，全仓 start_process 非 test
   调用点共 4 处：HTTP handler、demo main、消息启动、子流程）。因此 D2/D3 一旦生效，
   strict 天然兜底全部路径；缺口只在「发布闸没关严 + 没有一个定义真正用它」
   （grep 全部 .bpmn 无任何 varSchema 声明）。

## 二、目标形态

参数契约分三级，各级有不同的"不能不传"：

| 级别 | 含义 | 载体 |
|---|---|---|
| 结构必填 | 缺了 HTTP 400，引擎无条件保证 | `BizLinkReq` 字段（已有）；D1 追加 `definitionKey` |
| 业务必填 | 该定义声明了就要有，漏发起即被拒 | 定义级 `varSchema(required) × strict`（D2/D3） |
| 推荐项 | 缺了能跑，但日志定位提醒 | 告警日志（D4） |

## 三、改造项

### D1 · definitionKey 必传化（P0，小改）

- `StartReq.definition_key` 去掉兜底（`handlers.rs::start_instance` 内
  `unwrap_or_else(|| "credit_approval".to_string())` 一行），改为显式缺失报错：
  `"缺少 definitionKey（不再回落 demo 流程 credit_approval）"`。
- **拒绝语义（已拍板）**：`FlowError` 新增 `BadRequest` 变体 → **HTTP 400**（resp.rs
  错误映射加一条臂），`definitionKey` 缺失/空白由此拒绝。注意两条结构必填路径的实测
  状态码并存：BizLinkReq 字段缺失走 axum 0.8 Json rejection 的 **422**（引擎零改动
  自动拒），definitionKey 走本改造自控的 **400**——共同点是都非 200 成功信封。
- **空串边界**：serde 下 `"definitionKey": ""` 是 `Some("")` 不会命中 None 分支，
  会走到 get_definition 报"定义不存在"——语义混乱。实现时 trim 后判空，统一归入
  "缺少 definitionKey"（demo 页面 defKey 输入框留空即触发此形态）。
- **存量影响面（已全量排查，实测零命中裸调）**——现网全部 HTTP 发起方均显式带 key：
  | 发起方 | 位置 | 现状 |
  |---|---|---|
  | MDM CR 审批 | `cmx-mdm/.../flow_client.rs::start_instance` | 显式传 toml 配置 key |
  | 报表关账流程 | `cmx-report/.../consol-store-pg/flow_client.rs::start_close_instance` | 显式传，默认 `consol_close` 可 env 覆盖 |
  | 工作台发起页 | task-form.js submitStart | props 显式传 |
  | 引擎 demo 页面 | web/index.html 发起表单 | 页面输入框显式传 |
- 不受 D1 影响的内部路径：demo main.rs / 消息启动 / 子流程走 engine 层 API 本就必传 key 参数。
- 兼容性：属行为破坏变更，发版说明标注；demo 流程仍可通过显式传 key 使用，仅删除"静默兜底"。

### D2 · varSchema required × strict 发布闸（P0，核心）

- 问题：`var_validation` 默认 lenient，定义即使声明了 required 也只 warn。
- 改造：新增共用校验函数 `ensure_publishable(var_schema, var_validation)`——若
  schema 含任一 `required = true` 声明且策略不是 `strict`，报错并给出出路：
  "声明了必填变量必须 `cmx:varValidation="strict"`；确需宽松请先编辑草稿去掉 required 声明"
  （错误文案即操作指引，防存量遗留定义卡住操作者）。
- **闸必须同时堵两个入口**（只堵 publish 不够）：
  1. `definitions/{key}/publish` handler：在调用 `def_svc.publish` **落库之前**执行
     （编译产物已含 schema，属"先检查后落库"，不改变 hot_load 失败仅告警的既有语义）；
  2. `definitions/{key}/versions/{version}/activate`（`handlers.rs::activate_definition_version`
     直热装载历史版本、完全不经过 publish 校验）——activate 前同样 compile → 执行闸。
     否则闸上线前的历史 lenient+required 版本可经版本管理 UI 回切绕过。
- 遗留口径：闸对**已生效的历史定义不回溯**（它们重新 publish / activate 时才受闸，
  受闸时报错信息给出去路）。
- 开关实现：config 项 `[flow] enforce_strict_required_on_publish`（默认 true）+ 环境变量
  `FLOW_PUBLISH_STRICT_REQUIRED=off` 覆盖——平台内嵌形态下门户 toml 无 [flow] 段自然回落
  默认常开，环境级逃生门走 env 更贴合集群部署。

### D3 · MDM 定义落地 varSchema（P0 配套）

- `mdm_cr_approval` BPMN process 级 extensionElements 补充（`VarSchema` 是
  `#[serde(transparent)]` 的**顶层数组**；type/source 为 SCREAMING_SNAKE_CASE，
  camelCase 已由 VarDecl rename 处理）：
  ```json
  [
    {"name":"initiator","type":"STRING","required":true,"source":"START_PARAM"},
    {"name":"docNo","type":"STRING","required":true},
    {"name":"bizTable","type":"STRING","required":true},
    {"name":"bizId","type":"STRING","required":true}
  ]
  ```
  （以 `var_schema.rs::VarDecl` 实际 serde 拼写为准。）
- `initiatorName` 为展示快照变量，展示侧可按 initiator 回查，**不声明 required**
  （保持 cr.rs 现状：代提交等场景合法缺省）。
- **BPMN 改动落点（资产真源规则）**：改 `cmx-container/assets/flow/data/definitions/mdm_cr_approval.bpmn`
  （唯一真源），随后执行 `./scripts/publish-assets.sh flow` 同步。注意仓内现存三份同名副本
  ——assets 真源、`cmx-container/databack/flow/definitions/`（备份）、`cmx-flowengine/data/definitions/`
  （未跟踪工作目录）——禁止直接改后两者。
- 随 Step 2 部署链路（draft→validate→publish→forms）重新发布后生效；发布前先用
  validate 干跑确认 schema JSON 合法。

### D4 · 交叉一致性提醒（P1，可选）

- 带 `bizLink` 但 `variables` 缺 `bizTable`/`bizId`（或反之）→ 发起成功但记 warn 日志
  提示两条消费链路不同步。只提示不拒：纯展示场景反向差异是合法用法。
- 落点约束：bizLink 只存在于 HTTP StartReq（engine 层 API 无此概念），提醒逻辑只能放
  `handlers.rs::start_instance` 的 bizLink 绑定段附近，无法下沉 engine。

### D5 · 不做的事

- `businessKey` 不做必填（撤回/列表靠 instance id 与 initiator 即可运转）；
- `orgId` / `dimensions` 维持可选（仅维度路由场景有意义）；
- 不在引擎层硬编码"哪些变量必填"——业务必填集合随定义走（D2/D3 的载体是每个定义自己的 schema）。

## 四、验收标准

1. 不带 `definitionKey`（含空串 / 全空白形态）发起 → 400 明确报错（不再是 credit_approval 实例）；
2. `mdm_cr_approval` 发布后：漏 `initiator` / `docNo` / `bizTable` / `bizId` 任一发起 →
   被拒。**分层断言**：引擎层 `start_process` 返回 `Err(VarValidation)`；HTTP 层信封返回
   合并违规文案（现状 `Error::VarValidation(String)` 是多条违规以 `"; "` join 的单字符串，
   经 `engine_err` 转 business 错误——**无结构化违规数组**；如需机器可读明细，须把
   `Vec<VarViolation>` 序列化进 FlowError payload，列为独立增强项不阻塞本期）；
3. 未声明 varSchema 的内部流程（如巡检）发起行为不变；消息启动 / 子流程路径同受
   strict 校验兜底（engine 层校验点唯一所致，属正向收益）;
4. activate 回切一个 lenient+required 的历史版本 → 同样被闸拒绝；
5. 测试实施说明：`cmx-flow-tests/tests/var_schema_start.rs` 现有 6 个用例全部是引擎层
   直调范式（crate 内无任何 HTTP 测试基建）。验收 2/4 引擎层断言直接扩文件即可；
   验收 1/4 的 HTTP 层断言需新增 oneshot 样板——用 `tower::ServiceExt::oneshot` 挂
   `lib.rs` 公开的 `flow_routes()` 构造 JSON body 断言反序列化错误路径（约 30 行样板，
   不引 reqwest 不起服务器）；发布闸本身单测直测 `ensure_publishable` 函数纯逻辑;
6. 工作台/demo/report/MDM 四类调用方全量 grep 复查无裸 `{}` body 发起（首轮排查已零命中）。

## 五、分期与风险

| 期 | 内容 | 说明 |
|---|---|---|
| P0 | D1 + D2 + D3 | 同一版本内完成。D1 影响面实测零命中裸调（四类发起方全显式带 key），无前置改造依赖；D2 闸须 publish + activate 双入口同版上线 |
| P1 | D4 提醒日志、VarViolation 结构化 payload（验收 2 增强项） | 低优先 |
| — | 存量环境 | G1 只影响"从来没传过 key 的调用方"（排查为零命中，删兜底纯纠偏）；D2 对已生效定义不回溯，重新 publish / activate 时才受闸 |

| 风险 | 说明与应对 |
|---|---|
| 子流程运行期新故障面 | varSchema 校验点唯一（`start_process_inner`），callActivity 子定义声明 required+strict 后，父流程推进期传入变量不足会在**运行期失败**而非发起边界——行为合理但属 D2/D3 生效后的新故障形态，MDM 定义落地时须核对父流程传给子流程的变量映射 |
| 开关取值源歧义 | 平台内嵌形态下 ConfigManager 读门户进程全局配置，门户 toml 无 [flow] 段回落默认 true——与"默认常开"预期一致；环境级关闭走 env 覆盖。**实施前确认内嵌环境 ConfigManager 实际加载的 toml 来源** |
| activate 绕闸遗漏 | 若实现时只堵 publish 忘了 activate，历史版本回切即旁路——验收标准 4 专门覆盖此场景 |
| D1 兼容破坏 | 删兜底影响静默依赖方——实测四类发起方全显式传 key、零命中，纯纠偏；灰度期仍可临时以环境变量恢复旧行为（`FLOW_START_DEFAULT_DEFKEY=credit_approval`），观察一个迭代后删除该逃生门 |

## 六、遗留确认项（实施前）

- ~~D1 拒绝语义口径~~ **已拍板**：真 HTTP 400（新增 `FlowError::BadRequest` 变体），
  否决"信封 code≠0 零改动"备选；
- 指南 §6.3.1 与本方案旧稿曾按行号引用 handlers.rs（581/594），工作区未提交改动后已漂移
  （StartReq 现 ~610 行）——两份文档已改为符号定位约定，后续引用一律「文件 + 符号名」。
