# 三端字段定义 key/值 一致性系统检查报告

> 检查对象：DCT(数据字典) / DOC(业务单据) / CTX(弹性组合) 三端的字段·列定义。
> 检查维度：① key 同义不同名 / 同名不同义；② 同一属性的下拉值域是否一致。
> 数据源：`cmx-field-schema.js`（统一 schema，单一事实来源）+ 两个 manager 的硬编码下拉。

---

## 一、Key 层检查（schema 自动化校验，已固化为单测）

`cmx-field-schema.test.js` 的「key ↔ label 一一对应」不变式持续保证：

| 检查项 | 结果 |
|---|---|
| **A. 一个 key 多个 label**（同义不同名） | ✓ 无 |
| **B. 一个 label 多个 key**（同名不同义） | ✓ 无 |
| **C. 同 key 各端 entry 的下拉值域不一致** | ✓ 无 |
| **D. 同一端内 key 唯一** | ✓ 无重复 |

即：三端"相同含义"的属性用**同一个 key + 同一个 label + 同一套值域**；不同属性绝不撞名。`dataType`(数据类型) 与 `dimType`(维度类型) 是两个独立属性，各自唯一命名，未合并。

---

## 二、值层检查 —— 关键属性下拉值域

### 2.1 走统一 schema 的属性（三端一致，由 schema 定义、manager 不再硬编码）

| 属性 | key | 统一值域 | 端 |
|---|---|---|---|
| 维度类型 | `dimType` | 维度(dimension)/属性(attribute)/度量(measure)/关系(relation) | DOC, CTX |
| 数据类型 | `dataType` | VARCHAR/INT/BIGINT/TINYINT/DECIMAL/DATE/DATETIME/TEXT/BOOLEAN | DCT, DOC, CTX |
| 录入控件 | `edit.mode` | EDIT_MODES 全集（input/select/ref/dict-select/date… 16 项，中文(英文)） | DCT, DOC, CTX |
| 显示模式 | `display.mode` | text/badge/link/icon | CTX |
| 对齐 | `display.align` | left/center/right | CTX |
| 合计 | `column.agg` | sum/count/avg/max/min | CTX |
| 敏感级别 | `sensitive` | public/internal/confidential/pii | DCT, DOC, CTX |
| 字段控制条件 | `edit.requiredWhen`/`editableWhen`/`visibleWhen`/`readonlyWhen` | 表达式（无枚举） | 三端 |

> 这些属性的值域**只在 schema 里定义一次**，三端共用，不存在"同义不同值"。

### 2.2 端内独有下拉（schema 无对应 key，其他端也无此概念 → 不构成三端冲突）

这些是某一端**独有的领域概念**，无三端比较对象，各自自洽：

| 下拉 | 位置 | 值域 | 归属 | 说明 |
|---|---|---|---|---|
| 维度取值方式 `valueType` | CTX 维度面板 (context:1041) | text/select/ref/tree-ref/dict-select | CTX 独有 | **维度定义**的属性（维度本身怎么取值），非字段录入控件。DCT/DOC 无维度概念 |
| 匹配运算符 `op` | CTX 规则匹配条件 (context:1669) | eq/ne/in/nin/exists/any | CTX 独有 | 锚点匹配条件运算符。DCT/DOC 无匹配规则 |
| 合计位置 `aggregatePosition` | CTX 分组面板 (context:1878) | before/after | CTX 独有 | 分组合计行位置。属分组(group)属性，非字段属性 |

---

## 三、一处需留意的「相邻语义」（非冲突，但记录）

**维度取值方式 `valueType`** 与 **录入控件 `edit.mode`** 值域部分重叠但命名不齐：
- `valueType`: `text / select / ref / tree-ref / dict-select`
- `edit.mode`: `input / select / ref / dict-select / …`（有 `input`/`ignite-combo`，无 `text`/`tree-ref`）

二者是**不同对象上的不同属性**（维度的取值来源类型 vs 字段的录入控件），语义不同，独立合理，**不需要统一**。仅在此记录，避免日后误判为"同义不同值"。

---

## 四、结论

- **Key 层**：✓ 无同义不同名、无同名不同义（单测持续保证）。
- **值层**：✓ 所有"三端共有属性"的下拉值域统一（由 schema 单点定义）；端内独有下拉无三端比较对象，不构成冲突。
- 唯一的相邻语义（valueType vs edit.mode）已确认为不同属性，无需合并。

无遗留的"同义不同名"或"同义不同值"问题。
