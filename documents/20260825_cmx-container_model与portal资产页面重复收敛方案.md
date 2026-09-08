# model 与 portal 资产页面重复收敛方案

> 日期：2026-08-25 · 状态：**已实施（方案 B，2026-08-25 拍板）** · 范围：`cmx-container/assets/model/web` ↔ `cmx-container/assets/portal/data`

## 一、背景

`assets/model/web`（模型中心 web 资产）与 `assets/portal/data`（门户资产）存在大面积页面重复：
同一页面两边各存一份、id 命名空间不同（model 侧 `portal.model.*`，portal 侧 `portal.*` / `fi.cmxfico.*` / `fi.gl.*` / `definition.*`），
经 `publish-assets.sh` 分别发布到 cmx-model（:8093）与 cmx-portalservice（:8080）两个服务对外自暴，
门户按属主路由（`owner_service_of` / F3a 页面反代）对 `portal.model.*` 取页委托模型中心——**双份同时在线服务**。

## 二、梳理方法

- native 页：`model/web/ui-native/index.json`（10 页）× `portal/data/native-pages/index.json`（28 页）
- html 页：`model/web/ui-html/index/*.pages.json`（81 条）× `portal/data/html-pages/index/*.pages.json`（活 81 + _legacy 30）
- 配对规则：name + relPath 完全一致视为同一页面；逐字节 filecmp 比对源码
- 引用普查：`model/data/menu-pages`（gl/report/mdm/flow 四菜单）+ `portal/data/modules` + `portal/data/service-catalog`

## 三、梳理结果

### 3.1 总账

| 类别 | model 侧 | portal 侧 | 配对结果 |
| --- | --- | --- | --- |
| native 页 | 10 | 28 | **10 对全部逐字节一致**；portal 独有 18 页（帮助/通知/任务监控/注册表/服务拓扑/展示组件库/demo×11） |
| html 页 | 81 | 81（活）+30（_legacy） | **81 对全部配对**：76 逐字节一致、1 对仅页内跳转引用命名空间不同（voucher-list）、4 对双边死条目（rpt-ws-*，两侧索引有条目但源文件都不存在） |

model 侧 web 资产**没有任何独占页面**（native 独占 0、html 独占 0）——它是 portal 侧的完整镜像。

### 3.2 唯一的"分叉"：voucher-list

- model 版（8/24，11907B）与 portal 版（8/3，11905B）唯一差异：`openDetail` 页内跳转引用——model 版跳 `portal.model.gl.voucher-detail`，portal 版跳 `fi.cmxfico.gl.voucher-detail`
- 属命名空间自我一致，**无功能差异**；收敛后以 portal 版为准即可

### 3.3 页面内部跨页引用

- model 侧 html 仅 **1 个文件**含 `portal.model.*` 内部引用（voucher-list → voucher-detail）
- portal 侧自引用已是 `fi.cmxfico.gl.*`，收敛后无需再改

### 3.4 引用现状（决定改名方向的关键）

| 引用目标 | 处数 | 位置 |
| --- | --- | --- |
| `portal.model.*`（model 侧 id） | **81** | gl 菜单 80 处 + mdm 菜单 1 处（`portal.model.dct.data-editor`） |
| portal 侧对应 id（`portal.datasource.cluster` 等） | **0** | 无 |

即：**当前所有活引用都指向 model 侧 id**，portal 侧副本是"零引用的影子库"。

## 四、已定决策（2026-08-25 用户拍板）

1. **集群数据源浏览**：portal 侧保留，model 侧删除
2. **DAM 注册管理中心**：portal 侧保留，model 侧删除（gl 菜单 3 处引用改 `portal.dam.registry-center`）
3. **总方向 = 方案 B（按属主拆分）**：模型域 6 页保留 model 侧、引用零改动，其余 ~85 对归门户（见 5.1 与第六节实施结果）
4. **可选两页随大流**：`meta-model-service-test` / `dict-grid-meta`（元数据驱动演示页）随业务页归 portal

## 五、建议方案（待确认）

**方案 A（未被采纳）：model 侧 `web/` 整棵删除，页面统一归门户；81 处引用按映射表改名到 portal id。**
模型中心回归纯元数据服务（`assets/model/data` 的 menu-pages / meta 定义不动），不再持有 web 页面。

分类处理：

| 类别 | 内容 | 处理 |
| --- | --- | --- |
| 平台工具 native×5 | 字典基础元数据×2、通用单据加载页、加载服务自检、通用字典数据维护 | 同 dam/datasource：删 model 侧，引用改 portal id |
| 业务页面 html×76 + native 凭证×3 | 凭证/交易/差旅/三区工作台/字典维护全系 | portal 侧全有逐字节镜像，删 model 侧，引用改名 |
| voucher-list | 唯一分叉项 | 以 portal 版为准（无功能损失），删 model 版 |
| rpt-ws-* 死条目×4 | 双边索引条目、源文件皆无 | 双边索引条目都删 |
| `_legacy` 30 页 | portal 侧旧页 | 待确认（见第八节） |

### 5.1 方案 B：按属主拆分（✅ 2026-08-25 拍板采纳，源于用户质询）

方案 A 对"模型域页面"一刀切归门户值得商榷——字典/单据**元数据**维护本就是模型中心自身功能，
且 F3-save 架构本意即"业务域页真源在各服务 assets 工作区"（cmx-common-api pages.rs 注释原文）：
report / flow / rules 的 `portal.rpt.*` / `portal.flow.*` / `portal.rules.*` 均由各引擎服务自持自暴，
模型域页面没有理由例外。mdm 菜单亦以 `portal.model.dct.data-editor` 作主数据维护入口。

**方案 B：真正模型域的 6 页反向保留 model 侧（portal 侧删副本、引用零改动），其余仍按方案 A 归门户。**

| 模型域页面 | model 侧 id（留） | 引用现状 | 处理 |
| --- | --- | --- | --- |
| 字典基础元数据 | `portal.model.definition.base-dct` | 0 处（在库未引用） | model 留 / portal 删副本 |
| 字典基础元数据(native_pages) | `portal.model.definition.base-dct-native` | gl 菜单 4 处 | 同上，引用不改 |
| 通用业务单据加载页 | `portal.model.doc.doc-loader` | gl 菜单 3 处 | 同上 |
| 业务单据加载服务自检 | `portal.model.doc.doc-service-test` | gl 菜单 1 处 | 同上 |
| 通用字典数据维护 | `portal.model.dct.data-editor` | gl 菜单 1 + mdm 菜单 1 | 同上 |
| 字典数据维护(HTML) | `portal.model.gl.dct-data-editor-html` | gl 菜单 1 处 | 同上 |

- 可选同向归模型域：`portal.model.gl.meta-model-service-test`（元数据模型服务测试）、
  `portal.model.gl.dict-grid-meta`（数据字典动态表格）——元数据驱动演示/测试页，两可。
- 引用账（方案 B vs 方案 A）：gl 菜单 80 处中 10 处模型域引用**零改动**，改名 70 处；mdm 菜单 1 处零改动。
- 代价：model/web 不能整树删除（保留 6~8 页 + 索引同步收缩），`portal.model.*` F3a 谓词与
  `owner_service_of` 分支须长期保留。
- 收益：符合属主架构（与 report/flow/rules 一致）；模型中心 UI 随自身演进，不与门户发布耦合；
  mdm / gl 菜单对通用元数据页的引用不动。

**注意区分**：81 对主体（~60 对）是 fi.cmxfico.gl 的**业务字典数据维护工作台**（dictws 合并组织机构 /
dictflat 币种 / dicttree 总账科目 / dictcls 合作伙伴 / dictrel 核算分组 / glacct / acctws 等）——它们
消费模型中心服务，但页面是报账 GL 业务 UI（portal 侧 id 即 `fi.cmxfico.gl.*`），不属模型域，两方案下均归门户。

## 六、实施结果（2026-08-25 已执行，方案 B）

| # | 动作 | 结果 |
| --- | --- | --- |
| 1 | model ui-native 收缩 | 索引 10→5（删 datasource.cluster / dam.registry-center / voucher-native×3），源文件与空目录同步清理 |
| 2 | model ui-html 收缩 | 81→1（仅留 `portal.model.gl.dct-data-editor-html`）；cr 域整删，manifest 收缩为 `["fi"]`；另清 5 个索引外游离文件（gl-voucher-demo×2、voucher-doc-sqlxbin、_restore-fico-skin×2） |
| 3 | portal native 去重 | 28→23（删模型域 5 页副本：portal.definition.base-dct / definition.base-dct-native / portal.doc.doc-loader / portal.doc.doc-service-test / portal.dct.data-editor） |
| 4 | portal html 去重 | fi 分片 80→75（删 dct-data-editor-html 副本 + rpt-ws×4 死条目）；pages-list.json 124→119 |
| 5 | gl 菜单改名 | 70 处 `portal.model.*` → portal id（含 DAM 3 处 → `portal.dam.registry-center`）；模型域 10 处零改动；voucher-list 分叉以 portal 版为准（model 版随整批删除） |
| 6 | mdm 菜单 | 未动（`portal.model.dct.data-editor` 引用保留） |
| 7 | 前端唯一消费者 | `../cmx-portal-manager` "字典数据"快捷入口改指 `portal.model.dct.data-editor` |
| 8 | 代码注释 | `cmx-model-proxy/proxy.rs` `is_model_owned_page` 文档示例由已删的 dictcls-explorer 换成 dct-data-editor-html（`cargo check -p cmx-model-proxy` 通过） |
| 9 | cmx_menu 同步 | sync_menu_db.py 重同步 gl 菜单 66 节点；库内核验：旧业务引用 0 残留、模型域引用 11 处（gl 10 + mdm 1）分布正确（base-dct-native-pages-manager×4 / voucher-native 三节点×doc-loader×3 / doc-service-test / gl-dict-data-editor / gl-dict-data-editor-html / mdm-dict-data-editor）、DAM 3 处已指 portal |

**校验**：11 个 JSON 全部可解析；gl 菜单 108 处页面引用全部可解析（含 v1 pages-list 页面）；95 个已删 id 在菜单 / portal modules / service-catalog / crates / 前端源码中零残留（前后词边界精确匹配）。

**生效条件**：门户 jsonstore 带 moka 进程内缓存，需重启 `cmx-portal-server` 后索引变更生效；cmx-model 引擎 loader 逐请求读盘即时生效。cmx-model 服务仓远端 `web/` 仍是旧全量，下次 `publish-assets.sh` 发布自然收缩。

## 七、影响与风险（按方案 B 实施后）

- 业务页面（gl 菜单 70 处引用）改走门户同源（:8080 本地 jsonstore），打开不再依赖 cmx-model 在线；模型域 11 处引用仍走 F3a 反代到 cmx-model（:8093），属主架构完整保留
- cmx-model 仅自暴 6 页；`portal.model.*` 谓词（`owner_service_of` / cmx-model-proxy）与 F3-save 委托链路继续生效
- cmx-model 服务仓（本地未拉取）远端 `web/` 目录残留旧全量，下次 publish 自然收缩（见第八节）
- `cmx_menu.code` 不变（菜单节点 id 未动，只改 definition 内引用）；权限 `fun_code` 关联不受影响
- 门户 moka 缓存：重启 `cmx-portal-server` 前旧索引仍在内存，重启后与新索引一致

## 八、待确认问题

1. ~~总方向~~ ✅ 已拍板方案 B 并实施完毕（见第六节）。
2. **`_legacy` 30 页**：2026-08-25 引用普查 + **拍板执行**——
   - **活跃在用 6 页（保留）**：`welcome`（门户启动页，portal-app 自动打开 + shellbar 按钮 + portal-router 内置节点）；`tabulator-treegrid-demo` / `combo-box-demo` / `cmx-input-editors-demo` / `cmx-grid-form-linkage-demo` / `demo-master-slave`（gl 菜单"开发与演示"组引用）。
   - **组件演示互链簇 11 页（保留）**：`embed_page1/2`、`inner_page1/2`、`exp_view1`、`ctn_view1/2`、`btm_view1/2`、`pro_view1` —— cmx-embed-page 组件文档示例 + 互链 + `inner_page2` 被 cr 域活页 testdlg.html 运行时引用。
   - **真死页 13 页（✅ 2026-08-25 已删除）**：`outlook-mail-explorer/content`、`my-page-test101/102/103`、`ws-shared-model`、`my-data-set`、`exp_view2`、`pro_view2`、`flt_view1`、`flt_view2`、`ignite-combo-editor-demo`、`ignite-list-demo`。执行结果：`_legacy` 分片 30→17、pages-list.json 119→106、源文件删 13；全工作区零残留引用（仅设计器单测 `normalize-server-page-html-for-debug.test.js` 用 `my-page-test101` 作字符串夹具，自构造 HTML 不取资产，不受影响——该测试文件因 cmx-ui5-runtime exports 解析问题加载失败，属先前已存在的环境问题，与本删除无关，其他设计器单测 15/15 通过）。
3. **cmx-model 服务仓远端**：本地工作区已收缩，远端 `web/` 下次 `publish-assets.sh` 发布自然同步；如需立即收缩可手动跑一次 publish。
4. ~~`portal.model.*` 谓词~~ ✅ 方案 B 下长期保留（模型域 6 页依赖该链路），`owner_service_of` / cmx-model-proxy F3a 谓词不动，注释示例已同步更新。

## 附录 A：native 页映射表（10 对）

| 页面 | model 侧 id（删） | portal 侧 id（留） | 状态 |
| --- | --- | --- | --- |
| 集群数据源浏览 | `portal.model.datasource.cluster` | `portal.datasource.cluster` | 一致 |
| 字典基础元数据 | `portal.model.definition.base-dct` | `portal.definition.base-dct` | 一致 |
| 字典基础元数据(native_pages) | `portal.model.definition.base-dct-native` | `definition.base-dct-native` | 一致 |
| DAM 注册管理中心 | `portal.model.dam.registry-center` | `portal.dam.registry-center` | 一致 |
| 会计凭证（native_pages） | `portal.model.gl.voucher-native` | `fi.cmxfico.gl.voucher-native` | 一致 |
| 会计凭证（native_pages · tokio 二进制） | `portal.model.gl.voucher-native-bin` | `fi.cmxfico.gl.voucher-native-bin` | 一致 |
| 会计凭证（native_pages · Zmc零拷贝→JSON） | `portal.model.gl.voucher-native-zmcjson` | `fi.cmxfico.gl.voucher-native-zmcjson` | 一致 |
| 通用业务单据加载页（元数据驱动） | `portal.model.doc.doc-loader` | `portal.doc.doc-loader` | 一致 |
| 业务单据加载服务·全能力自检（native_pages） | `portal.model.doc.doc-service-test` | `portal.doc.doc-service-test` | 一致 |
| 通用字典数据维护 | `portal.model.dct.data-editor` | `portal.dct.data-editor` | 一致 |

## 附录 B：html 页映射表（81 对）

**fi.cmxfico.gl 域（72 对）**

| 页面 | model 侧 id | portal 侧 id | 状态 |
| --- | --- | --- | --- |
| 财务会计凭证 | `portal.model.gl.voucher` | `fi.cmxfico.gl.voucher` | 一致 |
| 财务会计凭证（科技版） | `portal.model.gl.voucher-neo` | `fi.cmxfico.gl.voucher-neo` | 一致 |
| 交易单据 | `portal.model.gl.trade` | `fi.cmxfico.gl.trade` | 一致 |
| 交易单据（科技版） | `portal.model.gl.trade-neo` | `fi.cmxfico.gl.trade-neo` | 一致 |
| 差旅费报销（科技版） | `portal.model.gl.travel-expense-neo` | `fi.cmxfico.gl.travel-expense-neo` | 一致 |
| 科目弹性组合 | `portal.model.gl.account-def` | `fi.cmxfico.gl.account-def` | 一致 |
| 元数据模型服务测试 | `portal.model.gl.meta-model-service-test` | `fi.cmxfico.gl.meta-model-service-test` | 一致 |
| 数据字典动态表格 | `portal.model.gl.dict-grid-meta` | `fi.cmxfico.gl.dict-grid-meta` | 一致 |
| ERP凭证样例(CNPC) | `portal.model.gl.erp-voucher-cnpc` | `fi.cmxfico.gl.erp-voucher-cnpc` | 一致 |
| ERP凭证样例(CmxMasterSlave模型版) | `portal.model.gl.erp-voucher-cnpc-ms` | `fi.cmxfico.gl.erp-voucher-cnpc-ms` | 一致 |
| 交易弹性组合 | `portal.model.gl.trade-def` | `fi.cmxfico.gl.trade-def` | 一致 |
| 交易单据（表单视图） | `portal.model.gl.trade-form` | `fi.cmxfico.gl.trade-form` | 一致 |
| Ignite 组合框编辑器 | `portal.model.gl.ignite-combo-editor` | `fi.cmxfico.gl.ignite-combo-editor` | 一致 |
| Ignite 列表主从 | `portal.model.gl.ignite-list` | `fi.cmxfico.gl.ignite-list` | 一致 |
| cmx-dict-select 编辑器演示 | `portal.model.gl.dict-editor-demo` | `fi.cmxfico.gl.dict-editor-demo` | 一致 |
| 总账主数据演示 | `portal.model.gl.gl-master-data-demo` | `fi.cmxfico.gl.gl-master-data-demo` | 一致 |
| 主数据帮助测试 | `portal.model.gl.dict-help-test` | `fi.cmxfico.gl.dict-help-test` | 一致 |
| 主数据帮助实验室 | `portal.model.gl.dict-help-lab` | `fi.cmxfico.gl.dict-help-lab` | 一致 |
| CCM 全属性测试 | `portal.model.gl.ccm-attrs-test` | `fi.cmxfico.gl.ccm-attrs-test` | 一致 |
| cmx-fico三区·共享模型(隐藏) | `portal.model.gl.fico-ws-model` | `fi.cmxfico.gl.fico-ws-model` | 一致 |
| cmx-fico三区·凭证批列表(explorer) | `portal.model.gl.fico-ws-explorer` | `fi.cmxfico.gl.fico-ws-explorer` | 一致 |
| cmx-fico三区·凭证头+科目行+辅助行(content) | `portal.model.gl.fico-ws-content` | `fi.cmxfico.gl.fico-ws-content` | 一致 |
| cmx-fico三区·源数据(content) | `portal.model.gl.fico-ws-source` | `fi.cmxfico.gl.fico-ws-source` | 一致 |
| cmx-fico三区·明细(property) | `portal.model.gl.fico-ws-prop-detail` | `fi.cmxfico.gl.fico-ws-prop-detail` | 一致 |
| cmx-fico三区·扩展操作(property) | `portal.model.gl.fico-ws-prop-actions` | `fi.cmxfico.gl.fico-ws-prop-actions` | 一致 |
| cmx-fico三区·外币管理(property) | `portal.model.gl.fico-ws-prop-fx` | `fi.cmxfico.gl.fico-ws-prop-fx` | 一致 |
| cmx-fico三区·预算管理(property) | `portal.model.gl.fico-ws-prop-budget` | `fi.cmxfico.gl.fico-ws-prop-budget` | 一致 |
| 合并组织机构维护·共享模型(隐藏) | `portal.model.gl.dictws-model` | `fi.cmxfico.gl.dictws-model` | 一致 |
| 合并组织机构维护·树视图 | `portal.model.gl.dictws-explorer` | `fi.cmxfico.gl.dictws-explorer` | 一致 |
| 合并组织机构维护·节点表格 | `portal.model.gl.dictws-content` | `fi.cmxfico.gl.dictws-content` | 一致 |
| 合并组织机构维护·节点详情 | `portal.model.gl.dictws-prop-detail` | `fi.cmxfico.gl.dictws-prop-detail` | 一致 |
| 总账科目维护·共享模型(隐藏) | `portal.model.gl.glacct-model` | `fi.cmxfico.gl.glacct-model` | 一致 |
| 总账科目维护·科目树 | `portal.model.gl.glacct-explorer` | `fi.cmxfico.gl.glacct-explorer` | 一致 |
| 总账科目维护·子科目表格 | `portal.model.gl.glacct-content` | `fi.cmxfico.gl.glacct-content` | 一致 |
| 总账科目维护·科目详情 | `portal.model.gl.glacct-prop-detail` | `fi.cmxfico.gl.glacct-prop-detail` | 一致 |
| 会计核算管理·共享模型(隐藏) | `portal.model.gl.acctws-model` | `fi.cmxfico.gl.acctws-model` | 一致 |
| 会计核算管理·合并组织树 | `portal.model.gl.acctws-explorer` | `fi.cmxfico.gl.acctws-explorer` | 一致 |
| 会计核算管理·科目核算(6类型treegrid) | `portal.model.gl.acctws-content` | `fi.cmxfico.gl.acctws-content` | 一致 |
| 会计核算管理·科目详情 | `portal.model.gl.acctws-prop-detail` | `fi.cmxfico.gl.acctws-prop-detail` | 一致 |
| 会计凭证（html_pages） | `portal.model.gl.voucher-doc` | `fi.cmxfico.gl.voucher-doc` | 一致 |
| 会计凭证（html_pages · Sqlx 二进制） | `portal.model.gl.voucher-doc-sqlxbin` | `fi.cmxfico.gl.voucher-doc-sqlxbin` | 一致 |
| 会计凭证·单据列表（Sqlx 二进制） | `portal.model.gl.voucher-list` | `fi.cmxfico.gl.voucher-list` | 分叉 |
| 会计凭证·单据详情（Sqlx 二进制） | `portal.model.gl.voucher-detail` | `fi.cmxfico.gl.voucher-detail` | 一致 |
| 业务单据加载服务·全能力自检（html_pages） | `portal.model.gl.doc-service-test` | `fi.cmxfico.gl.doc-service-test` | 一致 |
| cmx-fico三区·doc服务版··共享模型(隐藏) | `portal.model.gl.fico-ws-doc-model` | `fi.cmxfico.gl.fico-ws-doc-model` | 一致 |
| cmx-fico三区·doc服务版··凭证批列表(explorer) | `portal.model.gl.fico-ws-doc-explorer` | `fi.cmxfico.gl.fico-ws-doc-explorer` | 一致 |
| cmx-fico三区·doc服务版··凭证头+科目行+辅助行(content) | `portal.model.gl.fico-ws-doc-content` | `fi.cmxfico.gl.fico-ws-doc-content` | 一致 |
| cmx-fico三区·doc服务版··源数据(content) | `portal.model.gl.fico-ws-doc-source` | `fi.cmxfico.gl.fico-ws-doc-source` | 一致 |
| cmx-fico三区·doc服务版··明细(property) | `portal.model.gl.fico-ws-doc-prop-detail` | `fi.cmxfico.gl.fico-ws-doc-prop-detail` | 一致 |
| cmx-fico三区·doc服务版··扩展操作(property) | `portal.model.gl.fico-ws-doc-prop-actions` | `fi.cmxfico.gl.fico-ws-doc-prop-actions` | 一致 |
| cmx-fico三区·doc服务版··外币管理(property) | `portal.model.gl.fico-ws-doc-prop-fx` | `fi.cmxfico.gl.fico-ws-doc-prop-fx` | 一致 |
| cmx-fico三区·doc服务版··预算管理(property) | `portal.model.gl.fico-ws-doc-prop-budget` | `fi.cmxfico.gl.fico-ws-doc-prop-budget` | 一致 |
| 员工信息 | `portal.model.gl.employee` | `fi.cmxfico.gl.employee` | 一致 |
| 销售订单录入 | `portal.model.gl.salesOrder` | `fi.cmxfico.gl.salesOrder` | 一致 |
| 币种字典维护·共享模型(隐藏) | `portal.model.gl.dictflat-model` | `fi.cmxfico.gl.dictflat-model` | 一致 |
| 币种字典维护·检索 | `portal.model.gl.dictflat-explorer` | `fi.cmxfico.gl.dictflat-explorer` | 一致 |
| 币种字典维护·列表 | `portal.model.gl.dictflat-content` | `fi.cmxfico.gl.dictflat-content` | 一致 |
| 币种字典维护·详情 | `portal.model.gl.dictflat-prop-detail` | `fi.cmxfico.gl.dictflat-prop-detail` | 一致 |
| 总账科目字典维护·共享模型(隐藏) | `portal.model.gl.dicttree-model` | `fi.cmxfico.gl.dicttree-model` | 一致 |
| 总账科目字典维护·科目树 | `portal.model.gl.dicttree-explorer` | `fi.cmxfico.gl.dicttree-explorer` | 一致 |
| 总账科目字典维护·子科目 | `portal.model.gl.dicttree-content` | `fi.cmxfico.gl.dicttree-content` | 一致 |
| 总账科目字典维护·详情 | `portal.model.gl.dicttree-prop-detail` | `fi.cmxfico.gl.dicttree-prop-detail` | 一致 |
| 合作伙伴字典维护·共享模型(隐藏) | `portal.model.gl.dictcls-model` | `fi.cmxfico.gl.dictcls-model` | 一致 |
| 合作伙伴字典维护·分类树 | `portal.model.gl.dictcls-explorer` | `fi.cmxfico.gl.dictcls-explorer` | 一致 |
| 合作伙伴字典维护·伙伴列表 | `portal.model.gl.dictcls-content` | `fi.cmxfico.gl.dictcls-content` | 一致 |
| 合作伙伴字典维护·详情 | `portal.model.gl.dictcls-prop-detail` | `fi.cmxfico.gl.dictcls-prop-detail` | 一致 |
| 核算主体分组关系维护·共享模型(隐藏) | `portal.model.gl.dictrel-model` | `fi.cmxfico.gl.dictrel-model` | 一致 |
| 核算主体分组关系维护·主分组树 | `portal.model.gl.dictrel-explorer` | `fi.cmxfico.gl.dictrel-explorer` | 一致 |
| 核算主体分组关系维护·关系成员 | `portal.model.gl.dictrel-content` | `fi.cmxfico.gl.dictrel-content` | 一致 |
| 核算主体分组关系维护·详情 | `portal.model.gl.dictrel-prop-detail` | `fi.cmxfico.gl.dictrel-prop-detail` | 一致 |
| 会计凭证（弹性组合） | `portal.model.gl.voucher-flex` | `fi.cmxfico.gl.voucher-flex` | 一致 |
| 字典数据维护(HTML) | `portal.model.gl.dct-data-editor-html` | `fi.cmxfico.gl.dct-data-editor-html` | 一致 |
**fi.gl 域（fi_gl_base_data）（4 对）**

| 页面 | model 侧 id | portal 侧 id | 状态 |
| --- | --- | --- | --- |
| 科目弹性组合 | `portal.model.fi_gl_base_data.account-def` | `fi.gl.fi_gl_base_data.account-def` | 一致 |
| 交易单据 | `portal.model.fi_gl_base_data.trade` | `fi.gl.fi_gl_base_data.trade` | 一致 |
| 交易弹性组合 | `portal.model.fi_gl_base_data.trade-def` | `fi.gl.fi_gl_base_data.trade-def` | 一致 |
| 财务会计凭证 | `portal.model.fi_gl_base_data.voucher` | `fi.gl.fi_gl_base_data.voucher` | 一致 |
**cr 域（1 对）**

| 页面 | model 侧 id | portal 侧 id | 状态 |
| --- | --- | --- | --- |
| inner_page2 | `portal.model.explorer-menu.testdlg` | `cr.explorer.explorer-menu.testdlg` | 一致 |
**死条目（rpt-ws）（4 对）**

| 页面 | model 侧 id | portal 侧 id | 状态 |
| --- | --- | --- | --- |
| 财务报表·共享模型(隐藏) | `portal.model.gl.rpt-ws-model` | `fi.cmxfico.gl.rpt-ws-model` | 双边死条目 |
| 财务报表·报表目录 | `portal.model.gl.rpt-ws-explorer` | `fi.cmxfico.gl.rpt-ws-explorer` | 双边死条目 |
| 财务报表·报表视图(表样) | `portal.model.gl.rpt-ws-content` | `fi.cmxfico.gl.rpt-ws-content` | 双边死条目 |
| 财务报表·属性/数据集/勾稽 | `portal.model.gl.rpt-ws-prop` | `fi.cmxfico.gl.rpt-ws-prop` | 双边死条目 |

## 附录 C：菜单引用分布

- `assets/model/data/menu-pages/fi/cmxfico/gl/explorer-menu.json`：`portal.model.*` 引用 80 处（凭证/交易/差旅/三区/字典维护业务页 + DAM + definition + doc + dct）
- `assets/model/data/menu-pages/basic/dataplatform/mdm/mdm-menu.json`：`portal.model.dct.data-editor` 1 处
- report / flow 菜单：无 `portal.model.*` 引用（各自引用 `portal.rpt.*` / `portal.flow.*`，由报表/流程服务承载）
