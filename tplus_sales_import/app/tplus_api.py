"""T+ OpenAPI / Web API client for voucher approval."""
from __future__ import annotations
import json
import logging
import urllib.request
import urllib.error
import urllib.parse
import http.client
from log_util import logger, diagnostics
from io import BytesIO
from .configuration import TPlusApiConfig, LoginConfig
from .authorization import AuthorizationError, create_authorization
from .login import LoginClient, LoginError


class TPlusApiClient:
    def __init__(self, config: TPlusApiConfig, requester=None):
        self.config = config
        self.requester = requester or self._default_requester
        self.token = None
        self.log = logging.LoggerAdapter(logger, {"unmasked": True})

    def _default_requester(self, url: str, data=None, headers=None, timeout: int = 10):
        # Keep the supplied headers explicit; do not inject urllib defaults.
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise ValueError("T+ 接口必须使用完整 HTTP/HTTPS 地址")
        connection_type = http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
        connection = connection_type(parsed.hostname, port=parsed.port, timeout=timeout)
        target = urllib.parse.urlunsplit(("", "", parsed.path or "/", parsed.query, ""))
        try:
            connection.request("POST" if data is not None else "GET", target,
                               body=data, headers=headers or {})
            response = connection.getresponse()
            body = response.read()
            if response.status >= 400:
                raise urllib.error.HTTPError(url, response.status, response.reason,
                                             response.headers, BytesIO(body))
            return response.status, body.decode("utf-8")
        finally:
            connection.close()

    def _extract_http_error(self, exc: urllib.error.HTTPError) -> tuple[str, str]:
        """从 HTTP 异常响应体中提取 T+ 返回的真实错误消息（支持 HTTP 999/500/400 等）。"""
        raw_body = ""
        try:
            raw_body = exc.read().decode("utf-8", errors="ignore")
            if raw_body:
                try:
                    res = json.loads(raw_body)
                    msg = res.get("message") or res.get("msg") or res.get("Message") or raw_body
                    return str(msg), raw_body
                except json.JSONDecodeError:
                    return raw_body[:300], raw_body
        except Exception:
            pass
        return exc.reason or f"HTTP {exc.code}", raw_body

    def _build_auth_headers(self, with_token: bool = False) -> dict[str, str]:
        if with_token and not self.token:
            raise AuthorizationError("审核请求缺少 access_token，请重新登录。")
        return {
            # "Content-Type": "application/json; charset=utf-8",
            # "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) TPlusImport/1.0",
            "Authorization": create_authorization(self.config, self.token if with_token else None),
            # "Accept": "application/json",
        }

    def get_token(self) -> tuple[bool, str]:
        """Use the documented real-name endpoint with freshly signed Authorization."""
        if self.token:
            return True, "已使用登录取得的 Token"
        if not self.config.enabled:
            return True, "API审核未启用（模拟通过）"
        if not self.config.password:
            return False, "T+ 登录密码未配置，请在 config.ini 的 [tplus_api] 中配置 password"

        def request(req, timeout):
            status, body = self.requester(req.full_url, data=req.data,
                                          headers=dict(req.header_items()), timeout=timeout)
            response = BytesIO(body.encode("utf-8") if isinstance(body, str) else body)
            response.status = status
            return response

        login = LoginConfig(
            url=self.config.url.rstrip("/") +
                "/tplus/api/v2/collaborationapp/GetRealNameTPlusToken?IsFree=1",
            user_name=self.config.user, password=self.config.password,
            acc_num=self.config.account, api=self.config)
        try:
            self.token = LoginClient(requester=request).authenticate(login)
            return True, self.token
        except LoginError as exc:
            return False, str(exc)

    def audit_voucher(self, sa_code: str, voucher_id=None) -> tuple[bool, str]:
        """调用 T+ 销货单审批接口。

        成功返回 (True, "审核成功")，失败返回 (False, "失败详细原因")。
        """
        if not self.config.enabled:
            return True, "模拟审批成功"
        if not self.token:
            ok, msg = self.get_token()
            if not ok:
                return False, f"审批前获取Token失败：{msg}"

        url = f"{self.config.url.rstrip('/')}/tplus/api/v2/SaleDeliveryOpenApi/Audit"
        payload = {
            "param": {
                "voucherCode": sa_code,
            }
        }
        # OpenAPI v2 receives the existing business JSON through the _args form
        # field. This is form encoding, not a raw JSON body containing _args.
        args = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        data = urllib.parse.urlencode({"_args": args}).encode("utf-8")
        try:
            headers = self._build_auth_headers(with_token=True)
        except AuthorizationError as exc:
            return False, str(exc)
        headers["Content-Type"] = "application/x-www-form-urlencoded; charset=utf-8"

        self.log.info("【API请求】发起单据审批 method=POST url=%s sa_code=%s voucher_id=%s "
                      "headers=%s form=%s auth_mode=business access_token_present=%s",
                      url, sa_code, voucher_id, headers, {"_args": payload}, bool(self.token))
        try:
            status, body = self.requester(url, data=data, headers=headers, timeout=15)
            self.log.info("【API审批响应】url=%s sa_code=%s status=%d body=%s", url, sa_code, status, body)
            if status == 200:
                res = json.loads(body)
                code = str(res.get("code", res.get("Code", "0")))
                if code in ("0", "200", "SUCCESS", "success"):
                    return True, "审核成功"
                err_msg = res.get("message") or res.get("msg") or res.get("Message") or body
                return False, f"T+ 审批拒绝：{err_msg}"
            return False, f"T+ 审批接口 HTTP {status}"
        except urllib.error.HTTPError as exc:
            err_msg, raw_body = self._extract_http_error(exc)
            self.log.warning("【API审批异常】url=%s sa_code=%s status=%d body=%s", url, sa_code, exc.code, raw_body)
            return False, f"T+ 审批 HTTP {exc.code}：{err_msg}"
        except Exception as exc:
            self.log.error("【API审批调用异常】url=%s sa_code=%s %s", url, sa_code, diagnostics(exc))
            return False, f"T+ 审批调用异常：{diagnostics(exc)}"
