# UFDATA_999_1015 实际字段映射

只读读取实际数据库元数据。CSV列号从0开始；两表列序连续且与成功CSV宽度一致。

## dbo.SA_SaleDelivery

| CSV零基位置 | 字段 | 类型 | 可空 | 自增 | 默认值 |
|---:|---|---|---|---|---|
| 0 | code | nvarchar(50) | 是 | 否 |  |
| 1 | origCancelAmount | decimal(28,14) | 是 | 否 |  |
| 2 | origAmount | decimal(28,14) | 是 | 否 |  |
| 3 | amount | decimal(28,14) | 是 | 否 |  |
| 4 | origTaxAmount | decimal(28,14) | 是 | 否 |  |
| 5 | taxAmount | decimal(28,14) | 是 | 否 |  |
| 6 | isCounteractDelivery | tinyint | 是 | 否 |  |
| 7 | discountAmount | decimal(28,14) | 是 | 否 |  |
| 8 | discountRate | decimal(28,14) | 是 | 否 |  |
| 9 | discountsAndAllowances | decimal(28,14) | 是 | 否 |  |
| 10 | exchangeRate | decimal(28,14) | 是 | 否 |  |
| 11 | address | nvarchar(200) | 是 | 否 |  |
| 12 | linkMan | nvarchar(50) | 是 | 否 |  |
| 13 | cancelAmount | decimal(28,14) | 是 | 否 |  |
| 14 | isPriceTrace | tinyint | 是 | 否 |  |
| 15 | memo | nvarchar(200) | 是 | 否 |  |
| 16 | saleInvoiceNo | nvarchar(1000) | 是 | 否 |  |
| 17 | isAutoGenerateInvoice | tinyint | 是 | 否 |  |
| 18 | isAutoGenerateSaleOut | tinyint | 是 | 否 |  |
| 19 | origSettleAmount | decimal(28,14) | 是 | 否 |  |
| 20 | settleAmount | decimal(28,14) | 是 | 否 |  |
| 21 | contactPhone | nvarchar(100) | 是 | 否 |  |
| 22 | isNoModify | nvarchar(1000) | 是 | 否 |  |
| 23 | isBeforeSystemInuse | tinyint | 是 | 否 |  |
| 24 | maker | nvarchar(50) | 是 | 否 |  |
| 25 | auditor | nvarchar(50) | 是 | 否 |  |
| 26 | reviser | nvarchar(50) | 是 | 否 |  |
| 27 | iscarriedforwardout | tinyint | 是 | 否 |  |
| 28 | iscarriedforwardin | tinyint | 是 | 否 |  |
| 29 | ismodifiedcode | tinyint | 是 | 否 |  |
| 30 | docid | nvarchar(36) | 是 | 否 |  |
| 31 | OrigTS | timestamp | 是 | 否 |  |
| 32 | updatedBy | nvarchar(32) | 是 | 否 |  |
| 33 | priuserdefnvc1 | nvarchar(500) | 是 | 否 |  |
| 34 | priuserdefdecm1 | decimal(28,14) | 是 | 否 |  |
| 35 | priuserdefnvc2 | nvarchar(500) | 是 | 否 |  |
| 36 | priuserdefdecm2 | decimal(28,14) | 是 | 否 |  |
| 37 | priuserdefnvc3 | nvarchar(500) | 是 | 否 |  |
| 38 | priuserdefdecm3 | decimal(28,14) | 是 | 否 |  |
| 39 | priuserdefnvc4 | nvarchar(500) | 是 | 否 |  |
| 40 | priuserdefdecm4 | decimal(28,14) | 是 | 否 |  |
| 41 | priuserdefnvc5 | nvarchar(500) | 是 | 否 |  |
| 42 | priuserdefdecm5 | decimal(28,14) | 是 | 否 |  |
| 43 | priuserdefnvc6 | nvarchar(500) | 是 | 否 |  |
| 44 | priuserdefdecm6 | decimal(28,14) | 是 | 否 |  |
| 45 | pubuserdefnvc1 | nvarchar(500) | 是 | 否 |  |
| 46 | pubuserdefdecm1 | decimal(28,14) | 是 | 否 |  |
| 47 | pubuserdefnvc2 | nvarchar(500) | 是 | 否 |  |
| 48 | pubuserdefdecm2 | decimal(28,14) | 是 | 否 |  |
| 49 | pubuserdefnvc3 | nvarchar(500) | 是 | 否 |  |
| 50 | pubuserdefdecm3 | decimal(28,14) | 是 | 否 |  |
| 51 | pubuserdefnvc4 | nvarchar(500) | 是 | 否 |  |
| 52 | pubuserdefdecm4 | decimal(28,14) | 是 | 否 |  |
| 53 | pubuserdefnvc5 | nvarchar(500) | 是 | 否 |  |
| 54 | pubuserdefdecm5 | decimal(28,14) | 是 | 否 |  |
| 55 | pubuserdefnvc6 | nvarchar(500) | 是 | 否 |  |
| 56 | pubuserdefdecm6 | decimal(28,14) | 是 | 否 |  |
| 57 | isNoArapBookkeeping | tinyint | 是 | 否 |  |
| 58 | origprereceiveamount | decimal(28,14) | 是 | 否 |  |
| 59 | PreReceiveAmount | decimal(28,14) | 是 | 否 |  |
| 60 | ReceiveBalance | decimal(28,14) | 是 | 否 |  |
| 61 | SourceVoucherCode | nvarchar(50) | 是 | 否 |  |
| 62 | changer | nvarchar(50) | 是 | 否 |  |
| 63 | OrigInvoiceTaxAmount | decimal(28,14) | 是 | 否 |  |
| 64 | thisBalanceIntegral | decimal(28,14) | 是 | 否 |  |
| 65 | Mobilephone | nvarchar(50) | 是 | 否 |  |
| 66 | MemberAddress | nvarchar(50) | 是 | 否 |  |
| 67 | PrintCount | int | 是 | 否 |  |
| 68 | IsSeparateByWareHouse | tinyint | 是 | 否 |  |
| 69 | Allowances | decimal(28,14) | 是 | 否 |  |
| 70 | origAllowances | decimal(28,14) | 是 | 否 |  |
| 71 | IsAutoSaleOut | tinyint | 是 | 否 |  |
| 72 | ExternalCode | nvarchar(50) | 是 | 否 |  |
| 73 | collaborateVoucherCode | nvarchar(30) | 是 | 否 |  |
| 74 | ID | int | 否 | 是 |  |
| 75 | idbusinesstype | int | 是 | 否 |  |
| 76 | idcurrency | int | 是 | 否 |  |
| 77 | iddepartment | int | 是 | 否 |  |
| 78 | IdMember | int | 是 | 否 |  |
| 79 | idmarketingOrgan | int | 是 | 否 |  |
| 80 | idcustomer | int | 是 | 否 |  |
| 81 | idsettlecustomer | int | 是 | 否 |  |
| 82 | idclerk | int | 是 | 否 |  |
| 83 | idproject | int | 是 | 否 |  |
| 84 | idrdstyle | int | 是 | 否 |  |
| 85 | idwarehouse | int | 是 | 否 |  |
| 86 | idCollaborateUpVoucherType | int | 是 | 否 |  |
| 87 | idCollaborateUpVoucher | int | 是 | 否 |  |
| 88 | DataSource | int | 是 | 否 |  |
| 89 | deliveryMode | int | 是 | 否 |  |
| 90 | invoiceType | int | 是 | 否 |  |
| 91 | isCancel | int | 是 | 否 |  |
| 92 | isSaleOut | int | 是 | 否 |  |
| 93 | reciveType | int | 是 | 否 |  |
| 94 | voucherState | int | 是 | 否 |  |
| 95 | auditorid | int | 是 | 否 |  |
| 96 | makerid | int | 是 | 否 |  |
| 97 | changerid | int | 是 | 否 |  |
| 98 | idCollaborateDownVoucherType | int | 是 | 否 |  |
| 99 | CollaborateState | int | 是 | 否 |  |
| 100 | idCollaborateDownDraftVoucher | int | 是 | 否 |  |
| 101 | saleInvoiceID | int | 是 | 否 |  |
| 102 | idsourcevouchertype | int | 是 | 否 |  |
| 103 | deliveryDate | datetime | 是 | 否 |  |
| 104 | recivingMaturity | datetime | 是 | 否 |  |
| 105 | voucherdate | datetime | 是 | 否 |  |
| 106 | madedate | datetime | 是 | 否 |  |
| 107 | auditeddate | datetime | 是 | 否 |  |
| 108 | createdtime | datetime | 是 | 否 |  |
| 109 | updated | datetime | 是 | 否 |  |
| 110 | SourceVoucherDate | datetime | 是 | 否 |  |
| 111 | changedate | datetime | 是 | 否 |  |
| 112 | ExternalVoucherCode | nvarchar(50) | 是 | 否 | (NULL) |
| 113 | SaleInvoiceMedia | int | 是 | 否 |  |
| 114 | CustomerPhone | nvarchar(100) | 是 | 否 |  |
| 115 | HasRecordCredit | bit | 是 | 否 |  |
| 116 | IsAutoWarehouse | bit | 是 | 否 |  |
| 117 | InputDataSource | int | 是 | 否 |  |
| 118 | idSendPerson | int | 是 | 否 |  |
| 119 | SendDate | datetime | 是 | 否 |  |
| 120 | idConsignor | int | 是 | 否 |  |
| 121 | SendInfoSource | int | 是 | 否 |  |
| 122 | SaleOrderCode | nvarchar(30) | 是 | 否 |  |
| 123 | ConsignorDate | datetime | 是 | 否 |  |
| 124 | idExaminer | int | 是 | 否 |  |
| 125 | ExaminerDate | datetime | 是 | 否 |  |
| 126 | ts | varbinary | 是 | 否 | ((0)) |
| 127 | DirectCallSource | int | 是 | 否 | (NULL) |
| 128 | isAutoGenerateFromLMDeliver | bit | 是 | 否 | ((0)) |
| 129 | idLogisticsNetwork | int | 是 | 否 |  |
| 130 | TransDocNo | nvarchar(4000) | 是 | 否 |  |
| 131 | DeliveryCode | nvarchar(200) | 是 | 否 |  |
| 132 | DeliveryVoucherDate | datetime | 是 | 否 |  |
| 133 | TransDriverName | nvarchar(200) | 是 | 否 |  |
| 134 | TransDriverPhone | nvarchar(200) | 是 | 否 |  |
| 135 | TransVehicleInfo | nvarchar(200) | 是 | 否 |  |
| 136 | LogisticsFee | decimal(28,14) | 是 | 否 |  |
| 137 | LogisticsSettlementModes | int | 是 | 否 |  |
| 138 | LogisticsStatus | int | 是 | 否 |  |
| 139 | returnReason | int | 是 | 否 |  |
| 140 | returnOrderReason | nvarchar(500) | 是 | 否 |  |
| 141 | OrigSaleInvoiceCode | nvarchar(1000) | 是 | 否 |  |
| 142 | OrigSaleInvoiceNo | nvarchar(1000) | 是 | 否 |  |
| 143 | RedCofCause | nvarchar(200) | 是 | 否 |  |
| 144 | SaleInvoiceSystem | int | 是 | 否 |  |
| 145 | SaleInvoiceCode | nvarchar(1000) | 是 | 否 |  |
| 146 | SaleInvoiceSourceData | nvarchar(200) | 是 | 否 |  |
| 147 | ElecOrderFlag | int | 是 | 否 |  |
| 148 | IsMarkDelivery | int | 是 | 否 |  |
| 149 | IsDeliverySource | int | 是 | 否 |  |
| 150 | IdCountry | int | 是 | 否 |  |
| 151 | IdProvince | int | 是 | 否 |  |
| 152 | IdCity | int | 是 | 否 |  |
| 153 | IdDistrict | int | 是 | 否 |  |
| 154 | PostCode | nvarchar(20) | 是 | 否 |  |
| 155 | ElecOrderInfoKey | nvarchar(500) | 是 | 否 |  |
| 156 | idSaleIOU | int | 是 | 否 |  |
| 157 | TransNumber | nvarchar(200) | 是 | 否 |  |
| 158 | ThroughDate | datetime | 是 | 否 |  |
| 159 | IsDstRDDelivery | tinyint | 是 | 否 |  |
| 160 | CustomerMemo | nvarchar(200) | 是 | 否 |  |
| 161 | IsReadOnly | bit | 否 | 否 | ((0)) |
| 162 | FailSaleOutReason | nvarchar(1000) | 是 | 否 |  |
| 163 | SaleOutDate | datetime | 是 | 否 |  |
| 164 | agency | nvarchar(50) | 是 | 否 |  |
| 165 | agencyid | int | 是 | 否 |  |
| 166 | idReceiveWarehouse | int | 是 | 否 |  |
| 167 | idstore | int | 是 | 否 |  |
| 168 | DistributionMode | int | 是 | 否 |  |
| 169 | idDistributionLine | int | 是 | 否 |  |
| 170 | DeliveryTime | datetime | 是 | 否 |  |
| 171 | DeliveryPhoto | nvarchar(400) | 是 | 否 |  |
| 172 | idCarDispatcher | int | 是 | 否 |  |
| 173 | DispatchTime | datetime | 是 | 否 |  |
| 174 | EntruckingTime | datetime | 是 | 否 |  |
| 175 | idTransVehicle | int | 是 | 否 |  |
| 176 | SelfDistributionVoucherDisabled | bit | 是 | 否 |  |
| 177 | invoiceSpecial | nvarchar(50) | 是 | 否 |  |
| 178 | IsStockRequestAutoTransfer | bit | 是 | 否 | ((0)) |
| 179 | AuditedTime | datetime | 是 | 否 |  |
| 180 | DriversName | varchar | 是 | 否 |  |
| 181 | VehiclesName | varchar | 是 | 否 |  |
| 182 | ShiftNumber | varchar | 是 | 否 |  |
| 183 | DriverCount | int | 是 | 否 |  |
| 184 | AddressCoordinate | varchar | 是 | 否 |  |
| 185 | IsDistributionBlueGenRed | bit | 是 | 否 |  |
| 186 | BackToWarehouseTime | datetime | 是 | 否 |  |
| 187 | busOpAttachCount | int | 是 | 否 |  |
| 188 | RedCofCauseForDP | int | 是 | 否 |  |
| 189 | isSaleInvoiceNoFromSaleInvoice | bit | 是 | 否 | ((0)) |
| 190 | SocialCollaborateStatus | int | 是 | 否 |  |
| 191 | SocialCollaborateFlag | nvarchar(200) | 是 | 否 |  |
| 192 | SocialCollaborateReceiveWarehouse | nvarchar(200) | 是 | 否 |  |
| 193 | IsDigElectronicInvoice | tinyint | 是 | 否 |  |
| 194 | ExpenseDeductionRatio | decimal(28,14) | 是 | 否 |  |
| 195 | priuserdefnvc7 | nvarchar(500) | 是 | 否 |  |
| 196 | priuserdefnvc8 | nvarchar(500) | 是 | 否 |  |
| 197 | IdVchMutilTemplate | int | 是 | 否 |  |
| 198 | VchMutilTemplateTitle | nvarchar(200) | 是 | 否 |  |
| 199 | CollaborateFlag | nvarchar(200) | 是 | 否 |  |
| 200 | CollaborationType | int | 是 | 否 |  |
| 201 | EntrustedRole | int | 是 | 否 |  |
| 202 | CollaborativePriceTrategy | int | 是 | 否 |  |
| 203 | IdOppositeSideMarketingOrgan | int | 是 | 否 |  |
| 204 | IdEntrustMarketingOrgan | int | 是 | 否 |  |
| 205 | IdBeEntrustedMarketingOrgan | int | 是 | 否 |  |
| 206 | OppositeSideVoucherID | nvarchar(200) | 是 | 否 |  |
| 207 | IdEntrustedPurchaser | int | 是 | 否 |  |
| 208 | ProxyCustomerName | nvarchar(200) | 是 | 否 |  |
| 209 | ProxyCustomerLinkMan | nvarchar(200) | 是 | 否 |  |
| 210 | ProxyCustomerLinkPhoneNo | nvarchar(200) | 是 | 否 |  |
| 211 | ProxyCustomerPhoneNo | nvarchar(200) | 是 | 否 |  |
| 212 | CommissionedPurchasePrice | decimal(28,14) | 是 | 否 |  |
| 213 | IsOnlinePay | tinyint | 是 | 否 | ((0)) |
| 214 | ProxyCustomerAddress | nvarchar(500) | 是 | 否 |  |
| 215 | ProxySaleOrderCode | nvarchar(50) | 是 | 否 |  |
| 216 | IsRobotApprove | tinyint | 是 | 否 |  |
| 217 | totalPackNum | int | 是 | 否 |  |

## dbo.SA_SaleDelivery_b

| CSV零基位置 | 字段 | 类型 | 可空 | 自增 | 默认值 |
|---:|---|---|---|---|---|
| 0 | code | nvarchar(30) | 是 | 否 |  |
| 1 | isNoModify | nvarchar(1000) | 是 | 否 |  |
| 2 | quantity | decimal(28,14) | 是 | 否 |  |
| 3 | quantity2 | decimal(28,14) | 是 | 否 |  |
| 4 | unitExchangeRate | decimal(28,14) | 是 | 否 |  |
| 5 | baseQuantity | decimal(28,14) | 是 | 否 |  |
| 6 | subQuantity | decimal(28,14) | 是 | 否 |  |
| 7 | compositionQuantity | nvarchar(100) | 是 | 否 |  |
| 8 | origPrice | decimal(28,14) | 是 | 否 |  |
| 9 | price | decimal(28,14) | 是 | 否 |  |
| 10 | basePrice | decimal(28,14) | 是 | 否 |  |
| 11 | discountRate | decimal(28,14) | 是 | 否 |  |
| 12 | origDiscountPrice | decimal(28,14) | 是 | 否 |  |
| 13 | discountPrice | decimal(28,14) | 是 | 否 |  |
| 14 | baseDiscountPrice | decimal(28,14) | 是 | 否 |  |
| 15 | taxRate | decimal(28,14) | 是 | 否 |  |
| 16 | origTaxPrice | decimal(28,14) | 是 | 否 |  |
| 17 | taxPrice | decimal(28,14) | 是 | 否 |  |
| 18 | baseTaxPrice | decimal(28,14) | 是 | 否 |  |
| 19 | origDiscountAmount | decimal(28,14) | 是 | 否 |  |
| 20 | discountAmount | decimal(28,14) | 是 | 否 |  |
| 21 | origTax | decimal(28,14) | 是 | 否 |  |
| 22 | tax | decimal(28,14) | 是 | 否 |  |
| 23 | origTaxAmount | decimal(28,14) | 是 | 否 |  |
| 24 | taxAmount | decimal(28,14) | 是 | 否 |  |
| 25 | origDiscount | decimal(28,14) | 是 | 否 |  |
| 26 | discount | decimal(28,14) | 是 | 否 |  |
| 27 | costPrice | decimal(28,14) | 是 | 否 |  |
| 28 | costAmount | decimal(28,14) | 是 | 否 |  |
| 29 | receiveVoucherCode | nvarchar(50) | 是 | 否 |  |
| 30 | saleOrderCode | nvarchar(30) | 是 | 否 |  |
| 31 | batch | nvarchar(50) | 是 | 否 |  |
| 32 | adjustAmount | decimal(28,14) | 是 | 否 |  |
| 33 | isPresent | tinyint | 是 | 否 |  |
| 34 | counteractQuntity | decimal(28,14) | 是 | 否 |  |
| 35 | counteractQuntity2 | decimal(28,14) | 是 | 否 |  |
| 36 | returnQuntity | decimal(28,14) | 是 | 否 |  |
| 37 | returnQuntity2 | decimal(28,14) | 是 | 否 |  |
| 38 | saleoutquantity2 | decimal(28,14) | 是 | 否 |  |
| 39 | saleOutQuantity | decimal(28,14) | 是 | 否 |  |
| 40 | invoiceQuantity2 | decimal(28,14) | 是 | 否 |  |
| 41 | invoiceQuantity | decimal(28,14) | 是 | 否 |  |
| 42 | settleAmount | decimal(28,14) | 是 | 否 |  |
| 43 | origSettleAmount | decimal(28,14) | 是 | 否 |  |
| 44 | origExpenseAmount | decimal(28,14) | 是 | 否 |  |
| 45 | expenseAmount | decimal(28,14) | 是 | 否 |  |
| 46 | inventoryLocation | nvarchar(50) | 是 | 否 |  |
| 47 | sourceVoucherCode | nvarchar(50) | 是 | 否 |  |
| 48 | taxFlag | tinyint | 是 | 否 |  |
| 49 | isManualCost | tinyint | 是 | 否 |  |
| 50 | inventoryBarCode | nvarchar(200) | 是 | 否 |  |
| 51 | partnerInventoryCode | nvarchar(300) | 是 | 否 |  |
| 52 | OrigTS | timestamp | 是 | 否 |  |
| 53 | updatedBy | nvarchar(32) | 是 | 否 |  |
| 54 | freeItem0 | nvarchar(300) | 是 | 否 |  |
| 55 | freeItem1 | nvarchar(300) | 是 | 否 |  |
| 56 | freeItem2 | nvarchar(300) | 是 | 否 |  |
| 57 | freeItem3 | nvarchar(300) | 是 | 否 |  |
| 58 | freeItem4 | nvarchar(300) | 是 | 否 |  |
| 59 | freeItem5 | nvarchar(300) | 是 | 否 |  |
| 60 | freeItem6 | nvarchar(300) | 是 | 否 |  |
| 61 | freeItem7 | nvarchar(300) | 是 | 否 |  |
| 62 | freeItem8 | nvarchar(300) | 是 | 否 |  |
| 63 | freeItem9 | nvarchar(300) | 是 | 否 |  |
| 64 | priuserdefnvc1 | nvarchar(500) | 是 | 否 |  |
| 65 | priuserdefdecm1 | decimal(28,14) | 是 | 否 |  |
| 66 | priuserdefnvc2 | nvarchar(500) | 是 | 否 |  |
| 67 | priuserdefdecm2 | decimal(28,14) | 是 | 否 |  |
| 68 | priuserdefnvc3 | nvarchar(500) | 是 | 否 |  |
| 69 | priuserdefdecm3 | decimal(28,14) | 是 | 否 |  |
| 70 | priuserdefnvc4 | nvarchar(500) | 是 | 否 |  |
| 71 | priuserdefdecm4 | decimal(28,14) | 是 | 否 |  |
| 72 | pubuserdefnvc1 | nvarchar(500) | 是 | 否 |  |
| 73 | pubuserdefdecm1 | decimal(28,14) | 是 | 否 |  |
| 74 | pubuserdefnvc2 | nvarchar(500) | 是 | 否 |  |
| 75 | pubuserdefdecm2 | decimal(28,14) | 是 | 否 |  |
| 76 | pubuserdefnvc3 | nvarchar(500) | 是 | 否 |  |
| 77 | pubuserdefdecm3 | decimal(28,14) | 是 | 否 |  |
| 78 | pubuserdefnvc4 | nvarchar(500) | 是 | 否 |  |
| 79 | pubuserdefdecm4 | decimal(28,14) | 是 | 否 |  |
| 80 | partnerInventoryName | nvarchar(300) | 是 | 否 |  |
| 81 | virtualBaseQuantity | decimal(28,14) | 是 | 否 |  |
| 82 | virtualBaseAmount | decimal(28,14) | 是 | 否 |  |
| 83 | sentBaseQuantityAssociated | decimal(28,14) | 是 | 否 |  |
| 84 | sentBaseAmountAssociated | decimal(28,14) | 是 | 否 |  |
| 85 | backSentAmount | decimal(28,14) | 是 | 否 |  |
| 86 | backSentQuantity | decimal(28,14) | 是 | 否 |  |
| 87 | associatedDocIDs | nvarchar(400) | 是 | 否 |  |
| 88 | Retailprice | decimal(28,14) | 是 | 否 |  |
| 89 | DistributionQuantity | decimal(28,14) | 是 | 否 |  |
| 90 | DistributionQuantity2 | decimal(28,14) | 是 | 否 |  |
| 91 | BoxNumber | nvarchar(50) | 是 | 否 |  |
| 92 | OrigInvoiceTaxAmount | decimal(28,14) | 是 | 否 |  |
| 93 | PriceStrategyTypeName | nvarchar(200) | 是 | 否 |  |
| 94 | PriceStrategySchemeIds | nvarchar(1000) | 是 | 否 |  |
| 95 | PriceStrategySchemeNames | nvarchar(400) | 是 | 否 |  |
| 96 | PromotionVoucherCodes | nvarchar(400) | 是 | 否 |  |
| 97 | PromotionVoucherIds | nvarchar(400) | 是 | 否 |  |
| 98 | IsMemberIntegral | tinyint | 是 | 否 |  |
| 99 | IsPromotionPresent | tinyint | 是 | 否 |  |
| 100 | PromotionPresentVoucherCode | nvarchar(50) | 是 | 否 |  |
| 101 | PromotionSingleVoucherCode | nvarchar(50) | 是 | 否 |  |
| 102 | PromotionPresentGroupID | nvarchar(150) | 是 | 否 |  |
| 103 | PromotionSingleGroupID | nvarchar(150) | 是 | 否 |  |
| 104 | SuperSourceVoucherTypeCode | nvarchar(50) | 是 | 否 |  |
| 105 | DetailMemo | nvarchar(200) | 是 | 否 |  |
| 106 | ID | int | 否 | 是 |  |
| 107 | idinventory | int | 是 | 否 |  |
| 108 | idproject | int | 是 | 否 |  |
| 109 | idbaseunit | int | 是 | 否 |  |
| 110 | idsubunit | int | 是 | 否 |  |
| 111 | idunit | int | 是 | 否 |  |
| 112 | idunit2 | int | 是 | 否 |  |
| 113 | idwarehouse | int | 是 | 否 |  |
| 114 | isCancel | int | 是 | 否 |  |
| 115 | isSaleOut | int | 是 | 否 |  |
| 116 | CashbackWay | int | 是 | 否 |  |
| 117 | PriceStrategyTypeId | int | 是 | 否 |  |
| 118 | PromotionPresentTypeID | int | 是 | 否 |  |
| 119 | PromotionSingleTypeID | int | 是 | 否 |  |
| 120 | docid | int | 是 | 否 |  |
| 121 | PromotionPresentVoucherID | int | 是 | 否 |  |
| 122 | PromotionSingleVoucherID | int | 是 | 否 |  |
| 123 | sourceVoucherId | int | 是 | 否 |  |
| 124 | idSaleDeliveryDTO | int | 是 | 否 |  |
| 125 | sourceVoucherDetailId | int | 是 | 否 |  |
| 126 | saleOrderId | int | 是 | 否 |  |
| 127 | saleOrderDetailId | int | 是 | 否 |  |
| 128 | idsourcevouchertype | int | 是 | 否 |  |
| 129 | receiveVoucherId | int | 是 | 否 |  |
| 130 | receiveVoucherDetailId | int | 是 | 否 |  |
| 131 | expiryDate | datetime | 是 | 否 |  |
| 132 | deliveryDate | datetime | 是 | 否 |  |
| 133 | createdtime | datetime | 是 | 否 |  |
| 134 | updated | datetime | 是 | 否 |  |
| 135 | ProductionDate | datetime | 是 | 否 |  |
| 136 | LatestCost | decimal(28,14) | 是 | 否 | (NULL) |
| 137 | LatestPOrigTaxPrice | decimal(28,14) | 是 | 否 | (NULL) |
| 138 | LatestSaleOrigTaxPrice | decimal(28,14) | 是 | 否 | (NULL) |
| 139 | LowestSalePrice | decimal(28,14) | 是 | 否 | (NULL) |
| 140 | SingleInvGrossProfit | decimal(28,14) | 是 | 否 | (NULL) |
| 141 | GrossProfit | decimal(28,14) | 是 | 否 | (NULL) |
| 142 | GrossProfitRate | decimal(28,14) | 是 | 否 | (NULL) |
| 143 | DataSource | int | 是 | 否 | (NULL) |
| 144 | IsModifiedPrice | tinyint | 是 | 否 | ((0)) |
| 145 | CostPriceGetType | int | 是 | 否 |  |
| 146 | RefundDifferenceFlag | int | 是 | 否 |  |
| 147 | idExaminer | int | 是 | 否 |  |
| 148 | ExaminerDate | datetime | 是 | 否 |  |
| 149 | PromotionBatchMemo | nvarchar(200) | 是 | 否 |  |
| 150 | PromotionPresentBatchInfo | nvarchar(200) | 是 | 否 |  |
| 151 | PromotionPresentBatchType | nvarchar(200) | 是 | 否 |  |
| 152 | PromotionPriceBatchInfo | nvarchar(200) | 是 | 否 |  |
| 153 | PromotionPriceBatchType | nvarchar(200) | 是 | 否 |  |
| 154 | ts | varbinary | 是 | 否 | ((0)) |
| 155 | SNCount | int | 是 | 否 |  |
| 156 | SerialNumbers | nvarchar(500) | 是 | 否 |  |
| 157 | idCPMCopartner | int | 是 | 否 |  |
| 158 | SaleRevenueType | int | 是 | 否 |  |
| 159 | ReturnReason | int | 是 | 否 |  |
| 160 | BoxBarCodes | nvarchar(500) | 是 | 否 |  |
| 161 | BoxBarCodeCount | int | 是 | 否 |  |
| 162 | packBoxQuantity | decimal(28,14) | 是 | 否 |  |
| 163 | packBoxQuantity2 | decimal(28,14) | 是 | 否 |  |
| 164 | PreDiscountPrice | decimal(28,14) | 是 | 否 |  |
| 165 | PreTaxPrice | decimal(28,14) | 是 | 否 |  |
| 166 | PrePriceStrategyTypeId | int | 是 | 否 |  |
| 167 | DiscountPriceChange | int | 是 | 否 |  |
| 168 | TaxPriceChange | int | 是 | 否 |  |
| 169 | topFHCCode | nvarchar(200) | 是 | 否 |  |
| 170 | idTopFHCID | int | 是 | 否 |  |
| 171 | idTopFHCMXID | int | 是 | 否 |  |
| 172 | BusinessAttribute | int | 是 | 否 |  |
| 173 | SocialCollaborateReceiveWarehouse | nvarchar(200) | 是 | 否 |  |
| 174 | ControlMode | int | 是 | 否 |  |
| 175 | ExecutableQuantity | decimal(28,14) | 是 | 否 |  |
| 176 | ExecutableQuantity2 | decimal(28,14) | 是 | 否 |  |
| 177 | ExchangeVerifiedQuantity | decimal(28,14) | 是 | 否 |  |
| 178 | ExchangeVerifiedQuantity2 | decimal(28,14) | 是 | 否 |  |
| 179 | ExchangeUnVerifiedQuantity | decimal(28,14) | 是 | 否 |  |
| 180 | ExchangeUnVerifiedQuantity2 | decimal(28,14) | 是 | 否 |  |
| 181 | ExchangeVerifiedAmount | decimal(28,14) | 是 | 否 |  |
| 182 | ExchangeUnVerifiedAmount | decimal(28,14) | 是 | 否 |  |
| 183 | ExchangeVerifiedCodeNum | nvarchar(4000) | 是 | 否 |  |
| 184 | partnerExpenseAmount | decimal(28,14) | 是 | 否 |  |
| 185 | origPartnerExpenseAmount | decimal(28,14) | 是 | 否 |  |
| 186 | PriceDimension | int | 是 | 否 |  |
| 187 | PackingCount | int | 是 | 否 |  |
| 188 | IdUnitByPacking | int | 是 | 否 |  |
| 189 | PackingCapacity | decimal(28,14) | 是 | 否 |  |
| 190 | CollaborationType | int | 是 | 否 |  |
| 191 | EntrustedRole | int | 是 | 否 |  |
| 192 | CollaborativePriceTrategy | int | 是 | 否 |  |
| 193 | IdOppositeSideMarketingOrgan | int | 是 | 否 |  |
| 194 | IdEntrustMarketingOrgan | int | 是 | 否 |  |
| 195 | IdBeEntrustedMarketingOrgan | int | 是 | 否 |  |
| 196 | CollaborateVoucherCode | nvarchar(200) | 是 | 否 |  |
| 197 | OppositeSideVoucherID | nvarchar(200) | 是 | 否 |  |
| 198 | IdEntrustedPurchaser | int | 是 | 否 |  |
| 199 | ProxyCustomerName | nvarchar(200) | 是 | 否 |  |
| 200 | ProxyCustomerLinkMan | nvarchar(200) | 是 | 否 |  |
| 201 | ProxyCustomerLinkPhoneNo | nvarchar(200) | 是 | 否 |  |
| 202 | ProxyCustomerPhoneNo | nvarchar(200) | 是 | 否 |  |
| 203 | CommissionedPurchasePrice | decimal(28,14) | 是 | 否 |  |
| 204 | ProxyCustomerAddress | nvarchar(500) | 是 | 否 |  |
| 205 | CollaborateSourecVoucherDetailId | int | 是 | 否 |  |
| 206 | ProxySaleOrderCode | nvarchar(50) | 是 | 否 |  |

## dbo.AA_InventoryEntity

| CSV零基位置 | 字段 | 类型 | 可空 | 自增 | 默认值 |
|---:|---|---|---|---|---|
| 0 | code | nvarchar(50) | 是 | 否 |  |
| 1 | name | nvarchar(200) | 是 | 否 |  |
| 2 | shorthand | nvarchar(200) | 是 | 否 |  |
| 3 | specification | nvarchar(200) | 是 | 否 |  |
| 4 | procureBatch | decimal(28,14) | 是 | 否 |  |
| 5 | invSCost | decimal(28,14) | 是 | 否 |  |
| 6 | latestCost_Abandon | decimal(28,14) | 是 | 否 |  |
| 7 | avagCost_Abandon | decimal(28,14) | 是 | 否 |  |
| 8 | isLimitedWithdraw | tinyint | 是 | 否 |  |
| 9 | isBatch | tinyint | 是 | 否 |  |
| 10 | isQualityPeriod | tinyint | 是 | 否 |  |
| 11 | isSale | tinyint | 是 | 否 |  |
| 12 | isMadeSelf | tinyint | 是 | 否 |  |
| 13 | isPurchase | tinyint | 是 | 否 |  |
| 14 | isMaterial | tinyint | 是 | 否 |  |
| 15 | lowQuantity | decimal(28,14) | 是 | 否 |  |
| 16 | topQuantity | decimal(28,14) | 是 | 否 |  |
| 17 | safeQuantity | decimal(28,14) | 是 | 否 |  |
| 18 | picture | nvarchar(50) | 是 | 否 |  |
| 19 | disabled | tinyint | 是 | 否 |  |
| 20 | isQualityCheck | tinyint | 是 | 否 |  |
| 21 | isMadeRequest | tinyint | 是 | 否 |  |
| 22 | isSingleUnit | tinyint | 是 | 否 |  |
| 23 | ts | timestamp | 是 | 否 |  |
| 24 | updatedBy | nvarchar(32) | 是 | 否 |  |
| 25 | Userfreeitem7 | tinyint | 是 | 否 | ((0)) |
| 26 | Userfreeitem6 | tinyint | 是 | 否 | ((0)) |
| 27 | Userfreeitem2 | tinyint | 是 | 否 | ((0)) |
| 28 | Userfreeitem1 | tinyint | 是 | 否 | ((0)) |
| 29 | Userfreeitem9 | tinyint | 是 | 否 | ((0)) |
| 30 | Userfreeitem0 | tinyint | 是 | 否 | ((0)) |
| 31 | Userfreeitem8 | tinyint | 是 | 否 | ((0)) |
| 32 | Userfreeitem5 | tinyint | 是 | 否 | ((0)) |
| 33 | Userfreeitem4 | tinyint | 是 | 否 | ((0)) |
| 34 | Userfreeitem3 | tinyint | 是 | 否 | ((0)) |
| 35 | MustInputFreeitem7 | tinyint | 是 | 否 | ((0)) |
| 36 | MustInputFreeitem2 | tinyint | 是 | 否 | ((0)) |
| 37 | MustInputFreeitem6 | tinyint | 是 | 否 | ((0)) |
| 38 | MustInputFreeitem3 | tinyint | 是 | 否 | ((0)) |
| 39 | MustInputFreeitem5 | tinyint | 是 | 否 | ((0)) |
| 40 | MustInputFreeitem4 | tinyint | 是 | 否 | ((0)) |
| 41 | MustInputFreeitem9 | tinyint | 是 | 否 | ((0)) |
| 42 | MustInputFreeitem1 | tinyint | 是 | 否 | ((0)) |
| 43 | MustInputFreeitem8 | tinyint | 是 | 否 | ((0)) |
| 44 | MustInputFreeitem0 | tinyint | 是 | 否 | ((0)) |
| 45 | produceBatch | decimal(28,14) | 是 | 否 |  |
| 46 | imageFile | nvarchar(500) | 是 | 否 |  |
| 47 | priuserdefnvc1 | nvarchar(500) | 是 | 否 |  |
| 48 | priuserdefdecm1 | decimal(28,14) | 是 | 否 |  |
| 49 | priuserdefnvc2 | nvarchar(500) | 是 | 否 |  |
| 50 | priuserdefdecm2 | decimal(28,14) | 是 | 否 |  |
| 51 | priuserdefnvc3 | nvarchar(500) | 是 | 否 |  |
| 52 | priuserdefdecm3 | decimal(28,14) | 是 | 否 |  |
| 53 | priuserdefnvc4 | nvarchar(500) | 是 | 否 |  |
| 54 | priuserdefdecm4 | decimal(28,14) | 是 | 否 |  |
| 55 | priuserdefnvc5 | nvarchar(500) | 是 | 否 |  |
| 56 | priuserdefdecm5 | decimal(28,14) | 是 | 否 |  |
| 57 | standardturnoverdays | decimal(28,14) | 是 | 否 |  |
| 58 | HasEverChanged | nvarchar(32) | 是 | 否 |  |
| 59 | pickbatch | decimal(28,14) | 是 | 否 |  |
| 60 | isphantom | tinyint | 是 | 否 |  |
| 61 | ControlRangeFreeitem0 | tinyint | 是 | 否 | ((0)) |
| 62 | ControlRangeFreeitem1 | tinyint | 是 | 否 | ((0)) |
| 63 | ControlRangeFreeitem2 | tinyint | 是 | 否 | ((0)) |
| 64 | ControlRangeFreeitem3 | tinyint | 是 | 否 | ((0)) |
| 65 | ControlRangeFreeitem4 | tinyint | 是 | 否 | ((0)) |
| 66 | ControlRangeFreeitem5 | tinyint | 是 | 否 | ((0)) |
| 67 | ControlRangeFreeitem6 | tinyint | 是 | 否 | ((0)) |
| 68 | ControlRangeFreeitem7 | tinyint | 是 | 否 | ((0)) |
| 69 | ControlRangeFreeitem8 | tinyint | 是 | 否 | ((0)) |
| 70 | ControlRangeFreeitem9 | tinyint | 是 | 否 | ((0)) |
| 71 | IsLaborCost | tinyint | 是 | 否 |  |
| 72 | BatchRunNumber | decimal(18,0) | 是 | 否 |  |
| 73 | IsNew | tinyint | 是 | 否 |  |
| 74 | MadeRecordDate | datetime | 是 | 否 |  |
| 75 | InventoryDescript | nvarchar(1000) | 是 | 否 |  |
| 76 | ReNewGoodSellDays | int | 是 | 否 |  |
| 77 | ReNewGoodAheadDays | int | 是 | 否 |  |
| 78 | IsSuite | tinyint | 是 | 否 |  |
| 79 | IsWeigh | tinyint | 是 | 否 |  |
| 80 | DefaultBarCode | nvarchar(200) | 是 | 否 |  |
| 81 | NewProductPeriod | int | 是 | 否 |  |
| 82 | Expired | int | 是 | 否 |  |
| 83 | idbarcodesolution | int | 是 | 否 |  |
| 84 | id | int | 否 | 是 |  |
| 85 | idinventoryclass | int | 是 | 否 |  |
| 86 | idinvlocation | int | 是 | 否 |  |
| 87 | idMarketingOrgan | int | 是 | 否 |  |
| 88 | idpartner | int | 是 | 否 |  |
| 89 | idunit | int | 是 | 否 |  |
| 90 | idunitbymanufacture | int | 是 | 否 |  |
| 91 | idUnitByPurchase | int | 是 | 否 |  |
| 92 | idUnitByRetail | int | 是 | 否 |  |
| 93 | idUnitBySale | int | 是 | 否 |  |
| 94 | idUnitByStock | int | 是 | 否 |  |
| 95 | idunitgroup | int | 是 | 否 |  |
| 96 | idSubUnitByReport | int | 是 | 否 |  |
| 97 | ExpiredUnit | int | 是 | 否 |  |
| 98 | idwarehouse | int | 是 | 否 |  |
| 99 | customerReplenishmentRule | int | 是 | 否 |  |
| 100 | pickbatchmethod | int | 是 | 否 |  |
| 101 | planattribute | int | 是 | 否 |  |
| 102 | productInfo | int | 是 | 否 |  |
| 103 | storeReplenishmentRule | int | 是 | 否 |  |
| 104 | taxRate | int | 是 | 否 |  |
| 105 | unittype | int | 是 | 否 |  |
| 106 | valueType | int | 是 | 否 |  |
| 107 | madeDate | datetime | 是 | 否 |  |
| 108 | updated | datetime | 是 | 否 |  |
| 109 | createdTime | datetime | 是 | 否 |  |
| 110 | Creater | nvarchar(200) | 是 | 否 | (NULL) |
| 111 | Changer | nvarchar(200) | 是 | 否 | (NULL) |
| 112 | Changedate | datetime | 是 | 否 | (NULL) |
| 113 | JinShuiCode | nvarchar(40) | 是 | 否 | (NULL) |
| 114 | IsModifiedCode | tinyint | 是 | 否 |  |
| 115 | WithOutBargain | tinyint | 是 | 否 |  |
| 116 | idInventoryFreeItemClass0 | int | 是 | 否 |  |
| 117 | idInventoryFreeItemClass1 | int | 是 | 否 |  |
| 118 | idInventoryFreeItemClass2 | int | 是 | 否 |  |
| 119 | idInventoryFreeItemClass3 | int | 是 | 否 |  |
| 120 | idInventoryFreeItemClass4 | int | 是 | 否 |  |
| 121 | idInventoryFreeItemClass5 | int | 是 | 否 |  |
| 122 | idInventoryFreeItemClass6 | int | 是 | 否 |  |
| 123 | idInventoryFreeItemClass7 | int | 是 | 否 |  |
| 124 | idInventoryFreeItemClass8 | int | 是 | 否 |  |
| 125 | idInventoryFreeItemClass9 | int | 是 | 否 |  |
| 126 | InStorageUpLimit | decimal(32,15) | 是 | 否 |  |
| 127 | OutStorageUpLimit | decimal(32,15) | 是 | 否 |  |
| 128 | AutoGenProject | int | 是 | 否 |  |
| 129 | DefaultFreeItem0 | int | 是 | 否 |  |
| 130 | DefaultFreeItem1 | int | 是 | 否 |  |
| 131 | DefaultFreeItem2 | int | 是 | 否 |  |
| 132 | DefaultFreeItem3 | int | 是 | 否 |  |
| 133 | DefaultFreeItem4 | int | 是 | 否 |  |
| 134 | DefaultFreeItem5 | int | 是 | 否 |  |
| 135 | DefaultFreeItem6 | int | 是 | 否 |  |
| 136 | DefaultFreeItem7 | int | 是 | 否 |  |
| 137 | DefaultFreeItem8 | int | 是 | 否 |  |
| 138 | DefaultFreeItem9 | int | 是 | 否 |  |
| 139 | BackflushMaterial | tinyint | 是 | 否 |  |
| 140 | SaleReturnPercentRate | decimal(28,14) | 是 | 否 |  |
| 141 | IsEshop | tinyint | 是 | 否 |  |
| 142 | WorkingHours | decimal(28,14) | 是 | 否 |  |
| 143 | IsSerialNumber | tinyint | 是 | 否 | ((0)) |
| 144 | idSNSolution | int | 是 | 否 |  |
| 145 | PackageExpireDate | int | 是 | 否 |  |
| 146 | idDefaultRouting | int | 是 | 否 |  |
| 147 | InvoiceName | nvarchar(200) | 是 | 否 |  |
| 148 | TaxClassName | nvarchar(50) | 是 | 否 |  |
| 149 | TaxClassShortName | nvarchar(100) | 是 | 否 |  |
| 150 | IsUseDiscountPolicy | tinyint | 是 | 否 | ((0)) |
| 151 | TaxDiscountType | int | 是 | 否 |  |
| 152 | TaxDiscountRelation | nvarchar(100) | 是 | 否 |  |
| 153 | baseauditor | nvarchar(50) | 是 | 否 |  |
| 154 | baseauditorid | nvarchar(50) | 是 | 否 |  |
| 155 | baseauditeddate | datetime | 是 | 否 |  |
| 156 | basevoucherstate | tinyint | 是 | 否 |  |
| 157 | IdSerialNumberParseGenerateRule | int | 是 | 否 |  |
| 158 | orderPolicy | int | 是 | 否 |  |
| 159 | purchaseLeadTime | int | 是 | 否 |  |
| 160 | manufactureLeadTime | int | 是 | 否 |  |
| 161 | IsNeedQualityInspection | tinyint | 是 | 否 | ((0)) |
| 162 | InmeterialInspection | tinyint | 是 | 否 | ((0)) |
| 163 | InmeterialInspectionMethod | int | 是 | 否 |  |
| 164 | InmeterialInspectionSamplingRate | decimal(28,14) | 是 | 否 |  |
| 165 | ProductionInspection | tinyint | 是 | 否 | ((0)) |
| 166 | ProductionInspectionMethod | int | 是 | 否 |  |
| 167 | ProductionInspectionSamplingRate | decimal(28,14) | 是 | 否 |  |
| 168 | OutsourcingInspection | tinyint | 是 | 否 | ((0)) |
| 169 | OutsourcingInspectionMethod | int | 是 | 否 |  |
| 170 | OutsourcingInspectionSamplingRate | decimal(28,14) | 是 | 否 |  |
| 171 | InspectAccessory | nvarchar(400) | 是 | 否 |  |
| 172 | InvoiceSpecification | nvarchar(200) | 是 | 否 |  |
| 173 | IdInvoiceUnit | int | 是 | 否 |  |
| 174 | IsCostCardSendOut | tinyint | 是 | 否 | ((0)) |
| 175 | idInspectPlan | int | 是 | 否 |  |
| 176 | ReInspectDetail | tinyint | 是 | 否 | ((0)) |
| 177 | kitchenType | int | 是 | 否 |  |
| 178 | IsUseSettlePieceWage | tinyint | 是 | 否 | ((0)) |
| 179 | BatchSetRule | int | 是 | 否 |  |
| 180 | DriverPieceUnit | int | 是 | 否 |  |
| 181 | DriverPieceLabourPrice | decimal(28,14) | 是 | 否 |  |
| 182 | MReportUpLimit | decimal(28,14) | 是 | 否 |  |
| 183 | DeliveryType | int | 是 | 否 |  |
| 184 | idUnitByLoadCapacity | int | 是 | 否 |  |
| 185 | ProductiveProcessInspection | tinyint | 是 | 否 |  |
| 186 | MReportFinishLowerLimit | decimal(28,14) | 是 | 否 |  |
| 187 | ProcureMinBatch | decimal(28,14) | 是 | 否 |  |
| 188 | ProduceMinBatch | decimal(28,14) | 是 | 否 |  |
| 189 | PurchaseLaterTime | int | 是 | 否 |  |
| 190 | ProduceLaterTime | int | 是 | 否 |  |
| 191 | DefaultPackingCapacity | decimal(28,14) | 是 | 否 |  |
| 192 | idUnitByPacking | int | 是 | 否 |  |
| 193 | IsNeedQualityTrace | tinyint | 是 | 否 | ((0)) |
| 194 | QualityTraceMethod | int | 是 | 否 |  |
| 195 | ProduceArea | nvarchar(200) | 是 | 否 |  |
| 196 | DataFromSource | int | 是 | 否 |  |
| 197 | IdBrandProduct | nvarchar(200) | 是 | 否 |  |
| 198 | BrandMark | int | 是 | 否 |  |
| 199 | StoreMadeType | int | 是 | 否 |  |
| 200 | WorkingPrice | decimal(28,14) | 是 | 否 |  |
| 201 | UnitManuQuota | decimal(28,14) | 是 | 否 |  |
| 202 | InvWeight | decimal(28,14) | 是 | 否 |  |
| 203 | InvVolume | decimal(28,14) | 是 | 否 |  |
| 204 | SteelYardInternalCode | nvarchar(20) | 是 | 否 |  |
| 205 | EngineeringChangeManage | tinyint | 是 | 否 |  |
| 206 | AutoAddModel | nvarchar(100) | 是 | 否 |  |
| 207 | AutoAddFigureNo | nvarchar(100) | 是 | 否 |  |
| 208 | AutoAddMaterialQuality | int | 是 | 否 |  |
| 209 | ispricefreeitem0 | tinyint | 是 | 否 | ((0)) |
| 210 | ispricefreeitem1 | tinyint | 是 | 否 | ((0)) |
| 211 | ispricefreeitem2 | tinyint | 是 | 否 | ((0)) |
| 212 | ispricefreeitem3 | tinyint | 是 | 否 | ((0)) |
| 213 | ispricefreeitem4 | tinyint | 是 | 否 | ((0)) |
| 214 | ispricefreeitem5 | tinyint | 是 | 否 | ((0)) |
| 215 | ispricefreeitem6 | tinyint | 是 | 否 | ((0)) |
| 216 | ispricefreeitem7 | tinyint | 是 | 否 | ((0)) |
| 217 | ispricefreeitem8 | tinyint | 是 | 否 | ((0)) |
| 218 | ispricefreeitem9 | tinyint | 是 | 否 | ((0)) |
| 219 | IsEnableFreeItemPrice | tinyint | 是 | 否 | ((0)) |
| 220 | ExternalInvCode | nvarchar(200) | 是 | 否 |  |
| 221 | ExternalInvName | nvarchar(200) | 是 | 否 |  |
| 222 | IsMaterialRequest | tinyint | 是 | 否 |  |
| 223 | MakerId | int | 是 | 否 |  |
| 224 | IsNormalProduct | tinyint | 是 | 否 | ((0)) |
| 225 | idScrapWarehouse | int | 是 | 否 |  |
| 226 | IdUnitByProcess | int | 是 | 否 |  |
| 227 | tempfield | nvarchar(100) | 是 | 否 |  |
| 228 | IsPackage | tinyint | 是 | 否 | ((0)) |
| 229 | IsFeature | tinyint | 是 | 否 | ((0)) |
| 230 | IdFeaturePlan | int | 是 | 否 |  |

## dbo.AA_PartnerEntity

| CSV零基位置 | 字段 | 类型 | 可空 | 自增 | 默认值 |
|---:|---|---|---|---|---|
| 0 | code | nvarchar(50) | 是 | 否 |  |
| 1 | name | nvarchar(200) | 是 | 否 |  |
| 2 | partnerAbbName | nvarchar(100) | 是 | 否 |  |
| 3 | shortHand | nvarchar(100) | 是 | 否 |  |
| 4 | representative | nvarchar(50) | 是 | 否 |  |
| 5 | bankAccount | nvarchar(50) | 是 | 否 |  |
| 6 | taxRegcode | nvarchar(50) | 是 | 否 |  |
| 7 | saleCreditLine | decimal(28,14) | 是 | 否 |  |
| 8 | saleCreditDays | decimal(28,14) | 是 | 否 |  |
| 9 | purchaseCreditDays | decimal(28,14) | 是 | 否 |  |
| 10 | saleSpaceMonth | int | 是 | 否 |  |
| 11 | saleCheckMonth | int | 是 | 否 |  |
| 12 | saleCheckDate | int | 是 | 否 |  |
| 13 | purchaseSpaceMonth | int | 是 | 否 |  |
| 14 | purchaseCheckMonth | int | 是 | 否 |  |
| 15 | purchaseCheckDate | int | 是 | 否 |  |
| 16 | customeraddressphone | nvarchar(250) | 是 | 否 |  |
| 17 | ARBalance_Abandon | decimal(28,14) | 是 | 否 |  |
| 18 | APBalance_Abandon | decimal(28,14) | 是 | 否 |  |
| 19 | disabled | tinyint | 是 | 否 |  |
| 20 | ts | timestamp | 是 | 否 |  |
| 21 | updatedBy | nvarchar(32) | 是 | 否 |  |
| 22 | priuserdefnvc1 | nvarchar(500) | 是 | 否 |  |
| 23 | priuserdefdecm1 | decimal(28,14) | 是 | 否 |  |
| 24 | priuserdefnvc2 | nvarchar(500) | 是 | 否 |  |
| 25 | priuserdefdecm2 | decimal(28,14) | 是 | 否 |  |
| 26 | priuserdefnvc3 | nvarchar(500) | 是 | 否 |  |
| 27 | priuserdefdecm3 | decimal(28,14) | 是 | 否 |  |
| 28 | priuserdefnvc4 | nvarchar(500) | 是 | 否 |  |
| 29 | priuserdefdecm4 | decimal(28,14) | 是 | 否 |  |
| 30 | priuserdefnvc5 | nvarchar(500) | 是 | 否 |  |
| 31 | priuserdefdecm5 | decimal(28,14) | 是 | 否 |  |
| 32 | isContainTaxOnPurchase | tinyint | 是 | 否 |  |
| 33 | HasEverChanged | nvarchar(32) | 是 | 否 |  |
| 34 | codeSettlementPartner | nvarchar(50) | 是 | 否 |  |
| 35 | AdvRBalance_Abandon | decimal(28,14) | 是 | 否 |  |
| 36 | AdvPBalance_Abandon | decimal(28,14) | 是 | 否 |  |
| 37 | addressJC | nvarchar(200) | 是 | 否 |  |
| 38 | ShipmentAddress | nvarchar(200) | 是 | 否 |  |
| 39 | Contact | nvarchar(50) | 是 | 否 |  |
| 40 | MobilePhone | nvarchar(30) | 是 | 否 |  |
| 41 | TelephoneNo | nvarchar(100) | 是 | 否 |  |
| 42 | Fax | nvarchar(20) | 是 | 否 |  |
| 43 | EmailAddr | nvarchar(100) | 是 | 否 |  |
| 44 | QqNo | nvarchar(50) | 是 | 否 |  |
| 45 | MsnAddress | nvarchar(50) | 是 | 否 |  |
| 46 | UuNo | nvarchar(50) | 是 | 否 |  |
| 47 | creditBalance | decimal(28,14) | 是 | 否 |  |
| 48 | extendedAccounts | decimal(28,14) | 是 | 否 |  |
| 49 | SellCustomer | tinyint | 是 | 否 |  |
| 50 | MadeRecordDate | datetime | 是 | 否 |  |
| 51 | Position | varchar | 是 | 否 |  |
| 52 | RunShop | tinyint | 是 | 否 |  |
| 53 | CheckAddress | nvarchar(200) | 是 | 否 |  |
| 54 | CustomerAddress | nvarchar(200) | 是 | 否 |  |
| 55 | Birthday | datetime | 是 | 否 |  |
| 56 | AutoCreateMember | tinyint | 是 | 否 |  |
| 57 | id | int | 否 | 是 |  |
| 58 | idsaledepartment | int | 是 | 否 |  |
| 59 | iddistrict | int | 是 | 否 |  |
| 60 | idMarketingOrgan | int | 是 | 否 |  |
| 61 | idPmarketingOrgan | int | 是 | 否 |  |
| 62 | idsettlementPartner | int | 是 | 否 |  |
| 63 | idpartnerclass | int | 是 | 否 |  |
| 64 | idsaleman | int | 是 | 否 |  |
| 65 | idMemberType | int | 是 | 否 |  |
| 66 | accbank | int | 是 | 否 |  |
| 67 | customerType | int | 是 | 否 |  |
| 68 | partnerType | int | 是 | 否 |  |
| 69 | priceGrade | int | 是 | 否 |  |
| 70 | purchaseSettleStyle | int | 是 | 否 |  |
| 71 | saleSettleStyle | int | 是 | 否 |  |
| 72 | taxRate | int | 是 | 否 |  |
| 73 | saleStartDate | datetime | 是 | 否 |  |
| 74 | purchaseStartDate | datetime | 是 | 否 |  |
| 75 | madeDate | datetime | 是 | 否 |  |
| 76 | updated | datetime | 是 | 否 |  |
| 77 | createdTime | datetime | 是 | 否 |  |
| 78 | eAccount | varchar | 是 | 否 |  |
| 79 | IsModifiedCode | tinyint | 是 | 否 |  |
| 80 | ElectronicInvoiceReceiveMode | int | 是 | 否 |  |
| 81 | ElectronicInvoiceReceiveEMail | nvarchar(100) | 是 | 否 |  |
| 82 | ElectronicInvoiceReceiveMobilePhone | nvarchar(50) | 是 | 否 |  |
| 83 | DefaultInvoiceTypeOfReceive | int | 是 | 否 |  |
| 84 | iddefaultSettleStyleOfReceive | int | 是 | 否 |  |
| 85 | iddefaultBankAccountOfReceive | int | 是 | 否 |  |
| 86 | DefaultInvoiceTypeOfPayment | int | 是 | 否 |  |
| 87 | iddefaultSettleStyleOfPayment | int | 是 | 否 |  |
| 88 | iddefaultBankAccountOfPayment | int | 是 | 否 |  |
| 89 | isAutoCancel | tinyint | 是 | 否 |  |
| 90 | IsSystem | tinyint | 是 | 否 |  |
| 91 | VisitAddress | nvarchar(500) | 是 | 否 |  |
| 92 | Coordinate | nvarchar(200) | 是 | 否 |  |
| 93 | Longitude | nvarchar(200) | 是 | 否 |  |
| 94 | Latitude | nvarchar(200) | 是 | 否 |  |
| 95 | CheckInScope | decimal(32,15) | 是 | 否 |  |
| 96 | VisitFrequency | decimal(32,15) | 是 | 否 |  |
| 97 | IsNeedCheckInPhoto | tinyint | 是 | 否 | ((0)) |
| 98 | IsNeedLyHuoPhoto | tinyint | 是 | 否 | ((0)) |
| 99 | IsNeedPromotionPhoto | tinyint | 是 | 否 | ((0)) |
| 100 | IsNeedCompetitorPhoto | tinyint | 是 | 否 | ((0)) |
| 101 | PrintCount | int | 是 | 否 |  |
| 102 | Creater | nvarchar(200) | 是 | 否 | (NULL) |
| 103 | Changer | nvarchar(200) | 是 | 否 | (NULL) |
| 104 | Changedate | datetime | 是 | 否 | (NULL) |
| 105 | Route | nvarchar(500) | 是 | 否 |  |
| 106 | SavedRoutes | nvarchar(500) | 是 | 否 |  |
| 107 | LogisticsSettleStyle | int | 是 | 否 |  |
| 108 | idLogisticsNetwork | int | 是 | 否 |  |
| 109 | baseauditor | nvarchar(50) | 是 | 否 |  |
| 110 | baseauditorid | nvarchar(50) | 是 | 否 |  |
| 111 | baseauditeddate | datetime | 是 | 否 |  |
| 112 | basevoucherstate | tinyint | 是 | 否 |  |
| 113 | InvoiceAddress | nvarchar(200) | 是 | 否 |  |
| 114 | InvoicePhone | nvarchar(200) | 是 | 否 |  |
| 115 | idMallInvitee | int | 是 | 否 |  |
| 116 | DriverCoordinate | nvarchar(200) | 是 | 否 |  |
| 117 | ReceiveMode | int | 是 | 否 |  |
| 118 | CustomerLabourPriceType | nvarchar(200) | 是 | 否 |  |
| 119 | ImageFile | varchar | 是 | 否 |  |
| 120 | ExpriteDate | datetime | 是 | 否 |  |
| 121 | SaleAccountPeriodWDFlag | int | 是 | 否 |  |
| 122 | SaleAccountPeriodWeekStart | int | 是 | 否 |  |
| 123 | SaleAccountPeriodWeekEnd | int | 是 | 否 |  |
| 124 | SaleAccountPeriodDays | int | 是 | 否 |  |
| 125 | SaleAccountPeriodSpaceDays | int | 是 | 否 |  |
| 126 | SaleAccountPeriodSatrtDate | datetime | 是 | 否 |  |
| 127 | DistributionMode | int | 是 | 否 |  |
| 128 | DistributionModeByReturn | int | 是 | 否 |  |
| 129 | PartnerInvoiceName | nvarchar(200) | 是 | 否 |  |
| 130 | HeadQuarterCode | nvarchar(200) | 是 | 否 |  |
| 131 | DataFromSource | int | 是 | 否 |  |
| 132 | idHeadQuarterEntity | int | 是 | 否 |  |
| 133 | ExpenseUseRatio | decimal(28,14) | 是 | 否 |  |
| 134 | idDistributionLine | int | 是 | 否 |  |
| 135 | Channel | int | 是 | 否 |  |
| 136 | IsEntrustedPurchaser | tinyint | 是 | 否 |  |
| 137 | IdPurchaseMarketingOrgan | int | 是 | 否 |  |
| 138 | MemberName | nvarchar(200) | 是 | 否 |  |
| 139 | MemberMobilePhone | nvarchar(200) | 是 | 否 |  |
| 140 | IdDefaultMember | int | 是 | 否 |  |
