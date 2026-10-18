-- 已按 UFDATA_999_1015 实际结构核验的只读缓存查询。
-- 税率以客户档案为准，替代此前存货税率来源；库存仅用于存货和单位映射。
-- 当前账套缺税率枚举、操作员、币种及营销机构数据，查询成功不代表业务校验通过。
-- 制单人固定51/范立志；业务员NULL，不加载AA_Person。
-- 项目已在成功样本真实使用，按源值匹配，不再无条件排除项目查询。

-- 当前导入规则：客户编码匹配实际客户表，同时取得税率枚举名称。
-- 当前本地 eap_EnumItem 为空，TaxRateName 将为NULL；应标记，不默认13%。
SELECT p.id AS CustomerID,p.code AS CustomerCode,p.name AS CustomerName,p.disabled,
       p.taxRate AS TaxRateEnumID,e.Name AS TaxRateName,e.Code AS TaxRateCode
FROM dbo.AA_PartnerEntity p
LEFT JOIN dbo.eap_EnumItem e ON e.ID=p.taxRate;

SELECT N'dbo.AA_Warehouse' AS [__cache_name], [id], [code], [name], [disabled], [idMarketingOrgan], [ExternalWarehouseCode]
FROM dbo.AA_Warehouse;

SELECT N'dbo.AA_Unit' AS [__cache_name], [id], [code], [name], [disabled], [isMainUnit], [isSingleUnit], [idunitgroup], [changeRate], [changeType]
FROM dbo.AA_Unit;

SELECT N'dbo.AA_BusiType' AS [__cache_name], [id], [code], [name], [disabled], [idrdStyleIn], [idrdStyleOut]
FROM dbo.AA_BusiType;

SELECT N'dbo.AA_InventoryEntity' AS [__cache_name],
       inv.id,inv.code,inv.name,inv.specification,inv.disabled,inv.isSingleUnit,
       inv.idunit,inv.idUnitBySale,inv.idunitgroup,inv.idwarehouse
FROM dbo.AA_InventoryEntity inv;

SELECT N'dbo.AA_Project' AS [__cache_name],id,Code,Name,disabled
FROM dbo.AA_Project;

-- 固定制单人仅查一条；当前本地结果为空，应标记配置档案缺失。
SELECT id,Code,name,IsUsed,isStoped
FROM dbo.EAP_User WHERE id=51;
