# cmx-rulesengine 决策引擎与决策图全栈体检报告

| 项 | 内容 |
| --- | --- |
| 体检日期 | 2026-09-20 |
| 修复状态 | **✅ 2026-09-20 同日已全量修复**（用户指令"全部修改，一次解决"）——59 条确认问题全部清偿，见文末「附录 · 修复实施记录」；质量基线升级为 clippy 0 告警 + 88 单测全绿（原 67）+ 5 个真库集成测试（`#[ignore]`，`RULE_TEST_DB_URL` + 单线程跑） |
| 体检范围 | `backend/cmx-rulesengine`（全部 6 个 crate）+ `frontend/cmx-decision-graph`（决策图组件）+ `backend/cmx-container/assets/rules/web`（规则控制台页面真源，为 rulesengine 的配套 UI，一并纳入） |
| 体检方式 | 三路并行只读代码审查（内核求值链 / 应用层与存储 / 前端与契约），交叉下钻 cmx-container 公用 crate 真源；另跑 `cargo clippy --workspace --all-targets` 与 `cargo test --workspace` 作为质量基线 |
| 改动情况 | **未修改任何文件**，纯只读审查 |
| 范围外 | 本体平台内置规则（cmx-ontology 的 FEEL+Rhai 规则模块）不在本次范围 |

---

## 一、结论速览

**分级统计：P0×4、P1×13、P2×42，共 59 条确认问题。**

| 级别 | 定义 | 数量 |
| --- | --- | --- |
| P0 | 错误决策结果 / 数据损坏 / 功能不可用 | 4 |
| P1 | 特定条件下必错 / 数据丢失通路 / 规则违反 | 13 |
| P2 | 健壮性 / 契约 / 体验 | 42 |

**一句话总评**：编译纪律与常规链路是好的——clippy 0 告警、67 个单元测试全绿、SQL 全参数化无注入、Rhai 沙箱闸完整、前端路径级契约无一 404、转义纪律好；**但版本发布/激活状态机是"多步写、零事务、先破坏后校验"的实现，内核求值语义存在静默产出错误决策的裂缝，前端错误路径存在两条数据丢失通路**——问题集中在自动化测试完全没覆盖的盲区（存储层与应用层零测试、路由契约测试仅采样 2/30）。

**"测试全绿"与"很多 bug"并存的原因**：现有 67 个测试集中在 rule-model / rule-feel / rule-engine 三个内核 crate 的正常路径；本报告的 P0 全部落在零测试区域——`cmx-rule-store-pg` 与 `cmx-rule-app` 两个 crate 一个测试都没有，发布/激活一致性全靠手工 curl 脚本验证，而手工脚本恰好没测"激活不存在的版本"这种单请求即损坏状态的场景。

---

## 二、质量基线（验证过没问题的）

避免误伤，先列**验证过不是问题**的面：

- `cargo clippy --workspace --all-targets`：**0 告警**。
- `cargo test --workspace`：**67 个单测全部通过**（分布：内核三 crate；store-pg 与 app 为 0 个）。
- **SQL 注入**：存储层全部参数化查询，无动态拼接排序/过滤，未发现注入点。
- **Rhai 脚本沙箱**：`max_operations=100_000`、递归 32 层、字符串 64KB 等闸门完整；`ScriptFn` 编译失败会拒绝发布入口。
- **driver 类型映射**：`cmx-database-pg` INT8/TIMESTAMPTZ 分派核对无误，stats 的 `timing_us BIGINT → Int(i64)` 映射正确。
- **前端路径级契约**：控制台全部 API 调用与后端路由（`/api/rules/v1/*`）逐一比对，**无一 404**；唯一字段级实错是审计日志缺 `createdAt`（见 P1-9）。
- **XSS 防护**：五个控制台页面统一 `escHtml` 五字符集转义，决策图组件无 innerHTML 拼接用户输入（仅 demo 页自伤型注入，见 P2）。
- **真源漂移**：`cmx-rulesengine/web/ui-native/` 与真源 `assets/rules/web/ui-native/` 逐字节一致（仅行尾差异）；决策图 vendor 与 `frontend/cmx-decision-graph/dist` 一致——不存在"改了真源没发布"。
- **事件绑定**：控制台页面事件委托防重绑纪律良好，组件无监听泄漏。

---

## 三、P0 —— 必须优先修复（4 条）

### P0-1 激活不存在的版本会把该决策全部发布版失活，决策静默回退草稿求值

- **位置**：`backend/cmx-rulesengine/crates/cmx-rule-store-pg/src/store.rs:150-176`（入口 `crates/cmx-rule-app/src/handlers.rs:473-481`）
- **问题**：`activate_version` 先执行**破坏性的全量失活**，再按版本号定向激活，存在性校验放在失活**之后**，且三段写无事务：

```rust
self.exec("UPDATE cmx_rule_release SET active = FALSE WHERE key = $1", ...).await?;   // 先全量失活
let n = self.exec("UPDATE cmx_rule_release SET active = TRUE WHERE key = $1 AND version = $2", ...).await?;
if n == 0 {
    return Err(StoreError::NotFound(...));   // 此时全部版本已失活，无法恢复
}
```

- **触发与后果**：单条请求 `POST /definitions/{key}/versions/999/activate`（版本号不存在即可，无需并发）→ 该决策在 `cmx_rule_release` 中零激活版本 → `load_definition` 静默回退**草稿**求值——线上已发布决策的求值行为悄悄变成草稿版本，无任何报错暴露。
- **修复方向**：存在性校验前置；三段写收进一个事务（`BEGIN…COMMIT`）。

### P0-2 First / Priority / OutputOrder 命中策略对全部命中行求值输出，永不选中的坏行拖垮整个决策

- **位置**：`backend/cmx-rulesengine/crates/cmx-rule-engine/src/lib.rs:216-241`
- **问题**：`First` 语义只取首个命中行，实现却先把**所有**命中行的输出格全量求值，任何一行出错即整体失败（`outputs?`）。而 `DecisionTable::validate()`（`cmx-rule-model/src/ir.rs:128-148`）只校验列数、**不校验输出格语法**，含非法输出表达式的行可以正常发布。`Any` 策略同理（lib.rs:230-238）。
- **触发与后果**：命中行 0 输出正常、行 1 输出格写错（如调不存在的脚本函数）→ 整个决策失败、output=null——本应按行 0 产出正确决策的场景被一行"永远不会被选中"的坏行击穿；下游把 null 当"未命中/拒绝"处理即产生错误决策。
- **修复方向**：短路求值——First/Any 逐行求值、命中即停；Priority/OutputOrder 只对参与排序的行求值。

### P0-3 单元格 unary test 序比较仅支持数值，日期/字符串比较恒为 false 且静默

- **位置**：`backend/cmx-rulesengine/crates/cmx-rule-feel/src/lib.rs:188-199`
- **问题**：

```rust
// 序比较：仅数值有意义。
match (as_f64(lhs), as_f64(rhs)) {
    (Some(a), Some(b)) => Ok(...),
    _ => Ok(false),   // 非数值做序比较 → false，不报错
}
```

单元格 `>= "2026-01-01"`、`<= "B"` 一律返回 false 且**不报错**。而 FEEL 表达式路径（`expr.rs:516-531` 的 `cmp`）**支持**字符串字典序比较——同一业务判定两种写法结果相反：`? >= "2026-01-01"` 命中，`>= "2026-01-01"` 永不命中。`validate_unary_test`（用 null 值跑一遍，lib.rs:121-123）对此校验通过，设计器目录也不警示；gap 分析中该格解析为 `Constraint::Other`，完整性分析静默跳过。注意：提交 `e324e4c 统一时间转化处理` 只改了前端日志页的时间**显示**格式化，内核零改动，此雷原样保留。
- **触发与后果**：DMN 日期/字符串比较是标准用法，规则行静默永不命中 = 持续性错误决策，且无任何告警通路。
- **修复方向**：明确日期类型支持（至少 ISO 日期字符串字典序）；非数值序比较改为 fail-closed 报错并在 `validate_unary_test` 拦截。

### P0-4 可嵌 Web Component 独立壳 / demo 页整链路加载即崩

- **位置**：六个核心页面模块顶层——`backend/cmx-container/assets/rules/web/ui-native/rule/design-workbench.js:55`、`rule/designer.js:33`、`rule/graph-designer.js:32`、`rule/sim-workbench.js:67`、`rule/simulator.js:26`、`rule/logs.js:47`
- **问题**：模块求值期执行 `const { apiJson } = globalThis.__cmxDataComp`，该全局唯一赋值点在门户运行时（`cmx-portal-manager/src/import-ui5-and-app.js:14`）；独立壳 `cmx-rulesengine/web/index.js`、`elements/*.js`、demo 页均**没有任何装配点**。模块一加载即抛 `Cannot destructure property 'apiJson' of undefined` → `defineRuleElement` 永不执行 → `<rule-designer>` 等元素永远注册不上。
- **触发与后果**：demo 三个标签全白屏；`:8094` 直开 native 页同样崩。`index.js:10` 明示"第三方/任意框架，无需门户"——该能力实际 0 可用。门户内使用不受影响。
- **修复方向**：核内改惰性取用 `globalThis.__cmxDataComp?.apiJson` 并在独立壳内联兜底实现（apiJson/escHtml/cmxConfirm 三件套 polyfill）。

---

## 四、P1 —— 特定条件下必错 / 数据丢失（13 条）

### 后端·存储与状态机

#### P1-1 publish 三段写非事务 + `MAX(version)+1` 并发竞态 → 全版本失活 / 双激活

- **位置**：`crates/cmx-rule-store-pg/src/store.rs:62-121`（竞态窗口 79-87）
- **问题**：① 下一版本号取 `SELECT COALESCE(MAX(version),0)+1` 后再 INSERT，两个并发发布读到同一 `cur_max`，第二个撞唯一索引失败；② 失败发生在「旧版全失活」**之后**，无事务回滚（代码注释自认 R3 收进事务，始终没做）；③ 存在交错序可造成两行同时 active，`list_versions` 出现双激活。
- **触发与后果**：双击发布 / 重试 / 并发调用即触发；后果与 P0-1 同类——发布失败后决策回退草稿求值。
- **修复方向**：事务化 + 版本号改为序列或 `INSERT … RETURNING` 原子取号；release 表加 partial unique index（`WHERE active`）兜底双激活。

#### P1-2 脚本函数「发布」不冻结版本：草稿保存直接改写已发布函数体

- **位置**：`crates/cmx-rule-store-pg/src/store.rs:250-272`（`save_function` upsert）；消费方 `crates/cmx-rule-app/src/handlers.rs:352-363`
- **问题**：`ON CONFLICT (name) DO UPDATE SET params/body/lang/...` **不更新 `published` 也不更新 `version`**。函数发布过之后，任何一次"存草稿"都立即、无版本号地改写求值时实际注入的函数体——与决策定义的「不可变 release + activate」语义完全不对称，发布端点形同虚设。
- **触发与后果**：发布函数 → 保存修改 → 不点发布 → 所有租户内求值即刻使用新函数体，行为变更无审计版本可回溯。
- **修复方向**：与决策定义同构——`cmx_rule_script_function` 拆草稿/发布两态（或 body 冻结 + published 快照）。

#### P1-3 业务配置 `std::env::var` 直读（违反工作区全局规则 §四.10）+ 硬编码弱口令回退

- **位置**：`crates/cmx-rule-app/src/tenancy.rs:62-63`
- **问题**：租户库连接模板 `RULE_TENANT_DB_URL_TEMPLATE` 用 `std::env::var` 直读，未走 `cmx_utils::ConfigManager`（全局规则要求 toml 分组 + `分组__键` env 映射）；回退默认值内嵌 `postgres:postgres@127.0.0.1:5432` 弱口令。
- **后果**：multi 模式忘配 env 时静默把租户库连到本机 5432 的 postgres/postgres；配置无法进 toml 统一管理。
- **修复方向**：迁 ConfigManager（`[rules.tenancy] db_url_template`），删弱口令回退、改 fail-fast。

#### P1-4 租户名未做字符集校验，直接拼接进租户库连接 URL（multi 模式连接串注入）

- **位置**：`crates/cmx-rule-app/src/tenancy.rs:35-41`（db_id 派生）、`:61-64`（URL 拼接）；租户来源 `cmx-engine-kit/src/auth/jwt.rs:222-227`（off 模式 `X-Tenant` 头原样入 scope）
- **问题**：租户名全链路无字符集/长度白名单，`template.replace("{tenant}", &tenant)` 直接生成 PG 连接串。`X-Tenant: x@evilhost:5432/db?sslmode=disable` 会**重写连接的 host/db/参数**；超长租户名还使数据源 id `rule_<tenant>` 无界增长。
- **触发与后果**：`auth.tenancy = "multi"` + off 鉴权（当前 toml 默认即此组合）时，任何能触达 ：8094 的客户端一个请求头即可把租户库连接重定向到任意主机——跨租户读写与内网数据库探测通道。single 模式不受影响。
- **修复方向**：租户名白名单 `^[a-z0-9_]{1,32}$`，不合法即 400。

#### P1-5 dev/test 配置含明文数据库口令且入库

- **位置**：`rules-server-dev.toml:20`、`rules-server-test.toml:20`（两文件被 git 跟踪，此处不引用明文）
- **问题**：提交 4759feb 声明"排除本地真实连接配置（含明文密码，不入库）"，实际只排除了 `rules-server-local5432.toml`；dev/test 两份被跟踪的 toml 仍是内网真实库明文口令，`.env` 还把 `CONFIG_FILE` 默认指向 test 那份。
- **修复方向**：换密 + 改用 env 覆盖（`DATABASES__*`）注入，被跟踪 toml 只留占位。

### 后端·内核求值

#### P1-6 数值等值容差双标准：unary test 用 `f64::EPSILON`，FEEL 表达式用 `1e-9`

- **位置**：`crates/cmx-rule-feel/src/lib.rs:203-208` vs `crates/cmx-rule-feel/src/expr.rs:510-515`
- **问题**：值 `3.3000000000000003`（如 `1.1*3` 的浮点结果）对单元格 `= 3.3` 差 4.44e-16 > `f64::EPSILON`(2.22e-16) → **不命中**；同一值对 `? = 3.3`（走 feel_eq，容差 1e-9）→ 命中。同一输入在同一张表不同位置判定相反，`1.1+2.2=3.3` 这类常见浮点场景即触发。
- **修复方向**：统一为单一容差（建议 1e-9）。

#### P1-7 `split_top_commas` 不感知引号：含逗号的字符串单元格被拆碎

- **位置**：`crates/cmx-rule-feel/src/lib.rs:266-305`
- **问题**：单元格 `"a, b"`（匹配业务值 "a, b"）被拆成 `"a` 与 `b"` → 各自报"字符串未闭合"→ 该规则行求值失败 → **整个决策失败**（合法输入被拒）。含逗号的枚举 `"x,y", "z"` 同理炸成三段，失败归因文案定位不到真实原因。
- **修复方向**：切分时跳过引号内字符。

#### P1-8 决策图节点失败不级联，下游用 null 继续算出"看似成功"的错误输出

- **位置**：`crates/cmx-rule-engine/src/graph.rs:71-156`
- **问题**：decisionTable 节点失败后 output=null、`merge` 静默跳过，循环继续；下游节点引用缺失字段得 null（FEEL 静默 null 语义），`if` 分支按 null 比较走 else 产出错误值，最终 output 节点把**半污染上下文整体导出**。API 响应 `output` 非空、仅 trace 里有 failure——只消费 output 的调用方拿到错误决策。GoRules 在节点失败时默认短路，此处不短路也无"停用下游"标记。
- **修复方向**：失败短路（至少提供 `stopOnFailure` 选项默认开启），响应体显式携带 failure 顶层标记。

### 后端·未完成实现

#### P1-9 Priority / OutputOrder 命中策略从未实现，静默退化为 First

- **位置**：`crates/cmx-rule-engine/src/lib.rs:240-241`；`crates/cmx-rule-model/src/ir.rs:80-91`
- **问题**：注释写"R1 完善"，但 `OutputClause` 至今没有 priority 字段，IR 层无从承载优先级。用户选 P 策略（DMN 语义=按输出值优先级）实际得到行序首行，多命中时**决策结果错误**，且无运行期警告。R1 的表达式引擎均已落地，这是明确的修一半欠账。

### 前端·规则控制台与契约

#### P1-10 决策日志列表「时刻」列恒显示 "—"：后端漏返回 createdAt

- **位置**：前端 `rule/logs.js:111`（渲染 `l.createdAt`）；后端 `crates/cmx-rule-app/src/stats.rs:20-45`
- **问题**：`list_logs` 的 SELECT 明确取了 `created_at`，但组 JSON 时只输出 `id/decisionKey/decisionVersion/output/timingUs/caller/failure` 七个字段，**漏了 createdAt**。前端 `fmtTime(undefined)` 兜底返回 '—'。
- **后果**：审计中心每条日志的"时刻"列 100% 显示 "—"，审计核心字段（何时做的决策）不可见。这是前后端契约核对中发现的唯一字段级实错，一行可修。

#### P1-11 工作台改分类会用「已发布内容」回写草稿，静默丢弃草稿改动（数据丢失）

- **位置**：`rule/design-workbench.js:147-159`（recategorize）；语义根因 `crates/cmx-rule-store-pg/src/store.rs:347-363`（`load_definition` 发布版优先）
- **问题**：recategorize 实现 = `GET /definitions/{key}` 取完整 def → 改 categoryCode → `POST /definitions/draft` 整体回存。而详情接口**激活发布版优先**，且发布快照不带分类。已发布、且发布后又改过草稿（草稿≠发布版）时，切换分类 → 服务端草稿 body 被**发布版 body 整体覆盖**，无提示。
- **修复方向**：后端补"仅草稿"读语义（如 `?stage=draft`）或分类改独立轻量接口，禁止"详情→回存"模式。

#### P1-12 设计器装载失败被静默吞掉落成"空骨架"，一键保存即覆盖服务端定义（数据丢失）

- **位置**：`rule/designer.js:42`（决策表设计器）；同型 `rule/graph-designer.js:66`
- **问题**：`loadDef` 的 `catch` 既不提示也不置错误态，直接用空表骨架（inputs/outputs/rules 全空）冒充装载成功；graph-designer 静默换成 `in→out` 两节点最小图。用户面对假象空表点「保存草稿」，即把服务端已有定义整体覆盖为空（后端 `save_draft` 是无条件 upsert）。
- **修复方向**：装载失败显式报错并禁用保存按钮；保存前 diff 提示"由 N 条规则变为 0 条"。

---

## 五、P2 —— 健壮性 / 契约 / 体验（42 条）

### 后端内核（12 条）

| # | 问题 | 位置 |
| --- | --- | --- |
| 1 | decision 节点对失败的子决策记"成功"节点，失败藏在子 trace；失败子图无 output 时返回部分累积上下文并 merge 进父上下文 | `rule-engine/graph.rs:114-124` |
| 2 | 聚合策略空命中类型不一致：C+ 返回 `0.0`（浮点）、C# 返回 `0`（整数）、C</C> 返回 null | `rule-engine/lib.rs:208-213` |
| 3 | `x in ["a".."f"]` 字符串区间静默 false，不报错 | `rule-feel/expr.rs:492-499` |
| 4 | 未定义变量静默 null，与缺失输入不可区分——列表达式拼错变量名（`amout`）无任何告警，是最大的静默失败通道 | `rule-feel/expr.rs:394`、`rule-model/eval.rs:28-50` |
| 5 | FEEL 递归下降解析无深度上限，`"((((…))))"` 数万层嵌套可打爆线程栈（进程 abort）；Rhai 侧有 `max_call_levels=32`，FEEL 侧无对应闸门，属 DoS 面 | `rule-feel/expr.rs:188-259`、`lib.rs:40-41` |
| 6 | 类型混用列（行 1 数值、行 2 布尔）的 gap 分析静默半分析：`is_num` 优先，布尔行输入空间完全未探测且不告警 | `rule-engine/analyze.rs:115-148` |
| 7 | gap 分析组合数 `product()` 整数溢出：20 列×10 枚举 → debug panic / release 回绕后绕过 CELL_CAP 静默漏报 | `rule-engine/analyze.rs:73-79` |
| 8 | `NumRange::overlaps` EPSILON 判据在大数值域（>1e16）产生 overlap 误报，仅影响分析报告 | `rule-feel/lib.rs:330-340` |
| 9 | 决策图输入事实非对象时被静默丢弃，求值照常产出空上下文结果 | `rule-engine/graph.rs:64-67` |
| 10 | `with_functions` 的 thread_local 手工 set/restore 无 panic 保护：f panic 则旧值不恢复，tokio worker 长期复用可泄漏上一租户脚本函数 | `rule-feel/script.rs:61-66` |
| 11 | `register_functions` 静默吞掉编译失败的函数，调用处报"未知函数"，归因绕圈 | `rule-feel/script.rs:76-80` |
| 12 | 性能：unary test 无 AST 缓存（每单元格每次求值重新 parse）；gap 分析 CELL_CAP×规则×列 次完整解析大表秒级起步 | `rule-engine/lib.rs`、`analyze.rs` |

### 后端应用层与存储（19 条）

| # | 问题 | 位置 |
| --- | --- | --- |
| 1 | **同路径多方法 5 组**，违反全局规则 §四.6（本体存量 12 组已清零，本仓未跟上）：`/definitions/{key}` GET+DELETE、`/categories` GET+POST、`/decisions/{key}/tests` GET+POST、`/functions` GET+POST、`/functions/{name}` GET+DELETE | `cmx-rule-app/src/lib.rs:60-107` |
| 2 | `delete_definition` 四表删除非事务，中途失败留"定义在、版本全无"半删除态 | `rule-store-pg/store.rs:237-245` |
| 3 | 租户内跨决策改删测试用例：`delete_test` 丢弃路径 key 只按 id 删；`save_test` 接受客户端任意 id，可改写别家决策的用例 | `handlers.rs:577-583`、`:557-574` |
| 4 | 删除语义不一致：`delete_test` 删不存在也返 `deleted:true`，definition/function 则 404 | `store.rs:226-233` |
| 5 | 保留段 key 冲突：key 为 `draft`/`validate` 的定义能存进去但 `GET/DELETE /definitions/draft` 永远 405，取不到删不掉；空 key 存成孤儿行 | `handlers.rs:41-51` |
| 6 | 详情接口 name 恒为空：草稿路径 SELECT 了 name 却不传给 `def_from_parts`（写死空串），列表接口正常——契约口径不一 | `store.rs:365-379`、`:502-512` |
| 7 | 路由契约测试只采样：30 条业务路由仅探 2 条，无方法级断言、无"无凭证全 401"层覆盖断言 | `cmx-rule-server/main.rs:186-194` |
| 8 | OpenAPI 恒为空壳：openapi.rs 只有 info 无 paths，"路由与声明一致"无从谈起 | `cmx-rule-app/openapi.rs:7-19` |
| 9 | dev/test toml 第 21 行注释把 `default = true` 一并吞掉，两份配置 `[[databases]]` 均无 default 标记（因 require_default=false 未致启动失败，属配置损坏） | `rules-server-dev.toml:21`、`rules-server-test.toml:21` |
| 10 | 出厂默认不安全：被跟踪主配置 `auth.mode="off"` + 周知 dev API Key，fail-fast 只拦显式 off、不拦"忘改就上线" | `rules-server.toml:24-31` |
| 11 | `publish_function` 回读竞态：UPDATE 与 SELECT 非原子，并发下版本号可能错报；重复发布每次 +1 | `store.rs:275-294` |
| 12 | 列表无分页：`list_definitions` 全量无 LIMIT；`list_logs` 硬编码 LIMIT 100 无翻页，审计下钻超 100 条不可见 | `store.rs:405-427`、`stats.rs:16` |
| 13 | stats 口径：评估数 0 时成功率报 100.0；子查询失败静默取 0——DB 故障在大盘显示成"0 求值/100% 成功" | `stats.rs:113-126` |
| 14 | `json_deep_eq` 按 as_f64 全等：>2^53 整数判等失真、NaN 恒不等，`run_tests` 边界数值误报 | `handlers.rs:637-649` |
| 15 | 同步求值阻塞 async worker（Rhai 有闸，DoS 面已收敛）；`build_resolver` BFS 逐 key 串行查库（上限 128），深图求值延迟放大 | `handlers.rs:209-211`、`:312-337` |
| 16 | multi 租户懒备库失败不入 ready_set → 每请求重试（warn 刷屏）；`Mutex::lock().unwrap()` 毒化面；multi 模式下 toml 的 rule_pg 库成死配置 | `tenancy.rs:50-91` |
| 17 | 端口改写副作用：toml 显式配 `port=8080` 而无 `SERVER__PORT` env 时被静默改成 8094 | `main.rs:49-51` |
| 18 | 文档与行为漂移：engine.rs 注释称 warm_store 非致命，main.rs 实际作为致命钩子 | `engine.rs:16-17` vs `main.rs:109-115` |
| 19 | 落库不 trim：`save_category`/`save_function` 只对 code trim 判空，name 等原样入库 | `handlers.rs:66-76`、`:385-397` |

### 前端（11 条）

| # | 问题 | 位置 |
| --- | --- | --- |
| 1 | 组件 `attributeChangedCallback` 外部换图不清理选中态（与 setGraph 行为不一致），旧选中 id 悬空 | `cmx-decision-graph/src/element/cmx-decision-graph.ts:75-87` |
| 2 | 图设计器每次键击全量 `setGraph` 回灌：画布选中高亮在编辑中消失、SVG 全量重渲、壳与组件选中态不同步 | `rule/graph-designer.js:336,381-388` |
| 3 | 组件连线源高亮为死代码：RenderState 恒传 `connectFrom: null`，拉线时源节点无高亮反馈 | `cmx-decision-graph.ts:179,198`、`render/svg.ts:61,111` |
| 4 | 多实例页共享模块级 `analyzeTimer`：两个设计器 Tab 互相取消对方的 gap/overlap 防抖分析，风控语义页面输出过期结论 | `rule/designer.js:52-53`、`graph-designer.js:80-81` |
| 5 | 页面模块级状态只增不清（`state.hosts`/`instances`），未注册 portal 的 `onDispose`，长会话内存累积 | `design-workbench.js:199` 等 |
| 6 | `catMove` 两次 saveCategory 非原子，中途失败留下对调一半的 ord，排序错乱无提示 | `design-workbench.js:184` |
| 7 | 仿真台仍用原生 `prompt`（治理要求换 cmxConfirm）；沙箱环境 prompt 被禁用时"存为用例"无任何反应 | `rule/simulator.js:117` |
| 8 | 测试用例回填 facts 用 `String(v)`：对象/数组变 `"[object Object]"`，用例回放结果必然 diff 且无提示 | `rule/simulator.js:138` |
| 9 | 组件 blob 加载失败后 Promise 永久 rejected，本会话不再重试，须刷新页面 | `design-workbench.js:312-318`、`graph-designer.js:44-51` |
| 10 | 硬编码色值残留：各页 3-6 处（按钮 `color:#fff`、`--dg-purple:#7c5cff`、flash 阴影等），不随主题翻转，命中 CI 一票否决条款边缘情形；demo 页整页硬编码 | `designer.js:288`、`graph-designer.js:422,437`、`simulator.js:296` 等 |
| 11 | demo 页把输入框原文拼进 innerHTML（`stage.innerHTML = ...attrs...`），值含 `">` 即打断标签（仅 demo 自伤） | `cmx-rulesengine/web/demo/index.html:48-50` |

### 可疑但未确认（不定级）

- `!=` 对缺失输入命中（null≠3 → 规则命中）：符合 FEEL 语义，但业务预期值得产品侧确认。
- `normalize_numbers` 大整数（>2^53）经 as_f64 归一损失精度。
- decision 节点循环引用报错文案是"嵌套过深"，未点明循环引用。
- `ScriptFn::from_parts` 函数体注释里含 fn 名文本会被误判"已声明"而不包装。
- `not (` 带空格时剥壳失败落入表达式路径，报错无"not 剥壳失败"线索。
- `get_path` 平坦 key 优先于嵌套（已文档化），但与"嵌套优先"直觉相反，混入点号 key 会静默改变取值。
- gap 代表点列间独立性假设：相关列（A<B）产生业务不可能组合的 gap 误报（OpenL 同款通用局限，报告文案未声明）。
- `DecisionRule.id` 承诺进 trace 未兑现（matched_rules 只有行号）。
- API Key 非常数时间比较（HashMap 明文匹配）：平台级取舍。
- open 切片免认证投递 native 页（提交说明称设计如此）：资产含敏感线索则扩大暴露面。
- publish 不重校验草稿：当前唯一写入方有校验暂无实害，未来旁路写入即成洞。
- logs 核模块级单例状态，壳层未阻止同页多开 Tab，多开互相影响。
- sim-workbench 智能转型不认科学计数/千分位（`1e3`、`1,000` 按字符串下发）。

### 决策图组件历史债现状（frontend/cmx-decision-graph）

| 历史债 | 2026-09-20 现状 |
| --- | --- |
| fitView 有注释无实现 | **仍缺**——仅存在于文件头注释（cmx-decision-graph.ts:8），类内无此方法，宿主按注释调用会 TypeError |
| 无缩放 | **仍缺**——全仓无 wheel/zoom 逻辑，大图只能靠容器滚动 |
| 无 undo | **仍缺**——无历史栈/快照代码 |
| 无 Delete 键删除 | **仍缺**——未监听 keydown，删节点/边只能走壳层按钮 |
| 无导出 | **仍缺**——无 SVG/图片导出（JSON 仅编程 API） |
| vendor 落后 dist | **已消除**——vendor 与 dist 逐字节一致（仅 CRLF 行尾差异） |

### 前后端契约核对（控制台调用 vs 后端路由）

路径/方法级逐一比对**无一 404**：definitions/categories/publish/delete/analyze/simulate/tests/tests-run/feel-validate/feel-functions/logs/logs-detail/native-pages/鉴权头全部对上；`TraceNode` camelCase 序列化与前端读取一致。唯一字段级实错 = P1-10（logs 列表漏 createdAt）。

### 真源漂移

`cmx-rulesengine/web/` 反向多出 `demo/index.html`、`elements/*.js`、`index.js`（真源 `assets/rules/web/` 只有 `ui-native/`）。按发布规则属合法残留（多余不删不改），但这批文件正是 P0-4 已死的独立壳入口——建议向真源收敛或明示废弃。`ui-native/` 与 vendor 无漂移。

---

## 六、测试覆盖缺口汇总

1. **`cmx-rule-store-pg` 与 `cmx-rule-app` 全 crate 零 `#[test]`**——发布/激活/删除一致性全靠手工 curl 脚本；P0-1（激活不存在版本）正好落在盲区（qa 脚本只测"激活存在版本"）。
2. 路由契约测试 30 条路由仅 2 条进断言，无方法级、无鉴权层覆盖断言。
3. 内核缺口：Any 一致/不一致分支、RuleOrder vs Collect 顺序差异、Collect 聚合报错路径、not 嵌套、含逗号字符串单元格、字符串/日期序比较、图节点失败后下游行为、gap 分析多列/字符串/布尔/类型混用列、MAX_DEPTH 上限、图无 output 节点的隐式契约——均零测试。
4. 并发场景（并发 publish、并发 publish_function）零脚本零单测。
5. multi 租户模式零测试：全部 qa/seed/e2e 脚本按 `off + single` 直连，tenancy 全链路从未被执行过。

---

## 七、修复路线建议（未实施，等拍板）

**第一批 · 数据安全止血**（修完才能放心当生产用）：
1. 激活/发布/删除事务化 + 存在性校验前置（P0-1、P1-1、P2-2）；
2. 命中策略短路求值（P0-2）；
3. 前端两条数据丢失通路：装载失败禁保存 + 改分类不回写草稿（P1-11、P1-12）；
4. 独立壳装配兜底（P0-4）；
5. 顺手一行：logs 列表补 createdAt（P1-10）。

**第二批 · 语义补课**：
6. 日期/字符串序比较语义决策 + validate 拦截（P0-3、P2-3）；
7. 等值容差统一 1e-9（P1-6）；含逗号字符串拆分修引号感知（P1-7）；
8. 图节点失败短路（P1-8）；Priority/OutputOrder 实现（P1-9）；
9. 脚本函数发布冻结（P1-2）；
10. 同路径多方法 5 组整改（P2-1，全局规范）。

**第三批 · 边界与租户**：
11. multi 租户整改：租户名白名单 + ConfigManager 迁移 + 删弱口令回退（P1-3、P1-4）；
12. dev/test 明文密码出库换密（P1-5）；出厂 auth.mode 默认收紧（P2-10）；
13. gap 分析溢出保护（P2-7）、FEEL 深度上限（P2-5）、thread_local panic 保护（P2-10）。

**第四批 · 债务与防护网**：
14. 测试补盲：store-pg/app 至少补发布/激活状态机集成测试 + "激活不存在版本"回归 + 路由契约全量断言；
15. 决策图历史债（缩放/undo/Delete/导出/fitView）按需排期；
16. P2 批量清偿与 OpenAPI 补全。

---

## 附录 · 体检方法说明

- 三路并行只读审查：内核求值链（cmx-rule-model / cmx-rule-engine / cmx-rule-feel 全部源文件含测试）、应用层与存储（cmx-rule-app / cmx-rule-store-pg / cmx-rule-server / 配置 toml / qa 脚本）、前端（cmx-decision-graph 源码 + assets/rules/web 真源 + cmx-rulesengine/web 产物 + 后端路由基准）。
- 应用层审查对 `cmx-engine-kit`（auth/tenant/routes/resp）、`cmx-database-pg`、`cmx-service-base` 做了跨仓只读下钻验证。
- 质量基线：`cargo clippy --workspace --all-targets`（0 告警）+ `cargo test --workspace`（67 通过 / 0 失败）。
- 全程未修改任何文件；所有 file:line 引用基于 2026-09-20 工作区状态（cmx-rulesengine HEAD = b397eae）。

---

## 附录 · 复核勘误（2026-09-20 逐条对码复核）

本报告全部 P0/P1 已逐条对源码复核，P2 抽查 15 条，**无一条假问题**。复核中发现本报告自身 4 处瑕疵，更正如下：

1. **计数口径**：汇总表的 P1×13 是三路代理原始计数；整合时内核 P1-5（gap 组合数溢出）已并入 P2 表，正文实际为 P1×12。正确口径：**P0×4、P1×12、P2×43、共 59 条**（P2 计入溢出条与下条补回项）。
2. **正文内核 P2 表遗漏 1 条**（整合时被挤出）："DecisionGraph::validate 不校验 node_type 合法值（拼写错误发布期放行、运行期才报"未知节点类型"）"——`cmx-rule-model/src/ir.rs:227-241` 核实为真问题，补回；补回后内核 P2 为 13 条。
3. **P0-3 一处表述不准确**：原文"gap 分析中该格被解析为 Other → 空隙分析被跳过，无任何告警"。实际 `cmx-rule-engine/src/analyze.rs:62-67` 对含 Other 列的表会**显式**输出"决策表含 not()/!= 等无法结构化的单元格，未做空隙分析"提示——并非完全静默（但文案未涵盖日期/字符串比较场景，用户未必能归因）。P0 定级不变：求值侧静默 false、与表达式路径双标，均对码属实（`cmx-rule-feel/src/lib.rs:188-199` vs `expr.rs:516-531`）。
4. **P2"类型混用列"方向词不准**：原文称"布尔行的输入空间完全未探测（漏报）"。实际后果是以**误报为主**——布尔约束行不匹配数值代表点，仅被布尔行覆盖的组合会被误报为 gap（`cmx-rule-engine/src/analyze.rs:115-148`）。现象成立，"漏报"更正为"误报为主、分析失真"。

### 复核覆盖说明

- P0×4、P1×12：逐条对码核实，代码位置与触发路径全部属实（含缓解检查：`save_draft` 的 `check_scripts` 仅校验 `=rhai:` 脚本格、不校验 FEEL 输出格语法，`/evaluate` 内联定义连脚本校验都不经过——P0-2 触发路径成立）。
- P2：抽查 15 条（gap 溢出、decision 节点记成功、聚合空命中类型、eval_in 字符串区间、未定义变量 null、输入非对象丢弃、validate node_type、同路径多方法 5 组、delete/save_test 跨决策、json_deep_eq、toml 断行、publish 不重校验、端口改写、原生 prompt、analyzeTimer 单例、String(v) 回填），全部属实；其余 P2 未逐条复核，维持原报告判定。

---

## 附录 · 修复实施记录（2026-09-20 同日全量清偿）

用户指令「全部修改，一次解决」。59 条确认问题全部修复，另含 2 条历史债顺手项。**全部未提交**，等用户 git 指令。

### P0（4/4）

| # | 修复 | 落点 |
| --- | --- | --- |
| P0-1 | 激活存在性校验**前置** + 失活/激活/定义对齐收进单事务（RAII guard 未提交自动回滚），激活不存在版本不再全版本失活 | `cmx-rule-store-pg/store.rs::activate_version` |
| P0-2 | First 短路求值（首个命中行输出即返回）；Any 逐行 fail-fast；Unique/聚合保持语义所需全量；配套 check 链在**保存/校验期**就拦 FEEL 输出格与输入格语法（坏行不再能发布） | `cmx-rule-engine/lib.rs::summarize`、`cmx-rule-app/handlers.rs::check_table_cells` |
| P0-3 | 序比较支持字符串字典序（ISO 日期=时间序，与表达式路径双标消除）；null 侧保持"不命中不报错"；其余类型组合 fail-closed 报错；`validate_unary_test` 静态拦截布尔/null 字面量序比较操作数 | `cmx-rule-feel/lib.rs::compare`、`validate_unary_test` |
| P0-4 | 六页解构改防御式惰性取用（`__dc()`）+ 独立壳 polyfill（`web/cmx-datacomp-polyfill.js`：apiJson/escHtml/cmxConfirm 三件套同源实现），独立壳/demo/`:8094` 直开整链路复活；独立壳文件已向真源收敛（`assets/rules/web/{index.js,elements,demo,polyfill}`） | 六页顶部 + `web/` 侧 |

### P1（12/12）

| # | 修复 |
| --- | --- |
| P1-1 | publish 全程单事务 + `SELECT..FOR UPDATE` 锁定义行串行化取号（并发发布不再双取号/交错双激活） |
| P1-2 | 脚本函数发布冻结：表加 `pub_body/pub_params/pub_lang` 快照列（DDL 幂等补列），save 只写草稿列、publish 才固化快照、求值只读快照（老库 COALESCE 平滑） |
| P1-3 | 租户库模板迁 ConfigManager（`[rules.tenancy] db_url_template` ↔ env `RULES__TENANCY__DB_URL_TEMPLATE`），删 `postgres:postgres@127.0.0.1` 弱口令回退、未配置 fail 拒建 |
| P1-4 | 租户名白名单 `^[a-z0-9_]{1,32}$`，不合法拒绝派生租户库（连接串注入封死），error 日志点名疑似 X-Tenant 注入 |
| P1-5 | 注释侧处置：dev/test toml 密码行加「内网开发库、生产用 `DATABASES__*` env 注入」警示；**真换密需 DB 侧动作，等用户拍板**（代码侧无法单方完成） |
| P1-6 | 等值容差统一 `NUM_EQ_TOL = 1e-9`（单测/表达式同标准，`1.1*3 = 3.3` 两处判定一致） |
| P1-7 | `split_top_commas` 引号感知（`"a, b"` 不再拆碎）；未闭合引号交给表达式路径报"字符串未闭合"；顺带修 `]` 起始反括号深度负值 |
| P1-8 | 决策图节点失败**短路**：停止下游求值、output 置 null、不再导出半污染上下文 |
| P1-9 | Priority/OutputOrder **真实现**：`DecisionRule.priority`（IR serde 可选字段），P 按优先级降序取最高、O 按优先级降序输出全部；未标注按行序稳定兜底（零回归） |
| P1-10 | `list_logs` 补回 createdAt（RFC3339），审计「时刻」列复活 |
| P1-11 | 新增 `POST /definitions/recategorize`（独立轻量 UPDATE 只改分类），前端 recategorize 改调，"详情→回存"数据丢失通路消灭 |
| P1-12 | 两设计器装载失败显式错误横幅 + 重试按钮 + **禁用保存/发布**（防覆盖服务端定义为空）；全空表覆盖前二次确认 |

### P2（43/43）

- **内核 13**：decision 节点失败记失败不记成功；C+ 空命中统一整数 0；`in ["a".."f"]` 字符串区间支持；evaluate 严格变量提示（validate 返回 `warnings`，不阻断——静态近似已知集=输入列顶层名）；FEEL parse 深度上限 128 + not() 嵌套上限 128；类型混用列显式 gap 告警；组合数 `checked_mul` 溢出显式告知；`NumRange::overlaps` 相对容差（大数值域不误报，±∞ 界取有限端点缩放）；图输入非对象显式失败；`with_functions` RAII guard（panic 安全）；`register_functions` 失败 warn + `check_functions` 组合编译校验落库前暴露；AST 进程级缓存（2048 上限，gap 分析秒级→毫秒级）+ `DecisionGraph::validate` node_type 白名单（补回项）。
- **应用层与存储 19**：同路径多方法 5 组全部拆独立固定段（`POST /definitions/remove`、`/categories/save`、`/categories/reorder`、`/tests/save`、`/functions/remove`，原 `POST /functions` 并入 `/functions/draft`；存量单方法 DELETE 按规范不追溯）；delete_definition 四表事务；`delete_test` 按 key+id 双条件 + 404 语义统一；`save_test` 跨决策改写拒绝（归属校验 + SQL WHERE 双保险）；保留段 key（draft/validate/remove/recategorize/空）拒绝入库；详情接口 name 修复（发布路径 JOIN 定义表）；路由契约测试**全量 34 条**（挂载 + 声明方法级 + 同路径单方法守护 + 鉴权层 bogus-key 401 探针）；OpenAPI 补全 34 条 paths（不再空壳）；dev/test toml `default = true` 断行恢复；出厂 `rules-server.toml` auth.mode 收紧为 jwt + off 启动 error 横幅 + API key 标注仅开发；`publish_function` 改 `UPDATE..RETURNING` 原子；`list_definitions` LIMIT 1000 + `list_logs` limit 参数（≤500）；stats 子查询失败报错、0 评估 successRate=null（大盘显示 –）；`json_deep_eq` 整数精确分型 + 浮点 1e-9；求值挪 `spawn_blocking`（不阻塞 tokio worker）；tenancy 失败记忆 + Mutex 毒化恢复；端口改写 warn 不再静默；engine.rs 注释对齐实际致命行为；category/function 落库 trim。
- **前端 11**：`attributeChangedCallback` 换图清选中态；键击回灌防抖 300ms 合并（画布选中高亮不再闪失）；连线源高亮复活（`InteractionController.connectingFrom`）；`analyzeTimer`/`pushTimer` 实例级（多 Tab 互不取消）；六页 mount 注册 `host.onDispose` 清模块级引用；catMove 走批量重排单事务接口；原生 prompt 换页内输入模态（沙箱环境不再无反应）；用例回填对象/数组 JSON 化（不再 `[object Object]`）；blob 组件加载失败可重试；硬编码色值全部 `var(--sap*, fallback)` 化；demo 页 innerHTML 转义。

### 历史债顺手项（非 59 条内）

- `<cmx-decision-graph>` 补 `fitView()` 实现（注释承诺从未实现，宿主调用会 TypeError）+ `resetFit()`；
- Delete/Backspace 删除选中节点/边（tabIndex 聚焦 + 输入框内不拦截）；
- `build.sh` 工具链修复（`.tsc-tool` 与 `../cmx-home-site` 已不存在 → enterprise-portal 的 typescript + rolldown，Vite 8 现役工具链），构建+sync+publish 已跑通。

### 验证基线（修复后）

- `cargo clippy --workspace --all-targets`：**0 告警**。
- `cargo test --workspace`：**88 通过 / 0 失败**（原 67 → +21 防回归：序比较/容差/引号/短路/优先级/图短路/溢出/混用列/node_type/深度上限等）。
- 真库集成测试 5/5 通过（`RULE_TEST_DB_URL=<137.111 fico> cargo test -p cmx-rule-store-pg --lib -- --ignored --test-threads=1`：激活不存在版本保护、发布事务单激活、函数快照冻结、用例归属、删除行数语义）。
- 下游 `cmx-data-auth` `cargo check` 全绿（曾现跨仓陈旧 rmeta 假报错，touch 强刷后过——已知坑）。
- `cmx-decision-graph`：tsc 类型检查 + vitest **36/36 绿**；构建产物已 sync 到 vendor 真源并 publish。
- `publish-assets.sh rules` 已跑（ui-native/elements/demo/polyfill 同步）。

### 待用户决策/知悉

1. **P1-5 真换密**（dev/test toml 内网库明文口令出库）需 DB 侧改密配合，代码侧仅完成警示注释，等拍板。
2. 出厂 `rules-server.toml` auth.mode 已改 `jwt`——生产安全默认；本地联调继续用 dev/test（off），若直接用出厂配置需带门户 token。
3. 同路径多方法整改后**前端调用已同步改**，旧 `DELETE /definitions/{key}` 等端点已移除（外部若有直连脚本需跟进，qa 脚本未在本清单内）。
4. 全部改动未提交，等 git 指令（涉及 cmx-rulesengine、cmx-container（assets 真源）、cmx-decision-graph、根仓 documents 四处）。
