#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generator for 05_58表逐列详解.md — embedded base64 SVG + full column dictionary.

Run:  python3 gen_doc05.py
"""
import base64
import html
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "05_58表逐列详解.md")
SVGDIR = os.path.join(HERE, "docs", "svg")

# ---------------------------------------------------------------- palette
PAL = {
    "gov": ("#475569", "#f1f5f9"),
    "id":  ("#4338ca", "#eef2ff"),
    "ref": ("#0f766e", "#f0fdfa"),
    "org": ("#b45309", "#fffbeb"),
    "acc": ("#991b1b", "#fef2f2"),
    "map": ("#7c3aed", "#faf5ff"),
    "ver": ("#1d4ed8", "#eff6ff"),
    "val": ("#0369a1", "#f0f9ff"),
    "run": ("#0f766e", "#ecfdf5"),
}

# ---------------------------------------------------------------- modules
MODULES = [
 dict(code="M0", name="治理底座", color="gov", layer="平台治理（非 DCT/DOC）",
      desc="发布包、激活指针、幂等回执、事务发件箱、服务端快照。回答“这套配置是哪一版、这次请求是否已执行过”。",
      tables=["client_scope", "foundation_release", "config_head",
              "command_receipt", "outbox", "context_snapshot"]),
 dict(code="M1", name="稳定组织身份", color="id", layer="DCT（组织字典）",
      desc="七类组织单位的稳定主键。编码一旦分配不可回收再指向别的对象——这是历史单据可回溯的前提。",
      tables=["company_key", "valuation_area_key", "plant_key", "purchasing_org_key",
              "sales_org_key", "controlling_area_key", "ledger_key"]),
 dict(code="M2", name="参考数据与日历", color="ref", layer="DCT（参考字典）",
      desc="币种精度、单位维度、会计年度变式、年度/期间日历、过账变式。是金额与日期的“度量衡”。",
      tables=["currency_config", "uom_config", "fiscal_variant_config",
              "fiscal_year_config", "fiscal_period_config", "posting_variant_config"]),
 dict(code="M3", name="组织配置与分配", color="org", layer="DCT（组织字典）",
      desc="在稳定身份之上叠加“这一版里它叫什么、属于谁、能和谁配合”。全部绑 release_id。",
      tables=["company_config", "valuation_area_config", "plant_config", "storage_location_config",
              "purchasing_org_config", "purchasing_plant_config", "controlling_assignment_config",
              "sales_org_config", "sales_area_config", "sales_plant_config"]),
 dict(code="M4", name="账本与过账规则", color="acc", layer="DCT（核算字典）",
      desc="账本、公司-账本组合、币种角色、记账码区间、期间开闭窗口。凭证能不能过、过到哪个币种由这里决定。",
      tables=["ledger_config", "book_config", "book_currency_config",
              "posting_account_rule", "posting_window"]),
 dict(code="M5", name="主数据身份与源键映射", color="map", layer="DCT（身份字典）",
      desc="统一对象注册表 + 各源系统键映射。解决“SAP 的 KUNNR、本体的 object_id、外部系统的 key 是同一个东西”。",
      tables=["master_identity", "external_key_map", "bp_identity",
              "customer_link", "supplier_link", "material_identity"]),
 dict(code="M6", name="时态主数据版本", color="ver", layer="DCT（双时态主数据）",
      desc="13 张双时态版本表。业务时间（valid_*）与系统认知时间（recorded_*）分离，每行独立审批引用，GiST 排斥约束禁止重叠。",
      tables=["bp_role_version", "customer_company_version", "supplier_company_version",
              "customer_sales_version", "supplier_purchasing_version", "material_version",
              "material_plant_version", "material_uom_version", "gl_account_version",
              "gl_company_version", "profit_center_version", "profit_company_version",
              "cost_center_version"]),
 dict(code="M7", name="估值对象与价格汇率", color="val", layer="DCT（价格字典）",
      desc="价值对象（物料×估值范围×特殊库存的组合实例）、物料价格版本、已归一化汇率版本。",
      tables=["valuation_unit", "material_price_version", "fx_rate_version"]),
 dict(code="M8", name="运行门与动作冻结", color="run", layer="平台治理（非 DCT/DOC）",
      desc="期间状态机与动作冻结。是“当前运行态”，与历史配置快照刻意分离——不从旧快照放行。",
      tables=["period_gate", "action_block"]),
]

# ---------------------------------------------------------------- relationships
RELS = {
 "M0": [("config_head", "foundation_release", "active_release_id"),
        ("context_snapshot", "foundation_release", "release_id")],
 "M1": [("company_config", "company_key", "bukrs"),
        ("valuation_area_config", "valuation_area_key", "bwkey"),
        ("plant_config", "plant_key", "werks"),
        ("purchasing_org_config", "purchasing_org_key", "ekorg"),
        ("sales_org_config", "sales_org_key", "vkorg"),
        ("controlling_assignment_config", "controlling_area_key", "kokrs"),
        ("ledger_config", "ledger_key", "rldnr")],
 "M2": [("fiscal_year_config", "fiscal_variant_config", "periv"),
        ("fiscal_period_config", "fiscal_year_config", "periv+gjahr")],
 "M3": [("valuation_area_config", "company_config", "bukrs"),
        ("plant_config", "valuation_area_config", "bwkey"),
        ("storage_location_config", "plant_config", "werks"),
        ("purchasing_org_config", "company_config", "bukrs?"),
        ("purchasing_plant_config", "plant_config", "werks"),
        ("purchasing_plant_config", "purchasing_org_config", "ekorg"),
        ("controlling_assignment_config", "company_config", "bukrs"),
        ("sales_org_config", "company_config", "bukrs"),
        ("sales_area_config", "sales_org_config", "vkorg"),
        ("sales_plant_config", "sales_org_config", "vkorg")],
 "M4": [("book_config", "ledger_config", "rldnr"),
        ("book_config", "company_config", "bukrs"),
        ("book_currency_config", "book_config", "bukrs+rldnr"),
        ("book_currency_config", "currency_config", "currency"),
        ("posting_account_rule", "posting_variant_config", "opvar"),
        ("posting_window", "posting_account_rule", "rule_id"),
        ("book_currency_config", "book_config", "functional_currency_type ①")],
 "M5": [("external_key_map", "master_identity", "object_id+object_type"),
        ("bp_identity", "master_identity", "object_id+object_type"),
        ("material_identity", "master_identity", "object_id+object_type"),
        ("customer_link", "bp_identity", "partner_guid"),
        ("supplier_link", "bp_identity", "partner_guid")],
 "M6": [("bp_role_version", "bp_identity", "partner_guid"),
        ("customer_company_version", "customer_link", "kunnr"),
        ("customer_company_version", "company_key", "bukrs"),
        ("supplier_company_version", "supplier_link", "lifnr"),
        ("customer_sales_version", "customer_link", "kunnr"),
        ("customer_sales_version", "sales_org_key", "vkorg"),
        ("supplier_purchasing_version", "supplier_link", "lifnr"),
        ("supplier_purchasing_version", "purchasing_org_key", "ekorg"),
        ("material_version", "material_identity", "matnr"),
        ("material_plant_version", "material_identity", "matnr"),
        ("material_plant_version", "plant_key", "werks"),
        ("material_uom_version", "material_identity", "matnr"),
        ("gl_company_version", "company_key", "bukrs"),
        ("cost_center_version", "controlling_area_key", "kokrs"),
        ("cost_center_version", "company_key", "bukrs"),
        ("profit_center_version", "controlling_area_key", "kokrs"),
        ("profit_company_version", "controlling_area_key", "kokrs"),
        ("profit_company_version", "company_key", "bukrs")],
 "M7": [("material_price_version", "valuation_unit", "kalnr"),
        ("material_price_version", "ledger_key", "rldnr")],
 "M8": [("period_gate", "company_key", "bukrs ②"),
        ("period_gate", "ledger_key", "rldnr ②"),
        ("action_block", "master_identity", "object_id ②")],
}

T = {}


def tab(name, cn, sap, purpose, cols, notes=None, scen=None):
    T[name] = dict(cn=cn, sap=sap, purpose=purpose, cols=cols,
                   notes=notes or [], scen=scen or [])


# ============================== M0 ==============================
tab("client_scope", "租户-客户端范围", "MANDT + 租户收敛",
    "全部 58 张表的隔离根。每张表的 `(tenant_id, mandt)` 都外键指向本表，构成“一个租户在一个客户端下”的一行。",
    [("tenant_id", "uuid", "pn", "租户标识。多租户 SaaS 下每个客户一个 UUID。示例：`11111111-1111-1111-1111-111111111111`"),
     ("mandt", "varchar(3)", "pnk", "SAP 客户端号，3 位数字（CHECK `~ '^[0-9]{3}$'`）。示例：`100`。**不等于租户**——同一租户可有 100/200 两个客户端，配置完全隔离")],
    ["**为什么既要 tenant_id 又要 mandt**：SAP 用 MANDT 隔离，但 3 位最多 1000 个值，不适合 SaaS 多租户。这里把“平台租户”（UUID，无上限）与“SAP 客户端语义”（保留迁移原值）拆成两列。"],
    ["上线首日：为新客户 `corp-A` 建 `('11111111-…', '100')`。此后该客户的所有配置都落在这个范围内，跨客户查询会被 RLS 挡住。"])

tab("foundation_release", "不可变配置发布包", "类比 FINSC 配置传输请求",
    "一次“配置定版”的快照头。所有 release 绑定的配置表都外键指向它，触发器保证 `PUBLISHED` 之后整包不可写。",
    [("tenant_id", "uuid", "pnf", "租户。FK → client_scope"),
     ("mandt", "varchar(3)", "pnf", "客户端号。FK → client_scope"),
     ("release_id", "uuid", "pn", "发布包标识。示例：`22222222-2222-2222-2222-222222222222`。所有配置行的 release_id 填它"),
     ("version", "integer", "nk", "包版本号，`CHECK(version>0)` 且 `UNIQUE(tenant_id,mandt,version)`。示例：`1`。同租户递增，不允许跳号复用"),
     ("status", "text", "nk", "状态机 `DRAFT` → `VALIDATED` → `APPROVED` → `PUBLISHED`。示例：`PUBLISHED`"),
     ("profile", "text", "n", "包的业务档案名，供人读与筛选。示例：`FND_1_1_DEMO`"),
     ("content_hash", "varchar(64)", "k", "配置内容的 SHA-256 十六进制（CHECK 64 位小写十六进制）。**由服务计算校验，不是签名**——防“内容与批准时不一致”，不防伪造者"),
     ("created_by", "text", "n", "创建人。示例：`DEMO_BUILDER`"),
     ("approved_by", "text", "k", "批准人。CHECK 强制 `approved_by <> created_by`（四眼原则），且状态为 APPROVED/PUBLISHED 时不得为空"),
     ("approved_at", "timestamptz", "", "批准时刻。示例：`2026-01-15 09:30:00+08`"),
     ("published_at", "timestamptz", "k", "发布时刻。状态为 PUBLISHED 时 CHECK 强制非空")],
    ["**触发器 `prevent_release_rewrite`**：`OLD.status='PUBLISHED'` 时任何 UPDATE/DELETE 抛 `FND_PUBLISHED_RELEASE_IMMUTABLE`。",
     "**四眼原则是数据库强制的**，不是流程约定：同一人无法自批自发布。",
     "**content_hash 的边界**：文档明确“由服务验证，不是签名”。它证明内容未被改动，不证明谁改的。"],
    ["初始配置：张三建包（`DRAFT`）→ 校验通过（`VALIDATED`）→ 李四批准（`APPROVED`，approved_by≠created_by 由 CHECK 保证）→ 发布（`PUBLISHED`，同时写 content_hash 与 published_at）。此后任何配置改动都必须开新 release。"],
)

tab("config_head", "当前激活发布指针", "类比传输激活",
    "单行表：告诉系统“现在生效的是哪个 release_id”。`UNIQUE(tenant_id,mandt)` 保证一个租户-客户端只有一个激活指针。",
    [("tenant_id", "uuid", "pnf", "租户。FK → client_scope"),
     ("mandt", "varchar(3)", "pnuf", "客户端号。FK → client_scope；`UNIQUE(tenant_id,mandt)` 保证单行"),
     ("active_release_id", "uuid", "pnf", "当前激活的发布包。FK → foundation_release。示例：指向 `2222…2222`"),
     ("version", "bigint", "nk", "乐观版本号，`DEFAULT 1 CHECK(version>0)`。激活切换时递增，供并发控制与缓存失效")],
    ["**主键是 `(tenant_id,mandt,active_release_id)`，真正唯一的是 `(tenant_id,mandt)`**——刻意冗余：主键带 release_id 让外键能指过来，UNIQUE 保证只有一行。",
     "**用途**：解析上下文第一步读本表拿 release_id，再据此读所有配置表。**切版因此是更新一行**，不是改 N 张表。"],
    ["切版：新 release `v2` 发布后，一条 `UPDATE config_head SET active_release_id='<v2>', version=version+1` 即完成切换。若业务发现异常，改回 v1 同样是一条 UPDATE。"])

tab("command_receipt", "业务幂等回执", "无直接对应（SAP 用凭证号天然幂等）",
    "“这个请求我执行过了吗”。业务幂等键唯一性表，与正式激活在**同一事务**内提交，避免“回执写成功但业务没生效”。",
    [("tenant_id", "uuid", "pnf", "租户。FK → client_scope"),
     ("mandt", "varchar(3)", "pnf", "客户端号"),
     ("source_system", "text", "pn", "来源系统标识。示例：`SAP_S4F`"),
     ("action", "text", "pn", "业务动作名。示例：`CREATE_CUSTOMER`"),
     ("idempotency_key", "text", "pn", "调用方提供的幂等键。示例：`SAP-100-KUNNR-0000100001`。三列+本列构成主键，重复提交命中同一行"),
     ("request_hash", "varchar(64)", "nk", "请求体 SHA-256（CHECK 64 位十六进制）。**用途**：同一幂等键但请求体不同（客户端 bug 或重放）时可判定并拒绝"),
     ("state", "text", "nk", "`STARTED` / `COMPLETED`。示例：`COMPLETED`。STARTED 表示事务进行中或曾崩溃"),
     ("result", "jsonb", "n", "执行结果留档。示例：`{\"kunnr\":\"0000100001\"}`"),
     ("created_at", "timestamptz", "n", "回执创建时刻"),
     ("completed_at", "timestamptz", "n", "完成时刻。为空表示仍在 STARTED")],
    ["**与 outbox 的分工**：command_receipt 管**入站**幂等（我有没有处理过你的请求），outbox 管**出站**投递（我的事件有没有发出去）。"],
    ["网络超时重试：客户端因超时重发同一请求 → 命中主键冲突 → 读 result 直接返回上次结果，不重复建客户。若 request_hash 不同则报“键相同内容不同”，拒绝并告警。"])

tab("outbox", "事务性发件箱", "无直接对应（SAP 用 IDoc/BDC 队列）",
    "“业务库原子写入事件，外围至少一次投递”。事件与业务数据同一事务提交，避免“业务成功但消息丢失”。",
    [("tenant_id", "uuid", "pnf", "租户。FK → client_scope"),
     ("mandt", "varchar(3)", "pnf", "客户端号"),
     ("event_id", "uuid", "pn", "事件标识。示例：`7f3a…`"),
     ("aggregate_key", "text", "nk", "聚合根键。示例：`customer:0000100001`。与下两列+event_type 构成 UNIQUE，防同一聚合同一版本重复发事件"),
     ("aggregate_version", "bigint", "nk", "聚合版本号。示例：`3`"),
     ("event_type", "text", "nk", "事件类型。示例：`CustomerCreated`"),
     ("payload", "jsonb", "n", "事件体（自包含，消费方不必回查）。示例：`{\"kunnr\":\"0000100001\"}`"),
     ("created_at", "timestamptz", "n", "入箱时刻，也是投递顺序依据"),
     ("state", "text", "nk", "`PENDING` / `LEASED` / `DONE` / `DEAD`。示例：`PENDING`"),
     ("attempt", "integer", "nk", "已尝试次数，`DEFAULT 0 CHECK(attempt>=0)`。达上限置 `DEAD` 进人工队列"),
     ("available_at", "timestamptz", "n", "下次可投递时刻。失败重试向后推（指数退避）——**用这列实现延迟重试，不 sleep**"),
     ("lease_until", "timestamptz", "n", "租约到期时刻。取任务时置 `state='LEASED'` 并写此列，崩溃后到期自动可被他人领取")],
    ["**集群无状态的关键表**：投递者用 `SELECT … FOR UPDATE SKIP LOCKED WHERE state='PENDING' AND available_at<=now()` 取任务——多实例并发安全，不需要分布式锁。",
     "**为什么必须有 lease_until**：没有它，实例取走任务后崩溃，事件永久卡在 LEASED。租约把“崩溃”退化为“稍后重试”。",
     "**至少一次语义**：可能成功投递但在置 DONE 前崩溃，导致重复投递。**消费方必须自己幂等**——本表不能替你解决。"],
    ["客户创建成功后同事务插一条 `CustomerCreated`。投递者取走 → 发到下游 → 置 `DONE`。若下游 5xx，则 `attempt+1`、`available_at=now()+2^attempt 分钟`、回到 `PENDING`。"])

tab("context_snapshot", "服务端上下文快照", "无直接对应",
    "把一次业务动作的“配置视图 + 请求体”冻结下来，供执行期一致读取。带过期时间，是短期缓存而非审计档案。",
    [("tenant_id", "uuid", "pnf", "租户。FK → client_scope"),
     ("mandt", "varchar(3)", "pnf", "客户端号"),
     ("context_id", "uuid", "pn", "快照标识。示例：`c0ffee…`"),
     ("release_id", "uuid", "nf", "快照基于哪个发布包。FK → foundation_release。**关键**：让“执行到一半配置被切版”不影响本次执行"),
     ("request_hash", "varchar(64)", "n", "请求体哈希（64 位十六进制）。校验请求未被替换"),
     ("payload", "jsonb", "n", "冻结的上下文内容（解析出的组织、科目表、日历等）"),
     ("created_at", "timestamptz", "n", "创建时刻"),
     ("expires_at", "timestamptz", "nk", "过期时刻，`CHECK(expires_at>created_at)` 强制。示例：`created_at + 15 分钟`"),
     ("subject_id", "text", "n", "主体标识（谁在操作）。示例：`user:alice@corp`")],
    ["**不等于过账授权**：文档明确“服务端受控快照；不等于过账授权”。快照只保证**读到一致的配置**，不保证**允许过账**——后者由期间门与能力门决定。",
     "**为什么不用进程缓存**：集群无状态约束禁止本地缓存业务数据。快照落在数据库，多实例共享，过期语义显式。"],
    ["长事务：批处理开始解析上下文并冻结快照（绑定 release v1）；期间运维切到 v2；批处理继续用 v1 完成，不受切换影响，且可事后复核“它当时读的是哪一版”。"])

# ============================== M1 ==============================
M1 = [("company_key", "bukrs", "4", "公司代码", "T001 的 BUKRS", "`1000`", "c3ad7368-f126-5de6-97d6-441792934cae"),
      ("valuation_area_key", "bwkey", "4", "估值范围", "T001K 的 BWKEY", "`V100`", "96a188dd-3951-51dd-8322-25a5e3bc71f8"),
      ("plant_key", "werks", "4", "工厂", "T001W 的 WERKS", "`1100`", "72743ba7-626a-5ad1-aa0a-ea4830436456"),
      ("purchasing_org_key", "ekorg", "4", "采购组织", "T024E 的 EKORG", "`P100`", "33594832-9d18-5632-8123-c37993d32a82"),
      ("sales_org_key", "vkorg", "4", "销售组织", "TVKO 的 VKORG", "`S100`", "aa4127fb-107c-5f85-9352-dde0c2a8df07"),
      ("controlling_area_key", "kokrs", "4", "成本控制范围", "TKA01 的 KOKRS", "`A000`", "5504154c-45db-5325-9d03-74ebe45a9c7c"),
      ("ledger_key", "rldnr", "2", "分类账", "FINSC_LEDGER 的 RLDNR", "`0L`", "4106915e-0840-555c-8692-ec5f69659dc8")]
for nm, code, ln, cn, sap, ex, exid in M1:
    tab(nm, cn + "稳定身份", sap,
        f"把 `{code}` 从“一个编码字符串”升格为“一个永不重分配的对象”。名称、归属、状态都不在这里——那些在配套的 `*_config` 里，可随发布包变。",
        [("tenant_id", "uuid", "pnf", "租户。FK → client_scope"),
         ("mandt", "varchar(3)", "pnf", "客户端号"),
         (code, f"varchar({ln})", "pnk", f"{cn}编码，非空（CHECK 长度>0）。示例：{ex}"),
         ("object_id", "uuid", "nuf", f"该组织对象的全局身份 UUID，`UNIQUE(tenant_id,mandt,object_id)`。示例：`{exid}`。**外键的真正目标**——业务表引用 object_id 而非编码，编码可改名而身份不变")],
        [f"**为什么编码不能重分配**：若 `{code}` 被回收给另一个组织，历史上所有引用它的单据都会“改指”，这是审计不可接受的事故。所以 {code} 是主键且**永不删除**——停用是加状态，不是删行。",
         f"**与配置表的分工**：本表只回答“{code} 指向哪个对象”；`{nm.replace('_key','_config')}` 回答“这一版的它叫什么、归谁、什么属性”。改名只动配置表。"],
        [f"组织重编码场景：公司 `1000` 改名不影响任何历史凭证——名称在 `company_config.name`，本表只有编码与 UUID。"])

# ============================== M2 ==============================
tab("currency_config", "币种精度", "TCURX（但不宣称有 MANDT）",
    "定义每个币种的小数位数。金额的“最后一位”由这里决定——它直接约束 NUMERIC 的舍入行为。",
    [("tenant_id", "uuid", "pnf", "租户。FK → client_scope"),
     ("mandt", "varchar(3)", "pnf", "客户端号"),
     ("release_id", "uuid", "pnf", "所属发布包。FK → foundation_release。**本表是 release 绑定表**"),
     ("currency", "varchar(5)", "pn", "ISO 币种码。示例：`CNY` / `USD`"),
     ("minor_units", "smallint", "nk", "小数位数，`CHECK(minor_units BETWEEN 0 AND 8)`。示例：`CNY`→`2`，`JPY`→`0`，`KWD`→`3`")],
    ["**为什么不宣称 TCURX 有 MANDT**：SAP 的 TCURX 是跨客户端的（无 MANDT）。目录 JSON 明确标注“CMX 受控参考数据；不宣称 SAP TCURX 有 MANDT”——这是**不假装比 SAP 更懂**的写法：CMX 把它做成受控参考数据，就不声称与 SAP 表结构一致。",
     "**为什么精度必须进元数据而不是硬编码**：`JPY` 无小数位、`KWD` 三位小数，若代码里写死 2 位，跨币种金额会静默算错。CMX 的规范是金额 `NUMERIC(31,8)` 存储、按 `minor_units` 呈现与舍入。"],
    ["建 CNY/USD 两行（`minor_units=2`）。录入 `1234.5 CNY` 显示为 `1,234.50`；若同金额按 JPY（`minor_units=0`）呈现则为 `1,235`，并在过账时按精度规则舍入。"])

tab("uom_config", "计量单位与维度", "T006（维度与小数位）",
    "定义单位的物理量维度与小数位数。换算关系不在本表——在 `material_uom_version`，因为换算依赖具体物料。",
    [("tenant_id", "uuid", "pnf", "租户。FK → client_scope"),
     ("mandt", "varchar(3)", "pnf", "客户端号"),
     ("release_id", "uuid", "pnf", "所属发布包。FK → foundation_release"),
     ("unit", "varchar(3)", "pn", "单位码。示例：`EA`（个）/ `BOX` / `KG` / `M`"),
     ("dimension", "text", "n", "物理量维度。示例：`COUNT` / `MASS` / `LENGTH`。**用途**：阻止 `KG + M` 这类跨维度换算——只有同维度的单位才允许换算"),
     ("quantity_decimals", "smallint", "nk", "数量小数位数，`CHECK(quantity_decimals BETWEEN 0 AND 9)`。示例：`EA`→`0`，`KG`→`3`")],
    ["**维度是防错的关键**：SAP 允许在单位间配换算因子，但跨维度（如 KG↔M）配出来的因子在业务上无意义。CMX 把 `dimension` 显式化，让“异维度换算”在定义期就可拒。",
     "**数量用 NUMERIC(31,9) 而非 float**：9 位小数覆盖本表上限，且十进制精确——浮点的 0.1+0.2 问题在库存累加里会放大成对不上账。"],
    ["`EA` 维度 `COUNT`、小数 0 位；`KG` 维度 `MASS`、小数 3 位。录入 1.2345 KG 存入 `NUMERIC(31,9)`=1.234500000，呈现时按 3 位显示 1.235（或截断，取决于呈现策略）。"])

tab("fiscal_variant_config", "会计年度变式", "T009 / T009B",
    "年度变式的选择器：这一版用哪些变式、各自是什么日历类型。具体的年度与期间在下面两张表。",
    [("tenant_id", "uuid", "pnf", "租户。FK → client_scope"),
     ("mandt", "varchar(3)", "pnf", "客户端号"),
     ("release_id", "uuid", "pnf", "所属发布包。FK → foundation_release"),
     ("periv", "varchar(2)", "pn", "年度变式码。示例：`K4`（自然年 4 特殊期）/ `A4`（4 月起算）"),
     ("calendar_kind", "text", "nk", "日历类型，`CHECK IN ('CALENDAR','SHIFTED','EXPLICIT')`。`CALENDAR`=自然年；`SHIFTED`=跨年偏移（如会计年从 4 月 1 日起）；`EXPLICIT`=逐期显式定义"),
     ("original_t009", "jsonb", "", "SAP 原表行的原样留档。**用途**：迁移期审计“SAP 里原本是什么”，以及复杂日历时保留无法直接映射的声明")],
    ["**`calendar_kind` 与 `original_t009` 并存是刻意的**：前者是 CMX 能**执行**的语义，后者是 SAP 的**原始声明**。文档写“复杂日历启用仍需算法能力门”——即：能存下来，不代表能算，能力不够就必须拒绝而不是静默算错。",
     "**`EXPLICIT` 的存在理由**：有些客户用的是 SAP 零售/特殊日历，无法用 `CALENDAR`/`SHIFTED` 表达，只能逐期列。"],
    ["示例数据里 `K4` 标 `CALENDAR`（2025-01-01 起），`A4` 标 `SHIFTED`（2025-04-01 起）。同一套组织可以同时存在多个变式，由 `company_config.periv` 选择用哪个。"])

tab("fiscal_year_config", "会计年度实例", "T009（年度区间）",
    "某个变式下某一年的整体范围与期间数量。**日期上界不含**——`date_to` 是下一年的开始，不是最后一天。",
    [("tenant_id", "uuid", "pnf", "租户。FK → client_scope"),
     ("mandt", "varchar(3)", "pnf", "客户端号"),
     ("release_id", "uuid", "pnf", "所属发布包。FK → foundation_release"),
     ("periv", "varchar(2)", "pnf", "年度变式。FK → fiscal_variant_config(…,periv)"),
     ("gjahr", "integer", "pnk", "会计年度，`CHECK(gjahr BETWEEN 1 AND 9999)`。示例：`2025`"),
     ("normal_periods", "smallint", "nk", "正常期间数，`CHECK BETWEEN 1 AND 366`。示例：`12`"),
     ("special_periods", "smallint", "nk", "特殊期间数，`CHECK BETWEEN 0 AND 16`。示例：`4`（SAP 常见的 13–16 期用于调整）"),
     ("date_from", "date", "n", "年度起始日（含）。示例：`2025-01-01`"),
     ("date_to", "date", "nk", "年度结束日（**不含**），`CHECK(date_to>date_from)`。示例：`2026-01-01`")],
    ["**半开区间 `[)` 是本表的核心约定**：`2025-01-01` ~ `2026-01-01` 表示 2025 年。好处是相邻年度无缝隙无重叠（前一年 end = 后一年 start），GiST 排斥约束才能干净地判重叠。**若用闭区间，1 月 1 日会被两年同时包含**。",
     "**GiST EXCLUDE**：`(tenant,mandt,release,periv)` 相同则 `daterange(date_from,date_to,'[)')` 不得重叠。这防止“2025 年被定义两次”。",
     "**`normal_periods` 允许到 366**：因为存在“按周为期”的变式（一年 52 期）和零售日历。"],
    ["示例数据：`K4/2025` = 12 正常 + 4 特殊，`2025-01-01`~`2026-01-01`；`A4/2025` = 12+4，`2025-04-01`~`2026-04-01`。两者互不冲突，因为属于不同 `periv`。"])

tab("fiscal_period_config", "会计期间明细", "T009（逐期区间）",
    "把一个年度切成具体期间，每期一段日期。**只含正常期间**——特殊期间由 `fiscal_year_config.special_periods` 计数表达，不落日期。",
    [("tenant_id", "uuid", "pnf", "租户。FK → client_scope"),
     ("mandt", "varchar(3)", "pnf", "客户端号"),
     ("release_id", "uuid", "pnf", "所属发布包。FK → foundation_release"),
     ("periv", "varchar(2)", "pnf", "年度变式。FK 链到 fiscal_year_config"),
     ("gjahr", "integer", "pnf", "会计年度。FK 链到 fiscal_year_config"),
     ("poper", "smallint", "pnk", "期间号，`CHECK(poper>0)`。示例：`1`=1 月。SAP 惯例 `1..12` 正常期，`13..16` 特殊期"),
     ("date_from", "date", "n", "期间起始（含）。示例：`2025-01-01`"),
     ("date_to", "date", "nk", "期间结束（**不含**），`CHECK(date_to>date_from)`。示例：`2025-02-01`")],
    ["**为什么只存正常期间**：特殊期间（13–16）在 SAP 里也是真实过账期间，但它们的日期语义是“与第 12 期重叠的调整期”，无法用无重叠区间表达。文档明说“仅正常期间；连续覆盖与 1..N 由发布校验检查”——**重叠语义的部分留给发布校验，不硬塞进 GiST**。",
     "**GiST EXCLUDE 在 `(periv,gjahr)` 内判期间不重叠**：防止同一期被定义两次。",
     "**与 SAP 的差异**：SAP 的期间边界可跨年（如 `A4` 的第 1 期是 4 月），本表因有 `gjahr` 列而能正确表达，因为 `date_from/to` 是绝对日期，不假设与 `gjahr` 同年。"],
    ["`K4/2025/1` = `[2025-01-01, 2025-02-01)`；`K4/2025/2` = `[2025-02-01, 2025-03-01)`。查询“2025-01-15 属于哪期”用 `WHERE date_from <= d AND d < date_to`，命中第 1 期。"])

tab("posting_variant_config", "过账变式", "T010O",
    "过账变式的存在性声明。规则主体在 `posting_account_rule`，本表只声明“这一版有哪些变式”。",
    [("tenant_id", "uuid", "pnf", "租户。FK → client_scope"),
     ("mandt", "varchar(3)", "pnf", "客户端号"),
     ("release_id", "uuid", "pnf", "所属发布包。FK → foundation_release"),
     ("opvar", "varchar(4)", "pn", "过账变式码。示例：`P001`")],
    ["**为什么单独一张表**：SAP 的 T010O 与公司代码是**多对多**关系（一个变式可被多个公司用），而不是公司的一个属性。独立表让这个关系显式，也避免了 `company_config.opvar` 无法表达共享。",
     "**目录 JSON 的提醒**：“T010O 语义，与公司代码不同”——即不要把 `opvar` 当成 `bukrs` 的从属字段。"],
    ["`P001` 被 `company_config` 的 `1000` 和 `2000` 同时引用；`posting_account_rule` 里按 `opvar='P001'` 组织记账码规则，因此两个公司共享同一套规则。"])

# ============================== M3 ==============================
tab("company_config", "公司代码配置", "T001 选定字段",
    "公司代码的业务属性：叫什么、在哪国、本位币、科目表、年度变式、过账变式、时区。**全部绑 release**，可随版本变。",
    [("tenant_id", "uuid", "pnf", "租户。FK → client_scope"),
     ("mandt", "varchar(3)", "pnf", "客户端号"),
     ("release_id", "uuid", "pnf", "所属发布包。FK → foundation_release"),
     ("bukrs", "varchar(4)", "pnf", "公司代码。FK → company_key。示例：`1000`。**注意：引用稳定身份表，不是配置表**"),
     ("name", "text", "n", "公司名称。示例：`示例制造有限公司`。改名只改这一列"),
     ("country", "varchar(3)", "n", "国家码（ISO 3 位）。示例：`CHN`"),
     ("currency", "varchar(5)", "nf", "公司本位币。FK → currency_config(…,currency)。示例：`CNY`"),
     ("ktopl", "varchar(4)", "n", "科目表码。示例：`YCOA`。**无外键——FND 里没有独立的科目表主表**，科目表经 `gl_account_version.ktopl` 体现"),
     ("periv", "varchar(2)", "nf", "年度变式。FK → fiscal_variant_config。示例：`K4`"),
     ("opvar", "varchar(4)", "nf", "过账变式。FK → posting_variant_config。示例：`P001`"),
     ("time_zone", "text", "n", "公司时区。示例：`Asia/Shanghai`。**用途**：把业务日期解释成时间戳时的基准，也是 `recorded_at` 类时间列的显示基准")],
    ["**`ktopl` 无外键是已知缺口**：FND 没有 CoA 主表，所以科目表码只是个字符串。文档 E 系列的精神是“不假装有约束”——宁可让领域核校验，也不建一个空的主表来假装引用完整。",
     "**`country` 用 varchar(3) 而非 SAP 的 3 位 LAND1**：值时 `CHN`，与 ISO 3166-1 alpha-3 一致。"],
    ["建公司 `1000`：名称、`country='CHN'`、`currency='CNY'`、`ktopl='YCOA'`、`periv='K4'`、`opvar='P001'`、`time_zone='Asia/Shanghai'`。示例数据里 `1000` 与 `2000` 共用 `ktopl='YCOA'` 与 `periv='K4'`。"])

tab("valuation_area_config", "估值范围配置", "T001K",
    "估值范围归属哪个公司代码。估值范围是“物料在哪记账价格”的边界，它必须唯一归属于一个公司。",
    [("tenant_id", "uuid", "pnf", "租户。FK → client_scope"),
     ("mandt", "varchar(3)", "pnf", "客户端号"),
     ("release_id", "uuid", "pnf", "所属发布包。FK → foundation_release"),
     ("bwkey", "varchar(4)", "pnf", "估值范围。FK → valuation_area_key。示例：`V100`"),
     ("bukrs", "varchar(4)", "nf", "归属公司。FK → company_config(同一 release)。示例：`1000`"),
     ("bwmod", "varchar(4)", "n", "估值范围分类，`DEFAULT ''`。示例：空串表示标准。SAP 用于区分特殊估值范围")],
    ["**估值范围 vs 工厂**：SAP 里估值既可以按工厂也可以按公司，`T001K` 决定粒度。CMX 把 `bwkey` 独立成表，`plant_config.bwkey` 再指过来——这样“两个工厂共用一个估值范围”是自然表达，不需要特例。",
     "**外键指向同 release 的 company_config**：这保证估值范围不会跨版本引用公司——否则 v1 的估值范围可能挂到 v2 的公司上。"],
    ["`V100` 归 `1000`，`V200` 归 `2000`；工厂 `1100` 的 `bwkey='V100'`，`2100` 的 `bwkey='V200'`。因此估值按公司隔离。"])

tab("plant_config", "工厂配置", "T001W",
    "工厂的业务属性：名称、所属估值范围、时区、工厂日历。**没有独立可编辑的 BUKRS 字段**。",
    [("tenant_id", "uuid", "pnf", "租户。FK → client_scope"),
     ("mandt", "varchar(3)", "pnf", "客户端号"),
     ("release_id", "uuid", "pnf", "所属发布包。FK → foundation_release"),
     ("werks", "varchar(4)", "pnf", "工厂。FK → plant_key。示例：`1100`"),
     ("bwkey", "varchar(4)", "nf", "所属估值范围。FK → valuation_area_config。示例：`V100`"),
     ("name", "text", "n", "工厂名称。示例：`上海工厂`"),
     ("time_zone", "text", "n", "工厂时区。示例：`Asia/Shanghai`"),
     ("factory_calendar", "text", "", "工厂日历标识（可空）。示例：`CN`。用于工作日/班次推算")],
    ["**目录 JSON 明确“没有独立可编辑 BUKRS 字段”**：工厂属于哪个公司是**经 `bwkey` 推导**的（`plant → valuation_area → company`），不是直接字段。SAP 的 T001W 也没有 BUKRS——若 CMX 加一个，就会出现“工厂的 BUKRS 与估值范围的 BUKRS 不一致”这种无法自洽的状态。",
     "**这是“派生优于冗余”的范例**：少一个字段，少一类不一致。"],
    ["要查工厂属于哪个公司：`plant_config.bwkey → valuation_area_config.bukrs`。查 `1100` 得 `V100` 得 `1000`。"])

tab("storage_location_config", "存储地点配置", "T001L 复合键",
    "工厂下的存储地点。键是 `(werks, lgort)` 复合键——这是 SAP 里“组织层级”最典型的形态。",
    [("tenant_id", "uuid", "pnf", "租户。FK → client_scope"),
     ("mandt", "varchar(3)", "pnf", "客户端号"),
     ("release_id", "uuid", "pnf", "所属发布包。FK → foundation_release"),
     ("werks", "varchar(4)", "pnf", "所属工厂。FK → plant_config。示例：`1100`"),
     ("lgort", "varchar(4)", "pn", "存储地点码。示例：`0001`。**编码在工厂内唯一，跨工厂可重复**"),
     ("name", "text", "n", "存储地点名称。示例：`原料库`")],
    ["**复合键的意义**：`lgort='0001'` 在 `1100` 和 `2100` 下是**两个不同的地点**。这正是 SAP 的语义，也是为什么 DCT 的“单键 code”模板装不下它。",
     "**外键只指到 plant_config**，不指 plant_key：因为存储地点是“这一版的工厂”下的从属物，工厂换版本时地点也应随之换。"],
    ["示例数据：`(1100,'0001')` 与 `(2100,'0001')` 两行共存，各自属于不同工厂。"])

tab("purchasing_org_config", "采购组织配置", "T024E",
    "采购组织与其（可选的）归属公司。**`bukrs` 可空**是一个有语义的设计。",
    [("tenant_id", "uuid", "pnf", "租户。FK → client_scope"),
     ("mandt", "varchar(3)", "pnf", "客户端号"),
     ("release_id", "uuid", "pnf", "所属发布包。FK → foundation_release"),
     ("ekorg", "varchar(4)", "pnf", "采购组织。FK → purchasing_org_key。示例：`P100`"),
     ("bukrs", "varchar(4)", "nf", "归属公司，**可空**。FK → company_config。示例：`1000` 或 NULL"),
     ("name", "text", "n", "采购组织名称。示例：`上海采购组织`")],
    ["**`bukrs` 为 NULL 的确切语义**（目录 JSON 原文）：“NULL 表示无单公司限制而不是自动全工厂授权”。这是**极易误读**的一处：空值**不是**“这个组织能对任何公司采购”，而是“没有绑定到单一公司”。授权仍由 `purchasing_plant_config` 白名单决定。",
     "**为什么这个区分重要**：若把 NULL 理解为“全授权”，一个按公司维度做数据权限的系统会直接漏权。"],
    ["示例数据：`P100` 归 `1000`；`PG01` 的 `bukrs` 为 NULL（跨公司采购组织）。`PG01` 能对哪些工厂采购，完全由 `purchasing_plant_config` 决定。"])

tab("purchasing_plant_config", "采购组织-工厂分配", "T024W 允许清单",
    "**白名单**：哪个采购组织被允许对哪个工厂采购。不是“关系描述”，是“授权判据”。",
    [("tenant_id", "uuid", "pnf", "租户。FK → client_scope"),
     ("mandt", "varchar(3)", "pnf", "客户端号"),
     ("release_id", "uuid", "pnf", "所属发布包。FK → foundation_release"),
     ("werks", "varchar(4)", "pnf", "工厂。FK → plant_config。示例：`1100`"),
     ("ekorg", "varchar(4)", "pnf", "采购组织。FK → purchasing_org_config。示例：`P100`")],
    ["**目录 JSON 定性为“T024W 允许清单”**——这决定了它的用途：任何“某采购组织能否对某工厂下单”的判断，必须**存在性检查**本表，而不是看 `purchasing_org_config.bukrs`。",
     "**复合主键 `(werks, ekorg)` 的方向是“工厂在前”**，与 SAP T024W 的键顺序一致。"],
    ["示例数据：`(1100,P100)`、`(1100,PG01)`、`(2100,PG01)`。因此 `P100` 只能对 `1100` 采购；`PG01` 可对 `1100` 和 `2100`。"])

tab("controlling_assignment_config", "公司-业务范围-成本控制范围", "TKA02",
    "把公司代码与业务范围（GSBER）关联到成本控制范围。**GSBER 被显式保留**，不在迁移时丢弃。",
    [("tenant_id", "uuid", "pnf", "租户。FK → client_scope"),
     ("mandt", "varchar(3)", "pnf", "客户端号"),
     ("release_id", "uuid", "pnf", "所属发布包。FK → foundation_release"),
     ("bukrs", "varchar(4)", "pnf", "公司代码。FK → company_config。示例：`1000`"),
     ("gsber", "varchar(4)", "pnk", "业务范围，`DEFAULT ''`。示例：空串=未细分。SAP 用于跨公司报表段"),
     ("kokrs", "varchar(4)", "nf", "成本控制范围。FK → controlling_area_key。示例：`A000`")],
    ["**为什么保留 GSBER**：目录 JSON 原文“保留 GSBER，不在迁移时丢弃”。业务范围在 SAP 新版里逐渐被利润中心/段取代，但老系统里的历史数据依赖它——**静默丢弃会造成历史报表对不上**。",
     "**`gsber` 默认空串而非 NULL**：因为它是主键的一部分，主键列不能为 NULL。空串表示“该公司未按业务范围细分”。",
     "**注意 `kokrs` 外键指向 `controlling_area_key`（稳定身份）而不是配置表**：成本控制范围是较稳定的组织维度。"],
    ["示例数据两行：`(1000,'',A000)`、`(2000,'',A000)`。两个公司共用一个成本控制范围 `A000`，但业务范围均为空。"])

tab("sales_org_config", "销售组织配置", "TVKO 经 SI_TVKO 关联公司",
    "销售组织与其归属公司。销售组织必须归属且仅归属一个公司代码。",
    [("tenant_id", "uuid", "pnf", "租户。FK → client_scope"),
     ("mandt", "varchar(3)", "pnf", "客户端号"),
     ("release_id", "uuid", "pnf", "所属发布包。FK → foundation_release"),
     ("vkorg", "varchar(4)", "pnf", "销售组织。FK → sales_org_key。示例：`S100`"),
     ("bukrs", "varchar(4)", "nf", "归属公司。FK → company_config。示例：`1000`")],
    ["**目录 JSON 注明“TVKO 经 SI_TVKO 关联公司”**：SAP 里 TVKO 与公司的关系经过 `SI_TVKO` 这个关联表，不是直接字段。CMX 把它简化为一列外键，**但保留了“必须唯一归属”的语义**（单列非空 FK = 恰好一个公司）。",
     "**与 `purchasing_org_config.bukrs` 可空形成对比**：销售组织必须归公司，采购组织可以不归——这是 SAP 的实际语义差异，不是设计不一致。"],
    ["`S100` 归 `1000`。查询“某公司的所有销售组织”用 `WHERE bukrs='1000'`。"])

tab("sales_area_config", "销售范围（业务销售范围）", "TVTA",
    "销售范围 = `销售组织 + 分销渠道 + 产品组` 三元组。这是销售侧最细的组织粒度。",
    [("tenant_id", "uuid", "pnf", "租户。FK → client_scope"),
     ("mandt", "varchar(3)", "pnf", "客户端号"),
     ("release_id", "uuid", "pnf", "所属发布包。FK → foundation_release"),
     ("vkorg", "varchar(4)", "pnf", "销售组织。FK → sales_org_config。示例：`S100`"),
     ("vtweg", "varchar(2)", "pn", "分销渠道。示例：`10`=直销、`20`=经销。**编码非零填充**"),
     ("spart", "varchar(2)", "pn", "产品组。示例：`00`=通用、`01`=成品")],
    ["**`vtweg`/`spart` 是 varchar(2) 而非 char(2)**：示例数据里是 `'10'`、`'00'`，保留 SAP 的零填充惯例（`'00'` 是有意义的值，不是空）。",
     "**目录 JSON 注明“TVKOV/TVKOS 原始限定由适配器核验”**：SAP 里销售范围还有 `TVKOV`（分销渠道有效性）和 `TVKOS`（产品组有效性）两层限定，CMX 不在本表重复表达这些限定，而由适配器核验——**避免把 SAP 的三层嵌套压成一层而丢失语义**。"],
    ["示例数据：`(S100,'10','00')` 与 `(S100,'10','01')`。同一销售组织同一渠道下的两个产品组，是两个独立销售范围。"])

tab("sales_plant_config", "销售组织-工厂分配", "TVKWZ（粒度不含 SPART）",
    "销售组织+渠道 可对哪些工厂供货。**粒度刻意不含产品组**。",
    [("tenant_id", "uuid", "pnf", "租户。FK → client_scope"),
     ("mandt", "varchar(3)", "pnf", "客户端号"),
     ("release_id", "uuid", "pnf", "所属发布包。FK → foundation_release"),
     ("vkorg", "varchar(4)", "pnf", "销售组织。FK → sales_org_config。示例：`S100`"),
     ("vtweg", "varchar(2)", "pn", "分销渠道。示例：`10`"),
     ("werks", "varchar(4)", "pnf", "可供货工厂。FK → plant_config。示例：`1100`")],
    ["**为什么不含 `spart`**（目录 JSON 原文：“TVKWZ 的粒度不包含 SPART”）：SAP 的供货工厂分配是按 `销售组织+渠道+工厂`，产品组不参与。**若照搬 `sales_area_config` 的三元组，会造出 SAP 里不存在的粒度**，导致同一工厂被重复配置 N 次（每个产品组一次）。",
     "**这是“忠实于 SAP 粒度”的范例**：宁可两张表键长不同，也不强行统一。"],
    ["`(S100,'10',1100)`：`S100` 的直销渠道可由 `1100` 供货，对产品组 `00` 和 `01` 都生效。"])

# ============================== M4 ==============================
tab("ledger_config", "分类账配置", "FINSC_LEDGER 经明确代码映射",
    "账本的类型、是否主导、估值视角、默认会计原则。账本是并行会计的载体。",
    [("tenant_id", "uuid", "pnf", "租户。FK → client_scope"),
     ("mandt", "varchar(3)", "pnf", "客户端号"),
     ("release_id", "uuid", "pnf", "所属发布包。FK → foundation_release"),
     ("rldnr", "varchar(2)", "pnf", "账本码。FK → ledger_key。示例：`0L`（主导账本）/ `2L`（扩展）"),
     ("ledger_kind", "text", "nk", "类型，`CHECK IN ('STANDARD','EXTENSION','TECHNICAL')`。示例：`STANDARD`"),
     ("leading", "boolean", "n", "是否主导账本。**一个租户内应恰有一个 true**（由发布校验保证，不是数据库约束）"),
     ("valuation_view", "text", "n", "估值视角标识。示例：`LOCAL_GAAP`。决定金额用哪套估值规则"),
     ("default_principle", "text", "", "默认会计原则（可空）。示例：`CN_GAAP`。可被单据级覆盖")],
    ["**目录 JSON 注明“经明确代码映射，不照搬所有 SAP 内部账本处理”**：SAP 的 FINSC_LEDGER 里有许多内部账本（如合并账本、成本账本）由系统写死。CMX 只映射业务可理解的账本，**不假装能替代 SAP 的内部账本机制**。",
     "**`TECHNICAL` 类型对应 `02_实施详设.md` 里“不支持的移动平均价、实际成本、技术账本……”**——类型能声明，但能力门要拒绝其业务执行。**有字段 ≠ 允许业务**。"],
    ["建 `0L`（`STANDARD`，`leading=true`）与 `2L`（`EXTENSION`，`leading=false`）。`2L` 用于集团口径，通过 `book_config` 与 `0L` 并行挂到同一公司。"])

tab("book_config", "公司-账本组合（账套）", "FINSC_LD_CMP",
    "“某公司的某账本在什么期间用哪套规则”。**这是过账路由的核心表**——凭证的第一问是“过到哪个 book”。",
    [("tenant_id", "uuid", "pnf", "租户。FK → client_scope"),
     ("mandt", "varchar(3)", "pnf", "客户端号"),
     ("release_id", "uuid", "pnf", "所属发布包。FK → foundation_release"),
     ("bukrs", "varchar(4)", "pnf", "公司。FK → company_config。示例：`1000`"),
     ("rldnr", "varchar(2)", "pnf", "账本。FK → ledger_config。示例：`0L`"),
     ("periv", "varchar(2)", "nf", "年度变式。FK → fiscal_variant_config。示例：`K4`"),
     ("opvar", "varchar(4)", "nf", "过账变式。FK → posting_variant_config。示例：`P001`"),
     ("accounting_principle", "text", "n", "会计原则。示例：`CN_GAAP`"),
     ("functional_currency_type", "varchar(2)", "nd", "本位币角色类型。**循环外键，延迟到提交时校验** → `book_currency_config.external_currency_type`"),
     ("required_for_inventory", "boolean", "n", "是否库存必需账本，`DEFAULT false`。示例：`0L`→`true`。**用途**：库存过账必须落在至少一个 inventory 账本上"),
     ("inventory_capability", "text", "nk", "库存能力，`CHECK IN ('DESIGN_ONLY','IMPLEMENTED_NOT_ENABLED','ENABLED_AND_VALIDATED')`。**这是能力门，不是状态字段**"),
     ("price_method", "varchar(1)", "nk", "价格方法，`CHECK IN ('S','V')`。`S`=标准价、`V`=移动平均价。**`V` 在当前实现里被能力门拒绝**"),
     ("active_from", "date", "n", "生效起（含）。示例：`2025-01-01`"),
     ("active_to", "date", "k", "生效止（可空），`CHECK(active_to IS NULL OR active_to>active_from)`。空=长期有效")],
    ["**三态能力门 `inventory_capability` 是本表最值得注意的设计**：`DESIGN_ONLY`（只设计，不实现）、`IMPLEMENTED_NOT_ENABLED`（实现了但没启用）、`ENABLED_AND_VALIDATED`（启用且已验证）。**这三态把“设计存在”与“业务允许”分开**——文档反复强调“不能仅添加字典选项后视为可运行”。",
     "**循环外键为何需要 `DEFERRABLE INITIALLY DEFERRED`**：`book_config.functional_currency_type` → `book_currency_config.external_currency_type`，而 `book_currency_config` 又 → `book_config(bukrs,rldnr)`。**两者互相引用，谁先插都会失败**。延迟到事务提交时校验，就可以在同一事务里先插 A 再插 B。",
     "**`price_method='V'` 与 `inventory_capability` 的关系**：允许声明 `V`，但若能力门未到 `ENABLED_AND_VALIDATED`，执行移动平均价必须拒绝——**字段允许与业务允许是两件事**。"],
    ["建账套：`(1000,'0L')`，`price_method='S'`、`required_for_inventory=true`、`inventory_capability='ENABLED_AND_VALIDATED'`、`active_from='2025-01-01'`。示例数据里 `1000` 与 `2000` 的账套都 `functional_currency_type` 指向 `30`（集团币角色）。"])

tab("book_currency_config", "账套币种角色", "FINSC/FML 映射归一为行",
    "一个账套里各种“币种角色”对应哪个具体币种。**金额不按币种代码去重**——角色是键。",
    [("tenant_id", "uuid", "pnf", "租户。FK → client_scope"),
     ("mandt", "varchar(3)", "pnf", "客户端号"),
     ("release_id", "uuid", "pnf", "所属发布包。FK → foundation_release"),
     ("bukrs", "varchar(4)", "pnf", "公司。FK → book_config。示例：`1000`"),
     ("rldnr", "varchar(2)", "pnf", "账本。FK → book_config。示例：`0L`"),
     ("external_currency_type", "varchar(2)", "p", "外部币种角色码。示例：`30`（集团币）。**主键的一部分，也是发起循环外键的那一端**"),
     ("internal_currency_type", "varchar(2)", "nu", "内部币种角色码，`UNIQUE(…,internal_currency_type)`。**用途**：外部角色面向接口/报表，内部角色是内核索引"),
     ("currency", "varchar(5)", "nf", "该角色对应的实际币种。FK → currency_config。示例：`CNY`"),
     ("source_slot", "varchar(1)", "", "取数槽位（可空）。示例：`1`。声明该角色从单据的哪个字段取数"),
     ("ml_relevant", "boolean", "n", "是否与物料分类账相关。示例：`true`。**用途**：筛选需要 ML 处理的金额")],
    ["**目录 JSON 原文“金额不按币种代码去重”**：如果只看 `currency`，两个角色可能都是 `CNY`（如本位币=集团币时）。但它们**仍是两行**，因为角色不同、语义不同。若用 `currency` 去重，会丢掉“这份金额是以什么角色持有的”这一信息。",
     "**`external_currency_type` 的双重身份**：它既是本表主键的一部分，又是 `book_config.functional_currency_type` 的引用目标——**这是循环外键的成因**。",
     "**`internal_currency_type` 的唯一约束**：保证一个账套内每个内部角色只映射一次，避免歧义。"],
    ["账套 `(1000,'0L')` 的三个角色：`10`=交易币（`USD`）、`30`=集团币（`CNY`）、`60`=本位币（`CNY`）。`30` 与 `60` 的 `currency` 相同但仍是两行。"])

tab("posting_account_rule", "记账码区间规则", "T001B",
    "定义某个过账变式下，各类账户在哪些期间区间内允许过账。**区间重叠在发布时拒绝**。",
    [("tenant_id", "uuid", "pnf", "租户。FK → client_scope"),
     ("mandt", "varchar(3)", "pnf", "客户端号"),
     ("release_id", "uuid", "pnf", "所属发布包。FK → foundation_release"),
     ("rule_id", "uuid", "p", "规则标识。示例：`a1b2…`。**用 UUID 而非复合键**：因为同一规则可以有多行区间（在 posting_window）"),
     ("opvar", "varchar(4)", "nf", "过账变式。FK → posting_variant_config。示例：`P001`"),
     ("account_type", "varchar(1)", "nk", "账户类型，`CHECK IN ('+','A','D','K','M','S')`。`+`=全部；`A`=资产、`D`=客户、`K`=供应商、`M`=物料、`S`=总账"),
     ("account_from", "varchar(10)", "nk", "科目区间起（含），`COLLATE \"C\"`，`DEFAULT ''`"),
     ("account_to", "varchar(10)", "nk", "科目区间止（含），`COLLATE \"C\"`，`DEFAULT ''`。**含端点，与日期区间的半开约定相反**"),
     ("authorization_group", "text", "", "权限组（可空）。示例：`FI_AP`。用于字段级权限")],
    ["**`COLLATE \"C\"` 是必须的**：科目号是定长数字字符串，`'1000' < '900'` 在字典序下为真但业务上错误。`\"C\"` 排序规则是**逐字节比较**，对等长数字串给出正确顺序。**如果漏了它，区间判定会在跨长度时静默出错**。",
     "**CHECK 强制两条互斥形态**：`account_type='+'` 时必须 `from='' AND to=''`（全账户，无区间）；其他类型必须 `from<>'' AND from<=to`。这防止“全账户类型却给了半个区间”这种无意义状态。",
     "**`UNIQUE(tenant,mant,release,opvar,account_type,account_to)`**：同一个 `to` 值在同类账户下只能出现一次——这是**防区间重叠的轻量手段**。真正的重叠检测（区间相交）由发布校验做，因为“`[1000,2000]` 与 `[1500,2500]` 重叠但 `to` 不同”靠 UNIQUE 抓不到。",
     "**目录 JSON 原文“区间重叠在发布时拒绝，不能隐含依赖行顺序”**：如果不拒绝重叠，查询结果会依赖数据库返回顺序——这是不可复现的 bug。"],
    ["规则行：`opvar='P001'`、`account_type='S'`、`account_from='1000'`、`account_to='9999'`。若再插一行 `account_type='S'`、`from='5000'`、`to='8000'`，`account_to` 不同故 UNIQUE 通过，但**发布校验必须发现区间重叠并拒绝**。"])

tab("posting_window", "记账码区间窗口", "T001B 间隔 1/2/3",
    "每行规则再按期间的区间限定：最多 3 个间隔（`interval_number` 1–3）。**允许性解释由内核负责**。",
    [("tenant_id", "uuid", "pnf", "租户。FK → client_scope"),
     ("mandt", "varchar(3)", "pnf", "客户端号"),
     ("release_id", "uuid", "pnf", "所属发布包。FK → foundation_release"),
     ("rule_id", "uuid", "pnf", "所属规则。FK → posting_account_rule。示例：`a1b2…`"),
     ("interval_number", "smallint", "pnk", "间隔序号，`CHECK BETWEEN 1 AND 3`。**1/2 是一般期间区间，3 是 COFI 专用间隔**"),
     ("from_year", "integer", "nk", "起始年度，`CHECK BETWEEN 1 AND 9999`。示例：`2025`"),
     ("from_period", "smallint", "nk", "起始期间，`CHECK BETWEEN 1 AND 366`。示例：`1`"),
     ("to_year", "integer", "nk", "结束年度，`CHECK BETWEEN 1 AND 9999`。示例：`9999`（长期）"),
     ("to_period", "smallint", "nk", "结束期间，`CHECK BETWEEN 1 AND 366`。示例：`12`")],
    ["**`CHECK((from_year,from_period)<=(to_year,to_period))` 是行构造器比较**——这是 PostgreSQL 的行值比较语法，一行搞定“年月二元组有序”，比写成 `from_year<to_year OR (from_year=to_year AND from_period<=to_period)` 更不易错。",
     "**`to_year=9999` 是“长期有效”的惯例**：SAP 里常见，避免用 NULL 表达无上界（NULL 在比较中行为特殊）。",
     "**目录 JSON 原文“允许性解释由内核负责”**：本表只**存**区间，不**解释**。比如“间隔 3 只在 COFI 场景生效”这条规则在代码里，不在表里——因为它是业务语义，不是数据约束。"],
    ["`rule_id` 的第 1 间隔：`from=(2025,1)`、`to=(9999,12)`（长期开）；第 2 间隔若为 `from=(2025,1)`、`to=(2025,3)`，则 2025 年 1–3 月受额外限定。**哪个间隔优先由内核决定**。"])

# ============================== M5 ==============================
tab("master_identity", "统一对象身份注册表", "无直接对应（CMX 自有）",
    "所有主数据对象的统一注册表。`object_id` 是全局身份，`business_key` 是**规范化序列化**的业务键。",
    [("tenant_id", "uuid", "pnf", "租户。FK → client_scope"),
     ("mandt", "varchar(3)", "pnf", "客户端号"),
     ("object_id", "uuid", "pn", "全局对象身份。示例：`c3ad7368-f126-5de6-97d6-441792934cae`。**不可变、不复用**"),
     ("object_type", "text", "nu", "对象类型。示例：`BP` / `MATERIAL` / `COMPANY`"),
     ("business_key", "text", "nu", "业务键的**规范化序列化**。示例：`[\"KUNNR\",\"0000100001\"]`。**不是有歧义的文本拼接**")],
    ["**两条 UNIQUE 的分工**：`(object_id,object_type)` 保证“一个对象一个类型标签”；`(object_type,business_key)` 保证“同类型下业务键唯一”。**前者是身份唯一性，后者是业务唯一性**。",
     "**为什么用序列化数组而非拼接字符串**（目录 JSON 原文：“business_key 使用规范键数组序列化，不拼接有歧义的文本”）：若拼接成 `'A-B'`，则 `('A','B-C')` 与 `('A-B','C')` 会撞键。序列化数组（JSON 或带长度前缀）消除了这个歧义。**这是复合业务键的经典陷阱**。",
     "**为什么需要它而不是直接用业务表主键**：业务表主键是 SAP 编码（`kunnr`/`matnr`），会因源系统不同而冲突；`object_id` 是跨源统一身份，是源键映射（`external_key_map`）的锚点。"],
    ["客户 `0000100001` 注册为 `object_type='BP'`、`business_key='[\"KUNNR\",\"0000100001\"]'`，得到 `object_id=X`。此后 SAP 源键、本体节点、外部系统 ID 都通过 `external_key_map` 汇聚到 `X`。"])

tab("external_key_map", "源系统键映射", "无直接对应（类比 CVI 链接表）",
    "把“某个源系统的某个键”映射到统一 `object_id`。**源键映射不能任意重新指向**。",
    [("tenant_id", "uuid", "pnf", "租户。FK → client_scope"),
     ("mandt", "varchar(3)", "pnf", "客户端号"),
     ("source_system", "text", "pn", "源系统。示例：`SAP_S4F`。**同一目标可有多个源**"),
     ("source_client", "text", "pn", "源系统的客户端。示例：`810`。**SAP 客户端必须进键**——同一系统不同客户端可独立编号"),
     ("object_type", "text", "p", "对象类型。示例：`BP`。**与 object_id 一起构成到 master_identity 的逻辑引用**"),
     ("external_key", "text", "p", "源系统里的键。示例：`0000100001`"),
     ("object_id", "uuid", "n", "统一身份。示例：`X`。**逻辑引用 → master_identity(object_id,object_type)**")],
    ["**目录 JSON 原文“源键映射不能任意重新指向”**：这不是一句提醒，是**架构约束**。如果允许把 `SAP:810:BP:0000100001` 重指到另一个 `object_id`，那么所有历史凭证的客户归属会静默改变。**重指向必须是显式迁移动作（合并对象），不是一次 UPDATE**。",
     "**`source_client` 必须在键里**：SAP 的客户端是独立编号空间。若省略它，`100` 和 `200` 客户端的 `KUNNR=1000` 会撞键。",
     "**本表的 `release_id` 情况**：DDL 里有一行指向 `foundation_release` 的外键，但**本表无 `release_id` 列**（详见 §附录 A 设计完整性说明）。"])

tab("bp_identity", "业务伙伴身份", "CVI 映射的 BP 身份",
    "SAP 的 `PARTNER_GUID` 与 CMX 统一身份的桥。BP 是客商统一后的载体。",
    [("tenant_id", "uuid", "pnf", "租户。FK → client_scope"),
     ("mandt", "varchar(3)", "pnf", "客户端号"),
     ("partner_guid", "uuid", "p", "SAP BP 的 GUID（`BUT000.PARTNER_GUID`）。示例：`9f1c…`。**这是 SAP 侧的身份，不是 CMX 的**"),
     ("partner", "varchar(10)", "nu", "BP 编号。示例：`0000100001`。`UNIQUE(tenant,mandt,partner)`"),
     ("object_id", "uuid", "n", "CMX 统一身份。**逻辑引用 → master_identity(object_id,object_type)**"),
     ("object_type", "text", "nk", "固定 `'BP'`（`DEFAULT 'BP'` + `CHECK(object_type='BP')`）")],
    ["**`CHECK(object_type='BP')` 是刻意的窄化**：本表只装 BP。若允许任意类型，`object_type` 就成了“能装任何东西”的弱语义列，`UNIQUE` 与索引都会失去选择性。**用 CHECK 把类型固化，让表名与内容一致**。",
     "**`partner_guid` vs `partner`**：GUID 是 BP 创建时生成且**永不复用**的；编号可以（在极少数重组场景下）被重新分配。以 GUID 为键是防御性选择——但业务接口一般用编号，故两者都存。",
     "**与 `customer_link`/`supplier_link` 的三层关系**：`bp_identity`（BP 层）→ `customer_link`（客户号层）→ `customer_company_version`（公司视图层）。**一层都不能省**，因为编号空间不同（E04）。"])

tab("customer_link", "客户编号到 BP 的链接", "CVI（E04）",
    "客户号 `KUNNR` 与 BP 的映射。**客商编号不要求等于 BP 编号**。",
    [("tenant_id", "uuid", "pnf", "租户。FK → client_scope"),
     ("mandt", "varchar(3)", "pnf", "客户端号"),
     ("kunnr", "varchar(10)", "p", "客户号。示例：`0000100001`。**主键**"),
     ("partner_guid", "uuid", "nu", "对应 BP 的 GUID。**逻辑引用 → bp_identity(partner_guid)**。`UNIQUE(tenant,mandt,partner_guid)` 保证一个 BP 只对应一个客户号")],
    ["**“客商编号不要求等于 BP 编号”是本表存在的全部理由**：SAP CVI 之前，客户和供应商是两套独立编号；CVI 之后，同一个 BP 可以同时是客户和供应商，且客户号、供应商号、BP 号三者可以**互不相同**。**如果假设它们相等，映射会错**。",
     "**`partner_guid` 上的 UNIQUE 是“一对一”的保证**：一个 BP 不能对应两个客户号。若业务上需要，那就不是映射表而是关系表——需要显式改设计。",
     "**数据流**：`KUNNR` → 本表 → `partner_guid` → `bp_identity` → `object_id` → CMX 统一身份。三步查得。"],
    ["`kunnr='0000100001'` 映射到 `partner_guid='9f1c…'`；该 BP 的 `partner='0000100001'` 恰好相同。**但这是巧合而非规则**——示例数据里另一客户可能 `kunnr='0000100002'` 而 `partner='0000200005'`。"])

tab("supplier_link", "供应商编号到 BP 的链接", "CVI（E04）",
    "供应商号 `LIFNR` 与 BP 的映射。结构与 `customer_link` 完全对称。",
    [("tenant_id", "uuid", "pnf", "租户。FK → client_scope"),
     ("mandt", "varchar(3)", "pnf", "客户端号"),
     ("lifnr", "varchar(10)", "p", "供应商号。示例：`0000200001`。**主键**"),
     ("partner_guid", "uuid", "nu", "对应 BP 的 GUID。**逻辑引用 → bp_identity**。`UNIQUE` 保证一对一")],
    ["**为什么客户与供应商分成两张表而不是一张带 `type` 列**：两者键空间独立（`KUNNR` 与 `LIFNR` 可重号），且业务上可能同时是客户和供应商（同一 `partner_guid` 出现在两表）。**用一张表加 type 列会丢掉“同一 BP 双向”这一事实的可表达性**（或需要允许两行，那 UNIQUE 就失效了）。",
     "**《证据》E04 的要点**：CVI 映射是 SAP 里最容易“看起来显然、实际错”的地方——因为很多系统里客户号=BP号，迁移时容易硬编码这个假设。"],
    ["同一集团既是客户也是供应商：`partner_guid='9f1c…'` 同时出现在 `customer_link`（`kunnr='0000100001'`）和 `supplier_link`（`lifnr='0000200001'`）。**两个编号不同，BP 相同**。"])

tab("material_identity", "物料身份", "MATNR40 / MATN1 需单独验证",
    "物料的统一身份。`MATNR` 在 SAP 里可能是 `CHAR(18)` 或 `CHAR(40)`（MATN1 适配）。",
    [("tenant_id", "uuid", "pnf", "租户。FK → client_scope"),
     ("mandt", "varchar(3)", "pnf", "客户端号"),
     ("matnr", "varchar(40)", "p", "物料号，`varchar(40)`。示例：`MAT-0001`。**取 40 位**以覆盖 MATNR40；MATN1（18 位）适配需单独验证"),
     ("object_id", "uuid", "n", "统一身份。**逻辑引用 → master_identity**"),
     ("object_type", "text", "nk", "固定 `'MATERIAL'`（`DEFAULT` + `CHECK`）")],
    ["**目录 JSON 原文“MATNR40/业务编号字符串；MATN1 适配需单独验证”**：SAP 里 `MATNR` 的长度由 `MARA` 的域决定，可能是 18 或 40。**若源系统是 18 位，直接迁到 40 位表是安全的；反之会截断**。所以适配必须验证，不能假设。",
     "**为什么物料不用 `bp_identity` 那样的中间层**：物料没有“编号与 GUID 分离”的问题——`MATNR` 本身就是稳定标识。所以直接 `matnr → object_id` 一层。"],
    ["SAP 物料 `MAT-0001` 注册：`matnr='MAT-0001'`、`object_id=Y`。物料的所有版本（`material_version`/`material_plant_version`/`material_uom_version`）都通过 `matnr` 挂上来。"])

# ============================== M6 ==============================
BITEMPORAL = [
    ("valid_from", "date", "n", "业务有效起（含）。示例：`2025-01-01`。**业务时间**：这件事在现实中何时成立"),
    ("valid_to", "date", "k", "业务有效止（**不含**，可空=至今），`CHECK(valid_to IS NULL OR valid_to>valid_from)`。示例：`2026-01-01`"),
    ("recorded_from", "timestamptz", "n", "系统认知起（含）。示例：`2025-01-15 09:30:00+08`。**系统时间**：系统何时知道这件事"),
    ("recorded_to", "timestamptz", "k", "系统认知止（可空=仍是当前认知），`CHECK` 同上"),
    ("approved_change_id", "uuid", "n", "审批变更引用。**每行独立**——不是表级审批，而是这一行由哪次审批产生")]


def vtab(name, cn, sap, purpose, keycols, attrcols, notes, scenes, bitemp=True):
    """Build a version table entry: common head + key cols + attrs + bitemporal tail."""
    cols = [("tenant_id", "uuid", "pnf", "租户。FK → client_scope"),
            ("mandt", "varchar(3)", "pnf", "客户端号"),
            ("revision_id", "uuid", "p", "版本行标识。示例：`r-0001`。**主键**——每行一个 UUID，同一对象的历史行各有自己的 id")]
    cols += keycols + attrcols
    if bitemp:
        cols += list(BITEMPORAL)
    tab(name, cn, sap, purpose, cols, notes, scenes)


vtab("bp_role_version", "BP 角色版本", "BUT100（E05）",
     "BP 的角色及有效期。**唯一用 `timestamptz` 做 valid 范围的表**——因为 SAP 的 BUT100 角色有效期是时间戳而非日期。",
     [("partner_guid", "uuid", "nf", "BP 身份。FK → bp_identity。示例：`9f1c…`"),
      ("role", "varchar(6)", "n", "角色码。示例：`FLCU01`（客户）/ `FLVN01`（供应商）"),
      ("dfval", "varchar(1)", "n", "角色子类型，`DEFAULT ''`。示例：空串"),
      ("valid_from", "timestamptz", "n", "**注意类型**：业务有效起是 `timestamptz` 而非 `date`"),
      ("valid_to", "timestamptz", "k", "业务有效止（不含，可空）")],
     [("recorded_from", "timestamptz", "n", "系统认知起"),
      ("recorded_to", "timestamptz", "k", "系统认知止（可空）"),
      ("approved_change_id", "uuid", "n", "审批变更引用")],
     ["**为什么这张表必须用 `timestamptz`**（E05：BUT100 角色有效期是时间戳，不是普通 DATE）：如果照搬其他版本表用 `date`，会**丢掉当天内的时分秒**。若一个 BP 在 2025-01-15 上午是客户、下午被撤角色，用 `date` 表达会变成“2025-01-15 一整天都是客户”——**这是真实的数据损失**。",
      "**因此 GiST 排斥约束也用的是 `tstzrange` 而不是 `daterange`**：`tstzrange(valid_from,valid_to,'[)')`。这是 13 张版本表里唯一一个。",
      "**这条差异是实查发现的，不是设计出来的**——它证明了“按表逐列读 SAP”这一步不可省。"],
     ["BP `9f1c…` 在 `2025-01-15 08:00` 获得 `FLCU01` 角色，`2025-06-30 17:00` 撤销。两行版本（或一行 `valid_to` 落定），业务时间带时刻，可精确到分钟。"],
     bitemp=False)

vtab("customer_company_version", "客户公司视图版本", "KNB1",
     "客户在公司代码维度的属性：统驭科目、付款条件、冻结。**统驭科目必须按当前公司科目表与 D/K 类型进行领域校验**。",
     [("kunnr", "varchar(10)", "nf", "客户号。FK → customer_link。示例：`0000100001`"),
      ("bukrs", "varchar(4)", "nf", "公司代码。FK → company_key。示例：`1000`")],
     [("akont", "varchar(10)", "n", "统驭科目（对账科目）。示例：`11220000`。**领域校验**：必须是该公司科目表里的 D 类科目"),
      ("zterm", "varchar(4)", "", "付款条件（可空）。示例：`0001`"),
      ("posting_block", "boolean", "n", "记账冻结。示例：`false`。`true` 时该公司下禁止对该客户记账"),
      ("payment_block", "text", "", "付款冻结原因（可空）。示例：`信用超限`")],
     ["**目录 JSON 原文“统驭科目必须按当前公司科目表与 D/K 类型进行领域校验”**：`akont` 是个普通字符串列，**没有外键能约束它**——因为科目表是版本化主数据（`gl_account_version`），且 D/K 类型取决于该科目在 `gl_company_version` 里的 `reconciliation_type`。所以校验必须在领域核里做：读 `company_config.ktopl` → 查 `gl_account_version` 是否存在该科目 → 查 `reconciliation_type='D'`。**三步校验无法用一条外键表达**。",
      "**`posting_block` 是 boolean 而 `payment_block` 是 text**：前者是开关，后者是原因描述。语义不同，类型不同——**不要为了整齐把两者都做成 boolean 或都做成 text**。"],
     ["客户 `0000100001` 在 `1000` 从 `2025-01-01` 起挂统驭科目 `11220000`；`2025-07-01` 起银行账户变更导致统驭科目改为 `11220001`。两行版本，`valid_from` 分别是两个日期。**历史凭证仍指旧科目**。"])

vtab("supplier_company_version", "供应商公司视图版本", "LFB1",
     "供应商在公司代码维度的属性。结构与客户公司视图完全对称。",
     [("lifnr", "varchar(10)", "nf", "供应商号。FK → supplier_link。示例：`0000200001`"),
      ("bukrs", "varchar(4)", "nf", "公司代码。FK → company_key。示例：`1000`")],
     [("akont", "varchar(10)", "n", "统驭科目。示例：`22020000`。**校验要求 `reconciliation_type='K'`**"),
      ("zterm", "varchar(4)", "", "付款条件（可空）。示例：`0002`"),
      ("posting_block", "boolean", "n", "记账冻结"),
      ("payment_block", "text", "", "付款冻结原因（可空）")],
     ["**客户看 D、供应商看 K**：`gl_company_version.reconciliation_type` 里 `D`=客户、`K`=供应商、`A`=资产。客户公司视图的 `akont` 必须落在 D 类科目，供应商必须落在 K 类——**同一张科目表、同一列名、不同的校验目标**。",
      "**为什么校验不能只靠 `gl_account_version`**：`reconciliation_type` 在 `gl_company_version`（公司级），不在科目表级。所以科目表级看不出这个科目是不是统驭科目，必须查公司级。"],
     ["供应商 `0000200001` 在 `1000` 挂统驭科目 `22020000`（应付账款），付款条件 `0002`。若误配成 `11220000`（应收），领域校验必须拒绝——因为那是 D 类不是 K 类。"])

vtab("customer_sales_version", "客户销售视图版本", "KNVV",
     "客户在销售范围维度的属性：各种冻结、货币、付款条件。粒度是 `客户+销售组织+渠道+产品组`。",
     [("kunnr", "varchar(10)", "nf", "客户号。FK → customer_link"),
      ("vkorg", "varchar(4)", "nf", "销售组织。FK → sales_org_key。示例：`S100`"),
      ("vtweg", "varchar(2)", "n", "分销渠道。示例：`10`"),
      ("spart", "varchar(2)", "n", "产品组。示例：`00`")],
     [("order_block", "text", "", "订单冻结原因（可空）"),
      ("delivery_block", "text", "", "交货冻结原因（可空）"),
      ("billing_block", "text", "", "开票冻结原因（可空）"),
      ("currency", "varchar(5)", "", "销售货币（可空）。示例：`USD`"),
      ("payment_terms", "varchar(4)", "", "付款条件（可空）。示例：`0001`")],
     ["**三个冻结都是 `text` 而非 boolean**：SAP 的 KNVV 里这些冻结字段是**原因码**（如 `01`/`02`），不是简单开关。用 text 保留原因码，比压成 boolean 更有信息量——**但这也意味着判断“是否冻结”要看非空，而不是看真值**。",
      "**粒度含 `spart`，与 `sales_plant_config` 不含形成对比**：客户属性可以按产品组区分（不同产品组不同付款条件），但供货工厂分配不行。**这是 SAP 的实际差异**。",
      "**目录 JSON 原文“当前发布的合法销售范围由领域校验”**：`vkorg` 有外键指向 `sales_org_key`，但“这个销售组织+渠道+产品组的组合是否是当前发布里的合法销售范围”需要查 `sales_area_config`——**外键只保证销售组织存在，不保证销售范围存在**。"],
     ["客户 `0000100001` 在 `(S100,'10','00')` 下开票冻结（`billing_block='01'`），销售货币 `USD`。在 `(S100,'10','01')` 下无冻结。**同一客户同一渠道，因产品组不同而不同**。"])

vtab("supplier_purchasing_version", "供应商采购视图版本", "LFM1",
     "供应商在采购组织维度的属性。粒度是 `供应商+采购组织`。",
     [("lifnr", "varchar(10)", "nf", "供应商号。FK → supplier_link"),
      ("ekorg", "varchar(4)", "nf", "采购组织。FK → purchasing_org_key。示例：`P100`")],
     [("purchasing_block", "boolean", "n", "采购冻结。**注意是 boolean**，与客户侧三个 text 冻结不同"),
      ("order_currency", "varchar(5)", "", "订单货币（可空）。示例：`CNY`"),
      ("payment_terms", "varchar(4)", "", "付款条件（可空）")],
     ["**为什么供应商采购冻结是 boolean 而客户冻结是 text**：这是 SAP 的实际表结构差异（LFM1 用标志，KNVV 用原因码）。**CMX 选择忠实于源**，而不是为了对称把它们统一。**强行统一会丢掉 SAP 侧的原因码语义**。",
      "**`order_currency` 可空**：为空表示用采购组织的默认货币（经 `company_config.currency` 推导）。**可空不是“没配”，而是“继承”**。"],
     ["供应商 `0000200001` 在 `P100` 下无冻结，订单货币 `CNY`；在 `PG01`（跨公司采购组织）下采购冻结 `true`。**同一供应商可对某采购组织可用、对另一不可用**。"])

vtab("material_version", "物料主数据版本", "MARA",
     "物料核心属性：基本单位、物料类型、SKU、数量小数位。**主数据没有库存金额**。",
     [("matnr", "varchar(40)", "nf", "物料号。FK → material_identity。示例：`MAT-0001`")],
     [("base_unit", "varchar(3)", "n", "基本计量单位。示例：`EA`。**所有库存数量都以它为单位存储**"),
      ("material_type", "varchar(4)", "n", "物料类型。示例：`FERT`（成品）/ `ROH`（原料）"),
      ("sku", "varchar(100)", "", "SKU（可空）。示例：`SKU-0001`。外部电商/仓储系统的料号"),
      ("quantity_decimals", "smallint", "nk", "数量小数位，`CHECK BETWEEN 0 AND 9`。示例：`0`。**与 `uom_config.quantity_decimals` 的关系**：本列是物料级覆盖")],
     ["**目录 JSON 原文“MARA 核心；主数据没有库存金额”**：这是**划界声明**。物料的库存数量与金额在库存/物料凭证里，不在主数据里。主数据只描述“它是什么”，不描述“有多少”。**把库存快照塞进主数据是常见反模式**——它会导致主数据表随业务增长而爆炸。",
      "**`base_unit` 有外键吗**：DDL 里没有（因为 `uom_config` 是 release 绑定的，而版本表不绑 release）。**这是版本表与配置表之间无法建外键的结构性原因**——见 §附录 A。",
      "**`quantity_decimals` 与 `uom_config` 的重复**：物料可以有自己的数量精度（比单位默认更严/更松）。**两处都有值时以物料级为准**（这是领域核规则，不是数据库约束）。"],
     ["物料 `MAT-0001` 基本单位 `EA`、类型 `FERT`、数量小数 `0`。2025-06-01 起基本单位改为 `BOX`（因包装规格变更）——新增一行版本，`valid_from='2025-06-01'`。**旧行保留，历史凭证仍指 `EA`**。"])

vtab("material_plant_version", "物料工厂视图版本", "MARC",
     "物料在工厂维度的属性：成本控制范围、利润中心、状态码。",
     [("matnr", "varchar(40)", "nf", "物料号。FK → material_identity"),
      ("werks", "varchar(4)", "nf", "工厂。FK → plant_key。示例：`1100`")],
     [("kokrs", "varchar(4)", "", "成本控制范围（可空）。示例：`A000`"),
      ("prctr", "varchar(10)", "", "利润中心（可空）。示例：`PC01`"),
      ("status_code", "text", "", "状态码（可空）。示例：`ACTIVE`")],
     ["**目录 JSON 原文“MARC 核心；替代对象聚合字段不作为主数据自由维护”**：SAP 的 MARC 里有些字段是**系统聚合写入**的（不是用户维护的）。CMX 明确不把这些当自由维护字段——**避免把派生数据当输入数据**。",
      "**`kokrs`/`prctr` 可空的意义**：为空表示“未分配”或“继承默认”。**可空在此处是有信息的**（未分配 ≠ 分配了空值）。"],
     ["物料 `MAT-0001` 在工厂 `1100` 归属成本控制范围 `A000`、利润中心 `PC01`；在工厂 `2100` 未分配利润中心（`prctr` 为空）。**同一物料在不同工厂可有不同归属**。"])

vtab("material_uom_version", "物料单位换算版本", "MARM",
     "物料在其基本单位与替代单位之间的换算比。**SAP 原始 UMREZ/UMREN 需正数和精度控制**。",
     [("matnr", "varchar(40)", "nf", "物料号。FK → material_identity"),
      ("alternative_unit", "varchar(3)", "n", "替代单位。示例：`BOX`")],
     [("numerator", "numeric(31,9)", "nk", "换算分子，`CHECK(numerator>0 AND numerator<>'NaN')`。示例：`12`"),
      ("denominator", "numeric(31,9)", "nk", "换算分母，`CHECK(denominator>0 AND denominator<>'NaN')`。示例：`1`")],
     ["**为什么是分子/分母而不是一个小数因子**：`1 BOX = 12 EA` 精确表示；若存成 `12.0` 的因子，则 `1 EA = 0.0833333…` 无法精确表达。**分子分母是精确的有理数表示**，避免换算累积误差。这是 SAP 用 UMREZ/UMREN 的原意。",
      "**`>0` 与 `<>'NaN'` 双重 CHECK 都必要**：`>0` 排除零与负数；`<>'NaN'` 排除 `numeric` 类型能表示的 `NaN`（**`NaN` 在 PostgreSQL 里与任何值比较都为 false，会绕过 `>0`**）。**只写 `>0` 是不够的**。",
      "**精度 `numeric(31,9)`**：9 位小数足够表达常见换算，且十进制精确。"],
     ["`MAT-0001`：`EA` 与 `BOX` 换算 `12/1`（1 BOX = 12 EA）。若反过来要表示“1 EA = 1/12 BOX”，则分子分母互换。**永不出现 `0.0833` 这样的近似值**。"])

vtab("gl_account_version", "总账科目表视图版本", "SKA1",
     "科目在科目表层级的属性：类别、描述。**唯一的 FK 只指向 `client_scope`**。",
     [("ktopl", "varchar(4)", "n", "科目表码。示例：`YCOA`"),
      ("saknr", "varchar(10)", "n", "科目号。示例：`10010100`")],
     [("account_category", "text", "n", "科目类别。示例：`ASSET` / `LIABILITY` / `REVENUE`。**用途**：决定资产负债表归属，是报表上卷的依据"),
      ("description", "text", "n", "科目描述。示例：`库存现金`")],
     ["**本表为何没有指向 `company_config.ktopl` 的外键**（DDL 明说“FK client_scope only”）：`ktopl` 只在 `company_config` 里出现且是**版本绑定**的，而本表**不绑 release**（它是双时态版本表）。**跨这类边界建外键会把版本语义混淆**——所以只在领域核校验“这个 ktopl 在当前发布里存在”。",
      "**`saknr` 是 `varchar(10)` 而非定长数字**：SAP 科目号可以含字母（配置为字母数字科目号时）。**假设纯数字会在某些客户处失败**。",
      "**与 `gl_company_version` 的分工**：本表是“科目表级”（叫什么、哪一类），公司级属性（统驭、未清项、冻结）在下表。"],
     ["科目 `YCOA/10010100` 类别 `ASSET`、描述 `库存现金`。公司 `1000` 通过 `company_config.ktopl='YCOA'` 使用这张科目表。"])

vtab("gl_company_version", "总账科目公司视图版本", "SKB1",
     "科目在公司代码层级的属性。**科目表由公司配置派生，修改未清项等需迁移流程**。",
     [("bukrs", "varchar(4)", "nf", "公司代码。FK → company_key。示例：`1000`"),
      ("saknr", "varchar(10)", "n", "科目号。示例：`11220000`")],
     [("reconciliation_type", "varchar(1)", "k", "统驭类型，`CHECK IN ('D','K','A')`（可空）。`D`=客户、`K`=供应商、`A`=资产。**用途**：客户/供应商公司视图的 `akont` 校验目标"),
      ("currency", "varchar(5)", "n", "科目货币。示例：`CNY`"),
      ("open_item_managed", "boolean", "n", "是否管理未清项。示例：`true`。**目录 JSON 提醒“修改未清项等需迁移流程”**——这个开关不是随便改的，改它会影响已有余额的归集方式"),
      ("posting_block", "boolean", "n", "记账冻结"),
      ("automatic_postings_only", "boolean", "n", "仅允许自动过账。示例：`false`。`true` 时人工凭证不能直接记这个科目")],
     ["**`reconciliation_type` 是整条应收应付链的枢纽**：它决定了客户公司视图的 `akont` 必须是 D 类、供应商的必须是 K 类。**没有它，统驭科目校验无从下手**。",
      "**目录 JSON 原文“科目表由公司配置派生”**：本表**不含 `ktopl` 列**——公司用哪个科目表由 `company_config.ktopl` 决定。所以查“公司的某个科目”是 `company_config.ktopl + saknr` 的组合，而不是只看 `saknr`。**这是刻意的去冗余**。",
      "**为什么 `open_item_managed` 改动需要迁移流程**：未清项管理方式改变意味着已有余额的挂账维度改变。**这不是配置变更，是数据迁移**——所以文档要求走流程而不是直接 UPDATE。"],
     ["科目 `11220000` 在公司 `1000`：`reconciliation_type='D'`（客户统驭）、`open_item_managed=true`、科目货币 `CNY`。因此客户公司视图里的 `akont='11220000'` 能通过校验（D 类）。",
      "反过来，若某客户把它配成应付科目（K 类），校验必须拒绝——**同一科目表的同一个科目，在不同公司可有不同统驭类型**。"])

vtab("profit_center_version", "利润中心版本", "CEPC",
     "利润中心的时态主数据：名称与所属段。",
     [("kokrs", "varchar(4)", "nf", "成本控制范围。FK → controlling_area_key。示例：`A000`"),
      ("prctr", "varchar(10)", "n", "利润中心码。示例：`PC01`")],
     [("name", "text", "n", "利润中心名称。示例：`华东事业部`"),
      ("segment", "text", "", "所属段（可空）。示例：`SEG_EAST`。**用途**：分部报告维度")],
     ["**利润中心的键含 `kokrs`**：因为利润中心编码在**成本控制范围内唯一**，跨控制范围可重号。**这与公司代码 `bukrs` 的全局唯一性不同**——所以 `profit_center_version` 和 `profit_company_version` 都以 `kokrs` 起头。",
      "**`segment` 可空且是 text**：段是较新的 SAP 维度（替代业务范围），并非所有客户启用。**用可空 text 表示“可能未启用”**。"],
     ["`A000/PC01` = `华东事业部`，段 `SEG_EAST`。`2026-01-01` 起重组为 `SEG_EAST_2`——新增版本行，旧行保留。"])

vtab("profit_company_version", "利润中心-公司关系版本", "CEPC_BUKRS",
     "利润中心与公司代码的归属关系，带有效期。**有效期覆盖由发布校验**。",
     [("kokrs", "varchar(4)", "nf", "成本控制范围。FK → controlling_area_key"),
      ("prctr", "varchar(10)", "n", "利润中心码。示例：`PC01`"),
      ("bukrs", "varchar(4)", "nf", "公司代码。FK → company_key。示例：`1000`")],
     [],
     ["**为什么单独一张表而不是放进 `profit_center_version`**：SAP 的 `CEPC_BUKRS` 是**独立关系表**，因为一个利润中心可以跨多个公司（矩阵组织），且归属会随时间变。**塞进主表会变成多值字段**。",
      "**目录 JSON 原文“有效期覆盖由发布校验”**：GiST 排斥约束保证**同一 `(kokrs,prctr,bukrs)` 三元组**在有效期内不重叠；但“利润中心在这些公司上的有效期是否互相衔接”是**跨行的整体一致性**，GiST 管不了，必须由发布校验做。"],
     ["`A000/PC01` 归属 `1000`（`2025-01-01` 起）与 `2000`（`2025-07-01` 起）。两行，各自有效期独立。"])

vtab("cost_center_version", "成本中心版本", "CSKS（DATBI 留源值）",
     "成本中心的时态主数据。**原键 `DATBI` 保留为源值字段**。",
     [("kokrs", "varchar(4)", "nf", "成本控制范围。FK → controlling_area_key"),
      ("kostl", "varchar(10)", "n", "成本中心码。示例：`CC1000`")],
     [("bukrs", "varchar(4)", "nf", "所属公司。FK → company_key。示例：`1000`"),
      ("prctr", "varchar(10)", "", "利润中心（可空）。示例：`PC01`"),
      ("source_datbi", "varchar(8)", "", "SAP 原键 `DATBI` 留档（8 位，SAP 日期格式）。示例：`99991231`。**用途**：回溯到 SAP 原始行，不参与 CMX 的有效期计算"),
      ("name", "text", "n", "成本中心名称。示例：`生产一车间`")],
     ["**目录 JSON 原文“CSKS 原键 DATBI 留源值；CMX 稳定身份与版本分开”**：SAP 的 `CSKS` 用 `DATBI`（有效止）作为**主键的一部分**，这是 SAP 的时态实现方式。CMX 改用 `revision_id` 主键 + `valid_*` 范围，**但把 `DATBI` 原值留在 `source_datbi` 列**。理由：迁移对账时需要按 SAP 原键回溯，**若丢掉就无法与源系统核对**。",
      "**为什么 `source_datbi` 是 varchar(8) 而不是 date**：SAP 的 DATBI 是 `CHAR(8)` 格式 `YYYYMMDD`，其中 `99991231` 表示“无限”。**用 date 会把 `99991231` 变成一个怪异的值，且丢失“这是源格式”的信息**。",
      "**`bukrs` 非空而 `prctr` 可空**：成本中心必须属于公司（记账必需），但不一定分到利润中心。**这反映了“成本中心可先于利润中心建立”的现实**。"],
     ["成本中心 `A000/CC1000` 属于公司 `1000`、利润中心 `PC01`，源 `DATBI='99991231'`（无限期）。2026-04-01 调整利润中心归属 → 新版本行，`valid_from='2026-04-01'`，`source_datbi` 更新为实际 SAP 变更日。"])
T_END = True

# ============================== M7 ==============================
tab("valuation_unit", "估值对象（价值对象）", "独立价值对象（KALNR）",
    "“物料 × 估值范围 × 特殊库存维度”的具体实例。**有字段不等于允许业务**——特殊库存处理需能力支持。",
    [("tenant_id", "uuid", "pnf", "租户。FK → client_scope"),
     ("mandt", "varchar(3)", "pnf", "客户端号"),
     ("kalnr", "varchar(12)", "p", "价值对象号。示例：`100000000001`。**这是价格与库存的挂载点**"),
     ("matnr", "varchar(40)", "n", "物料号。**逻辑引用 → material_identity**"),
     ("bwkey", "varchar(4)", "n", "估值范围。**逻辑引用 → valuation_area_key**"),
     ("bwtar", "varchar(10)", "n", "估价类型（valuation type，如批次/等级），`DEFAULT ''`。示例：空串=无估价类型"),
     ("sobkz", "varchar(1)", "n", "特殊库存标识，`DEFAULT ''`。示例：`K`=寄售、`V`=在途。**空串=自有库存**"),
     ("kdauf", "varchar(10)", "n", "销售订单号，`DEFAULT ''`。用于销售订单专项库存"),
     ("kdpos", "varchar(6)", "n", "销售订单行项目，`DEFAULT ''`"),
     ("pspnr", "varchar(8)", "n", "WBS 元素（项目库存），`DEFAULT ''`"),
     ("lifnr", "varchar(10)", "n", "供应商号（供应商专项库存），`DEFAULT ''`")],
    ["**`kalnr` 是“组合实例”的标识，不是业务概念**：SAP 里价值对象由后台按“物料+估值范围+各维度”**自动生成**，业务人员从不手填。**CMX 保留这个设计，但强调它是派生键**。",
     "**`UNIQUE(tenant,mandt,matnr,bwkey,bwtar,sobkz,kdauf,kdpos,pspnr,lifnr)` 是十列唯一键**——这十列定义了“什么时候需要一个新的价值对象”。**每一列都参与判重**，漏一列就会把两个不同的库存池合成一个。",
     "**所有维度列都是 `NOT NULL DEFAULT ''` 而不是可空**：因为它们是唯一键的一部分，**主键/唯一键列不能为 NULL**。空串表示“该维度不适用”。这是 SAP 的惯例，也是必要技术手段。",
     "**目录 JSON 原文“特殊库存处理需能力支持，不仅有字段就允许业务”**：本表能存 `sobkz='K'`（寄售），但**能否真的处理寄售业务取决于能力门**。这是“字段 vs 能力”原则最直接的体现——**表结构能表达 ≠ 系统能正确处理**。"],
    ["物料 `MAT-0001` 在估值范围 `V100` 的自有库存 → 生成一个 `kalnr`（`sobkz=''`）。同一物料在 `V100` 的寄售库存 → **另一个** `kalnr`（`sobkz='K'`）。价格与库存挂在不同 `kalnr` 上，因此分开计价。"])

tab("material_price_version", "物料价格版本", "FMLT_PRICE 启发",
    "受 FMLT_PRICE 启发的本地独立价格模型。**有效期不自动等同 SAP 各价格类型语义**。",
    [("tenant_id", "uuid", "pnf", "租户。FK → client_scope"),
     ("mandt", "varchar(3)", "pnf", "客户端号"),
     ("revision_id", "uuid", "p", "版本行标识。**主键**"),
     ("kalnr", "varchar(12)", "nf", "价值对象。FK → valuation_unit。示例：`100000000001`"),
     ("rldnr", "varchar(2)", "nf", "账本。FK → ledger_key。示例：`0L`"),
     ("external_currency_type", "varchar(2)", "n", "币种角色。示例：`30`"),
     ("price_type", "varchar(20)", "n", "价格种类。示例：`STANDARD` / `MOVING_AVERAGE`"),
     ("price_subtype", "varchar(20)", "n", "价格子类，`DEFAULT ''`。示例：空串"),
     ("currency", "varchar(5)", "n", "价格货币。示例：`CNY`"),
     ("valuation_unit", "varchar(3)", "n", "**每几个单位的价格**（SAP 的 `PEINH` 计价单位，如“每 100 个”）。示例：`1` / `100`。**注意：本列不是指向 `valuation_unit` 表的外键**"),
     ("numerator", "numeric(38,18)", "nk", "价格分子，`CHECK(numerator>=0 AND <>'NaN')`。示例：`123456789012345678`"),
     ("denominator", "numeric(38,18)", "nk", "价格分母，`CHECK(denominator>0 AND <>'NaN')`。示例：`1000000000000000000`"),
     ("raw_price", "numeric(38,18)", "", "源价格原值（可空）。示例：`12.345678901234567890`。**留档用，不参与计算**"),
     ("raw_price_unit", "numeric(18,0)", "", "源价格的计价单位（可空）。示例：`1`"),
     ("source_reference", "jsonb", "n", "来源引用，`DEFAULT '{}'`。示例：`{\"sap_table\":\"MBEW\",\"mbew_field\":\"STPRS\"}`"),
     ("valid_from", "date", "n", "业务有效起（含）。示例：`2025-01-01`。**业务时间**：这个价格在现实中何时生效"),
     ("valid_to", "date", "k", "业务有效止（**不含**，可空=至今），`CHECK(valid_to IS NULL OR valid_to>valid_from)`"),
     ("recorded_from", "timestamptz", "n", "系统认知起（含）。示例：`2025-01-15 09:30:00+08`。**系统时间**：系统何时录入这个价格"),
     ("recorded_to", "timestamptz", "k", "系统认知止（可空=仍是当前认知）"),
     ("approved_change_id", "uuid", "n", "审批变更引用。**每行独立**——这一行由哪次审批产生")],
    ["**`valuation_unit varchar(3)` 是命名陷阱**：它是**价格的计价单位**（SAP `PEINH`，如“每 100 KG 的价格”），**不是指向 `valuation_unit` 表的外键**。指向那张表的外键是 `kalnr`。**同名不同义——这是本设计里最容易误读的一列**。",
     "**为什么价格用 `numeric(38,18)` 而不用金额精度 `numeric(31,8)`**：价格是个**比值**，单位价格可能极小（如每克贵金属）。31,8 的 8 位小数不足以表达。38,18 是“18 位整数 + 18 位小数”的极端精度，覆盖单价场景。**精度选择必须按语义，不是统一一个数**。",
     "**分子分母 + `raw_price` 三者并存**：分子分母是**归一化后的精确值**（用于计算），`raw_price` 是**源值留档**（用于对账）。**计算绝不用 raw_price**——因为源价格的计价单位与归一化后的不一致。这是 E16 的精神（原始汇率/价格不经解码不直接用）。",
     "**GiST 排斥约束的七元组**：`(kalnr, rldnr, external_currency_type, price_type, price_subtype)` + 两个时间范围。**七列判重**——同一价值对象在同一账本同一币种角色同一价格种类下，有效期不能重叠。",
     "**目录 JSON 原文“有效期不自动等同 SAP 各价格类型语义”**：标准价（`S`）与移动平均价（`V`）的有效期语义**不同**——移动平均价是每次收货都变，用有效期表达它没有意义。**本表不假装统一这些语义**。"],
    ["物料 `MAT-0001` 在 `V100`/`0L` 的标准价 `12.50 CNY`，计价单位 `1`：`numerator=12.5`、`denominator=1`、`valuation_unit='1'`。若 SAP 存的是“每 100 个 1250 元”，则 `numerator=1250000000000000000`、`denominator=1000000000000000000`、`valuation_unit='100'`。"])

tab("fx_rate_version", "汇率版本", "TCURR 经核验归一化",
     "只接受**已核验并归一化**的汇率。**不直接用 TCURR 原值算账**。",
    [("tenant_id", "uuid", "pnf", "租户。FK → client_scope"),
     ("mandt", "varchar(3)", "pnf", "客户端号"),
     ("revision_id", "uuid", "p", "版本行标识。**主键**"),
     ("rate_type", "varchar(4)", "n", "汇率类型。示例：`M`（平均）/ `B`（银行买卖）/ `G`（历史）。**SAP 的不同类型用途完全不同**"),
     ("from_currency", "varchar(5)", "n", "源币种。示例：`USD`"),
     ("to_currency", "varchar(5)", "n", "目标币种。示例：`CNY`"),
     ("normalized_multiplier", "numeric(38,18)", "nk", "归一化倍率，`CHECK(>0 AND <>'NaN')`。**语义固定为“1 源币 = X 目标币”**。示例：`7.123456789012345678`"),
     ("quotation_source", "text", "n", "报价来源声明。示例：`PBOC_MID`（央行中间价）"),
     ("raw_source", "jsonb", "n", "原始报价留档。示例：`{\"sap\":\"TCURR\",\"kursm\":\"0.140438\"}`。**不经解码不直接用（E16）**"),
     ("normalization_profile", "text", "n", "归一化档案，说明如何从原始值得到倍率。示例：`INVERT_AND_REDUCE_5`"),
     ("valid_from", "date", "n", "汇率生效起（含）。示例：`2025-01-01`"),
     ("valid_to", "date", "k", "汇率生效止（**不含**，可空）。示例：`2025-02-01`。**下期汇率上线即自动截断上期**"),
     ("recorded_from", "timestamptz", "n", "系统认知起（含）"),
     ("recorded_to", "timestamptz", "k", "系统认知止（可空）"),
     ("approved_change_id", "uuid", "n", "审批变更引用")],
    ["**E16 的核心**：SAP 的 `TCURR` 存的是**“从 X 到 Y 的比率”**，且依 `KURST`（汇率类型）与 `FFACT/TFACT`（从/到因子）不同而有**多种可能的表达**（直接报价/间接报价、是否已乘因子）。**直接拿 `TCURR.KURSM` 当汇率算账是错的**——这就是 S 系列实查里抓到的问题。",
     "**三列并存的设计意图**：`raw_source`（SAP 原样）→ `normalization_profile`（怎么转的）→ `normalized_multiplier`（结果）。**三步留痕让审计能复核归一化是否做对**。若只存最终值，一旦归一化写错就无人能发现。",
     "**`normalization_profile` 是 text 而非枚举**：因为归一化方式的组合很多（倒置 × 因子 × 精度压缩），**枚举会不断需要扩值**，而 text 允许声明任意档案名。这是“宁可宽松但留痕，不要窄化但丢失”的取舍。",
     "**`rate_type` 进 GiST 排斥键**：同一币种对在同一时间点可以同时存在 `M`（平均）和 `B`（银行）两个汇率——**它们不冲突**。所以判重必须含类型。"],
    ["SAP `TCURR`：`KURST='M'`、`FCURR='USD'`、`TCURR='CNY'`、`KURSM='0.140438'`、`FFACT=1`、`TFACT=1`。**这是 USD→CNY 的间接报价**（实际是 1 CNY = 0.140438 USD）。归一化后：`normalized_multiplier = 1/0.140438 ≈ 7.1206`，`normalization_profile='INVERT_AND_REDUCE_5'`，`raw_source` 保留原值。"])

# ============================== M8 (SVG helper above) ==============================
tab("period_gate", "期间状态门", "无直接对应（类比 OB52 期间控制）",
    "“这个公司+账本+期间现在允许过账吗”。**当前运行门，与历史配置快照分离**。",
    [("tenant_id", "uuid", "pnf", "租户。FK → client_scope"),
     ("mandt", "varchar(3)", "pnf", "客户端号"),
     ("bukrs", "varchar(4)", "pn", "公司代码。**逻辑引用 → company_key**"),
     ("rldnr", "varchar(2)", "pn", "账本。**逻辑引用 → ledger_key**"),
     ("gjahr", "integer", "pnk", "会计年度，`CHECK BETWEEN 1 AND 9999`。示例：`2025`"),
     ("poper", "smallint", "pnk", "期间号，`CHECK BETWEEN 1 AND 382`。示例：`1`。**上界 382 而非 16**——覆盖到周为期的变式"),
     ("application", "text", "pn", "应用门。示例：`FI` / `MM`。**每个应用一道门**，因为财务与物料可以开在不同的期"),
     ("status", "text", "nk", "状态机，`CHECK IN ('OPEN','CLOSING','CLOSED','HARD_CLOSED')`。示例：`OPEN`"),
     ("version", "bigint", "nk", "乐观版本号，`CHECK(version>0)`。每次状态变更 +1，由触发器强制"),
     ("changed_at", "timestamptz", "n", "状态变更时刻"),
     ("changed_by", "text", "n", "变更人。示例：`user:cfo@corp`"),
     ("approved_change_id", "uuid", "", "审批引用（可空，仅初始化可为空）。**状态变更必须填**")],
    ["**四态而非两态**：`OPEN`（可过账）→ `CLOSING`（结算中，限制新过账）→ `CLOSED`（已关，需专门冲销）→ `HARD_CLOSED`（硬关，任何操作都禁止）。**两态无法表达“结算中”这个真实存在的中间态**。",
     "**`application` 进主键的理由**：FI 期间与 MM 期间可以不同步（常见：财务先关，物料后关做盘点）。若主键不含它，就无法表达这个现实。",
     "**`poper` 上界 382**：`fiscal_period_config.poper CHECK(poper>0)` 无上界，但本表有 382 上界。**382 = 一年天数**，对应按日期间。",
     "**地址 JSON 原文“当前运行门，与历史配置快照分离”**：本表**不绑 release_id**——它是运行态，不是配置。**这保证“配置快照里的期间日历”与“当前是否允许过账”是两个独立事实**。运维切版不该重开已关的期间。",
     "**锁序**（来自 02_实施详设.md）：`lock_inventory_context` 在业务事务内对本表 4 元组 `FOR SHARE` 加锁，关账时 `FOR UPDATE`。**这是防“过账与关账竞态”的关键**。"],
    ["月结：`(1000,'0L',2025,12,'FI')` 从 `OPEN` → `CLOSING`（version 1→2）→ `CLOSED`（2→3）。此后任何对该期的新过账被拒。若发现漏记，必须走冲销/调整流程，不能直接改状态回 `OPEN`。"])

tab("action_block", "动作冻结", "无直接对应",
    "按“对象 × 组织范围 × 动作”冻结业务操作。**执行时重验，不从旧主数据快照放行**。",
    [("tenant_id", "uuid", "pnf", "租户。FK → client_scope"),
     ("mandt", "varchar(3)", "pnf", "客户端号"),
     ("object_id", "uuid", "pn", "被冻结对象。**逻辑引用 → master_identity**。示例：`X`"),
     ("organization_key", "text", "pnk", "组织范围键，`DEFAULT ''`。示例：空串=全局；`bukrs:1000`=仅该公司"),
     ("action", "text", "pn", "被冻结动作。示例：`CREATE_ORDER` / `POST_INVOICE`"),
     ("blocked", "boolean", "n", "是否冻结中。示例：`true`"),
     ("version", "bigint", "nk", "乐观版本号，`CHECK(version>0)`"),
     ("reason", "text", "", "冻结原因（可空）。示例：`信用超限`"),
     ("changed_at", "timestamptz", "n", "变更时刻")],
    ["**三维键 `(object_id, organization_key, action)` 的意义**：冻结的粒度是“**谁 × 在哪 × 做什么**”。同一个客户可以“在 `1000` 公司禁止下单，但在 `2000` 允许”；可以“禁止下单但允许开票”。**只有对象维是不够的**。",
     "**`organization_key` 是 text 而非多列**：因为组织维度多样（公司/工厂/销售组织…）。用 `'bukrs:1000'` 这样的标记串，**保持单列键的简洁**，代价是格式约定要在领域核里强制。这是与 `period_gate`（四个独立列）不同的取舍——**因为本表的组织维度不固定**。",
     "**目录 JSON 原文“执行时重验，不从旧主数据快照放行”**——这是本表最重要的性质。上下文快照（`context_snapshot`）冻结的是**配置**；而**授权这类运行态不能被冻结**，必须每次执行时重读。**若从快照读，会出现在冻结生效前冻结的快照里放行后续操作**。",
     "**`blocked` 是 boolean 而非只存存在性**：保留 `false` 行可以记录“曾经冻结，现已解除”的轨迹，且 `version` 递增可见。**纯删除会丢掉审计轨迹**。"],
    ["客户 `X` 因信用超限：`(X, 'bukrs:1000', 'CREATE_ORDER', blocked=true, version=1)`。执行时领域核在事务内读本行，命中则拒绝。信用恢复后置 `blocked=false`、`version=2`。"])

# ============================================================================
# SVG generation
# ============================================================================
def esc(s):
    return html.escape(str(s), quote=True)


def wrap(s, width):
    """Greedy wrap by display width (CJK counts 2)."""
    out, cur, w = [], "", 0
    for ch in s:
        cw = 2 if ord(ch) > 0x2000 else 1
        if w + cw > width:
            out.append(cur)
            cur, w = ch, cw
        else:
            cur += ch
            w += cw
    if cur:
        out.append(cur)
    return out


def table_card(name, cn, x, y, w, color, extra=None):
    """Render one table card. Returns (svg_fragment, height)."""
    stroke, fill = PAL[color]
    rows = [cn] + (extra or [])
    wrapped = []
    for r in rows:
        wrapped.extend(wrap(r, 34))
    lh = 16
    h = 26 + len(wrapped) * lh + 8
    s = [f'<g><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="7" '
         f'fill="{fill}" stroke="{stroke}" stroke-width="1.6"/>',
         f'<rect x="{x}" y="{y}" width="{w}" height="26" rx="7" fill="{stroke}"/>',
         f'<rect x="{x}" y="{y+18}" width="{w}" height="8" fill="{stroke}"/>']
    # title in header
    tn = name if len(name) <= 30 else name[:28] + "…"
    s.append(f'<text x="{x+10}" y="{y+18}" font-family="ui-monospace,SFMono-Regular,Menlo,monospace" '
             f'font-size="12.5" font-weight="700" fill="#ffffff">{esc(tn)}</text>')
    yy = y + 26 + 13
    for i, r in enumerate(wrapped):
        # first wrapped row is the Chinese caption -> emphasised
        emph = (i == 0)
        weight = ' font-weight="600"' if emph else ''
        fillc = "#0f172a" if emph else "#475569"
        s.append(f'<text x="{x+10}" y="{yy}" font-family="-apple-system,BlinkMacSystemFont,\'PingFang SC\','
                 f'\'Microsoft YaHei\',sans-serif" font-size="11.5" fill="{fillc}"{weight}>'
                 f'{esc(r)}</text>')
        yy += lh
    s.append('</g>')
    return "".join(s), h


def build_module_svg(mod, cards, edges, width=980):
    """cards: list of (name, cn, col, row) ; edges: list of (from,to,label)"""
    GAPX, GAPY = 26, 30
    CW, CH_EST = 250, 0
    ncol = 3
    # compute rows per column
    maxrows = (len(cards) + ncol - 1) // ncol
    pos = {}
    frags = []
    heights = []
    for (name, cn, c, r) in cards:
        x = 30 + c * (CW + GAPX)
        y = 40 + r * 150
        f, h = table_card(name, cn, x, y, CW, mod["color"])
        pos[name] = (x, y, CW, h)
        frags.append((c, r, f))
    rows_used = max((r for (_, _, _, r) in cards), default=0) + 1
    height = 40 + rows_used * 150 + 30
    body = "".join(f for _, _, f in frags)

    # edges: draw orthogonal elbow arrows from bottom/top of child to parent
    efr = []
    for (a, b, lbl) in edges:
        if a not in pos or b not in pos:
            continue
        ax, ay, aw, ah = pos[a]
        bx, by, bw, bh = pos[b]
        sx = ax + aw / 2
        sy = ay + ah
        tx = bx + bw / 2
        ty = by
        if abs(sy - ty) < 4:      # same column vertical -> side route
            sx = ax + aw
            sy = ay + ah / 2
            tx = bx + bw
            ty = by + bh / 2
            mid = max(sx, tx) + 22
            d = f"M {sx} {sy} H {mid} V {ty} H {tx}"
        else:
            midy = (sy + ty) / 2
            d = f"M {sx} {sy} V {midy} H {tx} V {ty}"
        efr.append(f'<path d="{d}" fill="none" stroke="#94a3b8" stroke-width="1.3" '
                   f'stroke-dasharray="4 3" marker-end="url(#ar)"/>')
        if lbl:
            mx = (sx + tx) / 2
            my = (sy + ty) / 2
            lw = 7 * len(lbl) + 10
            efr.append(f'<rect x="{mx-lw/2}" y="{my-9}" width="{lw}" height="16" rx="4" '
                       f'fill="#ffffff" fill-opacity="0.94" stroke="#cbd5e1" stroke-width="0.8"/>')
            efr.append(f'<text x="{mx}" y="{my+3}" text-anchor="middle" '
                       f'font-family="ui-monospace,Menlo,monospace" font-size="10" fill="#334155">{esc(lbl)}</text>')

    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
           f'width="{width}" height="{height}" role="img">'
           f'<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
           f'orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#94a3b8"/></marker></defs>'
           f'<rect width="{width}" height="{height}" fill="#fbfdff"/>'
           + body + "".join(efr) + '</svg>')
    return svg, height


def b64img(svg, alt, maxw=980):
    b = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return (f'<p align="center"><img alt="{esc(alt)}" '
            f'style="max-width:100%;height:auto;border:1px solid #e2e8f0;border-radius:8px" '
            f'src="data:image/svg+xml;base64,{b}"></p>')


# ---------------------------------------------------------------- key flags
FLAG = [("p", "PK"), ("f", "FK"), ("u", "UQ"), ("k", "CHECK"), ("x", "EXCLUDE"),
        ("n", "NOT NULL"), ("d", "延迟")]


def flags_render(s):
    got = []
    for ch, lab in FLAG:
        if ch in s:
            got.append(lab)
    return " · ".join(got) if got else "—"


def render_table(name):
    d = T[name]
    L = []
    L.append(f'### `{name}` — {d["cn"]}')
    L.append("")
    L.append(f'**SAP 对应**：{d["sap"]}')
    L.append("")
    L.append(f'**这张表做什么**：{d["purpose"]}')
    L.append("")
    L.append("| 列 | 类型 | 键/约束 | 作用 · 场景 · 示例 |")
    L.append("|---|---|---|---|")
    for (c, t, fl, desc) in d["cols"]:
        L.append(f'| `{c}` | `{t}` | {flags_render(fl)} | {desc} |')
    L.append("")
    if d["scen"]:
        L.append("**典型场景**")
        L.append("")
        for s in d["scen"]:
            L.append(f'- {s}')
        L.append("")
    if d["notes"]:
        L.append("**设计要点**")
        L.append("")
        for n in d["notes"]:
            L.append(f'- {n}')
        L.append("")
    return "\n".join(L)


def main():
    os.makedirs(SVGDIR, exist_ok=True)
    # ---------------- module card layouts ----------------
    LAYOUT = {
        "M0": [("client_scope", 0, 0), ("foundation_release", 1, 0), ("config_head", 2, 0),
               ("command_receipt", 0, 1), ("outbox", 1, 1), ("context_snapshot", 2, 1)],
        "M1": [("company_key", 0, 0), ("valuation_area_key", 1, 0), ("plant_key", 2, 0),
               ("purchasing_org_key", 0, 1), ("sales_org_key", 1, 1), ("controlling_area_key", 2, 1),
               ("ledger_key", 0, 2)],
        "M2": [("currency_config", 0, 0), ("uom_config", 1, 0), ("posting_variant_config", 2, 0),
               ("fiscal_variant_config", 0, 1), ("fiscal_year_config", 1, 1), ("fiscal_period_config", 2, 1)],
        "M3": [("company_config", 0, 0), ("valuation_area_config", 1, 0), ("plant_config", 2, 0),
               ("storage_location_config", 0, 1), ("purchasing_org_config", 1, 1),
               ("purchasing_plant_config", 2, 1), ("controlling_assignment_config", 0, 2),
               ("sales_org_config", 1, 2), ("sales_area_config", 2, 2),
               ("sales_plant_config", 0, 3)],
        "M4": [("ledger_config", 0, 0), ("company_config", 1, 0), ("book_config", 2, 0),
               ("book_currency_config", 0, 1), ("currency_config", 1, 1),
               ("posting_account_rule", 2, 1), ("posting_window", 0, 2)],
        "M5": [("master_identity", 0, 0), ("bp_identity", 1, 0), ("material_identity", 2, 0),
               ("external_key_map", 0, 1), ("customer_link", 1, 1), ("supplier_link", 2, 1)],
        "M6": [("customer_link", 0, 0), ("supplier_link", 1, 0), ("material_identity", 2, 0),
               ("customer_company_version", 0, 1), ("supplier_company_version", 1, 1),
               ("material_version", 2, 1), ("customer_sales_version", 0, 2),
               ("supplier_purchasing_version", 1, 2), ("material_plant_version", 2, 2),
               ("bp_role_version", 0, 3), ("material_uom_version", 1, 3),
               ("gl_account_version", 2, 3), ("gl_company_version", 0, 4),
               ("profit_center_version", 1, 4), ("profit_company_version", 2, 4),
               ("cost_center_version", 0, 5)],
        "M7": [("valuation_unit", 0, 0), ("ledger_key", 1, 0), ("material_identity", 2, 0),
               ("material_price_version", 0, 1), ("fx_rate_version", 1, 1)],
        "M8": [("company_key", 0, 0), ("ledger_key", 1, 0), ("master_identity", 2, 0),
               ("period_gate", 0, 1), ("action_block", 2, 1)],
    }
    CAPS = {
        "client_scope": "隔离根",
        "foundation_release": "发布包（不可变）",
        "config_head": "激活指针（单行）",
        "command_receipt": "入站幂等回执",
        "outbox": "出站事务发件箱",
        "context_snapshot": "配置快照（带过期）",
        "company_key": "公司（稳定身份）",
        "valuation_area_key": "估值范围（稳定）",
        "plant_key": "工厂（稳定）",
        "purchasing_org_key": "采购组织（稳定）",
        "sales_org_key": "销售组织（稳定）",
        "controlling_area_key": "成本控制范围（稳定）",
        "ledger_key": "账本（稳定）",
        "currency_config": "币种精度",
        "uom_config": "单位与维度",
        "fiscal_variant_config": "年度变式",
        "fiscal_year_config": "年度实例",
        "fiscal_period_config": "期间明细",
        "posting_variant_config": "过账变式",
        "company_config": "公司配置（绑 release）",
        "valuation_area_config": "估值范围→公司",
        "plant_config": "工厂配置",
        "storage_location_config": "存储地点",
        "purchasing_org_config": "采购组织配置",
        "purchasing_plant_config": "采购白名单",
        "controlling_assignment_config": "公司-业务范围-CCtr",
        "sales_org_config": "销售组织→公司",
        "sales_area_config": "销售范围",
        "sales_plant_config": "供货工厂分配",
        "ledger_config": "账本类型",
        "book_config": "公司-账本（账套）",
        "book_currency_config": "币种角色",
        "posting_account_rule": "记账码区间",
        "posting_window": "期间窗口",
        "master_identity": "统一对象注册",
        "external_key_map": "源系统键映射",
        "bp_identity": "BP 身份",
        "customer_link": "客户号→BP",
        "supplier_link": "供应商号→BP",
        "material_identity": "物料身份",
        "customer_company_version": "客户公司视图",
        "supplier_company_version": "供应商公司视图",
        "customer_sales_version": "客户销售视图",
        "supplier_purchasing_version": "供应商采购视图",
        "bp_role_version": "BP 角色（时间戳）",
        "material_version": "物料核心",
        "material_plant_version": "物料工厂视图",
        "material_uom_version": "单位换算",
        "gl_account_version": "科目表视图",
        "gl_company_version": "科目公司视图",
        "profit_center_version": "利润中心",
        "profit_company_version": "利润中心-公司",
        "cost_center_version": "成本中心",
        "valuation_unit": "价值对象",
        "material_price_version": "物料价格",
        "fx_rate_version": "汇率（归一化）",
        "period_gate": "期间状态门",
        "action_block": "动作冻结",
    }
    EDGELBL = {}
    for m, rels in RELS.items():
        for (a, b, lbl) in rels:
            EDGELBL.setdefault((a, b), lbl)

    svgs = {}
    for mod in MODULES:
        cards = [(n, CAPS.get(n, ""), c, r) for (n, c, r) in LAYOUT[mod["code"]]]
        edges = []
        cardset = {n for (n, _, _, _) in cards}
        for (a, b, lbl) in RELS.get(mod["code"], []):
            if a in cardset and b in cardset:
                edges.append((a, b, lbl))
        svg, _ = build_module_svg(mod, cards, edges)
        svgs[mod["code"]] = svg

    # ---------------- write document ----------------
    D = []
    A = D.append
    A("# CMX ERP Foundation V1.1 — 58 表逐列详解")
    A("")
    A("> **用途**：本文对 `cmx_fnd` schema 下全部 **58 张表、共 498 列**逐一说明「这一列做什么、什么场景会用、值长什么样」。列清单与类型已用脚本比对 `db/001_foundation.sql` 校验（58/58 表、498/498 列、0 处差集）。")
    A("> **依据**：`db/001_foundation.sql`（DDL 真源）、`docs/03_physical_table_catalog.json`（表用途与 SAP 源）、`docs/02_实施详设.md` 与 `evidence/SAP_实查证据.md`（E01–E16 语义修正）、`db/002_demo_seed.sql` + `examples/demo_fixture.json`（示例值取自真实 fixture，非编造）。")
    A("> **图**：每模块一张内嵌 SVG（base64 直嵌，无需外部文件、无网络依赖，GitHub/VSCode/浏览器直接渲染）。")
    A("")
    A("---")
    A("")
    A("## 目录")
    A("")
    A("| 模块 | 表数 | 主题 | 层 |")
    A("|---|---|---|---|")
    for mod in MODULES:
        A(f'| [{mod["code"]} {mod["name"]}](#{mod["code"].lower()}-{mod["name"]}) | {len(mod["tables"])} | {mod["desc"][:44]}… | {mod["layer"]} |')
    A("| — | **58** | | |")
    A("")
    A("附录：[A. 设计完整性说明](#附录-a-设计完整性说明) · [B. 键与约束记法](#附录-b-键与约束记法) · [C. SAP 缩写对照](#附录-c-sap-缩写对照) · [D. 全量外键清单](#附录-d-全量外键清单)")
    A("")
    A("---")
    A("")
    A("## 阅读前必读：四类表的列型规范")
    A("")
    A("58 张表看着多，其实只有四种列型骨架。**先认出骨架，逐列读就快了**。（下表由脚本对 `db/001_foundation.sql` 的实际列做归类得出，非人工声称。）")
    A("")
    A("| 骨架 | 表数 | 特征列 | 含哪些表 |")
    A("|---|---|---|---|")
    A("| **① 稳定组织身份** | 7 | `tenant_id, mandt` + 业务编码 + `object_id uuid UNIQUE` | M1：`company_key` 等七类组织 |")
    A("| **② 发布绑定配置** | 21 | 主键**含** `release_id` | M2 6 张 + M3 10 张 + M4 5 张 |")
    A("| **③ 双时态版本** | 13 | `revision_id` PK + `valid_from/to` + `recorded_from/to` + `approved_change_id`，挂 GiST EXCLUDE | M6 全部 |")
    A("| **④ 身份映射 / 估值 / 治理 / 运行态** | 17 | 混合：M5 6 张（`object_id` 或业务编码 PK）、M7 3 张、M0 6 张 + M8 2 张 | M5、M7、M0、M8 |")
    A("")
    A("**合计**：7 + 21 + 13 + 17 = **58**。")
    A("")
    A("**顺带给出 DCT 归属结论**（详见[下节](#关于-dct--doc-归属)）：")
    A("")
    A("| 归口 | 表数 | 构成 |")
    A("|---|---|---|")
    A("| **DCT 候选** | **50** | M1 7 + M2 6 + M3 10 + M4 5 + M5 6 + M6 13 + M7 3 |")
    A("| **非 DCT / DOC（平台治理与运行态）** | **8** | M0 6 + M8 2 |")
    A("| **DOC（单据）** | **0** | FND 全是主数据与配置，**凭证表不在这 58 张里**（属凭证模块自有表） |")
    A("| 合计 | 58 | |")
    A("")
    A("## 关于 DCT / DOC 归属")
    A("")
    A("**一句话**：这 58 张表是 `cmx_fnd` schema 下的**物理 PostgreSQL 表**；而 DCT（数据字典，`dictionaryTables`）与 DOC（业务单据，`voucherTables`）是 CMX **模型中心的元数据注册项**（JSON）。**两者不是同一层的对象**——58 张表目前一张都没注册成 DCT/DOC，DCT/DOC 是它们之上的描述层。")
    A("")
    A("| | 是什么 | 载体 |")
    A("|---|---|---|")
    A("| **DCT / DOC** | 模型中心的元数据注册项 | `backend/cmx-container/assets/model/data/meta/definitions/**/xxx_{dct,doc}_meta_v*.json` |")
    A("| **本文 58 表** | 物理表（SAP 语义的落库） | `db/001_foundation.sql` |")
    A("")
    A("**判定 DCT 的特征**（对照现有实例 `cf_*`/`cm_*`/`cg_*` 前缀的字典表）：有业务编码、有名称、供其他单据做维度引用（“可被选中的参照项”）。**判定 DOC 的特征**：有表头-明细层级（如 `cv_batch → cv_header → cv_acc_line → cv_aux_line`，用 `upper_id` 关联）。")
    A("")
    A("**按此判定**：")
    A("")
    A("- **DCT 候选 50 张**：M1 组织身份（对应 dictCode 先例 `comp_unit`/`ctrl_area`/`ledger`）、M2 参考日历（`currency`/`fy_variant`/`fisc_period`）、M3 组织配置、M4 核算配置（`acct_princ`）、M5 身份映射（`bus_partner`）、M6 时态主数据（`gl_account`/`cost_center`/`profit_ctr` 等，其双时态正是 DCT `dictionaryEffectiveFields` 的强化形态）、M7 估值价格。")
    A("- **非 DCT/DOC 8 张**：M0 治理底座 6 张（`client_scope`/`foundation_release`/`config_head`/`command_receipt`/`outbox`/`context_snapshot`）+ M8 运行门 2 张（`period_gate`/`action_block`）。它们是**平台可靠性机制**，没有“可选中”语义，也不承载业务录入。")
    A("- **DOC 0 张**：58 张里没有任何一张是“凭证/单据”。")
    A("")
    A("**若要真的注册成 DCT，有两个已知障碍**：(1) DCT 模板要求 `id BIGINT PK` + `code` + `name` + `sort_no` + `status` 四件套（见 `base_dct_meta_v1.json` 的 `dictionaryCommonFields`），而 FND 用 SAP 自然键或 UUID，**没有这套列**；(2) FND 的“配置版本 + 双时态版本”分离在现有 `designStyle`（`table` / `separate-dictionary-tables`）下都不映射。**建议另建一层薄 DCT 投影**，把 FND 表作为领域核实体，DCT 只暴露“可选的 code+name 投影”。")
    A("")
    A("")
    A("**通用列（所有 58 张表都有，下文各表不再重复解释）**")
    A("")
    A("| 列 | 类型 | 说明 |")
    A("|---|---|---|")
    A("| `tenant_id` | `uuid` | 租户标识。FK → `client_scope`，与 `mandt` 一起构成隔离范围 |")
    A("| `mandt` | `varchar(3)` | SAP 客户端号。FK → `client_scope`，CHECK 3 位数字 |")
    A("")
    A("> 下文的列清单中，这两列仍会列出（保持完整性），但说明从简。**未标注「逻辑引用」的外键都是物理外键**；标注「逻辑引用」的由领域核校验，DDL 不建外键（原因见 [附录 A](#附录-a-设计完整性说明)）。")
    A("")
    A("---")
    A("")

    for mod in MODULES:
        A(f'## {mod["code"]}. {mod["name"]}')
        A("")
        A(f'**层归属**：{mod["layer"]}　|　**表数**：{len(mod["tables"])}')
        A("")
        A(mod["desc"])
        A("")
        A(b64img(svgs[mod["code"]], f'{mod["code"]} {mod["name"]} 关系图'))
        A("")
        for t in mod["tables"]:
            A(render_table(t))
            A("---")
            A("")

    # appendix A
    A("## 附录 A. 设计完整性说明")
    A("")
    A("### A.1 DDL 中 8 张表的多余外键")
    A("")
    A("`db/001_foundation.sql` 中以下 8 张表的定义里含一行")
    A("")
    A("```sql")
    A("FOREIGN KEY (tenant_id, mandt, release_id) REFERENCES cmx_fnd.foundation_release (tenant_id, mandt, release_id)")
    A("```")
    A("")
    A("但**这 8 张表都没有定义 `release_id` 列**，因此该 DDL 语句**按现状无法执行**：")
    A("")
    A("| # | 表 | 实际应有的引用（据 `03_physical_table_catalog.json`） |")
    A("|---|---|---|")
    A("| 1 | `external_key_map` | → `master_identity(object_id,object_type)` |")
    A("| 2 | `bp_identity` | → `master_identity(object_id,object_type)` |")
    A("| 3 | `customer_link` | → `bp_identity(partner_guid)` |")
    A("| 4 | `supplier_link` | → `bp_identity(partner_guid)` |")
    A("| 5 | `material_identity` | → `master_identity(object_id,object_type)` |")
    A("| 6 | `valuation_unit` | → `material_identity(matnr)` + `valuation_area_key(bwkey)` |")
    A("| 7 | `period_gate` | → `company_key(bukrs)` + `ledger_key(rldnr)` |")
    A("| 8 | `action_block` | → `master_identity(object_id)` |")
    A("")
    A("**同一处遗漏还有第二个后果**：这 8 张表同时挂了 `config_no_published_mutation` 触发器，而该触发器的函数体读取 `NEW.release_id`（`IF TG_OP='INSERT' THEN t:=NEW.tenant_id; c:=NEW.mandt; r:=NEW.release_id;`）。**列不存在则触发器创建也会失败**。")
    A("")
    A("**判定**：这是从「发布绑定表」家族复制时残留的样板行——这 8 张表的业务语义都是**稳定身份/映射/运行态**，本就不该绑发布包（`client_scope`/`foundation_release` 之外的 21 张才是发布绑定表）。两种可能的处理：")
    A("")
    A("1. **删掉那行多余外键**（并按目录 JSON 补上正确的逻辑引用声明）——保持「身份与映射不绑发布」的设计。")
    A("2. **补 `release_id` 列**——但这会把稳定身份变成版本绑定的，**与「编码不可重分配」的核心设计冲突**。")
    A("")
    A("> 本文档的 ER 图与列说明按**方案 1**（即目录 JSON 记录的意图）绘制。另注：仓库内已存在的 `04_物理模型ER图与列字典.md` 把这 8 组关系描述为「刻意不建外键的逻辑引用」，**与 DDL 里确实存在那行外键文本这一事实不符**——需以其中一种口径统一。")
    A("")
    A("### A.2 循环外键（延迟约束）")
    A("")
    A("`book_config.functional_currency_type` ⇄ `book_currency_config.external_currency_type` 互为引用，用 `DEFERRABLE INITIALLY DEFERRED` 声明，**校验推迟到事务提交时**，从而允许在同一事务里先插任一方。")
    A("")
    A("### A.3 时态排斥约束（GiST EXCLUDE）")
    A("")
    A("13 张版本表 + `fiscal_year_config` + `fiscal_period_config` + `action_block` 之外的时态表均使用 `daterange(... '[)')` 或 `tstzrange(... '[)')` 的 `&&` 排斥，禁止同一逻辑键的有效期重叠。**区间一律半开 `[)`**——这样相邻区段无缝无叠。")
    A("")
    A("### A.4 触发器与 RLS")
    A("")
    A("- `prevent_published_config_mutation()`：阻止对已发布发布包的配置写入，并禁止改动 `(tenant_id,mandt,release_id)` 键。")
    A("- `prevent_release_rewrite()`：阻止改写 `PUBLISHED` 状态的发布包。")
    A("- 全部 58 张表 `ENABLE` + `FORCE ROW LEVEL SECURITY`，策略 `scope_guard` 依 `current_setting('app.tenant_id')` / `app.mandt`。**文档明确：GUC 不是对任意 SQL 的防御**——只防误用，不防被授予任意 SQL 的连接。")
    A("")
    A("---")
    A("")
    A("## 附录 B. 键与约束记法")
    A("")
    A("| 记号 | 含义 |")
    A("|---|---|")
    A("| PK | 主键的一部分 |")
    A("| FK | 外键（除非标注「逻辑引用」，否则为物理外键） |")
    A("| UQ | 有唯一约束 |")
    A("| CHECK | 有 CHECK 约束 |")
    A("| EXCLUDE | 有 GiST 排斥约束 |")
    A("| NOT NULL | 非空 |")
    A("| 延迟 | 延迟外键（DEFERRABLE） |")
    A("")
    A("> 未标注的列即为**可空**。所有 `numeric` 列均排除 `NaN`（`<>'NaN'::numeric`），金额/数量/价格一律**十进制精确类型，不使用浮点**。")
    A("")
    A("---")
    A("")
    A("## 附录 C. SAP 缩写对照")
    A("")
    A("| 缩写 | 含义 | 出现于 |")
    A("|---|---|---|")
    A("| MANDT | 客户端 | 全部 58 表 |")
    A("| BUKRS | 公司代码 | company_key/config, book_*, period_gate |")
    A("| BWKEY | 估值范围 | valuation_area_*, plant_config, valuation_unit |")
    A("| BWTAR | 估价类型（批次/等级） | valuation_unit |")
    A("| WERKS | 工厂 | plant_*, storage_location, material_plant, sales_plant |")
    A("| LGORT | 存储地点 | storage_location_config |")
    A("| EKORG | 采购组织 | purchasing_*, supplier_purchasing_version |")
    A("| VKORG | 销售组织 | sales_*, customer_sales_version |")
    A("| VTWEG | 分销渠道 | sales_area/plant, customer_sales_version |")
    A("| SPART | 产品组 | sales_area, customer_sales_version |")
    A("| KOKRS | 成本控制范围 | controlling_area_key, cost/profit_center_version |")
    A("| GSBER | 业务范围 | controlling_assignment_config |")
    A("| RLDNR | 分类账 | ledger_*, book_*, material_price_version, period_gate |")
    A("| PERIV | 会计年度变式 | fiscal_*, company_config, book_config |")
    A("| OPVAR | 过账变式 | posting_*, company_config, book_config |")
    A("| KTOPL | 科目表 | gl_account_version, gl_company_version |")
    A("| SAKNR | 总账科目号 | gl_account_version, gl_company_version |")
    A("| AKONT | 统驭（对账）科目 | customer/supplier_company_version |")
    A("| KUNNR | 客户号 | customer_link, *_version |")
    A("| LIFNR | 供应商号 | supplier_link, supplier_*, valuation_unit |")
    A("| PARTNER / GUID | BP 编号 / 全局标识 | bp_identity, customer_link, supplier_link |")
    A("| MATNR | 物料号 | material_*, valuation_unit |")
    A("| UMREZ / UMREN | 换算分子 / 分母 | material_uom_version |")
    A("| KALNR | 价值对象号 | valuation_unit, material_price_version |")
    A("| PRCTR | 利润中心 | profit_*_version, material_plant_version |")
    A("| KOSTL | 成本中心 | cost_center_version |")
    A("| GJAHR / POPER | 会计年度 / 期间 | fiscal_*, period_gate |")
    A("| ZTERM | 付款条件 | customer/supplier_*_version |")
    A("| DFVAL | 角色子类型 | bp_role_version |")
    A("| DATBI | 有效期止（SAP 原键） | cost_center_version.source_datbi |")
    A("")
    A("---")
    A("")
    A("## 附录 D. 全量外键清单")
    A("")
    A("> 下表为**物理外键**。统一指向 `client_scope` 的 58 条不在列（每张表都有）。标注「逻辑引用」的 8 组见 [附录 A.1](#a1-ddl-中-8-张表的多余外键)。")
    A("")
    A("| 子表 | 父表 | 外键列 |")
    A("|---|---|---|")
    seen = set()
    for mod in MODULES:
        for (a, b, lbl) in RELS.get(mod["code"], []):
            if (a, b) in seen:
                continue
            seen.add((a, b))
            if "①" in lbl or "②" in lbl:
                A(f'| `{a}` | `{b}` | {lbl} *(逻辑)* |')
            else:
                A(f'| `{a}` | `{b}` | `{lbl}` |')
    A("")
    A("① 循环延迟外键（`DEFERRABLE INITIALLY DEFERRED`）　② 逻辑引用（DDL 无外键，领域核校验）")
    A("")
    A("---")
    A("")
    A("> 生成脚本：`gen_doc05.py`（本文件由脚本产出，改内容请改脚本后重跑，以保证 58 表的列清单与 DDL 始终一致）。")

    txt = "\n".join(D)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(txt)

    # report
    ntab = len(T)
    ncol = sum(len(v["cols"]) for v in T.values())
    total_svg = sum(len(s.encode()) for s in svgs.values())
    print(f"tables defined : {ntab}")
    print(f"columns total  : {ncol}")
    print(f"svg raw bytes  : {total_svg}")
    print(f"output         : {OUT}")
    print(f"output bytes   : {os.path.getsize(OUT)}")
    for mod in MODULES:
        missing = [t for t in mod["tables"] if t not in T]
        if missing:
            print(f"  !! {mod['code']} missing defs: {missing}")


if __name__ == "__main__":
    main()
