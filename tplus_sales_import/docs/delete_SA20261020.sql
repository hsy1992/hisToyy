-- 在 SSMS 中先选择并确认目标账套，备份数据库后使用。
-- 范围：SA_SaleDelivery.code LIKE N'SA20261020%'。
-- 当前为执行模式（@ExecuteDelete=1）；如需先预览，请改为0。
-- 只删除销货单主明细，不删除出库单、发票、凭证或业务关系表。
-- 恢复明细四字段和表头引用线索检查；命中即中止并回滚，需核实实际关联。
-- 字段非零仅代表关联线索；检查通过也不能证明不存在其他逻辑关联。
-- 关联核对脚本若用于本批次，也需将编号前缀改为SA20261020。
SET NOCOUNT ON;
SET XACT_ABORT ON;

DECLARE @CodePrefix nvarchar(50) = N'SA20261020';
DECLARE @ExecuteDelete bit = 1;
DECLARE @HeaderCount bigint, @DetailCount bigint;
DECLARE @DeletedHeaders int, @DeletedDetails int;
DECLARE @TargetHeaders TABLE (ID int PRIMARY KEY);

BEGIN TRY
    BEGIN TRANSACTION;

    INSERT INTO @TargetHeaders (ID)
    SELECT h.ID
    FROM dbo.SA_SaleDelivery AS h WITH (UPDLOCK, HOLDLOCK)
    WHERE h.code LIKE @CodePrefix + N'%';

    SELECT @HeaderCount = COUNT_BIG(*) FROM @TargetHeaders;
    SELECT @DetailCount = COUNT_BIG(*)
    FROM dbo.SA_SaleDelivery_b AS d WITH (UPDLOCK, HOLDLOCK)
    INNER JOIN @TargetHeaders AS t ON t.ID = d.idSaleDeliveryDTO;

    SELECT DB_NAME() AS [当前账套], @CodePrefix AS [SA编号前缀],
           @HeaderCount AS [目标表头数量], @DetailCount AS [目标明细数量];

    SELECT h.ID, h.code, h.ExternalCode, h.createdtime, h.voucherdate
    FROM dbo.SA_SaleDelivery AS h
    INNER JOIN @TargetHeaders AS t ON t.ID = h.ID
    ORDER BY h.code, h.ID;

    -- 预览不执行删除；释放上面的核对锁。
    IF @ExecuteDelete = 0
    BEGIN
        ROLLBACK TRANSACTION;
        PRINT N'仅预览，未删除业务数据。';
        RETURN;
    END;



    -- 明细关联线索：任一字段非零时中止，不直接认定已有下游单据。
    IF EXISTS
    (
        SELECT 1
        FROM dbo.SA_SaleDelivery_b AS d
        INNER JOIN @TargetHeaders AS t ON t.ID = d.idSaleDeliveryDTO
        WHERE COALESCE(d.saleOutQuantity, 0) <> 0
           OR COALESCE(d.invoiceQuantity, 0) <> 0
           OR COALESCE(d.origSettleAmount, 0) <> 0
           OR COALESCE(d.settleAmount, 0) <> 0
    )
        RAISERROR(N'目标明细存在非零出库数量、开票数量或结算金额线索，已中止删除，请先核实实际关联。', 16, 1);

    -- 表头关联线索：凭证引用、发票号、开票金额和结算金额。
    IF EXISTS
    (
        SELECT 1
        FROM dbo.SA_SaleDelivery AS h
        INNER JOIN @TargetHeaders AS t ON t.ID = h.ID
        WHERE NULLIF(LTRIM(RTRIM(CONVERT(nvarchar(100), h.docid))), N'') IS NOT NULL
           OR NULLIF(LTRIM(RTRIM(h.saleInvoiceNo)), N'') IS NOT NULL
           OR COALESCE(h.OrigInvoiceTaxAmount, 0) <> 0
           OR COALESCE(h.origSettleAmount, 0) <> 0
           OR COALESCE(h.settleAmount, 0) <> 0
    )
        RAISERROR(N'目标表头存在凭证引用、发票号、开票金额或结算金额线索，已中止删除，请先核实实际关联。', 16, 1);

    DELETE d
    FROM dbo.SA_SaleDelivery_b AS d
    INNER JOIN @TargetHeaders AS t ON t.ID = d.idSaleDeliveryDTO;
    SET @DeletedDetails = @@ROWCOUNT;

    DELETE h
    FROM dbo.SA_SaleDelivery AS h
    INNER JOIN @TargetHeaders AS t ON t.ID = h.ID;
    SET @DeletedHeaders = @@ROWCOUNT;

    IF @DeletedHeaders <> @HeaderCount OR @DeletedDetails <> @DetailCount
        RAISERROR(N'实际删除数量与目标数量不一致，整笔事务回滚。', 16, 1);

    IF EXISTS
    (
        SELECT 1 FROM dbo.SA_SaleDelivery AS h
        INNER JOIN @TargetHeaders AS t ON t.ID = h.ID
    )
    OR EXISTS
    (
        SELECT 1 FROM dbo.SA_SaleDelivery_b AS d
        INNER JOIN @TargetHeaders AS t ON t.ID = d.idSaleDeliveryDTO
    )
        RAISERROR(N'删除后仍存在目标记录，整笔事务回滚。', 16, 1);

    COMMIT TRANSACTION;
    SELECT DB_NAME() AS [当前账套], @DeletedHeaders AS [已删除表头数量],
           @DeletedDetails AS [已删除明细数量];
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0
        ROLLBACK TRANSACTION;
    DECLARE @ErrorMessage nvarchar(4000) = ERROR_MESSAGE();
    RAISERROR(N'删除中止，事务已回滚：%s', 16, 1, @ErrorMessage);
END CATCH;
