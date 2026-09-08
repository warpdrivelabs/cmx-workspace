# CMX Workspace — 元数据驱动企业平台 · 多仓工作区

CMX 全家桶工作区：**10 个 Rust 后端微服务仓 + 3 个前端仓 + 1 个开发控制台**，元数据驱动（换一份定义 JSON 即得一套单据/字典/报表/流程），根仓承载导航、技能、文档与脚本等共享资产。

## 目录结构

```
cmx-workspace/
├── backend/                    # Rust 后端仓（10 个独立 Git 仓）
│   ├── cmx-container/          # 公用库 + 插件平台 + 资产真源 assets/<svc>/（无 server bin）
│   ├── cmx-portalservice/      # 门户主应用 cmx-portal-server  :8080
│   ├── cmx-flowengine/         # 流程 cmx-flow-server           :8091
│   ├── cmx-report/             # 报表 cmx-rpt-server            :8092
│   ├── cmx-model/              # 模型/元数据中心 :8093
│   ├── cmx-rulesengine/        # 规则 :8094
│   ├── cmx-mdm/                # 主数据治理 :8095
│   ├── cmx-ontology/           # 企业本体平台 :8097
│   ├── cmx-data-auth/          # 数据权限引擎 :8098
│   └── cmx-agent/              # 桌面智能体（CLI/桌面壳，M1）
├── frontend/                   # 前端仓（3 个独立 Git 仓）
│   ├── cmx-enterprise-portal/  # 前端 npm workspace（Portal + Designer + 组件包）
│   ├── cmx-mega-sheet/         # 自研电子表格引擎（TypeScript Web Components）
│   └── cmx-ontology-graph/     # 本体图可视化编辑组件
├── cmx-launcher/               # 开发服务控制台 :8100（启停/日志/target 治理）
├── .agents/skills/             # 跨子项目技能（12 个）
├── documents/                  # 人工方案库（唯一真源）
├── docs/                       # 历史 / 专题设计资料（只读参考）
├── scripts/                    # 根级脚本（资产发布等）
└── AGENTS.md                   # AI 协作导航 + 全局硬约束（必读）
```

## 快速开始

```bash
# 1. 克隆本仓（backend/frontend/launcher 为空壳，子仓见下一步）
git clone https://gitee.com/warpdrivelabs/cmx-workspace.git
cd cmx-workspace

# 2. 初始化 14 个子仓（幂等，可重跑；对 AI 说"初始化工程"亦可）
bash .agents/skills/workspace-init/scripts/init-workspace.sh

# 3. 前端（:5173）
cd frontend/cmx-enterprise-portal && npm install && npm run dev:portal

# 4. 后端门户主应用（:8080，需 PostgreSQL）
cd backend/cmx-portalservice && ./portal.sh
```

日常开发推荐用 [`cmx-launcher`](cmx-launcher/README.md)（:8100）一键启停全部服务；各引擎微服务用各仓 `*.sh` 启动，详见 `AGENTS.md` §七。

## 文档与规范

| 资料 | 位置 | 说明 |
|------|------|------|
| AI 协作导航 | `AGENTS.md` | 目录规范、技能索引、全局硬约束、Git 多仓规则 |
| 方案库 | `documents/` | 跨子项目方案/计划唯一真源（按 `yyyyMMdd_模块_中文标题.md` 命名） |
| 历史专题资料 | `docs/` | 只读参考，勿写新方案 |
| 仓库 Wiki | `.qoder/repowiki/` | 自动生成，与代码冲突以代码为准 |
| 各仓手册 | 各子仓 `README.md` / `docs/` | 架构 / API / 测试手册 |

## 仓库清单

14 个子仓均为独立 Git 仓（远端统一 `gitee.com/warpdrivelabs`），清单真源在 `init-workspace.sh`：

`backend/`：cmx-container · cmx-portalservice · cmx-agent · cmx-flowengine · cmx-report · cmx-model · cmx-rulesengine · cmx-mdm · cmx-ontology · cmx-data-auth
`frontend/`：cmx-enterprise-portal · cmx-mega-sheet · cmx-ontology-graph
根下：cmx-launcher

> 子仓内容**不进本仓**（嵌套独立仓）；提交前 `git status -sb` 确认范围，详见 `AGENTS.md` §六。

## 参与贡献 / 安全 / 许可

见 [CONTRIBUTING.md](CONTRIBUTING.md) · [SECURITY.md](SECURITY.md)（**勿开公开 Issue**） · [LICENSE](LICENSE)（Apache-2.0）
