#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cmx-flowengine 流程定义创建器（P0 契约：流程定义 × 审批定义分离）
============================

作用：把声明式 spec（JSON）编译成**语义 BPMN 2.0 XML**（无 DI，设计器打开自动布局），
可选经 REST **五步**部署到 flow-server 并起冒烟实例验证首节点停留位置。

P0 核心契约（与旧版的关键差异）：
  1. **BPMN 零审批属性**：办理人/抄送一律走审批定义（approvalDefs），spec 节点出现
     assignee/candidateUsers/candidateGroups/candidates/cc 直接拒绝（REJECTED_KEYS）。
  2. **五步部署链**：validate → draft → publish（key 在 body）→ approval-defs/save →
     forms/save（可选）→ approval-defs/startable 发起预检。
  3. **发起闸**：所有 userTask 节点都需要审批定义（静态 assignee 不豁免——本脚本已禁止
     在 BPMN 写审批属性，漏配会在 startable 预检暴露，运行期则 400）。
  4. **M1 拓扑**：userTask 出边必须恰 1 条；分支语义用排他/包容网关表达。
  5. 实例端点改为 /instances/start 与 /instances/cancel（body 带 id）。

语法契约源：backend/cmx-flowengine 路由表（cmx-flow-app/src/lib.rs RouteDef）与
cmx-flow-model/src/approval.rs；完整速查见技能 references/bpmn-def-guide.md。

spec 结构（examples/def-spec-*.json 为可运行样例）：
{
  "key":   "expense_v2",            // = process id = 定义 key
  "name":  "报销审批v2",
  "start": {"id":"s","name":"发起"},            // 可省：自动补 s → 首节点
  "nodes": [
    {"id":"mgr","type":"userTask","name":"经理审批","formMode":"approve"},
    {"id":"sign","type":"userTask","name":"会签"},   // 会签/或签由审批定义 mode 驱动，勿写 mi
    {"id":"risk","type":"serviceTask","name":"风控","delegate":"riskDelegate"},
    {"id":"level","type":"businessRuleTask","name":"定级","decisionRef":"approval_matrix"},
    {"id":"gw","type":"exclusiveGateway","name":"金额","defaultTo":"fin"},   // 缺省边指向的目标节点
    {"id":"call","type":"callActivity","name":"财务复核","calledKey":"fin_review",
     "inVars":"amount:subAmount, applicant","outVars":"subResult:reviewResult"},
    {"id":"wait","type":"messageCatch","name":"等外部","message":"verdictReceived",
     "correlationVar":"orderId"},
    {"id":"ok","type":"endEvent","name":"通过"},
    {"id":"rej","type":"endEvent","name":"否决","terminate":true},
    {"id":"mgr2","type":"userTask","name":"限时审批",
     "timers":[{"duration":"PT30S","to":"director"},               // 中断型升级
               {"duration":"PT20S","cancelActivity":false,"to":"notify"}]}  // 非中断催办
  ],
  "flows": [
    {"from":"s","to":"mgr"},
    {"from":"gw","to":"dir","condition":"${amount > 20000}","name":"大额"}
  ],
  // 审批定义（办理人真源）。orgId 必须真实存在于组织树；USER value 必须是**用户 id**（非账号名）。
  "approvalDefs": {
    "orgId": "org-root",
    "note": "v1 单签",
    "nodes": {
      "mgr":  {"inherit": false, "mode": "SINGLE",
               "objects": [{"kind": "USER", "value": "7503326638169403392"}],
               "emptyPolicy": "INCIDENT"},
      "sign": {"inherit": false, "mode": "PARALLEL_COUNTERSIGN",
               "collectionVar": "reviewers", "elementVar": "reviewer",
               "completionCondition": "${nrOfCompletedInstances/nrOfInstances >= 0.5}"},
      "mgr2": {"inherit": false, "mode": "SINGLE",
               "objects": [{"kind": "ROLE", "value": "manager"}],
               "cc": [{"kind": "USER", "value": "u_auditor1"}]}
    }
  },
  // 表单绑定（可选；不写 formKey → 待办中心走通用办结 UI，无需本段）
  "forms": [{"formKey": "fin_form", "kind": "NATIVE", "nativePage": "…"}],
  "deploy": {"server":"http://127.0.0.1:8091","apiKey":"cmx_sk_dev_...",
             "note":"上线 v1","publishedBy":"agent","name":"报销审批v2",
             "domain":"fi","application":"cmxfico","module":"gl"},
  "smoke":  {"orgId":"org-root","businessKey":"SMOKE-001",
             "variables":{"amount":50000,"initiator":"7503326638169403392"},
             "expectActive":["mgr"]}       // 起完断言 activeNodes；可另加 "cancel": true 收尾
}

用法：
  python3 create_flow_def.py --spec spec.json [--out out.bpmn]
         [--deploy] [--smoke] [--server URL] [--api-key KEY]

校验（写文件前必过）：唯一 startEvent；flows 端点存在；排他/包容网关 defaultTo 可解析；
至少一个 endEvent；userTask 出边恰 1 条（M1 拓扑）；无 BPMN 审批属性；XML 良构。
部署信封 code==0 且 validate data.valid==true 才继续（软失败也是 HTTP 200，必须看 valid）。
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

# 引擎白名单（usage/02 §2.4）；黑名单元素明确拒绝（§2.12）
NODE_TYPES = {
    "startEvent", "endEvent", "userTask", "serviceTask", "businessRuleTask",
    "exclusiveGateway", "parallelGateway", "inclusiveGateway", "callActivity",
    "messageCatch",
}
BLACKLIST = {"task", "scriptTask", "sendTask", "receiveTask", "manualTask",
             "eventBasedGateway", "complexGateway", "intermediateThrowEvent"}
# P0：BPMN 零审批属性——办理人/抄送真源在审批定义，spec 出现即拒
REJECTED_KEYS = {"assignee", "candidateUsers", "candidateGroups", "candidates", "cc"}


class SpecError(Exception):
    pass


def esc(s):
    return escape(str(s), {'"': "&quot;"})


def build_bpmn(spec):
    nodes = [dict(n) for n in spec.get("nodes", [])]
    flows = [dict(f) for f in spec.get("flows", [])]
    ids = [n["id"] for n in nodes]
    if len(ids) != len(set(ids)):
        dup = [x for x in ids if ids.count(x) > 1]
        raise SpecError(f"节点 id 重复: {sorted(set(dup))}")

    # P0：BPMN 零审批属性——出现即拒，指路 approvalDefs
    for n in nodes:
        hit = REJECTED_KEYS & set(n)
        if hit:
            raise SpecError(
                f"节点 {n['id']} 含 BPMN 审批属性 {sorted(hit)}（P0 已废除）："
                f"办理人/抄送改写 spec.approvalDefs.nodes.{n['id']}（见 references/bpmn-def-guide.md §3）")

    # 会签/或签由审批定义 mode 驱动（编译器生成 MI 域），spec 级 mi 与其互斥
    ad_nodes = ((spec.get("approvalDefs") or {}).get("nodes") or {})
    for n in nodes:
        if n.get("mi") and n["id"] in ad_nodes:
            raise SpecError(
                f"节点 {n['id']} 同时有 mi 与审批定义：会签由 approvalDefs 的 mode/collectionVar 驱动，"
                f"请删除 spec 级 mi（编译器自动生成 MI 域）")

    # 自动补 start / end
    has_start = any(n.get("type") == "startEvent" for n in nodes)
    if not has_start:
        start = dict(spec.get("start") or {"id": "s", "name": "发起"})
        start.setdefault("type", "startEvent")
        if start["id"] in ids:
            raise SpecError(f"自动 start id 冲突: {start['id']}")
        nodes.insert(0, start)
        ids.insert(0, start["id"])
    starts = [n for n in nodes if n.get("type") == "startEvent"]
    if len(starts) != 1:
        raise SpecError(f"startEvent 必须恰好一个，现有 {len(starts)}")

    # 入度=0 且非 start 的节点 → 由 start 连入（仅当 flows 里没有 start 出边时）
    s_id = starts[0]["id"]
    if not any(f["from"] == s_id for f in flows):
        timer_targets = {t.get("to") for n in nodes for t in (n.get("timers") or [])}
        no_in = [n["id"] for n in nodes
                 if n["id"] != s_id and n.get("type") != "endEvent"
                 and n["id"] not in timer_targets
                 and not any(f["to"] == n["id"] for f in flows)]
        if len(no_in) != 1:
            raise SpecError(f"无法自动连 start（入度 0 的非终点节点有 {len(no_in)} 个: {no_in}），请在 flows 显式连边")
        flows.insert(0, {"from": s_id, "to": no_in[0]})
        print(f"NOTE: 自动补边 {s_id} -> {no_in[0]}（如非预期请检查 flows 拼写）", file=sys.stderr)

    if not any(n.get("type") == "endEvent" for n in nodes):
        end = {"id": "e", "type": "endEvent", "name": "完成"}
        if end["id"] in ids:
            end = {"id": "e2", "type": "endEvent", "name": "完成"}
        nodes.append(end)
        ids.append(end["id"])
    # 出度 0 的节点 → 连到单个 endEvent（仅当该节点没有任何出边）
    end_events = [n["id"] for n in nodes if n.get("type") == "endEvent"]
    sinks = [n["id"] for n in nodes
             if n.get("type") not in ("endEvent", "startEvent")
             and not any(f["from"] == n["id"] for f in flows)]
    if sinks:
        if len(end_events) != 1:
            raise SpecError(f"有出度 0 节点 {sinks} 需自动连终点，但 endEvent 有 {len(end_events)} 个，请显式连边")
        for s_ in sinks:
            flows.append({"from": s_, "to": end_events[0]})
        print(f"NOTE: 自动补边 {sinks} -> {end_events[0]}（如非预期请检查 flows 拼写）", file=sys.stderr)

    # 端点存在性
    for f in flows:
        for side in ("from", "to"):
            if f[side] not in ids:
                raise SpecError(f"flow {f['from']}->{f['to']} 的 {side} 不存在: {f[side]}")
        if f["from"] in end_events:
            raise SpecError(f"终点 {f['from']} 不能有出边")

    # M1 拓扑：userTask 出边必须恰 1 条（分支语义走网关；定时器出边是边界事件不算）
    out_deg = {}
    for f in flows:
        out_deg[f["from"]] = out_deg.get(f["from"], 0) + 1
    for n in nodes:
        if n.get("type") == "userTask" and out_deg.get(n["id"], 0) > 1:
            raise SpecError(
                f"userTask {n['id']} 出边 {out_deg[n['id']]} 条（M1 拓扑要求恰 1 条）："
                f"分支语义请加排他/包容网关")

    # 网关 defaultTo → default 边 id
    flow_id = {}
    for i, f in enumerate(flows):
        fid = f.get("id") or f"f{i + 1}"
        if fid in flow_id:
            raise SpecError(f"flow id 冲突: {fid}")
        flow_id[fid] = f
        f["_id"] = fid
    for n in nodes:
        if n.get("type") in ("exclusiveGateway", "inclusiveGateway") and n.get("defaultTo"):
            cands = [f for f in flows if f["from"] == n["id"] and f["to"] == n["defaultTo"]]
            if len(cands) != 1:
                raise SpecError(f"{n['id']} 的 defaultTo={n['defaultTo']} 无唯一出边（命中 {len(cands)} 条）")
            n["_default_flow"] = cands[0]["_id"]

    # 定时器宿主与目标校验（边界定时器只能挂 userTask，usage/02 §2.10）
    for n in nodes:
        if n.get("timers"):
            if n.get("type") != "userTask":
                raise SpecError(f"{n['id']} 挂了 timers，但边界定时器宿主必须是 userTask（当前 {n.get('type')}）")
            for t in n["timers"]:
                if t.get("to") not in ids:
                    raise SpecError(f"{n['id']} 定时器目标不存在: {t.get('to')}")

    # 定时器生成 id 并入重名校验，防与用户/flow id 撞车
    gen_ids = []
    for n in nodes:
        for k, _t in enumerate(n.get("timers") or []):
            gen_ids += [f"{n['id']}_timer{k + 1}", f"{n['id']}_timer{k + 1}_out"]
    clash = [x for x in gen_ids if x in ids]
    if clash:
        raise SpecError(f"定时器生成 id 与节点 id 冲突: {clash}")
    clash2 = [x for x in flow_id if x in gen_ids]
    if clash2:
        raise SpecError(f"flow id 与定时器生成 id 冲突: {clash2}")
    # 节点未知键告警（防笔误静默丢属性）
    KNOWN = {"id", "type", "name", "formKey", "formMode", "formFields",
             "delegate", "decision", "decisionRef", "defaultTo", "calledKey",
             "calledElement", "inVars", "outVars", "in", "out", "message",
             "correlationVar", "terminate", "timers", "_default_flow"}
    for n in nodes:
        unknown = set(n) - KNOWN
        if unknown:
            print(f"WARNING: 节点 {n.get('id')} 有未识别键 {sorted(unknown)}（属性将被忽略）", file=sys.stderr)
    # 审批定义覆盖预检：userTask 节点漏配在本地就提醒（运行期发起闸 400）
    if spec.get("approvalDefs") is not None:
        missing = [n["id"] for n in nodes
                   if n.get("type") == "userTask" and n["id"] not in ad_nodes]
        if missing:
            print(f"WARNING: userTask 节点 {missing} 无审批定义（发起闸将拒绝发起，"
                  f"继承上级组织除外——本地无法校验组织树，请以 startable 预检为准）", file=sys.stderr)

    # —— 发射 XML ——
    L = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"',
         '                  xmlns:flowable="http://flowable.org/bpmn"',
         '                  xmlns:cmx="http://cmx.io/bpmn"',
         f'                  targetNamespace="http://cmx.io/flow/created"',
         f'                  id="defs_{esc(spec["key"])}">',
         f'  <bpmn:process id="{esc(spec["key"])}" name="{esc(spec.get("name") or spec["key"])}" isExecutable="true">']

    for n in nodes:
        t = n["type"]
        if t not in NODE_TYPES:
            hint = "（引擎黑名单，见 usage/02 §2.12）" if t in BLACKLIST else \
                "（引擎支持但本脚本不生成：用 callActivity 替代或手写 BPMN 后走 REST 部署）" if t == "subProcess" else ""
            raise SpecError(f"节点 {n['id']} 类型不支持: {t}{hint}")
        nid, name = esc(n["id"]), esc(n.get("name") or n["id"])
        if t == "startEvent":
            L.append(f'    <bpmn:startEvent id="{nid}" name="{name}"/>')
        elif t == "endEvent":
            if n.get("terminate"):
                L.append(f'    <bpmn:endEvent id="{nid}" name="{name}">')
                L.append('      <bpmn:terminateEventDefinition/>')
                L.append('    </bpmn:endEvent>')
            else:
                L.append(f'    <bpmn:endEvent id="{nid}" name="{name}"/>')
        elif t == "userTask":
            attrs = []
            if n.get("formKey"):
                attrs.append(f'cmx:formKey="{esc(n["formKey"])}"')
            if n.get("formMode"):
                attrs.append(f'cmx:formMode="{esc(n["formMode"])}"')
            if n.get("formFields"):
                attrs.append(f'cmx:formFields="{esc(n["formFields"])}"')
            a = (" " + " ".join(attrs)) if attrs else ""
            # P0：办理人/会签由审批定义编译期注入，spec 级 mi 已拒绝
            L.append(f'    <bpmn:userTask id="{nid}" name="{name}"{a}/>')
        elif t == "serviceTask":
            if not n.get("delegate"):
                raise SpecError(f"serviceTask {n['id']} 缺 delegate")
            L.append(f'    <bpmn:serviceTask id="{nid}" name="{name}"'
                     f' flowable:delegateExpression="${{{esc(n["delegate"])}}}"/>')
        elif t == "businessRuleTask":
            if not (n.get("decisionRef") or n.get("decision")):
                raise SpecError(f"businessRuleTask {n['id']} 缺 decisionRef")
            L.append(f'    <bpmn:businessRuleTask id="{nid}" name="{name}"'
                     f' flowable:decisionRef="{esc(n.get("decisionRef") or n.get("decision"))}"/>')
        elif t in ("exclusiveGateway", "parallelGateway", "inclusiveGateway"):
            d = f' default="{n["_default_flow"]}"' if n.get("_default_flow") else ""
            L.append(f'    <bpmn:{t} id="{nid}" name="{name}"{d}/>')
        elif t == "callActivity":
            attrs = []
            if n.get("calledKey"):
                attrs.append(f'cmx:calledKey="{esc(n["calledKey"])}"')
            if n.get("calledElement"):
                attrs.append(f'calledElement="{esc(n["calledElement"])}"')
            if not attrs:
                raise SpecError(f"callActivity {n['id']} 需要 calledKey 或 calledElement")
            if (n.get("inVars") and (n.get("in") is not None)) or (n.get("outVars") and (n.get("out") is not None)):
                raise SpecError(f"callActivity {n['id']}：inVars 与结构化 in 不可同给（引擎只用结构化，简写被忽略）")
            if n.get("inVars"):
                attrs.append(f'cmx:inVars="{esc(n["inVars"])}"')
            if n.get("outVars"):
                attrs.append(f'cmx:outVars="{esc(n["outVars"])}"')
            a = " " + " ".join(attrs)
            ins_outs = ""
            if n.get("in") or n.get("out"):
                ins_outs = "\n    <bpmn:extensionElements>"
                for i_ in n.get("in") or []:
                    ins_outs += f'\n      <flowable:in source="{esc(i_["source"])}" target="{esc(i_.get("target") or i_["source"])}"/>'
                for o_ in n.get("out") or []:
                    ins_outs += f'\n      <flowable:out source="{esc(o_["source"])}" target="{esc(o_.get("target") or o_["source"])}"/>'
                ins_outs += "\n    </bpmn:extensionElements>"
            L.append(f'    <bpmn:callActivity id="{nid}" name="{name}"{a}>{ins_outs}\n    </bpmn:callActivity>'
                     if ins_outs else f'    <bpmn:callActivity id="{nid}" name="{name}"{a}/>')
        elif t == "messageCatch":
            pre = ' cmx:correlationVar="{}"'.format(esc(n["correlationVar"])) if n.get("correlationVar") else ""
            L.append(f'    <bpmn:intermediateCatchEvent id="{nid}" name="{name}"{pre}>')
            L.append(f'      <bpmn:messageEventDefinition messageRef="{esc(n.get("message") or nid)}"/>')
            L.append('    </bpmn:intermediateCatchEvent>')

    # 边界定时器（挂在宿主 userTask 之后统一发射）
    for n in nodes:
        for k, t in enumerate(n.get("timers") or []):
            bid = f"{n['id']}_timer{k + 1}"
            _ca_raw = t.get("cancelActivity", True)
            _ca = _ca_raw if isinstance(_ca_raw, bool) else str(_ca_raw).strip().lower() not in ("false", "0", "no")
            cancel = "" if _ca else ' cancelActivity="false"'
            L.append(f'    <bpmn:boundaryEvent id="{bid}" attachedToRef="{esc(n["id"])}"{cancel}>')
            L.append(f'      <bpmn:timerEventDefinition><bpmn:timeDuration>{esc(t["duration"])}</bpmn:timeDuration></bpmn:timerEventDefinition>')
            L.append('    </bpmn:boundaryEvent>')

    for f in flows:
        attrs = f' id="{esc(f["_id"])}"'
        if f.get("name"):
            attrs += f' name="{esc(f["name"])}"'
        attrs += f' sourceRef="{esc(f["from"])}" targetRef="{esc(f["to"])}"'
        cond = f.get("condition")
        if cond:
            L.append(f'    <bpmn:sequenceFlow{attrs}>')
            L.append(f'      <bpmn:conditionExpression>{esc(cond)}</bpmn:conditionExpression>')
            L.append('    </bpmn:sequenceFlow>')
        else:
            L.append(f'    <bpmn:sequenceFlow{attrs}/>')

    # 定时器出边（timer.to）
    for n in nodes:
        for k, t in enumerate(n.get("timers") or []):
            bid = f"{n['id']}_timer{k + 1}"
            L.append(f'    <bpmn:sequenceFlow id="{bid}_out" sourceRef="{bid}" targetRef="{esc(t["to"])}"/>')

    L.append('  </bpmn:process>')
    L.append('</bpmn:definitions>')
    xml = "\n".join(L) + "\n"
    try:
        ET.fromstring(xml)  # 良构自检
    except ET.ParseError as e:
        raise SpecError(f"XML 良构失败（多为 id/name 含 & < > 引号）: {e}")
    return xml


# ———————————————————————————————————— REST 部署 / 冒烟 ————————————————————————————————————
def call(server, path, body, api_key=None):
    req = urllib.request.Request(
        server.rstrip("/") + "/api/flow/v1" + path,
        data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json",
                 **({"X-API-Key": api_key} if api_key else {})})
    return _open(req, path)


def get(server, path, api_key=None):
    req = urllib.request.Request(
        server.rstrip("/") + "/api/flow/v1" + path,
        headers={**({"X-API-Key": api_key} if api_key else {})})
    return _open(req, "GET " + path)


def _open(req, path):
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode()[:300]
        except Exception:
            pass
        raise SpecError(f"HTTP {e.code} {path}: {detail}")


def deploy(xml, spec, server, api_key):
    """五步部署链：validate → draft → publish → approval-defs/save → forms/save → startable 预检。"""
    key = spec["key"]
    # 1) validate（软失败必须看 data.valid）
    r = call(server, "/definitions/validate", {"bpmnXml": xml}, api_key)
    if r.get("code") != 0:
        raise SpecError(f"validate 信封异常: {r}")
    d = r.get("data") or {}
    if not d.get("valid"):
        raise SpecError(f"BPMN 校验失败: {d.get('error')}")
    print(f"[1/6] validate OK key={d.get('key')}")
    dp = (spec.get("deploy") or {})
    # 2) draft（key 由 BPMN process id 派生，服务端双编译对账）
    dr = call(server, "/definitions/draft", {
        "name": dp.get("name") or spec.get("name") or key, "bpmnXml": xml,
        "updatedBy": dp.get("publishedBy") or "agent",
        **{k: dp[k] for k in ("domain", "application", "module", "category") if dp.get(k)},
    }, api_key)
    if dr.get("code") != 0:
        raise SpecError(f"draft 失败: {dr}")
    print("[2/6] draft OK")
    # 3) publish（key 在 body；版本 +1 热装载）
    pr = call(server, "/definitions/publish", {
        "key": key,
        "note": dp.get("note") or "created by cmx-flow-toolkit",
        "publishedBy": dp.get("publishedBy") or "agent",
    }, api_key)
    if pr.get("code") != 0:
        raise SpecError(f"publish 失败: {pr}")
    pd = pr.get("data") or {}
    print(f"[3/6] publish OK version={pd.get('version')} hotLoaded={pd.get('hotLoaded')}")
    # 4) approval-defs/save（办理人真源；P0 起为必做——发起闸按 userTask 节点全量校验）
    ad = spec.get("approvalDefs")
    if ad:
        ar = call(server, "/approval-defs/save", {
            "defKey": key, "orgId": ad.get("orgId"),
            "content": {"nodes": ad.get("nodes") or {}},
            **({"note": ad["note"]} if ad.get("note") else {}),
        }, api_key)
        if ar.get("code") != 0:
            raise SpecError(f"approval-defs/save 失败: {ar}")
        print(f"[4/6] approval-defs/save OK orgId={ad.get('orgId')} nodes={sorted((ad.get('nodes') or {}).keys())}")
    else:
        print("[4/6] 无 approvalDefs（跳过）——若流程含 userTask 节点且该组织无历史审批定义，发起将被闸拒绝")
    # 5) forms/save（可选表单绑定；不写 formKey → 待办中心走通用办结 UI）
    for fb in spec.get("forms") or []:
        fr = call(server, "/forms/save", dict(fb), api_key)
        if fr.get("code") != 0:
            raise SpecError(f"forms/save 失败: {fr}")
        print(f"[5/6] forms/save OK formKey={fb.get('formKey')}")
    if not (spec.get("forms") or []):
        print("[5/6] 无 forms 绑定（跳过）")
    # 6) startable 发起预检（orgId 口径逐节点校验；漏配在此暴露而非运行期 400）
    if ad:
        sr = call(server, "/approval-defs/startable", {"defKey": key, "orgId": ad.get("orgId")}, api_key)
        if sr.get("code") != 0:
            raise SpecError(f"startable 预检失败: {sr}")
        bad = [x for x in (sr.get("data") or {}).get("nodes") or [] if not x.get("ok")]
        if bad:
            raise SpecError(f"startable 预检不通过（以下节点解析不出办理人）: {bad}")
        print("[6/6] startable 预检 OK（全部 userTask 节点可解析办理人）")
    return pd.get("version")


def smoke(spec, server, api_key):
    sm = spec.get("smoke") or {}
    r = call(server, "/instances/start", {
        "definitionKey": spec["key"], "orgId": sm.get("orgId"),
        "businessKey": sm.get("businessKey") or f"SMOKE-{spec['key']}",
        "variables": sm.get("variables") or {},
    }, api_key)
    if r.get("code") != 0:
        raise SpecError(f"发起失败（发起闸/审批定义缺失会在此 400）: {r}")
    d = r.get("data") or {}
    iid = d.get("id")
    active = d.get("activeNodes") or []
    expect = sm.get("expectActive")
    if expect is not None:
        got = sorted(active)
        want = sorted(expect)
        if got != want:
            raise SpecError(f"冒烟断言失败: activeNodes={got} 期望={want}")
    open_ = [(t.get("nodeBpmnId"), t.get("assignee")) for t in d.get("openTasks") or []]
    print(f"smoke OK instance={iid} activeNodes={active} openTasks={open_}")
    if sm.get("cancel"):
        c = call(server, "/instances/cancel", {"id": iid, "reason": "smoke cleanup"}, api_key)
        print(f"cancel -> code={c.get('code')}")
    return iid


def main():
    ap = argparse.ArgumentParser(
        description="cmx-flowengine 流程定义创建器（spec JSON → BPMN → 五步部署/冒烟；P0：定义×审批定义分离）")
    ap.add_argument("--spec", required=True, help="spec JSON 路径")
    ap.add_argument("--out", help="输出 BPMN 路径（缺省 <key>.bpmn，写到 spec 同目录）")
    ap.add_argument("--deploy", action="store_true",
                    help="部署（validate→draft→publish→approval-defs/save→forms/save→startable 预检）")
    ap.add_argument("--smoke", action="store_true", help="起冒烟实例并断言 activeNodes")
    ap.add_argument("--server", help="覆盖 spec.deploy.server")
    ap.add_argument("--api-key", help="覆盖 spec.deploy.apiKey")
    args = ap.parse_args()

    with open(args.spec, encoding="utf-8") as f:
        spec = json.load(f)
    if not spec.get("key"):
        sys.exit("spec 缺 key")
    xml = build_bpmn(spec)
    out = args.out or os.path.join(os.path.dirname(os.path.abspath(args.spec)), f"{spec['key']}.bpmn")
    with open(out, "w", encoding="utf-8") as f:
        f.write(xml)
    print(f"BPMN written: {out} ({len(xml)} B)")

    server = args.server or (spec.get("deploy") or {}).get("server")
    api_key = args.api_key or (spec.get("deploy") or {}).get("apiKey")
    if (args.deploy or args.smoke) and not server:
        sys.exit("需要 --server 或 spec.deploy.server")
    if args.deploy:
        deploy(xml, spec, server, api_key)
    if args.smoke:
        if not args.deploy:
            r = call(server, "/definitions/detail", {"key": spec["key"]}, api_key)
            if r.get("code") != 0:
                raise SpecError(f"定义 {spec['key']} 未部署且未加 --deploy: {r.get('msg')}")
        smoke(spec, server, api_key)


if __name__ == "__main__":
    try:
        main()
    except SpecError as e:
        sys.exit(f"SPEC ERROR: {e}")
