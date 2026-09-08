---
name: cmx-flow-toolkit
description: 当用户要求为 cmx-flowengine 创建/定义/部署新审批流程（按需求生成 BPMN 并发布）、重建/恢复/导出/留档流程测试数据、把流程实例转为 SQL、重放 transcript 流水生成数据快照、复现某轮流程测试的库内数据、给待办中心/设计工作台造流程演示数据，或提到"流程定义""流程测试数据""数据转 SQL""flow-test-data"时使用。
---

# cmx-flow-toolkit · 流程定义创建 + 测试数据复原

## 概述

cmx-flowengine 的双模式工具箱：**模式A 按需求创建/部署流程定义**（spec JSON → 语义 BPMN → validate/draft/publish → 冒烟验证）；**模式B 保真复原测试数据**（流水/报告/BPMN 重放 → 可执行 SQL）。核心原则：A 生成的定义可被 B 纳入下一轮复原，B 复原的绑定/身份供 A 的子流程路由使用——两模式互通。

基准（可对照）：examples/ 下 spec 与 manifest 样例；`cmx-flowengine/docs/flow-test-data-20260816.sql`（92 实例 / 23 定义 / 683 INSERT，空库零错误）。产物不可跨脚本版本 byte 级复现，"确定性"仅指同版本脚本 + 同参数。

## 意图分诊

| 用户要… | 走 |
|---|---|
| 新建/定义/设计一个审批流程、生成 BPMN、部署发布流程定义 | **模式A** |
| 复原/导出/留档某轮测试数据、转 SQL、造演示数据快照 | **模式B** |
| 改一个已有流程（调链路/换审批人/加节点） | **模式A**：改 spec（或既有 BPMN）再 publish，版本 +1 热装载无需重启 |
| 定义完还要跑通验证 | A →（可选）B 灌身份/绑定后 A 冒烟推进 |

## 模式A · 定义创建

```bash
# 相对路径按 cwd 解析。生成物默认 <key>.bpmn 落在 spec 同目录
python3 .agents/skills/cmx-flow-toolkit/scripts/create_flow_def.py \
  --spec <spec.json> [--out <key>.bpmn] \
  [--deploy] [--smoke] [--server http://127.0.0.1:8091] [--api-key <key>]
```

- spec 结构与完整语法（节点/候选人七类/网关条件/会签/子流程映射/定时器/部署契约/鉴权）→ **`references/bpmn-def-guide.md`**（重参考，写 spec 前必读）。
- 可运行样例：`def-spec-expense.json`（网关+组织路由子流程）、`def-spec-contract.json`（并行+会签+终止终点）、`def-spec-escalation.json`（定时器升级/催办+决策表+消息等待）。
- 关键契约（细节见参考）：validate 软失败要查 `data.valid`；办理类 E2E 需 jwt 模式 + 委托令牌（带 `exp`）；语义 BPMN 无 DI，设计器自动布局。
- E2E 实测链（2026-08-18）：spec → publish v1 热装载 → 冒烟断言首节点 → 办结过网关 → callActivity 按组织绑定路由到 fin_review_hq 子流程，父子状态全部正确。
- 生成物落盘：`cmx-flowengine/docs/<测试集>/defs/<key>.bpmn` + spec 同目录留存。

## 模式B · 数据复原

输入相对路径按 `--repo` 解析（`--out` 按 cwd）：

```bash
python3 .agents/skills/cmx-flow-toolkit/scripts/rebuild_flow_testdata.py \
  --repo <cmx-flowengine 绝对路径> \
  --transcript docs/full-test/logs/transcript.log \
  --transcript docs/full-test/logs/sub-transcript.log \
  --def-dir docs/biz-test --def-dir docs/full-test/defs --def-dir docs/full-test/defs/subflow \
  --manifest <manifest.json> \
  --iam-db cmxlocal --flow-db cmx_fico \
  --out <产物.sql>
# 可选: --handcrafted <手建模块.py>   ← 同轮次混有无流水的测试段时加（与流水重放段叠加输出）
# 可选: --base-ts <ISO 时刻>（缺省自动取流水内最早真实时间戳-10s；无时间戳必须显式给）
```

- 数据源清单与工作流：探库定路线（明确要求重建可跳）→ DDL 对账 → 写 manifest（新轮次存 `cmx-flowengine/docs/full-test/data/rebuild-<日期>.json`）→ 无流水轮次写手建模块（仿 `examples/biztest_handcrafted.py`）→ 跑脚本看 stats（`unparsed_blocks`/`skipped_no_view` > 0 先查丢没丢数据）→ 验证。
- DDL 真源：运行库 `cmx-flowengine/crates/{cmx-flow-store-pg/src/ddl.rs, cmx-flow-def/src/store.rs, cmx-flow-app/src/biz_link.rs}`；IAM 库 `cmx-container/docs/sql/v2/platform/migrations/20260819_001_baseline.up.sql`（历史迁移 20260615_002_iam_tables / 20260720_001_cmx_flow_engine 已并入该基线）。
- manifest 全字段：`iam`（orgs/roles/positions/users/user_roles/user_positions）、`subflow_bindings`（模式A 的 calledKey 路由也用它）、`form_bindings`、`def_versions`、`def_notes`、`called_targets`、`seed_time`、`publish_time`（后两者须是合法 PG 时间字面量）。
- 保真度分级（产物头部自动声明）：真实值 = 实例/任务/抄送 id、状态、businessKey、办理人、候选人、变量、台账 createdAt、任务 createdAt；重建值 = 令牌 id（uuid5，开放任务与令牌严格挂接有自检，已办任务 token_id 悬挂是引擎真实行为）、updated_at/completed_at/HI 时长/意见时间。台账 task_id 为启发式绑定（JUMP/URGE 等走兜底）。
- **验证五查**（不全绿不交付）：空库 `psql -v ON_ERROR_STOP=1 -f` EXIT=0 零 ERROR；计数对账（报告是累计数、流水重放是本轮数，产物头部有覆盖度声明）；开放任务令牌孤儿=0；子实例孤儿=0 且终态实例数=hi_instance 数；`duration_ms < 0` 计数为 0 + 关键用户待办数/绑定三层解析（精确/继承/兜底）抽检。

## 常见坑

| 坑 | 正解 |
|---|---|
| 以为库里还有测试数据 | 先探库；空/不可达 → 模式B。用户已明确要重建可跳过探库 |
| psql 验证命令接 `\| head` | SIGPIPE 截断执行却看似成功；一律 `> log 2>&1` 后看退出码 |
| 目标库不存在 / DROP 卡占用 | 先 CREATE DATABASE；重跑 `DROP DATABASE ... WITH (FORCE)` |
| 台账只有三种 kind | 实际还有 REJECT/WITHDRAW/JUMP/URGE；task_id NOT NULL 脚本已兜底 |
| `GET /cc` 列表没有 toUserId | 从查询参数 `user=` 补（脚本已处理） |
| 负向 BPMN（bad_nostart）混进定义 | 脚本按"发布过/被引用/绑定目标"过滤，缺 BPMN 会告警 |
| 报告实例数多于产物 | 报告是累计数；产物头部声明覆盖度，不硬凑数 |
| 向共享 IAM 库执行 | `uk_cmx_user_username` 撞已有用户；清理段 TRUNCATE 对共享库危险，按 users 清单 DELETE |
| 条件里裸写 `>` / `&&`（模式A 手改 BPMN） | spec 写原文由脚本转义；手改必须 `&gt;` `&amp;&amp;` |
| 网关缺省边写在边上 | default 是网关属性指向边 id；spec 用 `defaultTo` |
| 委托令牌缺 `exp` / off 模式办理 | 办理类 E2E 用 jwt 模式 + 带 exp 的 X-Delegated-User-Token；T0b 校验办理人 |
| 本机 8091 被常驻服务占用 | E2E 起服用 `FLOW_PORT=8099` 旁路；**勿 pkill 他人服务** |

## 交付约定

- 模式A：BPMN + spec 存 `cmx-flowengine/docs/<测试集>/defs/`；部署/冒烟结果如实汇报（版本号、实例 id、断言）。
- 模式B：单 SQL 文件存 `cmx-flowengine/docs/flow-test-data-<日期>.sql`，头部含保真度/覆盖度/清理指引（文末注释态清理段）。
- 任何模式完成后**不落 git 提交**——按仓库规则等用户明确指令。
