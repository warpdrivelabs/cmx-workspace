#!/usr/bin/env python3
"""Generate an offline Chinese reference for SAP S/4HANA ACDOCA fields."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen
import datetime as dt
import re


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "acdoca_universal_journal_structure.html"
CACHE = ROOT / "docs" / ".cache"
ERP_URL = "https://www.erpexplorer.com/sap/s4/table/ACDOCA"
PANDA_URL = "https://datapanda.eu/en/sap/table/ACDOCA"
KEY_FIELDS = {"RCLNT", "RLDNR", "RBUKRS", "GJAHR", "BELNR", "DOCLN"}


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
    if not path.exists() or path.stat().st_size < 10_000:
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


def parse_datapanda_checktables(html: str) -> dict[str, str]:
    parser = TdTableParser()
    parser.feed(html)
    out: dict[str, str] = {}
    for row in parser.rows:
        if len(row) >= 7 and re.match(r"^[A-Z0-9_./]+$", row[0]):
            if row[5]:
                out[row[0]] = row[5]
    return out


SPECIAL_ZH = {
    "RCLNT": "客户端",
    "RLDNR": "总账分类账",
    "RBUKRS": "公司代码",
    "GJAHR": "会计年度",
    "BELNR": "会计凭证号",
    "DOCLN": "分类账六位行项目号",
    "RYEAR": "总账会计年度",
    "RACCT": "总账科目",
    "KUNNR": "客户编号",
    "LIFNR": "供应商编号",
    "MATNR": "物料编号",
    "WERKS": "工厂",
    "EBELN": "采购凭证号",
    "EBELP": "采购凭证项目",
    "VBELN": "销售和分销凭证号",
    "POSNR": "销售和分销项目号",
    "ANLN1": "主资产号",
    "ANLN2": "资产子编号",
    "KOSTL": "成本中心",
    "PRCTR": "利润中心",
    "SEGMENT": "分部",
    "BUZEI": "会计凭证行项目",
    "BUDAT": "过账日期",
    "BLDAT": "凭证日期",
    "CPUDT": "录入日期",
    "USNAM": "录入用户",
    "AWTYP": "参考业务对象类型",
    "AWREF": "参考凭证号",
    "AWORG": "参考组织单元",
    "SGTXT": "行项目文本",
    "ZUONR": "分配号",
    "_DATAAGING": "数据老化过滤值",
}


PHRASES = [
    ("Ledger in General Ledger Accounting", "总账会计中的分类账"),
    ("Ledger specific Accounting Document Number", "分类账特定会计凭证编号"),
    ("Document Number of an Accounting Document", "会计凭证编号"),
    ("Six-Character Posting Item for Ledger", "分类账六位过账行项目"),
    ("Universal Journal Entry Line Item", "通用日记账分录行项目"),
    ("Business Transaction Category", "业务交易类别"),
    ("Business Transaction Type", "业务交易类型"),
    ("CO Business Transaction", "CO 业务交易"),
    ("Transaction Type for General Ledger", "总账业务交易类型"),
    ("Record Type", "记录类型"),
    ("Closing step", "关账步骤"),
    ("Reference procedure", "参考过程"),
    ("Reference Document Number", "参考凭证编号"),
    ("Reference Organizational Units", "参考组织单元"),
    ("Logical System", "逻辑系统"),
    ("Object Type", "对象类型"),
    ("Accounting Document Number", "会计凭证编号"),
    ("Net Due Date", "净到期日"),
    ("Risk Class", "风险等级"),
    ("Follow-up action", "后续处理动作"),
    ("Data Filter Value for Data Aging", "数据老化过滤值"),
    ("Source of a migrated journal entry item", "迁移日记账分录行项目来源"),
    ("Item ID of migrated G/L line item", "迁移总账行项目 ID"),
    ("Type of the Financial Valuation Object", "财务估值对象类型"),
    ("Identifier of the Financial Valuation Object", "财务估值对象标识"),
    ("Identifier of the Financial Valuation Subobject", "财务估值子对象标识"),
    ("Identifier of the Accrual Reference Object", "应计参考对象标识"),
    ("Identifier of the Accrual Subobject", "应计子对象标识"),
    ("Type of the Item of the Accrual Subobject", "应计子对象项目类型"),
    ("Accrual Value Date", "应计价值日"),
    ("Company Code", "公司代码"),
    ("Fiscal Year", "会计年度"),
    ("Client", "客户端"),
    ("Amount in", "金额"),
    ("Quantity", "数量"),
    ("Currency", "币种"),
    ("Unit of Measure", "计量单位"),
    ("Cost Center", "成本中心"),
    ("Profit Center", "利润中心"),
    ("Functional Area", "功能范围"),
    ("Business Area", "业务范围"),
    ("Segment", "分部"),
    ("Partner", "伙伴"),
    ("Customer", "客户"),
    ("Supplier", "供应商"),
    ("Vendor", "供应商"),
    ("Material", "物料"),
    ("Plant", "工厂"),
    ("Asset", "资产"),
    ("Order", "订单"),
    ("Project", "项目"),
    ("WBS Element", "WBS 元素"),
    ("Document Type", "凭证类型"),
    ("Posting Date", "过账日期"),
    ("Document Date", "凭证日期"),
    ("Clearing", "清账"),
    ("Tax", "税务"),
    ("Reference", "参考"),
    ("Account", "科目"),
    ("G/L Account", "总账科目"),
    ("Profitability Segment", "获利能力段"),
    ("Transaction", "业务交易"),
    ("Valuation", "估值"),
    ("Accounting", "会计"),
    ("Specific", "特定"),
    ("General", "总账"),
    ("Business", "业务"),
    ("Category", "类别"),
    ("Record", "记录"),
    ("Closing", "关账"),
    ("Step", "步骤"),
    ("Identifier", "标识"),
    ("Financial", "财务"),
    ("Accrual", "应计"),
    ("Subobject", "子对象"),
    ("Object", "对象"),
    ("Entry", "分录"),
    ("Item", "项目"),
    ("Journal", "日记账"),
    ("Due", "到期"),
    ("Source", "来源"),
    ("Migrated", "迁移"),
    ("Version", "版本"),
    ("Field", "字段"),
    ("Class", "等级"),
    ("Action", "动作"),
    ("Ledger", "分类账"),
    ("Line Item", "行项目"),
    ("Indicator", "标识"),
    ("Number", "编号"),
    ("Type", "类型"),
    ("Date", "日期"),
    ("Time", "时间"),
    ("Text", "文本"),
]


def zh_name(field: Field) -> str:
    if field.name in SPECIAL_ZH:
        return SPECIAL_ZH[field.name]
    text = field.english
    for en, zh in sorted(PHRASES, key=lambda item: len(item[0]), reverse=True):
        pattern = r"(?<![A-Za-z])" + re.escape(en) + r"(?![A-Za-z])"
        text = re.sub(pattern, zh, text, flags=re.I)
    if re.search(r"[A-Za-z]", text):
        return f"{text}（{field.name}）"
    return text


def source_area(field: Field) -> str:
    n = field.name
    de = field.data_element
    english = field.english.lower()
    if n in KEY_FIELDS or n.startswith("R"):
        if n in {"RACCT", "RLDNR", "RBUKRS", "RYEAR", "RRCTY", "RMVCT"}:
            return "FI-GL 总账/分类账主数据与凭证抬头"
    if any(token in n for token in ["KUNNR", "LIFNR", "KOART", "BSCHL", "AUG", "ZUONR", "SGTXT", "UMSK"]):
        return "FI-AP/AR/GL 行项目与清账信息"
    if any(token in n for token in ["KOSTL", "AUFNR", "PS_", "PROJ", "NPLNR", "VORNR", "CO_", "VRGNG"]):
        return "CO 控制对象、成本归集与业务交易"
    if n.startswith("PA") or "COPA" in de or "profitability" in english:
        return "CO-PA 获利能力分析特征"
    if any(token in n for token in ["MAT", "WERKS", "BWKEY", "BWTAR", "ML", "KALNR", "VPRSV", "LBKUM", "SALK"]):
        return "MM/物料分类账/库存估值"
    if any(token in n for token in ["VBEL", "POSNR", "KDAUF", "KDPOS", "FKART", "VTWEG", "SPART"]):
        return "SD 销售、开票与销售订单结算"
    if any(token in n for token in ["EBEL", "LIFNR", "MWSKZ", "BUSTW"]):
        return "MM 采购、发票校验与税务"
    if any(token in n for token in ["ANLN", "AFABE", "ANBWA", "DEPR", "AFASL"]):
        return "FI-AA 资产会计与折旧"
    if any(token in n for token in ["HSL", "KSL", "OSL", "VSL", "TSL", "WSL", "MSL", "CUR", "RUNIT", "QUAN"]):
        return "金额/币种/数量计量层"
    if any(token in n for token in ["AW", "SRC", "REF", "OBJ", "LOGSYS"]):
        return "源凭证引用与跨模块追溯"
    if any(token in n for token in ["CON", "FS_", "SUBIT", "INVEST"]):
        return "集团报告/合并会计扩展"
    if any(token in n for token in ["VAL", "RISK", "FUP", "NETDT"]):
        return "估值、信用风险或后续处理"
    if any(token in n for token in ["MIG", "SDM", "DATAAGING", "UPMODE"]):
        return "技术迁移、数据老化与系统管理"
    return "ACDOCA 通用日记账核心行项目"


def traits(field: Field) -> str:
    parts = []
    if field.name in KEY_FIELDS:
        parts.append("主键字段")
    if field.dtype in {"CURR", "DEC", "QUAN"} or re.search(r"amount|balance|price|cost", field.english, re.I):
        parts.append("数值/金额字段，需结合币种、计量单位或分类账视角解释")
    if field.dtype == "CUKY" or "currency" in field.english.lower():
        parts.append("币种字段")
    if field.dtype == "UNIT" or "unit" in field.english.lower():
        parts.append("计量单位字段")
    if field.dtype == "DATS" or "date" in field.english.lower():
        parts.append("日期字段")
    if field.dtype == "TIMS" or "time" in field.english.lower():
        parts.append("时间字段")
    if field.length == "1" and field.dtype == "CHAR":
        parts.append("标志/枚举型字段")
    if field.checktable:
        parts.append(f"受检查表 {field.checktable} 约束")
    if field.values:
        parts.append("存在固定值/值帮助")
    parts.append(f"DDIC: {field.dtype}({field.length},{field.decimals}) / 数据元素 {field.data_element or '-'}")
    return "；".join(parts)


def business_meaning(field: Field, zh: str, area: str) -> str:
    n = field.name
    base = f"在 {area} 中记录“{zh}”。SAP 原始描述为：{field.english}。"
    if n in KEY_FIELDS:
        return base + "它参与唯一定位 ACDOCA 的一条通用日记账行项目，是报表取数、凭证追溯和分类账并行处理的核心键值。"
    if any(token in n for token in ["HSL", "KSL", "OSL", "VSL", "TSL", "WSL", "PSL", "BSL", "CSL", "DSL", "ESL", "FSL", "GSL"]):
        return base + "该类字段保存不同币种/估值视图下的金额，常用于总账余额、管理会计分析、利润中心或集团报表。解释时必须同时查看币种字段、分类账和过账逻辑。"
    if field.dtype == "CUKY":
        return base + "它说明相关金额字段使用的币种，是多币种并行分类账、集团币种和交易币种报表的必要上下文。"
    if field.dtype == "UNIT" or "unit" in field.english.lower():
        return base + "它说明数量字段的计量单位，常与库存、生产、销售或采购数量一起使用。"
    if field.dtype == "DATS":
        return base + "它用于确定会计期间、账龄、清账、到期或业务发生时点，对期间报表和追溯分析非常关键。"
    if "clearing" in field.english.lower() or n.startswith("AUG"):
        return base + "它用于标识开放项是否已清账以及清账凭证/日期，是应收、应付和总账开放项管理的基础。"
    if any(token in n for token in ["AWTYP", "AWREF", "AWORG", "AWITEM", "SRC", "REF"]):
        return base + "它把 Universal Journal 行项目连接回原始业务凭证或逻辑系统，支持从财务分录反查采购、销售、资产、控制或迁移来源。"
    if any(token in n for token in ["KOSTL", "PRCTR", "SEGMENT", "GSBER", "FKBER", "PPRCTR"]):
        return base + "它提供组织和责任维度，用于利润中心、分部、功能范围、成本中心等多维损益和资产负债分析。"
    if any(token in n for token in ["MAT", "WERKS", "BWKEY", "BWTAR", "KALNR", "ML"]):
        return base + "它来自物料、工厂或估值对象，支撑库存价值、物料分类账、生产差异和成本组件分析。"
    if any(token in n for token in ["VBEL", "KDAUF", "KDPOS", "VTWEG", "SPART"]):
        return base + "它保留销售订单、交货、开票或销售组织维度，便于从财务收入/成本追溯到 SD 业务对象。"
    if any(token in n for token in ["EBEL", "EBELP"]):
        return base + "它连接采购订单或采购项目，常用于采购发票、GR/IR、库存入账和供应商结算追溯。"
    if any(token in n for token in ["ANLN", "AFABE", "ANBWA"]):
        return base + "它属于资产会计维度，用于资产购置、转账、折旧、报废及与总账的实时集成。"
    if n.startswith("PA") or "profitability" in field.english.lower():
        return base + "它是 CO-PA 特征或获利能力段相关信息，用于按客户、产品、市场和组织维度分析收入与边际贡献。"
    if n.startswith("X") or "indicator" in field.english.lower():
        return base + "它通常以单字符标志表达业务状态或处理方式，取值需要结合 SAP 固定值、值帮助或具体凭证流程判断。"
    return base + "它为通用日记账提供一个可筛选、可汇总或可追溯的业务维度，具体取值通常由源业务凭证、主数据、派生规则或过账程序写入。"


def render(fields: list[Field]) -> str:
    generated = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    rows = []
    areas = sorted({source_area(f) for f in fields})
    for f in fields:
        zh = zh_name(f)
        area = source_area(f)
        rows.append(
            "<tr "
            f"data-field='{escape(f.name)}' data-area='{escape(area)}' data-text='{escape((f.name + ' ' + zh + ' ' + f.english + ' ' + area).lower())}'>"
            f"<td>{f.pos}</td><td><code>{escape(f.name)}</code></td><td>{escape(zh)}</td>"
            f"<td>{escape(f.english)}</td><td>{escape(area)}</td><td>{escape(traits(f))}</td>"
            f"<td>{escape(f.checktable or '-')}</td><td>{escape(f.data_element or '-')}</td>"
            f"<td>{escape(f.dtype)}</td><td>{escape(f.length)}</td><td>{escape(f.decimals)}</td>"
            f"<td>{escape(business_meaning(f, zh, area))}</td></tr>"
        )
    options = "\n".join(f"<option value='{escape(a)}'>{escape(a)}</option>" for a in areas)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SAP S/4HANA ACDOCA Universal Journal 表结构中文说明</title>
<style>
:root {{ color-scheme: light; --ink:#1d2433; --muted:#617084; --line:#d8dee8; --head:#eef4fb; --accent:#0b65c2; --band:#f7f9fc; --warn:#fff7e6; }}
* {{ box-sizing: border-box; }}
body {{ margin:0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif; color:var(--ink); background:white; }}
header {{ padding:28px 32px 18px; border-bottom:1px solid var(--line); background:linear-gradient(180deg,#f7fbff,#fff); }}
h1 {{ margin:0 0 8px; font-size:28px; letter-spacing:0; }}
p {{ margin:8px 0; line-height:1.65; }}
.meta {{ display:flex; gap:12px; flex-wrap:wrap; margin-top:14px; }}
.pill {{ border:1px solid var(--line); background:white; padding:6px 10px; border-radius:6px; color:#304158; font-size:13px; }}
.toolbar {{ position:sticky; top:0; z-index:3; display:flex; gap:10px; flex-wrap:wrap; padding:12px 32px; border-bottom:1px solid var(--line); background:rgba(255,255,255,.96); backdrop-filter:saturate(1.2) blur(8px); }}
input, select {{ height:36px; border:1px solid var(--line); border-radius:6px; padding:0 10px; font:inherit; }}
input {{ min-width:300px; flex:1; }}
main {{ padding:18px 32px 36px; }}
.note {{ background:var(--warn); border:1px solid #f1d49a; padding:12px 14px; border-radius:8px; margin-bottom:16px; }}
.table-wrap {{ overflow:auto; border:1px solid var(--line); border-radius:8px; }}
table {{ border-collapse:separate; border-spacing:0; min-width:2100px; width:100%; font-size:13px; }}
th {{ position:sticky; top:61px; z-index:2; text-align:left; background:var(--head); border-bottom:1px solid var(--line); color:#26384f; }}
th, td {{ padding:9px 10px; vertical-align:top; border-right:1px solid var(--line); border-bottom:1px solid var(--line); }}
tr:nth-child(even) td {{ background:var(--band); }}
td:nth-child(1), td:nth-child(10), td:nth-child(11) {{ text-align:right; color:var(--muted); }}
td:nth-child(2) {{ white-space:nowrap; }}
td:nth-child(12) {{ min-width:430px; line-height:1.55; }}
code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; color:#084a8f; font-weight:650; }}
a {{ color:var(--accent); }}
.count {{ align-self:center; color:var(--muted); font-size:13px; }}
@media print {{ .toolbar {{ position:static; }} th {{ position:static; }} body {{ font-size:11px; }} }}
</style>
</head>
<body>
<header>
<h1>SAP S/4HANA ACDOCA Universal Journal 表结构中文说明</h1>
<p>ACDOCA 是 Universal Journal Entry Line Items，即通用日记账行项目表。本文档按公开 S/4HANA 字段快照整理完整字段清单，并为每个字段补充中文翻译、数据来源/业务域、字段特性和业务含义。</p>
<div class="meta">
<span class="pill">字段数：{len(fields)}</span>
<span class="pill">主键：RCLNT, RLDNR, RBUKRS, GJAHR, BELNR, DOCLN</span>
<span class="pill">生成时间：{escape(generated)}</span>
<span class="pill">来源：ERPExplorer + Data Panda</span>
</div>
</header>
<section class="toolbar">
<input id="q" type="search" placeholder="搜索字段名、中文名、英文描述或业务域">
<select id="area"><option value="">全部业务域</option>{options}</select>
<span class="count" id="visibleCount"></span>
</section>
<main>
<div class="note">
说明：SAP ACDOCA 会随 S/4HANA 版本、行业组件、激活业务功能和客户扩展而变化。本 HTML 以 ERPExplorer 标注的 S/4HANA ACDOCA 511 个标准字段为完整顺序基准，并用 Data Panda 字段页补充检查表信息；中文说明中“数据来源/业务域”为依据字段名、数据元素和通用日记账业务规则作出的归类。
来源链接：<a href="{ERP_URL}">{ERP_URL}</a>；<a href="{PANDA_URL}">{PANDA_URL}</a>。
</div>
<div class="table-wrap">
<table id="fields">
<thead><tr>
<th>#</th><th>列名</th><th>中文翻译</th><th>英文 DDIC 描述</th><th>数据来源/业务域</th><th>特性</th><th>检查表</th><th>数据元素</th><th>类型</th><th>长度</th><th>小数</th><th>详细业务含义</th>
</tr></thead>
<tbody>
{''.join(rows)}
</tbody>
</table>
</div>
</main>
<script>
const q = document.getElementById('q');
const area = document.getElementById('area');
const rows = Array.from(document.querySelectorAll('#fields tbody tr'));
const count = document.getElementById('visibleCount');
function applyFilter() {{
  const term = q.value.trim().toLowerCase();
  const selected = area.value;
  let shown = 0;
  rows.forEach(row => {{
    const okText = !term || row.dataset.text.includes(term);
    const okArea = !selected || row.dataset.area === selected;
    const show = okText && okArea;
    row.style.display = show ? '' : 'none';
    if (show) shown++;
  }});
  count.textContent = `显示 ${{shown}} / ${{rows.length}} 个字段`;
}}
q.addEventListener('input', applyFilter);
area.addEventListener('change', applyFilter);
applyFilter();
</script>
</body>
</html>
"""


def main() -> None:
    erp_html = fetch(ERP_URL, CACHE / "acdoca_erpexplorer.html")
    panda_html = fetch(PANDA_URL, CACHE / "acdoca_datapanda.html")
    fields = parse_erpexplorer(erp_html)
    checktables = parse_datapanda_checktables(panda_html)
    for field in fields:
        if not field.checktable and field.name in checktables:
            field.checktable = checktables[field.name]
    if len(fields) != 511:
        raise SystemExit(f"Expected 511 fields from ERPExplorer, got {len(fields)}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(fields), encoding="utf-8")
    print(f"Wrote {OUT} with {len(fields)} fields")


if __name__ == "__main__":
    main()
