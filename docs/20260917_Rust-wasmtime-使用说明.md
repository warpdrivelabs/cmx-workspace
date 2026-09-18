# Rust `wasmtime` crate 详细使用说明

> **定位**：`wasmtime` 是 Bytecode Alliance 出品、基于 Cranelift 的 WebAssembly 运行时，也是 Rust 生态里嵌入 WASM 的事实标准。后端把不可信 / 可插拔逻辑跑进 WASM 沙箱，正在成为插件系统、Serverless、边缘计算、多租户策略引擎的主流做法。
> **版本基线**：本文基于 **wasmtime 47.x（2026-07 发布线）**。wasmtime 与 `wasmtime-wasi` **同号发布**，约每月一个大版本，API 变动较快——凡易变处本文都标注，文末附「版本迁移对照」。
> **图**：6 张内嵌 base64 SVG，无外部依赖。

---

## 目录

1. [为什么是后端 WASM，为什么是 wasmtime](#一为什么是后端-wasm为什么是-wasmtime)
2. [核心对象模型](#二核心对象模型engine--module--store--linker)
3. [最小可运行例子](#三最小可运行例子)
4. [宿主 ↔ 客户机互操作](#四宿主--客户机互操作host-function--线性内存)
5. [WASI：让沙箱能读文件、走管道](#五wasi让沙箱能读文件走标准流)
6. [组件模型与 `bindgen!`](#六组件模型与-bindgen)
7. [客户机侧：用 `cargo component` 编成组件](#七客户机侧用-cargo-component-把-rust-编成-wasip2-组件)
8. [资源治理与安全沙箱](#八资源治理与安全沙箱)
9. [异步执行](#九异步执行)
10. [性能：AOT 预编译 · 缓存 · Pooling 分配器](#十性能aot-预编译--缓存--pooling-分配器)
11. [生产落地模式](#十一生产落地模式)
12. [常见坑](#十二常见坑)
13. [版本迁移对照 & Cargo features](#十三版本迁移对照--cargo-features)

---

## 一、为什么是后端 WASM，为什么是 wasmtime

把一段逻辑编译成 `.wasm`，丢进宿主进程里跑，你就得到了一个**默认无权限、可计量、可超时、可跨语言**的执行单元。典型落地：

| 场景 | 说明 | 代表 |
|---|---|---|
| 插件系统 | 第三方 / 租户上传逻辑，宿主给能力，跑在沙箱里 | 本仓 `cmx-container/cmx-runtime`（Extism，底层即 wasmtime）、Envoy、Zellij |
| Serverless / 边缘 | 冷启动微秒级、单机万级并发实例 | Fastly Compute、Fermyon Spin、Shopify Functions |
| 策略 / 规则引擎 | 把可版本化的业务差异编译成 wasm，热更不重启 | 各类 policy-as-code |
| 不可信代码 | 跑用户提交的算法 / UDF，掐死资源 | 数据库 UDF、CI 沙箱 |

**为什么选 wasmtime**：Cranelift 优化后端（运行时或 AOT 都行）、成熟的**能力安全沙箱**、`fuel`/`epoch` 两套资源治理、一等的**组件模型 + WASIp2** 支持、`pooling` 分配器把实例化压到微秒级。它就是上面多数框架的底层引擎。

> 提示：如果你要的是「开箱即用的插件加载 + 宿主函数 SDK」，可以用 Extism（封装 wasmtime）；如果你要**完全掌控**编译、资源、组件类型、异步调度，就直接用 `wasmtime`。本文讲后者。

## 二、核心对象模型（Engine / Module / Store / Linker）

理解 wasmtime，先理解 5 个类型和它们之间**谁能共享、谁必须独占**：

<p align="center"><img alt="图1：wasmtime 对象模型与所有权" style="max-width:100%;height:auto;border:1px solid #e8eef5;border-radius:10px" src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA5NDAgNDcwIiB3aWR0aD0iOTQwIiBoZWlnaHQ9IjQ3MCIgcm9sZT0iaW1nIj48ZGVmcz48bWFya2VyIGlkPSJhIiB2aWV3Qm94PSIwIDAgMTAgMTAiIHJlZlg9IjguNSIgcmVmWT0iNSIgbWFya2VyV2lkdGg9IjciIG1hcmtlckhlaWdodD0iNyIgb3JpZW50PSJhdXRvLXN0YXJ0LXJldmVyc2UiPjxwYXRoIGQ9Ik0gMCAwIEwgMTAgNSBMIDAgMTAgeiIgZmlsbD0iIzY0NzQ4YiIvPjwvbWFya2VyPjwvZGVmcz48cmVjdCB3aWR0aD0iOTQwIiBoZWlnaHQ9IjQ3MCIgZmlsbD0iI2ZiZmRmZiIvPjxnPjxyZWN0IHg9IjQwIiB5PSI2MCIgd2lkdGg9IjI1MCIgaGVpZ2h0PSI5MiIgcng9IjgiIGZpbGw9IiNlZWYyZmYiIHN0cm9rZT0iIzQzMzhjYSIgc3Ryb2tlLXdpZHRoPSIxLjciLz48cmVjdCB4PSI0MCIgeT0iNjAiIHdpZHRoPSIyNTAiIGhlaWdodD0iMjQiIHJ4PSI4IiBmaWxsPSIjNDMzOGNhIi8+PHJlY3QgeD0iNDAiIHk9Ijc2IiB3aWR0aD0iMjUwIiBoZWlnaHQ9IjgiIGZpbGw9IiM0MzM4Y2EiLz48dGV4dCB4PSI1MSIgeT0iNzciIGZvbnQtZmFtaWx5PSJ1aS1tb25vc3BhY2UsU0ZNb25vLVJlZ3VsYXIsTWVubG8sbW9ub3NwYWNlIiBmb250LXNpemU9IjEyIiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjZmZmIj5FbmdpbmU8L3RleHQ+PHRleHQgeD0iNTEiIHk9Ijk5IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwLjUiIGZpbGw9IiMxZTI5M2IiPuWFqOWxgOe8luivkeS4iuS4i+aWhzwvdGV4dD48dGV4dCB4PSI1MSIgeT0iMTE0IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwLjUiIGZpbGw9IiMxZTI5M2IiPkNsb25lID0gQXJjIMK3IFNlbmQgKyBTeW5jPC90ZXh0Pjx0ZXh0IHg9IjUxIiB5PSIxMjkiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTAuNSIgZmlsbD0iIzFlMjkzYiI+6Leo57q/56iL5YWx5Lqr77yM5Y+q5bu65LiA5qyhPC90ZXh0PjwvZz48Zz48cmVjdCB4PSI0MCIgeT0iMjAwIiB3aWR0aD0iMjUwIiBoZWlnaHQ9IjcwIiByeD0iOCIgZmlsbD0iI2YxZjVmOSIgc3Ryb2tlPSIjNDc1NTY5IiBzdHJva2Utd2lkdGg9IjEuNyIvPjxyZWN0IHg9IjQwIiB5PSIyMDAiIHdpZHRoPSIyNTAiIGhlaWdodD0iMjQiIHJ4PSI4IiBmaWxsPSIjNDc1NTY5Ii8+PHJlY3QgeD0iNDAiIHk9IjIxNiIgd2lkdGg9IjI1MCIgaGVpZ2h0PSI4IiBmaWxsPSIjNDc1NTY5Ii8+PHRleHQgeD0iNTEiIHk9IjIxNyIgZm9udC1mYW1pbHk9InVpLW1vbm9zcGFjZSxTRk1vbm8tUmVndWxhcixNZW5sbyxtb25vc3BhY2UiIGZvbnQtc2l6ZT0iMTIiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiNmZmYiPkNvbmZpZzwvdGV4dD48dGV4dCB4PSI1MSIgeT0iMjM5IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwLjUiIGZpbGw9IiMxZTI5M2IiPue8luivkS/ov5DooYzml7blvIDlhbM8L3RleHQ+PHRleHQgeD0iNTEiIHk9IjI1NCIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMC41IiBmaWxsPSIjMWUyOTNiIj5mdWVsIMK3IGVwb2NoIMK3IGFzeW5jIMK3IGNhY2hlPC90ZXh0PjwvZz48Zz48cmVjdCB4PSIzNjAiIHk9IjYwIiB3aWR0aD0iMjUwIiBoZWlnaHQ9IjkyIiByeD0iOCIgZmlsbD0iI2Y1ZjNmZiIgc3Ryb2tlPSIjN2MzYWVkIiBzdHJva2Utd2lkdGg9IjEuNyIvPjxyZWN0IHg9IjM2MCIgeT0iNjAiIHdpZHRoPSIyNTAiIGhlaWdodD0iMjQiIHJ4PSI4IiBmaWxsPSIjN2MzYWVkIi8+PHJlY3QgeD0iMzYwIiB5PSI3NiIgd2lkdGg9IjI1MCIgaGVpZ2h0PSI4IiBmaWxsPSIjN2MzYWVkIi8+PHRleHQgeD0iMzcxIiB5PSI3NyIgZm9udC1mYW1pbHk9InVpLW1vbm9zcGFjZSxTRk1vbm8tUmVndWxhcixNZW5sbyxtb25vc3BhY2UiIGZvbnQtc2l6ZT0iMTIiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiNmZmYiPk1vZHVsZTwvdGV4dD48dGV4dCB4PSIzNzEiIHk9Ijk5IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwLjUiIGZpbGw9IiMxZTI5M2IiPuW3sue8luivkeacuuWZqOeggTwvdGV4dD48dGV4dCB4PSIzNzEiIHk9IjExNCIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMC41IiBmaWxsPSIjMWUyOTNiIj5TZW5kICsgU3luYzwvdGV4dD48dGV4dCB4PSIzNzEiIHk9IjEyOSIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMC41IiBmaWxsPSIjMWUyOTNiIj7nvJbor5HkuIDmrKHvvIzlpJrlpITlpI3nlKggwrcg5Y+vIEFPVDwvdGV4dD48L2c+PGc+PHJlY3QgeD0iMzYwIiB5PSIzMDAiIHdpZHRoPSIyNTAiIGhlaWdodD0iMTEwIiByeD0iOCIgZmlsbD0iI2YwZmRmYSIgc3Ryb2tlPSIjMGQ5NDg4IiBzdHJva2Utd2lkdGg9IjEuNyIvPjxyZWN0IHg9IjM2MCIgeT0iMzAwIiB3aWR0aD0iMjUwIiBoZWlnaHQ9IjI0IiByeD0iOCIgZmlsbD0iIzBkOTQ4OCIvPjxyZWN0IHg9IjM2MCIgeT0iMzE2IiB3aWR0aD0iMjUwIiBoZWlnaHQ9IjgiIGZpbGw9IiMwZDk0ODgiLz48dGV4dCB4PSIzNzEiIHk9IjMxNyIgZm9udC1mYW1pbHk9InVpLW1vbm9zcGFjZSxTRk1vbm8tUmVndWxhcixNZW5sbyxtb25vc3BhY2UiIGZvbnQtc2l6ZT0iMTIiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiNmZmYiPlN0b3JlJmx0O1QmZ3Q7PC90ZXh0Pjx0ZXh0IHg9IjM3MSIgeT0iMzM5IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwLjUiIGZpbGw9IiMxZTI5M2IiPui/kOihjOaAgeaJgOacieadgyArIOWuv+S4u+aVsOaNriBUPC90ZXh0Pjx0ZXh0IHg9IjM3MSIgeT0iMzU0IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwLjUiIGZpbGw9IiMxZTI5M2IiPuWNlee6v+eoiyDCtyAhU3luYyDlubblj5E8L3RleHQ+PHRleHQgeD0iMzcxIiB5PSIzNjkiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTAuNSIgZmlsbD0iIzFlMjkzYiI+5q+P6K+35rGC5LiA5LiqIMK3IOWGheWtmOWPquWinuS4jeWHjzwvdGV4dD48L2c+PGc+PHJlY3QgeD0iNjkwIiB5PSIzMDAiIHdpZHRoPSIyMTAiIGhlaWdodD0iMTEwIiByeD0iOCIgZmlsbD0iI2ZmZmJlYiIgc3Ryb2tlPSIjYjQ1MzA5IiBzdHJva2Utd2lkdGg9IjEuNyIvPjxyZWN0IHg9IjY5MCIgeT0iMzAwIiB3aWR0aD0iMjEwIiBoZWlnaHQ9IjI0IiByeD0iOCIgZmlsbD0iI2I0NTMwOSIvPjxyZWN0IHg9IjY5MCIgeT0iMzE2IiB3aWR0aD0iMjEwIiBoZWlnaHQ9IjgiIGZpbGw9IiNiNDUzMDkiLz48dGV4dCB4PSI3MDEiIHk9IjMxNyIgZm9udC1mYW1pbHk9InVpLW1vbm9zcGFjZSxTRk1vbm8tUmVndWxhcixNZW5sbyxtb25vc3BhY2UiIGZvbnQtc2l6ZT0iMTIiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiNmZmYiPkluc3RhbmNlPC90ZXh0Pjx0ZXh0IHg9IjcwMSIgeT0iMzM5IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwLjUiIGZpbGw9IiMxZTI5M2IiPuaooeWdl+eahOS4gOasoeWunuS+i+WMljwvdGV4dD48dGV4dCB4PSI3MDEiIHk9IjM1NCIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMC41IiBmaWxsPSIjMWUyOTNiIj5leHBvcnRzOiBGdW5jL01lbW9yeS/igKY8L3RleHQ+PHRleHQgeD0iNzAxIiB5PSIzNjkiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTAuNSIgZmlsbD0iIzFlMjkzYiI+55Sf5ZG95ZGo5pyf57O75LqOIFN0b3JlPC90ZXh0PjwvZz48Zz48cmVjdCB4PSI2OTAiIHk9IjYwIiB3aWR0aD0iMjEwIiBoZWlnaHQ9IjkyIiByeD0iOCIgZmlsbD0iI2VlZjJmZiIgc3Ryb2tlPSIjNDMzOGNhIiBzdHJva2Utd2lkdGg9IjEuNyIvPjxyZWN0IHg9IjY5MCIgeT0iNjAiIHdpZHRoPSIyMTAiIGhlaWdodD0iMjQiIHJ4PSI4IiBmaWxsPSIjNDMzOGNhIi8+PHJlY3QgeD0iNjkwIiB5PSI3NiIgd2lkdGg9IjIxMCIgaGVpZ2h0PSI4IiBmaWxsPSIjNDMzOGNhIi8+PHRleHQgeD0iNzAxIiB5PSI3NyIgZm9udC1mYW1pbHk9InVpLW1vbm9zcGFjZSxTRk1vbm8tUmVndWxhcixNZW5sbyxtb25vc3BhY2UiIGZvbnQtc2l6ZT0iMTIiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiNmZmYiPkxpbmtlciZsdDtUJmd0OzwvdGV4dD48dGV4dCB4PSI3MDEiIHk9Ijk5IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwLjUiIGZpbGw9IiMxZTI5M2IiPuaMieWQjeino+aekCBpbXBvcnRzPC90ZXh0Pjx0ZXh0IHg9IjcwMSIgeT0iMTE0IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwLjUiIGZpbGw9IiMxZTI5M2IiPuWumuS5ieWuv+S4u+WHveaVsDwvdGV4dD48dGV4dCB4PSI3MDEiIHk9IjEyOSIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMC41IiBmaWxsPSIjMWUyOTNiIj5mdW5jX3dyYXAgLyBpbnN0YW50aWF0ZTwvdGV4dD48L2c+PGc+PHBhdGggZD0iTSAxNjUgMjAwIEwgMTY1IDE1MiIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjNDMzOGNhIiBzdHJva2Utd2lkdGg9IjEuNiIgc3Ryb2tlLWRhc2hhcnJheT0iNSAzIiBtYXJrZXItZW5kPSJ1cmwoI2EpIi8+PHJlY3QgeD0iMTUyIiB5PSIxNjciIHdpZHRoPSIyNiIgaGVpZ2h0PSIxNiIgcng9IjQiIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iMC45NSIgc3Ryb2tlPSIjY2JkNWUxIiBzdHJva2Utd2lkdGg9IjAuNyIvPjx0ZXh0IHg9IjE2NSIgeT0iMTc5IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LWZhbWlseT0idWktbW9ub3NwYWNlLFNGTW9uby1SZWd1bGFyLE1lbmxvLG1vbm9zcGFjZSIgZm9udC1zaXplPSI5LjUiIGZpbGw9IiMzMzQxNTUiPumFjee9rjwvdGV4dD48L2c+PGc+PHBhdGggZD0iTSAyOTAgMTA2IEwgMzYwIDEwNiIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjNjQ3NDhiIiBzdHJva2Utd2lkdGg9IjEuNiIgc3Ryb2tlLWRhc2hhcnJheT0iNSAzIiBtYXJrZXItZW5kPSJ1cmwoI2EpIi8+PHJlY3QgeD0iMjk0IiB5PSI5NyIgd2lkdGg9IjYxIiBoZWlnaHQ9IjE2IiByeD0iNCIgZmlsbD0iI2ZmZiIgZmlsbC1vcGFjaXR5PSIwLjk1IiBzdHJva2U9IiNjYmQ1ZTEiIHN0cm9rZS13aWR0aD0iMC43Ii8+PHRleHQgeD0iMzI1IiB5PSIxMDkiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtZmFtaWx5PSJ1aS1tb25vc3BhY2UsU0ZNb25vLVJlZ3VsYXIsTWVubG8sbW9ub3NwYWNlIiBmb250LXNpemU9IjkuNSIgZmlsbD0iIzMzNDE1NSI+Y29tcGlsZTwvdGV4dD48L2c+PGc+PHBhdGggZD0iTSA0ODUgMTUyIEwgNDg1IDMwMCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjN2MzYWVkIiBzdHJva2Utd2lkdGg9IjEuNiIgc3Ryb2tlLWRhc2hhcnJheT0iNSAzIiBtYXJrZXItZW5kPSJ1cmwoI2EpIi8+PHJlY3QgeD0iNDQwIiB5PSIyMTciIHdpZHRoPSI4OSIgaGVpZ2h0PSIxNiIgcng9IjQiIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iMC45NSIgc3Ryb2tlPSIjY2JkNWUxIiBzdHJva2Utd2lkdGg9IjAuNyIvPjx0ZXh0IHg9IjQ4NSIgeT0iMjI5IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LWZhbWlseT0idWktbW9ub3NwYWNlLFNGTW9uby1SZWd1bGFyLE1lbmxvLG1vbm9zcGFjZSIgZm9udC1zaXplPSI5LjUiIGZpbGw9IiMzMzQxNTUiPmluc3RhbnRpYXRlPC90ZXh0PjwvZz48Zz48cGF0aCBkPSJNIDY5MCAxMzAgTCA2MTAgMzAwIiBmaWxsPSJub25lIiBzdHJva2U9IiM0MzM4Y2EiIHN0cm9rZS13aWR0aD0iMS42IiBzdHJva2UtZGFzaGFycmF5PSI1IDMiIG1hcmtlci1lbmQ9InVybCgjYSkiLz48cmVjdCB4PSI1OTIiIHk9IjIwNiIgd2lkdGg9IjExNyIgaGVpZ2h0PSIxNiIgcng9IjQiIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iMC45NSIgc3Ryb2tlPSIjY2JkNWUxIiBzdHJva2Utd2lkdGg9IjAuNyIvPjx0ZXh0IHg9IjY1MCIgeT0iMjE4IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LWZhbWlseT0idWktbW9ub3NwYWNlLFNGTW9uby1SZWd1bGFyLE1lbmxvLG1vbm9zcGFjZSIgZm9udC1zaXplPSI5LjUiIGZpbGw9IiMzMzQxNTUiPnJlc29sdmUgaW1wb3J0czwvdGV4dD48L2c+PGc+PHBhdGggZD0iTSA2MTAgMzU1IEwgNjkwIDM1NSIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjMGQ5NDg4IiBzdHJva2Utd2lkdGg9IjEuNiIgc3Ryb2tlLWRhc2hhcnJheT0iNSAzIiBtYXJrZXItZW5kPSJ1cmwoI2EpIi8+PHJlY3QgeD0iNjE2IiB5PSIzNDYiIHdpZHRoPSI2OCIgaGVpZ2h0PSIxNiIgcng9IjQiIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iMC45NSIgc3Ryb2tlPSIjY2JkNWUxIiBzdHJva2Utd2lkdGg9IjAuNyIvPjx0ZXh0IHg9IjY1MCIgeT0iMzU4IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LWZhbWlseT0idWktbW9ub3NwYWNlLFNGTW9uby1SZWd1bGFyLE1lbmxvLG1vbm9zcGFjZSIgZm9udC1zaXplPSI5LjUiIGZpbGw9IiMzMzQxNTUiPnByb2R1Y2VzPC90ZXh0PjwvZz48dGV4dCB4PSI0NzAiIHk9IjQ0NSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMi41IiBmaWxsPSIjMzM0MTU1Ij7nu78v57Sr5Y+v6Leo57q/56iL5YWx5Lqr77yIRW5naW5lwrdNb2R1bGXvvInvvJvpnZLoibIgU3RvcmUg5Y2V57q/56iL44CB5q+P6K+35rGC5paw5bu6IOKAlOKAlCDov5nmnaHovrnnlYzmmK8gd2FzbXRpbWUg55So5rOV55qE56ys5LiA5Y6f5YiZPC90ZXh0Pjwvc3ZnPg=="></p>

| 类型 | 是什么 | 线程 / 复用 | 成本 |
|---|---|---|---|
| `Engine` | 全局编译上下文（持有 `Config`） | `Clone`=`Arc`，`Send+Sync`，**全进程一个** | 建一次 |
| `Module` | 编译后的机器码 | `Send+Sync`，**编译一次多处复用**，可序列化 | 编译**贵** |
| `Linker<T>` | 按名字解析 imports、定义宿主函数 | 复用于多次实例化 | 便宜 |
| `Store<T>` | 一批实例的**全部运行态** + 你的宿主数据 `T` | **单线程、!Sync**，**每请求一个** | 便宜，但内存**只增不减** |
| `Instance` | `Module` 的一次实例化 | 生命周期系于所属 `Store` | 便宜（pooling 更快） |

**两条铁律**，记住就不会用错：

1. **`Engine` / `Module` 编译一次、跨线程共享；`Store` 每请求新建、绝不跨线程。** `Store` 内存只增不减（无法单独释放某个 instance），所以它必须短命——请求级、任务级。
2. **所有运行态操作都要借道 `&mut store`**：调函数、读内存、加燃料……`Store` 是那个「可变世界」的句柄。

<p align="center"><img alt="图2：编译→实例化→调用 生命周期" style="max-width:100%;height:auto;border:1px solid #e8eef5;border-radius:10px" src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA5NDAgMzAwIiB3aWR0aD0iOTQwIiBoZWlnaHQ9IjMwMCIgcm9sZT0iaW1nIj48ZGVmcz48bWFya2VyIGlkPSJhIiB2aWV3Qm94PSIwIDAgMTAgMTAiIHJlZlg9IjguNSIgcmVmWT0iNSIgbWFya2VyV2lkdGg9IjciIG1hcmtlckhlaWdodD0iNyIgb3JpZW50PSJhdXRvLXN0YXJ0LXJldmVyc2UiPjxwYXRoIGQ9Ik0gMCAwIEwgMTAgNSBMIDAgMTAgeiIgZmlsbD0iIzY0NzQ4YiIvPjwvbWFya2VyPjwvZGVmcz48cmVjdCB3aWR0aD0iOTQwIiBoZWlnaHQ9IjMwMCIgZmlsbD0iI2ZiZmRmZiIvPjxnPjxyZWN0IHg9IjQwIiB5PSI5MCIgd2lkdGg9IjE5NSIgaGVpZ2h0PSI4NiIgcng9IjgiIGZpbGw9IiNmMWY1ZjkiIHN0cm9rZT0iIzQ3NTU2OSIgc3Ryb2tlLXdpZHRoPSIxLjciLz48cmVjdCB4PSI0MCIgeT0iOTAiIHdpZHRoPSIxOTUiIGhlaWdodD0iMjQiIHJ4PSI4IiBmaWxsPSIjNDc1NTY5Ii8+PHJlY3QgeD0iNDAiIHk9IjEwNiIgd2lkdGg9IjE5NSIgaGVpZ2h0PSI4IiBmaWxsPSIjNDc1NTY5Ii8+PHRleHQgeD0iNTEiIHk9IjEwNyIgZm9udC1mYW1pbHk9InVpLW1vbm9zcGFjZSxTRk1vbm8tUmVndWxhcixNZW5sbyxtb25vc3BhY2UiIGZvbnQtc2l6ZT0iMTIiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiNmZmYiPi53YXQgLyAud2FzbSAvIC5jd2FzbTwvdGV4dD48dGV4dCB4PSI1MSIgeT0iMTI5IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwLjUiIGZpbGw9IiMxZTI5M2IiPua6kOeggeaIlumihOe8luivkeS6p+eJqTwvdGV4dD48L2c+PGc+PHJlY3QgeD0iMjU1IiB5PSI5MCIgd2lkdGg9IjE5NSIgaGVpZ2h0PSI4NiIgcng9IjgiIGZpbGw9IiNmNWYzZmYiIHN0cm9rZT0iIzdjM2FlZCIgc3Ryb2tlLXdpZHRoPSIxLjciLz48cmVjdCB4PSIyNTUiIHk9IjkwIiB3aWR0aD0iMTk1IiBoZWlnaHQ9IjI0IiByeD0iOCIgZmlsbD0iIzdjM2FlZCIvPjxyZWN0IHg9IjI1NSIgeT0iMTA2IiB3aWR0aD0iMTk1IiBoZWlnaHQ9IjgiIGZpbGw9IiM3YzNhZWQiLz48dGV4dCB4PSIyNjYiIHk9IjEwNyIgZm9udC1mYW1pbHk9InVpLW1vbm9zcGFjZSxTRk1vbm8tUmVndWxhcixNZW5sbyxtb25vc3BhY2UiIGZvbnQtc2l6ZT0iMTIiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiNmZmYiPue8luivkSDihpIgTW9kdWxlPC90ZXh0Pjx0ZXh0IHg9IjI2NiIgeT0iMTI5IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwLjUiIGZpbGw9IiMxZTI5M2IiPkNyYW5lbGlmdCDnlJ/miJDmnLrlmajnoIE8L3RleHQ+PHRleHQgeD0iMjY2IiB5PSIxNDQiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTAuNSIgZmlsbD0iIzFlMjkzYiI+6LS1IMK3IOe8k+WtmCAvIEFPVCDmkYrplIA8L3RleHQ+PC9nPjxnPjxyZWN0IHg9IjQ5MCIgeT0iOTAiIHdpZHRoPSIxOTUiIGhlaWdodD0iODYiIHJ4PSI4IiBmaWxsPSIjZjBmZGZhIiBzdHJva2U9IiMwZDk0ODgiIHN0cm9rZS13aWR0aD0iMS43Ii8+PHJlY3QgeD0iNDkwIiB5PSI5MCIgd2lkdGg9IjE5NSIgaGVpZ2h0PSIyNCIgcng9IjgiIGZpbGw9IiMwZDk0ODgiLz48cmVjdCB4PSI0OTAiIHk9IjEwNiIgd2lkdGg9IjE5NSIgaGVpZ2h0PSI4IiBmaWxsPSIjMGQ5NDg4Ii8+PHRleHQgeD0iNTAxIiB5PSIxMDciIGZvbnQtZmFtaWx5PSJ1aS1tb25vc3BhY2UsU0ZNb25vLVJlZ3VsYXIsTWVubG8sbW9ub3NwYWNlIiBmb250LXNpemU9IjEyIiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjZmZmIj7lrp7kvovljJYg4oaSIFN0b3JlPC90ZXh0Pjx0ZXh0IHg9IjUwMSIgeT0iMTI5IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwLjUiIGZpbGw9IiMxZTI5M2IiPuWPluWGheWtmC/ooaggwrcg5L6/5a6cPC90ZXh0Pjx0ZXh0IHg9IjUwMSIgeT0iMTQ0IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwLjUiIGZpbGw9IiMxZTI5M2IiPnBvb2xpbmcg5Y+v5YaN5o+Q6YCfPC90ZXh0PjwvZz48Zz48cmVjdCB4PSI3MjUiIHk9IjkwIiB3aWR0aD0iMTk1IiBoZWlnaHQ9Ijg2IiByeD0iOCIgZmlsbD0iI2ZmZmJlYiIgc3Ryb2tlPSIjYjQ1MzA5IiBzdHJva2Utd2lkdGg9IjEuNyIvPjxyZWN0IHg9IjcyNSIgeT0iOTAiIHdpZHRoPSIxOTUiIGhlaWdodD0iMjQiIHJ4PSI4IiBmaWxsPSIjYjQ1MzA5Ii8+PHJlY3QgeD0iNzI1IiB5PSIxMDYiIHdpZHRoPSIxOTUiIGhlaWdodD0iOCIgZmlsbD0iI2I0NTMwOSIvPjx0ZXh0IHg9IjczNiIgeT0iMTA3IiBmb250LWZhbWlseT0idWktbW9ub3NwYWNlLFNGTW9uby1SZWd1bGFyLE1lbmxvLG1vbm9zcGFjZSIgZm9udC1zaXplPSIxMiIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iI2ZmZiI+dHlwZWQg6LCD55SoPC90ZXh0Pjx0ZXh0IHg9IjczNiIgeT0iMTI5IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwLjUiIGZpbGw9IiMxZTI5M2IiPmdldF90eXBlZF9mdW5jPC90ZXh0Pjx0ZXh0IHg9IjczNiIgeT0iMTQ0IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwLjUiIGZpbGw9IiMxZTI5M2IiPi5jYWxsKCZhbXA7bXV0IHN0b3JlLCBhcmdzKTwvdGV4dD48L2c+PGc+PHBhdGggZD0iTSAyMzUgMTMzIEwgMjU1IDEzMyIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjNjQ3NDhiIiBzdHJva2Utd2lkdGg9IjEuNiIgc3Ryb2tlLWRhc2hhcnJheT0iNSAzIiBtYXJrZXItZW5kPSJ1cmwoI2EpIi8+PC9nPjxnPjxwYXRoIGQ9Ik0gNDcwIDEzMyBMIDQ5MCAxMzMiIGZpbGw9Im5vbmUiIHN0cm9rZT0iIzY0NzQ4YiIgc3Ryb2tlLXdpZHRoPSIxLjYiIHN0cm9rZS1kYXNoYXJyYXk9IjUgMyIgbWFya2VyLWVuZD0idXJsKCNhKSIvPjwvZz48Zz48cGF0aCBkPSJNIDcwNSAxMzMgTCA3MjUgMTMzIiBmaWxsPSJub25lIiBzdHJva2U9IiM2NDc0OGIiIHN0cm9rZS13aWR0aD0iMS42IiBzdHJva2UtZGFzaGFycmF5PSI1IDMiIG1hcmtlci1lbmQ9InVybCgjYSkiLz48L2c+PHRleHQgeD0iMzUyIiB5PSI3MCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMSIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iIzdjM2FlZCI+57yW6K+R5LiA5qyhPC90ZXh0Pjx0ZXh0IHg9IjcwMCIgeT0iNzAiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTEiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiMwZDk0ODgiPuavj+ivt+axguS4gOasoSDCtyBTdG9yZSBkcm9wIOWNs+WbnuaUtjwvdGV4dD48dGV4dCB4PSI0NzAiIHk9IjI1MCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMi41IiBmaWxsPSIjMzM0MTU1Ij7ng63ot6/lvoTlj6rlgZrjgIzlrp7kvovljJYgKyDosIPnlKjjgI3vvJvmiornvJbor5HmjKrliLDmnoTlu7rmnJ/vvIhwcmVjb21waWxlX21vZHVsZSDihpIgLmN3YXNt77yJ77yM5ZCv5Yqo5Y2zIGRlc2VyaWFsaXplIOi9veWFpTwvdGV4dD48L3N2Zz4="></p>

## 三、最小可运行例子

`Cargo.toml`：

```toml
[dependencies]
wasmtime = "47"          # 与 wasmtime-wasi 同号发布
anyhow = "1"
```

调用一个客户机导出的 `add(i32,i32)->i32`：

```rust
use wasmtime::*;

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
}
```

`get_typed_func::<Params, Results>` 在取函数时就核对签名，之后 `.call` 零反射、直达机器码。若要动态签名，用 `get_func` + `Func::call(&mut store, &[Val], &mut [Val])`。

## 四、宿主 ↔ 客户机互操作（host function + 线性内存）

沙箱的本质是：**客户机默认什么也做不了，能做什么由宿主注入的 import 决定**。

<p align="center"><img alt="图3：宿主↔客户机沙箱边界" style="max-width:100%;height:auto;border:1px solid #e8eef5;border-radius:10px" src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA5NDAgNDAwIiB3aWR0aD0iOTQwIiBoZWlnaHQ9IjQwMCIgcm9sZT0iaW1nIj48ZGVmcz48bWFya2VyIGlkPSJhIiB2aWV3Qm94PSIwIDAgMTAgMTAiIHJlZlg9IjguNSIgcmVmWT0iNSIgbWFya2VyV2lkdGg9IjciIG1hcmtlckhlaWdodD0iNyIgb3JpZW50PSJhdXRvLXN0YXJ0LXJldmVyc2UiPjxwYXRoIGQ9Ik0gMCAwIEwgMTAgNSBMIDAgMTAgeiIgZmlsbD0iIzY0NzQ4YiIvPjwvbWFya2VyPjwvZGVmcz48cmVjdCB3aWR0aD0iOTQwIiBoZWlnaHQ9IjQwMCIgZmlsbD0iI2ZiZmRmZiIvPjxnPjxyZWN0IHg9IjQwIiB5PSIxMTAiIHdpZHRoPSIyMjAiIGhlaWdodD0iMTUwIiByeD0iOCIgZmlsbD0iI2YxZjVmOSIgc3Ryb2tlPSIjNDc1NTY5IiBzdHJva2Utd2lkdGg9IjEuNyIvPjxyZWN0IHg9IjQwIiB5PSIxMTAiIHdpZHRoPSIyMjAiIGhlaWdodD0iMjQiIHJ4PSI4IiBmaWxsPSIjNDc1NTY5Ii8+PHJlY3QgeD0iNDAiIHk9IjEyNiIgd2lkdGg9IjIyMCIgaGVpZ2h0PSI4IiBmaWxsPSIjNDc1NTY5Ii8+PHRleHQgeD0iNTEiIHk9IjEyNyIgZm9udC1mYW1pbHk9InVpLW1vbm9zcGFjZSxTRk1vbm8tUmVndWxhcixNZW5sbyxtb25vc3BhY2UiIGZvbnQtc2l6ZT0iMTIiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiNmZmYiPuWuv+S4uyBIb3N0IChSdXN0KTwvdGV4dD48dGV4dCB4PSI1MSIgeT0iMTQ5IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwLjUiIGZpbGw9IiMxZTI5M2IiPuaWh+S7tiDCtyDnvZHnu5wgwrcg5YaF5a2YPC90ZXh0Pjx0ZXh0IHg9IjUxIiB5PSIxNjQiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTAuNSIgZmlsbD0iIzFlMjkzYiI+5a6M5pW0IE9TIOadg+mZkDwvdGV4dD48dGV4dCB4PSI1MSIgeT0iMTc5IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwLjUiIGZpbGw9IiMxZTI5M2IiPuKAlOKAlCDmspnnrrHlpJY8L3RleHQ+PC9nPjxyZWN0IHg9IjM2MCIgeT0iNzAiIHdpZHRoPSIzMzAiIGhlaWdodD0iMjUwIiByeD0iMTIiIGZpbGw9IiNmZmZiZWIiIHN0cm9rZT0iI2I0NTMwOSIgc3Ryb2tlLXdpZHRoPSIyLjQiIHN0cm9rZS1kYXNoYXJyYXk9IjcgNCIvPjx0ZXh0IHg9IjUyNSIgeT0iOTgiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtZmFtaWx5PSJ1aS1tb25vc3BhY2UsU0ZNb25vLVJlZ3VsYXIsTWVubG8sbW9ub3NwYWNlIiBmb250LXNpemU9IjEzIiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjYjQ1MzA5Ij5HdWVzdCDmspnnrrE8L3RleHQ+PGc+PHJlY3QgeD0iMzkwIiB5PSIxMjAiIHdpZHRoPSIyNzAiIGhlaWdodD0iNjYiIHJ4PSI4IiBmaWxsPSIjZmZmYmViIiBzdHJva2U9IiNiNDUzMDkiIHN0cm9rZS13aWR0aD0iMS43Ii8+PHJlY3QgeD0iMzkwIiB5PSIxMjAiIHdpZHRoPSIyNzAiIGhlaWdodD0iMjQiIHJ4PSI4IiBmaWxsPSIjYjQ1MzA5Ii8+PHJlY3QgeD0iMzkwIiB5PSIxMzYiIHdpZHRoPSIyNzAiIGhlaWdodD0iOCIgZmlsbD0iI2I0NTMwOSIvPjx0ZXh0IHg9IjQwMSIgeT0iMTM3IiBmb250LWZhbWlseT0idWktbW9ub3NwYWNlLFNGTW9uby1SZWd1bGFyLE1lbmxvLG1vbm9zcGFjZSIgZm9udC1zaXplPSIxMiIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iI2ZmZiI+57q/5oCn5YaF5a2YIGxpbmVhciBtZW1vcnk8L3RleHQ+PHRleHQgeD0iNDAxIiB5PSIxNTkiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTAuNSIgZmlsbD0iIzFlMjkzYiI+54us56uL5Zyw5Z2A56m66Ze0PC90ZXh0Pjx0ZXh0IHg9IjQwMSIgeT0iMTc0IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwLjUiIGZpbGw9IiMxZTI5M2IiPui2iueVjOWNsyB0cmFw77yM56Kw5LiN5Yiw5a6/5Li7PC90ZXh0PjwvZz48Zz48cmVjdCB4PSIzOTAiIHk9IjIxMCIgd2lkdGg9IjI3MCIgaGVpZ2h0PSI5MCIgcng9IjgiIGZpbGw9IiNmZmZiZWIiIHN0cm9rZT0iI2I0NTMwOSIgc3Ryb2tlLXdpZHRoPSIxLjciLz48cmVjdCB4PSIzOTAiIHk9IjIxMCIgd2lkdGg9IjI3MCIgaGVpZ2h0PSIyNCIgcng9IjgiIGZpbGw9IiNiNDUzMDkiLz48cmVjdCB4PSIzOTAiIHk9IjIyNiIgd2lkdGg9IjI3MCIgaGVpZ2h0PSI4IiBmaWxsPSIjYjQ1MzA5Ii8+PHRleHQgeD0iNDAxIiB5PSIyMjciIGZvbnQtZmFtaWx5PSJ1aS1tb25vc3BhY2UsU0ZNb25vLVJlZ3VsYXIsTWVubG8sbW9ub3NwYWNlIiBmb250LXNpemU9IjEyIiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjZmZmIj7lrqLmiLfmnLrku6PnoIE8L3RleHQ+PHRleHQgeD0iNDAxIiB5PSIyNDkiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTAuNSIgZmlsbD0iIzFlMjkzYiI+5peg546v5aKD5p2D6ZmQIG5vIGFtYmllbnQgYXV0aG9yaXR5PC90ZXh0Pjx0ZXh0IHg9IjQwMSIgeT0iMjY0IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwLjUiIGZpbGw9IiMxZTI5M2IiPuS4jeiDveiHquW3seW8gOaWh+S7ti9zb2NrZXQ8L3RleHQ+PHRleHQgeD0iNDAxIiB5PSIyNzkiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTAuNSIgZmlsbD0iIzFlMjkzYiI+5Y+q6IO96LCD5pi+5byP5a+85YWl55qE5Ye95pWwPC90ZXh0PjwvZz48Zz48cGF0aCBkPSJNIDI2MCAxNTAgTCAzOTAgMTUwIiBmaWxsPSJub25lIiBzdHJva2U9IiM0MzM4Y2EiIHN0cm9rZS13aWR0aD0iMS42IiBzdHJva2UtZGFzaGFycmF5PSI1IDMiIG1hcmtlci1lbmQ9InVybCgjYSkiLz48cmVjdCB4PSIyNzciIHk9IjE0MSIgd2lkdGg9Ijk2IiBoZWlnaHQ9IjE2IiByeD0iNCIgZmlsbD0iI2ZmZiIgZmlsbC1vcGFjaXR5PSIwLjk1IiBzdHJva2U9IiNjYmQ1ZTEiIHN0cm9rZS13aWR0aD0iMC43Ii8+PHRleHQgeD0iMzI1IiB5PSIxNTMiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtZmFtaWx5PSJ1aS1tb25vc3BhY2UsU0ZNb25vLVJlZ3VsYXIsTWVubG8sbW9ub3NwYWNlIiBmb250LXNpemU9IjkuNSIgZmlsbD0iIzMzNDE1NSI+aW1wb3J0cyDlrr/kuLvlh73mlbA8L3RleHQ+PC9nPjxnPjxwYXRoIGQ9Ik0gMzkwIDI1MCBMIDI2MCAyNTAiIGZpbGw9Im5vbmUiIHN0cm9rZT0iIzBkOTQ4OCIgc3Ryb2tlLXdpZHRoPSIxLjYiIHN0cm9rZS1kYXNoYXJyYXk9IjUgMyIgbWFya2VyLWVuZD0idXJsKCNhKSIvPjxyZWN0IHg9IjI3NCIgeT0iMjQxIiB3aWR0aD0iMTAzIiBoZWlnaHQ9IjE2IiByeD0iNCIgZmlsbD0iI2ZmZiIgZmlsbC1vcGFjaXR5PSIwLjk1IiBzdHJva2U9IiNjYmQ1ZTEiIHN0cm9rZS13aWR0aD0iMC43Ii8+PHRleHQgeD0iMzI1IiB5PSIyNTMiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtZmFtaWx5PSJ1aS1tb25vc3BhY2UsU0ZNb25vLVJlZ3VsYXIsTWVubG8sbW9ub3NwYWNlIiBmb250LXNpemU9IjkuNSIgZmlsbD0iIzMzNDE1NSI+ZXhwb3J0cyDlrqLmiLfmnLrlh73mlbA8L3RleHQ+PC9nPjxnPjxyZWN0IHg9IjcyMCIgeT0iMTUwIiB3aWR0aD0iMTgwIiBoZWlnaHQ9IjExMCIgcng9IjgiIGZpbGw9IiNmZWYyZjIiIHN0cm9rZT0iI2RjMjYyNiIgc3Ryb2tlLXdpZHRoPSIxLjciLz48cmVjdCB4PSI3MjAiIHk9IjE1MCIgd2lkdGg9IjE4MCIgaGVpZ2h0PSIyNCIgcng9IjgiIGZpbGw9IiNkYzI2MjYiLz48cmVjdCB4PSI3MjAiIHk9IjE2NiIgd2lkdGg9IjE4MCIgaGVpZ2h0PSI4IiBmaWxsPSIjZGMyNjI2Ii8+PHRleHQgeD0iNzMxIiB5PSIxNjciIGZvbnQtZmFtaWx5PSJ1aS1tb25vc3BhY2UsU0ZNb25vLVJlZ3VsYXIsTWVubG8sbW9ub3NwYWNlIiBmb250LXNpemU9IjEyIiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjZmZmIj7og73lipsgPSDmmL7lvI/mjojkuog8L3RleHQ+PHRleHQgeD0iNzMxIiB5PSIxODkiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTAuNSIgZmlsbD0iIzFlMjkzYiI+V0FTSTog6aKE5omT5byA55uu5b2VL+euoemBkzwvdGV4dD48dGV4dCB4PSI3MzEiIHk9IjIwNCIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMC41IiBmaWxsPSIjMWUyOTNiIj7oh6rlrprkuYkgaG9zdCBmdW5jPC90ZXh0Pjx0ZXh0IHg9IjczMSIgeT0iMjE5IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwLjUiIGZpbGw9IiMxZTI5M2IiPum7mOiupOaLkue7nSAodjQ3OiBzb2NrZXQg6buY6K6k56aBKTwvdGV4dD48L2c+PHRleHQgeD0iNDcwIiB5PSIzNjAiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTIuNSIgZmlsbD0iIzMzNDE1NSI+5rKZ566x5piv44CM6buY6K6k5peg5p2D6ZmQ44CN77ya5a6i5oi35py66IO95YGa5LuA5LmI77yM5a6M5YWo55Sx5a6/5Li75rOo5YWl5LqG5ZOq5LqbIGltcG9ydCDlhrPlrpog4oCU4oCUIOi/meaYr+iDveWKm+WuieWFqOaooeWeizwvdGV4dD48L3N2Zz4="></p>

### 4.1 用 Linker 注入宿主函数

```rust
use wasmtime::*;

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
}
```

要点：

- **`Caller<'_, T>`** 是宿主函数里访问「调用方 Store」的句柄：`caller.data()/data_mut()` 取宿主数据，`caller.get_export("memory")` 拿客户机内存。
- **线性内存是一整块 `&[u8]`**：客户机传给你的永远是「偏移 + 长度」，你自己解释。写用 `mem.data_mut(&mut caller)`，或 `mem.write(&mut store, offset, bytes)`。
- 宿主函数返回 `Err` 会让客户机**陷阱（trap）**，调用栈整个中止——这是把错误传回宿主的正规通道。
- 用 `func_wrap` 处理静态签名（自动类型转换）；动态签名用 `Func::new` + `&[Val]`。

### 4.2 谁分配内存？

客户机的线性内存由**客户机自己**增长（`memory.grow`）。宿主要把数据「递进去」，惯例是：客户机导出一个 `alloc(len)->ptr`，宿主调用它拿到偏移，再 `mem.write` 填字节，最后把 `ptr,len` 传给业务函数。组件模型（下文）会把这套繁琐 ABI **自动生成**掉。

## 五、WASI：让沙箱能读文件、走标准流

裸沙箱连 `println!` 都不行（没有 stdout）。**WASI**（WebAssembly System Interface）是一组标准 import，按**能力**把受控的系统访问交给客户机：预打开某个目录、接一根 stdin/stdout、给几个环境变量——**给什么才有什么**。

> ⚠️ **v47 安全默认值**：`wasmtime-wasi` 现在**默认禁止**客户机创建 TCP/UDP socket，需显式放开。这是「默认拒绝」能力模型的体现。

WASI 有两代，对应两种模块形态：

| | Preview 1 (WASIp1) | Preview 2 (WASIp2) |
|---|---|---|
| 模块形态 | 核心模块（`.wasm`） | **组件**（component） |
| wasmtime 模块路径 | `wasmtime_wasi::preview1` | `wasmtime_wasi::p2` |
| 适用 | 已有 `wasm32-wasip1` 产物 | **新项目首选** |

### 5.1 WASIp2（组件，推荐）—— 当前 API

> 这里是最容易踩版本坑的地方。**v47 关键变化**：旧的 `IoView` trait 已删除；`WasiView` 现在只有一个方法 `ctx()`，返回把 `WasiCtx` 与 `ResourceTable` 打包在一起的 **`WasiCtxView`**。

```rust
use wasmtime::{Engine, Store, Config, Result};
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
}
```

### 5.2 WASIp1（核心模块，兼容老产物）

```rust
use wasmtime::{Engine, Store, Module, Linker, Result};
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
}
```

> 还有更新的 **WASIp3**（`wasmtime_wasi::p3::add_to_linker`，异步优先，需 `config.wasm_component_model_async(true)`），面向原生异步的组件；生产可先稳在 p2。

## 六、组件模型与 `bindgen!`

核心模块只有 4 种数字类型，字符串/结构全靠手搓 ABI。**组件模型**用 **WIT**（Wasm Interface Types）描述接口，`bindgen!` 宏据此**生成强类型 Rust 绑定**，跨语言可组合。

<p align="center"><img alt="图5：核心模块 vs 组件模型" style="max-width:100%;height:auto;border:1px solid #e8eef5;border-radius:10px" src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA5NDAgMzYwIiB3aWR0aD0iOTQwIiBoZWlnaHQ9IjM2MCIgcm9sZT0iaW1nIj48ZGVmcz48bWFya2VyIGlkPSJhIiB2aWV3Qm94PSIwIDAgMTAgMTAiIHJlZlg9IjguNSIgcmVmWT0iNSIgbWFya2VyV2lkdGg9IjciIG1hcmtlckhlaWdodD0iNyIgb3JpZW50PSJhdXRvLXN0YXJ0LXJldmVyc2UiPjxwYXRoIGQ9Ik0gMCAwIEwgMTAgNSBMIDAgMTAgeiIgZmlsbD0iIzY0NzQ4YiIvPjwvbWFya2VyPjwvZGVmcz48cmVjdCB3aWR0aD0iOTQwIiBoZWlnaHQ9IjM2MCIgZmlsbD0iI2ZiZmRmZiIvPjxnPjxyZWN0IHg9IjYwIiB5PSI3MCIgd2lkdGg9IjM2MCIgaGVpZ2h0PSIyMjAiIHJ4PSI4IiBmaWxsPSIjZmZmYmViIiBzdHJva2U9IiNiNDUzMDkiIHN0cm9rZS13aWR0aD0iMS43Ii8+PHJlY3QgeD0iNjAiIHk9IjcwIiB3aWR0aD0iMzYwIiBoZWlnaHQ9IjI0IiByeD0iOCIgZmlsbD0iI2I0NTMwOSIvPjxyZWN0IHg9IjYwIiB5PSI4NiIgd2lkdGg9IjM2MCIgaGVpZ2h0PSI4IiBmaWxsPSIjYjQ1MzA5Ii8+PHRleHQgeD0iNzEiIHk9Ijg3IiBmb250LWZhbWlseT0idWktbW9ub3NwYWNlLFNGTW9uby1SZWd1bGFyLE1lbmxvLG1vbm9zcGFjZSIgZm9udC1zaXplPSIxMiIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iI2ZmZiI+Q29yZSBNb2R1bGXvvIjmoLjlv4PmqKHlnZfvvIk8L3RleHQ+PHRleHQgeD0iNzEiIHk9IjEwOSIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMC41IiBmaWxsPSIjMWUyOTNiIj7nsbvlnovlj6rmnIkgaTMyIC8gaTY0IC8gZjMyIC8gZjY0IC8gdjEyODwvdGV4dD48dGV4dCB4PSI3MSIgeT0iMTI0IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwLjUiIGZpbGw9IiMxZTI5M2IiPuWtl+espuS4siAvIOe7k+aehOS9kyDihpIg6Z2g57qm5a6aICsg57q/5oCn5YaF5a2Y5YGP56e7PC90ZXh0Pjx0ZXh0IHg9IjcxIiB5PSIxMzkiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTAuNSIgZmlsbD0iIzFlMjkzYiI+5a6/5Li75omL5YqoIG1lbW9yeS5kYXRhKCkg6K+75YaZ5a2X6IqCPC90ZXh0Pjx0ZXh0IHg9IjcxIiB5PSIxNTQiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTAuNSIgZmlsbD0iIzFlMjkzYiI+QUJJIOmdoOWPjOaWueengeS4i+e6puWumu+8jOaYk+mUmeOAgeivreiogOW8uue7keWumjwvdGV4dD48dGV4dCB4PSI3MSIgeT0iMTY5IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwLjUiIGZpbGw9IiMxZTI5M2IiPndhc210aW1lOjpNb2R1bGUgLyBJbnN0YW5jZSAvIExpbmtlcjwvdGV4dD48L2c+PGc+PHJlY3QgeD0iNTIwIiB5PSI3MCIgd2lkdGg9IjM2MCIgaGVpZ2h0PSIyMjAiIHJ4PSI4IiBmaWxsPSIjZjVmM2ZmIiBzdHJva2U9IiM3YzNhZWQiIHN0cm9rZS13aWR0aD0iMS43Ii8+PHJlY3QgeD0iNTIwIiB5PSI3MCIgd2lkdGg9IjM2MCIgaGVpZ2h0PSIyNCIgcng9IjgiIGZpbGw9IiM3YzNhZWQiLz48cmVjdCB4PSI1MjAiIHk9Ijg2IiB3aWR0aD0iMzYwIiBoZWlnaHQ9IjgiIGZpbGw9IiM3YzNhZWQiLz48dGV4dCB4PSI1MzEiIHk9Ijg3IiBmb250LWZhbWlseT0idWktbW9ub3NwYWNlLFNGTW9uby1SZWd1bGFyLE1lbmxvLG1vbm9zcGFjZSIgZm9udC1zaXplPSIxMiIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iI2ZmZiI+Q29tcG9uZW5077yI57uE5Lu25qih5Z6L77yJPC90ZXh0Pjx0ZXh0IHg9IjUzMSIgeT0iMTA5IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwLjUiIGZpbGw9IiMxZTI5M2IiPldJVCDmjqXlj6PnsbvlnovvvJpzdHJpbmcvbGlzdC9yZWNvcmQvdmFyaWFudDwvdGV4dD48dGV4dCB4PSI1MzEiIHk9IjEyNCIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMC41IiBmaWxsPSIjMWUyOTNiIj5yZXNvdXJjZe+8muW4pueUn+WRveWRqOacn+eahOWPpeafhO+8iOWmguaWh+S7tu+8iTwvdGV4dD48dGV4dCB4PSI1MzEiIHk9IjEzOSIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMC41IiBmaWxsPSIjMWUyOTNiIj5iaW5kZ2VuISDku44gLndpdCDnlJ/miJDlvLrnsbvlnosgUnVzdCDnu5Hlrpo8L3RleHQ+PHRleHQgeD0iNTMxIiB5PSIxNTQiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTAuNSIgZmlsbD0iIzFlMjkzYiI+6K+t6KiA5peg5YWz77yaUnVzdC9Hby9KUyDnu4Tku7blj6/kupLnm7jnu4TlkIg8L3RleHQ+PHRleHQgeD0iNTMxIiB5PSIxNjkiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTAuNSIgZmlsbD0iIzFlMjkzYiI+d2FzbXRpbWU6OmNvbXBvbmVudDo6e0NvbXBvbmVudCwgTGlua2VyfTwvdGV4dD48L2c+PGc+PHBhdGggZD0iTSA0MjAgMTgwIEwgNTIwIDE4MCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjN2MzYWVkIiBzdHJva2Utd2lkdGg9IjEuNiIgc3Ryb2tlLWRhc2hhcnJheT0iNSAzIiBtYXJrZXItZW5kPSJ1cmwoI2EpIi8+PHJlY3QgeD0iNDUwIiB5PSIxNzEiIHdpZHRoPSI0MCIgaGVpZ2h0PSIxNiIgcng9IjQiIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iMC45NSIgc3Ryb2tlPSIjY2JkNWUxIiBzdHJva2Utd2lkdGg9IjAuNyIvPjx0ZXh0IHg9IjQ3MCIgeT0iMTgzIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LWZhbWlseT0idWktbW9ub3NwYWNlLFNGTW9uby1SZWd1bGFyLE1lbmxvLG1vbm9zcGFjZSIgZm9udC1zaXplPSI5LjUiIGZpbGw9IiMzMzQxNTUiPuS4iuWxguWwgeijhTwvdGV4dD48L2c+PHRleHQgeD0iNDcwIiB5PSIzMzAiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTIuNSIgZmlsbD0iIzMzNDE1NSI+5paw6aG555uu5LyY5YWI57uE5Lu25qih5Z6LICsgV0FTSXAy77ya57G75Z6L5a6J5YWo44CB6Leo6K+t6KiA44CB5Y+v57uE5ZCI77yb5qC45b+D5qih5Z2X6YCC5ZCI5p6B6Ie06L276YeP5oiW5bey5pyJIC53YXNtPC90ZXh0Pjwvc3ZnPg=="></p>

一个 WIT（`wit/calculator.wit`）：

```wit
package example:calc;

world calculator {
  // 客户机要实现的导出
  export add: func(a: s32, b: s32) -> s32;
  // 宿主提供给客户机的导入
  import log: func(msg: string);
}
```

宿主侧用 `bindgen!` 生成绑定并调用：

```rust
use wasmtime::component::bindgen;

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
}
```

`string` 参数你**直接传 `String`**，编解码、内存分配全由生成代码处理——这正是组件模型相对核心模块最大的工程价值。`resource` 类型还能表达「带生命周期的句柄」（文件、连接），由 `ResourceTable` 托管。

## 七、客户机侧：用 `cargo component` 把 Rust 编成 WASIp2 组件

前六节都站在**宿主**视角。这一节把镜头转到**客户机**：怎么用 Rust 写出、并编译出一个能被第六节宿主加载的 WASIp2 组件。以实现第六节那个 `calculator` world 为例，正好首尾闭环。

<p align="center"><img alt="图6：客户机侧组件构建流水线" style="max-width:100%;height:auto;border:1px solid #e8eef5;border-radius:10px" src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA5NDAgMjUwIiB3aWR0aD0iOTQwIiBoZWlnaHQ9IjI1MCIgcm9sZT0iaW1nIj48ZGVmcz48bWFya2VyIGlkPSJhIiB2aWV3Qm94PSIwIDAgMTAgMTAiIHJlZlg9IjguNSIgcmVmWT0iNSIgbWFya2VyV2lkdGg9IjciIG1hcmtlckhlaWdodD0iNyIgb3JpZW50PSJhdXRvLXN0YXJ0LXJldmVyc2UiPjxwYXRoIGQ9Ik0gMCAwIEwgMTAgNSBMIDAgMTAgeiIgZmlsbD0iIzY0NzQ4YiIvPjwvbWFya2VyPjwvZGVmcz48cmVjdCB3aWR0aD0iOTQwIiBoZWlnaHQ9IjI1MCIgZmlsbD0iI2ZiZmRmZiIvPjxnPjxyZWN0IHg9IjE4IiB5PSI3OCIgd2lkdGg9IjE1NiIgaGVpZ2h0PSI4MiIgcng9IjgiIGZpbGw9IiNmZmZiZWIiIHN0cm9rZT0iI2I0NTMwOSIgc3Ryb2tlLXdpZHRoPSIxLjciLz48cmVjdCB4PSIxOCIgeT0iNzgiIHdpZHRoPSIxNTYiIGhlaWdodD0iMjQiIHJ4PSI4IiBmaWxsPSIjYjQ1MzA5Ii8+PHJlY3QgeD0iMTgiIHk9Ijk0IiB3aWR0aD0iMTU2IiBoZWlnaHQ9IjgiIGZpbGw9IiNiNDUzMDkiLz48dGV4dCB4PSIyOSIgeT0iOTUiIGZvbnQtZmFtaWx5PSJ1aS1tb25vc3BhY2UsU0ZNb25vLVJlZ3VsYXIsTWVubG8sbW9ub3NwYWNlIiBmb250LXNpemU9IjEyIiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjZmZmIj5SdXN0IOa6kOeggSArIHdpdC88L3RleHQ+PHRleHQgeD0iMjkiIHk9IjExNyIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMC41IiBmaWxsPSIjMWUyOTNiIj7kuJrliqHpgLvovpE8L3RleHQ+PHRleHQgeD0iMjkiIHk9IjEzMiIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMC41IiBmaWxsPSIjMWUyOTNiIj53b3JsZCDlrprkuYk8L3RleHQ+PC9nPjxnPjxyZWN0IHg9IjIwNSIgeT0iNzgiIHdpZHRoPSIxNTYiIGhlaWdodD0iODIiIHJ4PSI4IiBmaWxsPSIjZjVmM2ZmIiBzdHJva2U9IiM3YzNhZWQiIHN0cm9rZS13aWR0aD0iMS43Ii8+PHJlY3QgeD0iMjA1IiB5PSI3OCIgd2lkdGg9IjE1NiIgaGVpZ2h0PSIyNCIgcng9IjgiIGZpbGw9IiM3YzNhZWQiLz48cmVjdCB4PSIyMDUiIHk9Ijk0IiB3aWR0aD0iMTU2IiBoZWlnaHQ9IjgiIGZpbGw9IiM3YzNhZWQiLz48dGV4dCB4PSIyMTYiIHk9Ijk1IiBmb250LWZhbWlseT0idWktbW9ub3NwYWNlLFNGTW9uby1SZWd1bGFyLE1lbmxvLG1vbm9zcGFjZSIgZm9udC1zaXplPSIxMiIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iI2ZmZiI+d2l0LWJpbmRnZW48L3RleHQ+PHRleHQgeD0iMjE2IiB5PSIxMTciIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTAuNSIgZmlsbD0iIzFlMjkzYiI+55Sf5oiQIGJpbmRpbmdzPC90ZXh0Pjx0ZXh0IHg9IjIxNiIgeT0iMTMyIiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwLjUiIGZpbGw9IiMxZTI5M2IiPkd1ZXN0IHRyYWl0ICsg5a+85YWl5Ye95pWwPC90ZXh0PjwvZz48Zz48cmVjdCB4PSIzOTIiIHk9Ijc4IiB3aWR0aD0iMTU2IiBoZWlnaHQ9IjgyIiByeD0iOCIgZmlsbD0iI2VlZjJmZiIgc3Ryb2tlPSIjNDMzOGNhIiBzdHJva2Utd2lkdGg9IjEuNyIvPjxyZWN0IHg9IjM5MiIgeT0iNzgiIHdpZHRoPSIxNTYiIGhlaWdodD0iMjQiIHJ4PSI4IiBmaWxsPSIjNDMzOGNhIi8+PHJlY3QgeD0iMzkyIiB5PSI5NCIgd2lkdGg9IjE1NiIgaGVpZ2h0PSI4IiBmaWxsPSIjNDMzOGNhIi8+PHRleHQgeD0iNDAzIiB5PSI5NSIgZm9udC1mYW1pbHk9InVpLW1vbm9zcGFjZSxTRk1vbm8tUmVndWxhcixNZW5sbyxtb25vc3BhY2UiIGZvbnQtc2l6ZT0iMTIiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiNmZmYiPnJ1c3RjIOe8luivkTwvdGV4dD48dGV4dCB4PSI0MDMiIHk9IjExNyIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMC41IiBmaWxsPSIjMWUyOTNiIj7moLjlv4PmqKHlnZc8L3RleHQ+PHRleHQgeD0iNDAzIiB5PSIxMzIiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTAuNSIgZmlsbD0iIzFlMjkzYiI+d2FzbTMyLXdhc2lwMTwvdGV4dD48L2c+PGc+PHJlY3QgeD0iNTc5IiB5PSI3OCIgd2lkdGg9IjE1NiIgaGVpZ2h0PSI4MiIgcng9IjgiIGZpbGw9IiNmMGZkZmEiIHN0cm9rZT0iIzBkOTQ4OCIgc3Ryb2tlLXdpZHRoPSIxLjciLz48cmVjdCB4PSI1NzkiIHk9Ijc4IiB3aWR0aD0iMTU2IiBoZWlnaHQ9IjI0IiByeD0iOCIgZmlsbD0iIzBkOTQ4OCIvPjxyZWN0IHg9IjU3OSIgeT0iOTQiIHdpZHRoPSIxNTYiIGhlaWdodD0iOCIgZmlsbD0iIzBkOTQ4OCIvPjx0ZXh0IHg9IjU5MCIgeT0iOTUiIGZvbnQtZmFtaWx5PSJ1aS1tb25vc3BhY2UsU0ZNb25vLVJlZ3VsYXIsTWVubG8sbW9ub3NwYWNlIiBmb250LXNpemU9IjEyIiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjZmZmIj7pgILphY0g4oaSIOe7hOS7tjwvdGV4dD48dGV4dCB4PSI1OTAiIHk9IjExNyIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMC41IiBmaWxsPSIjMWUyOTNiIj5hZGFwdGVyIOWwgeijhTwvdGV4dD48dGV4dCB4PSI1OTAiIHk9IjEzMiIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMC41IiBmaWxsPSIjMWUyOTNiIj5XQVNJcDIgLndhc208L3RleHQ+PC9nPjxnPjxyZWN0IHg9Ijc2NiIgeT0iNzgiIHdpZHRoPSIxNTYiIGhlaWdodD0iODIiIHJ4PSI4IiBmaWxsPSIjZjFmNWY5IiBzdHJva2U9IiM0NzU1NjkiIHN0cm9rZS13aWR0aD0iMS43Ii8+PHJlY3QgeD0iNzY2IiB5PSI3OCIgd2lkdGg9IjE1NiIgaGVpZ2h0PSIyNCIgcng9IjgiIGZpbGw9IiM0NzU1NjkiLz48cmVjdCB4PSI3NjYiIHk9Ijk0IiB3aWR0aD0iMTU2IiBoZWlnaHQ9IjgiIGZpbGw9IiM0NzU1NjkiLz48dGV4dCB4PSI3NzciIHk9Ijk1IiBmb250LWZhbWlseT0idWktbW9ub3NwYWNlLFNGTW9uby1SZWd1bGFyLE1lbmxvLG1vbm9zcGFjZSIgZm9udC1zaXplPSIxMiIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iI2ZmZiI+5a6/5Li75Yqg6L29PC90ZXh0Pjx0ZXh0IHg9Ijc3NyIgeT0iMTE3IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwLjUiIGZpbGw9IiMxZTI5M2IiPldhc210aW1lPC90ZXh0Pjx0ZXh0IHg9Ijc3NyIgeT0iMTMyIiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwLjUiIGZpbGw9IiMxZTI5M2IiPmJpbmRnZW4hIOiwg+eUqDwvdGV4dD48L2c+PGc+PHBhdGggZD0iTSAxNzQgMTE5IEwgMjA1IDExOSIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjNjQ3NDhiIiBzdHJva2Utd2lkdGg9IjEuNiIgc3Ryb2tlLWRhc2hhcnJheT0iNSAzIiBtYXJrZXItZW5kPSJ1cmwoI2EpIi8+PC9nPjxnPjxwYXRoIGQ9Ik0gMzYxIDExOSBMIDM5MiAxMTkiIGZpbGw9Im5vbmUiIHN0cm9rZT0iIzY0NzQ4YiIgc3Ryb2tlLXdpZHRoPSIxLjYiIHN0cm9rZS1kYXNoYXJyYXk9IjUgMyIgbWFya2VyLWVuZD0idXJsKCNhKSIvPjwvZz48Zz48cGF0aCBkPSJNIDU0OCAxMTkgTCA1NzkgMTE5IiBmaWxsPSJub25lIiBzdHJva2U9IiM2NDc0OGIiIHN0cm9rZS13aWR0aD0iMS42IiBzdHJva2UtZGFzaGFycmF5PSI1IDMiIG1hcmtlci1lbmQ9InVybCgjYSkiLz48L2c+PGc+PHBhdGggZD0iTSA3MzUgMTE5IEwgNzY2IDExOSIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjNjQ3NDhiIiBzdHJva2Utd2lkdGg9IjEuNiIgc3Ryb2tlLWRhc2hhcnJheT0iNSAzIiBtYXJrZXItZW5kPSJ1cmwoI2EpIi8+PC9nPjx0ZXh0IHg9IjQ3MCIgeT0iMjA1IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEyLjUiIGZpbGw9IiMzMzQxNTUiPmNhcmdvIGNvbXBvbmVudCBidWlsZCDmiorov5nmnaHmtYHmsLTnur/kuIDplK7ot5HlrozvvIzkuqfnianmmK/lj6/ooqvnrKzlha3oioLlrr/kuLvnm7TmjqXliqDovb3nmoTnu4Tku7Y8L3RleHQ+PC9zdmc+"></p>

### 7.1 两条路线

| 路线 | bindings 从哪来 | 适合 |
|---|---|---|
| **`cargo component`** | 生成进 `src/bindings.rs`，按 `Cargo.toml` 解析的依赖对齐 | 标准工程，推荐 |
| **`wit-bindgen` 宏** | 源码里 `generate!` 宏内联展开 | 想少一层工具 / 单文件 demo |

先讲用户点名的 `cargo component`。

### 7.2 装工具、起项目

```bash
cargo install cargo-component wasm-tools
cargo component new --lib calculator   # --lib = reactor 组件（库，无 _start）
cd calculator
```

`--lib` 造的是 **reactor（库）组件**：只导出接口、没有 `main`/`_start`，供宿主按需调用——正是插件想要的形态。省掉 `--lib` 则是 **command 组件**（有入口，像个可执行程序）。

### 7.3 放 WIT

把第六节那份 WIT 存到 `wit/world.wit`：

```wit
package example:calc;

world calculator {
  export add: func(a: s32, b: s32) -> s32;   // 客户机实现
  import log: func(msg: string);             // 宿主提供
}
```

`cargo component new` 会在 `Cargo.toml` 里生成大致这样的元数据（一般不用手写）：

```toml
[package.metadata.component]
package = "example:calc"

[package.metadata.component.target]
path = "wit"
world = "calculator"
```

### 7.4 写实现（`src/lib.rs`）

```rust
#[allow(warnings)]
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
bindings::export!(Component with_types_in bindings);
```

**最容易踩的坑 —— `Guest` trait 落在哪个模块**：

- 函数**直接从 world 导出**（本例的 `add`）→ 顶层 `bindings::Guest`。
- 若导出的是一个**具名 interface**（如 `export calc: interface { add: ... }`）→ trait 落到 `bindings::exports::example::calc::calc::Guest`，`export!` 的目标路径也随之变深。**报错「找不到 Guest」十有八九是这里。**
- world 级的 `import log` 则生成为可直接调用的自由函数 `bindings::log(&str)`。

### 7.5 编译 + 验证

```bash
cargo component build --release
# 产物是「真·组件」而非核心模块（当前经 wasm32-wasip1 适配为 p2）
ls target/wasm32-wasip1/release/calculator.wasm

# 用 wasm-tools 确认它确实是组件、接口对得上
wasm-tools component wit target/wasm32-wasip1/release/calculator.wasm
# 应打印：world calculator { export add: ...; import log: ...; }
```

> `wasm-tools component wit <file>` 能打印出 WIT，就证明产物是合法组件（而非核心模块）—— 这是客户机侧最实用的一条自检。

### 7.6 闭环：交给第六节的宿主跑

把 `calculator.wasm` 喂给第六节那段 `bindgen!` + `Calculator::instantiate` 的宿主代码：宿主实现 `CalculatorImports::log`，调 `bindings.call_add(&mut store, 2, 3)?` 得 `5`，同时客户机里的 `log` 会回调进宿主打印。宿主 ↔ 客户机两侧就此对上，一个完整的组件调用闭环成立。

### 7.7 wit-bindgen 宏路线（对照）

不想用 cargo component、想单文件搞定，可直接在库里内联生成：

```rust
wit_bindgen::generate!({
    world: "calculator",        // 读相邻 wit/ 目录；也可用 inline: r#"...WIT..."#
});

struct Component;

impl Guest for Component {
    fn add(a: i32, b: i32) -> i32 {
        log(&format!("computing {a} + {b}"));   // 宏在当前作用域直接生成 log()
        a + b
    }
}

export!(Component);
```

`Cargo.toml` 里 `crate-type = ["cdylib"]`、依赖 `wit-bindgen`，再 `cargo build --target wasm32-wasip2 --release` 即可。两条路线产出的组件，宿主侧用法完全一样。

> **版本提醒**：`cargo component` / `wit-bindgen` 目前仍是 `0.x`，`generate!` 的配置键、`export!` 写法、cargo component 的生成模板都会随小版本调整。`export!(T with_types_in bindings)` 是近期写法；很老的模板可能自动接线或用宏内 `exports:` 键。以 `wit_bindgen::generate!` 的 docs.rs 与 `cargo component new` 实际生成的模板为准。

## 八、资源治理与安全沙箱

跑不可信代码，必须能**掐住 CPU、内存、栈、时间**。wasmtime 给了四道可组合的闸门：

<p align="center"><img alt="图4：资源治理四闸门" style="max-width:100%;height:auto;border:1px solid #e8eef5;border-radius:10px" src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA5NDAgMzgwIiB3aWR0aD0iOTQwIiBoZWlnaHQ9IjM4MCIgcm9sZT0iaW1nIj48ZGVmcz48bWFya2VyIGlkPSJhIiB2aWV3Qm94PSIwIDAgMTAgMTAiIHJlZlg9IjguNSIgcmVmWT0iNSIgbWFya2VyV2lkdGg9IjciIG1hcmtlckhlaWdodD0iNyIgb3JpZW50PSJhdXRvLXN0YXJ0LXJldmVyc2UiPjxwYXRoIGQ9Ik0gMCAwIEwgMTAgNSBMIDAgMTAgeiIgZmlsbD0iIzY0NzQ4YiIvPjwvbWFya2VyPjwvZGVmcz48cmVjdCB3aWR0aD0iOTQwIiBoZWlnaHQ9IjM4MCIgZmlsbD0iI2ZiZmRmZiIvPjxjaXJjbGUgY3g9IjQ3MCIgY3k9IjE4NSIgcj0iNzQiIGZpbGw9IiNmZmZiZWIiIHN0cm9rZT0iI2I0NTMwOSIgc3Ryb2tlLXdpZHRoPSIyIi8+PHRleHQgeD0iNDcwIiB5PSIxNzkiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtZmFtaWx5PSJ1aS1tb25vc3BhY2UsU0ZNb25vLVJlZ3VsYXIsTWVubG8sbW9ub3NwYWNlIiBmb250LXNpemU9IjE0IiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjYjQ1MzA5Ij7ov5DooYzkuK3nmoQ8L3RleHQ+PHRleHQgeD0iNDcwIiB5PSIyMDEiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtZmFtaWx5PSJ1aS1tb25vc3BhY2UsU0ZNb25vLVJlZ3VsYXIsTWVubG8sbW9ub3NwYWNlIiBmb250LXNpemU9IjE0IiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjYjQ1MzA5Ij5HdWVzdDwvdGV4dD48Zz48cmVjdCB4PSI0MCIgeT0iNDAiIHdpZHRoPSIyNTAiIGhlaWdodD0iNzgiIHJ4PSI4IiBmaWxsPSIjZjBmZGZhIiBzdHJva2U9IiMwZDk0ODgiIHN0cm9rZS13aWR0aD0iMS43Ii8+PHJlY3QgeD0iNDAiIHk9IjQwIiB3aWR0aD0iMjUwIiBoZWlnaHQ9IjI0IiByeD0iOCIgZmlsbD0iIzBkOTQ4OCIvPjxyZWN0IHg9IjQwIiB5PSI1NiIgd2lkdGg9IjI1MCIgaGVpZ2h0PSI4IiBmaWxsPSIjMGQ5NDg4Ii8+PHRleHQgeD0iNTEiIHk9IjU3IiBmb250LWZhbWlseT0idWktbW9ub3NwYWNlLFNGTW9uby1SZWd1bGFyLE1lbmxvLG1vbm9zcGFjZSIgZm9udC1zaXplPSIxMiIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iI2ZmZiI+RnVlbCDnh4Pmlpk8L3RleHQ+PHRleHQgeD0iNTEiIHk9Ijc5IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwLjUiIGZpbGw9IiMxZTI5M2IiPmNvbnN1bWVfZnVlbCh0cnVlKTwvdGV4dD48dGV4dCB4PSI1MSIgeT0iOTQiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTAuNSIgZmlsbD0iIzFlMjkzYiI+c2V0X2Z1ZWwgLyBnZXRfZnVlbCDCtyDnoa7lrprmgKforqHph488L3RleHQ+PC9nPjxnPjxyZWN0IHg9IjY1MCIgeT0iNDAiIHdpZHRoPSIyNTAiIGhlaWdodD0iNzgiIHJ4PSI4IiBmaWxsPSIjZWVmMmZmIiBzdHJva2U9IiM0MzM4Y2EiIHN0cm9rZS13aWR0aD0iMS43Ii8+PHJlY3QgeD0iNjUwIiB5PSI0MCIgd2lkdGg9IjI1MCIgaGVpZ2h0PSIyNCIgcng9IjgiIGZpbGw9IiM0MzM4Y2EiLz48cmVjdCB4PSI2NTAiIHk9IjU2IiB3aWR0aD0iMjUwIiBoZWlnaHQ9IjgiIGZpbGw9IiM0MzM4Y2EiLz48dGV4dCB4PSI2NjEiIHk9IjU3IiBmb250LWZhbWlseT0idWktbW9ub3NwYWNlLFNGTW9uby1SZWd1bGFyLE1lbmxvLG1vbm9zcGFjZSIgZm9udC1zaXplPSIxMiIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iI2ZmZiI+RXBvY2gg5pe25LujPC90ZXh0Pjx0ZXh0IHg9IjY2MSIgeT0iNzkiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTAuNSIgZmlsbD0iIzFlMjkzYiI+ZXBvY2hfaW50ZXJydXB0aW9uKHRydWUpPC90ZXh0Pjx0ZXh0IHg9IjY2MSIgeT0iOTQiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTAuNSIgZmlsbD0iIzFlMjkzYiI+6K6h5pe257q/56iLIGluY3JlbWVudF9lcG9jaCDCtyDlv6sgMi0zeDwvdGV4dD48L2c+PGc+PHJlY3QgeD0iNDAiIHk9IjI1MCIgd2lkdGg9IjI1MCIgaGVpZ2h0PSI5MCIgcng9IjgiIGZpbGw9IiNmNWYzZmYiIHN0cm9rZT0iIzdjM2FlZCIgc3Ryb2tlLXdpZHRoPSIxLjciLz48cmVjdCB4PSI0MCIgeT0iMjUwIiB3aWR0aD0iMjUwIiBoZWlnaHQ9IjI0IiByeD0iOCIgZmlsbD0iIzdjM2FlZCIvPjxyZWN0IHg9IjQwIiB5PSIyNjYiIHdpZHRoPSIyNTAiIGhlaWdodD0iOCIgZmlsbD0iIzdjM2FlZCIvPjx0ZXh0IHg9IjUxIiB5PSIyNjciIGZvbnQtZmFtaWx5PSJ1aS1tb25vc3BhY2UsU0ZNb25vLVJlZ3VsYXIsTWVubG8sbW9ub3NwYWNlIiBmb250LXNpemU9IjEyIiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjZmZmIj5TdG9yZUxpbWl0czwvdGV4dD48dGV4dCB4PSI1MSIgeT0iMjg5IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwLjUiIGZpbGw9IiMxZTI5M2IiPlN0b3JlTGltaXRzQnVpbGRlciDihpIgbGltaXRlcigpPC90ZXh0Pjx0ZXh0IHg9IjUxIiB5PSIzMDQiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTAuNSIgZmlsbD0iIzFlMjkzYiI+57q/5oCn5YaF5a2YIC8g5a6e5L6LIC8g6KGoIOS4iumZkDwvdGV4dD48L2c+PGc+PHJlY3QgeD0iNjUwIiB5PSIyNTAiIHdpZHRoPSIyNTAiIGhlaWdodD0iOTAiIHJ4PSI4IiBmaWxsPSIjZjFmNWY5IiBzdHJva2U9IiM0NzU1NjkiIHN0cm9rZS13aWR0aD0iMS43Ii8+PHJlY3QgeD0iNjUwIiB5PSIyNTAiIHdpZHRoPSIyNTAiIGhlaWdodD0iMjQiIHJ4PSI4IiBmaWxsPSIjNDc1NTY5Ii8+PHJlY3QgeD0iNjUwIiB5PSIyNjYiIHdpZHRoPSIyNTAiIGhlaWdodD0iOCIgZmlsbD0iIzQ3NTU2OSIvPjx0ZXh0IHg9IjY2MSIgeT0iMjY3IiBmb250LWZhbWlseT0idWktbW9ub3NwYWNlLFNGTW9uby1SZWd1bGFyLE1lbmxvLG1vbm9zcGFjZSIgZm9udC1zaXplPSIxMiIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iI2ZmZiI+bWF4X3dhc21fc3RhY2s8L3RleHQ+PHRleHQgeD0iNjYxIiB5PSIyODkiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTAuNSIgZmlsbD0iIzFlMjkzYiI+Q29uZmlnOjptYXhfd2FzbV9zdGFjazwvdGV4dD48dGV4dCB4PSI2NjEiIHk9IjMwNCIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMC41IiBmaWxsPSIjMWUyOTNiIj7lrqLmiLfmnLrosIPnlKjmoIjkuIrpmZDvvIzpmLLmt7HpgJLlvZI8L3RleHQ+PC9nPjxnPjxwYXRoIGQ9Ik0gMjkwIDkwIEwgNDAwIDE1MCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjNjQ3NDhiIiBzdHJva2Utd2lkdGg9IjEuNiIgc3Ryb2tlLWRhc2hhcnJheT0iNSAzIiBtYXJrZXItZW5kPSJ1cmwoI2EpIi8+PC9nPjxnPjxwYXRoIGQ9Ik0gNjUwIDkwIEwgNTQwIDE1MCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjNjQ3NDhiIiBzdHJva2Utd2lkdGg9IjEuNiIgc3Ryb2tlLWRhc2hhcnJheT0iNSAzIiBtYXJrZXItZW5kPSJ1cmwoI2EpIi8+PC9nPjxnPjxwYXRoIGQ9Ik0gMjkwIDI5MCBMIDQwNSAyMjAiIGZpbGw9Im5vbmUiIHN0cm9rZT0iIzY0NzQ4YiIgc3Ryb2tlLXdpZHRoPSIxLjYiIHN0cm9rZS1kYXNoYXJyYXk9IjUgMyIgbWFya2VyLWVuZD0idXJsKCNhKSIvPjwvZz48Zz48cGF0aCBkPSJNIDY1MCAyOTAgTCA1MzUgMjIwIiBmaWxsPSJub25lIiBzdHJva2U9IiM2NDc0OGIiIHN0cm9rZS13aWR0aD0iMS42IiBzdHJva2UtZGFzaGFycmF5PSI1IDMiIG1hcmtlci1lbmQ9InVybCgjYSkiLz48L2c+PHRleHQgeD0iNDcwIiB5PSIzNzIiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTIuNSIgZmlsbD0iIzMzNDE1NSI+5Zub6YGT6Ze46Zeo5Y+v57uE5ZCI44CC5rOo5oSP77yaZnVlbC9lcG9jaCDlj6rmjpDjgIzov5DooYzkuK3nmoQgd2FzbeOAje+8jOWuouaIt+acuumYu+WhnuWcqOWuv+S4u+iwg+eUqOmHjOaXtuS4pOiAhemDveS4jeeUn+aViDwvdGV4dD48L3N2Zz4="></p>

### 7.1 Fuel —— 确定性计量

每条 wasm 指令消耗「燃料」，耗尽即 trap。**确定性**：同样输入必然在同一点停下，适合可复现、可计费场景。

```rust
let mut config = Config::new();
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
let used = 5_000_000 - store.get_fuel()?;    // 实际消耗，可用于计费
```

### 7.2 Epoch —— 计时器抢占（快，但非确定）

客户机只检查一个全局计数器，宿主用**独立线程 / 定时器**递增它，到点 trap。比 fuel **快 2–3 倍**（几乎零开销），代价是非确定：同样输入可能在不同位置被打断。做**墙钟超时**首选。

```rust
let mut config = Config::new();
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
// 长时间运行的 wasm 到点会以 Trap::Interrupt 中止
```

> **共同盲区**：fuel 和 epoch 都**只管运行中的 wasm**。若客户机阻塞在一次宿主调用里（比如宿主函数在等 IO），两者都叫不醒它——超时得由宿主自己在那次调用上做。另：epoch 与 Winch 基线编译器不兼容。

### 7.3 内存 / 实例 / 栈上限

```rust
use wasmtime::{StoreLimits, StoreLimitsBuilder};

struct Host { limits: StoreLimits }

let mut config = Config::new();
config.max_wasm_stack(512 * 1024);          // 客户机调用栈上限，防深递归打爆

let limits = StoreLimitsBuilder::new()
    .memory_size(64 << 20)                  // 单 Store 线性内存 ≤ 64 MiB
    .instances(1)
    .tables(1)
    .build();
let mut store = Store::new(&engine, Host { limits });
store.limiter(|h| &mut h.limits);           // 把 limiter 接到宿主数据
```

需要**动态**上限（按租户配额实时判断）时，自己实现 `ResourceLimiter` trait，在 `memory_growing`/`table_growing` 回调里裁决。

### 7.4 沙箱纪律（安全清单）

- **以非 root、非 superuser 的最小权限进程**跑宿主；wasm 沙箱防的是客户机，不是宿主自己的漏洞。
- **能力最小化**：WASI 只 `preopen` 必要目录，socket 默认已禁；宿主函数只暴露必需的。
- **给每个不可信调用配 fuel 或 epoch + 内存上限 + 栈上限**，三件套齐全。
- **别把裸 SQL / 原始连接 / 任意文件句柄递进沙箱**——那等于把沙箱门拆了（本仓 `cmx-container` 的硬约束正是此意）。

## 九、异步执行

要在一个 async 运行时里**并发跑成百上千个客户机**、或让宿主导入函数 `.await`，开 `async_support`：

```rust
let mut config = Config::new();
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
run.call_async(&mut store, ()).await?;
```

**关键**：wasm 本身是同步 CPU 流，不会主动让出。要**协作式抢占**（不让一个死循环客户机饿死 executor），把 epoch 或 fuel 接成「让出」而非「trap」：

- `store.epoch_deadline_async_yield_and_update(delta)`：到期让出 future（返回 `Pending` 并自唤醒），恢复时续期——多个 CPU 密集客户机就能在一个 executor 上时间片轮转。
- `store.fuel_async_yield_interval(Some(n))`：每消耗 n 燃料让出一次。

> 每个 async 调用会占一个执行栈；高并发下配合 pooling 分配器的 `total_stacks` 一起调。

## 十、性能：AOT 预编译 · 缓存 · Pooling 分配器

三板斧，把「编译贵、实例化频繁」这对矛盾拆开。

### 9.1 AOT：把编译挪到构建期

运行时 `Module::new` 每次都重编译。生产应当**构建期编译成 `.cwasm`，上线只加载**：

```rust
// —— 构建期（离线，一次）——
let engine = Engine::default();
let cwasm: Vec<u8> = engine.precompile_module(&wasm_bytes)?;   // 或 CLI: wasmtime compile
std::fs::write("app.cwasm", &cwasm)?;

// —— 服务期（每进程启动）——
let engine = Engine::default();
// SAFETY: 字节必须来自「可信、且与本 wasmtime 版本兼容」的构建产物；
//         对任意/不可信字节做 deserialize 是未定义行为。
let module = unsafe { Module::deserialize_file(&engine, "app.cwasm")? };
```

> `deserialize*` 是 `unsafe`：它**信任**字节是本引擎产的、没被篡改。`.cwasm` 只跟兼容的 wasmtime 版本 + 目标架构匹配；跨平台预编译要开 `all-arch` 特性并设 `Config::target`。

### 9.2 编译缓存（v47 新 API）

> **v47 变化**：旧 `config.cache_config_load_default()` 已废弃，改用 `Cache` 类型 + `config.cache(...)`（需 `cache` 特性）。

```rust
use wasmtime::{Config, Cache, CacheConfig};

let mut config = Config::new();

// 等价于旧 cache_config_load_default()：加载系统默认磁盘缓存配置
let cache = Cache::from_file(None)?;             // None=系统默认路径；Some(path)=指定文件
config.cache(Some(cache));
// 或程序化默认：Cache::new(CacheConfig::new())?
let engine = Engine::new(&config)?;
```

缓存命中时，相同 wasm 不再重编译——对「同一模块反复冷启动」的开发/CI 很有用；生产更推荐上面的 AOT。

### 9.3 Pooling 分配器：把实例化压到微秒

默认 `OnDemand` 每次实例化都向 OS 要内存/表。**Pooling** 预先开好一大池资源，实例化只是「从池里取一格」，配合**写时复制（COW）** 初始化线性内存，实例化成本可降一到两个数量级——Serverless / 高并发多租户的标配。

```rust
use wasmtime::{Config, Engine, InstanceAllocationStrategy, PoolingAllocationConfig};

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
let engine = Engine::new(&config)?;
```

> Pooling 会**预留一大片进程地址空间**（用来省掉内存边界检查），换来的是极快、可预测的实例化。它**不影响编译产物**，`.cwasm` 用不用 pooling 都能加载。需 `pooling-allocator` 特性（默认开）。

## 十一、生产落地模式

把前面的原则拼成一套可抄的骨架（多租户插件服务）：

```rust
// 进程级：一次建好，长期持有
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
}   // store 在此 drop，本次实例的全部资源回收
```

对照本仓的落地约束（`CLAUDE.md` §八「集群无状态」、`cmx-container` 插件平台）：

- **`Engine` / `Module` / `Linker` 是只读共享的**——符合「禁用 Mutex 缓存业务数据，但连接池 / 只读配置除外」：它们正是只读配置类，可长持有。
- **`Store` 每请求新建、不跨线程、用完即弃**——天然契合无状态进程；状态外置（Redis / 库），别把业务态攒在长命 Store 里。
- **别给不可信插件原始 SQL / 任意句柄**——`cmx-container` 硬约束与 wasmtime 能力模型是同一条底线：能力显式授予，默认拒绝。

## 十二、常见坑

| 坑 | 症状 | 正解 |
|---|---|---|
| 复用长命 `Store` 攒实例 | 内存持续上涨不回落 | Store 内存只增不减，**每请求新建**、用完 drop |
| 跨线程共享 `Store` | 编译不过 / 数据竞争 | Store `!Sync`；跨线程共享的是 `Engine`/`Module` |
| 每次请求都 `Module::new` | CPU 全耗在编译 | 编译一次缓存 `Module`，或 AOT `.cwasm` |
| 开了 epoch 没设 deadline | 一运行就 `Trap::Interrupt` | 运行前必须 `set_epoch_deadline(n)` |
| 指望 fuel/epoch 打断宿主阻塞 | 卡在宿主 IO 里超时不生效 | 两者只管运行中的 wasm；宿主调用自己做超时 |
| 用了旧 `IoView` / `preview2::` 路径 | v47 编译报找不到符号 | 用 `WasiCtxView` + `wasmtime_wasi::p2::` |
| `deserialize` 喂不可信字节 | UB / 崩溃 | 只 deserialize 自己可信构建的 `.cwasm` |
| 忘了给 stdout 就 `println!` | 客户机无输出 / 报错 | `WasiCtxBuilder::inherit_stdio()` |
| Winch + epoch | 配置报错 | epoch 与 Winch 不兼容，用 Cranelift |

## 十三、版本迁移对照 & Cargo features

### 从旧版本迁移（→ v47）

| 旧 API | v47 现行 |
|---|---|
| `config.cache_config_load_default()` | `config.cache(Some(Cache::from_file(None)?))` |
| `store.add_fuel(n)` / `fuel_consumed()` | `store.set_fuel(n)?` / `store.get_fuel()?` |
| `IoView` trait + `table()` 方法 | 已删除；`WasiView::ctx() -> WasiCtxView{ctx, table}` |
| `wasmtime_wasi::preview2::add_to_linker_*` | `wasmtime_wasi::p2::add_to_linker_*` |
| WASI 默认可建 socket | **默认禁 TCP/UDP**，需显式放开 |

### 常用 Cargo features（`wasmtime`）

| feature | 作用 | 默认 |
|---|---|---|
| `cranelift` | 优化编译器（生产用） | ✅ |
| `component-model` | 组件模型 + WASIp2 | ✅ |
| `async` | 异步执行 / `call_async` | ✅ |
| `pooling-allocator` | Pooling 分配器 | ✅ |
| `cache` | 编译缓存 `Cache` 类型 | ✅ |
| `parallel-compilation` | 并行编译大模块 | ✅ |
| `winch` | 基线快速编译器（编译快、无 epoch） | ❌ |
| `all-arch` | 跨架构 AOT 预编译 | ❌ |

最小化体积 / 无 JIT 部署（只跑 `.cwasm`）可关掉 `cranelift`，只留 runtime——用 `default-features = false` 精挑。

---

### 一句话收束

> **`Engine`/`Module` 编译一次、跨线程共享；`Store` 每请求新建、用完即弃；跑不可信代码就 fuel/epoch + 内存/栈上限三件套齐全；新项目走组件模型 + WASIp2。** 记住这三句，wasmtime 的九成用法就对了。

> 参考：wasmtime 47.x 官方文档（docs.wasmtime.dev / docs.rs），本文 API 以 2026-07 发布线为准。