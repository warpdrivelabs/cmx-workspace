# cmx-rpc RPC 皮肤归域与契约集中重构方案

> 状态：**✅ 已实施（落地记录）** · 分支：`refactor/cmx-rpc-skin-split`（cmx-container，7 commits）/ `refactor/cmx-rpc-docs`（根仓库文档）
> 关联：[cmx-api 依赖与 Handler 重构完整方案](./20260811_cmx-api_依赖与handler重构完整方案.md)（HTTP 层对称重构，已落地）
> 本方案经 **3 路并行一审 + 1 路二审** 子智能体审查驱动修订后定稿，随后按阶段全部落地。

---

## 一、背景与目标

### 1.1 问题

RPC 层与 HTTP 层重构前同构的两大瓶颈：

1. **`cmx-rpc` 中枢臃肿**：既装基础设施（Bundle trait / factory / server_runner / discover / retry / auth），又装全部具体服务皮肤（orchestrator + resource_data 的 client / server impl / Bundle / proto 转换）。
2. **`default_bundles()` 硬编码**：主应用对外提供哪些 gRPC 服务无法由"依赖了哪些模块"决定——新增服务必须改 cmx-rpc 中枢；不同部署形态无法裁剪 RPC 能力组合。

### 1.2 目标

对标 HTTP 层三段式（cmx-api-core + cmx-apis/*-api + platform-app 装配），做到**契约中心化 · 实现归域 · 装配显式**：

| 目标 | 衡量标准 |
|------|---------|
| RPC 能力跟随模块 | 主应用提供哪些 gRPC 服务 = cmx-platform-app 显式收集的 Bundle 列表 |
| 新增服务零侵入 | 加 proto + 新建 `*-rpc` 皮肤 crate + 组装层一行，cmx-rpc 零改动 |
| 部署形态可裁剪 | 门户版/精简版/独立微服务按需组合 Bundle，只改组装层 |
| 与 HTTP 层对称 | cmx-rpcs/ ↔ cmx-apis/，init_rpc(bundles) ↔ api_routes().merge() |

### 1.3 已确认方向（用户拍板）

- proto 契约：**单一 cmx-rpc-gen 集中**（proto 按域分子目录 + lib.rs 别名）。
- 皮肤位置：**薄 `*-rpc` crate 集中 `crates/libs/cmx-rpcs/`**（业务核心 crate 不染 volo-grpc）。
- 装配机制：**组装层显式注册 Bundle**（非 inventory/linkme 自动注册——符合项目"禁隐式全局状态"红线）。
- 阶段 5 别名+挪目录一起做；文档同步 + 新增服务 SOP + 运行时冒烟全纳入。
- 无需向后兼容；全程新分支开发。

---

## 二、目标架构

```
cmx-container/crates/libs/
  cmx-rpc-gen/                       # proto 契约（单一 contract crate）
    idl/
      orchestrator/cmx_service.proto
      resource/cmx_resource_data.proto
    src/lib.rs                       # + 便捷别名 orchestrator_proto / resource_data_proto
  cmx-infra/cmx-rpc/                 # ★ 瘦身为纯 RPC 基础设施（保留现名）
    bundle.rs                        # RpcServiceBundle trait + ServerDeps + ServerRegistration（删 default_bundles）
    factory.rs                       # init_rpc_clients(…, bundles) ← 接受外部传入
    server_runner.rs / global.rs / config.rs / discover.rs / error.rs
    client/{mod,infra,retry,auth_outbound}.rs
    server/{mod,auth_layer}.rs
  cmx-rpcs/                          # ★ 新建集中目录（对称 cmx-apis/）
    cmx-orchestrator-rpc/            # 编排 + 函数调用 gRPC 皮肤
      src/{lib,client,server}.rs
    cmx-resource-rpc/                # 资源数据导入 gRPC 皮肤
      src/{lib,client,server}.rs
```

**依赖拓扑**：皮肤 crate → cmx-rpc（基础设施）+ cmx-rpc-gen（契约）+ cmx-traits（trait 抽象；orchestrator 另需 cmx-core）；**不依赖任何业务 service crate**——业务实现经 `ServerDeps` 由组装层注入，依赖倒置保持。

**三层对照（与 HTTP 层对称）**：

| 层 | HTTP（已落地） | RPC（本方案） |
|---|---|---|
| 契约 | 各 *-api 的 ApiDoc | cmx-rpc-gen（proto 集中） |
| 基础设施 | cmx-api-core | cmx-rpc（瘦身后） |
| 皮肤 | cmx-apis/cmx-*-api | cmx-rpcs/cmx-*-rpc |
| 组装 | platform-app `api_routes().merge(...)` | platform-app `init_rpc(bundles, ...)` |

---

## 三、兼容性保证（已逐项验证）

| 维度 | 保证 |
|---|---|
| 运行时行为 | 皮肤代码逐字搬迁，零逻辑改动；启动链路不变；组装层注册同样 2 个服务（服务名/wire 不变） |
| 网络契约 | proto 内容一字不改 → wire format 不变 → **滚动升级新旧节点可互操作** |
| 配置部署 | `[rpc]` / `[service_auth]` / Nacos 服务名 / 鉴权三 header / `enabled=false` 跳过行为全部原样 |
| 防静默断裂 | 静态编译兜底（漏改即编译失败）+ grep 断言；消费点全清单已实证（6 处代码 + 1 处注释；portalservice / flowengine / mega-sheet 零直接引用） |
| 唯一变化 | 消费方 use 路径（`cmx_rpc::orchestrator_client()` → `cmx_orchestrator_rpc::orchestrator_client()`；`GlobalRpcClient` 守卫路径不变）；未来新增 RPC 接口的开发方式 |

---

## 四、关键设计决策

| 决策 | 选择 | 理由 |
|---|---|---|
| proto 契约组织 | 单一 cmx-rpc-gen 集中 + 域子目录 + 别名 | 跨进程网络契约，集中避免循环依赖、生成基础设施不重复 |
| 皮肤形态 | 薄 *-rpc crate（client.rs + server.rs 单文件） | 业务核心不染 volo-grpc，与 HTTP 层 Strategy 2 一致；现文件 260-310 行单文件足够 |
| 装配机制 | 显式注册 Bundle | 符合"禁隐式全局状态"红线；server/client 角色分离；可裁剪可调试 |
| 3a 过渡实现 | default_bundles() 仅补旧皮肤 **client 单例**，`init_rpc_clients` **返回值只含传入的新 bundles** | 二审发现：若返回合并列表，volo Router 对同名服务（`cmx.CmxServiceOrchestrator`）重复 `add_service` → matchit Conflict → panic（volo-grpc router.rs `set_node` + matchit tree.rs:182）。返回值只含新 bundles 则 server 路由表无重复，且旧消费路径仍可用 |
| ServerDeps | 保持 4 字段胖容器 + 修 doc + 写演进路线 | trait object 不支持关联类型；N 域时再评估 `HashMap<TypeId, Arc<dyn Any>>` 按类型取用 |
| cmx-service-base | 不新增皮肤依赖 | `init_rpc` 参数是 trait object；皮肤在 platform-app 组装——"主应用决定提供哪些 RPC 服务" |

---

## 五、分阶段实施（每子步独立 commit、可编译、可运行）

### 阶段 0：本方案文档（根仓库 refactor/cmx-rpc-docs）

### 阶段 1：cmx-rpc 共享层 pub 加固
- `client/mod.rs`：`safe_parse_json` `pub(crate)`→`pub`（**阶段 2 编译硬前提**）。
- `lib.rs` 精确路径 re-export：`client::infra::GrpcInfrastructure`、`client::retry::{with_retry, RetryStats}`、`client::auth_outbound::apply_auth_metadata`、`client::safe_parse_json`、`server::{AuthVerifier, VerifiedAuth, verify_request}`。
- bundle::* 皮肤走 `cmx_rpc::bundle::` 模块路径（不加顶层 re-export）。

### 阶段 2：新建皮肤 crate（并存，未接线）
- 逐字搬迁 4 个皮肤文件，路径改写三类：① 外部 use；② cmx-rpc 设施（`super::infra::…`→`cmx_rpc::GrpcInfrastructure` 等）；③ crate 内扁平化（`crate::server::orchestrator::X`→`crate::server::X`）。
- lib.rs：`pub use client::{OrchestratorBundle, orchestrator_client}; pub use server::CmxOrchestratorServerImpl;`（set_client 保持 crate 内可见）。
- 依赖（一审逐文件核对）：
  - cmx-orchestrator-rpc：cmx-rpc、cmx-rpc-gen、cmx-traits、cmx-core、volo-grpc、volo、pilota、tokio、async-trait、serde_json、tracing、chrono、uuid
  - cmx-resource-rpc：cmx-rpc、cmx-rpc-gen、cmx-traits、volo-grpc、volo、tokio、async-trait、tracing
- 根 Cargo.toml：`members` + `[workspace.dependencies]`（`version="0.1.12", registry="nora"`）。

### 阶段 3a：装配层接线（过渡实现，可编译可运行）
```rust
// cmx-rpc factory.rs —— init_rpc_clients 增参 bundles 后的过渡实现
for b in bundle::default_bundles() { b.init_client(infra.clone()); }  // 仅补旧皮肤 client 单例（旧消费路径可用）
for b in &bundles { b.init_client(infra.clone()); }                    // 新皮肤 client 单例
GlobalRpcClient::mark_initialized()?;
Ok(bundles)  // ★ 只返回传入的新 bundles——旧皮肤不进 server 路由表，规避 volo 同名服务重复注册 panic
```
- cmx-service-base `init_rpc` 增参 bundles 透传；cmx-platform-app 加两皮肤依赖并构造 `vec![Box::new(OrchestratorBundle), Box::new(ResourceDataBundle)]` 传入（**主应用 RPC 能力唯一决定点**）。

### 阶段 3b：消费方切换（无 panic 窗口）
- cmx-common-api：+ cmx-orchestrator-rpc 依赖（保留 cmx-rpc）；`handlers/service/handler.rs` 改 `cmx_orchestrator_rpc::orchestrator_client()`（`cmx_rpc::GlobalRpcClient` 守卫不变）。
- cmx-plugin：+ 两皮肤依赖（保留 cmx-rpc）；`host_functions.rs`、`service/remote_importers/mod.rs` 改新路径；`center_client/mod.rs:5` 注释更新。

### 阶段 4：cmx-rpc 瘦身 + 清理
- 删 4 皮肤文件 + mod.rs / lib.rs 声明与 re-export（含 `ResourceDataImporter` re-export）。
- 删 `default_bundles()` 及 factory 过渡循环。
- **Cargo.toml 删死依赖**：cmx-rpc-gen、pilota、uuid、chrono、async-trait（留 serde_json——safe_parse_json；cmx-core——auth_layer 的 AuthContext）。
- intra-doc 死链清理（lib.rs / client/infra.rs / global.rs / bundle.rs:7,12-13 / factory.rs:3）。
- 修 bundle.rs doc"3 字段"→"4 字段"+ 补 ServerDeps 演进路线。
- 重写 cmx-rpc/README.md（共享设施 + Bundle trait 形态；顺带修正既有 `create_rpc_client` 过期示例）。

### 阶段 5：proto 别名 + 挪目录（含安全验证与回退）
① proto 挪 `idl/orchestrator/`、`idl/resource/` → ② volo.yml 两 entry `path` 更新 → ③ `cargo check -p cmx-rpc-gen` 触发 build.rs 重跑，`ls target/debug/build/cmx-rpc-gen-*/out/` 核对生成文件名不变（多 hash 目录全核对）→ ④ lib.rs 加别名模块 → ⑤ 皮肤 use 改别名 → ⑥ cmx-rpc-gen/README 同步。
**回退**：若 ③ 生成文件名/模块名变化 → git checkout 回退 ①②，保留仅别名，挪目录单独排查。

### 阶段 6：全量验证 + 文档 + SOP + 冒烟
- 三 workspace `cargo check` + `cargo clippy` 全绿。
- grep 断言：cmx-rpc 无 default_bundles / 无皮肤 impl；Cargo.toml 无 5 个已删依赖；platform-app 含显式 Bundle 构造；全 workspace `cmx_rpc::orchestrator_client|cmx_rpc::resource_data_client` = 0。
- 文档同步：cmx-container/AGENTS.md 新增 RPC 皮肤规范章节 + 修 HTTP 遗留失效引用（cmx-api→cmx-common-api、失效 dct.rs 路径）；根 AGENTS.md 总览表登记 cmx-rpcs。
- SOP：产出"新增一个 gRPC 服务"标准步骤文档。
- 运行时冒烟：起 cmx-portal-server（`[rpc] enabled=true`），确认 gRPC 端口监听 + 触发一次 orchestrator call_service 验证链路，验完即停。

### 阶段 7（可选，默认不做）
cmx-rpc → cmx-rpc-core 改名（纯机械 rename，影响面与本次重构相当，单独立项）。

---

## 六、审查历程（浓缩）

- **一审 3 路并行**（A 完整性/逻辑、B 可行性代码验证、C 风险/优化）：
  - 🔴 阶段 3 存在运行时 panic 窗口（访问器 `.expect()` 未 init 即 panic；"编译器兜底"对阶段 3 不成立）→ 拆 3a/3b。
  - 🟡 阶段 4 漏 Cargo.toml 依赖清理（5 死依赖）；皮肤 crate 依赖不对称（resource-rpc 不需 cmx-core/pilota/uuid/chrono）；Cargo.toml 需逐 crate 矩阵；cmx-service-base 不新增皮肤依赖；文档同步遗漏（AGENTS.md 存在 HTTP 遗留失效引用铁证）。
  - 确认成立：cmx-rpc 零业务依赖（轻 core）、消费点全清单、配置零变化、retry 单测留 cmx-rpc、4 皮肤文件无内嵌测试。
- **二审**（验证修订）：🔴 发现 3a"双 init 合并返回"致命缺陷——volo Router 同名服务重复注册 panic（证据链：volo-grpc router.rs:84 `panic!` + matchit tree.rs:182 Conflict + 生成代码 NAME 相同）→ 修正为"default 仅补旧 client 单例、返回值只含新 bundles"。🟡 find OUT_DIR 多 hash 目录断言细化；cmx-rpcs 完整路径定死 `crates/libs/cmx-rpcs/`。
- **验证性结论**（一审 B）：`mark_initialized` 不会误触发（OnceLock 单次 set）；两套 OnceLock 分属两 crate 无符号冲突；volo filename 决定生成名（挪目录只改 path）；build.rs 无 rerun-if-changed → 包内任何变化重跑。

---

## 七、影响面

- **新建 2 crate**：cmx-orchestrator-rpc、cmx-resource-rpc。
- **改动 7 处**：cmx-rpc、cmx-service-base、cmx-platform-app、cmx-common-api、cmx-plugin、cmx-rpc-gen、cmx-container 根 Cargo.toml。
- **文档**：cmx-container/AGENTS.md、根 AGENTS.md、cmx-rpc/README.md、cmx-rpc-gen/README.md、SOP、本方案文档。
- **下游**：cmx-portalservice（经 platform-app 传递依赖，编译验证）；cmx-flowengine（不启用 rpc feature，零影响）；cmx-mega-sheet（零引用）。

---

## 八、落地记录（已全部完成）

| 阶段 | 内容 | Commit | 验证 |
|------|------|--------|------|
| 0 | 方案文档 | `18fc2a7`（根仓库 refactor/cmx-rpc-docs） | — |
| 1 | cmx-rpc pub 加固 | `dfed4ba4` | cargo check 绿 |
| 2 | 两皮肤 crate 新建 | `76c93efd` | cargo check 绿（一次通过） |
| 3a | 装配层接线（过渡） | `1842bec6` | 三 ws check 绿（portalservice 需 `cargo clean -p` 清旧 rmeta 缓存） |
| 3b | 消费方切换 | `0d7f1356` | container + portalservice check 绿 |
| 4 | cmx-rpc 瘦身+清理+README/SOP | `4dc9bcf5` | check 绿；本次改动 crate clippy 0 警告 |
| 5 | proto 挪目录+别名 | `7d6f1167` | 生成文件名/模块名经全 5 个 hash 目录核对不变；check 绿 |
| 6a | grep 断言 | — | 6 条断言全过：default_bundles=0、皮肤归位、Cargo 无 5 死依赖、platform-app 显式 Bundle、全 4 ws 旧访问器残留=0 |
| 6b | 文档同步 | `f68881d8` | AGENTS.md 第十九章 + 修 HTTP 遗留失效引用（cmx-api→cmx-common-api/cmx_api_core、dct.rs 死链→cmx-dct-api） |
| 6c | 运行时冒烟 | — | dev.toml `[rpc] enabled=true` 起 cmx-portal-server：gRPC 9090/HTTP 8080 双端口监听、`gRPC Server 启动成功`、**无 volo 重复注册 panic**；`POST /api/service/execute`（server_name=cmx-nonexistent-smoke）返回 `无可用实例`——守卫→新皮肤访问器→基础设施→Nacos 全链路贯通，验完即停 |

**最终变更**：35 文件，+430 / −624 行；新建 2 crate（cmx-orchestrator-rpc、cmx-resource-rpc）；cmx-rpc 净瘦身（删 4 皮肤文件 + 5 死依赖 + default_bundles）。

### 与方案的偏差

| 项 | 方案 | 实际 |
|----|------|------|
| volo.yml entry key | 保持 `proto` | 顺手改 `orchestrator`（原 key 与 protocol 语义混淆）；经全 hash 目录核对生成产物不变 |
| 根 AGENTS.md 登记 cmx-rpcs | 计划中 | **未改**——总览表仅列根级目录，cmx-rpcs 是 cmx-container 内部子目录不适用；RPC 规范已入 cmx-container/AGENTS.md 第十九章 |
| portalservice 验证 | 直接 check | 首次 check 因 target 旧 rmeta 缓存报假错误（错误在两个状态间振荡）；`cargo clean -p cmx-rpc …` 定向清缓存后一次通过 |
