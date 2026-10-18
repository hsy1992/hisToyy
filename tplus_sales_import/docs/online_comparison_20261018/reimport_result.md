# 本地测试销货单删除重导结果

任务：20261018_152102_9769e5bd；账套：UFDATA_999_1015。

- 旧测试删除：5166张表头、7156条明细。
- 原有保留：77张表头、373条明细，删除前后及重导后的全部字段摘要完全一致。
- 重新导入：5166单、7156行；373行重复跳过、40行客户编码为空/不存在。
- 导入耗时：32.743秒。
- 当前表总数：5243张表头、7529条明细。
- 全量配置字段、主从关系和金额核验：0差异。

含税金额G按源值直接写入；未税金额ROUND_HALF_UP两位；税额=G-N；非零数量未税单价G/Q/(1+r)四舍五入8位。
新增金额合计：G=555287.430，N=491406.00，T=63881.430。

表头agency=范立志、agencyid=51、isCarriedForwardOut=0；主从DataSource=2497、isSaleOut=15；明细taxFlag=1、isModifiedPrice=1、RefundDifferenceFlag=51185。

备份：G:\pythonProject\hisToyy\tplus_sales_import\backups\before_reimport_20261018_150957.json.gz
结果文件：C:\Users\Administrator\Desktop\医药\10.12A出_UFDATA_999_1015_20261018_152102_9769e5bd_异常结果.xlsx
任务快照：G:\pythonProject\hisToyy\tplus_sales_import\runtime\20261018_152102_9769e5bd.json

含税金额原值可能有三位小数，税额差额也相应保留；本报告验证源数据和用户最新规则，不宣称与线上所有两位金额逐行一致。
