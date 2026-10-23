# Win7 打包记录与下次构建步骤

记录日期：2026-10-21。范围：本目录的 TplusSalesImport，不是根目录 HIS 工具。

## 下次构建使用的基线

- 使用官方 CPython **3.8.10 x64**，不要使用终端中未确认来源的 `python`。
- 当前构建机解释器：`E:\Python38\python.exe`（此前另一台机器的路径为 `C:\Users\55301\AppData\Local\Programs\Python\Python38\python.exe`）。
- Qt 实际 DLL 版本为 **5.15.2**；PyQt5 绑定为 **5.15.11**。
- PyInstaller **6.17.0**，hooks **2025.11**，pyodbc **5.2.0**，xlrd **2.0.1**。
- 依赖版本快照见 `../requirements-win7-build.txt`，包含本机打包时可见的相关间接依赖及可选依赖，不是整个全局环境的 pip freeze。
- `.build_env_win7/` 是本机生成环境，已加入 `.gitignore`。不提交、不随程序分发，也不复制到其他机器使用。

当前构建机 `.build_env_win7` 是独立环境，不使用 `--system-site-packages`，依照锁定清单安装依赖。此前另一台机器曾复用外层Python38依赖；该环境未被复制。其他机器必须自行重建环境，版本快照不等于Win7实机兼容性保证。

## 其他机器首次准备

安装官方 Python 3.8.10 x64，进入 `tplus_sales_import` 目录。将下面的解释器路径替换为实际安装路径。新环境不使用 `--system-site-packages`：

```powershell
$python38 = 'E:\Python38\python.exe'
& $python38 -c "import sys, struct; assert sys.version_info[:3] == (3, 8, 10); assert struct.calcsize('P') == 8; print(sys.executable, sys.version)"
& $python38 -m venv .build_env_win7
& .\.build_env_win7\Scripts\python.exe -m pip --isolated install -r requirements-win7-build.txt
```

任一步失败应停止，先处理失败原因，不要继续使用另一套默认 Python 打包。

## 构建时隔离无关 DLL 搜索路径

在专门的新 PowerShell 窗口执行。以下环境变量变更仅影响这个窗口及子进程：

```powershell
$python38 = 'E:\Python38\python.exe'
$pythonRootPath = Split-Path -Parent $python38
$env:PATH = "$pythonRootPath;$pythonRootPath\DLLs;$env:SystemRoot\System32;$env:SystemRoot"
$env:PYTHONHOME = $null
$env:PYTHONPATH = $null
& .\.build_env_win7\Scripts\python.exe build_app.py
```

输出为 `dist/TplusSalesImport/`。分发整个文件夹，包含 `_internal/`。程序位数和目标 ODBC 驱动须匹配；本基线是 x64，不适用于 32 位 Win7。

`build_app.py` 会保留已有发布目录的配置、logs、runtime。它没有添加 `--clean`；切换解释器、依赖或 DLL 搜索路径时，应在新的源码工作目录构建，避免复用旧构建产物。需要用已生成的 spec 做 `--clean` 构建时，应选择独立输出目录，并补齐 `config.ini.example`、无密码 `config.ini` 和 README；直接调用 spec 不会执行 `build_app.py` 的配置及运行数据保留逻辑。

本次首轮发现 Anaconda 的 API/CRT DLL 被 PATH 带入，随后清理 PATH 并使用 spec 的 `--clean` 重建。不能只检查 Python 版本而忽略 DLL 来源。

## 验证与发布

1. 检查构建记录实际使用 Python 3.8.10 x64，确认 `Analysis-00.toc` 中没有 Anaconda 来源的文件。
2. 检查 EXE、DLL、PYD 的普通导入和延迟导入，确认没有引用 `api-ms-win-core-path-l1-1-0.dll`；这不能排除所有其他兼容性问题。
3. 在无 Python/Anaconda 搜索路径的环境运行离线自检：

   ```powershell
   $env:PATH = "$env:SystemRoot\System32;$env:SystemRoot"
   $env:PYTHONHOME = $null
   $env:PYTHONPATH = $null
   $process = Start-Process -FilePath '.\dist\TplusSalesImport\TplusSalesImport.exe' -ArgumentList '--self-test', "$PWD\.validation\win7_smoke" -WindowStyle Hidden -PassThru -Wait
   $process.ExitCode
   Get-Content .\.validation\win7_smoke\smoke_result.json
   ```

   退出码应为 0，JSON 中 `passed=true`、`database_connections=0`、`database_writes=0`。自检会生成示例界面与 XLSX，不连接数据库。
4. Win7 实机验证正常界面、真实 XLS 读取、XLSX 导出、ODBC 连接；业务导入在测试账套验证。Win11 自检通过不能替代 Win7 实测。
5. 发布包只包含运行文件和无密码配置，不包含虚拟环境、真实业务日志、任务结果或凭据。核对 ZIP 完整性并记录 SHA-256。

## 本次构建证据

- 使用以上 Python 3.8.10、Qt 5.15.2 基线。
- 清理 PATH 后构建成功，70 个 PE 文件未发现上述 core-path DLL 的普通或延迟导入引用，构建记录没有 Anaconda 来源。
- 离线自检通过，数据库连接和写入次数均为 0。
- 当时发布文件：`releases/TplusSalesImport_Win7_x64_Python3810_20261021.zip`。
- SHA-256：`699cb965ed8f3224fca01d13bd0c4e3857f8a23dfb21a8e68a260b5d3baab285`。
- 本机详细记录保存在忽略目录 `.validation/win7_build/`；Git 中保留本说明和版本快照，其他机器不依赖该忽略目录。
- 截至本记录，未收到 Win7 实机通过的明确反馈；不将此包标记为已完成 Win7 验收。

## 2026-10-21 20:02 发布记录

- 已包含当前会话撤销导入、票据类型281、收款方式7、结清状态428、表头折扣率1/折扣金额0，以及AuditedTime等于createdtime。
- 当前机器以官方Python 3.8.10 x64建立独立环境，Qt 5.15.2、PyInstaller 6.17.0；147项测试在此Python3.8环境全部通过。
- 使用全新的隔离源码/构建目录和清洁PATH；不复用原Python3.10构建目录，也未覆盖原dist中的配置与任务数据。
- 70个PE文件的普通及延迟导入检查通过，无api-ms-win-core-path-l1-1-0.dll导入，全部为x64；Analysis-00.toc未包含Anaconda来源。
- 打包程序在移除Python/Anaconda搜索路径后离线自检通过，未连接或写入数据库；ZIP完整性及无密码示例配置检查通过。
- 发布包：`releases/TplusSalesImport_Win7_x64_20261021_200205.zip`，39.07MB、159个文件。
- SHA-256：`160ac9a7eccbc599154275a26e6c5200bcd5945e774327216b9f07aa7a932096`。
- 证据：本机忽略目录`.validation/latest_win7_release.json`及`.validation/win7_build_20261021_200205/`。
- 目标为Win7 SP1 x64测试部署；尚未进行Win7实机验收，此x64包不适用于32位Win7。

## 2026-10-21 20:39 发布记录

- 新增表头origprereceiveamount、PreReceiveAmount、origSettleAmount、settleAmount显式默认Decimal(0)，其他规则沿用20:02版。
- Python3.8独立环境151项测试通过；全新隔离构建、70个PE文件检查、发布程序离线自检及ZIP完整性/无密码配置核验通过，未连接或写入数据库。
- 发布包：`releases/TplusSalesImport_Win7_x64_20261021_203938.zip`，39.07MB、159个文件。
- SHA-256：`2c3c75fe81d071d41a8ecc587be8c86004421845f68fed1bfa9da020b57f7c8b`。
- 证据：`.validation/latest_win7_release.json`及`.validation/win7_build_20261021_203938/`。Win7实机尚待验收。

## 2026-10-21 20:57 发布记录

- 表头isNoArapBookkeeping新增显式默认0，与原77条样本一致；不自动更新存量，凭证实际取科目仍需在T+中验证。
- Python3.8环境152项测试通过；70个PE文件检查、无Python/Anaconda搜索路径的打包程序离线自检及ZIP核验通过，未连接数据库。
- 发布包：`releases/TplusSalesImport_Win7_x64_20261021_205711.zip`，39.07MB。
- SHA-256：`14278e362d233a071c626b7909362eec065ff539387895f13ba3469aa47ea1cc`。
- 构建证据：`.validation/latest_win7_release.json`及`.validation/win7_build_20261021_205711/`。Win7实机尚待验收。

## 2026-10-21 21:00 发布记录

- 表头pubuserdefnvc1改为空字符串，不再映射操作员，取消同单操作员差异阻断；明细用友单号映射不变。
- Python3.8环境152项测试及发布包离线自检通过，70个PE文件检查和ZIP脱敏核验通过，未连接数据库。
- 发布包：`releases/TplusSalesImport_Win7_x64_20261021_210008.zip`，39.07MB。
- SHA-256：`5e37403b0cc633a012b94e2bbe41645c5f62ea08d1b2ae35767cd3e575e6fac3`。
- 构建证据：`.validation/latest_win7_release.json`及`.validation/win7_build_20261021_210008/`。Win7实机尚待验收。

## 2026-10-21 22:02 发布记录

- 加入表头SaleInvoiceMedia=51014、DistributionMode=57419、saleInvoiceID=281、LogisticsStatus=56134，并补齐用户确认的12项表头和6项明细零值标记。
- Python3.8环境174项测试通过；70个PE文件检查、发布包离线自检及ZIP完整性/无密码配置核验通过，未连接数据库。
- 发布包：`releases/TplusSalesImport_Win7_x64_20261021_220208.zip`，39.07MB、159个文件。
- SHA-256：`e6ef611d63f7383c8f1b97a8eb012f1efd7a0e71c794c5db9bc564c44de4b2ea`。
- 构建证据：`.validation/latest_win7_release.json`及`.validation/win7_build_20261021_220208/`。Win7实机尚待验收。

## 2026-10-21 23:04 最新发布

- 新增表头OrigInvoiceTaxAmount、Allowances、origAllowances、thisBalanceIntegral显式写Decimal(0)；明细saleOutQuantity写本行quantity，保留负数、零及小数，不额外生成出库单。
- Python3.8环境179项测试通过；70个PE文件检查、发布程序离线自检及ZIP完整性/无密码配置核验通过，未连接数据库。
- 发布包：`releases/TplusSalesImport_Win7_x64_20261021_230419.zip`，39.07MB、159个文件。
- SHA-256：`1b7f5579f2c1947041bd6b024a906c415e05e505acbe96d22815155807c4db9d`。
- 构建证据：`.validation/latest_win7_release.json`及`.validation/win7_build_20261021_230419/`。Win7实机尚待验收。


## 2026-10-23 Authorization 签名构建

本轮增加 OpenAPI v2 的 PS256 签名。构建环境新增 cryptography 3.4.8、cffi 1.17.1、pycparser 2.23，版本已写入 requirements-win7-build.txt；源码通用依赖清单也已加入 cryptography。

使用 Python 3.8.10 x64 独立环境完成打包，源代码测试247项通过、1项跳过。构建后的 EXE 在清除 Python/Anaconda 搜索路径后离线自检退出码0，authorization_signing=true，数据库连接/写入均为0。74个PE文件未发现 api-ms-win-core-path-l1-1-0.dll 普通或延迟导入。以上为本机验证，尚未进行本轮 Win7 实机验收。

产物为 dist/TplusSalesImport/TplusSalesImport.exe，config.ini 与 cjet_pri.pem 同在 EXE 旁，私钥不放在 _internal；重新打包保留现有配置及配套私钥。此次本地目录按用户要求包含实际配置及私钥，不应作为无凭据公共示例包发布。
