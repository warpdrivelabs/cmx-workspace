# cmx-flow / cmx-rpt 反向代理评估与优化方案

> 日期：2026-08-22
> 范围：`cmx-container/crates/libs/cmx-flow/cmx-flow-api`、`cmx-container/crates/libs/cmx-rpt/cmx-rpt-api`（及其兄弟 `cmx-rule-api`）、挂载点 `cmx-platform-app/src/routes.rs`、对端认证桥 `cmx-flowengine/crates/cmx-flow-app/src/auth.rs`
> 结论速览：**架构形态正确（同源 BFF + 透明反代 + OBO 令牌传播，符合企业微服务演进最佳实践），但工程细节未达生产强度**——存在 2 个 bug 级问题（30s 总超时掐断 SSE/长导出；出站鉴权头未剥除客户端同名头）、三份 ~95% 重复实现、以及熔断/负载均衡/可观测性三块网关基线能力缺口。建议按 P0（止血）→ P1（结构化）→ P2（演进）三阶段落地。

---

## 一、现状梳理

### 1.1 架构形态：「后端一芯双壳」

```
浏览器 ──同源请求──> 门户 cmx-portal-server (:8080)
                        │  /api/flow/*           /api/report-design/* /api/rpt/* /api/report-source-bindings*
                        │  /api/native-pages/{id} /api/html-pages/{id}（按 id 归属拦截）
                        ▼
              FlowProxyModule / ReportProxyModule（进程内反代壳，ModuleRoutes 契约）
                        │  重写路径（flow：/flow/{rest} → {base}/api/flow/v1/{rest}；rpt：恒等 {base}/api{path}）
                        │  注入三层出站鉴权：
                        │    ① X-API-Key                 —— 服务身份（[service_auth].outgoing_api_key）
                        │    ② X-Delegated-User-Token    —— 终端用户原始 JWT（on-behalf-of）
                        │    ③ X-Request-Id              —— 链路追踪
                        ▼
              cmx-flow-server (:8091) / cmx-rpt-server（独立微服务）
                        │  S6 认证桥：API Key 验服务身份 → 委托令牌验签解真实用户+租户
                        ▼
                    租户库（flow_pg / iam）
```

关键机制：

| 机制 | 位置 | 说明 |
| --- | --- | --- |
| 双壳切换 | `cmx-platform-app/src/routes.rs:151-186`（`merge_flow`/`merge_report`） | `[center_client.urls].flow/report` 非空 → 反代壳；空 → 进程内嵌（仅 flow 有内嵌壳）或无路由 |
| API 反代 | `cmx-flow-api/src/proxy.rs:83-137`、`cmx-rpt-api/src/proxy.rs:92-137` | 重写 URL → 注入三层鉴权 → 双向流式转发（`Body::wrap_stream`，不整体缓冲） |
| 页面反代 | 两 crate 的 `page_proxy_mw`/`with_*_page_proxy` | 共享端点 `/api/native-pages/{id}` 按 **id 前缀归属** 中间件拦截：命中→转发，未命中→`next.run` 落回门户 handler |
| 对端认证桥 | `cmx-flowengine/crates/cmx-flow-app/src/auth.rs:139-216` | X-API-Key 命中 → 验服务身份；有委托令牌则验签解用户+租户（租户以令牌 claim 优先），失败退化为纯服务调用 |
| 配置 | `cmx-plugin/src/center_client/config.rs:33-57`、`cmx-portalservice/dev.toml:259+` | `flow = "http://127.0.0.1:8091"`；与 `center_client` 的 http_url 模式语义混用同一节 |

flow 与 rpt 的差异仅一处：flow 转发时**升级到 v1 正式契约**（`/api/flow/v1/{rest}`），rpt 恒等映射（`{base}/api{path}`）。

### 1.2 三份拷贝

`cmx-flow-api` / `cmx-rpt-api` / `cmx-rule-api` 的 `proxy.rs` 各自维护一套 `is_hop_by_hop` / `forward_request_headers` / `build_response` / 转发核，代码 ~95% 相同（各 ~230-290 行，合计 ~700 行，去重后共享核约 250 行 + 每域 ~30 行声明）。

---

## 二、优点（值得肯定，应保持）

1. **「一芯双壳」切换设计**：embedded 与 proxy 实现**同一个 `ModuleRoutes` 契约、同一路由前缀**，前端永远打同源 `/api/flow/*`，切独立微服务只改一行配置。这是标准的 Strangler Fig（绞杀者模式）渐进迁移 + BFF 边缘聚合，正是微服务拆分期的企业最佳实践。
2. **双向流式转发**：请求/响应体均 `wrap_stream` 逐块透传，不缓冲整个 body——大报表导出、SSE、大上传的内存安全有保障。
3. **逐跳头处理符合 RFC 7230 §6.1**：connection/keep-alive/transfer-encoding/upgrade/host/content-length 剥除正确，避免协议头污染。
4. **三层出站鉴权（服务身份 + OBO 委托 + 追踪 ID）**：与平台既有 `remote_importers::apply_auth_headers` 对齐，token propagation 采用业界标准的 on-behalf-of 模式；对端"API Key 验服务 + 委托令牌解真实用户、租户以令牌 claim 优先"的多租户处理正确，且有单测覆盖（`auth.rs` tests）。
5. **错误信封统一**：下游不可达时返回 502 `{code, msg}`，前端可程序化识别，不泄漏内部堆栈。
6. **页面反代按 id 归属拦截**：共享端点部分归属的难题用"前缀判定 + 未命中落回本地 handler"解决，恒等转发保证 rev/ETag 字节不错位，shell 零感知——思路聪明。
7. **无状态**：反代壳只持连接池与配置（§五允许的基础设施连接池），多节点门户可水平扩展。

---

## 三、问题与风险（按严重度排序）

### P0-1【bug】30s 总超时会掐断 SSE 与长耗时请求

`FlowProxyModule::new` / `ReportProxyModule::new` 里：

```rust
reqwest::Client::builder().timeout(std::time::Duration::from_secs(30))
```

reqwest 的 `ClientBuilder::timeout` 是**总期限**：从开始连接到**响应体读完**为止（含 `bytes_stream()` 的逐块读取）。因此：

- flow 的 SSE `GET /api/flow/v1/events`（`cmx-flow-app/src/lib.rs:69`）经门户反代**最多 30 秒必被切断**——代码注释声称"SSE 逐块透传"，机制上确实透传，但总超时会杀流；
- rpt 的慢计算（`/rpt/compute`）与大报表导出同样会中途截断；
- 下游 IP 不可达（丢包型故障）时每个请求挂满 30s 才报 502，故障期请求堆积。

### P0-2【安全/正确性】出站鉴权头未剥除客户端同名头，且 reqwest 是 append 语义

`forward_request_headers` 只剥逐跳头，**原样透传**客户端发来的 `X-API-Key` / `X-Delegated-User-Token` / `X-Request-Id` / `X-Tenant` / `X-User` / `Cookie`；随后注入平台凭证用的 `RequestBuilder::header()` 在 reqwest 0.12 中是 **append**（已核对 `reqwest-0.12.28/src/async_impl/request.rs:219`：`req.headers_mut().append(key, value)`）→ 产生重复头。而 flow-server 侧 `header_str` 用 `.get()` 取**第一个**值 → **客户端可控值优先于平台注入值**。后果：

- 任意登录用户可自带 `X-Delegated-User-Token`（自己的有效 JWT）直打门户 `/api/flow/*`，绕过平台注入逻辑，获得 flow 侧附加的 `service` 角色标记；
- `X-Request-Id` 可被伪造污染链路追踪；
- 更隐蔽的链路：当 flow-server 未配 `FLOW_API_KEYS` 且门户未配 `outgoing_api_key` 时（配置不全的部署），请求无 X-API-Key → flow `AuthMode::Off` → 直接信任透传的 `X-Tenant`/`X-User` 头 → **完全绕过认证**；
- `Cookie`（门户会话）被无条件转发给下游服务，属不必要的凭据泄漏。

修复很小：转发前剥除这批头（见 P0 方案）。

### P1-1【工程】三份 ~95% 重复实现

`is_hop_by_hop` / `forward_request_headers` / `build_response` / 转发核在 flow/rpt/rule 三处各一份，注释已经开始分叉。任何一处修 bug（比如上述 P0 两项）都要改三遍、验证三遍——**本方案 P0 的修复如果逐 crate 打补丁，就是在为下次漂移埋雷**，应与抽共享核同步做。

### P1-2【工程】页面归属清单双写，靠注释约定同步

`is_flow_owned_page`（`cmx-flow-api/src/proxy.rs:208-210`）的前缀清单与 `cmx-flowengine/web` 侧清单仅靠注释"与清单一致"约定。flow 侧新增页面 id 忘了同步门户清单 → 页面 404，且故障模式隐蔽（两边都"各自正确"）。

### P1-3【生产强度】无熔断/重试/健康短路

下游宕机时无快速失败机制：每个请求都要等满超时才 502，门户集群流量放大下容易形成请求堆积。企业网关基线要求熔断 + fail-fast。

### P1-4【生产强度】可观测性薄

仅失败路径 `tracing::error`；成功路径无耗时、无状态码、无 QPS/延迟/错误率指标，无法回答"流程接口今天慢不慢、错了多少"。下游日志还因缺 `X-Forwarded-For` 丢失真实客户端 IP，审计链路断裂。

### P2-1【集群】单基址、无负载均衡

`flow = "http://127.0.0.1:8091"` 只支持单实例下游。多实例 flow-server/rpt-server 无法水平扩展（与根 AGENTS §五集群约束冲突）。`center_client` 本有 `http_discovery`（nacos）模式，但反代路径直读 `urls.flow`，不受益。

### P2-2【配置】语义过载

`[center_client.urls].flow` 同时承担"http_url 模式的 import 端点"与"反代服务基址"两种语义（dev.toml 注释自己都在提醒"注意此处是服务基址，非 http_url 模式的 import 端点"），且与 `mode = "grpc"` 无关——易误配。

### 其他已知边界（记录在案，暂不动）

- **响应头 insert 语义**：`build_response` 用 `headers.insert`，多个 `Set-Cookie` 会被折叠（应 append）——当前下游不用 Cookie，属隐患非故障；
- **不支持 WebSocket**（`upgrade` 被剥）——当前无 WS 需求；
- `merge_flow` 中 `FlowProxyModule::new` 被调两次（routes + `with_flow_page_proxy`）→ 两个独立连接池，小浪费，抽共享核时顺带解决；
- POST 转发无重试是**对的**（body 已流式化不可 replay、非幂等），重试只应考虑 GET——见 P2 方案。

---

## 四、企业最佳实践对标

对标 Spring Cloud Gateway / Envoy / Traefik 等企业网关的能力基线：

| 能力 | 业界基线 | CMX 现状 | 评价 |
| --- | --- | --- | --- |
| 路由/路径重写 | ✓ | ✓（v1 重写/恒等两种） | 达标 |
| 流式透传（SSE/大文件） | ✓ | ✓（机制上） | 达标 |
| 身份传播（OBO） | ✓ | ✓（三层头 + 认证桥） | 达标，且有测试 |
| 头卫生（防伪造/防泄漏） | ✓ | ✗（同名头 append 冲突、Cookie 透传） | **缺口** |
| 超时治理（分级超时） | ✓ | ✗（单一 30s 总超时） | **缺口** |
| 熔断/快速失败 | ✓ | ✗ | **缺口** |
| 重试（幂等限定） | ✓ | ✗（无，但 POST 不重试是对的） | 缺口（低优） |
| 负载均衡/多实例 | ✓ | ✗（单基址） | 缺口（演进） |
| 可观测（指标/追踪） | ✓ | △（仅失败日志） | 缺口 |
| 无状态/水平扩展 | ✓ | ✓ | 达标 |

**结论：架构选型（应用层同源反代而非外部网关硬切）是对的，"骨架"符合最佳实践；差的是生产级网关的"运维三件套"（超时治理、熔断降级、可观测）与安全头卫生。** 不需要推翻重来，做增强即可。

---

## 五、优化方案（分阶段）

### P0：止血（预计 1~2 天，与 P1-1 合并落地更划算）

**P0-1 超时治理**

```rust
let client = reqwest::Client::builder()
    .connect_timeout(Duration::from_secs(3))    // 连接快失败（不可达 IP 3s 报 502，不再挂 30s）
    .read_timeout(Duration::from_secs(60))      // 单次读空闲超时（reqwest 0.12 支持）；只要流持续有数据就不触发，SSE/大导出安全
    .pool_idle_timeout(Duration::from_secs(90))
    .build();
```

去掉 `.timeout(30s)` 总期限。普通 API 如需总期限，用 per-request `RequestBuilder::timeout()` 覆盖。

**P0-2 头卫生**

- `forward_request_headers` 增加剥除清单：`x-api-key`、`x-delegated-user-token`、`x-request-id`、`x-tenant`、`x-user`、`cookie`（`authorization` 保留——flow jwt 直连模式复用它）；
- `build_response` 响应头 `insert` → `append`（修多 Set-Cookie 折叠隐患）；
- 注入时改用可覆盖语义（先 `headers_mut().remove()` 再 append，或直接依赖"已剥除"保证唯一）。
- 部署侧配套：flow-server 生产环境 `FLOW_API_KEYS` 必配（文档 + 启动告警升级为 fail-close 建议），封死"配置不全 → X-Tenant/X-User 直通"链路。

**P0-3 转发链路头**

补 `X-Forwarded-Proto`、`X-Forwarded-Host`（原 Host）；`X-Forwarded-For` 需要门户 `into_make_service_with_connect_info::<SocketAddr>()` 支持，确认门户已带 ConnectInfo 则一并补，否则先上前两个。

### P1：结构化（预计 3~5 天）

**P1-1 抽共享代理核 `cmx-proxy-core`（强烈建议与 P0 一起做）**

新建 `cmx-container/crates/libs/cmx-proxy-core`（依赖 axum + reqwest + cmx-traits + cmx-api-core），提供：

```rust
pub struct ProxyUpstream { base, api_key, client }        // 唯一连接池，routes 与页面反代层共享一个实例
pub enum PathRewrite { Identity, StripPrefixAdd(&'static str) }  // rpt=Identity，flow=→/api/flow/v1
pub struct ProxySpec { prefix(es), rewrite, owned_page_prefixes } // 每域声明式配置
pub fn proxy_router(spec) -> Router<CmxAppState>            // API 反代
pub fn page_proxy_layer(router, upstream, spec) -> Router<CmxAppState> // 页面反代
```

三个 `*-api` 退化为 ~30 行声明（前缀 + 重写策略 + 页面归属前缀），P0 的修复只改共享核一处。验证：`cargo check -p cmx-proxy-core -p cmx-flow-api -p cmx-rpt-api -p cmx-rule-api` + 下游 `cmx-portalservice` 编译（反代壳不引引擎源码，编译图不受影响）。

**P1-2 页面归属真源下沉（消除双写漂移）**

- 推荐：flow-server / rpt-server 各暴露只读端点 `GET /api/{域}/v1/meta/pages`（返回本服务拥有的页面 id 清单，frontend_pages 模块本就有该清单），门户启动时拉取 + 缓存 + 定时刷新（只读探测，多节点并发无害，符合 §五）；
- 兜底（可与上条并存）：反代转发后下游返回 404 时 `next.run` 落回门户本地 handler——新增页面即时生效，无需等清单同步（代价是 miss 时双请求，可接受）。

**P1-3 熔断 + 快速失败**

进程内三态断路器（每节点独立即可，属流量保护非业务状态，不违反 §五）：连续 N=5 次连接类失败 → open（直接 503 `{"code":503,"msg":"流程服务熔断中"}`，TTL 10s）→ half-open 放 1 个试探请求。放共享核，三个域自动受益。

**P1-4 可观测**

- 转发 span：`tracing::info_span!("proxy_forward", module, method, path)` + 完成时 `info!(status, elapsed_ms)`，慢转发（>3s）升 warn；
- 指标：按域统计 QPS / 延迟分位 / 5xx 率 / 熔断状态，对接门户既有监控体系（cmx-web-monitor /_mon 若门户已挂）；
- P0-3 的 XFF 头补齐后，下游日志恢复真实客户端 IP。

### P2：演进（按需排期）

**P2-1 多实例负载均衡**：`[center_client.urls].flow` 支持 `http://host1:8091,http://host2:8091` 逗号分隔多基址 + 原子轮询，配合 P1-3 断路器按节点摘除；零新依赖。后续如需动态发现，接 `center_client.http_discovery`（nacos `flow_service`）既有模式。

**P2-2 配置语义拆分**：新增独立节承载反代配置，`center_client.urls` 回归 http_url 模式语义：

```toml
[gateway.flow]
bases = ["http://127.0.0.1:8091"]   # 兼容旧单值 base
connect_timeout_ms = 3000
```

读 `gateway.*` 优先、缺省回退 `center_client.urls`（保留一个版本的兼容期）。

**P2-3 GET 幂等重试**：仅 GET/HEAD + 连接错误/502/503 + ≤2 次 + jitter；POST 永不重试（body 流式不可 replay 且非幂等）。

**P2-4 WebSocket**：如未来流程中心需要 WS，再做 upgrade 透传（hyper upgrade）；在此之前在共享核文档中明确"不支持 WS"为契约。

### 不建议做的

- **不要把反代上移到 Nginx/Ingress 硬切**：会丢失 OBO 三层鉴权注入、页面归属判定、v1 路径重写等应用语义（搬进网关插件的维护成本更高）。外部网关可继续承担 TLS 终止/外层 LB，应用层反代保留。
- **不要改 gRPC**：HTTP 契约已稳定且 SSE 依赖 HTTP 流，收益小破坏大。
- **不要在反代层解析/缓存 body 或做细粒度授权**：保持透明转发；身份传播在代理、授权在对端（flow 侧 T0b 已做），职责清晰。

### 验收清单

- [ ] 单测：头剥除矩阵（六类头全剥）、路径重写（Identity / v1）、响应头 append（mock 多 Set-Cookie）、断路器三态迁移；
- [ ] 集成冒烟：起 flow-server + 门户反代模式，`curl /api/flow/v1/stats` 通；SSE 持续 >60s 不断流；拔掉 flow-server → 3s 内 502/503（熔断后即时 503）；恢复后自动闭合；
- [ ] 回归：`urls.flow` 留空（内嵌模式）路由行为不变；页面反代命中/未命中两路径正确；
- [ ] 三域（flow/rpt/rule）统一由 cmx-proxy-core 承载，各自 crate 仅剩声明。

---

## 六、证据附录

- reqwest `RequestBuilder::header` 为 append：`~/.cargo/registry/src/*/reqwest-0.12.28/src/async_impl/request.rs` `header_sensitive` 内 `req.headers_mut().append(key, value)`；
- reqwest `ClientBuilder::timeout` 为总期限（含响应体读完）：reqwest 0.12 文档 "The timeout is applied from when the request starts connecting until the response body has finished"；
- flow SSE 端点：`cmx-flowengine/crates/cmx-flow-app/src/lib.rs:69`（`/events`，v1 契约下经反代暴露）；
- 认证桥与委托令牌语义：`cmx-flowengine/crates/cmx-flow-app/src/auth.rs:139-216`（API Key 优先、委托令牌租户 claim 覆盖 key 绑定租户、验签失败退化为服务调用）。
