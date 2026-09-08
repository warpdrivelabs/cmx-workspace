#!/usr/bin/env python3
"""Build a broad SAP S/4 FICO table catalog from ERPExplorer sitemap.

The sitemap contains far more tables than a browser-friendly document can render with
full fields. This generator outputs every FICO candidate table it can discover and
renders full field structures for the highest-confidence core tables.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen
import datetime as dt
import re
import time


ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "docs" / ".cache" / "erpexplorer_fico"
SITEMAP_CACHE = ROOT / "docs" / ".cache" / "erpexplorer_sitemaps"
OUT = ROOT / "docs" / "erpexplorer_s4_fico_tables.html"
ERP_BASE = "https://www.erpexplorer.com/sap/s4/table/"
PANDA_BASE = "https://datapanda.eu/en/sap/table/"
UA = {"User-Agent": "Mozilla/5.0"}


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


def fetch(url: str, path: Path, timeout: int = 60) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.stat().st_size < 1000:
        with urlopen(Request(url, headers=UA), timeout=timeout) as response:
            path.write_bytes(response.read())
        time.sleep(0.05)
    return path.read_text(errors="ignore")


def sitemap_tables() -> list[str]:
    SITEMAP_CACHE.mkdir(parents=True, exist_ok=True)
    index = SITEMAP_CACHE / "sitemap.xml"
    fetch("https://www.erpexplorer.com/sitemap.xml", index)
    sitemap_urls = re.findall(
        r"<loc>(https://www\.erpexplorer\.com/sitemap-\d+\.xml)</loc>",
        index.read_text(errors="ignore"),
    )
    tables: list[str] = []
    for sitemap_url in sitemap_urls:
        path = SITEMAP_CACHE / sitemap_url.rsplit("/", 1)[1]
        text = fetch(sitemap_url, path)
        tables.extend(re.findall(r"<loc>https://www\.erpexplorer\.com/sap/s4/table/([^<]+)</loc>", text))
    return sorted(set(tables))


CORE_TABLES = {
    "ACDOCA", "BKPF", "BSEG", "BSET", "BSEC", "BSED", "BSAD", "BSAK", "BSAS", "BSID", "BSIK", "BSIS", "BSIP",
    "WITH_ITEM", "PAYR", "REGUH", "REGUP",
    "SKA1", "SKAT", "SKB1", "SKC1", "SKC3", "T001", "T003", "T004", "T004T", "TBSL", "T007A", "T007S", "T074",
    "T880", "T881", "T009", "T009B", "T011", "T012", "T042Z", "T052", "TCURC", "TCURR", "TCURV", "TCURX",
    "COBK", "COEP", "COEJ", "COSP", "COSS", "AUFK", "CSKS", "CSKT", "CEPC", "CEPCT", "TKA01", "TKA02",
    "ANLA", "ANLB", "ANLC", "ANLH", "ANLP", "ANLZ", "ANEK", "ANEP", "ANEA",
    "FAGLFLEXA", "FAGLFLEXT", "FAGL_LEDGER_INFO", "FAGL_DOCNR_LD", "FAGL_SPLINFO", "FAGL_SPLINFO_VAL",
    "FINSC_LEDGER", "FINSC_LD_CMP", "FINSC_CMP_VERSND", "FINSV_MIG_STATUS",
}

FICO_PREFIXES = (
    "FAGL", "FINSC", "FINS", "FI", "GL", "SKA", "SKB", "SKC", "BS", "BSE", "BSA", "BSI", "WITH_", "REGU",
    "CO", "COSP", "COSS", "CSKS", "CSKT", "CEPC", "CEPCT", "TKA", "TKE", "ANL", "ANE", "T093", "T095", "TCUR",
)

CONFIG_PATTERNS = (
    r"^T00", r"^T01", r"^T03", r"^T04", r"^T05", r"^T07", r"^T08", r"^T09", r"^TBSL$", r"^T880$", r"^T881$",
)


def fico_score(table: str) -> tuple[int, str]:
    reasons = []
    score = 0
    if table in CORE_TABLES:
        score += 100
        reasons.append("core")
    if any(table.startswith(prefix) for prefix in FICO_PREFIXES):
        score += 30
        reasons.append("prefix")
    if any(re.search(pattern, table) for pattern in CONFIG_PATTERNS):
        score += 20
        reasons.append("config")
    if "/" in table:
        score -= 40
        reasons.append("namespace")
    if table.endswith(("_DRAFT", "_BAK", "_BCK", "_TMP", "_OLD")):
        score -= 20
        reasons.append("technical")
    return score, ", ".join(reasons)


def parse_fields(html: str) -> list[Field]:
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


def parse_datapanda_fields(html: str) -> list[Field]:
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


def page_title(html: str, table: str) -> str:
    match = re.search(rf"SAP S/4HANA - {re.escape(table)} - ([^|<]+)", html)
    if match:
        return match.group(1).strip()
    match = re.search(r"<title>([^<]+)</title>", html)
    return match.group(1).strip() if match else ""


def load_table(table: str) -> tuple[str, list[Field]]:
    path = CACHE / f"{table.replace('/', '_')}.html"
    html = fetch(ERP_BASE + table, path)
    title = page_title(html, table)
    fields = parse_fields(html)
    if fields:
        return title, fields
    panda_path = CACHE / f"{table.replace('/', '_')}_datapanda.html"
    try:
        panda_html = fetch(PANDA_BASE + table, panda_path)
        panda_fields = parse_datapanda_fields(panda_html)
        if panda_fields:
            return title, panda_fields
    except Exception:
        pass
    return title, fields


def render_checktable(checktable: str, known: set[str]) -> str:
    if not checktable:
        return "-"
    out = []
    for part in re.split(r"[,/ ]+", checktable):
        if not part:
            continue
        if part in known:
            out.append(f"<a href='#{escape(part)}'><code>{escape(part)}</code></a>")
        else:
            out.append(f"<a href='{escape(ERP_BASE + part)}' target='_blank' rel='noopener'><code>{escape(part)}</code></a>")
    return " ".join(out)


def render(candidates: list[tuple[str, int, str]], full: dict[str, tuple[str, list[Field]]]) -> str:
    generated = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    known_full = set(full)
    catalog_rows = []
    for table, score, reason in candidates:
        title = full.get(table, ("", []))[0]
        catalog_rows.append(
            f"<tr data-text='{escape((table + ' ' + title + ' ' + reason).lower())}'>"
            f"<td><a href='#{escape(table)}'><code>{escape(table)}</code></a></td>"
            f"<td>{escape(title)}</td><td>{score}</td><td>{escape(reason)}</td>"
            f"<td><a href='{escape(ERP_BASE + table)}' target='_blank' rel='noopener'>ERPExplorer</a></td></tr>"
        )
    sections = []
    for table, (title, fields) in full.items():
        rows = []
        for field in fields:
            rows.append(
                f"<tr><td>{field.pos}</td><td><code>{escape(field.name)}</code></td><td>{escape(field.english)}</td>"
                f"<td>{escape(field.dtype)}</td><td>{escape(field.length)}</td><td>{escape(field.decimals)}</td>"
                f"<td>{escape(field.data_element)}</td><td>{render_checktable(field.checktable, known_full)}</td></tr>"
            )
        sections.append(
            f"<section id='{escape(table)}'><h2>{escape(table)} <small>{escape(title)}</small></h2>"
            f"<p><a href='{escape(ERP_BASE + table)}' target='_blank' rel='noopener'>{escape(ERP_BASE + table)}</a> · 字段数 {len(fields)}</p>"
            "<div class='table-wrap'><table><thead><tr><th>#</th><th>字段名</th><th>英文 DDIC 描述</th><th>类型</th><th>长度</th><th>小数</th><th>数据元素</th><th>检查表</th></tr></thead><tbody>"
            + "".join(rows)
            + "</tbody></table></div></section>"
        )
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>ERPExplorer SAP S/4 FICO 表清单与核心表结构</title>
<style>
body{{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;color:#182235}}
header{{padding:28px 32px 18px;border-bottom:1px solid #d9e1ec;background:#f7fbff}}
h1{{margin:0 0 8px;font-size:28px}} p{{line-height:1.6}} code{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;color:#084a8f;font-weight:650}}
.meta{{display:flex;gap:10px;flex-wrap:wrap}}.pill{{border:1px solid #d9e1ec;border-radius:6px;padding:6px 10px;background:white;font-size:13px}}
.toolbar{{position:sticky;top:0;z-index:3;padding:12px 32px;border-bottom:1px solid #d9e1ec;background:rgba(255,255,255,.96)}}input{{height:36px;width:100%;border:1px solid #d9e1ec;border-radius:6px;padding:0 10px;font:inherit}}
main{{padding:18px 32px 40px}}.note{{background:#fff8e8;border:1px solid #edd49b;border-radius:8px;padding:12px 14px;margin-bottom:16px}}
.table-wrap{{overflow:auto;border:1px solid #d9e1ec;border-radius:8px;margin-bottom:22px}}table{{border-collapse:separate;border-spacing:0;width:100%;min-width:1100px;font-size:13px}}
th{{background:#eef5fb;text-align:left;color:#26384f}}th,td{{padding:8px 9px;vertical-align:top;border-right:1px solid #d9e1ec;border-bottom:1px solid #d9e1ec}}tr:nth-child(even) td{{background:#f8fafc}}
a{{color:#075fb0}}a code{{text-decoration:underline;text-underline-offset:2px}}h2{{margin-top:28px}}h2 small{{font-size:14px;color:#607089;font-weight:500}}
</style></head><body>
<header><h1>ERPExplorer SAP S/4 FICO 表清单与核心表结构</h1>
<p>来源为 ERPExplorer S/4 sitemap 与表详情页。本文档先列出全部 FICO 候选表，再对高相关核心表渲染完整字段结构；候选规则基于 FI/CO/AA/GL/FAGL/FINS/TCUR/TKA/TKE 等前缀、经典表名和配置表模式。</p>
<div class="meta"><span class="pill">候选表：{len(candidates)}</span><span class="pill">完整结构表：{len(full)}</span><span class="pill">字段行：{sum(len(v[1]) for v in full.values())}</span><span class="pill">生成时间：{escape(generated)}</span></div></header>
<section class="toolbar"><input id="q" type="search" placeholder="搜索候选表名、描述或筛选原因"></section>
<main><div class="note">说明：ERPExplorer 没有公开 FI/CO 模块全量分类接口；本页的“全量”指从 ERPExplorer sitemap 中按 FICO 相关规则筛出的候选全集。字段结构默认只抓核心表，避免生成数百 MB 的不可用 HTML；脚本中可调整 <code>CORE_TABLES</code> 扩展完整字段表。</div>
<h2>FICO 候选表清单</h2><div class="table-wrap"><table id="catalog"><thead><tr><th>SAP 表</th><th>英文表说明</th><th>相关度</th><th>筛选依据</th><th>来源</th></tr></thead><tbody>{''.join(catalog_rows)}</tbody></table></div>
<h2>核心表完整字段结构</h2>{''.join(sections)}</main>
<script>
const q=document.getElementById('q');const rows=Array.from(document.querySelectorAll('#catalog tbody tr'));
q.addEventListener('input',()=>{{const term=q.value.trim().toLowerCase();rows.forEach(r=>r.style.display=!term||r.dataset.text.includes(term)?'':'none')}})
</script></body></html>"""


def main() -> None:
    tables = sitemap_tables()
    candidates = []
    for table in tables:
        score, reason = fico_score(table)
        if score >= 30:
            candidates.append((table, score, reason))
    candidates.sort(key=lambda row: (-row[1], row[0]))
    full_tables = [table for table, _, _ in candidates if table in CORE_TABLES]
    full: dict[str, tuple[str, list[Field]]] = {}
    for idx, table in enumerate(full_tables, 1):
        try:
            title, fields = load_table(table)
            if fields:
                full[table] = (title, fields)
            print(f"[{idx}/{len(full_tables)}] {table} fields={len(fields)}", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"[{idx}/{len(full_tables)}] {table} failed: {exc}", flush=True)
    OUT.write_text(render(candidates, full), encoding="utf-8")
    print(f"Wrote {OUT} candidates={len(candidates)} full={len(full)} fields={sum(len(v[1]) for v in full.values())}")


if __name__ == "__main__":
    main()
