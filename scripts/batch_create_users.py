#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量创建员工账号（初始密码 pansoft，首登须改密）。

配套方案：documents/plans/20260909_cmx-iam_批量账号创建与默认密码强制改密方案.md

两种建号方式（二选一）：
  1. 纯数字工号：--start/--end（如 0001-9999，4 位补零）
  2. 前缀工号：--group 前缀:位数:数量（可重复），如 --group BJ:5:1000 --group LF:4:500
     工号从 1 起补零到指定位数；数量超过位数容量（如 3 位最多 999）时从 0 起凑满
     （如 HF:3:1000 → HF000–HF999）

行为：
  1. 直写 platform 库 cmx_user（不走 /api/iam/users/create，初始密码不满足策略属预期）；
  2. must_change_password 置 1（登录响应透出 must_change_password=true，改密成功后后端清 0）；
  3. 幂等：按 username（archived=0）去重，重跑只补缺号，不动存量；
  4. 可选 --role-code 给号段内已有用户挂角色（cmx_user_role 同样幂等，按角色编码动态关联）。

模式：
  默认           解析平台库连接并执行
  --sql-out 文件 只生成 INSERT SQL 文件（不连库；含幂等补列 ALTER，角色按 code 动态 JOIN，
                 任何环境可执行：psql -f <文件>）
  --dry-run      只打印概要与样例 SQL，不落库

数据库解析（不硬编码，同 sync_menu_db.py 口径）：
  backend/cmx-portalservice/.env → CONFIG_FILE → toml [[databases]] 取 default=true 的 db_url；
  可用 --db-url 或环境变量 CMX_USER_DB_URL 覆盖。

密码哈希：
  默认密码 pansoft 内嵌已验证 Argon2id PHC 串（m=65536,t=3,p=4，与生产 Argon2Config
  默认一致；Argon2 校验按 PHC 内嵌参数走，全部账号共用一条哈希无额外泄露）。
  换密码时按优先级取哈希：--password-hash > python argon2 库(argon2-cffi) > argon2 CLI。

示例：
  python3 scripts/batch_create_users.py --dry-run                    # 试跑，只打印概要
  python3 scripts/batch_create_users.py --add-column --role-code user  # 全量 0001-9999
  python3 scripts/batch_create_users.py --group BJ:5:1000 --group LF:4:500 --sql-out out.sql
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

CHUNK = 1000  # 单条 INSERT 的 VALUES 行数上限（控制语句体积、便于阅读）


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
    # 密码等成分支持 URL 百分号编码（如 @ → %40）
    from urllib.parse import unquote

    m = re.match(r"postgres(?:ql)?://([^:]+):([^@]+)@([^:/]+):(\d+)/(.+)$", url)
    if not m:
        raise SystemExit(f"无法解析 db_url: {url}")
    return {"user": unquote(m.group(1)), "password": unquote(m.group(2)), "host": unquote(m.group(3)),
            "port": m.group(4), "dbname": unquote(m.group(5))}


def run_psql(db, sql, capture=True):
    # SQL 走 stdin（大批量 VALUES 超 Linux 单参数 128KiB 上限，不能放 -c）
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


def parse_groups(group_args):
    """解析 --group 前缀:位数:数量，返回 [(prefix, width, count)]，校验合法性与重复。"""
    groups, seen = [], set()
    for g in group_args or []:
        parts = g.split(":")
        if len(parts) != 3:
            raise SystemExit(f"--group 格式应为 前缀:位数:数量，实际: {g}")
        prefix, width, count = parts[0].strip(), parts[1].strip(), parts[2].strip()
        if not (prefix.isascii() and prefix.isalpha() and prefix.isupper()):
            raise SystemExit(f"--group 前缀须为大写字母，实际: {prefix!r}")
        if not width.isdigit() or not (1 <= int(width) <= 8):
            raise SystemExit(f"--group 位数须为 1-8，实际: {width}")
        if not count.isdigit() or int(count) < 1:
            raise SystemExit(f"--group 数量须为正整数，实际: {count}")
        width, count = int(width), int(count)
        if count > 10 ** width:
            raise SystemExit(f"--group {prefix}: 数量 {count} 超过 {width} 位数字容量（含 0 起步最多 {10 ** width} 个）")
        if prefix in seen:
            raise SystemExit(f"--group 前缀重复: {prefix}")
        seen.add(prefix)
        groups.append((prefix, width, count))
    return groups


def group_usernames(prefix, width, count):
    # 工号从 1 起补零到位数；数量超过 width 位容量（10^width - 1，如 3 位最多 999）时
    # 从 0 起凑满（如 3 位 ×1000 → 000–999）
    start = 1 if count <= 10 ** width - 1 else 0
    return [f"{prefix}{str(n).zfill(width)}" for n in range(start, start + count)]


def build_batches(args):
    """返回 [(批次标签, [工号])]。--group 批次与 --start/--end 纯数字二选一。"""
    groups = parse_groups(args.group)
    if groups and (args.start != 1 or args.end != 9999):
        raise SystemExit("--group 与 --start/--end 二选一，不要混用")
    if groups:
        return [(p, group_usernames(p, w, c)) for p, w, c in groups]
    if not (0 < args.start <= args.end):
        raise SystemExit("号段非法：需 0 < start <= end")
    return [(None, [str(n).zfill(4) for n in range(args.start, args.end + 1)])]


def chunked(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def build_user_inserts(batches, pw_hash, nickname_prefix):
    """生成建号 INSERT 语句列表（每 CHUNK 行一条，带批次注释）。"""
    stmts = []
    seq = 0
    for label, usernames in batches:
        for part_idx, part in enumerate(chunked(usernames, CHUNK)):
            ids = gen_snowflakes(len(part), BASE_MS + seq * 1_000_000)
            seq += 1
            values = ",\n  ".join(
                f"('{esc(i)}', '{esc(u)}', '{esc(nickname_prefix + u)}')"
                for i, u in zip(ids, part))
            title = f"批次 {label}" if label else "纯数字号段"
            seg = f"（第 {part_idx + 1} 段）" if len(list(chunked(usernames, CHUNK))) > 1 else ""
            stmts.append(
                f"-- 建号：{title} {part[0]}–{part[-1]} {seg}\n"
                "INSERT INTO cmx_user (id, username, password_hash, nickname, status, description, "
                "must_change_password, archived, create_time, update_time, create_by, create_name)\n"
                f"SELECT v.id, v.username, '{esc(pw_hash)}', v.nickname, 1, '批量创建，初始密码须修改', 1, 0, "
                "now(), now(), 'batch-script', '批量建号脚本'\n"
                f"FROM (VALUES\n  {values}\n) AS v(id, username, nickname)\n"
                "WHERE NOT EXISTS (SELECT 1 FROM cmx_user u WHERE u.username = v.username AND u.archived = 0);")
    return stmts


def build_role_inserts(batches, role_code):
    """生成角色关联 INSERT（按角色编码动态 JOIN，跨环境可执行；每 CHUNK 行一条）。"""
    if not role_code:
        return []
    stmts = []
    seq = 10_000_000
    for label, usernames in batches:
        for part in chunked(usernames, CHUNK):
            rids = gen_snowflakes(len(part), BASE_MS + seq)
            seq += 1
            values = ",\n  ".join(f"('{esc(i)}', '{esc(u)}')" for i, u in zip(rids, part))
            stmts.append(
                f"-- 角色：{label or '纯数字号段'} → {role_code}\n"
                "INSERT INTO cmx_user_role (id, user_id, role_id, archived, create_time, update_time, create_by)\n"
                "SELECT s.id, u.id, r.id, 0, now(), now(), 'batch-script'\n"
                f"FROM (VALUES\n  {values}\n) AS s(id, username)\n"
                "JOIN cmx_user u ON u.username = s.username AND u.archived = 0\n"
                f"JOIN cmx_role r ON r.code = '{esc(role_code)}' AND r.archived = 0\n"
                "WHERE NOT EXISTS (SELECT 1 FROM cmx_user_role ur "
                "WHERE ur.user_id = u.id AND ur.role_id = r.id AND ur.archived = 0);")
    return stmts


def render_sql_file(user_stmts, role_stmts, role_code):
    header = (
        "-- =============================================\n"
        "-- 批量员工账号初始化（初始密码 pansoft，首登须改密）\n"
        f"-- 生成：{time.strftime('%Y-%m-%d %H:%M:%S')} by scripts/batch_create_users.py\n"
        "-- 方案：工作区 documents/plans/20260909_cmx-iam_批量账号创建与默认密码强制改密方案.md\n"
        "-- 幂等：可重复执行（按 username / user_id+role_id 去重，已有账号不动）\n"
        "-- 执行：psql -h <host> -U <user> -d <平台库> -f 本文件\n"
        "-- =============================================\n\n"
        "-- 0. 改密标志列（幂等，已存在则跳过）\n"
        f"{ADD_COLUMN_SQL}\n\n"
        "BEGIN;\n\n"
    )
    body = "\n\n".join(user_stmts + role_stmts)
    tail = "\n\nCOMMIT;\n"
    return header + body + tail


BASE_MS = int(time.time() * 1000)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--group", action="append", default=None, metavar="前缀:位数:数量",
                    help="按前缀批次建号，可重复，如 BJ:5:1000、LF:4:500；与 --start/--end 二选一")
    ap.add_argument("--start", type=int, default=1, help="纯数字起始工号（含，默认 1）")
    ap.add_argument("--end", type=int, default=9999, help="纯数字结束工号（含，默认 9999）")
    ap.add_argument("--password", default=DEFAULT_PASSWORD, help=f"初始密码（默认 {DEFAULT_PASSWORD}）")
    ap.add_argument("--password-hash", default=None, help="直接指定 Argon2id PHC 串（优先于 --password）")
    ap.add_argument("--nickname-prefix", default="", help="昵称前缀，昵称=前缀+工号（默认昵称=工号）")
    ap.add_argument("--role-code", default=None, help="号段内用户统一挂到该角色编码（如 user）")
    ap.add_argument("--add-column", action="store_true", help="must_change_password 列缺失时自动执行幂等 ALTER")
    ap.add_argument("--db-url", default=None, help="显式指定平台库连接串（默认从 portalservice 配置解析）")
    ap.add_argument("--sql-out", default=None, metavar="PATH",
                    help="只生成 INSERT SQL 文件（不连库执行；幂等、跨环境可执行）")
    ap.add_argument("--dry-run", action="store_true", help="只打印概要与样例 SQL，不落库")
    args = ap.parse_args()

    batches = build_batches(args)
    total = sum(len(us) for _, us in batches)
    pw_hash = resolve_password_hash(args)

    print(f"初始密码   : {args.password}")
    print(f"密码哈希   : {pw_hash[:40]}...（Argon2id PHC）")
    if args.role_code:
        print(f"挂靠角色   : {args.role_code}")
    for label, usernames in batches:
        print(f"批次       : {label or '纯数字'} {usernames[0]} – {usernames[-1]}（{len(usernames)} 个）")
    print(f"合计       : {total} 个账号")

    user_stmts = build_user_inserts(batches, pw_hash, args.nickname_prefix)
    role_stmts = build_role_inserts(batches, args.role_code)

    if args.sql_out:
        sql = render_sql_file(user_stmts, role_stmts, args.role_code)
        with open(args.sql_out, "w", encoding="utf-8") as f:
            f.write(sql)
        print(f"已生成     : {args.sql_out}（{len(user_stmts) + len(role_stmts)} 条 INSERT，幂等可重复执行）")
        print("该模式不连库；目标环境执行：psql -h <host> -U <user> -d <平台库> -f " + args.sql_out)
        return

    db = parse_url(args.db_url or resolve_db_url())
    print(f"目标库     : {db['host']}:{db['port']}/{db['dbname']}")

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

    if args.dry_run:
        parts = user_stmts[0].split("\n  ")
        print("\n[dry-run] 建号 SQL（首条语句前 2 行样例）：")
        print("\n  ".join(parts[:3]) + "\n  ...")
        if role_stmts:
            rparts = role_stmts[0].split("\n  ")
            print("\n[dry-run] 角色分配 SQL（首条语句前 2 行样例）：")
            print("\n  ".join(rparts[:3]) + "\n  ...")
        print("\n试跑结束，未落库。去掉 --dry-run 正式执行。")
        return

    sqls = ["BEGIN;"] + user_stmts + role_stmts + ["COMMIT;"]
    out = run_psql(db, "\n".join(sqls))
    inserted = sum(int(m) for m in re.findall(r"INSERT 0 (\d+)", out))
    print(f"完成：本机新增 {inserted} 条（cmx_user + cmx_user_role），已有账号未改动。")


if __name__ == "__main__":
    main()
