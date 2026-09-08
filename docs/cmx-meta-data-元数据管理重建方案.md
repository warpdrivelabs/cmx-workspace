# cmx-meta-data —— 元数据管理 全新重建方案

> 目标：在 `presentation/cmx-meta-data/`（= `scripts/cmx-meta-data/`，与 cmx-model / cmx-mdm 并列）**全新重建**一套元数据管理能力，落地 [[DCT-DOC-FLC 元数据通用化国际化业务化方案]] 的核心主张。
>
> **硬约束**：① 不动 cmx-model 的代码与功能（并行独立，互不干扰）；② 无历史包袱（clean-room，不迁数据、不背旧 schema、不做兼容层）；③ 先出方案，不动代码。
>
> **已定决策**：
> - **形态**：独立微服务（一芯多壳，对标 cmx-model / cmx-mdm / cmx-report）。
> - **核心范式**：**统一 EntityType + Profile**（DCT/DOC/FLC 收敛为一个元模型 + 三 profile）。
> - **国际化**：结构 i18n + **外置翻译包**（对标 SAP：结构存 key，文本存 `i18n/<locale>.json`）。
> - **首批语言**：zh-CN + en-US。
> - **端口**：`:8096`（避开 portal 8080 / flow 8091 / report 8092 / model 8093 / rules 8094 / mdm 8095）。
>
> 状态：方案（草案）。日期 2026-08-25。

---

## 0. 结论先行（TL;DR）

- **一句话**：`cmx-meta-data` 是一个全新的、以"**统一实体元模型（EntityType）+ 三 profile**"为内核、**国际化优先（i18n-first）**、**语义类型驱动**、**业务/技术双视图**的元数据管理微服务；它不改 cmx-model，而是以更通用、更国际化、更业务化的范式**平行重建**同类能力。
- **为什么值得重建而非改 cmx-model**：cmx-model 背着真实运行数据 + 会计术语 + 单语言 + 三套割裂 schema 的历史包袱；本方案要的四大主张（统一模型 / i18n-first / 语义类型 / 双视图）若在 cmx-model 上做需大量兼容层。clean-room 重建可直接以目标范式落地，零妥协。
- **一芯多壳**：中立核 `cmx-meta-app`（`meta_routes::<S>()` + 大盘 + 前端联邦）+ 独立壳 `cmx-meta-server`（chassis bin :8096）+ 平台反代壳 `cmx-meta-proxy`（留 cmx-container）+ `web/` 前端联邦。
- **内核 = 一个元模型三种画像**：
  - `EntityType`（实体类型）：identity / role / fields[] / relations[] / aggregations[] / lifecycle / constraints[] / identityCode / i18n。
  - **profile: reference**（= 旧 DCT，引用/主数据）｜ **transaction**（= 旧 DOC，事务/单据，多层主子）｜ **composition**（= 旧 FLC，情境列规则，不建实体）。
- **字段三层解耦**：`structure`（建表）/ `semantic`（含义+semanticType+角色）/ `display`（locale-map caption + 组件 + 布局）。
- **国际化三件套**：全 label 用 locale-map key → 外置 `i18n/{zh-CN,en-US}.json` 翻译包；控制 token 与显示文本严格分离；BCP 47 + 回退链。
- **双视图工作台**：业务向导视图（问答式、业务词、零技术概念）↔ 技术 schema 视图（全字段、structure 层），同一事实源互为投影。
- **完整覆盖**（feature-complete，见 §3 能力清单）：定义 CRUD + 版本/默认 + 部署落库(DDL) + 字典数据维护 + 单据数据 + 情境列 + 编码 + 前端工作台，均以新范式重建。

---

## 1. 定位与边界

### 1.1 与 cmx-model 的关系（严格并行、零干扰）
| 维度 | cmx-model（不动） | cmx-meta-data（新建） |
|---|---|---|
| 端口 | :8093 | **:8096** |
| 核心模型 | DCT/DOC/FLC 三套割裂 schema（moduleMeta+dictionaryTables/voucherTables） | **统一 EntityType + 三 profile** |
| 国际化 | 单 zh_CN，fields 外无 locale 容器 | **i18n-first**，全 label locale-map + 外置翻译包（zh-CN/en-US） |
| 术语 | 会计术语（voucher/借贷/凭证批） | **领域中立**（entity/document/measure），会计入领域包 |
| 存储 | data/meta/**（真实运行数据）+ cmx_model_* 台账 + cf_*/cv_* | **独立新存储**（`data/` 独立目录 + 独立 DB schema/前缀，见 §6），与 cmx-model 零共享 |
| 数据库 | fico + cmx | **独立目标库/schema**（不碰 cmx-model 的表） |
| 前端 | web/ui-native/html（字典三工作台等） | **全新 web/**（双视图工作台） |

> **零干扰保证**：不 import cmx-model 的任何 crate；不读写 cmx-model 的 data/ 或表；端口/服务名/菜单 id/页面 id 全部新命名空间（`meta.*`）。仅**复用 cmx-container 的公用基础设施**（cmx-core/cmx-database-pg/cmx-web-chassis/cmx-web-monitor/cmx-service-base/cmx-api-types 等，跨 ws path，与 cmx-model 同源但只读依赖），不复用任何 cmx-model 域内 crate。

### 1.2 无历史包袱（clean-room）
- 不迁移 cmx-model 的 data/meta 定义文件；不提供旧 schema 兼容读；不背 `moduleMeta`/`voucherTables`/`dictKind` 等旧结构。
- 新平台自带**种子样例**（用新范式写的客户/供应商/物料等 reference + 订单/工单等 transaction + 情境列样例），演示能力、供上手，而非迁旧数据。
- 若未来需要从 cmx-model 导入，做成**独立的一次性 importer 工具**（不在核心路径、不成为长期兼容层）——本方案不含，留作可选后续。

---

## 2. 架构（一芯多壳，对标 cmx-model/cmx-mdm）

```
cmx-meta-data/                          # 新并列 workspace（scripts/ 下，= presentation/）
├── .cargo/config.toml                  # aliyun 镜像 + 定义 nora registry（复刻 cmx-model）
├── .env / meta-server.toml / meta.sh   # 启动契约（CONFIG_FILE / SERVER__PORT=8096 / [[databases]]）
├── rust-toolchain.toml / .gitignore
├── data/                               # ★ 独立存储：定义 + 翻译包 + 种子（与 cmx-model 无关）
│   ├── entitytypes/<domain>/<app>/<module>/<name>.json   # EntityType 定义（三 profile）
│   ├── i18n/{zh-CN,en-US}.json          # 外置翻译包
│   ├── semantic-types/registry.json     # 语义类型目录
│   └── seed/                            # 新范式样例（clean-room 演示数据）
├── web/                                 # ★ 全新前端（双视图工作台）
│   ├── ui-native/{index.json, sources/…}
│   └── ui-html/{index.json, index/, sources/…}
└── crates/
    ├── cmx-meta-model/                  # 中立域模型：EntityType/Field/Relation/SemanticType/Profile + i18n 类型；DB-free
    ├── cmx-meta-store/                  # 定义存储（JSON 文件读写 + DAM 寻址 + 版本 + resolve）+ i18n 包读写
    ├── cmx-meta-compile/               # EntityType → 物理 TableDefine 编译 + 语义类型→物理类型推导（对标 model-deploy 但全新）
    ├── cmx-meta-deploy/                 # 部署/落库：init 台账 + deploy 建表（DDL）+ SSE 流（复用 cmx-metadata DDL 引擎）
    ├── cmx-meta-data-svc/              # 数据服务：reference(字典行) + transaction(单据) 的 CRUD/装载（tokio-pg）
    ├── cmx-meta-app/                   # ★ 中立核：meta_routes::<S>() 全 handler + 大盘 + 前端联邦（不依赖 cmx-api-core）
    └── cmx-meta-server/               # ★ 独立壳：chassis bin :8096
# 平台侧（留 cmx-container）
crates/libs/cmx-meta/cmx-meta-proxy/    # ★ proxy-only 反代壳（MetaProxyModule + 页面反代）
```

> 依赖策略（同 cmx-model/cmx-mdm）：域内 crate 纯 path；基础设施跨 ws path 进 `../cmx-container`；外部 crate 走 aliyun。**不依赖 cmx-model 任何 crate。** 物理 DDL 复用 cmx-container 的 `cmx-metadata`（`PgTableDefineExecutor`，通用建表引擎，非 cmx-model 私有）+ sqlx `cmx-database` + tokio-pg `cmx-database-pg`。

### 2.1 门户接线（对标 model/mdm 的 merge_*）
- `[center_client.services].meta = { url = "http://127.0.0.1:8096" }`。
- container 新建 `cmx-meta-proxy`（`MetaProxyModule` 反代 `/api/meta/*` + `is_meta_owned_page` 页面反代 `meta.*`）。
- `routes.rs` 加 `merge_meta`（proxy-only，无内嵌——全新服务本就无内嵌）。
- 菜单：门户菜单加"元数据管理"入口，指向 `meta.*` 页面。

---

## 3. 能力范围（feature-complete 清单）

以 cmx-model 现有元数据管理能力为**对标基线**（下表为其真实能力，逐项以新范式重建；新平台端点前缀 `/api/meta/*`，页面命名空间 `meta.*`）：

| 能力域 | cmx-model 基线（端点数） | cmx-meta-data 重建映射 |
|---|---|---|
| **定义中心** | `/api/definitions/{list,config(GET/POST/DELETE),batch,default}`（6） | EntityType 定义 CRUD + 版本 + 设默认 + 批量（含外置 i18n 包联动）；三 profile 统一入口 |
| **部署落库(DDL)** | `/api/model/{db-state,init,init-plan-stream,init-stream,deploy,deploy-plan-stream,deploy-stream}`（7） | 库状态门闸 + init(建 `mt_*` 台账) + deploy(编译→建 `mr_*`/`mx_*` 表→台账) + SSE 计划/流式；**新增专用部署控制台页**（基线无独立页，仅靠大盘+SSE） |
| **字典数据(reference)** | `/api/dct/{meta,data/search,data/tokio-zmc-msgpack,entries(POST/DELETE),save,export,import}`（9） | reference 实体数据行：meta + 装载(零拷贝) + upsert + changeset 存 + 导入导出；**四态 relation 统一**平级/自分级/带分类 |
| **单据数据(transaction)** | `/api/doc/{data/*(7 变体),meta,save,save/batch,revisions,revision,restore}`（13） | transaction 实体数据：多驱动/传输装载 + 懒下钻 + 流式 + 存/批量存 + 版本快照/回滚 |
| **情境列(composition)** | `/api/flexible-combination/{list,config(GET/POST/DELETE),default,resolve,rule,validate,preview}`（9） | composition profile：规则表 CRUD + 解析(anchor→列) + 校验 + 预览；Overlay 唯一范式 + 裸码带标签 |
| **编码引擎** | `/api/code/{rules(GET/POST),rules/{code}(GET/PUT/DELETE),preview,preview/batch,generate,generate/batch,validate,gaps,gaps/take}`（12） | 编码规则 CRUD + 预览/铸号 + 断号；作 identity-code 能力接入 EntityType |
| **大盘/联邦** | `/`、`/api/model/stats`、`/api/{native,html}-pages/*` | `meta.*` 大盘 + stats + 前端页联邦 |

> 部署引擎细节（须等价重建）：`db-state` 门闸态（UNINITIALIZED / META_UPGRADE_REQUIRED / CURRENT）+ 每模块每 kind scenario 矩阵（create/upgrade/current/drift…）；init 建台账（幂等 CREATE IF NOT EXISTS，加法式永不 DROP）；deploy 编译定义→`PgTableDefineExecutor` 增量建表→写源档/台账/历史；SEED/MENU 部署。**改进点**：基线无独立部署页（靠大盘+SSE），重建提供 `meta.deploy.console` 专用页。

三类受众任务 → 能力：
- **建模（技术/建模用户）**：建/改/删/版本化/设默认 EntityType（三 profile）；语义类型选择；关系(四态)与聚合；校验规则；编码规则。
- **部署（运维/建模用户）**：库初始化(台账) + 定义部署落库(DDL) + 预览/流式进度 + 库状态门闸。
- **数据维护（业务用户）**：reference 数据行(平级/自分级/带分类统一) + transaction 数据装载/录入/版本。
- **情境列（业务/建模用户）**：composition 规则表编辑(锚点→列集)、预览、校验。
- **国际化（翻译/业务用户）**：翻译包编辑(zh-CN/en-US)、缺译检查、语言切换预览。

---

## 4. 核心内核：统一 EntityType 元模型

### 4.1 顶层 schema（一个模型，三种 profile）
所有定义都是一个 `EntityType`，`profile` 字段判别用途。领域中立、i18n-first：

```jsonc
{
  "kind": "EntityType",
  "coord": { "domain": "crm", "app": "sales", "module": "core" },   // DAM 三段坐标
  "name": "customer",                       // 稳定技术标识（ASCII, snake_case）——建表/API/公式引用
  "labelKey": "crm.customer.__name__",      // → i18n 包（不内联文本）
  "profile": "reference",                    // reference | transaction | composition
  "version": 1, "isDefault": true, "status": "draft|published",
  "identity": { "key": "id", "code": "customer_no", "label": "name" },  // 四逻辑角色列
  "fields": [ /* Field（三层解耦，见 4.3） */ ],
  "relations": [ /* RelationDef 四态（见 4.4） */ ],
  "aggregations": [ /* AggRule 上卷（transaction） */ ],
  "lifecycle": { /* StatusFlow 状态机（transaction） */ },
  "constraints": [ /* ValidationRule 表达式校验 */ ],
  "identityCode": { /* CodeRule 自动编号 */ },
  "updatedAt": "..."
}
```

### 4.2 三 profile 差异（DCT/DOC/FLC 的收敛）
| profile | 旧对应 | 语义 | 关键结构 |
|---|---|---|---|
| **reference** | DCT 数据字典 | 引用/主数据（"有哪些可选值"） | 单实体 + 可选 self-hierarchy / classification relation；identity.code/label |
| **transaction** | DOC 业务单据 | 事务数据（"要填哪些字段"） | 多层 `entities[]`（L1..Ln）+ relations(composition) + aggregations + lifecycle + constraints |
| **composition** | FLC 弹性组合 | 情境列规则（不建实体，装饰已有实体） | `targetRef`（指向某 transaction 实体的层）+ `dimensions`（每维引用一个 reference 实体）+ `rules[]`（anchor→columns，Overlay 范式） |

### 4.3 字段三层解耦（结构 / 语义 / 展示）
```jsonc
{
  "name": "amount",                                  // 稳定技术名
  "structure": { "dataType": "decimal", "precision": 18, "scale": 2, "nullable": false },  // 建表用
  "semantic":  { "role": "measure", "semanticType": "money", "unitRef": "currency" },       // 含义/类型/角色
  "display":   { "labelKey": "crm.order.amount", "widget": "money-input", "align": "right", "width": "140px" }  // UI（label 走 i18n key）
}
```
- 建表编译器只读 `structure`；组件/校验读 `semantic`；渲染读 `display`。三层独立演进、独立复用。
- `semantic.role` = dimension | measure | attribute | relation（保留 BI 三元+关系，业界标准）。

### 4.4 语义类型目录（semanticType，覆盖面关键）
`semanticType` 直接表达业务含义，平台据此推导物理类型 + 默认组件 + 默认校验 + 默认格式。目录存 `data/semantic-types/registry.json`，可扩展：
`entity-key / code / label / foreign-key(refEntity) / money(unit) / quantity(uom) / percent / email / phone / url / date / datetime / period / enum(options) / boolean-flag / geo / json / attachment …`
> 修 cmx-model 三硬伤：整数宽度不塌缩（int2/4/8）、未知类型报错不静默、单一权威 dataType→PG 映射。

### 4.5 关系四态（统一"平级/自分级/带分类/主子"）
`RelationDef { kind, parent, child, parentKey, childKey }`，kind ∈：
- `composition`（主子，= DOC 层级）｜ `self-hierarchy`（自分级，parent_id 自引用）｜ `classification`（带分类，分类实体→本实体）｜ `reference`（外键引用）｜ `many-to-many`（关系实体）。
- **收益**：旧"字典三工作台（平级/自分级/带分类）"退化为**同一 reference 实体 + 不同 relation 配置**，一套编辑器搞定。

### 4.6 控制 token 与显示文本严格分离
- 凡引擎按字面比较的值（如聚合目标 `to`、状态 code、profile、kind）一律稳定 ASCII token。
- 凡人看的文本（caption/name/message/label）一律 `labelKey` → 外置 i18n 包。**杜绝 cmx-model 的 `to:"上层"` 中文控制 token。**

## 5. 国际化（i18n-first + 外置翻译包）

### 5.1 外置翻译包（对标 SAP i18n bundle）
- 结构里只放 `labelKey`（如 `"labelKey": "crm.customer.name"`），**不内联文本**。
- 文本落 `data/i18n/<locale>.json`：`{ "crm.customer.name": "客户名称" }`（zh-CN）/ `{ "crm.customer.name": "Customer Name" }`（en-US）。
- key 命名：`<domain>.<entity>.<field>` + 特殊 `__name__`（实体名）/`__desc__`（描述）。
- **收益**：改翻译不动结构；翻译可交翻译团队独立维护；缺译一目了然。

### 5.2 回退链 + BCP 47
- locale 解析：请求 locale → 平台默认 → `x-default` → 显示 key 本身（便于发现缺译）。
- locale 标识用 BCP 47 连字符（`zh-CN`/`en-US`），不用下划线。

### 5.3 缺译治理
- 保存定义时校验：所有 `labelKey` 是否在 default locale 有值；缺译列 warning 清单。
- 翻译编辑器（前端 §7）：按实体/字段列出全 key × 全 locale 的矩阵，红标缺译。

### 5.4 数据行多语言（分阶段）
- 结构 i18n（本方案 M1-M6 覆盖）先行；**字典项数据行**的显示名多语言（如 `me_industry` 行的中英名）留 M7+（i18n 列或关联翻译表），方案标注为后续。

## 6. 存储设计（独立、与 cmx-model 零共享）

### 6.1 定义与翻译（文件）
- 定义：`data/entitytypes/<domain>/<app>/<module>/<name>.json`（新命名空间，非 cmx-model 的 `data/meta/definitions`）。
- 翻译：`data/i18n/{zh-CN,en-US}.json`；语义类型：`data/semantic-types/registry.json`；种子：`data/seed/`。

### 6.2 数据库（独立前缀，绝不碰 cmx-model 的表）
| 类别 | cmx-model（不动） | cmx-meta-data（新） |
|---|---|---|
| 台账/系统表 | `cmx_model_*` | **`mt_*`**（meta 台账：mt_meta / mt_entity / mt_deploy_history / mt_source …） |
| reference 物理表 | `cf_*` | **`mr_*`**（meta reference） |
| transaction 物理表 | `cv_*` | **`mx_*`**（meta transaction） |
| 对象注册 | `cmx_meta_table_define` | **`mt_table_define`** |
> 目标库可与 cmx-model 同一 PG 实例但**不同 schema 或不同前缀**，保证零冲突、可各自 drop/重建。独立壳 `[[databases]]` 配自己的库。

## 7. 前端：双视图工作台（全新 web/）

### 7.1 双视图（同一事实源，两种投影）
- **业务向导视图**（业务用户）：分步问答——"这是什么业务对象？(profile) 有哪些信息？(fields，用业务词+语义类型选择器) 值从哪来？(reference 关联) 要不要审批流转？(lifecycle)"——零技术词，产出即 EntityType。
- **技术 schema 视图**（技术用户）：表格化/JSON 编辑全字段含 structure 层。
- 二者实时互转，schema 为唯一事实源，向导为降噪投影 + 术语翻译。

### 7.2 工作台页面（新命名空间 `meta.*`，native/html 联邦，对标 cmx-model web/）
覆盖基线全部元数据管理界面（4 区工作台约定：explorer/content/property + 扩展 source/schema）：
- `meta.explorer`：DAM 树 + 实体列表（按 profile 分组：reference/transaction/composition）。
- `meta.entity.{list,design,source,inspector}`：实体定义 4 区编辑（**业务向导视图 design + 技术 schema source 双投影**）——统一替代旧 `dct/doc/base-def-*` 编辑器（含 5 种 reference 子类 + 多层 transaction + 字段集 overlay）。
- `meta.reference.data`（+ explorer/content/property）：reference 数据行维护，**四态 relation 统一**（平级/自分级/带分类/关系）——替代旧 dictflat/dicttree/dictcls/dictrel 四套。
- `meta.transaction.data`：transaction 数据装载/录入（N 层主子，metadata 驱动）——替代旧 doc-loader。
- `meta.composition.{editor,inspector,verify}`：情境列规则表编辑（维度/锚点/规则面板/公式 + validate/preview）——替代旧 FLC 编辑器。
- `meta.dam.registry`：DAM（域/应用/模块）注册中心。
- `meta.datasource.browser`：集群数据源浏览（按 db+版本只读浏览三 profile 定义）。
- `meta.deploy.console`：**新增专用部署控制台**——库状态门闸 + init/deploy 计划预览 + SSE 流式进度日志（替代旧"藏在 cluster-datasource 里的 SSE"）。
- `meta.i18n.editor`：翻译矩阵编辑（全 key × zh-CN/en-US）+ 缺译红标 + 语言切换预览。
- `meta.templates`：模板库（reference/transaction/composition 常见模板，选模板→改→存）。
- `meta.dashboard`（根 `/`）：能力大盘（实体数按 profile + 部署状态 + 缺译计数）。

### 7.3 技术栈与联邦（对齐平台既有，实测确认）
- **页面交付双模**（沿用平台）：
  - **native_pages**：`GET /api/native-pages/:id` → `{source, sourceType:js|html, rev, relPath}`；js 源 `import(blobURL)` 导出 `render()` 或 `{defaultView, views:{[view](ctx)}}`；`rev=xxhash64→16hex` + IndexedDB 缓存 + `If-None-Match`→304。
  - **html_pages**：`POST /api/html-pages/batch` → 声明式 HTML + `__designer_meta__`（pageData/pageFns/models: CmxMasterSlave/CmxColumnModel…）；同款 rev/缓存。
- **4 区工作台约定**（load-bearing）：menu-node 声明 `workspace.{explorer,content,property}`，每区 `views[]` 指 native/html 页 + `view` 名 + 可选 `-source`(CodeMirror)/`-schema`/`-verify` 扩展区；**隐藏 `-model` 页**为单一事实源（持 CmxMasterSlave/CmxColumnModel + 数据装载/存 API）；区间共享 `host.workspace.context` + 页级 CustomEvent 总线。
- **组件栈**：UI5 Web Components 2.23.2 + **纯 Web Component（非 Lit）** string-template + CodeMirror 6（JSON 源）+ Vite 8；数据层 `cmx-data-comp`（CmxColumn/CmxColumnModel/CmxMasterSlave/CmxDataSet/CmxDCTMeta/CmxDOCMeta/FlexibleCombinationEngine + ChangeSetCollector）；网格 `cmx-revo-grid`、表单 `cmx-ui5-form`、引用选择 `cmx-dict-select`；主题 `--sap*` 变量。

### 7.4 设计期编辑器（重建决策）
现状设计期编辑器是**门户 SPA 里的巨型 Web Component**（`portal-definition-manager.js` 245KB 管 DCT/DOC/BASE，`portal-flexible-combination-manager.js` 192KB 管 FLC），非按页联邦的独立单元。重建取舍：
- **方案（推荐）**：`cmx-meta-data` 自带全新设计期编辑器，作 native/html 联邦页（`meta.entity.*` / `meta.composition.editor`），门户经菜单 + F3 反代接入——与后端同仓、同范式（EntityType/i18n/semanticType），**不改门户 SPA**。
- 旧门户 SPA 的 `portal-definition-manager`/`portal-flexible-combination-manager` **保持不动**（服务 cmx-model）；新编辑器是平行新物，命名空间 `meta.*` 隔离。
- **菜单管理**（`portal-menu-editor`，导航元数据）非模型元数据核心，本方案列为**可选伴生模块**，默认不含（门户既有菜单管理继续用）。

## 8. 分阶段路线（每阶段独立可交付、可编译验证）

> **实施进度**（2026-08-25）：
> - ✅ **M0 骨架**：`cmx-meta-data/` workspace 建成（`.cargo/config.toml`/`.env`/`meta-server.toml`/`meta.sh`/`rust-toolchain.toml`/`.gitignore`/根 `Cargo.toml` + `cmx-meta-server` 空 chassis bin）。**双 DB 栈**数据源钩子（sqlx + tokio-pg，同 cmx-model）+ 根大盘占位 + `/_mon`。`cargo check` 绿（16.9s，exit 0），真机 boot 成功（:8096，双库注册 + `/`+`/_mon` 200）。建独立库 `cmx_meta` + `cmx_meta_biz`（clean-room）。坑：`init_infra` 需 `cmx-service-base` 的 `registry-config` feature。
> - ✅ **M1 统一 EntityType 域模型**（`cmx-meta-model`，DB-free）：落地方案核心——`EntityType{coord/name/labelKey/profile/identity/fields/relations/aggregations/lifecycle/constraints/identityCode}` + 三 profile + **字段三层解耦**（FieldStructure/Semantic/Display）+ **语义类型**（SemanticType 18 类，物理推导 + 默认组件）+ **DataType 整数宽度不塌缩**（Int2/4/8，修 cmx-model 硬伤）+ **关系四态** + 生命周期/校验/编号 + **LabelKey newtype**（i18n 引外置包）+ **控制 token 全 ASCII enum**（修 `to:"上层"` 之患）。`validate()` 结构自校验。**测试 3/3 绿**：客户(reference)往返+校验+语义推导(foreign-key→int8/email→varchar)、服务工单(transaction 双层+聚合+状态机)、缺 table 校验捕获——**两个非会计域(CRM/CSM)零会计词建成**。
> - ✅ **M2 编译 + 部署（真机闭环验证）**：`cmx-meta-compile`（EntityType→`cmx_core::TableDefine`：reference→1 张 `mr_*`、transaction→N 张 `mx_*`、composition→空；**整数宽度经 `ColumnDefine.db_type` 保留** int2/4/8，测试 2/2 绿）+ `cmx-meta-deploy`（`init_db` 建 `mt_*` 台账 3 表 / `deploy` 编译→`PgTableDefineExecutor` 建物理表→写 `mt_entity` 台账 / `db_state` 门闸）。server 加临时 3 端点（init/db-state/deploy，M4 迁 app）。**真机 E2E**：:8096 → init(`UNINITIALIZED`→`CURRENT`) → deploy 客户(reference)→**`mr_customer` 4 列真建成** + `mt_entity` 行 `crm/sales/core/customer/reference` → deploy 工单(transaction)→**`mx_ticket`+`mx_ticket_item` 建成**，`total_hours`→`numeric(10,2)` 精度保留，entity_count=2。**mr_/mx_ 前缀确认 clean-room 隔离**（非 cf_/cv_）。已知：create 路径走 cmx-metadata 通用引擎，`FieldType::String` 无长度时落 text（executor create 粗化，model 层仍保 varchar，升级路径可精确——文档记为后续）。
> - ✅ **M3 定义存储 + 数据服务（真机全通）**：`cmx-meta-store`（EntityType CRUD/版本/resolve/set-default，落 `data/entitytypes/**`；**独立 data_root**，不复用平台 assets.root；**外置 i18n 翻译包**读写 + set_key + **缺译检查**）+ `cmx-meta-data-svc`（reference 行 search/upsert/delete，PK 雪花铸号，db_id 缺省回退 biz）。server 加 M3 端点（entitytypes/i18n/data 共 10 个）。真机 E2E：存定义→列表→落盘；缺译查(4→翻2→剩2)→`zh-CN.json` 落盘；deploy→biz→upsert 无 db_id→`mr_customer` 行入 `cmx_meta_biz`。deploy 与 data-svc db_id 缺省均回退 biz，一致。全 workspace test 绿。
> - ✅ **M4 中立核 + 前端双视图（真机验证）**：`cmx-meta-app` 中立核（`meta_routes::<S>()` 收编 server 全部临时端点：部署/定义中心/i18n/数据行 12 路由 + 大盘 + stats；泛型 S、信封 cmx-api-types、不依赖 cmx-api-core）。server 重构为薄壳：`meta_routes::<()>()` + `cmx_form::serve::frontend_pages_routes`（native/html 联邦）+ 双 DB 栈钩子。前端首页 `meta.entity.workbench`（native JS，**业务向导视图 ↔ 技术 schema 视图**双投影同一 EntityType 事实源；explorer 列实体 + 语义类型下拉 + 保存/部署/缺译检查，纯原生 DOM）。真机 7/7 端点绿（含 native/html-pages 联邦），页面经 `/api/native-pages/meta.entity.workbench` 投递（rev=7a88cd…，11.6KB）。全 workspace test 绿。坑：server 头注释 `mr_*/mx_*` 的 `*/` 误闭合。
> - ✅ **M5 门户接线（真机 E2E）**：container 新建 proxy-only 薄壳 `cmx-meta-proxy`（`MetaProxyModule` 反代 `/meta` + `with_meta_page_proxy` 拦 `meta.*` 页面；零引擎依赖）。`routes.rs` 加 `meta_upstream()` + `merge_meta()`（无内嵌兜底）+ 装配 + topology。门户 `[services].meta={url=:8096}` + 白名单 `/api/meta`。container check 绿（1m41s）。**真机 E2E 6/6**：门户 :8080 → MetaProxy → :8096，db-state/stats/entitytypes/i18n + 页面 `meta.entity.workbench` **rev 字节一致（7a88cd…）**；**写路径亦通**：经门户 deploy→`mr_customer`、upsert→行入库、search→2 行。前端零改。
> - ✅ **M6 种子 + 翻译包 + 更多前端（真机全绿）**：**种子装载**——`cmx-meta-store::seed`（递归扫 `data/seed/entitytypes/**` 按 JSON 内 coord/name/version 落生效目录，复用 `defs::save` 走结构校验；`seed/i18n/<locale>.json` **非破坏合并**进生效包，只补缺失/空 key）+ app `POST /api/meta/seed` 端点。**三新范式种子**（零会计域）：`industry`(reference + self-hierarchy)、`customer`(reference + foreign-key→industry + money credit_limit)、`service_ticket`(transaction 双层 + 聚合 hours→total_hours + 生命周期 open/in_progress/closed + 约束 hours_positive)。**双语翻译包** `zh-CN.json`/`en-US.json`（各 31 键全覆盖）。**两新前端页**：`meta.data.maintenance`（引用数据行维护，按字段语义渲染表格/表单 CRUD，labelKey 走翻译包解析业务标题）+ `meta.i18n.editor`（zh-CN/en-US 并排逐键编辑 + 缺译红标 + 仅看缺译 + 新增键）。**真机 E2E 16 步全绿**：seed(3 定义 0 拒 + en 31/zh 29 补译) → 部署三实体(`mr_industry`/`mr_customer`/`mx_ticket`+`mx_ticket_item`) → **物理列校验**(int8→bigint 宽度保真、money/quantity→numeric 精度保真) → 数据行 upsert/search(money `5000000.00` 精度、雪花铸号) → 缺译检查(en-US 0 缺 / fr-FR 7 全缺，判别正确) → **seed 幂等**(二次 i18n_added=0) → 三页联邦(rev 各异) → **门户 :8080 fresh 全链**(db-state/seed/entitytypes/数据写读/i18n 写读 + 三页 rev 门户↔直连字节一致)。坑：起门户撞**既有平台库 schema 漂移**（`cmx_exclusion_rule_item.archived` 列缺失致 baseline 迁移失败，**与 meta 零关**，IAM 排他规则表旧版；补 7 列即通）。全 workspace 编译绿。

| 阶段 | 内容 | 验收 |
|---|---|---|
| **M0 骨架** ✅ | 新 workspace + chassis server :8096 + 双 DB 栈 | 绿 + boot |
| **M1 元模型** ✅ | `cmx-meta-model`（EntityType/Field 三层/semanticType/关系四态/i18n） | 测试 3/3 |
| **M2 编译+部署** ✅ | `cmx-meta-compile`（→TableDefine）+ `cmx-meta-deploy`（init mt_* / deploy mr_*/mx_*） | 真机建表闭环 |
| **M3 定义存储+数据服务** ✅ | `cmx-meta-store`（定义 CRUD/版本/resolve/set-default + i18n 包读写 + 缺译检查）+ `cmx-meta-data-svc`（reference 行 CRUD，db_id 缺省回退 biz） | 真机全通 |
| **M4 中立核+前端双视图** ✅ | `cmx-meta-app`（meta_routes::<S>() + 大盘）+ server 薄壳 + `web/` 双视图工作台 | 7/7 端点 + 页面联邦 |
| **M5 门户接线** ✅ | `cmx-meta-proxy`（反代壳）+ `merge_meta` + `[services].meta` + 白名单 | 门户→反代→:8096 E2E 6/6 |
| **M6 种子+i18n+测试** ✅ | 新范式种子(industry/customer/service_ticket) + zh-CN/en-US 翻译包 + seed 装载端点 + 数据维护/i18n 编辑页 + E2E | 端到端 16 步；中英切换；门户 fresh 全链 |

## 9. 风险与取舍

- **重建工作量大**：等于再造一遍模型中心（后端+前端）。→ 对策：最大化复用 cmx-container 公用设施（chassis/monitor/DDL 引擎/DB 层）；域内 crate 全新但薄；分阶段每阶段可用。
- **与 cmx-model 能力重叠**：平台出现两套元数据能力。→ 定位：cmx-meta-data 是"下一代范式"试验田/新项目首选；cmx-model 保留服务存量。二者端口/存储/命名空间隔离，互不干扰。是否最终替代 cmx-model 由后续演进决定，本方案不预设。
- **统一模型抽象过度**：简单字典也要填一堆 profile 字段。→ 对策：profile 强默认（reference 默认单实体、role=reference），向导视图零负担。
- **外置翻译包一致性**：结构改名/删字段导致孤儿 key。→ 对策：保存时校验 key 引用完整性 + 孤儿 key 清理工具。
- **物理 DDL 复用 cmx-metadata**：该 crate属 cmx-container 公用（flow/report 等也用），非 cmx-model 私有，复用不违反"不动 cmx-model"。→ 确认边界：只依赖 cmx-container 的 `cmx-metadata`，不碰 cmx-model 的 `cmx-model-deploy`。

