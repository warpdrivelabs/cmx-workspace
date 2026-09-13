# cmx-ontology 动作类型对标 Palantir 演进方案

> 日期：2026-09-12（v2.1，经两轮对抗性审查修订；v2.2 补 P2-0/P2-1 实施记录）　模块：cmx-ontology（后端 `backend/cmx-ontology/`，前端真源 `backend/cmx-container/assets/onto/`）
> 依据：Palantir 官方文档调研见 `documents/20260912_cmx-ontology_Palantir动作类型官方文档调研.md`（下称〔调研〕）
> 状态：P0/P1/P2-0/P2-1(workshop 部分) 已实施（2026-09-13）；P2 其余项（explorer 入口、revert、通知派生）待排期

**v2.2 实施补记（20260913，P2-0/P2-1）**：
- **作用对象物化列**：评审确认不加 tags 分类、对齐 Palantir（作用对象由参数类型声明，无独立语义）。为解决"参数埋在 JSONB 不好查"，新增保存期派生物化列 `om_action_type.target_object_types`（内核 `derive_target_object_types(parameters, logic)` 为唯一派生真源；`ALTER TABLE ADD COLUMN IF NOT EXISTS` + GIN 索引 `idx_om_action_type_targets`；boot `warm_store` 回填存量、快照恢复事务内回填、UPDATE 不动 updated_at）。清单接口换型 `ActionTypeMeta { apiName, displayName, status, parameters, targetObjectTypes }`。
- **check-permission 预检**：`POST /action-types/check-permission`（固定路径，动作列表入 body），口径与执行期 PEP 同源（静态解析编辑取作用域，失败回退参数声明派生）；函数动作残余风险不变（预检放行、执行 403 硬门兜底）。
- **workshop 动作中心分区**（用户批准的增量，替代原 P2-1 explorer 方案的首期形态）：按 `targetObjectTypes ∩ 当前类型` 分区——"适用于 X"置顶 + "全部动作"折叠；`deprecated` 不渲染；PEP 拒绝经预检不渲染（key 去重懒刷新）；`object/objectSet` 参数 `objectType===当前类型` 时**自动绑定选中对象**（只读回显 + 隐藏参数静默注入），替代手填/填 pk。
- explorer 对象浏览器动作入口（含行多选模型）**仍未实施**，维持原 P2-1 待排期项。
- 验证：内核新增派生单测（model 95 全绿）；新增 e2e `test/e2e/o4m6_manifest_targets.sh` 10/10（manifest 富化 / GIN 按类型查询 / check-permission 放行·拒绝·notFound / 执行期一致性），脚本末尾自清理 fixture。UI 侧因 dev server 故障未复验（workshop 分区为原生 JS 逻辑，待环境恢复后人工核验）。

**v2 修订摘要**（响应第一轮审查）：修正 revert 数据基础（before-image）、manifest 契约断言、function_backing 契约（降格为最小闭环 + 保留 validations）、新增接口路径违规、upsert 波及面、resolve_edits 签名、dry-run 兼容策略与 diff 取数来源、execute-batch 存储层改造点；重估工作量。

**v2.1 修订摘要**（响应第二轮审查）：修正 P0-4 组合矩阵自相矛盾（upsert 归一化四规则）、补 revert 对 create 覆盖写场景的 before 捕获（防数据销毁）、G4 接口规则显式归入不对齐名单、`edit_object_types` 补 UpsertObject（PEP 作用域下沉内核）、函数动作 object 型入参装载、executionLog 补 functionEvaluation/pepCheck 阶段、before-image 统一 schema、派生范围补 side_effects 引用、批量失败审计语义、explorer 多选模型边界、双主题验收、modify 丢更新既有债务记风险表。

---

## 一、现状盘点（cmx-ontology Action 今天的样子）

### 1.1 模型层（`crates/cmx-onto-model/src/def.rs` `ActionTypeDef`）

```rust
pub struct ActionTypeDef {
    pub api_name: String,
    pub display_name: String,
    pub description: String,
    pub parameters: Value,      // [{name, required, type: object|objectSet|string|long|double|boolean, objectType?}]
    pub logic: Value,           // [{op: createObject|modifyObject|deleteObject|addLink|removeLink, ...}]
    pub validations: Value,     // [{expression: FEEL, message}]
    pub side_effects: Value,    // [{kind, <targetKey>, ...}]
    pub function_backing: Option<String>,  // ⚠ 建模有、执行无
    pub status: TypeStatus,
}
```

### 1.2 执行链路（O4，`action.rs` 内核 + `action_handlers.rs` + `action_exec.rs`）

```
装载 ActionTypeDef
→ validate_params（必填参数结构化校验）
→ run_validations（FEEL 提交校验；ctx = 参数平铺 + params 别名；fail-closed）
→ resolve_edits（logic + $参数替换 → ObjectEdit 五类）
→ resolve_side_effects（SideEffect 列表；$内插）
→ 写侧 PEP（PolicyStore deny_actions，主体 deny → 403，fail-closed；作用域 = 编辑涉及的对象类型）
→ ActionExecutor.apply（一事务全成全败；审计 oe_action_log；副作用事务性 Outbox）
→ dispatcher 真投递（emitEvent/callFunction→进程内；webhook/startBusinessProcess/computeReport→跨服务 HTTP）
```

- `POST /action-types/{api_name}/execute` 与 `/dry-run`（既有接口；dry-run 只做标识预检 + 落审计，不触业务库、不入 Outbox）。
- API 齐全：action-types CRUD、action-logs、action-outbox（+dispatch/mark）、action-templates（内置模板）。

### 1.3 关键存储事实（v2 补记，后续设计的前提）

- `ObjectEdit::CreateObject` 本身是 **upsert 整行覆盖**（`action_exec.rs` `ON CONFLICT (pk) DO UPDATE` 覆盖 title+props，非 merge）——与"modify 合并 set"语义不同。
- `oe_action_log` **只存目标值（to）**，无 before-image；`edits_to_json` 中 `DeleteObject` 仅序列化 `op/objectType/pk`，**无属性快照**。
- `OntologyManifest.action_types` 是 `SimpleTypeMeta`（仅 apiName/displayName/updatedAt），**不含 parameters/status**。
- 函数运行时 `eval_function_any` 是**纯求值**（入参 JSON → 返回值），FEEL/Rhai 读不到本体对象状态。
- FEEL 求值器已支持链式成员访问（`objects.orderId.status` 可直接消费，无需改表达式引擎）。
- 前端动作 Inspector 在 designer.js 与 studio.js **各有一套实现**（改动需双份）；explorer.js 具备 `data-act` 事件委托与选中行机制，具备加动作入口的架构条件。

### 1.4 已经对齐 Palantir 的部分（不用动）

| Palantir 概念 | 我方现状 |
| --- | --- |
| Action Type 独立一等公民（MetaKind::ActionType、独立 CRUD、独立清单分区） | ✅ 已对齐 |
| Submission criteria 前置校验 + failure message | ✅ FEEL validations（fail-closed，全部失败项一次返回） |
| Side effects（通知/webhook/函数/事件） | ✅ 六种 kind + 事务性 Outbox + dispatcher（Outbox 模式比 Palantir 的顺序语义更严谨） |
| Action log 审计 | ✅ oe_action_log（含 dryRun 标记、失败原因） |
| Test run 不落库 | ✅ dry-run 预检不触业务库 |
| 写侧权限 | ✅ PEP deny_actions（fail-closed 硬门 403） |
| 原子事务 | ✅ 一事务全成全败（Palantir 同为 single transaction 语义） |
| Branching / 版本 | ◐ 全本体版本存档 + diff + restore 已有，动作级分支不做（见 §三 取舍） |

---

## 二、差距清单（对照〔调研〕逐项）

| # | 差距 | Palantir 行为 | 我方现状 | 严重度 |
| --- | --- | --- | --- | --- |
| G1 | **function_backing 死字段** | Run function 规则真正执行函数，函数输入自动成参数 | 字段建模/存储齐全，execute 链路**完全不消费**——用户配置了函数背书却毫无效果 | 🔴 高（语义欺骗） |
| G2 | **校验上下文读不到对象状态** | Parameter condition 可引用对象引用参数的属性（`ticket.status is Open`） | validation ctx 只有表单参数——"只允许对 Open 状态的单据提交"这类最常见校验**写不出来** | 🔴 高 |
| G3 | **值映射来源贫乏** | From parameter / Object parameter property / Static value / Current User / Current Time 五级 | logic 里只有 `$name` 整串替换；静态值、当前用户/时间、从对象参数取属性全部缺失 | 🔴 高 |
| G4 | **规则类型缺口** | 11+ 种规则 | 缺显式 upsert 语义（P0-5 解决）；接口多态规则（Interface rules）见下方"明确不对齐"名单（远期） | 🟡 中 |
| G5 | **无效组合不校验** | Invalid combinations 三条 + 编译排序语义 | resolve_edits 逐条解析，modify 后又 create 同一对象、同对象创建两次等非法组合照单全收 | 🟡 中 |
| G6 | **参数体系弱** | 约束（Multiple choice）、默认值、可见性覆写、规则自动派生参数 | 参数只有 name/required/type/objectType；约束、默认值、可见性、自动派生全无 | 🟡 中 |
| G7 | **试算体验浅** | Proposed changes（当前值 vs 建议值）+ Execution log 分解 + admin/end-user 错误分离 | dry-run 只回编辑 JSON 与计数 | 🟡 中 |
| G8 | **对象视图无动作按钮** | 三处自动聚合；当前对象经环境变量自动绑定；single/bulk 两类 | explorer 零集成；workshop 动作面板脱离对象上下文；无 bulk action | 🟡 中（使用面最大短板） |
| G9 | **无动作级撤销** | Undo or revert Actions（基于 action log 反演） | 有审计日志但无 revert 端点，且审计结构不支持反演 | 🟢 低（可后置） |
| G10 | **通知接收人不从对象派生** | 接收人可从对象参数属性派生 | notification 走 SSE 固定模板 | 🟢 低 |
| G11 | **无批量执行** | bulk action 与 batch API | execute 单次提交 | 🟢 低 |

**明确不对齐的（有意取舍）**：
- **writeback dataset / OSv1-v2**：我方直接写 per-type 对象表，无此概念。
- **Writeback Webhook（编辑前调外部系统且失败阻断）**：与"本体事务由本平台原子裁决"原则冲突，以"前置校验函数"（内部 FEEL/Rhai 函数调外部只读接口）替代，如未来有硬需求再议。
- **Interface rules（接口多态规则，5 种）**：需 interface reference parameter 体系 + per-type 表编译层配合多态写回，价值/成本比低，**远期条目**（平台 Interface 当前仅承载读侧多态契约）；写侧多态需求首版以"按具体对象类型分别建动作"过渡。
- **Apply scenario / Schedule rule / 动作级 branching**：分别依赖场景沙箱、数据集构建、分支评审能力，均不规划（schedule 的近似场景已由 `computeReport` 副作用覆盖）。

---

## 三、演进方案（三阶段）

### 总原则

1. **内核优先**：先补 `cmx-onto-model/src/action.rs` 纯逻辑内核（可单测、零 IO），再动 handler / 存储层 / 前端——与现有 O4 分层一致。内核保持零时钟、零 IO 依赖：对象状态、actor、now 均由 handler 装载后以参数传入。
2. **JSON 向后兼容**：logic / parameters 是自由 JSON，新增字段全部宽容读取，存量动作定义零迁移。
3. **fail-closed 沿袭**：校验语义保持"非真即败"；组合校验失败必须是**定义期/试算期报错**。
4. **新增接口一律 POST + 固定路径**（AGENTS §四.6）：资源标识/过滤/操作参数走 body/query，无可变路径段。
5. 每阶段独立可交付、可验收，前端随阶段同步。

---

### P0 语义补强（内核与执行链路，估 2–2.5 周）

#### P0-1 function_backing 最小闭环（G1，最高优先）

> 定位如实声明：我方函数运行时是纯求值（无本体读上下文），本项实现的是 **Palantir Run function rule 的最小闭环**（参数进 → 编辑 JSON 出），不承诺 Palantir"Ontology edit function 可读对象集"的完整能力——该能力的函数侧增强（函数求值注入对象装载上下文）列为后续独立演进，不在本方案内。

- **执行链路**（`execute_action` 内 function 分支，插在 validations 之后、PEP 之前）：
  1. `validate_params` → `run_validations`（**保留**，函数动作照样过提交校验——对齐 Palantir"submission criteria 与规则正交"）；
  2. 装载函数（`store().get_function`）→ 构造函数求值输入 `bound`：**`FunctionDef.inputs` 中 `type=="object"` / `type=="objectSet"` 的入参，经 P0-2 的 `load_param_objects` 装载为对象 JSON（集合）后**与标量参数合并（函数壳层契约即"对象型输入由调用方装载好注入"，直接传 pk 裸值会静默错乱）→ `eval_function_any` 求值；
  3. **返回值契约**：`{ "edits": [ObjectEdit JSON...], "sideEffects": [SideEffect JSON...] }`（两键均可省；顶层返回数组视为 edits 兼容写法）。新增内核纯函数 `parse_edits_json(&Value) -> Result<Vec<ObjectEdit>>`（ObjectEdit 目前无反序列化路径，需补）与 `parse_side_effects_json`；
  4. 函数返回的 edits **必须过 `validate_edit_sequence`**（P0-4）再进 PEP → apply；PEP 作用域照旧由 `edit_object_types` 从（函数产出的）编辑提取——**顺序固定为：validations → 函数求值 → 组合校验 → PEP**，函数求值发生在 PEP 之前（PEP 需要编辑才能定作用域），这意味着被 PEP 拒绝的函数动作白算一次求值，可接受（fail-closed 优先）。
  5. 函数返回的 sideEffects 与定义内 `side_effects` 的衔接：**定义内 sideEffects 必须为空**（保存期强制），运行时一律以函数返回为准，照常入 Outbox。
- **保存期校验**（`save_action_type` handler）：`function_backing` 非空 ⇒ `logic`、`side_effects` 必须为空（对齐"不能与其他规则组合"），`validations` 允许保留；校验函数存在，且从 `FunctionDef.inputs` **自动派生动作参数**（对齐 Palantir"函数输入自动成参数"：inputs 中每个入参在 `parameters` 缺失时自动补 `{name, required:与函数声明一致}`，只增不删）。
- 函数未定义 / 求值失败 / 返回 JSON 不合契约 → 动作失败（fail-closed），错误信息含函数 apiName 与阶段。
- 验收：配置 functionBacking 的动作 execute 真实按函数逻辑写回并过 PEP；functionBacking+logic 的定义保存被拒；函数动作的 validations 仍能拦截；函数入参自动出现在 parameters。

#### P0-2 提交校验上下文注入对象状态（G2）

- `execute_action` 在 `run_validations` 前，按**参数声明**收集待装载对象：`type=="object"` 的参数值（pk）；`type=="objectSet"` 的参数值（pk 列表，批量装载）→ 按 `objectType` 装载 props（存在才注入）。ctx 结构升级：

```json
{
  "orderId": "O-1",
  "params": { "orderId": "O-1" },
  "objects": { "orderId": { "pk": "O-1", "status": "open" },
               "orderSet": [ { "pk": "O-1", "status": "open" } ] }
}
```

- object 参数注入单对象（`objects.<param>.<property>` 链式访问，FEEL 引擎已支持）；objectSet 参数注入数组（表达式如 `count(objects.orderSet[status == 'open'])` 类聚合如 FEEL 不支持则首版仅支持逐元素谓词，**边界在方案内如实声明**：objectSet 校验首版限于 `count()` 与全称/存在判定，如引擎不支持则该场景降级为不支持并在文档标注）。
- 参数缺 `objectType` 或对象不存在 → 该参数不注入（引用即失败，fail-closed 不变）。
- **对象装载器做成独立函数** `load_param_objects(params, parameters) -> ObjectStateMap`，供 P0-2（校验上下文）、P0-3（值映射）、P1-1（diff）三处复用，避免三套装载逻辑。
- 验收：validations 能引用对象引用参数的当前属性并正确拦截；存量动作回归通过。

#### P0-3 值映射来源扩展（G3）

`logic` 各 op 的属性赋值/标识字段支持**五种**显式来源（统一顶层键 `"src"`，修正 v1 正文的 `_src` 笔误）：

```json
{ "op": "modifyObject", "objectType": "Order", "pk": "$orderId",
  "set": {
    "owner":    { "src": "param",         "name": "newOwner" },
    "memo":     { "src": "static",        "value": "系统年度结转" },
    "closedBy": { "src": "currentUser" },
    "closedAt": { "src": "currentTime" },
    "customer": { "src": "paramProperty", "param": "orderId", "property": "customerId" }
  } }
```

- **保留字约定**：属性值若为**含 `"src"` 键的对象字面量**即被解析为映射来源；确需写入形如 `{"src":...}` 的静态对象时必须显式 `{"src":"static","value":{...}}` 包裹。映射解析**递归**作用于 `set`/`properties` 内的嵌套对象与数组（struct 属性支持）。
- `paramProperty` 仅支持 `type=="object"` 的参数（objectSet 不支持，文档明示）；取值依赖被引用参数对象的 props，因此 **`resolve_edits` 签名升级为 `resolve_edits(action, params, objects, actor, now)`**（objects 来自 P0-2 的装载器，handler 传入；内核保持零 IO/零时钟）。取值失败（对象未装载/属性缺失）→ 解析报错，动作失败。
- 字符串裸写法（`"$name"`）继续支持为 `src: param` 的语法糖，存量定义不动。
- 验收：五种来源单测（含嵌套递归）；旧 JSON 全量回归；**静态对象含 `"src"` 键的保留字用例**；designer/studio 双 Inspector 的来源选择控件（P1 前可先用 JSON 编辑）。

#### P0-4 规则组合静态校验（G5）

- `resolve_edits` 末尾增加 `validate_edit_sequence(edits)` 纯函数。**矩阵归一化定则（v2.1 修正，消除 v2 的 modify→upsert 矛盾）**：upsert 在序列中**首个出现视为 create**，后续再次出现的 upsert 视为 modify（静态可判定，不依赖运行期对象存在性）。据此四条规则：
  1. 同一 (objectType, pk)：**delete 不得先于 create / modify / upsert**（upsert 归一为 create 后同样适用）；
  2. 同一 (objectType, pk)：**modify 不得先于 create / upsert**（modify → upsert **拒绝**）；
  3. 同一 (objectType, pk)：**create 不得出现两次**；**upsert 之后不得再 create**（upsert→create 拒绝；upsert→upsert 允许，归一为 modify；upsert→modify 允许）；
  4. 同一 (objectType, pk)：**upsert 之后不得 delete**（较归一化基线偏严的保守取舍：归一后 upsert=create，字面 create→delete 虽未被 Palantir 三条禁止，但 delete 的合法性依赖运行期对象是否真由本次 upsert 新建——静态不可判定，为安全统一拒绝）。
- 在**保存动作**时跑一遍（定义期拦截），dry-run 与 execute 再跑（防御直改库）。
- **PEP 作用域同步（v2.1 补，安全口径）**：`edit_object_types`（`action_handlers.rs`）只匹配 Create/Modify/Delete——新增 `UpsertObject` 后纯 upsert 动作的目标类型集合为空，类型级 deny 策略将失效。**将作用域提取逻辑下沉内核**（与 `validate_edit_sequence` 同层导出 `edit_object_types(edits)`，含 UpsertObject，一处维护），handler 改用内核版本；P2-1 check-permission 复用同源口径。
- 验收：四条规则的非法组合（含 upsert→create、modify→upsert、upsert→delete）保存与试算均被拒，错误信息指出第几条规则冲突；纯 upsert 动作被类型级 deny 策略正确拒绝。

#### P0-5 显式 upsert 规则 `createOrModifyObject`（G4 部分）

> 关键辨析：现有 `CreateObject` 是**整行覆盖式 upsert**，若 createOrModify 编译到它，对象已存在时会把未提交属性**整行抹掉**。故必须新增独立编辑变体，而非复用 CreateObject。

- 新增 `ObjectEdit::UpsertObject { object_type, pk, title, set }`：pk 存在 → 语义等同 ModifyObject（`set` 合并）；不存在 → 等同 CreateObject（`set` 全量落）。`apply_one` 增加 upsert 分支（事务内探存在性分流），**precheck、`edits_to_json`（审计序列化）、P0-4 矩阵、内核 `edit_object_types`（PEP 作用域）四处同步补齐**（v2.1 将最后一处显式化）。
- 保存期/dry-run 期跑 `validate_edit_sequence` 覆盖新变体。
- 验收：新 pk 建对象、旧 pk 合并改对象（**已存在的其他属性不被抹掉**——专设验收用例）；审计日志正确记录 upsert。

**P0 涉及文件**：`cmx-onto-model/src/action.rs`（内核主改：resolve_edits 签名、parse_edits_json、validate_edit_sequence、edit_object_types 下沉、五来源解析）、`cmx-onto-model/src/def.rs`（validate 补充）、`cmx-onto-app/src/action_handlers.rs`（function 分支、对象装载器）、`cmx-onto-store-pg/src/action_exec.rs`（UpsertObject 分支）、`handlers.rs`（保存期校验）、`openapi.rs`（契约同步）、designer.js + studio.js 双 Inspector 最小适配。
**P0 额外工作项（v2.1 补）**：action.rs 存量单测适配新签名（现有 8 个测试均为两参调用，编译必改）+ 新增 objects 注入 / 五来源 / 四规则矩阵 / upsert 用例——约半天，已含在 P0 估时内。

---

### P1 试算与参数体验（对齐 Test run / Parameters，估 1.5–2 周）

#### P1-1 dry-run / execute 响应升级（G7）

- 响应**新增**三段结构，旧字段（`edits`/`applied`/`logId`/`status`/`effects`）**保留共存一个版本周期**（前端三处消费方 workshop.js / studio.js / designer.js 按节奏切换，不构成破坏性变更）；execute 与 dry-run 共用同一构建函数，同步获得新字段。

```json
{
  "proposedChanges": [
    { "action": "modify", "objectType": "Order", "pk": "O-1", "title": "订单O-1",
      "diff": { "status": { "from": "open", "to": "closed" } } },
    { "action": "addLink", "link": "handledBy", "aPk": "O-1", "bPk": "U-9" }
  ],
  "executionLog": [
    { "stage": "loadDefinition", "ok": true },
    { "stage": "paramValidation", "ok": true },
    { "stage": "submissionCriteria", "ok": true, "evaluated": 2 },
    { "stage": "functionEvaluation", "ok": true },
    { "stage": "editResolution", "ok": true, "edits": 3 },
    { "stage": "editSequenceCheck", "ok": true },
    { "stage": "pepCheck", "ok": true }
  ],
  "sideEffectPreview": [ { "kind": "startBusinessProcess", "target": "approve_O-1" } ]
}
```

- **阶段清单与 P0-1 定序一致（v2.1 补）**：`functionEvaluation` 仅函数动作出现；`pepCheck` 恒出现（记录 PEP 结果）——execute 与 dry-run 共用构建函数，把实际走到的阶段如实记录（Palantir execution log 的对标意图即"逐步分解"）。

- **diff 取数来源（修正 v1）**：`resolve_edits` 之后按**编辑目标集合**（含 upsert/modify 的 pk、delete 的 pk；链接编辑无需 diff）装载当前对象 props，而非仅按参数装载——对象装载器复用 P0-2，扩一个 `load_edit_target_objects(edits)`。create 无 from；delete 条目含被删对象的完整 props 快照（为 P2-2 before-image 打底）。
- **before-image 统一 schema（v2.1 补，回应双取数点）**：dry-run 侧（handler 事务外预读）与 P2-2 审计侧（`apply_one` 事务内捕获）服务不同路径、均需保留，但**快照条目 JSON schema 在内核统一定义一处**（含 `objectType/pk/title/props/overwritten/preExisted` 字段，preExisted 供 revert 区分"新建"与"覆盖既有对象"），两侧共用，杜绝结构错位；execute 响应中的 from 值在文档/API 注释标注"预读快照，非事务提交快照"（TOCTOU 窗口如实声明）。
- proposedChanges 含**对象条目与链接条目**两类（对齐 Palantir proposed changes 覆盖对象与链接）。
- **错误双通道**：业务错误拆 `userMessage`（validations 的 message、缺参提示）与 `adminDetail`（内部表达式、存储错误栈），HTTP 层统一出口；execute 同步生效。
- 涉及文件：`action_handlers.rs`、`action_exec.rs`（delete 快照）、前端三处消费方渐进适配、`openapi.rs`。
- 验收：dry-run 改状态动作可见 from→to；链接编辑出现在 proposedChanges；校验失败时 userMessage 为配置提示而 adminDetail 含表达式。

#### P1-2 参数体系增强（G6）

`parameters` 条目扩展（全部宽容读取，向后兼容）：

```json
{ "name": "priority", "type": "string", "required": true,
  "objectType": "Order",
  "constraints": { "kind": "multipleChoice", "options": ["P0","P1","P2"] },
  "defaultValue": "P2",
  "hidden": false }
```

- 内核 `validate_params` 升级：multipleChoice 取值必须在 options 内；defaultValue 在 execute 缺参时自动补齐（补齐后再跑必填校验）。
- 保存期校验：defaultValue 必须满足 constraints。
- **自动派生参数范围**：① logic 中 `$name` 引用；② `src: param`/`paramProperty` 显式引用；③ functionBacking 时从 `FunctionDef.inputs` 派生（P0-1 已覆盖）；④ **side_effects 中 `$name` 内插引用（v2.1 补）**——target 与 payload 里的 `$name` 同样依赖参数存在，缺参时现仅静默保留字面量。四者并集，保存时补 `{name, required:false}`（响应提示补全数量），只增不删。
- 前端双 Inspector：参数行增加可选值/默认值/隐藏输入；执行弹窗 multipleChoice 渲染下拉、defaultValue 预填、hidden 参数不显示。

#### P1-3 批量执行（G11）

- **新接口**：`POST /action-types/execute-batch`（固定路径，apiName 与 items 入 body，符合 AGENTS §四.6）：

```json
{ "apiName": "closeOrder", "items": [ { "params": { "orderId": "O-1" } }, { "params": { "orderId": "O-2" } } ], "dryRun": false }
```

- 语义：每 item 独立走完整校验链（validations/组合校验/PEP）；**同事务逐项提交，任一失败全回滚**。取舍理由如实陈述：这是**产品语义取舍**（审计粒度与前端结果呈现简单、与现有"一事务全成全败"模型一致），并非无状态约束的必然要求；"部分成功"模式列为后续可选演进。
- **存储层改造点（v1 遗漏，补记）**：`ActionExecutor::apply` 每次调用自开事务；批量须抽出 `apply_edits_in_txn(txn_id, edits, ...)` 内部路径，外层 `execute_batch` 统一开一个事务逐 item 校验+落编辑，任一 abort 全回滚。
- 单批上限为 toml 配置项 **`[action] batch_max_items`（默认 100）**，经 config-sync 技能同步模板与手册；文档提示大事务锁持有时间随批量线性增长，超限建议分批。
- **失败审计语义（v2.1 补）**：任一 item 失败全回滚后，**整批落一条 `status=failed` 的批审计**（edits 中标注失败 item 序号与原因），成功项不逐条落审计（已回滚，无业务痕迹可落）；成功批次按现有单动作粒度落一条批审计。
- 验收：第 N 项失败全回滚（库内无残留、无 Outbox 残留）；上限生效；dryRun 批量预演正确。

---

### P2 使用面与治理（对齐 Use actions，估 3 周）

#### P2-0 manifest 动作清单富化（v2 新增，P2-1 的前置依赖）

- **问题**：`OntologyManifest.action_types` 为 `SimpleTypeMeta`，不含 parameters/status——explorer 无法按 objectType 匹配动作，也无法过滤 Deprecated。
- **方案**：新增 `ActionTypeMeta { api_name, display_name, status, parameters }`，`list_action_types` 查询补列，`OntologyManifest.action_types` 换型。**这是清单契约变更**：designer / studio / workshop / explorer 四个消费方逐一回归（现只读 apiName/displayName 的代码不受影响，serde 宽容读取保证）。
- 备选（按需逐个拉定义）因 N+1 被否决；workshop 现有的逐动作拉定义逻辑可顺势改读 manifest。
- 涉及文件：`def.rs`、`store.rs`（list 查询）、`handlers.rs`、`openapi.rs`。

#### P2-1 对象浏览器动作入口 + 当前对象自动绑定（G8，使用面核心）

- **交互形态（定夺）**：explorer.js 列表态顶栏新增"动作"下拉——
  - **single action**（parameters 含 `type=="object"` 且 `objectType==当前对象类型`）：需**恰好选中一行**（取选中行 pk 为当前对象），无选中/多选时置灰；
  - **bulk action**（含 `type=="objectSet"` 同类型参数）：**首版**选中单行时以该对象构成单元素集合应用；**行多选模型（checkbox 列 + 选中态渲染）作为显式子任务**——现 explorer.js 为单选模型（`state.sel` 单值），多选属新增机制，估时约 0.5 周，若 P2 超限则后置为独立迭代；
  - 下拉数据源 = 富化后的 manifest 过滤，**Deprecated 状态动作不渲染**。
- **当前对象自动绑定**（对齐 Palantir Environment variable → Current object）：弹表单时匹配的 object/objectSet 参数自动填当前选中 pk（集合）且按 `hidden` 配置隐藏；其余参数渲染输入控件（multipleChoice 下拉、defaultValue 预填）；表单校验失败就地标红。
- 表单渲染抽公共函数进 page-kit.js，workshop.js 动作面板复用（消除双份实现）。
- **权限前置查询（新端点）**：`POST /action-types/check-permission`（固定路径；body：`{ actions: [apiName...], subjects: [...] }`，返回各动作放行/拒绝）。服务端用与执行期**同源口径**计算目标类型——即服务端自行做定义扫描/`resolve_edits`（函数动作按函数返回无法预知，**如实降级**：函数动作预检按定义层 PEP 策略 + 执行期仍硬门，文档标注残余风险"函数动态目标类型可能预检放行但执行 403"）。被拒动作按钮不渲染（而非点击报 403）。
- 涉及文件：explorer.js、page-kit.js、workshop.js、`action_handlers.rs`（check-permission）、`policy_store.rs` 复用、`openapi.rs`。

#### P2-2 动作级撤销 revert（G9，v2 重做数据基础）

- **前置：before-image 落审计**（v1 完全遗漏，本项补上；**create 分支为 v2.1 补齐的关键半边**）：
  - `oe_action_log` 增加 `before_edits` 列（JSONB，走 sql-guide 迁移文件）；
  - `apply_one` 在**写前**捕获旧状态，各分支处理：
    - **modify**：复用事务内 `read_props_in_txn` 记录被改属性的 from 值；
    - **delete**：补读完整 props + title 再删，快照入 before_edits；
    - **create（含覆盖写）**：INSERT 前事务内探存在性（复用 `read_props_in_txn`）——**存在则捕获旧行完整快照并标记 `overwritten=true`**（现有 CreateObject 是整行覆盖 upsert，若不捕获，revert 按"create→delete"会把动作前已存在的旧数据直接 DELETE，造成不可恢复的数据销毁）；不存在则标记 `preExisted=false`；
    - **upsert**：存在 → 同 modify；不存在 → 记 `preExisted=false`（避免 revert 误删）；
    - **link**：边本身自反，无需快照。
  - `before_edits` 与编辑一一对应，条目 schema 用 P1-1 定义的统一 before-image schema。
  - **存量日志不含 before_edits，不可 revert**——revert 端点对旧日志返回明确错误提示，不静默。
- **revert 端点**：`POST /action-logs/revert`（固定路径，logId 入 body，符合 AGENTS §四.6）：
  - 读 `before_edits` → 构造逆编辑（create 且 `preExisted=false` → delete；**create 且覆盖了旧行（`overwritten=true`）→ 按快照重建原对象**；modify → 恢复 from 值；delete → 按快照重建；addLink→removeLink、removeLink→addLink）；
  - **并发安全（v1 遗漏）**：modify 逆操作用条件 UPDATE（`WHERE props->>'x' = 原动作后值`）或事务内 `SELECT ... FOR UPDATE` 复核——覆盖冲突（对象已被后续编辑改动）默认拒绝并提示，不做三层合并；
  - **revert 执行路径定夺**：直连 `ActionExecutor`（不走 validations——原动作已过校验），**但必须过 PEP**（对逆编辑目标类型执行同源检查），审计落 `kind="revert"` 并关联原 log_id；
  - **副作用不回滚**（已起的流程、已发的通知不撤销）——API 响应与前端提示明示此边界；
  - revert 动作本身入审计后，同样可被再 revert（有限次，链上靠 log 关联防环）。
- 前端：designer 增加审计 tab（消费现有 `GET /action-logs`），每行"撤销"按钮 + 二次确认 + 覆盖冲突提示。
- 涉及文件：`ddl.rs` + sql-guide 迁移、`action_exec.rs`（before 捕获）、`action_handlers.rs`（revert 端点）、designer.js、`openapi.rs`。

#### P2-3 通知接收人派生（G10）

- notification 副作用增加 `recipientsFrom: { param: "orderId", property: "ownerId" }`（对象参数属性派生接收人），与现有固定 `template` 模式并存。**解析时机定夺（v2.1，对齐 Palantir"内容基于编辑前状态"语义 + Outbox 事务性）**：在 execute 事务内解析 recipients 并随 payload 快照入 Outbox，dispatcher 投递时只透传不再读库（避免异步投递时读到动作写回后的新状态 / 多节点读到别节点已提交值）。`param` 引用的对象 props 从 P0-2 装载器获取。
- 邮件渠道不规划（平台无邮件网关，SSE 覆盖站内触达）。

---

## 四、实施顺序与依赖

```
P0-2 校验上下文（装载器）─→ P0-1 functionBacked（object 型函数入参依赖装载器，装载器先行）
P0-2 校验上下文 ─────┬─→ P1-1 dry-run 升级（依赖 P0-2 装载器，扩编辑目标装载）
P0-3 值映射 ─────────┤
P0-4 组合校验 ───────┼─→ P1-2 参数体系（依赖 P0-4 保存期校验框架 + P0-1 inputs 派生）
P0-5 upsert ─────────┘
P1 全部 ──→ P2-0 manifest 富化（清单契约变更，宜与 P1 前端切换同窗口）
         ──→ P2-1 对象视图按钮（强依赖 P2-0；表单渲染依赖 P1-2 参数契约）
         ──→ P2-2 revert（依赖 before-image 捕获，捕获代码与 P0 写路径同期实现、
                     列上线即可开启捕获，端点与 UI 可后置）
         ──→ P2-3 通知派生（独立）
```

- P0 五项可并行开工、合并验收；P2-2 的 before-image 捕获逻辑建议随 P0 合入（避免上线空窗期日志不可 revert）。
- cmx-ontology 为独立仓、无下游 path 引用（已核实），仓内 `cargo check`/`clippy` 即可，不触发跨仓验证。
- 前端改动全在真源 `backend/cmx-container/assets/onto/`；改完按需 `./scripts/publish-assets.sh onto`（打包归档用）。
- 新增 toml 配置（`[action] batch_max_items`）走 config-sync 技能；新增表列走 sql-guide 迁移文件。

## 五、验收清单（合并视图）

- [ ] function_backing 动作真实执行函数并过 validations/组合校验/PEP；object 型函数入参正确装载；非法组合保存被拒；函数入参自动派生为参数
- [ ] 校验表达式引用 `objects.<param>.<property>`（object）与 `objects.<param>`（objectSet 数组）正确拦截；存量动作回归全绿
- [ ] 五种值映射来源单测（含嵌套递归、保留字用例）；旧 JSON 回归全绿
- [ ] 四条 invalid combination 规则（含 upsert 归一矩阵：upsert→create、modify→upsert、upsert→delete）定义期/试算期均拦截；纯 upsert 动作被类型级 deny 策略正确拒绝
- [ ] createOrModifyObject：新 pk 建、旧 pk 合并不抹属性；审计正确
- [ ] dry-run/execute 返回 proposedChanges（含链接条目、from→to diff）+ executionLog（含 functionEvaluation/pepCheck 阶段）+ sideEffectPreview + userMessage/adminDetail 双通道；旧字段共存
- [ ] 参数 multipleChoice/defaultValue/hidden 全链生效；四类自动派生补全（logic/src/函数 inputs/side_effects 引用）
- [ ] execute-batch：固定路径 POST、同事务全回滚、`batch_max_items` 上限生效、失败批次单条 failed 批审计
- [ ] manifest 含 ActionTypeMeta（parameters/status），四端回归无破坏
- [ ] explorer 顶栏动作下拉：single/bulk 按选中形态启用、当前对象自动绑定、Deprecated 不渲染、PEP 拒绝不渲染；**新 UI 双主题合规（UI5 `var(--sap*)` 变量 + Neo skin/tone 切换，零硬编码色值）**
- [ ] revert：新日志可反演（含 create 覆盖写场景恢复原对象）、覆盖冲突拒绝、过 PEP、落 revert 审计、存量日志明确报错、副作用不回滚有提示
- [ ] notification recipientsFrom 在 execute 事务内解析并随 payload 快照入 Outbox，投递透传不读库
- [ ] `cargo check` + `clippy` 零新增告警；action.rs 内核单测全绿（存量迁移 + 新用例）；openapi 同步；sql-guide 迁移合规

## 六、风险与开放问题

1. **保留字 `"src"`**：属性值含 `"src"` 键的对象字面量被解析为映射来源；静态对象须显式包裹。已在 P0-3 写明约定与验收用例（待评审确认）。
2. **函数动作的 PEP 预检残余风险**：函数返回的编辑目标类型运行期才可知，check-permission 预检对函数动作只能按定义层策略，存在"预检放行、执行 403"的窗口（执行期硬门兜底，fail-closed 不破）。
3. **objectSet 校验能力边界**：首版 FEEL 对 objectSet 数组的聚合表达（count/全称/存在）若引擎不支持则降级声明，已在 P0-2 写明。
4. **execute-batch 全回滚**：产品语义取舍（非架构必然），若业务要求部分成功，后续以 per-item 事务模式演进（P1-3 已留口）。
5. **大事务锁持有**：execute-batch 批量与 revert 重建对象均为长事务场景，上限配置 + 文档提示分批；delete→rebuild 依赖快照完整性，before_edits 校验失败即拒。
6. **工作量**：P0 含存储层改动 + 双份 Inspector 适配 + 存量单测迁移，估 2–2.5 周；P1 1.5–2 周；P2（含 manifest 契约变更与四端回归 + before-image 全链 + 行多选模型子任务）估 3–3.5 周（多选若后置则 3 周内）。均为单人串行估算，多人并行可压缩。
7. **既有债务记一笔（不在本方案范围）**：`read_props_in_txn` 为普通 SELECT（无 `FOR UPDATE`），并发动作对同一对象 modify 存在丢更新——Palantir "冲突解决策略"在我方无对应物。revert 已采用条件 UPDATE / FOR UPDATE 先例，modify/upsert 读改写可低成本跟进（条件 UPDATE 版 CAS），列为后续独立小改进；本方案范围内 modify 语义保持现状。

## 七、遗留分歧点（需评审拍板）

以下为 v1 审查提出的分歧点，方案已给出倾向性决策，请确认或改判：

| # | 分歧点 | 方案倾向 | 备选 |
| --- | --- | --- | --- |
| 1 | 值映射键名与保留字 | 顶层 `"src"` + 显式包裹约定 | `_` 前缀键（更防御但 JSON 冗长） |
| 2 | function_backing 是否保留 validations | 保留（正交治理） | 全跳过（纯函数语义） |
| 3 | execute-batch 失败语义 | 全回滚 | 部分成功（per-item 事务） |
| 4 | explorer 交互形态 | 顶栏下拉 + 选中行启用 | 每行内嵌按钮（列表拥挤） |
| 5 | manifest 富化 vs 按需拉定义 | 富化（四端一次回归） | explorer 按需拉（N+1） |
| 6 | dry-run 响应兼容 | 新旧字段共存一个版本周期 | 整体替换 |
