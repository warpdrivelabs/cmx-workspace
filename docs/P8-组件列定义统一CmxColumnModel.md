# P8 — 可视组件列定义统一为 CmxColumnModel（删 cmx-ui5-table）

## 背景与目标
当前 `cmx-revo-grid` / `cmx-ui5-form` 同时支持三条列定义入口：CmxColumnModel(`setColumnModel`) + 自有 API(`setColumns`/`setFields`) + 声明式属性(`data-cmx-columns`/`data-cmx-fields`)，命名与机制割裂。

**目标**：这两个组件的列/字段定义**只能通过 CmxColumnModel**（运行时 `setColumnModel` + 设计器 `data-cmx-model-id`），关闭一切自有列设置 API 与内联列属性。未来同类组件也只走 CmxColumnModel。同时**删除 cmx-ui5-table 组件**（性能差）。

## 已确认决策
1. 旧 API 全部关闭，不对外提供（硬删，非软包装）
2. cmx-ui5-table 整组件删除
3. 存量演示页面按需迁移（本轮不强制全迁，受影响页面待用时改为 model-id）

## 现状（调研结论）
- **两组件已具备** `setColumnModel(model)` + 监听 `columns-changed` 动态重渲染（revo-grid:231-268、ui5-form:236-248）——CmxColumnModel 路径完整。
- **声明式绑定协议已贯通**：`data-cmx-model-id="<instanceId>"` → `init-page-models.js:203-207` 自动 `el.setColumnModel(host[modelId])`。
- **设计器 inspector 已有** CmxColumnModel 选择行（revo:71-78、form:62-69）。
- 缺口：两组件还保留自有列 API + 内联属性解析；inspector 还暴露内联列编辑；cmx-ui5-table 仍存在且被引用。

---

## 改造清单

### A. cmx-revo-grid.js — 关闭自有列 API
保留：`setColumnModel`/`_applyColumnModel`（唯一入口）、`_syncToRevo`、`_columns`/`_headerGroups`（降级为"仅由 `_applyColumnModel` 回填的派生缓存"，下游 totals 等仍读）。
删除：
- `setColumns`(274-281)、`setHeaderGroups`(287-294)、`_rebuildRevoColumns`(627-632)
- `_bootstrapFromAttributes`(607-619) 中 `data-cmx-columns`(609,615) 与 `data-cmx-header-groups`(610,616) 两支解析
- `_syncToRevo` 行 770 的 `_rebuildRevoColumns` 兜底
- `setTotals`：totals 改由 model 透传（`_applyColumnModel` 已合入 `_opts.totals`）；移除 `data-cmx-totals` 解析(611,617) 与 `setTotals`(357-360)
保留 `data-cmx-options` / `data-cmx-rows`（非列定义）。

### B. cmx-ui5-form.js — 关闭自有字段 API
保留：`setColumnModel`(236-248) 唯一入口、内部 `_fields`/`_fieldTree`（由 model 回填）。
删除：
- `setFields`(257-263) 对外能力（改为内部私有 `_applyFields`，仅 `setColumnModel` 回调调用）
- `_bootstrapFromAttributes` 中 `data-cmx-fields` 解析(121,124)

### C. data-cmx-model-id 声明式通道（已存在，确认即可）
运行时 `init-page-models.js:203-207` 已实现。两组件 `connectedCallback` 不再读内联列定义后，纯靠 init 流程注入 model。无需新增代码。

### D. 删除 cmx-ui5-table
- 删文件 `packages/cmx-data-comp/src/components/cmx-ui5-table.js`
- `index.js`:12(import)、:29(export) 删
- `package.json`:19 export 子路径删
- `../cmx-html-designer`：import (:20)、inspector import (:34)、调色板块 (:149-167)、customInspectors 映射 (:410) 删
- 删 `../cmx-html-designer` 整文件
- `cmx-column-adapter.js` 的 `toCmxUi5Table`(280) 及私有辅助(287/314/332/361) 删（死代码）
- ref-picker 内嵌 cmx-ui5-table(cmx-ui5-table.js:899) 随文件删除消失，无外部联动（已确认 revo-grid/ui5-form 无内嵌 ui5-table 用法）
- 次要：`event-script-hints.js`:42/53/55 文案、文档/注释（README、docs、各源文件注释里把 ui5-table 当参照物的）按需清理

### E. 设计器 inspector — 移除内联列编辑入口，只留 model 选择行
- `build-cmx-revo-grid-inspector.js`：删 `cmx-columns-editor` import(:8)+块(:89-96)、`headerGroups` textarea(:100)、`totals` textarea(:101)；保留 modelId 选择行(:71-78)、masterSlaveId、datasetId、options/rows
- `build-cmx-ui5-form-inspector.js`：删 `fields` textarea(:117)；保留 modelId 选择行(:62-69)、masterSlaveId、datasetId、layout/header/sources/row
- `cmx-data-plugin.js` 五处旧式 `data-cmx-model-id` 纯文本框入口(:61/107/168/205/244) 与新选择行并存——审视，revo/form 改为只留选择行；同时清理这两个组件 attrs 列表里的 `data-cmx-columns`/`data-cmx-fields`/`data-cmx-header-groups`
- `cmx-columns-editor.js`：若删 ui5-table + revo 后无人引用则删除（form 本就不用它；确认仅 revo inspector 引用过 → 一并删）

### F. 存量演示页面（按需，本轮不强制）
受影响（用内联列定义）：`trade.html`/`trade-form.html`/`trade-neo.html`/`voucher.html`/`voucher-neo.html`/`travel-expense-neo.html` 等。
本轮**不迁移**，待需要时逐个改为 `models[]` 定义 CmxColumnModel + 视图加 `data-cmx-model-id`（参照 `ccm-attrs-test.html`/`gl-voucher-v1-demo.html` 已用 model-id 的范例）。本轮可挑 1 个代表页（如 voucher）迁移并实测，验证链路。

---

## 实施步骤（每步可验证）
| 步 | 内容 | 验证 |
|---|---|---|
| 1 | cmx-revo-grid 关闭自有列 API（A） | 单测 + 用 model-id 的页面(ccm-attrs-test)正常渲染列 |
| 2 | cmx-ui5-form 关闭自有字段 API（B） | 用 model-id 的 form 页面正常 |
| 3 | 删 cmx-ui5-table + 清引用（D） | 构建通过、无断引用 |
| 4 | 设计器 inspector 收口（E） | 设计器选中 revo/form 只见 model 选择行；选 model 后页面生效 |
| 5 | 迁 1 个代表页(voucher)到 model-id（F） | 浏览器实测该页表格/表单正常 |
| 6 | 清理死代码(toCmxUi5Table)、文档、cmx-columns-editor | lint + 构建 + 全量回归 |

## 风险
- **totals 策略**：revo-grid 的 totals 现可由 model 透传，但删 setTotals 后需确认 model 的 aggregate 能完整表达现有 totals 用法（CmxColumnGroup.aggregate 已支持）。
- **`_columns`/`_headerGroups` 下游**：必须保留由 `_applyColumnModel` 回填，否则 `_renderTotals`/`_validateCellEdit` 读空。改造时只删"写入旁路"，不删字段本身。
- **存量页面空表**：F 不全迁会导致部分演示页空表——已与用户确认按需迁移，受影响页待用时改。
- **ref-picker 功能**：cmx-ui5-table 的外键搜索弹窗随删除消失；其外键选择场景由 cmx-combo-box(grid/tree/list picker) 承接（revo-grid 路线已有），属功能迁移、非断引用。

## 验证标准
- cmx-data-comp 全测试通过
- 构建成功、无对 cmx-ui5-table 的断引用
- 用 data-cmx-model-id 的页面（ccm-attrs-test 等）列/字段正常渲染、动态列(columns-changed)生效
- 设计器选中 revo-grid/ui5-form 只通过 model 选择行配列、保存的页面运行正常
- 代表页(voucher)迁移后浏览器实测通过
