# 本体平台 × 主数据平台双向打通方案（事件驱动 webhook，演示级最小实现）

> 日期：2026-09-12 ｜ 前置：`20260912_cmx-ontology_演示数据主数据真源对齐方案.md`（八类漏斗已就绪）
> 原则：**零新组件、复用既有引擎、每个改动点 ≤40 行**；满足演示叙事，不做通用平台化。

## 一、目标

```
┌──────────┐  ①激活事件 webhook（MDM Outbox→订阅）   ┌──────────┐
│          │ ─────────────────────────────────────▶ │          │
│   MDM    │   POST /api/onto/v1/funnel/push        │  本体     │
│  cm_*表  │                                        │  oo_*表  │
│ (黄金记录)│ ◀───────────────────────────────────── │ (镜像/扩展)│
└──────────┘  ②动作 webhook → CR 创建+提交           └──────────┘
              （审批→激活→铸号→事件→①回流）
```

- **方向一（主数据 → 本体）**：MDM 激活器落库后的事件（`md_event_log` Outbox）经分发引擎 Webhook 通道推给本体新端点 `POST /funnel/push`，自动触发对应类型的漏斗 sync——主数据变更**秒级可见**，不再依赖手动 sync。
- **方向二（本体 → 主数据）**：本体动作新增 `webhook` 副作用打 MDM CR 创建+提交接口，走既有 `mdm_cr_approval` 审批 → 激活器铸号写 `cm_*` → 触发方向一自动回流本体。**动作发起的是治理申请，不直写黄金记录**（守住 MDM 激活器唯一写入口铁律）。

## 二、现状核实（已读代码确认，非假设）

| 机制 | 结论 |
|---|---|
| MDM 分发引擎 | `distribution/` 已有 Dispatcher 常驻循环 + WebhookChannel（`channels/webhook.rs`），channel_config 支持 **url + secret（sha256 签名，与 flow 同协议）+ headers** |
| MDM 订阅 | `POST /api/mdm/subscriptions`（save/test/set-active/batch），订阅含 eventTypes/keyPatterns 过滤；事件信封含 `event_type/dict_code/record_id/data` |
| 激活事件 | 激活器单事务写 `md_event_log`，`event_type = cr_type=="create" ? …`，`dict_code = target_dict`（=字典 dictCode，如 supplier/material） |
| MDM 鉴权 | `[auth].api_keys = cmx_sk_dev_…`（演示 key 已配，服务身份可调 CR 接口） |
| 本体出站 | `outbound.rs` 已有通用 `post_webhook`（白名单 SSRF 护栏），但**只带 X-Onto-Source 头**——需加可选 API-Key |
| 本体漏斗 | `run_full_sync` 幂等全量；`GET /funnel/mappings` 可枚举全部映射 |
| 铸号 | `MDM_WL`（MAT+日期+流水）规则已在 fico 库 `cmx_code_rule` |
| 已知坑 | 服务身份（API-Key）创建 CR 时 user_id='0' → apply 节点派幽灵用户、自动确认失效（彩排踩过） |

## 三、改造点清单（4 处代码 + 3 项配置 + 2 项演示数据）

### 代码（合计 ~70 行）

**C1 · 本体：`POST /api/onto/v1/funnel/push`**（`funnel_handlers.rs` + `lib.rs` 路由，~40 行）
- body 接收 MDM 事件信封（`{eventType, dictCode, recordId, data…}`，宽容反序列化）；
- 逻辑：枚举 `list_mappings()`，对 sourceQuery 包含 `cm_{dict_code}` 的映射逐个 `run_full_sync`（dict_code=supplier→命中 cm_supplier；material→cm_material——子串匹配对本场景无歧义，无命中则不动作）；返回 `{synced:[{objectType,read,written,quarantined}]}`；
- 鉴权：同既有端点 X-API-Key；`ONTO_OUTBOUND=off` 不影响本端点（它是接收方）；
- 同步执行（8 类各 <1s，单类命中只 1 次 sync），不做异步任务化（M2 范围）。

**C2 · 本体：`post_webhook` 支持可选出站 API-Key**（`outbound.rs`，~6 行）
- 新配置 `ONTO_WEBHOOK_API_KEY` / `onto.webhook_api_key`（模式同 `flow_api_key`）：有则投递时带 `X-API-Key` 头；`config_snapshot` 加 `webhookApiKeySet` 布尔（不含密钥本身）。

**C3 · MDM：CR 创建/提交支持服务身份指定发起人**（`handlers/cr.rs`，~15 行）
- 当请求为 API-Key 服务身份（user_id='0'）且 body 带 `createBy`（用户 id）时：校验 `cmx_user` 存在后以该用户身份创建/提交（否则维持现状 '0'）；
- 用户决策路径不受影响（门户页面走委托令牌，天然带身份）。

**C4 · MDM：无**（分发引擎/通道/订阅零改动，纯配置）。

### 配置（零代码）

**P1 · MDM 订阅 1 条**（`POST /api/mdm/subscriptions`）：
```json
{"name":"本体漏斗推送","channelType":"webhook","active":true,
 "channelConfig":{"url":"http://127.0.0.1:8097/api/onto/v1/funnel/push",
                  "headers":{"X-API-Key":"cmx_sk_dev_A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6"}},
 "rules":[{"eventTypes":["created","updated"],"keyPatterns":["*"]}]}
```
（eventTypes 取激活器实际写入值，执行时以 `activate.rs` L351 为准；先 `POST /mdm/subscriptions/test` 连通性验证。）

**P2 · 本体 toml**：`ONTO_WEBHOOK_ALLOW` 已默认含 127.0.0.1（MDM :8095 可达）；新增 `onto.webhook_api_key = cmx_sk_dev_…`。

**P3 · 幕⑥既有 supplier_review 事件订阅不动**（flow 链路与本方案并行不悖）。

### 演示数据

**D1 · material 激活映射 1 条**（`mdm_activation` 表，SQL 直插运行库）：`source_doc_type='wl'`（自由串）+ `cr_type='create'` + `target_dict='material'` + `header_mapping`（name→name、classId→class_id、baseUomId→base_uom_id、refPrice→ref_price、safetyStock→safety_stock）+ `subject_name_field=name` + `key_fields=[name]`。

**D2 · 本体新动作 `applyNewMaterial`（新增物料申请）**（scenario-spec actions 段）：
- params：`name / categoryId / uomId / refPrice`；
- logic：**空编辑集**（不在本体建对象——黄金记录要等审批）；
- side_effects：`[{kind:"webhook", url:"http://127.0.0.1:8095/api/mdm/change-requests", payload:{docType:"wl", crType:"create", createBy:"7503326638169403392", data:{name:"$name", classId:"$categoryId", baseUomId:"$uomId", refPrice:"$refPrice"}}}]`；
- 走既有 `POST /action-outbox/dispatch` 手动分发（与幕⑥同款节拍，演示点一致）。CR body 契约以 `cr.rs` 实际签名为准（执行时对齐）。

**D3 · walkthrough 增补幕⑦「双向打通」**：
1. workshop 动作中心 →「新增物料申请」→ 填名称/分类/单位 → 试算（编辑集为空，讲"本体不直写黄金记录"）→ 执行 → 台后 dispatch；
2. 待办中心 →「主数据审批」（物料 CR）→ 同意 → 激活器写 `cm_material` **铸号 MAT20260913xxxx**；
3. **不手动 sync**——2 秒内 MDM Outbox → webhook → 本体自动 sync Material → explorer/workshop 直接出现新物料（本方案的高光时刻）；
4. 台后证据：`md_event_log` 事件、分发投递 DONE、本体 sync 日志/`oe_action_log`。

## 四、与既有演示铁律的兼容性

| 铁律 | 影响 | 处置 |
|---|---|---|
| 漏斗 sync 覆盖 props，幕⑥回写必须在最后一场 sync 之后 | push 使"激活即 sync"——幕⑤ CR 激活触发 push（sync Supplier）发生在幕⑥回写**之前**，顺序天然满足 | 无需改 |
| 幕⑥之后不得再有 Supplier 激活 | 方向二演示只激活 material（push 只 sync 命中的 Material，不碰 Supplier） | 幕⑦排在幕⑥之后安全；**新增铁律：幕⑥后不得再审批任何供应商 CR** |
| 幕⑤手动 sync 展示 read/written/quarantined | 保留：幕②讲管道时可手动 re-sync；幕⑤ CR 激活后可"见证自动推送"替代手动 sync，或两者都做（幂等） | walkthrough 里二选一，推荐自动推送为主、手动 sync 作为降级兜底（订阅失效时） |

## 五、风险与边界

1. **重复推送**：分发引擎重试/多事件 → 多次 sync，幂等无害；多集群部署时各副本都会收到→ 各自幂等 sync，可接受（演示单机）。
2. **dict_code↔表名子串匹配**是演示级简化（material 会同时命中自身 query 里的 cm_material_class——仍只 sync Material，无歧义）；平台化应改为映射表，列入遗留。
3. **C3 服务身份指定发起人**是信任边界放宽（API-Key 持有者可冒任意用户建 CR）——内网演示可接受；平台化应改为动作 payload 携带签名委托断言，列入遗留。
4. **webhook 失败链路**：MDM 投递失败走指数退避/dead（分发引擎既有），兜底=手动 sync（既有能力），演示可讲"最终一致 + 手动闸门双保险"。

## 六、工作量与顺序

| 项 | 估时 |
|---|---|
| C1 funnel/push 端点 | 0.5h（含 cargo check + 冒烟） |
| C2 webhook API-Key | 0.25h |
| C3 CR createBy | 0.5h（cr.rs 两处 + 校验） |
| P1/P2 配置 + 订阅 test | 0.5h |
| D1 激活映射 + D2 动作 + spec 重灌 | 1h |
| 双向联调（CR 审批→自动回流全链）+ walkthrough 幕⑦ | 1h |
| **合计** | **约半天** |

改动涉及 cmx-ontology（C1/C2，main 分支）、cmx-mdm（C3）、根仓（spec/walkthrough）。执行前置：mdm/model/onto/flow 四服务在跑（均已确认）。


## 七、执行记录（2026-09-12 晚，全部完成并 E2E/UI 验证）

### 代码（3 处，均编译通过）
| # | 仓 | 内容 |
|---|---|---|
| C1 | cmx-ontology | `POST /api/onto/v1/funnel/push`（funnel_handlers.rs+lib.rs）：按事件 dictCode 词边界匹配 sourceQuery 中 `cm_{dict}` 的映射自动全量 sync；dictCode 缺省=全量 |
| C2 | cmx-ontology | `post_webhook` 支持 `ONTO_WEBHOOK_HEADERS`/`onto.webhook_headers`（JSON 串）统一注入出站请求头；`/action-outbox/config` 暴露 webhookHeadersSet |
| C3' | cmx-mdm | `POST /api/mdm/change-requests/webhook-create`（cr.rs+mdm_routes.rs）：服务身份直插 cv_mdm_apply（create_by=body.createBy，**修幽灵发起人坑**）+ 复用 mdm_cr_submit 起流程；doc_no 由 DB to_char(now())+pk 尾 4 位生成 |

### 执行中修复的问题
1. **list_mappings 存量 bug**（funnel_store.rs）：`ds.iter().next()` 只取第一行——八类映射只返回 Contract；改全量遍历。
2. **push 命中误判**：改词边界匹配（cm_supplier 不命中 cm_supplier_class 类）。
3. **webhook-create 三连修**：占位符错位（$2→复用 $1 计数错误）/PG 参数类型冲突（$1 同参 bigint+text）/create_by 列型 BIGINT。
4. **workshop UI 执行按钮失灵（存量 UI bug）**：cmx-floating-dialog 点击「执行」被外部关闭逻辑抢先（cancel 先于 button 派发 → 执行静默丢失）。修法：workshop.js 执行对话框「执行」改 body 内按钮 + keep:true 强制走 okdCustom 通路；另在 page-kit.js okdFloating 加旧版组件 buttons 未渲染的运行时兜底（探测 shadow 无 [data-dlg-btn-id] 则降级 okdCustom）。

### 配置与演示数据
- MDM 端点+订阅：`md_subscription` id=56119639306240（webhook → onto /funnel/push，headers 带 API-Key，secret=onto-demo-secret）；subscriptions/test 连通 ✓
- onto toml：`[onto] webhook_headers`（X-API-Key + db_id）
- spec 新动作 `applyNewSupplier`（空编辑集 + webhook 副作用打 webhook-create）；复用既有 gys 激活映射与 mdm_cr_approval 流程（D1 取消）

### E2E 全链实测（两轮）
动作 execute → outbox dispatch → webhook-create（CR 草稿+提交，initiator=admin）→ 待办「发起人确认」→ 页面 cr-form 保存并提交 → review 审批（javier 委托令牌）→ **activated 铸号**（SUP202609120002 苏州永磁 / SUP202609120003 昆山精密轴承）→ md_event_log → 分发 webhook → funnel/push → **本体自动 sync 出现新供应商（全程零手动 sync）**。首轮投递 404 由引擎重试自愈（幂等 delivered/200）。

### UI 测试（浏览器实测）
- workshop：动作中心 9 动作（含新增供应商申请）→ 参数面板 → 试算（编辑 0 条）→ **执行 committed·副作用 1**（修复后）✓
- 待办中心：UI 发起的 CR 出现「发起人确认」待办 → 办理打开 cr-form（webhook 传参完整）→ 保存并提交 ✓
- workshop/explorer：自动回流的新供应商实时可见；类型树 9 类型、360 视图 MDM 真源属性+四组关系块 ✓

### 演示日补充铁律
- 幕序：幕⑤ → 幕⑦（双向打通）→ 幕⑥；**幕⑥之后严禁再审批任何供应商 CR**（自动 push 会清 reviewStatus）
- 测试素材已消耗铸号段：SUP202609120002/003 为测试数据；演示日幕⑤ CR…033、幕⑦现场新建铸号顺延
