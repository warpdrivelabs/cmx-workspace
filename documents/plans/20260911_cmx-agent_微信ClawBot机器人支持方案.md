# cmx-agent 微信机器人支持方案 — 微信 ClawBot（iLink 长轮询）Provider

> 2026-09-11 · 状态：**已实施（P0+P1 完成，当日评审通过后落地；同日用户追加拍板——GUI 扫码登录提前自 P2 落地；同日二次追加——QQ 个人号（OneBot v11 扫码）通道，见文末「附二」）**。离线验收全过：
> `cargo test --offline` **325 passed / 0 failed**、`cargo clippy --offline --all-targets` **零告警**、
> 桌面壳（独立 workspace）`cargo check --offline` 零告警、`sync-ui.sh` 已同步。
> **真机扫码端到端（§11 第 2–8 项）待用户执行**。
> 实施记录见文末「附：实施记录」。改动范围 = `cmx-agent` 仓 `crates/cmx-agent-im` + `crates/cmx-agent-cli`
> + 壳（`im_config` 校验分支 + `im_wechat_login` 扫码命令）+ UI 真源（IM 面板微信卡片），**不改内核、不改门户**。
> 实施验收基线：`cargo test --offline` 全绿 + `cargo clippy --offline --all-targets` 零告警。

## 目录

- [0. 决策记录](#0-决策记录)
- [1. 一页总览](#1-一页总览)
- [2. 渠道选型依据（为什么是 ClawBot）](#2-渠道选型依据为什么是-clawbot)
- [3. iLink 协议事实底座（写死，实施时不许再猜）](#3-ilink-协议事实底座写死实施时不许再猜)
- [4. 依赖事实底座（离线缓存已验证）](#4-依赖事实底座离线缓存已验证)
- [5. 现有代码事实底座（扩展点与集成点）](#5-现有代码事实底座扩展点与集成点)
- [6. 详细设计](#6-详细设计)
- [7. 改动清单（文件级）](#7-改动清单文件级)
- [8. 测试计划](#8-测试计划)
- [9. 分期交付](#9-分期交付)
- [10. 风险清单](#10-风险清单)
- [11. 验收清单](#11-验收清单)

---

## 0. 决策记录

| # | 决策 | 说明 |
|---|---|---|
| D1 | **渠道 = 微信 ClawBot 官方插件（iLink 协议）** | 用户拍板。微信团队 2026-03 官方发布的 OpenClaw 微信插件，底层 iLink 协议（`ilinkai.weixin.qq.com`），**合法、零封号风险**。注意与第三方逆向项目 WeClaw（`fastclaw-ai/weclaw`）区分——我们不引任何第三方桥接/逆向库，直接在 Rust 里原生实现 iLink bot 协议 |
| D2 | **provider 形态 = 长轮询型（Telegram 同款）** | iLink 是 HTTP/JSON 长轮询（`getupdates` 服务端挂起 ≤35s），出站连接、**零公网回调、零 WebSocket**。`ImProvider::start()` 走 trait 默认 no-op——不需要飞书/QQ 的常驻 task、generation 代际、热重载那套，比它们**简单一个量级** |
| D3 | **QR 扫码登录 = 独立 CLI 子命令 `cmx-agent im-login`**，凭证落盘 im.json | 登录是一次性动作（bot_token 长期复用），不该混进 provider 启动链路（fail-closed：没 token 就明确报错引导登录，而不是启动时阻塞扫码）。QR PNG 存 `<data_dir>/wechat_login_qr.png` 并打印路径（不引终端二维码渲染依赖） |
| D4 | **CLI `im` 模式装配改用 `resolve()`（env 优先 + im.json 回落）** | 现状：CLI 只读 env（`ImConfig::from_env`），桌面壳走 `resolve()`——im-login 写 im.json 后 CLI 会读不到，自相矛盾。改为与壳同一装配口，行为是纯超集；顺带获得多通道能力（每通道一个桥 task，与壳同构） |
| D5 | **v1 仅单聊文本**；群聊（`group_id` 非空）跳过并打日志 | iLink 群聊的权限模型未公开文档化（见 §3「已知限制」），不上生产赌未知行为。群聊 + 语音转写 + 媒体收发排 P2（§9） |
| D6 | **`context_token` 按会话缓存回传**（QQ `ReplyTicket` 同范式） | 每条入站消息带 `context_token`，回复回传可精确关联会话窗口（v2.1 起缺失也可发，但会退化为「最近活跃会话」——宁缓存不退化） |
| D7 | **游标（`get_updates_buf`，字符串）收在 provider 内部**，不改 `ImProvider` trait 签名 | trait 的 `poll(offset: i64)` 游标语义对字符串游标不适配；改 trait 会波及全部现有 provider 与桥。方案：wechat provider 内部 `Mutex<Option<String>>` 持游标，`update_id` 返回消息 `seq` 供桥透传，桥侧零感知。重启后游标不持久化（首轮排水历史残留，与飞书/QQ「跳过残留」同口径）；持久化排 P2 |
| D8 | **依赖零新增缓存外 crate** | 只加 `base64 = "0.22"`（QR data-url 解析 + X-WECHAT-UIN 编码）与 `getrandom = "0.2"`（X-WECHAT-UIN 随机数）。两者均已在 cmx-agent `Cargo.lock` 与本机离线缓存命中（§4）——符合仓规「外部 crate 版本照抄 cmx-container 根，新增依赖前确认缓存命中」 |
| D9 | **kind 标签 = `"wechat"`** | 会话前缀 `im-wechat-<chat>`；门户绑定表 `agent_im_binding.provider` 为开放字符串（注释枚举含 `wecom` 等），存 `"wechat"` **无需门户迁移**。env 名沿 `CMX_AGENT_IM_WECHAT_*` 前缀 |
| D10 | **`max_chunk() = 2000`**（保守值） | 微信单条文本上限未公开披露（且链接不可点击、纯文本展示），取 Telegram 4096 的一半留安全余量；后续真机测出实际上限再调常量 |
| D11 | **错误即暂停，不打腾讯接口**：`errcode=-14` 会话超时 → provider 内部 `pause_until` 暂停 1h；401 → 明确报错引导重新扫码 | 桥的 `run()` 出错只退避 3s 就重试，若把 -14 透传成 `Err` 会变成 3s 一发的撞墙——暂停逻辑必须收在 provider 内部 |

---

## 1. 一页总览

**目标**：给 `cmx-agent-im` 新增第 4 个 IM provider——微信（ClawBot / iLink）。用户用自己的微信扫码登录一次，之后在微信里私聊机器人，即可以本人身份遥控桌面 agent（个人模式）或经验证码绑定（绑定模式），与飞书/QQ 完全同构。

**数据流**：

```
微信用户 ──微信──> 腾讯 iLink 服务器 <──HTTP 长轮询 getupdates(35s)── cmx-agent（WechatProvider）
                                        <──HTTP sendmessage──────────      │
                                                                            ▼
                                                    ImBridge::tick()（白名单/绑定/个人三模式鉴权）
                                                                            │
                                                                            ▼
                                                          AgentApp::send/send_as（跑一个回合）
```

**本期（P0+P1）改动清单速览**：

| 文件 | 改动 | 规模 |
|---|---|---|
| `crates/cmx-agent-im/src/wechat.rs` | **新增**：WechatProvider + iLink 客户端 + QR 登录 | ~600 行（含内嵌单测） |
| `crates/cmx-agent-im/src/config.rs` | `ImKind::Wechat` + parse/build 分支 + 头注释 | ~20 行 |
| `crates/cmx-agent-im/src/remocon.rs` | `WechatCreds` + resolve_one 分支 + masked + `test_wechat` 预检 | ~90 行 |
| `crates/cmx-agent-im/src/lib.rs` | `mod wechat` + `pub use` | 4 行 |
| `crates/cmx-agent-im/Cargo.toml` | +`base64`、+`getrandom` | 2 行 |
| `crates/cmx-agent-im/tests/wechat_tests.rs` | **新增**：桥集成测试（对齐 qq_tests 口径） | ~120 行 |
| `crates/cmx-agent-cli/src/main.rs` | +`im-login` 子命令；`im` 装配改 `resolve()` | ~70 行 |

内核（`cmx-agent-core`）、app 层、桌面壳、门户：**零改动**。

---

## 2. 渠道选型依据（为什么是 ClawBot）

微信系四条通道的完整对比（调研结论存档）：

| 通道 | 收消息 | 发消息 | 公网回调 | 稳定性/合规 | 结论 |
|---|---|---|---|---|---|
| **微信 ClawBot（iLink）** | HTTP/JSON **长轮询**（出站） | HTTP sendmessage（主动发） | **不需要** | 微信官方插件，合法、零封号 | ✅ **选定** |
| 企业微信自建应用 | HTTP 回调（AES-CBC 加解密） | API 主动推送 | **需要** | 官方稳定，但（a）要公网回调端点，破坏桌面壳 NAT 后零暴露模型；（b）面向企业微信组织，不是「微信」 | 备选（绑定表已预留 `wecom`，将来要企业组织场景再做） |
| 企业微信群机器人/智能机器人 | HTTP 回调 | webhook/回调回复 | **需要** | 群聊 @ 场景为主 | 不合需求 |
| 微信公众号/测试号 | HTTP 回调（XML） | 客服接口 | **需要** | 主动发有 **48h 互动窗口**——遥控 agent 场景致命 | 排除 |
| 个人微信第三方逆向（WeClaw/wechatferry 等） | hook/逆向 | 同左 | 不需要 | **封号风险**，企业场景不可接受 | 排除 |

ClawBot 关键优势正中现有架构：

1. **长轮询 = 出站连接**，与 Telegram 同形态，桌面机在 NAT 后零公网暴露——飞书/QQ「无需内网穿透」的核心卖点完整保留。
2. **纯 HTTP/JSON**，无 protobuf（飞书要手写 pbbp2 帧）、无 WebSocket（QQ 要握手/心跳/identify）、无回调加解密（企业微信要 AES-CBC + sha1 验签）——**四个 provider 里实现成本最低**。
3. **可主动发消息**（无 QQ 群 5 分钟/5 条被动回复窗口），agent 长回合跑完再回复没有时间压力。

---

## 3. iLink 协议事实底座（写死，实施时不许再猜）

> 来源：`nightsailer/wechat-clawbot` 仓 `docs/ilink-protocol.md`（基于官方 npm 包 `@tencent-weixin/openclaw-weixin` v2.1.1 源码逐行整理，2026-03 抓取）。**该协议无官方公开文档**，实施中遇字段出入以 npm 包源码为最终对照真源（D11 风险项）。

### 3.1 基础

| 项目 | 值 |
|---|---|
| 基础 URL | `https://ilinkai.weixin.qq.com`（登录确认响应会下发 `baseurl`，以后者为准） |
| CDN URL（媒体，v1 不用） | `https://novac2c.cdn.weixin.qq.com/c2c` |
| 协议格式 | HTTP/JSON |
| 认证 | Bearer bot_token（QR 扫码获取，一次扫码长期使用；有效期未文档化） |

### 3.2 请求头

公共头（所有请求）：

```
iLink-App-Id: bot
iLink-App-ClientVersion: {uint32}     # 0x00MMNNPP 编码，如 0.3.0 -> 768
SKRouteTag: {routeTag}                # 可选，来自配置
```

POST 额外头：

```
Content-Type: application/json
AuthorizationType: ilink_bot_token
Authorization: Bearer {bot_token}
X-WECHAT-UIN: {base64(String(randomUint32()))}   # 随机 u32 → 十进制字符串 → 对该字符串 UTF-8 字节做 base64；防重放
```

⚠ token 处理细节：登录成功响应的 `bot_token` 字段形态可能已含 `Bearer ` 前缀（文档记为 "Bearer token"）。实现取「原样存储；发请求时若已以 `Bearer ` 开头直接用，否则补前缀」的防御策略。

### 3.3 QR 扫码登录

1. `GET /ilink/bot/get_bot_qrcode?bot_type=3`（`bot_type=3` 硬编码，含义未文档化）→
   `{ "qrcode": "<会话标识>", "qrcode_img_content": "data:image/png;base64,..." }`
2. `GET /ilink/bot/get_qrcode_status?qrcode={qrcode}`（仅公共头）轮询状态：
   `wait`（等待扫码）→ `scaned`（已扫待确认）→ `confirmed` / `expired`（二维码 ~5 分钟过期，可刷新，最多 3 次）。
   **`scaned_but_redirect`（v2.1.1+）**：响应带 `redirect_host`，后续轮询须切到 `https://{redirect_host}`（跨机房调度）。
3. `confirmed` 响应：`{ "status": "confirmed", "ilink_bot_id": "xxx@im.bot", "bot_token": "...", "baseurl": "https://ilinkai.weixin.qq.com", "ilink_user_id": "..." }`——**此后 API 基址以 `baseurl` 为准**。

### 3.4 收消息：`POST {base}/ilink/bot/getupdates`（服务端挂起 ≤35s）

请求：

```json
{ "get_updates_buf": "", "base_info": { "channel_version": "2.1.1" } }
```

响应：

```json
{ "ret": 0, "errcode": null, "errmsg": null,
  "msgs": [WeixinMessage...],
  "get_updates_buf": "<新游标>", "longpolling_timeout_ms": 35000 }
```

- `get_updates_buf` 是同步游标：首次传空串，此后**必须**原样回传上次响应值；不回传/回旧值 = 重复收消息。客户端应持久化（本期不持久化，见 D7）。
- 无历史消息查询 API，只能长轮询实时收。
- HTTP 客户端超时须 > 35s（方案定 45s；其余调用 15s）。

### 3.5 发消息：`POST {base}/ilink/bot/sendmessage`（≤15s）

```json
{ "msg": {
    "to_user_id": "xxx@im.wechat",
    "client_id": "<自定义客户端ID>",
    "message_type": 2, "message_state": 2,
    "context_token": "<回传收到的 token>",
    "item_list": [ { "type": 1, "text_item": { "text": "回复内容" } } ] },
  "base_info": { "channel_version": "2.1.1" } }
```

响应：HTTP 200，**无响应体**（非 2xx 即失败）。

### 3.6 WeixinMessage 结构与枚举

| 字段 | 说明 |
|---|---|
| `seq` / `message_id` | 序列号 / 唯一消息 ID（去重键） |
| `from_user_id` | 发送者（`xxx@im.wechat`）——**绑定模式的 sender** |
| `to_user_id` | 接收者（机器人是 `xxx@im.bot`） |
| `session_id` / `group_id` | 会话 / 群（群聊时 `group_id` 非空；权限模型未文档化 → v1 跳过群聊） |
| `message_type` | 0 NONE / **1 USER** / 2 BOT（我们只处理 1，跳过自己发的回声） |
| `message_state` | 0 NEW / 1 GENERATING / 2 FINISH |
| `item_list` | 内容列表：type 0 NONE / **1 TEXT**(`text_item.text`) / 2 IMAGE / 3 VOICE / 4 FILE / 5 VIDEO |
| `context_token` | 会话令牌，**回复时回传**（D6） |

语音特有：`voice_item.text` 是**微信服务端语音识别结果**（可能为空）——有值即可直接当文本用（P2 快赢）。

### 3.7 辅助端点（v1 不实现，记录备查）

| 端点 | 用途 | 备注 |
|---|---|---|
| `POST /ilink/bot/getconfig` | 取 `typing_ticket`（按用户，建议缓存 TTL 24h） | P2「正在输入」指示器用 |
| `POST /ilink/bot/sendtyping` | status 1=输入中（每 5s 续）、2=取消 | P2 |
| `POST /ilink/bot/getuploadurl` + CDN 上传 | 媒体上传（AES-128-ECB/PKCS7 加密，密钥 16 字节 hex） | P2 媒体收发用（`aes 0.8.4` 已在缓存） |

### 3.8 错误处理与重试

| 情形 | 处理 |
|---|---|
| `ret=0` | 成功 |
| `errcode=-14` 会话超时 | **暂停该账户所有 API 调用 1 小时**（D11：收在 provider 内部 `pause_until`，期间 `poll` 返回空并打一次 warn，不透传 Err 给桥避免 3s 撞墙） |
| HTTP 4xx（含 401 token 失效） | 401 → 报错带明确指引「token 失效，请重新 `cmx-agent im-login` 扫码」；provider 内部记 `needs_relogin`，此后 poll 返回同一条友好错误（打日志限频，不刷屏） |
| HTTP 5xx / 网络错误 | 返回 Err，桥 `run()` 自带 3s 退避；provider 内部长轮询连续失败再叠退避（1-2 次等 2s，≥3 次等 30s，协议文档建议值） |

### 3.9 已知限制（协议文档原文摘录）

无历史消息查询 API；速率限制未公开；`bot_type` 未文档化；**依赖 OpenClaw 平台生态**（微信侧要求用户装 ClawBot 插件并绑定）；**腾讯保留单方面变更/中断/终止服务的权利**；bot 发的消息中**链接不可点击**（纯文本展示）。

---

## 4. 依赖事实底座（离线缓存已验证）

cmx-agent-im 现有依赖（`Cargo.toml`）：`reqwest 0.12`（`json`+`rustls-tls`）、`tokio-tungstenite 0.24`、`futures-util`、`serde/serde_json/async-trait/tokio/tracing` + 三个 workspace 内部 crate。

本方案新增直接依赖，全部命中 `Cargo.lock` 与本机离线缓存（`CARGO_HOME=D:\Packages\cargo`）：

| crate | 锁定版本 | 缓存 | 用途 |
|---|---|---|---|
| `base64` | 0.22.1（lock 已有） | ✅ | QR `data:image/png;base64,...` 解码；`X-WECHAT-UIN` 字符串编码 |
| `getrandom` | 0.2.17（lock 已有，另有 0.4.3 并存；**取 0.2** 与现解析图一致，`getrandom::getrandom(&mut [u8;4])` 取随机 u32） | ✅ | `X-WECHAT-UIN` 防重放头 |

不新增任何加密/protobuf/websocket 依赖。`tokio-tungstenite`/`futures-util` 仍被飞书/QQ 使用，保留。

---

## 5. 现有代码事实底座（扩展点与集成点）

> 行号以 2026-09-11 工作区实读为准。

| 事实 | 出处 |
|---|---|
| `ImProvider` trait：`poll(offset: i64) -> (Vec<InboundMsg>, i64)`、`send(chat_id, text)`、`start()`（轮询型 no-op）、`stop()`（默认 no-op）、`max_chunk()`（默认 3800） | [lib.rs:55-74](file:///e:/Pansoft/cmx/cmx-workspace/backend/cmx-agent/crates/cmx-agent-im/src/lib.rs#L55-L74) |
| `InboundMsg { chat_id, text, update_id, sender }`；`sender` 空 → 绑定模式 fail-closed 拒 | [lib.rs:43-52](file:///e:/Pansoft/cmx/cmx-workspace/backend/cmx-agent/crates/cmx-agent-im/src/lib.rs#L43-L52)、[lib.rs:179-182](file:///e:/Pansoft/cmx/cmx-workspace/backend/cmx-agent/crates/cmx-agent-im/src/lib.rs#L179-L182) |
| 桥 `tick()`：poll → 白名单 → 个人/绑定鉴权 → `send_as`/`send` → `chunk_text(max_chunk)` 分段 `send`；会话 id `im-<kind>-<净化chat_id>`（`@` 会被净化掉，无碍） | [lib.rs:228-327](file:///e:/Pansoft/cmx/cmx-workspace/backend/cmx-agent/crates/cmx-agent-im/src/lib.rs#L228-L327)、[lib.rs:213-225](file:///e:/Pansoft/cmx/cmx-workspace/backend/cmx-agent/crates/cmx-agent-im/src/lib.rs#L213-L225) |
| 桥 `run()`：出错退避 3s 重试、无消息节流 500ms、watch 热重载 | [lib.rs:331-367](file:///e:/Pansoft/cmx/cmx-workspace/backend/cmx-agent/crates/cmx-agent-im/src/lib.rs#L331-L367) |
| `ImKind`：`Telegram/Feishu/Qq` + `label()` + `parse_kind`（错误信息里列可选值——**加分支时同步改错误文案**） | [config.rs:21-55](file:///e:/Pansoft/cmx/cmx-workspace/backend/cmx-agent/crates/cmx-agent-im/src/config.rs#L21-L55) |
| `ImConfig::build_provider()`：按 kind 读凭证 env 装配 provider | [config.rs:78-98](file:///e:/Pansoft/cmx/cmx-workspace/backend/cmx-agent/crates/cmx-agent-im/src/config.rs#L78-L98) |
| im.json 多通道：`ImRemoconConfig { enabled, kind, active, personal, feishu, telegram, qq, allow }`；`resolve()` env 优先 → im.json；半配凭证整体 Err（fail-closed）；`masked()` 脱敏回显 | [remocon.rs:24-52](file:///e:/Pansoft/cmx/cmx-workspace/backend/cmx-agent/crates/cmx-agent-im/src/remocon.rs#L24-L52)、[remocon.rs:246-292](file:///e:/Pansoft/cmx/cmx-workspace/backend/cmx-agent/crates/cmx-agent-im/src/remocon.rs#L246-L292)、[remocon.rs:145-161](file:///e:/Pansoft/cmx/cmx-workspace/backend/cmx-agent/crates/cmx-agent-im/src/remocon.rs#L145-L161) |
| 预检函数范式：`test_feishu` / `test_qq`（面板「测试连接」，两跳轻量验证，不建长连接） | [remocon.rs:303-412](file:///e:/Pansoft/cmx/cmx-workspace/backend/cmx-agent/crates/cmx-agent-im/src/remocon.rs#L303-L412) |
| 飞书/QQ 测试范式：`inject` 塞 inbox 队列（不连真服务）驱动桥；`MockModel::saying` + `DesktopAppBuilder` 真实 AgentApp；临时目录 `temp_dir + 唯一后缀`（不引 tempfile） | `tests/qq_tests.rs`、`tests/feishu_tests.rs` |
| CLI `im` 模式：`ImConfig::from_env` → `build_provider` → `provider.start()` → `ImBridge::run`（**只走 env，是 D4 要改的点**） | [main.rs:50-79](file:///e:/Pansoft/cmx/cmx-workspace/backend/cmx-agent/crates/cmx-agent-cli/src/main.rs#L50-L79) |
| 桌面壳装配（**本期不改，行为已兼容**）：`resolve(Some(&data_dir))` → 每通道 spawn 一个桥；`im_config` Tauri command get/set 热重载 | [shell main.rs:45-166](file:///e:/Pansoft/cmx/cmx-workspace/backend/cmx-agent/crates/cmx-agent-shell/src-tauri/src/main.rs#L45-L166) |
| 门户绑定表 `agent_im_binding.provider` 为开放字符串（注释枚举 `feishu / telegram / wecom / dingtalk …`），存 `wechat` 免迁移 | [迁移 SQL:32](file:///e:/Pansoft/cmx/cmx-workspace/backend/cmx-container/docs/sql/v2/platform/migrations/20260908_001_智能体IM绑定建表.up.sql#L32) |

---

## 6. 详细设计

### 6.1 `wechat.rs` — WechatProvider

```rust
pub(crate) const WECHAT_BASE_DEFAULT: &str = "https://ilinkai.weixin.qq.com";
/// iLink channel_version（照官方 v2.1.1 抄）；ClientVersion 头由 crate 版本按 0x00MMNNPP 编码。
pub(crate) const ILINK_CHANNEL_VERSION: &str = "2.1.1";
/// 回复分段上限（D10：官方上限未披露，保守 2000）。
const WECHAT_MAX_CHUNK: usize = 2000;
/// errcode=-14 暂停时长（协议文档：1 小时）。
const SESSION_TIMEOUT_PAUSE: Duration = Duration::from_secs(3600);
/// context_token 缓存 TTL（参考 typing_ticket 的 24h 建议值）。
const CONTEXT_TTL: Duration = Duration::from_secs(24 * 3600);

pub struct WechatProvider { inner: Arc<WechatInner> }

struct WechatInner {
    base: Mutex<String>,            // 登录 confirmed 后可被响应的 baseurl 覆盖（IDC 调度）
    bot_token: Mutex<String>,       // im-login 写入 im.json 后经 new() 注入；空 = 未登录
    http: reqwest::Client,          // 常规调用 15s
    longpoll: reqwest::Client,      // getupdates 专用 45s（> 服务端 35s 挂起）
    cursor: Mutex<Option<String>>,  // get_updates_buf（D7：字符串游标收内部）
    inbox: Mutex<VecDeque<InboundMsg>>,
    seen: Mutex<HashSet<i64>>,      // message_id 去重（>4096 清空）
    contexts: Mutex<HashMap<String, (String, Instant)>>, // chat_id → context_token（D6）
    pause_until: Mutex<Option<Instant>>,                 // -14 暂停（D11）
    seeded: AtomicBool,             // 首轮排水历史残留
}
```

公开方法（命名对齐飞书/QQ 范式）：

- `new(bot_token: &str, base: Option<&str>) -> Self`
- `from_env() -> Option<Self>`：`CMX_AGENT_IM_WECHAT_BOT_TOKEN`（必需）+ `CMX_AGENT_IM_WECHAT_BASE`（可选）。token 空返回 `None`（→ `build_provider` 报「缺 token」）
- `inject_inbound(&self, chat_id, sender, text, seq)`：测试注入口（绕网络直塞 inbox；对齐 qq/feishu `inject*` 命名）
- `async fn login_qr(&self, qr_png_path: &Path) -> Result<WechatLogin, String>`：§3.3 全流程——取 QR → 解 data-url 写 PNG 文件 → 轮询状态（处理 `scaned_but_redirect` 切 `redirect_host`；`expired` 重取 ≤3 次；每次状态变化经 `tracing::info` 打印）→ confirmed 时用响应 `baseurl` 覆盖 `self.base`。返回 `WechatLogin { bot_token, bot_id, user_id, base }`
- iLink 内部层：`fn common_headers(&self, rb: RequestBuilder)`、`async fn post_api(&self, path, body) -> Result<Value, String>`、`async fn get_updates(&self) -> Result<(Vec<WeixinMessage>, String), String>`、`async fn send_message(&self, to, text, context_token: Option<&str>) -> Result<(), String>`
- 纯函数（单测锚点）：`fn parse_weixin_message(&WeixinMessage) -> Option<ParsedMsg>`（过滤 + 提取）、`fn build_send_body(to, text, context_token, client_id) -> Value`、`fn encode_client_version(major, minor, patch) -> u32`、`fn random_uin() -> String`（base64(十进制字符串)）

`impl ImProvider`：

- `poll(offset)`：忽略桥的 i64 offset（D7）。① `pause_until` 未到 → 返回空；② `get_updates()`（失败退避策略见 §3.8）→ 逐条 `parse_weixin_message` 过滤转换 → 首轮（`seeded=false`）全部丢弃只推游标（跳过历史残留）→ 否则去重后塞 inbox；③ 排水 inbox 返回 `(Vec<InboundMsg>, 最后一条 seq)`
- `send(chat_id, text)`：从 `contexts` 取该会话 token（过期/缺失传 `None`）→ `send_message`
- `max_chunk()` → 2000；`start()`/`stop()` → trait 默认 no-op（轮询型）

**入站过滤与映射**（`parse_weixin_message`）：

| 条件 | 处理 |
|---|---|
| `message_type != 1`（BOT 回声/NONE） | 丢弃 |
| `group_id` 非空（群聊，D5） | 丢弃 + `tracing::info!` |
| `item_list` 无 `type=1` 文本项 | 丢弃（媒体消息 v1 不处理；语音转写见 P2） |
| `message_id` 已在 `seen` | 丢弃（游标回退兜底） |
| 文本 = 多个 text_item 顺序拼接 | 合并 |
| 映射 | `chat_id = from_user_id`、`sender = from_user_id`、`text`、`update_id = seq`；同时 `contexts.insert(chat_id, (context_token, now))` |

### 6.2 QR 登录与凭证落盘（`im-login` 子命令）

```
cmx-agent im-login [data_dir]
```

流程：数据根取 `shared_data_dir()` 同款解析（对齐 `im` 模式的 data_dir 语义）→ 从 im.json 读已存 `wechat.base`（可选）→ 构造 provider → `login_qr(<data_dir>/wechat_login_qr.png)`（控制台打印「二维码已保存：<路径>，请用微信扫码并在手机确认」）→ 成功后 `load_im_config` → 更新 `wechat` 字段（`bot_token/bot_id/user_id/base`）并把 `"wechat"` 追加进 `active`（已含则不动；文件不存在则新建默认配置）→ `save_im_config` → 打印 `✓ 登录成功 bot_id=… 凭证已写入 <im.json 路径>`。

凭证安全：bot_token 属「用户自己的凭证 + 本机 data_dir」，与 model.json 存 api_key、im.json 存 app_secret 同级（仓内既有定论，见 remocon.rs 头注释）；GUI 回显一律走 `masked()` 尾 4 位。

### 6.3 config.rs 接线

- `ImKind::Wechat`；`label() = "wechat"`；`parse_kind` 加 `"wechat"` 分支 + 错误文案改「可选 telegram / feishu / qq / wechat」
- `build_provider()` 加分支：`WechatProvider::from_env().ok_or("缺 CMX_AGENT_IM_WECHAT_BOT_TOKEN（微信 ClawBot bot_token，先运行 cmx-agent im-login 扫码）")`
- 模块头注释补 env 文档（`CMX_AGENT_IM_WECHAT_BOT_TOKEN` / `_BASE`）

### 6.4 remocon.rs 接线

```rust
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct WechatCreds {
    #[serde(default)] pub bot_token: String,  // 扫码获取，im-login 写入
    #[serde(default)] pub bot_id: String,     // xxx@im.bot（展示用）
    #[serde(default)] pub user_id: String,    // ilink_user_id（展示用）
    #[serde(default)] pub base: String,       // 空 = 默认 https://ilinkai.weixin.qq.com
}
```

- `ImRemoconConfig` 加 `#[serde(default)] pub wechat: WechatCreds`（旧文件无此字段自动补默认，不炸）
- `masked()` 加 `wechat_bot_id`、`wechat_token_masked`、`wechat_base`
- `resolve_one` 加 `ImKind::Wechat` 分支：`bot_token` 空 → `Err("im.json 已选 wechat 但未扫码登录（运行 cmx-agent im-login）")`（fail-closed，对齐「半配凭证」语义）
- 新增 `pub async fn test_wechat(bot_token: &str, base: Option<&str>) -> Result<String, String>`（面板「测试连接」）：空 token → Err 提示先扫码；有 token → 3s 超时调 `getupdates`（空游标，`ret=0` 即 ✓；HTTP 401 → 「token 已失效，请重新扫码」）。与 `test_feishu`/`test_qq` 同地位
- `lib.rs` 的 `pub use remocon::{...}` 补 `WechatCreds, test_wechat`

### 6.5 CLI（`cmx-agent-cli/src/main.rs`）

1. `main()` 分发加 `im-login` 分支（`args[1] == "im-login"`）
2. `im` 模式（D4）：`ImConfig::from_env + build_provider` 换成 `cmx_agent_im::resolve(Some(&data_dir))`；对 `resolved.channels` **逐通道** spawn 一个桥 task（watch stop 永不置位，与现语义一致；多通道同时在线，与桌面壳同构）。`tracing::info!` 打印各通道 kind
3. 头注释补 wechat env 与 im-login 用法

### 6.6 不改动项（明确边界）

- `cmx-agent-core` / `cmx-agent-app` / `cmx-agent-connectors`：零改动（`ImBridge`/`InboundMsg`/绑定协议原样复用）
- 桌面壳（Tauri `src-tauri/`）与前端 UI：零改动——壳走 `resolve()` 自动获得 wechat 通道（前提 im.json 已由 im-login 配好）。GUI 面板可视化扫码登录、IM 面板加微信卡片属 P2
- 门户（绑定 API / 表结构）：零改动（provider 为开放字符串）

---

## 7. 改动清单（文件级）

| # | 文件 | 动作 | 内容 |
|---|---|---|---|
| 1 | `crates/cmx-agent-im/src/wechat.rs` | 新增 | §6.1 全部 + 内嵌单测 |
| 2 | `crates/cmx-agent-im/src/lib.rs` | 修改 | `mod wechat;` + `pub use wechat::WechatProvider;` + remocon re-export 补两项 |
| 3 | `crates/cmx-agent-im/src/config.rs` | 修改 | §6.3 |
| 4 | `crates/cmx-agent-im/src/remocon.rs` | 修改 | §6.4 |
| 5 | `crates/cmx-agent-im/Cargo.toml` | 修改 | `base64 = "0.22"`、`getrandom = "0.2"`（带一行注释：用途 + 离线缓存命中依据） |
| 6 | `crates/cmx-agent-im/tests/wechat_tests.rs` | 新增 | §8 桥集成 |
| 7 | `crates/cmx-agent-cli/src/main.rs` | 修改 | §6.5 |

---

## 8. 测试计划

**口径**：全离线、确定性（仓规）。不写任何连 `ilinkai.weixin.qq.com` 的测试；HTTP 层靠「纯函数锚点 + inject 驱动桥」覆盖，真机验收单独立项（§11）。

### 8.1 wechat.rs 内嵌单测

| 测试 | 断言 |
|---|---|
| `client_version_encodes_mmnnpp` | `encode(0,3,0) == 768`；`encode(2,1,1) == 0x00020101` |
| `random_uin_shape` | 每次不同；base64 解码后是全数字十进制串 |
| `parse_user_text_message` | type=1 单/多 text_item → 文本合并、chat_id/sender=from_user_id、update_id=seq |
| `parse_skips_bot_echo_and_group` | type=2 丢弃；group_id 非空丢弃；纯图片 item 丢弃 |
| `parse_dedup_by_message_id` | 同 id 二次解析 → None |
| `build_send_body_shape` | message_type=2、message_state=2、context_token 透传、item_list[0].text_item.text 正确、client_id 非空 |
| `cursor_roundtrip` | get_updates 响应新游标覆盖旧值（用注入的假响应测状态机） |
| `context_token_expiry` | 超 CONTEXT_TTL 后 send 不再携带 |
| `session_timeout_pause` | -14 → `pause_until` 置位 → 期间 poll 返回空且不发网络请求 |

### 8.2 remocon/config 单测

`parse_kind("wechat")`；`resolve_one("wechat")` 无 token → Err 带指引、有 token → Ok 且 kind 正确；im.json roundtrip 含 `wechat` 字段（serde default 兼容旧文件）；`masked()` 含 wechat 掩码字段；`test_wechat` 空 token → Err。

### 8.3 桥集成（`tests/wechat_tests.rs`，对齐 `qq_tests` 口径）

`WechatProvider` 测试构造（token 随意 + `inject_inbound`）+ `MockModel::saying` + `DesktopAppBuilder` 真实 AgentApp：

1. 收消息跑回合并回复（断言发送捕获器收到回复，`provider.send` 经测试注入的发送捕获，与 qq/feishu `inject_with_sender` 同款）
2. 白名单外 chat 拒回复提示
3. 同 chat 复用会话 `im-wechat-<chat>`（两轮消息断言两次 UserMessage）
4. 绑定模式四例：未绑定不跑、发验证码完成绑定、已绑定直跑（`send_as` 身份正确）、绑定服务坏 fail-closed

### 8.4 既有回归

`cargo test --offline` 全绿（≥ 211 + 新增 ~20）；`cargo clippy --offline --all-targets` 零告警；`unsafe_code = "forbid"` 保持。

---

## 9. 分期交付

| 期 | 内容 | 完成标志 |
|---|---|---|
| **P0** | `wechat.rs` provider 核心（iLink 客户端 / QR 登录 / 长轮询 / 发送）+ 单测；Cargo.toml 依赖 | 单测全绿 |
| **P1** | config/remocon/lib 接线 + CLI（`im-login` + `im` 改 `resolve`）+ 桥集成测试 + 真机扫码端到端 | §11 全过；`cargo test --offline` 全绿 + clippy 零告警 |
| **P2**（另立方案/任务，本期不做；**①已随用户追加拍板提前落地**） | ① ~~壳 UI 扫码登录~~ ✅（Tauri command `im_wechat_login`（start/poll，`net_rt` 上跑网络）+ IM 面板微信卡片：登录状态/扫码按钮/二维码展示/状态轮询/confirmed 自动勾选并热重载）；② 「正在输入」指示器（`getconfig`/`sendtyping`，需给 `ImProvider`/`ImBridge` 加处理钩子）；③ 语音消息快赢（`voice_item.text` 服务端转写直接喂 agent）；④ 媒体收发（CDN + AES-128-ECB，`aes 0.8.4` 已在缓存）；⑤ 群聊（等协议权限模型明朗）；⑥ `get_updates_buf` 游标持久化；⑦ IM 面板微信卡片（`crates/cmx-agent-web/ui/` 真源 + sync-ui）——已随 ① 落地 | — |

---

## 10. 风险清单

| # | 风险 | 等级 | 缓解 |
|---|---|---|---|
| R1 | **iLink 无官方公开文档**，本方案协议事实来自社区对 `@tencent-weixin/openclaw-weixin` v2.1.1 的源码整理；腾讯保留变更/终止权利 | 高 | 实施前以 npm 包源码核对一遍字段；端点/枚举/结构全部收在 `wechat.rs` 常量与 serde 结构，变更时单文件可改；`channel_version` 常量化可跟随升级 |
| R2 | **bot_token 有效期未文档化**，失效后机器人静默不可用 | 中 | 401 → 日志 + `test_wechat`/poll 错误信息均带「重新扫码」指引；重登成本 = 一条命令；P2 壳 UI 后更进一步 |
| R3 | ClawBot 绑定**个人微信号**，需用户安装微信 ClawBot 插件；腾讯服务条款含内容审查/限流/可终止 | 中 | 使用须知写入 `im-login` 输出与 README；建议专用小号；企业合规场景仍以企业微信为正解（D1 备选路径保留） |
| R4 | 速率限制未披露，回复分段过多可能触发风控 | 中 | `max_chunk=2000` 保守；桥无消息节流 500ms 既有；长轮询天然低频 |
| R5 | IDC 重定向 / `baseurl` 覆盖处理不当导致登录后连错机房 | 中 | confirmed 响应 `baseurl` 必须覆盖 base（§6.1）；`scaned_but_redirect` 单测覆盖状态机 |
| R6 | 首轮长轮询拉到历史残留导致「复述旧消息」 | 低 | `seeded` 首轮排水（§6.1），与飞书/QQ 同口径，桥集成测试覆盖 |
| R7 | GUI 面板保存 im.json 时（P2 前）`im_config set` 若不透传 `wechat` 字段会**抹掉已扫码凭证** | 中 | P1 在 `im_config set` 侧（壳）加一行透传，或在文档标注「GUI 保存会清 wechat 凭证，重登即可」——实施时选前者（改动在壳 main.rs，一行级） |

---

## 11. 验收清单（真机，P1 出口）

1. ✅ `cargo test --offline` 全绿（323 passed，含新增 22 个 wechat 测试函数）+ `cargo clippy --offline --all-targets` 零告警
2. ⬜ `cmx-agent im-login <data_dir>`：打印 QR 路径 → 手机（已装微信 ClawBot 插件）扫码确认 → `✓ 登录成功 bot_id=xxx@im.bot` → im.json 出现 `wechat` 凭证且 token 掩码形态正确
3. ⬜ `CMX_AGENT_IM_KIND=wechat` + `CMX_AGENT_IM_WECHAT_BOT_TOKEN` + `CMX_AGENT_IM_ALLOW=<自己 chat_id>` → `cmx-agent im`：微信私聊发「算 2+3」→ 收到正确回复；连发两条上下文连贯（同会话）
4. ⬜ 白名单外微信号发消息 → 收「未授权」提示、agent 不跑回合
5. ⬜ 长回复（>2000 字）分段送达、顺序正确、无截断
6. ⬜ 桌面壳路径：im.json 配好后起壳 → 微信私聊以**登录人身份**跑回合（个人模式）；改绑定模式 → 验证码绑定全流程走通（provider 字符串 = `wechat`）
7. ⬜ 重启进程 → 不重放历史消息；微信侧无重复回复
8. ⬜ 停网 1 分钟 → 恢复后自动续收（退避重连生效），期间无 panic

---

## 附：实施参照索引

- Telegram 长轮询范式：`crates/cmx-agent-im/src/telegram.rs`
- inject 测试范式：`crates/cmx-agent-im/src/qq.rs`（`inject_with_sender`）+ `tests/qq_tests.rs`
- remocon 装配/预检范式：`crates/cmx-agent-im/src/remocon.rs`（`resolve_one` / `test_qq`）
- 飞书落地纪要（provider 落地过程文档范式）：`backend/cmx-agent/docs/20260907_飞书IM_Provider_Stream模式落地纪要.md`
- 协议原始文档：`https://github.com/nightsailer/wechat-clawbot/blob/master/docs/ilink-protocol.md`（v2.1.1）
- 官方实现对照真源：npm `@tencent-weixin/openclaw-weixin` v2.1.1（实施前核对字段用）

---

## 附：实施记录（2026-09-11，P0+P1 当日评审当日落地）

| # | 文件 | 实际改动 | 与方案差异 |
|---|---|---|---|
| 1 | `crates/cmx-agent-im/src/wechat.rs` | **新增 ~810 行**：WechatProvider（iLink 客户端 / QR 登录 `login_qr` / 长轮询 / 发送）+ 14 个内嵌单测 | 无实质差异 |
| 2 | `crates/cmx-agent-im/Cargo.toml` | +`base64 = "0.22"`、+`getrandom = "0.2"`（lock 命中 0.22.1 / 0.2.17，离线构建通过） | 无 |
| 3 | `crates/cmx-agent-im/src/config.rs` | `ImKind::Wechat` + `label()`/`parse_kind`/`build_provider` 分支 + 头注释 env 文档 + parse 测试断言 | 无 |
| 4 | `crates/cmx-agent-im/src/remocon.rs` | `WechatCreds` + `ImRemoconConfig.wechat` + `masked()` 三字段 + `resolve_one` 分支 + `test_wechat` 预检 + 3 处测试 | 无 |
| 5 | `crates/cmx-agent-im/src/lib.rs` | `mod wechat` + `WechatProvider`/`WechatCreds`/`test_wechat` 导出 + 头注释更新 | 无 |
| 6 | `crates/cmx-agent-im/tests/wechat_tests.rs` | **新增** 6 个桥集成测试（跑回合 / 白名单拦截 / 会话复用 `im-wechat-*` / 绑定模式三例） | 无 |
| 7 | `crates/cmx-agent-cli/src/main.rs` | +`im-login` 子命令（QR 登录 → im.json 落盘）；`im` 模式改 `resolve()` 多通道装配（每通道一个桥 task + personal + PortalBindingResolver） | 与方案 D4 一致；额外接了 `with_bindings`（portal_base 取 `CMX_AGENT_PORTAL_BASE` env 或 AuthConfig 默认），使绑定模式在 CLI 可用 |
| 8 | `crates/cmx-agent-shell/src-tauri/src/main.rs` | R7：`im_config` get 默认 JSON 补 wechat 三字段；set 凭证校验加 `"wechat" if bot_token.is_empty()` 分支（GUI set 本就不触碰 `cfg.wechat`，凭证天然保留） | 按方案 R7 首选路径 |
| 9 | `crates/cmx-agent-im/src/wechat.rs`（GUI 追加） | `login_qr` 拆分为分步会话：`qr_begin()` → `WechatQrSession::poll_once()`（`QrEvent::Waiting/Scaned/Refreshed/Confirmed`；IDC 重定向/过期自动重取收在会话内）；CLI `login_qr` 改为会话循环复用，签名不变；+`parse_qr_status` 纯函数单测 | P2-① 提前 |
| 10 | `crates/cmx-agent-shell/src-tauri/src/main.rs`（GUI 追加） | 新增 `im_wechat_login` Tauri command（`start`=取码入静态槽返回 PNG data-url；`poll`=轮询一次；confirmed 落盘 im.json + `wechat` 追加进 active + 启用态热重载；网络走 `net_rt()`+`spawn_blocking`，锁不跨 await）并注册 | P2-① 提前 |
| 11 | `crates/cmx-agent-web/ui/`（GUI 追加，真源；`sync-ui.sh` 已同步 Tauri 侧） | `index.html` IM 面板加微信卡片（登录状态/扫码按钮/二维码图/说明）；`im.js` 加 `scfgWechatLogin()`（start→2s 轮询→confirmed 自动勾选微信通道+回显 bot_id；关面板停轮询）+ 通道表统一 `credEl` 徽标逻辑；`main.js` ACTIONS 注册 | P2-①/⑦ 提前 |

**GUI 扫码交互闭环**：设置 → IM 遥控 → 微信卡片「扫码登录」→ 面板内显示二维码（5 分钟过期自动刷新，图片同步更新）→ 手机确认 → 凭证自动落盘 + 微信通道自动勾选 + IM 桥热重载（扫码即上线，无需再点保存）。首次绑定从此**不再依赖命令行**（CLI `im-login` 保留为无 GUI 场景兜底）。

**实现要点补充**（比方案更细的两处设计落定）：

1. **poll 排水优先**：`poll` 先排空 inbox，空了才发起 `getupdates` 长轮询——保证测试 inject 路径与桥的两轮 tick 间隙完全不触网（qq 的 poll 天然不触网，wechat 需要此设计才能保住「无网络、确定性」测试口径）。
2. **401 限频复用 pause 机制**：token 失效（401）→ 置 60s 静默期 + 返回一次带「重新 im-login」指引的 Err；此后静默期空轮，避免桥 3s 退避把指引刷屏（与 -14 的 1h 暂停同机制）。
3. **⚠ 二维码协议纠偏（GUI 自测发现，2026-09-11）**：真机探测 `get_bot_qrcode` 实际返回的 `qrcode_img_content` **不是** 社区文档所写的 `data:image/png;base64,…`，而是**二维码内容字符串**（`https://liteapp.weixin.qq.com/q/…` 授权页 URL）——图必须客户端自己渲染。修正：后端只下发内容（`qr_content`）；GUI 用 vendor 的 `qrcode-generator 1.5.2`（MIT，`ui/js/vendor/qrcode.min.js`，双壳共用，CSP `img-src data:` 放行其 GIF data-url）前端渲染；CLI 经 `qr_login_html()` 生成自包含 HTML（内嵌同款 lib）浏览器打开即见码；`login_qr` → `login_qr_with(on_qr)` 回调式（展示逻辑归调用方）。扫码提示文案同步精简、扫码按钮对齐面板主按钮样式。
4. **⚠ 登录轮询瞬断容错（CLI 自测复现，2026-09-11）**：`get_qrcode_status` 长轮询期间实测偶发 reqwest 瞬断（`error sending request`，运行数分钟后出现一次）——原实现一次失败即终态，把正常登录打死。修正：`poll_once` 加连续失败容忍（`LOGIN_POLL_MAX_FAILS=5`，成功清零，期间记日志自动重试），超限才透传最后一次错误；同时 GUI 失败原因改到**状态行常驻**（toast 1.6s 读不完），壳命令补 `tracing::warn` 后台日志。

**验证结果**：

- `cargo test --offline`：**325 passed / 0 failed**（AGENTS.md 旧计数 211 已同步更正为 325）
- `cargo clippy --offline --all-targets`：**零告警**（EXIT=0）
- `crates/cmx-agent-shell/src-tauri` 独立 workspace `cargo check --offline`：**零告警**通过（tauri 依赖本机缓存命中）
- `sync-ui.sh`：UI 真源已同步 Tauri 侧
- 真机扫码端到端（§11 第 2–8 项，GUI 与 CLI 双入口）：**待用户执行**（需已安装微信 ClawBot 插件的微信号）

---

## 附二：QQ 个人号（OneBot v11 扫码）通道追加实施记录（2026-09-11，同日二次追加）

### 背景与决策

用户要求 IM 遥控支持 **QQ、飞书、微信** 三通道，其中 **QQ 与微信都支持扫码**。微信扫码（ClawBot）已随本方案落地；QQ 官方机器人平台（q.qq.com）凭证是 AppID+AppSecret，**没有扫码通道**且个人开发者难以获得企业资质。故 QQ 扫码采用个人 QQ 的事实标准接法——**OneBot v11 协议端**（NapCat / Lagrange / LLOneBot 等）：

| # | 决策 | 说明 |
|---|---|---|
| E1 | **渠道 = OneBot v11 协议端，扫码在协议端侧完成** | 用户装 NapCat 等协议端并启动，在协议端（控制台二维码或 WebUI）扫码登录自己的 QQ 号；cmx-agent 作为 OneBot v11 客户端连其**正向 WebSocket**。协议端中立（任何 OneBot v11 实现均可），不绑定 NapCat 私有 API |
| E2 | **新 kind = `onebot`**（`ImKind::Onebot`，会话前缀 `im-onebot-`） | 与官方 `qq`（openid 形态）并存不互斥，可同时启用。门户绑定表 provider 为开放字符串，存 `onebot` 免迁移 |
| E3 | **chat_id 编码会话形态**：私聊 `u<QQ号>`、群 `g<群号>` | `send()` 按前缀选 `send_private_msg` / `send_group_msg`。OneBot 无官方机器人「5 分钟/5 条被动回复」限制，可主动发、长回合慢慢回 |
| E4 | **群聊仅响应 @机器人**：at 段 `qq == self_id`（事件自带 `self_id`，@全体不算） | 群聊不 @ 不响应，避免接闲聊。正文剥净 CQ 码（`strip_cq_codes`） |
| E5 | **`message` 两形态都容**：段数组（text/at 段）与 CQ 码字符串（退 `raw_message`） | OneBot 实现各异，解析全程防御式；仅文本，纯图/语音 v1 忽略 |
| E6 | **API 调用 = echo 关联 + 15s 超时** | 上行 `{"action","params","echo"}`；下行 echo 命中 pending 表 → oneshot 送还（`retcode 0/1` 为成功，1=async 受理）。连接断开时统一唤醒等待方 |
| E7 | **鉴权双发**：URL 拼 `?access_token=` + `Authorization: Bearer` 头 | OneBot v11 标准允许头或 query 其一，双发兼容各家协议端实现 |
| E8 | **依赖零新增** | 复用 `tokio-tungstenite` / `futures-util` / `serde_json`，与 qq.rs 同栈 |

### 改动清单（文件级）

| # | 文件 | 动作 | 内容 |
|---|---|---|---|
| 1 | `crates/cmx-agent-im/src/onebot.rs` | **新增 ~700 行** | OnebotProvider（正向 WS 常驻 task：代际/停止信号/3s 重连退避与 qq.rs 同构；`call_api` echo 关联；`get_login_info` 连接即验登录）+ `parse_onebot_event` / `extract_text_and_at` / `strip_cq_codes` / `send_params` / `ws_url_with_token` 纯函数 + `test_qq_onebot` 预检（连 WS → get_login_info → 「✓ 已登录 QQ：昵称（号）」）+ 11 个内嵌单测 |
| 2 | `crates/cmx-agent-im/src/config.rs` | 修改 | `ImKind::Onebot` + `label()`/`parse_kind`/`build_provider` 分支（env：`CMX_AGENT_IM_ONEBOT_WS` 必需 + `_TOKEN` 可选）+ 头注释 |
| 3 | `crates/cmx-agent-im/src/remocon.rs` | 修改 | `OnebotCreds { ws_url, access_token, bot_uin }` + `ImRemoconConfig.onebot`（serde default 兼容旧文件）+ `masked()` 三字段 + `resolve_one` 分支（缺 WS 地址 fail-closed 带指引）+ 3 处测试 |
| 4 | `crates/cmx-agent-im/src/lib.rs` | 修改 | `mod onebot` + `OnebotProvider`/`OnebotInbound`/`OnebotCreds`/`test_qq_onebot` 导出 + 头注释 |
| 5 | `crates/cmx-agent-im/tests/onebot_tests.rs` | **新增** | 6 个桥集成测试（跑回合 / 白名单拦截 / 会话复用 `im-onebot-*` / 绑定模式三例），口径对齐 qq/wechat_tests |
| 6 | `crates/cmx-agent-shell/src-tauri/src/main.rs` | 修改 | `im_config` get 默认 JSON 补 onebot 三字段；set 补 `onebot_ws`/`onebot_bot_uin`/`onebot_token keep\|set`；启用态校验加 onebot 缺 WS 地址分支 |
| 7 | `crates/cmx-agent-web/ui/`（真源；`sync-ui.sh` 已同步） | 修改 | IM 面板左列加「QQ 个人号」卡片：协议端 WS 地址（明文）+ Access Token（锁交互）+ 扫码接入三步引导文案；`im.js` 通道表/回显/锁/保存 payload；`main.js` 注册 `scfgObLock` |
| 8 | `crates/cmx-agent-cli/src/main.rs` | 修改 | 仅头注释 env 文档补 onebot（`im` 模式走 `resolve()` 自动获得新通道，零代码改动） |

### 用户操作路径（QQ 个人号·扫码）

1. 安装并启动 NapCat（<https://github.com/NapNeko/NapCat>，Shell/Framework 均可），开启 OneBot **正向 WS** 服务（默认如 `ws://127.0.0.1:3001`；设了 access_token 则记下）。
2. 在 NapCat 出二维码处（控制台或其 WebUI）用手机 QQ **扫码登录**（二维码过期可重扫）。
3. TrueMate → 设置 → IM 遥控 → 「QQ 个人号」卡片：填 WS 地址（+token），勾选启用，保存即上线（热重载）。
4. QQ 私聊该 QQ 号发消息即遥控；群聊须 @它。可用 `test_qq_onebot` 预检（返回已登录 QQ 号即通）。

### 验证结果（追加后）

- `cargo test --offline`：**347 passed / 0 failed**（325 + 新增 onebot 单测 11 + 桥集成 6 + remocon/config 断言扩展）
- `cargo clippy --offline --all-targets`：**零告警**（EXIT=0）
- `crates/cmx-agent-shell/src-tauri` 独立 workspace `cargo check --offline`：零告警通过
- `sync-ui.sh`：UI 真源已同步 Tauri 侧
- 真机验收（NapCat 扫码 → 私聊/群@ 遥控端到端）：**待用户执行**

### 已知边界（v1）

- 仅文本收发：图片/语音/表情/引用忽略；语音转写、媒体收发排后续。
- `get_login_info` 只在连接建立时验一次（失败仅 warn 不阻塞重连）——协议端掉线重连后由重连路径自动再验。
- 扫码界面在协议端侧（NapCat），TrueMate 面板内不代理扫码——NapCat WebUI 登录 API 无公开稳定文档，绑定单一实现反而脆弱；面板以引导文案 + WS 配置 + 测试连接构成闭环。

---

## 附三：真机 ret=-1 纠偏 + 通道收敛（2026-09-11，同日三次追加）

### 一、真机故障：`im tick 出错：getupdates ret=-1 msg=`

用户真机扫码后 getupdates 持续报 `ret=-1 msg=`。根因 = **响应包结构判读与官方实现不符**（即 §10-R1 预警的字段出入）。已下载官方 `@tencent-weixin/openclaw-weixin` **v2.4.8**（社区文档基于 v2.1.1，已滞后多版）逐行核对，四处偏差：

| # | 偏差点 | 原实现（照社区文档 v2.1.1） | 官方 v2.4.8 实况 | 纠偏 |
|---|---|---|---|---|
| F1 | **响应判读** | `ret` 取不到兜底 `-1` 视为失败 | `isApiError = (ret!==undefined && ret!==0) \|\| (errcode!==undefined && errcode!==0)`（monitor.js）——**ret 缺失 = 成功**（长轮询空转正常响应无 ret 字段） | `classify_response()` 纯函数复刻官方语义；**这就是 ret=-1 误报的根因** |
| F2 | **base_info** | `{"channel_version":"2.1.1"}` | `channel_version` = 包版本（2.4.8）；**2.3.1 起新增 `bot_agent`**（UA 风格，官方缺省回落 `"OpenClaw"`） | 版本升 `2.4.8` + 补 `bot_agent:"OpenClaw"` |
| F3 | **-14 语义** | 会话超时 | 2.4.6 起改名 `STALE_TOKEN_ERRCODE` = **token 失效** | 提示语改为「token 已失效…请重新 im-login 扫码」，暂停 1h 不变 |
| F4 | **sendmessage 响应** | 假定无响应体，只看 HTTP 状态 | 2.4.6 起回 JSON `{ret, errmsg}`，ret 非零 = 拒收（HTTP 仍 200） | send 解析响应体（空体/非 JSON 容忍），ret 非零报错带 code/msg |

另两处对照确认无偏差：`iLink-App-Id` 官方也取 `"bot"`（package.json `ilink_appid`）；`X-WECHAT-UIN` 编码算法一致。错误信息现在带**原始响应片段（截断 200 字）**作诊断面包屑——iLink 无公开文档，后续字段出入用户贴日志即可定位（R1 缓解措施升级）。

新增 `classify_response`/`ResponseVerdict` 单测（含真机回归形态：无 ret 的空轮响应判成功）。改动文件：`wechat.rs`（判读/base_info/send/头注释/单测）、`remocon.rs`（`test_wechat` 判读同步）。

### 二、通道收敛：下线 Telegram 与 QQ 个人号（用户拍板）

IM 通道收敛为 **飞书 / QQ 官方机器人 / 微信（扫码）** 三通道。同日上一版追加的 QQ 个人号（OneBot v11）provider 连同 Telegram provider 一并移除：

| 文件 | 处理 |
|---|---|
| `src/telegram.rs`、`src/onebot.rs`、`tests/onebot_tests.rs` | **删除** |
| `config.rs` | `ImKind` 收敛为 `Feishu/Qq/Wechat`；默认 kind 空串 → `feishu`（原 telegram）；`parse_kind` 对 `telegram`/`onebot` 返回 Err（旧 im.json 的 `active` 列表读入时自动过滤，不炸） |
| `remocon.rs` | `TelegramCreds`/`OnebotCreds` 删除；旧 im.json 里的 `telegram`/`onebot` 字段被 serde 静默忽略，无需迁移；`masked`/`resolve_one`/测试同步收敛 |
| `lib.rs` / CLI 头注释 | 导出与 env 文档同步（env 清单：`CMX_AGENT_IM_FEISHU_*` / `CMX_AGENT_IM_QQ_*` / `CMX_AGENT_IM_WECHAT_*`） |
| 壳 `main.rs` | `im_config` get 默认 JSON / set 字段处理 / 启用态校验同步收敛 |
| UI（真源 + sync-ui） | Telegram / QQ 个人号卡片与锁逻辑删除，面板回到三通道 |

QQ 扫码诉求结论：QQ 官方机器人平台凭证只有 AppID+Secret（平台无扫码通道）；个人 QQ 扫码需第三方协议端（NapCat 等），本期不接入。若将来要接，参照 `git log` 本版历史（onebot.rs 已实现过完整 OneBot v11 正向 WS provider，可按需恢复）。

### 三、验证结果（本轮）

- `cargo test --offline`：**328 passed / 0 failed**（46 套件）
- `cargo clippy --offline --all-targets`：**零告警**
- 桌面壳独立 workspace `cargo check --offline`：通过
- `sync-ui.sh`：UI 双侧已同步
- **真机复验待用户执行**：重启桌面壳（或重跑 CLI）后，微信通道应不再出现 `ret=-1` 误报；如仍有报错，日志会带原始响应片段，贴回即可继续定位。

---

## 附四：QQ 机器人官方扫码通道（2026-09-11，同日四次追加）

### 一、查证结论（推翻附三「平台无扫码通道」的判断）

用户指出「QQ 机器人官方现在建议优先用扫码」。经查证属实：QQ 开放平台为 **OpenClaw 场景**开放了官方扫码入口（`q.qq.com/qqbot/openclaw/login.html`），**手机 QQ 扫码即可创建/绑定机器人并自动下发 AppID/AppSecret**——免开发者注册、免企业资质、免费，一个 QQ 号最多创建 5 个机器人。AstrBot / OpenClaw / Qwen Code 等均已实现该扫码授权。凭证拿到后仍走官方标准 WebSocket 接入，**`QqProvider` 协议层零改动**。

**协议事实底座**（来源：官方扫码页前端 JS 的 `/lite/*` 端点族 + AstrBot `qqofficial/login_registration.py` 交叉核对，2026-09-11 抓取）：

| 步骤 | 端点 / 内容 | 说明 |
|---|---|---|
| ① 创建绑定任务 | `POST https://q.qq.com/lite/create_bind_task`，body `{"key":"<bind_key>"}` | `bind_key` = 客户端自生成 `base64(32B)`（AES-256 密钥，只存客户端）。响应 `{"retcode":0,"data":{"task_id":"…"}}` |
| ② 二维码内容 | `https://q.qq.com/qqbot/openclaw/connect.html?task_id=<task_id>&_wv=2` | **授权页 URL（非图片）**，前端渲染成二维码；手机 QQ 扫码打开并确认 |
| ③ 轮询结果 | `POST https://q.qq.com/lite/poll_bind_result`，body `{"task_id":"…"}` | `{"retcode":0,"data":{"status":N,"bot_appid":"…","bot_encrypt_secret":"…"}}`；status 0 NONE / 1 PENDING / **2 COMPLETED** / 3 EXPIRED |
| ④ 解密 secret | `base64(payload) = nonce(12B) \| ct \| tag(16B)`，AES-256-GCM，key=`base64_decode(bind_key)` | 明文即 AppSecret |
| 信封 | `retcode` 存在且 ≠0 → 失败（`msg`/`message`） | 防御式：无 retcode 按 data 域解析 |

### 二、实施记录

| # | 文件 | 改动 |
|---|---|---|
| 1 | `crates/cmx-agent-im/src/qqlogin.rs` | **新增 ~330 行**：`create_bind_task` / `poll_bind_result` / `connect_url` / `generate_bind_key` / `decrypt_secret`（AES-256-GCM，`Nonce::from_slice` + attached `ct\|\|tag` 形态）/ `parse_envelope` / `parse_poll_result` 纯函数锚点 + 8 个单测（roundtrip / 坏输入 / 四态解析 / 信封判读） |
| 2 | `crates/cmx-agent-im/Cargo.toml` | +`aes-gcm = "0.10"`（0.10.3 及 ghash 等传递依赖离线缓存命中，`cargo check --offline` 通过） |
| 3 | `crates/cmx-agent-im/src/lib.rs` | `mod qqlogin` + `QqBindEvent/QqBindSession/…` 导出 |
| 4 | 壳 `main.rs` | 新增 `im_qq_login` Tauri command（`start`=创建任务返回授权页 URL；`poll`=轮询，Pending 放回槽、Expired 终态错误、Completed 解密落盘 im.json `qq` 字段 + 追加 active + 热重载）；`QQ_BIND` 会话槽与微信扫码同款分步驱动；poll 网络抖动放回会话返回 waiting（不当终态，避免打死正常登录） |
| 5 | UI（真源 + sync-ui） | QQ 卡片新增「扫码登录」按钮 + 二维码展示 + 状态行；`renderQr` 抽为 `scfgRenderQr` 微信/QQ 共用；`scfgQqLogin()` 2s 轮询；confirmed 自动勾选 QQ 通道 + AppID 回填；卡片文案改为「官方推荐扫码，免开发者注册」 |

### 三、验证与边界

- `cargo test --offline`：**336 passed / 0 failed**；clippy 零告警；桌面壳 workspace check 零告警；UI 双侧同步。
- 真机验收待用户：面板点「扫码登录」→ 手机 QQ 扫码确认 → 凭证自动落盘 → QQ 通道上线。
- 边界：正式环境 QQ 平台要求部署 IP 白名单（收发消息的出口 IP）；主动消息可能被 QQ 拦截（用户近期无互动时）——与现有 QqProvider 行为一致，扫码只改变凭证获取方式。
