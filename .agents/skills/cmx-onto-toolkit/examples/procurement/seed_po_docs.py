#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
采购订单单据灌数（业务库 fico）
================================
经门户 /api/doc/save 写 10 张正式采购订单（覆盖全状态机），单据编码 PO-2026-XXXX 直接给值
（不走编码引擎）。幂等性：doc_no 有唯一键，重复执行会撞唯一键报错——重灌前先删
（psql: DELETE FROM cv_po_line WHERE upper_id IN (SELECT id FROM cv_po_order); DELETE FROM cv_po_order;）。

用法：
  python3 seed_po_docs.py [--portal http://127.0.0.1:8080]
前提：purchase_doc_meta_v1.json 已 deploy 到 fico-db（cv_po_order/cv_po_line 表已建）。
"""
import argparse
import json
import urllib.request

DOC_Q = {"domain": "basic", "application": "dataplatform", "module": "purchase", "file": "purchase_doc_meta_v1.json"}
API_KEY = "cmx_sk_dev_A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6"
DB_ID = "fico-db"

# (单号, 状态, 供应商编码, 供应商名称, 采购员, 期望到货, 总金额, [(行号,物料编码,物料名,数量,单价,已收数量), …])
ORDERS = [
    ("PO-2026-0001", "draft", "SUP0001", "苏州精工机械有限公司", "王建国", "2026-09-20", 86000.00,
     [(1, "GYL-001", "45号碳钢圆钢", 200, 180.0, 0), (2, "GYL-002", "Q235钢板", 500, 100.0, 0)]),
    ("PO-2026-0002", "submitted", "SUP0001", "苏州精工机械有限公司", "王建国", "2026-09-25", 45000.00,
     [(1, "LJ-001", "高强度螺栓M12", 20000, 1.25, 0), (2, "ZC-001", "轴承6204", 800, 25.0, 0)]),
    ("PO-2026-0003", "submitted", "SUP0002", "宁波华信金属材料有限公司", "李晓峰", "2026-09-22", 132000.00,
     [(1, "LH-001", "铝合金型材", 1200, 60.0, 0), (2, "HG-001", "环氧树脂", 600, 100.0, 0)]),
    ("PO-2026-0004", "approved", "SUP0002", "宁波华信金属材料有限公司", "李晓峰", "2026-09-18", 96000.00,
     [(1, "GYL-001", "45号碳钢圆钢", 300, 180.0, 0), (2, "DZ-001", "铜接线端子", 20000, 2.1, 0)]),
    ("PO-2026-0005", "approved", "SUP0003", "山东鲁化集团有限公司", "王建国", "2026-09-16", 150000.00,
     [(1, "HG-001", "环氧树脂", 1000, 100.0, 0), (2, "TL-001", "防锈漆", 500, 100.0, 0)]),
    ("PO-2026-0006", "partial_received", "SUP0004", "广州恒达电子科技有限公司", "陈静", "2026-09-10", 66000.00,
     [(1, "DZ-001", "铜接线端子", 10000, 2.1, 6000), (2, "ZC-001", "轴承6204", 1200, 25.0, 0)]),
    ("PO-2026-0007", "completed", "SUP0004", "广州恒达电子科技有限公司", "陈静", "2026-09-05", 37500.00,
     [(1, "DZ-001", "铜接线端子", 15000, 2.1, 15000), (2, "LJ-001", "高强度螺栓M12", 6000, 1.25, 6000)]),
    ("PO-2026-0008", "completed", "SUP0005", "常州密封件股份有限公司", "李晓峰", "2026-09-02", 24000.00,
     [(1, "MF-001", "橡胶密封圈", 8000, 3.0, 8000)]),
    ("PO-2026-0009", "closed", "SUP0006", "上海联合包装制品有限公司", "王建国", "2026-08-28", 19800.00,
     [(1, "BZ-001", "瓦楞纸箱", 12000, 1.4, 8000), (2, "BZ-002", "缠绕膜", 600, 5.0, 0)]),
    ("PO-2026-0010", "cancelled", "SUP0003", "山东鲁化集团有限公司", "李晓峰", "2026-09-30", 80000.00,
     [(1, "YH-001", "工业润滑油", 4000, 20.0, 0)]),
]


def post(url, body):
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json", "X-API-Key": API_KEY, "db_id": DB_ID})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--portal", default="http://127.0.0.1:8080")
    args = ap.parse_args()
    from urllib.parse import urlencode
    url = args.portal.rstrip("/") + "/api/doc/save?" + urlencode(DOC_Q)
    ok = fail = 0
    for (doc_no, status, sup_code, sup_name, buyer, expected, total, lines) in ORDERS:
        tid = f"T-{doc_no}"
        changes = {
            "cv_po_order": {"inserted": [{"id": tid, "fields": {
                "line_no": 1, "doc_status": status, "doc_type": "po", "doc_type_id": 1, "entity_id": 1,
                "doc_date": "2026-09-08", "doc_no": doc_no,
                "supplier_code": sup_code, "supplier_name": sup_name,
                "buyer": buyer, "expected_date": expected,
                "currency": "CNY", "total_amount": total, "remark": f"采购演示单据 {doc_no}",
            }}]},
            "cv_po_line": {"inserted": [{
                "id": f"{tid}-L{ln}", "upper_id": tid,
                "fields": {"line_no": ln, "material_code": mc, "material_name": mn,
                           "qty": q, "unit_price": p, "amount": round(q * p, 2), "received_qty": rq},
            } for (ln, mc, mn, q, p, rq) in lines]},
        }
        try:
            resp = post(url, {"saveMode": "merge", "changes": changes, "tableNames": ["cv_po_order", "cv_po_line"]})
            data = resp.get("data") or {}
            # 注意：信封 code==0 不代表保存成功——校验失败返回 data.ok=false + violations
            if resp.get("code") == 0 and data.get("ok") is not False and not data.get("violations"):
                ok += 1
                print(f"OK {doc_no} affected={data.get('affected')} idMap={data.get('idMap')}")
            else:
                fail += 1
                print(f"FAIL {doc_no}: {resp.get('msg')} data={json.dumps(data, ensure_ascii=False)[:300]}")
        except Exception as e:
            fail += 1
            print(f"FAIL {doc_no}: {e}")
    print(f"\n完成：成功 {ok} / 失败 {fail}（预期 10 单）")
    if fail:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
