# cmx-meta-data · DCT/DOC/FLC 专业定义设计器 — 交付报告

> 日期：2026-08-25 · 服务：cmx-meta-server（:8096，独立 workspace `presentation/cmx-meta-data`）
> 目标：在 cmx-meta-data 上补齐 DCT/DOC/FLC 三种元数据的**定义界面**，易用性/合理性不低于原 cmx-model，界面**专业·科技·智能·精致**。

## 决策（用户确认）
1. **三个专属设计器**（非统一工作台多形态）：`meta.dct.designer` / `meta.doc.designer` / `meta.flc.designer`；保留 `meta.entity.workbench` 作快速/高级入口。
2. **手搓 DOM + `--dg-*` 令牌**（非 UI5 WC）：语义令牌锚 UI5 `--sap*` + `color-mix` 科技微光，light/dark 自动跟随门户主题；零构建、零运行时依赖。
3. **DCT→DOC→FLC 分批**，每批独立真机验收。

## 交付物

### 共享地基 `meta._kit`（`web/ui-native/meta/_theme.js`，21KB）
- **主题令牌** `META_TOKENS`：`--dg-*`（fg/muted/surface/accent/glow/ok/warn/danger…）逐个锚 `--sap*` + hex 兜底 + `color-scheme:light dark`。**严禁裸 hex**——全部随主题翻。
- **无框架组件工厂**：`designerRoot/el/btn/input/select/checkbox/fieldRow/sectionHead/badge/tabBar/modal/toast/api`。
- **共享字段网格** `fieldGrid`：语义类型（20 类）驱动物理类型（13 类）+ 组件推导；行增删/上下移/复制；长度/精度/标度/可空/角色/显示名键。DCT/DOC/FLC 三设计器复用。
- 载入机制：门户 native 加载器用 `import(blobURL)`（相对 import 不解析），故套件注册为页面 `meta._kit`，设计器运行时 fetch 源码→blob→import（自包含顶层）。

### B1 · DCT 数据字典设计器 `meta.dct.designer`（26KB）
四区工作台 + 对标原 portal-definition-manager 的 DCT 能力：
- **子类型**（映射 RelationKind，替代旧字典三工作台）：平级 / 自分级(SelfHierarchy) / 带分类(Classification) / 关系(ManyToMany)，新建卡片选型即预置 identity+relation+特征字段；切换子类型智能增删 parent_id/category_id。
- **字段网格**：语义类型下拉驱动物理类型+组件（选"金额"自动 numeric+money-input）；「语义智能填充」批量推导。
- **主键/索引面板**、**编号规则**（模式/前缀/补零 + 实时示例预览）、**版本/状态徽标**、**Schema 源直编**（双向）、保存(422 违规内联)/部署(mr_*)/缺译。

### B2 · DOC 业务单据设计器 `meta.doc.designer`（21KB）
主子多层 + 对标 DOC 能力：
- **层级 tab**（主表 head + N 明细层，带字段计数徽标）：加/删明细层自动建主子 composition 关系 + upper_id。
- **每层字段网格**（复用套件）+ 层属性（物理表名/层显示名键/父外键列）。
- **聚合上卷**（源层→函数 sum/avg/min/max/count→目标层，from/to 层校验）、**生命周期状态机**（状态 + 转换，token ASCII、显示 labelKey）、**校验约束**（作用层 + 可求值 expr + 消息键）。
- 版本/部署（mx_ 多表）/缺译/Schema 源。

### B3 · FLC 弹性组合设计器 `meta.flc.designer`（19KB） + 后端强模型
- **后端强模型**（新 `crates/cmx-meta-model/src/composition.rs`）：`Composition{targetEntity, anchorDimensions[], dimensions[], rules[], tags[]}`，`CompositionRule{key, panel, when, fieldSets[], formula}`，`FieldSet{key, fields[]}`，`Dimension{key, labelKey, dictCode}`。`EntityType.composition` 由弱类型 `Option<Value>` 升为 `Option<Composition>`（serde default 保向后兼容）；`validate()` 加锚点存在性/键唯一/字段集非空校验。
- **两新端点**：`POST /meta/composition/validate`（结构校验）、`POST /meta/composition/preview`（给情境维度取值 → 解出命中规则 + 展开列集，when 支持等值合取 `&&` + 空兜底）。
- **设计器**：目标实体绑定 + 维度网格 + 锚点勾选 + **嵌套 tab**（规则面板 → 规则 → 字段集，对标原 portal-flexible-combination-manager）+ 命中条件(when)/公式 + **情境预览**（填维度值→解列集表）+ 校验/缺译/Schema 源。

## 真机验证

### 后端 E2E（直连 :8096）
- **DCT**：自分级字典 region save→deploy→`mr_region`（bigint id/parent_id，varchar code/name）✓
- **DOC**：双层 purchase_order save→deploy→`mx_purchase_order`+`mx_purchase_order_items`；money→numeric(18,2) 精度保真；聚合 from/to 层校验通过 ✓
- **FLC**：pricing_context save（强模型）→ validate（valid, 0 违规）→ preview `channel=online` 命中 online+fallback 展开 3 列 / `channel=store` 仅 fallback 展开 1 列（when 判别正确）✓

### 前端 CDP（Playwright + Chrome，注入 Horizon 明暗 `--sap*`）
- **DCT 10/10**：挂载 + 令牌翻转（暗 `rgb(234,236,238)` ↔ 亮 `rgb(28,37,48)`）+ 新建弹窗子类型卡片 + 字段网格 + 自分级注入 parent_id + Schema 源双向 + 无 JS 错误 + 双主题截图。
- **DOC 7/7**：挂载 + 暗色令牌 + 加明细层 tab + 聚合/状态机/composition 写入 schema + 无错误 + 截图。
- **FLC 7/7**：挂载 + 暗色令牌 + 维度 + 嵌套 tab（面板/规则/字段集）+ 命中条件 + 强模型写 schema + 无错误 + 截图。
- 合计 **24/24**；截图 `/tmp/{dct,doc,flc}-designer-*.png`（暗/亮/设计视图）确认专业 Horizon 观感。

### 编译/测试
- Rust workspace：`cargo test` 全绿；`cmx-meta-model` **5/5**（新增 2 条 composition 往返+锚点校验）。
- 三设计器 + 套件页联邦：rev 各异，字节投递正常。

## 页面清单（`web/ui-native/index.json`）
`meta._kit`（套件）· `meta.dct.designer` · `meta.doc.designer` · `meta.flc.designer` · `meta.entity.workbench`（保留）· `meta.data.maintenance` · `meta.i18n.editor`。

## 坑与取舍
- **struct-variant 语义类型**：`money`/`enum`/`foreign-key`/`quantity`/`custom` 是 serde struct variant，须 `{"money":{...}}` 而非裸串；设计器 `makeSem` 统一产出正确骨架（blankDoc 初值曾用裸 `"enum"` 已修）。
- **约束字段名**：ValidationRule 用 `expr`（非 `expression`）+ 须 `labelKey`；DOC 约束面板已对齐。
- **门户反代**：M5 `with_meta_page_proxy` 按 `meta.*` 通配拦截，新页/套件无需改门户；本轮门户未起（既有平台库 schema 漂移见 M6 报告，与本工作无关），以直连 :8096 + M5 通配证据为准。
- **清洁室不变量**：全部落 cmx-meta-data + 门户反代壳；零触碰 cmx-model crate。

## 边界与后续
- composition preview 的 when 求值目前覆盖「维度等值合取 + 空兜底」主场景；完整 FEEL 求值可后续接入（引擎接缝已留在 `when_matches`）。
- DCT 设计器保留自有字段网格（与套件 fieldGrid 等价，未强行合并以避回归）；DOC/FLC 已用套件 fieldGrid。
- 代码未提交（按惯例待确认）。
