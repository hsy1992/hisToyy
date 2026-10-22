/*
只读查询：在实际 T+ 业务账套中执行，修改 @SaleCode 为目标销货单号。
公式已与本地373条成本/287条毛利记录核对；线上结果用于继续验证。
LatestCost是已保存的取数输入，本查询不伪造其库存来源算法。
costPrice回算与costAmount复算是关系检查，不能据此确定内部计算先后。
多单位、外币、手工成本、出库调整及零数量请结合原单据解释。
不使用NOLOCK，避免读取尚未提交的成本。
*/
SET NOCOUNT ON;
SET LOCK_TIMEOUT 5000;

DECLARE @SaleCode nvarchar(50);
SET @SaleCode = N'SA2026101200001'; -- 改成要核对的销货单号

;WITH SourceRows AS
(
    SELECT
        h.ID AS HeaderID,h.code AS SaleCode,h.ExternalCode,
        h.voucherdate,h.idcustomer,h.idmarketingorgan,h.exchangeRate,
        b.ID AS DetailID,b.code AS DetailCode,
        b.idinventory,b.idwarehouse,b.idunit,b.idbaseunit,
        b.quantity,b.baseQuantity,b.saleOutQuantity,
        b.origDiscountPrice,b.discountPrice,b.origTaxPrice,b.taxRate,
        b.costPrice,b.costAmount,b.LatestCost,
        b.SingleInvGrossProfit,b.GrossProfit,b.GrossProfitRate,
        b.isManualCost,b.adjustAmount,
        CAST(ROUND(b.origDiscountPrice-b.LatestCost,8)
             AS decimal(28,8)) AS CalcSingleGrossProfit,
        ROUND(b.costPrice*b.baseQuantity,2) AS CalcCostAmount,
        ROUND(b.costAmount/NULLIF(b.baseQuantity,0),6,1) AS BackCalcCostPrice
    FROM dbo.SA_SaleDelivery AS h
    INNER JOIN dbo.SA_SaleDelivery_b AS b ON b.idSaleDeliveryDTO=h.ID
    WHERE h.code=@SaleCode
), CalcRows AS
(
    SELECT s.*,
        ROUND(s.CalcSingleGrossProfit*s.quantity,2) AS CalcGrossProfit,
        ROUND(s.CalcSingleGrossProfit /
              NULLIF(CAST(s.origDiscountPrice AS decimal(28,8)),0),4)
              AS CalcGrossProfitRate
    FROM SourceRows AS s
)
SELECT
    DB_NAME() AS [当前账套],c.SaleCode AS [销货单号],c.ExternalCode AS [源用友单号],
    c.voucherdate AS [单据日期],c.DetailID AS [明细ID],c.DetailCode AS [明细编号],
    c.idcustomer AS [客户ID],c.idmarketingorgan AS [营销机构ID],
    c.idinventory AS [存货ID],c.idwarehouse AS [仓库ID],
    c.idunit AS [销售单位ID],c.idbaseunit AS [基本单位ID],
    c.exchangeRate AS [汇率],c.quantity AS [销售数量],c.baseQuantity AS [基本数量],
    c.saleOutQuantity AS [累计出库数量],c.isManualCost AS [手工确定成本],
    c.adjustAmount AS [调差金额],
    c.origDiscountPrice AS [原币无税单价],c.discountPrice AS [本币无税单价],
    c.origTaxPrice AS [原币含税单价],c.taxRate AS [税率],
    c.LatestCost AS [LatestCost_已保存结存成本输入],
    c.costPrice AS [costPrice_原值],c.BackCalcCostPrice AS [costPrice_由金额回算截断6位],
    c.costPrice-c.BackCalcCostPrice AS [costPrice_差额],
    c.costAmount AS [costAmount_原值],c.CalcCostAmount AS [costAmount_复算2位],
    c.costAmount-c.CalcCostAmount AS [costAmount_差额],
    c.SingleInvGrossProfit AS [SingleInvGrossProfit_原值],
    c.CalcSingleGrossProfit AS [SingleInvGrossProfit_复算8位],
    c.SingleInvGrossProfit-c.CalcSingleGrossProfit AS [SingleInvGrossProfit_差额],
    c.GrossProfit AS [GrossProfit_原值],c.CalcGrossProfit AS [GrossProfit_复算2位],
    c.GrossProfit-c.CalcGrossProfit AS [GrossProfit_差额],
    c.GrossProfitRate AS [GrossProfitRate_原值],
    c.CalcGrossProfitRate AS [GrossProfitRate_复算4位],
    c.GrossProfitRate-c.CalcGrossProfitRate AS [GrossProfitRate_差额],
    CASE WHEN c.LatestCost IS NULL THEN N'缺少结存成本，毛利公式无法复算'
         WHEN c.origDiscountPrice IS NULL THEN N'缺少无税单价'
         WHEN c.origDiscountPrice=0 THEN N'无税单价为0，不计算毛利率'
         ELSE N'可核对各毛利差额列' END AS [毛利核对说明],
    CASE WHEN c.baseQuantity IS NULL OR c.baseQuantity=0 THEN N'基本数量为空或0，不回算成本价'
         WHEN c.costAmount IS NULL OR c.costPrice IS NULL THEN N'实际成本输入缺失'
         ELSE N'可核对实际成本差额列' END AS [成本核对说明]
FROM CalcRows AS c
ORDER BY c.HeaderID,c.DetailID;
