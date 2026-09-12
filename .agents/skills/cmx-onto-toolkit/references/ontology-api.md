# 本体平台接口速查（演示造数常用）

> 前缀 `/api/onto/v1`；免登录头 `X-API-Key`；信封 `{code:0, msg, data}`。POST+JSON body 为主，无 PUT。

## 定义层

| 接口 | body 要点 |
|---|---|
| `POST /object-types` | ObjectTypeDef 全量 upsert（camelCase；乐观锁 version 留 0 盲写） |
| `POST /link-types` | objectTypeA/B 必填；cardinality 缺省 oneToMany |
| `POST /interfaces` / `/shared-properties` | implements 校验：实现者须有同名同 baseType 属性 |
| `POST /functions` / `/action-types` | status="active" 才可求值/执行 |
| `GET /manifest` | 六类薄清单（页面左树真源） |

## 实例层

| 接口 | body 要点 |
|---|---|
| `POST /objects/{type}/batch` | `[{pk?, title?, properties:{…}}]` 同事务；**空数组=只建表**（激活类型可查询） |
| `POST /links` | `{link, aPk, bPk}`；两端对象须已存在 |
| `POST /objects/{type}/{pk}/modify` | `{set, expectedUpdatedAt?}`（None=盲写） |
| `POST /object-sets/load` | 对象集代数：`base/filter/searchAround{source,link,direction}/union/intersect/subtract/static` 任意嵌套 → 编译为一条 SQL；谓词 eq/ne/gt/ge/lt/le/in/contains/isNull/and/or/not |
| `POST /object-sets/aggregate` | `{objectSet, aggregation:{kind:"count"}}` 或 `{kind:"groupSum", groupBy, sum}` / groupCount |
| `GET /objects/{type}/{pk}/links/{link}` | 一跳便捷 Search-Around（方向按 A/B 端自动） |

## 集成与执行

| 接口 | 要点 |
|---|---|
| `POST /import/dct` | `{apiName, displayName, items:[{code,name}]}` 幂等；字典项当场物化 |
| `POST /import/doc` | 单对象模型（行折叠嵌套属性）；不产 LinkType、不导实例；cmx_origin 溯源 |
| `POST /funnel/mappings` | `{objectType, sourceDbId?, sourceQuery, keyColumns, titleColumn, propertyMap, required}` |
| `POST /funnel/sync/{type}` | 全量同步；返回 `{read, written, quarantined}`；违规入 oo_quarantine；**sync 覆盖对象全部 props** |
| `GET /funnel/quarantine?objectType=` / `GET /funnel/pipeline-status/{type}` | 隔离区 / 管道三段状态 |
| `POST /action-types/{api}/dry-run` \| `/execute` | `{params:{…}, actor}`；dryRun 返回编辑集预演；校验失败 code=1 + msg |
| `POST /action-outbox/dispatch` | **手动**分发发件箱（无 poller）；返回 `{dispatched, deferred, failed}` |
| `POST /functions/{api}/evaluate` | derivedProperty：`{objects:{<input>:{objectType,pk}}}`；aggregation：顶层 `objectSet` + `aggregation` |
| `POST /snapshots` | `{summary}`；存档检查点（内容同上一版时去重不涨版本） |
| `GET /versions` / `POST /versions/restore` | 版本回看 / 回滚（直改 live 架构：回滚=整体恢复 live 并留痕） |
| `POST /api/onto/v1/flow-callback` | flowengine webhook 接收端（instance.completed → 按 businessKey 回写 reviewStatus/status） |

## 环境备忘

- onto toml：`[onto] flow_api_key`（调 flow 服务身份）、`[[databases]] fico-db`（漏斗跨库源）、`flow_callback_object_type`（回调目标类型，缺省 Supplier）。
- flow toml：`[service_rpc.services] onto` + `[service_auth] outgoing_api_key`（webhook 目录模式注入 X-API-Key）。
- 事件订阅：`POST :8091/api/flow/v1/event-subscribers/save` `{name, channelConfig:{service_key, callback_path, secret(必填)}, rules:[{eventTypes, keyPatterns}]}`。
- 冒烟三件套：`GET /action-outbox/config`（flowApiKeySet=true）→ `GET /flow/definitions`（代理通）→ 订阅 `/event-subscribers/test`（2xx）。
