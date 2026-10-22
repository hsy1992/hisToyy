# 六个成本及毛利字段核验

2026-10-22，只读查询本机 127.0.0.1 / UFDATA_999_1015。未修改业务数据或导入逻辑。
字典：C:/Users/Administrator/Desktop/医药/T 数据字典.xlsx。

## 已验证关系

全库明细7529条；costPrice非空373条，LatestCost非空287条。
373条历史成本明细均为销售单位=基本单位；基本数量=销售数量=累计出库数量；公式适用范围限本次样本。

|关系|参与行数|一致行数|
|---|---:|---:|
|SingleInvGrossProfit = ROUND(origDiscountPrice - LatestCost,8)|287|287|
|SingleInvGrossProfit = ROUND(discountPrice - LatestCost,8)|287|287|
|GrossProfit = ROUND(SingleInvGrossProfit * quantity,2)|287|287|
|GrossProfitRate = ROUND(SingleInvGrossProfit / origDiscountPrice,4)|287|287|
|costAmount = ROUND(costPrice * baseQuantity,2)|373|373|
|costPrice = TRUNCATE_TOWARD_ZERO(costAmount / baseQuantity,6)|373|373|
|costPrice = ROUND(LatestCost,2)|287|48|

ROUND由Python Decimal ROUND_HALF_UP验证；TRUNCATE_TOWARD_ZERO由ROUND_DOWN验证。关系匹配并不能证明T+内部执行顺序。成本金额及成本价两式同时成立，不能据此断言是先取单价还是先取金额。
毛利金额向零截断仅146/287条匹配，毛利率向零截断仅153/287条匹配；不能套用当前导入销售金额的向零截断规则。
样本不能证明所有版本、所有账套使用相同精度，尤其无法覆盖多单位、外币、成本调整及所有退货场景。

## 用户数值的复算

本地未命中costPrice=22.12或LatestCost=22.12159222的明细，因此以下是数值关系推导，而非找到原单据后的核实。

假设quantity=baseQuantity=1：

- 无税单价P=22.12159222+13.27663787=35.39823009。
- 若含税单价为40，税率为13%，ROUND(40/1.13,8)=35.39823009，能一致复现P；40及13%仍须由原单据确认。
- 单品毛利=35.39823009-22.12159222=13.27663787。
- 参考毛利=ROUND(13.27663787*1,2)=13.28。
- 毛利率=ROUND(13.27663787/35.39823009,4)=0.3751，即37.51%。
- 实际成本金额22.12，基本数量1，对应成本价TRUNCATE_TOWARD_ZERO(22.12/1,6)=22.12。
- 本例ROUND(LatestCost,2)=22.12，但此关系只在本地287条可比记录中匹配48条，不能当通用成本价公式。
- 若先把毛利金额舍入成13.28再除无税单价，四舍五入四位得到0.3752，和原值不符。

## 成本来源与本地缺口

字典字段名页C13303:D13304定义SA_SaleDelivery_b.costAmount=成本金额、costPrice=成本价。
字典未收录该表LatestCost、SingleInvGrossProfit、GrossProfit、GrossProfitRate；其含义由本地数据关系及官方界面规则交叉解释，不宣称字典已直接定义。

AA_Inventory在字典中的invSCost为参考成本，latestCost为最新成本，valueType为计价方式。
实际本地AA_InventoryEntity对应旧列为latestCost_Abandon、avagCost_Abandon。373条匹配存货的invSCost及两个旧列全部NULL；valueType全部199，但本次未验证枚举名称。

ST_RDRecord、ST_RDRecord_b、ST_SubsidiaryBook、ST_AssistantDataBook、ST_SummaryBook、ST_NewCurrentStock、st_marketingorganinvprice均以COUNT_BIG核实0行。
所以本地目前可验证已保存成本与毛利关系，不能从这些空表重新还原原始成本来源。

官方规则将实际出库成本与销售单位结存成本分开：后者按营销机构及核算计价模式取当前时点结存成本，并转换销售单位与币种；后者是参考毛利基础，不保证等于实际出库成本。
候选来源应区分：实际成本查对应出入库明细及成本账；参考成本查按计价维度的结存数据。ST_CurrentStock在字典中属于结存数据，实际库有ST_NewCurrentStock等新结构，尚不能给出一条已验证可用的来源JOIN。
不能直接把st_marketingorganinvprice.latestCost、AA_InventoryEntity.invSCost按同名或名称相近替代销货明细LatestCost。

## 官方参考

- https://t.static.chanjet.com/helpfiles/Cloud/StdPro/WebHelp/Content/SA/SaleOrder.htm （销售单位结存成本、参考毛利公式）
- https://t.static.chanjet.com/helpfiles/Cloud/StdPro/WebHelp/Content/SA/Sale.htm （实际成本价、成本金额及手工确定成本）
- https://t.static.chanjet.com/helpfiles/Cloud/StdPro/WebHelp/Content/ST/STData/SaleOut.htm （出库金额及成本调整）

## 复核材料

- tools/analyze_cost_fields.py：只读取数工具，限制本机指定账套。
- tools/check_cost_formulas.py：Decimal关系验证。
- outputs/cost_fields_raw.txt：元数据、匹配结果和373条成本明细。
- outputs/cost_formula_verification.txt：公式全量匹配统计。
- outputs/cost_inventory_raw.txt：存货成本列核验。

## 官方资料补充检索（2026-10-22）

### 录单参考成本与实际计价成本

官方《库存单据的单价带出规则》明确区分：录单默认带出结存成本，单据生效时按计价方式计算准确出库成本并更新默认成本；手工确定成本行不重新计算。这解释了为什么销售参考毛利用的结存成本与实际出库成本可能不同。该解释属于官方业务机制，不构成对本地任一差异记录成因的逐单确认。

来源：https://t.static.chanjet.com/helpfiles/Cloud/StdPro/WebHelp/Content/ST/Special/STDataPriceOutRule.htm

### 计价模式与计价方式

- 计价模式为“仓库+存货”时，各仓库分别计价；为“存货”时，将各仓库业务合并计价。批号与计价法联用时还需要批号。
- 移动平均：每次入库后以结存总金额/结存总数量确定新的平均单位成本，发出按当时平均成本。
- 全月平均：单位成本=(月初成本金额+本月入库成本金额)/(月初数量+本月入库数量)。
- 先进先出：按入库先后分层耗用，出库成本金额为各耗用层数量乘该层成本的总和。
- 个别计价：由指定入库单对应的实际成本确定。
- 零成本或负成本、退货无来源单等场景还要按账套选项处理，不能简单套平均数。

来源：
https://t.static.chanjet.com/helpfiles/Cloud/StdPro/WebHelp/Content/ST/Special/PriceMode.htm
https://t.static.chanjet.com/helpfiles/Cloud/StdPro/WebHelp/Content/ST/Special/PriceFashion.htm

### 客户档案与存货档案

客户（往来单位）档案可查客户价格等级、税率等；前者参与销售价格策略，后者在相应取税率规则下影响无税单价，所以会间接影响毛利。普通库存计价模式并不以客户作为成本分组维度，不能仅由客户档案计算结存成本。

存货档案库存信息可显示参考成本、最新成本、平均成本：参考成本由用户维护，最新成本和平均成本由系统计价维护。最新成本取最近发生结存成本变化的仓库时点；平均成本为各仓库结存金额合计/数量合计。因此档案最新成本、档案平均成本、特定仓库结存成本与历史销货明细LatestCost不能无条件等同。

来源：
https://t.static.chanjet.com/helpfiles/Cloud/StdPro/WebHelp/Content/AA/CommonInfo/CandGArchives.htm
https://t.static.chanjet.com/helpfiles/Cloud/StdPro/WebHelp/Content/AA/CommonInfo/SaveArchives.htm

前述空表结论仅针对本机UFDATA_999_1015，不代表用户正在使用的T+账套没有相应数据；未核验T+前台当前连接的实际服务器和账套。

### 前台可核实的证据链

同一商品编码、营销机构、仓库和单位下，查看存货档案的计价方式、系统核算选项的计价模式，以及库存明细账的结存数量、结存金额和结存单价；与销货单保存的销售单位结存成本及关联出库成本对照。客户档案用于核对售价策略、税率；不能替代库存账取数。
官方帮助没有承诺上述业务栏目的数据库物理表字段及SQL接口，具体映射须在目标版本的实际账套核实。

## 线上五组数据的逐笔核验：SA2026102200001

证据：用户提供的线上查询文字结果；未直接连接线上。账套UFTData235382_300216，存货28094（C0086，山楂茯苓颗粒），仓库12，营销机构1，单位23，汇率1，计价方式199经枚举联查确认为移动平均。

### 业务关联已对齐

- 销货单1586744，明细5570141，类型104。
- 出入库单1987818（IO2026102200001），明细6980446，类型19；sourceVoucherId/sourceVoucherDetailId/idsourcevouchertype分别1586744/5570141/104；合并流程来源也一致。
- 库存明细账5646383：voucherID/voucherDetailID/idvouchertype分别1987818/6980446/19；voucherIDFlowUnite/voucherDetailIDFlowUnite/idvouchertypeflowunite分别1586744/5570141/104。存货、仓库均一致。
- r.saleDeliveryId/saleDeliveryCode为空不意味着无关联；本例真实关联在出入库明细来源字段和库存账合并流程字段。

### 六字段精确数值关系

库存账outPrice=22.12163433，outQuantity=1，outAmount=22.12；出入库明细price/basePrice/amount均22.12；销货明细costPrice/costAmount均22.12，LatestCost=22.12163433。

设P=35.39823009，C=22.12163433，Q=1，则：

- ROUND(C*Q,2)=22.12，吻合库存账outAmount、出库明细amount及销货costAmount。
- 销货costPrice=出库明细basePrice=22.12，亦吻合TRUNCATE_TOWARD_ZERO(22.12/1,6)。不能将其直接等同库存账outPrice。
- P-C=13.27659576，等于SingleInvGrossProfit。
- ROUND((P-C)*Q,2)=13.28，等于GrossProfit。
- ROUND((P-C)/P,4)=0.3751，等于GrossProfitRate。

### 出库前成本与出库后结存

202610汇总行1111293：finalQuantity=1339，finalAmount=29620.87。
将本次出库1件、22.12元加回：

    (29620.87+22.12)/(1339+1)
    =29642.99/1340
    =22.121634328358208955...
    ROUND(...,8)=22.12163433

精确吻合本次库存账outPrice及销货LatestCost。出库后：

    29620.87/1339=22.121635548917...
    ROUND(...,8)=22.12163555

与查询返回的期末结存单价吻合。金额按两位处理后导致结存单价细微变化，与本例数值一致。
这是强数值吻合，但“加回本笔即得出库前余额”要求汇总快照与本次交易时点对应且没有其他后续变动。未提供完整流水，不能把此逆推当作一般历史取数算法；线上通用SQL仍需从真实记账顺序重建出库前余额，或取得原始成本快照。

### 库存数量不同步问题

ST_NewCurrentStock仓库12数量1335，而ST_SummaryBook同仓库同期间finalQuantity1339，相差4。
当前库存行updated=2026-10-22 17:31:45，本次库存账AccountTime=20:11:20.570。不同表更新时间不构成错账证明，但现有结果不能认定两表属于同一快照/相同统计范围。
不得把汇总账29620.87除以当前库存1335；该混算得到22.18791760，不等于本次成本。
下一步若需通用成本生成SQL，应确认计价模式、汇总账isAccount口径、记账任务状态及目标前后流水；不能仅按业务日期或任意TOP 1选择成本。
