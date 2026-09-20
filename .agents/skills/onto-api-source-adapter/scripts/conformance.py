#!/usr/bin/env python3
"""CMX 本体 API 数据源协议 v1 合规自测（对任意实现了三端点的 baseUrl 跑断言）。

用法（默认参数对应 references/adapter-example.py / 平台演示适配器）：
    python3 conformance.py http://127.0.0.1:8600
换成你的资源与字段：
    python3 conformance.py https://erp.internal/api/erp/v1 \
        --type SalesOrder --pk-field order_no \
        --filter-field status --filter-value approved \
        --group-field status --sum-field amount \
        --nullable-field remark --token XXXX

覆盖协议红线：信封 / 错误码（40040·40044·40046·40047·40401）/ caps / schema 双形态 /
pk 非空 / hasMore / 分页与超页宽 / filter 组合节点 / total 三态 / 聚合三 kind / 前向兼容。
全绿（exit 0）再接平台；任何 FAIL 都要先修适配器。
"""
import argparse
import json
import sys
import urllib.request
import urllib.error

AP = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
AP.add_argument("base", help="适配器 baseUrl，如 http://127.0.0.1:8600")
AP.add_argument("--type", dest="rtype", default="PurchaseOrder", help="探测用资源名")
AP.add_argument("--pk-field", default="po_no", help="该资源的主键源字段")
AP.add_argument("--filter-field", default="status", help="eq 探测字段")
AP.add_argument("--filter-value", default="approved", help="eq 探测值（JSON 解析，失败按字符串）")
AP.add_argument("--group-field", default="status", help="groupCount/groupSum 分组字段")
AP.add_argument("--sum-field", default="amount", help="groupSum 求和字段")
AP.add_argument("--nullable-field", default="remark", help="isnull 探测字段（声明为可空）")
AP.add_argument("--token", default="", help="Bearer token（适配器启用认证时）")
ARGS = AP.parse_args()

BASE = ARGS.base.rstrip("/")
PASS, FAIL = [], []


def call(method, path, body=None):
    req = urllib.request.Request(BASE + path, method=method)
    if ARGS.token:
        req.add_header("Authorization", f"Bearer {ARGS.token}")
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, data=data, timeout=15) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:  # noqa: BLE001
            return e.code, {}


def check(name, ok, detail=""):
    (PASS if ok else FAIL).append(name)
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" —— {detail}" if detail and not ok else ""))


def jparse(v):
    try:
        return json.loads(v)
    except Exception:  # noqa: BLE001
        return v


def query(body):
    return call("POST", "/onto-source/query", body)


def leaf(prop, op, value=None):
    n = {"prop": prop, "op": op}
    if value is not None:
        n["value"] = value
    return n


# ── 1. schema 双形态 ──────────────────────────────────────────────
st, r = call("GET", "/onto-source/schema")
d = r.get("data") or {}
caps = d.get("caps") or {}
check("schema 无 type：HTTP 200 + code=0", st == 200 and r.get("code") == 0)
check("schema：caps.filterOps 为数组", isinstance(caps.get("filterOps"), list))
check("schema：caps.pageMax 为正整数", isinstance(caps.get("pageMax"), int) and caps["pageMax"] > 0)
check("schema：caps.cursor=false（平台 v1 仅 offset）", caps.get("cursor") is False)
res = d.get("resources")
check("schema：resources 非空数组且每项有 type",
      isinstance(res, list) and res and all(isinstance(x, dict) and x.get("type") for x in res))

st, r = call("GET", f"/onto-source/schema?type={ARGS.rtype}")
d = r.get("data") or {}
fields = ((d.get("resources") or [{}])[0]).get("fields") or []
fnames = {f.get("name") for f in fields}
check("schema?type：code=0 且 resources[0].fields 为数组", r.get("code") == 0 and isinstance(fields, list))
check("schema?type：字段均有 name+baseType（五种基型内）",
      bool(fields) and all(f.get("name") and f.get("baseType") in
                           ("string", "number", "boolean", "datetime", "array") for f in fields))
st, r = call("GET", "/onto-source/schema?type=__NoSuchResource__")
check("schema?type 未知资源 → 40401", r.get("code") == 40401)

# ── 2. query 基线 ────────────────────────────────────────────────
st, r = query({"version": 1, "type": ARGS.rtype, "page": {"offset": 0, "limit": 10}})
d = r.get("data") or {}
items = d.get("items") or []
ok_items = isinstance(items, list) and all(
    isinstance(x.get("pk"), (str, int)) and str(x["pk"]) != "" and isinstance(x.get("props"), dict)
    for x in items)
check("query 无 filter：code=0、items 结构合法（pk 非空、props 对象）", r.get("code") == 0 and ok_items)
check("query：len(items) ≤ limit 且 hasMore 为布尔", len(items) <= 10 and isinstance(d.get("hasMore"), bool))
check("query：pk 字段名在 schema 白名单内", ARGS.pk_field in fnames,
      f"pk-field「{ARGS.pk_field}」不在 fields；用 --pk-field 指定")

st, r = query({"version": 2, "type": ARGS.rtype})
check("query version=2 → 40040", r.get("code") == 40040)
st, r = query({"type": ARGS.rtype})
check("query 缺 version → 40040", r.get("code") == 40040)
st, r = query({"version": 1, "type": "__NoSuch__"})
check("query 未知 type → 40401", r.get("code") == 40401)
st, r = query({"version": 1, "type": ARGS.rtype, "futureField": 123})
check("query 未知字段前向兼容（code=0）", r.get("code") == 0)

# ── 3. 分页与超页宽 ───────────────────────────────────────────────
st, r = query({"version": 1, "type": ARGS.rtype,
               "page": {"offset": 0, "limit": int(caps.get("pageMax") or 100) + 1}})
check(f"limit 超 pageMax → 40046", r.get("code") == 40046)
st, r1 = query({"version": 1, "type": ARGS.rtype, "page": {"offset": 0, "limit": 1}})
st, r2 = query({"version": 1, "type": ARGS.rtype, "page": {"offset": 0, "limit": 1}})
first1 = ((r1.get("data") or {}).get("items") or [{}])[0].get("pk")
first2 = ((r2.get("data") or {}).get("items") or [{}])[0].get("pk")
check("分页顺序稳定（同请求两次首条一致）", first1 is not None and first1 == first2)

# ── 4. filter DSL ────────────────────────────────────────────────
st, r = query({"version": 1, "type": ARGS.rtype,
               "filter": leaf("__ghost__", "eq", 1)})
check("白名单外字段过滤 → 40044", r.get("code") == 40044)
st, r = query({"version": 1, "type": ARGS.rtype, "filter": leaf(ARGS.pk_field, "$regex", "x")})
check("未知算子 → 40044", r.get("code") == 40044)
st, r = query({"version": 1, "type": ARGS.rtype, "filter": leaf(ARGS.pk_field, "in", [])})
check("in 空数组合法（空结果）", r.get("code") == 0 and not (r.get("data") or {}).get("items"))
st, r = query({"version": 1, "type": ARGS.rtype, "filter": leaf(ARGS.pk_field, "isnull")})
check("isnull 节点（无 value）合法", r.get("code") == 0)
st, r = query({"version": 1, "type": ARGS.rtype, "filter":
               {"and": [{"or": [leaf(ARGS.pk_field, "ne", "__nope__")]},
                        {"not": leaf(ARGS.pk_field, "eq", "__nope__")}]}})
check("and/or/not 组合嵌套合法", r.get("code") == 0)

fv = jparse(ARGS.filter_value)
st, r = query({"version": 1, "type": ARGS.rtype,
               "filter": leaf(ARGS.filter_field, "eq", fv), "page": {"offset": 0, "limit": 50}})
rows = (r.get("data") or {}).get("items") or []
check(f"eq 探测（{ARGS.filter_field}={fv!r}）：结果全命中",
      r.get("code") == 0 and rows and all((x.get("props") or {}).get(ARGS.filter_field) == fv for x in rows),
      f"命中 {len(rows)} 行；--filter-field/--filter-value 换成你数据里存在的组合")

# ── 5. total 三态 ────────────────────────────────────────────────
tm = caps.get("totalMode") or "none"
total = (r.get("data") or {}).get("total")
check(f"total 与 totalMode 一致（声明 {tm}）",
      (tm == "exact" and isinstance(total, int)) or (tm in ("none", "estimated") and (total is None or isinstance(total, int))),
      f"实测 total={total!r}")

# ── 6. aggregate ────────────────────────────────────────────────
st, r = call("POST", "/onto-source/aggregate",
             {"version": 1, "type": ARGS.rtype, "aggregate": {"kind": "count"}})
check("aggregate count → data.count 整数", r.get("code") == 0 and isinstance((r.get("data") or {}).get("count"), int))
st, r = call("POST", "/onto-source/aggregate",
             {"version": 1, "type": ARGS.rtype, "aggregate": {"kind": "bogus"}})
check("未知聚合 → 40047", r.get("code") == 40047)
if "groupCount" in (caps.get("aggregates") or []):
    st, r = call("POST", "/onto-source/aggregate",
                 {"version": 1, "type": ARGS.rtype,
                  "aggregate": {"kind": "groupCount", "groupBy": ARGS.group_field}})
    gs = (r.get("data") or {}).get("groups")
    check("groupCount → groups[{key,count}]",
          r.get("code") == 0 and isinstance(gs, list) and all("key" in g and "count" in g for g in gs),
          "用 --group-field 指定你数据里的分组字段")
if "groupSum" in (caps.get("aggregates") or []):
    st, r = call("POST", "/onto-source/aggregate",
                 {"version": 1, "type": ARGS.rtype,
                  "aggregate": {"kind": "groupSum", "groupBy": ARGS.group_field, "prop": ARGS.sum_field}})
    gs = (r.get("data") or {}).get("groups")
    check("groupSum → groups[{key,sum}]",
          r.get("code") == 0 and isinstance(gs, list) and all("key" in g and "sum" in g for g in gs),
          "用 --sum-field 指定数值字段")

print(f"\n{len(PASS)} 通过 / {len(FAIL)} 失败" + ("" if not FAIL else f"；失败项：{FAIL}"))
sys.exit(1 if FAIL else 0)
