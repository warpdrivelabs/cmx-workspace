#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cmx-flowengine 流程测试数据重建器（通用版）
============================================

作用：把「真机测试留下的 REST 流水（transcript.log）+ BPMN 定义 + 身份种子/绑定清单」
重放成一份可在空库直接执行的 PostgreSQL 数据文件（含幂等 DDL + 全量 INSERT）。

数据源（详见技能 SKILL.md）：
  1. transcript 日志：形如 docs/full-test/logs/transcript.log，
     块格式 `### METHOD /path` + `REQ {json}` + `RESP {json}`（完整实例视图落在 RESP.data）。
  2. BPMN 定义目录：docs/biz-test、docs/full-test/defs[...]（文件即定义，XML 原样入库）。
  3. manifest JSON：身份库静态数据（组织/用户/角色/岗位/关系/子流程绑定/表单绑定/
     定义版本覆盖）——由人工按测试报告整理。
  4. handcrafted Python 模块（可选）：无流水留存的测试轮（只有报告快照），
     暴露 build() -> list[rows]，行结构与脚本内部一致（见 examples/biztest_handcrafted.py）。

保真度（SQL 文件头会自动声明）：
  真实值：实例/任务/抄送 id、状态、businessKey、办理人、候选人、变量、
          台账 kind/from/to/reason/createdAt、任务 createdAt（自 /tasks/my、/cc、
          /todos/initiated 响应收割）。
  确定性重建值：令牌 id（视图不含；uuid5 稳定生成；开放任务与令牌严格挂接，
          已办任务 token_id 悬挂——与引擎「快照全删重插」后的真实行为一致）、
          updated_at / completed_at / HI 时长 / 意见 created_at（等间隔合成）。

用法示例（重现 20260816 两测试数据文件）：
  python3 rebuild_flow_testdata.py \
    --repo <cmx-flowengine 绝对路径> \
    --transcript docs/full-test/logs/transcript.log \
    --transcript docs/full-test/logs/sub-transcript.log \
    --def-dir docs/biz-test --def-dir docs/full-test/defs --def-dir docs/full-test/defs/subflow \
    --manifest examples/manifest-20260816.json \
    --handcrafted examples/biztest_handcrafted.py \
    --iam-db cmxlocal --flow-db cmx_fico \
    --base-ts 2026-08-16T04:45:00+00:00 \
    --out flow-test-data-20260816.sql

依赖：Python 3.10+ 标准库。输出校验：psql -v ON_ERROR_STOP=1 -f <out> 于空库须零错误。
"""
import argparse
import importlib.util
import json
import os
import re
import sys
import uuid
from collections import OrderedDict
from datetime import datetime, timedelta, timezone

UUID_NS = uuid.UUID("6d5f9c2e-1111-4a2d-9b3f-5f1e87a2b0d1")  # 重建命名空间（勿改，保证 id 稳定）


def u5(*parts):
    return str(uuid.uuid5(UUID_NS, "#".join(str(p) for p in parts)))


# ———————————————————————————————————— 基础工具 ————————————————————————————————————
def parse_ts(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None


def fmt_ts(dt):
    if dt is None:
        return "NULL"
    s = dt.strftime("%Y-%m-%d %H:%M:%S.%f")
    off = dt.strftime("%z") or "+0000"
    return f"'{s}{off[:3]}:{off[3:]}'"


def ms(a, b):
    if not a or not b:
        return None
    return str(int((b - a).total_seconds() * 1000))


def q(v):
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def qj(v):
    if v is None:
        return "NULL"
    return "'" + json.dumps(v, ensure_ascii=False, separators=(",", ":")).replace("'", "''") + "'::jsonb"


def ins(table, cols, rows):
    return [f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(r)});" for r in rows]


# ———————————————————————————————————— transcript 解析 ————————————————————————————————————
def parse_transcript(path):
    """切出 [(method, path, req_json|None, resp_json|None)]。"""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    blocks = []
    unparsed = [0]
    for ch in re.split(r"^### ", text, flags=re.M)[1:]:
        lines = ch.splitlines()
        head = lines[0].strip()
        method, _, path = head.partition(" ")
        req = resp = None
        body_lines, in_req, seen_req = [], False, False
        for ln in lines[1:]:
            if ln.startswith("RESP "):
                try:
                    resp = json.loads(ln[5:].strip())
                except Exception:
                    resp = None
                    unparsed[0] += 1
                break
            if ln.startswith("REQ"):
                in_req, seen_req = True, True
                rest = ln[3:].strip()
                if rest:
                    body_lines.append(rest)
                continue
            if in_req:
                body_lines.append(ln)
        if seen_req and body_lines:
            try:
                req = json.loads("\n".join(body_lines))
            except Exception:
                req = None
                unparsed[0] += 1
        blocks.append((method, path.strip(), req, resp))
    return blocks, unparsed[0]


def is_view(d):
    return isinstance(d, dict) and "id" in d and "tokens" in d and "tasks" in d and "definitionKey" in d


class Replay:
    """按序重放全部流水，收割：实例视图序列、发布版本、意见、任务/实例/抄送真实时间戳。"""

    def __init__(self):
        self.inst = OrderedDict()   # iid -> {views:[{seq,v}], org, bk, defkey, first_seq}
        self.seq = 0
        self.task_created = {}      # task_id -> iso ts（GET /tasks/my、todos 等列表收割）
        self.inst_created = {}      # iid  -> iso ts（todos/initiated 的 inst-* 行）
        self.cc_rows = {}           # cc id -> row（GET /cc 列表收割；toUserId 从 user= 参数补）
        self.cc_read_at = {}        # cc id -> datetime（POST /cc/{id}/read）
        self.pubver = {}            # defkey -> 最大发布版本
        self.comments = []          # complete REQ 的意见留痕（真实 task_id）
        self.ops = []               # (iid, task_id, kind, req)

    def touch(self, iid, **kw):
        r = self.inst.setdefault(iid, {"views": [], "org": None, "bk": None, "defkey": None,
                                       "first_seq": self.seq})
        for k, v in kw.items():
            if k == "views":
                r["views"].append({"seq": self.seq, "v": v})
            elif v is not None:
                r[k] = v
        if not r["views"]:
            r["first_seq"] = self.seq
        return r

    def feed(self, method, path, req, resp):
        self.seq += 1
        data = (resp or {}).get("data") if isinstance(resp, dict) else None
        m = re.match(r"^/definitions/([^/]+)/publish$", path)
        if m and isinstance(data, dict) and "version" in data:
            self.pubver[m.group(1)] = max(self.pubver.get(m.group(1), 0), data["version"])
        # 列表端点收割真实时间戳
        if isinstance(data, dict) and isinstance(data.get("tasks"), list):
            for t in data["tasks"]:
                tid = t.get("taskId") or t.get("id")
                if tid and t.get("createdAt") and tid not in self.task_created:
                    self.task_created[tid] = t["createdAt"]
                iid = t.get("instanceId")
                if iid and t.get("createdAt") and str(tid).startswith("inst-"):
                    self.inst_created.setdefault(iid, t["createdAt"])
        if isinstance(data, dict) and isinstance(data.get("cc"), list):
            mu = re.search(r"[?&]user=([^&]+)", path)
            to_user = mu.group(1) if mu else None
            for c in data["cc"]:
                if c.get("id"):
                    c = dict(c)
                    c.setdefault("toUserId", to_user)
                    self.cc_rows[c["id"]] = c
        rm = re.match(r"^/cc/([^/]+)/read$", path)
        if method == "POST" and rm:
            self.cc_read_at[rm.group(1)] = True
        # 发起
        if method == "POST" and path == "/instances" and isinstance(req, dict) \
                and isinstance(data, dict) and data.get("id"):
            self.touch(data["id"], org=req.get("orgId"), bk=req.get("businessKey"),
                       defkey=req.get("definitionKey"))
            if is_view(data):
                self.touch(data["id"], views=data)
            return
        # 子实例视图（处理完继续走下方 is_view，防御未来 API 返回父视图+内嵌 children）
        if isinstance(data, dict) and isinstance(data.get("children"), list):
            for c in data["children"]:
                if is_view(c):
                    self.touch(c["id"], views=c, bk=c.get("businessKey"), defkey=c.get("definitionKey"))
        # 任意完整视图
        if is_view(data):
            self.touch(data["id"], views=data, bk=data.get("businessKey"), defkey=data.get("definitionKey"))
        # complete 意见（decision/comment/operator 任一非空才落库，对齐 handlers.rs）
        m = re.match(r"^/tasks/([^/]+)/complete$", path)
        if m and method == "POST" and isinstance(req, dict):
            if any(req.get(k) is not None for k in ("comment", "decision", "operator")):
                self.comments.append({
                    "instance_id": req.get("instanceId"), "task_id": m.group(1),
                    "decision": req.get("decision"), "comment": req.get("comment"),
                    "user_id": req.get("operator"), "seq": self.seq,
                })

    def finalize(self):
        # cc 已读时刻：无响应时间，用该行 createdAt + 60s
        for cid in list(self.cc_read_at):
            row = self.cc_rows.get(cid)
            c = parse_ts(row.get("createdAt")) if row else None
            if c:
                self.cc_read_at[cid] = c + timedelta(seconds=60)
            else:
                self.cc_read_at.pop(cid, None)


# ———————————————————————————————————— 令牌重放 ————————————————————————————————————
def _tok_key(node, state, idx):
    return (node, state, idx)


def replay_tokens(views):
    """对实例视图序列重放，返回 (最终令牌id列表, task->token 绑定, 每视图令牌id列表)。

    令牌 id 规则：视图不含令牌 id，按 (node,state,出现序) uuid5 稳定生成。
    携带判定用「相邻视图按 (node,state) 多重集贪心配对」：新视图某 (node,state)
    的令牌优先延续上一视图同组未认领令牌（FIFO），配不上才算新令牌——避免并行
    分支先后完成时令牌列表位移导致开放任务令牌孤儿（快照全删重插会移除已走令牌，
    下标不稳定，但 (node,state) 分组是稳定的）。
    """
    counter = {}
    replay_tokens._live = {}   # 每次调用重置（函数属性，避免跨实例串号）
    task_bind, per_view = {}, []

    def new_tid(v, base):
        counter[base] = counter.get(base, 0) + 1
        return u5("tok", v.get("id"), base[0], base[1], counter[base])

    for v in views:
        toks = v.get("tokens") or []
        # 按 (node,state) 分组（保序）
        groups = {}
        for t in toks:
            groups.setdefault((t.get("nodeBpmnId"), t.get("state")), []).append(t)
        # 上一视图存活令牌按 (node,state) 分组（保生成序）
        live_by_group = getattr(replay_tokens, "_live", {})
        newlive_by_group = {}
        ids_in_order = []
        for key, tl in groups.items():
            avail = list(live_by_group.get(key, []))
            assigned = []
            for _t in tl:
                if avail:
                    assigned.append(avail.pop(0))          # 延续旧令牌（FIFO）
                else:
                    assigned.append(new_tid(v, key))       # 新令牌
            newlive_by_group[key] = assigned
            ids_in_order.extend(assigned)
        replay_tokens._live = newlive_by_group
        live = newlive_by_group
        # 每视图令牌 id 按 toks 原顺序展开
        idx = {k: 0 for k in newlive_by_group}
        flat = []
        for t in toks:
            key = (t.get("nodeBpmnId"), t.get("state"))
            flat.append(newlive_by_group[key][idx[key]])
            idx[key] += 1
        per_view.append(flat)
        wait_nodes = {}
        for i, t in enumerate(toks):
            if t.get("state") == "WAITING":
                wait_nodes.setdefault(t.get("nodeBpmnId"), []).append((i, t))
        _ = flat
        node_task_idx = {}
        for task in v.get("tasks") or []:
            tid_ = task.get("id")
            if tid_ in task_bind:
                continue
            node = task.get("nodeBpmnId")
            j = node_task_idx.get(node, 0)
            node_task_idx[node] = j + 1
            cand = wait_nodes.get(node) or []
            if j < len(cand):
                i, t = cand[j]
                task_bind[tid_] = flat[i]
            else:
                task_bind[tid_] = u5("tokhist", v.get("id"), node, tid_)
    return (per_view[-1] if per_view else []), task_bind, per_view


# ———————————————————————————————————— BPMN 定义解析 ————————————————————————————————————
def parse_bpmn(path):
    with open(path, encoding="utf-8") as f:
        xml = f.read()
    pid = re.search(r'bpmn:process id="([^"]+)"', xml)
    pname = re.search(r'bpmn:process id="[^"]+" name="([^"]*)"', xml)
    calls = {}
    for m in re.finditer(r'<bpmn:callActivity id="([^"]+)"[^>]*cmx:calledKey="([^"]+)"', xml):
        calls[m.group(1)] = m.group(2)
    for m in re.finditer(r'cmx:calledKey="([^"]+)"[^>]*id="([^"]+)"', xml):
        calls.setdefault(m.group(2), m.group(1))
    mis = {}
    for m in re.finditer(r'<bpmn:userTask id="([^"]+)"[^>]*>(.*?)</bpmn:userTask>', xml, re.S):
        node, body = m.group(1), m.group(2)
        mi = re.search(r"<bpmn:multiInstanceLoopCharacteristics([^>]*)>(.*?)</bpmn:multiInstanceLoopCharacteristics>",
                       body, re.S)
        if mi is None:
            # 自闭合写法 <multiInstanceLoopCharacteristics isSequential="true" .../>
            mi2 = re.search(r"<bpmn:multiInstanceLoopCharacteristics([^/>]*)/>", body)
            if mi2:
                class _M:
                    def __init__(self, g1, g2):
                        self.g1, self.g2 = g1, g2
                    def group(self, i):
                        return [None, self.g1, self.g2][i]
                mi = _M(mi2.group(1), "")
        if mi:
            attrs, mi_body = mi.group(1), mi.group(2)

            def attr(name):
                a = re.search(name + r'="([^"]+)"', attrs)
                return a.group(1) if a else None

            cond = re.search(r"<bpmn:completionCondition>(.*?)</bpmn:completionCondition>", mi_body, re.S)
            coll = attr("flowable:collection")
            if coll:
                coll = coll.strip().lstrip("${").rstrip("}")   # 兼容 ${var} 包裹写法
            mis[node] = {
                "sequential": (attr("isSequential") or "false").lower() == "true",
                "collection": coll,
                "element_var": attr("flowable:elementVariable"),
                "condition": cond.group(1).strip() if cond else None,
            }
    return {"key": pid.group(1) if pid else None,
            "name": (pname.group(1) if pname else None) or (pid.group(1) if pid else None),
            "xml": xml, "calls": calls, "mi": mis}


def load_defs(def_dirs):
    defs = {}
    for d in def_dirs:
        if not os.path.isdir(d):
            sys.exit(f"定义目录不存在: {d}")
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".bpmn"):
                info = parse_bpmn(os.path.join(d, fn))
                if info["key"]:
                    if info["key"] in defs:
                        print(f"WARNING: 定义 key 重复，后者覆盖前者：{info['key']} "
                              f"({defs[info['key']]['_file']} -> {os.path.join(d, fn)})", file=sys.stderr)
                    info["_file"] = os.path.join(d, fn)
                    defs[info["key"]] = info
    return defs


# ———————————————————————————————————— 实例行构建 ————————————————————————————————————
def build_rows(R, defs, called_targets, iid, base):
    """构建一个流水实例的全部行。返回 dict(instance/tokens/tasks/candidates/mi/cc/delegations/comments)。"""
    r = R.inst[iid]
    views = r["views"]
    fin = views[-1]["v"]
    defkey = fin["definitionKey"]
    inst_c = parse_ts(R.inst_created.get(iid))
    tcs = [parse_ts(R.task_created[t["id"]]) for t in fin.get("tasks") or []
           if R.task_created.get(t["id"])]
    tcs = sorted([t for t in tcs if t])
    if inst_c is None:
        inst_c = tcs[0] - timedelta(seconds=10) if tcs else base
    view_list = [w["v"] for w in views]
    final_tids, task_bind, _ = replay_tokens(view_list)

    dg = fin.get("delegations") or []
    dts = [t for t in (parse_ts(d.get("createdAt")) for d in dg) if t]
    state = fin["state"]
    ended = None
    if state in ("COMPLETED", "TERMINATED"):
        cand = list(tcs) + dts
        ended = (max(cand) + timedelta(seconds=8)) if cand else inst_c + timedelta(seconds=300)
    updated = ended or (max(tcs + dts) if (tcs or dts) else inst_c + timedelta(seconds=30))

    # 父子挂载点：子实例首次出现前父实例最新视图里的 WAITING_SUBFLOW 令牌，
    # 用父定义 callActivity 的 calledKey→绑定目标 defkey 匹配；无法区分时取第一个。
    parent_iid = fin.get("parentInstanceId")
    p_tok = p_node = None
    if parent_iid and parent_iid in R.inst:
        pv = R.inst[parent_iid]["views"]
        prev = [w for w in pv if w["seq"] <= r["first_seq"]] or pv
        target = prev[-1]
        p_views = [w["v"] for w in ([x for x in pv if x["seq"] <= target["seq"]] or pv)]
        _, _, p_tids = replay_tokens(p_views)
        tview = target["v"]
        wtokens = [(i, t) for i, t in enumerate(tview.get("tokens") or [])
                   if t.get("state") == "WAITING_SUBFLOW"]
        chosen = None
        if wtokens:
            calls = (defs.get(tview.get("definitionKey")) or {}).get("calls") or {}
            for i, t in wtokens:
                key = calls.get(t.get("nodeBpmnId"))
                if key and defkey in called_targets.get(key, {defkey}):
                    chosen = (i, t)
                    break
            if chosen is None:
                chosen = wtokens[0]
        if chosen:
            i, t = chosen
            toks = p_tids[len(p_views) - 1] if p_tids else []
            p_tok = toks[i] if i < len(toks) else u5("tokhist", parent_iid, t.get("nodeBpmnId"), iid)
            p_node = t.get("nodeBpmnId")

    org = r["org"] or (R.inst.get(parent_iid, {}).get("org") if parent_iid else None)
    rows = {"instance": {
        "id": iid, "definition_key": defkey, "business_key": fin.get("businessKey"),
        "state": state, "variables": fin.get("variables") or {},
        "created_at": inst_c, "updated_at": updated, "ended_at": ended,
        "org_id": org, "parent_instance_id": parent_iid,
        "parent_token_id": p_tok, "parent_node_bpmn_id": p_node,
    }, "tokens": [], "tasks": [], "candidates": [], "mi": [], "cc": [], "delegations": [], "comments": []}

    ftoks = fin.get("tokens") or []
    for i, t in enumerate(ftoks):
        rows["tokens"].append({
            "id": final_tids[i] if i < len(final_tids) else u5("tok", iid, t.get("nodeBpmnId"), i),
            "instance_id": iid, "node_bpmn_id": t.get("nodeBpmnId"), "state": t.get("state"),
            "parent_id": None, "created_at": inst_c, "updated_at": updated,
        })

    tasks = fin.get("tasks") or []
    for k, t in enumerate(tasks):
        tid = t["id"]
        tc = parse_ts(R.task_created.get(tid)) or (inst_c + timedelta(seconds=20 * (k + 1)))
        done = bool(t.get("completed"))
        rows["tasks"].append({
            "id": tid, "instance_id": iid,
            "token_id": task_bind.get(tid) or u5("tokhist", iid, t.get("nodeBpmnId"), tid),
            "node_bpmn_id": t.get("nodeBpmnId"), "name": t.get("name"),
            "assignee": t.get("assignee"), "candidate_groups": None,
            "element_value": t.get("elementValue"), "owner_user_id": t.get("ownerUserId"),
            "parent_task_id": t.get("parentTaskId"), "delegation_state": t.get("delegationState"),
            "completed": done, "created_at": tc,
            "completed_at": (tc + timedelta(seconds=45 + (k * 7 % 40))) if done else None,
        })
        for j, c in enumerate(t.get("candidates") or []):
            rows["candidates"].append({
                "id": u5("cand", tid, c.get("userId"), j), "task_id": tid, "instance_id": iid,
                "candidate_type": c.get("type"), "candidate_ref": c.get("ref"),
                "resolved_user_id": c.get("userId"),
            })

    d = defs.get(defkey) or {}
    for node, mi in (d.get("mi") or {}).items():
        ntasks = [t for t in tasks if t.get("nodeBpmnId") == node]
        if not ntasks:
            continue
        coll = (fin.get("variables") or {}).get(mi.get("collection") or "")
        total = len(coll) if isinstance(coll, list) else len(ntasks)
        done_n = sum(1 for t in ntasks if t.get("completed"))
        open_n = sum(1 for t in ntasks if not t.get("completed"))
        rows["mi"].append({
            "id": u5("mi", iid, node), "instance_id": iid, "node_bpmn_id": node,
            "sequential": mi.get("sequential", False), "total": total, "completed": done_n,
            "next_index": done_n if mi.get("sequential") else total,
            "collection": coll if isinstance(coll, list) else [],
            "element_var": mi.get("element_var"),
            "completion_condition": mi.get("condition"),
            "finished": (open_n == 0) or (state in ("COMPLETED", "TERMINATED")),
        })

    # 抄送：GET /cc 真实行优先（含真实 id/createdAt），视图 ccRecords 兜底（按 节点+人 去重）
    harvested = set()
    for cid, c in R.cc_rows.items():
        if c.get("instanceId") == iid:
            harvested.add((c.get("nodeBpmnId"), c.get("toUserId")))
            rows["cc"].append({
                "id": cid, "instance_id": iid, "node_bpmn_id": c.get("nodeBpmnId"),
                "to_user_id": c.get("toUserId"), "from_user_id": _node_assignee(fin, c.get("nodeBpmnId")),
                "reason": c.get("reason"), "read_at": R.cc_read_at.get(cid) if c.get("read") else None,
                "created_at": parse_ts(c.get("createdAt")) or updated,
            })
    for k, c in enumerate(fin.get("ccRecords") or []):
        if (c.get("nodeBpmnId"), c.get("toUserId")) in harvested:
            continue
        rows["cc"].append({
            "id": u5("cc", iid, c.get("nodeBpmnId"), c.get("toUserId"), k),
            "instance_id": iid, "node_bpmn_id": c.get("nodeBpmnId"),
            "to_user_id": c.get("toUserId"), "from_user_id": _node_assignee(fin, c.get("nodeBpmnId")),
            "reason": None, "read_at": updated + timedelta(seconds=90) if c.get("read") else None,
            "created_at": updated - timedelta(seconds=120),
        })

    # 台账：真实 createdAt；task_id 由 from_user/目标启发式绑定，绑不上用实例首个任务兜底
    # （NOT NULL 约束；kind 覆盖 REJECT/WITHDRAW/TRANSFER/DELEGATE/ADDSIGN_*/JUMP/URGE）
    fallback_task = (tasks[0].get("id") if tasks else None) or u5("delegtask", iid, iid)
    seen_keys = set()
    for dgk, dgel in enumerate(dg):
        tid = _bind_delegation_task(r["views"], dgel)
        if tid is None and tasks:
            # 顺序兜底：同一实例多条台账按 from_user 依次找未用过的任务
            for t in tasks:
                if t.get("assignee") == dgel.get("fromUserId"):
                    tid = t["id"]
                    break
        rows["delegations"].append({
            "id": u5("deleg", iid, dgel.get("createdAt"), dgk),
            "task_id": tid or fallback_task, "instance_id": iid, "kind": dgel.get("kind"),
            "from_user_id": dgel.get("fromUserId"), "to_user_id": dgel.get("toUserId"),
            "temp_task_id": _temp_task(fin, tid), "reason": dgel.get("reason"),
            "created_at": parse_ts(dgel.get("createdAt")) or updated,
        })

    # 意见：REQ 真实文本；node 取任务节点；时间取该任务办结时刻（合成）
    node_of = {}
    for w in views:
        for t in w["v"].get("tasks") or []:
            node_of[t["id"]] = t.get("nodeBpmnId")
    trow = {t["id"]: t for t in rows["tasks"]}
    tdone = {t["id"]: t["completed_at"] for t in rows["tasks"]}
    for c in R.comments:
        if c["instance_id"] != iid or (iid, c["task_id"], c["seq"]) in seen_keys:
            continue
        seen_keys.add((iid, c["task_id"], c["seq"]))
        rows["comments"].append({
            "id": u5("cmt", iid, c["task_id"], c["seq"]),
            "instance_id": iid, "task_id": c["task_id"],
            "node_bpmn_id": node_of.get(c["task_id"]),
            "user_id": c["user_id"] or (trow.get(c["task_id"]) or {}).get("assignee"),
            "decision": c["decision"], "comment": c["comment"],
            "created_at": tdone.get(c["task_id"]) or (updated - timedelta(seconds=30)),
        })
    # 开放任务令牌重绑：终视图里同节点开放任务按序 ↔ 同节点 WAITING 令牌按序，
    # 保证「开放任务 token_id ∈ 该实例最终令牌集合」的不变量（重放绑定可能指到历史令牌）。
    tview_toks = fin.get("tokens") or []
    wait_by_node = {}
    for ti, tk in enumerate(tview_toks):
        if tk.get("state") == "WAITING":
            wait_by_node.setdefault(tk.get("nodeBpmnId"), []).append(final_tids[ti])
    open_idx = {}
    for t in rows["tasks"]:
        if t["completed"]:
            continue
        node = t["node_bpmn_id"]
        j = open_idx.get(node, 0)
        open_idx[node] = j + 1
        toks_at = wait_by_node.get(node) or []
        if j < len(toks_at):
            t["token_id"] = toks_at[j]
    return rows


def _node_assignee(view, node):
    for t in view.get("tasks") or []:
        if t.get("nodeBpmnId") == node:
            return t.get("assignee")
    return None


def _bind_delegation_task(views, dgel):
    """启发式：kind=REJECT → from_user 的任务；WITHDRAW → 终视图首个开放任务；
    转签族 → from_user 未办任务。返回 task_id 或 None。"""
    kind = dgel.get("kind")
    fin = views[-1]["v"]
    if kind == "REJECT":
        for w in views:
            for t in w["v"].get("tasks") or []:
                if t.get("assignee") == dgel.get("fromUserId"):
                    return t["id"]
    if kind == "WITHDRAW":
        for t in fin.get("openTasks") or []:
            return t["id"]
    if kind in ("TRANSFER", "DELEGATE", "ADDSIGN_BEFORE", "ADDSIGN_AFTER"):
        for w in views:
            for t in w["v"].get("tasks") or []:
                if t.get("assignee") == dgel.get("fromUserId") and not t.get("completed"):
                    return t["id"]
    return None


def _temp_task(view, task_id):
    if not task_id:
        return None
    for t in view.get("tasks") or []:
        if t.get("parentTaskId") == task_id and t.get("delegationState") == "ADDSIGN":
            return t["id"]
    return None


def validate_rows(rows):
    """行结构校验（手建模块产物同样走这里）。"""
    i = rows["instance"]
    assert i["state"] in ("ACTIVE", "COMPLETED", "TERMINATED", "SUSPENDED"), f"state 非法: {i}"
    must = {"instance", "tokens", "tasks", "candidates", "mi", "cc", "delegations", "comments"}
    assert must <= set(rows), f"缺区段: {must - set(rows)}"
    for t in rows["tasks"]:
        assert t.get("token_id") and t.get("node_bpmn_id"), f"任务缺 token_id/node: {t.get('id')}"
        assert t.get("created_at"), f"任务缺 created_at: {t.get('id')}"
        if t.get("completed"):
            assert t.get("completed_at"), f"已办任务缺 completed_at: {t.get('id')}"
    for d in rows["delegations"]:
        assert d.get("task_id") and d.get("created_at"), f"台账缺 task_id/created_at: {d}"
    for c in rows["cc"]:
        assert c.get("to_user_id") and c.get("created_at"), f"抄送缺 to_user_id/created_at: {c}"
    for c in rows["comments"]:
        assert c.get("task_id") and c.get("created_at"), f"意见缺 task_id/created_at: {c}"
    for t in rows["tokens"]:
        assert t.get("created_at") and t.get("updated_at"), f"令牌缺时间: {t}"
    assert i["created_at"] and i["updated_at"], "实例缺 created_at/updated_at"
    if i["state"] in ("COMPLETED", "TERMINATED"):
        assert i["ended_at"], "终态实例缺 ended_at"


# ———————————————————————————————————— DDL（与引擎 crates 自举一致，幂等）————————————————————————————
# 同步源：cmx-flow-store-pg/src/ddl.rs、cmx-flow-def/src/store.rs、cmx-flow-app/src/biz_link.rs。
# 引擎表结构演进后需先对账再更新此处（见 SKILL.md「DDL 对账」）。
DDL_IAM = r"""
-- 对齐平台真源（列超集；时间列为 TIMESTAMP 无时区，与平台一致）：
--   backend/cmx-container/docs/sql/migrations/20260615_002_iam_tables.up.sql（user/role/user_role）
--   backend/cmx-container/docs/sql/migrations/20260720_001_cmx_flow_engine.up.sql（org/position/user_position/subflow_binding）
CREATE TABLE IF NOT EXISTS cmx_user (
    id            VARCHAR(64)  NOT NULL,
    username      VARCHAR(100) NOT NULL,
    password_hash VARCHAR(500),
    nickname      VARCHAR(100),
    email         VARCHAR(200),
    phone         VARCHAR(50),
    avatar        VARCHAR(500),
    org_id        VARCHAR(64),
    gender        INT4      DEFAULT 0,
    status        INT4      DEFAULT 1,
    last_login_at TIMESTAMP,
    last_login_ip VARCHAR(50),
    description   VARCHAR(500),
    archived      INT4      DEFAULT 0,
    create_time   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    update_time   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    create_by     VARCHAR(100),
    create_name   VARCHAR(100),
    update_by     VARCHAR(100),
    update_name   VARCHAR(100),
    PRIMARY KEY (id)
);
CREATE UNIQUE INDEX IF NOT EXISTS uk_cmx_user_username ON cmx_user (username);
CREATE UNIQUE INDEX IF NOT EXISTS uk_cmx_user_email ON cmx_user (email) WHERE email IS NOT NULL;
CREATE TABLE IF NOT EXISTS cmx_role (
    id            VARCHAR(64)  NOT NULL,
    code          VARCHAR(100) NOT NULL,
    name          VARCHAR(100) NOT NULL,
    role_group_id VARCHAR(64),
    data_scope    INT4      DEFAULT 1,
    sort_order    INT4      DEFAULT 0,
    description   VARCHAR(500),
    status        INT4      DEFAULT 1,
    archived      INT4      DEFAULT 0,
    create_time   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    update_time   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
);
CREATE TABLE IF NOT EXISTS cmx_user_role (
    id          VARCHAR(64) NOT NULL,
    user_id     VARCHAR(64) NOT NULL,
    role_id     VARCHAR(64) NOT NULL,
    archived    INT4      DEFAULT 0,
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
);
CREATE TABLE IF NOT EXISTS cmx_org (
    id             VARCHAR(64)  NOT NULL,
    code           VARCHAR(100) NOT NULL,
    name           VARCHAR(100) NOT NULL,
    parent_id      VARCHAR(64),
    path           VARCHAR(500),
    leader_user_id VARCHAR(64),
    sort_order     INT4      DEFAULT 0,
    status         INT4      DEFAULT 1,
    archived       INT4      DEFAULT 0,
    create_time    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    update_time    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
);
CREATE UNIQUE INDEX IF NOT EXISTS uk_cmx_org_code ON cmx_org (code) WHERE archived = 0;
CREATE INDEX IF NOT EXISTS idx_cmx_org_parent ON cmx_org (parent_id);
CREATE TABLE IF NOT EXISTS cmx_position (
    id          VARCHAR(64)  NOT NULL,
    code        VARCHAR(100) NOT NULL,
    name        VARCHAR(100) NOT NULL,
    org_id      VARCHAR(64),
    level       INT4      DEFAULT 0,
    sort_order  INT4      DEFAULT 0,
    status      INT4      DEFAULT 1,
    archived    INT4      DEFAULT 0,
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
);
CREATE UNIQUE INDEX IF NOT EXISTS uk_cmx_position_code ON cmx_position (code) WHERE archived = 0;
CREATE INDEX IF NOT EXISTS idx_cmx_position_org ON cmx_position (org_id);
CREATE TABLE IF NOT EXISTS cmx_user_position (
    id          VARCHAR(64) NOT NULL,
    user_id     VARCHAR(64) NOT NULL,
    position_id VARCHAR(64) NOT NULL,
    is_primary  BOOLEAN   DEFAULT FALSE,
    archived    INT4      DEFAULT 0,
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
);
CREATE INDEX IF NOT EXISTS idx_cmx_user_position_user ON cmx_user_position (user_id);
CREATE INDEX IF NOT EXISTS idx_cmx_user_position_pos  ON cmx_user_position (position_id);
CREATE TABLE IF NOT EXISTS cmx_flow_subflow_binding (
    id                    VARCHAR(64)  PRIMARY KEY,
    called_key            VARCHAR(128) NOT NULL,
    org_id                VARCHAR(64),
    target_definition_key VARCHAR(128) NOT NULL,
    enabled               BOOLEAN      NOT NULL DEFAULT TRUE,
    remark                VARCHAR(500),
    created_at            TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_cmx_flow_subflow_binding_key ON cmx_flow_subflow_binding (called_key);
CREATE INDEX IF NOT EXISTS idx_cmx_flow_subflow_binding_org ON cmx_flow_subflow_binding (org_id);
"""

DDL_FLOW = r"""
CREATE TABLE IF NOT EXISTS cmx_flow_instance (
    id                  VARCHAR(64)  PRIMARY KEY,
    definition_key      VARCHAR(128) NOT NULL,
    business_key        VARCHAR(128),
    state               VARCHAR(16)  NOT NULL,
    variables           JSONB        NOT NULL DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ  NOT NULL,
    updated_at          TIMESTAMPTZ  NOT NULL,
    ended_at            TIMESTAMPTZ,
    org_id              VARCHAR(64),
    parent_instance_id  VARCHAR(64),
    parent_token_id     VARCHAR(64),
    parent_node_bpmn_id VARCHAR(128)
);
ALTER TABLE cmx_flow_instance ADD COLUMN IF NOT EXISTS org_id VARCHAR(64);
ALTER TABLE cmx_flow_instance ADD COLUMN IF NOT EXISTS parent_instance_id VARCHAR(64);
ALTER TABLE cmx_flow_instance ADD COLUMN IF NOT EXISTS parent_token_id VARCHAR(64);
ALTER TABLE cmx_flow_instance ADD COLUMN IF NOT EXISTS parent_node_bpmn_id VARCHAR(128);
CREATE INDEX IF NOT EXISTS idx_cmx_flow_instance_defkey ON cmx_flow_instance (definition_key);
CREATE INDEX IF NOT EXISTS idx_cmx_flow_instance_bizkey ON cmx_flow_instance (business_key);
CREATE INDEX IF NOT EXISTS idx_cmx_flow_instance_state ON cmx_flow_instance (state);
CREATE INDEX IF NOT EXISTS idx_cmx_flow_instance_parent ON cmx_flow_instance (parent_instance_id);
CREATE TABLE IF NOT EXISTS cmx_flow_token (
    id           VARCHAR(64)  PRIMARY KEY,
    instance_id  VARCHAR(64)  NOT NULL,
    node_bpmn_id VARCHAR(128) NOT NULL,
    state        VARCHAR(16)  NOT NULL,
    parent_id    VARCHAR(64),
    created_at   TIMESTAMPTZ  NOT NULL,
    updated_at   TIMESTAMPTZ  NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cmx_flow_token_instance ON cmx_flow_token (instance_id);
CREATE TABLE IF NOT EXISTS cmx_flow_task (
    id               VARCHAR(64)  PRIMARY KEY,
    instance_id      VARCHAR(64)  NOT NULL,
    token_id         VARCHAR(64)  NOT NULL,
    node_bpmn_id     VARCHAR(128) NOT NULL,
    name             VARCHAR(255),
    assignee         VARCHAR(128),
    candidate_groups VARCHAR(512),
    element_value    JSONB,
    owner_user_id    VARCHAR(64),
    parent_task_id   VARCHAR(64),
    delegation_state VARCHAR(16),
    completed        BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at       TIMESTAMPTZ  NOT NULL,
    completed_at     TIMESTAMPTZ
);
ALTER TABLE cmx_flow_task ADD COLUMN IF NOT EXISTS element_value JSONB;
ALTER TABLE cmx_flow_task ADD COLUMN IF NOT EXISTS owner_user_id VARCHAR(64);
ALTER TABLE cmx_flow_task ADD COLUMN IF NOT EXISTS parent_task_id VARCHAR(64);
ALTER TABLE cmx_flow_task ADD COLUMN IF NOT EXISTS delegation_state VARCHAR(16);
CREATE INDEX IF NOT EXISTS idx_cmx_flow_task_instance ON cmx_flow_task (instance_id);
CREATE INDEX IF NOT EXISTS idx_cmx_flow_task_assignee ON cmx_flow_task (assignee);
CREATE INDEX IF NOT EXISTS idx_cmx_flow_task_open ON cmx_flow_task (assignee, completed);
CREATE TABLE IF NOT EXISTS cmx_flow_mi_scope (
    id                   VARCHAR(64)  PRIMARY KEY,
    instance_id          VARCHAR(64)  NOT NULL,
    node_bpmn_id         VARCHAR(128) NOT NULL,
    sequential           BOOLEAN      NOT NULL DEFAULT FALSE,
    total                INTEGER      NOT NULL,
    completed            INTEGER      NOT NULL DEFAULT 0,
    next_index           INTEGER      NOT NULL DEFAULT 0,
    collection           JSONB        NOT NULL DEFAULT '[]'::jsonb,
    element_var          VARCHAR(128),
    completion_condition VARCHAR(512),
    finished             BOOLEAN      NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_cmx_flow_mi_scope_instance ON cmx_flow_mi_scope (instance_id);
CREATE TABLE IF NOT EXISTS cmx_flow_job (
    id               VARCHAR(64)  PRIMARY KEY,
    instance_id      VARCHAR(64)  NOT NULL,
    token_id         VARCHAR(64)  NOT NULL,
    boundary_bpmn_id VARCHAR(128) NOT NULL,
    cancel_activity  BOOLEAN      NOT NULL DEFAULT TRUE,
    due_at           TIMESTAMPTZ  NOT NULL,
    created_at       TIMESTAMPTZ  NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cmx_flow_job_instance ON cmx_flow_job (instance_id);
CREATE INDEX IF NOT EXISTS idx_cmx_flow_job_due ON cmx_flow_job (due_at);
CREATE TABLE IF NOT EXISTS cmx_flow_task_candidate (
    id               VARCHAR(64)  PRIMARY KEY,
    task_id          VARCHAR(64)  NOT NULL,
    instance_id      VARCHAR(64)  NOT NULL,
    candidate_type   VARCHAR(16)  NOT NULL,
    candidate_ref    VARCHAR(128) NOT NULL,
    resolved_user_id VARCHAR(64)  NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cmx_flow_task_candidate_instance ON cmx_flow_task_candidate (instance_id);
CREATE INDEX IF NOT EXISTS idx_cmx_flow_task_candidate_user ON cmx_flow_task_candidate (resolved_user_id);
CREATE INDEX IF NOT EXISTS idx_cmx_flow_task_candidate_task ON cmx_flow_task_candidate (task_id);
CREATE TABLE IF NOT EXISTS cmx_flow_cc (
    id           VARCHAR(64)  PRIMARY KEY,
    instance_id  VARCHAR(64)  NOT NULL,
    node_bpmn_id VARCHAR(128),
    to_user_id   VARCHAR(64)  NOT NULL,
    from_user_id VARCHAR(64),
    reason       VARCHAR(500),
    read_at      TIMESTAMPTZ,
    created_at   TIMESTAMPTZ  NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cmx_flow_cc_instance ON cmx_flow_cc (instance_id);
CREATE INDEX IF NOT EXISTS idx_cmx_flow_cc_to_user ON cmx_flow_cc (to_user_id, read_at);
CREATE TABLE IF NOT EXISTS cmx_flow_task_delegation (
    id           VARCHAR(64)  PRIMARY KEY,
    task_id      VARCHAR(64)  NOT NULL,
    instance_id  VARCHAR(64)  NOT NULL,
    kind         VARCHAR(20)  NOT NULL,
    from_user_id VARCHAR(64)  NOT NULL,
    to_user_id   VARCHAR(64)  NOT NULL,
    temp_task_id VARCHAR(64),
    reason       VARCHAR(500),
    created_at   TIMESTAMPTZ  NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cmx_flow_task_delegation_instance ON cmx_flow_task_delegation (instance_id);
CREATE INDEX IF NOT EXISTS idx_cmx_flow_task_delegation_task ON cmx_flow_task_delegation (task_id);
CREATE TABLE IF NOT EXISTS cmx_flow_hi_instance (
    id             VARCHAR(64)  PRIMARY KEY,
    definition_key VARCHAR(128) NOT NULL,
    business_key   VARCHAR(128),
    state          VARCHAR(16)  NOT NULL,
    variables      JSONB        NOT NULL DEFAULT '{}'::jsonb,
    created_at     TIMESTAMPTZ  NOT NULL,
    ended_at       TIMESTAMPTZ,
    duration_ms    BIGINT,
    archived_at    TIMESTAMPTZ  NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cmx_flow_hi_instance_defkey ON cmx_flow_hi_instance (definition_key);
CREATE INDEX IF NOT EXISTS idx_cmx_flow_hi_instance_bizkey ON cmx_flow_hi_instance (business_key);
CREATE TABLE IF NOT EXISTS cmx_flow_hi_task (
    id           VARCHAR(64)  PRIMARY KEY,
    instance_id  VARCHAR(64)  NOT NULL,
    node_bpmn_id VARCHAR(128) NOT NULL,
    name         VARCHAR(255),
    assignee     VARCHAR(128),
    created_at   TIMESTAMPTZ  NOT NULL,
    completed_at TIMESTAMPTZ,
    duration_ms  BIGINT,
    archived_at  TIMESTAMPTZ  NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cmx_flow_hi_task_instance ON cmx_flow_hi_task (instance_id);
CREATE INDEX IF NOT EXISTS idx_cmx_flow_hi_task_assignee ON cmx_flow_hi_task (assignee);
CREATE TABLE IF NOT EXISTS cmx_flow_definition (
    key            VARCHAR(128) PRIMARY KEY,
    name           VARCHAR(255) NOT NULL,
    domain         VARCHAR(64),
    application    VARCHAR(64),
    module         VARCHAR(64),
    category       VARCHAR(64),
    state          VARCHAR(16)  NOT NULL DEFAULT 'DRAFT',
    active_version INTEGER,
    draft_xml      TEXT,
    updated_at     TIMESTAMPTZ  NOT NULL,
    updated_by     VARCHAR(64)
);
ALTER TABLE cmx_flow_definition ADD COLUMN IF NOT EXISTS domain VARCHAR(64);
ALTER TABLE cmx_flow_definition ADD COLUMN IF NOT EXISTS application VARCHAR(64);
CREATE INDEX IF NOT EXISTS idx_cmx_flow_definition_module ON cmx_flow_definition (module);
CREATE INDEX IF NOT EXISTS idx_cmx_flow_definition_dam ON cmx_flow_definition (domain, application, module);
CREATE INDEX IF NOT EXISTS idx_cmx_flow_definition_state ON cmx_flow_definition (state);
CREATE TABLE IF NOT EXISTS cmx_flow_definition_version (
    id           VARCHAR(64)  PRIMARY KEY,
    def_key      VARCHAR(128) NOT NULL,
    version      INTEGER      NOT NULL,
    bpmn_xml     TEXT         NOT NULL,
    note         VARCHAR(512),
    published_at TIMESTAMPTZ  NOT NULL,
    published_by VARCHAR(64)
);
ALTER TABLE cmx_flow_definition_version ADD COLUMN IF NOT EXISTS note VARCHAR(512);
CREATE UNIQUE INDEX IF NOT EXISTS uq_cmx_flow_def_version ON cmx_flow_definition_version (def_key, version);
CREATE INDEX IF NOT EXISTS idx_cmx_flow_def_version_key ON cmx_flow_definition_version (def_key);
CREATE TABLE IF NOT EXISTS cmx_flow_biz_link (
    id           VARCHAR(64)  PRIMARY KEY,
    instance_id  VARCHAR(64)  NOT NULL,
    biz_table    VARCHAR(128) NOT NULL,
    biz_id       VARCHAR(128) NOT NULL,
    biz_key      VARCHAR(128),
    role         VARCHAR(32)  NOT NULL DEFAULT 'primary',
    created_at   TIMESTAMPTZ  NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cmx_flow_biz_link_instance ON cmx_flow_biz_link (instance_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_cmx_flow_biz_link_biz ON cmx_flow_biz_link (biz_table, biz_id, instance_id);
CREATE TABLE IF NOT EXISTS cmx_flow_task_comment (
    id           VARCHAR(64)  PRIMARY KEY,
    instance_id  VARCHAR(64)  NOT NULL,
    task_id      VARCHAR(64)  NOT NULL,
    node_bpmn_id VARCHAR(128),
    user_id      VARCHAR(64),
    decision     VARCHAR(32),
    comment      TEXT,
    created_at   TIMESTAMPTZ  NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cmx_flow_task_comment_instance ON cmx_flow_task_comment (instance_id);
CREATE TABLE IF NOT EXISTS cmx_flow_form_binding (
    form_key     VARCHAR(128) PRIMARY KEY,
    kind         VARCHAR(16)  NOT NULL DEFAULT 'native',
    native_page  VARCHAR(128),
    native_view  VARCHAR(64),
    html_page    VARCHAR(128),
    biz_table    VARCHAR(128),
    domain       VARCHAR(32),
    application  VARCHAR(32),
    module       VARCHAR(32),
    file         VARCHAR(128),
    pk_field     VARCHAR(64),
    title        VARCHAR(255),
    updated_at   TIMESTAMPTZ  NOT NULL
);
ALTER TABLE cmx_flow_form_binding ADD COLUMN IF NOT EXISTS native_view VARCHAR(64);
ALTER TABLE cmx_flow_form_binding ADD COLUMN IF NOT EXISTS file VARCHAR(128);
ALTER TABLE cmx_flow_form_binding ADD COLUMN IF NOT EXISTS pk_field VARCHAR(64);
ALTER TABLE cmx_flow_form_binding ADD COLUMN IF NOT EXISTS workspace_node VARCHAR(128);
"""


# ———————————————————————————————————— SQL 组装 ————————————————————————————————————
def emit_instance_block(rows, label):
    L = []
    i = rows["instance"]
    L.append(f"-- {label}: {i['definition_key']}  businessKey={i['business_key']}  state={i['state']}")
    L += ins("cmx_flow_instance",
             ["id", "definition_key", "business_key", "state", "variables", "created_at",
              "updated_at", "ended_at", "org_id", "parent_instance_id", "parent_token_id", "parent_node_bpmn_id"],
             [[q(i["id"]), q(i["definition_key"]), q(i["business_key"]), q(i["state"]), qj(i["variables"]),
               fmt_ts(i["created_at"]), fmt_ts(i["updated_at"]), fmt_ts(i["ended_at"]), q(i["org_id"]),
               q(i["parent_instance_id"]), q(i["parent_token_id"]), q(i["parent_node_bpmn_id"])]])
    for t in rows["tokens"]:
        L += ins("cmx_flow_token",
                 ["id", "instance_id", "node_bpmn_id", "state", "parent_id", "created_at", "updated_at"],
                 [[q(t["id"]), q(t["instance_id"]), q(t["node_bpmn_id"]), q(t["state"]), q(t["parent_id"]),
                   fmt_ts(t["created_at"]), fmt_ts(t["updated_at"])]])
    for t in rows["tasks"]:
        L += ins("cmx_flow_task",
                 ["id", "instance_id", "token_id", "node_bpmn_id", "name", "assignee", "candidate_groups",
                  "element_value", "owner_user_id", "parent_task_id", "delegation_state", "completed",
                  "created_at", "completed_at"],
                 [[q(t["id"]), q(t["instance_id"]), q(t["token_id"]), q(t["node_bpmn_id"]), q(t["name"]),
                   q(t["assignee"]), q(t["candidate_groups"]), qj(t["element_value"]), q(t["owner_user_id"]),
                   q(t["parent_task_id"]), q(t["delegation_state"]), q(t["completed"]),
                   fmt_ts(t["created_at"]), fmt_ts(t["completed_at"])]])
    for c in rows["candidates"]:
        L += ins("cmx_flow_task_candidate",
                 ["id", "task_id", "instance_id", "candidate_type", "candidate_ref", "resolved_user_id"],
                 [[q(c["id"]), q(c["task_id"]), q(c["instance_id"]), q(c["candidate_type"]),
                   q(c["candidate_ref"]), q(c["resolved_user_id"])]])
    for m in rows["mi"]:
        L += ins("cmx_flow_mi_scope",
                 ["id", "instance_id", "node_bpmn_id", "sequential", "total", "completed", "next_index",
                  "collection", "element_var", "completion_condition", "finished"],
                 [[q(m["id"]), q(m["instance_id"]), q(m["node_bpmn_id"]), q(m["sequential"]), q(m["total"]),
                   q(m["completed"]), q(m["next_index"]), qj(m["collection"]), q(m["element_var"]),
                   q(m["completion_condition"]), q(m["finished"])]])
    for c in rows["cc"]:
        L += ins("cmx_flow_cc",
                 ["id", "instance_id", "node_bpmn_id", "to_user_id", "from_user_id", "reason", "read_at", "created_at"],
                 [[q(c["id"]), q(c["instance_id"]), q(c["node_bpmn_id"]), q(c["to_user_id"]),
                   q(c["from_user_id"]), q(c["reason"]), fmt_ts(c["read_at"]), fmt_ts(c["created_at"])]])
    for d in rows["delegations"]:
        L += ins("cmx_flow_task_delegation",
                 ["id", "task_id", "instance_id", "kind", "from_user_id", "to_user_id", "temp_task_id", "reason", "created_at"],
                 [[q(d["id"]), q(d["task_id"]), q(d["instance_id"]), q(d["kind"]), q(d["from_user_id"]),
                   q(d["to_user_id"]), q(d["temp_task_id"]), q(d["reason"]), fmt_ts(d["created_at"])]])
    for c in rows["comments"]:
        L += ins("cmx_flow_task_comment",
                 ["id", "instance_id", "task_id", "node_bpmn_id", "user_id", "decision", "comment", "created_at"],
                 [[q(c["id"]), q(c["instance_id"]), q(c["task_id"]), q(c["node_bpmn_id"]), q(c["user_id"]),
                   q(c["decision"]), q(c["comment"]), fmt_ts(c["created_at"])]])
    L.append("")
    return L


def emit_hi(all_rows):
    L = ["-- ═══ 历史归档（HI）：终态实例归档 ═══"]
    hi_i, hi_t = [], []
    for rows in all_rows:
        i = rows["instance"]
        if i["state"] not in ("COMPLETED", "TERMINATED"):
            continue
        hi_i.append([q(i["id"]), q(i["definition_key"]), q(i["business_key"]), q(i["state"]),
                     qj(i["variables"]), fmt_ts(i["created_at"]), fmt_ts(i["ended_at"]),
                     ms(i["created_at"], i["ended_at"]) or "NULL", fmt_ts(i["ended_at"])])
        for t in rows["tasks"]:
            if t["completed"] and t["completed_at"]:
                hi_t.append([q(t["id"]), q(t["instance_id"]), q(t["node_bpmn_id"]), q(t["name"]),
                             q(t["assignee"]), fmt_ts(t["created_at"]), fmt_ts(t["completed_at"]),
                             ms(t["created_at"], t["completed_at"]) or "NULL", fmt_ts(i["ended_at"])])
    L += ins("cmx_flow_hi_instance",
             ["id", "definition_key", "business_key", "state", "variables", "created_at", "ended_at",
              "duration_ms", "archived_at"], hi_i)
    L += ins("cmx_flow_hi_task",
             ["id", "instance_id", "node_bpmn_id", "name", "assignee", "created_at", "completed_at",
              "duration_ms", "archived_at"], hi_t)
    L.append("")
    return L, len(hi_i), len(hi_t)


def load_handcrafted(path):
    sys.dont_write_bytecode = True   # 避免 __pycache__ 污染技能目录
    spec = importlib.util.spec_from_file_location("handcrafted", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    rows_list = mod.build()
    assert isinstance(rows_list, list) and rows_list, "handcrafted 模块须返回非空 list[rows]"
    for rows in rows_list:
        validate_rows(rows)
    return rows_list, getattr(mod, "LABEL", "handcrafted")


def main():
    ap = argparse.ArgumentParser(description="cmx-flowengine 流程测试数据重建器")
    ap.add_argument("--repo", required=True, help="cmx-flowengine 仓库绝对路径")
    ap.add_argument("--transcript", action="append", required=True, help="REST 流水日志（可多次）")
    ap.add_argument("--def-dir", action="append", required=True, help="BPMN 定义目录（可多次）")
    ap.add_argument("--manifest", required=True,
                    help="manifest JSON（身份/绑定/版本覆盖；相对路径按 --repo 解析）")
    ap.add_argument("--handcrafted",
                    help="可选：手建实例 Python 模块（混有无流水轮次时加，与流水重放段叠加；相对路径按 --repo 解析）")
    ap.add_argument("--iam-db", default="cmxlocal", help="身份库库名（写入 \\connect）")
    ap.add_argument("--flow-db", default="cmx_fico", help="运行库库名（写入 \\connect）")
    ap.add_argument("--base-ts", default=None,
                    help="合成时间戳基准；缺省自动取流水内最早真实时间戳 -10s（无任何时间戳时必须显式给）")
    ap.add_argument("--out", required=True, help="输出 SQL 文件路径（相对路径按 cwd 解析）")
    args = ap.parse_args()

    def resolve_repo(p):
        return p if os.path.isabs(p) else os.path.join(args.repo, p)

    with open(resolve_repo(args.manifest), encoding="utf-8") as f:
        mf = json.load(f)
    iam = mf.get("iam", {})
    seed_t = "'" + mf.get("seed_time", "2026-08-16 02:00:00+00") + "'"

    R = Replay()
    unparsed_total = 0
    for t in args.transcript:
        p = t if os.path.isabs(t) else os.path.join(args.repo, t)
        blocks, bad = parse_transcript(p)
        unparsed_total += bad
        for method, path, req, resp in blocks:
            R.feed(method, path, req, resp)
    R.finalize()
    harvested = [parse_ts(v) for v in list(R.task_created.values()) + list(R.inst_created.values())]
    harvested = [t for t in harvested if t]

    if args.base_ts:
        base = parse_ts(args.base_ts)
        assert base, f"--base-ts 非法: {args.base_ts}"
    elif harvested:
        base = min(harvested) - timedelta(seconds=10)
    else:
        sys.exit("无可收割的真实时间戳，必须显式传 --base-ts（如 2026-08-16T04:45:00+00:00）")
    if unparsed_total:
        print(f"WARNING: {unparsed_total} 个 REQ/RESP 块 JSON 解析失败（已跳过，可能丢数据）", file=sys.stderr)
    all_defs = load_defs([d if os.path.isabs(d) else os.path.join(args.repo, d) for d in args.def_dir])
    # 只保留本轮真正用到的定义：流水发布过 / 被实例引用 / 是绑定目标（剔除 bad_nostart 等负向样例）
    used = set(R.pubver) | {r.get("defkey") for r in R.inst.values() if r.get("defkey")}         | {b.get("target_definition_key") for b in mf.get("subflow_bindings", [])}
    used.discard(None)
    defs = {k: v for k, v in all_defs.items() if k in used}

    hand = []
    hand_label = "handcrafted"
    if args.handcrafted:
        hand, hand_label = load_handcrafted(resolve_repo(args.handcrafted))

    skipped = []
    for iid, r in R.inst.items():
        if not r["views"]:
            skipped.append({"id": iid, "defkey": r.get("defkey"), "businessKey": r.get("bk")})
            print(f"WARNING: 实例无任何视图，跳过: {iid} def={r.get('defkey')} bk={r.get('bk')}",
                  file=sys.stderr)
    missing_def = {r.get("defkey") for r in R.inst.values() if r.get("defkey")} \
        | {b.get("target_definition_key") for b in mf.get("subflow_bindings", [])} - set(defs)
    for key in sorted(x for x in missing_def if x and x not in defs):
        print(f"WARNING: 实例/绑定引用了定义 {key}，但 --def-dir 中无对应 BPMN，定义将缺失", file=sys.stderr)

    full = []
    for iid in R.inst:
        if iid in {s["id"] for s in skipped}:
            continue
        rows = build_rows(R, defs, mf.get("called_targets", {}), iid, base)
        validate_rows(rows)          # 重放段同样过结构校验（P2-1）
        full.append(rows)
    # 自检（fail-fast）：开放任务令牌必须落在该实例最终令牌集合内
    for rows in full:
        fin_ids = {t["id"] for t in rows["tokens"]}
        for t in rows["tasks"]:
            if not t["completed"] and t["token_id"] not in fin_ids:
                sys.exit(f"SELF-CHECK FAIL: 开放任务令牌孤儿 {rows['instance']['id']} "
                         f"task={t['id']} node={t['node_bpmn_id']} token={t['token_id']}")

    # ———— SQL 头 ————
    out = [f"""-- ═══════════════════════════════════════════════════════════════════════════════
-- cmx-flowengine 流程测试数据重建 SQL
-- 由技能 flow-testdata-generator/scripts/rebuild_flow_testdata.py 生成
-- 流水源: {', '.join(args.transcript)}
-- 定义项: {len(defs)} 个（{', '.join(args.def_dir)}）
-- 手建段: {args.handcrafted or '无'}
-- 覆盖度: 流水重放 {len(full)} 实例{'; 跳过无视图实例 ' + str(len(skipped)) + ' 个(' + ', '.join(s['id'][:8] for s in skipped) + ')' if skipped else ''}{'; 未解析块 ' + str(unparsed_total) + ' 个' if unparsed_total else ''}
-- ═══════════════════════════════════════════════════════════════════════════════
-- 目标库（两个库，按需修改 \\connect 行）：
--   身份库（{args.iam_db}）：组织/用户/角色/岗位 + 子流程组织绑定
--   运行库（{args.flow_db}）：流程定义 + 全部运行态/历史态
--
-- 数据保真度：
--   ✔ 真实值：实例/任务/抄送 id、定义 key、businessKey、状态、令牌节点、办理人、候选人、
--             变量、台账 kind/from/to/reason/createdAt、任务 createdAt、抄送 createdAt/read
--   ◈ 确定性重建值：令牌 id（uuid5 稳定生成；开放任务与令牌严格挂接，已办任务 token_id 悬挂
--             ——与引擎快照全删重插后的真实行为一致）、updated_at/completed_at/HI 时长/
--             意见 created_at（按流水顺序等间隔合成）
--
-- 执行：psql "postgres://<user>:<pwd>@<host>:5432/postgres" -f 本文件
-- 幂等性：DDL 幂等；数据 INSERT 不带冲突处理，重复执行前先跑文末清理段（注释态）。
-- ═══════════════════════════════════════════════════════════════════════════════

SET client_min_messages = WARNING;

-- ═══ 第一部分 · 身份库（{args.iam_db}）═══
\\connect {args.iam_db}
""", DDL_IAM]

    # ———— IAM 数据 ————
    out.append("\n-- —— 组织树 ——")
    out += ins("cmx_org",
               ["id", "code", "name", "parent_id", "path", "leader_user_id", "sort_order", "status", "archived", "create_time"],
               [[q(o["id"]), q(o.get("code")), q(o.get("name")), q(o.get("parent_id")), q(o.get("path")),
                 q(o.get("leader_user_id")), q(o.get("sort_order", 0)), q(o.get("status", 1)),
                 q(o.get("archived", 0)), seed_t] for o in iam.get("orgs", [])])
    out.append("\n-- —— 角色 / 岗位 ——")
    out += ins("cmx_role", ["id", "code", "name", "status", "archived", "create_time"],
               [[q(x["id"]), q(x["code"]), q(x.get("name")), "1", "0", seed_t] for x in iam.get("roles", [])])
    out += ins("cmx_position", ["id", "code", "name", "org_id", "status", "archived", "create_time"],
               [[q(x["id"]), q(x["code"]), q(x.get("name")), q(x.get("org_id")), "1", "0", seed_t]
                for x in iam.get("positions", [])])
    out.append("\n-- —— 用户 / 关系 ——")
    out += ins("cmx_user", ["id", "username", "nickname", "org_id", "status", "archived", "create_time", "update_time"],
               [[q(x["id"]), q(x.get("username", x["id"])), q(x.get("nickname")), q(x.get("org_id")),
                 "1", "0", seed_t, seed_t] for x in iam.get("users", [])])
    out += ins("cmx_user_role", ["id", "user_id", "role_id", "archived", "create_time"],
               [[q(x["id"]), q(x["user_id"]), q(x["role_id"]), "0", seed_t] for x in iam.get("user_roles", [])])
    out += ins("cmx_user_position", ["id", "user_id", "position_id", "is_primary", "archived", "create_time"],
               [[q(x["id"]), q(x["user_id"]), q(x["position_id"]),
                 "TRUE" if x.get("is_primary", True) else "FALSE", "0", seed_t]
                for x in iam.get("user_positions", [])])
    out.append("\n-- —— 子流程组织绑定 ——")
    out += ins("cmx_flow_subflow_binding",
               ["id", "called_key", "org_id", "target_definition_key", "enabled", "remark", "created_at", "updated_at"],
               [[q(u5("bind", b["called_key"], b.get("org_id") or "DEFAULT")), q(b["called_key"]),
                 q(b.get("org_id")), q(b["target_definition_key"]),
                 "TRUE" if b.get("enabled", True) else "FALSE", q(b.get("remark")), seed_t, seed_t]
                for b in mf.get("subflow_bindings", [])])

    # ———— 运行库 ————
    out.append(f"""
-- ═══ 第二部分 · 流程运行库（{args.flow_db}）═══
\\connect {args.flow_db}
""")
    out.append(DDL_FLOW)
    out.append("\n-- —— 流程定义（XML 源自 BPMN 文件；版本取流水最大发布号，manifest 可覆盖）——")
    ver_ov = mf.get("def_versions", {})
    notes = mf.get("def_notes", {})
    pub_ts = "'" + mf.get("publish_time", "2026-08-16 12:00:00+00") + "'"
    defrows, verrows = [], []
    for key in sorted(defs):
        info = defs[key]
        ver = ver_ov.get(key) or R.pubver.get(key, 1)
        defrows.append([q(key), q(info["name"] or key), "NULL", "NULL", "NULL", "NULL",
                        "'PUBLISHED'", q(ver), q(info["xml"]), pub_ts, "'tester'"])
        verrows.append([q(u5("defver", key, ver)), q(key), q(ver), q(info["xml"]),
                        q(notes.get(key, "")), pub_ts, "'tester'"])
    out += ins("cmx_flow_definition",
               ["key", "name", "domain", "application", "module", "category", "state",
                "active_version", "draft_xml", "updated_at", "updated_by"], defrows)
    out += ins("cmx_flow_definition_version",
               ["id", "def_key", "version", "bpmn_xml", "note", "published_at", "published_by"], verrows)
    fb = mf.get("form_bindings", [])
    if fb:
        out.append("\n-- —— 表单绑定 ——")
        out += ins("cmx_flow_form_binding",
                   ["form_key", "kind", "native_page", "native_view", "html_page", "biz_table",
                    "domain", "application", "module", "file", "pk_field", "title", "updated_at"],
                   [[q(x.get(k)) for k in ("form_key", "kind", "native_page", "native_view", "html_page",
                                           "biz_table", "domain", "application", "module", "file",
                                           "pk_field", "title")] + [q(x.get("updated_at"))] for x in fb])

    if hand:
        out.append(f"\n-- ═══ 手建段 · {hand_label}（无流水轮次，按测试报告快照手工重建）═══\n")
        for rows in hand:
            out += emit_instance_block(rows, hand_label)
    out.append(f"\n-- ═══ 流水重放段 · {len(full)} 实例（真实 id/状态/办理人）═══\n")
    for rows in full:
        out += emit_instance_block(rows, "replay")
    hi, n_hi_i, n_hi_t = emit_hi(hand + full)
    out += hi

    out.append(f"""
-- ═══════════════════════════════════════════════════════════════════════════════
-- 附 · 清理段（重复导入前执行；默认注释）
-- ═══════════════════════════════════════════════════════════════════════════════
-- \\connect {args.flow_db}
-- TRUNCATE cmx_flow_task_comment, cmx_flow_biz_link, cmx_flow_form_binding,
--          cmx_flow_task_candidate, cmx_flow_task_delegation, cmx_flow_cc, cmx_flow_job,
--          cmx_flow_mi_scope, cmx_flow_task, cmx_flow_token, cmx_flow_instance,
--          cmx_flow_hi_task, cmx_flow_hi_instance,
--          cmx_flow_definition_version, cmx_flow_definition, cmx_flow_subflow_binding;
-- \\connect {args.iam_db}
-- DELETE FROM cmx_flow_subflow_binding;
-- TRUNCATE cmx_user_role, cmx_user_position;
-- TRUNCATE cmx_user, cmx_role, cmx_org, cmx_position;   -- 若为共享 IAM 库请改按本文件 users/orgs 清单 DELETE
""")

    text = "\n".join(out)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(text)

    def cnt(rs, k):
        return sum(len(r[k]) for r in rs)
    stats = {
        "unparsed_blocks": unparsed_total, "skipped_no_view": len(skipped),
        "handcrafted_instances": len(hand), "replay_instances": len(full),
        "defs": len(defs), "tokens": cnt(hand + full, "tokens"), "tasks": cnt(hand + full, "tasks"),
        "candidates": cnt(hand + full, "candidates"), "mi": cnt(hand + full, "mi"),
        "cc": cnt(hand + full, "cc"), "delegations": cnt(hand + full, "delegations"),
        "comments": cnt(hand + full, "comments"), "hi_instance": n_hi_i, "hi_task": n_hi_t,
        "bindings": len(mf.get("subflow_bindings", [])), "users": len(iam.get("users", [])),
        "orgs": len(iam.get("orgs", [])),
    }
    stats["inserts"] = text.count("INSERT INTO")
    print(json.dumps(stats, ensure_ascii=False, indent=1))
    print("OUT:", os.path.abspath(args.out), f"{os.path.getsize(args.out)/1024:.0f} KB")


if __name__ == "__main__":
    main()
