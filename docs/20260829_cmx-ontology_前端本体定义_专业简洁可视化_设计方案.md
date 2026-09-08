# cmx-ontology 前端本体定义 · 专业 · 简洁 · 可视化 设计方案

> 版本 v1.0 · 2026-08-29
> 定位：一份**只谈"本体定义如何在前端被创建与维护"**的交互与视觉设计方案。目标是把 §5 元模型
> （对象/属性/关系/接口/共享属性/动作/函数七类元素）的定义工作，做成**图为先、直接操作、内联编辑、
> 规格可验证**的专业工作台——对标 Palantir Ontology Manager，融合业界图式 Schema 设计器（dbdiagram /
> Prisma Editor / DbSchema / Hackolade）的成熟范式，落到你已有的 cmx 资产上（`@cmx/decision-graph`
> Web Component、native 四区、门户联邦、O1 REST 端点）。
>
> 本文只出**方案**，不动代码。文中 HTML/JSON/交互片段均为契约示意。上游总纲见
> `20260828_cmx-ontology_Palantir式企业本体平台_Rust完整建设方案.md`（本体后端 O0–O2 已落地真机绿）。

---

## 目录

1. [问题与设计原则](#一问题与设计原则)
2. [三种定义范式的取舍（为什么"图为先"）](#二三种定义范式的取舍)
3. [信息架构：一台三面板 + 双向同步](#三信息架构一台三面板--双向同步)
4. [核心画布：本体图（Ontology Graph）](#四核心画布本体图ontology-graph)
5. [Inspector：右侧内联编辑器（七类元素）](#五inspector右侧内联编辑器)
6. [属性编辑器：本体定义的最高频交互](#六属性编辑器本体定义的最高频交互)
7. [关系定义：在画布上"拉一条线"](#七关系定义在画布上拉一条线)
8. [动作 / 函数：图元 + 专用编辑器](#八动作--函数图元--专用编辑器)
9. [双向同步：图 ⇄ 规格（Spec）⇄ 后端](#九双向同步图--规格--后端)
10. [演进安全：编辑守卫与破坏性变更提示](#十演进安全编辑守卫与破坏性变更提示)
11. [低摩擦入口：导入 / AI 生成 / 键盘流](#十一低摩擦入口)
12. [视觉系统：令牌、图元语言、双主题](#十二视觉系统)
13. [组件抉择：复用 vs 新建 `@cmx/ontology-graph`](#十三组件抉择)
14. [与后端契约的映射](#十四与后端契约的映射)
15. [布局线框（ASCII）](#十五布局线框)
16. [落地路线 UI0–UI5](#十六落地路线-ui0ui5)
17. [参考](#十七参考)

---

## 一、问题与设计原则

**问题**：本体定义天然是"一张图"——对象类型是节点，关系类型是边，接口是横切契约，动作/函数挂在对象上。
但它又要求**精确**（apiName 稳定、主键、基数、类型约束）。纯表单太碎（七张表、来回跳转、看不见全局关系），
纯画图又不够精确（拉个框画条线，落不到强类型定义）。专业工具的答案是：**图为先，但图元背后是强类型规格，
两者双向同步、都可编辑**。

**五条设计原则**（贯穿全文，来自业界图式设计器共识 + Palantir OMA 实践）：

| # | 原则 | 含义 | 反面 |
| --- | --- | --- | --- |
| P1 | **图为先，规格为真** | 画布是主视图；但"真相"是强类型规格（Spec），画布是它的一种可编辑投影 | 画布是死图（只能导出、不能回写） |
| P2 | **直接操作** | 节点/边是活的矢量对象——拖、连、选、改都在画布上原地发生 | 一切靠模态框、离开画布才能改 |
| P3 | **内联编辑** | 改字段/类型/基数无需模态跳转；选中即在右侧 Inspector 就地编辑 | 每改一处弹一个窗 |
| P4 | **规格可验证** | 每次编辑即时结构校验（apiName 合法性、主键存在、关系两端存在、成环检测），错误就地红标 | 保存后才报错、错误信息在别处 |
| P5 | **演进安全** | 破坏性变更（改主键、删被引用属性、改关系基数）显式警示 + 影响面预览 | 静默改坏、下游应用崩了才知道 |

> 一句话北极星：**"看得见全局关系（图），改得动每个细节（Inspector），且永远改不出非法定义（校验）。"**

---

## 二、三种定义范式的取舍

本体定义的前端，历史上有三条路。明确取舍，避免"什么都做一点"。

<p align="center"><img alt="fig-paradigms" src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA4NDAgMjY0IiBmb250LWZhbWlseT0idWktc2Fucy1zZXJpZixzeXN0ZW0tdWksJ1BpbmdGYW5nIFNDJyxzYW5zLXNlcmlmIj4KPHJlY3Qgd2lkdGg9Ijg0MCIgaGVpZ2h0PSIyNjQiIHJ4PSIxNCIgZmlsbD0iI2ZmZmZmZiIgc3Ryb2tlPSIjZTJlOGYwIi8+Cjx0ZXh0IHg9IjMwIiB5PSIzNCIgZm9udC1zaXplPSIxNSIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iIzBmMTcyYSI+5LiJ56eN5pys5L2T5a6a5LmJ6IyD5byP55qE5Y+W6IiN77yaQ++8iOWbvuS4uuWFiCArIOW8uuexu+WeiyBJbnNwZWN0b3LvvInog5zlh7o8L3RleHQ+CjwhLS0gQSDnuq/ooajljZUgLS0+CjxyZWN0IHg9IjMwIiB5PSI1NiIgd2lkdGg9IjI0MCIgaGVpZ2h0PSIxODAiIHJ4PSIxMCIgZmlsbD0iI2ZlZjJmMiIgc3Ryb2tlPSIjZmVjYWNhIi8+Cjx0ZXh0IHg9IjQ2IiB5PSI4MiIgZm9udC1zaXplPSIxMyIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iI2I5MWMxYyI+QSDCtyDnuq/ooajljZUgLyDliJfooag8L3RleHQ+Cjx0ZXh0IHg9IjQ2IiB5PSIxMDgiIGZvbnQtc2l6ZT0iMTEuNSIgZmlsbD0iIzk5MWIxYiI+5LiD57G75YWD57Sg5LiD5byg6KGo77yM5p2l5Zue6Lez6L2sPC90ZXh0Pgo8dGV4dCB4PSI0NiIgeT0iMTMwIiBmb250LXNpemU9IjExLjUiIGZpbGw9IiM5OTFiMWIiPueci+S4jeingeWFqOWxgOWFs+ezuzwvdGV4dD4KPHRleHQgeD0iNDYiIHk9IjE1MiIgZm9udC1zaXplPSIxMS41IiBmaWxsPSIjOTkxYjFiIj7inJcg57K+56Gu77yM5L2G5b+D5pm66LSf5ouF6auYPC90ZXh0Pgo8dGV4dCB4PSI0NiIgeT0iMjA2IiBmb250LXNpemU9IjEyIiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjYjkxYzFjIj7liKTlhrPvvJrku4XkvZwgSW5zcGVjdG9yIOWGhemDqOaJv+i9vTwvdGV4dD4KPCEtLSBCIOe6r+eUu+WbviAtLT4KPHJlY3QgeD0iMzAwIiB5PSI1NiIgd2lkdGg9IjI0MCIgaGVpZ2h0PSIxODAiIHJ4PSIxMCIgZmlsbD0iI2ZmZmJlYiIgc3Ryb2tlPSIjZmRlMDhhIi8+Cjx0ZXh0IHg9IjMxNiIgeT0iODIiIGZvbnQtc2l6ZT0iMTMiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiM5MjQwMGUiPkIgwrcg57qv55S75Zu+PC90ZXh0Pgo8dGV4dCB4PSIzMTYiIHk9IjEwOCIgZm9udC1zaXplPSIxMS41IiBmaWxsPSIjYjQ1MzA5Ij7mi5bmoYbnlLvnur/vvIznm7Top4njgIHnnIvlvpfop4HlhbPns7s8L3RleHQ+Cjx0ZXh0IHg9IjMxNiIgeT0iMTMwIiBmb250LXNpemU9IjExLjUiIGZpbGw9IiNiNDUzMDkiPueUu+S4quahhiDiiaAg5LiA5Liq5by657G75Z6L5a6a5LmJPC90ZXh0Pgo8dGV4dCB4PSIzMTYiIHk9IjE1MiIgZm9udC1zaXplPSIxMS41IiBmaWxsPSIjYjQ1MzA5Ij7inJcg5LiN5Y+v6aqM6K+BPC90ZXh0Pgo8dGV4dCB4PSIzMTYiIHk9IjIwNiIgZm9udC1zaXplPSIxMiIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iIzkyNDAwZSI+5Yik5Yaz77ya5ryC5Lqu5L2G5LiN57K+56Gu77yM5byDPC90ZXh0Pgo8IS0tIEMg5Zu+5Li65YWIK0luc3BlY3RvciAtLT4KPHJlY3QgeD0iNTcwIiB5PSI1NiIgd2lkdGg9IjI0MCIgaGVpZ2h0PSIxODAiIHJ4PSIxMCIgZmlsbD0iI2VjZmRmNSIgc3Ryb2tlPSIjNmVlN2I3IiBzdHJva2Utd2lkdGg9IjIiLz4KPHRleHQgeD0iNTg2IiB5PSI4MiIgZm9udC1zaXplPSIxMyIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iIzA2NWY0NiI+QyDCtyDlm77kuLrlhYggKyDlvLrnsbvlnosgSW5zcGVjdG9yIOKYhTwvdGV4dD4KPHRleHQgeD0iNTg2IiB5PSIxMDgiIGZvbnQtc2l6ZT0iMTEuNSIgZmlsbD0iIzA0Nzg1NyI+55S75biD55yL5YWo5bGA77yMSW5zcGVjdG9yIOaUuee7huiKgjwvdGV4dD4KPHRleHQgeD0iNTg2IiB5PSIxMzAiIGZvbnQtc2l6ZT0iMTEuNSIgZmlsbD0iIzA0Nzg1NyI+5Y+M5ZCR5ZCM5q2lICsg5Y2z5pe25qCh6aqMPC90ZXh0Pgo8dGV4dCB4PSI1ODYiIHk9IjE1MiIgZm9udC1zaXplPSIxMS41IiBmaWxsPSIjMDQ3ODU3Ij7inJMg5YWo5bGA5YWz57O75Y+v6KeBICsg57K+56Gu5Y+v6aqM6K+BPC90ZXh0Pgo8dGV4dCB4PSI1ODYiIHk9IjIwNiIgZm9udC1zaXplPSIxMiIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iIzA2NWY0NiI+5Yik5Yaz77ya6YeH55So77yI5pys5pa55qGI77yJPC90ZXh0Pgo8L3N2Zz4="/></p>

| 范式 | 代表 | 优 | 劣 | 判决 |
| --- | --- | --- | --- | --- |
| **A. 纯表单/列表** | 传统 CRUD 后台（含你现有 O1 dashboard 雏形） | 精确、实现快 | 看不见全局关系、七类元素来回跳、心智负担高 | ❌ 仅作 Inspector 内部承载 |
| **B. 纯画图** | 白板/思维导图 | 直觉、看得见关系 | 落不到强类型（画个框≠一个 ObjectType）、不可验证 | ❌ |
| **C. 图为先 + 强类型 Inspector**（本方案） | Palantir OMA、Prisma Editor、DbSchema、Hackolade | 全局关系可见 + 每个细节精确可编辑 + 可验证 + 演进安全 | 实现成本高（画布 + 双向同步） | ✅ **采用** |

**判决：C。** 画布负责"看得见关系、直接操作"，Inspector 负责"精确、强类型、可验证"，二者双向同步——
这正是 dbdiagram/Prisma Editor 的"canvas 与 code 是同一真相的两个可编辑视图"共识，也是 Palantir OMA 的
"object-type overview（图+分区）+ property editor（精确表单）"结构。

---

## 三、信息架构：一台三面板 + 双向同步

沿用你成熟的 **native 四区**骨架，但按"图为先"重排为**三面板**（把四区的"中上/中下"合并为一块主画布）：

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  顶栏：本体名 · 版本徽标(草稿/已发布 vN) · [校验✓/⚠N] · [发布] · [导入] · [主题] │
├──────────────┬───────────────────────────────────────────────┬────────────────┤
│  ① Explorer  │            ② 本体图画布 (Ontology Graph)         │ ③ Inspector    │
│  类型浏览器   │  ┌──────┐        places        ┌──────┐          │  内联编辑器     │
│              │  │Customer│──────1:N──────────▶│ Order │          │ (选中元素的     │
│ ▸ 对象类型 3 │  │◇id  PK │                     │◇oid PK│          │  强类型表单)    │
│ ▸ 关系类型 1 │  │ name ⌾│                     │ amount│          │                │
│ ▸ 接口 1     │  └──┬───┘                     └───────┘          │ [Tab:概览|属性  │
│ ▸ 共享属性 1 │     │ implements                                  │  |关系|动作|数据]│
│ ▸ 动作 1     │  ┌──▽──────┐  «interface»                        │                │
│ ▸ 函数 1     │  │Locatable │  （虚线挂接）                        │                │
│              │  └──────────┘                                    │                │
│  [+ 新建 ▾]  │  [自动布局] [+对象] [+关系] [适应] [－ 缩放 ＋]     │  [保存] [删除]  │
└──────────────┴───────────────────────────────────────────────┴────────────────┘
             ▲ 三者同一真相（Spec），任一处改动 → 另两处即时反映（双向同步）
```

- **① Explorer（左，可折叠）**：七类元素分组树（对齐 rulesengine explorer 的查找/刷新/分组折叠范式）。
  点条目 = 在画布中定位并高亮 + 打开 Inspector。是"精确查找 + 大本体导航"的入口（画布看关系，树看清单）。
- **② 本体图画布（中，主角）**：对象类型=节点，关系类型=边，接口=虚线挂接的横切节点。直接操作全在这里。
- **③ Inspector（右，可折叠）**：当前选中元素的**强类型内联编辑器**，分 Tab（对齐 OMA 的 object-type
  overview 分区：概览/属性/关系/动作/数据）。这里承载"范式 A 的精确"，但被收进单一上下文面板，不再是散落七张表。

> 关键：**三面板是同一 Spec 的三个投影**。在画布拖一条线、在 Explorer 改个名、在 Inspector 加个属性——
> 都写同一份内存 Spec，另外两面板即时重渲染（P1）。

---

## 四、核心画布：本体图（Ontology Graph）

画布是"专业·简洁·可视化"的主战场。它不是通用流程图，而是**本体专属的 ER 式关系图**。

### 4.1 图元语言（一眼可辨的视觉编码）

| 元素 | 图元 | 视觉编码 |
| --- | --- | --- |
| **对象类型** | 圆角矩形卡片 | 顶部色条（类型自定义 color）+ 图标 + displayName + apiName（小字 mono）；卡内列**关键属性**（主键 `◇PK`、标题 `⌾`、索引 `⚡`），其余属性折叠为"+N more" |
| **属性** | 卡内行 | 主键行置顶加 `◇`；必填加 `*`；已建索引加 `⚡`；语义类型（金额/百分比…）小徽标 |
| **关系类型** | 连线 | 实线；端点符号表基数（`1—`、`—∈`(多)、`—◆`(组合)）；线中标签=关系 displayName + role；箭头指向 B 端 |
| **接口** | 虚线菱形/胶囊节点 | `«interface»` 前缀；对象类型 `implements` 它 → 虚线挂接 |
| **状态** | 卡片描边 | Experimental=琥珀虚线；Active=绿实线；Deprecated=灰+删除线标题 |

> 层级关系（自关联 `OneToMany`，如组织树/BOM）用**自环回连线 + `⤴` 标记**，与普通关系区分（呼应后端复用
> `cmx-hierarchy`）。

### 4.2 画布交互（直接操作，P2）

| 操作 | 手势 | 结果 |
| --- | --- | --- |
| 平移 / 缩放 | 拖空白 / 滚轮（或 `－/＋`） | 视口移动；缩放带**语义细节层级**：缩小只显卡片名，放大显属性 |
| 选中 | 点节点/边 | 高亮 + 打开 Inspector 对应 Tab；Explorer 同步高亮 |
| 移动节点 | 拖卡片 | 更新布局坐标（存入 `_layout`，见 §9.3） |
| **建关系** | 从卡片右缘连接点拖橡皮筋线到另一卡片 | 落点弹**轻量关系速建气泡**（apiName/基数/角色），确认即新增 LinkType（§7） |
| **建对象类型** | 双击空白 / `[+对象]` | 新卡片就地命名（apiName 内联输入）→ Inspector 补全 |
| 加属性 | 卡片底 `+` 或 Inspector | 卡内新增属性行（§6） |
| 框选 / 分组 | 拖选多个 → 右键"建分组" | 大本体分域（对齐 DbSchema 分组范式，见 §4.4） |
| 自动布局 | `[自动布局]` | 分层/力导算法排布（关系少用分层、稠密用力导） |
| 删除 | 选中 `Del` | 删元素 + 演进安全守卫（§10） |

### 4.3 校验即时可见（P4）

画布是错误的第一现场：

- **成环拦截**（接口继承、组合关系）：拖线若致环，橡皮筋变红 + 落点拒绝（复用 `wouldCycle` 思路）。
- **悬空引用**：关系一端指向不存在/已删对象类型 → 该边红色虚线 + `⚠`。
- **缺主键**：对象类型无主键 → 卡片角标 `⚠ 无主键`。
- **顶栏校验徽标**：`✓ 全部合法` 或 `⚠ 3 处问题`，点开=问题清单（点条目跳画布定位）。

### 4.4 驾驭大本体（简洁不等于只能小）

- **分组（Domain）**：把对象类型圈进"财务域/供应链域"分组框，可折叠为单个聚合节点。
- **多视图**：同一对象类型可出现在多张"视图"里（面向不同受众切片），呼应 DbSchema"一模型多视图"。
- **聚焦模式**：选中一个对象类型 → `聚焦` 只显示它 + 一跳邻居（Search-Around 式浏览），大图不糊。
- **迷你地图**：右下角 minimap，大图快速定位。

---

## 五、Inspector：右侧内联编辑器

Inspector 是"精确"的家。选中什么，它就变成什么的强类型编辑器。分 Tab 对齐 Palantir OMA 的
object-type overview 分区。

### 对象类型 Inspector（Tab）

| Tab | 内容 |
| --- | --- |
| **概览** | apiName（稳定锚，改名有守卫）· displayName（i18n 双语）· 描述 · 图标选择器 · 颜色 · 状态（Experimental/Active/Deprecated）· 主键选择（下拉，来自属性）· 标题属性选择 |
| **属性** | 属性表格编辑器（§6）——最高频，重点打磨 |
| **关系** | 该对象类型参与的关系列表（可跳转/新建）；显示方向与基数 |
| **动作** | 挂在该对象类型上的动作类型（可新建/编辑，§8） |
| **数据** | O2 已物化对象计数 + "在对象浏览器打开"入口（连通后端 O2 `oo_*`） |

其余六类元素（关系/接口/共享属性/动作/函数）各有精简 Inspector，字段一一对应后端 def（§14）。

---

## 六、属性编辑器：本体定义的最高频交互

改属性是本体定义 80% 的操作。它必须**快、内联、可批量、强类型**。设计为**卡内可编辑表格**（不是弹窗）：

```
属性 (Customer)                                    [+ 加属性] [批量▾]
┌──┬───────────┬────────────┬────┬────┬──────────┬──────────────┬──┐
│⣿ │ apiName   │ 类型        │主键│必填│ 索引     │ 语义类型      │  │
├──┼───────────┼────────────┼────┼────┼──────────┼──────────────┼──┤
│⣿ │ id        │ long     ▾ │ ◉  │ ✓  │          │              │🗑│  ← 拖 ⣿ 排序
│⣿ │ name      │ string   ▾ │ ○  │ ✓  │ ⚡ 已索引 │              │🗑│
│⣿ │ region    │ string   ▾ │ ○  │    │ ⚡        │              │🗑│
│⣿ │ amount    │ decimal  ▾ │ ○  │    │          │ 金额 (money) ▾│🗑│
│⣿ │ createdAt │ timestamp▾ │ ○  │    │          │              │🗑│
└──┴───────────┴────────────┴────┴────┴──────────┴──────────────┴──┘
       从共享属性引用：[currencyCode ▾] 一键加入（继承标准类型+语义）
```

**要点**：

- **内联即改（P3）**：apiName 单击改（带合法性即时校验，非法红框）；类型下拉即选；勾选即切必填/索引。
- **主键单选（◉/○）**：整列单选，改主键触发演进守卫（§10）。
- **拖拽排序**：`⣿` 拖动改属性顺序（存 `ord`，影响卡片与前端展示顺序）。
- **语义类型下拉**：复用 cmx-meta-data semanticType（金额/百分比/邮箱/电话…），驱动后续渲染与校验。
- **引用共享属性**：一键从 SharedPropertyType 拉入标准字段（币种/国家码），继承类型+语义，避免各自定义。
- **结构体/数组属性**：`struct`/`array` 类型行可展开子表（嵌套属性），对齐 OSv2 struct 属性。
- **渲染/索引提示**（对齐 OMA render hints）：`isIndexed` 勾选即建 O2 搜索索引；语义类型即渲染提示。
- **批量**：多选属性 → 批量改必填/删除。

> 属性编辑器直接映射后端 `PropertyTypeDef`（apiName/baseType/required/isIndexed/semanticType/
> sharedProperty/marking/ord）。每次编辑即时结构校验（重名、非法 apiName、主键存在性）。

---

## 七、关系定义：在画布上"拉一条线"

关系是本体高于"一堆表"的关键。定义关系的最专业方式=**在画布上从 A 拖到 B**，落点即成边，再补精确参数。

**交互流**：

1. 悬停对象类型卡片 → 右缘出现**连接点**（`○`）。
2. 从连接点拖出橡皮筋线 → 拖到目标对象类型卡片（成环则红色拒绝）。
3. 落点弹**关系速建气泡**（不打断心流，就地填）：

```
   新建关系  Customer ──▶ Order
   ┌─────────────────────────────────┐
   │ apiName  [customerPlacesOrder ] │  ← 自动建议 camelCase
   │ 基数     [ 1:N ▾ ]              │  ← 1:1 / 1:N / N:M
   │ A→B 角色 [ places       ]       │
   │ B→A 角色 [ placedBy     ]       │
   │ 落存储   ⦿外键 ○中间表 ○关系对象 │  ← backing（§14）
   │            [取消]  [创建关系]    │
   └─────────────────────────────────┘
```

4. 确认 → 画布出现带基数符号的边；Inspector 可继续精修（描述、状态、边属性）。

**基数的视觉语言**（端点符号，一眼读懂）：`1—` 一端 · `—<` 多端（鸦爪）· `—◆` 组合 · `⤴` 自关联层级。

> N:M 关系与"携带属性的关系"（Intermediary，如"参与"带角色/工时）→ 边中央显 `◆` 徽标，点开可编辑边属性。

---

## 八、动作 / 函数：图元 + 专用编辑器

动作（动词）与函数（计算）也是定义的一等公民，但它们"挂在对象上"，不占主图节点，避免图爆炸。

- **图上呈现**：对象类型卡片底部一排**能力徽章**——`⚡3 动作` `ƒ2 函数`。点徽章 → Inspector 切到对应 Tab
  列表；不喧宾夺主。
- **动作类型编辑器**（Inspector 内，§6.6 后端 def）：参数（绑对象/对象集/标量）· 编辑规则（可视化选
  "创建/修改/删除对象、增删关系"）· 校验（内嵌 FEEL 编辑，复用 rules 决策表的格内 FEEL + gap/overlap）·
  副作用（选流程定义/通知/webhook/事件——对齐后端 `SideEffect`）。
- **函数编辑器**：运行时（FEEL/Rhai/Wasm/Native）· 用途（Query/DerivedProperty/Validation/Aggregation）·
  输入（可吃对象/对象集）· 函数体（FEEL 表达式框 / Rhai 代码框，带语法高亮）· 输出类型。
- **派生属性的图上暗示**：若某属性由函数派生（DerivedProperty），属性行加 `ƒ` 前缀，与存储属性区分。

> 动作/函数的"逻辑编辑"直接复用规则引擎已有的 FEEL 编辑器与决策表设计器资产，不重造。

---

## 九、双向同步：图 ⇄ 规格（Spec）⇄ 后端

这是"图为先、规格为真"（P1）的技术心脏。三层单向真相 + 双向编辑。

### 9.1 单一内存真相：OntologySpec

前端持有一份规范化的 **OntologySpec**（= 七类元素定义的规范化集合 + 布局元数据）。Explorer / 画布 /
Inspector 都是它的**只读投影 + 编辑命令发起者**。任一处编辑 → 派发命令改 Spec → 三处 diff 重渲染。

```
        编辑命令 (addProperty / connectLink / renameType / moveNode ...)
Explorer ─┐                                        ┌─ 画布 (节点/边/布局)
          ├──────▶  OntologySpec (单一真相)  ──────┤
Inspector ─┘        + 即时结构校验 + 脏标记          └─ Inspector (强类型表单)
```

### 9.2 与后端的粒度化保存

- **草稿态**：编辑改内存 Spec + 标脏；**按元素粒度**保存（改一个对象类型 → `POST /object-types` 一次），
  不是整体大提交（呼应 O1 已有的 per-type upsert 端点）。乐观锁：`updatedAt` 当 etag，冲突走对话框。
- **发布态**：`[发布]` → 后端 `POST /publish` 生成不可变版本快照（O1 已实现，rev=xxhash64）。顶栏版本徽标
  从"草稿·未保存"→"已发布 vN"。
- **校验**：前端结构校验（即时）+ 后端权威校验（保存时返回结构化 violations，就地红标——复用 DCT/DOC
  错误展示层范式）。

### 9.3 布局持久化（P6：布局随规格存活）

节点坐标/分组/视图=**表现层元数据**，与逻辑定义分离，但需随本体存活（重开图不散架）。存后端对象类型的
`cmxOrigin`/专用 `om_layout` 侧表（或对象类型 def 的 `_layout` 扩展字段，后端忽略语义只存字节）。呼应
DbSchema"positions/groups 存进项目文件、可离线重开"。

> 双向同步的另一半——**代码视图**：可选提供一个"规格 DSL/JSON 视图"（只读或可编辑），与画布互为投影
> （dbdiagram/Prisma Editor 范式）。首版给**只读 Spec JSON 抽屉**（便于复制/审阅/diff），可编辑 DSL 后置。

---

## 十、演进安全：编辑守卫与破坏性变更提示

Palantir 反复强调"编辑对象类型不是纯装饰，可能让应用崩"。本方案把**演进安全**做成一等交互（P5）：

| 破坏性操作 | 守卫 | 影响面预览 |
| --- | --- | --- |
| 改 **apiName** | 二次确认；提示"apiName 是稳定锚，下游 OSDK/动作/引用将断" | 列出引用该类型的关系/动作/函数 |
| 改 / 删 **主键** | 强警示 | 已物化对象（O2 `oo_*` 计数）将需迁移 |
| **删属性** | 若属性被动作/函数/关系引用 → 阻止或强确认 | 列引用点；提示"曾接受编辑的属性删除风险"（对齐 OMA edit-safety 高亮） |
| 改**关系基数** | 确认 | 1:N→N:M 影响已建边与查询 |
| 改属性**类型** | 确认 | 提示"动作/函数中该属性的期望类型需同步更新"（对齐 OMA 依赖提示） |
| 删对象类型 | 强确认 | 连带其属性/关系/已物化对象 |

**呈现**：破坏性操作 → **专业对话框**（复用 cmx-message-dialog 三级别）+ 影响面清单 + "改为废弃
（Deprecated）而非删除"的更安全建议（对齐后端"废弃→迁移→移除"三步演进）。状态机 `Experimental → Active →
Deprecated` 在 Inspector 顶部显式可切，把"能不能安全改"与生命周期绑定（Experimental 期随便改，Active 后守卫升级）。

---

## 十一、低摩擦入口

不要求用户从空画布一笔一画。三条快速起步路径（对齐 Lucidchart/dbdiagram 的低摩擦入口共识）：

1. **从 cmx-model 导入**：一键把既有 **DOC**（主从实体图）导入为对象类型 + 组合关系、**DCT**（字典）导入为
   参照对象类型（枚举）。本体成为既有元数据的"语义投影"，不推倒重来（后端方案已列此能力）。
2. **AI 生成骨架**（可选，后置）：自然语言描述业务（"客户下单，订单含商品，商品属于类目"）→ 生成对象/关系
   草图 → 人工精修。对齐 Lucidchart"prompt 生成 ERD"。**NL→模型，非 NL→代码**（呼应你低代码演进方案主张）。
3. **键盘流速建**（进阶）：`o` 建对象、`p` 加属性、`l` 拉关系、`/` 搜索定位——dbdiagram 式键盘优先，专业用户
   全键盘建模。

---

## 十二、视觉系统：令牌、图元语言、双主题

- **双主题令牌**：严格走你验证过的"UI5 在 `:root` 重定义 `--sap*` 穿透 shadow + `--onto-*` 令牌锚 `--sap*`
  + hex 兜底"做法（见 `portal-native-page-dual-theme-token-pattern`）。裸 hex 不翻，一律走令牌。
- **图元着色**：对象类型顶部色条用类型自定义 color（图谱着色，后端 def 已有 `color` 字段）；边/接口/状态用
  语义色（关系=中性、接口=紫、Experimental=琥珀、Active=绿、错误=红）。参照 dataviz skill 的品牌中性色板，
  保证明暗双主题下对比度达标。
- **简洁的密度**：默认"关系视图"只显卡片名 + 主键；放大或聚焦才显全属性。信息**按需展开**，不一次糊满。
- **专业感细节**：mono 字体显 apiName（技术锚）、基数用规范 ER 符号、状态用描边而非填充（不抢注意力）。

---

## 十三、组件抉择：复用 vs 新建 `@cmx/ontology-graph`

你已有 `@cmx/decision-graph`（独立 Web Component，拖拽节点/拉线/防环/SVG DAG/`node-select` 宿主编辑）。
它与本体图**神似但不等价**：

| 维度 | `@cmx/decision-graph` | 本体图所需 |
| --- | --- | --- |
| 拓扑 | DAG（input→output 左右分层，**无环**） | 一般图（关系可双向、可自环层级、**接口继承才防环**） |
| 节点 | 简单类型节点 | 富卡片（属性列表/主键/徽章/色条/状态描边） |
| 边 | 无向连接 | 有基数符号 + 角色标签 + 方向 |
| 布局 | 分层 BFS | 分层 + 力导 + 分组 + minimap |
| 宿主编辑 | `node-select` → 宿主渲染 | 相同范式可复用 |

**判决**：**新建 `@cmx/ontology-graph`**（独立 Web Component，clean-room），但**大量借鉴** decision-graph 的
成熟骨架——自定义元素契约（`setGraph/getGraph`、`node-select`/`edge-add` 事件、`getModel()` 逃生舱）、拖拽/
拉线/`wouldCycle`、shadow DOM + 双主题、tsc+esbuild 构建与 `sync-component.sh` 交付管线。**对齐而非改造**：
decision-graph 继续服务规则引擎，本体图是其"富卡片 + 基数边 + 分组"的兄弟组件。两者共享设计语言，不共享代码
（避免把 ER 语义塞进 DAG 核，重演"领域逻辑不进通用图核"的教训）。

> 组件契约（示意）：`<cmx-ontology-graph>` · `setSpec(ontologySpec)` / `getSpec()` · 事件
> `type-select` / `link-add` / `property-add` / `spec-change` / `connect-rejected` · 逃生舱 `getModel()`。
> 富卡片渲染 + 基数边 + 分组 + minimap 为其增量。

---

## 十四、与后端契约的映射

前端每个编辑动作，精确落到 O1/O2 已实现的端点与 def（无缝对接，不需要后端改）：

| 前端动作 | 后端端点（O1/O2 已实现） | def / 字段 |
| --- | --- | --- |
| 建/改对象类型 | `POST /object-types` | `ObjectTypeDef`（apiName/displayName/primaryKey/titleProperty/properties/status/color/icon） |
| 加/改属性 | 同上（对象类型内嵌 properties） | `PropertyTypeDef`（apiName/baseType/required/isIndexed/semanticType/sharedProperty/marking/ord） |
| 拉关系 | `POST /link-types` | `LinkTypeDef`（apiName/cardinality/objectTypeA/B/roleA/B/backing） |
| 接口 / 共享属性 | `POST /interfaces` · `POST /shared-properties` | `InterfaceDef` · `SharedPropertyTypeDef` |
| 动作 / 函数 | `POST /action-types` · `POST /functions` | `ActionTypeDef` · `FunctionDef` |
| 即时校验 | `POST /object-types/validate` + 前端本地校验 | 结构化 violations |
| 全局清单（Explorer/画布初始） | `GET /manifest` | `OntologyManifest` |
| 发布 / 版本 | `POST /publish` · `GET /versions` | 不可变快照 rev |
| 顶栏统计 | `GET /stats` | 各类型计数 |
| "在对象浏览器打开"（数据 Tab） | O2 `POST /object-sets/load`、Search-Around | 连通对象层 |

> 布局元数据（坐标/分组/视图）是唯一"前端新增、后端只存不解释"的部分——存对象类型 def 的扩展字段或
> `om_layout` 侧表（§9.3）。其余全部命中现有契约。

---

## 十五、布局线框（ASCII）

**建模态·关系视图（默认）**：

```
┌ cmx-ontology · 客户域本体 ────────── 草稿·未保存 ⚠2 ── [校验] [发布] [导入▾] [🌓] ┐
├─Explorer──┬────────────── 本体图画布 ─────────────────────────┬── Inspector ─────┤
│🔍_______  │                                                    │ Customer         │
│▾对象类型3 │   ┌─────────────┐  places (1:N)   ┌───────────┐    │ [概览][属性][关系]│
│  Customer●│   │▉ Customer    │─────────────▶  │▉ Order     │    │ ─────────────────│
│  Order    │   │ ◇ id     PK  │                │ ◇ oid  PK  │    │ apiName          │
│  Product  │   │ ⌾ name       │                │   no       │    │ [Customer______] │
│▾关系类型1 │   │ ⚡ region     │                │ ƒ total    │    │ 显示名 [客户____]│
│  places   │   │   +2 more    │                └───────────┘    │ 主键 [id ▾]      │
│▾接口1     │   └──────┬──────┘                                   │ 标题 [name ▾]    │
│  Locatable│      implements ┊                                   │ 状态 [Active ▾]  │
│▾共享属性1 │   ┌─────▽───────┐                                   │ 颜色 [▉]  图标[◇]│
│  currency │   │«Locatable»   │                                  │                  │
│▾动作1 函数1│  └─────────────┘                                   │ [保存] [废弃]    │
│[+新建▾]   │  [⚙自动布局][+对象][+关系][适应][－ 100% ＋]  ▣minimap│                  │
└───────────┴────────────────────────────────────────────────────┴──────────────────┘
```

**属性 Tab（Inspector 展开态，最高频）**：见 §6 的卡内表格线框。

---

## 十六、落地路线 UI0–UI5

在后端 O0–O2 已绿的地基上，前端分阶段交付（每阶段真机 CDP 可测）：

| 阶段 | 交付 | 验收 |
| --- | --- | --- |
| **UI0 三面板骨架** | Explorer 树 + 空画布 + Inspector 壳 + 顶栏；接 `GET /manifest` 渲染现有本体 | 打开即见 O1 建的客户/订单本体（列表态） |
| **UI1 本体图只读** | `@cmx/ontology-graph` 组件（富卡片 + 基数边 + 接口挂接 + 自动布局 + minimap）；点选联动 Inspector | 客户—订单关系图可视；点节点出 Inspector |
| **UI2 对象类型 + 属性编辑** | 对象类型 Inspector（概览 Tab）+ 属性卡内表格（内联/拖排/语义类型/引用共享属性）；接 `POST /object-types` | 画布建对象类型、加属性、存草稿，字节回读一致 |
| **UI3 关系直接操作** | 画布拉线建关系 + 速建气泡 + 基数符号 + `wouldCycle`；接 `POST /link-types` | 拖 Customer→Order 成边并落库；成环被拒 |
| **UI4 演进安全 + 校验 + 发布** | 即时结构校验红标 + 破坏性变更守卫 + 影响面预览 + 顶栏发布 → 版本徽标 | 改主键弹守卫；发布出 vN；非法定义拦下 |
| **UI5 动作/函数 + 低摩擦入口** | 能力徽章 + 动作/函数编辑器（复用 FEEL 编辑器）+ 从 cmx-model 导入 | 挂一个动作/函数；DOC 一键导入为对象类型 |

> 每阶段遵循既有纪律：门户联邦挂载（`portal.onto.designer` 视图 + 反代 `/api/onto/*` + 白名单）、native
> 页 rev 字节一致、CDP 前端测试。菜单部署 `cmx_menu`（注意"菜单 id 撞 PK / whitelist 漏项 → 空数据"两坑）。

---

## 十七、参考

- [Ontology Manager 概览 · Palantir](https://www.palantir.com/docs/foundry/ontology-manager/overview)
- [编辑对象类型属性 · Palantir](https://www.palantir.com/docs/foundry/object-link-types/edit-properties)
- [编辑对象类型 · Palantir](https://www.palantir.com/docs/foundry/object-link-types/edit-object-type)
- [允许用户编辑对象与关系 · Palantir](https://www.palantir.com/docs/foundry/object-link-types/allow-editing)
- [对象与关系类型 · 类型参考 · Palantir](https://www.palantir.com/docs/foundry/object-link-types/type-reference)
- [Prisma Editor（图 ⇄ schema 双向编辑）](https://prisma-editor.vercel.app/)
- [DbSchema · 图设计/分组/离线项目文件](https://dbschema.com/documentation/diagram.html)
- [Lucidchart · 数据库设计/导入/AI 生成](https://www.lucidchart.com/pages/examples/database-design-tool)
- [Top free database diagram tools · Holistics](https://www.holistics.io/blog/top-5-free-database-diagram-design-tools/)
- [Graph 数据 UX 挑战与机会 · Expero](https://www.experoinc.com/insights/blog/minding-the-sharp-edges-ux-considerations-with-graph-data-part-1-the-design-challenges-and-opportunities-of-graph-data)

### cmx 生态内部关联（memory 锚点）

本体总纲 `[[cmx-ontology-palantir-platform-plan]]` · 决策图组件 `[[cmx-decision-graph-component]]` ·
双主题令牌 `[[portal-native-page-dual-theme-token-pattern]]` · 规则引擎决策表设计器
`[[cmx-rulesengine-f3-decision-table-designer]]` · 专业对话框 `[[dialog-help-center-wiring]]` ·
元数据 semanticType `[[cmx-meta-data-rebuild-plan]]` · 菜单管理 `[[menu-manager-two-region-refactor]]`

---

> 下一步（待你确认）：本文为纯设计。认可后建议从 **UI0 三面板骨架 + UI1 本体图只读** 起步——先把
> `@cmx/ontology-graph` 组件（富卡片 + 基数边 + 自动布局）与三面板联动跑通，读 `GET /manifest` 把 O1/O2
> 已建的本体画出来；随后 UI2 属性编辑接 `POST /object-types` 形成建模闭环。是否需要我：①先出
> `@cmx/ontology-graph` 组件的详细 API 契约与图元渲染规格；②补几张高保真 SVG 线框（对齐 docs 图文并茂）；
> ③直接落 UI0+UI1 前端骨架？
