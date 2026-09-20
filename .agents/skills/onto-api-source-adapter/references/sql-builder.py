#!/usr/bin/env python3
"""协议 filter DSL → SQL 编译器（方言感知：PostgreSQL / MySQL / Oracle；配套 sql-translation.md）。

把 /onto-source/query|aggregate 收到的 JSON 编译成【参数化 SQL + 参数列表】。
直接抄进你的适配器：把 TableSpec 的映射表换成你自己的即可；执行与行→items 组装参考 fetch() 注释。

    python3 sql-builder.py        # 跑内置演示：若干请求 → SQL（验证编译器本身，无需数据库）

安全设计（sql-translation.md §1 三铁律的落地）：
  1) 标识符（表/列）只来自 TableSpec 白名单，请求里的 type/prop 查不到即 40044；
  2) 值 100% 参数绑定，占位符按方言生成（PG $n / MySQL %s / Oracle :n）；
  3) 标识符加方言引用符（PG/Oracle "x"、MySQL `x`）。
"""
import json

# ── 表规格：type → 表、协议字段 → 列、主键协议字段、标题协议字段（★换成你的映射） ──
TABLES = {
    "PurchaseOrder": {
        "table": "erp_purchase_order",
        "columns": {"po_no": "po_no", "status": "status", "amount": "amount",
                    "orderDate": "order_date", "remark": "remark", "lines": "lines"},
        "pk": "po_no", "title": "po_no",
    },
}


class Err(Exception):
    def __init__(self, code, msg):
        self.code, self.msg = code, msg


class SqlBuilder:
    def __init__(self, dialect="pg"):
        assert dialect in ("pg", "mysql", "oracle")
        self.dialect = dialect
        self.params = []
        self._n = 0

    # ── 基础件 ──────────────────────────────────────────────
    def _q(self, ident):  # 标识符引用
        return f"`{ident}`" if self.dialect == "mysql" else f'"{ident}"'

    def _ph(self, value):  # 值占位符（值恒绑定）
        self.params.append(value)
        if self.dialect == "pg":
            return f"${len(self.params)}"
        if self.dialect == "oracle":
            return f":{len(self.params)}"
        return "%s"

    def compile_filter(self, spec, node):
        """filter 节点 → WHERE 字符串（无过滤返回 None；恒假返回 1=0）。"""
        if node is None:
            return None
        if not isinstance(node, dict):
            raise Err(40044, "filter 节点须为对象")
        for key in ("and", "or"):
            if key in node:
                parts = [self.compile_filter(spec, x) for x in (node[key] or [])]
                parts = [p for p in parts if p]
                if not parts:
                    return None
                glue = " AND " if key == "and" else " OR "
                return "(" + glue.join(parts) + ")"
        if "not" in node:
            inner = self.compile_filter(spec, node["not"])
            return None if inner is None else f"NOT ({inner})"
        prop, op, val = node.get("prop") or "", node.get("op") or "", node.get("value")
        col = spec["columns"].get(prop)          # 铁律 1：白名单外 40044，绝不进 SQL
        if not col:
            raise Err(40044, f"字段 {prop} 不在资源字段白名单")
        c = self._q(col)
        if op == "eq":
            return f"{c} = {self._ph(val)}"
        if op == "ne":
            return f"{c} <> {self._ph(val)}"     # NULL 行被排除；要含 NULL 见 sql-translation.md §2
        if op in ("gt", "ge", "lt", "le"):
            sym = {"gt": ">", "ge": ">=", "lt": "<", "le": "<="}[op]
            return f"{c} {sym} {self._ph(val)}"
        if op == "in":
            vals = val or []
            if not vals:                          # 铁律边缘：空数组恒假，禁生成 IN ()
                return "1 = 0"
            return f"{c} IN ({', '.join(self._ph(v) for v in vals)})"
        if op == "contains":
            like = "%" + str(val).replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_") + "%"
            kw = "ILIKE" if (self.dialect == "pg") else "LIKE"
            esc = "" if self.dialect == "pg" else " ESCAPE '\\\\'"
            return f"{c} {kw} {self._ph(like)}{esc}"
        if op == "isnull":
            return f"{c} IS NULL"
        raise Err(40044, f"不支持的过滤算子 {op}（字段 {prop}）")

    # ── 两个端点的编译 ──────────────────────────────────────
    def compile_query(self, body, page_max):
        spec = TABLES.get(body.get("type") or "")
        if not spec:
            raise Err(40401, f"资源 {body.get('type')} 不存在")
        where = self.compile_filter(spec, body.get("filter"))
        page = body.get("page") or {}
        limit, offset = int(page.get("limit") or 50), int(page.get("offset") or 0)
        if limit > page_max:
            raise Err(40046, f"页宽 {limit} 超出上限 {page_max}")
        cols = ", ".join(self._q(c) for c in spec["columns"].values())
        sql = f"SELECT {cols} FROM {self._q(spec['table'])}"
        if where:
            sql += f" WHERE {where}"
        sql += f" ORDER BY {self._q(spec['pk'])}"        # 稳定序恒带主键
        sql += {"pg": f" LIMIT {limit} OFFSET {offset}",
                "mysql": f" LIMIT {limit} OFFSET {offset}",
                "oracle": f" OFFSET {offset} ROWS FETCH NEXT {limit} ROWS ONLY"}[self.dialect]
        return sql

    def compile_aggregate(self, body):
        spec = TABLES.get(body.get("type") or "")
        if not spec:
            raise Err(40401, f"资源 {body.get('type')} 不存在")
        agg = body.get("aggregate") or {}
        kind = agg.get("kind") or ""
        where = self.compile_filter(spec, body.get("filter"))
        base = f" FROM {self._q(spec['table'])}" + (f" WHERE {where}" if where else "")
        if kind == "count":
            return f"SELECT COUNT(*) AS c{base}"
        if kind == "groupCount":
            by = spec["columns"].get(agg.get("groupBy") or "")
            if not by:
                raise Err(40047, "groupCount 缺 groupBy")
            k = self._q(by)
            return f"SELECT {k} AS k, COUNT(*) AS c{base} GROUP BY {k} ORDER BY c DESC"
        if kind == "groupSum":
            by, su = spec["columns"].get(agg.get("groupBy") or ""), spec["columns"].get(agg.get("prop") or "")
            if not by or not su:
                raise Err(40047, "groupSum 缺 groupBy/prop")
            k, s = self._q(by), self._q(su)
            return f"SELECT {k} AS k, SUM({s}) AS s{base} GROUP BY {k} ORDER BY s DESC"
        raise Err(40047, f"不支持的聚合 {kind}")


if __name__ == "__main__":
    CASES = [
        ("query 嵌套 filter", "pg", {
            "version": 1, "type": "PurchaseOrder",
            "filter": {"and": [{"prop": "status", "op": "eq", "value": "approved"},
                               {"or": [{"prop": "amount", "op": "ge", "value": 10000},
                                       {"not": {"prop": "remark", "op": "isnull"}}]}]},
            "page": {"offset": 0, "limit": 50}}),
        ("in 列表（pk 桥接回查）", "mysql", {
            "version": 1, "type": "PurchaseOrder",
            "filter": {"prop": "po_no", "op": "in", "value": ["PO-1", "PO-2", "PO-3"]},
            "page": {"offset": 0, "limit": 100}}),
        ("contains 转义 + isnull", "pg", {
            "version": 1, "type": "PurchaseOrder",
            "filter": {"and": [{"prop": "remark", "op": "contains", "value": "100%完_好"},
                               {"prop": "remark", "op": "isnull"}]},
            "page": {"offset": 20, "limit": 10}}),
        ("空数组 IN → 恒假", "oracle", {
            "version": 1, "type": "PurchaseOrder",
            "filter": {"prop": "po_no", "op": "in", "value": []},
            "page": {"offset": 0, "limit": 50}}),
        ("groupSum", "pg", {"version": 1, "type": "PurchaseOrder",
                            "filter": {"prop": "status", "op": "ne", "value": "draft"},
                            "aggregate": {"kind": "groupSum", "groupBy": "status", "prop": "amount"}}),
    ]
    for name, d, body in CASES:
        b = SqlBuilder(dialect=d)
        if "aggregate" in body:
            sql = b.compile_aggregate(body)
        else:
            sql = b.compile_query(body, page_max=100)
        print(f"── {name} [{d}] params={b.params}\n{sql}\n")
    try:
        SqlBuilder(dialect="pg").compile_query({"version": 1, "type": "PurchaseOrder",
                                                "filter": {"prop": "ghost", "op": "eq", "value": 1},
                                                "page": {"limit": 10}}, page_max=100)
    except Err as e:
        print(f"── 白名单外字段 → code={e.code}（{e.msg}）\n")
    try:
        SqlBuilder(dialect="pg").compile_query({"version": 1, "type": "PurchaseOrder",
                                                "page": {"limit": 999}}, page_max=100)
    except Err as e:
        print(f"── 超页宽 → code={e.code}（{e.msg}）")
