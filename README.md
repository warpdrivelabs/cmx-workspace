# CMX Presentation — 元数据驱动平台前端

> 元数据驱动的企业级全栈平台前端：门户运行时 + 可视化设计器 + 数据层 Web Components。
> 与后端 [cmx-container](https://github.com/) 配套。

![License](https://img.shields.io/badge/license-Apache--2.0-blue)

## 这是什么

**presentation** 是 npm workspace monorepo：

- **CMXPortalManager**（门户运行时，路由 `/portal/`）
- **CMXHTMLDesigner**（可视化设计器，路由 `/html/`）
- **packages/cmx-data-comp**（数据层 Web Components：主从表格、组合框、树表、公式编辑器、单据/字典/报表组件…）
- **packages/cmx-ui5-runtime**（共享 UI5/Tabler 运行时，路由 `/shared/`）

后端 **cmx-container**（Rust 多 crate workspace）提供元数据驱动的单据（DOC）/ 数据字典（DCT）/ 报表（RPT）/ 流程（FLOW）存储与服务、异步任务中心、插件系统。

## 核心特性

- **元数据驱动**：换一份定义 JSON 即得一套 L1..Ln 单据的装载/回存/建表，零专属代码。
- **数据层组件**：主从协调（CmxMasterSlave）、列模型（CmxColumnModel）、数据集（CmxDataSet）、增量 changeset。
- **报表**：可视化设计器 + 应用器、自定义取数函数（QM/QC）、浮动行列动态展开、协同编辑。
- **无框架 Web Components**：组件层不依赖 React/Vue/Angular，可嵌入任意宿主。

## 快速开始

### 依赖
- Node + npm、（配合后端）Rust + PostgreSQL

### 构建
```bash
npm install
npm run build          # 构建各子项目（portal / designer / 共享运行时）
```

### 测试
```bash
npm test               # vitest
npm run lint
```

前后端一键起、同源托管等见后端 cmx-container 的 README。

## 架构

```
presentation (前端 monorepo)              cmx-container (后端 Rust workspace)
├─ CMXPortalManager   /portal/            ├─ crates/web/web-server        HTTP 入口
├─ CMXHTMLDesigner    /html/              ├─ crates/libs/cmx-biz          单据/字典业务
├─ packages/cmx-data-comp   数据层组件     ├─ crates/libs/cmx-rpt/*        报表
└─ packages/cmx-ui5-runtime /shared/      ├─ crates/libs/cmx-flow/*       流程引擎
                                          ├─ crates/libs/cmx-job/*        异步任务中心
   构建产物 dist/ ← web-server 同源托管 →  └─ crates/libs/cmx-*            字典/门户/插件…
```

## 第三方与商业依赖（部署方必读）

本项目**核心**采用 Apache-2.0，但部分**增强组件**目前依赖商业授权库。开源产物**不打包**这些商业包；使用相关功能需自备合法授权：

| 组件 | 用途 | 授权 | 状态 |
|------|------|------|------|
| `@mescius/spread-sheets`·`spread-excelio`（SpreadJS） | 报表可视化设计器/应用器的电子表格引擎 | 商业 | 隔离在 `packages/cmx-data-comp/src/components/spreadjs/` 单一 wrapper 之后；替换/可选化方案评估中 |
| `@infragistics/*`（Ignite UI） | 部分表格/仪表组件 | 商业 | 使用面盘点中；非报表主链路 |

> 报表设计器的电子表格引擎替换方案（含开源引擎评估）见 `docs/`。未持有上述商业授权时，相关设计器功能不可用，但不影响其余组件与后端。

## 参与贡献
见 [CONTRIBUTING.md](CONTRIBUTING.md)。安全问题请见 [SECURITY.md](SECURITY.md)（**勿开公开 Issue**）。

## 许可证
[Apache-2.0](LICENSE)。
