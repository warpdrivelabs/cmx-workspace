# DOC 装载路径缺口（不归本技能管）

> 元数据 `cmxfico_doc_meta_v2.json` 经过 `meta-enricher` 补全后，所有字段都有正确的 `edit.mode` / `display` / `width` / `required` / `visible` / `frozen`。**但运行时不一定能消费到这些属性**——因为 DOC 装载路径本身有缺口。

权威分析见 [docs/表格组件编辑渲染体系与三元定义缺口分析.md §6.2](../../../../docs/表格组件编辑渲染体系与三元定义缺口分析.md)。

## 问题

[cmx-doc-meta-loader.js](../../../../packages/cmx-data-comp/src/lib/cmx-doc-meta-loader.js) 的 `buildColumnModel` **只消费 6 个属性**：

```js
new CmxColumn({
  id: c.name,
  caption: c.caption || c.name,
  dataType: c.dataType || 'VARCHAR',
  width: defaultWidth(c.dataType, c.name),
  align: alignFor(c.dataType),
  editMode: (c.isPrimaryKey || SYSTEM_COLS.has(c.name)) ? 'readonly' : undefined,
})
```

DOC 字段上的 `edit.mode` / `dimType` / `agg` / `refDict` / `displayField` / `fieldLength` / `decimalDigits` / `nullable` / `pattern` / `enumValues` / `display` **全部丢弃**。

## 典型表现

- DOC 金额列的 `decimalDigits: 4` 被忽略，一律走 grid 默认 2 位
- DOC 的 `refDict`（如 `account_id → gl_account`）不生成 dictSettings，退化成裸文本输入
- DOC 没有 display/format 概念，千分位/负数红字全走默认

## 修复方向（不归本技能）

需要一个类似 FLC `_fieldToColumn`（[flexible-combination-engine.js](../../../../packages/cmx-data-comp/src/lib/flexible-combination-engine.js)）的完整映射函数，把 DOC 字段的编辑/渲染语义真正落到 CmxColumn。

伪代码：

```js
const members = cols.map((c) => new C.CmxColumn({
  id: c.name,
  caption: c.caption || c.name,
  dataType: c.dataType || 'VARCHAR',
  length: c.fieldLength,                    // ★ 补
  integerDigits: c.intDigits,               // ★ 补
  decimalDigits: c.decimalDigits,           // ★ 补
  agg: c.agg,                               // ★ 补
  width: c.width || defaultWidth(c.dataType, c.name),
  editMode: (c.isPrimaryKey || SYSTEM_COLS.has(c.name)) ? 'readonly' : (c.edit?.mode),
  required: c.edit?.required,               // ★ 补
  // refDict → 生成 editSettings（dict-select 配置）   ★ 补
  // display → 透传                                    ★ 补
  // enumValues → edit.options                         ★ 补
}))
```

## 本技能能做 vs 不能做

| 能力 | 本技能 | DOC 装载修复 |
|---|---|---|
| 补全元数据 JSON 里的 edit/display/width/required/visible/frozen | ✅ | — |
| 验证值域合法 | ✅ | — |
| 让 `__designer_meta__` 里的字段描述正确 | ✅ | — |
| 运行时 DOC 装载消费这些属性 | ❌ | ✅（需改 `cmx-doc-meta-loader.js`） |
| `defaultValue` / `unique` / `sensitive` 等运行时消费 | ❌ | —（CmxColumn 无此键） |

## 临时绕过方案

如果需要在 DOC 动态装载后保留完整编辑/渲染语义，可在 pageFn 里手动构造 CmxColumn（参考 [html-page-generator 技能](../../html-page-generator)）：

```js
// pageFns/initData 末尾追加：
const cols = host.docMetaVoucherTables.flatMap(t => t.fields.map(f => new CmxColumn({
  id: f.id,
  caption: f.caption,
  dataType: f.dataType,
  edit: f.edit,
  display: f.display,
  width: f.width,
  required: f.required,
  visible: f.visible,
  frozen: f.frozen,
})));
host.ms.columnModels.forEach(cm => cm.members = [...cm.members, ...cols]);
```

待 `cmx-doc-meta-loader.js` 增强后可删。
