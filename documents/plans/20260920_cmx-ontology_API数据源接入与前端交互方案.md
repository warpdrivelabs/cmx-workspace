# cmx-ontology API 数据源接入与前端交互方案

| 项 | 内容 |
| --- | --- |
| 日期 | 2026-09-20 |
| 状态 | **已实施（M2a/M2b 落地，2026-09-20；e2e 37/37 + UI 实测通过）** |
| 模块 | backend/cmx-ontology（芯 cmx-onto-model + 壳 cmx-onto-app / cmx-onto-server）+ backend/cmx-container（通用适配 crate + 前端资产真源 assets/onto/） |
| 定位 | 既有方案 **M2 细化卷**：把 20260918 方案中「REST API 数据源 + 查询协议」从一节草案细化为可实施设计，并以**前端交互 / 用户体验**为主线补齐全链路 |
| 关联文档 | [20260918_cmx-ontology_对象数据源统一抽象与外部取数方案.md](./20260918_cmx-ontology_对象数据源统一抽象与外部取数方案.md)（母方案 v1.4，D2/D3/D7/E7 等决策沿用）、[20260918_cmx-ontology_对象数据源统一抽象与外部取数PRD.md](./20260918_cmx-ontology_对象数据源统一抽象与外部取数PRD.md)（US-021~025 对应本方案验收） |
| 用户已拍板 | ① 接入配套 = 协议规范 + CMX 通用适配 crate + conformance 套件（全档）；② 单据（头+行）虚拟化示范纳入本期 |

---

## 一、背景与架构定位（先回答三个根本问题）

### 1.1 现状核实（2026-09-20 代码实况）

母方案 M0/M1a/M1b 已全部落地（commit `71a12ff` 等）：PG 虚拟直查、`om_data_source` 注册表、数据源管理页、studio-next 绑定向导、explorer 直查徽章与未映射置灰均在运行。**API 数据源是唯一剩下的完整缺口**，且"座位已预留、乘客未上车"：

| 层 | 已预留 | 缺失 |
| --- | --- | --- |
| 注册表 | `om_data_source.kind` 值域已含 `api`，api 源**可创建落库**（`crates/cmx-onto-store-pg/src/source_store.rs:69-78`） | 无任何消费方 |
| 契约 | `BackendKind::RestApi` 枚举变体已存在（`crates/cmx-onto-model/src/backend.rs:28-38`，注释「M2 落地」） | `RestApiBackend` 零实现，`BackendCaps::rest_api()` 构造器缺失 |
| 绑定 | bind 校验链完整（source_handlers.rs:184-314） | 源 kind≠pg 直接硬拒：「查询后端随 M2 交付，当前仅支持 pg 源」（source_handlers.rs:240-245） |
| 探测/反射 | probe（pg）/ schema（pg）已有 | api 源探测、api 源字段反射均未实现（source_store.rs:150-154 明示「api 走 GET /onto-source/schema，M2」） |
| 分派 | `binding_of` 只按 `mode==virtual` 二分，virtual 恒 `pg_direct_backend()`（backend_dispatcher.rs:87-116） | 未按注册行 kind 分派 RestApiBackend |
| 前端 | 数据源管理页（`assets/onto/web/ui-native/onto/sources.js`）、绑定向导（studio-next `runtime.js`）形态完备 | **新建表单硬编码 `kind:'pg'` 无类型选择器**（sources.js dlgDraft L454-457）；绑定向导选源两处硬过滤 `kind==='pg'`（runtime.js L1218/L1600） |

结论：**前端「只支持 pg 数据源」属实，但这是最后一公里的呈现问题，后端抽象座位已全部留好**。本方案不推翻任何既有决策，只填空。

### 1.2 问题一：API 算一种数据源吗？——算，且是「非 PG 业务的唯一入口」

**结论：API 是与 PG 并列的一种数据源**（母方案 D3 拍板：pg / api / connector 三种外部源 + 内置物化，定义为统一 `ObjectDataBackend` trait 的不同实现）。对建模者而言，API 源与 PG 源**同构**：同一张注册表、同一张绑定表、同一套绑定向导、同一个 explorer 徽章位——差别只在配置表单和取数通道。

必须先讲清楚一个容易混淆的架构边界（本次规划中用户明确提出）：

> **「虚拟直查」是读路径语义（查询时取数、数据不落地），实现它的后端有两种，边界完全不同：**

|  | PgDirectBackend（已实现） | **RestApiBackend（本方案交付）** |
| --- | --- | --- |
| 谁写 SQL | **本体平台**把对象集过滤代数编译成 PG 方言 SQL，直连对方库执行 | **本体平台不生成任何 SQL**——把结构化查询以 JSON 发给业务系统的适配端点，**业务系统自己**转成底层查询 |
| 对方存储 | 必须是 PostgreSQL（`cmx-database-pg` 只有 PG 驱动，方言锁定） | **不限**：MySQL / Oracle / 达梦 / ES / MongoDB 甚至无库微服务——转换职责全在业务系统侧，本体零感知 |
| 数据库凭证 | 本体持有只读账号（env 引用） | 凭证留在业务系统；本体只存 API 认证的 env 引用 |
| 查询传输形态 | SQL 文本下推 | JSON 结构化查询参数（filter + page） |
| 行级权限 | 残差编译进下推 SQL | 残差编码进 JSON filter（E7），远端执行 |

所以「如果我们直接转成 SQL，那不相当于直连对方数据库了」的担心，正是母方案 D2 已经划掉的边界：**本体直接生成 SQL 的路只对 PG 开放；一切非 PG 业务系统走 API 源，本体发出的是 JSON 查询参数，永远不会碰对方数据库**。业务系统底层换成任何存储，本体侧一行代码不用改。

### 1.3 问题二：API 数据源如何与 om_source_mapping 结合？——权威行原样复用，source_id 指向 api 注册行

`om_source_mapping` 行继续作为绑定关系**唯一权威**（母方案 E1），API 源不新增表、不加列，靠「source_id → 注册行 kind」完成语义分派。字段对照与细节见 §三。

### 1.4 取数语义边界

- **本期 = 仅虚拟直查**（与母方案 D2/D3 一致）：API 源绑定的对象类型查询时下推，数据零拷贝、实时。
- 「从 API 定期拉取物化到本地」（漏斗 API reader）**不在本期**，作为 M3 规划草案收入附录 A——大数据量 / 源不稳定 / 需要稳定快照的场景引导先评估物化诉求，本期用 PG 漏斗或后续 M3 解决。

---

## 二、API 查询协议 v1（业务系统必须遵守的契约）

> 本章是「让业务系统来遵守」的规范真源。落地时以独立协议文档形式发布到 `backend/cmx-ontology/docs/`（实施清单见 §6.3），本章为设计定稿。

### 2.1 总则

1. **通信形态**：业务系统在本系统内暴露固定约定的三个端点（挂载前缀 `{base}` 由源配置的 baseUrl 决定，如 `http://erp.internal:9000/api/erp/v1`）；
2. **响应信封**：全生态统一 `{code, msg, data}`（对齐 `cmx-api-types::ApiResp`）；
3. **路径规范**：遵守根 AGENTS.md §四.6——固定资源段、无路径参数、写操作 POST（本协议只有 query/aggregate 两个 POST 与一个 GET schema，天然合规）；
4. **fail-fast 原则**：业务系统**不支持**的查询（算子/页宽/排序）必须显式报错，**严禁静默降级**（如忽略过滤条件返回全量）——这是虚拟直查正确性的生命线；
5. **版本协商**：请求体带 `version` 字段（当前恒 `1`）；业务系统不识别的版本返回 code=40040，本体侧报错不重试。

### 2.2 端点清单

| 端点 | 方法 | 用途 | 本体侧调用方 |
| --- | --- | --- | --- |
| `{base}/onto-source/query` | POST | 对象集查询（过滤/分页/投影） | RestApiBackend.load、resolve_pks（转 pk IN filter） |
| `{base}/onto-source/aggregate` | POST | 聚合（count / groupCount / groupSum） | RestApiBackend.aggregate |
| `{base}/onto-source/schema` | GET | 能力矩阵 + 资源清单 + 字段反射 | probe 探测、绑定向导「读取源结构」、漂移基线 |

`schema` 端点的双形态：**不带 `type`** 返回能力矩阵 + 资源清单（供新建源测试连接与绑定向导选资源）；**带 `?type=X`** 返回该资源字段清单（供字段反射导入与映射校验、漂移比对）。

### 2.3 请求格式（query）

```json
POST {base}/onto-source/query
{
  "version": 1,
  "type": "PurchaseOrder",
  "filter": {
    "and": [
      {"prop": "status", "op": "eq", "value": "approved"},
      {"or": [
        {"prop": "amount", "op": "ge", "value": 1000},
        {"prop": "supplier", "op": "in", "value": ["华中钢铁", "宝钢"]}
      ]},
      {"prop": "deleted", "op": "isnull"}
    ]
  },
  "page": {"offset": 0, "limit": 50, "cursor": null},
  "select": null,
  "orderBy": null
}
```

**filter 规则**：

- 叶子节点：`{"prop": <字段名>, "op": <算子>, "value": <标量或数组>}`；
- 组合节点：`{"and": [...]}` / `{"or": [...]}`，可任意嵌套；
- 算子集**与本体 `PredicateKind` 一一对齐**（9 个）：`eq` `ne` `gt` `lt` `ge` `le` `in`（value 为数组）`contains`（子串，字符串型）`isnull`（无 value）；**没有 Like**——contains 是等价物；
- **行级权限残差编码于此**（母方案 E7）：本体把当前用户策略残差作为 filter 的 AND 支路一并发送；业务系统**必须**把它当普通过滤执行，不得剥离。业务系统还可在此之上叠加自身权限（推荐叠加，形成双保险）；
- 字段名即绑定时 `property_map` 声明的**源字段名**（不是本体属性 apiName）。

**page 规则**（双形态，按源声明 `caps.cursor` 二选一）：

- offset 协议（`cursor:false`）：`{"offset": 0, "limit": 50}`，offset 缺省 0；
- cursor 协议（`cursor:true`）：`{"cursor": null, "limit": 50}`，首页 cursor 为 null，后续页回传上次响应的 `nextCursor`；
- `limit` ≤ `caps.pageMax`（超限本体侧**先行 clamp**，不发非法请求）。

**select / orderBy**：v1 恒为 `null`（全量 props 投影；排序走源稳定默认序）。字段保留，M2 后续开 orderBy 时启用（母方案 E4：排序能力与协议字段一并开）。

### 2.4 响应格式（query）

```json
{
  "code": 0,
  "msg": "ok",
  "data": {
    "items": [
      {
        "pk": "PO-2026-0001",
        "title": "采购订单 PO-2026-0001",
        "props": {
          "status": "approved",
          "amount": 12500.50,
          "supplier": "华中钢铁",
          "orderDate": "2026-09-01T00:00:00+08:00",
          "remark": null,
          "lines": [
            {"lineNo": 1, "materialCode": "M-001", "material": "螺纹钢 HRB400", "qty": 100, "price": 3800.00}
          ]
        }
      }
    ],
    "total": null,
    "hasMore": true,
    "nextCursor": "b2Zmc2V0OjUw"
  }
}
```

| 字段 | 类型 | 规则 |
| --- | --- | --- |
| `items[].pk` | **string 恒定** | 数字主键转字符串传输；一行一 pk，与绑定 `keyColumns` 恰 1 列对应 |
| `items[].title` | string | 展示标题；绑定 `titleColumn` 对应字段；无标题语义时回填 pk 字符串 |
| `items[].props` | object | **源字段名 → 值**。值类型：string / number（JSON number，不限整数浮点）/ boolean / **ISO8601 带时区字符串**（datetime 一律字符串，禁裸时间戳数字）/ null。**嵌套数组 = 单据明细行**（见 §4.5），数组元素为同构 object |
| `total` | number \| null | 按 `caps.totalMode`：`exact` 必须给精确值；`estimated` 给估算（允许漂移）；`none` 恒 null。**大表 count 代价由业务系统自决档位** |
| `hasMore` | boolean | **必填**。`rows == limit` 时为 true 的近似口径可接受 |
| `nextCursor` | string \| null | 仅 cursor 协议源在还有下一页时必填；offset 源忽略 |

**分页正确性红线**：翻页期间源数据变化允许产生漂移（实时语义固有），但**同一过滤条件下的页间不得重复/跳空主键**（cursor 协议天然保证；offset 协议要求源有稳定默认序 `caps.defaultOrder`，通常为 pk）。

### 2.5 请求/响应格式（aggregate）

```json
POST {base}/onto-source/aggregate
{"version": 1, "type": "PurchaseOrder", "filter": {…同 query…},
 "aggregate": {"kind": "groupCount", "groupBy": "status"}}

→ {"code":0,"msg":"ok","data":{"groups":[{"key":"approved","count":120},{"key":"draft","count":31}], "total":null}}
```

- `kind` 三种（与物化侧现有聚合对齐，不扩）：
  - `count`：`{"kind":"count"}` → `data: {"count": 4312, "total": null}`；
  - `groupCount`：`{"kind":"groupCount","groupBy":"<字段>"}` → `data: {"groups":[{"key","count"}]}`；
  - `groupSum`：`{"kind":"groupSum","groupBy":"<字段>","prop":"<数值字段>"}` → `data: {"groups":[{"key","sum"}]}`；
- filter 语义与 query 完全一致（含权限残差）；不支持聚合或聚合字段的源报 code=40047。

### 2.6 能力矩阵与 schema 反射

`GET {base}/onto-source/schema`（不带 type）：

```json
{
  "code": 0, "msg": "ok",
  "data": {
    "caps": {
      "version": 1,
      "filterOps": ["eq", "ne", "gt", "lt", "ge", "le", "in", "isnull"],
      "pageMax": 100,
      "totalMode": "none",
      "cursor": false,
      "defaultOrder": "pk"
    },
    "resources": [
      {"type": "PurchaseOrder", "name": "采购订单"},
      {"type": "Supplier",     "name": "供应商"}
    ]
  }
}
```

`GET {base}/onto-source/schema?type=PurchaseOrder`：

```json
{
  "code": 0, "msg": "ok",
  "data": {
    "caps": { …同上… },
    "resources": [
      {"type": "PurchaseOrder", "name": "采购订单", "fields": [
        {"name": "po_no",     "baseType": "string",   "sourceType": "varchar(32)",  "comment": "单号"},
        {"name": "amount",    "baseType": "number",   "sourceType": "decimal(18,2)"},
        {"name": "orderDate", "baseType": "datetime", "sourceType": "datetime"},
        {"name": "status",    "baseType": "string",   "sourceType": "varchar(16)"},
        {"name": "lines",     "baseType": "array",    "fields": [
          {"name": "lineNo", "baseType": "number", "sourceType": "int"},
          {"name": "qty",    "baseType": "number", "sourceType": "decimal(18,3)"}
        ]}
      ]}
    ]
  }
}
```

- **caps 五要素**：`filterOps`（算子白名单）、`pageMax`（单页上限）、`totalMode`（exact/estimated/none）、`cursor`（分页协议）、`defaultOrder`（稳定默认序说明，供展示）；
- **baseType 协议基型**五种：`string / number / boolean / datetime / array`；`array` 必须带 `fields` 子清单（明细行结构，单据场景用）；
- caps 是**运行时真相**：本体每次 probe / 绑定校验 / 漂移探测都从 schema 端点拉取为准；`om_data_source.caps` 列只存「上次探测快照」用于列表快速展示（§4.1）。

### 2.7 错误语义

HTTP 层：超时 / 5xx / 连接失败 = 源不可用（本体侧报「数据源不可达」并触发一次 probe 记录）。HTTP 200 + `code != 0` 为业务错误：

| code | 语义 | 本体侧呈现 |
| --- | --- | --- |
| 0 | 成功 | — |
| 40040 | 协议版本不支持 | 「该数据源协议版本过旧，请联系业务系统升级适配器」 |
| 40044 | **不支持的过滤算子**（msg 指明算子与字段） | 「该数据源不支持 contains 过滤（字段 status）」→ explorer 算子收敛的依据 |
| 40045 | 不支持的排序 | 同上句式（M2 orderBy 开放后生效） |
| 40046 | 页宽超限 | 本体侧已 clamp，正常不出现；出现即协议实现缺陷 |
| 40401 | 资源不存在 | 「资源 PurchaseOrder 不存在于该数据源」 |
| 40047 | 不支持的聚合 | 「该数据源不支持按 status 分组统计」 |
| 50000 | 业务系统内部错误 | 透传 msg + 源 id |

业务系统允许使用自有 code 空间（≥50000 段），本体兜底展示 msg。**专用 code 的价值在于本体可以把远端能力缺陷转成用户可懂的精确提示，而不是一串堆栈**。

### 2.8 认证与传输安全

源配置（`om_data_source.config`，api 形态）：

```json
{
  "baseUrl": "http://erp.internal:9000/api/erp/v1",
  "auth": {"mode": "bearer", "tokenEnv": "ONTO_SRC_ERP_TOKEN"},
  "headers": {"X-Org": "hq"},
  "timeoutMs": 8000,
  "qps": 10,
  "maxConcurrent": 4
}
```

- **认证四式**：`none` / `api-key`（`{"mode":"api-key","headerName":"X-API-Key","keyEnv":"…"}`）/ `bearer`（tokenEnv）/ `basic`（userEnv + passwordEnv）。**凭证一律环境变量引用名，不落库不落 git**（新增 env 走 config-sync 技能同步模板与手册）；
- **headers 禁认证类键**：authorization / cookie / x-api-key / api-key / x-auth-token / proxy-authorization（后端校验已实现 source_store.rs:16-18、232-246；前端即时校验见 §4.1）；
- **网络护栏**（复用 outbound.rs 模式，outbound.rs:116-127）：baseUrl host 须过白名单 `onto.source_allow`（env `ONTO_SOURCE_ALLOW`，逗号分隔，支持 `*`，默认 `127.0.0.1,localhost`）；`ONTO_OUTBOUND` 与 `ONTO_VIRTUAL_QUERY` 双总闸任一 off 即拒绝；统一超时（config `onto.api_timeout_secs`，默认 8s）；per-source QPS / 并发限流（tokio Semaphore + 简单令牌桶）。

---

## 三、与 om_source_mapping 的结合（后端设计）

### 3.1 权威行字段对照：零新增列

`om_source_mapping` 行继续是绑定唯一权威（E1）。API 源绑定时各列语义：

| 列 | API 源语义 | 与 PG 源的差异 |
| --- | --- | --- |
| `mode` | `virtual`（恒） | 无差异 |
| `source_id` | 指向 `om_data_source.id`，注册行 **kind='api'** | 仅指向的注册行 kind 不同 |
| `resource` | **API 资源名**（协议 `type`，如 `PurchaseOrder`） | PG 是 `schema.table`；API 是资源标识符，校验规则换为 `^[A-Za-z][A-Za-z0-9_.-]{0,127}$`（替代 `safe_qualified_table` 的「恰一段点号」规则） |
| `key_columns` | 恰 1 列（协议 pk 单值，string 传输） | 无差异（bind 校验本就恰 1） |
| `title_column` | 可选，缺省回填 pk | 无差异 |
| `property_map` | **源字段名 → 属性 apiName**（含嵌套明细行场景：明细行结构**不进映射**，整挂在一个 array 基型属性下，见 §4.5） | 无差异（同构！） |
| `required` | API 虚拟查询不消费（物化灌数校验用），恒空 | PG 直查同样不消费，无差异 |
| `source_db_id` | **无意义，恒空**（api 源不走数据库池） | PG 源的历史双读通道，见 §3.3 |

### 3.2 分派器改造：从「mode 二分」到「mode + kind 三分」

`backend_dispatcher.rs` 现状：`binding_of`(:87-98) 查权威行 → 只按 `mode == Virtual` 二分。改造为：

```
binding_of(def) → 权威行(mode=virtual, source_id)
  ↓ 注册行装载（load om_data_source[source_id]，随绑定行同请求查库，量级小走索引）
  match 注册行.kind:
    "pg"  → ensure_source_pool_ready（池自愈，现状保留）→ PgDirectBackend
    "api" → RestApiBackend::new(注册行.config, caps快照)     // 无池，跳过池自愈
    其他  → 「connector 后端未实装」明确报错
```

- 桥接复用：`resolve_pks`（trait 既有方法）在 RestApiBackend 实现为「pk IN filter + query 下推」，桥接上限 2000 不变（backend_dispatcher.rs:266/:352 的 `bridge_set`/`resolve_virtual_pks` 对两种 backend 通用）；
- `funnel.rs:70-73` 的 `effective_source()` 恒读 `source_db_id`——api 源该值为空时**不再触发池自愈放行歧义**：`ensure_source_pool_ready`（source_handlers.rs:608-633）增加前置判断「注册行 kind=api 直接返回 Ok（无池语义）」；
- 写保护矩阵（E3）天然覆盖 api 源：mode=virtual 的写端点拒绝逻辑与 backend 无关，零改动。

### 3.3 bind 校验的 api 分支（source_handlers.rs:184-314 改造点）

1. **解除硬拒**（:240-245 的 `kind != "pg"` 报错删除），替换为按 kind 分支；
2. **resource 校验**：api 分支用资源标识符 regex（§3.1）；
3. **映射列校验双档**：调 `GET {base}/onto-source/schema?type=<resource>` 拉字段清单——
   - 可达：强校验（映射源字段必须存在于字段清单，类型与属性基型兼容，含 array→嵌套属性校验），同时把字段清单写入 `probe_report` 作**漂移基线**（与 PG 源同机制）；
   - 不可达：**降级为警告保存**（明确 toast「源暂不可达，映射列未经校验」；不同于 PG 源 probe 失败即拒，因为 API 源可能晚于建模上线）。保存后首次查询失败会自动触发 probe（既有机制）；
4. **能力预检**：schema 响应的 `caps.filterOps` 为空集（不含 eq）→ 拒绝绑定（连 eq 都不支持的源没有直查价值）；
5. `upsert_virtual` 落库路径不变（source_query 恒空串）。

### 3.4 probe / schema 的 api 支持（数据源管理 API 面）

| 端点 | api 源行为 |
| --- | --- |
| `POST /data-sources/probe` | 代理 `GET {base}/onto-source/schema`（不带 type）：回显可达、延迟、**caps 实测**、资源数；结果写 `probe_report` / `last_probe_at`，caps 快照写 `caps` 列 |
| `GET /data-sources/schema?sourceId=&resource=` | 代理远端 schema（带 type）：返回 `{columns:[{name, baseType, sourceType, comment, fields?}]}`，**字段名对齐 PG 源响应结构**（columns 同名同义），前端绑定向导零分叉（§4.2） |
| `POST /data-sources/create` | kind=api 的 config 校验：baseUrl 必填合法 URL（http/https）、auth 四式结构、headers 认证键禁入（已有）、timeoutMs/qps/maxConcurrent 数值域 |
| `POST /data-sources/update` | api 源 baseUrl/auth/headers/治理参数可改（无连接池可拆，改完即生效——比 pg 独立源的「改配置=拆池重建」更轻）；id/kind 不可变沿用 |

### 3.5 RestApiBackend 实现要点（新文件 `crates/cmx-onto-app/src/backend_api.rs`）

- 复用 outbound.rs 的共享 reqwest Client + rustls；认证头按 §2.8 注入；
- `BackendCaps::rest_api(caps_json)` 构造器：`algebra = Base|Filter|Static`、`filter_ops = caps.filterOps`、`sortable = false`（E4）、`page_max = caps.pageMax`、`total_mode = caps.totalMode`、`aggregates` 按探测结果；
- 对象集代数 → 协议 filter 的编译器：谓词树遍历骨架复用 backend_pg.rs 的既有遍历（谓词 → 物理列的映射换成谓词 → 源字段名，无 SQL 文本生成）；
- **能力前置校验 fail-closed**：分派器预校验（现状机制）+ backend 二次校验（filter 含 caps 外算子 → 整查询拒绝，错误文案「该数据源不支持 XX 过滤」）；
- 残差编码：PEP 残差 Predicate 折入 filter AND 支路（E7）；残差算子远端不支持 → 整查询拒绝，**绝不拉回内存过滤**；
- 分页双形态适配器（offset / cursor 两套翻页驱动）；totalMode=none 时响应 total 恒丢弃；
- 结构化日志：每次调用记录源 id / 资源 / filter 摘要 / 行数 / 耗时；慢调用（>2s）告警日志——与 PG 直查同一观测格式。

---

## 四、前端交互设计（本方案主体）

> 落点真源：`backend/cmx-container/assets/onto/web/ui-native/`（sources.js / studio-next/ / explorer.js，均为 native-page JS 模块）。改造后须 `./scripts/publish-assets.sh onto` 同步。双主题通路（UI5 + Neo）零硬编码色值（根 AGENTS.md §四.5），徽章/状态色一律 `var(--sap*, fallback)` 派生。

### 4.0 建模者全旅程（交互主线叙事）

```
业务系统开发者          平台超管/建模者                    建模者                      业务用户
─────────────         ──────────────────               ─────────                  ─────────
挂适配 crate           数据源管理页                       studio-next                explorer
(或自实现协议)          新建 → 选 REST API                建类型/后补绑定             浏览·过滤·钻取
  ↓                    填端点+认证+治理                  选 API 源 → 选资源          「直查·API」徽章
提供 baseUrl           测试连接                          字段反射导入 → 绑定          算子按能力收敛
+ 能力矩阵              (caps+资源清单回显)                (能力 chips 上卡)           单据明细子表
```

四个角色的体验闭环，缺任何一环都说不出「单据实例留业务库」的完整故事。

### 4.1 数据源管理页（sources.js 改造）

#### 4.1.1 新建向导：加类型选择步

现状 dlgDraft 硬编码 `kind:'pg'`（L454-457）。改造为向导第一步**类型三卡**：

```
┌ 新建数据源 ────────────────────────────────────────────┐
│  第 1 步 · 选择类型                                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐   │
│  │ PostgreSQL   │ │  REST API    │ │   连接器      │   │
│  │   ⛁          │ │   ⇄          │ │   ⚌ (灰)     │   │
│  │ 直连业务库     │ │ 业务系统适配   │ │ ES/文件/MQ    │   │
│  │ 查询下推       │ │ JSON查询协议  │ │ 敬请期待      │   │
│  └──────────────┘ └──────────────┘ └──────────────┘   │
└────────────────────────────────────────────────────────┘
```

- 三卡单选，选「连接器」置灰不可点（tooltip「M3 规划中」）；选卡后进入第 2 步分类型表单（pg 表单 = 现有八字段原样搬迁，体验零变化）；
- 列表页空态 hero 与新建按钮入口同步更新文案（现状只提 PostgreSQL，L276）。

#### 4.1.2 API 源表单（第 2 步，四分组）

```
┌ 新建数据源（REST API） ─────────────────────────────────┐
│ ① 基本信息                                              │
│   数据源 id* [erp-api        ]  显示名* [ERP 订单中心    ] │
│ ② 端点与认证                                             │
│   baseUrl* [http://erp.internal:9000/api/erp/v1        ] │
│   认证方式  [Bearer ▾]   Token 环境变量* [ONTO_SRC_ERP_TOKEN]│
│   附加 headers  [X-Org]-[hq] [＋ 添加]                    │
│      ↳ 输入 Authorization 等认证键 → 即时红字禁入提示       │
│ ③ 分页与治理                                             │
│   分页协议  (●) offset  ( ) cursor                        │
│   超时 ms [8000]  QPS 上限 [10]  最大并发 [4]              │
│ ④ 能力矩阵（可留空，测试连接后自动回填实测值）                │
│   过滤算子  [eq✓][ne✓][gt][lt][ge][le][in✓][contains][isnull✓] │
│   单页上限 [100]  total 口径 [不给总数 ▾]  默认稳定序 [pk  ] │
│                                                          │
│   [ 测试连接 ]                        [取消] [保存]        │
└────────────────────────────────────────────────────────┘
```

交互细节：

- **认证方式联动**：none 无附加输入；api-key 出 headerName+keyEnv 两框；bearer 出 tokenEnv；basic 出 userEnv+passwordEnv。所有 env 引用名输入框带统一 placeholder「环境变量名（不收明文）」+ 链接「如何配置 →」指向 ENV_MANUAL 锚点；
- **headers 键值编辑器**：动态行；键名输入即时校验，命中认证类键（§2.8 清单）→ 该行红框 + 行下提示「认证类 header 请走上方认证配置」；保存时后端二次校验兜底（已实现）；
- **能力矩阵四件**：算子用可多选 chips（选中态实心）；total 口径下拉三选（不给总数 / 精确 / 估算，**默认不给**——大表 count 代价归业务系统自决，前端默认不引诱用户选精确）；**整组可留空**——留空时保存前若未测试连接给黄牌提示「未声明能力，建议先测试连接以实测回填」；
- 分页协议选 cursor 时表单内嵌说明文案「cursor 源须保证页间主键不重不漏，适合高频写入的数据」。

#### 4.1.3 测试连接（probe）结果卡：API 源的「先测后存」体验

```
┌ 测试结果 ──────────────────────────────────────────────┐
│  ✓ 可达 · 236ms · 12 个资源                              │
│  能力实测：eq ne in isnull · 页宽100 · total 不给 · offset │
│  ⚠ 与声明不一致：声明含 contains，实测不支持                │
│  资源：PurchaseOrder(采购订单) · Supplier(供应商) · +10    │
└────────────────────────────────────────────────────────┘
```

- 数据来自 `POST /data-sources/probe` 代理远端 schema（§3.4）；失败红卡给具体原因（超时 / 401 认证失败 / DNS 不可达 / 协议版本过旧 40040），保存按钮保持可点但带二次确认「源未通过测试，确认保存？」（对齐 pg 源「先测后存不强锁」的既有口径，US-012）；
- **声明 vs 实测差异黄牌**：caps 声明（表单④）与 schema 返回实测不一致时逐项黄牌列出，点「以实测为准」一键回填表单——消除「声明写错 → 运行期才发现不支持」的坑（PRD US-022 验收 3）；
- 探测成功即把 caps 快照与资源清单写入 `probe_report` / `caps` 列，列表页据此显示健康徽章与最近探测时间（现状列已有，数据源换成 api 语义）。

#### 4.1.4 列表与编辑

- 列表「类型」列徽章：pg（现状绿）/ **api（新增，蓝色 `var(--sapInfobarBackground)` 系）**/ connector（灰，预留）；「连接」列 api 源显示 `baseUrl` 的 host:port + 路径摘要（现状 `cfgText` 只拼 host:port/db，api 分支改拼 baseUrl）；
- 行操作沿用：编辑 / 测试连接 / 源结构（api 源 = 资源清单+字段浏览，数据源换成 schema 代理返回）/ 删除；
- 编辑弹窗：api 源 baseUrl、认证、headers、治理、能力声明**全部可改**（无池可拆，改完即生效——比 pg 独立源轻；提示文案「保存后立即生效」）；id/kind 不可变沿用（改类型 = 删源重建）；
- 「源结构」弹窗（现状 schemaDialog L558-593）api 源形态：左侧资源列表（schema resources），右侧选中资源的字段表（name / baseType / sourceType / comment，array 字段可展开嵌套 fields）。

### 4.2 studio-next 绑定向导（runtime.js / inspector.js 改造）

#### 4.2.1 选源：去掉 pg 硬过滤

`openDsSourceWizard`（runtime.js:1197）与 `newObjectDialog` 数据来源下拉（L1585-1714）两处 `kind==='pg' && status==='active'` 过滤放开为 `status==='active'`（api 源以「API」徽章 + 名称后缀「· API 源」列出）；toml db_id 手填输入框**仅 pg 模式向导保留**（api 源必须走注册行——API 源没有 toml 池概念），virtual 向导 api 分支隐藏该输入框。

闸门行为不变：`onto.virtual_query` / `onto.authz_mode` 任一未放行 → API 源同样禁选并提示（列表接口已返回 `virtualQueryEnabled` / `authzMode`，现状机制复用）。

#### 4.2.2 「源表」→「资源」：反射链路零分叉

- pg 向导的「源表」输入框（手填 schema.table），API 向导换成**资源下拉**：数据来自 `GET /data-sources/schema?sourceId=<id>`（不带 resource 的资源清单形态，§3.4 代理）→ 下拉项 `PurchaseOrder · 采购订单`；
- 「读取源结构」按钮（`dsLoadSchema` L1372 / `nwLoadSchema` L1716）调用不变——**后端 `/data-sources/schema` 对 api 源返回与 pg 源同构的 columns 结构**（§3.4 对齐设计），前端反射导入逻辑（camelCase 属性生成 + `pgTypeToBase` 类型推断 + pk/title 预填）复用，仅类型映射表增加协议基型分支：`string→String / number→Double|Long（整数推断）/ boolean→Boolean / datetime→DateTime / array→嵌套属性组`；
- array 字段反射：生成一个 array 基型属性（如 `lines`），嵌套 fields 生成**子属性清单挂在该属性的定义里**（对象类型属性支持嵌套结构——单据场景，见 §4.5）；

#### 4.2.3 映射行表格与校验

- 映射行表格（源字段 ↔ 属性，勾选映射 / 下拉映射既有属性 / ＋新增属性）完全复用；array 字段行显示「明细行 · N 列」徽章，映射粒度 = 整体一行（不展开行内字段逐列映射——明细行结构由业务系统组装，本体不拆）；
- beforeOk 校验（L1276-1298）api 分支：resource 必选（下拉强制）、主键恰 1 列、标题列可选——与 pg 相同；**新增软校验**：若源 schema 可达而所选算子…（无此环节，能力预检在绑定卡呈现，见下）；
- 提交仍走 `POST /object-types/datasource/bind`（请求结构不变，后端 api 分支 §3.3）。

#### 4.2.4 Inspector「数据映射」卡：API 能力上卡

`dsCapsHtml`（inspector.js:1691）现状能力 chips 是 PgDirect 固定口径（✓直查/过滤/聚合下推、桥接≤2000，✘写入/全量同步/SSE）。改造为**按源 kind 与 caps 快照动态生成**：

```
┌ 数据映射 ──────────────────────────────────────────────┐
│  虚拟直查 · ERP 订单中心 (api)                            │
│  资源 PurchaseOrder · 主键 po_no · 标题 po_no · 映射 14 列 │
│  [✓ 实时直查] [✓ 过滤 eq·ne·in·isnull] [✓ 聚合 分组统计]   │
│  [✗ contains 过滤] [✗ 写入] [✗ 全量同步] [✗ 实时推送]      │
│  漂移探测：2026-09-20 10:32 一致 · [探测漂移] [切换绑定]…  │
└────────────────────────────────────────────────────────┘
```

- 过滤 chip 的算子清单来自 `probe_report.caps.filterOps`——**建模者一眼看到哪些算子在 explorer 里可用**（✗ 的算子到 explorer 会被禁用，见 §4.3）；
- 聚合 chip 按 caps 声明显示（不支持聚合的源显示 ✗聚合）；桥接 ≤2000 chip 不变；
- 漂移探测（dsProbe）对 api 源 = 比对 schema 字段清单与绑定映射（远端改字段名/删字段 → 漂移报告，与 pg 同机制，基线来自 bind 时的 probe_report）。

### 4.3 explorer 对象浏览器（explorer.js 改造）

1. **徽章区分**：`isVirtualType`（L180）判据不变（mode=virtual），徽章文案按源 kind 分「直查」（pg）与「直查·API」（api）——`loadTypeDetail` 已补拉绑定摘要（L198-203），摘要响应增加 `sourceKind` 字段即可区分；对象列表头的提示文案 api 源为「实时读业务系统 · 手动刷新」；
2. **过滤算子按能力收敛**（新增，对应 PRD US-024）：过滤构造器（L377-381 一带）的算子下拉按 `binding.caps.filterOps` 过滤——未支持算子禁用 + option 后缀「· 源不支持」；整列字段都不支持任何算子时该字段不可选为过滤字段；**能力外查询绝不发出**（前端收敛 + 后端 fail-closed 双保险）；
3. **total 口径**（对应 US-025 的 total 面）：`totalMode=none` 的源，列表页脚不显示「共 N 条」，改显示「已加载 50 行 · 继续加载更多」（hasMore 驱动）；`estimated` 显示「约 N 条」（弱化样式）；`exact` 正常显示——三种呈现让业务用户对数字的可信度有正确预期；
4. **未映射属性置灰**（L432-437 / L551）机制不变，api 源天然继承；
5. **单据明细子表**：见 §4.5。

### 4.4 建类型向导「数据来源」步骤（newObjectDialog）

数据来源下拉（L1609）放开 kind 过滤后 api 源可选；「读取源结构并导入字段」（nwLoadSchema）走 §4.2.2 同一反射链路；建型后自动 bind（L1698-1699）不变。**建模者从「建类型」到「看到真数据」的路径与 pg 源完全一致**——这是「API 是一种数据源」在体验层面的最终兑现。

### 4.5 单据（头+行）虚拟化：协议、映射与呈现约定

母方案 D7：单据虚拟化 = M2 API 适配示范（业务侧组装嵌套 props，PG 平面映射覆盖不了头+行）。三方约定：

**① 协议侧**（§2.4 已定）：props 中嵌套数组 = 明细行，数组元素为同构 object，字段结构在 schema 的 array 字段 `fields` 中声明。

**② 映射侧**：头表字段逐列映射到属性（同平面表）；明细行整挂一个 array 基型属性（如 `lines`），**行内字段不逐列映射**——行结构以 schema 声明为准，展示端按声明渲染。这样 `property_map` 保持平面语义，不为嵌套结构加复杂度。

**③ 呈现侧**（explorer 对象详情）：

```
┌ 采购订单 PO-2026-0001 ───────── 「直查·API」只读 ───────┐
│  状态 approved    金额 12,500.50    供应商 华中钢铁        │
│  ┌ 明细行 (2) ────────────────────────── [展开 ▾] ────┐  │
│  │ 行号  物料编码  物料名称        数量   单价      金额 │  │
│  │  1    M-001    螺纹钢 HRB400   100   3,800.00  …   │  │
│  │  2    M-014    高线 HPB300     250   3,650.00  …   │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

- 详情面板识别 array 基型属性 → 渲染为可折叠子表（列 = schema fields 声明顺序，列名取字段 comment ?? name）；
- 明细行字段**不参与过滤/排序/聚合下推**（协议 v1 filter 只打头表字段）——过滤构造器中明细字段不可选，悬停提示「明细行字段暂不支持过滤」；这与 PRD US-023 验收 3 对齐（「按明细字段过滤按能力矩阵提示」——v1 统一收敛为不支持，M3 若协议扩展再开）；
- 明细行不进对象集列表的列选择（列表只呈现头表标量字段）。

### 4.6 交互文案与双主题红线

- 所有错误文案遵守「一句现状 + 一句出路」格式（对齐 US-005 文案纪律）：如「该类型为虚拟直查（数据在源系统），如需变更请通过动作/流程」；API 源特有：「该数据源不支持 contains 过滤（字段 status）」；
- 徽章/状态/黄牌红牌全部 `var(--sap*, fallback)` 派生色，Neo 皮肤接 `data-cmx-skin` / `data-cmx-skin-tone`（真源：技能 cmx-components-guide → references/neo-theme-onboarding.md）；
- 虚拟类型无 SSE 实时推送的轻提示文案，api 源沿用（「实时读源 · 手动刷新」）。

---

## 五、业务系统接入配套（协议 + 适配 crate + conformance 套件）

用户已拍板全档投入。三件套的关系：**协议规范是契约真源，适配 crate 是 CMX 系技术栈的「挂上即合规」实现，conformance 套件是对任意实现（含自定义）的合规自测**。

### 5.1 协议规范文档

- 落点：`backend/cmx-ontology/docs/20260920_cmx-ontology_本体数据源API查询协议v1.md`（随 M2a 实施）；
- 内容 = 本方案 §二 全文 + 请求/响应 JSON Schema（可机读）+ 错误码表 + 接入自查清单；
- 面向两类读者：CMX 业务系统开发者（优先读 §5.2 直接挂 crate）、外部系统开发者（按协议自实现）。

### 5.2 CMX 通用适配参考实现（cmx-container 新 crate）

- 建议落点：`backend/cmx-container/crates/libs/cmx-onto-source-adapter/`（crate 名 `cmx-onto-source-adapter`；跨仓引用走 path，符合「公用库进 container」惯例）；
- 形态：**axum Router + 声明式映射**，业务系统三行接入：

```rust
// 业务系统 main.rs 内挂载
let source = OntoSourceAdapter::new(pool)
    .resource(ResourceMapping {
        r#type: "PurchaseOrder",
        table: "po_header",
        pk: "po_no",
        title: "po_no",
        fields: &["po_no", "status", "amount", "supplier", "order_date"],
        detail: Some(DetailMapping { field: "lines", table: "po_line",
                                     fk: "po_no", fields: &[..]}),   // 单据头+行组装
        row_guard: Some(|ctx| FilterNode::eq("org_code", ctx.org())), // 业务自身权限叠加
        caps: Caps::default(),        // filterOps 默认全量，totalMode 默认 none
    })
    .resource(ResourceMapping { r#type: "Supplier", .. });
app.merge(source.router());            // 暴露 /onto-source/{query,aggregate,schema}
```

- 内部实现：结构化 filter（协议叶子/组合节点）→ modql FilterGroups → `TryFrom<FilterGroups> for sea_query::Condition` 参数化 SQL（复用 `crates/libs/modql`，零手写 SQL 拼接）；明细行 = 头表分页后按 fk 批量取行、内存组装嵌套数组；
- **row_guard 钩子**：业务系统注入自身行级/租户权限（与本体下推的权限残差 AND 叠加，双保险）；
- 交付要求：下游仓验证（根 AGENTS §六.4——主应用 cmx-portalservice + 至少一个引擎各跑 `cargo check`，因 container 公用库新增 crate）；
- 明确边界：适配 crate 只覆盖「表 → 协议」的标准形态；ES / 自定义查询引擎 / 视图聚合等复杂系统按协议自行实现（参考 crate 源码即示例）。

### 5.3 conformance 测试套件

- 形态：适配 crate 内 `tests/conformance.rs`（对 crate 自身）+ 独立 bin `cmx-onto-source-conformance`（对任意 baseUrl 跑：`cmx-onto-source-conformance http://erp:9000/api/erp/v1 --token-env ONTO_SRC_ERP_TOKEN`）；
- 用例矩阵：信封合规（code/msg/data）、三端点可达、filter 全算子往返（构造已知数据断言过滤正确性——**正确性而不只是不报错**）、分页双形态页间不重不漏、total 三档口径、错误码语义（不支持的算子必须报 40044 而非静默全量——**反向断言：发了 contains 过滤，若返回行数等于全量则 FAIL**）、caps 与实测一致、schema 字段与数据自洽（items 字段 ⊆ schema 声明）；
- 接入流程约定（写入协议文档）：**conformance 全绿才允许生产对接**（PRD US-021 验收 2）。

---

## 六、实施分期与验收

### 6.1 分期（依赖序：协议 → 后端 → 前端 → 配套）

| 期 | 内容 | 估时 | 验收口径（对齐 PRD） |
| --- | --- | --- | --- |
| **M2a 后端协议闭环** | RestApiBackend（backend_api.rs）+ BackendCaps::rest_api + 分派器 kind 三分 + bind api 分支（含 schema 强/降级校验、能力预检）+ probe/schema 代理 + outbound 护栏（onto.source_allow / api_timeout_secs / 限流）+ 结构化日志 + e2e | 8~10 人日 | curl 全链路：注册 api 源 → probe 回显 caps → bind → object-sets/load 下推（日志可见远端调用与耗时）；能力外查询 4xx 精确文案；残差编码进 filter（抓包可验）；virtual 写端点 4xx；存量 e2e 全绿 |
| **M2b 前端三件** | sources.js 类型选择步 + API 表单 + probe 结果卡；studio-next 两处去 pg 过滤 + 资源下拉 + 反射类型映射 + 能力 chips；explorer 徽章区分 + 算子收敛 + total 三态 | 8~10 人日 | US-022/023/024/025 全部验收标准；pg 源全流程回归零变化 |
| **M2c 配套与示范** | 协议规范文档 + 适配 crate + conformance 套件 + 下游仓 cargo check + fico（或独立演示系统）经适配 crate 示范接入 + **单据头+行示范**（业务侧组装嵌套 props + explorer 明细子表）+ 接口清单/技能文档补账 | 6~8 人日 | conformance 对示范系统全绿；explorer 浏览单据类型（列表分页 + 详情明细行展开 + 头表字段过滤下推）；US-021 验收 |

### 6.2 存量零回归红线

- 未绑定与 pg 绑定对象类型的全部行为零变化（存量 e2e 全绿为准出，母方案口径延续）；
- pg 源新建/编辑/绑定向导的表单字段与流程**原样搬迁不重构**（类型选择步是纯增量）；
- 数据源管理页列表对 connector kind 的展示兼容（现状已渲染 warn 色徽章，不动）。

### 6.3 文档 / 技能 / 配置补账清单（M2c 收口项）

| 项 | 内容 |
| --- | --- |
| 接口规范 | `documents/20260918_cmx-ontology_全量接口清单与请求参数说明.md` 补 data-sources 专节（M1b 六端点欠账）+ bind api 分支说明 + 协议 v1 摘要 |
| 协议文档 | §5.1 落地 `backend/cmx-ontology/docs/` |
| config-sync | 新配置项：`onto.source_allow` / `onto.api_timeout_secs`（env：ONTO_SOURCE_ALLOW 等）+ 凭证 env 示例 → 同步 config_template.toml / .env.template / CONFIG_MANUAL.md / ENV_MANUAL.md |
| 技能 cmx-onto-toolkit | scenario-spec 的 `datasourceBind` 段支持 api 源（sourceId 指向 api 注册行 + resource=资源名）；onto_seed.py 兼容验证；演示叙事锚更新（「单据实例留业务库」自此有真实含义） |
| 演示环境 | cmx-onto-toolkit 预配一个挂适配 crate 的演示业务系统（可复用 fico 库 + 适配 crate 起 demo bin），保证 API 源演示可复现 |

---

## 七、风险与开放问题

| # | 风险 | 等级 | 应对 |
| --- | --- | --- | --- |
| A1 | 业务系统静默忽略 filter（全量返回）→ 数据越权 + 性能灾难 | **高** | conformance 反向断言（§5.3）；运行期护栏：单次响应行数 > pageMax 即断连报错；残差编码 + 探测抽测 |
| A2 | 残差算子远端不支持 → 整查询拒绝，业务用户困惑 | 中 | 错误文案指明「权限过滤所需能力源不支持，联系管理员」；绑定时的能力预检提前暴露（§3.3-4） |
| A3 | cursor 分页实现错误导致页间重/漏 | 中 | conformance 页间不重不漏断言；优先引导 offset + defaultOrder |
| A4 | 深分页 offset 性能退化 | 中 | 协议文档明示 offset 源建议 pageMax 内浅翻页 + 长列表引导 cursor；本体侧不做自动深翻页 |
| A5 | 适配 crate 成为新的跨仓维护面 | 低 | 走 container 公用库流程（下游 cargo check 纪律）；协议版本字段防漂移 |
| A6 | api 源慢/不可用拖累浏览体验 | 中 | 超时 + per-source 限流 + 慢调用告警 + ONTO_VIRTUAL_QUERY 总闸止血（母方案 R2 同源应对） |
| A7 | 明细行字段不可过滤的预期落差 | 低 | UI 明示（悬停提示）+ 协议文档能力边界声明；M3 评估协议扩展 |

**开放问题**：

| # | 问题 | 倾向 |
| --- | --- | --- |
| Q-A1 | 适配 crate 命名与落位（cmx-onto-source-adapter） | 实施时定，建议如上 |
| Q-A2 | orderBy 是否随 M2a 协议一并实装（母方案归 M2） | 协议字段先定稿、实装随 M2b/M2c 之间按余量插入；不阻塞主线 |
| Q-A3 | deep_get 端点（POST /objects/get）是否仍随 M2 交付 | 维持母方案口径（M2 交付），优先级低于主线，可滑 M2c 尾部 |
| Q-A4 | 演示业务系统选型（复用 fico 库 vs 独立 demo bin） | 倾向 fico 库 + 适配 crate demo bin（不侵入 fico 服务本身） |

---

## 附录 A：API 物化拉取（M3 规划草案，本期不实施）

场景：源数据量大 / 源不稳定 / 需要稳定快照与全量聚合时，虚拟直查不合适，需要「从 API 定期拉取物化到本地 oo_ 表」。草图：

- 漏斗 funnel 的 reader 抽象化：现有「PG SQL 读源」与新增「API 分页遍历读源」实现同一 trait（`query_source_readonly` 泛化为 `SourceReader`）；API reader = 按 query 协议 cursor/offset 全量遍历 + 本地 upsert + 隔离区（复用 map_row 校验内核）；
- `om_source_mapping.mode` 增第三值 `virtual_api_sync`（或独立 `sync_source` 段，实施时定）；调度依赖 T1（平台缺口）先行；
- 与虚拟直查共存：同一 api 源既可被虚拟绑定也可被物化映射（不同对象类型各自选择）；
- 风险预告：全量遍历对业务系统的压力（限流 + 增量水位 M3 一并考虑）。

## 附录 B：本方案不重复母方案已定事项索引

D2（PG 直连边界）/ D3（统一 trait）/ D7（单据走 API 适配）/ E1（mapping 唯一权威）/ E3（写保护矩阵）/ E4（排序固定）/ E7（残差编码禁内存过滤）——均直接沿用，见母方案 §三。工作量合计：M2a + M2b + M2c ≈ 22~28 人日（与母方案 M2 估算 12~15 + 跨仓 1~2 相比上浮，因本方案把前端交互与配套三件套细化进了主线）。

## 附录 C：实施记录与方案差异（2026-09-20 M2a/M2b 落地）

**已交付**（本表为实施真源，与上文有出入处以本表为准）：

| 层 | 落点 | 内容 |
| --- | --- | --- |
| 契约 | `cmx-onto-model/src/backend.rs` | `ApiSourceCaps`（协议 caps 五要素 + normalize/fallback）+ `BackendCaps::rest_api()` |
| 后端 | `cmx-onto-app/src/backend_api.rs`（新） | RestApiBackend：协议客户端（query/aggregate/schema 代理）、对象集→JSON filter 编译、能力矩阵 fail-closed、认证四式（凭证请求时刻注入）、per-source 并发闸 + QPS 滑窗、结构化日志 + 慢查询告警；单测 6 个 |
| 分派 | `backend_dispatcher.rs` | 「mode 二分」→「mode + kind 三分」（pg/api/connector + 停用明确报错）；`binding_summary` 增 sourceKind/sourceName/sourceStatus/apiCaps |
| 绑定 | `source_handlers.rs` | bind api 分支：资源名标识符校验、schema 强校验（映射列存在）/**不可达降级警告保存**、能力预检（无 eq 拒绑）、**cursor 分页源拒绑**、漂移基线落库；probe/schema 代理（pg 同构 columns 双形态）；update api 源无池语义 |
| 校验 | `cmx-onto-store-pg/src/source_store.rs` | api config 校验增强：baseUrl http(s) 前缀、auth 四式结构（凭证 env 引用必填）、治理参数数值域、headers 认证键禁入（已有） |
| 护栏 | `backend_api.rs` + `outbound.rs` | `onto.source_allow`（env `ONTO_SOURCE_ALLOW`，默认仅本机）host 白名单 + `ONTO_OUTBOUND` 总闸 + 每请求超时（`onto.api_timeout_secs` 缺省 8s，源 config.timeoutMs 优先） |
| 前端 | `sources.js` | 新建向导类型三卡（pg/api/connector 置灰）；API 四分组表单（认证联动/headers 编辑器认证键即时红牌/能力声明 chips）；probe 结果卡（实测 caps + 资源清单 + **声明差异黄牌 + 以实测为准**）；编辑双类型；列表 REST API 徽章 + baseUrl 列；源结构弹框资源联想 |
| 前端 | `studio-next/runtime.js` | 绑定向导/建型向导放开 api 源（·API 标注）；资源名留空 → 资源清单点选；协议基型映射（`apiBaseToOnto`，array=明细行整挂）；bind 降级警告 toast 透出；API 源禁 toml db_id 混填校验 |
| 前端 | `studio-next/inspector.js` | 数据映射卡「虚拟直查 · API」徽章 + **能力 chips 按 caps 快照动态生成**（过滤算子枚举/聚合/页宽/total/桥接） |
| 前端 | `explorer.js` | 「直查·API」徽章 + 「实时读业务系统」提示；**过滤算子按 caps.filterOps 收敛**（不含即不出现在下拉）；array 属性「明细行不支持过滤」禁用；**total 三态**（none=已加载 N 行 / estimated=约 N / exact=共 N，none 不发 count 聚合）；**详情明细行子表**（array 属性折叠表格） |
| 配套 | `test/e2e/_onto_source_demo.py`（新） | 协议 v1 演示适配器（采购订单头+明细行 + 供应商；caps 无 contains 用于 fail-closed 演示） |
| 配套 | `test/e2e/virtual_api_source.sh`（新） | API 源 e2e 全链路 37 断言 |
| 配置 | config-sync | `onto.source_allow` / `onto.api_timeout_secs` → config_template.toml + CONFIG_MANUAL.md + onto-server-{dev,test}.toml 注释示例 |

**与方案正文的差异（3 处，均为实施中的修正决策）**：

1. **协议 filter 支持 `not` 节点**（§2.3 原文只有 and/or）：残差策略含 `Not` 谓词时若拒绝会使该类型整体不可查——协议 v1 收录 `{"not": <node>}`，演示适配器与通用适配实现均支持。
2. **caps 快照优先级 = 实测 > 声明**（§4.1.2 表单④原设计为「本地声明」）：运行期真相同意为「远端实测（probe/bind 时落 `probe_report.caps`）优先于 `caps` 列本地声明，声明仅作未探测兜底」——消除「声明写错 → 运行期才发现」的窗口（与 §4.1.3 黄牌设计同目标）。
3. **cursor 分页源 bind 时拒绝**（§2.3/§4.1.2 将分页协议列为源配置项）：实施中 cursor 由**远端 caps 声明**（非本地配置）；因本体 `Page` 仅有 offset 语义、cursor 翻页需跨请求状态，M2 在 bind 时 fail-fast 拒绑并给出生路文案（业务系统声明 `caps.cursor=false`）。

**验证记录**：cargo check/clippy 零告警；cmx-onto-app + cmx-onto-store-pg lib 测试 45 全绿；`virtual_api_source.sh` e2e 37/37（注册拒绝面/probe 实测/schema 双形态/bind 强校验/下推过滤/静态 pk/分页/能力 fail-closed/聚合/写保护）；`qa-backend.sh` 41/42（唯一失败为并行会话「修订去重」未提交改动所致的存量断言，与本特性无关）；UI 实测（IAB 浏览器）：数据源管理页类型三卡/API 表单/认证键红牌/probe 结果卡/以实测为准回填保存、studio-next Inspector「虚拟直查 · API」+ 动态能力 chips、explorer 徽章/算子收敛（无 contains）/lines 明细行禁过滤标注/total 三态/status=approved 下推 4 行/明细子表、暗色变量组注入下两页整体翻转无硬编码残留。

**遗留（非阻塞）**：M2c 适配 crate + conformance 套件（§5.2/§5.3，cmx-container 侧）与 fico 示范接入未动工；orderBy 协议字段已定稿未实装（§七 Q-A2 口径）；studio-next 元素目录查询偶发骨架屏不加载（既有问题，与本特性无关）。
