---
name: meta-enricher
description: 为 CMX 字典/单据元数据（backend/cmx-container/assets/model/data/meta/definitions）批量补全 edit / display / width / required / visible / frozen 等列属性。当用户要求"补全元数据字段的录入控件和显示属性""按规范值域给字段加 edit.mode/display""修复元数据的合法值"或提到 EDIT_MODES、display.mode、field-edit-display-modes、cmx-field-uicontrol、cmx-field-schema、enrich-meta 时必用。严格按 cmx-data-comp 规范值域生成，幂等不覆盖手工值。
---

# Meta Enricher（元数据属性补全器）

为 `backend/cmx-container/assets/model/data/meta/definitions/**` 下的字典/单据/字段集 JSON，**自动按 cmx-data-comp 规范值域**补全 `edit.*` / `display.*` / `width` / `required` / `visible` / `frozen` 等列属性。

> **核心原则**：不发明短名、不踩规。edit.mode 严格用 `packages/cmx-data-comp/src/lib/cmx-field-uicontrol.js` 的 `EDIT_MODES` 16 规范值；display.mode 严格用 `packages/cmx-data-comp/src/lib/cmx-field-schema.js` 中 `display.mode` 控件的 options 合法值（7 个含空串：''/text/number/badge/link/icon/actions；actions 属页面级操作列，元数据补全不涉及）。

---

## 一、何时用

| 场景 | 用本技能 |
|---|---|
| 新建/导入字典/单据定义 JSON，字段没写 edit/display | ✅ 自动按 dataType + caption + refDict 推导 |
| 已有定义，但 edit.mode 用了 `text`/`number` 等非法短名 | ✅ 强制重写为规范值 |
| display.mode 写成了 `date`/`datetime`/`checkbox` | ✅ 强制重写为 `text`/`number`/`badge` |
| 想给字段加 width/required/visible/frozen | ✅ 统一补默认 |
| 想用 `tree-ref` 树形引用 | ❌ 改用 `cmx-dict-select` + `parent: 'parent_id'`（脚本自动） |
| 手工调过某字段的 edit/display | ❌ 脚本幂等不覆盖 |
| 校验某元数据文件所有值域合法 | ✅ 用 `scripts/verify-meta.mjs` |

## 二、复杂度速判

| 表类型 | 用到的模型属性 | 走哪条规则 |
|---|---|---|
| `dictionaryTables[i]` 字典表 | `dictMeta.selfHierarchy` 决定 `parent_id` 是否树形 | `enrichDctTable()` |
| `voucherTables[i]` 单据表 | `segment`/`fs_version`/`cons_org` 默认树形引用 | `enrichDocTable()` |
| `fieldSets.<name>` 字段集 | 普通 | `enrichBaseFieldSet()` |

## 三、命令

```bash
# 1. 补全（dry-run：先输出到 .out.json，看 diff 再覆盖）
node .agents/skills/meta-enricher/scripts/enrich-meta.mjs \
  backend/cmx-container/assets/model/data/meta/definitions/base/base_dct_meta_v1.json \
  /tmp/base_dct.out.json

# 2. 校验（CI 友好：发现非法值 exit code=1）
node .agents/skills/meta-enricher/scripts/verify-meta.mjs \
  backend/cmx-container/assets/model/data/meta/definitions/base/base_dct_meta_v1.json \
  backend/cmx-container/assets/model/data/meta/definitions/fi/cmxfico/gl/cmxfico_dct_meta_v3.json

# 3. 批量：对 definitions 下所有 base + fi/cmxfico 文件
for f in backend/cmx-container/assets/model/data/meta/definitions/base/*.json \
         backend/cmx-container/assets/model/data/meta/definitions/fi/cmxfico/gl/*.json; do
  out="/tmp/$(basename $f .json).out.json"
  node .agents/skills/meta-enricher/scripts/enrich-meta.mjs "$f" "$out"
  node .agents/skills/meta-enricher/scripts/verify-meta.mjs "$out"
done
```

> ⚠️ 脚本默认**幂等**：如果 `edit.mode` 已是规范值（`cmx-text-input` 等），不覆盖；如果 display.mode 已是合法值之一，不覆盖。手工调过的字段保持原样。

## 四、推导规则速查

详细规则见 [references/enrich-rules.md](references/enrich-rules.md)。要点：

| 输入特征 | 推导 edit.mode | 推导 display |
|---|---|---|
| TINYINT + 「是否/启用/允许/标记」 | `checkbox` | `text`,center |
| 主键 `id`/`isPrimaryKey=1` | `readonly` | `text` (顶层 `visible:false`) |
| `*_id/parent_id/upper_id/...`（无 refDict） | `readonly` | `text` (顶层 `visible:false`) |
| 有 `refDict` 的字段 | `cmx-dict-select` | `text`,left |
| 自分级字典的 `parent_id` | `cmx-dict-select,parent:parent_id` | `text` |
| `segment`/`fs_version`/`cons_org` 引用 | `cmx-dict-select,parent:parent_id` | `text` |
| `DATE` | `cmx-date-input` | `text,format:'date:YYYY-MM-DD'` |
| `DATETIME` | `cmx-datetime-input` | `text,format:'datetime:YYYY-MM-DD HH:mm:ss'` |
| `DECIMAL` 金额 | `cmx-number-input` | `number` + 2位 + thousands + 零空 + 负红（true） + 右对齐（**不写 format**） |
| `DECIMAL` 汇率 | `cmx-number-input` | `number` + 5位 + 负红（true） + 右对齐（无千分位，**不写 format**） |
| `DECIMAL` 百分比 | `cmx-number-input` | `number` + N 位 + 右对齐（**不写 format**，用户配 `percent:N`） |
| `DECIMAL` 数量 | `cmx-number-input` | `number` + 整数 + thousands + 右对齐（**不写 format**） |
| 整数序号 `line_no`/`sort_no`/`level_no` | `cmx-number-input` | `number` + 整数 + thousands + 右对齐（**不写 format**） |
| `doc_status`/状态字段（非 TINYINT） | `checkbox` | `badge` + `badgeMap`（草稿/过账/冲销等） |
| TINYINT 的 `status`（0/1 布尔） | `checkbox` | `text`,center（不套业务 badgeMap） |
| `enumValues` 显式枚举 | `select` + `options` | `text`,left |
| 有 `refDict`（cmx-dict-select） | `cmx-dict-select` | `text`,left + **editSettings 补 5 属性**（见下） |
| 其他 VARCHAR | `cmx-text-input` | `text`,left |
| `TEXT` | `cmx-textarea-input` | `text`,left |

### cmx-dict-select 的 editSettings 补全（参考 [field-edit-display-modes.md](../cmx-components-guide/references/field-edit-display-modes.md#cmx-dict-select字典选择属性落-editsettings) 14 属性）

edit.mode='cmx-dict-select' 时，脚本补 **5 个确定且必要**的 editSettings，其余 9 个属于用户配置区：

| editSettings 属性 | 脚本行为 | 推导 |
|---|---|---|
| `helpLayout` | ✅ 必补 | 自分级字典(segment/fs_version/cons_org) → `'grid'`；普通 → `'classify'` |
| `hierarchical` | ✅ 自分级补 `true` | 同 helpLayout 判断 |
| `dictTitle` | ✅ 补 | `'选择' + caption`（如"选择国家"） |
| `showClear` | ✅ 非必填补 `true` | 提升体验 |
| `idCol` | ✅ **条件补** | refDict 指向 NoID 字典（`baseFieldSet=dictionaryCommonNoIDFields`，无 id 列）→ 补 `'code'`；其余走默认 `'id'` 不写 |
| 其它 9 个 | ❌ 不写 | displayMode/displayTemplate/codeCol/labelCol/parentCol/valueField/displayField/mruMax/dropdownWidth/dropdownMaxHeight/placeholder —— 有合理默认或业务自选 |

**幂等**：已有 editSettings（含运行时 dictCode+coord）不覆盖，仅补缺失的 idCol（NoID 字典）。详见 [references/enrich-rules.md §三·补](references/enrich-rules.md#三补cmx-dict-select-的-editsettings-推导14-属性脚本补-5-个)。

## 五、必填（required）推导

保守原则（缺省不强制）：

- `code` / `name` / `doc_no` / `doc_status` → `required: true`
- 字段在表的 `uniqueKeys` 列表中 → `required: true`
- 字段 `nullable: false`（排除审计/系统字段）→ `required: true`
- 主键/审计/`parent_id`/`upper_id` → `required: false`
- `required: true` 同步写入 `edit.required`

## 六、列宽（width）推导

| dataType | width |
|---|---|
| DATE | 130px |
| DATETIME | 160px |
| TINYINT | 90px |
| BIGINT 关系 ID | 100px |
| BIGINT | 120px |
| INT | 90px |
| DECIMAL 汇率/百分比 | 110px |
| DECIMAL | 140px |
| TEXT | 280px |
| `code` | 140px |
| `name` | 180px |
| `doc_no` | 160px |

## 七、可见性（visible）/ 冻结（frozen）

- 主键列 → 顶层 `visible: false`、`frozen: true`
- 内部关系 ID（`*_id` 无 refDict）→ 顶层 `visible: false`
- 其他 → 默认可见

## 八、已知限制 / 缺口

1. **DOC 装载路径本身"裸奔"**（`cmx-doc-meta-loader.js` 只消费 6 属性）—— 补全后的字段在 `__designer_meta__` JSON 里都正确，但 DOC 动态装载仍可能丢失。详见 [references/dct-doc-meta-loader-gap.md](references/dct-doc-meta-loader-gap.md)
2. **CmxColumn 缺口**（`defaultValue`/`unique`/`searchable`/`sensitive`/`editableWhen`/`visibleWhen`）：这些 key schema 允许填但 grid 端不消费 —— 脚本不补，参见 [field-edit-display-modes.md §六](../cmx-components-guide/references/field-edit-display-modes.md)
3. **运行时无编辑器**：`cmx-textarea-input`/`cmx-richtext-input`/`image`/`video`/`ref` 退化 — 脚本照填，需要时人工干预

## 九、运行后自检

- [ ] 4 份文件 `node .../verify-meta.mjs` 跑出 `badEdit=0 badDisplay=0 badIdField=0 badIdCol=0`
- [ ] 看 diff：金额列 → `display.mode='number'` + `decimalDigits/thousandSeparator/zeroAsBlank/negativeColor(true)/align`（**没有 `format` 字段，留给用户配**）
- [ ] 看 diff：状态列 → `display.mode='badge'` + `badgeMap`
- [ ] 看 diff：引用字段 → `edit.mode='cmx-dict-select'`（不是 `dict-select`）
- [ ] 看 diff：dict-select 字段 → `editSettings.helpLayout`（grid/classify）+ `dictTitle` + 非必填 `showClear:true`；自分级字典额外有 `hierarchical:true`
- [ ] 看 diff：refDict 指向 NoID 字典（country/currency/doc_type 等 60 本）→ `editSettings.idCol:'code'`
- [ ] 看 diff：NoID 字典自身 → `dictMeta.idField:'code'`（不是 `'id'`）
- [ ] 看 diff：主键/内部 ID → `edit.mode='readonly'` + `visible:false`
- [ ] **幂等性自检**（见 [references/enrich-rules.md §8.1](references/enrich-rules.md#81-验证方法)）：同份文件跑两次脚本 diff=0（除 `updatedAt`）
- [ ] `git diff` 检查误改的字段

## 十、文件清单

| 路径 | 说明 |
|---|---|
| `scripts/enrich-meta.mjs` | 核心补全脚本（Node ≥ 18） |
| `scripts/verify-meta.mjs` | 合法值校验脚本（CI 友好） |
| `references/enrich-rules.md` | 详细推导规则与覆盖优先级 |
| `references/dct-doc-meta-loader-gap.md` | DOC 装载路径缺口（不归本技能管） |
| `../cmx-components-guide/references/field-edit-display-modes.md` | 字段属性权威 Schema（共享真源，cmx-components-guide 维护） |
