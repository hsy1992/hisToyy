-- 当前导入规则：客户编码匹配实际客户表，同时取得税率枚举名称。
-- 当前本地 eap_EnumItem 为空，TaxRateName 将为NULL；应标记，不默认13%。
SELECT p.id AS CustomerID,p.code AS CustomerCode,p.name AS CustomerName,p.disabled,
       p.taxRate AS TaxRateEnumID,e.Name AS TaxRateName,e.Code AS TaxRateCode
FROM dbo.AA_PartnerEntity p
LEFT JOIN dbo.eap_EnumItem e ON e.ID=p.taxRate;
