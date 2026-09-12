# BPMN 定义语法与部署契约（重参考 · P0：定义 × 审批定义分离）

> 模式A（定义创建）的完整语法契约。真源：`backend/cmx-flowengine` 路由表
> （`crates/cmx-flow-app/src/lib.rs` RouteDef）、审批模型（`crates/cmx-flow-model/src/approval.rs`）、
> usage 文档（`docs/usage/{02..06}-*.md`）；本文件是"写 spec + 部署 + 冒烟"所需的全部速查。

## 0. P0 核心契约（先读）

1. **BPMN 零审批属性**：办理人/抄送真源在**审批定义**（`approvalDefs`），spec 节点出现
   `assignee/candidateUsers/candidateGroups/candidates/cc` 直接被脚本拒绝。
2. **发起闸**：所有 userTask 节点都需要审批定义（旧的"静态 assignee 豁免"已废除）。
   漏配在 `approval-defs/startable` 预检暴露；运行期发起 400。
3. **流程定义 × 审批定义分离**：BPMN 描述拓扑，审批定义描述"谁办、怎么办"（含会签/或签，
   由编译器生成 MI 域——spec 不写 `mi`）。
4. **M1 拓扑**：userTask 出边必须恰 1 条；分支语义用排他/包容网关表达（脚本同步校验）。

## 1. spec JSON 结构（create_flow_def.py 输入）

```jsonc
{
  "key": "expense_v2",                       // 必填，= process id = 定义 key
  "name": "报销审批v2",                       // 展示名
  "start": {"id": "s", "name": "发起"},       // 可省：自动补 s → 唯一入度0节点
  "nodes": [ /* 见 §2 */ ],
  "flows": [
    {"from": "gw", "to": "dir", "condition": "${amount > 20000}", "name": "大额"},
    {"from": "s", "to": "mgr"}                // 无 condition = 无条件边
  ],
  "approvalDefs": {                          // 办理人真源（含 userTask 的流程必配，见 §3）
    "orgId": "org-root",                     // 必须真实存在于组织树；发起时 orgId 须一致
    "note": "v1 单签",
    "nodes": {
      "mgr":  {"inherit": false, "mode": "SINGLE",
               "objects": [{"kind": "USER", "value": "7503326638169403392"}],
               "emptyPolicy": "INCIDENT"}
    }
  },
  "forms": [{"formKey": "fin_form", "kind": "NATIVE", "nativePage": "…"}],  // 可选
  "deploy": {"server": "http://127.0.0.1:8091", "apiKey": "...",
             "note": "上线 v1", "publishedBy": "agent",
             "name": "…", "domain": "fi", "application": "…", "module": "…"},
  "smoke":  {"orgId": "org-root", "businessKey": "SMOKE-1",
             "variables": {"amount": 50000, "initiator": "7503326638169403392"},
             "expectActive": ["mgr"], "cancel": false}
}
```

endEvent 可省：出度 0 的节点自动连到唯一终点；终点多个时必须显式连边。

## 2. 节点类型 × spec 属性

| type | spec 属性 | 生成的 BPMN |
|---|---|---|
| `userTask` | `formKey`/`formMode`/`formFields`、`timers`（**办理人/会签禁止写在此处** → approvalDefs） | `<bpmn:userTask>` + `cmx:formKey` … |
| `timers` 数组 | `{duration:"PT30S", to:"目标节点", cancelActivity:false?}`（宿主必须 userTask；时长 ISO 8601 `P[nD]T[nH][nM][nS]`，不支持周/月/绝对时刻） | 挂宿主的 `<boundaryEvent>`（缺省中断型）+ 定时器出边 |
| `exclusiveGateway` / `inclusiveGateway` | `defaultTo`（缺省边的**目标节点 id**，脚本解析成网关 `default` 属性） | `default="<flowId>"` |
| `parallelGateway` | —（>1 出边=fork，>1 入边=join） | — |
| `callActivity` | `calledKey`（逻辑名，按组织路由）或 `calledElement`（直调 key）、`inVars`/`outVars`（`src:dst` 逗号串）或结构化 `in`/`out` 数组（**两者不可同给**） | `cmx:calledKey` / `<flowable:in>` `<flowable:out>` |
| `serviceTask` | `delegate` | `flowable:delegateExpression="${delegate}"` |
| `businessRuleTask` | `decisionRef` | `flowable:decisionRef`；**流程部署前须先 `POST /decisions` 注册决策表**，否则宽容跳过、网关恒走 default |
| `messageCatch` | `message`、`correlationVar` | `<intermediateCatchEvent>` + messageEventDefinition |
| `endEvent` | `terminate: true` → 一票否决终点 | `<terminateEventDefinition/>` |

**引擎黑名单**（spec 直接拒绝）：`task`/`scriptTask`/`sendTask`/`receiveTask`/`manualTask`/`eventBasedGateway`/`complexGateway`/`intermediateThrowEvent`。
**引擎支持但本脚本不生成**：`subProcess`（嵌入子流程）——用 callActivity 替代或手写 BPMN 后走 REST 部署。process 级 `startFormKey` spec 亦未暴露。
**已废除**：spec 级 `mi`（多实例）与审批定义的会签 mode 冲突——同给即拒；`cc` 移入 approvalDefs。

## 3. 审批定义（approvalDefs / NodeApproval 全字段）

保存端点 `POST /approval-defs/save`，body `{defKey, orgId, content:{nodes}, note?}`；
`content.nodes` 是 **{节点 bpmnId → NodeApproval}** 映射。整体新版本 + 激活，版本列表即审计
（`/approval-defs/versions/list`，回滚 `/approval-defs/versions/activate`）。

| NodeApproval 字段 | 值域 / 语义 |
|---|---|
| `inherit` | true（**缺省**）=继承上级组织配置（本组织不落库，解析时向上找）；false=本地配置生效 |
| `mode` | `SINGLE` 单签（缺省）/ `ANY` 或签（并发派发一人通过即过）/ `PARALLEL_COUNTERSIGN` 并行会签（全员完成）/ `SEQUENTIAL_COUNTERSIGN` 串行会签（逐个办理） |
| `objects` | 办理人规则数组 `[{kind, value}]`，见下表；value 支持 `${item.xxx}` 元素插值 |
| `assignWay` | P0 仅 `NONE`（缺省）；`BY_INITIATOR_NODE`/`BY_PREVIOUS_NODE` 为 P1 预留，保存校验拒绝 |
| `collectionVar` | 元素驱动集合变量名。与 objects **组合语义非互斥**：空+objects → objects 即人集；有值+objects 空 → 元素值直派；有值+objects 非空 → 元素插值后逐条解析 |
| `elementVar` | 每个子任务携带当前元素的变量名（元素驱动场景） |
| `completionCondition` | 完成条件（可空）。缺省按 mode 折叠：ANY 自动注入 `nrOfCompletedInstances >= 1`；其余自然完成 |
| `emptyPolicy` | 空审批人策略：`INCIDENT`（**缺省**，令牌停故障态可见可处置）/ `AUTO_PASS`（建 system 已办结任务留痕继续）/ `ASSIGN`（直派 `fallbackAssignee`，兜底无效仍 INCIDENT） |
| `fallbackAssignee` | emptyPolicy=ASSIGN 时的兜底办理人（user id） |
| `selfApproval` | `NORMAL`（**缺省**照常审批）/ `AUTO_PASS`（仅 Single 通道且解析结果恰为发起人一人时自动通过——**显式勾选才生效**，防死循环特例不许静默） |
| `cc` | 抄送 `[{kind, value}]` 数组（live 语义：办结时读最新展开）——P0 起抄送在此，不在 BPMN |

**办理人对象 kind 七类**（CandidateKind，SCREAMING_SNAKE_CASE）：

| kind | value 语义 |
|---|---|
| `USER` | **用户 id**（非账号名！admin=`7503326638169403392` 这类 id） |
| `ROLE` | 角色 code（cmx_role，经 cmx_user_role 反查用户） |
| `POSITION` | 岗位 code |
| `ORG` | 组织 id（取该部门**及子树**全部用户） |
| `ORG_LEADER` | 组织领导（value 可空=用实例所属组织；对应 cmx_org.leader_user_id） |
| `INITIATOR` | 发起人本人（value 忽略；读实例变量 `initiator`） |
| `INITIATOR_LEADER` | 发起人所属组织的领导（value 忽略） |

**继承与组织树**：orgId 必须存在于组织树（`cmx_org`），发起时的 orgId 须与配置口径一致否则 400。
`inherit:true` 的节点本组织不落库；`/approval-defs/coverage` 可预览"每节点生效配置来自哪个组织"；
`/approval-defs/orgs` 提供组织扁平行列表。

## 4. 条件表达式速记（网关/边 condition）

- 运算符：`&& || ! == != < <= > >= + - * /`（`and`/`or`/`not` 同义；单个 `&`/`|`/`=` 报错）。
- 变量路径支持点号嵌套与数组下标：`${order.customer.level == 'VIP'}`、`${items.0.qty > 10}`。
- MI 完成条件内置计数：`nrOfInstances` / `nrOfCompletedInstances` / `nrOfActiveInstances`。
- 无时间函数（NOW 等刻意排除）。真值：null/false/0/""/[]/{} 为假。
- **null 安全**：比较任一侧为 null → false → 走网关 default（写条件必知）。内置函数 18 个（LEN/CONTAINS/IN/COALESCE/IF…见 usage/05 §5.3 或 `GET /conditions/functions`）。
- **spec 里写原文**（`${amount > 20000}`），脚本负责 XML 转义（`>`→`&gt;`）。

## 5. 部署 REST 契约（五步链；POST，信封 `{code,msg,data}`，业务失败也是 HTTP 200）

| 步 | 端点 | body | 通过标准 |
|---|---|---|---|
| ① 校验 | `/api/flow/v1/definitions/validate` | `{bpmnXml}` | `code==0 && data.valid==true`（valid=false 是软失败！） |
| ② 草稿 | `/definitions/draft` | `{name, bpmnXml, updatedBy, domain?…}`（key 由 process id 派生） | `code==0` |
| ③ 发布 | `/definitions/publish` | **`{key, note?, publishedBy?}`（key 在 body）** | `code==0 && hotLoaded==true`（版本 +1 热装载无需重启） |
| ④ 审批定义 | `/approval-defs/save` | `{defKey, orgId, content:{nodes}, note?}` | `code==0`；orgId 不存在在此报错 |
| ④b 表单绑定 | `/forms/save` | `{formKey, kind, nativePage?…}`（可选） | `code==0`；不写 formKey → 待办中心走通用办结 UI |
| ⑤ 发起预检 | `/approval-defs/startable` | `{defKey, orgId?}`（orgId=逐节点 / 缺省=任一组织 EXISTS） | `data.nodes[].ok` 全 true |
| 冒烟发起 | `/instances/start` | `{definitionKey, orgId?, businessKey?, variables}` | `code==0`，断言 `activeNodes`/`openTasks` |
| 冒烟收尾 | `/instances/cancel` | `{id, reason?}` | `code==0` |
| 决策注册 | `/decisions` | 决策表定义（usage/05 §5.6.3） | businessRuleTask 流程**部署前必做** |

**大小写陷阱**：complete/reject/urge 等 body 是 camelCase（`instanceId`）；`claim/transfer/delegate/addsign` 是 snake_case（`instance_id`）。
定义详情用 `POST /definitions/detail {key, version?}`（旧 `GET /definitions/{key}` 已废）。

## 6. 鉴权与"办理需身份"（T0b 授权）

- 服务调用：`X-API-Key: <key>`（命中即服务身份）。
- **complete/reject/withdraw 等办理动作必须有用户身份**（且须是该任务 assignee 或候选）：加
  `X-Delegated-User-Token: Bearer <JWT>`（HS256，`sub`=用户 id、`tenant`=租户、**必须带 `exp`**）。
  dev 密钥见 `flow-server.toml [auth] jwt_secret`。python 铸 token：hmac-sha256 签 `{"sub":"<用户id>","tenant":"default","exp":<now+3600>}`。
- `FLOW_AUTH_MODE=off` 时**委托令牌验不了**（不初始化 JWT 密钥），但 off 模式可直接 `X-User: <uid>` 头建立用户身份（免铸 JWT，仅限本机开发）；jwt 模式办理用委托令牌。

## 7. 冒烟后推进验证（可选加深）

```bash
# 起实例断言首节点后：取 openTasks[0].id → complete（带委托令牌）→ 断言 activeNodes 走向预期分支；
# callActivity 场景：POST /instances/children {id} 断言子流程 key（组织路由结果）与父 waitingSubflow=true。
```

## 8. 与模式B（数据复原）的联动

- callActivity 的 `calledKey` 组织路由依赖 `cmx_flow_subflow_binding`（身份库）——目标库没有绑定时：
  先用模式B 的复原 SQL 灌入（examples/manifest-20260816.json 里有 fin_review/dept_review 两套矩阵），
  或直接给 callActivity 用 `calledElement` 直调。
- 审批定义存身份库 `cmx_flow_approval_def`（PK(def_key, org_id)）——空库复原时勿漏，否则发起闸全拦。
- 语义 BPMN 无 DI：设计工作台打开自动 BFS 布局，不必生成图形坐标。
- 生成物落盘建议：`backend/cmx-flowengine/docs/<测试集>/defs/<key>.bpmn`（与既有 defs 目录同级惯例），
  spec 文件与 BPMN 同目录留存，便于模式B 下一轮把该定义纳入复原范围。

## 9. 常见坑（模式A · P0）

| 坑 | 正解 |
|---|---|
| spec 节点写 `assignee`/`candidates`/`cc` | P0 已废除：脚本直接拒；办理人/抄送写 `approvalDefs.nodes.<id>` |
| 以为静态 assignee 可豁免发起闸 | 发起闸按 userTask **全量**校验审批定义，无豁免 |
| USER value 填账号名（如 `admin`） | 必须填**用户 id**（如 `7503326638169403392`），否则解析 0 人落 INCIDENT |
| orgId 随手填 | 必须真实存在于组织树（`cmx_org`）；发起 orgId 须与配置一致，否则 400 |
| userTask 直连两个终点 | M1 拓扑：userTask 出边恰 1 条；分支加**排他网关**（脚本与引擎双重拒绝） |
| 会签在 spec 写 `mi` | 会签/或签由 approvalDefs 的 `mode`+`collectionVar` 驱动，编译器生成 MI；同给即拒 |
| 以为抄送还在 BPMN | `cc` 已移入 NodeApproval.cc（live 语义：办结时读最新展开） |
| 条件里裸写 `>` / `<` / `&&` | spec 写原文，脚本转义；手改 BPMN 时必须 `&gt;` `&lt;` `&amp;&amp;` |
| 在**边上**写 `default="true"` | 引擎规定 default 是**网关属性**指向边 id；spec 用节点 `defaultTo` |
| validate 返回 HTTP 200 就当成功 | 软失败：必须看 `data.valid`；publish 响应看 `hotLoaded` |
| 漏跑 approval-defs/save 就发起 | 发起闸 400；部署后务必跑 `/approval-defs/startable` 预检 |
| 发布用 `POST /definitions/{key}/publish` 路径 | P0 改为 **key 在 body**：`POST /definitions/publish {key,…}` |
| 委托令牌缺 `exp` | jsonwebtoken 默认校验 exp，缺了直接验签失败（退化服务调用→办理被拒） |
| complete 用错人 | T0b 校验办理人必须是 assignee 或候选；换人先换委托令牌 sub |
| 起服务撞 8091 端口 | 本机常有常驻 flow-server；E2E 用 `FLOW_PORT=8099` 等旁路端口 |
| smoke 后库脏 | 冒烟实例留在库中便于查看；要干净加 `"cancel": true` |
