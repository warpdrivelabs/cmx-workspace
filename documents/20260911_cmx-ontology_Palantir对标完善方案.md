# cmx-ontology × Palantir 对标完善方案

> 口径：针对 `docs/20260911_本体平台_Palantir对标_已有与欠缺.html` 的**核验结论 + 可执行完善方案**。
> 基线：cmx-ontology `main@567efe4`（2026-09-11，与 origin 同步）代码实测。
> 本文件遵 plan-naming 归档于根 `documents/`（方案不入子仓 docs/）。

---

## 一、核验结论：文档是否属实

**结论：后端主张全部属实、证据扎实；仅前端"横切·工程债"一节 2 条失实、草稿并发 1 处措辞偏差。** 可放心作为路线图依据。

### 已逐条代码核实为**属实**的主张

| 类别 | 主张 | 证据（文件:行） |
|---|---|---|
| **P0-S1** | 主体身份可自报、角色用租户名占位 | `pep.rs:144-156 subjects_from`（body `subjects` 逐字信任、恒优先于令牌；空则 `current_tenant()` 当角色）；`action_handlers.rs:353` 同构 |
| **P0-S2** | Funnel 源 SQL 不设防（任意 SQL + 字符串拼接） | `funnel_store.rs:151` 直接执行存储的 `source_query`（无只读/表级授权/白名单）；`:101` `WHERE object_type='{}'` 字符串拼接 |
| Q1 | isIndexed 物理索引未消费 | `object_store.rs:214-230` 建表仅 pk 主键 + title 索引，不读 `is_indexed`；model trait 文档（`object_store.rs:19`）承诺"按 isIndexed 建索引"却未兑现（契约自相矛盾） |
| Q2 | 删对象清边全局 pk 误删同名 | `object_store.rs:302-307` `DELETE FROM ol_edge WHERE a_pk=$1 OR b_pk=$1`（不分对象类型）；`action_exec.rs:180` 另有一份 |
| Q3 | 发布撞版本号 | `store.rs:222-248` `SELECT MAX(version)+1` 后 INSERT，非原子/无锁/无 sequence；撞号→唯一键冲突→该次发布失败（丢更新） |
| Q4 | FEEL 数值走 f64、金额精度隐患 | `feel.rs:41 Num(f64)`，算术全 `as_f64`（`:473/:561`） |
| T1 | 全仓无调度器 | 零 `tokio::time::interval`/cron；同步、outbox 派发均为 HTTP 端点靠外部触发 |
| 功能 | 对象编辑历史缺失（旧值不落库） | `action_exec.rs:150-163` 读旧 props 后原地 `UPDATE SET props=$1` 覆盖丢弃；审计只记新值 `edits_to_json :499` |
| 功能 | 无全文搜索（连 pg_trgm 未开） | 全仓无 `to_tsvector`/GIN/`CREATE EXTENSION`；唯一 ILIKE 是元数据过滤 `view_store.rs:209` |
| 功能 | wasm 未实装、NativeRust 仅 1 内置 | `function_runtime.rs:17` Wasm→`UnsupportedRuntime`；`:35-40` 注册表仅 `nativeTierTax` 一支 |
| 功能 | SSE 进程内广播、掉线丢、多副本不互通 | `events.rs:25` 进程内 `OnceLock<broadcast::Sender>`；`:70 Lagged=>continue` 丢事件；无持久化/MQ |
| 安全 | om_maintainer 空表=放行 | `draft_handlers.rs:32-39` `if rows.is_empty(){return Ok(())}`；`ddl.rs:205` 注释"空白名单=开放" |
| 功能 | 异步任务中心缺失（T5） | 无 task/job 表与 `/tasks` 路由；`run_sync`/`import` 均在 HTTP handler 内同步跑完 |
| 功能 | OSDK 仅 TS 单语言 | `osdk.rs` 仅 `generate_typescript`；路由仅 `/osdk/typescript` |
| 建模 | backing：edge 全量 / FK 仅读侧 / joinTable·intermediary 未实装 | `compile.rs:130-191` FK 走 `fk_search_around`；`put_link`/`AddLink` 不看 backing 一律写 ol_edge；`compile.rs:136 _=>` joinTable/intermediary 回退 ol_edge |

### 需**修正/精确化**的三点（据此调整方案范围）

| 文档主张 | 实测 | 修正 |
|---|---|---|
| 前端 vendor 落后 dist、"平台跑旧组件" | **不属实**：ontology-graph / ontology-canvas / decision-graph / datacomp-subset 的 vendor 与 dist md5 **逐一一致** | 该工程债**不存在**；"把 sync 挂进 build"可作预防性纪律，但非当前缺口 |
| cmx-ontology-canvas 未交付、无页面引用 | **不属实**：已入 `cmx-container/assets/onto/web/ui-native/vendor/cmx-ontology-canvas.js`，且注册页 `portal.onto.studio`（`studio.js` `document.createElement('cmx-ontology-canvas')` :1491）已挂载；仅"千级 LOD 全量虚拟视图"档标 P4 延后 | 组件**已交付**；只剩 P4 大规模档 |
| 草稿"两人同时改互相踩" | **部分属实**：单区 id=1 属实，但保存走行级乐观锁 `WHERE id=1 AND version=$5`→不符即 409（`draft_store.rs:121-144`），**不会静默丢更新** | 真实短板是"单草稿区无并行分支"，非"互相踩" |

> 即：文档"一页纸结论"的"本周两件小事"（同步 vendor、接线 canvas）**实已完成**——文档对当天刚落地的 P1/P2（studio/canvas）判断滞后。其余结论成立。

### 探子附加发现（强化 backing 缺口，方案已纳入）
**FK 关系读写不对称**：写侧 `put_link`/Action `AddLink` 把边落 `ol_edge`，读侧 `fk_search_around` 只从对象表 FK 列取 → 经 Action 给 FK 关系加的边，FK 读路径永远查不到。这是"FK 仅读侧编译"的具体代价。

---

## 二、完善方案（按优先级；每项：缺口 → 做法 → 落点 → 验收 → 粗估）

### P0 · 安全止血（能否上生产的分水岭）

#### S1 主体身份不可自报
- **做法**：引入 `[authz] mode = off | local | dataauth` 三态开关（onto 专属段，ConfigManager 读）。`local`/`dataauth` 模式下**一律忽略请求体 `subjects`**，主体只从 JWT 上下文派生（`current_user` + JWT `roles` claim，不再用租户名占位）；`dataauth` 模式进一步 HTTP 调 `cmx-data-auth /decide` 拿行残差/脱敏义务（复用已 path-dep 的 dataauth-core 决策模型）。`off` 保持现状兼容（本地/单测）。
- **落点**：`pep.rs:144 subjects_from` + `action_handlers.rs:353 subjects_of` 增加模式判定；`object_handlers.rs:183/215/249`、`policy_handlers.rs:83`、`action_handlers.rs:70` 调用点统一经新入口；新增 `[authz]` 读取（仿 dataauth 的 `auth.*` ConfigManager 直读）。
- **验收**：E2E `o6_authz_hardgate.sh` 扩——`local` 模式下 body 自报 `role:admin` 被忽略、以令牌角色为准；受控类型无令牌角色→403；`off` 模式回归现状。
- **粗估**：8–10 人日（文档口径，方案已备）。

#### S2 Funnel 源 SQL 治理
- **做法**：`source_query` 上治理闸——(a) 只读校验（model 加纯函数 `validate_source_query`：仅允单条 SELECT/CTE，拒 DDL/DML/多语句/注释注入）；(b) 表级白名单（映射保存时登记可读表，执行前校验 FROM/JOIN 目标 ∈ 白名单）；(c) `load_mapping` 的字符串拼接改参数化。
- **落点**：`funnel_store.rs:101`（参数化）、`:151`（执行前插入校验）；model 新增 `validate_source_query`（零 IO 可单测）；保存映射 handler 加登记。
- **验收**：E2E——非 SELECT / 越权表 / 多语句被拒；正常只读 SELECT 通过；既有 `o3_funnel.sh` 回归。
- **粗估**：3–5 人日。

### P1 · 性能与正确性（能否扛大流量 / 数据对不对）

| 项 | 做法 | 落点 | 粗估 |
|---|---|---|---|
| **Q1 isIndexed 建索引** | `ensure_object_table` 按 `def.properties[].is_indexed` 建 JSONB 表达式索引 `CREATE INDEX ... ON oo_<t>((props->>'p'))`（数值属性另建 `::numeric` 索引）。需给 ensure 传入 def（现签名未带）。 | `object_store.rs:214-230` + 调用处 | 2–3 天 |
| **Q2 清边误删** | `ol_edge` 端点加 `a_type/b_type` 列（schema 迁移），put/delete 按 (link,a_type,a_pk,b_type,b_pk) 精确；清边 DELETE 加类型约束。 | `object_store.rs:302-307` + `action_exec.rs:180` + `ddl.rs` ol_edge 表 | 3–4 天 |
| **Q3 发布版本号原子化** | 改用 PG sequence 或单事务 + `SELECT ... FOR UPDATE`/重试；撞号不再丢发布。 | `store.rs:222-248` | 1–2 天 |
| **T1 调度器** | 最简：外部 cron 调 `/funnel/sync` + `/action-outbox/dispatch`（文档化即可）；进阶：内置 `tokio::interval` + `SELECT FOR UPDATE SKIP LOCKED` 可重入（守 CLAUDE.md 集群无状态约束）。 | 新增 scheduler 模块 / 或仅运维文档 | 1 天（文档）/ 4–5 天（内置） |
| **T4 增量水位** | `source_query` 支持 `{cursor}` 占位 + `om_source_mapping` 加源侧游标列（非 last_sync_at 墙钟），`load_mapping` 回读注入增量 SQL。 | `funnel_store.rs:101/151` + ddl | 3–4 天 |
| **Q4 FEEL 金额精度** | 评估项：FEEL 数值引入 `rust_decimal` 定点，或约定"金额计算走 nativeRust/SQL numeric 不进 FEEL"并在校验层拦截。建议先评估再定。 | `feel.rs` | 评估后定 |

### P2 · 平台能力补课（像不像一个平台）

| 项 | 做法 | 落点 | 粗估 |
|---|---|---|---|
| **对象编辑历史** | 新增 `oo_history`（object_type/pk/property/old_val/new_val/actor/at）；ModifyObject 执行时 diff 旧→新落历史 + `/objects/{type}/{pk}/history` 查询。 | `action_exec.rs:150-163`（覆盖前 diff）+ ddl + handler | 4–5 天 |
| **全文搜索** | 开 `pg_trgm` + 对象表 GIN 索引 + `/search` 端点（跨类型 trigram）+ 浏览器搜索框。 | ddl + store-pg + `object_handlers` + 前端 explorer | 5–6 天 |
| **backing 补全 + FK 读写对齐** | foreignKey 写侧落地（put_link 按 backing 写对象表 FK 列，消除读写不对称）；joinTable/intermediary 读写实装。 | `object_store.rs put_link` + `compile.rs` + `action_exec.rs:191 AddLink` | 5–7 天 |
| **wasm 函数运行时** | Extism 插件接入（方案已探明链路：RuntimeInvoker + ExtismEngine + 插件 wasm_path + rmp-serde）。**测试缺口**：需装了插件的环境验 E2E。 | `function_runtime.rs:17` | 5–6 天 |
| **聚合扩展** | 补 avg/min/max + 独立 Sum。 | `objectset.rs Aggregation` + `object_store.rs:430-483` | 2 天 |
| **异步任务中心（T5）** | 任务表 + `/tasks` 查询 + run_full_sync/import 改异步提交 + SSE 进度（funnel 已自认 M2）。 | 新增 task 模块 + 改造 funnel/import handler | 6–8 天 |
| **SSE 持久化 / 多副本** | 事件落表补发（掉线重放）或接 NATS；多副本共享。 | `events.rs` + ddl/MQ | 4–6 天 |
| **多分支草稿** | 草稿从单区 id=1 → per-user/branch + 提案合并（已有乐观锁防丢，缺并行隔离）。 | `draft_store.rs` + ddl | 6–8 天 |
| **OSDK 多语言** | Python/Java 生成器。 | `osdk.rs` + handler | 各 3–4 天 |

### P3 · 生态（能否长出应用生态）
- **MCP 工具面**：把本体端点包成 MCP 工具，让 cmx-agent 查对象/执行动作——本地版"AIP 时刻"，随 cmx-agent 规划。
- **本体感知 AI 助手**、**双向闭环回写**（流程审批→本体 T3、本体→MDM T7）、**模板市场**（动作模板→跨域本体模板）。

### ⛔ 明确不跟（同文档，不列入缺口）
换图数据库 / RDF-OWL-SPARQL / 联邦查询 / IoT 数字孪生——均为有意不做，理由见对标文档 §⑤。

---

## 三、对标文档本身的勘误建议
建议更新 `docs/20260911_...html` 三处，避免误导后续决策：
1. **横切·前端工程债 → vendor 落后 dist**：删除或改为"已一致（md5 核验通过）"；"sync 挂进 build"降级为预防性建议。
2. **横切 → cmx-ontology-canvas 未交付**：改为"组件已交付、入 assets、studio 页已挂载；仅千级 LOD 全量虚拟视图档 P4 延后"。
3. **F-10 / 一页纸 → 草稿"互相踩"**：改为"单草稿区（有乐观锁防丢更新），缺多人并行分支"。
4. 相应地，"一页纸结论"的"本周两件小事"已完成，可移除或标注"✅ 已落"。

---

## 四、排期建议
1. **先 P0**（S1 + S2）——安全分水岭，S1 方案已备。二者独立，可并行。
2. **再 P1**——Q2/Q3 是小而确定的正确性债（各 1–4 天），优先；Q1/T4 提性能；T1 先出运维文档、内置调度按需。
3. **P2 挑平台感三件**（编辑历史 / 全文搜索 / 异步任务中心）+ backing 补全（顺带修 FK 读写不对称）。
4. **P3 押 MCP 工具面**——对标叙事最值得投入的一步。
- **纪律**：每项独立 PR + 单测 + 真机 E2E（沿用 `test/e2e/` 22 脚本模式）；改 model 保零 IO；提交遵多仓铁律。
