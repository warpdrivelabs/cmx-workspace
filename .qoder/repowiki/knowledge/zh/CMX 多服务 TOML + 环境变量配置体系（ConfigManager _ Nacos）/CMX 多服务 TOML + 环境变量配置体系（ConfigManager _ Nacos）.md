---
kind: configuration_system
name: CMX 多服务 TOML + 环境变量配置体系（ConfigManager / Nacos）
category: configuration_system
scope:
    - '**'
source_files:
    - cmx-container/config/config_template.toml
    - cmx-container/config/docker.toml
    - cmx-container/config/.env.template
    - cmx-container/config/CONFIG_MANUAL.md
    - cmx-container/config/ENV_MANUAL.md
    - cmx-flowengine/flow-server.toml.example
    - cmx-rulesengine/rules-server.toml.example
    - CMXPortalManager/.env
    - CMXHTMLDesigner/.env
---

## 1. 采用的系统/框架

- **配置格式**：TOML（`config_template.toml`、各引擎 `*-server.toml`、`docker.toml`），使用 Rust `serde`/`toml` 反序列化。
- **加载器**：通过统一的 `ConfigManager`（`cmx-service-base` 提供的 `ChassisConfig`）加载，支持 `__` 分隔的环境变量覆盖约定（如 `SERVER__PORT` → `server.port`、`AUTH__JWT__SECRET` → `auth.jwt.secret`）。
- **远程配置中心**：Nacos（`SERVICE_REGISTRY_TYPE=nacos` / `CONFIG_CENTER_TYPE=nacos`），启动时从 Nacos 拉取配置，优先级高于本地 TOML。
- **注册中心**：Nacos（也可 mock），用于服务发现与实例元数据注入（`grpc_port` 自动注入）。
- **前端工程**：CMXPortalManager / CMXHTMLDesigner 使用 Vite 的 `import.meta.env.*` 读取构建期注入的 `VITE_*` 环境变量（`.env` / `.env.production`），属于独立的前端构建期配置，与后端 TOML 体系解耦。

## 2. 关键文件

| 文件 | 作用 |
|---|---|
| `cmx-container/config/config_template.toml` | 平台容器（门户+插件+RPC+存储+认证+MDM分发等）完整 TOML 模板 |
| `cmx-container/config/docker.toml` | Docker 部署专用 TOML（路径改为 `/app/*`，启用 RPC） |
| `cmx-container/config/.env.template` | 所有可注入环境变量的参考模板 |
| `cmx-container/config/CONFIG_MANUAL.md` | 逐字段说明（类型、默认值、示例、环境变量映射） |
| `cmx-container/config/ENV_MANUAL.md` | 环境变量手册（前缀、优先级、废弃旧名） |
| `cmx-flowengine/flow-server.toml.example` | 流程引擎微服务的 TOML 示例（注释中写明加载顺序） |
| `cmx-rulesengine/rules-server.toml.example` | 规则引擎微服务 TOML 示例 |
| `cmx-container/config/.env` / `../../../../../cmx-portal-manager` / `../../../../../cmx-html-designer` | 各前端工程的构建期环境变量 |

## 3. 架构与约定

### 3.1 三层叠加的配置来源（文档明确定义优先级）

1. **环境变量** — 最高优先级，不可被覆盖；敏感项（Nacos 连接、JWT 密钥、RS256 私钥、超管密码、`SERVICE_AUTH__OUTGOING_API_KEY` 等）强制要求通过环境变量注入，禁止写入 TOML。
2. **Nacos 远程配置** — 从配置中心拉取的配置，位于环境变量之下、本地 TOML 之上。
3. **本地 TOML 文件** — 由 `CONFIG_FILE` 指定或默认路径（如 `./flow-server.toml`、`./config.toml`）。
4. **代码默认值** — 最低层。

### 3.2 统一的服务间通信配置模型

`[center_client]` 采用 per-key 单表形态（`[center_client.services]`），每个服务键（`menu`/`perm`/`form`/`flow`/`report`/`rules`/`model`/`mdm`）自带 `url`（静态基址）、`discovery`（Nacos 服务名）、`transport`（`http`/`grpc`）。新增微服务只需在 TOML 加一行键值，无需改代码；环境变量可通过 `CENTER_CLIENT__SERVICES__<KEY>__<FIELD>` 覆盖。

### 3.3 部署模式契约

`[deploy].mode = "mono" | "micro"` 是启动期契约：
- `mono`（默认）：一个进程服务所有域/应用/模块，`get_app_id()` 固定返回 `"default"`，数据源加载全部 `status=1 AND archived=0` 的记录，`[app]` 块整体不生效。
- `micro`：按 `[app]` 三元组精确过滤数据源，`module_code` 必需且不能为 `default`，模块导入守卫保留。

`DEPLOY__MODE` 环境变量可覆盖该值；切换时需执行迁移脚本把历史 `app_id` 统一为 `'default'`。

### 3.4 数据库/Redis/存储的多实例数组

`[[databases]]`、`[[storage.instances]]`、`[[auth.static_api_keys]]`、`[[auth.oauth2.providers]]`、`[[plugin.auto_install.plugins]]` 等均采用 TOML 数组段，支持在同一进程中配置多个实例（多库、多存储平台、多 OAuth2 Provider、自动安装插件列表）。

### 3.5 各引擎共享的 chassis 配置

所有 Rust 服务（portal、flow、report、rule、mdm、model）均通过 `cmx-service-base::init_infra()` 接入同一套 ConfigManager，因此 `[server]`、`[[databases]]`、`[assets]`、`[auth]` 等段在各引擎 TOML 中形态一致，仅端口和 db_url 不同。

### 3.6 前端构建期配置

CMXPortalManager 与 CMXHTMLDesigner 各自维护 `.env` / `.env.production`，通过 Vite 的 `import.meta.env.VITE_*` 在构建期注入到前端代码，与后端 TOML 体系完全隔离。

## 4. 约定与约束

| 规则 | 来源/依据 |
|---|---|
| 注册中心与配置中心相关配置必须通过环境变量注入，不支持在 TOML 中配置（安全考虑） | `ENV_MANUAL.md` 首节声明 |
| 敏感信息（JWT 密钥、RS256 私钥、超管密码、`SERVICE_AUTH__OUTGOING_API_KEY`）务必通过环境变量注入，不要写入 TOML | `ENV_MANUAL.md` 认证章节警告 |
| 环境变量命名遵循 `SECTION__KEY`（双下划线分隔层级），与 ConfigManager 的 `__` 约定同名 | `ENV_MANUAL.md` 框架级环境变量章节 |
| 旧版 `FLOW_/RPT_/RULE_/MDM_/MODEL_` 前缀及 `CMX_*` 统一前缀已废弃，改用 `SERVER__*`、`ASSETS__*`、`AUTH__*`、`CENTER_CLIENT__*` 等族 | `ENV_MANUAL.md` 多处废弃说明 |
| `center_client` 旧形态（`mode`/`urls`/`discovery.services`）已废弃，出现时被忽略并打迁移 warn | `CONFIG_MANUAL.md` 旧配置形态章节 |
| `url` 值需带 scheme（如 `http://...`），纯数字会被环境变量层解析为整数导致反序列化失败 | `ENV_MANUAL.md` 基础服务中心环境变量注释 |
| gRPC 传输的键必配 `discovery`（gRPC 经全局 RPC 客户端按服务名路由，不支持静态地址直连） | `CONFIG_MANUAL.md` center_client 章节 |
| mono 切换到 micro 后需执行迁移脚本把历史 `app_id` 统一为 `'default'`，否则历史数据不可见 | `CONFIG_MANUAL.md` 部署模式章节 |
| 反向代理恒走 HTTP，给 flow/report/rules 配 `transport = "grpc"` 会打 warn 提示 | `CONFIG_MANUAL.md` center_client 章节 |
| 健康检查/连接池/超时等参数均有默认值，生产建议显式调整（如 `max_connections` 建议 20-50） | `CONFIG_MANUAL.md` 各段说明 |
| 页面资产目录可通过 `ASSETS__ROOT` 环境变量覆盖，缺省回退 `./data` | `config_template.toml` assets 段注释 |
| 各引擎 TOML 加载顺序：`CONFIG_FILE` 指定文件 → 默认 `./xxx-server.toml` → 环境变量覆盖 | `flow-server.toml.example` 头部注释 |
| 独立微服务开启注册时必须填 `SERVICE_REGISTRY_PORT`，否则注册成 8080 错端口 | `.env.template` 与 `ENV_MANUAL.md` 注册中心章节 |

## 5. 前端侧补充

CMXPortalManager 与 CMXHTMLDesigner 作为 Vite 前端工程，各自根目录下的 `.env` / `.env.production` 通过 `VITE_*` 前缀注入构建期常量（如 API 基址、调试开关），与后端 TOML 体系互不干扰。两个工程共用 `packages/` 下的共享 npm 包（cmx-data-comp、cmx-icon-resource、cmx-ui5-runtime），这些包的发布与版本由顶层 `package.json` 的 npm workspaces 管理，不属于运行时配置范畴。