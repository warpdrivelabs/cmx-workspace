---
kind: logging_system
name: 基于 tracing 的分层结构化日志系统（chassis 统一初始化）
category: logging_system
scope:
    - '**'
source_files:
    - cmx-container/crates/libs/cmx-web-chassis/src/lib.rs
    - cmx-container/crates/libs/cmx-web-chassis/src/format.rs
    - cmx-container/crates/libs/cmx-web-chassis/src/config.rs
    - cmx-container/Cargo.toml
    - cmx-flowengine/flow-server.toml
    - cmx-container/config/config_template.toml
    - cmx-container/logs/cmx-server.log.2026-08-11
    - cmx-flowengine/logs/flow.log.2026-08-19
---

## 1. 使用的框架与工具

后端 Rust 服务统一采用 **tracing + tracing-subscriber + tracing-appender** 作为日志/追踪框架：
- `tracing`：事件记录 API（`info!` / `warn!` / `error!` / `debug!` / `trace!`），所有 crate 通过 workspace 依赖声明。
- `tracing-subscriber`：订阅器，提供 `EnvFilter`（按模块/crate 粒度过滤）、`fmt::layer`（格式化输出）。
- `tracing-appender`：文件追加器，使用 `RollingFileAppender` 按天轮转日志。

前端 Node 应用（CMXHTMLDesigner、CMXPortalManager）未引入第三方日志库，直接复用浏览器 `console.log` / `console.warn` / `console.error`，并在设计器中把 `ctx.log` 桥接到 `console.log`，错误路径用 `console.warn` 打印带前缀的上下文信息。

## 2. 核心文件与位置

| 职责 | 文件 | 说明 |
|---|---|---|
| 日志初始化入口 | `cmx-container/crates/libs/cmx-web-chassis/src/lib.rs` | `run()` 首步调用 `init_tracing(&spec.config)`，返回 `WorkerGuard` 保活至进程退出 |
| 控制台格式器 | `cmx-container/crates/libs/cmx-web-chassis/src/format.rs` | 自定义 `CompactFormatter`，输出 `[时间] [级别] [线程名+ID] [file:line]: message`，带 ANSI 颜色 |
| 配置加载 | `cmx-container/crates/libs/cmx-web-chassis/src/config.rs` | `ChassisConfig::load` 从 `[server]` 段 + `SERVER__*` 环境变量装配 `log_dir` / `log_level` / `log_file` |
| 工作区依赖声明 | `cmx-container/Cargo.toml` | `[workspace.dependencies]` 集中声明 `tracing = "0.1"`、`tracing-subscriber = { version = "0.3", features = ["env-filter"] }`、`tracing-appender = "0.2"` |
| 独立微服务配置 | `cmx-flowengine/flow-server.toml` | `[server] log_dir = "logs"`、`log_level = "info"`，与平台共用同一 chassis |
| 平台模板配置 | `cmx-container/config/config_template.toml` | `[server]` 段注释说明 `log_dir` / `log_level` 默认值及 `SERVER__LOG_DIR` / `SERVER__LOG_LEVEL` 覆盖方式 |
| 日志产出样例 | `cmx-container/logs/cmx-server.log.*`、`cmx-flowengine/logs/flow.log.*` | 每日轮转 JSON 文件 |

## 3. 架构与约定

### 3.1 分层日志（双 sink）
`init_tracing` 同时注册两个 layer：
- **控制台层**：`fmt::layer().event_format(CompactFormatter).with_writer(stdout).with_ansi(true)`，用于开发时彩色可读输出。
- **文件层**：`fmt::layer().json().with_writer(non_blocking(file_appender)).with_target(true).with_thread_ids(true).with_file(true).with_line_number(true).with_thread_names(true)`，输出结构化 JSON，包含 `timestamp`、`level`、`fields.message`、`target`、`filename`、`line_number`、`threadName`、`threadId` 等字段。

文件写入通过 `non_blocking` 异步化，避免阻塞业务线程；`WorkerGuard` 由 `run()` 持有直到进程退出，保证优雅关闭期间日志不丢失。

### 3.2 日志级别与过滤
- 默认级别来自 `ChassisConfig::defaults("service")` 的 `log_level = "info"`。
- 可通过 `RUST_LOG` 环境变量（`EnvFilter::try_from_default_env()`）或 `SERVER__LOG_LEVEL` 覆盖，支持细粒度如 `info,cmx_access=off`。
- 控制台与文件共享同一个 `EnvFilter`，即同一次运行下两级输出遵循相同过滤规则。

### 3.3 配置来源优先级
`ChassisConfig::load(service, default_toml)` 按以下顺序合并：
1. `ChassisConfig::defaults(service)`：`host=0.0.0.0`、`port=8080`、`log_dir="logs"`、`log_file="<service>.log"`、`log_level="info"`、`graceful_timeout_secs=10`。
2. 可选 TOML 文件的 `[server]` 段（路径由 `CONFIG_FILE` 指定，各服务传不同文件名，如 `flow-server.toml`、`portal-server.toml`）。
3. 环境变量 `SERVER__HOST` / `SERVER__PORT` / `SERVER__LOG_DIR` / `SERVER__LOG_LEVEL` / `SERVER__GRACEFUL_TIMEOUT_SECS`（与 ConfigManager 的 `__` 约定同名，保证与业务配置源一致）。

旧版顶层散字段（如直接在 toml 根写 `log_level`）会被 `eprintln!` 提示迁移到 `[server]` 段，且不生效——这是显式的向后兼容约束。

### 3.4 轮转策略
使用 `RollingFileAppender::new(Rotation::DAILY, &config.log_dir, &config.log_file)`，按天轮转，文件名形如 `cmx-server.log.2026-08-11`、`flow.log.2026-08-19`。每个服务的 `log_file` 前缀取自服务名（`ServiceSpec.name`），因此多服务共存时不会互相覆盖。

### 3.5 结构化字段约定
JSON 日志字段固定为：
- `timestamp`：UTC ISO 8601 精确到微秒（`%Y-%m-%dT%H:%M:%S%.6fZ`）。
- `level`：`ERROR` / `WARN` / `INFO` / `DEBUG` / `TRACE`。
- `fields.message`：业务消息体（由 `info!` / `warn!` 宏的字符串参数提供）。
- `target`：触发日志的 crate/module 路径（如 `cmx_plugin::center_client::config`）。
- `filename`、`line_number`：源码定位。
- `threadName`、`threadId`：Tokio worker 线程标识。

这些字段由 `tracing_subscriber::fmt::layer().json()` 自动注入，业务代码只需通过命名参数（如 `info!(service = %name, hook = %hook_name, "启动钩子执行中…")`）补充业务维度。

### 3.6 前端日志
- CMXHTMLDesigner 与 CMXPortalManager 未引入日志框架，直接使用 `console.log` / `console.warn` / `console.error`。
- 设计器内部将 `ctx.log` 桥接为 `console.log`，错误场景统一用 `console.warn` 并带上 `[module-name]` 前缀（如 `[designer-app]`、`[cmx-page-dialog]`），便于在浏览器控制台快速区分来源。
- 测试用例（`cmx-console.test.js`）直接断言 `console.log/warn/error` 的输出行为。

## 4. 约定与约束

1. **所有 Rust 服务必须通过 `cmx_web_chassis::run` 启动**，以复用统一的日志初始化、中间件栈和优雅关闭逻辑；新服务不得自行 `tracing_subscriber::init`。
2. **日志级别仅通过 `[server].log_level` 或 `SERVER__LOG_LEVEL` 修改**，禁止在业务代码中硬编码级别。
3. **日志目录仅通过 `[server].log_dir` 或 `SERVER__LOG_DIR` 修改**，默认 `logs` 相对进程工作目录。
4. **TOML 中框架级配置必须放在 `[server]` 段**，顶层散字段已废弃且会打印迁移警告。
5. **文件日志保持非阻塞**：`WorkerGuard` 必须在进程生命周期内持有，不可提前 drop，否则后台写入线程终止导致日志丢失。
6. **JSON 日志字段是契约**：下游日志采集系统（如 ELK/Loki）应解析 `timestamp`、`level`、`fields.message`、`target`、`filename`、`line_number`、`threadName`、`threadId` 等固定字段。
7. **前端不使用第三方日志库**，统一走 `console.*`，并通过模块前缀区分来源，便于调试。
8. **跨服务日志可关联**：通过 `target`（crate/module 路径）和 `threadName` 可区分不同 crate 与 Tokio worker 线程，结合业务字段（如 `service`、`hook`）实现请求级追踪。

## 5. 适用性判断

本仓库的后端（cmx-container、cmx-flowengine、cmx-mdm、cmx-model、cmx-portalservice、cmx-report、cmx-rulesengine）全部基于 Rust 并使用统一的 tracing 日志体系；前端 Node 应用使用浏览器 console 日志。该类别完全适用。

<result>
{
  "title": "基于 tracing 的分层结构化日志系统（chassis 统一初始化）",
  "content": "## 1. 使用的框架与工具\n\n后端 Rust 服务统一采用 **tracing + tracing-subscriber + tracing-appender** 作为日志/追踪框架：\n- `tracing`：事件记录 API（`info!` / `warn!` / `error!` / `debug!` / `trace!`），所有 crate 通过 workspace 依赖声明。\n- `tracing-subscriber`：订阅器，提供 `EnvFilter`（按模块/crate 粒度过滤）、`fmt::layer`（格式化输出）。\n- `tracing-appender`：文件追加器，使用 `RollingFileAppender` 按天轮转日志。\n\n前端 Node 应用（CMXHTMLDesigner、CMXPortalManager）未引入第三方日志库，直接复用浏览器 `console.log` / `console.warn` / `console.error`，并在设计器中把 `ctx.log` 桥接到 `console.log`，错误路径用 `console.warn` 打印带前缀的上下文信息。\n\n## 2. 核心文件与位置\n\n| 职责 | 文件 | 说明 |\n|---|---|---|\n| 日志初始化入口 | `cmx-container/crates/libs/cmx-web-chassis/src/lib.rs` | `run()` 首步调用 `init_tracing(&spec.config)`，返回 `WorkerGuard` 保活至进程退出 |\n| 控制台格式器 | `cmx-container/crates/libs/cmx-web-chassis/src/format.rs` | 自定义 `CompactFormatter`，输出 `[时间] [级别] [线程名+ID] [file:line]: message`，带 ANSI 颜色 |\n| 配置加载 | `cmx-container/crates/libs/cmx-web-chassis/src/config.rs` | `ChassisConfig::load` 从 `[server]` 段 + `SERVER__*` 环境变量装配 `log_dir` / `log_level` / `log_file` |\n| 工作区依赖声明 | `cmx-container/Cargo.toml` | `[workspace.dependencies]` 集中声明 `tracing = \"0.1\"`、`tracing-subscriber = { version = \"0.3\", features = [\"env-filter\"] }`、`tracing-appender = \"0.2\"` |\n| 独立微服务配置 | `cmx-flowengine/flow-server.toml` | `[server] log_dir = \"logs\"`、`log_level = \"info\"`，与平台共用同一 chassis |\n| 平台模板配置 | `cmx-container/config/config_template.toml` | `[server]` 段注释说明 `log_dir` / `log_level` 默认值及 `SERVER__LOG_DIR` / `SERVER__LOG_LEVEL` 覆盖方式 |\n| 日志产出样例 | `cmx-container/logs/cmx-server.log.*`、`cmx-flowengine/logs/flow.log.*` | 每日轮转 JSON 文件 |\n\n## 3. 架构与约定\n\n### 3.1 分层日志（双 sink）\n`init_tracing` 同时注册两个 layer：\n- **控制台层**：`fmt::layer().event_format(CompactFormatter).with_writer(stdout).with_ansi(true)`，用于开发时彩色可读输出。\n- **文件层**：`fmt::layer().json().with_writer(non_blocking(file_appender)).with_target(true).with_thread_ids(true).with_file(true).with_line_number(true).with_thread_names(true)`，输出结构化 JSON，包含 `timestamp`、`level`、`fields.message`、`target`、`filename`、`line_number`、`threadName`、`threadId` 等字段。\n\n文件写入通过 `non_blocking` 异步化，避免阻塞业务线程；`WorkerGuard` 由 `run()` 持有直到进程退出，保证优雅关闭期间日志不丢失。\n\n### 3.2 日志级别与过滤\n- 默认级别来自 `ChassisConfig::defaults(\"service\")` 的 `log_level = \"info\"`。\n- 可通过 `RUST_LOG` 环境变量（`EnvFilter::try_from_default_env()`）或 `SERVER__LOG_LEVEL` 覆盖，支持细粒度如 `info,cmx_access=off`。\n- 控制台与文件共享同一个 `EnvFilter`，即同一次运行下两级输出遵循相同过滤规则。\n\n### 3.3 配置来源优先级\n`ChassisConfig::load(service, default_toml)` 按以下顺序合并：\n1. `ChassisConfig::defaults(service)`：`host=0.0.0.0`、`port=8080`、`log_dir=\"logs\"`、`log_file=\"<service>.log\"`、`log_level=\"info\"`、`graceful_timeout_secs=10`。\n2. 可选 TOML 文件的 `[server]` 段（路径由 `CONFIG_FILE` 指定，各服务传不同文件名，如 `flow-server.toml`、`portal-server.toml`）。\n3. 环境变量 `SERVER__HOST` / `SERVER__PORT` / `SERVER__LOG_DIR` / `SERVER__LOG_LEVEL` / `SERVER__GRACEFUL_TIMEOUT_SECS`（与 ConfigManager 的 `__` 约定同名，保证与业务配置源一致）。\n\n旧版顶层散字段（如直接在 toml 根写 `log_level`）会被 `eprintln!` 提示迁移到 `[server]` 段，且不生效——这是显式的向后兼容约束。\n\n### 3.4 轮转策略\n使用 `RollingFileAppender::new(Rotation::DAILY, &config.log_dir, &config.log_file)`，按天轮转，文件名形如 `cmx-server.log.2026-08-11`、`flow.log.2026-08-19`。每个服务的 `log_file` 前缀取自服务名（`ServiceSpec.name`），因此多服务共存时不会互相覆盖。\n\n### 3.5 结构化字段约定\nJSON 日志字段固定为：\n- `timestamp`：UTC ISO 8601 精确到微秒（`%Y-%m-%dT%H:%M:%S%.6fZ`）。\n- `level`：`ERROR` / `WARN` / `INFO` / `DEBUG` / `TRACE`。\n- `fields.message`：业务消息体（由 `info!` / `warn!` 宏的字符串参数提供）。\n- `target`：触发日志的 crate/module 路径（如 `cmx_plugin::center_client::config`）。\n- `filename`、`line_number`：源码定位。\n- `threadName`、`threadId`：Tokio worker 线程标识。\n\n这些字段由 `tracing_subscriber::fmt::layer().json()` 自动注入，业务代码只需通过命名参数（如 `info!(service = %name, hook = %hook_name, \"启动钩子执行中…\")`）补充业务维度。\n\n### 3.6 前端日志\n- CMXHTMLDesigner 与 CMXPortalManager 未引入日志框架，直接使用 `console.log` / `console.warn` / `console.error`。\n- 设计器内部将 `ctx.log` 桥接为 `console.log`，错误场景统一用 `console.warn` 并带上 `[module-name]` 前缀（如 `[designer-app]`、`[cmx-page-dialog]`），便于在浏览器控制台快速区分来源。\n- 测试用例（`cmx-console.test.js`）直接断言 `console.log/warn/error` 的输出行为。\n\n## 4. 约定与约束\n\n1. **所有 Rust 服务必须通过 `cmx_web_chassis::run` 启动**，以复用统一的日志初始化、中间件栈和优雅关闭逻辑；新服务不得自行 `tracing_subscriber::init`。\n2. **日志级别仅通过 `[server].log_level` 或 `SERVER__LOG_LEVEL` 修改**，禁止在业务代码中硬编码级别。\n3. **日志目录仅通过 `[server].log_dir` 或 `SERVER__LOG_DIR` 修改**，默认 `logs` 相对进程工作目录。\n4. **TOML 中框架级配置必须放在 `[server]` 段**，顶层散字段已废弃且会打印迁移警告。\n5. **文件日志保持非阻塞**：`WorkerGuard` 必须在进程生命周期内持有，不可提前 drop，否则后台写入线程终止导致日志丢失。\n6. **JSON 日志字段是契约**：下游日志采集系统（如 ELK/Loki）应解析 `timestamp`、`level`、`fields.message`、`target`、`filename`、`line_number`、`threadName`、`threadId` 等固定字段。\n7. **前端不使用第三方日志库**，统一走 `console.*`，并通过模块前缀区分来源，便于调试。\n8. **跨服务日志可关联**：通过 `target`（crate/module 路径）和 `threadName` 可区分不同 crate 与 Tokio worker 线程，结合业务字段（如 `service`、`hook`）实现请求级追踪。\n\n## 5. 适用性判断\n\n本仓库的后端（cmx-container、cmx-flowengine、cmx-mdm、cmx-model、cmx-portalservice、cmx-report、cmx-rulesengine）全部基于 Rust 并使用统一的 tracing 日志体系；前端 Node 应用使用浏览器 console 日志。该类别完全适用。