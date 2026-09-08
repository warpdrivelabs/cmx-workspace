# BPMN 定义语法与部署契约（重参考）

> 模式A（定义创建）的完整语法契约。真源：`backend/cmx-flowengine/docs/usage/{02,03,04,05,06}-*.md`；
> 本文件是"写 spec + 部署 + 冒烟"所需的全部速查，不必回读全部文档。

## 1. spec JSON 结构（create_flow_def.py 输入）

```jsonc
{
  "key": "expense_v2",                       // 必填，= process id = 定义 key
  "name": "报销审批v2",                       // 展示名
  "start": {"id": "s", "name": "发起"},       // 可省：自动补 s → 唯一入度0节点
  "nodes": [ /* 见下表 */ ],
  "flows": [
    {"from": "gw", "to": "dir", "condition": "${amount > 20000}", "name": "大额"},
    {"from": "s", "to": "mgr"}                // 无 condition = 无条件边
  ],
  "deploy": {"server": "http://127.0.0.1:8091", "apiKey": "...",
             "note": "上线 v1", "publishedBy": "agent",
             "name": "…", "domain": "fi", "application": "…", "module": "…"},
  "smoke":  {"orgId": "zongbu", "businessKey": "SMOKE-1",
             "variables": {"amount": 50000, "initiator": "u_emp"},
             "expectActive": ["mgr"], "cancel": false}
}
```

endEvent 可省：出度 0 的节点自动连到唯一终点；终点多个时必须显式连边。

## 2. 节点类型 × spec 属性

| type | spec 属性 | 生成的 BPMN |
|---|---|---|
| `userTask` | `assignee`（静态 id 或 `${var}`）、`candidates`、`candidateUsers`、`candidateGroups`、`cc`、`formKey`/`formMode`/`formFields`、`mi`、`timers` | `flowable:assignee` / `cmx:candidates` / `cmx:cc` … |
| `mi` 子对象 | `collection`（数组变量名）、`elementVar`、`sequential`（true=或签）、`completion`（完成条件） | `<multiInstanceLoopCharacteristics>` |
| `timers` 数组 | `{duration:"PT30S", to:"目标节点", cancelActivity:false?}`（宿主必须 userTask；时长 ISO 8601 `P[nD]T[nH][nM][nS]`，不支持周/月/绝对时刻） | 挂宿主的 `<boundaryEvent>`（缺省中断型）+ 定时器出边 |
| `exclusiveGateway` / `inclusiveGateway` | `defaultTo`（缺省边的**目标节点 id**，脚本解析成网关 `default` 属性） | `default="<flowId>"` |
| `parallelGateway` | —（>1 出边=fork，>1 入边=join） | — |
| `callActivity` | `calledKey`（逻辑名，按组织路由）或 `calledElement`（直调 key）、`inVars`/`outVars`（`src:dst` 逗号串）或结构化 `in`/`out` 数组（**两者不可同给**；"空 in 列表=全量透传"本 spec 无法表达，需手写 BPMN） | `cmx:calledKey` / `<flowable:in>` `<flowable:out>` |
| `serviceTask` | `delegate` | `flowable:delegateExpression="${delegate}"` |
| `businessRuleTask` | `decisionRef` | `flowable:decisionRef`；**流程部署前须先 `POST /decisions` 注册决策表**（usage/05 §5.6.3），否则宽容跳过、网关恒走 default |
| `messageCatch` | `message`、`correlationVar` | `<intermediateCatchEvent>` + messageEventDefinition |
| `endEvent` | `terminate: true` → 一票否决终点 | `<terminateEventDefinition/>` |

**引擎黑名单**（spec 直接拒绝）：`task`/`scriptTask`/`sendTask`/`receiveTask`/`manualTask`/`eventBasedGateway`/`complexGateway`/`intermediateThrowEvent`。
**引擎支持但本脚本不生成**：`subProcess`（嵌入子流程，usage/03 §3.4）——需分组语义时用 callActivity 替代或手写 BPMN 后走 REST 部署。process 级 `startFormKey` spec 亦未暴露，需要时手加到 process 标签。

## 3. 候选人七类（candidates / cc 值语法，逗号分隔）

| 写法 | 解析 |
|---|---|
| `user(u1)` / 裸 `u1` | 具体用户（不查库） |
| `role(finance)`；`candidateGroups="finance"` 同义 | 角色全部用户 |
| `position(cfo)` | 岗位全部用户 |
| `org(fin_bj)` | 组织**及子树**全部用户 |
| `orgLeader` / `orgLeader(d_fin)` | 组织领导（省参=实例组织） |
| `initiator` | 发起人（实例变量 `initiator`，**不查库**） |
| `initiatorLeader` | 发起人所属组织的领导 |

解析：0 人→回退静态 assignee；1 人→直派；≥2 人→候选池待 `claim`。

## 4. 条件表达式速记（网关/边 condition）

- 运算符：`&& || ! == != < <= > >= + - * /`（`and`/`or`/`not` 同义；单个 `&`/`|`/`=` 报错）。
- 变量路径支持点号嵌套与数组下标：`${order.customer.level == 'VIP'}`、`${items.0.qty > 10}`。
- MI 完成条件内置计数：`nrOfInstances` / `nrOfCompletedInstances` / `nrOfActiveInstances`。
- 无时间函数（NOW 等刻意排除）。真值：null/false/0/""/[]/{} 为假。
- **null 安全**：比较任一侧为 null → false → 走网关 default（写条件必知）。内置函数 18 个（LEN/CONTAINS/IN/COALESCE/IF…见 usage/05 §5.3 或 `GET /conditions/functions`）。
- **spec 里写原文**（`${amount > 20000}`），脚本负责 XML 转义（`>`→`&gt;`）。

## 5. 部署 REST 契约（POST，信封 `{code,msg,data}`，业务失败也是 HTTP 200）

| 步 | 端点 | body | 通过标准 |
|---|---|---|---|
| 校验 | `/api/flow/v1/definitions/validate` | `{bpmnXml}` | `code==0 && data.valid==true`（valid=false 是软失败！） |
| 草稿 | `/definitions/draft` | `{name, bpmnXml, updatedBy, domain?…}` | `code==0` |
| 发布 | `/definitions/{key}/publish` | `{note, publishedBy}` | `code==0 && hotLoaded==true`（发布即热装载无需重启） |
| 决策注册 | `/decisions` | 决策表定义（usage/05 §5.6.3） | businessRuleTask 流程**部署前必做**（未注册=宽容跳过恒走 default） |
| 冒烟起 | `/instances` | `{definitionKey, orgId?, businessKey?, variables}` | `code==0`，断言 `activeNodes`/`openTasks` |

**大小写陷阱**：complete/reject/urge 等 body 是 camelCase（`instanceId`）；`claim/transfer/delegate/addsign` 是 snake_case（`instance_id`）。

## 6. 鉴权与"办理需身份"（T0b 授权）

- 服务调用：`X-API-Key: <key>`（命中即服务身份）。
- **complete/reject/withdraw 等办理动作必须有用户身份**（且须是该任务 assignee 或候选）：加
  `X-Delegated-User-Token: Bearer <JWT>`（HS256，`sub`=用户 id、`tenant`=租户、**必须带 `exp`**）。
  dev 密钥见 `flow-server.toml [auth] jwt_secret`。python 铸 token：hmac-sha256 签 `{"sub":"u_mgr","tenant":"default","exp":<now+3600>}`。
- `FLOW_AUTH_MODE=off` 时**委托令牌验不了**（不初始化 JWT 密钥），但 off 模式可直接 `X-User: <uid>` 头建立用户身份（免铸 JWT，仅限本机开发）；jwt 模式办理用委托令牌。

## 7. 冒烟后推进验证（可选加深）

```bash
# 起实例断言首节点后：取 openTasks[0].id → complete（带委托令牌）→ 断言 activeNodes 走向预期分支；
# callActivity 场景：GET /instances/{iid}/children 断言子流程 key（组织路由结果）与父 waitingSubflow=true。
```

## 8. 与模式B（数据复原）的联动

- callActivity 的 `calledKey` 组织路由依赖 `cmx_flow_subflow_binding`（身份库）——目标库没有绑定时：
  先用模式B 的复原 SQL 灌入（examples/manifest-20260816.json 里有 fin_review/dept_review 两套矩阵），
  或直接给 callActivity 用 `calledElement` 直调。
- 语义 BPMN 无 DI：设计工作台打开自动 BFS 布局，不必生成图形坐标。
- 生成物落盘建议：`backend/cmx-flowengine/docs/<测试集>/defs/<key>.bpmn`（与既有 defs 目录同级惯例），
  spec 文件与 BPMN 同目录留存，便于模式B 下一轮把该定义纳入复原范围。

## 9. 常见坑（模式A）

| 坑 | 正解 |
|---|---|
| 条件里裸写 `>` / `<` / `&&` | spec 写原文，脚本转义；手改 BPMN 时必须 `&gt;` `&lt;` `&amp;&amp;` |
| 在**边上**写 `default="true"` | 引擎规定 default 是**网关属性**指向边 id；spec 用节点 `defaultTo` |
| validate 返回 HTTP 200 就当成功 | 软失败：必须看 `data.valid` |
| 委托令牌缺 `exp` | jsonwebtoken 默认校验 exp，缺了直接验签失败（退化服务调用→办理被拒） |
| complete 用错人 | T0b 校验办理人必须是 assignee 或候选；换人先换委托令牌 sub |
| 起服务撞 8091 端口 | 本机常有常驻 flow-server；E2E 用 `FLOW_PORT=8099` 等旁路端口 |
| smoke 后库脏 | 冒烟实例留在库中便于查看；要干净加 `"cancel": true` |
