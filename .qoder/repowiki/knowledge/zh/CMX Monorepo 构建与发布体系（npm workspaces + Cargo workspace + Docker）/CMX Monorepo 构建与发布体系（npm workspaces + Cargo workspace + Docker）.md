---
kind: build_system
name: CMX Monorepo 构建与发布体系（npm workspaces + Cargo workspace + Docker）
category: build_system
scope:
    - '**'
source_files:
    - package.json
    - cmx-container/Cargo.toml
    - cmx-container/.gitlab-ci.yml.example
    - cmx-container/docker/Dockerfile
    - cmx-container/Cross.toml
    - cmx-container/bash/deploy.sh
    - CMXPortalManager/package.json
    - CMXHTMLDesigner/package.json
    - packages/cmx-ui5-runtime/package.json
    - cmx-flowengine/Cargo.toml
    - cmx-mdm/Cargo.toml
    - cmx-report/Cargo.toml
    - cmx-rulesengine/Cargo.toml
    - cmx-portalservice/Cargo.toml
    - cmx-model/Cargo.toml
---

## 1. 整体架构：双栈 monorepo

本仓库是一个混合语言 monorepo，前端使用 **npm workspaces**，后端核心服务 `cmx-container` 使用 **Cargo workspace**，并通过 Docker 统一编排。

- 前端工作区（根 `package.json`）：
  - `workspaces: ["packages/*", "CMXHTMLDesigner", "CMXPortalManager"]`
  - 顶层脚本通过 `-w <workspace>` 调用子包命令，如 `build:apps` 依次构建 `cmx-ui5-runtime`、`cmx-portal-manager`、`cmx-html-designer`。
  - 依赖版本通过 `overrides` 强制统一（graphql、vitest、@vitest/coverage-v8），避免多子包版本漂移。
- Rust 工作区（`cmx-container/Cargo.toml`）：
  - `[workspace] members = [...]` 声明 70+ 个 crate，按 `crates/libs/*`、`crates/tests/*`、`sdk/*` 分层组织。
  - 所有 crate 共享 `[workspace.package] version = "0.1.12"`、`edition = "2024"`，并通过 `[workspace.dependencies]` 集中管理第三方依赖版本。
  - 独立微服务（flowengine、mdm、report、rulesengine、portalservice、model）各自拥有独立 `Cargo.toml` workspace，由 `cmx-container` 以 proxy-only crate 引用。

## 2. 前端构建链（Vite + UI5 Web Components）

- 每个前端应用（`cmx-portal-manager`、`cmx-html-designer`）的 `scripts.build` 先执行 `npm run build -w cmx-ui5-runtime`，再调用 `node scripts/run-vite.mjs build`。
- 共享运行时 `packages/cmx-ui5-runtime` 输出到 `dist/`，被两个前端通过 `/shared/assets/install-*.js` 动态加载；部署脚本会校验该文件存在，否则阻断。
- Vite 通过 `.env` / `.env.production` / `.env.<mode>` 切换环境，`run-vite.mjs` 是统一的入口封装。
- 测试：`cmx-html-designer` 使用 Vitest (`vitest.config.js`)，`cmx-data-comp` 同样用 Vitest；根 `test` 脚本串联各子包测试。

## 3. Rust 后端构建链（cargo workspace + cargo-chef + Cross）

- 开发/本地构建：`bash/deploy.sh` 是单键部署脚本，顺序为：
  1) 构建两个前端（`npm run build` in each frontend）→ 校验 `dist/index.html` 和 shared runtime。
  2) `cargo build --release -p web-server` 编译后端二进制。
  3) 启动进程、写 PID 文件、轮询 `/api/auth/login` 健康检查。
- CI（`.gitlab-ci.yml.example`）：
  - stages: `secrets → check → lint → test`。
  - `check`: `cargo check --workspace --all-targets`。
  - `lint`: `cargo fmt --all -- --check` + `cargo clippy --workspace --all-targets -- -D warnings`（硬失败）。
  - `test`: `cargo test --workspace --lib`（纯单元）+ `integration-test`（PostgreSQL service + `--ignored` 门控的 PG 集成测试）。
  - 缓存：基于 `Cargo.lock` key 缓存 `.cargo/registry/*` 和 `target/`；禁用增量编译（`CARGO_INCREMENTAL=0`）。
- 容器镜像（`cmx-container/docker/Dockerfile`）：
  - 四阶段构建：`chef`（安装 cargo-chef）→ `planner`（`cargo chef prepare`）→ `builder`（`cargo chef cook` 预编译依赖 + `cargo build --release -p web-server`）→ `runtime`（debian-slim，仅拷贝二进制、web 静态资源、配置文件、迁移 SQL）。
  - 通过 `SWAGGER_UI_DOWNLOAD_URL=file:///app/assets/swagger-ui-5.17.14.zip` 离线注入 Swagger UI。
  - 非 root 用户 `cmx`，暴露 8080/9090，HEALTHCHECK 调用 `/api/health`。
- 交叉编译：`Cross.toml` 配置了 `x86_64-unknown-linux-musl` 目标镜像 `ghcr.io/cross-rs/x86_64-unknown-linux-musl:latest`，用于 musl 静态链接产物。
- 工具链锁定：`rust-toolchain.toml` + CI `image: rust:1.97.1` 保证一致性。

## 4. 其他服务的构建/部署

- 独立 Rust 服务（`cmx-flowengine`、`cmx-mdm`、`cmx-report`、`cmx-rulesengine`、`cmx-portalservice`、`cmx-model`）各自提供：
  - 根级 `Cargo.toml` workspace。
  - 启动脚本 `*.sh`（如 `flow.sh`、`mdm.sh`、`report.sh`、`rules.sh`、`portal.sh`、`model.sh`）。
  - 服务专属 `docker-compose.yml` / `Dockerfile`（例如 `cmx-flowengine/deploy/`）。
- 这些服务在 `cmx-container` 中仅以 proxy-only crate 引用，不进入门户主编译图，从而隔离编译体积。

## 5. 约定与约束

- 前端必须通过 npm workspaces 构建，禁止绕过 `cmx-ui5-runtime` 直接引入 UI5 组件。
- 部署前必须校验 shared runtime 产出 `install-*.js`，缺失即白屏——这是硬性门禁。
- Rust 代码合并前必须通过 `cargo fmt --all -- --check` 与 `cargo clippy -- -D warnings`（CI 硬失败）。
- `.env` 不得进入 git（CI secrets 阶段显式检查 `git ls-files .env`）。
- 版本号集中在 `Cargo.toml [workspace.package]` 与根 `package.json` 维护，避免散落的版本字符串。
- 跨 workspace 依赖通过 `path` + `version` + `registry = "nora"` 双重声明，发布时走私有 registry，本地开发走 patch 覆盖（见 `[patch.nora]`）。
- 集成测试默认跳过需要数据库种子的用例，仅跑 `#[ignore]` 门控的轻量 PG 测试；完整 E2E 需有数据的 runner。