---
kind: error_handling
name: CMX 前端错误处理体系：统一 API 信封、全局拦截与分层提示
category: error_handling
scope:
    - '**'
source_files:
    - CMXPortalManager/src/lib/api-client.js
    - CMXHTMLDesigner/src/lib/api-client.js
    - CMXPortalManager/src/lib/notify.js
    - packages/cmx-data-comp/src/lib/cmx-toast.js
    - cmx-mega-sheet/src/formula/Evaluator.ts
    - cmx-mega-sheet/src/core/validation.ts
    - CMXPortalManager/src/main.js
    - CMXHTMLDesigner/src/main.js
    - CMXPortalManager/eslint.config.js
---

## 1. 整体方案

CMX 企业门户前端（Portal Manager / HTML Designer / cmx-mega-sheet）采用**「后端统一 ApiResp 信封 + 前端统一 apiFetch 解包 + 全局 fetch 拦截器 + 分层提示 UI」**的错误处理架构。核心思想是：所有网络请求通过 `api-client.js` 的 `apiFetch` 或全局 `installAuthFetchInterceptor` 发起，后端响应一律为 `{ code, msg, data }`，`code === 0` 成功，非 0 抛 Error；401 自动清 token 并跳转登录；业务错误透传 `msg`/`violations`/`detail`，由上层组件用 `showCmxMessage`/`showCmxError`/`showCmxToast` 呈现。

## 2. 关键文件与职责

- **`../../../../../cmx-portal-manager`** 与 **`../../../../../cmx-html-designer`**：两个应用各自一份，实现完全一致的 `apiFetch`/`apiGet`/`apiPost`/`apiDelete`，以及 `installAuthFetchInterceptor`。职责包括：
  - 自动注入 `Authorization: Bearer <token>`（从 `localStorage.cmx_access_token` 读取）。
  - 解析 `ApiResp` 信封：`code !== 0` 时 `throw new Error(body.msg || '业务错误 (code N)')`，成功返回 `data`。
  - HTTP 层失败（`!res.ok`）时优先取信封 `msg`/裸 `error`，否则回退到 `HTTP ${status}`。
  - 401 时 `clearTokens()` + `redirectToLogin()`（带 base-aware 的 `login.html` 回跳，防 `redirect=` 参数指数膨胀导致 414）。
  - 全局拦截器把未走 `apiFetch` 的散落 `fetch('/api/*')` 也补上 token、拆信封、转非 2xx 响应，使存量代码无需逐个改造。

- **`../../../../../cmx-portal-manager`**：定义中心共享提示工具，提供 `buildHttpError`（从 Response 构造带 `code`/`violations`/`detail` 的 Error）、`extractErrorDetails`（抽取 violations/detail 成行列表）、`notifyDef`/`showDefError`/`showDefWarn`（调用 `cmx-data-comp` 的 `showCmxMessage` 弹出模态对话框）。用于 PortalDefinitionManager / PortalDefinitionList 等组件统一错误展示。

- **`packages/cmx-data-comp/src/lib/cmx-toast.js`**：共享 UI 层错误呈现库，导出：
  - `showCmxToast(message, opts)`：右上角轻量非模态 toast，最多 5 条叠放，按 level 自动消失（info 3.5s/warning 5s/error 6s），同文案去重，支持 hover 暂停。
  - `showCmxError(title, err, opts)`：一行 catch 样板——`console.warn` + error 级 toast。
  - `installGlobalErrorToast()`：注册 `unhandledrejection`/`window error` 监听，消灭静默失败（已弹过的 `err.__presented`、AbortError、无 message 的资源加载事件不弹）。
  - `showCmxFatalScreen(title, err)`：应用启动失败全屏占位，含错误详情与「重新加载」按钮。

- **`cmx-mega-sheet/src/formula/Evaluator.ts`**：公式求值引擎内部使用 Excel 风格的 `FormulaError`（如 `#DIV/0!`、`#NAME?`、`#VALUE!`、`#NUM!`），通过 `isError()` 判断并在运算链中短路传播，不抛 JS Exception，保证表格渲染不因单个单元格错误崩溃。

- **`cmx-mega-sheet/src/core/validation.ts`**：数据验证引擎返回 `ValidationResult { ok, message? }`，失败时优先取规则定义的 `rule.error` 文案，否则用默认中文提示（如「须为整数」「不允许空值」）。

## 3. 架构与约定

| 层次 | 约定 | 说明 |
|---|---|---|
| 后端契约 | `ApiResp = { code: number, msg: string, data: T }` | `code === 0` 成功；非 0 即业务错误，`msg` 为用户可读消息 |
| 网络层 | 全部经 `apiFetch` 或全局拦截器 | 401 → 清 token + 跳登录；非 2xx → 抛 Error；信封透明拆解 |
| 错误对象 | Error.message = 用户消息；可附加 `code`/`violations`/`detail` | `notify.js` 的 `buildHttpError` 负责组装 |
| 展示层 | 模态 `showCmxMessage`（需确认/信息量大） vs 非模态 `showCmxToast`（告知即可） | ESLint 禁止裸 `alert`/`confirm`/`prompt`，强制走 cmx 组件 |
| 全局兜底 | `installGlobalErrorToast()` + `showCmxFatalScreen` | 捕获 unhandledrejection 与脚本错误，避免白屏 |
| 领域错误 | 公式层用 Excel 风格字符串错误；校验层返回 `ValidationResult` | 不抛异常，保持计算稳定性 |

## 4. 约束与规范

- **必须通过 `apiFetch`/拦截器 发起 `/api/*` 请求**：拦截器会补 token、拆信封、处理 401；直接 `fetch` 虽能命中拦截器但无法获得结构化错误。
- **401 必须清 token 并跳转登录页**：`apiFetch` 与拦截器均实现幂等的 `redirectToLogin`，防止回环与 URL 膨胀。
- **禁止原生 alert/confirm/prompt**：ESLint 规则（`../../../../../cmx-portal-manager`）明确禁止，改用 `showCmxMessage`/`CmxFloatingDialog`。
- **全局错误必须兜底**：Portal/Designer 的 `main.js` 在启动时调用 `installGlobalErrorToast()`，catch 启动失败时调用 `showCmxFatalScreen`。
- **表单/列级校验失败必须携带 violations**：后端返回 `data.violations`（含 `table`/`column`/`message`），前端 `extractErrorDetails` 将其逐行展开到对话框。
- **公式与校验不抛异常**：`Evaluator` 返回 `#NAME?`/`#DIV/0!` 等字符串错误，`validation.ts` 返回 `ok:false`，确保单格错误不影响整表渲染。
- **toast 去重与限流**：同 level+title+text 短窗内只刷新已有条目计时，最多同时显示 5 条，超出挤掉最老一条。