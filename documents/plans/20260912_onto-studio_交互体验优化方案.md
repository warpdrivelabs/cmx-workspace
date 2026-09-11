# 本体工作室(studio.js)交互体验优化方案

> 日期:2026-09-12 · 模块:onto-studio(`backend/cmx-container/assets/onto/web/ui-native/onto/studio.js`)+ cmx-ontology
> 目标:修复用户提出的 6 项交互问题;规划为 P0-P5 六个工作包,全部落地并完成 e2e/UI 验收。
> 分支:`cmx-container → feat/onto-studio-ux`、`cmx-ontology → feat/shared-props-pagination`(开发完成**不自动提交**)。

## 一、问题清单与结论映射

| # | 用户问题 | 结论 / 方案 |
| --- | --- | --- |
| 1 | dam 不应手动输入,应下拉选择 | DAM=Domain·Application·Module 三级分类,后端自由字符串 JSONB(`cmx-onto-model/src/def.rs:105` DamRef,无值域 API)。做**级联下拉**(选项从 manifest.objectTypes 聚合)+ 每级『＋ 新建…』入口(用户已确认)。→ P1 |
| 2 | 接口·共享属性改弹框选择(搜索+分页) | 现为普通下拉(studio.js:1710/:1724,manifest 全量);对象属性表"引用共享属性"同病(:1595);`ensureSpFull` 还逐个 GET 详情(:1631)。后端 `GET /shared-properties` 无 q/page/size(handlers.rs:231)。→ 后端加兼容分页(参照 list_object_types 模式 view_handlers.rs:533 + view_store.rs:196-261),前端做 `openSpPicker` 帮助弹框(K.openDialog + mountPager,双环境)。→ P2 |
| 3 | 新建/编辑五类实体必填字段加 `*` | 现状表单无任何红星。后端校验:对象=apiName;关系=apiName+两端;接口/共享属性/动作/函数=apiName(def.rs validate)。按"真实校验"口径标红星+提交拦截。→ P3 |
| 4 | 页面很多 renderAll,点列表行闪烁 | 点目录行已走轻量 `paintSelection()`(:2653);但树展开/折叠(:3530)、树过滤(:3778)、页签切换(:3517)、目录查询/分页(:3552/:2675)、属性表操作(:1526/:1549/:3380/:3394/:3408)、spFull 就绪(:1641)仍整屏 renderAll。→ 分区化渲染。→ P0 |
| 5 | 右栏编辑态与浏览态重复;对象关系要能点开看全 | 编辑态把浏览态 `ro` 拼尾部(objectInspector:1404、link:1678、interface:1726、shared:1742);浏览态不展示关系。→ 编辑/浏览互斥;浏览态对象类型加「关系(N)」可展开区块(懒 GET 详情)。→ P4 |
| 6 | 右侧详情统一抽屉组件(关闭按钮+拖宽)? | **评估:不做浮层抽屉**。理由:cmx-floating-dialog dock 模式不支持拖宽(cmx-floating-dialog.js:298-314)、遮挡画布、独立 :8097 vendor 子集无此组件(vendor/cmx-datacomp-subset.js 仅 4 个展示组件)、双环境一致性成本高;studio 核心工作流是"边看画布边编辑属性"。**用户已确认采用"增强右栏"**:header+收起按钮+拖宽 clamp+展开入口。→ P5 |

## 二、工作包明细

### P0 渲染分区化(去闪烁)

新增五个分区渲染函数,`renderAll()`(:2308)改为组合调用:

- `renderToolbar()` / `renderTabs()` / `renderLeft()` / `renderRight()`(含 bindPropExtras 重挂 + `.stu-right` 滚动保持)/ `renderMid()`(提取现有 tabbody 分支逻辑,canvas 页签保留 `<cmx-ontology-canvas>` 实例只 refreshCanvasSpec)。
- 替换点:
  - `data-dam` 树展开/折叠(:3526-3531)→ `renderLeft()`
  - 树关键字过滤(onRootInput :3785-3797 的树分支)→ 防抖 + `renderLeft()`
  - `data-tab` 页签切换(:3517-3520)→ tabs 高亮更新 + `renderMid()`
  - `cat-go` 查询(:3549-3555)/目录分页 onGo(:2675)/`cat-kind` 切换(:3761-3768)→ `renderMid()`
  - `addSharedRefOp`(:1626)、`ensureSpFull` 就绪(:1641)、`propBulkOp`(:1526)、`movePropRow`(:1549)、`propTableOp`(:3380)、`ifacePropOp`(:3394)、`ifaceExtOp`(:3408)、`implAdd/implDel` → `renderRight()`
- 保留 `renderAll()`:toggleMode、openScene/openBase、reloadLive、restoreVersion、applyElementOverlay、refreshAfterMutation、delElement、新建元素成功、cv-full、loadRoles 初始化。

### P1 DAM 级联下拉(问题 1,20260912 用户反馈后修订:调用注册中心接口、去掉页面新建)

- 新 util `ensureDamRegistry()`:调用门户统一 **DAM 注册中心接口 `GET /api/registry/dam`**,取得 domains/applications/modules 三级权威值域(带中文名);挂载后预载,编辑表单惰性兜底,装载成功右栏局部刷新一次;独立 :8097 无此路由 → 404 静默回退 manifest 聚合。
- `damAgg()` 聚合:**注册表值域 ∪ manifest 对象现有值(遗留值兜底,标「当前值·未在注册表」)**;级联选项 label 带中文名(`fi · 财务资源管理`)。
- objectInspector 编辑态:三个级联 `selHtml`(选域过滤应用/模块,只重建下级 select,未保存键入不丢);**无『＋ 新建…』入口**(用户裁决:DAM 是注册中心完整实体,页面不提供新建,新增分组一律到 DAM 注册中心维护)。
- newObjectDialog 域下拉同源同款;保存逻辑不变。

### P2 共享属性帮助弹框(问题 2)

**后端(cmx-ontology)**:
- `list_shared_properties`(handlers.rs:231)加可选 Query `q/page/size`:任一出现 → `{rows,total,page,size}` 信封;都不传 → 全量数组(旧语义兼容,旧前端不受影响)。q 对 api_name/display_name ILIKE;分页模式返回**完整定义**(SharedPropertyTypeDef 含 baseType/semanticType),顺带消除前端逐个拉详情。存储层参照 view_store.rs:196-261 模式。遵循"既有 GET 加可选查询参数",不新增路径、不动删除。
- 验证:`cargo check`(+clippy 新增代码零告警)→ cmx-launcher API 重启 onto :8097 → curl 验证两种形态。

**前端(studio.js)**:
- 新函数 `openSpPicker({ excludeSet, onPick })`:K.openDialog(宽 720,标题"选择共享属性")内装配 搜索输入(250ms 防抖)+ 表头表格 + `K.mountPager`(20/页);数据 `GET /shared-properties?q&page&size`;响应为数组(旧后端/独立环境)时客户端过滤+分页兜底;行点击选中 → `onPick(sp)`。
- 接入点 1:`interfaceInspector`"要求的共享属性"添加按钮 → `openSpPicker`,onPick 推入 `d.properties` + `renderRight()`;移除原 `data-f="prop-add"` 下拉(:1724)。
- 接入点 2:`sharedRefBarHtml`『＋ 引入』→ `openSpPicker`,onPick 直接拿到完整 sp 走引入逻辑;移除原 `data-f="sp-ref"` 下拉(:1595)。
- `ensureSpFull`(:1631)退役(调用点删除,函数移除)。

### P3 必填红星(问题 3)

- 标 \* 口径(与真实校验一致):
  - 新建五类:`apiName`*;关系另 `A 端`*`B 端`*`基数`*(默认 oneToMany);共享属性 `基础类型`*;函数 `运行时`*。
  - 新建对象:`apiName`*、`主键属性`*、`标题属性`*(有预填)。
  - 编辑 Inspector:对象 显示名(不标,后端 apiName 兜底)/主键属性*、标题属性*;关系 基数*;共享属性 基础类型*。
- 样式:`<i class="req">*</i>` 红星,色值 `var(--sapNegativeColor,#bb0000)` token 派生(privCss 模式,双主题零硬编码)。
- 校验:`dlg()` 增加 `beforeOk(bodyEl, values)` 回调——返回错误消息数组则红框(`.stu-ovl-bd .bad`)+toast 且**不关弹层**;`saveObjectForm/saveSimple/saveAction/saveFn` 保存前同样拦截(Inspector 内红框 + toast)。

### P4 右栏编辑/浏览去重 + 对象关系列表(问题 5)

- 六类 Inspector 编辑态去掉尾部 `+ ro` 拼接;action/fn 的试算/执行面板保留(ro 描述部分仍去重)。
- 浏览态对象类型新增「关系(N)」区块:`S.manifest.linkTypes` 过滤 `objectTypeA/objectTypeB === apiName`;行 = 方向(A→B / B→A)+ 显示名(apiName)+ 基数 + 对端类型;点击行 → 懒 `GET /link-types/{api}`(S.linkDetailCache 缓存)展开完整字段:roleA/roleB、backing 解析(Edge/ForeignKey/JoinTable/Intermediary)、两端 DAM、状态、更新时间 + 「画布定位」按钮(locateOnCanvas)。编辑态该区块默认折叠。

### P5 右栏增强(问题 6,已评估)

- `inspectorHtml` 顶部统一 header:元素名 + apiName chip + 状态 + 类型 + 『⇥ 收起』按钮(`data-act="right-collapse"`)。
- 收起:右栏隐藏(width 0 / display none)、右 gutter 隐藏、中栏自动占满;工具条出现「属性」按钮(或右缘竖条)恢复;状态存 sessionStorage(跨 renderAll 保持)。
- `bindGutters` 拖宽 clamp:右栏 280~640px、左栏 200~360px;localStorage 记忆保留。
- 全部新增 CSS 走 privCss token 派生,双主题(UI5 + Neo)双皮肤,零硬编码色值。

## 三、对抗性审查记录(3 轮)

**轮 1 · 回归风险(renderAll 依赖)**
- 风险:分区化后漏掉隐式依赖——页签切到 canvas 需要 ensureCanvas/wireCanvas;renderMid 必须完整复用 renderAll 的 tabbody 分支(提取而非复制)。✔ 方案:提取 `renderTabbody(root)` 供两者调用。
- 风险:renderRight 重建后 bindPropExtras(拖拽)未重挂 → 拖拽失效。✔ renderRight 内强制重挂;改造后逐点手测:批量条、行拖拽、PK 单选。
- 风险:左树重建丢展开态/滚动 → 展开态在 `S.expDam`、滚动保存恢复照抄 renderAll 既有模式,renderLeft 内做同款保存/恢复。
- 风险:paintSelection 与 renderRight 双轨不一致 → paintSelection 改为薄封装调 renderRight(行为收敛为一条路径)。

**轮 2 · 双环境兼容(门户 / 独立 :8097)**
- 弹框必须双通路:门户有 `__cmxDataComp`(全量),独立环境仅 vendor 子集。✔ 用 K.openDialog(K 内部探测 floating-dialog,否则自绘 okd)+ K.mountPager(独立环境手写页脚)——两条通路工作区已有成熟用例(workshop.js:689、studio.js:2672),**不引入新组件依赖、不动 vendor 子集**。
- 后端分页兜底:openSpPicker 检测响应为数组(未升级后端)→ 客户端过滤+分页,页面不报错。
- selHtml 级联下拉沿用现有双通路控件(UI5 select / 原生 select 回退)。

**轮 3 · 数据与权限门控**
- 草稿轨:所有编辑仍走既有 `D.row` 草稿 + 保存/发布流程,P2/P4 不改变提交语义(ifacePropOp 仍改内存草稿、保存按钮才提交)。
- 只读角色:`D.available === false` 时维护按钮隐藏的既有门控全部保留;新增交互(关系展开、picker、收起)对只读角色同样可用(浏览能力)。
- 后端兼容:不传参返回全量数组,旧版 studio/其他调用方(explorer/workshop/designer 用 manifest,不走该 list)零影响;删除接口不动。
- 会话状态:S.damExtra / S.linkDetailCache / 收起态均为会话级,不落 localStorage 污染,刷新即清。

## 四、测试与验收(完成定义)

1. 后端:cmx-ontology `cargo check` + clippy 新增代码零告警;cmx-launcher API 重启 onto;curl 验证 `GET /shared-properties`(全量数组)与 `?q=&page=1&size=20`(信封)。
2. 前端 e2e(control-browser,@ http://127.0.0.1:5173/view/onto-studio,admin/Admin@12345),P0-P5 逐项:
   - P0:点目录行/树展开折叠/切页签/目录查询——无整屏闪烁(对比改造前后);属性表拖拽/批量/PK 仍正常。
   - P1:对象编辑 DAM 三级级联选值;新建域;保存后左树分组正确。
   - P2:接口添加共享属性走弹框:搜索过滤、翻页、选中入 chip;对象属性表引入共享属性同验;旧语义兜底可用。
   - P3:五类新建弹层红星;清空 apiName 提交被拦截不关弹层;编辑 Inspector 红星同验。
   - P4:编辑态无重复浏览块;浏览态对象关系区块可展开看全字段、画布定位可用。
   - P5:右栏可收起/展开、拖宽 clamp 生效、刷新后宽度记忆。
   - 回归:画布选中/undo-redo/场景切换/目录六类/新建五类草稿/删除 e2etest_ 前缀测试数据;双主题无硬编码色值;截图留证。
3. 汇报改动清单;**不 commit / 不 push**,等用户指令。

## 五、明确不做

- 不改 explorer / workshop / designer 三页;不动 vendor 子集与 page-kit 公共 API(dlg 的 beforeOk 为 studio 本地函数扩展);接口"继承/实现接口"下拉保留(数据量小);不做浮层抽屉;不动发布/版本中心流程。

## 附录:开发与测试结果(2026-09-12 实施后补记)

### 实际改动
- `cmx-ontology`(feat/shared-props-pagination):`handlers.rs`(+Query 结构与分页分支)、`view_store.rs`(+`list_shared_properties_paged`,完整定义直出)。cargo check/clippy 零新增告警;curl 验证旧语义(全量数组)/新信封(q+page+size,ILIKE 中文搜索)/分页钳制均生效。
- `cmx-container`(feat/onto-studio-ux):仅 `studio.js`(+约 600 行)。渲染分区化、DAM 级联、openSpPicker、必填校验(beforeOk/markBad/requireOk)、关系区块、右栏收起与分侧拖宽 clamp、树过滤输入即滤(200ms 防抖)。

### 测试中额外发现并修复的 3 个问题
1. `openSpPicker` 行渲染漏 `.join('')`(数组直赋 innerHTML 会出逗号垃圾)——已修。
2. 保存成功后 `S.propDraft=null` 但表格未重建,「从目录引入」守卫静默失效——改为与 objectInspector 同款惰性初始化。
3. 进入编辑态时关系区块未按"编辑默认折叠"重置——`toggleMode` 中重置 `relOpen/relExpanded`;顺带把树过滤从 change(失焦才生效)改为 input 即滤。

### E2E/UI 测试结果(11 项,全部通过)
| # | 验收项 | 结果 |
| --- | --- | --- |
| 1 | P0 树展开/折叠仅重建左栏(MutationObserver 计数 left=1,其余 0) | ✅ |
| 2 | P0 页签切换仅重建 tabs+mid | ✅ |
| 3 | P4 点目录行轻量选中(right=1);浏览态含「关系(N)」区块;无编辑/浏览重复 | ✅ |
| 4 | P4 关系行展开完整定义(懒 GET:方向角色/基数/落库方式/DAM/状态+画布定位) | ✅ |
| 5 | P5 右栏收起(width=0、工具条「▤ 详情」恢复、目录占满全宽、选中态保留) | ✅ |
| 6 | P1 编辑态 DAM 三级级联下拉+当前值兜底+红星 | ✅ |
| 7 | P3 新建对象弹层 3 处红星;清空 apiName 提交被 beforeOk 拦截(红框+toast 不关弹层) | ✅ |
| 8 | P1 域切换级联过滤/『＋新建…』登记会话聚合/保存后下级选项聚合 | ✅ |
| 9 | P2 对象「从目录选择引入」picker:标题/3 行数据/计数/分页器/搜索过滤/选中追加 ⊞ 锁定行 | ✅ |
| 10 | P2 接口「＋从目录选择添加」:选中入 chip;重开 picker 已选项标「已用」且无选择按钮;保存生效 | ✅ |
| 11 | P0 树过滤输入即滤(left=1、焦点保持);目录查询仅重建 mid | ✅ |

- 回归:画布组件存活与渲染、undo/redo、草稿待发布徽标、目录分页器、删除流程(草稿删除登记)均正常;全程零 JS 错误。
- P5 拖宽 clamp:实测右栏 669px(=640+padding/border)与 309px(=280+padding/border),钳制生效。
- 测试数据清理:e2etest_obj/e2etest_iface 走草稿删除,3 条 e2etest 共享属性 API 删除,验证剩余 0。
- 双主题:新增 CSS 全部 `var(--sap*/neo-*,fallback)` token 派生,零硬编码色值。

### 测试环境说明(重要)
门户 dev(:5173/view/onto-studio)在本轮测试期间出现**与本次改动无关的页面楔死问题**:门户壳层加载原生页面源码的 fetch 永久挂起(旧版 studio/workshop 同样无法打开,可证明非本次回归)。已排查:后端 :8080/:8097 健康、SSE 端点 TTFB 正常、vite 代理正常、IndexedDB 正常;症状为 webview 对同源请求全量排队(cross-origin 正常),疑似 zcode 内嵌浏览器(IAB)网络服务对长连接/HMR 的连接池占满问题,**建议在用户常规浏览器中直接验证门户路径**。本轮 UI 测试改用旁路 harness(:5173 静态页 + 跨域挂 :8097 的 studio.js + X-API-Key 鉴权,数据/交互全链路真实),测毕已删除 harness 文件。

### 门户路径 UI5 双通路最终验收(2026-09-12 补充,常规 Chromium + Playwright)
上一节的楔死问题经常规浏览器(独立 Chromium,非 zcode 内嵌 webview)复测,**不复现**——门户 dev 页面在真实浏览器中挂载正常,楔死确认为 zcode IAB webview 特有的网络栈问题(存量问题,与本次改动无关,建议单独立项排查 IAB 对长连接/HMR 的连接处理)。

真实门户路径(admin/Admin@12345 登录 → /view/onto-studio)下 UI5 双通路验收 **20/20 全部通过**。

**P1 补充裁决(20260912 用户反馈二)**:DAM 级联下拉**必须调用已有的 DAM 注册中心接口**,且页面不提供新建入口(注册中心的域/应用/模块是完整实体,不是填个 name 就行)。落地:
- 值域权威来源 = `GET /api/registry/dam?active_only=false`(门户统一 DAM 注册表,返回 domains/applications/modules 三级,含中文名),`ensureDamRegistry()` 挂载预载 + 编辑表单惰性兜底,加载成功后右栏局部刷新一次;
- 级联选项 label 带 中文名(`fi · 财务资源管理`);对象遗留值不在注册表时以「当前值·未在注册表」兜底显示(不丢老数据);独立 :8097 无此路由 → 404 静默回退 manifest 聚合;
- **去掉页面『＋ 新建…』入口与配套的新值输入框/会话缓存**(damOptsFor/damSelHtml/handleDamCascade/saveObjectForm/newObjectDialog 六处清理),新建分组一律到 DAM 注册中心维护。

| # | 验收项 | 结果 |
| --- | --- | --- |
| 1 | 门户登录 + 壳层挂载(.stu attached) | ✅ |
| 2 | UI5 运行时(ui5-select/ui5-input/ui5-button 均注册) | ✅ |
| 3-4 | P0 树展开仅左栏(left=1)/页签切换仅 tabs+mid(mid=2),右栏/工具条零重建 | ✅ |
| 5-6 | P4 浏览态关系区块 + 行展开完整定义 + cmx-desc-list 渲染 | ✅ |
| 7-8 | P5 右栏收起(display:none+工具条「详情」恢复)/拖宽钳制(实测 669/309px,含 padding) | ✅ |
| 9-10 | P4 编辑态去重(roCount=0)+ P1 DAM 三级级联 ui5-select 真通路渲染(ui5-option×10、ui5-input×4) | ✅ |
| 11 | **P1 DAM 注册表接入:域选项含 fi/basic/cr/dr/hr/portal/sc 且 label=「fi · 财务资源管理」、无『＋新建…』入口** | ✅ |
| 12 | **P1 注册表级联:域选 fi → 应用选项自动过滤为 cmxfico/ebs/kingdee/sap/yonyou 并选中** | ✅ |
| 13 | P3 新建弹层 3 处红星 + 清空 apiName 提交拦截(.bad 红框、弹层保持打开) | ✅ |
| 14 | **P1 新建对象(域=fi 注册表值)创建成功,草稿 dam={domain:'fi'}** | ✅ |
| 15 | **P1 级联保存:Type1.dam={fi, cmxfico} 落草稿 → 还原为未分组** | ✅ |
| 16 | P2 picker:打开/计数/分页器/搜索过滤/选中引入 ⊞ 锁定行 | ✅ |
| 17 | P0 目录查询仅重建 mid(mid=1) | ✅ |
| 18-20 | 清理:e2e2_obj 草稿删除、e2e2_sp_1/2 API 删除、Type1 DAM 还原 | ✅ |

- 已知观察(均为存量行为,非本次引入):①新建对象后不自动选中(newObjectDialog 与 newSimpleDialog 行为不一致);②目录在编辑态查询过滤后,草稿新增行全量追加且 propertyCount 显示 undefined;③点选「仅草稿存在」的对象时 live GET 404 回退(Inspector 显示装载失败占位)。
- 测试方法备注:UI5 select **不支持** `selectedIndex` 编程式赋值(内部选中态不跟随,属组件设计),自动化验证须走真实交互(点击开弹层 + 方向键 + Enter,或鼠标点选),产品代码对真实 change 事件的响应已全链路验证。

### 追加裁决(20260912 用户反馈三):弹层点击边缘不再关闭

- `dlg()`(studio 本地弹层工厂,新建/重命名/删除确认/元素库/⌘K 等全部弹层共用):**移除「点击遮罩即关闭」**——防误触丢失已键入内容,对齐 Fiori 模态规范。关闭只走明确动作:**✕ 按钮 / 取消·关闭按钮 / Esc**。
- 常规 Chromium 门户路径验证:点遮罩边缘 → 弹层保留且 apiName 键入保留;Esc → 关闭;✕ → 关闭。

- 备注:UI5 select 不支持 `selectedIndex` 编程式赋值(组件设计),自动化须走真实交互(点开弹层+方向键+Enter 或鼠标点选)。

### 追加修复(20260912 用户反馈五):属性表格列错位(对齐 designer.js)

- **Bug**:属性表格行只有 8 个 `<td>`(勾选与属性名合并在第一格),表头有 9 列——自「中文名称」起整体错位一格:中文名称列显示的是**数据类型下拉**、语义类型列显示的是 **PK 单选**,与 designer.js 参考界面严重不符。
- 修复:拆分首格为「勾选」「属性名」两列(层级缩进移至属性名格),9 列一一对齐;按 designer.js 对齐**语义类型控件**:由自由文本输入框改为固定词表下拉(移植 `SEMANTIC_TYPES`/`SEMANTIC_LABEL`:—/金额/百分比/数量/比率/邮箱/电话/链接/证件号/国家码/币种/坐标/颜色/时长),遗留自定义值以「当前值」兜底;共享属性 Inspector 的语义类型同步改词表下拉。
- 验证(DOM 级):表头 9 列 ↔ 行 9 格,控件类型逐列核对(勾选=checkbox、属性名/中文名称/语义类型… 语义=下拉、PK=radio);完整回归 20/20 通过。

### 追加优化(20260912 用户反馈六):属性表格交互三项

- **拖拽改手柄发起**:行不再整行 `draggable`(整行拖动会干扰行内输入框的文本选择),行首新增 `⠿` 手柄(仅手柄 draggable),拖拽换序/跨层禁用/高亮逻辑不变。
- **添加属性不再跳动**:点击「＋ 添加属性」/「＋子」后,新行 `scrollIntoView(block:nearest)` 最小滚动滚入视口,页面不再跳动。
- **下拉收窄**:数据类型下拉 104px→**88px** 固定宽,语义类型下拉 88px→**76px** 固定宽。
- 验证(常规 Chromium 门户路径):手柄拖拽换序生效(newProp 行拖至首行)、新行滚入可视区、宽度实测 88/76px。

### 追加裁决(20260912 用户反馈四):接口选择同样改弹框字典选择

- 对象类型「实现接口挂接」与接口「继承添加」的原生下拉**全部移除**,统一改走 `openSpPicker` 帮助弹框(搜索 + 分页,与共享属性同款交互);`openSpPicker` 泛化为 `entity: 'shared' | 'interface'` 双实体。
- 后端补齐 `GET /interfaces` 兼容分页(镜像 shared-properties:`q/page/size` 任一传 → `{rows,total,page,size}` 信封,不传 → 全量数组旧语义;`list_interfaces_paged` 轻量 meta + ILIKE)。
- 排除语义:实现挂接排除已实现;继承添加排除自身与已继承;picker 内被排除项标「已用」且无选择按钮。
- 验收(常规 Chromium 门户路径,9/9 通过):挂接 picker 打开/搜索/选中/ chip/草稿落轨/重开「已用」排除/继承自排除/选中/extends 落轨/Type1 摘除还原,全部通过。
- 备注:UI5 select 不支持 `selectedIndex` 编程式赋值(组件设计),自动化须走真实交互(点开弹层+方向键+Enter 或鼠标点选)。
