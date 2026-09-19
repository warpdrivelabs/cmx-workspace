# 场景职责收口方案——场景只管成员，关系归底座

> 20260918 · cmx-ontology + 本体工作室（studio / studio-next 两版同修） · 已实施

## 一、需求模型（用户裁决）

| 上下文 | 职责 | 允许的操作 |
| --- | --- | --- |
| **底座（全局总览）** | 唯一建模面：对象、关系（定义+背书）、接口都在这定义 | 新建/修改/删除关系、挂接摘除接口、建对象 |
| **场景（业务切片）** | 底座的只读投影 + 一件事：**选对象** | 引入对象 / 移出对象 / 拖布局 |

场景画布 = 「勾了这几个对象，把它们之间的关系画出来」。关系显示**纯派生**：两端对象都在场景里才画边；对端不在场景的关系，边不画、也**不做任何提醒**（含角标）。场景内不新建关系、不删关系定义。

## 二、改前问题（代码实证）

1. **场景画布拉线新建关系落全局底座**：`link-add → quickLinkDialog → POST /link-types`，场景成了建模入口。
2. **场景画布 Delete 边 = 直删全局关系定义**（所有场景一起失效），风险与心智错位。
3. **场景内对象↔接口拉线挂接/摘除** = 改对象 `implements`（全局定义）。
4. **角标（externalCount）**：断头关系计数 + 补引弹框，与「场景是主观切片」心智冲突——场景外关系不展示也不该提醒。
5. **links 白名单多余**：manual 场景引入对象后其关系不自动显示，须去右栏「可加入场景的关系」逐条加入，违背派生模型。
6. **studio-next 添加对象入口丢失**：M3 重写时 `addMembersDialog` 函数与 `data-act="add-members"` 分派都搬了，唯独按钮渲染点没搬——场景画布无任何添加入口（能删不能加：旧版成员树 ✕ 也在重写中消失）。

## 三、改动清单（已实施）

### 后端 cmx-ontology（crates/cmx-onto-app/src/view_handlers.rs）

- `GET /graph` 投影：**边 = 两端成员在场即派生**（manual 与 auto 统一）；`links` 白名单不再消费。
- 不再计算/返回 `externalCount` / `externalPeers` / `availableLinks`（响应键删除）。
- `resolve_view` 签名去掉白名单位；`meta.linkCount` 恒 0。
- 存量兼容：`members.links` 保留存储不读；`POST /views` 仍接受该字段（清洗逻辑不变），仅投影不消费。

### 前端 studio-next（assets/onto/web/ui-native/onto/studio-next/）

- `panels.js`：画布悬浮工具组（canvasOpsHtml）**恢复「＋ 引入对象」**（场景态 + 编辑态 + 有维护权限时显示，复用现成 addMembersDialog——含「连同直接关联（一跳邻域）」）。
- `canvas.js`：场景上下文拦截 `link-add` / `edge-delete-request` / `implements-request` / `implements-remove-request`，toast 引导回底座画布；**badge-click 补引监听整体删除**；quickLinkDialog 文案更新。
- `inspector.js`：删除「可加入场景的关系」区块（availableLinksBlock）；新增**「场景成员」区块**——场景上下文 + manual + 编辑态显示「移出场景」按钮（与引入对称成闭环；studio-next 左栏无成员树，此为唯一移出入口）。
- `runtime.js`：删除 addLinkToScene 及 `avail-add` 分派；新增 `rm-member-scene` 分派（走现成 removeMember）。

### 前端旧 studio（assets/onto/web/ui-native/onto/studio/，菜单当前入口，同修同口径）

- canvas.js：同款四处拦截 + badge-click 删除 + 文案更新。
- inspector.js：删除 availableLinksBlock。
- runtime.js：删除 addLinkToScene 及分派（旧 studio 左栏成员树 ✕ 移出入口保留不动）。

### vendor 不动

角标由 spec 数据驱动（vendor 组件按 `n.externalCount` 渲染），后端不传字段即不渲染，零 vendor 改动。

## 四、实测记录（20260919，finance_rev 本体 / view-revenue-closure 场景）

| # | 用例 | 结果 |
| --- | --- | --- |
| 1 | graph API：响应无 `availableLinks`、节点无 `externalCount`、边=成员派生 | ✔ |
| 2 | 场景画布节点无角标（截图） | ✔ |
| 3 | 编辑态画布工具组出现「＋ 引入对象」，点击弹框正常（搜索/一跳邻域/引入所选） | ✔ |
| 4 | 引入 2 对象（勾一跳邻域实引 8 个）→ 画布节点+边自动全亮（派生口径生效） | ✔ |
| 5 | 场景内拉线（link-add）→ toast「场景内不可新建关系——关系定义请在底座总览画布拉线创建」 | ✔ |
| 6 | 场景内删边（edge-delete-request）→ toast「…如不想显示该边，请把对端对象移出场景」 | ✔ |
| 7 | 右栏选中对象：仅「关系（N）」区块，无「可加入场景的关系」 | ✔ |
| 8 | 右栏「场景成员 → 移出场景」→ toast 移出成功、场景刷新 | ✔ |
| 9 | 测试引入的成员已清理恢复（场景恢复原 7 成员，version 6） | ✔ |

## 四a、成员派生端到端闭环（20260919 二轮，新建「成员派生验证」空白场景）

| 步骤 | 操作 | 成员 | 边 | 结论 |
| --- | --- | --- | --- | --- |
| ① | 引入 Customer（对端均不在场） | 1 | 0 | 断头关系不显示 ✔ |
| ② | 引入 PickupMaterialBatch | 2 | 1（pickupSoldTo 自动进来） | 关系随成员派生 ✔ |
| ③ | 引入 AccountingJudgment | 3 | 2（+pickupFormsJudgment） | 画布截图三节点两边、无角标 ✔ |
| ④ | 右栏移出 PickupMaterialBatch | 2 | 0（两条边同时消失） | 移出后关系随之消失 ✔ |

测试场景已删除，数据零残留。

### 二轮实测发现并修复的三个存量 bug

1. **引入弹框候选池被场景口径污染**（两 studio 同有）：场景态 `reloadLive` 重拉 manifest 带 `&view=`（R4.2 场景口径，非成员类型从清单剔除）且缓存跨场景残留 → 引入弹框候选只剩「当前/上一场景的成员」，空场景几乎无法引入任意对象。修复：`addMembersDialog` 单独拉全量 manifest（不带 view）作弹框局部数据，不写缓存；`oneHopNeighbors` 支持 linkTypes 入参。
2. **page-kit liveValues 对 ui5-checkbox 取值恒真**：`el.type === 'checkbox'` 对 ui5-checkbox 不成立（type=undefined），落入 `el.value` 分支，而 ui5-checkbox 的 value 默认 `"on"` → 引入弹框「连同直接关联」永不关（勾不勾都带一跳邻域）。修复：判定加 `el.tagName === 'UI5-CHECKBOX'`（page-kit 共享弹层一处修复，全部弹框受益）。
3. **reloadLive 先置 null 后拉取，失败即打空页面**：正打开的场景被外部删除时 `manifest?view=` 404 → catch 后 manifest 停在 null，画布/左栏/目录全空且不自愈。修复：先拉 views（正打开场景不在清单 → 自动回底座并 toast）再拉 manifest，**成功才赋值**，失败保持旧清单（两 studio 同修）。

验证方式：`cargo check` 通过；7 个 JS 文件 `node --check` 通过；全仓 grep 无 availableLinks/externalCount/addLinkToScene 业务残留；onto 服务重启后 API + 浏览器（门户 dev :5173/view/onto-studio-next）实测。

## 五、影响面与注意

- **cmx-ontology 单仓**改动，无下游 path 引用；`cmx-container` 前端资产为真源直读，刷新页面即生效。
- 老 manual 场景此前未显式加入白名单的关系会**自动变多**（派生口径的正确结果）；如嫌多，移出对端对象即可。
- 场景内建模操作为前端拦截，后端 `/link-types` 等接口语义不变（底座全局），其他消费方不受影响。
- 接口清单同步：`documents/20260918_cmx-ontology_全量接口清单与请求参数说明.md` §7 已更新。
