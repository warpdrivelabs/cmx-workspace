# cmx-web-treeview 树视图组件

> 何时读：需要树形数据展示、节点拖拽、层级筛选、节点角标时查阅本文件。
> 源码：`packages/cmx-data-comp/src/components/cmx-web-treeview.js`

## 1. 概述

`<cmx-web-treeview>` 基于 `@keenmate/web-treeview` 封装，集成 CmxDataSet + CmxColumnModel。封装模式与 CmxRevoGrid 一致：内部 `web-treeview` 在 Shadow DOM 里，通过属性代理和方法代理暴露能力。

### 1.1 数据转换规则

| 场景 | 规则 |
|------|------|
| 显示文本 | `display-value-member` 字段值；有 model 时由 `model.getTitleColIds()` 对应字段值空格拼接写入 |
| 图标 | `model.iconCol` 字段值，通过 `renderNodeCallback` 渲染为 `<ui5-icon>`；无 model 时用 `icon-member` 属性 |
| 角标 | `badge-member` 属性指定字段名，值 > 0 时以蓝色气泡显示在右侧（> 99 显示 99+） |
| 选中态 | `is-selected-member` 字段值为 `true`/`1`/`'1'`/`'true'` 时标记选中 |
| 加载态 | `children-loading-member` 字段值为 `true`/`1` 时在展开图标处显示 spinner |

## 2. 配置方法

| 方法 | 说明 |
|------|------|
| `setDataSet(ds)` | 绑定 CmxDataSet，rows 变更时自动刷新树（监听 `ds-row-added`/`ds-row-removed`/`row-changed`） |
| `setColumnModel(model)` | 绑定 CmxColumnModel，控制显示字段与图标字段 |

## 3. 属性（observedAttributes，共 61 个）

### 3.1 数据字段映射

| 属性 | 说明 |
|------|------|
| `tree-id` | 树 id |
| `id-member` | 节点 id 字段名 |
| `path-member` | 路径字段名 |
| `parent-path-member` | 父路径字段名 |
| `level-member` | 层级字段名 |
| `is-expanded-member` | 是否展开字段名 |
| `is-selected-member` | 是否选中字段名 |
| `is-draggable-member` | 是否可拖拽字段名 |
| `is-drop-allowed-member` | 是否允许放置字段名 |
| `has-children-member` | 是否有子节点字段名 |
| `children-loading-member` | 子节点加载中字段名 |
| `display-value-member` | 显示文本字段名 |
| `search-value-member` | 搜索值字段名 |
| `is-selectable-member` | 是否可选字段名 |
| `is-collapsible-member` | 是否可折叠字段名 |
| `order-member` | 排序字段名 |
| `allowed-drop-positions-member` | 允许放置位置字段名 |
| `icon-member` | 图标字段名（无 model 时使用） |
| `badge-member` | 角标字段名 |

### 3.2 树行为

| 属性 | 说明 |
|------|------|
| `expand-level` | 默认展开层级 |
| `tree-path-separator` | 路径分隔符 |
| `should-toggle-on-node-click` | 点击节点是否切换展开 |
| `is-sorted` | 是否排序 |
| `should-use-internal-search-index` | 是否使用内部搜索索引 |
| `indexer-batch-size` | 索引批次大小 |
| `indexer-timeout` | 索引超时 |
| `search-text` | 搜索文本 |
| `toggle-icon-mode` | 切换图标模式 |
| `scroll-highlight-timeout` | 滚动高亮超时 |
| `scroll-highlight-class` | 滚动高亮 class |
| `align-node-icons` | 是否对齐节点图标 |

### 3.3 样式 class

| 属性 | 说明 |
|------|------|
| `body-class` | body class |
| `selected-node-class` | 选中节点 class |
| `drag-over-node-class` | 拖拽悬停 class |
| `expand-icon-class` | 展开图标 class |
| `collapse-icon-class` | 折叠图标 class |
| `leaf-icon-class` | 叶子图标 class |

### 3.4 拖拽

| 属性 | 说明 |
|------|------|
| `drag-drop-mode` | 拖拽模式 |
| `drop-zone-mode` | 放置区模式 |
| `drop-zone-layout` | 放置区布局 |
| `drop-zone-start` | 放置区起点 |
| `drop-zone-max-width` | 放置区最大宽度 |
| `allow-copy` | 是否允许复制 |
| `auto-handle-copy` | 是否自动处理复制 |
| `context-menu-x-offset` | 右键菜单 x 偏移 |
| `context-menu-y-offset` | 右键菜单 y 偏移 |

### 3.5 渲染与虚拟化

| 属性 | 说明 |
|------|------|
| `use-flat-rendering` | 扁平渲染 |
| `flat-indent-size` | 扁平缩进大小 |
| `progressive-render` | 渐进渲染 |
| `initial-batch-size` | 初始批次大小 |
| `max-batch-size` | 最大批次大小 |
| `virtual-scroll` | 虚拟滚动 |
| `virtual-row-height` | 虚拟行高 |
| `virtual-overscan` | 虚拟预渲染 |
| `virtual-container-height` | 虚拟容器高度 |
| `is-loading` | 加载中状态 |
| `should-display-debug-information` | 显示调试信息 |

### 3.6 cmx 自有属性（不透传给内部 web-treeview）

| 属性 | 说明 |
|------|------|
| `data-cmx-skin` | 皮肤模式；`colored` 启用彩色悬停/选中渐变效果 |
| `data-cmx-accent-color` | 强调色，默认 `var(--sapHighlightColor,#0070f2)` |
| `data-cmx-tree-lines` | 树连接线；`false` 时隐藏连接线 |
| `data-cmx-sync-current-row` | 节点点击时是否同步 DataSet 游标；`false` 禁用（默认启用） |

## 4. API（方法代理）

| 方法 | 说明 |
|------|------|
| `expandAll(opts)` | 展开全部节点 |
| `collapseAll(opts)` | 折叠全部节点 |
| `expandNodes(paths)` | 展开指定路径节点 |
| `collapseNodes(paths)` | 折叠指定路径节点 |
| `filterNodes(text)` | 按文本过滤节点 |
| `scrollToPath(path, opts)` | 滚动到指定路径，返回 `Promise<boolean>` |
| `getNodeByPath(path)` | 按路径获取节点，返回节点或 `null` |
| `getExpandedPaths()` | 获取已展开路径列表 |
| `setExpandedPaths(paths)` | 设置展开路径列表 |
| `update(config)` | 更新树配置 |
| `getTree()` | 获取内部树实例 |

## 5. 属性代理（getter/setter）

| 属性 | 说明 |
|------|------|
| `data` | 内部树数据 |
| `isLoading` | 加载中状态 |
| `searchText` | 搜索文本 |
| `renderNodeCallback` | 节点渲染回调 |

## 6. 事件

所有事件均 `bubbles: true, composed: true`，转发内部 `web-treeview` 事件。

| 事件名 | 说明 |
|--------|------|
| `node-clicked` | 节点点击；触发前同步 DataSet 游标（除非 `data-cmx-sync-current-row="false"`） |
| `node-drop` | 节点拖拽放置 |
| `selected-node-changed` | 选中节点变化 |
| `tree-changed` | 树结构变化 |

## 7. 主题

- 与 cmx-revo-grid 相同的检测方式：延一帧读 `--sapBackgroundColor` 亮度判断明暗。
- 暗色时覆盖 `--tv-*` 变量（背景/文字/边框/悬停/选中/强调色等）。
- 监听 `cmx-portal-theme-change` 事件，门户切换主题时重新应用。

## 8. 数据刷新机制

`setDataSet` 后 rows 变更时自动调用 `_syncToInner()`：
1. 捕获当前展开路径（`getExpandedPaths()`）。
2. 将 rows 转为节点数据写入内部 `web-treeview.data`。
3. `requestAnimationFrame` 中恢复展开路径（`setExpandedPaths()`）。
4. 规范化已渲染节点的选中态。

## 9. 代码示例

```html
<cmx-web-treeview
  id-member="id"
  path-member="path"
  parent-path-member="parentPath"
  display-value-member="name"
  expand-level="2"
  tree-path-separator="/"
  icon-member="icon"
  badge-member="count"
  data-cmx-skin="colored"
  data-cmx-tree-lines="true"
></cmx-web-treeview>
```

```js
const tree = document.querySelector('cmx-web-treeview')
tree.setDataSet(ds)
tree.setColumnModel(model)

// 监听节点点击
tree.addEventListener('node-clicked', (e) => {
  const node = e.detail.node
  console.log('clicked:', node.id)
})

// 编程式展开
tree.expandAll()
tree.scrollToPath('root/child/grandchild').then((ok) => {
  if (ok) console.log('scrolled')
})
```
