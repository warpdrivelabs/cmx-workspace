# Rust Arena（内存竞技场 / 区域分配器）模式详解与实现对比

> **Arena**（竞技场 / 区域分配器 / region allocator）是一种「**批量分配、统一释放**」的内存管理模式：从一块预留内存里飞快地划出对象，**不单独归还**，等整个 arena 生命周期结束时一次性释放。它在 Rust 中尤其重要——既是高性能内存管理手段，也是**绕开借用检查器、优雅建模图/树/自引用结构**的惯用法（用索引句柄或统一生命周期引用替代 `Rc<RefCell<T>>`）。
>
> 本报告说明 Arena 的作用与原理，系统对比生态中的主流实现（typed-arena / bumpalo / blink-alloc / bump-scope / id-arena / generational-arena / slotmap / slab / thunderdome / la-arena / elsa 等），给出特性矩阵、定位象限、性能视角与选型决策树，并延伸到标准库现状与 rustc 自带 arena。
>
> **时效声明**：事实核实于 **2026 年 9 月**（版本号/许可证取自 crates.io 与各仓源码）。版本号会持续变动，请以 crates.io 为准；`allocator_api` 稳定化状态等易变项文中已标注。图形为内嵌 base64 SVG（`<img>` 标签），单文件自包含，可离线用浏览器或支持 HTML 的 Markdown 阅读器打开。

---

## 目录

1. [什么是 Arena？它解决什么问题](#1-什么是-arena它解决什么问题)
2. [Bump 分配的工作原理](#2-bump-分配的工作原理)
3. [Arena 如何化解「图 / 自引用」难题](#3-arena-如何化解图--自引用难题)
4. [两大流派总览](#4-两大流派总览)
5. [逐一详解（含代码示例）](#5-逐一详解含代码示例)
6. [特性能力矩阵](#6-特性能力矩阵)
7. [选型定位象限图](#7-选型定位象限图)
8. [性能视角](#8-性能视角)
9. [横向对比总表](#9-横向对比总表)
10. [选型决策树](#10-选型决策树)
11. [常见陷阱与最佳实践](#11-常见陷阱与最佳实践)
12. [进阶：标准库与 rustc 的 arena](#12-进阶标准库与-rustc-的-arena)
13. [结论与建议](#13-结论与建议)
14. [参考资料](#14-参考资料)

---

## 1. 什么是 Arena？它解决什么问题

传统的 `malloc`/`free`（Rust 里是全局分配器 + 每个 `Box`/`Vec` 各自分配）对**每一个对象**都要记账、可能加锁、容易碎片化；释放时还要**逐个**归还与析构。Arena 反其道而行：

> **一次预留一大块内存，之后用「指针递增」飞快地划分对象；不支持单独释放；整个 arena 丢弃时把所有内存一次性还给系统。**

Arena 主要解决**两类核心问题**（两者常常同时成立）：

1. **分配性能 + 批量释放 + 局部性**。大量「同生命周期的短命对象」——编译器一趟 pass 产生的 AST 节点、一次请求处理中的临时对象、游戏每帧的临时数据——用 arena 分配几乎零开销（指针 += size），用完整块扔掉，无需逐个 `free`，且对象在内存里连续，**缓存友好**。

2. **绕过借用检查器，建模图 / 树 / 自引用结构**。Rust 的所有权模型让「相互引用的节点」很难表达，传统做法 `Rc<RefCell<T>>` 既有运行时开销、又易因环而泄漏、还啰嗦。Arena 提供两种干净的替代：让所有节点**同属一个 arena（统一生命周期）**，彼此用 `&'arena T` 引用；或更常见地，用 **`Vec` 下标 / 代际句柄**当「指针」。这一思路的权威源头是 Niko Matsakis 的《Modeling graphs in Rust using vector indices》。

> 实证：Rust 编译器 `rustc` 大量使用自带的 `rustc_arena`；rust-analyzer 用自研 `la-arena`（`Arena<T>` + `Idx<T>`）以索引替代 `Rc`/`RefCell`。

---

## 2. Bump 分配的工作原理

<p align="center">
<img alt="Bump 分配原理" style="width:100%;max-width:900px;height:auto;" src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA5MDAgNTAwIiBmb250LWZhbWlseT0iJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJywnU2Vnb2UgVUknLHNhbnMtc2VyaWYiPgogIDxkZWZzPgogICAgPG1hcmtlciBpZD0iYXIiIG1hcmtlcldpZHRoPSIxMCIgbWFya2VySGVpZ2h0PSIxMCIgcmVmWD0iOCIgcmVmWT0iMyIgb3JpZW50PSJhdXRvIj48cGF0aCBkPSJNMCwwIEw4LDMgTDAsNiBaIiBmaWxsPSIjMzM0MTU1Ii8+PC9tYXJrZXI+CiAgICA8bWFya2VyIGlkPSJhcmIiIG1hcmtlcldpZHRoPSIxMSIgbWFya2VySGVpZ2h0PSIxMSIgcmVmWD0iOCIgcmVmWT0iMy41IiBvcmllbnQ9ImF1dG8iPjxwYXRoIGQ9Ik0wLDAgTDksMy41IEwwLDcgWiIgZmlsbD0iIzI1NjNlYiIvPjwvbWFya2VyPgogIDwvZGVmcz4KICA8cmVjdCB3aWR0aD0iOTAwIiBoZWlnaHQ9IjUwMCIgZmlsbD0iI2Y4ZmFmYyIvPgogIDx0ZXh0IHg9IjQ1MCIgeT0iMzQiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtc2l6ZT0iMjQiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiMwZjE3MmEiPkJ1bXDvvIjmjIfpkojpgJLlop7vvInliIbphY3ljp/nkIY8L3RleHQ+CgogIDwhLS0gUGFuZWwgQTogYXJlbmEgYnVtcCAtLT4KICA8cmVjdCB4PSIyNiIgeT0iNTYiIHdpZHRoPSI4NDgiIGhlaWdodD0iMjE2IiByeD0iMTIiIGZpbGw9IiNmZmZmZmYiIHN0cm9rZT0iIzI1NjNlYiIgc3Ryb2tlLXdpZHRoPSIxLjYiLz4KICA8dGV4dCB4PSI0NiIgeT0iODQiIGZvbnQtc2l6ZT0iMTYiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiMxZTNhOGEiPkFyZW5h77ya5LiA5aSn5Z2X5YaF5a2YICsg5LiA5LiqIGJ1bXAg5oyH6ZKIPC90ZXh0PgoKICA8IS0tIGNodW5rIDEgLS0+CiAgPHRleHQgeD0iNjAiIHk9IjExMiIgZm9udC1zaXplPSIxMSIgZmlsbD0iIzY0NzQ4YiI+Q2h1bmsgMe+8iOmihOWIhumFjeWkp+Wdl++8iTwvdGV4dD4KICA8cmVjdCB4PSI2MCIgeT0iMTE4IiB3aWR0aD0iNTYwIiBoZWlnaHQ9IjUwIiByeD0iNCIgZmlsbD0iI2VmZjZmZiIgc3Ryb2tlPSIjOTNjNWZkIi8+CiAgPHJlY3QgeD0iNjAiIHk9IjExOCIgd2lkdGg9IjkwIiAgaGVpZ2h0PSI1MCIgZmlsbD0iIzYwYTVmYSIvPjx0ZXh0IHg9IjEwNSIgeT0iMTQ4IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LXNpemU9IjEzIiBmaWxsPSIjZmZmIj5BPC90ZXh0PgogIDxyZWN0IHg9IjE1MCIgeT0iMTE4IiB3aWR0aD0iMTMwIiBoZWlnaHQ9IjUwIiBmaWxsPSIjM2I4MmY2Ii8+PHRleHQgeD0iMjE1IiB5PSIxNDgiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtc2l6ZT0iMTMiIGZpbGw9IiNmZmYiPkI8L3RleHQ+CiAgPHJlY3QgeD0iMjgwIiB5PSIxMTgiIHdpZHRoPSI4MCIgIGhlaWdodD0iNTAiIGZpbGw9IiMyNTYzZWIiLz48dGV4dCB4PSIzMjAiIHk9IjE0OCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1zaXplPSIxMyIgZmlsbD0iI2ZmZiI+QzwvdGV4dD4KICA8dGV4dCB4PSI0OTAiIHk9IjE0OCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1zaXplPSIxMiIgZmlsbD0iIzk0YTNiOCI+5pyq5L2/55So77yIZnJlZe+8iTwvdGV4dD4KCiAgPCEtLSBidW1wIHBvaW50ZXIgLS0+CiAgPGxpbmUgeDE9IjM2MCIgeTE9IjE4NiIgeDI9IjM2MCIgeTI9IjE3MCIgc3Ryb2tlPSIjMjU2M2ViIiBzdHJva2Utd2lkdGg9IjIiIG1hcmtlci1lbmQ9InVybCgjYXJiKSIvPgogIDx0ZXh0IHg9IjM2MCIgeT0iMjAyIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LXNpemU9IjExIiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjMjU2M2ViIj5idW1wIOaMh+mSiO+8iOS4i+S4gOS4quWIhumFjeS9jee9ru+8iTwvdGV4dD4KCiAgPCEtLSBuZXcgY2h1bmsgd2hlbiBmdWxsIC0tPgogIDx0ZXh0IHg9IjY1NSIgeT0iMTEyIiBmb250LXNpemU9IjExIiBmaWxsPSIjNjQ3NDhiIj7lnZfmu6HihpLlho3mjILmlrDlnZc8L3RleHQ+CiAgPHBhdGggZD0iTTYyNCwxNDMgTDY0OCwxNDMiIHN0cm9rZT0iIzMzNDE1NSIgc3Ryb2tlLXdpZHRoPSIxLjYiIG1hcmtlci1lbmQ9InVybCgjYXIpIi8+CiAgPHJlY3QgeD0iNjU0IiB5PSIxMTgiIHdpZHRoPSIxODAiIGhlaWdodD0iNTAiIHJ4PSI0IiBmaWxsPSIjZWZmNmZmIiBzdHJva2U9IiM5M2M1ZmQiLz4KICA8cmVjdCB4PSI2NTQiIHk9IjExOCIgd2lkdGg9IjYwIiBoZWlnaHQ9IjUwIiBmaWxsPSIjNjBhNWZhIi8+PHRleHQgeD0iNjg0IiB5PSIxNDgiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtc2l6ZT0iMTMiIGZpbGw9IiNmZmYiPkQ8L3RleHQ+CgogIDx0ZXh0IHg9IjQ2IiB5PSIyMzQiIGZvbnQtc2l6ZT0iMTIuNSIgZmlsbD0iIzFlNDBhZiI+4oCiIOWIhumFjSA9IOaMh+mSiCArPSBzaXpl77yMPHRzcGFuIGZvbnQtd2VpZ2h0PSI3MDAiPk8oMSk8L3RzcGFuPu+8jOaXoOmAkOWvueixoeiusOi0pu+8m+WvueixoeWGheWtmOi/nue7rSDihpIg57yT5a2Y5Y+L5aW9PC90ZXh0PgogIDx0ZXh0IHg9IjQ2IiB5PSIyNTYiIGZvbnQtc2l6ZT0iMTIuNSIgZmlsbD0iIzFlNDBhZiI+4oCiIERyb3Ag5pW05LiqIGFyZW5hIOKGkiDmiYDmnIkgY2h1bmsgPHRzcGFuIGZvbnQtd2VpZ2h0PSI3MDAiPuS4gOasoeaAp+mHiuaUvjwvdHNwYW4+77yI5aSa5pWwIGJ1bXAg5a6e546w6buY6K6kPHRzcGFuIGZpbGw9IiNiOTFjMWMiIGZvbnQtd2VpZ2h0PSI3MDAiPuS4jemAkOS4quiwg+eUqOaekOaehDwvdHNwYW4+77yB77yJPC90ZXh0PgoKICA8IS0tIFBhbmVsIEI6IG1hbGxvYy9mcmVlIC0tPgogIDxyZWN0IHg9IjI2IiB5PSIyODgiIHdpZHRoPSI4NDgiIGhlaWdodD0iMTY4IiByeD0iMTIiIGZpbGw9IiNmZmZmZmYiIHN0cm9rZT0iIzk0YTNiOCIgc3Ryb2tlLXdpZHRoPSIxLjQiLz4KICA8dGV4dCB4PSI0NiIgeT0iMzE2IiBmb250LXNpemU9IjE2IiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjNDc1NTY5Ij7lr7nmr5TvvJrns7vnu58gbWFsbG9jIC8gZnJlZe+8iOmAkOS4quWIhumFjemHiuaUvu+8iTwvdGV4dD4KCiAgPGc+CiAgICA8cmVjdCB4PSI2MCIgeT0iMzMyIiB3aWR0aD0iMTgiIGhlaWdodD0iNDAiIGZpbGw9IiNjYmQ1ZTEiLz48cmVjdCB4PSI3OCIgeT0iMzMyIiB3aWR0aD0iNzAiIGhlaWdodD0iNDAiIGZpbGw9IiNmY2E1YTUiLz4KICAgIDxyZWN0IHg9IjE2OCIgeT0iMzMyIiB3aWR0aD0iMTgiIGhlaWdodD0iNDAiIGZpbGw9IiNjYmQ1ZTEiLz48cmVjdCB4PSIxODYiIHk9IjMzMiIgd2lkdGg9IjUwIiBoZWlnaHQ9IjQwIiBmaWxsPSIjZmRiYTc0Ii8+CiAgICA8cmVjdCB4PSIyNjAiIHk9IjMzMiIgd2lkdGg9IjE4IiBoZWlnaHQ9IjQwIiBmaWxsPSIjY2JkNWUxIi8+PHJlY3QgeD0iMjc4IiB5PSIzMzIiIHdpZHRoPSI5MCIgaGVpZ2h0PSI0MCIgZmlsbD0iI2ZjYTVhNSIgb3BhY2l0eT0iMC40IiBzdHJva2U9IiNlZjQ0NDQiIHN0cm9rZS1kYXNoYXJyYXk9IjMgMyIvPgogICAgPHJlY3QgeD0iMzkyIiB5PSIzMzIiIHdpZHRoPSIxOCIgaGVpZ2h0PSI0MCIgZmlsbD0iI2NiZDVlMSIvPjxyZWN0IHg9IjQxMCIgeT0iMzMyIiB3aWR0aD0iNjAiIGhlaWdodD0iNDAiIGZpbGw9IiNmY2QzNGQiLz4KICAgIDxyZWN0IHg9IjUwMCIgeT0iMzMyIiB3aWR0aD0iMTgiIGhlaWdodD0iNDAiIGZpbGw9IiNjYmQ1ZTEiLz48cmVjdCB4PSI1MTgiIHk9IjMzMiIgd2lkdGg9IjQ0IiBoZWlnaHQ9IjQwIiBmaWxsPSIjZmNhNWE1IiBvcGFjaXR5PSIwLjQiIHN0cm9rZT0iI2VmNDQ0NCIgc3Ryb2tlLWRhc2hhcnJheT0iMyAzIi8+CiAgICA8cmVjdCB4PSI2MDAiIHk9IjMzMiIgd2lkdGg9IjE4IiBoZWlnaHQ9IjQwIiBmaWxsPSIjY2JkNWUxIi8+PHJlY3QgeD0iNjE4IiB5PSIzMzIiIHdpZHRoPSI4MCIgaGVpZ2h0PSI0MCIgZmlsbD0iI2ZkYmE3NCIvPgogIDwvZz4KICA8dGV4dCB4PSI2NiIgeT0iMzI2IiBmb250LXNpemU9IjkuNSIgZmlsbD0iIzY0NzQ4YiI+54GwPeWIhumFjeWZqOWFg+aVsOaNri/lpLTpg6jjgIDjgIDomZrnur895bey6YeK5pS+55qE56m65rSe77yI56KO54mH77yJPC90ZXh0PgogIDx0ZXh0IHg9IjQ2IiB5PSIzOTgiIGZvbnQtc2l6ZT0iMTIuNSIgZmlsbD0iIzQ3NTU2OSI+4oCiIOavj+asoeWIhumFjS/ph4rmlL7pg73otbDliIbphY3lmajvvJrlhYPmlbDmja4gKyDorrDotKYgKyDlj6/og73liqDplIHjgIDigKIg6YeK5pS+6KaB6YCQ5Liq44CB5LiU6YCQ5Liq6LeR5p6Q5p6EPC90ZXh0PgogIDx0ZXh0IHg9IjQ2IiB5PSI0MjAiIGZvbnQtc2l6ZT0iMTIuNSIgZmlsbD0iIzQ3NTU2OSI+4oCiIOWPjeWkjeWIhumFjS/ph4rmlL7kuI3lkIzlpKflsI8g4oaSIDx0c3BhbiBmb250LXdlaWdodD0iNzAwIj7lhoXlrZjnoo7niYfljJY8L3RzcGFuPu+8jOWxgOmDqOaAp+W3rjwvdGV4dD4KCiAgPHRleHQgeD0iNDUwIiB5PSI0ODIiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtc2l6ZT0iMTIuNSIgZmlsbD0iIzBmMTcyYSIgZm9udC13ZWlnaHQ9IjYwMCI+QXJlbmEg55qE55Sc5Yy6ID0g44CM6Zi25q615oCnIC8g5om56YeP44CN55Sf5ZG95ZGo5pyf77ya57yW6K+R5ZmoIHBhc3PjgIHljZXmrKHor7fmsYLlpITnkIbjgIHmr4/luKflvqrnjq8g4oCU4oCUIOeUqOWujOaVtOWdl+aJlOaOiTwvdGV4dD4KPC9zdmc+Cg=="/>
</p>
<p align="center"><sub><b>图 1</b> · Bump（指针递增）分配 vs 系统 malloc/free</sub></p>

Bump（撞针/指针递增）分配是 arena 的核心机制：arena 持有一大块内存和一个 **bump 指针**。每次分配只是「把指针向前移动 size 字节、返回旧位置」——这就是全部，`O(1)`、无逐对象记账。块用满了就再挂一块新 chunk。**释放不是逐个进行的**：丢弃整个 arena 时，直接把所有 chunk 还给系统（部分实现 `reset()` 可保留内存复用）。

代价是：**arena 存活期间，单个对象占用的内存不会被回收**；而且多数 bump 实现**默认不会运行所分配值的析构函数 `Drop`**（见 §11 陷阱）。因此 Arena 的甜区是「**阶段性 / 批量**」生命周期——编译器 pass、单次请求、每帧循环——用完把整块一次性扔掉。

---

## 3. Arena 如何化解「图 / 自引用」难题

<p align="center">
<img alt="Arena 化解图与自引用" style="width:100%;max-width:920px;height:auto;" src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA5MjAgNDgwIiBmb250LWZhbWlseT0iJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJywnU2Vnb2UgVUknLHNhbnMtc2VyaWYiPgogIDxkZWZzPgogICAgPG1hcmtlciBpZD0iYzEiIG1hcmtlcldpZHRoPSIxMCIgbWFya2VySGVpZ2h0PSIxMCIgcmVmWD0iOCIgcmVmWT0iMyIgb3JpZW50PSJhdXRvIj48cGF0aCBkPSJNMCwwIEw4LDMgTDAsNiBaIiBmaWxsPSIjMzM0MTU1Ii8+PC9tYXJrZXI+CiAgICA8bWFya2VyIGlkPSJjMXIiIG1hcmtlcldpZHRoPSIxMCIgbWFya2VySGVpZ2h0PSIxMCIgcmVmWD0iOCIgcmVmWT0iMyIgb3JpZW50PSJhdXRvIj48cGF0aCBkPSJNMCwwIEw4LDMgTDAsNiBaIiBmaWxsPSIjZGMyNjI2Ii8+PC9tYXJrZXI+CiAgICA8bWFya2VyIGlkPSJjMWciIG1hcmtlcldpZHRoPSIxMCIgbWFya2VySGVpZ2h0PSIxMCIgcmVmWD0iOCIgcmVmWT0iMyIgb3JpZW50PSJhdXRvIj48cGF0aCBkPSJNMCwwIEw4LDMgTDAsNiBaIiBmaWxsPSIjN2MzYWVkIi8+PC9tYXJrZXI+CiAgPC9kZWZzPgogIDxyZWN0IHdpZHRoPSI5MjAiIGhlaWdodD0iNDgwIiBmaWxsPSIjZjhmYWZjIi8+CiAgPHRleHQgeD0iNDYwIiB5PSIzNCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1zaXplPSIyNCIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iIzBmMTcyYSI+QXJlbmEg5aaC5L2V5YyW6Kej44CM5Zu+IC8g5qCRIC8g6Ieq5byV55So44CN6Zq+6aKYPC90ZXh0PgoKICA8IS0tIExlZnQ6IFJjPFJlZkNlbGw+IC0tPgogIDxyZWN0IHg9IjI2IiB5PSI1NiIgd2lkdGg9IjI5MCIgaGVpZ2h0PSI0MDAiIHJ4PSIxMiIgZmlsbD0iI2ZmZmZmZiIgc3Ryb2tlPSIjZWY0NDQ0IiBzdHJva2Utd2lkdGg9IjEuNiIvPgogIDx0ZXh0IHg9IjE3MSIgeT0iODQiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtc2l6ZT0iMTUiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiNiOTFjMWMiPuKdjCDml6AgQXJlbmHvvJpSYyZsdDtSZWZDZWxsJmx0O1QmZ3Q7Jmd0OzwvdGV4dD4KCiAgPHJlY3QgeD0iODAiIHk9IjEwNiIgd2lkdGg9IjE4MCIgaGVpZ2h0PSI0NCIgcng9IjgiIGZpbGw9IiNmZWUyZTIiIHN0cm9rZT0iI2VmNDQ0NCIvPgogIDx0ZXh0IHg9IjE3MCIgeT0iMTMzIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LXNpemU9IjEyIiBmb250LXdlaWdodD0iNjAwIiBmaWxsPSIjOTkxYjFiIj5SYyZsdDtSZWZDZWxsJmx0O05vZGUmZ3Q7Jmd0OzwvdGV4dD4KICA8cmVjdCB4PSI4MCIgeT0iMjEwIiB3aWR0aD0iMTgwIiBoZWlnaHQ9IjQ0IiByeD0iOCIgZmlsbD0iI2ZlZTJlMiIgc3Ryb2tlPSIjZWY0NDQ0Ii8+CiAgPHRleHQgeD0iMTcwIiB5PSIyMzciIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtc2l6ZT0iMTIiIGZvbnQtd2VpZ2h0PSI2MDAiIGZpbGw9IiM5OTFiMWIiPlJjJmx0O1JlZkNlbGwmbHQ7Tm9kZSZndDsmZ3Q7PC90ZXh0PgogIDxsaW5lIHgxPSIxNTAiIHkxPSIxNTAiIHgyPSIxNTAiIHkyPSIyMDgiIHN0cm9rZT0iI2RjMjYyNiIgc3Ryb2tlLXdpZHRoPSIxLjYiIG1hcmtlci1lbmQ9InVybCgjYzFyKSIvPgogIDxsaW5lIHgxPSIxOTIiIHkxPSIyMTAiIHgyPSIxOTIiIHkyPSIxNTIiIHN0cm9rZT0iI2RjMjYyNiIgc3Ryb2tlLXdpZHRoPSIxLjYiIG1hcmtlci1lbmQ9InVybCgjYzFyKSIvPgogIDx0ZXh0IHg9IjI3MCIgeT0iMTg0IiBmb250LXNpemU9IjEwIiBmaWxsPSIjZGMyNjI2Ij7kupLlvJU9546vPC90ZXh0PgoKICA8dGV4dCB4PSI0NiIgeT0iMzAwIiBmb250LXNpemU9IjExLjUiIGZpbGw9IiM3ZjFkMWQiPuKAoiDlvJXnlKjorqHmlbDmnInov5DooYzml7blvIDplIA8L3RleHQ+CiAgPHRleHQgeD0iNDYiIHk9IjMyNCIgZm9udC1zaXplPSIxMS41IiBmaWxsPSIjN2YxZDFkIj7igKIgUmVmQ2VsbCDov5DooYzml7blgJ/nlKjmo4Dmn6Ug4oaSIOWPr+iDvSBwYW5pYzwvdGV4dD4KICA8dGV4dCB4PSI0NiIgeT0iMzQ4IiBmb250LXNpemU9IjExLjUiIGZpbGw9IiM3ZjFkMWQiPuKAoiDnjq/lvaLlvJXnlKjkvJrms4TmvI/vvIzpnIDmiYvliqggV2VhazwvdGV4dD4KICA8dGV4dCB4PSI0NiIgeT0iMzcyIiBmb250LXNpemU9IjExLjUiIGZpbGw9IiM3ZjFkMWQiPuKAoiDnsbvlnovlsYLlsYLltYzlpZfjgIHlhpfplb/mmJPplJk8L3RleHQ+CiAgPHRleHQgeD0iNDYiIHk9IjM5NiIgZm9udC1zaXplPSIxMS41IiBmaWxsPSIjN2YxZDFkIj7igKIg6IqC54K55pWj6JC95aCG5LiK77yM5bGA6YOo5oCn5beuPC90ZXh0PgoKICA8IS0tIFJpZ2h0OiBBcmVuYSAtLT4KICA8cmVjdCB4PSIzMzIiIHk9IjU2IiB3aWR0aD0iNTYyIiBoZWlnaHQ9IjQwMCIgcng9IjEyIiBmaWxsPSIjZmZmZmZmIiBzdHJva2U9IiM3YzNhZWQiIHN0cm9rZS13aWR0aD0iMS42Ii8+CiAgPHRleHQgeD0iNjEzIiB5PSI4NCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1zaXplPSIxNSIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iIzZiMjFhOCI+4pyFIEFyZW5h77ya5Y2V5LiA5omA5pyJ6ICF77yM5YaF6YOo5LqS5byVPC90ZXh0PgoKICA8IS0tIGFyZW5hIGNvbnRhaW5lciAtLT4KICA8cmVjdCB4PSIzNTYiIHk9IjEwMCIgd2lkdGg9IjUxNCIgaGVpZ2h0PSIxNzYiIHJ4PSIxMCIgZmlsbD0iI2ZhZjVmZiIgc3Ryb2tlPSIjYzRiNWZkIiBzdHJva2Utd2lkdGg9IjEuNSIvPgogIDx0ZXh0IHg9IjM3MiIgeT0iMTIyIiBmb250LXNpemU9IjEyIiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjNmIyMWE4Ij5BcmVuYe+8iOaLpeacieWFqOmDqOiKgueCue+8iTwvdGV4dD4KCiAgPHJlY3QgeD0iMzg2IiB5PSIxMzQiIHdpZHRoPSI3NiIgaGVpZ2h0PSI0MCIgcng9IjYiIGZpbGw9IiNkZGQ2ZmUiIHN0cm9rZT0iIzhiNWNmNiIvPjx0ZXh0IHg9IjQyNCIgeT0iMTU5IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LXNpemU9IjEyIiBmaWxsPSIjNGMxZDk1Ij5ub2RlIDA8L3RleHQ+CiAgPHJlY3QgeD0iNTYwIiB5PSIxMjYiIHdpZHRoPSI3NiIgaGVpZ2h0PSI0MCIgcng9IjYiIGZpbGw9IiNkZGQ2ZmUiIHN0cm9rZT0iIzhiNWNmNiIvPjx0ZXh0IHg9IjU5OCIgeT0iMTUxIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LXNpemU9IjEyIiBmaWxsPSIjNGMxZDk1Ij5ub2RlIDE8L3RleHQ+CiAgPHJlY3QgeD0iNzQyIiB5PSIxMzQiIHdpZHRoPSI3NiIgaGVpZ2h0PSI0MCIgcng9IjYiIGZpbGw9IiNkZGQ2ZmUiIHN0cm9rZT0iIzhiNWNmNiIvPjx0ZXh0IHg9Ijc4MCIgeT0iMTU5IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LXNpemU9IjEyIiBmaWxsPSIjNGMxZDk1Ij5ub2RlIDI8L3RleHQ+CiAgPHJlY3QgeD0iNTc0IiB5PSIyMjAiIHdpZHRoPSI3NiIgaGVpZ2h0PSI0MCIgcng9IjYiIGZpbGw9IiNkZGQ2ZmUiIHN0cm9rZT0iIzhiNWNmNiIvPjx0ZXh0IHg9IjYxMiIgeT0iMjQ1IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LXNpemU9IjEyIiBmaWxsPSIjNGMxZDk1Ij5ub2RlIDM8L3RleHQ+CgogIDxsaW5lIHgxPSI0NjIiIHkxPSIxNTQiIHgyPSI1NTgiIHkyPSIxNDciIHN0cm9rZT0iIzdjM2FlZCIgc3Ryb2tlLXdpZHRoPSIxLjYiIG1hcmtlci1lbmQ9InVybCgjYzFnKSIvPgogIDxsaW5lIHgxPSI2MzYiIHkxPSIxNDYiIHgyPSI3NDAiIHkyPSIxNTIiIHN0cm9rZT0iIzdjM2FlZCIgc3Ryb2tlLXdpZHRoPSIxLjYiIG1hcmtlci1lbmQ9InVybCgjYzFnKSIvPgogIDxsaW5lIHgxPSI3NzAiIHkxPSIxNzQiIHgyPSI2NTAiIHkyPSIyMzUiIHN0cm9rZT0iIzdjM2FlZCIgc3Ryb2tlLXdpZHRoPSIxLjYiIG1hcmtlci1lbmQ9InVybCgjYzFnKSIvPgogIDxsaW5lIHgxPSI1OTgiIHkxPSIyMjAiIHgyPSI1OTgiIHkyPSIxNjgiIHN0cm9rZT0iIzdjM2FlZCIgc3Ryb2tlLXdpZHRoPSIxLjYiIG1hcmtlci1lbmQ9InVybCgjYzFnKSIvPgogIDx0ZXh0IHg9IjQ4NiIgeT0iMjAwIiBmb250LXNpemU9IjEwIiBmaWxsPSIjN2MzYWVkIj7njq/kuZ8gT0s8L3RleHQ+CgogIDx0ZXh0IHg9IjM1NiIgeT0iMzA0IiBmb250LXNpemU9IjEyLjUiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiM0MzM4Y2EiPuiKgueCuemXtOW8leeUqOeahOS4pOenjeihqOi+vu+8mjwvdGV4dD4KICA8dGV4dCB4PSIzNzIiIHk9IjMyNiIgZm9udC1zaXplPSIxMiIgZmlsbD0iIzMzNDE1NSI+PHRzcGFuIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiMyNTYzZWIiPuKRoCDlvJXnlKjlnos8L3RzcGFuPu+8muWtl+auteWtmCAmYW1wOydhcmVuYSBOb2Rl44CA77yIdHlwZWQtYXJlbmEgwrcgYnVtcGFsb++8iTwvdGV4dD4KICA8dGV4dCB4PSIzNzIiIHk9IjM0OCIgZm9udC1zaXplPSIxMiIgZmlsbD0iIzMzNDE1NSI+PHRzcGFuIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiNkOTc3MDYiPuKRoSDlj6Xmn4Tlnos8L3RzcGFuPu+8muWtl+auteWtmCBJbmRleO+8iENvcHnvvInvvIhpZC1hcmVuYSDCtyBzbG90bWFwIMK3IHNsYWLvvIk8L3RleHQ+CgogIDx0ZXh0IHg9IjM1NiIgeT0iMzgwIiBmb250LXNpemU9IjExLjUiIGZpbGw9IiM0YzFkOTUiPuKAoiBBcmVuYSDmmK/llK/kuIDmiYDmnInogIUg4oaSIOiKgueCueS6kuW8leS4jei/neWPjeWAn+eUqOinhOWImTwvdGV4dD4KICA8dGV4dCB4PSIzNTYiIHk9IjQwMiIgZm9udC1zaXplPSIxMS41IiBmaWxsPSIjNGMxZDk1Ij7igKIg5Y+l5p+E5Y+vIENvcHkgLyDlrZjlgqggLyDluo/liJfljJbvvIzml6DnlJ/lkb3lkajmnJ/jgIzkvKDmn5PjgI08L3RleHQ+CiAgPHRleHQgeD0iMzU2IiB5PSI0MjQiIGZvbnQtc2l6ZT0iMTEuNSIgZmlsbD0iIzRjMWQ5NSI+4oCiIOWkqeeEtuihqOi+vueOr+S4juWFseS6q++8m+iKgueCuei/nue7reWtmOaUvu+8jOWxgOmDqOaAp+WlvTwvdGV4dD4KICA8dGV4dCB4PSIzNTYiIHk9IjQ0NiIgZm9udC1zaXplPSIxMS41IiBmaWxsPSIjNGMxZDk1Ij7igKIg55So5a6M5pW05Z2X6YeK5pS+77yM5peg6ZyA6YCQ6IqC54K55riF55CGPC90ZXh0Pgo8L3N2Zz4K"/>
</p>
<p align="center"><sub><b>图 2</b> · Rc&lt;RefCell&lt;T&gt;&gt; 之苦 vs Arena 的两种互引表达</sub></p>

图、带父指针的树、双向链表这类**相互引用**的结构，在 Rust 里直接写会被借用检查器拒绝。`Rc<RefCell<T>>` 能绕过，但代价不小：引用计数开销、`RefCell` 运行时借用检查（可能 `panic`）、环会泄漏（需 `Weak`）、类型冗长。

Arena 给出两种更干净的表达：

- **① 引用型**（typed-arena / bumpalo）：所有节点都分配在同一个 arena 里，拥有**统一的 `'arena` 生命周期**，节点字段直接存 `&'arena Node`。Arena 是唯一所有者，节点互引不违反借用规则。
- **② 句柄型**（id-arena / slotmap / slab / …）：节点存在一个 `Vec` 式容器里，节点之间用 **`Copy` 的索引句柄**（`Index`/`Key`/`Id`）互相引用，而非裸指针。句柄可 `Copy`、可存储、可序列化，**不带生命周期「传染」**，天然容纳环。

---

## 4. 两大流派总览

按「内存怎么回收 + 节点怎么互相引用」，arena 实现分成两大流派：

<p align="center">
<img alt="Arena 两大流派总览" style="width:100%;max-width:960px;height:auto;" src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA5NjAgNDcwIiBmb250LWZhbWlseT0iJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJywnU2Vnb2UgVUknLHNhbnMtc2VyaWYiPgogIDxyZWN0IHdpZHRoPSI5NjAiIGhlaWdodD0iNDcwIiBmaWxsPSIjZjhmYWZjIi8+CiAgPHRleHQgeD0iNDgwIiB5PSIzMiIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1zaXplPSIyNCIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iIzBmMTcyYSI+QXJlbmEg5Lik5aSn5rWB5rS+5oC76KeIPC90ZXh0PgogIDx0ZXh0IHg9IjQ4MCIgeT0iNTUiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtc2l6ZT0iMTMiIGZpbGw9IiM2NDc0OGIiPuaMieOAjOWGheWtmOaAjuS5iOWbnuaUtiArIOiKgueCueaAjuS5iOS6kuebuOW8leeUqOOAjeWIhuaIkOS4pOexuzwvdGV4dD4KCiAgPCEtLSBMZWZ0OiBCdW1wIC0tPgogIDxyZWN0IHg9IjI2IiB5PSI3MCIgd2lkdGg9IjQ0MCIgaGVpZ2h0PSIzODQiIHJ4PSIxMiIgZmlsbD0iI2ZmZmZmZiIgc3Ryb2tlPSIjMjU2M2ViIiBzdHJva2Utd2lkdGg9IjEuNiIvPgogIDxyZWN0IHg9IjI2IiB5PSI3MCIgd2lkdGg9IjQ0MCIgaGVpZ2h0PSI1NCIgcng9IjEyIiBmaWxsPSIjMjU2M2ViIi8+CiAgPHJlY3QgeD0iMjYiIHk9IjEwMCIgd2lkdGg9IjQ0MCIgaGVpZ2h0PSIyNCIgZmlsbD0iIzI1NjNlYiIvPgogIDx0ZXh0IHg9IjI0NiIgeT0iOTQiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtc2l6ZT0iMTciIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiNmZmZmZmYiPuKRoCBCdW1wIC8g5Yy65Z+f5YiG6YWN5Z6LPC90ZXh0PgogIDx0ZXh0IHg9IjI0NiIgeT0iMTE0IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LXNpemU9IjExLjUiIGZpbGw9IiNkYmVhZmUiPui/lOWbniAmYW1wOydhcmVuYSBUIMK35pW05L2T5LiA5qyh5oCn6YeK5pS+wrfliIbphY3mnoHlv6s8L3RleHQ+CgogIDxyZWN0IHg9IjQyIiB5PSIxMzQiIHdpZHRoPSI0MDgiIGhlaWdodD0iNjYiIHJ4PSI4IiBmaWxsPSIjZWZmNmZmIiBzdHJva2U9IiNiZmRiZmUiLz4KICA8dGV4dCB4PSI1NiIgeT0iMTYwIiBmb250LXNpemU9IjE0IiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjMWUzYThhIj50eXBlZC1hcmVuYTwvdGV4dD4KICA8dGV4dCB4PSI1NiIgeT0iMTgyIiBmb250LXNpemU9IjExLjUiIGZpbGw9IiM0NzU1NjkiPuWNleS4gOexu+WeiyBU77ybYWxsb2Mg4oaSICZhbXA7bXV0IFTvvJvkvJrmiafooYzlhYPntKDmnpDmnoQ8L3RleHQ+CgogIDxyZWN0IHg9IjQyIiB5PSIyMDYiIHdpZHRoPSI0MDgiIGhlaWdodD0iNjYiIHJ4PSI4IiBmaWxsPSIjZWZmNmZmIiBzdHJva2U9IiNiZmRiZmUiLz4KICA8dGV4dCB4PSI1NiIgeT0iMjMyIiBmb250LXNpemU9IjE0IiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjMWUzYThhIj5idW1wYWxvPC90ZXh0PgogIDx0ZXh0IHg9IjU2IiB5PSIyNTQiIGZvbnQtc2l6ZT0iMTEuNSIgZmlsbD0iIzQ3NTU2OSI+5byC5p6E5Lu75oSP57G75Z6L77yb5p6B5b+r77ybPHRzcGFuIGZpbGw9IiNiOTFjMWMiIGZvbnQtd2VpZ2h0PSI3MDAiPum7mOiupOS4jei3kSBEcm9wPC90c3Bhbj7vvJvlkKsgY29sbGVjdGlvbnMvQm94PC90ZXh0PgoKICA8cmVjdCB4PSI0MiIgeT0iMjc4IiB3aWR0aD0iNDA4IiBoZWlnaHQ9IjY2IiByeD0iOCIgZmlsbD0iI2VmZjZmZiIgc3Ryb2tlPSIjYmZkYmZlIi8+CiAgPHRleHQgeD0iNTYiIHk9IjMwNCIgZm9udC1zaXplPSIxNCIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iIzFlM2E4YSI+YmxpbmstYWxsb2M8L3RleHQ+CiAgPHRleHQgeD0iNTYiIHk9IjMyNiIgZm9udC1zaXplPSIxMS41IiBmaWxsPSIjNDc1NTY5Ij7lj6/lpI3kvY3lpI3nlKjnmoTlv6vpgJ8gYnVtcO+8m+WvueaOpSBhbGxvY2F0b3JfYXBpPC90ZXh0PgoKICA8cmVjdCB4PSI0MiIgeT0iMzUwIiB3aWR0aD0iNDA4IiBoZWlnaHQ9IjY2IiByeD0iOCIgZmlsbD0iI2VmZjZmZiIgc3Ryb2tlPSIjYmZkYmZlIi8+CiAgPHRleHQgeD0iNTYiIHk9IjM3NiIgZm9udC1zaXplPSIxNCIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iIzFlM2E4YSI+YnVtcC1zY29wZTwvdGV4dD4KICA8dGV4dCB4PSI1NiIgeT0iMzk4IiBmb250LXNpemU9IjExLjUiIGZpbGw9IiM0NzU1NjkiPuW4puS9nOeUqOWfnyAvIOajgOafpeeCueeahCBidW1w77yM5Y+v5YiG5q615Zue5pS2PC90ZXh0PgoKICA8IS0tIFJpZ2h0OiBIYW5kbGUgLS0+CiAgPHJlY3QgeD0iNDk0IiB5PSI3MCIgd2lkdGg9IjQ0MCIgaGVpZ2h0PSIzODQiIHJ4PSIxMiIgZmlsbD0iI2ZmZmZmZiIgc3Ryb2tlPSIjZDk3NzA2IiBzdHJva2Utd2lkdGg9IjEuNiIvPgogIDxyZWN0IHg9IjQ5NCIgeT0iNzAiIHdpZHRoPSI0NDAiIGhlaWdodD0iNTQiIHJ4PSIxMiIgZmlsbD0iI2Q5NzcwNiIvPgogIDxyZWN0IHg9IjQ5NCIgeT0iMTAwIiB3aWR0aD0iNDQwIiBoZWlnaHQ9IjI0IiBmaWxsPSIjZDk3NzA2Ii8+CiAgPHRleHQgeD0iNzE0IiB5PSI5NCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1zaXplPSIxNyIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iI2ZmZmZmZiI+4pGhIEhhbmRsZSAvIOWPpeafhOe0ouW8leWeizwvdGV4dD4KICA8dGV4dCB4PSI3MTQiIHk9IjExNCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1zaXplPSIxMS41IiBmaWxsPSIjZmVmM2M3Ij7ov5Tlm54gQ29weSDlj6Xmn4TCt+inhOmBv+eUn+WRveWRqOacn8K36YOo5YiG5Y+v5Yig6ZmkPC90ZXh0PgoKICA8cmVjdCB4PSI1MTAiIHk9IjEzMiIgd2lkdGg9IjQwOCIgaGVpZ2h0PSI0OCIgcng9IjciIGZpbGw9IiNmZmY3ZWQiIHN0cm9rZT0iI2ZlZDdhYSIvPgogIDx0ZXh0IHg9IjUyNCIgeT0iMTUyIiBmb250LXNpemU9IjEzLjUiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiM5YTM0MTIiPmlkLWFyZW5hPC90ZXh0PgogIDx0ZXh0IHg9IjUyNCIgeT0iMTcxIiBmb250LXNpemU9IjExIiBmaWxsPSIjNDc1NTY5Ij5JZCZsdDtUJmd0O++8m+WPqui/veWKoOOAgeaXoOWIoOmZpO+8m+eugOWNleW/qzwvdGV4dD4KCiAgPHJlY3QgeD0iNTEwIiB5PSIxODYiIHdpZHRoPSI0MDgiIGhlaWdodD0iNDgiIHJ4PSI3IiBmaWxsPSIjZmZmN2VkIiBzdHJva2U9IiNmZWQ3YWEiLz4KICA8dGV4dCB4PSI1MjQiIHk9IjIwNiIgZm9udC1zaXplPSIxMy41IiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjOWEzNDEyIj5nZW5lcmF0aW9uYWwtYXJlbmE8L3RleHQ+CiAgPHRleHQgeD0iNTI0IiB5PSIyMjUiIGZvbnQtc2l6ZT0iMTEiIGZpbGw9IiM0NzU1NjkiPuS7o+mZhSBJbmRleO+8m+WPr+WIoOmZpCvku6PpmYXlronlhajvvJs8dHNwYW4gZmlsbD0iI2I5MWMxYyIgZm9udC13ZWlnaHQ9IjcwMCI+4pqg5bey5YGc57u04oaS5pS555SoIHNsb3RtYXA8L3RzcGFuPjwvdGV4dD4KCiAgPHJlY3QgeD0iNTEwIiB5PSIyNDAiIHdpZHRoPSI0MDgiIGhlaWdodD0iNDgiIHJ4PSI3IiBmaWxsPSIjZmZmN2VkIiBzdHJva2U9IiNmZWQ3YWEiLz4KICA8dGV4dCB4PSI1MjQiIHk9IjI2MCIgZm9udC1zaXplPSIxMy41IiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjOWEzNDEyIj5zbG90bWFwPC90ZXh0PgogIDx0ZXh0IHg9IjUyNCIgeT0iMjc5IiBmb250LXNpemU9IjExIiBmaWxsPSIjNDc1NTY5Ij7ku6PpmYUgS2V577ybU2xvdC9Ib3AvRGVuc2Ug5LiJ5Z6L77ybZ2FtZWRldiDmnIDniLE8L3RleHQ+CgogIDxyZWN0IHg9IjUxMCIgeT0iMjk0IiB3aWR0aD0iNDA4IiBoZWlnaHQ9IjQ4IiByeD0iNyIgZmlsbD0iI2ZmZjdlZCIgc3Ryb2tlPSIjZmVkN2FhIi8+CiAgPHRleHQgeD0iNTI0IiB5PSIzMTQiIGZvbnQtc2l6ZT0iMTMuNSIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iIzlhMzQxMiI+c2xhYjwvdGV4dD4KICA8dGV4dCB4PSI1MjQiIHk9IjMzMyIgZm9udC1zaXplPSIxMSIgZmlsbD0iIzQ3NTU2OSI+dXNpemUga2V577yb5aSN55So5qe95L2N77yb5peg5Luj6ZmFKHN0YWxlIOmjjumZqSnvvJt0b2tpbyDlnKjnlKg8L3RleHQ+CgogIDxyZWN0IHg9IjUxMCIgeT0iMzQ4IiB3aWR0aD0iMjAwIiBoZWlnaHQ9IjQ4IiByeD0iNyIgZmlsbD0iI2ZmZjdlZCIgc3Ryb2tlPSIjZmVkN2FhIi8+CiAgPHRleHQgeD0iNTI0IiB5PSIzNjgiIGZvbnQtc2l6ZT0iMTMuNSIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iIzlhMzQxMiI+dGh1bmRlcmRvbWU8L3RleHQ+CiAgPHRleHQgeD0iNTI0IiB5PSIzODciIGZvbnQtc2l6ZT0iMTEiIGZpbGw9IiM0NzU1NjkiPuabtOe0p+WHkS/lv6vnmoTku6PpmYUgYXJlbmE8L3RleHQ+CgogIDxyZWN0IHg9IjcxOCIgeT0iMzQ4IiB3aWR0aD0iMjAwIiBoZWlnaHQ9IjQ4IiByeD0iNyIgZmlsbD0iI2ZmZjdlZCIgc3Ryb2tlPSIjZmVkN2FhIi8+CiAgPHRleHQgeD0iNzMyIiB5PSIzNjgiIGZvbnQtc2l6ZT0iMTMuNSIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iIzlhMzQxMiI+bGEtYXJlbmE8L3RleHQ+CiAgPHRleHQgeD0iNzMyIiB5PSIzODciIGZvbnQtc2l6ZT0iMTEiIGZpbGw9IiM0NzU1NjkiPnJ1c3QtYW5hbHl6ZXIg55qEIElkeO+8m+WPqui/veWKoDwvdGV4dD4KCiAgPHRleHQgeD0iNzE0IiB5PSI0MjIiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtc2l6ZT0iMTAuNSIgZmlsbD0iIzk0YTNiOCI+5Y+l5p+E5Z6LID0g55So44CM5pWw57uE5LiL5qCHICsg5Y+v6YCJ5Luj6ZmF5Y+344CN5pu/5Luj6KO45oyH6ZKI77yM5aSp54S25a+5IENvcHnjgIHlj6/luo/liJfljJY8L3RleHQ+Cjwvc3ZnPgo="/>
</p>
<p align="center"><sub><b>图 3</b> · Arena 两大流派：Bump/区域分配型 vs Handle/句柄索引型</sub></p>

- **① Bump / 区域分配型**：返回 `&'arena T` 引用，整体一次性释放，分配极快。代表：`typed-arena`、`bumpalo`、`blink-alloc`、`bump-scope`。
- **② Handle / 句柄索引型**：返回 `Copy` 句柄（`Index`/`Key`/`Id`），规避生命周期，**部分支持单独删除 + 槽位复用**。代表：`id-arena`、`generational-arena`（已停维）、`slotmap`、`slab`、`thunderdome`、`la-arena`。

---

## 5. 逐一详解（含代码示例）

### 5.1 Bump / 区域分配型

#### typed-arena

- **定位**：单一类型 `Arena<T>` 的快速受限分配器；所有对象同生命周期，适合建图/树/带父指针的环。
- **返回**：`alloc(v) -> &mut T`（另有 `alloc_str`、`alloc_extend`）。**异构 ✗**（单类型）。**删除 ✗**。
- **Drop**：✅ arena 丢弃时对所有值执行析构。**no_std** ✅（关 `std` 默认特性）。**allocator_api** ✗。
- **现状**：`2.0.2`（2023-01，成熟稳定、低活跃），许可 **MIT**，累计下载约 8000 万，是元老级事实标准。

```rust
use typed_arena::Arena;
use std::cell::RefCell;

// 一棵可含环/父指针的树：所有节点共享 'a 生命周期
struct Node<'a> {
    value: i32,
    links: RefCell<Vec<&'a Node<'a>>>,
}

fn main() {
    let arena: Arena<Node> = Arena::new();
    let a = arena.alloc(Node { value: 0, links: RefCell::new(vec![]) });
    let b = arena.alloc(Node { value: 1, links: RefCell::new(vec![]) });
    a.links.borrow_mut().push(b);    // a -> b
    b.links.borrow_mut().push(a);    // b -> a，环也没问题（同为 &'a）
    // arena 丢弃时，全部节点一次性释放并析构
}
```

#### bumpalo ⭐

- **定位**：最流行的 bump 分配 arena，异构、极快，phase-oriented 批量分配。
- **返回**：`alloc(v) -> &mut T`、`alloc_str`、`alloc_slice_*`。**异构 ✓**。`reset()` 批量回收并复用最大 chunk。
- **Drop（重点）**：**默认 ✗ 不运行析构**（README 明确：allocated objects' `Drop` impls are *not* invoked）。需要析构时用 `bumpalo::boxed::Box`（会 drop）或 `bumpalo::collections::{Vec, String}`（集合值自身被 drop 时跑元素析构）。
- **no_std** ✅（需 `alloc`）。**allocator_api** ✅（nightly feature，或稳定版用 `allocator-api2`）；但**不能**作 `#[global_allocator]`。
- **现状**：`3.20.3`（2026-05，活跃），许可 **MIT/Apache-2.0**，累计下载约 5.7 亿，512 个直接反向依赖；采用者含 **wasm-bindgen、SWC、typst**。

```rust
use bumpalo::Bump;

fn main() {
    let bump = Bump::new();
    let n: &mut u64 = bump.alloc(42);                 // 异构：任意类型
    let s: &str     = bump.alloc_str("hello arena");
    let buf: &mut [u8] = bump.alloc_slice_fill_copy(4, 0u8);

    // ⚠ 默认不跑 Drop！持有资源(File/Socket)的类型要用会析构的封装：
    // let boxed = bumpalo::boxed::Box::new_in(MyGuard::new(), &bump); // 这个会 drop

    println!("{n} {s} {}", buf.len());
    // 方式一：drop(bump) 整块释放；方式二：bump.reset() 清空但复用内存
}
```

#### blink-alloc / bump-scope（新生代 Bump）

- **blink-alloc**：「快速、并发、**带 drop 支持**」的 bump 分配器。安全适配器 `Blink::put(v) -> &mut T`，**默认在 `reset` 时 drop 已放入值**；底层实现 `Allocator`，并**支持 `#[global_allocator]`**（`GlobalBlinkAlloc`）。`0.4.0`（2025-12），MIT/Apache，较小众。
- **bump-scope**：带**作用域 / 检查点（checkpoint）** 的 bump，受 bumpalo 启发但支持栈式/分段回收。返回 `BumpBox<T>`（**总是** drop，与 bumpalo 相反），或对无需析构类型 `into_ref()`。`2.3.3`（2026-07，最新活跃），MIT/Apache，edition 2024。

```rust
// bump-scope：用作用域在「阶段结束」时回收该段分配
use bump_scope::Bump;
let mut bump: Bump = Bump::new();
bump.scoped(|mut scope| {
    let tmp = scope.alloc_slice_copy(&[1, 2, 3]);   // 仅本作用域存活
    // ……使用 tmp……
}); // 离开作用域即回收该段，且 BumpBox 会跑析构
```

### 5.2 Handle / 句柄索引型

#### id-arena / la-arena（只追加、无代际）

- **id-arena**：`alloc(v) -> Id<T>`（`Copy` 句柄）。**无删除、无代际**；适合一次性建图（AST/IR/CFG）。`2.3.0`（2026-01，休眠但未弃），MIT/Apache，采用者 walrus、wit-parser、cairo-lang、rkv。
- **la-arena**：rust-analyzer 的 `alloc(v) -> Idx<T>`。**纯追加、无删除、无代际**，`Idx` 是类型化的 `u32`。`0.3.1`（2023-06），MIT/Apache，**不支持 no_std**。

```rust
use id_arena::{Arena, Id};

struct Node { edges: Vec<Id<Node>> }   // 用 Copy 句柄互引，无生命周期传染

fn main() {
    let mut arena: Arena<Node> = Arena::new();
    let a = arena.alloc(Node { edges: vec![] });
    let b = arena.alloc(Node { edges: vec![a] });   // b -> a
    arena[a].edges.push(b);                          // a -> b，成环也 OK
    // 只追加、无删除；Id<T> 可 Copy、可放进任意结构体
}
```

#### generational-arena ⚠（已停维）

- **定位**：用**世代索引**支持删除且防 ABA 的安全 arena（源自 Catherine West 的 ECS 演讲）。`insert -> Index { index, generation }`，`remove` 后槽位复用、代际号递增，陈旧 `Index` 被拒绝。
- **现状**：⚠️ **仓库 2023-11 归档、末版 `0.2.9`**；**RUSTSEC-2024-0014 判定 unmaintained 并点名 `slotmap` 为替代**；许可 **MPL-2.0**。**新项目请改用 slotmap / thunderdome**，此处仅作概念参照。

```rust
// ⚠ 已停维，示意其代际语义即可，新项目用 slotmap / thunderdome
use generational_arena::Arena;
let mut arena = Arena::new();
let i = arena.insert("x");          // 代际 Index
arena.remove(i);
assert!(arena.get(i).is_none());    // 旧 Index 落到复用槽被拒 → 安全
```

#### slotmap（代际句柄的当红之选）

- **定位**：带持久 `Key` 的容器，`O(1)` 插入/访问/删除，官方点名「游戏实体 / 图节点」。
- **返回**：`insert(v) -> Key`（内含 `version: NonZeroU32`，`Copy`）。**删除 ✓ + 代际安全 ✓**。
- **三变体**：`SlotMap`（基准，删除最快、迭代最慢）、`HopSlotMap`（迭代快，**⚠ 自 1.1.0 起废弃、2.0 将移除**）、`DenseSlotMap`（值稠密存储、迭代最快，随机访问多一层间接）。
- **现状**：`1.1.1`（2025-12，活跃），许可 **Zlib**；采用者众多：**bevy_ecs、gpui(Zed)、taffy、dioxus、polars、rerun、s2n-quic-dc**。

```rust
use slotmap::{SlotMap, DefaultKey};

fn main() {
    let mut sm: SlotMap<DefaultKey, &str> = SlotMap::new();
    let k1 = sm.insert("entity A");    // 代际 Key（Copy）
    let k2 = sm.insert("entity B");

    sm.remove(k1);                     // 删除 → 槽位待复用
    assert!(sm.get(k1).is_none());     // 旧 key 代际不匹配 → 安全失效
    assert_eq!(sm[k2], "entity B");
    // 需要按 key 关联额外数据：SecondaryMap；迭代密集：DenseSlotMap
}
```

#### slab（简单、无代际，tokio 同款）

- **定位**：单类型预分配存储，`insert -> usize` key，`remove` 后槽位复用；像「会复用空位的 Vec」。
- **关键**：**无代际**——`remove` + `insert` 后旧 `usize` key 可能落到被复用的新槽（**stale/别名风险**，需业务自证 key 不会过期）。
- **现状**：`0.4.12`（2026-01），tokio-rs 组织、Alice Ryhl 维护，许可 **MIT**，累计下载约 9 亿；采用者 **tokio、h2、tower、quinn-proto**。

```rust
use slab::Slab;

fn main() {
    let mut slab: Slab<String> = Slab::new();
    let key: usize = slab.insert("conn #1".into());   // 返回 usize
    println!("{}", slab[key]);
    slab.remove(key);                                 // 槽位复用
    // ⚠ 无代际：若他处还存着旧 key，remove 后它可能指向新占用者
}
```

#### thunderdome（更紧凑的代际 arena）

- **定位**：紧凑的世代竞技场，`Index` 压到 **8 字节**（slot + generation），常数时间 insert/get/remove；是 `generational-arena` 的现代替代。
- **返回**：`insert -> Index`（`Copy`）。**删除 ✓ + 代际安全 ✓**。`0.6.1`（2023-06，稳定/「done」型），MIT/Apache；采用者 yakui、firewheel、gfx-backend。

```rust
use thunderdome::{Arena, Index};

fn main() {
    let mut arena: Arena<&str> = Arena::new();
    let i: Index = arena.insert("player");   // 8 字节 Copy 句柄
    assert_eq!(arena.get(i), Some(&"player"));
    arena.remove(i);
    assert_eq!(arena.get(i), None);          // 代际保护
}
```

### 5.3 相关：elsa 与字符串驻留

#### elsa（append-only，交出「真引用」）

- **定位**：append-only 集合，让「持有 `&T` 的同时继续插入」成为可能。`FrozenVec` / `FrozenMap` 用 `&self` 插入，只存带间接层的类型（`String`/`Box<T>`），交出指向**堆上稳定数据**的 `&T`——外层重分配只移动指针、不移动被指向数据，故已有引用在后续插入后仍有效。
- **返回真引用 `&T`（非句柄）**，**纯 append-only、无删除**。**不支持 no_std**。`1.11.2`（2025-03），MIT/Apache；**被 rustc（`rustc_data_structures`）、ICU4X、Typst 采用**。

```rust
use elsa::FrozenVec;

fn main() {
    let cache: FrozenVec<String> = FrozenVec::new();
    let a: &str = cache.push_get("alpha".to_string());  // 拿到稳定 &str
    cache.push("beta".to_string());                     // 追加不会使 a 失效
    println!("{a}");                                     // 仍然有效
}
```

#### lasso / string-interner（字符串驻留）

把重复字符串收敛为可 `O(1)` 比较/查回的小整数 key，本质是「字符串 arena + 去重」。**lasso**：返回 `Spur`（`NonZeroU32`），有单线程 `Rodeo` 与并发 `ThreadedRodeo`；`0.7.3`（2024-08，休眠但稳定）。**string-interner**：返回 `SymbolU32`，可插拔后端，单线程；`0.20.0`（2026-04，积极维护）。两者均 MIT/Apache。

---

## 6. 特性能力矩阵

<p align="center">
<img alt="特性能力矩阵" style="width:100%;max-width:960px;height:auto;" src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA5NjAgNDc2IiBmb250LWZhbWlseT0iJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJywnU2Vnb2UgVUknLHNhbnMtc2VyaWYiPgogIDxyZWN0IHdpZHRoPSI5NjAiIGhlaWdodD0iNDc2IiBmaWxsPSIjZjhmYWZjIi8+CiAgPHRleHQgeD0iNDgwIiB5PSIzMiIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1zaXplPSIyMyIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iIzBmMTcyYSI+54m55oCn6IO95Yqb55+p6Zi1PC90ZXh0PgogIDx0ZXh0IHg9IjQ4MCIgeT0iNTQiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtc2l6ZT0iMTIiIGZpbGw9IiM2NDc0OGIiPuKckyDmlK/mjIHjgIDinJcg5LiN5pSv5oyB44CA4pazIOWPr+mAiS/lj5fpmZDjgIDigJQg5LiN6YCC55So77yI54mI5pys55u45YWz6aG56K+35LulIGNyYXRlcy5pbyDmlofmoaPkuLrlh4bvvIk8L3RleHQ+CgogIDxyZWN0IHg9IjIwIiB5PSI2NCIgd2lkdGg9IjkyMCIgaGVpZ2h0PSI1MiIgZmlsbD0iIzFlMjkzYiIvPgogIDx0ZXh0IHg9Ijg1IiB5PSI5NSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1zaXplPSIxMyIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iI2ZmZmZmZiI+Y3JhdGU8L3RleHQ+CiAgPHRleHQgeD0iMjE1IiB5PSI5NSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1zaXplPSIxMiIgZmlsbD0iI2ZmZmZmZiI+6L+U5Zue57G75Z6LPC90ZXh0PgogIDx0ZXh0IHg9IjMzNSIgeT0iOTUiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtc2l6ZT0iMTIiIGZpbGw9IiNmZmZmZmYiPuW8guaehOexu+WeizwvdGV4dD4KICA8dGV4dCB4PSI0NDUiIHk9Ijk1IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LXNpemU9IjEyIiBmaWxsPSIjZmZmZmZmIj7lj6/liKDpmaTCt+WkjeeUqDwvdGV4dD4KICA8dGV4dCB4PSI1NTUiIHk9Ijk1IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LXNpemU9IjEyIiBmaWxsPSIjZmZmZmZmIj7ku6PpmYXlronlhag8L3RleHQ+CiAgPHRleHQgeD0iNjY1IiB5PSI5NSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1zaXplPSIxMiIgZmlsbD0iI2ZmZmZmZiI+6L+Q6KGMIERyb3A8L3RleHQ+CiAgPHRleHQgeD0iNzc1IiB5PSI5NSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1zaXplPSIxMiIgZmlsbD0iI2ZmZmZmZiI+bm9fc3RkPC90ZXh0PgogIDx0ZXh0IHg9Ijg4NSIgeT0iOTAiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtc2l6ZT0iMTEiIGZpbGw9IiNmZmZmZmYiPmFsbG9jYXRvcjwvdGV4dD48dGV4dCB4PSI4ODUiIHk9IjEwNCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1zaXplPSIxMSIgZmlsbD0iI2ZmZmZmZiI+X2FwaTwvdGV4dD4KCiAgPHJlY3QgeD0iMjAiIHk9IjExNiIgd2lkdGg9IjkyMCIgaGVpZ2h0PSI0NCIgZmlsbD0iI2ZmZmZmZiIvPgogIDxyZWN0IHg9IjIwIiB5PSIxNjAiIHdpZHRoPSI5MjAiIGhlaWdodD0iNDQiIGZpbGw9IiNmMWY1ZjkiLz4KICA8cmVjdCB4PSIyMCIgeT0iMjA0IiB3aWR0aD0iOTIwIiBoZWlnaHQ9IjQ0IiBmaWxsPSIjZmZmZmZmIi8+CiAgPHJlY3QgeD0iMjAiIHk9IjI0OCIgd2lkdGg9IjkyMCIgaGVpZ2h0PSI0NCIgZmlsbD0iI2YxZjVmOSIvPgogIDxyZWN0IHg9IjIwIiB5PSIyOTIiIHdpZHRoPSI5MjAiIGhlaWdodD0iNDQiIGZpbGw9IiNmZmZmZmYiLz4KICA8cmVjdCB4PSIyMCIgeT0iMzM2IiB3aWR0aD0iOTIwIiBoZWlnaHQ9IjQ0IiBmaWxsPSIjZjFmNWY5Ii8+CiAgPHJlY3QgeD0iMjAiIHk9IjM4MCIgd2lkdGg9IjkyMCIgaGVpZ2h0PSI0NCIgZmlsbD0iI2ZmZmZmZiIvPgoKICA8dGV4dCB4PSIzNCIgeT0iMTQzIiBmb250LXNpemU9IjEzIiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjMjU2M2ViIj50eXBlZC1hcmVuYTwvdGV4dD4KICA8dGV4dCB4PSIzNCIgeT0iMTg3IiBmb250LXNpemU9IjEzIiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjMjU2M2ViIj5idW1wYWxvPC90ZXh0PgogIDx0ZXh0IHg9IjM0IiB5PSIyMzEiIGZvbnQtc2l6ZT0iMTMiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiNkOTc3MDYiPmlkLWFyZW5hPC90ZXh0PgogIDx0ZXh0IHg9IjM0IiB5PSIyNzMiIGZvbnQtc2l6ZT0iMTEuNSIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iI2Q5NzcwNiI+Z2VuZXJhdGlvbmFsLWFyZW5hPC90ZXh0PgogIDx0ZXh0IHg9IjM0IiB5PSIzMTkiIGZvbnQtc2l6ZT0iMTMiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiNkOTc3MDYiPnNsb3RtYXA8L3RleHQ+CiAgPHRleHQgeD0iMzQiIHk9IjM2MyIgZm9udC1zaXplPSIxMyIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iI2Q5NzcwNiI+c2xhYjwvdGV4dD4KICA8dGV4dCB4PSIzNCIgeT0iNDA3IiBmb250LXNpemU9IjEzIiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjZDk3NzA2Ij50aHVuZGVyZG9tZTwvdGV4dD4KCiAgPGcgZm9udC1zaXplPSIxMiIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZmlsbD0iIzMzNDE1NSIgZm9udC1mYW1pbHk9Im1vbm9zcGFjZSI+CiAgPHRleHQgeD0iMjE1IiB5PSIxNDMiPiZhbXA7bXV0IFQ8L3RleHQ+CiAgPHRleHQgeD0iMjE1IiB5PSIxODciPiZhbXA7bXV0IFQ8L3RleHQ+CiAgPHRleHQgeD0iMjE1IiB5PSIyMzEiPklkJmx0O1QmZ3Q7PC90ZXh0PgogIDx0ZXh0IHg9IjIxNSIgeT0iMjc1Ij5JbmRleDwvdGV4dD4KICA8dGV4dCB4PSIyMTUiIHk9IjMxOSI+S2V5PC90ZXh0PgogIDx0ZXh0IHg9IjIxNSIgeT0iMzYzIj51c2l6ZTwvdGV4dD4KICA8dGV4dCB4PSIyMTUiIHk9IjQwNyI+SW5kZXg8L3RleHQ+CiAgPC9nPgoKICA8ZyBmb250LXNpemU9IjE3IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LXdlaWdodD0iNzAwIj4KICA8dGV4dCB4PSIzMzUiIHk9IjE0NCIgZmlsbD0iI2VmNDQ0NCI+4pyXPC90ZXh0Pjx0ZXh0IHg9IjQ0NSIgeT0iMTQ0IiBmaWxsPSIjZWY0NDQ0Ij7inJc8L3RleHQ+PHRleHQgeD0iNTU1IiB5PSIxNDQiIGZpbGw9IiM5NGEzYjgiPuKAlDwvdGV4dD48dGV4dCB4PSI2NjUiIHk9IjE0NCIgZmlsbD0iIzE2YTM0YSI+4pyTPC90ZXh0Pjx0ZXh0IHg9Ijc3NSIgeT0iMTQ0IiBmaWxsPSIjMTZhMzRhIj7inJM8L3RleHQ+PHRleHQgeD0iODg1IiB5PSIxNDQiIGZpbGw9IiNlZjQ0NDQiPuKclzwvdGV4dD4KICA8dGV4dCB4PSIzMzUiIHk9IjE4OCIgZmlsbD0iIzE2YTM0YSI+4pyTPC90ZXh0Pjx0ZXh0IHg9IjQ0NSIgeT0iMTg0IiBmaWxsPSIjZWY0NDQ0Ij7inJc8L3RleHQ+PHRleHQgeD0iNDQ1IiB5PSIxOTkiIGZvbnQtc2l6ZT0iOCIgZm9udC13ZWlnaHQ9IjQwMCIgZmlsbD0iIzk0YTNiOCI+5pW05L2TIHJlc2V0PC90ZXh0Pjx0ZXh0IHg9IjU1NSIgeT0iMTg4IiBmaWxsPSIjOTRhM2I4Ij7igJQ8L3RleHQ+PHRleHQgeD0iNjY1IiB5PSIxODQiIGZpbGw9IiNlZjQ0NDQiPuKclzwvdGV4dD48dGV4dCB4PSI2NjUiIHk9IjE5OSIgZm9udC1zaXplPSI4IiBmb250LXdlaWdodD0iNDAwIiBmaWxsPSIjYjkxYzFjIj7pu5jorqTkuI3ot5E8L3RleHQ+PHRleHQgeD0iNzc1IiB5PSIxODgiIGZpbGw9IiMxNmEzNGEiPuKckzwvdGV4dD48dGV4dCB4PSI4ODUiIHk9IjE4OCIgZmlsbD0iIzE2YTM0YSI+4pyTPC90ZXh0PgogIDx0ZXh0IHg9IjMzNSIgeT0iMjMyIiBmaWxsPSIjZWY0NDQ0Ij7inJc8L3RleHQ+PHRleHQgeD0iNDQ1IiB5PSIyMzIiIGZpbGw9IiNlZjQ0NDQiPuKclzwvdGV4dD48dGV4dCB4PSI1NTUiIHk9IjIzMiIgZmlsbD0iI2VmNDQ0NCI+4pyXPC90ZXh0Pjx0ZXh0IHg9IjY2NSIgeT0iMjMyIiBmaWxsPSIjMTZhMzRhIj7inJM8L3RleHQ+PHRleHQgeD0iNzc1IiB5PSIyMzIiIGZpbGw9IiMxNmEzNGEiPuKckzwvdGV4dD48dGV4dCB4PSI4ODUiIHk9IjIzMiIgZmlsbD0iI2VmNDQ0NCI+4pyXPC90ZXh0PgogIDx0ZXh0IHg9IjMzNSIgeT0iMjc2IiBmaWxsPSIjZWY0NDQ0Ij7inJc8L3RleHQ+PHRleHQgeD0iNDQ1IiB5PSIyNzYiIGZpbGw9IiMxNmEzNGEiPuKckzwvdGV4dD48dGV4dCB4PSI1NTUiIHk9IjI3NiIgZmlsbD0iIzE2YTM0YSI+4pyTPC90ZXh0Pjx0ZXh0IHg9IjY2NSIgeT0iMjc2IiBmaWxsPSIjMTZhMzRhIj7inJM8L3RleHQ+PHRleHQgeD0iNzc1IiB5PSIyNzYiIGZpbGw9IiMxNmEzNGEiPuKckzwvdGV4dD48dGV4dCB4PSI4ODUiIHk9IjI3NiIgZmlsbD0iI2VmNDQ0NCI+4pyXPC90ZXh0PgogIDx0ZXh0IHg9IjMzNSIgeT0iMzIwIiBmaWxsPSIjZWY0NDQ0Ij7inJc8L3RleHQ+PHRleHQgeD0iNDQ1IiB5PSIzMjAiIGZpbGw9IiMxNmEzNGEiPuKckzwvdGV4dD48dGV4dCB4PSI1NTUiIHk9IjMyMCIgZmlsbD0iIzE2YTM0YSI+4pyTPC90ZXh0Pjx0ZXh0IHg9IjY2NSIgeT0iMzIwIiBmaWxsPSIjMTZhMzRhIj7inJM8L3RleHQ+PHRleHQgeD0iNzc1IiB5PSIzMjAiIGZpbGw9IiMxNmEzNGEiPuKckzwvdGV4dD48dGV4dCB4PSI4ODUiIHk9IjMyMCIgZmlsbD0iI2VmNDQ0NCI+4pyXPC90ZXh0PgogIDx0ZXh0IHg9IjMzNSIgeT0iMzY0IiBmaWxsPSIjZWY0NDQ0Ij7inJc8L3RleHQ+PHRleHQgeD0iNDQ1IiB5PSIzNjQiIGZpbGw9IiMxNmEzNGEiPuKckzwvdGV4dD48dGV4dCB4PSI1NTUiIHk9IjM2MCIgZmlsbD0iI2VmNDQ0NCI+4pyXPC90ZXh0Pjx0ZXh0IHg9IjU1NSIgeT0iMzc1IiBmb250LXNpemU9IjgiIGZvbnQtd2VpZ2h0PSI0MDAiIGZpbGw9IiNiOTFjMWMiPnN0YWxlIOmjjumZqTwvdGV4dD48dGV4dCB4PSI2NjUiIHk9IjM2NCIgZmlsbD0iIzE2YTM0YSI+4pyTPC90ZXh0Pjx0ZXh0IHg9Ijc3NSIgeT0iMzY0IiBmaWxsPSIjMTZhMzRhIj7inJM8L3RleHQ+PHRleHQgeD0iODg1IiB5PSIzNjQiIGZpbGw9IiNlZjQ0NDQiPuKclzwvdGV4dD4KICA8dGV4dCB4PSIzMzUiIHk9IjQwOCIgZmlsbD0iI2VmNDQ0NCI+4pyXPC90ZXh0Pjx0ZXh0IHg9IjQ0NSIgeT0iNDA4IiBmaWxsPSIjMTZhMzRhIj7inJM8L3RleHQ+PHRleHQgeD0iNTU1IiB5PSI0MDgiIGZpbGw9IiMxNmEzNGEiPuKckzwvdGV4dD48dGV4dCB4PSI2NjUiIHk9IjQwOCIgZmlsbD0iIzE2YTM0YSI+4pyTPC90ZXh0Pjx0ZXh0IHg9Ijc3NSIgeT0iNDA4IiBmaWxsPSIjMTZhMzRhIj7inJM8L3RleHQ+PHRleHQgeD0iODg1IiB5PSI0MDgiIGZpbGw9IiNlZjQ0NDQiPuKclzwvdGV4dD4KICA8L2c+CgogIDxyZWN0IHg9IjIwIiB5PSI2NCIgd2lkdGg9IjkyMCIgaGVpZ2h0PSIzNjAiIGZpbGw9Im5vbmUiIHN0cm9rZT0iI2NiZDVlMSIgc3Ryb2tlLXdpZHRoPSIxLjUiLz4KICA8ZyBzdHJva2U9IiNlMmU4ZjAiIHN0cm9rZS13aWR0aD0iMSI+CiAgICA8bGluZSB4MT0iMTUwIiB5MT0iMTE2IiB4Mj0iMTUwIiB5Mj0iNDI0Ii8+PGxpbmUgeDE9IjI4MCIgeTE9IjExNiIgeDI9IjI4MCIgeTI9IjQyNCIvPgogICAgPGxpbmUgeDE9IjM5MCIgeTE9IjExNiIgeDI9IjM5MCIgeTI9IjQyNCIvPjxsaW5lIHgxPSI1MDAiIHkxPSIxMTYiIHgyPSI1MDAiIHkyPSI0MjQiLz4KICAgIDxsaW5lIHgxPSI2MTAiIHkxPSIxMTYiIHgyPSI2MTAiIHkyPSI0MjQiLz48bGluZSB4MT0iNzIwIiB5MT0iMTE2IiB4Mj0iNzIwIiB5Mj0iNDI0Ii8+PGxpbmUgeDE9IjgzMCIgeTE9IjExNiIgeDI9IjgzMCIgeTI9IjQyNCIvPgogIDwvZz4KICA8bGluZSB4MT0iMjAiIHkxPSIxMTYiIHgyPSI5NDAiIHkyPSIxMTYiIHN0cm9rZT0iI2NiZDVlMSIgc3Ryb2tlLXdpZHRoPSIxLjUiLz4KCiAgPHRleHQgeD0iNDgwIiB5PSI0NDgiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtc2l6ZT0iMTAuNSIgZmlsbD0iIzk0YTNiOCI+bm9fc3RkIOWkmuS4uiBmZWF0dXJlLWdhdGVk77yIZGVmYXVsdC1mZWF0dXJlcz1mYWxzZe+8ie+8m+S+i+Wklu+8mmxhLWFyZW5hIOS4jiBlbHNhIOS4jeaUr+aMgSBub19zdGTjgIJnZW5lcmF0aW9uYWwtYXJlbmEg5bey5YGc57u0KE1QTC0yLjAp77yMSG9wU2xvdE1hcCDoh6ogMS4xIOi1t+W6n+W8g+OAgjwvdGV4dD4KPC9zdmc+Cg=="/>
</p>
<p align="center"><sub><b>图 4</b> · 主流 arena crate 特性能力矩阵</sub></p>

速记：**异构**只有 bump 型（bumpalo/blink-alloc/bump-scope）支持；**单独删除 + 代际安全**是 slotmap/thunderdome 的招牌（generational-arena 同类但已停维）；**跑 Drop** 除 bumpalo 默认不跑外基本都跑；**no_std** 大多支持（多为 feature-gated），**例外是 la-arena 与 elsa**。

---

## 7. 选型定位象限图

<p align="center">
<img alt="选型定位象限图" style="width:100%;max-width:840px;height:auto;" src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA4NDAgNTgwIiBmb250LWZhbWlseT0iJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJywnU2Vnb2UgVUknLHNhbnMtc2VyaWYiPgogIDxkZWZzPgogICAgPG1hcmtlciBpZD0iYXgiIG1hcmtlcldpZHRoPSIxMSIgbWFya2VySGVpZ2h0PSIxMSIgcmVmWD0iOSIgcmVmWT0iNCIgb3JpZW50PSJhdXRvIj48cGF0aCBkPSJNMCwwIEwxMCw0IEwwLDggWiIgZmlsbD0iIzQ3NTU2OSIvPjwvbWFya2VyPgogIDwvZGVmcz4KICA8cmVjdCB3aWR0aD0iODQwIiBoZWlnaHQ9IjU4MCIgZmlsbD0iI2Y4ZmFmYyIvPgogIDx0ZXh0IHg9IjQyMCIgeT0iMzQiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtc2l6ZT0iMjMiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiMwZjE3MmEiPumAieWei+WumuS9jeixoemZkOWbvjwvdGV4dD4KICA8dGV4dCB4PSI0MjAiIHk9IjU2IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LXNpemU9IjEyLjUiIGZpbGw9IiM2NDc0OGIiPuaoqui9tCA9IOWGheWtmOWbnuaUtueykuW6puOAgOe6tei9tCA9IOiKgueCueaAjuagt+iiq+W8leeUqDwvdGV4dD4KCiAgPCEtLSBxdWFkcmFudCB0aW50cyAtLT4KICA8cmVjdCB4PSI5MCIgeT0iOTAiIHdpZHRoPSIzNDUiIGhlaWdodD0iMjA1IiBmaWxsPSIjZWZmNmZmIi8+CiAgPHJlY3QgeD0iNDM1IiB5PSI5MCIgd2lkdGg9IjM0NSIgaGVpZ2h0PSIyMDUiIGZpbGw9IiNmMWY1ZjkiLz4KICA8cmVjdCB4PSI5MCIgeT0iMjk1IiB3aWR0aD0iMzQ1IiBoZWlnaHQ9IjIwNSIgZmlsbD0iI2ZmZjdlZCIvPgogIDxyZWN0IHg9IjQzNSIgeT0iMjk1IiB3aWR0aD0iMzQ1IiBoZWlnaHQ9IjIwNSIgZmlsbD0iI2YwZmRmNCIvPgogIDxyZWN0IHg9IjkwIiB5PSI5MCIgd2lkdGg9IjY5MCIgaGVpZ2h0PSI0MTAiIGZpbGw9Im5vbmUiIHN0cm9rZT0iI2NiZDVlMSIvPgoKICA8IS0tIGF4ZXMgLS0+CiAgPGxpbmUgeDE9IjgyIiB5MT0iMjk1IiB4Mj0iNzkyIiB5Mj0iMjk1IiBzdHJva2U9IiM0NzU1NjkiIHN0cm9rZS13aWR0aD0iMS44IiBtYXJrZXItZW5kPSJ1cmwoI2F4KSIvPgogIDxsaW5lIHgxPSI4OCIgeTE9IjI5NSIgeDI9Ijc4IiB5Mj0iMjk1IiBzdHJva2U9IiM0NzU1NjkiIHN0cm9rZS13aWR0aD0iMS44IiBtYXJrZXItZW5kPSJ1cmwoI2F4KSIvPgogIDxsaW5lIHgxPSI0MzUiIHkxPSI1MDgiIHgyPSI0MzUiIHkyPSI4MiIgc3Ryb2tlPSIjNDc1NTY5IiBzdHJva2Utd2lkdGg9IjEuOCIgbWFya2VyLWVuZD0idXJsKCNheCkiLz4KICA8bGluZSB4MT0iNDM1IiB5MT0iNTAyIiB4Mj0iNDM1IiB5Mj0iNTEyIiBzdHJva2U9IiM0NzU1NjkiIHN0cm9rZS13aWR0aD0iMS44IiBtYXJrZXItZW5kPSJ1cmwoI2F4KSIvPgoKICA8IS0tIGF4aXMgbGFiZWxzIC0tPgogIDx0ZXh0IHg9IjEwNCIgeT0iMzE1IiBmb250LXNpemU9IjEyLjUiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiM0NzU1NjkiPuaVtOS9kyAvIOaJuemHj+mHiuaUvjwvdGV4dD4KICA8dGV4dCB4PSI3NzYiIHk9IjMxNSIgdGV4dC1hbmNob3I9ImVuZCIgZm9udC1zaXplPSIxMi41IiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjNDc1NTY5Ij7lj6/ljZXni6zliKDpmaQgwrcg5aSN55SoPC90ZXh0PgogIDx0ZXh0IHg9IjQ0NSIgeT0iMTAyIiBmb250LXNpemU9IjEyLjUiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiM0NzU1NjkiPui/lOWbnuW8leeUqCAmYW1wO1Q8L3RleHQ+CiAgPHRleHQgeD0iNDQ1IiB5PSI0OTUiIGZvbnQtc2l6ZT0iMTIuNSIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iIzQ3NTU2OSI+6L+U5Zue5Y+l5p+EIEluZGV4L0tleTwvdGV4dD4KCiAgPCEtLSB0b3AtbGVmdCBwaWxscyAoYnVtcCBmYW1pbHkpIC0tPgogIDxnIGZvbnQtc2l6ZT0iMTEuNSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC13ZWlnaHQ9IjcwMCI+CiAgPHJlY3QgeD0iMTIwIiB5PSIxMzIiIHdpZHRoPSIxMTAiIGhlaWdodD0iMzAiIHJ4PSI3IiBmaWxsPSIjZmZmIiBzdHJva2U9IiMyNTYzZWIiIHN0cm9rZS13aWR0aD0iMS42Ii8+PHRleHQgeD0iMTc1IiB5PSIxNTIiIGZpbGw9IiMxZTNhOGEiPnR5cGVkLWFyZW5hPC90ZXh0PgogIDxyZWN0IHg9IjI2MiIgeT0iMTMyIiB3aWR0aD0iODYiIGhlaWdodD0iMzAiIHJ4PSI3IiBmaWxsPSIjZmZmIiBzdHJva2U9IiMyNTYzZWIiIHN0cm9rZS13aWR0aD0iMS42Ii8+PHRleHQgeD0iMzA1IiB5PSIxNTIiIGZpbGw9IiMxZTNhOGEiPmJ1bXBhbG88L3RleHQ+CiAgPHJlY3QgeD0iMTI4IiB5PSIxODAiIHdpZHRoPSIxMDIiIGhlaWdodD0iMzAiIHJ4PSI3IiBmaWxsPSIjZmZmIiBzdHJva2U9IiMyNTYzZWIiIHN0cm9rZS13aWR0aD0iMS42Ii8+PHRleHQgeD0iMTc5IiB5PSIyMDAiIGZpbGw9IiMxZTNhOGEiPmJsaW5rLWFsbG9jPC90ZXh0PgogIDxyZWN0IHg9IjI1OCIgeT0iMTgwIiB3aWR0aD0iMTAyIiBoZWlnaHQ9IjMwIiByeD0iNyIgZmlsbD0iI2ZmZiIgc3Ryb2tlPSIjMjU2M2ViIiBzdHJva2Utd2lkdGg9IjEuNiIvPjx0ZXh0IHg9IjMwOSIgeT0iMjAwIiBmaWxsPSIjMWUzYThhIj5idW1wLXNjb3BlPC90ZXh0PgogIDxyZWN0IHg9IjE5MCIgeT0iMjMyIiB3aWR0aD0iMTEwIiBoZWlnaHQ9IjMwIiByeD0iNyIgZmlsbD0iI2ZmZiIgc3Ryb2tlPSIjN2MzYWVkIiBzdHJva2Utd2lkdGg9IjEuNiIvPjx0ZXh0IHg9IjI0NSIgeT0iMjUyIiBmaWxsPSIjNmIyMWE4Ij5lbHNhIChhcHBlbmQpPC90ZXh0PgogIDwvZz4KCiAgPCEtLSBib3R0b20tbGVmdCBwaWxscyAoaGFuZGxlLCBhcHBlbmQtb25seSkgLS0+CiAgPGcgZm9udC1zaXplPSIxMS41IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LXdlaWdodD0iNzAwIj4KICA8cmVjdCB4PSIxNTAiIHk9IjM2MCIgd2lkdGg9IjkyIiBoZWlnaHQ9IjMwIiByeD0iNyIgZmlsbD0iI2ZmZiIgc3Ryb2tlPSIjZDk3NzA2IiBzdHJva2Utd2lkdGg9IjEuNiIvPjx0ZXh0IHg9IjE5NiIgeT0iMzgwIiBmaWxsPSIjOWEzNDEyIj5pZC1hcmVuYTwvdGV4dD4KICA8cmVjdCB4PSIyNjIiIHk9IjQxMCIgd2lkdGg9IjkyIiBoZWlnaHQ9IjMwIiByeD0iNyIgZmlsbD0iI2ZmZiIgc3Ryb2tlPSIjZDk3NzA2IiBzdHJva2Utd2lkdGg9IjEuNiIvPjx0ZXh0IHg9IjMwOCIgeT0iNDMwIiBmaWxsPSIjOWEzNDEyIj5sYS1hcmVuYTwvdGV4dD4KICA8L2c+CgogIDwhLS0gYm90dG9tLXJpZ2h0IHBpbGxzIChoYW5kbGUsIGRlbGV0YWJsZSkgLS0+CiAgPGcgZm9udC1zaXplPSIxMS41IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LXdlaWdodD0iNzAwIj4KICA8cmVjdCB4PSI1MDAiIHk9IjM1MiIgd2lkdGg9IjkyIiBoZWlnaHQ9IjMwIiByeD0iNyIgZmlsbD0iI2ZmZiIgc3Ryb2tlPSIjMTZhMzRhIiBzdHJva2Utd2lkdGg9IjEuNiIvPjx0ZXh0IHg9IjU0NiIgeT0iMzcyIiBmaWxsPSIjMTY2NTM0Ij5zbG90bWFwPC90ZXh0PgogIDxyZWN0IHg9IjYxMiIgeT0iMzUyIiB3aWR0aD0iMTE2IiBoZWlnaHQ9IjMwIiByeD0iNyIgZmlsbD0iI2ZmZiIgc3Ryb2tlPSIjMTZhMzRhIiBzdHJva2Utd2lkdGg9IjEuNiIvPjx0ZXh0IHg9IjY3MCIgeT0iMzcyIiBmaWxsPSIjMTY2NTM0Ij50aHVuZGVyZG9tZTwvdGV4dD4KICA8cmVjdCB4PSI1MTIiIHk9IjQwNiIgd2lkdGg9IjcwIiBoZWlnaHQ9IjMwIiByeD0iNyIgZmlsbD0iI2ZmZiIgc3Ryb2tlPSIjMTZhMzRhIiBzdHJva2Utd2lkdGg9IjEuNiIvPjx0ZXh0IHg9IjU0NyIgeT0iNDI2IiBmaWxsPSIjMTY2NTM0Ij5zbGFiPC90ZXh0PgogIDxyZWN0IHg9IjU3NCIgeT0iNDUyIiB3aWR0aD0iMTgwIiBoZWlnaHQ9IjMwIiByeD0iNyIgZmlsbD0iI2ZmZiIgc3Ryb2tlPSIjOWNhM2FmIiBzdHJva2Utd2lkdGg9IjEuNCIgc3Ryb2tlLWRhc2hhcnJheT0iNCAzIi8+PHRleHQgeD0iNjY0IiB5PSI0NzIiIGZvbnQtc2l6ZT0iMTAuNSIgZmlsbD0iIzZiNzI4MCI+Z2VuZXJhdGlvbmFsLWFyZW5hIOKaoOWBnOe7tDwvdGV4dD4KICA8L2c+CgogIDwhLS0gdG9wLXJpZ2h0IGVtcHR5IG5vdGUgLS0+CiAgPHRleHQgeD0iNjA4IiB5PSIxNzAiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtc2l6ZT0iMTIiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiM5NGEzYjgiPuKJiCDln7rmnKzkuLrnqbo8L3RleHQ+CiAgPHRleHQgeD0iNjA4IiB5PSIxOTIiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtc2l6ZT0iMTAuNSIgZmlsbD0iIzk0YTNiOCI+5pei5Lqk6KO45byV55SoICZhbXA7VOOAgeWPiOiDveWNleeLrOmHiuaUvu+8jDwvdGV4dD4KICA8dGV4dCB4PSI2MDgiIHk9IjIwOCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1zaXplPSIxMC41IiBmaWxsPSIjOTRhM2I4Ij7lvojpmr7lkIzml7bkv53or4HlhoXlrZjlronlhag8L3RleHQ+CgogIDx0ZXh0IHg9IjQyMCIgeT0iNTQyIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LXNpemU9IjExLjUiIGZpbGw9IiM0NzU1NjkiPuW3puWIl+OAjOaVtOS9k+mHiuaUvuOAjT0gQnVtcC/lj6rov73liqDvvJvlj7PliJfjgIzlj6/liKDpmaTjgI3lv4XnhLbotbDlj6Xmn4TlnovvvIjku6PpmYXlj6Xmn4TmiY3pmLLmgqzlnoLvvIk8L3RleHQ+Cjwvc3ZnPgo="/>
</p>
<p align="center"><sub><b>图 5</b> · 按「回收粒度 × 引用方式」定位各 crate</sub></p>

两根轴就能把候选迅速收敛：**横轴**=内存回收粒度（只能整体释放 ↔ 可单独删除复用），**纵轴**=节点引用方式（返回 `&T` ↔ 返回句柄）。注意右上象限（既交裸引用又能单独释放）**基本为空**——因为这很难同时保证内存安全，这正是「要删除就得用句柄型」的根本原因。

---

## 8. 性能视角

<p align="center">
<img alt="分配吞吐示意" style="width:100%;max-width:780px;height:auto;" src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA3ODAgNDQwIiBmb250LWZhbWlseT0iJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJywnU2Vnb2UgVUknLHNhbnMtc2VyaWYiPgogIDxyZWN0IHdpZHRoPSI3ODAiIGhlaWdodD0iNDQwIiBmaWxsPSIjZjhmYWZjIi8+CiAgPHRleHQgeD0iMzkwIiB5PSIzMiIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1zaXplPSIyMiIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iIzBmMTcyYSI+5YiG6YWN5ZCe5ZCQ56S65oSP77yI6LaK6ZW/6LaK5b+r77yJPC90ZXh0PgogIDx0ZXh0IHg9IjM5MCIgeT0iNTQiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtc2l6ZT0iMTIiIGZpbGw9IiNkYzI2MjYiPuKaoCDnpLrmhI/mgKfnm7jlr7nlgLzvvIzlu7rnq4vnm7Top4nnlKjvvIzpnZ7lrp7mtYvln7rlh4bvvJvliqHlv4XnlKjkvaDnmoTotJ/ovb3ot5EgY3JpdGVyaW9uPC90ZXh0PgoKICA8bGluZSB4MT0iMTkwIiB5MT0iOTIiIHgyPSIxOTAiIHkyPSIzNzIiIHN0cm9rZT0iI2NiZDVlMSIgc3Ryb2tlLXdpZHRoPSIxLjUiLz4KCiAgPHRleHQgeD0iMTgyIiB5PSIxMjUiIHRleHQtYW5jaG9yPSJlbmQiIGZvbnQtc2l6ZT0iMTIuNSIgZmlsbD0iIzMzNDE1NSI+YnVtcGFsbzwvdGV4dD4KICA8cmVjdCB4PSIxOTAiIHk9IjEwNiIgd2lkdGg9IjQ5MCIgaGVpZ2h0PSIyOCIgcng9IjQiIGZpbGw9IiMyNTYzZWIiLz48dGV4dCB4PSI2ODgiIHk9IjEyNSIgZm9udC1zaXplPSIxMiIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iIzFlM2E4YSI+OTg8L3RleHQ+CiAgPHRleHQgeD0iMTgyIiB5PSIxNzMiIHRleHQtYW5jaG9yPSJlbmQiIGZvbnQtc2l6ZT0iMTIuNSIgZmlsbD0iIzMzNDE1NSI+YmxpbmstYWxsb2M8L3RleHQ+CiAgPHJlY3QgeD0iMTkwIiB5PSIxNTQiIHdpZHRoPSI0ODUiIGhlaWdodD0iMjgiIHJ4PSI0IiBmaWxsPSIjMjU2M2ViIi8+PHRleHQgeD0iNjgzIiB5PSIxNzMiIGZvbnQtc2l6ZT0iMTIiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiMxZTNhOGEiPjk3PC90ZXh0PgogIDx0ZXh0IHg9IjE4MiIgeT0iMjIxIiB0ZXh0LWFuY2hvcj0iZW5kIiBmb250LXNpemU9IjEyLjUiIGZpbGw9IiMzMzQxNTUiPnR5cGVkLWFyZW5hPC90ZXh0PgogIDxyZWN0IHg9IjE5MCIgeT0iMjAyIiB3aWR0aD0iNDY1IiBoZWlnaHQ9IjI4IiByeD0iNCIgZmlsbD0iIzNiODJmNiIvPjx0ZXh0IHg9IjY2MyIgeT0iMjIxIiBmb250LXNpemU9IjEyIiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjMWUzYThhIj45MzwvdGV4dD4KICA8dGV4dCB4PSIxODIiIHk9IjI2OSIgdGV4dC1hbmNob3I9ImVuZCIgZm9udC1zaXplPSIxMi41IiBmaWxsPSIjMzM0MTU1Ij5zbGFi77yI57Si5byV77yJPC90ZXh0PgogIDxyZWN0IHg9IjE5MCIgeT0iMjUwIiB3aWR0aD0iNDEwIiBoZWlnaHQ9IjI4IiByeD0iNCIgZmlsbD0iI2Q5NzcwNiIvPjx0ZXh0IHg9IjYwOCIgeT0iMjY5IiBmb250LXNpemU9IjEyIiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjOWEzNDEyIj44MjwvdGV4dD4KICA8dGV4dCB4PSIxODIiIHk9IjMxNyIgdGV4dC1hbmNob3I9ImVuZCIgZm9udC1zaXplPSIxMi41IiBmaWxsPSIjMzM0MTU1Ij5zbG90bWFw77yI57Si5byVK+S7o+mZhe+8iTwvdGV4dD4KICA8cmVjdCB4PSIxOTAiIHk9IjI5OCIgd2lkdGg9IjM2MCIgaGVpZ2h0PSIyOCIgcng9IjQiIGZpbGw9IiNkOTc3MDYiLz48dGV4dCB4PSI1NTgiIHk9IjMxNyIgZm9udC1zaXplPSIxMiIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iIzlhMzQxMiI+NzI8L3RleHQ+CiAgPHRleHQgeD0iMTgyIiB5PSIzNjUiIHRleHQtYW5jaG9yPSJlbmQiIGZvbnQtc2l6ZT0iMTIuNSIgZmlsbD0iIzMzNDE1NSI+Qm94OjpuZXfvvIjns7vnu58gbWFsbG9j77yJPC90ZXh0PgogIDxyZWN0IHg9IjE5MCIgeT0iMzQ2IiB3aWR0aD0iMTcwIiBoZWlnaHQ9IjI4IiByeD0iNCIgZmlsbD0iIzk0YTNiOCIvPjx0ZXh0IHg9IjM2OCIgeT0iMzY1IiBmb250LXNpemU9IjEyIiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjNDc1NTY5Ij4zNCDCtyDln7rnur88L3RleHQ+CgogIDxyZWN0IHg9IjQwIiB5PSIzOTIiIHdpZHRoPSI3MDAiIGhlaWdodD0iNDAiIHJ4PSI4IiBmaWxsPSIjZWZmNmZmIi8+CiAgPHRleHQgeD0iNTYiIHk9IjQwOSIgZm9udC1zaXplPSIxMSIgZmlsbD0iIzFlNDBhZiI+4oCiIEJ1bXAg5YiG6YWNID0g5oyH6ZKI6YCS5aKe77yM6L+c5b+r5LqOIG1hbGxvY++8m+WPpeafhOWei+WkmuS4gOWxgiBWZWMg6K6w6LSmL+S7o+mZheagoemqjO+8jOS4lDx0c3BhbiBmb250LXdlaWdodD0iNzAwIj7orr/pl67ml7blpJrkuIDmrKHpl7TmjqXlr7vlnYA8L3RzcGFuPjwvdGV4dD4KICA8dGV4dCB4PSI1NiIgeT0iNDI1IiBmb250LXNpemU9IjExIiBmaWxsPSIjNDc1NTY5Ij7igKIg55yf5a6e5oCn6IO96L+Y5Y+W5Yaz5LqO5YiG6YWN5aSn5bCP44CB6K6/6Zeu5qih5byP44CB5piv5ZCm6Kem5Y+RIGNodW5rIOaJqeWuuSDigJTigJQg5Lul6Ieq5rWL5Li65YeGPC90ZXh0Pgo8L3N2Zz4K"/>
</p>
<p align="center"><sub><b>图 6</b> · 分配吞吐示意（相对值，非实测基准）</sub></p>

- **Bump 型分配最快**：指针递增，远快于 `malloc`/`Box::new`；适合海量短命对象。
- **句柄型**在分配路径上多一层 `Vec` 记账 / 代际校验，**访问时还多一次间接寻址 + 边界检查**，但换来删除能力与 `Copy` 句柄。
- **务必自测**：实际性能还取决于对象大小、访问模式、是否触发 chunk 扩容。上图仅为建立直觉的相对示意，不是可引用的基准。

---

## 9. 横向对比总表

| crate | 类别 | 返回 | 异构 | 删除 | 代际 | 跑 Drop | no_std | 最新版 | 许可 | 代表采用方 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| typed-arena | Bump | `&mut T` | ✗ | ✗ | — | ✓ | ✓ | 2.0.2 | MIT | （元老） |
| bumpalo | Bump | `&mut T` | ✓ | reset | — | ✗默认 | ✓ | 3.20.3 | MIT/Apache | wasm-bindgen·SWC·typst |
| blink-alloc | Bump | `&mut T`/裸 | ✓ | tip/reset | — | ✓ | ✓ | 0.4.0 | MIT/Apache | （小众） |
| bump-scope | Bump | `BumpBox<T>` | ✓ | scope | — | ✓总是 | ✓ | 2.3.3 | MIT/Apache | — |
| id-arena | Handle | `Id<T>` | ✗ | ✗ | ✗ | ✓ | ✓ | 2.3.0 | MIT/Apache | walrus·wit-parser |
| generational-arena ⚠ | Handle | `Index` | ✗ | ✓ | ✓ | ✓ | ✓ | 0.2.9 停维 | MPL-2.0 | （荐迁 slotmap） |
| slotmap | Handle | `Key` | ✗ | ✓ | ✓ | ✓ | ✓ | 1.1.1 | Zlib | bevy·Zed·dioxus·polars |
| slab | Handle | `usize` | ✗ | ✓ | ✗ | ✓ | ✓ | 0.4.12 | MIT | tokio·h2·tower·quinn |
| thunderdome | Handle | `Index`(8B) | ✗ | ✓ | ✓ | ✓ | ✓ | 0.6.1 | MIT/Apache | yakui·firewheel |
| la-arena | Handle | `Idx<T>` | ✗ | ✗ | ✗ | ✓ | ✗ | 0.3.1 | MIT/Apache | rust-analyzer |
| elsa | append-only | `&T` 真引用 | ✗ | ✗ | — | ✓ | ✗ | 1.11.2 | MIT/Apache | rustc·ICU4X·Typst |
| lasso | interner | `Spur` | — | — | — | — | — | 0.7.3 | MIT/Apache | （字符串驻留） |
| string-interner | interner | `SymbolU32` | — | — | — | — | — | 0.20.0 | MIT/Apache | wasmi·tract |

---

## 10. 选型决策树

<p align="center">
<img alt="Arena 选型决策树" style="width:100%;max-width:980px;height:auto;" src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA5ODAgNTAwIiBmb250LWZhbWlseT0iJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJywnU2Vnb2UgVUknLHNhbnMtc2VyaWYiPgogIDxyZWN0IHdpZHRoPSI5ODAiIGhlaWdodD0iNTAwIiBmaWxsPSIjZjhmYWZjIi8+CiAgPHRleHQgeD0iNDkwIiB5PSIzMCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1zaXplPSIyMyIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iIzBmMTcyYSI+QXJlbmEg6YCJ5Z6L5Yaz562W5qCRPC90ZXh0PgoKICA8IS0tIHJvb3QgY29ubmVjdG9ycyAtLT4KICA8bGluZSB4MT0iNDkwIiB5MT0iODQiIHgyPSI0OTAiIHkyPSIxMDgiIHN0cm9rZT0iIzk0YTNiOCIgc3Ryb2tlLXdpZHRoPSIxLjgiLz4KICA8bGluZSB4MT0iMjcwIiB5MT0iMTA4IiB4Mj0iNzEwIiB5Mj0iMTA4IiBzdHJva2U9IiM5NGEzYjgiIHN0cm9rZS13aWR0aD0iMS44Ii8+CiAgPGxpbmUgeDE9IjI3MCIgeTE9IjEwOCIgeDI9IjI3MCIgeTI9IjEzNCIgc3Ryb2tlPSIjOTRhM2I4IiBzdHJva2Utd2lkdGg9IjEuOCIvPgogIDxsaW5lIHgxPSI3MTAiIHkxPSIxMDgiIHgyPSI3MTAiIHkyPSIxMzQiIHN0cm9rZT0iIzk0YTNiOCIgc3Ryb2tlLXdpZHRoPSIxLjgiLz4KICA8dGV4dCB4PSIzNzUiIHk9IjEwMiIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1zaXplPSIxMi41IiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjMjU2M2ViIj7lkKYgwrcg5pW05L2T6YeK5pS+PC90ZXh0PgogIDx0ZXh0IHg9IjYxMiIgeT0iMTAyIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LXNpemU9IjEyLjUiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiMxNmEzNGEiPuaYryDCtyDopoHliKDpmaTlpI3nlKg8L3RleHQ+CgogIDwhLS0gcm9vdCAtLT4KICA8cmVjdCB4PSIzMzAiIHk9IjM2IiB3aWR0aD0iMzIwIiBoZWlnaHQ9IjQ4IiByeD0iMjQiIGZpbGw9IiMxZTI5M2IiLz4KICA8dGV4dCB4PSI0OTAiIHk9IjY1IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LXNpemU9IjE1LjUiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiNmZmZmZmYiPumcgOimgeWNleeLrOWIoOmZpCAvIOWbnuaUtuS4quWIq+WvueixoeWQlz88L3RleHQ+CgogIDwhLS0gUTIgKGxlZnQpIC0tPgogIDxyZWN0IHg9IjEzMCIgeT0iMTM0IiB3aWR0aD0iMjgwIiBoZWlnaHQ9IjUyIiByeD0iMTIiIGZpbGw9IiNkYmVhZmUiIHN0cm9rZT0iIzI1NjNlYiIgc3Ryb2tlLXdpZHRoPSIxLjYiLz4KICA8dGV4dCB4PSIyNzAiIHk9IjE2NSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1zaXplPSIxMy41IiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjMWUzYThhIj7lkIzkuIAgYXJlbmEg5pS+5byC5p6E57G75Z6L5ZCXPzwvdGV4dD4KICA8IS0tIFEzIChyaWdodCkgLS0+CiAgPHJlY3QgeD0iNTYwIiB5PSIxMzQiIHdpZHRoPSIzMDAiIGhlaWdodD0iNTIiIHJ4PSIxMiIgZmlsbD0iI2RjZmNlNyIgc3Ryb2tlPSIjMTZhMzRhIiBzdHJva2Utd2lkdGg9IjEuNiIvPgogIDx0ZXh0IHg9IjcxMCIgeT0iMTY1IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LXNpemU9IjEzLjUiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiMxNjY1MzQiPuimgemYsuatoiBzdGFsZSDlj6Xmn4Qo5Luj6ZmF5a6J5YWoKeWQlz88L3RleHQ+CgogIDwhLS0gUTIgY29ubmVjdG9ycyAtLT4KICA8bGluZSB4MT0iMjcwIiB5MT0iMTg2IiB4Mj0iMjcwIiB5Mj0iMjE4IiBzdHJva2U9IiM5NGEzYjgiIHN0cm9rZS13aWR0aD0iMS44Ii8+CiAgPGxpbmUgeDE9IjE4MCIgeTE9IjIxOCIgeDI9IjM3NSIgeTI9IjIxOCIgc3Ryb2tlPSIjOTRhM2I4IiBzdHJva2Utd2lkdGg9IjEuOCIvPgogIDxsaW5lIHgxPSIxODAiIHkxPSIyMTgiIHgyPSIxODAiIHkyPSIyNTAiIHN0cm9rZT0iIzk0YTNiOCIgc3Ryb2tlLXdpZHRoPSIxLjgiLz4KICA8bGluZSB4MT0iMzc1IiB5MT0iMjE4IiB4Mj0iMzc1IiB5Mj0iMjUwIiBzdHJva2U9IiM5NGEzYjgiIHN0cm9rZS13aWR0aD0iMS44Ii8+CiAgPHRleHQgeD0iMTY2IiB5PSIyNDAiIHRleHQtYW5jaG9yPSJlbmQiIGZvbnQtc2l6ZT0iMTEuNSIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iIzY0NzQ4YiI+5pivPC90ZXh0PgogIDx0ZXh0IHg9IjM4OSIgeT0iMjQwIiB0ZXh0LWFuY2hvcj0ic3RhcnQiIGZvbnQtc2l6ZT0iMTEuNSIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iIzY0NzQ4YiI+5ZCmPC90ZXh0PgoKICA8IS0tIFEzIGNvbm5lY3RvcnMgLS0+CiAgPGxpbmUgeDE9IjcxMCIgeTE9IjE4NiIgeDI9IjcxMCIgeTI9IjIxOCIgc3Ryb2tlPSIjOTRhM2I4IiBzdHJva2Utd2lkdGg9IjEuOCIvPgogIDxsaW5lIHgxPSI2MjAiIHkxPSIyMTgiIHgyPSI4MzAiIHkyPSIyMTgiIHN0cm9rZT0iIzk0YTNiOCIgc3Ryb2tlLXdpZHRoPSIxLjgiLz4KICA8bGluZSB4MT0iNjIwIiB5MT0iMjE4IiB4Mj0iNjIwIiB5Mj0iMjUwIiBzdHJva2U9IiM5NGEzYjgiIHN0cm9rZS13aWR0aD0iMS44Ii8+CiAgPGxpbmUgeDE9IjgzMCIgeTE9IjIxOCIgeDI9IjgzMCIgeTI9IjI1MCIgc3Ryb2tlPSIjOTRhM2I4IiBzdHJva2Utd2lkdGg9IjEuOCIvPgogIDx0ZXh0IHg9IjYwNiIgeT0iMjQwIiB0ZXh0LWFuY2hvcj0iZW5kIiBmb250LXNpemU9IjExLjUiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiM2NDc0OGIiPuaYrzwvdGV4dD4KICA8dGV4dCB4PSI4NDQiIHk9IjI0MCIgdGV4dC1hbmNob3I9InN0YXJ0IiBmb250LXNpemU9IjExLjUiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiM2NDc0OGIiPuWQpjwvdGV4dD4KCiAgPCEtLSBsZWF2ZXMgLS0+CiAgPHJlY3QgeD0iODUiIHk9IjI1MCIgd2lkdGg9IjE5MCIgaGVpZ2h0PSI4MCIgcng9IjEwIiBmaWxsPSIjZmZmZmZmIiBzdHJva2U9IiMyNTYzZWIiIHN0cm9rZS13aWR0aD0iMiIvPgogIDx0ZXh0IHg9IjE4MCIgeT0iMjc4IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LXNpemU9IjE1IiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjMWUzYThhIj5idW1wYWxvPC90ZXh0PgogIDx0ZXh0IHg9IjE4MCIgeT0iMjk5IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LXNpemU9IjEwLjUiIGZpbGw9IiM0NzU1NjkiPuW8guaehCBidW1wIMK3IOaegeW/qzwvdGV4dD4KICA8dGV4dCB4PSIxODAiIHk9IjMxOCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1zaXplPSIxMC41IiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjYjkxYzFjIj7imqAg6buY6K6k5LiN6LeRIERyb3A8L3RleHQ+CgogIDxyZWN0IHg9IjI4MCIgeT0iMjUwIiB3aWR0aD0iMTkwIiBoZWlnaHQ9IjgwIiByeD0iMTAiIGZpbGw9IiNmZmZmZmYiIHN0cm9rZT0iIzI1NjNlYiIgc3Ryb2tlLXdpZHRoPSIyIi8+CiAgPHRleHQgeD0iMzc1IiB5PSIyNzgiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtc2l6ZT0iMTUiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiMxZTNhOGEiPnR5cGVkLWFyZW5hPC90ZXh0PgogIDx0ZXh0IHg9IjM3NSIgeT0iMjk5IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LXNpemU9IjEwLjUiIGZpbGw9IiM0NzU1NjkiPuWNleexu+WeiyDCtyDov5Tlm54gJmFtcDttdXQgVDwvdGV4dD4KICA8dGV4dCB4PSIzNzUiIHk9IjMxOCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1zaXplPSIxMC41IiBmaWxsPSIjNDc1NTY5Ij7kvJrot5HmnpDmnoQ8L3RleHQ+CgogIDxyZWN0IHg9IjUyMCIgeT0iMjUwIiB3aWR0aD0iMjAwIiBoZWlnaHQ9IjgwIiByeD0iMTAiIGZpbGw9IiNmZmZmZmYiIHN0cm9rZT0iIzE2YTM0YSIgc3Ryb2tlLXdpZHRoPSIyIi8+CiAgPHRleHQgeD0iNjIwIiB5PSIyNzgiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtc2l6ZT0iMTQiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiMxNjY1MzQiPnNsb3RtYXAgLyB0aHVuZGVyZG9tZTwvdGV4dD4KICA8dGV4dCB4PSI2MjAiIHk9IjI5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1zaXplPSIxMC41IiBmaWxsPSIjNDc1NTY5Ij7ku6PpmYUgS2V5L0luZGV4IMK3IOmYsuaCrOWegjwvdGV4dD4KICA8dGV4dCB4PSI2MjAiIHk9IjMxOCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1zaXplPSIxMC41IiBmaWxsPSIjOTRhM2I4Ij4oZ2VuLWFyZW5hIOW3suWBnOe7tCk8L3RleHQ+CgogIDxyZWN0IHg9Ijc0MCIgeT0iMjUwIiB3aWR0aD0iMTkwIiBoZWlnaHQ9IjgwIiByeD0iMTAiIGZpbGw9IiNmZmZmZmYiIHN0cm9rZT0iIzE2YTM0YSIgc3Ryb2tlLXdpZHRoPSIyIi8+CiAgPHRleHQgeD0iODM1IiB5PSIyNzgiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtc2l6ZT0iMTUiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiMxNjY1MzQiPnNsYWI8L3RleHQ+CiAgPHRleHQgeD0iODM1IiB5PSIyOTkiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtc2l6ZT0iMTAuNSIgZmlsbD0iIzQ3NTU2OSI+dXNpemUga2V5IMK3IOeugOWNlTwvdGV4dD4KICA8dGV4dCB4PSI4MzUiIHk9IjMxOCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1zaXplPSIxMC41IiBmaWxsPSIjNDc1NTY5Ij50b2tpbyDlkIzmrL4gwrcg5peg5Luj6ZmFPC90ZXh0PgoKICA8IS0tIG5vdGUgYm94IC0tPgogIDxyZWN0IHg9IjQwIiB5PSIzNTYiIHdpZHRoPSI5MDAiIGhlaWdodD0iMTE2IiByeD0iMTIiIGZpbGw9IiNmZmZiZWIiIHN0cm9rZT0iI2ZjZDM0ZCIgc3Ryb2tlLXdpZHRoPSIxLjUiLz4KICA8dGV4dCB4PSI1OCIgeT0iMzgwIiBmb250LXNpemU9IjEzLjUiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiM5MjQwMGUiPueJueS+i+S4juaJqeWxlTwvdGV4dD4KICA8dGV4dCB4PSI1OCIgeT0iNDA0IiBmb250LXNpemU9IjEyIiBmaWxsPSIjNzgzNTBmIj7igKIg5Y+q5bu65Zu+IC8g5Y+q6L+95Yqg44CB6KaBIENvcHkg5Y+l5p+EIOKGkiA8dHNwYW4gZm9udC13ZWlnaHQ9IjcwMCI+aWQtYXJlbmEgwrcgbGEtYXJlbmE8L3RzcGFuPjwvdGV4dD4KICA8dGV4dCB4PSI1OCIgeT0iNDI2IiBmb250LXNpemU9IjEyIiBmaWxsPSIjNzgzNTBmIj7igKIgYXBwZW5kLW9ubHkg5LiU6KaB5Lqk44CM55yfICZhbXA7VOOAjeW8leeUqCDihpIgPHRzcGFuIGZvbnQtd2VpZ2h0PSI3MDAiPmVsc2HvvIhGcm96ZW5WZWPvvIk8L3RzcGFuPuOAgO+9nOOAgOW4puS9nOeUqOWfny/mo4Dmn6Xngrnlm57mlLbnmoQgYnVtcCDihpIgPHRzcGFuIGZvbnQtd2VpZ2h0PSI3MDAiPmJ1bXAtc2NvcGU8L3RzcGFuPjwvdGV4dD4KICA8dGV4dCB4PSI1OCIgeT0iNDQ4IiBmb250LXNpemU9IjEyIiBmaWxsPSIjNzgzNTBmIj7igKIg5b2TICNbZ2xvYmFsX2FsbG9jYXRvcl0gLyBBbGxvY2F0b3Ig4oaSIDx0c3BhbiBmb250LXdlaWdodD0iNzAwIj5ibGluay1hbGxvY++8iOWFqOWxgO+8icK3IGJ1bXBhbG/vvIjlrrnlmajnuqfvvIk8L3RzcGFuPuOAgO+9nOOAgOWtl+espuS4sumpu+eVmSDihpIgPHRzcGFuIGZvbnQtd2VpZ2h0PSI3MDAiPmxhc3NvIMK3IHN0cmluZy1pbnRlcm5lcjwvdHNwYW4+PC90ZXh0PgogIDx0ZXh0IHg9IjU4IiB5PSI0NjgiIGZvbnQtc2l6ZT0iMTEuNSIgZmlsbD0iIzkyNDAwZSI+4oCiIOWPguiAgyBydXN0YyDlhoXpg6jlgZrms5XvvJo8dHNwYW4gZm9udC13ZWlnaHQ9IjcwMCI+cnVzdGNfYXJlbmE8L3RzcGFuPiA9IFR5cGVkQXJlbmHvvIjot5EgRHJvcO+8iSsgRHJvcGxlc3NBcmVuYe+8iOW8guaehOOAgeS4jei3kSBEcm9w77yJPC90ZXh0Pgo8L3N2Zz4K"/>
</p>
<p align="center"><sub><b>图 7</b> · Arena 选型决策树</sub></p>

**文字版**

1. **需要单独删除 / 回收个别对象吗？**
   - **否（只在最后整体释放）** → 同一 arena 放异构类型吗？
     - 是 → **bumpalo**（异构 bump、极快；⚠ 默认不跑 Drop）
     - 否 → **typed-arena**（单类型、返回 `&mut T`、会跑析构）
     - （只建图/只追加且想要 `Copy` 句柄 → **id-arena / la-arena**）
   - **是（要删除 + 复用槽位）** → 需要防止 stale 句柄误用（代际安全）吗？
     - 是 → **slotmap / thunderdome**（代际 `Key`/`Index`，防悬垂；`generational-arena` 已停维）
     - 否（简单够用）→ **slab**（`usize` key，tokio 同款，无代际）
2. **特例与扩展**
   - append-only 且要交「真 `&T`」引用 → **elsa（FrozenVec）**
   - 把 arena 当 `#[global_allocator]` / `Allocator` → **blink-alloc（全局）· bumpalo（容器级）· bump-scope**
   - 带作用域/检查点回收的 bump → **bump-scope**
   - 字符串驻留 → **lasso（可并发）/ string-interner**

---

## 11. 常见陷阱与最佳实践

- **bumpalo 默认不跑 Drop**：分配持有资源的类型（`File`、`Socket`、`MutexGuard`）会**泄漏资源**。要析构就用 `bumpalo::boxed::Box` 或 `bumpalo::collections`；或改用 typed-arena / bump-scope（它们会析构）。
- **Bump arena 的内存在丢弃/`reset` 前不回收**：长生命周期的 arena 会持续膨胀。请把 arena 绑定到明确的「阶段」（请求/帧/pass），阶段结束 `reset()` 或丢弃；或用 bump-scope 的作用域分段回收。
- **无代际句柄（slab / id-arena / la-arena）的 stale 风险**：`remove` 后旧 `usize`/`Id` 可能指向被复用的新对象，造成逻辑层面的「use-after-free」。句柄若会在删除后继续被持有，改用 **slotmap / thunderdome** 的代际句柄。
- **生命周期「传染」**：typed-arena / bumpalo 返回的 `&'arena T` 会把 `'arena` 带进你的所有结构体，难以存进比 arena 活得久的地方。要消除这种传染，用**句柄型**（`Copy` 句柄不带生命周期）。
- **generational-arena 已停维**：新代码别再选它，迁移到 slotmap / thunderdome。
- **HopSlotMap 已废弃**：slotmap 1.1 起 `HopSlotMap` 不再维护、2.0 将移除，改用 `SlotMap` 或 `DenseSlotMap`。
- **别拿 arena 装「生命周期各异」的对象**：arena 假设批量同生命周期；若对象寿命彼此独立、不可预测，arena 只会让内存一直涨——那种场景该用普通 `Box`/`Rc` 或带删除的句柄型。
- **访问成本**：句柄型每次取值都有一次间接寻址 + 边界检查；热路径上可缓存解引用结果。

---

## 12. 进阶：标准库与 rustc 的 arena

- **标准库没有内置 arena**。stable 的 `std`/`alloc` 只给全局分配器 + 标准集合（`Vec`/`Box`/`HashMap`），**不含任何公开的 arena/bump 类型**；最接近「批量分配」的手段就是 `Vec`。要 arena 必须用第三方 crate。
- **`allocator_api`（每容器自定义分配器，如 `Vec<T, A>` / `Box<T, A>` / `*_in` 构造器）截至 2026 仍是 nightly unstable**（tracking issue **#32838**）；稳定 polyfill 用 **`allocator-api2`**。其稳定化 PR（#156882）核实时处于 open + FCP、因 soundness 疑虑未合并——**这是最易变的一项，定稿前请刷新 GitHub 状态**。
- **别混淆两套机制**：程序级的 `GlobalAlloc` trait + `#[global_allocator]` 属性（换 jemalloc 等）**早在 Rust 1.28（2018）就已 stable**；不稳定的是 per-container 的 `Allocator`/`allocator_api`。`blink-alloc`/`bumpalo` 能对接前者/后者的程度各异（见 §5）。
- **rustc 自带 `rustc_arena`**（编译器内部 crate，非公开标准库）：`TypedArena<T>`（单类型、**会跑 Drop**）+ `DroplessArena`（混存**任意不实现 Drop** 的类型、**从不析构**、甚至允许引用环）。rustc 用 `declare_arena!` 宏把二者聚合：需析构的走各自 `TypedArena<T>`，其余走共享 `DroplessArena`。这套「Drop 与 Dropless 分流」的设计，正是理解各第三方 arena「跑不跑析构」取舍的最佳范本。

---

## 13. 结论与建议

- **海量短命对象、要极致分配速度、可接受整块释放** → **bumpalo**（异构）或 **typed-arena**（单类型、要析构）。这是「经典 arena」的主场。
- **建图/树/IR、只追加不删、想要 `Copy` 句柄规避生命周期** → **id-arena**（或 rust-analyzer 同款 **la-arena**）。
- **对象会动态增删、且句柄会被长期持有、要防悬垂** → **slotmap**（生态最广、gamedev 首选）或 **thunderdome**（更紧凑）。**别再用 generational-arena（已停维）**。
- **简单的「可复用槽位表」、删除后不会再拿旧 key** → **slab**（tokio 同款，轻量）。
- **要在持有引用的同时继续追加、需要稳定 `&T`** → **elsa（FrozenVec）**。
- **要把 arena 接入分配器体系 / 全局分配器** → **blink-alloc**、**bump-scope**（或 `bumpalo` + `allocator-api2`）。
- **字符串/标识符去重** → **lasso / string-interner**。
- **一句话**：*不删除就选 Bump 型（要不要析构决定 typed-arena/bumpalo）；要删除就选句柄型（要不要防悬垂决定 slotmap-thunderdome/slab）。*

---

## 14. 参考资料

**核心 crate**

- typed-arena：<https://docs.rs/typed-arena> · <https://github.com/thomcc/rust-typed-arena>
- bumpalo：<https://docs.rs/bumpalo> · <https://github.com/fitzgen/bumpalo>
- blink-alloc：<https://docs.rs/blink-alloc> · <https://github.com/zakarumych/blink-alloc>
- bump-scope：<https://docs.rs/bump-scope> · <https://github.com/bluurryy/bump-scope>
- id-arena：<https://docs.rs/id-arena> · <https://github.com/fitzgen/id-arena>
- generational-arena：<https://github.com/fitzgen/generational-arena> · 停维公告 <https://rustsec.org/advisories/RUSTSEC-2024-0014.html>
- slotmap：<https://docs.rs/slotmap> · <https://github.com/orlp/slotmap>
- slab：<https://docs.rs/slab> · <https://github.com/tokio-rs/slab>
- thunderdome：<https://docs.rs/thunderdome> · <https://github.com/LPGhatguy/thunderdome>
- la-arena：<https://docs.rs/la-arena> · <https://github.com/rust-lang/rust-analyzer/tree/master/lib/la-arena>
- elsa：<https://github.com/Manishearth/elsa>
- lasso：<https://docs.rs/lasso> ／ string-interner：<https://docs.rs/string-interner>

**概念与标准库**

- Niko Matsakis《Modeling graphs in Rust using vector indices》：<https://smallcultfollowing.com/babysteps/blog/2015/04/06/modeling-graphs-in-rust-using-vector-indices/>
- 《Arenas in Rust》(llogiq)：<https://llogiq.github.io/2019/04/06/arena.html>
- LogRocket《A guide to using arenas in Rust》：<https://blog.logrocket.com/guide-using-arenas-rust/>
- `allocator_api` tracking issue #32838：<https://github.com/rust-lang/rust/issues/32838>
- `#[global_allocator]` 稳定（Rust 1.28）：<https://blog.rust-lang.org/2018/08/02/Rust-1.28/>
- rustc 内存与 `rustc_arena`：<https://rustc-dev-guide.rust-lang.org/memory.html> · <https://github.com/rust-lang/rust/blob/master/compiler/rustc_arena/src/lib.rs>

<p align="center"><sub>本报告图形均为内嵌 base64 SVG，单文件自包含。版本号/许可证核实于 2026-09（以 crates.io 为准）；<code>allocator_api</code> 稳定化等易变项请以一手来源复核。</sub></p>
