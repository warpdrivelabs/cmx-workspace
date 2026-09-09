# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **权威导航是 `AGENTS.md`**（9 章：目录规范 / 技能索引 / 全局硬约束 / Git 多仓规则 / 联调运维 / 命令速查 / 文档路径）。本文件只做最小提炼与硬约束前置；进任意子目录开发前先读该目录的 `AGENTS.md`（就近优先）。**用中文回复。**

## 这是什么仓：工作区根仓（无构建产物）

`cmx-workspace` 是元数据驱动企业平台的**多仓工作区根仓**，本身**不含可构建代码**——只承载导航（`AGENTS.md`）、跨子项目技能（`.agents/skills/`，12 个）、人工方案库（`documents/`）、历史资料（`docs/`）、根级脚本（`scripts/`）。真正的代码在 **15 个独立 Git 子仓**里。

⚠️ **首次克隆后 `backend/`、`frontend/`、`cmx-launcher/` 是空的**（未跟踪的独立子仓）。开工第一步——用户说「初始化工程」时触发技能 `workspace-init`，或直接：

```bash
bash .agents/skills/workspace-init/scripts/init-workspace.sh   # 幂等克隆 15 仓；--update 更新；--dry-run 试跑
```

子仓清单的**唯一真源**是该脚本的 `REPOS` 数组（增删子仓改脚本并同步 `AGENTS.md` §六）。

## 架构大图（跨多仓才看得懂的部分）

**元数据驱动**：换一份定义 JSON 即得一套单据 / 字典 / 报表 / 流程，无需写业务代码。

- **`backend/cmx-container` 是轴心**：公用库 + 插件平台，**无 server bin**。8 个下游后端仓经 `path = "../cmx-container/crates/..."` **跨工作区引用**它。它还是**前端 / 页面 / 种子资产的唯一真源** `assets/<svc>/`（portal / model / mdm / flow / report / rules / onto 七组）。
- **门户主应用 `cmx-portalservice`（:8080）是薄壳**，通过 `[center_client.services]` **反代**七个微服务引擎：flow :8091 / report :8092 / model :8093 / rules :8094 / mdm :8095 / onto :8097 / dataauth :8098。**联调最小集 = portal + model 同起**。
- **`cmx-agent`（桌面智能体）是孤岛**：无 HTTP 端口，无 cmx-container 引用，有自己的 `AGENTS.md`；所有 cargo 命令一律加 `--offline`。
- **前端 `cmx-enterprise-portal` 是 npm workspace**（包名 `cmx-monorepo`）：Portal 管理端 + HTML 设计器 + 共享包。`packages/cmx-ui5-runtime`（UI5+Tabler 运行时）是 Portal / Designer 的**构建前置——必须先建它**。`packages/cmx-data-comp` 是组件库封装源头（97 元素）。另有 3 个独立前端仓（`cmx-mega-sheet` 电子表格 / `cmx-ontology-graph` 本体图 / `cmx-decision-graph` 决策图）被对应后端引用。

## 常用命令

**前端**（在 `frontend/cmx-enterprise-portal/` 下，不是工作区根；改 `package.json` 后先 `npm install`）：

```bash
npm run dev:portal          # 本地 dev :5173（账号 admin / Admin@12345）
npm run build:apps          # 全量构建（ui5-runtime + Portal + Designer）
npm run build:runtime       # 仅共享运行时（Portal/Designer 前置）
npm run build:portal        # 仅 Portal（已含 runtime 前置）；build -w <包名> 不含前置
npm test                    # 全量 vitest；npm test -w cmx-data-comp / -w cmx-html-designer / -w cmx-shared
npm run lint                # ESLint；npx eslint <file> 单文件
```

> `frontend/cmx-mega-sheet` **不在 workspace**：进目录单独 `npm test` / `build` / `typecheck`。Portal 无自动化测试网，重构靠 build + lint + 手动 dev 验证。

**后端**（Rust / axum）：

```bash
cd backend/cmx-portalservice && cargo check    # 检查用 check/clippy，禁用 cargo build（见硬约束）
cd backend/cmx-portalservice && ./portal.sh    # 起门户主应用（--release 发布）；各引擎用各仓 *.sh
cargo run --offline -p cmx-agent-cli           # cmx-agent 专用（一律 --offline）
```

**共享 target（省磁盘，勿在各仓覆盖）**：全工作区 Rust 编译产物统一到 `~/.cargo-shared-target`，由**全局** `~/.cargo/config.toml` 的 `[build]` 段配置（`target-dir` + `incremental = false` + `rustc-wrapper = sccache`），与 sibling 工作区 `Workspace/presentation` 共用同一目录——同名仓 / 重合依赖只编一份。各 backend 仓的仓内 `.cargo/config.toml` **只配镜像源 / registry，禁止加 `[build] target-dir` 覆盖**（一覆盖就与全局分家、依赖重编、白占几十 G）。故各仓目录下**不会生成 `target/`**（无误提交风险）；磁盘紧张用 `cmx-launcher` 的 target 治理或 `sccache --show-stats` 看命中。依赖此机制需两个前置：`sccache` 已装（全局配了 `rustc-wrapper`，缺则所有 cargo 命令直接失败）、macOS 用 Homebrew bash 5+（`/bin/bash` 仍是 3.2）。

**联调控制台（推荐）**：`cd cmx-launcher && ./run.sh` → http://127.0.0.1:8100（自动发现服务，一键启停 / toml 切换 / 日志 / target 磁盘治理；Windows 用 `run.bat` / `run.ps1`）。

**资产发布**（改真源后同步发布产物）：`./scripts/publish-assets.sh <portal|model|mdm|flow|report|rules>`（发布前自动跑 `scripts/check-asset-ownership.py` 归属守护；各仓 toml `[assets]` 已直指工作区真源，此拷贝仅打包归档用）。

## 硬约束（违反即打回；完整清单见 `AGENTS.md` §四~六）

1. **禁止自动提交**：任务完成只汇报改动，等用户明确说「提交 / commit」才动 git；`.env` 只能用户自己提交。
2. **Rust 检查用 `cargo check` / `clippy`，禁止 `cargo build`**（耗时数倍；仅运行服务 / 集成测试 / release 例外）。`cmx-agent` 全部命令加 `--offline` 且 clippy 零告警。
3. **改 `cmx-container` 公用库 API 必须下游验证**：至少主应用 + 一个引擎各跑 `cargo check`（改 core/sql/web/rpc 等共用 crate 则逐仓全跑）；改 `cmx-rulesengine` 的 rule-feel/rule-model/rule-engine 须到 `cmx-data-auth` 补跑。
4. **页面 / 组件必须双主题通路兼容（UI5 + Neo），禁止硬编码色值**：UI5 色值一律 `var(--sap*, fallback)` 派生；Neo 展示类组件须支持 `data-cmx-skin` / `data-cmx-skin-tone` 切换。CI/Review 对暗色掉队、tone 失效、硬编码色值一票否决。真源：技能 `cmx-components-guide` 的 `references/{neo-theme-onboarding,frontend-conventions,page-style-guide}.md`。
5. **新增接口禁用可变路径段，禁用 PUT/PATCH/DELETE**：路径只允许固定资源段，标识 / 过滤 / 操作参数走 query 或 body；更新 / 删除一律 `POST` + JSON body（只取详情可退 `GET`）。仅约束新增接口。
6. **前端 / 数据资产真源在 `backend/cmx-container/assets/<svc>/`**：各主应用仓 `web/` / `data/` 下同名子目录是发布产物，**禁止直接改**——改真源后用 `publish-assets.sh` 同步。
7. **Git 多仓铁律**：`backend/` / `frontend/` / `cmx-launcher/` 是未跟踪的**独立子仓**——**严禁** `git add backend/` / `frontend/` / `git add .` / `-A`（嵌套仓会以 gitlink 污染跨仓），只 `git add <具体路径>`。子仓 commit 前先 `git rev-parse --show-toplevel && git remote -v && git status -sb` 自报家门。禁止 force push / 未授权 push main。
8. **集群无状态**：进程无状态、状态外置 Redis / 共享存储、定时任务用 `SELECT ... FOR UPDATE SKIP LOCKED` 可重入。❌ 禁用 `Mutex`+`OnceCell`/`LazyLock` 缓存业务数据（连接池 / 只读配置除外）、本地磁盘当持久化、前端登录态仅存 Pinia。

## 技能与文档去哪找

- **技能**（`.agents/skills/<name>/SKILL.md`，需要时才点开）：页面生成 `html-page-generator` / `native-page-generator` / `doc-crud-pages`；组件手册 `cmx-components-guide`；主数据 `mdm-master-data-onboarding`；菜单 `menu-generator`；元数据补全 `meta-enricher`；方案命名 `plan-naming`；流程 `cmx-flow-toolkit`；工作区初始化 `workspace-init`；配置同步 `config-sync`；SQL `sql-guide`。cmx-container 仓内另有 12 个后端技能。
- **规范类内容真源在技能**（组件用法 / 主题接入 / 页面样式 / SQL / handler 规范），Wiki 与 docs 与之冲突以技能为准。
- **新方案 / 计划**唯一去处 `documents/`（按 `plan-naming`：`yyyyMMdd_模块名_中文标题.md`），❌ 禁塞子仓 `docs/`；根 `docs/` 是历史只读资料区。
- **上手 / 改模块前**先查 `.qoder/repowiki/zh/{content,knowledge}/`（自动生成，与代码冲突以代码为准，仍反映重组前结构；目录名含中文空格，命令行引用须加引号）。
