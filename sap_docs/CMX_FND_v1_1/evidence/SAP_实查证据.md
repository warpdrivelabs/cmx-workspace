# SAP 实查证据与 V1.0 修正清单



本文件是2026-09-14通过abap-mcp对S4F/810质量参考客户端的实际只读观察摘要。E编号是本设计包内部证据编号，不是SAP Note编号。

成功读取63个对象定义/源码，包含2个函数；另预览FINSC_LD_CMP的3行（仍有更多行），以及返回0行的FMLC_TOGGLE。完整对象名见sap_objects.json。未执行SAP业务逻辑、未修改SAP。

未确认S4CORE版本或UPA启用状态；不能把含有UPA代码与客户已经启用混同。CVERS和DD03L的SQL查询被策略拒绝，未绕过限制。

本包不包含完整SAP私有源码，不包含账户名、口令、服务器地址。以下提炼事实并独立设计CMX实现。



## E01 工厂→估值范围→公司

实际来源：`T001W、T001K、T001、SI_T001K`。

**观察事实：** T001W键MANDT/WERKS；BWKEY外键到T001K。T001K键MANDT/BWKEY，BUKRS引用T001。

**CMX实施变化：** 按BWKEY连接，不能假定WERKS=BWKEY=BUKRS；公司的权威归属不在一个随意填写的工厂BUKRS字段。



## E02 采购与销售分配的不同粒度

实际来源：`T024E、T024W、TVKO/SI_TVKO、TVTA、TVKWZ`。

**观察事实：** T024W键MANDT/WERKS/EKORG；TVTA含VKORG/VTWEG/SPART；TVKWZ含VKORG/VTWEG/WERKS而不含SPART。

**CMX实施变化：** 分别校验销售范围与供货工厂授权；采购组织无公司限制不代表全工厂许可。



## E03 控制范围与利润中心公司分配

实际来源：`TKA02、CEPC_BUKRS`。

**观察事实：** TKA02主键为MANDT/BUKRS/GSBER，KOKRS为关联字段。CEPC_BUKRS主键包含MANDT/KOKRS/PRCTR/BUKRS。

**CMX实施变化：** 保留GSBER；拒绝有歧义的公司控制范围；利润中心不能硬编码为单一公司。



## E04 BP与客商的身份不相等

实际来源：`CVI_CUST_LINK、CVI_VEND_LINK、BUT100`。

**观察事实：** CVI映射键为CLIENT/PARTNER_GUID，业务字段CUSTOMER或VENDOR；BUT100键含MANDT/PARTNER/RLTYP/DFVAL。

**CMX实施变化：** 创建稳定GUID映射；不要按BP编码等于客商编号推导关系；保留CLIENT与MANDT源列区别。



## E05 主数据日期粒度不能统一成DATE

实际来源：`CSKS、BUS100_NCHR、BU_ROLE_VALID_FROM/TO`。

**观察事实：** CSKS键含DATBI，并有DATAB。BP角色日期经数据元素核实为TZNTSTMPS域、DEC(15,0)时间戳。

**CMX实施变化：** 成本中心采用日期区间；BP角色按时间戳处理。源端上界包含性须按对象核验，不能统一加一天。



## E06 统驭科目是完整的关系校验

实际来源：`KNB1/SI_KNB1、LFB1/SI_LFB1、SKB1、SKA1`。

**观察事实：** 客商公司视图AKONT关联公司SKB1；SKB1科目关联SKA1时科目表由T001-KTOPL提供。SKB1含MITKZ/XOPVW/XINTB/XSPEB等控制。

**CMX实施变化：** AKONT不只是科目选择器；验证公司扩展、科目表、D/K统驭类型和冻结状态；核算敏感字段变更走迁移。



## E07 期间开放变式不是公司代码

实际来源：`T001B、SI_T001、FINSC_LD_CMP；配置表抽样`。

**观察事实：** T001B名为BUKRS的列实际使用OPVAR数据元素并关联T010O；FINSC_LD_CMP样本公司1300的OPVAR是1310。

**CMX实施变化：** 内核使用明确的posting_period_variant；SAP兼容层再映射到T001B-BUKRS。



## E08 财年和期间由边界表解析

实际来源：`DATE_TO_PERIOD_CONVERT（ADAT）、T009、T009B`。

**观察事实：** 函数按XKALE/XJABH和T009B边界处理；T009B键PERIV/BDATJ/BUMON/BUTAG，结果POPER及RELJR。

**CMX实施变化：** 发布时编译具体年度日期区间，运行时按账本PERIV和实际过账日期查期间，不能按月份取值。



## E09 开放期间的头检查、行检查和授权

实际来源：`FI_PERIOD_CHECK（FACS）、T001B`。

**观察事实：** 源码先检查+头级记录；明细按科目类型与账号范围。明细无匹配不必然失败。间隔1/2和间隔1授权组有不同作用；COFI另有间隔3处理。

**CMX实施变化：** 先通用门，再适用的明细门；保留授权；CMX发布时拒绝重叠区间，不复制源程序依赖首命中顺序的行为。



## E10 UPA跨账本期间分支

实际来源：`FI_PERIOD_CHECK（FACS）`。

**观察事实：** 源码存在fins_parallel_accounting_rs分支，遍历相关账本，以过账日期和账本年度方案重新确定期间；含增强和特殊分支。

**CMX实施变化：** CMX必须显式携带postingDate并逐账本解析；本次未执行该分支，也未核验客户BAdI实现。



## E11 账本币种槽与功能币类型

实际来源：`FINSC_LEDGER、FINSC_LD_CMP、FINSC_CURTYPE；FINSC_LD_CMP抽样`。

**观察事实：** 账本公司配置含PERIV/OPVAR/ACC_PRINCIPLE及CURTPH/K/O/V/B..G槽；FUNCTIONAL_CURRENCY引用币种类型；样本值10不是ISO币种。

**CMX实施变化：** 槽位转币种角色行，保留内外币种类型；不可直接把功能币字段当作CNY/USD。



## E12 物流币种映射的内外类型区别

实际来源：`FMLV_CURTP_ML、FMLT_CURTP_ML、FINSC_CURTYPE`。

**观察事实：** CDS连接FMLT_CURTP_ML、FINSC_LEDGER、FINSC_CURTYPE及FMLC_TOGGLE，按开关选择返回类型；FMLT_CURTP_ML键包含RBUKRS/CURTP/RLDNR。

**CMX实施变化：** 用公司＋账本＋外部币种类型定位映射，不能在整个公司范围按10/30去重。



## E13 物料价格不是一个STPRS字段

实际来源：`FMLT_PRICE及其FMLS_PRICE_*包含结构`。

**观察事实：** 价格键展开为MANDT/KALNR/RLDNR/EXT_CURTYPE/PRICE_TYPE/PRICE_SUBTYPE/DATE_FROM；有DATE_TO、PRICE、WAERS、PEINH、VALUM、PRICE_NUMERATOR/DENOMINATOR及特殊库存引用。

**CMX实施变化：** 独立价值对象与版本化价格；按账本、币种角色、价格类型和日期解析；字段存在不证明所有价格类型的读写优先级已验证。



## E14 历史价格键与功能标识不同

实际来源：`FMLT_PRICE_HIST、FMLS_PRICE_HIST_KEY、FMLS_PRICE_HIST_IDENTIFIER`。

**观察事实：** 历史表物理键是MANDT/PRICE_HISTORY_ID，功能标识另含KALNR/RLDNR/EXT_CURTYPE/价格类型/DATE_FROM/TIME_STAMP。

**CMX实施变化：** 不能照当前价格自然键设计一个会覆盖历史的history表。



## E15 DDIC包含、域与替代对象

实际来源：`MBEW、MARC、MARA、MARM/EMARM、MATNR域`。

**观察事实：** MBEW声明mbv_mbew替代对象；MARC声明nsdm_e_marc；MATNR域为CHAR40、MATN1转换例程；MARM换算字段UMREZ/UMREN在EMARM内。

**CMX实施变化：** 元数据提取递归解析INCLUDE；区分真实key与foreignKey.keyType注解；不凭表名推断持久化来源；不将物料号强制转整数或截18位。



## E16 币种参考数据有非客户端对象

实际来源：`TCURX、TCURR、TCURF、GDATU_INV域`。

**观察事实：** TCURX主键CURRKEY，不含MANDT；TCURR/TCURF含GDATU倒置日期，GDATU_INV域为NUMC8、INVDT转换例程。

**CMX实施变化：** 显式源语义适配，不能统一把日期NUMC作为日期或把UKURS直接当标准倍率；本轮未实现完整原始SAP汇率解码器。



## 实际配置抽样（不是产品初始配置）

|客户端|账本|公司|币种类型H/K|年度方案|开放期间变式|准则|功能币类型|

|---|---|---|---|---|---|---|---|

|810|0C|0001|10 / 空|K4|1310|空|空|

|810|0C|1300|10 / 30|K4|1310|CNAP|10|

|810|0C|1310|10 / 30|K4|1310|CNAP|10|



这些行只证明对应配置存在；不能推出全部账本清单、其生产正确性、国家适用性或ML/UPA全部激活状态。FMLC_TOGGLE返回空集也不等同完成开关框架的完整诊断。

## 尚需验证但本次不冒充完成的内容

S4CORE/SP级别；客户增强实际执行；UPA开关端到端；各价格类型的标准读取/回退/更新调用链；原始SAP汇率与金额缩放；全部DDIC包含、域固定值、搜索帮助、转换例程；CMX代码仓库crate API；真实PostgreSQL执行、权限隔离、并发和SAP差分对拍。