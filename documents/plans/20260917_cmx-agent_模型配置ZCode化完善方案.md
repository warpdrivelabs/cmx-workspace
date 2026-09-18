# cmx-agent 模型配置 ZCode 化完善方案

> 2026-09-17 · 状态：**P1 已实施 + E2E 自测全过（同日）**（用户 /goal「改模型配置跟报错可见性」授权；P2 未做）
> 实施补充：模板表 7 条含 custom；C 期工具失败摘要一并落地（用户指令"不要独立排期，全做"）；E2E 中修掉两个真 bug——①协议 SetModelConfig 缺 models/kind/preset/api_key_url 字段（serde 静默丢弃）且 model 未改可选；②「测试连接」按钮对新建条目不带 model（修为默认清单第一个启用项）。
> 参考对象：ZCode 桌面版（D:/ZCode，资源内 `resources/config/provider/zcode-builtin.json` + `v2/provider_config.json` + `v2/config.json` + app.asar 内 i18n 文案）

---

## 1. 背景与目标

cmx-agent（TrueMate）现有模型配置是「单 Provider 表单」形态：一个 OpenAI 兼容端点 + 一个 key + 一个模型名，能跑但小白不友好——不知道去哪拿 Key、不知道模型名填什么、填错了保存前不知道、思考功能时有时无没有解释。

ZCode 的模型配置是成熟的多供应商形态。本方案把 ZCode 的设计拆开，挑对 cmx-agent 有价值的部分分两期落地。**P1 不动模型调用协议层**（仍是 OpenAI 兼容），只完善配置体验；P2 再考虑协议扩展。

---

## 2. 现状盘点（cmx-agent）

### 2.1 数据模型（providers.json）

`crates/cmx-agent-model/src/providers.rs:16-39`：

```
ProviderFile {
  active: Option<String>,        // 激活 provider id，None=回退 DemoModel
  providers: [ NamedProvider ]
}
NamedProvider { id, name, builtin, config: {
  base_url, api_key, model, temperature(0.2), timeout_ms(60000)
}}
```

要点：
- **没有协议类型字段**：单一实现 OpenAI 兼容 `chat/completions`（`cmx-agent-model/src/openai.rs`），Provider 身份就是 base_url 字符串。
- **没有模型清单字段**：候选模型靠 base_url 关键词硬编码（`config.rs:140-161` 后端 + `ui/js/model.js:63-65` 前端两份维护），自定义 URL 无候选。
- id：内置 `builtin-mlamp`；自定义 `p-<纳秒>`。
- api_key 明文落盘（约定靠目录权限）；所有读路径脱敏（末 4 位明文）。
- 解析优先级：env > providers.json(active) > model.json（`providers.rs:292-305`）。

### 2.2 UI 入口（三处）

| 入口 | 位置 | 现状 |
| --- | --- | --- |
| 设置中心「模型」分区 | `ui/index.html:144-195` + `ui/js/model.js`（242 行） | 左列表 + 右表单（名称/预设/Base URL/Key🔒/模型 datalist/温度/超时） |
| 聊天输入框 ◎ 选择器 | `ui/js/model.js:12-57` | 按 provider 分组，点行整体切换；仅激活条目下挂硬编码候选；不列 demo |
| 子智能体「模型」下拉 | `ui/index.html:227-228` | 值 = provider id，删 provider 时引用自动置回继承默认 |

**已知缺陷**：`ui/index.html:372-428` 残留重构前的独立配置 Modal，`mcfg-*` 重复 ID 与设置分区全量冲突（`getElementById` 恰好命中靠前者才没出事），应删。

### 2.3 校验与测试

- 无任何连通性测试；仅非空/重名/存在性校验（`app.rs:847-919`），超时范围只有 HTML min/max 前端拦。
- 保存错误统一 toast「保存失败：{message}」。

### 2.4 痛点小结（本方案要解决的）

1. 小白不知道 Key 从哪来、模型 ID 填什么。
2. 填完保存才知道错没错，第一次失败发生在聊天回合里（配合报错可见性方案另文处理）。
3. 候选模型两份硬编码，换网关就失效；自定义 URL 完全没有候选。
4. 思考卡只有 glm-5.2 出内容（MLamp 网关行为），用户困惑"为什么这个模型不思考"——没有任何地方告诉他。
5. `mcfg-*` 重复 ID 隐患。

---

## 3. ZCode 参考设计拆解

ZCode 的模型配置本质是**三层结构**：

### 3.1 第一层：内置模板目录（随应用分发，revision 管理）

`zcode-builtin.json` 里 `providerConfigRules.templateRules` 共 **20 个供应商模板**（Z.ai、BigModel、Kimi、MiniMax、DeepSeek、阿里云百炼、小米 MiMo、OpenAI、Anthropic、xAI、OpenRouter、OpenCode Go/Zen…），每个模板五要素：

```json
{
  "templateId": "bigmodel-standard-api",
  "templateNameMap": { "zh-CN": "BigModel API", "en-US": "..." },
  "config": {
    "access": { "type": "api-key", "apiKeyManagementUrl": "https://bigmodel.cn/usercenter/proj-mgmt/apikeys" },
    "api":    { "type": "openai-chat-completions", "baseUrl": "https://open.bigmodel.cn/api/coding/paas/v4" },
    "builtinModelIds": ["GLM-5.3", "GLM-5.3-Flash", "..."],
    "logo": { "type": "builtin", "key": "bigmodel" }
  }
}
```

关键设计点：
- **access 与 api 解耦**：凭证类型（api-key / 编程套餐账号）与调用协议（`anthropic-messages` / `openai-chat-completions` / `openai-responses`）是两个独立维度。
- **`apiKeyManagementUrl`**：表单上直接给「获取 API Key」外链——小白不用上网搜。
- **`builtinModelIds`**：模板自带模型清单，选完模板模型列表即就位。

### 3.2 第二层：模型能力规则（声明式，按模型名正则匹配）

同文件 `modelConfigRules.modelRules`：正则 → 能力默认值。

```
.*glm-5\.3(-flash)?  → contextWindow: 1,000,000；maxOutputTokens ≤ 128,000；reasoningLevel 档位 [low, high, max]
.*glm-5\.3-flash     → 追加：输入支持 image/video/pdf
.*                   → 兜底：200k 上下文、支持 tool call、不支持图
```

能力字段：contextWindow、maxOutputTokens 上限、**reasoningLevel 档位**（disabled/enabled 或 low/high/max）、输入输出模态、tool call 支持。用户自配的模型可以补 per-provider 规则（本机实例 `provider_config.json` 里就有 `providerModelRules`：火山方舟/mlamp 的自配模型各补了 contextWindow）。

### 3.3 第三层：用户实例（本机落盘形态）

`v2/provider_config.json`（用户自建供应商）：

```json
{ "providerId": "uuid", "providerName": "mlamp",
  "config": { "group": "standard-personal",
    "access": { "type": "api-key", "apiKey": "***" },
    "api": { "type": "anthropic-messages", "baseUrl": "https://llmgw-bz.mlamp.cn" },
    "personalModelIds": ["mlamp/kimi-k3", "mlamp/glm-5.3-flash"],
    "modelOrder": ["mlamp/kimi-k3", "mlamp/glm-5.3-flash"] } }
```

`v2/config.json`（运行时投影）：provider map，每 provider 下每模型有 `reasoning {enabled, variants, defaultVariant}`、`limit {context, output}`、`modalities`、`priority`；provider 级有 `enabled` + `systemDisabledReason`（如 `coding_plan_not_entitled`）、`deletedModels`（从模板删掉的模型留痕，模板更新不复活）。

### 3.4 UI 流程（app.asar i18n 文案还原）

添加供应商 = **供应商目录（可搜索）→ 选模板或自定义端点 → API 格式三选一 → 填 Key（带「获取 API Key」外链）→ 测试连接 → 保存**。

测试体系（`settings.modelProvider.*` 文案）：
- 「测试连接」「测试模型」「正在测试 {provider} / {model}」——按 provider+model 粒度真实发请求；
- 错误分类：`auth`（认证失败）/ `network`（网络错误）/ `model_not_found`（模型未找到）/ `rate_limit`（请求频率限制）/ `server`（服务端错误）/ `noEndpoint`（未配置 endpoint）/ `unknown`；
- 「测试失败：{error}」带原文。

模型编辑：上下文窗口（校验正整数）、推理设置（档位从低到高排序、推理参数映射、校验「档位不能为空或重复」「推理参数映射无效」）、`{provider} / {model} 保存成功`、删除确认（「确定要删除{name}吗？」）。

会话内模型标识形态：`provider-id/model-id`（如 `account:bigmodel-individual-coding-plan/GLM-5.3-Flash`），可切 provider、模型、思考档位。

---

## 4. 差距对照

| 维度 | cmx-agent 现状 | ZCode 设计 | 取舍 |
| --- | --- | --- | --- |
| 调用协议 | 仅 OpenAI 兼容，无 kind 字段 | 三协议（anthropic / chat-completions / responses），模板声明 | **P2**（协议实现工作量大；当前用户全在 OpenAI 兼容网关） |
| 供应商预设 | 1 条 MLamp 硬编码（前端） | 20 模板目录：名、baseUrl、key 获取链接、预置模型、logo | **P1 做**：模板表后端化 + 目录选择，砍 logo/多语言 |
| 候选模型 | base_url 关键词硬编码 ×2 份 | 模板 builtinModelIds + 用户增删排序（modelOrder/deletedModels） | **P1 做**：models 进 providers.json，模板携带预置 |
| 模型能力 | 无 | 声明式规则（contextWindow/模态/tool call/输出上限） | **P1 做最小版**：per-model `reasoning` 标记；完整规则引擎不做（规模不匹配，过度设计） |
| 思考控制 | 无（被动解析 reasoning_content） | per-model reasoning 档位 + 默认档 | **P1 做标记展示**；请求传参 P2（需网关实测） |
| 连通性测试 | 无 | 测试连接/测试模型 + 7 类错误分类 | **P1 做**：chat 探测 + 错误分类 |
| Key 获取指引 | 无 | apiKeyManagementUrl 外链 | **P1 做**（模板携带） |
| 保存校验 | 仅非空 | + 正整数、档位合法性等 | **P1 做**：超时范围、contextWindow 正整数 |
| 模型选择器 | provider 整切，全局 active | provider+model+思考档位 | **P1 做**：模型子列表来自数据 + 思考标记；会话级覆盖 **不做**（全局 active 语义保留） |
| 可用性状态 | 无 | enabled + systemDisabledReason | 不做（无套餐体系） |
| 死代码 | 残留 Modal 重复 ID | — | **P1 删** |

---

## 5. P1 方案设计

### 5.1 数据模型扩展（providers.json，向后兼容）

```json
{
  "active": "p-xxx",
  "providers": [{
    "id": "p-xxx",
    "name": "MLamp 网关",
    "builtin": false,
    "kind": "openai",                 // 新增，默认 "openai"；P2 增 "anthropic"，反序列化缺省兼容
    "preset": "mlamp",                // 新增：来源模板 id，空=自定义
    "base_url": "https://llmgw-bz.mlamp.cn/v1",
    "api_key": "***",
    "model": "glm-5.2",               // 保留：当前使用中模型，仅由聊天 ◎ 选择器 set_model 维护，配置页不提供选择（无主模型概念）
    "models": [                       // 新增：候选模型清单（替代硬编码）
      { "id": "glm-5.2",        "reasoning": true,  "enabled": true },
      { "id": "glm-5.3-flash",  "reasoning": false, "enabled": false }
    ],
    "api_key_url": "…",               // 新增：Key 获取指引外链，空=不显示
    "temperature": 0.2,
    "timeout_ms": 60000
  }]
}
```

- 老文件读入：`merge_legacy` 补默认（kind=openai、models=[{id: model 字段值, enabled:true}]、preset/api_key_url 空、模型 enabled 缺省 true），现有 8 个单测口径不动。
- `candidate_models`（`config.rs:140-161`）与前端 `model.js:63-65` 硬编码**下线**，候选一律来自 `models` 字段。
- 模板表真源**挪到后端**（`providers.rs` 预设常量，含 name/base_url/api_key_url/models 预置），新命令 `list_provider_presets` 下发——消灭前端第二份硬编码。前端 `MCFG_PRESETS` 删除。

### 5.2 内置模板表（P1 版）

| preset id | 名称 | base_url | api_key_url | 预置模型 |
| --- | --- | --- | --- | --- |
| mlamp | MLamp 网关 | `https://llmgw-bz.mlamp.cn/v1` | （内部网关，无公开页） | glm-5.2🧠 / glm-5.3-flash / kimi-k3 / deepseek-v4-pro（对齐网关实测可得清单） |
| bigmodel | 智谱 BigModel | `https://open.bigmodel.cn/api/coding/paas/v4` | bigmodel.cn 控制台 API Keys 页 | glm-5.3🧠 / glm-5.3-flash🧠 / glm-5.2🧠 … |
| deepseek | DeepSeek | `https://api.deepseek.com/v1` | platform.deepseek.com/api_keys | deepseek-v4-pro🧠 / deepseek-v4-flash |
| dashscope | 阿里云百炼 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | bailian 控制台 | qwen 系列 |
| moonshot | 月之暗面 Kimi | `https://api.moonshot.cn/v1` | platform.kimi.com 控制台 | kimi-k3 🧠 … |
| openai | OpenAI | `https://api.openai.com/v1` | platform.openai.com/api-keys | gpt 系列 |
| custom | 自定义端点 | 空 | 空 | 空 |

🧠 = `reasoning: true`（该模型会吐思考内容，UI 显示思考标记）。模板内置 reasoning 标记即对现状「思考卡只有 glm-5.2 有内容」给出**预期管理**：选了不吐思考的模型，选择器里就有标记说明，不再神秘。

### 5.3 设置中心「模型」分区改造

新增流程：**「＋ 新增」→ 供应商目录（模板卡网格，含名称/一句话说明/模型数）→ 选模板预填 → 填 Key → 测试连接 → 保存**。

表单变化：
- API Key 行加「获取 API Key ↗」外链（`api_key_url` 非空才显示）；
- 「模型」从 datalist 改为**清单管理**：列表展示 `models[]`，支持添加/删除/重命名；每行一个**启用开关**（ZCode 同款：关闭=保留配置但不进聊天选择器）；🧠 思考标记保留；每行 🧪 单测。**不设「主模型」**——`model` 字段语义改为「当前使用中模型」，只由聊天 ◎ 选择器 `set_model` 维护，配置页不提供任何「选主模型」交互；停用/删除的恰好是当前模型时，后端自动回落到第一个启用项；
- 「高级」折叠区：温度、超时（后端补 5000–300000 范围校验，对齐现有 HTML min/max）；
- 底部「测试连接」按钮（见 5.4），保存按钮不变；
- 顺手删除 `index.html:372-428` 残留 Modal 与其 CSS。

### 5.4 测试连接（后端新命令 `test_model_config`）

- 入参：完整表单暂存配置（含明文 key，**只进内存不落盘**）或已存 provider_id；
- 探测：向 `{base_url}/chat/completions` 发 `max_tokens=1` 的一次真实请求（比 GET /models 普适——同时验证 key、URL、模型名三样；部分网关没有 /models）；
- 出参：成功 `{ok, latency_ms}`；失败 `{ok:false, err_kind, message}`，错误分类对齐 ZCode 七类：`auth / network / timeout / model_not_found / rate_limit / server / unknown`，分类逻辑与报错可见性方案（姊妹文档）的 `friendly_model_error` 共用一张映射表；
- 前端展示：「✓ 连接成功（1.2 秒）」/「✗ 认证失败：API Key 无效」（分类中文文案 + 原文折叠）。

### 5.5 聊天选择器（◎）增强

- 模型子列表改读激活 provider 的 `models[]`（**仅 enabled 项**，含 🧠 标记）；
- 每模型行点击即 `set_model`（现有语义不变，`model` 字段=当前使用中模型由这里维护）；
- 「⚙ 管理模型…」入口保留；
- 无 Key 提示保留。

### 5.6 明确不做（P1）

logo 体系、多语言名、编程套餐/账号接入（coding plan）、enabled/systemDisabledReason 状态机、会话级模型覆盖、思考档位 low/high/max（仅 true/false 两档）、模型清单排序（modelOrder/拖动，添加顺序即展示顺序）。

---

## 6. P2 展望（本次不实施，仅留接口）

1. **`kind = "anthropic"` 协议实现**：`cmx-agent-model` 新增 anthropic-messages 适配（请求/SSE 事件流格式不同）；`kind` 字段 P1 已预留。触发条件：出现只提供 anthropic 端点的网关需求（如火山方舟 coding 端点）。
2. **思考传参**：per-model reasoning 从"展示标记"升级为"请求控制"（OpenAI 兼容侧透传 `reasoning_effort`/`enable_thinking` 类参数）——**必须先对 MLamp 网关实测参数语义**，网关不认就维持现状（网关自动吐思考）。
3. **GET /models 拉取候选**：测试连接成功后提示「发现 N 个可用模型，一键导入」，导入合并进 `models[]`。
4. 会话级模型覆盖（子智能体已有 provider 引用，主会话按需扩展）。

---

## 7. 落点清单（P1）

| 层 | 文件 | 改动 |
| --- | --- | --- |
| 模型层 | `crates/cmx-agent-model/src/providers.rs` | schema 扩展（kind/preset/models/api_key_url）+ merge_legacy 兼容 + 内置模板表常量 + 单测 |
| 模型层 | `crates/cmx-agent-model/src/config.rs` | `candidate_models` 关键词硬编码下线（读 provider.models） |
| 应用层 | `crates/cmx-agent-app/src/app.rs` | `list_provider_presets` / `test_model_config` 新命令；`set_model_config` 扩展字段校验（models 结构含 enabled、timeout 范围、api_key_url 格式）；停用/删除当前模型自动回落第一个启用项；`provider_label` 改读 preset/name |
| 应用层 | `crates/cmx-agent-app/src/protocol.rs` | 新命令注册与错误码 |
| UI | `ui/index.html` | 模板目录弹层、表单改造、模型清单管理 DOM；**删 372-428 残留 Modal** |
| UI | `ui/js/model.js` | 目录选择流、清单管理逻辑、测试连接调用、预设改后端下发 |
| UI | `ui/js/main.js` / `settings.js` | data-act 接线扩展 |
| UI | `ui/css/modals.css` | 目录卡、清单管理样式（遵守双主题通路，禁硬编码色值） |
| 同步 | `sync-ui.sh` 后确认 Tauri 壳 `src-tauri/ui/` 更新 | 生成物，勿手改 |

## 8. 兼容与风险

- providers.json 老文件零迁移可用（merge_legacy 补默认）；现有 active 指针、子智能体 provider 引用语义不变。
- 测试连接发真实请求会消耗极少量 token（max_tokens=1），方案可接受；在按钮旁不提示计费（1 token 级）。
- 模板表后端常量意味着升级应用才能更新模板——可接受（ZCode 同款做法，revision 随版本走）。
- 候选模型硬编码下线后，未升级数据文件的用户首次打开设置会看到 models=[当前模型] 单条，不算回归。
- 双主题约束：新样式全走 `var(--…)` 派生，UI5/Neo 双通路验收。
