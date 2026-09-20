# cmx-ontology 全量接口清单与请求参数说明（大白话版）

> **20260919 同路径多方法整改**：**同一路径只挂一个 HTTP 方法**（GET 列表 + POST 写入不得复用同一路径，AGENTS.md §四.6 新增约束）。六类元素 / 本体 / 数据源 / 策略 / 漏斗映射等 **12 组集合路径拆分**——写侧移独立固定段：`POST /object-types` → `/object-types/save`、`POST /ontologies` → `/ontologies/create`、`POST /data-sources` → `/data-sources/create`、`DELETE /links` → `POST /links/remove`，其余同理（`/link-types/save`、`/interfaces/save`、`/shared-properties/save`、`/views/save`、`/action-types/save`、`/functions/save`、`/policies/save`、`/funnel/mappings/save`）。`GET /集合` 列表语义不变。前端四页 + dashboard + cmx-agent 测试 + onto-toolkit 脚本已同步适配。
> **20260918 多本体改造（M1+M2）后版本**：全接口 `?ontology=` 必填（例外见 §0）、§3.7 去路径化（detail/remove/save/execute/evaluate 等 apiName 一律入 query/body）、新增 §2.5 本体管理五端点、SSE 按本体过滤。前端四页 + cmx-agent 连接器 + onto-toolkit 已同步适配。

> **范围**：本体平台 `backend/cmx-ontology` 注册的全部 HTTP 接口（**97 个业务端点**，20260919 同路径拆分后口径、20260920 移除旧旁路 `/secure/object-sets/load` + 4 类服务级端点），逐个说明用途、请求参数、响应要点，并标注**哪些前端页面真的在用、哪些目前没有页面调用**。
> **调用方代码依据**：`backend/cmx-container/assets/onto/web/ui-native/onto/` 下四个前端页（`designer.js` / `explorer.js` / `workshop.js` / `studio.js` + studio 八模块 + `page-kit.js`）+ `cmx-onto-app/src/dashboard.rs` 自带控制台 + 仓内 QA 脚本（`qa-backend.sh` / `qa-object.sh` / `test/e2e` 21 个 / `test/fe` 19 个）。
> **写作日期**：2026-09-18，以当日 main 分支代码为准（cmx-ontology 最新提交 `5614a85`；对照重设计案 `documents/plans/20260917_cmx-ontology_状态生命周期与版本发布及场景机制重设计方案.md`）。

---

## 0. 通用约定（先读这节，后面不重复）

| 约定 | 说明 |
| --- | --- |
| **URL 前缀** | 正式契约 `/api/onto/v1`；旧前缀 `/api/onto` 同路由表双挂载保留（内嵌壳兼容）。下文只写 v1 相对路径 |
| **认证** | 请求头 `Authorization: Bearer <token>` 或开发免登录 `X-API-Key: cmx_sk_dev_…`；免认证的只有：控制台 `GET /`、`openapi.json`、`docs`、`/api/native-pages/*` 页面投递。**注意 `GET /events`（SSE）自 P2 起已注册进鉴权路由**，需带令牌，前端用 fetch 流式读取 |
| **统一响应壳** | 除特别说明外，全部返回 `{ "code": "ok", "message": "", "data": … }`；业务错误 code 非 ok，HTTP 状态码 200/400/403/404/409 |
| **字段风格** | 请求/响应 body 一律 **camelCase**；可缺字段带默认值（只传部分字段也能受理） |
| **乐观锁** | **七类资源 + 场景全部带 `version` 字段**（20260917 补齐五类表）：拿旧版本号保存已被人改过的定义 → 409 Conflict。`version=0` = 新建/盲写 |
| **同路径单方法（20260919 起）** | **同一路径只挂一个 HTTP 方法**：读走 `GET`，写走独立固定段 `POST`（`/save` / `/create` / `/remove` 等）；`GET /集合` = 列表，`POST /集合` 已拆除（405） |
| **状态纪律** | 七类资源的 `status` / `deprecation` **save 端点一律剥离忽略**（请求体带了会回 `warnings` 提示）；状态变更**唯一入口**是 `POST /lifecycle/transition` |
| **维护角色守卫** | 存档 / 回滚 / 发布标记 / 状态流转 / 场景编辑走 `require_maintainer`：`om_maintainer` 白名单表**空表 = 开放**；有行时按 用户id / 展示名 / 角色 三路匹配，不命中 → 403（前端统一降级隐藏写入口） |
| **本体参数（20260918 M1 起必填）** | 除例外清单外，**全部接口必带 `?ontology=<本体apiName>`**（元数据/实例/事件/版本按本体隔离；apiName 唯一性放宽为本体内唯一）。例外（不收该参数）：`/ontologies*`、`/data-sources*`、`/me/roles`、`/funnel/push`。缺参 → **400 `ONTOLOGY_REQUIRED`**；不存在 → **404 `ONTOLOGY_NOT_FOUND`**；已停用 → **409 `ONTOLOGY_DISABLED`**。前端各页收到后两者时 toast + 回落 `default_ontology` 自动重载 |

**调用方代号**（下文"谁在用"列使用）：

| 代号 | 是什么 | 代码位置 |
| --- | --- | --- |
| **设计台** | 本体设计工作台（建模主页面，四区薄壳 + 画布组件） | `…/ui-native/onto/designer.js` |
| **浏览器** | 对象浏览器（看数据、顺关系钻取） | `…/ui-native/onto/explorer.js` |
| **搭建台** | 应用搭建台 / 对象 360（业务角色执行动作） | `…/ui-native/onto/workshop.js` |
| **工作室** | 本体工作室（20260913 上线：场景画布 + 版本中心 + 修订时间线，`studio.js` 薄壳 + `studio/` 八模块） | `…/ui-native/onto/studio*.js` |
| **控制台** | 服务自带建模控制台（浏览器直接开 `:8097/`） | `cmx-onto-app/src/dashboard.rs` |
| **MDM** | MDM 分发引擎 webhook 订阅（服务身份 X-API-Key） | cmx-mdm 侧配置 |
| **flow** | 流程引擎审批回调（服务身份 X-API-Key） | cmx-flowengine 侧 |
| **QA** | 仓内自动化测试脚本 | `qa-backend.sh`、`qa-object.sh`、`test/e2e`、`test/fe` |
| **—** | 目前无任何业务调用方（预留 / 工具向） | |

> ⚠️ 两个容易搞混的点：
> ① **设计台/浏览器/搭建台/工作室左侧元素清单全部来自 `GET /manifest`**（支持 `?types=` 子集 + `?include=` 状态分层 + `?view=` 场景口径），各元素单独的 `GET /xxx-types`（列表）页面大多不依赖——工作室只在清单缺项时兜底补拉。
> ② **"发布"一词已改义**（20260917）：旧 `POST /publish` 端点已删除。现在"存档 = 打检查点（`POST /snapshots`）"，"发布 = 给检查点起名（`POST /releases`）"。编辑直写 live，没有草稿态。

---

## 1. 使用全景速览

| 接口组 | 端点数 | 设计台 | 浏览器 | 搭建台 | 工作室 | 控制台 | QA |
| --- | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| §2 服务级（控制台/文档/页面投递） | 4类 | 页面载体 | 页面载体 | 页面载体 | 页面载体 | ✔ | ✔ |
| §3 对象类型 object-types | 6 | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |
| §4 关系类型 link-types | 4 | ✔ | — | — | ✔ | ✔ | ✔ |
| §5 接口 interfaces | 4 | ✔ | — | — | ✔ | — | ✔ |
| §6 共享属性 shared-properties | 5 | ✔ | — | — | ✔ | — | ✔ |
| §7 场景视图 views + graph | 5 | — | — | — | ✔ | — | — |
| §8 动作类型 action-types（建模） | 4 | ✔ | — | ✔(详情) | ✔ | — | ✔ |
| §9 动作执行（execute/dry-run/batch/预检） | 4 | ✔ | — | ✔ | ✔ | — | ✔ |
| §10 函数 functions（建模+求值） | 5 | ✔ | — | — | ✔ | — | ✔ |
| §11 生命周期 + 修订 | 4 | — | — | — | ✔ | — | ✔ |
| §12 清单/存档/版本/发布/me | 9 | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |
| §13 SSE 事件流 events | 1 | — | — | — | ✔ | — | ✔ |
| §14 对象实例 objects/links | 7 | — | ✔(钻取) | — | — | — | ✔ |
| §15 对象集 load/aggregate | 2 | ✔(聚合) | ✔ | ✔ | ✔(计数) | — | ✔ |
| §16 动作引擎辅助（日志/Outbox/代理） | 8 | ✔(模板/流程/报表) | — | — | — | — | ✔ |
| §17 安全策略 policies | 3 | — | — | — | — | — | ✔ |
| §18 数据集成 funnel | 7 | — | — | — | — | — | ✔(+MDM push) |
| §19 反向导入 import + 流程回调 | 3 | — | — | — | — | — | ✔(+flow) |
| §20 SDK 生成 osdk + 统计 stats | 2 | — | — | — | — | ✔(stats) | ✔ |

**结论**：四个前端页面 + 控制台实际活跃使用的接口约 **55 个**（六类元素 CRUD + manifest/快照/版本 + 场景/图数据 + 修订/流转 + 动作执行/预检 + 对象集加载聚合 + SSE）；**没有任何页面调用**的约 **25 个**（对象实例直接写入、关系边写入、策略、数据集成、导入、SDK、审计/Outbox 手动投递——由 QA 脚本验证，设计上给外部系统 / 运维脚本 / 后续页面用）。

---

## 2. 服务级端点（server `main.rs` 组合根注册，不在 `/api/onto/v1` 业务路由表内）

| 方法+路径 | 大白话作用 | 参数 | 谁在用 |
| --- | --- | --- | --- |
| `GET /` | 打开自带建模控制台网页（统计块 + 对象/关系类型管理 + 存档），免认证 | 无 | 浏览器直开 `:8097/` |
| `GET /api/onto/v1/openapi.json` | 输出本服务全部接口的 OpenAPI 描述（给 Swagger/代码生成工具用） | 无 | —（QA o7） |
| `GET /api/onto/v1/docs` | Swagger UI 调试页（人工点着试接口用），免认证 | 无 | — |
| `/api/native-pages/*` | 静态投递前端页面 JS 与组件 vendor（15 个注册条目：designer / explorer / workshop / studio 薄壳 + studio 八模块 + page-kit + 画布组件 + 组件子集） | 路径即页面 id（如 `portal.onto.designer`） | 四页前端载体 |

---

## 2.5 本体管理 ontologies（5 个端点）——20260918 M1 新增，例外路由（不收 ontology 参数）

| 方法+路径 | 大白话作用 | 参数 | 谁在用 |
| --- | --- | --- | --- |
| `GET /ontologies?includeDisabled=` | 本体清单（管理弹框；缺省仅启用，true 含停用） | query：`includeDisabled?` | 工作室Next（管理弹框） |
| `GET /ontologies/enabled` | **启用本体清单**（各页选择器数据源；停用本体天然不出现） | 无 | 浏览器/搭建台/工作室/工作室Next（选择器） |
| `POST /ontologies/create` | 新建本体 | body：`{ apiName*, displayName*, description? }` | 工作室Next |
| `POST /ontologies/update` | 改名称/描述（apiName 不可改） | body：`{ apiName*, displayName?, description? }` | 工作室Next |
| `POST /ontologies/set-status` | 启用/停用。**默认本体不可停用（409）**；停用后各页请求该本体 → 409 自动回落 | body：`{ apiName*, status*: active|disabled }` | 工作室Next |

> 默认本体 `default_ontology` 由迁移 seed 创建（`is_default=true`，存量数据归属锚点）；apiName 全局唯一（本体表本身不隔离）。

---

## 3. 对象类型 object-types（6 个端点）

"对象类型"就是"一类东西的模板"——比如客户、订单。这里是这套模板的增删改查。

| 方法+路径 | 大白话作用 | 请求参数 | 谁在用 |
| --- | --- | --- | --- |
| `GET /object-types` | 列出对象类型。**双形态**：不传参 = 全量摘要数组（旧语义）；传 `q`（关键字）/`dam`（域路径）/`page`/`size` 任一 = 服务端分页信封 `{rows, total, page, size}`（工作室目录表格用） | query 全可选 | 控制台（全量）；工作室（分页检索） |
| `POST /object-types/save` | 新建或更新一个对象类型（upsert：apiName 相同即覆盖）。结构校验 + **接口契约校验**（implements 声明的共享属性必须落实）+ **active 保护**（active 资源不可改主键）。body 里的 `status`/`deprecation` 被剥离并回 warnings | body：**ObjectTypeDef**（见 §3.1） | 设计台、工作室、控制台、QA |
| `POST /object-types/validate` | 只校验不保存——检查这份定义合不合法，返回 `{valid, error?}` | body：ObjectTypeDef | —（QA） |
| `POST /object-types/batch` | 按 apiName 列表**批量取完整定义**（设计器/工作室画布首屏装载，避免逐个 GET 的 N+1） | body：`{ "apiNames": ["Customer", …] }`；响应 `{items, errors}` | 设计台、工作室 |
| `GET /object-types/detail?apiName=` | 看某个对象类型的**完整定义**（含全部属性） | query：`apiName*`；`?ontology=` | 四页 + 控制台 |
| `POST /object-types/remove` | 删除对象类型。**三重安全网**：① active 资源不可删（409 先降级）；② 被关系/动作编辑引用 → 409 出引用清单；③ 删除前自动存档检查点（可撤销），场景引用级联清理（响应带 `sceneRefs` / `affectedScenes`） | body：`{ apiName* }` | 设计台、工作室、控制台 |

### 3.1 ObjectTypeDef 请求体字段

```jsonc
{
  "apiName": "Customer",        // 必填。英文唯一标识：字母/下划线开头，仅字母数字下划线
  "displayName": "客户",         // 显示名
  "description": "", "icon": "", "color": "",   // 描述/图标/图谱色
  "dam": { "domain": "crm", "application": "sales", "module": "customer" },  // 域/应用/模块三级分类（场景分域折叠依据）
  "docType": { "code": "", "name": "" },        // 业务单据类型（DOC 导入回填，浏览器在模块下再分一层）
  "primaryKey": "id",           // 主键属性 apiName（必须是 properties 之一；active 后不可改）
  "titleProperty": "name",      // 用哪个属性当对象的"名字"
  "properties": [               // 属性列表（PropertyTypeDef）
    { "apiName": "id", "displayName": "ID", "baseType": "long", "required": true,
      "isIndexed": true, "semanticType": null, "sharedProperty": null,
      "marking": null, "constraints": {}, "description": "" }
  ],
  "implements": ["Locatable"],  // 实现的接口 apiName 列表（保存时强校验共享属性契约）
  "datasource": null,           // 背书数据源（数据集成用，原样 JSON）
  "cmxOrigin": null,            // 由 DOC/DCT 导入时的来源回指
  "version": 3                  // 乐观锁：0=新建盲写；>0=带版本条件更新（过期保存 409）
  // "status"/"deprecation" 传了会被剥离（状态唯一入口 = POST /lifecycle/transition）
}
```

**响应**：`{ "saved": true, "version": 4, "warnings": [] }`——**前端必须拿响应里的 version 刷新基线**，否则下次保存必 409。

**属性 baseType 可选值**（16 种）：`string / integer / long / double / decimal / boolean / date / timestamp / array / struct / attachment / mediaReference / marking / geohash / geoShape / vector`。

---

## 4. 关系类型 link-types（4 个端点）

"关系类型"= 两类东西之间怎么连（客户→订单、1 对多）。20260910 起 backing **严格 Palantir 化**：只认三种顶层键，旧 `{"kind":…}` 口径废除。

| 方法+路径 | 大白话作用 | 请求参数 | 谁在用 |
| --- | --- | --- | --- |
| `GET /link-types` | 列出全部关系类型（摘要，含两端 DAM 富化） | 无 | 控制台、QA |
| `POST /link-types/save` | 新建/更新关系类型（画布拉线速建 / Inspector 保存都走它）。**乐观锁已补齐**（version>0 条件更新）；两端对象状态兼容矩阵在保存期校验 | body：**LinkTypeDef**（见下） | 设计台、工作室、控制台 |
| `GET /link-types/detail?apiName=` | 某个关系类型的完整定义 | query：`apiName*` | 设计台、工作室 |
| `POST /link-types/remove` | 删除关系类型。active 保护 + 场景引用级联清理 + 删除前自动存档 | body：`{ apiName* }` | 设计台、工作室、控制台 |

```jsonc
{
  "apiName": "customerPlacesOrder",   // 必填
  "displayName": "客户下单",
  "cardinality": "oneToMany",         // oneToOne | oneToMany(默认) | manyToOne | manyToMany（有向：oneToMany=源1:靶N）
  "objectTypeA": "Customer",          // 必填。A 端对象类型
  "objectTypeB": "Order",             // 必填。B 端对象类型
  "roleA": "下单人",                   // A→B 方向的角色名（连线标签）
  "roleB": "订单列表",                 // B→A 方向的角色名
  "backing": {                        // 落存储方式（唯一口径=页面形状，三种顶层键）：
    "fk": { "sourceProperty": "customerId", "side": "b", "targetProperty": "orderId" }
    // ① fk 外键：side 端 props.sourceProperty 存对端匹配值；side 缺省按基数推导
    //    （oneToMany→b / manyToOne→a / oneToOne→a）；targetProperty 缺省=对端主键 pk 列；
    //    仅 1:1/1:N/N:1 可用（N:M 拒绝）。白名单键仅 sourceProperty/side/targetProperty
    // ② {"joinTable":{"table","leftColumn","rightColumn"}}：连接表（仅 N:M）
    // ③ {"intermediary":{"objectType","leftProperty","rightProperty"}}：中间对象（仅 N:M）
    // ④ 空对象/无法识别 = Edge 原生边表兜底
  },
  "status": "experimental",           // 保存期剥离忽略（走 /lifecycle/transition）
  "version": 2                        // 乐观锁（20260917 补齐）
}
```

**响应**：`{ "saved": true, "version": 3, "warnings": [] }`。

---

## 5. 接口 interfaces（4 个端点）

"接口"= 一组公共能力的标签。比如 `Locatable`（有地址）——客户、仓库都 `implements` 它。

| 方法+路径 | 大白话作用 | 请求参数 | 谁在用 |
| --- | --- | --- | --- |
| `GET /interfaces` | 列出全部接口。**双形态**：不传参 = 全量数组；传 `q`/`page`/`size` 任一 = 分页信封（工作室引用选择器用） | query 全可选 | 工作室（选择器/兜底）；QA |
| `POST /interfaces/save` | 新建/更新接口 | body：`{ apiName*, displayName?, properties?: string[]（要求实现者具备的共享属性）, extends?: string[]（接口继承）, version? }` | 设计台、工作室 |
| `GET /interfaces/detail?apiName=` | 某接口完整定义 | query：`apiName*` | 设计台、工作室 |
| `POST /interfaces/remove` | 删除接口 | body：`{ apiName* }` | 设计台、工作室 |

---

## 6. 共享属性 shared-properties（5 个端点）

"共享属性"= 全公司统一的标准化字段。比如 `currencyCode` 定义一次，各对象类型的属性引用它。

| 方法+路径 | 大白话作用 | 请求参数 | 谁在用 |
| --- | --- | --- | --- |
| `GET /shared-properties` | 列出全部共享属性。**双形态**：不传参全量；`q`/`page`/`size` = 分页信封 | query 全可选 | 工作室（选择器） |
| `POST /shared-properties/save` | 新建/更新共享属性 | body：`{ apiName*, displayName?, baseType?(默认 string), semanticType?, description?, version? }` | 设计台、工作室 |
| `POST /shared-properties/batch` | 按 apiName 列表批量取详情 | body：`{ "apiNames": […] }`；响应 `{items, errors}` | 工作室（装载层） |
| `GET /shared-properties/detail?apiName=` | 某共享属性完整定义 | query：`apiName*` | 设计台、工作室 |
| `POST /shared-properties/remove` | 删除共享属性 | body：`{ apiName* }` | 设计台、工作室 |

---

## 7. 场景视图 views + 图数据 graph（5 个端点）——本体工作室 P1

"场景"是**过滤器/透镜，不是容器**：全局底座（六类元素定义）只有一份，场景只存"成员引用清单 + 画布布局"。两种来源：
- **auto**（域默认视图）：apiName 固定 `auto:<domain>`，成员**读时按 DAM 域现算**，不物化；域消失 → 虚拟条目自然消失；
- **manual**（手动场景）：成员物化（快照语义），不随 DAM 漂移。

**20260918 场景职责收口（用户裁决）**：关系定义由底座唯一管理，场景只管成员——
- `links` 白名单**下线**：边 = 两端对象都在场即派生显示（manual 与 auto 统一口径）。存量 `members.links` 保留存储不消费；`POST /views/save` 仍接受该字段（兼容旧客户端）但不影响投影；
- `GET /graph` 不再返回 `availableLinks` 与节点角标 `externalCount/externalPeers`（断头关系不展示也不提醒，补全由「引入对象（可连同直接关联）」承担）；
- 场景画布内新建关系 / 删除关系 / 挂接摘除接口全部前端拦截引导回底座画布（后端接口本身不变，仍是底座全局语义）。

| 方法+路径 | 大白话作用 | 请求参数 | 谁在用 |
| --- | --- | --- | --- |
| `GET /views` | 场景清单：已落行场景 + **域派生虚拟条目**合并返回（虚拟条目 `virtual:true`，不可直接删） | 无 | 工作室 |
| `POST /views/save` | 保存场景（新建/覆盖/域播种/成员编辑/转手动）。维护角色守卫。`links` 字段兼容接收（清洗保留，投影不消费）；**请求不带 layout 时保留已有布局**（成员编辑不吞布局）；乐观锁 `version` | body：`{ apiName*, displayName, description, dam, members:{objects[], interfaces[], links[]}, source:"auto"\|"manual", layout?, version }` | 工作室 |
| `POST /views/remove` | 删场景（写墓碑修订 + 广播 view-changed）。auto 行豁免（返回 `removed:false, reason:"auto 豁免"`）；行不存在幂等成功 | body：`{ apiName* }` | 工作室 |
| `POST /views/layout` | 画布拖拽布局**单列 LWW 直写**（不做版本检查、不进乐观锁——布局是物化产物不进版本语义，存档指纹也排除 layout）。auto 视图行不存在时按需落行（只落 meta+layout，永不落成员） | body：`{ apiName*, layout }` | 工作室 |
| `GET /graph?view=X` | **服务端组装成员级画布 spec，一条请求到位**：解析视图成员 → 批量装成员对象全量定义 → 接口 = implements 并集 ∪ members.interfaces → 边 = **两端在场即派生**（白名单已下线）→ 悬空引用进 `warnings` | query：`view*`（场景 apiName）、`include`（状态分层，缺省全量） | 工作室 |

**graph 响应**：`{ view: {…meta}, spec: {name, nodes, edges}, layout, sharedProperties: […], warnings: […] }`。

---

## 8. 动作类型 action-types · 建模 4 端点

"动作"= 一次**带校验、带规则、带副作用**的业务操作（动词），比如"转派订单"。动作引擎已对标 Palantir P0/P1/P2（函数背书 / 对象状态校验 / 值映射 / 组合校验 / upsert / 批量 / 作用对象物化列）。

| 方法+路径 | 大白话作用 | 请求参数 | 谁在用 |
| --- | --- | --- | --- |
| `GET /action-types` | 列出全部动作类型（摘要，含 `parameters` 与**作用对象类型物化列** `targetObjectTypes`——保存期从 parameters+logic 派生，GIN 索引支持按类型查动作） | 无 | 工作室（兜底）；QA |
| `POST /action-types/save` | 新建/更新动作类型（保存表单 / 从模板创建都走它）；保存期重算 `targetObjectTypes` | body：**ActionTypeDef**（见 §8.1） | 设计台、工作室 |
| `GET /action-types/detail?apiName=` | 某动作完整定义（搭建台/工作室执行前拉它动态生成参数表单） | query：`apiName*` | 设计台、搭建台、工作室 |
| `POST /action-types/remove` | 删除动作类型 | body：`{ apiName* }` | 设计台、工作室 |

### 8.1 ActionTypeDef 请求体字段

```jsonc
{
  "apiName": "reassignOrder",     // 必填
  "displayName": "转派订单",
  "description": "",
  "parameters": [ /* 表单参数定义：名字/类型/是否必填/默认值/约束；可绑对象/对象集/标量（P1 参数体系） */ ],
  "logic": [ /* 编辑规则：createObject / modifyObject / deleteObject / createOrModifyObject(upsert)
                 / addLink / removeLink；值支持五种显式映射来源（见 §9） */ ],
  "validations": [ /* 提交校验：FEEL 表达式（可引用参数与参数对象状态），不过则拒绝执行；fail-closed */ ],
  "sideEffects": [ /* 副作用：emitEvent / notification / callFunction / webhook /
                      startBusinessProcess / computeReport */ ],
  "functionBacking": null,        // 函数背书（复杂逻辑走函数：函数返回编辑 JSON）
  "version": 1                    // 乐观锁（20260917 补齐）
}
```

> `parameters / logic / validations / sideEffects` 四块都是 JSON 数组，原样入库；执行引擎（§9）按固定语义消费。动作的 `targetObjectTypes` 是保存期派生的**物化列**（语义真源仍是 parameters/logic），manifest 据此做"按对象类型过滤动作"。

---

## 9. 动作执行（4 个端点）

| 方法+路径 | 大白话作用 | 请求参数 | 谁在用 |
| --- | --- | --- | --- |
| `POST /action-types/execute` | **真正执行**一个动作：默认值填充 → 参数校验 → 装载参数对象 → 跑校验表达式 → 算编辑集（含组合序列校验）→ 写侧 PEP（deny_actions 硬门）→ **一个事务**写回 + 审计 + 副作用入 Outbox | body：**ExecuteReq**（见下） | 设计台、搭建台、工作室 |
| `POST /action-types/dry-run` | **试算不落库**：完整校验链 + 预演（等价 execute 但强制 dryRun）——告诉你"如果执行会改什么" | body：同 ExecuteReq | 设计台、搭建台、工作室 |
| `POST /action-types/execute-batch` | **同事务批量执行**（P1-3；固定路径无路径参数，apiName 入 body）：逐项走完整校验链，任一失败整批回滚；单批上限 100（`ONTO_ACTION_BATCH_MAX` 可调） | body：`{ apiName*, items:[{params},…], dryRun?, actor?, subjects? }` | —（QA；给外部系统的批量入口） |
| `POST /action-types/check-permission` | **动作可见性 PEP 预检**（P2-1；固定路径）：前端据此**不渲染**被拒按钮。目标类型由定义静态解析（解析失败回退参数声明派生），与执行期 PEP 同源 | body：`{ actions: ["closeOrder",…], subjects: ["role:admin"] }`；响应 `{results:[{action, allowed, deniedBy?, scopes}]}` | 搭建台、QA |

```jsonc
// ExecuteReq
{
  "params": { "orderId": "SO001", "newOwner": "bob" },  // 动作参数（对 ActionTypeDef.parameters）
  "dryRun": false,             // true=只预演（一般用 /dry-run 端点）
  "actor": "workshop",         // 操作人署名（写审计日志；缺省取当前登录用户）
  "subjects": ["role:admin"]   // 主体声明（写侧 PEP 用 ["role:x","user:y"]）；
                               // 缺省回退 role:<租户> + user:<当前用户>；jwt 模式以令牌为准
}
```

**值映射五来源**（`logic` 里对象字面量含 `"src"` 键即解析，对标 Palantir Rules）：`{"src":"param","name":"x"}`（取参数）、`{"src":"static","value":…}`、`{"src":"currentUser"}`、`{"src":"currentTime"}`、`{"src":"paramProperty","param":"p","property":"f"}`（取参数对象的属性）。字符串 `"$name"` 仍是参数替换语法糖。

**执行响应**：`{ action, dryRun, applied, edits, effects, logId, status: "committed"|"dryRun", proposedChanges, executionLog, sideEffectPreview, snapshotBasis:"preRead" }`——`proposedChanges` 是 P1-1 新增的 from→to diff 预览（对象条目带属性级变化，删除含完整快照）。

> ⚠️ **非 Edge backing 的关系不落 ol_edge 边表**：FK/连接表/中间对象背书的关系，`addLink/removeLink` 编辑与 `/links` 边写入一律 fail-fast 拒绝（防"写入 200 成功、查询永不生效"的静默假写）——请直接维护外键属性值 / 连接表 / 中间对象数据。

---

## 10. 函数 functions（5 个端点）

"函数"= 存在平台里的一段可复用计算（FEEL 表达式 / Rhai 脚本 / wasm / nativeRust 四种运行时），可被动作背书、被派生属性引用、也可单独调。

| 方法+路径 | 大白话作用 | 请求参数 | 谁在用 |
| --- | --- | --- | --- |
| `GET /functions` | 列出全部函数（摘要，含 runtime/kind/status 富化） | 无 | 工作室（兜底）；QA |
| `POST /functions/save` | 新建/更新函数 | body：`{ apiName*, displayName?, runtime?(feel[默认]/rhai/wasm/nativeRust), kind?(query[默认]/derivedProperty/validation/actionLogic/aggregation), inputs?, output?, body*, description?, version? }` | 设计台、工作室 |
| `GET /functions/detail?apiName=` | 某函数完整定义 | query：`apiName*` | 设计台、工作室 |
| `POST /functions/remove` | 删除函数 | body：`{ apiName* }` | 设计台、工作室 |
| `POST /functions/evaluate` | **求值**：绑定输入 → 执行函数体 → 返回结果 | body：**EvalFnReq**（见 §10.1） | 设计台（试运行）、工作室 |

### 10.1 EvalFnReq 请求体（`apiName` 已入 body——M1 §3.7）

```jsonc
{
  "args": { "amount": 5000, "region": "east" },       // 标量参数：直接注入
  "objects": {                                          // 对象输入：参数名 → 指向一个对象实例
    "cust": { "objectType": "Customer", "pk": "C001" } //   平台把该对象的全部属性注入为参数值
  },
  "objectSets": {                                       // 对象集输入：参数名 → 对象集代数（§15.1）
    "orders": { "op": "base", "objectType": "Order" }  //   行属性数组注入，函数体可 sum/count
  },
  "aggregation": null,   // 仅 kind=aggregation 的函数要给：聚合规格（见 §15.2）
  "objectSet": null      // 仅 kind=aggregation：要聚合的对象集
}
```

**响应**：`{ function, kind, runtime, result }`。

---

## 11. 生命周期 + 修订历史（4 个端点）——20260917 新增

Palantir 式**软治理**：资源状态 `experimental → active → deprecated` 的变更不再靠保存盲写，而是走唯一入口；每次保存/流转/回滚都留修订痕迹。

| 方法+路径 | 大白话作用 | 请求参数 | 谁在用 |
| --- | --- | --- | --- |
| `POST /lifecycle/transition` | **七类资源（含场景 view）状态流转唯一入口**（维护角色守卫）。→deprecated 必填弃用元数据（reason/sunsetAt）；关系流转过**兼容矩阵**（任一端 deprecated → 仅 deprecated；任一端 experimental → 仅 experimental）；对象流转触发**机械级联**（级联目标=矩阵判定结果，系统不产生违规态）；`dryRun:true` 返回级联影响预览不落库；每个变更资源写一条修订 + SSE `resource-changed` | body：`{ kind*: object\|link\|interface\|shared_property\|action\|function\|view, apiName*, target*: experimental\|active\|deprecated, dryRun?, deprecation?: {reason, sunsetAt, replacementApiName?}, changeNote? }` | 工作室 |
| `GET /revisions` | 单资源修订时间线（谁在什么时候把它改成了什么）；`deleted=true` 时改为列出**带墓碑的已删除资源** | query：`kind`+`apiName`（与 deleted 二选一必填）、`limit`（默认100）、`deleted?` | 工作室 |
| `GET /revisions/detail` | 单条修订详情（含完整 payload 快照） | query：`id*`（修订全局 id） | 工作室 |
| `POST /revisions/revert` | **git revert 式回滚**：以旧定义执行一次新保存（历史只追加）；资源已删除（墓碑）时升级为创建语义（恢复该资源） | body：`{ kind*, apiName*, revision*（资源内序号）, changeNote? }` | 工作室 |

---

## 12. 清单 / 存档 / 版本 / 发布（9 个端点）

**直改 live 架构**：建模编辑直接写 om_* 真源（消费方读取路径零改动）；"存档"= 用户主动把 live 打成不可变检查点；"发布"= 给检查点起名打 tag；"回滚"= 把历史快照整体恢复回 live。

| 方法+路径 | 大白话作用 | 请求参数 | 谁在用 |
| --- | --- | --- | --- |
| `GET /manifest` | **本体全量清单**：六类元素摘要一次全给（对象类型带完整属性体）。`?types=` 逗号分隔取子集；`?include=` 状态分层（**默认仅 active**；可 experimental/deprecated 逗号组合或 all）；`?view=` 场景六段口径（成员对象 / 场景内关系 / 派生动作 / 派生共享属性；functions 恒空） | query 全可选 | 四页全用；QA |
| `POST /snapshots` | **存档检查点**（旧"发布"的新身份）：当前 live 全量快照 → om_version 不可变行。rev 与最新版本相同 → 去重不插行（`deduped:true`）。广播 SSE `checkpoint-created` | body：`{ "summary": "本次存档说明" }`（维护角色守卫） | 设计台、工作室、控制台 |
| `GET /versions` | 检查点版本列表（新→旧），含 tag/release_note | 无 | 四页 + 控制台 |
| `GET /versions/detail?version=` | 回看某版本的**完整快照** | query：`version*` | 工作室 |
| `GET /versions/diff` | **服务端元素级 diff**：a/b 两侧可以是版本号或 `"live"`；返回逐元素 `added/modified/removed` 清单 + 计数 | query：`a*`、`b*` | 工作室 |
| `POST /versions/restore` | **回滚**：历史快照整体恢复回 live（无草稿中转）。结构/引用校验（Error 阻断）→ **大规模删除护栏**（派生删除集超 `max(50, total/5)` 必须显式确认）→ 单事务应用（六类 upsert + views + 派生删除 + 级联）→ 回滚留痕存档 → SSE 广播 | body：`{ version*, confirmMassDelete? }`（维护角色守卫） | 工作室 |
| `POST /releases` | **命名发布标记**：跑发布门禁（live 含 experimental/deprecated 资源 → 警告清单，须 `acknowledgeWarnings:true` 显式放行）→ 打全量检查点并置 tag。tag 规则：非空 ≤64、`^[A-Za-z0-9][A-Za-z0-9._-]*$`、不得纯数字。广播 SSE `release-created` | body：`{ tag*, note?, acknowledgeWarnings? }`（维护角色守卫） | 工作室 |
| `POST /releases/remove` | 解除发布标记（只清 tag，不删检查点行） | body：`{ tag* }` | 工作室 |
| `GET /me/roles` | 当前用户角色/权限码（无守卫）：`{ user, username, roles, maintainer, permissionCodes }`——工作室据此决定降级隐藏写入口 | 无 | 工作室 |

---

## 13. SSE 实时事件流 events（1 个端点；`?ontology=` 必填——服务端按本体过滤事件，切本体重连）

| 方法+路径 | 大白话作用 | 参数 | 谁在用 |
| --- | --- | --- | --- |
| `GET /events` | **SSE 实时事件流**（P2 起在鉴权路由内，需带 Bearer 令牌；前端 fetch 流式读取）。进程内 broadcast 通道，无持久化（掉线丢事件，需可靠投递走 Outbox/webhook）。事件种类：`checkpoint-created`（存档）、`release-created`（发布）、`resource-changed`（保存/流转/回滚/删除）、`view-changed`（场景变更）、`notification`（动作通知副作用）、`emitEvent` 目标事件、`published`（兼容保留） | query：`tenant`（可选，按租户过滤） | 工作室；QA |

---

## 14. 对象实例 objects / links（7 个端点）

前面管"模板"，这里管"数据"——真正的一条客户、一张订单。**前端页面不直接写对象**（数据从业务库集成或经动作间接改），浏览器只用"读"的一个。

| 方法+路径 | 大白话作用 | 请求参数 | 谁在用 |
| --- | --- | --- | --- |
| `POST /objects/save` | 写入/更新**一个**对象（类型必须已定义；pk/title 缺省按定义从 properties 抽；物理表不存在会自动建） | body：`{ objectType*, properties*, pk?, title? }` | —（QA、agent） |
| `POST /objects/save-batch` | 批量写入（同一事务，要么全成要么全败） | body：`{ objectType*, items: [{properties, pk?, title?}, …] }` | —（QA、toolkit） |
| `POST /objects/remove` | 删除一个对象（连带清掉它的关系边） | body：`{ objectType*, pk* }` | —（QA） |
| `POST /objects/modify` | **乐观锁修改**：带 `expectedUpdatedAt`，别人改过则返回 conflict（前端刷新重试） | body：`{ objectType*, pk*, set: {要改的字段}, expectedUpdatedAt? }` | —（QA） |
| `POST /objects/links` | **Search-Around 顺藤摸瓜**：从某对象沿某条关系走到另一头。**方向自动解析**（按对象在关系的 A 端还是 B 端定 forward/reverse）；走读侧 PEP 硬门 + 列脱敏 | 路径：`objectType`、`pk`、`link`；query：`view?`（场景校验）、`include?`（状态分层） | **浏览器**（对象详情关系钻取） |
| `POST /links/save` | 建立**一条关系边**（仅 Edge backing 关系可用；FK/连接表/中间对象关系显式拒绝） | body：`{ link*, aPk*, bPk*, properties? }` | —（QA） |
| `POST /links/remove` | 删除一条关系边（原 `DELETE /links`，20260919 改 POST 固定段） | body：`{ link*, aPk*, bPk* }` | —（QA） |

---

## 15. 对象集 load / aggregate（2 个端点）——查询的核心

"对象集"是本体查询的统一抽象：**一段递归组合的 JSON 代数，后端编译成一条 SQL**（含 JOIN，杜绝 N+1）。20260917 起读侧全走 **PEP 硬门**：行级策略把"看不见的行"直接折进查询条件，列脱敏在返回前抹值。

| 方法+路径 | 大白话作用 | 请求参数 | 谁在用 |
| --- | --- | --- | --- |
| `POST /object-sets/load` | 按对象集代数查一页对象 | body：`{ objectSet*: <代数>, limit?(默认100), offset?, subjects?(读侧主体覆盖，缺省回退上下文), view?(场景校验：terminal 类型必须是场景成员), include?(状态分层，默认仅 active) }` | **浏览器**（列表+过滤+钻取）、**搭建台**（对象列表+关系块）、工作室 |
| `POST /object-sets/aggregate` | 按对象集聚合统计（受限行不计入统计） | body：`{ objectSet*: <代数>, aggregation*: <聚合规格>, subjects?, view?, include? }` | **设计台**（计数徽标）、浏览器、搭建台、工作室 |

### 15.1 objectSet 代数（`op` 标签区分，可递归嵌套）

```jsonc
// ① 某类型全量
{ "op": "base", "objectType": "Order" }

// ② 过滤（包一层 filter；predicate 见下）
{ "op": "filter", "source": {…}, "predicate": { "kind": "eq", "property": "region", "value": "east" } }

// ③ 关系遍历（本体的灵魂）：沿关系从源集合走到相关集合
{ "op": "searchAround", "source": {…}, "link": "customerPlacesOrder", "direction": "forward" }  // forward | reverse

// ④⑤⑥ 集合运算（按 pk）
{ "op": "union", "left": {…}, "right": {…} }       // 并集
{ "op": "intersect", "left": {…}, "right": {…} }   // 交集
{ "op": "subtract", "left": {…}, "right": {…} }    // 差集

// ⑦ 静态集：直接给一组主键
{ "op": "static", "objectType": "Order", "primaryKeys": ["SO001","SO002"] }
```

**predicate 的 kind**：`eq / ne / gt / ge / lt / le`（`property` + `value`）、`in`（`property` + `values` 数组）、`contains`（子串匹配）、`isNull`、`and / or`（`predicates` 数组）、`not`（`predicate`）。不接受裸 SQL，天然防注入。

> 实际使用现状：浏览器/搭建台用了 `base + filter + searchAround + static`（钻取/关系块都是 searchAround 包 static），设计台只用 base 计数——`union / intersect / subtract` 是后端能力已就绪、页面未用。

### 15.2 aggregation 聚合规格

```jsonc
{ "kind": "count" }                                          // 计数
{ "kind": "groupCount", "property": "region" }               // 按属性分组计数
{ "kind": "groupSum", "groupBy": "region", "sum": "amount" } // 按属性分组求和
```

**load 响应**：`{ objectType, rows: [{pk, title, properties}…], limit, offset, hasMore }`。

---

## 16. 动作引擎辅助（8 个端点）

| 方法+路径 | 大白话作用 | 请求参数 | 谁在用 |
| --- | --- | --- | --- |
| `GET /action-logs` | 动作执行审计流水（谁在什么时候跑了什么动作、改了什么） | query：`action`（按动作过滤，可选）、`limit`（默认50，最大500） | —（QA / 运维排查） |
| `GET /action-outbox` | 副作用发件箱列表 | query：`status`（如 `pending`，可选）、`limit`（默认100） | —（QA） |
| `GET /action-outbox/config` | 出站配置快照（`{outboundEnabled, flowUrl, flowInstancesPath, webhookAllow}`，不含密钥）——排查"副作用为什么没发出去" | 无 | —（QA） |
| `POST /action-outbox/dispatch` | **手动投递**：抽取 pending 副作用按类型分发（SSE 事件 / 调函数 / webhook / 起流程引擎实例 / 触发报表计算）。**注意：服务已内置定时自动投递**（间隔默认 10s，`ONTO_OUTBOUND=off` 全局熄火；SKIP LOCKED 认领，多实例安全），此端点主要留给运维补投 | query：`limit`（默认50） | —（QA / 运维） |
| `POST /action-outbox/dispatched` | 投递完回写状态（成功→dispatched，失败→failed；原 `/action-outbox/{id}/dispatched` 已去路径化，id 入 body） | body：`{ id*, ok*: true/false, error? }` | —（dispatcher 回调） |
| `GET /flow/definitions` | 代理查询流程引擎已发布流程定义（副作用"触发流程"的**下拉选项来源**）；流程引擎不可达时容错返回空列表（前端降级自由输入） | 无 | **设计台、工作室** |
| `GET /report/definitions` | 代理查询报表模块的报表列表（副作用"生成报表"的下拉来源）；同样容错 | 无 | **设计台、工作室** |
| `GET /action-templates` | 内置动作模板清单（关账联动等预置组合）——"从模板新建动作"的来源 | 无 | **设计台、工作室** |

**副作用投递语义**（dispatcher 按 kind 分派）：`emitEvent` → SSE 事件流；`notification` → SSE 通知事件；`callFunction` → O5 函数求值；`webhook` → 真发 HTTP（host 白名单 `ONTO_WEBHOOK_ALLOW`，默认仅本机——SSRF 护栏）；`startBusinessProcess` → 调 cmx-flowengine v1 起实例（`ONTO_FLOW_URL`，默认 :8091）；`computeReport` → 触发 cmx-report 报表计算（默认 :8092）。

---

## 17. 安全策略 policies（3 个端点）——前端暂未使用

"策略"= 行级过滤 + 列级脱敏规则：谁能看哪些行、哪些列要打码。读侧已从"可选增强"升级为**硬门**（`/object-sets/load`、聚合与 Search-Around 都过 PEP：deny 403 / 受控类型默认拒 / 行残差折入 / 命中 marking 的列直接移除）；策略的管理界面还没建。旧旁路 `POST /secure/object-sets/load` 已于 20260920 移除——主链路即唯一安全路径。

| 方法+路径 | 大白话作用 | 请求参数 | 谁在用 |
| --- | --- | --- | --- |
| `GET /policies` | 列出全部策略 | 无 | — |
| `POST /policies/save` | 新建/更新一条策略 | body：`{ apiName*，displayName?, objectType?(作用的对象类型), subjectKind?(role/user，默认role), subject*, rowFilter?: [谓词数组，命中则这些行可见], denyMarkings?: [禁止查看的列标记], denyActions?: [禁止执行的动作], status?(默认active) }` | —（QA） |
| `POST /policies/remove` | 删除策略 | body：`{ apiName* }` | —（QA） |

---

## 18. 数据集成 funnel（7 个端点）——页面暂未使用（push 由 MDM 调）

"漏斗"= 把外部业务库的数据按映射规则灌进本体对象；不合格的行进"隔离区"，不污染主库。

| 方法+路径 | 大白话作用 | 请求参数 | 谁在用 |
| --- | --- | --- | --- |
| `GET /funnel/mappings` | 列出全部源→对象映射 | 无 | — |
| `POST /funnel/mappings/save` | 新建/更新映射（哪个源查询、主键取哪些列、字段怎么对应、**读源走哪个库**） | body：`{ objectType*, sourceQuery（可空=生成式默认路径）, keyColumns*, titleColumn?, propertyMap*, required?, sourceDbId? }`；`sourceDbId` = 读源执行的数据库池 db_id（toml `[[databases]]` 池名如 `fico-db`，或注册源懒注册名 `ontosrc_<id>`），**缺省/空 = 本体库 onto_pg**；工作室「映射明细与源查询」弹框可配置（20260920 起支持） | 工作室（映射明细弹框）、onto-toolkit |
| `POST /funnel/mappings/remove` | 删除某对象类型的映射 | body：`{ objectType* }` | — |
| `POST /funnel/sync` | **全量同步**：读源 → 按映射转换 → 合格的写入对象库，违规的进隔离区。响应带 `{read, written, quarantined}`（原 `POST /funnel/sync/{objectType}` 已去路径化，objectType 入 body） | body：`{ objectType* }` | 工作室（数据集成卡）、onto-toolkit |
| `GET /funnel/quarantine` | 看隔离区：哪些源行没进来、为什么（violations） | query：`objectType`（可选）、`limit`（默认100） | —（QA） |
| `GET /funnel/pipeline-status?object_type=` | 管道状态图数据（抽取/映射/索引三段计数；原 `/{objectType}` 路径形态已去路径化） | query：`object_type*`（蛇形，该端点未做 camelCase 映射） | —（QA） |
| `POST /funnel/push` | **MDM 字典数据事件推送入口**（MDM 分发引擎 webhook 订阅；服务身份 X-API-Key 鉴权）：按 dictCode 命中映射后增量同步对应对象 | body：`{ dictCode | dict_code, …事件负载 }` | **MDM** |

---

## 19. 反向导入 import + 流程回调 flow-callback（3 个端点）

| 方法+路径 | 大白话作用 | 请求参数 | 谁在用 |
| --- | --- | --- | --- |
| `POST /import/doc` | 导入 DOC（主从单据元数据）→ 自动建对象类型（头/行）+ 组合关系 | body：归一化后的 DOC JSON（调用方从 cmx-model 适配） | —（QA；fe 脚本用它造数） |
| `POST /import/dct` | 导入 DCT（字典元数据）→ 建参照对象类型 + 把字典项种成对象实例 | body：归一化后的 DCT JSON | —（QA） |
| `POST /flow-callback` | **流程审批结果回调**（cmx-flowengine 生命周期事件 webhook；服务身份 X-API-Key 鉴权）：`event=instance.completed` 且 `businessKey`（=对象 pk）能定位到对象时，回写 `reviewStatus="已通过"` + `lastReviewAt`。幂等：非 completed / 对象找不到 / 已同状态 → 一律 200 `{skipped:…}`。目标对象类型可配 `ONTO_FLOW_CALLBACK_OBJECT_TYPE`（默认 `Supplier`） | body：flowengine 事件 JSON（`event`、`businessKey`…） | **flow** |

---

## 20. SDK 生成 osdk + 统计 stats（2 个端点）

| 方法+路径 | 大白话作用 | 请求参数 | 谁在用 |
| --- | --- | --- | --- |
| `GET /osdk/typescript` | 按当前本体**生成一份 TypeScript 客户端代码**（强类型的对象接口 + fetch 封装），直接下载 `.ts` 文件（此端点免响应壳，返回 `text/typescript`） | 无 | —（QA / 外部开发） |
| `GET /stats` | 各类元素计数 + 最新检查点版本号 + 版本总数（控制台顶部统计块 / `/_mon` 监控的数据源） | 无 | **控制台** |

---

## 21. "没用到"接口汇总与解读

以下 **~25 个端点目前没有任何前端页面调用**（按价值分三类）：

**① 面向外部系统 / 未来页面的能力（后端已就绪，等 UI 跟进）**
- `POST /objects/save`、`/objects/save-batch`、`/objects/remove`、`/objects/modify`、`POST /links/save`、`POST /links/remove` —— 对象实例直写（M1 去路径化后 apiName/pk 全入 body）。当前数据从业务库集成（funnel）或经动作间接修改。
- 对象集代数中的 `union / intersect / subtract` —— 查询能力已实现，页面目前只用 base/filter/searchAround/static。
- `POST /object-types/validate` —— 设计台用的是保存期后端隐式校验 + 画布本地校验。
- `POST /action-types/execute-batch` —— 批量执行入口已通 QA（e2e o4m4），等业务页面接入。

**② 运维 / 调度向（本就该脚本或后台任务调，不该页面调）**
- `GET /action-logs`、`GET /action-outbox`、`GET /action-outbox/config`、`POST /action-outbox/dispatch`、`POST /action-outbox/dispatched`（id 入 body）—— 审计与 Outbox 投递闭环（**定时自动投递已内置**，手动 dispatch 主要留运维补投；QA 脚本全覆盖）。

**③ 治理能力先行、页面未建**
- 安全策略 3 个（`policies` ×3；旧旁路 `secure/object-sets/load` 已移除）——O6 动态安全已通 QA（且读侧硬门已在生产查询路径生效），缺策略管理界面；
- 数据集成 6 个（`funnel/mappings|sync|quarantine|pipeline-status`）——O3 已通 QA，缺配置界面（`funnel/push` 由 MDM 调，不算闲置）；
- 导入 2 个（`import/doc|dct`）——设计给 cmx-model 侧或运维脚本调用；
- `GET /osdk/typescript`、openapi/swagger —— 工具向。

> **给后续开发的提示**：若要为 ③ 类能力补页面，接口无需改动直接可用；策略管理界面是当前最明显的缺口（读侧硬门已上线，策略却只能脚本配）。

---

## 附 A：前端页面 + 控制台的接口调用底账（精确到行为；20260918 M2 起四页全部带 `?ontology=`（各自记忆、回落 default_ontology），下表不再逐条标注）

| 页面 | 调用的接口（页面加载即调的在前） |
| --- | --- |
| **设计台** designer.js（**已停维护**：R7.1 菜单节点移除，页面文件保留；下列调用 20260919 已同步新路由：六类保存走 `/save`、删除走 `POST /xxx/remove`，其余见历史记录） | `GET /manifest` → `POST /object-types/batch` → `GET /versions`；六类元素详情/保存/删除；`POST /action-types/{id}/dry-run`、`/execute`；`POST /functions/{id}/evaluate`；`GET /action-templates`；`GET /flow/definitions`、`GET /report/definitions`（副作用下拉）；`POST /snapshots`（存档）；`POST /object-sets/aggregate`（对象计数徽标）；另调门户 `POST /api/domains/tree`（DAM 分域树，独立 ：8097 无此路由静默失败） |
| **浏览器** explorer.js | `GET /manifest?include={四档状态}` → `GET /object-types/detail?apiName=` → `POST /object-sets/aggregate`（计数，支持 base/searchAround/filter 组合 + include）→ `POST /object-sets/load`（列表分页 50/页 + Search-Around 钻取：`{op:"searchAround", source:{op:"static",…}, link, direction}`） |
| **搭建台** workshop.js | `GET /manifest` → `GET /object-types/detail?apiName=` → `POST /object-sets/aggregate`（含关键字 contains(title) 过滤口径）→ `POST /object-sets/load`（列表 + 各关系块并发懒加载 searchAround）→ `POST /action-types/check-permission`（动作中心 PEP 批量预检，`subjects:["role:admin"]`）→ `GET /action-types/detail?apiName=`（动态参数表单）→ `POST /action-types/dry-run`、`/execute`（apiName 入 body，`actor:"workshop"`） |
| **工作室** studio.js + 八模块 | `GET /manifest?types=…&include=all`、`GET /views`、`GET /me/roles`（403 降级依据）、`GET /graph?view=…&include=all`（场景画布一条到位）、`GET /object-types?q=&dam=&page=&size=`（目录分页）；六类元素 `POST /xxx/save` 保存（带 version）+ `GET /xxx/detail?apiName=` 详情 + `POST /xxx/remove`；`GET /events?ontology=`（SSE 订阅：checkpoint-created / release-created / resource-changed / view-changed）；`POST /snapshots`、`GET /versions`、`GET /versions/detail?version=`、`GET /versions/diff?a=&b=`、`POST /versions/restore`（版本中心）；`POST /releases`、`POST /releases/remove`（发布标记）；`POST /lifecycle/transition`（状态流转）；`GET /revisions?kind=&apiName=`、`POST /revisions/revert`（修订时间线）；`POST /views/save`、`POST /views/layout`、`POST /views/remove`（场景管理）；`GET /flow/definitions`、`GET /report/definitions`、`GET /action-templates`；`POST /action-types/dry-run`、`/execute`、`POST /functions/evaluate`（apiName 入 body）、`POST /object-sets/aggregate`；另调门户 `GET /api/registry/dam`（DAM 注册表，404 静默回退 manifest 聚合） |
| **控制台** dashboard（`:8097/`；20260918 已适配：api 层统一注入 `?ontology=default_ontology`） | `GET /stats`、`GET /object-types`、`POST /object-types/save`、`POST /object-types/remove`、`GET /link-types`、`POST /link-types/save`、`POST /link-types/remove`、`GET /versions`、`POST /snapshots` |

## 附 B：QA 脚本覆盖面

- **仓根**：`qa-backend.sh`（建模全链：六类 CRUD + manifest + versions + stats）、`qa-object.sh`（对象写入/批量/删除/关系边/对象集加载聚合）。
- **`test/e2e/`（21 个）**：接口校验（o1）、FK backing（o2）、funnel（o3）、动作引擎与校验（o4 系列，含 Palantir P0/P1 对齐 o4m4：函数背书 / upsert / execute-batch / proposedChanges）、Outbox 手动与自动投递 + flow/report 连通（o4m3 系列、conn_flow_report）、清单 targets 物化 + check-permission（o4m6）、PEP 与乐观锁（o4_pep_optlock）、函数六运行时（o5）、策略硬门与带安全加载（o6 族）、headless 自描述（o7：openapi/docs/events）、DOC/DCT 导入（p1）、OSDK（p2）。
- **`test/fe/`（19 个）**：起本机 harness 反代 `/api/*` → :8097，经 `GET /api/native-pages/*` 取页源 blob import 驱动**真实页面**跑 UI 回归（designer / explorer / workshop 全覆盖 + 分组、主题、DAM、菜单、安全删除等专项），另含门户反代全链路人工走查脚本（`portal_manual_walkthrough.cjs`）。

## 附 C：想手工试接口

服务起好后（`cd backend/cmx-ontology && CONFIG_FILE=onto-server-dev.toml cargo run -p cmx-onto-server`）：

- 浏览器打开 `http://127.0.0.1:8097/api/onto/v1/docs` —— Swagger UI 里每个接口都能直接填参试跑；
- 或带开发免登录头：`curl -H "X-API-Key: cmx_sk_dev_A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6" http://127.0.0.1:8097/api/onto/v1/manifest`；
- SSE 试订阅：`curl -N -H "Authorization: Bearer <token>" http://127.0.0.1:8097/api/onto/v1/events`（免登录头亦可）；
- 门户反代场景把主机换成 `http://127.0.0.1:8080`（路径不变，`/api` 前缀经 `[center_client.services]` 转发）。
