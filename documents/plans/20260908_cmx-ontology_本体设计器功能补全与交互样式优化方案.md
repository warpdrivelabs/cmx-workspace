# 本体设计器功能补全与交互样式优化方案

> 日期：2026-09-08（v3，经两轮共三视角对抗性审查修订；第二轮确认阶段 1 可直接开工） ｜ 模块：cmx-ontology
> 涉及四仓（组件构建链涉及 `frontend/cmx-enterprise-portal`，其余三仓同分支 `feat/onto-designer-ux`）：
> - `frontend/cmx-ontology-graph` @ 287d36e（组件：虚线增删、撤销/重做挂钩）
> - `backend/cmx-container` @ 63af989f（onto 三页 designer/explorer/workshop + vendor）
> - `backend/cmx-ontology`（后端小改：乐观锁、删接口级联；从 main 新建同名分支）
> - `frontend/cmx-enterprise-portal`（W0：cmx-data-comp 子集 bundle 构建脚本；从 main 新建同名分支）
> 状态：定稿待用户确认开工

## 一、背景与问题

用户对本体设计工作台的三条核心抱怨：**样式丑、交互不友好、上手难度高**；且组件能力（接口实现虚线增删、撤销/重做等）未在宿主接通，功能不完整。调研结论（file:line 证据见附录 A）：

**功能不完整**
- 接口 / 共享属性 Inspector 是占位文案「待补」（designer.js:358）；接口建后不自动选中、不可编辑、不可删。
- 对象实现接口（implements）没有任何编辑入口——后端 `POST /object-types` 全量 upsert 通路现成，纯前端缺 UI。
- 画布上接口虚线**增删均不可能**：拉线落到接口锚点会错误地建「指向接口的实线关系」；Delete 删虚线是空操作且提示误报「已删除关系」（OntologyModel.ts:179 delLink 保护派生边）。
- 组件已有的撤销/重做、fitView、缩放等能力宿主**全部未接线**；组件空态文案承诺「双击画布新建」但宿主没实现。
- explorer 搜索框是摆设（designer.js:275 无监听）；脏标永不点亮、恒显「已同步」（state.dirty 无处赋 true）；关系属性映射（linkProps）仅会话内存、刷新即丢。
- 删除确认覆盖不全：属性行/子属性裸删；`window.prompt` ×5、`window.confirm` ×1 与自建对话框混用。

**交互不友好**
- 关系速建气泡固定 top:56px 居中，不跟随拉线落点；无 Esc、无点外关闭、无必填标记。
- 反馈通道单一：自研 toast 成功/错误共用（3.2s 消失），错误截断、无复制、无重试；保存/删除期间按钮不禁用。
- 加载 N+1 串行（逐对象拉详情），只有一行「加载中…」。
- 快捷键（Delete/Ctrl+Z/Y）只在画布聚焦后生效且无说明；按钮普遍无 title。

**样式丑 / 主题违规（工作区硬红线）**
- 壳 token fallback 全暗色、vendor 组件 fallback 全亮色：独立 :8097 下**壳暗图亮割裂**；接门户亮主题后壳内纯硬编码色不跟随。
- 语义色硬编码 `--o-ok:#22c55e / --o-err:#ef4444`；裸 rgba 约 18 处；`--o-accent2` 从未定义。
- 红线组件违规：手搓模态 `.o-dlg`、prompt/confirm；圆角 6~14px 六种混用；三页样式各写一份。

## 二、目标与非目标

**目标**
1. **功能做完整**：接口/共享属性 Inspector 落地、implements 画布+Inspector 双通路管理（**含落库闭环与缓冲一致性**）、虚线增删、撤销/重做/fitView 接线、搜索可用、脏标真实、关系属性映射落库。
2. **交互友好**：统一对话框体系（prompt/confirm 清零）、气泡跟随落点+键盘可用、删除确认分级、加载进度+可重试、反馈走 cmx 通道（子集）、快捷键可发现。
3. **样式合规好看**：双主题通路合规（亮暗一致、零裸 rgba、`--sap*`+`--neo-*` 派生）、可迁移红线组件清零+其余显式豁免、三页视觉统一。
4. **上手容易**：帮助面板、空态引导真实可用（含一键载入示例本体）、术语悬停解释、新建流程带校验与建议。

**非目标**
- 不动四区宿主 `cmx-native-pages-host` 装配机制；保持 native page 单文件、无构建、`export default {views}` 契约。
- 后端**不加新端点**、不改表结构；既有 8 处 DELETE 端点保持原样——**唯一行为级豁免见 B1**（删接口级联清 implements，理由：消灭悬空引用，属缺陷修复）。
- 不引入 UI5 runtime 到独立壳（评估结论：@ui5/webcomponents 独立引导需 theme assets 托管，成本远超收益，见 W0）；因此 **cmx-data-comp 仅迁移零 UI5 依赖子集**，依赖 UI5 的组件（cmx-floating-dialog / cmx-dict-select / cmx-combo-box）本期豁免并记 backlog（待其提供零 UI5 依赖版本后迁移）。豁免清单见 S2，验收按豁免口径执行。
- 不引入 i18n 框架；不做画布键盘可达（方向键选卡/键盘拉线）——**显式记入 backlog**，帮助面板不得暗示键盘全覆盖（本期键盘 = Delete / Ctrl+Z / Ctrl+Y / Esc / Enter / `/` / F1）。
- explorer.js / workshop.js 仅样式对齐与红线清理。
- 画布框选、多选、协作编辑、版本 diff 视图——backlog。

## 三、方案设计

### 3.0 前置工作项 W0：onto 双端组件底座（新建构建链，非登记产物）

**事实**（第二轮审查查证）：`packages/cmx-data-comp` 无构建产物——`package.json` 无 build 脚本、`main` 直指源码；barrel 静态引入 revo-grid / tabulator / web-treeview / ignite / fx-editor 全家桶；`cmx-floating-dialog`、`cmx-dict-select` 硬依赖 `@ui5/webcomponents`（独立引导还需运行时 theme assets）。`globalThis.__cmxDataComp` 仅门户注入，独立 :8097 拿不到。

**方案**：在 `frontend/cmx-enterprise-portal` 新增 esbuild bundle 脚本（如 `scripts/bundle-datacomp-subset.mjs`），产出一个**零 UI5 依赖子集** IIFE 到 `backend/cmx-container/assets/onto/web/ui-native/vendor/cmx-datacomp-subset.js`（同 vendor 纪律：构建产物不手改，来源注释+版本号+md5）。子集清单（已核实零外部依赖）：

| 能力 | 组件/函数 | 用途 |
|---|---|---|
| 轻提示 | `showCmxToast`（四级、叠放、主题自适应） | D10 反馈通道 |
| 工具条 | `cmx-toolbar` | S2 工具栏迁移 |
| 状态标签 | `cmx-status-tag` | 状态/脏标展示 |
| KPI 磁贴 | `cmx-kpi-card` | 顶部统计 |
| 键值描述 | `cmx-desc-list` | 对象/接口摘要 |

onto 三页经既有通路（`/api/native-pages/portal.onto.<id>` 登记 `onto/index.json` → fetch → Blob → `import()`）按需引导，封装为共享的 `ensureDataComp()`。

**豁免登记**（随本方案过评审即生效）：原生 `<button>`/`<select>` 保留（S1/S3 token 化重绘统一视觉）；对话框走自研 `openDialog` 升级（D7）；理由=双端可用性优先 + 目标组件存在 UI5 硬依赖；backlog 记录迁移条件。验收第 4 条按豁免口径执行（见 §六）。

**W0 完成判据**：独立 :8097 下 `ensureDataComp()` 引导成功、五个组件渲染与主题正常（无门户变量时 light fallback 生效）、bundle 体积记录在案（预期百 KB 级，若超 500KB 需回到本方案裁剪子集）。

### 3.1 组件层（frontend/cmx-ontology-graph）—— 虚线增删闭环 + 宿主挂钩

| # | 改动 | 细节 |
|---|---|---|
| C1 | 拉线到接口 = 建实现 | `requestConnect` 判两端 kind：对象↔接口 → `setImplements(obj, iface, true)`（幂等，hint「已实现接口 X」）；接口↔接口 → hint 拒绝「实现边只能连接对象类型与接口」；**任一端为接口时显式忽略属性锚点**（对象端口恒带 `data-prop`、接口四端口没有——svg.ts:103-104 vs 201-204 已核实）；重复实现不产生 def 变更（emitSpecChange 变更检测天然不污染撤销栈）。组件只改 def 并 emit，**落库职责在宿主（见 D6）** |
| C2 | Delete 虚线 = 摘实现 | 元素 `delLink` 先查边：`isInterfaceLink` → `model.setImplements(source, target, false)`（implements 单一真源不变）；键盘提示区分「已移除实现 X / 已删除关系 X」。落库职责同 C1 在宿主 |
| C3 | addLink 防御 | `model.addLink` 拒绝任一端为接口节点（返回原因文案），杜绝「指向接口的实线关系」 |
| C4 | 新增元素 API | `setImplements(obj, iface, on)`；`canUndo()/canRedo()`；`contentToScreen(x,y)`（`transform-origin:0 0` + makeViewTransform.contentToClient 为 toSvgPoint 严格逆，已核实可行） |
| C5 | 双击空白建点 | 画布空白双击 → emit `canvas-dblclick`（不直接建数据，交宿主）；空态文案与实际能力对齐 |
| C6 | 事件 detail 增强 | ①`link-add` detail 附拉线落点屏幕坐标：需把 `onConnect` 回调签名扩为可透传 pointerup 的 clientX/clientY（pointer.ts:26,288 签名改动，element 层透传，约半小时改动量）+ 源锚点内容坐标；②`edge-select` detail 已带完整 edge 对象（isInterfaceLink 直接判，宿主不得靠 apiName 字符串约定）；③新增 `history-change` 事件：**undo/redo/变更入栈/resetHistory（setSpec/首挂）四处都发**，detail 带 canUndo/canRedo，供宿主工具栏禁用态（漏 resetHistory 则保存后按钮态失真） |
| C7 | 质量门 | vitest +3（addLink 拒绝接口端点；setImplements 元素 API；delLink 虚线转摘实现）；demo 自检 +4（拉线到接口建虚线→Ctrl+Z 撤销；接口↔接口拒绝提示；选虚线 Delete→implements 同步→Ctrl+Z 恢复；双击空白发事件）；`build.sh` + `sync-component.sh` + vendor md5 双侧对账 |

### 3.2 designer.js 功能补全

| # | 改动 | 细节 |
|---|---|---|
| D1 | **接口 Inspector**（替换占位） | displayName/status 编辑；extends 管理；properties（共享属性引用选择）；**实现者清单**（逐个「移除实现」）；删除接口：影响面提示（实现者数），前端先逐对象摘实现再 DELETE（与 B1 双保险）；建接口后自动选中 |
| D2 | **对象 Inspector「实现的接口」区** | 接口标签管理（增=从清单选/删=点 ✕），随「保存对象」全量 POST；保存带 B0 乐观锁（读到的 version 随请求上送，409 特化文案见 D10） |
| D3 | **共享属性 Inspector + 管理入口** | 编辑/删除（影响面：被多少对象属性 `sharedProperty` 引用）；explorer 新建条补「+ 共享属性」 |
| D4 | **画布工具条升级 + 保存后画布局部回写** | 工具条：撤销/重做（禁用态订阅 C6 `history-change`）、fitView、放大/缩小、帮助（F1/?）。**替换清单（7 处 setSpec 改模型级局部回写，保撤销历史）**：保存对象→`setProperties`+`setNodeMeta`（displayName/status/DAM/implements）；新建对象/接口→`addObjectType`/`addInterface`；删关系→`delLink`；删对象→`delNode`；废弃→`setNodeMeta(status)`（designer.js:1273,1151,1158,1288,1361,1371,1375 逐处替换）。**全量 setSpec 仅保留**：初次加载 / 手动刷新 / 发布后（此时清撤销历史合理） |
| D5 | **搜索框生效** | explorer 树+平铺组实时过滤（apiName+displayName 包含匹配）；`/` 聚焦 |
| D6 | **spec-change 分级脏标 + implements 自动落库**（关键闭环） | ①**diff 基线 = 上一条 spec-change**；仅 `_layout/_edgeRoutes/_groupCollapsed` 变 →「画布已调整 · 视图级」（视图级落 localStorage，键=本体 apiName，setSpec 前并入 def 注入；undo 不跨持久层，以最后一次 spec-change 为准）；②implements 有变 → **数据级**：防抖 800ms 自动「re-GET → 仅改 implements → POST /object-types（带 version 走 B0）」；**diff 后 implements 无差（如防抖窗口内撤销抵消）即取消挂起落库**；③落库成功且变更对象==当前选中对象 → **硬规则：同步 `state.detail.version` 并把新 implements 合并进 `state.detail.implements`**（防 D2 保存带旧 version 必 409、或全量 upsert 用旧 implements 静默回滚刚建的实现边）；④**对象保存串行队列**：同一对象的 D6 自动落库与「保存对象」手动保存互斥排队，保存中对方禁用；⑤失败降级「未保存的模型修改」+重试 + `beforeunload` 拦截 |
| D7 | **统一对话框体系**（归属阶段 2b；W0 豁免项，走自研增强） | `openDialog` 升级：Esc 关闭、焦点圈+关闭后焦点归还触发按钮、Enter 确认、severity 图标、危险操作红按钮；5 处 `window.prompt` → 「新建元素」对话框（apiName+displayName 双字段、即时格式校验+建议名、kind 切换）；`window.confirm` ×1 收编 |
| D8 | **删除确认分级** | **缓冲态**（Inspector 未保存的属性行/子属性/标签）删除**不确认**——脏标+放弃编辑兜底；**已持久化且不可逆**的操作才确认（删对象=影响面三选、删接口/关系类型/函数/动作/共享属性=确认+影响面）；画布数据级删除（虚线）撤销语义**统一走 D6**（撤销引发的 implements 变化由 D6 自动再落库），不另设补偿通路；「被 N 个关系映射引用」提示仅对 backing 已登记数据展示，存量显示「存量关系未登记映射」 |
| D9 | **关系速建气泡增强** | 跟随拉线落点（C6 屏幕坐标直用，宿主视口矩形防出界钳制）；Esc/点外关闭；必填星标+apiName 即时校验；自关联层级预填保留 |
| D10 | **反馈通道** | toast → `showCmxToast`（W0 子集；**409 冲突特化文案**「定义已被他人修改，请刷新后重试」）；长错误/影响面明细 → 对话框展开+复制（自研，W0 豁免口径）；加载：manifest 后对象详情分批并行（批 6）+ 顶部细进度条 + 失败项列名重试；保存/删除按钮 loading 禁用 |
| D11 | **帮助与引导** | 帮助面板：鼠标操作、本期键盘真集（不暗示键盘全覆盖）、概念卡片（对象/接口/实现虚线/关系实线/DAM/动作/函数 各一句人话）；空态引导接通双击画布 + **「载入示例本体」按钮**（走既有 import 通路）；术语 title 解释 |
| D12 | **关系属性映射落库** | `LinkTypeDef.backing` jsonb 唯一口径：`{"fk":{"sourceProperty":"...","targetProperty":"..."}}`——前端常量 `LINK_BACKING_FK='fk'` 单点定义，后端 B2 注释互指；速建气泡收集值随 `POST /link-types` 持久化，关系 Inspector 回显编辑（backing 为 serde_json::Value 原样存取，round-trip 已核实） |
| D13 | **实现边选中面板** | edge-select 且 `detail.edge.isInterfaceLink` → 专用小面板：「X 实现了 Y」+「移除实现」+「查看接口」跳转；不再掉进关系 Inspector 404 空壳 |

### 3.3 后端小改（backend/cmx-ontology，无新端点、无 DDL）

| # | 改动 | 细节 |
|---|---|---|
| B0 | **乐观锁（最高优先；原子化口径）** | `save_object_type`：**更新路径用单条条件 UPDATE**（`... WHERE api_name=$1 AND version=$n`，按 rowcount 判冲突返回 409 业务码；或事务内 `SELECT ... FOR UPDATE`——复用 B1 同一事务机制），**禁止 handler 内裸 SELECT+UPSERT 两步（TOCTOU）**；更新成功服务端置 `version = 旧 + 1` 回带响应，前端以响应刷新基线。version=0/缺省（新建）跳过校验。**行为变更声明**：现行 designer 保存本就携带 GET 读到的 version——B0 上线后跨标签页/久置缓冲的保存将开始收到 409，这是预期改进；`deprecateObjectType`（GET→改→POST 即时串行）不受影响、`quickCreateObject`（无 version）跳过、import 直调 store 不经校验面——三类调用方已逐一核对 |
| B1 | 删接口级联清 implements（非目标唯一豁免） | `delete_interface` 改走事务上下文（先例 object_store.rs:241；store exec 助手不支持多语句）：同事务 `DELETE om_interface` + `UPDATE om_object_type SET implements = implements - $1::text WHERE implements ? $1`（`-` 重载需显式 `::text`，冒烟验证）。版本快照表不动 |
| B2 | linkProps 服务端防御 | `save_link_type` 对 backing.fk 的 sourceProperty/targetProperty 做存在性检查，缺失记**服务端日志**（不拒绝、不新增响应通道——校验主体在前端，B2 仅留痕） |
| 质量门 | `cargo check` + :8097 API 冒烟：①同 version 保存必成功、跨 version 必 409 且 version 自增回带 ②建接口→被实现→删接口→对象 implements 已清 ③backing fk 存取回读 |

### 3.4 样式重构（designer.js 为主，explorer/workshop 同步）

| # | 改动 | 细节 |
|---|---|---|
| S1 | **token 层重写** | 三页统一同源 token 块：`--o-*` 全量重映射 `var(--sap*, light 兜底)`（fallback 一律 light，与 vendor 组件同向；`--neo-*` 同样带 light 兜底）；语义色接 `--sapPositiveColor/--sapNegativeColor/--sapCriticalColor`；品牌强调接 `--neo-cyan/--neo-violet`（只引用不重定义）；补 `--o-accent2`；全部裸 rgba → `color-mix(in srgb, var(--sap*/--neo-*) X%, transparent)`；字体接 `--sapFontFamily` |
| S2 | **组件迁移（收缩为 W0 子集）+ 显式豁免清单** | **迁移**：工具栏 → `cmx-toolbar`；状态/脏标 → `cmx-status-tag`；统计磁贴 → `cmx-kpi-card`；对象摘要 → `cmx-desc-list`；toast → `showCmxToast`。**豁免**（双端可用性，backlog 待组件零 UI5 依赖版）：按钮/下拉保留原生（token 化重绘）；`.o-dlg` 保留但按 D7 升级能力。cmx 组件**一律不写 `data-cmx-skin`**（默认即 Neo），不本地重定义 `--neo-*` 数值 |
| S3 | **视觉体系** | 间距 scale（4/8/12/16，区块 gap 10）；圆角三档（容器 9/卡片 8/按钮输入 7/标签 5）；字号四档（页题/区块头/正文/辅助）；树/Inspector/工具栏密度统一；焦点环 `--sapContent_FocusColor` |
| S4 | **token 同源策略** | native 页不能相对 import：三页各自内嵌同一份 token 块，块头 `/* onto-ui-tokens v1 (同 explorer.js/workshop.js，改一处须三处同步) */`；阶段 5 grep 比对三页一致性 |
| S5 | **主题验证矩阵（5 格）** | ①独立 :8097（无门户 `--sap*`/`--neo-*`/`__cmxDefault*Skin`，验 light fallback 全链路）②门户 UI5 亮 ③门户 UI5 暗 ④门户内 cmx 组件 `data-cmx-skin-tone` 切换（cyan/mint 各一）⑤`data-cmx-skin="plain"` 逃生对照。亮暗均无割裂/低对比，截图存档 |

### 3.5 明确不做 / 保持原样

- 既有 DELETE 端点形态不改造（B1 只改 delete_interface 的**行为缺陷**）；`/api/domains/tree` 门户依赖保持既有降级。
- 画布键盘可达、框选、多选、协作、版本 diff——backlog。
- UI5 runtime 不进独立壳（W0 已论证）；依赖 UI5 的 cmx 组件不迁移（S2 豁免清单）。
- 不手改 vendor 产物（`cmx-ontology-graph.js` 与 `cmx-datacomp-subset.js` 均为构建产物，md5 对账）。

## 四、实施顺序与验证

| 阶段 | 内容（目标仓） | 交付/验证门 | 预估 |
|---|---|---|---|
| 0 基线+底座 | 前置：起 :8097（依赖外部 PG，`onto-server-dev.toml` 已配 db_url；`./onto.sh`，禁止 cargo build 手搓）；亮主题截图需门户同起（:5173+:8080）。三页现状截图（亮/暗）；**W0 构建链**（frontend/cmx-enterprise-portal 加 bundle 脚本 → vendor 子集 → 独立 :8097 实测）；cmx-ontology 建分支 | 截图基线 + W0 完成判据 + 体积记录 | 1-2d |
| 1 组件 | C1-C7（frontend/cmx-ontology-graph） | vitest 全绿、demo 自检 +4 全绿、md5 对账、真浏览器走查 | 1d |
| 2a Inspector 双写 | D1/D2/D3/D13 + D6 最小闭环（cmx-container） | 真机走查：接口全链路（建→拉线实现→面板移除→删接口回收）+ 落库/缓冲一致性硬规则生效 | 1.5d |
| 2b 对话框与反馈 | D4 局部回写清单、D7/D8/D9/D10/D11、D6 完整三态脏标 | prompt/confirm grep=0；气泡定位实测；toast 分通道+409 文案；7 处 setSpec 替换后撤销历史保持 | 1.5d |
| 3 后端 | B0→B1→B2（cmx-ontology） | cargo check + 冒烟三条 | 0.5d |
| 4 样式 | S1-S5：designer 先行，explorer/workshop 跟进 | 5 格主题矩阵截图 + 红线 grep（裸 rgba/纯 hex/prompt/confirm 清零；`<button`/`<select` 按豁免清单口径） | 2-3d |
| 5 验收 | 全量回归（见 §六） | 清单全绿；四仓分阶段提交 | 0.5d |

> 每阶段独立提交（子仓提交前 `git rev-parse --show-toplevel && git remote -v && git status -sb` 自报家门）；改组件必跑 build+sync+md5（vendor 纪律）。

## 五、风险与对策

| 风险 | 对策 |
|---|---|
| W0 子集 bundle 超重或个别组件有隐性门户依赖 | 完成判据兜底（体积上限 500KB + 独立引导实测）；超限则裁子集、再退全豁免（按钮/工具栏原生+token 化，已在豁免清单框架内） |
| D6 自动落库与 Inspector 缓冲互相踩 | D6 ③硬规则（同步 detail.version/implements）+ ④对象级串行队列 + B0 兜底 409 |
| 自动落库风暴（连续拖线） | 防抖 800ms + diff 基线取消机制（无差即不发）+ 失败停止自动转手动 |
| B0 上线后存量长会话保存开始 409 | 属预期改进；D10 特化文案引导刷新；前端保存前 re-GET 预检降低触发面 |
| B1 级联影响其它消费方 | 只清工作区 `om_object_type.implements`，版本快照不动；方案已声明豁免 |
| backing 语义演进 | `fk` 包装层留扩展；前后端常量/注释互指 |
| token 三处漂移 | 块头版本注释 + 阶段 5 grep 一致性比对 |
| 撤销历史与外部 setSpec 冲突 | D4 七处替换清单 + 全量 setSpec 收敛到三场景 |

## 六、验收清单

1. **虚线闭环**：拉线 对象→接口 建虚线且**落库**（刷新仍在）；接口→接口 提示拒绝；Delete 虚线 = implements 移除且落库；Ctrl+Z 撤销后由 D6 自动再落库（刷新后撤销态保持）；无「已删除」误报。
2. **Inspector 与一致性**：接口/共享属性 Inspector 完整可用；对象 Inspector implements 管理落库；实现边面板正常；B0 冒烟三条通过（同版本必成功/跨版本必 409+自增回带/409 有特化文案）；拉线落库后选中对象的缓冲 version/implements 同步（D6③）。
3. **交互**：搜索、三态脏标、撤销/重做按钮禁用态（含保存后不失真）、fitView、帮助面板、空态引导+示例本体、气泡跟随落点、Esc/点外关闭、删除确认分级、7 处 setSpec 替换后撤销历史保持——全部真实生效。
4. **红线 grep**：onto 三页 `prompt(/confirm(/alert(` = 0；裸 rgba = 0；无 var 包裹 hex = 0；`--o-accent2` 有定义；`<button`/`<select` 计数 = 豁免清单登记数（附件列出）。
5. **主题**：5 格矩阵无割裂、无低对比，截图存档。
6. **工程**：组件 vitest + demo 自检全绿、vendor md5 双侧一致（graph + datacomp-subset）；后端 cargo check + 冒烟通过；四仓 `feat/onto-designer-ux` 分阶段提交齐全。

---

## 附录 A：关键证据索引

- 接口/共享属性 Inspector 占位：designer.js:358；搜索框无监听：designer.js:275 vs bind() 998-1063；脏标恒假：designer.js:52,291；prompt 清单：873,878,1143,1148,1155；confirm：1220；气泡定位：1497；toast 通道：1378-1387,1504-1505；N+1 加载：117-119；独立壳兜底注释：designer.js:63-65；保存/删除后 setSpec 七处：1273,1151,1158,1288,1361,1371,1375。
- `__cmxDataComp` 仅门户注入：frontend/cmx-enterprise-portal/cmx-portal-manager/src/import-ui5-and-app.js:14；cmx-data-comp 无构建产物、barrel 依赖全家桶：packages/cmx-data-comp/package.json:7-13、src/index.js:9-32；floating-dialog/dict-select 硬依赖 UI5：src/components/cmx-floating-dialog.js:26-28、cmx-dict-select.js:57-63；showCmxToast 零外部依赖：src/lib/cmx-toast.js:25-26。
- 虚线派生与删除保护：frontend/cmx-ontology-graph/src/model/OntologyModel.ts:179,184-209；接口锚点无 data-prop：src/render/svg.ts:103-104,201-204；requestConnect 无接口分支：src/element/cmx-ontology-graph.ts:443-454；view 私有：element:63；undoStack 私有：element:73-74；resetHistory 时机：element:188-194。
- 后端：对象类型 upsert handlers.rs:41-51（无 version 校验）、store.rs:198-226（version 客户端回写）；Error::conflict 409 现成：cmx-container/crates/libs/cmx-apis/cmx-api-types/src/error.rs:228；implements 列 ddl.rs:20；删接口不清引用 store.rs:459-465；backing 原样存取 def.rs:251/store.rs:336,366；事务先例 object_store.rs:241；save_link_type 响应无 warning 通道 handlers.rs:94-103；import 直调 store：import_handlers.rs:21,48；onto-server-dev.toml:11-16（外部 PG db_url）。
- 样式债务：designer.js:1391（token fallback 暗色 + 语义色硬编码 + accent2 未定义）、1439/1468-1523（裸 rgba）；vendor 亮色 fallback：assets/onto/web/ui-native/vendor/cmx-ontology-graph.js:1051-1066。
- 规范真源：技能 cmx-components-guide references/{page-style-guide,neo-theme-onboarding,frontend-conventions}.md。

## 附录 B：审查记录

- 第一轮（双视角并行）：工程可行性+事实核查、规范合规+UX 完备性。产出阻塞 4 条（画布落库缺失、双端组件前提失实、backing 口径矛盾、乐观锁假安全）、重要 9 条——全部吸收进 v2/v3。
- 第二轮（修订一致性+可实施性）：确认 backing③ 彻底解决、阶段 1 可直接开工；新增阻塞 3 条（W0 前提失实需新建构建链+第 4 仓、D6×Inspector 缓冲踩踏硬规则、B0 原子化口径）、重要 2 条（D4 七处 setSpec 替换清单、D6 diff 基线定义）——已全部吸收进 v3。
