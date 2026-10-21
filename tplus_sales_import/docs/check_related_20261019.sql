-- 在 SSMS 中选择目标账套后执行。业务表只读，仅使用 tempdb 临时表。
-- 按 SA 编号前缀筛选：code LIKE N'SA20261019%'，不按创建时间筛选。
-- 外键查询未命中不代表没有业务关联；元数据权限不足也会影响结果。
SET NOCOUNT ON;

DECLARE @CodePrefix nvarchar(50) = N'SA20261019';

IF OBJECT_ID('tempdb..#TplusRelatedHeaders') IS NOT NULL
    DROP TABLE #TplusRelatedHeaders;
IF OBJECT_ID('tempdb..#TplusRelatedDetails') IS NOT NULL
    DROP TABLE #TplusRelatedDetails;

SELECT h.ID, h.code, h.ExternalCode, h.createdtime
INTO #TplusRelatedHeaders
FROM dbo.SA_SaleDelivery AS h
WHERE h.code LIKE @CodePrefix + N'%';

SELECT d.ID, d.idSaleDeliveryDTO
INTO #TplusRelatedDetails
FROM dbo.SA_SaleDelivery_b AS d
INNER JOIN #TplusRelatedHeaders AS h ON h.ID = d.idSaleDeliveryDTO;

-- 结果1：核对账套、范围和数量。建议暂停相关业务操作后核对。
SELECT DB_NAME() AS [当前账套], @CodePrefix AS [SA编号前缀],
       (SELECT COUNT_BIG(*) FROM #TplusRelatedHeaders) AS [目标表头数量],
       (SELECT COUNT_BIG(*) FROM #TplusRelatedDetails) AS [目标明细数量],
       HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'VIEW DEFINITION') AS [可查看全库定义];

-- 结果2：表头上的凭证、发票、来源和业务状态线索。
-- 仅选择当前库实际存在的字段；字段原值不直接解释为已产生下游单据。
DECLARE @Columns nvarchar(max), @Sql nvarchar(max);
SELECT @Columns = STUFF((
    SELECT N',h.' + QUOTENAME(c.name)
    FROM sys.columns AS c
    WHERE c.object_id = OBJECT_ID('dbo.SA_SaleDelivery')
      AND LOWER(c.name) IN
          ('id','code','externalcode','voucherdate','createdtime','maker',
           'voucherstate','docid','saleinvoiceid','saleinvoiceno','saleinvoicecode',
           'originvoicetaxamount','origsettleamount','settleamount',
           'origprereceiveamount','prereceiveamount','receivebalance',
           'sourcevouchercode','idsourcevouchertype','isautogeneratesaleout',
           'isautosaleout','issaleout','isautogenerateinvoice','saleoutdate',
           'iscarriedforwardout','iscarriedforwardin','isnoarapbookkeeping',
           'idcollaborateupvoucher','idcollaborateupvouchertype',
           'idcollaboratedowndraftvoucher','idcollaboratedownvouchertype')
    ORDER BY c.column_id
    FOR XML PATH(''), TYPE).value('.', 'nvarchar(max)'), 1, 1, N'');
SET @Sql = N'SELECT ' + @Columns + N'
FROM dbo.SA_SaleDelivery AS h
INNER JOIN #TplusRelatedHeaders AS t ON t.ID=h.ID ORDER BY h.ID;';
EXEC sys.sp_executesql @Sql;

-- 结果3：明细上的出库/开票/结算数量金额及单据引用线索。
SELECT @Columns = STUFF((
    SELECT N',d.' + QUOTENAME(c.name)
    FROM sys.columns AS c
    WHERE c.object_id = OBJECT_ID('dbo.SA_SaleDelivery_b')
      AND LOWER(c.name) IN
          ('id','code','idsaledeliverydto','idinventory','quantity',
           'saleoutquantity','saleoutquantity2','invoicequantity','invoicequantity2',
           'origsettleamount','settleamount','originvoicetaxamount',
           'returnquntity','counteractquntity','docid','associateddocids',
           'sourcevouchercode','sourcevoucherid','sourcevoucherdetailid',
           'idsourcevouchertype','receivevouchercode','receivevoucherid',
           'receivevoucherdetailid','issaleout')
    ORDER BY c.column_id
    FOR XML PATH(''), TYPE).value('.', 'nvarchar(max)'), 1, 1, N'');
SET @Sql = N'SELECT t.idSaleDeliveryDTO AS [目标表头ID],' + @Columns + N'
FROM dbo.SA_SaleDelivery_b AS d
INNER JOIN #TplusRelatedDetails AS t ON t.ID=d.ID ORDER BY t.idSaleDeliveryDTO,d.ID;';
EXEC sys.sp_executesql @Sql;

-- 结果4：实际存在的、指向目标主明细表的物理外键。
SELECT fk.name AS [外键名称],
       OBJECT_SCHEMA_NAME(fk.parent_object_id) AS [引用表架构],
       OBJECT_NAME(fk.parent_object_id) AS [引用表], pc.name AS [引用字段],
       OBJECT_NAME(fk.referenced_object_id) AS [被引用表], rc.name AS [被引用字段],
       fk.is_disabled AS [外键已禁用], fk.is_not_trusted AS [外键未受信任]
FROM sys.foreign_keys AS fk
INNER JOIN sys.foreign_key_columns AS fkc ON fkc.constraint_object_id=fk.object_id
INNER JOIN sys.columns AS pc
    ON pc.object_id=fkc.parent_object_id AND pc.column_id=fkc.parent_column_id
INNER JOIN sys.columns AS rc
    ON rc.object_id=fkc.referenced_object_id AND rc.column_id=fkc.referenced_column_id
WHERE fk.referenced_object_id IN
      (OBJECT_ID('dbo.SA_SaleDelivery'), OBJECT_ID('dbo.SA_SaleDelivery_b'))
ORDER BY fk.name, fkc.constraint_column_id;

-- 结果5：逐个物理外键统计实际引用本次目标记录的行数。
-- 动态语句仅 SELECT；关联条件取自真实外键，支持多列外键。
-- SA_SaleDelivery_b 对表头的引用是预期的主从关系，不能当作下游单据。
DECLARE @FkID int, @ParentID int, @ReferenceID int;
DECLARE @ParentName nvarchar(517), @ReferenceName nvarchar(517);
DECLARE @Join nvarchar(max), @Scope nvarchar(100);
DECLARE @FkName sysname;
DECLARE RelationCursor CURSOR LOCAL FAST_FORWARD FOR
    SELECT object_id, parent_object_id, referenced_object_id
    FROM sys.foreign_keys
    WHERE referenced_object_id IN
          (OBJECT_ID('dbo.SA_SaleDelivery'), OBJECT_ID('dbo.SA_SaleDelivery_b'));
OPEN RelationCursor;
FETCH NEXT FROM RelationCursor INTO @FkID,@ParentID,@ReferenceID;
WHILE @@FETCH_STATUS=0
BEGIN
    SET @ParentName=QUOTENAME(OBJECT_SCHEMA_NAME(@ParentID))+N'.'+QUOTENAME(OBJECT_NAME(@ParentID));
    SET @ReferenceName=QUOTENAME(OBJECT_SCHEMA_NAME(@ReferenceID))+N'.'+QUOTENAME(OBJECT_NAME(@ReferenceID));
    SET @Scope=CASE WHEN @ReferenceID=OBJECT_ID('dbo.SA_SaleDelivery')
                   THEN N'#TplusRelatedHeaders' ELSE N'#TplusRelatedDetails' END;
    SELECT @Join=STUFF((
        SELECT N' AND p.'+QUOTENAME(pc.name)+N'=r.'+QUOTENAME(rc.name)
        FROM sys.foreign_key_columns AS fkc
        INNER JOIN sys.columns AS pc
            ON pc.object_id=fkc.parent_object_id AND pc.column_id=fkc.parent_column_id
        INNER JOIN sys.columns AS rc
            ON rc.object_id=fkc.referenced_object_id AND rc.column_id=fkc.referenced_column_id
        WHERE fkc.constraint_object_id=@FkID
        ORDER BY fkc.constraint_column_id
        FOR XML PATH(''),TYPE).value('.','nvarchar(max)'),1,5,N'');
    SET @Sql=N'SELECT @TableName AS [引用表],@FkName AS [外键名称],COUNT_BIG(*) AS [实际引用行数]
FROM '+@ParentName+N' AS p INNER JOIN '+@ReferenceName+N' AS r ON '+@Join+N'
INNER JOIN '+@Scope+N' AS t ON t.ID=r.ID;';
    BEGIN TRY
        SET @FkName=OBJECT_NAME(@FkID);
        EXEC sys.sp_executesql @Sql,N'@TableName nvarchar(517),@FkName sysname',@ParentName,@FkName;
    END TRY
    BEGIN CATCH
        SELECT @ParentName AS [未完成核对的表],ERROR_MESSAGE() AS [错误_不能视为无关联];
    END CATCH;
    FETCH NEXT FROM RelationCursor INTO @FkID,@ParentID,@ReferenceID;
END;
CLOSE RelationCursor;
DEALLOCATE RelationCursor;

-- 结果6：发现无物理外键时仍可能使用的业务关联字段和相关单据表。
-- 这里只发现候选结构，不按数值相同直接认定关联；来源ID还需要匹配来源单据类型。
SELECT s.name AS [架构],t.name AS [候选表],c.name AS [字段],
       TYPE_NAME(c.user_type_id) AS [类型],c.max_length AS [最大字节长度],
       CAST(ep.value AS nvarchar(4000)) AS [字段说明]
FROM sys.tables AS t
INNER JOIN sys.schemas AS s ON s.schema_id=t.schema_id
INNER JOIN sys.columns AS c ON c.object_id=t.object_id
LEFT JOIN sys.extended_properties AS ep
    ON ep.class=1 AND ep.major_id=c.object_id AND ep.minor_id=c.column_id
   AND ep.name=N'MS_Description'
WHERE t.is_ms_shipped=0
  AND
  (
      LOWER(c.name) LIKE '%saledelivery%'
      OR LOWER(c.name) IN ('sourcevoucherid','sourcevoucherdetailid','sourcevouchercode',
          'idsourcevouchertype','sourcevouchertype','docid','associateddocids',
          'idcollaborateupvoucher','idcollaborateupvouchertype')
      OR
      (
          (LOWER(t.name) LIKE '%saleout%' OR LOWER(t.name) LIKE '%rdrecord%'
           OR LOWER(t.name) LIKE '%invoice%' OR LOWER(t.name) LIKE '%voucher%'
           OR LOWER(t.name) LIKE '%relation%' OR LOWER(t.name) LIKE '%accvouch%')
          AND (LOWER(c.name) LIKE '%source%' OR LOWER(c.name) LIKE '%voucher%'
               OR LOWER(c.name) IN ('id','code','docid'))
      )
  )
ORDER BY s.name,t.name,c.column_id;

DROP TABLE #TplusRelatedDetails;
DROP TABLE #TplusRelatedHeaders;
