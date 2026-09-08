# 前端复用规范

> 本文件整合自原根目录 `FRONTEND_CONVENTIONS.md`，作为 cmx-components-guide 技能的 reference。
> 覆盖范围：`cmx-portal-manager`（门户管理 / UI5）、`packages/cmx-data-comp`（共享数据组件库）、`cmx-html-designer`（HTML 设计器）。
> `cmx-portal` / `cmx-devops` 是独立 Git 子仓库，各有自己的 AGENTS.md，本文件不约束它们。
>
> **何时读**：涉及跨组件复用红线、div 自建白名单、apiFetch 后端通信、UI5 装载规范、ESLint 强制项、展示组件迁移受阻时。

---

## 一、总则：复用优先，禁止重复封装

1. **新增能力前先查现有封装。** 写任何"对话框 / 提示 / HTTP / 校验 / 转义 / UI5 注册"逻辑前，先查本文件第二节清单——大概率已经封装好了。
2. **同一逻辑只允许存在一份实现。** 如果两个类需要同一套方法，抽成 `src/lib/*.js` 的普通函数 `export`，两边 `import` 调用；**禁止各自内联一份**，禁止用继承/mixin 来"共享"（本仓库主导模式是纯函数模块，无 mixin 先例）。
3. **cmx-data-comp 是封装源头。** 改它的导出 API 会影响全前端，需评审；消费方按需 `import { X } from 'cmx-data-comp/lib/xxx.js'`。

---

## 二、封装清单（按场景）

> 组件本体（CmxFloatingDialog / showCmxMessage / CmxUi5Form.validate / 表格列模型）的完整配置项见本技能其他 reference（`dialog-message.md` / `form-components.md`）。本节只列**不在组件 reference 里的领域封装与基础设施**。

### 1. 后端通信 → `apiFetch`

**路径**：`packages/cmx-ui5-runtime/src/api-client.js`（2026-08-27 A-02 收敛，Portal / Designer 两端 alias 共享同一实现；原 Portal 本地副本已删）
**何时用**：应用源码（Portal / Designer）对接 cmx-container 后端。**原生页面（native-pages）不走这里**——用 barrel 全局的 `apiJson` / `apiGet` / `apiPost`（见 `page-helpers.md`）。

```js
import { apiGet, apiPost, apiDelete, apiFetch } from 'cmx-ui5-runtime/api-client'

const data = await apiGet('/api/domains')        // 自动解 ApiResp 信封，成功返回 data
await apiPost('/api/definitions/config', body)   // 自动 JSON + token
await apiDelete(`/api/x/${id}`)
// rawResponse:true 用于下载等二进制场景
```

**重要**：`main.js` 已调 `installAuthFetchInterceptor()` 全局 patch `window.fetch`——所有同源 `/api/*` 的裸 `fetch()` 会自动带 token、拆 ApiResp 信封、401 跳登录。所以存量裸 `fetch('/api/...')` 能正常工作；但**新代码应直接用 `apiFetch`**，避免手写 `res.json()` + `_httpError` 组装。

### 2. 定义中心错误封装 → `notify.js`

**路径**：`../../../../cmx-portal-manager`
**何时用**：定义中心（PortalDefinitionManager/List）展示后端错误。这是 `showCmxMessage` + 后端错误组装的领域封装，复用它，别再造 `_showError`/`_showWarn`/`_httpError`。

```js
import { showDefError, showDefWarn, buildHttpError, extractErrorDetails } from '../lib/notify.js'
```

### 3. HTML / 属性转义 → `escHtml` / `escAttr` / `escAttrHtml`

**路径**：`../../../../cmx-portal-manager`

| 函数 | 转义字符 | 用于 |
|---|---|---|
| `escHtml(s)` | `& < >` | **文本节点**上下文：`<span>${escHtml(name)}</span>` |
| `escAttr(s)` | `& < > "` | **属性值**上下文：`value="${escAttr(v)}"` |
| `escAttrHtml(s)` | `& < > " '` | 属性值且需防单引号（少见） |

> ESLint 已强制禁止内联定义这三个函数（`no-restricted-syntax` error），必须 `import`。详见 `common-mistakes.md` 陷阱 3。

### 4. UI5 注册 → `ensureCmxUi5Runtime`

**路径**：`packages/cmx-ui5-runtime/src/client.js`（`main.js` 已调用）
**约束**：UI5 组件注册统一走 runtime bundle，业务组件只需 `import '@ui5/webcomponents/dist/Input.js'` 声明依赖（按需引入，不重复加载）。**禁止**在业务组件里 `boot()` 或 `import bundle.esm`。

### 5. cmx-data-comp lib 导航（按需 import）

- 对话框拖拽/缩放/居中：`cmx-dialog-interact.js`（`wireDialogBoxDrag/Resize`、`centerDialogBox`）、`dialog-center.js`（`openDialogCentered`）
- 存储服务错误展示：`cmx-doc-error-presenter.js`（`presentDocError`、`describeDocError`）
- 列模型：`CmxColumnModel`、`buildColumnModel`、`registerColumnPreset`
- 元模型：`CmxDCTMeta`、`CmxDOCMeta`、`loadMetaBatch`
- DOC 坐标：`normalizeDocCoord`、`docCoordQuery`、`resolveCoord`
- 主从协调：`CmxMasterSlave`、`CmxDataSet`、`loadDocData`/`saveDocData`
- 展示组件（面板/工具条/状态标签/空状态/键值清单/筛选条/统计卡）：`cmx-panel`/`cmx-toolbar`/`cmx-status-tag`/`cmx-empty-state`/`cmx-desc-list`/`cmx-filter-bar`/`cmx-kpi-card`，import 即自注册自定义元素，直接写标签用（强制使用，禁止手搓，配置见 `display-components.md`，红线见本文件第三节）

### 6. 时间显示 → `cmx.datetime`（cmx-shared，硬性规范）

**真源**：`packages/cmx-shared/src/datetime.js`（宿主入口 import 副作用挂 `globalThis.cmx.datetime`；组件库源码内用 `import { parseDate, getParts } from 'cmx-shared/datetime'`）。**规范级硬约束**：所有面向用户的时间展示（native-pages / html-pages pageFns / 门户与设计器源码 / 组件内格式化）必须遵守本节；评审一票否决。

**背景**：后端时间一律 UTC ISO（chrono `to_rfc3339`，如 `2026-09-03T16:43:38.238813+00:00`）。显示前必须转**浏览器当前时区**（或显式 tz），`slice`/`replace('T')` 截取 = UTC 冒充本地（差一个时区偏移，评审一票否决）。

**页面接入**（native-pages / html-pages pageFns 统一 4 行标准片段）：

```js
/* 时间显示统一走 cmx-shared 注册的 globalThis.cmx.datetime（转当前时区，禁截取 ISO 串）；未装配时降级显示原文 */
const __CMX_DT = (typeof globalThis !== 'undefined' && globalThis.cmx && globalThis.cmx.datetime) || null
const fmtT = (t) => (__CMX_DT ? __CMX_DT.fmtDateTime(t) : (t ? String(t) : ''))   // 年月日 时分秒
const fmtD = (t) => (__CMX_DT ? __CMX_DT.fmtDate(t) : (t ? String(t) : ''))       // 年月日
```

**API 一览**（第二参统一 `opts = { tz?: IANA 时区名, empty?: 空值占位（默认 ''） }`）：

| 函数 | 输出 | 场景 |
|---|---|---|
| `fmtDateTime(t, opts)` | `YYYY-MM-DD HH:mm:ss` | 表格/详情默认 |
| `fmtDate` / `fmtTime` | `YYYY-MM-DD` / `HH:mm:ss` | 纯日期 / 纯时间 |
| `fmtMinute` | `YYYY-MM-DD HH:mm` | 列表紧凑列 |
| `fmtDateTimeMs` | `YYYY-MM-DD HH:mm:ss.SSS` | 日志/事件排障 |
| `fmtShort` | `MM-DD HH:mm` | 卡片/徽标 |
| `fmtFriendly` | 今天 `HH:mm`；今年 `MM-DD HH:mm`；跨年 `YYYY-MM-DD` | 智能短格式 |
| `fmtRelative` | 刚刚 / n 分钟前 / 昨天 HH:mm / … | 相对时间 |
| `fmtDuration(ms, opts)` / `fmtDurationBetween(a, b)` | `2d 3h 5m` | 时长/耗时 |
| `parseDate(t)` | `Date \| null`（date-only 按本地午夜；无时区串按 UTC；微秒截断兼容 Safari） | 高级用法 |
| `getParts(d, tz)` | `{year,month,day,hour,minute,second}` | 自定义拼接 |

**解析口径**（parseDate）：带 `Z`/`±HH:MM` 按其时区；**无时区后缀按 UTC**（CMX 后端全 UTC 存储约定）；date-only 按本地午夜（修正 ES 规范按 UTC 解析的偏移）。

---

## 三、红线（禁止项）

| ❌ 禁止 | ✅ 应改用 |
|---|---|
| 自造拖拽 / 居中 / 遮罩对话框（手写 `position:fixed` + shadow DOM） | `CmxFloatingDialog`（已内置） |
| 在 CmxFloatingDialog 内容区自画底部按钮（`showConfirm:false` + 表单内 `<ui5-button>`） | 内置 `showConfirm`/`showCancel`/`buttons`（统一底部栏，按钮在最右）；需校验拦截用 `beforeClose` 钩子 |
| 各组件自定义 `_showError` / `_showWarn` / `_httpError` | `showDefError`/`showDefWarn`/`buildHttpError`（`src/lib/notify.js`）或直接 `showCmxMessage` |
| 原生 `alert()` / `confirm()` / `prompt()` | `showCmxMessage`（信息类）/ `cmxConfirm`（确定/取消二选一，返回 `Promise<boolean>`）/ `CmxFloatingDialog`（表单类） |
| 内联定义 `escHtml` / `escAttr` / `escAttrHtml` | `import { escHtml, escAttr } from '../lib/escape.js'` |
| 组件内 `boot()` / `import bundle.esm` | `ensureCmxUi5Runtime`（main.js 已调） |
| 裸 `el.innerHTML = dynamicValue` | `escHtml`/`escAttr` 转义后赋值，或 `textContent` / DOM API |
| 手搓 `position:fixed` + `translateX` 侧滑抽屉 | `CmxFloatingDialog` 的 dock 模式（`configure({ dock: 'right'\|'left' })`） |
| 手搓 `.panel`/`.empty`/`.chip`/`.badge`/`.kv`/`.acct-kpi` 等展示碎片 | 展示组件（`cmx-panel`/`cmx-empty-state`/`cmx-status-tag`/`cmx-desc-list`/`cmx-kpi-card`，配置见 `display-components.md`） |
| 时间显示 `slice(0,10/16/19)` / `replace('T',' ')` / `substr` 截取 UTC ISO 串 | `cmx.datetime`（`fmtDateTime`/`fmtDate`/…，见上文 §二.6；转当前时区，禁截取） |

---

## 四、ESLint 强制项（CMXPortalManager）

`eslint.config.js` 的 `no-restricted-syntax`（error 级）已强制以下红线，提交前 `npx eslint "src/**/*.js"` 必须 0 error：

1. 裸 `innerHTML =` / `outerHTML =` / `insertAdjacentHTML(...)` / `document.write(...)`
2. `eval(...)` / `new Function(...)`
3. 内联定义 `escHtml` / `escAttr` / `escAttrHtml`
4. 原生 `alert(...)` / `confirm(...)` / `prompt(...)`

> "禁止自造对话框组件"属抽象行为，AST 无法识别，靠本文件约束 + 评审。

**豁免**：`src/ai-workbench/**`（Lit 组件，innerHTML 受框架管控）、`src/lib/escape.js`（权威定义所在）、`vite.config.js`、`eslint.config.js` 已整体豁免 `no-restricted-syntax`。

**注意**：验证 lint 直接用 `npx eslint "src/**/*.js"`。

---

## 五、组件分层与选型优先级（含业务 HTML 页面）

遇到一个界面需求，**从上到下**选第一个命中的层：

| 优先级 | 层 | 来源 | 什么时候用 |
| --- | --- | --- | --- |
| ① 最高 | **cmx-data-comp 业务组件**（`cmx-` 前缀） | `packages/cmx-data-comp/src/components/` | 有对应 cmx 封装时，必须用。业务语义优先（表格/表单/字典选择/对话框/分割面板/编辑器） |
| ② | **cmx-data-comp 数据模型与工具**（非可视） | `packages/cmx-data-comp/src/lib/` | 数据建模/装载/校验/消息对话框函数，复用既有封装，禁止重复造 |
| ③ | **UI5 Web Components**（`ui5-` 前缀） | `@ui5/webcomponents` 2.x，经 `packages/cmx-ui5-runtime` 统一装载 | cmx 没封装的通用控件（按钮/输入/下拉/日期/工具条/面板/消息条/toast 等）用 UI5 原生 |
| ④ | **IgniteUI 薄封装**（`cmx-ignite-*`） | `packages/cmx-data-comp/src/components/ignite/` | 仅当 UI5 与 cmx 都不满足、且 IgniteUI 有更合适组件时（设计器「Ignite 全组件」分组下 38 个） |
| ⑤ 最低 | **`div` / 原生标签自建** | — | 仅当 ①②③④ 都没有对应能力，且属于第六节白名单 |

**cmx 可视组件速查**：完整分类速查表、选型决策树 -> 本技能 [`../SKILL.md`](../SKILL.md) 第一节 / 第二节。

**UI5 版本约定**：全栈 `@ui5/webcomponents` `^2.23.2`，经 `packages/cmx-ui5-runtime` 统一 `boot()` 装载；业务代码只按需 `import '@ui5/webcomponents/dist/Xxx.js'`，禁止 `boot()`/`import bundle.esm`（与第二节 4、第三节红线一致）。**导出业务页**（`cmx-container/assets/portal/data/html-pages/sources/`，运行在 pageview iframe）经 importmap + CDN 装载，`../../../../cmx-html-designer` 拼的 importmap 版本须与运行时一致，发现漂移（如 2.22.0 vs 2.23.2）立即对齐。UI5 允许标签清单以 `../../../../cmx-html-designer` + `fiori/*.json`（约 150 个）为准。

**判定流程**：需求 → 查 cmx 速查有没有 → 没有则查 UI5 允许清单 → 还没有才考虑自建，并核对第六节白名单。

---

## 六、`div` / 原生标签自建白名单（仅下列场景允许）

下列场景 UI5 与 cmx **确实没有对应封装**，允许 `div` / 原生标签自建，但须遵循约定样式名，不得每页自创 class：

1. **页面骨架布局容器**：根级 `display:flex` 包裹（如顶部 `ui5-bar` + 内容区 grid 的纵向 flex 容器）。合理，但「上下分区」场景应优先用 `cmx-split-pane`。
2. **品牌主题装饰条**（如 `neo-meta-strip` / `neo-lane`）：属设计语言层皮肤，保留但文档化为主题约定，不计入通用组件。

**不在白名单的，禁止自建**——典型违规见第三节红线。补充几条业务页高频违规（CMXPortalManager 外的场景）：

- ❌ **原生 `<button>` 模拟按钮** → 用 `ui5-button`（业务页原生 `<button>` 现状 36 处，须逐步收敛）。
- ❌ **原生 `<select>`** → 用 `ui5-select` + `ui5-option`（业务页 4 页混用，须统一）。
- ❌ **`div[role=toolbar]` + 原生 button 堆工具条** → 用 `cmx-toolbar` + slot 放 `ui5-button`，或做成 `cmx-revo-grid` 的工具条插槽。
- ❌ **`div` 手搓模态/右侧抽屉**（`position:fixed` + overlay + `translateX`）→ 用 `cmx-floating-dialog`（dock 模式贴边抽屉）/ `ui5-dialog`。
- ❌ **手搓 `.empty`/`.chip`/`.badge`/`.kv`/`.panel`/`.acct-kpi` 展示碎片** → 用展示组件（`cmx-empty-state`/`cmx-status-tag`/`cmx-desc-list`/`cmx-panel`/`cmx-kpi-card`，配置见 `display-components.md`）。

---

## 七、展示组件迁移受阻项（已知约束，需配套方案）

> 展示组件（`cmx-panel`/`cmx-toolbar`/`cmx-status-tag`/`cmx-empty-state`/`cmx-desc-list`/`cmx-filter-bar`/`cmx-kpi-card`）+ `cmxConfirm` + `cmx-floating-dialog` dock 模式均已开发完成，强制使用（红线见第三节，配置项见 `display-components.md` 与 `dialog-message.md`）。
>
> 下列手搓模式因架构约束暂不能直接替换，需配套改动后迁移：

| 受阻模式 | 阻碍因素 | 配套方案 |
| --- | --- | --- |
| html-page 的 `.de-toolbar`/命令条 | pageFns 用 `host.shadowRoot.querySelector('#btnXxx')` 查按钮；cmx-toolbar 的 slotted 按钮成为其 light DOM 子节点，shadowRoot 查询穿透不到 | 改 pageFns 查询方式（`shadowRoot.querySelector('cmx-toolbar').querySelector(...)`），或 cmx-toolbar 提供 `getButton(id)` API |
| html-page 的 `.acct-kpi`/`.neo-kpi`/`.fico-kpi` | value 被 pageFn 通过 `getElementById('kpiXxx').textContent` 动态更新；且有设计器 `data-node-id` 序列化标记 | 改 pageFn 为 `el.value = xxx`（setAttribute）；保留 data-node-id |
| `.kv` 含 `<input>` 可编辑控件 / value 含 HTML 函数返回值 | cmx-desc-item 只支持只读文本（textContent） | 不替换；可编辑行保留原结构；或给 cmx-desc-item 加 editable 变体 |
| ai-workbench 的 `.empty`（opencode 主题） | 用 `--oc-*` token，与 cmx 的 `--sap*`/neo 主题不兼容 | 先做主题变量桥接（`--oc-*` → `--sap*`），或 cmx-empty-state 支持 opencode 皮肤 |
| 含 `<ui5-icon>` 的 badge/chip（mc-badge/ra-ctx-chip） | cmx-status-tag 只有圆点（dot），替换会丢失图标 | 给 cmx-status-tag 加 icon slot/属性 |
| CMXHTMLDesigner 的 `confirm()`/`alert()` | 设计器应用未接入 cmx 消息体系（无 cmx-message-dialog import） | 设计器 import cmx-message-dialog 后统一替换 |

补封装时遵循 `packages/cmx-data-comp` 既有风格（`customElements.define`、Shadow DOM 隔离、`package.json` 的 `exports` 登记、设计器 `cmx-data-plugin.js` 注册可拖拽、配套 `*-neo-skin.js` neo 皮肤 + 技能文档）。
