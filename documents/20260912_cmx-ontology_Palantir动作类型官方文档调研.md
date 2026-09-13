# Palantir Foundry Action Type 官方文档调研

> 调研日期：2026-09-12
> 资料来源（Palantir 官方文档，Foundry → Ontology → Action types 分区）：
> 1. [Overview（概览）](https://www.palantir.com/docs/foundry/action-types/overview/)
> 2. [Getting started（入门）](https://www.palantir.com/docs/foundry/action-types/getting-started/)
> 3. [Explore other action types（动作类型与规则全景）](https://www.palantir.com/docs/foundry/action-types/explore-action-types/)
> 4. [Use actions（平台内使用）](https://www.palantir.com/docs/foundry/action-types/use-actions/)
> 5. [Test run（测试运行）](https://www.palantir.com/docs/foundry/action-types/test-run/)
> 6. [Rules（规则参考）](https://www.palantir.com/docs/foundry/action-types/rules/)
>
> 本文只整理 Palantir 官方事实；与我方 cmx-ontology 的差距分析与演进方案见姊妹篇
> `documents/plans/20260912_cmx-ontology_动作类型对标Palantir演进方案.md`。

---

## 一、Action Type 的本体定位（Overview）

### 1.1 一等公民，独立定义

- **Action（动作）** 官方定义：*"a single transaction that changes the properties of one or more objects, based on a user-defined logic"*——基于用户自定义逻辑、修改一个或多个对象属性的**单次事务**。
- **Action Type（动作类型）**：对一组可一次性执行的变更（对象、属性值、链接的 edits）的定义，并包含提交时伴随的 side effect 行为。
- 在 Ontology Manager 中，Action Type 与 **Object Type / Link Type / Interface / Shared Property / Struct / Value Type** 并列，是**独立顶级定义元素**，拥有自己的左侧导航分区、自己的 RID（Action RID）、自己的创建向导。
- Action Type **不强制**关联任何对象类型：可以只通过 API / 函数调用存在；对象类型也可以一个 Action 都不建，本体照常只读使用。

### 1.2 与对象类型的关联方式

- 通常通过**对象引用参数（object reference parameter）**指定"主对象"作为上下文（如修改订单的 Action，主对象是 Order）。
- 通过多个参数，一个 Action 可以**同时作用于多个对象类型**（如同时改订单、更新客户、扣减库存）。
- 即：不是"挂在某个对象类型下的子元素"，而是"作用于一个或多个对象类型的独立能力"。

### 1.3 写回与一致性

- 用户执行 Action 后，变更提交到 Ontology 并反映到所有应用；带用户编辑的最新对象数据保存在对象类型的 **writeback dataset（写回数据集）**（Object Storage v1 所需；v2 通过 edits toggle 开启）。
- 同一套 Action 逻辑与验证可在**所有面向用户的应用中复用**，保证对 Ontology 的编辑一致性——这是 Palantir 推崇"经 Action 编辑、反对绕过 Action 直改"的核心理念。

### 1.4 Action Type 的构成要素（以官方 Assign Employee 示例）

| 要素 | 英文 | 作用 |
| --- | --- | --- |
| 参数 | Parameters | 表单输入（如新角色 role），可带约束 |
| 规则 | Rules | 定义如何创建/修改对象、建立/删除链接等 |
| 提交标准 | Submission Criteria | 控制何时允许提交的前置条件 |
| 副作用 | Side Effects | 通知（Notifications）、Webhook、触发构建等 |
| 测试运行 | Test Run | 正式使用前验证行为 |
| 权限 | Permissions / Read and write authorizations | 控制谁可执行/修改 Action |

治理与运维周边（文档导航明确列出的能力）：Action log / Action metrics（监控与指标）、**Undo or revert Actions（撤销/回退）**、**Branching action types（分支管理，配合 Ontology branching 与 proposal 评审）**、Dropdown security considerations、参数性能考量。

---

## 二、入门流程（Getting started）

官方教程以 Demo Ticket 对象类型（属性：Ticket ID / Title / Priority / Status）走通全流程：

### 2.1 创建（Ontology Manager 创建向导，4 步）

1. **Action type step**：选 Object 标签页 → 选对象类型（Demo Ticket）→ 在 **Object actions** 下选动作（**Modify object(s)**）。
2. **Mapping step**：通过 Add property 添加要修改的属性（Priority）。
3. **Metadata step**：填 Action type name。
4. **Create** 创建，进入详情视图（Overview 加 Description、Rules 加更多规则）。

**关键机制：规则自动派生参数**——选择 Modify object(s) 后，**Ticket** 与 **Priority** 参数根据 Rule 自动创建，无需手填。

### 2.2 参数约束（Parameters）

- 选中 Priority 参数，把约束从 **User input** 改为 **Multiple choice**，添加 P0/P1/P2 可选值——修改参数约束会**联动影响规则产生的编辑结果**。
- 参数体系还包括：默认值（Set parameter default value）、下拉结果过滤、参数配置覆写（override）、性能考量。

### 2.3 提交标准（Submission Criteria）

- 位置：**Security & Submission Criteria** 标签页 → Execution 部分选 **Condition** 新建。
- 用 **Parameter condition** 模板：对 **Ticket 对象参数的 Status 属性** 设条件，操作符 **is** 精确匹配 `Open`，附 **failure message**（失败提示）。
- 效果：只允许对 Open 状态的 ticket 改优先级；对已关闭 ticket 提交即失败。
- **注意：条件引用的是对象的当前属性值**（对象状态参与校验），不是只有表单参数。

### 2.4 发布与界面呈现（Object View 按钮）

- 进入对象（Demo Ticket One）的 **Object View** 编辑 → 顶部加 **Actions widget** → Add Item → 粘贴 **Action RID** → 命名按钮（如 "Change Ticket Priority"）→ 保存并发布 Object View。
- **默认行为**：action 表单把所有参数（含 Ticket）显示为表单字段，但 Action 并不知道要把当前对象填进 Ticket 参数。
- **当前对象绑定**：在参数的 **Default value** 中，value type 选 **Environment variable → Current object**，display option 改 **Hidden**（隐藏 Ticket 字段，防止用户改别的 ticket）。
- 应用：打开 open ticket → 点按钮 → 表单弹出（Priority 字段上能看到配置的 submission criterion）→ Submit → Object View 更新为新优先级。

### 2.5 测试运行

- 在 Ontology Manager 中 test run，验证 submission criteria、rules、resulting edits，之后再在应用中铺开。

### 2.6 编辑前提与冲突解决

- Object Storage v1 需创建 writeback dataset；v2 需开启 edits toggle（v1 已计划废弃）。
- 冲突解决策略：Strategy 1 **Apply user edits**（默认）；Strategy 2 **Apply most recent value**。

---

## 三、动作类型与规则全景（Explore other action types）

### 3.1 规则配置位置

- 创建向导（配第一条规则）；或对已有 action type 在 **Rules 标签页 → Add new rule** 追加。
- 一个 action type 可**组合多条规则**；唯一例外：**Run function 规则不能与其他 Ontology 规则组合**（函数代码本身能表达一切）。

### 3.2 规则类型速查表（官方原文）

| 目标 | 规则（Rule） |
| --- | --- |
| 创建新对象 | Create object |
| 用户可能不提供对象时创建/修改 | Create or modify object |
| 删除现有对象 | Delete object |
| 建立/解除对象关系 | Create link / Delete link |
| 表达规则无法描述的逻辑 | Run function |
| 请求外部系统（编辑后） | Webhook |
| 任何编辑**前**调用外部系统 | Writeback Webhook |
| 通知用户 | Notification |
| 应用时重算数据集 | Schedule |
| 提交场景沙箱暂存编辑 | Apply scenario |
| 操作任何实现接口的对象 | Interface rules |

### 3.3 各规则要点

1. **Create object**：填主键（必填属性），其他属性可选；每个属性自动创建同名参数并映射。映射选项见 §四。
2. **Create or modify object**：修改对象引用参数提供的对象；未提供对象时用自动生成的唯一 ID 或用户提交的主键**创建新对象**（upsert 语义）。
3. **Delete object**：删除对象引用参数提供的对象；**不能引用同一 action 内创建的对象**。
4. **Create link / Delete link**：仅适用于**多对多** link type；一对一/一对多关系存外键属性，应用 Modify object 规则设/清外键。可在单条 action 中**同时创建对象及其多对多链接**（Create object 规则下 Add link）。
5. **Run function**：调用已发布的 Ontology edit function，选函数与版本；函数每个输入自动成为 action 参数（可像普通参数一样约束）；默认锁定版本，可开 **auto upgrades** 按版本范围运行时解析。**不能与其他 Ontology 规则组合**。
6. **Webhook**：编辑应用**后**发请求；一个 action 可含多个；**失败不展示给最终用户**（用户可能已看到成功消息）。
7. **Writeback Webhook**：在**任何规则求值前**发送；请求失败则**不应用任何编辑**，用户看到失败信息；一个 action 只能一个；**其输出参数可被后续规则使用**（外部系统参与决策）。
8. **Notification**：接收人可以是固定用户集**或从对象参数属性派生**；内容为引用 action 参数的模板；按接收人偏好经平台内推送、邮件或两者发送；在所有编辑应用后发送，但**内容基于编辑前的 Ontology 状态**生成。
9. **Schedule**：action 应用时触发 schedule 的数据集重算；Ontology 编辑在构建开始后应用，不等构建完成；可传参数值并把 schedule run RID 记录到对象。
10. **Apply scenario**：把 scenario 沙箱中的暂存编辑作为一个事务提交（beta）；需要 Scenario 参数持有 scenario RID。
11. **Interface rules**（5 种）：Create/Modify/Delete object(s) of interface、Create/Delete link(s) on object(s) of interface——目标是**任何实现该接口的对象类型**（多态），modify/delete 用 interface reference parameter。
12. **Struct 属性**：取值来自 struct parameter，嵌套字段镜像属性字段，**必须映射每个字段**。

### 3.4 多规则组合语义（Rules 文档补充）

- Actions backend 将多条规则**编译为每个对象的一条编辑**（Add / Modify / Delete object(s)）。
- **规则顺序影响结果**：两条规则先后把同一属性改为 "A"、"B"，最终编辑为 "B"。
- **无效组合（Invalid combinations）**：
  - 对象不能在 add 或 modify 之前被 **delete**；
  - 对象不能在 add 之前被 **modify**；
  - 同一次表单提交中对象**不能被创建两次**。

---

## 四、规则取值映射（Rules: Values and parameters）

创建/修改对象或链接时，每个属性可映射到以下来源之一（**链接规则只能用对象引用参数**）：

| 来源 | 英文 | 说明 |
| --- | --- | --- |
| 来自参数 | From parameter | 与属性同类型的已有参数；**新增属性到规则时默认自动创建同名参数并映射** |
| 对象参数属性 | Object parameter property | 已有 object reference parameter 的某个属性，类型须匹配映射目标 |
| 静态值 | Static value | 仅存在于 Rules 部分；提交时用户不可更改 |
| 当前用户/时间 | Current User / Current Time | String 与 timestamp 属性可用提交时的当前用户/时间；提交时不可交互，也不能用于 action type 其他部分 |

---

## 五、平台内使用（Use actions）

Action types 可无缝集成到 Foundry 各应用。术语：**single action type** = 使用单个对象引用参数的 action；**bulk action type** = 使用对象引用**列表**参数的 action。

### 5.1 Object Views（Actions section）

- 可将任意 action 添加为 section 内按钮；自定义 label 与 color。
- 点击行为默认打开表单，可改为**"用默认值立即执行（if valid）"**。
- 可指定 non-visible parameter 无效时按钮 **hidden 还是 disabled**（可见参数无效时用户可开表单修正，不可见参数无效则只能藏/禁按钮）。
- 每个参数可给默认值：当前对象的 property value，或 "local" 值（current user / current timestamp / current object / 手动输入）。
- 可逐参数覆写可见性（visibility override）。
- 由此可把同一个通用 action 做成多个结构化版本，例如 "Delay 10 minutes"、"Delay 30 minutes"。

### 5.2 Object Explorer（自动出现，零配置）

Action 自动显示在三个位置：

1. **Exploration View 的 Actions dropdown**（右上）：基于当前对象集合自动填充适用的 **bulk actions**；
2. **Object View 的 Object Actions dropdown**（右上）：基于当前对象自动填充适用的 single + bulk action types；
3. **Object View 的 Linked objects view section**（顶部）：基于选中对象自动填充。

限制：bulk 上下文中**只显示接受正确类型 object list parameters 的 action**——按参数类型匹配自动筛选。

### 5.3 Workshop（Button group widget）

- 配置项与 Object Views 相同，另有：三种 layout、按钮显示选项（左右图标、minimal styles、tag styles）、按钮还可触发 Workshop event / URL / object set export。
- 差异：default value 可以是 **variable**（链接 Workshop 变量）、current user、current timestamp。

> 本页不含 Ontology SDK / API batch actions / AIP 内容（另有 API Reference 与 OSDK 章节）。

---

## 六、测试运行（Test run）

### 6.1 定位与入口

- 在 Ontology Manager 中**模拟** action type，在终端用户实际使用前验证行为：根据提供的参数值评估 action，返回**会产生的编辑（edits）+ 详细的执行分解（execution breakdown）**。
- 入口：action form preview 的 **Test run** 标签页（仅 form layout 可用，table layout 不支持）。
- 权限：能看到该 action type 配置即可运行测试。

### 6.2 测试与正式提交的等效性

- 在**当前 Ontology branch** 上评估；以**你的权限**执行；强制与正式提交相同的 **object security** 与 **submission criteria**。

### 6.3 结果展示

- **Proposed changes**：将创建/修改/删除的对象与链接；属性变化以**当前值 vs 建议值**对比展示；无编辑时显示 "No proposed changes"。
- **Details** 标签页：
  - **Execution log**：逐步分解——metadata 加载 → 依赖验证 → submission criteria → 参数验证 → edits 计算——用于理解 action 为何成功/失败；
  - **Side effects 预览**：如 notifications，可预览将生成的内容与接收者；
  - **Referred entities**：运行期间引用的 object types / link types / interface types / functions。

### 6.4 写与不写的边界（重点）

- **编辑不落库**：*"The edits produced by a test run are not applied to your Ontology."*
- **但外部调用会真实执行**：为得出准确结果，test run 会执行 action 所需的 functions 与 calls（规则中的 functions、生成通知正文/接收者的 functions、生成 webhook payload 的 functions、**writeback webhooks**、访问外部资源的 functions），**可能影响外部系统**；Foundry 会列出执行来源并要求 **Confirm** 后才继续。

### 6.5 失败排查与限制

- 错误分两类：**Admin-facing errors**（管理员调试技术细节）与 **End-user-facing errors**（面向触发用户的消息）。
- 限制：仅 form layout；有**未保存修改**时不能 test run（评估的是已保存配置）。
- 会被跳过（action 应用后才生效的 side effects）：**side effect webhooks 不调用**、**notifications 不发送**（但展示分解说明）、**schedule builds 不触发**。

---

## 七、要点总结（为对标做准备）

1. **一等公民**：Action Type 与 Object/Link Type 并列独立定义，不强制挂接对象。
2. **参数驱动一切**：参数是 Action 的输入契约；**规则自动派生同名参数**、参数可带约束（多选）、默认值、可见性覆写。
3. **规则类型丰富**：11+ 种规则，覆盖增删改对象/链接、函数、前后置 Webhook、通知、构建触发、场景合并、接口多态。
4. **取值映射四级**：参数 / 对象参数属性 / 静态值 / 当前用户与时间。
5. **提交标准引用对象状态**：条件可对"对象引用参数的属性"求值（如 `ticket.status is Open`），不只看表单输入。
6. **测试运行即预演**：不落库、同权限同标准、proposed changes 对比 + 执行日志分解 + 管理员/用户错误分离；外部调用需人工 Confirm。
7. **使用面自动聚合**：Object Explorer / Object View / Workshop 三处按参数类型匹配自动出现按钮；**当前对象经环境变量自动绑定**进对象引用参数；single/bulk 两类 action。
8. **治理闭环**：action log / metrics、undo-revert、branching、权限与读写授权。

---

## 八、补充调研：动作在大规模本体中的发现与收敛（20260913）

> 回答的问题："企业应用中上千个动作怎么找？Palantir 是否对动作有分类（公共的/作用于哪些对象）？"
> 补充来源：[Use actions](https://www.palantir.com/docs/foundry/action-types/use-actions/)（见 §五）、[Actions on interfaces](https://www.palantir.com/docs/foundry/action-types/actions-on-interfaces/)、[Use Actions in Workshop](https://palantir.com/docs/foundry/workshop/actions-use/)、[Button Group widget](https://palantir.com/docs/foundry/workshop/widgets-button-group/)。

### 8.1 结论先行

**Palantir 没有动作"分类/标签"体系**（所查官方文档范围内无 tags/category 概念）。它靠**三层机制**收敛用户可见的动作集合，从"全量清单"到"用户 sees 3 个按钮"：

1. **参数类型自动匹配（平台级，主要机制）**：动作是否作用于某对象，由它的 **object reference / object list 参数的类型**声明决定；Object Explorer / Object Views **只渲染参数类型与当前对象匹配的动作**——bulk 上下文"只显示接受正确类型 object list parameters 的 action"。single action（单对象参数）与 bulk action（对象列表参数）据此自动分流。见 §五.2。
2. **应用侧人工策展（应用级）**：Object Views 的 Actions section 与 Workshop 的 Button Group widget 由**构建者手动逐个挑选**动作放进应用（"Select an action..."），每个按钮可配 label/color/icon，参数默认值绑定为 **Active object 变量**（当前选中对象）、可设 Visible/Hidden/Disabled；无默认值的参数才出现为空表单字段。**Workshop 内没有按类型自动过滤机制**——企业用户看到的不是"所有动作"，而是该对象视图/应用策展后的几个按钮。
3. **接口动作（建模级，防膨胀）**：Interface action rules + interface reference parameter 让**一份动作覆盖所有实现该接口的对象类型**（如 Ticket 接口下的 Feature request 与 Bug 共用一个"Create a ticket"），编辑仅限接口共享属性；执行时对象专属动作与接口动作**一并出现在下拉**。这从建模源头减少动作数量，并形成"接口级动作契约"。

辅以**细粒度权限**（actions 可按用户组/条件授权写回，如 analyst 可开调查、仅 manager 可关闭）进一步收窄可见集；Ontology Manager 提供治理侧的搜索与管理。

### 8.2 接口动作的限制（如未来对标需知）

- 编辑仅限**接口共享属性**；Create/Modify 涉及 primary key 会提交失败。
- 与 function-backed actions **不能组合**；action logs 暂不支持。
- 权限无法按实现类型细分（submission criteria 对所有实现类型统一）；只能在 Ontology Manager 对特定类型禁用继承的接口动作（更细控制 under active development）。
- 支持面限于 Ontology Manager（创建）+ Object Explorer / Object Views（渲染），非 SDK 调用面。

### 8.3 对 cmx-ontology 的对照

| 机制 | Palantir | 我方现状 |
| --- | --- | --- |
| 参数类型声明 | object reference / object list 参数类型即"作用于哪些对象"的声明 | ✅ 同构：`parameters[].type=object/objectSet + objectType` |
| 平台级自动匹配 | Object Explorer 三处按参数类型自动聚合 | ❌ 无（explorer 无动作入口）；workshop 动作中心全量展示 + 关键字过滤，**且 manifest 不含 parameters，前端想过滤也没有数据** → 正是 P2-0/P2-1 要修的 |
| 应用侧策展 | Object Views / Workshop 手动挑按钮 + 当前对象变量绑定 | ❌ 无策展层（原生页面即应用，P2-1 的"当前对象自动绑定"迈出第一步） |
| 接口动作 | 一份动作覆盖全部实现类型 | ❌ 已列入"明确不对齐（远期）"，写侧多态首版以按类型分建动作过渡 |
| 分类/标签 | 无官方体系 | 可自选增强：`ActionTypeDef.tags[]`（管理视图分组用），非对标必需 |
