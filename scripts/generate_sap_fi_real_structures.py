#!/usr/bin/env python3
"""Generate an offline reference of real SAP FI table structures from FI meta JSON."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen
import datetime as dt
import json
import re


ROOT = Path(__file__).resolve().parents[1]
DCT_JSON = ROOT / "CMXPortalManager/cmx-node-server/data/meta/definitions/fi/fico/sap_fi_dct_meta_v1.json"
DOC_JSON = ROOT / "CMXPortalManager/cmx-node-server/data/meta/definitions/fi/fico/sap_fi_doc_meta_v1.json"
OUT = ROOT / "docs" / "sap_fi_real_table_structures.html"
CACHE = ROOT / "docs" / ".cache" / "sap_tables"
ERP_BASE = "https://www.erpexplorer.com/sap/s4/table/"
PANDA_BASE = "https://datapanda.eu/en/sap/table/"


@dataclass
class SapTableSpec:
    table: str
    title: str
    zh_title: str
    recommended_name: str
    source_kind: str
    meta_object: str
    meta_file: str
    reason: str


@dataclass
class Field:
    pos: int
    name: str
    english: str
    domain: str
    checktable: str
    data_element: str
    dtype: str
    length: str
    decimals: str
    values: str


class TdTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_tr = False
        self.in_td = False
        self.rows: list[list[str]] = []
        self.current: list[str] = []
        self.buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self.in_tr = True
            self.current = []
        elif self.in_tr and tag == "td":
            self.in_td = True
            self.buffer = []

    def handle_endtag(self, tag: str) -> None:
        if self.in_tr and tag == "td":
            self.current.append(" ".join("".join(self.buffer).split()))
            self.in_td = False
        elif tag == "tr" and self.in_tr:
            if self.current:
                self.rows.append(self.current)
            self.in_tr = False

    def handle_data(self, data: str) -> None:
        if self.in_td:
            self.buffer.append(data)


def fetch(url: str, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.stat().st_size < 8_000:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=60) as response:
            path.write_bytes(response.read())
    return path.read_text(errors="ignore")


def parse_erpexplorer(html: str) -> list[Field]:
    parser = TdTableParser()
    parser.feed(html)
    fields: list[Field] = []
    for row in parser.rows:
        if len(row) >= 11 and row[2].isdigit() and re.match(r"^[A-Z0-9_./]+$", row[3]):
            fields.append(
                Field(
                    pos=int(row[2]),
                    name=row[3],
                    english=row[4],
                    domain=row[5],
                    checktable=row[6],
                    data_element=row[7],
                    dtype=row[8],
                    length=str(int(row[9])) if row[9].isdigit() else row[9],
                    decimals=str(int(row[10])) if row[10].isdigit() else row[10],
                    values=row[11] if len(row) > 11 else "",
                )
            )
    return fields


def parse_datapanda(html: str) -> list[Field]:
    parser = TdTableParser()
    parser.feed(html)
    fields: list[Field] = []
    for row in parser.rows:
        if len(row) >= 7 and re.match(r"^[A-Z0-9_./]+$", row[0]):
            fields.append(
                Field(
                    pos=len(fields) + 1,
                    name=row[0],
                    english=row[1],
                    domain="",
                    checktable=row[5],
                    data_element=row[6],
                    dtype=row[2],
                    length=str(int(row[3])) if row[3].isdigit() else row[3],
                    decimals=str(int(row[4])) if row[4].isdigit() else row[4],
                    values=row[7] if len(row) > 7 else "",
                )
            )
    return fields


def read_meta_specs() -> list[SapTableSpec]:
    dct = json.loads(DCT_JSON.read_text())
    doc = json.loads(DOC_JSON.read_text())
    specs: list[SapTableSpec] = [
        SapTableSpec("BKPF", "Accounting Document Header", "会计凭证抬头", "accounting_document_header", "DOC", "sap_fi_document_header", DOC_JSON.name, "DOC 凭证头 tableAlias 明确对应 BKPF"),
        SapTableSpec("BSEG", "Accounting Document Segment", "会计凭证行项目", "accounting_document_item", "DOC", "sap_fi_document_item", DOC_JSON.name, "DOC 行项目 tableAlias 明确对应 BSEG"),
    ]
    mapping = {
        "company": [("T880", "Company", "公司/合并主体", "company")],
        "company_code": [("T001", "Company Codes", "公司代码", "company_code")],
        "business_area": [("TGSB", "Business Areas", "业务范围", "business_area")],
        "functional_area": [("TFKB", "Functional Areas", "功能范围", "functional_area")],
        "segment": [("FAGL_SEGM", "Segments", "分部", "segment")],
        "controlling_area": [("TKA01", "Controlling Areas", "成本控制范围", "controlling_area")],
        "profit_center": [("CEPC", "Profit Center Master Data", "利润中心主数据", "profit_center")],
        "cost_center": [("CSKS", "Cost Center Master Data", "成本中心主数据", "cost_center")],
        "chart_of_accounts": [("T004", "Directory of Charts of Accounts", "会计科目表目录", "chart_of_accounts")],
        "gl_account": [("SKA1", "G/L Account Master Chart of Accounts", "总账科目主数据-科目表层", "gl_account_chart"), ("SKB1", "G/L Account Master Company Code", "总账科目主数据-公司代码层", "gl_account_company_code")],
        "account_group": [("T077S", "Account Groups", "科目组", "account_group")],
        "fs_version": [("T011", "Financial Statement Versions", "财务报表版本", "financial_statement_version")],
        "document_type": [("T003", "Document Types", "凭证类型", "document_type")],
        "posting_key": [("TBSL", "Posting Keys", "记账码", "posting_key")],
        "special_gl_ind": [("T074", "Special G/L Indicators", "特别总账标识", "special_gl_indicator")],
        "field_status_group": [("T004G", "Field Status Groups", "字段状态组", "field_status_group")],
        "currency": [("TCURC", "Currency Codes", "货币代码", "currency")],
        "exchange_rate_type": [("TCURV", "Exchange Rate Types", "汇率类型", "exchange_rate_type")],
        "fiscal_year_variant": [("T009", "Fiscal Year Variants", "会计年度变式", "fiscal_year_variant")],
        "fiscal_period": [("T009B", "Fiscal Year Variant Periods", "会计年度变式期间", "fiscal_period")],
        "ledger": [("T881", "Ledgers", "分类账", "ledger"), ("FAGL_LEDGER_INFO", "New General Ledger Configuration Information", "新总账分类账配置信息", "ledger_configuration")],
        "tax_code": [("T007A", "Tax Codes", "税码", "tax_code")],
        "payment_terms": [("T052", "Terms of Payment", "付款条件", "payment_terms")],
        "payment_method": [("T042Z", "Payment Methods", "付款方式", "payment_method")],
        "business_partner": [("BUT000", "Business Partner General Data", "业务伙伴通用数据", "business_partner"), ("KNA1", "Customer Master General Data", "客户主数据通用数据", "customer"), ("LFA1", "Vendor Master General Data", "供应商主数据通用数据", "vendor")],
        "house_bank": [("T012", "House Banks", "开户行", "house_bank"), ("BNKA", "Bank Master Record", "银行主记录", "bank")],
        "internal_order": [("AUFK", "Order Master Data", "内部订单主数据", "internal_order")],
        "wbs_element": [("PRPS", "WBS Element Master Data", "WBS 元素主数据", "wbs_element")],
        "country": [("T005", "Countries", "国家/地区", "country")],
    }
    for item in dct["dictionaryTables"]:
        code = item["dictMeta"]["dictCode"]
        name = item["dictMeta"]["dictName"]
        reason = item["dictMeta"].get("remark", "")
        for table, title, zh_title, recommended_name in mapping.get(code, []):
            specs.append(SapTableSpec(table, title, zh_title, recommended_name, "DCT", f"{code} / {name}", DCT_JSON.name, reason))
    seen = set()
    deduped = []
    for spec in specs:
        if spec.table not in seen:
            deduped.append(spec)
            seen.add(spec.table)
    return deduped


DOMAINS = [
    {
        "domain": "KOART",
        "name": "Account Type",
        "zh": "账户类型",
        "source": "DCT account_type；DOC BSEG-KOART",
        "values": "S=总账, D=客户, K=供应商, A=资产, M=物料",
        "meaning": "KOART 是 SAP 域/字段取值，不是独立透明表；BSEG-KOART 用它标识行项目对应的账户类别。",
    },
    {
        "domain": "SHKZG",
        "name": "Debit/Credit Indicator",
        "zh": "借贷标志",
        "source": "DCT debit_credit_ind；DOC BSEG-SHKZG",
        "values": "S=借方, H=贷方",
        "meaning": "SHKZG 是 SAP 域/字段取值，不是独立透明表；SAP FI 真实行项目通常使用金额字段加 SHKZG 表达借贷方向。",
    },
]


SPECIAL_ZH = {
    "MANDT": "客户端",
    "BUKRS": "公司代码",
    "BELNR": "会计凭证号",
    "GJAHR": "会计年度",
    "BUZEI": "行项目号",
    "BLART": "凭证类型",
    "BUDAT": "过账日期",
    "BLDAT": "凭证日期",
    "MONAT": "记账期间",
    "WAERS": "货币码",
    "BKTXT": "凭证抬头文本",
    "XBLNR": "参考凭证号",
    "USNAM": "用户名",
    "TCODE": "事务码",
    "AWTYP": "参考过程",
    "AWKEY": "参考键",
    "STBLG": "冲销凭证号",
    "STJAH": "冲销会计年度",
    "BSTAT": "凭证状态",
    "HKONT": "总账科目",
    "KOART": "账户类型",
    "BSCHL": "记账码",
    "SHKZG": "借贷标志",
    "DMBTR": "本位币金额",
    "WRBTR": "凭证货币金额",
    "MWSKZ": "税码",
    "KOSTL": "成本中心",
    "PRCTR": "利润中心",
    "SEGMENT": "分部",
    "GSBER": "业务范围",
    "FKBER": "功能范围",
    "VBUND": "贸易伙伴",
    "AUFNR": "内部订单",
    "PROJK": "WBS 元素",
    "KUNNR": "客户编号",
    "LIFNR": "供应商编号",
    "SGTXT": "行项目文本",
    "ZUONR": "分配号",
    "ZTERM": "付款条件",
    "ZLSCH": "付款方式",
    "AUGBL": "清账凭证号",
    "AUGDT": "清账日期",
    "LAND1": "国家/地区",
    "WAERS": "货币",
    "KTOPL": "会计科目表",
    "SAKNR": "总账科目",
    "KOKRS": "控制范围",
}


RECOMMENDED_FIELD_NAMES = {
    "MANDT": "client",
    "BUKRS": "company_code",
    "BELNR": "document_number",
    "GJAHR": "fiscal_year",
    "BUZEI": "line_item",
    "BLART": "document_type",
    "BUDAT": "posting_date",
    "BLDAT": "document_date",
    "CPUDT": "entry_date",
    "CPUTM": "entry_time",
    "MONAT": "posting_period",
    "WAERS": "currency",
    "BKTXT": "header_text",
    "XBLNR": "reference_document_number",
    "USNAM": "user_name",
    "TCODE": "transaction_code",
    "AWTYP": "reference_procedure",
    "AWKEY": "reference_key",
    "STBLG": "reversal_document_number",
    "STJAH": "reversal_fiscal_year",
    "BSTAT": "document_status",
    "HKONT": "gl_account",
    "SAKNR": "gl_account",
    "KTOPL": "chart_of_accounts",
    "KOART": "account_type",
    "BSCHL": "posting_key",
    "SHKZG": "debit_credit_indicator",
    "DMBTR": "local_currency_amount",
    "WRBTR": "document_currency_amount",
    "DMBE2": "group_currency_amount",
    "MWSKZ": "tax_code",
    "HWBAS": "tax_base_amount",
    "WMWST": "tax_amount",
    "KOSTL": "cost_center",
    "PRCTR": "profit_center",
    "SEGMENT": "segment",
    "GSBER": "business_area",
    "FKBER": "functional_area",
    "VBUND": "trading_partner",
    "AUFNR": "internal_order",
    "PROJK": "wbs_element",
    "KUNNR": "customer",
    "LIFNR": "vendor",
    "SGTXT": "line_item_text",
    "ZUONR": "assignment",
    "UMSKZ": "special_gl_indicator",
    "ZTERM": "payment_terms",
    "ZLSCH": "payment_method",
    "ZLSPR": "payment_block",
    "ZFBDT": "baseline_date",
    "AUGBL": "clearing_document_number",
    "AUGDT": "clearing_date",
    "MENGE": "quantity",
    "MEINS": "unit_of_measure",
    "LAND1": "country",
    "SPRAS": "language",
    "NAME1": "name_1",
    "NAME2": "name_2",
    "ORT01": "city",
    "PSTLZ": "postal_code",
    "STRAS": "street",
    "TELF1": "telephone",
    "STCD1": "tax_number_1",
    "STCD2": "tax_number_2",
    "KOKRS": "controlling_area",
    "KURSF": "exchange_rate",
    "KURST": "exchange_rate_type",
}


PHRASES = [
    ("Accounting Document", "会计凭证"),
    ("Document Number", "凭证编号"),
    ("Company Code", "公司代码"),
    ("Fiscal Year", "会计年度"),
    ("Line Item", "行项目"),
    ("Posting Date", "过账日期"),
    ("Document Date", "凭证日期"),
    ("Posting Period", "记账期间"),
    ("Document Type", "凭证类型"),
    ("Currency Key", "货币码"),
    ("G/L Account", "总账科目"),
    ("Account Type", "账户类型"),
    ("Posting Key", "记账码"),
    ("Debit/Credit Indicator", "借贷标志"),
    ("Tax Code", "税码"),
    ("Cost Center", "成本中心"),
    ("Profit Center", "利润中心"),
    ("Business Area", "业务范围"),
    ("Functional Area", "功能范围"),
    ("Segment", "分部"),
    ("Customer", "客户"),
    ("Vendor", "供应商"),
    ("Supplier", "供应商"),
    ("Payment Terms", "付款条件"),
    ("Payment Method", "付款方式"),
    ("Clearing Document", "清账凭证"),
    ("Clearing Date", "清账日期"),
    ("Amount", "金额"),
    ("Quantity", "数量"),
    ("Text", "文本"),
    ("Name", "名称"),
    ("Description", "描述"),
    ("Country", "国家/地区"),
    ("Chart of Accounts", "会计科目表"),
    ("Controlling Area", "控制范围"),
    ("Fiscal Year Variant", "会计年度变式"),
    ("Exchange Rate Type", "汇率类型"),
    ("Reference", "参考"),
    ("Reversal", "冲销"),
    ("Ledger", "分类账"),
    ("Client", "客户端"),
    ("Key", "键"),
    ("Type", "类型"),
    ("Date", "日期"),
    ("Indicator", "标识"),
    ("Number", "编号"),
]


def zh_name(field: Field) -> str:
    if field.name in SPECIAL_ZH:
        return SPECIAL_ZH[field.name]
    text = field.english
    for en, zh in sorted(PHRASES, key=lambda item: len(item[0]), reverse=True):
        text = re.sub(r"(?<![A-Za-z])" + re.escape(en) + r"(?![A-Za-z])", zh, text, flags=re.I)
    return text if not re.search(r"[A-Za-z]", text) else f"{text}（{field.name}）"


def recommended_field_name(field: Field) -> str:
    if field.name in RECOMMENDED_FIELD_NAMES:
        return RECOMMENDED_FIELD_NAMES[field.name]
    name = re.sub(r"[^A-Za-z0-9]+", "_", field.name).strip("_").lower()
    return name or field.name.lower()


def traits(field: Field) -> str:
    parts = []
    if field.pos <= 4 and field.name in {"MANDT", "BUKRS", "BELNR", "GJAHR", "BUZEI", "KTOPL", "SAKNR"}:
        parts.append("常见主键/键字段")
    if field.dtype in {"CURR", "DEC", "QUAN"} or re.search(r"amount|balance|price|quantity", field.english, re.I):
        parts.append("金额/数量型字段")
    if field.dtype == "CUKY" or "currency" in field.english.lower():
        parts.append("币种字段")
    if field.dtype == "DATS" or "date" in field.english.lower():
        parts.append("日期字段")
    if field.length == "1" and field.dtype == "CHAR":
        parts.append("标志/枚举型字段")
    if field.checktable:
        parts.append(f"检查表 {field.checktable}")
    if field.values:
        parts.append("有固定值/值帮助")
    parts.append(f"DDIC {field.dtype}({field.length},{field.decimals}) / 数据元素 {field.data_element or '-'}")
    return "；".join(parts)


def business_meaning(table: str, field: Field, zh: str) -> str:
    base = f"{table}-{field.name} 在 SAP 真实表中表示“{zh}”。原始 DDIC 描述：{field.english}。"
    if table == "BKPF":
        return base + "它属于会计凭证抬头层，一张 FI 凭证一行，用于确定公司代码、年度、期间、凭证控制、来源引用和冲销状态。"
    if table == "BSEG":
        return base + "它属于 FI 凭证行项目层，用于保存科目、借贷方向、金额、税、清账、往来和 CO/利润中心等分析维度。"
    if table in {"SKA1", "SKB1"}:
        return base + "它属于总账科目主数据；SKA1 是科目表层，SKB1 是公司代码层，二者共同决定科目能否记账及其控制属性。"
    if table in {"T001", "T880", "TKA01"}:
        return base + "它属于 SAP 组织结构配置，决定 FI/CO 记账、出表和组织归属边界。"
    if table in {"T003", "TBSL", "T074", "T004G"}:
        return base + "它属于凭证与字段控制配置，影响编号范围、允许账户类型、借贷方向、特别总账和字段状态。"
    if table in {"CSKS", "CEPC", "FAGL_SEGM", "TGSB", "TFKB", "AUFK", "PRPS"}:
        return base + "它提供凭证行项目的管理会计或报表维度，用于成本归集、利润责任、分部报告或项目/订单追溯。"
    if table in {"TCURC", "TCURV", "T009", "T009B", "T881", "FAGL_T_LEDGER"}:
        return base + "它属于币种、期间或分类账配置，是多币种、期间控制和并行会计的基础。"
    if table in {"BUT000", "KNA1", "LFA1", "T052", "T042Z", "T012", "BNKA"}:
        return base + "它属于业务伙伴、收付款或银行相关主数据/配置，支撑应收应付与付款流程。"
    return base + "它是该 SAP 配置表或主数据表中的标准字段，取值由 SAP 配置、主数据维护或过账程序使用。"


def render_checktable(checktable: str, known_tables: set[str]) -> str:
    if not checktable:
        return "-"
    links = []
    for part in re.split(r"[,/ ]+", checktable):
        table = part.strip()
        if not table:
            continue
        if table in known_tables:
            links.append(f"<a href='#{escape(table)}'><code>{escape(table)}</code></a>")
        else:
            links.append(f"<a href='{escape(ERP_BASE + table)}' target='_blank' rel='noopener'><code>{escape(table)}</code></a>")
    return " ".join(links) if links else escape(checktable)


def load_table_fields(table: str) -> tuple[list[Field], str, str]:
    errors = []
    try:
        html = fetch(ERP_BASE + table, CACHE / f"{table}_erpexplorer.html")
        fields = parse_erpexplorer(html)
        if fields:
            return fields, ERP_BASE + table, "ERPExplorer S/4HANA"
    except Exception as exc:  # noqa: BLE001
        errors.append(f"ERPExplorer: {exc}")
    try:
        html = fetch(PANDA_BASE + table, CACHE / f"{table}_datapanda.html")
        fields = parse_datapanda(html)
        if fields:
            return fields, PANDA_BASE + table, "Data Panda"
    except Exception as exc:  # noqa: BLE001
        errors.append(f"DataPanda: {exc}")
    return [], "", "; ".join(errors)


def render(specs: list[SapTableSpec], table_data: dict[str, tuple[list[Field], str, str]]) -> str:
    generated = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    total_fields = sum(len(v[0]) for v in table_data.values())
    known_tables = {spec.table for spec in specs}
    nav = []
    sections = []
    for spec in specs:
        fields, source_url, source_name = table_data[spec.table]
        nav.append(f"<a href='#{escape(spec.table)}'><span class='nav-name'><b>{escape(spec.table)}</b><em>{escape(spec.zh_title)}</em><code>{escape(spec.recommended_name)}</code></span><span>{len(fields)}</span></a>")
        if not fields:
            body = f"<p class='missing'>未抓取到 {escape(spec.table)} 的公开字段结构。来源尝试：{escape(source_name)}</p>"
        else:
            rows = []
            for field in fields:
                zh = zh_name(field)
                zh_with_recommended = f"{zh} ({recommended_field_name(field)})"
                rows.append(
                    f"<tr data-text='{escape((spec.table + ' ' + field.name + ' ' + zh + ' ' + field.english).lower())}'>"
                    f"<td>{field.pos}</td><td><code>{escape(field.name)}</code></td><td>{escape(zh_with_recommended)}</td>"
                    f"<td>{escape(field.english)}</td><td>{escape(traits(field))}</td><td>{render_checktable(field.checktable, known_tables)}</td>"
                    f"<td>{escape(field.data_element or '-')}</td><td>{escape(field.dtype)}</td><td>{escape(field.length)}</td>"
                    f"<td>{escape(field.decimals)}</td><td>{escape(business_meaning(spec.table, field, zh))}</td></tr>"
                )
            body = (
                "<div class='table-wrap'><table><thead><tr>"
                "<th>#</th><th>字段名</th><th>中文翻译</th><th>英文 DDIC 描述</th><th>字段特性</th>"
                "<th>检查表</th><th>数据元素</th><th>类型</th><th>长度</th><th>小数</th><th>详细业务含义</th>"
                "</tr></thead><tbody>"
                + "".join(rows)
                + "</tbody></table></div>"
            )
        sections.append(
            f"<section id='{escape(spec.table)}' class='sap-table' data-table='{escape(spec.table)}'>"
            f"<h2>{escape(spec.table)} <small>{escape(spec.zh_title)} / {escape(spec.title)}</small></h2>"
            f"<p class='reason'><b>来自：</b>{escape(spec.meta_file)} / {escape(spec.source_kind)} / {escape(spec.meta_object)}。"
            f"<b>还原依据：</b>{escape(spec.reason)}</p>"
            f"<p class='source'><b>字段来源：</b>{escape(source_name)}"
            + (f" · <a href='{escape(source_url)}'>{escape(source_url)}</a>" if source_url else "")
            + f" · 字段数 {len(fields)}</p>"
            + body
            + "</section>"
        )
    domain_rows = "".join(
        f"<tr><td><code>{escape(d['domain'])}</code></td><td>{escape(d['zh'])}</td><td>{escape(d['name'])}</td>"
        f"<td>{escape(d['source'])}</td><td>{escape(d['values'])}</td><td>{escape(d['meaning'])}</td></tr>"
        for d in DOMAINS
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SAP FI 真实表结构还原</title>
<style>
:root {{ --ink:#182235; --muted:#607089; --line:#d9e1ec; --head:#eef5fb; --band:#f8fafc; --accent:#075fb0; --warn:#fff8e8; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif; color:var(--ink); background:white; }}
header {{ padding:28px 32px 18px; border-bottom:1px solid var(--line); background:linear-gradient(180deg,#f5faff,#fff); }}
h1 {{ margin:0 0 8px; font-size:28px; letter-spacing:0; }}
h2 {{ margin:28px 0 8px; padding-top:10px; font-size:22px; }}
h2 small {{ color:var(--muted); font-size:14px; font-weight:500; }}
p {{ line-height:1.62; margin:7px 0; }}
.meta {{ display:flex; gap:10px; flex-wrap:wrap; margin-top:14px; }}
.pill {{ border:1px solid var(--line); background:#fff; border-radius:6px; padding:6px 10px; font-size:13px; }}
.toolbar {{ position:sticky; top:0; z-index:4; display:flex; gap:10px; padding:12px 32px; border-bottom:1px solid var(--line); background:rgba(255,255,255,.96); backdrop-filter:blur(8px); }}
input {{ height:36px; flex:1; min-width:300px; border:1px solid var(--line); border-radius:6px; padding:0 10px; font:inherit; }}
main {{ display:grid; grid-template-columns:250px minmax(0,1fr); gap:22px; padding:18px 32px 40px; }}
nav {{ position:sticky; top:62px; align-self:start; max-height:calc(100vh - 80px); overflow:auto; border:1px solid var(--line); border-radius:8px; padding:8px; background:#fff; }}
nav a {{ display:flex; justify-content:space-between; gap:8px; padding:7px 8px; color:var(--accent); text-decoration:none; border-radius:5px; font-size:13px; }}
nav a:hover {{ background:var(--head); }}
nav span {{ color:var(--muted); }}
.nav-name {{ display:flex; flex-direction:column; gap:2px; color:var(--accent); min-width:0; }}
.nav-name b {{ color:var(--accent); font-weight:700; }}
.nav-name em {{ color:var(--muted); font-style:normal; font-size:12px; line-height:1.2; }}
.nav-name code {{ color:#40526a; font-size:11px; font-weight:500; overflow-wrap:anywhere; }}
.note {{ background:var(--warn); border:1px solid #edd49b; border-radius:8px; padding:12px 14px; }}
.reason,.source {{ color:#39475a; font-size:13px; }}
.missing {{ color:#9b4d00; background:var(--warn); border:1px solid #edd49b; padding:10px; border-radius:6px; }}
.table-wrap {{ overflow:auto; border:1px solid var(--line); border-radius:8px; }}
table {{ border-collapse:separate; border-spacing:0; width:100%; min-width:1700px; font-size:13px; }}
th {{ background:var(--head); text-align:left; color:#26384f; }}
th,td {{ padding:8px 9px; vertical-align:top; border-right:1px solid var(--line); border-bottom:1px solid var(--line); }}
tr:nth-child(even) td {{ background:var(--band); }}
td:nth-child(1),td:nth-child(9),td:nth-child(10) {{ text-align:right; color:var(--muted); }}
td:nth-child(2) {{ white-space:nowrap; }}
td:nth-child(11) {{ min-width:420px; line-height:1.55; }}
code {{ font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; color:#084a8f; font-weight:650; }}
a code {{ text-decoration:underline; text-underline-offset:2px; }}
.domains table {{ min-width:1000px; }}
@media (max-width:900px) {{ main {{ grid-template-columns:1fr; }} nav {{ position:static; max-height:none; }} th {{ position:static; }} }}
</style>
</head>
<body>
<header>
<h1>SAP FI 真实表结构还原</h1>
<p>本页根据后端 meta 目录下 SAP FI 的 DCT/DOC 元数据文件抽取范围，但输出对象是 SAP 真实表：例如 BKPF、BSEG、T001、SKA1、SKB1、T003、TBSL 等，而不是本系统的语义表。</p>
<div class="meta">
<span class="pill">SAP 表数：{len(specs)}</span>
<span class="pill">字段行数：{total_fields}</span>
<span class="pill">域/固定值：{len(DOMAINS)}</span>
<span class="pill">生成时间：{escape(generated)}</span>
</div>
</header>
<section class="toolbar"><input id="q" type="search" placeholder="搜索表名、字段名、中文名或英文 DDIC 描述"></section>
<main>
<nav>{''.join(nav)}<a href="#domains">SAP 域/固定值 <span>{len(DOMAINS)}</span></a><a href="#acdoca">ACDOCA 参考 <span>511</span></a></nav>
<div>
<div class="note">
口径说明：DCT/DOC JSON 是本系统元模型，本文档只把其中映射/备注指向的 SAP 对象还原为真实 SAP 表结构。字段清单来源优先使用 ERPExplorer S/4HANA 表页，失败时回退 Data Panda。ACDOCA 已在独立文件中完整生成，本页只提供引用。
</div>
{''.join(sections)}
<section id="domains" class="domains">
<h2>SAP 域/固定值 <small>不是透明表</small></h2>
<div class="table-wrap"><table><thead><tr><th>域</th><th>中文</th><th>英文</th><th>来源</th><th>典型取值</th><th>说明</th></tr></thead><tbody>{domain_rows}</tbody></table></div>
</section>
<section id="acdoca">
<h2>ACDOCA <small>Universal Journal Entry Line Items</small></h2>
<p class="reason">DOC 元数据备注说明 S/4HANA 行项目对应 Universal Journal ACDOCA，但不是 BSEG 同一物理表。完整 ACDOCA 结构见 <a href="acdoca_universal_journal_structure.html">acdoca_universal_journal_structure.html</a>。</p>
</section>
</div>
</main>
<script>
const q = document.getElementById('q');
const sections = Array.from(document.querySelectorAll('.sap-table'));
const rows = Array.from(document.querySelectorAll('.sap-table tbody tr'));
q.addEventListener('input', () => {{
  const term = q.value.trim().toLowerCase();
  rows.forEach(row => row.style.display = !term || row.dataset.text.includes(term) ? '' : 'none');
  sections.forEach(section => {{
    const visible = Array.from(section.querySelectorAll('tbody tr')).some(row => row.style.display !== 'none');
    const tableHit = section.dataset.table.toLowerCase().includes(term);
    section.style.display = !term || visible || tableHit ? '' : 'none';
  }});
}});
</script>
</body>
</html>
"""


def main() -> None:
    specs = read_meta_specs()
    table_data = {spec.table: load_table_fields(spec.table) for spec in specs}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(specs, table_data), encoding="utf-8")
    missing = [table for table, (fields, _, _) in table_data.items() if not fields]
    print(f"Wrote {OUT} with {len(specs)} SAP tables and {sum(len(v[0]) for v in table_data.values())} field rows")
    if missing:
        print("Missing field structures:", ", ".join(missing))


if __name__ == "__main__":
    main()
