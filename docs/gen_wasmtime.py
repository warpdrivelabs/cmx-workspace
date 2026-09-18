#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成《Rust wasmtime crate 详细使用说明》—— 内嵌 base64 SVG。
Run: python3 gen_wasmtime.py   (基于 wasmtime 47.x / 2026-07 线)
"""
import base64
import html
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "20260917_Rust-wasmtime-使用说明.md")

SANS = "-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif"
MONO = "ui-monospace,SFMono-Regular,Menlo,monospace"
BG = "#fbfdff"
ENG = ("#4338ca", "#eef2ff")   # engine indigo
MOD = ("#7c3aed", "#f5f3ff")   # module violet
STO = ("#0d9488", "#f0fdfa")   # store teal
GST = ("#b45309", "#fffbeb")   # guest amber
DAN = ("#dc2626", "#fef2f2")   # danger red
GRY = ("#475569", "#f1f5f9")   # slate


def esc(s):
    return html.escape(str(s), quote=True)


def b64img(svg, alt):
    b = base64.b64encode(svg.encode("utf-8")).decode("ascii")
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


# ---------------------------------------------------------------- FIG 1 对象模型
def fig_objects():
    W, H = 940, 470
    b = []
    b.append(box(40, 60, 250, 92, "Engine", ["全局编译上下文", "Clone = Arc · Send + Sync", "跨线程共享，只建一次"], ENG))
    b.append(box(40, 200, 250, 70, "Config", ["编译/运行时开关", "fuel · epoch · async · cache"], GRY, "#fff"))
    b.append(box(360, 60, 250, 92, "Module", ["已编译机器码", "Send + Sync", "编译一次，多处复用 · 可 AOT"], MOD))
    b.append(box(360, 300, 250, 110, "Store<T>", ["运行态所有权 + 宿主数据 T", "单线程 · !Sync 并发", "每请求一个 · 内存只增不减"], STO))
    b.append(box(690, 300, 210, 110, "Instance", ["模块的一次实例化", "exports: Func/Memory/…", "生命周期系于 Store"], GST))
    b.append(box(690, 60, 210, 92, "Linker<T>", ["按名解析 imports", "定义宿主函数", "func_wrap / instantiate"], ENG))
    b.append(arrow(165, 200, 165, 152, "配置", ENG[0]))
    b.append(arrow(290, 106, 360, 106, "compile"))
    b.append(arrow(485, 152, 485, 300, "instantiate", MOD[0]))
    b.append(arrow(690, 130, 610, 300, "resolve imports", ENG[0]))
    b.append(arrow(610, 355, 690, 355, "produces", STO[0]))
    b.append(caption(W, 445, "绿/紫可跨线程共享（Engine·Module）；青色 Store 单线程、每请求新建 —— 这条边界是 wasmtime 用法的第一原则"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 2 生命周期
def fig_lifecycle():
    W, H = 940, 300
    b = []
    stages = [
        (40, ".wat / .wasm / .cwasm", ["源码或预编译产物"], GRY),
        (255, "编译 → Module", ["Cranelift 生成机器码", "贵 · 缓存 / AOT 摊销"], MOD),
        (490, "实例化 → Store", ["取内存/表 · 便宜", "pooling 可再提速"], STO),
        (725, "typed 调用", ["get_typed_func", ".call(&mut store, args)"], GST),
    ]
    for (x, t, lines, col) in stages:
        b.append(box(x, 90, 195, 86, t, lines, col))
    for x in (235, 470, 705):
        b.append(arrow(x, 133, x + 20, 133))
    b.append(f'<text x="352" y="70" text-anchor="middle" font-family="{SANS}" font-size="11" font-weight="700" fill="{MOD[0]}">编译一次</text>')
    b.append(f'<text x="700" y="70" text-anchor="middle" font-family="{SANS}" font-size="11" font-weight="700" fill="{STO[0]}">每请求一次 · Store drop 即回收</text>')
    b.append(caption(W, 250, "热路径只做「实例化 + 调用」；把编译挪到构建期（precompile_module → .cwasm），启动即 deserialize 载入"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 3 沙箱边界
def fig_sandbox():
    W, H = 940, 400
    b = []
    b.append(box(40, 110, 220, 150, "宿主 Host (Rust)", ["文件 · 网络 · 内存", "完整 OS 权限", "—— 沙箱外"], GRY))
    b.append(f'<rect x="360" y="70" width="330" height="250" rx="12" fill="{GST[1]}" stroke="{GST[0]}" stroke-width="2.4" stroke-dasharray="7 4"/>')
    b.append(f'<text x="525" y="98" text-anchor="middle" font-family="{MONO}" font-size="13" font-weight="700" fill="{GST[0]}">Guest 沙箱</text>')
    b.append(box(390, 120, 270, 66, "线性内存 linear memory", ["独立地址空间", "越界即 trap，碰不到宿主"], GST))
    b.append(box(390, 210, 270, 90, "客户机代码", ["无环境权限 no ambient authority", "不能自己开文件/socket", "只能调显式导入的函数"], GST))
    b.append(arrow(260, 150, 390, 150, "imports 宿主函数", ENG[0]))
    b.append(arrow(390, 250, 260, 250, "exports 客户机函数", STO[0]))
    b.append(box(720, 150, 180, 110, "能力 = 显式授予", ["WASI: 预打开目录/管道", "自定义 host func", "默认拒绝 (v47: socket 默认禁)"], DAN))
    b.append(caption(W, 360, "沙箱是「默认无权限」：客户机能做什么，完全由宿主注入了哪些 import 决定 —— 这是能力安全模型"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 4 资源闸门
def fig_gates():
    W, H = 940, 380
    cx, cy = 470, 185
    b = []
    b.append(f'<circle cx="{cx}" cy="{cy}" r="74" fill="{GST[1]}" stroke="{GST[0]}" stroke-width="2"/>')
    b.append(f'<text x="{cx}" y="{cy-6}" text-anchor="middle" font-family="{MONO}" font-size="14" font-weight="700" fill="{GST[0]}">运行中的</text>')
    b.append(f'<text x="{cx}" y="{cy+16}" text-anchor="middle" font-family="{MONO}" font-size="14" font-weight="700" fill="{GST[0]}">Guest</text>')
    b.append(box(40, 40, 250, 78, "Fuel 燃料", ["consume_fuel(true)", "set_fuel / get_fuel · 确定性计量"], STO))
    b.append(box(650, 40, 250, 78, "Epoch 时代", ["epoch_interruption(true)", "计时线程 increment_epoch · 快 2-3x"], ENG))
    b.append(box(40, 250, 250, 90, "StoreLimits", ["StoreLimitsBuilder → limiter()", "线性内存 / 实例 / 表 上限"], MOD))
    b.append(box(650, 250, 250, 90, "max_wasm_stack", ["Config::max_wasm_stack", "客户机调用栈上限，防深递归"], GRY))
    b.append(arrow(290, 90, 400, 150, ""))
    b.append(arrow(650, 90, 540, 150, ""))
    b.append(arrow(290, 290, 405, 220, ""))
    b.append(arrow(650, 290, 535, 220, ""))
    b.append(caption(W, 372, "四道闸门可组合。注意：fuel/epoch 只掐「运行中的 wasm」，客户机阻塞在宿主调用里时两者都不生效"))
    return svg(W, H, "".join(b))


# ---------------------------------------------------------------- FIG 5 core vs component
def fig_component():
    W, H = 940, 360
    b = []
    b.append(box(60, 70, 360, 220, "Core Module（核心模块）", [
        "类型只有 i32 / i64 / f32 / f64 / v128",
        "字符串 / 结构体 → 靠约定 + 线性内存偏移",
        "宿主手动 memory.data() 读写字节",
        "ABI 靠双方私下约定，易错、语言强绑定",
        "wasmtime::Module / Instance / Linker",
    ], GST))
    b.append(box(520, 70, 360, 220, "Component（组件模型）", [
        "WIT 接口类型：string/list/record/variant",
        "resource：带生命周期的句柄（如文件）",
        "bindgen! 从 .wit 生成强类型 Rust 绑定",
        "语言无关：Rust/Go/JS 组件可互相组合",
        "wasmtime::component::{Component, Linker}",
    ], MOD))
    b.append(arrow(420, 180, 520, 180, "上层封装", MOD[0]))
    b.append(caption(W, 330, "新项目优先组件模型 + WASIp2：类型安全、跨语言、可组合；核心模块适合极致轻量或已有 .wasm"))
    return svg(W, H, "".join(b))


def fig_guest():
    W, H = 940, 250
    b = []
    stages = [
        (18, "Rust 源码 + wit/", ["业务逻辑", "world 定义"], GST),
        (205, "wit-bindgen", ["生成 bindings", "Guest trait + 导入函数"], MOD),
        (392, "rustc 编译", ["核心模块", "wasm32-wasip1"], ENG),
        (579, "适配 → 组件", ["adapter 封装", "WASIp2 .wasm"], STO),
        (766, "宿主加载", ["Wasmtime", "bindgen! 调用"], GRY),
    ]
    for (x, t, lines, col) in stages:
        b.append(box(x, 78, 156, 82, t, lines, col))
    for x in (174, 361, 548, 735):
        b.append(arrow(x, 119, x + 31, 119))
    b.append(caption(W, 205, "cargo component build 把这条流水线一键跑完，产物是可被第六节宿主直接加载的组件"))
    return svg(W, H, "".join(b))



# ---------------------------------------------------------------- 正文
IMG1 = b64img(fig_objects(), "图1：wasmtime 对象模型与所有权")
IMG2 = b64img(fig_lifecycle(), "图2：编译→实例化→调用 生命周期")
IMG3 = b64img(fig_sandbox(), "图3：宿主↔客户机沙箱边界")
IMG4 = b64img(fig_gates(), "图4：资源治理四闸门")
IMG5 = b64img(fig_component(), "图5：核心模块 vs 组件模型")
IMG6 = b64img(fig_guest(), "图6：客户机侧组件构建流水线")


def main():
    D = []
    A = D.append
    A("# Rust `wasmtime` crate 详细使用说明")
    A("")
    A("> **定位**：`wasmtime` 是 Bytecode Alliance 出品、基于 Cranelift 的 WebAssembly 运行时，也是 Rust 生态里嵌入 WASM 的事实标准。后端把不可信 / 可插拔逻辑跑进 WASM 沙箱，正在成为插件系统、Serverless、边缘计算、多租户策略引擎的主流做法。")
    A("> **版本基线**：本文基于 **wasmtime 47.x（2026-07 发布线）**。wasmtime 与 `wasmtime-wasi` **同号发布**，约每月一个大版本，API 变动较快——凡易变处本文都标注，文末附「版本迁移对照」。")
    A("> **图**：6 张内嵌 base64 SVG，无外部依赖。")
    A("")
    A("---")
    A("")
    A("## 目录")
    A("")
    A("1. [为什么是后端 WASM，为什么是 wasmtime](#一为什么是后端-wasm为什么是-wasmtime)")
    A("2. [核心对象模型](#二核心对象模型engine--module--store--linker)")
    A("3. [最小可运行例子](#三最小可运行例子)")
    A("4. [宿主 ↔ 客户机互操作](#四宿主--客户机互操作host-function--线性内存)")
    A("5. [WASI：让沙箱能读文件、走管道](#五wasi让沙箱能读文件走标准流)")
    A("6. [组件模型与 `bindgen!`](#六组件模型与-bindgen)")
    A("7. [客户机侧：用 `cargo component` 编成组件](#七客户机侧用-cargo-component-把-rust-编成-wasip2-组件)")
    A("8. [资源治理与安全沙箱](#八资源治理与安全沙箱)")
    A("9. [异步执行](#九异步执行)")
    A("10. [性能：AOT 预编译 · 缓存 · Pooling 分配器](#十性能aot-预编译--缓存--pooling-分配器)")
    A("11. [生产落地模式](#十一生产落地模式)")
    A("12. [常见坑](#十二常见坑)")
    A("13. [版本迁移对照 & Cargo features](#十三版本迁移对照--cargo-features)")
    A("")
    A("---")
    A("")
    # 一
    A("## 一、为什么是后端 WASM，为什么是 wasmtime")
    A("")
    A("把一段逻辑编译成 `.wasm`，丢进宿主进程里跑，你就得到了一个**默认无权限、可计量、可超时、可跨语言**的执行单元。典型落地：")
    A("")
    A("| 场景 | 说明 | 代表 |")
    A("|---|---|---|")
    A("| 插件系统 | 第三方 / 租户上传逻辑，宿主给能力，跑在沙箱里 | 本仓 `cmx-container/cmx-runtime`（Extism，底层即 wasmtime）、Envoy、Zellij |")
    A("| Serverless / 边缘 | 冷启动微秒级、单机万级并发实例 | Fastly Compute、Fermyon Spin、Shopify Functions |")
    A("| 策略 / 规则引擎 | 把可版本化的业务差异编译成 wasm，热更不重启 | 各类 policy-as-code |")
    A("| 不可信代码 | 跑用户提交的算法 / UDF，掐死资源 | 数据库 UDF、CI 沙箱 |")
    A("")
    A("**为什么选 wasmtime**：Cranelift 优化后端（运行时或 AOT 都行）、成熟的**能力安全沙箱**、`fuel`/`epoch` 两套资源治理、一等的**组件模型 + WASIp2** 支持、`pooling` 分配器把实例化压到微秒级。它就是上面多数框架的底层引擎。")
    A("")
    A("> 提示：如果你要的是「开箱即用的插件加载 + 宿主函数 SDK」，可以用 Extism（封装 wasmtime）；如果你要**完全掌控**编译、资源、组件类型、异步调度，就直接用 `wasmtime`。本文讲后者。")
    A("")
    # 二
    A("## 二、核心对象模型（Engine / Module / Store / Linker）")
    A("")
    A("理解 wasmtime，先理解 5 个类型和它们之间**谁能共享、谁必须独占**：")
    A("")
    A(IMG1)
    A("")
    A("| 类型 | 是什么 | 线程 / 复用 | 成本 |")
    A("|---|---|---|---|")
    A("| `Engine` | 全局编译上下文（持有 `Config`） | `Clone`=`Arc`，`Send+Sync`，**全进程一个** | 建一次 |")
    A("| `Module` | 编译后的机器码 | `Send+Sync`，**编译一次多处复用**，可序列化 | 编译**贵** |")
    A("| `Linker<T>` | 按名字解析 imports、定义宿主函数 | 复用于多次实例化 | 便宜 |")
    A("| `Store<T>` | 一批实例的**全部运行态** + 你的宿主数据 `T` | **单线程、!Sync**，**每请求一个** | 便宜，但内存**只增不减** |")
    A("| `Instance` | `Module` 的一次实例化 | 生命周期系于所属 `Store` | 便宜（pooling 更快） |")
    A("")
    A("**两条铁律**，记住就不会用错：")
    A("")
    A("1. **`Engine` / `Module` 编译一次、跨线程共享；`Store` 每请求新建、绝不跨线程。** `Store` 内存只增不减（无法单独释放某个 instance），所以它必须短命——请求级、任务级。")
    A("2. **所有运行态操作都要借道 `&mut store`**：调函数、读内存、加燃料……`Store` 是那个「可变世界」的句柄。")
    A("")
    A(IMG2)
    A("")
    # 三
    A("## 三、最小可运行例子")
    A("")
    A("`Cargo.toml`：")
    A("")
    A("```toml")
    A(r'''[dependencies]
wasmtime = "47"          # 与 wasmtime-wasi 同号发布
anyhow = "1"''')
    A("```")
    A("")
    A("调用一个客户机导出的 `add(i32,i32)->i32`：")
    A("")
    A("```rust")
    A(r'''use wasmtime::*;

fn main() -> anyhow::Result<()> {
    // 1) Engine：全进程一个，可跨线程 clone
    let engine = Engine::default();

    // 2) Module：编译（这里用内联 WAT；生产用 Module::from_file / deserialize）
    let module = Module::new(&engine, r#"
        (module
          (func (export "add") (param i32 i32) (result i32)
            local.get 0
            local.get 1
            i32.add))
    "#)?;

    // 3) Store：每请求一个，携带宿主数据（这里是 ()）
    let mut store = Store::new(&engine, ());

    // 4) 实例化（无 imports 时可直接 Instance::new；有 imports 用 Linker）
    let instance = Instance::new(&mut store, &module, &[])?;

    // 5) 取强类型函数并调用——注意所有调用都要 &mut store
    let add = instance.get_typed_func::<(i32, i32), i32>(&mut store, "add")?;
    let result = add.call(&mut store, (2, 3))?;

    println!("2 + 3 = {result}");
    Ok(())
}''')
    A("```")
    A("")
    A("`get_typed_func::<Params, Results>` 在取函数时就核对签名，之后 `.call` 零反射、直达机器码。若要动态签名，用 `get_func` + `Func::call(&mut store, &[Val], &mut [Val])`。")
    A("")
    # 四
    A("## 四、宿主 ↔ 客户机互操作（host function + 线性内存）")
    A("")
    A("沙箱的本质是：**客户机默认什么也做不了，能做什么由宿主注入的 import 决定**。")
    A("")
    A(IMG3)
    A("")
    A("### 4.1 用 Linker 注入宿主函数")
    A("")
    A("```rust")
    A(r'''use wasmtime::*;

struct Host { logs: Vec<String> }   // 放进 Store 的宿主数据 T

fn main() -> anyhow::Result<()> {
    let engine = Engine::default();
    let mut linker = Linker::new(&engine);

    // 客户机侧： (import "host" "log" (func (param i32 i32)))  —— ptr,len 指向其线性内存
    linker.func_wrap("host", "log",
        |mut caller: Caller<'_, Host>, ptr: i32, len: i32| -> anyhow::Result<()> {
            // 从 Caller 拿到客户机导出的 memory
            let mem = caller.get_export("memory")
                .and_then(Extern::into_memory)
                .ok_or_else(|| Error::msg("guest 未导出 memory"))?;
            let data = mem.data(&caller);           // &[u8] 只读视图
            let (start, end) = (ptr as usize, (ptr + len) as usize);
            let bytes = data.get(start..end).ok_or_else(|| Error::msg("越界"))?;
            let s = std::str::from_utf8(bytes)?.to_owned();
            caller.data_mut().logs.push(s);         // 写回宿主数据
            Ok(())
        })?;

    let module = Module::from_file(&engine, "guest.wasm")?;
    let mut store = Store::new(&engine, Host { logs: vec![] });

    // Linker 解析 imports 并实例化
    let instance = linker.instantiate(&mut store, &module)?;
    let run = instance.get_typed_func::<(), ()>(&mut store, "run")?;
    run.call(&mut store, ())?;

    println!("客户机打了 {} 条日志", store.data().logs.len());
    Ok(())
}''')
    A("```")
    A("")
    A("要点：")
    A("")
    A("- **`Caller<'_, T>`** 是宿主函数里访问「调用方 Store」的句柄：`caller.data()/data_mut()` 取宿主数据，`caller.get_export(\"memory\")` 拿客户机内存。")
    A("- **线性内存是一整块 `&[u8]`**：客户机传给你的永远是「偏移 + 长度」，你自己解释。写用 `mem.data_mut(&mut caller)`，或 `mem.write(&mut store, offset, bytes)`。")
    A("- 宿主函数返回 `Err` 会让客户机**陷阱（trap）**，调用栈整个中止——这是把错误传回宿主的正规通道。")
    A("- 用 `func_wrap` 处理静态签名（自动类型转换）；动态签名用 `Func::new` + `&[Val]`。")
    A("")
    A("### 4.2 谁分配内存？")
    A("")
    A("客户机的线性内存由**客户机自己**增长（`memory.grow`）。宿主要把数据「递进去」，惯例是：客户机导出一个 `alloc(len)->ptr`，宿主调用它拿到偏移，再 `mem.write` 填字节，最后把 `ptr,len` 传给业务函数。组件模型（下文）会把这套繁琐 ABI **自动生成**掉。")
    A("")
    # 五
    A("## 五、WASI：让沙箱能读文件、走标准流")
    A("")
    A("裸沙箱连 `println!` 都不行（没有 stdout）。**WASI**（WebAssembly System Interface）是一组标准 import，按**能力**把受控的系统访问交给客户机：预打开某个目录、接一根 stdin/stdout、给几个环境变量——**给什么才有什么**。")
    A("")
    A("> ⚠️ **v47 安全默认值**：`wasmtime-wasi` 现在**默认禁止**客户机创建 TCP/UDP socket，需显式放开。这是「默认拒绝」能力模型的体现。")
    A("")
    A("WASI 有两代，对应两种模块形态：")
    A("")
    A("| | Preview 1 (WASIp1) | Preview 2 (WASIp2) |")
    A("|---|---|---|")
    A("| 模块形态 | 核心模块（`.wasm`） | **组件**（component） |")
    A("| wasmtime 模块路径 | `wasmtime_wasi::preview1` | `wasmtime_wasi::p2` |")
    A("| 适用 | 已有 `wasm32-wasip1` 产物 | **新项目首选** |")
    A("")
    A("### 5.1 WASIp2（组件，推荐）—— 当前 API")
    A("")
    A("> 这里是最容易踩版本坑的地方。**v47 关键变化**：旧的 `IoView` trait 已删除；`WasiView` 现在只有一个方法 `ctx()`，返回把 `WasiCtx` 与 `ResourceTable` 打包在一起的 **`WasiCtxView`**。")
    A("")
    A("```rust")
    A(r'''use wasmtime::{Engine, Store, Config, Result};
use wasmtime::component::{Component, Linker, ResourceTable};
use wasmtime_wasi::{WasiCtx, WasiCtxBuilder, WasiCtxView, WasiView};

// 1) 放进 Store 的宿主数据：至少含一个 ResourceTable + 一个 WasiCtx
struct Ctx {
    table: ResourceTable,
    wasi: WasiCtx,
}

// 2) 实现 WasiView（v47：只需 ctx()，返回 WasiCtxView）
impl WasiView for Ctx {
    fn ctx(&mut self) -> WasiCtxView<'_> {
        WasiCtxView { ctx: &mut self.wasi, table: &mut self.table }
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    let mut config = Config::new();
    config.async_support(true);              // p2 的 add_to_linker_async 走异步
    let engine = Engine::new(&config)?;

    // 3) 把 WASI 宿主实现挂到「组件 Linker」上（注意在 p2 模块下）
    let mut linker = Linker::<Ctx>::new(&engine);
    wasmtime_wasi::p2::add_to_linker_async(&mut linker)?;

    // 4) 按能力构造 WasiCtx：这里只继承 stdio，别的一律不给
    let wasi = WasiCtxBuilder::new()
        .inherit_stdio()
        // .preopened_dir("/data", "/", DirPerms::READ, FilePerms::READ)?  // 需要才给
        // .inherit_network()                                              // socket 默认禁
        .build();
    let mut store = Store::new(&engine, Ctx { table: ResourceTable::new(), wasi });

    let component = Component::from_file(&engine, "app.wasm")?;  // 已是组件产物
    let instance = linker.instantiate_async(&mut store, &component).await?;

    // …按组件导出的世界调用（见第六节 bindgen!）…
    let _ = instance;
    Ok(())
}''')
    A("```")
    A("")
    A("### 5.2 WASIp1（核心模块，兼容老产物）")
    A("")
    A("```rust")
    A(r'''use wasmtime::{Engine, Store, Module, Linker, Result};
use wasmtime_wasi::WasiCtxBuilder;
use wasmtime_wasi::preview1::{self, WasiP1Ctx};

fn main() -> Result<()> {
    let engine = Engine::default();
    let mut linker: Linker<WasiP1Ctx> = Linker::new(&engine);

    // 闭包把 &mut T 映射到 &mut WasiP1Ctx（此处 T == WasiP1Ctx）
    preview1::add_to_linker_sync(&mut linker, |t| t)?;

    let wasi = WasiCtxBuilder::new()
        .inherit_stdio()
        .inherit_args()
        .build_p1();                         // 注意 p1 用 build_p1()
    let mut store = Store::new(&engine, wasi);

    let module = Module::from_file(&engine, "program.wasm")?;   // wasm32-wasip1 产物
    linker.module(&mut store, "", &module)?;
    linker.get_default(&mut store, "")?
        .typed::<(), ()>(&store)?
        .call(&mut store, ())?;              // 相当于运行其 _start
    Ok(())
}''')
    A("```")
    A("")
    A("> 还有更新的 **WASIp3**（`wasmtime_wasi::p3::add_to_linker`，异步优先，需 `config.wasm_component_model_async(true)`），面向原生异步的组件；生产可先稳在 p2。")
    A("")
    # 六
    A("## 六、组件模型与 `bindgen!`")
    A("")
    A("核心模块只有 4 种数字类型，字符串/结构全靠手搓 ABI。**组件模型**用 **WIT**（Wasm Interface Types）描述接口，`bindgen!` 宏据此**生成强类型 Rust 绑定**，跨语言可组合。")
    A("")
    A(IMG5)
    A("")
    A("一个 WIT（`wit/calculator.wit`）：")
    A("")
    A("```wit")
    A(r'''package example:calc;

world calculator {
  // 客户机要实现的导出
  export add: func(a: s32, b: s32) -> s32;
  // 宿主提供给客户机的导入
  import log: func(msg: string);
}''')
    A("```")
    A("")
    A("宿主侧用 `bindgen!` 生成绑定并调用：")
    A("")
    A("```rust")
    A(r'''use wasmtime::component::bindgen;

// 编译期从 WIT 生成 `Calculator` 及其 imports/exports 的强类型接口
bindgen!({
    world: "calculator",
    path: "wit/calculator.wit",
    // async: true,   // 需要异步导入时开
});

struct Host { /* 你的状态 */ }

// 实现 WIT 里声明的 import `log`
impl CalculatorImports for Host {
    fn log(&mut self, msg: String) {
        println!("[guest] {msg}");
    }
}

fn run(engine: &wasmtime::Engine, comp: &wasmtime::component::Component)
    -> wasmtime::Result<i32>
{
    let mut store = wasmtime::Store::new(engine, Host {});
    let mut linker = wasmtime::component::Linker::new(engine);
    Calculator::add_to_linker(&mut linker, |h: &mut Host| h)?;   // 挂宿主实现

    let bindings = Calculator::instantiate(&mut store, comp, &linker)?;
    // 直接以原生类型调用导出：字符串/结构体全自动 marshal
    let sum = bindings.call_add(&mut store, 2, 3)?;
    Ok(sum)
}''')
    A("```")
    A("")
    A("`string` 参数你**直接传 `String`**，编解码、内存分配全由生成代码处理——这正是组件模型相对核心模块最大的工程价值。`resource` 类型还能表达「带生命周期的句柄」（文件、连接），由 `ResourceTable` 托管。")
    A("")
    # 七 客户机侧
    A("## 七、客户机侧：用 `cargo component` 把 Rust 编成 WASIp2 组件")
    A("")
    A("前六节都站在**宿主**视角。这一节把镜头转到**客户机**：怎么用 Rust 写出、并编译出一个能被第六节宿主加载的 WASIp2 组件。以实现第六节那个 `calculator` world 为例，正好首尾闭环。")
    A("")
    A(IMG6)
    A("")
    A("### 7.1 两条路线")
    A("")
    A("| 路线 | bindings 从哪来 | 适合 |")
    A("|---|---|---|")
    A("| **`cargo component`** | 生成进 `src/bindings.rs`，按 `Cargo.toml` 解析的依赖对齐 | 标准工程，推荐 |")
    A("| **`wit-bindgen` 宏** | 源码里 `generate!` 宏内联展开 | 想少一层工具 / 单文件 demo |")
    A("")
    A("先讲用户点名的 `cargo component`。")
    A("")
    A("### 7.2 装工具、起项目")
    A("")
    A("```bash")
    A(r'''cargo install cargo-component wasm-tools
cargo component new --lib calculator   # --lib = reactor 组件（库，无 _start）
cd calculator''')
    A("```")
    A("")
    A("`--lib` 造的是 **reactor（库）组件**：只导出接口、没有 `main`/`_start`，供宿主按需调用——正是插件想要的形态。省掉 `--lib` 则是 **command 组件**（有入口，像个可执行程序）。")
    A("")
    A("### 7.3 放 WIT")
    A("")
    A("把第六节那份 WIT 存到 `wit/world.wit`：")
    A("")
    A("```wit")
    A(r'''package example:calc;

world calculator {
  export add: func(a: s32, b: s32) -> s32;   // 客户机实现
  import log: func(msg: string);             // 宿主提供
}''')
    A("```")
    A("")
    A("`cargo component new` 会在 `Cargo.toml` 里生成大致这样的元数据（一般不用手写）：")
    A("")
    A("```toml")
    A(r'''[package.metadata.component]
package = "example:calc"

[package.metadata.component.target]
path = "wit"
world = "calculator"''')
    A("```")
    A("")
    A("### 7.4 写实现（`src/lib.rs`）")
    A("")
    A("```rust")
    A(r'''#[allow(warnings)]
mod bindings;                 // cargo component 生成的绑定（src/bindings.rs）

use bindings::Guest;          // add 是 world 级导出 → 顶层 Guest trait

struct Component;

impl Guest for Component {
    fn add(a: i32, b: i32) -> i32 {   // WIT 的 s32 → Rust i32
        // 调用宿主提供的 import：world 级导入 → bindings 里的自由函数
        bindings::log(&format!("computing {a} + {b}"));
        a + b
    }
}

// 把实现接到组件导出上（近期 cargo component / wit-bindgen 写法）
bindings::export!(Component with_types_in bindings);''')
    A("```")
    A("")
    A("**最容易踩的坑 —— `Guest` trait 落在哪个模块**：")
    A("")
    A("- 函数**直接从 world 导出**（本例的 `add`）→ 顶层 `bindings::Guest`。")
    A("- 若导出的是一个**具名 interface**（如 `export calc: interface { add: ... }`）→ trait 落到 `bindings::exports::example::calc::calc::Guest`，`export!` 的目标路径也随之变深。**报错「找不到 Guest」十有八九是这里。**")
    A("- world 级的 `import log` 则生成为可直接调用的自由函数 `bindings::log(&str)`。")
    A("")
    A("### 7.5 编译 + 验证")
    A("")
    A("```bash")
    A(r'''cargo component build --release
# 产物是「真·组件」而非核心模块（当前经 wasm32-wasip1 适配为 p2）
ls target/wasm32-wasip1/release/calculator.wasm

# 用 wasm-tools 确认它确实是组件、接口对得上
wasm-tools component wit target/wasm32-wasip1/release/calculator.wasm
# 应打印：world calculator { export add: ...; import log: ...; }''')
    A("```")
    A("")
    A("> `wasm-tools component wit <file>` 能打印出 WIT，就证明产物是合法组件（而非核心模块）—— 这是客户机侧最实用的一条自检。")
    A("")
    A("### 7.6 闭环：交给第六节的宿主跑")
    A("")
    A("把 `calculator.wasm` 喂给第六节那段 `bindgen!` + `Calculator::instantiate` 的宿主代码：宿主实现 `CalculatorImports::log`，调 `bindings.call_add(&mut store, 2, 3)?` 得 `5`，同时客户机里的 `log` 会回调进宿主打印。宿主 ↔ 客户机两侧就此对上，一个完整的组件调用闭环成立。")
    A("")
    A("### 7.7 wit-bindgen 宏路线（对照）")
    A("")
    A("不想用 cargo component、想单文件搞定，可直接在库里内联生成：")
    A("")
    A("```rust")
    A(r'''wit_bindgen::generate!({
    world: "calculator",        // 读相邻 wit/ 目录；也可用 inline: r#"...WIT..."#
});

struct Component;

impl Guest for Component {
    fn add(a: i32, b: i32) -> i32 {
        log(&format!("computing {a} + {b}"));   // 宏在当前作用域直接生成 log()
        a + b
    }
}

export!(Component);''')
    A("```")
    A("")
    A("`Cargo.toml` 里 `crate-type = [\"cdylib\"]`、依赖 `wit-bindgen`，再 `cargo build --target wasm32-wasip2 --release` 即可。两条路线产出的组件，宿主侧用法完全一样。")
    A("")
    A("> **版本提醒**：`cargo component` / `wit-bindgen` 目前仍是 `0.x`，`generate!` 的配置键、`export!` 写法、cargo component 的生成模板都会随小版本调整。`export!(T with_types_in bindings)` 是近期写法；很老的模板可能自动接线或用宏内 `exports:` 键。以 `wit_bindgen::generate!` 的 docs.rs 与 `cargo component new` 实际生成的模板为准。")
    A("")
    # 八
    A("## 八、资源治理与安全沙箱")
    A("")
    A("跑不可信代码，必须能**掐住 CPU、内存、栈、时间**。wasmtime 给了四道可组合的闸门：")
    A("")
    A(IMG4)
    A("")
    A("### 7.1 Fuel —— 确定性计量")
    A("")
    A("每条 wasm 指令消耗「燃料」，耗尽即 trap。**确定性**：同样输入必然在同一点停下，适合可复现、可计费场景。")
    A("")
    A("```rust")
    A(r'''let mut config = Config::new();
config.consume_fuel(true);
let engine = Engine::new(&config)?;

let mut store = Store::new(&engine, ());
store.set_fuel(5_000_000)?;                 // 注入预算

match func.call(&mut store, ()) {
    Ok(_) => {}
    Err(e) if e.downcast_ref::<Trap>() == Some(&Trap::OutOfFuel) => {
        eprintln!("超算力预算，已安全中止");
    }
    Err(e) => return Err(e),
}
let used = 5_000_000 - store.get_fuel()?;    // 实际消耗，可用于计费''')
    A("```")
    A("")
    A("### 7.2 Epoch —— 计时器抢占（快，但非确定）")
    A("")
    A("客户机只检查一个全局计数器，宿主用**独立线程 / 定时器**递增它，到点 trap。比 fuel **快 2–3 倍**（几乎零开销），代价是非确定：同样输入可能在不同位置被打断。做**墙钟超时**首选。")
    A("")
    A("```rust")
    A(r'''let mut config = Config::new();
config.epoch_interruption(true);
let engine = Engine::new(&config)?;

let mut store = Store::new(&engine, ());
store.set_epoch_deadline(1);   // 必须先设，否则一运行就立刻 trap
store.epoch_deadline_trap();   // 到期即 trap（也可 async 让出）

// 后台计时线程：每 100ms 敲一下，1 tick ≈ 100ms 预算
let engine2 = engine.clone();
std::thread::spawn(move || loop {
    std::thread::sleep(std::time::Duration::from_millis(100));
    engine2.increment_epoch();
});
// 长时间运行的 wasm 到点会以 Trap::Interrupt 中止''')
    A("```")
    A("")
    A("> **共同盲区**：fuel 和 epoch 都**只管运行中的 wasm**。若客户机阻塞在一次宿主调用里（比如宿主函数在等 IO），两者都叫不醒它——超时得由宿主自己在那次调用上做。另：epoch 与 Winch 基线编译器不兼容。")
    A("")
    A("### 7.3 内存 / 实例 / 栈上限")
    A("")
    A("```rust")
    A(r'''use wasmtime::{StoreLimits, StoreLimitsBuilder};

struct Host { limits: StoreLimits }

let mut config = Config::new();
config.max_wasm_stack(512 * 1024);          // 客户机调用栈上限，防深递归打爆

let limits = StoreLimitsBuilder::new()
    .memory_size(64 << 20)                  // 单 Store 线性内存 ≤ 64 MiB
    .instances(1)
    .tables(1)
    .build();
let mut store = Store::new(&engine, Host { limits });
store.limiter(|h| &mut h.limits);           // 把 limiter 接到宿主数据''')
    A("```")
    A("")
    A("需要**动态**上限（按租户配额实时判断）时，自己实现 `ResourceLimiter` trait，在 `memory_growing`/`table_growing` 回调里裁决。")
    A("")
    A("### 7.4 沙箱纪律（安全清单）")
    A("")
    A("- **以非 root、非 superuser 的最小权限进程**跑宿主；wasm 沙箱防的是客户机，不是宿主自己的漏洞。")
    A("- **能力最小化**：WASI 只 `preopen` 必要目录，socket 默认已禁；宿主函数只暴露必需的。")
    A("- **给每个不可信调用配 fuel 或 epoch + 内存上限 + 栈上限**，三件套齐全。")
    A("- **别把裸 SQL / 原始连接 / 任意文件句柄递进沙箱**——那等于把沙箱门拆了（本仓 `cmx-container` 的硬约束正是此意）。")
    A("")
    # 八
    A("## 九、异步执行")
    A("")
    A("要在一个 async 运行时里**并发跑成百上千个客户机**、或让宿主导入函数 `.await`，开 `async_support`：")
    A("")
    A("```rust")
    A(r'''let mut config = Config::new();
config.async_support(true);
let engine = Engine::new(&config)?;

// 宿主异步导入
let mut linker = Linker::new(&engine);
linker.func_wrap_async("host", "fetch",
    |mut caller: Caller<'_, Host>, (url_ptr, url_len): (i32, i32)| {
        Box::new(async move {
            // …真正的异步 IO…
            Ok(())
        })
    })?;

// 调用要 .await
let instance = linker.instantiate_async(&mut store, &module).await?;
let run = instance.get_typed_func::<(), ()>(&mut store, "run")?;
run.call_async(&mut store, ()).await?;''')
    A("```")
    A("")
    A("**关键**：wasm 本身是同步 CPU 流，不会主动让出。要**协作式抢占**（不让一个死循环客户机饿死 executor），把 epoch 或 fuel 接成「让出」而非「trap」：")
    A("")
    A("- `store.epoch_deadline_async_yield_and_update(delta)`：到期让出 future（返回 `Pending` 并自唤醒），恢复时续期——多个 CPU 密集客户机就能在一个 executor 上时间片轮转。")
    A("- `store.fuel_async_yield_interval(Some(n))`：每消耗 n 燃料让出一次。")
    A("")
    A("> 每个 async 调用会占一个执行栈；高并发下配合 pooling 分配器的 `total_stacks` 一起调。")
    A("")
    # 九
    A("## 十、性能：AOT 预编译 · 缓存 · Pooling 分配器")
    A("")
    A("三板斧，把「编译贵、实例化频繁」这对矛盾拆开。")
    A("")
    A("### 9.1 AOT：把编译挪到构建期")
    A("")
    A("运行时 `Module::new` 每次都重编译。生产应当**构建期编译成 `.cwasm`，上线只加载**：")
    A("")
    A("```rust")
    A(r'''// —— 构建期（离线，一次）——
let engine = Engine::default();
let cwasm: Vec<u8> = engine.precompile_module(&wasm_bytes)?;   // 或 CLI: wasmtime compile
std::fs::write("app.cwasm", &cwasm)?;

// —— 服务期（每进程启动）——
let engine = Engine::default();
// SAFETY: 字节必须来自「可信、且与本 wasmtime 版本兼容」的构建产物；
//         对任意/不可信字节做 deserialize 是未定义行为。
let module = unsafe { Module::deserialize_file(&engine, "app.cwasm")? };''')
    A("```")
    A("")
    A("> `deserialize*` 是 `unsafe`：它**信任**字节是本引擎产的、没被篡改。`.cwasm` 只跟兼容的 wasmtime 版本 + 目标架构匹配；跨平台预编译要开 `all-arch` 特性并设 `Config::target`。")
    A("")
    A("### 9.2 编译缓存（v47 新 API）")
    A("")
    A("> **v47 变化**：旧 `config.cache_config_load_default()` 已废弃，改用 `Cache` 类型 + `config.cache(...)`（需 `cache` 特性）。")
    A("")
    A("```rust")
    A(r'''use wasmtime::{Config, Cache, CacheConfig};

let mut config = Config::new();

// 等价于旧 cache_config_load_default()：加载系统默认磁盘缓存配置
let cache = Cache::from_file(None)?;             // None=系统默认路径；Some(path)=指定文件
config.cache(Some(cache));
// 或程序化默认：Cache::new(CacheConfig::new())?
let engine = Engine::new(&config)?;''')
    A("```")
    A("")
    A("缓存命中时，相同 wasm 不再重编译——对「同一模块反复冷启动」的开发/CI 很有用；生产更推荐上面的 AOT。")
    A("")
    A("### 9.3 Pooling 分配器：把实例化压到微秒")
    A("")
    A("默认 `OnDemand` 每次实例化都向 OS 要内存/表。**Pooling** 预先开好一大池资源，实例化只是「从池里取一格」，配合**写时复制（COW）** 初始化线性内存，实例化成本可降一到两个数量级——Serverless / 高并发多租户的标配。")
    A("")
    A("```rust")
    A(r'''use wasmtime::{Config, Engine, InstanceAllocationStrategy, PoolingAllocationConfig};

let mut pool = PoolingAllocationConfig::new();
pool.total_core_instances(1000);    // 整池最大并发核心实例数
pool.total_memories(1000);          // 并发线性内存槽数（≈最大并发实例）
pool.max_memory_size(64 << 20);     // 每槽上限 64 MiB —— 决定每槽预留的虚拟地址空间
pool.total_tables(1000);            // 并发表数
pool.table_elements(5000);          // 单表元素上限
// pool.total_stacks(1000);         // 异步执行栈数（需 async 特性）
// 另有 *_per_component / *_per_module 系列：限制「单次实例化」占用，而非整池

let mut config = Config::new();
config.allocation_strategy(InstanceAllocationStrategy::Pooling(pool));
let engine = Engine::new(&config)?;''')
    A("```")
    A("")
    A("> Pooling 会**预留一大片进程地址空间**（用来省掉内存边界检查），换来的是极快、可预测的实例化。它**不影响编译产物**，`.cwasm` 用不用 pooling 都能加载。需 `pooling-allocator` 特性（默认开）。")
    A("")
    # 十
    A("## 十一、生产落地模式")
    A("")
    A("把前面的原则拼成一套可抄的骨架（多租户插件服务）：")
    A("")
    A("```rust")
    A(r'''// 进程级：一次建好，长期持有
struct Platform {
    engine: Engine,                    // 全局唯一
    modules: HashMap<String, Module>,  // 插件名 -> 已编译模块（可来自 .cwasm）
    linker: Linker<Tenant>,            // 宿主函数一次定义，反复用
}

// 请求级：每次调用新建 Store，用完即弃
fn invoke(p: &Platform, tenant: Tenant, plugin: &str, input: &[u8]) -> anyhow::Result<Vec<u8>> {
    let module = p.modules.get(plugin).ok_or_else(|| anyhow::anyhow!("no plugin"))?;

    let mut store = Store::new(&p.engine, tenant);   // ← 每请求一个
    store.set_fuel(10_000_000)?;                     // ← 掐 CPU
    store.set_epoch_deadline(50);                    // ← 掐墙钟（配合计时线程）
    store.limiter(|t| &mut t.limits);                // ← 掐内存

    let instance = p.linker.instantiate(&mut store, module)?;
    // …写 input 到客户机内存 → 调导出函数 → 读结果…
    let _ = input;
    Ok(vec![])
}   // store 在此 drop，本次实例的全部资源回收''')
    A("```")
    A("")
    A("对照本仓的落地约束（`CLAUDE.md` §八「集群无状态」、`cmx-container` 插件平台）：")
    A("")
    A("- **`Engine` / `Module` / `Linker` 是只读共享的**——符合「禁用 Mutex 缓存业务数据，但连接池 / 只读配置除外」：它们正是只读配置类，可长持有。")
    A("- **`Store` 每请求新建、不跨线程、用完即弃**——天然契合无状态进程；状态外置（Redis / 库），别把业务态攒在长命 Store 里。")
    A("- **别给不可信插件原始 SQL / 任意句柄**——`cmx-container` 硬约束与 wasmtime 能力模型是同一条底线：能力显式授予，默认拒绝。")
    A("")
    # 十一
    A("## 十二、常见坑")
    A("")
    A("| 坑 | 症状 | 正解 |")
    A("|---|---|---|")
    A("| 复用长命 `Store` 攒实例 | 内存持续上涨不回落 | Store 内存只增不减，**每请求新建**、用完 drop |")
    A("| 跨线程共享 `Store` | 编译不过 / 数据竞争 | Store `!Sync`；跨线程共享的是 `Engine`/`Module` |")
    A("| 每次请求都 `Module::new` | CPU 全耗在编译 | 编译一次缓存 `Module`，或 AOT `.cwasm` |")
    A("| 开了 epoch 没设 deadline | 一运行就 `Trap::Interrupt` | 运行前必须 `set_epoch_deadline(n)` |")
    A("| 指望 fuel/epoch 打断宿主阻塞 | 卡在宿主 IO 里超时不生效 | 两者只管运行中的 wasm；宿主调用自己做超时 |")
    A("| 用了旧 `IoView` / `preview2::` 路径 | v47 编译报找不到符号 | 用 `WasiCtxView` + `wasmtime_wasi::p2::` |")
    A("| `deserialize` 喂不可信字节 | UB / 崩溃 | 只 deserialize 自己可信构建的 `.cwasm` |")
    A("| 忘了给 stdout 就 `println!` | 客户机无输出 / 报错 | `WasiCtxBuilder::inherit_stdio()` |")
    A("| Winch + epoch | 配置报错 | epoch 与 Winch 不兼容，用 Cranelift |")
    A("")
    # 十二
    A("## 十三、版本迁移对照 & Cargo features")
    A("")
    A("### 从旧版本迁移（→ v47）")
    A("")
    A("| 旧 API | v47 现行 |")
    A("|---|---|")
    A("| `config.cache_config_load_default()` | `config.cache(Some(Cache::from_file(None)?))` |")
    A("| `store.add_fuel(n)` / `fuel_consumed()` | `store.set_fuel(n)?` / `store.get_fuel()?` |")
    A("| `IoView` trait + `table()` 方法 | 已删除；`WasiView::ctx() -> WasiCtxView{ctx, table}` |")
    A("| `wasmtime_wasi::preview2::add_to_linker_*` | `wasmtime_wasi::p2::add_to_linker_*` |")
    A("| WASI 默认可建 socket | **默认禁 TCP/UDP**，需显式放开 |")
    A("")
    A("### 常用 Cargo features（`wasmtime`）")
    A("")
    A("| feature | 作用 | 默认 |")
    A("|---|---|---|")
    A("| `cranelift` | 优化编译器（生产用） | ✅ |")
    A("| `component-model` | 组件模型 + WASIp2 | ✅ |")
    A("| `async` | 异步执行 / `call_async` | ✅ |")
    A("| `pooling-allocator` | Pooling 分配器 | ✅ |")
    A("| `cache` | 编译缓存 `Cache` 类型 | ✅ |")
    A("| `parallel-compilation` | 并行编译大模块 | ✅ |")
    A("| `winch` | 基线快速编译器（编译快、无 epoch） | ❌ |")
    A("| `all-arch` | 跨架构 AOT 预编译 | ❌ |")
    A("")
    A("最小化体积 / 无 JIT 部署（只跑 `.cwasm`）可关掉 `cranelift`，只留 runtime——用 `default-features = false` 精挑。")
    A("")
    A("---")
    A("")
    A("### 一句话收束")
    A("")
    A("> **`Engine`/`Module` 编译一次、跨线程共享；`Store` 每请求新建、用完即弃；跑不可信代码就 fuel/epoch + 内存/栈上限三件套齐全；新项目走组件模型 + WASIp2。** 记住这三句，wasmtime 的九成用法就对了。")
    A("")
    A("> 参考：wasmtime 47.x 官方文档（docs.wasmtime.dev / docs.rs），本文 API 以 2026-07 发布线为准。")
    txt = "\n".join(D)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(txt)
    print("output:", OUT)
    print("bytes :", os.path.getsize(OUT))


if __name__ == "__main__":
    main()
