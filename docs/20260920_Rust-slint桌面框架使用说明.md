# Rust Slint 桌面框架详细使用说明

> **定位**：Slint 是**声明式 `.slint` DSL** 驱动的原生 UI 框架——UI 用一门专门的标记语言写（类 QML），`build.rs` 在**编译期把它生成 Rust 代码**，逻辑用 Rust 写，**设计与逻辑物理分离**。创始团队出自 Qt/QML，目标就是「现代 Qt」。
> **杀手锏**：多渲染器（Skia / FemtoVG / 软件），**唯一能 `no_std` 下沉到 MCU（单片机）** 的 Rust GUI；Rust/C++/JS/Python 四语言绑定；live-preview 即改即见。
> **版本基线（2026-09）**：Slint **1.17.x**。1.x 有明确的语义化版本纪律，比多数 0.x 框架稳。
> **要单独看的一条**：**许可三选一**（GPLv3 / 免版税 / 商业）——桌面/移动/Web 走免版税免费，**只有「闭源 + 嵌入式发货」才收费**（第 12 节）。
> **一句话取舍**：给「有设计师协作、有嵌入式野心、想要类 Qt 工作流」的团队；短板是要学一门 DSL、许可有决策成本、社区规模小于另外四家。
> **图**：8 张内嵌 base64 SVG。所有易变 API 处均标注「以 docs.rs 对应版本为准」。

> 姊妹篇：iced（Elm·自绘）、egui（立即模式·自绘）、Dioxus（组件/信号·WebView）三份使用说明 + `docs/20260920_Rust桌面GUI框架横评.md`（五框架横评）。

---

## 目录

1. [一、Slint 是什么：声明式 DSL，编译期生成](#一slint-是什么声明式-dsl编译期生成)
2. [二、安装与第一个程序](#二安装与第一个程序)
3. [三、.slint 语言：组件 · 属性 · 布局](#三slint-语言组件--属性--布局)
4. [四、属性与数据绑定：in/out/in-out · 双向绑定](#四属性与数据绑定inoutin-out--双向绑定)
5. [五、回调与 Rust 集成：DSL 声明 ↔ Rust 处理](#五回调与-rust-集成dsl-声明--rust-处理)
6. [六、内置控件与标准布局](#六内置控件与标准布局)
7. [七、全局单例与逻辑组织](#七全局单例与逻辑组织)
8. [八、模型与列表：VecModel · ListView](#八模型与列表vecmodel--listview)
9. [九、主题与样式：Palette · 明暗](#九主题与样式palette--明暗)
10. [十、多渲染器与嵌入式：no_std 下沉 MCU](#十多渲染器与嵌入式nostd-下沉-mcu)
11. [十一、live-preview 与工具链](#十一live-preview-与工具链)
12. [十二、许可证三选一：GPL / 免版税 / 商业](#十二许可证三选一gpl--免版税--商业)
13. [十三、完整实例：待办事项 Todo](#十三完整实例待办事项-todo)
14. [十四、常见坑速查](#十四常见坑速查)
15. [十五、与 CMX 工作区的呼应](#十五与-cmx-工作区的呼应)
16. [十六、版本与参考资源](#十六版本与参考资源)

---

## 一、Slint 是什么：声明式 DSL，编译期生成

<p align="center"><img alt="图1：声明式 DSL 编译期生成" style="max-width:100%;height:auto;border:1px solid #e8eef5;border-radius:10px" src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA5NDAgNDIwIiB3aWR0aD0iOTQwIiBoZWlnaHQ9IjQyMCIgcm9sZT0iaW1nIj48ZGVmcz48bWFya2VyIGlkPSJhIiB2aWV3Qm94PSIwIDAgMTAgMTAiIHJlZlg9IjguNSIgcmVmWT0iNSIgbWFya2VyV2lkdGg9IjciIG1hcmtlckhlaWdodD0iNyIgb3JpZW50PSJhdXRvLXN0YXJ0LXJldmVyc2UiPjxwYXRoIGQ9Ik0gMCAwIEwgMTAgNSBMIDAgMTAgeiIgZmlsbD0iIzY0NzQ4YiIvPjwvbWFya2VyPjwvZGVmcz48cmVjdCB3aWR0aD0iOTQwIiBoZWlnaHQ9IjQyMCIgZmlsbD0iI2ZiZmRmZiIvPjxnPjxyZWN0IHg9IjcwIiB5PSI2NiIgd2lkdGg9IjMyMCIgaGVpZ2h0PSIxMTYiIHJ4PSI4IiBmaWxsPSIjZjBmZGZhIiBzdHJva2U9IiMwZDk0ODgiIHN0cm9rZS13aWR0aD0iMS43Ii8+PHJlY3QgeD0iNzAiIHk9IjY2IiB3aWR0aD0iMzIwIiBoZWlnaHQ9IjIyIiByeD0iOCIgZmlsbD0iIzBkOTQ4OCIvPjxyZWN0IHg9IjcwIiB5PSI4MCIgd2lkdGg9IjMyMCIgaGVpZ2h0PSI4IiBmaWxsPSIjMGQ5NDg4Ii8+PHRleHQgeD0iODAiIHk9IjgyIiBmb250LWZhbWlseT0idWktbW9ub3NwYWNlLFNGTW9uby1SZWd1bGFyLE1lbmxvLG1vbm9zcGFjZSIgZm9udC1zaXplPSIxMS41IiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjZmZmIj5hcHAuc2xpbnTvvIjlo7DmmI7lvI8gVUnvvIk8L3RleHQ+PHRleHQgeD0iODAiIHk9IjEwMiIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMCIgZmlsbD0iIzFlMjkzYiI+ZXhwb3J0IGNvbXBvbmVudCDigKYgaW5oZXJpdHMgV2luZG93PC90ZXh0Pjx0ZXh0IHg9IjgwIiB5PSIxMTYiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTAiIGZpbGw9IiMxZTI5M2IiPnByb3BlcnR5IOWxnuaApyArICZsdDs9Jmd0OyDnu5Hlrpo8L3RleHQ+PHRleHQgeD0iODAiIHk9IjEzMCIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMCIgZmlsbD0iIzFlMjkzYiI+5biD5bGAICsgY2FsbGJhY2sg5Zue6LCD5aOw5piOPC90ZXh0Pjx0ZXh0IHg9IjgwIiB5PSIxNDQiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTAiIGZpbGw9IiMxZTI5M2IiPuKGkCDorr7orqHlmaggLyBsaXZlLXByZXZpZXcg5Y+v55u05o6l5pS5PC90ZXh0PjwvZz48Zz48cmVjdCB4PSI1NTAiIHk9IjY2IiB3aWR0aD0iMzIwIiBoZWlnaHQ9IjExNiIgcng9IjgiIGZpbGw9IiNmZmY3ZWQiIHN0cm9rZT0iI2MyNDEwYyIgc3Ryb2tlLXdpZHRoPSIxLjciLz48cmVjdCB4PSI1NTAiIHk9IjY2IiB3aWR0aD0iMzIwIiBoZWlnaHQ9IjIyIiByeD0iOCIgZmlsbD0iI2MyNDEwYyIvPjxyZWN0IHg9IjU1MCIgeT0iODAiIHdpZHRoPSIzMjAiIGhlaWdodD0iOCIgZmlsbD0iI2MyNDEwYyIvPjx0ZXh0IHg9IjU2MCIgeT0iODIiIGZvbnQtZmFtaWx5PSJ1aS1tb25vc3BhY2UsU0ZNb25vLVJlZ3VsYXIsTWVubG8sbW9ub3NwYWNlIiBmb250LXNpemU9IjExLjUiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiNmZmYiPm1haW4ucnPvvIjkuJrliqHpgLvovpHvvIk8L3RleHQ+PHRleHQgeD0iNTYwIiB5PSIxMDIiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTAiIGZpbGw9IiMxZTI5M2IiPmxldCB1aSA9IEFwcFdpbmRvdzo6bmV3KCk/OzwvdGV4dD48dGV4dCB4PSI1NjAiIHk9IjExNiIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMCIgZmlsbD0iIzFlMjkzYiI+dWkub25feHh4KC4uLikg5aSE55CG5Zue6LCDPC90ZXh0Pjx0ZXh0IHg9IjU2MCIgeT0iMTMwIiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwIiBmaWxsPSIjMWUyOTNiIj51aS5zZXRfeHh4KC4uLikg5ZaC5pWw5o2uIC8gZ2V0IOivuzwvdGV4dD48dGV4dCB4PSI1NjAiIHk9IjE0NCIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMCIgZmlsbD0iIzFlMjkzYiI+dWkucnVuKCk/PC90ZXh0PjwvZz48Zz48cGF0aCBkPSJNIDIzMCAxODIgTCAzODAgMjMyIiBmaWxsPSJub25lIiBzdHJva2U9IiMwZDk0ODgiIHN0cm9rZS13aWR0aD0iMS42IiBzdHJva2UtZGFzaGFycmF5PSI1IDMiIG1hcmtlci1lbmQ9InVybCgjYSkiLz48cmVjdCB4PSIyODkiIHk9IjE5OCIgd2lkdGg9IjMxLjc5OTk5OTk5OTk5OTk5NyIgaGVpZ2h0PSIxNiIgcng9IjQiIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iMC45NSIgc3Ryb2tlPSIjY2JkNWUxIiBzdHJva2Utd2lkdGg9IjAuNyIvPjx0ZXh0IHg9IjMwNSIgeT0iMjEwIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LWZhbWlseT0idWktbW9ub3NwYWNlLFNGTW9uby1SZWd1bGFyLE1lbmxvLG1vbm9zcGFjZSIgZm9udC1zaXplPSI5IiBmaWxsPSIjMzM0MTU1Ij7nvJbor5HmnJ88L3RleHQ+PC9nPjxnPjxwYXRoIGQ9Ik0gNzEwIDE4MiBMIDU2MCAyMzIiIGZpbGw9Im5vbmUiIHN0cm9rZT0iI2MyNDEwYyIgc3Ryb2tlLXdpZHRoPSIxLjYiIHN0cm9rZS1kYXNoYXJyYXk9IjUgMyIgbWFya2VyLWVuZD0idXJsKCNhKSIvPjxyZWN0IHg9IjU3NiIgeT0iMTk4IiB3aWR0aD0iMTE3LjYiIGhlaWdodD0iMTYiIHJ4PSI0IiBmaWxsPSIjZmZmIiBmaWxsLW9wYWNpdHk9IjAuOTUiIHN0cm9rZT0iI2NiZDVlMSIgc3Ryb2tlLXdpZHRoPSIwLjciLz48dGV4dCB4PSI2MzUiIHk9IjIxMCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1mYW1pbHk9InVpLW1vbm9zcGFjZSxTRk1vbm8tUmVndWxhcixNZW5sbyxtb25vc3BhY2UiIGZvbnQtc2l6ZT0iOSIgZmlsbD0iIzMzNDE1NSI+aW5jbHVkZV9tb2R1bGVzITwvdGV4dD48L2c+PGc+PHJlY3QgeD0iMzIwIiB5PSIyMzIiIHdpZHRoPSIzMDAiIGhlaWdodD0iNTgiIHJ4PSI4IiBmaWxsPSIjZjVmM2ZmIiBzdHJva2U9IiM3YzNhZWQiIHN0cm9rZS13aWR0aD0iMS43Ii8+PHJlY3QgeD0iMzIwIiB5PSIyMzIiIHdpZHRoPSIzMDAiIGhlaWdodD0iMjIiIHJ4PSI4IiBmaWxsPSIjN2MzYWVkIi8+PHJlY3QgeD0iMzIwIiB5PSIyNDYiIHdpZHRoPSIzMDAiIGhlaWdodD0iOCIgZmlsbD0iIzdjM2FlZCIvPjx0ZXh0IHg9IjMzMCIgeT0iMjQ4IiBmb250LWZhbWlseT0idWktbW9ub3NwYWNlLFNGTW9uby1SZWd1bGFyLE1lbmxvLG1vbm9zcGFjZSIgZm9udC1zaXplPSIxMS41IiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjZmZmIj5idWlsZC5ycyDCtyBzbGludF9idWlsZDo6Y29tcGlsZSgpPC90ZXh0Pjx0ZXh0IHg9IjMzMCIgeT0iMjY4IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwIiBmaWxsPSIjMWUyOTNiIj7mioogLnNsaW50IOeUn+aIkCBSdXN0IOS7o+egge+8iOaXoOi/kOihjOaXtuino+mHiu+8iTwvdGV4dD48L2c+PGc+PHBhdGggZD0iTSA0NzAgMjkwIEwgNDcwIDMyMCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjNjQ3NDhiIiBzdHJva2Utd2lkdGg9IjEuNiIgc3Ryb2tlLWRhc2hhcnJheT0iNSAzIiBtYXJrZXItZW5kPSJ1cmwoI2EpIi8+PC9nPjxnPjxyZWN0IHg9IjMzMCIgeT0iMzIwIiB3aWR0aD0iMjgwIiBoZWlnaHQ9IjUwIiByeD0iOCIgZmlsbD0iI2YxZjVmOSIgc3Ryb2tlPSIjNDc1NTY5IiBzdHJva2Utd2lkdGg9IjEuNyIvPjxyZWN0IHg9IjMzMCIgeT0iMzIwIiB3aWR0aD0iMjgwIiBoZWlnaHQ9IjIyIiByeD0iOCIgZmlsbD0iIzQ3NTU2OSIvPjxyZWN0IHg9IjMzMCIgeT0iMzM0IiB3aWR0aD0iMjgwIiBoZWlnaHQ9IjgiIGZpbGw9IiM0NzU1NjkiLz48dGV4dCB4PSIzNDAiIHk9IjMzNiIgZm9udC1mYW1pbHk9InVpLW1vbm9zcGFjZSxTRk1vbm8tUmVndWxhcixNZW5sbyxtb25vc3BhY2UiIGZvbnQtc2l6ZT0iMTEuNSIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iI2ZmZiI+5Y6f55Sf5LqM6L+b5Yi277yI57yW6K+R5pyf5bey5a6a5Z6L77yJPC90ZXh0PjwvZz48dGV4dCB4PSI0NzAiIHk9IjM5OCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMi41IiBmaWxsPSIjMzM0MTU1Ij7orr7orqHvvIguc2xpbnTvvInkuI7pgLvovpHvvIhSdXN077yJ54mp55CG5YiG56a777yM57G7IFFNTO+8m2J1aWxkLnJzIOe8luivkeacn+aKiiBEU0wg5Y+Y5oiQIFJ1c3TigJTigJTov5DooYzml7bml6Dop6Pph4rlvIDplIDvvIzkuJQgLnNsaW50IOWPr+iiq+WPr+inhuWMluiuvuiuoeWZqC/pooTop4jlmajnm7TmjqXnvJbovpE8L3RleHQ+PC9zdmc+"></p>

Slint 的世界观和另外四家都不同——**UI 不用宿主语言写，而用一门专门的声明式 DSL 写**：

- **`.slint` 文件**：声明式描述 UI（组件、属性、布局、绑定、回调），类似 QML。**设计师、可视化设计器、live-preview 都能直接编辑它**。
- **`build.rs`**：用 `slint-build` 在**编译期**把 `.slint` **生成 Rust 代码**（不是运行时解释）——所以没有解释开销，且类型安全。
- **Rust 侧**：写业务逻辑，通过生成的 `AppWindow::new()` / `get_*` / `set_*` / `on_*` 与 UI 交互。

> 核心价值是**设计与逻辑的物理分离**（类 Qt/QML 工作流）：UI 描述独立成文件，可被工具链可视化编辑、可被设计师改，逻辑代码不受污染。这对「有设计协作、UI 迭代频繁」的团队是实打实的好处；代价是你得**多学一门 DSL**。

> 与本系列另外三位的分野：iced/egui **自绘**、用 Rust 写 UI；Dioxus 用 Rust RSX、桌面走 WebView；**Slint 用独立 DSL、编译期生成、自绘（Skia/软件），且能下沉到 MCU**——这是它最独特的地方（第 10 节）。

## 二、安装与第一个程序

三个文件：`.slint`（UI）、`build.rs`（编译期生成）、`main.rs`（逻辑）。`Cargo.toml`：

```toml
[dependencies]
slint = "1.17"

[build-dependencies]
slint-build = "1.17"
```

`ui/app-window.slint`——声明 UI：

```slint
import { Button, VerticalBox, HorizontalBox } from "std-widgets.slint";

export component AppWindow inherits Window {
    in-out property <int> counter: 0;      // 属性（带初值），Rust 可读可写
    callback increase();                   // 回调，交给 Rust 处理
    callback decrease();

    VerticalBox {
        Text { text: "计数: \{root.counter}"; font-size: 24px; }
        HorizontalBox {
            Button { text: "-"; clicked => { root.decrease(); } }
            Button { text: "+"; clicked => { root.increase(); } }
        }
    }
}
```

`build.rs`——编译期把 `.slint` 变成 Rust：

```rust
fn main() {
    slint_build::compile("ui/app-window.slint").unwrap();
}
```

`src/main.rs`——写逻辑：

```rust
slint::include_modules!();   // 拉入 build.rs 生成的代码（AppWindow 就来自这里）

fn main() -> Result<(), slint::PlatformError> {
    let ui = AppWindow::new()?;

    // 注册回调：捕获 Weak 句柄，避免闭包与组件循环引用而泄漏
    let weak = ui.as_weak();
    ui.on_increase(move || {
        let ui = weak.upgrade().unwrap();
        ui.set_counter(ui.get_counter() + 1);   // getter + setter（属性名 - 变 _）
    });
    let weak = ui.as_weak();
    ui.on_decrease(move || {
        let ui = weak.upgrade().unwrap();
        ui.set_counter(ui.get_counter() - 1);
    });

    ui.run()
}
```

`cargo run` 即见窗口。对比另外三家：iced 四件套、egui 每帧 `update`、Dioxus 组件/信号——**Slint 是「DSL 声明界面 + Rust 处理回调」**，UI 和逻辑在不同文件、不同语言。中文默认能显示（自绘但内置字体处理，复杂场景仍可配字体）。

## 三、.slint 语言：组件 · 属性 · 布局

<p align="center"><img alt="图2：.slint 语言解剖" style="max-width:100%;height:auto;border:1px solid #e8eef5;border-radius:10px" src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA5NDAgNDQwIiB3aWR0aD0iOTQwIiBoZWlnaHQ9IjQ0MCIgcm9sZT0iaW1nIj48ZGVmcz48bWFya2VyIGlkPSJhIiB2aWV3Qm94PSIwIDAgMTAgMTAiIHJlZlg9IjguNSIgcmVmWT0iNSIgbWFya2VyV2lkdGg9IjciIG1hcmtlckhlaWdodD0iNyIgb3JpZW50PSJhdXRvLXN0YXJ0LXJldmVyc2UiPjxwYXRoIGQ9Ik0gMCAwIEwgMTAgNSBMIDAgMTAgeiIgZmlsbD0iIzY0NzQ4YiIvPjwvbWFya2VyPjwvZGVmcz48cmVjdCB3aWR0aD0iOTQwIiBoZWlnaHQ9IjQ0MCIgZmlsbD0iI2ZiZmRmZiIvPjxyZWN0IHg9IjQ1IiB5PSI1NSIgd2lkdGg9IjU0NSIgaGVpZ2h0PSIzNTAiIHJ4PSIxMCIgZmlsbD0iIzFlMjkzYiIvPjxjaXJjbGUgY3g9IjY2IiBjeT0iNzYiIHI9IjQuNSIgZmlsbD0iI2ZmNWY1NyIvPjxjaXJjbGUgY3g9IjgwIiBjeT0iNzYiIHI9IjQuNSIgZmlsbD0iI2ZlYmMyZSIvPjxjaXJjbGUgY3g9Ijk0IiBjeT0iNzYiIHI9IjQuNSIgZmlsbD0iIzI4Yzg0MCIvPjx0ZXh0IHg9IjYyIiB5PSIxMDAiIGZvbnQtZmFtaWx5PSJ1aS1tb25vc3BhY2UsU0ZNb25vLVJlZ3VsYXIsTWVubG8sbW9ub3NwYWNlIiBmb250LXNpemU9IjEyIiBmaWxsPSIjZDZkZWViIj5pbXBvcnQgeyBCdXR0b24sIFZlcnRpY2FsQm94IH08L3RleHQ+PHRleHQgeD0iNzYiIHk9IjEyMCIgZm9udC1mYW1pbHk9InVpLW1vbm9zcGFjZSxTRk1vbm8tUmVndWxhcixNZW5sbyxtb25vc3BhY2UiIGZvbnQtc2l6ZT0iMTIiIGZpbGw9IiNkNmRlZWIiPmZyb20gJnF1b3Q7c3RkLXdpZGdldHMuc2xpbnQmcXVvdDs7PC90ZXh0Pjx0ZXh0IHg9IjYyIiB5PSIxNDAiIGZvbnQtZmFtaWx5PSJ1aS1tb25vc3BhY2UsU0ZNb25vLVJlZ3VsYXIsTWVubG8sbW9ub3NwYWNlIiBmb250LXNpemU9IjEyIiBmaWxsPSIjZDZkZWViIj48L3RleHQ+PHRleHQgeD0iNjIiIHk9IjE2MCIgZm9udC1mYW1pbHk9InVpLW1vbm9zcGFjZSxTRk1vbm8tUmVndWxhcixNZW5sbyxtb25vc3BhY2UiIGZvbnQtc2l6ZT0iMTIiIGZpbGw9IiNkNmRlZWIiPmV4cG9ydCBjb21wb25lbnQgQXBwV2luZG93PC90ZXh0Pjx0ZXh0IHg9IjExOCIgeT0iMTgwIiBmb250LWZhbWlseT0idWktbW9ub3NwYWNlLFNGTW9uby1SZWd1bGFyLE1lbmxvLG1vbm9zcGFjZSIgZm9udC1zaXplPSIxMiIgZmlsbD0iI2Q2ZGVlYiI+aW5oZXJpdHMgV2luZG93IHs8L3RleHQ+PHRleHQgeD0iOTAiIHk9IjIwMCIgZm9udC1mYW1pbHk9InVpLW1vbm9zcGFjZSxTRk1vbm8tUmVndWxhcixNZW5sbyxtb25vc3BhY2UiIGZvbnQtc2l6ZT0iMTIiIGZpbGw9IiNkNmRlZWIiPmluLW91dCBwcm9wZXJ0eSAmbHQ7aW50Jmd0OyBjb3VudDogMDs8L3RleHQ+PHRleHQgeD0iOTAiIHk9IjIyMCIgZm9udC1mYW1pbHk9InVpLW1vbm9zcGFjZSxTRk1vbm8tUmVndWxhcixNZW5sbyxtb25vc3BhY2UiIGZvbnQtc2l6ZT0iMTIiIGZpbGw9IiNkNmRlZWIiPmNhbGxiYWNrIGluY3JlYXNlKCk7PC90ZXh0Pjx0ZXh0IHg9IjYyIiB5PSIyNDAiIGZvbnQtZmFtaWx5PSJ1aS1tb25vc3BhY2UsU0ZNb25vLVJlZ3VsYXIsTWVubG8sbW9ub3NwYWNlIiBmb250LXNpemU9IjEyIiBmaWxsPSIjZDZkZWViIj48L3RleHQ+PHRleHQgeD0iOTAiIHk9IjI2MCIgZm9udC1mYW1pbHk9InVpLW1vbm9zcGFjZSxTRk1vbm8tUmVndWxhcixNZW5sbyxtb25vc3BhY2UiIGZvbnQtc2l6ZT0iMTIiIGZpbGw9IiNkNmRlZWIiPlZlcnRpY2FsQm94IHs8L3RleHQ+PHRleHQgeD0iMTE4IiB5PSIyODAiIGZvbnQtZmFtaWx5PSJ1aS1tb25vc3BhY2UsU0ZNb25vLVJlZ3VsYXIsTWVubG8sbW9ub3NwYWNlIiBmb250LXNpemU9IjEyIiBmaWxsPSIjZDZkZWViIj5UZXh0IHsgdGV4dDogJnF1b3Q76K6h5pWwOiBce3Jvb3QuY291bnR9JnF1b3Q7OyB9PC90ZXh0Pjx0ZXh0IHg9IjExOCIgeT0iMzAwIiBmb250LWZhbWlseT0idWktbW9ub3NwYWNlLFNGTW9uby1SZWd1bGFyLE1lbmxvLG1vbm9zcGFjZSIgZm9udC1zaXplPSIxMiIgZmlsbD0iI2Q2ZGVlYiI+QnV0dG9uIHs8L3RleHQ+PHRleHQgeD0iMTQ2IiB5PSIzMjAiIGZvbnQtZmFtaWx5PSJ1aS1tb25vc3BhY2UsU0ZNb25vLVJlZ3VsYXIsTWVubG8sbW9ub3NwYWNlIiBmb250LXNpemU9IjEyIiBmaWxsPSIjZDZkZWViIj50ZXh0OiAmcXVvdDvliqDkuIAmcXVvdDs7PC90ZXh0Pjx0ZXh0IHg9IjE0NiIgeT0iMzQwIiBmb250LWZhbWlseT0idWktbW9ub3NwYWNlLFNGTW9uby1SZWd1bGFyLE1lbmxvLG1vbm9zcGFjZSIgZm9udC1zaXplPSIxMiIgZmlsbD0iI2Q2ZGVlYiI+Y2xpY2tlZCA9Jmd0OyB7IHJvb3QuaW5jcmVhc2UoKTsgfTwvdGV4dD48dGV4dCB4PSIxMTgiIHk9IjM2MCIgZm9udC1mYW1pbHk9InVpLW1vbm9zcGFjZSxTRk1vbm8tUmVndWxhcixNZW5sbyxtb25vc3BhY2UiIGZvbnQtc2l6ZT0iMTIiIGZpbGw9IiNkNmRlZWIiPn08L3RleHQ+PHRleHQgeD0iOTAiIHk9IjM4MCIgZm9udC1mYW1pbHk9InVpLW1vbm9zcGFjZSxTRk1vbm8tUmVndWxhcixNZW5sbyxtb25vc3BhY2UiIGZvbnQtc2l6ZT0iMTIiIGZpbGw9IiNkNmRlZWIiPn08L3RleHQ+PHRleHQgeD0iNjIiIHk9IjQwMCIgZm9udC1mYW1pbHk9InVpLW1vbm9zcGFjZSxTRk1vbm8tUmVndWxhcixNZW5sbyxtb25vc3BhY2UiIGZvbnQtc2l6ZT0iMTIiIGZpbGw9IiNkNmRlZWIiPn08L3RleHQ+PGc+PHBhdGggZD0iTSA1OTAgMTA4IEwgNjM2IDEwOCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjMGQ5NDg4IiBzdHJva2Utd2lkdGg9IjEuNiIgc3Ryb2tlLWRhc2hhcnJheT0iNSAzIiBtYXJrZXItZW5kPSJ1cmwoI2EpIi8+PC9nPjxyZWN0IHg9IjY0MCIgeT0iOTUiIHdpZHRoPSIyNzAiIGhlaWdodD0iMjYiIHJ4PSI2IiBmaWxsPSIjZmZmIiBzdHJva2U9IiMwZDk0ODgiIHN0cm9rZS13aWR0aD0iMS40Ii8+PHRleHQgeD0iNjUyIiB5PSIxMTIiIHRleHQtYW5jaG9yPSJzdGFydCIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMSIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iIzFlMjkzYiI+5a+85YWl5qCH5YeG5o6n5Lu2PC90ZXh0PjxnPjxwYXRoIGQ9Ik0gNTkwIDE0OCBMIDYzNiAxNTIiIGZpbGw9Im5vbmUiIHN0cm9rZT0iIzdjM2FlZCIgc3Ryb2tlLXdpZHRoPSIxLjYiIHN0cm9rZS1kYXNoYXJyYXk9IjUgMyIgbWFya2VyLWVuZD0idXJsKCNhKSIvPjwvZz48cmVjdCB4PSI2NDAiIHk9IjEzOSIgd2lkdGg9IjI3MCIgaGVpZ2h0PSIyNiIgcng9IjYiIGZpbGw9IiNmZmYiIHN0cm9rZT0iIzdjM2FlZCIgc3Ryb2tlLXdpZHRoPSIxLjQiLz48dGV4dCB4PSI2NTIiIHk9IjE1NiIgdGV4dC1hbmNob3I9InN0YXJ0IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjExIiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjMWUyOTNiIj7moLnnu4Tku7YgaW5oZXJpdHMgV2luZG93PC90ZXh0PjxnPjxwYXRoIGQ9Ik0gNTkwIDE4OCBMIDYzNiAxOTYiIGZpbGw9Im5vbmUiIHN0cm9rZT0iIzAyODRjNyIgc3Ryb2tlLXdpZHRoPSIxLjYiIHN0cm9rZS1kYXNoYXJyYXk9IjUgMyIgbWFya2VyLWVuZD0idXJsKCNhKSIvPjwvZz48cmVjdCB4PSI2NDAiIHk9IjE4MyIgd2lkdGg9IjI3MCIgaGVpZ2h0PSIyNiIgcng9IjYiIGZpbGw9IiNmZmYiIHN0cm9rZT0iIzAyODRjNyIgc3Ryb2tlLXdpZHRoPSIxLjQiLz48dGV4dCB4PSI2NTIiIHk9IjIwMCIgdGV4dC1hbmNob3I9InN0YXJ0IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjExIiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjMWUyOTNiIj7lsZ7mgKcgcHJvcGVydHkgKyDliJ3lgLw8L3RleHQ+PGc+PHBhdGggZD0iTSA1OTAgMjA4IEwgNjM2IDI0MCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjYjQ1MzA5IiBzdHJva2Utd2lkdGg9IjEuNiIgc3Ryb2tlLWRhc2hhcnJheT0iNSAzIiBtYXJrZXItZW5kPSJ1cmwoI2EpIi8+PC9nPjxyZWN0IHg9IjY0MCIgeT0iMjI3IiB3aWR0aD0iMjcwIiBoZWlnaHQ9IjI2IiByeD0iNiIgZmlsbD0iI2ZmZiIgc3Ryb2tlPSIjYjQ1MzA5IiBzdHJva2Utd2lkdGg9IjEuNCIvPjx0ZXh0IHg9IjY1MiIgeT0iMjQ0IiB0ZXh0LWFuY2hvcj0ic3RhcnQiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTEiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiMxZTI5M2IiPuWbnuiwgyBjYWxsYmFjayDlo7DmmI48L3RleHQ+PGc+PHBhdGggZD0iTSA1OTAgMjg4IEwgNjM2IDI5MiIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjYzI0MTBjIiBzdHJva2Utd2lkdGg9IjEuNiIgc3Ryb2tlLWRhc2hhcnJheT0iNSAzIiBtYXJrZXItZW5kPSJ1cmwoI2EpIi8+PC9nPjxyZWN0IHg9IjY0MCIgeT0iMjc5IiB3aWR0aD0iMjcwIiBoZWlnaHQ9IjI2IiByeD0iNiIgZmlsbD0iI2ZmZiIgc3Ryb2tlPSIjYzI0MTBjIiBzdHJva2Utd2lkdGg9IjEuNCIvPjx0ZXh0IHg9IjY1MiIgeT0iMjk2IiB0ZXh0LWFuY2hvcj0ic3RhcnQiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTEiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiMxZTI5M2IiPuW4g+WxgOWuueWZqCBWZXJ0aWNhbEJveDwvdGV4dD48Zz48cGF0aCBkPSJNIDU5MCAzMDggTCA2MzYgMzM2IiBmaWxsPSJub25lIiBzdHJva2U9IiMxNTgwM2QiIHN0cm9rZS13aWR0aD0iMS42IiBzdHJva2UtZGFzaGFycmF5PSI1IDMiIG1hcmtlci1lbmQ9InVybCgjYSkiLz48L2c+PHJlY3QgeD0iNjQwIiB5PSIzMjMiIHdpZHRoPSIyNzAiIGhlaWdodD0iMjYiIHJ4PSI2IiBmaWxsPSIjZmZmIiBzdHJva2U9IiMxNTgwM2QiIHN0cm9rZS13aWR0aD0iMS40Ii8+PHRleHQgeD0iNjUyIiB5PSIzNDAiIHRleHQtYW5jaG9yPSJzdGFydCIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMSIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iIzFlMjkzYiI+5o+S5YC8IFx7cm9vdC5jb3VudH08L3RleHQ+PGc+PHBhdGggZD0iTSA1OTAgMzY4IEwgNjM2IDM4MCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjZGMyNjI2IiBzdHJva2Utd2lkdGg9IjEuNiIgc3Ryb2tlLWRhc2hhcnJheT0iNSAzIiBtYXJrZXItZW5kPSJ1cmwoI2EpIi8+PC9nPjxyZWN0IHg9IjY0MCIgeT0iMzY3IiB3aWR0aD0iMjcwIiBoZWlnaHQ9IjI2IiByeD0iNiIgZmlsbD0iI2ZmZiIgc3Ryb2tlPSIjZGMyNjI2IiBzdHJva2Utd2lkdGg9IjEuNCIvPjx0ZXh0IHg9IjY1MiIgeT0iMzg0IiB0ZXh0LWFuY2hvcj0ic3RhcnQiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTEiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiMxZTI5M2IiPuS6i+S7tue7keWumiBjbGlja2VkID0mZ3Q7PC90ZXh0Pjx0ZXh0IHg9IjQ3MCIgeT0iNDI0IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEyLjUiIGZpbGw9IiMzMzQxNTUiPi5zbGludCDmmK/lo7DmmI7lvI8gRFNM77yaaW1wb3J0IOaOp+S7tuOAgWNvbXBvbmVudCDlrprkuYnjgIFwcm9wZXJ0eSDlsZ7mgKfjgIFjYWxsYmFjayDlm57osIPjgIHluIPlsYDlrrnlmajjgIFce30g5o+S5YC844CBPSZndDsg5LqL5Lu257uR5a6a4oCU4oCU57yW6K+R5pyf55Sf5oiQIFJ1c3TvvIzpnZ7lrZfnrKbkuLI8L3RleHQ+PC9zdmc+"></p>

`.slint` 是一门小而专的声明式语言。要素：

```slint
// 导入标准控件
import { Button, LineEdit, VerticalBox } from "std-widgets.slint";

// 自定义可复用组件
component LabeledInput inherits HorizontalBox {
    in property <string> label;
    in-out property <string> value;
    Text { text: root.label; }
    LineEdit { text <=> root.value; }        // <=> 双向绑定
}

// 结构体（会生成对应的 Rust struct）
struct Person { name: string, age: int }

// 导出的主组件
export component MainWindow inherits Window {
    preferred-width: 400px;
    preferred-height: 300px;

    in-out property <string> username;

    VerticalBox {
        LabeledInput { label: "用户名"; value <=> root.username; }
        Text { text: "你好, \{root.username}"; }   // \{} 插值
    }
}
```

| 语法 | 说明 |
|---|---|
| `component X inherits Y { }` | 定义组件（继承 Window / 布局 / 其它组件） |
| `property <类型> 名: 初值;` | 属性；类型有 `int/float/string/bool/color/length/[T]` 等 |
| `struct S { … }` | 结构体，生成对应 Rust `struct` |
| `callback foo(参数);` | 回调声明 |
| `属性: 表达式;` | 绑定（表达式变，属性自动更新——响应式） |
| `a <=> b` | 双向绑定 |
| `"…\{expr}…"` | 字符串插值 |
| `//` `/* */` | 注释 |

> `-` 和 `_` 在 `.slint` 里等价（`request-increase` == `request_increase`），但生成到 Rust 时统一变 `_`（`on_request_increase`）。属性绑定是**响应式**的：`Text { text: "\{a + b}" }` 里 `a` 或 `b` 变，文本自动重算。

## 四、属性与数据绑定：in/out/in-out · 双向绑定

属性有**方向**，决定 Rust 侧能读还是能写：

```slint
export component W inherits Window {
    in property <string> title;      // 输入：Rust set，组件内只读（有 set_title）
    out property <bool> is-valid;     // 输出：组件内算，Rust 读（有 get_is_valid）
    in-out property <int> count;      // 双向：Rust 可读可写（get + set）
    property <int> internal: 0;       // 无方向 = 私有，仅组件内部用（Rust 看不到）

    // 绑定：is-valid 由 title 推导，title 一变自动重算（响应式）
    is-valid: root.title != "";
}
```

| 方向 | Rust 侧 | 用途 |
|---|---|---|
| `in` | 只 `set_x()` | 外部喂数据给 UI（如标题、列表） |
| `out` | 只 `get_x()` | UI 算出结果给外部（如校验结果） |
| `in-out` | `get` + `set` | 双向（如输入框内容） |
| 无方向 | 不可见 | 组件内部私有状态 |

**双向绑定 `<=>`** 是减少样板的利器——控件和属性自动同步，不用手写回调：

```slint
in-out property <string> name;
LineEdit { text <=> root.name; }     // 输入框改 → name 改；name 改 → 输入框改
```

> 绑定是 Slint「声明式」的精髓：你声明「谁等于谁的函数」，值一变，依赖它的全部自动更新——和 Dioxus 信号异曲同工，但写在 DSL 里、编译期定型。

## 五、回调与 Rust 集成：DSL 声明 ↔ Rust 处理

<p align="center"><img alt="图3：DSL ↔ Rust 桥" style="max-width:100%;height:auto;border:1px solid #e8eef5;border-radius:10px" src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA5NDAgNDEwIiB3aWR0aD0iOTQwIiBoZWlnaHQ9IjQxMCIgcm9sZT0iaW1nIj48ZGVmcz48bWFya2VyIGlkPSJhIiB2aWV3Qm94PSIwIDAgMTAgMTAiIHJlZlg9IjguNSIgcmVmWT0iNSIgbWFya2VyV2lkdGg9IjciIG1hcmtlckhlaWdodD0iNyIgb3JpZW50PSJhdXRvLXN0YXJ0LXJldmVyc2UiPjxwYXRoIGQ9Ik0gMCAwIEwgMTAgNSBMIDAgMTAgeiIgZmlsbD0iIzY0NzQ4YiIvPjwvbWFya2VyPjwvZGVmcz48cmVjdCB3aWR0aD0iOTQwIiBoZWlnaHQ9IjQxMCIgZmlsbD0iI2ZiZmRmZiIvPjxnPjxyZWN0IHg9IjYwIiB5PSI2NiIgd2lkdGg9IjMzMCIgaGVpZ2h0PSIxNTAiIHJ4PSI4IiBmaWxsPSIjZjBmZGZhIiBzdHJva2U9IiMwZDk0ODgiIHN0cm9rZS13aWR0aD0iMS43Ii8+PHJlY3QgeD0iNjAiIHk9IjY2IiB3aWR0aD0iMzMwIiBoZWlnaHQ9IjIyIiByeD0iOCIgZmlsbD0iIzBkOTQ4OCIvPjxyZWN0IHg9IjYwIiB5PSI4MCIgd2lkdGg9IjMzMCIgaGVpZ2h0PSI4IiBmaWxsPSIjMGQ5NDg4Ii8+PHRleHQgeD0iNzAiIHk9IjgyIiBmb250LWZhbWlseT0idWktbW9ub3NwYWNlLFNGTW9uby1SZWd1bGFyLE1lbmxvLG1vbm9zcGFjZSIgZm9udC1zaXplPSIxMS41IiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjZmZmIj5hcHAuc2xpbnQg5aOw5piOPC90ZXh0Pjx0ZXh0IHg9IjcwIiB5PSIxMDIiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTAiIGZpbGw9IiMxZTI5M2IiPmluLW91dCBwcm9wZXJ0eSAmbHQ7aW50Jmd0OyBjb3VudDs8L3RleHQ+PHRleHQgeD0iNzAiIHk9IjExNiIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMCIgZmlsbD0iIzFlMjkzYiI+Y2FsbGJhY2sgaW5jcmVhc2UoKTs8L3RleHQ+PHRleHQgeD0iNzAiIHk9IjEzMCIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMCIgZmlsbD0iIzFlMjkzYiI+PC90ZXh0Pjx0ZXh0IHg9IjcwIiB5PSIxNDQiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTAiIGZpbGw9IiMxZTI5M2IiPkJ1dHRvbiB7PC90ZXh0Pjx0ZXh0IHg9IjcwIiB5PSIxNTgiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTAiIGZpbGw9IiMxZTI5M2IiPiAgY2xpY2tlZCA9Jmd0OyB7IHJvb3QuaW5jcmVhc2UoKTsgfTwvdGV4dD48dGV4dCB4PSI3MCIgeT0iMTcyIiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwIiBmaWxsPSIjMWUyOTNiIj59PC90ZXh0PjwvZz48Zz48cmVjdCB4PSI1NjAiIHk9IjY2IiB3aWR0aD0iMzMwIiBoZWlnaHQ9IjE1MCIgcng9IjgiIGZpbGw9IiNmZmY3ZWQiIHN0cm9rZT0iI2MyNDEwYyIgc3Ryb2tlLXdpZHRoPSIxLjciLz48cmVjdCB4PSI1NjAiIHk9IjY2IiB3aWR0aD0iMzMwIiBoZWlnaHQ9IjIyIiByeD0iOCIgZmlsbD0iI2MyNDEwYyIvPjxyZWN0IHg9IjU2MCIgeT0iODAiIHdpZHRoPSIzMzAiIGhlaWdodD0iOCIgZmlsbD0iI2MyNDEwYyIvPjx0ZXh0IHg9IjU3MCIgeT0iODIiIGZvbnQtZmFtaWx5PSJ1aS1tb25vc3BhY2UsU0ZNb25vLVJlZ3VsYXIsTWVubG8sbW9ub3NwYWNlIiBmb250LXNpemU9IjExLjUiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiNmZmYiPm1haW4ucnMg6amx5YqoPC90ZXh0Pjx0ZXh0IHg9IjU3MCIgeT0iMTAyIiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwIiBmaWxsPSIjMWUyOTNiIj51aS5nZXRfY291bnQoKSAvIHVpLnNldF9jb3VudCh2KTwvdGV4dD48dGV4dCB4PSI1NzAiIHk9IjExNiIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMCIgZmlsbD0iIzFlMjkzYiI+ICDihpAg5bGe5oCn55qEIGdldHRlciAvIHNldHRlcjwvdGV4dD48dGV4dCB4PSI1NzAiIHk9IjEzMCIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMCIgZmlsbD0iIzFlMjkzYiI+PC90ZXh0Pjx0ZXh0IHg9IjU3MCIgeT0iMTQ0IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwIiBmaWxsPSIjMWUyOTNiIj51aS5vbl9pbmNyZWFzZShtb3ZlIHx8IHsg4oCmIH0pPC90ZXh0Pjx0ZXh0IHg9IjU3MCIgeT0iMTU4IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwIiBmaWxsPSIjMWUyOTNiIj4gIOKGkCDlm57osIPlpITnkIblmag8L3RleHQ+PHRleHQgeD0iNTcwIiB5PSIxNzIiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTAiIGZpbGw9IiMxZTI5M2IiPmxldCB3ZWFrID0gdWkuYXNfd2VhaygpOzwvdGV4dD48L2c+PGc+PHBhdGggZD0iTSAzOTAgMTA4IEwgNTYwIDEwOCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjMDI4NGM3IiBzdHJva2Utd2lkdGg9IjEuNiIgc3Ryb2tlLWRhc2hhcnJheT0iNSAzIiBtYXJrZXItZW5kPSJ1cmwoI2EpIi8+PHJlY3QgeD0iNDM2IiB5PSI5OSIgd2lkdGg9Ijc4LjAiIGhlaWdodD0iMTYiIHJ4PSI0IiBmaWxsPSIjZmZmIiBmaWxsLW9wYWNpdHk9IjAuOTUiIHN0cm9rZT0iI2NiZDVlMSIgc3Ryb2tlLXdpZHRoPSIwLjciLz48dGV4dCB4PSI0NzUiIHk9IjExMSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1mYW1pbHk9InVpLW1vbm9zcGFjZSxTRk1vbm8tUmVndWxhcixNZW5sbyxtb25vc3BhY2UiIGZvbnQtc2l6ZT0iOSIgZmlsbD0iIzMzNDE1NSI+5bGe5oCn4oaUZ2V0L3NldDwvdGV4dD48L2c+PGc+PHBhdGggZD0iTSAzOTAgMTY4IEwgNTYwIDE2OCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjYjQ1MzA5IiBzdHJva2Utd2lkdGg9IjEuNiIgc3Ryb2tlLWRhc2hhcnJheT0iNSAzIiBtYXJrZXItZW5kPSJ1cmwoI2EpIi8+PHJlY3QgeD0iNDM5IiB5PSIxNTkiIHdpZHRoPSI3MS40IiBoZWlnaHQ9IjE2IiByeD0iNCIgZmlsbD0iI2ZmZiIgZmlsbC1vcGFjaXR5PSIwLjk1IiBzdHJva2U9IiNjYmQ1ZTEiIHN0cm9rZS13aWR0aD0iMC43Ii8+PHRleHQgeD0iNDc1IiB5PSIxNzEiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtZmFtaWx5PSJ1aS1tb25vc3BhY2UsU0ZNb25vLVJlZ3VsYXIsTWVubG8sbW9ub3NwYWNlIiBmb250LXNpemU9IjkiIGZpbGw9IiMzMzQxNTUiPuWbnuiwg+KGkm9uXyDlpITnkIY8L3RleHQ+PC9nPjxnPjxyZWN0IHg9IjIzMCIgeT0iMjU4IiB3aWR0aD0iNDgwIiBoZWlnaHQ9Ijg0IiByeD0iOCIgZmlsbD0iI2ZlZjJmMiIgc3Ryb2tlPSIjZGMyNjI2IiBzdHJva2Utd2lkdGg9IjEuNyIvPjxyZWN0IHg9IjIzMCIgeT0iMjU4IiB3aWR0aD0iNDgwIiBoZWlnaHQ9IjIyIiByeD0iOCIgZmlsbD0iI2RjMjYyNiIvPjxyZWN0IHg9IjIzMCIgeT0iMjcyIiB3aWR0aD0iNDgwIiBoZWlnaHQ9IjgiIGZpbGw9IiNkYzI2MjYiLz48dGV4dCB4PSIyNDAiIHk9IjI3NCIgZm9udC1mYW1pbHk9InVpLW1vbm9zcGFjZSxTRk1vbm8tUmVndWxhcixNZW5sbyxtb25vc3BhY2UiIGZvbnQtc2l6ZT0iMTEuNSIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iI2ZmZiI+4pqgIOWbnuiwg+mXreWMheaNleiOtyBXZWFr77yM5Yir5o2V6I635by65byV55SoPC90ZXh0Pjx0ZXh0IHg9IjI0MCIgeT0iMjk0IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwIiBmaWxsPSIjMWUyOTNiIj51aS5vbl94KG1vdmUgfHwgeyBsZXQgdWkgPSB3ZWFrLnVwZ3JhZGUoKS51bndyYXAoKTsg4oCmIH0pPC90ZXh0Pjx0ZXh0IHg9IjI0MCIgeT0iMzA4IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwIiBmaWxsPSIjMWUyOTNiIj7mjZXojrflvLrlvJXnlKgg4oaSIOe7hOS7tiDihpQg6Zet5YyFIOW+queOr+W8leeUqCDihpIg5YaF5a2Y5rOE5ryP77yIU2xpbnQg5aS05Y+35Z2R77yJPC90ZXh0PjwvZz48dGV4dCB4PSI0NzAiIHk9IjM4NCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMi41IiBmaWxsPSIjMzM0MTU1Ij5EU0wg5LiOIFJ1c3Qg55qE5qGl77ya5bGe5oCnIOKGlCBnZXQvc2V0IOWPjOWQkeOAgWNhbGxiYWNrIOKGlCBvbl8g5aSE55CG5Zmo77yI5ZG95ZCNIC0g5Y+YIF/vvInjgILpk4HlvovvvJrlm57osIPph4znlKggYXNfd2VhaygpIOeahOW8seWPpeafhO+8jHVwZ3JhZGUg5ZCO5YaN55SoPC90ZXh0Pjwvc3ZnPg=="></p>

回调（callback）是 UI 通知 Rust「发生了事」的通道：`.slint` **声明**，Rust 用 `on_*` **处理**。

```slint
export component W inherits Window {
    callback increase();                 // 无参
    callback name-edited(string);        // 带参
    callback validate(string) -> bool;   // 带返回值

    LineEdit { edited(text) => { root.name-edited(text); } }
    Button { clicked => { root.increase(); } }
}
```

```rust
let weak = ui.as_weak();
ui.on_increase(move || {
    let ui = weak.upgrade().unwrap();    // 弱句柄升级
    ui.set_counter(ui.get_counter() + 1);
});

ui.on_name_edited(move |text| {          // 参数按声明顺序传入（- 变 _）
    println!("输入变成: {text}");
});

ui.on_validate(|text| !text.is_empty()); // 带返回值的回调
```

**Rust 集成三件套 + 一条铁律**：

- `slint::include_modules!()`（配 `build.rs`）或内联 `slint::slint!{ … }` 宏引入生成代码。
- 属性：`get_x()` / `set_x(v)`；回调：`on_x(closure)`；命名里的 `-` 到 Rust 全变 `_`。
- **铁律：回调闭包里用 `ui.as_weak()` 的弱句柄，`upgrade()` 后再用**。捕获强引用 `ui` 会造成「组件 ↔ 闭包」循环引用 → **内存泄漏**（这是 Slint 的头号坑）。
- **线程**：事件循环必须在主线程；组件也要在主线程创建。跨线程更新见第 8 节。

## 六、内置控件与标准布局

`std-widgets.slint` 提供一套跨平台控件，配合布局容器用：

```slint
import {
    Button, LineEdit, TextEdit, CheckBox, Switch, Slider, SpinBox,
    ComboBox, ListView, StandardListView, ScrollView, ProgressIndicator,
    VerticalBox, HorizontalBox, GridBox, GroupBox, TabWidget
} from "std-widgets.slint";

export component W inherits Window {
    VerticalBox {
        LineEdit { placeholder-text: "搜索…"; }
        HorizontalBox {
            CheckBox { text: "记住我"; }
            Switch { checked: true; }
        }
        Slider { minimum: 0; maximum: 100; value: 50; }
        ComboBox { model: ["苹果", "梨", "橙"]; }
        Button { text: "提交"; primary: true; }
    }
}
```

| 控件 | 布局 |
|---|---|
| `Button`（`primary`） / `LineEdit` / `TextEdit` | `VerticalBox` 竖排 |
| `CheckBox` / `Switch` / `Slider` / `SpinBox` | `HorizontalBox` 横排 |
| `ComboBox` / `ListView` / `StandardListView` | `GridBox` 网格 |
| `ScrollView` / `TabWidget` / `GroupBox` | `Spacer` 弹性占位 |
| `ProgressIndicator` | 手写 `Rectangle` + `x/y/width/height` 绝对定位 |

> 布局容器（`*Box`）自动排布并响应窗口缩放；也能用 `Rectangle` + 几何属性做像素级绝对定位。控件外观随选定的 style（Fluent/Material/…）变（第 9 节）。

## 七、全局单例与逻辑组织

跨组件共享状态用 **全局单例 `global`**，避免层层传属性：

```slint
// 定义一个全局单例
export global AppState {
    in-out property <string> user;
    in-out property <bool> dark-mode;
    callback logout();
}

export component W inherits Window {
    Text { text: "当前用户: \{AppState.user}"; }        // 任意组件直接引用
    Button { text: "退出"; clicked => { AppState.logout(); } }
}
```

```rust
use slint::ComponentHandle;

let ui = AppWindow::new()?;
// 通过 global::<T>() 访问全局单例
ui.global::<AppState>().set_user("张三".into());
ui.global::<AppState>().on_logout(move || { /* … */ });
```

> `global` 适合放「整个应用的状态与命令」（当前用户、主题、路由）。组织大型 UI 时：拆多个 `.slint` 文件（`import` 复用组件）、用 `global` 管全局态、用 `struct` + 模型管数据——DSL 侧就有一套完整的模块化手段。

## 八、模型与列表：VecModel · ListView

<p align="center"><img alt="图4：模型与列表" style="max-width:100%;height:auto;border:1px solid #e8eef5;border-radius:10px" src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA5NDAgNDAwIiB3aWR0aD0iOTQwIiBoZWlnaHQ9IjQwMCIgcm9sZT0iaW1nIj48ZGVmcz48bWFya2VyIGlkPSJhIiB2aWV3Qm94PSIwIDAgMTAgMTAiIHJlZlg9IjguNSIgcmVmWT0iNSIgbWFya2VyV2lkdGg9IjciIG1hcmtlckhlaWdodD0iNyIgb3JpZW50PSJhdXRvLXN0YXJ0LXJldmVyc2UiPjxwYXRoIGQ9Ik0gMCAwIEwgMTAgNSBMIDAgMTAgeiIgZmlsbD0iIzY0NzQ4YiIvPjwvbWFya2VyPjwvZGVmcz48cmVjdCB3aWR0aD0iOTQwIiBoZWlnaHQ9IjQwMCIgZmlsbD0iI2ZiZmRmZiIvPjxnPjxyZWN0IHg9IjYwIiB5PSI2NiIgd2lkdGg9IjM1MCIgaGVpZ2h0PSIxNDAiIHJ4PSI4IiBmaWxsPSIjZmZmN2VkIiBzdHJva2U9IiNjMjQxMGMiIHN0cm9rZS13aWR0aD0iMS43Ii8+PHJlY3QgeD0iNjAiIHk9IjY2IiB3aWR0aD0iMzUwIiBoZWlnaHQ9IjIyIiByeD0iOCIgZmlsbD0iI2MyNDEwYyIvPjxyZWN0IHg9IjYwIiB5PSI4MCIgd2lkdGg9IjM1MCIgaGVpZ2h0PSI4IiBmaWxsPSIjYzI0MTBjIi8+PHRleHQgeD0iNzAiIHk9IjgyIiBmb250LWZhbWlseT0idWktbW9ub3NwYWNlLFNGTW9uby1SZWd1bGFyLE1lbmxvLG1vbm9zcGFjZSIgZm9udC1zaXplPSIxMS41IiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjZmZmIj5SdXN0IOS+p++8mlZlY01vZGVsPC90ZXh0Pjx0ZXh0IHg9IjcwIiB5PSIxMDIiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTAiIGZpbGw9IiMxZTI5M2IiPmxldCBtID0gUmM6Om5ldyhWZWNNb2RlbDo6ZGVmYXVsdCgpKTs8L3RleHQ+PHRleHQgeD0iNzAiIHk9IjExNiIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMCIgZmlsbD0iIzFlMjkzYiI+dWkuc2V0X3RvZG9zKG0uY2xvbmUoKS5pbnRvKCkpOzwvdGV4dD48dGV4dCB4PSI3MCIgeT0iMTMwIiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwIiBmaWxsPSIjMWUyOTNiIj5tLnB1c2goaXRlbSkgIMK3ICBtLnNldF92ZWModik8L3RleHQ+PHRleHQgeD0iNzAiIHk9IjE0NCIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMCIgZmlsbD0iIzFlMjkzYiI+bS5yb3dfZGF0YShpKSAvIG0uc2V0X3Jvd19kYXRhKGksIHgpPC90ZXh0Pjx0ZXh0IHg9IjcwIiB5PSIxNTgiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTAiIGZpbGw9IiMxZTI5M2IiPm0ucmVtb3ZlKGkpPC90ZXh0PjwvZz48Zz48cmVjdCB4PSI1NDAiIHk9IjY2IiB3aWR0aD0iMzUwIiBoZWlnaHQ9IjE0MCIgcng9IjgiIGZpbGw9IiNmMGZkZmEiIHN0cm9rZT0iIzBkOTQ4OCIgc3Ryb2tlLXdpZHRoPSIxLjciLz48cmVjdCB4PSI1NDAiIHk9IjY2IiB3aWR0aD0iMzUwIiBoZWlnaHQ9IjIyIiByeD0iOCIgZmlsbD0iIzBkOTQ4OCIvPjxyZWN0IHg9IjU0MCIgeT0iODAiIHdpZHRoPSIzNTAiIGhlaWdodD0iOCIgZmlsbD0iIzBkOTQ4OCIvPjx0ZXh0IHg9IjU1MCIgeT0iODIiIGZvbnQtZmFtaWx5PSJ1aS1tb25vc3BhY2UsU0ZNb25vLVJlZ3VsYXIsTWVubG8sbW9ub3NwYWNlIiBmb250LXNpemU9IjExLjUiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiNmZmYiPi5zbGludCDkvqfvvJpmb3Ig4oCmIGluIG1vZGVsPC90ZXh0Pjx0ZXh0IHg9IjU1MCIgeT0iMTAyIiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwIiBmaWxsPSIjMWUyOTNiIj5pbiBwcm9wZXJ0eSAmbHQ7W1RvZG9JdGVtXSZndDsgdG9kb3M7PC90ZXh0Pjx0ZXh0IHg9IjU1MCIgeT0iMTE2IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwIiBmaWxsPSIjMWUyOTNiIj5MaXN0VmlldyB7PC90ZXh0Pjx0ZXh0IHg9IjU1MCIgeT0iMTMwIiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwIiBmaWxsPSIjMWUyOTNiIj4gIGZvciBpdCBpbiByb290LnRvZG9zOjwvdGV4dD48dGV4dCB4PSI1NTAiIHk9IjE0NCIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMCIgZmlsbD0iIzFlMjkzYiI+ICAgIEhvcml6b250YWxCb3ggeyBDaGVja0JveCDigKYgfTwvdGV4dD48dGV4dCB4PSI1NTAiIHk9IjE1OCIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMCIgZmlsbD0iIzFlMjkzYiI+fTwvdGV4dD48L2c+PGc+PHBhdGggZD0iTSA0MTAgMTIwIEwgNTQwIDEyMCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjMGQ5NDg4IiBzdHJva2Utd2lkdGg9IjEuNiIgc3Ryb2tlLWRhc2hhcnJheT0iNSAzIiBtYXJrZXItZW5kPSJ1cmwoI2EpIi8+PHJlY3QgeD0iNDA2IiB5PSIxMTEiIHdpZHRoPSIxMzcuMzk5OTk5OTk5OTk5OTgiIGhlaWdodD0iMTYiIHJ4PSI0IiBmaWxsPSIjZmZmIiBmaWxsLW9wYWNpdHk9IjAuOTUiIHN0cm9rZT0iI2NiZDVlMSIgc3Ryb2tlLXdpZHRoPSIwLjciLz48dGV4dCB4PSI0NzUiIHk9IjEyMyIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1mYW1pbHk9InVpLW1vbm9zcGFjZSxTRk1vbm8tUmVndWxhcixNZW5sbyxtb25vc3BhY2UiIGZvbnQtc2l6ZT0iOSIgZmlsbD0iIzMzNDE1NSI+c2V0X3RvZG9zKG0uaW50bygpKTwvdGV4dD48L2c+PGc+PHJlY3QgeD0iMjMwIiB5PSIyNDYiIHdpZHRoPSI0ODAiIGhlaWdodD0iODQiIHJ4PSI4IiBmaWxsPSIjZmVmMmYyIiBzdHJva2U9IiNkYzI2MjYiIHN0cm9rZS13aWR0aD0iMS43Ii8+PHJlY3QgeD0iMjMwIiB5PSIyNDYiIHdpZHRoPSI0ODAiIGhlaWdodD0iMjIiIHJ4PSI4IiBmaWxsPSIjZGMyNjI2Ii8+PHJlY3QgeD0iMjMwIiB5PSIyNjAiIHdpZHRoPSI0ODAiIGhlaWdodD0iOCIgZmlsbD0iI2RjMjYyNiIvPjx0ZXh0IHg9IjI0MCIgeT0iMjYyIiBmb250LWZhbWlseT0idWktbW9ub3NwYWNlLFNGTW9uby1SZWd1bGFyLE1lbmxvLG1vbm9zcGFjZSIgZm9udC1zaXplPSIxMS41IiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjZmZmIj7imqAgTW9kZWxSYyDkuI3mmK8gU2VuZDwvdGV4dD48dGV4dCB4PSIyNDAiIHk9IjI4MiIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMCIgZmlsbD0iIzFlMjkzYiI+6Leo57q/56iL5pS55qih5Z6L77ya5Y+q5oqKIFdlYWsg6YCB6L+b57q/56iL77yM5Zue5Li757q/56iL5pS54oCU4oCUPC90ZXh0Pjx0ZXh0IHg9IjI0MCIgeT0iMjk2IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwIiBmaWxsPSIjMWUyOTNiIj51aS5hc193ZWFrKCkg4oaSIHVwZ3JhZGVfaW5fZXZlbnRfbG9vcChtb3ZlIHx1aXwgeyDigKbmlLnmqKHlnovigKYgfSk8L3RleHQ+PC9nPjx0ZXh0IHg9IjQ3MCIgeT0iMzc2IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEyLjUiIGZpbGw9IiMzMzQxNTUiPuWKqOaAgeWIl+ihqCA9IOaooeWei+mpseWKqO+8mlJ1c3Qg5bu6IFZlY01vZGVs44CBc2V0IOe7meWxnuaAp++8jC5zbGludCDnlKggZm9y4oCmaW4g6YGN5Y6G5riy5p+T77yb5qih5Z6L6Z2eIFNlbmTvvIzot6jnur/nqIvlv4Xpobvlm57kuovku7blvqrnjq/ph4zmlLk8L3RleHQ+PC9zdmc+"></p>

动态列表用**模型（Model）**驱动：Rust 建 `VecModel`、set 给属性，`.slint` 用 `for … in` 遍历。

```slint
struct TodoItem { id: int, text: string, done: bool }

export component W inherits Window {
    in property <[TodoItem]> todos;        // 列表属性
    callback toggle(int);

    ListView {
        for item in root.todos: HorizontalBox {
            CheckBox { checked: item.done; toggled => { root.toggle(item.id); } }
            Text { text: item.text; }
        }
    }
}
```

```rust
use slint::{VecModel, ModelRc};
use std::rc::Rc;

let ui = W::new()?;
let todos = Rc::new(VecModel::<TodoItem>::default());
ui.set_todos(todos.clone().into());        // Rc<VecModel> -> ModelRc（.into()）

todos.push(TodoItem { id: 1, text: "买菜".into(), done: false });  // 增
todos.set_row_data(0, updated_item);                              // 改
todos.remove(0);                                                  // 删
// 这些改动会自动通知 UI 刷新（Model 通知机制）
```

| 操作 | API |
|---|---|
| 建模型 | `Rc::new(VecModel::default())` |
| 绑到属性 | `ui.set_x(model.clone().into())` |
| 增 / 删 | `model.push(x)` / `model.remove(i)` |
| 读 / 改某行 | `model.row_data(i)` / `model.set_row_data(i, x)` |
| 整体替换 | `model.set_vec(vec)` |

> **跨线程铁律**：`ModelRc` **不是 `Send`**，只能在主线程用。后台线程算完数据，**只把 `ui.as_weak()` 送进线程**，回到 `weak.upgrade_in_event_loop(move |ui| { …改模型… })` 里改——直接把 `Rc<VecModel>` move 进线程会编译报错。

## 九、主题与样式：Palette · 明暗

<p align="center"><img alt="图5：主题与 Palette" style="max-width:100%;height:auto;border:1px solid #e8eef5;border-radius:10px" src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA5NDAgNDMwIiB3aWR0aD0iOTQwIiBoZWlnaHQ9IjQzMCIgcm9sZT0iaW1nIj48ZGVmcz48bWFya2VyIGlkPSJhIiB2aWV3Qm94PSIwIDAgMTAgMTAiIHJlZlg9IjguNSIgcmVmWT0iNSIgbWFya2VyV2lkdGg9IjciIG1hcmtlckhlaWdodD0iNyIgb3JpZW50PSJhdXRvLXN0YXJ0LXJldmVyc2UiPjxwYXRoIGQ9Ik0gMCAwIEwgMTAgNSBMIDAgMTAgeiIgZmlsbD0iIzY0NzQ4YiIvPjwvbWFya2VyPjwvZGVmcz48cmVjdCB3aWR0aD0iOTQwIiBoZWlnaHQ9IjQzMCIgZmlsbD0iI2ZiZmRmZiIvPjxnPjxyZWN0IHg9IjUwIiB5PSI1MCIgd2lkdGg9IjIwNSIgaGVpZ2h0PSIyMDUiIHJ4PSI5IiBmaWxsPSIjZmZmZmZmIiBzdHJva2U9IiNjYmQ1ZTEiIHN0cm9rZS13aWR0aD0iMS40Ii8+PHJlY3QgeD0iNTAiIHk9IjUwIiB3aWR0aD0iMjA1IiBoZWlnaHQ9IjI2IiByeD0iOSIgZmlsbD0iIzdjM2FlZCIvPjxyZWN0IHg9IjUwIiB5PSI2NyIgd2lkdGg9IjIwNSIgaGVpZ2h0PSI5IiBmaWxsPSIjN2MzYWVkIi8+PGNpcmNsZSBjeD0iNjUiIGN5PSI2MyIgcj0iNC41IiBmaWxsPSIjZmY1ZjU3Ii8+PGNpcmNsZSBjeD0iODAiIGN5PSI2MyIgcj0iNC41IiBmaWxsPSIjZmViYzJlIi8+PGNpcmNsZSBjeD0iOTUiIGN5PSI2MyIgcj0iNC41IiBmaWxsPSIjMjhjODQwIi8+PHRleHQgeD0iMTUyLjUiIHk9IjY3IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LWZhbWlseT0idWktbW9ub3NwYWNlLFNGTW9uby1SZWd1bGFyLE1lbmxvLG1vbm9zcGFjZSIgZm9udC1zaXplPSIxMSIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iI2ZmZiI+TGlnaHQ8L3RleHQ+PC9nPjx0ZXh0IHg9IjcwIiB5PSI5MiIgdGV4dC1hbmNob3I9InN0YXJ0IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjE0IiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjMWUxZTFlIj7moIfpopg8L3RleHQ+PGc+PHJlY3QgeD0iNzAiIHk9IjEwNCIgd2lkdGg9Ijc2IiBoZWlnaHQ9IjI2IiByeD0iNiIgZmlsbD0iIzdjM2FlZCIvPjx0ZXh0IHg9IjEwOC4wIiB5PSIxMjAiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTEiIGZvbnQtd2VpZ2h0PSI2MDAiIGZpbGw9IiNmZmYiPuehruWumjwvdGV4dD48L2c+PGc+PHJlY3QgeD0iMTU1IiB5PSIxMDQiIHdpZHRoPSI4MiIgaGVpZ2h0PSIyNiIgcng9IjYiIGZpbGw9IiNmZmYiIHN0cm9rZT0iI2NiZDVlMSIgc3Ryb2tlLXdpZHRoPSIxLjMiLz48dGV4dCB4PSIxNjUiIHk9IjEyMSIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMSIgZmlsbD0iIzk0YTNiOCI+6L6T5YWl4oCmPC90ZXh0PjwvZz48cmVjdCB4PSI3MCIgeT0iMTQ2IiB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHJ4PSIzIiBmaWxsPSIjN2MzYWVkIi8+PHBhdGggZD0iTSA3MyAxNTQgbCAzIDMgbCA2IC03IiBzdHJva2U9IiNmZmYiIHN0cm9rZS13aWR0aD0iMiIgZmlsbD0ibm9uZSIvPjx0ZXh0IHg9Ijk0IiB5PSIxNTkiIHRleHQtYW5jaG9yPSJzdGFydCIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMSIgZm9udC13ZWlnaHQ9IjQwMCIgZmlsbD0iIzFlMWUxZSI+6YCJ6aG5PC90ZXh0Pjx0ZXh0IHg9IjcwIiB5PSIyMTAiIHRleHQtYW5jaG9yPSJzdGFydCIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMSIgZm9udC13ZWlnaHQ9IjQwMCIgZmlsbD0iIzY0NzQ4YiI+5q2j5paH5paH5pysPC90ZXh0PjxnPjxyZWN0IHg9IjI5NSIgeT0iNTAiIHdpZHRoPSIyMDUiIGhlaWdodD0iMjA1IiByeD0iOSIgZmlsbD0iIzIwMjEyNCIgc3Ryb2tlPSIjY2JkNWUxIiBzdHJva2Utd2lkdGg9IjEuNCIvPjxyZWN0IHg9IjI5NSIgeT0iNTAiIHdpZHRoPSIyMDUiIGhlaWdodD0iMjYiIHJ4PSI5IiBmaWxsPSIjM2EzMTQ1Ii8+PHJlY3QgeD0iMjk1IiB5PSI2NyIgd2lkdGg9IjIwNSIgaGVpZ2h0PSI5IiBmaWxsPSIjM2EzMTQ1Ii8+PGNpcmNsZSBjeD0iMzEwIiBjeT0iNjMiIHI9IjQuNSIgZmlsbD0iI2ZmNWY1NyIvPjxjaXJjbGUgY3g9IjMyNSIgY3k9IjYzIiByPSI0LjUiIGZpbGw9IiNmZWJjMmUiLz48Y2lyY2xlIGN4PSIzNDAiIGN5PSI2MyIgcj0iNC41IiBmaWxsPSIjMjhjODQwIi8+PHRleHQgeD0iMzk3LjUiIHk9IjY3IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LWZhbWlseT0idWktbW9ub3NwYWNlLFNGTW9uby1SZWd1bGFyLE1lbmxvLG1vbm9zcGFjZSIgZm9udC1zaXplPSIxMSIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iI2ZmZiI+RGFyazwvdGV4dD48L2c+PHRleHQgeD0iMzE1IiB5PSI5MiIgdGV4dC1hbmNob3I9InN0YXJ0IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjE0IiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjZThlOGU4Ij7moIfpopg8L3RleHQ+PGc+PHJlY3QgeD0iMzE1IiB5PSIxMDQiIHdpZHRoPSI3NiIgaGVpZ2h0PSIyNiIgcng9IjYiIGZpbGw9IiNhNzhiZmEiLz48dGV4dCB4PSIzNTMuMCIgeT0iMTIwIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjExIiBmb250LXdlaWdodD0iNjAwIiBmaWxsPSIjMWExNTIzIj7noa7lrpo8L3RleHQ+PC9nPjxnPjxyZWN0IHg9IjQwMCIgeT0iMTA0IiB3aWR0aD0iODIiIGhlaWdodD0iMjYiIHJ4PSI2IiBmaWxsPSIjMmYyZjM0IiBzdHJva2U9IiM1NTUiIHN0cm9rZS13aWR0aD0iMS4zIi8+PHRleHQgeD0iNDEwIiB5PSIxMjEiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTEiIGZpbGw9IiM5YWEwYTYiPui+k+WFpeKApjwvdGV4dD48L2c+PHJlY3QgeD0iMzE1IiB5PSIxNDYiIHdpZHRoPSIxNiIgaGVpZ2h0PSIxNiIgcng9IjMiIGZpbGw9IiNhNzhiZmEiLz48cGF0aCBkPSJNIDMxOCAxNTQgbCAzIDMgbCA2IC03IiBzdHJva2U9IiMxYTE1MjMiIHN0cm9rZS13aWR0aD0iMiIgZmlsbD0ibm9uZSIvPjx0ZXh0IHg9IjMzOSIgeT0iMTU5IiB0ZXh0LWFuY2hvcj0ic3RhcnQiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTEiIGZvbnQtd2VpZ2h0PSI0MDAiIGZpbGw9IiNlOGU4ZTgiPumAiemhuTwvdGV4dD48dGV4dCB4PSIzMTUiIHk9IjIxMCIgdGV4dC1hbmNob3I9InN0YXJ0IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjExIiBmb250LXdlaWdodD0iNDAwIiBmaWxsPSIjOWFhMGE2Ij7mraPmlofmlofmnKw8L3RleHQ+PGc+PHBhdGggZD0iTSAyNTUgMTUyIEwgMjk1IDE1MiIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjN2MzYWVkIiBzdHJva2Utd2lkdGg9IjEuNiIgc3Ryb2tlLWRhc2hhcnJheT0iNSAzIiBtYXJrZXItZW5kPSJ1cmwoI2EpIi8+PHJlY3QgeD0iMjYyIiB5PSIxNDMiIHdpZHRoPSIyNS4yIiBoZWlnaHQ9IjE2IiByeD0iNCIgZmlsbD0iI2ZmZiIgZmlsbC1vcGFjaXR5PSIwLjk1IiBzdHJva2U9IiNjYmQ1ZTEiIHN0cm9rZS13aWR0aD0iMC43Ii8+PHRleHQgeD0iMjc1IiB5PSIxNTUiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtZmFtaWx5PSJ1aS1tb25vc3BhY2UsU0ZNb25vLVJlZ3VsYXIsTWVubG8sbW9ub3NwYWNlIiBmb250LXNpemU9IjkiIGZpbGw9IiMzMzQxNTUiPuWIh+aNojwvdGV4dD48L2c+PGc+PHJlY3QgeD0iNTUwIiB5PSI1MCIgd2lkdGg9IjM1MCIgaGVpZ2h0PSIxMjAiIHJ4PSI4IiBmaWxsPSIjZjVmM2ZmIiBzdHJva2U9IiM3YzNhZWQiIHN0cm9rZS13aWR0aD0iMS43Ii8+PHJlY3QgeD0iNTUwIiB5PSI1MCIgd2lkdGg9IjM1MCIgaGVpZ2h0PSIyMiIgcng9IjgiIGZpbGw9IiM3YzNhZWQiLz48cmVjdCB4PSI1NTAiIHk9IjY0IiB3aWR0aD0iMzUwIiBoZWlnaHQ9IjgiIGZpbGw9IiM3YzNhZWQiLz48dGV4dCB4PSI1NjAiIHk9IjY2IiBmb250LWZhbWlseT0idWktbW9ub3NwYWNlLFNGTW9uby1SZWd1bGFyLE1lbmxvLG1vbm9zcGFjZSIgZm9udC1zaXplPSIxMS41IiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjZmZmIj5QYWxldHRlICsgU3R5bGXvvIjkuLvpopjnnJ/mupDvvIk8L3RleHQ+PHRleHQgeD0iNTYwIiB5PSI4NiIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMCIgZmlsbD0iIzFlMjkzYiI+5YaF572u6aOO5qC877yaRmx1ZW50IC8gTWF0ZXJpYWwgLyBDdXBlcnRpbm8gLzwvdGV4dD48dGV4dCB4PSI1NjAiIHk9IjEwMCIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMCIgZmlsbD0iIzFlMjkzYiI+ICAgICAgICBDb3NtaWMgLyBuYXRpdmXvvIjlkITluKYgLWxpZ2h0Ly1kYXJr77yJPC90ZXh0Pjx0ZXh0IHg9IjU2MCIgeT0iMTE0IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwIiBmaWxsPSIjMWUyOTNiIj5QYWxldHRlLmJhY2tncm91bmQgLyAuZm9yZWdyb3VuZCAvIC5hY2NlbnTigKY8L3RleHQ+PC9nPjx0ZXh0IHg9IjU1MCIgeT0iMTk2IiB0ZXh0LWFuY2hvcj0ic3RhcnQiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTEiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiMzMzQxNTUiPuS7jiBQYWxldHRlIOWPluiJsu+8iOekuuaEj++8iTo8L3RleHQ+PHJlY3QgeD0iNTUwIiB5PSIyMDYiIHdpZHRoPSI2NCIgaGVpZ2h0PSIzNCIgcng9IjYiIGZpbGw9IiNmZmZmZmYiIHN0cm9rZT0iI2NiZDVlMSIgc3Ryb2tlLXdpZHRoPSIxIi8+PHRleHQgeD0iNTgyIiB5PSIyNTkiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtZmFtaWx5PSJ1aS1tb25vc3BhY2UsU0ZNb25vLVJlZ3VsYXIsTWVubG8sbW9ub3NwYWNlIiBmb250LXNpemU9IjgiIGZvbnQtd2VpZ2h0PSI0MDAiIGZpbGw9IiM2NDc0OGIiPmJhY2tncm91bmQ8L3RleHQ+PHJlY3QgeD0iNjIwIiB5PSIyMDYiIHdpZHRoPSI2NCIgaGVpZ2h0PSIzNCIgcng9IjYiIGZpbGw9IiMxZTFlMWUiIHN0cm9rZT0iI2NiZDVlMSIgc3Ryb2tlLXdpZHRoPSIxIi8+PHRleHQgeD0iNjUyIiB5PSIyNTkiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtZmFtaWx5PSJ1aS1tb25vc3BhY2UsU0ZNb25vLVJlZ3VsYXIsTWVubG8sbW9ub3NwYWNlIiBmb250LXNpemU9IjgiIGZvbnQtd2VpZ2h0PSI0MDAiIGZpbGw9IiM2NDc0OGIiPmZvcmVncm91bmQ8L3RleHQ+PHJlY3QgeD0iNjkwIiB5PSIyMDYiIHdpZHRoPSI2NCIgaGVpZ2h0PSIzNCIgcng9IjYiIGZpbGw9IiM3YzNhZWQiIHN0cm9rZT0iI2NiZDVlMSIgc3Ryb2tlLXdpZHRoPSIxIi8+PHRleHQgeD0iNzIyIiB5PSIyNTkiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtZmFtaWx5PSJ1aS1tb25vc3BhY2UsU0ZNb25vLVJlZ3VsYXIsTWVubG8sbW9ub3NwYWNlIiBmb250LXNpemU9IjgiIGZvbnQtd2VpZ2h0PSI0MDAiIGZpbGw9IiM2NDc0OGIiPmFjY2VudDwvdGV4dD48cmVjdCB4PSI3NjAiIHk9IjIwNiIgd2lkdGg9IjY0IiBoZWlnaHQ9IjM0IiByeD0iNiIgZmlsbD0iI2NiZDVlMSIgc3Ryb2tlPSIjY2JkNWUxIiBzdHJva2Utd2lkdGg9IjEiLz48dGV4dCB4PSI3OTIiIHk9IjI1OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1mYW1pbHk9InVpLW1vbm9zcGFjZSxTRk1vbm8tUmVndWxhcixNZW5sbyxtb25vc3BhY2UiIGZvbnQtc2l6ZT0iOCIgZm9udC13ZWlnaHQ9IjQwMCIgZmlsbD0iIzY0NzQ4YiI+Ym9yZGVyPC90ZXh0PjxyZWN0IHg9IjgzMCIgeT0iMjA2IiB3aWR0aD0iNjQiIGhlaWdodD0iMzQiIHJ4PSI2IiBmaWxsPSIjZGMyNjI2IiBzdHJva2U9IiNjYmQ1ZTEiIHN0cm9rZS13aWR0aD0iMSIvPjx0ZXh0IHg9Ijg2MiIgeT0iMjU5IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LWZhbWlseT0idWktbW9ub3NwYWNlLFNGTW9uby1SZWd1bGFyLE1lbmxvLG1vbm9zcGFjZSIgZm9udC1zaXplPSI4IiBmb250LXdlaWdodD0iNDAwIiBmaWxsPSIjNjQ3NDhiIj5lcnJvcjwvdGV4dD48Zz48cmVjdCB4PSIxODAiIHk9IjMwMCIgd2lkdGg9IjU4MCIgaGVpZ2h0PSI3NCIgcng9IjgiIGZpbGw9IiNmZWYyZjIiIHN0cm9rZT0iI2RjMjYyNiIgc3Ryb2tlLXdpZHRoPSIxLjciLz48cmVjdCB4PSIxODAiIHk9IjMwMCIgd2lkdGg9IjU4MCIgaGVpZ2h0PSIyMiIgcng9IjgiIGZpbGw9IiNkYzI2MjYiLz48cmVjdCB4PSIxODAiIHk9IjMxNCIgd2lkdGg9IjU4MCIgaGVpZ2h0PSI4IiBmaWxsPSIjZGMyNjI2Ii8+PHRleHQgeD0iMTkwIiB5PSIzMTYiIGZvbnQtZmFtaWx5PSJ1aS1tb25vc3BhY2UsU0ZNb25vLVJlZ3VsYXIsTWVubG8sbW9ub3NwYWNlIiBmb250LXNpemU9IjExLjUiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiNmZmYiPuemgeehrOe8lueggeiJsuWAvO+8iOWvuem9kCBDTVgg56Gs57qm5p2f77yJPC90ZXh0Pjx0ZXh0IHg9IjE5MCIgeT0iMzM2IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwIiBmaWxsPSIjMWUyOTNiIj7inJQg55SoIFBhbGV0dGUuYWNjZW50LWJhY2tncm91bmQgLyBQYWxldHRlLmZvcmVncm91bmQg5rS+55SfPC90ZXh0Pjx0ZXh0IHg9IjE5MCIgeT0iMzUwIiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwIiBmaWxsPSIjMWUyOTNiIj7inJgg5Yir5YaZ5q27ICM3YzNhZWQg4oCU4oCUIOaNoiBzdHlsZSAvIOaYjuaal+WwseaOiemYn+OAgeWvueavlOW0qeWdjzwvdGV4dD48L2c+PHRleHQgeD0iNDcwIiB5PSI0MDIiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTIuNSIgZmlsbD0iIzMzNDE1NSI+6YCJ5LiA5aWXIHN0eWxl77yIRmx1ZW50L01hdGVyaWFsL+KApu+8ieWumuWfuuiwg++8jOminOiJsuS7jiBQYWxldHRlIOa0vueUn+OAgemaj+aYjuaal+WIh+aNouKAlOKAlOS4jiBDTVjjgIzlj4zkuLvpopjpgJrot6/jgIHnpoHnoaznvJbnoIHoibLlgLzjgI3lkIzmrL7opoHmsYI8L3RleHQ+PC9zdmc+"></p>

Slint 的外观由**选定的 style** + **`Palette` 全局调色板**决定：

- **Style**（编译期选）：`fluent` / `material` / `cupertino` / `cosmic` / `native`，各带 `-light` / `-dark`。控件长相随之变。
- **`Palette`**：内置全局调色板（`Palette.background` / `.foreground` / `.accent-background` …），控件和你的自定义元素都应**从它取色**。

```slint
export component W inherits Window {
    // ✔ 从 Palette 派生颜色，随 style / 明暗自动适配
    Rectangle {
        background: Palette.accent-background;
        Text { text: "标题"; color: Palette.accent-foreground; }
    }
    // ✘ 别写死：background: #7c3aed;  —— 换 style / 暗色就掉队
}
```

选 style 的两种方式：

```rust
// build.rs 里指定
slint_build::compile_with_config(
    "ui/app.slint",
    slint_build::CompilerConfiguration::new().with_style("fluent-dark".into()),
).unwrap();
// 或运行时用环境变量 SLINT_STYLE=material-light cargo run
```

> **对齐 CMX 硬约束 #4（双主题通路、禁硬编码色值）**：Slint 里同理——颜色一律从 `Palette` 派生，明暗随 style 切换。写死色值的后果就是换主题/换 style 后对比度崩坏。这条与 iced/egui 的自绘取色、Dioxus 的 CSS 变量，本质是同一个要求。

## 十、多渲染器与嵌入式：no_std 下沉 MCU

<p align="center"><img alt="图6：多渲染器与下沉 MCU" style="max-width:100%;height:auto;border:1px solid #e8eef5;border-radius:10px" src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA5NDAgNDQwIiB3aWR0aD0iOTQwIiBoZWlnaHQ9IjQ0MCIgcm9sZT0iaW1nIj48ZGVmcz48bWFya2VyIGlkPSJhIiB2aWV3Qm94PSIwIDAgMTAgMTAiIHJlZlg9IjguNSIgcmVmWT0iNSIgbWFya2VyV2lkdGg9IjciIG1hcmtlckhlaWdodD0iNyIgb3JpZW50PSJhdXRvLXN0YXJ0LXJldmVyc2UiPjxwYXRoIGQ9Ik0gMCAwIEwgMTAgNSBMIDAgMTAgeiIgZmlsbD0iIzY0NzQ4YiIvPjwvbWFya2VyPjwvZGVmcz48cmVjdCB3aWR0aD0iOTQwIiBoZWlnaHQ9IjQ0MCIgZmlsbD0iI2ZiZmRmZiIvPjxnPjxyZWN0IHg9IjM2MCIgeT0iNTAiIHdpZHRoPSIyMjAiIGhlaWdodD0iNTIiIHJ4PSI4IiBmaWxsPSIjZjVmM2ZmIiBzdHJva2U9IiM3YzNhZWQiIHN0cm9rZS13aWR0aD0iMS43Ii8+PHJlY3QgeD0iMzYwIiB5PSI1MCIgd2lkdGg9IjIyMCIgaGVpZ2h0PSIyMiIgcng9IjgiIGZpbGw9IiM3YzNhZWQiLz48cmVjdCB4PSIzNjAiIHk9IjY0IiB3aWR0aD0iMjIwIiBoZWlnaHQ9IjgiIGZpbGw9IiM3YzNhZWQiLz48dGV4dCB4PSIzNzAiIHk9IjY2IiBmb250LWZhbWlseT0idWktbW9ub3NwYWNlLFNGTW9uby1SZWd1bGFyLE1lbmxvLG1vbm9zcGFjZSIgZm9udC1zaXplPSIxMS41IiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjZmZmIj7kuIDku70gLnNsaW50IOa6kDwvdGV4dD48dGV4dCB4PSIzNzAiIHk9Ijg2IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwIiBmaWxsPSIjMWUyOTNiIj7lkIzkuIDlpZcgVUkg5aOw5piOPC90ZXh0PjwvZz48Zz48cGF0aCBkPSJNIDQ3MCAxMDIgTCA0NzAgMTI0IiBmaWxsPSJub25lIiBzdHJva2U9IiM2NDc0OGIiIHN0cm9rZS13aWR0aD0iMS42IiBzdHJva2UtZGFzaGFycmF5PSI1IDMiIG1hcmtlci1lbmQ9InVybCgjYSkiLz48L2c+PGc+PHJlY3QgeD0iNjAiIHk9IjEyNCIgd2lkdGg9IjI1MCIgaGVpZ2h0PSI2NiIgcng9IjgiIGZpbGw9IiNmMGY5ZmYiIHN0cm9rZT0iIzAyODRjNyIgc3Ryb2tlLXdpZHRoPSIxLjciLz48cmVjdCB4PSI2MCIgeT0iMTI0IiB3aWR0aD0iMjUwIiBoZWlnaHQ9IjIyIiByeD0iOCIgZmlsbD0iIzAyODRjNyIvPjxyZWN0IHg9IjYwIiB5PSIxMzgiIHdpZHRoPSIyNTAiIGhlaWdodD0iOCIgZmlsbD0iIzAyODRjNyIvPjx0ZXh0IHg9IjcwIiB5PSIxNDAiIGZvbnQtZmFtaWx5PSJ1aS1tb25vc3BhY2UsU0ZNb25vLVJlZ3VsYXIsTWVubG8sbW9ub3NwYWNlIiBmb250LXNpemU9IjExLjUiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiNmZmYiPlNraWEg5riy5p+T5ZmoPC90ZXh0Pjx0ZXh0IHg9IjcwIiB5PSIxNjAiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTAiIGZpbGw9IiMxZTI5M2IiPkdQVSDnm7Tnu5jvvIzmoYzpnaIv6auY56uv6K6+5aSHPC90ZXh0Pjx0ZXh0IHg9IjcwIiB5PSIxNzQiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTAiIGZpbGw9IiMxZTI5M2IiPuinguaEn+acgOeyvue7hjwvdGV4dD48L2c+PGc+PHJlY3QgeD0iMzQ1IiB5PSIxMjQiIHdpZHRoPSIyNTAiIGhlaWdodD0iNjYiIHJ4PSI4IiBmaWxsPSIjZjBmZGZhIiBzdHJva2U9IiMwZDk0ODgiIHN0cm9rZS13aWR0aD0iMS43Ii8+PHJlY3QgeD0iMzQ1IiB5PSIxMjQiIHdpZHRoPSIyNTAiIGhlaWdodD0iMjIiIHJ4PSI4IiBmaWxsPSIjMGQ5NDg4Ii8+PHJlY3QgeD0iMzQ1IiB5PSIxMzgiIHdpZHRoPSIyNTAiIGhlaWdodD0iOCIgZmlsbD0iIzBkOTQ4OCIvPjx0ZXh0IHg9IjM1NSIgeT0iMTQwIiBmb250LWZhbWlseT0idWktbW9ub3NwYWNlLFNGTW9uby1SZWd1bGFyLE1lbmxvLG1vbm9zcGFjZSIgZm9udC1zaXplPSIxMS41IiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjZmZmIj5GZW10b1ZHIOa4suafk+WZqDwvdGV4dD48dGV4dCB4PSIzNTUiIHk9IjE2MCIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMCIgZmlsbD0iIzFlMjkzYiI+T3BlbkdML0dMRVM8L3RleHQ+PHRleHQgeD0iMzU1IiB5PSIxNzQiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTAiIGZpbGw9IiMxZTI5M2IiPuS4reerr+iuvuWkhzwvdGV4dD48L2c+PGc+PHJlY3QgeD0iNjMwIiB5PSIxMjQiIHdpZHRoPSIyNTAiIGhlaWdodD0iNjYiIHJ4PSI4IiBmaWxsPSIjZjBmZGY0IiBzdHJva2U9IiMxNTgwM2QiIHN0cm9rZS13aWR0aD0iMS43Ii8+PHJlY3QgeD0iNjMwIiB5PSIxMjQiIHdpZHRoPSIyNTAiIGhlaWdodD0iMjIiIHJ4PSI4IiBmaWxsPSIjMTU4MDNkIi8+PHJlY3QgeD0iNjMwIiB5PSIxMzgiIHdpZHRoPSIyNTAiIGhlaWdodD0iOCIgZmlsbD0iIzE1ODAzZCIvPjx0ZXh0IHg9IjY0MCIgeT0iMTQwIiBmb250LWZhbWlseT0idWktbW9ub3NwYWNlLFNGTW9uby1SZWd1bGFyLE1lbmxvLG1vbm9zcGFjZSIgZm9udC1zaXplPSIxMS41IiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjZmZmIj7ova/ku7bmuLLmn5Plmag8L3RleHQ+PHRleHQgeD0iNjQwIiB5PSIxNjAiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTAiIGZpbGw9IiMxZTI5M2IiPue6ryBDUFUg5YWJ5qCF5YyWPC90ZXh0Pjx0ZXh0IHg9IjY0MCIgeT0iMTc0IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwIiBmaWxsPSIjMWUyOTNiIj7ml6AgR1BVIOS5n+iDvei3kTwvdGV4dD48L2c+PGc+PHBhdGggZD0iTSAxODUgMTkwIEwgMzAwIDI0MCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjMDI4NGM3IiBzdHJva2Utd2lkdGg9IjEuNiIgc3Ryb2tlLWRhc2hhcnJheT0iNSAzIiBtYXJrZXItZW5kPSJ1cmwoI2EpIi8+PC9nPjxnPjxwYXRoIGQ9Ik0gNDcwIDE5MCBMIDQ3MCAyNDAiIGZpbGw9Im5vbmUiIHN0cm9rZT0iIzBkOTQ4OCIgc3Ryb2tlLXdpZHRoPSIxLjYiIHN0cm9rZS1kYXNoYXJyYXk9IjUgMyIgbWFya2VyLWVuZD0idXJsKCNhKSIvPjwvZz48Zz48cGF0aCBkPSJNIDc1NSAxOTAgTCA2NDAgMjQwIiBmaWxsPSJub25lIiBzdHJva2U9IiMxNTgwM2QiIHN0cm9rZS13aWR0aD0iMS42IiBzdHJva2UtZGFzaGFycmF5PSI1IDMiIG1hcmtlci1lbmQ9InVybCgjYSkiLz48L2c+PGc+PHJlY3QgeD0iMTIwIiB5PSIyNDAiIHdpZHRoPSIyMjAiIGhlaWdodD0iNjAiIHJ4PSI4IiBmaWxsPSIjZjFmNWY5IiBzdHJva2U9IiM0NzU1NjkiIHN0cm9rZS13aWR0aD0iMS43Ii8+PHJlY3QgeD0iMTIwIiB5PSIyNDAiIHdpZHRoPSIyMjAiIGhlaWdodD0iMjIiIHJ4PSI4IiBmaWxsPSIjNDc1NTY5Ii8+PHJlY3QgeD0iMTIwIiB5PSIyNTQiIHdpZHRoPSIyMjAiIGhlaWdodD0iOCIgZmlsbD0iIzQ3NTU2OSIvPjx0ZXh0IHg9IjEzMCIgeT0iMjU2IiBmb250LWZhbWlseT0idWktbW9ub3NwYWNlLFNGTW9uby1SZWd1bGFyLE1lbmxvLG1vbm9zcGFjZSIgZm9udC1zaXplPSIxMS41IiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjZmZmIj7moYzpnaLvvIhXaW4vbWFjL0xpbnV477yJPC90ZXh0Pjx0ZXh0IHg9IjEzMCIgeT0iMjc2IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwIiBmaWxsPSIjMWUyOTNiIj5HUFUg5riy5p+T77yM5Yqf6IO95YWoPC90ZXh0PjwvZz48Zz48cGF0aCBkPSJNIDM0MCAyNzAgTCA0MDAgMjcwIiBmaWxsPSJub25lIiBzdHJva2U9IiMxNTgwM2QiIHN0cm9rZS13aWR0aD0iMS42IiBzdHJva2UtZGFzaGFycmF5PSI1IDMiIG1hcmtlci1lbmQ9InVybCgjYSkiLz48cmVjdCB4PSIzNTciIHk9IjI2MSIgd2lkdGg9IjI1LjIiIGhlaWdodD0iMTYiIHJ4PSI0IiBmaWxsPSIjZmZmIiBmaWxsLW9wYWNpdHk9IjAuOTUiIHN0cm9rZT0iI2NiZDVlMSIgc3Ryb2tlLXdpZHRoPSIwLjciLz48dGV4dCB4PSIzNzAiIHk9IjI3MyIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1mYW1pbHk9InVpLW1vbm9zcGFjZSxTRk1vbm8tUmVndWxhcixNZW5sbyxtb25vc3BhY2UiIGZvbnQtc2l6ZT0iOSIgZmlsbD0iIzMzNDE1NSI+5LiL5rKJPC90ZXh0PjwvZz48Zz48cmVjdCB4PSI0MDAiIHk9IjI0MCIgd2lkdGg9IjIwMCIgaGVpZ2h0PSI2MCIgcng9IjgiIGZpbGw9IiNmMWY1ZjkiIHN0cm9rZT0iIzQ3NTU2OSIgc3Ryb2tlLXdpZHRoPSIxLjciLz48cmVjdCB4PSI0MDAiIHk9IjI0MCIgd2lkdGg9IjIwMCIgaGVpZ2h0PSIyMiIgcng9IjgiIGZpbGw9IiM0NzU1NjkiLz48cmVjdCB4PSI0MDAiIHk9IjI1NCIgd2lkdGg9IjIwMCIgaGVpZ2h0PSI4IiBmaWxsPSIjNDc1NTY5Ii8+PHRleHQgeD0iNDEwIiB5PSIyNTYiIGZvbnQtZmFtaWx5PSJ1aS1tb25vc3BhY2UsU0ZNb25vLVJlZ3VsYXIsTWVubG8sbW9ub3NwYWNlIiBmb250LXNpemU9IjExLjUiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiNmZmYiPuW1jOWFpeW8jyBMaW51eDwvdGV4dD48dGV4dCB4PSI0MTAiIHk9IjI3NiIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMCIgZmlsbD0iIzFlMjkzYiI+5bel5o6nIEhNSSAvIOi9puacujwvdGV4dD48L2c+PGc+PHBhdGggZD0iTSA2MDAgMjcwIEwgNjYwIDI3MCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjMTU4MDNkIiBzdHJva2Utd2lkdGg9IjEuNiIgc3Ryb2tlLWRhc2hhcnJheT0iNSAzIiBtYXJrZXItZW5kPSJ1cmwoI2EpIi8+PHJlY3QgeD0iNjE0IiB5PSIyNjEiIHdpZHRoPSIzMS43OTk5OTk5OTk5OTk5OTciIGhlaWdodD0iMTYiIHJ4PSI0IiBmaWxsPSIjZmZmIiBmaWxsLW9wYWNpdHk9IjAuOTUiIHN0cm9rZT0iI2NiZDVlMSIgc3Ryb2tlLXdpZHRoPSIwLjciLz48dGV4dCB4PSI2MzAiIHk9IjI3MyIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1mYW1pbHk9InVpLW1vbm9zcGFjZSxTRk1vbm8tUmVndWxhcixNZW5sbyxtb25vc3BhY2UiIGZvbnQtc2l6ZT0iOSIgZmlsbD0iIzMzNDE1NSI+5YaN5LiL5rKJPC90ZXh0PjwvZz48Zz48cmVjdCB4PSI2NjAiIHk9IjI0MCIgd2lkdGg9IjI0MCIgaGVpZ2h0PSI2MCIgcng9IjgiIGZpbGw9IiNmMGZkZjQiIHN0cm9rZT0iIzE1ODAzZCIgc3Ryb2tlLXdpZHRoPSIxLjciLz48cmVjdCB4PSI2NjAiIHk9IjI0MCIgd2lkdGg9IjI0MCIgaGVpZ2h0PSIyMiIgcng9IjgiIGZpbGw9IiMxNTgwM2QiLz48cmVjdCB4PSI2NjAiIHk9IjI1NCIgd2lkdGg9IjI0MCIgaGVpZ2h0PSI4IiBmaWxsPSIjMTU4MDNkIi8+PHRleHQgeD0iNjcwIiB5PSIyNTYiIGZvbnQtZmFtaWx5PSJ1aS1tb25vc3BhY2UsU0ZNb25vLVJlZ3VsYXIsTWVubG8sbW9ub3NwYWNlIiBmb250LXNpemU9IjExLjUiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiNmZmYiPk1DVe+8iG5vX3N0ZO+8iTwvdGV4dD48dGV4dCB4PSI2NzAiIHk9IjI3NiIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMCIgZmlsbD0iIzFlMjkzYiI+U1RNMzIvRVNQMzLvvIzmlbDnmb4gS0IgUkFNPC90ZXh0Pjx0ZXh0IHg9IjY3MCIgeT0iMjkwIiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwIiBmaWxsPSIjMWUyOTNiIj7ova/ku7bmuLLmn5MgKyDlubPlj7DpgILphY3lsYI8L3RleHQ+PC9nPjxnPjxyZWN0IHg9IjIzMCIgeT0iMzQwIiB3aWR0aD0iNDgwIiBoZWlnaHQ9IjQyIiByeD0iOCIgZmlsbD0iI2Y1ZjNmZiIgc3Ryb2tlPSIjN2MzYWVkIiBzdHJva2Utd2lkdGg9IjEuNyIvPjxyZWN0IHg9IjIzMCIgeT0iMzQwIiB3aWR0aD0iNDgwIiBoZWlnaHQ9IjIyIiByeD0iOCIgZmlsbD0iIzdjM2FlZCIvPjxyZWN0IHg9IjIzMCIgeT0iMzU0IiB3aWR0aD0iNDgwIiBoZWlnaHQ9IjgiIGZpbGw9IiM3YzNhZWQiLz48dGV4dCB4PSIyNDAiIHk9IjM1NiIgZm9udC1mYW1pbHk9InVpLW1vbm9zcGFjZSxTRk1vbm8tUmVndWxhcixNZW5sbyxtb25vc3BhY2UiIGZvbnQtc2l6ZT0iMTEuNSIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iI2ZmZiI+4piFIOadgOaJi+mUj++8muS6lOahhuaetumHjOWUr+S4gOiDvSBub19zdGQg6LeR5LiK5Y2V54mH5py655qEPC90ZXh0PjwvZz48dGV4dCB4PSI0NzAiIHk9IjQxNCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMi41IiBmaWxsPSIjMzM0MTU1Ij7lkIzkuIDku70gLnNsaW5077yM5o2i5riy5p+T5Zmo5ZCO56uv5Y2z5LuO5qGM6Z2iIEdQVSDkuIDot6/kuIvmsonliLDltYzlhaXlvI8gTGludXjjgIHkuYPoh7PmlbDnmb4gS0IgUkFNIOeahCBNQ1XigJTigJRpY2VkL2VndWkvRGlveHVzL1RhdXJpIOmDveWIsOS4jeS6hui/meS4gOWxgjwvdGV4dD48L3N2Zz4="></p>

**这是 Slint 相对另外四家的独门能力**：同一份 `.slint`，换渲染器后端就能从桌面一路下沉到单片机。

- **三渲染器**：`Skia`（GPU，桌面/高端，最精细）、`FemtoVG`（OpenGL/GLES，中端）、`software`（纯 CPU 光栅化，无 GPU 也能跑）。用 feature 选：

```toml
slint = { version = "1.17", features = ["renderer-skia"] }
# 或 renderer-femtovg / renderer-software；嵌入式再加 no_std 相关配置
```

- **下沉链**：桌面（GPU）→ 嵌入式 Linux（工控 HMI / 车机）→ **MCU（`no_std`，STM32/ESP32 级，数百 KB RAM，软件渲染 + 自定义平台适配层）**。
- **杀手锏**：**五框架里唯一能 `no_std` 跑上单片机的**——iced / egui / Dioxus / Tauri 全都到不了这一层。做工业 HMI、车机、白电、仪器面板，这是 Slint 的独家主场。

> 嵌入式做法：`no_std` + `renderer-software` + 实现 `slint::platform::Platform`（提供显示缓冲、时间、输入）。官方有 MCU 板级示例（STM32、ESP32、树莓派 Pico 等）。这也是 Slint 有商业公司背书、按设备收费的底气所在（第 12 节）。

## 十一、live-preview 与工具链

Slint 的工具链是它「设计协作」卖点的兑现：

| 工具 | 用途 |
|---|---|
| **VS Code 扩展** | `.slint` 语法高亮 + **live-preview（即改即见）** + 补全 |
| **SlintPad** | 浏览器里在线写 `.slint` 即时预览（slintpad.com） |
| **`slint-viewer`** | 命令行直接预览一个 `.slint` 文件 |
| **设计器（Slint Designer）** | 可视化拖拽编辑 `.slint`（面向设计师） |
| **Figma 导入** | 从 Figma 设计稿生成 `.slint`（官方插件） |

> **live-preview 是它对 iced 的代差**：改 `.slint` 里的 UI，预览器**即刻刷新**，不用重编 Rust（逻辑没变时）。这让 UI 迭代很快——是「设计与逻辑分离」在开发体验上的直接兑现。逻辑改动仍要重编。

## 十二、许可证三选一：GPL / 免版税 / 商业

<p align="center"><img alt="图7：许可三选一" style="max-width:100%;height:auto;border:1px solid #e8eef5;border-radius:10px" src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA5NDAgNDIwIiB3aWR0aD0iOTQwIiBoZWlnaHQ9IjQyMCIgcm9sZT0iaW1nIj48ZGVmcz48bWFya2VyIGlkPSJhIiB2aWV3Qm94PSIwIDAgMTAgMTAiIHJlZlg9IjguNSIgcmVmWT0iNSIgbWFya2VyV2lkdGg9IjciIG1hcmtlckhlaWdodD0iNyIgb3JpZW50PSJhdXRvLXN0YXJ0LXJldmVyc2UiPjxwYXRoIGQ9Ik0gMCAwIEwgMTAgNSBMIDAgMTAgeiIgZmlsbD0iIzY0NzQ4YiIvPjwvbWFya2VyPjwvZGVmcz48cmVjdCB3aWR0aD0iOTQwIiBoZWlnaHQ9IjQyMCIgZmlsbD0iI2ZiZmRmZiIvPjxnPjxyZWN0IHg9IjM2MCIgeT0iNDYiIHdpZHRoPSIyMjAiIGhlaWdodD0iNDQiIHJ4PSI4IiBmaWxsPSIjZjFmNWY5IiBzdHJva2U9IiM0NzU1NjkiIHN0cm9rZS13aWR0aD0iMS43Ii8+PHJlY3QgeD0iMzYwIiB5PSI0NiIgd2lkdGg9IjIyMCIgaGVpZ2h0PSIyMiIgcng9IjgiIGZpbGw9IiM0NzU1NjkiLz48cmVjdCB4PSIzNjAiIHk9IjYwIiB3aWR0aD0iMjIwIiBoZWlnaHQ9IjgiIGZpbGw9IiM0NzU1NjkiLz48dGV4dCB4PSIzNzAiIHk9IjYyIiBmb250LWZhbWlseT0idWktbW9ub3NwYWNlLFNGTW9uby1SZWd1bGFyLE1lbmxvLG1vbm9zcGFjZSIgZm9udC1zaXplPSIxMS41IiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjZmZmIj7kvaDnmoQgU2xpbnQg5bqU55So6KaB5Y+R5biD5oiQ77yfPC90ZXh0PjwvZz48Zz48cmVjdCB4PSI2MCIgeT0iMTUwIiB3aWR0aD0iMjUwIiBoZWlnaHQ9Ijk2IiByeD0iOCIgZmlsbD0iI2YwZmRmNCIgc3Ryb2tlPSIjMTU4MDNkIiBzdHJva2Utd2lkdGg9IjEuNyIvPjxyZWN0IHg9IjYwIiB5PSIxNTAiIHdpZHRoPSIyNTAiIGhlaWdodD0iMjIiIHJ4PSI4IiBmaWxsPSIjMTU4MDNkIi8+PHJlY3QgeD0iNjAiIHk9IjE2NCIgd2lkdGg9IjI1MCIgaGVpZ2h0PSI4IiBmaWxsPSIjMTU4MDNkIi8+PHRleHQgeD0iNzAiIHk9IjE2NiIgZm9udC1mYW1pbHk9InVpLW1vbm9zcGFjZSxTRk1vbm8tUmVndWxhcixNZW5sbyxtb25vc3BhY2UiIGZvbnQtc2l6ZT0iMTEuNSIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iI2ZmZiI+4pGgIOW8gOa6kOW6lOeUqDwvdGV4dD48dGV4dCB4PSI3MCIgeT0iMTg2IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwIiBmaWxsPSIjMWUyOTNiIj7mlbTkvZPlvIDmupDljbPlj6/lhY3otLk8L3RleHQ+PHRleHQgeD0iNzAiIHk9IjIwMCIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMCIgZmlsbD0iIzFlMjkzYiI+5ZCr5bWM5YWl5byP6K6+5aSHPC90ZXh0Pjx0ZXh0IHg9IjcwIiB5PSIyMTQiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTAiIGZpbGw9IiMxZTI5M2IiPjwvdGV4dD48dGV4dCB4PSI3MCIgeT0iMjI4IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwIiBmaWxsPSIjMWUyOTNiIj7ihpIgR1BMdjM8L3RleHQ+PC9nPjxnPjxyZWN0IHg9IjM0NSIgeT0iMTUwIiB3aWR0aD0iMjUwIiBoZWlnaHQ9Ijk2IiByeD0iOCIgZmlsbD0iI2VlZjJmZiIgc3Ryb2tlPSIjNDMzOGNhIiBzdHJva2Utd2lkdGg9IjEuNyIvPjxyZWN0IHg9IjM0NSIgeT0iMTUwIiB3aWR0aD0iMjUwIiBoZWlnaHQ9IjIyIiByeD0iOCIgZmlsbD0iIzQzMzhjYSIvPjxyZWN0IHg9IjM0NSIgeT0iMTY0IiB3aWR0aD0iMjUwIiBoZWlnaHQ9IjgiIGZpbGw9IiM0MzM4Y2EiLz48dGV4dCB4PSIzNTUiIHk9IjE2NiIgZm9udC1mYW1pbHk9InVpLW1vbm9zcGFjZSxTRk1vbm8tUmVndWxhcixNZW5sbyxtb25vc3BhY2UiIGZvbnQtc2l6ZT0iMTEuNSIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iI2ZmZiI+4pGhIOmXrea6kO+8muahjOmdoi/np7vliqgvV2ViPC90ZXh0Pjx0ZXh0IHg9IjM1NSIgeT0iMTg2IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwIiBmaWxsPSIjMWUyOTNiIj7lhY3otLnvvIzlkKvllYbnlKjpl63mupA8L3RleHQ+PHRleHQgeD0iMzU1IiB5PSIyMDAiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTAiIGZpbGw9IiMxZTI5M2IiPuadoeS7tu+8muS/neeVmTwvdGV4dD48dGV4dCB4PSIzNTUiIHk9IjIxNCIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMCIgZmlsbD0iIzFlMjkzYiI+44CMTWFkZSB3aXRoIFNsaW5044CN5b2S5bGePC90ZXh0Pjx0ZXh0IHg9IjM1NSIgeT0iMjI4IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwIiBmaWxsPSIjMWUyOTNiIj7ihpIgUm95YWx0eS1GcmVlIOWFjeeJiOeojjwvdGV4dD48L2c+PGc+PHJlY3QgeD0iNjMwIiB5PSIxNTAiIHdpZHRoPSIyNTAiIGhlaWdodD0iOTYiIHJ4PSI4IiBmaWxsPSIjZmZmYmViIiBzdHJva2U9IiNiNDUzMDkiIHN0cm9rZS13aWR0aD0iMS43Ii8+PHJlY3QgeD0iNjMwIiB5PSIxNTAiIHdpZHRoPSIyNTAiIGhlaWdodD0iMjIiIHJ4PSI4IiBmaWxsPSIjYjQ1MzA5Ii8+PHJlY3QgeD0iNjMwIiB5PSIxNjQiIHdpZHRoPSIyNTAiIGhlaWdodD0iOCIgZmlsbD0iI2I0NTMwOSIvPjx0ZXh0IHg9IjY0MCIgeT0iMTY2IiBmb250LWZhbWlseT0idWktbW9ub3NwYWNlLFNGTW9uby1SZWd1bGFyLE1lbmxvLG1vbm9zcGFjZSIgZm9udC1zaXplPSIxMS41IiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjZmZmIj7ikaIg6Zet5rqQICsg5bWM5YWl5byP5Y+R6LSnPC90ZXh0Pjx0ZXh0IHg9IjY0MCIgeT0iMTg2IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwIiBmaWxsPSIjMWUyOTNiIj7orr7lpIfnq6/pl63mupDlh7rotKc8L3RleHQ+PHRleHQgeD0iNjQwIiB5PSIyMDAiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTAiIGZpbGw9IiMxZTI5M2IiPuW/hemhu+S7mOi0ue+8iOaMieiuvuWkh+iuoei0ue+8iTwvdGV4dD48dGV4dCB4PSI2NDAiIHk9IjIxNCIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMCIgZmlsbD0iIzFlMjkzYiI+5oiW5Zue5YiwIEdQTDwvdGV4dD48dGV4dCB4PSI2NDAiIHk9IjIyOCIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMCIgZmlsbD0iIzFlMjkzYiI+4oaSIENvbW1lcmNpYWwg5ZWG5Lia6K645Y+vPC90ZXh0PjwvZz48Zz48cGF0aCBkPSJNIDQwMCA5MCBMIDE4NSAxNTAiIGZpbGw9Im5vbmUiIHN0cm9rZT0iIzE1ODAzZCIgc3Ryb2tlLXdpZHRoPSIxLjYiIHN0cm9rZS1kYXNoYXJyYXk9IjUgMyIgbWFya2VyLWVuZD0idXJsKCNhKSIvPjxyZWN0IHg9IjI4MCIgeT0iMTExIiB3aWR0aD0iMjUuMiIgaGVpZ2h0PSIxNiIgcng9IjQiIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iMC45NSIgc3Ryb2tlPSIjY2JkNWUxIiBzdHJva2Utd2lkdGg9IjAuNyIvPjx0ZXh0IHg9IjI5MiIgeT0iMTIzIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LWZhbWlseT0idWktbW9ub3NwYWNlLFNGTW9uby1SZWd1bGFyLE1lbmxvLG1vbm9zcGFjZSIgZm9udC1zaXplPSI5IiBmaWxsPSIjMzM0MTU1Ij7lvIDmupA8L3RleHQ+PC9nPjxnPjxwYXRoIGQ9Ik0gNDcwIDkwIEwgNDcwIDE1MCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjNDMzOGNhIiBzdHJva2Utd2lkdGg9IjEuNiIgc3Ryb2tlLWRhc2hhcnJheT0iNSAzIiBtYXJrZXItZW5kPSJ1cmwoI2EpIi8+PHJlY3QgeD0iNDQxIiB5PSIxMTEiIHdpZHRoPSI1OC4xOTk5OTk5OTk5OTk5OTYiIGhlaWdodD0iMTYiIHJ4PSI0IiBmaWxsPSIjZmZmIiBmaWxsLW9wYWNpdHk9IjAuOTUiIHN0cm9rZT0iI2NiZDVlMSIgc3Ryb2tlLXdpZHRoPSIwLjciLz48dGV4dCB4PSI0NzAiIHk9IjEyMyIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1mYW1pbHk9InVpLW1vbm9zcGFjZSxTRk1vbm8tUmVndWxhcixNZW5sbyxtb25vc3BhY2UiIGZvbnQtc2l6ZT0iOSIgZmlsbD0iIzMzNDE1NSI+6Zet5rqQwrfpnZ7ltYzlhaXlvI88L3RleHQ+PC9nPjxnPjxwYXRoIGQ9Ik0gNTQwIDkwIEwgNzU1IDE1MCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjYjQ1MzA5IiBzdHJva2Utd2lkdGg9IjEuNiIgc3Ryb2tlLWRhc2hhcnJheT0iNSAzIiBtYXJrZXItZW5kPSJ1cmwoI2EpIi8+PHJlY3QgeD0iNjIyIiB5PSIxMTEiIHdpZHRoPSI1MS41OTk5OTk5OTk5OTk5OTQiIGhlaWdodD0iMTYiIHJ4PSI0IiBmaWxsPSIjZmZmIiBmaWxsLW9wYWNpdHk9IjAuOTUiIHN0cm9rZT0iI2NiZDVlMSIgc3Ryb2tlLXdpZHRoPSIwLjciLz48dGV4dCB4PSI2NDgiIHk9IjEyMyIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1mYW1pbHk9InVpLW1vbm9zcGFjZSxTRk1vbm8tUmVndWxhcixNZW5sbyxtb25vc3BhY2UiIGZvbnQtc2l6ZT0iOSIgZmlsbD0iIzMzNDE1NSI+6Zet5rqQwrfltYzlhaXlvI88L3RleHQ+PC9nPjxnPjxyZWN0IHg9IjE1MCIgeT0iMzAwIiB3aWR0aD0iNjQwIiBoZWlnaHQ9IjYwIiByeD0iOCIgZmlsbD0iI2Y1ZjNmZiIgc3Ryb2tlPSIjN2MzYWVkIiBzdHJva2Utd2lkdGg9IjEuNyIvPjxyZWN0IHg9IjE1MCIgeT0iMzAwIiB3aWR0aD0iNjQwIiBoZWlnaHQ9IjIyIiByeD0iOCIgZmlsbD0iIzdjM2FlZCIvPjxyZWN0IHg9IjE1MCIgeT0iMzE0IiB3aWR0aD0iNjQwIiBoZWlnaHQ9IjgiIGZpbGw9IiM3YzNhZWQiLz48dGV4dCB4PSIxNjAiIHk9IjMxNiIgZm9udC1mYW1pbHk9InVpLW1vbm9zcGFjZSxTRk1vbm8tUmVndWxhcixNZW5sbyxtb25vc3BhY2UiIGZvbnQtc2l6ZT0iMTEuNSIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iI2ZmZiI+5Yaz562W5o+Q56S6PC90ZXh0Pjx0ZXh0IHg9IjE2MCIgeT0iMzM2IiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwIiBmaWxsPSIjMWUyOTNiIj7kvIHkuJrlhoXpg6jlt6XlhbcgLyDmoYzpnaLkuqflk4HvvJrotbAgUm95YWx0eS1GcmVl77yM5YWN6LS577yI5L+d55WZ5b2S5bGe5aOw5piO5Y2z5Y+v77yJPC90ZXh0Pjx0ZXh0IHg9IjE2MCIgeT0iMzUwIiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEwIiBmaWxsPSIjMWUyOTNiIj7llK/kuIDkvJrnorDmlLbotLnpl7jpl6jnmoTnu4TlkIggPSDjgIzpl63mupAgKyDltYzlhaXlvI/orr7lpIflj5HotKfjgI3vvJvlkKvlrpjmlrnku5jotLnmioDmnK/mlK/mjIE8L3RleHQ+PC9nPjx0ZXh0IHg9IjQ3MCIgeT0iMzk4IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEyLjUiIGZpbGw9IiMzMzQxNTUiPlNsaW50IOeLrOacieeahOS4ieiuuOWPr++8muW8gOa6kOKGkkdQTO+8m+mXrea6kOahjOmdoi/np7vliqgvV2Vi4oaS5YWN54mI56iO77yI5YWN6LS5K+W9kuWxnu+8ie+8m+mXrea6kOW1jOWFpeW8j+WPkei0p+KGkuWVhuS4mu+8iOS7mOi0ue+8ieOAgumAieWei+W/hemhu+aKiui/meadoeeul+i/m+WOuzwvdGV4dD48L3N2Zz4="></p>

**这一节可能直接决定你能不能用它**——Slint 是本系列唯一非纯宽松许可的框架，**三选一**：

| 许可 | 适用 | 代价 |
|---|---|---|
| **GPLv3** | 应用整体开源（含嵌入式） | 你的应用也得开源 |
| **Royalty-Free（免版税）** | **桌面 / 移动 / Web，含闭源商用** | 保留「Made with Slint」归属声明 |
| **Commercial（商业）** | **闭源 + 嵌入式设备发货** | 按设备计费；含官方付费支持 |

决策提示：

- **企业内部工具 / 桌面产品**：走 **Royalty-Free**，免费，保留一行归属声明即可——绝大多数团队走这条。
- **要开源**：GPLv3，免费，含嵌入式。
- **唯一会碰收费闸门的组合 = 「闭源 + 嵌入式设备发货」**：要么买商业许可（按设备计费，官方公布过 1 美元/台级起步的方案），要么回到 GPL。

> 一句话：**桌面/Web 场景 Slint 免费可商用**（保留归属）；**只有闭源硬件出货这一种情况要付费**。选型时把这条和「你会不会做嵌入式发货」一起想清楚。

## 十三、完整实例：待办事项 Todo

<p align="center"><img alt="图8：Todo 应用界面" style="max-width:100%;height:auto;border:1px solid #e8eef5;border-radius:10px" src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA2NDAgNDUwIiB3aWR0aD0iNjQwIiBoZWlnaHQ9IjQ1MCIgcm9sZT0iaW1nIj48ZGVmcz48bWFya2VyIGlkPSJhIiB2aWV3Qm94PSIwIDAgMTAgMTAiIHJlZlg9IjguNSIgcmVmWT0iNSIgbWFya2VyV2lkdGg9IjciIG1hcmtlckhlaWdodD0iNyIgb3JpZW50PSJhdXRvLXN0YXJ0LXJldmVyc2UiPjxwYXRoIGQ9Ik0gMCAwIEwgMTAgNSBMIDAgMTAgeiIgZmlsbD0iIzY0NzQ4YiIvPjwvbWFya2VyPjwvZGVmcz48cmVjdCB3aWR0aD0iNjQwIiBoZWlnaHQ9IjQ1MCIgZmlsbD0iI2ZiZmRmZiIvPjxnPjxyZWN0IHg9IjgwIiB5PSI0MCIgd2lkdGg9IjQ4MCIgaGVpZ2h0PSIzNzAiIHJ4PSI5IiBmaWxsPSIjZmZmZmZmIiBzdHJva2U9IiNjYmQ1ZTEiIHN0cm9rZS13aWR0aD0iMS40Ii8+PHJlY3QgeD0iODAiIHk9IjQwIiB3aWR0aD0iNDgwIiBoZWlnaHQ9IjI2IiByeD0iOSIgZmlsbD0iIzdjM2FlZCIvPjxyZWN0IHg9IjgwIiB5PSI1NyIgd2lkdGg9IjQ4MCIgaGVpZ2h0PSI5IiBmaWxsPSIjN2MzYWVkIi8+PGNpcmNsZSBjeD0iOTUiIGN5PSI1MyIgcj0iNC41IiBmaWxsPSIjZmY1ZjU3Ii8+PGNpcmNsZSBjeD0iMTEwIiBjeT0iNTMiIHI9IjQuNSIgZmlsbD0iI2ZlYmMyZSIvPjxjaXJjbGUgY3g9IjEyNSIgY3k9IjUzIiByPSI0LjUiIGZpbGw9IiMyOGM4NDAiLz48dGV4dCB4PSIzMjAuMCIgeT0iNTciIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtZmFtaWx5PSJ1aS1tb25vc3BhY2UsU0ZNb25vLVJlZ3VsYXIsTWVubG8sbW9ub3NwYWNlIiBmb250LXNpemU9IjExIiBmb250LXdlaWdodD0iNzAwIiBmaWxsPSIjZmZmIj5Ub2RvcyDigJQgU2xpbnQ8L3RleHQ+PC9nPjx0ZXh0IHg9IjEwNSIgeT0iODQiIHRleHQtYW5jaG9yPSJzdGFydCIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxNiIgZm9udC13ZWlnaHQ9IjcwMCIgZmlsbD0iIzBmMTcyYSI+5b6F5Yqe5LqL6aG5PC90ZXh0PjxnPjxyZWN0IHg9IjEwNSIgeT0iMTAwIiB3aWR0aD0iMzIwIiBoZWlnaHQ9IjMyIiByeD0iNiIgZmlsbD0iI2ZmZiIgc3Ryb2tlPSIjY2JkNWUxIiBzdHJva2Utd2lkdGg9IjEuMyIvPjx0ZXh0IHg9IjExNSIgeT0iMTIwIiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjExIiBmaWxsPSIjOTRhM2I4Ij7opoHlgZrngrnku4DkuYjvvJ88L3RleHQ+PC9nPjxnPjxyZWN0IHg9IjQzOCIgeT0iMTAyIiB3aWR0aD0iOTYiIGhlaWdodD0iMjgiIHJ4PSIxNCIgZmlsbD0iIzdjM2FlZCIvPjx0ZXh0IHg9IjQ4Ni4wIiB5PSIxMjAiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTEiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiNmZmYiPua3u+WKoDwvdGV4dD48L2c+PGxpbmUgeDE9IjEwNSIgeTE9IjE1MCIgeDI9IjUzNCIgeTI9IjE1MCIgc3Ryb2tlPSIjZTJlOGYwIiBzdHJva2Utd2lkdGg9IjEuNCIvPjxyZWN0IHg9IjExMiIgeT0iMTY2IiB3aWR0aD0iMjAiIGhlaWdodD0iMjAiIHJ4PSI0IiBmaWxsPSIjN2MzYWVkIi8+PHBhdGggZD0iTSAxMTYgMTc2IGwgNCA0IGwgOCAtOSIgc3Ryb2tlPSIjZmZmIiBzdHJva2Utd2lkdGg9IjIuMiIgZmlsbD0ibm9uZSIvPjx0ZXh0IHg9IjE0MiIgeT0iMTgxIiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEyLjUiIGZpbGw9IiM5NGEzYjgiIHRleHQtZGVjb3JhdGlvbj0ibGluZS10aHJvdWdoIj7lhpkgc2xpbnQg5L2/55So6K+05piOPC90ZXh0PjxnPjxyZWN0IHg9IjQ5NCIgeT0iMTY0IiB3aWR0aD0iNDAiIGhlaWdodD0iMjQiIHJ4PSI2IiBmaWxsPSIjZmVmMmYyIi8+PHRleHQgeD0iNTE0LjAiIHk9IjE4MCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMSIgZm9udC13ZWlnaHQ9IjYwMCIgZmlsbD0iI2RjMjYyNiI+5Yig6ZmkPC90ZXh0PjwvZz48cmVjdCB4PSIxMTIiIHk9IjIwOCIgd2lkdGg9IjIwIiBoZWlnaHQ9IjIwIiByeD0iNCIgZmlsbD0iIzdjM2FlZCIvPjxwYXRoIGQ9Ik0gMTE2IDIxOCBsIDQgNCBsIDggLTkiIHN0cm9rZT0iI2ZmZiIgc3Ryb2tlLXdpZHRoPSIyLjIiIGZpbGw9Im5vbmUiLz48dGV4dCB4PSIxNDIiIHk9IjIyMyIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMi41IiBmaWxsPSIjOTRhM2I4IiB0ZXh0LWRlY29yYXRpb249ImxpbmUtdGhyb3VnaCI+55S7IDgg5bygIFNWRyDlm748L3RleHQ+PGc+PHJlY3QgeD0iNDk0IiB5PSIyMDYiIHdpZHRoPSI0MCIgaGVpZ2h0PSIyNCIgcng9IjYiIGZpbGw9IiNmZWYyZjIiLz48dGV4dCB4PSI1MTQuMCIgeT0iMjIyIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjExIiBmb250LXdlaWdodD0iNjAwIiBmaWxsPSIjZGMyNjI2Ij7liKDpmaQ8L3RleHQ+PC9nPjxyZWN0IHg9IjExMiIgeT0iMjUwIiB3aWR0aD0iMjAiIGhlaWdodD0iMjAiIHJ4PSI0IiBmaWxsPSIjZmZmIiBzdHJva2U9IiM5NGEzYjgiIHN0cm9rZS13aWR0aD0iMS44Ii8+PHRleHQgeD0iMTQyIiB5PSIyNjUiIHRleHQtYW5jaG9yPSJzdGFydCIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMi41IiBmb250LXdlaWdodD0iNDAwIiBmaWxsPSIjMWUyOTNiIj7ot5EgZ2VuX3NsaW50LnB5IOagoemqjDwvdGV4dD48Zz48cmVjdCB4PSI0OTQiIHk9IjI0OCIgd2lkdGg9IjQwIiBoZWlnaHQ9IjI0IiByeD0iNiIgZmlsbD0iI2ZlZjJmMiIvPjx0ZXh0IHg9IjUxNC4wIiB5PSIyNjQiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTEiIGZvbnQtd2VpZ2h0PSI2MDAiIGZpbGw9IiNkYzI2MjYiPuWIoOmZpDwvdGV4dD48L2c+PGxpbmUgeDE9IjEwNSIgeTE9IjMwNiIgeDI9IjUzNCIgeTI9IjMwNiIgc3Ryb2tlPSIjZTJlOGYwIiBzdHJva2Utd2lkdGg9IjEuNCIvPjx0ZXh0IHg9IjExMiIgeT0iMzMwIiB0ZXh0LWFuY2hvcj0ic3RhcnQiIGZvbnQtZmFtaWx5PSItYXBwbGUtc3lzdGVtLEJsaW5rTWFjU3lzdGVtRm9udCwnUGluZ0ZhbmcgU0MnLCdNaWNyb3NvZnQgWWFIZWknLHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTIiIGZvbnQtd2VpZ2h0PSI3MDAiIGZpbGw9IiM2NDc0OGIiPuWFsSAzIOmhuSDCtyDlt7LlrozmiJAgMiDpobk8L3RleHQ+PHRleHQgeD0iMTA1IiB5PSIzOTYiIHRleHQtYW5jaG9yPSJzdGFydCIgZm9udC1mYW1pbHk9Ii1hcHBsZS1zeXN0ZW0sQmxpbmtNYWNTeXN0ZW1Gb250LCdQaW5nRmFuZyBTQycsJ01pY3Jvc29mdCBZYUhlaScsc2Fucy1zZXJpZiIgZm9udC1zaXplPSI5LjUiIGZvbnQtd2VpZ2h0PSI0MDAiIGZpbGw9IiM5NGEzYjgiPuexu+WOn+eUn+aOp+S7tuinguaEn++8iEZsdWVudCDpo47vvInvvJvkuIrpnaLov5nkuIDlsY8gPSDnrKwgMTMg6IqC5a6M5pW05Luj56CB55qE5Lqn54mpPC90ZXh0Pjx0ZXh0IHg9IjMyMCIgeT0iNDM0IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LWZhbWlseT0iLWFwcGxlLXN5c3RlbSxCbGlua01hY1N5c3RlbUZvbnQsJ1BpbmdGYW5nIFNDJywnTWljcm9zb2Z0IFlhSGVpJyxzYW5zLXNlcmlmIiBmb250LXNpemU9IjEyLjUiIGZpbGw9IiMzMzQxNTUiPuesrCAxMyDoioLlrozmlbTku6PnoIHnmoTmiJDlk4HvvJpMaW5lRWRpdCArIExpc3RWaWV377yI5Yu+6YCJL+WIoOmZpO+8iSsg6K6h5pWw77yMVUkg5ZyoIC5zbGludOOAgemAu+i+keWcqCBSdXN0PC90ZXh0Pjwvc3ZnPg=="></p>

把前面的概念串起来——待办事项应用。`ui/todo.slint`（UI）：

```slint
import { Button, LineEdit, CheckBox, ListView, VerticalBox, HorizontalBox } from "std-widgets.slint";

struct TodoItem { id: int, text: string, done: bool }

export component TodoWindow inherits Window {
    preferred-width: 460px;
    preferred-height: 420px;

    in property <[TodoItem]> todos;
    in-out property <string> input;
    callback add();
    callback toggle(int);
    callback remove(int);

    VerticalBox {
        Text { text: "待办事项"; font-size: 22px; }
        HorizontalBox {
            LineEdit {
                placeholder-text: "要做点什么？";
                text <=> root.input;                 // 双向绑定
                accepted => { root.add(); }          // 回车提交
            }
            Button { text: "添加"; clicked => { root.add(); } }
        }
        ListView {
            for item in root.todos: HorizontalBox {
                CheckBox { checked: item.done; toggled => { root.toggle(item.id); } }
                Text { text: item.text; horizontal-stretch: 1; }
                Button { text: "删除"; clicked => { root.remove(item.id); } }
            }
        }
    }
}
```

`src/main.rs`（逻辑）：

```rust
slint::include_modules!();
use slint::{Model, VecModel};
use std::rc::Rc;

fn main() -> Result<(), slint::PlatformError> {
    let ui = TodoWindow::new()?;
    let todos = Rc::new(VecModel::<TodoItem>::default());
    ui.set_todos(todos.clone().into());
    let mut next_id = 0;

    // 添加
    let weak = ui.as_weak();
    let model = todos.clone();
    ui.on_add(move || {
        let ui = weak.upgrade().unwrap();
        let text = ui.get_input();
        if !text.trim().is_empty() {
            model.push(TodoItem { id: next_id, text: text.trim().into(), done: false });
            next_id += 1;
            ui.set_input(Default::default());
        }
    });

    // 勾选
    let model = todos.clone();
    ui.on_toggle(move |id| {
        for i in 0..model.row_count() {
            let mut it = model.row_data(i).unwrap();
            if it.id == id { it.done = !it.done; model.set_row_data(i, it); break; }
        }
    });

    // 删除
    let model = todos.clone();
    ui.on_remove(move |id| {
        for i in 0..model.row_count() {
            if model.row_data(i).unwrap().id == id { model.remove(i); break; }
        }
    });

    ui.run()
}
```

这段覆盖了：**属性 + 双向绑定、callback 声明与 `on_*` 处理、Weak 句柄、VecModel 增删改、`for…in` 列表**——就是图 8 那个界面。UI 全在 `.slint`、逻辑全在 Rust，物理分离。

## 十四、常见坑速查

| 坑 | 症状 | 正解 |
|---|---|---|
| 回调捕获强引用 `ui` | 内存泄漏（组件不释放） | 用 `ui.as_weak()` + `upgrade()`（Slint 头号坑） |
| 把 `Rc<VecModel>` move 进线程 | 编译报错「不是 Send」 | 送 `Weak`，`upgrade_in_event_loop` 里改模型 |
| 忘了 `build.rs` / `include_modules!` | 找不到 `AppWindow` | 两者配套：build 编译 .slint，include 拉进来 |
| 属性方向选错 | Rust 没有 `set_x` / `get_x` | 要 Rust 写用 `in`/`in-out`，要读用 `out`/`in-out` |
| 事件循环不在主线程 | 崩溃 / 卡住 | `ui.run()` 与组件创建都在主线程 |
| 以为免费随便用 | 闭源嵌入式发货侵权 | 该场景需商业许可或 GPL（第 12 节） |
| DSL 里 `-` 和 `_` 混用困惑 | 其实等价 | 生成到 Rust 统一 `_`（`on_request_x`） |
| 只改 Rust 期待热更 UI | UI 没变 | UI 改在 .slint 才有 live-preview；逻辑改要重编 |

## 十五、与 CMX 工作区的呼应

对照本工作区（元数据驱动企业平台，前端以 Web 资产为主）：

1. **Slint 在本仓当下无强对口场景**。横评（`docs/20260920_Rust桌面GUI框架横评.md`）结论：本仓**无嵌入式诉求**，Slint 的杀手锏（下沉 MCU）用不上；面向用户的桌面产品首选 **Tauri 2**（复用 `frontend/` 资产），内部诊断面板选 **egui**。Slint 的 DSL 设计协作、类 Qt 工作流，与 CMX 当前以 Web 为主的形态不重叠。
2. **它的独家价值在「设备端」**：如果 CMX 未来延伸出**工控终端、车间专用设备、仪器面板**这类**嵌入式 UI**，Slint 是**唯一**能从桌面下沉到 MCU 的选项——届时它没有竞品。
3. **双主题纪律一致**：Slint 从 `Palette` 派生颜色、随 style 切明暗，正是 CMX 硬约束 #4 在 DSL 框架里的等价表达（第 9 节）。
4. **许可要留意**：企业内部/桌面走免版税免费；只有「闭源 + 设备发货」才需商业许可——若真做设备端产品，这笔账要提前算（第 12 节）。

> 与本系列的分工：**iced=可演进的自绘桌面产品；egui=最快出活的内部工具；Dioxus=前端背景全 Rust 多端（WebView）；Slint=设计协作 + 嵌入式下沉（唯一到 MCU）**。五者主场清晰，Slint 在 CMX 语境下是「未来若做设备端 UI」的唯一候选。

## 十六、版本与参考资源

**版本基线（2026-09）**：Slint **1.17.x**。1.x 遵循语义化版本、迭代克制，是本系列里**稳定性承诺最强**的之一（对比 iced/Dioxus 的 0.x 破坏性变更）。背后是商业公司 **SixtyFPS GmbH**，有付费支持。

| 资源 | 地址 | 说明 |
|---|---|---|
| 官网 & 文档 | slint.dev · docs.slint.dev | 教程 + `.slint` 语言参考 + Rust API |
| API 文档 | docs.rs/slint | **锁定你的版本看** |
| 在线试玩 | slintpad.com | 浏览器里写 `.slint` 即时预览 |
| 源码 & 示例 | github.com/slint-ui/slint（`examples/`、`demos/`） | 桌面 + MCU 板级示例都有 |
| 许可说明 | slint.dev（licensing） | 三许可细则，选型必读 |
| 工具 | VS Code 扩展「Slint」 | live-preview 即改即见 |

> 学习路径建议：装 VS Code 「Slint」扩展、打开官方 `examples/`，**边改 `.slint` 边看 live-preview**——这是 Slint 最高效的学法（所见即所写）。逻辑侧照本文各节对 Rust API。遇到 API 对不上，认准你锁定版本的 docs.rs。

---

### 一句话收束

> **Slint = 现代 Qt 的 Rust 答卷**：声明式 `.slint` DSL 编译期生成、设计与逻辑物理分离、live-preview 即改即见、多渲染器，且**唯一能 no_std 下沉到单片机**。给「有设计协作、有嵌入式野心、要类 Qt 工作流」的团队；代价是学一门 DSL、许可三选一有决策成本。桌面/Web 免费可商用，只有闭源硬件发货才付费——想清楚你要不要那份「从桌面一直下沉到 MCU」的能力。

> 参考：slint.dev、docs.slint.dev 与 docs.rs/slint、github.com/slint-ui/slint（examples）、slintpad.com。版本以 2026-09 的 1.17.x 线为准；凡涉及具体 API，请以你锁定版本的 docs.rs / 语言参考为准，勿跨版本照抄。