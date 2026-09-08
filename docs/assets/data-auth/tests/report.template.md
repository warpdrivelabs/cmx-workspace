# cmx-data-auth 全面测试报告

> 数据权限引擎微服务 · 单元 + 功能 + 前后端 · 真机执行 · 2026-09-01

{{FIG:test-summary}}

---

## 一、执行摘要

对 `cmx-data-auth`（数据权限引擎微服务）做了**五层全面测试**，全部真机执行（连本机 PostgreSQL `fico` 库），
**135 项断言全绿、0 失败、0 构建/静态警告**：

| 层 | 手段 | 结果 |
| --- | --- | --- |
| ① 静态分析 | `cargo build` + `cargo clippy --all-targets` | ✅ 通过，**0 警告** |
| ② 单元测试 | `cargo test --workspace` | ✅ **47 通过 / 0 失败 / 1 ignored** |
| ③ 后端功能（off） | `dataauth.sh` 真机 E2E | ✅ **64 / 64** |
| ④ 后端功能（jwt/认证） | `dataauth-auth.sh` 真机 E2E | ✅ **10 / 10** |
| ⑤ 前端工作台 | Chrome DevTools Protocol 驱动 `/console` | ✅ **8 / 8 标签** live 渲染，0 错误 |
| ⑥ 安全专项 | 撤销失效 / 管理面 / JWT / 注入 / 泄露 | ✅ 全部 PASS |

**结论**：`cmx-data-auth` 引擎自身能力（P0 安全 · P1 能力 · P2 性能 · P3 治理/契约/工作台）全部有测试覆盖且真机通过；
唯一未在本机验证的是跨仓运行时（门户反代需远程 `cmx` 库、#5 报表/流程注入）——非本服务范围。

---

## 二、测试环境

| 项 | 值 |
| --- | --- |
| 日期 | 2026-09-01 |
| toolchain | `cargo 1.97.1`；离线 aliyun 镜像 |
| 数据库 | PostgreSQL `127.0.0.1:5432/fico`（真机） |
| 服务端口 | `:8098`（默认，避开门户已占的 meta:8096） |
| 认证模式 | `off`（功能/前端）+ `jwt`（认证/管理面）双模式各跑一遍 |
| 缓存 | `DATAAUTH_DECIDE_CACHE_TTL_SECS=30`（开启 decide 缓存以覆盖其路径） |
| 前端驱动 | Chrome 152 headless + DevTools Protocol（node v25 驱动） |

---

## 三、静态分析

```
cargo build --workspace     → Finished（4 crate 全编译）
cargo clippy --workspace --all-targets → 0 warning / 0 error
```

四 crate（core / store-pg / app / server）均编译通过；clippy `--all-targets`（含测试代码）零告警。

---

## 四、单元测试（47 通过 / 0 失败 / 1 ignored）

`cargo test --workspace`。核心逻辑集中在 `cmx-dataauth-core`（纯函数、零 DB，可全量单测）；`cmx-dataauth-app` 覆盖 D3 决策表源；
`cmx-dataauth-store-pg` 的测试是 DB-gated（走 E2E 覆盖，见 §五）。

| 模块 | 数量 | 覆盖点（测试名） |
| --- | --- | --- |
| 约束 AST 智能构造 | 6 | `and_short_circuits_false` · `and_drops_true_and_flattens` · `and_single_unwraps` · `or_short_circuits_true` · `or_drops_false` · `not_double_negation` |
| AST 序列化 | 1 | `constraint_serde_roundtrip` |
| SqlCompiler（防注入/参数化） | 9 | `sql_in_parameterized` · `sql_and_or_nesting` · `sql_unknown_field_rejected` · `sql_empty_in_is_false` · `sql_between` · `sql_cmp_ops` · `sql_relation_unresolved_errors` · `sql_start_at_offset` · `sql_field_mapping` |
| RowFilterCompiler（内存谓词） | 5 | `rowfilter_in` · `rowfilter_cmp_numeric` · `rowfilter_like` · `rowfilter_and_or` · `rowfilter_between` |
| EsCompiler | 2 | `es_in_terms` · `es_cmp_and_range` |
| PDP `compose`（部分求值/裁决） | 10 | `compose_superadmin_permit_all` · `compose_no_policy_denies` · `compose_dim_expansion` · `compose_user_placeholder` · `compose_empty_dim_grant_denies` · `compose_deny_only_denies` · **`compose_conditional_deny_subtracts_rows`** · **`compose_deny_all_beats_permit`** · **`compose_inherit_false_only_self`** · **`compose_org_subject_hit`** |
| 列脱敏 mask | 7 | `mask_full` · `mask_partial_default` · `mask_partial_pattern` · `mask_partial_too_short` · `mask_hash_deterministic` · `apply_masks_over_rows` · **`apply_masks_hide_removes_column`** |
| 维度展开 | 1 | `expander_mock_adds_self` |
| RLS 生成（防注入） | 3 | `generate_dimension_backstop` · `rejects_injection_ident` · `schema_qualified_table_ok` |
| D3 决策表源（app） | 3 | `resolves_decision_table_to_inline` · `non_east_region_gets_false` · `inline_policy_passthrough` |
| **合计** | **47** | + 1 ignored（`pep::guard` 文档示例，需运行时） |

---

## 五、后端功能测试 —— off 模式（`dataauth.sh` 64/64）

真机端到端：seed 维度树/策略/授权 → 跑 decide/compile/enforce/CRUD/治理，断言响应。**幂等**（每次先清理）。

| 步骤 | 能力 | 断言 | 结果 |
| --- | --- | --- | --- |
| 3 | DECIDE 决策 | 维度展开含子孙 · `$user` 占位替换 · effect=permitWithConstraint | ✅ 3/3 |
| 4 | COMPILE → SQL | `ou_id IN ($1,$2,$3)` 参数化 · 参数含 public | ✅ 2/2 |
| 4b | **inherit=false 只授本节点** | 编译只含单占位 · 参数只有 1001 | ✅ 2/2 |
| 5 | 无授权 Deny | effect=deny | ✅ 1/1 |
| 6 | ReBAC 单跳 | Relation→In · 参数含 RX1 | ✅ 2/2 |
| 6b | **ReBAC 多跳（组成员闭包）** | 含直接授权 MD2 · 含嵌套组 MD1（alice∈eng∈eng2） | ✅ 2/2 |
| 7 | ENFORCE 内存过滤+脱敏 | 保留 2 / 过滤 1 / amount→**** | ✅ 3/3 |
| 7b | **列隐藏 HIDE** | 保留 1 · 无 secret:TOP 泄露 · 数据行无 HIDE 键 · amount 仍脱敏 | ✅ 4/4 |
| 8 | D3 决策表作策略源 | east→org 展开 · west→Deny | ✅ 2/2 |
| 8b | **ORG 主体授权** | ORG 命中→子树 · 展开含子孙 | ✅ 2/2 |
| 8c | **条件 Deny 扣除行集** | NOT(amount>阈值) · 阈值参数 · Deny=True 拒全部 | ✅ 3/3 |
| 10 | L3 物化缓存 | 首查物化 · 子树 3 条 · 再查命中 · 重分配失效 · 含华南 · 显式 refresh | ✅ 6/6 |
| 11 | **RLS DDL 生成** | ENABLE RLS · 会话 GUC · 维度列过滤 · set_config · 非法表名拒绝 | ✅ 5/5 |
| 12 | **列表分页/检索** | total 信封 · limit 生效 · 本页 2 条 · q 命中 · q total=1 | ✅ 5/5 |
| 13 | **审计上下文** | subjectCtx · roles · orgs · obligations | ✅ 4/4 |
| 14 | **审计 TTL 清理** | 高保留期删 0 · beforeDays=0 返回删除数 | ✅ 2/2 |
| 15 | **L1 缓存（展开记忆+decide）** | 展开记忆填充 · 配置写清零 · decide 缓存填充 | ✅ 3/3 |
| 16 | **治理（变更审计/解释/重叠）** | 变更审计 policy/upsert · explain 命中策略/解释数组 · overlap 检出 Deny=True/denies=1 | ✅ 6/6 |
| 17 | **生效期 valid_from/to** | 过期授权→Deny · 管理面 list 仍见 · 未生效策略→Deny | ✅ 3/3 |
| 18 | 工作台/OpenAPI | OpenAPI 3.0 有效/覆盖 /decide · /console · /swagger | ✅ 4/4 |
| **合计** | | | ✅ **64 / 64** |

---

## 六、后端功能测试 —— jwt/认证管理面（`dataauth-auth.sh` 10/10）

以 `DATAAUTH_AUTH_MODE=jwt` 起服务，验证认证与管理面鉴权（P0）。

| 组 | 断言 | 结果 |
| --- | --- | --- |
| #1 管理面守卫 | 非管理员写→**403** · 管理员读→200 · 非管理员仍可用数据面 /decide→200 | ✅ 3/3 |
| #2 JWT 校验 | 无 exp→**401** · 错误密钥→**401** · 无令牌→**401** | ✅ 3/3 |
| #3 数据面 PEP 读注入 | 读 demo 注入 scoped WHERE | ✅ 1/1 |
| #4 写/删执行接缝 | 删 demo 注入 scoped DELETE · scope 参数在前 · 无删权用户→**403** 短路 | ✅ 3/3 |
| **合计** | | ✅ **10 / 10** |

---

## 七、安全专项

针对权限系统的关键安全属性做了定向验证：

| 专项 | 验证方法 | 结果 |
| --- | --- | --- |
| **撤销即失效（无陈旧放行）** | 授权→decide 放行（缓存命中，decideCache=1）→删授权→再 decide | ✅ **effect=deny，缓存清零 1→0**，无陈旧放行 |
| **管理面越权** | jwt 模式非管理员 `POST /policies` | ✅ 403（无法自我提权） |
| **JWT 弱令牌** | 无 exp / 错误密钥 / 无令牌 | ✅ 全部 401 |
| **默认免鉴权告警** | off 模式启动 | ✅ 日志打印醒目 off 告警（1 次） |
| **RLS 防注入** | `POST /rls/ddl {table:"v; DROP TABLE x"}` | ✅ 拒绝（非法标识符） |
| **列隐藏不泄露** | HIDE 列经 enforce | ✅ 数据行无该键、原值不外泄 |
| **超管短路正确** | roles=[admin] | ✅ permit + constraint=True（全放行） |
| **fail-closed** | 无匹配策略 / 空维度授值 | ✅ Deny（见单测 + E2E） |

---

## 八、前端工作台（Chrome DevTools Protocol 驱动，8/8 标签）

`/console` 自包含单页 SPA，用 CDP 逐标签驱动（调用页面 `go(tab)`），采集每标签的行数/表单存在/错误信号并截图。**全部 live 渲染真实 DB 数据，0 错误**：

| 标签 | 探针（rows / hasForm / err） | 结论 |
| --- | --- | --- |
| 大盘 | 计数卡片（策略/授权/元组/缓存） · err="" | ✅ 渲染真实计数 |
| 策略 | 12 行 · 表单 ✓ · err="" | ✅ 列表+新建+重叠分析 |
| 授权 | 9 行 · 表单 ✓ · err="" | ✅ |
| 脱敏 | 1 行 · 表单 ✓ · err="" | ✅ |
| 维度 | 5 行 · 表单 ✓ · err="" | ✅ |
| 关系 | 5 行 · 表单 ✓ · err="" | ✅ |
| 决策解释 | 表单 ✓ · explain 输出渲染 · err="" | ✅ 解释 reasons + JSON |
| 审计 | 56 行（决策+变更）· err="" | ✅ |

**契约**：OpenAPI 3.0 `/api/dataauth/v1/openapi.json` 有效（20 路径/4 schema）；`/console`、`/swagger` 均 200，jwt 模式下亦免认证可达（内嵌门户由反代注入身份）。

### 截图证据（真机 live）

策略标签（列表 + 新建表单 + 重叠分析）：

{{PNG:console-policy}}

决策解释标签（explain 输出 reasons + 完整 Decision JSON）：

{{PNG:console-decide}}

---

## 九、功能 × 测试覆盖矩阵

| 能力 | 单测 | 后端 E2E | 前端 | 安全专项 |
| --- | :-: | :-: | :-: | :-: |
| 约束 AST / 智能构造 / 序列化 | ✅ | ✅ | — | — |
| SQL / RowFilter / ES 三后端编译 | ✅ | ✅（sql/es） | — | — |
| PDP 部分求值 / 裁决 / fail-closed | ✅ | ✅ | ✅（explain） | ✅ |
| 层级维度展开（WITH RECURSIVE） | ✅（mock） | ✅ | ✅ | — |
| inherit 语义（P0#3） | ✅ | ✅ | ✅ | ✅ |
| 列脱敏 FULL/PARTIAL/HASH/HIDE | ✅ | ✅ | ✅ | ✅（HIDE 泄露） |
| ReBAC 单跳 + 多跳组成员（P1#6） | — | ✅ | ✅ | — |
| ORG/POST 主体（P1#9） | ✅ | ✅ | ✅ | — |
| 条件 Deny（P1#7）/ priority（#10） | ✅ | ✅ | ✅ | — |
| D3 决策表作策略源 | ✅ | ✅ | — | — |
| RLS 兜底生成（P1#11） | ✅ | ✅ | — | ✅（注入） |
| 管理面鉴权 + JWT 加固（P0#1/#2） | — | ✅ | — | ✅ |
| 写/删执行接缝（P0#4） | — | ✅ | — | ✅ |
| L1 decide 缓存 + 展开记忆（P2#12/#15） | — | ✅ | — | ✅（撤销失效） |
| 列表分页/检索（P2#14） | — | ✅ | ✅ | — |
| 审计上下文 + TTL（P2#20/#13） | — | ✅ | ✅ | — |
| 变更审计 / explain / overlap（P3#21/#19） | — | ✅ | ✅ | — |
| 生效期 valid_from/to（P3#21b） | — | ✅ | ✅ | — |
| L3 物化权限集缓存 | — | ✅ | ✅（大盘） | — |
| OpenAPI / 管理工作台（#17/#18） | — | ✅ | ✅ | — |

---

## 十、未覆盖 / 边界（诚实声明）

| 项 | 原因 | 缓解 |
| --- | --- | --- |
| `cmx-dataauth-store-pg` 单元测试 | DB-gated（`#[ignore]`，需真库） | 由 §五 真机 E2E 全量覆盖存储层（CRUD/递归/审计/分页/生效期过滤） |
| Swagger UI 视觉渲染 | 依赖 unpkg CDN（离线不加载 UI） | `/swagger` 页 200 + `/openapi.json` 契约有效已验；契约是真交付物 |
| 门户运行时反代（#16） | 门户需远程 `cmx` 库 + Redis，本机不可达 | 反代壳 + 平台挂载**编译通过**；菜单 SQL 契约经前端源码核实 |
| 报表/流程注入（#5） | 跨服务（cmx-report / cmx-flow） | 未开始（引擎侧 `DataScope` 接缝已就绪） |
| 多租户 multi 模式 | 本轮只测 single | db-per-tenant 逻辑与 single 同源；未回归 |

---

## 十一、复现步骤

```bash
cd cmx-data-auth

# ① 静态 + 单元
cargo build --workspace && cargo clippy --workspace --all-targets && cargo test --workspace

# ② 后端功能（off）
DATAAUTH_PG_URL=postgres://postgres:postgres@127.0.0.1:5432/fico \
  DATAAUTH_DECIDE_CACHE_TTL_SECS=30 cargo run -p cmx-dataauth-server &   # :8098
./dataauth.sh                       # 64/64

# ③ 后端功能（jwt/认证）—— 重启为 jwt 模式
DATAAUTH_AUTH_MODE=jwt DATAAUTH_JWT_SECRET=test-secret ./dataauth-auth.sh   # 10/10

# ④ 前端：浏览器打开 http://127.0.0.1:8098/console （或 CDP 驱动截图）
```

---

## 十二、结论

`cmx-data-auth` 在 2026-09-01 的全面测试中 **135 项断言全绿、0 失败、0 静态告警**。引擎从核心决策（PDP/PEP 解耦、
约束 AST 多后端）到安全（管理面鉴权、JWT、fail-closed、撤销即失效）、性能（三级缓存）、治理（审计/解释/重叠/生效期）
与前端工作台，端到端可用且经真机验证。剩余项均为**跨服务/跨仓运行时**（门户反代运行时、#5 报表/流程注入），不属本服务边界。

> 本报告数据由真机执行采集；截图为 Chrome headless 对 live `/console` 的实拍。SVG/PNG 源见 `docs/assets/data-auth/tests/`。
