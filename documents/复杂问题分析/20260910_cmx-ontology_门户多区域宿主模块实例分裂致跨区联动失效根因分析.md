# 门户多区域宿主模块实例分裂致跨区联动失效根因分析

> 模块：cmx-ontology 本体设计工作台（portal.onto.designer）× cmx-portal-manager 工作台框架
> 日期：2026-09-10 · 关联改动：`backend/cmx-container/assets/onto/web/ui-native/onto/designer.js`（D15）

## 一、现象

本体设计工作台四区布局（model / explorer / content / property）在门户主工作台里出现两类故障：

1. **点击左侧对象类型 / 关系类型，右侧属性栏纹丝不动**——且不是偶发，主工作台路径下稳定复现；而换别的宿主形态（如浮动窗，三区同 scope）就是好的。
2. 伴随问题：点击后哪怕联动，也要等详情接口返回才更新；后台刷新（DAM 树 / 惰性加载 / 自动落库）撞上详情在途时，右栏还会渲染**上一个选中元素**的陈旧数据。

## 二、排查过程（关键三步）

1. **同步读验证**：点击行后当帧读右栏 DOM——不更新；再读 explorer 行高亮——已切换；再读画布节点高亮——**跟手了**。由此判定：explorer 与 content 是同一个模块实例（state.sel 已更新、`state.el.selectNode` 生效），而 property 区纹丝不动——疑似独立实例。
2. **scope 链实测**：从三个 `cmx-native-pages-host` 分别向上爬 `parentElement`，三者都能解析到 `data-cmx-workspace-id = "tab:onto-designer"`（挂在 `cmx-ws-tab-cache-root` 上）。scope id 相同，理论上 `getScope(id)` 返回同一 workspace 对象、`_scopeModuleCache`（WeakMap）应命中同一份模块。
3. **结论反推**：property 宿主拿到独立实例的唯一解释是**它物化模块的时刻，scope 判定失败了**。`scopeIdFromDom` 从宿主向上爬的是 `parentElement`，而宿主挂载时序中存在「宿主已 import、cache-root（含 workspace id 属性）尚未挂到自身祖先链」的窗口；此外属性面板是可折叠面板，其宿主重建路径与 explorer/content 的 tab 缓存根路径不同。只要物化瞬间爬不到 id，`this.workspace = null` → `scopeNativePageModuleCache(null)` 返回 null → 走 `importNativePageModule` **每次新建 Blob URL 动态 import**——一个全新的模块实例，且不进任何缓存。

### 根因链

```
native 页模块按 workspace scope 物化（WeakMap<scope, Map<pageId, module>>）
  └─ scope 判定 = scopeIdFromDom(host)：parentElement 上溯找 data-cmx-workspace-id
       └─ 属性面板宿主挂载时序特殊（折叠面板独立重建路径 / cache-root 属性挂载晚于 import）
            └─ 物化瞬间 scope = null → 不进实例缓存 → 每宿主各 import 一份
                 └─ designer.js 的模块级 const state 裂成多份
                      └─ explorer 实例的 selectElement 更新自己的 state.sel
                         property 实例渲染自己的 state.sel（永远 null）→ 右栏不动
```

## 三、解决方案

### 页面侧修复（本次落地，`designer.js` D15）

核心思想：**跨区联动的状态不放在模块级变量里，按 workspace scope 挂到 `globalThis` 单例**。同一 scope 的所有模块实例（无论裂成几份）读写同一份状态；不同 scope（并列 tab 双开同一页面）天然隔离——保住「scope 隔离」的设计初衷。

```js
const __S = globalThis.__cmxOntoDesigner || (globalThis.__cmxOntoDesigner = { states: new Map(), dc: null, component: null, load: null });
let state = null; // mount() 时按宿主 scope 绑定
function stateFor(host) {
  let key = 'global';
  for (let cur = host; cur; cur = cur.parentElement) {
    if (cur instanceof HTMLElement && cur.dataset.cmxWorkspaceId) { key = cur.dataset.cmxWorkspaceId; break; }
  }
  let s = __S.states.get(key);
  if (!s) { s = { scopeKey: key, loaded: false, hosts: new Set(), el: null, /* ...全量字段 */ }; __S.states.set(key, s); }
  return s;
}
function mount(ctx, view) {
  const host = ctx.host; state = stateFor(host); state.hosts.add(host); host.__view = view;
  // ...
}
```

配套三处（缺一不可）：

| 配套点 | 为什么必须 |
| --- | --- |
| `_suppressDiff` 移入共享 state | 落库抑制是跨实例协议：保存动作发生在 property 实例（`state.el.addLink`），而 `spec-change` 监听注册在 content 实例——标记放模块级，另一个实例不认账，会产生假数据级 diff（误弹删除确认 / 误标未落库） |
| `loadAll` / 组件源 / datacomp 子集的进行中 Promise 挂 `__S` 共享 | 三实例并发首挂时，若各持各的 Promise，会并发跑 3 次 `loadAll`（3×50 个请求）、拉 3 份 115KB 组件源 |
| Inspector 渲染加 `detail.apiName === sel.id` 守卫 | 状态共享后右栏由任意实例刷新，守卫防「详情在途 + 后台 refresh」竞态渲染陈旧元素（对象/函数/动作三个面板原本就没有守卫） |

### portal 侧根治方向（未动，评估结论）

`scopeIdFromDom` 只爬 `parentElement`、跨不出 shadow root，是分裂的制度性温床；根治需：① 爬链支持 `cur.parentElement || cur.getRootNode()?.host` 穿 shadow 边界；② 保证三区宿主挂载前 cache-root（含 workspace id）已在祖先链上。**本次不动 portal 的原因**：影响所有 native 页的实例物化路径，回归面大（flow 待办中心等多区页共用此机制）；页面侧 globalThis 修复已完整闭环且对宿主形态免疫。portal 侧修复作为独立改造另行评估。

## 四、最佳实践

1. **native 页跨区状态禁止放模块级变量**。必须假设「同一页面的多个区域宿主可能拿到不同的模块实例」（scope 物化 + 宿主挂载时序决定，页面无法控制）。跨区联动状态一律按 `data-cmx-workspace-id` 键挂 `globalThis` 单例：同 scope 共享、异 scope 隔离。
2. **跨实例事件协议同样入共享状态**。凡「A 实例发动作、B 实例监听」的旗标（落库抑制、回声抑制 `_selSync` 等），放共享 state；放模块级等于协议失效。
3. **进行中的加载 Promise 全局共享**。多实例并发首挂时防重复装载（网络风暴放大器：N 实例 × 全量请求）。
4. **首屏装载严禁门控在 `requestAnimationFrame` 上**。rAF 在隐藏页签 / 后台 webview 里冻结不触发（Chrome 对隐藏页停帧），页面会永远停在加载占位——这是「偶发挂死」的另一种机制。用 `setTimeout(0)`（后台至多被钳到 1s/次，仍会完成）。本次 designer/explorer/workshop 三页一并修复。
5. **Inspector 渲染必须校验 `detail.apiName === 当前选中`**。详情异步装载期间任何路径触发重渲，都会把上一个选中元素的陈旧 detail 画成本面板（「点了没变化」的第二成因）。
6. **排查此类问题的手法**：不要只看「点击后最终更没更新」，要**当帧同步读各区域 DOM**并分别制造可观测标记（行高亮 / 画布高亮 / 面板头），三角定位哪两个区共享实例；再用 `parentElement` 爬链实测各宿主解析到的 scope id，与物化时刻的时序对账。

## 五、验证记录

- rAF 禁用条件下（模拟隐藏页签）四区装载成功——挂死机制闭环。
- 真实门户路由 `/view/onto-designer`：点对象/关系类型右栏当帧跟手（`📦 Type2` / `🔗 纵向关系 dgVert`），行高亮互斥正确。
- 删/建关系回归：DELETE 1 请求、POST 1 请求，画布边、左树计数、右栏 Inspector 三区同步（跨实例），backing.fk 落库完整，撤销栈保留。
