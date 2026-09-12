# 演示数据主数据真源对齐方案（含对抗审查与执行记录）

> 日期：2026-09-12 晚 ｜ 关联：`20260912_cmx-ontology_本体平台演示业务场景与测试数据方案.md`
> 结论先行：本体演示的字典类对象（类型/属性/实例/关系）已全部切换为 **MDM 主数据平台真源**——元数据 deploy 建表、seed 单一真源、漏斗八类拉取、引用列→关系、演示派生属性保留为 SQL 派生/流程属性。

## 一、目标与决策（用户拍板）

1. 主数据已有定义的（供应商/物料/计量单位/币种/付款条件/员工），本体侧不自造字段定义——**以主数据元数据为准**。
2. 主数据缺关系字段 → 补元数据（refDict）+ 补数据关联 + 完善漏斗映射；非引用字段以主数据为准。
3. 用户决策三项：物料改用库内 MAT 码（单据行同步改）；**八类字典全漏斗化**；演示属性"派生+补列"。

## 二、现状结论（执行前核实）

- fico 库 22 张 cm_* 表，7 组跨表引用全可解析；缺口=cm_supplier 后 3 行引用列全空、cm_material 采购/库存单位列未填全、物料码 MAT0001~0010 ≠ 演示自造码（且 cv_po_line.material_code 用的是 GYL 演示码）。
- 硬约束：漏斗 sync 整体覆盖 props → 走漏斗的类型属性必须全部来自 propertyMap。
- spec 两 bug：contractSpendBySupplier groupBy 引用未定义 supplierName；pauseSupplier 写未定义 remark。

## 三、对抗审查（/reviewplanplus 两轮红队）

第一轮：3 致命（Employee 无供给路径 / dctImports 未处置致 Uom 双源 / GYL→MAT 缺映射表）+ 4 严重（姓名三方不一致 / SEED upsert 会冲掉直改 / 清理范围漏 ol_edge·oe_outbox / 演示日 sync 范围未写死）+ derivedLinks 降级建议。全部接受修订。
第二轮复核：第一轮全关闭；新增 3 严重（N1 三参照类型定义须进 objectTypes / N2 代理键→pk JOIN 翻译+验证盲区 / N3 单据行码名同改+单价去对撞）——全部纳入后收敛。**复杂度净减**（derivedLinks 取消、cm_material 直改取消、技能完善后置）。

关键裁决：①GYL→MAT 显式映射表（12 码→9 MAT，码名同改）；②cm_material 引用列只以 seed 为单一真源（砍直改）；③cv_po_line 走 seed 脚本重灌（不直改）；④员工姓名改 MDM 侧（王建国/李晓峰/陈静→采购处 dept 7）；⑤演示日全场只 sync Supplier 一次。

## 四、执行记录（2026-09-12，全部完成）

| 步骤 | 内容 | 结果 |
|---|---|---|
| S0 | id↔code 前置核对（CNY=1/USD=2、EMP0001=1、dept7=采购处、SUP-BAD 非库内行） | ✅ 假设全部成立 |
| S1 | cm_supplier 3 行 UPDATE（事务+快照 bak_cm_supplier_0912） | ✅ 3 行补全 |
| S2 | 元数据补列（cm_material +safety_stock/ref_price）+ employee/material seed 修正 + deploy DCT v3（24 表：material 升级、warehouse/contract 创建）+ SEED 181 行 0 失败 | ✅ |
| S4 | scenario-spec v2：8 类型 MDM 口径（Uom/Currency/PaymentTerm 参照类型入 objectTypes，共享属性 sharedProperty 引用式）、dctImports/objects 段删除、funnelMappings 八类（LEFT JOIN+COALESCE+CASE 中文翻译）、links 68 条（数据驱动 41 + 手工语义 27，代理键逐条 JOIN 翻译）、修 createMaterial status/contractSpendBySupplier groupBy | ✅（baseType 用 double；buyerOf aPk/bPk 曾反置已修正重建） |
| S3/S5 | 本体清理（oo_*/ol_edge/oe_outbox/oe_action_log/oo_quarantine）→ onto_seed 全量 → 八类 sync（Supplier 12/11/1，其余全 0 隔离）→ links 68 全建 → snapshot v11 | ✅ |
| 单据 | seed_po_docs 重灌：10 单 18 行，供应商名/物料码名与主数据严格一致，头金额=行合计，PO-0001/0010 单价去对撞 | ✅ 10/0 |
| S7 | walkthrough 更新（八类漏斗、下钻讲点、函数新期望值、演示日 sync 铁律） | ✅ |

### 验证证据（API 实测）

- 遍历：SUP0001→结算币种=CNY（反向 CNY 11 供应商）；SUP0001→buyerOf 反向=EMP0001 王建国；MAT0001→useUom=pcs 个；CT-2026-001→付款条件=net60/币种=CNY；SUP0001→signContract=CT-2026-001。
- 函数：supplierGrade SUP0001="A"；supplierRiskScore SUP0002=93；materialFullLabel MAT0002="钢材类 / Q235B 热轧钢板 δ10（千克）"；聚合=中信重工 120万/华胜 76万/晨光 58万。
- 属性：SUP0001 MDM 真源字段齐（taxNo/invoiceType=增值税专用发票/paymentTerm/riskLevel + 派生 rating 4.6/onTimeRate 96.5/status 合作中）。
- 幕⑥：submitSupplierReview dryRun 编辑集正确；隔离区 1 条；manifest 9 类型/9 关系（PoHead 仍在）。

## 五、演示日注意事项（新增/变更）

1. **sync 铁律**：全场只允许 `POST /funnel/sync/Supplier` 一次（幕⑤）；其余八类不再 sync、不重跑 onto_seed。
2. 幕②讲点改为"八类全漏斗 + 隔离区"（import/dct 节拍已移除）。
3. 幕④函数演示值：materialFullLabel 用 MAT0002；聚合组名为供应商显示名（中信重工/华胜/晨光）。
4. 幕⑤新铸号（CR…033）引用列为空 → 结算币种/采购对接无新边属正常；页面补全引用列后重跑 links 段即可。
5. 本体 Supplier 显示名=MDM 种子名（中信重工等），单据页 supplier_name 已同步对齐。
6. GYL→MAT 物料对照表见 walkthrough 与 seed_po_docs.py 注释。

## 六、遗留（演示后）

- S6 技能完善：mdm-master-data-onboarding 补 refDict/数据关联章节；cmx-onto-toolkit 补 derivedLinks 能力与"漏斗覆盖 props"坑表。
- meta-enricher 富化已在字段定义中体现（edit/display），如需全量跑一遍可后置。
- fico 回滚备份：bak_cm_supplier_0912（3 行旧值）。
