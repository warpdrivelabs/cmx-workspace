# 主应用路由装配统一推广方案（引擎侧）v2.1

> 前置：`20260916_cmx-platform-app_路由装配倒置与模块组合方案.md`（v2.1 已实施）。门户主应用（cmx-portal-server）已完成「bin 作组合根 + `ModuleRoutes` trait + `PlatformModules` 统一组合」改造。
>
> 本文回答：**其余 7 个主应用（flow :8091 / report :8092 / model :8093 / rules :8094 / mdm :8095 / onto :8097 / dataauth :8098）是否按同一方式改造**——结论：**推广，契约先泛型化下沉，再按「基建 → 试点 → 批量」三阶段落地**。
>
> 修订记录见附录 C（v2.0：第一轮对抗审查，修正 3 项 P0 与全部 P1/P2；v2.1：第二轮复核，首轮 13 项处置全部复核通过，再修 1 项 P1 挂载位置与 4 项 P2——复核结论：可实施）。

---

## 一、结论先行

1. **值得推广，但不是照搬**。7 个引擎主应用的 bin 其实**已经是组合根**：业务路由全部来自 `*-app` 中立核的自由函数 `xxx_routes::<S>()`，bin 显式逐条 `.merge()`，不存在门户旧版 `api_routes()` 式隐藏聚合。缺口不在「装配位置」，而在「模块契约」：自由函数与 trait 对象两套装配语言并存，且无去重守卫、无 api_doc 槽位、无统一组合器。
2. **直接照搬会踩一个历史决策**。`ModuleRoutes` 目前绑定 `Router<CmxAppState>`（cmx-api-core），而引擎中立核刻意「不认 CmxAppState」——cmx-model-app 的路由表**曾经 impl 过 ModuleRoutes，后来主动删除**改为对任意 S 成立的自由函数（dct_routes.rs:3-6 注释）。照搬等于让中立核重新绑死平台状态类型，开倒车。
3. **解法：把契约泛型化** `ModuleRoutes<S>`，与具体 State 解耦后下沉到 `cmx-engine-kit`（中立核们的中立核，7 仓中 6 个 `*-app` 已依赖它，依赖面轻）。门户侧 34 处 impl（cmx-container 33 处 + cmx-portalservice 1 处）机械补 `<CmxAppState>`，行为零变化；引擎核以 `impl<S> ModuleRoutes<S>` 适配器接入，中立性保持。
4. **引擎侧装配模式 = 按仓现状归属切片的组合根**：bin 把 `/api` 内路由按**现状认证归属**分入 authed 切片（auth 中间件内）与 open 切片（auth 外）——flow / report / rules / onto 存在显式 open 子树，**model / mdm 的 stats 与页面投递现状在 auth 层之内、必须留在 authed 切片**（见 §3.3，照搬 report 形态会扩大认证面外的暴露，属安全回归）；根级 / 边角路由（dashboard 大盘、swagger/docs、console——openapi 类注意保留其在 api_router 上的既有位置）保持 bin 手写。
5. **实施顺序**：阶段 0（cmx-container 基建，零行为变化）→ 阶段 1（试点 cmx-flowengine，模式最全）→ 阶段 2（批量 6 仓，每仓独立提交独立回滚）。前端与平台外部行为零影响（纯装配重构，路径/中间件层级/免认证面逐一保持，并恢复**全量路由契约测试**作每仓验收）。

---

## 二、现状调查：7 主应用装配矩阵

### 2.1 共性骨架与两种层序（7/7 同构，细节两态）

```
bin main.rs（140~200 行）
  ├─ cmx_service_base::init_infra()
  ├─ ChassisConfig::load("<svc>", "<svc>-server.toml")
  ├─ 自行组装 Router（业务表来自 *-app 自由函数，bin 显式 merge）
  │    ├─ authed 子树：核心路由表 + 中间件（层序两态，见下）
  │    ├─ open 子树（仅 flow / report / rules / onto）：前端页投递（± stats）免认证
  │    │     model / mdm 无 open 子树——stats 与页面投递全在 auth 层之内
  │    ├─ 根级：/ 大盘、swagger/docs、（dataauth: /console /swagger）
  │    └─ .nest("/api", ...)   ← 搭配 chassis .nest_api(false) 让根路由逃出 /api
  ├─ ServiceSpec::<()>::new(name, cfg).router(..).state(()) + init 钩子
  └─ cmx_web_chassis::run(spec)   ← 纯 HTTP 服务器壳，不参与路由组合
       └─ 追加 merge(/_mon 监控三端点) + default_layers(Trace/BodyLimit/CORS/Compression)
```

**中间件层序两态**（axum `.layer()` 只包住之前添加的路由，后挂者在**外**先跑）：

| 层序 | 仓 | 现状语义 |
|---|---|---|
| `.layer(observe)` → `.layer(auth)`（auth 在外先跑） | flow / report / rules / onto / dataauth | 遥测采到已认证身份 |
| `.layer(auth)` → `.layer(observe)`（observe 在外先跑） | **model / mdm** | 遥测采到匿名身份 |

改造时**按仓保持原层序**，不做有意识统一（若要统一须单独声明为行为变化并评审）。

| # | 仓 | bin / 端口 | 中立核 | 核心路由表（自由函数） | State |
|---|---|---|---|---|---|
| 1 | cmx-flowengine | cmx-flow-server :8091 | cmx-flow-app | `flow_routes::<S>()` + `flow_routes_v1::<S>()`（同一 inner 表双前缀二重挂载） | `()` |
| 2 | cmx-report | cmx-rpt-server :8092 | cmx-rpt-app | `report_routes::<S>()` + `consol_routes::<S>()` | `()` |
| 3 | cmx-model | cmx-model-server :8093 | cmx-model-app | `model_routes`（内部 3 合 1 可见）+ `dct_routes` + `doc_routes` + `code_routes` | `()` |
| 4 | cmx-rulesengine | cmx-rule-server :8094 | cmx-rule-app | `rule_routes::<S>()` + `rule_routes_v1::<S>()` | `()` |
| 5 | cmx-mdm | cmx-mdm-server :8095 | cmx-mdm-app | `mdm_routes::<S>()`（内部 8 合 1，含 `/mdm/health`） | `()` |
| 6 | cmx-ontology | cmx-onto-server :8097 | cmx-onto-app | `onto_routes::<S>()` + `onto_routes_v1::<S>()` | `()` |
| 7 | cmx-data-auth | cmx-dataauth-server :8098 | cmx-dataauth-app | `dataauth_routes::<S>()` + `dataauth_routes_v1::<S>()`（同一 inner 表双前缀二重挂载，lib.rs:30-44） | `()` |

### 2.2 差异点（改造时逐一对待）

| 仓 | OpenAPI/Swagger | health | 特殊边角 |
|---|---|---|---|
| flow | `flow_openapi()` 由 route_defs 派生，挂 `/api/flow/v1/docs` + `openapi.json`（根级逃出 nest） | 无 | v1_extras（SSE/票据/协同）在 `flow_routes_v1` 内部 merge（有注释，轻度聚合）；前端页挂 auth 外；JWT 白名单仅 SSE 票据路径 |
| report | **完全没有**（无 utoipa 依赖） | 无 | `/rpt/stats` 免认证（open 子树，仅 observe 层，main.rs:75-80）；零 feature 零 cfg，最干净 |
| model | handler 有大量 `#[utoipa::path]` 但**无文档结构、未挂载** | 无（靠 `/` 大盘 + `/_mon`） | 四张表；**`/model/stats` 与页面投递在 auth 层内**（main.rs:80-92），认证白名单内置为空（cmx-model-app/auth.rs:18）、toml 白名单注释态；bin 内双 DB 栈注册钩子 + GlobalCodeMinter 注入 |
| rules | `rule_openapi()` 仅骨架，`let _ = rule_openapi()` 占位；`/rules/v1/openapi.json` 手写 | 无 | 页面投递 `HtmlLayout::Disabled`；白名单空（cmx-rule-app/auth.rs:28） |
| mdm | `MdmApiDoc` derive 已存在但**全 workspace 零消费者**（预留死代码） | 有：`/api/mdm/health`（auth 白名单放行，cmx-mdm-app/auth.rs:20） | **`/mdm/stats` 与页面投递在 auth 层内**（main.rs:63-74）；分发通道 feature（kafka/rocketmq，默认关，不涉路由）；启动期 distribution 钩子 |
| onto | 手写宏 openapi.json + CDN Swagger UI（`/onto/v1/docs`） | 无 | 页面投递 `HtmlLayout::Disabled`；白名单空（cmx-onto-app/auth.rs:26）；Outbox 定时投递钩子（非路由） |
| dataauth | 手写 serde_json openapi（**刻意不引 utoipa**）+ `/swagger` CDN 页 | 无（大盘轮询 `/api/dataauth/v1/stats`，在 authed 内） | **唯一 bin 级 console**（`/console` 工作台单页）；admin 子表内部 `require_admin` 整组层；**不挂 form pages**（7 仓唯一）；唯一未依赖 cmx-engine-kit |

### 2.3 关键基础设施事实

- `cmx-web-chassis`：`pub async fn run<S>(spec: ServiceSpec<S>)`（lib.rs:159），Builder 接收**已组装好的** Router，只做 nest `/api` 开关、`/_mon` 挂载、default_layers、init 钩子、优雅停机、banner——**不参与路由组合，本次改造不动它**。
- `cmx-api-core`（ModuleRoutes 现居地）：重依赖 crate（cmx-database / cmx-auth / cmx-iam / cmx-agent / modql…），为平台 API 骨架服务。**中立核不应为拿一个 trait 依赖它**。
- `cmx-engine-kit`（「中立核们的中立核」，请求期横切件单源）：依赖面轻（cmx-core / cmx-traits / cmx-utils / cmx-database-pg / cmx-web-monitor / cmx-api-types / axum / jsonwebtoken / tokio / serde*），**6/7 引擎核已依赖**（唯 dataauth-app 未接）。生命周期分工明确：启动期归 cmx-service-base，请求期归本 crate——路由组合契约属请求期，落这里名正言顺。已验证 engine-kit 及其依赖均不（传递）依赖 cmx-api-core，api-core 反向新增 engine-kit 依赖**无环**（`cargo tree -p cmx-engine-kit -i cmx-api-core` 无匹配）。
- 门户侧 `ModuleRoutes` 波及面：**34 处 impl**（cmx-container 33 处 + cmx-portalservice `cmx-portal-api/src/handlers/mod.rs:41` 的 PortalModule），编译器可全量兜住。
- utoipa：cmx-container 根 `Cargo.toml:386` 定义 `utoipa = { version = "5", features = ["axum_extras", "chrono", "decimal", "uuid"] }`（默认特性含 macros）。`utoipa::openapi::OpenApi` 类型**不受特性门控**（utoipa-5.4.0 lib.rs:239 `pub mod openapi;` 无 cfg），api_doc 签名无需任何特性。
- 平台侧 8 个反代壳消费的是中立核**平台壳**，与本仓 `*-app` 无直接耦合；`cmx-model-proxy` 的「进程内嵌回退」用的是 cmx-container 自己的 cmx-model 域 crate，不依赖 cmx-model 仓——**无跨仓引用变化**。

---

## 三、目标架构

### 3.1 契约泛型化：`ModuleRoutes<S>`（cmx-engine-kit）

```rust
// cmx-engine-kit/src/routes/mod.rs（新）
pub trait ModuleRoutes<S>: Send + Sync {
    /// 注册该模块的路由（全路径含业务前缀，由装配方 merge）
    fn routes(&self) -> axum::Router<S>;
    /// 模块前缀（仅诊断元数据，不参与挂载；多前缀模块可写 "/flow|/flow/v1"）
    fn prefix(&self) -> &'static str;
    /// 模块名（组合清单查重 + 日志）
    fn module_name(&self) -> &'static str;
    /// OpenAPI 文档切片（无文档返回 None）
    fn api_doc(&self) -> Option<utoipa::openapi::OpenApi> { None }
    /// 全量装配后的整路由器包装钩子（默认恒等；门户页面反代中间件用）
    fn wrap_router(&self, router: axum::Router<S>) -> axum::Router<S> { router }
}
```

- **为何必须泛型化**：中立核的存在意义是不认 `CmxAppState`（mdm-app 注释明示；model-app 曾主动删过 ModuleRoutes impl）。泛型后同一份 trait：门户在 `S = CmxAppState` 实例化，引擎 bin 在 `S = ()` 实例化，中立核 `impl<S: Clone + Send + Sync + 'static> ModuleRoutes<S> for XxxModule` 保持零平台耦合。对象安全已论证：方法全部 `&self` 接收器、无泛型方法，`Box<dyn ModuleRoutes<S>>` 成立。
- **为何放 engine-kit 而非 api-core**：api-core 重依赖会拖垮中立核依赖树；engine-kit 轻且 6/7 已依赖。已评估并否决的备选：新建契约 crate（与 engine-kit 定位重复）；trait 拆两处（门户引擎两套语言，违背统一初衷）；不推广（引擎收编是前置方案 §十.2 既定演进）。
- **utoipa 依赖写法（定案）**：engine-kit **不走 workspace 继承**，直写 `utoipa = { version = "5", default-features = false }`，附注释说明缘由——Cargo 规定 workspace 继承只允许追加 `features`/`optional`，**`default-features` 与继承连用是非法 manifest**；而若改根定义（default-features = false + 显式 macros），engine-kit 继承后会把 utoipa-gen（过程宏）拖进 7 个引擎仓的构建。直写的版本 `"5"` 与根一致；特性按 Cargo 加法并集规则合成为单份构建——engine-kit 自身边零特性；无其他 utoipa 边的 report / ontology / data-auth 三仓整体拿到零特性最小面；自身已带 macros 的 flowengine / rulesengine / model / mdm 四仓保持既有特性面不变（非本次新增）。`OpenApi` 类型不受特性门控，api_doc 签名成立。
- **api-core 保持源兼容**：`routes/traits.rs` 本地定义删除，改为 `pub use cmx_engine_kit::ModuleRoutes;`（api-core 新增 engine-kit 轻依赖，无环）。现有 impl 的 `use cmx_api_core::routes::traits::ModuleRoutes;` 导入路径**不变**。

### 3.2 `ModuleSet<S>`：从 PlatformModules 提取的通用组合器（cmx-engine-kit）

```rust
pub struct ModuleSet<S> { items: Vec<Box<dyn ModuleRoutes<S>>> }

impl<S: Clone + Send + Sync + 'static> ModuleSet<S> {
    /// 由既有清单构造（不查重——对齐 PlatformModules::new(items) 现状语义）
    pub fn new(items: Vec<Box<dyn ModuleRoutes<S>>>) -> Self;
    /// 追加模块，module_name 重复即 panic（启动期 fail-fast，替代静默双挂载）
    pub fn with(self, m: Box<dyn ModuleRoutes<S>>) -> Self;
    /// 合并另一个集合，逐个走 with 查重
    pub fn merge(self, other: Self) -> Self;
    /// 两阶段 fold：① 按清单顺序 merge 全部 routes() → ② 按同序应用 wrap_router
    pub fn fold(&self) -> axum::Router<S>;
    /// 种子 ApiDoc + 逐模块 api_doc() 切片合并（引擎可暂不使用，槽位备用）
    pub fn merged_openapi(&self, seed: utoipa::openapi::OpenApi) -> utoipa::openapi::OpenApi;
}
```

- 即现 `PlatformModules` 的通用骨架原样下沉：`new(items)` 保持**不查重**的现状语义（现无调用方触发重复），`with`/`merge` 查重——「对外行为不变」包含这一边角（PlatformModules 薄封装时逐方法对号）。
- **两阶段 fold 的语义原样保留**——先全量 merge 再统一 wrap，因为 `Router::layer` 只包住当时已存在的路由，跨模块中间件（门户页面反代）必须后置应用。
- `PlatformModules` 改为内部持有 `ModuleSet<CmxAppState>` 的薄封装，**对外方法签名与行为不变**（core_kit / dev_kit / upstream 拓扑等门户特有内容全部留在 cmx-platform-app）。

### 3.3 引擎侧装配模式：按现状归属切片的组合根

**切片划分规则：模块进哪个切片 = 现状它在 auth 层之内还是之外，逐仓对齐，禁止照搬统一模板**：

| 仓 | authed 切片（auth 层内） | open 切片（auth 层外） | 中间件层序（authed 内，外→内） |
|---|---|---|---|
| flow | FlowCoreModule + FlowV1Module | FormPagesModule（from_assets） | observe → auth |
| report | ReportCoreModule + ConsolModule | FormPagesModule + **RptStatsModule**（现状唯一免认证 stats） | observe → auth |
| model | ModelCore/Dct/Doc/Code + **ModelStatsModule + FormPagesModule**（现状全在 auth 层内） | 无 | **auth → observe** |
| rules | RuleCoreModule + RuleV1Module | FormPagesModule（HtmlLayout::Disabled） | observe → auth |
| mdm | MdmCoreModule + **MdmStatsModule + FormPagesModule**（现状全在 auth 层内） | 无 | **auth → observe** |
| onto | OntoCoreModule + OntoV1Module | FormPagesModule（HtmlLayout::Disabled） | observe → auth |
| dataauth | DataAuthCoreModule + DataAuthV1Module | 无（**不挂 form pages**，现状就没有） | observe → auth |

> **open 切片中间件同样按现状**：仅 report 的 open 带 observe 层；flow / rules / onto 的 open 现状无任何层，保持不新增。

> **model/mdm 的 stats 与页面投递为何留 authed**：现状它们在 auth 层内、白名单未配（model 内置白名单为空、mdm 仅放行 `/mdm/health` 与 `/mdm/flow/callback`），公开取数只在 `auth.mode = off` 的 dev 环境成立。若业务上确要公开，正确做法是在 `*-app` 认证中间件白名单补条目（engine-kit 已支持前缀匹配），**不动装配结构**，且须作为有意行为变化单独评审——本方案默认严格保持现状。

bin 形态（以 report 为例，open 切片带 observe 层与现状一致）：

```rust
let authed = ModuleSet::<()>::new(vec![])
    .with(Box::new(ReportCoreModule))
    .with(Box::new(ConsolModule))
    .fold()
    .layer(axum::middleware::from_fn(cmx_web_monitor::observe))
    .layer(axum::middleware::from_fn(cmx_rpt_app::auth_middleware));
let open = ModuleSet::<()>::new(vec![])
    .with(Box::new(FormPagesModule::<cmx_api_types::Error>::new(PageServeConfig::from_assets())))
    .with(Box::new(RptStatsModule))
    .fold()
    .layer(axum::middleware::from_fn(cmx_web_monitor::observe));
let router = Router::new()
    .route("/", get(cmx_rpt_app::dashboard::dashboard))   // 根级边角，bin 手写
    .nest("/api", authed.merge(open));
// ServiceSpec::<()>::new(...)  ← chassis 用法不变
```

**`FormPagesModule<E>`（cmx-form 新增，6 仓共用，dataauth 不装）**：`frontend_pages_routes::<S, E>(cfg)` 的 ModuleRoutes 适配器：

```rust
pub struct FormPagesModule<E> { cfg: PageServeConfig, _e: PhantomData<E> }
impl<S, E> ModuleRoutes<S> for FormPagesModule<E>
where
    S: Clone + Send + Sync + 'static,
    E: IntoResponse + From<PageServeError> + 'static,
{
    fn routes(&self) -> Router<S> { frontend_pages_routes::<S, E>(self.cfg.clone()) }
    // module_name: "form.pages"，prefix: "/native-pages*|/html-pages*"
}
```

构造器接受完整 `PageServeConfig`（rules / onto 传 `HtmlLayout::Disabled` 变体，model / mdm / flow / report 传 `from_assets()`）；错误类型 E 逐仓取各引擎既有实例（`cmx_api_types::Error` 或 `cmx_xxx_app::XxxError`，与现状一致）。

**中立核适配器**（`*-app` 内新增 `module.rs`，free fn 保留为双壳真源）：

```rust
// cmx-rpt-app/src/module.rs
pub struct ReportCoreModule;
impl<S: Clone + Send + Sync + 'static> ModuleRoutes<S> for ReportCoreModule {
    fn routes(&self) -> Router<S> { report_routes::<S>() }
    fn prefix(&self) -> &'static str { "/report-design|/report-source-bindings|/rpt/*" }
    fn module_name(&self) -> &'static str { "rpt.core" }
}
```

**特殊形态处理**：

- **flow / rules / onto / dataauth 的 v1 二重挂载**：`XxxCoreModule`（`xxx_routes`，前缀 `/xxx`）与 `XxxV1Module`（`xxx_routes_v1`，前缀 `/xxx/v1`）注册为**两个模块**，module_name 不同（如 `flow.core` / `flow.v1`），去重守卫不误伤；同一 inner 表被双前缀共享的现状保持。改造前后挂载路径集合相同，不新增 matchit 冲突面（现状已同挂验证可行）。
- **dataauth 内部分层**：admin 子表的 `require_admin` 整组层、demo 子表的 pep guard 层都在 `dataauth_routes` 内部，收敛进 `DataAuthCoreModule.routes()` 后原样保持，bin 不感知。
- **mdm 八合一 / model 四表**：mdm 取 `MdmCoreModule` 一枚（内部 8 合 1 本来可见）；model 拆 4 枚对应四张表。
- **引擎 openapi/docs**：本期不做 `api_doc()` 接入（report/model 的 swagger 缺失另立项）；既有挂载位置按仓保持——**rules / onto / dataauth 的 openapi.json（含 onto 的 docs）挂在 api_router 上、authed 子树之外**（URL 含 `/api` 前缀，改造时保留在 api_router，**不得挪到 app_router 根**，否则丢前缀致消费方 404）；**flow 的 SwaggerUi 是唯一真·bin 根级**（完整外部路径 `/api/flow/v1/docs`，规避尾斜杠重定向）；`merged_openapi` 槽位备用。

### 3.4 平台侧（cmx-container + cmx-portalservice）改动与影响

| 项 | 改动 | 行为 |
|---|---|---|
| `ModuleRoutes` 定义 | 移至 engine-kit 并泛型化；api-core re-export 保路径兼容 | 零 |
| 34 处 impl（container 33 + **portalservice 1：cmx-portal-api handlers/mod.rs:41**） | `impl ModuleRoutes for X` → `impl ModuleRoutes<CmxAppState> for X`（机械） | 零 |
| `PlatformModules` | 内部改持 `ModuleSet<CmxAppState>`，方法逐一对号委托（new 不查重语义保留）；core_kit/dev_kit/upstream/拓扑不动 | 零 |
| cmx-form | 新增 `FormPagesModule<E>` 适配器（纯新增） | 零 |
| 门户路由面 | fold 逻辑等价搬迁（顺序/去重/wrap 语义一致） | 零（DebugModule 移除等上次改造结论不变） |

---

## 四、实施计划

### 阶段 0：cmx-container 基建（零行为变化；cmx-container 1 次提交 + cmx-portalservice 1 次独立小提交）

| 文件 | 改动 |
|---|---|
| `cmx-container/crates/libs/cmx-engine-kit/Cargo.toml` | + `utoipa = { version = "5", default-features = false }`（直写不继承，缘由见 §3.1） |
| `cmx-container/crates/libs/cmx-engine-kit/src/lib.rs` | + `pub mod routes;` |
| `cmx-container/crates/libs/cmx-engine-kit/src/routes/mod.rs` | 新增：`ModuleRoutes<S>` + `ModuleSet<S>` + 去重/fold/openapi 单元测试 |
| `cmx-container/crates/libs/cmx-apis/cmx-api-core/Cargo.toml` | + `cmx-engine-kit`（workspace path） |
| `cmx-container/crates/libs/cmx-apis/cmx-api-core/src/routes/traits.rs` | 本地定义 → `pub use cmx_engine_kit::ModuleRoutes;` |
| cmx-container 33 个 impl 文件 | 机械补 `<CmxAppState>`（脚本 + 编译器兜底） |
| `cmx-portalservice/crates/cmx-portal-api/src/handlers/mod.rs` | 同上（第 34 处，独立仓独立提交） |
| `cmx-container/crates/libs/cmx-platform-app/src/routes.rs` | PlatformModules 内部 ModuleSet 化 |
| `cmx-container/crates/libs/cmx-form/src/serve/module.rs` | 新增 `FormPagesModule<E>` |

**验证（覆盖两面：api-core 面 + engine-kit 面）**：
- api-core 面：cmx-container、cmx-portalservice（dev-tools 开 + 关双态）`cargo check`（cmx-model 的 api-core 声明无消费者，`cargo tree -i cmx-api-core` 已证空，无需 check）。
- engine-kit 面：**6 个依赖 engine-kit 的引擎仓各跑一次 `cargo check`**（flowengine / report / rulesengine / model / mdm / ontology），确认 utoipa 零特性进入不破坏编译。
- `cargo tree` 抽查：任一引擎仓确认 utoipa 无特性链；container 内特性合并无回归。
- portal 路由面无 diff（fold 等价性靠代码审查 + 阶段 1 起的路由契约测试兜底）。
- **Cargo.lock 归属策略**：6 个引擎仓的 lockfile 变更（含 3 个无 utoipa 仓首次拉入 utoipa 子树）**随各仓阶段 1/2 的改造提交一并提交**（各仓首次 build/check 自然产生），阶段 0 只动 container 与 portalservice 两仓，保持「每仓提交可独立回滚」。

### 阶段 1：试点 cmx-flowengine（1 次提交，含本仓 lockfile）

模式最全（v1 二重挂载 + openapi 挂载 + form pages + dashboard + SSE），试点通过则批量无悬念。

- `cmx-flow-app`：新增 `src/module.rs`（`FlowCoreModule` / `FlowV1Module`），lib.rs 导出。
- `cmx-flow-server/src/main.rs`：组合根改写（authed = 两 flow 模块 + observe → auth；open = FormPagesModule——**现状无 observe 层，保持不加**；`/` 大盘 bin 根级；SwaggerUi 真·bin 根级完整外部路径 `/api/flow/v1/docs` 原样保留）。
- **验证**：`cargo check` + `cargo clippy`；**新增 bin 装配级路由契约守护测试**（flow-app 既有 `api_contract` 是 *-app 内部 defs 级、不覆盖 bin 装配面，lib.rs:312 仅作形式参照）：静态清单**以改造前 main.rs 逐条抄录生成、改造前先跑绿一次**，改造后测试不变即零回归；launcher 冒烟：`/` 大盘 200、`/_mon` 200、`/api/flow/v1/openapi.json` 200、一条业务 GET、native-pages 免认证投递 200。

### 阶段 2：批量 6 仓（每仓 1 次提交，含各自 lockfile；顺序 = 风险从低到高）

| 顺序 | 仓 | 适配器 | bin 要点 |
|---|---|---|---|
| 1 | cmx-report | ReportCoreModule / ConsolModule / RptStatsModule / FormPagesModule | 最简；stats 与 pages 留 open 切片（现状免认证） |
| 2 | cmx-model | ModelCore/Dct/Doc/Code + ModelStatsModule + FormPagesModule | **stats 与 pages 留 authed 切片**（现状 auth 层内）；auth → observe 层序保持；双 DB 钩子不动 |
| 3 | cmx-mdm | MdmCoreModule + MdmStatsModule + FormPagesModule | 同上（auth 层内、层序保持）；distribution 钩子不动 |
| 4 | cmx-rulesengine | RuleCoreModule / RuleV1Module / FormPagesModule(Disabled) | openapi.json 根级保持 |
| 5 | cmx-ontology | OntoCoreModule / OntoV1Module / FormPagesModule(Disabled) | docs + Outbox 钩子不动 |
| 6 | cmx-data-auth | DataAuthCoreModule / **DataAuthV1Module** | **需新增 cmx-engine-kit 依赖**；不装 form pages；console/swagger 根级保持 |

**每仓验证清单（统一）**：
1. `cargo check` + `cargo clippy`；
2. **路由契约守护测试**：以静态清单断言全量挂载路径——清单**以改造前 bin main.rs 逐条抄录为准生成、改造前先跑绿一次**（避免清单与实施者对装配的同一误解同源），改造后不变即零回归；
3. git diff 审查中间件挂载层级、层序与免认证面不变；
4. launcher 冒烟（大盘 / `/_mon` / openapi.json / 一条业务接口 / 页面投递）；
5. 改 cmx-rulesengine 后到 cmx-data-auth 补一次 `cargo check`（其依赖 rule-feel/rule-model/rule-engine，本方案虽不碰，仍按规程复核）。

### 收尾

- 根仓 `documents/` 归档实施记录（本方案追加附录）。
- 全程不 push，等待用户明确指令；各仓独立提交可独立回滚。

---

## 五、风险与对策

| # | 风险 | 等级 | 对策 |
|---|---|---|---|
| 1 | trait 泛型化动 34 处 impl（含 portalservice）+ PlatformModules | 低 | 纯机械、编译器全量兜住；api-core re-export 保导入路径不变；portalservice 独立提交 |
| 2 | 引擎切片归属搞错（auth 罩到免认证面，或反之把受保护端点挪出认证面） | 中 | §3.3 逐仓归属表（model/mdm 的 stats/pages 明确留 authed）+ git diff 审查 + **全量路由契约测试**（不再是采样对账） |
| 3 | flow/rules/onto/**dataauth** v1 双挂载被去重守卫误杀 | 低 | 双模块不同 module_name（`xxx.core`/`xxx.v1`），试点仓先行验证 |
| 4 | engine-kit 引入 utoipa 拖重引擎编译 | 低 | 直写 `default-features = false`（合法写法，见 §3.1 定案），跨仓零特性；`cargo tree` 复核 |
| 5 | dataauth「刻意不引 utoipa」的立场 | 低 | 依阶段 2 将产生**传递依赖**（随 engine-kit）但零直接使用、零 derive；如实记录，不宣称完全避免 |
| 6 | 改 cmx-rulesengine 影响 cmx-data-auth（其依赖 rule-feel/rule-model/rule-engine） | 低 | 本方案只动 cmx-rule-app 与 bin，不碰那三个 crate；事后到 data-auth 补 `cargo check`（§四阶段 2 第 5 条） |
| 7 | 各引擎仓独立 workspace 的 lockfile / 依赖树漂移（report/ontology/data-auth 首次拉入 utoipa 子树） | 低 | lockfile 随各仓改造提交携带（§四阶段 0 归属策略）；首次 check 提前暴露编译问题 |
| 8 | model/mdm 的 observe/auth 层序被统一模板翻转，遥测身份归属变化 | 中 | 层序两态写死在 §3.3 表格（auth → observe），diff 审查专项核对；如要有意识统一须单独评审 |
| 9 | 7 仓一次性全改回滚困难 | 中 | 三阶段推进，每仓独立提交；阶段 1 试点通过才进阶段 2 |
| 10 | 平台/前端行为变化 | 低 | 纯装配重构：路径、中间件、免认证面逐一保持；前端零改动；路由契约测试全量兜底 |

---

## 六、明确不做（边界）

- **不动** `xxx_routes::<S>()` 自由函数——它们是「一芯多壳」的路由真源（引擎 bin 与平台壳双消费），模块适配器只是薄封装。
- **不动** `cmx-web-chassis`——纯 HTTP 服务器壳定位不变（nest_api / _mon / default_layers / 优雅停机）。
- **不补** report/model 的 swagger、各引擎统一 /health——用 `api_doc()` / 模块槽位把位置留好，但实现另立项。
- **不模块化**根级边角路由（大盘 / docs / console）——它们是主应用特有部分，归组合根手写。
- **不给 dataauth 装配 form pages**——现状没有，装配新增免认证路由属行为面扩大，不在本次范围。
- **不改** model/mdm 的 stats/页面认证归属——现状在 auth 层内就留 authed；如业务要求公开，走认证白名单配置另案评审。
- **不含** cmx-agent（无 HTTP 端口）与门户侧 core_kit 清单调整（上次改造已完成）。
- **不改**任何 handler / 业务逻辑 / 请求路径。

## 七、成本估算

- 阶段 0：约 0.5 天（含 8 仓验证与双 feature 态）。
- 阶段 1：约 0.5 天（含路由契约测试落地与冒烟）。
- 阶段 2：每仓 2~3 小时 × 6（含各自契约测试），约 1.5 天。
- 合计约 2.5~3 天，9 次子仓提交（container 1 + portalservice 1 + 7 引擎仓各 1）+ 1 次根仓文档提交。

---

## 附录 A：7 仓 bin 装配明细（调查原文浓缩）

**flow（main.rs:69-94）**：`flow_routes_v1::<()>()` + `.merge(flow_routes::<()>())` + observe/auth 两层（auth 在外）→ api_router = authed + `frontend_pages_routes::<(), FlowError>(from_assets())`（auth 外，无 observe 层）；app = `/` dashboard + nest `/api`；SwaggerUi 挂**真·bin 根级**（完整外部路径 `/api/flow/v1/docs`，规避尾斜杠重定向，main.rs:90-93）。无 health。

**report（main.rs:68-85）**：`report_routes::<()>()` + `consol_routes::<()>()` + observe/auth 两层；open = `/rpt/stats` + form pages（仅 observe 层）；app = `/` dashboard + nest `/api`。无 swagger、无 health、零 feature。

**model（main.rs:80-95）**：`model_routes` + `dct_routes` + `doc_routes` + `code_routes` + `/model/stats` + form pages **全在同一 api_router**，后挂 auth → observe（observe 在外）；app = `/` dashboard + nest `/api`。stats 与 pages 均在 auth 层内，白名单内置为空。四表内部子表（definitions / flexible-combination / deploy）可见。

**rules（main.rs:56-76）**：`rule_routes_v1::<()>()` + `rule_routes::<()>()` + observe/auth 两层；api_router += form pages（html Disabled，auth 外，无 observe 层）+ `/rules/v1/openapi.json`（挂 api_router、authed 之外，URL 含 `/api` 前缀）；app = `/` dashboard + nest `/api`。openapi 骨架占位。

**mdm（main.rs:63-74）**：`mdm_routes::<()>()`（内含 8 子表 + `/mdm/health`）+ `/mdm/stats` + form pages **全在 auth 层内**（auth → observe，observe 在外）；app = `/` dashboard + nest `/api`。MdmApiDoc 死代码预留。

**onto（main.rs:52-76）**：`onto_routes_v1::<()>()` + `onto_routes::<()>()` + observe/auth 两层；api_router += form pages（Disabled，auth 外，无 observe 层）+ `/onto/v1/openapi.json` + `/onto/v1/docs`（均挂 api_router、authed 之外，URL 含 `/api` 前缀）；app = `/` dashboard + nest `/api`。Outbox 钩子。

**dataauth（main.rs:59-76）**：`dataauth_routes_v1::<()>()` + `dataauth_routes::<()>()`（同一 inner 表；内部 open/admin(require_admin 整层)/demo(pep guard) 三分）+ observe/auth 两层；api_router **无 form pages**，另挂 `/dataauth/v1/openapi.json`（authed 之外，URL 含 `/api` 前缀）；app = `/` + `/console` + `/swagger`（真·bin 根级）+ nest `/api`。唯一未依赖 engine-kit 的仓。

## 附录 B：各仓模块适配器规划（含认证归属）

| 仓 | module_name | prefix | routes 来源 | 切片归属 |
|---|---|---|---|---|
| flow | `flow.core` / `flow.v1` | `/flow` / `/flow/v1` | flow_routes / flow_routes_v1 | authed |
| report | `rpt.core` / `rpt.consol` | `/report-*` / `/consol/*` | report_routes / consol_routes | authed |
| report | `rpt.stats` | `/rpt/stats` | dashboard::rpt_stats | **open**（现状免认证，7 仓唯一） |
| model | `model.core` / `model.dct` / `model.doc` / `model.code` | `/model/*`+`/definitions/*`+`/flexible-combination/*` / `/dct/*` / `/doc/*` / `/code/*` | 四张路由表 | authed |
| model | `model.stats` | `/model/stats` | dashboard::model_stats | **authed**（现状在 auth 层内） |
| mdm | `mdm.core` | `/mdm/*` | mdm_routes（8 合 1 含 health） | authed |
| mdm | `mdm.stats` | `/mdm/stats` | dashboard::mdm_stats | **authed**（现状在 auth 层内） |
| rules | `rules.core` / `rules.v1` | `/rules` / `/rules/v1` | rule_routes / rule_routes_v1 | authed |
| onto | `onto.core` / `onto.v1` | `/onto` / `/onto/v1` | onto_routes / onto_routes_v1 | authed |
| dataauth | `dataauth.core` / `dataauth.v1` | `/dataauth` / `/dataauth/v1` | dataauth_routes / dataauth_routes_v1 | authed |
| 6 仓共用 | `form.pages`（cmx-form 提供） | `/native-pages*`、`/html-pages*` | frontend_pages_routes::<S, E> | flow/report → open；**model/mdm → authed**；rules/onto → open（Disabled）；dataauth 不装 |

## 附录 C：审查修订记录

**v2.0（2026-09-16，第一轮对抗审查后修订）**

| 编号 | 问题 | 处置 |
|---|---|---|
| P0-1 | 「stats 现状免认证」对 5/7 仓不成立；model/mdm 的 stats 与页面投递现状在 auth 层内，照搬 report 切片会扩大认证面外暴露 | 重写 §3.3 切片规则为「按仓现状归属」；附录 B 增认证归属列；§六新增不改认证归属边界 |
| P0-2 | dataauth 也有 v1 双挂载，附录 B 漏 `DataAuthV1Module`，照表实施丢失 `/api/dataauth/v1/*` 全量路由 | §2.1 矩阵、§3.3、附录 B 补 dataauth.core + dataauth.v1 |
| P0-3 | utoipa「workspace 继承 + default-features=false」是非法 Cargo manifest | §3.1 定案：engine-kit 直写依赖（不继承），附缘由；风险 #4 同步改写 |
| P1-1 | model/mdm 的 observe/auth 层序与其余 5 仓相反，统一模板会翻转遥测身份归属 | §2.1 增层序两态表；§3.3 增层序列；风险 #8 新增 |
| P1-2 | impl 计数「34 文件 39 处全部在 container」不实：实为 container 33 + portalservice 1 | §2.3、§3.4、阶段 0 清单修正，portalservice 独立提交 |
| P1-3 | 「model api-core 在树」不实（cargo tree 无匹配）；engine-kit 变更影响 6 仓未全覆盖验证 | 阶段 0 验证改「api-core 面（container+portalservice）+ engine-kit 面（6 引擎仓）」 |
| P1-4 | form.pages「全引擎共用」对 dataauth 不成立（其不挂页面投递） | 附录 B 标注 6 仓；§六明确不给 dataauth 装配 |
| P1-5 | 风险表缺 lockfile 漂移、portalservice 波及、路由对拍强度不足 | 新增风险 #7；阶段 0 增 lockfile 归属策略；每仓验收改全量路由契约测试（flow-app api_contract 先例） |
| P2-1 | 附录 B rpt.stats prefix 误写 `/rpt/compute` | 已改 `/rpt/stats` |
| P2-2 | report 示例 open 切片漏 observe 层 | 示例已补 `.layer(observe)` |
| P2-3 | FormPagesModule 签名缺 S 约束、未支持 Disabled 配置 | §3.3 签名补全；构造器接受完整 PageServeConfig，rules/onto 传 Disabled |
| P2-4 | PlatformModules::new(items) 现状绕过查重，「行为不变」需注明 | §3.2 明确 new 不查重语义保留、逐方法对号 |
| P2-5 | 「dataauth 不实现 api_doc 即不引 utoipa」表述不实（传递依赖仍在） | 风险 #5 如实改写为传递依赖零直接使用 |

**v2.1（2026-09-16，第二轮复核后修订——首轮 13 项处置经逐条复核全部通过）**

| 编号 | 问题 | 处置 |
|---|---|---|
| P1 | rules/onto/dataauth 的 openapi.json 实际挂 api_router（authed 外、nest /api 内）而非「bin 根级」，照原文实施会丢 `/api` 前缀致消费方 404 | §3.3 特殊形态与附录 A 三仓改写为「api_router 上、authed 子树之外，URL 含 `/api` 前缀，不得挪 app_router」；仅 flow SwaggerUi 与 dataauth `/console` `/swagger` 标注真·bin 根级 |
| P2-1 | 阶段 1 给 flow open 切片加 observe 属新增层（flow 现状 open 无任何层） | 阶段 1 改为保持现状不加；§3.3 与附录 A 增「open 无 observe（仅 report 有）」注记 |
| P2-2 | 成本算术 8≠9（container + portalservice + 7 引擎仓） | §七改 9 次子仓提交；阶段 0 标题明确 2 次提交 |
| P2-3 | 「跨仓零特性最小面」措辞过宽——flow/rules/model/mdm 四仓自身 workspace 已带 macros，特性并集后仍含 utoipa-gen（既有状态） | §3.1 收窄为「engine-kit 自身边零特性；report/ontology/data-auth 三仓整体零特性；其余四仓保持既有特性面不变」 |
| P2-4 | 路由契约测试的静态清单需权威来源（flow-app api_contract 先例是 *-app defs 级，不覆盖 bin 装配面） | 阶段 1/2 验证明确「清单以改造前 bin main.rs 逐条抄录生成、改造前先跑绿一次」，防清单与实施误解同源 |
| 备注 | 附录 B model.core prefix 漏 `/definitions/*`、`/flexible-combination/*` | 已补全（prefix 仅诊断元数据，不参与挂载） |

**第二轮复核结论**：v2.1 无遗留问题，达到可实施标准（完整、逻辑严密、可行、风险可控）。

**遗留业务疑点（不阻塞实施，按保守默认处理）**：model/mdm 的 stats 与页面投递现状在认证层内但大盘 HTML（免认证）又在轮询它们——生产 jwt 模式下大盘应取数失败。本方案按「严格保持现状」处理（留 authed）；若业务上确认二者应公开，另行在认证中间件白名单补条目（engine-kit 已支持前缀匹配），不动装配结构。

## 附录 D：实施记录（2026-09-16）

**分支策略**：9 个子仓（container / portalservice / 7 引擎仓）在 `feat/route-assembly-unify` 分支开发，验证通过后合并回 `main`，删除特性分支；未 push（等用户明确指令）。

**落地与 v2.1 的差异（实施期代码级修正，两处，均为编译器/测试当场抓住）**：
1. `FormPagesModule<E>` 在引擎仓首次编译暴露 `PhantomData<E>` 随 E 退化 Send/Sync——impl 补 `E: Send + Sync` 约束（引擎错误类型本就满足，零语义影响）。
2. 契约测试模块补 `use axum::Router`（report 首跑 E0425 抓出；flow 试点用全限定名未踩）。

**验证矩阵（全部通过）**：
- `cargo check`：container workspace、portalservice（默认 + dev-tools 双态）、六引擎仓 workspace；
- 路由契约测试 25 个：flow 4 / report 4 / model 3 / mdm 3 / rules 4 / onto 4 / dataauth 3；
- engine-kit 单元测试 7 个（含去重 panic 与 openapi 种子）；
- clippy 溯源：六 bin/app **零条** warning 落在新改代码（rules/dataauth 全仓零 warning，其余为依赖仓既有）。

**遗留（不阻塞）**：model/mdm 的 stats 与页面投递保持 authed 现状（业务如需公开走认证白名单另案）；report/model 的 swagger 缺失与引擎统一 /health 留 `api_doc()` 槽位另立项。
