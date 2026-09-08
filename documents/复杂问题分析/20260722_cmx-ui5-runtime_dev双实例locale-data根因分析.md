# DatePicker 日历头"月份/年份 undefined"根因与方案分析

> 日期：2026-07-22（初版）/ 2026-07-25（v2：方案 A 已实施 + 日历头标题 Render.js 挂起根因）
> 涉及包：`cmx-ui5-runtime` / `cmx-data-comp` / `cmx-portal-manager` / `cmx-html-designer`

***

## 一、问题现象

Portal dev 模式下，进入"总账科目维护(自分级)"页面，双击"生效日期"列单元格编辑，
弹出的 `<ui5-date-picker>` 日历头部月份/年份显示 undefined（`_headerMonthButtonText = null`）。
**首页（welcome）上同样创建 date-picker 却正常**——这是定位根因的关键线索。

## 二、本次修复总结（TL;DR）

本次根因分析与修复涉及**两个独立 bug**，需要分别处理：

| # | Bug | 根因 | 修复 |
|---|-----|------|------|
| 1 | dev 模式 UI5 模块双实例 → locale data 不共享 → 月份名 undefined | Vite dev server 和 runtime chunk 各持一份 ES module 实例 | dev 模式不 external UI5，由 Vite dev server 统一解析（详见第三节） |
| 2 | dev 模式 UI5 Render.js 渲染队列挂起 → `Calendar.onAfterRendering` 内 `await renderFinished()` 永远不返回 → header 文本设置逻辑不执行 | `whenDOMUpdated()` 在 `invalidatedWebComponents` 队列非空时永久挂起 | monkey-patch `Calendar.prototype.onAfterRendering`，把 `await renderFinished()` 替换为带 250ms 超时的 `Promise.race`（详见第五节） |

***

## 三、根因：dev 模式下 UI5 模块双实例

### 3.1 两份独立的 ES module 图

| 来源                  | 模块图                                                                               | 加载方式                                    |
| ------------------- | --------------------------------------------------------------------------------- | --------------------------------------- |
| **Vite dev server** | Portal 应用代码（`cmx-date-input.js` 等）通过 Vite 解析 UI5 模块，走 `/@fs/` 或 `.vite/deps/` 预打包 | ESM 原生 import                           |
| **runtime chunk**   | `/shared/assets/install-*.js`（生产构建产物）内联了 UI5 全部代码                                 | `import(/* @vite-ignore */ entry)` 动态加载 |

这两份是**独立的 ES module 实例**，各自有独立的模块级变量。
`LocaleData.js` 的 `localeDataMap`（Map）和 `loaders`（Map）是模块级变量，
两份实例各持一份，**互不可见**。

### 3.2 Calendar 用的是哪份？

Calendar 自定义元素由 runtime chunk 的 `bundle.esm.js` 注册（`customElements.define('ui5-calendar', ...)`）。
Calendar 的 `onAfterRendering` 调用 `getCachedLocaleDataInstance(getLocale())`，
该函数内部 `new LocaleData(locale)` → `loadData()` → `LoaderExtensions.loadResource()` → `getLocaleData()`，
**走的是 runtime chunk 内的** **`LocaleData.js`** **实例**。

### 3.3 locale data 注册到了哪份？

- runtime chunk 的 `install.js` 执行 `fetchCldr('zh','CN')` → 数据写入 **runtime 实例** 的 `localeDataMap`
- Portal 应用代码（如 `import-ui5-and-app.js`、`cmx-date-input.js`）里的 `import '@ui5/webcomponents-base/dist/asset-registries/LocaleData.js'` → Vite 解析到 **Vite 实例**

注册到 Vite 实例的数据，runtime 的 Calendar 读不到。

### 3.4 为什么首页正常、字典页不正常？

首页 date-picker 是在**首次**打开 Calendar，此时 runtime 的 `install.js` 的 `fetchCldr` 预加载已完成，
`getCachedLocaleDataInstance` 用 runtime 实例拿到了数据。

字典页面打开后，页面脚本（`cmx-data-comp` barrel import）触发了 Vite 解析的 UI5 模块加载，
这些模块的执行**在某些时机会重新调用** **`getCachedLocaleDataInstance`** **或相关缓存**，
如果缓存 key 不一致或时序交错，就会取到空数据。
更深层的原因是 Vite 的 `optimizeDeps` 预打包和 `/@fs/` 路径在字典页面打开后产生了**第三份** LocaleData 实例（完全没注册任何数据）。

### 3.5 为什么生产构建没问题？

生产构建中 `@ui5/webcomponents` 被 `external`（runtime 提供），所有 UI5 import 都走 side-effect shim（空操作），
不存在双实例——只有 runtime chunk 一份实例，locale data 也只注册在这一份上。

### 3.6 解决方案：dev 模式由 Vite 统一解析

dev 模式下不再从 `/shared/` 加载 runtime chunk，而是让 Vite dev server 原生解析所有 UI5 模块，
所有代码共享同一份 ES module 实例，从根源消除双实例。

**核心改动**（3 个文件）：

1. [packages/cmx-ui5-runtime/vite-app.js](file:///media/yqs/工作/rustspace/cmx/packages/cmx-ui5-runtime/vite-app.js)
   - `isUi5SideEffectImport` 排除 base / localization / Assets / bundle.esm / AllIcons（这些是 install.js 关键依赖，不能 shim 成空）
   - `cmxUi5SideEffectShimPlugin` 与 `cmxUi5RuntimeAppPlugin` 在 dev 模式整体跳过（`return null` / 不设 external / 不注入 hash URL）
2. [packages/cmx-ui5-runtime/src/client.js](file:///media/yqs/工作/rustspace/cmx/packages/cmx-ui5-runtime/src/client.js)
   - dev 模式走 `import.meta.env.DEV ? import('cmx-ui5-runtime/src/install.js') : import('runtime-chunk')`
3. [CMXPortalManager/vite.config.js](file:///media/yqs/工作/rustspace/cmx/CMXPortalManager/vite.config.js)
   - `optimizeDeps.exclude` 增加 base / localization / theming
   - `resolve.alias` 映射 `cmx-ui5-runtime/src/*` 等子路径

**架构对比**：

```
改动前：双实例                           改动后：单实例
┌─ 应用代码 ─┐                          ┌─ 应用代码 ─┐
│  Vite 实例 V │   ← 不共享 →            │  Vite 实例 V │   ← 共享同一份
└────────────┘                          └────────────┘
┌─ Runtime 实例 R ─┐                       ↕
│  Calendar 等     │              install.js / 应用代码
│  LocaleData      │              共享同一份实例
└──────────────────┘

实例 R 的 LocaleData ≠ 实例 V 的 LocaleData
Calendar 走实例 R，但数据注册到实例 V → undefined
```

**优点**：

- 从根源消除双实例，locale data 注册一份即可
- dev 模式享受 HMR（改 install.js 不用重新构建 runtime）
- 生产构建行为不变（仍然 external + runtime chunk）

**缺点**：

- dev 启动时间略增（Vite 需要解析更多 UI5 模块）

***

## 四、附：双实例验证方法

```javascript
// 在浏览器 console 执行（Portal dev 模式）
const LR1 = await import('/node_modules/.vite/deps/@ui5_webcomponents-base_dist_asset-registries_LocaleData__js.js')
const LR2 = await import('/@fs/.../node_modules/@ui5/webcomponents-base/dist/asset-registries/LocaleData.js')
LR1 === LR2  // false → 双实例确认
LR1.registerLocaleDataLoader('test', async () => ({}))
LR2.getLocaleData('test')  // Error: CLDR data not loaded → 两份独立
```

***

## 五、日历头标题 undefined 第二个根因：UI5 Render.js 渲染队列挂起

### 5.1 现象

方案 A 实施后，「总账科目维护(自分级)」页面打开 date-picker，日历头仍显示 undefined。
但首页同样 date-picker 正常。

### 5.2 诊断

Playwright 注入 `onAfterRendering` hook 拦截测试：

```javascript
const origAfter = CalClass.prototype.onAfterRendering
CalClass.prototype.onAfterRendering = async function() {
  window.__cmxHook.push({ phase: 'start', ts: Date.now() })
  try {
    const r = origAfter.call(this)
    if (r?.then) {
      const timeout = new Promise((_, rej) => setTimeout(() => rej(new Error('TIMEOUT_5s')), 5000))
      await Promise.race([r, timeout])
    }
    window.__cmxHook.push({ phase: 'end', header: this._headerMonthButtonText })
  } catch (e) {
    window.__cmxHook.push({ phase: 'error', err: e.message })
  }
}
```

测试结果：所有 Calendar 实例的 hook 触发后**5 秒内不结束**（`phase: 'end'` 永不出现），
header 字段保持 `null`。

### 5.3 根因：Render.js `whenDOMUpdated()` 在 dev 模式下永久挂起

源码 [Render.js](file:///media/yqs/工作/rustspace/cmx/node_modules/@ui5/webcomponents-base/dist/Render.js)：

```javascript
const whenDOMUpdated = () => {
  if (renderTaskPromise) return renderTaskPromise
  renderTaskPromise = new Promise(resolve => {
    renderTaskPromiseResolve = resolve
    window.requestAnimationFrame(() => {
      if (invalidatedWebComponents.isEmpty()) {
        renderTaskPromise = undefined
        resolve()
      }
      // ⚠️ 关键 bug：队列非空时啥都不做，Promise 永远不 resolve！
    })
  })
  return renderTaskPromise
}
```

永久挂起的时序：

```
T0: scheduleRenderTask
    └─ queuePromise = new Promise(resolve => RAF(() => {
          invalidatedWebComponents.process(renderImmediately)  // 渲染 Calendar 子 picker
          queuePromise = null
          resolve()
          if (!mutationObserverTimer) {
            mutationObserverTimer = setTimeout(() => {
              if (invalidatedWebComponents.isEmpty()) {
                _resolveTaskPromise()  // ← 仅在 200ms 后队列空时 resolve
              }
            }, 200)
          }
       }))

T1: whenDOMUpdated()
    └─ renderTaskPromise = new Promise(resolve => RAF(() => {
          if (invalidatedWebComponents.isEmpty()) {
            renderTaskPromise = undefined
            resolve()
          }
       }))
    └─ return renderTaskPromise  // 永远 pending

T2: Calendar 子 picker (DayPicker/MonthPicker) 触发的 invalidate
    └─ invalidatedWebComponents.add(dayPicker)
    └─ renderTaskPromise 没被 resolve（_resolveTaskPromise 在 200ms 后发现队列非空，跳过）
    └─ 之后没有新的 renderDeferred 调用，renderTaskPromise 永远不 resolve

T3: Calendar.onAfterRendering 第一行 `await renderFinished()`
    └─ renderFinished → whenAllCustomElementsAreDefined → whenDOMUpdated
    └─ 永久 pending
    └─ 后续 `_headerMonthButtonText = ...` 永远不执行
```

**为什么首页正常，字典页不正常？**
首页 date-picker 是首次打开 Calendar，picker 还未挂载，队列一开始就是空的，
`whenDOMUpdated` 的 RAF 回调里 `isEmpty() === true`，直接 resolve。
字典页是先渲染 grid，再打开 date-picker，grid 已经触发了一堆 `renderDeferred`，
Calendar 子 picker 在 RAF 回调时还在队列里 → 永远不 resolve。

### 5.4 修复：monkey-patch `Calendar.prototype.onAfterRendering`

策略：保留原 `onAfterRendering` 的后续逻辑（设置 header / prev/next 按钮等），
但把 `await renderFinished()` 替换为带 250ms 兜底的 `Promise.race`。

代码位置：[install.js L80-118](../packages/cmx-ui5-runtime/src/install.js)

```javascript
function patchCalendarOnAfterRendering () {
  const CalClass = customElements.get('ui5-calendar')
  if (!CalClass) return false
  const proto = CalClass.prototype
  if (proto.__cmxPatched) return true
  if (typeof proto.onAfterRendering !== 'function') return false
  proto.onAfterRendering = async function cmxPatchedOnAfterRendering () {
    // 250ms 兜底：UI5 内部 renderFinished 在 dev 模式下可能永久挂起
    const timeout = new Promise(resolve => setTimeout(() => resolve('timeout'), 250))
    const { renderFinished } = await import('@ui5/webcomponents-base/dist/Render.js')
    try {
      await Promise.race([renderFinished(), timeout])
    } catch (_) { /* 渲染失败不影响 header 设置 */ }
    // 复刻 Calendar 原 onAfterRendering 后续逻辑
    try {
      this._previousButtonDisabled = !this._currentPickerDOM._hasPreviousPage()
      this._nextButtonDisabled = !this._currentPickerDOM._hasNextPage()
    } catch (_) { /* picker 未就绪 */ }
    try {
      const loc = getLocale()
      const localeData = getCachedLocaleDataInstance(loc)
      const yearFormat = DateFormat.getDateInstance({ format: 'y', calendarType: this.primaryCalendarType })
      this._headerMonthButtonText = localeData.getMonthsStandAlone('wide', this.primaryCalendarType)[this._calendarDate.getMonth()]
      this._headerYearButtonText = String(yearFormat.format(this._localDate, true))
      const { rangeStartText, rangeEndText } = this._formatYearRangeText(this._currentYearRange)
      this._headerYearRangeButtonText = `${rangeStartText} - ${rangeEndText}`
      this._secondaryCalendarType && this._setSecondaryCalendarTypeButtonText()
    } catch (_) {
      // 极少见：LocaleData 异常时用 getCalendarHeaderTexts 兜底
      const texts = getCalendarHeaderTexts(new Date())
      if (texts) {
        this._headerMonthButtonText = texts.monthText
        this._headerYearButtonText = texts.yearText
      }
    }
  }
  proto.__cmxPatched = true
  return true
}

patchCalendarOnAfterRendering()
```

**为什么 250ms 够？**
UI5 原版逻辑是先 `await renderFinished()` 再读 `_currentPickerDOM._hasPreviousPage()`。
而 picker 的 `connectedCallback` 是在 Calendar 渲染**同步阶段**触发的，
`renderFinished` resolve 后 picker 一定在 shadowRoot 里，调用 picker 方法不会失败。
250ms 兜底让 header 设置逻辑**总会**执行；如果 renderFinished 在 250ms 内就 resolve
（正常情况），行为与原版一致；只有当 UI5 内部渲染队列异常挂起时，250ms 后兜底。

### 5.5 验证

Playwright 在「总账科目维护(自分级)」页面穿透 shadow root 触发所有 date-picker，
检查 Calendar 实例的 `_headerMonthButtonText` 和 DOM span：

| # | id | _headerMonthButtonText | _headerYearButtonText | DOM month | DOM year | patched |
|---|----|------------------------|----------------------|-----------|----------|---------|
| 1 | ui5wc_261-calendar | 一月 | 2020年 | 一月 | 2020年 | ✅ |
| 2 | ui5wc_262-calendar | 七月 | 2026年 | 七月 | 2026年 | ✅ |
| 3 | ui5wc_263-calendar | 七月 | 2026年 | 七月 | 2026年 | ✅ |

截图（[04_visual_calendar.png](file:///tmp/cmx-calendar-verify/04_visual_calendar.png)）显示日历头「一月 2020年」正确渲染。

***

## 六、精简后的前端代码改动清单

所有改动文件（按必要性评估）：

| # | 文件 | 必要性 | 说明 |
|---|------|--------|------|
| 1 | [CMXPortalManager/vite.config.js](file:///media/yqs/工作/rustspace/cmx/CMXPortalManager/vite.config.js) | ✅ 必要 | `optimizeDeps.exclude` 增加 base / localization / theming，让 Vite 走 `/@fs/` 实时解析 |
| 2 | [packages/cmx-ui5-runtime/src/client.js](file:///media/yqs/工作/rustspace/cmx/packages/cmx-ui5-runtime/src/client.js) | ✅ 必要 | dev 模式走 Vite alias 解析源码 install.js |
| 3 | [packages/cmx-ui5-runtime/src/install.js](file:///media/yqs/工作/rustspace/cmx/packages/cmx-ui5-runtime/src/install.js) | ✅ 必要 | 根因修复：monkey-patch `Calendar.onAfterRendering`；`fetchCldr` 提前到 `boot()` 之前 |
| 4 | [packages/cmx-ui5-runtime/vite-app.js](file:///media/yqs/工作/rustspace/cmx/packages/cmx-ui5-runtime/vite-app.js) | ✅ 必要 | shim 排除关键功能模块；dev 模式跳过 external / 注入 hash URL |
| 5 | [packages/cmx-data-comp/src/components/cmx-date-input.js](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/components/cmx-date-input.js) | ✅ 必要 | 删除临时代码（`_patchCalendarHeader` / `_fixHeaderIfNull`） |
| 6 | [packages/cmx-data-comp/src/components/cmx-datetime-input.js](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/components/cmx-datetime-input.js) | ✅ 必要 | 同上 |
| 7 | [packages/cmx-ui5-runtime/src/runtime-api.js](file:///media/yqs/工作/rustspace/cmx/packages/cmx-ui5-runtime/src/runtime-api.js) | ✅ 必要（精简后） | 移除未使用的 API 类型声明 |

**精简过程中删除的非必要代码**：
- `install.js` 中的 `patchWhenDOMUpdated()` 空函数（探索过程遗留）
- `install.js` 中未使用的 `let reason` 变量
- `install.js` 中 `api` 对象上未使用的 3 个键（应用层不调用）
- `runtime-api.js` 中对应的 3 条 `@property` 类型声明
- 两个 `setTimeout(patchCalendarOnAfterRendering, 100/500)` 兜底（`await Promise.all([import('bundle.esm.js'), ...])` 已保证 ui5-calendar 自定义元素注册完成）
- 简化的长注释行（保留核心解释，删除探索性讨论）

**保留的兜底**：
- `getCalendarHeaderTexts(date)` 函数：monkey-patch 内部 LocaleData 异常时使用，应用层不再调用
- `getLocale` / `getCachedLocaleDataInstance` / `DateFormat` / `UI5Date` import：monkey-patch 内部使用
- `optimizeDeps.exclude`：避免 Vite 预打包 UI5 大包
- catch 块结构：保留以防御 UI5 内部 API 变化导致的异常

***

## 七、复盘：同类问题的预防

1. **UI5 渲染期依赖**：任何 UI5 组件的 `onAfterRendering` 内 `await renderFinished()` 都可能在
   dev 模式下挂起。如果未来其他 UI5 组件出现"dev 正常但生产/特殊页面异常"的情况，
   优先检查 `await renderFinished()` 是否在 critical 路径上。
2. **ES module 实例隔离**：Vite dev 与生产构建的模块图必须一致。**任何**新增的 bare import
   （特别是 UI5 子模块）都要确认 dev/prod 一致，否则会出现"首页正常、字典页异常"。
3. **顶层 await 的依赖时序**：`boot()` / `fetchCldr` 等初始化操作的顺序必须明确，注释中
   说明为什么是这个顺序。

***

## 八、附录：CMXHTMLDesigner 影响范围

CMXHTMLDesigner 与 CMXPortalManager **共享同一份** [`cmx-ui5-runtime`](../packages/cmx-ui5-runtime/) 和
[`cmx-data-comp`](../packages/cmx-data-comp/) 组件库，因此本次修复（install.js 的 monkey-patch、
client.js 的 dev alias、vite-app.js 的 shim 排除、fetchCldr 提前）**自动覆盖** CMXHTMLDesigner。

[CMXHTMLDesigner/vite.config.js](../CMXHTMLDesigner/vite.config.js) 已包含必要的配置：

- `optimizeDeps.exclude` 已列出 `@ui5/webcomponents-base` / `localization`（dev 模式不走 Vite 预打包）
- `resolve.alias` 已映射 `cmx-ui5-runtime/src/*` / `cmx-ui5-runtime/client` / `vite-app` / `vite`
- `resolve.dedupe` 已包含所有 `@ui5/webcomponents*` 与 `cmx-ui5-runtime`

**结论：CMXHTMLDesigner 无需额外修改，方案 A 直接生效。**

> 若未来需要为 CMXHTMLDesigner 独立添加 vite 配置项（如增加 `optimizeDeps.entries`），应同步检查
> 上述三项是否仍满足方案 A 的"dev 模式统一 ES module 实例"前提。

***

## 九、附录：根因修复验证脚本（Playwright）

下列脚本用于回归测试——验证 `cmx-date-input` / `cmx-datetime-input` 弹出的 `<ui5-calendar>` 头部
月份/年份文本正确显示，**穿透 Shadow DOM** 触发所有 picker 实例并报告结果。

**使用方式**：

```bash
# 前置：Portal dev server 已在 http://127.0.0.1:5173/ 运行
pip install playwright
playwright install chromium
python /tmp/verify_calendar_header.py
# 退出码 0 = 全部通过；非 0 = 有 calendar 头 undefined
```

**截图**：`/tmp/cmx-calendar-verify/03_calendar_opened.png` —— 打开 picker 后的可视化结果。

```python
"""
根因修复验证脚本 V5 — 穿透 shadow root 打开 picker

前置：
  - Portal dev server 已在 http://127.0.0.1:5173/ 运行
  - 登录账号 admin / cmxadmin
  - 菜单"总账科目维护(自分级)"已发布
退出码 0 = 全部通过；非 0 = 有 calendar 头 undefined
"""
import asyncio
import sys
import os
from playwright.async_api import async_playwright

URL = 'http://127.0.0.1:5173/'
ACCOUNT = 'admin'
PASSWORD = 'cmxadmin'
SCREEN_DIR = '/tmp/cmx-calendar-verify'


async def main():
    os.makedirs(SCREEN_DIR, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
        ctx = await browser.new_context(viewport={'width': 1440, 'height': 900})
        page = await ctx.new_page()

        console_logs = []
        page.on('console', lambda m: console_logs.append((m.type, m.text)))
        page.on('pageerror', lambda e: console_logs.append(('pageerror', str(e))))

        # 1. 打开 + 登录
        print(f'[1] Open {URL}')
        await page.goto(URL, wait_until='domcontentloaded', timeout=30_000)
        await page.wait_for_timeout(3000)
        await page.locator('input').nth(0).fill(ACCOUNT)
        await page.locator('input').nth(1).fill(PASSWORD)
        btn = page.locator('button').filter(has_text='登').first
        await btn.click()
        try:
            await page.wait_for_url(lambda u: 'login' not in u.lower(), timeout=10_000)
        except Exception:
            pass
        await page.wait_for_timeout(3000)
        print('  - 登录完成')

        # 2. 搜索菜单
        print('[2] 搜索"总账科目维护"')
        search = page.locator('input[placeholder*="搜索"]').first
        await search.click()
        await search.fill('总账科目维护')
        await page.wait_for_timeout(2500)
        target = page.locator('text=总账科目维护(自分级)').first
        await target.wait_for(timeout=5000)
        await target.click()
        await page.wait_for_timeout(6000)
        print('  - 已点击"总账科目维护(自分级)"')

        # 3. 穿透 shadow root 找 picker 并打开
        print('[3] 穿透 shadow root 找 picker 并打开')
        opened = await page.evaluate('''async () => {
            function deepQuery(selector, root) {
                root = root || document;
                const result = Array.from(root.querySelectorAll(selector));
                const allWithShadow = root.querySelectorAll('*');
                for (const el of allWithShadow) {
                    if (el.shadowRoot) {
                        const sub = deepQuery(selector, el.shadowRoot);
                        for (const s of sub) result.push(s);
                    }
                }
                return result;
            }
            const dps = deepQuery('ui5-date-picker, ui5-datetime-picker');
            const out = { pickerCount: dps.length, opened: [], errors: [] };
            for (const dp of dps) {
                try {
                    if (typeof dp.openPicker === 'function') {
                        await dp.openPicker();
                        out.opened.push({ ok: true, value: dp.value });
                    }
                } catch (e) {
                    out.errors.push({ err: e.message });
                }
            }
            await new Promise(r => setTimeout(r, 1500));
            const cals = deepQuery('ui5-calendar');
            out.calendarCount = cals.length;
            return out;
        }''')
        print(f'  - date pickers: {opened["pickerCount"]}')
        print(f'  - opened: {opened["opened"]}')
        print(f'  - errors: {opened["errors"]}')
        print(f'  - calendars: {opened["calendarCount"]}')

        await page.wait_for_timeout(2000)
        await page.screenshot(path=f'{SCREEN_DIR}/03_calendar_opened.png', full_page=False)
        print('  - 截图 03_calendar_opened.png')

        # 4. 穿透 shadow root 检查 calendar header
        result = await page.evaluate('''async () => {
            function deepQuery(selector, root) {
                root = root || document;
                const result = Array.from(root.querySelectorAll(selector));
                const allWithShadow = root.querySelectorAll('*');
                for (const el of allWithShadow) {
                    if (el.shadowRoot) {
                        const sub = deepQuery(selector, el.shadowRoot);
                        for (const s of sub) result.push(s);
                    }
                }
                return result;
            }
            const cals = deepQuery('ui5-calendar');
            const out = [];
            for (const c of cals) {
                const month = c._headerMonthButtonText;
                const year = c._headerYearButtonText;
                const monthSpan = c.shadowRoot?.querySelector('[data-ui5-cal-header-btn-month] span')?.textContent;
                const yearSpan = c.shadowRoot?.querySelector('[data-ui5-cal-header-btn-year] span')?.textContent;
                const isPatched = !!(c.constructor && c.constructor.prototype && c.constructor.prototype.__cmxPatched);
                out.push({
                    id: c.id || '(no-id)',
                    propMonth: month,
                    propYear: year,
                    domMonth: monthSpan,
                    domYear: yearSpan,
                    isPatched,
                });
            }
            return out;
        }''')
        print()
        print('=' * 60)
        print('Calendar header 检查结果：')
        print('=' * 60)
        ok = False
        if not result:
            print('  ❌ 未找到任何 ui5-calendar 实例')
        else:
            ok = True
            for i, r in enumerate(result, 1):
                print(f'  [{i}] id={r["id"]}  patched={r["isPatched"]}')
                print(f'      属性 _headerMonthButtonText = {r["propMonth"]!r}')
                print(f'      属性 _headerYearButtonText  = {r["propYear"]!r}')
                print(f'      DOM   month span = {r["domMonth"]!r}')
                print(f'      DOM   year  span = {r["domYear"]!r}')
                if not r["propMonth"] or 'undefined' in str(r["propMonth"]) or 'undefined' in str(r["domMonth"]):
                    ok = False

        # 5. console 错误
        print()
        print('=' * 60)
        print('关键 console 日志')
        print('=' * 60)
        for tp, text in console_logs:
            if tp in ('warning', 'error', 'pageerror') and 'Images loaded lazily' not in text and 'Lit is in dev mode' not in text:
                print(f'  [{tp}] {text[:300]}')

        await browser.close()

        if ok:
            print()
            print('✅ 验证通过：Calendar header 文本正确显示')
            sys.exit(0)
        else:
            print()
            print('❌ 验证失败')
            sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
```

**关键验证点**：

| 检查项 | 期望 | 说明 |
|--------|------|------|
| `propMonth`（`_headerMonthButtonText`） | `"一月"` / `"七月"` 等本地化月份名 | Calendar 内部状态，monkey-patch 直接写入 |
| `propYear`（`_headerYearButtonText`） | `"2020年"` / `"2026年"` | DateFormat 格式化结果 |
| `domMonth` / `domYear`（DOM span） | 同上 | UI5 通过 `_headerMonthButtonText` 渲染到 shadow DOM |
| `isPatched`（`__cmxPatched`） | `true` | monkey-patch 生效标记 |
| console 无 `Multiple UI5 Web Components instances detected` | ✓ | 双实例已消除 |
| console 无 `[LocaleData] Supported locale "zh_CN" not configured` | ✓ | LocaleData 已就绪 |
