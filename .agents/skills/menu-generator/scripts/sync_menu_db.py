#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""已运行环境菜单直写 cmx_menu（Python 版，menu-generator 技能配套）。

用途：launcher/门户侧栏实际从 cmx_menu 数据库回源（/api/menu/tree）时，
仅改 menu-pages JSON 不会刷新已运行环境的侧栏。本脚本把某个 menu-pages JSON
的节点 **upsert** 进 cmx_menu，让已运行环境立即生效。

数据库解析（不硬编码）：
  1. 只读 backend/cmx-portalservice/.env 取 CONFIG_FILE（如 ./portal-server-dev.toml）
  2. 解析该 toml 的 [[databases]]，取 default=true 的 db_url（默认/平台库）；
     source_type="biz" 的是业务库，菜单不写业务库
  3. 解析 postgres URL → host/port/user/password/dbname

用法：
  python3 scripts/sync_menu_db.py <menu-pages 相对 cmx-container 的路径或绝对路径.json>
  例：python3 scripts/sync_menu_db.py assets/model/data/menu-pages/basic/dataplatform/mdm/mdm-menu.json

仅开发/已运行环境同步用；新环境初始化仍走 menu_seed.sql（v2）。
"""
import json, os, re, sys, time, subprocess, random

def menu_pages_dir(root):
    # 资产重构后菜单目录在 assets/model/data/menu-pages，兼容旧 data/menu-pages
    for sub in (("assets", "model", "data", "menu-pages"), ("data", "menu-pages")):
        p = os.path.join(root, *sub)
        if os.path.isdir(p):
            return p
    return None

def find_container_root():
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(8):
        # 自身即容器根，或兄弟目录 cmx-container（.agents 与 cmx-container 同级时）；
        # 2026-09 结构重组后 cmx-container 在 backend/ 下，一并兼容
        for cand in (d, os.path.join(d, "cmx-container"),
                     os.path.join(d, "backend", "cmx-container")):
            if menu_pages_dir(cand):
                return cand
        d = os.path.dirname(d)
    raise SystemExit("未找到 cmx-container 根（含 data/menu-pages 或 assets/model/data/menu-pages）")

def resolve_db_url(root):
    # 库配置真源 = backend/cmx-portalservice/.env（cmx-container 的兄弟仓，CONFIG_FILE 相对其解析）；
    # backend/cmx-container/.env 只是蓝本，仅在 portalservice 不存在时回退。不回退 .env.local。
    svc_dir = next((cand for cand in (
        os.path.normpath(os.path.join(root, "..", "backend", "cmx-portalservice")),
        os.path.normpath(os.path.join(root, "..", "cmx-portalservice")),
        os.path.join(root, "backend", "cmx-portalservice"),
        os.path.join(root, "cmx-portalservice"),
        root,
    ) if os.path.isfile(os.path.join(cand, ".env"))), None)
    if svc_dir is None:
        raise SystemExit("未找到 backend/cmx-portalservice/.env")
    env = {}
    p = os.path.join(svc_dir, ".env")
    for line in open(p, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    cfg = env.get("CONFIG_FILE", "./portal-server-dev.toml")
    toml_path = os.path.normpath(os.path.join(svc_dir, cfg))
    if not os.path.isfile(toml_path):
        for fb in ("portal-server-dev.toml", "dev.toml"):
            if os.path.isfile(os.path.join(svc_dir, fb)):
                toml_path = os.path.join(svc_dir, fb)
                break
    import tomllib
    with open(toml_path, "rb") as f:
        doc = tomllib.load(f)
    dbs = doc.get("databases", [])
    if not dbs:
        raise SystemExit(f"{toml_path} 无 [[databases]]")
    default = next((d for d in dbs if d.get("default")), dbs[0])
    return default["db_url"]

def parse_url(url):
    m = re.match(r"postgres(?:ql)?://([^:]+):([^@]+)@([^:/]+):(\d+)/(.+)$", url)
    if not m:
        raise SystemExit(f"无法解析 db_url: {url}")
    return {"user": m.group(1), "password": m.group(2), "host": m.group(3),
            "port": m.group(4), "dbname": m.group(5)}

def snowflake():
    return (int(time.time() * 1000) << 22) | random.getrandbits(22)

def run_psql(db, sql):
    env = dict(os.environ, PGPASSWORD=db["password"])
    r = subprocess.run(
        ["psql", "-h", db["host"], "-p", db["port"], "-U", db["user"], "-d", db["dbname"],
         "-v", "ON_ERROR_STOP=1", "-c", sql],
        capture_output=True, text=True, env=env)
    if r.returncode != 0:
        raise SystemExit(f"psql 失败: {r.stderr.strip()[:500]}")
    return r.stdout

def esc(s):
    return str(s).replace("'", "''")

def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    root = find_container_root()
    arg = sys.argv[1]
    # 绝对路径直用；相对路径优先按当前目录解析（如从工作区根传 backend/cmx-container/assets/...），
    # 不存在再按 cmx-container 根拼接（如传 assets/model/data/menu-pages/...）
    if os.path.isabs(arg):
        path = arg
    else:
        path = arg if os.path.isfile(arg) else os.path.join(root, arg)
    rel = os.path.relpath(path, menu_pages_dir(root))
    parts = rel.replace("\\", "/").split("/")
    domain, app, module = parts[0], parts[1], parts[2]

    doc = json.load(open(path, encoding="utf-8"))
    items = doc["items"] if isinstance(doc, dict) and "items" in doc else doc

    # CMX_MENU_DB_URL 可显式指定目标库（如运行中服务的 CONFIG_FILE 被 env 覆盖、与 .env 文件不一致时）
    db = parse_url(os.environ.get("CMX_MENU_DB_URL") or resolve_db_url(root))
    nodes = []
    def walk(list_, parent, depth, id_path, code_path):
        for i, n in enumerate(list_):
            code = n["id"]
            nid = snowflake()
            n["_nid"] = nid
            n["_depth"] = depth
            n["_sort"] = i + 1  # 同级序，口径同 gen_menu_migration.mjs / menu_seed.sql
            n["_id_path"] = f"{id_path}/{nid}"
            n["_code_path"] = f"{code_path}/{code}"
            nodes.append((n, parent))
            walk(n.get("children", []) or [], n, depth + 1, n["_id_path"], n["_code_path"])
    walk(items, None, 1, "", "")

    # 先删后插（同 menu_seed.sql 幂等策略），保证 id/parent_id/树形字段一次一致
    sqls = ["BEGIN;"]
    sqls.append(f"DELETE FROM cmx_menu WHERE domain_code='{esc(domain)}' AND application_code='{esc(app)}' AND module_code='{esc(module)}';")
    for n, parent in nodes:
        code = n["id"]
        defn = {k: v for k, v in n.items() if k not in ("children",) and not k.startswith("_")}
        defn_json = json.dumps(defn, ensure_ascii=False)
        leaf = 0 if (n.get("children") or []) else 1
        name = n.get("caption") if isinstance(n.get("caption"), str) else n.get("name", code)
        # visible: 0 隐藏 / 1 显示（节点 JSON 可带 visible 字段；口径同前端 menu-cache——仅 0 视为隐藏）
        try:
            visible = 0 if int(n.get("visible", 1)) == 0 else 1
        except (TypeError, ValueError):
            visible = 1
        pid = parent["_nid"] if parent else None
        pcode = parent["id"] if parent else None
        sqls.append(f"""
INSERT INTO cmx_menu (id, code, name, icon, fun_code, domain_code, application_code, module_code,
  definition, status, leaf, depth, sort_order, parent_id, parent_code, id_path, code_path, visible, archived, create_time, update_time)
VALUES ({n['_nid']}, '{esc(code)}', '{esc(name)}', '{esc(n.get('icon',''))}',
  {("'" + esc(n['permissionId']) + "'") if n.get('permissionId') else 'NULL'},
  '{esc(domain)}', '{esc(app)}', '{esc(module)}', '{esc(defn_json)}'::jsonb,
  1, {leaf}, {n['_depth']}, {n['_sort']}, {pid if pid else 'NULL'}, {("'" + esc(pcode) + "'") if pcode else 'NULL'},
  '{esc(n['_id_path'])}', '{esc(n['_code_path'])}', {visible}, 0, now(), now());""")
    sqls.append("COMMIT;")
    out = run_psql(db, "\n".join(sqls))
    print(f"已同步 {len(nodes)} 个菜单节点 → {domain}/{app}/{module} @ {db['host']}:{db['port']}/{db['dbname']}")
    print(out.strip()[:200])

if __name__ == "__main__":
    main()
