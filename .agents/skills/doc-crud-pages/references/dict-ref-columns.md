# 字典引用列配置

> 本文件是 doc-crud-pages 技能的 references 细节层（从 SKILL.md 下沉，内容未改）。返回决策入口：[../SKILL.md](../SKILL.md)

## 七、字典引用列配置（极易配错，单独一章）

详情/列表页的字典选择列（cmx-dict-select）涉及 refField/displayField/dictCode/helpLayout 多个配置，配错会导致**存值不一致**或**弹窗左树空**。

### 7.1 字段名语义决定 refField（存 id 还是 code）

| 字段名后缀 | 字段类型 | 应存的值 | refField | 例子 |
| --- | --- | --- | --- | --- |
| `_id` | BIGINT/INT | 字典的 id | `id` | comp_unit_id、cost_center_id |
| `_code` | VARCHAR | 字典的 code | `code` | ledger_code、period_code |

> **铁律**：字段名带 `_id` 存 id（字典必须有 id 列），字段名带 `_code` 存 code。**表头和子表的同名字段必须 refField 一致**，否则同一业务实体在表头和子表存不同类型的值（如公司代码表头存 id=1、分录存 code="1000"），数据不一致。

### 7.2 displayField（显示什么）

`displayField` 决定回显时显示字典的哪个字段。按业务需求选 `name`（名称，友好）或 `code`（编码，精确）。**同一字段在各表/页面要统一**。

### 7.3 dictCode（字典弹窗定位）

`editSettings.dictCode` 是字典的真实编码（通常是 `cf_<refDict>`）。**必须有**，否则字典弹窗定位失败。列模型生成时若无 dictCode 会退回 refDict 名，可能导致弹窗拉不到数据。

完整配置模板（以 comp_unit_id 存 id 为例）：

```jsonc
{
  "id": "comp_unit_id", "refDict": "comp_unit", "refField": "id", "displayField": "name",
  "edit": { "mode": "cmx-dict-select" },
  "editSettings": {
    "dictCode": "cf_comp_unit",          // 必填：字典真实编码
    "coord": { "domain": "fi", "application": "cmxfico", "module": "gl" },
    "idCol": "id",                        // 与 refField 一致
    "valueField": "id",                   // 弹窗选中后回填的值（与 refField 一致）
    "labelCol": "name"                    // 弹窗显示列
  }
}
```

### 7.4 helpLayout：仅真分级字典才能用 classify

`helpLayout: "classify"`（左分类树 + 右 grid）要求字典**有 parent_id 层级数据**（selfHierarchy=true）。平级字典配 classify 会导致**左侧树空白**。

| helpLayout | 适用 | 左树 |
| --- | --- | --- |
| 不配（默认 grid） | 所有字典 | 无左树，直接平铺 |
| `classify` | **仅真分级字典**（如会计科目 gl_account） | 按 parent_id 建分类树 |

> **检查方法**：配 classify 前，确认字典的 DCT 元数据 `selfHierarchy=true` 且 seed 数据有非空 `parent_id`。否则去掉 helpLayout 用默认 grid。

### 7.5 字典回显（grid 列显示名称而非原始 id/code）

**已知技术债**：`cmx-revo-grid` 的 `_autoEnableDictEcho()` 被注释（性能问题，待优化）。grid 字典引用列默认不自动翻译 id/code 为名称。

如需回显，在 initPage 对可编辑 grid 手动调一次 `enableDictEcho`（共享同一 coord，CmxDictCache 内部去重）：

```js
// initPage（详情页）—— 视需求决定是否启用回显
var coord = { domain: "...", application: "...", module: "..." };
['#headerGrid','#gAcc','#auxGrid'].forEach(function(sel){
  var g = host.shadowRoot.querySelector(sel);
  if (g && typeof g.enableDictEcho === 'function') {
    g.enableDictEcho({ coord: coord }, host);   // 异步预加载字典 + 挂 resolver
  }
});
```

> 这会触发字典数据网络请求，字典多/大时有性能开销。是否启用需权衡（这是 `_autoEnableDictEcho` 被注释的原因）。

---
