# cmx-center-client 服务定位 map 化与微服务接入 Nacos 方案（P2-2）

> 日期：2026-08-22
> 状态：已经两轮独立审查修订（审查记录见 §七），待实施
> 关联：`20260822_cmx-flow-rpt_反向代理评估与优化方案.md`（P2-2 条目的落地设计；本方案取代其中"新增 [gateway.*] 配置节"的原设想，改为沿用 center_client 既有 mode 约定并 map 化）
> 涉及仓库：cmx-container（主体）、cmx-portalservice / cmx-flowengine / cmx-report / cmx-rulesengine（跟随，分仓提交）

---

## 一、背景与目标

门户经 `FlowProxyModule` / `ReportProxyModule` / `RulesProxyModule` 反代到三个独立微服务，远程基址现读 `[center_client.urls].{flow,report,rules}` 固定字段——**与 mode 无关、每加一个微服务都要改 `config.rs` 加字段**。同时三个独立服务只做轻量配置初始化，完全没接注册中心/配置中心。

本方案目标：

1. **沿用 center_client 既有 mode 驱动约定**：`http_url` 手动配基址；`http_discovery`/`grpc` 只配 Nacos 服务名（复用既有订阅推送 + 30s 同步 + healthy 随机选实例，不新造机制）。
2. **配置层 map 化**：`urls` 与 `discovery.services` 均为 `HashMap<String,String>` 自由表——**新增微服务只在 toml 加一行，配置层零代码改动**；存量写死字段的全量消费代码一并迁移，不留双轨。
3. **三独立服务（cmx-flow-server / cmx-rpt-server / cmx-rule-server）接入注册中心 + 配置中心**：与门户同构 env 开关，默认全关（行为与现状一致），开启后 create 阶段强依赖失败（用户已拍板）。
4. 不含 P0（头卫生/超时治理）内容，另行批次实施。

## 二、配置形态与语义

### 2.1 目标配置形态

```toml
[center_client]
mode = "http_url"          # local | http_url | http_discovery | grpc

[center_client.urls]       # 自由表：服务键 → 手动基址（纯基址，无路径）
flow   = "http://127.0.0.1:8091"
report = "http://127.0.0.1:8092"
rules  = "http://127.0.0.1:8094"
menu   = "http://127.0.0.1:8080"    # 导入器目标 = 门户自身基址

[center_client.discovery]
nacos_group = "DEFAULT_GROUP"

[center_client.discovery.services]   # 自由表：服务键 → Nacos 服务名
flow   = "cmx-flow-server"
menu   = "cmx-portal-local"
```

env 覆盖：`CENTER_CLIENT__URLS__<KEY>` / `CENTER_CLIENT__DISCOVERY__SERVICES__<KEY>`（经 config crate `separator("__")` 产生嵌套表，`HashMap<String,String>` 反序列化已实证兼容）。

### 2.2 mode 分派矩阵

| mode | 反代目标来源 | 导入器路径 |
| --- | --- | --- |
| `http_url` | `urls[key]` 基址 | HTTP 自环/直连：基址 + `/api/plugin/data/import` |
| `http_discovery` | `discovery.services[key]` → Nacos 实例 | HTTP + 服务发现选例 |
| `grpc` | 同 `http_discovery` | gRPC（经 rpc 层 volo Discover） |
| `local` / 未知值（含遗留 `mock`） | 不挂反代 + warn | 本地直调 |
| 未配置 `[center_client]` 节 | 同 local（启动日志区分两种情形） | 本地直调 |

强依赖边界（措辞修正，二轮 H2）：三服务开启 Nacos 后，**create 阶段**（注册/配置中心客户端创建）失败即中止启动；**register 阶段**失败仅 warn（Nacos 中途宕机服务照跑，与门户 `register_service` 行为一致）。

### 2.3 键所有权约定（写入 config.rs / upstream.rs 文档注释）

| 键组 | 归属 | 值语义 |
| --- | --- | --- |
| `menu / perm / form` | 导入器 | 门户/能力中心基址（接收端 `/api/plugin/data/import` 已确认挂在门户：cmx-plugin-api `handlers/plugin/mod.rs:56`） |
| `flow / report / rules` | 反代 | 独立微服务基址（flow-server 无 `/api/plugin/data/import` 端点；`DataCategory::Flow` 现无发送方，`urls["flow"]` 现实消费者仅反代） |

## 三、存量写死字段迁移清单（已经两轮全工作区 grep 核实穷尽）

| 消费点 | 位置 | 迁移方式 |
| --- | --- | --- |
| 四个 `*_service` 字段 + `get_service_name()` | `cmx-plugin/src/center_client/config.rs:63-91` | 删字段与访问器；`CenterDiscoveryConfig = nacos_group + services: HashMap` |
| `resolve_service_name()`（`get_service_name` 唯一调用方） | `remote_importers/mod.rs:127-138`（:188/:311/:414 三处使用） | 改查 `services.get(category.as_str())`（`DataCategory::as_str()` 已有） |
| `resolve_http_url` 两分支 | `remote_importers/mod.rs:396-442` | http_url：`urls.get(key)` 基址 + 统一路径 `/api/plugin/data/import`（消除 flow 键"基址/端点"双形）；http_discovery：复用 upstream.rs 共享选例函数（消除两份 LB 逻辑漂移） |
| urls 六字段定义 | `config.rs:38-57` | 删结构体，`urls: HashMap<String,String>` |
| `cfg.urls.{flow,report,rules}` 三读取函数 | `cmx-platform-app/src/routes.rs:36-71` | 改走 `proxy_upstream(key)`（mode 分派查 map） |
| `resolve_urls()` 死代码 | `config.rs:141-156`（全工作区无调用） | 删除 |
| `table.rs:50` 注释引用 | `remote_importers/table.rs` | 文档注释更新 |

下游无构造/序列化这两个结构体的代码（cmx-portalservice / cmx-flowengine / cmx-report / cmx-rulesengine / cmx-mega-sheet 均已核实），字段删除不会引起 cmx-container 之外的编译失败。`cmx-server-local` 字符串仅存在于 toml/.env，无代码硬编码。

## 四、改动清单

### 4.1 cmx-plugin/center_client

- `config.rs` map 化（见 §三）；头注释与 `load()` 内 4 处 "mock" 文案更新；**加载时对 urls 值含 `/api/` 打 warn**（旧端点写法检测，防双路径拼接）。
- 新建 `upstream.rs`：
  - `pub enum ProxyUpstream { Static(String), Discovery { service: String, group: String } }`
  - `pub fn proxy_upstream(key: &str) -> Option<ProxyUpstream>`：mode 分派查两 map，未知 mode 视同 local + warn。
  - `pub fn resolve(&self) -> Option<String>`：**先判 `GlobalServiceInstanceCache::is_initialized()`**（未初始化返回 None → 503，绝不 panic，`get()` 裸调用会 expect 崩溃）；healthy 过滤 + 随机选 + `metadata["http_port"]` 优先缺省 `instance.port` → `http://{ip}:{port}`。
  - 共享选例函数（私有 `resolve_with(cache: &ServiceInstanceCache, …)`，`ServiceInstanceCache::new/get/update` 全 pub 可构造，单测依赖注入，不碰进程单例）。
  - `pub async fn warm_proxy_upstreams()`：对 Discovery 目标 `subscribe_instances` 预热（参照 rpc.rs warmup 先例；dev http_url 下为 no-op）。
  - 启动日志：生效 mode、urls/discovery 快照、已挂反代目标清单（补偿 map 键拼写错误静默不挂的可见性）。

### 4.2 remote_importers

见 §三迁移清单第 2、3 行；`send_via_http` 需带 `outgoing_api_key` 过 mw_auth（现状已配，不变）。

### 4.3 三个反代壳（cmx-flow-api / cmx-rpt-api / cmx-rule-api，不新增依赖）

- 公开 API 收敛为 `with_resolver(resolver, api_key)`（删除 `new(base,…)`——全部调用方在 routes.rs 与壳内部，删除后无死代码）；`with_*_page_proxy(router, resolver, api_key)` 签名同步。
- `ProxyState`：基址 `String` → `resolver: Arc<dyn Fn() -> Option<String> + Send + Sync>`（**必须有 Send+Sync**，axum state 约束）；API 路由与页面反代层共享同一 resolver / reqwest client（顺带消除 merge_* 双客户端）。
- 每请求 resolve：`None` → 503 `{"code":503,"msg":"xx服务无可用实例（服务名 xxx）"}`（区别于 502 不可达）。转发内部逻辑（头处理/流式/三层鉴权注入）本批不动。

### 4.4 cmx-platform-app

- `routes.rs`：`*_remote_base()` → `*_upstream()` 返回 `Option<ProxyUpstream>`；`merge_*` 构造 resolver——**捕获启动期配置快照**（Static 固化返回基址；Discovery 每请求查实例缓存选例，不每请求反序列化 toml，消除一轮 M2 性能回退）；`service_topology()` target = 当前解析实例或 `None`（不用 `nacos://` 伪 scheme，避免探测面板恒红）；`flow_is_proxied()` = upstream 已配置。
- `lib.rs`：`init_infra()` 后（async 上下文内）调 `warm_proxy_upstreams()`。

### 4.5 三独立服务接入注册中心 + 配置中心

- **Cargo.toml（3 处）**：`cmx-service-base = { workspace = true, features = ["config-manager"] }` → `features = ["config-manager", "registry-config"]`（`init_infra`/`shutdown_infra` 均 `#[cfg(feature="registry-config")]` 门控，cmx-service-base/src/lib.rs:64-67）。改后先 `cargo check` 再继续（AGENTS 全局规则 3）。
- **main（3 处）**：
  - **删除** `init_config_manager()` 调用——与 `init_infra` 内的 `ConfigManager::initialize` 二次初始化冲突，并存会**启动必崩**（cmx-utils config_impl.rs:777-781）。
  - 改 `cmx_service_base::init_infra().await.map_err(|e| ChassisError::Config(e.to_string()))?`（无 `From<BaseError>`，直接 `?` 编译不过；create 阶段强依赖失败）。
  - 关停：`let res = chassis::run(spec).await; cmx_service_base::shutdown_infra().await; res`（**不得用 `?`**——Err 提前返回会跳过注销）。
- **env 配置**：cmx-report / cmx-rulesengine **新建** `.env`（全注释 Nacos 可选块；rules 与 `rules-server.toml.example` 的分工加注释说明），cmx-flowengine/.env 补块。开启 Nacos 时**必填**：

  ```bash
  NACOS_ENABLED=true
  NACOS_SERVER_ADDR=192.168.1.14:8848
  NACOS_NAMESPACE=dev13
  NACOS_NAMING_SERVICE_NAME=cmx-flow-server   # rpt/rule 对应 cmx-rpt-server / cmx-rule-server
  SERVICE_REGISTRY_PORT=8091                  # ★必填：不设回退 8080 注册错端口（rpt 8092 / rule 8094）
  ```
  模板注明 `SERVICE_REGISTRY_NAME` 优先级高于 `NACOS_NAMING_SERVICE_NAME`（config_model.rs:297/331/353）；配置中心子开关 `NACOS_CONFIG_ENABLED` + listener 变量对照 `config_model.rs:417-450`。
- 未开 `NACOS_ENABLED` 时 `create_registry_with_cache` 走 MockRegistry，不产生网络行为，与现状一致。

### 4.6 配置迁移（6 个 toml，逐键决策表——已经二轮逐文件核实）

| 文件 | mode 目标 | urls 目标 | discovery.services 目标 |
| --- | --- | --- | --- |
| cmx-portalservice/dev.toml | `http_url`（导入从 gRPC→自环 HTTP 为**有意取舍**：统一 dev 模式、降低对 nacos/rpc 依赖；`[rpc]` 保留闲置无害） | menu/perm/form→`http://127.0.0.1:8080`；flow→8091 保留；补 report→8092、rules→8094 | menu/perm/form→`cmx-portal-local`（门户 .env 实际注册名）；flow→`cmx-flow-server`（备未来切 discovery） |
| cmx-portalservice/portal-server.toml | **`http_url`**（否决一轮的 mock→local——该文件 140-148 配着三反代基址，归 local 会**静默丢三个反代**，rules 连 `/api/rules/*` 都没了） | 六键齐配（同 dev） | 同 dev |
| cmx-portalservice/dev-vpn.toml | `http_url`（行为零变化：flow 无 urls 值→继续无流程路由） | 保持无 flow 键 | menu/perm/form→`cmx-portal-local`；**不配 flow**（避免 grpc 切换时反代从无到有） |
| cmx-portalservice/dev-xty.toml | `http_url` | 同 dev | 同 dev |
| cmx-container/dev.toml | `http_url`、无 flow 键 | 保持现状形态 | **保留 `cmx-server-local`**——该工作区 .env 注册名即此，消费方视角反而正确 |
| cmx-container/dev-vpn.toml | 同上 | 同上 | 同上 |

- 所有注释从"完整端点"（`.../api/plugin/menu/import`）改写为"基址 + 统一路径"语义。
- 迁移逐键按**消费方视角核对真实注册名**，不做全局替换。

### 4.7 配置文档同步（config-sync 技能，必须执行）

本方案新增/修改 TOML 配置项与环境变量，按 `cmx-container/.agents/skills/config-sync` 规范必须同步四件套（已核实全工作区仅 `cmx-container/config/` 持有这套文件）：

**`config/config_template.toml`**（:284-325 一带）：

- `[center_client]` mode 注释更新（四模式语义 + 反代同读 mode；`local`/未知值不挂反代）。
- `[center_client.urls]`（:303）：改为自由表语义——键 = 服务键，值 = **纯基址**（无路径）；示例键按「L2 `##` 描述 + L3 `# key = value`」配对注释呈现，标注键所有权（menu/perm/form 归导入器、flow/report/rules 归反代）。
- `[center_client.discovery]`（:315-325 现为被注释可选块）：删四个旧 `*_service` 字段，改 `nacos_group` + `[center_client.discovery.services]` 自由表（同样按 L2/L3 配对给示例键）。

**`config/CONFIG_MANUAL.md`**（:706-807）：

- `[center_client]` / `[center_client.urls]` / `[center_client.discovery]` 三章节重写为 map 语义；**删除** `menu_service`/`perm_service`/`form_service`/`flow_service` 四个小节，新增 `[center_client.discovery.services]` 小节（类型 HashMap、键所有权、与 mode 的关系）。
- 章节末尾 env 覆盖说明更新为 map 键格式：`CENTER_CLIENT__URLS__<KEY>` / `CENTER_CLIENT__DISCOVERY__SERVICES__<KEY>`，并提醒纯数字值会被 try_parsing 转整数（值需带 scheme）。
- **目录条目同步增删**。

**`config/.env.template`**：`SERVICE_REGISTRY_*` / `NACOS_*` 变量已存在，无需新增变量；核对 `SERVICE_REGISTRY_PORT`（:29）说明改准确——回退链 `SERVICE_REGISTRY_PORT > NACOS_REGISTER_SERVER_PORT > server.port > 8080`，并标注"独立微服务（flow/rpt/rule-server）开启注册时**必填**（否则回退 8080 注册错端口）"。

**`config/ENV_MANUAL.md`**：注册中心与配置中心章节补充三服务接入场景的行为说明（create 阶段强依赖 / register 阶段仅 warn、`SERVICE_REGISTRY_NAME` 优先级高于 `NACOS_NAMING_SERVICE_NAME`）；目录同步。

三服务侧（cmx-flowengine / cmx-report / cmx-rulesengine）**无** config/ 四件套，新建的 `.env` 内容必须与上述 ENV_MANUAL 变量清单一致。

### 4.8 代码内文档更新清单

`center_client/config.rs` 头注释与 load() mock 文案、`center_client/mod.rs:8`、三反代壳 README（cmx-flow-api:20,120 / cmx-rpt-api:15,118 / cmx-rule-api:13,116 均写死旧语义）、`cmx-plugin/README.md:127`、`cmx-portalservice/README.md:107-112`。

## 五、验证方案

1. `cargo test -p cmx-plugin`：mode 分派矩阵、未知键容错、`resolve_with` 依赖注入（healthy 过滤 / http_port 优先 / 未初始化返 None）、urls 值含 `/api/` 告警。
2. `cargo check` 覆盖 **5 个 workspace**：cmx-container、cmx-portalservice、cmx-flowengine、cmx-report、cmx-rulesengine（跨 4 个 git 仓库，各自 check、分仓提交）。
3. 静态冒烟（回归）：起 flow-server + 门户，`curl http://127.0.0.1:8080/api/flow/v1/stats` 行为与改造前一致；门户启动日志出现 mode / 已挂反代目标清单。
4. Nacos 路径（可选，本地 192.168.1.14:8848 / dev13 可用）：三服务带注册 env 启动（日志确认注册端口 8091/8092/8094）→ 门户切 `http_discovery` → 验证反代命中实例、kill 一实例自动摘除；配置中心远程 toml 下发验证热更。
5. config-sync 自检（对照技能 §六 清单）：
   - [ ] TOML 配置项变更 → `config_template.toml` 与 `CONFIG_MANUAL.md` 已同步（含目录条目）
   - [ ] 环境变量说明变更 → `.env.template` 与 `ENV_MANUAL.md` 已同步（含目录条目）
   - [ ] 模板中所有「示例/可选/废弃」项的描述注释均为 `##`（L2）且与被注释项（L3）严格配对
   - [ ] `.env.template` 每个激活变量上方有 L1 说明注释
   - [ ] 删除的旧字段（四个 `*_service`）在手册中无残留引用

## 六、风险与对策

| 风险 | 对策 |
| --- | --- |
| map 键拼写错误静默不挂路由 | 启动日志打印 urls/discovery 快照 + 已挂目标清单 |
| urls 残留旧"完整端点"写法拼出双路径 | 加载时对值含 `/api/` 打 warn |
| Discovery 缓存未就绪首请求 | warmup 订阅 + 30s ServiceListSyncer 兜底；期间 503 语义明确 |
| `GlobalServiceInstanceCache` 未初始化 panic | resolve() 先判 `is_initialized()`，未初始化返 None |
| 三服务 create 阶段强依赖 Nacos（用户拍板） | 部署文档写明；register 失败仅 warn 不阻塞 |
| `SERVICE_REGISTRY_PORT` 缺省回退 8080 注册错端口 | 升为开启 Nacos 时必填项（二轮隐藏坑） |
| 随机 LB 无熔断/失败摘除 | P1-3 衔接点，本批不做 |
| env 纯数字值被 try_parsing 转整数 | 部署文档提醒值带 scheme（`http://…`） |
| 配置中心开启后优先级 toml ← 远程 ← env | 部署文档写明（env 最高） |

## 七、审查记录（两轮，决策留痕）

### 第一轮（general-purpose 子智能体，60 次工具调用全工作区核实）

- 高：portal-server.toml `mode="mock"` 分派盲区（已实证 :134）；三服务 Cargo.toml 缺 `registry-config` feature（已实证三处）；全局实例缓存单例 panic / 单测争抢一次性 `set`。
- 中：init_infra 失败策略未定（用户拍板：**强依赖失败**）；每请求 load 配置性能回退（对策：捕获启动期快照）；dev.toml 切 http_url 后 menu/perm/form 缺值（对策：指门户基址）；flow 键双消费者语义（对策：键所有权约定）；门户实注册名与 toml 旧值不一致（对策：逐键核对）。
- 采纳：导入器 http_discovery 复用共享选例函数；未解析实例时拓扑 target=None。
- 不采纳/缓议：chassis `ServiceSpec` shutdown_hooks（控范围，各 main 三行解决）；三反代壳公共类型抽取（留 P1-1 cmx-proxy-core）。

### 第二轮（Explore 子智能体，62 次工具调用）

- 高：**portal-server.toml 归 local 会静默丢三反代 → 改判 `http_url`**（推翻一轮建议，主智能体疑点成立）；**`init_infra().await?` 编译不过且与 init_config_manager 并存启动必崩**（对策：删轻量调用 + map_err 转换）。
- 中：遗漏 cmx-container 侧 2 个 toml（迁移清单 4→6）；urls 端点→基址为破坏性变更（对策：`/api/` warn）；dev 导入传输切换为有意取舍；`run().await?` 跳过注销（对策：`let res = …` 模式）；resolver 语义措辞修正（配置快照 + Discovery 每请求选例）。
- 低：resolver 类型补 `Send+Sync`；check 范围改 5 workspace；文档更新面扩展；report/rules 需**新建** .env；启动日志区分"未配置节/显式 local"。
- 隐藏坑：`SERVICE_REGISTRY_PORT` 缺省回退 8080（升必填）。
- 已实证成立：env 嵌套覆盖兼容 HashMap、统一导入端点挂在门户、`chassis::run` 返回后可接注销、MockRegistry 默认无网络行为、Router 泛型自洽、mode 单值无交叉读取。

### 第三轮（用户指正）

- **遗漏 config-sync 配置文档同步**：方案大量新增/修改 TOML 配置项与环境变量，按 `cmx-container/.agents/skills/config-sync` 规范必须同步 `cmx-container/config/` 四件套（`config_template.toml` / `.env.template` / `CONFIG_MANUAL.md` / `ENV_MANUAL.md`）。已补 §4.7（含逐文件条目级改动与 L2/L3 注释配对约定）与 §五验证清单第 5 项（config-sync 自检 checklist）。

## 八、实施顺序建议

1→2→3（cmx-container：config map 化 + upstream.rs + remote_importers + 三反代壳 + cmx-platform-app，`cargo check` + `cargo test -p cmx-plugin`）→ 4（§4.7 config-sync 四件套同步）→ 5（三服务 Cargo feature + main + .env，各自 `cargo check`）→ 6（6 个 toml 迁移）→ 7（§4.8 代码内文档）→ 验证 §五。跨 4 个 git 仓库分仓提交（禁自动提交，等用户指令）。
