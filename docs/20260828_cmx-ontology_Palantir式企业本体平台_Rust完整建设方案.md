# cmx-ontology · Palantir 式企业本体平台 · Rust 完整建设方案

> 版本 v1.0 · 2026-08-28
> 定位：以 **Palantir Foundry Ontology** 为蓝本，用 Rust 从零构建一套**可落地、可独立部署、可嵌入 cmx-\* 生态**的企业本体（Ontology）平台。本体是"企业的数字孪生"——既有**语义元素**（对象/属性/关系/接口，描述"是什么"），又有**动能元素**（动作/函数/动态安全，驱动"如何变"）。本方案覆盖：五大核心组件、数据持久化、前端交互与展示，以及与既有 cmx 微服务（flow / rulesengine / dataauth / model / hierarchy）的集成地图。
>
> 本文只出**方案**，不动代码。文中 Rust / SQL / REST 片段均为**设计示意**，用于锁定接口契约与数据形态，非最终实现。

---

## 目录

1. [背景与定位](#一背景与定位)
2. [Palantir 本体是什么（概念精要）](#二palantir-本体是什么概念精要)
3. [设计目标与非目标](#三设计目标与非目标)
4. [总体架构：Language / Engine / Toolchain 三层](#四总体架构languageenginetoolchain-三层)
5. [本体元模型（Metamodel — 平台的心脏）](#五本体元模型metamodel平台的心脏)
6. [五大核心组件](#六五大核心组件)
   - [6.1 组件一 · 本体建模引擎（语义核心）](#61-组件一--本体建模引擎语义核心)
   - [6.2 组件二 · 对象存储与索引引擎（Object Store & Index）](#62-组件二--对象存储与索引引擎object-store--index)
   - [6.3 组件三 · 动作引擎（Action Engine）](#63-组件三--动作引擎action-engine)
   - [6.4 组件四 · 函数与计算引擎（Function & Compute）](#64-组件四--函数与计算引擎function--compute)
   - [6.5 组件五 · 数据集成与管道（Object Data Funnel）](#65-组件五--数据集成与管道object-data-funnel)
7. [横切关注点](#七横切关注点)
   - [7.1 动态安全（复用 cmx-dataauth）](#71-动态安全复用-cmx-dataauth)
   - [7.2 多租户](#72-多租户)
   - [7.3 API 与 SDK（OSDK 对等）](#73-api-与-sdkosdk-对等)
8. [数据持久化设计](#八数据持久化设计)
9. [前端交互与展示](#九前端交互与展示)
10. [Rust 工作区与 crate 结构（一芯多壳）](#十rust-工作区与-crate-结构一芯多壳)
11. [技术选型](#十一技术选型)
12. [与 cmx-\* 生态的集成地图](#十二与-cmx-生态的集成地图)
13. [落地路线图 O0–O8](#十三落地路线图-o0o8)
14. [风险、权衡与边界](#十四风险权衡与边界)
15. [附录：术语表与参考](#十五附录术语表与参考)

---

## 一、背景与定位

传统 ERP / 数据平台把"数据"和"意义"分离：数据躺在几百张物理表里，"这行是谁、和谁有关系、能对它做什么操作"散落在无数应用代码、SQL、存储过程中。业务每变一次，就要在数据层、服务层、前端层三处同步改动，语义漂移、口径不一、权限失控随之而来。

**Palantir 本体（Ontology）** 给出的答案是：在原始数据之上架一层**操作型语义层**——把真实世界的实体、关系、可执行操作，一次性地建模为**对象类型 / 关系类型 / 动作类型 / 函数**，让所有应用（分析、录入、审批、AI Agent）都通过**同一个本体**读写，而不是各自绕过它直连数据库。这一层同时是：

- **语义的（Semantic）**：对象、属性、关系——描述"企业里有什么、彼此如何关联"（名词）；
- **动能的（Kinetic）**：动作、函数、动态安全——描述"人和系统如何受控地改变它"（动词）。

> 关键区别：普通"语义层 / 指标层"是**只读**的（BI 口味）；本体的动能层让写入也受同一套治理——**校验、副作用、审计无论哪个应用发起都一致生效**。这正是本体高于普通 metrics layer 的地方。

**本方案的定位**：你已有一套成熟的 cmx-\* 微服务生态（元数据 DCT/DOC/FLC、流程 flow、规则 rules、数据权限 dataauth、层级 hierarchy、报表 report）。本体平台不是另起炉灶，而是把这些既有能力**编织成一张统一的企业知识图谱**——本体是"语义总纲"，既有引擎是它的动能后端。cmx-ontology 作为**独立微服务工作区**（`:8097`）落地，遵循你已验证的"一芯多壳"范式，可独立部署、亦可反代内嵌门户。

---

## 二、Palantir 本体是什么（概念精要）

Palantir 用一组极小的原语描述整个企业。理解这些原语是本方案的地基。

| 原语 | 英文 | 一句话定义 | 例 |
| --- | --- | --- | --- |
| **对象类型** | Object Type | 真实世界实体/事件的 schema 定义，由一个个对象实例组成 | `机场` 类型；JFK、LHR 是它的对象 |
| **属性** | Property | 对象类型的特征（字段） | 机场的 `iata_code`、`经纬度` |
| **关系类型** | Link Type | 两个对象类型间的关系 | `航班` —(降落于)→ `机场` |
| **接口** | Interface | 描述对象类型"形状与能力"的多态类型 | `可定位物` 接口（凡有经纬度者皆可实现） |
| **共享属性类型** | Shared Property Type | 跨对象类型复用的标准属性定义 | 全局统一的 `币种`、`国家代码` |
| **动作类型** | Action Type | 用户一次性对对象/属性/关系施加的一组编辑 + 副作用的 schema | `改签航班`：改属性 + 发通知 + 触发流程 |
| **函数** | Function | 输入参数、返回输出的代码逻辑；原生集成本体，可吃对象/对象集 | `计算延误风险(航班) -> 分数` |
| **对象集** | Object Set | 对象的集合（可保存、可组合、可遍历），读取的基本单位 | "今天所有延误 > 30min 的航班" |

后端由三个概念层驱动（Palantir 官方框架）：

- **Language 语义层**：类型系统、动作、逻辑——定义"本体长什么样"。
- **Engine 引擎层**：读、写、批量变更，以及 CDC（变更数据捕获，低延迟镜像）——把定义变成运行时。
  - **Object Storage V2**（取代旧的 Phonograph/OSv1）：本体的规范数据存储，专门优化高速索引、**Search-Around（关系遍历）**、写回。
  - **Object Data Funnel**：编排"数据源 + 用户编辑"→ 索引进对象库，并持续保鲜。
  - **Object Set Service (OSS)**：服务所有读取——搜索、过滤、聚合、加载对象；对象集可静态（存主键列表）或动态（存定义）。
- **Toolchain 工具链**：SDK（**OSDK**，从本体生成强类型客户端）、DevOps、各类 UI（Ontology Manager 建模、Workshop 搭应用）。

> 一处务实的边界：Palantir 用**专有表示**（Object/Link/Action Type），不走 W3C 的 OWL/RDF/SPARQL。本方案对齐这一取舍——追求**操作型可用**而非学术型可推理，元模型自定义、面向工程落地。

---

## 三、设计目标与非目标

### 3.1 目标

| # | 目标 | 衡量 |
| --- | --- | --- |
| G1 | **语义/动能双层完整**：对象、属性、关系、接口 + 动作、函数、动态安全俱全 | 五大组件均可端到端跑通一个案例 |
| G2 | **写入受治理**：任意应用发起的写，都过同一套 校验→编辑→副作用→审计 | 绕过动作直改对象库 = 不可能（仅 Funnel/Action 两个受控入口） |
| G3 | **读取可组合**：对象集代数（过滤/并/交/差/Search-Around）编译为一次高效查询 | 关系遍历不 N+1；下推到 PG |
| G4 | **一芯多壳 + 可独立部署**：中立核 + 内嵌壳（门户反代）+ 独立壳（`:8097`） | 与 flow/rules 同构；门户字节级复现零回归 |
| G5 | **最大化复用 cmx 生态**：不重造 规则/流程/权限/层级/元数据 | 动作校验走 rules、副作用走 flow、安全走 dataauth |
| G6 | **本体可演进**：类型加字段/改关系/迁移实例，不停机、可回滚 | 借鉴 flow A9 实例迁移思想 |
| G7 | **多租户**：db-per-tenant，租户间本体与对象数据物理隔离 | 复用 flow S2 / dataauth 的租户范式 |

### 3.2 非目标（明确不做，避免范围蔓延）

- ❌ 不实现 OWL/RDF/SPARQL 推理机（对齐 Palantir 专有表示）。
- ❌ 不自建分布式计算集群（Palantir 的 Spark 下推）；大规模计算下推到 PG / Polars，超限场景给出明确边界（见 §14）。
- ❌ 首版不做地理空间高级检索（GeoShape 相交等）与向量语义检索——预留 `Geo*`/`Vector` 属性类型与索引接口，实现留到后续里程碑。
- ❌ 不做完整"无代码应用搭建台（Workshop 全功能）"——前端首版聚焦建模台 + 对象浏览器 + 动作表单，应用搭建给最小可用。

---

## 四、总体架构：Language / Engine / Toolchain 三层

```
┌──────────────────────────────────────────────────────────────────────────┐
│  TOOLCHAIN 工具链（前端 + SDK）                                             │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐    │
│   │本体建模台│ │对象浏览器│ │应用搭建台│ │管道监控台│ │ OSDK 代码生成 │    │
│   │Onto Mgr  │ │Explorer  │ │Workshop  │ │Funnel Ops│ │ Rust / TS 客户端│  │
│   └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────────┘    │
├──────────────────────────────────────────────────────────────────────────┤
│  ENGINE 引擎层（运行时）                                                     │
│   ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐  │
│   │②对象存储  │ │③动作引擎  │ │④函数计算  │ │ 读:对象集  │ │写:Funnel  │  │
│   │  与索引   │ │ Action    │ │ Function  │ │ 代数编译器 │ │ 数据管道  │  │
│   │ObjectStore│ │ Engine    │ │ &Compute  │ │Object Set │ │Integration│  │
│   └───────────┘ └───────────┘ └───────────┘ └───────────┘ └───────────┘  │
│   ── 横切：动态安全(PDP/PEP) · 多租户 · 审计/CDC · 事件总线(SSE/webhook) ──  │
├──────────────────────────────────────────────────────────────────────────┤
│  LANGUAGE 语义层（定义）                                                     │
│   ①本体建模引擎：ObjectType · PropertyType · LinkType · Interface           │
│                  · SharedPropertyType · ActionType · FunctionType（元模型） │
└──────────────────────────────────────────────────────────────────────────┘
        ▲ 读写定义                                     ▲ 物化/查询对象
        │ om_*（本体元数据）                            │ oo_* / ol_* / oe_*（对象/关系/编辑）
        ▼                                              ▼
   ┌─────────────────┐                        ┌──────────────────────────────┐
   │ PostgreSQL       │                        │ PostgreSQL（对象数据库）        │
   │ 元数据库(定义)    │                        │ + 搜索索引(GIN/pg_trgm/pgvector)│
   └─────────────────┘                        └──────────────────────────────┘
```

**数据双库分治**（对齐 Palantir "定义 vs 对象" 分离）：

- **元数据库**（本体定义）：`om_*` 表族，存对象/关系/动作/函数**类型定义**。低频写、强一致、有版本。
- **对象数据库**（物化对象）：`oo_*`（对象实例）、`ol_*`（关系边）、`oe_*`（用户编辑日志）、`os_*`（对象集）。高频读写、面向查询与索引优化。二者可同库不同 schema，也可分库（大租户）。

**两个受控写入口**（G2 的物理保证）：
1. **Object Data Funnel** —— 从外部数据源（数据集/表/流）批量/增量灌入对象；
2. **Action Engine** —— 用户/系统发起的编辑（写回）。

对象数据库**不对外开放裸 SQL 写**；所有变更必经上述二者之一，天然可审计、可回放、可 CDC 外发。

---

## 五、本体元模型（Metamodel — 平台的心脏）

元模型是全平台的"名词表 + 动词表"。以下 Rust 类型为**契约示意**，落在 `cmx-onto-core` crate（框架无关，纯类型 + trait）。

### 5.1 资源标识与国际化

```rust
/// 本体资源统一标识：ri.ontology.<tenant>.<kind>.<uuid>，对齐 Palantir RID 习惯
pub struct OntologyRid(String);

/// 复用 cmx 既有 i18n 容器（zh-CN / en-US 双语，见 cmx-meta-data i18n-first）
pub struct I18nText { /* { "zh-CN": "...", "en-US": "..." } */ }

pub enum TypeStatus { Experimental, Active, Deprecated }  // 类型生命周期
```

### 5.2 对象类型 ObjectType（名词）

```rust
pub struct ObjectTypeDef {
    pub api_name: String,          // 稳定 API 名，如 "Customer"（跨版本不变，命名的锚）
    pub rid: OntologyRid,
    pub display_name: I18nText,
    pub description: I18nText,
    pub icon: IconSpec,
    pub color: String,             // 图谱着色
    pub primary_key: PropertyApiName,   // 主键属性
    pub title_property: PropertyApiName,// 展示标题（对象卡片用哪个字段当"名字"）
    pub properties: Vec<PropertyTypeDef>,
    pub implements: Vec<InterfaceApiName>,  // 实现的接口（多态）
    pub datasource: Option<DatasourceRef>,  // 背书数据源（Funnel 从哪里灌）
    pub status: TypeStatus,
    pub visibility: Visibility,             // Prominent / Normal / Hidden
    // —— cmx 集成锚点 ——
    pub cmx_origin: Option<CmxOrigin>,      // 若由 DOC/DCT 生成，回指其来源
}
```

### 5.3 属性类型 PropertyType（字段）

```rust
pub struct PropertyTypeDef {
    pub api_name: String,
    pub display_name: I18nText,
    pub base_type: PropertyBaseType,
    pub required: bool,
    pub value_constraints: Vec<ValueConstraint>,   // 落到规则引擎 FEEL（见 §6.4）
    pub shared_property: Option<SharedPropertyApiName>, // 引用共享属性类型
    pub is_indexed: bool,                          // 是否建搜索索引
    pub is_title_key: bool,
    pub semantic_type: Option<SemanticType>,       // 复用 cmx-meta-data semanticType（金额/百分比/邮箱…）
    pub security: Option<PropertyMarking>,         // 列级安全标记（marking），接 dataauth
}

pub enum PropertyBaseType {
    String, Integer, Long, Double, Decimal, Boolean,
    Date, Timestamp,
    Array(Box<PropertyBaseType>),
    Struct(Vec<PropertyTypeDef>),                  // 结构体属性（对齐 OSv2 struct）
    Attachment, MediaReference,                    // 附件/媒体
    Marking,                                        // 安全标记值
    Geohash, GeoShape,                             // 地理（首版占位，索引后置）
    Vector(u32),                                   // 向量（维度；语义检索占位）
}
```

### 5.4 关系类型 LinkType（连线）

```rust
pub struct LinkTypeDef {
    pub api_name: String,
    pub rid: OntologyRid,
    pub cardinality: LinkCardinality,              // OneToOne | OneToMany | ManyToMany
    pub side_a: LinkSide,                          // { object_type, role_api_name, display }
    pub side_b: LinkSide,
    pub backing: LinkBacking,                      // 关系如何落到存储
}

pub enum LinkBacking {
    ForeignKey { on: LinkSideRef, fk_property: PropertyApiName }, // 1:N 靠外键属性
    JoinTable  { table: String, a_key: String, b_key: String },  // N:M 靠中间表 ol_*
    Intermediary { via_object_type: String },                    // 关系本身是对象（携带属性的边）
}
```

> **层级关系**（组织树、BOM、科目表）是 LinkType 的特例（自关联 `OneToMany`）。此处**复用 `cmx-hierarchy`**（主从 + 拓扑排序引擎）承载"祖先/子孙/路径"查询，不重造。

### 5.5 接口与共享属性（多态与标准化）

```rust
pub struct InterfaceDef {                          // 对象类型的"形状契约"
    pub api_name: String,
    pub properties: Vec<SharedPropertyApiName>,     // 接口要求实现者具备的共享属性
    pub extends: Vec<InterfaceApiName>,             // 接口继承
}
pub struct SharedPropertyTypeDef {                  // 全局标准属性（一处定义，处处引用）
    pub api_name: String,
    pub base_type: PropertyBaseType,
    pub semantic_type: Option<SemanticType>,
}
```

接口带来**多态查询**：一次 `按接口 可定位物 查询` 即可跨"机场/仓库/门店"所有实现类型统一返回，前端无需知道具体子类型。

### 5.6 动作类型 ActionType（动词）

```rust
pub struct ActionTypeDef {
    pub api_name: String,
    pub rid: OntologyRid,
    pub display_name: I18nText,
    pub parameters: Vec<ActionParameter>,          // 表单参数（可绑对象/对象集/标量）
    pub logic: Vec<EditRule>,                       // 一组编辑（原子提交）
    pub validations: Vec<SubmissionCriterion>,      // 提交校验（FEEL/规则引擎）
    pub side_effects: Vec<SideEffect>,              // 副作用
    pub function_backing: Option<FunctionRef>,      // 函数背书动作（复杂逻辑走函数）
}

pub enum EditRule {
    CreateObject { object_type: String, from: ParamMapping },
    ModifyObject { target: ParamRef, set: Vec<PropertyAssignment> },
    DeleteObject { target: ParamRef },
    AddLink { link_type: String, a: ParamRef, b: ParamRef },
    RemoveLink { link_type: String, a: ParamRef, b: ParamRef },
}

pub enum SideEffect {
    Notification { to: RecipientSpec, template: I18nText },
    Webhook { url: String, payload: FunctionRef },
    CallFunction { function: FunctionRef },
    StartBusinessProcess { flow_def_key: String, biz_link: BizLinkSpec }, // → cmx-flow
    EmitEvent { topic: String },                                          // → SSE/CDC 外发
}
```

> 动作是本体的**写回契约**。参数 → 校验 → 编辑 → 副作用，全程一个事务边界（副作用中的异步项如流程/webhook 走可靠投递队列，见 §6.3）。

### 5.7 函数类型 FunctionType（计算）

```rust
pub struct FunctionDef {
    pub api_name: String,
    pub runtime: FunctionRuntime,                  // Feel | Rhai | Wasm | NativeRust
    pub kind: FunctionKind,                         // Query | DerivedProperty | Validation | ActionLogic | Aggregation
    pub inputs: Vec<FunctionParam>,                 // 可吃 对象 / 对象集 / 标量
    pub output: FunctionReturn,
    pub body: FunctionBody,                          // 源码或引用
}
```

函数**原生吃对象与对象集**——这是它区别于"普通存储过程"的关键：`延误风险(航班对象) -> f64`、`Top客户(客户对象集) -> 客户对象集`。运行时复用 `cmx-rulesengine` 已有的 FEEL 表达式引擎与 Rhai 脚本载体（见 §6.4）。

### 5.8 元模型总览（一图对齐 Palantir 与 cmx）

| Palantir 原语 | 本方案类型 | 存储 | 复用/协作 cmx |
| --- | --- | --- | --- |
| Object Type | `ObjectTypeDef` | `om_object_type` + 物化表 `oo_<t>` | 可由 cmx-model **DOC**（主从实体）生成 |
| Property Type | `PropertyTypeDef` | `om_property` | semanticType/i18n ← cmx-meta-data |
| Link Type | `LinkTypeDef` | `om_link_type` + `ol_<l>` | 层级 ← cmx-hierarchy |
| Interface / Shared Prop | `InterfaceDef` / `SharedPropertyTypeDef` | `om_interface` / `om_shared_property` | — |
| Action Type | `ActionTypeDef` | `om_action_type` | 副作用 → cmx-flow；校验 → cmx-rulesengine |
| Function | `FunctionDef` | `om_function` | 运行时 → cmx-rulesengine（FEEL/Rhai） |
| Object Set | `ObjectSet`（代数） | `os_object_set` | 过滤编译 ← cmx-dataauth 约束 AST |
| Object Storage V2 | 对象存储引擎 | `oo_*` / `oe_*` | ZMC 零拷贝 + tokio-postgres |
| Object Data Funnel | 数据集成引擎 | 连接器 + 索引器 | — |
| Dynamic Security | PDP/PEP | 残差约束 | **直接复用 cmx-dataauth-core** |
| OSDK | 代码生成 SDK | — | — |

---

## 六、五大核心组件

> 五大组件 = ①建模引擎（Language）＋ ②对象存储索引、③动作引擎、④函数计算、⑤数据集成（Engine 的五根支柱，读取的对象集代数与安全作为横切贯穿其中）。逐一给出：职责 → Rust 设计 → 关键机制/难点 → 与 Palantir 对应 → cmx 复用。

### 6.1 组件一 · 本体建模引擎（语义核心）

**职责**：本体定义的权威源。对象/属性/关系/接口/动作/函数类型的 CRUD、校验、版本、发布、演进。是"Language 层"的唯一入口。

**Rust 设计**（crate：`cmx-onto-core` 定义类型；`cmx-onto-model` 定义领域服务 trait；`cmx-onto-store-pg` 落 PG）：

```rust
pub trait OntologyRepository {
    fn upsert_object_type(&self, t: ObjectTypeDef) -> Result<OntologyRid>;
    fn get_object_type(&self, api_name: &str) -> Result<Option<ObjectTypeDef>>;
    fn list_types(&self, filter: TypeFilter) -> Result<OntologyManifest>;
    fn upsert_link_type(&self, l: LinkTypeDef) -> Result<OntologyRid>;
    fn upsert_action_type(&self, a: ActionTypeDef) -> Result<OntologyRid>;
    fn upsert_function(&self, f: FunctionDef) -> Result<OntologyRid>;
    // —— 发布与版本 ——
    fn publish(&self, changeset: OntologyChangeset) -> Result<OntologyVersion>;
    fn diff(&self, from: OntologyVersion, to: OntologyVersion) -> Result<OntologyDiff>;
}
```

**关键机制**：

1. **定义校验**：api_name 唯一性/命名规范、主键存在、关系两端类型存在、动作编辑引用的属性存在、函数签名合法。校验失败返回**结构化 violations**（复用你 DCT/DOC 落库前列级校验 + CmxErrCode 的成熟范式）。
2. **发布即快照**：类型定义采"草稿 → 发布"两态，发布生成不可变版本（对齐 flow 定义持久化/发布闭环）。运行时永远读"当前激活版本"。
3. **演进 = 类型级迁移**：给对象类型加字段（补列 + 默认值）、改关系基数、废弃属性——生成**迁移计划**，对物化表做 `ALTER` + 对存量对象回填。借鉴 **flow A9 实例迁移**：先 `validate` 出违规码，再执行，可回滚。
4. **从 cmx 反向导入**：一键把 cmx-model 的 **DOC**（主从实体图）导入为对象类型 + 组合关系，**DCT**（字典）导入为参照对象类型（枚举）。本体成为既有元数据的"语义投影"，不推倒重来。

**与 Palantir 对应**：Ontology Manager 的建模能力 + 类型系统。
**cmx 复用**：i18n/semanticType ← cmx-meta-data；校验/错误码范式 ← DCT/DOC；发布/版本范式 ← cmx-flow-def。

### 6.2 组件二 · 对象存储与索引引擎（Object Store & Index）

**职责**：物化对象实例、承载关系边、服务所有读取（搜索/过滤/聚合/Search-Around）、维护索引。对齐 **Object Storage V2 + Object Set Service**。

**存储策略抉择**——两条路线权衡：

| 方案 | 描述 | 优 | 劣 | 取舍 |
| --- | --- | --- | --- | --- |
| A. **Per-Type 物理表**（推荐） | 每个对象类型据定义生成一张强类型表 `oo_<type>`，属性即列 | 强类型、原生索引、SQL 下推、查询快 | 类型演进要 DDL；表数量多 | ✅ 首选，配 §6.1 迁移引擎 |
| B. 通用 JSONB/EAV | 单表 `oo_object(type, pk, props jsonb)` | 零 DDL、演进无痛 | 索引弱、聚合慢、类型靠运行时 | 仅用于 Experimental 期或超稀疏类型 |

**采 A 为主、B 为过渡**：类型 `status=Experimental` 时落 B 快速试错，`Active` 后由迁移引擎"固化"为 A（JSONB → 物理列）。这与 OSv2"Active 才可被高效查询"的语义一致。

**核心：对象集代数（Object Set）—— 读取的统一抽象**

```rust
pub enum ObjectSet {
    Base { object_type: String },                              // 全量
    Filter { source: Box<ObjectSet>, predicate: Predicate },   // 过滤（谓词树）
    SearchAround { source: Box<ObjectSet>, link: String },     // ★关系遍历（本体灵魂）
    Union(Box<ObjectSet>, Box<ObjectSet>),
    Intersect(Box<ObjectSet>, Box<ObjectSet>),
    Subtract(Box<ObjectSet>, Box<ObjectSet>),
    Static { object_type: String, primary_keys: Vec<PkValue> },// 静态集（存主键列表）
    Reference { rid: OntologyRid },                            // 已保存的对象集
}

pub trait ObjectSetCompiler {
    /// 把对象集代数 + 安全约束，编译为**一条** SQL（含 JOIN/CTE），避免 N+1
    fn compile(&self, set: &ObjectSet, security: &ConstraintAst) -> CompiledQuery;
}
```

**关键机制**：

1. **Search-Around 不 N+1**：`客户 →(下单)→ 订单 →(含)→ 商品` 三跳，编译成一条带 `JOIN ol_*` 的 SQL（或递归 CTE for 层级），一次往返。这是本体相对"逐对象 REST 拉取"的根本性能优势。
2. **安全下推**：对象集编译时，把 dataauth 返回的**残差约束 AST**（见 §7.1）作为额外 `WHERE` 合并进同一条 SQL——行级权限与查询同库执行，零绕过。
3. **索引**：`is_indexed` 属性建 PG 索引；全文检索用 `pg_trgm` + GIN（首版）；`GeoShape` / `Vector` 预留 PostGIS / pgvector 接口，实现后置。是否引入外部引擎（Tantivy/ES）作为 `SearchBackend` trait 的另一实现，见 §14 边界。
4. **对象集持久化**：静态集存主键快照（不随数据变），动态集存代数定义（每次求值）——对齐 Palantir 静态/动态、临时/永久四象限。
5. **零拷贝读**：批量对象加载复用你的 **ZMC / cmx-rowsource**（driver 无关零拷贝 RowSource），大结果集不额外堆分配。

**与 Palantir 对应**：Object Storage V2（物化 + 索引 + Search-Around）+ Object Set Service（读取服务）。
**cmx 复用**：约束 AST ← cmx-dataauth；零拷贝 ← ZMC/cmx-rowsource；层级遍历 ← cmx-hierarchy。

### 6.3 组件三 · 动作引擎（Action Engine）

**职责**：本体的**唯一用户写入口**。执行动作 = 参数校验 → 权限校验 → 生成编辑 → 事务写回对象库 → 触发副作用 → 审计。对齐 **Action Types + 写回**。

**执行管线**：

```
apply(action, params)
  │
  ├─ 1. 参数解析与类型校验（对齐 ActionType.parameters）
  ├─ 2. 权限校验（PEP：本用户能否对这些对象执行此动作？→ dataauth）
  ├─ 3. 提交校验 validations（FEEL/规则引擎；失败→结构化 violations，整体拒绝）
  ├─ 4. 生成 EditBatch（Create/Modify/Delete Object，Add/Remove Link）
  ├─ 5. 【事务】写 oo_*/ol_* + 追加 oe_*（编辑日志，可回放/审计）+ 乐观锁校验
  ├─ 6. 提交后副作用（可靠投递）：
  │       通知 · webhook · CallFunction · StartBusinessProcess(cmx-flow) · EmitEvent(CDC)
  └─ 7. 返回 ActionResult { edited_objects, version, side_effect_receipts }
```

```rust
pub trait ActionExecutor {
    fn apply(&self, ctx: &AuthCtx, action: &str, params: ActionParams)
        -> Result<ActionResult, ActionError>;   // 校验失败 => ActionError::Validation(violations)
    fn dry_run(&self, ctx: &AuthCtx, action: &str, params: ActionParams)
        -> Result<EditPreview>;                  // 试算：只出将要发生的编辑，不落库
}
```

**关键机制/难点**：

1. **原子性**：步骤 5 的所有编辑在**一个 PG 事务**内。副作用（6）中的同步项（通知落库）进事务；异步项（流程/webhook）走"**事务性发件箱（Outbox）**"——先在事务内写 `oe_side_effect_job`，事务提交后由投递器消费，保证"编辑成功 ⇔ 副作用最终触发"，且失败可重试（复用 flow P1/P2 的 AsyncJob + 死信队列范式：`SKIP LOCKED` 抢占 + 重试耗尽转死信）。
2. **校验分层**：结构校验（引擎内）+ 业务校验（**下沉 cmx-rulesengine**，FEEL 表达 gap/overlap 皆可），二者都产出统一 violations，前端弹专业对话框（复用 DCT/DOC 错误展示层）。
3. **乐观锁**：对象带 `updated_at`/`__version`，动作携带读时版本，冲突走 `code=0 + data.conflict`（复用 flow 设计器协同 M1 的乐观锁范式）。
4. **函数背书动作**：复杂逻辑（跨多对象、条件分支）走 `function_backing`，动作退化为"调用函数 → 函数返回一批编辑 → 引擎落库"，逻辑演进不改引擎。
5. **写回 vs Funnel 的合并**：用户编辑（oe_*）与数据源灌入（Funnel）对同一对象可能并存——采"**编辑覆盖源**"策略：读取时 `源值 LEFT JOIN 编辑 → 编辑优先`（对齐 OSv2 "编辑经动作施加并索引"，不再靠独立 writeback 数据集）。

**与 Palantir 对应**：Action Type 的编辑 + 校验 + 副作用；写回。
**cmx 复用**：校验 → cmx-rulesengine；业务流程副作用 → cmx-flow（`StartBusinessProcess`，且 flow 已有 `businessRuleTask`/`biz_link` 单据↔实例机制现成）；异步可靠投递 → flow P1/P2 AsyncJob/死信；错误展示 → DCT/DOC presenter。

### 6.4 组件四 · 函数与计算引擎（Function & Compute）

**职责**：承载本体上的一切计算——**派生属性**（对象的计算字段）、**查询函数**（对象集 → 对象集/标量）、**校验函数**（动作用）、**聚合**（跨对象汇总）。对齐 **Functions on Objects**。

**运行时分层**（一个接缝，多种载体——直接搬 cmx-rulesengine 脚本能力方案的成熟结论）：

```rust
pub enum FunctionRuntime {
    Feel,        // 表达式：判定/派生/校验首选（可做 gap/overlap 静态分析）——复用 cmx-rule-feel
    Rhai,        // 脚本：命令式、循环、多分支——复用 rulesengine SC0-SC4 的 Rhai 载体
    Wasm,        // 沙箱：重逻辑/二开，SSRF 白名单/配额——复用 cmx-wasm-http-provider 护栏
    NativeRust,  // 平台内置函数（聚合原语、地理/向量算子）
}

pub trait FunctionEngine {
    fn eval(&self, f: &FunctionDef, args: FunctionArgs, ctx: &EvalCtx) -> Result<FunctionValue>;
    /// 派生属性：查询对象时按需计算（可缓存/可物化）
    fn derive(&self, obj: &ObjectRef, prop: &str) -> Result<PropertyValue>;
}
```

**关键机制**：

1. **函数吃对象/对象集**：`EvalCtx` 提供 `load_object(rid)`、`search_around(set, link)` 回调，函数体内可读属性、遍历关系——这是"本体函数"区别于普通 UDF 的本质。为防 N+1，编译期尽量把函数内的集合遍历**下推**为对象集代数（§6.2）。
2. **派生属性两态**：轻量（表达式）→ 查询时实时算；重量（跨对象聚合）→ 物化 + 增量刷新（对象变更触发失效，复用 flow 派生变量历史/TTL sweep 范式）。
3. **聚合 = 补 cmx-agg 空白**：你 memory 里明确记着"缺后端层间汇总 cmx-agg"。本体的 `Aggregation` 函数正好是它的落点——`SUM/COUNT/AVG over 对象集 group by 属性`，编译为 PG 聚合 SQL，服务报表/指标。
4. **判定永远走 FEEL**：凡涉及"能否/是否"的判定（校验、路由、权限），一律 FEEL，保住可做 gap/overlap 静态分析的红线（这是 rulesengine 的核心资产，不可让 Rhai/Wasm 蚕食）。

**与 Palantir 对应**：Functions（Query / Derived Property / Action logic）。
**cmx 复用**：几乎全量复用 cmx-rulesengine（FEEL 引擎 cmx-rule-feel、Rhai 脚本、失败归因 trace）与 cmx-wasm 护栏；聚合填补 cmx-agg。

### 6.5 组件五 · 数据集成与管道（Object Data Funnel）

**职责**：把外部数据源"灌"成对象，并**持续保鲜**。对齐 **Object Data Funnel**——读数据源 + 用户编辑，索引进对象库，源更新即同步。

**架构**：

```
数据源(Source)          映射(Mapping)              索引(Indexer)          对象库
┌──────────┐  抽取   ┌──────────────┐  变换   ┌──────────────┐  upsert ┌────────┐
│ PG 表/视图│──────▶│ 源列 → 属性    │──────▶│ 校验+主键裁定  │───────▶│ oo_<t>  │
│ 数据集    │       │ 关系 → 外键/中表│        │ + 编辑合并     │        │ ol_<l>  │
│ CDC 流    │       │ FEEL 派生      │        │ + 增量 diff    │        │ 索引     │
│ HTTP/文件 │       └──────────────┘        └──────────────┘        └────────┘
└──────────┘                                          ▲
                                                      │ oe_*（用户编辑，Action 产）
```

```rust
pub trait SourceConnector {                    // 数据源连接器（可插拔）
    fn schema(&self) -> SourceSchema;
    fn read_batch(&self, cursor: Option<Cursor>) -> Result<RecordBatch>;   // 批量
    fn subscribe_cdc(&self) -> Option<CdcStream>;                          // 增量（可选）
}
pub struct ObjectMapping {                      // 源 → 对象的映射规格
    pub object_type: String,
    pub key_columns: Vec<String>,               // 主键裁定
    pub property_map: Vec<(String /*src*/, String /*prop*/)>,
    pub link_map: Vec<LinkMapping>,             // 外键/中间表 → 关系边
    pub derivations: Vec<(String, FunctionRef)>,// 灌入时 FEEL 派生
}
pub trait Funnel {
    fn run_sync(&self, mapping: &ObjectMapping, mode: SyncMode) -> Result<SyncReport>; // Full | Incremental
    fn pipeline_status(&self, object_type: &str) -> PipelineGraph;         // 管道图（前端监控）
}
```

**关键机制**：

1. **批量 + 增量双模**：首灌 `Full`（全量 upsert）；之后 `Incremental`（按游标/CDC diff）。大批量走 `COPY`/分批事务；复用 ZMC 零拷贝减少中间分配。
2. **编辑与源合并**：索引时，用户编辑（oe_*）优先于源值（同 §6.3.5）。源删了但有编辑的对象，按策略保留/软删。
3. **更严校验**（对齐 OSv2 "比 OSv1 更严"）：主键非空唯一、类型可转、必填齐全——违规进"隔离区"并在管道图标红，不污染主对象库。
4. **管道图可视化**：`pipeline_status` 输出各阶段（抽取/映射/索引）状态，前端管道监控台渲染（对齐 Ontology Manager 的 pipeline graph，绿勾=就绪可查）。
5. **长任务治理**：全量灌入是长任务——**复用你的"异步任务中心 M1"**（SSE 进度 + 暂停/停/重启 + PG 恢复 + 分布式抢占 HA），Funnel sync 作为其一种 job 类型接入。

**与 Palantir 对应**：Object Data Funnel（数据源 + 编辑 → 索引 → 保鲜）。
**cmx 复用**：长任务 → 异步任务中心；零拷贝 → ZMC；派生 → FEEL。

---

## 七、横切关注点

### 7.1 动态安全（复用 cmx-dataauth）

Palantir 本体的"动态安全"是动能层的一等公民——**读写皆受粒度化、可随上下文变化的权限治理**。本方案**不重造**，直接编织进已设计的 **cmx-dataauth**（PDP/PEP 分离 + 约束 AST 多后端编译）：

| 粒度 | 机制 | 落点 |
| --- | --- | --- |
| **对象类型级** | 能否 See/Query 某类型 | PDP 决策，命中即拒 |
| **行级（对象级）** | "只能看本部门的客户" | dataauth 返回**残差约束 AST** → §6.2 对象集编译器合并进 `WHERE`，同库执行零绕过 |
| **列级（属性级）** | `PropertyMarking` 敏感字段脱敏/隐藏 | dataauth 列脱敏（Column Masking） |
| **关系级（ReBAC）** | "我参与的项目的所有任务" | dataauth ReBAC + Search-Around 结合 |
| **强制标记（Marking）** | Mandatory 控制（密级） | `Marking` 属性 + PDP 前置门 |

> 妙处：本体的**对象集代数**天然是 dataauth **约束 AST**的消费者——权限过滤 = 往对象集上再叠一个 `Filter(残差约束)`，与业务过滤走同一条编译后的 SQL。决策（谁能看什么）与执行（在对象集里过滤）彻底解耦，DB 无关、可单测。动作写入侧则由 PEP 在 §6.3 步骤 2 前置拦截。

### 7.2 多租户

复用 flow S2 / dataauth 已验证的 **db-per-tenant** 范式：

- 租户经 JWT → `tenant` task_local；本体元数据库/对象数据库均按 `onto_<tenant>` 懒注册连接池（`OnceCell`-per-tenant）。
- 每租户独立本体定义与对象数据，物理隔离。单租户 `mode=off` 零回归（对齐 rules/flow）。

### 7.3 API 与 SDK（OSDK 对等）

**REST（v1 前缀，对齐 headless 契约）**：

```
# 元模型
GET    /v1/onto/{tenant}/object-types
POST   /v1/onto/{tenant}/object-types
GET    /v1/onto/{tenant}/link-types  ·  /action-types  ·  /functions  ·  /interfaces
# 对象读取（Object Set Service 对等）
POST   /v1/onto/{tenant}/object-sets/load        # body: 对象集代数 → 分页对象
POST   /v1/onto/{tenant}/object-sets/aggregate   # 聚合
GET    /v1/onto/{tenant}/objects/{type}/{pk}
GET    /v1/onto/{tenant}/objects/{type}/{pk}/links/{link}   # Search-Around
# 动作写回
POST   /v1/onto/{tenant}/actions/{action}/apply
POST   /v1/onto/{tenant}/actions/{action}/dry-run
# 函数
POST   /v1/onto/{tenant}/functions/{fn}/execute
# 实时（对齐 flow SSE 按租户隔离 + 一次性票据）
GET    /v1/onto/{tenant}/stream?ticket=...        # 对象/编辑变更 CDC 推流
# 契约
GET    /v1/onto/{tenant}/openapi.json  ·  /swagger
```

**OSDK 对等（代码生成）**：读本体定义 → 生成**强类型客户端**（Rust crate + TypeScript 包）。`ont.objects.Customer.where(...).search_around(orders)` 直接映射对象集代数，前端/二开零手写 REST。生成器复用你已有的 codegen 经验（cmx-codegen 编码引擎）。

---

## 八、数据持久化设计

**元数据库（`om_*`，本体定义）**：

```sql
om_object_type(rid, tenant, api_name UNIQUE, display_name jsonb, primary_key,
               title_property, datasource jsonb, status, cmx_origin jsonb,
               version, created_at, updated_at)
om_property(rid, object_type_rid, api_name, base_type, required, semantic_type,
            constraints jsonb, marking, is_indexed, ord)
om_link_type(rid, tenant, api_name, cardinality, side_a jsonb, side_b jsonb, backing jsonb)
om_interface(rid, api_name, properties jsonb, extends jsonb)
om_shared_property(rid, api_name, base_type, semantic_type)
om_action_type(rid, api_name, parameters jsonb, logic jsonb, validations jsonb,
               side_effects jsonb, function_backing)
om_function(rid, api_name, runtime, kind, inputs jsonb, output jsonb, body text)
om_version(version, tenant, changeset jsonb, published_at, published_by)  -- 发布快照
```

**对象数据库（`oo_*`/`ol_*`/`oe_*`/`os_*`，对象运行时）**：

```sql
-- Per-Type 物理表（由 ObjectTypeDef 生成 DDL；此为 Customer 示例）
oo_customer(pk BIGINT PRIMARY KEY, name TEXT, region TEXT, ...,
            __version BIGINT, __marking TEXT[], __src_cursor TEXT,
            created_at, updated_at)                       -- 属性即列，索引按 is_indexed 建
-- 关系边（N:M 中间表；1:N 走对象表外键列）
ol_customer_places_order(a_pk BIGINT, b_pk BIGINT, props jsonb, PRIMARY KEY(a_pk,b_pk))
-- 编辑日志（Action 产；写回审计 + 回放 + 与源合并）
oe_edit(id BIGSERIAL, object_type, pk, op, before jsonb, after jsonb,
        action_rid, actor, ctx jsonb, created_at)
-- 副作用发件箱（事务性 Outbox，可靠投递）
oe_side_effect_job(id, edit_id, kind, payload jsonb, status, attempts, next_at)
-- 对象集（静态存主键 / 动态存定义）
os_object_set(rid, tenant, name, kind /*static|dynamic*/, definition jsonb,
              primary_keys BIGINT[], owner, shared_with jsonb)
-- 隔离区（Funnel 校验不通过）
oo_quarantine(object_type, raw jsonb, violations jsonb, source, created_at)
```

**要点**：

- **JSONB 可空列一律 `NullTyped`**：你 memory 明确记着"空 `dimensions jsonb` 裸 `Null` 序列化 500"的教训——本方案所有可空 jsonb 走类型化 Null，杜绝复发。
- **tokio-postgres 类型坑**：BIGINT/`i64`、jsonb/`serde_json::Value`、`TIMESTAMPTZ` 映射按你报表两模式加载踩过的类型坑预先约定。
- **bigint 主键后端铸号**：对象 pk 复用你 DCT/DOC 的"后端首存铸号（52 位 JS 安全算法）"，前端临时 id → 落库真 id。

---

## 九、前端交互与展示

遵循你成熟的 **native page 四区 + 门户微前端联邦**（自暴 `/api/native-pages`，门户反代，rev=xxhash64 字节一致）范式；主题走"UI5 在 `:root` 重定义 `--sap*` 穿透 shadow + `--onto-*` 令牌锚 `--sap*`"的双主题做法。四个工作台：

### 9.1 本体建模工作台（Ontology Manager）

四区：左=类型浏览器树（对象/关系/动作/函数分组，带查找/分页/刷新，复用 rulesengine explorer 范式）｜中上=**本体图谱画布**｜中下=类型属性编辑（属性表格 + 校验/语义类型）｜右=情境预览。

- **图谱画布直接复用你已抽出的独立 Web Component `@cmx/decision-graph`**（拖拽节点 + 拉线 + 防环 + SVG DAG）——对象类型=节点、关系类型=连线，天然契合本体图谱。省掉从零手搓画布。
- 动作类型设计器：参数表单 + 编辑规则 + 校验（内嵌 FEEL 编辑，复用 rules 决策表设计器的格内 FEEL + fx + gap/overlap）+ 副作用（选流程定义）。

### 9.2 对象浏览器（Object Explorer）

四区：左=对象集构造器（选类型 → 加过滤 → Search-Around 遍历）｜中=对象列表（**表格视图复用 cmx-spreadsheet**，大数据量虚拟滚动）｜右=对象详情卡（属性 + 关系 + 可执行动作按钮）。

- Search-Around 交互：在对象详情点关系 → 一键跳到"相关对象集"，图谱式钻取。
- 保存对象集：静态/动态，可分享（对齐 Palantir 对象集资源）。

### 9.3 应用搭建台（Workshop 最小版）

以"对象详情页 + 动作表单"为原子，配置化拼装面向业务角色的操作页（如"客户 360"：一个客户对象 + 其订单/工单/发票关系区 + 常用动作）。首版给最小可用（对象视图 + 动作触发），全功能后置。

### 9.4 数据管道监控台（Funnel Ops）

渲染 `pipeline_status` 的管道图（抽取/映射/索引三段状态、绿勾就绪、隔离区计数），接异步任务中心 SSE 显示灌入进度、暂停/重启。

> 所有工作台走门户联邦（`portal.onto.*` 视图 + 反代 `/api/onto/*` + 白名单），菜单部署到 `cmx_menu`（注意你踩过的"菜单 id 撞 PK / whitelist 漏项 → 空数据"两坑，预先规避）。

---

## 十、Rust 工作区与 crate 结构（一芯多壳）

新建独立工作区 `cmx-ontology/`（跨 ws path 复用 infra，对齐 flowengine/rulesengine），`:8097`（承 meta-data `:8096` 之后；若 cmx-data-auth 已占 `:8097` 则顺延 `:8098`）。

```
cmx-ontology/
├── .cargo/                      # 定义 nora 等（新 ws 必须，你踩过的坑）
├── Cargo.toml                   # workspace
├── onto-server.toml(.example)   # [server]:8097 / [[databases]] / [auth] / [assets]
├── crates/
│   ├── cmx-onto-core/           # 【芯·类型】元模型类型 + 核心 trait（框架无关，零 IO）
│   ├── cmx-onto-model/          # 领域服务 trait（Repository / Executor / Compiler / Funnel）
│   ├── cmx-onto-store-pg/       # PG 实现：om_*/oo_*/ol_*/oe_*；DDL 生成器；tokio-postgres
│   ├── cmx-onto-index/          # 对象集编译器 + 搜索索引（SearchBackend trait）
│   ├── cmx-onto-action/         # 动作引擎（管线 + Outbox 投递）
│   ├── cmx-onto-function/       # 函数引擎（接 cmx-rule-feel / Rhai / Wasm / 聚合原语）
│   ├── cmx-onto-funnel/         # 数据集成（SourceConnector + Mapping + Indexer）
│   ├── cmx-onto-security/       # 安全适配（薄封装，委托 cmx-dataauth-core）
│   ├── cmx-onto-app/            # 【芯·应用】中立应用核：单例装配 + handlers + onto_routes::<S>
│   ├── cmx-onto-api/            # 【壳·内嵌】门户内嵌壳（同核）
│   ├── cmx-onto-server/         # 【壳·独立】独立 bin :8097（chassis run()）
│   ├── cmx-onto-sdk/            # OSDK 对等：客户端 + 代码生成器
│   └── cmx-onto-tests/          # 集成/E2E（真机 boot + curl，对齐 flow-tests）
└── web/                         # native/html 页面资产（建模台/浏览器/搭建台/管道台）
```

- **一芯多壳**：`cmx-onto-app` 是中立核（`onto_routes::<S: OntoStore>` 泛型 store，去 `CmxAppState`），`api`（内嵌）与 `server`（独立）两薄壳同核（对齐 flow-app / rule-app）。
- **服务骨架**：`cmx-onto-server` 声明式装配 `ServiceSpec`，跑 `cmx-web-chassis::run()`（复用通用服务骨架，infra 零 cmx-api）。
- **门户接入**：`cmx-onto-api` 经 `center_client` 接回门户；内嵌↔独立看 `urls.onto`（对齐 flow S6）。

---

## 十一、技术选型

| 关注 | 选型 | 理由 |
| --- | --- | --- |
| 语言/运行时 | Rust + Tokio | 与全生态一致 |
| Web 框架 | 复用 `cmx-web-chassis`（Axum 底座） | 声明式装配、统一形态 |
| DB 驱动 | `tokio-postgres`（+ ZMC 零拷贝 RowSource） | 与 flow/rules/report 一致；大结果集零拷贝 |
| 搜索 | PG `pg_trgm`+GIN（首版）｜`SearchBackend` trait 预留 Tantivy/ES | 先零外部依赖，可插拔升级 |
| 地理/向量 | PostGIS / pgvector（后置） | 属性类型与索引接口先占位 |
| 表达式/脚本 | `cmx-rule-feel`（FEEL）+ Rhai + Wasm | 判定走 FEEL 保 gap/overlap；脚本/沙箱按需 |
| 序列化 | serde / serde_json（jsonb 一律 NullTyped） | 规避裸 Null 序列化坑 |
| 前端图谱 | `@cmx/decision-graph` Web Component | 已有、契合本体 DAG |
| 前端表格 | `cmx-spreadsheet` | 大对象集虚拟滚动 |
| 多租户/认证 | JWT + task_local + db-per-tenant | 对齐 flow S2 |
| 长任务 | 异步任务中心（SSE + HA 抢占） | Funnel 全量灌入 |
| 可靠投递 | 事务性 Outbox + AsyncJob/死信 | 对齐 flow P1/P2 |

---

## 十二、与 cmx-\* 生态的集成地图

本体是**语义总纲**，既有引擎是它的动能后端。集成关系一览：

```
                       ┌─────────────────────────────┐
                       │       cmx-ontology           │
                       │   （语义总纲 / 本体平台）      │
                       └──────────────┬──────────────┘
        对象类型 ← 生成                │ 副作用：StartBusinessProcess
   ┌────────────────┐                 ▼
   │ cmx-model      │        ┌─────────────────┐   校验/函数    ┌──────────────────┐
   │ DOC 主从实体   │───────▶│  动作引擎③       │──────────────▶│ cmx-rulesengine   │
   │ DCT 字典→枚举  │  导入  │  函数引擎④       │  FEEL/Rhai    │ (FEEL/Rhai/trace) │
   └────────────────┘        └───────┬─────────┘               └──────────────────┘
   ┌────────────────┐  语义/i18n      │ 行/列/关系级安全
   │ cmx-meta-data  │───────▶ 属性    ▼
   │ semanticType   │        ┌─────────────────┐               ┌──────────────────┐
   └────────────────┘        │  对象集编译②     │──────────────▶│ cmx-data-auth     │
   ┌────────────────┐  层级   │  (残差约束合并)   │  约束 AST     │ (PDP/PEP)         │
   │ cmx-hierarchy  │───────▶ 关系遍历           └─────────────────┘               └──────────────────┘
   │ 主从/拓扑      │                 │ 聚合（补空白）
   └────────────────┘                 ▼
                              ┌─────────────────┐
                              │  cmx-agg (新落点) │  ← 本体 Aggregation 函数
                              └─────────────────┘
   共用基座：cmx-web-chassis(服务骨架) · cmx-jsonstore(定义持久化) · cmx-service-base(Nacos/RPC/门户联邦)
```

| cmx 资产 | 在本体中的角色 | 方向 |
| --- | --- | --- |
| **cmx-model（DOC/DCT/FLC）** | DOC→对象类型+组合关系；DCT→参照对象类型 | 导入（本体是其语义投影） |
| **cmx-meta-data** | 属性的 semanticType / i18n 双语 | 复用 |
| **cmx-hierarchy** | 层级关系类型（组织/BOM/科目）的遍历 | 复用 |
| **cmx-rulesengine** | 动作校验 + 本体函数运行时（FEEL/Rhai/trace） | 复用 |
| **cmx-flow** | 动作副作用触发业务流程（biz_link 单据↔实例现成） | 委托 |
| **cmx-data-auth** | 动态安全（对象/行/列/ReBAC，约束 AST） | 委托 |
| **cmx-agg（空白）** | 本体聚合函数的落地点 | 新建/填补 |
| **cmx-web-chassis / jsonstore / service-base** | 服务骨架 / 定义存储 / 门户联邦 | 复用 |
| **异步任务中心 / ZMC / cmx-codegen** | 灌入长任务 / 零拷贝读 / OSDK 生成 | 复用 |

> 一句话：本体平台把你散落各微服务的能力，**用统一的对象/关系/动作/函数语义收口**——DOC 有了图谱语义、rules 有了对象上下文、flow 有了触发契约、dataauth 有了对象集执行点、agg 有了归宿。

---

## 十三、落地路线图 O0–O8

| 里程碑 | 交付 | 验收 |
| --- | --- | --- |
| **O0 骨架** ✅ | 独立 ws `cmx-ontology`，一芯多壳空跑，`:8097` boot，chassis/多租户接好 | `curl /health` 绿；门户反代壳挂通 |
| **O1 建模引擎①** ✅ | 元模型类型 + 对象/属性/关系类型 CRUD + `om_*` 持久化 + 发布/版本 + 建模台雏形 | 建一个"客户/订单"本体并发布；结构化校验生效 |
| **O2 对象存储②** ✅ | Per-Type 物化表 `oo_<type>`(props JSONB) + 统一边表 `ol_edge` + upsert(事务) + **对象集代数编译器**(Base/Filter/SearchAround双向/∪∩−/Static) + 聚合(Count/GroupCount/GroupSum) | 三跳 Search-Around 一条 SQL 出结果；Rust 20 + O1 41 + O2 25 全绿 |
| **O3 数据集成⑤** | SourceConnector(PG 表/数据集) + Mapping + 全量/增量灌入 + 管道图 + 接异步任务中心 | 从既有 fico 表灌 10w+ 对象；管道台绿勾 |
| **O4 动作引擎③** | 动作类型 + 编辑管线 + 校验(接 rules) + 事务写回 + Outbox 副作用(接 flow) + oe_* 审计 | 执行"改签"动作：校验→落库→触发流程→审计全绿；dry-run 试算 |
| **O5 函数计算④** | 函数引擎(FEEL/Rhai) + 派生属性 + 查询函数 + **聚合(cmx-agg)** | 派生"客户总额"；聚合"按区域 GMV"；函数吃对象集 |
| **O6 动态安全** | 接 cmx-dataauth：对象/行/列/ReBAC + Marking；对象集编译合并残差约束 | 换租户/角色，同一查询返回不同行/脱敏列 |
| **O7 API/SDK** | REST v1 全量 + OpenAPI/Swagger + SSE live + **OSDK 代码生成(Rust/TS)** | 生成的客户端跑通 CRUD/动作/Search-Around |
| **O8 前端 + 案例** | 四工作台完善 + 门户联邦字节一致 + 端到端案例(客户 360 / 供应链) | CDP 全绿；一个业务角色可视化操作闭环 |

> 每个里程碑遵循你的既有纪律：真机 boot + curl E2E + Rust 单测 + CDP 前端测试 + 零回归门（对齐 flow 159/159、rules 223 断言范式）。

---

## 十四、风险、权衡与边界

| # | 风险/权衡 | 取舍与缓解 |
| --- | --- | --- |
| R1 | **Per-Type 表 vs 通用 JSONB**：类型演进要 DDL | Experimental 期用 JSONB，Active 由迁移引擎固化为物理表；DDL 迁移借鉴 flow A9（validate→执行→回滚） |
| R2 | **大规模 Search-Around / 聚合**（Palantir 用 Spark 下推 10w+） | 下推 PG（CTE/物化视图/并行）；超阈值（如单查 >50w 对象）给**明确边界与降级**（分页/异步物化对象集），不硬扛。评估 Polars 作为 NativeRust 聚合后端 |
| R3 | **搜索能力**：PG 全文/地理/向量弱于专用引擎 | `SearchBackend` trait 抽象，首版 PG，预留 Tantivy/ES/pgvector 平滑替换，不锁死 |
| R4 | **写回与源的合并一致性** | "编辑覆盖源"单一策略 + oe_* 审计可回放；源删除有编辑的对象按显式策略处理，避免隐式丢数据 |
| R5 | **本体演进破坏兼容** | api_name 稳定锚 + 发布快照 + 类型迁移；改基数/删属性走"废弃→迁移→移除"三步，不一步到位 |
| R6 | **副作用可靠性**（编辑成了但流程没触发） | 事务性 Outbox（编辑与 job 同事务）+ 死信重试，保证最终一致；对齐 flow P1/P2 |
| R7 | **与 cmx-model 职责重叠**（DOC 也建实体） | 明确分工：cmx-model 管**定义与录入表单**；本体管**跨实体的图谱语义、关系遍历、动作治理、跨源物化**。本体从 DOC 导入而非取代 |
| R8 | **范围蔓延**（Workshop 全功能是无底洞） | 前端首版聚焦建模台+浏览器+动作表单；应用搭建最小可用，全功能后置（§3.2 非目标） |
| R9 | 不做 OWL/RDF 推理 | 对齐 Palantir 专有表示；追求操作型可用，非学术可推理（明确非目标） |

---

## 十五、附录：术语表与参考

### 15.1 术语表

| 术语 | 释义 |
| --- | --- |
| **本体 Ontology** | 企业数字孪生的操作型语义层，含语义（对象/关系）与动能（动作/函数/安全）元素 |
| **对象类型 / 对象** | 实体的 schema / 其实例（`机场` / `JFK`） |
| **关系类型 Link Type** | 对象类型间的关系；Search-Around 的路径 |
| **接口 Interface** | 对象类型的形状契约，提供多态 |
| **动作类型 Action Type** | 一组受治理的编辑 + 校验 + 副作用 |
| **函数 Function** | 原生吃对象/对象集的计算逻辑 |
| **对象集 Object Set** | 对象的可组合、可保存集合；读取的基本单位 |
| **Search-Around** | 沿关系类型从一个对象集遍历到相关对象集 |
| **Object Storage V2 (OSv2)** | Palantir 新一代对象规范存储（取代 Phonograph/OSv1） |
| **Object Data Funnel** | 编排数据源 + 用户编辑 → 索引进对象库并保鲜 |
| **Object Set Service (OSS)** | 服务本体所有读取的服务 |
| **OSDK** | 从本体生成的强类型 SDK |
| **写回 Writeback** | 用户通过动作对对象施加编辑并被索引 |
| **动态安全 / Marking** | 随上下文变化的粒度化权限 / 强制安全标记 |
| **一芯多壳** | 中立核 app + 内嵌壳 api + 独立壳 server 的 cmx 微服务范式 |

### 15.2 参考

- [Ontology 概览 · Palantir](https://www.palantir.com/docs/foundry/ontology/overview)
- [Ontology 核心概念 · Palantir](https://www.palantir.com/docs/foundry/ontology/core-concepts)
- [对象与关系类型 · 类型参考 · Palantir](https://www.palantir.com/docs/foundry/object-link-types/type-reference)
- [动作类型概览 · Palantir](https://www.palantir.com/docs/foundry/action-types/overview)
- [对象后端概览与架构 · Palantir](https://www.palantir.com/docs/foundry/object-backend/overview)
- [OSv1→OSv2 迁移与破坏性变更 · Palantir](https://www.palantir.com/docs/foundry/object-backend/object-storage-v2-breaking-changes)
- [Ontology SDK (Python OSDK) · Palantir](https://www.palantir.com/docs/foundry/ontology-sdk/python-osdk)
- [Palantir Ontology 架构与收益 · PuppyGraph](https://www.puppygraph.com/blog/palantir-ontology)
- [The Palantir Ontology, Explained · bdemerson](https://www.bdemerson.com/article/palantir-ontology-explained)

### 15.3 cmx 生态内部关联（memory 锚点）

统一建模 `[[unified-modeling-rpt-to-doc-dct]]` · 数据权限 `[[data-auth-scheme-pdp-pep-constraint-ast]]` / `[[cmx-dataauth-m1-impl]]` · 层级引擎 `[[cmx-hierarchy-impl]]` · 规则引擎 `[[cmx-rulesengine-r0-impl]]` / `[[cmx-rulesengine-script-capability-plan]]` · 流程引擎 `[[cmx-flowengine-standalone-microservice-design]]` / `[[cmx-flowengine-p1-async-job-executor]]` · 元数据 `[[cmx-meta-data-rebuild-plan]]` / `[[dct-doc-flc-metadata-evolution-proposal]]` · 服务骨架 `[[cmx-web-chassis-shared-server]]` · 决策图组件 `[[cmx-decision-graph-component]]` · 零拷贝 `[[cmx-rowsource-zmc]]`

---

> 下一步（待你确认）：本文为纯设计。若认可整体骨架，建议从 **O0 骨架 + O1 建模引擎①** 起步——先把元模型类型（`cmx-onto-core`）与对象/关系类型 CRUD + 发布跑通，其余组件在稳定的语义地基上逐个叠加。是否需要我：①对某一组件（如②对象集编译器 / ③动作管线）出更细的详设与时序图；②补几张内嵌 SVG 架构图（对齐你 docs 图文并茂风格）；③先落 O0 工作区骨架？
