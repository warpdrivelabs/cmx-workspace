# CMX  开发导航

> 本文件是**根路由索引**——告诉你"进哪个目录、先读哪个规范、技能在哪、资料/Wiki 在哪、全局硬约束是什么"。子目录有自己的 `AGENTS.md` 时，**子目录规范优先**，本文件仅做总览与跨子项目硬约束。
>
> 📚 **动手前先查资料**：仓库 Wiki（`.qoder/repowiki/`）、方案库（`documents/`）、历史专题资料（`docs/`）的路径与用途见 **§九**。
>
> 🏗️ **2026-09 结构重组**：工作区由"根目录平铺子仓"重组为 **`backend/` + `frontend/` + `cmx-launcher/` 三分目录**，根目录只保留导航 / 技能 / 文档 / 脚本等共享资产。旧文档 / 技能 / 脚本里的裸路径（`cmx-container/…`、`cmx-portalservice/…`）一律对应新路径 `backend/cmx-container/…`、`backend/cmx-portalservice/…`（前端对应 `frontend/…`）。

***

## 一、项目总览

### 1.1 顶层三分 + 根级共享资产

| 目录 / 文件              | 是什么                                                                                     |
| -------------------- | -------------------------------------------------------------------------------------- |
| `backend/`           | **全部 Rust 后端仓**（10 个独立 Git 仓，见 §1.2）                                                      |
| `frontend/`          | **全部前端仓**（3 个独立 Git 仓：`cmx-enterprise-portal` npm workspace / `cmx-mega-sheet` / `cmx-ontology-graph`） |
| `cmx-launcher/`      | **开发服务控制台**（独立 Git 仓，Python FastAPI + 原生 JS 单页，<http://127.0.0.1:8100>）——一键启停 / 实时日志 / target 磁盘治理 |
| `.agents/skills/`    | 根级跨子项目技能（11 个，见 §三）                                                                      |
| `documents/`         | 人工方案库（唯一真源，见 §四、8 / §九）                                                                  |
| `docs/`              | 历史 / 专题设计资料区（只读参考，见 §九）                                                                   |
| `scripts/`           | 根级脚本（**`init-workspace.sh` 子仓初始化** / `publish-assets.sh` / `check-asset-ownership.py` / `generate_*.py` ×3） |
| `.qoder/repowiki/`   | 自动生成的仓库 Wiki + 模块知识库（生成物，勿手改）                                                              |

### 1.2 `backend/` —— Rust 后端仓（10 个）

| 目录                    | 是什么                                                                                     | 技术栈                              |
| --------------------- | --------------------------------------------------------------------------------------- | -------------------------------- |
| `cmx-container`       | 后端**公用库 + 插件平台**（无可执行 server bin；各微服务经 `path = "../cmx-container/crates/..."` 跨 ws 引用）；**前端/页面/种子资产唯一真源** `assets/<svc>/`（portal / model / mdm / flow / report / rules / onto 七组） | Rust / axum / PostgreSQL / WASM |
| `cmx-portalservice`  | **门户微服务（主应用 `cmx-portal-server`，:8080）**，薄 bin 跨 ws 引 cmx-container                           | Rust / axum                      |
| `cmx-flowengine`      | 流程微服务（`cmx-flow-server`，:8091）                                                            | Rust / axum                      |
| `cmx-report`          | 报表微服务（`cmx-rpt-server`，:8092）                                                             | Rust / axum                      |
| `cmx-model`           | **模型微服务（`cmx-model-server`，:8093）**，元数据中心：DCT / DOC / 主从 / 编码引擎 / deploy                 | Rust / axum                      |
| `cmx-rulesengine`     | 规则微服务（`cmx-rule-server`，:8094）                                                            | Rust / axum                      |
| `cmx-mdm`             | **主数据治理微服务（`cmx-mdm-server`，:8095）**，中立核 `cmx-mdm-app` + 门户反代壳                              | Rust / axum                      |
| `cmx-ontology`        | **本体平台微服务（`cmx-onto-server`，:8097）**，Palantir 式企业本体（对象/关系/接口/动作/函数），一芯多壳（onto-model / onto-store-pg / onto-app / onto-server） | Rust / axum                      |
| `cmx-data-auth`       | **数据权限引擎微服务（`cmx-dataauth-server`，:8098）**，PDP 部分求值产出约束 AST 多后端编译（SQL / 内存谓词 / ES）+ 列脱敏 + ReBAC，一芯多壳（dataauth-core / store-pg / app / server） | Rust / axum                      |
| `cmx-agent`           | **企业桌面智能体微服务**（复刻腾讯云 WorkBuddy，「形/核/体」三层；当前 M1：内核回合循环 + 五层守卫 + 会话 JSONL 落库 + JSON 前门，**CLI/桌面壳、无 HTTP 端口**；构建测试一律加 `--offline`）。有自己的 `AGENTS.md`，与 cmx-container 无跨仓 path 引用 | Rust / edition 2024              |

### 1.3 `frontend/` —— 前端仓（3 个）

| 目录                                | 是什么                                                                                     | 技术栈                                   |
| --------------------------------- | --------------------------------------------------------------------------------------- | ------------------------------------ |
| `cmx-enterprise-portal`           | **前端 npm workspace**（原根仓迁出，包名 `cmx-monorepo`）                                             | 原生 JS / npm workspaces              |
| ├ `cmx-portal-manager`            | 门户管理（UI5 WebComponents，dev :5173）                                                        | 原生 JS / Vite 8 / UI5 / Lit          |
| ├ `cmx-html-designer`             | HTML 页面设计器                                                                               | 原生 JS / Vite 8                       |
| └ `packages/cmx-data-comp`        | 共享数据组件库（表格/表单/数据集）                                                                       | 原生 JS Web Components / Vitest 4     |
| └ `packages/cmx-ui5-runtime`      | 共享 UI5 + Tabler 运行时（前端挂 `/shared/`，Portal / Designer 均依赖，构建须**先建它**）                          | 原生 JS / Vite 8                      |
| └ `packages/cmx-icon-resource`    | 共享图标资源（Tabler / SAP 图标）                                                                  | 静态资源                                |
| └ `packages/cmx-shared`           | **共享纯工具域注册中心**（运行时挂 `globalThis.cmx.{domain}`，native/html 资产页经全局取用，与组件库解耦）                    | 原生 JS / Vitest 4                    |
| `cmx-mega-sheet`                  | 自研电子表格引擎（`<cmx-megasheet>` 自定义元素，零运行时依赖，含公式引擎 / 画布渲染 / XLSX·PDF·CSV IO）                        | TypeScript / Web Components / Vitest |
| `cmx-ontology-graph`              | 本体图可视化编辑 Web Component（ER 图：富卡片对象 + 基数关系边 + 接口虚线），`cmx-ontology` 前端四区工作台引用                     | TypeScript / 零框架零运行时依赖               |

> `cmx-enterprise-portal` 内部的 `cmx-portal-manager` / `cmx-html-designer` / `packages/*` **均非独立 Git 仓**，随 `cmx-enterprise-portal` 仓提交（见 §六）。

***

## 二、开发导航

进入任意子目录开发前，**先读该目录的 `AGENTS.md`**（就近原则）。无规范文件的目录遵循就近代码风格。

| 目录                                                                                          | 权威规范 / 技能目录                                                                  |
| ------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| `backend/cmx-container`                                                                     | `backend/cmx-container/AGENTS.md`（19 章）+ `.agents/skills/`（14 个）              |
| `backend/cmx-agent`                                                                         | `backend/cmx-agent/AGENTS.md`（不变量 / fail-closed / crate 分层等架构约束）             |
| `backend/cmx-portalservice` / `backend/cmx-flowengine` / `backend/cmx-report` / `backend/cmx-rulesengine` / `backend/cmx-mdm` / `backend/cmx-model` / `backend/cmx-ontology` / `backend/cmx-data-auth` | 业务层薄，遵循 `backend/cmx-container/AGENTS.md`（各仓 README 有架构说明）   |
| `frontend/cmx-mega-sheet` / `frontend/cmx-ontology-graph`                                   | 无（遵循就近代码风格；`README.md` 是唯一手册）                                                 |
| `frontend/cmx-enterprise-portal/cmx-portal-manager` / `cmx-html-designer`                   | 技能 `cmx-components-guide`（`references/frontend-conventions.md`）                 |
| `frontend/cmx-enterprise-portal/packages/cmx-data-comp`                                     | 技能 `cmx-components-guide`（封装源头，改导出 API 需评审）                                  |
| `frontend/cmx-enterprise-portal/packages/cmx-ui5-runtime` / `packages/cmx-icon-resource` / `packages/cmx-shared` | 无专项规范（ui5-runtime / icon-resource 改动影响 Portal + Designer 两端，须双端构建验证）    |
| `cmx-launcher`                                                                              | `cmx-launcher/README.md`（功能 / 启停 / 目录结构唯一手册）                                 |

***

## 三、技能索引

需要时点开 `.agents/skills/<name>/SKILL.md` 查看，不要求预读。根目录 12 个（跨子项目）+ `backend/cmx-container/.agents/skills/` 14 个（Rust 后端）。

> ⚠️ 结构重组后，部分技能正文里的仓库内路径引用仍是旧平铺路径（如 `cmx-container/assets/…`），使用时按 §首部约定加 `backend/` / `frontend/` 前缀解读；后续逐步修正技能正文。

### cmx-container（Rust 后端，`backend/cmx-container/.agents/skills/`）

| 技能                                  | 触发场景                          |
| ----------------------------------- | ----------------------------- |
| `axum-handler-generator`            | 生成 axum REST handler 前       |
| `modql`                             | 设计 Filter / Entity、动态查询过滤 |
| `cmx-sql-execution`                 | 手写 SQL、构造 DataValue         |
| `pg-table-generator`                | 新建 PostgreSQL 表 DDL          |
| `sql-guide`                         | 编写 / 维护 SQL 迁移、`init_ddl.sql` |
| `config-sync`                       | 新增 / 修改 TOML 配置项或环境变量       |
| `wasm-plugin-developer`             | 开发 WASM 插件项目                |
| `plugin-metadata-generator`         | 创建 / 修改插件表、种子数据            |
| `plugin-fn-doc`                     | 编写 `#[plugin_fn]` 函数文档注释     |
| `service-orchestration-generator`   | 创建 / 编辑服务编排 Flow JSON       |
| `rust-comment-convention`           | 编写 / 审查 Rust 文档注释           |
| `clippy-fix`                        | 检查 / 修复 clippy 警告           |
| `rust-arch-review`                  | Rust 架构审查（4 大类 11 子维度）           |
| `doc-generator`                     | 为 crate 生成 README            |

### 根目录（跨子项目，`.agents/skills/`）

| 技能                     | 触发场景                                                                                                |
| ---------------------- | --------------------------------------------------------------------------------------------------- |
| `html-page-generator`  | 生成**设计器业务页面**（html-pages）：6 大模型 `__designer_meta__.models` + HTML + DOM 绑定 + pageFns                |
| `native-page-generator` | 生成**原生页面**（native-pages）：JS 模块 `render(ctx)` 或 HTML 片段                                               |
| `doc-crud-pages`        | 生成**单据管理三页一体**（列表 + 详情 + 新建）：跨页传参、预建根行、保存链路、字典引用列                                          |
| `cmx-components-guide`  | **cmx-data-comp 组件使用手册**（97 个自定义元素；含页面技能共享的 component-catalog / field-edit-display-modes / page-style-guide 真源） |
| `mdm-master-data-onboarding` | MDM 新增一种**主数据类型**（客户/物料/组织等）：DCT 元数据 + 激活映射 + 菜单 + 编码规则端到端配置                                    |
| `menu-generator`        | 门户**菜单**增删改：menu-pages JSON（真源）+ `.agents/skills/menu-generator/scripts/sync_menu_db.py` 同步 `cmx_menu`              |
| `meta-enricher`         | 批量**补全元数据**字段 edit/display/width 等列属性（EDIT_MODES 规范值域，幂等）                                          |
| `plan-naming`           | 用 `/plan` 创建方案文档（全工作区唯一真源）                                                                          |
| `cmx-flow-toolkit`      | cmx-flowengine 双模式：流程定义部署、流程测试数据重建                                                               |
| `workspace-init`        | **刚克隆根仓后的工作区初始化**：一句"初始化工程"触发，跑 `scripts/init-workspace.sh` 幂等克隆 14 个子仓 + 校验 + 后续步骤指引        |
| `config-sync`           | 根级版（与 cmx-container 内同名技能**内容不同、各自演化**：根级面向全工作区，container 版面向其仓内 `config/` 模板）                      |
| `sql-guide`             | 根级版（同上，与 container 内同名技能内容不同）                                                                     |

### 技能编写规范（新增/修改技能必读）

1. **frontmatter**：仅 `name`（无引号）+ `description`（中文单段，句式「当用户……时必用」，写全触发关键词——description 是技能被命中的唯一入口）。
2. **渐进式披露**：SKILL.md ≤400 行，只放决策入口（边界/决策树/工作流/索引/自检）；模板、示例、大段代码、逐项规范下沉 `references/`；脚本一律放 `scripts/` 子目录。
3. **引用原则**：引用仓库内文件给**相对路径**（禁 `file:///` 绝对 URI）；**禁精确行号**（重构即失效，改用「文件 + 函数/符号名」定位）；引用的数字（组件数、字典数、章数）必须实测并注明口径。
4. **共享真源**：跨技能重复内容只留一份（前端共享 references 挂 `cmx-components-guide`，后端 SQL 共享内容挂 `cmx-sql-execution`），引用方只留链接不复述。
5. **产物文档**：技能产出的计划/报告按 `plan-naming` 命名，归档工作区根 `documents/plans/`（子仓内不建 documents/）。
6. **改完自检**：新增路径引用逐一 `test -e`；同库无逐字节重复文件；frontmatter 与触发关键词无丢失。

***

## 四、全局通用规则

跨所有子项目，与子目录规范叠加生效。

1. **禁止自动提交代码** — 完成任务后仅汇报改动，等用户明确指令（"提交"/"commit"）才执行 `git commit`。任何情况下`.env`文件都只能用户自己提交，不允许ai提交。
2. **使用中文回复。**
3. **改** `package.json` / `Cargo.toml` **后先装再构建** — 先 `npm install` / `cargo check` 同步依赖，再 `build`，避免依赖未装导致构建失败。（npm 命令在 `frontend/cmx-enterprise-portal/` 下执行，见 §八。）
4. **Rust 编译检查用** `cargo check` / `cargo clippy` — 禁止用 `cargo build`（耗时是 check 的数倍），仅产可执行产物（运行服务 / 跑集成测试 / release）时例外。`backend/cmx-agent` 额外要求**一律加 `--offline`**。
5. **所有页面 / 组件必须支持主题切换（UI5 + Neo），禁止硬编码色值** — CMX 同时存在**两条主题通路**（UI5 大主题 + Neo 皮肤 / 色调），新写的前端代码（页面、组件、CSS）**必须同时兼容两条**；任何"先不接主题，事后再说"的提交**一律打回**。

   **强约束要点**（详见技能，**不重复**展开）：

   - **UI5 大主题**（`sap_horizon` / `sap_fiori_3` / `*_dark` / `*_hcb`）必须兼容——色值一律 `var(--sap*, fallback)` 派生、**零硬编码** `#xxx` / `rgb()` / `hsl()`；**禁止**为亮 / 暗各写一份（`color-mix` + `--sap*` 自动适配）。
   - **Neo 皮肤 / 色调**（cyan / mint / violet / azure）必须兼容——展示类组件（form / grid / panel / toolbar / status-tag / empty-state / desc-list / filter-bar 等）**必须**接 Neo 皮肤，支持 `data-cmx-skin="plain|none"` 关闭和 `data-cmx-skin-tone="..."` 色调切换。
   - CI / Code Review **一票否决**："切 UI5 暗色主题后视觉掉队" / "切 Neo tone 后强调色不变" / "色值硬编码"——任一命中即拒收。

   **权威指南**（必须阅读，不在 AGENTS.md 复述细节）：

   - 完整接入步骤、模板代码、A/B 写法判定、反模式：技能 `cmx-components-guide` → `references/neo-theme-onboarding.md`（**全工作区唯一真源**）。
   - 前端复用规范 / 白名单 / 红线：技能 `cmx-components-guide` → `references/frontend-conventions.md`。
   - 页面样式规范：技能 `cmx-components-guide` → `references/page-style-guide.md`（页面技能 `html-page-generator` / `native-page-generator` 共享此真源）。

   **新组件 / 新页面提交前必过**（执行细节见技能 `neo-theme-onboarding.md` §6.2 / §9 自检清单）：零硬编码色值、亮 / 暗主题可读、tone 切换生效、plain 模式回退、字体 / 圆角 / 间距符合 neo 规范。
6. **新接口禁用可变路径段，禁用 PUT/PATCH/DELETE** —

   - 路径里只允许**固定资源段**（如 `/api/mdm/activations`），资源标识 / 过滤 / 操作参数走 query 或 body。
   - 更新 / 删除一律 `POST`。
   - 默认 `POST` + JSON body；只有"取一条详情"或"参数极少且语义只读"时才退到 `GET` + query。
   - ✅ 只对**新增接口**生效；既有接口保持原样。
7. **前端资源 / 数据资产必须从工作区真源发布** — `backend/cmx-container/assets/<svc>/` 是**唯一真源**；各主应用仓 `web/` / `data/` 下**与真源同名的顶层子目录**（如 `ui-html/`、`ui-native/`）是 `publish-assets.sh` 的发布产物，**禁止直接修改**（下次发布整目录替换即被覆盖）。注：重组后 `cmx-portalservice` 的 `web/` 发布产物已清理，仅存 `data/`。

   - ⚠️ **重组遗留**：根 `scripts/publish-assets.sh` 与 `scripts/check-asset-ownership.py` 内部路径仍指向旧平铺结构（`$ROOT/cmx-container/...`、`$ROOT/<repo>`），**在新结构下运行会失败**——需先改为 `$ROOT/backend/cmx-container/...`、`$ROOT/backend/<repo>` 再用。
   - 改完 `backend/cmx-container/assets/<svc>/` 后执行 `./scripts/publish-assets.sh <portal|model|mdm|flow|report|rules>` 同步（svc → 目标仓：portal→`backend/cmx-portalservice`、model→`backend/cmx-model`、mdm→`backend/cmx-mdm`、flow→`backend/cmx-flowengine`、report→`backend/cmx-report`、rules→`backend/cmx-rulesengine`；`onto` 无本地 publish 目标，页面经平台反代）。
   - 同步粒度 = 真源 `web/`（`data/`）下的**顶层子目录**逐个整目录替换 + 顶层散文件覆盖拷入；目标目录下真源没有的其它内容（README、`core/` 等）**不删不改**。真源撤销某顶层子目录后，目标仓残留同名目录需**人工清理**（脚本仅提示）。
   - 归属自检：`python scripts/check-asset-ownership.py`（校验是否误改了发布产物而非真源；同样待适配新路径）。
   - ✅ 仅约束**资源文件**（页面 / JS / HTML / JSON / BPMN / 种子数据 / 菜单 / 元数据），不约束各仓 Rust 源码 / `Cargo.toml` / `.env`。
   - ✅ 各主应用仓 `[assets]` 已**直指工作区**（运行时直接读 `backend/cmx-container/assets/<svc>/`），发布脚本的拷贝仅用于打包 / 归档一致性——可选跑。
8. **方案 / 规划 / 计划类文档统一归档到根目录** `documents/`，按 `plan-naming` 命名（`.agents/skills/plan-naming/SKILL.md`）：

   - 方案 / 规划 / 计划 进 `documents/plans/`；其它（复盘 / 技术债 / 专题）按主题建子目录（现有：`MDM主数据管理平台/`、`复杂问题分析/`、`技术债/`）。
   - 命名：`yyyyMMdd_模块名_中文标题.md`（带模块）或 `yyyyMMdd_中文标题.md`（无模块）。日期 `yyyyMMdd`、标题**必须中文**、`_` 分隔、`.md` 后缀。
   - ✅ 跨子项目、需长期留档的方案才进 `documents/`；子仓 `README.md` / `docs/` 是该仓的架构 / API 手册，**不强制**搬——但若陈旧 / 脱节，应在 `documents/plans/` 起"对齐计划"再迁移。
   - ❌ 禁止把方案文档塞到子仓 `docs/` 或随代码提交——会随子仓独立发布而脱节；根目录 `docs/` 是**历史专题资料区**（只读参考），新方案也不要写进去（详见 §九）。

***

## 五、集群部署与无状态约束（前后端通用）

**核心原则**：进程无状态 · 可水平扩展 · 本地仅作可重建缓存 · 会话与状态外置（Redis / 共享存储）· 定时任务可重入（`SELECT ... FOR UPDATE SKIP LOCKED`）· 共享缓存变更须广播全集群 · 优雅启停（`/ready` 探针 + `SIGTERM`）。

**红线**：

- ❌ `tokio::sync::Mutex` + `OnceCell` / `LazyLock` 缓存业务数据（基础设施连接池、只读配置除外）。
- ❌ 本地磁盘当持久化存储。
- ❌ 前端登录态仅存于 Pinia / Vuex。
- ❌ 定时任务假设"只有我这一台在跑"。
- ❌ 多节点各自跑全量数据同步 Worker。
- ✅ DB / Redis / 对象存储 / NATS / Kafka 须集群 / 哨兵 / 高可用参数。

***

## 六、Git 仓库分布与操作注意

本工作区是**根仓 + 14 个独立子仓**：根仓 `cmx-workspace.git`（gitee `warpdrivelabs` org）承载根级共享资产；`backend/` 10 仓 + `frontend/` 3 仓 + `cmx-launcher/` 1 仓均为独立 Git 仓，远端统一在 gitee `warpdrivelabs` org。`frontend/cmx-enterprise-portal` 内部的 `cmx-portal-manager` / `cmx-html-designer` / `packages/*` **非独立 Git**，随该仓提交。原 `cmx-portal` / `cmx-devops` 仓未拉取，忽略。

> **🚀 新克隆根仓后的初始化**：clone `cmx-workspace` 后 `backend/`、`frontend/`、`cmx-launcher/` 为空，对 AI 说一句**"初始化工程"**（触发技能 `workspace-init`），或直接执行：
>
> ```bash
> ./scripts/init-workspace.sh            # 幂等克隆全部 14 个子仓（--depth 1 浅克隆 / --update 顺带更新 / --dry-run 试跑）
> # PowerShell / cmd 终端改用：bash scripts/init-workspace.sh（Windows 装 Git 即自带 bash）
> ```
>
> 子仓清单**唯一真源**在该脚本的 `REPOS` 数组；新增/下线子仓时改脚本并同步本节仓库清单。

> **根仓 ignore 策略**：`.gitignore` **不忽略** `/backend/`、`/frontend/`、`cmx-launcher/`（保持三目录对 AI 工具可见可索引），但它们是**未跟踪**的独立 Git 仓——**严禁** `git add backend/`、`git add frontend/`、`git add cmx-launcher/`、`git add .`、`git add -A`——嵌套 Git 仓只能以 gitlink 形式被嵌入，会造成跨仓污染；提交前 `git status -sb` 确认范围，只 add 根级文件。

### 仓库清单

| 路径                                              | 性质      | 远端（均为 gitee `warpdrivelabs` org）       |
| ----------------------------------------------- | ------- | -------------------------------------- |
| `/`（根目录）                                        | Git     | `cmx-workspace.git`（根级共享资产）            |
| `backend/cmx-container/`                        | Git     | `cmx-container.git`（后端公用库，无 server bin） |
| `backend/cmx-portalservice/`                    | Git     | `cmx-portalservice.git`（主应用 bin，:8080）   |
| `backend/cmx-agent/`                            | Git     | `cmx-agent.git`（桌面智能体，M1）              |
| `backend/cmx-flowengine/` / `backend/cmx-report/` / `backend/cmx-rulesengine/` / `backend/cmx-mdm/` / `backend/cmx-model/` / `backend/cmx-ontology/` / `backend/cmx-data-auth/` | Git | `cmx-<svc>.git`（各引擎微服务）        |
| `frontend/cmx-enterprise-portal/`               | Git     | `cmx-enterprise-portal.git`（前端 npm workspace，main 分支） |
| `frontend/cmx-mega-sheet/`                      | Git     | `cmx-mega-sheet.git`（**master 分支**）      |
| `frontend/cmx-ontology-graph/`                  | Git     | `cmx-ontology-graph.git`（main 分支）        |
| `cmx-launcher/`                                 | Git     | `cmx-launcher.git`（开发服务控制台）            |

### 操作要点

1. **根目录慎用** `git add .` / `-A` — 除通用风险外，当前会把未跟踪的 `backend/` / `frontend/` / `cmx-launcher/` 整目录以 gitlink 纳入暂存区，跨仓污染。提交前 `git status -sb` 确认范围，改用 `git add <具体路径>`。
2. **进入子仓先自报家门** — 先 `git rev-parse --show-toplevel && git remote -v && git status -sb` 再决定 commit / push。
3. **子仓提交不反向同步根仓** — 根仓需要记录"子仓已更新"（如刷新引用快照）时，须在根目录单独提交一次，**仅针对根仓关注的文件**。
4. **跨子项目资料归根仓** — 导航、计划、`documents/` 等不要塞到子仓内（详见 §四、8）。
5. **改 cmx-container 公用库 API 必须下游验证** — 8 个下游仓（`cmx-portalservice` / `cmx-flowengine` / `cmx-report` / `cmx-rulesengine` / `cmx-model` / `cmx-mdm` / `cmx-ontology` / `cmx-data-auth`）都经 `path = "../cmx-container/crates/..."` 反向引用公用库；改后**至少**在主应用 + 一个引擎各跑 `cargo check`，动到被多仓共用的 crate（core / sql / web / rpc 等）则**逐仓全跑**：
   ```bash
   cd backend/cmx-portalservice && cargo check
   cd backend/cmx-flowengine && cargo check
   ```
   > `backend/cmx-data-auth` 还跨仓引用 `cmx-rulesengine` 的 rule-feel / rule-model / rule-engine crate——改 rulesengine 这三个 crate 时须到 `cmx-data-auth` 补跑 `cargo check`。`backend/cmx-agent` 与 cmx-container **无** path 引用（独立 kernel），不在此列。
6. **安全协议叠加** — 禁止 force push；未经授权禁止 push main；任何 commit / push 必须等用户明确指令（与 §四、1 叠加）。

***

## 七、联调与后端运维默认信息

### 7.1 一键控制台（推荐）

`cmx-launcher`（<http://127.0.0.1:8100>）：自动扫描工作区发现全部 `*-server` bin 与前端 Vite 应用，支持启停 / `*.toml` 配置切换 / 实时日志（SSE）/ target 磁盘治理。启动：`cd cmx-launcher && ./run.sh`（Windows 用 `run.bat` 或 `run.ps1`）。

### 7.2 前端联调（webapp-testing / Playwright）

- 前端地址：`http://127.0.0.1:5173/`（在 `frontend/cmx-enterprise-portal/` 下 `npm run dev:portal` 启动）
- 登录账号：`admin` / 密码：`Admin@12345`

> 适用于 Vite 启动的本地开发服务。端口或账号变更时按用户最新指令覆盖。

### 7.3 后端配置与数据库解析

主服务 `cmx-portal-server` 在 `backend/cmx-portalservice` 仓库，读它自己的 `.env` / toml。

- **只读** `backend/cmx-portalservice/.env`（蓝本是 `backend/cmx-container/.env`，凡指向 cmx-container 资源的相对路径前缀 `../cmx-container/`，如 `WEB_FOLDER="../cmx-container/crates/web/web-folder"`），取 `CONFIG_FILE`（当前 `./portal-server-dev.toml`）确定生效的 toml。各引擎微服务同理：`<svc>-server-dev.toml`（dev）/ `<svc>-server.toml`；`cmx-data-auth` 用 `data-auth-server.toml.example` 作蓝本。
- 页面 / 字典 / 元数据等**资产路径不在 `WEB_FOLDER`**，在生效 toml 的 `[assets]`：`root`（如 `../cmx-container/assets/portal/data`）+ `ui_native_dir` / `ui_html_dir`（如 `../cmx-container/assets/<svc>/web/ui-native`）；portal 另有 `web_portal_dist` / `web_html_dist` / `web_shared_dist` 指向三个前端 `dist/`。
- 解析 `[[databases]]`：`default = true` 的是**平台库**（菜单、治理表），`source_type = "biz"` 的是**业务库**。
- 连库 URL 从数据源 `db_url` 解析，**不硬编码地址**。

### 7.4 后端启动

```bash
cd backend/cmx-portalservice && ./portal.sh    # 开发模式（debug，增量编译）
./portal.sh --release                           # 发布模式
```

七个引擎微服务（flow :8091 / report :8092 / model :8093 / rules :8094 / mdm :8095 / onto :8097 / dataauth :8098）各仓各自 `*.sh`（`flow.sh` / `report.sh` / `model.sh` / `rules.sh` / `mdm.sh` / `onto.sh` / `dataauth.sh`）启动；门户经 `[center_client.services]` 反代。前端资产真源在 `backend/cmx-container/assets/<svc>/`，由各仓 toml `[assets]` 直指（见 §四、7）。`backend/cmx-agent` 无 HTTP 服务（CLI / 桌面壳），用 `cargo run --offline -p cmx-agent-cli`。

### 7.5 服务地址与 API 鉴权

- 后端：`http://127.0.0.1:8080`（API 前缀 `/api`，如 `/api/mdm/health`）
- 鉴权二选一：
   1. 登录取 token：`POST /api/auth/login`（`{"username":"admin","password":"Admin@12345"}`）→ `data.access_token`，后续带 `Authorization: Bearer <token>`；
   2. 或请求头 `X-API-Key: cmx_sk_dev_A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6`（开发环境免登录）。

***

## 八、构建与测试命令速查

npm workspace 在 `frontend/cmx-enterprise-portal/`（**不是工作区根**），统一用 `-w <包名>` 或根脚本执行。**改 `package.json` 后先 `npm install` 再 build。**

| 命令（在 `frontend/cmx-enterprise-portal/` 下） | 说明                                  |
| --------------------------------------- | ----------------------------------- |
| `npm run build:apps`                    | 全量构建（cmx-ui5-runtime + Portal + Designer） |
| `npm run build:runtime`                 | 仅构建共享运行时（Portal / Designer 的前置依赖）   |
| `npm run build:portal` / `build:html`   | 仅构建 CMXPortalManager / CMXHTMLDesigner（各自已含 runtime 前置） |
| `npm run build -w cmx-portal-manager`   | 单包构建（**不含** runtime 前置）             |
| `npm run dev:portal` / `dev:html`       | 本地 dev（Vite，默认 :5173）              |
| `npm test`                              | 全量测试（cmx-data-comp + cmx-html-designer） |
| `npm test -w cmx-data-comp`             | cmx-data-comp 单元测试（~616 用例）       |
| `npm test -w cmx-html-designer`         | CMXHTMLDesigner 单元测试（~108 用例）     |
| `npm test -w cmx-shared`                | cmx-shared 单元测试（Vitest）            |
| `npm run lint`                          | ESLint（cmx-data-comp + cmx-portal-manager） |
| `npx eslint <file>`                     | 单文件 lint（绕过项目脚本）                    |

> `frontend/cmx-mega-sheet` **不在** workspace 内：进目录单独跑（`npm test` / `npm run build` / `npm run typecheck`，vitest + tsc）。
>
> `backend/cmx-agent`：`cargo build/test/clippy` 一律加 `--offline`，clippy 必须零告警；e2e 用 `./e2e-serve.sh`。
>
> Vite 8 / Rolldown：Portal build ~5s、Designer ~27s。**CMXPortalManager 无自动化测试网**，重构后只能靠 `npm run build -w cmx-portal-manager` + lint + 手动 dev 验证。

### 根目录遗留（重组后失效，待清理）

- `e2e-struct.mjs` / `shot-hdr.mjs`：Playwright 脚本，写死旧机器 macOS 路径（`/Users/nanomesh/...`），已不可用。
- 根 `README.md`：仍是旧"presentation monorepo"自述，与现三分结构不符（前端自述见 `frontend/cmx-enterprise-portal/`）。
- `.gitignore` 中 `docs-site/` 相关规则：`docs-site/` 目录已不存在，为历史遗留。

***

## 九、文档与知识库路径（动手前先查）

五处资料并存，**用途不同别混**：

| 路径                                   | 是什么                                                                                                                          | 怎么用                                                     |
| ------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| `.qoder/repowiki/zh/content/`         | **仓库 Wiki（自动生成，中文）**——前端侧为主：`项目概览.md` / `快速开始.md` / `开发指南.md` + 11 个专题目录（`架构设计`、`门户管理器 (CMXPortalManager)`、`可视化设计器 (CMXHTMLDesigner)`、`数据组件库 (cmx-data-comp)`、`电子表格引擎 (cmx-mega-sheet)`、`共享包`、`扩展开发`、`最佳实践`、`故障排除`、`部署运维`、`API 参考文档`） | **入门 / 补背景首选**（读，别改）；元数据 `.qoder/repowiki/zh/meta/repowiki-metadata.json` |
| `.qoder/repowiki/knowledge/zh/`       | **模块知识库（自动生成）**——含 `_index.yaml` + 构建发布体系、配置体系（TOML + Nacos）、日志体系（tracing / chassis）、错误处理体系、样式体系（UI5 + Neo）、npm 依赖管理等条目 | **改某模块前**先读该条目的 `概述` / `架构设计` / `技术栈` / `编码规范` / `特殊配置与命令` |
| `documents/`                          | **人工方案库（唯一真源，见 §四、8）**——根 37 个方案散文件 + `plans/`（22）、`MDM主数据管理平台/`（20）、`复杂问题分析/`（3）、`技术债/`（3）                                    | **新方案 / 计划写这里**，按 `plan-naming` 命名                     |
| `docs/`                              | **历史 / 专题设计资料区**——79 个条目（DCT/DOC 元数据、MDM、Rust-WASM、SAP FI/CO 参考、报表 / 权限 / 编码引擎、WorkBuddy / cmx-agent 系列、本体平台系列等 + `CMXPortalManager+CMXHTMLDesigner-模型体系文档/`、`assets/`、`.cache/` 脚本抓取缓存） | **查历史设计**用；❌ 不要往里写新方案                                 |
| 子仓 `docs/` + `README.md`             | 各仓自身架构 / API / 测试手册（如 `backend/cmx-container/docs/{sql,assessments}`、`backend/cmx-flowengine/docs/{usage,biz-test,agent-flows}`、`backend/cmx-report/docs/summary`、`backend/cmx-rulesengine/docs/full-test`） | 后端细节查这里；跨子项目材料**不要**塞进去（§六、4）                       |

**红线**：

- `.qoder/repowiki/` 全是**生成物**——不手工编辑（重新生成即覆盖）；与代码冲突时**以代码为准**，并按 §四、8 把纠偏结论写进 `documents/`。Wiki 内容仍反映重组前的目录结构，路径按新结构换算后使用。
- Wiki / knowledge 目录名含中文与空格，命令行引用**必须加引号**。
- 规范类内容（组件用法、主题接入、页面样式、SQL / handler 规范）真源在**技能** `.agents/skills/`（§三），不在 Wiki / docs——两者冲突以技能为准。
