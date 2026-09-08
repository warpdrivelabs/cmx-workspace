# cmx-floating-dialog 弹框组件完善与存量页面迁移方案（v3）

> 日期：2026-08-19（v3：经子智能体两轮审查修订。R1：P0×1 / P1×6 / P2×11 全部处置；R2：发现 v2 Esc 修复方案违反 DOM 事件语义（P0）已重写为栈顶判定，另 5 项 P2 文字口径修正。见附录 B）
> 范围：`packages/cmx-data-comp`（组件增强）+ cmx-container native-pages（5 文件 10 处迁移）+ CMXPortalManager（3 文件 4 处迁移）+ 生成器技能文档同步
> 结论先行：**不新建组件**，在现有 `cmx-floating-dialog` 上做向后兼容增强（内部契约修复 + 10 个新属性 + Esc 多层语义修复），存量 14 处内容弹框同批迁移吃默认 padding；`setLeftRight/setSingleRegion` 路径、纯 description 弹框、legacy demo 均不动。

---

## 一、背景与问题

### 1.1 组件现状

`<cmx-floating-dialog>`（`packages/cmx-data-comp/src/components/cmx-floating-dialog.js`，样式真源 `src/lib/cmx-dialog-shell.js`，与 CMXPortalManager dialog-worknode 共用）结构：

```
.dlg-box（--dlg-w/--dlg-h，默认 85vw/80vh，min 480×300，flex column，overflow:hidden，白底 --sapBaseColor）
 ├─ #dlg-bar     标题区（icon + title + description；end 槽自定义按钮；拖拽手柄）
 ├─ #dlg-body    内容区（flex ROW、flex:1、overflow:hidden、灰底 --sapGroup_ContentBackground、无 padding、无 position）
 └─ #dlg-footer  底部区（footer-extra 左槽 + 取消/确定按钮右槽）
 + .dlg-resize-root（八方位缩放手柄）
```

能力：三种布局（`setContent` / `setLeftRight` / `setSingleRegion`）、`openModal()` Promise、`beforeClose` 拦截、dock 左右抽屉、拖拽 + 缩放 + Esc + 遮罩关闭。

### 1.2 已踩的四类坑（M5 分发订阅开发期实际发生）

| # | 坑 | 根因 |
| --- | --- | --- |
| 1 | 订阅编辑弹框滚动条顶到标题栏、标题栏不可拖拽 | 使用方 `position:absolute; inset:0`，但 `#dlg-body` **没有 `position:relative`**，锚到了 `.dlg-box` 连标题栏一起盖住 |
| 2 | 4 处弹框右侧空白、内容靠左 | `#dlg-body` 是 flex 行容器，注入 wrap 无伸展约定，按内容收缩 |
| 3 | payload/详情弹框底部内容被裁 | 使用方写死 `max-height:58vh`，大屏下头部开销一扣就超出内容区，被 `overflow:hidden` 裁底 |
| 4 | 各处 padding 手写漂移（12px 14px / 14px 16px / 16px / 18px 20px） | 内容区无默认 padding，无标准容器 |

**共同根因**：组件把布局责任全丢给使用方，`#dlg-body` 的容器形态是未文档化的隐含契约。

### 1.3 对照 Element Plus Dialog / Ant Design Modal+Drawer 的能力差距

| 能力 | Element Plus | Ant Design | 现状 |
| --- | --- | --- | --- |
| 标题栏 ✕ 关闭 | `show-close`（默认有） | `closable`（默认有） | ❌ 无 |
| Esc 关闭开关 | `close-on-press-escape` | `keyboard` | ❌ 恒开，且多层叠开时**一次 Esc 全关**（缺陷） |
| 遮罩点击开关 | `close-on-click-modal` | `maskClosable` | ❌ 恒开 |
| 遮罩显隐 | `modal` | `mask` | ❌ 恒有 |
| 锁 body 滚动 | `lock-scroll`（默认 true） | 内置 | ❌ 有滚动穿透 |
| 拖拽开关 | `draggable`（默认 false） | — | ❌ 恒开 |
| 缩放开关 | — | — | ❌ 恒开（特色能力，仅缺开关） |
| 全屏 | `fullscreen` | — | ❌ 无 |
| 层级 | z-index | `zIndex` | ❌ 固定 900，多层弹框层序不可控 |

已达标项：`beforeClose`（比 EP 强，支持 async）、`openModal()` Promise、宽度+高度双控、按钮文案/显隐、dock 抽屉（对标 Drawer placement）、close 即 remove（天然 destroy-on-close）、默认居中。

---

## 二、目标与原则

1. **不新建组件**：12+ 处业务使用 + `cmx-dict-select` help 内部依赖 + PortalManager dialog-worknode 共享 shell 真源，新建必然分裂两套弹框。
2. **默认行为完全向后兼容**（Esc 多层修复与 lockScroll 两处**有意的缺陷修复**除外，见 3.4 矩阵）；清单内页面同批迁移，不留双重 padding 中间态（见五、批次原子性）。
3. **坑从根上消**：布局契约下沉到组件内，使用方只管内容自身。
4. **契约制度化**：不只改组件，同步落进组件手册与页面生成器技能规范，防增量复发。

---

## 三、组件增强详细设计

### 3.1 内部契约修复（非属性，治本）

#### 3.1.1 `#dlg-body` 加 `position:relative`

`cmx-dialog-shell.js` 的 `DIALOG_SHELL_STYLES` 中 `.dlg-body` 增加 `position: relative;`。

- 效果：使用方若写 `position:absolute; inset:0`，锚定到内容区自身（标题栏以下），不再盖标题栏。
- 兼容性：`setLeftRight/setSingleRegion` 构建的 `.dlg-region` 是正常流 flex 子项，不受影响；`.dlg-region-body` 本身已有 relative，无叠加问题。已核 PortalManager 三个 worknode 消费方均为正常流注入，无 absolute 用法。

#### 3.1.2 `setContent(el, opts)` 自动标准内容容器 `.dlg-content`

**DOM 变化**（仅 `setContent` 路径；`setLeftRight` / `setSingleRegion` 不变）：

```
#dlg-body
 └─ .dlg-content            ← 新增（组件创建，shadow 样式）
     └─ el                  ← 使用方元素
```

**CSS**（加入 DIALOG_SHELL_STYLES）：

```css
.dlg-content {
  flex: 1 1 auto;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: var(--dlg-content-padding, 14px 16px);
  box-sizing: border-box;
  /* 背景 transparent：露出 #dlg-body 既有灰底，迁移页面零底色 diff */
}
.dlg-content[data-bleed="true"] { padding: 0; }
```

> 背景决策：`.dlg-content` **不加背景**（transparent）。现状 `#dlg-body` 为 `--sapGroup_ContentBackground`（#fafafa）灰底，若给 `.dlg-content` 上白底（--sapBaseColor）会造成 14 处迁移页面底色灰→白的视觉变化；透明则完全保持现状观感。

**API**：`setContent(el, opts?)`，`opts.padding`：

- `undefined`（默认）→ 用 `--dlg-content-padding`（来自 configure 的 `contentPadding`，未配置则 14px 16px）；
- `false` → `data-bleed="true"` 全出血；
- CSS padding 字符串 → **写入本次创建的 `.dlg-content` 元素自身的 style**（每次 `setContent` 重建容器，天然无实例级残留，与 configure 累积合并语义解耦）。

`configure` 的 `contentPadding`（true/false/string）作为实例级默认写在 `:host` 的 `--dlg-content-padding` 上；**注意 configure 是浅合并累积，`contentPadding` 一经设置无法通过 `configure({})` 清除，需显式传 `contentPadding: true` 或 `false` 归位**（文档标注）。opts 优先级高于 configure。

**使用方契约（迁移后）**：
- 普通表单/文本内容：元素**零样式要求**，自然高度，自动获得 padding；
- 需要填满/内部滚动的元素（如 `<pre>`、表格容器）：写 `flex:1; min-height:0`；
- 不再需要手写 `flex:1 1 auto; min-width:0; box-sizing:border-box; padding:...`。

**兼容推演**：
- 存量 wrap 带 `flex:1 1 auto; min-width:0`：在 `.dlg-content`（flex column）内是唯一子项，伸展仍生效，无害；
- 存量 wrap 自带 padding：双重 padding，**由第四节迁移同批消化**；
- `_pendingContent` 暂存路径同步携带 opts。

#### 3.1.3 空 footer 折叠

`showConfirm === false && showCancel === false &&` 未配置 `buttons` 时，`#dlg-footer` 初始 `display:none`。

恢复机制采用**调用即恢复**：折叠态下 `getFooterExtra()` 被调用时，先把 footer 切回显示再返回元素引用（不依赖 MutationObserver、不依赖"填充时机"——因为使用方必然是先拿引用后 appendChild，任何基于"返回时检测子节点"的方案在时序上都不成立）。当前全工作区无 `getFooterExtra` 业务使用方，此机制为零成本预留。

### 3.2 新增 configure 属性（10 项）

> **时序契约**：新属性（含既有全部属性）须在**首次 appendChild 之前** configure。`_wireInteract` 仅在 connectedCallback 执行一次，连接后的 configure 不会重绑拖拽/缩放；`closable` 的 ✕ 在 `_applySpec` 中按 id 查重实现幂等（多次 configure 不重复追加），但 `draggable/resizable/fullscreen/zIndex` 等不走 wiring 重绑路径的属性以"append 前配置"为准。文档统一标注。

| # | 属性 | 类型 / 默认 | 行为与实现要点 | 对标 |
| --- | --- | --- | --- | --- |
| 1 | `closable` | boolean / `false` | `true` 时 `#dlg-bar-end` 末尾追加 `ui5-icon name="decline" id="dlg-close-x"`（cursor:pointer），点击 `_emitClose('cancel')`。`_applySpec` 按 id 查重保证幂等 | EP `show-close`、antd `closable` |
| 2 | `closeOnEsc` | boolean / `true` | `false` 时该实例不响应 Esc。Esc handler 增加栈顶判定（见 3.6，监听阶段保持 bubble 不变）；栈顶实例关闭自身，非栈顶不响应；**栈顶 `closeOnEsc:false` 时整次 Esc 无任何弹框响应**（天然吞掉，不穿透关下层，与 EP 一致） | EP `close-on-press-escape`、antd `keyboard` |
| 3 | `closeOnMask` | boolean / `true` | `false` 时 `:host` pointerdown（composedPath 不含 dlg-box）不关闭；遮罩仍拦截点击 | EP `close-on-click-modal`、antd `maskClosable` |
| 4 | `mask` | boolean / `true` | `false` = **非模态**（对齐 EP `modal:false` 语义）：`:host` 加 `data-mask="false"`，由 CSS 控制背景透明 + `pointer-events:none`，`.dlg-box` 恢复 `pointer-events:auto`——底层页面可正常操作，`closeOnMask` 自然失效（点不到 host）。**建议 `mask:false` 同时配 `lockScroll:false`**（非模态却锁文档滚动，组合怪异） | EP `modal`、antd `mask` |
| 5 | `lockScroll` | boolean / `true` | 见 3.3 | EP `lock-scroll` |
| 6 | `draggable` | boolean / `true` | `false` 时 `_wireInteract` 跳过 `wireDialogBoxDrag`（`#dlg-bar` cursor 恢复 default） | EP `draggable`（EP 默认 false，此处不翻默认保兼容） |
| 7 | `resizable` | boolean / `true` | `false` 时跳过 `wireDialogBoxResize` 且 `.dlg-resize-root` 隐藏（走 data 属性由 CSS 控制） | 组件特色，仅补开关 |
| 8 | `fullscreen` | boolean / `false` | `true` 时 `.dlg-box` 加 `data-fullscreen`：`left:4px; top:4px; width:calc(100vw - 8px); height:calc(100vh - 8px)`（与既有 max-width 约束一致、四周均匀 4px 缝）、隐藏缩放手柄、跳过 `_center()` | EP `fullscreen` |
| 9 | `contentPadding` | `true` / `false` / string | `.dlg-content` 实例级默认，写 `:host` 的 `--dlg-content-padding`；`setContent` opts 可逐次覆盖（opts 写容器自身，见 3.1.2）。**累积合并下不可通过不传清除，需显式传值归位** | —（3.1.2 配套） |
| 10 | `zIndex` | number / `900` | 写 `this.style.zIndex`（`:host` 是 fixed 全屏层）。dict-select help 嵌套场景可传 1000+。层序现状盘点见附录 C | antd `zIndex` |

### 3.3 lockScroll：独立模块 + 严格配对计数

抽为**独立模块** `packages/cmx-data-comp/src/lib/cmx-scroll-lock.js`（供后续 `cmx-message-dialog`/`cmxConfirm` 家族复用，本期 floating-dialog 先接入）：

```js
// cmx-scroll-lock.js（模块级，多实例嵌套安全）
let _count = 0
let _prevHtmlOverflow = ''
let _prevHtmlGutter = ''
export function acquireScrollLock () {
  if (++_count === 1) {
    const html = document.documentElement
    _prevHtmlOverflow = html.style.overflow
    _prevHtmlGutter = html.style.scrollbarGutter
    html.style.overflow = 'hidden'                      // 锁 html（视口滚动归 html 管）
    html.style.scrollbarGutter = 'stable'               // 防经典滚动条消失的横向抖动
  }
}
export function releaseScrollLock () {
  if (_count <= 0) return
  if (--_count === 0) {
    const html = document.documentElement
    html.style.overflow = _prevHtmlOverflow
    html.style.scrollbarGutter = _prevHtmlGutter
  }
}
```

> **收益边界**：锁的是 `document.documentElement`，只消除「视口级」滚动穿透。门户布局中滚动发生在内部容器（菜单区/内容区各自 `overflow:auto`）时，鼠标悬停在这些容器上仍可滚——这是预期边界而非缺陷，6.3 冒烟包含真实门户页的滚动锁定感知验证。

**实例侧严格配对（防 reconnect 泄漏）**：`connectedCallback` 的 acquire 放在 `if (this._wired) return` 守卫**之前**，并以实例标志保证幂等：

```js
// connectedCallback 首行（_wired 守卫之前）
if (!this._scrollLocked && this._spec.lockScroll !== false) { acquireScrollLock(); this._scrollLocked = true }
// disconnectedCallback（无条件，与 _wired 无关）
if (this._scrollLocked) { releaseScrollLock(); this._scrollLocked = false }
```

> 不能把 acquire 放在 `_wired` 守卫之后：元素被移动父节点时会触发 disconnected（release）+ reconnected（守卫提前 return 不重新 acquire），导致计数提前归零、仍在显示的弹框滚动解锁。

**布局抖动**：锁滚动后 Windows 经典滚动条消失会引起页面横向跳动。方案：在锁定的同时给 `document.documentElement` 加 `scrollbar-gutter: stable`（与 overflow 一起存/恢复）；不支持该属性的浏览器（旧 Firefox）接受轻微抖动，不做测量补偿。

### 3.4 属性-行为矩阵（向后兼容证明）

| 场景 | 增强前 | 增强后（不传新属性） | 差异 |
| --- | --- | --- | --- |
| setContent 注入 | 直接进 `#dlg-body` | 进 `.dlg-content`（默认 padding，背景透明露灰底） | ⚠️ 内容区多 14px 16px padding —— **由第四节迁移同批消化** |
| absolute 锚定 | 锚到 dlg-box（bug） | 锚到 dlg-body（正确） | 修复 |
| showConfirm/showCancel 全 false | 空 footer 条 | footer 隐藏（getFooterExtra 调用即恢复） | 修复视觉瑕疵 |
| Esc 关闭（单层） | 关闭 | 关闭（handler 增栈顶判定，监听阶段不变） | 无 |
| **Esc 关闭（多层叠开）** | **一次 Esc 全部关闭（缺陷）** | 只关最顶层（见 3.6） | ✅ 有意修复 |
| body 滚动 | 可穿透 | 锁定 + scrollbar-gutter | ✅ 有意修复（EP 默认同此）；个别页面需穿透传 `lockScroll:false` |
| 遮罩 / 拖拽 / 缩放 | 恒开 | 恒开（默认不变） | 无 |

### 3.5 dock 模式与新增属性交互规则

- dock 已隐含禁用拖拽/缩放：`draggable/resizable` 显式传值也不开启（dock 优先）；
- dock + `closable`：✕ 显示在 bar-end（抽屉场景常需要）；
- dock + `fullscreen`：冲突，fullscreen 忽略（console.warn 一次）；
- dock + `closeOnEsc/closeOnMask/lockScroll/zIndex`：正常生效；
- dock + `contentPadding`：**仅当 dock 弹框走 `setContent` 时生效**；dock 主流用法是 `setSingleRegion/setLeftRight`（如 dict-select help），该路径不创建 `.dlg-content`，contentPadding 无效。

### 3.6 Esc 多层语义修复（顺带缺陷修复）

现状每个实例在 document 上注册 bubble 阶段 keydown，两层弹框叠开时一次 Esc 同时关闭所有层。

> **为什么不能用 capture + stopPropagation**（v2 方案，R2 审查证伪）：DOM 事件两条硬规则——① 同一节点上同阶段监听器按**注册顺序**执行（capture/bubble 只决定节点树层级间先后），"最后连接的实例最先收到事件"不成立；② `stopPropagation()` 不阻止**同节点同阶段**的其他监听器。叠加结果是照 v2 实现仍会全关，改 `stopImmediatePropagation` 则会关掉底层留下顶层（更糟）。且 floating-dialog 一旦改 capture，还会反转破坏与 `cmx-message-dialog` 的既有协同——message-dialog 的 capture+stop 之所以能屏蔽 floating 的 Esc，恰恰因为 floating 监听在 bubble 阶段。

**v3 方案：栈顶判定（监听阶段保持 bubble 不变）**。Esc handler 首行判定：

```js
// _onKeyDown 内（bubble 阶段监听保持不变）
const stack = document.querySelectorAll('cmx-floating-dialog')
if (stack[stack.length - 1] !== this) return            // 非栈顶：不响应
if (document.querySelector('[data-cmx-message-dialog], [data-cmx-confirm-dialog]')) return
                                                          // 更高层的 message/confirm 家族在场：让位
if (this._spec.closeOnEsc === false) return              // 栈顶禁 Esc：整次按键无弹框响应（吞掉）
this._emitClose('cancel')
```

- **栈顶判定依据**：`querySelectorAll` 文档序的最后一个即视觉最顶层（同 z-index 下 DOM 序 = 视觉序；显式传了不同 `zIndex` 的场景由让位判定兜底）；
- **message-dialog 让位**：`[data-cmx-message-dialog]` / `[data-cmx-confirm-dialog]` 是 message-dialog 家族 host 自带属性；"floating 在下、message 在上"（表单弹框里弹 cmxError 的常见场景）时 floating 让位、message 自行关闭——与现状 bubble 被 capture 屏蔽的协同方向一致，双保险。反向（message 在下、floating 在上）的错关属 message-dialog 既有局限（它无条件响应 Esc），列入九-1 演进；
- **栈顶 closeOnEsc:false = 吞掉**：所有实例都做栈顶判定后，栈顶禁 Esc 时下层也不会响应（它们非栈顶直接 return），天然实现"整次按键无响应、不穿透关下层"，与 EP 行为一致；
- 单层场景行为完全不变。存量影响面：仅多层叠开场景由"全关"变"关顶层"，属缺陷修复。

---

## 四、存量页面迁移方案

### 4.1 迁移原则

1. 手写 padding 与默认一致的 → **删手写，吃默认**；
2. 非对称/特殊 padding 的 → `setContent(el, { padding:false })` + 保留手写；
3. 自带 `max-height + overflow:auto` 的内容 → 顺带改为 `flex:1; min-height:0` 契约写法（消裁切隐患）；
4. `setLeftRight/setSingleRegion` 路径、纯 description 弹框（无 setContent）、legacy demo → **一律不动**（`setSingleRegion/setLeftRight` 路径不创建 `.dlg-content`，删其手写 padding 会导致内容裸贴边）。

### 4.2 cmx-container native-pages（5 文件 10 处）

| 文件 | 弹框 | 现状（行号为当前 dev） | 迁移动作 |
| --- | --- | --- | --- |
| `portal/mdm/subscription-manager.js` | 补发弹框（~370） | `flex:1 1 auto;min-width:0;box-sizing:border-box;padding:14px 16px;...` | 删 wrap 的 flex 三件套与 padding，只留 `display:flex;flex-direction:column;gap:10px;font-size:13px` |
| 同上 | 编辑订阅（~457） | `padding:6px 18px 14px` 非对称 + 内含自绘底栏 | `setContent(wrap, { padding:false })`，wrap 保留手写 padding（sm-scroll/dlg-foot 结构不变），flex 三件套可简化 |
| `portal/mdm/dispatch-monitor.js` | 投递详情 openDetail（~427） | `padding:12px 14px` + pre `flex:1;min-height:0` | 删 wrap padding 与 flex 三件套（pre 的 `flex:1;min-height:0` 保留——填满契约仍需） |
| 同上 | 长文本探视 openTextDialog（~459） | `padding:12px 14px` | 同上 |
| 同上 | 手动补发 openPublishDialog（~516） | `padding:14px 16px`（wrap 同带 flex 三件套） | 与上两处同：删 wrap padding 与 flex 三件套，留 `display:flex;gap;font-size` |
| `portal/dct/data-editor.js` | 查看器弹框（~287） | `padding:16px;...max-height:60vh;overflow:auto` | 删 padding；`max-height:60vh` 改 `flex:1;min-height:0` |
| 同上 | JSON 弹框（~311） | `padding:16px` | 删 padding；pre 加 `flex:1;min-height:0;overflow:auto` |
| 同上 | 两个表单弹框（~804 / ~886） | `padding:16px` + flex column | 删 padding 与 flex 三件套，留 gap/font |
| `portal/display/showcase.js` | 组件演示弹框（~250） | `padding:16px` | 删手写吃默认 |

### 4.3 CMXPortalManager（3 文件 4 处）

| 文件 | 弹框 | 现状 | 迁移动作 |
| --- | --- | --- | --- |
| `portal-menu-editor.js` | 功能码选择器（~424，`.cmx-menu-funcode-picker`） | 类样式 `padding:14px 16px` + `width:100%;height:100%`；内部 `.mfp-table-wrap` 靠根高度做 `flex:1` 滚动 | 删类内 padding；`width/height:100%` **替换为 `flex:1 1 auto;min-height:0`**（不能只删——picker 在 `.dlg-content` 中需显式伸展，否则表格区高度塌陷、滚动契约失效） |
| `portal-menu-editor.js` | 删除确认（~390） | 纯 description，无内容 | **不动** |
| `portal-workspace-node-dialog.js` | 删除确认（~1529） | 纯 description | **不动** |
| `portal-flexible-combination-manager.js` | 预览结果（`.fc-preview-body`，~934） | `padding:16px 20px; max-height:60vh; overflow:auto` | 删 padding 与 max-height，改 `flex:1;min-height:0;overflow:auto` |
| `portal-flexible-combination-panels.js` | 新建弹性组合（`.cmx-create-form`，~497） | `padding:18px 20px` | 删类内 padding（18px 20px→14px 16px） |
| `portal-definition-panels.js` | 新建字典/单据定义（`.cmx-create-form`，~460） | `padding:18px 20px` | 同上 |

### 4.4 不迁移项（明确出清单防误改）

| 项 | 原因 |
| --- | --- |
| `mdm/duplicate-check.js` 规则弹框（~762，`padding:14px 18px`） | 走 `setSingleRegion`（770 行），不经 `setContent`，无 `.dlg-content`；删手写 padding 会裸贴边。维持现状 |
| `cmx-dict-select.js` help 弹层（`setLeftRight`/`setSingleRegion`） | 同上，region-body 布局 |
| `portal-menu-editor.js` / `portal-workspace-node-dialog.js` 删除确认 | 纯 description 弹框，无内容区 |
| `html-pages/_legacy/dict-select-demo.html` | `_legacy` 目录、弹框部分影响极小，**放弃迁移**收敛范围 |
| PortalManager dialog-worknode（workspace 模板） | 非 `cmx-floating-dialog` 实例；shell 新增规则对其无副作用 |

### 4.5 视觉变化说明

`.dlg-content` 背景透明（露 `#dlg-body` 既有灰底），**无底色变化**。统一默认 padding `14px 16px` 后：data-editor（16px→14px 上下）、PortalManager 表单（18px 20px→14px 16px）每边收窄 2~4px；subscription-manager 编辑订阅（非对称 padding）与全出血场景完全不变。此为"统一"的预期成本。

---

## 五、实施步骤（原子批次）

| 批次 | 内容 | 验证 | commit 归属仓库 |
| --- | --- | --- | --- |
| 1（原子，不可拆） | 组件增强：shell 样式（dlg-body relative + `.dlg-content` + data-bleed）+ setContent opts + 空 footer 折叠 + 10 属性 + Esc 栈顶判定修复（3.6）+ `cmx-scroll-lock.js` + 全部新增单测 | `npm test -w cmx-data-comp` 全绿（含既有 dock 用例） | 前端根仓库 |
| 2 | 文档同步：① `dialog-message.md` 属性表 + 「内容区布局契约」一节；② `html-page-generator` / `native-page-generator` 技能的 component-catalog 弹框用法节——**新契约零 padding、填满写 `flex:1;min-height:0`**（防 AI 生成新页面复发旧写法） | 人工核对 | 前端根仓库 |
| 3 | native-pages 迁移（4.2 表 10 处） | `node --check` 各文件 | cmx-container 仓库 |
| 4 | CMXPortalManager 迁移（4.3 表 4 处） | `npm run build -w cmx-portal-manager` + lint（无测试网） | 前端根仓库 |
| 5 | 全量回归 + 冒烟：`npm test -w cmx-data-comp` + `npm run lint` + **html-pages 抽检**（任意打开 2~3 个设计器弹框页面确认无双重 padding）+ 浏览器冒烟（用户执行） | 全部通过 | — |

依赖与原子性：批次 1 与 3/4 必须在同一合入序列（PR 内多 commit、一次评审一次合入），避免任何"组件已默认 padding、页面未迁移"的双重 padding 中间态暴露给用户；批次 3（cmx-container 仓库）与 1/4（前端根仓库）分属两个独立 Git 仓库，按 AGENTS.md §六 嵌套仓库规范分别提交、根仓库不 `git add .`。

---

## 六、测试计划

### 6.1 Vitest 新增用例（`__tests__/cmx-floating-dialog.test.js`；jsdom 不解析样式表规则，**断言一律走 DOM 结构/属性/内联 style/`<style>` 文本**，对齐既有 dock 测试的写法）

| 用例 | 断言要点（jsdom 可行口径） |
| --- | --- |
| setContent 默认包装 | `#dlg-body > .dlg-content > el` 结构成立；shadow `<style>` 文本含 `.dlg-content` 规则与 `--dlg-content-padding, 14px 16px` |
| setContent padding:false | `.dlg-content` 有 `data-bleed="true"` |
| setContent padding 自定义串 | 容器元素内联 `style.padding` 为传入值 |
| configure contentPadding | `:host` 内联 `--dlg-content-padding` 值；opts 覆盖 configure |
| 空 footer 折叠/恢复 | 双 false + 无 buttons 时 footer `hidden`/display none（走 data 属性断言）；调用 getFooterExtra() 后恢复 |
| closable | true 时 bar-end 存在 `#dlg-close-x`；再次 configure 不重复追加（幂等）；点击派发 `cmx-dialog-cancel` |
| closeOnEsc false | dispatch keydown Escape 后元素仍 connected；双层叠开且栈顶为 closeOnEsc:false 时两层均不关（吞事件） |
| Esc 多层只关顶层 | 两个叠开实例，dispatch 一次 Escape → 仅后连接者 removed |
| closeOnMask false | :host pointerdown（box 外）不关闭 |
| mask false | `:host` 有 `data-mask="false"`；`<style>` 文本含非模态规则（背景透明 + pointer-events）；点击 :host 不关闭 |
| lockScroll 配对 | 开两个弹框 `documentElement.style.overflow === 'hidden'`；关一个仍 hidden；全关恢复原值；**reconnect 场景**（A 开→移动节点→B 关→A 仍锁）不泄漏 |
| draggable/resizable false | 拖拽监听未注册（pointerdown 后 box 位置不变/无 handlers 断言）；`.dlg-resize-root` 有隐藏 data 属性 |
| fullscreen | `.dlg-box` 有 `data-fullscreen`；`<style>` 文本含对应规则 |
| zIndex | `dlg.style.zIndex` 等于传入值 |
| 兼容回归 | 无 opts 的 setContent 旧用法不抛错；dock 既有用例不回归 |

### 6.2 构建与静态验证

- `npm test -w cmx-data-comp`（全量用例不回归）
- `npm run build -w cmx-portal-manager`（PortalManager 无测试网，靠 build）
- `npm run lint`（cmx-data-comp + cmx-portal-manager）
- native-pages 各迁移文件 `node --check`

### 6.3 页面冒烟点（用户验证）

订阅管理（新建/编辑/补发/测试）、分发监控（详情/payload 探视/死信错误/补发）、查重候选台（确认规则弹框**不受影响**）、字典数据维护（data-editor 4 弹框）、PortalManager 菜单功能码选择器（重点：表格仍填满可滚）/弹性组合预览与新建/定义新建、dict-select help（回归确认不受影响）、任意 2~3 个 html-pages 设计器弹框页面（抽检双重 padding）、**滚动锁定感知**（打开任一弹框后确认页面视口滚动被锁、关闭后恢复——校准 3.3 收益边界）、**多层 Esc**（订阅管理编辑弹框内再开"测试通道"结果弹框，按一次 Esc 只关顶层）。

---

## 七、风险与回滚

| 风险 | 概率 | 缓解 |
| --- | --- | --- |
| 迁移遗漏某处 setContent（双重 padding） | 低 | 全工作区 grep `setContent` 复核清单（4.2/4.3 即来自该扫描）；双重 padding 属视觉问题不致功能损坏 |
| `dlg-body:relative` 波及 html-pages 用户页面中未知的 absolute 用法 | 低 | 已核 PortalManager 三 worknode 与 native-pages 均无；批次 5 html-pages 抽检兜底；该修复方向正确（absolute 应锚内容区） |
| lockScroll / Esc 多层两处有意的行为变化引存量不适 | 低 | 均为缺陷修复且对齐 EP 默认；不适页面可 `lockScroll:false` 退回；Esc 单层场景无感知 |
| `.dlg-content` 包装层对深依赖 `#dlg-body` 直查子节点的隐藏用法造成破坏 | 低 | grep 核实 `dlg-body` 外部引用仅组件内部与文档；抽检兜底 |
| PortalManager 构建回归 | 低 | build + 冒烟；改动仅删类内 padding/替换填满写法，无逻辑变更 |
| 中间态双重 padding | — | 批次 1 与 3/4 同一合入序列原子合入（见五） |
| 回滚 | — | 按批次 commit（根仓库 2 个：组件+文档、PortalManager；cmx-container 1 个：native-pages），可独立 revert |

---

## 八、工作量估算

| 批次 | 估算 |
| --- | --- |
| 1 组件增强（10 属性 + Esc 修复 + scroll-lock 模块 + 空 footer + 单测 15 组） | 1 天 |
| 2 文档 + 生成器技能同步 | 0.5 天 |
| 3 native-pages 迁移（10 处） | 0.5 天 |
| 4 PortalManager 迁移（4 处）+ build/lint | 0.5 天 |
| 5 全量回归 + 冒烟整理 | 0.5 天 |
| **合计** | **约 3 天** |

---

## 九、后续演进（本期不做，立项备忘）

1. **焦点管理**：初始焦点 / Tab 焦点陷阱 / 关闭恢复焦点——抽 `cmx-message-dialog.js` 既有范式（prevActive 记录 + Tab 循环）为共享工具，floating-dialog 与 message-dialog 家族统一接入；
2. **message-dialog 家族接入 scroll-lock**：`showCmxMessage`/`cmxConfirm` 当前无锁滚动，复用 `cmx-scroll-lock.js`；
3. **setSingleRegion/setLeftRight 路径的 padding 机制**：本期明确不动（波及 dict-select help），如有统一诉求独立评估；
4. **层序体系统一盘点**：现状 toast 99999 / floating-dialog 900 / message-dialog 2147483000 跨六个数量级，应统一为常量分层（如 9000 档），独立小任务。

---

## 附录 A：Element Plus / Ant Design 属性映射总表

| 本组件属性 | Element Plus | Ant Design |
| --- | --- | --- |
| closable | show-close | closable |
| closeOnEsc | close-on-press-escape | keyboard |
| closeOnMask | close-on-click-modal | maskClosable |
| mask | modal | mask |
| lockScroll | lock-scroll | 内置 |
| draggable | draggable | — |
| resizable | —（本组件特色） | — |
| fullscreen | fullscreen | — |
| contentPadding | —（本组件特色） | — |
| zIndex | —（EP Dialog 无此 prop，由底层 Popup 管理） | zIndex |
| beforeClose（已有） | before-close | — |
| dialogWidth/Height（已有） | width | width |
| confirmText/cancelText（已有） | — | okText/cancelText |
| dock（已有） | — | Drawer placement |

## 附录 B：审查问题处置记录

### 第一轮（R1）：P0×1 / P1×6 / P2×11

| 级别 | 问题 | 处置 |
| --- | --- | --- |
| P0 | duplicate-check 走 setSingleRegion 与迁移原则矛盾 | 采纳：移出迁移清单（4.4），口径改 native-pages 10 + PortalManager 4 |
| P1 | getFooterExtra「返回前检测」时序不成立 | 采纳：改「调用即恢复」（3.1.3） |
| P1 | funcode-picker 删 height:100% 会高度塌陷 | 采纳：替换为 `flex:1 1 auto;min-height:0`（4.3） |
| P1 | Esc 多层一次全关 | 采纳（R2 修正实现）：栈顶判定方案（3.6） |
| P1 | lockScroll reconnect 泄漏 | 采纳：acquire 移守卫前 + 实例标志严格配对（3.3），reconnect 单测覆盖 |
| P1 | 测试断言超 jsdom 能力 | 采纳：全部改 DOM/属性/内联 style/`<style>` 文本断言（6.1） |
| P1 | 生成器技能文档未同步 | 采纳：批次 2 扩为 dialog-message.md + 两生成器技能（五） |
| P2 | 处数口径不一致 | 采纳：全文统一 10+4 + legacy 放弃 |
| P2 | contentPadding 合并不可清除 / opts 写入目标未定义 | 采纳：opts 写容器自身、configure 不可清除已标注（3.1.2/3.2 #9） |
| P2 | append 后 configure 重配语义未设计 | 采纳：明确「append 前配置」时序契约 + closable 幂等（3.2 引言） |
| P2 | dock+contentPadding 表述错误 | 采纳：修正为仅 setContent 路径生效（3.5） |
| P2 | `.dlg-content` 白底造成底色变化 | 采纳：改透明露既有灰底，零底色 diff（3.1.2/4.5） |
| P2 | 滚动条抖动 / 锁不共享 | 采纳：scrollbar-gutter:stable + 独立 cmx-scroll-lock.js（3.3），message-dialog 接入列后续演进 |
| P2 | fullscreen inset 矛盾 | 采纳：left/top 4px + calc 尺寸（3.2 #8） |
| P2 | mask:false 语义与 closeOnMask 矛盾 | 采纳：对齐 EP 非模态语义（3.2 #4） |
| P2 | 焦点管理缺失 | 采纳：列后续演进 #1（九） |
| P2 | 批次 1 单独合入改变行为 / 中间态窗口 | 采纳：批次 1 原子化 + 同一合入序列 + html-pages 抽检（五/七） |
| P2 | 估算乐观 + 跨仓库边界 | 采纳：批次 1 调 1 天总 3 天；commit 仓库归属入批次表（五/八） |

### 第二轮（R2）：17/18 闭环确认 + 新发现 P0×1 / P2×5

R2 对 v2 逐条核验：R1 的 18 条中 17 条确认闭环（lockScroll 配对伪代码经逐路径推演成立、funcode-picker 动作完整、15 组测试断言全部 jsdom 可行）；**Esc 修复（3.6）方向正确但 v2 的 capture+stopPropagation 实现违反 DOM 事件语义被退回**，v3 重写。

| 级别 | 问题 | 处置 |
| --- | --- | --- |
| P0 | v2 3.6 capture+stopPropagation 不成立：同节点同阶段监听按注册顺序执行、stopPropagation 不阻同节点监听 → 仍全关或关错层；且 floating 改 capture 会反转破坏 message-dialog 既有屏蔽协同 | 采纳：重写为**栈顶判定**（bubble 监听不变，handler 首行判 `querySelectorAll('cmx-floating-dialog')` 末位 + message 家族让位 + 栈顶禁 Esc 吞事件），并记录「为什么不能用 capture」防止回退（3.6） |
| P2 | 3.3 伪代码缺 gutter 存/恢复字段；锁 html 对门户内部容器滚动无效的收益预期未校准 | 采纳：伪代码补 `_prevHtmlGutter`；补收益边界说明；6.3 冒烟加滚动锁定感知验证 |
| P2 | 6.1 mask:false 断言写「内联」与 data 属性实现套路不一致 | 采纳：统一 `data-mask="false"` + style 文本断言（3.2 #4 / 6.1） |
| P2 | 4.2 dispatch-monitor 第三处动作与前两处不统一 | 采纳：补齐「与上同：删 padding 与 flex 三件套」 |
| P2 | mask:false 非模态与 lockScroll 默认 true 组合怪异未提示 | 采纳：3.2 #4 补「建议同时配 lockScroll:false」 |
| P2 | 附录 A「z-index（险）」笔误；文档头 P2 计数不符 | 采纳：修正为「EP Dialog 无此 prop，由 Popup 管理」；计数改 P2×11 |

R2 结论：3.6 修正 + P2 清理后即可进入实施，其余无需再轮审。

## 附录 C：浮层层序现状盘点（zIndex 属性背景）

| 层 | z-index | 出处 |
| --- | --- | --- |
| cmx-floating-dialog :host | 900（固定） | cmx-dialog-shell.js |
| native 页面 toast | 99999 | 各 native-page 自建 |
| cmx-message-dialog（showCmxMessage/cmxConfirm） | 2147483000 | cmx-message-dialog.js |

zIndex 属性先解决 floating-dialog 自身多层叠开（help 弹在表单弹框上）的可控性；全站层序统一见九-4。
