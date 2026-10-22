/*
用途：确定线上实际成本源结构，为成本生成SQL建立依据。
只读；在T+业务账套执行。该脚本不是成本计算SQL。
返回：1.数据库 2.候选表/视图字段 3.候选表行数。
结果3按顺序执行SELECT；未使用NOLOCK，不改业务数据。
*/
SET NOCOUNT ON;
SET LOCK_TIMEOUT 5000;
SELECT DB_NAME() AS [业务账套];

SELECT s.name AS [架构],o.name AS [对象],o.type_desc AS [对象类型],
       c.column_id AS [字段顺序],c.name AS [字段],ty.name AS [类型],
       c.precision AS [精度],c.scale AS [小数位],
       CAST(ep.value AS nvarchar(2000)) AS [字段说明]
FROM sys.objects AS o
JOIN sys.schemas AS s ON s.schema_id=o.schema_id
JOIN sys.columns AS c ON c.object_id=o.object_id
JOIN sys.types AS ty ON ty.user_type_id=c.user_type_id
LEFT JOIN sys.extended_properties AS ep
  ON ep.class=1 AND ep.major_id=c.object_id AND ep.minor_id=c.column_id
 AND ep.name=N'MS_Description'
WHERE o.type IN ('U','V')
  AND LOWER(o.name) IN
  ('st_currentstock','st_newcurrentstock','st_summarybook','st_subsidiarybook',
   'st_assistantdatabook','st_marketingorganinvprice','st_marketingorganskuinvprice',
   'st_rdrecord','st_rdrecord_b')
ORDER BY o.name,c.column_id;

DECLARE @schema sysname,@table sysname,@sql nvarchar(max);
DECLARE CostSourceTables CURSOR LOCAL FAST_FORWARD FOR
SELECT s.name,t.name
FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id
WHERE LOWER(t.name) IN
 ('st_currentstock','st_newcurrentstock','st_summarybook','st_subsidiarybook',
  'st_assistantdatabook','st_marketingorganinvprice','st_marketingorganskuinvprice',
  'st_rdrecord','st_rdrecord_b');
OPEN CostSourceTables;
FETCH NEXT FROM CostSourceTables INTO @schema,@table;
WHILE @@FETCH_STATUS=0
BEGIN
    SET @sql=N'SELECT N'''+REPLACE(@schema+N'.'+@table,N'''',N'''''')+
      N''' AS [来源表],COUNT_BIG(*) AS [行数] FROM '+QUOTENAME(@schema)+N'.'+QUOTENAME(@table);
    BEGIN TRY
        EXEC sp_executesql @sql;
    END TRY
    BEGIN CATCH
        SELECT @schema+N'.'+@table AS [来源表],ERROR_MESSAGE() AS [查询失败原因];
    END CATCH;
    FETCH NEXT FROM CostSourceTables INTO @schema,@table;
END;
CLOSE CostSourceTables;
DEALLOCATE CostSourceTables;
