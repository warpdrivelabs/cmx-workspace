#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
onto_seed.py —— 本体平台演示数据·规格驱动造数器
================================================
读「场景规格 JSON」（scenario-spec），按依赖顺序调 cmx-ontology REST API 灌数：

    sharedProperties → interfaces → objectTypes → linkTypes → functions → actions
    → dctImports（import/dct，字典项物化） → funnelMappings（+sync，支持跨库 sourceDbId）
    → objects（批量 upsert） → links（关系边） → views（场景视图） → snapshot（存档基线）
    → docImports（import/doc，单据只入定义）

所有写接口均为 upsert 语义，**幂等可重跑**（links 依赖 ol_edge 主键去重；views 需 version 递增
或保持缺省盲写）。执行完打印各段结果汇总，任何一段失败即退出非 0。

用法：
  python3 onto_seed.py --spec scenario-spec.json [--base http://127.0.0.1:8097]
        [--api-key cmx_sk_dev_...] [--ontology default_ontology]
        [--skip objects|links|funnelSync,…] [--only <段名>,…]

规格 schema（各段均可省略）见 examples/procurement/scenario-spec.json 注释。
"""
import argparse
import json
import sys
import urllib.error
import urllib.request

DEFAULT_BASE = "http://127.0.0.1:8097"
DEFAULT_KEY = "cmx_sk_dev_A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6"
DEFAULT_ONTOLOGY = "default_ontology"

# 段 → (api 路径模板, 是否逐条 POST)
SECTION_APIS = {
    "sharedProperties": "/shared-properties/save",
    "interfaces": "/interfaces/save",
    "objectTypes": "/object-types/save",
    "linkTypes": "/link-types/save",
    "functions": "/functions/save",
    "actions": "/action-types/save",
    "dctImports": "/import/dct",
    "docImports": "/import/doc",
}
ORDER = ["sharedProperties", "interfaces", "objectTypes", "linkTypes", "functions", "actions",
         "dctImports", "funnelMappings", "objects", "links", "views", "snapshot", "docImports"]


class SeedError(Exception):
    pass


# 动作/函数定义数组字段的脏项剔除（对齐 studio normalizeDefArrays）：logic/parameters/
# validations/sideEffects/inputs 必须是干净对象数组——om_action_type.logic 落 [null] 会让
# 工作室 Inspector 渲染崩、执行解析挂；空编辑集必须写 []，禁止 null / [null]。
DEF_ARRAY_FIELDS = ("parameters", "logic", "validations", "sideEffects", "inputs")


def sanitize_def(item):
    if isinstance(item, dict):
        for k in DEF_ARRAY_FIELDS:
            v = item.get(k)
            if isinstance(v, list):
                item[k] = [x for x in v if isinstance(x, dict)]
    return item


def call(base, path, body, api_key, ontology=DEFAULT_ONTOLOGY, method="POST"):
    # M1 起本体参数必填：统一追加 ?ontology=（path 现均无自带查询串）。
    sep = "&" if "?" in path else "?"
    req = urllib.request.Request(
        base.rstrip("/") + "/api/onto/v1" + path + sep + "ontology=" + ontology,
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
        headers={"Content-Type": "application/json", "X-API-Key": api_key})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode()[:400]
        except Exception:
            pass
        raise SeedError(f"{method} {path} → HTTP {e.code}: {detail}")
    if resp.get("code") != 0:
        raise SeedError(f"{method} {path} → code={resp.get('code')} {resp.get('msg')}")
    return resp.get("data")


def run_section(name, spec, base, key, ontology, summary):
    items = spec.get(name)
    if not items:
        return
    if name in SECTION_APIS:
        path = SECTION_APIS[name]
        if isinstance(items, dict):  # 单对象段
            items = [items]
        for i, item in enumerate(items):
            call(base, path, sanitize_def(item), key, ontology)
            label = item.get("apiName") or item.get("objectType") or f"#{i + 1}"
            summary.append(f"{name}: {label}")
    elif name == "funnelMappings":
        for m in items:
            ot = m["objectType"]
            call(base, "/funnel/mappings/save", m, key, ontology)
            summary.append(f"funnel.mapping: {ot} (db={m.get('sourceDbId') or 'onto_pg'})")
            if not spec.get("_skipFunnelSync"):
                rep = call(base, "/funnel/sync", {"objectType": ot}, key, ontology)
                summary.append(
                    f"funnel.sync: {ot} read={rep.get('read')} written={rep.get('written')} quarantined={rep.get('quarantined')}")
    elif name == "objects":
        for ot, rows in items.items():
            # M1 §3.7 去路径化：POST /objects/save-batch body {objectType, items}
            data = call(base, "/objects/save-batch", {"objectType": ot, "items": rows}, key, ontology)
            written = data.get("written") if isinstance(data, dict) else "?"
            summary.append(f"objects: {ot} ×{len(rows)} (written={written})")
    elif name == "links":
        by_link = {}
        for l in items:
            by_link.setdefault(l["link"], []).append(l)
        for link, ls in by_link.items():
            ok = 0
            for l in ls:
                call(base, "/links/save", {"link": l["link"], "aPk": l["aPk"], "bPk": l["bPk"]}, key, ontology)
                ok += 1
            summary.append(f"links: {link} ×{ok}")
    elif name == "views":
        for v in items:
            call(base, "/views/save", v, key, ontology)
            summary.append(f"view: {v['apiName']}「{v.get('displayName')}」 objects={v.get('members', {}).get('objects')}")
    elif name == "snapshot":
        rep = call(base, "/snapshots", {"summary": items if isinstance(items, str) else items.get("summary", "")}, key, ontology)
        summary.append(f"snapshot: version={rep.get('version')} deduped={rep.get('deduped')}")


def main():
    ap = argparse.ArgumentParser(description="本体平台演示数据·规格驱动造数器")
    ap.add_argument("--spec", required=True, help="场景规格 JSON 路径")
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--api-key", default=DEFAULT_KEY)
    ap.add_argument("--ontology", default=DEFAULT_ONTOLOGY,
                    help="目标本体 apiName（M1 起接口必填；缺省 default_ontology）")
    ap.add_argument("--skip", help="跳过的子段（逗号分隔，如 funnelSync,links）")
    ap.add_argument("--only", help="只执行这些段（逗号分隔）")
    args = ap.parse_args()

    with open(args.spec, encoding="utf-8") as f:
        spec = json.load(f)
    if args.skip:
        for s in args.skip.split(","):
            s = s.strip()
            if s == "funnelSync":
                spec["_skipFunnelSync"] = True
            elif s in spec:
                del spec[s]
    sections = ORDER
    if args.only:
        sections = [s.strip() for s in args.only.split(",")]

    summary = []
    for name in sections:
        try:
            run_section(name, spec, args.base, args.api_key, args.ontology, summary)
        except SeedError as e:
            print(f"FAILED at [{name}]: {e}", file=sys.stderr)
            print("\n".join(summary))
            sys.exit(1)
    print("=== 造数完成 ===")
    for line in summary:
        print(" ", line)


if __name__ == "__main__":
    main()
