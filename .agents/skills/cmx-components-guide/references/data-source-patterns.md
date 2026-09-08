# 数据源适配器模式

> 何时读：需要为下拉/combo/异步搜索组件提供数据源时查阅本文件；REST 直连、pageServices、内存数据源三种变体。
> 源码：`packages/cmx-data-comp/src/lib/cmx-dict-data-source.js`、`cmx-async-source.js`

## 1. DataSource 契约

所有数据源（无论远程或内存）都实现以下接口，被 `cmx-dict-select` / `cmx-async-source` / combo 等组件消费。

### 1.1 必需方法

| 方法 | 签名 | 说明 |
|------|------|------|
| `search` | `(query, opts) => Promise<items[]>` | 搜索查询，返回条目数组 |
| `loadByKeys` | `(keys) => Promise<items[]>` | 按 key 批量加载条目 |

### 1.2 可选字段

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `keyField` | `string` | `'code'` | 主键字段名 |
| `labelField` | `string` | `'name'` | 显示文本字段名 |
| `pageSize` | `number` | `50` | 默认每页条数 |
| `items` | `array` | - | 同步缓存（有值时 `lookupByKeyAsync` 优先查这里） |
| `cacheSize` | `number` | `200` | LRU 缓存容量 |
| `debounceMs` | `number` | `250` | debounce 延迟（ms） |

### 1.3 search 的 opts 参数

| 字段 | 类型 | 说明 |
|------|------|------|
| `page` | `number` | 页码，默认 1 |
| `pageSize` | `number` | 每页条数，默认取 source.pageSize |
| `signal` | `AbortSignal` | 中断信号（由 `searchAsync` 注入） |

## 2. createDictDataSource 工厂

> 路径：`packages/cmx-data-comp/src/lib/cmx-dict-data-source.js`

### 2.1 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `host` | `any` | - | 宿主对象，提供 `host[service]` 方法 |
| `def.id` | `string` | `def.service` | 数据源 id |
| `def.service` | `string` | - | **必需**；host 上的方法名 |
| `def.keyField` | `string` | `'code'` | 主键字段名 |
| `def.labelField` | `string` | `'name'` | 显示文本字段名 |
| `def.queryParam` | `string` | `'q'` | 搜索关键字参数名 |
| `def.filtersParam` | `string` | `'filters'` | 过滤参数名 |
| `def.pageSize` | `number` | `50` | 每页条数 |
| `def.minPageSizeForKeys` | `number` | `20` | loadByKeys 的最小 pageSize |
| `def.extraParams` | `object` \| `Function` | - | 额外参数；函数形式接收 `{ query, page, pageSize }` 上下文 |
| `def.responsePath` | `string` \| `Function` | - | 响应取值路径；字符串用点号分割，函数形式接收 `(res, ctx)` |
| `def.transform` | `Function` | - | 响应转换函数 `(res, ctx) => items[]`；优先级高于 `responsePath` |

### 2.2 调用协议

工厂不拼 URL，只约定 `host[service]` 的调用协议：

| 方法 | 调用参数 |
|------|----------|
| `search` | `host[service]({ q, page, pageSize, ...extra }, { signal })` |
| `loadByKeys` | `host[service]({ filters: { [keyField]: keys }, page: 1, pageSize }, { signal })` |

### 2.3 响应取值优先级

1. `transform(res, ctx)` -- 自定义转换
2. `responsePath` 为函数 -- `responsePath(res, ctx)`
3. `responsePath` 为字符串 -- 点号分割取值
4. `pickRows(res)` -- 自动探测：`res` / `res.rows` / `res.items` / `res.data` / `res.data.rows` / `res.data.items`

## 3. makeDictSource 标准骨架（三种变体）

### 3.1 变体一：REST 直连

直接 fetch 远程接口，适合独立页面或无 pageServices 的场景。

```js
function makeDictSource(dictId) {
  return {
    keyField: 'id',
    labelField: 'item_name',
    pageSize: 50,
    search(query, o) {
      return fetch('/api/dict/' + dictId + '/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ q: query||'', page: o.page||1, pageSize: o.pageSize||50 })
      }).then(r => r.json()).then(j => j.rows || [])
    },
    loadByKeys(keys) {
      return fetch('/api/dict/' + dictId + '/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filters: { id: keys }, page:1, pageSize: Math.max(20, keys.length) })
      }).then(r => r.json()).then(j => j.rows || [])
    }
  }
}
```

### 3.2 变体二：走 pageServices

通过设计器页面的 `host[serviceName](params, {signal})` 调用后端服务，适合 html-pages 场景。

```js
function makeDictSource(host, serviceName) {
  return {
    keyField: 'id',
    labelField: 'name',
    pageSize: 50,
    search(query, o) {
      return host[serviceName]({
        q: query || '',
        page: o.page || 1,
        pageSize: o.pageSize || 50
      }, { signal: o.signal }).then(res => res.rows || [])
    },
    loadByKeys(keys) {
      return host[serviceName]({
        filters: { id: keys },
        page: 1,
        pageSize: Math.max(20, keys.length)
      }, { signal: o.signal }).then(res => res.rows || [])
    }
  }
}
```

> 推荐直接用 `createDictDataSource(host, { service: serviceName, keyField: 'id' })` 替代手写。

### 3.3 变体三：内存数据源

本地数据转成 DataSource 协议，适合枚举字段或静态选项。可直接用 `createLocalDictDataSource(options, def)` 工厂。

```js
function makeDictSource(options) {
  const rows = (options || []).map(o => ({
    id: o.value != null ? o.value : o.code,
    name: o.label != null ? o.label : o.name
  }))
  return {
    keyField: 'id',
    labelField: 'name',
    items: rows,
    search(q) {
      const s = String(q || '').trim().toLowerCase()
      if (!s) return Promise.resolve(rows.slice())
      return Promise.resolve(
        rows.filter(r =>
          String(r.id).toLowerCase().includes(s) ||
          String(r.name).toLowerCase().includes(s)
        )
      )
    },
    loadByKeys(keys) {
      const set = new Set(keys.map(String))
      return Promise.resolve(rows.filter(r => set.has(String(r.id))))
    }
  }
}
```

> 也可用内置工厂：`createLocalDictDataSource(options, { keyField: 'id', labelField: 'name' })`，自动从 `{ value, label }` 或 `{ code, name }` 格式转换。

## 4. searchAsync / lookupByKeyAsync 工具

> 路径：`packages/cmx-data-comp/src/lib/cmx-async-source.js`

这些工具由 `cmx-ui5-table` / `cmx-ui5-form` 内部使用，为 DataSource 提供缓存、防抖、中断能力。

### 4.1 searchAsync(source, query, opts)

远程搜索，同一 source 上前一次未结束的请求会被 abort。

| 特性 | 说明 |
|------|------|
| LRU 缓存 | 按 `${query}::${stableOptsKey(opts)}` 缓存结果，命中直接同步 resolve |
| AbortController | 同一 source 同时只保留最后一次未完成请求 |
| keyCache 顺便填充 | 搜索结果中每条的 `keyField` 值写入 keyCache |

```js
import { searchAsync } from 'cmx-data-comp/src/lib/cmx-async-source.js'

searchAsync(source, '张', { page: 1, pageSize: 50 }).then(items => {
  console.log(items)
})
```

### 4.2 lookupByKeyAsync(source, key)

按 keyField 单值查找，查找顺序：

| 步骤 | 来源 | 说明 |
|------|------|------|
| 1 | `source.items` | 同步缓存直接命中（有值时） |
| 2 | keyCache | LRU 缓存命中 |
| 3 | `source.loadByKeys([key])` | 远程加载，结果写入 keyCache |
| 4 | `source.search(key)` | loadByKeys 不存在时回退到搜索 |

```js
import { lookupByKeyAsync } from 'cmx-data-comp/src/lib/cmx-async-source.js'

lookupByKeyAsync(source, 'user_001').then(row => {
  console.log(row) // { id: 'user_001', name: '张三' } 或 null
})
```

### 4.3 debounceForSource(source, fn)

工厂：返回一个 debounce 包装函数。同一 source 共享 timer，多次快速调用只触发最后一次。

```js
import { debounceForSource } from 'cmx-data-comp/src/lib/cmx-async-source.js'

const debouncedSearch = debounceForSource(source, (query) => {
  searchAsync(source, query).then(render)
})
input.addEventListener('input', (e) => debouncedSearch(e.target.value))
```

### 4.4 getAsyncSourceCache(source)

给 DataSource 创建/取出共享的远程辅助缓存对象。同一 source 实例多次调用返回同一份缓存。

| 字段 | 说明 |
|------|------|
| `queryCache` | LRU，query string -> items[] |
| `keyCache` | LRU，valueField -> row |
| `debounceMs` | 来自 `source.debounceMs`，默认 250 |
| `pageSize` | 来自 `source.pageSize`，默认 20 |
| `abortCtrl` | 当前未完成的 AbortController |
| `debounceTimer` | debounce 定时器 |

## 5. 高频陷阱

| 陷阱 | 说明 |
|------|------|
| 不要每页手写 makeDictSource | 优先用 `createDictDataSource` 工厂或复用标准骨架；手写易遗漏 keyField/responsePath 对齐 |
| keyField 默认 `'code'` 但字典接口通常返回 `'id'` | `createDictDataSource` 默认 `keyField='code'`；字典数据走 `POST /api/dct/data/search`（直读 `cf_*` 物理表），接口返回的通常是 `id` 字段，需显式传 `keyField: 'id'` |
| search 的 opts.signal 必须透传 | `createDictDataSource` 已透传；手写时若不透传 `signal`，`searchAsync` 的 abort 机制无效，快速输入会产生堆积请求 |
| loadByKeys 的 pageSize 要够大 | `createDictDataSource` 用 `Math.max(minPageSizeForKeys, keys.length)`；手写时若 pageSize 固定小值，批量回显时会截断 |
| 内存数据源也要设 `items` | `lookupByKeyAsync` 优先查 `source.items`；不设则每次都走远程，性能差 |
