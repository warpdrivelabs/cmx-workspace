# CMX ERP Foundation V1.1 — SAP实查与实施包

**这是一份可开始编码、迁移评审与本地验收的实施包，不是已经安装的CMX插件。**

## 建议阅读顺序

1. `evidence/SAP_实查证据.md`：63个SAP对象只读核查后得到的16项关键事实与修正。
2. `docs/02_实施详设.md`：组织、主数据、时间和估值的完整实施设计、写入边界、事务、服务和任务拆分。
3. `docs/03_physical_table_catalog.json` 与 `db/001_foundation.sql`：58张表（含client_scope）的键、字段、约束与隔离设计。
4. `contracts/`、`examples/`：拟新增命令目录、JSON Schema、完整演示请求/响应。
5. `reference/` 与 `TEST_REPORT.md`：可运行规则基准、72条测试及实际执行状态。

## 文件定位

- `db/001_foundation.sql`：首次PostgreSQL建模迁移，含配置发布保护和RLS策略。
- `db/003_locking.sql`：主数据历史写保护、期间门版本、库存动作提交前的多账本FI/MM共享锁。
- `db/002_demo_seed.sql`：仅组织/日历/账本配置与门的人工种子，不包含全量主数据；必须显式授权并在隔离测试库执行。
- `db/004_read_paths.sql`：参数化组织关联和价格解析查询。
- `reference/foundation.py`：Python标准库独立规则规格；不是CMX生产后端，未复制SAP私有源代码。
- `reference/demo_fixture.py`：人工主数据、配置、价格；与真实S4F配置无关。
- `tests/postgres_acceptance.sql`、`tests/并发与集成验收.md`：尚未执行的PG/CMX/SAP对拍验收。
- `evidence/sap_objects.json`：对象类型、名称、ADT定位信息；不是SAP全量DDIC导出。
- `evidence/research_scope.json`：连接范围、取样、访问失败与未验证项，不含凭证或基础设施地址。

## 复现已通过的本地规则测试

需要Python 3.10或以上，不依赖第三方包：

```bash
cd reference
python -m unittest -v
```

演示输入输出见examples。这里的`Scope`代表生产中由认证中间件注入的可信范围；不要从前端JSON创建任意租户Scope。`contextHash`只是内容摘要，不是授权令牌。

两份JSON Schema及示例在本次环境通过jsonschema校验；规则测试在标准库环境执行72/72通过。生产语言仍应采用CMX既有Rust技术栈，通过实际仓库端口实现；本包没有声称Rust适配已编译。

## PostgreSQL试装路径（尚未执行）

针对新的、可丢弃的测试数据库，先审阅迁移、扩展、RLS及权限分配。不要在现有生产schema直接运行。

```bash
psql "$TEST_DATABASE_URL" -v ON_ERROR_STOP=1 -f db/001_foundation.sql
psql "$TEST_DATABASE_URL" -v ON_ERROR_STOP=1 -f db/003_locking.sql
PGOPTIONS='-c app.allow_demo_seed=yes' psql "$TEST_DATABASE_URL" -v ON_ERROR_STOP=1 -f db/002_demo_seed.sql
psql "$TEST_DATABASE_URL" -v ON_ERROR_STOP=1 -f tests/postgres_acceptance.sql
```

`001`故意不以IF NOT EXISTS吞掉同名表：已有库应通过CMX迁移版本和结构差异工具管理。脚本不提供生产角色GRANT。应用身份不能为superuser或BYPASSRLS；不可信插件不能拿到任意SQL连接。仅设置app.tenant_id/app.mandt的GUC不是对任意SQL攻击者的安全边界。

`lock_inventory_context`必须在最终业务写入的同一数据库事务内调用。单独自动提交锁函数，之后另开事务过账，不具备一致性保证。

回退策略：隔离新库可销毁重建；生产已使用后不能回滚发布去覆盖账务。正式发布保留历史，通过新发布、受控主数据修订、业务冲销或迁移纠正。本文不提供自动删除生产schema的脚本。

## 范围限制

S4CORE/SP、UPA实际启用、全部SAP价格类型的标准读写优先级与原始汇率/金额换算尚未确认。63个对象定义读成功不等于完成这些运行验证。SAP参考环境不是你们已批准的公司模型。

58张表对应本期组织/主数据/日历/账本/价格上下文链及治理底座，不包含整个ERP，也不宣称已实现资产、银行、税务、项目等每一种主数据的完整维护应用。原V1.0更广产品范围继续保留；V1.1纠正冲突处并明确本次可执行范围。

当前环境没有PostgreSQL服务端或Rust工具链；相关依赖下载因网络解析失败。数据库迁移、真实并发、权限隔离、CMX端口和SAP对拍明确为NOT_RUN，不能把本地规则测试计入它们的通过数量。
