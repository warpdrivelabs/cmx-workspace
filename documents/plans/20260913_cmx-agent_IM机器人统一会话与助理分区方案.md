# cmx-agent IM 机器人统一会话与「助理」分区方案

> 2026-09-13 · 状态：**已审查修复并实施完成（验证全绿）**。前置：微信/QQ/飞书三通道已收敛（见 `20260911_cmx-agent_微信ClawBot机器人支持方案.md` 附三/附四）。
>
> 需求原话：①这些机器人绑定同一个会话；②都用默认工作空间；③会话展示在「助理」位置，不在空间或任务中展示。

## 〇·二、实施记录（2026-09-13，按修复后方案执行，未提交）

- 后端：`cmx-agent-app` 新增 `ASSISTANT_SESSION_ID`/`ASSISTANT_SESSION_TITLE` 常量（lib.rs 导出）、`create_session` 改 get-or-create、新增 `ensure_session` 与 `open_assistant_session`；protocol.rs 新增 `OpenAssistantSession`（cmd=`open_assistant_session`，双壳经 dispatch_json 同享）。`cmx-agent-im` 删 `session_for`/`sessions` 缓存，tick 恒落 `im-assistant` + `ensure_session(default, "IM 助理")`，消息加【飞书】/【QQ】/【微信】来源前缀。
- 前端：index.html「助理」navitem 接 `data-act="openAssistant"`（id=nav-assistant）；main.js ACTIONS 注册；session.js 新增 `openAssistant`/`updateAssistantNav` 并在 refreshTasks **空态判断之前**过滤 `^im-`；tabs.js renderTabs 挂导航高亮；layout.css 新增 `.navitem.active`（全主题变量）。已跑 `sync-ui.sh` 同步 Tauri 壳生成物。
- 验证：`cargo test -p cmx-agent-app -p cmx-agent-im --offline` 全绿（app 集成 8 二进制 49 用例 + im 66 用例；新增 assistant_session_tests 两侧 6 例）；`cargo clippy -p cmx-agent-app -p cmx-agent-im -p cmx-agent-cli -p cmx-agent-web --offline` 零告警；Tauri 壳 `cargo check` 通过；改动 JS `node --check` 通过。
- ⚠️ 预存失败（与本方案无关）：`cmx-agent-app` lib 单测 `workspace::tests::local_workspace_is_searchable_without_relocation` 在本机恒失败（`\\?\` UNC 路径前缀断言不匹配；workspace.rs 处于 HEAD 提交态 ea1637e 即失败，非本次改动引入）。待用户指示是否修复。
- 测试防碰撞教训：同进程并行测试用"纯纳秒"临时目录会撞名共享存储——新测试目录名已加进程内自增序号。

## 〇·三、补遗：首开助理 tab 标题英文（2026-09-13 用户真机反馈，已修）

- **根因**：空会话（只有 meta、JSONL 日志未落）调 `get_events` 时，`FileSessionStore::load_events_window` 因日志文件不存在直接返回 NotFound——首开「助理」时前端拿不到 meta 标题，tab 停留在会话 id `im-assistant`。
- **修复**：store 层改为「meta 存在 = 会话存在」——日志缺失时返回空窗口（events=[], total=0）并带 meta 标题；meta 也没有才报 NotFound。前端既有 `if(d.title)` 命名逻辑零改动即可生效。新增回归用例 `get_events_on_fresh_assistant_session_returns_title_not_found`。
- **顺带根除测试撞名**：feishu/qq/wechat/bridge 四个测试文件的 `temp_app` 纯纳秒临时目录在同进程并行测试下会撞名共享存储（曾致 feishu_bridge_blocks_unauthorized 偶发失败）——统一加进程内自增序号，连跑三轮全绿。
- **空态组头补齐**（用户反馈"空间跟任务平级，空态只展示了空间"）：refreshTasks 空态分支改为经 renderTaskGroup 渲染「任务」组头（与「空间」区标签同款 section 样式），空态提示文案挂在任务组 items 内（`emptyHint`，随组折叠）。
- **空会话占位卡**（用户反馈"首开助理对话区空白"）：renderHistory 空窗口时追加 `.log-empty` 占位卡（flex 列 margin:auto 居中）——助理会话给专属引导（三通道汇聚/桌面与 IM 共享上下文/固定 default 空间），其它新会话给通用上手提示；`renderEvent` 单一事件出口处移除占位卡，IM 实时首条消息/本地发送都不会残留。样式全主题变量（chat.css）。
- **空间/任务组恒渲染**（用户反馈"一边有会话另一边消失"）：refreshTasks 重写组装逻辑——每个空间（除 default）恒渲染一个组头（无会话也保留，可发现、可从 ⋯ 菜单移除；排序空组沉底），任务组恒垫底恒渲染；任务组空时分语义提示（全局无会话→「还没有任务…」，仅任务组无→「不使用工作空间的任务会出现在这里。」）。

## 〇、审查修复记录（2026-09-13 二轮代码级复核）

| # | 发现 | 处置 |
| --- | --- | --- |
| F1 | 原稿把常量 `IM_SESSION_SID` 放在 `cmx-agent-im`——但依赖方向是 im→app（ImBridge 持有 `Arc<AgentApp>`），app 层的 protocol.rs 引不到它 | **修正**：常量 `ASSISTANT_SESSION_ID` 归属 `cmx-agent-app`（app.rs 导出），im 引用之；UI 侧 JS 写死同值字面量并注释耦合 |
| F2 | 核实命令派发机制：`AppRequest` 为 `#[serde(tag="cmd", rename_all="snake_case")]`（protocol.rs:13），新增变体自动得 `open_assistant_session` 命令，Tauri/Web 双壳经 `dispatch_json` 同享，零壳侧代码 | 方案成立，无需改 |
| F3 | `refreshTasks` 的空态判断（`list.length===0` 显示"还没有任务"）在分组**之前**——过滤必须同时前移到空态判断之前，否则只剩 IM 会话时空态文案与过滤行为不一致 | 补入 §3.4 实现要点 |
| F4 | 泄漏点排查：`tabs.js` 仅剩历史注释（会话列表已挪入 session.js），`im-*` 无其它 UI 消费点 | 通过，无额外改动 |
| F5 | 预存竞态确认：`root_agent_to_session_workspace` 切的是全局 agent 文件根（app.rs:1143），两个不同空间会话并发跑回合时后写覆盖先写——**本期之前就存在**（桌面与 IM 桥本就可并发），统一会话不扩大该面 | 记为已知边界（§3.5），不在本期修 |
| F6 | 测试可行性核实：`create_workspace`（app.rs:1303）+ `select_workspace(Option<&str>)`（app.rs:1296）可在测试里构造"当前空间非 default"场景；store 无 `get_meta`，get-or-create 用 `list()` 判存在 | 补入 §五 |
| F7 | 桌面会话 id 前缀为 `task-<ts>`（session.js），过滤正则 `^im-` 无误伤 | 通过 |
| F8 | 断言更新点位已定位：`tests/{qq,wechat,feishu}_tests.rs` 共 20 处 `im-<kind>-*` get_events 断言 | 见 §四改动清单 |

## 一、现状盘点（代码事实）

| # | 事实 | 位置 |
| --- | --- | --- |
| 1 | 每个 IM 会话（聊天对象）映射稳定会话 id：`im-<kind>-<净化chat_id>`，跨通道互不撞名 | `crates/cmx-agent-im/src/lib.rs:220` `session_for` |
| 2 | 桥每处理**一条**消息都调 `session_for` + `create_session` | `lib.rs:312-313` |
| 3 | `create_session` **无条件覆盖写 meta**（title=None、workspace=当前空间） | `crates/cmx-agent-app/src/app.rs:1031-1047` |
| 4 | 回合收尾重建 meta：title 保留 prev、workspace 取 prev.or(当前)——但 prev 已被 #3 覆盖 | `app.rs:1220-1236` |
| 5 | 同会话并发有锁：后到回合排队等当前回合完成 | `app.rs:1086-1094` |
| 6 | 每回合开始把文件根切到「会话自己 meta 里的 workspace_id」 | `app.rs:1367` `root_agent_to_session_workspace` |
| 7 | 侧栏按 workspace_id 分组：None/"default"/已移除 → 任务组（垫底），其余挂空间组；`im-*` 无特殊处理 | `crates/cmx-agent-web/ui/js/session.js:20-34` |
| 8 | 「助理」是左侧栏 nav 里的**占位项**（不可点） | `crates/cmx-agent-web/ui/index.html:73` |
| 9 | 命令派发单点：`AppRequest` 枚举 → Tauri 壳 `dispatch_json` 与 Web 壳共用，加命令双壳同享 | `crates/cmx-agent-app/src/protocol.rs` |

**⚠️ 勘误**：因 #2+#3，IM 会话的 workspace 实际是「**最后一条消息那一刻**的当前空间」（每条消息重绑一次），标题也被最后一条消息重写——此前答复"首条消息那一刻绑定后固定"不准确。本方案顺带把这个不稳定修掉。

## 二、目标行为（验收口径）

1. 飞书 / QQ / 微信三通道、所有聊天对象的消息 → **同一个会话** `im-assistant`（标题「IM 助理」）。
2. 该会话 `workspace_id` **恒为 `default`**：桌面当前切到任何空间都不影响；每回合文件根随之固定 default。
3. 侧栏「助理」占位项点亮为入口：点击打开该会话，激活时高亮；**空间组与任务组不再出现任何 `im-*` 会话**（含历史散会话，隐藏不删，磁盘数据保留）。
4. 桌面端可直接在助理会话里对话——与 IM 共享同一份上下文、同一个 default 空间。
5. 助理会话被删除后，下一条 IM 消息**自愈重建**（get-or-create）。

## 三、设计

### 3.1 会话统一（`cmx-agent-im`）

- `session_for(chat)` 改为恒返回固定 id `im-assistant`；常量 `ASSISTANT_SESSION_ID` **定义在 `cmx-agent-app` 并导出**（依赖方向 im→app，见 F1），`sessions` chat→sid 缓存不再需要，一并删除。
- 消息文本加**通道来源前缀**（决策点 a）：落库与发给模型的用户回合文本变为 `【微信】你好` / `【QQ】…` / `【飞书】…`——共享会话里可分辨消息来自哪条通道；前端/回复逻辑零改动。
- tick 中 `create_session(&sid)` 改调 `ensure_session`（见 3.2），传 `workspace=Some("default")`、`title=Some("IM 助理")`。

### 3.2 空间固定 + meta 修复（`cmx-agent-app`）

- `create_session` 改 **get-or-create**：meta 已存在则原样返回、不再覆盖。这同时修掉 #3 的覆盖缺陷（桌面侧会话 id 唯一，行为不受影响；IM 侧从此标题/空间不再被反复重写）。
- 新增 `ensure_session(id, workspace_id: Option<String>, title: Option<String>) -> AppResult<String>`：get-or-create，**仅在新建时**采用给定 workspace 与 title（已存在则完全不动）。
- `root_agent_to_session_workspace` **零改动**——它读的就是 meta 里的 workspace_id，恒为 default 后每回合自动切 default。

### 3.3 桌面入口命令（`protocol.rs` 单点，双壳同享）

- 新增 `AppRequest::OpenAssistantSession`：`ensure_session("im-assistant", Some("default"), Some("IM 助理"))` 后返回会话 meta。桌面点「助理」时先 ensure 再打开——**保证从桌面首次进入（会话尚不存在）时空间/标题就正确**（若直接走 `send`，收尾兜底会用"当时当前空间"建 meta）。

### 3.4 侧栏「助理」分区（`cmx-agent-web/ui`，双壳共用真源）

- `index.html:73`：「助理」navitem 去掉 `title="占位"`，加 `data-act="openAssistant"`。
- `main.js` ACTIONS 注册 `openAssistant`：`call({cmd:"open_assistant_session"})` → `openSession(sid)`。
- 激活高亮：`CURRENT === "im-assistant"` 时给该 navitem 加 `.active`（小量 CSS）。形态为「navitem 即入口」（决策点 b，备选：navitem 下挂会话行）。
- `session.js` `refreshTasks`：`list` 取回后**先**过滤 `filter(m => !/^im-/.test(m.id))` **再**做空态判断与分组（F3）——统一会话与旧 `im-<kind>-*` 散会话一律不进空间/任务分组。
- 不动：`im-panel`（即时通讯联系人面板）维持现状；`tabs.js` 无消费点（F4）。

### 3.5 行为细节与边界

- **并发**：两通道同时来消息 → 既有会话锁排队串行执行，后者等前者回合完成（回复不串行丢失，只是延迟）。
- **绑定模式多人**：所有绑定用户的消息进同一会话，上下文互通（回复仍按各自 chat 回）。个人/单管理员场景正是需求本身；真正的多用户隔离需按绑定用户分会话，本期不做（决策点 d）。
- **个人模式**身份不变（桌面登录用户），未登录仍 fail-closed 提示。
- **已知边界（F5，预存非本期引入）**：`root_agent_to_session_workspace` 切换的是全局 agent 文件根，两个不同空间的会话并发跑回合时存在后写覆盖先写——桌面与 IM 桥本就可并发，统一会话不扩大该面；如需根治须按回合隔离根上下文，另立方案。

## 四、改动清单

| 文件 | 改动 |
| --- | --- |
| `crates/cmx-agent-im/src/lib.rs` | `session_for` 恒返 `im-assistant`；删 sessions 缓存；通道前缀；改调 `ensure_session` |
| `crates/cmx-agent-app/src/app.rs` | `create_session` 改 get-or-create；新增 `ensure_session`、`open_assistant_session` |
| `crates/cmx-agent-app/src/protocol.rs` | `AppRequest::OpenAssistantSession` + 派发分支 |
| `crates/cmx-agent-web/ui/index.html` | 「助理」navitem 接 `data-act` |
| `crates/cmx-agent-web/ui/js/main.js` | ACTIONS 注册 `openAssistant` |
| `crates/cmx-agent-web/ui/js/session.js` | `im-*` 会话过滤（不进空间/任务） |
| `crates/cmx-agent-web/ui/css/*` | navitem `.active` 样式（如缺） |
| `crates/cmx-agent-shell/src-tauri/ui/**` | 改完真源跑 `sync-ui.sh` 同步（生成物，勿手改） |
| 测试 | `tests/{qq,wechat,feishu}_tests.rs` 的 sid 断言 `im-<kind>-*` → `im-assistant`；新增 §五 用例 |

## 五、测试与验收

新增/调整单测（`cargo test -p cmx-agent-im -p cmx-agent-app --offline`）：

1. 两个不同 kind 的桥各发一条消息 → 事件都落在 `im-assistant` 同一会话。
2. 桌面先切到非 default 空间（`create_workspace` + `select_workspace`，app.rs:1296/1303，F6），再跑 IM 回合 → 会话 meta `workspace_id == "default"`。
3. `create_session` 对已存在会话二次调用 → title / workspace_id / event_count 不被覆盖。
4. `ensure_session` 幂等；新建时采用给定 workspace 与 title。

真机手工验收：三通道各发一条 → 聚合进助理会话且回复各回各通道；桌面切空间后再发 IM 消息 → 空间组不冒新会话；点「助理」打开+高亮；删除助理会话 → 下条消息自愈重建；旧散会话从侧栏消失（磁盘保留）。收尾：clippy 零告警（仓规）。

## 六、决策点（均有默认推荐，拍板或直接说"改"按推荐实施）

| # | 决策点 | 推荐 | 备选 |
| --- | --- | --- | --- |
| a | 消息加通道前缀【微信】 | **加**（共享会话可溯源） | 不加（转写保持原话） |
| b | 助理入口形态 | **navitem 即入口 + 激活高亮** | navitem 下挂会话行（似空间组） |
| c | 旧 `im-<kind>-*` 散会话 | **隐藏不删**（数据保留） | 提供一键清理 |
| d | 绑定模式多人共享上下文 | **本期接受**（个人场景） | 后续按绑定用户分会话 |
