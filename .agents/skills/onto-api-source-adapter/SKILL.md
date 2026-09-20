---
name: onto-api-source-adapter
description: 指导三方业务系统按 CMX 本体平台 API 查询协议 v1 开发数据源适配器（/onto-source/query · /onto-source/aggregate · /onto-source/schema 三端点）。当用户要求把业务系统数据以「API 数据源 / REST API 数据源 / 虚拟直查」方式接入本体平台、询问协议入参出参格式、filter 过滤 DSL 语法、能力矩阵 caps、错误码（40040/40044/40046/40047/40401）、要适配器示例代码或协议合规自测时必用。
---

# onto-api-source-adapter —— 本体 API 数据源适配器开发指南

## Overview

CMX 本体平台（cmx-ontology）支持把外部业务系统的数据以「API 数据源（kind=api）」接入并**虚拟直查**：
本体在查询时把对象集编译为**结构化 JSON 查询**下推给业务系统，业务系统自行转为底层查询后按协议返回。

**核心原则：本体不生成任何 SQL。** 业务系统的底层是 MySQL / Oracle / ES / 无库微服务，本体零感知——
这是**非 PG 存储接入本体的唯一路径**（PG 业务库走 `[[databases]]` 直连，不用本协议）。

业务系统开发者只需要做一件事：**实现 3 个端点，遵守协议 v1**。

```text
┌──────────────┐  POST {base}/onto-source/query    ┌──────────────────┐      ┌─────────────┐
│ cmx-ontology │──────────────────────────────────▶│ 业务系统适配器     │─────▶│ 任意存储      │
│  (本体平台)   │  结构化 filter + 分页（协议 v1）     │  (本文档的产出物)  │ 自转  │ MySQL/ES/…  │
│              │◀──────────────────────────────────│                  │◀─────│             │
└──────────────┘  {code,msg,data} 信封 + items        └──────────────────┘      └─────────────┘
```

## 何时用 / 何时不用

- ✅ 业务系统数据库**不是 PG**（MySQL / Oracle / 达梦 / ES…），或数据根本不在库里（微服务内存计算）。
- ✅ 业务系统不愿把数据库账号交给平台，只想以 HTTP API 受控地暴露查询。
- ✅ 单据（头+行）场景：明细行以嵌套数组挂在 props 里随头表一并返回。
- ❌ 业务库就是 PG 且可直连 → 用 toml `[[databases]]` / 独立凭证注册 **PG 数据源**（本体直接下推 SQL，无需开发适配器）。
- ❌ 需要把外部数据**拉进来物化**（漏斗全量同步）→ 现阶段漏斗仅支持 PG 源，API 物化属 M3 规划。

## 快速开始（四步）

1. **实现 3 个端点**（路径固定，挂在你的 baseUrl 下）：
   - `GET  /onto-source/schema`——能力矩阵 + 资源清单（不带 `type`）；资源字段清单（带 `?type=`）；
   - `POST /onto-source/query`——结构化查询（filter 下推 + offset 分页）；
   - `POST /onto-source/aggregate`——计数 / 分组计数 / 分组求和。
2. **照抄示例改造**：[`references/adapter-example.py`](references/adapter-example.py) 是零依赖
   （Python 标准库）可运行模板，含采购订单「头+明细行」+ 供应商两个资源。把 `RESOURCES` 换成你的数据即可。
3. **跑合规自测**：`python3 scripts/conformance.py http://127.0.0.1:8000`（详见该文件头注释，
   支持 `--type` / `--pk-field` / `--filter-field` 等参数换成你的资源与字段）。全绿再接平台。
4. **平台注册与绑定**（建模者在门户操作，无需写代码）：
   - 门户 → 本体工作室 → **数据源管理** → 新建数据源 → 类型选 **REST API** →
     填 baseUrl / 认证（密钥只填环境变量**引用名**，绝不填明文）/ 分页与治理 / 能力矩阵声明 →
     「测试连接」（实测探测，结果卡回显能力与资源清单）→ 保存；
   - studio 绑定向导选该源 → 选资源 → 字段反射导入 → 完成绑定；
   - 对象浏览器（explorer）验证：类型带「直查·API」徽章，过滤 / 分页 / 明细行子表正常。

## 三端点速查

> 完整字段表、filter DSL 文法、错误码语义见 **[references/protocol-v1.md](references/protocol-v1.md)（规范真源，实现前必读）**。

| 端点 | 请求要点 | 响应 data 要点 |
| --- | --- | --- |
| `GET /onto-source/schema` | 无参 → 全局；`?type=<资源名>` → 单资源 | `{caps:{filterOps,pageMax,totalMode,cursor,defaultOrder,aggregates}, resources:[{type,name,fields?}]}`；fields[] = `{name,baseType,sourceType?,comment?,fields?}` |
| `POST /onto-source/query` | `{version:1, type, filter?, page:{offset,limit}}` | `{items:[{pk,title,props}], total?, hasMore}`；`pk` **恒为非空字符串** |
| `POST /onto-source/aggregate` | `{version:1, type, filter?, aggregate:{kind:"count"\|"groupCount"\|"groupSum", groupBy?, prop?}}` | count → `{count}`；分组 → `{groups:[{key,count\|sum}]}` |

所有响应一律 `{code, msg, data}` 信封：`code=0` 成功；业务错误用协议错误码
（`40040` 版本 / `40044` 不支持的过滤 / `40046` 超页宽 / `40047` 不支持的聚合 / `40401` 资源不存在），HTTP 状态仍回 200。

## 红线（双侧 fail-closed，违反任一条对接会被打回）

1. **能力外请求必须显式拒绝**：未声明的算子回 `40044`、超页宽回 `40046`、不支持的聚合回 `40047`。
   ❌ 绝不静默降级为全量返回或静默截断——平台侧同样在能力矩阵预检后才会发出请求，双侧一致才不吐错数据。
2. **`items[].pk` 恒为非空字符串**（数字主键请转字符串）。pk 缺失 / 空值会让整页数据被平台拒收。
3. **翻页顺序必须稳定**（声明 `defaultOrder`，如按主键排序）。顺序不稳的源，offset 分页会跨页漂移重复 / 丢行。
4. **只读、幂等**：平台只会发 GET / POST 查询，任何 DML 语义都不该出现在适配器里；平台侧还有写保护
   （virtual 类型写端点一律 4xx）兜底。
5. **适配器要快**：平台默认单请求超时 8s（源上可配 `timeoutMs`，上限 60s）、per-source 限流（默认 QPS 10 /
   并发 4）、>2s 记慢查询日志。慢适配器会直接表现为浏览器里直查失败。
6. **请求里出现未知字段请忽略**（前向兼容），未知 `version` 才回 `40040`。

## 常见错误与排错

| 现象（平台侧报错） | 根因 | 处理 |
| --- | --- | --- |
| 「API 数据源不可达」 | baseUrl 不对 / 适配器没起 / 网络不通 | 先 `curl {base}/onto-source/schema` 自测 |
| 「不在白名单 …（SSRF 护栏）」 | baseUrl 的 host 未进平台 `onto.source_allow` 白名单 | 运维在 toml/env 放行业务系统 host（`ONTO_SOURCE_ALLOW`） |
| 「认证失败（HTTP 401/403）」 | 平台侧凭证环境变量未配或值错误 | 检查源 config 的 `auth.*Env` 引用名在平台环境里真实存在且有值 |
| 「协议版本过旧」（40040） | 适配器收到的 `version` ≠ 1 | 平台恒发 `version:1`；检查适配器是否误改 / 透传丢字段 |
| 「不支持此过滤：…」（40044） | 请求了 caps.filterOps 外的算子 | 属预期行为（能力矩阵生效）；要么实现该算子并在 caps 声明，要么前端不提供该过滤 |
| 「页宽超出上限」（40046） | limit > caps.pageMax | 平台按 caps 自钳制，出现即说明声明与实现不一致，修 caps 或实现 |
| 「资源不存在」（40401） | 绑定的 resource 名在适配器里不存在 | 资源名大小写敏感；重新绑定或补资源 |

排错技巧：平台出站请求带固定头 `X-Onto-Source: cmx-ontology`，适配器日志可据此识别平台流量；
平台侧每次调用落结构化日志（源 / 资源 / 行数 / 耗时），>2s 有慢查询告警。

## 协议要点备忘（详见 references/protocol-v1.md）

- filter 是**可嵌套 DSL**：`{"and":[…]}` / `{"or":[…]}` / `{"not":{…}}` / 叶子
  `{"prop":"<源字段>","op":"<算子>","value":…}`；九个算子 `eq/ne/gt/lt/ge/le/in/contains/isnull`
  （`in` 的 `value` 是数组，`isnull` 无 `value`）。
- `filter` 里出现的字段名是**源字段名**（绑定映射的左侧），不是本体属性名——适配器直接拿它去查底层存储。
- props 值类型约定：`string / number / boolean / ISO8601 字符串 / null / 数组`；
  **数组 = 单据明细行**（schema 里该字段 `baseType:"array"` 并带嵌套 `fields`）。
- `baseType` 五种：`string / number / boolean / datetime / array`（平台映射：number→double、
  datetime→timestamp、array→array、其余→string）。
- `totalMode` 三档：`exact`（回数字 total）/ `estimated`（约数）/ `none`（不给 total，
  平台前端显示「已加载 N 行」）。不声明时兜底为 `none`。
- 资源名规则：`^[A-Za-z][A-Za-z0-9_.-]{0,127}$`（即绑定 mapping.resource 的合法值）。

## 文件索引

| 文件 | 用途 |
| --- | --- |
| `references/protocol-v1.md` | **协议 v1 全量规范（真源）**：信封 / 三端点字段表 / filter DSL 文法 / caps / 错误码 / 认证 / 单据头+行约定 |
| `references/adapter-example.py` | 零依赖可运行适配器模板（Python 标准库；含单据头+行）；`python3 adapter-example.py` 后用 conformance 自测 |
| `scripts/conformance.py` | 协议合规自测（~20 项断言，参数化适配任意资源/字段） |
| 平台侧 e2e | `backend/cmx-ontology/test/e2e/_onto_source_demo.py`（演示适配器）+ `virtual_api_source.sh`（平台全链路 37 断言），可作对照实现 |
