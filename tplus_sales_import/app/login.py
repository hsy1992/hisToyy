"""Real-name T+ login using a single multipart form field named _args."""
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

from log_util import logger, register_secret
from .authorization import AuthorizationError, create_authorization


class LoginError(ValueError):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class LoginClient:
    def __init__(self, requester=None):
        self.requester = requester or urllib.request.build_opener(_NoRedirect()).open
        self.log = logging.LoggerAdapter(logger, {"unmasked": True})

    def authenticate(self, config):
        if not all((config.url, config.user_name, config.password, config.acc_num)):
            raise LoginError("请在 config.ini 的 [login] 中配置 url、userName、password、accNum。")
        url = urllib.parse.urlsplit(config.url)
        if url.scheme not in ("http", "https") or not url.netloc or url.fragment or url.username or url.password:
            raise LoginError("登录接口 url 必须是完整的 HTTP/HTTPS 地址。")
        try:
            authorization = create_authorization(config.api)
        except AuthorizationError as exc:
            raise LoginError(str(exc)) from None
        boundary = "TPlusLogin" + uuid.uuid4().hex
        args = json.dumps(dict(userName=config.user_name, password=config.password,
                               accNum=config.acc_num), ensure_ascii=False)
        body = (f'--{boundary}\r\nContent-Disposition: form-data; name="_args"\r\n\r\n'
                f'{args}\r\n--{boundary}--\r\n').encode("utf-8")
        request = urllib.request.Request(config.url, data=body, method="POST", headers={
            "Content-Type": "multipart/form-data; boundary=" + boundary,
            "Authorization": authorization, "Accept": "application/json"})
        self.log.info("Token请求 method=POST url=%s timeout=15 headers=%s form=%s", config.url,
                      {"Content-Type": request.get_header("Content-type"),
                       "Authorization": authorization, "Accept": "application/json"},
                      {"_args": dict(userName=config.user_name, password=config.password, accNum=config.acc_num)})
        started = time.perf_counter()
        try:
            with self.requester(request, timeout=15) as response:
                self.log.info("Token响应 status=%s elapsed_seconds=%.3f", response.status,
                              time.perf_counter() - started)
                if response.status != 200:
                    self.log.warning("Token认证失败 reason=HTTP状态异常")
                    raise LoginError("Token 接口未返回 HTTP 200，登录失败。")
                raw = response.read()
                self.log.info("Token响应正文 body=%s", raw.decode("utf-8", errors="replace"))
        except urllib.error.HTTPError as exc:
            self.log.warning("Token请求失败 status=%s elapsed_seconds=%.3f", exc.code,
                             time.perf_counter() - started)
            raise LoginError(f"Token 接口 HTTP {exc.code}，登录失败，请检查配置。") from None
        except (urllib.error.URLError, TimeoutError, OSError):
            self.log.warning("Token请求失败 reason=网络连接失败或超时 elapsed_seconds=%.3f",
                             time.perf_counter() - started)
            raise LoginError("Token 接口连接失败或超时，请检查网络及登录配置。") from None
        try:
            result = json.loads(raw)
        except (ValueError, TypeError):
            self.log.warning("Token认证失败 reason=无效JSON")
            raise LoginError("Token 接口未返回有效 JSON，登录失败。") from None
        if not isinstance(result, dict) or result.get("result") is not True:
            self.log.warning("Token认证失败 reason=result不是true")
            raise LoginError("Token 接口认证未通过（result 必须为 true），请检查登录配置。")
        token = result.get("access_token")
        if not isinstance(token, str) or not token.strip():
            self.log.warning("Token认证失败 reason=缺少有效access_token")
            raise LoginError("Token 接口缺少有效 access_token，登录失败。")
        register_secret(token)
        self.log.info("Token认证成功 result=true access_token=%s", token.strip())
        return token.strip()
