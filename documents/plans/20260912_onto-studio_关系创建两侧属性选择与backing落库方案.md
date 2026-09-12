# 本体工作室关系创建补全:两侧属性选择 + backing 必有值方案(v3·终版)

> 日期:2026-09-12 · 模块:onto-studio(studio.js)
> 目标:修复「关系创建不选两侧实体属性、backing 列空值」问题,对齐 designer.js D12 约定与 Palantir 实现。
> 流程:已经两轮子智能体对抗审查(第一轮:需修改后通过,5 项问题;第二轮:通过,1 项验收必改 + 4 条实现注记),本文为吸收全部审查意见后的终版。
> 分支:继续在 `cmx-container feat/onto-studio-ux` 开发;**零后端改动**(已核实全链路,见 §四)。

## 一、背景与现状(根因)

| 路径 | 现状 | 问题 |
| --- | --- | --- |
| 画布拖线建关系(link-add,studio.js:2596-2646) | 弹层显示"锚点 A.xxx → B.yyy",**但持久化 `backing: {}` 丢弃锚点**;且画布 link-add 事件 payload 实为 `{source, target, dropScreen, sourceContent}`,**不含属性字段**(vendor/cmx-ontology-canvas.js:2963 注释"属性字段恒空") | 选了没存 / 事件里根本没有 |
| 目录·元素库新建关系(newSimpleDialog link 分支) | 无两侧属性选择,直接 `backing: {}` | 功能缺失 |
| 关系编辑(linkInspector 编辑区) | 无属性映射区块,不能补/改 | 存量空 backing 无法补救 |
| 旧版 designer(D12,:1520-1545) | `backing = { fk: { sourceProperty, targetProperty } }`,画布 specEdge 锚点遍历消费;删除关系警示"backing.fk 依赖 ol_edge 遍历,删则断链" | **要补回的就是这套** |

**两套形状的裁决**:模型层 `LinkBacking` enum(ForeignKey{property,side}/JoinTable/Intermediary,def.rs:289-309)是 O2 对象存储的声明占位(未实装,`{fk:...}` 解析失败回退 Edge);designer/O-graph 消费的是 `backing.fk` 形状。**本方案只写 `fk` 形状、不双写**——与画布边遍历、designer、删除警示全兼容;后端 `backing` 为 jsonb 原样随存,`LinkTypeDef.backing` 是 `serde_json::Value` 接受任意形状,O1 保存校验/发布快照校验/读侧编译全链路核实不拒绝(**零后端改动成立**)。

## 二、开发项(P0-P2,全部 studio.js)

### P0 新建关系弹框(newSimpleDialog link 分支)补两侧属性选择(必选)

- A 端对象、B 端对象下拉 change → 级联出「A 端连接属性」「B 端连接属性」下拉:
  - 选项 = 该对象类型属性列表(S.manifest.objectTypes[].properties,**清单富化全量属性**);
  - **按 baseType 统一排除复合类型**(struct/array 及其子属性不作为连接属性;共享属性引用行 locked 与否无关,同样按 baseType 过滤);
  - label = `中文名称(apiName)`(无中文名则裸 apiName);
  - 对象切换 → 属性下拉联动重建;若排除后为空 → 即时提示「对象 X 无可选连接属性,请先补属性」(change 时即提示,不等提交)。
- **必选(用户裁决)**:提交时两侧连接属性任一为空 → 红框 + toast 阻止;对象无可选属性 → 阻止创建。
- 补 roleA/roleB 字段(对齐 designer 与 om_link_type 表)。
- 生成:`backing = LINK_BACKING_FK(aProp, bProp) = { fk: { sourceProperty: aProp, targetProperty: bProp } }`。

### P1 画布速建弹层(link-add)

- **画布事件 payload 不动**(画布只画关系连线,与属性无关——用户裁决);弹层内把原"锚点"只读行升级为「A 端连接属性」「B 端连接属性」下拉(选项 = source/target 对象属性;**默认预填两端主键**),必选 → `LINK_BACKING_FK` 随 `POST /link-types` 落库。
- 画布 `edge-delete-request` 删除确认框补**断链警示**:提交前 `GET /link-types/{api}` 取 backing(manifest.linkTypes 是 LinkTypeMeta 不含 backing,必须单独 GET)——有 `fk` → 显示「该关系已登记属性映射,删除后已建边不再可遍历」;无 → 维持原文案。

### P2 关系编辑态 + 详情对齐

- linkInspector 编辑区新增「属性映射(backing.fk)」区块:A/B 连接属性下拉(预填现存 `backing.fk` 值;预填值已不在选项中时追加「当前值(属性已不存在)」兜底,防静默漂移)。
- **saveSimple('link') 收集扩展(上轮审查 P0-2 断点)**:`body.backing = (src && tgt) ? LINK_BACKING_FK(src, tgt) : {}`——两侧齐全写 fk;任一清空 → **显式 `{}`**(回 Edge 的唯一正确路径,全行覆盖语义下不可省略)。
- 保存成功后:失效 `S.relDetail[d.apiName]` 缓存 + 局部重渲(P4 关系区块展开详情即时更新)。
- relDetailHtml backingTxt 识别 `fk` 形状 → 显示「属性映射:A.x → B.y」;`{}`/缺失 → 「未登记属性映射(Edge 兜底)」。

### 实现约定

- 统一工厂 `LINK_BACKING_FK(sourceProperty, targetProperty)`(兑现后端 handlers.rs `log_backing_fk_gaps` 注释引用的"前端唯一口径";字段齐全则不触发服务端 warn)。
- 属性下拉统一加 manifest 幂等守卫(新建态 newSimpleDialog 已预载;速建/编辑态入口先 `await loadManifest()`),不假设必在。
- 编辑清空一侧(另一侧有值)会丢弃另一侧值:表单内两个下拉同时可见,保存即明示;不加二次确认(记录为已知取舍)。

## 三、验证计划

1. 常规 Chromium 门户路径 E2E:
   - 新建关系:不选属性提交被拦(红框)/对象属性空被阻 → 选两侧属性创建 → 草稿 content.linkTypes 的 `backing.fk` 两字段齐全(API 校验);
   - 编辑:Inspector 重选两侧属性 → 保存接口为「保存(关系)」→ 草稿 backing 更新;清空一侧 → backing 显式 `{}`;
   - 画布:拖线速建弹层可选属性并落库;删边确认文案随 backing 有无变化(fk → 断链警示);
   - 详情:关系区块 backingTxt 显示「属性映射:A.x → B.y」;
   - 回归:P0-P5 既有 20 项验收 + 接口 picker 9 项。
2. API 校验:`GET /link-types/{api}`(live)与草稿双口径核对 backing 形状。
3. ~~画布边锚点显示~~(**第二轮审查必改**:画布组件无锚点渲染能力且与"画布只画连线"裁决矛盾,从验收清单删除)。

## 四、明确不做

- 不双写 `LinkBacking`(kind:ForeignKey/JoinTable)形状——待 O2 对象存储实装时再定 canonicalize 映射(N:M 的 JoinTable 约定、FK 的 side 归属),本期 fk 为声明性映射,运行时仍 ol_edge;
- 不动画布组件(vendor/cmx-ontology-canvas.js);
- 不做 designer 的画布"属性映射 details 折叠"交互(studio 以 Inspector 区块承载);
- 零后端改动(已两轮核实:请求反序列化/O1 校验/落库/存档回滚校验/读侧编译五环节证据链完整)。

## 五、两轮审查记录摘要

- **第一轮(需修改后通过)**:P0-1 画布 link-add 事件不含属性字段,原 P1"持久化事件锚点"被证伪;P0-2 saveSimple 不收集 backing,编辑态修改会静默丢失;P1-1 必选一刀切与 designer 可选矛盾(后经用户裁决为必选);P1-3 画布删边缺断链警示;P2-1 属性下拉行为未定义(复合排除/级联/预填/中文名);"零后端改动"经五环节证据链核实**成立**。
- **第二轮(通过)**:上轮问题全部闭环;必选边界(排除复合后为空)无阻断;清空→显式 `{}` 为必要设计(优于 designer 单边写法,规避服务端 warn);manifest 时序守卫、locked 按 baseType 统一过滤、当前值兜底、edge-delete 用 GET 取 backing、验收清单删除画布锚点项等实现注记已全部吸收进 §二/§三。

## 六、实施与验证补记(20260912 开发完成)

- **实现落地**:P0/P1/P2 三层全部落地于 `backend/cmx-container/assets/onto/web/ui-native/onto/studio.js`(分支 `feat/onto-studio-ux`,commit `dd3b2478`),零后端改动。另修一处既有交互瑕疵:A/B 端对象原本默认同选第一个对象,直接创建必被"A/B 端须为不同对象"拦截——B 端对象改为默认选第二个。
- **用户反馈追加(开发验证期)**:任一端"无可选连接属性"提示出现时,**创建按钮直接置灰**(P0 级联同步置灰/恢复;P1 静态置灰),`beforeOk` 必拦保留为兜底。
- **验证结论**:
  - 新功能 E2E(Playwright,门户 :5173 路径,UI5 真实键盘交互)20/20 全过:级联、置灰、必拦、创建落库(API 核对 backing.fk 与角色)、编辑态预填/保存保持/缓存失效、速建预填主键、删边两套断链文案;
  - 回归:门户 UI5 验收 20 项全 PASS,接口/共享属性 picker 套件 ALL_PASS(两套脚本已按 `984de5b` 直改 live 架构修正,原基于已移除的草稿双轨 API);
  - 浏览器实测(IAB):弹框字段/级联/置灰/创建/API 核对/删边文案全过,测试数据零残留。
