/*
线上成本来源追查，只读业务数据；不是UPDATE，也不是已确认的成本生成算法。
只改@SaleCode；可选指定@DetailID。默认选该单第一条已有LatestCost的明细。
返回5组结果。请复制结果文字/导出CSV，避免截图只显示部分列。
使用本地同版本已确认的字段；若线上提示列不存在，请保留报错。
结存比值仅为候选成本；必须核对计价维度、会计期间、记账状态和取数时点。
*/
SET NOCOUNT ON;
SET LOCK_TIMEOUT 5000;
DECLARE @SaleCode nvarchar(50),@DetailID int,@InventoryID int;
SET @SaleCode=N'请填写实际销货单号';
SET @DetailID=NULL; -- 有指定明细ID时填写数字，否则自动选择一条

IF @DetailID IS NULL
    SELECT TOP (1) @DetailID=b.ID
    FROM dbo.SA_SaleDelivery h
    JOIN dbo.SA_SaleDelivery_b b ON b.idSaleDeliveryDTO=h.ID
    WHERE h.code=@SaleCode
    ORDER BY CASE WHEN b.LatestCost IS NOT NULL THEN 0 ELSE 1 END,b.ID;

SELECT @InventoryID=b.idinventory
FROM dbo.SA_SaleDelivery h
JOIN dbo.SA_SaleDelivery_b b ON b.idSaleDeliveryDTO=h.ID
WHERE h.code=@SaleCode AND b.ID=@DetailID;

IF @InventoryID IS NULL
BEGIN
    SELECT N'未匹配到目标明细，请检查业务账套、销货单号及明细ID' AS [说明];
    RETURN;
END;

-- 1. 确认目标明细与计价方式，禁止用枚举ID猜方法名称。
SELECT N'1_目标明细' AS [结果组],DB_NAME() AS [账套],
    h.code AS [销货单号],h.ID AS [销货单ID],h.voucherdate,
    h.idmarketingorgan,h.exchangeRate,
    b.ID AS [明细ID],b.idinventory,i.code AS [商品编码],i.name AS [商品名称],
    i.valueType AS [计价方式ID],e.Name AS [计价方式名称],
    b.idwarehouse,b.idunit,b.idbaseunit,b.quantity,b.baseQuantity,b.saleOutQuantity,
    b.origDiscountPrice,b.discountPrice,b.costPrice,b.costAmount,
    b.LatestCost,b.SingleInvGrossProfit,b.GrossProfit,b.GrossProfitRate,
    b.isManualCost,b.adjustAmount,b.sourceVoucherId,b.sourceVoucherDetailId,
    b.idsourcevouchertype,b.createdtime,b.updated
FROM dbo.SA_SaleDelivery h
JOIN dbo.SA_SaleDelivery_b b ON b.idSaleDeliveryDTO=h.ID
LEFT JOIN dbo.AA_InventoryEntity i ON i.ID=b.idinventory
LEFT JOIN dbo.eap_EnumItem e ON e.ID=i.valueType
WHERE h.code=@SaleCode AND b.ID=@DetailID;

-- 2. 该销货单同一存货的库存明细账候选。可能一条销货行对应多条库存账。
-- 同号同存货用于发现候选；还必须核对单据类型和明细ID，不能直接求和回填。
SELECT TOP (100) N'2_对应库存账候选' AS [结果组],
    s.ID,s.voucherCode,s.voucherCodeFlowUnite,
    s.voucherID,s.voucherDetailID,s.idvouchertype,
    s.voucherIDFlowUnite,s.voucherDetailIDFlowUnite,s.idvouchertypeflowunite,
    s.idinventory,s.idwarehouse,s.batch,s.idCostPricingDimension,
    s.accountYear,s.accountPeriod,s.voucherdate,s.accountDate,s.AccountTime,
    s.inQuantity,s.inPrice,s.inAmount,s.outQuantity,s.outPrice,s.outAmount,
    s.isTrueAccount,s.isInStock,s.isManual,s.isAdjustVoucher,
    s.iscarriedforwardin,s.iscarriedforwardout,s.orderNo,s.seqOrderNO
FROM dbo.ST_SubsidiaryBook s
WHERE s.idinventory=@InventoryID
  AND (s.voucherCode=@SaleCode OR s.voucherCodeFlowUnite=@SaleCode)
ORDER BY s.accountDate,s.orderNo,s.ID;

-- 3. 同商品的各计价维度、各期结存。不要跨期间累加finalAmount/finalQuantity。
-- 这里只计算候选比值，尚不能认定其必然等于历史销货单LatestCost。
SELECT TOP (200) N'3_结存成本候选' AS [结果组],
    s.ID,s.idinventory,s.idwarehouse,s.batch,s.idCostPricingDimension,
    s.accountYear,s.accountPeriod,s.AccountYearPeriod,s.isAccount,
    s.beginQuantity,s.beginAmount,s.incomeQuantity,s.incomeAmount,
    s.sendOutQuantity,s.sendOutAmount,s.adjustInAmount,s.adjustOutAmount,
    s.finalQuantity,s.finalAmount,
    ROUND(s.finalAmount/NULLIF(s.finalQuantity,0),8) AS [期末结存单价候选],
    s.iscarriedforwardin,s.iscarriedforwardout
FROM dbo.ST_SummaryBook s
WHERE s.idinventory=@InventoryID
ORDER BY s.accountYear DESC,s.accountPeriod DESC,s.idwarehouse,s.ID DESC;

-- 4. 当前库存维度（本地同版本此表没有成本金额，不拿数量表伪造成本）。
SELECT TOP (100) N'4_当前库存维度' AS [结果组],
    s.ID,s.idinventory,s.IdMarketingOrgan,s.idwarehouse,s.batch,
    s.idbaseunit,s.baseQuantity,s.subQuantity,
    s.receiveVoucherId,s.receiveVoucherDetailId,s.receiveVoucherCode,
    s.createdtime,s.updated,s.isCarriedForwardIn,s.isCarriedForwardOut
FROM dbo.ST_NewCurrentStock s
WHERE s.idinventory=@InventoryID
ORDER BY s.idwarehouse,s.ID;

-- 5. 有明确销货单来源线索的出入库明细候选，区分普通来源与合并流程来源。
-- 展示类型字段及父单线索供确认，不将数值相同的ID直接认定为业务关联。
SELECT TOP (100) N'5_出入库成本候选' AS [结果组],
    r.ID AS [出入库单ID],r.code AS [出入库单号],r.idvouchertype,r.idbusitype,
    r.voucherdate,r.saleDeliveryId,r.saleDeliveryCode,r.rdDirectionFlag,
    d.ID AS [出入库明细ID],d.idinventory,d.idwarehouse,
    d.sourceVoucherId,d.sourceVoucherDetailId,d.sourceVoucherCode,d.idsourcevouchertype,
    d.SourceVoucherIdByMergedFlow,d.SourceVoucherDetailIdByMergedFlow,
    d.SourceVoucherCodeByMergedFlow,d.idsourceVoucherTypeByMergedFlow,
    d.quantity,d.baseQuantity,d.price,d.basePrice,d.amount,
    d.dispatchAdjust,d.receiveAdjust,d.feeAdjust,d.totalAmount,
    d.isManualCost,d.isCostAccounted
FROM dbo.ST_RDRecord r
JOIN dbo.ST_RDRecord_b d ON d.idRDRecordDTO=r.ID
WHERE d.idinventory=@InventoryID
  AND (r.saleDeliveryCode=@SaleCode OR d.sourceVoucherCode=@SaleCode
       OR d.SourceVoucherCodeByMergedFlow=@SaleCode)
ORDER BY r.voucherdate,r.ID,d.ID;
