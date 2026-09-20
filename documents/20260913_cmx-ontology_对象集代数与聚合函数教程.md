# 本体平台对象集代数与聚合函数教程

> 对标 Palantir **Object Set Service**：一次查询 = 一棵对象集代数树，由存储层编译为**一条** SQL（含 JOIN/子查询，无 N+1）；过滤谓词为**类型化表示**，不接受裸 SQL（防注入）。全部示例在演示数据基线（v6：7 主数据类型 / 6 条 FK 关系）上**实测通过**。
>
> **2026-09-20 复核更新**：按最新代码全量复测并修订——① 函数求值路由已去路径化（`POST /functions/evaluate`，`apiName` 入 body，20260919 接口整改）；② 全部接口 `?ontology=<本体 apiName>` **必填**（缺省 400 ONTOLOGY_REQUIRED，多本体改造）；③ `object-sets/load|aggregate` 请求体新增 `view`（场景口径）与 `include`（类型状态分层）可选字段；④ 新增虚拟直查类型读取（§2.7，20260918 方案）；⑤ 文中数值即 2026-09-20 当前库实况（与 v6 基线大体同源，仅个别行数因后续测试数据有出入，如 Supplier 13→14）。

## 一、30 秒上手：以「按供应商汇总合同额」为例

聚合函数 `contractSpendBySupplier`（groupSum）吃一个**对象集**入参。求值接口把「算哪些对象」和「怎么汇总」分成两段：

```bash
curl -s -X POST -H 'X-API-Key: cmx_sk_dev_A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6' \
  -H 'Content-Type: application/json' \
  'http://127.0.0.1:8097/api/onto/v1/functions/evaluate?ontology=default_ontology' \
  -d '{
    "apiName": "contractSpendBySupplier",
    "objectSet": { "op": "base", "objectType": "Contract" },
    "aggregation": { "kind": "groupSum", "groupBy": "supplierName", "sum": "amount" }
  }'
```

```json
// 实测结果
{ "code": 0, "data": { "function": "contractSpendBySupplier", "kind": "aggregation",
  "result": { "groups": [
    { "group": "中信重工机械股份有限公司", "sum": "1200000.00" },
    { "group": "华胜信息技术有限公司",     "sum": "760000.00" },
    { "group": "晨光办公用品股份有限公司", "sum": "580000.00" }
  ]}}}
```

- `objectSet`：**算哪些对象**。`op: "base"` = 某类型全量，这里即全部 3 份合同。
- `aggregation`：**怎么汇总**。`groupSum` 分组求和——按 `supplierName` 分组、组内对 `amount` 求和。
- 等价 SQL：`SELECT supplier_name, SUM(amount) FROM cm_contract GROUP BY supplier_name;`

把 `objectSet` 换成关系钻取版（先沿「签订合同」关系钻取再聚合）：

```json
{
  "objectSet": {
    "op": "searchAround",
    "source": { "op": "static", "objectType": "Supplier", "primaryKeys": ["SUP0001"] },
    "link": "signContract",
    "direction": "forward"
  },
  "aggregation": { "kind": "groupSum", "groupBy": "supplierName", "sum": "amount" }
}
// 实测（20260920）：中信重工机械股份有限公司 → 1200000.00（SUP0001 只签了 CT-2026-001）
// 注意：换路由后函数名走 body 的 apiName 字段（evaluate 请求体首字段），不再拼进 URL
```

字段解读：

| 字段 | 含义 |
|---|---|
| `source` | 钻取起点（这里是手工钉死的 SUP0001，见 `static`） |
| `op: "searchAround"` | 从起点沿一条**关系**走一步，邻居对象即结果集 |
| `link` | 走哪条关系类型（signContract：Supplier A 端 → Contract B 端，backing 外键 `Contract.supplierId = Supplier.id`） |
| `direction` | `forward` = 沿 A→B 正向走；`reverse` = 沿 B→A 反向走。**方向由起点对象在关系里的 A/B 端序决定，与外键存在哪端（side）无关** |

**核心思想**：`aggregation` 不用改，换 `objectSet` 就换了统计口径——范围可以是全量、过滤结果、多跳钻取、集合运算的任意组合。

> **两个请求硬约束（20260920）**：① 所有接口必须带 `?ontology=<本体 apiName>`，缺省报 400 `ONTOLOGY_REQUIRED`；② 函数求值走 `POST /functions/evaluate`，`apiName` 是 body 首字段（路由已禁可变路径段，老路径 `/functions/{apiName}/evaluate` 已不存在）。

## 二、对象集代数：7 种操作（`op`）

真源：`backend/cmx-ontology/crates/cmx-onto-model/src/objectset.rs`（`enum ObjectSet`，`serde(tag = "op")`，字段 camelCase）。

| op | 字段 | 语义 |
|---|---|---|
| `base` | `objectType` | 某对象类型的**全量** |
| `static` | `objectType`, `primaryKeys[]` | 手工指定的主键列表（pk 是各类型 `primaryKey` 属性的**值**：Supplier→SUP0001，Contract→CT-2026-001，Currency→CNY） |
| `filter` | `source`, `predicate` | 对子集做谓词过滤（谓词树见 §三） |
| `searchAround` | `source`, `link`, `direction`（缺省 `forward`） | ★关系遍历：从源对象集沿关系走到另一端 |
| `union` | `left`, `right` | 并集（按 pk 去重） |
| `intersect` | `left`, `right` | 交集（按 pk） |
| `subtract` | `left`, `right` | 差集（左 − 右） |

除 `base`/`static` 外，每个 op 都吃**子对象集**——所以可任意递归嵌套。

### 2.1 base + 分页

```bash
curl -s -X POST -H "$AK" -H 'Content-Type: application/json' \
  'http://127.0.0.1:8097/api/onto/v1/object-sets/load?ontology=default_ontology' \
  -d '{"objectSet":{"op":"base","objectType":"Supplier"},"limit":3,"offset":3}'
```

```json
{ "code":0, "data": { "objectType":"Supplier",
  "rows":[{"pk":"SUP0006","title":"…","properties":{…}}, …],
  "limit":3, "offset":3, "hasMore":true }}
// 实测（20260920）本页 pk：SUP0006 / SUP0003 / SUP0010（首批有后续测试造的 SUP202609130001 顶在第一页）
```

- load 信封：`{ objectSet, limit?, offset?, subjects?, view?, include? }`（`limit` 缺省 100；`subjects` 为读侧权限主体覆盖，一般不传；`view` = 场景可见性口径，值场景 apiName 或 `auto:<域>`，校验规则见 §七坑 9；`include` 类型状态分层，值 `all` 或 `experimental,deprecated` 逗号组合——非 active 类型默认按 404 隐藏）
- 响应 `data`：`objectType`（类型提示）+ `rows[]`（每行 `pk`/`title`/`properties`）+ `hasMore`（本页满即 true，可翻下页）

### 2.2 static：钉死对象

```json
{ "op": "static", "objectType": "Contract", "primaryKeys": ["CT-2026-001", "CT-2026-003"] }
```

### 2.3 filter：谓词过滤

```json
{ "op": "filter",
  "source": { "op": "base", "objectType": "Supplier" },
  "predicate": { "kind": "eq", "property": "riskLevel", "value": "低" } }
// 实测（20260920）：11 个供应商（riskLevel 是 MDM 枚举标签口径「低」）
```

### 2.4 searchAround：关系遍历（本体灵魂）

```json
{ "op": "searchAround",
  "source": { "op": "static", "objectType": "Employee", "primaryKeys": ["EMP0001"] },
  "link": "managerOf",
  "direction": "forward" }
// 实测（20260920）：EMP0001（王建国）主管的仓库 → WH-01
```

反向版（从 B 端出发）：

```json
{ "op": "searchAround",
  "source": { "op": "base", "objectType": "Material" },
  "link": "useUom",
  "direction": "reverse" }
// 实测（20260920）：全部物料 → 各自的基本计量单位（8 个；Material 是 useUom 的 B 端，故反向）
```

### 2.5 union / intersect / subtract：集合运算

```json
// union：低风险 ∪ 高风险供应商（实测 11 个：高风险对象暂无，并集=低风险全集）
{ "op": "union",
  "left":  { "op": "filter", "source": {"op":"base","objectType":"Supplier"}, "predicate": {"kind":"eq","property":"riskLevel","value":"低"} },
  "right": { "op": "filter", "source": {"op":"base","objectType":"Supplier"}, "predicate": {"kind":"eq","property":"riskLevel","value":"高"} } }

// intersect：人民币结算的供应商 ∩ 已配采购对接人的供应商（实测 11 个）
{ "op": "intersect",
  "left":  { "op": "searchAround", "source": {"op":"static","objectType":"Currency","primaryKeys":["CNY"]}, "link":"settleCurrency", "direction":"forward" },
  "right": { "op": "filter", "source": {"op":"base","objectType":"Supplier"}, "predicate": {"kind":"not","predicate":{"kind":"isNull","property":"buyerId"}} } }

// subtract：全部物料 − 钢材类物料（实测 7 个非钢材类物料）
{ "op": "subtract",
  "left":  { "op": "base", "objectType": "Material" },
  "right": { "op": "filter", "source": {"op":"base","objectType":"Material"}, "predicate": {"kind":"eq","property":"category","value":"钢材类"} } }
```

### 2.6 嵌套组合：过滤 → 钻取

```json
{ "op": "searchAround",
  "source": { "op": "filter",
    "source": { "op": "base", "objectType": "Supplier" },
    "predicate": { "kind": "eq", "property": "riskLevel", "value": "低" } },
  "link": "signContract",
  "direction": "forward" }
// 实测（20260920）：低风险供应商们签的所有合同 → CT-2026-001 / 002 / 003（3 份全中）
```

再嵌一层就是「多跳」：供应商 → 合同 →（contractCurrency 反向）→ 币种。

### 2.7 虚拟直查类型：读取透明下推源库（20260918 方案）

对象类型可以**不物化**、绑定到源库表/查询（`om_source_mapping.mode = virtual`，经数据源注册 + 绑定 API 建立，如演示库的 `VCustomer`）。这类类型在对象集读取上**与物化类型完全同构**——`op/base|filter|static` 的 simple 树直接**下推源库编译执行**（只读事务 + 语句超时 + 谓词参数化），分页语义完整：

```json
// 虚拟类型 load：与物化类型无差别（实测（20260920）返回源库 3 行 Ada/Bob/Cee）
{ "op": "base", "objectType": "VCustomer" }

// 虚拟类型聚合：同样下推（groupSum 按 region 汇总 amount）
{ "objectSet": { "op": "base", "objectType": "VCustomer" },
  "aggregation": { "kind": "groupSum", "groupBy": "region", "sum": "amount" } }
// 实测（20260920）data.groups：east 3700 / west 800
```

与物化路径的三点差异：

| 维度 | 行为 |
|---|---|
| **总闸** | `onto.virtual_query = true` 才放行虚拟读取；off 时虚拟类型查询明确报「虚拟直查已停用」（绑定退化为不可查，不静默回退） |
| **复杂树桥接** | 树中含 searchAround / 集合运算 / 跨源组合时，不硬凑 join 下推——自顶向下找到「产出类型为虚拟的最大子树」，整树解析为 **pk 集合**（谓词随之下推，上限 `PK_BRIDGE_MAX = 2000`，超出整查询拒绝），替换为 `static` 子集继续分派 |
| **安全前置** | 虚拟绑定要求 authz 模式 ≠ off；读仍过 PEP 行权限/列脱敏，与物化同口径 |

> 虚拟绑定、数据源注册（`om_data_source`，toml `[[databases]]` 引用池 / 独立连接懒注册 `ontosrc_*`）的管理 API 见数据源与绑定相关文档；本教程只覆盖读取侧语义。

## 三、谓词：12 种（`kind`）

真源同文件 `enum Predicate`（`serde(tag = "kind")`，camelCase）。`property` 一律填对象属性 apiName；值为标量 JSON。

| kind | 字段 | 语义 | 实测示例 |
|---|---|---|---|
| `eq` / `ne` | `property`, `value` | 等于 / 不等于 | `{"kind":"eq","property":"riskLevel","value":"低"}` → 11 个 |
| `gt` / `ge` / `lt` / `le` | `property`, `value` | 数值比较 | `{"kind":"ge","property":"rating","value":4.0}` → 11 个 |
| `in` | `property`, `values[]` | 值 ∈ 列表 | `{"kind":"in","property":"riskLevel","values":["低","中"]}` → 14 个 |
| `contains` | `property`, `value` | 文本包含（LIKE %v%） | `{"kind":"contains","property":"name","value":"钢"}` |
| `isNull` | `property` | 属性缺失或 null | `{"kind":"isNull","property":"settleCurrencyId"}` → 2 个（SUP202609130001 / SUP202609120003，引用列空，正是「关系跟着外键列走」的对照例） |
| `and` | `predicates[]` | 全部成立 | 钢材类 且 名称含「钢」→ MAT0002 / MAT0010 |
| `or` | `predicates[]` | 任一成立 | 中风险 或 名称含「办公」→ SUP0004/0005/0006/0010 |
| `not` | `predicate` | 取反 | `{"kind":"not","predicate":{"kind":"isNull","property":"buyerId"}}`（有对接人的 12 家） |

复合示例（and + contains）：

```json
{ "kind": "and", "predicates": [
  { "kind": "eq", "property": "category", "value": "钢材类" },
  { "kind": "contains", "property": "name", "value": "钢" } ] }
```

## 四、聚合：3 种（`kind`）

真源同文件 `enum Aggregation`（`serde(tag = "kind")`，camelCase）。注意各函数体 JSON 里写的是 `groupBy`（驼峰）。

| kind | 字段 | 语义 |
|---|---|---|
| `count` | — | 对象计数 |
| `groupCount` | `property` | 按属性分组计数 |
| `groupSum` | `groupBy`, `sum` | 按属性分组，对另一数值属性求和 |

没有 min/max/avg——需要时用派生属性函数（FEEL/Rhai）在对象集行数组上自行计算。

### 4.1 直连聚合端点 `/object-sets/aggregate`

```bash
# count（实测（20260920）data.count = 14）
curl -s -X POST -H "$AK" -H 'Content-Type: application/json' \
  'http://127.0.0.1:8097/api/onto/v1/object-sets/aggregate?ontology=default_ontology' \
  -d '{"objectSet":{"op":"base","objectType":"Supplier"},"aggregation":{"kind":"count"}}'
// 响应：{ "code":0, "data": { "count": 14 } }

# groupCount 按风险等级（实测）
-d '{"objectSet":{"op":"base","objectType":"Supplier"},"aggregation":{"kind":"groupCount","property":"riskLevel"}}'
// 响应 data：{ "groups": [ {"group":"低","count":11}, {"group":"中","count":3} ] }

# groupSum 物料按类别汇总安全库存（实测）
-d '{"objectSet":{"op":"base","objectType":"Material"},"aggregation":{"kind":"groupSum","groupBy":"category","sum":"safetyStock"}}'
// 响应 data.groups：钢材类 14500.00 / 包装物 2800.00 / 电子元器件 1200.00 / 辅料 1000.00 / 半成品 300.00 / 整机类 20.00
```

> 请求体同样支持 `view`（场景口径）与 `include`（状态分层）可选字段，语义同 §2.1。
> 虚拟类型聚合直接下推源库（§2.7）；物化/虚拟两条路径的数值信封一致。
>
> 读侧硬门：聚合走权限检查，「受限行不计入统计」（行残差折入后再聚合），deny 直接 403——聚合结果与权限一致。

### 4.2 经函数求值 `/functions/evaluate`

聚合类函数（如 `contractSpendBySupplier`，kind=aggregation）走 §一 的两段式：`{ apiName, objectSet, aggregation }`，结果在 `data.result.groups[]`。

## 五、函数求值的三种入参形态

`POST /functions/evaluate?ontology=…` 按**函数定义的 inputs** 绑定入参（`{name, type}`）；`apiName` 为 body 首字段（20260919 去路径化）：

| input type | 请求字段 | 形状 | 例子 |
|---|---|---|---|
| 标量（string/long/double/boolean） | `args` | `{参数名: 值}` | `{"apiName":"…","args":{"supplierId":"SUP0009","newRating":4.8}}` |
| `object` | `objects` | `{参数名: {objectType, pk}}` | supplierGrade：`{"apiName":"supplierGrade","objects":{"supplier":{"objectType":"Supplier","pk":"SUP0001"}}}` → 实测（20260920）`data.result = "A"`（响应另带 `kind:"derivedproperty"`、`runtime:"feel"`） |
| `objectSet`（聚合用途） | `objectSet` + `aggregation` | 两段式 | 见 §一/§四 |

## 六、速查卡（贴屏边）

```jsonc
// 对象集：递归树，叶子是 base / static
{ "op": "base",     "objectType": "X" }
{ "op": "static",   "objectType": "X", "primaryKeys": ["pk1","pk2"] }
{ "op": "filter",   "source": <set>, "predicate": <谓词> }
{ "op": "searchAround", "source": <set>, "link": "关系apiName", "direction": "forward|reverse" }
{ "op": "union" | "intersect" | "subtract", "left": <set>, "right": <set> }

// 谓词
{ "kind": "eq|ne|gt|ge|lt|le", "property": "p", "value": v }
{ "kind": "in", "property": "p", "values": [v1,v2] }
{ "kind": "contains", "property": "p", "value": "子串" }
{ "kind": "isNull", "property": "p" }
{ "kind": "and|or", "predicates": [<谓词>,…] }
{ "kind": "not", "predicate": <谓词> }

// 聚合
{ "kind": "count" }
{ "kind": "groupCount", "property": "p" }
{ "kind": "groupSum", "groupBy": "p", "sum": "数值属性p" }
```

端点一览：

| 端点 | 用途 |
|---|---|
| `POST /api/onto/v1/object-sets/load?ontology=…` | 对象集加载（分页 limit/offset；view/include 可选） |
| `POST /api/onto/v1/object-sets/aggregate?ontology=…` | 对象集聚合（count/groupCount/groupSum） |
| `POST /api/onto/v1/functions/evaluate?ontology=…` | 函数求值（`apiName` 入 body；标量/对象/聚合三形态） |

> 所有端点 `?ontology=` 必填；`ontology=default_ontology` 即演示本体。

## 七、常见坑

1. **`?ontology=` 必填**：所有接口缺本体参数一律 400 `ONTOLOGY_REQUIRED`——每个 curl 别忘了带。
2. **函数求值已去路径化**：`apiName` 在 body 里，老路径 `/functions/{apiName}/evaluate` 返回 404（20260919 接口整改，禁可变路径段）。
3. **direction 与 side 无关**：`forward/reverse` 由起点在关系的 **A/B 端序**决定（A 端出发 forward），与外键存在哪端（`backing.fk.side`）无关。拿不准就看关系定义的 `objectTypeA/objectTypeB`；FK backing 关系靠 `targetProperty` 指到对端 pk 列（20260920 修复后全部对齐 id）。
4. **static 的 primaryKeys 是 pk 值**：各类型 pk 不同——Supplier 填 `SUP0001`（supplierCode），Contract 填 `CT-2026-001`（contractNo），Currency 填 `CNY`（code），不是内部 id。
5. **聚合口径大小写**：JSON 里写驼峰 `groupBy`；属性名是对象属性 apiName（如 `supplierName`、`amount`），翻译错名字会得到空组。
6. **searchAround 的产出类型**由关系两端 + 方向决定，编译器经关系元数据自动推断，请求里不用（也没法）声明。
7. **聚合结果的数值是字符串**（如 `"1200000.00"`，保留 DECIMAL 精度），前端展示/再计算时注意类型；虚拟直查路径同样输出纯数字字符串（20260920 修复了曾出现的 `Decimal(…)` Debug 格式泄漏）。
8. **过滤谓词拒绝裸 SQL**：只接受上述类型化谓词，这是防注入的硬约束，不要想办法拼字符串。
9. **场景 `view` 是可见性口径不是参数装饰**：`object-sets/load|aggregate` 传入时**终端产出类型**必须 ∈ 场景成员（否则 409「不在场景内」）；便捷钻取端点 `/objects/links` 额外校验 link ∈ 场景关系清单；场景视图不存在直接 404。不传 = 全量口径。
