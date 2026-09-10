---
name: menu-generator
description: 指导生成 CMX 门户菜单。当用户要求新增菜单 / 添加菜单 / 生成菜单 / 删除菜单 / 改菜单，或提到 menu-pages、菜单文件、menu_seed.sql（旧称 init_menu.sql）、菜单节点、ExplorerMenuNode、workspace-node 时必用。菜单增删改落到 menu-pages JSON 文件（定义真源）后须用 scripts/sync_menu_db.py 同步 cmx_menu 侧栏才生效；SQL（menu_seed.sql / 迁移文件）仅当用户主动要求"生成 SQL / 更新 SQL / 同步数据库"时才由脚本产出，避免文件与数据库脱节。**新增模块时不能只跑 sync_menu_db.py**：DAM 三表（cmx_domain/cmx_application/cmx_module）未注册的模块须先维护并执行模块创建 SQL（§四），模块行缺失侧栏不显示。
---

# 菜单生成器

指导你为 CMX 门户**新增 / 修改 / 删除菜单**：改 `backend/cmx-container/assets/model/data/menu-pages/**/<file>.json`（菜单文件，定义真源）后**必须同步 `cmx_menu` 表**（§3.4 `sync_menu_db.py`）侧栏才生效；`docs/sql/v2/platform/menu_seed.sql` 与迁移文件仅在用户主动要求生成 SQL 时由脚本产出。

> **铁律：菜单只改 `backend/cmx-container/assets/model/data/menu-pages/` 下的 JSON 文件，SQL 永远由脚本生成，不手写 SQL；改完 JSON 必须同步 `cmx_menu`（§3.4 `sync_menu_db.py`），侧栏才生效。** **默认不重生成 menu_seed.sql**：常规增删改 = 改 JSON + 同步 cmx_menu 即完成；只有当用户明确说"生成 SQL / 更新 SQL / 初始化新环境"时，才跑脚本产出 `menu_seed.sql`（v2） 等文件。用户未要求 SQL，不擅自跑生成脚本。
>
> **新增模块例外（§四）：不能只跑 `sync_menu_db.py`。** 侧栏域树（`POST /api/domains/tree`）直读 DAM 三表（`cmx_domain` / `cmx_application` / `cmx_module`），菜单挂在模块下——模块行不存在时，`sync_menu_db.py` 把菜单同步进 `cmx_menu` 了侧栏**也不会显示**。必须先维护并执行**模块创建 SQL**（迁移文件 + `init_dml.sql` 补录），再同步菜单。

---

## 一、核心数据流（必须理解）

```
backend/cmx-container/assets/model/data/menu-pages/<domain>/<app>/<module>/<file>.json   （你手写的源 · 定义真源）
        │
        │  ① 常规生效路径（必做）：改完 JSON 同步 cmx_menu ——
        │     python3 .agents/skills/menu-generator/scripts/sync_menu_db.py <菜单文件>（在工作区根执行）
        ▼
cmx_menu 表  ←── GET /api/menu/tree ←── 门户侧栏 + 菜单管理页（运行时唯一数据源）
        ▲
        │  ② 新环境初始化路径（可选，仅当用户要求 SQL）：
        │     node .agents/skills/menu-generator/scripts/gen_menu_migration.mjs（全量扫描，cwd 无关）
        │     产出 menu_seed.sql 后执行
docs/sql/v2/platform/menu_seed.sql                            （脚本生成，覆盖；仅 SQL 需求触发）
docs/sql/v2/platform/migrations/20260819_001_baseline.up.sql  （基线，含菜单建表与首迁历史，不动）
```

> **默认路径**：改 JSON → `sync_menu_db.py` 同步 cmx_menu → 浏览器刷新生效，**结束**。
> **SQL 路径（可选）**：新环境初始化或用户主动要 SQL 时，跑脚本产出 `menu_seed.sql`（v2） 并执行。
> **注意**：门户侧栏**只认 `cmx_menu`**（`GET /api/menu/tree`）。旧 `/api/menu-pages` 直读 JSON 的接口已在后端注释废弃（`crates/libs/cmx-apis/cmx-common-api/src/handlers/portal/mod.rs`，被 `POST /api/domains/tree` + `GET /api/menu/tree` 替代），"改 JSON 即生效"的说法**不再成立**。

- **模块（如总账 gl、报表 report）不属于菜单**，由 DAM 派生（`cmx_module` 表 + manifest），不落入 cmx_menu。**manifest 文件只是被 `cmx_module.manifest_path` 引用的资产，不会被自动入库**——模块注册必须显式执行 SQL（或经门户 DAM 管理页创建），`sync_menu_db.py` 只管 `cmx_menu`，替代不了这一步。
- 一个菜单文件 = 一个模块的菜单根节点集合。文件路径 `menu-pages/fi/cmxfico/gl/explorer-menu.json` 决定 `domain_code=fi, application_code=cmxfico, module_code=gl`。
- 模块 manifest（`backend/cmx-container/assets/portal/data/modules/<d>/<a>/<m>/module.json`）的 `resources.menus[].menuRef` 指向菜单文件，是 DAM 派生 → DB 回源的桥梁，必须与文件路径对齐。

---

## 二、菜单文件结构（ExplorerMenuNode）

文件顶层：`{ "version": 1, "items": [ <节点>, ... ] }`，或直接是数组。

**节点字段**（参考 `backend/cmx-container/assets/model/data/menu-pages/fi/cmxfico/gl/explorer-menu.json`）：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | **菜单内唯一标识**（如 `gl-portal-console`），映射到 cmx_menu.code。**强烈建议每个文件内的 id 都带文件专属 prefix**（见 §2.1），跨文件冲突脚本兜底加 `_dup` 后缀 |
| `name` | string | 内部名（路由/引用），入 definition.name |
| `caption` | string \| i18n对象 | 显示文案（中文）。字符串→cmx_menu.name；对象→definition.caption 保留 i18n |
| `icon` | string | UI5 图标名（如 `tabler-outline/file-spreadsheet`） |
| `permissionId` | string \| null | 权限码，映射 cmx_menu.fun_code（关联 cmx_permission.code） |
| `children` | array | 子菜单（递归） |
| `expanded` | boolean | 分组是否默认展开 |
| `type` | string | `"workspace-node"` 表示可打开工作区的功能节点 |
| `workspace` | object | type=workspace-node 时内联的工作区布局（见下） |
| `dialogspace` | object | 弹窗对话框配置 |
| `dirty` | boolean | 运行时态，不持久化（生成 SQL 时丢弃） |

**workspace 布局**（9 区域，每区域 `{caption,icon,views:[...]}`）：
区域键：`prepare` / `content` / `explorer` / `property` / `bottom` / `floatview` / `model` / `inner` / `embed`
每个 view：`{ id?, tabLabel?, type, icon?, data? }`，type ∈ `placeholder/html_pages/native_pages/html/iframe/link/json/code/markdown/split/menu-pages`。

### 2.1 id 命名与 prefix 规范（避免跨文件冲突）

> **铁律：cmx_menu.code 全局唯一。** 不同菜单文件中 `id` 一旦冲突，SQL 生成脚本会兜底加 `_dup` 后缀（丑且不稳），应在源头避免。

**每个 JSON 文件的菜单节点 id 都必须带文件专属 prefix**，从源头杜绝跨文件重复。约定如下：

| 维度 | 推荐做法 |
|---|---|
| **prefix 来源** | 用文件路径第 3 段 `module_code`（如 `gl` / `report` / `ar`），保证模块内自洽、跨模块天然隔离 |
| **根节点 id** | 直接用 prefix 本身（一个文件通常只有一个根），如 `gl` / `report` |
| **子节点 id** | 用 `<prefix>-<业务名>`，如 `gl-portal-console` / `report-portal-console` |
| **多文件同模块** | 用 `<module>-<file-stem>` 作 prefix，如 `gl-explorer` / `gl-tree`（同一模块下多个文件不冲突） |
| **跨模块同业务** | 各自带自己模块的 prefix，自然不同：`gl-voucher` vs `report-voucher` |

**示例对比**：

```jsonc
// ❌ 不推荐：裸 id，跨文件极易冲突（gl 文件与 report 文件都有 "voucher"，脚本只能加 _dup）
{
  "id": "voucher"
}

// ✅ 推荐：带文件专属 prefix
{
  "id": "gl-voucher"        // gl 模块
}
{
  "id": "report-voucher"    // report 模块
}
```

**实际项目范例**：
- `backend/cmx-container/assets/model/data/menu-pages/fi/cmxfico/report/report-menu.json` 根 `id: "report"`，子节点 `report-portal-console` / `report-user-edit` / `report-grp-pages` 等
- `backend/cmx-container/assets/model/data/menu-pages/fi/cmxfico/gl/explorer-menu.json` 根 `id: "gl"`，子节点建议改为 `gl-portal-console` / `gl-user-edit` / `gl-grp-pages` 等

**冲突兜底**：即使按上述规范写，脚本仍保留 `_dup` 兜底机制（按路径排序后扫到冲突 code 自动加后缀），保证不会因冲突导致 SQL 生成失败；新写菜单不要依赖兜底，应主动用 prefix。

---

## 三、操作流程（新增/修改/删除菜单）

> **改 JSON + 同步 cmx_menu**：JSON 是定义真源，侧栏运行时从 `cmx_menu` 回源，所以每个流程都以「改 JSON → 跑 `sync_menu_db.py` 同步（直写 DB，不经 SQL 文件）」收尾。"跑脚本生成 menu_seed.sql"仅当用户主动要求 SQL 时才执行。

### 3.1 新增菜单节点

1. **定位目标文件**：`backend/cmx-container/assets/model/data/menu-pages/<domain>/<app>/<module>/<file>.json`。模块不存在则新建文件（需同时建 manifest + DAM 注册，见 §四）。
2. **在 items 数组或某节点 children 中插入新节点**，按上表字段填写。`id` **必须带文件专属 prefix**（见 §2.1，如 `<module>-<业务名>`），保证跨文件不冲突；只在文件内唯一不够。
3. 跑 `sync_menu_db.py` 同步 cmx_menu（§3.4）——侧栏刷新即生效。
4. **（可选 · 仅当用户要求 SQL 时）跑脚本重生成**（在仓库任意位置均可，脚本自动定位 cmx-container）：
   ```bash
   node .agents/skills/menu-generator/scripts/gen_menu_migration.mjs
   ```
5. **核对**：`menu_seed.sql`（v2） 出现新节点的 INSERT；如新 code 与其他文件冲突（应已用 prefix 避免），确认 `_dup` 后缀是否符合预期（不符合则改 JSON 的 id）。
6. **（可选）已运行环境同步**：执行 `menu_seed.sql`（v2）（全量覆盖，幂等 `ON CONFLICT DO NOTHING`），或用菜单管理页 UI 新增。

### 3.2 修改菜单节点

1. 改 JSON 文件对应节点的字段（caption/icon/workspace 等）。
2. 跑 `sync_menu_db.py` 同步 cmx_menu（§3.4）——侧栏刷新即生效。
3. **（可选 · 仅当用户要求 SQL 时）** 跑脚本重生成 menu_seed.sql。
4. **注意**：`ON CONFLICT DO NOTHING` 对已入库数据不更新——已运行环境需先删旧行或用 UI 改（走 `/api/menu/update`）。

### 3.3 删除菜单节点

1. 从 JSON 文件移除该节点（及其 children）。
2. 跑 `sync_menu_db.py` 同步 cmx_menu（§3.4）——侧栏刷新即生效。
3. **（可选 · 仅当用户要求 SQL 时）** 跑脚本重生成 menu_seed.sql（该节点 INSERT 消失）。
4. 已运行环境需手动 `DELETE FROM cmx_menu WHERE code = '<code>'` 或用 UI 删（走 `/api/menu/delete`）。

### 3.4 同步 cmx_menu（`sync_menu_db.py`，改完 JSON 的必做步骤）

> **必做**：门户侧栏运行时从 `cmx_menu` 回源（`GET /api/menu/tree`），仅改 menu-pages JSON **不会**刷新侧栏——改完必须用本脚本同步，立即生效。
>
> ⚠️ **本脚本只同步 `cmx_menu`，不同步 DAM 三表。** 新增**模块**的菜单：若 `cmx_module` 还没有该模块行，先按 §四 维护并执行模块创建 SQL，再跑本脚本——只跑脚本侧栏不会出现新模块。

```bash
# 在工作区根（或任意位置；参数 = 相对 cmx-container 的路径或绝对路径）：
python3 .agents/skills/menu-generator/scripts/sync_menu_db.py assets/model/data/menu-pages/<domain>/<app>/<module>/<file>.json
# 例：
python3 .agents/skills/menu-generator/scripts/sync_menu_db.py assets/model/data/menu-pages/basic/dataplatform/mdm/mdm-menu.json
```

**数据库不硬编码**，脚本自动解析：
1. **只读 `backend/cmx-portalservice/.env`** 取 `CONFIG_FILE`（如 `./portal-server-dev.toml`，相对 `backend/cmx-portalservice/` 解析）；
2. 解析该 toml 的 `[[databases]]`，取 `default = true` 的 `db_url`（默认/平台库）；`source_type = "biz"` 的是**业务库**，菜单不写业务库；
3. 解析 postgres URL（user/password/host/port/dbname）→ 经 `psql` 执行先删后插同步。

**行为**：按菜单文件路径前 3 段定 domain/application/module；展平树，按模块**先删后插**（与 menu_seed.sql 幂等策略一致，保证 id/parent_id/树形字段一次一致）：`DELETE FROM cmx_menu WHERE domain_code=… AND application_code=… AND module_code=…` 后逐节点 INSERT（code=id、definition=节点 JSON、树形字段 leaf/depth/parent_code、**sort_order=同级序号从 1 递增**，口径同 menu_seed.sql 生成器），id 用雪花算法，事务包裹（BEGIN/COMMIT），功能幂等。**注意**：`cmx_menu.id` 每次同步会漂移（新雪花 id）——权限按 code/fun_code 关联不受影响；若有外部数据直接引用 `cmx_menu.id` 会失效。

> 新环境初始化仍走 `menu_seed.sql`（v2）；本脚本服务"改完 JSON 后让运行环境侧栏立即生效"。

---

## 四、新建模块（少见，需配套）

新增一个模块的菜单需要三处配套（缺一不可，否则 DAM 派生/DB 回源断链）：

1. **菜单文件**：`backend/cmx-container/assets/model/data/menu-pages/<domain>/<app>/<newmodule>/<file>.json`
2. **模块 manifest**：`backend/cmx-container/assets/portal/data/modules/<domain>/<app>/<newmodule>/module.json`，`resources.menus[].menuRef` 指向菜单文件（如 `fi.cmxfico.newmodule.explorer-menu`，前 3 段必须 = domain/app/module）
3. **DAM 主数据（模块创建 SQL，必须维护并执行）**：`cmx_domain` / `cmx_application` / `cmx_module` 三表注册（domain/app 已存在则只插 module 行）。**manifest 不会自动入库，`sync_menu_db.py` 也只管 `cmx_menu`——这一步不做，模块和它名下的菜单都不会出现在侧栏。**

   **SQL 落地两处**（与 onto / 智能体平台先例一致）：
   - **迁移文件**（存量环境升级，引擎启动自动执行）：`docs/sql/v2/platform/migrations/<yyyyMMdd>_NNN_<标题>.up.sql` 末尾加一节 `INSERT INTO cmx_module ... ON CONFLICT (id) DO UPDATE`（配置数据，重放以仓库为准），配套 `.down.sql` 补对应 `DELETE`。先例：智能体平台模块注册随 `20260909_002_智能体自动更新建表.up.sql` 第 4 节入库。
   - **`init_dml.sql` §1 补行**（新环境手工重建）：模块段 VALUES 追加同一行，条数注释同步 +1。先例：`init_dml.sql` cmx_module 段（onto / agent 补录）。
   - **id 约定**：目标库已有该模块行（如手工预置）则**沿用其既有雪花 id**，`ON CONFLICT (id)` 才能命中刷新、不插双行（先例：onto `7499424336261840896` / agent `71788973651079482`）；全新模块用确定性 id `<domain>_<app>_<module>`（先例：mdm `basic_dataplatform_mdm`）。
   - **执行顺序**：先执行模块 SQL（存量环境跑迁移或手工执行），再跑 §3.4 同步菜单。**注意**：迁移一经引擎执行即记入 `cmx_schema_migrations` 台账、**不会重跑**——迁移入库后再补进迁移文件的内容，需在已执行过的环境手工补执行。

> 常规"跑脚本生成 menu_seed.sql"仅当用户主动要求时执行，默认不需要——它只覆盖 `cmx_menu`，**不覆盖 DAM 三表**；模块创建 SQL 必须按上面手工维护。

> 新建模块前先和用户确认是否真要新模块，多数情况是在现有模块下加菜单节点（§3.1）。

---

## 五、生成脚本说明（`.agents/skills/menu-generator/scripts/gen_menu_migration.mjs`）

**位置**：本技能 `scripts/` 目录下。脚本从自身位置向前查找 `cmx-container`（含 `assets/model/data/menu-pages`，兼容旧 `data/menu-pages`），与执行时的工作目录无关，可在仓库任意位置运行。

**触发时机**：**默认不跑**。仅当用户主动要求"生成 SQL / 更新 SQL / 同步数据库 / 初始化菜单种子"时才执行。常规菜单增删改 = 改 JSON + `sync_menu_db.py` 同步 cmx_menu 即生效（§3.4）。

**职责**：只管 SQL 生成。自动扫描 `backend/cmx-container/assets/model/data/menu-pages/**/*.json`，展平树、计算树形字段、处理冲突、输出 SQL。**不读写 JSON 菜单内容**（那是你/用户的职责）。

**扫描规则**：路径 `<domain>/<app>/<module>/<file>.json` 的前 3 段 = cmx_menu 的 domain_code/application_code/module_code。

**树形字段**（与 `cmx-biz/src/menu/service.rs::compute_tree_fields` 一致）：
- **id**：雪花算法生成（19 位数字，全局唯一），**不拼接路径**（避免多层嵌套时 id_path 过长）
- 根：`depth=1, code_path=/code, id_path=/<雪花id>`
- 子：`depth=父+1, code_path={父code_path}/code, id_path={父id_path}/<子雪花id>`
- `parent_id`：指向父节点的雪花 id
- `code_path`：仍用业务 code（人类可读，如 `/gl/portal-console`）
- `leaf`：无 children=1，否则=0

**冲突处理**：按路径排序扫描，后扫文件中与已存 code 冲突的加 `_dup` 后缀，子节点 parent 跟随。**新写菜单应在源头避免冲突**——按 §2.1 给所有 id 加文件专属 prefix（如 `<module>-<业务名>`），脚本的 `_dup` 兜底只作最后保险。

**幂等机制（先 DELETE 后 INSERT）**：生成的 SQL 文件结构为：
1. **先按 domain/application/module 删除旧数据**（动态生成，按扫描到的域/应用/模块去重）：
   ```sql
   DELETE FROM cmx_menu WHERE domain_code='fi' AND application_code='cmxfico' AND module_code='gl';
   DELETE FROM cmx_menu WHERE domain_code='fi' AND application_code='cmxfico' AND module_code='report';
   ```
2. **再 INSERT 最新数据**（保留 `ON CONFLICT (code) WHERE archived=0 DO NOTHING` 作兜底，DELETE 已清空通常不会触发）

这样**重跑 = 完全重置为 menu-pages 文件最新状态**，不会残留旧数据（如 menu-pages 改了 workspace 但旧库里还是老的，重跑 menu_seed.sql 会清掉旧的换新的）。新环境初始化与已运行环境重置用同一份 SQL，无需手动 DELETE。

**输出**：
- `docs/sql/v2/platform/menu_seed.sql`（全量最新，覆盖）—— **唯一产物，新环境初始化/重置用这个**
- 历史首迁 `20260716_001_menu_pages_to_cmx_menu` 已并入 `docs/sql/v2/platform/migrations/20260819_001_baseline.up.sql` 基线，脚本不再生成 up/down 迁移文件

---

## 六、检查清单（交付前自检）

**默认检查（每次增删改都要）**：
- [ ] 改了 `backend/cmx-container/assets/model/data/menu-pages/` 下的 JSON 文件？（不是直接改 SQL）
- [ ] 跑了 `sync_menu_db.py` 同步 cmx_menu？（不同步侧栏不生效）
- [ ] 新增/修改的节点 `id` 都带了文件专属 prefix（推荐 `<module>-<业务名>`，见 §2.1）？
- [ ] 新建模块时三处配套齐全？（菜单文件 / manifest / DAM 表）
- [ ] **新建模块的模块创建 SQL 已维护（迁移文件 + `init_dml.sql` 补录）并在目标库执行？**（§四；只跑 sync_menu_db.py 侧栏不显示）
- [ ] manifest 的 menuRef 前 3 段与菜单文件路径的 domain/app/module 对齐？

**SQL 路径检查（仅当用户主动要求生成 SQL 时才自检）**：
- [ ] 跑了 `node .agents/skills/menu-generator/scripts/gen_menu_migration.mjs`？
- [ ] `menu_seed.sql`（v2） 与 JSON 文件一致？（新增节点有 INSERT，删除节点 INSERT 消失）
- [ ] 跨文件 code 冲突的 `_dup` 后缀计数为 0？（>0 说明没按 §2.1 加 prefix，应回去改 JSON）

---

## 七、常见错误

| 错误 | 原因 | 修复 |
|---|---|---|
| 直接改 menu_seed.sql | SQL 是生成产物，手改会被下次重生成覆盖 | 改 JSON 文件；SQL 需要时跑脚本重生成 |
| 擅自跑脚本生成 SQL（用户未要求） | 技能默认不重生成 SQL，避免无意义的文件改动 | 默认只改 JSON；等用户明确要 SQL 才跑脚本 |
| 菜单文件改了但侧栏没变 | 侧栏从 cmx_menu 回源，改 JSON 不同步不生效 | 跑 `sync_menu_db.py`（§3.4）同步后刷新浏览器 |
| 新模块菜单同步了但侧栏不显示 | 只跑了 `sync_menu_db.py`，`cmx_module` 没有模块行（DAM 未注册）——侧栏域树以 DAM 三表为主干，菜单挂在模块下 | 按 §四 维护并执行模块创建 SQL（迁移 + init_dml 补录），再刷新侧栏 |
| 新模块菜单侧栏不显示 | manifest menuRef 与文件路径不对齐 | menuRef 前 3 段必须 = domain/app/module |
| 跨文件 id 重复（生成 `_dup` 后缀） | code 全局唯一，文件内裸 id 跨文件必撞 | 按 §2.1 给所有 id 加文件专属 prefix（如 `<module>-<业务名>`），重跑脚本 |
| workspace 布局丢失 | 改 JSON 时漏了 workspace 字段 | workspace 是节点字段，整体保留 |
