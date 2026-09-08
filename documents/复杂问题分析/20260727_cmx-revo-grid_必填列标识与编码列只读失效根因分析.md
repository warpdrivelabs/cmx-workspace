# cmx-revo-grid 必填列标识与编码列只读失效根因分析

> 日期：2026-07-27
> 涉及模块：`packages/cmx-data-comp/src/components/cmx-revo-grid.js` + `cmx-container/data/native-pages/sources/portal/dct/data-editor.js`
> 触发页面：`/view/gl-dict-data-editor`（http://127.0.0.1:5173/view/gl-dict-data-editor，加载约 15s）

---

## 一、问题现象

| # | 现象 | 影响范围 |
|---|---|---|
| 1 | **必填列列头不显示红色 `*` 标识** | 编辑器页所有 `required:true` 列（编码/名称/排序号/启用状态/系统预置 等 5 列） |
| 2 | **编码列 readonlyWhen 失效** | 业务键列：存量行仍可修改、新增行也无法填写 |
| 2a | 存量行（`id` 为数字/UUID）应只读 → 实际可点击进入编辑 | 破坏业务编码唯一性、外键一致性 |
| 2b | 新增行（`id` 以 `t` 开头）应可填 → 实际无法编辑 | 新增的字典项无法写入业务编码 |

---

## 二、根因分析（两个独立问题，三层根因）

### 2.1 必填列 `*` 不显示（根因 A：Stencil lazy load 竞态）

**文件**：[`packages/cmx-data-comp/src/components/cmx-revo-grid.js`](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/components/cmx-revo-grid.js) → `_applyRequiredMarks()`

**机制**：必填标识的实现思路
```js
// 数据列的 _cmxCol.required / _cmxCol.edit.required 为 true 时
// 给该列挂 columnTemplate = (h) => [<span * />, <span 标题 />]
// revo-grid 列头 renderer 调 data.columnTemplate(createElement, columnData) 渲染
```

**根因**：原实现"新建一个 col 对象再赋值"——在 Stencil lazy load 模式下失效。

```
_syncToRevo()
  → _applyRequiredMarks(cols) 返回新数组
    → _setRevoProp('columns', newCols, signature)
      → Stencil prop watcher 第一次触发（componentWillLoad 之后）
        → watcher 收到的引用 与 我们后续 _setRevoProp 的引用之间存在初始化竞态
          → columnTemplate 丢失（revo 内部收到的列定义不含 columnTemplate）
```

**验证**：通过 Playwright 在浏览器中探测 shadowRoot，确认 revo-grid 内部 `columnTemplate` 为 undefined；返回新对象策略在 race window 内被丢弃。

### 2.2 编码列 readonlyWhen 完全失效（根因 B+C：revo-grid 不识别公式 + 焦点路径冲突）

**根因 B：revo-grid 只识别 `readonly` 为布尔或函数，不识别公式字符串**

[`packages/cmx-data-comp/src/components/cmx-revo-grid.js`](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/components/cmx-revo-grid.js) → `setColumnModel` 路径

```js
// data-editor.js 对业务键的列配置：
colOpts.edit.mode = 'cmx-text-input'
colOpts.edit.readonlyWhen = `NOT(STARTSWITH(id, 't'))`   // 新增行(id 以 t 开头)可编辑
colOpts.edit.required = true
```

但 `CmxColumnAdapter.toRevoGrid()` 输出的列定义中 `readonly` 字段是 `undefined`（公式串被丢弃），revo-grid 不知道什么时候该锁列 → 整列都可编辑。

**根因 C：`_maybeEditOnFocus` 用 `column.readonly === true` 把"未来要做条件只读"的列提前放行**

```js
// 原代码（错误）：
if (column.readonly === true) return  // 布尔 true 才阻止
// 但 readonly=true 的"业务锁"列和 readonlyWhen="公式"列都该阻止"click 进编辑"
// 实际：
//   - readonly=true 整数主键：        revo-grid 内部 canEdit 拦截 → 进不去  ✓
//   - readonly=undefined 业务键列：   revo-grid 内部 canEdit 不拦截 → 进了    ✗（错）
//   - readonly=function 翻译后：     revo-grid 内部按行调函数 → 正确       ✓（修复后）
```

**链路**：
```
用户点击编码列单元格
  → _onAfterFocus 触发
    → _maybeEditOnFocus：column.readonly 不是 true → 放行
      → queueMicrotask 里 this._revo.setCellEdit(rowIndex, 'code')
        → revo-grid 内部 canEdit() 查 column.readonly
          → column.readonly === undefined → 不拦截 → 打开编辑器   ✗ 错
```

---

## 三、修复方案

### 3.1 必填列 `*` — 改为「原对象 mutate」+「showRequiredMark 开启时强制赋值」+「afterheaderrender 兜底」

#### 3.1.1 `_applyRequiredMarks` 直接修改原列对象

**[`cmx-revo-grid.js:1010-1047`](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/components/cmx-revo-grid.js#L1010-L1047)**

```js
_applyRequiredMarks(cols) {
  if (!this._opts.showRequiredMark || !Array.isArray(cols)) return cols
  const walk = (list) => {
    for (const col of list) {
      if (!col) continue
      if (Array.isArray(col.children) && col.children.length) {
        walk(col.children)
        continue
      }
      const cmxCol = col._cmxCol
      const required = cmxCol && (cmxCol.required === true
        || (cmxCol.edit && cmxCol.edit.required === true))
      if (!required || col.columnTemplate) continue
      const title = col.name || col.prop
      // 【关键】直接修改原对象而非创建新对象。
      // 原因：Stencil 框架在 lazy load 模式下对 prop watcher 第一次触发时，
      // 内部存在一个会丢失新建对象 columnTemplate 的时机。
      // 直接修改原对象可绕开该问题。
      col.columnTemplate = (h) => [
        h('span', {
          class: 'cmx-req-mark',
          style: {
            color: 'var(--sapNegativeColor,#bb0000)',
            fontWeight: '700',
            marginRight: '3px',
          },
        }, '*'),
        h('span', {}, title),
      ]
    }
    return list
  }
  return walk(cols)
}
```

#### 3.1.2 `_syncToRevo` showRequiredMark 开启时绕开签名比对

**[`cmx-revo-grid.js:953-962`](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/components/cmx-revo-grid.js#L953-L962)**

```js
const columns = this._applyRequiredMarks(this._columnsForViewport())
// 必填标识（columnTemplate）是纯视觉态，必须确保 revo 收到最新列定义。
// _setRevoProp 的签名比对在 template 变化时可能因时序问题漏赋值，
// 故 showRequiredMark 开启时强制直接赋值并刷新签名，绕过签名跳过逻辑。
if (this._opts.showRequiredMark) {
  this._revo.columns = columns
  this._revoPropSigs['prop:columns'] = this._columnsSignature(columns)
} else {
  this._setRevoProp('columns', columns, this._columnsSignature(columns))
}
```

#### 3.1.3 `afterheaderrender` 兜底（revo 内部重渲后重新挂）

revo-grid 内部 `column.service` 处理列时可能丢失函数引用（`before/aftercolumnsset` 之间），在 `afterheaderrender` 阶段重新挂一次 `_applyRequiredMarks`。

**效果**：5/5 必填列全部正确显示 `color: rgb(250,97,97) fontWeight: 700` 的红色 `*`。

---

### 3.2 编码列 readonlyWhen — 翻译为 `readonly` 函数 + 调整焦点路径

#### 3.2.1 `_patchReadonlyFn`：公式 → 函数翻译器

**[`cmx-revo-grid.js:444-466`](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/components/cmx-revo-grid.js#L444-L466)**

```js
_patchReadonlyFn(col) {
  if (!col) return
  if (Array.isArray(col.children)) {
    for (const c of col.children) this._patchReadonlyFn(c)
    return
  }
  if (col.readonly === true) return   // 业务锁列保持原状
  const cmxCol = col._cmxCol
  const rw = cmxCol?.edit?.readonlyWhen ?? cmxCol?.readonlyWhen
  if (typeof rw !== 'string' || !rw.trim()) return
  const prop = col.prop
  col.readonly = (model) => {
    const row = (model && typeof model === 'object') ? model : {}
    try {
      return !!evalFormula(rw, { ...row, value: row[prop], __col: prop }, false)
    } catch (_) { return false }
  }
}
```

**调用入口**（[`cmx-revo-grid.js:413-421`](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/components/cmx-revo-grid.js#L413-L421)）：
```js
_applyColumnModel(model) {
  const { columns, totals } = CmxColumnAdapter.toRevoGrid(model)
  // 把 _cmxCol.edit.readonlyWhen 翻译为 revo-grid 的 readonly 函数
  for (const c of columns) {
    this._patchReadonlyFn(c)
  }
  ...
}
```

**`formula-eval` scope 约定**：行字段直接铺平 + `value`（当前列值）。`formula-eval` 只认单段标识符，故条件用扁平字段名，如 `value < 0` 或 `NOT(STARTSWITH(id, 't'))`。

#### 3.2.2 `_onBeforeEditBound` 兜底拦截（双保险）

**[`cmx-revo-grid.js:1173-1189`](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/components/cmx-revo-grid.js#L1173-L1189)**

```js
this._onBeforeEditBound  = (e) => {
  const model = e.detail?.model
  if (model?.__cmxFiller) { e.preventDefault?.(); return }
  /* 列级条件只读 readonlyWhen：满足表达式时阻止进入编辑（行级动态只读） */
  const prop = e.detail?.prop ?? e.detail?.column?.prop
  const cmxCol = this._findRevoCol(prop)?._cmxCol
  const rw = cmxCol?.edit?.readonlyWhen ?? cmxCol?.readonlyWhen
  if (rw && model && evalFormula(rw, { ...model, value: model[prop], __col: prop }, false)) {
    e.preventDefault?.()
    return
  }
  this.setAttribute('data-cmx-editing', '1')
}
```

**为什么需要双保险**：revo-grid 的 `canEdit()` 调用栈在某些时序下（如单元格 focus 后但 editor 还没挂上）可能不走 `readonly` 函数；`beforeedit` 事件是编辑器打开前的最后一道门，是用户视角的"最终防线"。

#### 3.2.3 `_maybeEditOnFocus` 不再拦截函数形态的 readonly

**[`cmx-revo-grid.js:1347-1371`](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp/src/components/cmx-revo-grid.js#L1347-L1371)**

```js
_maybeEditOnFocus (e) {
  if (this._opts.readonly) return
  const detail = e?.detail
  const model = detail?.model
  if (!model || model.__cmxFiller || model.__cmxTotals) return
  const column = detail?.column
  if (!column) return
  // 仅布尔 true 才阻止编辑；函数形态由 revo-grid 内部按行判定
  if (column.readonly === true) return
  // ... 后面 click 触发 setCellEdit 不变
}
```

**关键改动**：原 `if (column.readonly) return` 会把 `readonly=function` 也当成 truthy 一并拦截，导致业务键列永远点不开。改为只对 `=== true` 拦截，函数形态交给 revo-grid 内部的 `canEdit` 流程。

---

## 四、readonlyWhen 逻辑时序图（修复后）

```
用户点击【编码列】单元格
  ↓
revo-grid 内部 canEdit(row, col)
  → col.readonly(model) = evalFormula('NOT(STARTSWITH(id, "t"))', {...row, value: row.code, __col: 'code'}, false)
  ↓
  ├─ 存量行：id='100' → NOT(false) = true → return true → 跳过编辑 ✓
  └─ 新增行：id='t123' → NOT(true)  = false → 继续
  ↓
打开编辑器（cmx-text-input）
  ↓
revo-grid 派发 beforeedit 事件
  → _onBeforeEditBound 再次校验
    → 存量行：preventDefault → 编辑器关闭 ✓
    → 新增行：放行 → 进入编辑态 ✓
  ↓
用户键入 NEW99
  ↓
afteredit 事件
  → _onAfterEdit 写入 model[rowIndex].code = 'NEW99' ✓
```

---

## 五、验证结果

通过 Playwright（`webapp-testing` 技能）自动化测试：

| 验证项 | 修复前 | 修复后 |
|---|---|---|
| 必填列 `*` 标识（5 列） | 0/5 显示 | **5/5** 显示（color=`rgb(250,97,97)`, fontWeight=`700`） |
| 编码列 readonly 函数（新增行 id='t...'） | 仍只读 | **False**（应可编辑） |
| 编码列 readonly 函数（存量行 id='100'） | 仍可编辑 | **True**（应只读） |
| 存量行双击编码列 → 编辑器打开 | 打开了 | **未打开**（PASS） |
| 新增行双击编码列 + 键入 `NEW99` | 写不进去 | **写入成功**（`newRowCode='NEW99'`） |
| 截图佐证 | — | `/tmp/regress_v3_loaded.png`（5 个红色 `*`）、`/tmp/regress_v3_final.png`（蓝色聚焦框 + `NEW99`） |

---

## 六、涉及文件清单

| 文件 | 改动点 |
|---|---|
| `packages/cmx-data-comp/src/components/cmx-revo-grid.js` | `_applyRequiredMarks` 改为原对象 mutate；`_syncToRevo` 在 `showRequiredMark=true` 时绕开签名比对；`_applyColumnModel` 调用 `_patchReadonlyFn`；`_patchReadonlyFn` 把 `readonlyWhen` 翻译为 `readonly` 函数；`_onBeforeEditBound` 兜底拦截；`_maybeEditOnFocus` 仅拦截布尔 `true` |
| `cmx-container/data/native-pages/sources/portal/dct/data-editor.js` | **无改动**——上游已正确设置 `colOpts.edit.readonlyWhen = 'NOT(STARTSWITH(id, "t"))'` 和 `colOpts.edit.required = true`，是 grid 组件侧未正确消费 |

---

## 七、经验总结

1. **Stencil lazy load 模式下"新建对象赋值"会丢失 prop**——必须直接 mutate 原对象，或在合适的时机（如 `componentDidLoad` 后）重新赋值。`columnTemplate` 这种函数 prop 尤其敏感，丢失后表现为 UI 完全不显示该模板，无 console 报错（最坑）。
2. **第三方库的 prop 形态约束要在适配层显式翻译**——revo-grid 的 `readonly` 只认 `boolean | function`，cmx 侧的 `readonlyWhen` 公式串需要 `_patchReadonlyFn` 这层翻译器，否则"配置写了等于没写"。
3. **focus 路径拦截与 edit 路径拦截是两条独立防线**——`_maybeEditOnFocus`（focus → setCellEdit）和 `_onBeforeEditBound`（beforeedit → preventDefault）都需正确处理条件只读；只改一处会被 revo-grid 内部时序绕过。
4. **Playwright 真实交互是唯一可信验证**——静态读代码看不出"原对象 vs 新对象"的差异，shadowRoot 内的 `columnTemplate` 也只能从浏览器运行时探测。
5. **避免在生产代码留调试日志**——开发期 `console.log` / `__dbg` / `window.__cmxDbg` 必须交付前清理（git diff 检查 `console\.(log|debug|info)|__dbg|__cmxDbg`）。
