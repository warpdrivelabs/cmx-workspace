# 对话框与消息弹窗

> 何时读：需要弹模态对话框（表单 / 左右分栏 / 自定义按钮）、信息提示（info / warning / error）、或确认弹窗时读。

> 源码：`packages/cmx-data-comp/src/components/cmx-floating-dialog.js` · `packages/cmx-data-comp/src/lib/cmx-message-dialog.js`

---

## 一、组件总览

| 组件 / 函数 | tag / 导出名 | 用途 |
|-------------|-------------|------|
| CmxFloatingDialog | `<cmx-floating-dialog>` | 通用浮层对话框（可拖拽 / 缩放 / 居中），吃实时 DOM |
| showCmxMessage | `showCmxMessage(opts)` | 信息 / 警告 / 错误 三级消息弹窗 |
| cmxInfo / cmxWarn / cmxError | 便捷别名 | 一行调用 info / warning / error 弹窗 |

---

## 二、cmx-floating-dialog

### 2.1 configure(spec) 全字段表

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `title` | `string` | `''` | 标题栏标题 |
| `icon` | `string` | `'document'` | 标题栏图标（UI5 icon name，经 safeDialogIconName 归一） |
| `description` | `string` | `''` | 标题栏副标题描述；为空时隐藏 |
| `buttons` | `Array<{id,text,icon?,design?,disabled?}>` | `undefined` | 标题栏右侧自定义按钮组 |
| `confirmText` | `string` | `'确定'` | 底部确定按钮文案 |
| `cancelText` | `string` | `'取消'` | 底部取消按钮文案 |
| `showConfirm` | `boolean` | `true` | 是否显示确定按钮；`false` 隐藏 |
| `showCancel` | `boolean` | `true` | 是否显示取消按钮；`false` 隐藏。与 showConfirm 同 false 且无 buttons 时整个 footer 折叠（`getFooterExtra()` 调用即恢复） |
| `dialogWidth` | `string` | `85vw` | 对话框宽度 CSS 值（如 `'640px'`），写入 `--dlg-w` |
| `dialogHeight` | `string` | `80vh` | 对话框高度 CSS 值（如 `'480px'`），写入 `--dlg-h` |
| `closable` | `boolean` | `false` | 标题栏右侧显示 ✕ 关闭按钮（触发 cancel，与 Esc/遮罩同语义） |
| `closeOnEsc` | `boolean` | `true` | Esc 是否可关。多层叠开时 Esc 仅关**栈顶**实例；栈顶 `false` 时该次 Esc 不被任何弹框响应 |
| `closeOnMask` | `boolean` | `true` | 点击遮罩是否可关；`false` 时遮罩仍拦截点击但不关闭 |
| `mask` | `boolean` | `true` | `false` = 非模态：遮罩透明不拦截（底层页面可操作），建议同时配 `lockScroll:false` |
| `lockScroll` | `boolean` | `true` | 打开时锁文档滚动（引用计数，多层嵌套安全；`scrollbar-gutter:stable` 防抖动） |
| `draggable` | `boolean` | `true` | 标题栏拖拽开关（dock 模式恒禁用） |
| `resizable` | `boolean` | `true` | 八方位缩放开关（dock 模式恒禁用） |
| `fullscreen` | `boolean` | `false` | 铺满视口（四周 4px 缝）；与 dock 冲突时忽略并 warn |
| `contentPadding` | `boolean\|string` | `true` | 内容区默认 padding：`true`=14px 16px / `false`=0 / CSS 串。累积合并语义：不传不改既有值，显式传 `true` 归位 |
| `zIndex` | `number` | `900` | 覆盖 host 层级（多层弹框嵌套如 help 弹在表单弹框上时用） |
| `beforeClose` | `(ctx) => boolean \| Promise<boolean>` | — | 关闭前拦截钩子（仅 confirm / button 触发） |

> **时序契约**：新属性须在**首次 appendChild 之前** configure（wiring 类属性连接后不重绑）。

`buttons` 数组每项字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `string` | 按钮标识，点击时随 `cmx-dialog-button` 事件 detail 返回 |
| `text` | `string` | 按钮文案 |
| `icon` | `string?` | UI5 icon name |
| `design` | `string?` | UI5 button design，默认 `'Transparent'` |
| `disabled` | `boolean?` | 是否禁用 |

### 2.1.x dock 抽屉模式（右侧/左侧滑入）

`configure({ dock: 'right' | 'left' })` 启用贴边抽屉模式——对话框贴右/贴左滑入、高度撑满视口、固定宽度（默认 420px，可用 `dialogWidth` 覆盖）、横向滑入动画、禁用拖拽与缩放。不设 `dock`（默认）= 居中模态（原行为）。

| dock 值 | 行为 |
|---------|------|
| 不设（默认） | 居中模态：`centerDialogBox` 设 left/top，支持拖拽 + 八方位缩放 |
| `'right'` | 右侧贴边：`right:0`、`height:100vh`、宽度 `var(--dlg-w,420px)`、`dlg-dock-right-in` 滑入动画、禁用拖拽/缩放 |
| `'left'` | 左侧贴边：`left:0`、其余同上、`dlg-dock-left-in` 滑入动画 |

> 遮罩点击 / Esc 关闭 / beforeClose / 事件派发 / `openModal` / `close` 等逻辑均与位置无关，dock 模式下行为不变。

```javascript
const dlg = document.createElement('cmx-floating-dialog')
dlg.configure({
  title: '详情', icon: 'detail-view',
  dock: 'right',          // 右侧抽屉
  dialogWidth: '440px',   // 覆盖默认 420px
  showConfirm: false,
  cancelText: '关闭',
})
dlg.setContent(contentEl)   // 或 setLeftRight / setSingleRegion
document.body.appendChild(dlg)
const result = await dlg.openModal()   // { action: 'cancel' }（点遮罩/Esc/关闭按钮）
```

### 2.2 API 方法

| 方法 | 签名 | 说明 |
|------|------|------|
| `configure(spec)` | `(spec) -> this` | 设置对话框规格；可链式调用，可多次合并 |
| `setContent(el, opts?)` | `(el, opts?: { padding?: boolean\|string }) -> this` | 注入单区实时内容（自动包入 `.dlg-content` 标准容器，见 2.2.x 布局契约） |
| `setLeftRight(leftEl, rightEl, opts)` | `(left, right, opts?) -> this` | 注入左右分栏布局（字典 help 用；不走 `.dlg-content`） |
| `setSingleRegion(el, opts)` | `(el, opts?) -> this` | 仅注入右侧单区（grid 模式，无左树；不走 `.dlg-content`） |
| `getFooterExtra()` | `() -> HTMLElement` | 底部左侧额外区（放提示/状态），可自由填充；footer 折叠态下调用即恢复显示 |
| `openModal()` | `() -> Promise<{action, buttonId?}>` | Promise 风格打开；未挂载时自动 appendChild |
| `close(action, buttonIdOrOpts, opts)` | `(action?, buttonIdOrOpts?, opts?) -> void` | 外部主动关闭 |

`setLeftRight` 的 `opts` 参数：

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `leftLabel` | `string` | `'分类'` | 左栏标题 |
| `leftIcon` | `string` | `'tree'` | 左栏图标 |
| `rightLabel` | `string` | `'数据'` | 右栏标题 |
| `rightIcon` | `string` | `'table'` | 右栏图标 |
| `leftWidth` | `number` | `240` | 左栏固定宽度（px），可拖拽调整 |

### 2.2.x 内容区布局契约（setContent 路径，重要）

`setContent(el)` 会自动把内容包入标准容器 `.dlg-content`（flex 纵向 + `flex:1` 伸展链 + **默认 padding 14px 16px**，背景透明）。使用规则：

1. **不要再给内容元素手写 padding / flex 三件套**（`flex:1 1 auto;min-width:0;box-sizing:border-box;padding:...`）——容器已提供，写了会双重 padding；
2. 普通表单/文本内容：元素**零样式要求**，自然高度即可；
3. 需要填满弹框或内部滚动的元素（`<pre>`、表格容器）：写 `flex:1; min-height:0` 两行即可；
4. 全出血（grid 铺满整个内容区）：`setContent(el, { padding: false })`；
5. 自定义 padding：`setContent(el, { padding: '10px 12px' })`（只影响本次，不改实例默认）或 `configure({ contentPadding: ... })`（实例级）；
6. **禁止 `position:absolute; inset:0` 铺内容**——内容区 `#dlg-body` 已是 `position:relative`，absolute 只能锚到内容区（标题栏以下），盖不到标题栏；需要铺满请用第 3 条的 flex 契约。

`setLeftRight` / `setSingleRegion` 走 region-body 布局，**不经 `.dlg-content`**，内容 padding 由使用方自理（保持原状）。

### 2.3 beforeClose 钩子

`beforeClose` 是 confirm / 自定义 button 动作关闭前的可拦截钩子（cancel / Esc / 遮罩点击**不触发**）。

- 返回假值（`false` / `undefined` / `null`）：中止关闭，弹窗保持可用、可再次点击。
- 返回真值（`true`）：正常关闭。
- 支持 `async`：返回 `Promise<boolean>`。
- 未注册时维持原行为（直接关闭）。
- 落盘成功后需强制关闭请用 `close(action, { force: true })`，跳过钩子。

**典型场景**：确认前做表单校验，校验不过则不关。

```javascript
dlg.configure({
  title: '编辑用户',
  beforeClose: async (ctx) => {
    if (ctx.action === 'confirm') {
      const ok = await validateForm()
      if (!ok) {
        // 校验失败，弹窗不关，用户可修正后重试
        return false
      }
      await saveUser() // 落盘成功
    }
    return true
  },
})

// 落盘成功后强制关闭（绕过 beforeClose）
// dlg.close('confirm', { force: true })
```

### 2.4 事件

所有事件 `bubbles: true, composed: true`。

| 事件名 | detail | 触发时机 |
|--------|--------|----------|
| `cmx-dialog-confirm` | `{ action: 'confirm', buttonId: undefined }` | 用户点确定按钮 |
| `cmx-dialog-cancel` | `{ action: 'cancel', buttonId: undefined }` | 取消按钮 / Esc / 遮罩点击 |
| `cmx-dialog-button` | `{ action: 'button', buttonId: string }` | 用户点自定义按钮 |

### 2.5 三种布局

| 布局 | 方法 | 说明 |
|------|------|------|
| 单区内容 | `setContent(el)` | 纯内容注入，无区域标题 |
| 单区面板 | `setSingleRegion(el, opts)` | 带区域标题（header + body），适合 grid 模式 |
| 左右分栏 | `setLeftRight(leftEl, rightEl, opts)` | 左栏固定宽可拖拽，右栏 flex；适合字典 help |

### 2.6 完整代码示例

**事件风格**：

```javascript
import 'cmx-data-comp/components/cmx-floating-dialog.js'

const dlg = document.createElement('cmx-floating-dialog')
dlg.configure({
  title: '选择部门',
  icon: 'tree',
  description: '从组织树中选择目标部门',
  dialogWidth: '720px',
  dialogHeight: '480px',
  confirmText: '确认选择',
  cancelText: '关闭',
})

// 注入左右分栏：左树 + 右表格
dlg.setLeftRight(treeEl, gridEl, {
  leftLabel: '组织架构',
  leftWidth: 260,
  rightLabel: '部门列表',
})

document.body.appendChild(dlg)

dlg.addEventListener('cmx-dialog-confirm', () => {
  console.log('用户确认')
})
dlg.addEventListener('cmx-dialog-cancel', () => {
  console.log('用户取消')
})
```

**Promise 风格（推荐）**：

```javascript
const dlg = document.createElement('cmx-floating-dialog')
dlg.configure({
  title: '编辑表单',
  dialogWidth: '600px',
  beforeClose: async (ctx) => {
    if (ctx.action !== 'confirm') return true
    const ok = await myForm.validate()
    if (!ok) return false // 校验不过，不关
    await myForm.save()
    return true
  },
})
dlg.setContent(formEl)

const result = await dlg.openModal()
// result: { action: 'confirm'|'cancel'|'button', buttonId?: string }
if (result.action === 'confirm') {
  console.log('已保存')
}
```

---

## 三、showCmxMessage / cmxWarn / cmxError / cmxInfo

### 3.1 showCmxMessage(opts)

弹出通用信息对话框（信息 / 警告 / 错误 三级）。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `level` | `'info' \| 'warning' \| 'error'` | `'info'` | 消息级别 |
| `title` | `string` | 级别名（信息/警告/错误） | 标题 |
| `message` | `string` | — | 正文（支持 `\n` 换行） |
| `details` | `string[]` | — | 明细列表，每项一行（如各条校验错误） |
| `helpCode` | `string` | — | 帮助定位码；warning/error 时显示「获取帮助」 |
| `helpUrl` | `string` | — | 帮助 URL；无门户监听时回退 `window.open` |
| `okText` | `string` | `'确定'` | 主按钮文案 |
| `allowCopy` | `boolean` | `error && details.length > 0` | 是否显示「复制详情」 |
| `onClose` | `function(how)` | — | 关闭回调，参数 `'ok'` / `'help'` |

**返回值**：`Promise<'ok' | 'help'>` — 点确定 resolve `'ok'`，点帮助 resolve `'help'`（不关闭对话框）。

level 级别配色：

| level | 图标 | 强调色（亮） | 强调色（暗） |
|-------|------|-------------|-------------|
| `info` | 信息 i | `#0a6ed1` | `#4db1ff` |
| `warning` | 三角感叹号 | `#e9730c` | `#ffab4a` |
| `error` | 圆形叉 | `#bb0000` | `#ff6d6d` |

### 3.2 便捷别名

| 别名 | 签名 | 等价于 |
|------|------|--------|
| `cmxInfo(message, opts)` | `(msg, opts?) -> Promise` | `showCmxMessage({ ...opts, level:'info', message })` |
| `cmxWarn(message, opts)` | `(msg, opts?) -> Promise` | `showCmxMessage({ ...opts, level:'warning', message })` |
| `cmxError(message, opts)` | `(msg, opts?) -> Promise` | `showCmxMessage({ ...opts, level:'error', message })` |

### 3.3 特性

- **主题自适应**：跟随门户 UI5 主题（`localStorage.__portal_ui5_theme__`）或系统 `prefers-color-scheme`，light / dark 两套配色；主题切换时已开对话框实时跟随。
- **可访问**：`role="alertdialog"`、`aria-*`、焦点锁定（Tab 循环）、ESC / 点遮罩 / 确定 三种关闭。
- **帮助机制**：warning / error 且有 `helpUrl` 或 `helpCode` 时显示「获取帮助」按钮。点击优先派发 `cmx-help-request` 事件（门户帮助中心接管），无人处理时回退 `window.open(helpUrl)`。
- **复制详情**：error 且有 details 时默认显示「复制详情」按钮，复制标题 + 正文 + 明细。

### 3.4 代码示例

```javascript
import { showCmxMessage, cmxWarn, cmxError, cmxInfo } from 'cmx-data-comp/lib/cmx-message-dialog.js'

// 基本用法
await showCmxMessage({
  level: 'error',
  title: '保存失败',
  message: '以下字段校验未通过：',
  details: [
    '• 第 3 行「金额」不能为负数',
    '• 第 7 行「日期」格式不正确',
    '• 第 12 行「编码」不能为空',
  ],
  helpCode: 'VALIDATION_ERROR',
  helpUrl: 'https://docs.example.com/errors/validation',
})

// 便捷别名
await cmxWarn('库存不足，请先补货')
await cmxError('网络请求失败，请稍后重试', { details: ['status: 500', 'url: /api/save'] })
await cmxInfo('操作已完成')
```

---

## 四、cmxConfirm（确认对话框）

确认弹窗（确定 / 取消二选一），返回 `Promise<boolean>`，替代原生 `confirm()`。

**路径**：`packages/cmx-data-comp/src/lib/cmx-message-dialog.js`（与 showCmxMessage 同文件，复用其配色 / 主题跟随 / 遮罩 / 焦点锁定基础设施）。

**与 showCmxMessage 的区别**（故独立实现）：
- 返回 boolean（true=确定，false=取消）而非关闭方式字符串；
- ESC / 点遮罩 = **取消**（决策型语义），而非 showCmxMessage 的「确定」；
- footer 是「取消 + 确定」二元按钮，`intent:'danger'` 时确定按钮红色。

### 4.1 签名

```typescript
cmxConfirm(opts: {
  title?: string,          // 默认 '确认'
  message: string,         // 正文（支持 \n 换行）
  confirmText?: string,    // 默认 '确定'（danger 时默认 '删除'）
  cancelText?: string,     // 默认 '取消'
  intent?: 'danger' | 'normal',  // danger 时主按钮红色（删除/作废）
  icon?: string,           // SVG path d 值；默认按 intent 选
}) => Promise<boolean>     // true=确定，false=取消
```

### 4.2 用法

```javascript
import { cmxConfirm } from 'cmx-data-comp/lib/cmx-message-dialog.js'

// 普通确认
if (await cmxConfirm({ message: '确定提交该单据？' })) {
  await submit()
}

// 危险确认（删除）：主按钮红色，文案默认「删除」
if (await cmxConfirm({ message: '删除后不可恢复，确定？', intent: 'danger' })) {
  await deleteRecord()
}

// 自定义文案
const ok = await cmxConfirm({
  title: '作废确认',
  message: '作废后单据状态不可逆',
  confirmText: '作废',
  cancelText: '再想想',
  intent: 'danger',
})
```

> 需要表单输入的确认（如「输入原因后确认」）仍用 `<cmx-floating-dialog>`（支持 beforeClose 拦截 + 自定义内容）。

---

## 五、红线提醒

| 禁止 | 替代方案 |
|------|----------|
| 原生 `alert()` | `cmxInfo(msg)` 或 `showCmxMessage({ level:'info' })` |
| 原生 `confirm()` | `cmxConfirm()`（返回 `Promise<boolean>`；需表单输入用 `cmx-floating-dialog`） |
| 原生 `prompt()` | `cmx-floating-dialog` + `cmx-text-input` |
| 自造拖拽 / 居中 / 遮罩对话框 | 统一用 `<cmx-floating-dialog>`（已内置拖拽、缩放、居中、遮罩、Esc 关闭） |
| 自造消息弹窗 | 统一用 `showCmxMessage` / `cmxWarn` / `cmxError` / `cmxInfo` |
