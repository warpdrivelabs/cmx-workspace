---
kind: frontend_style
name: CMX 企业门户前端样式体系：UI5 + Neo 主题变量 + Web Components Shadow DOM 多包风格
category: frontend_style
scope:
    - '**'
source_files:
    - CMXPortalManager/src/app-shell.css
    - CMXPortalManager/src/lib/portal-neo-theme.css
    - CMXPortalManager/src/lib/portal-neo-theme.js
    - CMXHTMLDesigner/src/style.css
    - packages/cmx-ui5-runtime/package.json
    - packages/cmx-ui5-runtime/src/client.js
    - packages/cmx-data-comp/package.json
    - packages/cmx-data-comp/src/index.js
    - cmx-mega-sheet/src/element/cmx-megasheet.ts
    - CMXPortalManager/vite.config.js
    - CMXHTMLDesigner/vite.config.js
---

## 1. 整体方案

本仓库是一个基于 npm workspaces 的前端 Monorepo，包含多个独立构建的前端应用与共享包。样式体系围绕 **SAP UI5 Web Components** 主题系统展开，并通过自定义 CSS 变量层（Neo 主题）叠加品牌色，同时各子项目根据自身特性采用不同的样式策略。

- **UI5 主题基线**：所有应用通过 `cmx-ui5-runtime` 包统一加载 `@ui5/webcomponents`、`@ui5/webcomponents-fiori`、`@ui5/webcomponents-icons*`、`@ui5/webcomponents-theming` 等运行时，并在 Vite 配置中通过 `optimizeDeps.exclude` 排除这些包，避免 Vite 预构建破坏 UI5 主题注入机制。
- **Neo 品牌主题层**：在 Portal Manager 的 `src/lib/portal-neo-theme.css` 中定义 `--neo-*` 系列 CSS 变量（cyan/violet/mint/warn/accent/glass/border/glow 等），并通过 `color-mix(in srgb, ...)` 混合 UI5 的 `--sap*` 变量派生玻璃态背景、渐变 ShellBar 等效果，实现亮/暗主题随 UI5 自适应。
- **Web Components Shadow DOM 隔离**：组件库 `packages/cmx-data-comp` 和自研电子表格 `cmx-mega-sheet` 均使用原生 Web Components + Shadow DOM，样式通过 `<style>` 内嵌或 `:host` 规则封装，不污染宿主页面；`cmx-mega-sheet` 还通过 `cmx-dark` class 切换明暗主题。
- **Vite 构建与分包**：两个主应用（Portal Manager、HTMLDesigner）均使用 Vite，按第三方库粒度拆分 chunk（ignite-spreadsheet、ignite-grids、tabulator、revogrid、lit、shiki 等），并针对首屏 modulePreload 做精细化过滤，避免重型 vendor chunk 阻塞入口。

## 2. 关键文件与包

- `../../../../../cmx-portal-manager`：Portal 根级样式，引入 Neo 主题，设置 body 布局、滚动收口、`--portal-workspace-bg` 等全局变量。
- `../../../../../cmx-portal-manager`：Neo 主题变量集中定义处，所有 `--neo-*` 变量在此声明，依赖 `--sap*` 变量实现主题联动。
- `../../../../../cmx-portal-manager` / `portal-module-theme.js`：运行时主题切换逻辑（JS 侧）。
- `../../../../../cmx-html-designer`：设计器根样式，直接引用 `--sapBackgroundColor`、`--sapTextColor` 等 UI5 变量。
- `packages/cmx-ui5-runtime/package.json` 与 `src/client.js`：共享 UI5 运行时包，提供 `ensureCmxUi5Runtime()` 单例加载 API，dev/build 双模式注入。
- `packages/cmx-data-comp/package.json`：数据组件库，peerDependencies 锁定 `@ui5/webcomponents >=2.0.0`，内部组件均为自定义元素（`cmx-*` 前缀）。
- `cmx-mega-sheet/src/element/cmx-megasheet.ts`：自研电子表格 Web Component，内置 LIGHT/DARK 两套主题常量与 Shadow DOM 样式字符串，通过 `setTheme('light'|'dark')` 切换。
- `../../../../../cmx-portal-manager` 与 `../../../../../cmx-html-designer`：Vite 配置，含 UI5 插件、别名、chunk 拆分策略、optimizeDeps.exclude 列表。

## 3. 架构与约定

### 3.1 主题分层

| 层级 | 来源 | 作用域 | 说明 |
|---|---|---|---|
| SAP UI5 主题变量 | `@ui5/webcomponents-theming` | 全局 `:root` | 提供 `--sapBackgroundColor`、`--sapShellColor`、`--sapField_Background` 等基础语义变量，支持 light/dark 主题切换 |
| Neo 品牌变量 | `portal-neo-theme.css` | `:root` | 定义 `--neo-cyan`、`--neo-violet`、`--neo-glass` 等品牌色，通过 `color-mix` 混合 UI5 变量生成渐变背景 |
| 应用级变量 | `app-shell.css` | `html/body` | 定义 `--portal-workspace-bg`、`--portal-panel-bg` 等应用级变量，供组件消费 |
| 组件 Shadow DOM 变量 | 各组件 `<style>` | `:host` / 组件内 | 如 `cmx-megasheet` 的 `--cmx-*` 变量，完全隔离于宿主 |

### 3.2 组件样式组织

- **Portal 与 Designer 应用**：采用传统 CSS 文件 + 全局变量方式，通过 `@import url('./lib/portal-neo-theme.css')` 引入主题，组件内直接使用 `var(--neo-*)`、`var(--sap-*)`。
- **cmx-data-comp 组件库**：每个组件一个 JS 文件，样式通过 `component.addStyle(...)` 或 Shadow DOM `<style>` 内联注册，遵循 `cmx-*` 自定义元素命名约定。
- **cmx-mega-sheet**：纯 vanilla Web Component，样式以模板字符串形式嵌入 TS 文件，通过 `:host` 选择器和 `cmx-dark` class 控制明暗主题，不依赖任何 CSS 框架。

### 3.3 运行时主题切换

- Portal 通过 `portal-neo-theme.js` 动态切换 UI5 主题，Neo 变量自动跟随 `--sap*` 变化。
- HTMLDesigner 通过 `designer-topbar.js` 中的主题菜单调用 UI5 主题 API 切换，并将当前主题持久化到 `sessionStorage.__designer_theme__`。
- cmx-mega-sheet 暴露 `setTheme('light'|'dark'|'auto')` 方法，内部切换 `cmx-dark` class 并更新 Canvas 渲染主题常量。

## 4. 约定与约束

- **禁止直接修改 UI5 主题变量**：所有品牌色必须通过 `--neo-*` 变量中转，再经由 `color-mix` 混合 UI5 变量，确保亮/暗主题自动适配。
- **Shadow DOM 样式隔离**：组件库与 mega-sheet 的样式不得泄漏到宿主文档；需要穿透时（如原生 `<select option>`）仅在全局 CSS 中覆盖，且注释明确标注浏览器兼容性限制。
- **UI5 运行时唯一实例**：通过 `cmx-ui5-runtime` 包的 `ensureCmxUi5Runtime()` 保证 dev 模式下应用代码与 runtime 共享同一份 ES module 实例，避免双实例导致主题失效。
- **Vite optimizeDeps 排除 UI5 包**：两个应用的 vite.config.js 均在 `optimizeDeps.exclude` 中列出全部 `@ui5/*` 包，防止 Vite 预构建破坏主题注入。
- **chunk 拆分优先级**：生产构建通过 `rollupOptions.manualChunks` 与 `rolldownOptions.codeSplitting.groups` 将 ignite-spreadsheet、ignite-grids、tabulator、lit、shiki 等拆为独立 chunk，并按 priority 降序匹配，确保更具体的库先命中。
- **组件命名约定**：所有共享 Web Components 使用 `cmx-` 前缀（如 `cmx-revo-grid`、`cmx-floating-dialog`、`cmx-kpi-card`），避免与第三方元素冲突。
- **CSS 变量命名空间**：不同子系统使用不同变量前缀——UI5 用 `--sap-*`，Portal Neo 主题用 `--neo-*` 与 `--portal-*`，mega-sheet 用 `--cmx-*`，互不干扰。
- **移动端适配**：`app-shell.css` 显式处理 Mobile Safari 的 `height: -webkit-fill-available`，避免地址栏遮挡导致的视口裁切问题。
