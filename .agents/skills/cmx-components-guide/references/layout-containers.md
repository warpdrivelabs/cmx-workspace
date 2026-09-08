# 布局与容器组件

> 何时读：需要分栏布局、标签页切换、嵌入视图、分页栏时查阅本文件。
> 源码：`packages/cmx-data-comp/src/components/cmx-split-pane.js`、`cmx-view-tabs.js`、`cmx-embed-page.js`、`cmx-pager.js`

## 1. cmx-split-pane（分栏布局）

可拖拽调整大小的双区域分栏容器，支持水平 / 垂直方向。

### 1.1 属性

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `orientation` | `'horizontal'` \| `'vertical'` | `'horizontal'` | `horizontal` = 上下分栏；`vertical` = 左右分栏 |
| `size` | `'40%'` \| `'240px'` | `'50%'` | 第一区域尺寸，支持百分比或像素值 |
| `min-first` | number | `120` | 第一区域最小尺寸（px） |
| `min-second` | number | `120` | 第二区域最小尺寸（px） |
| `splitter-size` | number | `3` | 分隔条宽度（px） |

### 1.2 API

| 方法 | 说明 |
|------|------|
| `setSize(value)` | 设置第一区域尺寸，等价 `setAttribute('size', value)` |
| `refresh()` | 通知子组件（grid/form/treeview）重新计算布局 |

### 1.3 事件

| 事件名 | `detail` | 说明 |
|--------|----------|------|
| `cmx-split-change` | `{ size }` | 拖拽结束或键盘调整后派发，`bubbles + composed` |

### 1.4 Slot

| Slot | 说明 |
|------|------|
| `slot="first"` | 第一区域内容 |
| `slot="second"` | 第二区域内容 |

### 1.5 交互

- 鼠标拖拽分隔条调整大小，受 `min-first` / `min-second` 约束。
- 键盘：分隔条聚焦后按方向键调整，`Shift` 加速（步长 40px，默认 16px）。
- 拖拽结束后自动调用子组件 `refreshLayout()` / `redraw()`。

```html
<cmx-split-pane orientation="vertical" size="240px" min-first="160" min-second="200">
  <cmx-web-treeview slot="first" id-member="id" path-member="path"></cmx-web-treeview>
  <cmx-revo-grid slot="second"></cmx-revo-grid>
</cmx-split-pane>
```

## 2. cmx-view-tabs（标签页）

轻量标签控制器，管理 slot 内的面板切换。

### 2.1 属性

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `active` | viewId | 首个 tab | 当前激活的视图 id |

### 2.2 API

| 方法 | 说明 |
|------|------|
| `select(id)` | 切换到指定视图，更新 `active` 属性并派发事件 |

### 2.3 事件

| 事件名 | `detail` | 说明 |
|--------|----------|------|
| `cmx-view-change` | `{ view }` | 切换标签时派发，`bubbles + composed` |

### 2.4 Slot

| Slot | 说明 |
|------|------|
| `slot="tabs"` | 标签条区域，子元素需带 `data-view="<id>"` 属性 |
| 默认 slot | 面板区域，子元素需带 `data-view-panel="<id>"` 属性 |

### 2.5 行为

- 无 `active` 属性时自动取第一个 tab 的 `data-view` 值。
- 切换面板后自动调用面板内 `cmx-revo-grid` / `cmx-tabulator` / `cmx-ui5-form` / `cmx-web-treeview` 的 `refreshLayout()` / `redraw()`。
- 支持 `data-cmx-fill` 属性撑满父容器（flex 布局）。

```html
<cmx-view-tabs active="list">
  <div slot="tabs">
    <button data-view="list">列表</button>
    <button data-view="chart">图表</button>
  </div>
  <div data-view-panel="list">
    <cmx-revo-grid></cmx-revo-grid>
  </div>
  <div data-view-panel="chart">
    <cmx-ignite-gauge data-cmx-gauge-type="radial"></cmx-ignite-gauge>
  </div>
</cmx-view-tabs>
```

## 3. cmx-embed-page（嵌入视图）

在当前视图中嵌入 workspace.embed 区定义的 html_pages 视图，支持单视图或多视图 tab 切换。

### 3.1 属性

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `pages` | viewId 列表 | — | 逗号或空白分隔的 viewId，对应 `workspace.embed.views[].id` |
| `tab-position` | `'top'` \| `'bottom'` \| `'left'` \| `'right'` | `'top'` | 多视图时 tab 条位置；单视图时不显示 tab 条 |
| `initial-view` | viewId | 列表首项 | 多视图初始激活的 viewId |

### 3.2 视图根节点管理

通过 host 的 workspace 管理视图根节点的借入与归还：

| 方法 | 说明 |
|------|------|
| `host.workspace.borrowEmbedRoot(viewId, container)` | 借入视图的 mount root 到指定容器，返回 `{ root, icon, label }` 或 `null` |
| `host.workspace.returnEmbedRoot(viewId, borrower)` | 归还借出的 root，回到隐藏 holder |

### 3.3 行为

- `connectedCallback` 时通过 `borrowEmbedRoot` 借入每个 view 的 root；CE 不会被重 hydrate（同 document tree 内移动）。
- `disconnectedCallback` / `pages` / `tab-position` 变更时归还所有借出的 root。
- 多视图：当前激活 view 的 root 可见，其余 `display:none`；切 tab 仅改 display。
- 视图不存在时渲染 placeholder 提示（Negative 风格）。
- workspace 未就绪时 rAF 有限次重试（最多 30 次），仍未就绪才提示。

### 3.4 访问视图 API

视图脚本通过 `host.workspace` 访问 mainapp 中的 `tab:<id>` workspace，`host.workspace.pageview['embed_page1']` 可拿到对应 CE 实例。

```html
<!-- 单视图嵌入 -->
<cmx-embed-page pages="embed_page1"></cmx-embed-page>

<!-- 多视图嵌入 + tab 位置 -->
<cmx-embed-page pages="embed_page1,embed_page2" tab-position="left" initial-view="embed_page2"></cmx-embed-page>
```

## 4. cmx-pager（分页栏）

通用分页栏，支持独立模式与协作模式。

### 4.1 属性

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page` | number | `1` | 当前页码 |
| `page-size` | number | `50` | 每页条数 |
| `page-sizes` | string | `'50,100,200'` | 可选每页条数，逗号分隔 |
| `total` | number | `null` | 总条数；`null` 表示未知（显示「第 N 页」） |
| `compact` | boolean | — | 紧凑模式，隐藏首页/末页按钮 |
| `master-slave-id` | string | — | 协作模式协调器属性名（设此值即进入协作模式） |
| `layer` | string | — | 协作模式绑定层 id；缺省时用协调器根层 |

### 4.2 CSS Parts

| Part | 说明 |
|------|------|
| `root` | 分页栏根容器 |
| `first` / `prev` / `next` / `last` | 首页 / 上一页 / 下一页 / 末页按钮 |
| `info` | 页码信息文本 |
| `size` | 每页条数下拉 |
| `suffix` | “条/页”后缀 |

窄容器（如 explorer 侧栏）可配合 `compact`，并通过 `::part(size)` / `::part(suffix)` 隐藏每页条数区域。

### 4.3 双模式

| 模式 | 触发条件 | 行为 |
|------|----------|------|
| 独立模式（默认） | 未设 `master-slave-id` | 组件自管 `page`/`pageSize`/`total`，派发 `page-change` 事件，外部监听后拉数据并回填 `pager.total` |
| 协作模式 | 设了 `master-slave-id` | 操作转发到协调器（`host[msId]`），状态从协调器 `page-changed` 事件反向同步；不派发 `page-change` |

### 4.4 API

| 方法 | 说明 |
|------|------|
| `nextPage()` | 下一页 |
| `prevPage()` | 上一页 |
| `firstPage()` | 首页 |
| `lastPage()` | 末页 |
| `gotoPage(n)` | 跳转到第 n 页 |
| `setPageSize(n, opts?)` | 设置每页大小；`opts.resetPage` 默认 `true`（重置到第 1 页） |
| `getPagingInfo()` | 返回 `{ page, pageSize, total, totalPages, offset }` |

属性 getter/setter：`page`、`pageSize`、`total`、`totalPages`（只读计算属性）。

### 4.5 事件

| 事件名 | `detail` | 说明 |
|--------|----------|------|
| `page-change` | `{ page, pageSize, total, totalPages, offset, reason }` | 独立模式下页码或每页大小变化时派发，`bubbles + composed`；协作模式不派发 |

### 4.6 独立模式示例

```html
<cmx-pager page-size="5" page-sizes="5,10,20,50"></cmx-pager>
```

```js
const pager = document.querySelector('cmx-pager')
pager.addEventListener('page-change', (e) => {
  const { page, pageSize, offset } = e.detail
  fetchData(page, pageSize).then(({ rows, total }) => {
    pager.total = total
    renderRows(rows)
  })
})
```

### 4.7 协作模式示例

```html
<cmx-pager master-slave-id="ms" layer="cv_batch"></cmx-pager>
```

协作模式下协调器未就绪时显示占位提示，连接成功后状态自动同步。
