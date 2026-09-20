# 本体平台接口速查（演示造数常用）

> **M1 起**：除 /ontologies*、/data-sources*、/me/roles、/funnel/push 外全部接口必带 `?ontology=<apiName>`；下表仅列方法与 body，query 里的 ontology 不再逐行标注。

> 前缀 `/api/onto/v1`；免登录头 `X-API-Key`；信封 `{code:0, msg, data}`。POST+JSON body 为主，无 PUT。

## 定义层

| 接口 | body 要点 |
|---|---|
| `POST /object-types/save` | ObjectTypeDef 全量 upsert（camelCase；乐观锁 version 留 0 盲写） |
| `POST /link-types/save` | objectTypeA/B 必填；cardinality 缺省 oneToMany。`backing` 页面形状：`{"fk":{"sourceProperty","side"?,"targetProperty"?}}`——side 缺省按基数推导（oneToMany→b / manyToOne→a / oneToOne→a），targetProperty 缺省=**对端主键 pk 列**（严格 Palantir 语义），显式指定=对端属性对属性 JOIN（外键存非 pk 列场景）；锚点跨端校验，对端无此属性 400 拒。多对多专用：`{"joinTable":{"table","leftColumn","rightColumn"}}` 或 `{"intermediary":{"objectType","leftProperty","rightProperty"}}`。缺 backing = Edge 物化 ol_edge（配合 `POST /links/save` 建边） |
| `POST /interfaces/save` / `/shared-properties/save` | implements 校验：实现者须有同名同 baseType 属性 |
| `POST /functions/save` / `/action-types/save` | status="active" 才可求值/执行 |
| `GET /manifest` | 六类薄清单（页面左树真源） |

## 实例层

| 接口 | body 要点 |
|---|---|
| `POST /objects/save-batch` | body `{objectType, items:[{pk?, title?, properties:{…}}]}` 同事务；**空数组=只建表**（激活类型可查询） |
| `POST /links/save` | `{link, aPk, bPk}`；两端对象须已存在（删边 `POST /links/remove`，同 body） |
| `POST /objects/modify` | `{objectType, pk, set, expectedUpdatedAt?}`（None=盲写；版本冲突 409 conflict） |
| `POST /object-sets/load` | 对象集代数：`base/filter/searchAround{source,link,direction}/union/intersect/subtract/static` 任意嵌套 → 编译为一条 SQL；谓词 eq/ne/gt/ge/lt/le/in/contains/isNull/and/or/not |
| `POST /object-sets/aggregate` | `{objectSet, aggregation:{kind:"count"}}` 或 `{kind:"groupSum", groupBy, sum}` / groupCount |
| `POST /objects/links` | 一跳便捷 Search-Around：`{objectType, pk, link, view?, include?}`（方向按 A/B 端自动；去路径化替代旧 `GET /objects/{type}/{pk}/links/{link}`） |

## 集成与执行

| 接口 | 要点 |
|---|---|
| `POST /import/dct` | `{apiName, displayName, items:[{code,name}]}` 幂等；字典项当场物化 |
| `POST /import/doc` | 单对象模型（行折叠嵌套属性）；不产 LinkType、不导实例；cmx_origin 溯源 |
| `POST /funnel/mappings/save` | `{objectType, sourceId?/sourceDbId?, resource?, sourceQuery?, keyColumns, titleColumn?, propertyMap, required}`。物化映射唯一建立口（mode 恒 materialized；virtual 只能经 bind）；`sourceId`=注册源 id（优先）或兼容 `sourceDbId`（toml db_id）；`sourceQuery` 可空 = 由 resource+propertyMap 生成参数化 SELECT（生成式默认路径）；keyColumns 物化可多列联合（'\|' 拼 pk） |
| `POST /funnel/sync` | body `{objectType}` 全量同步；返回 `{objectType, written}`；违规入 oo_quarantine；**sync 覆盖对象全部 props** |
| `GET /funnel/quarantine?objectType=` / `GET /funnel/pipeline-status?object_type=` | 隔离区 / 管道三段状态。⚠ pipeline-status 参数是 **snake_case `object_type`**（PipelineQuery 无 rename_all）：`?objectType=` 静默丢值返回空，路径段写法 `/{type}` 404 |
| `POST /action-types/dry-run` \| `/execute` | 共用体 `{apiName, params:{…}, dryRun?, actor?, subjects?}`（apiName body 携带，去路径参数）；校验上下文含 `objects.<参数>`（object 参数自动装载对象状态，表达式可写 `objects.doc.status=='open'`）；响应含 `proposedChanges`（from→to diff）+ `executionLog` + `sideEffectPreview`，校验失败错误体带 `adminDetail`/`executionLog` |
| `POST /action-types/execute-batch` | 同事务逐项批量执行（`{apiName, items:[{params}], dryRun?}`）；任一项失败整批回滚；上限 `ONTO_ACTION_BATCH_MAX`（默认 100） |
| `POST /action-types/check-permission` | 动作可见性 PEP 预检 `{actions:[…], subjects:[…]}` → `{results:[{action, allowed, deniedBy, scopes}]}`；workshop 据此不渲染被拒动作 |
| `POST /action-outbox/dispatch` | **手动**分发发件箱（无 poller）；返回 `{dispatched, deferred, failed}` |
| `POST /functions/evaluate` | body 带 `apiName`（去路径参数）；derivedProperty：`{apiName, objects:{<input>:{objectType,pk}}}`；aggregation：`{apiName, objectSet, aggregation}`（objectSet 顶层单数） |
| `POST /snapshots` | `{summary}`；存档检查点（内容同上一版时去重不涨版本） |
| `GET /versions` / `POST /versions/restore` | 版本回看 / 回滚（直改 live 架构：回滚=整体恢复 live 并留痕） |
| `POST /api/onto/v1/flow-callback` | flowengine webhook 接收端（instance.completed → 按 businessKey 回写 reviewStatus/status） |

## 数据源与绑定

> `/data-sources*` 是全局连接管理（scope 例外路由，不带 ontology）；bind/unbind 带本体。

| 接口 | 要点 |
|---|---|
| `GET /data-sources` | 注册源清单（om_data_source；kind=pg/api） |
| `POST /data-sources/create` / `update` / `delete` | 注册表管理；config 里密码只存 `passwordEnv`（环境变量名），不落明文 |
| `POST /data-sources/probe` | `{id, resource?}` → `{reachable, columns}`；id 接受注册源 id **或** toml db_id（探测+结构反射双兼容） |
| `GET /data-sources/schema?id=` | 源表结构反射，**只认注册源 id**（toml db_id 的反射走 probe） |
| `POST /object-types/datasource/bind` | 虚拟直查绑定唯一写入口：`{objectType, mode:"virtual", sourceId, resource, keyColumns(恰1列), titleColumn?, propertyMap, required}`；走修订链强校验。普通 object-types/save 会剥离 datasource 指针（E2），绑定只能经 bind/unbind 维护 |
| `POST /object-types/datasource/unbind` | 解除虚拟绑定（物化无"绑定"态，解除=unbind 或 mappings/remove） |

## 环境备忘

- onto toml：`[onto] flow_api_key`（调 flow 服务身份）、`[[databases]] fico-db`（漏斗跨库源）、`flow_callback_object_type`（回调目标类型，缺省 Supplier）。
- 多本体：`GET /ontologies` 清单 / `POST /ontologies/create` 注册（`{apiName, displayName}`；如 finance_rev 收入确认独立本体）；造数前目标本体不存在会 40x，先注册再 `--ontology` 指定。
- 注册源密码：om_data_source.config.passwordEnv 指向环境变量名（如 ONTO_SRC_FICO_PW），probe unreachable 先查该变量是否在 onto 进程环境里。
- flow toml：`[service_rpc.services] onto` + `[service_auth] outgoing_api_key`（webhook 目录模式注入 X-API-Key）。
- 事件订阅：`POST :8091/api/flow/v1/event-subscribers/save` `{name, channelConfig:{service_key, callback_path, secret(必填)}, rules:[{eventTypes, keyPatterns}]}`。
- 冒烟三件套：`GET /action-outbox/config`（flowApiKeySet=true）→ `GET /flow/definitions`（代理通）→ 订阅 `/event-subscribers/test`（2xx）。
