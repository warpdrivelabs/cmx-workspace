#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Assemble the test report: embed {{FIG:name}} (SVG) + {{PNG:name}} (screenshot) as base64 <img>."""
import base64, pathlib, re

HERE = pathlib.Path(__file__).resolve().parent          # docs/assets/data-auth/tests
REPO = HERE.parents[3]
TEMPLATE = HERE / "report.template.md"
RENDER = HERE.parent / "_render"                         # screenshots live here
OUT = REPO / "docs" / "20260901_数据权限全面测试报告.md"
MAXW = 900

FIG = re.compile(r"\{\{FIG:([a-z0-9\-]+)\}\}")
PNG = re.compile(r"\{\{PNG:([a-z0-9\-]+)\}\}")


def img(b64: str, mime: str, name: str) -> str:
    return (f'<p align="center"><img alt="{name}" style="width:100%;max-width:{MAXW}px" '
            f'src="data:{mime};base64,{b64}"/></p>')


def main():
    t = TEMPLATE.read_text(encoding="utf-8")
    used = []

    def fig(m):
        name = m.group(1); used.append("svg:" + name)
        svg = HERE / f"{name}.svg"
        return img(base64.b64encode(svg.read_bytes()).decode(), "image/svg+xml", name)

    def png(m):
        name = m.group(1); used.append("png:" + name)
        p = RENDER / f"{name}.png"
        return img(base64.b64encode(p.read_bytes()).decode(), "image/png", name)

    t = FIG.sub(fig, t)
    t = PNG.sub(png, t)
    left = FIG.findall(t) + PNG.findall(t)
    if left:
        raise SystemExit(f"unresolved: {left}")
    OUT.write_text(t, encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO)} ({len(t.encode())/1024:.0f} KiB); embedded {used}")


if __name__ == "__main__":
    main()
