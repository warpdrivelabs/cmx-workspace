# cmx-ontology + cmx-ontology-graph 本体平台前后端代码实现与工程结构讲解

> **读者**：第一次接触这两个仓的同学（不需要懂 Rust / Web Component，文中术语出现处都会解释）。
> **读完你能回答**：这两个仓是干什么的？代码放在哪？一次点击 / 一个请求是怎么从页面走到数据库再回来的？想加功能该改哪个文件？
> **写作日期**：2026-09-18，代码以当日 main 分支为准（cmx-ontology `5614a85`；cmx-ontology-graph `f0dd0a2`）。行号引用（如 `def.rs:181`）可直接点击跳转。

---

## 目录

1. [什么是"本体"？这两个仓各干什么](#1)
2. [全景图：前后端怎么分工](#2)
3. [后端 cmx-ontology：工程结构（一芯多壳 + 组合根模块化）](#3)
4. [后端：直改 live 架构与数据模型](#4)
5. [后端：HTTP 层与一次请求的生命周期](#5)
6. [前端 cmx-ontology-graph：双组件体系](#6)
7. [前端：从数据到画面的流水线](#7)
8. [前端：交互是怎么接起来的](#8)
9. [前后端如何对接（契约 + 交付链 + 四页面）](#9)
10. [怎么跑起来（快速上手）](#10)
11. [术语表](#11)
12. [FAQ](#12)

---

<a id="1"></a>
## 1. 什么是"本体"？这两个仓各干什么

### 1.1 用大白话解释"本体（Ontology）"

企业系统里到处是"概念"：客户、订单、产品、合同……以及它们之间的关系（客户**下**订单、订单**包含**订单行）。**本体就是把企业的这些概念和关系，变成机器可读、可查询、可操作的一张"概念地图"**。

我们的本体平台对标的是 **Palantir Foundry Ontology**（业界最有名的企业本体产品），把概念地图拆成七类元素：

| 元素 | 大白话 | 例子 |
| --- | --- | --- |
| 对象类型 Object Type | 一类"东西"的模板（有哪些字段、主键是谁） | `Customer`（客户） |
| 属性 Property | 对象类型的字段 | 客户的 `name`、`region` |
| 关系类型 Link Type | 两类东西之间怎么连，连几对几（含落存储方式 backing） | 客户→订单 `1:N`，外键落在订单端 |
| 接口 Interface | 一组公共能力的"横切标签"，多个对象类型可以实现它 | `Locatable`（有地址的东西） |
| 共享属性 Shared Property | 全公司统一的标准化字段定义 | `currencyCode` |
| 动作类型 Action Type | 对数据的一次"带校验的业务操作" | `reassignOrder`（转派订单：先校验，再改数，再通知流程） |
| 函数 Function | 一段可复用的计算逻辑 | `delayRisk`（算延误风险分） |

在这个"语义层"之上，20260917 起平台又长出了三层**治理/消费设施**：**场景（Scene View）**——把底座元素按业务视角组合成一张可编辑的画布；**生命周期 + 修订历史**——每个定义有 experimental/active/deprecated 三态和完整的改动时间线；**检查点与命名发布**——live 定义随时可存档、对比、回滚。

> ⚠️ **它不是 RDF/OWL**。RDF/OWL 是 W3C 的语义网标准（基于 XML），面向学术推理和知识图谱工具链；我们的体系是 JSON + PostgreSQL 的工程化实现，语义上学 Palantir，工具链上与 Protégé / SPARQL 无关。已全局检索确认：两个仓零 RDF/OWL/SPARQL 代码。

### 1.2 两个仓的分工

| 仓 | 语言 | 一句话定位 |
| --- | --- | --- |
| `backend/cmx-ontology` | Rust（axum 微服务，端口 **:8097**） | 本体平台的"大脑 + 仓库"：存定义、治理状态、执行动作、算函数、查对象、集成外部数据 |
| `frontend/cmx-ontology-graph` | TypeScript（Web Component，零框架） | 画这张"概念地图"的**可视化画布组件**：现役 `<cmx-ontology-canvas>`（SVG）+ 性能裕量版 `<cmx-ontology-canvas2d>`（Canvas 2D 位图） |

它们**不直接依赖**：前端是通用组件，后端是通用服务，中间靠一份 JSON 契约（见 §9）粘合。真正把两者拼在一起的是本体平台自己的四个前端"薄壳页面"（designer / explorer / workshop / studio，见 §9.3）。

---

<a id="2"></a>
## 2. 全景图：前后端怎么分工

```
浏览器
 ┌────────────────────────────────────────────────────────────┐
 │  四个 native 薄壳页（designer / explorer / workshop / studio）│
 │   ┌──────────────────────────────────────────────┐         │
 │   │ <cmx-ontology-canvas>  ← 来自 cmx-ontology-graph 仓 │    │
 │   │  只管：画布/布局/拖拽/连线/分域折叠，发事件       │         │
 │   └──────────────┬───────────────────────────────┘          │
 │  宿主壳负责：Inspector 表单、场景/版本/流转按钮（领域逻辑） │
 └────────────────┼───────────────────────────────────────────┘
                  │ fetch /api/onto/v1/*  (JSON, camelCase)
                  ▼
 ┌────────────────────────────────────────────────────────────┐
 │ cmx-onto-server :8097（壳：组合根装配，main.rs 249 行）      │
 │  → cmx-onto-app（芯：路由 + handler + 治理 + 中间件）        │
 │      │ OntologyStore / ObjectStore 契约（trait，驱动无关）   │
 │      ▼                                                      │
 │  cmx-onto-store-pg（PG 实现：save/revision/snapshot/view…） │
 │      │                                                      │
 │      ▼                                                      │
 │  PostgreSQL：om_* 定义表 + oo_*/ol_* 对象实例表              │
 └────────────────────────────────────────────────────────────┘
        │ Outbox 定时投递（10s）          ▲ SSE /events（订阅推送）
        ▼                                 │
   flowengine :8091 / report :8092 / webhook / MDM push 回调
```

分工哲学一句话：**组件管"画和手势"，宿主壳管"业务"，后端管"真理"**。画布组件刻意不理解"什么是客户"——它只认 `nodes/edges`；字段校验、状态流转、发布门禁这些领域逻辑都在宿主壳（designer.js / studio）和后端。

---

<a id="3"></a>
## 3. 后端 cmx-ontology：工程结构（一芯多壳 + 组合根模块化）

### 3.1 目录树

```
backend/cmx-ontology/
├── Cargo.toml                  # workspace 清单（管下面 4 个 crate）
├── onto-server.toml(.example)  # 配置文件（端口 / 数据库 / 认证）
├── onto-server-dev.toml 等     # 开发/测试环境配置（连真机开发库）
├── onto.sh                     # 启动脚本
├── qa-backend.sh / qa-object.sh  # 仓根 QA 脚本
├── docs/                       # 仓内设计文档（含 assets 演示数据）
├── test/e2e/（21 个）/ test/fe/（19 个）  # e2e 与前端 UI 回归
└── crates/
    ├── cmx-onto-model/         # 【芯·内核】类型 + 存储契约 + 纯逻辑（零 IO）
    ├── cmx-onto-store-pg/      # 存储实现（PostgreSQL，14 个文件）
    ├── cmx-onto-app/           # 【芯·应用】HTTP 路由 + handler + 治理 + 中间件
    └── cmx-onto-server/        # 【壳】独立启动进程（main.rs 只有 249 行）
```

### 3.2 什么是"一芯多壳"？

这是 CMX 后端的统一骨架（flowengine / rulesengine 同构）：

- **芯（core）** = `cmx-onto-model` + `cmx-onto-app`：装着全部业务逻辑，但**不绑定任何具体部署形态**。handler 不绑 axum 的 `State` 提取器，所以路由函数 `onto_routes::<S>()` 对任意 state 泛型成立（`cmx-onto-app/src/lib.rs:75`）。
- **壳（shell）** = `cmx-onto-server`：只是组合根，把芯装配成独立微服务。
- 好处：将来想把本体功能**内嵌**进门户主应用（:8080），不需要复制代码——计划中的平台壳 `cmx-onto-api`（放 cmx-container）直接调 `onto_routes::<CmxAppState>()` 即可（见 `cmx-onto-app/src/lib.rs:1-8` 的注释）。

**20260915 起组合根模块化**：路由装配走 `cmx-engine-kit` 的 `ModuleRoutes/ModuleSet` 契约——`module.rs` 把同一张路由表适配成两个模块（`OntoV1Module` = `/onto/v1` 正式契约、`OntoCoreModule` = `/onto` 旧前缀兼容），bin 侧 `ModuleSet::new().with(...).fold()` 组合，**带去重守卫**防路径冲突；并配了**路由契约测试**（`main.rs:182` 起用 OPTIONS 探测守护挂载清单，改造即零回归）。

### 3.3 四个 crate 各装什么

#### ① `cmx-onto-model` —— 内核（"什么是本体"，约 5750 行）

| 文件 | 内容 |
| --- | --- |
| `def.rs`（911 行） | 七类元素的定义结构体：`ObjectTypeDef` / `LinkTypeDef` / `InterfaceDef` / `SharedPropertyTypeDef` / `ActionTypeDef` / `FunctionDef` + 各自的 `validate()` 结构校验；`TypeStatus` 三态 + `DeprecationMeta` 弃用元数据；**关系 backing 强类型解析**（`fk`/`joinTable`/`intermediary` 三种页面形状 → `LinkBacking` 枚举，`def.rs:351`）；**接口契约校验** `validate_implements`（`def.rs:276`）与**关系状态兼容矩阵** `allowed_link_status`（`def.rs:66`） |
| `action.rs`（1181 行） | O4 动作引擎纯逻辑：参数替换（`$name`）→ **五来源值映射**（param/static/currentUser/currentTime/paramProperty）→ 编辑集解析（Create/Modify/Upsert/Delete Object + Add/Remove Link）→ 组合序列校验 |
| `view.rs` | 场景视图定义 `SceneViewDef`：auto（域派生，成员读时现算）/ manual（成员物化）两态 + `links` 白名单 + 校验（auto 必须带 `auto:` 前缀且不物化成员） |
| `snapshot.rs`（733 行） | 存档/回滚纯函数：快照**指纹**（rev = xxh64，覆盖七类元素 + views 语义字段，**排除 layout 与乐观锁 version**，数组顺序不敏感）、元素级 diff、派生删除集、回滚校验 |
| `objectset.rs` | 对象集代数（Base/Filter/SearchAround/Union/Intersect/Subtract/Static）+ 谓词树 + 聚合（Count/GroupCount/GroupSum）的内存语义 |
| `feel.rs` / `function.rs` / `rhai_engine.rs` | FEEL 表达式求值器 + 函数求值（FEEL / Rhai 运行时） |
| `authz.rs` / `funnel.rs` / `import.rs` / `osdk.rs` | 动态安全纯逻辑 / 数据集成映射与校验报告 / DOC-DCT 反向导入 / TypeScript SDK 生成 |
| `store.rs` / `object_store.rs` | `OntologyStore` / `ObjectStore` 两个 **trait**——存储契约（不关心底下是 PG 还是内存） |
| `lib.rs` | 模块出口 + 大量单元测试（校验规则、序列化契约） |

> 这个 crate 的注释第一行写着"语义中立内核，零 DB/infra 依赖"（`def.rs:1`）——它连数据库都不认识，所以可以随心所欲地单测。

#### ② `cmx-onto-store-pg` —— 存储实现（"本体存在哪"，约 7100 行）

把两个 trait 用 `tokio-postgres` 落到 PostgreSQL。比 9 月初多了一倍，因为治理设施各自独立成文件：

| 文件 | 内容 |
| --- | --- |
| `ddl.rs`（506 行） | 全部建表 DDL（幂等 `IF NOT EXISTS`），见 §4.3 |
| `save_store.rs`（680 行） | **统一保存管道**：七类元素 `save_*_with_revision` ——乐观锁条件更新 + 写修订 + 墓碑 + SSE，一套代码六类复用 |
| `revision_store.rs`（676 行） | 修订历史（`om_revision`）：时间线 / 详情 / git revert 式回滚 / 墓碑 / 级联写结构 `CascadeWrite` |
| `snapshot_store.rs`（1138 行） | 检查点（`om_version`）：指纹存档 + 去重、tag 发布、diff、整体恢复（单事务应用 + 大规模删除护栏） |
| `view_store.rs`（517 行） | 场景表（`om_view`）CRUD：upsert 乐观锁 / 布局单列 LWW / 域派生虚拟条目 / 场景引用级联清理 |
| `store.rs`（1193 行） | `OntologyStore` 的 PG 主实现：六类定义表 CRUD + manifest（含状态分层过滤）+ 生命周期 `apply_transition` + 维护角色表 |
| `object_store.rs`（579 行） | 对象实例存储：**每个对象类型一张物理表**（`oo_<类型名>`）+ 关系边表 `ol_edge` |
| `link_resolver.rs` | 关系端点解析：FK/连接表/中间对象 backing 的 Search-Around 编译（Edge 之外的物理布局直查） |
| `compile.rs`（566 行） | 把对象集代数**编译成一条 SQL**（`props->>'字段名'` 抽取 + 参数绑定 `$N` 防注入 + searchAround JOIN） |
| `action_exec.rs`（648 行） | 动作执行的事务落地：一个事务里写回 + 审计 + Outbox（含 `apply_batch` 批量） |
| `funnel_store.rs` / `policy_store.rs` | 数据集成映射表 / 安全策略表的实现 |

#### ③ `cmx-onto-app` —— 应用层（"HTTP 接口长什么样"，约 6800 行）

| 文件 | 内容 |
| --- | --- |
| `lib.rs`（260 行） | `onto_routes_inner::<S>()` 全量路由表（84 端点，见 §5.1）+ 模块出口 |
| `module.rs` | 路由模块适配器（`OntoV1Module` / `OntoCoreModule`，接入 `ModuleSet` 契约） |
| `handlers.rs`（1024 行） | 六类元素 CRUD + manifest + versions（模式统一：**先校验，后落库**；save 剥离 status；active 保护；引用检查；删除前自动存档） |
| `view_handlers.rs`（723 行） | 场景 CRUD + 布局 + **`GET /graph` 服务端组装画布 spec**（成员对象/接口/边/跨场景角标/悬空告警一次到位）+ 对象类型分页目录 |
| `action_handlers.rs`（938 行） | 动作 execute / dry-run / execute-batch / check-permission / 审计 / Outbox / flow·report 代理 / 模板 / **定时投递线程** |
| `lifecycle.rs`（373 行） | `POST /lifecycle/transition`：兼容矩阵判定 + 机械级联 + dryRun 预览 + 单事务落库（§11 生命周期的入口） |
| `revision_handlers.rs` / `archive_handlers.rs` | 修订时间线/详情/回滚；检查点/版本 diff/恢复/发布标记/`me/roles` + **维护角色守卫 `require_maintainer`** |
| `object_handlers.rs`（374 行） | 对象实例读写 / 批量 / Search-Around（方向自动解析）/ 对象集加载与聚合（带 PEP 硬门 + 场景校验） |
| `pep.rs` / `filter.rs` | **PEP**（读侧行残差集 + 列脱敏计划；写侧 deny_actions）；**状态分层过滤器**（include 解析 + 场景成员范围校验） |
| `function_handlers.rs` / `function_runtime.rs` | 函数求值端点 |
| `policy_handlers.rs` / `funnel_handlers.rs` / `import_handlers.rs` / `osdk_handlers.rs` | 策略 CRUD + 带安全加载 / 漏斗同步 + **MDM push 订阅入口** / DOC-DCT 导入 / SDK 生成 |
| `outbound.rs`（296 行） | 出站投递：webhook 真发 HTTP（host 白名单 SSRF 护栏）+ 调 flowengine v1 起实例 + 触发报表计算 |
| `flow_callback_handlers.rs` | 流程审批结果回调（`instance.completed` → 按 businessKey 回写对象状态，幂等） |
| `events.rs` | SSE 实时变更流（进程内 broadcast，按租户过滤） |
| `engine.rs` / `tenancy.rs` / `tenant.rs` / `auth.rs` / `resp.rs` | 存储入口 + 启动预热 / 多租户库路由 / 当前用户与租户 / 认证中间件 / 统一响应壳 `ApiResp` |
| `dashboard.rs`（243 行） | 根路径 `/` 的**建模控制台**（自包含 HTML 单页，vanilla JS，双主题） |
| `openapi.rs` / `action_templates.rs` / `stats.rs` | OpenAPI JSON + Swagger UI / 内置动作模板 / 统计端点 |

#### ④ `cmx-onto-server` —— 壳（"怎么启动"）

`main.rs` 仅 249 行，干四件事：

1. 填一个 `ServiceSpec`（服务名、TOY 字符画 banner、组合根路由）交给通用骨架 `cmx-web-chassis::run()`；
2. 注册**三个启动钩子**（`main.rs:75` 起）：①校验并注册 `[[databases]]` 数据源（要求 db_id=`onto_pg`，连不上启动失败 fail-fast）；②建表预热 + 存量回填（`warm_store()` 建表 + 动作 targets 列回填 + 场景 links 回填；`warm_object_store()` 建 `ol_edge`）；③**拉起 Outbox 定时投递**（动作副作用出站自动挡）；
3. 挂中间件：监控遥测 `observe`（内）→ 认证 `auth_middleware`（外）；openapi/docs/根控制台/native-pages 挂在认证之外；
4. 技术监控（`/_mon`）：注入身份读取器与服务拓扑。

> 长驻任务**只有 Outbox 定时投递**（间隔缺省 10s，`ONTO_OUTBOUND=off` 全局熄火；`SELECT … FOR UPDATE SKIP LOCKED` 认领，多实例部署安全）。本体建模本身纯请求驱动，无 poller。

---

<a id="4"></a>
## 4. 后端：直改 live 架构与数据模型

### 4.1 先讲清 20260917 的架构转向：直改 live

旧架构是"草稿 → 发布"两态：平时改草稿，点发布才生成全量快照。**现在改成了"直改 live"**：

- `om_*` 定义表就是**已发布真源**（消费方随时读，读取路径零改动）；
- 编辑直接写 live，**"存档"= 用户主动把 live 打成 `om_version` 检查点**（不可变快照，带内容指纹 rev）；
- **"发布"= 给检查点起名**（tag + release_note，带 experimental/deprecated 警告门禁）；
- **"回滚"= 把历史快照整体恢复回 live**（过结构校验 + 大规模删除护栏，单事务应用）；
- 每一次保存 / 流转 / 回滚 / 删除都**追加一条修订记录**（`om_revision`，历史只增不改），删除走"墓碑"（可查可恢复）。

一句话类比：**以前是 git 的暂存区+commit，现在直接在 main 上干活，随时打 tag、可 revert、每次改动都有 log。**

### 4.2 状态生命周期（Palantir 式软治理）

- 每类资源有 `status`：`experimental`（试验）→ `active`（激活，可被高效查询）→ `deprecated`（废弃）；
- **save 端点一律剥离 status**（带了只回 warnings）——状态变更唯一入口是 `POST /lifecycle/transition`，防止旁路篡改；
- → deprecated 必填弃用元数据（`reason` + `sunsetAt` 日期 + 可选 `replacementApiName`）；离开 deprecated 四列清空；
- **active 保护**：active 资源不可删除、不可改主键（要先降级）；
- **兼容矩阵**（`allowed_link_status`）：关系的合法状态由两端对象状态决定（任一端 deprecated → 关系只能 deprecated；任一端 experimental → 只能 experimental）；对象流转时**机械级联**把相关关系对齐到矩阵允许的唯一状态，系统永不产生违规态；
- 场景视图也是第七类"资源"，同样有状态、修订、墓碑。

### 4.3 PG 表设计（`ddl.rs`，全部幂等 DDL）

**定义与治理侧**：

| 表 | 装什么 | 特殊设计 |
| --- | --- | --- |
| `om_object_type` / `om_link_type` / `om_interface` / `om_shared_property` / `om_action_type` / `om_function` | 六类元素定义 | 复杂部分全塞 **JSONB 列**（properties / backing / parameters / logic…）——改结构不用改表；`om_action_type` 另有 `target_object_types` **GIN 物化列**（保存期从 parameters+logic 派生，按类型查动作）；五类表已补 `version` 乐观锁列 |
| `om_view` | 场景视图 | members/layout JSONB；`source` 列分 auto/manual；布局单列 LWW 直写 |
| `om_version` | 存档检查点 | 不可变；`snapshot` JSONB 存全量清单 + `rev` 指纹 + `tag`/`release_note`（发布标记）；`archived_at` 索引 |
| `om_revision` | 修订历史 | 只追加；按 `(resource_kind, api_name, revision)` 索引；删除 = 墓碑行 |
| `om_maintainer` | 维护角色白名单 | 空表 = 开放；有行按 用户/展示名/角色 三路匹配 |
| `om_policy` / `om_source_mapping` | 安全策略 / 集成映射 | 见 §5.3 与接口文档 §17/§18 |
| `oe_action_log` / `oe_outbox` | 动作审计 / 副作用发件箱 | Outbox 表按 `(status, id)` 索引供 SKIP LOCKED 认领 |
| `oo_quarantine` | 集成隔离区 | 违规源行留痕 |

两条硬约束（对齐全后端规范）：**禁外键**（用索引替代，微服务各自独立演进）；**DDL 幂等**（启动时可重复执行）。

**实例侧（对象数据）**：

- **每个对象类型一张物理表**（`oo_<apiName>`）：主键 + 标题列 + `props JSONB`（装全部属性）+ 审计列。表骨架固定查询定位快，属性走 JSONB 则"类型演进零 DDL"（加字段不用 `ALTER TABLE`）；
- **关系实例统一一张边表 `ol_edge`**：`link_api` + A 端 pk + B 端 pk + `props JSONB`。**只有 Edge backing 的关系落这张表**——FK 关系直接查外键属性值，连接表/中间对象 backing 直查对应物理布局（`link_resolver.rs` 负责编译），杜绝"边写了但查询走另一条路"的双轨不一致。

### 4.4 多租户怎么做的

**库即租户边界**：single 模式全用默认库 `onto_pg`；multi 模式每个租户一个库（`onto_<tenant>`），所以表内**没有 tenant 列**。handler 里一句 `let tenant = current_tenant();`（从请求头解析）→ `store()` 按租户派生 db_id（`engine.rs:12`），`PgOntologyStore` 只是 db_id 的轻包装，构造零成本。

---

<a id="5"></a>
## 5. 后端：HTTP 层与一次请求的生命周期

### 5.1 路由总览（`cmx-onto-app/src/lib.rs:75`）

正式前缀 `/api/onto/v1`（旧前缀 `/api/onto` 同表双挂载）。**84 个端点**按功能分组：

| 分组 | 端点示例 | 说明 |
| --- | --- | --- |
| 六类元素 CRUD | `GET/POST /object-types`、`POST /object-types/batch`、`GET/DELETE /object-types/{api}` … | 建模核心（+validate / 共享属性 batch） |
| 场景视图 | `GET/POST /views`、`POST /views/remove|layout`、`GET /graph?view=` | 工作室画布一条到位 |
| 清单/存档/版本 | `GET /manifest`、`POST /snapshots`、`GET /versions[/diff|/{v}]`、`POST /versions/restore`、`POST /releases[remove]`、`GET /me/roles` | 直改 live 的治理闭环 |
| 生命周期/修订 | `POST /lifecycle/transition`、`GET /revisions[/detail]`、`POST /revisions/revert` | 软治理 + 时间线 |
| 对象实例 | `POST /objects/{type}[batch|/{pk}/modify]`、`GET /objects/{type}/{pk}/links/{link}`、`POST/DELETE /links` | 写 / 改 / Search-Around |
| 对象集 | `POST /object-sets/load|aggregate` | 过滤查询编译成一条 SQL（PEP 硬门） |
| 动作 | `POST /action-types/{api}/execute|dry-run`、`POST /action-types/execute-batch|check-permission`、`GET /action-logs`、`/action-outbox*` | 执行 / 试算 / 批量 / 预检 / 审计 |
| 函数 | `POST /functions/{api}/evaluate` | 求值 |
| 安全 | `GET/POST/DELETE /policies`、`POST /secure/object-sets/load` | 策略 + 显式带安全查询 |
| 集成 | `POST /funnel/sync/{type}`、`POST /funnel/push`、`GET /funnel/quarantine`、`POST /import/doc|dct`、`POST /flow-callback` | 漏斗 / 导入 / 审批回写 |
| SDK/工具 | `GET /osdk/typescript`、`GET /stats`、`GET /events`(SSE，鉴权内) | 代码生成 / 监控 / 实时流 |

> 注意路径风格：`{apiName}` 这类**路径参数只出现在既有接口**；按工作区新规，新增接口（如 execute-batch、check-permission、views/remove）一律固定资源段 + query/body。

### 5.2 一次请求的生命周期：以"保存对象类型"为例

你在设计工作台点了"保存"按钮，背后发生了什么（对应 `handlers.rs:76`）：

```
① 浏览器   POST /api/onto/v1/object-types
           body: { "apiName":"Customer", "primaryKey":"id", "properties":[…], "version":3 }

② 认证中间件 auth.rs
           校验 Bearer token / X-API-Key → 把当前用户、租户塞进请求上下文

③ handler  save_object_type(body)
           ├─ stripped_warnings()        ← body 里带了 status/deprecation？剥离并记 warnings
           │                               （状态变更唯一入口是 /lifecycle/transition）
           ├─ def.validate()             ← 内核纯结构校验：apiName 合法？属性重名？
           │                               主键/标题属性存在于 properties？不过 → 400
           ├─ validate_object_implements ← implements 声明的接口逐个装载，
           │                               校验共享属性契约（类型必须完全匹配）
           ├─ active 保护                ← 已是 active 且改了主键 → 409
           └─ save_object_with_revision  ← 乐观锁：version>0 走原子条件更新
                                           （你拿 version=3，库里已是 4 → 409）；
                                           成功 = 更新 om_object_type + 追加一条 om_revision
                                           + SSE 广播 resource-changed

④ 响应     { "code":"ok", "data": { "saved":true, "version":4, "warnings":[] } }
           ← 前端拿响应里的 version 刷新自己的基线，下次保存才不会 409
```

所有 save handler 都是同一个模式：**解析 → 剥离 status → 结构校验（fail fast）→ 领域校验（接口契约 / 兼容矩阵）→ 乐观锁落库 + 修订 + SSE → 错误翻译（StoreError → HTTP 语义码）→ 统一 ApiResp 壳**。而且 handler 不绑定 axum 的 `State` 提取器，所以路由函数是泛型的（这就是"一芯多壳"的技术基础）。

### 5.3 三个值得记住的工程机制

- **Outbox 模式 + 自动投递**：执行动作时，"改数据"和"发副作用事件"在**同一个事务**里落库（事件先写 `oe_outbox`，status=pending）；服务内置定时投递线程（默认 10s 一轮，SKIP LOCKED 认领）按 kind 分派——SSE / 函数 / webhook（host 白名单）/ 起流程实例 / 触发报表。`ONTO_OUTBOUND=off` 一键熄火，多实例部署安全。
- **读侧 PEP 硬门**：`/object-sets/load`、aggregate、Search-Around 全部先过 `pep::enforce_read`——把主体策略的行级条件**折进 SQL**（看不见的行直接查不出来，而不是查出来再过滤），命中 `denyMarkings` 的列值在返回前抹掉；写侧动作执行按编辑涉及的对象类型查 `deny_actions`（deny 即 403）。
- **修订与检查点**：每次保存追加一条 `om_revision`（谁、何时、从什么改成什么）；删除走墓碑可恢复；`POST /snapshots` 打检查点（rev 指纹相同自动去重）；回滚 = 快照整体恢复回 live（先过校验 + 大规模删除护栏）。高危删除（删对象/关系类型）前还会**自动存档**一次，兜底可撤销。

---

<a id="6"></a>
## 6. 前端 cmx-ontology-graph：双组件体系

### 6.1 先讲 2026-09 的架构演变

9 月 12 日前只有一个组件 `<cmx-ontology-graph>`。9 月的连续改造后，**旧组件已整体删除**（9-17 提交），现在是**双组件体系**：

| 组件 | 渲染技术 | 定位 | 交付 |
| --- | --- | --- | --- |
| `<cmx-ontology-canvas>` | **SVG DOM** | 生产现役（designer / studio 都用它），支持 CSS 主题变量、悬浮 title、易做无障碍 | vendor 已发布（esm 约 127KB） |
| `<cmx-ontology-canvas2d>` | **Canvas 2D 位图** | 性能裕量版（千级节点基准更省内存/重绘），契约与 SVG 版**逐项一致** | 仅构建产物，暂不发布 vendor |

两组件**共享 model / layout / render / interaction 四层**，属性（14 个）/ 事件（11 种）/ 方法 / spec 契约完全一致，由仓根 AGENTS.md「双组件同步纪律」约束——改契约必须双端同改。节点样式有两档：`node-style="circle"`（默认圆形）与 `"soft"`（软底卡）；统一主色 `--og-node-color` 动态派生选中色；**鸦爪基数符号已移除**，改为文本角标（1:1 / 1:N / N:1 / N:M）。

### 6.2 两个名词

- **Web Component**：浏览器原生的"自定义 HTML 标签"技术。写一个 `<cmx-ontology-canvas>` 标签，浏览器就把它渲染成本体画布——**不需要 React/Vue**，任何页面扔个 `<script>` 就能用。内部用 **Shadow DOM**（影子树）把样式与外界隔离。
- **零运行时依赖**：`package.json` 的 dependencies 是空的，devDependencies 仅 typescript / esbuild / vitest / happy-dom。

### 6.3 目录树（src 合计约 6014 行 TS + test 1242 行）

```
frontend/cmx-ontology-graph/
├── src/
│   ├── index.ts               # 公共出口：import 本文件 = 自动注册 <cmx-ontology-canvas>
│   ├── canvas/                # ① SVG 版组件（生产现役，2225 行）
│   │   ├── element.ts        #    1345 行：<cmx-ontology-canvas> 元素层——shadow DOM、spec 适配、
│   │   │                     #    拖动/拉线/分域状态机、撤销重做、视口剔除、rAF 合帧 renderEpoch
│   │   ├── svg.ts            #    816 行：SVG 渲染（唯一渲染真源）：circle/soft 双形态、
│   │   │                     #    统一主色、浮动锚点贝塞尔连线
│   │   ├── spaceGrid.ts      #    52 行：uniform grid 空间索引（视口剔除，格 512px）
│   │   └── index.ts
│   ├── canvas2d/              # ② Canvas 2D 版组件（性能裕量版，1700 行）
│   │   ├── element.ts        #    951 行：契约与 SVG 版一一对应；单 canvas dirty+rAF、几何命中
│   │   └── renderer.ts       #    737 行：纯绘制层（readTheme 读 --sap*/--og-* 变量派生同一套色）
│   ├── model/                 # ③ 共享数据层
│   │   ├── types.ts           #    serde 契约类型（与后端 cmx-onto-model 对齐）
│   │   └── OntologyModel.ts   #    可变模型：增删改节点/边/属性/布线（纯数据操作，不碰 DOM）
│   ├── layout/                # ④ 共享布局层（全是纯函数，可单测）
│   │   ├── layout.ts          #    确定性网格布局 + circle/soft 尺寸常量（非 DAG，不做拓扑分层）
│   │   ├── groupLayout.ts     #    按 DAM 域/应用/模块分域嵌套折叠布局（默认收起）
│   │   └── route.ts           #    正交直角布线（A* 避让 + 跳线射线；手动布线用）
│   ├── render/                # ⑤ 共享渲染基础
│   │   ├── svg.ts             #    graphCss / --og-* 主题令牌样式表（唯一真源）
│   │   ├── annotations.ts     #    基数文本角标（1:1/1:N/N:1/N:M）+ 节点/边 title 纯函数
│   │   └── legend.ts          #    图例浮层（sessionStorage 折叠记忆，不进 def）
│   └── interaction/           # ⑥ 共享交互层
│       ├── pointer.ts         #    指针交互几何/判定（与 @cmx/decision-graph 同构）
│       └── viewTransform.ts   #    屏幕↔内容坐标纯函数换算
├── demo/                      # canvas-demo.html（66 条自检，?selfcheck=1 触发）
│                             # canvas2d-demo.html（6 条）+ perf.html 性能基准
├── docs/                      # canvas-component.md（双组件共用手册十章）+
│                             # components-comparison.md（选型）+ performance-notes.md（千节点基准）
├── build.sh                   # tsc 类型检查 + esbuild 打 4 个产物（canvas/canvas2d × esm/iife）
├── sync-component.sh          # 交付：仅同步 SVG 版 esm → 后端资产 vendor 目录
└── package.json               # name=@cmx/ontology-graph，dependencies 为空
```

### 6.4 分层思想（为什么这么拆）

共享四层从下往上依赖，**下层不知道上层存在**；两个组件目录只是"元素层"的两份实现：

```
canvas/element.ts（SVG 版总指挥）   canvas2d/element.ts（Canvas 版总指挥）
  ↑ 调用（共享下面四层，契约一致）
interaction（手势几何）   render（主题令牌/角标/图例）
  ↑                          ↑
layout（数据 → 坐标：网格/分域/布线）
  ↑
model（JSON 契约 + 纯数据操作）
```

好处：`model` / `layout` / `route` / `viewTransform` 是纯函数，vitest 直接单测（98 个用例，7 个测试文件）；渲染只是"把状态变成字符串/绘制指令"，出 bug 一眼能定位是哪层。共享层只此一份，双组件不会漂移。

---

<a id="7"></a>
## 7. 前端：从数据到画面的流水线

### 7.1 数据入口：一份 spec

宿主页面把整张图作为一个 JSON（叫 **def / spec**）喂给组件，两种等价方式：

```html
<cmx-ontology-canvas data-spec='{"nodes":[…],"edges":[…]}'></cmx-ontology-canvas>
```
```js
el.setSpec(def);        // 或 el.getSpec() 取回
```

spec 结构就是后端契约的图形投影（`model/types.ts`，与后端 serde 结构逐字段对齐）：

```jsonc
{
  "nodes": [
    { "id": "Customer",              // = apiName
      "kind": "object",              // object | interface（接口画成胶囊）
      "displayName": "客户", "status": "experimental",
      "properties": [{ "apiName": "id", "baseType": "long", "isPrimaryKey": true,
                        "children": […], "isLevel": false }],   // children 支持层块嵌套
      "implements": ["Locatable"],
      "groupPath": ["crm", "sales"], // DAM 分域（组盒折叠用）
      "projection": "full",          // full 全卡 | ref 引用胶囊（跨场景引用）
      "externalCount": 2,            // +N 跨场景关系角标（studio /graph 接口供给）
      "externalPeers": [{ "apiName": "…", "peer": "…" }] }
  ],
  "edges": [
    { "apiName": "customerPlacesOrder", "source": "Customer", "target": "Order",
      "cardinality": "oneToMany", "roleA": "下单人", "roleB": "订单列表",
      "sourceProperty": "customerId", "targetProperty": "orderId",  // 缺省回退对端主键
      "backing": "fk" }              // fk | joinTable | intermediary
  ],
  "_layout":         { "Customer": {"x": 300, "y": 120}, "#g:crm": {…} },  // 组件私有：拖拽坐标
  "_edgeRoutes":     { … },                        // 组件私有：手动布线折点
  "_groupCollapsed": { … }                         // 组件私有：分域折叠态（缺省视为收起）
}
```

> 关键设计：`_` 开头的三个字段是**组件私有视图态**（你拖到哪、线怎么拐、分组收没收），随 `spec-change` 事件流转给宿主一起存盘（后端存进 `om_view.layout`），但后端"忽略未知字段"——前端视图个性化不会污染本体定义；且**存档指纹排除 layout**（纯拖动不产生新检查点）。

### 7.2 一次完整渲染（paint）走过五层

```
setSpec(def)
  → OntologyModel.setDef()      ① 存好数据，顺手把 implements 派生成虚线边
  → layout(def.nodes)           ② 没拖过位置的节点按"零遮挡网格"排位
                                  （拖过位置的以 _layout 为准，钉在原地）
  → groupLayout()               ②' 带 groupPath 且 ≥2 条不同路径 → 自动切分域折叠视图
                                  （组盒默认收起；跨容器边归约聚合）
  → 边几何 + 浮动锚点           ③ 现役画布默认贝塞尔轻弧连线（浮动锚点贴轮廓零间隙）；
                                  手动布线/旧路径走 route.ts 正交直角 A*
  → renderSvg(state)            ④ 生成整幅 SVG：对象 = 圆形/软底卡（主色 + 属性行：
                                  ◇主键 ⌾标题 *必填 ⚡索引 + 语义徽标；逐层 +N more 折叠）
                                  接口 = «interface» 胶囊 + 虚线挂接；基数 = 文本角标
  → shadowRoot.innerHTML = …    ⑤ 塞进 Shadow DOM；超过阈值（300 节点）启用视口剔除——
                                  空间索引只画看得见的，拖动落定才重建
```

Canvas 2D 版流程相同，只是第④⑤步换成"单 canvas + dirty 标记 + rAF 重绘"，主题色从 CSS 变量读取后经 mixRgb 派生成同一套色板。

---

<a id="8"></a>
## 8. 前端：交互是怎么接起来的

### 8.1 组件对外的三面接口（两组件同契约）

**属性（14 个）**：`data-spec`、`node-style`(circle/soft)、`node-color`、`node-selected-color`、`no-sub-label`、`edge-color`、`edge-selected-color`、`show-props`(默认关)、`canvas-bg`(dots/chess/lines/plain)、`handle-style`(ring/plus)、`readonly`、`no-legend`、`no-zoom-controls`、`hover-title`(默认关)。

**事件（11 种，全部 bubbles+composed；组件不落数据，一律交宿主 setSpec 回写）**：

| 事件 | 什么时候发 | 宿主拿到后干什么 |
| --- | --- | --- |
| `type-select` / `edge-select` | 点选卡片/关系线 | 右侧 Inspector 渲染强类型编辑表单 |
| `link-add` | 拉线对象→对象整卡吸附松手 | 弹"关系速建气泡"补 apiName/基数/锚点，再调 `addLink()` 回写 |
| `implements-request` | 拉线对象→接口吸附松手 | 给对象 implements 追加该接口 |
| `implements-remove-request` | Delete 删实现虚线 | 摘除 implements |
| `edge-delete-request` | Delete 删普通关系边 | 删关系类型 |
| `connect-rejected` | 不支持连线（接口→接口等） | 弹错误提示 |
| `spec-change` | 拖卡落定 / autoLayout / fitView 重排 / 分组编排 | 拿新 spec 存盘 |
| `badge-click` | 点 `+N` 跨场景角标 | 弹补引对端成员面板 |
| `canvas-dblclick` | 双击画布空白 | 宿主"新建对象类型"入口 |
| `history-change` | 撤销栈变化 | 刷新撤销/重做按钮态 |

**方法**：数据 `setSpec/getSpec/getModel/refresh`；选中 `selectNode/selectEdge/restoreSelection/restoreEdgeSelection/revealNode/focusNode`；视图 `zoomIn/zoomOut/zoomReset/zoomAt/panBy/fitView/screenToContent/contentToScreen`；布局编排 `autoLayout/setAllGroups/setAllLevels/toggleLevelFold/toggleMoreOpen/toggleGroupWithGuard`；撤销 `undo/redo/canUndo/canRedo`。

### 8.2 手势 → 语义的"回调反转"设计

交互层只监听原始 pointer 事件，做坐标换算（除以缩放倍数）、判定"这是拖卡还是拉线还是平移"，然后**通过回调把语义动作交还给元素层**：

```ts
// 元素层消费回调（示意）
onNodeDrag: (id, x, y) => { model.setLayoutHint(id, x, y); this.schedulePaint(); },
onConnect:  (src, tgt) => this.requestConnect(src, tgt, …),   // 拉线吸附成功
onConnectCancel: () => { /* 组件内自反馈：橡皮筋红闪 + 提示条 */ },
onPanBy: (dx, dy) => this.panBy(dx, dy), …
```

这样手势识别和业务反应完全解耦——组件不认识"客户"，但拖卡、连线、平移照常工作。**领域逻辑（"客户能连什么"、锚点是否合法）全部留给宿主**，组件只负责把候选锚点高亮、把结果事件抛出去。

### 8.3 撤销/重做怎么实现

每次手势落定 / API 调用引起 def 变化，把整个 def 序列化成一串 JSON 压入撤销栈；`Ctrl+Z` 弹栈后**精确恢复**（不沿用旧视图态，否则撤销"删除拖拽位置"时旧位置会阴魂不散）。外部 `setSpec` 视为新编辑会话，历史清空。组件本身不做结构校验——非法连线由后端保存期校验兜底。

---

<a id="9"></a>
## 9. 前后端如何对接（契约 + 交付链 + 四页面）

### 9.1 契约：一份 camelCase JSON

后端 `cmx-onto-model/src/def.rs` 的 serde 结构与前端 `model/types.ts` 手工对齐（两边都有测试锁住序列化格式；前端类型注释直接引用后端文件名）。记住两条：**后端忽略未知字段**，所以前端可以往 spec 里塞私有扩展（`_layout` 等）而不破坏契约；**前端契约类型改动必须双组件同步**（仓 AGENTS.md 纪律）。

### 9.2 交付链：组件源怎么到达浏览器

前端组件**构建后以 vendor 文件形式**进入后端资产（不是 npm 依赖）：

```
frontend/cmx-ontology-graph
   │  ./build.sh          → dist/cmx-ontology-canvas.esm.js（约 127KB，给线上）
   │                        dist/cmx-ontology-canvas.iife.js（给 demo 直开）
   │                        dist/cmx-ontology-canvas2d.{esm,iife}.js（暂不发布）
   ▼  ./sync-component.sh（只同步 SVG 版 esm）
backend/cmx-container/assets/onto/web/ui-native/vendor/cmx-ontology-canvas.js
   │  （assets/onto/ 是本体平台前端资产唯一真源，toml [assets] 直指工作区）
   ▼  :8097 启动时经 cmx_form::serve 挂 /api/native-pages/* 静态投递
浏览器宿主页首次挂载时 fetch 该文件 → blob module URL → 动态 import → 自注册
```

> **红线**（仓 AGENTS.md 明确）：改组件源必须重跑 `build.sh` + `sync-component.sh`，否则本体平台用的还是旧组件；且 `cmx-ontology-canvas.js` 禁止直接手改（AGENTS §四、8）。

### 9.3 宿主薄壳：四个 native 页面（在 `backend/cmx-container/assets/onto/web/ui-native/onto/`）

本体平台的前端"页面"是四个后端投递的 native JS 薄壳，都遵循门户"四区"布局（model 顶栏 / explorer 左树 / content 画布 / property 右侧检查器）：

| 页面 | 干什么 | 画布组件 |
| --- | --- | --- |
| `designer.js` | **本体设计工作台**：装载 manifest（含 batch 批量详情）、六类元素保存/删除、动作/函数试运行、存档；关系速建气泡 | `canvas-component`（内嵌 `<cmx-ontology-canvas>`） |
| `explorer.js` | **对象浏览器**：逛数据——选类型、状态分层、加过滤条件、看对象列表、Search-Around 顺关系钻取 | 不用（表格为主） |
| `workshop.js` | **应用搭建台/对象 360**：选一个对象看全貌 + 相关对象 + 动作中心（check-permission 预检后渲染可执行动作） | 不用 |
| `studio.js` + `studio/` 八模块 | **本体工作室**（20260913 上线，面向"本体维护者"）：场景画布（`GET /graph` 一条到位 + `POST /views` 成员/布局管理）、版本中心（检查点/对比/回滚/发布标记）、修订时间线（时间线/详情/revert）、状态流转、SSE 实时协同刷新、`/me/roles` 无权限降级只读 | `canvas`（经 state.js 统一装载） |

studio 的八模块拆分（`state` 数据层 / `controls` 控件 / `css` 样式 / `panels` 面板 / `inspector` 检查器 / `canvas` 画布编排 / `runtime` 操作运行时 / `main` 装配）是"薄壳变大后"的模块化——薄壳只做顺序装载（8 个 `/api/native-pages/portal.onto.studio.*` 请求），领域逻辑全在模块里。

此外后端 `dashboard.rs` 还提供一个开箱即用的**建模控制台**（根路径 `/`，纯 HTML 无依赖，双主题），不依赖任何前端仓，适合快速验证。页面注册清单在 `ui-native/index.json`（15 个条目）。

---

<a id="10"></a>
## 10. 怎么跑起来（快速上手）

### 10.1 起后端（本体平台独立服务）

```bash
cd backend/cmx-ontology
CONFIG_FILE=onto-server-dev.toml cargo run -p cmx-onto-server
# 浏览器打开 http://127.0.0.1:8097/  ← 自带建模控制台
# API 文档：http://127.0.0.1:8097/api/onto/v1/docs （Swagger UI）
```

配置链：`.env` → `CONFIG_FILE` 指定 toml → `[[databases]]` 里 db_id 必须是 `onto_pg`（缺了启动直接失败）。鉴权与门户一致：`POST /api/auth/login`（走 :8080 门户）或请求头 `X-API-Key` 开发免登录。前端联调最小集 = portal + model 同起，本体独立页也可直接开 `:8097` 的 native 页。

### 10.2 起/改前端组件

```bash
cd frontend/cmx-ontology-graph
npm install            # 首次 / 依赖变更后
./build.sh             # tsc 类型检查 + esbuild 四产物
./sync-component.sh    # 交付 SVG 版到后端 vendor（改了源必须跑，否则平台用旧组件！）
npx --no-install vitest run          # 纯逻辑单测（98 用例）
# 手动玩：浏览器开 demo/canvas-demo.html?selfcheck=1（66 条自检，IIFE 产物需先 build）
# 性能基准：demo/perf.html?auto=1&n=1000 / perf-canvas2d.html
```

### 10.3 检查命令（改完代码必跑）

```bash
# 后端（工作区规范：check/clippy，禁止 cargo build）
cd backend/cmx-ontology && cargo check && cargo clippy
# 前端
cd frontend/cmx-ontology-graph && npx tsc -p tsconfig.json --noEmit && npx --no-install vitest run
```

---

<a id="11"></a>
## 11. 术语表

| 术语 | 意思 |
| --- | --- |
| 本体 / Ontology | 企业概念地图：对象类型 + 关系 + 接口 + 共享属性 + 动作 + 函数（+ 场景） |
| apiName | 概念的英文稳定标识（如 `Customer`），表名/路由/契约都认它 |
| 直改 live | 20260917 架构：定义表即已发布真源，编辑直接生效；无草稿态 |
| 检查点 / snapshot | 用户主动把 live 打成的不可变全量快照（om_version），rev 指纹相同自动去重 |
| 发布标记 / release | 给检查点起名（tag + note），带 experimental/deprecated 警告门禁 |
| 修订 / revision | 每次保存追加的改动记录（om_revision）；删除走墓碑可恢复 |
| 生命周期 / transition | experimental → active → deprecated 的状态流转；唯一入口 `POST /lifecycle/transition` |
| 兼容矩阵 | 关系合法状态由两端对象状态决定的判定表（任一端废弃 → 关系只能废弃） |
| 机械级联 | 对象流转时把相关关系自动对齐到矩阵允许的状态，系统不产生违规态 |
| 场景 / Scene View | 底座元素的"过滤器/透镜"：成员引用 + 画布布局；auto 按域现算，manual 物化 |
| FEEL | DMN 标准表达式语言（`amount > 10000` 这类），动作校验和函数用它写 |
| 值映射五来源 | 动作编辑里显式取值：param / static / currentUser / currentTime / paramProperty |
| Search-Around | 从一个对象顺着某条关系把相关对象捞出来（图谱式钻取） |
| 对象集 Object Set | 带过滤/遍历/集合运算/聚合的一批对象（后端编译成一条 SQL） |
| PEP | 策略执行点：读侧行残差折进 SQL + 列脱敏；写侧 deny_actions 硬门 |
| Outbox | 事务性发件箱：副作用事件与业务数据同事务落库，定时线程自动投递 |
| 乐观锁 / version | 保存时带版本号，库里版本更新则拒绝（409），防互相覆盖（七类全有） |
| 维护角色守卫 | om_maintainer 白名单：空表开放；有行则存档/回滚/流转/场景编辑仅白名单可用 |
| 一芯多壳 | 业务逻辑装"芯" crate，部署形态装"壳" bin；同一套芯可独立部署也可内嵌 |
| ModuleSet | 路由模块组合器（cmx-engine-kit）：bin 组合根按契约装配 + 去重守卫 + 契约测试 |
| chassis | 通用服务骨架 `cmx-web-chassis`：main 只填 ServiceSpec 即起一个微服务 |
| Web Component | 浏览器原生自定义标签技术；Shadow DOM 隔离样式 |
| def / spec | 本体画布的 JSON 全量定义（nodes + edges + `_` 私有视图态） |
| vendor 交付 | 前端构建产物以 JS 文件形式拷进后端资产目录（非 npm 依赖） |
| 双组件纪律 | `<cmx-ontology-canvas>`(SVG) 与 `<cmx-ontology-canvas2d>` 契约逐项一致，改一处必改两处 |
| 视口剔除 | 大图性能优化：空间索引 + 只渲染视口内节点，拖动落定才重建 |
| 引用胶囊 / projection | 节点两形态：full 全卡 / ref 引用胶囊（跨场景引用的对象） |
| 正交布线 | 连线只走横平竖直的直角折线（现役画布默认贝塞尔轻弧，正交用于手动布线） |
| A\* | 一种最短路搜索算法，手动布线用它绕开卡片找最优直角路径 |

---

<a id="12"></a>
## 12. FAQ

**Q1：我们的本体是 RDF/OWL 吗？**
不是。全仓零 RDF/OWL/SPARQL 代码。表示形式是 **camelCase JSON 契约 + PostgreSQL（JSONB）存储**，语义体系对标 Palantir Foundry Ontology。要接语义网工具链需自写导入/导出适配器。

**Q2：旧的 `POST /publish` 去哪了？**
被拆成了三件事（20260917）：**存档** `POST /snapshots`（打检查点）、**发布** `POST /releases`（给检查点起名 + 门禁）、**回滚** `POST /versions/restore`（快照恢复回 live）。编辑不再有草稿态，直接写 live；每次保存都有修订记录兜底。SSE 的 `published` 事件保留兼容，新事件是 `checkpoint-created` / `release-created`。

**Q3：为什么对象类型定义里很多字段塞 JSONB，而不是一列一个字段？**
建模期结构常变（加字段、改约束），JSONB 让"类型演进零 DDL"；查询定位靠固定骨架列（apiName 主键、status 等）。例外是动作的 `target_object_types`——查询热点字段固化成 GIN 物化列，保存期自动派生。索引属性后续再按需固化。

**Q4：为什么本体画布拆成了两个组件？**
SVG 版（canvas）是生产现役：DOM 渲染天然吃 CSS 主题变量、好做悬浮提示与无障碍。Canvas 2D 版（canvas2d）是性能裕量版：千级节点场景重绘/内存更优。两者契约逐项一致（仓 AGENTS.md 双组件同步纪律），共享 model/layout/render/interaction 四层，选型见 `docs/components-comparison.md`。

**Q5：我改了前端组件源码，为什么平台上看不到效果？**
没跑 `sync-component.sh`（或没重跑 `build.sh`）。平台加载的是 vendor 目录里的构建产物，不是你改的源码。另外注意只发布 SVG 版——改了 canvas2d 只影响 demo/基准页。

**Q6：想加一个新 HTTP 接口，改哪里？**
① `cmx-onto-app/src/lib.rs` 的 `onto_routes_inner` 路由表加一条（注意工作区新规：固定资源段 + query/body，更新删除用 POST）；② 对应 `*_handlers.rs` 写 handler（模式照抄：剥离 status → 校验 → store → ApiResp）；③ 存储层不够用时去 `cmx-onto-store-pg` 补实现、`cmx-onto-model/src/store.rs` 补 trait 方法。若走组合根契约，还要确认 `module.rs` 两个模块前缀不受影响（路由契约测试会守护）。

**Q7：想给对象卡片加一种显示符号（比如"加密"徽标），改哪里？**
共享契约三处起步：`model/types.ts` 的 `GraphProperty` 加字段（后端契约对应 `def.rs` 的 `PropertyTypeDef` 同步加，带 `#[serde(default)]`）→ `canvas/svg.ts` 与 `canvas2d/renderer.ts` **两处**渲染各画一遍（双组件纪律）→ `render/annotations.ts` 补 title 文案。改完 build + sync + 双端联调。

**Q8：动作执行和直接写对象，该用哪个？**
业务语义的修改一律走动作（带校验、带审计、带副作用、过 PEP）；`POST /objects*` 直写是给数据集成（funnel）和运维脚本用的底层通道。前端页面目前全部只读对象 + 经动作改数。

---

## 附：关键文件速查

| 想看什么 | 去哪看 |
| --- | --- |
| 七类元素的类型定义与校验规则 | `backend/cmx-ontology/crates/cmx-onto-model/src/def.rs` |
| 场景视图定义 | `backend/cmx-ontology/crates/cmx-onto-model/src/view.rs` |
| 动作引擎纯逻辑（值映射/编辑集） | `backend/cmx-ontology/crates/cmx-onto-model/src/action.rs` |
| 存档指纹/diff/回滚校验 | `backend/cmx-ontology/crates/cmx-onto-model/src/snapshot.rs` |
| 全部 REST 路由（84 端点） | `backend/cmx-ontology/crates/cmx-onto-app/src/lib.rs:75` |
| 保存管道（乐观锁+修订+SSE） | `backend/cmx-ontology/crates/cmx-onto-store-pg/src/save_store.rs` |
| 修订历史与墓碑 | `backend/cmx-ontology/crates/cmx-onto-store-pg/src/revision_store.rs` |
| 检查点/发布/回滚存储 | `backend/cmx-ontology/crates/cmx-onto-store-pg/src/snapshot_store.rs` |
| 状态流转入口（矩阵+级联） | `backend/cmx-ontology/crates/cmx-onto-app/src/lifecycle.rs` |
| 建表 DDL | `backend/cmx-ontology/crates/cmx-onto-store-pg/src/ddl.rs` |
| 服务怎么启动（组合根+钩子） | `backend/cmx-ontology/crates/cmx-onto-server/src/main.rs`（249 行） |
| Outbox 自动投递线程 | `backend/cmx-ontology/crates/cmx-onto-app/src/action_handlers.rs`（spawn_outbox_dispatcher） |
| 出站投递（webhook/flow/report） | `backend/cmx-ontology/crates/cmx-onto-app/src/outbound.rs` |
| 场景图数据组装 | `backend/cmx-ontology/crates/cmx-onto-app/src/view_handlers.rs`（GET /graph） |
| 读侧 PEP / 状态过滤 | `backend/cmx-ontology/crates/cmx-onto-app/src/pep.rs` / `filter.rs` |
| SVG 组件元素层 | `frontend/cmx-ontology-graph/src/canvas/element.ts` |
| Canvas 2D 绘制层 | `frontend/cmx-ontology-graph/src/canvas2d/renderer.ts` |
| 前端契约类型 | `frontend/cmx-ontology-graph/src/model/types.ts` |
| 分域折叠布局 | `frontend/cmx-ontology-graph/src/layout/groupLayout.ts` |
| 手动布线算法 | `frontend/cmx-ontology-graph/src/layout/route.ts` |
| 双组件共用手册 | `frontend/cmx-ontology-graph/docs/canvas-component.md` |
| 设计工作台宿主壳 | `backend/cmx-container/assets/onto/web/ui-native/onto/designer.js` |
| 本体工作室（场景/版本/修订） | `backend/cmx-container/assets/onto/web/ui-native/onto/studio.js` + `studio/` |
