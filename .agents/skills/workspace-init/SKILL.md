---
name: workspace-init
description: 初始化 CMX 工作区子仓。当用户刚克隆 cmx-workspace 根仓后要求"初始化工程""初始化工作区""初始化workspace""拉取全部子仓""下载所有子仓库""克隆子仓""同步子仓""init workspace""setup workspace"，或询问"怎么把 backend/frontend 下的仓库拉下来""工作区还缺哪些子仓"时必用。执行本技能 scripts/init-workspace.sh 幂等克隆 backend/ 10 仓 + frontend/ 4 仓 + cmx-launcher 共 15 个子仓并校验汇总。
---

# workspace-init — 工作区子仓初始化

刚 clone 完 `cmx-workspace` 根仓时，`backend/`、`frontend/`、`cmx-launcher/` 都是空的（根仓不跟踪子仓内容），需按下述步骤把 15 个子仓拉到位。

## 执行步骤

1. 确认当前目录是工作区根（有 `AGENTS.md` + `scripts/`；不是则先 `cd` 到根）。
2. 跑脚本（**幂等**，已存在的仓自动跳过，失败可重跑；`bash` 前缀在 Git Bash / PowerShell / cmd 通用）：

   ```bash
   bash .agents/skills/workspace-init/scripts/init-workspace.sh
   ```

3. 看汇总行：`失败 0 · 冲突 0 / 共 15 仓` 即成功；有失败/冲突按"常见问题"处理。

## 参数

| 参数            | 作用                                                       |
| --------------- | ---------------------------------------------------------- |
| （无）          | 完整克隆缺失子仓（不浅克，保留全量历史），已存在跳过            |
| `--update`      | 已存在的仓顺带 `git pull --ff-only` 更新（日常同步全部子仓用这个） |
| `--dry-run`     | 只打印将执行的动作，不实际 clone / pull                       |

## 完成后的验证清单

- [ ] `backend/` 下 10 仓、`frontend/` 下 4 仓、`cmx-launcher/` 均存在且 `git rev-parse --show-toplevel` 指向自身
- [ ] 抽查 `git remote -v` 为 `https://gitee.com/warpdrivelabs/<repo>.git`
- [ ] 分支：除 `frontend/cmx-mega-sheet` 是 **master** 外，其余均为 main

## 初始化后的建议步骤（按需，不自动执行）

| 目标                     | 命令（工作区根）                                            |
| ------------------------ | ----------------------------------------------------------- |
| 前端开发                 | `cd frontend/cmx-enterprise-portal && npm install`（再 `npm run dev:portal`，:5173） |
| 后端编译检查             | `cd backend/cmx-portalservice && cargo check`（首次编译较久）   |
| 后端联调（最小服务集）   | **portal 与 model 须同起**：`cd backend/cmx-model && ./model.sh`（:8093 元数据中心）+ `cd backend/cmx-portalservice && ./portal.sh`（:8080 主应用）——model 承载字典 / 元数据，门户经 `[center_client.services]` 反代，**只起 portal 时页面数据不可用**；其余引擎（flow/report/rules/mdm/onto/dataauth）按需再起 |
| 一键控制台（启停全部服务） | `cd cmx-launcher && ./run.sh` → <http://127.0.0.1:8100>（Windows 用 `run.bat`，勾选 portal + model 启动即可满足常规联调） |

## 常见问题

- **部分仓 clone 失败（网络）**：直接重跑脚本，已克隆的自动跳过，只补缺的。
- **目录存在但不是 Git 仓（冲突）**：脚本不覆盖，需人工确认该目录内容后删除/改名再重跑。
- **https 访问 gitee 受限**：改用 SSH——把脚本顶部 `ORG` 换成 `git@gitee.com:warpdrivelabs`（需先配好公钥）。
- **只想看清单不执行**：`bash .agents/skills/workspace-init/scripts/init-workspace.sh --dry-run`。

## 清单维护（改这里！）

子仓清单**唯一真源**在本技能 `scripts/init-workspace.sh` 顶部的 `REPOS` 关联数组（路径 → 仓库名）。新增/下线子仓时：改脚本 → 同步 `AGENTS.md` §六仓库清单 → 全工作区 `git status -sb` 确认无跨仓污染。
