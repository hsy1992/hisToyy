# Win7 打包记录与下次构建步骤

记录日期：2026-10-21。范围：本目录的 TplusSalesImport，不是根目录 HIS 工具。

## 下次构建使用的基线

- 使用官方 CPython **3.8.10 x64**，不要使用终端中未确认来源的 `python`。
- 本机解释器：`C:\Users\55301\AppData\Local\Programs\Python\Python38\python.exe`。
- Qt 实际 DLL 版本为 **5.15.2**；PyQt5 绑定为 **5.15.11**。
- PyInstaller **6.17.0**，hooks **2025.11**，pyodbc **5.2.0**，xlrd **2.0.1**。
- 依赖版本快照见 `../requirements-win7-build.txt`，包含本机打包时可见的相关间接依赖及可选依赖，不是整个全局环境的 pip freeze。
- `.build_env_win7/` 是本机生成环境，已加入 `.gitignore`。不提交、不随程序分发，也不复制到其他机器使用。

本机现有 `.build_env_win7` 使用 `--system-site-packages`，复用外层已使用的 Python38 依赖，单独补装 xlrd。其他机器必须自行重建环境；新的独立环境尚未在另一台机器验证，版本快照不等于 Win7 兼容性保证。

## 其他机器首次准备

安装官方 Python 3.8.10 x64，进入 `tplus_sales_import` 目录。将下面的解释器路径替换为实际安装路径。新环境不使用 `--system-site-packages`：

```powershell
$python38 = 'C:\Users\55301\AppData\Local\Programs\Python\Python38\python.exe'
& $python38 -c "import sys, struct; assert sys.version_info[:3] == (3, 8, 10); assert struct.calcsize('P') == 8; print(sys.executable, sys.version)"
& $python38 -m venv .build_env_win7
& .\.build_env_win7\Scripts\python.exe -m pip --isolated install -r requirements-win7-build.txt
```

任一步失败应停止，先处理失败原因，不要继续使用另一套默认 Python 打包。

## 构建时隔离无关 DLL 搜索路径

在专门的新 PowerShell 窗口执行。以下环境变量变更仅影响这个窗口及子进程：

```powershell
$python38 = 'C:\Users\55301\AppData\Local\Programs\Python\Python38\python.exe'
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
