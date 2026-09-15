# 关系 backing 去 targetProperty 严格 Palantir 化全链改造方案

> 2026-09-14 · cmx-ontology（本体平台）
> 裁决来源：2026-09-14 用户裁决——`target_property` 去掉，前后端彻底改造，不留技术债；独立新文档，不在 20260913 文档上续改。
> 调研基础：`documents/plans/20260913_cmx-ontology_Palantir关系类型对标调研与backing优化方案.md`（Palantir 四篇官方文档调研 + §十一 遍历链路/FK 四分支/性能实测）。

---

## 一、裁决与目标

### 1.1 已裁决（本轮落地）

1. **FK 严格 Palantir 语义**：外键属性值 = 对端对象**主键**（`oo_<type>.pk` 列）。`target_property`（页面口径 `targetProperty`）从模型、编译、校验、前端 UI、规格数据中**彻底移除**——Palantir 文档明确 FK link 恒为「一端外键属性 → 另一端主键属性」，不存在"属性对任意属性"的 FK 关系。
2. **不留技术债**：`backing_parsed` 的 tagged `{"kind":...}` 第二口径一并废除，页面 fk 形状成为**唯一**可识别口径；编译层 `tp=Some` 属性对属性 JOIN 两分支删除。
3. **同批打包治理项**（上轮 §11.5 P0，"不留债"精神下并入，单项可裁）：save 跨端校验 + 方向规则、FK 键表达式索引自动维护、legacy GET 方向自判、JoinTable/Intermediary 真编译（消除占位静默回退）。

### 1.2 改造后口径（唯一）

```json
{"fk": {"sourceProperty": "settleCurrencyId", "side": "b"}}
```

- `sourceProperty`：**持键端**对象的外键属性（`side` 端），值必须存对端对象 pk（数值 id，v3 铁律不变）。
- `side`：持键端，**缺省时按 cardinality 自动推导**（oneToMany→b、manyToOne→a、oneToOne→a）；显式传值时校验与基数一致（见 §二 2.4）。
- **对端恒为主键**，无需（也不允许）声明对端属性——Palantir 的 `foreignProperty` 在本平台恒等于对端主键属性 `id`，因此以"恒主键"约定替代显式声明。

### 1.3 存量影响面（已核实）

实库 `om_link_type` 仅 6 条关系，全部 `{"fk":{"side":"b","sourceProperty":"…","targetProperty":"id"}}` 且 `targetProperty` 恒为 `"id"`（= 对端主键）——**迁移为纯 JSON 剥键，零语义损失**。无 tagged 形状、无 JoinTable/Intermediary 存量、`ol_edge` 0 行。

---

## 二、后端改造（cmx-ontology 仓，4 文件）

### 2.1 `cmx-onto-model/src/def.rs` —— 枚举与解析单口径化

1. **枚举收窄**（现 L298-307）：`ForeignKey { property: String, side: LinkEnd }`，删除 `target_property` 字段及其文档注释；枚举文档（L282-291）改写为新口径示例 `{"fk":{"sourceProperty":"buyerId","side":"b"}}`，明确"对端恒主键（Palantir Key 语义）"。
2. **`backing_parsed` 单认页面口径**（现 L355-378）：
   - 认三种页面形状：`fk` / `joinTable` / `intermediary`（后两种为本轮真编译配套，§四、5）；
   - **删除 tagged `{"kind":...}` 分支**（L374-376）——历史口径废除，无法识别一律 `Edge` 兜底；
   - fk 分支不再读 `targetProperty`。
3. **`validate` 收紧**（现 L392-412）：
   - FK：`sourceProperty` 必填 + 合法标识符（保留现有两条）；
   - **新增白名单键校验**：`fk` 对象仅允许 `sourceProperty` / `side` 两键，出现 `targetProperty` 即报错，文案指明废除："targetProperty 已废除：外键恒匹配对端主键，请删除该字段后重试"；
   - JoinTable / Intermediary：三字段必填 + 合法标识符（配套 §四、5）。

### 2.2 `cmx-onto-model/src/lib.rs` —— 单测重写（L185-281 附近）

- L190/L205：枚举构造去 `target_property` 实参；
- L235-243（`targetProperty:"empNo"` 解析用例）：改为**拒绝用例**——validate 报"targetProperty 已废除"；
- L269-273（`{"fk":{"targetProperty":"id"}}` 缺 sourceProperty）：期望报错文案改为白名单/废除语义；
- L280（`targetProperty:"2bad"` 非法标识符）：同上；
- 新增：joinTable / intermediary 页面形状解析 + 校验用例；tagged 形状 → Edge 兜底用例。

### 2.3 `cmx-onto-store-pg/src/compile.rs` —— 编译四分支归两分支

1. **分派**（L132-133）：`ForeignKey { property, side } => self.fk_search_around(&inner, ends, src_end, &property, side)`。
2. **`fk_search_around`**（L163-215）：删除 `target_property` 参数与 `tp=Some` 两分支（L183-190、L200-207），保留已实测验证的 `tp=None` 两分支原样：
   - FK 在源端表（`side == src_end`）：`SELECT DISTINCT s.props->>'{prop}' AS pk FROM {src_tbl} s WHERE s.pk IN ({inner}) AND s.props->>'{prop}' IS NOT NULL`（fk 值即对端 pk）；
   - FK 在终端表（`side != src_end`）：`SELECT DISTINCT t.pk AS pk FROM {terminal_tbl} t WHERE t.props->>'{prop}' IN ({inner})`。
3. **JoinTable / Intermediary 真编译**（替换 L135 `_ =>` 回退，Edge 兜底仅剩真 Edge）：
   ```rust
   // JoinTable：left_column↔A端主键、right_column↔B端主键（声明语义固定，Palantir 同构）
   LinkBacking::JoinTable { table, left_column, right_column } => {
       let (from_col, to_col) = match src_end { A => (&lc, &rc), B => (&rc, &lc) };
       format!("SELECT DISTINCT j.{to_col} AS pk FROM {tbl} j WHERE j.{from_col} IN ({inner})")
   }
   // Intermediary：中间对象两属性各存两端 pk
   LinkBacking::Intermediary { object_type, left_property, right_property } => {
       let (from_p, to_p) = match src_end { A => (&lp, &rp), B => (&rp, &lp) };
       format!("SELECT DISTINCT i.props->>'{to_p}' AS pk FROM oo_{intermediary} i WHERE i.props->>'{from_p}' IN ({inner})")
   }
   ```

### 2.4 `cmx-onto-app/src/handlers.rs` —— 留痕与 save 治理

1. **B2 留痕**（L181-191）：`for key in ["sourceProperty", "targetProperty"]` → `["sourceProperty"]`；注释同步新口径；顺带对含 `kind` 键的 tagged 形状打 warn（+3 行——旧口径直写由静默变有痕）。
2. **save 跨端校验**（`save_link_type` L193 起，validate 后、落库前，async 查属性注册表）：
   - FK：`sourceProperty` 必须存在于**持键端**对象类型的属性定义中（`store().get_object_type` 查 `properties`）；
   - JoinTable / Intermediary：两端/中间对象类型必须已存在；**JoinTable 另以 `to_regclass` 查连接表已建**，缺表报明确 business_error——否则索引维护 `CREATE INDEX` 撞 relation not exist 使 save 500（与 §五 ensure 空表修复同型，落点在非 oo_ 表的连接表）。
3. **save 方向规则 + side 推导**（Palantir 编辑约束"其中一端的 key 必须映射到该端自己的 Primary key"的轻量版）：
   - `side` 缺省时按 cardinality 推导：OneToMany→b、ManyToOne→a、OneToOne→a（validate +4 行；现网 6 条显式 `side:"b"` 兼容）；
   - `FK + ManyToMany` → 拒绝；
   - `FK + OneToMany` → `side` 必须 `"b"`（many 端持键）；`FK + ManyToOne` → `side` 必须 `"a"`；`FK + OneToOne` → 任意；
   - `JoinTable` → cardinality 必须 `ManyToMany`；`Intermediary` → 建议（校验拒绝）`ManyToMany`；
   - 违例报 `business_error`，文案写明期望 side。缺省 side 的最小 payload（`{"fk":{"sourceProperty":"x"}}` + 缺省 OneToMany）推导为 b 后合法——消除「两个缺省值（OneToMany+A 端）互相矛盾」的默认值陷阱。实现约定：**`backing_parsed` 解析层对 side 只透传（serde 缺省语义不变）、推导只发生在 validate**，防止两层各推一份分叉。
4. **非 Edge 关系禁写 ol_edge（fail-fast）**：`put_link` / `delete_link`（`object_handlers.rs` L129-147）与动作 AddLink sideEffect（`action_exec.rs` 写 ol_edge 处）读 `backing_parsed`，非 Edge 一律 `business_error`（"该关系为连接表/中间对象背书，请直接维护连接表/中间对象数据"）——杜绝「写入返回 200 成功、查询永不生效」的静默假写（约 +10 行）。按 backing 分派写连接表/中间对象 props 为后续增强。

### 2.5 查询侧影响面（三形态齐全后的完整清单）

**要改的**（全部已在本节列出，仅四处）：`backing_parsed` 识别 `joinTable` / `intermediary` 形状（2.1）→ `compile.rs` 两段新 SearchAround SQL（2.3）→ save 存在性/方向校验（2.4）→ 索引自动维护（§五）。

**零改动的**：backing 对查询栈是**纯 SQL 生成策略替换**——编译器对上层输出的契约不变（「终端对象类型 + 终端 pk 集合 SQL」），因此 `object-sets/load` 编译入口、PEP 读侧（`link_resolver.ends` 只读关系两端，不看 backing）、SearchAround 方向判定（源对象类型与 ends 比对得出，`compile.rs` L126-129）、explorer / 360 / studio 钻取消费端**全部不动**。ol_edge 链路中 Edge 关系读+写照旧；非 Edge 关系的 `/links` 写入由静默死写改为显式拒绝（§2.4-4）。

**连接表宿主约定（MVP）**：连接表建在本体库（`cmx_onto`）普通表，由工具/SQL 预建（遵循 sql-guide 规范），**两列类型必须 `text`（与 `oo_*.pk` 同型）**——编译 SQL 是 text 语义，按直觉建 `BIGINT` 会在遍历时报 `operator does not exist: bigint = text`；scenario-spec.md 连接表示例补 DDL。save 仅校验表名/列名合法性，查询遇缺表按 SQL 错误 fail-fast（不静默 0 结果）。「Generate join table（按两端主键自动建表）」列为后续可选增强（对标 Palantir 同名按钮）。

---

## 三、前端改造（两处真源；三形态创建 + 展示）

### 3.0 形态与基数联动（Palantir 同款约束）

| 基数 | 可选 backing | UI 形态 |
| --- | --- | --- |
| oneToMany / manyToOne / oneToOne | 仅 **FK** | 持键端属性一栏（必填）+ 对端只读「主键：id」；side 按基数自动（oneToMany→b、manyToOne→a、oneToOne→a，高级可改） |
| manyToMany | **连接表** 或 **中间对象**（二选一） | 连接表：表名 + 左列（A 端主键）+ 右列（B 端主键）；中间对象：中间对象类型下拉（已注册对象类型）+ 左属性 + 右属性 |

designer 速建气泡与 studio 画布表单的「基数」下拉切换时形态区联动；保存按形态调 `LINK_BACKING_FK` / `LINK_BACKING_JOIN_TABLE` / `LINK_BACKING_INTERMEDIARY`（state.js 新增后两者）。FK 在 manyToMany 下不可选（与后端方向规则 §二 2.4 双向对齐）。

### 3.1 `frontend/cmx-ontology-graph` 仓（vendor 构建真源）

1. `src/model/types.ts` L83：删除 `targetProperty?: string`；新增可选 `backing?: "fk" | "joinTable" | "intermediary"`；
2. `src/render/svg.ts` L372：`tgtProp = e.targetProperty ?? primaryKeyProp(tgtNode)` → `tgtProp = primaryKeyProp(tgtNode)`（L371 源端回退链保留）；边上标注按 `backing` 分形态：fk 显示持键属性（现状），joinTable / intermediary 显示类型徽标（「连接表」/「中间对象」）；
3. `src/element/cmx-ontology-graph.ts` L582-583：`link-add` detail 不再透传 `tgt.prop → detail.targetProperty`；
4. **同步 vendor**：该仓执行 `./build.sh && ./sync-component.sh`，产物落到 `backend/cmx-container/assets/onto/web/ui-native/vendor/cmx-ontology-graph.js`（AGENTS §四、8 铁律：禁改 vendor）。

### 3.2 `backend/cmx-container/assets/onto/web/ui-native/onto/`（studio + designer）

| 文件 | 位置 | 改造 |
| --- | --- | --- |
| `studio/state.js` | L317-318 | `LINK_BACKING_FK(sourceProperty, side)` → `{ fk: { sourceProperty, side } }`；**新增** `LINK_BACKING_JOIN_TABLE(table, leftColumn, rightColumn)` / `LINK_BACKING_INTERMEDIARY(objectType, leftProperty, rightProperty)` |
| `studio/canvas.js` | L120-170、L232 | 速建表单按基数三形态：FK 只留持键端属性下拉（原 B 端连接属性下拉删除，改只读「对端主键：id」）；manyToMany 出连接表/中间对象两形态表单；`LINK_BACKING_*` 调用同步；L232 `b.kind === 'foreignKey'` 旧口径死代码顺带清理 |
| `studio/runtime.js` | L1181、L1363-1364、L1415、refCheck 死代码 | 两侧连接属性 → 仅持键端属性落 `backing.fk`（side 按基数推导）；fk 提取、side 归位与画布回显扩展三形态；`b.kind === 'foreignKey'` 旧口径死代码顺带清理 |
| `studio/inspector.js` | L63-69、L715-722 | 人读行三态：fk「持键端·prop → 对端主键(id)」/ joinTable「表(左列 ↔ 右列)」/ intermediary「中间对象(左属性 ↔ 右属性)」；编辑表单三态（对端侧只读） |
| `designer.js` | L25、L87-88、L465-490、L568、L604、L1635、L1689-1695、L1729-1749 | 气泡「属性映射」区按基数联动三形态（FK 删「目标属性」输入框改只读；manyToMany 出连接表/中间对象表单）；**「源属性」由自由文本 input 改为注册属性下拉**（复用 canvas 属性下拉同款数据源——新 save 跨端校验下自由手输打字错误全变硬失败）；`linkProps` 会话映射、specEdge/live 重挂链路去 `targetProperty`、按形态落库 |

> 主题红线：以上 UI 片段沿用现有 `var(--o-*)` / `var(--sap*)` 变量，不新增硬编码色值（CI 一票否决项）。

---

## 四、存量数据迁移与技能同步

### 4.1 数据迁移（实施时在 `cmx_onto` 库执行）

```sql
UPDATE om_link_type
SET backing = jsonb_set(backing, '{fk}', (backing->'fk') - 'targetProperty')
WHERE backing->'fk' ? 'targetProperty';
-- 预期 UPDATE 6；复核：SELECT count(*) FROM om_link_type WHERE backing->'fk' ? 'targetProperty';  → 0

-- 版本快照同步剥键（红队 P1：漏掉会被 validate_snapshot 以「targetProperty 已废除」硬阻断历史版本回滚）
UPDATE om_version
SET snapshot = jsonb_set(snapshot, '{linkTypes}', (
  SELECT jsonb_agg(CASE WHEN v->'backing'->'fk' ? 'targetProperty'
                        THEN jsonb_set(v, '{backing,fk}', (v->'backing'->'fk') - 'targetProperty')
                        ELSE v END ORDER BY ord)
  FROM jsonb_array_elements(snapshot->'linkTypes') WITH ORDINALITY AS t(v, ord))
WHERE snapshot->'linkTypes' @? '$[*].backing.fk.targetProperty';
-- 预期 UPDATE 1（当前实库 1 行归档快照，已实库预览验证剥键正确、其余字段无损）；复核：
--   SELECT count(*) FROM om_version WHERE snapshot->'linkTypes' @? '$[*].backing.fk.targetProperty';  → 0
-- @? 路径存在匹配任意值（不限定 "id"，防未来其他取值漏剥）；WITH ORDINALITY 保序（diff 展示稳定）
```

六条全为 `targetProperty:"id"`，剥离后语义不变（对端恒主键），**无需改任何对象行数据**。

> ⚠️ 实施修正（e2e 发现）：上段"无需改对象行数据"断言有误——现网对象 **pk 是业务键**（如 `oo_Currency.pk='CNY'`）而外键属性存的是**数值 id**（`settleCurrencyId='1'`），改造前靠 `targetProperty:"id"`（props 对 props）掩盖了 pk≠id 的事实。严格化后「外键值=对端 pk」语义下必须把外键值重写为对端 pk，六条关系各一条映射 UPDATE（按对端 `props->>'id'` 找到对端行、取其 pk 回写；外键为空的行自然不更新）：
>
> ```sql
> UPDATE oo_Supplier  s SET props = jsonb_set(s.props,'{settleCurrencyId}',to_jsonb(t.pk)) FROM oo_Currency t WHERE t.props->>'id' = s.props->>'settleCurrencyId';
> UPDATE oo_Supplier  s SET props = jsonb_set(s.props,'{buyerId}',        to_jsonb(t.pk)) FROM oo_Employee t WHERE t.props->>'id' = s.props->>'buyerId';
> UPDATE oo_Warehouse s SET props = jsonb_set(s.props,'{managerId}',      to_jsonb(t.pk)) FROM oo_Employee t WHERE t.props->>'id' = s.props->>'managerId';
> UPDATE oo_Material  s SET props = jsonb_set(s.props,'{baseUomId}',      to_jsonb(t.pk)) FROM oo_Uom      t WHERE t.props->>'id' = s.props->>'baseUomId';
> UPDATE oo_Contract  s SET props = jsonb_set(s.props,'{currencyId}',     to_jsonb(t.pk)) FROM oo_Currency t WHERE t.props->>'id' = s.props->>'currencyId';
> UPDATE oo_Contract  s SET props = jsonb_set(s.props,'{supplierId}',     to_jsonb(t.pk)) FROM oo_Supplier t WHERE t.props->>'id' = s.props->>'supplierId';
> ```
>
> 已执行（12/12/3/10/3/3 行），六关系正反向遍历 12/12 复验通过。演示规格重灌时外键值同样须写对端 pk。

> 快照处置裁决（红队分歧点 4）：`om_version` 快照是 studio 版本管理的业务快照、非审计归档（无合规不可变诉求）——**剥键**优于「重挂基线+旧版作废」（旧版本保留、随时可回滚）与「validate 留 legacy 例外」（给 targetProperty 开后门，违背彻底废除裁决）。

### 4.2 `cmx-onto-toolkit` 技能与演示规格

1. `references/scenario-spec.md` L46-53：backing 口径注释改写——`{"fk":{"sourceProperty","side"}}`、对端恒主键、targetProperty 已废除、外键属性存真实外键值（= 对端 pk）；
2. `examples/procurement/scenario-spec.json` L532-613：六处删 `"targetProperty": "id"` 行；
3. `examples/procurement/walkthrough.md`：grep 无 `targetProperty`，实施时顺带核对"属性映射"相关描述字样；
4. 根 `SKILL.md` 无口径描述（已 grep 确认），不动。

---

## 五、实施顺序（4 批）

| 批 | 内容 | 验证 |
| --- | --- | --- |
| ① 后端口径 | §二 2.1-2.3（def.rs / lib.rs 单测 / compile.rs） | `cargo test --workspace`（cmx-ontology workspace 全量——顺带修复现存坏账：store-pg 内嵌测试仍以旧两字段构造书写，当前 `cargo test -p cmx-onto-store-pg` 本就编译不过 E0063，`cargo check` 看不出来） |
| ② 后端治理 | §二 2.4（跨端校验/方向规则/非 Edge 禁写）+ 索引自动维护 + legacy GET 方向自判（`object_handlers.rs` L227-248：`ends` 后按 `object_type` 命中端判 Forward/Reverse，未命中报 404，**自关联 A==B 取 Forward**） | `cargo test --workspace`；⚠️ 不单独重启生效（见下方发布编排） |
| ③ 数据+规格 | §四 4.2 技能/规格修改 → 4.1 迁移 SQL（含 om_version） | psql 复核 om_link_type / om_version 均 0 残留；六关系正反向 search-around 复验（POST `/object-sets/load`） |
| ④ 前端 | §三 3.1（build+sync vendor）→ 3.2 五文件（三形态创建+展示） | studio/designer UI 冒烟：FK（仅持键端属性）、连接表、中间对象三形态各建一条关系 → 落库对应新形状 → explorer 正反向遍历全通 |

**发布编排（防「白名单先行」保存失败窗口）**：批①②合入后**不单独重启**后端——旧 designer.js / 旧 spec / 未迁移存量恒带 `targetProperty` 键，白名单先生效会让 designer 速建、studio 画布、onto_seed 灌数三条通道全部保存报错，且静态资源无 hash 指纹、浏览器缓存用户会持续踩中。收口顺序：①②代码就绪 → ③技能/spec 修改 + ④前端 build+sync **全部完成** → 执行 §4.1 迁移 SQL（**合入后即可尽早执行**——旧后端对剥键无感，先迁移只会缩小意外重启的暴露窗口）→ **再重启后端**（白名单生效时前端/规格/存量已全部无 targetProperty）→ UI 冒烟（提示浏览器强刷防旧缓存；ui-native 资产为运行时目录投递、落盘即生效，无需重启 cmx-container）。

索引自动维护（批②）挂载点：`store-pg` 层 `upsert_link_type` 内，**建索引前先复用对象写入同款 `ensure_object_table` 确保持键端表已物化**（新注册未录数的对象类型建空表即可——否则 `CREATE INDEX` 报 relation not exist，把 save_link_type 打成 500，"先建模后录数"流程当场断掉）：

```sql
CREATE INDEX IF NOT EXISTS idx_oo_<持键端类型>_<prop> ON oo_<持键端类型> ((props->>'<prop>'));
```

**只建不删**：改 sourceProperty / 删关系时旧索引残留不清理——同一 (持键端, 属性) 可被多条关系共享，DROP 会误伤仍在用的关系（遍历从 19.2ms 静默退化回 65.6ms 且无报错）；残留索引仅占磁盘与写放大，确需清理时手工 DROP。命名统一**小写不加引号**（PG 标识符大小写折叠 + 63 字节截断，DROP/CREATE 两侧规则不一致会让 `IF EXISTS` 静默空转）。对端匹配走 pk 主键索引，无需额外索引；JoinTable/Intermediary 启用时同理对连接表两列 / 中间对象两属性建表达式索引（连接表缺表已在 save 校验 `to_regclass` 拦截，索引维护天然安全）。验收基准：20260913 文档 §11.7 十万行实测（FK 无索引 65.6ms → 有索引 19.2ms）。

---

## 六、验证清单

- [ ] `cargo test --workspace`（cmx-ontology 全量，含 store-pg 内嵌测试）：单口径用例全绿（fk 解析 / targetProperty 拒绝 / tagged→Edge 兜底 / joinTable·intermediary 解析与校验 / side 缺省推导）
- [ ] 迁移 SQL 执行：om_link_type 6 行更新、om_version 1 行更新，两表复核 0 残留
- [ ] 改造前基线版本的回滚（versions/restore）不再被 validate_snapshot 阻断
- [ ] 六条关系正反向 Search-Around 复验全通（buyerOf / settleCurrency / useUom / signContract / contractCurrency / managerOf）
- [ ] save 方向规则：造反例（FK+manyToMany、JoinTable+非 manyToMany）被拒；**缺省 side 最小 payload（`{"fk":{"sourceProperty":"x"}}` + 缺省 OneToMany）落库成功且推导为 b**
- [ ] 未录对象数据的新对象类型：建模 → 速建 FK 关系保存成功（ensure 空表路径，不 500）
- [ ] 非 Edge 关系 `POST /links` 返回 business_error（fail-fast 生效，无静默假写）
- [ ] 索引自动维护：save 后 `oo_<持键端>` 出现表达式索引（含空表场景）；改 sourceProperty 后新索引自动建、旧索引按「只建不删」残留无害
- [ ] legacy `GET /objects/{type}/{pk}/links/{link}`：A 端对象与 B 端对象各调一次均返回正确终端（自关联取 Forward）
- [ ] cmx-ontology-graph 仓 `./build.sh && ./sync-component.sh` 成功，vendor 更新
- [ ] studio 速建气泡/画布建 FK 关系（仅持键端属性）→ 落库 `{"fk":{"sourceProperty","side"}}` → explorer 钻取通
- [ ] 连接表端到端：预建连接表 → 气泡 manyToMany·连接表形态建关系 → 落库 `{"joinTable":{...}}` → 正反向 SearchAround 通
- [ ] 中间对象端到端：造中间对象类型+数据 → 气泡 manyToMany·中间对象形态建关系 → 落库 `{"intermediary":{...}}` → 正反向 SearchAround 通
- [ ] 基数联动：非 manyToMany 时形态区锁定 FK；manyToMany 时 FK 不可选（前后端双向一致）
- [ ] 关系图边标注：fk 持键属性 / joinTable·intermediary 类型徽标显示正确（vendor 同步后）
- [ ] 主题检查：改动片段无硬编码色值，亮暗两态正常

---

## 七、风险与边界

1. **tagged 口径废除**：外部若有工具直写 `{"kind":...}` 将回退 Edge。已核实实库无 tagged 存量、后端无其他写入方；B2 留痕对含 `kind` 键的 backing 打 warn（§2.4-1），静默变有痕；文档口径唯一。
2. **语义收窄**：去掉 target_property 后"外键属性 ↔ 对端非主键属性"关系不可表达（Palantir 同口径）。此类场景改为：对象主键即业务锚，或外键属性改存对端 pk（v3 铁律已是主流形态，v6 数据零改动）。
3. **前端 vendor 重建**：cmx-ontology-graph 构建链路若失败，ui-native 侧改动仍独立成立（designer/studio 不依赖 vendor 的新字段），仅关系图渲染的 targetProperty 展示残留旧回退逻辑，需重试同步。
4. **改动文件均未提交**：全部等用户明确提交指令；`.env` 一律不动。

---

## 八、实施修正（2026-09-15 · 第二轮裁决）：targetProperty 缺省化受控回归 + 统一 FK 锚点表单

本轮实施 + e2e/UI 验证后，用户复核发现两处设计问题，二次裁决修正：

### 8.1 问题

1. **FK 匹配语义收窄过严**：「外键恒 = 对端 pk 列」堵死了"外键存对端 code 等自然键"的合法场景（对端表常有 id/code 多个候选键，pk 锚定不统一——Currency pk=CNY 而 id=1 已经踩过一次，那次靠改数据侥幸解决，反向场景改数据不可行）。
2. **新建与编辑表单不统一**：新建（速建弹框/气泡）显示 A/B 端两个属性下拉（其一为摆设），编辑（Inspector）只有一个持键端下拉——交互不对称且配对关系不可见。

### 8.2 修正后口径

`{"fk": {"sourceProperty", "side"?, "targetProperty"?}}`

- `targetProperty` **缺省 = 对端主键**（pk 列，严格 Palantir 语义，主流路径，已迁移数据零改动）；**显式指定 = 对端属性对属性匹配**（受控扩展；validate 校验其存在于对端对象属性；编译走属性对属性 JOIN 分支）。
- 注意显式化细节：对象 **pk 列**与 props 里的 **id 属性**不保证同值（币种 pk=CNY / id=1），UI「对端匹配属性」下拉中「主键（pk 列）」与「id」是两个选项。

### 8.3 统一 FK 锚点表单（新建 / 编辑同一形态）

| 栏 | 内容 |
| --- | --- |
| 外键在哪端（仅 oneToOne 显示） | A / B 切换（一对多/多对一由基数自动定，不显示） |
| 外键属性（持键端 · 对象名） | 候选 = 持键端属性 |
| 对端匹配属性（对端 · 对象名） | 首项「主键（pk 列）」缺省选中，其余列对端全量属性 |

- 落库：对端选「主键」→ 不落 targetProperty 字段（与现网六条数据形状一致）；选其他属性 → 落 `targetProperty`。
- 交接设计器（designer 气泡）、本体工作室（canvas 速建弹框 + Inspector 编辑）三处同构；graph 组件恢复 targetProperty 终点锚（spec 透传）。

### 8.4 改动落点

- 后端：`def.rs`（枚举/解析/validate 恢复 target_property）、`compile.rs`（四分支回归）、`handlers.rs`（跨端校验对端属性存在性）、`store.rs`（索引维护覆盖对端匹配属性）、`lib.rs` 单测（显式解析/非法拒绝）。
- 前端：`state.js`（三参构造）、`canvas.js`/`designer.js`（两栏 + oneToOne 端切换 + 动态候选）、`inspector.js`（编辑两栏）、`runtime.js`（重组带 targetProperty/fkSide）、graph 仓三文件恢复 + vendor 重建。
- 数据零迁移；`scenario-spec.md` 口径注释同步（优先级：①外键=pk 省略 targetProperty ②显式指定真实存放属性 ③不得已改数据）。

## 九、UI 验证与收尾修复（2026-09-15 · 第三轮）

第二轮改造完成后，浏览器端到端 UI 走查（本体工作室，编辑视角）全部通过；过程中发现并修复两处收尾问题。

### 9.1 UI 走查结论（全部通过）

| 项 | 结果 |
| --- | --- |
| 速建弹框两栏缺省 | 对端匹配属性缺省选中「主键（pk 列）」（`fillOpts` 以 property 显式选中，修复 ui5-select 二次重建 selected attribute 失效）；持键端标签「Warehouse · B 端」/「Supplier · A 端」正确 |
| oneToOne 端切换（弹框） | 基数切 1:1 →「外键在哪端」出现；切 B 端 → 持键端/候选端互换、对端缺省恒回主键 |
| 弹框真建 oneToOne + 外键 B 端 | 落库 `{"fk":{"sourceProperty":"warehouseCode","side":"b"}}`（缺省主键正确省略 targetProperty），捕获请求报文与设计一一对应 |
| Inspector 两栏回显 | 外键属性回显持键端属性、对端匹配属性回显「主键（pk 列）」、配对提示「Material·warehouseCode ↔ Warehouse·主键（pk 列），两值相等即成链」 |
| Inspector oneToOne | 「外键在哪端」渲染并回显当前 side；在线改端（A↔B）保存落库验证通过（side 'b'→'a'，外键属性同步改为持键端属性 materialCode） |
| Inspector 改对端匹配属性保存 | supplierCode → 落库 `targetProperty:"supplierCode"` ✓ |
| 跨端校验 | 改端后保留旧端属性保存 → 后端 400（sourceProperty 不在持键端）按设计拦截 |
| 删除链路 | 删除确认弹框提示锚点影响（「该关系带锚点映射（外键 xxx）」）；两条 UI 造的关系均经 UI 删除，清单回到 6 条原始关系 |

### 9.2 走查发现并修复的两处问题

1. **清单缺锚点（后端）**：`/manifest?types=linkTypes` 行不含 `backing`（`LinkTypeMeta` 无此字段）——Inspector 选中关系若走清单态会误判「未登记锚点」，此时点保存会把锚点洗成 `{}`（回退 Edge）。修复：`LinkTypeMeta` 增 `backing: Option<Value>` + `list_link_types` SELECT 补 `l.backing`；`cargo check` + 单测全绿，重启后 manifest 六条关系均带锚点。
2. **Inspector 改端不联动（前端）**：锚点区为渲染期静态生成，change 无联动——切「外键在哪端」后外键属性候选仍是旧端属性，保存必被跨端校验拒（切端在编辑表单实际不可用）。修复：`runtime.js onRootChange` 顶部加基数/`fkSide` 分支——先把表单的基数与端选择写回 `selDef`（渲染真源）再 `renderAllRight()`，候选端/配对提示随切换重建（对齐 designer 气泡的联动模式）。

### 9.3 环境备注

走查期间开发库经 VPN 访问间歇拥塞（POST/GET 偶发挂起、详情拉取失败呈现存根态），复现时以「强制重选（full）重拉详情 / 重试请求」恢复；所有结论以最终成功回包与库内形状为准。遗留：JoinTable/Intermediary 的写路径分派（/links 直写连接表）为后续增强。
