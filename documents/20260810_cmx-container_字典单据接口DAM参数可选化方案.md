# 字典/单据接口 DAM 参数可选化方案

> 状态：设计已评审（用户确认）· 待实施
> 范围：cmx-container 后端（`/api/dct/*`、`/api/doc/*`），前端零改动、完全兼容
> 日期：2026-08-10

## 一、背景与目标

当前三个典型接口强制要求 `domain/application/module`（DAM）三段坐标：

- `GET /api/dct/data/search?domain=basic&application=dataplatform&module=mdm&dict=supplier`
- `GET /api/dct/meta?...&dict=supplier&with_props=true`
- `GET /api/doc/data/sqlx-zmc-msgpack?domain=fi&application=cmxfico&module=gl&doc=cmxfico&depth=10`

DAM 缺失时 axum 反序列化直接 400（`missing field`）。而实际上：

1. **DAM 只用于定位设计期定义文件**（`data/meta/definitions/<D>/<A>/<M>/*.json`），不参与数据库路由（数据库由独立的 `db_id` 请求头决定，缺失回退 biz 库）；
2. 字典 `dictCode` / 单据 `moduleCode` 在绝大多数场景下全局唯一，调用方却必须事先知道完整坐标——坐标目前靠前端设计期固化注入（`editSettings.coord` / 页面 `loadDef`），运行时 host 并无天然来源。

**目标**：DAM 三段不再强制——常规使用只传 `dict` / `doc`（moduleCode）即可；仅当同一编码在多个 DAM 下冲突时才要求显式传 DAM 消歧。以最小侵入实现，全链路向后兼容。

## 二、现状关键事实（探索结论）

| # | 事实 | 依据 |
|---|---|---|
| 1 | `DctQuery`（`crates/libs/cmx-dct/cmx-dct-model/src/lib.rs:26`）与 `DocDataQuery`（`crates/libs/cmx-doc/cmx-doc-api/src/handlers.rs:39`）的 DAM 三字段为裸 `String` 必填 | 缺失即 axum 400 |
| 2 | DCT 全部操作（meta/search/zmc-msgpack/upsert/delete/save/export/import）都经过咽喉点 `resolve_dict()`（`cmx-dct-store-pg/src/resolve.rs:332`）；DOC 全部端点（5 个 data 组合 + stream + meta）都经过 `resolve_doc_meta()`（`cmx-doc-store-pg/src/resolve.rs:54`） | 改两点即覆盖全链路 |
| 3 | `store::list_definitions(kind, domain, app, module)` 三段均支持 `None` 全扫（`cmx-model-meta/src/definitions/store.rs:512`），是现成的全局扫描基础设施；部署模块 `collect_db_definitions` 已在用 | 可复用 |
| 4 | dictCode/moduleCode **无跨 DAM 唯一约束**（定义是文件系统 JSON，仅单 DAM 内有重复检测 warn），冲突真实可能存在，必须检测 | `resolve.rs` C1/C2 检测仅 DAM 内 |
| 5 | 已有 `Error::Conflict`（HTTP 409，`cmx-api-types/src/error.rs`）可用于冲突响应 | — |
| 6 | 既有脏值惯例：`file`/`doc` 参数的 `""`/`"undefined"`/`"null"` 一律视为缺失（`resolve_doc_file_smart`） | 沿用 |
| 7 | 既有定义派生缓存均无带外失效：`DOC/DICT/BASE_FILE_CACHE` 永不失效；DocMetaView 缓存仅 10 分钟 TTL 且 `invalidate` 无调用方；TableSpec 缓存键含 version 但不含内容指纹 | 手动改文件需重启才生效（现状痛点） |
| 8 | 数据根 `data_root()` 支持 `portal.data_root` 配置 / `CMX_PORTAL_DATA_ROOT` 环境变量（`cmx-portal-base/src/config.rs`） | 集成测试可用临时目录 |

## 三、需求决策记录

| 决策点 | 结论 |
|---|---|
| 生效范围 | **全部 `/dct/*` 与 `/doc/*` 端点**（读写统一；写端点的歧义由 409 兜底，不会写错目标） |
| 冲突响应 | **HTTP 409 + msg 枚举全部候选 DAM 坐标**（`Error::Conflict`） |
| 部分 DAM | **支持**——只传三段中的一部分可缩小反查范围 |
| 前端改动 | **本次仅后端**，前端带全 DAM 的既有调用完全兼容，后续再逐步停传 |
| 手动改文件刷新 | **必须支持**：直接改磁盘定义 JSON 后，不重启、不手动调接口，缓存自动刷新（定义树"代数"机制，见 4.4） |
| 实现路径 | **终版：`Option<String>` + 咽喉点归一化**。演进：初版方案 B（平行输入 DTO `DctQueryIn`/`DocDataQueryIn` + 15 处 handler 签名变更）→ 按"API 兼容即可、后端不留冗余代码、精简"指令改 A（`serde(default)` + 空串=缺失）→ 按"后端要能明确知道参数非必填"定案 A'：DAM 三字段直接改 `Option<String>`（与同结构体 `file`/`doc` 字段既有风格一致），咽喉点归一化产出 owned String 后下游取显式 `&str`；零新增结构体、零冗余分支、零 unwrap |

## 四、方案设计

### 4.1 总体架构与解析流程

```
请求 ?dict=supplier（无 DAM）
   │
   ▼
Query<DctQuery> / Query<DocDataQuery>          ← axum 边界：DAM 三字段改 Option<String>，
   │                                              缺失 → None（不再 400）；与 file/doc 字段既有风格一致
   ▼
咽喉点归一化（resolve_dict / resolve_doc_meta 首步）：
┌─ DAM 三段均 Some(非空) ─────→ 直通（零开销快路径，现有调用 100% 走这里）
├─ DAM 缺失/部分（None）─────→ 全局编码反查（共享层 cmx-model-meta::definitions::resolve）
│      │   （先查编码索引缓存；代数失配则重建，见 4.4）
│      ├─ 恰好 1 个 DAM 命中 → 补全坐标，产出 owned String 三元组，后续逻辑取显式 &str
│      ├─ 0 命中            → business_error（与既有 resolve 失败风格一致）
│      └─ 多 DAM 命中       → Error::Conflict（HTTP 409）枚举候选坐标
   ▼
现有链路：file 解析 / 装载 / 回存（咽喉点内以归一化后的 &str 传参，主体逻辑不改）
```

核心思想：**零新增结构体 + Option 类型自述 + 咽喉点归一化**。DAM 三字段直接改 `Option<String>`：可选性由类型自述（后端明确知道参数非必填），与同结构体 `file`/`doc` 的既有风格一致；坐标补全收敛在两个咽喉点内部，归一化后产出 owned String 三元组，下游 helper 接收显式 `&str` 参数——无冗余逻辑、无 unwrap。

咽喉点内的签名调整（不外溢到 handler 之外）：

- DCT：`cmx-dct-store-pg::resolve::resolve_dict` 首步归一化；其私有 helper `resolve_doc`/`resolve_or_build_spec` 由接收 `&DctQuery` 改为接收显式 `&str` 参数（DAM 三元组 + file/dict 等所需字段）。`hier_service` 内部构造的 `DctQuery` 坐标恒齐全（三段 `Some(..)`），走快路径不受影响。
- DOC：`cmx-doc-store-pg::resolve::resolve_doc_meta`/`resolve_doc_file_smart` 形参 `&str` → `Option<&str>`，归一化内置；底层 `resolve_doc_file`/`resolve_dict_file`（cmx-model-meta）仍收 `&str`（归一化之后才调用），不动。
- 全局反查本体：`cmx-model-meta::definitions::resolve`（DOC/DCT 共享层，避免 `cmx-api ⇄ cmx-doc/cmx-dct` 依赖环——该模块的既有定位）。

### 4.2 API 契约

| 参数形态 | 行为 |
|---|---|
| 三段齐全（现状所有调用） | 完全不变，不触发反查，无额外开销 |
| 三段全缺 + `dict`/`doc` 有值 | 全局按编码反查，唯一命中即用 |
| 部分段（如只传 `domain=basic`） | 已传段作为过滤条件缩小扫描范围，缺的段反查 |
| 只传 `file` 无 DAM（DOC） | 按文件名在定义清单中反查坐标（同名跨 DAM 同样 409） |
| DOC：DAM、`doc`、`file` 全缺 | 400「无法定位单据定义：请至少提供 doc(moduleCode)、file 或完整 DAM」；部分 DAM + 无 doc/file 同样 400（跨模块盲选默认不安全） |
| DCT：`dict` | 仍必填（它是反查键本身） |

**脏值归一**：DAM 三段的 `Some("")` / `Some("undefined")` / `Some("null")` 一律归一为 `None`（沿用 `resolve_doc_file_smart` 惯例；`?domain=` 空值会反序列化为 `Some("")`）。

**匹配语义**：
- DCT：先按 `dictMeta.dictCode` 精确匹配；**仅当全局无任何 dictCode 命中**才回退 `dictMeta.tableName` 匹配（避免"A 域 dictCode = B 域 tableName"造成伪冲突）。DAM 内既有 `dict_matches` 语义不变。
- DOC：按 `moduleMeta.moduleCode` 精确匹配。

**冲突响应**（`Error::Conflict` → HTTP 409，body `{code:409, msg}`），候选按字典序排序（跨副本确定性）：

```
字典 supplier 在多个 DAM 下存在，无法自动定位，请显式传入 domain/application/module 消除歧义：
  - basic/dataplatform/mdm
  - fi/cmxfico/gl
```

**零命中响应**：`Error::business_error`（与既有「未在 X 下找到…」风格一致，前端零改动即可展示 msg）：

```
字典 supplier 未在任何 DAM 下找到；请确认 dictCode 或显式传入 domain/application/module
```

### 4.3 全局编码索引（CODE_INDEX）

反查不走"每次全扫文件系统"，而是进程内编码索引（懒构建、常驻）：

```rust
// cmx-model-meta::definitions::resolve 新增
struct CodeIndex {
    gen: u64,                                       // 构建时的定义树代数（见 4.4）
    dct_by_code: HashMap<String, Vec<DamCoord>>,    // dictCode → DAM 坐标集（排序去重）
    dct_by_table: HashMap<String, Vec<DamCoord>>,   // tableName → DAM 坐标集（回退用）
    doc_by_code: HashMap<String, Vec<DamCoord>>,    // moduleCode → DAM 坐标集
    file_map: HashMap<(String, String), Vec<DamCoord>>, // (kind, file) → DAM 坐标（file 反查用）
}
static CODE_INDEX: OnceLock<RwLock<Option<CodeIndex>>>;
```

- **构建**：首次反查时一次 `list_definitions(None, None, None, None)` 全扫，逐文件 `get_definition` 提取编码（DCT 读 `dictionaryTables[].dictMeta.{dictCode,tableName}`；DOC 读 `moduleMeta.moduleCode`；跳过 base 域与 UNKNOWN 文件）。此后常驻，反查 O(1)。
- **对外函数**：
  ```rust
  pub struct DamPartial { pub domain: Option<String>, pub application: Option<String>, pub module: Option<String> }
  pub struct DamCoord  { pub domain: String, pub application: String, pub module: String }
  pub async fn resolve_dam_by_code(kind: &str, code: &str, partial: &DamPartial) -> Result<DamCoord>;
  pub async fn resolve_dam_by_file(kind: &str, file: &str, partial: &DamPartial) -> Result<DamCoord>;
  ```
- **集群合规**（AGENTS §五）：索引是只读配置的进程内可重建缓存，允许；各节点独立构建、确定性排序保证跨副本一致。

### 4.4 定义树"代数"（generation）——手动改文件自动刷新

解决现状痛点：直接改磁盘定义 JSON（绕过 API）后，`DOC/DICT/BASE_FILE_CACHE`、DocMetaView 缓存、TableSpec 缓存、CODE_INDEX 全部感知不到，只能重启。

**机制**：

```rust
// cmx-model-meta::definitions::resolve 新增
/// 定义树指纹 = (文件数, 最大 mtime)；指纹变化 → generation +1。
/// stat 遍历（不读内容、不解析 JSON），微秒级；节流：扫描间隔默认 2s
/// （代码常量 GEN_SCAN_INTERVAL，暂不做 TOML 配置项，YAGNI），
/// 窗口内访问直接复用上次结果（一次原子读）。
pub async fn definitions_generation() -> u64;
/// 进程内写路径成功后调用，立时代数 +1（0 延迟通道）。
/// 实现注意：bump 时同步把"上次扫描时间"置为当前，让紧随其后的节流扫描
/// 重新采样指纹，避免旧指纹导致二次 +1（二次本身幂等无害，但要可预期）。
pub fn bump_generation();
```

**所有定义派生缓存改为代数感知**（访问前取 generation，失配即清/重建）：

| 缓存 | 现状 | 改造 |
|---|---|---|
| CODE_INDEX（本次新增） | — | 记录构建时代数，失配重建 |
| `DOC/DICT/BASE_FILE_CACHE`（resolve.rs 既有） | 永不失效 | 访问时校验代数，失配整体清空（重建代价低，既有收敛逻辑兜底） |
| DocMetaView 解析缓存（`cmx-doc-store-pg/cache.rs`） | 仅 10 分钟 TTL，`invalidate` 无人调用 | `resolve_doc_meta` 命中前校验代数，失配调**既有** `clear()`；TTL 保留兜底 |
| 校验规范 TableSpec 缓存（`cmx-biz::validation`） | 键含 version，改字段不升版本即陈旧 | 调用方 `resolve_or_build_spec` 把 generation 拼入 spec_key（旧键残留有界且小，可接受，注释注明） |

**两条失效通道叠加**：

1. **进程内写**（`save_definition` / `set_default_version` / `delete_definition`，store.rs 仅有的三个写路径）：成功后 `bump_generation()`——0 延迟；
2. **带外变更**（手动改文件、git pull）：≤ 2s 节流窗口后的下一次访问自动检测 mtime 指纹变化并刷新——**不用重启、不用手动调接口**。

**为什么不用 fs watcher（notify crate）**：集群共享存储（NFS 等）上 inotify 不可靠；原子写（rename 落盘）产生事件噪声需防抖；新依赖 + 常驻后台任务。stat 轮询零依赖、任意文件系统可用、各节点独立自愈。

### 4.5 代码改动清单

| # | 文件 | 改动 | 量级 |
|---|---|---|---|
| 1 | `cmx-model-meta/src/definitions/resolve.rs` | `DamPartial`/`DamCoord`、CODE_INDEX 构建/查询/失效、`resolve_dam_by_code`/`resolve_dam_by_file`（含 409 候选构造）、generation 检测器、三个 file cache 的代数守卫 | ~200 行新增 |
| 2 | `cmx-model-meta/src/definitions/store.rs` | 三个写路径成功后 `bump_generation()` | 3 行 |
| 3 | `cmx-dct-model/src/lib.rs` | `DctQuery` 的 domain/application/module 三字段改 `Option<String>` + 注释（None=缺失自动反查） | ~6 行 |
| 4 | `cmx-dct-store-pg/src/resolve.rs` | `resolve_dict` 首步坐标归一化（None 段 → 反查 → 产出 owned String 三元组）；私有 helper `resolve_doc`/`resolve_or_build_spec` 改收显式 `&str` 参数；spec_key 拼 generation | ~60 行 |
| 5 | `cmx-dct-store-pg/src/hier_service.rs` | 构造 `DctQuery` 处 3 处 `Some(..)` 包裹 | 3 行 |
| 6 | `cmx-dct-api/src/handlers.rs` | dct_meta 的 debug 日志 `q.module` → `as_deref().unwrap_or("")` | 1 行 |
| 7 | `cmx-doc-api/src/handlers.rs` | `DocDataQuery` 的 DAM 三字段改 `Option<String>` + 注释；7 处 `resolve_doc_meta` 调用实参 `&q.x` → `q.x.as_deref()`；debug 日志 ~5 处同样处理 | ~20 行 |
| 8 | `cmx-doc-store-pg/src/resolve.rs` | `resolve_doc_meta` 形参 `&str` → `Option<&str>` + 首步归一化 + 代数守卫（失配调 `cache.rs` **既有**的 `clear()`，cache.rs 本身零改动） | ~55 行 |
| 9 | `cmx-doc-store-pg/src/hier_service.rs` | 3 处 `resolve_doc_meta` 调用：具体坐标实参包 `Some(..)` | 3 行 |

**handler 签名零改动**：dct 8 个 + doc 7 个共 15 个 handler 的签名不动；doc 侧仅调用实参表达式机械微调（`&q.domain` → `q.domain.as_deref()`）。

**明确不动**：`DctQuery`/`DocDataQuery` 的 `dict`/`file`/`doc`/`with_props` 等其余字段、咽喉点归一化之后的主体逻辑及其下游、底层 `resolve_dict_file`/`resolve_doc_file`（仍收 `&str`）、前端一切调用点、`db_id` 路由、`/api/definitions/config`。

**附带收益**：`/dct/data/tokio-zmc-msgpack`、`/dct/upsert|delete|save|export|import`、`/doc/data/*` 全组合、`/doc/data/tokio-zmc-stream`、`/doc/meta` 同步获得 DAM 可选能力；且所有定义派生缓存获得带外变更自动刷新（现状痛点的根治）。

## 五、兼容性、风险与 YAGNI

**兼容性**：

- 带全 DAM 的既有调用走快路径，行为与性能完全不变（仅多一次脏值归一判断）；
- 前端零改动：cmx-data-comp 的 `editSettings.coord` 注入、html-pages `loadDef`、native-pages 全部照常工作；
- 错误语义：零命中沿用 business_error 风格；冲突是新增的 409 场景（此前请求根本到不了 handler）。

**风险与对策**：

| 风险 | 对策 |
|---|---|
| 首次反查全扫成本（读全部定义 JSON） | 仅首次一次，索引常驻；定义总量为文件数十~数百量级，毫秒级 |
| 节流窗口内（≤2s）读到旧缓存 | 业务语义可接受（定义是准静态配置）；窗口为代码常量，需要时可改 |
| TableSpec 旧键残留 | 有界（表数 × 代数）、单体小；注释注明，不治理 |
| 集群跨节点带外变更 | 各节点独立 stat 自愈，≤2s 收敛；与现有"准静态 + TTL 兜底"模型一致 |

**本次不做（YAGNI）**：

- 前端调用点停传 DAM（后续阶段，后端已就绪）；
- Redis pub/sub 缓存广播（`cache.rs` 既有 todo，维持 TTL + 代数兜底）；
- `/api/definitions/config` 反查放宽（设计期工具端点，维持四段必填）；
- BASE 域参与反查（base 文件无 DAM 语义）。

## 六、测试与验证

**单元测试**（`resolve.rs` 内，对纯逻辑注入构造数据，不依赖文件系统）：

- CODE_INDEX 构建：多 DAM、多版本（isDefault/version 收敛）、脏文件容错；
- 反查：partial 过滤、唯一命中、零命中、多 DAM 冲突候选字典序；
- dictCode 优先于 tableName 回退；
- 指纹计算与代数跳变触发清缓存。

**集成验证**（AGENTS §七 开发环境，后端 `cargo run --bin web-server`）：

1. `curl 'http://127.0.0.1:8080/api/dct/data/search?dict=supplier'`（无 DAM，带 API-Key 头）→ 200 + 数据；
2. 构造跨 DAM 同名字典 → 409 + 候选列表；清理；
3. `?domain=basic&dict=supplier` 部分段反查；
4. `curl '.../api/doc/data/sqlx-zmc-msgpack?doc=cmxfico&depth=10'`（无 DAM）→ 200 msgpack；
5. **带外刷新**：服务运行中手动改一个定义 JSON → 等 2s 后请求 → 返回新内容（DCT 与 DOC 各验一次）；
6. 回归：前端冒烟（字典维护页走 `/api/dct/meta`、凭证页走 `/doc/data/sqlx-zmc-msgpack`，均带全 DAM）。

**编译质量**：`cargo check` + `cargo clippy`（AGENTS §四，不用 cargo build 验证编译）。
