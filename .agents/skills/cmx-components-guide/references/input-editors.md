# 输入编辑器（text / number / date / datetime）

> 何时读：需要 form / grid 字段编辑器（文本、数值、日期、日期时间）时读。

> 源码：
> - `packages/cmx-data-comp/src/components/cmx-text-input.js`
> - `packages/cmx-data-comp/src/components/cmx-number-input.js`
> - `packages/cmx-data-comp/src/components/cmx-date-input.js`
> - `packages/cmx-data-comp/src/components/cmx-datetime-input.js`

---

## 一、共同特征

四个输入编辑器均封装 UI5 控件，作为 `cmx-ui5-form` / `cmx-revo-grid` 的字段类型编辑器，由 `CmxColumnModel.columns[].edit.mode`（或 `editMode`）触发。

### 1.1 共同 API

| 方法 | 签名 | 说明 |
|------|------|------|
| `setField(field)` | `(field: object) -> this` | 绑定字段配置（读 field.* 及 editSettings.*） |
| `setValue(v, opts)` | `(v, { silent?: boolean }) -> this` | 回填值；`silent:true` 时不派发事件 |
| `getValue()` | `() -> *` | 取值 |
| `setReadonly(b)` | `(b: boolean) -> this` | 设置只读 |
| `setPlaceholder(t)` | `(t: string) -> this` | 设置占位文本 |
| `focus()` | `() -> void` | 聚焦 |
| `validate()` | `() -> true \| string` | 校验；返回 `true` 合法，返回字符串为错误信息 |
| `commitPending()` | `() -> *` | 提交输入框挂起文本到 _value（grid 取值前调用） |

### 1.2 共同事件

| 事件名 | detail | 触发时机 |
|--------|--------|----------|
| `cmx-value-change` | `{ value, valid }` | 值变化；`valid` 为 `validate()` 结果的布尔值 |

所有事件 `bubbles: true, composed: true`。

### 1.3 共同配置路径

- 通过 `setField(field)` 配置，读取 `field.*` 及 `field.editSettings.*`（简称 `es`）。
- 也支持 HTML 声明式属性（设计器调色板 / 静态 HTML 用）；外部调 `setField` 后属性不再覆盖。
- grid 单元格编辑器：`data-cmx-fill-host` 属性让组件撑满单元格宽高。

---

## 二、cmx-text-input

封装 `<ui5-input>`，作为 `'text'` 字段类型编辑器。

### 2.1 observedAttributes

| 属性 | 说明 |
|------|------|
| `input-type` | 输入类型：`text` / `phone` / `email` / `idcard` |
| `pattern` | 自定义校验正则字符串 |
| `maxlength` | 最大长度 |
| `placeholder` | 占位文本 |
| `i18n` | 多语言模式（`'false'` 关闭） |
| `readonly` | 只读（`'false'` 关闭） |

### 2.2 INPUT_TYPES

| inputType | ui5Type | 校验正则 | placeholder |
|-----------|---------|----------|------------|
| `text` | `Text` | 无（`null`） | `''` |
| `phone` | `Tel` | `/^[+]?[\d\s-]{5,20}$/` | `如 13800138000` |
| `email` | `Email` | `/^[^\s@]+@[^\s@]+\.[^\s@]+$/` | `如 name@example.com` |
| `idcard` | `Text` | `/(^\d{15}$)\|(^\d{17}[\dXx]$)/` | `18 位或 15 位身份证号` |

- `pattern` 优先于 `inputType` 内置正则。
- `idcard` 除位数正则外，还校验出生日期合法性 + GB 11643 校验码（18 位）。

### 2.3 多语言输入（i18n）

`field.i18n`（或 `editSettings.i18n`）为真时：
- 值以 `{ 语言: 文本 }` 对象存储，如 `{ zh_CN: '你好', en_US: 'Hello' }`。
- 编辑「当前语言」分量（`locale` 默认 `zh_CN`），其余语言分量原样保留。
- `setValue` 接受对象或字符串（字符串视为当前语言分量）。
- `getValue` 返回对象。
- `setLocale(loc)` 切换当前编辑语言。

### 2.4 代码示例

```javascript
import 'cmx-data-comp/components/cmx-text-input.js'

// 基本文本输入
const input = document.createElement('cmx-text-input')
input.setField({
  inputType: 'text',
  maxlength: 50,
  placeholder: '请输入名称',
})
document.body.appendChild(input)

input.addEventListener('cmx-value-change', (e) => {
  console.log('值:', e.detail.value, '合法:', e.detail.valid)
})

// 手机号输入（内置正则校验）
const phone = document.createElement('cmx-text-input')
phone.setField({ inputType: 'phone' })

// 身份证输入（内置 GB 11643 校验码校验）
const idcard = document.createElement('cmx-text-input')
idcard.setField({ inputType: 'idcard' })

// 多语言输入
const i18nInput = document.createElement('cmx-text-input')
i18nInput.setField({ i18n: true, locale: 'zh_CN' })
i18nInput.setValue({ zh_CN: '你好', en_US: 'Hello' }, { silent: true })
// 切换到英文编辑
i18nInput.setLocale('en_US')
```

---

## 三、cmx-number-input

封装 `<ui5-input type="Text">`，作为 `'number'` 字段类型编辑器。

> 用 `type="Text"` 而非 `Number`：HTML `<input type=number>` 会丢弃 `=`、`*`、`(` 等非数字字符，导致表达式输入打不进去。改用 Text 后由 `_onCommit` 负责求值归一。

### 3.1 observedAttributes

| 属性 | 说明 |
|------|------|
| `int-digits` | 整数位最大位数 |
| `decimal-digits` | 小数位位数（提交时四舍五入） |
| `min` | 最小值 |
| `max` | 最大值 |
| `placeholder` | 占位文本 |
| `readonly` | 只读（`'false'` 关闭） |

### 3.2 field 配置项

| field / editSettings 字段 | 说明 |
|--------------------------|------|
| `field.integerDigits` / `field.intDigits` / `es.intDigits` | 整数位最大位数 |
| `field.decimalDigits` / `es.decimalDigits` | 小数位位数 |
| `field.min` / `es.min` | 最小值 |
| `field.max` / `es.max` | 最大值 |
| `field.placeholder` / `es.placeholder` | 占位文本 |
| `field.readonly` | 只读 |

### 3.3 整数位 / 小数位限制

- **小数位**：提交时（`_onCommit`）按 `decimalDigits` 四舍五入。格式化显示也按此精度（`toFixed`）。
- **整数位**：校验时（`validate`）检查整数部分位数是否超限。

### 3.4 表达式自动计算

输入以 `=` 开头或含运算符（`+` `-` `*` `/` `(` `)`）时，失焦 / 回车自动按表达式求值：

```javascript
// 用户输入 '=12*16' -> 失焦后自动求值为 192
// 用户输入 '100+50' -> 失焦后自动求值为 150
```

使用安全求值器 `formula-eval`（非 `eval`），支持基本四则运算 + 括号。

### 3.5 下拉微型计算器

输入框尾部有计算器按钮（UI5 icon: `simulate`），点击弹出微型计算器：
- 基本四则：`7 8 9 /` `4 5 6 *` `1 2 3 -` `0 . = +` `C ⌫`
- `=` 求值后回写到输入框并关闭
- `C` 清空，`⌫` 退格
- 求值结果按 `decimalDigits` 四舍五入

### 3.6 代码示例

```javascript
import 'cmx-data-comp/components/cmx-number-input.js'

const input = document.createElement('cmx-number-input')
input.setField({
  intDigits: 8,
  decimalDigits: 2,
  min: 0,
  max: 99999999.99,
  placeholder: '请输入金额',
})
document.body.appendChild(input)

input.addEventListener('cmx-value-change', (e) => {
  console.log('值:', e.detail.value, '合法:', e.detail.valid)
})

// 表达式输入：用户在输入框打 '=12*16+100' 后按回车，自动求值为 292
// 小数位限制：输入 '3.14159' -> 提交后四舍五入为 '3.14'
```

---

## 四、cmx-date-input

封装 `<ui5-date-picker>`，作为 `'date'` 字段类型编辑器。

### 4.1 observedAttributes

| 属性 | 说明 |
|------|------|
| `format` | 日期格式（如 `yyyy-MM-dd`） |
| `min-date` | 最小日期 |
| `max-date` | 最大日期 |
| `placeholder` | 占位文本 |
| `readonly` | 只读（`'false'` 关闭） |

### 4.2 field 配置项

| field / editSettings 字段 | 说明 |
|--------------------------|------|
| `field.formatPattern` / `field.format` / `es.formatPattern` / `es.format` | 日期格式，默认 `yyyy-MM-dd` |
| `field.minDate` / `es.minDate` | 最小日期 |
| `field.maxDate` / `es.maxDate` | 最大日期 |
| `field.placeholder` / `es.placeholder` | 占位文本 |
| `field.readonly` | 只读 |

### 4.3 特性

- 默认格式：`yyyy-MM-dd`
- 值为字符串（按 formatPattern 文本）
- 内置下拉日历选择
- UI5 date-picker 自带格式校验（`isValid()`）
- 支持 `min-date` / `max-date` 范围限制

### 4.4 代码示例

```javascript
import 'cmx-data-comp/components/cmx-date-input.js'

const input = document.createElement('cmx-date-input')
input.setField({
  format: 'yyyy-MM-dd',
  minDate: '2020-01-01',
  maxDate: '2030-12-31',
  placeholder: '请选择日期',
})
document.body.appendChild(input)

input.setValue('2025-07-24', { silent: true })

input.addEventListener('cmx-value-change', (e) => {
  console.log('日期:', e.detail.value, '合法:', e.detail.valid)
})
```

---

## 五、cmx-datetime-input

封装 `<ui5-datetime-picker>`，作为 `'datetime'` 字段类型编辑器。

### 5.1 observedAttributes

| 属性 | 说明 |
|------|------|
| `format` | 日期时间格式（如 `yyyy-MM-dd HH:mm:ss`） |
| `min-date` | 最小日期 |
| `max-date` | 最大日期 |
| `placeholder` | 占位文本 |
| `readonly` | 只读（`'false'` 关闭） |

### 5.2 field 配置项

| field / editSettings 字段 | 说明 |
|--------------------------|------|
| `field.formatPattern` / `field.format` / `es.formatPattern` / `es.format` | 日期时间格式，默认 `yyyy-MM-dd HH:mm:ss` |
| `field.minDate` / `es.minDate` | 最小日期 |
| `field.maxDate` / `es.maxDate` | 最大日期 |
| `field.placeholder` / `es.placeholder` | 占位文本 |
| `field.readonly` | 只读 |

### 5.3 特性

- 默认格式：`yyyy-MM-dd HH:mm:ss`
- 值为字符串（按 formatPattern 文本）
- 内置下拉日期 + 时间选择器
- UI5 datetime-picker 自带格式校验（`isValid()`）
- 支持 `min-date` / `max-date` 范围限制

### 5.4 代码示例

```javascript
import 'cmx-data-comp/components/cmx-datetime-input.js'

const input = document.createElement('cmx-datetime-input')
input.setField({
  format: 'yyyy-MM-dd HH:mm:ss',
  placeholder: '请选择日期时间',
})
document.body.appendChild(input)

input.setValue('2025-07-24 14:30:00', { silent: true })

input.addEventListener('cmx-value-change', (e) => {
  console.log('日期时间:', e.detail.value, '合法:', e.detail.valid)
})
```

---

## 六、对应 edit.mode 速查

| 组件 | edit.mode | 封装的 UI5 控件 | 值类型 |
|------|-----------|----------------|--------|
| `<cmx-text-input>` | `text` | `<ui5-input>` | `string` 或多语言 `object` |
| `<cmx-number-input>` | `number` | `<ui5-input type="Text">` | `number \| null` |
| `<cmx-date-input>` | `date` | `<ui5-date-picker>` | `string`（如 `'2025-07-24'`） |
| `<cmx-datetime-input>` | `datetime` | `<ui5-datetime-picker>` | `string`（如 `'2025-07-24 14:30:00'`） |

在 `CmxColumnModel` 列定义中通过 `editMode`（或 `edit.mode`）指定：

```javascript
import { CmxColumn, CmxColumnModel } from 'cmx-data-comp'

const cm = new CmxColumnModel({
  members: [
    new CmxColumn({ id: 'name', caption: '名称', type: 'text', editMode: 'text',
      editSettings: { maxlength: 50, placeholder: '请输入名称' } }),

    new CmxColumn({ id: 'amount', caption: '金额', type: 'number', editMode: 'number',
      editSettings: { intDigits: 8, decimalDigits: 2, min: 0 } }),

    new CmxColumn({ id: 'orderDate', caption: '订单日期', type: 'date', editMode: 'date',
      editSettings: { format: 'yyyy-MM-dd' } }),

    new CmxColumn({ id: 'createTime', caption: '创建时间', type: 'datetime', editMode: 'datetime',
      editSettings: { format: 'yyyy-MM-dd HH:mm:ss' } }),
  ],
})
```
