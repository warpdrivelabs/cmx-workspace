# 从协议 JSON 生成 SQL——业务系统适配器实现指南

> 配套 [protocol-v1.md](protocol-v1.md)（协议规范）与 [sql-builder.py](sql-builder.py)（可直接抄的方言感知编译器，MySQL / PostgreSQL / Oracle）。
> 适用：你的适配器底层是关系库（MySQL / PostgreSQL / Oracle / SQL Server…），需要把 `/onto-source/query|aggregate`
> 收到的结构化 JSON 翻译成 SQL。翻译发生在**你的适配器里**，本体平台不生成任何 SQL、也看不到你的表结构。

## 0. 总体管线（一次 query 请求在你这边发生什么）

```text
POST /onto-source/query
{ "version":1, "type":"PurchaseOrder", "filter":{...}, "page":{"offset":100,"limit":50} }
        │
        ├─ 1) type → 表名            ：白名单映射（如 PurchaseOrder → erp_purchase_order），表名不来自请求，来自你自己的映射表
        ├─ 2) filter → WHERE 子句    ：递归编译（本文 §2/§3），值全部参数绑定
        ├─ 3) page   → LIMIT/OFFSET  ：先钳制 pageMax，超了回 40046
        ├─ 4) 恒带 ORDER BY 主键     ：稳定序（协议 caps.defaultOrder 的承诺）
        ▼
   SELECT <列…> FROM <表> WHERE <…> ORDER BY <pk> LIMIT ? OFFSET ?
        │
        ▼
   行 → {"items":[{"pk":主键,"title":标题列,"props":{字段:值,…}}], "total":?, "hasMore":?}
```

aggregate 同理：`COUNT(*)` / `GROUP BY + COUNT(*)` / `GROUP BY + SUM(col)`（§5）。

## 1. 安全铁律（三条，违反即注入面）

1. **标识符只从白名单来**：`filter.prop` 必须先查你的「字段 → 列名」映射表（即绑定时 schema 声明的
   fields）；查不到 → 回 `40044`，**绝不进 SQL**。表名同理——只允许出现在你自己的 type→表 映射里，
   请求永远不能指定表名。
2. **值一律参数绑定**：`status = %s` + 参数列表；数字、字符串、布尔、NULL 全部走绑定。绝不用
   字符串拼接把值写进 SQL——filter 里的值来自业务用户在平台前端的输入。
3. **标识符加方言引用符**：列名 / 表名统一包引用符（MySQL 反引号 `` `col` ``、PG / Oracle / SQL Server
   双引号 `"col"`），防保留字冲突，同时收窄注入面。

> 字段名与列名可以不同：绑定时 schema 声明的 `name` 是协议字段名，你的映射表决定它对应哪一列。
> 最简单的做法是两者同名，映射表退化成一个 set 白名单。

## 2. 叶子算子 → WHERE 片段对照表（value 全部绑定为参数）

| filter 叶子 | WHERE 片段 | NULL / 边界语义（务必读） |
| --- | --- | --- |
| `{"op":"eq","value":V}`    | `col = ?`      | SQL 三值逻辑：col 为 NULL 时比较恒 UNKNOWN → 该行不返回。协议口径一致（NULL ≠ 任何值） |
| `{"op":"ne","value":V}`    | `col <> ?`     | **NULL 行也会被排除**。若你希望「不等于」把 NULL 算进去：`(col <> ? OR col IS NULL)`。二选一，保持稳定，并在 comment 里写明口径 |
| `{"op":"gt/ge/lt/le","value":V}` | `col > ?` 等 | NULL 参与比较恒 UNKNOWN → 排除（这就是协议想要的）。datetime 字段绑定 ISO8601 字符串，数据库会按时间类型比较 |
| `{"op":"in","value":[…]}`  | `col IN (?,…)` | **空数组 → 直接生成 `1 = 0`（恒假）**，不要生成 `IN ()`——那是语法错误。这是合法请求，必须处理 |
| `{"op":"contains","value":V}` | `col LIKE ?`，绑定值 `'%'+V+'%'` | V 里的 `%` `_` `\` 要转义 + `ESCAPE '\'` 子句；PG 想大小写不敏感用 `ILIKE`——用哪种就声明哪种口径，保持恒定 |
| `{"op":"isnull"}`（无 value） | `col IS NULL` | 无参数绑定 |

布尔值绑定：MySQL `1/0`（tinyint）或驱动自动处理；PG 原生 boolean 直接绑 `True/False`。
NULL 值绑定：`eq null` 就绑 `None/NULL`——`col = NULL` 恒 UNKNOWN，所以**语义上等价于 isnull 的查询
平台一般发 `isnull`**；你无需特判，按表实现即可。

## 3. 组合节点递归编译（and / or / not）

```text
compile(node):
  "and" : "(" + join(" AND ", map(compile, children)) + ")"     # 空数组 → 返回 None（不加 WHERE）
  "or"  : "(" + join(" OR ",  map(compile, children)) + ")"     # 空数组 → None
  "not" : "NOT " + compile(child)
  叶子  → §2 对照表
顶层：compile(filter) 为 None → 不拼 WHERE（= 全量）
```

要点：

- **括号恒加**：or 嵌 and、not 包 or 这类组合靠括号保证优先级，编译器一律给组合节点加括号，不做「聪明省略」。
- `not` 里出现白名单外字段同样 40044——白名单校验发生在每个叶子，与嵌套深度无关。
- 协议保证 `and`/`or` 数组至少一个元素，但编译器按「空数组 = 无条件」防御即可（见上）。

## 4. 分页与稳定序

```sql
-- MySQL / PostgreSQL / SQLite
SELECT … FROM … WHERE … ORDER BY `po_no` LIMIT ? OFFSET ?      -- 先 limit 后 offset
-- Oracle 12c+
SELECT … FROM … WHERE … ORDER BY "po_no" OFFSET :o ROWS FETCH NEXT :l ROWS ONLY
-- SQL Server（ORDER BY 必写）
SELECT … FROM … WHERE … ORDER BY [po_no] OFFSET @o ROWS FETCH NEXT @l ROWS ONLY
```

- **ORDER BY 恒带主键列**：offset 分页的正确性依赖稳定序（caps.defaultOrder 对平台的承诺）。
  需要业务默认序（如按单号倒序）就 `ORDER BY <业务列>, <pk>`——第二键恒为主键防抖动。
- **先钳制再编译**：`limit > caps.pageMax` → 回 `40046`（别让 SQL 去执行一个大 limit）。
- offset 翻大页数据库本身会变慢，属正常；平台 pk 桥接回查不用 offset（见 §6）。

## 5. 聚合 → SQL

| aggregate 请求 | SQL |
| --- | --- |
| `{"kind":"count"}` | `SELECT COUNT(*) AS c FROM t [WHERE …]` |
| `{"kind":"groupCount","groupBy":F}` | `SELECT <F> AS k, COUNT(*) AS c FROM t [WHERE …] GROUP BY <F> ORDER BY c DESC` |
| `{"kind":"groupSum","groupBy":F,"prop":F2}` | `SELECT <F> AS k, SUM(<F2>) AS s FROM t [WHERE …] GROUP BY <F> ORDER BY s DESC` |

- `SUM` 自动忽略 NULL；整组全 NULL 时返回 NULL → 响应里 `"sum": null` 即可。
- `groups[].key` 允许 null（GROUP BY NULL 是合法分组）。
- `totalMode:"exact"` 时 query 响应里的 total = 同 filter 的 `COUNT(*)`；`"estimated"` 可取优化器近似
  （PG `pg_class.reltuples`、MySQL `information_schema.TABLES.TABLE_ROWS`），不必精确。

## 6. 平台会发来的三类「特殊」查询（都是普通编译）

### 6.1 多跳关系遍历到你手里=一串独立查询（适配器不做 JOIN、不感知"链"）

平台的对象集 JSON 支持 `searchAround` 多跳嵌套（如：审批采购单 →供应商 →风险事件，末端带 filter）。
**这个递归在平台分派器里被拆解**：每一跳到适配器这里就是一次普通的单资源 query——上一跳的产出 pk
变成下一跳的 `in` 过滤值。适配器无状态、逐请求独立，永远看不到"链"的全貌（连接语义由平台持有，
这正是跨源/跨后端能统一走的原因）。以「审批采购单 → rel_po_supplier → 供应商 → rel_supplier_risk
→ 风险事件(level≥3)」为例，假设供应商与风险事件都挂在你的 API 源上，你只会依次收到：

```jsonc
// 请求 1：第一跳（起点在别处则不会有；此处示例起点也在你源上）
{ "version":1, "type":"PurchaseOrder", "filter":{"prop":"status","op":"eq","value":"approved"},
  "page":{"offset":0,"limit":1000} }
// 请求 2：第二跳（平台查完本体库关系边，拿供应商 pk 来问风险事件）
{ "version":1, "type":"RiskEvent",
  "filter":{ "and":[ {"prop":"level","op":"ge","value":3},
                     {"prop":"supplier_id","op":"in","value":["SUP-01","SUP-07", …≤2000] } ] },
  "page":{"offset":0,"limit":1000} }
```

对应生成的 SQL 就是 §2/§3 的普通编译，没有任何 JOIN：

```sql
SELECT "po_no",… FROM "erp_purchase_order" WHERE "status" = $1 ORDER BY "po_no" LIMIT 1000 OFFSET 0;
SELECT "risk_id",…  FROM "erp_risk_event"
  WHERE ("level" >= $1 AND "supplier_id" IN ($2,$3,…)) ORDER BY "risk_id" LIMIT 1000 OFFSET 0;
```

### 6.2 pk 桥接回查

关系钻取（searchAround）的目标端回查就是上面的 `in` 形态：单列主键、值 ≤2000 个（平台已兜底超限）。
MySQL 注意 `max_allowed_packet` 与驱动参数上限即可。

### 6.3 恒假查询

空 pk 集合 / 空数组 IN → 编译成 `1 = 0`（或 `WHERE 1 = 0`），不会打到你的库也行，
但直接回 `{"items":[],"hasMore":false}` 最省事。

## 7. 明细行（单据头 + 行）两种落地

明细行字段（`baseType:"array"`）**不参与过滤**，只在 query 响应的 props 里随头表返回。两种实现：

- **A. JSON 列**（PG `jsonb` / MySQL `JSON`）：行数据整存一列，`SELECT lines …` 后反序列化进 props。
  最省事，推荐新系统。
- **B. 独立行表**：先查头表页（≤pageMax 个 pk），再**一次** `SELECT … FROM erp_po_line WHERE po_no IN (…页内全部 pk…)`
  拉回分组组装进各行 props。切忌逐头查询（N+1）。

## 8. 端到端示例（可对着 [sql-builder.py](sql-builder.py) 看）

请求：

```json
{ "version":1, "type":"PurchaseOrder",
  "filter": {"and":[
      {"prop":"status","op":"eq","value":"approved"},
      {"or":[{"prop":"amount","op":"ge","value":10000},
            {"not":{"prop":"remark","op":"isnull"}}]}]},
  "page": {"offset":0,"limit":50} }
```

生成（PostgreSQL，:1 为占位）：

```sql
SELECT "po_no","status","amount","order_date","remark","lines"
FROM "erp_purchase_order"
WHERE ("status" = $1 AND (("amount" >= $2 OR NOT ("remark" IS NULL))))
ORDER BY "po_no" LIMIT 50 OFFSET 0
-- params: ['approved', 10000]
```

行 → 响应：

```json
{ "code":0, "msg":"ok", "data":{ "items":[
    { "pk":"PO-2026-0001", "title":"PO-2026-0001",
      "props":{ "po_no":"PO-2026-0001","status":"approved","amount":12500.5,
                "orderDate":"2026-08-01T10:00:00+08:00","remark":"加急",
                "lines":[{ "lineNo":1, "materialCode":"M-001", … }] } } ],
  "total":null, "hasMore":false } }
```

注意 props 的键是**协议字段名**（`orderDate`），SQL 列名是 `order_date`——出口处按你的映射表翻回去。

## 9. 自查清单（SQL 型适配器）

- [ ] prop / type 任何一处不在白名单 → 40044，值永不拼接
- [ ] 空数组 IN → `1 = 0`；contains 的 `%` `_` 已转义；ne 的 NULL 口径已定且稳定
- [ ] 恒带 ORDER BY 主键；limit 先过 pageMax 钳制
- [ ] count / groupCount / groupSum 三条 SQL 与 caps.aggregates 声明一致
- [ ] 明细行：JSON 列或 IN 批量二次查询（无 N+1）
- [ ] `scripts/conformance.py` 全绿 + 用真实库再手测一条嵌套 filter
