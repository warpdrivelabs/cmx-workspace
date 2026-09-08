# CMXPortalManager + CMXHTMLDesigner 模型体系文档

> 一本给"完全不懂这个工程"的小白看的"模型 + 元数据 + 协调"入门书

---

## 这本书是什么

这两个项目的源代码里有一套完整的**模型体系**——"模型"你可以简单理解为"程序里描述业务数据的形状和规矩的模板"。

这套体系里有 6 种核心模型：

- **CmxDataSet**（数据集）
- **CmxColumnModel**（列模型）
- **CmxMasterSlave**（主从协调器）
- **CmxDCTMeta**（数据字典元数据）
- **CmxDOCMeta**（业务单据元数据）
- **FlexibleCombination**（弹性组合，别名 `ContextProfile`）

每一种都有自己的配置字段、运行行为、事件机制。它们组合在一起，让设计器里"拖拖拽拽 + 填几个字段"就能生成一个完整的业务页面（例如会计凭证、库存表单、交易明细）。

这本小书把这些东西**讲清楚**，按"故事 → 概念 → 字段 → 流程 → 例子"的顺序展开。

---

## 目录

### 入门三章

| # | 章节 | 你会得到什么 |
| --- | --- | --- |
| 00 | [术语表（速读版）](00-术语表-名词解释.md) | 一开始就看懂所有缩写 |
| 01 | [两个项目到底是干啥的](01-项目总览-两个项目干什么的.md) | CMXPortalManager / CMXHTMLDesigner 各扮演什么角色 |
| 02 | [模型体系全景图](02-模型体系全景图.md) | 一张图把 6 大模型和视图组件串起来 |

### 设计器侧

| # | 章节 |
| --- | --- |
| 03 | [模型面板——在设计器里怎么配](03-模型面板-在设计器里怎么配.md) |

### 模型详解（每种一个章节）

| # | 章节 | 重点 |
| --- | --- | --- |
| 04 | [CmxDCTMeta 数据字典模型](04-字典模型-CmxDCTMeta.md) | 字典表怎么定义 |
| 05 | [CmxDOCMeta 业务单据模型](05-单据模型-CmxDOCMeta.md) | 单据表怎么定义 |
| 06 | [基础元数据 BASE 是什么](06-基础元数据-BASE是什么.md) | DCT 和 base DCT 的区别（重点） |
| 07 | [CmxDataSet 数据集](07-数据集-CmxDataSet.md) | 树形数据长什么样 |
| 08 | [CmxColumnModel 列模型](08-列模型-CmxColumnModel.md) | 表格列怎么配置 |
| 09 | [CmxMasterSlave 主从协调器](09-主从协调器-CmxMasterSlave.md) | 主表 + 子表怎么联动（重点） |
| 10 | [FlexibleCombination 弹性组合](10-弹性组合-FlexibleCombination.md) | 上下文驱动的动态列（重点） |

### 进阶

| # | 章节 |
| --- | --- |
| 11 | [模型事件与脚本](11-模型事件与脚本.md) |
| 12 | [运行时初始化流程](12-运行时初始化流程.md) |
| 13 | [常用字段速查表](13-常用字段速查表.md) |
| 14 | [典型场景示例](14-典型场景示例.md) |
| 15 | [术语表（详细版）](15-术语表-详细版.md) |
| 16 | [后端 API 详解（cmx-container）](16-后端API详解.md) |
| 17 | [元数据 JSON 文件字段详解](17-元数据JSON文件字段详解.md) |
| 18 | [维度概念详解](18-维度概念详解.md) |

---

## 建议阅读路径

### 🟢 小白路径（先看 4 章再决定）

1. `00-术语表-名词解释.md` — 看懂名词
2. `01-项目总览-两个项目干什么的.md` — 知道这俩项目干啥
3. `02-模型体系全景图.md` — 一张图看明白
4. `14-典型场景示例.md` — 看个真实例子

读完上面 4 章，再回头看你感兴趣的模型。

### 🟡 完整路径（每章都看）

```
00 → 01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 09 → 10 → 11 → 12 → 13 → 14 → 15
```

### 🔵 重点问题路径

- **"字典模型和单据模型怎么定义"** → 04 → 05
- **"数据字典定义和字典基础元数据有什么区别"** → 04 → 06
- **"弹性组合怎么配置使用"** → 02 → 10 → 14 场景 1/2
- **"主从协调器是什么"** → 02 → 09 → 14 场景 1

---

## 文档约定

- 所有 mermaid 流程图都可以在 VSCode / Typora / GitBook 里直接渲染
- JSON 示例尽量不超过 30 行；超过的部分用 `...省略` 标注
- 出现"运行/运行时"时指的是**真实用户在 Portal 里打开页面**那一刻
- 出现"设计时/设计期"时指的是**开发者在 Designer 里拖拽配置**那一刻
- 字段名用 `code style` 标记，比如 `domain` `voucherTables` `aggregations`
- 文件名/路径用 [file:///...](file:///) 形式可点击跳转

---

## 配套资源

- 项目根目录：[file:///media/yqs/工作/rustspace/cmx](file:///media/yqs/工作/rustspace/cmx)
- 设计器源码：[file:///media/yqs/工作/rustspace/cmx/CMXHTMLDesigner](file:///media/yqs/工作/rustspace/cmx/CMXHTMLDesigner)
- 门户源码：[file:///media/yqs/工作/rustspace/cmx/CMXPortalManager](file:///media/yqs/工作/rustspace/cmx/CMXPortalManager)
- 数据组件库（cmx-data-comp）：[file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp](file:///media/yqs/工作/rustspace/cmx/packages/cmx-data-comp)
- Mermaid 源文件：`diagrams/` 子目录

---

> 这本小书由探索代码生成，2026-07-13 整理。
