# 单据 / 字典通用后台接口（DCT / DOC API）

> 何时读：页面需要加载字典/单据**数据**或**元数据**时（L3 及任何调后端取业务数据的场景）。
> 区别于 `model-dct-doc-meta.md`：那个讲 **CmxDCTMeta/CmxDOCMeta 模型组件**怎么配；本文件讲**后端 HTTP 接口**怎么调、参数怎么传、有哪些真实页面案例。

---

## 总览：两条数据线

| 线 | 用途 | 核心接口 |
| --- | --- | --- |
| **DCT（数据字典）** | 装载"可选项"数据（科目、客户、币种…） + 字典显示元数据 | `/api/dct/meta` + `/api/dct/data/search` |
| **DOC（业务单据）** | 装载/回存单据数据（凭证、订单…） + 单据显示元数据（层序+列） | `/api/doc/meta` + `/api/doc/data/*` + `/api/doc/save` |

> 另有 `/api/definitions/config`（kind=DCT/DOC/BASE）——加载**定义 JSON 本身**（结构定义文件），由 `CmxDCTMeta`/`CmxDOCMeta` 模型组件调用（见 `model-dct-doc-meta.md`）。本文件讲的是**业务数据接口**，不是定义文件接口。

---

## 一、DCT 数据字典接口

### 1.1 `GET /api/dct/meta` —— 字典显示元数据

返回某张字典表的列定义（caption/类型/PK/是否自分级），供前端构造列模型。

**Query 参数**（`DctQuery`，源码 `cmx-model/crates/cmx-model-app/src/handlers/dct.rs`，模型中心独立仓）：

| 参数 | 必填 | 含义 |
| --- | --- | --- |
| `domain` | 是 | 业务域，如 `fi` |
| `application` | 是 | 应用，如 `cmxfico` |
| `module` | 是 | 模块，如 `gl` |
| `dict` | 是 | 字典表 dictCode，如 `currency` / `gl_account` / `bus_partner` |
| `file` | 否 | 定义文件名；缺失时自动扫描含该 dictCode 的 DCT 文件（优先 isDefault，回退最高版本） |

**响应 `data`**（源码 `cmx-model/crates/cmx-model-app/src/handlers/dct.rs`）：
```jsonc
{
  "dictCode": "gl_account",
  "dictName": "会计科目",
  "tableName": "gl_account",
  "idField": "id",
  "codeField": "code",
  "labelField": "name",
  "parentField": "parent_id",      // 自分级字典才有
  "selfHierarchy": true,            // 是否自分级（树形）
  "pk": "id",
  "columns": [
    {
      "name": "code", "caption": "编码", "dataType": "VARCHAR",
      "isPrimaryKey": false, "nullable": false,
      "dimType": "dimension",       // 有值才输出
      "refDict": "currency",        // 引用别的字典（有值才输出）
      "edit": {...}, "display": {...}  // 编辑/显示设置（有值才输出）
    }
  ]
}
```

**用法**：前端据 `columns` 动态构造 `CmxColumnModel`（见案例 `doc-loader.js` 的 `buildColumnModel`）。

### 1.2 `POST /api/dct/data/search` —— 装载字典数据

**Query**：同 1.1 的 `DctQuery`（domain/application/module/dict[/file]）。

**请求体**（`DctSearchBody`，源码 `cmx-model/crates/cmx-model-app/src/handlers/dct.rs`）：

```jsonc
{
  "parentId": null,                 // 自分级：按 parentField 过滤；null=根级；不传键=不过滤
  "filters": { "status": "active" },// 简单等值过滤 {col: value}
  "q": "应收",                       // 关键字（对 code/label 模糊）
  "page": 1,
  "pageSize": 50
}
```

**响应 `data`**：`{ rows: [...], total, page, pageSize }`

**curl 示例**：
```bash
curl -X POST 'http://localhost:8080/api/dct/data/search?domain=fi&application=cmxfico&module=gl&dict=gl_account' \
  -H 'Content-Type: application/json' \
  -d '{"q":"应收","page":1,"pageSize":20}'
```

### 1.3 `POST /api/dct/entries` —— 回存字典条目（upsert，merge 语义）

参数同 1.1（Query）+ body `{ entries: [{ id?, code, name, ... }, ...] }`。响应 `{ ok, upserted, errors? }`。

### 1.4 `DELETE /api/dct/entries/{id}` —— 删除字典条目

Path 参数 `id`。

---

## 二、DOC 业务单据接口

### 2.1 `GET /api/doc/meta` —— 单据显示元数据（层序 + 列 + 父子关系）

返回单据的 N 层结构（L1..LN），每层带列定义，附父子关系。**通用单据前端页据此端点动态构建 N 层主从 schema + 各层 grid 列头**。

**Query 参数**（`DocDataQuery`，源码 `cmx-model/crates/cmx-model-app/src/handlers/doc.rs`）：

| 参数 | 必填 | 含义 |
| --- | --- | --- |
| `domain` | 是 | 业务域 |
| `application` | 是 | 应用 |
| `module` | 是 | 模块 |
| `file` | 否 | 单据定义文件名（如 `cmxfico_doc_meta_v1.json`）；缺失自动选默认/最高版本 |
| `doc` | 否 | 单据模块编码（`moduleMeta.moduleCode`）；有值时按 `moduleCode` 精确定位 |
| `filter` | 否 | 根层 `col:value` 简单等值 |
| `limit` | 否 | 根层限制行数 |
| `depth` | 否 | 装载深度（懒下钻） |

**响应 `data`**（源码 `cmx-model/crates/cmx-model-app/src/handlers/doc.rs`）：
```jsonc
{
  "layers": [
    {
      "id": "cv_batch", "tableName": "cv_batch", "level": 1, "levelName": "凭证批",
      "columns": [
        { "name":"doc_no", "caption":"凭证批号", "dataType":"VARCHAR", "isPrimaryKey":true, "dimType":"dimension", "agg":"", "nullable":false }
      ],
      "summaries": [...],            // 本表汇总表（sum 表）
      "aggFields": [...]             // 聚合字段
    },
    { "id":"cv_header", "level":2, "levelName":"凭证头", "columns":[...] },
    { "id":"cv_acc_line", "level":3, ... },
    { "id":"cv_aux_line", "level":4, ... }
  ],
  "layerGroups": [ { "level":4, "levelName":"辅助核算", "tableIds":["cv_aux_line","cv_cyzb_line"] } ],
  "relations": [
    { "parent":"cv_batch", "child":"cv_header",   "parentKey":"id", "childKey":"upper_id" },
    { "parent":"cv_header","child":"cv_acc_line", "parentKey":"id", "childKey":"upper_id" }
  ],
  "layerOrder": ["cv_batch","cv_header","cv_acc_line","cv_aux_line"]   // 主链路
}
```

**用法**：前端据 `layers` 动态建 N 个 grid，据 `relations` 建 CmxMasterSlave 的 schema + relations。见案例 `doc-loader.js`。

### 2.2 `GET|POST /api/doc/data/sqlx-dataset-json` —— 装载单据数据（最常用）

**命名规则**（源码 `cmx-model/crates/cmx-model-app/src/handlers/doc.rs`）：`/api/doc/data/<驱动>-<内存模式>-<传输>`
- 驱动：`sqlx`（默认连接池）/ `tokio`（tokio-postgres 直连）
- 内存模式：`dataset`（老 DataSet，全拷贝）/ `zmc`（ZmcDataSet，零拷贝）
- 传输：`json` / `msgpack`

5 个组合端点：
| 端点 | 何时用 |
| --- | --- |
| `sqlx-dataset-json` | **默认首选**，sqlx + DataSet + JSON |
| `sqlx-zmc-json` | 大数据量，sqlx + 零拷贝 + JSON |
| `sqlx-zmc-msgpack` | 大数据量 + 二进制（更快） |
| `tokio-zmc-json` | tokio 直连 + 零拷贝 + JSON |
| `tokio-zmc-msgpack` | tokio 直连 + 零拷贝 + 二进制（最快） |

**Query**：同 2.1 的 `DocDataQuery`（domain/application/module/file[/doc/filter/limit/depth]）。

**POST body**（富查询 `DocQuery`）：
```jsonc
{
  "perLayer": {
    "head":  { "filter":"period = '2026-05'", "sort":[{"field":"id","dir":"asc"}], "page":1, "pageSize":20 },
    "items": { "filter":"amount > 0", "sort":[{"field":"id","dir":"asc"}] }
  }
}
```

**响应 `data`**（sqlx-dataset-json）：`{ datasetId, tables: { cv_batch:[...], cv_header:[...], ... }, total: {...} }`

> 返回的是**列式 DataSet 包**，前端用 `CmxDataSet.fromJSON(pkg)` 反序列化，再 `ms.setDataSet({ cv_batch: rootDs })`。

**Header**：
- `db_id: fico-db` —— 多库时切换数据源（DCT/DOC 数据接口必读）
- `Accept: application/json`
- `credentials: same-origin`

### 2.3 `POST /api/doc/save` —— 回存单据数据（merge / replace 双模式）

**Query**：`domain/application/module/file`（同 2.1）。

**请求体**（`saveBody`，源码 `cmx-model/crates/cmx-model-app/src/handlers/doc.rs`）：
```jsonc
{
  "saveMode": "merge",          // 'merge'（增量）| 'replace'（全替换）
  "changes": [                  // merge 模式
    { "layer":"cv_header", "op":"insert", "data":{...} },
    { "layer":"cv_header", "op":"update", "rowId":"h1", "data":{...} },
    { "layer":"cv_acc_line", "op":"delete", "rowId":"a2" }
  ]
  // 或 replace 模式用 "snapshot": { "cv_batch":[...], ... }
}
```

**响应 `data`**：`{ ok, affected: { cv_header: 3 }, warnings?: [...] }`

**校验失败**：HTTP 200 但 `code = 422`，`data.violations` 含校验诊断（源码 `cmx-model/crates/cmx-model-app/src/handlers/doc.rs`）。前端应用 `presentDocError` 对话框展示。

### 2.4 `POST /api/doc/save/batch` —— 批量回存多单

body `{ atomic: true, docs: [{ domain, application, module, file, saveBody }, ...] }`。`atomic:true` 任一失败整体回滚。

### 2.5 `POST /api/doc/data/children` —— 懒下钻

body `{ domain, application, module, file, layer, parentId }` → `{ rows: [...] }`。grid 展开子层时调。

---

## 三、真实页面案例参考

### 3.1 DOC 元数据驱动四层凭证页（html-page 范例）

**文件**：`cmx-container/assets/portal/data/html-pages/sources/fi/cmxfico/voucher-doc.html`

**特点**：
- 用 `cmx-master-slave` 模型组件 + 4 个 `cmx-column-model`（手工配列）
- pageFn `loadVoucher` 调 `/api/doc/data/sqlx-dataset-json` 装载
- 用 `CmxDataSet.fromJSON(pkg)` + `ms.setDataSet({ cv_batch: rootDs })` 灌入
- 用 `ChangeSetCollector` 收集变更，`saveVoucher` 调 `/api/doc/save` 回存
- 用 `presentDocError` 展示校验失败

**关键 pageFn 片段**（节选）：
```js
var q = new URLSearchParams({ domain:'fi', application:'cmxfico', module:'gl', file:'cmxfico_doc_meta_v1.json', limit:'50' });
fetch('/api/doc/data/sqlx-dataset-json?' + q.toString(), {
  headers: { Accept:'application/json', db_id:'fico-db' }, credentials:'same-origin'
})
.then(function(r){ return r.json(); })
.then(function(body){
  var pkg = (body && typeof body.code === 'number') ? body.data : body;  // 兼容信封
  var rootDs = C.CmxDataSet.fromJSON(pkg);
  ms.setDataSet({ cv_batch: rootDs });
  if (C.ChangeSetCollector) host.__collector = new C.ChangeSetCollector(ms).attach();
});
```

> 这是 html-page 用 DOC 接口的**标准范式**，生成同类页面时直接参照。

### 3.2 DCT 字典主数据管理页（html-page 范例）

**文件**：`cmx-container/assets/portal/data/html-pages/sources/fi/cmxfico/gl/gl-master-data-demo.html`

**特点**：用 `CmxDCTMeta` 模型组件加载字典定义 + 字典选择/展示。参考其 `__designer_meta__.models` 里的 `CmxDCTMeta` 配置。

### 3.3 DOC 元数据驱动 N 层动态页（native-page 范例，更通用）

**文件**：`cmx-container/assets/model/web/ui-native/portal/doc/doc-loader.js`（445 行）

**特点**：
- **零硬编码**：层数 N、各层列、主从关系全部来自 `/api/doc/meta`
- 用 `globalThis.__cmxDataComp` 取 `buildMasterSlaveSchema` / `buildColumnModel` / `loadDocData` 等助手
- props 注入业务参数：`{ file, dbId?, apiPath?, binary? }`；DAM（domain/application/module）由框架 openNode 时注入 `workspace.context`，页面用 `ctx.host.workspace.context.get('domain')` 读取（不写进 props）

> 这是"一份页面覆盖全部单据"的极致通用范式。生成元数据驱动页时优先参照。详见 `native-page-generator` 技能。

### 3.4 其它相关页面

| 文件 | 用途 |
| --- | --- |
| `voucher-doc-sqlxbin.html` | DOC + sqlx 二进制通道范例 |
| `doc-service-test.html` | DOC 接口测试页 |
| `fi/cmxfico/voucher-native.js` | native 版凭证页（JS 模块） |
| `fi/cmxfico/voucher-native-bin.js` | native 版凭证页（msgpack 二进制） |

---

## 四、6 大模型 vs 直接 fetch 的选择

| 场景 | 用什么 |
| --- | --- |
| 页面有固定结构，走设计器配置 | `CmxDCTMeta` / `CmxDOCMeta` **模型组件**（autoLoad 自动调 `/api/definitions/config`） |
| 需要**字典数据行**（如下拉选项） | 直接 fetch `/api/dct/data/search`，或用 `cmx-dict-select` 组件 |
| 需要**单据数据行**（装载业务数据） | 直接 fetch `/api/doc/data/sqlx-dataset-json`（见 3.1 范式） |
| 需要**动态 N 层**（结构来自后端） | fetch `/api/doc/meta` 拿层序，动态构造（见 3.3 范式） |

---

## 五、通用约定

### 响应信封

所有 handler 统一返回 `ApiResp`：
```jsonc
{ "code": 0, "ok": true,  "data": { ... } }    // 成功
{ "code": 422, "ok": false, "msg": "...", "data": { "violations":[...] } }  // 业务失败
{ "code": 500, "ok": false, "msg": "Internal: ..." }  // 系统错误
```

> 前端 `apiFetch` 自动拆 `data`。但手写 `fetch` 时要自己处理信封（见 3.1 的 `body.code` 兼容）。

### 身份与上下文头

| Header | 含义 | 必要性 |
| --- | --- | --- |
| `Authorization: Bearer <jwt>` | 鉴权 | 必 |
| `x-cmx-db-id: default` / `db_id: fico-db` | 数据源（多库切换） | DCT/DOC 数据接口必读 |
| `x-cmx-trace-id: ...` | 链路追踪 | 缺省自动生成 |

### 错误码

| 范围 | 含义 |
| --- | --- |
| `0` | 成功 |
| `4xx` | 业务可处理（422 校验失败，404 不存在，409 冲突） |
| `5xx` | 系统错误 |
