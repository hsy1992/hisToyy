-- 只读排查：在发生异常的账套执行。不会修改单据或枚举。
-- 填写一张异常单据和一张显示正常的第一版单据；可只填写异常单据。
DECLARE @TargetCode nvarchar(50) = N'';
DECLARE @BaselineCode nvarchar(50) = N'';

-- 先核实本账套的状态字典，不能把枚举 ID 当作布尔值。
SELECT ID, Name, Code, idEnum, IsDeleted
FROM dbo.eap_EnumItem
WHERE idEnum IN (40, 88, 16, 501)
ORDER BY idEnum, ID;

-- 核实审核字段省略插入后采用的数据库默认值。
SELECT OBJECT_NAME(c.object_id) AS TableName, c.name AS ColumnName,
       t.name AS TypeName, c.is_nullable,
       OBJECT_DEFINITION(c.default_object_id) AS DefaultValue
FROM sys.columns AS c
JOIN sys.types AS t ON t.user_type_id = c.user_type_id
WHERE c.object_id IN (OBJECT_ID(N'dbo.SA_SaleDelivery'),
                      OBJECT_ID(N'dbo.SA_SaleDelivery_b'),
                      OBJECT_ID(N'dbo.ARAP_Detail'))
  AND (c.name LIKE N'%audit%' OR c.name LIKE N'%state%'
       OR c.name LIKE N'%flag%'
       OR c.name IN (N'isSaleOut', N'isCancel', N'saleOutQuantity'))
ORDER BY TableName, c.column_id;

IF @TargetCode = N'' AND @BaselineCode = N''
BEGIN
    SELECT N'请填写脚本顶部的异常/正常 SA 单号，再执行单据对比查询。' AS Message;
    RETURN;
END;

SELECT h.ID, h.code, h.voucherState, vs.Name AS VoucherStateName,
       h.isSaleOut, so.Name AS SaleOutStateName,
       CASE WHEN so.ID IS NULL THEN N'出库状态无有效枚举' ELSE N'出库枚举存在' END AS SaleOutCheck,
       h.isCancel, cs.Name AS SettlementStateName,
       h.auditor, h.auditorid, h.auditeddate, h.AuditedTime,
       h.isAutoGenerateSaleOut, h.IsAutoSaleOut,
       h.isNoArapBookkeeping, h.LogisticsStatus, h.createdtime
FROM dbo.SA_SaleDelivery AS h
LEFT JOIN dbo.eap_EnumItem AS vs ON vs.ID = h.voucherState AND vs.idEnum = 88 AND vs.IsDeleted = 0
LEFT JOIN dbo.eap_EnumItem AS so ON so.ID = h.isSaleOut AND so.idEnum = 40 AND so.IsDeleted = 0
LEFT JOIN dbo.eap_EnumItem AS cs ON cs.ID = h.isCancel AND cs.idEnum = 16 AND cs.IsDeleted = 0
WHERE h.code IN (@TargetCode, @BaselineCode)
ORDER BY h.ID;

SELECT h.code AS HeaderCode, d.ID, d.code AS DetailCode,
       d.isSaleOut, so.Name AS SaleOutStateName,
       CASE WHEN so.ID IS NULL THEN N'出库状态无有效枚举' ELSE N'出库枚举存在' END AS SaleOutCheck,
       d.quantity, d.saleOutQuantity, d.RefundDifferenceFlag, d.DataSource
FROM dbo.SA_SaleDelivery AS h
JOIN dbo.SA_SaleDelivery_b AS d ON d.idSaleDeliveryDTO = h.ID
LEFT JOIN dbo.eap_EnumItem AS so ON so.ID = d.isSaleOut AND so.idEnum = 40 AND so.IsDeleted = 0
WHERE h.code IN (@TargetCode, @BaselineCode)
ORDER BY h.ID, d.ID;

SELECT h.code AS HeaderCode, a.ID, a.voucherID, a.voucherDetailID,
       a.auditFlag, a.auditBussinessFlag, a.BookFlag, bf.Name AS BookFlagName,
       a.isArFlag, a.flag, a.idarapvouchertype, a.idvouchertype
FROM dbo.SA_SaleDelivery AS h
JOIN dbo.ARAP_Detail AS a ON a.voucherID = h.ID
LEFT JOIN dbo.eap_EnumItem AS bf ON bf.ID = a.BookFlag AND bf.idEnum = 501 AND bf.IsDeleted = 0
WHERE h.code IN (@TargetCode, @BaselineCode)
ORDER BY h.ID, a.ID;
