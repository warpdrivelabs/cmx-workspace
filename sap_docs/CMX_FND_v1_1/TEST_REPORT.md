# 本次实际验证报告

日期：2026-09-14。Python：3.13.5。

|项目|实际结果|不应被解释为|
|---|---|---|
|SAP对象源码/定义读取|63个成功；2个函数只读研究|63张完整表DDL或者SAP业务运行通过|
|SAP配置取样|FINSC_LD_CMP 3行且hasMore=true；FMLC_TOGGLE 0行|完整公司账本清单、已启用UPA|
|独立规则基准|72条 unittest，72通过|SAP对拍、ABAP Unit或数据库事务通过|
|请求/响应JSON Schema|2份schema与2份示例校验通过|CMX已有这些HTTP端点|
|本包JSON文件|12份均可解析|已导入CMX元数据中心|
|PostgreSQL DDL|生成58张表；未执行|数据库迁移、FK、RLS、触发器和锁已验证|
|PostgreSQL并发|NOT_RUN|内存门版本测试等于真实并发测试|
|Rust/CMX源码接入|NOT_RUN|可直接安装的CMX生产插件|
|SAP业务执行和写入|未执行|已验证目标系统业务结果|

本地测试日志：tests/local_test_output.txt。待执行数据库/并发/SAP对拍：tests/目录。

已核实的示例结果：WERKS1100→BWKEY V100→BUKRS1000；5 BOX→60 EA；2026-09-14在0L/K4为2026/9，在2L/A4为2026/6；CNY试算6000.00及6300.00；两套账本共同引用一次基本数量。数据均为人工测试数据。

限制：当前容器无PostgreSQL及Rust工具链，依赖下载因网络解析失败，未将未运行的项目伪装成通过。SQL经过设计检查，不等同实际数据库解析/运行验证。
