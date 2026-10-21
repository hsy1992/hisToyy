-- 业务数据及结构只读；不刷新视图、不创建对象、不执行删除。
-- 先在 SSMS 选择“其他工具”实际连接的数据库，再执行整个脚本。
-- 如截图中的库名识别有误，请按详细错误中的原文修改下一行。
SET NOCOUNT ON;
DECLARE @ReferencedDb sysname = N'UFTData235382_300216';
DECLARE @Sql nvarchar(max);

-- 1. 核对实例、当前库、登录及权限。需与报错工具的连接配置对照。
SELECT @@SERVERNAME AS [服务器], DB_NAME() AS [当前数据库],
       ORIGINAL_LOGIN() AS [原始登录], SUSER_SNAME() AS [当前登录],
       USER_NAME() AS [数据库用户], @ReferencedDb AS [错误引用的数据库],
       HAS_DBACCESS(@ReferencedDb) AS [是否可访问引用库],
       HAS_PERMS_BY_NAME(DB_NAME(),'DATABASE','VIEW DEFINITION') AS [可查看当前库定义];

SELECT name AS [数据库], state_desc AS [状态], collation_name AS [排序规则]
FROM sys.databases
WHERE name = DB_NAME() OR name = @ReferencedDb;

-- 2. 定位当前库中的报错视图/函数，以及往来单位对象。
-- 零行也可能受元数据权限影响，不能仅据此判定对象被删。
SELECT s.name AS [架构], o.name AS [对象], o.type_desc AS [对象类型],
       o.create_date AS [创建时间], o.modify_date AS [最近定义修改时间],
       m.definition AS [定义]
FROM sys.objects AS o
INNER JOIN sys.schemas AS s ON s.schema_id=o.schema_id
LEFT JOIN sys.sql_modules AS m ON m.object_id=o.object_id
WHERE LOWER(o.name) LIKE N'%retqpartner%'
   OR LOWER(o.name) IN (N'aa_partner',N'aa_partnerentity');

-- 3. 报错对象的依赖路径：重点检查是否写死了旧账套、错误架构或旧表名。
SELECT OBJECT_SCHEMA_NAME(d.referencing_id) AS [视图或函数架构],
       OBJECT_NAME(d.referencing_id) AS [视图或函数],
       d.referenced_server_name AS [引用服务器],
       d.referenced_database_name AS [引用数据库],
       d.referenced_schema_name AS [引用架构],
       d.referenced_entity_name AS [引用对象],
       d.referenced_id AS [解析到的本库对象ID]
FROM sys.sql_expression_dependencies AS d
WHERE LOWER(OBJECT_NAME(d.referencing_id)) LIKE N'%retqpartner%'
   OR LOWER(d.referenced_entity_name) IN (N'aa_partner',N'aa_partnerentity');

SELECT SCHEMA_NAME(schema_id) AS [同义词架构], name AS [同义词],
       base_object_name AS [实际指向]
FROM sys.synonyms
WHERE LOWER(name) LIKE N'%partner%'
   OR LOWER(base_object_name) LIKE N'%partner%';

-- 4. 在错误指向的数据库里核对对象是否存在及实际列结构。
IF HAS_DBACCESS(@ReferencedDb) = 1
BEGIN
    SET @Sql=N'SELECT @Db AS [被检查数据库],s.name AS [架构],o.name AS [对象],
o.type_desc AS [对象类型],o.create_date,o.modify_date
FROM '+QUOTENAME(@ReferencedDb)+N'.sys.objects AS o
INNER JOIN '+QUOTENAME(@ReferencedDb)+N'.sys.schemas AS s ON s.schema_id=o.schema_id
WHERE LOWER(o.name) IN (N''aa_partner'',N''aa_partnerentity'');
SELECT @Db AS [被检查数据库],s.name AS [架构],o.name AS [对象],
c.column_id,c.name AS [字段],ty.name AS [类型],c.max_length
FROM '+QUOTENAME(@ReferencedDb)+N'.sys.objects AS o
INNER JOIN '+QUOTENAME(@ReferencedDb)+N'.sys.schemas AS s ON s.schema_id=o.schema_id
INNER JOIN '+QUOTENAME(@ReferencedDb)+N'.sys.columns AS c ON c.object_id=o.object_id
INNER JOIN '+QUOTENAME(@ReferencedDb)+N'.sys.types AS ty ON ty.user_type_id=c.user_type_id
WHERE LOWER(o.name) IN (N''aa_partner'',N''aa_partnerentity'')
ORDER BY s.name,o.name,c.column_id;';
    EXEC sys.sp_executesql @Sql,N'@Db sysname',@ReferencedDb;

    -- 按错误中的“数据库..aa_partner”形式验证对象绑定，不读取业务行。
    BEGIN TRY
        SET @Sql=N'SELECT TOP (0) * FROM '+QUOTENAME(@ReferencedDb)+N'..[aa_partner];';
        EXEC sys.sp_executesql @Sql;
        SELECT N'按数据库..aa_partner形式绑定成功' AS [对象绑定检查];
    END TRY
    BEGIN CATCH
        SELECT ERROR_NUMBER() AS [错误编号],ERROR_MESSAGE() AS [对象绑定错误];
    END CATCH;
END
ELSE
    SELECT N'当前登录无法访问错误指向的数据库；先核对实例、库名和权限。' AS [未完成检查];

-- 5. 当前库销货单表是否存在触发器；排查删除可能触发的间接操作。
SELECT OBJECT_SCHEMA_NAME(t.parent_id) AS [业务表架构],
       OBJECT_NAME(t.parent_id) AS [业务表],t.name AS [触发器],
       t.is_disabled AS [已禁用],m.definition AS [触发器定义]
FROM sys.triggers AS t
LEFT JOIN sys.sql_modules AS m ON m.object_id=t.object_id
WHERE t.parent_id IN (OBJECT_ID(N'dbo.SA_SaleDelivery'),OBJECT_ID(N'dbo.SA_SaleDelivery_b'));
