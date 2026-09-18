# CMX 引擎微服务 OpenAPI utoipa 注解范式改造方案与实施记录

> 日期：2026-09-18 ｜ 范围：`backend/cmx-mdm`、`backend/cmx-ontology`、`backend/cmx-flowengine` 三仓
> 决策：用户拍板弃用「路由表派生文档」路线，统一采用 utoipa 标准注解范式——每个 handler
> 挂 `#[utoipa::path]`，中央 `#[derive(OpenApi)] #[openapi(paths(...))]` 聚合，接入既有
> `ModuleRoutes` / `ModuleSet` 架构。经 /reviewplan 两轮对抗性审查闭合 12 条硬伤后实施。

## 一、范式四层模板（三仓同构）

| 层 | 内容 | 载体 |
| --- | --- | --- |
| ① 端点注解 | `#[utoipa::path(method, path = "<全外路径含 /api 前缀>", tag, summary, request_body, responses)]` | 各 handler fn（文档注释之下、fn 之上） |
| ② 切片聚合 | `#[derive(OpenApi)] #[openapi(paths(...))]` 显式入册全部端点（漏注解=编译错，漏入册=契约测试红）+ `openapi_seed()`（InfoBuilder + tags 元数据） | `<app>/src/openapi.rs` |
| ③ 装配挂载 | `ModuleRoutes::api_doc()` 返回切片；bin 组合根 `build_modules().merged_openapi(openapi_seed())` 驱动 SwaggerUi；`SwaggerUi` **根级全外路径挂载**（并进被 nest 的 api_router 会叠成 `/api/api/…`） | `<app>/src/module.rs` + `<server>/src/main.rs` |
| ④ 契约守护 | `api_contract` 测试：源码扫描 `.route(` 字面量（剔注释+去空白，括号深度取参）→ (method, path) 有序对集合与文档**双向相等**；扫描计数基线断言；操作质量门（tag/summary/200）；各仓专属硬约束 | `<app>/src/openapi.rs` `#[cfg(test)]` |

### 关键技术约定

- **seed 不带 servers**：注解 path 写全路径（含 `/api` 前缀），Swagger UI 以页面 origin 直发请求；带 servers 会叠加双前缀（Try-it-out 必 404）。flow 现网旧 builder 的 `servers: /api/flow/v1` + 全路径双前缀缺陷顺带修掉。
- **utoipa 5 行为边界**（已源码/编译验证）：从 handler 签名 `Json<T>` 推断请求体且要求 `T: ToSchema`，显式写 `request_body(content = …)` 即跳过推断；`Query<T>` 不做推断（无需 IntoParams）；`OpenApi::merge` 按 path 浅比较（同名静默丢弃后者）→ 一模块一切片，旧前缀别名模块不接 api_doc；tags 按 Tag 全等去重 → tags 元数据只在 seed 声明。
- **kernel 红线**：嵌套内核类型（`cmx-flow-model` / `cmx-onto-model`）不加 utoipa 依赖——顶层本地 Req 补 `utoipa::ToSchema` derive，字段为内核类型时 `#[schema(value_type = Object)]`。
- **handler 签名红线**：禁止为文档改签名（不把 `Json<Value>` 换成强类型 Req）。
- **响应标注**：JSON 端点统一 `(status = 200, description = "统一信封 {code,msg,data}", body = ApiResp<Value>)`；SSE 端点 `content_type = "text/event-stream"`；Prometheus `/metrics` `content_type = "text/plain; version=0.0.4"`。
- **文档/路由真源分离**：路由真源 = 链式 `.route()` 注册；文档真源 = handler 注解；第四层测试守护二者双向一致。

## 二、三仓实施记录

### 2.1 cmx-mdm（main `9329ed9`，19 文件 +491/−73）

- 13 个 handler 文件 + dashboard：57 操作全量注解，tag 细化 15 业务域；补齐存量漂移 2 条（`mdm_cr_webhook_create`、`mdm_stats` 有路由无注解）。
- `openapi.rs` 手写 builder → 双切片（`MdmApiDoc` + `MdmStatsApiDoc`）+ seed（info + 15 tags）。
- server 根级挂 SwaggerUi：`/api/mdm/docs`、`/api/mdm/openapi.json`（免认证）；`build_modules()` 单一装配真源。
- 契约测试 3 条：基线 57 操作 / 双向相等 / 质量门。验证：52+29+4+4 测试全绿，clippy 与 HEAD 基线持平（存量告警）。

### 2.2 cmx-ontology（feat/onto-status-version-scenario `75682ef`，23 文件 +1317/−123）

- 15 个 handler 文件：84 操作全量注解（10 业务域 tag；6 条手写 + 78 条按路由素材抢救生成）。
- `openapi.rs` 手写 `json!` 契约 → `OntoV1ApiDoc` + seed（info + 10 tags）；`LinkReq` 补 ToSchema；移除 `recursion_limit`。
- `OntoV1Module` 接 api_doc；`OntoCoreModule` 保持 None（与 v1 路径同源，merge 浅比较防互吞）。
- server 根级挂 SwaggerUi `/api/onto/v1/docs`、`/api/onto/v1/openapi.json`；swagger 特性 CDN → **vendored**（离线可用）。
- 契约测试：扫描基线 84 / 双向相等 / 质量门。验证：128 测试全绿（9 app 含 3 契约 + 104 model + 4 store-pg + 11 server），clippy 15=15 基线持平。
- **演进性变更声明**：文档由手写 JSON 升级为注解聚合，path/操作集合不变（`servers: /api/onto/v1` 语义由「页面 origin 直发」等价承接）；字段级 schema（本地 Req）为增量增强。

### 2.3 cmx-flowengine（本次改动，未提交）

- **解散 RouteDef 路由表**：`RouteDef`/`RouteMethod`/`defs_to_router`/`route_defs`/`v1_extra_defs` 全部移除，`lib.rs` 改为 **13 业务域链式子表**（审批定义/定义/实例/表单/待办/异步作业/子流程路由/条件/决策/身份/监控/事件订阅/运维）+ `v1_extras` 独立 fn（8 端点，**仅挂 /flow/v1**）；`flow_routes`/`flow_routes_v1` 签名不变，平台壳/独立壳零影响（cmx-container 现零引用，已核实）。
- **129 操作全量注解**（128 生成 + 1 手写）：tag/summary 全量迁移自原表；`request_body(content = <Req>, description = "<原 body 字段提示>")` 类型化——82 个本地 Req 补 ToSchema；4 处特殊处理：
  - `ApprovalDefContent` / `VarSchema`（内核类型）→ 字段级 `#[schema(value_type = Object)]`；
  - `SubRule` / `PreviewSample` / `BizLinkReq`（嵌套本地类型）→ 补 ToSchema；
  - `observe.rs`：`client_stats` 是 `cmx_web_monitor` 再导出（外部 fn 无法注解）→ 摘除再导出改**本地薄壳**委托，注解承载在壳上，路由引用路径零改动；
  - 裸 JSON 端点 `/dimensions/ancestors` → `body = Value` 不套信封。
- `openapi.rs` builder → `FlowV1ApiDoc`（129 paths 按域分组入册）+ seed（info + 15 tags，无 servers）+ 6 条契约测试：基线 129 / 双向相等 / 零可变段 / GET 白名单（/metrics、/events、/design/collab 双向）/ **v1_extras 不泄漏旧前缀**（装配级文本断言，剔注释后判）/ 质量门。
- `module.rs`：`FlowV1Module` 接 api_doc；`FlowCoreModule` None + 注释（旧前缀为同 handler 别名不单列文档）。
- `server main.rs`：`build_modules()` 唯一装配真源；SwaggerUi url 换 `merged_openapi(openapi_seed())`（URL 不变）。
- 验证：`cargo check` 全绿；`cargo test` 全部套件 0 failed（测试函数文本计数 HEAD 400 → 404，Δ+4 = 旧契约 2 条换新契约 6 条，零丢失）；clippy app 告警 7→5（重写 lib.rs 头注释顺带修复 2 条存量 doc-list 告警）。

## 三、技术债 016 范式更替说明

016 的原始方案是「RouteDef 单一真源表 + 文档派生」，flow 是唯一落地仓。本次更替为注解范式后：

- 016 的**验收目标不变**（全 POST 收敛、零可变段、GET 白名单、路由↔文档零漂移），守护手段从「表驱动派生」升级为「注解 + 源码扫描双向相等测试」——漂移面更窄（原 openapi_covers_all_routes 只防漏登，新范式连路径拼写漂移、方法写错、幽灵条目都拦）。
- flow 的 RouteDef 表机制删除；`api_contract` 硬约束单测语义原样保留于新范式第四层。

## 四、遗留记录（不修改，仅备案）

- **cmx-engine-kit `ModuleRoutes::api_doc` 注释定位漂移**：trait 注释称「不要求实现方引入 derive 或挂载 Swagger」，而本范式后引擎侧模块一律 derive + 挂载，注释口径偏保守。属 cmx-container 公用库，本轮不动（红线），后续随 cmx-container 文档批次更新。
- mdm 仓 clippy 存量告警与 HEAD 持平，未清理（超范围）。
- flow `openapi.rs` 请求体字段提示 description 沿用原表文案（camelCase 速查），字段级 schema 已由 82 个 Req ToSchema 承载，二者互补。

## 五、验证命令速查

```bash
cd backend/cmx-flowengine && cargo check && cargo test && cargo clippy
# 契约单跑：cargo test -p cmx-flow-app api_contract
```
