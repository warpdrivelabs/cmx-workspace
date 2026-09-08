# P4 — 三端列定义 UI 统一（共享 schema 驱动）实施计划

## 目标
数据字典(DCT) / 业务单据(DOC) / 弹性组合 三端的「列/字段定义 UI」统一：
- 基于 `<table>` 的**列表内联编辑**
- property 区的**属性详编面板**

两块都由**一份共享的"列定义 schema"驱动渲染**，属性取并集并合并同类项。各端键名差异（fieldName / code / id）通过**适配器**桥接，**不动存盘数据**（零迁移、向后兼容）。

## 已确认决策
1. 统一强度 = **共享 schema 驱动（彻底）**
2. 字段键名 = **保留各端键名 + 适配器**（不改存盘 JSON / store / 引擎）
3. （前序 P0-P2 已落地）录入控件统一为 `edit.mode` 全集值域；display 子键规范名

---

## 架构设计

### 新增共享模块（packages/cmx-data-comp/src/lib/）

**A. `cmx-field-schema.js` — 列定义 schema（单一事实来源）**
描述"一个字段/列可设的所有属性"，取三端并集、合并同类项。每个属性条目形如：
```
{
  key: 'caption',              // 规范属性键
  label: '标题',               // 中文标签
  control: 'text'|'number'|'select'|'checkbox'|'select-labeled'|'dict-ref'|'formula'|'multiselect'|'readonly-text',
  section: 'basic'|'reference'|'constraint'|'display'|'edit'|'governance'|'control'|'advanced',
  placement: 'inline'|'panel'|'both',   // 在表格内联 / property 面板 / 两者
  options?: (ctx)=>[{value,label}] | [...],  // 下拉选项 provider（支持动态+防丢值）
  enableWhen?: (row,ctx)=>bool,         // 如长度随 dataType 联动
  visibleWhen?: (row,ctx)=>bool,        // 如 dict 块仅 dimension 显示
  appliesTo?: ['DCT','DOC','CTX'],      // 该属性属于哪些端（取并集后按端过滤）
  valueType?: 'string'|'number'|'boolean'|'boolean-visible'|'list',
}
```
分区（section）合并同类项后的统一集合：
- **basic**：字段名 / 标题 / 数据类型 / 长度·整数位·小数位 / 可空 / 维度类型(kind/dimType) / 维度绑定
- **reference**：引用字典 / 引用字段 / 显示字段（DCT 的 refDict 三件套 ∪ 档案的 dict.*）
- **edit**：录入控件(edit.mode 统一值域) / 必填 / 占位符 / 条件必填 / 条件只读
- **display**：对齐 / 显示模式 / 格式 / 小数位 / 千分位 / 0显示空 / 负数红字
- **constraint**：默认值 / 唯一 / 校验正则 / 枚举值 / 校验规则(validations[])
- **governance**：敏感级别 / 多语言 / 可搜索 / 可筛选
- **control**：必填条件 / 可编辑条件 / 可见条件（fieldControl.* ∪ edit.*When）
- **compute**：公式 / 依赖 / 属性带出 source / 默认值 defaultFrom（档案特有，appliesTo=CTX）
- **advanced**：列属性逃生舱 field.column.*（档案特有；P3 已规划折叠，这里归入高级区）

每个属性标 `appliesTo`，渲染时按当前端过滤——这就是"并集 + 按端裁剪"。

**B. `cmx-field-adapter.js` — 各端字段对象 ↔ 规范属性的 get/set 适配器**
三个适配器（DCT/DOC、CTX、未来设计器），每个实现：
```
{
  getProp(field, key, ctx) -> value      // 读：把规范 key 映射到该端存储键（caption←→fieldName/code/...）
  setProp(field, key, value, ctx)        // 写：含特殊键行为（enumValues 数组、fieldControl.* 点路径、dataType 联动、refDict 联动、boolean-visible）
  listFields(owner) / addField / removeField / moveField
  options(key, field, ctx)               // 动态下拉（refDict/refField/uiControl…）+ 防丢值
}
```
键名映射表（规范 → 各端存储键）：

| 规范 key | DCT/DOC 存储 | CTX 存储 |
|---|---|---|
| fieldName | `fieldName` | `code` |
| caption | `label`(回退fieldComment) | `caption` |
| description | `fieldComment` | （无） |
| type(逻辑) | 由 `dataType`(VARCHAR…) 映射 | `dataType` |
| dataType(物理) | `dataType` | （无，保留物理仅DCT） |
| kind/维度语义 | `dimType` | `kind` |
| editMode | `uiControl`(经 toEditMode) | `edit.mode` |
| required | `fieldControl.requiredWhen`有/无 近似 | `edit.required` |
| refDict/refField/displayField | 同名 | `dict.dictId/valueField/labelField` |
| display.* | （DCT无，仅占位） | `display.*` |
| validations | `pattern`→单条 | `validations[]` |

> 写盘仍是各端原键名——适配器只在 UI 读写时桥接。

**C. `cmx-field-ui.js` — schema 驱动的渲染器（纯函数，输出 HTML 字符串）**
```
renderFieldTable(fields, {schema, adapter, ctx, selectedKey, placement:'inline'}) -> html
renderFieldPanel(field,  {schema, adapter, ctx}) -> html   // 按 section 分区渲染详编
```
- 沿用现有 data 协议：`data-field-key` + `data-field-prop`（表格内联）、`data-field-path`/`fp()`（面板）、`data-action`（select/add/remove/move/open-formula/add-validation…）
- 控件渲染收敛：`text/number/checkbox/select/select-labeled/multiselect/dict-ref/formula/readonly-text` 一组统一控件函数（合并现有 `selOpt`/`selOptLabeled`/`selectHtml`/`chk`/`txt`/公式按钮）
- option provider + 防丢值统一包装
- `enableWhen`（长度联动）/`visibleWhen`（dict 块按 kind）统一钩子

**D. `cmx-field-events.js` — schema 驱动的事件处理（可选，或保留在各主体）**
统一 `handleFieldClick(e, {adapter,ctx})` / `handleFieldInput(e, {adapter,ctx})`，分发到 adapter 的 setProp / add / remove / move / 公式 / 校验。

### 各端接入（薄改）
两端主体（definition-manager / flexible-combination-manager）：
- 字段表格渲染：`_renderGroupTable` / `_renderFieldsTable` → 调 `renderFieldTable(..., adapter=DCT/CTX)`
- 详编面板渲染：`_renderFieldDetailHtml` / `_renderInspector`(字段分支) → 调 `renderFieldPanel(...)`
- 事件：`_handleClick`/`_handleInput` 字段分支 → 委托 `handleFieldClick/Input`（或保留薄分发到 adapter.setProp）
- 各端保留自己的"宿主对象"获取（DCT 的 fieldGroups/只读引用组、CTX 的 fsc.fieldsOwner、字段集 tab）——这些是端特有结构，schema 渲染器接收"已取好的 fields[] + 该组是否 editable"

### 保留各端特有能力（不强行合并）
- DCT/DOC：引用 fieldSet **只读组**（editable=false，纯文本 + dimension 行 refDict 例外）、数据类型长度联动、引用模板列
- CTX：公式编辑器模态、字段集 tab、维度 source/defaultFrom 带出、列属性逃生舱、校验 validations[]、移动排序
- 这些通过 schema 的 `appliesTo` + `placement` + 端 ctx 能力开关表达，不影响另一端

---

## 实施步骤（分阶段，每步可独立验证）

| 步 | 内容 | 验证 |
|---|---|---|
| 1 | 建 `cmx-field-schema.js`：把三端属性并集编码为 schema（含 section/appliesTo/control/options/enableWhen）。纯数据 + 单测 | schema 单测：每端过滤出的属性集与现状一致 |
| 2 | 建 `cmx-field-adapter.js`：DCT/DOC 适配器 + CTX 适配器（get/set/options/list）。单测覆盖特殊键（enumValues/fieldControl/dataType联动/refDict联动/boolean-visible/键名映射） | adapter 单测全绿 |
| 3 | 建 `cmx-field-ui.js`：renderFieldTable + renderFieldPanel + 统一控件函数。先以 DCT 端跑通（替换 `_renderGroupTable`+`_renderFieldDetailHtml`），保持 data 协议不变 | DCT 定义页：表格内联 + 详编逐项回归（增删改、长度联动、引用字典、录入控件、约束/治理/控制） |
| 4 | CTX 端接入：替换 `_renderFieldsTable`+`_renderInspector`(字段分支)，复用同一渲染器；公式/校验/带出作为 CTX 专属 section 注入 | 弹性组合页：字段表 + 详编 + 公式编辑器 + 字段集 tab + 校验 全回归 |
| 5 | 事件层统一（可选）：抽 `handleFieldClick/Input`，两端委托 | 两端交互回归 |
| 6 | 清理：删除两端重复的 selOpt/selectHtml/chk/txt 等，收敛到共享控件函数 | lint + 构建 + 全量回归 |

> 建议先做 **步1-3（schema+adapter+DCT接入）** 作为第一里程碑验证可行性，再做步4 CTX 接入（CTX 更复杂），最后步5-6 收尾。

## 风险与规避
- **风险：UI 重构面大，回归成本高** → 分端分步，data 协议（data-field-prop/data-field-path/data-action）保持不变，渲染输出 HTML 等价替换，可逐项对照
- **风险：CTX 的公式/字段集 tab/逃生舱 复杂** → 不塞进 schema 通用区，作为 CTX 专属 section/能力开关，渲染器留扩展点
- **风险：只读引用组（DCT）特殊** → 渲染器接收 `editable` 标志，editable=false 走只读文本分支（含 dimension 行 refDict 例外作为列级 `editableWhen`）
- **零数据迁移**：适配器只在 UI 读写桥接，存盘键名不变，引擎/store 不动

## 不在本次范围
- P3（消除 CTX field.column 双轨）——可与步4 顺带，但作为独立项
- P5（设计器两套列编辑器合一）——CMXHTMLDesigner 侧，后续
- P6（映射层集中测试）——随步2 adapter 单测部分完成

## 验证标准
- 新增 schema/adapter/ui 单测全绿
- 引擎现有 65 测试不回归
- portal 构建成功
- DCT / DOC / 弹性组合三页字段定义功能逐项回归（增删改、各属性编辑、联动、公式、字段集、引用组）
