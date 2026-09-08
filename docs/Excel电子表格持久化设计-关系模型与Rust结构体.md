# Excel 电子表格持久化设计：关系模型 + 稳定身份 + Rust 结构体

> 主题：把一个多 sheet 的 Excel 电子表格（workbook / sheet / 行 / 列 / 单元格 / 数据 / 公式）持久化到关系型数据库，并给出对应的 Rust 内存结构体设计（采用「稳定身份行列」方案）。

---

## 目录

1. [设计目标与核心矛盾](#一设计目标与核心矛盾)
2. [关系型数据库表设计](#二关系型数据库表设计)
3. [位置坐标 vs 稳定身份：会不会"错位"](#三位置坐标-vs-稳定身份会不会错位)
4. [Rust 结构体设计（稳定身份方案）](#四rust-结构体设计稳定身份方案)
5. [关键取舍速查](#五关键取舍速查)

---

## 一、设计目标与核心矛盾

电子表格持久化的核心矛盾：

- **表面是二维网格，实际极度稀疏**：一个 sheet 理论上 100 万行 × 1.6 万列，但有数据的可能只有几千格。
- **单元格同时承载四类信息**：值、公式、缓存结果、样式。

所以设计目标是：

| 目标 | 手段 |
|------|------|
| 稀疏存储 | 只存非空格 / 非默认行列，空白不入库 |
| 值带类型 | `value_type` 判别 + 分类型列（数值/文本/布尔/日期/错误） |
| 公式与缓存结果并存 | `formula` 文本 + 缓存值同时存，不重算也能显示 |
| 样式/字符串去重共享 | 抽独立表 + hash 去重，单元格只存外键 |

---

## 二、关系型数据库表设计

### 2.1 ER 概览

```
workbook (工作簿)
 └─< sheet (工作表)
      ├─< sheet_column (列定义，仅非默认列)
      ├─< sheet_row    (行定义，仅非默认行)
      ├─< cell         (单元格，仅非空格)   ──> style (样式，多对一共享)
      │                                      ──> shared_string (字符串，多对一共享)
      ├─< merged_region(合并区域)
      └─< defined_name (命名区域，也可挂 workbook 级)
```

关键点：`sheet_column / sheet_row / cell` 都**只存"有内容/非默认"的记录**，空白格不入库。

### 2.2 核心设计决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 单元格存储 | 稀疏（一格一行，`(sheet_id,row,col)` 唯一） | 二维实体表会爆炸且 99% 是空 |
| 值的类型 | 加 `value_type` 判别字段 + 分类型列 | 单元格可为 数值/文本/布尔/日期/错误，类型化才能正确比较、聚合 |
| 公式 | `formula` 文本 **与** 缓存结果**同时存** | 不重算也能直接显示；重算引擎再用 formula |
| 字符串 | 抽 `shared_string` 表去重 | 同一文本（如"合计"）反复出现，共享省空间（Excel 自身也这么做） |
| 行列元数据 | 单独表，只存非默认（改过行高/列宽/隐藏） | 绝大多数行列是默认值，不必每行都存 |
| 样式 | 抽 `style` 表，单元格引用 `style_id` | 样式高度重复，去重后单元格只存一个外键 |

### 2.3 建表 DDL（PostgreSQL 语法）

```sql
-- 1. 工作簿
CREATE TABLE workbook (
  id            BIGINT PRIMARY KEY,
  name          VARCHAR(255) NOT NULL,
  file_name     VARCHAR(255),
  author        VARCHAR(128),
  active_sheet  INT,                       -- 默认激活的 sheet 序号
  properties    JSONB,                     -- 其余文档属性（公司、关键字等）
  created_at    TIMESTAMPTZ DEFAULT now(),
  updated_at    TIMESTAMPTZ DEFAULT now()
);

-- 2. 工作表
CREATE TABLE sheet (
  id            BIGINT PRIMARY KEY,
  workbook_id   BIGINT NOT NULL REFERENCES workbook(id) ON DELETE CASCADE,
  name          VARCHAR(255) NOT NULL,
  sheet_index   INT NOT NULL,              -- tab 顺序
  state         SMALLINT DEFAULT 0,        -- 0可见 1隐藏 2深度隐藏
  dimension     VARCHAR(32),               -- 已用区域，如 'A1:Z100'（缓存，便于快速取范围）
  frozen_rows   INT DEFAULT 0,             -- 冻结窗格
  frozen_cols   INT DEFAULT 0,
  default_row_height NUMERIC,
  default_col_width  NUMERIC,
  UNIQUE (workbook_id, name),
  UNIQUE (workbook_id, sheet_index)
);

-- 3. 列定义（仅存改过宽度/隐藏/默认样式的列）
CREATE TABLE sheet_column (
  id          BIGINT PRIMARY KEY,
  sheet_id    BIGINT NOT NULL REFERENCES sheet(id) ON DELETE CASCADE,
  col_index   INT NOT NULL,                -- 1-based 列号（A=1）
  width       NUMERIC,
  hidden      BOOLEAN DEFAULT FALSE,
  style_id    BIGINT REFERENCES style(id), -- 整列默认样式
  UNIQUE (sheet_id, col_index)
);

-- 4. 行定义（仅存改过行高/隐藏的行）
CREATE TABLE sheet_row (
  id          BIGINT PRIMARY KEY,
  sheet_id    BIGINT NOT NULL REFERENCES sheet(id) ON DELETE CASCADE,
  row_index   INT NOT NULL,                -- 1-based 行号
  height      NUMERIC,
  hidden      BOOLEAN DEFAULT FALSE,
  style_id    BIGINT REFERENCES style(id),
  UNIQUE (sheet_id, row_index)
);

-- 5. 共享字符串表
CREATE TABLE shared_string (
  id          BIGINT PRIMARY KEY,
  workbook_id BIGINT NOT NULL REFERENCES workbook(id) ON DELETE CASCADE,
  text        TEXT NOT NULL,
  text_hash   BYTEA,                       -- 对 text 做 hash，便于去重查找
  rich_runs   JSONB,                       -- 富文本分段（同格多色/多字体）时存格式段
  UNIQUE (workbook_id, text_hash)
);

-- 6. 单元格（核心，稀疏）
CREATE TABLE cell (
  id            BIGINT PRIMARY KEY,
  sheet_id      BIGINT NOT NULL REFERENCES sheet(id) ON DELETE CASCADE,
  row_index     INT NOT NULL,
  col_index     INT NOT NULL,
  value_type    SMALLINT NOT NULL,         -- 0空 1数值 2文本(共享) 3布尔 4日期 5错误 6内联文本
  value_number  DOUBLE PRECISION,          -- value_type=1/4(日期序列号) 用
  string_id     BIGINT REFERENCES shared_string(id),  -- value_type=2 用
  value_inline  TEXT,                       -- value_type=6 不入共享表的临时文本
  value_bool    BOOLEAN,                    -- value_type=3 用
  value_error   VARCHAR(16),               -- value_type=5，如 '#DIV/0!'
  formula       TEXT,                       -- 公式（A1 引用，如 '=SUM(A1:A10)'），非公式格为 NULL
  formula_type  SMALLINT DEFAULT 0,        -- 0普通 1数组 2共享 3动态溢出
  formula_ref   VARCHAR(32),               -- 数组/共享公式的作用范围
  style_id      BIGINT REFERENCES style(id),
  comment       TEXT,                       -- 批注（量大可单拆 cell_comment 表）
  UNIQUE (sheet_id, row_index, col_index)
);
-- 关键索引：按区域取数 / 按列扫描
CREATE INDEX idx_cell_sheet_rowcol ON cell (sheet_id, row_index, col_index);
CREATE INDEX idx_cell_sheet_col    ON cell (sheet_id, col_index, row_index);

-- 7. 样式（去重共享；半规范化，font/fill/border/对齐拆 JSONB）
CREATE TABLE style (
  id            BIGINT PRIMARY KEY,
  workbook_id   BIGINT NOT NULL REFERENCES workbook(id) ON DELETE CASCADE,
  number_format VARCHAR(64),               -- 数字格式串，如 '#,##0.00' / 'yyyy-mm-dd'
  font          JSONB,                     -- {name,size,bold,italic,color}
  fill          JSONB,                     -- {pattern,fgColor,bgColor}
  border        JSONB,                     -- {top,bottom,left,right:{style,color}}
  alignment     JSONB,                     -- {horizontal,vertical,wrapText,indent}
  style_hash    BYTEA,                     -- 整体 hash，去重用
  UNIQUE (workbook_id, style_hash)
);

-- 8. 合并区域
CREATE TABLE merged_region (
  id          BIGINT PRIMARY KEY,
  sheet_id    BIGINT NOT NULL REFERENCES sheet(id) ON DELETE CASCADE,
  start_row   INT NOT NULL,
  start_col   INT NOT NULL,
  end_row     INT NOT NULL,
  end_col     INT NOT NULL
);

-- 9. 命名区域（workbook 级 sheet_id 为 NULL；sheet 级则填 sheet_id）
CREATE TABLE defined_name (
  id          BIGINT PRIMARY KEY,
  workbook_id BIGINT NOT NULL REFERENCES workbook(id) ON DELETE CASCADE,
  sheet_id    BIGINT REFERENCES sheet(id),
  name        VARCHAR(255) NOT NULL,
  refers_to   TEXT NOT NULL                -- 如 "Sheet1!$A$1:$B$10"
);
```

### 2.4 要点说明

**1. 行号/列号 vs 引用串**
用整数 `row_index / col_index` 而不是 `"A1"` 字符串存——便于范围查询（`WHERE row_index BETWEEN 1 AND 100`）、排序、相对引用计算。展示时再转 A1。

**2. 公式格的双轨存储**
一个公式格同时有 `formula='=SUM(A1:A10)'` **和**缓存结果（`value_type=1, value_number=55`）。打开文件直接显示缓存值，无需重算；只有数据变了才触发重算引擎更新缓存。这是 Excel/xlsx 本身的做法。

**3. 日期的存法**
Excel 日期本质是数值（序列号 + 数字格式）。建议 `value_type=4` 仍存进 `value_number`（序列号），靠 `style.number_format` 决定显示成日期——和 Excel 语义一致；若业务上想直接 SQL 查日期，可加一列 `value_datetime` 冗余。

**4. 样式与字符串的 hash 去重**
入库时对样式/字符串算 hash，命中已有记录就复用 `id`。一个上万格的报表，样式可能只有几十种、字符串重复率极高，去重后体积大幅下降。

### 2.5 可选的高级表

```sql
-- 公式依赖图（要做增量重算引擎时才需要）
CREATE TABLE cell_dependency (
  sheet_id   BIGINT, dependent_cell_id BIGINT,   -- 依赖方（公式格）
  precedent_sheet_id BIGINT,
  precedent_range    VARCHAR(32)                 -- 被依赖的格/区域
);

-- 条件格式、数据验证（下拉、范围校验）
CREATE TABLE conditional_format (...);
CREATE TABLE data_validation (...);

-- 图表、图片等浮动对象（通常存元数据 + 二进制走对象存储）
CREATE TABLE drawing (...);
```

---

## 三、位置坐标 vs 稳定身份：会不会"错位"

### 3.1 cell 是有自己的 id 的

`cell` 表里有 `id BIGINT PRIMARY KEY`，这是它的**稳定身份**。`(sheet_id, row_index, col_index)` 只是加了个 **UNIQUE 约束**当"自然键/坐标"。真正的设计分叉是：

> cell 是按**位置坐标**（row_index/col_index 整数）定位，还是该按**外键**（FK 到 sheet_row.id / sheet_column.id）定位？

### 3.2 位置坐标方案会不会"错位"

不会**静默错位**，但插入/删除行列时它不是 O(1)，而是要做一次批量重排。

**在第 5 行前插入一行**，必须在同一事务里：

```sql
UPDATE sheet_row SET row_index = row_index + 1 WHERE sheet_id=? AND row_index >= 5;
UPDATE cell     SET row_index = row_index + 1 WHERE sheet_id=? AND row_index >= 5;
-- 还要重写引用了被移动单元格的公式：=A10 → =A11
```

只要三步在一个事务里做完，数据正确、不错位。问题是：

1. 下方有几十万格时，这是一次**大批量 UPDATE**；
2. **公式重写**容易漏（`=A10` 必须变 `=A11`），这才是真正的隐患。

> ⚠️ **铁律：位置坐标是"可变坐标"，不是"稳定身份"。**
> 任何外部表要持久引用某个格，必须存 `cell.id`（代理主键），**绝不能存 (row,col)**——否则插一行，外部引用就指错格了。这正是"错位"的根因。

> 补充：位置坐标方案其实就是 **xlsx 文件格式本身的做法**（`<c r="B5">` 是位置式），Excel 插入行时也是整体重写引用。所以它不"错"，只是把成本压在结构变更上。

### 3.3 替代方案：稳定身份 + 排序列

频繁在中间插删行列（尤其在线协同编辑）时，应让 cell 引用稳定身份，行列各自带"顺序"字段：

```sql
-- 行：surrogate id 永不变，position 决定视觉顺序
CREATE TABLE sheet_row (
  id        BIGINT PRIMARY KEY,        -- 稳定身份(cell 引用它)
  sheet_id  BIGINT NOT NULL,
  position  NUMERIC NOT NULL,          -- 视觉顺序(用小数/稀疏值)
  height NUMERIC, hidden BOOLEAN,
  UNIQUE (sheet_id, position)
);
-- 列同理 sheet_column(id, position, ...)

CREATE TABLE cell (
  id       BIGINT PRIMARY KEY,
  row_id   BIGINT NOT NULL REFERENCES sheet_row(id) ON DELETE CASCADE,
  col_id   BIGINT NOT NULL REFERENCES sheet_column(id) ON DELETE CASCADE,
  -- 值/公式/样式同前
  UNIQUE (row_id, col_id)
);
```

- **插入一行 = 插入 1 条 sheet_row**（position 取邻居之间的值），所有 cell 的 row_id 不动 → **零 cell 改动、零错位**。
- **公式**也别存 A1 文本，存成对 (row_id,col_id) 的引用（或相对偏移），插行后公式天然不破。

代价：

- "取视觉第 5 行第 3 列的格"要 join 排序；按区域查也要靠 position 排序，**读路径变复杂**。
- A1 引用、导入/导出 xlsx 时要在 position ↔ A1 之间翻译。

**position 的坑**：若 position 用密集整数 1,2,3...，中间插入还是要批量重排。要真正 O(1)，用**稀疏/小数排序**（初始 1000、2000、3000，插入取 1500），或 LexoRank 这类分数索引；隔段时间后台重整。

### 3.4 两方案对比与选型

| 维度 | 位置坐标 | 稳定身份 + 排序列 |
|------|---------|------------------|
| 插/删行列 | 批量 UPDATE 索引 + 重写公式，O(受影响格数) | 插 1 行，cell 不动，O(1) |
| 读单格/区域 | 直接 `WHERE row_index BETWEEN` 极简 | 需按 position join 排序 |
| 公式 | A1 文本，插删必重写 | 按身份引用，插删不破 |
| 与 xlsx 映射 | 1:1，导入导出最省事 | 需 position↔A1 翻译 |
| 复杂度 | 低 | 高 |

**选型规则**：

- **导入 / 归档 / 报表渲染 / 结构基本不变** → 位置坐标方案足够，别过度设计。
- **在线编辑、协同、频繁中间插删行列** → 稳定身份 + 稀疏排序 + 公式按身份引用。
- 真·实时多人协同到极致 → 关系型 per-cell 已不够，得上 CRDT/OT。

---

## 四、Rust 结构体设计（稳定身份方案）

稳定身份在 Rust 里的对应模式是 **slotmap / 世代竞技场（generational arena）**：插入返回稳定 key、删除不让其它 key 失效，正是"稳定身份"的教科书实现。

### 4.1 Cargo 依赖

```toml
[dependencies]
slotmap = "1"          # 稳定身份 key(行/列/表)
# serde = { version = "1", features = ["derive"] }   # 需要序列化再开
```

### 4.2 ID 类型

```rust
use slotmap::{new_key_type, SlotMap};
use std::collections::HashMap;

// 行/列/表用 slotmap 的世代 key —— 插入得到稳定 key，删除不影响其它 key
new_key_type! {
    pub struct SheetKey;
    pub struct RowKey;
    pub struct ColKey;
}

// 字符串/样式是「内容寻址去重池」，从不删除 → 用普通 u32 newtype 即可
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct StringId(u32);
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct StyleId(u32);
```

> 为什么不给 `Cell` 也来个 `CellKey`？因为 cell 的身份天然是 `(RowKey, ColKey)` 这对句柄——行列稳定，cell 坐标就稳定，**插入一行不会让任何 cell 错位**。

### 4.3 值、错误、公式

```rust
/// 单元格值：类型化枚举(对应 Excel 的数值/文本/布尔/日期/错误)
#[derive(Debug, Clone, PartialEq, Default)]
pub enum CellValue {
    #[default]
    Empty,
    Number(f64),
    Text(StringId),       // 走共享字符串池
    Bool(bool),
    DateSerial(f64),      // Excel 日期序列号；显示交给 number_format
    Error(CellError),
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CellError { Div0, NA, Name, Null, Num, Ref, Value, Spill }

#[derive(Debug, Clone)]
pub struct Formula {
    pub kind: FormulaKind,
    pub source: String,        // 公式文本(A1 或结构化)；也可换成 AST
    pub cached: CellValue,     // 缓存结果，打开不重算直接显示
    pub spill_range: Option<CellRange>,  // 数组/共享/动态溢出的作用域
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FormulaKind { Normal, Array, Shared, Dynamic }

/// 公式引用范围，务必用句柄而非 A1 文本(插删行不破)
#[derive(Debug, Clone, Copy)]
pub struct CellRange {
    pub start: (RowKey, ColKey),
    pub end:   (RowKey, ColKey),
}
```

### 4.4 Cell

```rust
#[derive(Debug, Clone, Default)]
pub struct Cell {
    pub value: CellValue,
    pub formula: Option<Box<Formula>>,  // Box：公式是少数派，装箱让普通格更小
    pub style: Option<StyleId>,
    pub comment: Option<StringId>,
}
```

> ⚠️ **Cell 里不存自己的 (row,col)**。它是 `HashMap<(RowKey,ColKey), Cell>` 的值，坐标在 key 里——避免冗余、杜绝"字段与 key 不一致"。cell 永远靠句柄被找到。

### 4.5 行 / 列（稳定身份，不存自己的 index）

```rust
#[derive(Debug, Clone, Default)]
pub struct Row {
    pub height: Option<f64>,    // None=默认行高
    pub hidden: bool,
    pub style: Option<StyleId>, // 整行默认样式
}

#[derive(Debug, Clone, Default)]
pub struct Column {
    pub width: Option<f64>,
    pub hidden: bool,
    pub style: Option<StyleId>,
}
```

> Row/Column **不带 position 字段，也不带 id**。id 是 slotmap key；**顺序由 Sheet 里一条 `Vec<RowKey>` 维护**。这比"position 小数排序"更简单。

### 4.6 Sheet

```rust
pub struct Sheet {
    pub name: String,
    pub state: SheetState,

    // 稳定身份存储
    pub rows: SlotMap<RowKey, Row>,
    pub cols: SlotMap<ColKey, Column>,
    pub cells: HashMap<(RowKey, ColKey), Cell>,  // 稀疏：只存非空格

    // 视觉顺序(真相源)：从上到下 / 从左到右
    pub row_order: Vec<RowKey>,
    pub col_order: Vec<ColKey>,

    pub merged: Vec<MergedRegion>,
    pub frozen_rows: u32,
    pub frozen_cols: u32,
    pub default_row_height: f64,
    pub default_col_width: f64,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum SheetState { #[default] Visible, Hidden, VeryHidden }

#[derive(Debug, Clone, Copy)]
pub struct MergedRegion {     // 角点也用句柄
    pub top_left: (RowKey, ColKey),
    pub bottom_right: (RowKey, ColKey),
}
```

### 4.7 Workbook

```rust
pub struct Workbook {
    pub name: String,
    pub sheets: SlotMap<SheetKey, Sheet>,
    pub sheet_order: Vec<SheetKey>,        // tab 顺序
    pub strings: StringPool,               // 全簿共享字符串去重池
    pub styles: StylePool,                 // 全簿样式去重池
    pub defined_names: Vec<DefinedName>,
}

#[derive(Debug, Clone)]
pub struct DefinedName {
    pub name: String,
    pub scope: Option<SheetKey>,           // None=全簿级
    pub range: CellRange,
}
```

去重池（内容寻址，append-only）：

```rust
#[derive(Default)]
pub struct StringPool {
    items: Vec<String>,
    dedup: HashMap<String, StringId>,
}
impl StringPool {
    pub fn intern(&mut self, s: &str) -> StringId {
        if let Some(&id) = self.dedup.get(s) { return id; }
        let id = StringId(self.items.len() as u32);
        self.items.push(s.to_owned());
        self.dedup.insert(s.to_owned(), id);
        id
    }
    pub fn get(&self, id: StringId) -> &str { &self.items[id.0 as usize] }
}
// StylePool 同理，key 用样式的结构体 hash
```

### 4.8 稳定身份的回报：插入一行

```rust
impl Sheet {
    /// 在视觉第 `visual_idx` 行前插入新行 —— 不触碰任何 cell，零错位
    pub fn insert_row_at(&mut self, visual_idx: usize, row: Row) -> RowKey {
        let key = self.rows.insert(row);          // O(1)，拿到稳定 key
        self.row_order.insert(visual_idx, key);   // 只挪 8 字节 key，不挪 cell/数据
        key
    }

    /// 取「视觉第 r 行、第 c 列」的格
    pub fn cell_at(&self, r: usize, c: usize) -> Option<&Cell> {
        let rk = *self.row_order.get(r)?;
        let ck = *self.col_order.get(c)?;
        self.cells.get(&(rk, ck))
    }

    /// 删除一行：移句柄 + 清该行的 cell(级联)
    pub fn remove_row(&mut self, key: RowKey) {
        self.rows.remove(key);
        self.row_order.retain(|&k| k != key);
        self.cells.retain(|&(rk, _), _| rk != key);   // 扫一遍清该行格
    }
}
```

对比 SQL 的位置坐标方案：插入行**不重排任何 cell、不重写公式**（公式用 `CellRange{RowKey,ColKey}` 引用，插行后句柄不变天然正确）。这正是"错位"被根除的地方。

### 4.9 两个顺序表示法的取舍

| | `Vec<RowKey>` 顺序表 | Row 里带 `position: f64` 小数排序 |
|---|---|---|
| 渲染(按序遍历) | O(n) 直接走 Vec，**免排序** | 每次 collect+sort 或自己维护缓存 |
| 中间插入 | 挪 key，O(n) memmove(只挪 8 字节) | O(1) 取邻居中点，但久了要重整 |
| 实现复杂度 | 低 | 中(小数耗尽/精度问题) |
| 适合 | 单机内存模型、渲染频繁 | 协同编辑/CRDT、并发插入冲突少 |

**默认选 `Vec<RowKey>`**：更简单、渲染零成本，插入挪的只是句柄不是数据。只有要做并发协同（LexoRank 分数索引）时才换 position 方案。

### 4.10 收尾要点

- **A1 文本 ↔ 句柄翻译**留在 I/O 边界：导入 xlsx 时把 `B5` 解析成 `(row_order[4], col_order[1])` 存句柄；导出时反向。结构体内部一律句柄，不存 A1。
- **CellValue 体积**：最大变体是 `f64`(8B)+tag，很小；故意没放 `Inline(String)` 变体——所有文本都 `intern` 进池，保持 `Cell` 紧凑。
- **序列化**：slotmap 支持 serde（开 feature），`new_key_type!` 的 key 可序列化往返；落库时再映射到关系表（RowKey→sheet_row.id）。
- **CellValue 默认值**用 `#[derive(Default)]` + `#[default] Empty`（Rust 1.62+ 枚举默认派生），省掉手写 `impl Default`。

---

## 五、关键取舍速查

| 场景 | DB 方案 | Rust 顺序方案 | 公式引用 |
|------|---------|--------------|---------|
| 导入 / 归档 / 报表渲染 / 结构不变 | 位置坐标(row_index/col_index) | — | A1 文本即可 |
| 在线编辑 / 频繁中间插删行列 | 稳定身份(row_id/col_id) + position | `Vec<RowKey>` 顺序表 | 句柄引用 `(RowKey,ColKey)` |
| 实时多人协同(极致) | 稳定身份 + 分数索引 | `position: f64` / LexoRank | 句柄引用 + CRDT/OT |

**三条铁律**：

1. **可变坐标 ≠ 稳定身份**：对外持久引用一律用代理主键 / slotmap key，绝不用 (row,col)。
2. **公式双轨存**：formula 文本 + 缓存结果同时存，打开免重算。
3. **去重共享**：字符串、样式用 hash / intern 去重，单元格只引外键，保持紧凑。

---

## 附：混合存储建议（实务）

实际系统常**混合**：

- 单元格走稀疏关系表（支持 SQL 查询 / 编辑 / 协同 / 增量重算）；
- 同时把原始 xlsx 二进制存对象存储做**归档与精确还原**（样式 / 图表 / 浮动对象细节难 100% 关系化）。
