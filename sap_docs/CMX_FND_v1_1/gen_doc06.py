#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generator for 06_CMX平台SAP功能落地增强报告.md — 差距分析 + 增强路线。

Run: python3 gen_doc06.py
"""
import base64
import html
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "06_CMX平台SAP功能落地增强报告.md")


def esc(s):
    return html.escape(str(s), quote=True)


def b64img(svg, alt):
    b = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return (f'<p align="center"><img alt="{esc(alt)}" '
            f'style="max-width:100%;height:auto;border:1px solid #e2e8f0;border-radius:8px" '
            f'src="data:image/svg+xml;base64,{b}"></p>')


# ---------------------------------------------------------------------------
# SVG builders
# ---------------------------------------------------------------------------
ARROW = ('<marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
         'orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#64748b"/></marker>')
ARROWR = ('<marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
          'orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#dc2626"/></marker>')


def box(x, y, w, h, title, lines, stroke, fill, title_color="#fff"):
    s = [f'<g><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="1.6"/>',
         f'<rect x="{x}" y="{y}" width="{w}" height="26" rx="8" fill="{stroke}"/>',
         f'<rect x="{x}" y="{y+18}" width="{w}" height="8" fill="{stroke}"/>',
         f'<text x="{x+12}" y="{y+18}" font-family="ui-monospace,Menlo,monospace" font-size="12.5" '
         f'font-weight="700" fill="{title_color}">{esc(title)}</text>']
    yy = y + 26 + 15
    for ln in lines:
        s.append(f'<text x="{x+12}" y="{yy}" font-family="-apple-system,BlinkMacSystemFont,\'PingFang SC\','
                 f'\'Microsoft YaHei\',sans-serif" font-size="11" fill="#1e293b">{esc(ln)}</text>')
        yy += 15
    s.append('</g>')
    return "\n".join(s)


def edge(a, b, label="", color="#64748b", dash="4 3", x1=None, y1=None, x2=None, y2=None, marker="ar"):
    # a,b are (x,y) anchor points
    (ax, ay), (bx, by) = (a, b)
    if x1 is None:
        d = f"M {ax} {ay} C {ax} {(ay+by)/2} {bx} {(ay+by)/2} {bx} {by}"
    else:
        d = f"M {x1} {y1} L {x2} {y2}"
    s = [f'<g><path d="{d}" fill="none" stroke="{color}" stroke-width="1.5" stroke-dasharray="{dash}" '
         f'marker-end="url(#{marker})"/>']
    if label:
        mx = (ax + bx) / 2
        my = (ay + by) / 2
        lw = 7.2 * len(label) + 12
        s.append(f'<rect x="{mx-lw/2}" y="{my-9}" width="{lw}" height="16" rx="4" '
                 f'fill="#fff" fill-opacity="0.95" stroke="#cbd5e1" stroke-width="0.8"/>')
        s.append(f'<text x="{mx}" y="{my+3}" text-anchor="middle" font-family="ui-monospace,Menlo,monospace" '
                 f'font-size="9.5" fill="{color}">{esc(label)}</text>')
    s.append('</g>')
    return "\n".join(s)


def svg1_target_arch():
    """目标架构：分层 + 三类写路径 + 领域核"""
    W, H = 1000, 620
    e = []
    e.append(box(30, 40, 300, 130, "接入层（已具备）",
                 ["DCT/DOC 元数据页面 · 表单", "REST · 导入 · 流程回调 · WASM · AI",
                  "全部经同一受控业务入口"], "#0f766e", "#f0fdfa"))
    e.append(box(390, 40, 280, 130, "领域核 cmx-fnd-kernel（新增）",
                 ["Resolver 上下文解析", "Guard 重验 + 锁序 + 期间门",
                  "领域命令：校验→写→回执→Outbox"], "#dc2626", "#fef2f2"))
    e.append(box(730, 40, 240, 130, "平台底座（已具备）",
                 ["cmx-container 事务桥 · IAM · RLS",
                  "cmx-dct/doc 三件套 · 主库/业务库"], "#4338ca", "#eef2ff"))
    # 三类写路径
    e.append(box(30, 230, 300, 110, "写路径① 配置发布服务",
                 ["组织/参考/核算配置表（绑 release）", "发布校验 → 冻结 → 激活指针"], "#b45309", "#fffbeb"))
    e.append(box(390, 230, 280, 110, "写路径② MDM 领域激活",
                 ["BP/客商/物料/科目成本（时态版本）", "CR 审批 + 激活器 + 类型化校验"], "#1d4ed8", "#eff6ff"))
    e.append(box(730, 230, 240, 110, "写路径③ 专用价格服务",
                 ["估值对象/价格/汇率（非 MDM）", "归一化 + 审批 + 精度"], "#0369a1", "#f0f9ff"))
    e.append(box(390, 400, 280, 90, "运行时门（已具备）",
                 ["period_gate · action_block", "重验不信任旧快照"], "#0f766e", "#ecfdf5"))
    e.append(box(390, 520, 280, 70, "cmx_fnd 58 表（PostgreSQL 15）",
                 ["GiST 双时态 · RLS · 触发器"], "#475569", "#f1f5f9"))
    # edges
    e.append(edge((180, 170), (460, 230), "三类写路径路由", "#dc2626", "5 3"))
    e.append(edge((460, 170), (460, 400), "Guard 锁序", "#dc2626"))
    e.append(edge((530, 290), (530, 400), "", "#dc2626"))
    e.append(edge((530, 490), (530, 520), "", "#64748b"))
    e.append(edge((850, 170), (560, 170), "事务桥/IAM/RLS", "#4338ca"))
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img">'
           f'<defs>{ARROW}{ARROWR}</defs><rect width="{W}" height="{H}" fill="#fbfdff"/>'
           + "\n".join(e) + '</svg>')
    return svg


def svg2_gap_matrix():
    """差距矩阵：需求 × 平台现状"""
    rows = [
        ("发布包 + 四眼 + 不可变", "release/status/触发器 已设计；平台无配置发布服务", "GAP"),
        ("双时态主数据（valid/recorded）", "DCT 只有 effective(date)；DOC 单版本快照", "GAP"),
        ("稳定身份 object_id + 源键映射", "NoID 字典 + code_rule 编码；无跨源身份注册", "半"),
        ("组织/参考配置（绑 release）", "DCT 建表+TableSpec 校验；无发布/冻结语义", "GAP"),
        ("账套/过账规则/期间窗口", "DOC 多层主从可承载；无记账码区间重叠校验", "半"),
        ("统驭科目 D/K 类型校验", "TableSpec 只做列级；无跨表领域校验", "GAP"),
        ("能力门（有字段≠可运行）", "inventory_capability 列已设计；平台无能力门机制", "GAP"),
        ("期间门 + 锁序 + 乐观锁", "DOC 乐观锁 B2 已有；无 FOR SHARE 锁序", "半"),
        ("入站幂等 + Outbox", "command_receipt/outbox 表已设计；平台无发件箱", "半"),
        ("RLS 租户隔离", "dataauth 有 RLS 兜底（dim GUC）+ 应用下推", "OK"),
        ("金额/数量十进制精度", "DataValue + 强类型绑定已有", "OK"),
        ("汇率/价格归一化留痕", "规则引擎决策表可承载；无归一化服务", "半"),
    ]
    W, H = 1000, 60 + len(rows) * 34 + 10
    e = [f'<rect width="{W}" height="{H}" fill="#fbfdff"/>']
    # header
    e.append(box(20, 20, 460, 30, "", ["SAP 功能需求（58 表隐含）"], "#475569", "#f1f5f9", "#334155"))
    e.append(box(500, 20, 360, 30, "", ["CMX 平台现状"], "#475569", "#f1f5f9", "#334155"))
    e.append(box(880, 20, 100, 30, "", ["差距"], "#475569", "#f1f5f9", "#334155"))
    y = 58
    for (need, cur, gap) in rows:
        col = "#dc2626" if gap == "GAP" else ("#b45309" if gap == "半" else "#0f766e")
        e.append(f'<rect x="20" y="{y}" width="460" height="30" fill="#f8fafc" stroke="#e2e8f0" rx="4"/>')
        e.append(f'<rect x="500" y="{y}" width="360" height="30" fill="#f8fafc" stroke="#e2e8f0" rx="4"/>')
        e.append(f'<rect x="880" y="{y}" width="100" height="30" fill="{col}" stroke="{col}" rx="4"/>')
        e.append(f'<text x="30" y="{y+19}" font-size="11.5" font-family="sans-serif" fill="#0f172a">{esc(need)}</text>')
        e.append(f'<text x="510" y="{y+19}" font-size="11" font-family="sans-serif" fill="#334155">{esc(cur)}</text>')
        e.append(f'<text x="930" y="{y+19}" text-anchor="middle" font-size="11.5" font-weight="700" '
                 f'font-family="sans-serif" fill="#fff">{esc(gap)}</text>')
        y += 34
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img">'
           f'<defs>{ARROW}{ARROWR}</defs>' + "\n".join(e) + '</svg>')
    return svg


def svg3_roadmap():
    """增强路线：三阶段"""
    W, H = 1000, 300
    e = [f'<rect width="{W}" height="{H}" fill="#fbfdff"/>']
    phases = [
        ("P0 领域核落地（1 期）", "#dc2626", "#fef2f2",
         ["cmx-fnd-kernel crate：Resolver/Guard/领域命令", "配置发布服务 + 能力门 + 锁序 + 发件箱",
          "受保护表路由到领域命令（8 表直连封死）"]),
        ("P1 双时态 + MDM 升级（2 期）", "#1d4ed8", "#eff6ff",
         ["时态字段集（valid/recorded + approved_change_id）", "MDM 激活器挂类型化资格/核算影响校验",
          "统驭科目 D/K、组织关系、年度覆盖发布校验"]),
        ("P2 价格/汇率/对拍（3 期）", "#0f766e", "#f0fdfa",
         ["专用价格发布服务 + 归一化留痕", "标准价/汇率调用链 + SAP 差分对拍",
          "压测 + 审批回调/Outbox 故障恢复"]),
    ]
    x = 20
    for (t, c, f, lines) in phases:
        e.append(box(x, 30, 300, 220, t, lines, c, f))
        if x > 20:
            e.append(f'<text x="{x-15}" y="140" font-size="22" fill="#94a3b8">→</text>')
        x += 320
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img">'
           f'<defs>{ARROW}</defs>' + "\n".join(e) + '</svg>')
    return svg


def svg4_domain_kernel():
    """领域核内部结构"""
    W, H = 1000, 420
    e = [f'<rect width="{W}" height="{H}" fill="#fbfdff"/>']
    e.append(box(30, 40, 200, 90, "ContextResolver", ["resolve(scope,req,clock)", "→ ResolvedContext"], "#dc2626", "#fef2f2"))
    e.append(box(260, 40, 220, 90, "ContextCommitGuard", ["recheck_and_lock(tx,ctx)", "→ GuardReceipt"], "#dc2626", "#fef2f2"))
    e.append(box(510, 40, 220, 90, "CapabilityGate", ["能力门判定（字段≠可运行）", "inventory/价格方法/日历"], "#dc2626", "#fef2f2"))
    e.append(box(760, 40, 210, 90, "DomainCommand", ["领域命令（每受保护表一命令）", "校验→写→回执→Outbox"], "#dc2626", "#fef2f2"))
    e.append(box(30, 190, 300, 90, "PublicationService", ["配置发布：发布校验→冻结→激活指针", "release 四眼 + content_hash"], "#b45309", "#fffbeb"))
    e.append(box(360, 190, 300, 90, "MdmActivatorHook", ["类型化资格/核算影响校验", "继承业务事务，非法变更零写入"], "#1d4ed8", "#eff6ff"))
    e.append(box(690, 190, 280, 90, "PriceNormalization", ["标准价/汇率归一化留痕", "raw_source→profile→value"], "#0369a1", "#f0f9ff"))
    e.append(box(360, 320, 300, 70, "BitemporalFieldSet", ["valid_from/to + recorded_from/to", "+ approved_change_id + GiST"], "#475569", "#f1f5f9"))
    e.append(edge((130, 130), (130, 190), "①", "#b45309"))
    e.append(edge((370, 130), (370, 320), "③", "#475569"))
    e.append(edge((510, 130), (510, 190), "③", "#1d4ed8"))
    e.append(edge((620, 130), (620, 320), "③", "#475569"))
    e.append(edge((720, 130), (720, 190), "②", "#0369a1"))
    e.append(edge((865, 130), (830, 190), "③", "#1d4ed8"))
    e.append(edge((510, 280), (360, 320), "④", "#475569"))
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img">'
           f'<defs>{ARROW}{ARROWR}</defs>' + "\n".join(e) + '</svg>')
    return svg


def main():
    D = []
    A = D.append
    A("# CMX 平台落地 SAP 功能 — 增强改造报告")
    A("")
    A("> **对象**：`sap_docs/CMX_FND_v1_1` 的 58 张表（SAP 财务/主数据/估值语义），在 CMX 平台上实现完整功能所需的平台增强。")
    A("> **依据**：`05_58表逐列详解.md`（58 表需求侧）、`docs/02_实施详设.md`（FND 写路径与领域核边界）、`backend/` 各仓源码（平台现状，含 `cmx-dct-model` / `cmx-doc-*` / `cmx-mdm-*` / `cmx-dataauth-core` / `cmx-rule-engine` / `cmx-model-deploy` / `cmx-plugin` 的实读证据）。")
    A("> **图**：4 张内嵌 base64 SVG（无需外部文件）。")
    A("")
    A("---")
    A("")
    A("## 0. 结论速览")
    A("")
    A("**一句话**：CMX 平台底座（DCT/DOC/MDM/规则/数据权限/插件/事务桥）已经具备「定义-页面-字典-审批-分发-隔离」的完整骨架，**缺的是一层「领域核」**——把 SAP 里「金额精度、双时态、组织合法性、期间锁、能力门、汇率归一化」这些**只有代码能权威执行、不能靠字典选项假装生效**的东西，落成平台可复用的服务。")
    A("")
    A("| 结论 | 说明 |")
    A("|---|---|")
    A("| **已具备（不必改）** | DCT 双主键形态（id 铸号 / code NoID）、DOC 多层主从 + 乐观锁 + 版本快照、MDM 激活器（CR→published 唯一入口）、dataauth 应用下推 + RLS 兜底、插件签名与生命周期 |")
    A("| **半成品（需补）** | 发布包（表已设计但平台无发布/冻结服务）、双时态（DCT 只有单 effective date）、期间门锁序、入站幂等/Outbox 发件箱 |")
    A("| **缺失（需新建）** | 领域核 crate、配置发布服务、能力门、统驭/组织/日历领域校验、价格与汇率归一化服务 |")
    A("")
    A(b64img(svg1_target_arch(), "目标架构图"))
    A("")
    A("---")
    A("")
    A("## 1. 现状盘点（平台已有什么，附证据）")
    A("")
    A("### 1.1 DCT（数据字典）——已强于预期")
    A("")
    A("`cmx-container/crates/libs/cmx-dct/cmx-dct-model/README.md` 明确：两种主键形态——整型 `id` 走服务端铸号（`pk_is_generated`），以 `code` 作主键的 NoID 字典（如 `cf_currency`）**原样保留不铸号**。这直接解决了 FND 表 `bukrs/werks/kalnr` 等 SAP 自然键「进不了 DCT」的第一重顾虑——NoID 形态天然兼容。")
    A("")
    A("- 列白名单 `valid_col` + `$N` 占位参数化，杜绝注入。")
    A("- 自分级 `parent_id` 重指向（科目树）。")
    A("- `TableSpec` 列级落库校验（`cmx-biz/validation`）。")
    A("- `code_rule` 编码引擎挂载点、`unique_keys` 业务唯一键。")
    A("")
    A("**缺口**：`TableSpec` 只做**列级**格式校验（类型/长度/必填），没有**跨表领域校验**（统驭科目 D/K 类型、组织关系、年度覆盖）；没有**双时态字段集**；没有**能力门**。")
    A("")
    A("### 1.2 DOC（业务单据）——版本化与并发已成熟")
    A("")
    A("`cmx-doc-store-pg/README.md`：多层主从装载/回存 + 四个平台级横切机制——铸号、审计方案 C、乐观锁 B2（根层 `update_time` 基线）、版本快照 B1（`cmx_doc_revision` 列式台账）。另有严格对账 H1（写行数不符即回滚）与 SAVEPOINT 容错。")
    A("")
    A("**缺口**：版本快照是**单版本 DOC 修订**，不是 FND 要的**双时态**（业务时间 valid_* + 系统认知时间 recorded_* + 每行 approved_change_id）。前者是「单据改了几次」，后者是「这条主数据在现实中何时生效、系统何时得知」。")
    A("")
    A("### 1.3 MDM（主数据）——激活器是现成底座")
    A("")
    A("`cmx-mdm-model/README.md`：五块纯逻辑——激活（`ActivationConfig` 字段搬运）、查重（分块/加权/聚类）、survivorship（合并）、distribution（通道 trait）、codegen。V3 铁律：`cm_*` 只存 `published`，草稿走 CR 单据 `cv_mdm_apply`，**激活器是 `cm_*` 唯一写入入口**。状态机 `draft→submit→approving→approve(激活器)→activated`，激活器单事务内 `approving→activated`。")
    A("")
    A("**缺口**：激活器只做**字段搬运**，没有 FND 要求的**类型化资格/核算影响校验**（如「客户统驭科目必须是 D 类」）与**继承业务事务**（激活写库与领域锁在同一事务）。且 MDM 治理的是 `cm_*` 单表字典，**没有跨 5 张 BP/物料版本表的一次性时态激活**。")
    A("")
    A("### 1.4 数据权限——应用下推 + RLS 兜底已具备")
    A("")
    A("`cmx-dataauth-core/rls.rs`：「应用层 WHERE 下推是主力；RLS 是即便漏拼 WHERE 也拦得住的数据库层兜底」，按 `current_setting('dataauth.<t>_scope')` 的 dim 列做 `ENABLE/FORCE ROW LEVEL SECURITY`，并显式警告 RLS 对超级用户无效、须以非超级用户连库。另有 `mask.rs`（Full/Partial/Hash/Hide 列级脱敏）、`pdp.rs`（策略约束模板编译）。")
    A("")
    A("**与 FND 对齐**：FND 的 `scope_guard` 策略（`app.tenant_id`/`app.mandt` GUC）与 dataauth 的 RLS 生成器**同一套思路**——差异在 FND 用 `tenant_id+mandt` 两列、dataauth 用单 dim 列 + bypass GUC。**建议统一**，避免两套 RLS 语义并存。")
    A("")
    A("### 1.5 规则引擎——可承载「版本化企业差异」")
    A("")
    A("`cmx-rule-engine/lib.rs`：决策表/决策图求值，11 命中策略，失败归因（哪条规则、哪个输入列、什么错）。`cmx-rule-feel` 做 unary test。**定位是决策**，不是通用计算。")
    A("")
    A("**缺口**：规则引擎适合「过账校验规则、命中策略」，**不适合**汇率归一化算法、金额精度舍入、锁序这类**过程式领域逻辑**——这些要写在领域核（Rust），不能硬塞进决策表。")
    A("")
    A("### 1.6 插件平台与部署")
    A("")
    A("`cmx-plugin`：ZIP 加载、签名验证、生命周期（安装/升级/降级/回滚）、host_functions、集群部署。`cmx-model-deploy`：定义编译→建表→台账 `cmx_model_deploy_history`→SEED→MENU 顺序。")
    A("")
    A("**关键边界**：插件是**真运行时**。FND 文档 308 行已警告「不能给不可信插件原始 SQL 连接、GUC 不是抗伪造边界」——所以**领域核必须作为插件与核心表之间的受控边界**，插件只能调领域命令，不能直接 SQL 写受保护表。")
    A("")
    A("---")
    A("")
    A("## 2. 差距矩阵")
    A("")
    A(b64img(svg2_gap_matrix(), "差距矩阵"))
    A("")
    A("| # | SAP 功能 | 平台现状 | 差距 | 增强方式 |")
    A("|---|---|---|---|---|")
    A("| 1 | 稳定身份 + 源键映射 | NoID 字典 + code_rule 编码 | **GAP**（无跨源身份注册 `object_id`） | 新建 `master_identity` 领域命令 + `external_key_map` 服务 |")
    A("| 2 | 配置发布包（四眼/冻结/激活指针） | 表已设计，平台无发布服务 | **GAP** | 新建 `PublicationService`（发布校验→冻结→激活指针） |")
    A("| 3 | 双时态主数据 | DCT 单 effective date；DOC 单版本快照 | **GAP** | 新建 `BitemporalFieldSet` + GiST 排斥 + 领域命令 |")
    A("| 4 | 组织/参考配置 | DCT 建表 + TableSpec 列校验 | **GAP** | 发布服务 + 组织关系领域校验 |")
    A("| 5 | 账套/过账规则/期间窗口 | DOC 多层主从可承载 | **半** | 记账码区间重叠 + `COLLATE 'C'` 领域校验 |")
    A("| 6 | 统驭科目 D/K 校验 | TableSpec 只列级 | **GAP** | MDM 激活器挂类型化资格校验 |")
    A("| 7 | 能力门（有字段≠可运行） | 表列已设计，无机制 | **GAP** | 新建 `CapabilityGate` 服务 |")
    A("| 8 | 期间门 + 锁序 | DOC 乐观锁 B2 已有 | **半** | 领域核 Guard：`lock_inventory_context` FOR SHARE |")
    A("| 9 | 入站幂等 + Outbox | 表已设计，无发件箱 | **半** | 领域命令内嵌 `command_receipt` + `outbox` 写入 |")
    A("| 10 | RLS 租户隔离 | dataauth 下推 + RLS 兜底 | **OK** | 统一 FND `tenant_id+mandt` 与 dataauth dim GUC |")
    A("| 11 | 金额/数量十进制精度 | `DataValue` 强类型绑定 | **OK** | 沿用 |")
    A("| 12 | 汇率/价格归一化留痕 | 规则引擎可承载部分 | **半** | 新建 `PriceNormalization` 服务 |")
    A("")
    A("---")
    A("")
    A("## 3. 核心建议：新建「领域核」crate（最优先）")
    A("")
    A(b64img(svg4_domain_kernel(), "领域核内部结构"))
    A("")
    A("### 3.1 为什么必须是新 crate，而不是塞进现有引擎")
    A("")
    A("FND 文档第 59 行定死：「金额、有效期、合法组织关系、必需账本和最终期间锁**由领域核权威执行**，不能只放在前端公式、流程节点或通用字典保存逻辑中。」现有平台没有这个层——DCT 只管定义与列校验，MDM 只管搬运与审批，规则引擎管决策，谁都不该也不该各自实现一套金额舍入/期间锁。**分散实现 = 每处都能被绕过**（FND 299 行：受保护表必须路由到领域命令，页面/导入/插件/AI 均不能绕过）。")
    A("")
    A("### 3.2 领域核四个组件")
    A("")
    A("| 组件 | 职责 | 对应 FND 表/契约 |")
    A("|---|---|---|")
    A("| `ContextResolver` | 按 scope+request+clock 解析出 ResolvedContext（组织、科目表、日历、账套） | `config_head` → `foundation_release` → 各配置表 |")
    A("| `ContextCommitGuard` | 在**同一业务事务**内重验 + 按序加锁 | `period_gate`（FOR SHARE）、`003_locking.sql` 的 `lock_inventory_context` |")
    A("| `CapabilityGate` | 判定「字段存在」是否「业务可运行」 | `book_config.inventory_capability`、`price_method`、日历 `calendar_kind` |")
    A("| `DomainCommand`（每受保护表一个） | 校验→写→回执→Outbox 原子落库 | 受保护 8 表 + 三类写路径 |")
    A("")
    A("### 3.3 三类写路径如何落到平台")
    A("")
    A("| 写路径 | 落点 | 说明 |")
    A("|---|---|---|")
    A("| ① 配置发布服务 | 新建 `cmx-fnd-publish`（或作为领域核子模块） | 组织/参考/核算配置表；发布校验（年度覆盖、记账码区间重叠）→ 冻结 → `config_head` 激活指针 |")
    A("| ② MDM 领域激活 | **扩展现有 `cmx-mdm` 激活器** | BP/客商/物料/科目成本时态版本；激活器挂 `DomainValidator` trait（类型化资格/核算影响）；继承业务事务 |")
    A("| ③ 专用价格服务 | 新建 `cmx-fnd-price` | 估值对象/价格/汇率；归一化留痕 `raw_source→profile→value`；**不能由通用 MDM 改库存金额** |")
    A("")
    A("### 3.4 受保护表路由（硬约束）")
    A("")
    A("以下 8 张表（`external_key_map` / `bp_identity` / `customer_link` / `supplier_link` / `material_identity` / `valuation_unit` / `period_gate` / `action_block`）**必须路由到领域命令**，DCT 通用保存入口、MDM 自动合并、历史版本恢复均不得直写。落地方式：")
    A("")
    A("1. DCT `write.rs` 增加「受保护表注册」：命中即转领域命令，否则拒绝。")
    A("2. 插件 SDK 只暴露领域命令接口，不暴露受保护表 SQL。")
    A("3. RLS 之外，领域命令内再做一次权威校验（纵深防御）。")
    A("")
    A("---")
    A("")
    A("## 4. 次优先：双时态 + 发布 + 领域校验（P1）")
    A("")
    A("### 4.1 双时态字段集（BitemporalFieldSet）")
    A("")
    A("在 `base_dct_meta_v1.json` 现有 `dictionaryEffectiveFields`（单 effective date）之外，新增**双时态字段集**：`valid_from/valid_to`（业务时间，date 或 timestamptz）+ `recorded_from/recorded_to`（系统时间）+ `approved_change_id`。配套：")
    A("")
    A("- 建表时挂 GiST `daterange/tstzrange` 排斥约束（半开 `[)`）。")
    A("- `bp_role_version` 的 valid 用 `timestamptz`（E05），其余用 `date`——**字段集要支持 per-table 覆盖类型**。")
    A("- 版本行「旧行禁改写」触发器（FND 已有 `003_locking.sql` 思路）。")
    A("")
    A("### 4.2 MDM 激活器升级（类型化领域校验）")
    A("")
    A("现有激活器是「配置驱动的字段搬运」，缺「领域校验钩子」。建议在 `cmx-mdm-model` 的 activation 增加 `DomainValidator` trait：")
    A("")
    A("```rust")
    A("trait DomainValidator {")
    A("    // 校验 CR 搬运结果，返回领域错误；激活器在单事务内调用，失败即零写入")
    A("    fn validate(&self, ctx: &ResolvedContext, target: &Value) -> Result<(), DomainError>;")
    A("}")
    A("```")
    A("")
    A("具体校验：统驭科目 D/K 类型（读 `company_config.ktopl` → `gl_account_version` 存在 → `gl_company_version.reconciliation_type`）、组织关系（估值范围归属公司）、年度覆盖（连续无空洞）、记账码区间重叠。")
    A("")
    A("### 4.3 配置发布服务（PublicationService）")
    A("")
    A("FND 的 `foundation_release`（四眼 + content_hash + 触发器不可变）与 `config_head`（激活指针）表已设计，**缺的是平台侧发布编排**：")
    A("")
    A("1. 草稿 release 累积配置变更 → `VALIDATED`（跑发布校验：年度覆盖、区间重叠、能力门）→ `APPROVED`（四眼）→ `PUBLISHED`（写 content_hash + published_at）。")
    A("2. 切版 = `UPDATE config_head SET active_release_id`（单行）。")
    A("3. 已发布 release 不可变由触发器保证，发布服务只做编排。")
    A("")
    A("---")
    A("")
    A("## 5. 增强路线（三阶段）")
    A("")
    A(b64img(svg3_roadmap(), "增强路线"))
    A("")
    A("### P0（第一期）领域核落地 —— 决定「能不能跑起来」")
    A("")
    A("- 新建 `cmx-fnd-kernel` crate（Resolver/Guard/CapabilityGate/DomainCommand）。")
    A("- 修复 `001_foundation.sql` 8 张表的多余 `release_id` 外键（详见 `05_58表逐列详解.md` 附录 A）。")
    A("- 配置发布服务 + 受保护表路由。")
    A("- 入站幂等 + Outbox 发件箱（复用 DOC 的事务编排）。")
    A("")
    A("### P1（第二期）双时态 + MDM 升级 —— 决定「主数据对不对」")
    A("")
    A("- BitemporalFieldSet + GiST 排斥。")
    A("- MDM 激活器挂 DomainValidator（统驭 D/K、组织、年度、区间重叠）。")
    A("- 统一 dataauth RLS 与 FND `scope_guard` 语义。")
    A("")
    A("### P2（第三期）价格/汇率/对拍 —— 决定「金额准不准」")
    A("")
    A("- 专用价格发布服务 + 归一化留痕。")
    A("- 标准价/汇率调用链 + SAP 差分对拍（`tests/并发与集成验收.md` 明确要求）。")
    A("- 压测 + 审批回调/Outbox 故障恢复。")
    A("")
    A("---")
    A("")
    A("## 6. 已存在但不合适、建议不用/改造的")
    A("")
    A("| 现有能力 | 问题 | 处置 |")
    A("|---|---|---|")
    A("| DCT `designStyle`（table / separate-dictionary-tables） | FND 的「配置版本 + 双时态版本」分离在两种 style 下都不映射 | 新增第三种（或按 `05` 文档建议：FND 表走领域核，DCT 只做薄投影） |")
    A("| DCT `dictionaryEffectiveFields` 单 effective date | 装不下双时态四列 + approved_change_id | 保留（单日期字典仍用），另建 `BitemporalFieldSet` |")
    A("| DOC 版本快照 `cmx_doc_revision` | 是单据修订台账，不是双时态主数据 | 保留给 DOC，不用它承载 FND 主数据时态 |")
    A("| MDM 通用激活（字段搬运） | 会把「字段存在」当「可维护」，漏掉能力门与 D/K 校验 | 加 DomainValidator 钩子，FND 表走领域激活 |")
    A("| 规则引擎决策表 | 不适合过程式领域逻辑（舍入/归一化/锁序） | 只用于过账规则/命中策略；过程式逻辑写领域核 |")
    A("| dataauth 单 dim 列 RLS | FND 用 `tenant_id+mandt` 两列 | 统一为两列 + bypass GUC，避免两套语义 |")
    A("")
    A("---")
    A("")
    A("## 7. 结论")
    A("")
    A("CMX 平台**不需要推倒重来**——它的定义/页面/字典/审批/分发/隔离骨架是完整且比 FND 文档预判的更成熟。要落地这 58 张 SAP 表的完整功能，本质是**在骨架上补一层「领域核」**：把发布、双时态、能力门、统驭校验、锁序、价格归一化这六样「不能靠字典选项假装生效」的东西，做成平台可复用的服务，并把受保护表统一路由到领域命令。")
    A("")
    A("**最优先一件事**：新建 `cmx-fnd-kernel` crate（含 `ContextResolver` + `ContextCommitGuard` + `CapabilityGate` + `DomainCommand`）。这一步不做，其余都是沙滩上的楼。")
    A("")
    A("> 生成脚本：`gen_doc06.py`。")
    txt = "\n".join(D)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(txt)
    print("output:", OUT)
    print("bytes :", os.path.getsize(OUT))


if __name__ == "__main__":
    main()
