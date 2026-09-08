# cmx-center-client per-key 服务定位与传输混用方案（v3）

> 日期：2026-08-22 · 状态：已实施
> 前置：`20260822_cmx-center-client_服务定位map化与微服务接入Nacos方案.md`（v2，map 化 + 三服务接入 Nacos，已实施）
> 本批：v2 的"mode 全局单选"升级为"per-key 双维度独立配置"——不同服务键可混用定位方式与传输协议。

## 一、问题

v2 后 `[center_client]` 仍是 `mode` 全局单选（http_url / http_discovery / grpc / local），把**定位**（怎么找到目标）与**传输**（怎么通信）两个正交维度耦合在一个进程级开关上：

1. **定位混不了**：flow 本机静态调试 + report 走 Nacos 联调，同一环境做不到。
2. **传输混不了**：menu 中心提供 gRPC、form 中心只有 HTTP，只能全进程统一。
3. 反代场景传输协议无 gRPC 选项（浏览器流量必须 HTTP 透明转发），`grpc` 模式对反代实际只是"Nacos 定位"——mode 语义失真。

## 二、设计

### 配置形态（v3：services 单表）

```toml
[center_client]
default_transport = "http"        # 服务间调用全局传输缺省（http|grpc），键级可覆盖
nacos_group = "DEFAULT_GROUP"     # discovery 定位的键共用（从 discovery 子节提升到顶层）
timeout_ms = 30000

[center_client.services]          # 服务键 → 服务描述（自由表，新增微服务加一行）
menu   = { url = "http://127.0.0.1:8080", discovery = "cmx-portal-local" }  # 双路备好，url 优先
perm   = { discovery = "cmx-perm-center", transport = "grpc" }              # Nacos + gRPC
form   = { discovery = "cmx-form-center" }                                  # Nacos + HTTP（缺省）
flow   = { url = "http://127.0.0.1:8091", discovery = "cmx-flow-server" }   # 反代目标
```

- **`url` / `discovery` 二选一定位**：并存时 **url 优先**（非主备兜底：url 不可达即 502 不会切
  discovery，并存时启动打 warn；删 url 即切服务发现选例）——保留 v2 环境
  toml"两路都备好、切换只动一档"的配置习惯，且不再依赖 mode 开关。
- **`transport` 仅服务间调用生效**（remote_importers 的 send/list 分派）；反向代理恒 HTTP
  （透明转发语义），反代键配 `transport = "grpc"` 打 warn 提示无效。
- **`grpc` 传输必须配 `discovery`**（gRPC 经全局 RPC 客户端按服务名路由，不支持静态地址直连），
  配了 `url` 打 warn。
- `mode` / `[center_client.urls]` / `[center_client.discovery]` 三段**退役**（不考虑向前兼容）；
  `load()` 经 toml::Value 中转检测旧字段，出现时打迁移 warn（不报错，被忽略）。
- `local` 语义由"services 表为空"自然表达。

### 消费点改造清单（全量，不留双轨）

| 消费点 | 位置 | v2 行为 | v3 行为 |
| --- | --- | --- | --- |
| 配置结构 | `cmx-plugin/center_client/config.rs` | mode + urls + discovery(nacos_group+services) | `ServiceEntry { url, discovery, transport }` + services 单表 + `default_transport` + 顶层 `nacos_group` |
| 传输分派 | `remote_importers/mod.rs` send/send_list | 按 `config.mode` 全局匹配 | 按 `config.transport_of(category)`（键级 ?? 全局，空白/未知回退 http） |
| HTTP 客户端构造 | `RemoteImporterContext::new` | 仅 http 系 mode 构造 | 无条件构造（per-key 混存两路都要；reqwest 惰性连接零开销） |
| 服务名解析 | `resolve_service_name` | 查 `discovery.services.{key}` | 查 `services.{key}.discovery` |
| HTTP 端点解析 | `resolve_http_url` | mode==http_url 查 urls / 否则选例核 | `services.{key}.url` 优先 → 静态；否则 `discovery` → 选例核 |
| 反代目标分派 | `upstream_from_config` | mode 分派查两张表 | 逐键：`url` → Static、`discovery` → Discovery；两字段空 → warn + None；grpc 覆盖打 warn |
| 订阅预热 | `warm_proxy_upstreams` | mode 为 discovery 系才收集 | 遍历 services 全部 discovery 非空键 |
| 启动快照 | `log_center_client_snapshot` | mode + 两表 keys | default_transport + 每键"定位 + 生效传输"描述 |
| 导入器本地/远程切换 | `cmx-platform-app/config/iam.rs` | `matches!(mode, "grpc"|"http_url"|"http_discovery")` | `has_remote_import_keys()`（menu/perm/form 任一键存在） |
| 值校验 | config load | urls 值含 `/api/` warn | + transport 值域校验、grpc+url 无效组合、旧形态迁移提示 |

### 键所有权约定（不变）

- `menu` / `perm` / `form`：归远程导入器（DataCategory）；任一键存在 → DefinitionImporterBundle 取远程实现（Bundle 粒度，缺键在调用时报错指明）。
- `flow` / `report` / `rules`：归反向代理（ProxyUpstream）。

## 三、实施记录

- **config.rs**：`ServiceEntry` + `CenterClientConfig` v3（`transport_of` / `has_remote_import_keys`）+ `warn_legacy_shape` / `warn_misplaced_values`；5 个单测（单表反序列化 / 缺省 / 旧字段忽略 / transport 覆盖链 / 远程键检测）。
- **upstream.rs**：`upstream_from_config` 逐键分派（url 优先）；warm/snapshot 逐键化；4 个单测重写（per-key 矩阵含混用、url 优先、空白值、group 缺省）。
- **remote_importers**：send/send_list 按 `transport_of` 分派；`new` 无条件构造 HTTP 客户端；`resolve_service_name` / `resolve_http_url` 逐键解析；模块文档改 per-key。
- **iam.rs**：`is_remote` 改 `has_remote_import_keys()`，远程模式日志列出已配置键。
- **7 个 toml 迁移**（tomllib 验证键位）：cmx-container dev/dev-vpn/config_template；cmx-portalservice portal-server/dev/dev-vpn/dev-xty（后三者为本地未入库文件）。
- **config-sync 四件套**：config_template.toml / CONFIG_MANUAL.md（含"旧配置形态（v2 已废弃）"章节）/ .env.template（修复了 v2 漏改的 `CENTER_CLIENT__MODE=mock` 残留）/ ENV_MANUAL.md。
- **验证**：cmx-container workspace check 全绿；clippy 改动 crate 零新警告（platform-app 唯一警告为存量 datasource.rs，不属本批）；cmx-plugin 254 单测全过；portalservice / flowengine 跨 ws check 通过。

## 四、边界与风险

- **旧字段静默忽略**：配置了 mode/urls/discovery 的旧 toml 在新代码下全内嵌 + 打迁移 warn——升级部署必须迁 toml（文档 + warn 双提示）。
- **transport_of 宽容回退**：未知传输值回退 http 而非报错（启动 warn + 快照可见），避免单键笔误拖垮整个导入链。
- **Bundle 粒度**：只配 menu 不配 perm 时 Bundle 三件全远程，perm 缺键在首次调用时报"未配置服务名"——错误信息指明键名。
- **同键 url+discovery 并存**：discovery 沉默（仅 url 生效）；服务发现订阅预热仍会订阅它（无害，且删 url 即切换无需重启预热）。
- gRPC 键的 RPC 通道依赖 `[rpc]` 启用与 GlobalRpcClient 初始化（未初始化时报错，不 panic）。
