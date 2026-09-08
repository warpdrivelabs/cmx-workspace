# 展示组件

> 何时读：需要可折叠面板、命令栏、状态徽章、空状态、键值清单、筛选条、统计卡、流程审批轨迹时查阅本文件。
> 源码：`packages/cmx-data-comp/src/components/cmx-panel.js`、`cmx-toolbar.js`、`cmx-status-tag.js`、`cmx-empty-state.js`、`cmx-desc-list.js`、`cmx-filter-bar.js`、`cmx-kpi-card.js`、`cmx-flow-trail.js`
>
> **neo 主题**：8 个组件全部支持 neo 皮肤。门户内默认启用（`__cmxDefaultXxxSkin='neo'`）；单组件可用 `data-cmx-skin="none"` 关闭；色调用 `tone` 或 `data-cmx-skin-tone`（`cyan|violet|mint|azure`）。

---

## 1. cmx-panel（可折叠面板）

标题栏 + 内容区 + 可选折叠的卡片外壳，收敛项目中 `.panel`/`.neo-panel`/`.fico-*-section` 碎片。

### 1.1 属性

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `title` | string | `''` | 标题文本 |
| `collapsible` | boolean | `false` | 是否可折叠（出现折叠箭头，点击标题栏切换） |
| `collapsed` | boolean | `false` | 当前是否折叠 |
| `icon` | string | `''` | ui5 图标名（标题前缀） |
| `tone` | `'cyan'` \| `'violet'` \| `'mint'` \| `'azure'` | `''` | neo 强调色调 |

### 1.2 API

| 方法 | 说明 |
|------|------|
| `toggle(force?)` | 切换折叠状态（`force` 显式指定 true/false），非可折叠面板无效 |

### 1.3 事件

| 事件名 | `detail` | 说明 |
|--------|----------|------|
| `cmx-panel-collapse` | `{ collapsed }` | 折叠状态变化，`bubbles + composed` |

### 1.4 Slot

| Slot | 说明 |
|------|------|
| (默认) | 内容区 |
| `header-actions` | 标题栏右侧操作区（按钮等） |
| `summary` | 折叠态摘要（collapsed 时显示，替代内容区） |

```html
<cmx-panel title="基本信息" collapsible icon="detail-view" tone="violet">
  <ui5-button slot="header-actions" icon="edit">编辑</ui5-button>
  <cmx-desc-list border>
    <cmx-desc-item label="编码">DOC001</cmx-desc-item>
    <cmx-desc-item label="状态">已审核</cmx-desc-item>
  </cmx-desc-list>
</cmx-panel>
```

---

## 2. cmx-toolbar（命令栏）

声明式命令栏，slot 透传风格——只做横向布局 + 分隔符 + 左右分区，内部按钮/输入框用 UI5 通过 slot 放入。

### 2.1 属性

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `align` | `'start'` \| `'center'` \| `'end'` | `'start'` | 主区对齐 |
| `gap` | number | `8` | 项间间距（px） |
| `wrap` | boolean | `false` | 项过多时是否换行 |
| `divider` | boolean | `false` | 主区与 actions 区之间显示分隔线 |
| `tone` | string | `''` | neo 色调 |

### 2.2 Slot

| Slot | 说明 |
|------|------|
| (默认) | 主操作区（左/起始，放 ui5-button 等） |
| `actions` | 右侧次要操作区（导出/更多等） |

> 无事件——点击由内部 ui5-button 自行冒泡，业务方监听按钮 click 即可。

```html
<cmx-toolbar divider>
  <ui5-button design="Default" icon="add" id="btnAdd">新增</ui5-button>
  <ui5-button design="Default" icon="delete" id="btnDel">删除</ui5-button>
  <ui5-button design="Emphasized" icon="save" slot="actions" id="btnSave">保存</ui5-button>
  <ui5-button design="Transparent" icon="export" slot="actions" id="btnExport">导出</ui5-button>
</cmx-toolbar>
```

---

## 3. cmx-status-tag（状态徽章）

语义色 + 填充风格的状态标签，收敛 100+ 处 span 手搓的 chip/badge。

### 3.1 属性

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `tone` | `'success'` \| `'warning'` \| `'danger'` \| `'info'` \| `'neutral'` | `'neutral'` | 语义色 |
| `variant` | `'solid'` \| `'subtle'` \| `'outline'` | `'solid'` | 填充风格（solid 实色 / subtle 浅底深字 / outline 描边） |
| `dot` | boolean | `false` | 前缀发光圆点 |
| `size` | `'sm'` \| `'md'` | `'md'` | 尺寸 |

### 3.2 Slot

| Slot | 说明 |
|------|------|
| (默认) | 标签文本 |

```html
<cmx-status-tag tone="success" variant="subtle" dot>已启用</cmx-status-tag>
<cmx-status-tag tone="danger" variant="solid">已作废</cmx-status-tag>
<cmx-status-tag tone="warning" variant="outline" size="sm">待审核</cmx-status-tag>
```

---

## 4. cmx-empty-state（空状态）

图标 + 标题 + 副标题 + 可选动作的空状态占位，收敛 75 处 `class="empty"` 碎片。

### 4.1 属性

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `icon` | string | `'activity-assistance'` | ui5 图标名 |
| `title` | string | `''` | 标题 |
| `description` | string | `''` | 副标题 |
| `size` | `'sm'` \| `'md'` \| `'lg'` | `'md'` | 尺寸 |

### 4.2 Slot

| Slot | 说明 |
|------|------|
| `icon` | 覆盖图标（默认按 icon 属性渲染 ui5-icon） |
| `title` | 覆盖标题文本 |
| `description` | 覆盖副标题 |
| (默认) | 动作区（如「去创建」按钮） |

```html
<cmx-empty-state icon="database" title="暂无数据" description="点击新增创建第一条记录">
  <ui5-button design="Emphasized" icon="add">新增记录</ui5-button>
</cmx-empty-state>
```

---

## 5. cmx-desc-list / cmx-desc-item（键值清单）

label:value 两列只读清单，收敛 `class="kv"` 与详情面板手搓碎片。

### 5.1 属性（cmx-desc-list）

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `columns` | number | `1` | 响应式列数 |
| `label-width` | string（CSS） | `'6rem'` | 标签列宽 |
| `border` | boolean | `false` | 项间显示分隔线 |
| `tone` | string | `''` | neo 色调 |

### 5.2 子元素 cmx-desc-item

| 属性 | 说明 |
|------|------|
| `label` | 标签文本 |
| (默认 slot) | 值 |

> 子项增删 / label 变化由 MutationObserver 自动响应，无需手动刷新。

```html
<cmx-desc-list columns="2" border>
  <cmx-desc-item label="单据编码">DOC20260729001</cmx-desc-item>
  <cmx-desc-item label="状态">已审核</cmx-desc-item>
  <cmx-desc-item label="制单人">张三</cmx-desc-item>
  <cmx-desc-item label="制单日期">2026-07-29</cmx-desc-item>
</cmx-desc-list>
```

---

## 6. cmx-filter-bar（筛选条）

内置搜索框 + slot 自定义条件 + 搜索/清空事件的查询条件区。

### 6.1 属性

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `collapsible` | boolean | `false` | 条件多时可折叠收起 |
| `collapsed` | boolean | `false` | 当前是否折叠 |
| `search-text` | string | `''` | 搜索框文本（双向） |
| `search-placeholder` | string | `'关键字'` | 搜索框占位提示 |
| `show-search` | boolean | `true` | 是否显示内置搜索框 |
| `tone` | string | `''` | neo 色调 |

### 6.2 API

| 方法 | 说明 |
|------|------|
| `search()` | 触发搜索，派发 `cmx-filter-search` |
| `reset()` | 清空搜索框文本，派发 `cmx-filter-reset`（不清空 slot 内自定义控件） |

### 6.3 事件

| 事件名 | `detail` | 说明 |
|--------|----------|------|
| `cmx-filter-search` | `{ text }` | 搜索/回车触发，`bubbles + composed` |
| `cmx-filter-reset` | `{}` | 清空触发，`bubbles + composed` |

### 6.4 Slot

| Slot | 说明 |
|------|------|
| (默认) | 自定义条件控件（ui5-select / ui5-date-picker 等） |
| `actions` | 右侧操作按钮区 |

```html
<cmx-filter-bar id="filterBar" collapsible search-placeholder="编码/名称">
  <ui5-select id="fStatus">
    <ui5-option selected>全部</ui5-option>
    <ui5-option>已审核</ui5-option>
    <ui5-option>待审核</ui5-option>
  </ui5-select>
  <ui5-date-picker id="fDate"></ui5-date-picker>
</cmx-filter-bar>
<script>
  filterBar.addEventListener('cmx-filter-search', (e) => {
    console.log('搜索', e.detail.text, fStatus.value, fDate.value)
    reload()
  })
  filterBar.addEventListener('cmx-filter-reset', () => {
    fStatus.value = ''; fDate.value = ''
    reload()
  })
</script>
```

---

## 7. cmx-kpi-card（统计卡）

统计卡 / KPI 指标卡，收敛财务模块 125+ 处手搓的 `acct-kpi`/`neo-kpi`/`fico-kpi` 碎片。统一两种视觉风格 + 语义色调。

### 7.1 属性

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `label` | string | `''` | 标签文本（如「资产」「借方」） |
| `value` | string | `''` | 数值文本（如「12,345.00」） |
| `unit` | string | `''` | 单位（如「万元」「%」），显示在数值后 |
| `tone` | `'success'\|'warning'\|'danger'\|'info'\|'neutral'\|'cash-in'\|'cash-out'\|'revenue'\|'expense'\|'asset'` | `'neutral'` | 语义色（合并 acct-kpi 的 data-kind 与 neo-kpi 的修饰符 class） |
| `variant` | `'card'\|'inline'` | `'card'` | 视觉风格：card（圆角块卡片，neo-kpi 风格）/ inline（行内 label:value，acct-kpi 风格） |
| `trend` | `'up'\|'down'\|'flat'` | `''` | 趋势指示（不设则不显示） |
| `delta` | string | `''` | 趋势附带的数值文本（如「+5.2%」），配合 trend 显示 |
| `clickable` | boolean | `false` | 是否可点击（acct-kpi 风格的筛选链接） |

### 7.2 事件

| 事件名 | `detail` | 说明 |
|--------|----------|------|
| `cmx-kpi-click` | `{ label, value }` | `clickable` 时点击派发，`bubbles + composed` |

### 7.3 Slot

| Slot | 说明 |
|------|------|
| (默认) | 覆盖 value 区域（自定义内容） |

```html
<!-- variant=card：看板统计卡 -->
<cmx-kpi-card label="净利润" value="89,432.10" unit="元" tone="success" trend="up" delta="+12.3%"></cmx-kpi-card>
<cmx-kpi-card label="流失客户" value="23" tone="danger" trend="down" delta="-8.1%"></cmx-kpi-card>

<!-- variant=inline：财务 acct-kpi 风格（可点击筛选） -->
<cmx-kpi-card variant="inline" label="现金流入" value="56,789.00" tone="cash-in" clickable></cmx-kpi-card>
<cmx-kpi-card variant="inline" label="现金流出" value="34,210.50" tone="cash-out" clickable></cmx-kpi-card>
```

---

## 8. cmx-flow-trail（流程审批轨迹）

流程/审批轨迹时间线（事件流口径，钉钉/飞书「审批记录」同款）：一条意见一条事件按时间正序铺开，退回重走同节点出现多次；「发起」为人造首条；尾部补当前等待节点与待处理节点；终止实例尾部留提示。纯呈现组件，不负责取实例数据。20260903 自 native 页三副本（mdm/cr-form / flow/task-form / flow/todo-center）上收归库，改一处全生效。

### 8.1 数据绑定（命令式，无属性）

| 用法 | 说明 |
|------|------|
| `el.trail = { instance, definition, comments }` | `instance`=实例全量（`/api/flow/instances/{id}`，含 tokens/tasks/activeNodes/state）；`definition`=流程定义单条（`/api/flow/definitions`，含 nodes/edges）；`comments`=意见数组（userId/nickName/decision/nodeBpmnId/comment/createdAt） |

办理人显示名经 `globalThis.__cmxFlowUsers` 用户快照解析；快照为空时组件自动拉 `/api/iam/users/list` 兜底（页面已填充则零请求），失败回退显示原始 id。

### 8.2 皮肤属性

| 属性 | 说明 |
|------|------|
| `data-cmx-skin` | `neo`（默认）/ `plain`·`none`（回退 `--sap*` 令牌基础样式） |
| `data-cmx-skin-tone` | `cyan`（默认）/ `mint` / `violet` / `azure`——neo 强调色（当前节点圆点/文字/荧光）随 tone 切换 |

```html
<!-- 页面静态占位 + bind() 里回填 el.trail -->
<cmx-flow-trail></cmx-flow-trail>
```

---

## neo 主题速查

所有 8 个组件共享同一套皮肤机制：

| 用法 | 效果 |
|------|------|
| 默认（门户内） | 自动启用 neo 皮肤（`__cmxDefaultXxxSkin='neo'`） |
| `data-cmx-skin="none"` | 关闭 neo，用基础 sap 令牌样式 |
| `tone="violet"` 或 `data-cmx-skin-tone="violet"` | 切换强调色调 |
| `data-cmx-style-id="my-style"` | 引用同页 `<style id="my-style">` 作为页面级覆盖（layer=page，优先级最高） |
