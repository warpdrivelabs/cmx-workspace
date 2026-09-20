# CMX 本体 API 数据源查询协议 v1（规范全文）

> 适用：三方业务系统向 CMX 本体平台（cmx-ontology）暴露「API 数据源（kind=api）」供虚拟直查。
> 本文档是协议的**规范真源**；平台侧权威实现：`backend/cmx-ontology/crates/cmx-onto-app/src/backend_api.rs`，
> 参考实现：`backend/cmx-ontology/test/e2e/_onto_source_demo.py`。
> 方案背景：《documents/plans/20260920_cmx-ontology_API数据源接入与前端交互方案.md》§二。

---

## 0. 版本与演进规则

- 所有 POST 请求体携带 `"version": 1`；适配器收到其它值必须回 `{"code":40040,...}`，不得猜测语义。
- **请求中出现协议未定义的字段 → 忽略**（前向兼容，平台后续版本可能追加）。
- **未声明的算子 / 聚合 → 显式回 40044 / 40047**，不得按近似语义猜测执行。
- 协议字段命名一律 **camelCase**（`filterOps`、`pageMax`、`hasMore`…）；源字段名不受限（保持业务系统原样）。

## 1. 通用约定

| 项 | 约定 |
| --- | --- |
| 信封 | 所有响应（含错误）一律 `{"code": <int>, "msg": <string>, "data": <object>}`；`code=0` 成功，非 0 走 §6 错误码表 |
| HTTP 状态 | 业务错误（40040/40044/…）HTTP 恒 **200** + 信封 code；仅基础设施故障（路由不存在、鉴权拒收）用 404 / 401 / 403 / 500 |
| Content-Type | 请求与响应均 `application/json`（UTF-8） |
| 方法语义 | 全部只读、幂等；平台只会发 `GET`（schema）与 `POST`（query / aggregate），不会有写语义 |
| 路径 | 固定资源段，**无路径参数**：`/onto-source/schema`、`/onto-source/query`、`/onto-source/aggregate`（挂在注册的 baseUrl 下） |
| 平台标识头 | 平台出站请求恒带 `X-Onto-Source: cmx-ontology`（适配器可据此识别 / 统计平台流量） |
| baseUrl | 平台注册的 `config.baseUrl`，如 `http://erp.internal:8000/api/erp/v1`；实际请求 URL = `{baseUrl 去尾斜杠}{固定路径}` |
| 超时 | 平台单请求超时 = 源 `config.timeoutMs`（钳制 500ms~60s），未配则 `onto.api_timeout_secs`（默认 8s）；适配器应远快于此返回 |
| 限流 | 平台按源限流：`config.qps`（默认 10，1~1000）与 `config.maxConcurrent`（默认 4，1~64）——适配器无需实现限流，但应能承受该压力 |

## 2. 能力矩阵 caps（schema 响应 `data.caps`）

caps 是**适配器对平台的契约声明**：平台据此在本地预检（能力外的查询直接拒绝、不出网），并在
管理页 / Inspector / explorer 里收敛用户可用的过滤算子与统计口径。**声明什么，平台就认为支持什么——
声明与实现必须一致**（平台「测试连接」会实测探测并落快照，实测优先于声明）。

| 字段 | 类型 | 必填 | 语义 | 缺省（未声明时平台兜底） |
| --- | --- | --- | --- | --- |
| `filterOps` | string[] | 推荐 | 支持的过滤算子，取值 ⊆ `eq/ne/gt/lt/ge/le/in/contains/isnull` | 九个全量（宽松兜底） |
| `pageMax` | int | 推荐 | 单页行数上限（平台钳制 1~1000）；请求超限适配器必须回 40046 | 1000 |
| `totalMode` | string | 推荐 | total 计数档位：`exact` / `estimated` / `none` | `none`（不给总数，fail-closed） |
| `cursor` | bool | 必须 false | 是否游标分页。**平台 v1 仅支持 offset 分页，`true` 会在绑定时被直接拒绝** | false |
| `defaultOrder` | string | 推荐 | 稳定默认序说明（如 `"pk"`），仅展示用；分页顺序稳定是硬要求 | `"pk"` |
| `aggregates` | string[] | 推荐 | 支持的聚合，取值 ⊆ `count/groupCount/groupSum` | 三个全量（宽松兜底） |

示例（演示适配器：不支持 contains、大表不给总数）：

```json
{
  "filterOps": ["eq","ne","gt","ge","lt","le","in","isnull"],
  "pageMax": 100,
  "totalMode": "none",
  "cursor": false,
  "defaultOrder": "pk",
  "aggregates": ["count","groupCount","groupSum"]
}
```

> 建议**全字段显式声明**：缺省兜底是「宽松 + total none」，若你的适配器其实只支持 3 个算子却漏声明，
> 平台会按全量算子放行查询，最终在远端吃 40044——能用，但用户体验差（错误晚一步）。

## 3. 端点一：`GET {base}/onto-source/schema`（双形态）

### 3.1 不带 `type`——资源清单 + 能力矩阵（「测试连接」探测用）

```jsonc
// 响应 data
{
  "caps": { /* §2 */ },
  "resources": [
    { "type": "PurchaseOrder", "name": "采购订单" },
    { "type": "Supplier",      "name": "供应商" }
  ]
}
```

- `resources[].type`：资源名，即绑定 `mapping.resource` 的取值，必须匹配
  **`^[A-Za-z][A-Za-z0-9_.-]{0,127}$`**（字母开头；字母/数字/下划线/点/连字符；≤128 字符）。
- `resources[].name`：中文显示名（管理页资源清单、绑定向导资源下拉展示用）。

### 3.2 带 `?type=<资源名>`——该资源的字段清单（绑定向导字段反射用）

```jsonc
// 响应 data —— 平台读取 resources[0].fields
{
  "caps": { /* 同上，建议一并返回 */ },
  "resources": [
    {
      "type": "PurchaseOrder",
      "name": "采购订单",
      "fields": [
        { "name": "po_no",     "baseType": "string",   "sourceType": "varchar(32)",    "comment": "单号" },
        { "name": "amount",    "baseType": "number",   "sourceType": "decimal(18,2)",  "comment": "金额" },
        { "name": "orderDate", "baseType": "datetime", "sourceType": "datetime",       "comment": "下单时间" },
        { "name": "lines",     "baseType": "array",    "sourceType": "jsonb",          "comment": "明细行",
          "fields": [
            { "name": "lineNo",        "baseType": "number", "sourceType": "int" },
            { "name": "materialCode",  "baseType": "string", "sourceType": "varchar(16)" },
            { "name": "materialName",  "baseType": "string", "sourceType": "varchar(64)" },
            { "name": "qty",           "baseType": "number", "sourceType": "decimal(18,3)" },
            { "name": "price",         "baseType": "number", "sourceType": "decimal(18,2)" }
          ] }
      ]
    }
  ]
}
```

字段对象约束：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `name` | ✅ | 源字段名；**query 请求 filter.prop 与响应 props 的键都以此为准** |
| `baseType` | ✅ | 协议基型，五选一：`string / number / boolean / datetime / array` |
| `sourceType` | 可选 | 底层原始类型描述（如 `varchar(32)`、`decimal(18,2)`），仅展示用 |
| `comment` | 可选 | 字段中文注释，绑定向导展示用 |
| `fields` | array 型必填 | **明细行子字段清单**（嵌套结构同本表）；非 array 字段不带 |

平台侧基型映射（绑定导入属性时自动换算本体基型）：

| 协议 baseType | 本体基型 |
| --- | --- |
| `string`（及未知值兜底） | string |
| `number` | double |
| `boolean` | boolean |
| `datetime` | timestamp |
| `array` | array（明细行整挂一个属性，explorer 详情展开为子表） |

资源不存在时回 `{"code":40401,"msg":"资源 X 不存在"}`。

## 4. 端点二：`POST {base}/onto-source/query`

### 4.1 请求

```jsonc
{
  "version": 1,                    // 必填；≠1 → 40040
  "type": "PurchaseOrder",         // 必填；资源不存在 → 40401
  "filter": { /* §4.2，可省略 = 无过滤（全量） */ },
  "page": { "offset": 0, "limit": 50 },   // 平台恒带；limit ≤ caps.pageMax，超限适配器必须回 40046
  "select": null,                  // v1 恒 null，忽略（投影由绑定映射决定）
  "orderBy": null                  // v1 恒 null（排序能力预留）；按 defaultOrder 返回稳定序
}
```

未知顶层字段（含 `select`/`orderBy` 的 null 值）一律忽略。

### 4.2 filter DSL（结构化过滤，业务系统自行翻译为底层查询条件）

节点两类，可任意深度嵌套：

**组合节点**：

| 形态 | 语义 |
| --- | --- |
| `{"and": [<节点>, …]}` | 子节点结果取交集（空数组 = 不过滤，见下方注意） |
| `{"or": [<节点>, …]}` | 子节点结果取并集 |
| `{"not": <节点>}` | 子节点结果取补集 |

**叶子节点**：`{"prop": "<源字段名>", "op": "<算子>", "value": <值>}`

| op | 语义 | value 形态 |
| --- | --- | --- |
| `eq` / `ne` | 等于 / 不等于 | 标量：string / number / boolean / null |
| `gt` / `ge` / `lt` / `le` | 比较（number 按数值、ISO8601 字符串按时间字典序均可比） | 标量 |
| `in` | 属于集合 | **标量数组**（键名恒为 `value`，不是 `values`） |
| `contains` | 字符串包含（子串） | string |
| `isnull` | 字段为 null / 缺失 | **无 value 键** |

值类型约束：标量或标量数组（平台侧已浅校验）；对象/嵌套数组做值 → 平台直接拒绝不出网。

> ⚠️ 语义注意：平台编译产物中 `and`/`or` 数组**至少有一个元素**；但适配器仍应对空数组防御
> （参考实现按「空 = 不过滤」处理）。`not` 嵌套是 v1 正式能力（平台权限残差会用到），必须实现。

filter 里的 `prop` 恒为**源字段名**（绑定 property_map 的左侧）。平台保证：未映射到源字段的本体属性
不会出现在 filter 里（那类查询在平台侧整查询拒绝）。

### 4.3 响应

```jsonc
// 响应 data
{
  "items": [
    {
      "pk": "PO-2026-0001",          // ⚠️ 恒为非空字符串（数字主键转字符串）；缺失/空 → 整页被平台拒收
      "title": "PO-2026-0001",       // 列表标题展示用；建议给业务标题，没有就与 pk 相同
      "props": {                      // 键 = schema 声明的源字段名；值见下方类型约定
        "po_no": "PO-2026-0001",
        "status": "approved",
        "amount": 12500.5,
        "orderDate": "2026-08-01T10:00:00+08:00",
        "remark": "加急",
        "lines": [                    // 数组 = 单据明细行（baseType=array 的字段）
          { "lineNo": 1, "materialCode": "M-001", "materialName": "螺纹钢 HRB400", "qty": 100, "price": 3800.0 }
        ]
      }
    }
  ],
  "total": null,                      // 见 total 三态
  "hasMore": true                     // 是否还有下一页；平台缺失时按「本次返回行数 == limit」推断，建议显式给
}
```

- **props 值类型约定**：`string` / `number` / `boolean` / ISO8601 字符串（datetime 字段）/
  `null` / **数组（仅 array 字段 = 明细行对象数组）**。未在 schema 声明的键平台会忽略；
  声明了但本行无值的键请显式给 `null`（不要省略键）。
- **total 三态**（与 caps.totalMode 对应）：
  - `exact`：`"total": <int>` 精确总数（与无分页时的命中行数一致）；
  - `estimated`：`"total": <int>` 约数（前端显示「约 N」）；
  - `none`：不给 total（`null` 或省略键；前端显示「已加载 N 行」）。
- 平台重排序 / 重投影 props（按绑定映射翻回本体属性名），适配器无需关心投影，返回全字段即可。

### 4.4 适配器内部的翻译示例（伪代码）

```text
收到  {"prop":"status","op":"eq","value":"approved"}          → SQL: WHERE status = 'approved'
收到  {"prop":"amount","op":"ge","value":1000}                → SQL: WHERE amount >= 1000
收到  {"prop":"status","op":"in","value":["draft","closed"]}  → SQL: WHERE status IN ('draft','closed')
收到  {"prop":"remark","op":"isnull"}                         → SQL: WHERE remark IS NULL
收到  {"and":[<A>,<B>]} / {"or":[…]} / {"not":{…}}            → SQL: (…) AND (…) / OR / NOT
page {offset:100, limit:50}                                   → SQL: LIMIT 50 OFFSET 100（order by 稳定列）
```

> **SQL 拼接安全由适配器自负**：值只允许参数化绑定，字段名只允许出现在 schema 声明白名单里
> （收到白名单外的 prop → 40044），这是适配器侧防注入的最低要求。参考实现 `eval_filter` 演示了
> 白名单校验 + 值绑定的写法。

## 5. 端点三：`POST {base}/onto-source/aggregate`

请求：

```jsonc
{
  "version": 1,
  "type": "PurchaseOrder",
  "filter": { /* 同 §4.2，可省略 */ },
  "aggregate": {                       // 三选一
    "kind": "count"
    // "kind": "groupCount", "groupBy": "status"
    // "kind": "groupSum",   "groupBy": "status", "prop": "amount"
  }
}
```

响应：

```jsonc
// count →
{ "count": 8 }
// groupCount / groupSum → （groups 建议按值降序；key 允许 null）
{ "groups": [ { "key": "approved", "count": 4 }, { "key": "draft", "count": 2 } ] }
{ "groups": [ { "key": "approved", "sum":   53660.5 } ] }
```

未声明的 kind → 40047；groupX 缺 `groupBy` → 40047。平台只消费 `count` / `groups[].key` /
`groups[].count` / `groups[].sum` 四种键。

## 6. 错误码表（信封 code）

| code | 含义 | msg 建议 | 平台侧呈现 |
| --- | --- | --- | --- |
| `0` | 成功 | `"ok"` | — |
| `40040` | 协议版本不支持 | 指明收到的 version | 「该数据源协议版本过旧，请联系业务系统升级适配器」 |
| `40044` | 不支持的过滤（算子未实现 / 字段不在白名单 / filter 节点畸形） | 指明算子与字段 | 「该数据源不支持此过滤：\<msg\>」 |
| `40045` | 不支持的排序 | 指明字段 | 「该数据源不支持此排序：\<msg\>」（v1 平台不下推排序，预留） |
| `40046` | 页宽超上限 | 指明 limit 与 pageMax | 「页宽超出该数据源上限」 |
| `40047` | 不支持的聚合 / 聚合参数缺失 | 指明 kind | 「该数据源不支持此聚合：\<msg\>」 |
| `40401` | 资源不存在 | 指明资源名 | 「资源不存在于该数据源：\<msg\>」 |
| `50000` | 适配器内部错误（约定俗成） | 异常摘要 | 原 msg 透传给用户 |
| 其它非 0 | 适配器自定义 | 任意 | 原 msg 透传 |

HTTP 层：`401/403` 平台按「认证失败」提示（检查平台侧 `auth.*Env` 凭证）；其余非 2xx 报
「API 数据源返回 HTTP xxx」并截取响应前 200 字符。**业务错误不要用非 200**，否则平台无法展示精确文案。

## 7. 认证（平台 → 业务系统方向）

平台在注册源时配置 `config.auth`，**凭证只存环境变量引用名，请求时刻才注入**——业务系统侧无需做任何事，
但要知道平台会怎么调你：

| mode | 平台发出的头 | 所需 env 引用（平台侧配置） |
| --- | --- | --- |
| `none`（默认） | 无 | — |
| `api-key` | `<headerName 默认 X-API-Key>: <keyEnv 的值>` | `keyEnv` |
| `bearer` | `Authorization: Bearer <tokenEnv 的值>` | `tokenEnv` |
| `basic` | `Authorization: Basic base64(<userEnv>:<passwordEnv>)` | `userEnv` + `passwordEnv` |

另可配 `config.headers`（静态附加头，键值对；**认证类键名被平台校验拒绝**——认证走上表，不允许绕道）。
适配器校验失败（如 token 不对）直接回 HTTP 401，平台会给出精确提示。

## 8. 单据（头 + 行）约定

单据在协议里就是**一个资源**：头表字段平铺，明细行是 `baseType:"array"` 字段（§3.2 嵌套 `fields` 声明子字段），
query 响应的 `props.<明细字段>` 返回**对象数组**。不需要独立的「行资源」、不需要平台侧 JOIN。

```text
schema:  fields: [ …头表字段…, { name:"lines", baseType:"array", fields:[行子字段…] } ]
query:   props:  { …头表字段值…, "lines": [ {行对象}, … ] }
explorer:列表 = 头表；详情展开「明细行」子表（每行一个数组元素）
```

限制：明细行子字段**只展示不过滤**（平台对 array 属性禁用过滤算子）；行级聚合（groupSum 按行字段）
v1 不支持下推——需要时在头表冗余汇总列（如 `totalQty`）。

## 9. 平台侧行为备忘（适配器开发者须知）

以下由平台保证，适配器可以据此简化实现，但**不构成协议义务**：

- **预检在先**：算子不在 caps.filterOps、聚合不在 caps.aggregates、未映射字段参与过滤、
  cursor 源——这些查询平台在本地直接拒绝，**不会出网**；适配器收到的 filter 理论上都在声明能力内。
- **兜底语义仍 fail-closed**：若适配器 caps 声明与实现不符（声明有、实现无），平台把请求发过来后，
  适配器必须回 40044——绝不静默返回错误数据。
- **bind 时强校验**：绑定时平台会拉 schema 强校验映射列（不可达时降级警告保存）；无 `eq` 算子的源
  拒绝绑定（pk 桥接依赖 `in`，`in` 也必须有——声明算子时请至少包含 `eq` 与 `in`）。
- **pk 桥接**：跨类型关系钻取会以 `{"prop":"<pk 字段>","op":"in","value":[…≤2000…]}` 回查你的资源，
  单列主键 + eq/in 支持即可满足。
- **探测落基线**：绑定 / 测试连接时的 schema 实测结果会落库（probe_report），后续以实测 caps 优先于
  声明 caps 运行——改协议行为后记得在管理页重新「测试连接」。

## 10. 最小合规清单（对接验收口径）

- [ ] 三个端点路径、方法、信封 `{code,msg,data}` 全部符合
- [ ] `version≠1` → 40040；未知资源 → 40401；未知算子 → 40044；超页宽 → 40046；未知聚合 → 40047
- [ ] caps 全字段显式声明且与实现一致（`cursor:false`；至少含 `eq`、`in`）
- [ ] schema 双形态正确（无 type 资源清单；带 type `resources[0].fields`）
- [ ] query：pk 恒非空字符串；props 键 = schema 字段名；hasMore 正确；分页顺序稳定
- [ ] total 行为与 totalMode 声明一致
- [ ] aggregate 三种 kind 的响应键正确
- [ ] `scripts/conformance.py` 全绿（用你自己的 `--type`/`--pk-field` 参数）
- [ ] 平台「测试连接」结果卡：可达、能力实测与声明一致（无黄牌或黄牌可解释）
