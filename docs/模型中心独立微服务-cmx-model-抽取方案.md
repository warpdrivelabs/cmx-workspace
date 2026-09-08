# 模型中心独立微服务（cmx-model）抽取方案

> 目标：参照 `cmx-flowengine` / `cmx-report` / `cmx-rulesengine` 的「一芯多壳」独立微服务范式，
> 把 `cmx-container` 里的**模型中心**能力（字典定义 DCT / 单据定义 DOC / 弹性组合 FLC / 数据库初始化 / 落库创建）
> 抽到并列的 `cmx-model/` workspace，形成端到端独立部署的能力中心。门户经反向代理接回，前端零改。
>
> 状态：**已定范围，进入实施**。日期 2026-08-23。
>
> **范围决策（已定夺）**：A=**MDM 抽为独立并列微服务 `cmx-mdm/`**（非并入 cmx-model；见 §9-A 修订）；B=**Code 随迁 cmx-model**；C=**`data/**` 随迁**（C1，模型中心为唯一权威源）；D=Phase 1 独立壳直连平台主库落 MENU/SEED。
>
> **仓库形态**：各 workspace 为独立 git 仓（`cmx-container`/`cmx-report`/… 各自 `.git`）。故 crate 迁移 = 文件系统复制 + 原仓删除，非跨仓 `git mv`。为避免 container 长时间不可编译，M0–M4 以**副本**在 `cmx-model` 建服务（container 保持内嵌可用），**M5 才做 container 切换**（删原 crate + 挂 proxy），风险隔离在最后一步。

---

## 0. 结论先行（TL;DR）

- **新建并列 workspace `cmx-model/`**（与 `cmx-container` / `cmx-report` 同级），承载模型中心微服务。
- **端口 `:8093`**（避开 portal 8080 / flow 8091 / report 8092 / rules 8094）。env 前缀 `MODEL_`，配置 `model-server.toml`，启动 `model.sh`。
- **一芯多壳**：中立核 `cmx-model-app`（`model_routes::<S>()` 泛型路由 + 自包含大盘 + 前端联邦）；独立壳 `cmx-model-server`（chassis bin）；平台壳 `ModelProxyModule`（proxy-only，留 `cmx-container`）。
- **推荐 Phase 1 范围 = 你点名的能力**：`cmx-model-meta` + `cmx-model-deploy` + `cmx-dct-*` + `cmx-doc-*` + `cmx-master-slave`（FLC 后端）迁入 `cmx-model/`。
- **一个必须定夺的范围问题**：`cmx-mdm-*`（主数据）是**唯一**在 `cmx-container` 内消费 `cmx-dct-store-pg` 的模块。为避免「container → cmx-model」反向 path 依赖，建议 **MDM 随迁**（只需重连 MDM→`cmx-portal` 死信一条边）；`cmx-code`（编码引擎）完全自洽，可选随迁。见 §9 决策点。
- **两个关键技术难点**（比 report 多出来的活）：① **双 DB 栈**——独立壳要同时注册 sqlx（`cmx-database`）与 tokio-pg（`cmx-database-pg`）两套数据源；② **落库引擎写平台库**——MENU/SEED 部署经 `cmx_biz::LocalMenuDefinitionImporter` 写 `cmx_menu`/`cmx_module`（主库），独立后需把「主库」也注册为一个数据源。
- **定义层是文件型**（`data/meta/**`、`data/dict/**`，非落库），随服务迁入 `cmx-model/data/`，经 `data_root` 配置指向；顺带修掉 `cmx-model-deploy/src/lib.rs:104` 的 crate 相对硬编码兜底路径。

---

## 1. 背景与目标

`cmx-container` 已从「大单体」逐步演进为「一批公用库 + 若干独立能力中心微服务」：门户（`cmx-portalservice` :8080）、流程（`cmx-flowengine` :8091）、报表（`cmx-report` :8092）、规则（`cmx-rulesengine` :8094）均已抽为并列 workspace，`cmx-container` 只留公用库与平台总装配器 `cmx-platform-app`。

**模型中心**是平台的元数据底座——设计期定义字典（DCT）、单据（DOC）、弹性组合（FLC），部署期把定义编译成物理表并初始化台账（数据库初始化 + 创建）。它目前仍**内嵌**在 `cmx-platform-app` 的路由总装里（`routes.rs:218-243` 无条件 `.merge()`）。本方案将其抽为独立微服务 `cmx-model`，达成：

1. **独立部署 / 独立演进**：模型中心可单独起进程（:8093），单独发版、单独扩容。
2. **门户瘦身**：`cmx-platform-app` 去掉模型中心引擎的编译期依赖，改为 proxy-only 薄壳（与 flow/report/rules 一致）。
3. **一芯多壳**：同一份中立核既能被独立壳装配（独立进程），也能被平台壳反代（门户视图），前端字节零改。

---

## 2. 现状分析（抽取的对象）

### 2.1 三层架构与 crate 归属

| 层 | crate | 职责 | 存储 |
|---|---|---|---|
| 定义层 | **cmx-model-meta** | DCT/DOC/RPT/BASE 定义 + FLC/FC 规则引擎 + 字典检索引擎；metaKind 分类学；DRN | **JSON 文件**（`data/meta/**`、`data/dict/**`），不落库 |
| 部署层 | **cmx-model-deploy** | 定义 JSON → `cmx_core::TableDefine` 编译；建 5 张 `cmx_model_*` 台账表；经 `PgTableDefineExecutor` 跑增量 DDL；台账 DML；漂移/场景矩阵 | 写目标 Postgres |
| 数据层 | —（目标库本身） | 物理业务表 + 台账表 | Postgres（由部署层经 `cmx-database`/`cmx-metadata` 落库） |
| HTTP 层 | **cmx-model-api** | axum handler + `ModuleRoutes`（`Router<CmxAppState>`） | 无状态 |

**metaKind 分类学**（`cmx-model-meta/src/definitions/store.rs:159-189, 335-495`）：定义层 = **DCT / DOC / RPT / BASE**（+ UNKNOWN 兜底）。部署层 `Kind` 枚举（`db_state.rs:337-394`）= **DCT / DOC / RPT / SEED / MENU**。

> ⚠️ **无 `FLX` token**：你说的「弹性组合」在代码里是 **`FLC`/`FC`**（flexible combination），只活在定义层（`cmx-model-meta/flexible_combination/**`），**从不落物理表**。后端运行时对等物是 `cmx-master-slave`（`CmxMasterSlave` 协调器 + `cmx-agg` 层间汇总）。

### 2.2 落库 / 数据库初始化引擎（"初始化、创建"能力的真身）

均在 `cmx-model-deploy`：

- **初始化目标库**（建 5 张台账表）：`init::init_db(db_id, operator_id, operator_name)`（`init.rs:27`）→ 逐条执行 `LEDGER_INIT_DDL`（`ledger.rs:398-523`，幂等 `CREATE TABLE IF NOT EXISTS`）→ `ensure_ledger_schema` → 写 `cmx_model_meta` + `cmx_model_deploy_history(kind=INIT)`。流式变体 `init_db_stream` / `init_plan_stream`。
- **定义 → 物理表**：`deploy::deploy(db_id, items, ...)`（`deploy.rs:93`）→ 按 `kind_order`（DCT 0→DOC 1→RPT 2→SEED 3→MENU 4）排序 → 逐项 `compile_definition`（`compile.rs:969`：`compile_dct`/`compile_doc`/`compile_rpt`）得 `Vec<TableDefine>` → `PgTableDefineExecutor::create_or_upgrade_table`（`deploy.rs:534`，增量 DDL，加法式）→ 台账事务写 `cmx_model_source` / `cmx_model_module` / `cmx_model_module_kind` / `cmx_meta_table_define(_version)` / `cmx_model_deploy_history`。
- **台账 5 表**（`lib.rs:50-62` `LEDGER_TABLES`）：`cmx_model_meta`、`cmx_model_module`、`cmx_model_module_kind`、`cmx_model_deploy_history`、`cmx_model_source`。
- **物理业务表前缀**：DCT→`cf_*`、DOC→`cv_*`、RPT→`cr_*`（3 张共享）。**全部动态**从定义 JSON 生成，无字面表名需迁移。

### 2.3 域 crate 依赖图（抽取关键）

```
cmx-rowsource                         (infra 叶)
   ▲
cmx-master-slave ──► [仅 cmx-rowsource]           ◄── 纯叶子（FLC 后端 + cmx-agg），无域依赖
   ▲     ▲
cmx-dct-model ─► core,utils,biz        │
   ▲                                   │
cmx-dct-store-pg ─► dct-model, master-slave, rowsource, database-pg,
   ▲   ▲            core, traits, biz, api-types, model-meta
   │   └────────────────┐（跨域，MDM 复用 dict_upsert）
cmx-dct-api ─► dct-store-pg, dct-model, api-core, api-types, biz
                        │
cmx-doc-model ─► core, biz, utils      │
   ▲                                   │
cmx-doc-store-pg ─► doc-model, master-slave, rowsource, database(sqlx),
   ▲                database-pg, core, traits, utils, biz, api-types, model-meta
cmx-doc-api ─► doc-model, doc-store-pg, api-core, api-types, model-meta, biz, core, database, database-pg

cmx-model-meta ─► cmx-jsonstore, api-types
cmx-model-deploy ─► core, database(sqlx), cmx-metadata, utils, api-types, model-meta, biz(菜单), traits
cmx-model-api ─► api-core, model-meta, model-deploy, core, api-types

cmx-mdm-store-pg ─► mdm-model, cmx-dct-store-pg◄──跨域, database-pg, core, ...
cmx-mdm-api ─► mdm-store-pg, cmx-dct-store-pg◄──跨域, cmx-portal◄──跨域(死信), ...
cmx-code-model ─► 仅 core ；cmx-code-api ─► code-model, api-core, ...（内嵌自己的 store，最自洽）
```

**抽取关键结论：**
1. `cmx-master-slave` 是**纯叶子**（只依赖 `cmx-rowsource`）——最先迁、可自由共享。
2. **两套 DB 栈并存**：DOC store 同时用 `cmx-database`(sqlx) + `cmx-database-pg`(tokio-pg)；DCT 只用 tokio-pg；`cmx-model-deploy` 只用 sqlx（经 `get_default_db_manager()`）。
3. `cf_*`/`cv_*` 表 100% 动态，无字面表名迁移。
4. **`DatabaseManager` 不在 `CmxAppState` 里**——handler 经全局 `get_default_db_manager()` 取（sqlx）或 `cmx-database-pg` 全局管理器取（tokio-pg）。**这正是能把路由泛型化 `<S>` 的前提**（与 report 同理）。
5. **唯一的 container 内反向消费者是 MDM**：`cmx-mdm-store-pg`/`cmx-mdm-api` 依赖 `cmx-dct-store-pg`（激活时在主事务里复用 `dict_upsert`），且 `cmx-mdm-api` 还依赖 `cmx-portal`（死信通知）。这决定了 MDM 的去留（§9）。

### 2.4 前端页面清单与联邦现状

模型中心前端有三类物理页面，**当前经门户 `cmx-form` 从 `cmx-container/data/{native,html}-pages/**` 读盘服务**（rev-based ETag/304），非微服务：

- **native 页**（`data/native-pages/sources/`，`index.json`）：`portal.definition.base-dct`、`portal.dct.data-editor`、`portal.doc.doc-loader`、`portal.datasource.cluster`（字典/单据/弹性组合三视图只读）、`portal.dam.registry-center`、`demo.dict-base.*`（4 页）、`demo.doc-base.*`（5 页）等。
- **html 页**（`data/html-pages/sources/fi/cmxfico/gl/`）：三套字典维护工作台 **平级 `dictflat-*` / 自分级 `dicttree-*` / 带分类 `dictcls-*`**（各 4 文件：model/explorer/content/prop-detail）+ `dct-data-editor-html` + 弹性组合 demo（科目/交易）。
- **设计期编辑器**（UI5 Web Components，编译进 `/portal/` SPA `cmx-portal-manager`，非 data 页）：`portal-definition-manager.js`（DCT+DOC 定义器）、`portal-flexible-combination-manager.js`（弹性组合定义器）、`portal-menu-editor.js`（菜单管理）。
- **数据库初始化 / 模型部署 UI**：无专用 SPA 组件（后端驱动）；旧的部署/菜单控制台在根 `web-folder`（"CloudMatrix 开发套件"，Vue）。

> ⚠️ **前端的两难**（§7 详述）：设计期定义器是编译进**共享门户 SPA**的，不是按页联邦的独立单元。抽微服务时可先联邦**data 页**（native+html），设计期编辑器暂留门户 shell（它们只是打 `/api/definitions`、`/api/flexible-combination` 等，会被 API 反代自然转发）。

---

## 3. 参照模板：cmx-report 的「一芯多壳」七步范式

`cmx-report` 已把范式固化，逐项复用：

1. **新 workspace**：域 crate 作 `path` 成员；基础设施（`cmx-database-pg`/`cmx-core`/`cmx-biz`/`cmx-api-types`/`cmx-web-chassis`/`cmx-web-monitor`/`cmx-service-base` …）以**跨 ws `path`** 反向引用 `../cmx-container`（仍是 container 成员，非本库成员）。故构建本库需 `../cmx-container` 并排存在。
2. **`.cargo/config.toml`**：aliyun 镜像 source-replace；**必须定义 `nora` registry**（即使不拉——因为跨 ws infra crate 继承 container 根 manifest 的 `[patch.nora]`，Cargo 需能解析该名）；`[http] check-revoke=false` + `[net] git-fetch-with-cli=true`。
3. **中立核 app crate**：`xxx_routes::<S>() where S: Clone+Send+Sync+'static`（handler 只用 `Path`/`Query`/`Json`，不用 `State`；身份经 `cmx-traits::auth::context_scope`；信封 `cmx-api-types`）；`include_str!` 自包含大盘；`native_pages.rs` 联邦（字节对齐门户信封，`rev=xxhash64`，`web/ui-*` 读盘）。
4. **独立壳 bin**：`dotenvy` 首行 → `cmx_service_base::init_config_manager()` → `ChassisConfig::load` → `ServiceSpec::<()>::new(...).nest_api(false).router(...).state(()).init("datasources", ...)` → `run(spec)`。
5. **平台壳（留 container）proxy-only**：deps 仅 `cmx-api-core`+`axum`+`reqwest`+`cmx-traits`（**零引擎依赖**）；`impl ModuleRoutes`，恒等转发 `{base}/api{path}{query}` + 三层出站认证（`X-API-Key`/`X-Delegated-User-Token`/`X-Request-Id`）+ 页面反代中间件。
6. **门户接线**：`CenterUrlsConfig` 加 `Option<String>` 字段；`xxx_remote_base()` reader；`routes.rs` 的 `merge_xxx()`；`service_topology()` 登记。
7. **`.env` + `*-server.toml` + `run.sh`**，新端口。

---

## 4. 目标架构（cmx-model workspace）

```
cmx-model/                              # 并列 workspace（与 cmx-container/cmx-report 同级）
├── .cargo/config.toml                  # aliyun source-replace + 定义 nora registry（复刻 report）
├── .env                                # CONFIG_FILE / MODEL_PORT=8093 / MODEL_PG_URL / MODEL_MAIN_PG_URL / CMX_PORTAL_DATA_ROOT
├── model-server.toml                   # chassis: host/port/log + [datasource] 两库 url
├── model.sh                            # exec cargo run -p cmx-model-server "$@"
├── rust-toolchain.toml
├── data/                               # ★ 文件型定义层随迁（原 cmx-container/data 的模型中心子集）
│   ├── meta/definitions/**             # DCT/DOC/RPT/BASE 定义 JSON
│   ├── meta/flexible-combination/**    # FLC 规则
│   ├── dict/**                         # 字典检索数据
│   ├── menu-pages/**                   # 菜单定义（MENU deploy 源）
│   └── native-pages|html-pages/**      # （可选）若前端页也随迁，见 §7
├── web/                                # ★ 前端联邦源（复刻 report web/）
│   ├── ui-native/{index.json, model/*.js}
│   ├── ui-html/{index.json, index/, fi/…}
│   └── menu-source/ , menu-manifest.json
└── crates/
    ├── cmx-model-meta/                 # 迁入（git mv，零改）— 定义层
    ├── cmx-model-deploy/               # 迁入（改：data_root 兜底、双库 db_id）— 部署/落库层
    ├── cmx-dct-model/                  # 迁入
    ├── cmx-dct-store-pg/               # 迁入
    ├── cmx-doc-model/                  # 迁入
    ├── cmx-doc-store-pg/               # 迁入
    ├── cmx-master-slave/               # 迁入（FLC 后端 + cmx-agg）
    ├── cmx-model-app/                  # ★ 新建：中立核（泛型路由 + 大盘 + 联邦）
    └── cmx-model-server/               # ★ 新建：独立壳 bin（:8093）
    #  （若 §9 决定随迁）cmx-mdm-*、cmx-code-*
```

**平台侧（留 `cmx-container`）**：
```
cmx-container/crates/libs/cmx-model/cmx-model-proxy/   # ★ 新建 proxy-only 薄壳（ModelProxyModule + with_model_page_proxy）
                                     cmx-model-api/     # ↓ 退役（handler 逻辑迁入 cmx-model-app）
cmx-container/crates/libs/cmx-dct/cmx-dct-api/          # ↓ 退役
cmx-container/crates/libs/cmx-doc/cmx-doc-api/          # ↓ 退役
```

> `cmx-model-app` 合并原 `cmx-dct-api` + `cmx-doc-api` + `cmx-model-api` 三个 `-api` crate 的 handler，泛型化 `<S>`。原三个 `-api` crate 从 container 移除（逻辑已迁走），由**单一** `ModelProxyModule` 反代其全部前缀。

### 4.1 路由归并（中立核 → 独立壳）

中立核暴露与门户**逐字节一致**的绝对路径（`/dct/*`、`/doc/*`、`/model/*`、`/definitions/*`、`/flexible-combination/*`、`/dict/*`），独立壳 `nest("/api", ...)`：

```rust
// cmx-model-server/src/main.rs（复刻 cmx-rpt-server）
let api_router = cmx_model_app::model_routes::<()>()            // /model/* + /definitions/* + /flexible-combination/*
    .merge(cmx_model_app::dct_routes::<()>())                  // /dct/* + /dict/*
    .merge(cmx_model_app::doc_routes::<()>())                  // /doc/*
    .route("/model/stats", get(dashboard::model_stats))
    .merge(cmx_model_app::native_pages::frontend_pages_routes::<()>())
    .layer(axum::middleware::from_fn(cmx_web_monitor::observe));
let app_router = Router::new()
    .route("/", get(dashboard::dashboard))                     // 根大盘逃出 /api
    .nest("/api", api_router);
```

---

## 5. Crate 迁移清单与依赖策略

| crate | 动作 | 说明 |
|---|---|---|
| `cmx-master-slave` | **git mv → cmx-model** | 纯叶子，零改 |
| `cmx-dct-model` / `cmx-dct-store-pg` | **git mv → cmx-model** | 零改（infra 转跨 ws path） |
| `cmx-doc-model` / `cmx-doc-store-pg` | **git mv → cmx-model** | 零改 |
| `cmx-model-meta` | **git mv → cmx-model** | 零改 |
| `cmx-model-deploy` | **git mv + 小改 → cmx-model** | 修 `lib.rs:104` 硬编码兜底路径；确认 `data_root` 经配置解析 |
| `cmx-model-app` | **新建** | 合并 dct/doc/model 三 `-api` 的 handler，泛型 `<S>` |
| `cmx-model-server` | **新建** | chassis bin，:8093，注册**双 DB 栈** |
| `cmx-dct-api` / `cmx-doc-api` / `cmx-model-api` | **退役（container）** | 逻辑迁入 `cmx-model-app` |
| `cmx-model-proxy` | **新建（container）** | proxy-only 薄壳 |
| `cmx-mdm-*` / `cmx-code-*` | **见 §9 决策** | 随迁 or 留 container（取 cross-ws 反向 path） |

**依赖策略**（复刻 report）：
- 域内 model crate 之间：纯 `path`（本库成员）。
- 基础设施：跨 ws `path` 反向引用 `../cmx-container/crates/libs/...`（`cmx-core`、`cmx-utils`、`cmx-biz`、`cmx-traits`、`cmx-api-types`、`cmx-database`、`cmx-database-pg`、`cmx-metadata`、`cmx-rowsource`、`cmx-jsonstore`、`cmx-web-chassis`、`cmx-web-monitor`、`cmx-service-base`）。这些仍是 container 成员，对其根解析 `workspace=true` 与 `[patch.nora]`。
- 外部 crate：走 aliyun 镜像，版本与 container 根对齐。
- **`cmx-api-core`（`CmxAppState`/`ModuleRoutes`）不进 `cmx-model-app`**——中立核不认平台状态，只认 `<S>` + `cmx-api-types`。

---

## 6. 关键技术难点与决策

### 6.1 双 DB 栈注册（比 report 多的核心活）

report 独立壳只注册 tokio-pg（`cmx_service_base::register_pg_datasources`）。模型中心**必须同时注册两套**：

- **sqlx `cmx-database`**（`get_default_db_manager()`）——`cmx-model-deploy` 全部 DDL/台账、`cmx-doc-store-pg` 的 sqlx 装载路径依赖它。平台是在 `cmx-platform-app::config::datasource::init_datasources()` → `db_manager.register_data_source()` 建立的。独立壳需在 `.init("datasources", ...)` 钩子里等价调用（把 sqlx `DatabaseManager` 也初始化 + 注册目标库）。
- **tokio-pg `cmx-database-pg`**（`register_pg_datasources`）——`cmx-dct-store-pg`/`cmx-doc-store-pg` 的零拷贝 ZMC 路径依赖它。

**动作**：`cmx-model-server` 的 datasource init 钩子里，对每个目标 db_id **各注册两套驱动**。建议抽一个 `cmx-service-base::register_dual_datasources(configs)` 便捷原语（或在 server bin 内内联），避免各服务重写。

### 6.2 "主库" 与 "目标库" 双重身份

`cmx-model-deploy` 除了写**目标业务库**（per-request `db_id`，如 `fico-db`），还会：
- 读 `get_default_db_id()` 主库的 `cmx_module` 拿模块权威显示名（`ledger.rs:344`）。
- **MENU 部署经 `cmx_biz::LocalMenuDefinitionImporter` 写主库** `cmx_menu`/`cmx_module`（`deploy_seed_menu.rs:387`，先删后插，自管事务）。

**含义**：独立 `cmx-model-server` 必须把**平台主库**也注册为一个数据源（默认库），否则 `db-state` 的模块名解析与 MENU 部署会失败。

**决策**：`model-server.toml` 配 **两个** PG url——`main_pg_url`（平台主库，注册为 default db，承载 `cmx_menu`/`cmx_module` 读写）+ 目标业务库（如 `fico-db`）。二者可指向同一实例不同 db。

> 备选：把 MENU/SEED 部署**委托回门户**（模型服务只发 HTTP 让门户 `LocalMenuDefinitionImporter` 落库）。更解耦但改动大，建议 Phase 2 再议；Phase 1 直接注册主库最省事。

### 6.3 文件型定义层的 data_root

定义/字典/菜单是**磁盘 JSON**，经 `data_root` 解析：`portal.data_root` 配置 → `CMX_PORTAL_DATA_ROOT` 环境变量 → `./data`（`seed_scanner.rs:31-41`、`deploy_seed_menu.rs:182`）。

**动作**：
1. 把 `cmx-container/data/` 的模型中心子集（`meta/**`、`dict/**`、`menu-pages/**`）**git mv → `cmx-model/data/`**（或保留门户一份、服务一份——见 §9 单一事实源决策）。
2. `.env` 设 `CMX_PORTAL_DATA_ROOT=./data`（相对 `model.sh` 的 cwd）。
3. **修 `cmx-model-deploy/src/lib.rs:104`** 的 `CARGO_MANIFEST_DIR/../../../../data/meta/definitions` 硬编码兜底——迁 ws 后相对层级失效，改为统一走 `data_root` 解析或读 `CMX_PORTAL_DATA_ROOT`。

### 6.4 泛型化 `<S>`（handler 去 CmxAppState）

原 `cmx-dct-api`/`cmx-doc-api`/`cmx-model-api` 的 handler 返回 `Router<CmxAppState>` 且部分抽 `CmxSvrContext`（认证）。迁入 `cmx-model-app` 后需：
- 路由改 `Router<S> where S: Clone+Send+Sync+'static`。
- handler 只留 `Path`/`Query`/`Json` 提取器；DB 经全局管理器取（本就如此）。
- 认证身份改经 `cmx-traits::auth::context_scope::current_auth()`（内嵌时同源，独立时兜底空串）——与 report `apply_ops` 同款。原 `model_operator`(从 `CmxSvrContext` 取 operator) 改走 context_scope。

### 6.5 cmx-biz 编译期依赖

`cmx-model-deploy` `use cmx_biz::menu::LocalMenuDefinitionImporter`（MENU 落库）+ `cmx_biz` seed 装载。`cmx-biz` 是 container 公用库，report 已跨 ws path 复用它——照搬即可，无需拆。

---

## 7. 前端联邦

### 7.1 data 页（native + html）——可直接联邦

复刻 `cmx-report/crates/cmx-rpt-app/src/native_pages.rs`：

- 把模型中心 data 页从 `cmx-container/data/{native,html}-pages/` 迁到 `cmx-model/web/{ui-native,ui-html}`。
- 新建 `cmx-model-app/src/native_pages.rs`：读盘 → 组装门户同款 `NativePageFull`（`rev = format!("{:016x}", xxh64(bytes,0))`）→ 暴露 `/api/native-pages/{id}`、`/api/html-pages/{id}`（+ batch/list），字节对齐门户信封。UI 目录经 env（`MODEL_UI_DIR` 默认 `web/ui-native`、`MODEL_UI_HTML_DIR` 默认 `web/ui-html`）。

### 7.2 门户 F3 反代

复刻 `cmx-container/crates/libs/cmx-rpt/cmx-rpt-api/src/proxy.rs` 的页面反代中间件到 `cmx-model-proxy`：

- `is_model_owned_page(id)` predicate 覆盖：`portal.definition.*`、`definition.*`、`portal.dct.*`、`portal.doc.*`、`portal.datasource.cluster`、`portal.dam.registry-center`、`demo.dict-base.*`、`demo.doc-base.*`、`fi.cmxfico.gl.dict{flat,tree,cls}-*`、`fi.cmxfico.gl.dct-data-editor-html`、弹性组合 demo id 等。
- `page_proxy_mw`：命中则转发到 `{model_base}/api/native-pages/{id}`，否则 `next.run`（batch/list 混合 id 留门户）。

### 7.3 设计期编辑器（暂留门户 SPA）

`portal-definition-manager.js`（DCT/DOC 定义器）、`portal-flexible-combination-manager.js`（FLC 定义器）、`portal-menu-editor.js`（菜单管理）编译进共享 `/portal/` SPA `cmx-portal-manager`。它们只是打 `/api/definitions`、`/api/flexible-combination`、`/api/model/*`、`/api/menu` 等——这些前缀被 `ModelProxyModule` **API 反代**自然转发到 :8093。故 **Phase 1 无需动 SPA**：编辑器留门户 shell，后端定义/落库全走反代。真正的"独立门面"（模型中心自持 SPA）留待 Phase 3。

### 7.4 菜单联邦

`cmx-report/web/menu-manifest.json` 目前是**静态未被门户消费**的产物（F3 联邦时门户聚合器实时拉取的规划契约）。Phase 1 沿用现状：模型中心菜单仍走 DB MENU-deploy（§6.2）落 `cmx_menu`。`menu-manifest.json` 的实时聚合是全平台统一议题，不在本方案 Phase 1。

---

## 8. 门户接线（cmx-container / cmx-portalservice）

1. **`CenterUrlsConfig`**（`cmx-container/crates/libs/cmx-plugin/src/center_client/config.rs:37-57`）加字段：
   ```rust
   /// 模型中心（独立 cmx-model-server）URL。非空=平台反代到它，空=进程内嵌（过渡期）。
   #[serde(default)]
   pub model: Option<String>,
   ```
2. **`routes.rs`** 加 `model_remote_base()` reader + `merge_model(router)` 包装（复刻 `merge_report`）：`Some(base)` → `router.merge(ModelProxyModule::new(base, api_key).routes())` + `with_model_page_proxy(router, base, api_key)`；`None` → 保持**内嵌**（过渡期回退，或直接告警不挂）。
3. **退役内嵌 merge**：`routes.rs:218-243` 的 `.merge(DocModule.routes())`、`.merge(DctModule.routes())`、`.merge(ModelModule.routes())` 移除，改由 `merge_model(...)` 统一。总装：`merge_model(merge_flow(merge_report(merge_rules(base))))`。
4. **`service_topology()`**（`routes.rs:78-140`）：`doc`/`dct`/`model` 从 `embedded("…")` 改 `proxy` 登记。
5. **代理 URL 配置**（`dev-local.toml` / `portal-server.toml` `[center_client.urls]`）加 `model = "http://127.0.0.1:8093"`。
6. **白名单**（`portal-server.toml:181-209`）：`/api/definitions`、`/api/flexible-combination`、`/api/dct`、`/api/dict`、`/api/doc`、`/api/model`、`/api/native-pages`、`/api/html-pages` 等条目**保持**（反代不改鉴权面）。

---

## 9. 范围决策点（需定夺）

### 决策 A：MDM（主数据）是否随迁？【关键】

`cmx-mdm-store-pg`/`cmx-mdm-api` 是 **container 内唯一**消费 `cmx-dct-store-pg` 的模块（激活时主事务复用 `dict_upsert`——**强耦合，难 RPC 化**），且 `cmx-mdm-api` 依赖 `cmx-portal`（死信通知）。

- **选项 A1（推荐）随迁 MDM 到 cmx-model**：避免「container → cmx-model」反向 path 依赖，保持 container 干净。代价：重连 MDM→`cmx-portal` 一条边（改为跨 ws path 反向引用 container 的 `cmx-portal`，或死信改 HTTP 回调）。MDM 概念上也属主数据建模族，归位合理。
- **选项 A2 MDM 留 container**：则 container 需 cross-ws path-dep 进 cmx-model 取 `cmx-dct-store-pg`——**引入反向编译期依赖**，container 不再自洽（须并排 cmx-model 才能编译）。破坏 report/flow 建立的「container = 自洽公用库」原则。**不推荐**。
- **选项 A3 dct/doc 等留 container 当共享库，cmx-model 反向复用**：改动最小但不"抽出"，与你的诉求（抽到 cmx-model）相悖。**不推荐**。

> 倾向：**A1**。即 Phase 1 一并迁 `cmx-mdm-{model,store-pg,api}`。

### 决策 B：Code（编码引擎）是否随迁？

`cmx-code-*` 完全自洽（model 仅依赖 `cmx-core`，api 内嵌自己的 store，`Advance` trait 已反转 DB 依赖），迁不迁都低风险。倾向**随迁**（它常与单据/字典配套用于业务编码），但可留待 Phase 2，无耦合阻塞。

### 决策 C：定义/字典文件（`data/**`）单一事实源

门户 SPA 与部分 demo 页也读同一批 `data/`。抽出后：
- **C1（推荐）**：`data/meta`、`data/dict`、`data/menu-pages`（定义/字典/菜单）**移** cmx-model（模型中心是其唯一权威写入方）；门户不再持有。
- **C2**：暂时门户/服务各留一份（双写风险），迁移期过渡。

### 决策 D：MENU/SEED 落库位置

§6.2 —— Phase 1 建议 cmx-model-server **注册平台主库**直接落 `cmx_menu`（选项内联）；Phase 2 可改**委托门户** HTTP 落库（更解耦）。

---

## 10. 分阶段路线图

> **实施进度**（2026-08-23）：
> - ✅ **M0 骨架**：`cmx-model/` workspace 建成（`.cargo/config.toml`/`.env`/`model-server.toml`/`model.sh`/`rust-toolchain.toml`/`.gitignore`/根 `Cargo.toml`）。`cargo metadata` 通过。
> - ✅ **M1 迁域 crate**：9 个库 crate（master-slave/dct-model/dct-store-pg/doc-model/doc-store-pg/model-meta/model-deploy/code-model/code-api）复制入 `cmx-model/crates/`，infra 转跨 ws path。`data/**`（meta/dict/menu-pages/native-pages/html-pages/form-pages/modules/dam-registry，6.4M）随迁。**`cargo check --workspace` 绿（1m04s，exit 0）**——所有迁入 crate 在新 ws 对 container infra 编译通过，源 Cargo.toml 零改。
> - ✅ **M2 中立核 `cmx-model-app`**：dct/doc/model/code 四域 handler 全迁并泛型化 `<S>`（删 `State(_s)`；`CmxSvrContext` 丢弃项删、真用项改 `context_scope::current_auth()`）。**关键纠错**：DOC 有 3 个 handler（save/save_batch/restore）真用 ctx 写 BIGINT 审计列，子代理改走 `current_auth()` 并逐字复刻原 `actor_id_i64/actor_name` 语义（已核对）。native_pages（适配 `sources/` 布局）+ dashboard + msgpack/db_id 内联 + 中央 lib.rs 完成。`cargo check` 绿（两处中央修补：补 `cmx-database`/`cmx-code-api`/`regex` 依赖、修 server 头注释 `cf_*/cv_*` 的 `*/` 误闭合）。
> - ✅ **M3 独立壳 `cmx-model-server`（:8093）**：**双 DB 栈**实现并编译通过——sqlx 主库(默认=cmx，承 cmx_menu/cmx_module + deploy get_default_db_id)+ sqlx 目标库(fico) + 两库注册进 tokio-pg（逐字段 DbConfig 转换，对齐 platform-app）。banner/大盘/联邦/observe 装配完成。`cargo check --workspace` 全绿。
> - ✅ **M4 前端联邦 + 真机验证**：`cmx-model-server` 独立起于 :8093（双 DB 栈注册成功，日志确认 cmx-db + fico-db 各注册进 sqlx & tokio-pg），端点扫描 **13/13 绿**——根大盘/`_mon`/`model/stats`(15定义:5DCT/3DOC/3RPT/3BASE)/`definitions/list`/`db-state?db_id=fico-db`(initialized:true,CURRENT,含24表模块)/`flexible-combination/list`/native-pages(list+单页)/html-pages(list+三套字典工作台 平级`dictflat`/自分级`dicttree`/带分类`dictcls` 单页)/`doc/meta`/`dct/meta`(消歧后返 cf_currency 元数据) 全通。DCT/DOC data 端点走通（返「表未部署」= 正确业务错误，非代码问题）。**抓修一真 bug**：门户 html 页面清单 `fi` 分片含 `"doc":null`，serde `default` 不覆盖显式 `null` → 整分片解析静默降级为空（80 个 fi 页全 404）；修 = `null_str` 反序列化器（null/缺失→空串）应用于 HtmlRow/IndexEntry 全可选字符串字段，修后 html 页 30+1+80=111 全载。
> - ✅ **M5 container 反代切换**：container 新建 proxy-only 薄壳 `cmx-model-proxy`（`ModelProxyModule` impl `ModuleRoutes` + `with_model_page_proxy` 页面反代中间件，仅依赖 `cmx-api-core`+`axum`+`cmx-proxy-core`，零引擎依赖）。`routes.rs` 加 `model_upstream()`(读 `[center_client.services].model`) + `merge_model()`（**保留内嵌兜底**：配了→反代到 :8093，没配→内嵌 Dct/Doc/Model/Code 四模块；`MdmModule` 恒内嵌待另抽）；四模块从 `base` 移入 `merge_model` None 分支；`service_topology()` 按配置切 proxy/embedded。container `cargo check` 绿（1m48s）。门户 `portal-server.toml` 加 `model={url=:8093}` + 白名单 `/api/model`、`/api/code`。**真机 E2E 10/10 绿**：门户 :8080 → ModelProxy → cmx-model-server :8093，`model/db-state`(initialized:true)/`definitions`/`flexible-combination`/`dct/meta`/三套字典工作台 html + native 页全通；**页面 rev 门户代理 == 直连 :8093 字节一致（8ae9cac4b278203a）**。前端零改达成。
> - ⚠️ **旁注（非本次改动）**：门户启动时平台库 `cmx` 有一处**既有迁移漂移**（`20260819_001 baseline`：`cmx_exclusion_rule_item.archived` 列缺失，属规则引擎表非模型中心），会阻断 `migration.enabled=true` 启动；与本抽取无关，测试时临时置 false 验证后已复原 true。建议后续单独修该迁移。
> - 🔜 **后续**：container 侧退役内嵌 dct/doc/model/code `-api`（当前保留作兜底，可择期删）；前端设计期编辑器随门户 SPA（API 反代自然转发，无需动）。

---

## 附录 B：MDM 独立微服务 `cmx-mdm/`（并列抽取，进行中）

> 决策 A 落地：MDM **不并入 cmx-model**，抽为独立并列微服务 `cmx-mdm/`（:8095）。三向跨 ws 依赖：
> infra→cmx-container、`cmx-dct-store-pg`→**cmx-model**、`cmx-portal`→**cmx-portalservice**（DCT 不反依赖 MDM，无环）。单 DB 栈（tokio-pg，比 model 简单——MDM 不落 DDL）。

- ✅ **M0/M1**：`cmx-mdm/` workspace 建成（.cargo/config.toml/.env/mdm-server.toml/mdm.sh/根 Cargo.toml）；迁 `cmx-mdm-{model,store-pg}` + 10 个 `portal.mdm.*` native 页（index 裁剪至 mdm-owned）。**`cargo check` 绿（55s，exit 0）**——两库对跨 ws 依赖编译通过，源 Cargo.toml 零改。
- ✅ **M2 中立核 `cmx-mdm-app`**：合并 cmx-mdm-api 全部 handler（11 文件 + distribution 引擎 + flow_client，5479 行）泛型化 `<S>`（两子代理并行）。**坑同 DOC**：activation/scan/merge 的 `actor_id_i64` + flow_cb/review/governance 的 `current_user_id(&svr_ctx)` 共 8 处真用身份 → 改 `context_scope::current_auth()`（子代理 A 精准发现我配方漏数、停在 4 文件；我手工补全）。MDM 不用 msgpack。
- ✅ **M3/M4 独立壳 `cmx-mdm-server`（:8095）**：单 DB 栈（tokio-pg，fico biz + cmx 主库 default 供死信 notify）。boot 成功，端点扫描 **8/8 绿**（health/stats/大盘/_mon/native 联邦 10 页/activations/channels）。DCT 跨 ws 耦合、distribution 引擎真机走通。
- ✅ **M5 container 反代切换**：新建 proxy-only `cmx-mdm-proxy`（`MdmProxyModule` + `portal.mdm.*` 页面反代）；`merge_mdm`（内嵌兜底）+ topology + 门户 `[services].mdm=:8095`（已预留）。**真机 E2E 7/7 绿**：门户 :8080 → MdmProxy → :8095，4 个鉴权 API（带 JWT 委托）+ 2 页 + **rev 字节一致（87408663cad38abe）**。
- ⚠️ **抓修 package collision**：模型中心抽出后 `cmx-model-meta` 同名同版存在于 cmx-container 原址（内嵌兜底保留）与 cmx-model 副本两处。MDM 初版 `cmx-dct-store-pg` 取自 cmx-model → 与 `cmx-portal`（经 container 根解析 cmx-model-meta→container 原址）冲突，Cargo 无法写锁。**修**：MDM 的 `cmx-dct-store-pg` 改取 **cmx-container**（与 cmx-portal 同源解析），两路径统一；MDM 遂只跨 container+portalservice 两 ws（不依赖 cmx-model）。教训：跨 ws path 复用时，同名 crate 须全链路同源。

---

## 附录 C：退役 container 内嵌兜底 crate（全量清理，已完成）

> 决策「Retire + repoint」落地：删除 container 内 15 个模型中心/主数据引擎 crate，反代变强制（去内嵌兜底），并把 cmx-mdm/portalservice 的相关依赖统一 repoint 到 cmx-model（消除 package collision 根因）。

- ✅ **前置修复（真 bug）**：`cmx-model-server` 原**未注入** `GlobalCodeMinter` → 独立服务里 DCT/DOC 带 code_rule 保存会静默跳过铸号（此前被门户内嵌注入掩盖）。补：server 数据源钩子里 `GlobalCodeMinter::set(CodeEngine)`（+ cmx-code-api/cmx-traits 依赖）。同理 MDM 激活用 `GlobalCodeMinter::get()?` 有占位码兜底，独立态降级为占位（可后续补注入，非阻塞）。
- ✅ **repoint（消歧根因）**：`cmx-mdm` 的 `cmx-dct-store-pg` + `cmx-portalservice` 的 `cmx-model-meta` 均改指 **cmx-model** 副本——三仓（cmx-model/cmx-mdm/portalservice）对 cmx-model-meta 全链同源，collision 根除。
- ✅ **删 15 crate**：container 内 `cmx-dct/*`、`cmx-doc/*`、`cmx-code/*`、`cmx-master-slave`、`cmx-mdm/{model,store-pg,api}`、`cmx-model/{meta,deploy,api}` 物理删除 + 根 manifest members/deps 清理；**保留** `cmx-model-proxy`、`cmx-mdm-proxy` 两反代壳。
- ✅ **platform-app 解耦**：`merge_model`/`merge_mdm` 去内嵌 None 分支（改为「没配=不挂路由」，与 flow/report/rules 同构）；删 5 个 `-api` import + 3 个 OpenAPI 合并 + `start_distribution()`（分发引擎随 MDM 迁独立壳）+ `init_code_engine()`（编码注入随模型中心迁独立壳）+ config/code.rs。
- ✅ **四 ws 全绿**：container `cargo check`（31.9s）+ portal build（9.9s）+ cmx-mdm + cmx-model 全 exit 0。**真机 E2E 8/8**：门户 :8080 → 两代理 → :8093/:8095，model/mdm 全能力 + 页面联邦通过；model server 日志确认 `✅ 编码引擎已注入`。既有迁移漂移测试临时关 migration 已复原。
- **现状**：container 彻底无模型中心/主数据引擎源码，只余两反代壳。门户编译期不再碰这些引擎。反代成强制——**必须**起独立 cmx-model-server(:8093)+cmx-mdm-server(:8095) 并配 `[services].{model,mdm}`，否则门户不挂对应路由（无内嵌回退）。
> - **注**：container 侧原 crate **未动**（仍内嵌可用）；M5 才切换。MDM 待 cmx-model 就绪后另建并列 `cmx-mdm/` ws（跨 ws 取本库 `cmx-dct-store-pg`）。

| 阶段 | 内容 | 验收 |
|---|---|---|
| **M0 骨架** | 建 `cmx-model/` workspace、`.cargo/config.toml`、`.env`、`model-server.toml`、`model.sh`、`rust-toolchain.toml`（复刻 report） | `cargo metadata` 通过；空 server 起在 :8093，`/_mon` 可达 |
| **M1 迁域 crate** | git mv `master-slave`/`dct-*`/`doc-*`/`model-meta`/`model-deploy`（+ 按决策 A/B 的 mdm/code）；infra 转跨 ws path；修 `model-deploy` 硬编码路径 | `cargo build` 绿；域 crate 单测零回归 |
| **M2 中立核** | 新建 `cmx-model-app`：合并 dct/doc/model handler，泛型 `<S>`；认证走 context_scope；`include_str!` 大盘 | `model_routes::<()>()` 编译；handler 单测绿 |
| **M3 独立壳 + 双 DB** | `cmx-model-server`：dotenvy/config-manager/chassis；**注册 sqlx + tokio-pg 双栈** + 主库&目标库 | 真机：`POST /api/model/init`（建 5 台账表）、`POST /api/model/deploy`（DCT→`cf_*`、DOC→`cv_*`）、`GET /api/model/db-state`、`/api/dct/meta`、`/api/doc/data/*` 全通 |
| **M4 前端联邦** | `native_pages.rs` 迁 `web/ui-{native,html}`；服务自投递 | 独立起 :8093，`/api/native-pages/{model-id}` 与门户内嵌字节一致 |
| **M5 门户反代壳** | container 建 `cmx-model-proxy`（`ModelProxyModule` + `with_model_page_proxy`）；退役 dct/doc/model `-api` 内嵌；`CenterUrlsConfig.model` + `merge_model` + topology + urls 配置 | 门户 :8080 打 `/api/dct/*`、`/api/model/*`、模型中心页 → 经反代命中 :8093，前端零改；`service_topology` 显示 `proxy` |
| **M6 全量测试 + 文档** | 端到端（门户↔服务）回归；字典三工作台 / 单据定义 / 弹性组合 / 初始化 / 部署真机；技术方案+测试报告（对标 report `docs/summary/`） | 报告归档；`dev-local.toml` 配 `model=:8093` 后全链路绿 |

---

## 11. 风险与回滚

- **双 DB 栈初始化顺序**：sqlx `DatabaseManager` 与 tokio-pg 管理器需在路由挂载前就绪；`.init("datasources", ...)` 里保证 both 注册成功再放行。回滚：`CenterUrlsConfig.model` 留空 → 门户回退内嵌（Phase 5 前保留内嵌分支作为回退闸）。
- **主库耦合**：MENU/SEED 写主库——若主库 url 未配，`db-state`/菜单部署失败。M3 显式校验主库可达，失败 fail-fast 并告警。
- **MDM 跨域边**（决策 A）：A1 需重连 MDM→cmx-portal；先跑通 DCT/DOC/FLC/deploy，MDM 作 M1 子步单独验证。
- **前端单一事实源**（决策 C）：迁 `data/` 前先 grep 门户 SPA / demo 对同路径的读，确认无遗漏消费者；迁移期可 C2 双份过渡。
- **`nora` registry 解析**：`.cargo/config.toml` 必须定义 nora 名（否则 `patch entry nora should be a URL or registry name`）——M0 即复刻到位。
- **回滚粒度**：M1-M4 全在新 ws，不触门户；M5 才改 container 路由。M5 前门户完全不受影响，风险隔离在最后一步。

---

## 12. 验收标准

1. `cmx-model-server` 独立起于 :8093，`init`/`deploy`/`db-state`/`dct`/`doc`/`definitions`/`flexible-combination` 全能力真机绿；建物理表 `cf_*`/`cv_*`/`cr_*` + 5 张 `cmx_model_*` 台账。
2. 门户 :8080 配 `[center_client.urls].model` 后，所有模型中心 API 与页面经反代命中 :8093，**前端字节零改**；`service_topology` 显示模型中心为 `proxy`。
3. `cmx-container` 移除模型中心引擎编译期依赖（`cmx-model-proxy` 仅 `reqwest`+`axum`+`api-core`+`traits`）；container 仍自洽可编译（决策 A 若选 A1）。
4. 域 crate 单测零回归；端到端回归报告归档 `cmx-model/docs/summary/`。

---

## 附：端口 / 命名总表

| 服务 | workspace | bin | 端口 | env 前缀 | 启动 |
|---|---|---|---|---|---|
| 门户 | cmx-portalservice | cmx-portal-server | 8080 | — | — |
| 流程 | cmx-flowengine | cmx-flow-server | 8091 | FLOW_ | flow |
| 报表 | cmx-report | cmx-rpt-server | 8092 | RPT_ | report.sh |
| **模型** | **cmx-model** | **cmx-model-server** | **8093** | **MODEL_** | **model.sh** |
| 规则 | cmx-rulesengine | cmx-rule-server | 8094 | RULE_ | rules.sh |
