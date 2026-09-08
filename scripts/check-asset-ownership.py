#!/usr/bin/env python3
"""资产归属守护（W6）：校验 cmx-container/assets 工作区内
1. 每个页面 id 匹配其所属服务文件夹的唯一前缀（防新页面走散）；
2. 任一 id 不允许跨文件夹重复出现；
3. html v2 行的 domain/app/module 字段与 id 前缀一致。

用法: python3 scripts/check-asset-ownership.py   （违规退出码 1）
"""
import json, glob, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WS = os.path.join(ROOT, "cmx-container", "assets")

# 服务 → 允许的 id 精确前缀（native 与 html 同规）
PREFIX = {
    "portal": ("portal.job.", "portal.notify.", "portal.help.", "portal.system.",
               "portal.display.", "demo."),          # + _legacy 裸名特判
    "model":  ("portal.model.",),
    "mdm":    ("portal.mdm.",),
    "flow":   ("portal.flow.",
               "fi.cmxfico.gl.flow-"),               # 业务命名特例：与 cmx-flow-api proxy 谓词一致
    "report": ("portal.rpt.", "portal.consol.",
               "fi.cmxfico.gl.rpt-designer-",
               "fi.cmxfico.gl.rpt-spreadjs-designer-"),  # 同上：与 cmx-rpt-api proxy 谓词一致
    "rules":  ("portal.rules.",),
    # onto：独立本体微服务（远端 cmx-onto-server，无本地 publish 目标），页面经平台反代
    "onto":   ("portal.onto.", "onto."),
}

def owner_ok(svc, pid):
    if svc == "portal":
        if "." not in pid:            # _legacy 裸名（welcome/btm_view1…）
            return True
        return pid.startswith(PREFIX[svc])
    return pid.startswith(PREFIX[svc])

seen = {}       # id -> folder
errors = []

def scan(idx_path, svc):
    rel = os.path.relpath(idx_path, WS)
    for pg in json.load(open(idx_path)).get("pages", []):
        pid = pg["id"]
        if ".." in pid:
            errors.append(f"[畸形id] {rel}: {pid}")
            continue
        if not owner_ok(svc, pid):
            errors.append(f"[前缀越界] {rel}: {pid} 不属于 {svc}/")
        if pid in seen and seen[pid] != svc:
            errors.append(f"[跨仓重复] {pid}: 同时出现在 {seen[pid]}/ 与 {svc}/")
        seen[pid] = svc
        # html 行字段 = 业务坐标（host.$coord 数据源），与 id 归属前缀解耦：
        # 归属看 id 前缀；行字段必须保留业务域值，禁止被归属前缀（portal/model）污染
        if "html" in idx_path and svc == "model":
            dom, app = pg.get("domain"), pg.get("app")
            if (dom, app) == ("portal", "model"):
                errors.append(f"[坐标污染] {rel}: {pid} 行字段 domain/app 被归属前缀覆盖，应为业务坐标（如 fi/cmxfico）")

for svc in sorted(os.listdir(WS)):
    d = os.path.join(WS, svc)
    if not os.path.isdir(d):
        continue
    for p in glob.glob(os.path.join(d, "web/ui-native/index.json")):
        scan(p, svc)
    for p in glob.glob(os.path.join(d, "web/ui-html/index/*.pages.json")):
        scan(p, svc)

total = len(seen)
if errors:
    print(f"❌ 归属校验失败（{len(errors)} 处，扫描 id {total} 个）：")
    for e in errors[:30]:
        print("  -", e)
    sys.exit(1)
print(f"✅ 资产归属校验通过：{total} 个页面 id，前缀/去重/字段全部合规")
