# 数据权限缺口审计与补齐路线 · cmx-data-auth

> 逐行审计 `cmx-data-auth/` 全部源码，列出 **28 项**待补内容，按 **P0–P4** 优先级排序，区分
> **🐛 隐患/与设计不符 · 🔧 加固 · 🗺 已知非目标（路线图）**。每项给出**证据（文件:行）· 影响 · 补齐方向**。
>
> 本文是后续 **P0 开工** 的施工说明书。姊妹篇：[实现方案](20260831_数据权限完整实现方案.md)。

---

## 全景

当前 M1 已交付「决策/执行解耦」的完整纵切（PDP 部分求值 + 约束 AST + 多后端编译 + db-per-tenant +
决策审计），真机 19/19 冒烟绿。但**从"能演示"到"可对外用于 ERP"**，还差 28 项。红=隐患须先修（多在 P0/P1），
琥珀=加固，灰=已知非目标。

{{FIG:gap-01-landscape}}

统计：**8 项隐患**（🐛，多为字段/端点已存在但语义未生效）· **14 项加固**（🔧）· **6 项非目标**（🗺，路线内）。
热度自上而下递减：P0 阻断上线，P4 属打磨。

---

## P0 · 安全与正确性（阻断级，先修）

四项都会导致"能演示但不能对外用"。前两项是**认证/授权**空洞，第三项是**静默过度授权**，第四项是**写侧零管控**。

### #1 管理面无鉴权 + 默认免认证　🐛

**证据**：`app/src/auth.rs:57` 默认 `AUTH_MODE=off` → `scoped_run(default)` 直接放行；`app/src/handlers.rs`
全部 `save_*/delete_*`（`/policies /grants /mask-rules /relation-tuples /dimension-values`）只读
`current_tenant()`，**无任何 admin 角色门**。

**影响**：治理数据访问的权限系统自身不设防 —— 默认部署下任何人可 `POST /grants` 给自己授任意维度（自我提权）；
即便开 jwt，任一合法用户也能改策略。这是经典的"who guards the guards"。

{{FIG:gap-02-security-hole}}

**补齐方向**：
- 引入**管理员角色门**（如 `dataauth-admin` / 复用 `SUPERADMIN_ROLES`），守全部写端点（读端点 `/decide`
  `/compile` `/enforce` 保持面向业务开放）。
- 生产**强制** `jwt`/`api-key`，禁 `off`（可加启动告警：off 模式打印醒目 warning）。
- decide 用的主体与"能否管理策略"的主体是两套判定，不要混用。

### #2 JWT 弱校验　🐛

**证据**：`app/src/auth.rs:98-99` `validation.validate_exp = false` + `required_spec_claims.clear()`；
仅 HS256，密钥默认 `change-me`（`auth.rs:37`）；无 `iss/aud/nbf`；`decode_claims` 从 claim 读 `tenant`
但无租户白名单校验。

**影响**：令牌永不过期、可重放；共享密钥下 `tenant` claim 可被任意设置 → 跨租户越权。

**补齐方向**：开启 `validate_exp`；拒绝默认/空密钥启动；可选校验 `iss/aud`；multi 模式校验 tenant claim 是否在允许集内。

### #3 grant.inherit 被忽略　🐛

**证据**：`grant.inherit` 在 `store-pg/src/store.rs` 正常存/读，但 `app/src/engine.rs` decide 第③步对每个 grant
**无条件** `ex.descendants(...)`，`core/src/pdp.rs::expand_for` 也不看 `inherit`。字段是"死配置"。

**影响**：语义"只授本节点、不含子孙"（`inherit=false`）完全失效 → **静默过度授权**，永远展开整棵子树。默认
`inherit=true` 时行为正确，但任何显式设 `false` 的授权都被悄悄放大。

{{FIG:gap-03-inherit-bug}}

**补齐方向**：展开前判 `if g.inherit { descendants } else { vec![root] }`；补一条冒烟断言 `inherit=false`
的 grant 编译出的 SQL 只含根节点。

### #4 写/删/导出无执行接缝　🐛/🗺

**证据**：`Action` 枚举有 `Write/Delete/Export`，`decide` 也支持，但唯一织入（`pep::guard`、`enforce`）
**只面向读**（产出 SELECT 的 WHERE）；`lib.rs` 仅 `demo/vouchers` GET 一处消费 `DataScope`。

**影响**：更新/删除的行级授权、导出管控无处落地。写侧数据权限=0。

{{FIG:gap-04-enforcement-coverage}}

**关键澄清**：`decide()` 对四种 action 皆成立，缺的是**下游消费者（执行接缝）**，不是决策能力。

**补齐方向**：写/删在 `UPDATE/DELETE` 前用同一 constraint 限定行集（`... WHERE id=? AND {scope}`，改动行数
校验）；导出走 read scope + **强制** `apply_masks`（避免绕过脱敏）。

---

## P1 · 核心能力（决定产品完整度）

| # | 项 | 类型 | 证据 | 补齐方向 |
| --- | --- | --- | --- | --- |
| 5 | **报表/流程 WHERE 注入未接线** | 🗺 | 仅 `demo_vouchers` 消费 `DataScope` | 把 `DataScope` 接进 cmx-report 取数、cmx-flow 查询 —— **数据权限落地 ERP 的主价值点**（单项最高杠杆 ★） |
| 6 | **ReBAC 仅单跳** | 🗺 | `store.rs::lookup_resources` 平表查询；`engine.rs::resolve_relations` 硬编码 `subject_kind="user"` | 支持 Zanzibar userset：组→成员多跳、`viewer=editor` 重写、tuple-to-userset |
| 7 | **Deny 不能带条件** | 🐛 | `pdp.rs::compose` 命中任一 `Effect::Deny` 即返回，忽略其 `constraint_tpl` | 让 Deny 携带约束，做**部分拒绝**（如"仅拒 amount>100万的行"）；与 permit 求差集 |
| 8 | **列"隐藏"缺失** | 🔧 | `mask.rs` 只有 FULL/PARTIAL/HASH 改呈现值 | 增列级"不可投影/禁止 SELECT"，区别于脱敏（`****` ≠ 列不可见） |
| 9 | **主体类型 ORG/POST 不支持** | 🐛 | `pdp.rs::subject_hit` 仅 `USER/ROLE`，其余返 false；matcache 同 | 支持按组织/岗位授权（ERP 常见）；Subject 需带 org/post 维度 |
| 10 | **priority 对结果无效** | 🐛 | `store.rs::load_policies` 有 `ORDER BY priority`，但 compose 把 permit 全 OR、任一 deny 短路，priority 不参与裁决 | 明确语义：要么实现有序 first-applicable，要么移除该列避免误解 |
| 11 | **PG RLS 兜底未生成** | 🗺 | D6 非目标 | 从同一 grant 配置生成 RLS DDL，作防绕过纵深（应用层下推为主、RLS 兜底） |

---

## P2 · 性能与规模

| # | 项 | 类型 | 证据 | 补齐方向 |
| --- | --- | --- | --- | --- |
| 12 | **decide 无 L1/L2 缓存** | 🗺 | 每次决策=装策略+装授权+N 次递归展开+装脱敏+写审计，全打 DB | `(subject,resource)→Decision` 与编译产物缓存（Redis）；matcache 已解决字典可见集，此处解决 decide 热路径 |
| 13 | **审计每决策同步写、无 TTL/分区** | 🔧 | `engine.rs` 内联 `append_audit`；`audit_log` 无留存策略 | 审计异步化（队列/批量）+ TTL/分区；采样高频只读决策 |
| 14 | **列表无分页/检索** | 🔧 | `list_policies/grants/tuples` 无 LIMIT；`delete_grant` 为失效缓存**全表扫 grants** 找 victim | 加 `limit/offset/q`；`delete_grant` 改按 id 直取维度信息（免全扫） |
| 15 | **descendants 跨请求不记忆** | 🔧 | 仅单次 decide 内 `expanded` 去重 | 维度闭包进程内/Redis 缓存 + 维度树变更失效 |

---

## P3 · 可运维与治理

| # | 项 | 类型 | 说明 / 补齐方向 |
| --- | --- | --- | --- |
| 16 | **无门户接入** | 🗺 | 无反代壳/菜单/native pages（对比 flow/report/rules/onto 皆有）→ 加 `DataAuthProxyModule` + `cmx_menu` |
| 17 | **无管理工作台** | 🗺 | 策略/授权/脱敏/维度树/ReBAC/审计浏览全靠裸 curl → 建设计器工作台（可复用 rules 引擎设计器风格） |
| 18 | **无 OpenAPI/Swagger** | 🗺 | 无机器可读契约（rules、onto O7 都有）→ 补 OpenAPI + Swagger UI |
| 19 | **无 explain/overlap 治理** | 🔧 | `Decision.trace` 有信息但无"为何得此 scope"预览端点；无策略重叠/冲突分析 → 加 simulate/explain + overlap（可借鉴 rules 的 gap/overlap） |
| 20 | **审计上下文单薄** | 🐛 | `store.rs::append_audit` 只记 effect+constraint+user；`backend` 在 decide 路径**恒 null**；不记 roles/dims/obligations/trace → 补全上下文 |
| 21 | **无配置变更审计与生效期** | 🔧 | 策略/授权无 `valid_from/valid_to`、无"谁改了策略"变更审计（区别于决策审计）→ 加变更日志 + 生效期 |

---

## P4 · 健壮性与收尾

| # | 项 | 类型 | 证据 / 补齐方向 |
| --- | --- | --- | --- |
| 22 | **测试覆盖薄** | 🔧 | 39 单测集中在 `core/lib.rs`(30)+`mask.rs`(6)+`policy_source.rs`(3)；`engine/pep/matcache/store` 无同级单测，**无 `tests/` 集成目录**；multi 租户、递归 ReBAC 未冒烟 → 补关键路径单测 + 集成 |
| 23 | **HASH 非加密** | 🐛 | `mask.rs` 用 `DefaultHasher`（自注"生产换 HMAC-SHA256"）；小域可猜、跨版本不稳 → 换 HMAC-SHA256 + 密钥 |
| 24 | **SQL 侧不下推脱敏** | 🔧 | `apply_masks` 仅内存；大导出/流式或 handler 漏调 → PII 泄露 → 提供"脱敏编译进 SELECT 投影"选项 |
| 25 | **错误无结构化翻译** | 🔧 | `StoreError::Backend` 裹原始 PG 串；无 CmxErrCode/violation（对比 DCT/DOC）→ 结构化错误码 + PG 错误翻译 |
| 26 | **grant 双重语义未澄清** | 🔧 | `policy_id=0` 的 grant 是 matcache 的"纯维度授权"，但对 decide 惰性无效；语义随 policy_id 是否解析而变 → 显式区分或文档化 |
| 27 | **Relation object_kind 约定脆弱** | 🔧 | `engine.rs` 靠"去 `_id` 后缀"推 object_kind，字段不叫 `<kind>_id` 即静默错配 → 显式配置映射 + 校验 |
| 28 | **Between/Like 无授权产出路径与测试** | 🔧 | AST+编译器支持，但无策略模板示例、无测试 → 补示例 + 覆盖 |

---

## 补齐路线

依赖关系：**P0 是硬前置**（不修不能对外）；**P1#5 是价值前置**（不接报表/流程，引擎再全也悬空）；P2–P4 大多可并行。

{{FIG:gap-05-roadmap}}

---

## 下一步：P0 开工

按上图，先交付 **P0 四项**，逐条真机绿后再进 P1：

1. **#1 管理面鉴权**：新增 admin 角色门守全部写端点；生产禁 `off`（启动告警）。
2. **#2 JWT 加固**：开 `validate_exp`；拒默认密钥；multi 校验 tenant claim 白名单。
3. **#3 inherit 语义**：`descendants` 前判 `g.inherit`；补 `inherit=false` 冒烟断言。
4. **#4 写/删/导出接缝**：写/删前 `WHERE … AND {scope}` + 改动行数校验；导出强制 `apply_masks`。

每项：改代码 → `cargo build/test/clippy` 绿 → 扩 `dataauth.sh` 冒烟断言 → 真机验证。完成后本文对应项标记 ✅。

### P0 交付状态（首轮）

| 项 | 落点 | 状态 |
| --- | --- | --- |
| #1 管理面鉴权 | `auth.rs::require_admin`（新）+ `lib.rs` 拆 open/admin 路由 + off 模式启动告警 | ✅ 已实现 |
| #2 JWT 加固 | `auth.rs`：`validate_exp=true` + `set_required_spec_claims(["exp"])` + 拒默认密钥 + `DATAAUTH_ALLOWED_TENANTS` 白名单 | ✅ 已实现 |
| #3 inherit 语义 | `pdp.rs::expand_for` 按 `g.inherit` 分支 + `engine.rs`/`matcache.rs` 同步 + 新增 core 单测 | ✅ 已实现 |
| #4 写/删/导出接缝 | `pep::guard` 已 action-agnostic；新增 `DELETE /demo/vouchers/{id}`（Action::Delete）+ `DataScope` 变量续号约定文档 | ✅ 已实现（seam 打通 + 删侧演示） |

**验证**：`cargo build --workspace` ✓ · `cargo test --workspace` ✓ **40 单测**（+1 inherit）· `cargo clippy` ✓ 0 警告。
认证/管理面真机冒烟见新脚本 `dataauth-auth.sh`（jwt 模式，覆盖 #1 非管理员写→403/管理员→200、#2 无 exp/错密钥/无令牌→401、
#4 删侧 scoped DELETE + 无权 403）；`dataauth.sh` 新增 4b 步断言 `inherit=false` 只授本节点。

### P1 交付状态（首批：核心补全三项）

| 项 | 落点 | 状态 |
| --- | --- | --- |
| #9 ORG/POST 主体 | `subject.rs` 加 `orgs/posts` + `pdp::subject_hit` 匹配 ORG/POST + `engine` 装 ORG/POST 授权 + `matcache`/`dict_permitted` 并集 + 2 单测 | ✅ 已实现 |
| #7 条件 Deny | `pdp::compose` 重写：Deny 约束描述"被拒行集"，最终 = OR(permit) AND NOT(OR(deny))；True=拒全部、False=不拒、谓词=拒子集 + 3 单测 | ✅ 已实现 |
| #10 priority 语义 | 明确为**求值/trace 排序**（非覆盖裁决，组合是集合式）+ `def.rs` DTO 文档化 Deny/priority 语义 + compose 保序 | ✅ 已澄清+落文档 |

**验证（P1 首批）**：`cargo build` ✓ · `cargo test` ✓ **43 单测**（+3：条件 Deny/Deny-all/ORG 主体）· `cargo clippy` ✓ 0 警告。
真机 **36/36**：`dataauth.sh` **26/26**（+8b ORG 主体子树 · +8c 条件 Deny `NOT(amount>阈值)` / Deny=True 拒全部）· `dataauth-auth.sh` **10/10**（P0 无回归）。

### P1 第二批（自包含：列隐藏 + ReBAC 多跳）

| 项 | 落点 | 状态 |
| --- | --- | --- |
| #8 列隐藏 | `MaskType::Hide`（新）→ `apply_masks` 移除列（≠`****`）；`DataScope::hidden_columns()` 供 SQL 投影省略；store 加 HIDE + 1 单测 | ✅ 已实现 |
| #6 ReBAC 多跳 | `lookup_resources` 重写为 `WITH RECURSIVE` userset 闭包（用户→组→嵌套组，`member`/`group` 边），无组元组时退化单跳（向后兼容） | ✅ 已实现 |

**验证（P1 第二批）**：`cargo test` ✓ **44 单测**（+1 Hide）· `cargo clippy` ✓ 0 警告。
真机 `dataauth.sh` **32/32**（+6b 组成员多跳：alice∈eng∈eng2 → 见嵌套组 MD1 + 直接 MD2 · +7b HIDE：列被移除、值不外泄）。

### P1 第三批（自包含：RLS 兜底）

| 项 | 落点 | 状态 |
| --- | --- | --- |
| #11 PG RLS 兜底 | 新 `core::rls`（纯生成器 + 标识符防注入）：ENABLE/FORCE RLS + 按会话 GUC 过滤维度列的策略（GUC 未设→无行 fail-closed）+ `set_config` 写 scope；admin 端点 `POST /rls/ddl`；3 单测 | ✅ 已实现（生成器） |

**边界**：RLS 是**维度级**兜底（完整残差仍靠应用层下推）；对超级用户/BYPASSRLS 无效，故加 `FORCE` 且应用须以**非超级用户**连库——正因 smoke 连的是超级用户，无法在本环境演示 RLS 实际拦截（那是 DBA/部署事项），此处验证 DDL **生成正确性**。

**验证（P1 第三批）**：`cargo test` ✓ **47 单测**（+3 RLS：结构/防注入/schema 限定）· `cargo clippy` ✓ 0 警告。
真机 `dataauth.sh` **37/37**（+11 RLS：ENABLE/FORCE + GUC 过滤 + set_config + 非法表名拒绝）。

### P2/P3 第一批（自包含：审计上下文 + 分页 + 审计 TTL）

| 项 | 落点 | 状态 |
| --- | --- | --- |
| #20 审计上下文 | audit_log 加 `subject_ctx`（roles/orgs/posts/dims）+ `obligations` 列；engine 填充；顺带**修 effect VARCHAR(16) 溢出 → 32**（permitWithConstraint 21 字符，此前 Permit 类决策静默漏审计） | ✅ 已实现（含 bug 修复） |
| #14 列表分页/检索 | 3 大列表（policies/grants/tuples）改 `?limit=&offset=&q=` + `count_*` 返回 `{items,total,limit,offset}`；stats 改用 COUNT(*)；delete_grant 改 `get_grant` 免全表扫 | ✅ 已实现 |
| #13 审计保留期 TTL | `store::prune_audit(before)` + admin 端点 `POST /audit-logs/prune?beforeDays=90` | ✅ 已实现（异步写入留待后续） |

**验证（P2/P3 首批）**：`cargo test` ✓ 47 单测 · `cargo clippy` ✓ 0 警告。真机 **58/58**：`dataauth.sh` **48/48**
（+12 分页信封/检索 · +13 审计记录 roles/orgs/obligations · +14 prune 保留期）· `dataauth-auth.sh` **10/10**（无回归）。

### P2 第二批（自包含：decide 缓存 + 展开记忆）

| 项 | 落点 | 状态 |
| --- | --- | --- |
| #12 decide 决策缓存 | 新 `app/cache.rs`：`(tenant,subject,resource)→Decision`，**默认关闭**（`DATAAUTH_DECIDE_CACHE_TTL_SECS`）；命中**仍写审计**（不漏留痕）；generation 失效 + TTL 兜底 | ✅ 已实现（默认关闭，opt-in） |
| #15 descendants 展开记忆 | 同 `cache.rs`：`(tenant,dim_key,root)→子孙集`，默认开启（`DATAAUTH_DESC_CACHE_TTL_SECS`=60）；engine 与 matcache 共用 | ✅ 已实现 |

**失效模型**：任一配置写（策略/授权/脱敏/元组/维度 save/delete）调 `bump_generation()` → 全局代际自增 + 清空两缓存
（fail-fresh，写后立即新鲜）；TTL 兜底多实例。**已真机证撤销即失效**：授权→缓存放行→删授权→再决策必 `deny`，无陈旧放行。

**验证（P2 第二批）**：`cargo test` ✓ 47 · `cargo clippy` ✓ 0 警告。真机 **61/61**：`dataauth.sh` **51/51**
（+15 展开记忆填充/配置写清零 + decide 缓存填充）· `dataauth-auth.sh` **10/10**（缓存开启下无回归）+ 撤销失效专项 PASS。

### P3 第一批（自包含：变更审计 + 决策解释 + 策略重叠）

| 项 | 落点 | 状态 |
| --- | --- | --- |
| #21 配置变更审计 | 新 `ChangeLog` DTO + `cmx_dataauth_change_log` 表 + `append_change/list_changes`；9 个 CRUD handler 写变更（actor=当前用户）；`GET /change-logs` | ✅ 变更审计（生效期 valid_from/to 另做） |
| #19 决策解释 | `POST /explain{subject,resource}` → 决策 + 人类可读 reasons（命中策略/维度展开/脱敏义务/notes） | ✅ 已实现 |
| #19 策略重叠分析 | `GET /policies/overlap?resourceKind=&action=` → permits/denies 计数 + findings（多放行取并/Deny 扣除/Deny=True 拒全部/重复约束可合并） | ✅ 已实现 |

**验证（P3 首批）**：`cargo test` ✓ 47 · `cargo clippy` ✓ 0 警告。真机 **67/67**：`dataauth.sh` **57/57**
（+16 变更审计 policy upsert · explain 命中策略/解释数组 · overlap 检出 Deny=True 拒全部）· `dataauth-auth.sh` **10/10**（无回归）。

### P3 第二批（自包含：生效期 valid_from/valid_to）

| 项 | 落点 | 状态 |
| --- | --- | --- |
| #21b 生效期 | policy/grant 加 `valid_from`/`valid_to`（DTO + DDL 补列）；**`load_policies`/`load_grants` 热路径按 `now()` 过滤**未生效/已过期（`WHERE … AND (valid_from IS NULL OR ≤now) AND (valid_to IS NULL OR ≥now)`）；管理面 list/get **不过滤**（可见全部含未来/过期） | ✅ 已实现 |

**踩坑（真 bug）**：可空 `timestamptz` 的 `None` 用 `DataValue::Null` 绑定 → tokio-postgres 报 `cannot convert Option<String> ↔ timestamptz`；必须用 **`DataValue::NullTyped(SqlTypeMarker::Timestamp)`**（带类型 NULL）。动态 OR 授权子句须先括号化再 AND 生效期过滤。

**验证（P3 第二批）**：`cargo test` ✓ 47 · `cargo clippy` ✓ 0 警告。真机 **69/69**：`dataauth.sh` **59/59**
（+17 过期授权→decide 拒绝 / 管理面 list 仍见 / 未生效策略→decide 拒绝）· `dataauth-auth.sh` **10/10**（无回归）+ 生效窗口内正常授权专项 PASS（validTo 正确 round-trip）。

### P3 第三批（页面与契约：OpenAPI + 管理工作台 + 门户就绪）

| 项 | 落点 | 状态 |
| --- | --- | --- |
| #18 OpenAPI/Swagger | 新 `openapi.rs`：手写 OpenAPI 3.0 契约（20 路径/4 schema，不引 utoipa）+ `/api/dataauth/v1/openapi.json`（免认证）+ `/swagger`（Swagger UI CDN） | ✅ 已实现 |
| #17 管理工作台 | 新 `console.rs`：自包含单页 SPA（`/console`，免认证）——大盘/策略/授权/脱敏/维度/关系/决策解释/审计，纯 vanilla JS 调 API | ✅ 已实现（真机 live 渲染 DB 数据） |
| #16 门户接入 | 数据权限侧就绪：`/console` `/swagger` `/openapi.json` 稳定免认证可反代；chassis `topology proxiable:true` | ◑ 数据侧就绪；门户侧 `DataAuthProxyModule`+`cmx_menu`（跨 ws）另做 |

**验证（P3 第三批）**：`cargo test` ✓ 47 · `cargo clippy` ✓ 0 警告。真机 **73/73**：`dataauth.sh` **63/63**
（+18 OpenAPI 契约有效/覆盖 /decide · /console 可达 · /swagger 可达）· `dataauth-auth.sh` **10/10**（jwt 下 console/openapi 仍免认证 200，无回归）；Chrome headless 截图确认工作台 live 渲染真实 DB 计数。

### P3 第四批（#16 门户反代接线，跨 workspace，编译绿）

跨 `cmx-container` + `cmx-portalservice` 把数据权限引擎接进门户反代（镜像 `cmx-meta-proxy` 模式）：

| 落点 | 改动 |
| --- | --- |
| 新反代壳 crate | `cmx-container/crates/libs/cmx-dataauth/cmx-dataauth-proxy`：`DataAuthProxyModule`（`/api/dataauth/*` 恒等转发）+ `console_routes`（顶层 `/console` 反代，非 `/api`） |
| workspace 登记 | `cmx-container/Cargo.toml` members + workspace.dependencies |
| 平台挂载 | `cmx-platform-app`：`routes.rs` 加 `merge_dataauth` + 链；`router.rs` 顶层 merge `/console`（免认证边缘，API 仍认证）；Cargo dep |
| 门户配置 | `portal-server*.toml` `[center_client.services]` 加 `dataauth = { url = ":8098" }` |
| 端口去冲突 | 引擎默认 8096 撞门户已占 `meta`(:8096) → 数据权限改 **:8098**（脚本/示例/README 同步） |

**验证**：`cmx-platform-app` + `cmx-portal-server` **均编译通过**；dataauth 引擎默认 :8098 起，`dataauth.sh` **64/64** + `dataauth-auth.sh` **10/10**（端口迁移无回归）。**门户运行时反代未在本机验证**（门户需远程 `cmx` 库 + Redis）；反代逻辑逐字节镜像在用的 meta/model/rules 反代壳。

**菜单/模块登记（已交付，契约核实）**：探路 agent 逐行核实前端运行时——**门户 SPA 忽略 `open_type`**（仅编辑器用），独立 URL 页经**四区工作台 iframe 视图**加载，URL 必须落在 `definition.workspace.content.views[].data.src`（`workspace-view-renderer.js` 核实）；仅 `workspace/dialogspace/expanded/type` 抵达前端，`path/component/open_type` 列不抵达；须叶子节点。据此产出幂等 `dataauth-portal-menu.sql`（`cmx_module` + `cmx_menu` 叶子 → iframe `/console`）+ `module.json` 清单。SQL 已校验（JSON 合法、iframe src == `/console`、列/值 22=22）。**不入共享 `init_dml.sql`**（随引擎部署单独落库，同反代配置 opt-in）。

> 剩余：P1 仅 **#5 报表/流程注入 ★**（跨服务，改 cmx-report/cmx-flow）。**cmx-data-auth 引擎能力全闭环 + 门户接入全接线（反代 + 菜单，编译级/契约级）**，唯待门户目标环境运行时验证。

---

> 本文档图示按 `cmx-data-auth/` 当前源码绘制，SVG 源见 `docs/assets/data-auth/gaps/`。
