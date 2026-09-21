#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成《Pingora 技术方案》—— 内嵌 base64 SVG。
Run: python3 gen_pingora.py   (pingora 0.9 / MSRV 1.84 / Cloudflare)
"""
import base64
import html
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "20260919_Pingora-技术方案.md")

SANS = "-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif"
MONO = "ui-monospace,SFMono-Regular,Menlo,monospace"
BG = "#fbfdff"
SRV = ("#4338ca", "#eef2ff")   # server indigo
PXY = ("#0d9488", "#f0fdfa")   # proxy teal
UP = ("#7c3aed", "#f5f3ff")    # upstream violet
LBc = ("#b45309", "#fffbeb")   # lb amber
DAN = ("#dc2626", "#fef2f2")   # danger red
GRY = ("#475569", "#f1f5f9")   # slate


def esc(s):
    return html.escape(str(s), quote=True)


def b64img(svg_str, alt):
    b = base64.b64encode(svg_str.encode("utf-8")).decode("ascii")
    return ('<p align="center"><img alt="' + esc(alt) + '" '
            'style="max-width:100%;height:auto;border:1px solid #e8eef5;border-radius:10px" '
            'src="data:image/svg+xml;base64,' + b + '"></p>')


MARK = ('<marker id="a" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7" markerHeight="7" '
        'orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#64748b"/></marker>')


def svg(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img">'
            f'<defs>{MARK}</defs><rect width="{w}" height="{h}" fill="{BG}"/>' + body + '</svg>')


def box(x, y, w, h, title, lines, col, tcol="#fff"):
    st, fl = col
    out = ['<g>',
           f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fl}" stroke="{st}" stroke-width="1.7"/>',
           f'<rect x="{x}" y="{y}" width="{w}" height="22" rx="8" fill="{st}"/>',
           f'<rect x="{x}" y="{y+14}" width="{w}" height="8" fill="{st}"/>',
           f'<text x="{x+10}" y="{y+16}" font-family="{MONO}" font-size="11.5" font-weight="700" fill="{tcol}">{esc(title)}</text>']
    yy = y + 22 + 14
    for ln in lines:
        out.append(f'<text x="{x+10}" y="{yy}" font-family="{SANS}" font-size="10" fill="#1e293b">{esc(ln)}</text>')
        yy += 14
    out.append('</g>')
    return "".join(out)


def chip(x, y, w, text, col, tcol="#fff"):
    st, _ = col
    return (f'<g><rect x="{x}" y="{y}" width="{w}" height="30" rx="6" fill="{st}"/>'
            f'<text x="{x+w/2:.0f}" y="{y+19}" text-anchor="middle" font-family="{MONO}" font-size="10.5" '
            f'font-weight="700" fill="{tcol}">{esc(text)}</text></g>')


def arrow(x1, y1, x2, y2, label="", col="#64748b", dash="5 3", curve=False):
    if curve:
        d = f"M {x1} {y1} C {x1} {(y1+y2)/2} {x2} {(y1+y2)/2} {x2} {y2}"
    else:
        d = f"M {x1} {y1} L {x2} {y2}"
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    out = ['<g>', f'<path d="{d}" fill="none" stroke="{col}" stroke-width="1.6" '
           f'stroke-dasharray="{dash}" marker-end="url(#a)"/>']
    if label:
        lw = 6.6 * len(label) + 12
        out.append(f'<rect x="{mx-lw/2:.0f}" y="{my-9:.0f}" width="{lw}" height="16" rx="4" fill="#fff" '
                   f'fill-opacity="0.95" stroke="#cbd5e1" stroke-width="0.7"/>')
        out.append(f'<text x="{mx:.0f}" y="{my+3:.0f}" text-anchor="middle" font-family="{MONO}" '
                   f'font-size="9" fill="#334155">{esc(label)}</text>')
    out.append('</g>')
    return "".join(out)


def caption(w, y, text):
    return (f'<text x="{w/2:.0f}" y="{y}" text-anchor="middle" font-family="{SANS}" font-size="12.5" '
            f'fill="#334155">{esc(text)}</text>')


# ---------------------------------------------------------------- FIG 1 架构
def fig_arch():
    W, H = 940, 400
    b = []
    b.append(box(300, 34, 340, 60, "Server（进程）", ["信号处理 · 配置 · 线程编排 · 零停机热升级"], SRV))
    b.append(box(40, 140, 260, 92, "HttpProxy Service", ["你的 impl ProxyHttp", "http_proxy_service(conf, MyProxy)", "add_tcp / add_tls 监听"], PXY))
    b.append(box(340, 140, 260, 92, "Background Service", ["LoadBalancer 健康检查", "服务发现 · 定期刷新", "background_service(name, lb)"], LBc))
    b.append(box(640, 140, 260, 92, "监听器 Listeners", ["TCP / Unix socket", "TLS: OpenSSL 或 BoringSSL", "HTTP/1.x · HTTP/2"], UP))
    b.append(box(120, 286, 700, 66, "多线程 work-stealing 运行时（tokio）", [
        "单地址空间、多线程（非 nginx 的多进程 worker）→ 负载在核间自动均衡",
        "全局共享连接池：任意线程可复用彼此的上游空闲连接"], GRY))
    b.append(arrow(400, 94, 170, 140))
    b.append(arrow(470, 94, 470, 140))
    b.append(arrow(540, 94, 770, 140))
    b.append(arrow(170, 232, 300, 286))
    b.append(arrow(470, 232, 470, 286))
    b.append(arrow(770, 232, 640, 286))
    b.append(caption(W, 384, "Server 托管多个 Service，跑在一个多线程运行时上；这套「多线程 + 全局连接池」是相对 nginx 的根本差异"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 2 生命周期
def fig_life():
    W, H = 940, 430
    b = []
    r1 = [("下游读请求", GRY), ("early_request_filter", PXY), ("request_filter", PXY),
          ("upstream_peer ★", LBc), ("连接 / 复用池", UP), ("upstream_request_filter", PXY)]
    r2 = [("双工转发", UP), ("response_filter", PXY), ("response_body_filter", PXY),
          ("写回下游", GRY), ("logging", SRV)]
    x0, step, w = 20, 152, 140
    for i, (t, c) in enumerate(r1):
        b.append(box(x0 + i * step, 60, w, 46, t, [], c))
    for i in range(len(r1) - 1):
        xx = x0 + i * step + w
        b.append(arrow(xx, 83, xx + (step - w), 83))
    # wrap from row1 end down to row2 start
    b.append(arrow(x0 + 5 * step + w / 2, 106, x0 + w / 2, 200, "上游响应到达", UP[0], curve=True))
    for i, (t, c) in enumerate(r2):
        b.append(box(x0 + i * step, 210, w, 46, t, [], c))
    for i in range(len(r2) - 1):
        xx = x0 + i * step + w
        b.append(arrow(xx, 233, xx + (step - w), 233))
    # error hooks
    b.append(box(120, 320, 320, 66, "错误钩子", [
        "fail_to_connect：可判定是否可重试 → 重回 upstream_peer",
        "fail_to_proxy：全局兜底，生成自定义错误响应"], DAN))
    b.append(box(500, 320, 320, 66, "贯穿全程", [
        "CTX：new_ctx() 建每请求上下文，串起所有阶段",
        "connected_to_upstream：记录 RTT / TLS 信息"], GRY))
    b.append(caption(W, 414, "★ upstream_peer 是唯一必须实现的阶段；其余 30+ 钩子都有默认实现，按需覆盖即可注入逻辑"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 3 连接池对比
def fig_pool():
    W, H = 940, 380
    b = []
    # nginx side
    b.append(f'<rect x="30" y="50" width="410" height="290" rx="12" fill="{DAN[1]}" stroke="{DAN[0]}" stroke-width="1.8"/>')
    b.append(f'<text x="235" y="76" text-anchor="middle" font-family="{MONO}" font-size="13" font-weight="700" fill="{DAN[0]}">nginx：多进程 worker</text>')
    for i in range(3):
        x = 55 + i * 128
        b.append(box(x, 96, 108, 96, f"worker {i+1}", ["独立进程", "自带连接池", "互不可见"], GRY))
        b.append(f'<rect x="{x+14}" y="205" width="80" height="30" rx="6" fill="#fff" stroke="{DAN[0]}" stroke-width="1.3"/>')
        b.append(f'<text x="{x+54}" y="224" text-anchor="middle" font-family="{MONO}" font-size="9" fill="{DAN[0]}">pool {i+1}</text>')
    b.append(f'<text x="235" y="270" text-anchor="middle" font-family="{SANS}" font-size="11" fill="{DAN[0]}">请求钉在单 worker：跨 worker 不能复用连接</text>')
    b.append(f'<text x="235" y="292" text-anchor="middle" font-family="{SANS}" font-size="11" fill="{DAN[0]}">→ 更多上游 TCP/TLS 握手，负载在核间不均</text>')
    # pingora side
    b.append(f'<rect x="500" y="50" width="410" height="290" rx="12" fill="{PXY[1]}" stroke="{PXY[0]}" stroke-width="1.8"/>')
    b.append(f'<text x="705" y="76" text-anchor="middle" font-family="{MONO}" font-size="13" font-weight="700" fill="{PXY[0]}">Pingora：多线程单进程</text>')
    for i in range(3):
        x = 525 + i * 128
        b.append(box(x, 96, 108, 70, f"thread {i+1}", ["无锁热池", "(thread-local)"], PXY))
    b.append(f'<rect x="540" y="205" width="330" height="46" rx="8" fill="#fff" stroke="{PXY[0]}" stroke-width="1.6"/>')
    b.append(f'<text x="705" y="233" text-anchor="middle" font-family="{MONO}" font-size="11" font-weight="700" fill="{PXY[0]}">全局共享连接池（Mutex）</text>')
    for i in range(3):
        x = 525 + i * 128 + 54
        b.append(arrow(x, 166, 705, 205))
    b.append(f'<text x="705" y="278" text-anchor="middle" font-family="{SANS}" font-size="11" fill="{PXY[0]}">任意线程复用彼此空闲连接（per-peer 匹配）</text>')
    b.append(f'<text x="705" y="300" text-anchor="middle" font-family="{SANS}" font-size="11" fill="{PXY[0]}">→ 握手锐减；负载 work-stealing 自动均衡</text>')
    b.append(caption(W, 364, "「全局连接池」是 Cloudflare 替换 nginx 时最看重的一点——连接复用率的提升直接省下大量上游握手"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 4 负载均衡
def fig_lb():
    W, H = 940, 340
    b = []
    b.append(box(40, 120, 220, 80, "ProxyHttp", ["upstream_peer()", "→ lb.select(key, n)"], PXY))
    b.append(box(320, 110, 240, 100, "LoadBalancer<Selection>", [
        "RoundRobin / Random", "Weighted / KetamaHashing", "select / select_with"], LBc))
    for i, name in enumerate(["backend A", "backend B", "backend C"]):
        b.append(box(650, 40 + i * 92, 240, 66, name, ["健康: ✔", "地址 · 权重"], UP))
        b.append(arrow(560, 150, 650, 73 + i * 92))
    b.append(arrow(260, 160, 320, 160, "选后端", PXY[0]))
    b.append(box(320, 250, 240, 66, "Background Service", ["Tcp/HttpHealthCheck", "health_check_frequency"], SRV))
    b.append(arrow(440, 250, 440, 210, "更新健康", SRV[0]))
    b.append(caption(W, 330, "upstream_peer 里调 LoadBalancer.select 选后端；后台服务按频率健康检查，秒级摘除/恢复节点"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 5 热升级
def fig_upgrade():
    W, H = 940, 320
    b = []
    b.append(box(40, 70, 250, 120, "旧进程（运行中）", [
        "① 正在处理连接", "③ 交出监听 socket FD", "⑤ 排空在途请求后退出"], SRV))
    b.append(box(650, 70, 250, 120, "新进程（--upgrade）", [
        "② 启动，不立刻绑定端口", "④ 接管监听，处理新连接"], PXY))
    b.append(f'<rect x="360" y="95" width="220" height="70" rx="10" fill="{LBc[1]}" stroke="{LBc[0]}" stroke-width="1.8"/>')
    b.append(f'<text x="470" y="120" text-anchor="middle" font-family="{MONO}" font-size="11" font-weight="700" fill="{LBc[0]}">upgrade_sock</text>')
    b.append(f'<text x="470" y="140" text-anchor="middle" font-family="{SANS}" font-size="10" fill="#475569">共享路径 · 传递 FD</text>')
    b.append(f'<text x="470" y="156" text-anchor="middle" font-family="{SANS}" font-size="10" fill="#475569">(非纯 SO_REUSEPORT)</text>')
    b.append(arrow(290, 120, 360, 120, "SIGQUIT", DAN[0]))
    b.append(arrow(580, 140, 650, 140, "接管", PXY[0]))
    b.append(caption(W, 250, "保证：每个请求要么旧进程处理、要么新进程处理；不会 connection refused；宽限期内在途请求不被中断"))
    b.append(caption(W, 280, "SIGTERM = 优雅关闭；SIGQUIT = 优雅升级。这就是 nginx `USR2` 平滑升级的 Rust 版"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 6 生态
def fig_eco():
    W, H = 940, 300
    b = []
    b.append(box(300, 40, 340, 56, "你的产品", ["反向代理 · API 网关 · LB · WAF · 边缘服务"], GRY))
    b.append(box(60, 130, 360, 60, "River（ISRG 开箱应用）", ["配置文件驱动、无需写码 —— 适合直接部署"], PXY))
    b.append(box(520, 130, 360, 60, "自研代理（写 Rust）", ["实现 ProxyHttp，完全可编程 —— 最大灵活"], UP))
    b.append(box(230, 224, 480, 52, "Pingora（框架 / 引擎）", ["pingora-core / proxy / load-balancing / cache / http …"], SRV))
    b.append(arrow(240, 190, 380, 224))
    b.append(arrow(700, 190, 560, 224))
    b.append(arrow(430, 96, 300, 130))
    b.append(arrow(510, 96, 700, 130))
    b.append(caption(W, 294, "「Pingora 是引擎，不是整车」：要开箱即用选 River；要极致可编程就直接基于 Pingora 写代理"))
    return svg(W, H, "".join(b))


IMG1 = b64img(fig_arch(), "图1：Pingora 整体架构")
IMG2 = b64img(fig_life(), "图2：请求生命周期与 filter 钩子")
IMG3 = b64img(fig_pool(), "图3：连接池模型 nginx vs Pingora")
IMG4 = b64img(fig_lb(), "图4：负载均衡与健康检查")
IMG5 = b64img(fig_upgrade(), "图5：零停机热升级")
IMG6 = b64img(fig_eco(), "图6：Pingora 生态定位")


def main():
    D = []
    A = D.append
    A("# Pingora 技术方案：用 Rust 构建下一代代理")
    A("")
    A("> **一句话**：Pingora 是 Cloudflare 用 Rust 写的**网络服务框架**，用来构建高性能、可编程、内存安全的代理（反代 / API 网关 / 负载均衡）。它是 Cloudflare 内部替代 nginx 的引擎，支撑其边缘每天 **1 万亿+** 请求。")
    A("> **重要定位**：Pingora **不是** nginx 那样「装上就用、写配置文件」的二进制——它是**库/框架**，你用 Rust 实现 `ProxyHttp` trait 来定义代理行为。要开箱即用的应用，看基于它构建的 **River**。")
    A("> **版本基线**：umbrella crate `pingora` **0.9.x**；Rust **MSRV 1.84**（滚动 6 个月）；**Linux 为一级平台**，macOS 可用、Windows 初步。2024-02 开源。")
    A("> **图**：6 张内嵌 base64 SVG，无外部依赖。")
    A("")
    A("---")
    A("")
    A("## 目录")
    A("")
    A("1. [为什么用它替代 nginx](#一为什么用它替代-nginx)")
    A("2. [整体架构](#二整体架构)")
    A("3. [请求生命周期与 filter 钩子](#三请求生命周期与-filter-钩子)")
    A("4. [编程模型：ProxyHttp trait](#四编程模型proxyhttp-trait)")
    A("5. [负载均衡与健康检查](#五负载均衡与健康检查)")
    A("6. [连接池与复用](#六连接池与复用)")
    A("7. [TLS 与协议](#七tls-与协议)")
    A("8. [缓存（实验性）](#八缓存实验性)")
    A("9. [零停机热升级](#九零停机热升级)")
    A("10. [可观测性与限流](#十可观测性与限流)")
    A("11. [部署与运维](#十一部署与运维)")
    A("12. [从 nginx 迁移映射](#十二从-nginx-迁移映射)")
    A("13. [选型、限制与落地建议](#十三选型限制与落地建议)")
    A("")
    A("---")
    A("")
    # 一
    A("## 一、为什么用它替代 nginx")
    A("")
    A("Cloudflare 的动机不是「跑分输了」，而是 nginx 在其规模下的**架构天花板**（源自官方博客）：")
    A("")
    A("1. **worker 进程钉死**：nginx 每个请求只能由某一个 worker 处理，CPU 密集或阻塞 IO 的请求会拖慢同 worker 的其它请求，核间负载不均。")
    A("2. **连接复用差（最关键）**：nginx 连接池是**每 worker 各一份**，请求落到某 worker 只能复用该 worker 的连接，导致大量重复的上游 TCP/TLS 握手。")
    A("")
    A("Pingora 用「**多线程单进程 + 全局共享连接池**」正面解决这两点。")
    A("")
    A("### 性能数字（诚实标注来源）")
    A("")
    A("| 指标 | 数值 | 来源可靠度 |")
    A("|---|---|---|")
    A("| 请求量 | **> 1 万亿 / 天** | Cloudflare 官方博客 |")
    A("| 资源占用 | 仅为旧代理设施的 **约 1/3 CPU 与内存** | Cloudflare 官方（原话 “about a third”） |")
    A("| 换算说法 | 「CPU −70% / 内存 −67%」 | ⚠️ 第三方转述，非官方原文 |")
    A("| 单服务吞吐 | pingora-origin **35M+ req/s**；边缘 40M+ req/s | 官方 2025 帖 / 第三方 |")
    A("")
    A("> ⚠️ **不要把它当成受控 benchmark**：以上是 Cloudflare **生产机队的观测值**，不是同条件对拍实验；官方从未发布「Pingora vs nginx」的 RPS/延迟对拍表。「1/3」是官方口径，「70%/67%」只出现在第三方博客，可靠度更低。本方案不伪造对拍数据。")
    A("")
    # 二
    A("## 二、整体架构")
    A("")
    A(IMG1)
    A("")
    A("三层对象：")
    A("")
    A("- **`Server`**：进程本体，管信号、配置、线程编排、热升级。")
    A("- **`Service`**：一个可监听端口的服务单元。两类常用：`HttpProxy`（你的 `ProxyHttp` 实现）与 `Background`（跑 `LoadBalancer` 健康检查等后台任务）。")
    A("- **运行时**：多线程 work-stealing（tokio），**单地址空间**——这是全局连接池与核间均衡的前提。")
    A("")
    A("crate 全景：")
    A("")
    A("| crate | 职责 |")
    A("|---|---|")
    A("| `pingora` | umbrella，聚合下列 + `prelude` |")
    A("| `pingora-core` | Server / Service / 监听 / 协议 / 基础 trait |")
    A("| `pingora-proxy` | `ProxyHttp` trait + `http_proxy_service()` |")
    A("| `pingora-http` | `RequestHeader` / `ResponseHeader` 等 HTTP 类型 |")
    A("| `pingora-load-balancing` | `LoadBalancer`、选择算法、健康检查、服务发现 |")
    A("| `pingora-cache` | HTTP 缓存（**实验性**） |")
    A("| `pingora-openssl` / `pingora-boringssl` | 两套 TLS 后端二选一 |")
    A("| `pingora-ketama` | 一致性哈希（nginx 算法的 Rust 移植） |")
    A("| `pingora-limits` / `pingora-pool` / `pingora-timeout` | 限流 / 连接池 / 超时 |")
    A("")
    # 三
    A("## 三、请求生命周期与 filter 钩子")
    A("")
    A("Pingora 把一次代理请求切成若干**阶段（phase）**，每个阶段暴露一个可覆盖的 filter，让你注入逻辑。这是它「可编程」的核心。")
    A("")
    A(IMG2)
    A("")
    A("| 阶段 | 时机 / 用途 |")
    A("|---|---|")
    A("| `early_request_filter` | 最早，先于一切下游模块逻辑，最细粒度控制 |")
    A("| `request_filter` | 鉴权 / 校验 / 限流 / 可**短路返回**（返回 `Ok(true)` = 已处理，不再转发） |")
    A("| `upstream_peer` ★ | **唯一必须实现**：选上游、决定如何连接，返回 `Box<HttpPeer>` |")
    A("| `connected_to_upstream` | 连上后回调，记录 RTT / TLS cipher |")
    A("| `upstream_request_filter` | 发往上游前改写请求头（加鉴权、抹客户端信息、改 Host） |")
    A("| `response_filter` | 收到上游响应头、回给下游前改写（隐藏后端版本、改缓存头） |")
    A("| `response_body_filter` | 流式改写响应体 |")
    A("| `fail_to_connect` | 连接失败：判定是否**可重试**（可重回 `upstream_peer` 换节点） |")
    A("| `fail_to_proxy` | 全局兜底：任一阶段出错时生成自定义错误响应 |")
    A("| `logging` | 请求结束**必经**，做访问日志 / 指标 |")
    A("")
    A("> `ProxyHttp` 共 30+ 个方法，**绝大多数有默认实现**——你只覆盖关心的阶段。每请求还有一个 `CTX`（`new_ctx()` 创建）贯穿所有阶段，用来携带 trace id、计时、选路结果等状态。")
    A("")
    # 四
    A("## 四、编程模型：ProxyHttp trait")
    A("")
    A("`Cargo.toml`：")
    A("")
    A("```toml")
    A(r'''[dependencies]
pingora = { version = "0.9", features = ["lb"] }   # lb=负载均衡；tls 按需选 openssl/boringssl 特性
async-trait = "0.1"''')
    A("```")
    A("")
    A("一个带负载均衡 + 健康检查的完整反向代理（对齐官方 `load_balancer.rs`）：")
    A("")
    A("```rust")
    A(r'''use async_trait::async_trait;
use pingora::prelude::*;          // ProxyHttp / Session / HttpPeer / Result / Server / LoadBalancer …
use std::sync::Arc;

pub struct LB(Arc<LoadBalancer<RoundRobin>>);

#[async_trait]
impl ProxyHttp for LB {
    type CTX = ();
    fn new_ctx(&self) -> Self::CTX {}

    // 唯一必须实现：选一个上游后端
    async fn upstream_peer(&self, _session: &mut Session, _ctx: &mut ())
        -> Result<Box<HttpPeer>>
    {
        let backend = self.0.select(b"", 256).unwrap();       // 按算法选（key, max_iterations）
        // HttpPeer::new(地址, 是否 TLS, SNI)
        let peer = HttpPeer::new(backend, true, "one.one.one.one".to_string());
        Ok(Box::new(peer))
    }

    // 发往上游前改写请求头
    async fn upstream_request_filter(&self, _s: &mut Session,
        req: &mut RequestHeader, _ctx: &mut ()) -> Result<()>
    {
        req.insert_header("Host", "one.one.one.one")?;
        Ok(())
    }
}

fn main() {
    let mut server = Server::new(None).unwrap();
    server.bootstrap();

    // 后端集合 + TCP 健康检查，跑成后台服务
    let mut upstreams =
        LoadBalancer::try_from_iter(["1.1.1.1:443", "1.0.0.1:443"]).unwrap();
    upstreams.set_health_check(TcpHealthCheck::new());
    upstreams.health_check_frequency = Some(std::time::Duration::from_secs(1));

    let background = background_service("health check", upstreams);
    let upstreams = background.task();                 // Arc<LoadBalancer<RoundRobin>>

    // 代理服务，监听 6188
    let mut proxy = http_proxy_service(&server.configuration, LB(upstreams));
    proxy.add_tcp("0.0.0.0:6188");

    server.add_service(background);
    server.add_service(proxy);
    server.run_forever();
}''')
    A("```")
    A("")
    A("**短路返回**（在 `request_filter` 里自己应答，不打上游，比如健康探针 / 拦截）：")
    A("")
    A("```rust")
    A(r'''async fn request_filter(&self, session: &mut Session, _ctx: &mut Self::CTX)
    -> Result<bool>
{
    if session.req_header().uri.path() == "/healthz" {
        let mut resp = ResponseHeader::build(200, None)?;
        resp.insert_header("Content-Type", "text/plain")?;
        session.write_response_header(Box::new(resp), false).await?;
        session.write_response_body(Some("ok".into()), true).await?;
        return Ok(true);     // 已自行处理，框架不再走 upstream_peer
    }
    Ok(false)                // 继续正常代理流程
}''')
    A("```")
    A("")
    # 五
    A("## 五、负载均衡与健康检查")
    A("")
    A(IMG4)
    A("")
    A("`pingora-load-balancing` 提供服务发现、健康检查与选择算法：")
    A("")
    A("| 能力 | 选项 |")
    A("|---|---|")
    A("| 选择算法 | `RoundRobin` · `Random` · `Weighted` · `KetamaHashing`（一致性哈希，nginx 算法移植，默认每权重 160 点） |")
    A("| 健康检查 | `TcpHealthCheck` · `HttpHealthCheck`（实现 `HealthCheck` trait） |")
    A("| 频率 | `health_check_frequency` / `update_frequency`（服务发现刷新） |")
    A("| 选择接口 | `select(key, max_iterations)` · `select_with(自定义 accept 函数)` |")
    A("")
    A("**运行方式**：`LoadBalancer` 必须作为 `background_service` 跑起来才会做健康检查/发现；`background.task()` 返回 `Arc<LoadBalancer<_>>` 交给你的 `ProxyHttp`。上面第四节代码就是标准写法——健康检查频率设 1 秒，则节点恢复后约 1 秒内重新进入轮询。")
    A("")
    A("> 一致性哈希（Ketama）适合「同一 key 尽量命中同一后端」（缓存亲和、会话粘滞）；注意其查找是线性的，用 `max_iterations` 兜底搜索步数。")
    A("")
    # 六
    A("## 六、连接池与复用")
    A("")
    A("这是 Pingora 相对 nginx 最实质的性能来源。")
    A("")
    A(IMG3)
    A("")
    A("- **两级设计**：每线程一个**无锁热池**（thread-local，接近裸内存访问速度）+ 一个**全局共享池**（Mutex）。热池命中最快，未命中回全局池借。")
    A("- **跨线程复用**：因为 worker 是**同一进程里的线程**，A 线程建立的上游空闲连接，B 线程也能借用；nginx 多进程模型下邻居 worker 的空闲连接彼此看不见，只能新建。")
    A("- **per-Peer 严格匹配**：只有「完全相同的 Peer」（地址 + TLS + SNI + …全部属性一致）之间才复用，保证正确性与安全。要**禁用**某 Peer 的复用，把它的 `idle_timeout` 设为 0。")
    A("")
    A("> 连接池、TLS 握手、读写、请求解析这些通用代理工作都由框架包办，你只写「选谁、改什么、记什么」的业务逻辑。")
    A("")
    # 七
    A("## 七、TLS 与协议")
    A("")
    A("- **协议**：下游与上游均支持 **HTTP/1.x 与 HTTP/2**（含 h2 到上游）。")
    A("- **TLS 后端二选一**：`pingora-openssl` 或 `pingora-boringssl`（编译期特性选择）。BoringSSL 需 Clang，OpenSSL 需 Perl 5。")
    A("- 上游 `HttpPeer` 携带是否 TLS、SNI、验证选项；下游监听用 `add_tls(...)` 配证书。")
    A("- 近期版本对 HTTP/1 帧做了**安全加固**：拒绝非法 `Content-Length` 请求、响应里 `Content-Length` 与 `Transfer-Encoding` 冲突时按 RFC 处理，消除请求走私（request smuggling）的歧义。")
    A("")
    # 八
    A("## 八、缓存（实验性）")
    A("")
    A("`pingora-cache` 提供 HTTP 缓存（缓存键、TTL、可插拔存储、`request_cache_filter` / `cache_key_callback` / `response_cache_filter` 等钩子）。")
    A("")
    A("> ⚠️ **官方明确标注：缓存集成属实验性，相关 API 高度不稳定（highly volatile）。** 生产上做缓存要么锁死版本并做好升级会破坏的预期，要么先用成熟缓存层（如前置 CDN / Varnish），把 Pingora 定位在可编程代理/LB。")
    A("")
    # 九
    A("## 九、零停机热升级")
    A("")
    A("Pingora 支持**不丢一个请求**的自我升级——这是它「运维可靠」的招牌能力。")
    A("")
    A(IMG5)
    A("")
    A("流程：")
    A("")
    A("1. 老、新进程约定同一个 `upgrade_sock`（共享套接字路径）。")
    A("2. 新进程用 `--upgrade` 启动，**不立即绑定端口**，而是去向老进程索要监听套接字。")
    A("3. 给老进程发 **`SIGQUIT`**：老进程经 `upgrade_sock` 把**监听 socket 的文件描述符**交给新进程；新进程随即开始处理新连接。")
    A("4. 老进程继续把在途请求跑完（宽限期内），然后退出。")
    A("")
    A("**保证**：任一请求要么被老进程、要么被新进程处理；不会出现 connection refused；宽限期内能完成的在途请求不被中断。")
    A("")
    A("> 传的是**真实监听 FD**，而非单纯 `SO_REUSEPORT` 重新绑定——因为 `SO_REUSEPORT` 会在内核里新建一个独立 socket 结构，无法继承老连接的接受队列。信号约定：`SIGTERM` = 优雅关闭，`SIGQUIT` = 优雅升级（相当于 nginx 的 `USR2`）。")
    A("")
    # 十
    A("## 十、可观测性与限流")
    A("")
    A("- **访问日志 / 指标**：在 `logging` 阶段统一落日志、上报指标（延迟、字节数、上游 RTT、状态码）；`CTX` 里攒的计时/trace 在这里汇总。")
    A("- **Prometheus**：可挂一个独立 metrics service 暴露 `/metrics`（Pingora 提供 Prometheus 集成的服务）。")
    A("- **限流**：`pingora-limits` 提供估算器（滑动窗口 / 近似计数），配合 `request_filter` 做每 key（IP / API key / 路径）限流，超限直接短路返回 429。")
    A("- **错误处理**：`fail_to_connect` 判重试、`fail_to_proxy` 兜底自定义错误页——把可重试与不可重试分开，是做高可用代理的关键。")
    A("")
    # 十一
    A("## 十一、部署与运维")
    A("")
    A("**命令行 / 配置**（Pingora 内置 clap 解析）：")
    A("")
    A("```bash")
    A(r'''./my-proxy -c /etc/my-proxy/conf.yaml     # -c 指定配置文件
./my-proxy -d                              # -d 守护进程
./my-proxy -u                              # -u/--upgrade 热升级（配合对老进程发 SIGQUIT）''')
    A("```")
    A("")
    A("**ServerConf 常用项**（YAML）：")
    A("")
    A("```yaml")
    A(r'''---
version: 1
threads: 4                     # 工作线程数
work_stealing: true            # 线程间任务窃取，核间均衡
pid_file: /run/my-proxy.pid
upgrade_sock: /run/my-proxy_upgrade.sock   # 热升级 FD 传递套接字
error_log: /var/log/my-proxy/error.log
upstream_keepalive_pool_size: 128          # 上游连接池大小
ca_file: /etc/ssl/certs/ca-certificates.crt''')
    A("```")
    A("")
    A("**systemd**：用 `ExecStart` 起进程、`ExecReload` 发 `SIGQUIT` + 拉起 `--upgrade` 新进程即可实现平滑重载；`Type=forking` 配 `pid_file`。生产建议 Linux（一级平台）。")
    A("")
    A("> **开箱即用**：不想写 Rust，可用 **River**——ISRG 基于 Pingora 构建的反向代理**应用**，配置文件驱动。定位：Pingora 是引擎，River 是整车。")
    A("")
    A(IMG6)
    A("")
    # 十二
    A("## 十二、从 nginx 迁移映射")
    A("")
    A("| nginx 概念 | Pingora 对应 | 说明 |")
    A("|---|---|---|")
    A("| `nginx.conf` 声明式配置 | **写 Rust 实现 `ProxyHttp`** | 逻辑即代码；配置文件只管进程/线程/端口等运行参数 |")
    A("| `upstream {}` + `server` | `LoadBalancer::try_from_iter([...])` | 后端集合 |")
    A("| `least_conn` / `ip_hash` / 轮询 | `RoundRobin` / `Weighted` / `KetamaHashing` | 选择算法 |")
    A("| `proxy_pass` | `upstream_peer()` 返回 `HttpPeer` | 选上游 |")
    A("| `proxy_set_header` | `upstream_request_filter` | 改上游请求头 |")
    A("| `add_header` / `sub_filter` | `response_filter` / `response_body_filter` | 改响应 |")
    A("| `location` 路由 | `request_filter` / `upstream_peer` 里按 path 分支 | 用代码路由 |")
    A("| `limit_req` | `pingora-limits` + `request_filter` | 限流 |")
    A("| `health_check`（商业版） | `Tcp/HttpHealthCheck` + background service | 开源自带 |")
    A("| `nginx -s reload` / `USR2` | `SIGQUIT` + `--upgrade` | 零停机热升级 |")
    A("| Lua / njs 扩展 | **原生 Rust**（无需嵌入脚本） | 性能与类型安全都更好 |")
    A("")
    # 十三
    A("## 十三、选型、限制与落地建议")
    A("")
    A("**适合 Pingora 的场景**：需要**深度可编程**的代理 / API 网关 / 自定义负载均衡；追求内存安全与高连接复用；团队有 Rust 能力。")
    A("")
    A("**先掂量的限制**：")
    A("")
    A("- **不是 drop-in**：迁移 = 写 Rust，不是翻译 `nginx.conf`。评估工程量。")
    A("- **缓存实验性**：`pingora-cache` API 不稳定，重缓存场景谨慎。")
    A("- **平台**：Linux 一级；Windows 仅初步。")
    A("- **静态文件/通用 Web 服务器**：Pingora 面向**代理**，不是替代 nginx 做静态站点/FastCGI 的全能 Web server；那类需求 nginx/caddy 仍更合适。")
    A("- **MSRV 滚动**：需跟进 Rust 版本（当前 1.84，滚动 6 个月）。")
    A("")
    A("**落地路线建议**：")
    A("")
    A("1. **试点**：挑一个「逻辑复杂、但功能边界清晰」的代理场景（如需要自定义选路/鉴权的内部网关）用 Pingora 重写，直接吃到可编程 + 连接复用红利。")
    A("2. **不想写码**：先用 **River** 验证部署/运维闭环（热升级、健康检查），再决定是否下沉到框架层定制。")
    A("3. **与本仓的呼应**：Pingora 的「多线程单进程 + 全局连接池 + 无状态 + 优雅升级」与本仓 `CLAUDE.md` 的「集群无状态、状态外置」理念一致；若要在 CMX 前面放一层可编程 Rust 代理（灰度/鉴权/多引擎反代），Pingora 是顺手的选型。")
    A("")
    A("---")
    A("")
    A("### 一句话收束")
    A("")
    A("> **Pingora = 把「写一个生产级代理」需要的脏活（连接池 / TLS / HTTP/1·2 / 优雅升级 / 健康检查）全包了，只把「选谁、改什么、记什么」这几个可编程钩子留给你。** 它是引擎不是整车——要整车用 River，要极致定制就自己基于它造。")
    A("")
    A("> 参考：Cloudflare 博客（how-we-built-pingora / pingora-open-source）、github.com/cloudflare/pingora（docs/user_guide、examples/load_balancer.rs）、docs.rs/pingora。版本以 2026 的 0.9 线为准；缓存等实验性 API 请对照对应版本文档。")
    txt = "\n".join(D)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(txt)
    print("output:", OUT)
    print("bytes :", os.path.getsize(OUT))


if __name__ == "__main__":
    main()
