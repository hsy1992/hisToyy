# 销货单状态字段历史对比

日期：2026-10-27。用户反馈：销售单页面出现 `[object Object]`。

## 核查范围与结论

“第一版”暂取 Git 中最早包含本应用 domain.py 的 dac4d1c（2026-10-18），并复核 e8a10db（2026-10-22，API 审批改造前）。使用同一模拟单据调用各版本 build_payload，比较实际构造的主明细字段，不依赖注释描述。

已确认当前主表和明细表 isSaleOut=0 与本地留存的枚举脚本不匹配。脚本中出库状态 idEnum=40：15=已出库、305=未出库，无 ID=0。若实际账套字典一致，未出库应使用305；不能把枚举Code='00'转换成整数0作为ID保存。

这是一处已验证的载荷取值差异，尚不能认定它已经解释页面上的 `[object Object]`。缺少异常单据SA编号、页面具体字段和响应数据，未能复现T+前端显示。实际账套连接尝试失败（OperationalError，SQLSTATE 08S01），未执行数据库修改。

## 关键字段比较

| 表/字段 | 最早版 dac4d1c | API改造前 e8a10db | 当前源码 |
|---|---|---|---|
| SA_SaleDelivery.voucherState | 189 | 189 | 181 |
| SA_SaleDelivery.auditor / auditorid | 范立志 / 51 | 范立志 / 51 | 不插入 |
| SA_SaleDelivery.auditeddate | 源日期 | 源日期 | 不插入 |
| SA_SaleDelivery.AuditedTime | 不插入 | 创建时间 | 不插入 |
| SA_SaleDelivery.isSaleOut | 15 | 15 | 0 |
| SA_SaleDelivery_b.isSaleOut | 15 | 15 | 0 |
| SA_SaleDelivery_b.saleOutQuantity | 不插入 | 源数量 | 0 |
| SA_SaleDelivery.isAutoGenerateSaleOut / IsAutoSaleOut | 1 / 1 | 1 / 1 | 1 / 1 |
| SA_SaleDelivery.isCancel | 不插入 | 428 | 428 |
| SA_SaleDelivery.isNoArapBookkeeping | 不插入 | 0 | 0 |
| ARAP_Detail | 无构造函数 | 无构造函数 | 已恢复直接插入 |

ARAP_Detail在后续3f1bf67版本已有构造函数，auditFlag/auditBussinessFlag为1/1；当前改为0/0，BookFlag=2212、isArFlag=1、flag=-1不变。最早两版不能被描述为“同样插入应收，只是审核值不同”。

## 本地字典证据

来源：C:/Users/Administrator/Desktop/医药/script_enum_utf8.sql（仅读取，没有执行INSERT脚本）。

| ID | 名称 | Code | idEnum | 源文件行号 |
|---|---|---|---|---|
| 15 | 已出库 | 01 | 40 | 17 |
| 305 | 未出库 | 00 | 40 | 295 |
| 181 | 未审 | 00 | 88 | 175 |
| 189 | 生效 | 01 | 88 | 182 |
| 428 | 未结清 | NoSettle | 16 | 413 |
| 2212 | 普通应收 | 00 | 501 | 2107 |
| 56134 | 未发货 | 00 | 55906 | 3582 |

本地脚本不等于实际发生异常的账套字典；应使用配套check_sales_status_20261027.sql核实。ARAP的auditFlag/auditBussinessFlag不按eap_EnumItem全局ID解释；其0/1业务行为仍需用同账套正常未审单据比较。

## 校验缺口与下一步

现有测试断言主明细isSaleOut=0；preflight只校验invoiceType、reciveType、isCancel的枚举，未校验isSaleOut/voucherState，所以测试通过不能证明界面状态可解析。

1. 在异常账套执行配套只读SQL，填异常SA编号和一张正常单据编号，核实主明细出库状态对应枚举。
2. 维持未审核要求：voucherState=181、不写审核人/时间；若实际字典一致，主明细未出库值使用305，saleOutQuantity=0。
3. 同账套通过T+界面保存一张正常未审单据，对比ARAP是否生成、审核标志、自动出库配置。不能直接认定未审核单据应与旧生效单据全部字段一致。
4. 保存异常页面请求的脱敏响应或具体状态控件信息，确认修正单字段后原来的显示异常是否消失，再认定根因。

本次只排查并生成对比记录与只读SQL，没有改应用状态值、没有回填历史单据、没有重新打包。
