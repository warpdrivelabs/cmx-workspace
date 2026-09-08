# CMX 微服务间调用统一框架方案（cmx-service-rpc + 契约 SDK）

> 日期：2026-08-31（批次二阶段三实施记录 2026-09-01 补记，见 §十三；阶段四降级同日，见决策 14；§六 #4 收尾同日，见 §十四；webhook 契约去 SDK 化同日，见决策 15 与 §十五） · 版本：**v2.5**
> 状态：已与用户确认三个决策点（配置段改名 `[service_rpc]`、gRPC 基座统一+REST 先行、契约 SDK 内容与依赖关系见 §二）；v2 新增决策见 §九；批次实施记录见 §十二（批次一）/ §十三（批次二·阶段三）/ §十四（批次一收尾·§六 #4）
> 涉及仓库：cmx-container（主体）、六个服务仓（跟随迁移）
> 前置：`20260831_cmx-后端_六服务微服务化评审报告.md`（P4 东向服务化、P5 mdm↔model 解耦的落地设计）
> 原则：**不考虑向后兼容，允许全部改造**（终态不留双轨；阶段内分批合入的中间提交除外，见 §七）；健壮性、简洁性优先；cmx 是框架产品，按企业级标准设计解耦/复用/扩展

---

## 一、目标与现状证据

### 1.1 用户需求（原话归纳）

1. 服务间调用**统一支持 REST 与 gRPC**：有的服务只支持 grpc、有的只支持 rest、有的两者都支持——两种传输一套心智模型；**但只用 REST 的服务不能被强塞 gRPC 依赖**（v2：feature 门控解决，见 §三.2）；
2. 把 `[center_client]` 相关代码抽出来，做成**微服务 REST 调用封装的基础库**；
3. **无注册中心时可回滚到默认 url 直连**；
4. 企业级全局考虑：合并/迁移/新建哪些 crate、如何协同；解耦、复用、可扩展；
5. SDK 化体验：**"某个服务增加一个依赖，就可以调用另一个服务的某些功能"**（对标 Spring Cloud OpenFeign / Dubbo API jar）；
6. 处理评审报告 P5 点名的两个跨仓依赖（cmx-dct-store-pg、cmx-code-api——**实际迁移闭包 ≥5 个 crate**，见 §七阶段三）。

### 1.2 现状证据（实地查证，经审查复核）

| 事实 | 证据 | 含义 |
| --- | --- | --- |
| 消费端 DTO 全部自造，无共享契约类型 | mdm `flow_client.rs`（11 个业务方法，imports 仅 serde_json/cmx_utils/cmx_traits）；report `flow_client.rs`（仅 `start_close_instance` 一个方法） | 契约目前是"隐式 JSON 对齐"，字段改名无编译期保护；也证明契约 SDK 可自包含 |
| **五引擎仓现状零 gRPC 依赖** | 六仓 Cargo.toml grep：cmx-plugin/cmx-common-api/cmx-rpc 全部零引用；volo 只经 portal 一条链进入构建（portal-server → cmx-platform-app → rpc feature） | 基座若硬带 volo，五个纯 REST 服务凭空引入 ~230 个额外编译单元（volo-grpc 依赖树实测）——**必须 feature 门控** |
| cmx-rpc 依赖成本 | `cargo tree` 实测：cmx-rpc 全树 **575** 个唯一 crate（volo-grpc 231、volo 113）；对照 cmx-registry-config 307、reqwest 176 | feature 不开则 volo 完全不进依赖图（六服务各自独立 workspace，feature unification 不跨仓生效） |
| container → 服务仓直接反向依赖仅一处，但**有传递链** | `cmx-container/Cargo.toml`：`cmx-portal = { path = "../cmx-portalservice/crates/cmx-portal" }`（消费方是 `cmx-common-api`）；而 cmx-portal → `cmx-model-meta`（path 进 cmx-model 仓）——构建 container 需两个服务仓在场 | "container 不依赖服务仓"红线要连传递链一起清偿（单列治理项，见 §六 #10） |
| `[center_client]` 段实际只存在于门户 | 仅 cmx-portalservice 3 份 toml（dev/100/正式）；**五引擎 toml 无此段**；config 四件套中：`.env.template` 是 `CENTER_CLIENT__` 前缀形式，CONFIG_MANUAL.md 与 config_template.toml 是 `[center_client]` 段名形式（docker.toml 无此段） | 配置迁移面 = 门户 3 份 toml **改名** + 五引擎**新增** + 四件套同步（见 §四.1 迁移清单） |
| mdm 现打旧路径，v1 契约存在但未被消费方使用 | mdm `flow_client.rs` 打 `/api/flow/instances`（无 v1）；flow 同时提供 `/api/flow/v1/instances`（cmx-flow-server/src/main.rs） | SDK 路径常量必须以 **v1 openapi.json 逐方法核对 JSON 形状**后定稿，不能照抄存量内联 JSON（两版形状可能不同） |
| mdm→cmx-model 两个 path 依赖的迁移闭包 | cmx-mdm 根 Cargo.toml 两处 path；`cmx-dct-store-pg` 依赖 `cmx-dct-model` + `cmx-model-meta`；`cmx-code-api` 依赖 `cmx-code-model`；`cmx-model-meta` 另被 cmx-doc-store-pg / cmx-model-app / cmx-model-deploy / **cmx-portalservice 的 cmx-portal** 依赖 | 阶段三实际要迁 **{cmx-dct-store-pg, cmx-dct-model, cmx-code-api, cmx-code-model, cmx-model-meta}** 5 个 crate，cmx-portal 引用跟随改 |
| `CodeMinter` trait 是异步的 | cmx-traits 的 `CodeMinter`：`#[async_trait]`（mint/mint_batch/record_gap_for_code）；`mint_dict_code` 调用点在 async 上下文 | 阶段四铸号远程化 trait 层面可行（但注意：`record_gap_for_code` 返回 bool、错误类型 String，跨服务需映射到 ServiceRpcError） |
| 服务间调用基础设施分散三处 | cmx-plugin/center_client（config+upstream+导入器）、cmx-infra/cmx-rpc（volo gRPC 双端）、各服务散装 reqwest | 合并/迁移主对象 |

---

## 二、核心设计理念

### 2.1 "暴露接口 = 提供 SDK 吗？"——是，且这是本方案的骨架

| Spring Cloud | CMX 等价物 | 说明 |
| --- | --- | --- |
| API module（接口 + DTO jar） | **契约 SDK crate**（`cmx-{svc}-sdk`） | 服务方发布、消费方依赖 |
| `@FeignClient` 接口 | SDK 里的 `trait XxxClient` | 方法签名即契约 |
| RestTemplate / WebClient | 基座 `cmx-service-rpc` 的 HTTP 传输（default feature） | 传输 + 信封解包 |
| gRPC stub | 基座的 gRPC 传输（**optional feature**） | 按需启用 |
| Nacos Discovery + LoadBalancer | `cmx-registry-config` 实例缓存 + 选例核 | 已有，复用 |
| `service.url` 直连（无注册中心） | `[service_rpc.services.{key}.url]` | **回滚路径，明确保留** |

消费方体验（目标代码）：

```rust
// cmx-mdm 里，Cargo.toml 加一行：cmx-flow-sdk = { workspace = true }（默认 feature = http-only）
use cmx_flow_sdk::{FlowClient, StartInstanceReq};

let flow = cmx_flow_sdk::client()?;       // 从全局服务目录解析 key="flow"，按 transport 配置选实现
let inst = flow.start_instance(StartInstanceReq { ... }).await?;
// Result<StartInstanceResp, ServiceRpcError>——发现/负载均衡/鉴权/超时/重试/解包全部由基座完成
```

### 2.2 依赖方向铁律（三条，根除"乱"）

```
                    cmx-api-types / cmx-utils（基础类型）
                                ↑
              cmx-infra/cmx-service-rpc（统一调用基座，默认 http-only）
                                ↑
    cmx-flow-sdk  cmx-model-sdk  ~~cmx-mdm-sdk~~  …（契约 SDK，各域组下；mdm-sdk 已移除，决策 15）
          ↑              ↑              ↑
   ┌──────┴─────┐  ┌─────┴─────┐  ┌─────┴────┐
   │            │  │           │  │          │
cmx-flowengine  cmx-mdm(消费)  cmx-model    cmx-report(消费)
(服务端半边实现)              (服务端半边)
```

1. **container 不依赖任何服务仓**（含传递依赖；现存违例 `cmx-portal`→cmx-model-meta 链单列治理，见 §六 #10）；
2. **服务仓 → container 严格单向**；
3. **服务仓之间零依赖**（消灭 mdm→cmx-model 的 path 依赖模式，验收标准之一）。

### 2.3 契约 SDK 里放什么、不放什么

**结论：契约 SDK 完全自包含，不引用任何服务方仓的内部类型。**

| 放（契约的全部内容） | 不放 |
| --- | --- |
| ① 服务键常量（`SERVICE_KEY = "flow"`） | 服务方内部领域模型（cmx-flow-model 的类型） |
| ② 路径常量（客户端拼 URL 与服务端挂路由**同源**；以 **v1 openapi.json 核对后**定稿） | 存储层、业务逻辑 |
| ③ 请求/响应 DTO（wire contract，只依赖 serde + cmx-api-types） | 数据库实体、内部配置 |
| ④ 客户端 trait + HTTP 默认实现（基于基座） | |
| ⑤ （按需）gRPC 绑定（proto stub 薄封装，依赖基座 grpc feature） | |

服务方 handler 做"契约 DTO ↔ 内部模型"的 `From/Into` 转换。**契约变更 = 改 container 一处，双方编译期立刻感知**；服务方内部重构不影响消费方。

### 2.4 async trait 选型（v2 定案）

契约 trait 统一用 **`#[async_trait]`（async-trait crate）**：workspace 已有 23 个 crate 在用（惯例一致）；SDK 需返回 `Arc<dyn FlowClient>`（dyn 兼容必需），原生 AFIT 的 dyn 支持仍需额外手段（dynosaur/手动 Box 化）——不引入新机制，沿惯例最稳。

---

## 三、Crate 布局：合并 / 迁移 / 新建 / 退役全清单

### 3.1 总图

```
cmx-container/crates/
  libs/cmx-infra/
    cmx-registry-config          【保留·微调】注册/配置中心 + 实例缓存 + 选例核
                                   （选例 API 公开化供基座消费；实例 metadata 扩展 transports/grpc_port）
    cmx-service-rpc              【★新建·核心】统一服务间调用基座
                                   ├─ 默认 feature：http（reqwest）+ 目录 + 门面 + 横切（零 volo 依赖）
                                   ├─ grpc-client（optional）：volo 客户端（吸收 cmx-rpc client/*）
                                   └─ grpc-server（optional）：gRPC 服务端设施（吸收 cmx-rpc server/*，
                                      仅 portal / 未来提供 gRPC 服务的引擎需要）
    cmx-rpc                      【退役】内容按 feature 拆入基座后删除（波及图见 §3.3）
  libs/cmx-plugin/               【瘦身】center_client 的 config/upstream 迁出；packer/types（DataCategory、
                                   ZIP 打包）留在 cmx-plugin（导入器语义）；remote_importers 改走基座门面
  libs/cmx-proxy-core/           【保留·不动】南北向反代核（与东西向调用职责分离）
  libs/cmx-flow/   cmx-flow-sdk   【★新建】flow 契约
  libs/cmx-model/ cmx-model-sdk  【★新建】元数据查询 + 铸号契约
  libs/cmx-mdm/   cmx-mdm-sdk    【已移除（2026-09-01，决策 15）】原 mdm webhook 回调契约——对外回调不以共享 crate 为载体，契约内联回 flow 侧 + 文档真源
  libs/cmx-rpt/、cmx-rule/       【预留】按需
  libs/（新组 cmx-dct/）          【★迁移·下沉】cmx-dct-store-pg + cmx-dct-model（自 cmx-model 仓）
  libs/（新组 cmx-code/）         【★迁移·下沉】cmx-code-api + cmx-code-model
  libs/（cmx-model-meta 归属）    【★迁移·下沉】cmx-model-meta（定义 JSON 读取层，mdm 激活落库的公共依赖，
                                   随闭包下沉；归属论证见 §七阶段三）
```

### 3.2 feature 矩阵与消费方组合（v2 核心，回答"REST-only 不背 gRPC 依赖"）

| feature | 引入依赖 | 内容 | 谁开 |
| --- | --- | --- | --- |
| `default = ["http"]` | reqwest + registry-config | 目录/定位/门面/鉴权注入/重试/熔断/可观测 | **所有消费方** |
| `grpc-client`（optional） | volo/volo-grpc + cmx-rpc-gen 产物 | Transport 的 gRPC 实现（discover/retry/auth_outbound/GlobalRpcClient） | 需要按 gRPC **调用**的服务 |
| `grpc-server`（optional） | 同上 + server 设施 | auth_layer/server_runner/bundle 注册 | **提供** gRPC 服务的服务（现仅 portal） |

- workspace 有强先例：`cmx-service-base` 的 `rpc = ["dep:cmx-rpc", ...]` 本身就是 optional 门控，flow 已用 `default-features = false` 惯例（注释明言"跨 ws 消费不膨胀"）；
- 六服务各自独立 workspace 构建，**feature unification 不跨仓生效**——report 不开 grpc feature，volo 完全不进它的依赖图（依赖成本对照：cmx-rpc 全树 575 crate / volo-grpc 231 vs reqwest 176）；
- SDK crate 依赖基座时 `default-features = false`，需要 gRPC 绑定的 SDK feature 透传；
- 目录校验联动：键配 `transport = "grpc"` 但进程未开 `grpc-client` feature → 启动报 `NoBinding` 类错误并提示开 feature（错配显性化，不静默）。

### 3.3 cmx-rpc 退役波及图（v2 补全，6 个消费方 + 生态件逐一去向）

| 现依赖方（Cargo.toml 实测） | 去向 |
| --- | --- |
| `cmx-service-base`（feature `rpc`，`init_rpc`） | init_rpc 改为构造基座（开 grpc-server/client feature 时）；feature 名保留、指向新 crate |
| `cmx-plugin`（remote_importers 的 grpc 分支） | 改走基座 `grpc-client`（feature 透传） |
| `cmx-common-api`（GlobalRpcClient 守卫引用） | 守卫改指基座（`grpc-client` feature 门控编译） |
| `cmx-platform-app`（直引 + bundle 注册点 `src/lib.rs` 的 OrchestratorBundle/ResourceDataBundle） | 改指基座 `grpc-server`；bundle 注册逻辑原样迁移 |
| `cmx-orchestrator-rpc`、`cmx-resource-rpc`（cmx-rpcs/ 皮肤 crate） | **保留独立**（业务 proto 皮肤），依赖从 cmx-rpc 改为基座 grpc feature；**仅 portal 构建链消费**（cmx-plugin/cmx-common-api 为非 optional 硬依赖，五引擎不消费） |
| `cmx-rpc-gen`（volo-build 生成工具） | **保留独立工具**，服务对象改为基座生态 |

### 3.4 协同关系

| 场景 | 参与方 | 时序 |
| --- | --- | --- |
| 服务启动 | `init_infra`（注册+实例缓存）→ **新增** `init_service_rpc`（读 `[service_rpc]`、构造门面、目录校验、订阅预热 discovery 键） | 校验不过按 §四.1 判定矩阵处理 |
| 消费方调用 | 业务代码 → 契约 SDK → 基座门面 → 定位（url 静态 \| 实例缓存选例）→ 传输（http \| grpc） | 全链路类型化 |
| 服务方暴露 | 服务仓依赖契约 SDK → handler 用契约 DTO + 路径常量挂路由 | 两端同源，编译期防漂移 |
| 门户反代 | ProxyUpstream 改从基座目录读**定位字段**；消费方共 4 处（cmx-platform-app/routes.rs、cmx-flow-api/proxy.rs、cmx-rpt-api/proxy.rs、cmx-rule-api/proxy.rs + cmx-common-api 的 pages.rs import） | 反代只取 url/discovery，不取 transport；配置一份目录两用 |
| 优雅停机 | shutdown_infra → 基座排空在途调用、注销实例 | 与现有 shutdown 钩子衔接 |

---

## 四、cmx-service-rpc 基座设计

### 4.1 配置（新段 `[service_rpc]`，取代 `[center_client]`；原 `[rpc]` 段并入）

```toml
[service_rpc]
default_transport = "http"   # http | grpc；键级可覆盖
timeout_ms = 30000           # 全局默认（东向调用无 SSE 长流，可用总超时；键级可覆盖）
retry_max = 1                # 仅幂等方法（GET/查询）+ connect 级错误换实例重试

[service_rpc.services]
# 服务键 → { url | discovery, transport, timeout_ms, retry_max }
# - url       = 静态基址（★无注册中心的回滚形态；与 discovery 并存时 url 优先——灰度切换语义）
# - discovery = Nacos 服务名（删 url 即切发现选例；transport=grpc 时必配）
flow  = { discovery = "cmx-flow-server" }
model = { url = "http://127.0.0.1:8093" }        # 回退直连示例
# env 覆盖：SERVICE_RPC__SERVICES__FLOW__URL（值带 scheme）

[service_rpc.server]         # 原 [rpc] 段并入（grpc-server feature 下生效；[service_auth] 段保留独立——
enabled = false              #   鉴权配置语义独立，被委托链广泛使用，不合并）
grpc_port = 0
warmup_services = []
```

**目录校验判定矩阵（v2 修正，取代"读不到段就 fail-fast"的粗表述）**：

| 情形 | 行为 | 理由 |
| --- | --- | --- |
| `[service_rpc]` 段缺失 | **空目录，合法**（全内嵌/零出站形态） | rules/model 等零出站服务根本不需要该段；现状 `CenterClientConfig::load()` 的"无段=空表=全内嵌"是合法形态，不能打崩 |
| 键已配置 `discovery` 但注册中心未启用、且无 `url` | **fail-fast**，启动报缺失键清单 | 静默 503 不可接受；显性提示"补 url 或开注册中心" |
| 旧段 `[center_client]` 残留 | **启动报错**并提示迁移命令 | 不做兼容读取（用户拍板），但错误信息可操作 |
| 键配 `transport = "grpc"` 但进程未开 grpc feature | fail-fast，报 NoBinding + 提示开 feature | 错配显性化 |

**配置迁移清单（实测面）**：
- 门户 3 份 toml（portal-server/-dev/-100.toml）：段改名 + `[rpc]` 并入（注意 dev/-100 的 onto、正式的 meta 等环境差异键同步核对）；
- 五引擎 toml：**新增**段（本来就没有 `[center_client]`；本期只有 mdm/report 需要配键）；
- `cmx-container/config/` 四件套：config_template.toml / .env.template / CONFIG_MANUAL.md / ENV_MANUAL.md 的段与 `CENTER_CLIENT__` → `SERVICE_RPC__` 前缀同步（config-sync 技能）；
- 各环境 `.env` 中出现的 `CENTER_CLIENT__SERVICES__*` 覆盖值逐一排查改写；
- 验证命令：迁移后全量服务启动 + `RUST_LOG` 观察目录快照日志；漏配由判定矩阵兜底显性报错。

### 4.2 模块结构

```
cmx-service-rpc/src/
  lib.rs          // 门面 + 全局句柄（与 GlobalServiceInstanceCache 同期初始化；基础设施合规——连接池/只读配置，无业务态）
  config.rs       // ServiceRpcConfig（吸收 center_client/config.rs，含旧段检测）
  directory.rs    // ServiceDirectory：key → ServiceEntry；resolve(key) -> ResolvedEndpoint
                  //   （url 静态 | 实例缓存选例【healthy + weight 加权 + http_port 元数据优先】）
  error.rs        // ServiceRpcError：{ Unavailable(key, cause), Timeout(key), AuthRejected,
                  //   Remote{ http_status, code, msg }, Decode(cause), NoBinding{ sdk, transport } }
  invoke.rs       // RpcCall（key, method, path, query, body, 幂等标记）→ 按 transport/feature 分派
  transport/
    mod.rs        // trait Transport
    http.rs       // reqwest：ApiResp 信封解包、鉴权注入、总超时、幂等重试（connect 错误换实例）
  transport/grpc/ # 【cfg(feature = "grpc-client")】吸收 cmx-rpc client（discover/retry/auth_outbound/GlobalRpcClient）
  server/         # 【cfg(feature = "grpc-server")】吸收 cmx-rpc server（auth_layer/server_runner/bundle）
  guard.rs        // per-key 熔断：连续失败 N 次快速失败 + 半开探活
  obs.rs          // tracing span（key + 目标实例）+ /metrics 打点（per-key QPS/延迟/错误率）
```

### 4.3 鉴权链（复用现有语义）

出站注入：`X-API-Key`（`[service_auth].outgoing_api_key`）+ `X-Delegated-User-Token`（有用户上下文时透传原始 JWT）+ `X-Request-Id`；引擎侧 engine-kit delegated 中间件零改动。**迁移注意（v2）**：report 现用 `X-User`/`X-Tenant` 直设头——切换到统一鉴权链时，需实测 flow 侧对"无 X-User、仅委托令牌"调用的接受度（列入 §七 **1b 验收清单**显式验证项）。

### 4.4 能力声明：服务只支持 grpc / rest / both

三层机制，静态优先：
1. **SDK 类型层**：契约只出 HTTP 绑定时，配 `transport="grpc"` 启动即 NoBinding 报错；
2. **配置层**：per-key transport 覆盖缺省；
3. **注册中心 metadata**：实例 metadata `transports = "http,grpc"`、`grpc_port`（扩展现有 `http_port` 机制）——基座选例时校验所选实例是否支持目标传输并按端口寻址。不做运行时动态协商。

---

## 五、契约 SDK 模式（以 cmx-flow-sdk 为例）

```rust
// cmx-container/crates/libs/cmx-flow/cmx-flow-sdk/src/lib.rs

pub const SERVICE_KEY: &str = "flow";

pub mod paths {   // ★以 flow 的 v1 openapi.json 逐方法核对后定稿（存量 mdm 内联 JSON 打的是旧无 v1 路径，形状未必一致）
    pub const INSTANCES: &str = "/api/flow/v1/instances";
    // ...
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StartInstanceReq { /* wire contract，自包含 */ }

#[async_trait::async_trait]   // §2.4 选型：沿 workspace 惯例，dyn 兼容
pub trait FlowClient: Send + Sync {
    async fn start_instance(&self, req: StartInstanceReq) -> Result<FlowInstanceResp, ServiceRpcError>;
    async fn complete_apply_task(&self, req: CompleteTaskReq) -> Result<(), ServiceRpcError>;
    async fn my_claimable_tasks(&self, user: &str) -> Result<Vec<TaskSummary>, ServiceRpcError>;
    // 首批方法集 = mdm 11 个方法 + report start_close_instance；逐方法对照 v1 openapi
}

pub struct HttpFlowClient { rpc: ServiceRpcHandle }

/// 从全局服务目录构造（transport/feature 配置决定实现；错配返回 Err 而非 panic）
pub fn client() -> Result<Arc<dyn FlowClient>, ServiceRpcError>;
```

**服务端半边（cmx-flowengine）**：handler `use cmx_flow_sdk::{paths, StartInstanceReq}` 挂路由 + `From<StartInstanceReq> for InternalStartParams`——路径、DTO 两端同源。

**首批三个契约**：

| 契约 crate | 方法来源 | 消费方 | 服务端 |
| --- | --- | --- | --- |
| `cmx-flow-sdk` | mdm 11 方法 + report `start_close_instance`（**逐方法对照 v1 openapi**） | cmx-mdm、cmx-report | cmx-flowengine |
| `cmx-model-sdk` | mdm 激活链路的元数据读取（`/api/dct/meta` 等）+ 铸号（`CodeMinter` trait 的远程实现） | cmx-mdm | cmx-model |
| `cmx-mdm-sdk` | ~~flow webhook 生命周期回调（`/api/mdm/flow/callback` + `X-Cmx-Flow-Signature` HMAC 约定，**仅路径与算法，secret 不进 SDK**）~~ **已移除（2026-09-01，决策 15）**：对外回调契约不以共享 crate 为载体，实现内联 flow 侧 `webhook.rs` + mdm 侧 `flow_cb.rs` 验签，文档真源 flowengine `docs/usage/08` §8.6 | ~~cmx-flowengine~~ | ~~cmx-mdm~~ |

**测试策略（v2 补）**：SDK 单测基于 `Transport` trait 的 mock 实现（目录/解包/错误映射全链路）；服务端契约测试 = SDK 客户端打真实 handler（`tower::ServiceExt::oneshot`，不起端口）；每契约一组"DTO 双端编译期对齐"由类型系统天然保证。

---

## 六、存量迁移清单（全部改造，终态不留双轨）

| # | 现状 | 迁移目标 | 附带 |
| --- | --- | --- | --- |
| 1 | mdm `flow_client.rs`：裸 reqwest + **绕行门户**（loopback→8080→反代→8091） | `cmx-flow-sdk` + 目录键直连 | 去两跳；路径升 v1（对照 openapi） |
| 2 | mdm `dispatcher.rs` 死信通知（`[mdm.notify].portal_base` 静态） | 通知契约 + 目录键 | 静态地址清零 |
| 3 | report `flow_client.rs`（`FLOW_BASE_URL`，默认关；用 `X-User`/`X-Tenant` 头） | `cmx-flow-sdk` | §4.3 鉴权头验证项 |
| 4 | flow adapters（identity/subflow/delegate，默认 pg 直连） | **已完成（2026-09-01，见 §十四）**：http 形态切基座目录键；pg 直连保留为 trait 的本地实现（部署形态选项） | 协议不变；env `FLOW_*_URL` → `FLOW_*_TARGET` |
| 5 | flow `webhook.rs`（`FLOW_WEBHOOK_URLS` 静态 + HMAC） | **已完成，形态变更（2026-09-01，决策 15）**：不建 `cmx-mdm-sdk`——契约内联 `webhook.rs`（HMAC + 三头 + `键:路径` 目标）+ 目录键；成功判定 HTTP 2xx | 签名/重试/幂等单测覆盖（flow 集成测试 + mdm 验签单测对拍） |
| 6 | `remote_importers`（menu/perm/form） | HTTP/gRPC 分派改走基座门面；DataCategory/packer **留 cmx-plugin** | 消除第二套调用栈 |
| 7 | 门户反代 upstream（4 处消费：cmx-platform-app/routes.rs、cmx-flow-api、cmx-rpt-api、cmx-rule-api 的 proxy.rs + cmx-common-api pages.rs import） | 从基座目录读定位字段 | 语义不变 |
| 8 | `cmx-rpc` | 按 §3.3 波及图并入/改造，crate 删除 | 6 消费方 + cmx-rpcs/ + cmx-rpc-gen 去向已定 |
| 9 | mdm → cmx-model 依赖 | 阶段三下沉 5 crate（§七）；阶段四 SDK 远程化 | P5 闭环 |
| 10 | `cmx-portal` 反向依赖（消费方 cmx-common-api；传递拉 cmx-model-meta） | **单列治理项（不占阶段一）**：门户 store 层下沉 container 门户域组或装配挪 platform-app；与阶段三的 cmx-model-meta 下沉联动 | 量级偏大（cmx-portal 37 个 rs，cmx-common-api 深度使用），超预期单独出补充方案 |

**行为变化显式化（v2）**：mdm 超时 10s → 全局默认 30s（保留键级覆盖，迁移时 mdm 显式配 10s 可保现状）；幂等重试为新增语义（现状 mdm 无重试），非幂等 POST 一律不重试。

---

## 七、实施阶段（每子阶段独立验收；终态单轨，阶段内分批合入允许过渡提交）

**批次划分（v2.2 调整，用户已确认；2026-09-01 更新：批次二·阶段三已实施，见 §十三；阶段四同日降级为条件触发、默认不做，见决策 14）**：本方案拆为两个正交批次——**第一批：rpc 统一（1a/1b/1c）先行实施**；**第二批：模型中心下沉（阶段三）于 2026-09-01 实施（§十三），model 远程化（阶段四）条件触发、默认不做（决策 14）**。两批无依赖关系：1b 首批契约只含 cmx-flow-sdk 与 cmx-mdm-sdk（cmx-model-sdk 本属阶段四）；cmx-portal→cmx-model-meta 传递依赖随阶段三下沉自然消解为同源引用（真源回归 container）。

| 阶段 | 内容 | 验收 |
| --- | --- | --- |
| **1a 基座骨架**（第一批） | cmx-service-rpc（http-only + 目录 + 门面 + 鉴权/重试/熔断/可观测）；配置模型与判定矩阵；与 center_client **双轨并存**（基座就绪，存量暂未切） | 新 crate 单测全绿；container workspace check |
| **1b 存量切换**（第一批） | 门户 3 份 toml 迁移 + 四件套 + .env 前缀；4 处 proxy_upstream 消费方、remote_importers、mdm/report/flow 存量调用点切基座与契约 SDK（原"阶段二"首批契约并入此批，故编号 1a/1b/1c→三/四/五）；五引擎 toml 增段 | 六仓 check；全功能冒烟（登录/送审/关账/webhook 回调）；**report X-User/X-Tenant → 委托令牌接受度实测**；无 Nacos 时全量 url 直连可跑（**回滚验证**） |
| **1c gRPC 并入**（第一批） | cmx-rpc 按 §3.3 拆入 grpc-client/grpc-server feature；cmx-rpcs/、cmx-rpc-gen、6 消费方改指；**cmx-rpc 删除**；`[rpc]` 段并入。工单补记：cmx-plugin 与 cmx-common-api 对两个皮肤 crate 是**非 optional 硬依赖**且 cmx-plugin 现无 [features] 段——需为其新增 feature 段做透传（不击穿门控：五引擎不消费这两个 crate） | portal 的 gRPC 链路（bundle 注册）行为等价；五引擎依赖树 **零 volo**（cargo tree 验证） |
| **三 下沉**（第二批·**已实施，2026-09-01，见 §十三**） | 迁移闭包 {cmx-dct-store-pg, cmx-dct-model, cmx-code-api, cmx-code-model, **cmx-model-meta**} → container（新组 cmx-dct/、cmx-code/，model-meta 归属定论见下）；cmx-mdm / cmx-model / **cmx-portal**（含 cmx-portalservice 根 toml 的 cmx-model-meta path）三方引用跟随改 | 全工作区 grep（**含 cmx-portalservice**）：无 `path = "../cmx-model` 出现；六仓 check |
| **四 model 远程化**（第二批·**条件触发，默认不做**，决策 14） | cmx-model-sdk（元数据 + 铸号远程实现 `CodeMinter`）；mdm 激活链路"读"走远程 + 短 TTL 缓存；`record_gap_for_code` 的 bool/String 错误语义映射到 ServiceRpcError | **触发条件：出现 mdm 与 model 不共资产目录/不共库的部署需求**（如 model 独立交付/独立发布节奏）。触发后：mdm/model 独立机器部署跑通；铸号基准测试（不达标→降级保留本地 CodeEngine） |
| **五 gRPC 按需**（随用随做） | 有真实高性能场景时：proto + 服务端 bundle + SDK 加 GrpcXxxClient | 同一消费方 http/grpc 切换零代码（仅配置） |

**阶段三的两个定论（v2）**：
1. `cmx-model-meta` 下沉 container——它是定义 JSON 读取层（definitions store + resolve_dict_file），是 mdm 激活**落库**路径（`dict_upsert` 仍留在 mdm 本地、经下沉后的 cmx-dct-store-pg、Txn::External 主事务）的公共依赖，mdm 不引它就得整体远程化落库（**跨服务分布式事务，改造量与风险不可接受**）——下沉是唯一务实解。"元数据读取逻辑住进公用库"的归属质疑，以"mdm 激活落库是平台公共链路"辩护并记录在案。
2. **阶段三必须先于阶段四**：激活链路远程化的只是"元数据读取 + 铸号"，`dict_upsert` 落库仍在本地——这正是下沉先行、远程化只切读写边界中"读"与"号"两处的原因，跳过阶段三则阶段四无从谈起。

**下沉后的 cmx-model 仓格局（避免"模型中心被抽空"误读）**：下沉的是 5 个**库形态**的运行态数据访问 crate（dct 存储层/铸号引擎/定义读取层——平台公共层，类比 spring-data）；cmx-model 仓保留 6 个**服务形态** crate：`cmx-doc-model`、`cmx-doc-store-pg`（单据模型）、`cmx-master-slave`（主从模型）、`cmx-model-deploy`（部署引擎：定义编译→建表→台账→菜单种子，模型中心核心价值）、`cmx-model-app`、`cmx-model-server`。判断标准：**定义的管理态（设计/版本/部署/发布）留模型中心，数据的运行态读写下沉平台**；下沉 crate 真源随之移至 container 仓（修改走平台仓集中治理），cmx-model 改 workspace 引用。

**阶段四的硬前提（v2 显式化）**：铸号远程化后 mdm 与 model **独立部署但共享同一业务库**（cmx_code_* 表事务仍在 DB 侧）——分库则断号一致性崩塌，届时唯一选项是降级路径（本地 CodeEngine）。此前提作为架构约束写入部署文档。

## 八、风险与对策

| 风险 | 对策 |
| --- | --- |
| 契约变更集中 container 仓，跨仓协调 | 契约即产品，走平台评审；CI 对 `cmx-*-sdk` diff 打标签提醒双方升级；版本策略见下 |
| 版本与发布（v2 补） | 新 crate 随 container 仓 `registry = "nora"` 发布，语义化版本：0.x 阶段契约 SDK 的 breaking（删方法/改字段）升 minor + CHANGELOG 显式标注（0.x 惯例 minor 即破坏位）；**1.0 后 breaking 必须升 major**，消费方升级有据 |
| DTO 转换样板 | 服务端 `From/Into` 集中一个 `contract.rs`；同构 DTO 用 type 别名 |
| 配置迁移漏改 | §4.1 判定矩阵兜底显性报错；迁移检查清单（文件+env+验证命令）入实施工单 |
| mdm 铸号远程化性能回退 | 元数据 TTL 缓存、铸号批量接口、阶段四基准测试，不达标降级本地 CodeEngine（下沉后无跨仓依赖，降级可接受） |
| webhook 迁移回归 | cmx-mdm-sdk 首个单测集：签名/重试/幂等 |
| `cmx-portal` 清偿范围膨胀 | 已移出阶段一单列（§六 #10），超预期单独补充方案，不阻塞主线 |
| feature 错配（grpc 配置但 feature 未开） | 启动 NoBinding 报错 + 提示；CI 可加 `cargo tree -i volo` 守卫五引擎零 gRPC 依赖 |

## 九、决策记录

1. 配置段 `[center_client]` → `[service_rpc]`，原 `[rpc]` 段并入 `[service_rpc.server]`；`[service_auth]` 保留独立（用户已确认改名；v2 定 rpc 段归属）；
2. gRPC：**feature 门控**（grpc-client/grpc-server optional，默认 http-only）——v2 修订：否决"硬吸收 cmx-rpc 全部"原稿写法（依赖实测：cmx-rpc 全树 575 crate，五引擎现状零 gRPC 依赖，硬合并违背 SDK 轻量目标）；gRPC 绑定按需后补（用户已确认基座统一+REST 先行）；
3. 契约 SDK 自包含（不引用服务方仓类型），放各域组目录，依赖三条铁律；
4. `cmx-proxy-core`（南北向反代）与 `cmx-service-rpc`（东西向调用）职责分离、不合并；
5. `cmx-rpc` 退役（v2 补全波及图：6 消费方 + cmx-rpcs 保留独立 + cmx-rpc-gen 保留工具）；
6. flow adapters 的 pg 直连保留为 trait 本地实现（部署形态选项）；
7. （v2）async trait 用 `#[async_trait]`（workspace 惯例 + dyn 兼容）；
8. （v2）fail-fast 判定矩阵四情形（段缺失=合法空目录；discovery 键无注册中心无 url=报错；旧段残留=报错提示；grpc 错配=NoBinding）；
9. （v2）cmx-model-meta 随闭包下沉 container（mdm 激活落库公共层，论证见 §七）；
10. （v2）阶段四硬前提：mdm/model 独立部署、共享业务库；分库即走本地 CodeEngine 降级；
11. （v2）阶段一拆 1a/1b/1c（骨架→切换→退役），终态单轨不变；
12. （v2）路径常量以 v1 openapi.json 核对定稿（存量 mdm 内联 JSON 打旧路径，不照抄）。
13. （v2.2，用户拍板）**实施分两批：rpc 统一（1a/1b/1c）先行，模型中心下沉与远程化（阶段三/四）暂停、另行排期**——两批正交无依赖；暂停期间 mdm 的跨仓 path 依赖作为存量延续，不阻塞第一批任何验收。
14. （v2.4，2026-09-01 用户拍板）**阶段四（model 远程化）降级为条件触发、默认不做，取代决策 13 中"另行排期"的表述**。理由：阶段三下沉后 mdm 已进程内本地直读元数据 + 共库铸号，远程化收益仅剩"mdm 与 model 部署隔离"一个场景，而该场景受两条既有硬约束排除（铸号必须共库否则断号、元数据目录集群本就同构）——不触发即纯成本（网络跳数/缓存/故障面）。**触发条件：出现 mdm 与 model 不共资产目录/不共库的部署需求**（如模型中心独立交付、发布节奏完全脱钩）；触发时按 §七 阶段四原设计执行。
15. （v2.5，2026-09-01 用户拍板）**`cmx-mdm-sdk` 整体移除，webhook 回调契约不以共享 crate 为载体**。理由：对流程引擎而言，webhook 订阅方（mdm 及未来任意外部/三方系统）是**外部系统**，不会共享本工作区的 Rust crate——"两端同源 SDK"的契约形态只对内部服务间调用成立，对出站回调不成立（同 GitHub/Stripe webhook：契约载体是文档，双端各自实现）。落地：①契约实现内联进 flow 侧 `cmx-flow-adapters/src/webhook.rs`（事件 DTO + HMAC 签名 + 三头常量），mdm 接收端 `flow_cb.rs` 内联验签（常量时间比较）；②契约真源 = flowengine `docs/usage/08-external-integration.md` §8.6；③`FLOW_WEBHOOK_TARGETS` 条目从纯服务键（`mdm`）升级为 `键:回调路径`（`mdm:/api/mdm/flow/callback`，路径归接收方定义，不再写死 mdm 路径）；④成功判定从"信封 code==0"改 **HTTP 2xx**（接收方协议自由，`execute` 裸响应层）；⑤crate 从 container 工作区删除。契约漂移风险由双端测试对拍兜底（flow 侧集成测试含接收端视角 HMAC 重算；mdm 侧签名/验签往返单测）。

## 十、与用户问题的对应

- **"rpc 和 rest 放一起合适吗？REST-only 服务会引入 rpc 依赖不好"**——担心成立。v2 采用 feature 门控（§3.2）：默认 feature 只有 http（reqwest），volo 全家桶是 optional 的 `grpc-client`/`grpc-server`；六服务独立 workspace 构建下 feature 不跨仓统一，report 不开 feature 就**零 volo 依赖**（cargo tree 守卫入 CI）。为什么不拆两个 crate（选项 B）：workspace 已有 feature 门控先例（cmx-service-base `rpc` feature），拆 crate 会让 trait/类型接口面变大且与"crate 数量-1"目标相悖——门控已完全达成"按需引入"效果。
- 其余见 §二.1（SDK 体验）、§二.2（依赖方向）。

## 十一、审查记录

### 第一轮（general-purpose 子智能体，52 次工具调用，代码逐项核查）

- **P0-1** gRPC 依赖硬塞全部消费方（cmx-rpc 全树 575 crate 实测）→ v2 改 feature 门控（§3.2）。
- **P1-1** 下沉闭包低估（2→实际 5 crate，cmx-model-meta 另被 cmx-portal 传递依赖）→ v2 §七阶段三改写 + 归属定论。
- **P1-2** cmx-rpc 退役漏 3 消费方（cmx-common-api、cmx-platform-app 直引、cmx-rpcs 皮肤）+ cmx-rpc-gen 未交代 → v2 §3.3 波及图。
- **P1-3** "六仓 toml 改名"写反（仅门户 3 份有段，五引擎是新增）+ fail-fast 会打崩合法空段环境 → v2 §4.1 判定矩阵 + 迁移清单。
- **P1-4** 示例宏 `#[cmx_api::async_trait]` 不存在 → v2 改 `#[async_trait]` 并补选型节（§2.4）。
- **P1-5** 阶段一过载 → v2 拆 1a/1b/1c。
- **P1-6** 铸号远程化共库前提未言明 + 错误语义（bool/String）未设计 → v2 §七阶段四硬前提 + 映射任务。
- **P2×9**：report X-User/X-Tenant 鉴权头验证、v1 openapi 对照、proxy_upstream 4 消费方、packer/types 去向、[rpc]/[service_auth] 段关系、超时/重试行为变化、版本发布策略、激活落库本地语义、cmx-portal 清偿移出阶段一——全部吸收（§四.3、§五、§三.4、§三.1、§四.1、§六、§八、§七、§六#10）。
- 断言核查 20 项：17 项一致/基本一致，3 项不一致已修正（退役影响面、下沉闭包、配置迁移面），1 项虚构宏已改。

### 第二轮（Explore 复核，26 次工具调用）

- **结论：通过，可进入实施**。7 项必修全部实质落实且经代码复核吻合；3 个抽查断言（service-base rpc feature 门控先例 / cmx-portal→cmx-model-meta 传递依赖 / report X-User 头）全部属实。
- 新发现 5 条 P2（不阻塞），已全部修入 v2.1：①§4.3 阶段编号改指 1b 并入 1b 验收清单；②皮肤 crate 措辞改"仅 portal 构建链消费"+ cmx-plugin 需新增 [features] 段的实施细节入 1c 工单；③阶段三验收 grep 范围扩至全工作区（含 cmx-portalservice 的 cmx-model-meta path）；④§1.2 四件套证据措辞收窄（前缀/段名两种形式）；⑤版本策略补 0.x/1.0 语义边界。
- 复核确认的关键前提：五引擎不消费 cmx-plugin/cmx-common-api/cmx-rpc（feature 门控不被击穿的成立条件，实测）；`[rpc]` 与 `[service_auth]` 段并存于 portal-server.toml（支撑决策 1）；cmx-portal 实测 37 个 rs（量级描述准确）。


---

## 十二、批次一实施记录（2026-08-31，分支 feat/batch1-service-rpc）

> 1a + 1b + 1c 全部落地并通过端到端验证；第二批阶段三已于 2026-09-01 实施（§十三），阶段四降级为条件触发（决策 14）。

### 落地清单

| 项 | 内容 |
| --- | --- |
| **cmx-service-rpc 基座**（新建，`crates/libs/cmx-infra/cmx-service-rpc/`） | 模块：config（`[service_rpc]` 模型 + 旧段 fail-fast 检测）/ directory（Locator 定位 + 选例核 + 校验矩阵）/ error（ServiceRpcError 六变体）/ invoke（RpcRequest/RpcResponse + 标准信封解包）/ transport（trait + http 实现 + NoopTransport 占位）/ guard（per-key 熔断：5 连败开放→10s 冷却半开探活）/ obs（span + per-key 打点）；feature：`default=["http"]`、`grpc-client`、`grpc-server`（蕴含 client）。全局句柄 `init/init_and_warm/install/global(_arc)`，`cmx-service-base::init_infra` 末尾自动调用（registry-config feature 门控） |
| **契约 SDK**（新建） | `cmx-flow-sdk`（10 方法覆盖 mdm 11 方法 + report 起实例；v1 路径常量；请求 DTO 严格类型化、响应稳定字段 + flatten extra；flex_string 兼容 id 双形态）；`cmx-mdm-sdk`（webhook 回调契约：路径 + HMAC 签名/验签 + FlowEvent wire DTO + 投递客户端；secret 不进 SDK） |
| **center_client 退役** | config.rs/upstream.rs 删除（能力入基座）；types（DataCategory）/packer 迁 `service/remote_importers/`；remote_importers 切基座门面（multipart 走 RpcRequest、legacy 信封 `{code:200,message}` 自解析、grpc 分支 feature 门控）；消费方 4 处（platform-app routes/iam/lib、common-api pages）改指 `cmx_service_rpc::locator` |
| **cmx-rpc 退役（1c）** | 全部模块吸收进基座 `src/grpc/`（client/discover/global ← grpc-client；bundle/factory/server/server_runner ← grpc-server）；六消费方改指：cmx-service-base（rpc feature → `cmx-service-rpc/grpc-server`）、cmx-plugin（皮肤 optional + `[features] grpc`）、cmx-common-api（同 + 端点未启用占位）、cmx-platform-app、两个皮肤 crate；`[rpc]` 配置段并入 `[service_rpc.server]`（load_rpc_config 读新位、inject_rpc_metadata 跟随）；crate 目录与 workspace 条目删除 |
| **存量调用点切换** | mdm flow_client 重写为 SDK 薄封装（去 loopback 两跳、路径升 v1、超时 10s 保语义入键级配置）+ dispatcher 死信通知走目录键 `portal` + flow_cb 验签切 SDK；report flow_client 重写（`X-User/X-Tenant` 头移除——实测 flow jwt 模式下本就无效，发起人走 `variables.initiator`；信封判据修正为严格 code==0）；flowengine webhook 目标从 `FLOW_WEBHOOK_URLS` 改 `FLOW_WEBHOOK_TARGETS`（服务键）+ 投递走 cmx-mdm-sdk |
| **配置迁移** | 门户 3 toml + 容器 dev/dev-vpn/docker：`[center_client]`→`[service_rpc]`（+retry_max）、`[rpc]`→`[service_rpc.server]`；mdm toml（flow/portal 键，`[mdm.flow]` 收敛、`[mdm.notify]` 删除）；report toml（flow 键 + `[consol.flow]`）；flow toml（新增 mdm 键——webhook 出站，**实施中发现的原方案遗漏**）；config 四件套同步（config-sync 规范，含废弃前缀 L2/L3 配对） |
| **顺手修复（存量问题）** | ① cmx-biz 显式启用 `cmx-api-types/db-error`（修复 `-p` 作用域 check 必败的存量地雷）；② `registry_enabled()` 判据修正——`MockRegistry::is_enabled` 恒 true（历史语义），改按 `RegistryConfig::from_env().enabled` 判定，discovery-only fail-fast 在 Mock 环境真正生效 |
| **文档同步（2026-09-01 补做）** | 三个新 crate README（service-rpc 含判定矩阵/SOP 承接 + VOLO_GUIDE 随迁改写 42 处引用）；cmx-container 根 README（架构图/crate 清单/契约 SDK 行 + 顺手补存量缺失的 meta-proxy 条目与重复表头）+ AGENTS 十九章（基础设施层指向 service-rpc grpc 模块）；14 个 crate README 与源码 doc 注释清旧引用（`[center_client]`→`[service_rpc]`、`cmx_plugin::center_client::*`→`cmx_service_rpc::*`、`cmx_rpc::`→`cmx_service_rpc::grpc::`）；cmx-rpcs 分组 README；子仓：portalservice README 配置章整体重写（原为 v1 mode/urls 形态，误导性最强）、mdm README（[mdm.flow] 收敛 / [mdm.notify] 删除）、flowengine README 里程碑措辞、report consol_close.bpmn.xml 注释（FLOW_BASE_URL→service_rpc）；注释改动经 scoped cargo check 验证，活文档旧引用终扫零残留（历史档案 .trae/docs 按规范不动） |

### 验证记录

- **编译**：cmx-container 全 workspace check 绿；六仓（container/portalservice/flowengine/report/rulesengine/mdm）check 全绿。
- **单测**：基座 22 + flow-sdk 6 + mdm-sdk 3 + cmx-plugin 245 + mdm-app 12 + flow-adapters 20（含 webhook 全链路集成测试：真实 axum 桩 + 基座目录 + 签名 + 重试）全绿；新 crate clippy 零警告（改动 crate 零新增警告）。
- **五引擎零 volo**：`cargo tree -i volo` 在 flowengine/report/rulesengine/mdm/model 均 "did not match any packages"（依赖图完全不含）；门户 volo 链保持完整（volo ← cmx-rpc-gen ← 皮肤 ← common-api/plugin ← platform-app）。
- **E2E**（四服务联起，全程 Mock 注册中心 + url 直连 = 回滚形态）：登录 ✓；门户反代 flow/report/mdm（新基座 locator）✓；`X-API-Key` 服务间鉴权直连 v1 ✓；**mdm 送审 5 条 CR → cmx-flow-sdk 直连起实例（v1/bizLink/信封）全通**；审批 complete → 实例 COMPLETED ✓；**webhook flow→mdm（cmx-mdm-sdk 签名投递）→ mdm 验签 → CR 激活 activated ✓**（flow_cb "流程通过 → 激活完成"实证）；判定矩阵：段缺失合法 ✓、旧段残留 fail-fast ✓（错误信息带迁移提示）、discovery-only 无 url fail-fast ✓。
- **E2E 环境数据问题（非代码）**：3 条 CR 激活失败均为存量测试数据缺陷（create_by=0 / 银行账号唯一约束 / account_no 必填缺失）——错误透传链路（ServiceRpcError::Remote msg）反而得到实证；report 关账业务闭环因 dev 库无关账表（cg_scope 等 4 表全缺）未执行，路由/反代/委托鉴权（via_proxy=true auth=delegated）已实证。
- **未端到端项**：mdm 死信通知（portal 键）——需造分发死信场景，`call_api_unit` 路径由单测与同链路覆盖。（2026-09-01 用户拍板免验证，事项关闭）

### 行为变化显式化（部署注意）

1. mdm flow 调用不再绕行门户（loopback:8080 两跳 → 直连 8091）；`[mdm.flow].loopback_base/timeout_ms` 与 `[mdm.notify].portal_base` 已删（超时语义迁 `[service_rpc.services.flow].timeout_ms=10000`）。
2. report 对接 flow 从 env（`FLOW_BASE_URL` 族）迁 toml（`[service_rpc.services.flow]` + `[consol.flow]`）；`FLOW_*` env 不再读取。
3. flow webhook：`FLOW_WEBHOOK_URLS`（URL 列表）→ `FLOW_WEBHOOK_TARGETS`（服务目录键列表）；密钥 `FLOW_WEBHOOK_SIGNING_KEY` 不变（须与 mdm `[mdm.flow].webhook_secret` 一致）。
4. env 前缀 `CENTER_CLIENT__*` → `SERVICE_RPC__*`；旧段残留（`[center_client]`/`[rpc]`）启动即报错（错误信息可操作）。
5. report 信封判据修正（旧 `code != 1` → 严格 `code == 0`）；幂等重试为新增语义（非幂等 POST 不重试）。

### 遗留与后续

- flowengine `http_start_validation` 2 个存量失败测试——2026-09-01 定性并修复：断言口径过时（handler 经 `FlowError::bad_request` 返回信封 `code:400` = `ErrCode::BadRequest`，测试仍断言旧 `code:2`），改测试断言对齐现状后 3 例全绿、flowengine 全 workspace 测试零失败。
- ~~门户 `dev-vpn.toml`/`dev-xty.toml`（本地未入库）如启用需自行迁移段名~~——2026-09-01 复核：两文件本地均已不存在（container 版 dev-vpn.toml 批次一已迁段名）；全工作区 toml `[center_client]`/`[rpc]` 旧段与 .env `CENTER_CLIENT__` 活前缀**零残留**（`.env.template` 内为 config-sync 规范的废弃对照注释，非活配置），事项关闭。
- 第二批阶段三（数据运行态下沉）已于 2026-09-01 实施（见 §十三）；阶段四（model 远程化）已于同日降级为条件触发、默认不做（决策 14）。
- mdm→flow 的 `cmx-model-sdk`、五 gRPC 按需（阶段四/五）未动。

---

## 十三、批次二·阶段三实施记录（2026-09-01，分支 feat/batch2-phase3-sink）

> 数据运行态 8 crate 自 cmx-model 回沉 cmx-container，服务仓间 path 依赖清零（已提交并 --no-ff 合并回 dev/main 原分支）。
> 闭包两次扩大：方案预估 5 → 实施确认 6（+cmx-master-slave）→ 用户拍板 8（+cmx-doc-model/doc-store-pg，
> 「DOC 数据层与 DCT 同构对称，同为平台通用功能」——方案原文将 doc 两件套留在 cmx-model 属保守最小闭包，
> 按「数据的运行态读写下沉平台」判断标准 doc 本应同沉，实施采纳）。

### 迁移清单（实际闭包 = 8 crate）

| Crate | 新址（cmx-container） | 说明 |
| --- | --- | --- |
| `cmx-model-meta` | `crates/libs/cmx-model/cmx-model-meta` | 定义 JSON 读取层（方案闭包第 5 员） |
| `cmx-dct-store-pg` | `crates/libs/cmx-dct/cmx-dct-store-pg` | DCT 数据服务（含 tests/hier_service_pg 真机集成测试随迁——其 ASSETS__ROOT 推导恰好按 container 位置写死 nth(4)，回迁后自动正确） |
| `cmx-dct-model` | `crates/libs/cmx-dct/cmx-dct-model` | DCT 模型层 |
| `cmx-code-api` | `crates/libs/cmx-code/cmx-code-api` | CodeEngine 无状态实现 |
| `cmx-code-model` | `crates/libs/cmx-code/cmx-code-model` | 编码规则模型 |
| `cmx-master-slave` | `crates/libs/cmx-model/cmx-master-slave` | **实施确认的闭包第 6 员**：dct-store-pg 硬依赖（impl HierService），近叶子纯协议层（仅依赖 cmx-rowsource + serde 系）；不随沉则 container→服务仓反向依赖违反铁律。§1.2「≥5 个」预判命中 |
| `cmx-doc-model` | `crates/libs/cmx-doc/cmx-doc-model` | **用户拍板的闭包第 7/8 员**：DOC 定义模型（SQL 生成，sqlx/tokio-pg 双驱动通用） |
| `cmx-doc-store-pg` | `crates/libs/cmx-doc/cmx-doc-store-pg` | DOC 单据 PG 存储层（装载/回存/版本化 + impl HierService 上卷）；下沉后其对 master-slave/model-meta 的跨 ws 引用收敛为 container 仓内关系，消费方仅 cmx-model-app（全工作区零外部引用） |

- **零代码迁移**：8 crate 依赖全为 `workspace = true` 继承式，两仓 workspace 元数据完全对齐（0.1.12/2024/同作者），utoipa 等 container 均已声明——源码零改动，仅物理搬运 + workspace 声明。
- **container**：members +8、`[workspace.dependencies]` +8（registry = "nora"）；顺手修复 5 条孤儿注释（S0 抽走声明时遗留，其中数条恰对应本次回迁 crate，还原为真实声明）。
- **cmx-model**（11→3 crate，纯管理态）：删 8 目录（git rm）；8 条 workspace 声明改跨 ws path 指 container；保留 crate（model-deploy/model-app/model-server）经 workspace 机制无感切换；补仓 README（此前缺失）。
- **cmx-mdm**：`cmx-dct-store-pg`/`cmx-code-api` 两条 path 改指 container；原「三仓同源消歧」注释失效改写（全链单源后不再有 collision 协调问题）。
- **cmx-portalservice**：`cmx-model-meta` 一条 path 改指 container（§六 #10 的传递链 cmx-portal→cmx-model-meta 随之消解为平台仓内部引用——该治理项剩余部分仅剩 container 根对 `cmx-portal` 本体的反向依赖）。

### 验证记录

- **编译**：七仓 check 全绿（container / model / mdm / portalservice / flowengine / report / rulesengine）。
- **单测**：8 迁移 crate 共 248 用例全绿（code-api 13 + code-model 25 + dct-model 17 + dct-store-pg 32 + master-slave 17 + model-meta 47 + doc-model 50 + doc-store-pg 47；另有 hier_service_pg 2 例 / doc_versioning 4 例 ignored 需真机，parity_ms 1 例过）；消费方回归 mdm-app 12 ✓、model-deploy 41 ✓（5 例存量失败顺手修复后恢复，见下）。
- **验收 grep**：全工作区 `../cmx-model` 跨仓 path 引用清零；container 反向依赖服务仓仅剩已知单列项（`cmx-portal`，§六 #10）。
- **clippy**：迁移 crate 报 12 条警告全为存量基线（未动过的 cmx-biz 同报佐证；代码零改动自原仓复制），非迁移引入。
- **实施插曲 ×2**：① mdm 首次 check 报 E0463/E0460（cmx_flow_sdk 找不到/元数据不匹配）——磁盘满时期损坏的 rmeta 缓存指纹误命中，`cargo clean -p` 涉事包后干净通过；② portalservice 一次 check 报 No space——编译瞬时并发写满（临时文件随即释放，重试即过），顺手清理 container/model 两仓 incremental（释放 ~15.6G）。

### 顺手修复（存量问题，S0 迁仓路径错位同款）

- `cmx-doc-store-pg/tests/parity/ms-driver.mjs`：前端包路径按「presentation 下 7 层」硬编码上溯，S0 迁仓即错位（实证：本批对该文件所在 crate 零改动、main 上必同败），跨引擎 parity 测试长期红。改为逐层上溯探测（≤10 层），修复后 `cross_engine_parity_rollup` 通过——顺带实证迁移后的 cmx-master-slave 与前端参考实现上卷输出逐字一致。
- `cmx-model-deploy/src/lib.rs` 测试 `load()`：夹具根按固定 4 层上溯（`../../../../data/meta/definitions`）——同样 S0 迁仓错位，**main 上 5 例 compile_* 测试长期失败**（夹具真源实际在仓根 `data/meta/`，上溯 2 层）。改为逐层探测（≤6 层找 `data/meta/definitions`），41 例全绿。此为对实施记录初稿的勘误：首轮汇报"model-deploy 47 passed"实为 doc-store-pg 的用例数，deploy 失败行被输出截断漏看。

### 遗留与后续

- 阶段四（model 远程化：cmx-model-sdk + 元数据读远程化 + 铸号远程化 + 共库硬前提）降级为条件触发、默认不做（决策 14，2026-09-01 用户拍板；触发条件 = mdm 与 model 不共资产目录/不共库的部署需求）。
- §六 #10 剩余：container 根 `cmx-portal = { path = "../cmx-portalservice/..." }` 反向依赖（传递链已消解，仅剩本体）。
- cmx-model 仓 Cargo.lock 含上批次遗留漂移（cmx-service-rpc 条目）与本批删除条目，随本批一并提交。

---

## 十四、批次一收尾：flow adapters http 形态切基座（2026-09-01，cmx-flowengine main）

> §六 #4 欠账清偿：cmx-flow-adapters 四个 http 形态实现（identity/subflow/delegate + RD5 维度层级）
> 从「裸 reqwest + env URL 直连」切到 cmx-service-rpc 基座。默认 pg 模式零改动。

### 改动清单（cmx-flowengine 仓，10 文件）

| 项 | 内容 |
| --- | --- |
| **四个 http 实现切基座** | struct 从 `{ base_url, reqwest::Client }` 改持 `{ 服务目录键, Arc<ServiceRpcHandle> }`；发请求走 `RpcRequest::post/get(key, path)` + `handle.execute()`（raw 响应，**不走 call_api 信封语义**——对端是任意外部系统，协议保持自定义裸 JSON，这正是当初预留 execute 裸层的用途） |
| **构造双形态** | `new(key) -> Option<Self>`（生产：取全局基座句柄；None = 基座未初始化，装配点回退 mock——与原「缺 URL 回退 mock」语义对齐）；`with_handle(key, handle)`（测试：独立句柄不经全局单例，**测试并行安全**，无需像 webhook 测试那样顺序化） |
| **幂等标记** | identity/subflow/dimension 是查询语义 → `.idempotent()`（连接级错误换实例重试）；delegate 外部逻辑可能改状态 → 不标 |
| **错误映射** | ServiceRpcError → 各 trait 错误：identity 4xx→InvalidRef；subflow 404→NoBinding（修正了初稿误归 Backend）；dimension 404→空链 Ok；delegate 全转 String。**非 JSON 响应**（基座置 Null）显式报错，对齐原裸 reqwest 行为（防静默解空值） |
| **env 改名** | `FLOW_{IDENTITY,SUBFLOW,DELEGATE,DIMENSION}_URL` → `_TARGET`（值语义：地址 → `[service_rpc.services]` 服务目录键，无注册中心时目录配静态 url 直连——与 `FLOW_WEBHOOK_TARGETS` 先例一致；生产默认 pg 无人用过 http 形态，零迁移负担） |
| **依赖瘦身** | cmx-flow-adapters 删 reqwest 直接依赖（基座已在其 [dependencies]，现成为正式传输层） |
| **文档同步** | docs 4 文件（s6 / usage 03 / 04 / 08）：env 表 + 契约描述 + 适配器汇总表（补 RD5 行）；delegate 路径收敛为固定 `/delegate/run`（原一 key 一完整 URL） |

### 验证记录

- `cargo check -p cmx-flow-adapters -p cmx-flow-app` 绿；flowengine 全 workspace 测试**零失败**（adapters 单测 10 + http_adapters 8 + webhook 3 全绿）。
- 新增 dimension（RD5）http 集成用例（此前该实现零测试覆盖：祖先链 + 404 空链）。
- clippy：改动 crate 零新增警告（adapters 存量 1 条在未动的 webhook.rs；flow-model 11 条为存量基线）。
- 全仓 grep：五个旧 env 名（`FLOW_*_URL` / `FLOW_WEBHOOK_URLS`）代码与文档清零。

### 顺手修复（批次一漏改）

- docs/usage/08-external-integration.md 两处 `FLOW_WEBHOOK_URLS` 旧名残留（ASCII 集成图 + env 表）——webhook 已于批次一切 `FLOW_WEBHOOK_TARGETS`，文档漏同步。

### 行为变化显式化（部署注意）

1. env 变量改名 ×4（URL → TARGET），值从完整地址变为服务目录键；实际地址（静态 url 或 discovery）登记到 `[service_rpc.services]`。
2. http 形态自动获得基座横切能力：鉴权注入（X-API-Key / 委托令牌 / Request-Id）、键级超时/重试、熔断、打点。
3. delegate 外呼路径固定 `/delegate/run`（原 URL 含路径）。

---

## 十五、webhook 回调契约去 SDK 化（2026-09-01，决策 15 实施）

> `cmx-mdm-sdk` crate 整体移除：对流程引擎而言 webhook 订阅方是外部/三方系统，不会共享
> 本工作区的 Rust crate——契约载体回归 HTTP 层（文档 + 双端各自实现 + 测试对拍），
> 与内部服务间调用（cmx-service-rpc + 共享 SDK）区分为两类东西。

### 改动清单（三仓）

| 仓 | 项 | 内容 |
| --- | --- | --- |
| cmx-flowengine | `webhook.rs` 重写 | 契约自包含：三头常量（`x-cmx-flow-{signature,event,delivery}`）+ `sign_body`（HMAC-SHA256 → `sha256=<hex>`）+ `FlowEvent::delivery_id`；投递改基座 `execute` 裸层——**成功判定 HTTP 2xx**（原 SDK `call_api_unit` 解标准信封，隐含要求接收方回 CMX 信封，对外部系统不成立）；`spawn_worker` 捕获 `global_arc()`，基座未初始化降级 disabled（warn） |
| cmx-flowengine | `config.rs` | 新增 `WebhookTarget { key, path }`；`FLOW_WEBHOOK_TARGETS` 条目 `键:路径`（如 `mdm:/api/mdm/flow/callback`），路径归接收方定义（原路径 `/api/mdm/flow/callback` 写死在 SDK）；不合法条目 warn 跳过 |
| cmx-flowengine | 测试/文档 | `tests/webhook.rs` 重写（接收端视角 HMAC 重算对拍 + 常量断言 + 新目标形态）；`docs/usage/08` §8.6 契约化改写（**契约真源**）；`docs/usage/11` §11.3.3/§11.6 同步 |
| cmx-mdm | `flow_cb.rs` | 验签内联（`verify_signature` 本地实现：hex 解码 + 常量时间 MAC 比较，密钥空/头缺失/前缀不符均拒绝——与 flow 侧 `sign_body` 同式对拍）；测试 `sign` 辅助本地化 |
| cmx-container | crate 删除 | `crates/libs/cmx-mdm/cmx-mdm-sdk/` 目录删除；workspace members + `[workspace.dependencies]` + README 表行清理 |

### 行为变化显式化（部署注意）

1. `FLOW_WEBHOOK_TARGETS` 条目语法升级：`mdm` → `mdm:/api/mdm/flow/callback`（旧纯键条目启动时 warn 跳过、不投递——需更新配置）；本仓 `.env` 已同步改值。
2. 成功判定从"响应信封 `code==0`"放宽为 **HTTP 2xx**（接收方回任意 2xx 即成功，响应体不解析）——对 mdm 现状兼容（其回调 handler 回 200 + ApiResp）。
3. 事件载荷（camelCase + None 省略）与三头**逐字节不变**，mdm 接收端业务逻辑零改动。

### 验证记录

- `cargo check`：cmx-flowengine / cmx-mdm / cmx-container 三仓全绿。
- 测试：cmx-flow-adapters 23 个全绿（12 单测含 `sign_body_shape`/`parse_webhook_targets`/`event_wire_shape` 新用例 + 8 http 适配器 + 3 webhook 集成含重试全链路与 HMAC 对拍）；cmx-mdm-app `flow_cb` 4 个验签/分类单测全绿。
- 全工作区 grep `cmx-mdm-sdk|cmx_mdm_sdk` 清零（仅方案文档历史记录章节留存叙述性提及）。
