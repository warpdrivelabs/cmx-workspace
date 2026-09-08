# 新建态配方与保存链路

> 本文件是 doc-crud-pages 技能的 references 细节层（从 SKILL.md 下沉，内容未改）。返回决策入口：[../SKILL.md](../SKILL.md)

## 五、新建态配方（详情页的 id 为空分支）

新建态是详情页的**关键且易错**部分。核心：空装载后立即预建根行，让用户从一开始就编辑 DataSet 真实行。

### 5.1 空装载 + 预建根行

```js
// initPage 新建态分支
loadDef.filter = "id:-1";   // 空装载：初始化 _def/_collector/空根表
ms.loadDoc(loadDef).then(function(){
  try { host.ensureBatchRow(); } catch(_) {}   // 立即预建根行
  host.refreshCounts();
});
```

### 5.2 ensureBatchRow：预建根行 + 合并用户输入

```js
// pageFn: ensureBatchRow
var ms = host.ms;
var ds = ms.getRootDataSet("cv_batch");
if (!ds) return null;
if (ds.rows && ds.rows.length > 0) return ds.rows[0];   // 已有根行直接返回

// 根表空时新建根行。先读 batchForm.getData() 把用户已输入的值合并进来
// （用户可能在预建完成前就编辑了表单，值在游离 _row 里）
var userInput = {};
try {
  var form = host.batchForm;
  if (form && typeof form.getData === "function") {
    var d = form.getData() || {};
    for (var k in d) { if (d[k] != null && String(d[k]).trim() !== "") userInput[k] = d[k]; }
  }
} catch(_) {}

var todayStr = /* 今日 yyyy-MM-dd */;
var newRow = {
  id: "b" + (++host.__seq),                          // 临时 id（后端铸号时换真实雪花 id）
  doc_no: "<前缀>" + todayStr.replace(/-/g,"") + String(Date.now()).slice(-6),
  doc_date: todayStr,
  // ... 其他默认值
};
for (var uk in userInput) { if (userInput[uk] != null) newRow[uk] = userInput[uk]; }  // 用户输入优先

var CmxDataSet = (globalThis.__cmxDataComp || {}).CmxDataSet;
var children = {};
if (CmxDataSet) children.cv_header = new CmxDataSet();   // 预建第一层子数据集
ds.addRow(newRow, children);
if (ds.moveToId) ds.moveToId(newRow.id);

// 关键：addRow 后从 ds.rows 重新取真实行引用（ms 内部可能用包装对象）
var realRow = null;
for (var ri = 0; ri < ds.rows.length; ri++) {
  if (String(ds.rows[ri].id) === String(newRow.id)) { realRow = ds.rows[ri]; break; }
}
return realRow || ds.rows[0] || newRow;
```

> **为什么要预建根行**：loadDoc(id:-1) 后根表为空，此时 batchForm 绑定的是游离 `_row = {}`（不在 DataSet 里）。用户编辑写入游离对象，点"新增子行"时 ensureBatchRow 发现根表空 → 新建根行用默认值 → 用户输入丢失。预建根行让用户一开始就编辑真实行，彻底避免。

### 5.3 新增子行：_ensureChildDs + 继承父字段

子层数据集需要懒创建 + 注册到 ms 监听 + 绑 collector：

```js
// pageFn: _ensureChildDs(parentRow, childId, parentPath)
if (!parentRow._children) parentRow._children = {};
if (!parentRow._children[childId]) {
  var CmxDataSet = (globalThis.__cmxDataComp || {}).CmxDataSet;
  parentRow._children[childId] = CmxDataSet ? new CmxDataSet() : null;
  var ms = host.ms;
  var fullPath = (parentPath || "") + (parentPath ? "." : "") + childId;
  var newDs = parentRow._children[childId];
  if (newDs) {
    if (ms._registerDsListeners) ms._registerDsListeners(newDs, fullPath);      // 事件监听
    if (ms._collector && ms._collector._bindRecursive) ms._collector._bindRecursive(newDs, fullPath);  // 变更收集
  }
}
return parentRow._children[childId];
```

新增子行时设 `upper_id` 指向父行，继承父行的单据标识字段：

```js
// pageFn: addHeader（新增 L2 行）
var batchRow = host.ensureBatchRow();
var childDs = host._ensureChildDs(batchRow, "cv_header", "cv_batch");
var newRow = { id: "h" + (++host.__seq), upper_id: batchRow.id, /* 业务字段默认值 */ };
// 继承父批的单据标识
var baseFields = ["doc_no","doc_type_id","entity_id","doc_date","doc_status"];
for (var i=0;i<baseFields.length;i++){ var k=baseFields[i]; if (batchRow[k] != null && batchRow[k] !== "") newRow[k] = batchRow[k]; }
newRow.line_no = childDs.rows.length + 1;
childDs.addRow(newRow, kids);   // kids 里可预建再下一层
if (childDs.moveToId) childDs.moveToId(newRow.id);
ms._renderView && ms._renderView("cv_batch.cv_header");   // 触发 grid 刷新
```

### 5.4 删除子行：需选中 + 二次确认

```js
// pageFn: removeXxx
var g = host.shadowRoot.querySelector('#xxxGrid');
var selId = g._selectedId;
if (!selId) { host._cmxNotify('warn', '请先选择一条...'); return; }
host._libConfirm('删除将连同其下子行一起移除，确定？', '删除确认').then(function(ok){
  if (!ok) return;
  if (g._ds && g._ds.removeRow) g._ds.removeRow(selId);
  host.refreshCounts();
});
```

---

## 六、保存链路（最易出错的环节）

保存涉及四个关键点：提交编辑中的单元格 → saveDoc → 后端铸号 → idMap 回写。每一步都有坑。

### 6.1 保存前先 commitEdit（收拢编辑中的单元格）

**问题**：revo-grid 里用户正在编辑的单元格（焦点未失），值还没 dispatch 到 DataSet，直接 saveDoc 会丢最后一格。

**解决**：保存前对所有可编辑 grid 调 `cmx-revo-grid.commitEdit()`（组件库公共方法）：

```js
// pageFn: saveVoucher
var grids = ['#headerGrid','#gAcc','#auxGrid'].map(function(sel){
  return host.shadowRoot.querySelector(sel);
}).filter(Boolean);
Promise.all(grids.map(function(g){
  return typeof g.commitEdit === 'function' ? g.commitEdit() : Promise.resolve();
})).then(function(){
  return ms.saveDoc();
}).then(function(r){
  host._cmxNotify('ok', '保存成功');
}).catch(function(e){
  if (!e || !e.conflict) host._cmxNotify('error', '保存失败：' + (e && e.message || e));
});
```

> `commitEdit()` 通过合成 Enter 键事件走 revo-grid 原生 save 链路（Enter→afteredit→写回 DataSet）。无编辑态时立即 resolve，零副作用。

### 6.2 后端铸号与 idMap（保存后临时 id 换真实 id）

**机制**：前端用临时 id（`b1`/`h1`）新增行。保存时后端 `mint_ids_for_changeset` 给新增行铸真实雪花 id，并重路由子行 `upper_id`。后端 `SaveResult.idMap` 返回「临时id→真实id」映射。

**前端自动处理**：组件库 `saveDocData` 在 return data 前调 `collector.applyIdMap(data.idMap)`，自动替换 DataSet 行 id + 重路由 upper_id + 同步 collector.inserted key。**二次保存不断链**（无需手动重载）。

**不需要做的事**：保存后不必整页 reload 来"刷新 id"。applyIdMap 已把临时 id 换成真实 id。如需刷新 `update_time` 乐观锁基线或显示落库最终值，可补一次 `loadDoc({filter:'doc_no:' + row.doc_no})` 重载作双保险。

### 6.3 doc_no（单据号）的前端生成与后端铸号

当前 `doc_no` 在前端 `ensureBatchRow` 里生成（日期+时间戳）。**已知局限**（需业务确认是否要改后端铸号）：
- 并发下可能撞号（同秒新增）。
- 前端生成可被篡改（F12 改请求体）。
- 若要后端铸号：在 `saver.rs` 的 `mint_ids_for_changeset` 同侧加 doc_no 铸号钩子（对 doc_no 为空的新增行补号），前端留空。**改后端铸号影响所有 doc 类型，需评审。**

---
