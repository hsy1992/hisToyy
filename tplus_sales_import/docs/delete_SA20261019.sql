-- 在 SSMS 中先选择并确认目标账套，备份数据库后使用。
-- 范围：SA_SaleDelivery.code LIKE N'SA20261019%'。
-- 默认仅预览；将 @ExecuteDelete 改为 1 才会尝试删除。
-- 只删除销货单主明细，不删除出库单、发票、凭证或业务关系表。
-- 保留表头引用线索检查；不再以明细出库/开票数量或结算金额非零拦截。
-- 检测通过也不能证明不存在其他逻辑关联。
-- 执行前仍须完成 check_related_20261019.sql 的关联核对。
SET NOCOUNT ON;
SET XACT_ABORT ON;

DECLARE @CodePrefix nvarchar(50) = N'SA20261019';
DECLARE @ExecuteDelete bit = 1;
DECLARE @ExpectedHeaders bigint = 5822; -- 根据本次截图；范围变化时先重新核对。
DECLARE @ExpectedDetails bigint = 8606;
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

    IF @HeaderCount <> @ExpectedHeaders OR @DetailCount <> @ExpectedDetails
        RAISERROR(N'目标数量与已核对的5822张表头、8606条明细不一致，请重新核对范围。', 16, 1);


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
