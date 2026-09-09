#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量创建员工账号（工号 0001-9999，默认密码 pansoft，首登须改密）。

配套方案：documents/plans/20260909_cmx-iam_批量账号创建与默认密码强制改密方案.md

行为：
  1. 直写 platform 库 cmx_user（不走 /api/iam/users/create，初始密码不满足策略属预期）；
  2. must_change_password 置 1（登录响应透出 must_change_password=true，改密成功后后端清 0）；
  3. 幂等：按 username（archived=0）去重，重跑只补缺号，不动存量；
  4. 可选 --role-code 给号段内已有用户挂角色（cmx_user_role 同样幂等）。

数据库解析（不硬编码，同 sync_menu_db.py 口径）：
  backend/cmx-portalservice/.env → CONFIG_FILE → toml [[databases]] 取 default=true 的 db_url；
  可用 --db-url 或环境变量 CMX_USER_DB_URL 覆盖。

密码哈希：
  默认密码 pansoft 内嵌已验证 Argon2id PHC 串（m=65536,t=3,p=4，与生产 Argon2Config
  默认一致；Argon2 校验按 PHC 内嵌参数走，全部账号共用一条哈希无额外泄露）。
  换密码时按优先级取哈希：--password-hash > python argon2 库(argon2-cffi) > argon2 CLI。

用法：
  python3 scripts/batch_create_users.py --dry-run                 # 试跑，只打印概要
  python3 scripts/batch_create_users.py --add-column --role-code user   # 全量建号+补列+挂角色
  python3 scripts/batch_create_users.py --start 1 --end 500       # 指定号段
"""
import argparse
import os
import re
import subprocess
import sys
import time

DEFAULT_PASSWORD = "pansoft"
# pansoft 的 Argon2id PHC 串；再生成方式见方案文档 §七（argon2-cffi 或 argon2 CLI）
EMBEDDED_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$mLGKBCddZDLMG1a32TMWCQ$"
    "rZi1UMPvAmP7il9jZ5tlbMDiANRBzGsErRVQc7/qREQ"
)

ADD_COLUMN_SQL = (
    "ALTER TABLE cmx_user ADD COLUMN IF NOT EXISTS must_change_password INT4 NOT NULL DEFAULT 0;\n"
    "COMMENT ON COLUMN cmx_user.must_change_password IS "
    "'初始密码未修改标志：0-正常，1-须修改（登录/刷新/me 响应透出 must_change_password）';"
)


def resolve_db_url():
    # 显式环境变量优先；否则从 portalservice 配置解析（CONFIG_FILE 相对其目录解析）
    if os.environ.get("CMX_USER_DB_URL"):
        return os.environ["CMX_USER_DB_URL"]
    svc_dir = next(
        (
            cand
            for cand in (
                os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", "cmx-portalservice")),
            )
            if os.path.isfile(os.path.join(cand, ".env"))
        ),
        None,
    )
    if svc_dir is None:
        raise SystemExit("未找到 backend/cmx-portalservice/.env（可用 --db-url 显式指定连接串）")
    env = {}
    with open(os.path.join(svc_dir, ".env"), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    cfg = env.get("CONFIG_FILE", "./portal-server-dev.toml")
    toml_path = os.path.normpath(os.path.join(svc_dir, cfg))
    if not os.path.isfile(toml_path):
        raise SystemExit(f"CONFIG_FILE 指向的 toml 不存在: {toml_path}")
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


def run_psql(db, sql, capture=True):
    # SQL 走 stdin（9999 行 VALUES 超 Linux 单参数 128KiB 上限，不能放 -c）
    env = dict(os.environ, PGPASSWORD=db["password"])
    # -A -t：元组裸输出，SELECT 结果不带表头与 "(N 行)" 尾注，便于解析；
    # INSERT 0 N 命令标签不受影响，用于计数
    r = subprocess.run(
        ["psql", "-h", db["host"], "-p", db["port"], "-U", db["user"], "-d", db["dbname"],
         "-v", "ON_ERROR_STOP=1", "-A", "-t", "-f", "-"],
        input=sql, capture_output=capture, text=True, env=env)
    if r.returncode != 0:
        raise SystemExit(f"psql 失败: {(r.stderr or r.stdout).strip()[:800]}")
    return r.stdout or ""


def esc(s):
    return str(s).replace("'", "''")


def gen_snowflakes(n, base_ms):
    # 与存量用户同构的雪花数字串：41bit 毫秒 | 22bit(机器 0 + 12bit 序列)；
    # 单进程内毫秒递增 + 序列循环，保证互不碰撞
    return [str(((base_ms + i // 4096) << 22) | (i % 4096)) for i in range(n)]


def resolve_password_hash(args):
    if args.password_hash:
        return args.password_hash
    if args.password == DEFAULT_PASSWORD:
        return EMBEDDED_HASH
    try:
        from argon2 import PasswordHasher  # pip install argon2-cffi

        ph = PasswordHasher(memory_cost=65536, time_cost=3, parallelism=4)
        return ph.hash(args.password)
    except ImportError:
        pass
    try:
        salt = subprocess.run(["od", "-An", "-N16", "-tx1", "/dev/urandom"],
                              capture_output=True, text=True, check=True).stdout.replace(" ", "").replace("\n", "")
        r = subprocess.run(["argon2", salt, "-id", "-t", "3", "-m", "16", "-p", "4", "-e"],
                           input=args.password, capture_output=True, text=True, check=True)
        return r.stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        raise SystemExit(
            f"密码 {args.password!r} 非默认值且本机无 argon2-cffi / argon2 CLI，无法生成哈希；\n"
            "请 pip install argon2-cffi 后重试，或用 --password-hash 直接传入 PHC 串。")


def column_exists(db):
    out = run_psql(db, "SELECT count(*) FROM information_schema.columns "
                       "WHERE table_name='cmx_user' AND column_name='must_change_password';")
    return out.strip() != "0"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--start", type=int, default=1, help="起始工号（含，默认 1）")
    ap.add_argument("--end", type=int, default=9999, help="结束工号（含，默认 9999）")
    ap.add_argument("--password", default=DEFAULT_PASSWORD, help=f"初始密码（默认 {DEFAULT_PASSWORD}）")
    ap.add_argument("--password-hash", default=None, help="直接指定 Argon2id PHC 串（优先于 --password）")
    ap.add_argument("--nickname-prefix", default="", help="昵称前缀，昵称=前缀+工号（默认昵称=工号）")
    ap.add_argument("--role-code", default=None, help="号段内用户统一挂到该角色编码（如 user）")
    ap.add_argument("--add-column", action="store_true", help="must_change_password 列缺失时自动执行幂等 ALTER")
    ap.add_argument("--db-url", default=None, help="显式指定平台库连接串（默认从 portalservice 配置解析）")
    ap.add_argument("--dry-run", action="store_true", help="只打印概要与样例 SQL，不落库")
    args = ap.parse_args()

    if not (0 < args.start <= args.end):
        raise SystemExit("号段非法：需 0 < start <= end")

    users = [str(n).zfill(4) for n in range(args.start, args.end + 1)]
    pw_hash = resolve_password_hash(args)
    db = parse_url(args.db_url or resolve_db_url())

    print(f"目标库     : {db['host']}:{db['port']}/{db['dbname']}")
    print(f"号段       : {users[0]} - {users[-1]}（{len(users)} 个）")
    print(f"初始密码   : {args.password}")
    print(f"密码哈希   : {pw_hash[:40]}...（Argon2id PHC）")
    if args.role_code:
        print(f"挂靠角色   : {args.role_code}")

    if not column_exists(db):
        if args.dry_run:
            print(f"[dry-run] must_change_password 列缺失，"
                  f"{'正式执行将自动补列' if args.add_column else '正式执行需 --add-column 或先跑迁移'}")
        elif args.add_column:
            run_psql(db, ADD_COLUMN_SQL)
            print("已补列     : cmx_user.must_change_password（幂等 ALTER）")
        else:
            raise SystemExit("cmx_user.must_change_password 列不存在。\n"
                             "请先执行迁移 20260909_001_用户初始密码改密标识，或加 --add-column 代为执行：\n"
                             f"  {ADD_COLUMN_SQL}")
    else:
        print("改密标志列 : 已存在")

    base_ms = int(time.time() * 1000)
    ids = gen_snowflakes(len(users), base_ms)
    values = ",\n  ".join(f"('{esc(i)}', '{esc(u)}', '{esc(args.nickname_prefix + u)}')"
                          for i, u in zip(ids, users))
    insert_users = (
        "INSERT INTO cmx_user (id, username, password_hash, nickname, status, description, "
        "must_change_password, archived, create_time, update_time, create_by, create_name)\n"
        f"SELECT v.id, v.username, '{esc(pw_hash)}', v.nickname, 1, '批量创建，初始密码须修改', 1, 0, "
        "now(), now(), 'batch-script', '批量建号脚本'\n"
        f"FROM (VALUES\n  {values}\n) AS v(id, username, nickname)\n"
        "WHERE NOT EXISTS (SELECT 1 FROM cmx_user u WHERE u.username = v.username AND u.archived = 0);"
    )

    insert_roles = None
    if args.role_code:
        role_out = run_psql(db, f"SELECT id FROM cmx_role WHERE code = '{esc(args.role_code)}' AND archived = 0;")
        role_lines = [l.strip() for l in role_out.strip().splitlines() if l.strip()]
        if not role_lines:
            raise SystemExit(f"角色编码不存在或已归档: {args.role_code}")
        role_id = role_lines[-1]
        rids = gen_snowflakes(len(users), base_ms + 10_000)  # 错开 10s，与前批 id 绝不重叠
        rvalues = ",\n  ".join(f"('{esc(i)}', '{esc(u)}')" for i, u in zip(rids, users))
        insert_roles = (
            "INSERT INTO cmx_user_role (id, user_id, role_id, archived, create_time, update_time, create_by)\n"
            "SELECT s.id, u.id, " + f"'{esc(role_id)}'" + ", 0, now(), now(), 'batch-script'\n"
            f"FROM (VALUES\n  {rvalues}\n) AS s(id, username)\n"
            "JOIN cmx_user u ON u.username = s.username AND u.archived = 0\n"
            "WHERE NOT EXISTS (SELECT 1 FROM cmx_user_role ur "
            "WHERE ur.user_id = u.id AND ur.role_id = '" + esc(role_id) + "' AND ur.archived = 0);"
        )

    if args.dry_run:
        parts = insert_users.split("\n  ")
        print("\n[dry-run] 建号 SQL（首 2 行样例）：")
        print("\n  ".join(parts[:3]) + "\n  ...")
        if insert_roles:
            rparts = insert_roles.split("\n  ")
            print("\n[dry-run] 角色分配 SQL（首 2 行样例）：")
            print("\n  ".join(rparts[:3]) + "\n  ...")
        print("\n试跑结束，未落库。去掉 --dry-run 正式执行。")
        return

    sqls = ["BEGIN;", insert_users]
    if insert_roles:
        sqls.append(insert_roles)
    sqls.append("COMMIT;")
    out = run_psql(db, "\n".join(sqls))
    inserted = sum(int(m) for m in re.findall(r"INSERT 0 (\d+)", out))
    print(f"完成：本机新增 {inserted} 条（cmx_user + cmx_user_role），号段内已有账号未改动。")


if __name__ == "__main__":
    main()
