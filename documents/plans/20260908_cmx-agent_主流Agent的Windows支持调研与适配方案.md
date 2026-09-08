# 主流 Agent 的 Windows 支持调研与 cmx-agent 适配方案

> 日期：2026-09-08 ｜ 模块：`backend/cmx-agent` ｜ 状态：**P0 + P1 + P1.5 已实施**（同日；含增补的 set_policy 前门命令与 UI 接线；P2 绑 M3 未动。验证：`cargo test --offline` 207 全绿、新增代码 clippy 0 告警、CLI 冒烟确认探测链生效）
> 缘起：在 Windows 上实测 cmx-agent 时，bash 工具报 `{"ok":false,"error":"启动 sh 失败: program not found"}`。根因是工具硬编码 `sh -c`，而 Windows 持久 PATH（本机实测只有 `D:\Git`、`D:\Git\cmd`）不含 Git 的 `usr\bin`（sh.exe 所在）。本方案调研主流编码智能体如何支持 Windows，据此给 cmx-agent 定适配路线。
> 调研方式：4 路并行调研（源码核对 + 官方文档 + issue/讨论），关键事实均带出处；标注【已确认】/【推断】。

---

## 0. TL;DR

1. **业界没有人硬编码 `sh`**。各家都有"shell 探测/抽象层"：Codex 默认 PowerShell（兜底 cmd），Claude Code 装了 Git for Windows 就用 Git Bash、没装自动落 PowerShell 工具，OpenCode 是 pwsh > powershell > Git Bash > cmd 探测链，Goose 默认 cmd 可用环境变量换，Crush 干脆内嵌了一个纯 Go 的 POSIX shell 解释器（零依赖）。
2. **命令语义适配一律靠模型，不靠工具层翻译**。各家只做三件事：把"当前是什么 shell / 什么平台"告诉模型（工具描述注入）、给 PowerShell 注入 UTF-8 输出编码前缀、做路径规范。没有一家做 bash→PowerShell 命令转换器。
3. **Windows 原生沙箱只有 OpenAI Codex 做成了**（专用低权账户 + WFP 防火墙 + 受限令牌，Apache-2.0 开源）；Gemini CLI 有实验性 icacls 低完整性方案；Claude Code / OpenCode / Goose / Aider / IDE 系全部没有，靠审批门兜底——cmx-agent 现有的"人在环审批"路线与业界主流一致。
4. **cmx-agent 走"探测链 + 平台信号注入"路线**（P0，约半天工作量）：`CMX_AGENT_SHELL > pwsh > powershell > sh（git.exe 反推 usr\bin）> cmd` 五级探测，每 shell 一套 argv 模板 + UTF-8 前缀 + `-NoProfile -NonInteractive`，并把"当前 shell 与平台"写进工具描述让模型自己适配。**已拍板**：工具改名 `shell`（不留别名）、pwsh 优先、路径桥接只做提示层、Job Object 提前到 P1 之后（工程正确性，非安全功能）；受限令牌沙箱绑 M3。

---

## 1. 背景与问题（cmx-agent 现状）

cmx-agent 的子进程执行器 `crates/cmx-agent-tools/src/proc.rs` 与 `bash.rs`：

- bash 工具硬编码 `proc::run("sh", ["-c", cmd], cwd, timeout)`；`run_tests.rs` 的自定义命令路径同样硬编码 `sh`。
- `proc::run` 本身设计不差：cwd 锁工作区、超时钳制 1–120s、输出 64KB 截断、并发读防死锁、**永不 Err**（错误编码进 JSON 回灌模型自愈）。问题只出在 `sh` 的解析——`Command::new("sh")` 在 Windows 上按 PATH 找 `sh.exe`，找不到就是 "program not found"。
- Git Bash 会话会临时把 `/usr/bin` 加进 PATH（所以从 Git Bash 里起服务就能用），但**持久 PATH（注册表机器级）只有 `D:\Git`、`D:\Git\cmd`**——从 launcher / cmd / 双击启动的进程继承的 PATH 里没有 sh。本机已实测确认。
- 沙箱现状为 E1 应用层围栏（cwd 限定 + 路径检查 + 守卫审批），OS 级隔离排在 E2（bash.rs 头注释）。

也就是说：cmx-agent 缺的正是所有主流产品都有的一块——**shell 抽象层**。

## 2. 调研总表（2026-09-08 基准）

| 产品 | Windows 默认 shell | 探测/配置方式 | Unix 语义怎么处理 | Windows 沙箱 | Windows 前置依赖 |
| --- | --- | --- | --- | --- | --- |
| **OpenAI Codex CLI**（Rust） | **PowerShell**（pwsh > powershell），兜底 cmd.exe | 硬编码平台分支，不读 SHELL/COMSPEC；模型可在调用时指定 shell（含 bash.exe） | 靠模型：工具描述注入 Windows 安全规则 + 平台信号；工具层只做 PowerShell 解析、UTF-8 前缀、apply_patch 解包 | ✅ 最完善：elevated（专用账户+WFP 防火墙）/ unelevated（受限令牌+ACL）双方案 | 仅 PowerShell（7+ 或自带 5.1）；不需要 Git/WSL |
| **Claude Code** | 装了 Git for Windows → **Git Bash**；没装 → **PowerShell 工具**（v2.1.120 起软依赖） | 自动探测 Git Bash；`CLAUDE_CODE_GIT_BASH_PATH` 可指定；v2.1.84 起有独立 PowerShell 工具（opt-in→默认化中） | Bash 工具=真 bash 语义；PowerShell 工具独立权限规则 `PowerShell(...)` | ❌ 官方明说 "Native Windows is not supported"，要沙箱去 WSL2（bubblewrap） | Git for Windows 推荐非必需；Windows 10 1809+ |
| **OpenCode**（原 sst，现 anomalyco） | **pwsh > powershell > Git Bash > COMSPEC(cmd)** 探测链 | 配置文件 `shell` 键（路径/短名）> `$SHELL` > 平台回落；`OPENCODE_GIT_BASH_PATH` | 配了 POSIX shell 时用 `cygpath -w` 桥接路径；权限询问用 tree-sitter 同时解析 bash+PS 语法 | ❌ 无（仅审批/超时/截断）；官方推荐 WSL | 原生零 shell 依赖（默认 pwsh 路径） |
| **Crush**（charmbracelet，已转 Go） | **不用系统 shell**：内嵌 mvdan.cc/sh/v3 POSIX 解释器，进程内执行 | 无 shell 配置项；`CRUSH_CORE_UTILS` 开关内建 coreutils | 完整 POSIX 模拟；Windows 默认启用 Go 版 coreutils + 内建 gojq；shebang 探测分发 | ❌ 无（`isolateProcess` 在 Windows 是空函数） | 无 shell 依赖（自带解释器） |
| **Goose**（原 block，现 aaif-goose） | **cmd**（可用 `GOOSE_SHELL` 换 pwsh/bash） | 环境变量 `GOOSE_SHELL`；按可执行名自动配 flags；多行命令在 cmd 下直接拒绝 | 不模拟：Unix 靠系统 bash/sh（刻意不读 `$SHELL`，注释说明因 LLM 输出是 POSIX 模式）；Windows 默认 cmd | ❌ 无（v1.25.0 连 macOS seatbelt 都移除了，靠 GOOSE_MODE 审批） | Git Bash（推荐）/MSYS2/PowerShell 三选一 |
| **Gemini CLI** | **PowerShell**（pwsh 优先，注释写明 5.1 会剥引号、PSReadLine 拦输入） | 硬编码；沙箱严格模式强制 cmd；无用户可配置入口（issue 长期未决） | 靠模型 | ⚠️ 实验性 `windows-native`：icacls 低完整性标签（副作用：文件 Low 标签永久残留） | PowerShell；Docker 沙箱需 Docker Desktop |
| **Aider**（Python） | **cmd**（`subprocess shell=True`）；父进程是 powershell 才包 `powershell -Command` | 无配置，跟父 shell 走 | 不处理（文件修改不走 shell，LLM 只产 diff；/run 显式人工触发） | ❌ 无（纯人工审批制） | 无 |
| **IDE 系**（Cline/Roo/Cursor/Windsurf） | **跟随 VS Code/IDE 终端 profile**，Windows 默认 PowerShell | 终端 profile；Cline 另有 Background Exec 子进程模式；Roo inline 模式实为 cmd | 靠模型（社区流行把默认终端改 Git Bash/WSL 求 bash 语义） | ❌ 无 | 无 |

**来源**：Codex 源码 `codex-rs/shell-command/src/shell_detect.rs`、`core/src/shell.rs` 等 + [官方 Windows 文档](https://developers.openai.com/codex/windows) + [沙箱工程博客](https://openai.com/index/building-codex-windows-sandbox/)；Claude Code [官方 setup/tools-reference/sandboxing](https://code.claude.com/docs/en/setup) + 官方 CHANGELOG.md（v1.0.51 原生支持、v2.1.120 去 Git 硬依赖等逐条核对）；OpenCode `packages/core/src/shell.ts` + [配置文档](https://opencode.ai/docs/config/)；Crush `internal/shell/shell.go` + [bash 工具文档](https://mintlify.wiki/charmbracelet/crush/tools/bash.md)；Goose `crates/goose/src/agents/platform_extensions/developer/shell.rs` + [v1.25.0 博文](https://github.com/aaif-goose/goose/blob/main/documentation/blog/2026-02-23-goose-v1-25-0/index.md)；Gemini CLI `packages/core/src/utils/shell-utils.ts` + [沙箱文档](https://geminicli.com/docs/cli/sandbox/)；Aider `aider/run_cmd.py`。

## 3. 流派分析：四条路线

### 3.1 Git Bash 软依赖派（Claude Code、Copilot CLI、Cursor 社区实践）

**逻辑**：模型训练语料以 POSIX/bash 为主，`&&`、管道、heredoc、`$VAR` 语义跨平台一致，failed turns 最少。Git for Windows 开发机几乎必装，把它当"可选加速器"：装了就用真 bash，没装自动降级 PowerShell 工具。

**教训**（Claude Code 的坑，均出自官方 issue/changelog）：
- PATH 里同时有 Git Bash 和 `C:\Windows\System32\bash.exe`（WSL 启动器）时曾误选 WSL 启动器静默失败（[#26505](https://github.com/anthropics/claude-code/issues/26505)）→ **指定 bash 路径时必须校验文件名**（新版校验必须是 bash.exe/sh.exe）。
- login shell 快照 + 函数恢复机制在 Windows 上让每条命令慢数秒（社区实测）→ 别照抄"环境快照"这套。
- 每次执行弹黑色控制台窗口（[#28138](https://github.com/anthropics/claude-code/issues/28138)）→ 桌面壳场景必须 `CREATE_NO_WINDOW`。

### 3.2 原生 PowerShell 派（Codex、Gemini CLI、IDE 系跟随）

**逻辑**：零外部依赖、开箱即用；命令跑在用户真实 shell 语义里；与 Windows 原生沙箱（账户/令牌级）天然配套。Codex 是这派的完成态：pwsh > powershell > cmd 三级探测、每 shell 一套 argv 模板（PS 用 `-Command`、cmd 用 `/c`）、PowerShell 命令前注入 UTF-8 输出编码、Windows 工具描述追加安全规则（禁跨 shell 组合破坏性操作、递归删除前校验绝对路径在工区内、`Start-Process` 必须 `-WindowStyle Hidden`）。

**教训**：PowerShell 5.1 的坑要主动规避（`&&` 不支持、`>` 写出 UTF-16LE 文件、参数剥引号、PSReadLine 拦 ConPTY）——优先探测 pwsh 7，PS 一律 `-NoProfile -NonInteractive`。

### 3.3 内嵌解释器派（Crush 独此一家）

**逻辑**：不依赖系统任何 shell，进程内跑 POSIX 解释器（mvdan/sh），Windows 默认启用 Go 版 coreutils，跨平台行为 100% 一致。

**评估**：体验最整齐，但代价是：外部真工具（node/cargo/npm）照旧要 fork，解释器只统一了语法层；且 Rust 生态没有 mvdan/sh 的等价物（nushell 嵌入过重），**cmx-agent 不可行，仅作认知参照**。

### 3.4 cmd 隐式派（Aider、Gemini 早期、Roo inline）

无一主动选择，全是"子进程库 shell=True 的默认残留"。cmd 语法贫瘠，对 LLM 的 bash 风格输出兼容最差。**只能当兜底，不能当目标**。

### 结论

头部 CLI 的收敛趋势：**"原生 PowerShell 为主 + Git Bash 为可选语义增强 + 探测链自动降级"**（Claude Code 与 Codex 事实上在互相趋同：一个从 Git Bash 出发加 PS 工具，一个从 PS 出发允许指定 bash）。这正是 cmx-agent 该走的路。

## 4. Windows 沙箱生态（供 E2 参考）

| 机制 | 说明 | 业界采用 |
| --- | --- | --- |
| **专用低权账户 + WFP 防火墙 + 受限令牌** | Codex elevated 方案：CodexSandboxOffline/Online 隐藏账户、WFP 出站阻断、CreateProcessAsUserW + ConPTY、DPAPI 存凭据、私有桌面 | Codex（生产级，Apache-2.0 开源，可借鉴 `windows-sandbox-rs`） |
| **受限令牌 + ACL**（unelevated） | 从当前用户派生 write-restricted token，cwd 设允许 ACL、`.git` 等设 deny ACL；网络阻断只能靠毒化环境变量（advisory） | Codex（轻量档） |
| **AppContainer** | UWP 能力隔离；OpenAI 评估后**否决**（约 25% 性能损失 + 须预先枚举全部工具，不适合开放式开发流） | Gemini CLI 实验性采用（icacls 低完整性标签，副作用 Low 标签永久残留） |
| **Windows Sandbox（VM）** | 一次性 VM，太重、Home 版不可用 | 无产品采用 |
| **Docker / WSL2** | 容器/VM 级，跨平台方案在 Windows 的落点 | Gemini CLI（docker）、Claude Code（官方让用户去 WSL2） |
| **Job Object** | 进程组限制 + kill-on-close（进程树清理） | Codex runner 内部使用【推断】 |

**其余全部产品（Claude Code / OpenCode / Crush / Goose / Aider / IDE 系）在 Windows 上没有 OS 级沙箱**，安全模型 = 审批门 + 黑名单 + 输出截断。cmx-agent 现有五层守卫 + `interactive_approval()`（X4 人在环）与业界主流同水位，不落后。

## 5. cmx-agent 适配方案

### 5.0 设计原则（与仓内既有约束对齐）

- 不破坏离线可测性（`--offline` 全绿是 M0 以来的红线）；
- 不破坏"永不 Err"的 proc::run 契约（错误继续编码进 JSON 回灌）；
- 守卫语义不变：bash 工具的 `GuardHints`（Conditional 审批 + workspace-write）原样保留，换 shell 不换护栏；
- 同核多壳：改动只在 `cmx-agent-tools`（核的 tools 层），Web 壳/Tauri 壳零改动。

### 5.1 P0：shell 探测链 + argv 模板（解 "启动 sh 失败"，约半天）

**新增 `proc::resolve_shell() -> ResolvedShell`**（结构体：可执行路径 + ShellKind 枚举），决策顺序：

```
1. 环境变量 CMX_AGENT_SHELL（绝对路径或短名；文件名校验白名单 sh/bash/pwsh/powershell/cmd，
   借鉴 Claude Code v2.1.219 的校验教训——任意路径直接用会被误配）
2. Windows：PATH 上探测 pwsh.exe → powershell.exe
3. sh.exe 探测：PATH 直查 → 由 PATH 上的 git.exe 反推同安装树 usr\bin\sh.exe
   （D:\Git\cmd\git.exe → D:\Git\usr\bin\sh.exe；本机已验证该推导成立）
4. PowerShell 兜底再找一次（ProgramFiles 硬编码位置）
5. 全部失败：cmd.exe（COMSPEC），并在工具结果里附加降级警告
非 Windows：维持 sh（PATH 语义）
```

**优先级已拍板（§7-Q2）**：pwsh 优先于 sh。理由：产品最终分发到无 Git for Windows 的企业桌面，`powershell.exe` 5.1 恒在 = 零依赖兜底；UTF-8 前缀 + `-NoProfile` 行为确定。开发者要 POSIX 语义设 `CMX_AGENT_SHELL` 指向 sh（对标 Claude Code 的 `CLAUDE_CODE_GIT_BASH_PATH` 定位）。远期可学 Codex 加"模型按调用指定 shell"参数，P0 不做。

**每 shell 一套 argv 模板**（照抄 Codex `derive_exec_args`）：

| ShellKind | argv |
| --- | --- |
| sh/bash | `[sh, -c, cmd]`（现状） |
| pwsh/powershell | `[pwsh, -NoProfile, -NonInteractive, -Command, <UTF-8 前缀 + cmd>]` |
| cmd | `[cmd, /C, cmd]`；多行命令直接返回可行动错误（Goose 同款处理） |

**UTF-8 前缀**（照抄 Codex `powershell.rs`，cmx 全中文场景必需）：

```
try { [Console]::OutputEncoding=[System.Text.Encoding]::UTF8 } catch {}\n
```

**平台信号注入**：bash 工具的 `ToolSpec.description` 在 Windows 构建下追加一句"当前 shell 是 X，输出 Windows 适用的命令语法"（Codex `windows_shell_guidance` 思路），并借机注入三条 Windows 安全规则（禁跨 shell 组合破坏性操作、递归删前校验路径在工区内、后台进程隐藏窗口）。**不做任何命令翻译。**

**工具名**：**已拍板（§7-Q1）：`bash` → `shell` 干净改名，不留别名。** 名字是给模型的信号（叫 bash 就会稳定输出 bash 语法，与 pwsh 底层错配）；当前无外部用户是改名成本最低的窗口；别名会让会话日志/协议双名并存，回放与统计混乱。改动点：工具注册、`run_tests` 等引用处、测试用例、前端工具卡按名渲染处、system 提示词引用——一次改完。

**验收**：`cargo test --offline` 新增用例——探测链单测（含 git.exe 反推路径）、argv 模板单测、cmd 多行拒绝、PowerShell UTF-8 前缀拼装；clippy 零告警。

### 5.2 P1：桌面壳体验补丁（与 P0 同批或紧随，约半天）

1. **CREATE_NO_WINDOW**：`proc::run` 在 Windows 上加 `creation_flags(CREATE_NO_WINDOW)`。Tauri 壳是 windows 子系统，现在子进程每次执行都会闪黑窗（Claude Code #28138 同款病）；Web 壳是 console 子系统不受影响，加了也无害。
2. **run_tests 自定义命令接入同一 resolve_shell**（它现在也硬编码 sh）。
3. **错误信息可行动化**：探测全失败时返回"未找到可用 shell：请安装 Git for Windows，或设 CMX_AGENT_SHELL 指向 sh.exe/pwsh.exe"——比现在的 "program not found" 对模型和用户都可行动。
4. **路径桥接**：**已拍板（§7-Q3）：只做提示层，不做 cygpath 机械桥接**——工具描述写明"路径用 Windows 原生写法（`C:\...`）"，让模型自己适配（与业界"语义适配靠模型"共识一致）。机械桥接不做的理由：pwsh 优先后触发场景只剩"显式配 sh 的开发机"，很窄；cygpath 每参数多 exec 一次且有注入面。上线后踩坑多再评估。

### 5.3 P1.5：Job Object（已拍板提前，不绑 M3）

**提前理由**（§7-Q4）：这不是安全功能，是工程正确性修复——`proc::run` 超时走 `child.start_kill()`，只杀直接子进程；`sh -c <命令>` 里的真命令是孙进程，超时后被孤儿化留在系统里占端口、锁文件（今天 sh 模式下就存在，pwsh 模式同理）。Job Object 的 kill-on-close 把整棵进程树一并收尸：纯 Rust `windows` crate 实现、无需任何权限、约半天工作量，**排在 P1 之后立刻做**，附带进程级资源上限能力（为 E2 铺路）。

### 5.4 P2：E2 沙箱（绑 M3，与 data-auth 接地同批）

- **受限令牌 + ACL**（Codex unelevated 同款）：write-restricted token、工作区允许 ACL、`.git` deny ACL、网络毒化环境变量。需要 unsafe WinAPI，工程量约一周级。
- **专用账户 + WFP 防火墙**（Codex elevated）不作为目标——需要管理员 setup，企业桌面分发成本高；cmx-agent 有 cmx-data-auth 接地（U13）做数据面防线，命令面靠审批门 + 受限令牌已达到业界主流水位。

### 5.5 不做的事

- ❌ bash→PowerShell 命令转换器（无一家做，成本高且必错）；
- ❌ 内嵌 POSIX 解释器（Rust 无可用等价物，Crush 路线不可复制）；
- ❌ login shell / 环境快照机制（Claude Code 在 Windows 上的性能教训）；
- ❌ 强制要求安装 Git Bash（Claude Code 已把它从硬依赖降级，业界趋势是软依赖）。

## 6. 附录：时间线与迁移备注

- **Codex**：2025-04 要求 WSL2 → 2025-11 原生受限令牌实验（[#6065](https://github.com/openai/codex/discussions/6065)）→ 2026-08-26 elevated 沙箱正式官宣（[工程博客](https://openai.com/index/building-codex-windows-sandbox/)）；当前 npm 0.153.4 仅要求 PowerShell。
- **Claude Code**：2025-07-11 v1.0.51 原生 Windows（要求 Git for Windows）→ 2026-03 v2.1.84 PowerShell 工具预览 → 2026-04-24 v2.1.120 Git for Windows 降为可选 → 2026-05 Bedrock/Vertex 默认 PowerShell 工具。
- **仓库迁移备注**：opencode 已从 `sst/opencode` 更名 `anomalyco/opencode`；goose 已从 `block/goose` 迁至 `aaif-goose/goose`；crush 已从 Rust 重写为 Go。引用时以本表为准。
- **Gemini CLI 文档陷阱**：其工具文档至今仍写 "cmd.exe /c"，与源码（PowerShell）不符，为过期文案——引用需以源码为准。

## 7. 决策记录（2026-09-08 已全部拍板）

| # | 问题 | 决策 | 要点 |
| --- | --- | --- | --- |
| 1 | 工具是否改名 `bash`→`shell` | ✅ 改，**不留别名** | 名字是给模型的信号（叫 bash 就输出 bash 语法，与 pwsh 底层错配）；无外部用户期是改名成本最低窗口；别名会让日志/协议双名并存。改动点：工具注册、测试、前端工具卡渲染、system 提示词引用，一次改完 |
| 2 | 探测链 sh 与 pwsh 谁优先 | ✅ **pwsh 优先** | 产品分发到无 Git for Windows 的企业桌面，`powershell.exe` 5.1 恒在 = 零依赖兜底；UTF-8 前缀 + `-NoProfile` 行为确定。POSIX 需求走 `CMX_AGENT_SHELL`（对标 `CLAUDE_CODE_GIT_BASH_PATH`）。用户画像对齐 Codex 而非 Claude Code。远期可加"模型按调用指定 shell" |
| 3 | 路径桥接做不做 | ✅ **只做提示层** | 工具描述写明"路径用 Windows 原生写法 `C:\...`"，模型自己适配；cygpath 机械桥接不做（pwsh 优先后触发场景窄、每参数多一次 exec、有注入面）。踩坑多再评估 |
| 4 | E2 时间点 | ✋ **拆开** | Job Object 提前到 P1 之后（工程正确性：进程树收尸，非安全功能，无需权限）；受限令牌 + ACL 绑 M3（与 cmx-data-auth 接地同批，数据面 + 命令面一起收口） |

**实施顺序**：P0（shell 探测链 + 改名）→ P1（桌面壳体验补丁）→ P1.5（Job Object）→ P2（受限令牌，绑 M3）。

**实施记录（2026-09-08，P0/P1/P1.5 已落地，未提交）**：
- `tools/src/proc.rs`：`resolve_shell`/`shell_argv`/`run_cmd` + UTF-8 前缀 + cmd 多行拒绝 + CREATE_NO_WINDOW + lossy 解码 + Job Object 挂载；`tools/src/job.rs` 新增（windows-sys 0.59，离线缓存命中）。
- `tools/src/bash.rs` → `shell.rs` 改名（工具名/结构体/描述平台信号），system 提示词、审批夹具、前端工具卡（web + tauri 两份 ui）同步。
- `core/src/agent.rs`：`Policy` 换 `RwLock`（`Agent::set_policy`），`ApprovalPolicy` 补 serde；`app` 层 + 协议新增 `set_policy` 命令；UI 🛡 下拉接线（原占位控件）。
- 验证：`cargo test --offline` 207 全绿（含进程树收尸、探测链、set_policy 协议负例）；新增代码 clippy 0 告警（仓内存量约 25 条在本次未触碰文件，遗留待另行清理）；CLI 冒烟：本机解析到 PowerShell 7 `pwsh.exe`。
- 实施时另发现并处理：PowerShell 5.1 `Set-Content` 默认 UTF-16、`tasklist` 子串误报两处测试陷阱（已在用例中规避）。

**第二轮实施记录（2026-09-08 同日"一步改到位"，未提交）**：
- **掐流自愈补全**（`model/openai.rs`）：`read_sse_once` 硬错不再经 `?` 直接抛出——已收 finish_reason 则采纳已收内容、否则 `on_stream_reset` 后整轮重试；重试耗尽回报最后一次真实流错误。带本地假流服务器回归测试 ×2（断流重试成功 / 已完成断流采纳）。
- **PptxWriteTool**（`office/pptx.rs` + `tool.rs`）：纯 Rust 组包（zip + PresentationML 最小合规集：presentation/slide×N/slideMaster/slideLayout/theme），每页=标题+要点列表；注册进 `DesktopAppBuilder`，system 提示词补"办公"行；结构化测试（条目齐全/页数/转义/负例）。
- **set_policy 持久化**：UI 🛡 选择记 localStorage、启动恢复（web + tauri 两份）。
- **clippy 存量清零**：`--fix` 自动修复 + 3 处手修（chart.rs 同块合并、openai.rs let-else→`?`、loop→while-let），全仓 `--all-targets` **0 告警**（含历史存量）。
- **文档更新**：README/AGENTS.md 同步真实状态（13 crate、211 测试、shell 改名、Windows 支持要点、两旋钮运行时切换约束）。
- 验证：`cargo test --offline` **211 全过**；clippy **0 告警**；CLI 冒烟正常（本机解析 pwsh）。
- 明确不做：P2 受限令牌（绑 M3）、git 提交（等指令）、Tauri 重打包（用户侧）。

---

### 附：本方案引用的主要来源

- Codex：[codex-rs 源码](https://github.com/openai/codex/tree/main/codex-rs)（shell_detect.rs / shell.rs / powershell.rs / windows-sandbox-rs）· [Windows 文档](https://developers.openai.com/codex/windows) · [配置参考](https://developers.openai.com/codex/config-reference) · [Windows 沙箱工程博客](https://openai.com/index/building-codex-windows-sandbox/) · [#6065](https://github.com/openai/codex/discussions/6065)
- Claude Code：[setup](https://code.claude.com/docs/en/setup) · [tools-reference](https://code.claude.com/docs/en/tools-reference) · [sandboxing](https://code.claude.com/docs/en/sandboxing) · 官方 CHANGELOG.md · [#26505](https://github.com/anthropics/claude-code/issues/26505) · [#28138](https://github.com/anthropics/claude-code/issues/28138)
- OpenCode：[shell.ts 源码](https://github.com/anomalyco/opencode/blob/dev/packages/core/src/shell.ts) · [配置文档](https://opencode.ai/docs/config/) · [windows-wsl](https://opencode.ai/docs/windows-wsl)
- Crush：[shell.go 源码](https://github.com/charmbracelet/crush) · [bash 工具文档](https://mintlify.wiki/charmbracelet/crush/tools/bash.md)
- Goose：[shell.rs 源码](https://github.com/aaif-goose/goose/blob/main/crates/goose/src/agents/platform_extensions/developer/shell.rs) · [v1.25.0 博文](https://github.com/aaif-goose/goose/blob/main/documentation/blog/2026-02-23-goose-v1-25-0/index.md)
- Gemini CLI：[shell-utils.ts 源码](https://github.com/google-gemini/gemini-cli) · [沙箱文档](https://geminicli.com/docs/cli/sandbox/) · [#3126](https://github.com/google-gemini/gemini-cli/issues/3126) · [#21340](https://github.com/google-gemini/gemini-cli/issues/21340) · [AppContainer PoC 提案](https://github.com/google-gemini/gemini-cli/discussions/20868)
- Aider：[run_cmd.py 源码](https://github.com/Aider-AI/aider) · [HISTORY](https://aider.chat/HISTORY.html)
- IDE 系：[Cline 文档](https://docs.cline.bot/tools-reference/all-cline-tools) · [#9859](https://github.com/cline/cline/issues/9859) · [Roo shell-integration](https://roocodeinc.github.io/Roo-Code/features/shell-integration/) · [#9933](https://github.com/RooCodeInc/Roo-Code/issues/9933)
