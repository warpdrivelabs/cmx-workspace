# cmx-code 通用业务编码引擎设计方案 V2.1

> **主题**　通用业务编码引擎（crate `cmx-code`，两段式：cmx-code-model + cmx-code-api），七种段（含随机段）+ 断号补偿 + 独立规则库 + 反查 max 不存已分配码。
>
> **范围**　只出方案不落地代码。函数签名级设计（结构体 / trait / 表结构 / API / 改动接缝 / 落地路线）。
>
> **对标**　金蝶苍穹 AMDM（断号补偿/补位/编码依据）· SAP MDG 编号范围 · 用友编码管理。
>
> **现状基线**　DCT codeRule 纯声明未实现 · DOC doc_no 全前端传无防重。
>
> **设计约束**　不建编码计数器表 · 只存断号 · 后端权威生成 · 前端只预览 · 兼容 manual 现状。
>
> **落地形态**　独立 crate `cmx-code`（两段式：cmx-code-model + cmx-code-api）。
>
> **V2.1 修订（2026-08-05）**　补全 V2 的含糊处：① §2.4 按属性区分前缀（const vs ref 边界）② §3.4-3.6 规则匹配契约（orgScope/condition JSON 算子/priority）+ DAM 隔离 + db_id 解析 + pattern 双语义 ③ §4.8 resetBy 机制（reset_key 进 WHERE）④ §5.3 断号事务陷阱 ⑤ 附录 C 实现现状对账（resetBy/try_insert 等 8 项已知偏差）。

---

## 目录

```
01 现状基线、设计目标与金蝶借鉴
02 七种段类型（含随机段）+ 自定义扩展
  └ 2.4 按属性/类型动态区分段值（前缀分流）★V2.1
03 独立编码规则库（不内联字典元数据）
  ├ 3.4 规则匹配契约（orgScope + condition + priority）★V2.1
  ├ 3.5 DAM 隔离与 db_id 解析 ★V2.1
  └ 3.6 pattern 字段的两种语义 ★V2.1
04 流水号：反查 max + UNIQUE 重试（默认支持高并发）
  └ 4.8 resetBy 机制（reset_key 进 WHERE）★V2.1
05 断号表 + 断号补偿（借鉴金蝶）
  └ 5.3 断号记录的事务陷阱 ★V2.1
06 随机段：字符池/数值范围（防重机制）
07 断号表与「不存已分配编码」的调和
08 前后端协作：后端权威 + 前端预览
09 补位 / 填充 / 截断 / 替代 / 步长（借鉴金蝶）
10 与 DCT/DOC 的集成（钩子 + 引用 + 多级表各自铸号 + 可选级联）
11 REST API 契约
12 完整规则示例（八类典型场景）
13 crate 架构与无状态约束
14 落地路线图与风险
附录 A · 凭证号场景落地（多级表各自铸号）
附录 B · 可视化配置（操作指南 + 前端实现）
附录 C · 实现现状与设计偏差（落地须知）★V2.1
```

---

## 01 · 现状基线、设计目标与金蝶借鉴

### 1.1 现状基线（代码勘探结论）

| 维度 | 现状 | 对本引擎的约束 |
|---|---|---|
| **DCT `codeRule`** | 纯声明，Rust 后端**零解析**（compile_dct 不读 codeRule，运行时也不生成业务编码）。现状全是 manual 形态 `{mode,field,pattern,uniqueCheck}`；auto 形态未见实例 | 引擎要让 auto 生效并扩展段定义 |
| **DOC 单据号 `doc_no`** | 完全前端传，无 codeRule、无 uniqueKeys、无索引、无防重 | 引擎要通用化，同时服务 DCT 与 DOC |
| **主键 id 铸号** | pk52 纯后端原子，前端临时占位 `t${Date.now()}`，后端铸真号回填 | 业务 code 协作复用这套思想 |
| **`code` 列 UNIQUE** | 仅当显式 `uniqueKeys:[["code"]]` 才有索引 `uk_<table>_1` | auto 规则要求目标列声明 uniqueKeys |
| **硬约束** | 「不建议数据库存储**已分配**的编码」 | 不建计数器表；断号表只存断号不存已分配（§07） |

### 1.2 金蝶苍穹编码规则--值得借鉴的点

| 金蝶机制 | 金蝶的做法 | V2 是否纳入 |
|---|---|---|
| **断号表 + 断号补偿** | 流水号被跳过产生「断号」，断号表记录空缺，后续可回收填补。启用「不允许断号」时必须含流水号段、不能含多语言字段、需开即时触发值更新 | ✅ §05（默认关闭，连号域可选开） |
| **补号（手动补号）** | 运行时支持手动补号，勾选后允许修改；流水号步长/起始值为小数时不支持补号 | ✅ §05（管理员手动补断号） |
| **补位符 + 填充方向** | 补位符、右侧填充（不勾选默认左填充）、右侧截断（超长截断）、替代符（取不到值时的替代字符） | ✅ §09 |
| **编码依据（流水号依据）** | 设置某段为「编码依据」，其值变化时流水号重置；支持基础资料/文本/日期；设组织为依据则做组织内唯一校验 | ✅ 即 `resetBy`（§04） |
| **起始值 + 步长（支持小数）** | 流水号起始值和步长都支持整数和小数 | ✅ §09（步长默认 1，可配） |
| **受控组织生效** | 规则按受控组织设置，需在对应组织生效后才调用 | ✅ 已有 orgScope |
| **段类型** | 文本字段/日期字段/基础资料/流水号/常量（5 种） | ✅ 本引擎 7 种 + 自定义，超越金蝶 |
| **规则绑定元数据** | 金蝶把编码规则作为单据编号字段的属性项（内联） | ❌ 改为独立规则库（你的要求） |

### 1.3 V2 相对 V1 的五处升级

1. **新增随机段**：字符池随机 / 数值范围随机；不要 UUID；防重靠 UNIQUE 冲突重试（§06）
2. **断号表 + 断号补偿**：连号域（凭证号/发票号）可选启用；补偿优先填断号（§05）
3. **独立规则库**：规则存 `cmx_code_rule` 表，字典/单据只引用 `ruleCode`，不内联（§03）
4. **补位/步长细节**：补位符、左/右填充、截断、替代符、起始值、步长（§09）
5. **编码依据明确**：`resetBy` 即金蝶「编码依据」，组织作依据 -> 组织内唯一校验

---

## 02 · 七种段类型（含随机段）+ 自定义扩展

编码规则 = 段序列。V2 在 V1 五种基础上新增**随机段**（第六种内置），并保留**自定义段**扩展点。

### 2.1 七种段总览

| # | 段类型 | 用途 | 关键属性 | 并发模型 |
|---|---|---|---|---|
| ① | **const** 固定段 | 常量前缀/后缀（`V`、`M`、`FV`） | `value` | 无并发 |
| ② | **serial** 流水段 | 自增序列。反查 max + 重试 | `width/step/start/resetBy` + 补位 `padChar/padSide`（§09） | 并发重试 |
| ③ | **date** 日期段 | 日期格式化（`YYMM`、`YYYYMMDD`） | `format` | 无并发 |
| ④ | **dateSerial** 日期流水段 | 日期 + 按日重置流水（③+② 语法糖） | `format/width` | 并发重试 |
| ⑤ | **ref** 引用段 | 取字段值或映射（分类->EL、上级科目码） | `field/map/refDict/take/pad` | 无并发 |
| ⑥ | **random** 随机段 **NEW** | 字符池随机 / 数值范围随机。不要 UUID | `mode/width/charset/min/max` | UNIQUE 重试 |
| ⑦ | **custom** 自定义段 | 扩展点（校验位 mod11、组织码、hash 短码） | `impl` + 任意 params | 看实现 |

### 2.2 段求值契约（统一 trait）

```rust
pub trait SegmentResolver: Send + Sync {
    fn seg_type(&self) -> &str;
    async fn resolve(&self, seg: &SegmentSpec, ctx: &ResolveContext<'_>)
        -> Result<SegmentValue, CodeError>;
}

pub enum SegmentValue {
    Literal(String),                        // 固定/日期/引用/随机/自定义(非流水)
    NeedsSerial { reset_key: String, width: usize, step: i64, start: i64 }, // serial/dateSerial
    NeedsUniqueCheck { candidate: String }, // random:生成候选,靠 UNIQUE 重试
}
```

三态：`Literal`（直接用）/ `NeedsSerial`（交流水推进器反查 max）/ `NeedsUniqueCheck`（随机段，不反查 max，纯靠 UNIQUE 冲突重试）。

### 2.3 自定义段扩展点（实例：校验位段）

```rust
pub struct CheckDigitResolver;
impl SegmentResolver for CheckDigitResolver {
    fn seg_type(&self) -> &str { "custom:check_digit" }
    async fn resolve(&self, _seg: &SegmentSpec, ctx: &ResolveContext<'_>)
        -> Result<SegmentValue, CodeError> {
        let prefix = ctx.resolved_so_far.join("");
        Ok(SegmentValue::Literal(mod11_check(&prefix).to_string()))
    }
}
CODE_REGISTRY.register(CheckDigitResolver);
```

### 2.4 按属性/类型动态区分段值（前缀分流）

**常见误区**：用户想「按单据类型区分前缀」（SA 凭证前缀 `01`、AR 凭证前缀 `02`），第一反应是给 **const 固定段**配多个值。这是错的——const 段是**真常量**，实现上 `const_.rs` 只读 `value` 字段、完全忽略 `ctx.attrs`，一个 const 段只有一个值。

**正确做法：用 ref 引用段，不要用 const 段。** const 与 ref 的边界：

| 段类型 | 取值来源 | 是否读 ctx | 适用场景 |
|---|---|---|---|
| **const** | 段声明里的 `value` 字段 | ❌ 不读 | 真常量（固定前缀 `FV`、固定分隔符 `-`） |
| **ref** | 业务行的字段值（`ctx.attrs[field]`） | ✅ 读 | 动态前缀（按类型/组织/分类区分） |

**三种前缀分流写法**（按从简单到灵活排序）：

**写法 A · ref + map 映射**（推荐，最常用）

把属性字段的原始值映射成编码前缀。类型码 → 前缀字典：

```jsonc
{
  "ruleCode": "voucher_by_type",
  "segments": [
    { "type": "ref", "field": "doc_type_code", "map": { "SA": "01", "AR": "02", "GL": "09" } },
    { "type": "dateSerial", "format": "YYYYMMDD", "width": 4 }
  ]
}
// SA 凭证 -> 01202608050001
// AR 凭证 -> 02202608050001
// GL 凭证 -> 09202608050001
```

**写法 B · ref + take 取前 N 位**（无映射表，直接截字段值）

不建映射表，把类型码本身当前缀：

```jsonc
{
  "segments": [
    { "type": "ref", "field": "doc_type_code", "take": 2 },
    { "type": "dateSerial", "format": "YYYYMMDD", "width": 4 }
  ]
}
// doc_type_code="SA" -> SA202608050001（直接用类型码当前缀）
```

**写法 C · 多条规则 + condition 选优**（分流逻辑复杂时，见 §3.4）

每类一条规则，靠 condition 表达式选优，前缀可任意复杂：

```jsonc
// 规则 1：销售凭证
{ "ruleCode": "voucher_sa", "condition": { "eq": ["doc_type_code", "SA"] },
  "segments": [{ "type": "const", "value": "SA-" }, { "type": "dateSerial", "format": "YYYYMMDD", "width": 4 }] }
// 规则 2：应收凭证
{ "ruleCode": "voucher_ar", "condition": { "eq": ["doc_type_code", "AR"] },
  "segments": [{ "type": "const", "value": "AR-" }, { "type": "dateSerial", "format": "YYYYMMDD", "width": 4 }] }
```

> 📌 **选择建议**：前缀是简单 1:1 字典 → 写法 A（ref+map）；前缀就是字段值本身 → 写法 B（ref+take）；前缀含常量/多段/各类型规则差异大 → 写法 C（多规则+condition）。**永远不要试图用 const 段做动态取值。**

**关键前提（容易漏）**：分流依赖的属性字段（如 `doc_type_code`）必须在 preview/generate 请求的 `attrs` 里传给引擎，否则 ref 段取不到值、走 `fallback`（默认空串），前缀会缺位。前端预览按钮和后端铸号钩子都要把该字段塞进 `attrs`。

---

## 03 · 独立编码规则库（不内联字典元数据）

**采纳你的建议**：编码规则不写在字典/单据的元数据里，而是独立管理。字典/单据定义里只**引用** ruleCode。

### 3.1 为什么要独立规则库

**❌ 内联在字典元数据（V1 / 金蝶做法）**：
- 规则与字典定义耦合，改规则要改 JSON 定义文件
- 一个字典只能有一套规则，难支持「按组织/属性分流」
- 规则无法跨字典复用（供应商和客户想用同套规则要复制）
- 规则版本化困难

**✅ 独立规则库（V2 采用）**：
- 规则存 `cmx_code_rule` 表，独立 CRUD、版本化
- 字典/单据定义里只写 `"codeRule": {"ruleCode":"supplier_hq"}` 引用
- 一个目标可挂多条规则（orgScope/condition/priority 选优）
- 规则可跨目标复用、可独立改版不影响字典定义
- 规则管理是独立功能页，业务人员自助配置

### 3.2 规则库表结构（cmx_code_rule · 纯算法，不带 target）

规则表**只存"怎么生成编码"的纯算法**，**不带** target_kind/target_code/target_field--target 由 DCT/DOC 钩子调用时作为上下文传入。这样一条规则可被任意多个字典/单据复用。

```sql
CREATE TABLE cmx_code_rule (
  id          BIGINT PRIMARY KEY,             -- pk52
  rule_code   VARCHAR(64) NOT NULL UNIQUE,    -- 规则码(人类可读,如 supplier_hq)
  rule_name   VARCHAR(128) NOT NULL,          -- 规则名称(展示用)
  mode        VARCHAR(16) NOT NULL,           -- auto | manual
  org_scope   VARCHAR(64),                    -- 受控组织(可选,组织命中才生效)
  condition   TEXT,                           -- 适用条件表达式(可选,按属性分流)
  segments    JSONB NOT NULL,                 -- 段序列(auto 必填)
  joiner      VARCHAR(4) DEFAULT '',          -- 段间连接符
  pattern     TEXT,                           -- 校验正则(可选)
  enable_gap  BOOLEAN NOT NULL DEFAULT false, -- 是否启用断号补偿(§05)
  valid_from  DATE,                           -- 规则版本化
  valid_to    DATE,
  priority    INT DEFAULT 100,                -- 多规则选优
  is_active   BOOLEAN DEFAULT true,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- 注意:无 target_kind/target_code/target_field -- 规则是纯算法,可被任意字典/单据复用
-- target 由调用方(DCT/DOC 钩子)作为上下文传入,见 §10.2
CREATE INDEX ix_code_rule_active ON cmx_code_rule(is_active, priority);
```

> 📌 **命名约定**：数据库表字段用 snake_case（`enable_gap`/`rule_code`/`org_scope`）；JSON 配置（段声明/规则示例）可用 camelCase（`enableGap`/`ruleCode`/`orgScope`）便于前端阅读。Rust 结构体用 `#[serde(rename_all = "camelCase")]` 统一桥接。本文档 SQL 用 snake、JSON 示例用 camel，两者指同一字段。

**规则与 target 解耦 -> 真正可复用**：一条 `supplier_hq` 规则可被 `bus_partner`、`customer`、`vendor` 三个字典同时引用。改规则只改一处，所有引用方自动生效。

### 3.3 字典/单据定义如何引用规则（挂载点声明，含 target 行为）

**关键分工**：规则表（§3.2）存「算法」（纯段序列，无 target）；定义里的 codeRule 存「挂载点行为」（target.field / mode / 局部覆盖 / cascade 级联）。两者解耦，一条算法可被多个挂载点复用。

```jsonc
// DCT 字典定义里 -- codeRule 是挂载点声明
"dictMeta": {
  "dictCode": "bus_partner",
  "codeRule": {
    "ruleCode": "supplier_hq",   // 引用 §3.2 规则表的算法
    "field": "code",                // target.field：铸号写回本表的哪列（引擎只认这个，不硬编码列名）
    "mode": "auto"                  // 局部声明，覆盖规则表 mode（默认 auto）
  }
}

// DOC 单据定义里 -- voucherTables[].codeRule 同款声明
"voucherTables": [{
  "tableName": "cv_header",
  "codeRule": {
    "ruleCode": "voucher_daily",
    "field": "doc_no",
    "mode": "auto",
    "enableGap": true,              // 局部覆盖规则表的 enable_gap（连号域在此挂载点启用）
    "cascade": {                    // 可选：父表铸号后沿 relations 回填子表（§10.4），默认不配=不级联
      "field": "doc_no",            //   回填到子表的哪个字段
      "scope": "children"           //   children=直接子表；descendants=沿链全部后代
    }
  }
}, {
  "tableName": "cv_acc_line"
  // 未声明 codeRule → 引擎跳过该表（§10.3）
}]

// 兼容现状:无 ruleCode 时回退到 manual(保持 V1 现状零破坏)
"codeRule": { "mode": "manual", "pattern": "^[0-9]+$" }  // 不引用规则库,走 manual
```

**挂载点声明的字段**（都不进规则表，随 DCT/DOC 定义走）：

| 字段 | 必填 | 作用 | 默认 |
|---|---|---|---|
| `ruleCode` | auto 必填 | 引用规则表的算法 | — |
| `field` | 是 | target.field：铸号写回本表哪列 | DCT 默认 `code` |
| `mode` | 否 | 局部覆盖规则表 mode | `auto` |
| `enableGap` | 否 | 局部覆盖规则表 enable_gap | 规则表值 |
| `pattern` | 否 | manual 模式的正则兜底校验 | — |
| `uniqueCheck` | 否 | 是否强制 UNIQUE 校验（auto 自动开；manual 时显式开则铸号后查重） | auto=true / manual=false |
| `cascade` | 否 | 级联回填配置（§10.4） | 不级联 |

> 📌 `uniqueCheck` 是现状 codeRule 已有字段（cmxfico_dct_meta_v3.json:117），V2 保留兼容。auto 模式下 UNIQUE 校验是反查 max + 重试的前提（§4.2），恒为 true；manual 模式下若设 true，引擎在落库前对 code 列做一次 `SELECT EXISTS` 查重（非 UNIQUE 索引时的兜底）。

**为什么 cascade 不进规则表**：规则表是「纯算法，无 target，可被多目标复用」（§3.1）；cascade 是「挂载点行为」（cv_header 铸号→回填 cv_acc_line），与 target 强绑定。若放规则表，一条规则被多目标复用时 cascade 会污染别的目标。cascade 随挂载点声明走，每个目标独立配。

**向后兼容**：现有 cmxfico 几十处 `codeRule:{mode:"manual",...}` 声明**无需任何修改**--引擎读到 manual 走现状路径。只有显式写 `ruleCode` 引用独立规则的才走新引擎。

### 3.4 规则匹配契约（orgScope + condition + priority）

同一 `ruleCode` 可挂多条规则（按组织分流、按属性分流、版本迭代）。铸号时按三要素筛优：

```
查规则(同 ruleCode) → 过滤 orgScope 命中 → 过滤 condition 成立 → 取 priority 最大
```

#### 3.4.1 orgScope · 受控组织匹配规则

| 规则配置 | 匹配语义 | 示例 |
|---|---|---|
| `null` / 空 | 全局生效，任何组织命中 | `"orgScope": null` |
| `"CODE"` | **精确匹配** `ctx.org.orgCode` | `"orgScope": "HQ"` 仅 HQ 组织生效 |
| `["A","B"]` | 数组=多组织（精确匹配其一） | `"orgScope": ["EAST","WEST"]` |

**不做父子继承**：`orgScope:"HQ"` 不会让子组织 `HQ_001` 生效。组织树继承由调用方解析后传完整的 `ctx.org.orgCode`（叶子组织码），规则只做精确匹配。理由：组织树结构在业务侧，引擎不该内置树遍历逻辑。

**多组织传参**：前端/钩子把当前用户的组织码塞进请求 `orgCtx.orgCode`（§11.1）。引擎不查组织表，只比对字符串。

#### 3.4.2 condition · 属性分流表达式（JSON 语法，**非 JS 字符串**）

condition 用**受控的 JSON 对象表达式**（类似 JSONLogic），**禁止任意 JS 字符串求值**（防注入、可序列化、可在 SQL 侧编译）。

支持的算子（白名单，`attrs` 即 preview/generate 请求的 `attrs` 上下文）：

| 算子 | 语义 | 示例 |
|---|---|---|
| `{"eq": [field, value]}` | attrs[field] === value | `{"eq": ["doc_type_code", "SA"]}` |
| `{"in": [field, [v1,v2]]}` | attrs[field] ∈ 数组 | `{"in": ["bp_role", ["supplier","vendor"]]}` |
| `{"ne": [field, value]}` | attrs[field] !== value | `{"ne": ["is_internal", true]}` |
| `{"exists": field}` | attrs 有该字段 | `{"exists": "parent_id"}` |
| `{"and": [expr, expr]}` | 逻辑与 | `{"and": [{"eq":["t","SA"]}, {"exists":"ref_no"}]}` |
| `{"or": [expr, expr]}` | 逻辑或 | `{"or": [{"eq":["t","SA"]}, {"eq":["t","AR"]}]}` |
| `{"not": expr}` | 逻辑非 | `{"not": {"exists": "parent_id"}}` |

**求值器**：白名单算子 + 字段访问只读 `attrs`，不允许访问 `__proto__` / 全局对象。未知算子直接判 false（规则不命中，不报错）。

> 📌 **实现现状（2026-08-05 更新）**：JSON 算子求值器**已实现**（`rule_store::eval_json_condition`，白名单 eq/ne/in/exists/and/or/not），**同时向后兼容**字符串表达式（`field==value` / `!=`，JSON 解析失败时回退）。condition 配置可用 JSON 算子（推荐）或字符串表达式（兼容）。未知算子严格判 **false**（非 true，修复安全隐患）。附录 C.2.8 记录。

**示例**：

```jsonc
// 供应商码规则：仅当业务伙伴是供应商角色时生效
{
  "ruleCode": "supplier_hq",
  "condition": { "eq": ["bp_role", "supplier"] },
  "segments": [...]
}

// 复合条件：销售凭证且有关联单号
{
  "condition": { "and": [ {"eq": ["doc_type_code", "SA"]}, {"exists": "ref_no"} ] }
}
```

> 📌 **为什么不用 JS 字符串**（如 `"attrs.bp_role=='supplier'"`）：① 注入风险（`__proto__`、`eval`）；② 不可序列化进 SQL；③ 跨语言难复用。JSON 算子表达式三者更安全。
>
> **实现状态**（2026-08-05 更新）：JSON 算子求值器**已实现**（`rule_store::eval_json_condition`，白名单 eq/ne/in/exists/and/or/not），向后兼容字符串表达式（`field==value`，解析失败回退）。未知算子严格判 false（非 true）。附录 C.2.8 已标记修复。

#### 3.4.3 priority · 多规则选优

多条规则同时命中（orgScope + condition 都满足），取 `priority` **最大**者（默认 100）。`priority` 相同时取 `updated_at` 最新者（确定性兜底）。建议不同分流的规则用不同 priority 显式排序，避免依赖时间兜底。

### 3.5 DAM（域/应用/模块）隔离与 db_id 解析

规则表带 `domain_code / application_code / module_code` 三字段（DAM 归属），实现已落地（migration `20260805_003_cmx_code_rule_dam`）。不同调用场景的 DAM 行为不同：

| 调用场景 | 是否带 DAM 过滤 | 理由 |
|---|---|---|
| **规则管理页**（CRUD 列表） | ✅ 带当前模块 DAM | 实施顾问只看本模块规则，不串模块 |
| **字典/单据挂规则码下拉** | ❌ 不带 DAM | 规则可跨模块引用（如组织码规则全公司共用） |
| **铸号 preview/generate** | ❌ 用 `Dam::default()` | ruleCode 全局唯一，铸号无需按模块过滤 |

**前端带法**：规则管理页从菜单缓存取当前节点的 `domainCode/applicationCode/moduleCode`，所有 fetch 加请求头 `domain_code/application_code/module_code`（后端 `dam_from(headers)` 读取，列表查询带 WHERE 过滤，create/update 时若 body 未带则从 header 补）。

**db_id 解析链**（决定规则/业务数据查哪个库）：

```
请求 header db_id → 有则用(指定库)
                 → 无则 get_biz_db_id()(第一个 source_type="biz" 的库)
                 → 再退 default 库
```

**现状**：所有模块共享一个 biz 库（cmxfico 用 `fico-db`），无「DAM → 库」映射表。规则表随业务数据落在 biz 库（与业务表同库，便于同事务反查 max）。未来若多业务库，可在 db 配置里按 DAM 路由。

### 3.6 pattern 字段的两种语义

`pattern` 字段在 manual / auto 两种模式下语义不同，**不要混用**：

| 模式 | pattern 作用 | 何时校验 | 失败行为 |
|---|---|---|---|
| **manual** | 用户输入的**业务校验正则**（如 `^[0-9]{4}$`） | 落库前 | 拒绝保存，提示用户 |
| **auto** | 引擎生成码的**自检兜底正则**（可选） | 铸号后 | 引擎内部断言，正常永不出错（出错=规则配错） |

**auto 模式下 pattern 几乎不会失败**——码是引擎自己按段拼的，能产出不符合 pattern 的码只说明规则配置自相矛盾（如段宽度加起来不够、map 映射漏了类型）。此时 pattern 是配置自检的护栏，不是运行时校验。

**建议**：auto 模式留空 pattern 即可（引擎自检默认关闭）；确需配置自检时，pattern 应是段拼装结果的超集（如 `^FV\d{12}$`），不要写得太严（否则 map 扩展新类型会触发误报）。

---

## 04 · 流水号：反查 max + UNIQUE 重试（默认支持高并发）

核心创新：**不建计数器表**，靠业务表 code 列反推 max + DB UNIQUE 冲突重试。天然「永不回收」「集群无状态」。

**高并发是默认需求**，不是"可选"--引擎内置三档并发策略，按场景自动切换。

### 4.1 反查 max 算法（单条 SQL）

```sql
-- prefix="VRM2608", width=4 -> 找当前前缀下最大流水
SELECT COALESCE(
    MAX(CAST(SUBSTRING(code FROM LENGTH('VRM2608')+1 FOR 4) AS INTEGER)),
    0
) AS max_serial
FROM cf_bus_partner
WHERE code LIKE 'VRM2608%'
  AND LENGTH(code) = LENGTH('VRM2608')+4
  AND SUBSTRING(code FROM LENGTH('VRM2608')+1) ~ '^[0-9]+$';
```

候选号 = `start + (max - start) / step * step + step`（考虑 start/step）。补零到 width 位。

> ⚠ **性能要点**：反查 max 的 `WHERE code LIKE 'prefix%'` 需要前缀索引支撑。auto 规则的目标列必须声明 `uniqueKeys`（既有 compile 机制自动建唯一索引，`LIKE` 前缀匹配可走该索引）。

> ⚠ **同事务多行铸号的 buffer 注入**：当一次保存含多行同表铸号（如 3 张凭证头，§10.3），第 2 行反查 max 时第 1 行的号还没落库，`SELECT MAX` 查不到。解法：`query_max_serial` 接受可选 `minted_buffer: &[String]` 参数，反查时把 buffer 里的号 union 进候选集：
> ```sql
> -- 带 buffer 的反查（minted_buffer 非空时）
> SELECT GREATEST(
>   COALESCE(MAX(CAST(SUBSTRING(code FROM ...) AS INTEGER)), 0),  -- 已落库的 max
>   COALESCE((SELECT MAX(v) FROM unnest($buffer::int[]) AS v), 0) -- 本次事务已铸的 max
> ) AS max_serial FROM cf_bus_partner WHERE code LIKE ...;
> ```
> 单条独立保存（buffer 为空）退化为纯 `SELECT MAX`，零开销。

### 4.2 并发正确性：UNIQUE 约束保证绝对不重号

反查 max 是"先读后写"，读和写之间没有锁。并发时多个请求可能读到同一个 max：

```
A: SELECT MAX -> 7  ──┐
B: SELECT MAX -> 7  ──┤（A 还没插入，B 也读到 7）
A: INSERT 0008 -> 成功 ✅
B: INSERT 0008 -> UNIQUE 冲突 ❌ -> 重试 -> MAX=8 -> INSERT 0009 -> 成功 ✅
```

**DB 的 UNIQUE 约束是最后防线**--即使并发读到同一个 max，也只有一个能插入成功，另一个冲突重试。**绝对不重号**。

### 4.3 三档并发策略（默认支持高并发）

| 档位 | 场景 | 并发量 | 策略 | 建表 |
|---|---|---|---|---|
| **单条重试** | 人填表点保存（凭证录入、字典维护） | <100/秒 | 反查 max + UNIQUE 重试（最多 8 次） | ❌ |
| **批量取号** | 批量导入、ETL 装载 | 100~10000/秒 | 一次查 max 取一段号，本地分配，整批 INSERT | ❌ |
| **PG SEQUENCE 兜底** | 海量初始化、极端高并发 | >10000/秒 | 可选启用 PG 原生 SEQUENCE | ✅（DB 内置，非业务表） |

**三档自动切换**：引擎根据调用方式决定走哪档--单条 save 走单条重试，批量 import 走批量取号，规则配 `useSequence:true` 走 SEQUENCE。不需要手动选。

### 4.4 单条重试主循环（档位一：低并发默认）

```rust
/// 单条铸号：反查 max + UNIQUE 重试。minted_buffer 用于同事务多行铸号推进（§10.3）。
async fn mint_single(
    rule: &RuleSpec, target: &Target, ctx: &ResolveContext,
    minted_buffer: &[String],   // 同事务已铸号（单条独立保存传 &[]）
) -> Result<String> {
    const MAX_RETRY: u32 = 8;
    for attempt in 1..=MAX_RETRY {
        let prefix = resolve_fixed_segments(rule, ctx).await?;
        // ① 若规则启用断号补偿且断号表有货 -> 优先取断号(§05)
        if rule.enable_gap {
            if let Some(gap) = take_gap(&prefix, rule.serial_width, ctx).await? {
                let code = format!("{}{:0width$}", prefix, gap, width=rule.serial_width);
                match try_insert(target, &code, ctx.txn()).await { Ok(_) => return Ok(code), Err(UniqueViolation) => continue, e => return e? }
            }
        }
        // ② 否则反查 max（带 minted_buffer：union 本次事务已铸号，§4.1 buffer 注入）
        let max = query_max_serial(target, &prefix, rule.serial_width, minted_buffer, ctx).await?;
        let candidate = next_after(max, rule.serial_start, rule.serial_step);
        let code = format!("{}{:0width$}", prefix, candidate, width=rule.serial_width);
        match try_insert(target, &code, ctx.txn()).await {
            Ok(_) => return Ok(code),
            Err(UniqueViolation) if attempt < MAX_RETRY => continue,
            e => return e?,
        }
    }
    Err(CodeError::MaxRetryExceeded)
}
```

> 📌 **统一函数签名**（跨 §4.4/§4.5/§10.3 一致）：
> - `resolve_fixed_segments(rule: &RuleSpec, ctx: &ResolveContext) -> Result<String>` — 求固定段前缀
> - `query_max_serial(target: &Target, prefix: &str, width: usize, minted_buffer: &[String], ctx: &ResolveContext) -> Result<i64>` — 反查 max（target 含 table+field，buffer 为空时退化纯 MAX）
> - `try_insert(target: &Target, code: &str, txn: &Transaction) -> Result<()>` — 插入候选号（UNIQUE 冲突返回 UniqueViolation）

### 4.5 批量取号（档位二：高并发默认）

批量导入 N 条时，不逐条反查 max（冲突概率随并发指数增长），而是**一次取一段**：

```rust
/// 批量取号：一次反查 max，本地分配 [max+1 .. max+count]，整批 INSERT。
/// 冲突时整批重试（极少发生：只有另一批同时取了重叠号段才会冲突）。
async fn batch_generate(
    rule: &RuleSpec, target: &Target, count: usize, ctx: &ResolveContext
) -> Result<Vec<String>> {
    let prefix = resolve_fixed_segments(rule, ctx).await?;
    // 批量取号传空 buffer：一次取整段号本地分配，不需要逐行推进
    let max = query_max_serial(target, &prefix, rule.serial_width, &[], ctx).await?;
    // 本地分配 count 个连续号
    let candidates: Vec<String> = (1..=count)
        .map(|i| format!("{}{:0width$}", prefix, max + i as i64, width=rule.serial_width))
        .collect();
    // 整批 INSERT，冲突则整批重试（max 已变，重新取一段）
    match batch_insert(target, &candidates, ctx.txn()).await {
        Ok(_) => Ok(candidates),
        Err(UniqueViolation) => {
            let new_max = query_max_serial(target, &prefix, rule.serial_width, &[], ctx).await?;
            let retry: Vec<String> = (1..=count)
                .map(|i| format!("{}{:0width$}", prefix, new_max + i as i64, width=rule.serial_width))
                .collect();
            batch_insert(target, &retry, ctx.txn()).await?;
            Ok(retry)
        }
        e => e?,
    }
}
```

**效果**：导入 1000 条凭证，只查 1 次 max、1 次 INSERT（批量），冲突概率从 1000 次降到 1 次。**不建任何表**。

### 4.6 PG SEQUENCE 兜底（档位三：极端高并发可选）

对于日均 10 万+ 且要求连续号的域（极少见），规则可配 `useSequence:true`，引擎走 PG 原生 SEQUENCE：

```sql
-- 规则启用时自动创建（DDL 随规则部署）
CREATE SEQUENCE IF NOT EXISTS seq_cv_header_doc_no;

-- 取号（PG 行级锁，并发绝对安全，无重试）
SELECT nextval('seq_cv_header_doc_no');
```

**这不是"计数器表"**：PG SEQUENCE 是数据库内置机制（存在 pg_sequence 系统表里），不是业务表，不存储编码本身，只存递增游标。不违背"不存已分配编码"约束。

> ⚠ SEQUENCE 的号不保证连续（事务回滚号会跳）--所以**默认不开**，只在断号补偿（enableGap）能接受跳号或不需要连号的极端高并发域显式启用。连号域（凭证号）不用 SEQUENCE，走批量取号。

### 4.7 并发性能对比

| 并发量 | 单条重试 | 批量取号 | PG SEQUENCE |
|---|---|---|---|
| 10/秒 | 0 次冲突 | 不适用 | 不需要 |
| 100/秒 | 偶尔 1-2 次重试 | 0 次冲突 | 0 次冲突 |
| 1000/秒 | 重试次数高（不推荐） | 0-1 次整批重试 | 0 次冲突 |
| 10000/秒 | 雪崩（禁用） | 偶尔整批重试 | 0 次冲突 |
| 建表 | ❌ | ❌ | ✅（DB 内置 SEQUENCE，非业务表） |

### 4.8 编码依据（resetBy）= 金蝶「编码依据」

| resetBy | 求值 | 语义（金蝶同构） |
|---|---|---|
| `null` | `"_global_"` | 全局连续 |
| `"date"` | 当前日期 | 按日重置（金蝶「按天重置流水」） |
| `"category+date"` | 分类+日期 | 多维重置 |
| `"org_code"` | 组织码 | **组织作编码依据 -> 组织内唯一校验**（金蝶明确支持） |
| 任意字段名（如 `"parent_id"`） | `attrs[field]` 的值 | 按该字段值分组重置（树形科目按父级重置） |

#### 4.8.1 resetBy 如何影响反查 max（关键机制）

**resetBy 不是装饰字段——它直接改变反查 max 的 WHERE 子句。** resetBy 求值出 `reset_key` 后，必须作为独立的分组维度参与 max 查询，否则「按日重置」「按组织重置」全是空话。

**反查 max 的正确形态**（reset_key 非全局时）：

```sql
-- resetBy="date"，reset_key="20260805"
-- 反查范围 = prefix + reset_key 分组下的最大流水
SELECT COALESCE(
    MAX(CAST(SUBSTRING(code FROM LENGTH('FV20260805')+1 FOR 4) AS INTEGER)), 0
) FROM cv_header
WHERE code LIKE 'FV20260805%'          -- prefix 必须含 reset_key
  AND LENGTH(code) = LENGTH('FV20260805')+4
  AND SUBSTRING(code FROM LENGTH('FV20260805')+1) ~ '^[0-9]+$';
```

**两种实现路径**（任选其一，落地须明确）：

| 路径 | 做法 | 优点 | 缺点 |
|---|---|---|---|
| **A. reset_key 拼进 prefix** | reset_key 求值后拼进固定段前缀，反查 `WHERE code LIKE '{prefix}{reset_key}%'` | 复用现有 prefix LIKE，无需改 SQL 签名 | prefix 动态膨胀；同一规则多 reset 维度时 prefix 较长 |
| **B. query_max_serial 加 reset_key 参数** | `query_max_serial(target, prefix, width, reset_key, buffer)`，WHERE 加 `AND reset_key 列匹配`（需额外列或派生） | prefix 与 reset 维度解耦 | 业务表需有 reset_key 派生列，或 SQL 内 SUBSTRING 提取 |

**CMX 采用路径 A**（reset_key 进 prefix）：简单、复用 LIKE 索引、无需改表结构。规则配置时确保 resetBy 依赖的值**已经出现在段序列里**（要么是显式 ref/date 段，要么 reset_key 自动拼进 prefix）。

#### 4.8.2 dateSerial 段的隐式 resetBy

`dateSerial` 段的 resetBy 隐式 = 日期串（format 出来的值）。关键：**这个日期串必须进 prefix**，否则 dateSerial 退化成「全局 serial + 装饰日期」。

- dateSerial 段求值时，先把日期 format 出来拼进 prefix（如 `20260805`），再返回 `NeedsSerial { reset_key: "20260805", ... }`
- 反查 max 走 `WHERE code LIKE '{前缀日期}%'`，天然按日分组
- 落地要点：`rule_algo::resolve_fixed_segments` 求固定段前缀时，**dateSerial 段的日期部分要算进前缀**，不能只把 serial 部分留到 NeedsSerial

#### 4.8.3 resetBy 求值规则（serial 段）

`serial` 段的 resetBy 支持 `+` 分隔的复合表达式：

| 表达式 | 求值 | 示例 |
|---|---|---|
| `null` / 空 | 字面量 `"_global_"` | 全局连续 |
| `"date"` | `ctx.now` 按 `YYYYMMDD` 格式化 | `20260805` |
| `"org_code"` | `ctx.org.org_code` | `HQ` |
| `"category"` 或任意字段名 | `ctx.attr_str(field)`，取不到**报错**（`RefFieldMissing`） | `raw` |
| `"category+date"` | 上述多个值拼接 | `raw20260805` |

**取不到值的处理差异**：
- `date` / `org_code`：系统上下文，必有值
- 任意字段名：业务属性，**取不到必须报错**（不是走 fallback 空串）—— 因为 resetBy 的值是分组维度，空串会让所有缺失该字段的行混进同一组，造成号段错乱

#### 4.8.4 resetBy 与 ref 段前缀的关系

如果规则里**既有 ref 段（取 `category` 当前缀）又有 serial 段（resetBy 也是 `category`）**，两者重复但不冲突——prefix 里已含 category 值，reset_key 再拼一次是冗余但无害（路径 A 的 LIKE 子串匹配幂等）。设计上建议：ref 段出现过的字段，serial 的 resetBy 不必再指定（避免配置冗余）。

---

## 05 · 断号表 + 断号补偿（借鉴金蝶）

**默认关闭**--只有**连号域**（凭证号、发票号、支票号要求连号）才启用。普通主数据（供应商、物料）不需要连号，默认走反查 max。

### 5.1 什么场景产生断号

```
断号 = 曾被分配但最终未落库的流水号（号段出现空缺）

产生场景：
  ① 事务回滚:   A 在事务内拿到 0008,整个业务事务回滚 -> 0008 没进业务表
                 但 B 在 A 之后并发已拿到 0009 并落库 -> 0008 成断号
  ② 规则改版:   旧规则 validTo 生效停在 0007,新规则换前缀从新序列开始
                 -> 旧前缀 0008-9999 成片"断号"
  ③ 手动删除:   管理员物理删了某条记录 -> 被删的号成断号
  ④ 并发冲突后放弃: A 拿 0008 冲突,重试拿 0009;若启用预占模式,A 预占的 0008 未释放
```

### 5.2 断号表结构

```sql
CREATE TABLE cmx_code_gap (              -- 断号表(只记断号,不记已分配码)
  id          BIGINT PRIMARY KEY,
  rule_id     BIGINT NOT NULL,                  -- 关联 cmx_code_rule.id
  prefix      VARCHAR(128) NOT NULL,            -- 断号所属前缀(如 "FV20260804")
  gap_value   INTEGER NOT NULL,                 -- 断号的流水值(如 8)
  gap_reason  VARCHAR(32) NOT NULL,             -- rollback/re-rule/delete/abandon
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(rule_id, prefix, gap_value)            -- 同前缀同号不重复记
);
CREATE INDEX ix_gap_take ON cmx_code_gap(rule_id, prefix, gap_value);
```

### 5.3 断号补偿工作流（启用 enable_gap 时）

```
铸号请求 (enable_gap=true)
 │
 ├─ 1. 查断号表: SELECT ... FROM cmx_code_gap
 │               WHERE rule_id=? AND prefix=?
 │               ORDER BY gap_value ASC LIMIT 1 FOR UPDATE SKIP LOCKED
 │      ├─ 有断号 -> 取最小断号 -> DELETE 该断号 -> 返回此号(填补空缺)
 │      └─ 无断号 -> 走反查 max(§04)
 │
 ├─ 2. 落库失败回滚时 -> 把刚分配的号 INSERT 进 cmx_code_gap(记为断号)
 └─ 3. 管理员手动补号 -> /api/code/gaps 手动录入已知断号供补偿
```

#### 5.3.1 断号记录的事务陷阱（必读）

**步骤 2「落库失败回滚时记断号」有一个事务陷阱**：断号记录与业务落库若在同一事务，业务回滚时断号 INSERT 也会一起回滚，断号就丢了。

```
事务内：
  BEGIN
    INSERT 业务表 ... doc_no='FV202608050008'   ← 拿到号 0008
    ... 后续业务校验失败 ...
    INSERT cmx_code_gap gap_value=8              ← 想记断号
  ROLLBACK
    → 业务表的 INSERT 回滚 ✅
    → cmx_code_gap 的 INSERT 也回滚 ❌  ← 断号没记上！
```

**根本原因**：`try_insert` 在业务事务内执行，回滚是原子的，断号记录无法在回滚事务里幸存。

**三种解法**（落地任选其一）：

| 解法 | 做法 | 适用场景 |
|---|---|---|
| **A. 独立事务记断号** | 回滚发生后，开一个**新的独立事务** INSERT 断号（与业务事务解耦） | 通用，推荐 |
| **B. SAVEPOINT 局部提交** | 断号 INSERT 用 `SAVEPOINT gap_log` 包裹，业务回滚前先 `RELEASE SAVEPOINT` 提交断号 | PG 原生支持，稍复杂 |
| **C. 不在铸号时记，靠对账补** | 铸号时不记断号；定期对账任务扫描「号段空洞」补录 cmx_code_gap | 简单但断号补偿有延迟 |

**CMX 建议路径 A**：铸号函数返回「待记断号」标记，由 saver 的回滚回调（或事务后钩子）开独立事务补记。理由：① 不污染业务事务；② 回滚路径清晰；③ 集群安全（独立事务走连接池）。

> 📌 **C1 阶段的现状**：当前 `try_insert` 恒返回 `Ok(())`（serial_pg.rs:100），铸号阶段不做真实 INSERT，断号记录尚未接入。真正的 UNIQUE 兜底靠 saver 落库时的 DB 约束，断号补偿（C6）实现时必须按本节解法处理事务边界。

#### 5.3.2 断号产生的真实场景与记录时机

对照 §5.1 的四种断号场景，记录时机：

| 场景 | 触发点 | 记录方式 |
|---|---|---|
| ① 事务回滚 | saver 业务事务 ROLLBACK | 解法 A/B（独立事务或 SAVEPOINT） |
| ② 规则改版 | 旧规则停用、换前缀 | 对账任务扫旧前缀空洞（场景 C） |
| ③ 手动删除 | 管理员物理删业务记录 | 删除 API 钩子记断号（删除在同一事务，可直接 INSERT） |
| ④ 并发冲突放弃 | UNIQUE 冲突后重试，旧候选号被放弃 | **不记**——重试是正常并发行为，被放弃的号不算断号（否则每次并发都产生大量假断号） |

**场景 ④ 不记断号**是重要约定：UNIQUE 冲突重试是引擎正常工作，每次冲突都记断号会让断号表被并发噪音淹没。只有「已分配但最终未落库」的号（场景 ① ③）才是真断号。

### 5.4 连号域 vs 非连号域的选型

| 域类型 | enable_gap | 代表场景 | 理由 |
|---|---|---|---|
| **连号域** | `true` | 凭证号、发票号、支票号、合同号 | 审计/税务要求连号，断号要解释 |
| **非连号域** | `false`（默认） | 供应商码、物料码、客户码 | 主数据不要求连号，号段空洞无妨，省一张表 |

---

## 06 · 随机段：字符池 / 数值范围（防重机制）

**支持指定位数的随机数**。两种随机模式（**不要 UUID**）。关键：**随机段不反查 max**（无 max 概念），靠 UNIQUE 冲突重试。

### 6.1 两种随机模式

```jsonc
// 模式 1:字符池随机
{ "type": "random", "mode": "charset", "width": 6,
  "charset": "alnum", "excludeAmbiguous": true }
// 从字符池均匀抽取 6 位 -> K7M3PQ

// 模式 2:数值范围随机
{ "type": "random", "mode": "range", "min": 1, "max": 9999, "pad": 4 }
// 1~9999 随机整数,左补零到 4 位 -> 0387
```

### 6.2 字符集（charset 模式）

| charset | 基础字符池 | excludeAmbiguous 过滤 |
|---|---|---|
| `"digit"` | `0123456789` | ❌ 不过滤（纯数字无字母歧义） |
| `"alpha"` | `ABCDEFGHIJKLMNOPQRSTUVWXYZ` | ✅ 过滤 → 去掉 0/O/1/I/l/Z/2/B/8 中池里存在的 |
| `"alnum"` **默认** | `0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ` | ✅ 过滤 → 去掉 0/O/1/I/l/Z/2/B/8（剩去混淆字母数字） |
| `"hex"` | `0123456789abcdef` | ❌ 不过滤（16 进制无字母歧义，过滤会删 0/2 导致池缺失） |
| `"custom"` | 用户传入 `chars:"ABCD"` | ✅ 过滤（保守，防用户池混入歧义字符） |
| 其它字符串 | 用户直接传的字符串当池 | ❌ 不过滤（尊重用户输入） |

**excludeAmbiguous 过滤的 9 个易混淆字符**：`0 O 1 I l Z 2 B 8`（形似对：0/O、1/I/l、Z/2、B/8）。`excludeAmbiguous:false` 可关闭过滤（用完整基础池）。digit/hex 池天然无字母歧义，excludeAmbiguous 对它们**不生效**（避免删 0/2 破坏池完整性）。

### 6.3 防重机制：UNIQUE 冲突重试

```rust
/// 随机段铸号：生成候选 + UNIQUE 冲突重试。不反查 max（无 max 概念）。
/// 入口由 resolve_and_apply（§10.2）按段类型分流调用——规则含 random 段时走此函数而非 mint_single。
async fn mint_random(
    rule: &RuleSpec, target: &Target, ctx: &ResolveContext,
) -> Result<String> {
    const MAX_RETRY_RANDOM: u32 = 16;
    let random_seg = rule.segments.iter().find(|s| s.seg_type == "random")
        .ok_or(CodeError::NoRandomSegment)?;
    for attempt in 1..=MAX_RETRY_RANDOM {
        let candidate = resolve_fixed_segments(rule, ctx).await?   // 非随机段前缀
                      + &random_gen(random_seg)?;                  // 随机段（§6.1/6.2）
        match try_insert(target, &candidate, ctx.txn()).await {    // 签名与 §4.4 一致
            Ok(_) => return Ok(candidate),
            Err(UniqueViolation) if attempt < MAX_RETRY_RANDOM => continue, // 换种子重试
            e => return e?,
        }
    }
    Err(CodeError::RandomSpaceExhausted)    // 空间快满,提示扩位
}

/// 随机段候选生成（charset 模式从字符池抽位 / range 模式取区间随机整数，§6.1/6.2）
fn random_gen(seg: &SegmentSpec) -> Result<String>;
```

### 6.4 碰撞空间护栏（生日悖论）

| 位数 | 字符集 | 空间 N | 安全用量（碰撞率<1%） |
|---|---|---|---|
| 4 | 数字 | 1 万 | ~66 |
| 6 | 数字 | 100 万 | ~660 |
| 6 | 去混淆 alnum | 8 亿 | ~6000 |
| 8 | 去混淆 alnum | 1.3 万亿 | ~25 万 |
| 10 | 去混淆 alnum | 5700 万亿 | ~50 亿 |

deploy 校验时按业务预估用量告警。

---

## 07 · 断号表与「不存已分配编码」的调和

你担心断号表会违背「不存储已分配编码」。两者不矛盾--**断号 ≠ 已分配**。

| 维度 | 已分配编码 | 断号 |
|---|---|---|
| **定义** | 成功落库、正在使用的编码 | 曾被分配但最终未落库的空缺号 |
| **存哪** | **业务表自身**（cf_bus_partner.code 列） | 断号表 cmx_code_gap（可选） |
| **你的约束** | ❌ 不另存（反查 max 即可） | ✅ 可存（不违背约束） |
| **为什么不矛盾** | 反查 max 读的是业务表，不读计数器 | 断号表只记「空缺」，不记「已用」 |

**三种数据存储的边界**：

```
┌─────────────────────────────────────────────────────────────────┐
│  业务表 cf_bus_partner.code 列                                    │  ← 唯一真相
│  存:已分配并落库的编码(VRM26080008)                                 │  ← 反查 max 的数据源
│  性质:✅ 存(这是业务数据本身,不算"额外存储已分配码")                │
├─────────────────────────────────────────────────────────────────┤
│  断号表 cmx_code_gap(可选,连号域才开)                              │  ← 只存空缺
│  存:曾被分配但未落库的号(8)                                        │  ← 不是"已分配"
│  性质:✅ 存(不违背"不存已分配",因为存的是"未分配的空缺")            │
├─────────────────────────────────────────────────────────────────┤
│  计数器表 cmx_code_counter(❌ 不建)                                │  ← 你明确反对
│  存:已分配到的最大号(next_val)                                     │
│  性质:❌ 不存(这才是"存储已分配编码",违背约束)                      │
└─────────────────────────────────────────────────────────────────┘
```

**一句话**：你的约束是「不存**已分配**的编码」--指的是不建计数器表记录 next_val。断号表存的是**未被使用的空缺**，性质完全不同。V2 方案：**不建计数器（反查 max）+ 可选建断号表（只记空缺）**，两者都符合你的约束。

---

## 08 · 前后端协作：后端权威 + 前端预览

**不能两端都生成，必须后端权威 + 前端预览**。理由：并发安全、永不回收、审计责任、防篡改。

### 8.1 协作流程

```
用户填表(ref 段所需属性填好)
 │
 ├─ 点「预览编码」 -> POST /api/code/preview
 │     后端:选规则 -> 求固定段 -> (查断号/反查 max) -> 返回 code + ruleCode
 │     ★ 不落库,不推进流水号,纯算术展示
 │     前端:code 字段只读显示 "VRM260800087"
 │
 ├─ 用户「保存」 -> 后端在事务内:反查 max + 拼装 + UNIQUE 重试 -> 定稿
 │     ★ 真正的号分配只发生在落库事务内
 │
 └─ 用户放弃 -> 无副作用(预览未落库,未占号)
```

**关键：预览不占号**--预览不推进流水号、不落库。用户放弃预览无任何副作用。真正的号分配只发生在落库事务内。

### 8.2 manual 模式：前端手敲，引擎只校验

现状 manual（用户手敲 + pattern 正则校验）**完全保留**，不调 preview/generate，与现状零差异。

---

## 09 · 补位 / 填充 / 截断 / 替代 / 步长（借鉴金蝶）

| 属性 | 金蝶叫法 | 作用 | V2 默认 |
|---|---|---|---|
| **padChar** | 补位符 | 长度不够时补的字符 | `"0"`（流水）/ `" "`（文本） |
| **padSide** | 右侧填充 | 补位方向：`left`左补 / `right`右补 | `left`（金蝶不勾选=左填充） |
| **truncate** | 右侧截断 | 超长时是否截断：`none`报错 / `right`右截 | `none`（超长报错） |
| **fallback** | 替代符 | 取不到值时的替代字符（ref 段引用字段为空时） | `""`空串（或报错） |
| **step** | 步长 | 流水号递增步长（支持整数；小数不支持断号补偿） | `1` |

段声明示例（含所有细节）：

```jsonc
{
  "type": "serial",
  "width": 6,
  "start": 1,                    // 起始值(金蝶支持整数和小数)
  "step": 1,                     // 步长(默认1;小数时不支持断号补偿)
  "resetBy": "date",             // 编码依据=金蝶「编码依据」,值变化时重置
  "padChar": "0",                // 补位符
  "padSide": "left",             // 左补(金蝶不勾选「右侧填充」)
  "truncate": "none"             // 超长报错(不截断)
}
```

ref 段的 fallback（替代符）：

```jsonc
{
  "type": "ref",
  "field": "category",
  "map": {"raw":"RM"},
  "fallback": "XX",            // category 为空或 map 无匹配时用 "XX" 替代
  "width": 2, "padChar": "_", "padSide": "right"
}
```

---

## 10 · 与 DCT/DOC 的集成（钩子 + 引用 + 多级表各自铸号 + 可选级联）

### 10.1 集成点：落库前钩子

```
DCT /api/dct/entries (upsert)   ┐
DCT /api/dct/save (changeset)  ┤   落库前(已过列级校验)
DOC /api/doc/.../save          ┤   ↓
                               ├─-> cmx_code::before_save(target, rows, txn)
                               │     ├─ 查 cmx_code_rule(按 target + orgScope + condition)
                               │     ├─ 若 mode=auto 且 code 为空/占位:
                               │     │   ├─ enable_gap? 查断号表 : 反查 max
                               │     │   └─ 拼装 + UNIQUE 重试(在事务内)
                               │     ├─ 若 mode=auto 且 code 已有(前端预览传): 后端重算定稿
                               │     └─ 若 mode=manual: 跳过(code 来自用户)
                               └─-> DCT/DOC 原落库逻辑
```

### 10.2 引用解析：ruleCode + target 上下文

target 不存在规则表里，由钩子调用时传入。解析分两步：① 从字典/单据定义读 `ruleCode`；② 用 ruleCode 查规则算法 + 用 target 查业务表。

```rust
async fn resolve_and_apply(
    rule_code: &str,            // 来自字典定义 codeRule.ruleCode
    target: &Target,            // 调用上下文 {kind, code, field} 由 DCT/DOC 钩子传入
    ctx: &ResolveContext,       // attrs + orgCtx + db + txn + minted_buffer + overrides
) -> Result<String> {
    // 1. 查 cmx_code_rule(纯算法,无 target)
    let candidates = query_rules(rule_code, ctx).await?;
    // 2. 按 orgScope + condition + priority 选优(规则自带,与 target 无关)
    let rule = candidates.into_iter()
        .filter(|r| org_matches(r, &ctx.org) && cond_matches(r, &ctx.attrs))
        .max_by_key(|r| r.priority)
        .ok_or(CodeError::NoMatchingRule)?;
    // 3. 应用挂载点局部覆盖（enableGap/pattern）后调 mint_single（§4.4）铸号
    let rule = rule.apply_overrides(ctx.overrides());
    let code = mint_single(&rule, target, ctx, ctx.minted_buffer()).await?;
    Ok(code)
}

// DCT 钩子调用示例:target 由 DCT 自己构造
let target = Target { kind: "dct", code: "bus_partner", field: "code" };
let code = resolve_and_apply("supplier_hq", &target, &ctx).await?;
```

### 10.3 DOC 多级表各自铸号（默认行为，不级联）

DOC 单据是多级树（批→头→分录→辅助），每级表都可能有自己的业务编码。**默认行为：遍历 changeset 里所有表，每张挂了 codeRule 的表独立铸号，互不干扰**。

**典型场景：凭证的批号与凭证号是两个独立号**

勘探结论（cmxfico_doc_meta_v1.json + 5 个厂商 DOC 定义一致）：

| 层级 | 表 | 有 doc_no 列 | 业务语义 |
|---|---|---|---|
| L0 批 | cv_batch | ✓ | **批号**（一次批量过户的批次标识） |
| L1 头 | cv_header | ✓ | **凭证号**（一张凭证的标识，≠批号） |
| L2 分录 | cv_acc_line | ✗ | 无此列，靠 `upper_id → cv_header.id` 外键关联头表 |
| L3 辅助 | cv_aux_line | ✗ | 同上 |

**关键**：批号和凭证号是**两个不同的号**，一个批含多张凭证（`cv_header.upper_id → cv_batch.id`）。引擎给 cv_batch 和 cv_header 各配一条 codeRule，各自独立铸号：

```
保存一个批（含 1 批 + 3 张凭证头 + N 条分录）
  │
  ├─ 遍历 changeset 表：
  │   ├─ cv_batch   挂了 codeRule(batch_daily,  field=doc_no) → 铸批号 BAT20260804001
  │   ├─ cv_header  挂了 codeRule(voucher_daily, field=doc_no) → 每张头各自铸 FV202608040001/0002/0003
  │   └─ cv_acc_line 没挂 codeRule（也无 doc_no 列）→ 跳过
  │
  └─ 批号 BAT20260804001 与凭证号 FV202608040001 互不干扰，各自连续
```

**钩子遍历伪码**（接在 §10.1 的 before_save 之后）：

```rust
async fn before_save_doc(
    changeset: &mut ChangeSet,     // 含本次保存的全部表行
    doc_meta: &DocMeta,            // 含 voucherTables + voucherSchema.relations
    ctx: &mut ResolveContext,      // 见 §10.2/§13.1，含 attrs/org/now/db/txn + builder 方法
) -> Result<()> {
    // 1. 遍历每张表，看是否挂了 codeRule
    for tbl in &doc_meta.voucher_tables {
        let Some(code_rule) = tbl.code_rule.as_ref() else { continue }; // 未挂→跳过
        if code_rule.mode != "auto" { continue; }                       // manual→跳过

        let target = Target {
            kind: "doc",
            code: &tbl.table_name,     // 如 "cv_header"
            field: &code_rule.field,   // 如 "doc_no"
        };

        // 2. 收集本表待铸号行（跳过已有非占位值=前端预览传的，§08 后端重算定稿）
        let pending_rows: Vec<usize> = changeset.row_indices(&tbl.table_name)
            .filter(|i| is_placeholder_or_empty(changeset.row(*i).get(&code_rule.field)))
            .collect();
        let n = pending_rows.len();
        if n == 0 { continue; }

        // 3. 按行数切档位（§4.3 三档策略）：
        //    n==1 或小批量(<阈值 BATCH_THRESHOLD=50)：走单条重试 + minted_buffer 推进（§4.4）
        //    n>=阈值：走批量取号（§4.5），一次反查 max 取一段，本地分配后整批写回
        //    原因：1000 张头逐行反查会触发 §4.3 的"1000/秒雪崩"；批量取号只 1 次 max + 1 次 INSERT
        if n < BATCH_THRESHOLD {
            // 3a. 单条重试路径（档位一）+ minted_buffer 推进
            let mut local_buffer: Vec<String> = Vec::new();
            for row_idx in pending_rows {
                if let Some(cascade) = &code_rule.cascade {
                    mint_and_cascade(target, code_rule, row_idx, cascade, changeset, doc_meta, ctx, &mut local_buffer).await?;
                } else {
                    let ctx2 = ctx.with(changeset.row(row_idx).attrs()).with_minted(&local_buffer);
                    let code = resolve_and_apply(&code_rule.rule_code, &target, &ctx2).await?;
                    changeset.row_mut(row_idx).insert(code_rule.field.clone(), code.clone());
                    local_buffer.push(code);
                }
            }
        } else {
            // 3b. 批量取号路径（档位二，§4.5）：一次取 n 个连续号，按行序分配
            //     级联场景：号已预分配，复用 §10.4 mint_and_cascade 的 ②③ 步（沿 relations 回填子表），
            //     只是号来自 batch_generate 而非逐行铸。把 mint_and_cascade 的 ① 铸号替换为「取已分配号」即可。
            let codes = batch_generate(&code_rule.to_rule_spec(), &target, n, ctx).await?;
            for (row_idx, code) in pending_rows.iter().zip(codes.iter()) {
                changeset.row_mut(*row_idx).insert(code_rule.field.clone(), code.clone());
                if let Some(cascade) = &code_rule.cascade {
                    // 批量级联回填：复用 §10.4 mint_and_cascade 的 ② relations 查找 + ③ 外键匹配回填，
                    // 跳过 ① 铸号（号已由 batch_generate 预分配）。封装为 cascade_fill_only 辅助函数。
                    cascade_fill_only(target, code, cascade, *row_idx, changeset, doc_meta, ctx).await?;
                }
            }
        }
    }
    Ok(())
}
```

> ⚠ **同一 changeset 多行铸号的两条路径**：
> - **小批量（n < 50）**：走单条重试 + `minted_buffer` 推进。buffer 记录本次已铸号，反查 max 时 union 进候选集（§4.1 buffer 注入），保证同事务内多行号连续不重。典型场景：凭证录入一次存 1-3 张头。
> - **大批量（n ≥ 50）**：走批量取号（§4.5），一次反查 max 取 n 个连续号本地分配，避免逐行反查触发雪崩。典型场景：批量导入 1000 张凭证头。
> - **档位切换阈值 `BATCH_THRESHOLD`**：默认 50（可配），平衡单条重试的简单与批量取号的效率。跨事务并发仍靠 UNIQUE 重试（§4.2）。

**为什么默认不级联**：分录表靠 `upper_id` 外键关联头表，查 doc_no 走 `JOIN cv_header` 即可，物理冗余 doc_no 违反范式。五个厂商（cmxfico/金蝶/SAP/用友/EBS）的分录表都没冗余 doc_no，引擎遵循这一行业惯例。需要冗余时显式配 cascade（§10.4）。

### 10.4 可选级联回填（cascade）

**仅当业务要求子表物理冗余父表编码时启用**（少数反范式优化场景）。在父表的 codeRule 上声明 `cascade`，引擎铸完父号后沿 `voucherSchema.relations` 把号写到子表对应字段。

> ⚠ **relations 逻辑名 vs 物理表名映射**（勘探结论）：cmxfico 的 `voucherSchema.relations` 用的是**逻辑名**，不是物理表名：
> ```
> parent=cv_batch    child=headers        parentKey=id  childKey=upper_id
> parent=headers     child=account_lines  parentKey=id  childKey=upper_id
> ```
> 而 `voucherTables[].tableName` 是物理表名（`cv_header`/`cv_acc_line`）。引擎拿物理表名 `cv_header` 去匹配 relations 的 `parent="headers"` 会**匹配不上**。
> **解法**：`DocMeta` 提供 `logical_to_physical` 映射（由 `voucherSchema.schema` 树的 `id` 字段推导：树节点 `id` 是物理表名，节点在 relations 里以逻辑名出现）。`direct_children`/`all_descendants` 内部先做 `physical → logical → relations 查找 → logical → physical` 双向转换。伪码里 `target.code` 是物理表名，辅助函数内部处理映射，调用方无感。

**cascade 声明形态**：

```json
// 例：cv_header 铸完凭证号后，回填到直接子表（cv_acc_line）的 doc_no 列
{
  "mode": "auto",
  "field": "doc_no",
  "ruleCode": "voucher_daily",
  "cascade": {
    "field": "doc_no",     // 回填到子表的哪个字段
    "scope": "children"    // 默认 children=仅直接子表；descendants=沿 relations 链下钻全部后代（少用）
  }
}
```

**前置约束**：子表必须**物理存在**该字段，否则引擎跳过（不报错，记 warn 日志）。给分录表加 doc_no 列需改定义：

```json
// cv_acc_line 的 documentFieldSets 加 documentIdentityFields（含 doc_no）
"documentFieldSets": ["documentLevelFields", "documentTechnicalFields", "documentIdentityFields"]
```

改完重新 compile 建表加列，之后 cascade 才能写入。

**级联回填伪码**（不硬编码表名，纯靠 relations 驱动）：

```rust
async fn mint_and_cascade(
    target: &Target,
    code_rule: &CodeRule,            // 挂载点声明（含局部 enableGap 覆盖），命名与 §10.3 调用点一致
    parent_row_idx: usize,          // 父行在 changeset 的下标（用下标避免借用冲突）
    cascade: &Cascade,
    changeset: &mut ChangeSet,
    doc_meta: &DocMeta,
    ctx: &mut ResolveContext,       // 见 §10.2/§13.1
    local_buffer: &mut Vec<String>, // 同事务本表已铸号（§10.3 缺陷1：多行铸号 max 推进）
) -> Result<()> {
    // ① 先给父表铸号（局部 enableGap 覆盖规则表：传 ctx.with_overrides 把挂载点的 enableGap 注入）
    let parent_attrs = changeset.row(parent_row_idx).attrs();
    let ctx2 = ctx.with(parent_attrs).with_minted(local_buffer)
                     .with_overrides(code_rule.local_overrides()); // 含 enableGap/pattern 局部覆盖
    let code = resolve_and_apply(&code_rule.rule_code, target, &ctx2).await?;
    changeset.row_mut(parent_row_idx).insert(code_rule.field.clone(), code.clone());
    local_buffer.push(code.clone()); // 记住本次铸的号

    // ② 沿 voucherSchema.relations 找子表（relations 逻辑名→物理表名映射由 doc_meta 提供）
    let descendants = match cascade.scope {
        Scope::Children => direct_children(doc_meta, target.code),     // 直接子表
        Scope::Descendants => all_descendants(doc_meta, target.code),  // 沿链下钻全部后代
    };

    // ③ 对每个子表，若有 cascade.field 列，按外键关联回填
    //    parent_key 取父表主键（如 cv_header.id），由 mint_ids_for_changeset ① 已铸
    for (child_tbl, parent_key, child_key) in descendants {
        if !ctx.has_column(&child_tbl, &cascade.field) { continue; } // 子表没这列→跳过+warn
        // relations 给的是 child_row.{child_key} == parent_row.{parent_key}
        let pv = changeset.row(parent_row_idx).get(&parent_key).cloned();
        for child_idx in changeset.row_indices(&child_tbl) {
            if changeset.row(child_idx).get(&child_key) == pv.as_ref() {
                changeset.row_mut(child_idx).insert(cascade.field.clone(), code.clone());
            }
        }
    }
    Ok(())
}
```

**为什么靠 relations 驱动**：换采购订单（po_header→po_line）、换发票（inv_header→inv_line），relations 不同但机制相同，引擎零改。`voucherSchema.relations` 已是 DOC 定义的标准结构（见 cmxfico_doc_meta_v1.json: `cv_header.id → cv_acc_line.upper_id`）。

**与「不存已分配编码」原则的关系**：cascade 回填的是**父表的编码副本**到子表，不是子表独立取号。子表不参与反查 max、不参与 UNIQUE 重试，只是被动接收父号。不违反 §07 的原则。

> 📌 **批量取号 + 级联（§10.3 步骤 3b 调用）**：批量路径（n ≥ BATCH_THRESHOLD）用 `batch_generate` 一次取 n 个号后，级联回填复用本函数的 ②（relations 查找）+ ③（外键匹配回填）两步，跳过 ①（铸号，号已预分配）。封装为 `cascade_fill_only(target, code, cascade, parent_row_idx, changeset, doc_meta, ctx)` 辅助函数——即 `mint_and_cascade` 去掉 ① 铸号的剩余部分。

**辅助函数签名**（mint_and_cascade ②③ 步依赖，归 cmx-code-api 的 store 模块）：

```rust
/// 沿 voucherSchema.relations 找直接子表（depth=1）
/// 返回 [(child_table, parent_key, child_key)]，如 [("cv_acc_line", "id", "upper_id")]
fn direct_children(doc_meta: &DocMeta, parent_table: &str) -> Vec<(String, String, String)>;

/// 沿 relations 链下钻全部后代（BFS 直到叶子）
/// 如 cv_header → [cv_acc_line] → [cv_aux_line]，返回两层的 (table, parent_key, child_key)
fn all_descendants(doc_meta: &DocMeta, parent_table: &str) -> Vec<(String, String, String)>;

/// 批量取号场景的级联回填：号已由 batch_generate 预分配，只做 mint_and_cascade 的 ②③ 步
/// 签名与 mint_and_cascade 相同但去掉 rule/local_buffer 参数，多一个已分配的 code 参数
async fn cascade_fill_only(
    target: &Target, code: &str, cascade: &Cascade,
    parent_row_idx: usize, changeset: &mut ChangeSet,
    doc_meta: &DocMeta, ctx: &mut ResolveContext,
) -> Result<()>;
```

---

## 11 · REST API 契约（归 cmx-code-api 管）

所有 API 由 `cmx-code-api` crate 提供（`CodeModule impl ModuleRoutes`，前缀 `/api/code/*`），在 `web-server/routes.rs` 一行 `.merge(CodeModule.routes())` 接入。

| 端点 | 方法 | 职责 |
|---|---|---|
| `/api/code/rules` | GET/POST | 规则库 CRUD（独立管理） |
| `/api/code/rules/{ruleCode}` | GET/PUT/DELETE | 单条规则 |
| `/api/code/preview` | POST | 预览编码（不落库，不占号） |
| `/api/code/preview/batch` **NEW** | POST | 批量预览（N 行同表，不落库不占号，按行返回 N 个预览码） |
| `/api/code/generate` | POST | 权威生成并落库（事务内重试） |
| `/api/code/generate/batch` **NEW** | POST | 批量生成（N 行同表，走 §4.5 批量取号一次取一段，整批落库） |
| `/api/code/validate` | POST | 校验 code 是否符合规则（manual 用） |
| `/api/code/gaps` **NEW** | GET/POST | 断号查询 / 手动补号（连号域） |
| `/api/code/gaps/take` **NEW** | POST | 手动取一个断号填补 |

> 📌 **批量端点对应 §10.3 档位切换**：DOC 保存多行时，钩子按 `BATCH_THRESHOLD` 决定走 `/generate`（单条重试 + minted_buffer）还是 `/generate/batch`（批量取号）。前端预览多行同理走 `/preview/batch`。批量端点的 target 必须同表同字段（一次调用只服务一张表的 N 行）。

### 11.1 preview 契约

```jsonc
// POST /api/code/preview
{
  "target": { "kind": "dct", "code": "bus_partner", "field": "code" },
  "attrs": { "category": "raw" },
  "orgCtx": { "orgCode": "HQ" }
}
// Response
{ "code": 0, "data": {
  "code": "VRM260800087", "ruleCode": "supplier_hq",
  "segments": [ {"type":"const","value":"V"}, {"type":"ref","resolved":"RM"}, {"type":"date","resolved":"2608"}, {"type":"serial","resolved":"0008"}, {"type":"custom:check_digit","resolved":"7"} ],
  "warning": "预览码非定稿,最终以保存时为准"
}}
```

---

## 12 · 完整规则示例（八类典型场景）

> 八个示例覆盖 §2 全部 7 种段类型。段类型 × 示例矩阵：

| 段类型 | 出现在 | 覆盖 |
|---|---|---|
| const 固定段 | §12.1/12.2/12.3/12.5/12.7 | ✅ |
| serial 流水段 | §12.1/12.2/12.3(dateSerial)/12.4/12.7 | ✅ |
| date 日期段 | §12.1/12.6 | ✅ |
| dateSerial 日期流水段 | §12.3 | ✅ |
| ref 引用段 | §12.1/12.2/12.4/12.7 | ✅ |
| random 随机段 | §12.5(charset)/12.6(range) | ✅ |
| custom 自定义段 | §12.1(check_digit) | ✅ |

### 12.1 供应商码（固定+引用+日期+流水+校验位）

```jsonc
{ "ruleCode":"supplier_hq", "target":{"kind":"dct","code":"bus_partner"},
  "mode":"auto", "orgScope":"HQ",
  "condition": "bp_role=='supplier'",   // 简化字符串表达式(当前实现支持);JSON 算子为目标形态(§3.4.2)
  "segments":[
    {"type":"const","value":"V"},
    {"type":"ref","field":"category","map":{"raw":"RM"}},
    {"type":"date","format":"YYMM"},
    {"type":"serial","width":4,"resetBy":"category+date"},
    {"type":"custom:check_digit","algo":"mod11"}
  ] }
// -> VRM260800087
```

### 12.2 物料码（固定+分类引用+流水）

```jsonc
{ "segments":[
    {"type":"const","value":"M"},
    {"type":"ref","field":"material_group","take":3},
    {"type":"serial","width":5} ] }
// -> MEL000042
```

### 12.3 凭证号（日期流水 + 断号补偿）连号域

```jsonc
{ "ruleCode":"voucher_daily",
  "target":{"kind":"doc","code":"cv_header","field":"doc_no"},  // 表名见附录 A：cv_header（非 gl_voucher）
  "mode":"auto",
  "enableGap": true,                  // ★ 连号域启用断号补偿
  "segments":[
    {"type":"const","value":"FV"},
    {"type":"dateSerial","format":"YYYYMMDD","width":4}
  ] }
// -> FV202608040001 (断号会被补偿填补,保证连号；与附录 A 一致)
```

### 12.4 科目码（引用上级 + 流水，树形）

```jsonc
{ "segments":[
    {"type":"ref","field":"parent_id","refField":"code"},   // refField 取父记录字段值(钩子层以 code 名塞进 attrs)
    {"type":"serial","width":2,"resetBy":"parent_id"} ] }
// -> 100103 (父1001 + 子03)
```

### 12.5 邀请码（固定前缀 + 随机）随机段

```jsonc
{ "segments":[
    {"type":"const","value":"INV"},
    {"type":"random","mode":"charset","width":6,"charset":"alnum"} ] }
// -> INVK7M3PQ (防猜测,UNIQUE 冲突重试)
```

### 12.6 防猜测订单号（日期 + 随机数值范围）随机段

```jsonc
{ "segments":[
    {"type":"date","format":"YYMMDD"},
    {"type":"random","mode":"range","min":1000,"max":9999,"pad":4} ] }
// -> 260804-7381 (竞品无法推算单量)
```

### 12.7 组织码（固定+引用+流水，按集团重置）

```jsonc
{ "segments":[
    {"type":"const","value":"O"},
    {"type":"ref","field":"group_code","map":{"east":"E","west":"W"}},
    {"type":"serial","width":4,"resetBy":"group_code"} ] }
// -> OE0012
```

### 12.8 manual 模式（保留现状）

```jsonc
// 现有定义不变,引擎读 manual 走现状
"codeRule": { "mode": "manual", "pattern": "^[0-9]{1,3}$" }
// 引擎:前端手敲 + 正则校验 + DB UNIQUE 兜底。零改动。
```

---

## 13 · crate 架构与无状态约束

采用**两段式**：`cmx-code-model`（纯逻辑，可被 DCT/DOC 钩子轻量依赖）+ `cmx-code-api`（store 并入 api：规则库/断号表读写 + HTTP handlers）。

### 13.1 两段式 crate 结构

```
cmx-code-model/                  # 纯逻辑层(无 DB/无 HTTP),可被 cmx-dct/cmx-doc 钩子轻量依赖
├── src/
│   ├── lib.rs                  # 公共入口
│   ├── error.rs                # CodeError(thiserror)
│   ├── spec.rs                 # 类型定义：
│   │                           #   RuleSpec（规则算法：segments/joiner/enable_gap，来自 cmx_code_rule 表）
│   │                           #   CodeRule（挂载点声明：rule_code/field/mode/enableGap/pattern/uniqueCheck/cascade，来自 DCT/DOC 定义 §3.3）
│   │                           #     ├ to_rule_spec() -> RuleSpec   // 挂载点→算法（§10.3 batch_generate 调用）
│   │                           #     └ local_overrides() -> Overrides // 取 enableGap/pattern 局部覆盖（§10.4 with_overrides 调用）
│   │                           #   SegmentSpec（段声明：type + 各段专属字段，§2.1）
│   │                           #   Target { kind, code, field }（§10.2）
│   │                           #   Cascade { field, scope: Scope }（§10.4 级联配置）
│   │                           #   Scope 枚举 { Children, Descendants }（§10.4 级联范围）
│   ├── registry.rs             # SegmentResolver 注册表(内置+自定义)
│   ├── context.rs              # ResolveContext：行数据/org/now/resolved_so_far + minted_buffer/overrides
│   │                           #   builder：.with(attrs) .with_minted(&[str]) .with_overrides(Overrides) .txn()
│   ├── segments/
│   │   ├── mod.rs              # SegmentResolver trait
│   │   ├── const_.rs           # ① 固定段
│   │   ├── serial.rs           # ② 流水段(返回 NeedsSerial)
│   │   ├── date.rs             # ③ 日期段
│   │   ├── date_serial.rs      # ④ 日期流水段
│   │   ├── ref_.rs             # ⑤ 引用段
│   │   ├── random.rs           # ⑥ 随机段(NEW,返回 NeedsUniqueCheck)
│   │   └── custom.rs           # ⑦ 自定义段注册
│   ├── pad.rs                  # 补位/填充/截断/替代(借鉴金蝶)
│   ├── rule_algo.rs            # 纯算法:段序列求值+拼装(无副作用)
│   └── advance.rs              # 推进器 trait(DB 操作抽象,由 api 层实现)

cmx-code-api/                    # store + api 合并:DB 读写 + HTTP handlers
├── src/
│   ├── lib.rs                  # CodeModule impl ModuleRoutes
│   ├── store/
│   │   ├── mod.rs              # 数据库访问实现(含 batch_generate 批量取号 §4.5)
│   │   ├── rule_store.rs       # cmx_code_rule 表 CRUD
│   │   ├── gap_store.rs        # cmx_code_gap 断号表读写(可选)
│   │   ├── serial_pg.rs        # 反查 max SQL 实现(impl Advance trait, 含 minted_buffer 注入§4.1)
│   │   └── random_pg.rs        # 随机 UNIQUE 重试(impl Advance trait)
│   ├── engine.rs               # 主引擎:组合 rule_algo + advance,落地 DB
│   ├── handlers.rs             # HTTP handlers(§11 API 全在这里)
│   └── routes.rs               # ModuleRoutes:/api/code/* 前缀
└── tests/
```

### 13.2 为什么两段式

| 方案 | 利 | 弊 |
|---|---|---|
| **三段式** model/store-pg/api | 完全对齐 DCT/DOC/RPT 惯例 | cmx-code 相对轻量,三 crate 偏重;store 独立但只服务于 api |
| **单 crate** | 最轻量 | model 被钩子依赖时连带引入 store/api(cmx-dct->cmx-code 拉进 HTTP 层) |
| **两段式 ✅** model + api | model 纯逻辑可被钩子轻量依赖;store 并入 api;比三段少一个 crate | store 不独立(但本就只服务 api) |

**关键解耦**：`cmx-code-model` 定义 `Advance` trait（`query_max / take_gap / insert_with_retry` 等抽象方法），**不依赖**任何 DB crate。`cmx-code-api` 的 `serial_pg.rs / random_pg.rs` 实现这个 trait。DCT/DOC 钩子只需依赖轻量的 `cmx-code-model` + 由调用方注入 Advance 实现--**钩子不直接依赖 cmx-code-api**，避免环依赖。

### 13.3 依赖关系（破环）

```
cmx-code-model ──依赖──-> cmx-core(model/DataValue)            ← 纯逻辑,无 DB/HTTP
               ──定义──-> Advance trait(由 api 实现)

cmx-code-api   ──依赖──-> cmx-code-model(规则算法/段/Advance trait)
               ──依赖──-> cmx-database(反查 max/规则表/断号表)
               ──依赖──-> cmx-api(ModuleRoutes trait)
               ──实现──-> Advance trait

cmx-dct-store-pg ──依赖──-> cmx-code-model(钩子调用规则算法)  ← 轻量,不拉 api
                  └─ Advance 实现由 web-server 启动时注入(依赖注入)

cmx-doc-store-pg ──依赖──-> cmx-code-model(同上)

cmx-code-api ──不依赖──-> cmx-dct / cmx-doc  (反向解耦,无环)
cmx-code-model ──不依赖──-> cmx-database / cmx-api  (纯逻辑)
```

### 13.4 web-server 接入（一行 merge）

```rust
// crates/web/web-server/src/routes.rs
api_routes()
    .merge(ReportModule.routes()).merge(FlowModule.routes())
    .merge(DocModule.routes()).merge(DctModule.routes())
    .merge(CodeModule.routes())              // ← cmx-code-api 一行接入
    .merge(JobModule.routes()).merge(ModelModule.routes())
```

**完全无状态，集群安全**：无内存计数器、无单点状态、无文件锁。规则解析结果可进只读缓存（准静态）。唯一「状态」是业务表 code 列（PG 共享存储）+ 可选断号表。

---

## 14 · 落地路线图与风险

| 期 | 交付 | 性质 | 验收 |
|---|---|---|---|
| **C0** | **cmx-code-model** crate 骨架 + RuleSpec + SegmentResolver trait + **6 种段**（const/serial/date/dateSerial/ref/custom；random 段延后 C5）+ 补位/步长 + Advance trait（含 `query_max/take_gap/insert_with_retry` 抽象方法，实现可 stub）+ 纯算法 rule_algo | 新造 | 6 种段单测通过;model 无 DB 依赖;Advance trait 可 stub 实现 |
| **C1** | **cmx-code-api** crate 骨架 + store(单条反查 max 重试 + **批量取号**) + CodeModule.routes 接入 + UNIQUE 重试护栏 + **PG SEQUENCE 兜底**；`take_gap` 此时为 stub（返回 None，断号补偿 C6 才接真实断号表） | 核心 | 并发 100 线程零重号；批量 1000 条 1 次 max 查询；web-server merge 通过；enable_gap=true 时走纯反查 max（断号补偿待 C6） |
| **C2** | **独立规则库** cmx_code_rule 表(纯算法无 target) + rule_store + CRUD API + 规则选优(orgScope/condition/priority) | 新造 | 规则独立配置,字典引用 ruleCode,一条规则多处复用 |
| **C3** | DCT/DOC 集成钩子 + 内联/引用双解析 + **DOC 多级表各自铸号遍历（§10.3）** + **可选级联 cascade（§10.4）** + 1 样例字典改 auto | 接线 | 保存时按表各自铸号;多级树(批/头)各铸各号;manual 零影响;cascade 沿 relations 回填子表 |
| **C4** | preview API + 前端「预览编码」按钮 | 新造 | 预览不占号;保存定稿 |
| **C5** | **随机段**（§2.1 第⑥种段，C0 延后到此）charset/range + UNIQUE 重试 + 碰撞空间护栏；补全 `segments/random.rs`（model 层）+ `random_pg.rs`（api 层 Advance 实现） | 新造 | 邀请码/防猜测单号生成；C0 的 6 段补全为 7 段 |
| **C6** | **断号表 + 断号补偿** cmx_code_gap + enable_gap 流程 + 手动补号 API；C1 的 `take_gap` stub 升级为真实断号表查询 | 新造 | 凭证号连号域断号被填补；enable_gap=true 时优先取断号 |

### 14.1 风险

1. **高并发已内建三档策略**（§4.3-4.6）：单条重试（<100/秒）/ 批量取号（100~10000/秒，不建表）/ PG SEQUENCE 兜底（>10000/秒，可选）。凭证录入走单条重试零冲突；批量导入走批量取号一次查 max。
2. **随机段空间耗尽**：重试 16 次仍冲突报错。**缓解**：deploy 按预估用量告警扩位。
3. **断号表一致性**：事务回滚时要正确记断号。**缓解**：断号记录与业务落库在同一事务，回滚一起回滚。
4. **引擎不认识具体域**：供应商/科目全是配置，无 if 分支。

### 14.2 一页纸总结

**cmx-code V2** 是通用业务编码引擎，**两段式 crate**：cmx-code-model（纯逻辑，DCT/DOC 钩子轻量依赖）+ cmx-code-api（store 并入，DB 读写 + HTTP handlers + `/api/code/*`）。**七种段**：固定/流水/日期/日期流水/引用/**随机**/自定义。**独立规则库** cmx_code_rule 表（**纯算法，不带 target**，可被多处复用，字典定义只引用 ruleCode，target 由钩子调用时传入）。**不存已分配编码**--流水靠反查 max + UNIQUE 重试；**高并发默认支持**：三档策略（单条重试 / 批量取号不建表 / PG SEQUENCE 兜底可选）；**断号表只存空缺**（≠已分配，不违背约束），连号域默认关、可选开。**借鉴金蝶**：断号补偿、补位符/填充方向/替代符、步长/起始值、编码依据（resetBy）。**前后端协作后端权威**：前端只预览（不占号），后端事务内定稿。对现有 manual **完全兼容**，落地零破坏。

---

## 附录 A · 凭证号场景落地（多级表各自铸号）

> 回答"编码引擎如何落实到会计凭证"。核心结论：**批号、凭证号是两个独立号，各自铸号，互不级联；分录不存 doc_no，靠外键关联**。

### A.1 现状（勘探结论）

cmxfico 凭证 5 张表的 doc_no 分布（5 个厂商 DOC 定义一致）：

| 层级 | 表 | 有 doc_no 列 | 业务语义 |
|---|---|---|---|
| L0 批 | cv_batch | ✓ | 批号（一次批量过户的批次标识） |
| L1 头 | cv_header | ✓ | 凭证号（一张凭证的标识） |
| L2 分录 | cv_acc_line | ✗ | 无，靠 `upper_id → cv_header.id` 外键关联头表 |
| L3 辅助 | cv_aux_line | ✗ | 同上 |
| L4 作业 | cv_cyzb_line | ✗ | 同上 |

- **批号 ≠ 凭证号**：一个批含多张凭证（`cv_header.upper_id → cv_batch.id`），是两个独立号
- cv_header / cv_batch 的 doc_no **全程无人赋值**--完全靠前端/用户手填，无防重
- DOC saver（saver.rs:143）的 `mint_ids_for_changeset` 只铸主键 id，不碰 doc_no
- 分录表靠外键关联头表，查 doc_no 走 `JOIN cv_header`，无需冗余存储

### A.2 落地步骤

**前提**：批号、凭证号是两个独立号，各建各的规则。

1. **建规则**：在 cmx_code_rule 表建两条规则
   - `batch_daily`（auto + 固定 BAT + 日期 + 流水宽度 4）→ 批号 BAT202608040001
   - `voucher_daily`（auto + 固定 FV + 日期 + 流水宽度 4，enableGap=true 连号域）→ 凭证号 FV202608040001
2. **挂规则（定义管理器操作）**：
   - cv_batch 表：编码字段 doc_no，编码规则选自动，规则码 batch_daily
   - cv_header 表：编码字段 doc_no，编码规则选自动，规则码 voucher_daily，勾连号补偿
   - cv_acc_line / cv_aux_line / cv_cyzb_line：不挂 codeRule（无 doc_no 列，引擎跳过）
3. **声明 uniqueKeys**：cv_batch 加 `["doc_no"]`、cv_header 加 `["doc_no"]`（反查 max + UNIQUE 重试的前提）
4. **接入钩子**：DOC saver.rs 的 `apply_and_version` 落库前调 `cmx_code::before_save_doc(changeset, doc_meta, ctx)`（§10.3 遍历每张挂了 codeRule 的表各自铸号；ctx 含 txn）

### A.3 取号流程（一次保存含 1 批 + 3 张凭证头 + N 条分录）

```
用户填批（含多张凭证头 + 分录，doc_no 全留空）-> 点保存
  │
  ▼ DocSaver::save -> apply_and_version
  │
  ├─① mint_ids_for_changeset（铸全部主键 id，现状已有）
  ├─② cmx_code::before_save_doc（本方案钩子，遍历 changeset 各表）
  │     │
  │     ├─ cv_batch 行：挂了 codeRule(batch_daily, field=doc_no)
  │     │   ├─ 反查 max: SELECT MAX(...) FROM cv_batch WHERE doc_no LIKE 'BAT20260804%'
  │     │   └─ 铸批号 BAT20260804001 -> 写 cv_batch.doc_no
  │     │
  │     ├─ cv_header 行（3 张，各自铸号）：
  │     │   ├─ 反查 max: SELECT MAX(...) FROM cv_header WHERE doc_no LIKE 'FV20260804%'
  │     │   ├─ 查断号表(连号补偿)：无断号 -> 用 max+1
  │     │   ├─ 铸 FV202608040001 -> 写第 1 张头 doc_no（UNIQUE 重试）
  │     │   ├─ 铸 FV202608040002 -> 写第 2 张头 doc_no（UNIQUE 重试）
  │     │   └─ 铸 FV202608040003 -> 写第 3 张头 doc_no（UNIQUE 重试）
  │     │
  │     └─ cv_acc_line / cv_aux_line / cv_cyzb_line：没挂 codeRule -> 跳过
  │
  ├─③ validate_changeset（列级校验）
  └─④ apply_merge（落库）
```

**结果**：批号 BAT20260804001 一条；凭证号 FV202608040001/0002/0003 三张，各自连续。分录靠 `upper_id` 关联到对应凭证头，查 doc_no 走 join。

### A.4 字段名配置驱动

引擎只认 target.field（="doc_no"），不认识 doc_no 这个名字。换采购订单只需改 target.field="order_no"，引擎代码零改。

### A.5 分录表为何不存 doc_no（行业惯例）

五个厂商 DOC 定义的分录表都没冗余 doc_no：

| 厂商 | 头表（有 doc_no） | 分录表（无 doc_no） |
|---|---|---|
| cmxfico | cv_header | cv_acc_line, cv_aux_line, cv_cyzb_line |
| EBS | ebs_gl_je_header | ebs_gl_je_lines |
| SAP | sap_fi_document_header | sap_fi_document_item |
| 金蝶 | kd_gl_voucher_header | kd_gl_voucher_entry |
| 用友 | yy_gl_voucher_header | yy_gl_voucher_entry |

**原因**：分录靠 `upper_id` 外键关联头表，查 doc_no 走 `JOIN 头表`，物理冗余违反范式且更新不一致。引擎遵循此惯例：**默认不级联**；仅当业务确需冗余时显式配 `cascade`（§10.4）并先改定义给分录表加列。

### A.6 若确需分录冗余 doc_no（少数场景，可选）

1. **改定义加列**：cv_acc_line 的 `documentFieldSets` 加 `documentIdentityFields`（含 doc_no），重新 compile 建表加列
2. **配 cascade**：cv_header 的 codeRule 加 `"cascade": {"field":"doc_no", "scope":"children"}`
3. **引擎行为**：铸完每张头号后，沿 `relations`（`cv_header.id → cv_acc_line.upper_id`）把该头号写到对应分录的 doc_no（§10.4）

---

## 附录 B · 可视化配置（操作指南 + 前端实现）

> **本附录面向两类读者**：B.1-B.6 是**操作指南**（管理员怎么在网页上配规则、挂规则，零 JSON）；B.7-B.13 是**前端实现细节**（给开发看，对齐现有技术栈与页面风格，不引入新框架）。所有配置全程走 UI，不让用户手改 JSON。

### B.1 配置全景：两个入口 + 一条端到端流程

编码引擎的可视化配置由**两个网页入口**组成，分工明确：

| 入口 | 在哪 | 配什么 | 谁用 |
|---|---|---|---|
| **① 规则管理页** | 新 workspace view `code-rule-manager` | 「编码怎么生成」--段序列、连号、组织范围 | 实施顾问 / 高级管理员 |
| **② 定义管理器** | 现有 `portal-definition-manager` | 「规则挂到哪张表的哪个字段」--mode/field/ruleCode | 定义管理员 |

**端到端流程（一次完整配置的全过程，零 JSON）**：

```
┌─────────────────────────────────────────────────────────────────────┐
│ 步骤 1 · 实施顾问在【规则管理页】配「编码怎么生成」                     │
├─────────────────────────────────────────────────────────────────────┤
│  ① 左侧规则列表点「+ 新建规则」                                       │
│  ② 右侧属性区填：规则码 voucher_daily / 规则名「凭证日流水号」         │
│     / 勾选「连号补偿」                                                │
│  ③ 中间段序列区逐段添加：                                             │
│       [固定段] 值填 FV                                                │
│       [日期段] 格式选 YYYYMMDD                                        │
│       [流水段] 宽度填 4，重置依据选「按日」                            │
│  ④ 段序列下方实时预览：FV202608040001                                 │
│  ⑤ 点「保存」                                                        │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 步骤 2 · 定义管理员在【定义管理器】配「规则挂到哪」                     │
├─────────────────────────────────────────────────────────────────────┤
│  ① 打开凭证 DOC 定义，切到 cv_header 屝始化层                         │
│  ② 「本层表」卡片里：                                                │
│       编码字段填 doc_no   ← 叫什么都行，引擎只认这里填的               │
│       编码规则下拉选「自动生成」                                       │
│       规则码填 voucher_daily（步骤 1 建的那条）                        │
│       勾连号补偿                                                     │
│  ③ 保存定义                                                          │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 步骤 3 · 最终用户在【业务页面】用                                      │
├─────────────────────────────────────────────────────────────────────┤
│  ① 填凭证（doc_no 留空）                                              │
│  ② 点「预览编码」按钮 → 显示 FV202608040001（不占号）                  │
│  ③ 点「保存」→ 后端在保存事务内定稿铸号                                │
└─────────────────────────────────────────────────────────────────────┘
```

> **核心原则**：步骤 1 配「算法」，步骤 2 配「挂载点」，两者解耦。一条规则可挂多张表；一张表换规则只改步骤 2 的下拉。**全程不碰 JSON**。

---

### B.2 入口①规则管理页：配「编码怎么生成」

**页面布局**（三区，复用现有 `.list-region` / `.inspect-body` / `.section` 类名，视觉与定义管理器一致）：

```
┌─ explorer ──────┬─ content ────────────────────────────┬─ property ──┐
│ 规则列表         │ 段序列编辑（动态行）                    │ 规则属性     │
│ · supplier_hq   │ ┌──────────────────────────────────┐ │ 规则码*      │
│ · voucher_daily │ │ [固定段] 值: FV          [↑↓🗑]  │ │  voucher_.. │
│ · material_code │ │ [日期段] 格式: YYYYMMDD  [↑↓🗑]  │ │ 规则名       │
│ · org_code      │ │ [流水段] 宽度:4 重置:按日 [↑↓🗑] │ │  凭证日流水  │
│ [+ 新建规则]     │ │ [+ 添加段]                         │ │ 模式  auto  │
│                 │ │                                    │ │ 组织范围 全局│
│                 │ │ 预览：FV202608040001               │ │ 连号补偿 ☑  │
│                 │ │                                    │ │ 优先级  100 │
│                 │ └──────────────────────────────────┘ │ 生效日期     │
└─────────────────┴──────────────────────────────────────┴─────────────┘
```

**配一条规则的完整操作**：

1. **新建**：左侧「+ 新建规则」→ 右侧属性区填规则码（必填，全局唯一，如 `voucher_daily`）、规则名、选模式（manual/auto，默认 auto）
2. **加段**：中间段序列区点「+ 添加段」→ 弹下拉选段类型（7 选 1）→ 选定后该行展开该段的专属字段
3. **每段的专属输入**（按段类型自动切换表单）：

   | 段类型 | 表单字段 | 示例值 |
   |---|---|---|
   | 固定段 const | 值（文本框） | `FV` |
   | 流水段 serial | 宽度（数字框）/ 起始值 / 步长 / 重置依据（下拉：全局/按日/按分类/按组织） | 宽度 4，重置「按日」 |
   | 日期段 date | 格式（下拉：YYYYMMDD / YYMM / YYYYMM 等） | `YYYYMMDD` |
   | 日期流水 dateSerial | 日期格式 + 流水宽度 + 重置依据 | 同上两段合体 |
   | 引用段 ref | 字段名（下拉，来自目标表字段）/ 映射表（键值对）/ 取前 N 位 | 字段 `doc_type_code`，映射 `{SA:01, AR:02}` |
   | 随机段 random | 字符池（下拉：数字/小写/大写/混合）/ 长度 | 数字池，长度 4 |
   | 自定义 custom | 函数名（对接已注册的 `&dyn SegmentFn`） | `luhn_check` |

4. **排序**：每行右侧 ↑↓ 调整段顺序，🗑 删除该段
5. **预览**：段序列下方实时算出预览码（调 `/api/code/preview`，不占号），边配边看结果
6. **属性微调**：右侧属性区勾选连号补偿（连号域必勾）、组织范围（全局/指定组织码）、优先级（多条规则竞争时取大）、生效日期
7. **保存**：点「保存」→ 调 `/api/code/rules` POST/PUT，落 `cmx_code_rule` 表

**段序列动态行编辑**（前端实现细节见 B.11）。

---

### B.3 入口②定义管理器：配「规则挂到哪张表的哪个字段」

**在现有定义管理器里加 codeRule 编辑器**，分 DCT 和 DOC 两个挂载点：

**DCT 侧（字典，如供应商）**--在表信息区加一行：
```
表信息
├ 表名: cf_bus_partner
├ 编码字段: code          ← 下拉选本表字段（这就是「doc_no 不叫 doc_no」的可视化答案）
└ 编码规则: [自动生成 ▼]  ← 下拉：手动录入 / 自动生成
            └ 自动生成时展开：
                规则码: [voucher_daily____]   ← 下拉选已建规则（步骤 1 配的）
                连号补偿: ☐
                兜底正则(可选): [__________]
```

**DOC 侧（单据，如凭证头 cv_header）**--在层级信息区「本层表」的每张表卡片里加 codeRule 编辑器：
```
本层表（1）
┌ cv_header ────────────────────────┐
│ 中文名: 凭证头    物理表: cv_header │
│ 父表: (无)                         │
│ ───────────────────────────────── │
│ 编码字段: doc_no          ← 填什么引擎就查什么列
│ 编码规则: [自动生成 ▼]             │
│   规则码: [voucher_daily____]     ← 关联步骤 1 建的规则
│   连号补偿: ☑                      │
│   ▸ 高级（级联回填）   ← 默认折叠，多数场景不展开 │
└────────────────────────────────────┘
```

**高级·级联回填**（点「▸ 高级」展开，仅 DOC 父表可选配）：
```
┌ cv_header · 级联回填（§10.4，可选）──────────────────┐
│ ☑ 启用级联（铸完本表号后，沿父子关系回填到子表）       │
│ 回填字段: [doc_no ▼]   ← 选子表已有的字段              │
│ 回填范围: ●仅直接子表  ○全部后代                      │
│ ⚠ 子表必须已有该字段，否则引擎跳过（不报错）           │
│   （给分录表加列需改 documentFieldSets 重新 compile）  │
└──────────────────────────────────────────────────────┘
```

**操作要点**：

- **编码字段**是下拉框，选项来自当前表已声明的字段列表（DCT 从 fields，DOC 从字段集）--不允许手输不存在的列名，从源头杜绝 `target.field` 指错
- **编码规则**下拉只有两个选项：手动录入 / 自动生成；选自动生成才展开规则码下拉
- **规则码**下拉的数据源是规则管理页（入口①）建好的规则列表--两边通过 ruleCode 关联，不用记不用抄
- **mode 切换**：下拉一改，下方表单跟着重渲染（manual 显示正则框，auto 显示规则码框）--前端实现见 B.10
- **级联回填默认折叠**：多数场景不配（分录靠外键关联头表，查 doc_no 走 join）。只有业务确需子表物理冗余 doc_no 时才展开配，配前需先给子表加字段
- **多张表各配各的**：DOC 是多级树（批/头/分录），每张表卡片独立配 codeRule。凭证典型配置：批配 batch_daily、头配 voucher_daily、分录不配（§10.3 各自铸号，互不干扰）

**这就是回答「doc_no 不叫 doc_no 怎么办」的可视化答案**：在「编码字段」下拉里选实际字段名（如 `voucher_number`），引擎拿到 target.field 后全部动态拼装，零硬编码。

---

### B.4 业务页面预览（最终用户视角）

业务页面（html-pages，如凭证录入页）加一个「预览编码」按钮，给最终用户用：

```
┌─ 凭证录入页 ────────────────────────────────────┐
│ 凭证类型: [SA 销售凭证 ▼]    [💡 预览编码]       │
│ 凭证号:   FV202608040001  ← 预览后回填（只读）   │
│ ...                                             │
└─────────────────────────────────────────────────┘
```

- 点「预览编码」→ 调 `/api/code/preview`（不落库不占号）→ 回填到凭证号字段（只读）+ 弹通知「预览编码：FV202608040001（保存时定稿）」
- 点「保存」→ 后端在保存事务内定稿铸号（预览值可能与最终值不同，以最终为准）

前端实现见 B.12。

---

### B.5 六类配置场景速查（操作者照着做）

| 场景 | 步骤 1 规则管理页 | 步骤 2 定义管理器 | 预览结果 |
|---|---|---|---|
| **供应商编码**（手动） | 不用配规则 | 编码规则选「手动录入」，填正则 `^VRM\d{4}$` | 用户手输，保存时校验 |
| **物料编码**（自动，组织范围） | 新建 `material_code`：固定段 RM + 引用段 org_code + 流水段宽度 4 | 物料表编码规则选自动，规则码填 material_code | RM00100001 |
| **凭证号**（自动，连号域） | 新建 `voucher_daily`：固定 FV + 日期 + 流水宽度 4，勾连号补偿 | cv_header 编码规则选自动，规则码填 voucher_daily，勾连号补偿 | FV202608040001 |
| **凭证号按类型区分前缀** | 新建 `voucher_by_type`：引用段 doc_type_code 映射 {SA:01,AR:02} + 流水 | 同上，规则码换 voucher_by_type | 0126080400001 |
| **凭证批+凭证头**（多级各自铸号） | 新建 `batch_daily`（固定 BAT+日期+流水）+ `voucher_daily` 两条 | cv_batch 配 batch_daily；cv_header 配 voucher_daily；分录不配 | 批 BAT20260804001 / 头 FV202608040001 各自连续（§10.3） |
| **凭证头号→分录冗余**（少数反范式，可选） | 头规则同上 | cv_header 展开「高级·级联回填」，勾启用，回填字段选 doc_no，范围「仅直接子表」；先给 cv_acc_line 加 doc_no 列 | 头 FV202608040001 → 分录 doc_no 同值（§10.4） |

---

### B.6 可视化配置的边界（不做什么）

- ❌ **不让用户手改 JSON**--所有配置走 UI 编辑器（定义管理器 codeRule 编辑器 + 规则管理页）
- ❌ **不新增 cmx-* 自定义元素**--规则编辑器内联在 portal-definition-manager 里，不独立成 web component
- ❌ **不引入新框架/新依赖**--纯 ES 模板字符串 + 事件委托，与现有代码同款
- ✅ **段序列编辑复用 renderValidations 的"动态行表格"模式**--不造新交互范式
- ✅ **UI 控件全部复用现有类名体系**（.kv/.section/.lt-row/.chip）--视觉与定义管理器一致

---

## B.7-B.13 前端实现细节（给开发看）

> 以下小节是上述操作指南的技术实现，严格对齐 CMXPortalManager 现有技术栈：**不引入新框架**，命令式 innerHTML + data-action 路由 + .kv/.section/.lt-row 类名体系；规则管理页复用 portal-definition-manager 的组件注册模式（workspace view type）。

### B.7 技术栈对齐基线（勘探结论）

| 维度 | 现有技术栈 | 本方案对齐方式 |
|---|---|---|
| **门户壳/设计器** | CMXPortalManager：Lit3 + UI5 WebComponents + Vite8（`_render()` 方法） | 规则管理页复用同一组件注册模式（workspace view type） |
| **渲染机制** | 命令式 `this.shadowRoot.innerHTML = \`...\`` + escHtml/escAttr 转义（`_render()` 方法） | 规则编辑器走同款命令式 innerHTML |
| **CSS 注入** | 内联 `<style>` 标签 + `defBaseNeoStyleBlock(kind)`（`definition-helpers.js`） | 复用同一 CSS 注入机制，不引 adoptedStyleSheets |
| **类名体系** | `.kv` / `.section` / `.inspect-body` / `.insp-section` / `.box` / `.lt-row` / `.chip` / `.item-sub` | 规则编辑器复用这些类名，视觉一致 |
| **事件路由** | `data-action` / `data-table-prop` / `data-vt-prop` / `data-field-path` 属性委托（`_handleInput` 方法） | 规则编辑器走 `data-code-rule-prop` 同款属性委托 |
| **字段编辑面板** | schema 驱动：`cmx-field-schema.js` FIELD_SCHEMA + SECTIONS + `cmx-field-ui.js:renderFieldPanel` | 段编辑器复用 renderValidations/renderEnumValues 的"动态行表格"模式 |
| **业务页面** | 配置即页面：HTML 片段 + `__designer_meta__` JSON（pageFns/models/dataFlow） | 预览编码按钮走 pageFns 范式 |
| **组件库** | cmx-data-comp：原生 HTMLElement + 副作用 `customElements.define`（~89 个元素） | 不新增 cmx-* 元素；规则编辑器内联在 portal-definition-manager 里 |

### B.8 前端工作清单（4 项）

| # | 工作项 | 位置 | 阶段 |
|---|---|---|---|
| ① | **修复 codeRule 类型不一致 bug** | portal-definition-manager.js + relation-dict.js | C2 |
| ② | **DCT/DOC 表信息区加 codeRule 结构化编辑器** | portal-definition-manager.js `_renderDictMetaEditor` + DOC 层级信息区 | C2 |
| ③ | **独立规则管理页**（cmx_code_rule CRUD） | 新 workspace view type `code-rule-manager` | C2 |
| ④ | **业务页面"预览编码"按钮** | html-pages 的 pageFns + DOM 绑定 | C4 |

### B.9 ① 修复 codeRule 类型不一致 bug

**现状**（勘探发现的 bug）：
- 骨架默认值是空串 `codeRule: ''`（`_newDictEntry` 骨架构造 + `relation-dict.js` 骨架）
- 数据层是对象 `{mode,field,pattern,...}`（cmxfico_dct_meta_v3.json:4329）
- UI 两处当字符串处理：`val(meta.codeRule)` 显示 `[object Object]`（:2624）、`value: meta.codeRule \|\| ''` 当 text input（:2775）

**修复**：
```javascript
// 骨架默认值（_newDictEntry 骨架构造 + relation-dict.js 骨架）
// 改前：codeRule: ''
// 改后：
codeRule: { mode: 'manual', field: 'code' }

// DCT 表信息 rows（:2775）-- 归一为对象后取 pattern 供编辑
const _cr = (typeof meta.codeRule === 'object' && meta.codeRule) ? meta.codeRule : { mode: 'manual', field: meta.codeField || 'code' }
rows.push({ path: 'dictMeta.codeRule', label: '编码规则', type: 'coderule',
  value: _cr.pattern || '', mode: _cr.mode || 'manual', codeField: meta.codeField || 'code' })

// DOC 引用字典只读展示（:2624）-- 对象摘要
const codeRuleSummary = (cr) => {
  if (cr == null || cr === '') return '-'
  if (typeof cr === 'object') return [cr.mode, cr.pattern && `/${cr.pattern}/`, cr.ruleCode].filter(Boolean).join(' · ')
  return String(cr)
}
```

### B.10 ② DCT/DOC 表信息区 codeRule 结构化编辑器

> **操作流程见 B.3**（操作指南，含 DCT/DOC 两处挂载点的 UI 草图）。本节讲渲染/写回代码。

**渲染**（复用 `_renderDictMetaEditor` 的 row.type 分派模式）：

```javascript
// _renderDictMetaEditor 加 coderule type 分支
// row 多带两个字段：codeFieldOptions（本表字段下拉源）+ ctx（'dct'|'doc'）+ vtIndex（DOC 专用）
if (row.type === 'coderule') {
  const mode = row.mode || 'manual'
  const codeField = escAttr(row.codeField || 'code')
  const ctx = row.ctx || 'dct'                          // dct 走 data-table-prop，doc 走 data-vt-index
  const vtIdx = row.vtIndex != null ? `data-vt-index="${row.vtIndex}"` : ''
  const tblProp = ctx === 'dct' ? `data-table-prop="${path}"` : ''

  // ① 编码字段下拉（B.3 承诺的「doc_no 不叫 doc_no」可视化入口）
  //    选项来自本表已声明字段（DCT: fields；DOC: 字段集）--不允许手输，杜绝 target.field 指错
  const fieldOpts = (row.codeFieldOptions || ['code']).map(f =>
    `<option value="${escAttr(f)}" ${f===codeField?'selected':''}>${escHtml(f)}</option>`
  ).join('')
  let body = `<div class="cmx-cr-field"><label class="cmx-cr-inline">编码字段</label>
    <select data-coderule-field>${fieldOpts}</select></div>`

  // ② 模式下拉
  body += `<select data-coderule-mode>
    <option value="manual" ${mode==='manual'?'selected':''}>手动录入(校验正则)</option>
    <option value="auto" ${mode==='auto'?'selected':''}>自动生成(段引擎)</option>
  </select>`

  // ③ manual -> pattern 正则输入
  if (mode === 'manual') {
    body += `<input data-coderule-pattern placeholder="正则" value="${escAttr(row.value||'')}">`
  }
  // ④ auto -> ruleCode 下拉（数据源=规则管理页建的规则，走 /api/code/rules 拉列表）
  //         + enableGap 开关 + pattern 兜底校验（可选）
  if (mode === 'auto') {
    const ruleOpts = (row.ruleCodeOptions || []).map(r =>
      `<option value="${escAttr(r.ruleCode)}" ${r.ruleCode===row.ruleCode?'selected':''}>${escHtml(r.ruleName||r.ruleCode)}</option>`
    ).join('')
    body += `<select data-coderule-rulecode><option value="">(选规则)</option>${ruleOpts}</select>`
    body += `<label class="cmx-cr-inline"><input type="checkbox" data-coderule-enablegap ${row.enableGap?'checked':''}>连号补偿</label>`
    body += `<input data-coderule-pattern placeholder="兜底正则(可选)" value="${escAttr(row.value||'')}">`

    // ⑤ DOC + auto 才显示级联（cascade）高级配置（§10.4，默认折叠）
    //    子表字段下拉源：本表子表的字段并集（从 voucherSchema.relations 推导子表，取其 fields）
    if (ctx === 'doc') {
      const cas = row.cascade || {}
      const childFieldOpts = (row.cascadeFieldOptions || []).map(f =>
        `<option value="${escAttr(f)}" ${f===cas.field?'selected':''}>${escHtml(f)}</option>`
      ).join('')
      body += `<details class="cmx-cr-cascade"><summary>高级·级联回填（可选）</summary>
        <label class="cmx-cr-inline"><input type="checkbox" data-coderule-cascade-enable ${cas.field?'checked':''}>启用级联</label>
        <label class="cmx-cr-inline">回填字段 <select data-coderule-cascade-field>${childFieldOpts}</select></label>
        <label class="cmx-cr-inline">范围
          <select data-coderule-cascade-scope>
            <option value="children" ${cas.scope!=='descendants'?'selected':''}>仅直接子表（默认）</option>
            <option value="descendants" ${cas.scope==='descendants'?'selected':''}>全部后代</option>
          </select>
        </label>
        <div class="item-sub">铸完本表号后，沿父子关系回填到子表。子表必须已有该字段，否则引擎跳过。</div>
      </details>`
    }
  }

  return `<label>${label}</label><div class="cmx-coderule-edit" ${tblProp} ${vtIdx} data-ctx="${ctx}" data-cur-mode="${mode}">${body}</div>`
}
```

**写回**（`_handleInput` 的 coderule 分支，复用 `_updateTableProp` 的 data-table-prop 路由 + `_updateVoucherTable` 的 data-vt-prop 路由）：

```javascript
// codeRule 结构化编辑：组装对象写回
if (el.closest('.cmx-coderule-edit')) {
  const wrap = el.closest('.cmx-coderule-edit')
  const ctx = wrap.dataset.ctx || 'dct'
  const codeField = wrap.querySelector('[data-coderule-field]')?.value || 'code'
  const mode = wrap.querySelector('[data-coderule-mode]')?.value || 'manual'
  const rule = { mode, field: codeField }
  if (mode === 'manual') {
    const pattern = wrap.querySelector('[data-coderule-pattern]')?.value || ''
    if (pattern) rule.pattern = pattern
  }
  if (mode === 'auto') {
    const ruleCode = wrap.querySelector('[data-coderule-rulecode]')?.value?.trim() || ''
    if (ruleCode) rule.ruleCode = ruleCode
    const enableGap = wrap.querySelector('[data-coderule-enablegap]')?.checked
    if (enableGap) rule.enableGap = true
    const pattern = wrap.querySelector('[data-coderule-pattern]')?.value || ''
    if (pattern) rule.pattern = pattern
    // 级联回填（仅 DOC，§10.4）--勾选启用且选了回填字段才组装
    const cascadeEnable = wrap.querySelector('[data-coderule-cascade-enable]')?.checked
    if (ctx === 'doc' && cascadeEnable) {
      const casField = wrap.querySelector('[data-coderule-cascade-field]')?.value
      if (casField) {
        rule.cascade = {
          field: casField,
          scope: wrap.querySelector('[data-coderule-cascade-scope]')?.value || 'children'
        }
      }
    }
  }
  // DCT 模式 -> _updateTableProp
  if (ctx === 'dct' && wrap.dataset.tableProp) {
    this._updateTableProp(wrap.dataset.tableProp, rule, 'coderule')
  }
  // DOC 模式 -> _updateVoucherTable 的 else 分支（tbl[prop]=value）
  if (ctx === 'doc' && wrap.dataset.vtIndex != null) {
    this._updateVoucherTable(Number(wrap.dataset.vtIndex), 'codeRule', rule)
  }
  // mode 切换重渲染（manual<->auto 表单不同）
  if (mode !== wrap.dataset.curMode) { wrap.dataset.curMode = mode; this._render() }
  // 编码字段切换不重渲染，只更新 data-code-field（避免丢其他输入焦点）
}
```

**DOC 侧挂载位置**：层级信息区「本层表」的每张表卡片（`_render()` 的 DOC 层级信息分支，`<div class="lt-meta">` 上方），插一行 codeRule 编辑器，`ctx='doc'` + `vtIndex=x.gIndex`，字段下拉源取 `x.table.fields`。

**ruleCode 下拉数据源**：组件首次渲染时（或 codeRule 编辑器获得焦点时）调一次 `GET /api/code/rules?fields=ruleCode,ruleName`（§11 API），结果缓存到组件实例，供所有 codeRule 编辑器复用。

**CSS**（内联 `<style>` 加几行，复用 .kv/.lt-row 风格）：

```css
.cmx-coderule-edit{display:flex;flex-wrap:wrap;align-items:center;gap:4px}
.cmx-coderule-edit>select{flex:0 0 auto;min-width:120px}
.cmx-coderule-edit>input{flex:1 1 120px;min-width:80px}
.cmx-cr-field{display:flex;align-items:center;gap:4px;width:100%;margin-bottom:2px}
.cmx-cr-field>select{flex:1 1 160px}
.cm-cr-inline{display:inline-flex;align-items:center;gap:3px;font-size:11px;white-space:nowrap;color:var(--sapContent_LabelColor,#6a6d70)}
.cmx-cr-cascade{width:100%;margin-top:4px;padding:6px 8px;border:1px dashed var(--sapNeutralBorder,#d9d9d9);border-radius:4px}
.cmx-cr-cascade>summary{font-size:11px;color:var(--sapContent_LabelColor,#6a6d70);cursor:pointer;list-style:revert}
.cmx-cr-cascade[open]>summary{margin-bottom:4px}
```

### B.11 ③ 独立规则管理页（C2 阶段，实现侧）

> **页面布局与操作流程见 B.2**（操作指南）。本节只讲技术实现。

**注册方式**：新 workspace view type `code-rule-manager`，照搬 portal-definition-manager 的注册模式（registerWorkspaceViewType）。

**三区结构**：explorer（规则列表）/ content（段序列编辑）/ property（规则属性），全部复用 `.list-region` / `.inspect-body` / `.section` 现有类名。

**段序列动态行编辑**（复用 `cmx-field-ui.js` 的 `renderValidations` 动态行表格模式）：

```javascript
// 每段一行：type 下拉 + 该 type 专属字段输入 + 排序/删除按钮
function renderSegments(segments) {
  return segments.map((seg, i) => `<div class="seg-row">
    <select data-seg-type data-seg-idx="${i}">
      <option value="const" ${seg.type==='const'?'selected':''}>固定段</option>
      <option value="serial" ${seg.type==='serial'?'selected':''}>流水段</option>
      <option value="date" ${seg.type==='date'?'selected':''}>日期段</option>
      <option value="dateSerial" ${seg.type==='dateSerial'?'selected':''}>日期流水</option>
      <option value="ref" ${seg.type==='ref'?'selected':''}>引用段</option>
      <option value="random" ${seg.type==='random'?'selected':''}>随机段</option>
      <option value="custom" ${seg.type==='custom'?'selected':''}>自定义</option>
    </select>
    ${renderSegFields(seg, i)}  <!-- 按 type 渲染专属字段 -->
    <button data-action="seg-up" data-seg-idx="${i}">↑</button>
    <button data-action="seg-down" data-seg-idx="${i}">↓</button>
    <button data-action="seg-del" data-seg-idx="${i}">🗑</button>
  </div>`).join('') + `<button data-action="seg-add">+ 添加段</button>`
}
```

**数据源**：调 `/api/code/rules` CRUD（§11 API），走 `host.fetch` 或全局 fetch（与 cmx-doc-source 同款取数方式）。

### B.12 ④ 业务页面"预览编码"按钮（C4 阶段）

在 html-pages 的 `__designer_meta__` 里加 pageFns，DOM 加一个预览按钮：

```html
<!-- HTML 片段里加预览按钮（复用 ui5-button 风格） -->
<ui5-button design="Transparent" icon="hint" data-eventclick="previewCode();">预览编码</ui5-button>
<!-- doc_no 字段设为只读（预览值由后端返回，用户不能改） -->
```

```javascript
// pageFns 加 previewCode（走 /api/code/preview，不落库不占号）
{
  "name": "previewCode",
  "body": "var ms = host.ms;\n\
var row = ms.getRow('cv_header', 0);\n\
if (!row) { host._cmxNotify('warn','请先填写凭证头'); return; }\n\
fetch('/api/code/preview', {\n\
  method: 'POST',\n\
  headers: {'Content-Type':'application/json'},\n\
  body: JSON.stringify({\n\
    target: {kind:'doc', code:'cv_header', field:'doc_no'},\n\
    attrs: row\n\
  })\n\
}).then(r=>r.json()).then(j=>{\n\
  if (j.code===0 && j.data.code) {\n\
    row.doc_no = j.data.code;\n\
    host._cmxNotify('ok','预览编码：'+j.data.code+'（保存时定稿）');\n\
  } else { host._cmxNotify('error','预览失败：'+(j.message||'未知错误')); }\n\
});"
}
```

**风格对齐**：
- 按钮用 `<ui5-button>`（与现有 voucher-list.html:4 的 ui5-button 一致）
- 通知用 `host._cmxNotify`（与 voucher-list.html initPage 的 cmxInfo/cmxWarn/cmxError 一致）
- fetch 走全局 `fetch`（与 cmx-doc-source 的 `_fetch` 一致）

### B.13 不做什么（前端边界，与 B.6 操作视角呼应）

- ❌ **不新增 cmx-* 自定义元素**--规则编辑器内联在 portal-definition-manager 里，不独立成 web component
- ❌ **不引入新框架/新依赖**--纯 ES 模板字符串 + 事件委托，与现有代码同款
- ❌ **不让用户手改 JSON**--所有配置走 UI 编辑器（表信息区 codeRule 编辑器 + 独立规则管理页）
- ✅ **segments 段序列编辑复用 renderValidations 的"动态行表格"模式**--不造新交互范式

---

## 附录 C · 实现现状与设计偏差（落地须知）

> 本附录记录截至 2026-08-05 的 cmx-code 实现状态，列出**与设计文档的偏差**和**未接线的功能**。落地后续阶段（C3-C6）时必须逐项处理。本附录随实现进展更新，是「设计 vs 实现」的对账单。

### C.1 已落地（与设计一致）

| 能力 | 位置 | 状态 |
|---|---|---|
| 七种段类型（const/serial/date/dateSerial/ref/random/custom） | cmx-code-model/src/segments/ | ✅ 全部实现 |
| 段求值 trait（SegmentResolver + SegmentValue 三态） | cmx-code-model/src/segments/mod.rs | ✅ |
| 反查 max 算法（单条 SQL + minted_buffer 注入） | cmx-code-api/src/store/serial_pg.rs | ✅ §4.1 |
| 独立规则库表 cmx_code_rule + CRUD API | cmx-code-api/src/store/rule_store.rs + handlers.rs | ✅ §3.2 |
| RuleSpec / CodeRule / Target / Cascade 类型定义 | cmx-code-model/src/spec.rs | ✅ |
| 补位 padChar/padSide + 步长 step + 起始值 start | cmx-code-model/src/pad.rs + spec.rs | ✅ §09（serial/dateSerial/ref 段接线） |
| ref 段 map/take/fallback/pad | cmx-code-model/src/segments/ref.rs | ✅ §2.1 |
| rule_algo 段序列求值 + UNIQUE 重试循环（8 次） | cmx-code-model/src/rule_algo.rs | ✅ §4.4（但 try_insert 见 C.2.2） |
| 两段式 crate（model + api）+ web-server merge | cmx-code-api/src/routes.rs | ✅ §13 |
| preview / generate / validate API | cmx-code-api/src/handlers.rs | ✅ §11 |
| 规则管理页（三区 workspace view） + 定义管理器 codeRule 编辑器 | CMXPortalManager/src/components/ | ✅ 附录 B |
| DAM 隔离（domain/application/module）+ db_id 兜底 | handlers.rs `db_id_from` + `dam_from` | ✅ §3.5 |
| CodeMinter trait 接入（cmx-traits） | cmx-code-api/src/engine.rs `mint_via_minter` | ✅ |

### C.2 已知偏差与缺陷（按严重度）

#### 🟢 C.2.1 resetBy 已修复（2026-08-05，原 P0）

**原问题**：`rule_algo.rs` 把 serial 段求出的 `reset_key` 直接 `reset_key: _` 丢弃；反查 max 不按 reset 维度分组。

**修复**：采用 §4.8.1 路径 A —— `resolve_fixed_segments` 和 `evaluate_segments` 求前缀时，把 serial/dateSerial 段的 `reset_key`（非 `_global_` 占位）拼进 prefix。反查 max 的 `WHERE code LIKE '{prefix_with_reset_key}%'` 天然按 reset 维度分组。

**验证**：新增 4 个单测（`test_resolve_fixed_segments_with_reset_key` / `_global_serial` / `_reset_by_field` / `test_evaluate_date_serial`）覆盖 dateSerial 日期进 prefix、全局 serial 不污染、字段名 resetBy、完整 dateSerial 铸号。全过。

#### 🟢 C.2.2 try_insert 责任边界明确化（原 P0，降级为设计说明）

**原描述**：try_insert 恒返回 Ok，UNIQUE 重试循环空转。

**澄清**：经审查，这是**有意的设计决策，非 bug**。铸号阶段（`evaluate_segments`）发生在 saver 的 apply_merge 之前，只算号写回 changeset，不落库。真正的 INSERT 由 saver 完成，UNIQUE 约束在 saver 落库时兜底；若冲突，saver 重新调 mint 取下一号（C3 钩子接入后）。

**已做**：`serial_pg.rs` / `advance.rs` 的 try_insert 注释改清楚，明确「铸号函数只算号不落库，UNIQUE 重试责任在 saver 层」。附录 C.2.2 从「待修 bug」改为「设计说明」。未来若需铸号阶段预检（SELECT EXISTS），在此实现返回 Err 触发重试。

#### 🟢 C.2.3 mint_batch 已修复（2026-08-05，原 P1）

**原问题**：忽略 step / 不调 try_insert / 用 `format!` 绕过 padChar+padSide。

**算法层修复**：`engine.rs::mint_batch` 复用 `rule_algo::next_after`（含 step）+ `pad::format_serial`（含 padChar/padSide）+ `resolve_fixed_segments`（含 reset_key）。与单条铸号 `evaluate_segments` 语义统一。

**调用层修复（C.2.11 已接通）**：`CodeEngine::mint_batch` trait 实现走 `mint_via_minter_batch`（prefix 分组 + buffer 推进），DOC/DCT 钩子改调 `minter.mint_batch`。

**说明**：mint_batch 不调 try_insert，与 §4.5「整批 INSERT 冲突重试」设计有差异 —— 但本引擎的 UNIQUE 兜底统一由 saver 负责（见 C.2.2），mint_batch 只负责「算出一批号」，落库冲突由 saver 处理。与单条路径责任边界一致。

#### 🟢 C.2.4 preview 已修复（2026-08-05，原 P1）

**原问题**：`preview` 用 `format!("{next:0width$}")` 补 0，忽略 step / padChar / padSide，与定稿不一致。

**修复**：`engine.rs::preview` 复用 `next_after` + `format_serial` + `resolve_fixed_segments`（含 reset_key）。预览码 = 定稿码（相同 prefix + 相同补位 + 相同 step 推进），唯一差异是 preview 不调 try_insert（不占号）。

#### 🟢 C.2.5 mint_random_code 已修复（2026-08-05，原 P1）

**原问题**：冲突后重试用同一 candidate 字符串，没换种子。

**修复**：`rule_algo.rs::mint_random_code` 重构 —— 接收 `random_segs: &[SegmentSpec]`，每次重试循环内重新 `registry.resolve(seg)` 生成新随机候选（换种子）。16 次重试全用新种子。

#### 🟢 C.2.6 truncate 已接线（2026-08-05，原 P3）

**原问题**：`pad.rs` 实现了 truncate(none/right)，但无任何段调用；SegmentSpec 无 `truncate()` 取值方法。

**修复**：
1. `spec.rs` 加 `truncate_mode()`（默认 `"none"`）+ `truncate_width()`（取 `width` 或 `take`）取值方法
2. `ref.rs` resolve 末尾接 `pad::truncate(&value, tw, mode)` —— ref 段最可能超长（取字段值可能很长），超长时 `right`=右截断 / `none`=报错
3. serial/dateSerial 不接 truncate —— 流水段补位后长度恒等于 width（format_serial 保证），不会超长

**说明**：truncate 配合 pad 使用——pad 补短，truncate 截长，两者正交。

#### 🟢 C.2.7 preview_batch / generate_batch 已实现（2026-08-05，原 P3）

**原问题**：返回「待 C4 实现」空 stub。

**修复**：`handlers.rs` 新增 `BatchBody { target, rows, rule_code }`，`preview_batch` / `generate_batch` 构造 `CodeEngine` 实例调 `mint_batch` trait 方法（走 `mint_via_minter_batch`：prefix 分组 + buffer 推进）。两者语义一致（都只算号不落库，落库由 saver 负责）。

#### 🟢 C.2.8 condition/orgScope 已对齐文档（2026-08-05，原 P2）

**原偏差**：orgScope 只支持单字符串；condition 是字符串 `== / !=`；cond_matches 未知表达式默认 true（安全隐患）。

**修复**：
1. **orgScope 多组织**：`org_matches` 支持逗号分隔多组织（`"EAST,WEST"` → 任一精确匹配，方案 §3.4.1 数组的字符串编码形式）
2. **condition JSON 算子**：`cond_matches` 优先尝试 JSON 解析，支持白名单算子 `eq/ne/in/exists/and/or/not`（方案 §3.4.2）；解析失败回退字符串 `field==value` 兼容
3. **严格模式**：未知算子/不识别表达式判 **false**（修复原默认 true 的安全隐患）
4. **priority updated_at 兜底**：暂未实现（RuleSpec 无 updated_at 字段，需改表结构），priority 相同取候选列表第一个（稳定）

**验证**：新增 5 个单测（JSON eq/in/and/未知算子严格 false + 多组织匹配）全过。

#### 🟢 C.2.9 ref 段 refField 已实现（2026-08-05，原 P2）

**原问题**：§12.4 示例用 `{"type":"ref","field":"parent_id","refField":"code"}`，但 ref.rs 只读 field 不读 refField。

**修复**：ref 段 resolve 时，**优先**从 attrs 取 `refField` 名的字段值，取不到回退取 `field`。约定：钩子层把父记录的目标字段值以 `refField` 名塞进 attrs（如父记录的 code → `attrs["code"]`）。

**语义**：`{"field":"parent_id","refField":"code"}` → 优先取 `attrs["code"]`（父记录 code），无则取 `attrs["parent_id"]`（父 id）。model 层不查 DB，只从 attrs 取值——跨表查询由钩子层预解析。

**说明**：§12.4 的 refField 标注已移除（实现已支持）。

#### 🟢 C.2.10 minted_buffer 生产路径推进已修复（2026-08-05，原 P0）

**原问题**：DOC/DCT 钩子逐行调 `minter.mint`，每次新建空 `ResolveContext`，buffer 推进机制失效。同事务多行铸号会读到同一 max。

**修复**：
1. **engine.rs** 新增 `mint_via_minter_batch` 内部函数——反序列化 + 查规则表一次，按 prefix 分组，同 prefix 组调 `engine::mint_batch` 一次取连续号（buffer union 已铸号，保证不重）。
2. **engine.rs** `mint_batch` 的 `query_max_serial` 改为尊重 `ctx.minted_buffer()`（原写死空 `&[]`）。
3. **saver.rs** `mint_codes_for_changeset` + **write.rs** `mint_codes_for_inserts` 从逐行调 `minter.mint` 改为收集待铸号行后调 `minter.mint_batch`。

**验证**：cargo check 全 workspace 通过（零警告）；cmx-code 16 + cmx-doc-store-pg 42 + cmx-dct-store-pg 20 = 78 单测全过，零回归。

#### 🟢 C.2.11 mint_batch 调用链已接通（2026-08-05，原 P1）

**原问题**：`engine::mint_batch` 算法已修（C.2.3），但 trait 实现 `CodeEngine::mint_batch` 走循环单条，且无调用者。

**修复**：`CodeEngine::mint_batch` trait 实现改为调 `mint_via_minter_batch`（真正的批量取号 + prefix 分组 + buffer 推进）。DOC/DCT 钩子改调 `minter.mint_batch`，§4.5「批量取号一次查 max」优化生效。

**prefix 分组设计**：不同行的 attrs 可能不同（ref 段取不同值 → 不同 prefix），批量取号要求同 prefix 才能取连续号段。`mint_via_minter_batch` 先按 prefix 分组，同 prefix 组批量取号，不同 prefix 各自独立取号——边界 case 正确处理。

#### 🟡 C.2.12 record_gap 待 C6 接线（P2，延后）

**现状**：`gap_store.rs` 的 `record_gap` 函数已实现（独立连接，不走业务事务，符合 §5.3.1 解法 A），但**无调用者**。断号补偿只有「取」（take_gap 已接 `serial_pg.rs`），没有「记」。

**延后原因**：record_gap 的接入点在 saver 的 **conflict/回滚路径**——需要 saver 检测到「编码列 UNIQUE 冲突」时调 record_gap 记断号。当前 saver 的 conflict 处理走 ON CONFLICT DO NOTHING/UPDATE，不区分「编码冲突」和「其他唯一约束冲突」。完整接线需要 saver conflict 路径重构，属于 C6 阶段（断号补偿）专项工作。

**当前影响**：enable_gap=true 的连号域，断号表永远空，take_gap 永远返回 None（走反查 max）。连号域的断号补偿功能待 C6 完成。

#### 🟡 C.2.13 excludeAmbiguous 已修 / unique_check 待 C3（2026-08-05）

**excludeAmbiguous 已修复**：`random.rs::charset_pool` 重写——
- 过滤字符补全 9 个：`0/O/1/I/l/Z/2/B/8`（方案 §6.2 全部易混淆字符）
- `digit` / `hex` 池**不再过滤**（纯数字/16 进制无字母歧义，过滤会删 0/2 导致池缺失）
- 用户自定义字符串（other）不过滤（尊重用户输入）
- `alpha` / `alnum` / `custom` 按需过滤

**unique_check 待 C3**：`CodeRule.unique_check` 字段已定义（spec.rs），但 manual 模式的查重逻辑未接线。当前铸号钩子只处理 auto（manual 跳过）。unique_check=true 时需在 manual 落库前做 SELECT EXISTS 查重——涉及 saver/write 钩子的 manual 分支改造，属于 C3 阶段（DCT/DOC 集成深化）。当前 auto 模式靠 saver UNIQUE 兜底，manual 模式无查重。

### C.3 文档已补、实现跟进状态（2026-08-05 更新）

| 契约 | 文档位置 | 实现状态 |
|---|---|---|
| 按属性区分前缀 = ref+map（非 const） | §2.4 | ✅ ref 段已支持 |
| orgScope 匹配 | §3.4.1 | ✅ 已实现（单字符串精确 + 逗号分隔多组织，C.2.8） |
| condition 表达式 | §3.4.2 | ✅ 已实现（JSON 算子 + 字符串兼容回退，C.2.8） |
| priority 选优 | §3.4.3 | 🟡 max_by_key 已实现；updated_at 兜底未实现 |
| DAM 三场景（管理页带 / 挂规则不带 / 铸号默认） | §3.5 | ✅ 已实现 |
| db_id 解析链（header → biz → default） | §3.5 | ✅ 已实现 |
| pattern manual/auto 双语义 | §3.6 | ✅ auto 模式 pattern 可选 |
| resetBy reset_key 进 WHERE（路径 A） | §4.8.1 | ✅ 已修复（C.2.1） |
| dateSerial 日期进 prefix | §4.8.2 | ✅ 已修复（C.2.1） |
| 断号记录事务陷阱（独立事务 / SAVEPOINT） | §5.3.1 | ❌ 待实现（C6 阶段） |
| 断号场景 ④（并发冲突）不记 | §5.3.2 | ❌ 待实现（C6 阶段） |
| ref 段 refField（取父记录字段） | §12.4 | ✅ 已实现（C.2.9），ref 段优先取 refField 名的 attrs 值 |
| minted_buffer 生产路径推进 | §4.1/§10.3 | ✅ 已修复（C.2.10），钩子改调 mint_batch + engine 内 prefix 分组 |
| mint_batch 批量取号调用链 | §4.5 | ✅ 已修复（C.2.11），trait 实现走 mint_via_minter_batch |
| record_gap 断号记录调用链 | §5.3 | 🟡 函数已实现，接入点待 C6 saver conflict 重构（C.2.12） |
| unique_check 查重 | §3.3 | 🟡 字段已定义，manual 查重待 C3 钩子深化（C.2.13） |
| excludeAmbiguous 字符过滤 | §6.2 | ✅ 已修复（C.2.13），补全 9 字符 + digit/hex 不过滤 |
| truncate 接线 | §09 | ✅ 已修复（C.2.6），ref 段接 pad::truncate |
| preview_batch / generate_batch | §11 | ✅ 已实现（C.2.7），调 mint_batch |

### C.4 落地优先级建议（2026-08-05 全量审查后更新）

1. ~~**P0（铸号正确性·第一批）**：C.2.1 resetBy 接线 + C.2.2 try_insert 责任边界~~ → ✅ 已完成
2. ~~**P1（一致性·第一批）**：C.2.4 preview + C.2.5 random 重试~~ → ✅ 已完成
3. ~~**P0（铸号正确性·第二批，全量审查新发现）**：C.2.10 minted_buffer 生产路径推进~~ → ✅ 已完成（钩子改调 mint_batch + engine 内 prefix 分组 + buffer union）
4. ~~**P1（调用链对齐，全量审查新发现）**：C.2.11 mint_batch 调用链~~ → ✅ 已完成（trait 实现走 mint_via_minter_batch，§4.5 批量取号优化生效）
5. **P1（一致性·第一批）**：~~C.2.3 mint_batch 算法~~ → ✅ 已完成（算法 + 调用链都通了，配合 C.2.11）
6. ~~**P2（多规则选优）**：C.2.8 condition/orgScope + C.2.9 refField~~ → ✅ 已完成（JSON 算子 + 多组织 + refField 全实现）
7. **P2（断号补偿接线）**：C.2.12 record_gap → 函数已实现，接入点待 C6 saver conflict 重构（连号域才需要）
8. ~~**P3（收尾）**：C.2.6 truncate + C.2.7 批量 stub + C.2.13 excludeAmbiguous~~ → ✅ 已完成（truncate 接线 + batch 实现 + 过滤补全）
9. **P3（延后）**：C.2.13 unique_check → 字段已定义，manual 查重待 C3 saver 钩子深化

---

**方案结束（V2 最终版）。** 只出方案不落地代码。实现按 C0->C1->C2->C3->C4->C5->C6 顺序推进，每期独立可验收。附录 C 随实现进展同步更新。
