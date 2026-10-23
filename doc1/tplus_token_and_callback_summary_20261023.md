# T+ Token 认证与快解析回调测试记录

记录日期：2026-10-23。

## 1. 本轮目标与范围

围绕现有 T+ 销货单导入程序排查“始终获取不到 Token”的问题，研究在线授权、软证书和 appTicket 接收方式，并提供独立的操作入口与回调连通测试服务。

用户要求：

- 优先处理认证和 Token，暂不修改现有导入、审核业务流程。
- 新增独立按钮进行在线 Token 操作，保留原认证逻辑。
- 用户不希望采用手动填写 OAuth 回调地址和 code 的操作方式。
- 用户已取得开放平台应用凭据及可复制的软证书字符串，后续关注 appTicket 的获取。
- 在内网本地启动服务，通过快解析映射后进行访问和回调测试。
- 先使用单独文件测试，不接入原导入程序。

本文不记录任何实际 appKey、appSecret、软证书、消息密钥、Token 或回调正文。

## 2. 已确认的上下文

1. 最初使用的应用标识来自账套 `EAP_AccInformation` 的 `PosAppKey`。该信息由用户确认；本轮未直接连接账套查询。
2. 当前真实环境从未成功取得 Token。本轮未拿到现场完整脱敏错误响应，不能确认唯一根因。
3. 后续用户取得了应用 appKey 及其他授权材料，软证书为可复制字符串。未验证它们与实际应用、企业和账套的绑定关系。
4. 内网地址需要通过公网可达入口接收平台服务器推送；用户选择研究快解析内网穿透。

## 3. 原项目认证与官方 Python SDK 的差异

原实现位于 `tplus_sales_import/app/tplus_api.py`，采用内网账号密码及配置的应用凭据认证：

- 依次尝试五个候选本地登录接口。
- 尝试特定用户名替换，以及 Header、Body、Query 参数组合。
- 从顶层或 `data` 下的若干字段提取 Token。
- 业务请求使用 `Authorization: Bearer ...`。
- 只在内存保存 Token 字符串，没有完整有效期和刷新互斥管理。

所参考官方 SDK 的授权码流程则为：

- 基址：`https://openapi.chanjet.com`。
- 授权码换 Token：GET `/auth/getToken`。
- Header 使用 `appKey`、`appSecret`。
- Query 使用 `grantType=authorization_code`、`appKey`、`redirectUri`、`code`。
- 成功响应按 SDK 定义检查 `code=200`，读取 `result.access_token` 及有效期等字段。
- 开放平台业务请求通过 `openToken` 请求头传递访问令牌。

本地回放确认：原解析器不读取 `result.access_token`，会将这种 SDK 结构的成功响应判为获取失败。此结果证明协议结构不兼容，但不证明现场服务实际返回了该结构。

不能把数据库 PosAppKey、本地登录协议和开放平台凭据直接混用，也不能仅修改请求头就认定认证已修复。

## 4. 讨论过的三种认证路线

### 4.1 本地 T+ / RSA PEM 方式

前期参考文章提及 orgId/v2OrgId、RSA 密钥及 `Appserver\config\pubkeys`。

本轮没有取得与现场 T+ 版本匹配的完整协议，因此未实现：

- 本地证书认证请求及签名。
- orgId 的确定表查询或转换。
- 公钥文件命名、绑定与部署。

PEM 是文件封装格式，可能包含公钥、私钥或 X.509 证书，不能仅凭扩展名判断用途。自行生成的 RSA PEM 与自建应用授权获得的软证书字符串不能直接互换。

### 4.2 OAuth 授权码方式

已根据官方 SDK 构造独立窗口，但用户随后表示不希望采用该操作方式。

OAuth 回跳由用户浏览器访问，和平台主动推送消息不是同一种链路。内网地址是否可用于 OAuth，还取决于平台是否允许登记该地址及用户浏览器的访问能力。

### 4.3 自建应用软证书 + appTicket

用户取得的是软证书字符串，讨论路线为：

```text
应用管理员授权取得 certificate
             +
平台消息推送取得 appTicket
             +
对应应用 appKey / appSecret
             ↓
换取 accessToken
             ↓
通过 openToken 调用业务接口
```

公开第三方实现采用：

```text
POST https://openapi.chanjet.com/v1/common/auth/selfBuiltApp/generateToken
Header: appKey / appSecret / Content-Type: application/json
Body: {"appTicket": "...", "certificate": "..."}
```

该请求结构来自公开实现源码，尚未通过现场应用验证，不是本轮已确认适用于所有版本的官方接口契约。不同资料对响应信封和刷新方式存在差异，不能混用；后续须核对当前控制台文档与真实脱敏响应。

appTicket 是短期票据，需要持续更新，不能复制一次后长期写死。推送周期、有效期、消息类型、解密规则和应答格式以应用当前协议为准。

## 5. 快解析方案的可行性

快解析官方资料说明可以把本地 HTTP 服务映射为公网 HTTPS 地址。这在网络结构上能够承载平台推送：

```text
畅捷通平台
    ↓ POST
快解析公网 HTTPS 地址 /chanjet/messages
    ↓ 映射
本机 HTTP 127.0.0.1:18080/chanjet/messages
    ↓
本地接收服务
```

仍须现场验证：

- 当前账号/映射类型是否提供稳定 HTTPS 地址、有效证书及合适公网端口。
- 畅捷通控制台是否接受该域名和端口。
- 如要求可信域名或域名所有权验证，分配域名能否满足。
- POST、路径和请求体是否完整转发。
- 地址验证消息和真实票据消息是否符合应用协议。

访问密码页、验证码和不正确的白名单可能阻挡机器推送。映射目标应为独立消息服务，不是 T+ 业务端口或 SQL Server 端口。

## 6. 已实现内容

### 6.1 独立在线 Token 窗口

文件：

- `tplus_sales_import/app/online_token.py`
- `tplus_sales_import/app/gui.py` 中新增按钮、打开窗口方法和按钮忙碌状态。
- `tplus_sales_import/tests/test_online_token.py`

窗口提供应用凭据、回调地址和授权码输入、后台执行、Token 显示和复制。不会读取原认证配置，不自动将结果接入原导入流程，不保存输入和结果到文件。

**真实联网传输未启用。** 自动审批曾拒绝发送 appSecret 和授权码的补丁，要求明确授权敏感凭据到指定接口的传输。最终代码默认没有网络传输函数；完整填写后仍提示“在线请求尚未启用”。模拟测试通过不代表真实授权成功。

用户后来转向软证书方案，该窗口保留为前期独立工具，尚未改造成软证书取 Token 工具。

### 6.2 单文件回调连通测试服务

文件：

- `tplus_sales_import/callback_probe.py`
- `tplus_sales_import/tests/test_callback_probe.py`

运行文件只依赖 Python 3.8+ 标准库，不依赖原应用、PyQt、数据库或业务配置。

| 路径 | 方法 | 功能 |
| --- | --- | --- |
| `/` | GET | 测试页、快解析映射说明、回调地址复制、POST 测试、接收统计 |
| `/health` | GET | 健康检查，返回 `connectivity_only` 模式 |
| `/api/status` | GET | 测试/回调次数及最近十条元数据记录 |
| `/probe` | POST | 浏览器模拟连通测试，单独计数 |
| `/chanjet/messages` | POST | 接收含非空字符串 `encryptMsg` 的 JSON，并确认传输接收 |

该版本：

- 只记录接收时间、类型、正文大小，记录仅保存在内存。
- 不保存、显示或打印回调正文及凭据。
- 限制请求体大小，拒绝非法 JSON、缺少 `encryptMsg` 等请求。
- 合法形状的回调返回 `{"result":"success"}`，这是连通测试采用的应答，不是来源验证。
- 页面明确显示“尚未解密”和 `ticket_verified=false`。

**尚未实现消息解密、来源验证、真实 appTicket 提取、持续存储或软证书换 Token。回调次数增加不等于取得有效票据。**

## 7. 本地启动与快解析测试步骤

在 PowerShell 执行并保持终端运行：

```powershell
python "D:\project\hisToyy\tplus_sales_import\callback_probe.py"
```

默认测试页：`http://127.0.0.1:18080/`。

自定义端口示例：

```powershell
python "D:\project\hisToyy\tplus_sales_import\callback_probe.py" --port 18081
```

快解析与服务同机时配置：

| 项目 | 示例 |
| --- | --- |
| 映射名称 | 畅捷通回调测试 |
| 内网 IP | `127.0.0.1` |
| 应用程序端口 | `18080`，与启动参数保持一致 |
| 映射类型 | 支持公网 HTTPS 的网站映射 |

若快解析客户端位于另一台局域网电脑，需要使用接收服务主机的内网地址、相应监听设置与网络访问规则。本轮未修改防火墙或公网映射。

映射后操作：

1. 从外部网络使用生成的公网 HTTPS 地址打开测试页。
2. 点击“发送连通测试”，确认浏览器测试计数增加。
3. 复制页面按访问域名生成的 `/chanjet/messages` 地址。
4. 将该公网地址配置到畅捷通消息接收设置。
5. 执行平台测试/等待真实推送，观察回调计数和接收时间。

通过本地 URL 测试只证明本地连通；必须通过公网地址和平台推送分别验证剩余链路。

## 8. 验证记录

- 独立在线窗口及既有认证、审核、连接配置相关测试：本轮此前运行 37 项通过。
- 回调服务真实本机 HTTP 测试：9 项通过，覆盖页面/健康检查、测试与回调分开计数、错误输入、正文不进入控制台、请求大小限制。
- 普通沙箱曾阻止本机回环连接，报 WinError 10013；经允许的本地回环执行后测试通过。
- 回调服务曾在 `127.0.0.1:18080` 启动，健康接口返回正常。运行进程是临时会话，不代表已安装后台常驻服务。
- 未完成快解析公网访问验收、平台地址验证或真实 appTicket/token 获取。
- 未重新打包 EXE，未变更数据库。

提交前重新运行上述五个相关测试文件，结果为 **46 passed**；`git diff --check` 未发现空白格式问题。

验证命令（使用可用解释器，并允许本机回环 HTTP 访问）：

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$env:QT_QPA_PLATFORM='offscreen'
python -m pytest tplus_sales_import/tests/test_online_token.py tplus_sales_import/tests/test_callback_probe.py tplus_sales_import/tests/test_tplus_api.py tplus_sales_import/tests/test_engine_approval.py tplus_sales_import/tests/test_connection_config.py -q --basetemp tplus_sales_import/.validation/token-doc-commit-20261023-01 --tb=short
```

`--basetemp` 应使用本次测试专用目录；重复执行时 pytest 会清理该目录，不要指向业务数据目录。

## 9. 后续待办

1. 验证快解析公网 HTTPS 地址和 POST 转发。
2. 取得当前应用准确的推送协议及脱敏测试报文，确认验证消息、解密、来源校验和应答要求。
3. 为单文件测试服务补入消息密钥配置、解密、票据识别与更新时间展示。
4. 保存并更新真实票据，处理重试、重复及乱序消息。
5. 在明确授权凭据传输目的地后，独立实现软证书换 Token 并进行只读接口验证。
6. 确认稳定运行后，再决定是否接入导入程序；不得由测试连通状态自动放行认证。

本轮初始分析还发现审核结果未知时自动清理草稿、提交恢复后漏审、审核后撤销兼容等风险。这些未在本次认证/连通测试范围内修复，后续应单独处理。

## 10. 参考资料与证据级别

### 官方源码和产品文档

- [畅捷通官方 Python SDK](https://github.com/Chanjet/chanjet-openapi-python-sdk)
- [SDK 认证示例](https://github.com/Chanjet/chanjet-openapi-python-sdk/blob/a076ce11d6d1789e657b96d72bbbcff594dbb4e9/chanjet_openapi_python_sdk/common_api_demo.py)
- [SDK 客户端请求头](https://github.com/Chanjet/chanjet-openapi-python-sdk/blob/a076ce11d6d1789e657b96d72bbbcff594dbb4e9/chanjet_openapi_python_sdk/chanjet_client.py)
- [SDK Token 响应定义](https://github.com/Chanjet/chanjet-openapi-python-sdk/blob/a076ce11d6d1789e657b96d72bbbcff594dbb4e9/chanjet_openapi_python_sdk/response/get_token_response.py)
- [畅捷通应用入驻接入指南](https://open.chanjet.com/docs/quickstart/ksrm/yyfblc)
- [快解析使用指南](https://www.kuaijiexi.com/Instructions)
- [快解析映射配置教程](https://www.kuaijiexi.com/Instructions/46.html)
- [快解析 HTTP 映射公网 HTTPS 说明](https://www.kuaijiexi.com/helpDetail183.html)
- [OpenSSL 密钥生成](https://docs.openssl.org/3.0/man1/openssl-genpkey/)

### 第三方文章与公开实现，仅作参考

- [最初参考的 T+ 离线认证文章](https://blog.csdn.net/weixin_42525738/article/details/164384291)
- [销帮帮自建应用配置说明](https://qwhelp.xbongbong.com/?p=16638)
- [公开自建应用对接实现](https://github.com/hkxiaoyao/cjt2mcp)
- [公开实现：软证书换 Token](https://github.com/hkxiaoyao/cjt2mcp/blob/main/app/chanjet/client.py)
- [公开实现：消息接收](https://github.com/hkxiaoyao/cjt2mcp/blob/main/app/chanjet/webhook.py)
- [公开实现：消息解密](https://github.com/hkxiaoyao/cjt2mcp/blob/main/app/crypto.py)

第三方资料不替代现场版本协议；未验证的接口、时效、文件命名及部署规则不能写成已生效配置。
