"""T+ OpenAPI / Web API client for voucher approval."""
from __future__ import annotations
import json
import re
import urllib.request
import urllib.parse
import urllib.error
from log_util import logger, diagnostics
from .configuration import TPlusApiConfig


class TPlusApiClient:
    def __init__(self, config: TPlusApiConfig, requester=None):
        self.config = config
        self.requester = requester or self._default_requester
        self.token = None
        self.log = logger

    def _default_requester(self, url: str, data=None, headers=None, timeout: int = 10):
        req = urllib.request.Request(url, data=data, headers=headers or {})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8")

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

    def _build_auth_headers(self, with_bearer: bool = False) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) TPlusImport/1.0",
        }
        if with_bearer and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if self.config.app_key:
            headers["appKey"] = self.config.app_key
            headers["AppKey"] = self.config.app_key
        if self.config.app_secret:
            headers["appSecret"] = self.config.app_secret
            headers["AppSecret"] = self.config.app_secret
        return headers

    def _extract_token(self, res: dict) -> str | None:
        token = res.get("token") or res.get("access_token") or res.get("Value")
        data_val = res.get("data")
        if not token and isinstance(data_val, dict):
            token = data_val.get("token") or data_val.get("accessToken") or data_val.get("Value")
        elif not token and isinstance(data_val, str) and len(data_val) > 8:
            token = data_val
        return str(token) if token else None

    def get_token(self) -> tuple[bool, str]:
        """前置获取 Token / 会话认证。

        若认证失败，返回 (False, 错误说明)，用于主流程熔断阻断。
        """
        if not self.config.enabled:
            return True, "API审核未启用（模拟通过）"
        if not self.config.password:
            return False, "T+ 登录密码未配置，请在 config.ini 的 [tplus_api] 中配置 password"

        # 尝试的用户名候选：先用配置值，如果是手机号则尝试于淑梅，反之亦然
        users = [self.config.user]
        if self.config.user == "18249513776":
            users.append("于淑梅")
        elif self.config.user == "于淑梅":
            users.append("18249513776")

        endpoints = [
            "/tplus/api/v2/Token",
            "/tplus/api/v2/token/CreateToken",
            "/tplus/api/v2/login",
            "/tplus/api/v2/user/login",
            "/tplus/api/v2/pos/login",
        ]

        last_error = ""

        for u in users:
            for ep in endpoints:
                base_url = f"{self.config.url.rstrip('/')}{ep}"
                # 兼容不同网关规则：1. 纯 URL（靠 Header 与 Body 携带 AppKey）
                # 2. Query 参数携带 AppKey
                candidate_urls = [base_url]
                if self.config.app_key and self.config.app_secret:
                    query = urllib.parse.urlencode({
                        "appKey": self.config.app_key,
                        "appSecret": self.config.app_secret,
                    })
                    candidate_urls.append(f"{base_url}?{query}")

                for url in candidate_urls:
                    payload = {
                        "account": self.config.account,
                        "accNum": self.config.account,
                        "userName": u,
                        "password": self.config.password,
                    }
                    if self.config.app_key:
                        payload["appKey"] = self.config.app_key
                        payload["AppKey"] = self.config.app_key
                    if self.config.app_secret:
                        payload["appSecret"] = self.config.app_secret
                        payload["AppSecret"] = self.config.app_secret

                    safe_payload = {k: ("******" if any(s in k.lower() for s in ("pass", "secret")) else v) for k, v in payload.items()}
                    safe_url = re.sub(r"(appSecret=)[^&]+", r"\1******", url, flags=re.IGNORECASE)
                    data = json.dumps(payload).encode("utf-8")
                    headers = self._build_auth_headers(with_bearer=False)

                    self.log.info("【API请求】发起认证 url=%s payload=%s", safe_url, safe_payload)
                    try:
                        status, body = self.requester(url, data=data, headers=headers, timeout=8)
                        self.log.info("【API响应成功】url=%s status=%d body=%s", safe_url, status, body)
                        if status == 200:
                            try:
                                res = json.loads(body)
                                token = self._extract_token(res)
                                if token:
                                    self.token = token
                                    self.log.info("获取 T+ API Token 成功 endpoint=%s user=%s token=%s...", safe_url, u, self.token[:10])
                                    return True, self.token
                                msg = res.get("message") or res.get("msg") or res.get("Message") or body
                                last_error = f"T+ 认证返回：{msg}"
                            except json.JSONDecodeError:
                                last_error = f"T+ 响应非JSON：{body[:200]}"
                        else:
                            last_error = f"T+ HTTP {status}"
                    except urllib.error.HTTPError as exc:
                        err_msg, raw_body = self._extract_http_error(exc)
                        self.log.warning("【API响应异常】url=%s status=%d reason=%s body=%s", safe_url, exc.code, exc.reason, raw_body)
                        if exc.code == 404:
                            continue
                        last_error = f"T+ HTTP {exc.code}：{err_msg}"
                    except urllib.error.URLError as exc:
                        self.log.error("【API连接失败】url=%s error=%s", safe_url, exc.reason)
                        last_error = f"无法连接到 T+ 服务（{self.config.url}）：{exc.reason}"
                        return False, last_error
                    except Exception as exc:
                        self.log.error("【API未知异常】url=%s %s", safe_url, diagnostics(exc))
                        last_error = f"T+ 认证调用异常：{diagnostics(exc)}"

        return False, last_error or "未找到可用的 T+ 认证接口"

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

        base_url = f"{self.config.url.rstrip('/')}/tplus/api/v2/saleDelivery/Audit"
        url = base_url
        if self.config.app_key and self.config.app_secret:
            query = urllib.parse.urlencode({
                "appKey": self.config.app_key,
                "appSecret": self.config.app_secret,
            })
            url = f"{base_url}?{query}"

        payload = {
            "param": {
                "Code": sa_code,
                "ID": voucher_id,
            }
        }
        if self.config.app_key:
            payload["appKey"] = self.config.app_key
        if self.config.app_secret:
            payload["appSecret"] = self.config.app_secret

        headers = self._build_auth_headers(with_bearer=True)
        data = json.dumps(payload).encode("utf-8")
        safe_url = re.sub(r"(appSecret=)[^&]+", r"\1******", url, flags=re.IGNORECASE)

        self.log.info("【API请求】发起单据审批 url=%s sa_code=%s voucher_id=%s", safe_url, sa_code, voucher_id)
        try:
            status, body = self.requester(url, data=data, headers=headers, timeout=15)
            self.log.info("【API审批响应】url=%s sa_code=%s status=%d body=%s", safe_url, sa_code, status, body)
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
            self.log.warning("【API审批异常】url=%s sa_code=%s status=%d body=%s", safe_url, sa_code, exc.code, raw_body)
            return False, f"T+ 审批 HTTP {exc.code}：{err_msg}"
        except Exception as exc:
            self.log.error("【API审批调用异常】url=%s sa_code=%s %s", safe_url, sa_code, diagnostics(exc))
            return False, f"T+ 审批调用异常：{diagnostics(exc)}"
