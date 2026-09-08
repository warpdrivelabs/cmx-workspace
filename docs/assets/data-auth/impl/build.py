#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Assemble the data-auth implementation doc: replace {{FIG:name}} placeholders in the
template with <img> tags carrying base64-embedded SVGs (self-contained markdown)."""
import base64
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent          # docs/assets/data-auth/impl
REPO = HERE.parents[3]                                    # presentation/
TEMPLATE = HERE / "impl-doc.template.md"
OUT = REPO / "docs" / "20260831_数据权限完整实现方案.md"
MAXW = 900  # px

FIG_RE = re.compile(r"\{\{FIG:([a-z0-9\-]+)\}\}")


def img_tag(name: str) -> str:
    svg = HERE / f"{name}.svg"
    if not svg.exists():
        raise SystemExit(f"missing SVG: {svg}")
    b64 = base64.b64encode(svg.read_bytes()).decode("ascii")
    return (
        f'<p align="center"><img alt="{name}" '
        f'style="width:100%;max-width:{MAXW}px" '
        f'src="data:image/svg+xml;base64,{b64}"/></p>'
    )


def main() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")
    used = []

    def repl(m):
        name = m.group(1)
        used.append(name)
        return img_tag(name)

    out = FIG_RE.sub(repl, text)
    leftover = FIG_RE.findall(out)
    if leftover:
        raise SystemExit(f"unresolved placeholders: {leftover}")
    OUT.write_text(out, encoding="utf-8")
    kb = len(out.encode("utf-8")) / 1024
    print(f"wrote {OUT.relative_to(REPO)}  ({kb:.0f} KiB)")
    print(f"embedded {len(used)} figures: {', '.join(used)}")


if __name__ == "__main__":
    main()
