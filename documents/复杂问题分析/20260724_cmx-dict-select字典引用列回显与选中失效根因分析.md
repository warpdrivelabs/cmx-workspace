# cmx-dict-select 字典引用列回显与选中失效根因分析

> 日期：2026-07-24
> 涉及模块：`packages/cmx-data-comp`（cmx-dict-select / cmx-dict-field-type / cmx-revo-grid / cmx-column / init-page-models）+ `cmx-container/data/native-pages/portal/dct/data-editor.js`

---

## 一、问题现象

字典引用列（`refDict`，如 `country_code` 引用 `country` 字典）在 grid 中存在三个互相关联的故障：

| # | 现象 | 影响范围 |
|---|---|---|
| 1 | **首次加载 400 错误**：`/api/dct/data/search?dict=xxx` 缺 domain/application/module 参数 | 所有通过元数据声明式引用（`metaModelId`）生成的 dict-select 列 |
| 2 | **首次加载单元格只显示 code**：`country_code='CNY'` 显示为 `CNY` 而非 `人民币` | 所有 dict-select 列（后端首次加载的行无展开字段） |
| 3 | **help 弹窗选"确定"后单元格不更新**：选中值后单元格仍为旧值或空值 | 所有 cmx-dict-select 组件（help 弹窗路径） |

---

## 二、根因分析（四层问题）

### 2.1 editSettings 未通过 toDescriptor 输出（根因 #1）

**文件**：`packages/cmx-data-comp/src/lib/cmx-column.js` → `toDescriptor()`

**问题**：`toDescriptor()` 输出了 `refDict` / `refField` / `displayField`，但**没输出 `editSettings`**。cmx-ui5-form 通过 `model.toDescriptors()` 提取字段时，editSettings（含 coord / idCol / labelCol）被丢弃。

**链路**：
```
cmx-ui5-form.setColumnModel(model)
  → _applyFields(toCmxFormGrouped(model))
    → model.toDescriptors()          // editSettings 丢失
      → form.write(field)
        → dictCfgFromField(field)    // es.coord = {} 空
          → createRestDictDataSource // URL 缺坐标 → 400
```

### 2.2 元数据驱动列模型不组装 editSettings（根因 #1 补充）

**文件**：`packages/cmx-data-comp/src/lib/init-page-models.js` → `metaTableFieldsToColumns()` + `backfillColumnCoord()`

**问题**：
- `metaTableFieldsToColumns` 对 refDict 列只设 `edit.mode='cmx-dict-select'`，不组装 editSettings（idCol / labelCol / dictCode）
- `backfillColumnCoord` 补建 editSettings 时只补 coord，不补 idCol / labelCol
- `host.$coord` 为空时（html-page 未注入），不从元数据模型实例取兜底坐标

### 2.3 dict-select 列的 cellTemplate 缺字典缓存兜底（根因 #2）

**文件**：`packages/cmx-data-comp/src/lib/cmx-dict-field-type.js` → `formatDictDisplayFromRow()` + `cmx-revo-grid.js` → `enableDictEcho()`

**问题**：两条回显路径互斥导致盲区：

| 路径 | 机制 | 适用 | 排除条件 |
|---|---|---|---|
| **A. enableDictEcho** | 拉全典→挂 `display.resolve`→cellTemplate 查表 | 只读 refDict 列 | 原代码 `edit.mode==='cmx-dict-select'` 时**跳过** |
| **B. dict-select cellTemplate** | 从行展开字段读（`applyDictRowToHost` 选中时写入） | dict-select 编辑列 | 后端首次加载的行**无展开字段**→降级显示 raw code |

dict-select 列被路径 A 跳过、路径 B 又读不到展开字段 → 盲区。

### 2.4 help 弹窗 ID 随机值陷阱（根因 #3）

**文件**：`packages/cmx-data-comp/src/components/cmx-dict-select.js` → `_loadHelpGrid()` + `openHelp()`

**问题**：`_loadHelpGrid` 把字典行直接 `ds.setRows(items)`，但字典行没有 `id` 字段（主键列名是 `code`），CmxDataSet 生成随机占位 id（如 `r123`）。

help 弹窗确认后：
```js
const ids = grid.getSelectedIds()          // → ['r123']（随机 id）
const idCol = this._cfg.idCol              // → 'code'
const plain = rows.find(r => String(r[idCol]) === String(id))
// r.code='CNY' !== 'r123' → 匹配失败 → plain = undefined
// → 不调 _commitRow → 不派发 cmx-dict-change 事件
// → grid 编辑器回调不触发 → 单元格不更新
```

---

## 三、修复清单

### 3.1 `cmx-column.js` — toDescriptor 输出 editSettings

```js
// toDescriptor() 末尾，在 refField/displayField 之后追加：
if (this.editSettings != null) d.editSettings = this.editSettings
```

**效果**：form 端从 descriptor 构建字段时不再丢 editSettings（coord / idCol / labelCol），消除 400。

### 3.2 `init-page-models.js` — metaTableFieldsToColumns 组装 editSettings

```js
// metaTableFieldsToColumns 内，对 refDict 列：
if (hasRefDict && mode === 'cmx-dict-select') {
  const metaEs = (c.editSettings && typeof c.editSettings === 'object') ? { ...c.editSettings } : {}
  colOpts.editSettings = {
    ...metaEs,
    dictCode: metaEs.dictCode || c.refDict,
    idCol: metaEs.idCol || c.refField || 'code',
    labelCol: metaEs.labelCol || c.displayField || 'name',
  }
}
```

**backfillColumnCoord 补建时也补 idCol/labelCol**：
```js
col.editSettings = {
  dictCode: col.refDict,
  idCol: col.refField || 'code',
  labelCol: col.displayField || 'name',
  coord: merged,
}
```

**host.$coord 为空时从元数据模型实例取兜底**：
```js
const metaCoord = {
  domain: meta.domain || '',
  application: meta.application || meta.app || '',
  module: meta.module || '',
}
const fallbackCoord = (globalCoord.domain || globalCoord.application || globalCoord.module)
  ? globalCoord
  : metaCoord
backfillColumnCoord(model, fallbackCoord)
```

### 3.3 `cmx-revo-grid.js` — enableDictEcho 不再跳过 dict-select 列 + setColumnModel 自动触发

**enableDictEcho 移除跳过逻辑**：
```js
// 原：if (col.edit?.mode === 'cmx-dict-select') continue
// 改：对所有有 refDict 的列都挂 resolver
```

**setColumnModel 后自动触发字典回显**：
```js
// setColumnModel 末尾追加：
this._autoEnableDictEcho()

// _autoEnableDictEcho：从列 editSettings.coord 取坐标，异步调 enableDictEcho
```

### 3.4 `cmx-dict-field-type.js` — cellTemplate 降级到 display.resolve

**fieldFromGridCellProps 带出 resolve**：
```js
return cmxCol
  ? { ..., resolve: cmxCol.display?.resolve }
  : { ..., resolve: column.display?.resolve }
```

**formatDictDisplayFromRow 在展开字段和 _label 都缺失时，降级到 resolve**：
```js
if (typeof field.resolve === 'function' && raw != null && String(raw) !== '') {
  const resolved = field.resolve(raw)
  if (resolved != null && String(resolved) !== '' && String(resolved) !== String(raw)) return String(resolved)
}
return raw == null ? '' : String(raw)
```

### 3.5 `cmx-dict-select.js` — _loadHelpGrid 按 idCol 重塑行 id

```js
async _loadHelpGrid (grid, filter) {
  // ...
  const idCol = this._cfg.idCol || 'id'
  const fixed = (Array.isArray(items) ? items : []).map((r) => ({ ...r, id: r[idCol] ?? r.id }))
  ds.setRows(fixed)
  // ...
}
```

**效果**：help grid 的行 id 就是字典的 `code` 值，`getSelectedIds()` 返回 `['CNY']`，与 `r[code]` 匹配成功 → 派发 `cmx-dict-change` → 回调触发 → save + applyDictRowToHost 正常执行。

### 3.6 `cmx-dict-select.js` — _syncClearVisible 空值保护

```js
// 原：this._clearBtn.hidden = !show
// 改：if (this._clearBtn) this._clearBtn.hidden = !show
```

**效果**：修复 setValue 在 connectedCallback（_cacheEls 填充 _clearBtn）之前被调用时的 `Cannot set properties of undefined` 崩溃。

---

## 四、修复后的回显优先级链

```
formatDictDisplayFromRow 渲染（从高到低）：
  1. 展开字段 row['field.dictCode.name']（选中时 applyDictRowToHost 写入）→ "编码 - 名称"
  2. _label 冗余字段 row['field_label']（选中时写入）
  3. display.resolve（enableDictEcho 从 CmxDictCache 挂上）→ 名称  ← 新增兜底
  4. raw code 值（最终降级）
```

---

## 五、验证结果

通过 Playwright 自动化测试验证：

| 验证项 | 修复前 | 修复后 |
|---|---|---|
| 400 错误数 | 5 个（coa / acct_group / account_type / currency / comp_unit） | **0 个** |
| 首次加载 acct_group_code 显示 | `"A001"` | **`"流动资产科目组"`** |
| help 弹窗选确定后 | 单元格不更新（事件不派发） | 单元格更新为选中值 |

---

## 六、涉及文件清单

| 文件 | 改动点 |
|---|---|
| `packages/cmx-data-comp/src/lib/cmx-column.js` | `toDescriptor` 输出 editSettings |
| `packages/cmx-data-comp/src/lib/init-page-models.js` | `metaTableFieldsToColumns` 组装 editSettings；`backfillColumnCoord` 补 idCol/labelCol；host.$coord 为空时从元数据模型取兜底坐标 |
| `packages/cmx-data-comp/src/components/cmx-revo-grid.js` | `setColumnModel` 后自动触发 `_autoEnableDictEcho`；`enableDictEcho` 不再跳过 dict-select 列 |
| `packages/cmx-data-comp/src/lib/cmx-dict-field-type.js` | `fieldFromGridCellProps` 带出 resolve；`formatDictDisplayFromRow` 降级到 display.resolve |
| `packages/cmx-data-comp/src/components/cmx-dict-select.js` | `_loadHelpGrid` 按 idCol 重塑行 id；`_syncClearVisible` 空值保护 |

---

## 七、经验总结

1. **toDescriptor 是 form/grid 双端的字段契约**——新增的字段属性（如 editSettings）必须在 toDescriptor 里输出，否则 form 端会丢配置。
2. **两条回显路径不能简单互斥**——dict-select 编辑列既需要路径 B（选中时的展开字段），也需要路径 A（首次加载时的字典缓存）。两者是互补关系，不是替代关系。
3. **CmxDataSet 的 id 字段约定是隐式契约**——行没有 `id` 字段时会生成随机占位 id，所有 `setRows` 前都应确保 id 字段与组件期望的 idCol 对齐。
4. **Playwright 运行时调试 + CDP 调用栈追踪**是定位前端"请求缺参数""事件不触发"类问题的有效手段——比纯静态代码分析更快定位到真正的调用路径。
