#!/usr/bin/env node
// gen_menu_migration.mjs -- 菜单文件(menu-pages JSON) -> cmx_menu INSERT SQL 生成器。
//
// 本脚本属于 menu-generator 技能（.agents/skills/menu-generator/scripts/），从技能目录向上
// 定位根仓库，再进入 cmx-container 扫描 assets/model/data/menu-pages（兼容旧 data/menu-pages）并输出 SQL。
//
// 背景：菜单以 JSON 文件存放在 cmx-container/assets/model/data/menu-pages/<domain>/<app>/<module>/<file>.json，
// 现迁移到数据库 cmx_menu 表（节点级映射：每节点一行，workspace/dialogspace 等富数据入
// definition JSONB）。本脚本自动扫描所有 menu-pages 文件，递归展平树、计算树形字段
// (depth/code_path/id_path/leaf/parent)、处理跨文件重复 code，输出可核对、可重跑的 INSERT。
//
// ⚠️ 默认行为：dry-run（只扫描 + 输出统计，不写任何文件）。
//    技能约定：常规菜单增删改 = 改 JSON + scripts/sync_menu_db.py 同步 cmx_menu 即生效，不需要重生成 SQL。
//    只有用户主动要求"生成 SQL / 更新 SQL / 同步数据库"时，才加 --write 参数写入文件。
//
// 用法（在仓库任意位置均可，脚本自动定位 cmx-container）：
//   node .agents/skills/menu-generator/scripts/gen_menu_migration.mjs             # dry-run：仅扫描 + 输出统计
//   node .agents/skills/menu-generator/scripts/gen_menu_migration.mjs --write     # 写入 SQL 文件
//
// 写入产物（仅 --write 模式，唯一产物）：
//   cmx-container/docs/sql/v2/platform/menu_seed.sql   （全量最新菜单，每次重生成覆盖）
//   （历史首迁 20260716_001_menu_pages_to_cmx_menu 已并入 migrations/20260819_001_baseline.up.sql，脚本不再生成）
//
// 扫描规则：遍历 cmx-container/assets/model/data/menu-pages/**/*.json（兼容旧 data/menu-pages 回退），
// 文件路径 <domain>/<app>/<module>/<file>.json
// 对应 cmx_menu 的 domain_code/application_code/module_code（模块本身由 DAM 派生，不落入 cmx_menu；
// 文件内 items 作为该模块的菜单根节点）。
//
// 重复 code 处理：扫描顺序按路径排序；后扫文件与已存 code 冲突的追加 `_dup` 后缀，
// 子节点 parent_code/parent_id 跟随父节点重命名同步，保证 code 全局唯一。
//
// 树形字段格式与 MenuService::compute_tree_fields 一致：
//   根：code_path=/code，id_path=/id，depth=1
//   子：code_path={父code_path}/code，id_path={父id_path}/id，depth=父+1

import { readFileSync, writeFileSync, readdirSync, statSync, existsSync } from 'node:fs'
import { resolve, dirname, join, relative } from 'node:path'
import { fileURLToPath } from 'node:url'

// ── 命令行参数：默认 dry-run，仅当显式传 --write 时才写入 SQL 文件 ──
const WRITE = process.argv.slice(2).includes('--write')

// ── 雪花算法 ID 生成器（复刻 cmx-utils/src/id/snowflake.rs，64 位需用 BigInt）──
// 结构：符号位(1) + 时间戳(41) + 节点ID(10) + 序列号(12)
const EPOCH = 0n // 与 Rust 端一致（用 UNIX 原点）
const NODE_ID = 1n // 脚本固定节点 1（单进程生成，无需分布式）
let _seq = 0n
let _lastTs = 0n
function snowflakeId () {
  const now = BigInt(Date.now())
  if (now === _lastTs) {
    _seq += 1n
    if (_seq >= 4096n) { // 同毫秒序列耗尽，等到下一毫秒
      while (BigInt(Date.now()) === _lastTs) { /* spin */ }
      _seq = 0n
      _lastTs = BigInt(Date.now())
    }
  } else {
    _seq = 0n
    _lastTs = now
  }
  const id = (now << 22n) | (NODE_ID << 12n) | _seq
  return id.toString()
}

const __dirname = dirname(fileURLToPath(import.meta.url))

// 从脚本位置向上查找根仓库（含 cmx-container 子目录），再定位 cmx-container 与菜单目录。
// 资产重构后菜单真源在 assets/model/data/menu-pages；兼容旧 data/menu-pages（与 sync_menu_db.py 一致）。
function findCmxContainer () {
  let cur = __dirname
  for (let i = 0; i < 10; i++) {
    const candidate = join(cur, 'cmx-container')
    if (existsSync(join(candidate, 'assets', 'model', 'data', 'menu-pages'))) return candidate
    if (existsSync(join(candidate, 'data', 'menu-pages'))) return candidate
    const parent = dirname(cur)
    if (parent === cur) break
    cur = parent
  }
  throw new Error(`未找到 cmx-container/assets/model/data/menu-pages（从 ${__dirname} 向上查找失败）`)
}

const CONTAINER = findCmxContainer()
const MENU_PAGES_DIR = existsSync(join(CONTAINER, 'assets', 'model', 'data', 'menu-pages'))
  ? resolve(CONTAINER, 'assets/model/data/menu-pages')
  : resolve(CONTAINER, 'data/menu-pages')

/**
 * 递归扫描 menu-pages 目录，收集所有 *.json 文件。
 * 返回 [{ file, domain, app, module }]，按路径排序（保证跨文件 code 冲突处理稳定）。
 */
function scanMenuPages () {
  const out = []
  const walk = (dir) => {
    let entries = []
    try { entries = readdirSync(dir) } catch { return }
    for (const name of entries) {
      const full = join(dir, name)
      const st = statSync(full)
      if (st.isDirectory()) walk(full)
      else if (name.endsWith('.json')) out.push(full)
    }
  }
  walk(MENU_PAGES_DIR)
  // 解析 <domain>/<app>/<module>/<file>.json
  const docs = []
  for (const full of out.sort()) {
    const rel = relative(MENU_PAGES_DIR, full).split(/[/\\]/)
    if (rel.length < 4) continue // 至少 domain/app/module/file 四段
    docs.push({
      file: relative(CONTAINER, full),
      domain: rel[0], app: rel[1], module: rel[2],
    })
  }
  return docs
}

/**
 * 递归展平一棵菜单树为节点数组。
 * @param {any[]} items 菜单节点数组
 * @param {string|null} parentCode 父节点（已重命名后的）code，顶层为 null
 * @param {number} depth 当前深度（根=1）
 * @param {string} codePath 父 code_path（根前为 ''）
 * @param {string} idPath 父 id_path（根前为 ''）
 * @param {string} domain / app / module
 * @param {Set<string>} usedCodes 已用 code 集合（跨文档去重）
 * @param {boolean} addSuffix 冲突时是否加后缀（扫描模式下始终 true）
 * @param {{count:number}} dupCount 冲突计数对象（统计 _dup 重命名数）
 * @returns {object[]} 扁平节点数组
 */
function flatten (items, parentCode, parentId, depth, codePath, idPath, domain, app, module, usedCodes, addSuffix, dupCount) {
  const out = []
  if (!Array.isArray(items)) return out
  items.forEach((node, i) => {
    let code = String(node.id ?? '')
    if (!code) return
    // code 中的 / 替换为 -，避免与 code_path 的层级分隔符 / 冲突（如 id="a/b" → code="a-b"）
    code = code.replace(/\//g, '-')
    // 跨文件重复 code 处理：冲突加 _dup 后缀（基于替换后的 code 判断）
    if (addSuffix && usedCodes.has(code)) { code = code + '_dup'; dupCount.count++ }
    usedCodes.add(code)

    // 主键 id 用雪花算法生成（不拼接路径，避免多层嵌套时 id_path 过长）
    const id = snowflakeId()
    const newCodePath = codePath + '/' + code
    const newIdPath = idPath + '/' + id

    const caption = node.caption
    // name 列：caption 为字符串直接用，否则回退内部 name 或 code
    const nameCol = typeof caption === 'string' ? caption : (node.name ?? code)

    // definition JSONB：保留 caption(含 i18n 对象)/workspace/dialogspace/expanded/type/name
    const definition = {}
    if (caption != null) definition.caption = caption
    if (node.workspace) definition.workspace = node.workspace
    if (node.dialogspace) definition.dialogspace = node.dialogspace
    if (node.expanded != null) definition.expanded = node.expanded
    if (node.type) definition.type = node.type
    if (node.name) definition.name = node.name

    const children = Array.isArray(node.children) ? node.children : []
    // visible: 0 隐藏 / 1 显示（节点 JSON 可带 visible 字段；口径同前端 menu-cache——仅 0 视为隐藏）
    const visible = Number(node.visible) === 0 ? 0 : 1
    out.push({
      id, code, name: String(nameCol), icon: node.icon ?? null, fun_code: node.permissionId ?? null,
      sort_order: i + 1, definition, domain_code: domain, application_code: app, module_code: module,
      parent_id: parentId,
      parent_code: parentCode, depth, leaf: children.length === 0 ? 1 : 0,
      code_path: newCodePath, id_path: newIdPath, visible,
    })
    out.push(...flatten(children, code, id, depth + 1, newCodePath, newIdPath, domain, app, module, usedCodes, addSuffix, dupCount))
  })
  return out
}

/** SQL 字面量转义 */
function sqlVal (v) {
  if (v == null) return 'NULL'
  if (typeof v === 'number') return String(v)
  return `'${String(v).replace(/'/g, "''")}'`
}

/** JSONB 字面量 */
function sqlJson (obj) {
  return `'${JSON.stringify(obj).replace(/'/g, "''")}'::jsonb`
}

// ── 主流程 ──
const DOCS = scanMenuPages()
const usedCodes = new Set()
const dupCount = { count: 0 }
const all = []
for (const d of DOCS) {
  const raw = readFileSync(resolve(CONTAINER, d.file), 'utf8')
  const doc = JSON.parse(raw)
  const items = Array.isArray(doc) ? doc : (doc.items ?? [])
  // 扫描顺序按路径排序；后扫文件与已存 code 冲突的加 _dup 后缀（func flatten 内按 usedCodes 判断）
  all.push(...flatten(items, null, null, 1, '', '', d.domain, d.app, d.module, usedCodes, true, dupCount))
}

// 唯一产物：menu_seed.sql（v2 全量最新）。历史首迁已并入 baseline 迁移，不再单独生成 up/down。
const INIT_PATH = resolve(CONTAINER, 'docs/sql/v2/platform/menu_seed.sql')

const COLS = 'id, code, name, icon, fun_code, sort_order, definition, domain_code, application_code, module_code, parent_id, parent_code, depth, leaf, code_path, id_path, visible, status, open_type, archived, create_time, update_time'
const lines = all.map(n => {
  const vals = [
    sqlVal(n.id), sqlVal(n.code), sqlVal(n.name), sqlVal(n.icon), sqlVal(n.fun_code),
    sqlVal(n.sort_order), sqlJson(n.definition), sqlVal(n.domain_code), sqlVal(n.application_code), sqlVal(n.module_code),
    sqlVal(n.parent_id), sqlVal(n.parent_code), sqlVal(n.depth), sqlVal(n.leaf), sqlVal(n.code_path), sqlVal(n.id_path),
    sqlVal(n.visible ?? 1), '1', '0', '0', 'now()', 'now()',
  ]
  return `INSERT INTO cmx_menu (${COLS}) VALUES (${vals.join(', ')}) ON CONFLICT (code) WHERE archived = 0 DO NOTHING;`
})

// 按扫描到的 (domain, application, module) 去重，生成 DELETE 语句先清旧数据再插入。
// 保证重跑幂等：每次先删该域/应用/模块下的旧菜单，再插入最新，避免旧数据残留。
const delTriples = [...new Set(
  all.map((n) => `${n.domain_code}|${n.application_code}|${n.module_code}`)
)]
const deleteLines = delTriples.map((t) => {
  const [d, a, m] = t.split('|')
  return `DELETE FROM cmx_menu WHERE domain_code = '${d}' AND application_code = '${a}' AND module_code = '${m}';`
})

const header = `-- 菜单 INSERT（由 .agents/skills/menu-generator/scripts/gen_menu_migration.mjs 自动扫描 cmx-container/assets/model/data/menu-pages 生成，可重跑）
-- 模块本身由 DAM 派生（不在 cmx_menu）；此处仅各模块下的菜单 items 作为该模块菜单根节点。
-- 节点级映射：workspace/dialogspace 等富数据入 definition JSONB；跨文件冲突 code 加 _dup 后缀。
-- 幂等保证：先按 domain/application/module 删除旧数据，再插入最新（重跑 = 重置为文件最新状态）。`

if (WRITE) {
  // 全量最新 menu_seed.sql（每次重生成覆盖，与 menu-pages 文件保持同步）
  writeFileSync(INIT_PATH, `${header}
-- 本文件是菜单的全量最新状态（类似 init_ddl.sql 理念）：每次增删改菜单后重跑脚本覆盖。
-- 新环境初始化或重置菜单数据时执行本文件即可（先 DELETE 该域/应用/模块旧数据再 INSERT）。

${deleteLines.join('\n')}

${lines.join('\n')}
`)
}

console.log(`定位 cmx-container: ${CONTAINER}`)
console.log(`扫描 ${DOCS.length} 个菜单文件 -> 生成 ${all.length} 条 INSERT`)
console.log(`  _dup 重命名: ${dupCount.count} 个（跨文件 code 冲突自动后缀）`)
if (WRITE) {
  console.log(`  [已写入] menu_seed 全量: ${relative(process.cwd(), INIT_PATH)}`)
} else {
  console.log(`  [dry-run] 未写入任何文件。如需生成 SQL，请加 --write 参数。`)
}
