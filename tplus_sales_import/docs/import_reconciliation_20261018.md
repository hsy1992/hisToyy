# 2026-10-18 销货单导入核对报告

账套：UFDATA_999_1015；任务：20261018_122910_2020f552。本次核对只读，没有修改数据库。

## 结论

本次新增5166张表头、7156条明细，原始XLS与任务保存的输入一致。按当前确认规则重建预期数据，与数据库逐字段比较（排除实际创建/更新时间），未发现差异。此结论不代表与T+原导入流程产生的所有系统字段完全相同，也未验证T+界面及后续业务操作。

## 全量核对

| 项目 | 结果 |
|---|---|
| 新增表头/明细 | 5166 / 7156 |
| 重复跳过 | 77单 / 373行 |
| 校验失败 | 40行，客户编码为空或不存在 |
| 新增编号 | SA2026101200078 至 SA2026101205243，5166个连续编号 |
| 源单号重复检查 | 本日目标销货单未发现重复ExternalCode |
| 主从关联、明细数、客户、存货、单位、仓库、项目、业务类型 | 与当前规则一致 |
| 表头金额与明细合计 | 全部核对相符 |
| 本次普通销售/销售退货 | 4781 / 385单 |
| 本次税率 | 7156条均为0.13，符合对应客户档案 |
| 零数量明细 | 2条，已按规则保留 |

| 金额 | 原始数据按当前规则计算 | 数据库 |
|---|---:|---:|
| 含税金额 | 555285.56 | 555285.56 |
| 未税金额 | 491370.78 | 491370.78 |
| 税额 | 63914.78 | 63914.78 |

## 历史373条明细与当前计算规则的差异

匹配方法：原始销售标识与历史明细priuserdefnvc3对应。本次对这77张已有单据执行跳过，没有用当前规则覆盖旧金额。以下差异统计不相互排斥。

| 字段 | 差异行数 | 历史值减当前规则合计 | 单行最大绝对差 |
|---|---:|---:|---:|
| origdiscountamount | 223 | 2.49000000000000 | 0.02000000000000 |
| origtax | 172 | -1.72000000000000 | 0.01000000000000 |
| origtaxamount | 77 | 0.77000000000000 | 0.01000000000000 |

例如源含税金额90.515，历史值90.52，当前向零截断为90.51；源含税金额4368.000，历史未税3865.49/税502.51，当前未税3865.48/税502.52。新数据采用用户确认的十进制向零截断，因此不应宣称与历史金额计算完全一致。

## 历史样本快照与当前已有记录

匹配到原sa_d.csv的77张表头（218列）及sa_d1.csv的373条明细（207列）。表头除isCarriedForwardOut、origts外，其余字段与快照一致；明细除origts外，其余字段与快照一致。77张表头isCarriedForwardOut在CSV快照为0、当前为1。仅凭本次检查无法确定该差异发生的时间和原因，不能归因于本次导入。

## 新旧记录的日期与系统字段差异

制单日期madedate：历史77单为2026-10-13，新单为2026-10-12，符合使用单据日期的最新约定。单据日期、审核日期均为2026-10-12。审核状态189、自动出库标记1、不自动生成发票标记0与历史样本相同。

以下字段在历史记录中有值，而本次新增记录全部为NULL。成本、毛利、出库数量及单据关联不能直接复制其他单据的历史值；是否需要由T+补全需结合实际业务验证。普通标记的NULL也不能直接视为与0或1等价。

### 表头

| 字段 | 历史非空数量（共77） | 历史值示例 | 新记录 |
|---|---:|---|---|
| iscounteractdelivery | 77 | 0 | NULL |
| discountamount | 77 | 0E-14 | NULL |
| discountrate | 77 | 1.00000000000000 | NULL |
| address | 77 |  | NULL |
| linkman | 77 |  | NULL |
| ispricetrace | 77 | 0 | NULL |
| origsettleamount | 77 | 0E-14 | NULL |
| settleamount | 77 | 0E-14 | NULL |
| contactphone | 77 |  | NULL |
| isbeforesysteminuse | 77 | 0 | NULL |
| iscarriedforwardout | 77 | 1 | NULL |
| iscarriedforwardin | 77 | 0 | NULL |
| ismodifiedcode | 77 | 0 | NULL |
| updatedby | 77 | 15046102049 | NULL |
| pubuserdefnvc1 | 77 |  | NULL |
| pubuserdefnvc2 | 77 |  | NULL |
| isnoarapbookkeeping | 77 | 0 | NULL |
| origprereceiveamount | 77 | 0E-14 | NULL |
| prereceiveamount | 77 | 0E-14 | NULL |
| originvoicetaxamount | 77 | 0E-14 | NULL |
| thisbalanceintegral | 77 | 0E-14 | NULL |
| printcount | 77 | 0 | NULL |
| isseparatebywarehouse | 77 | 0 | NULL |
| allowances | 77 | 0E-14 | NULL |
| origallowances | 77 | 0E-14 | NULL |
| datasource | 77 | 2497 | NULL |
| invoicetype | 77 | 281 | NULL |
| iscancel | 77 | 428 | NULL |
| issaleout | 77 | 15 | NULL |
| recivetype | 77 | 7 | NULL |
| saleinvoiceid | 77 | 281 | NULL |
| saleinvoicemedia | 77 | 51014 | NULL |
| isautowarehouse | 77 | False | NULL |
| sendinfosource | 77 | 0 | NULL |
| logisticsstatus | 77 | 56134 | NULL |
| returnorderreason | 77 |  | NULL |
| isdeliverysource | 77 | 0 | NULL |
| isdstrddelivery | 77 | 0 | NULL |
| agency | 77 | 范立志 | NULL |
| agencyid | 77 | 51 | NULL |
| distributionmode | 77 | 57419 | NULL |
| selfdistributionvoucherdisabled | 77 | False | NULL |
| auditedtime | 77 | 2026-10-13 19:59:52.140000, 2026-10-13 20:00:15.717000, 2026-10-13 20:00:33.133000 | NULL |
| drivercount | 77 | 0 | NULL |
| isdistributionbluegenred | 77 | False | NULL |
| isdigelectronicinvoice | 77 | 0 | NULL |
| oppositesidevoucherid | 23 |  | NULL |

### 明细

| 字段 | 历史非空数量（共373） | 历史值示例 | 新记录 |
|---|---:|---|---|
| costprice | 373 | 4.07000000000000, 104.57400000000000, 4.47700000000000 | NULL |
| costamount | 373 | 12.21000000000000, 522.87000000000000, 44.77000000000000 | NULL |
| ispresent | 373 | 0 | NULL |
| saleoutquantity | 373 | 3.00000000000000, 5.00000000000000, 10.00000000000000 | NULL |
| taxflag | 373 | 1 | NULL |
| ismanualcost | 373 | 0 | NULL |
| updatedby | 373 | 15046102049 | NULL |
| ismemberintegral | 373 | 0 | NULL |
| ispromotionpresent | 373 | 0 | NULL |
| issaleout | 373 | 15 | NULL |
| latestcost | 287 | 4.07076923000000, 3209.05287307000000, 3.36287836000000 | NULL |
| singleinvgrossprofit | 287 | 0.18881779000000, -3204.01216511000000, 2.72030748000000 | NULL |
| grossprofit | 287 | 0.57000000000000, -16020.06000000000000, 13.60000000000000 | NULL |
| grossprofitrate | 287 | 0.04430000000000, -635.62740000000000, 0.44720000000000 | NULL |
| datasource | 373 | 2497 | NULL |
| refunddifferenceflag | 373 | 51185 | NULL |
| discountpricechange | 373 | 0 | NULL |
| taxpricechange | 373 | 0 | NULL |
| executablequantity | 373 | 0E-14 | NULL |

## 核对边界

预期字段通过当前导入校验/映射逻辑重建，并与原始XLS、数据库及历史CSV交叉检查；并未独立重实现全部业务规则。未核验未配置字段在T+应用中的业务效果，未执行审核API、生成出库单、发票或凭证。历史样本与新数据不是同一组单据，不能逐行比较全部业务取值相等。
