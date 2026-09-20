#!/usr/bin/env python3
"""CMX 本体 API 数据源适配器模板（协议 v1；Python 标准库零依赖，python3 直接运行）。

对接文档：本目录 protocol-v1.md（规范真源）。本模板实现协议最小完整集：

  GET  /onto-source/schema            资源清单 + 能力矩阵（caps）；?type=X → 字段清单
  POST /onto-source/query             filter DSL 求值 + offset 分页 + 单据（头+行）嵌套 props
  POST /onto-source/aggregate         count / groupCount / groupSum

业务系统接入只需改三处（见 ★ 标注）：
  1) CAPS       —— 按你的真实能力声明（声明与实现必须一致，平台实测为准）
  2) RESOURCES  —— 资源名 → {name 显示名, fields 字段清单}
  3) fetch()    —— 把「内存列表 + eval_filter」换成你的底层查询（SQL / ES / 微服务调用），
                   filter 翻译规则见文件尾注释；本模板用内存求值演示协议语义。

运行与自测：
    python3 adapter-example.py                       # 监听 127.0.0.1:8600
    python3 ../scripts/conformance.py http://127.0.0.1:8600
认证（可选）：设环境变量 ONTO_ADAPTER_TOKEN 后，平台侧源 config 需配 auth.mode=bearer + tokenEnv。
"""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# ★ 1) 能力矩阵：平台据此预检（能力外的查询根本不会发过来）并收敛前端算子。
#    原则：声明什么就必须支持什么；不支持 contains / 大表不给总数，照抄本例即可。
CAPS = {
    "filterOps": ["eq", "ne", "gt", "ge", "lt", "le", "in", "isnull"],  # 演示不含 contains
    "pageMax": 100,            # 平台请求 limit 恒 ≤ 此值；超限必须回 40046
    "totalMode": "none",       # exact=回精确 total / estimated=约数 / none=不给总数
    "cursor": False,           # 平台 v1 仅支持 offset 分页，必须 false
    "defaultOrder": "pk",      # 你返回行的稳定排序说明（列表请按主键排序！）
    "aggregates": ["count", "groupCount", "groupSum"],
}

# ★ 2) 资源与字段清单。资源名必须匹配 ^[A-Za-z][A-Za-z0-9_.-]{0,127}$。
#      baseType 五选一：string/number/boolean/datetime/array；
#      array 字段带嵌套 fields = 单据明细行（explorer 详情展开为子表）。
RESOURCES = {
    "PurchaseOrder": {
        "name": "采购订单",
        "fields": [
            {"name": "po_no",     "baseType": "string",   "sourceType": "varchar(32)",   "comment": "单号"},
            {"name": "status",    "baseType": "string",   "sourceType": "varchar(16)",   "comment": "状态"},
            {"name": "amount",    "baseType": "number",   "sourceType": "decimal(18,2)", "comment": "金额"},
            {"name": "orderDate", "baseType": "datetime", "sourceType": "datetime",      "comment": "下单时间"},
            {"name": "remark",    "baseType": "string",   "sourceType": "varchar(200)",  "comment": "备注（可空）"},
            {"name": "lines",     "baseType": "array",    "sourceType": "jsonb",         "comment": "明细行",
             "fields": [
                 {"name": "lineNo",       "baseType": "number", "sourceType": "int"},
                 {"name": "materialCode", "baseType": "string", "sourceType": "varchar(16)"},
                 {"name": "materialName", "baseType": "string", "sourceType": "varchar(64)"},
                 {"name": "qty",          "baseType": "number", "sourceType": "decimal(18,3)"},
                 {"name": "price",        "baseType": "number", "sourceType": "decimal(18,2)"},
             ]},
        ],
    },
    "Supplier": {
        "name": "供应商",
        "fields": [
            {"name": "supplier_no", "baseType": "string",  "sourceType": "varchar(16)", "comment": "供应商编号"},
            {"name": "name",        "baseType": "string",  "sourceType": "varchar(64)", "comment": "名称"},
            {"name": "region",      "baseType": "string",  "sourceType": "varchar(16)", "comment": "区域"},
            {"name": "active",      "baseType": "boolean", "sourceType": "bool",        "comment": "启用"},
        ],
    },
}

# ★ 3) 数据面：把 fetch() 换成你的底层查询。模板数据含一张单据（头+行）与一张主数据。
_ROWS = {
    "PurchaseOrder": [
        {"po_no": "PO-2026-0001", "status": "approved", "amount": 12500.50,
         "orderDate": "2026-08-01T10:00:00+08:00", "remark": "加急",
         "lines": [{"lineNo": 1, "materialCode": "M-001", "materialName": "螺纹钢 HRB400", "qty": 100, "price": 3800.0},
                   {"lineNo": 2, "materialCode": "M-014", "materialName": "高线 HPB300", "qty": 250, "price": 3650.0}]},
        {"po_no": "PO-2026-0002", "status": "draft", "amount": 800.00,
         "orderDate": "2026-08-02T10:00:00+08:00", "remark": None,
         "lines": [{"lineNo": 1, "materialCode": "M-020", "materialName": "中厚板 Q235", "qty": 20, "price": 4000.0}]},
        {"po_no": "PO-2026-0003", "status": "approved", "amount": 30500.00,
         "orderDate": "2026-08-03T10:00:00+08:00", "remark": None,
         "lines": [{"lineNo": 1, "materialCode": "M-001", "materialName": "螺纹钢 HRB400", "qty": 500, "price": 3800.0}]},
    ],
    "Supplier": [
        {"supplier_no": "SUP-01", "name": "华中钢铁", "region": "central", "active": True},
        {"supplier_no": "SUP-02", "name": "宝钢股份", "region": "east", "active": True},
        {"supplier_no": "SUP-03", "name": "鞍钢集团", "region": "northeast", "active": False},
    ],
}
_PK = {"PurchaseOrder": "po_no", "Supplier": "supplier_no"}  # 主键源字段（恒单列，平台桥接依赖）


def fetch(resource, filter_node, offset, limit):
    """执行一次查询：返回 (window_rows, total_or_None, has_more)。

    ★ 真实系统里把本函数替换为底层查询；filter → WHERE 的翻译规则：
        {"prop":F,"op":"eq","value":V}              → WHERE F = :v        （值一律参数绑定，防注入）
        {"prop":F,"op":"in","value":[...]}          → WHERE F IN (:v1,:v2,…)
        {"prop":F,"op":"isnull"}                    → WHERE F IS NULL
        {"and":[…]} / {"or":[…]} / {"not":{…}}      → (…) AND (…) / (…) OR (…) / NOT (…)
      F 必须先过 RESOURCES[resource] 字段白名单，白名单外一律 40044（防注入 + fail-closed）。
    """
    rows = eval_filter(_ROWS[resource], filter_node, allowed={f["name"] for f in RESOURCES[resource]["fields"]})
    window = rows[offset:offset + limit]
    total = len(rows) if CAPS["totalMode"] == "exact" else None   # none/estimated 按你的实现给
    return window, total, offset + len(window) < len(rows)


def eval_filter(rows, node, allowed):
    """filter DSL 求值（协议 §4.2 文法的参考实现；未知算子/字段一律 40044）。"""
    if node is None:
        return list(rows)
    if not isinstance(node, dict):
        raise Err(40044, "filter 节点须为对象")
    for key in ("and", "or"):
        if key in node:
            parts = [eval_filter(rows, x, allowed) if x else [] for x in node[key]]
            ids = set.intersection(*[{id(r) for r in p} for p in parts]) if key == "and" and parts else set()
            if key == "or":
                ids = set().union(*[{id(r) for r in p} for p in parts]) if parts else set()
            return [r for r in rows if id(r) in ids]
    if "not" in node:
        hit = {id(r) for r in eval_filter(rows, node["not"], allowed)}
        return [r for r in rows if id(r) not in hit]
    prop, op, val = node.get("prop") or "", node.get("op") or "", node.get("value")
    if prop not in allowed:
        raise Err(40044, f"字段 {prop} 不在资源字段白名单")
    out = []
    for r in rows:
        v = r.get(prop)
        try:
            if op == "eq":
                keep = v == val
            elif op == "ne":
                keep = v != val
            elif op in ("gt", "ge", "lt", "le"):
                keep = v is not None and val is not None and \
                    {"gt": v > val, "ge": v >= val, "lt": v < val, "le": v <= val}[op]
            elif op == "in":
                keep = v in (val or [])
            elif op == "contains":
                if "contains" not in CAPS["filterOps"]:
                    raise Err(40044, f"不支持的过滤算子 contains（字段 {prop}）")
                keep = isinstance(v, str) and isinstance(val, str) and val in v
            elif op == "isnull":
                keep = v is None
            else:
                raise Err(40044, f"不支持的过滤算子 {op}（字段 {prop}）")
        except TypeError:
            keep = False
        if keep:
            out.append(r)
    return out


class Err(Exception):
    def __init__(self, code, msg):
        self.code, self.msg = code, msg


class _Stop(Exception):
    pass


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # 安静模式
        pass

    def _send(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _auth(self):
        token = os.environ.get("ONTO_ADAPTER_TOKEN", "").strip()
        if token and self.headers.get("Authorization", "") != f"Bearer {token}":
            self._send({"code": 401, "msg": "unauthorized"}, status=401)   # HTTP 401：平台提示「认证失败」
            raise _Stop()

    def do_GET(self):
        try:
            self._auth()
            path, _, qs = self.path.partition("?")
            if path != "/onto-source/schema":
                return self._send({"code": 404, "msg": "not found"}, status=404)
            t = dict(p.split("=", 1) for p in qs.split("&") if "=" in p).get("type", "")
            if not t:   # 形态一：资源清单 + caps
                return self._send({"code": 0, "msg": "ok", "data": {
                    "caps": CAPS,
                    "resources": [{"type": k, "name": v["name"]} for k, v in RESOURCES.items()]}})
            if t not in RESOURCES:
                return self._send({"code": 40401, "msg": f"资源 {t} 不存在"})
            # 形态二：平台读取 resources[0].fields
            return self._send({"code": 0, "msg": "ok", "data": {
                "caps": CAPS,
                "resources": [{"type": t, "name": RESOURCES[t]["name"], "fields": RESOURCES[t]["fields"]}]}})
        except _Stop:
            pass

    def do_POST(self):
        try:
            self._auth()
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
            if body.get("version") != 1:                       # 未知顶层字段忽略；版本必须严格
                return self._send({"code": 40040, "msg": f"协议版本 {body.get('version')} 不支持"})
            t = body.get("type") or ""
            if t not in _ROWS:
                return self._send({"code": 40401, "msg": f"资源 {t} 不存在"})
            if self.path != "/onto-source/query" and self.path != "/onto-source/aggregate":
                return self._send({"code": 404, "msg": "not found"}, status=404)
            rows = eval_filter(_ROWS[t], body.get("filter"), allowed={f["name"] for f in RESOURCES[t]["fields"]})
            if self.path == "/onto-source/query":
                page = body.get("page") or {}
                limit = int(page.get("limit") or 50)
                if limit > CAPS["pageMax"]:                    # 红线：超页宽显式拒绝，绝不静默截断
                    return self._send({"code": 40046, "msg": f"页宽 {limit} 超出上限 {CAPS['pageMax']}"})
                window, total, has_more = fetch(t, body.get("filter"), int(page.get("offset") or 0), limit)
                pk = _PK[t]
                return self._send({"code": 0, "msg": "ok", "data": {
                    "items": [{"pk": str(r[pk]), "title": str(r[pk]), "props": r} for r in window],
                    "total": total,                            # totalMode=none → 恒 None（或省略键）
                    "hasMore": has_more}})
            agg = body.get("aggregate") or {}
            kind = agg.get("kind") or ""
            if kind == "count":
                return self._send({"code": 0, "msg": "ok", "data": {"count": len(rows)}})
            if kind in ("groupCount", "groupSum"):
                by = agg.get("groupBy") or ""
                if not by:
                    return self._send({"code": 40047, "msg": "groupX 缺 groupBy"})
                buckets, order = {}, []
                for r in rows:
                    k = r.get(by)
                    if k not in buckets:
                        buckets[k] = 0
                        order.append(k)
                    buckets[k] += (r.get(agg.get("prop") or "") or 0) if kind == "groupSum" else 1
                groups = [{"key": k, ("sum" if kind == "groupSum" else "count"): buckets[k]}
                          for k in sorted(order, key=lambda x: -buckets[x])]
                return self._send({"code": 0, "msg": "ok", "data": {"groups": groups}})
            return self._send({"code": 40047, "msg": f"不支持的聚合 {kind}"})
        except _Stop:
            pass
        except Err as e:
            self._send({"code": e.code, "msg": e.msg})         # 业务错误：HTTP 200 + 信封 code
        except Exception as e:  # noqa: BLE001
            self._send({"code": 50000, "msg": str(e)})


if __name__ == "__main__":
    port = int(os.environ.get("ONTO_ADAPTER_PORT") or 8600)
    print(f"onto-source adapter on http://127.0.0.1:{port} (pid={os.getpid()})", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
