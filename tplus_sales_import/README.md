# T+ 销货单导入（独立程序）

新程序、测试、配置、打包及运行数据均放在本目录；未改原HIS/凭证程序。

## 启动

源码运行：在本目录执行 `python main.py`。依赖安装：`python -m pip install -r requirements.txt`。
打包：`python build_app.py`，生成 `dist/TplusSalesImport/TplusSalesImport.exe`。分发整个TplusSalesImport文件夹，不单独复制exe。SQL Server ODBC驱动须在运行电脑已安装，位数与Python/程序一致。

手动修改程序旁的 `config.ini`，配置 `[sqlserver]` 中 `ip`、`port`、`database`、`user`、`password`；`driver`可指定已安装ODBC驱动。SERVER由ip和port组合，DATABASE使用database，UID使用user，PWD使用password。提供的配置不包含密码，请填入实际值。不要把实际config.ini提交到版本库。

主页面只读显示服务器、用户和目标账套，密码隐藏。点击“测试连接/重新读取配置”后，测试实际目标数据库；数据库切换不再读取原程序另一份build_db/test_db。测试连接为可选操作；点击导入会重新读取配置并自动连接，运行中的任务保持启动时的配置快照。

## 操作

1. 按需测试目标账套连接，可跳过此步。
2. 选择与10.12A出.xls列结构一致的真正XLS；支持单文件的多个工作表，在表格查看全部源明细。预览只读；筛选不改变“导入全部数据”的范围。
3. 文件加载后即可点击导入，无需先测试连接：后台自动读取配置、连接账套、缓存档案、校验并标记问题，再按主表ExternalCode中的源用友单号去重。已存在整单跳过，即使新文件同号内容变化也不更新旧单。
4. 正常完整单据批量提交。一个表头和所有明细同事务，数据错误拆分定位坏单，其他正常单据继续。
5. 任务结束自动在源XLS同文件夹保存异常结果XLSX（含汇总、失败及未处理、重复跳过、成功但有说明）。全部失败和停止也输出。全部成功无说明时仍保留汇总文件。
6. 停止按钮等待当前批次提交或回滚，保留已提交，余下未处理；不强杀线程，不等于撤销全部导入。关闭运行中的窗口使用同样停止流程。

结果不可写时显示失败，内存与runtime日志保留；可重试导出或另存为。“另存为”还包含全部结果页。源目录在开始写入前检查可写性。任务报告含业务原始数据，请按业务文件妥善保存。

## 已实现的业务口径

- 主表SA_SaleDelivery、明细SA_SaleDelivery_b，两表自增ID。按源用友单号去重，新SA编号按源单据日期取当日最大五位流水递增。
- 客户AA_PartnerEntity.code同时带出客户/结算客户ID；客户taxRate关联eap_EnumItem后解析Name，不按枚举ID推算税率。名称13、17及13%按百分数转换为0.13、0.17；0至小于1的数值保留为比例，1至100按百分数（1代表1%，100代表100%）。缺失、非数值、负数及超范围税率标记失败。
- 存货AA_InventoryEntity.code，单位用idunit关联AA_Unit；只支持已确认的单计量口径，不取规格末字。quantity与单位名称组成数量说明，零数量退货保留。
- 仓库按AA_Warehouse.code匹配，各行可不同。项目按AA_Project.Code，表头明细同步；不存在时NULL并留说明，重复候选或停用失败。
- 源15→普通销售65，源16→退货66。制单/审核人员范立志、ID51；状态189；币种4、营销机构1、部门和业务员NULL、类别24。业务日期为源单据日期，系统时间为操作时间。
- isAutoGenerateSaleOut、IsAutoSaleOut均1；不执行生成出库单，不生成发票和凭证、不调用审核接口。
- 源含税金额G以Decimal原值写入，不截断、不四舍五入；N=四舍五入(G/(1+r),2，ROUND_HALF_UP)；T=G-N，税额保留差额所需的小数位，保证G=N+T，正负采用同一规则，表头汇总最终明细。原含税单价保留，折扣率1；数量非零时未税单价=四舍五入(G/数量/(1+r),8)。零数量继续导入，未税单价使用源单价/(1+r)四舍五入8位，避免除零；不为零金额自动设置0.0001单价。目标字段容纳不了原值精度时标记整单失败，不静默改金额。
- 明细taxFlag=1、isModifiedPrice=1；表头和明细显式写入DataSource=2497、isSaleOut=15，并参与写入核对。这些字段不执行生成出库单、发票或凭证的业务操作。新版规则仅用于后续导入，已有单据仍按源用友单号跳过，不自动更新历史金额或标记。
- 表头agency=范立志、agencyid=51、isCarriedForwardOut=0；明细RefundDifferenceFlag=51185。提交前与断线恢复核验覆盖全部已配置表头业务字段（排除实际创建/更新时间），并核对日期与所有明细配置字段。
- 明细同时保存两组源追溯字段：priuserdefnvc2/pubuserdefnvc1均为用友单号，priuserdefnvc3/pubuserdefnvc2均为该行销售标识；四个字段均参与字段精度校验和提交前核对。表头pubuserdefnvc1固定写空字符串，不再映射源“操作员”，同单操作员不同不阻断导入；固定制单/审核/经手人沿用原配置。
- 原币与本币按样本exchangeRate=1填写；本程序限定该账套样本口径，未实现外币汇率转换。目标固定配置、数据结构及人员档案缺失时不执行写入。

## 恢复与限制

runtime下保存无密码任务JSON，含原行、结果和写入意图；写入前先保存待确认状态，提交成功后保存结果。连接/提交应答异常会重连查询源单号并核对主明细；无法确认保持待确认，不盲目重插。确认未提交的部分本次停止写入，修复连接后重选源文件导入即可重新去重。

“恢复任务结果”读取runtime中的JSON，可以查看与重新导出；不自动恢复数据库写入，不把待确认改成成功。进程崩溃后重跑仍依目标表源单号判重。运行时用账套进程锁避免本机同用户重复导入；仍依赖已确认的“没有其他服务或事务写入目标表”前提，不宣称支持多机并发。

数据库需开放查询档案、目标表元数据、临时表和主明细写入所需权限。程序不自动创建索引、不新建业务档案、不修复历史残缺单据。千万级目标表需部署方评估ExternalCode索引，当前程序不承诺未经压测的耗时。

本地账套此前eap_EnumItem、EAP_User、AA_Currency、AA_MarketingOrgan为空。这些数据不补齐，真实导入会被预检或逐单校验阻止；测试连接成功不代表可以导入。T+页面对审核字段的解释及销售出库标志1是否产生后续自动动作，需在隔离测试账套验证。本轮开发测试不写实际数据库。

设计与历史证据见docs/technical_solution_import_dedup.md。金额/主键/事务、线程和模拟数据库测试见tests。运行测试：`python -m pytest tests -q`；不要将测试主机配置改成实际连接，测试使用FakeRepository。


## 本机打包环境及验证

Win7 打包优先使用 [Win7 构建记录与步骤](docs/win7_build.md) 及 `requirements-win7-build.txt`：官方 Python 3.8.10 x64、固定依赖版本，并清理 Anaconda 等无关 DLL 搜索路径。`.build_env_win7/` 仅本机使用，其他机器按说明重建，不复制虚拟环境。

当前Anaconda含冲突的旧pathlib分发包，没有卸载或修改全局环境。已在本目录.build_env中离线构造独立打包环境，并生成EXE。如需在相同环境重建，可执行：

```powershell
python prepare_build_environment.py
.\.build_env\Scripts\python.exe build_app.py
```

测试依赖可按requirements-dev.txt安装。当前机器第三方pytest插件会阻塞自动加载，验证时使用：

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$env:QT_QPA_PLATFORM='offscreen'
python -m pytest tests -q
```

EXE自检：`TplusSalesImport.exe --self-test 输出目录`，只创建示例界面、示例结果表及JSON验证记录，不连接数据库。自检文件是示例，不能作为真实导入结果。

构建结果及剩余联调范围见BUILD_STATUS.md。发布版config.ini首次创建自无密码示例；重新打包保留已有发布目录中的config.ini、logs及runtime。请勿在修改配置时启动导入。


## 运行日志

沿用项目log_util.py的logger接口和“时间 - 级别 - 模块 - 消息”格式，独立目录保留一份适配工具，不修改旧程序的日志工具。新增task任务编号关联同一导入的各阶段。源码运行日志在本目录logs/appYYYY-MM-DD.log；EXE运行日志在EXE旁logs/appYYYY-MM-DD.log。持续跨日运行时自动切换日期文件，命令行运行还输出到控制台。

记录连接测试结果及耗时、XLS加载行数/单据数、各档案缓存条数、校验/去重汇总、日期编号起点、批次提交/回滚/拆分/重试、坏单定位、停止及提交结果恢复、结果导出位置和最终统计。正常路径不逐行输出，也不打印SQL参数、原始业务行、密码或完整连接串。异常保留类型、SQLSTATE、数据库错误编号和调用位置，不直接打印含连接凭据的驱动异常值。详细逐行问题仍在异常结果表和任务JSON中。


### 解释器不同导致缺依赖

项目IDE当前使用E:/Python38/python.exe，终端默认python可能指向另一个环境。依赖必须安装到实际运行解释器；2026-10-17已在E:/Python38离线补装xlrd 2.0.1，并成功读取真实源XLS。后续缺依赖时，界面及日志会显示模块名与实际解释器路径。不要仅在另一个环境执行pip后认为IDE环境已同步。

导入按钮仅要求文件成功加载且当前没有其他任务运行；界面单独显示导入就绪条件与可选连接测试状态。配置有语法错误时按钮仍可点击，但会提示先修正配置，不会开始写入。

连接诊断：每次测试连接或开始导入连接前，日志打印当前进程位数及pyodbc可见的全部ODBC驱动；配置驱动不在列表中则额外提示核对驱动名称和位数。该列表不触发数据库查询，也不会自动替换用户配置的驱动。

窗口启动尺寸：按鼠标所在屏幕的可用宽度与高度各取2/3，居中普通显示，不自动最大化；多屏使用所在屏幕坐标，高DPI由Qt逻辑尺寸适配。按钮分两排，小屏幕内容超出时可滚动，窗口仍可手动缩放。

销货单表头默认写入invoiceType=281（专用发票）、reciveType=7（其它），不自动生成发票。导入前一次性检查eap_EnumItem中的两个ID唯一存在、类别分别为56/41且未删除；异常则阻止本次导入并提示。两个字段参与提交前回查及提交结果恢复核验，已有单据仍按去重规则跳过。

按2026-10-21用户确认的线上样本，表头同时固定写入SaleInvoiceMedia=51014、DistributionMode=57419、saleInvoiceID=281、LogisticsStatus=56134。四个字段参与既有表结构/类型校验、提交前回查及提交结果恢复核验；不向明细写入，不更新已有单据，不调用生成发票流程。

当前导入普通销售/普通销售退货，表头显式写0：isCounteractDelivery、isPriceTrace、isBeforeSystemInuse、iscarriedforwardin、ismodifiedcode、PrintCount、IsSeparateByWareHouse、IsAutoWarehouse、SendInfoSource、IsReadOnly、IsDigElectronicInvoice、IsOnlinePay；明细显式写0：isPresent、isManualCost、IsMemberIntegral、IsPromotionPresent、DiscountPriceChange、TaxPriceChange。与线上SA2026102000001样本一致，参与提交前及恢复回查，NULL不视为0。isCounteractDelivery指冲抵销货，普通退货仍为0；iscarriedforwardin指是否结转来的单据。零金额/零数量不自动标记赠品；保留isModifiedPrice=1，不据此改变两个价格改动标记。不自动计算成本、追踪更新售价或生成支付/发票记录。

表头OrigInvoiceTaxAmount、Allowances、origAllowances、thisBalanceIntegral按线上样本及用户要求显式写Decimal(0)，参与表结构/精度校验和提交、恢复回查；NULL不视为0。仅用于后续新导入，不更新已有数据，不扩展到明细。这是默认值补齐，尚未证明可解决凭证生成预收账款的问题。

按用户要求，明细saleOutQuantity直接写本行源数量quantity（销售单位），保留负数、零及小数精度，不取绝对值，不使用整单合计。参与提交及恢复回查。该字段记录累计出库数量，赋值本身不生成出库单或库存流水，不自动更新已有单据。

表头isCancel默认写入428（eap_EnumItem名称“未结清”，即未清算状态），不按0/1布尔值处理。导入预检要求该枚举唯一存在、idEnum=16且未删除；该字段参与提交前回查和恢复核验。

表头AuditedTime与createdtime使用同一个实际创建时间写入。回查及提交结果恢复时核验数据库中两者非空且相等，避免重建载荷时取新时间产生误判；auditeddate继续使用源单据日期。

表头origprereceiveamount、PreReceiveAmount、origSettleAmount、settleAmount均显式写入Decimal(0)，表示本次导入未使用预收且未结算。四个字段参与表结构/精度校验、提交前回查及提交结果恢复核验，NULL不视为0。明细对应结算字段及表头ReceiveBalance仍沿用原规则。

表头isNoArapBookkeeping显式默认0，与原77条线上样本一致，参与表结构校验及提交前、提交结果恢复核验，NULL不视为0。不自动补写已有单据；此字段对凭证取科目的实际影响须在T+中验证。

“撤销本次导入”只在当前应用会话的最新导入任务包含已确认成功单据时启用。部分成功或停止后已提交的部分也可撤销，但存在待确认提交则禁用。点击后先后台核对，二次确认窗口列出服务器、账套、源文件、任务、两张表名称及数量、每张单据的表头ID/SA编号/用友单号/明细数；取消不删除。

确认后按本次回收的主键ID定位，同一事务先删SA_SaleDelivery_b再删SA_SaleDelivery；校验已配置业务字段和确认前后的整行摘要（含明细ID及数据库版本字段），不一致则拒绝删除。启用的触发器或级联外键会阻止撤销，普通外键约束失败则整笔回滚，不额外删除其他业务表。成功后状态改为“已撤销”，保存任务结果并重新导出。提交/回滚结果不明则标记“撤销待确认”并禁用，需人工核实，不自动重复删除。

撤销资格仅保存在内存；选择另一个XLS（含重新选择同一文件）、开始新导入、恢复任务结果或关闭应用都会清除资格。取消选择文件不清除；恢复历史任务结果不会恢复删除权限。撤销始终使用本次导入时的连接配置；不更新重复跳过的数据，不重置自增主键或修改已分配编号。
