-- 主表源单号去重查询结构；临时表由导入器在同一连接创建和批量填充。
-- 本文件仅提供查询模板，未创建临时表、索引，也未插入数据。
-- VoucherCode应与ExternalCode匹配：nvarchar(50)、Chinese_PRC_CI_AS。
SELECT p.VoucherCode AS SourceVoucherCode,h.ID,h.code AS SACode
FROM #TempPendingCodes p
JOIN dbo.SA_SaleDelivery h ON h.ExternalCode=p.VoucherCode;

-- 源数据新插入表头时同时保存ExternalCode和ExternalVoucherCode。
-- ID由数据库自增生成，明细idSaleDeliveryDTO取本次返回的表头ID。
-- 本地ExternalCode尚无索引；千万级底表性能需另行审阅索引方案。
