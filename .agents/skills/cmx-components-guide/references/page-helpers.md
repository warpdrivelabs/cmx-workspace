# 原生页面共享微工具（page-helpers）

> **何时读**：给 native-pages 写 / 改页面代码，需要 HTML 转义、JSON API 调用、toast 提示时。
> 本文件是 **原生页面侧**共享工具的唯一真源说明；应用源码（Portal / Designer）转义用 `../../../../cmx-portal-manager`，两界并存、语义见文末对照。

---

## 一、为什么原生页面要用全局 barrel 取工具

原生页面模块经 **Blob URL 动态 import**，没有裸包 import 通道（无模块图可走），唯一共享通路是运行时挂好的全局：

```js
// 页面模块顶部一次性解构（Portal 由 import-ui5-and-app.js 挂载，Designer 由 cmx-models-plugin.js 挂载，均为整 barrel）
const { escHtml, escAttr, apiJson, apiGet, apiPost, showCmxToast, showCmxError } = globalThis.__cmxDataComp
```

实现在 `packages/cmx-data-comp/src/lib/cmx-page-helpers.js`（治理清单 20260827 B-01 起收敛）。
**禁止在页面里再内联定义** `esc` / `escHtml` / `escAttr` / fetch 封装 / 自造 toast——历史上 37 份页面各写 esc（3 种语义分叉）、17 份各写 fetch、18 份各写 toast，已造成行为分叉。

---

## 二、escHtml / escAttr —— HTML 转义

```js
row.innerHTML = `<td>${escHtml(r.name)}</td>`
el.innerHTML = `<div data-code="${escAttr(r.code)}" title="${escAttr(r.name)}">…</div>`
```

- **语义（最严格集合）**：`& < > " '` 五字符全转；null / undefined 输出空串。
- `escAttr` 与 `escHtml` 同实现，双名只表达**插值上下文意图**（文本 vs 属性），便于读代码与 grep 审计。
- 替换历史宽松变体（少转 `"` 或 `'` 的旧 esc）**只会多转不少转**，文本 / 属性上下文都安全；不确定上下文时闭眼用也不会错。

## 三、apiJson / apiGet / apiPost —— 统一 fetch 封装

```js
// 通用：method / body / headers 经 options 透传
const list = await apiJson('/api/dct/entries/list', { method: 'POST', body: JSON.stringify(q) })

// GET / POST 便捷版：dbId 非空自动带 db_id 请求头（多数据源路由）
const meta = await apiGet('/api/model/dct/<code>', dbId)
const saved = await apiPost('/api/dct/save', payload, dbId)
```

行为契约（对齐历史最完整变体：信封解包 + HTTP 错误 + msg 透传）：

- ApiResp 信封 `{code,msg,data}`：`code === 0` 解包返回 `data`；无 `data` 字段的响应原样返回 body。
- `code !== 0` 抛 `Error`，文案取 `body.msg || body.error`（后端两套错误体字段名都覆盖），都没有则 `业务错误 N`。
- HTTP 非 2xx 抛 `Error`，文案取 `body.error` / `body.msg`，兜底 `HTTP <status>`。
- 错误对象挂 `.status`（HTTP 状态码）与 `.body`（响应体），调用方可分支处理。
- 默认 `credentials: 'same-origin'`；组件壳场景经第三参 `cfg` 覆盖：

```js
const cfg = {
  apiBase: '',                                // 请求前缀（门户空串 = 同源）
  fetchInit: { credentials: 'omit' },         // 整块 fetch init 默认值
  authHeaders: () => ({ Authorization: 'Bearer …' }),
}
await apiJson('/api/x', { method: 'POST', body: '{}' }, cfg)   // 页面 CFG 对象可直接传（多余键忽略）
```

## 四、toast —— 用 barrel 里的 showCmxToast / showCmxError

**不要自造 toast 元素**。barrel 已导出（`lib/cmx-toast.js`，右上角叠放 / 自动消失 / 同文案去重 / 主题自适应）：

```js
showCmxToast('保存成功', { level: 'success' })          // info | success | warning | error
showCmxToast('网络异常，稍后重试', { level: 'warning', duration: 4000 })
showCmxError('列表装载失败', err)                        // catch 样板：level=error + 提取 err.message + console.warn
```

与模态对话框的分工：要用户确认 / 信息量大（violations 明细）→ `showCmxMessage` / `cmxError`；告知即可 → toast。详见 `references/dialog-message.md`。

---

## 五、与应用侧 escape.js 的语义对照

| 实现 | 集合 | 说明 |
|------|------|------|
| 原生页 `cmx-page-helpers.js` escHtml / escAttr | `& < > " '` 全转 | 原生页面 esc 历史变体最多、插值上下文混杂，统一最保守集合（等价应用侧 escAttrHtml） |
| 应用侧 `escape.js` escHtml | `& < >` | 文本节点专用（不在属性里，不转引号） |
| 应用侧 `escape.js` escAttr | `& < > "` | 双引号属性专用 |
| 应用侧 `escape.js` escAttrHtml | `& < > " '` | 两可 / 不确定上下文 |

原生页版是应用侧三者的**超集**——任何上下文替换都只增不减，安全。两界并存的原因：应用源码有模块图（import escape.js），原生页面走 Blob URL（只能取全局 barrel），各自只有一条共享通路。
