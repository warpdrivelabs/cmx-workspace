# Codex 开源 harness 全面了解

> 调研日期:2026-08-26
> 对象:OpenAI 开源编码 agent —— [github.com/openai/codex](https://github.com/openai/codex)(Apache-2.0)
> 规模:≈67K stars / 9K forks / 400+ contributors;核心团队 4–5 人,每天 10–15 次提交(战略产品级投入)

---

## 一、用什么语言开发

**结论:现在是 Rust(≈95.7%),从 TypeScript / Node 完整重写而来。**

| 阶段 | 时间 | 技术栈 |
|---|---|---|
| 首发 | 2025-04-16 | React + TypeScript + Node.js(为快速迭代) |
| 宣布重写 | 2025-06 | Codex co-lead Fouad Matin 在 GitHub Discussion #1174 宣布 "going native" |
| 现状 | 2026 | 引擎全在 `codex-rs/`(Rust);`codex-cli/`(TS)只剩薄壳 |

### 重写的三条硬理由
1. **零依赖安装** —— Node v22+ 是硬依赖,企业 / air-gapped 环境打包困难,需要 bundle Node 或 shim 层。
2. **无 GC 停顿** —— 长时运行的 agent 进程会累积 history / 工具结果 / 渲染 diff,TS 运行时堆不断膨胀,GC 停顿与延迟、内存预算冲突。
3. **原生沙箱** —— 想直接调平台内核级安全 API,而非应用层 hook。

### 现在的 TS 残留
- `codex-cli/` = Node.js wrapper:`npm i -g @openai/codex` 时下载 Rust 二进制。
- TypeScript SDK 仍在(供 TS 侧扩展)。

> 备注:这条「Node/TS 起步 → Rust 重写(纯库、全对等、拥抱 crate)」的路径,与本项目 `cmx-spreadsheet` 中 `cmx-megasheet`(TS)→ `cmx-rust-sheet`(Rust 移植)的动机高度一致。

---

## 二、架构(Cargo workspace ≈70 crates)

分层原则:**用户入口 → 共享核心引擎 → 平台 / 协议层**。

| crate | 职责 |
|---|---|
| `codex-core` | 可复用库(OpenAI 拟发布供他人嵌入 Rust 应用):`ThreadManager` / `CodexThread` / `Session`,负责回合交互、上下文压缩(compaction)、工具分派 |
| `codex-tui` | 全屏交互式终端 UI(Ratatui 框架) |
| `codex-rs/cli` | 产出 `codex` 二进制 |
| `codex-rs/tui` | 产出 `codex-tui` 二进制 |
| 沙箱 / 协议层 | bubblewrap 沙箱、规则化 exec policy、两阶段持久记忆管线、JSON-RPC app-server 接口 |

### 沙箱是架构核心卖点(内核级,非应用层 hook)
- **macOS**:Apple Seatbelt
- **Linux**:Landlock / seccomp + bubblewrap(namespace 隔离 + seccomp filter + 规则化 exec policy)
- 号称是唯一在**内核级**强制安全的主流编码 agent。

### 扩展面
- **JSON-RPC app-server 接口** —— wire protocol 让 TypeScript、Python 等其他语言扩展 agent。

---

## 三、前端情况

**纯终端 TUI —— 没有 Web UI、Electron 或浏览器组件。**

| 维度 | 细节 |
|---|---|
| UI 框架 | **Ratatui**(Rust TUI 库,前身 tui-rs) |
| 终端后端 | **crossterm**(开 `bracketed-paste` + `event-stream` feature) |
| 渲染模型 | immediate-mode:每帧从头重绘所有可见 widget(中间 buffer)→ 亚毫秒响应、无陈旧状态 |
| 约定色 | cyan=用户提示 · green=成功 · red=错误 · magenta=Codex 品牌元素 |
| ratatui feature | `scrolling-regions` / `unstable-backend-writer` / `unstable-rendered-line-info` / `unstable-widget-ref` |
| 无头模式 | `codex exec`(带 `--json`)—— 非交互 runner,脚本 / CI 集成入口 |

### 生态信号
- **Ratatui 已加入 OpenAI 的 Codex Fund**,为 Rust 终端 UI 生态注入资源。

---

## 四、怎么才能用好

### 核心心智模型:两个正交旋钮,别只拧一个

Codex 把「能力」与「许可」拆成两个独立设置:

| 旋钮 | 含义 |
|---|---|
| `sandbox_mode` | **能做什么** —— 能否读 / 写目录、可访问哪些文件 |
| `approval_policy` | **何时问你** —— 什么时候请求你批准执行命令 |

- **最常见新手错误**:为免打扰把 `approval_policy="never"`,却留着 `sandbox_mode="read-only"` → 结果什么都改不了。**两个都要设。**
- **日常推荐**:`sandbox_mode="workspace-write"` + `approval_policy="on-request"`,唠叨停止且能干活。
- **绝对避免**:`approval_policy="never"` + `sandbox_mode="danger-full-access"`(即 `--yolo`)—— 无安全网,模型能 `rm -rf $HOME`。需要自动化就用 `codex exec` + 显式最小权限。

### config.toml(`~/.codex/config.toml`)

- 命名是 snake_case:`mcp_servers`(不是 `mcpServers`)。
- 已有 **150+ 键**,多数人只改 5 个。两个默认值强烈建议覆盖:
  - `shell_environment_policy.inherit="all"`(默认)会把**全部环境变量泄露给每次工具调用** → 5 行配置堵住,规避巨大审计风险。
  - `startup_timeout_sec` 默认 10 —— 慢的(Node lazy-load)MCP server 注册失败还被静默丢弃 → 调到 30。

### Profiles(整套配置一键切换)

- 激活总是显式:`--profile dev` 或 `CODEX_PROFILE=dev`。
- 最耐用命名按**环境**而非人 / 项目:`dev` / `ci` / `prod`(+ 可选 `agent`)。
- 典型:高推理模型、快速模型、零数据保留模型各占一个 profile,差一个 `--profile` 标志。

### AGENTS.md(= Codex 版 CLAUDE.md)

- 任务前加载的项目指令;沿目录树 **root→leaf 层级合并**,越靠近工作目录优先级越高;上限 `project_doc_max_bytes`(默认 32 KiB)。
- 全局放 `~/.codex/AGENTS.md`;窄目录要覆盖用 `AGENTS.override.md`。
- 内容:构建 / 测试命令、架构约束、包管理规则、安全边界。
- **治「把简单改动过度工程化」最好的药**;Codex 同一错误犯两次时,让它写 retrospective 并更新 AGENTS.md,保持活文档。

### MCP(第一类扩展面,与 Claude Code 同协议 → 生态可移植)

- `[mcp_servers.NAME]` 声明:
  - STDIO server:`command` / `args` / `env`
  - HTTP server:`url` + `bearer_token_env_var`
- **成本提醒**:每个 MCP server 都把工具定义塞进**每一次** API 调用 → 费用异常时先看挂了几个。

### 自动化 / 团队

- **CI**:`codex exec --json` 无头运行 + 收紧 autonomy + 一份紧凑 AGENTS.md;难任务 `--profile deep`,杂活 `--profile fast`。
- **组织级**:`requirements.toml`(admin enforcement)可跨组织约束 approval policy、sandbox mode、MCP allowlist。
- **不可信仓库**:先审 AGENTS.md / hooks / plugins / MCP 配置再信任。

### 快速起步清单

1. `sandbox_mode="workspace-write"` + `approval_policy="on-request"` 作日常默认
2. 写好带 build / test 命令与约定的 AGENTS.md
3. 定义环境名 profiles(`dev` / `ci` / `prod`)
4. 在 `[mcp_servers.NAME]` 声明 MCP server

> 注意:各版本键名演进快(参考指南覆盖到 v0.149.x),具体键请对照你所装版本的官方 config 参考。

---

## 附:与本项目的可能结合点

- `codex exec --json` 无头模式可接入 cmx 微服务的测试 / CI 流水线(类比现有 `e2e-consol-*.sh` 的自动化断言)。
- JSON-RPC app-server 协议可作为「让其他语言扩展 agent」的参考范式。
- Ratatui immediate-mode 渲染思路,与终端类工具的 UI 设计有借鉴价值。

---

## 参考来源

- [InfoQ — Codex CLI Goes Native (Rust rewrite)](https://www.infoq.com/news/2025/06/codex-cli-rust-native-rewrite/)
- [codex-rs Architecture 深度解析](https://codex.danielvaughan.com/2026/03/28/codex-rs-rust-rewrite-architecture/)
- [Zylos Research — Codex CLI Architecture & Multi-Runtime Patterns](https://zylos.ai/research/2026-03-26-openai-codex-cli-architecture-multi-runtime-patterns/)
- [Botmonster — Rust-Powered Terminal Agent](https://botmonster.com/posts/openai-codex-cli-rust-powered-ai-agent/)
- [awesome-ratatui(TUI 生态)](https://github.com/ratatui/awesome-ratatui)
- [Ratatui joins OpenAI's Codex Fund](https://undercodetesting.com/ratatui-joins-openais-codex-fund-building-terminal-uis-with-rust/)
- [OpenAI 官方 — Codex Best Practices](https://developers.openai.com/codex/learn/best-practices)
- [Shipyard — Codex CLI Cheatsheet](https://shipyard.build/blog/codex-cli-cheat-sheet/)
- [Majestic Labs — config.toml Guide 2026](https://majesticlabs.dev/blog/202607/codex-cli-configuration-guide)
- [Codex CLI as an MCP Server(多 agent 工作流)](https://codex.danielvaughan.com/2026/04/24/codex-cli-mcp-server-multi-agent-workflows-agents-sdk/)
