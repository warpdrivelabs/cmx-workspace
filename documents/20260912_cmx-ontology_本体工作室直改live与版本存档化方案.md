# 本体工作室「直改 live + 版本存档化」方案（草稿轨彻底移除）

> 日期：2026-09-12 · 模块：cmx-ontology + studio.js · 状态：方案（经两轮对抗性审查 + 用户裁决修订，复核结论可交付实施）
> 前置讨论：同日《本体工作室草稿发布状态机梳理与数据消失诊断》§五——三痛点的代码级核实。
> **用户裁决（最终，覆盖此前"草稿轨保留"的取舍）**：草稿相关的表、端点、代码**全部删除，不留历史包袱**；旧 `POST /publish` 一并删除；om_version 表与代码注释全面改为「存档」语义；编辑态/浏览态是**同一套接口**的「可改/只读」两种视角；六类直改写端点**不补**服务端守卫（与旧设计器对齐）。

---

## 一、背景与问题

现行 P2 双轨：编辑写 `om_draft`（fork/乐观锁/base_rev），发布原子应用到 live 并打 `om_version`。三个经代码核实的痛点：

1. **动作调试闭环被草稿切断（结构性）**：动作执行 `execute_action`（`action_handlers.rs:40`）只读 live——`get_action_type` 查 `om_action_type`，FEEL 校验、ObjectEdit、对象引擎写 `oo_*` 全链路只认 live。草稿里建的对象类型对对象引擎不存在（建不了实例、动作指不到），草稿动作调 `/execute` 404。每次调试迭代被迫走「保存草稿 → 发布中心 → 预览 → 确认发布」。
2. **草稿税 > 评审收益**：双轨为「评审门 + 多人协作」设计；现状 `om_maintainer` 空表（评审门从未启用）、单人建模迭代，fork/基线过期/rebase/丢弃全部泄漏到 UI，纯属负担。
3. **om_version 未产生价值**：唯一消费方是版本中心，而回滚也过发布门（绕一圈还是草稿语义）。

## 二、目标与非目标

**目标**
1. 建类型 → 建动作 → 试算/执行的调试闭环**零仪式**（直改即生效）。
2. 版本历史变为**存档/撤销栈**：一键存档（rev 去重、并发安全）、回滚即生效且回滚留痕。
3. **草稿轨连根移除**：`om_draft` 表、草稿端点、草稿代码、草稿注释全部删除；代码里不再出现「草稿/发布」概念，统一为「编辑（直改）/存档/回滚」。
4. **编辑态/浏览态 = 同一套接口的两种视角**：浏览态=只读查看（写 UI 隐藏/禁用），编辑态=可修改（写 UI 启用）；读写端点完全相同。写权限口径与旧设计器对齐：六类直改端点**不加**服务端守卫（用户裁决，§九）；已有守卫的端点（存档/回滚/场景）维持不变。

**非目标**
- 不动对象引擎/OSDK 读路径（维持「om_* 是已发布真源」铁律）。
- om_version 表结构不变（列名 published_by/summary 保留，注释与代码语义改为「存档人/存档说明」）。

## 三、总体设计

```
旧：编辑 → om_draft（fork/锁/基线） → 发布门（校验+base_rev比对） → 原子应用 live + 打版本
新：编辑 → 直写 live（同一套读写端点，浏览态只是只读视角） ─→ 随时「存档」→ om_version（rev 去重+并发安全）
                                                        任意版本「回滚」→ 恢复 live + 留痕存档
```

- **single source of truth 只剩 live**：studio、旧设计器、对象浏览器、OSDK、动作执行全部同一份 live 定义；「编辑 vs 浏览」只是前端视角切换（可改/只读），服务端无模式概念。
- **版本 = 存档点**：用户主动的检查点；回滚以存档为粒度整体恢复，回滚本身留痕。
- **安全网分层**：前端删除对话框引用提示（refCheck，已有）→ 服务端高危删除引用检查（新增）→ 删除前自动存档（新增）→ 存档/回滚兜底。

## 四、后端设计

### 4.1 新增 `POST /api/onto/v1/snapshots` —— 存档

- 请求体 `{ "summary": "..." }`（可选，默认「（无摘要）」）。
- 逻辑：`snapshot_full()`（六类+views 单语句批量，自 `draft_store.rs:213` 迁移）→ `snapshot_fingerprint` → 与 `latest_rev()` 比对：相同则不插行，返回 `{version: 最新, deduped: true}`；不同则插 `om_version`。
- **并发安全（第一轮审查 🟠-1）**：`om_version.version` 是主键，`MAX(version)+1` 两段式并发撞号 500。实现必须：全程单事务 + `INSERT ... ON CONFLICT (version) DO NOTHING`，0 行插入则重读 latest 重算重试（≤3 次）；或 `pg_advisory_xact_lock` 序列化。二者选实现简单者。
- **快照瘦身（🟡-2）**：存档剥离 views 的 `layout` 字段（layout 不进指纹、回滚也不恢复，重复入库纯浪费）。
- **SSE 事件契约（🟡-3）**：广播事件名沿用 `published`，payload `{version, rev, deduped, summary, publishedBy}`（前端靠 `publishedBy === D.me` 过滤自发提示）。
- 响应：`{ version, rev, deduped, summary }`。鉴权：`require_maintainer`（空表=开放）。

### 4.2 回滚即生效：重写 `POST /versions/restore`（草稿路径随草稿删除）

- 新语义（唯一语义，无 apply 参数）：请求 `{version, confirmMassDelete?}` → 装载 `om_version.snapshot` → **单事务直应用 live**：六类批量 upsert（复用现 `publish_draft_tx` 骨架的 `UPSERT_*` 常量，整体迁出 `draft_store.rs`）→ views 应用/删除（manual 删、auto 豁免）→ 派生删除集 = live − 快照批量 DELETE → 级联清 implements → 插留痕存档（summary=「回滚到 v{n}」）→ SSE 广播。
- **留痕与去重的边界**：回滚目标与当前 live 指纹全等时不插留痕行，响应 `deduped: true`，前端 toast「live 已与 v{n} 一致」。
- **旧版本 views 段回填**：P2 前快照无 views 段 → 保留当前 live 场景不动（原 `draft_handlers.rs:429-438` 逻辑迁入）。
- **派生删除边界（写明为设计语义）**：回滚只动 `om_*` 定义表，**不 DROP `oo_<type>`、不删实例数据**（`object_engine.rs` 惰性 ensure、全仓无 DROP TABLE）。删类型后实例数据原地保留、回滚恢复定义后重新可见——「删类型可撤销到数据级」。已知限制：回滚前后主键属性变更时 `oo_` 表结构与新定义可能漂移（直改同风险，不处理）。
- 校验：`validate_snapshot`（原 `validate_draft` 经 M1 改名的 Value 基签名——快照为目标、live 为基线，Error 级阻断）+ 大规模删除护栏（`max(50, liveTotal/5)` + `confirmMassDelete`）。

### 4.3 删除清单（不留历史包袱）

**删表（ddl.rs）**
- 删 `om_draft` 的 `CREATE TABLE` 与相关 COMMENT；追加 `DROP TABLE IF EXISTS om_draft`——放独立常量段（如 `DDL_CLEANUPS`，与建表/补列的 `DDL_STATEMENTS` 区分，注释声明「一次性清理，可随稳定性移除」），经 `ensure_schema` 启动幂等重放（第二轮复核确认无 FK 依赖、无顺序冲突）。

**删端点（lib.rs 路由 + handler 文件）**
| 删除 | 原职责 | 去向 |
| --- | --- | --- |
| `GET /draft`、`POST /draft/save`、`POST /draft/discard` | 草稿 CRUD/fork | 无（概念消亡） |
| `POST /releases/preview`、`POST /releases/publish` | 发布门 | 校验/护栏逻辑迁入 restore（§4.2）；存档由 `/snapshots` 承担 |
| `POST /publish`（旧，`handlers.rs:407` + `store.rs:213` `publish()`） | 旧式快照打版本（N+1、无去重） | **删除**；调用方 designer.js / dashboard.rs 切 `/snapshots`（一行改动） |
| `POST /versions/restore` 旧实现 | 写草稿 | 重写为 §4.2 直应用（同路径复用） |

**删代码文件/模块**
| 文件 | 处置 |
| --- | --- |
| `cmx-onto-app/src/draft_handlers.rs` | **整文件删除**；`require_maintainer`/`me_roles` 迁至 `handlers.rs`（权限守卫仍需要）；`versions_diff`/`resolve_snapshot` 迁至 `handlers.rs` 版本段 |
| `cmx-onto-store-pg/src/draft_store.rs` | **整文件删除**；存活件迁移：`snapshot_full`/`snapshot_value`/六类 `list_*_defs`/`UPSERT_*` 常量/`derive_deletions_tx`/`apply_deletions_tx`/`latest_rev`/`PublishCounts` → 新 `snapshot_store.rs`（存档+回滚共用）；`get/save/insert/restore/discard_draft_row`、`store.rs:298-344` 私有 `snapshot()`（仅被旧 `publish()` 使用的 N+1 旧快照）等删除；`list_maintainers` 迁 store.rs |
| `view_handlers.rs:28-31` | `draft_err` 委托 `crate::draft_handlers::draft_store_err`——随视图重写迁移/内联（M2） |
| `cmx-onto-model/src/draft.rs` | **重构改名 `snapshot.rs`**：保留纯函数 `snapshot_fingerprint`/`diff_snapshots`/`derive_deletions`/`kind_key`/`KIND_*`（存档、回滚校验、版本 diff 消费）；**`validate_draft` 改为 Value 基签名 `validate_snapshot(target: &Value, deletions: &[DeletionRef], live: &Value)`**——现签名 `(&DraftContent, &Value)` 依赖被删类型，函数体本就主要作用于 `to_snapshot_value()` 产物（第二轮复核 M1，不改必编译失败），`validate_shape` 并入其中或随草稿保存消亡；删除 `DraftContent`/`DraftRow`（被快照形状 Value + `DeletionRef` 取代）；`lib.rs` 导出同步更新；文件内 8 个单测随重构改写 |
| `openapi.rs:53` | 删 `"/publish"` 条目，补 `/snapshots`（第二轮复核 M2） |
| `handlers.rs:429-434` | `PublishReq`（旧发布请求体）随 `POST /publish` 删除（M2） |
| `cmx-onto-store-pg/src/lib.rs:7` | `pub mod draft_store;` → `pub mod snapshot_store;`（M2） |

**删注释/文案（全面换「存档」语义）**
- `ddl.rs`：`COMMENT ON TABLE om_version`「发布版本快照表」→「本体存档快照表（检查点，可整体回滚）」；`rev`→「内容指纹（xxh64，去重锚）」、`summary`→「存档说明」、`published_by`→「存档人」、`published_at`→「存档时间」；`publishedVersion` 相关注释同步。
- 代码内：`store.rs`/`handlers.rs`/`stats.rs`/`events.rs` 中「发布/草稿」字样注释全部改写；`OntologyVersionMeta` 字段注释同步（字段名不改）。
- 前端：studio.js/designer.js/dashboard.rs 全部「发布/草稿」文案 →「存档」（§5.3）。

### 4.4 直改后的安全网（第一轮审查 🟠-4 补强，全部进 P1）

1. **高危删除服务端引用检查**：`DELETE /object-types/{name}`、`DELETE /shared-properties/{name}` 增加引用检查——对象类型被关系/动作编辑规则/视图成员引用、共享属性被对象属性/接口引用时 409（复用 `validate_snapshot` 检查口径，提示引用方清单）。
2. **删除前自动存档**：六类 delete 端点删除前自动插存档（`auto_snapshot_before(op)`，summary=「删除 {kind} {name} 前」），复用 §4.1 并发安全实现——删除永远可撤销。**顺序钉死：先引用检查（409 可拒绝）→ 后自动存档 → 再删除**——避免被拒的删除留下噪音存档行（第二轮复核建议）。
3. 其余写操作靠手动存档 + 回滚兜底。

### 4.5 视图写轨回归 live

- **视图端点重写为 live 直写**（`save_view`/`remove_view` 现写草稿 views 段，`view_handlers.rs:129-224`——草稿删除后必须重写）：改调 `view_store.rs` 现成的 `upsert_view_locked`（B0 乐观锁）/`delete_view`；`SaveViewReq.version` 语义 = `om_view` 行版本；`remove_view` auto 行豁免（布局物化产物，与派生删除同口径）；SSE 事件 `draft-changed` → `view-changed`。`/views/layout` 本就直写 live，不动。
- **六类写端点守卫：不做（用户裁决）**——直改端点与旧设计器行为完全对齐（旧设计器 POST/DELETE 本无守卫），写入口的权限语义由前端视角门控承担（§5.1）；已有守卫的端点维持不变，**完整清单**：`POST /views`、`POST /views/remove`、`POST /views/layout`（layout 也在守卫内）、`POST /versions/restore`、`POST /snapshots`（新增）——实施/文档按此对齐。绕过 UI 直调六类 API 的写与旧设计器同风险面，接受。
- **评审门启用 checklist（第二轮复核要求留档）**：守卫不对称是延期风险——当前 `om_maintainer` 空表=开放，全部守卫"装饰性"，无实际暴露面扩大；**一旦向 `om_maintainer` 插入首行（启用评审门），必须同批给六类写端点补 `require_maintainer`**，否则不在白名单的账号对场景/回滚/存档吃 403 却仍可直删定义（未被引用者服务端无拦），守卫分裂即刻成为真实漏洞。本 checklist 置于 §八 遗留事项，实施后随代码移交。

## 五、前端设计（studio.js + designer.js + dashboard.rs）

### 5.1 模式语义：同一套接口的「查看/编辑」视角

- 「浏览态/编辑态」开关**保留**，语义改为「查看/编辑」：`S.mode === 'browse'` = 只读视角（写按钮隐藏/禁用、画布 readonly），`'edit'` = 可修改视角；**两态读同一套 live 端点，无任何数据/接口差异**——切换不再触发草稿装载（`toggleMode` 的 `ensureDraft`/overlay 分支删除，只重渲染）。
- 权限：`D.available === false`（非维护角色）恒只读——**前端视角门控是唯一写权限闸口**（六类直改端点服务端不加守卫，用户裁决 §九，与旧设计器对齐）；维护角色两态可切。
- **动作执行入口（🔴-2 修正）**：`canExec = S.mode !== 'edit'` 有**两处**（studio.js:2086 定义 + :2149 编辑态渲染硬编码 `runPanelHtml(d, canTry, false)`——只改一处编辑态仍不出现执行按钮），统一改为 `canExec = D.available !== false`——⚡执行两态常驻，点击弹红色确认框（列出目标对象类型与编辑规则数；真实执行写 `oo_*` + Outbox）。原「浏览态才可执行」是草稿轨产物。
- 场景写按钮的门控统一为 `S.mode === 'edit' && D.available !== false`（现 ~10 处只判 `S.mode`，studio.js:1181/1190/1296-1305/2833/2868/2892/2921/2692，逐一补 `D.available`）。

### 5.2 写路径换直改端点

| 操作 | 旧（草稿轨） | 新（直改） |
| --- | --- | --- |
| 新建/编辑对象类型 | `persistElement` → `draftUpsert` + `POST /draft/save` | `POST /object-types` |
| 删除元素 | `draftRemove` + 保存草稿 | `DELETE /object-types/{name}` 等（§4.4 安全网） |
| 新建五类 | 同上草稿轨 | `POST /link-types` 等 |
| 场景成员 | 草稿 views 段（`version`=草稿行锁） | `POST /views`（`version`=`currentViewRow().version`） |
| 场景布局 | `POST /views/layout` | 不变 |

- **草稿机制拆除用全量引用点清单驱动**（🟠-5：`D.row` 读取点约 40 处）——实施时先 grep 生成清单，逐点标注处置：
  - **删除**：`applyDraftOverlay`/`mergedArray`/`mergedViews`/`draftUpsert`/`draftRemove`/`deletedNames`/`ensureDraft`/`persistDraft`/目录 overlay/`overlaySceneGraph` 草稿分支/SSE draft-changed 提示；
  - **换 live 来源**：`selectElement` 草稿优先取 def（:2980）、画布挂接/摘除 def 查找（:2879/:2904）、`deprecateObjectType`（:3690）、`refCheck`（:3870）、`ifaceImplBy` 差量（:2000）；
  - **换 version 来源**：`saveView`/`saveViewFor`/`deleteScene`/`to-manual` 的乐观锁基线（:242/:4167/:4184/:3270）→ `currentViewRow().version`；
  - **简化**：`reloadLive`/SSE `published` 处理器去 D 依赖；`toggleMode` 去草稿装载。
- **其他页面**：designer.js「发布」按钮与 dashboard.rs「发布本体」→ `POST /snapshots`、文案「发布」→「存档」（各一行级改动；explorer.js 不涉及，已核实）；**`designerback0912.js`（:257 调 `/publish` 的旧设计器备份，未注册进 index.json 的死文件）直接删除**——否则是漏网的 `/publish` 调用方，且会随 publish-assets.sh 打包分发（第二轮复核 M4）。

### 5.3 UI 与文案替换

| 旧 UI | 新 UI |
| --- | --- |
| 「发布」按钮 + 发布中心（预览/校验/基线警告/丢弃重开） | 「存档」按钮：确认框（摘要输入）→ `POST /snapshots` → toast「已存档 v{n}」/「内容与上次存档一致（v{n}）」 |
| 「● 草稿待发布」徽标、「基线过期/丢弃草稿重开」 | 移除 |
| 版本中心「回滚」写草稿 + 二次发布 | 「回滚」确认框（先 `GET /versions/diff?a=v{n}&b=live` 展示 diff 概要；大规模删除红色警告+确认）→ `restore` → reloadLive + toast「已回滚到 v{n}」/「live 已与 v{n} 一致」 |
| 开关文案「浏览态/编辑态（写草稿）」 | 「查看/编辑」（title：查看=只读；编辑=修改即生效） |
| 动作试算/⚡执行 | 试算不变；⚡执行两态常驻 + 红色确认框（§5.1） |

**存量文案清理（🟡-1）**：「试算/执行均基于已发布定义…」(:2157)、「先落草稿防丢」(:2361-2369)、「不产生草稿、直接生效」(:2417)、「已写入草稿（发布后生效）」(:3577/:3609)、「废弃 toast」(:3694)、「挂接/摘除实现 toast」(:4123/:4137)、「场景删除/移出 toast」(:4187/:4207)、「回滚=写草稿」(:679)——全部改写为直改/存档口径，行号以实施时 grep 为准；designer.js/dashboard.rs 的「发布」文案同步。

### 5.4 双主题与规范

- 新增/调整 UI 沿用 page-kit token（`--sap*`/`--neo-*` 派生），零硬编码色值；新端点 POST+JSON body、无可变路径段。

## 六、兼容性与风险

| # | 风险 | 评估/缓解 |
| --- | --- | --- |
| R1 | 直改即对消费方可见，改错立即可见 | 单人开发场景可接受；三道安全网（§4.4）+ 存档/回滚兜底 |
| R2 | 并发编辑覆盖：行级乐观锁仅对象类型（B0）与场景（upsert_view_locked）；关系/接口/共享属性/动作/函数盲写、delete 无锁——双开标签页改同一动作后者静默覆盖 | 与旧设计器同风险，单人场景接受，如实声明 |
| R3 | 失去多元素原子发布 | 代价明示；「存档」只记检查点不承担原子性 |
| R4 | 大规模误删/悬空引用 | §4.4 三道安全网；派生删除护栏数定义不数实例数据（实例本就不删） |
| R5 | 消费角色误得写权限 | 前端视角门控（§5.1）为唯一闸口；六类直改端点不加服务端守卫（用户裁决，与旧设计器对齐）——绕过 UI 直调 API 的写与旧设计器同风险面，接受 |
| R6 | om_version 膨胀 | rev 去重 + 存档剥离 layout；真膨胀再引入保留策略 |
| R7 | `/snapshots` 并发撞版本主键 | §4.1 单事务 + ON CONFLICT 重试 / advisory lock |
| R8 | 快照与 `oo_*` 实例数据漂移（主键变更场景） | 已知限制（§4.2），不处理 |
| R9 | **删除端点的破坏面**：`POST /publish` 删除影响 designer.js/dashboard.rs；`/releases/*` 删除影响 studio.js（本方案改造对象） | designer/dashboard 同步切 `/snapshots`（§5.2）；升级与前端同批上线，避免窗口期 404 |
| R10 | 草稿代码删除的连带编译面 | `draft.rs`→`snapshot.rs` 重构后 `KIND_*`/指纹/diff/校验导出保持（`KIND_*` 词表的真实消费方是 Rust 侧回滚校验/diff；studio.js 的 DELKIND 等是前端本地常量，独立存留）；实施以 `cargo check` 全仓 + 前端 `node --check` 收口 |

## 七、实施步骤与验收

**P1（一次交付）**
1. 后端删除：`draft_handlers.rs`/`draft_store.rs` 整删、`draft.rs`→`snapshot.rs` 重构、路由与 `POST /publish`/`store().publish()` 删除、`om_draft` DROP + COMMENT 更新（§4.3 全清单）。
2. 后端新增/重写：`POST /snapshots`；`versions/restore` 直应用；`save_view`/`remove_view` live 化；高危删除引用检查；删除前自动存档；`require_maintainer`/`versions_diff` 迁移落位（六类写端点守卫不做，§4.5）。`cargo check` + clippy 全绿，存量测试（`cmx-onto-model` 79 例中 draft 相关用例随重构迁移/改写）全过。
3. 前端：studio.js（§5 引用点清单驱动）+ designer.js/dashboard.rs 切 `/snapshots`；`node --check` + 浏览器全功能回归。
4. 文档：本文件 §八 补记；全景文档相应章节更新。

**验收标准**
1. 新建对象类型 → 对象浏览器立即可见可建实例，无需任何发布动作；
2. 新建动作 → 立即可试算；⚡执行两态常驻（维护角色 + 红色确认），真实执行写 `oo_*` 生效；
3. 存档重复触发不涨版本；并发存档不 500；
4. 回滚 v{n} 后 live 立即恢复、本身留痕；目标与 live 全等时提示一致不插行；
5. 删除对象类型：被引用时服务端 409 出清单；删除前自动产生「删除前」存档；`oo_` 实例数据保留；
6. 场景成员编辑/删除直生效；**库内无 `om_draft` 表**（`\dt om_draft` 不存在）；
7. 全代码库残留检查：cmx-ontology + studio.js/designer.js/dashboard.rs 中 `om_draft|/draft|draftUp|draftRemove|draftPend|ensureDraft|persistDraft|草稿` 词表 grep 零命中（**豁免**：`propDraft` 家族——`S.propDraft`/`__pkDraft` 等 ~51 处为属性表格编辑缓冲，与草稿轨无关合法存留；`validate_snapshot` 已随 M1 改名不误报）；
8. 浏览态（查看）与编辑态调用同一套端点，差异仅写 UI 门控；消费角色页内两态均只读（前端视角门控；六类直改端点无服务端守卫属裁决口径）；
9. 新 UI 走双主题 token；`GET /versions/diff`、`/me/roles`、`/stats` 等保留端点行为不变；`/publish` 全仓（含 openapi.rs、designerback0912.js）零引用。

**工作量估计**：后端删除 ~1380 行（draft_handlers.rs 500 + draft_store.rs 880 + 旧 publish/snapshot 约 60，第二轮复核校准）+ 新增/迁移 ~500 行；前端净减 ~300 行；1.5～2 天。

## 八、实施补记与遗留事项

> （实施完成后回填：改动清单、验证证据）

**遗留事项（随代码移交）**
1. **评审门启用 checklist**：向 `om_maintainer` 插入首行前，必须同批给六类直改写端点补 `require_maintainer`（理由与完整守卫清单见 §4.5）——否则守卫分裂成真实漏洞。
2. 快照保留策略（R6）：rev 去重 + layout 剥离后暂不膨胀，真膨胀再引入。

## 九、审查记录与裁决

**第一轮对抗性审查**（子智能体，2026-09-12）：🔴×2 / 🟠×7 / 🟡×7。处置：

| 问题 | 级别 | 裁决 |
| --- | --- | --- |
| 视图端点实写草稿（原方案事实错误） | 🔴-1 | 采纳并升级：随草稿删除，重写为 live 直写（§4.3/§4.5） |
| `S.mode` 恒 edit 锁死 ⚡执行入口 | 🔴-2 | 采纳：`canExec` 挂 `D.available` + 红色确认框（§5.1） |
| `/snapshots` 并发撞版本主键 | 🟠-1 | 采纳：单事务 + ON CONFLICT 重试 / advisory lock（§4.1） |
| B0 锁覆盖面夸大 | 🟠-2 | 采纳：R2 如实改写（§六） |
| 消费角色门控挂 S.mode + 直改端点无守卫 | 🟠-3 | 部分采纳：前端门控落地（§5.1）；服务端补守卫经用户裁决**不做**（§4.5） |
| 服务端引用完整性门消失 | 🟠-4 | 采纳：高危删除引用检查 + 删除前自动存档进 P1（§4.4） |
| `D.row` 引用点 ~40 处清单不全 | 🟠-5 | 采纳：清单驱动改造（§5.2） |
| 回滚留痕与去重相克 / views 段回填遗漏 | 🟠-6 | 采纳：全等不留痕边界 + views 回填（§4.2） |
| oo_* 实例数据边界未写明 | 🟠-7 | 采纳：写为设计语义 + 主键漂移已知限制（§4.2/R8） |
| 文案/事件契约/清表落点/dashboard 污染/layout 入库 | 🟡-1~5 | 全部采纳（§5.3/§4.1/§4.5/§六 R6） |

**用户裁决（第二轮前，2026-09-12）**：推翻第一轮疑点裁决中「草稿轨端点原样保留」的立场——**草稿表/端点/代码/注释全部删除，不留历史包袱**；旧 `POST /publish` 一并删除（designer/dashboard 切 `/snapshots`）；om_version 表与代码注释全面改为存档语义；编辑态/浏览态定义为同一套接口的「可改/只读」视角。方案已按此全面重写（§四删除清单、§五模式语义、§六 R9/R10 新增）。

**用户裁决补充（第二轮中，2026-09-12）**：六类直改写端点**不补**服务端守卫（🟠-3 的服务端部分不做）——写权限口径与旧设计器对齐，前端视角门控为唯一闸口（§4.5/§5.1/R5 已同步修订）。

**第二轮复核**（同一子智能体，2026-09-12，按最新裁决版）：第一轮 9 项实质问题处置经代码逐条复核**全部成立**；「彻底删除」路径全仓 grep 验证无漏网编译面。新发现 4 项必须修订，已全部落入正文：M1 `validate_draft` 改 Value 基签名 `validate_snapshot`（§4.3，现签名依赖被删类型必编译失败）；M2 删除/迁移清单补漏 5 处（`draft_store_err`/`openapi.rs:53`/`store.rs:298-344 snapshot()`/`handlers.rs PublishReq`/`store-pg lib.rs:7` 模块声明，§4.3）；M3 验收 7 grep 口径精确词表 + `propDraft` 家族豁免（§七）；M4 死备份 `designerback0912.js` 删除（§5.2）。建议项同批采纳：评审门启用 checklist 留档（§4.5/§八）、auto-snapshot 先检查后存档顺序（§4.4）、:2149 第二处 canExec 行号、工作量行数校准（500/880）、R10 表述修正、`snapshot_full` 行号、ddl.rs DROP 独立常量段。**复核结论：可交付实施。**
