#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手建段示例：biz-test 差旅报销测试（无流水留存，按报告 §7 保留态快照手工重建）。
═══════════════════════════════════════════════════════════════════════════════
这是 rebuild_flow_testdata.py --handcrafted 的真实样例（2026-08-16 测试轮），
新轮次按本文件结构替换：实例 id 保留报告披露前缀（biz_uuid），终态/停留位置/
办理人严格照报告表格，意见文案为通用占位（报告仅记数目时须在产物头部声明）。

契约：
  LABEL  可选，输出分节标题
  build() -> list[rows]，rows 含 instance/tokens/tasks/candidates/mi/cc/delegations/comments
            （键名与 rebuild_flow_testdata.build_rows 一致；生成器会做 validate_rows 校验）
自包含：不 import 生成器；uuid5 命名空间须与其一致（跨段令牌 id 才能对上）。
"""
import uuid
from datetime import datetime, timedelta, timezone

NS = uuid.UUID("6d5f9c2e-1111-4a2d-9b3f-5f1e87a2b0d1")  # 与生成器一致，勿改
LABEL = "biz-test 差旅报销（报告 §7 快照）"
BASE = datetime(2026, 8, 16, 3, 0, 0, tzinfo=timezone.utc)


def u5(*parts):
    return str(uuid.uuid5(NS, "#".join(str(p) for p in parts)))


def biz_uuid(prefix8, n):
    """报告只披露实例 id 前 8 位 → 拼成合法 UUID（前缀可对照报告）。"""
    return f"{prefix8}-0000-4000-8000-{n:012d}"


def new_rows(iid, defkey, bk, org, state, vars_, tokens, delegations=None,
             parent=None, ended=None, created=None):
    """骨架：instance + tokens + delegations；tasks/comments 由 task()/set_comments() 追加。"""
    created = created or BASE
    delegations = delegations or []
    upd = ended or max([d["created_at"] for d in delegations] + [created])
    return {
        "instance": {"id": iid, "definition_key": defkey, "business_key": bk, "state": state,
                     "variables": vars_, "created_at": created, "updated_at": upd,
                     "ended_at": ended, "org_id": org,
                     "parent_instance_id": parent and parent[0],
                     "parent_token_id": parent and parent[1],
                     "parent_node_bpmn_id": parent and parent[2]},
        "tokens": [{"id": u5("tok", iid, t[0], t[1], k), "instance_id": iid, "node_bpmn_id": t[0],
                    "state": t[1], "parent_id": None, "created_at": created, "updated_at": upd}
                   for k, t in enumerate(tokens)],
        "tasks": [], "candidates": [], "mi": [], "cc": [],
        "delegations": [{"id": u5("deleg", iid, d["created_at"].isoformat(), k),
                         "task_id": d["task_id"], "instance_id": iid, "kind": d["kind"],
                         "from_user_id": d["from_user_id"], "to_user_id": d["to_user_id"],
                         "temp_task_id": None, "reason": d["reason"], "created_at": d["created_at"]}
                        for k, d in enumerate(delegations)],
        "comments": [],
    }


def add_task(rows, node, name, assignee, created, completed=None, done=True):
    """追加任务行；token 优先挂当前 WAITING/WAITING_SUBFLOW 令牌，否则挂历史令牌 id。返回 task_id。"""
    iid = rows["instance"]["id"]
    tid = u5("task", iid, node, created.isoformat())
    tok = next((t["id"] for t in rows["tokens"]
                if t["node_bpmn_id"] == node and t["state"] in ("WAITING", "WAITING_SUBFLOW")), None)
    rows["tasks"].append({
        "id": tid, "instance_id": iid,
        "token_id": tok or u5("tokhist", iid, node, tid),
        "node_bpmn_id": node, "name": name, "assignee": assignee, "candidate_groups": None,
        "element_value": None, "owner_user_id": None, "parent_task_id": None,
        "delegation_state": None, "completed": done, "created_at": created,
        "completed_at": completed,
    })
    return tid


def set_comments(rows, raw):
    """把 {task_id,node,user,text,at} 裸意见转成行结构。"""
    rows["comments"] = [{
        "id": u5("cmt", rows["instance"]["id"], c["task_id"], k),
        "instance_id": rows["instance"]["id"],
        "task_id": c["task_id"], "node_bpmn_id": c["node"], "user_id": c["user"],
        "decision": c.get("decision"), "comment": c["text"], "created_at": c["at"],
    } for k, c in enumerate(raw)]


def build():
    T = lambda m, s=0: BASE + timedelta(minutes=m, seconds=s)

    # —— 场景 A · CLYX-2026-001 总部大额 50000：父子全办结 ——
    a = new_rows(biz_uuid("d1dd3f63", 1), "travel_expense", "CLYX-2026-001", "zongbu",
                 "COMPLETED", {"amount": 50000, "initiator": "u_emp", "comment": "打款完成"},
                 [("end", "ENDED")], ended=T(4, 30), created=T(0))
    t1 = add_task(a, "mgr", "部门经理审批", "u_mgr", T(0, 5), T(0, 50))
    t2 = add_task(a, "director", "总监审批", "u_director", T(0, 55), T(1, 30))
    t3 = add_task(a, "cashier", "出纳打款", "u_cashier", T(3, 40), T(4, 25))
    set_comments(a, [
        {"task_id": t1, "node": "mgr", "user": "u_mgr", "text": "属实，同意", "at": T(0, 50)},
        {"task_id": t2, "node": "director", "user": "u_director", "text": "大额已核，通过", "at": T(1, 30)},
        {"task_id": t3, "node": "cashier", "user": "u_cashier", "text": "打款完成", "at": T(4, 25)}])
    a_child = new_rows(biz_uuid("0b0ab0fc", 1), "fin_review_hq", "CLYX-2026-001", "zongbu",
                       "COMPLETED", {"amount": 50000, "initiator": "u_emp"}, [("end", "ENDED")],
                       parent=(a["instance"]["id"], u5("tokhist", a["instance"]["id"], "fin_review", "subA"), "fin_review"),
                       ended=T(3, 30), created=T(1, 40))
    c1 = add_task(a_child, "fin1", "财务初审", "u_fin1", T(1, 45), T(2, 10))
    c2 = add_task(a_child, "fin2", "财务经理复核", "u_fin2", T(2, 15), T(2, 40))
    c3 = add_task(a_child, "fin3", "财务总监审批", "u_fin3", T(2, 45), T(3, 20))
    set_comments(a_child, [
        {"task_id": c1, "node": "fin1", "user": "u_fin1", "text": "票据齐全", "at": T(2, 10)},
        {"task_id": c2, "node": "fin2", "user": "u_fin2", "text": "复核通过", "at": T(2, 40)},
        {"task_id": c3, "node": "fin3", "user": "u_fin3", "text": "同意报销", "at": T(3, 20)}])

    # —— 场景 B · CLYX-2026-002 上海小额 3000：父子全办结（单签子流程）——
    b = new_rows(biz_uuid("a5cd07dd", 1), "travel_expense", "CLYX-2026-002", "fin_sh",
                 "COMPLETED", {"amount": 3000, "initiator": "u_emp2", "comment": "打款完成"},
                 [("end", "ENDED")], ended=T(9, 0), created=T(5, 0))
    b1 = add_task(b, "mgr", "部门经理审批", "u_mgr", T(5, 5), T(5, 40))
    b2 = add_task(b, "cashier", "出纳打款", "u_cashier", T(8, 20), T(8, 55))
    set_comments(b, [
        {"task_id": b1, "node": "mgr", "user": "u_mgr", "text": "同意", "at": T(5, 40)},
        {"task_id": b2, "node": "cashier", "user": "u_cashier", "text": "打款完成", "at": T(8, 55)}])
    b_child = new_rows(biz_uuid("1172dcd3", 1), "fin_review_branch", "CLYX-2026-002", "fin_sh",
                       "COMPLETED", {"amount": 3000, "initiator": "u_emp2"}, [("end", "ENDED")],
                       parent=(b["instance"]["id"], u5("tokhist", b["instance"]["id"], "fin_review", "subB"), "fin_review"),
                       ended=T(8, 10), created=T(5, 50))
    bc1 = add_task(b_child, "finb", "分公司财务单签", "u_finb", T(5, 55), T(8, 0))
    set_comments(b_child, [{"task_id": bc1, "node": "finb", "user": "u_finb", "text": "单签通过", "at": T(8, 0)}])

    # —— 场景 E1 · CLYX-2026-003 北京 8000：停子流程 fin1（沿 path 继承路由）——
    e1 = new_rows(biz_uuid("e1000001", 1), "travel_expense", "CLYX-2026-003", "fin_bj",
                  "ACTIVE", {"amount": 8000, "initiator": "u_emp3"}, [("fin_review", "WAITING_SUBFLOW")],
                  created=T(11, 0))
    e1_t = add_task(e1, "mgr", "部门经理审批", "u_mgr", T(11, 5), T(11, 40))
    set_comments(e1, [{"task_id": e1_t, "node": "mgr", "user": "u_mgr", "text": "同意", "at": T(11, 40)}])
    e1_child = new_rows(biz_uuid("e1000002", 1), "fin_review_hq", "CLYX-2026-003", "fin_bj",
                        "ACTIVE", {"amount": 8000, "initiator": "u_emp3"}, [("fin1", "WAITING")],
                        parent=(e1["instance"]["id"], e1["tokens"][0]["id"], "fin_review"), created=T(11, 50))
    add_task(e1_child, "fin1", "财务初审", "u_fin1", T(11, 55), None, done=False)

    # —— 场景 E2 · CLYX-2026-004 未知组织 1500：停子流程 fin1（默认兜底路由）——
    e2 = new_rows(biz_uuid("e2000001", 1), "travel_expense", "CLYX-2026-004", "ghost_dept",
                  "ACTIVE", {"amount": 1500, "initiator": "u_emp4"}, [("fin_review", "WAITING_SUBFLOW")],
                  created=T(12, 0))
    e2_t = add_task(e2, "mgr", "部门经理审批", "u_mgr", T(12, 5), T(12, 40))
    set_comments(e2, [{"task_id": e2_t, "node": "mgr", "user": "u_mgr", "text": "同意", "at": T(12, 40)}])
    e2_child = new_rows(biz_uuid("e2000002", 1), "fin_review_hq", "CLYX-2026-004", "ghost_dept",
                        "ACTIVE", {"amount": 1500, "initiator": "u_emp4"}, [("fin1", "WAITING")],
                        parent=(e2["instance"]["id"], e2["tokens"][0]["id"], "fin_review"), created=T(12, 50))
    add_task(e2_child, "fin1", "财务初审", "u_fin1", T(12, 55), None, done=False)

    # —— 场景 C · CLYX-2026-005 总部 30000：子流程 fin3 跨级退回 fin1 返工态 ——
    c = new_rows(biz_uuid("53aec125", 1), "travel_expense", "CLYX-2026-005", "zongbu",
                 "ACTIVE", {"amount": 30000, "initiator": "u_emp"}, [("fin_review", "WAITING_SUBFLOW")],
                 created=T(13, 0))
    c_t1 = add_task(c, "mgr", "部门经理审批", "u_mgr", T(13, 5), T(13, 40))
    c_t2 = add_task(c, "director", "总监审批", "u_director", T(13, 45), T(14, 20))
    set_comments(c, [
        {"task_id": c_t1, "node": "mgr", "user": "u_mgr", "text": "同意", "at": T(13, 40)},
        {"task_id": c_t2, "node": "director", "user": "u_director", "text": "通过，转财务复核", "at": T(14, 20)}])
    c_child = new_rows(biz_uuid("c0aec125", 1), "fin_review_hq", "CLYX-2026-005", "zongbu",
                       "ACTIVE", {"amount": 30000, "initiator": "u_emp"}, [("fin1", "WAITING")],
                       delegations=[{"task_id": None, "kind": "REJECT", "from_user_id": "u_fin3",
                                     "to_user_id": "fin1", "reason": "金额有误，跨级退回初审重审",
                                     "created_at": T(16, 30)}],
                       parent=(c["instance"]["id"], c["tokens"][0]["id"], "fin_review"), created=T(14, 30))
    cf1 = add_task(c_child, "fin1", "财务初审", "u_fin1", T(14, 35), T(15, 0))
    cf2 = add_task(c_child, "fin2", "财务经理复核", "u_fin2", T(15, 5), T(15, 30))
    cf3 = add_task(c_child, "fin3", "财务总监审批", "u_fin3", T(15, 35), T(16, 30))
    set_comments(c_child, [
        {"task_id": cf1, "node": "fin1", "user": "u_fin1", "text": "初审通过", "at": T(15, 0)},
        {"task_id": cf2, "node": "fin2", "user": "u_fin2", "text": "复核通过", "at": T(15, 30)},
        {"task_id": cf3, "node": "fin3", "user": "u_fin3", "text": "金额有误，退回初审",
         "decision": "REJECT", "at": T(16, 30)}])
    add_task(c_child, "fin1", "财务初审", "u_fin1", T(16, 35), None, done=False)  # 退回后的返工待办
    c_child["delegations"][0]["task_id"] = cf3

    # —— 场景 D-a · CLYX-2026-006 总部 6000：发起人取回，改派回 u_emp6 ——
    wd_ts = datetime(2026, 8, 16, 3, 11, 38, 250000, tzinfo=timezone.utc)  # 报告 §6.1 实测时刻
    d = new_rows(biz_uuid("8f403176", 1), "travel_expense", "CLYX-2026-006", "zongbu",
                 "ACTIVE", {"amount": 6000, "initiator": "u_emp6"}, [("mgr", "WAITING")],
                 delegations=[{"task_id": None, "kind": "WITHDRAW", "from_user_id": "u_emp6",
                               "to_user_id": "u_emp6", "reason": "信息填错，取回修改", "created_at": wd_ts}],
                 created=T(11, 30))
    dt = add_task(d, "mgr", "部门经理审批", "u_emp6", T(11, 35), None, done=False)  # 取回后改派发起人
    d["delegations"][0]["task_id"] = dt

    # —— 场景 D-b · CLYX-2026-007 总部 9000：经理已办结，停子流程 fin1（strict 拒取）——
    db = new_rows(biz_uuid("991ca740", 1), "travel_expense", "CLYX-2026-007", "zongbu",
                  "ACTIVE", {"amount": 9000, "initiator": "u_emp7"}, [("fin_review", "WAITING_SUBFLOW")],
                  created=T(13, 30))
    db_t = add_task(db, "mgr", "部门经理审批", "u_mgr", T(13, 35), T(14, 10))
    set_comments(db, [{"task_id": db_t, "node": "mgr", "user": "u_mgr", "text": "同意", "at": T(14, 10)}])
    db_child = new_rows(biz_uuid("d91ca740", 1), "fin_review_hq", "CLYX-2026-007", "zongbu",
                        "ACTIVE", {"amount": 9000, "initiator": "u_emp7"}, [("fin1", "WAITING")],
                        parent=(db["instance"]["id"], db["tokens"][0]["id"], "fin_review"), created=T(14, 20))
    add_task(db_child, "fin1", "财务初审", "u_fin1", T(14, 25), None, done=False)

    return [a, a_child, b, b_child, e1, e1_child, e2, e2_child, c, c_child, d, db, db_child]
