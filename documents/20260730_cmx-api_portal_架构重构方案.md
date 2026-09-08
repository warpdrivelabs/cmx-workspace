# cmx-api/portal 架构重构方案：模型中心独立化

## 一、现状分析

### 1.1 当前 crate 依赖拓扑

```
web-server
  ├── cmx-api (api_routes 聚合)
  │     ├── portal/PortalModule ← 所有门户 handler 堆在此
  │     │     ├── ai.rs          → cmx_portal::ai/agent
  │     │     ├── meta.rs        → cmx_portal::meta
  │     │     ├── pages.rs       → cmx_portal::pages (= cmx_form 再导出)
  │     │     ├── data.rs        → cmx_portal::fact/help
  │     │     ├── notify.rs      → cmx_portal::notify
  │     │     ├── launcher.rs    → cmx_portal::launcher
  │     │     ├── registry.rs    → cmx_portal::dam/service_catalog/meta
  │     │     ├── definitions.rs → cmx_portal::definitions (= cmx_model 再导出)  ← 模型中心
  │     │     ├── flexible_combination.rs → cmx_portal::flexible_combination (= cmx_model) ← 模型中心
  │     │     └── model.rs       → cmx_model_center (直接依赖)  ← 模型中心
  │     ├── cmx-portal (门面，再导出 cmx_model + cmx_form)
  │     └── cmx-model-center
  ├── cmx-doc-api (DocModule, 独立合并)    ← 已按新模式拆分
  ├── cmx-dct-api (DctModule, 独立合并)    ← 已按新模式拆分
  ├── cmx-rpt-api (ReportModule, 独立合并)
  ├── cmx-flow-api (FlowModule, 独立合并)
  └── cmx-job-api (JobModule, 独立合并)
```

### 1.2 问题

portal 目录混装了**三类不同归属的接口**：

| 类别       | portal 中的 handler                                       | 实际归属                         | 问题                                         |
| -------- | ------------------------------------------------------- | ---------------------------- | ------------------------------------------ |
| **模型中心** | definitions / flexible\_combination / model             | cmx-model + cmx-model-center | 22 个端点应随模型中心独立部署，当前被硬编在 portal 里           |
| **门户本体** | ai / meta / pages / data / notify / launcher / registry | cmx-portal                   | 47 个端点属于门户，留在 portal 合理                    |
| **页面中心** | pages.rs（form/native/html）                              | cmx-form                     | 经 cmx-portal 再导出，未来可独立为 cmx-form-api（本次不动） |

**核心矛盾**：cmx-doc-api / cmx-dct-api 已遵循"父目录三层 + ModuleRoutes + web-server merge"的破环模式，但模型中心仍堆在 cmx-api 的 portal 目录里，命名和结构都不统一。

### 1.3 cmx-doc / cmx-dct 已验证的分层模式（参考标杆）

```
crates/libs/cmx-doc/          ← 父目录
  cmx-doc-model/              ← 语义中立层（DB-free）
  cmx-doc-store-pg/           ← PG 持久化层
  cmx-doc-api/                ← HTTP 层（ModuleRoutes）
        ↓
web-server                    ← .merge(DocModule.routes())
```

## 二、目标架构

### 2.1 重组后的目录结构（对标 cmx-doc）

```
crates/libs/cmx-model/                ← 父目录（不再是独立 crate）
  cmx-model-meta/                     ← 原 cmx-model 改名（定义/FC/dict 读写，JSON 存储）
    src/
      definitions/
      dict/
      flexible_combination/
      lib.rs
    Cargo.toml  (name = "cmx-model-meta")
  cmx-model-deploy/                   ← 原 cmx-model-center 改名 + 移动（编译/初始化/部署，DB 落库）
    src/
      compile.rs / db_state.rs / deploy.rs / init.rs / ledger.rs / ...
    tests/
    Cargo.toml  (name = "cmx-model-deploy")
  cmx-model-api/                      ← 新建 HTTP 层
    src/
      handlers/
        definitions.rs
        flexible_combination.rs
        deploy.rs
      lib.rs
    Cargo.toml  (name = "cmx-model-api")
```

### 2.2 重构后的依赖拓扑

```
web-server
  ├── cmx-api (api_routes 聚合)
  │     └── portal/PortalModule  ← 只剩门户本体 7 个 handler 组
  ├── cmx-model-api (ModelModule, 新建)  ← 模型中心独立 HTTP 层
  │     ├── cmx-model-meta (definitions / flexible_combination)
  │     └── cmx-model-deploy (db_state / init / deploy)
  ├── cmx-doc-api (DocModule)
  ├── cmx-dct-api (DctModule)
  └── ...
```

### 2.3 改名映射

| 原 crate 名          | 新 crate 名          | Rust import 变化                              | 物理位置变化                                                                      |
| ------------------ | ------------------ | ------------------------------------------- | --------------------------------------------------------------------------- |
| `cmx-model`        | `cmx-model-meta`   | `cmx_model::` → `cmx_model_meta::`          | `crates/libs/cmx-model/` → `crates/libs/cmx-model/cmx-model-meta/`          |
| `cmx-model-center` | `cmx-model-deploy` | `cmx_model_center::` → `cmx_model_deploy::` | `crates/libs/cmx-model-center/` → `crates/libs/cmx-model/cmx-model-deploy/` |
| —（新建）              | `cmx-model-api`    | `cmx_model_api::`                           | `crates/libs/cmx-model/cmx-model-api/`                                      |

### 2.4 端点归属划分

**移入 cmx-model-api（新建）：22 个端点**

| 当前 portal handler        | 路由前缀                      | 调用链（改后）                                      | 端点数 |
| ------------------------ | ------------------------- | -------------------------------------------- | :-: |
| deploy.rs（原 model.rs）    | `/model/*`                | `cmx_model_deploy::db_state/init/deploy`     |  7  |
| definitions.rs           | `/definitions/*`          | `cmx_model_meta::definitions::store/resolve` |  6  |
| flexible\_combination.rs | `/flexible-combination/*` | `cmx_model_meta::flexible_combination`       |  9  |

**留在 cmx-api/portal（门户本体）：47 个端点**

| handler     | 路由前缀                                                         | 端点数 |
| ----------- | ------------------------------------------------------------ | :-: |
| ai.rs       | `/ai/*`, `/agent/*`                                          |  5  |
| meta.rs     | `/domains`, `/menu-pages`, `/activities`, `/workspace-nodes` |  7  |
| pages.rs    | `/form-pages`, `/native-pages`, `/html-pages`                |  10 |
| data.rs     | `/fact/*`, `/help/*`                                         |  8  |
| notify.rs   | `/notifications/*`                                           |  6  |
| launcher.rs | `/launcher/*`                                                |  1  |
| registry.rs | `/registry/*`, `/service-catalog/*`, `/modules/*`            |  10 |

## 三、实施方案（分 5 步）

### 步骤 1：目录重组 + crate 改名

**1.1 将 cmx-model 移入子目录并改名**

```
原：crates/libs/cmx-model/          （crate name = "cmx-model"）
新：crates/libs/cmx-model/cmx-model-meta/   （crate name = "cmx-model-meta"）
```

操作（使用 `git mv` 保留历史）：
```bash
mkdir -p crates/libs/cmx-model/cmx-model-meta
git mv crates/libs/cmx-model/src crates/libs/cmx-model/cmx-model-meta/src
git mv crates/libs/cmx-model/Cargo.toml crates/libs/cmx-model/cmx-model-meta/Cargo.toml
```

- 修改 `cmx-model-meta/Cargo.toml`：`name = "cmx-model"` → `name = "cmx-model-meta"`
- 修改 `cmx-model-meta/src/lib.rs:1`：`//! cmx-model —— 模型中心。` → `//! cmx-model-meta —— 模型中心元数据层。`（及第 1-17 行相关自描述）

> ⚠️ **Cargo 硬约束**：移动后 `crates/libs/cmx-model/` 父目录下**必须没有任何 Cargo.toml**，否则 Cargo 会把父目录当独立 crate 解析，与 members 中并列声明的三个子 crate 冲突。执行后用 `find crates/libs/cmx-model -name Cargo.toml` 确认只有 3 个子 Cargo.toml。

**1.2 将 cmx-model-center 移入子目录并改名**

```
原：crates/libs/cmx-model-center/   （crate name = "cmx-model-center"）
新：crates/libs/cmx-model/cmx-model-deploy/  （crate name = "cmx-model-deploy"）
```

操作（使用 `git mv` 保留历史）：
```bash
git mv crates/libs/cmx-model-center crates/libs/cmx-model/cmx-model-deploy
```

- 修改 `cmx-model-deploy/Cargo.toml`：`name = "cmx-model-center"` → `name = "cmx-model-deploy"`
- 修改 `cmx-model-deploy/Cargo.toml`：`cmx-model = { workspace = true }` → `cmx-model-meta = { workspace = true }`
- **其余依赖段原样保留**（含 `[dev-dependencies]` 中的 `tempfile`，以及 cmx-core / cmx-database / cmx-metadata / cmx-utils / cmx-api-types / cmx-biz / cmx-traits 等）

**1.3 修改 workspace Cargo.toml（根 cmx-container/Cargo.toml）**

```toml
# [workspace.members] 移除旧路径，添加新路径：
# 移除："crates/libs/cmx-model"
# 移除："crates/libs/cmx-model-center"
# 添加：
"crates/libs/cmx-model/cmx-model-meta",
"crates/libs/cmx-model/cmx-model-deploy",
"crates/libs/cmx-model/cmx-model-api",

# [workspace.dependencies] 改名 + 新增：
# 移除：cmx-model = { path = ... }
# 移除：cmx-model-center = { path = ... }
# 添加：
# 内部依赖 - 模型中心元数据层（定义/FC/dict 读写，JSON 存储）
cmx-model-meta = { path = "crates/libs/cmx-model/cmx-model-meta", version = "0.1.12", registry = "nora" }
# 内部依赖 - 模型中心部署层（编译/初始化/部署，DB 落库）
cmx-model-deploy = { path = "crates/libs/cmx-model/cmx-model-deploy", version = "0.1.12", registry = "nora" }
# 内部依赖 - 模型中心 HTTP 层（ModelModule 路由，在此合并进主路由，避免 cmx-api⇄cmx-model 环）
cmx-model-api = { path = "crates/libs/cmx-model/cmx-model-api", version = "0.1.12", registry = "nora" }
```

### 步骤 2：全量替换 Rust import 路径

> 以下清单基于 grep 扫描 + 子智能体评审补全（原方案遗漏了 db_state.rs 和 compile.rs 中的 8 处真实调用）。

#### cmx-model-deploy 内部（cmx_model:: → cmx_model_meta::）

| 文件 | 行号 | 性质 | 内容 |
|------|:---:|------|------|
| `src/seed_scanner.rs` | 7 | use | `use cmx_model::config::data_path` |
| `src/db_state.rs` | 552 | 注释 | `cmx_model::definitions::store::list_definitions` |
| `src/db_state.rs` | **559** | **真实调用** | `cmx_model::definitions::store::list_definitions(...)` |
| `src/compile.rs` | 612 | 注释 | `cmx_model::definitions::store::get_definition` |
| `src/compile.rs` | **617** | **真实调用** | `cmx_model::definitions::store::DefRef { ... }` |
| `src/compile.rs` | **628** | **真实调用** | `cmx_model::definitions::store::get_definition(&r)` |
| `src/compile.rs` | **638** | **真实调用** | `cmx_model::definitions::store::DefRef { ... }` |
| `src/compile.rs` | **647** | **真实调用** | `cmx_model::definitions::store::get_definition(&r)` |
| `src/deploy_seed_menu.rs` | 18 | use | `use cmx_model::definitions::store::list_definitions` |
| `src/deploy_seed_menu.rs` | **184** | **真实调用** | `cmx_model::config::data_path(["meta", "definitions"])` |
| `src/lib.rs` | 43 | 文档注释 | `cmx_api 通过 cmx_model_center::xxx 调用` → `cmx_model_deploy` |

#### cmx-model-deploy 测试路径修复（CARGO_MANIFEST_DIR 错位）

> ⚠️ 阻断问题：原位置 `crates/libs/cmx-model-center/` 上溯 3 层到 cmx-container 根；新位置 `crates/libs/cmx-model/cmx-model-deploy/` 多了一层，必须改为 4 层。否则测试运行时找不到数据文件。

| 文件 | 行号 | 原值 | 新值 |
|------|:---:|------|------|
| `src/lib.rs` | 103 | `join("../../../data/meta/definitions")` | `join("../../../../data/meta/definitions")` |

#### cmx-model-deploy 测试文件（cmx_model_center:: → cmx_model_deploy::）

| 文件 | 行号 | 内容 |
|------|:---:|------|
| `tests/seed_scanner_test.rs` | 1 | `use cmx_model_center::seed_scanner::...` |
| `tests/menu_pages_adapter_test.rs` | 1 | `use cmx_model_center::menu_pages_adapter::...` |
| `tests/deploy_seed_test.rs` | 9 | `use cmx_model_center::deploy_seed_menu::...` |
| `tests/deploy_seed_integration_test.rs` | 11-26 | 文档注释中 `cmx_model_center::` → `cmx_model_deploy::`（rustdoc 链接 + 命令示例 + 描述，共 ~6 处）|

#### cmx-portal（cmx_model:: → cmx_model_meta::）

| 文件 | 行号 | 内容 |
|------|:---:|------|
| `Cargo.toml` | 19 | `cmx-model = { workspace = true }` → `cmx-model-meta = { workspace = true }` |
| `src/lib.rs` | 41 | `pub use cmx_model::{definitions, dict, flexible_combination}` → `pub use cmx_model_meta::{definitions, dict, flexible_combination}` |

> **验证结论**：cmx-portal 内部 agent/tools/ 的 `crate::{dict, definitions, flexible_combination}` 引用（meta_query.rs:79/120/138、read.rs:63、mod.rs:123-124）全部通过 lib.rs 的 re-export 解析，只需改 lib.rs 一行，无需改动 agent 代码。

#### cmx-dct-store-pg（cmx_model:: → cmx_model_meta::）

| 文件 | 行号 | 内容 |
|------|:---:|------|
| `Cargo.toml` | 25 | `cmx-model = { workspace = true }` → `cmx-model-meta = { workspace = true }` |
| `src/resolve.rs` | — | `cmx_model::definitions::` → `cmx_model_meta::definitions::` |

#### cmx-doc-api（cmx_model:: → cmx_model_meta::）

| 文件 | 行号 | 内容 |
|------|:---:|------|
| `Cargo.toml` | 21 | `cmx-model = { workspace = true }` → `cmx-model-meta = { workspace = true }` |
| `src/handlers.rs` | 1073 | `use cmx_model::definitions::resolve::resolve_doc_file` → `use cmx_model_meta::definitions::resolve::resolve_doc_file` |

#### 不改的历史注释（避免误改）

以下"model_center.rs"引用指向曾经的 `cmx-api/handlers/portal/model_center.rs`（已不存在），是历史溯源注释，**不应改动**：
- `cmx-biz/src/validation/mod.rs:4,71`
- `cmx-doc/cmx-doc-model/src/meta.rs:706`

### 步骤 3：新建 cmx-model-api crate

**目录**：`crates/libs/cmx-model/cmx-model-api/`

**Cargo.toml**：

```toml
[package]
name = "cmx-model-api"
version.workspace = true
edition.workspace = true
authors.workspace = true

[dependencies]
# 内部依赖 - API 框架
cmx-api = { workspace = true }
# 内部依赖 - 模型中心元数据层
cmx-model-meta = { workspace = true }
# 内部依赖 - 模型中心部署层
cmx-model-deploy = { workspace = true }
# 内部依赖 - 核心类型
cmx-core = { workspace = true }
# 内部依赖 - API 通用类型
cmx-api-types = { workspace = true }
# Web 框架
axum = { workspace = true }
# 序列化
serde = { workspace = true }
serde_json = { workspace = true }
# 异步运行时
tokio = { workspace = true }
# 流处理
futures = { workspace = true }
```

**src/lib.rs**：

```rust
//! 模型中心 HTTP 层（定义中心 + 弹性组合 + 数据库部署）。
//!
//! 对标 cmx-doc-api / cmx-dct-api 的分层模式：
//! - cmx-model-meta：元数据定义读写（JSON 存储）
//! - cmx-model-deploy：编译/初始化/部署（DB 落库）
//! - cmx-model-api（本 crate）：薄 axum handler + ModuleRoutes 路由聚合

pub mod handlers;

use axum::Router;
use axum::routing::{get, post};
use cmx_api::app_state::CmxAppState;
use cmx_api::routes::traits::ModuleRoutes;

/// 模型中心路由模块。
pub struct ModelModule;

impl ModuleRoutes for ModelModule {
    fn routes(self) -> Router<CmxAppState> {
        Router::new()
            .merge(definitions_routes())
            .merge(flexible_combination_routes())
            .merge(deploy_routes())
    }

    fn prefix() -> &'static str {
        "model"
    }

    fn module_name(&self) -> &'static str {
        "model"
    }
}

// ─── 定义中心（DCT/DOC/BASE）───
fn definitions_routes() -> Router<CmxAppState> { ... }

// ─── 弹性组合 ───
fn flexible_combination_routes() -> Router<CmxAppState> { ... }

// ─── 数据库初始化 + 模块部署 ───
fn deploy_routes() -> Router<CmxAppState> { ... }
```

**src/handlers/**：
从 portal 搬移 3 个文件，修改 import：

* `definitions.rs`：`cmx_portal::definitions::*` → `cmx_model_meta::definitions::*`

* `flexible_combination.rs`：`cmx_portal::flexible_combination::*` → `cmx_model_meta::flexible_combination::*`

* `deploy.rs`（原 model.rs）：`super::model_center::*` → `cmx_model_deploy::*`

### 步骤 4：从 cmx-api/portal 移除 3 个 handler

**删除文件**：

* `portal/definitions.rs`

* `portal/flexible_combination.rs`

* `portal/model.rs`

**修改 portal/mod.rs**：

* 移除 `pub mod definitions` / `pub mod flexible_combination` / `pub mod model`

* 移除 `pub use cmx_model_center as model_center`

* `routes()` 中移除 `.merge(definitions_routes())` / `.merge(flexible_combination_routes())` / `.merge(model_routes())`

* 移除对应的 3 个路由注册函数定义

**修改 cmx-api/Cargo.toml**：

* 移除 `cmx-model-center = { workspace = true }`（不再直接依赖）

### 步骤 5：web-server 合并 ModelModule

**修改 web-server/Cargo.toml**：

```toml
# 内部依赖 - 模型中心 HTTP 层（ModelModule 路由，在此合并进主路由，避免 cmx-api⇄cmx-model 环）
cmx-model-api = { workspace = true }
```

**修改 web-server/src/routes.rs**：

```rust
use cmx_model_api::ModelModule;

pub fn routes() -> Router<CmxAppState> {
    api_routes()
        .merge(ReportModule.routes())
        .merge(FlowModule.routes())
        .merge(DocModule.routes())
        .merge(DctModule.routes())
        .merge(JobModule.routes())
        .merge(ModelModule.routes())  // 新增
}
```

## 四、不动的部分

| 范围                                               | 原因                               |
| ------------------------------------------------ | -------------------------------- |
| cmx-portal 内部业务逻辑                                | 只搬 HTTP handler，不动业务层            |
| cmx-model-meta / cmx-model-deploy 的源码内容          | 不改逻辑，只改 crate 名和 import 路径       |
| cmx-portal 的 `pub use cmx_model_meta::{...}` 再导出 | 保留（agent dict 工具仍依赖），只改 import 名 |
| pages.rs（form/native/html）                       | 属于 cmx-form，本次不拆                 |
| iam / 用户相关                                       | 本次先不考虑                           |
| portal/legacy.rs（废弃接口）                           | 留在 portal，已注释无影响                 |

## 五、影响范围清单

### 需修改的 Cargo.toml（7 个）

| 文件                                      | 改动                                                       |
| --------------------------------------- | -------------------------------------------------------- |
| `cmx-container/Cargo.toml`（根）           | members 改路径 + dependencies 改名 + 新增 cmx-model-api         |
| `cmx-model/cmx-model-meta/Cargo.toml`   | name 改为 cmx-model-meta                                   |
| `cmx-model/cmx-model-deploy/Cargo.toml` | name 改为 cmx-model-deploy + 依赖 cmx-model → cmx-model-meta |
| `cmx-portal/Cargo.toml`                 | cmx-model → cmx-model-meta                               |
| `cmx-api/Cargo.toml`                    | 移除 cmx-model-center                                      |
| `cmx-dct/cmx-dct-store-pg/Cargo.toml`   | cmx-model → cmx-model-meta                               |
| `cmx-doc/cmx-doc-api/Cargo.toml`        | cmx-model → cmx-model-meta                               |
| `web-server/Cargo.toml`                 | 新增 cmx-model-api                                         |

### 需修改的 Rust 源文件（约 18 个）

| 文件 | 改动 |
|------|------|
| `cmx-model-deploy/src/seed_scanner.rs` | `cmx_model::` → `cmx_model_meta::`（行 7） |
| `cmx-model-deploy/src/db_state.rs` | `cmx_model::` → `cmx_model_meta::`（行 552 注释 + 行 559 真实调用） |
| `cmx-model-deploy/src/compile.rs` | `cmx_model::` → `cmx_model_meta::`（行 612 注释 + 行 617/628/638/647 真实调用） |
| `cmx-model-deploy/src/deploy_seed_menu.rs` | `cmx_model::` → `cmx_model_meta::`（行 18 use + 行 184 真实调用） |
| `cmx-model-deploy/src/lib.rs` | 文档注释 + CARGO_MANIFEST_DIR 路径修复（行 43/103） |
| `cmx-model-deploy/tests/seed_scanner_test.rs` | `cmx_model_center::` → `cmx_model_deploy::` |
| `cmx-model-deploy/tests/menu_pages_adapter_test.rs` | `cmx_model_center::` → `cmx_model_deploy::` |
| `cmx-model-deploy/tests/deploy_seed_test.rs` | `cmx_model_center::` → `cmx_model_deploy::` |
| `cmx-model-deploy/tests/deploy_seed_integration_test.rs` | `cmx_model_center::` → `cmx_model_deploy::`（含文档注释 ~6 处） |
| `cmx-portal/src/lib.rs` | `cmx_model::` → `cmx_model_meta::` |
| `cmx-model-meta/src/lib.rs` | 模块级文档注释 `cmx-model` → `cmx-model-meta` |
| `cmx-dct-store-pg/src/resolve.rs` | `cmx_model::` → `cmx_model_meta::` |
| `cmx-doc-api/src/handlers.rs` | `cmx_model::` → `cmx_model_meta::` |
| `cmx-api/src/handlers/portal/mod.rs` | 移除 model/definitions/flexible_combination 相关代码 |
| `web-server/src/routes.rs` | 新增 ModelModule merge |

### 需删除的文件（3 个）

* `cmx-api/src/handlers/portal/definitions.rs`

* `cmx-api/src/handlers/portal/flexible_combination.rs`

* `cmx-api/src/handlers/portal/model.rs`

### 需新建的文件

* `cmx-model/cmx-model-api/Cargo.toml`

* `cmx-model/cmx-model-api/src/lib.rs`

* `cmx-model/cmx-model-api/src/handlers/mod.rs`

* `cmx-model/cmx-model-api/src/handlers/definitions.rs`

* `cmx-model/cmx-model-api/src/handlers/flexible_combination.rs`

* `cmx-model/cmx-model-api/src/handlers/deploy.rs`

## 六、验证步骤

1. `cargo check -p cmx-model-meta` — 改名后编译通过
2. `cargo check -p cmx-model-deploy` — 改名 + 依赖更新后编译通过
3. `cargo check -p cmx-model-api` — 新 crate 编译通过
4. `cargo check -p cmx-api` — portal 移除 3 个 handler 后编译通过
5. `cargo check -p cmx-portal` — import 路径更新后编译通过
6. `cargo check -p cmx-dct-store-pg` — import 路径更新后编译通过
7. `cargo check -p cmx-doc-api` — import 路径更新后编译通过
8. `cargo check -p web-server` — ModelModule 合并后编译通过
9. `cargo check --workspace --all-targets` — 含 tests/examples/benches，捕获 `#[cfg(test)]` 内的 CARGO_MANIFEST_DIR 路径错位
10. `cargo test -p cmx-model-deploy --tests --no-run` — 编译期即可发现测试路径错误，不必真跑测试
11. `cargo clippy --workspace --all-targets` — 无新增警告
12. 启动服务验证端点可达（路由路径不变，只是归属 crate 变了）

