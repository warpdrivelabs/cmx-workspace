# cmx-agent 技能（Skills）与 MCP 支持方案

> 2026-09-20 · 对标调研 opencode / codex 技能与 MCP 机制后为 TrueMate（cmx-agent）设计。
> 状态：**方案待评审，未实施、未提交**。
> UI 参考：用户提供的两张设置页截图（「技能」「MCP 服务器」两个管理页：scope 下拉 + 计数 + 搜索 + 已安装列表 + 行卡开关/删除 + 刷新 + 新建）。
> 关联：`documents/plans/20260917_cmx-agent_图片粘贴多模态输入方案.md`（其中「图片解析 MCP」依赖本方案 remote MCP 能力）。

---

## 一、背景与目标

cmx-agent 的「技能」与 MCP 目前处于**地基已打、体验未收口**的状态：

- 技能：`SKILL.md` 扫描、斜杠菜单三分（命令/技能/子智能体）、系统提示词索引均已存在，但**没有管理界面**——用户只能手工建目录，看不到装了哪些技能、无法开关/删除/新建；
- MCP：stdio 客户端与 `mcp.json` 配置已存在，但**只支持本地子进程**（不能接 apifox 这类 remote http MCP）、**没有 enabled 开关与连接状态**、**没有管理界面**，配置只能手编 JSON。

目标：**参照 opencode 的机制 + 用户截图的设置页形态**，把技能与 MCP 做成设置中心两个正式分区——可看、可开关、可增删、可测连接、状态实时可见；同时补齐 remote MCP 与技能多目录（工作空间级）两个能力缺口。

---

## 二、业界调研

### 2.1 技能体系（opencode 主对标，codex 对照）

| 环节 | opencode | codex |
| --- | --- | --- |
| 发现目录 | 用户级 `~/.claude/skills`、`~/.agents/skills`；项目级从当前目录向上扫 `.claude`/`.agents`；自有 `.opencode/{skill,skills}/**/SKILL.md`；外加配置 `skills.paths` 与远程 `skills.urls` | User/Repo/System/Admin 四级技能根，系统技能从二进制 `include_dir!` 安装到 `$CODEX_HOME/skills/.system` |
| frontmatter | 仅 `name`（必填）+ `description`（可选）；解析失败发错误事件跳过该文件 | `name`/`description`/`metadata.short-description`，带非法 YAML 容错修复 |
| 加载时机 | 首次访问按目录惰性扫描并**全文进内存缓存** | 目录常驻，**正文不缓存**、选中时现场读文件 |
| 注入模型 | 系统提示词常驻 `<available_skills>` **索引**（name+description+location）；模型按需调内置 `skill` 工具注入**全文**（`<skill_content>` + 基准目录 + ripgrep 抽样同目录 10 个文件），加载走权限 ask 且 `always` 记忆 | developer 消息常驻目录 + 触发规则（`$技能名` 点名或描述匹配即必须用）；选中后以 user 消息注入全文 |
| 防膨胀 | 无工具体量限制 | **spec 字节预算**：单工具 8KB、总量 64KB，超预算降为隐藏 |
| slash 菜单 | `Command.list` 统一合并 内置命令 → markdown 命令 → **MCP prompts** → **skills**；TUI 刻意**排除 skill**（技能靠系统提示词触发，不占斜杠位），web 端则全量展示 | TUI `/skills` 弹 fuzzy 选择器 |
| 安装分发 | `skills.urls` 指向远程 `index.json`（`{skills:[{name,files,version}]}`），staging 目录 + 原子 rename 升级——marketplace 雏形 | plugin 体系（`PluginSkillRoot`） |

### 2.2 MCP 体系

**配置 schema（opencode `opencode.json` 的 `mcp` 字段，discriminator `type`）**：

```jsonc
{
  "mcp": {
    "apifox": { "type": "remote", "url": "https://api.apifox.com/mcp", "enabled": true, "headers": { "X-Project-Id": "123" }, "timeout": 30 },
    "local-fs": { "type": "local", "command": ["npx", "-y", "@xx/mcp-fs"], "cwd": "...", "environment": { "K": "V" }, "enabled": true }
  }
}
```

**客户端与生命周期（opencode）**：

- transport：stdio（子进程）/ StreamableHTTP（先试）/ SSE（回退）；remote 鉴权三层——静态 `headers`、OAuth（SDK provider，token 持久化 `mcp-auth.json` 0600 + 文件锁）、区分 `needs_auth` 与 `needs_client_registration` 两种失败态；
- 生命周期：`enabled === false` 连接前短路；连接超时默认 30s；工具调用 `resetTimeoutOnProgress`；**无自动重连**——`onclose` 把状态置 `failed` 并广播 `mcp.tools.changed`；`ToolListChangedNotification` 到达时重新拉工具；提供手动 `connect/disconnect` API；
- 状态枚举：`connected | disabled | failed{error} | needs_auth | needs_client_registration`；查询 `GET /mcp` 返回 `{name: Status}` map，配置里没启用的默认 `disabled`。

**工具并入与命名**：

- 命名：opencode = `sanitize(server)_sanitize(tool)`（单下划线）；codex = `server__tool` 命名空间。cmx-agent 现行 `mcp_{label}_{tool}` 与两者同构；
- 并入：MCP 工具包上权限（per-server permission key）后挂进工具注册表，注册表内置工具之后；任一 server 声明 `resources` 能力则额外注入 `list/read_mcp_resource` 三个内置工具；
- 错误回传：`isError` 结果转文本抛给会话工具错误管道（空文本兜底 "MCP tool returned an error"）；
- 治理：opencode 无工具数上限（分页上限 1000 页、输出截断、blob 10MB）；codex 有 per-tool `enabled_tools/disabled_tools` 双列表、`output_token_limit`、审批档位 `default_tools_approval_mode`。

**管理 UI / API（opencode web 端）**：

- `dialog-select-mcp`：列表 + 搜索 + 每项 Switch + 状态标签（i18n）+ 错误展示 + 「已启用/总数」计数；**无新建/删除 UI**（增删走 CLI `opencode mcp add`）；
- 开关是**按状态路由的动作**：`connected→disconnect`、`needs_auth→authenticate`、`disabled/failed→connect`，配置持久化另走 `PATCH /config`；
- HTTP 端点：`GET /mcp`（状态）、`POST /mcp`（add）、`POST /mcp/:name/connect|disconnect`、`/mcp/:name/auth*`（OAuth 四件）；前端靠 SSE 事件 invalidate 查询。

### 2.3 调研结论

| | opencode | codex | 取舍 |
| --- | --- | --- | --- |
| 技能注入 | 索引常驻 + 模型自主 `skill` 工具按需加载全文 | 目录常驻 + 点名/匹配即全文 user 注入 | **期一取 cmx-agent 现行**（索引常驻 + 斜杠选中注入全文，效果等价 codex）；**期二补 `skill` 工具**（模型自主加载，取 opencode） |
| 技能目录 | 多级（用户 + 项目向上扫） | 四级根 | 取两级：用户级数据根 + **当前工作空间 `.agents/skills/`**（与 CMX 工作区技能目录惯例天然一致） |
| 技能体量 | 无限制 | 8KB/64KB 预算 | 期二取 codex 预算 |
| MCP 配置 | map + discriminator `type` + enabled | 字段更全（per-tool 治理） | **取 opencode 形态**（够用），per-tool 治理列期二 |
| MCP transport | stdio + StreamableHTTP→SSE 回退 | stdio + streamable(重试/OAuth 刷新) | 全取（cmx-agent 现缺 remote） |
| 重连 | 无自动重连，手动 connect/disconnect | 有刷新命令 | 取 opencode（手动启停 + 状态可见），自动重连不做 |
| 开关语义 | 按状态路由（connected→断开） | enabled 是持久配置 | **两者都要**：`enabled` 持久化到配置，开关同时触发 connect/disconnect（对齐截图 toggle 直觉） |
| 状态上报 | GET + SSE 事件 invalidate | JSON-RPC 通知流 | 取：查询命令 + 复用现有 `/api/subscribe` 总线广播 |
| OAuth | SDK provider + token 0600 持久化 | OAuth 自动刷新 | 列期三（期一 remote 仅静态 headers，覆盖 apifox 类场景已够） |

---

## 三、cmx-agent 现状（资产盘点与差距）

### 3.1 已有资产（好消息：大半地基在）

| 环节 | 现状 | 证据 |
| --- | --- | --- |
| SKILL.md 体系 | `<数据根>/skills/<目录名>/SKILL.md`，frontmatter `name`/`description` 手写解析，`scan()` 扫子目录、非法/重名标 `invalid`，首启种示例 `meeting-notes` | `crates/cmx-agent-app/src/skills.rs:33-141` |
| 斜杠三分 | `list_slash()` 返回 commands（`/compact` `/plan`）/ skills / subagents；技能命中把 SKILL.md 全文包 `<skill-instruction>` 前缀注入本轮用户输入 | `crates/cmx-agent-app/src/app.rs:2319-2488` |
| 技能索引常驻 | `skills_prompt_section()` 把可用技能清单拼进 system prompt，每回合重建 | `app.rs:2366-2381,2986-2993` |
| MCP stdio 客户端 | `initialize`(2024-11-05)/`list_tools`/`call_tool`/`shutdown`；`McpTool` 实现内核 `Tool` trait | `crates/cmx-agent-mcp/src/client.rs`、`tool.rs:16-74` |
| MCP 配置 | `<data>/mcp.json` 数组 `[{label,command,args?,env?}]`，不存在 = opt-in；双壳接线点已有 | `tool.rs:90-112`、`cmx-agent-web/src/main.rs:96`、`cmx-agent-shell/src-tauri/src/main.rs:717-719` |
| 工具热注册 | `ToolRegistry::register_dyn`（拒同名遮蔽）/`unregister`；内核每步 `tools.specs()` 现取——**热插拔下一回合即对模型可见** | `cmx-agent-core/src/tool.rs:209-245`、`agent.rs:472` |
| 审批与守卫 | GuardPipeline 首个非 Allow 短路（fail-closed）；计划模式白名单**已拦 MCP 工具**；`InteractiveApprover` 300s | `cmx-agent-core/src/guard.rs`、`cmx-agent-app/src/approval.rs:37-217` |
| 插件 mcp 载体 | `cmx-plugin.json` kind:"mcp" 桥接 + 安装/启用时热连（市场分发形态） | `crates/cmx-agent-plugin/src/mcp.rs:18,47` |
| SSE 总线 | `SessionEventBus`（broadcast 1024）+ `GET /api/subscribe`，任何来源事件实时上屏 | `cmx-agent-app/src/bus.rs`、`cmx-agent-web/src/main.rs:322-354` |
| 设置中心 | 7 分区两栏（account/models/im/agents/appearance/general/about），`settings.js` 分区交互 + `agents.js` 分区可作样板 | `cmx-agent-web/ui/index.html:101-118` |
| 配置读写范式 | providers.json：load→内存改→临时文件+rename 原子写，`providers_lock` 串行化 | `cmx-agent-model/src/providers.rs:549-594`、`app.rs:105-112` |

### 3.2 差距清单

| # | 差距 | 影响 |
| --- | --- | --- |
| G1 | MCP 仅 stdio，**无 remote（http/sse）** | 接不了 apifox / 云端 MCP；截图中的 http 型服务器无法支持 |
| G2 | `mcp.json` 无 `enabled`、无连接状态、无热启停（进程随应用启动拉起，失败静默跳过） | 用户不知道哪个 server 挂了、为什么工具没出现 |
| G3 | MCP 无任何管理 UI | 配置靠手编 JSON |
| G4 | 技能只有用户级一个目录，**无工作空间级** | 打开 CMX 工作区（`.agents/skills/` 下 24 个技能）吃不到 |
| G5 | 技能无管理 UI（列表/开关/删除/新建） | 同 G3 |
| G6 | MCP 工具默认不审批（「显式配置即信任」） | 与红蓝审查口径偏宽，且不可调 |
| G7 | 旧 `list_skills`（=tools.specs()）与真技能撞名 | 概念混淆（子智能体编辑器里「技能」实为工具清单） |
| G8 | MCP server 崩溃无事件（静默失联） | 会话里工具凭空消失 |

---

## 四、方案设计

### 4.1 总体架构

```
配置层（数据根 %APPDATA%\pansoft\cmx-agent\data\）
  skills/                        技能真身（用户级，现有）
    <name>/SKILL.md
  mcp.json                       MCP 配置 v2（map + type + enabled，见 4.3）
  skills.json                    技能运行状态（enabled 开关，按 name）

<当前工作空间>/.agents/skills/    技能（空间级，只读发现 + 可管理开关）

运行层
  cmx-agent-mcp    stdio 客户端（现有）+ 新增 remote 客户端（StreamableHTTP→SSE 回退）
  cmx-agent-app    McpHub（连接编排/状态机/热启停）+ SkillsIndex（两级扫描）
  事件总线          mcp.status.changed / skills.changed 全局事件 → /api/subscribe → 设置页实时刷新

UI 层（设置中心新两分区，单份真源 cmx-agent-web/ui/）
  技能分区 / MCP 分区 —— 对齐截图：scope 下拉 + 计数 + 搜索 + 行卡（图标/状态点/副标题/toggle/删除）+ 刷新 + 新建
```

### 4.2 技能体系

**目录与 scope（G4）**：

- 用户级：`<数据根>/skills/**/SKILL.md`（现有，不变）；
- 空间级：`<当前工作空间>/.agents/skills/**/SKILL.md`——与 CMX 工作区、opencode/codex 的 `.agents/skills` 惯例对齐；空间未绑定或目录不存在时自然为空；
- 扫描归一：`SkillsIndex::scan()` 合并两级，同名时**空间级覆盖用户级**（项目定制优先），重名条目保留 `invalid` 标记不静默吞（沿用现行语义）。

**frontmatter**：维持 `name`（必填）+ `description`（可选）最小集不变，与 opencode 对齐；解析失败的条目照旧标 `invalid` 并在设置页可见（错误原因列出来，不弹打扰）。

**注入模型（维持现行，微调）**：

- 系统提示词索引段升级为 opencode 式三要素：`名称 + 描述 + 调用方式`（`/名称 参数`），description 缺失时以目录名兜底；空间级技能在索引里标注来源，提示词补一句「工作空间技能优先于同名用户技能」；
- 斜杠选中注入全文机制不变（`<skill-instruction name>` + 正文 + 基准目录尾注）。

**启用状态（skills.json）**：`{ "<name>": { "enabled": false } }`，缺省 enabled=true；被禁用技能**不进系统提示词索引、不进斜杠菜单**（三处过滤位置对齐 opencode：扫描后、注入前、菜单前）。读写走 providers.json 同款「load→改→原子写」范式。

**新建（对齐截图「+ 新建」）**：弹窗输入名称 + 描述 → 创建 `<数据根>/skills/<名称>/SKILL.md` 骨架（含 frontmatter 模板与使用说明注释）→ 打开该目录（复用 `open_workspace_folder` 命令模式）→ 广播 `skills.changed`。

**删除**：仅允许删用户级（空间级只读发现，行卡不显示删除按钮，副标题标「来自工作空间」）；删除前确认弹窗；删除 = 移除目录。

### 4.3 MCP 体系

**配置 schema v2（`mcp.json`）**——从数组升级为 map，读时兼容旧格式归一迁移（数组项 `{label,command,args,env}` → `{type:"local", enabled:true}`），写回一律新格式：

```jsonc
{
  "version": 2,
  "servers": {
    "apifox-new-mcp": {
      "type": "remote",                       // remote | local
      "url": "https://api.apifox.com/mcp",
      "headers": { "X-Project-Id": "123" },   // remote 静态鉴权头
      "enabled": true,
      "timeout_secs": 30
    },
    "local-fs": {
      "type": "local",
      "command": "npx",
      "args": ["-y", "@xx/mcp-fs"],
      "env": { "K": "V" },
      "enabled": true
    }
  }
}
```

**McpHub（cmx-agent-app 新增连接编排层）**：

- 启动时对 `enabled:true` 的 server **并发连接**，单个失败不炸（状态 `failed{error}`），失败原因可查；
- 状态机：`disabled → connecting → connected | failed{error}`；stdio 子进程退出 → `failed`；**无自动重连**（对齐 opencode），设置页 toggle 或刷新按钮手动重连；
- 热启停：`connect(name)` / `disconnect(name)`；`disconnect` 对 stdio 走现有 `shutdown`；`register_dyn`/`unregister` 同步工具注册表；
- 工具变更：支持 `ToolListChangedNotification` 时重拉 `list_tools`（remote 常见增量发布场景）；
- **状态广播（G2/G8）**：每次状态迁移向 `SessionEventBus` 发布全局事件 `mcp.status.changed { name, status, error?, tools_count }`（envelope `session_id` 置空串表示全局事件，前端 `/api/subscribe` 分流刷新；不落会话日志，符合「不变量约束的是会话内模型可见内容」的口径）；
- 与插件 mcp 载体的关系：`connect_mcp_plugins`（市场分发）保持独立通道不变，McpHub 管手工配置的 `mcp.json`；两者都汇入同一个工具注册表，状态广播共用。

**remote 客户端（cmx-agent-mcp 新增）**：

- Streamable HTTP 为主：JSON-RPC over `POST <url>`，`Accept: text/event-stream` 处理流式响应，维护 `Mcp-Session-Id` 头；服务器不支持时回退 HTTP+SSE（`GET /sse` 事件流 + `POST /messages`）旧 transport；
- 最小能力集：`initialize` / `tools/list` / `tools/call`（不含 sampling/elicitation/roots，与现行 stdio 客户端能力对齐）；协议版本头随握手协商；
- 鉴权：期一仅静态 `headers`（覆盖 apifox 类「URL + 项目 ID」场景）；连接收到 401/403 → 状态 `failed{error:"鉴权失败，请检查 headers"}`，OAuth 列期三；
- 超时：连接 `timeout_secs`（默认 30），工具调用沿用现有调用超时语义。

**工具并入（维持现行命名，G6 收口）**：

- 命名保持 `mcp_{label}_{tool}`（与 opencode `server_tool` / codex `server__tool` 同构，改名无收益且计划模式白名单、子智能体工具选择已引用）；
- 审批档位 per-server 化：新增 `"approval": "never" | "on-request" | "always"`（缺省 **`on-request`**，收紧 G6 的现行默认「never 即信任」；老用户升级后首次会多一次审批，属安全默认的正确代价）；`GuardHints` 按 server 档位装配（`network:true` 恒真）；
- 工具描述截断：单工具 spec 超 8KB 截断并附「（描述已截断）」（codex 预算思想的最小落地，防个别 server 的巨型 schema 撑爆上下文）。

### 4.4 设置页 UI（对齐用户截图）

设置中心导航新增两分区（插在「子智能体」之后）：**技能**、**MCP**。前端单份真源 `cmx-agent-web/ui/`，新文件 `js/skills.js`、`js/mcp.js`（+ 必要的 css）——**记得同步 include_bytes 白名单**（`cmx-agent-web/src/main.rs:206-263`）与 Tauri 壳 `sync-ui.sh`。分区交互样板抄 `agents.js`。

**技能分区**：

```
技能                                      [🔍 搜索技能…]
[💻 用户 ▾] ｜ 技能 7                       （scope：用户 / <当前空间名>）
已安装 4                          [⋯] [⟳] [+ 新建]
┌──────────────────────────────────────────────────────┐
│ [🪄] find-skills                              [⬤⬤] [🗑] │
│      Helps users discover and install agent skills…    │
│ [🪄] meeting-notes（无效：frontmatter 缺 name）  [⬤◯]    │
└──────────────────────────────────────────────────────┘
```

- scope 下拉：「用户」= 数据根 skills/；「<空间名>」= 当前工作空间 `.agents/skills/`（未绑定空间时置灰）；
- 行卡：图标 + 名称 + description 截断一行；`invalid` 条目红字标原因；右侧 toggle（写 skills.json）+ 删除（仅用户级）；空间级行副标题加「来自工作空间」、无删除钮；
- `⟳` 重扫并广播；`⋯` 菜单：打开技能目录。

**MCP 分区**：

```
MCP 服务器                                 [🔍 搜索 MCP 服务器…]
（无 scope 下拉，配置全局） ｜ MCP 3
已启用 2                          [⋯] [⟳] [+ 新建]
┌──────────────────────────────────────────────────────┐
│ [🔌] apifox-new-mcp  ●                          [⬤⬤]   │
│      http · https://api.apifox.com/mcp · 12 个工具      │
│ [🔌] local-fs        ●（红：进程已退出）          [⬤⬤]   │
│      stdio · npx -y @xx/mcp-fs · 连接失败: …            │
└──────────────────────────────────────────────────────┘
```

- 行卡：图标 + 状态点（绿=connected、灰=disabled、红=failed、黄=connecting）+ 名称 + 副标题（`http · <url>` / `stdio · <command>`）+ 工具数或错误信息；
- toggle 语义 = opencode「按状态路由」+ 持久化双写：开 = 写 `enabled:true` + `mcp_connect`；关 = 写 `enabled:false` + `mcp_disconnect`；
- `⟳` = 全量重连 `enabled` 项并刷新状态；`+ 新建` = 弹窗表单（类型 local/remote、名称、command+args+env / url+headers、超时、审批档位）+「测试连接」（临时连接验证后关闭，不落盘）；行点击 = 编辑表单；
- 删除 = 删 `mcp.json` 条目 + disconnect + unregister，确认弹窗。

### 4.5 前门协议（protocol.rs 新增，全部走 `POST /api` dispatch_json）

| cmd | 参数 | 返回 | 对应 |
| --- | --- | --- | --- |
| `list_skill_details` | — | `[{name, description, source: user/workspace, path, enabled, invalid?, error?}]` | 技能列表 |
| `set_skill_enabled` | `{name, enabled}` | `{ok}` | 行卡 toggle |
| `create_skill` | `{name, description}` | `{path}` | + 新建 |
| `delete_skill` | `{name}` | `{ok}` | 删除（仅 user 级） |
| `reload_skills` | — | `{count}` | ⟳ |
| `list_mcp_servers` | — | `[{name, config, status, error?, tools_count}]` | MCP 列表 |
| `add_mcp_server` | `{name, config}` | `{ok}`（重名拒绝） | + 新建 |
| `remove_mcp_server` | `{name}` | `{ok}` | 删除 |
| `set_mcp_enabled` | `{name, enabled}` | `{ok}` | toggle（含 connect/disconnect 联动） |
| `mcp_connect` / `mcp_disconnect` | `{name}` | `{status}` | ⟳ / 手动重连 |
| `test_mcp_server` | `{config}` | `{ok, tools_count, error?}` | 表单「测试连接」 |

**权限模型说明**：MCP 工具调用的运行期审批走既有 `ApprovalGuard`/`InteractiveApprover`（per-server 档位装配 GuardHints，见 4.3），设置页的管理命令（增删改 mcp.json / 删技能目录）是**本机配置操作**，不做会话级审批——与现状一致（设置页本就绕过会话审批），登录门（Web 壳 401）+ loopback 限制继续兜底。

### 4.6 安全与不变量对齐

| 项 | 处置 |
| --- | --- |
| fail-closed | 计划模式白名单已拦全部 MCP 工具（现状），不回归；MCP 工具 GuardHints 恒 `network:true` |
| 审批默认收紧 | MCP `approval` 缺省从「never（信任配置）」改为 `on-request`（G6）；用户可 per-server 调回 never |
| remote SSRF | 允许任意 https URL（桌面工具本就全网络权限）；`http://` 仅允许 loopback（本地网关调试场景），非 loopback 明文 http 拒绝保存并在表单标红 |
| 凭据明文 | headers/env 里的 key 明文存 `mcp.json`——沿用用户已拍板口径（本机应用凭据明文落盘、登录门覆盖） |
| 子进程治理 | stdio MCP 子进程沿用 `proc::run` 链 + `CREATE_NO_WINDOW` + Job Object（AGENTS.md Windows 约束），disconnect 时 Job Object 级联回收 |
| 不变量 | `Model-visible means logged` 不受影响：技能/MCP 配置与状态是宿主配置非会话内容；`mcp.status.changed` 走全局事件不落会话日志 |
| per-account | skills.json / mcp.json 暂挂全局数据根（与现行 mcp.json 一致）；per-user 分区是既有独立待办（providers.json 已做 per-user），不在本方案扩权 |

### 4.7 收尾整改（顺手清偿）

- **G7 撞名**：`AgentApp::list_skills()`（实为 `tools.specs()`）更名 `list_tools_specs`（`AppRequest::ListSkills` 同步更名，前端 agents.js 调用点同步）——「技能」一词归还 SKILL.md 体系；
- 旧数组版 `mcp.json` 首次读取后静默迁移为 v2（原文件备份为 `mcp.json.bak`）。

---

## 五、分期实施

| 期 | 内容 | 依赖/规模 |
| --- | --- | --- |
| **期一（MVP）** | ① McpHub + 状态机 + 热启停 + `mcp.status.changed` 广播；② `mcp.json` v2 + 旧格式迁移；③ remote 客户端（StreamableHTTP→SSE 回退、静态 headers、401 明示）；④ per-server 审批档位（缺省 on-request）+ spec 8KB 截断；⑤ SkillsIndex 两级扫描（用户级 + 工作空间 `.agents/skills/`）+ skills.json 启用态；⑥ 设置页「技能」「MCP」两分区（对齐截图全要素：scope/搜索/计数/行卡/删除/新建/测试连接/刷新）+ 协议 11 命令；⑦ `list_skills`→`list_tools_specs` 更名 | 全部在 cmx-agent 仓内（core 不动或仅加事件枚举）；remote 客户端需 HTTP 依赖（`cmx-agent-net` 已有 reqwest，可复用） |
| **期二** | ① 内置 `load_skill` 工具（模型自主按描述加载全文，权限 ask + `always` 记忆——opencode 渐进披露）；② MCP per-server `enabled_tools/disabled_tools`；③ 技能 spec 预算（单 8KB/总 64KB 超限隐藏）；④ MCP prompts 并入斜杠菜单（`/名称:mcp` 形态） | 期一 |
| **期三** | ① remote OAuth（SDK 式 provider、token `mcp-auth.json` 0600、`needs_auth` 状态 + 浏览器回调 127.0.0.1）；② 技能 marketplace（远程 index.json 拉取 + 原子 rename 升级，接插件市场形态） | 期二；OAuth 需真机验证回调链路 |

**明确不做**：MCP 自动重连（opencode 亦无，手动 ⟳ 足够）；MCP resources 三件套资源工具（当前无场景）；sampling/elicitation。

---

## 六、验收口径

- `cargo test` 全绿 + `cargo clippy --all-targets` 零告警（仓内硬约束）；
- 安全负例必须覆盖：计划模式下 MCP 工具被拒、`enabled:false` 不连接不出工具、审批档位 `always` 下 MCP 调用必出审批卡、非 loopback http URL 拒绝保存、invalid SKILL.md 不进索引但设置页可见；
- 迁移负例：旧数组 `mcp.json` 迁移后功能等价 + `.bak` 存在；
- E2E 按既定政策由用户自测（交付汇报附「看哪里、点什么」）；双壳均需验证（Web 壳 + Tauri 壳 `sync-ui.sh` 后重建）。

---

## 附：与两份既有资产的关系

- **图片粘贴方案（20260917）**：其「文本模型借图片解析 MCP」通路依赖本方案期一的 remote MCP（配一个视觉 MCP server 即可用）；两方案无代码冲突（一个改消息链路，一个改工具/配置链路）。
- **插件市场四载体**：`kind:"mcp"` 的市场插件继续走 `connect_mcp_plugins` 独立通道，本方案的 McpHub 只管手工配置；后续期三 marketplace 可统一入口。
