# cmx-platform-app 路由装配倒置与模块组合方案

> 日期：2026-09-16 · 状态：**已实施**（2026-09-16 完成 W1→W5 全部代码落地，实施记录见文末附录）
> 前身：同日《cmx-common-api_门户HTTP层反向依赖解耦方案》被本总体方案吸收取代（该文档未提交即改写）
> 范围：`backend/cmx-container`（cmx-api-core / cmx-platform-app / cmx-common-api + 34 处 impl 签名）+ `backend/cmx-portalservice`（新 crate cmx-portal-api / bin 组合根）
> 迁移节奏：**一步到位**（静态清单一次性删除，全部改走 bin 组合；commit 序列内部仍分步便于 review）

---

## 一、背景与问题

### 1.1 装配现状：同一份知识，三处两张表

```
cmx-portal-server (portalservice 仓, bin)
    └── cmx-platform-app (container 仓, "平台总装配器")
            ├── routes()                  静态 merge 17 个模块        routes.rs:434-450
            ├── merged_openapi()          静态 merge 7 个 ApiDoc      routes.rs:471-483
            └── cmx-common-api::api_routes()
                    ├── service::ServiceModule                        routes_impl.rs:47
                    ├── debug::DebugModule（无门控！生产也挂）           routes_impl.rs:50
                    ├── portal::PortalModule                           routes_impl.rs:55
                    ├── dev::DevModule（#[cfg(feature = "dev-tools")]）routes_impl.rs:63
                    └── /health（实际 URL /api/health，见 §4.7）        routes_impl.rs:67
            另：8 个引擎反代经 merge_* 辅助条件装配（routes.rs:245-261 等），其中 7 个
            在配置反代时还要对整棵路由器叠「页面反代中间件」（§4.4，这是纯 merge 表达不了的结构）
```

同时存在反向依赖：container 经根 `Cargo.toml:207` 跨仓 path 引用 portalservice 仓的 `cmx-portal`
业务库，唯一消费方 `cmx-common-api/Cargo.toml:56`——门户 HTTP 层（handlers/portal，42 个 handler）
在 P-S1 迁移业务层时掉队留在了 container，原因是当时 bin 侧没有路由注入通道。

### 1.2 问题清单（有实证）

| # | 问题 | 实证 |
| --- | --- | --- |
| 1 | **知识分裂**：加一个模块要动 2-3 处（路由表 + 文档表），漏一处即「有路由没文档」 | 上表三处静态清单；现状 portal 有 doc、8 个 Proxy/service/debug 没有 |
| 2 | **库在做装配**：cmx-common-api 是公共库，却在 `api_routes()` 里 merge 业务模块——库应「提供模块」，不该「决定挂载」 | routes_impl.rs:47/50/55 |
| 3 | **bin 无裁剪权**：部署面锁死在库代码里，换部署形态只能改库重新编译 | 上述清单对任何 bin 生效 |
| 4 | **调试面失控**：`DebugModule` 无门控挂载，生产二进制带调试端点（前端四仓 grep 零消费方，见 §4.6）；`DevModule` 靠 feature 门控——feature 是编译期全局开关，粒度过粗（其注释自述「违反集群无状态约束，生产禁用」） | routes_impl.rs:50、:62-69 |
| 5 | **反向依赖**：上游公共库仓 → 下游业务仓 | container Cargo.toml:207 |

### 1.3 地基已经在了

全 container 已有 **34 个参与编译的 `impl ModuleRoutes`**（另有 1 处死代码 PluginControlModule，
其 `pub mod control;` 被注释未编译，随本方案删除）——Auth/Iam 聚合/Ai/Biz 6 件/Plugin/Storage/Job/
Service/Debug/Dev + 8 个引擎 Proxy + Portal。trait 早已是事实上的模块契约，**要反转的只是装配点**：
从「库内部静态 merge」倒置为「bin 收集、平台 fold」。

---

## 二、目标与非目标

**目标**

1. 装配倒置：platform-app 只认 `ModuleRoutes` trait，不认识任何具体模块；静态清单（17 + 4 + 7）一次性删除；
2. 组合根在 bin：门户进程挂了哪些路由，`main.rs` 一目了然；部署面可按 bin 裁剪；
3. 常用组合预置（kit）：底层通用模块预组合，bin 一行取用，不每次手列；
4. 路由与 OpenAPI 文档一体注册，消灭双表漂移；
5. 反代页面拦截等横切层收进契约（`wrap_router` 钩子，§4.4），条件装配语义保持；
6. 顺带收口：`DebugModule` 生产面治理（§4.6，唯一有意的行为变化）；
7. container → portalservice 反向依赖归零（portal HTTP 层迁 portalservice）；
8. 运行时路由行为零变化（除 §4.6 一项），前端零影响。

**非目标**

- 不迁 `cmx-portal` 业务库本体（它 path 回 container 基础库，方向合法）；
- 不做 P-S4 的 HTTP 反代化（portal-server 独立进程 + service_rpc 反代）；
- 不动 `portal_routes::<S>()` 泛型设计与 handler 全局单例访问模式；
- 不动 router.rs 两处根级条件装配（dataauth `/console` 整页反代 router.rs:67-73、agent-updates
  边缘端点 router.rs:81-89）——二者非 ModuleRoutes 形态，划为底盘 infra 保留；
- gRPC `rpc_bundles` 静态清单（lib.rs:171-174）与本次双表病同构，但属 RPC 域，列入后续演进（§10）；
- 不改引擎仓（已核实：8 仓无 `impl ModuleRoutes`、不调 `run_platform`；cmx-model-app 已显式去
  api-core 依赖）。

---

## 三、目标架构

### 3.1 trait：对象安全化 + 文档一体注册 + 横切包装钩子

```rust
// cmx-api-core（现行定义在 routes::traits，routes(self) + 无 self 的 prefix() 非对象安全）
pub trait ModuleRoutes: Send + Sync {
    /// 模块全部路由（全路径，含业务前缀；由装配方 merge）
    fn routes(&self) -> Router<CmxAppState>;            // self → &self
    /// 模块标识（仅诊断元数据；现状零挂载用途，保持语义不变；另用于组合查重）
    fn prefix(&self) -> &'static str;                   // 增加 &self 接收者
    fn module_name(&self) -> &'static str;
    /// 模块的 OpenAPI 文档（无则 None；路由+文档一体注册，消灭双表）
    fn api_doc(&self) -> Option<utoipa::openapi::OpenApi> { None }
    /// 全量装配后的整路由器包装钩子（默认恒等）。
    /// 用于跨模块横切层：引擎页面反代（拦截 /native-pages/{id}、/html-pages/{id} 中
    /// 属主引擎的取页请求，未命中落回门户内嵌）。纯 merge fold 无法表达这类
    /// 「作用于他人路由上的中间件」，故以钩子显式入约。
    fn wrap_router(&self, router: Router<CmxAppState>) -> Router<CmxAppState> { router }
}
```

### 3.2 可组合集合 + 预置套件（kit）

```rust
// cmx-platform-app
pub struct PlatformModules { items: Vec<Box<dyn ModuleRoutes>> }

impl PlatformModules {
    pub fn new(items: Vec<Box<dyn ModuleRoutes>>) -> Self;
    pub fn with(mut self, m: Box<dyn ModuleRoutes>) -> Self { self.items.push(m); self }
    pub fn merge(mut self, other: PlatformModules) -> Self;

    /// 预置套件——生产必挂的平台底座（15 个模块）：
    /// AuthModule / IamModule / AgentModule / AgentUpdatesModule / StorageModule /
    /// JobModule / ServiceModule + 8 个引擎 Proxy（Flow/Report/Rules/Onto/Model/Mdm/Meta/DataAuth，
    /// 路由自门控 + wrap_router 自门控）
    /// 注意：构造 Proxy 需读服务定位全局（OnceLock），**必须在 init_infra 之后调用**
    /// （生产路径一律经 run_platform 的工厂闭包，时机由签名保证）。
    pub fn core_kit() -> Self;

    /// 预置套件——开发工具（仅开发 bin 显式取用，整体 #[cfg(feature = "dev-tools")]）：
    /// DebugModule / DevModule（DevModule 的启动期 warn 日志随迁）
    #[cfg(feature = "dev-tools")]
    pub fn dev_kit() -> Self;
}
```

**查重护栏**：`with` / `merge` 时按 `module_name()` 查重，重复即启动期 fail-fast——kit 与 bin 显式
双挂同一模块时，报错直接指名模块，而非等 axum 对重复路径 panic（axum-0.8.9 routing/mod.rs:48-52）。

### 3.3 组合根（bin）：惰性工厂，init 之后再装配

> **构造时机是硬约束**：服务定位全局是 `OnceLock`（cmx-service-rpc/src/lib.rs:271），由
> `init_infra` 末尾的 `cmx_service_rpc::init()` 安装，而 `init_infra` 在 `run_platform` **内部**
> 执行（lib.rs:75）。若在 main 顶部直接构造 core_kit，8 个反代的 `locator()` 全部返回 None、
> **静默不挂**。故 run_platform 接收「模块工厂闭包」，在全部 init 之后、build_router 之前调用。

```rust
// cmx-platform-app
/// 原：pub async fn run_platform(banner: BannerSpec) -> Result<()>（lib.rs:61）
pub async fn run_platform(
    banner: cmx_web_chassis::BannerSpec,
    build_modules: impl FnOnce() -> PlatformModules,
) -> Result<()>
// 内部：init_infra/缓存/数据源/存储等全部就绪后、build_router 之前调 build_modules()
```

```rust
// cmx-portal-server/src/main.rs —— 门户进程的完整路由面，第一次一目了然
cmx_platform_app::run_platform(banner, || {
    let modules = PlatformModules::core_kit()
        .with(Box::new(AiModule))
        .with(Box::new(DomainModule))
        .with(Box::new(ApplicationModule))
        .with(Box::new(MenuModule))
        .with(Box::new(SysDatasourceModule))
        .with(Box::new(FormModule))
        .with(Box::new(ModuleCrudModule))
        .with(Box::new(PluginModule))
        .with(Box::new(TableMetadataModule))
        .with(Box::new(MarketplaceModule))
        .with(Box::new(ModulePackageModule))
        .with(Box::new(PortalModule));      // 迁自 cmx-common-api，见 §4.5
    #[cfg(feature = "dev-tools")]
    let modules = modules.merge(PlatformModules::dev_kit());
    modules
})
.await
```

bin `Cargo.toml` 需声明 feature 转发（feature 是 per-crate 的，否则 `cfg!` 恒 false）：

```toml
[features]
dev-tools = ["cmx-platform-app/dev-tools"]   # platform-app 已有同名转发 feature（其 Cargo.toml:19-24）
# 开发构建：portal.sh 增加 --features dev-tools 透传
```

底盘 fold 逻辑：先逐个 `merge(m.routes())`（含 base 链上的 /health），再**按清单顺序**逐个
`router = m.wrap_router(router)`；Swagger = 底盘种子 ApiDoc + `api_doc()` 逐个 merge（§4.8）。

### 3.4 条件装配收进契约

- 8 个 ProxyModule 的 `routes()` 内部自查 `locator()`：未配置返回空 `Router`（merge 空 Router 是
  no-op，与现状「没配 `[service_rpc.services].*` 就不挂」一致）；
- 7 个有页面反代的 Proxy（flow/report/rules/onto/model/mdm/meta）另在 `wrap_router` 里自门控叠
  `with_*_page_proxy` 层（§4.4）；DataAuthProxyModule 无页面反代，无需实现；
- **删除范围仅限 routes.rs 内 8 个 `merge_*` 分支**；router.rs 的两处根级条件装配（dataauth
  console、agent-updates edge）非 ModuleRoutes 形态，保留为底盘 infra（§二 非目标）。

### 3.5 挂载语义零变化

- 继续 `merge` 全路径（现状即如此：`prefix()` 全仓零调用点，从不参与 nest），URL 不变、前端零影响；
- `/health` 保持注册在 fold 前的 base 链上（即 `/api` nest 之内，实际 URL 仍为 **`/api/health`**——
  V2 Dockerfile HEALTHCHECK 探的就是它，container/docker/V2/Dockerfile:275-76）；
- Swagger 壳、静态资源、`/_mon` 属底盘基础设施，不模块化，留 platform-app 自持。

---

## 四、关键设计决策

### 4.1 trait 对象安全化（`self` → `&self`）

现行 `fn routes(self)`（按值）与 `fn prefix() -> &'static str`（无 self 接收者）使 trait 非对象安全。
改为 `&self` 后 34 处参与编译的 impl 全部改签名，调用点不变（unit struct 值调用 `&self` 方法自动
取引用，如 `AuthModule.routes()`）。已抽查各类形态：8 个 Proxy impl 内部 `let proxy = self.inner;`
改为 `self.inner.clone()`（Arc 克隆，代价可忽略）；IamModule 内部子模块 merge、PortalModule 调
`portal_routes::<CmxAppState>()`、Debug/Agent/Storage/Job/Service/Ai 等 unit struct 均机械可行。

### 4.2 `api_doc()` 上 trait + 文档归属约定

路由表与文档表合成一张：新增模块只动 bin 一处。**归属约定**（避免共享切片的模糊性）：
每 crate 指定**一个 owner 模块**返回 `Some(doc)`，同 crate 其余模块返回 `None`——
IamModule 持 IamApiDoc（聚合先例）、AgentModule 持 AgentApiDoc、AiModule 持 AiApiDoc、
StorageModule 持 StorageApiDoc、BizApiDoc 由 DomainModule 持有
（覆盖 6 个 biz 模块）、PluginApiDoc 由 PluginModule 持有（覆盖 3 个 plugin 模块）、PortalModule 持
PortalApiDoc。utoipa merge 为浅比较（同 path/schema 命中即忽略后者），重复 merge 无害但以
paths 数量对拍兜底（§八）。

### 4.3 kit 三条护栏（「预组合」的正确姿势）

| 护栏 | 内容 | 防的是什么 |
| --- | --- | --- |
| 放对层 | kit 只能定义在 platform-app（装配底盘）；**严禁**放 cmx-common-api 或任何业务库 | 「库做装配决策」问题复辟 |
| 按部署面切 | `core_kit`（生产必挂）/ `dev_kit`（仅开发 bin 显式取用）两个面；**不做全家桶** | 调试端点混进生产面 |
| 查重 fail-fast | `with`/`merge` 按 `module_name()` 查重 | kit + bin 显式双挂 |

kit 的位置同时是「平台默认部署面」这一产品决策的唯一载体：改 kit = 改所有取用 kit 的 bin 的部署面，
集中、review 可见；需要完全自定义面的 bin 用 `PlatformModules::new()` 自列，不被 kit 绑架。

### 4.4 反代页面拦截层：`wrap_router` 钩子（本方案最关键的结构修正）

**现状机制**（第一轮审查发现，原稿误判）：7 个反代（flow/report/rules/onto/model/mdm/meta）在配置
反代目标时，除 merge 反代路由外，还要对**整棵已累积路由器**叠页面反代中间件
（`with_flow_page_proxy(router, ...)` = `router.layer(from_fn_with_state(...))`，cmx-flow-api/proxy.rs:196-203，
其余 6 处同构）——它拦截 `/native-pages/{id}`、`/html-pages/{id}` 中**属主引擎**的取页请求
（这些路由挂在 PortalModule 名下）。axum 语义：`Router::layer` 只包住当时已存在的路由，且 Proxy
不能自行注册同名页面路由（与 PortalModule 重复路径直接 panic）——**纯 merge fold 结构上无法表达**。

**方案**：trait 增加 `wrap_router` 钩子（默认恒等，§3.1），fold 分两段——先全部 merge，再按清单顺序
应用各模块的 `wrap_router`。7 个 Proxy 的实现：`locator()` 命中才构造 resolver 叠层，否则恒等返回。

**行为等价性论证**：与现状的真实差异只有两点——①各层包住的路由集合从「当时已 merge 的局部」
变为「全量」；②7 层相对顺序翻转（现状内层 onto → v2 内层 flow）。结论成立依赖两条前提：
各引擎页面归属谓词互斥（各 proxy.rs 的 `is_*_owned_page`，一个页面 id 只属一个引擎）且中间件对
非命中请求零副作用（仅 `next.run`）——两条均已核实成立。注意：**若未来两引擎页面 id 出现重叠，
模块清单顺序即成为语义**（先 wrap 者内层优先）。页面反代冒烟（§八.5）兜底验证。
`wrap_router` 在 build_router 期执行（惰性工厂保证），此时 `locator()`/ConfigManager 已就绪。

**启动告警随迁**：现 routes.rs 各 merge_* 的 None 分支各有一条 `tracing::warn!`
（:257/:285/:348/:372/:395/:414，补偿「静默不挂」可见性的有意设计）——自门控移入各 Proxy 模块的
`routes()`/`wrap_router` 时，**告警日志随之迁入**（未配置分支照发 warn），部署排障可见性不回退。

> 备选方案（若评审否决钩子）：页面反代层保留为 platform-app 底盘 infra（照抄现 merge_* 链），
> kit 只管 Proxy 路由模块——改动更小，但 platform-app 保留 7 处引擎引用，「倒置」不彻底。**默认按钩子方案实施。**

### 4.5 门户 HTTP 层迁移（原方案A内容，原样成立）

- 新 crate `cmx-portalservice/crates/cmx-portal-api`：handlers/portal 8 文件 + `PortalModule` +
  `portal_routes::<S>()` + `PortalApiDoc`（`PortalModule::api_doc()` 返回它，从此自带文档）；
  依赖 cmx-portal（同仓）/ cmx-api-core / cmx-api-types / axum / utoipa；
- import 机械改写（5 类符号，约 16 处 use 行）：7 个 handler 文件各含
  `use crate::middleware::CmxSvrContext;` + `use crate::{ApiResp, Result};`（7 处），mod.rs 含
  `use crate::app_state::CmxAppState;` + `use crate::routes::traits::ModuleRoutes;` 及 1 处文档注释
  引用——映射：`CmxSvrContext→cmx_api_core::middleware::`、`CmxAppState→cmx_api_core::app_state::`、
  `ModuleRoutes→cmx_api_core::routes::traits::`、`ApiResp/Result→cmx_api_types::`；
  `cmx_portal::` 的 99 处调用零改动（同仓 workspace 直引）；
- container 侧删除：handlers/portal 目录、`PortalApiDoc`（openapi.rs:137）、routes_impl.rs:55 merge、
  `Cargo.toml:56` 依赖、根 `Cargo.toml:207` workspace 别名；死代码 `cmx-plugin-api` 的
  `handlers/plugin/control/` 一并删除（`pub mod control;` 本就被注释）。

### 4.6 DebugModule 生产面收口（唯一有意的行为变化）

现状 `DebugModule` 无门控挂载（routes_impl.rs:50，调试会话查询端点），生产二进制自带。
本方案将其移入 `dev_kit()`：生产 bin 不再挂载。**收窄前已核实**：frontend 四仓 grep
`/api/debug`、`/debug/current` 零命中，container assets 无引用；实施前对 cmx-agent 桌面端补一轮
grep 定案。附带声明：现状 dev-tools 开启时 Debug+Dev 都在、关闭时仅 Debug 在；方案后两者统一由
`dev-tools` 单开关控制——这是有意收窄。若后续发现生产消费方，该 bin 显式 `.with(DebugModule)` 即可。

### 4.7 /health 保持 `/api/health`

`/health` 在 api_routes() 内注册（routes_impl.rs:67），而 api_routes 被 `nest("/api", ...)`
（router.rs:39）——实际 URL 是 **/api/health**，V2 Dockerfile HEALTHCHECK 依赖它。解散 api_routes 时
该路由移入 platform-app fold 的 base 链（仍在 /api nest 内），URL 不变；冒烟项按 /api/health 执行。

### 4.8 Swagger 种子文档归属

现状 Swagger = 基础 `ApiDoc::openapi()` 作种子（携带 info/title/version、Pagination schema 及
ServiceModule 全部 paths，openapi.rs:8-71）+ merge 7 片。utoipa merge **不合并 info 字段**——种子
不可省。方案：基础 ApiDoc 原样保留为底盘种子（platform-app 自持），模块文档经 `api_doc()` 叠加，
行为与现状逐字段一致；ServiceModule 的 paths 暂留种子（后续可下沉为 `ServiceModule::api_doc()`，
列入 §10 演进）。

### 4.9 服务拓扑面板（service_topology）

`service_topology()`（routes.rs:119-231）硬编码镜像 routes() 装配决策（监控面板数据源）。fold 化后
其注释失效：方案将其**定义为与 core_kit 绑定的底盘能力**（适用边界：取用 core_kit 的 bin），
从 PlatformModules 装配结果派生列为后续演进（§10）。

---

## 五、分文件改动清单（一步到位，按 commit 序列）

| # | 仓 | 文件 | 动作 |
| --- | --- | --- | --- |
| W1 | container | `crates/libs/cmx-apis/cmx-api-core/src/routes/traits.rs` | trait 对象安全化 + `api_doc()` / `wrap_router()` 默认方法 |
| W2 | container | 34 处参与编译的 `impl ModuleRoutes` 所在文件 | 签名 `routes(self)`→`routes(&self)`、`prefix()`→`prefix(&self)`；Proxy impl 内 `self.inner` 改 `self.inner.clone()`（机械，调用点不变） |
| W2 | container | `crates/libs/cmx-apis/cmx-plugin-api/src/handlers/plugin/control/` | 删除死代码（`pub mod control;` 本被注释） |
| W3 | container | `crates/libs/cmx-platform-app/src/lib.rs` | `run_platform(banner, build_modules: impl FnOnce() -> PlatformModules)`（惰性工厂，§3.3）；`PlatformModules`（new/with/merge/core_kit/dev_kit/按名查重）；rpc_bundles 不动（§10） |
| W3 | container | `crates/libs/cmx-platform-app/src/routes.rs` | 删 17 模块静态 merge（:434-450）与 7 doc merge（:472-482）及 `PortalApiDoc` import（:7）；改两段式 fold（merge → wrap_router）；8 个 `merge_*` 分支删除（Proxy 路由自门控 + wrap_router 自门控，None 分支 warn 告警随迁 §4.4）；`service_topology()` 改注释为 core_kit 绑定（§4.9）；保留 infra（/api/health、swagger 壳 :485-486、静态资源、/_mon、种子 ApiDoc §4.8） |
| W3 | container | `crates/libs/cmx-platform-app/src/router.rs` | 不动（nest("/api") :39、dataauth console :67-73、agent-updates edge :81-89 均保留） |
| W4 | container | `crates/libs/cmx-apis/cmx-common-api/src/routes/routes_impl.rs` | `api_routes()` 解散：service/debug/dev 的 merge 移交 bin 组合，/health 移交 platform-app base 链（§4.7）；附带清理无调用方的 `swagger_routes()`（:83） |
| W4 | container | `crates/libs/cmx-apis/cmx-common-api/src/handlers/portal/` 等 | 按原方案A删除/迁移（§4.5） |
| W4 | container | `Cargo.toml` | 删 ：207 `cmx-portal` workspace 别名 |
| W5 | portalservice | `crates/cmx-portal-api/**` | 新增 crate（§4.5） |
| W5 | portalservice | `Cargo.toml` | members + `[workspace.dependencies]` 补组合根**直接**依赖：cmx-ai-api / cmx-biz-api / cmx-plugin-api / cmx-portal-api（Agent 两模块由 core_kit 经 platform-app 提供，bin 无需直依赖 cmx-agent-api；§3.2/§3.3） |
| W5 | portalservice | `crates/cmx-portal-server/Cargo.toml` | + `cmx-portal-api` 等依赖；+ `[features] dev-tools = ["cmx-platform-app/dev-tools"]`（§3.3） |
| W5 | portalservice | `crates/cmx-portal-server/src/main.rs` | 组合根惰性工厂（§3.3） |

> 下游 8 引擎仓零改动（已核实）。35 处 impl 中未上清单者已定案：RuleModule 经 IamModule 聚合挂载
> （iam/mod.rs:26）；PluginControlModule 死代码删除；其余为 Iam 内部子模块。

---

## 六、关键事实依据（评审可复核，第一轮审查已逐条核实）

| # | 事实 | 佐证 |
| --- | --- | --- |
| 1 | 34 处参与编译的 `impl ModuleRoutes`（35 处含死代码 PluginControlModule） | grep 计数 + `cmx-plugin-api/src/handlers/plugin/mod.rs:16`（`// pub mod control;`） |
| 2 | platform-app 静态 17 merge | routes.rs:434-450（:433 为 base 行） |
| 3 | api_routes 内 4 模块 + /health | routes_impl.rs:47（service）/ :50（debug，无门控）/ :55（portal）/ :63（dev，feature 门控）/ :67（/health，实 URL /api/health） |
| 4 | Swagger 聚合 7 doc + 种子 ApiDoc | routes.rs:471-483；PortalApiDoc merge 在 ：481 |
| 5 | `prefix()` 全仓零调用点 | grep `\.prefix()` 无命中 |
| 6 | `run_platform` 调用方唯一 | main.rs:36；签名 lib.rs:61 |
| 7 | cmx-portal 本体在 portalservice 仓 | container `Cargo.toml:207`；container 内唯一依赖方 `cmx-common-api/Cargo.toml:56` |
| 8 | `cmx_portal::` 调用 99 处全在 handlers/portal | ai7/data18/launcher2/legacy19 注释态/meta10/notify18/pages15/registry10 |
| 9 | portal handler 不读 AppState | portal/mod.rs 头注 + `portal_routes::<S>()` |
| 10 | handlers/portal 自引用 5 类符号 | CmxSvrContext×8（含 1 处注释）、{ApiResp,Result}×7 文件、ModuleRoutes×1、CmxAppState×1 |
| 11 | `PortalApiDoc` 外部消费者唯一 | routes.rs:7 与 ：481 |
| 12 | IamModule 聚合 User/Role/RoleGroup/Permission/Rule | iam/mod.rs:18-27；RuleModule 归属定案 |
| 13 | `swagger_routes()`（routes_impl.rs:83）死代码 | 全仓无调用方 |
| 14 | 8 Proxy 页面反代是整路由器 layer | cmx-flow-api/proxy.rs:196-203 等 7 处同构；DataAuthProxy 无 |
| 15 | locator 是 OnceLock、init 由 init_infra 末尾调用 | cmx-service-rpc/src/lib.rs:271/277/343；lib.rs:75 init_infra 在 run_platform 内 |
| 16 | /api nest 在 router.rs:39 | `/api/health` 为实际 URL；V2 Dockerfile:275-76 HEALTHCHECK |
| 17 | engine 仓零耦合 | 8 仓无 impl ModuleRoutes、不调 run_platform |
| 18 | 前端零消费 /api/debug | frontend 四仓 grep 零命中（node_modules/dist 除外） |
| 19 | container 与 portalservice 均为 edition 2024 | container Cargo.toml:112 —— edition 差异风险不存在 |
| 20 | utoipa merge 不合并 info；浅比较 | utoipa-5.5.0 openapi.rs:182-205 |

---

## 七、风险与对策

| # | 风险 | 对策 |
| --- | --- | --- |
| 1 | 一步到位 PR 大（trait 签名 ×34 + 底盘重写 + 跨仓迁移） | commit 序列按 W1→W5，每步可独立编译；review 按 commit 分片 |
| 2 | 路由行为回归（fold 顺序、Proxy 自门控、wrap_router 等价性） | 迁移前后**全量路由表对拍**（预期差异仅 DebugModule 段）+ Swagger paths 数量对拍 + 页面反代冒烟（反代模式下取一个属 flow 的 native 页验证转发） |
| 3 | DebugModule 收口影响隐性消费方 | §4.6：前端/资产已核实零消费，实施前补 cmx-agent 端 grep；必要时 bin 显式加回 |
| 4 | kit 复辟「隐藏清单」 | §4.3 三护栏 |
| 5 | feature 传播断裂（bin cfg! 恒 false / dev_kit 编译失败） | §3.3 三件套：bin [features] 转发、dev_kit 整体 #[cfg]、构建命令透传；CI 各跑一次开/关 feature 构建 |
| 6 | 惰性工厂时机错误（kit 在 init 前构造 → 反代静默不挂） | §3.3 签名强制 `FnOnce` 工厂；验证：反代配置模式下冒烟 /api/flow/* 可达 |
| 7 | utoipa 宏路径重写遗漏 | 编译器兜底 + openapi.json 对拍 |
| 8 | `cmx-portal-api` 发布语义 | bin 专属本地壳 crate，workspace path 引用、不发布 nora |

## 八、验证方案

1. **container**：`cargo check --workspace`（开/关 dev-tools 各一遍）；`cargo tree -i cmx-portal` 报 "did not match any packages"。
2. **portalservice**：`cargo check --workspace`（开/关 feature）；`cargo tree -i cmx-portal` 仍存在。
3. **全量路由对拍（核心验收）**：迁移前后导出完整路由表 diff——预期差异**仅 DebugModule 段**；`/api/health` 必须在列。
4. **Swagger 对拍**：`/api-docs/openapi.json` 的 info 与 paths 集合迁移前后一致（除 debug 段）。
5. **行为冒烟**（联调最小集 portal + model）：登录、workspace-nodes 增删查、form-pages、通知、`/api/agent/capabilities`、**`/api/agent/bindings`（P0-1 补测）**、SSE 建流、`/swagger-ui`、`/api/health` 200；反代模式（配 `[service_rpc.services].flow`）下取一个属 flow 引擎的 native 页验证页面反代转发。
6. **查重护栏自测**：故意双挂一模块，确认启动期按名报错。

## 九、回滚方案

纯编译期重构、无数据/配置/DDL 变更：两仓各一次 `git revert`（container 恢复 trait/静态清单/portal 层，
portalservice 删 cmx-portal-api、还原 main.rs）。commit 序列与 W1→W5 反序回退亦可逐级回退。

## 十、后续演进

1. **gRPC rpc_bundles 同款改造**（lib.rs:171-174 静态 Bundle 清单，与本次双表病同构）：移交 RPC 域另行立项，契约可复用 `PlatformModules` 形态；
2. **引擎仓收编**：flow/report 等未来统一到底盘时，同一契约直接复用；
3. **P-S4 反代化**：portal-server 独立部署后平台对门户段改 service_rpc 反代，bin 清单删 PortalModule 即可；
4. **聚合模块扩展**：Biz/Plugin 仿 IamModule 提供领域聚合，缩短 bin 清单；
5. **service_topology 从装配结果派生**（§4.9）；ServiceModule 文档从种子下沉为 `api_doc()`（§4.8）；
6. **handler 状态注入化**（可选）：多实例/多租户需求出现时再评估。

---

## 附录：修订记录

**v2（第一轮对抗性审查后）**——审查发现 3×P0、3×P1、4×P2、若干 P3，全部处置：

- **P0-1** 组合清单漏 AgentModule/AgentUpdatesModule（智能体域会静默 404）→ 纳入 core_kit（13→15），W5 补 cmx-agent-api 依赖，冒烟补 /api/agent/bindings；
- **P0-2** 反代页面拦截层是整路由器中间件，纯 merge fold 无法表达 → trait 新增 `wrap_router` 钩子（§3.1/§4.4），两段式 fold，备选方案（留底盘 infra）已注明；
- **P0-3** kit 构造早于 init_infra，locator() 全空致反代静默不挂 → `run_platform` 改收惰性工厂闭包（§3.3）；
- **P1** dev-tools feature 传播三件套补全（§3.3）；基础 ApiDoc 定为底盘种子（§4.8）；/health 钉死 /api/health（§4.7）；
- **P2** import 清单修正为 5 类符号（§4.5）；router.rs 两处根级条件装配划为 infra 保留（§3.4）；service_topology 处置（§4.9）；impl 基数修正 34 并删 PluginControlModule 死代码（§1.3/W2）；
- **P3** ApiDoc 归属约定（§4.2）；行号修正；edition 风险销项（两仓均 2024）；DevModule warn 日志随迁、Debug+Dev 单开关收窄声明（§4.6）。

**v2.1（第二轮复审后，复审结论：可实施）**——复审逐项确认三项 P0 修复与全部 P1/P2 处置成立，
v2 新增事实引用抽查全部准确；随后落实第二轮 5 条随手修订：

- [P2] 反代「未配置」启动告警随自门控逻辑迁入各 Proxy 模块（§4.4，防止部署排障可见性回退）；
- [P3] W5 依赖清单更正：bin 组合根直接依赖仅 4 个 `*-api`，Agent 两模块由 core_kit 经 platform-app 提供；
- [P3] §4.4 等价性论证改写为两点真实差异（层包住集合变全集、7 层相对顺序翻转）+ 两条前提
  （页面归属谓词互斥、中间件零副作用），并注明页面 id 重叠时清单序即语义；
- [P3] `core_kit()` 文档注明「须在 init_infra 之后调用」（§3.2）；
- [P3] 归属约定补 AiModule→AiApiDoc、StorageModule→StorageApiDoc（§4.2）。

---

## 附录二：实施记录（2026-09-16）

**全部代码落地完成，双仓编译验证通过。改动面：cmx-container 73 文件（+617/−3637，删 14 文件）；cmx-portalservice 5 文件修改 + 新增 crates/cmx-portal-api。**

| 工作流 | 落地内容 | 验证 |
| --- | --- | --- |
| W1 | `cmx-api-core/routes/traits.rs`：trait 加 `Send + Sync` 超界，`routes(self)`→`routes(&self)`、`prefix()`→`prefix(&self)`，新增 `api_doc()` / `wrap_router()` 默认方法 | ✅ |
| W2 | 34 处 impl 签名机械改造；8 个 Proxy 模块 `inner` 改 `Option<Arc<ProxyCore>>` + 新增 `detect(api_key)` 自门控构造（locator 检查 + 原 merge_* 的 info/warn 告警逐字随迁）+ `wrap_router` 叠页面反代层；删除 7 个 `with_*_page_proxy` 自由函数（lib.rs 再导出与 rustdoc 同步清理）；删除 PluginControlModule 死代码 | ✅ 17 crate 局部 check 绿 |
| W3 | platform-app：`PlatformModules`（new/with/merge 按 module_name 查重 + core_kit 15 模块 + dev_kit 2 模块整体 cfg 门控）；`routes()` 两段式 fold（/health 底盘自持 + 全量 merge + 按清单序 wrap）；`merged_openapi` 种子+切片聚合；`run_platform(banner, build_modules: impl FnOnce() -> PlatformModules + Send)` 惰性工厂（init 后调用点保证 locator 就绪）；`service_topology` 文档改 core_kit 绑定；onto_upstream 死代码清理 | ✅ 开/关 dev-tools 双态绿 |
| W4 | cmx-common-api：`routes_impl.rs` 整文件删除（api_routes/swagger_routes 解散，/health 移交底盘）、`handlers/portal/` 9 文件迁出删除、`openapi.rs` 仅存种子 ApiDoc、`Cargo.toml` 删 cmx-portal、container 根 `Cargo.toml` 删 workspace 别名 | ✅ `cargo tree -i cmx-portal` = did not match any packages |
| W5 | portalservice：新 crate `cmx-portal-api`（8 handler 零改动平移 + lib.rs 再导出保持 `crate::xxx` 路径不变 + openapi 路径去 `portal::` 段 + PortalModule 挂 api_doc）；workspace members/依赖（api-core/types/ai-api/biz-api/plugin-api + axum/utoipa/tokio/reqwest/futures/cmx-service-rpc 等）；portal-server 增 `[features] dev-tools = ["cmx-platform-app/dev-tools"]` 转发；main.rs 改组合根（core_kit + 12 应用模块 + dev_kit） | ✅ 双 feature 态全绿 |

**文档 owner 模块的 api_doc() 落位**：AiModule→AiApiDoc、StorageModule→StorageApiDoc、IamModule→IamApiDoc、DomainModule→BizApiDoc、PluginModule→PluginApiDoc、AgentModule→AgentApiDoc、PortalModule→PortalApiDoc（7/7 与原 merged_openapi 的 7 个 merge 一一对应）。

**实施中修复的脚手架缺陷**（不影响最终代码）：proxy 批量改造脚本首轮两处缺陷（自由函数删除正则的 `///` 跨行吞噬导致 7 文件截断、wrap_router 插入剥掉 impl 收括号、model info 消息花括号未转义、dataauth 文档行丢 `///` 前缀），均经编译错误定位后定点修复并补完整性断言（行数不降 + 锚点齐全）。

**DebugModule 收口定案**：frontend 四仓 + cmx-agent 桌面端 grep `/api/debug`、`/debug/current` 全部零命中——生产 bin 不再挂调试端点，无已知消费方受影响。

**验证矩阵**：container `cargo check --workspace` 绿（零告警）×2（默认/dev-tools）；portalservice `cargo check --workspace` 绿（默认/dev-tools）；下游 flowengine / model / mdm 逐仓 `cargo check` 绿（其余引擎经 grep 判定仅注释级引用，零实际依赖）；反向依赖消除硬证据（cargo tree 无 cmx-portal）；container 内 portal 引用零残留。

**待运行时验收**（需 DB/Redis 环境，非编译期）：起 portal-server 后全量路由表对拍（预期差异仅 DebugModule 段）、`/api/health` 200、`/api/agent/bindings` 冒烟、反代模式下 flow 页面转发冒烟、`/swagger-ui` paths 数量对拍、查重护栏自测（双挂启动报错）。
