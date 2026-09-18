#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成《Extism 插件框架详细使用说明》—— 内嵌 base64 SVG。
Run: python3 gen_extism.py   (extism 1.13 / extism-pdk 1.4，基于 wasmtime 27–30)
"""
import base64
import html
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "20260917_Extism-插件框架使用说明.md")

SANS = "-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif"
MONO = "ui-monospace,SFMono-Regular,Menlo,monospace"
BG = "#fbfdff"
HOST = ("#4338ca", "#eef2ff")   # host indigo
RT = ("#7c3aed", "#f5f3ff")     # runtime violet
PLG = ("#0d9488", "#f0fdfa")    # plugin teal
CAP = ("#b45309", "#fffbeb")    # capability amber
DAN = ("#dc2626", "#fef2f2")    # danger red
GRY = ("#475569", "#f1f5f9")    # slate


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
           f'<rect x="{x}" y="{y}" width="{w}" height="24" rx="8" fill="{st}"/>',
           f'<rect x="{x}" y="{y+16}" width="{w}" height="8" fill="{st}"/>',
           f'<text x="{x+11}" y="{y+17}" font-family="{MONO}" font-size="12" font-weight="700" fill="{tcol}">{esc(title)}</text>']
    yy = y + 24 + 15
    for ln in lines:
        out.append(f'<text x="{x+11}" y="{yy}" font-family="{SANS}" font-size="10.5" fill="#1e293b">{esc(ln)}</text>')
        yy += 15
    out.append('</g>')
    return "".join(out)


def arrow(x1, y1, x2, y2, label="", col="#64748b", dash="5 3"):
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    out = ['<g>', f'<path d="M {x1} {y1} L {x2} {y2}" fill="none" stroke="{col}" stroke-width="1.6" '
           f'stroke-dasharray="{dash}" marker-end="url(#a)"/>']
    if label:
        lw = 7 * len(label) + 12
        out.append(f'<rect x="{mx-lw/2:.0f}" y="{my-9:.0f}" width="{lw}" height="16" rx="4" fill="#fff" '
                   f'fill-opacity="0.95" stroke="#cbd5e1" stroke-width="0.7"/>')
        out.append(f'<text x="{mx:.0f}" y="{my+3:.0f}" text-anchor="middle" font-family="{MONO}" '
                   f'font-size="9.5" fill="#334155">{esc(label)}</text>')
    out.append('</g>')
    return "".join(out)


def caption(w, y, text):
    return (f'<text x="{w/2:.0f}" y="{y}" text-anchor="middle" font-family="{SANS}" font-size="12.5" '
            f'fill="#334155">{esc(text)}</text>')


# ---------------------------------------------------------------- FIG 1 架构总览
def fig_arch():
    W, H = 940, 380
    b = []
    b.append(box(40, 70, 210, 210, "宿主应用（任意语言）", [
        "Rust / Go / Python", "Node / C# / Java …", "", "引入 extism 宿主 SDK",
        "load manifest → call", "", "几行代码就能加载插件"], HOST))
    b.append(box(365, 90, 210, 170, "Extism 运行时", [
        "封装 wasmtime 引擎", "简单 bytes ABI", "Manifest 能力策略", "host functions",
        "config / vars / HTTP"], RT))
    b.append(box(690, 70, 210, 210, "插件（任意语言）", [
        "Rust / Go / JS / Zig", "C / AssemblyScript …", "", "用 extism-pdk (PDK)",
        "#[plugin_fn] 导出", "", "编译成一个 .wasm"], PLG))
    b.append(arrow(250, 160, 365, 160, "SDK 调用", HOST[0]))
    b.append(arrow(690, 200, 575, 200, "PDK 导出", PLG[0]))
    b.append(caption(W, 330, "一次编译的插件，任意语言写的宿主都能加载；一次写好的宿主，任意语言写的插件都能跑 —— 这是 Extism 的核心卖点"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 2 数据流
def fig_dataflow():
    W, H = 940, 300
    b = []
    stages = [
        (30, "宿主", ["plugin.call(", '  "f", input)'], HOST),
        (222, "写入插件内存", ["input bytes", "→ 线性内存"], RT),
        (414, "插件函数", ["#[plugin_fn]", "f(input) -> out"], PLG),
        (606, "读回输出", ["output(bytes)", "宿主取回"], RT),
        (798, "宿主拿到结果", ["Output", "(String/Json…)"], HOST),
    ]
    for (x, t, lines, col) in stages:
        b.append(box(x, 90, 150, 78, t, lines, col))
    for x in (180, 372, 564, 756):
        b.append(arrow(x, 129, x + 42, 129))
    b.append(caption(W, 230, "Extism ABI 极简：可选字节进、可选字节出。复杂类型（String / Json / Msgpack）由 SDK/PDK 自动编解码"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 3 Manifest 能力面板
def fig_manifest():
    W, H = 940, 340
    b = []
    b.append(f'<rect x="270" y="50" width="400" height="250" rx="12" fill="{CAP[1]}" stroke="{CAP[0]}" stroke-width="2.2"/>')
    b.append(f'<text x="470" y="78" text-anchor="middle" font-family="{MONO}" font-size="13" font-weight="700" fill="{CAP[0]}">Manifest = 能力清单（默认拒绝）</text>')
    rows = [
        ("wasm 源", "Wasm::file / url / data"),
        ("memory max", "with_memory_max(页数) · 超限即 oom trap"),
        ("timeout", "with_timeout(Duration) · 墙钟超时"),
        ("allowed_hosts", "with_allowed_host(...) · 不给=禁所有 HTTP"),
        ("allowed_paths", "with_allowed_path(宿主, 插件) · WASI 文件"),
        ("config", "with_config_key(k,v) · 插件只读读取"),
    ]
    y = 100
    for (k, v) in rows:
        b.append(f'<text x="292" y="{y}" font-family="{MONO}" font-size="11.5" font-weight="700" fill="#0f172a">{esc(k)}</text>')
        b.append(f'<text x="292" y="{y+15}" font-family="{SANS}" font-size="10.5" fill="#475569">{esc(v)}</text>')
        y += 33
    b.append(caption(W, 328, "没在 manifest 里显式授予的能力，插件一律得不到 —— 网络、文件、内存、时间都是白名单"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 4 宿主函数双向
def fig_hostfn():
    W, H = 940, 320
    b = []
    b.append(box(60, 80, 320, 150, "宿主侧（extism SDK）", [
        "host_fn!(kv_read(user_data: T; key: String) -> u32 { … })",
        "PluginBuilder::new(manifest)",
        "  .with_function(\"kv_read\", [PTR],[PTR], data, kv_read)",
        "UserData 跨线程须 Send + Sync"], HOST))
    b.append(box(560, 80, 320, 150, "插件侧（extism-pdk）", [
        "#[host_fn]",
        "extern \"ExtismHost\" {",
        "    fn kv_read(key: String) -> u32;",
        "}   // 调用处需 unsafe { }"], PLG))
    b.append(arrow(380, 130, 560, 130, "定义 → 授予能力", HOST[0]))
    b.append(arrow(560, 185, 380, 185, "声明 → 回调宿主", PLG[0]))
    b.append(caption(W, 275, "宿主函数 = 把沙箱外的能力（DB / KV / 密钥）受控地递给插件；两侧同名，一方定义一方声明"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 5 分层
def fig_layers():
    W, H = 940, 320
    b = []
    b.append(box(190, 60, 560, 56, "你的宿主应用", ["load manifest → plugin.call(...) —— 通常十几行"], HOST))
    b.append(box(190, 140, 560, 70, "Extism", [
        "bytes ABI · Manifest 能力策略 · host functions",
        "config / variables · HTTP · 多语言 SDK+PDK · CompiledPlugin 池"], RT))
    b.append(box(190, 236, 560, 56, "wasmtime", ["引擎 · Cranelift · 沙箱 · fuel/epoch · 线性内存"], GRY))
    b.append(arrow(470, 116, 470, 140, ""))
    b.append(arrow(470, 210, 470, 236, ""))
    b.append(f'<text x="770" y="175" font-family="{SANS}" font-size="11" fill="#475569">Extism =</text>')
    b.append(f'<text x="770" y="192" font-family="{SANS}" font-size="11" fill="#475569">把 wasmtime 的裸 API</text>')
    b.append(f'<text x="770" y="209" font-family="{SANS}" font-size="11" fill="#475569">收敛成插件框架</text>')
    b.append(caption(W, 312, "要极致掌控（编译/组件/资源）→ 裸 wasmtime；要「几行代码上插件、还跨语言」→ Extism"))
    return svg(W, H, "".join(b))


IMG1 = b64img(fig_arch(), "图1：Extism 跨语言架构")
IMG2 = b64img(fig_dataflow(), "图2：一次调用的字节数据流")
IMG3 = b64img(fig_manifest(), "图3：Manifest 能力清单")
IMG4 = b64img(fig_hostfn(), "图4：宿主函数双向")
IMG5 = b64img(fig_layers(), "图5：Extism 与 wasmtime 分层")


def main():
    D = []
    A = D.append
    A("# Extism 插件框架详细使用说明")
    A("")
    A("> **定位**：Extism 是**通用插件框架**——在 `wasmtime` 之上封装出「极简 bytes ABI + 能力清单 Manifest + 宿主函数 + 配置/状态/HTTP + 多语言 SDK/PDK」。一句话：**让任何软件都能安全地被插件扩展，且宿主与插件可以是不同语言。**")
    A("> **版本基线**：宿主 SDK `extism` **1.13.x**、插件 PDK `extism-pdk` **1.4.x**（内部基于 wasmtime 27–30）。Extism 1.x 自 2024 稳定，比裸 wasmtime 稳。")
    A("> **与本仓的关系**：`backend/cmx-container/cmx-runtime` 正是基于 Extism 的 WASM 插件运行时——本文可直接映射到该模块的用法。")
    A("> **图**：5 张内嵌 base64 SVG，无外部依赖。")
    A("")
    A("---")
    A("")
    A("## 目录")
    A("")
    A("1. [Extism 解决什么，与裸 wasmtime 的关系](#一extism-解决什么与裸-wasmtime-的关系)")
    A("2. [架构：宿主 SDK + PDK + 极简 ABI](#二架构宿主-sdk--pdk--极简-abi)")
    A("3. [宿主侧快速开始](#三宿主侧快速开始)")
    A("4. [写插件（PDK）](#四写插件pdk)")
    A("5. [Manifest：能力清单](#五manifest能力清单)")
    A("6. [宿主函数：把沙箱外的能力递进去](#六宿主函数把沙箱外的能力递进去)")
    A("7. [配置、变量与 HTTP](#七配置变量与-http)")
    A("8. [性能与并发：CompiledPlugin 与插件池](#八性能与并发compiledplugin-与插件池)")
    A("9. [资源治理与安全](#九资源治理与安全)")
    A("10. [Extism vs 裸 wasmtime：怎么选](#十extism-vs-裸-wasmtime怎么选)")
    A("11. [落地 CMX：对到 cmx-runtime](#十一落地-cmx对到-cmx-runtime)")
    A("12. [常见坑](#十二常见坑)")
    A("13. [多语言生态与版本](#十三多语言生态与版本)")
    A("")
    A("---")
    A("")
    # 一
    A("## 一、Extism 解决什么，与裸 wasmtime 的关系")
    A("")
    A("裸 `wasmtime` 给你的是引擎和沙箱，但要跑一个插件，你得自己搞定：把字符串/结构体在线性内存里手搓 ABI、写 `alloc`、管理内存偏移、注入宿主函数、配资源上限……**样板巨多**。")
    A("")
    A("Extism 把这些**收敛成一个插件框架**，只暴露一个极简约定：**可选字节进、可选字节出**。复杂类型自动编解码，能力用 Manifest 白名单声明，还顺带给了配置、跨调用状态、HTTP，并且**宿主和插件可以是完全不同的语言**。")
    A("")
    A(IMG5)
    A("")
    A("| 你要的 | 裸 wasmtime | Extism |")
    A("|---|---|---|")
    A("| 调一个「字节进字节出」的函数 | 手搓内存 ABI + alloc | `plugin.call::<In,Out>(name, input)` |")
    A("| 复杂类型（String/JSON） | 自己序列化 + 写内存 | 类型参数自动编解码 |")
    A("| 资源/能力策略 | 逐项写 `Config`/`StoreLimits`/WASI | 一个 `Manifest` 声明式搞定 |")
    A("| 宿主函数 | `Linker::func_wrap` + 手读内存 | `host_fn!` 宏，参数已是原生类型 |")
    A("| 跨语言 | 只有 Rust 嵌入 API | 10+ 宿主 SDK / 10+ PDK |")
    A("| 完全掌控编译/组件/异步 | ✅ 全在你手里 | ⚠️ 框架替你决定了大部分 |")
    A("")
    A("**选择原则**：要极致掌控（组件模型、AOT、pooling、自定义异步调度）→ 裸 wasmtime；要「十几行就上插件、还得跨语言、还得快速给能力」→ Extism。")
    A("")
    # 二
    A("## 二、架构：宿主 SDK + PDK + 极简 ABI")
    A("")
    A(IMG1)
    A("")
    A("三个角色：")
    A("")
    A("- **宿主 SDK**（`extism` crate 等）：你的应用引入它来**加载并调用**插件。")
    A("- **PDK**（Plug-in Development Kit，`extism-pdk` 等）：写插件时引入，用宏把普通函数**导出**成 Extism 函数。")
    A("- **Manifest**：声明「加载哪个 wasm + 给哪些能力」。")
    A("")
    A("一次调用的数据流，就是字节进、字节出：")
    A("")
    A(IMG2)
    A("")
    # 三
    A("## 三、宿主侧快速开始")
    A("")
    A("`Cargo.toml`：")
    A("")
    A("```toml")
    A(r'''[dependencies]
extism = "1"        # 宿主 SDK（当前 1.13.x）
anyhow = "1"''')
    A("```")
    A("")
    A("加载一个官方示例插件并调用它的 `count_vowels` 导出：")
    A("")
    A("```rust")
    A(r'''use extism::*;

fn main() -> anyhow::Result<()> {
    // 1) wasm 源：url / file / data 三选一
    let url = Wasm::url(
        "https://github.com/extism/plugins/releases/latest/download/count_vowels.wasm",
    );

    // 2) Manifest：这里只声明 wasm 源，不给任何额外能力
    let manifest = Manifest::new([url]);

    // 3) 建插件：(manifest, 宿主函数列表, with_wasi)
    let mut plugin = Plugin::new(&manifest, [], true)?;

    // 4) 调用：可选字节进、可选字节出；这里类型标注为 <&str, &str>
    let out = plugin.call::<&str, &str>("count_vowels", "Hello, world!")?;

    println!("{out}");   // => {"count":3,"total":3,"vowels":"aeiouAEIOU"}
    Ok(())
}''')
    A("```")
    A("")
    A("`plugin.call::<In, Out>` 的 `In`/`Out` 可以是 `&str` / `String` / `Vec<u8>` / `&[u8]`，或 `Json<T>` / `Msgpack<T>`（自动 serde）。这就是「字节 ABI + 自动编解码」的全部体验。")
    A("")
    # 四
    A("## 四、写插件（PDK）")
    A("")
    A("插件是一个 `cdylib` 的 wasm。`Cargo.toml`：")
    A("")
    A("```toml")
    A(r'''[lib]
crate-type = ["cdylib"]

[dependencies]
extism-pdk = "1"                                  # 当前 1.4.x
serde = { version = "1", features = ["derive"] }''')
    A("```")
    A("")
    A("`src/lib.rs`——用 `#[plugin_fn]` 把普通函数导出，返回 `FnResult<T>`：")
    A("")
    A("```rust")
    A(r'''use extism_pdk::*;
use serde::Serialize;

#[derive(Serialize)]
struct Out { count: usize }

#[plugin_fn]
pub fn count_vowels(input: String) -> FnResult<Json<Out>> {
    let count = input.chars().filter(|c| "aeiouAEIOU".contains(*c)).count();
    Ok(Json(Out { count }))     // Json<T> 自动序列化为字节输出
}''')
    A("```")
    A("")
    A("编译与本地测试（用 Extism CLI，不必写宿主就能验证）：")
    A("")
    A("```bash")
    A(r'''# 不需要系统访问 → 编到最轻量的 wasm32-unknown-unknown（要 WASI 才用 wasm32-wasip1）
cargo build --release --target wasm32-unknown-unknown

# 用 CLI 直接调，字节进字节出
extism call target/wasm32-unknown-unknown/release/plugin.wasm \
  count_vowels --input "Hello, world!"
# => {"count":3}''')
    A("```")
    A("")
    A("要点：")
    A("")
    A("- `#[plugin_fn]` 负责导出 + 处理底层 ABI，让你**像写普通 Rust 函数一样**写插件。")
    A("- 返回 `FnResult<T>`：`T` 可为 `String` / 数字 / `Vec<u8>` / `Json<T>` / `Msgpack<T>`；`Err` 自动带状态码 `-1`（可定制 `WithReturnCode`）。")
    A("- **插件不能直接 `println!`**（没有终端）；用 PDK 的 `log!` 宏。")
    A("")
    # 五
    A("## 五、Manifest：能力清单")
    A("")
    A("Manifest 是 Extism 的安全核心——**默认什么都不给，能力逐项显式授予**。")
    A("")
    A(IMG3)
    A("")
    A("```rust")
    A(r'''use extism::*;
use std::time::Duration;

let manifest = Manifest::new([Wasm::file("plugin.wasm")])
    .with_memory_max(64)                       // 线性内存上限 64 页 = 4 MiB（超限 → oom trap）
    .with_timeout(Duration::from_secs(5))      // 墙钟超时（epoch 实现）
    .with_allowed_host("*.example.com")        // 仅放行该 HTTP 主机；一个都不给 = 禁所有网络
    .with_allowed_path("./data", "/data")      // 宿主 ./data 挂到插件内 /data（需 with_wasi）
    .with_config_key("api_key", "secret");     // 插件用 config::get("api_key") 只读读取''')
    A("```")
    A("")
    A("| 字段 | 作用 | 不设的默认 |")
    A("|---|---|---|")
    A("| `with_memory_max(pages)` | 线性内存上限（1 页 = 64 KiB） | 引擎默认上限 |")
    A("| `with_timeout(Duration)` | 执行超时 | 不超时 |")
    A("| `with_allowed_host(host)` | HTTP 白名单（支持通配） | **禁所有 HTTP** |")
    A("| `with_allowed_path(host, guest)` | WASI 文件映射 | **无文件** |")
    A("| `with_config_key(k, v)` | 传给插件的只读配置 | 空 |")
    A("")
    A("> **安全默认值**：`allowed_hosts` / `allowed_paths` 不设就是**全禁**。Extism 的沙箱是「白名单」而非「黑名单」——这与裸 wasmtime 的能力模型一脉相承。")
    A("")
    # 六
    A("## 六、宿主函数：把沙箱外的能力递进去")
    A("")
    A("插件默认碰不到数据库、密钥、内部服务。要让它用，就由**宿主定义函数**递给它——这是受控的能力注入。")
    A("")
    A(IMG4)
    A("")
    A("### 6.1 宿主侧：`host_fn!` 定义 + `PluginBuilder` 注册")
    A("")
    A("```rust")
    A(r'''use extism::*;
use std::collections::BTreeMap;
use std::sync::Mutex;

type Kv = Mutex<BTreeMap<String, u32>>;

// 分号前的 `user_data: Kv` 声明 UserData 参数（宿主共享状态）
host_fn!(kv_read(user_data: Kv; key: String) -> u32 {
    let kv = user_data.get()?;
    let kv = kv.lock().unwrap();
    Ok(kv.get(&key).copied().unwrap_or(0))
});

host_fn!(kv_write(user_data: Kv; key: String, value: u32) {
    let kv = user_data.get()?;
    kv.lock().unwrap().insert(key, value);
    Ok(())
});

fn main() -> anyhow::Result<()> {
    // UserData 若跨线程共享，类型必须 Send + Sync（这里用 Mutex）
    let data = UserData::new(Mutex::new(BTreeMap::new()));

    let manifest = Manifest::new([Wasm::file("kv_plugin.wasm")]);
    let mut plugin = PluginBuilder::new(manifest)
        .with_wasi(true)
        // 签名：(名字, 入参类型, 出参类型, user_data, 函数)
        // Extism 把每个参数当作一个内存句柄，用 [PTR] 表示；无返回则出参为 []
        .with_function("kv_read",  [PTR], [PTR], data.clone(), kv_read)
        .with_function("kv_write", [PTR, PTR], [], data.clone(), kv_write)
        .build()?;

    let _ = plugin.call::<&str, &str>("run", "")?;
    Ok(())
}''')
    A("```")
    A("")
    A("低层写法是 `Function::new(name, [ValType::I64], [], UserData::default(), |plugin, inputs, outputs, ud| { … })`——闭包首参 `CurrentPlugin` 用于在宿主函数里读写插件内存。日常用 `host_fn!` 宏即可，它把内存句柄自动 marshal 成原生参数。")
    A("")
    A("### 6.2 插件侧：`#[host_fn]` 声明并调用")
    A("")
    A("```rust")
    A(r'''use extism_pdk::*;

// 声明宿主会提供的函数（同名）
#[host_fn]
extern "ExtismHost" {
    fn kv_read(key: String) -> u32;
    fn kv_write(key: String, value: u32);
}

#[plugin_fn]
pub fn run(_: ()) -> FnResult<()> {
    // 调宿主函数需要 unsafe（跨越沙箱边界）
    let n = unsafe { kv_read("counter".into())? };
    unsafe { kv_write("counter".into(), n + 1)? };
    Ok(())
}''')
    A("```")
    A("")
    A("> 两侧**同名**：宿主用 `extism` 的 `host_fn!` **定义**，插件用 `extism-pdk` 的 `#[host_fn]` **声明**。名字对不上，实例化时报缺失导入。")
    A("")
    # 七
    A("## 七、配置、变量与 HTTP")
    A("")
    A("Extism 给插件三样开箱即用的能力（都受 Manifest 管控）：")
    A("")
    A("| 机制 | 谁写 | 谁读 | 生命周期 |")
    A("|---|---|---|---|")
    A("| **config** | 宿主（Manifest） | 插件只读 | 随插件实例 |")
    A("| **variables** | 插件读写 | 插件 | **跨调用持久**（插件未卸载前） |")
    A("| **HTTP** | 插件发起 | —— | 仅 `allowed_hosts` 放行的主机 |")
    A("")
    A("```rust")
    A(r'''use extism_pdk::*;

#[plugin_fn]
pub fn tick(_: ()) -> FnResult<i64> {
    // 只读配置：来自宿主 Manifest.with_config_key
    let _api_key = config::get("api_key")?;

    // 变量：跨多次调用持久的可变状态（宿主未 free 插件前一直在）
    let mut n: i64 = var::get("count")?.unwrap_or(0);
    n += 1;
    var::set("count", n)?;
    Ok(n)                       // 第 1、2、3 次调用分别返回 1、2、3
}

#[plugin_fn]
pub fn fetch(url: String) -> FnResult<String> {
    // HTTP：只有 Manifest.allowed_hosts 放行时才成功，否则报错
    let req = HttpRequest::new(&url).with_method("GET");
    let res = http::request::<()>(&req, None)?;
    Ok(String::from_utf8(res.body())?)
}''')
    A("```")
    A("")
    A("> `variables` 让插件有了「会话记忆」——但它是**进程内、随实例**的状态。集群/多实例下别拿它当持久存储（与本仓「集群无状态」一致，持久态应外置）。")
    A("")
    # 八
    A("## 八、性能与并发：CompiledPlugin 与插件池")
    A("")
    A("和裸 wasmtime 同理：**编译贵、实例化频繁**。Extism 用 `CompiledPlugin` 把这对矛盾拆开——`PluginBuilder` 可以 `build()` 出单个 `Plugin`，也可以**编译成可复用模板 `CompiledPlugin`**，再从模板快速实例化多个 `Plugin`。")
    A("")
    A("```rust")
    A(r'''use extism::*;

// 编译一次（贵）：得到可复用模板
let compiled: CompiledPlugin = PluginBuilder::new(manifest)
    .with_wasi(true)
    .compile()?;

// 每请求从模板快速实例化（便宜）——放进对象池即为「插件池」
let mut plugin: Plugin = compiled.instantiate()?;
let out = plugin.call::<&str, &str>("run", input)?;
// 具体方法名以 docs.rs 对应版本为准（compile / instantiate 家族）''')
    A("```")
    A("")
    A("并发要点：")
    A("")
    A("- **单个 `Plugin` 不是并发安全的**（内部是一个 wasmtime `Store`，单线程语义）。多线程要么每线程一个 `Plugin`，要么用**插件池**（`CompiledPlugin` 出多个实例）。")
    A("- **`UserData` 跨线程共享必须 `Send + Sync`**（用 `Arc<Mutex<T>>` 之类）；否则在多线程里传非线程安全的 UserData 是未定义行为。")
    A("")
    # 九
    A("## 九、资源治理与安全")
    A("")
    A("Extism 的资源闸门本质是 wasmtime 的那几道，经 Manifest/PluginBuilder 暴露：")
    A("")
    A("| 闸门 | 配置 | 触发结果 |")
    A("|---|---|---|")
    A("| 内存上限 | `with_memory_max(pages)` | 增长失败 → `Error::Runtime(\"oom\")`，整调用 trap |")
    A("| 超时 | `with_timeout(Duration)` | 到点 → `Error::Timeout`，结果丢弃 |")
    A("| 燃料 | `PluginBuilder` 的 fuel 设置 | 耗尽 → trap |")
    A("| 网络/文件 | `allowed_hosts` / `allowed_paths` | 未授予 → 调用失败 |")
    A("")
    A("**一个必须知道的行为细节**（Extism 超时基于 wasmtime 的 epoch）：")
    A("")
    A("> 超时**不会打断正在执行的宿主函数**——因为 epoch 只能在「运行中的 wasm」上触发，而 Rust 宿主函数是同步跑在 wasm 之外的。所以一个 sleep 2s 的宿主函数配 500ms 超时，宿主调用会**照样跑完**，但控制权一回到 wasm，下一次 epoch 检查就立刻 trap、返回 `Error::Timeout`。**给插件的宿主函数自己也要有超时**，别指望 Extism 的 timeout 掐得住它。")
    A("")
    A("安全清单（与 wasmtime 一致）：宿主以最小权限进程运行；能力全走 Manifest 白名单；每次不可信调用配 timeout + memory + （必要时）fuel；**绝不把裸 DB 连接 / 任意文件句柄经宿主函数递进沙箱**。")
    A("")
    # 十
    A("## 十、Extism vs 裸 wasmtime：怎么选")
    A("")
    A("| 维度 | Extism | 裸 wasmtime |")
    A("|---|---|---|")
    A("| 上手速度 | 十几行加载+调用 | 要懂 Engine/Module/Store/Linker/内存 |")
    A("| ABI | 极简 bytes 进出，自动编解码 | 手搓线性内存 + alloc 约定 |")
    A("| 跨语言 | 10+ 宿主 SDK / 10+ PDK | 仅各自语言的嵌入 API |")
    A("| 能力策略 | 声明式 Manifest | 逐项 Config/StoreLimits/WASI |")
    A("| 组件模型 / WASIp2 | 不直接暴露 | 一等支持 |")
    A("| AOT / pooling / 自定义异步 | 框架封装、可调项有限 | 完全掌控 |")
    A("| 适合 | 通用插件系统、跨语言、快速落地 | 需要极致性能/组件/掌控的运行时 |")
    A("")
    A("**经验法则**：做「让用户/租户上传逻辑」的**插件平台** → Extism；做「自己就是个 WASM 运行时/边缘平台、要榨性能」→ 裸 wasmtime。两者不互斥——Extism 本身就是裸 wasmtime 的上层。")
    A("")
    # 十一
    A("## 十一、落地 CMX：对到 `cmx-runtime`")
    A("")
    A("本仓 `backend/cmx-container/cmx-runtime` 是基于 Extism 的插件运行时，`cmx-plugin` 管加载/签名/生命周期。把本文映射过去：")
    A("")
    A("| 本文概念 | 对应 CMX |")
    A("|---|---|")
    A("| 宿主 SDK 加载 `Manifest` → `Plugin` | `cmx-runtime` 的插件装载 |")
    A("| `host_fn!` 注入能力 | `cmx-plugin` 的 host functions（受控暴露平台能力） |")
    A("| Manifest 白名单（host/path/mem/timeout） | 插件的能力/资源策略 |")
    A("| `CompiledPlugin` + 池 | 无状态集群下的实例复用 |")
    A("| 「别把裸 SQL 递进沙箱」 | 与 `CLAUDE.md` 硬约束、FND 文档「不给不可信插件原始 SQL 连接」完全一致 |")
    A("")
    A("> 换言之：本仓对插件的所有安全底线，Extism 的能力模型天然支持——关键是**宿主函数只暴露领域命令，绝不暴露原始 SQL / 任意句柄**。")
    A("")
    # 十二
    A("## 十二、常见坑")
    A("")
    A("| 坑 | 症状 | 正解 |")
    A("|---|---|---|")
    A("| 插件里 `println!` | 无输出 | 用 PDK `log!` 宏 |")
    A("| 忘了 `crate-type=[\"cdylib\"]` | 产物不是可加载 wasm | Cargo.toml 加上 |")
    A("| 期望超时掐断宿主函数 | 宿主调用照跑完 | epoch 只掐 wasm；宿主函数自己做超时 |")
    A("| 多线程共享一个 `Plugin` | 数据竞争/报错 | 每线程一个，或 `CompiledPlugin` 池 |")
    A("| `UserData` 非 Send+Sync 跨线程 | UB | 用 `Arc<Mutex<T>>` |")
    A("| 插件发 HTTP 失败 | 报错拒绝 | Manifest `with_allowed_host` 放行 |")
    A("| 读不到文件 | WASI 无权限 | `with_allowed_path` + `with_wasi(true)` |")
    A("| 宿主/插件 host_fn 名字对不上 | 实例化报缺失导入 | 两侧同名，签名一致 |")
    A("| 内存超限 | `Error::Runtime(\"oom\")` | 调大 `with_memory_max` 或优化插件 |")
    A("")
    # 十三
    A("## 十三、多语言生态与版本")
    A("")
    A("Extism 的核心价值是**一次写插件、到处加载**。官方维护两套矩阵：")
    A("")
    A("- **宿主 SDK**（加载/调用插件）：Rust、Go、Python、Node/Bun、Ruby、C/C++、C#/.NET、Java、Zig、Haskell、PHP、Elixir、OCaml、browser 等。")
    A("- **PDK**（写插件）：Rust、Go、JS/TypeScript、C、Zig、AssemblyScript、Haskell、.NET 等。")
    A("")
    A("**版本**：宿主 `extism` 1.13.x、PDK `extism-pdk` 1.4.x（内部 wasmtime 27–30）。Extism 1.x 遵循语义化版本，API 比裸 wasmtime 稳定得多；跨语言 SDK 用统一的 Extism ABI，互操作有保证。")
    A("")
    A("```bash")
    A(r'''# CLI（本地跑/调试插件，不写宿主也能用）
extism call plugin.wasm my_func --input "hi" --config key=value
extism --help''')
    A("```")
    A("")
    A("---")
    A("")
    A("### 一句话收束")
    A("")
    A("> **Extism = 把 wasmtime 收敛成插件框架**：字节进字节出的极简 ABI、Manifest 白名单能力、`host_fn!` 注入、config/vars/HTTP、跨语言。做插件平台它让你十几行上手；要榨性能/要组件模型再下沉到裸 wasmtime。")
    A("")
    A("> 参考：extism.org 文档、docs.rs/extism 与 docs.rs/extism-pdk（版本以 2026 的 1.13 / 1.4 线为准）。")
    txt = "\n".join(D)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(txt)
    print("output:", OUT)
    print("bytes :", os.path.getsize(OUT))


if __name__ == "__main__":
    main()
