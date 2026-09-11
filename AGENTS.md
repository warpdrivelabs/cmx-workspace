# CMX 开发导航

> **根路由索引**：进哪个目录、先读哪个规范、技能在哪、资料在哪、全局硬约束。子目录有自己的 `AGENTS.md` 时**子目录规范优先**，本文件仅做总览与跨子项目硬约束。

## 一、项目总览

### 1.1 顶层结构

| 目录 / 文件 | 是什么 |
| --- | --- |
| `backend/` | 全部 Rust 后端仓（10 个独立 Git 仓，见 §1.2） |
| `frontend/` | 全部前端仓（4 个独立 Git 仓：`cmx-enterprise-portal` npm workspace / `cmx-mega-sheet` / `cmx-ontology-graph` / `cmx-decision-graph`） |
| `cmx-launcher/` | 开发服务控制台（独立仓，Python FastAPI + 原生 JS，http://127.0.0.1:8100）：一键启停 / 实时日志 / target 磁盘治理 |
| `.agents/skills/` | 根级跨子项目技能 12 个（见 §三） |
| `documents/` | 人工方案库（新方案唯一去处，见 §四、8） |
| `docs/` | 历史 / 专题设计资料区（只读参考，见 §九） |
| `scripts/` | 根级脚本：`publish-assets.sh` / `check-asset-ownership.py` / `generate_*.py` ×3 |
| `.qoder/repowiki/` | 自动生成 Wiki + 模块知识库（生成物，勿手改） |

### 1.2 `backend/` —— Rust 后端仓（10 个，均为 Rust / axum）

| 目录 | 定位 |
| --- | --- |
| `cmx-container` | **公用库 + 插件平台**，无 server bin（各微服务经 `path = "../cmx-container/crates/..."` 跨 ws 引用）；**前端 / 页面 / 种子资产唯一真源** `assets/<svc>/`（portal / model / mdm / flow / report / rules / onto 七组） |
| `cmx-portalservice` | 门户主应用 `cmx-portal-server`（:8080），薄 bin 跨 ws 引 cmx-container |
| `cmx-flowengine` / `cmx-report` / `cmx-rulesengine` | 流程 / 报表 / 规则微服务（`cmx-flow-server` :8091、`cmx-rpt-server` :8092、`cmx-rule-server` :8094） |
| `cmx-model` | **模型微服务**（:8093），元数据中心：DCT / DOC / 主从 / 编码引擎 / deploy |
| `cmx-mdm` | 主数据治理（:8095），中立核 `cmx-mdm-app` + 门户反代壳 |
| `cmx-ontology` | 本体平台（:8097）：对象 / 关系 / 接口 / 动作 / 函数，一芯多壳 |
| `cmx-data-auth` | 数据权限引擎（:8098）：PDP 部分求值 + 约束 AST 多后端编译（SQL / 内存谓词 / ES）+ 列脱敏 + ReBAC，一芯多壳 |
| `cmx-agent` | 企业桌面智能体（edition 2024，当前 M1；**无 HTTP 端口**，CLI / 桌面壳）。有自己的 `AGENTS.md`，与 cmx-container 无跨仓引用 |

### 1.3 `frontend/` —— 前端仓（4 个）

| 目录 | 是什么 |
| --- | --- |
| `cmx-enterprise-portal` | 前端 npm workspace（包名 `cmx-monorepo`）：`cmx-portal-manager` 门户管理（UI5 WebComponents，dev :5173）、`cmx-html-designer` 页面设计器、`packages/cmx-data-comp` 共享数据组件库、`packages/cmx-ui5-runtime` 共享 UI5+Tabler 运行时（构建须**先建它**）、`packages/cmx-icon-resource` 图标资源、`packages/cmx-shared` 工具域注册中心 |
| `cmx-mega-sheet` | 自研电子表格引擎 `<cmx-megasheet>`（公式 / 画布 / XLSX·PDF·CSV IO，零运行时依赖） |
| `cmx-ontology-graph` | 本体图（ER）可视化编辑 Web Component，`cmx-ontology` 前端引用 |
| `cmx-decision-graph` | 决策图（JDM DAG）可视化编辑 Web Component，`cmx-rulesengine` 前端引用 |

> `cmx-enterprise-portal` 内部的 `cmx-portal-manager` / `cmx-html-designer` / `packages/*` **均非独立 Git 仓**，随该仓提交（§六）。

## 二、开发导航

进入任意子目录开发前，**先读该目录的 `AGENTS.md`**（就近原则）；无规范文件的遵循就近代码风格。

| 目录 | 权威规范 |
| --- | --- |
| `backend/cmx-container` | 仓内 `AGENTS.md`（19 章）+ `.agents/skills/`（12 个） |
| `backend/cmx-agent` | 仓内 `AGENTS.md`（不变量 / fail-closed / crate 分层） |
| 其余 8 个后端仓 | 业务层薄，遵循 `backend/cmx-container/AGENTS.md` |
| `frontend/cmx-portal-manager` / `cmx-html-designer` / `packages/cmx-data-comp` | 技能 `cmx-components-guide`（`references/frontend-conventions.md`；data-comp 是封装源头，改导出 API 需评审） |
| `frontend/cmx-enterprise-portal/packages/{cmx-ui5-runtime,cmx-icon-resource,cmx-shared}` | 无专项规范（ui5-runtime / icon-resource 改动影响 Portal + Designer，须双端构建验证） |
| `frontend/cmx-{mega-sheet,ontology-graph,decision-graph}` | 无（`README.md` 是唯一手册） |
| `cmx-launcher` | 仓内 `README.md`（唯一手册） |

## 三、技能索引

需要时点开 `.agents/skills/<name>/SKILL.md`，不要求预读。根目录 12 个 + `backend/cmx-container/.agents/skills/` 12 个。

**cmx-container（Rust 后端）**：`axum-handler-generator`（REST handler）、`modql`（Filter/Entity 动态查询）、`cmx-sql-execution`（手写 SQL / DataValue）、`pg-table-generator`（建表 DDL）、`wasm-plugin-developer`、`plugin-metadata-generator`（插件表 / 种子）、`plugin-fn-doc`（`#[plugin_fn]` 注释）、`service-orchestration-generator`（编排 Flow JSON）、`rust-comment-convention`、`clippy-fix`、`rust-arch-review`、`doc-generator`。

**根目录（跨子项目）**：

| 技能 | 触发场景 |
| --- | --- |
| `html-page-generator` | 生成设计器业务页面（html-pages）：6 大模型 + HTML + DOM 绑定 + pageFns |
| `native-page-generator` | 生成原生页面（native-pages）：JS 模块 `render(ctx)` 或 HTML 片段 |
| `doc-crud-pages` | 单据管理三页一体（列表 + 详情 + 新建） |
| `cmx-components-guide` | cmx-data-comp 组件使用手册（97 个元素；页面技能共享 references 真源） |
| `mdm-master-data-onboarding` | MDM 新增一种主数据类型（DCT + 激活映射 + 菜单 + 编码规则端到端） |
| `menu-generator` | 门户菜单增删改（menu-pages JSON 真源 + `sync_menu_db.py` 同步 `cmx_menu`） |
| `meta-enricher` | 批量补全元数据字段 edit / display / width 等（EDIT_MODES 值域，幂等） |
| `plan-naming` | 用 `/plan` 创建方案文档（命名规范唯一真源） |
| `cmx-flow-toolkit` | cmx-flowengine：流程定义部署、流程测试数据重建 |
| `workspace-init` | 刚克隆根仓后的工作区初始化（"初始化工程"触发，幂等克隆 15 个子仓） |
| `config-sync` | 全工作区唯一版（原 cmx-container 内同名技能已删除）：新增 / 修改 TOML 配置项或环境变量后同步模板与手册 |
| `sql-guide` | 全工作区唯一版（原 cmx-container 内同名技能已删除）：SQL 真源在 `backend/cmx-container/docs/sql/` |

## 四、全局通用规则

跨所有子项目，与子目录规范叠加生效。

1. **禁止自动提交代码**：完成任务仅汇报改动，等用户明确指令（"提交" / "commit"）才 `git commit`。任何情况下 `.env` 只能用户自己提交。
2. **使用中文回复。**
3. **改 `package.json` / `Cargo.toml` 后先装再构建**：先 `npm install` / `cargo check` 再 build（npm 命令在 `frontend/cmx-enterprise-portal/` 下执行，§八）。
4. **Rust 检查用 `cargo check` / `clippy`，禁止 `cargo build`**（耗时数倍；仅运行服务 / 集成测试 / release 例外）。`backend/cmx-agent` 额外要求 clippy 零告警。
5. **页面 / 组件必须双主题通路兼容（UI5 + Neo），禁止硬编码色值**，"先不接主题"的提交一律打回：
   - UI5 大主题：色值一律 `var(--sap*, fallback)` 派生，零硬编码 `#xxx` / `rgb()` / `hsl()`，禁止为亮 / 暗各写一份。
   - Neo 皮肤 / 色调：展示类组件必须接 Neo 皮肤，支持 `data-cmx-skin="plain|none"` 与 `data-cmx-skin-tone` 切换。
   - CI / Review 一票否决：暗色掉队、tone 切换失效、色值硬编码，任一命中即拒收。
   - 权威真源（必读，本文不复述细节）：技能 `cmx-components-guide` → `references/{neo-theme-onboarding,frontend-conventions,page-style-guide}.md`。
6. **新接口禁用可变路径段，禁用 PUT/PATCH/DELETE**：路径只允许固定资源段，资源标识 / 过滤 / 操作参数走 query 或 body；更新 / 删除一律 `POST`，默认 `POST` + JSON body（仅取详情 / 极少参数只读可退 `GET`）。只约束**新增接口**，既有接口保持原样。
7. **前端 / 数据资产真源发布**：`backend/cmx-container/assets/<svc>/` 是**唯一真源**；各主应用仓 `web/` / `data/` 下与真源同名的顶层子目录是发布产物，**禁止直接修改**。改真源后 `./scripts/publish-assets.sh <portal|model|mdm|flow|report|rules>` 同步（同步粒度 = 真源顶层子目录整目录替换，目标侧多余内容不删不改）。各仓 toml `[assets]` 已直指工作区真源，脚本拷贝仅打包归档用——可选跑。仅约束资源文件，不约束 Rust 源码 / `Cargo.toml` / `.env`。
8. **方案文档统一归档根目录 `documents/`**（命名按 `plan-naming`：`yyyyMMdd_模块名_中文标题.md`）：方案 / 计划进 `documents/plans/`，其它按主题子目录。❌ 禁止塞子仓 `docs/` 或随代码提交；根 `docs/` 是历史资料区，新方案不写入。仅跨子项目、长期留档的才进 `documents/`。

## 五、集群部署与无状态约束（前后端通用）

**核心原则**：进程无状态 · 可水平扩展 · 本地仅作可重建缓存 · 会话与状态外置（Redis / 共享存储）· 定时任务可重入（`SELECT ... FOR UPDATE SKIP LOCKED`）· 共享缓存变更须广播全集群 · 优雅启停（`/ready` 探针 + `SIGTERM`）。

**红线**：❌ `tokio::sync::Mutex` + `OnceCell` / `LazyLock` 缓存业务数据（连接池 / 只读配置除外）；❌ 本地磁盘当持久化；❌ 前端登录态仅存 Pinia / Vuex；❌ 定时任务假设单机；❌ 多节点各自跑全量同步 Worker；✅ DB / Redis / 对象存储 / NATS / Kafka 须集群 / 哨兵 / 高可用参数。

## 六、Git 仓库分布与操作

根仓 `cmx-workspace.git`（gitee `warpdrivelabs` org）+ **15 个独立子仓**（backend 10 + frontend 4 + launcher 1，远端同 org）。原 `cmx-portal` / `cmx-devops` 仓未拉取，忽略。

> **新克隆初始化**：clone 后 `backend/`、`frontend/`、`cmx-launcher/` 为空，说一句**"初始化工程"**（技能 `workspace-init`），或执行 `bash .agents/skills/workspace-init/scripts/init-workspace.sh`（幂等克隆 15 仓；`--update` 更新 / `--dry-run` 试跑）。子仓清单唯一真源在脚本 `REPOS` 数组，增删子仓改脚本并同步本节清单。

> **ignore 策略**：`.gitignore` 不忽略三个目录（保持 AI 可见），但它们是未跟踪的独立仓——**严禁** `git add backend/` / `frontend/` / `cmx-launcher/` / `git add .` / `-A`（嵌套仓会以 gitlink 被嵌入，跨仓污染）；只 `git add <具体路径>`。

### 仓库清单（远端均为 gitee `warpdrivelabs`）

`/`→`cmx-workspace.git`；`backend/cmx-{container,portalservice,agent,flowengine,report,rulesengine,model,mdm,ontology,data-auth}`→同名 `.git`；`frontend/cmx-{enterprise-portal,mega-sheet,ontology-graph,decision-graph}`→同名 `.git`；`cmx-launcher/`→`cmx-launcher.git`。分支：除 `cmx-mega-sheet` 为 **master** 外均 main。

### 操作要点

1. **子仓先自报家门**：`git rev-parse --show-toplevel && git remote -v && git status -sb` 再 commit / push。
2. **子仓提交不反向同步根仓**：根仓需记录时单独提交，仅针对根仓关注的文件。
3. **跨子项目资料归根仓**（§四、8），不塞子仓。
4. **改 cmx-container 公用库 API 必须下游验证**：8 个下游仓 path 引用；改后至少主应用 + 一个引擎各跑 `cargo check`（`cd backend/cmx-portalservice && cargo check`、`cd backend/cmx-flowengine && cargo check`），动多仓共用 crate（core / sql / web / rpc 等）则逐仓全跑。`cmx-data-auth` 还引用 `cmx-rulesengine` 的 rule-feel / rule-model / rule-engine——改这三个须到 data-auth 补跑。`cmx-agent` 无 path 引用，不在此列。
5. **安全协议**：禁止 force push；未经授权禁止 push main；commit / push 必须等用户明确指令（叠加 §四、1）。

## 七、联调与后端运维默认信息

- **一键控制台（推荐）**：`cd cmx-launcher && ./run.sh` → http://127.0.0.1:8100（自动发现服务，启停 / toml 切换 / 日志 / 磁盘治理；Windows 用 `run.bat` / `run.ps1`）。
- **前端联调**：`frontend/cmx-enterprise-portal/` 下 `npm run dev:portal` → http://127.0.0.1:5173/，账号 `admin` / `Admin@12345`。
- **后端配置**：主服务读 `backend/cmx-portalservice/.env`（蓝本 `backend/cmx-container/.env`，cmx-container 资源相对路径前缀 `../cmx-container/`）→ `CONFIG_FILE`（当前 `./portal-server-dev.toml`）确定生效 toml；各引擎同理 `<svc>-server-dev.toml`。资产路径在生效 toml `[assets]`（`root` + `ui_native_dir` / `ui_html_dir`；portal 另有三个前端 `dist/`），不在 `WEB_FOLDER`。`[[databases]]`：`default = true` 平台库，`source_type = "biz"` 业务库；连库 URL 从 `db_url` 解析，**不硬编码地址**。
- **后端启动**：`cd backend/cmx-portalservice && ./portal.sh`（`--release` 发布）；七引擎各仓 `*.sh`（flow :8091 / report :8092 / model :8093 / rules :8094 / mdm :8095 / onto :8097 / dataauth :8098），门户经 `[center_client.services]` 反代——**联调最小集 = portal + model 同起**。`cmx-agent` 无 HTTP：`cargo run -p cmx-agent-cli`。
- **API 鉴权**：`http://127.0.0.1:8080`（前缀 `/api`）；`POST /api/auth/login`（`{"username":"admin","password":"Admin@12345"}`）取 `data.access_token` 带 Bearer，或请求头 `X-API-Key: cmx_sk_dev_A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6`（开发免登录）。

## 八、构建与测试命令速查

npm workspace 在 `frontend/cmx-enterprise-portal/`（不是工作区根），用 `-w <包名>` 或根脚本；**改 `package.json` 后先 `npm install` 再 build**。

| 命令（在 `frontend/cmx-enterprise-portal/` 下） | 说明 |
| --- | --- |
| `npm run build:apps` | 全量构建（ui5-runtime + Portal + Designer） |
| `npm run build:runtime` | 仅共享运行时（Portal / Designer 前置） |
| `npm run build:portal` / `build:html` | 仅 Portal / Designer（已含 runtime 前置） |
| `npm run build -w cmx-portal-manager` | 单包构建（**不含** runtime 前置） |
| `npm run dev:portal` / `dev:html` | 本地 dev（Vite，默认 :5173） |
| `npm test` / `npm test -w cmx-data-comp` / `-w cmx-html-designer` / `-w cmx-shared` | 全量 / 组件库 / 设计器 / shared 测试 |
| `npm run lint` / `npx eslint <file>` | ESLint / 单文件 lint |

> `frontend/cmx-mega-sheet` 不在 workspace：进目录单独 `npm test` / `build` / `typecheck`。`backend/cmx-agent`：clippy 零告警，e2e 用 `./e2e-serve.sh`。Vite 8：Portal build ~5s、Designer ~27s；**Portal 无自动化测试网**，重构后靠 build + lint + 手动 dev 验证。

## 九、文档与知识库路径（动手前先查）

| 路径 | 是什么 / 怎么用 |
| --- | --- |
| `.qoder/repowiki/zh/{content,knowledge}/` | 自动生成 Wiki（前端为主）+ 模块知识库——**入门 / 改模块前先读**；生成物勿手改，与代码冲突以代码为准，路径按新结构换算；仍反映重组前结构 |
| `documents/` | **人工方案库（新方案唯一去处）**，按 `plan-naming` 命名（§四、8） |
| `docs/` | 历史 / 专题设计资料区（DCT/DOC、MDM、报表 / 权限 / 编码引擎、本体系列等 79 条）——查历史用，❌ 不写新方案 |
| 子仓 `docs/` + `README.md` | 各仓架构 / API 手册——后端细节查这里；跨子项目材料不要塞（§六、3） |

**红线**：规范类内容（组件用法、主题接入、页面样式、SQL / handler 规范）真源在**技能** `.agents/skills/`（§三），Wiki / docs 与之冲突以技能为准；Wiki / knowledge 目录名含中文与空格，命令行引用必须加引号。
