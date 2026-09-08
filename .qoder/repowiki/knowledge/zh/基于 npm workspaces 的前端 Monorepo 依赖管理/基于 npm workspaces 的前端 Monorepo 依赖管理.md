---
kind: dependency_management
name: 基于 npm workspaces 的前端 Monorepo 依赖管理
category: dependency_management
scope:
    - '**'
source_files:
    - package.json
    - .npmrc
    - CMXHTMLDesigner/package.json
    - CMXPortalManager/package.json
    - packages/cmx-data-comp/package.json
    - packages/cmx-ui5-runtime/package.json
    - packages/cmx-icon-resource/package.json
    - cmx-mega-sheet/package.json
---

## 1. 系统/方案概述

本仓库采用 **npm workspaces** 作为前端 monorepo 的依赖管理与构建编排核心，将三个子应用（`cmx-html-designer`、`cmx-portal-manager`）与三个共享包（`packages/cmx-data-comp`、`packages/cmx-ui5-runtime`、`packages/cmx-icon-resource`）统一纳入同一 `node_modules` 树中。根 `package.json` 通过 `workspaces` 字段声明子目录，并通过顶层 `scripts` 以 `npm run -w <workspace>` 形式在子工作区执行命令。

此外，仓库还包含 Rust 后端服务（`cmx-container`、`cmx-flowengine`、`cmx-mdm`、`cmx-model`、`cmx-portalservice`、`cmx-report`、`cmx-rulesengine`），各自使用 Cargo workspace + `Cargo.lock` 进行依赖锁定；但本卡片仅聚焦前端 JS/TS 依赖管理。

## 2. 关键文件

- `package.json`（根）：定义 workspaces、全局 `overrides`、顶层脚本、以及 Infragistics UI 组件等公共依赖。
- `.npmrc`：配置 `bin-links=true` 以避免符号链接导致的 `../dist/...` 解析失败；同时为 `@infragistics/*` 私有包指定专用 registry `https://packages.infragistics.com/npm/js-licensed/`。
- `../../../../../cmx-html-designer`：设计器应用，依赖 `cmx-data-comp`、`cmx-icon-resource`、`cmx-ui5-runtime` 及 `@ui5/webcomponents*`、CodeMirror、Zod。
- `../../../../../cmx-portal-manager`：门户管理器应用，同样依赖三个共享包与 UI5 Web Components，并额外引入 Fastify 后端、gRPC、tRPC、Lit、Shiki 等。
- `packages/cmx-data-comp/package.json`：数据组件库，通过 `exports` 字段精细暴露多个子路径（如 `./components/cmx-revo-grid.js`、`./lib/cmx-data-set.js`、`./components/ignite/index.js`），并使用 `peerDependencies` 声明对 `@ui5/webcomponents` 的运行时依赖。
- `packages/cmx-ui5-runtime/package.json`：封装 UI5 + Tabler 运行时，对外暴露 `client`、`vite`、`vite-app` 三个入口。
- `packages/cmx-icon-resource/package.json`：图标资源包，通过 `exports` 暴露 `tabler/*`、`icons/*` 等静态资源路径。
- `cmx-mega-sheet/package.json`：独立电子表格引擎包（未加入 workspaces），以 `@cmx/megasheet` 发布，使用 TypeScript + Vitest 构建。

## 3. 架构与约定

### 3.1 工作区划分
- 根 `workspaces: ["packages/*", "CMXHTMLDesigner", "CMXPortalManager"]` 将共享包与应用解耦：应用通过 `"*"` 引用本地共享包，实现跨项目复用而不需发布到 npm registry。
- `cmx-mega-sheet` 未纳入 workspaces，保持独立发布形态（`@cmx/megasheet`），与其他模块松耦合。

### 3.2 版本策略
- 共享包（`cmx-data-comp`、`cmx-ui5-runtime`、`cmx-icon-resource`）使用固定小版本号（`0.1.0`），由 monorepo 内部直接引用，不对外发布。
- 第三方依赖普遍使用 `^` 语义化版本范围（如 `@ui5/webcomponents ^2.23.2`、`vitest ^4.1.10`），但根 `overrides` 强制锁定 `graphql 16.14.0`、`vitest 4.1.10`、`@vitest/coverage-v8 4.1.10`，用于解决传递依赖冲突。
- 部分关键依赖使用精确版本（如 `@infragistics/igniteui-webcomponents-core 7.1.0`、`@keenmate/web-treeview 2.0.0-rc01`），避免升级不确定性。

### 3.3 私有源与许可证包
- `@infragistics/*` 系列组件属于商业许可包，通过 `.npmrc` 中的 `@infragistics:registry=https://packages.infragistics.com/npm/js-licensed/` 指向私有 npm registry，确保安装时从正确源拉取。
- 根 `allowScripts.esbuild@0.25.12` 与 `protobufjs@7.6.1` 显式允许这两个包执行安装后脚本，配合 npm 的安全机制控制风险。

### 3.4 构建与依赖联动
- 应用构建前会先构建共享运行时：`build` 脚本统一执行 `npm run build -w cmx-ui5-runtime && node scripts/run-vite.mjs build`，保证 UI5 运行时产物优先产出。
- `cmx-data-comp` 通过 `exports` 字段提供细粒度子路径导出，使上层应用可按需引入具体组件（如 `cmx-data-comp/components/cmx-revo-grid.js`），减少打包体积。

### 3.5 运行环境约束
- `cmx-portal-manager` 通过 `engines.node` 限定 Node 版本为 `^18.0.0 || ^20.0.0 || >=22.0.0`，确保工具链一致性。
- 根 `.npmrc` 设置 `bin-links=true`，避免 npm 创建 `.bin` 符号链接导致 Vite 插件中 `../dist/...` 相对路径解析失败。

## 4. 约定与约束

- **Monorepo 内共享包必须通过 `*` 版本引用**：`cmx-html-designer` 与 `cmx-portal-manager` 均以 `"cmx-data-comp": "*"`、`"cmx-ui5-runtime": "*"`、`"cmx-icon-resource": "*"` 引用本地包，禁止使用 npm registry 版本。
- **UI5 Web Components 版本统一**：所有子项目对 `@ui5/webcomponents*` 系列均锁定 `^2.23.2`，并通过 `cmx-ui5-runtime` 集中打包，避免多份实例。
- **Infragistics 包必须走私有 registry**：`.npmrc` 中 `@infragistics:registry=...` 是硬性约束，若切换默认 registry 将无法安装这些商业组件。
- **依赖升级需经根 `overrides` 管控**：`graphql`、`vitest`、`@vitest/coverage-v8` 被强制覆盖到固定版本，任何子包的版本变更需评估是否影响其他工作区。
- **Rust 后端与前端依赖完全隔离**：Rust 服务使用独立的 Cargo workspace 与 `Cargo.lock`，与前端 npm 依赖互不影响，不存在跨语言依赖共享。
- **无 lockfile 提交**：根目录存在 `package-lock.json`，但未发现各子工作区单独提交 lockfile 的证据；实际锁定效果依赖 npm workspaces 的扁平化 `node_modules` 行为。
- **Vitest 版本统一**：通过根 `overrides` 强制 `vitest 4.1.10`，即使某些子包声明 `^4.1.6`（如 `cmx-mega-sheet`），也会被提升到一致版本。