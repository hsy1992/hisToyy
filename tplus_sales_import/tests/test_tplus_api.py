import json
import pytest
import urllib.error
import urllib.parse
from unittest.mock import Mock
from io import BytesIO

from app.configuration import TPlusApiConfig
from app.tplus_api import TPlusApiClient


@pytest.mark.parametrize("status", [200, 999])
def test_audit_wire_headers_body_fresh_signature_and_http_error(signed_api, status):
    from dataclasses import replace
    from http.server import BaseHTTPRequestHandler, HTTPServer
    import threading
    from test_authorization import decode_verified
    received = []
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            received.append((self.path, dict(self.headers),
                             self.rfile.read(int(self.headers["Content-Length"]))))
            body = json.dumps({"code": "0"} if status == 200 else
                              {"code": "EXSM0003", "message": "提供令牌信息不正确"}).encode()
            self.send_response(status)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def log_message(self, *args):
            pass
    with HTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.02), daemon=True)
        thread.start()
        client = TPlusApiClient(replace(signed_api, org_id="configured-org", url="http://127.0.0.1:" + str(server.server_port)))
        client.token = "test-login-token"
        try:
            for _ in range(2):
                ok, message = client.audit_voucher("SA-2021-05-0002", 1591859)
                assert ok == (status == 200)
                if status == 999:
                    assert "999" in message and "提供令牌信息不正确" in message
        finally:
            server.shutdown()
            thread.join(timeout=2)
    assert len(received) == 2
    for path, headers, body in received:
        assert path == "/tplus/api/v2/SaleDeliveryOpenApi/Audit"
        assert not ({"user-agent", "accept"} & {key.lower() for key in headers})
        assert headers["Content-Type"] == "application/x-www-form-urlencoded; charset=utf-8"
        form = urllib.parse.parse_qs(body.decode("utf-8"), strict_parsing=True)
        assert set(form) == {"_args"}
        assert json.loads(form["_args"][0]) == {"param": {"voucherCode": "SA-2021-05-0002"}}
        envelope, claims = decode_verified(headers["Authorization"], signed_api.pem_path)
        assert envelope["orgId"] == "configured-org"
        import hashlib
        assert claims["datas"] == hashlib.md5(
            b'{"appkey":"test-app","orgid":"configured-org","appsecret":"test-secret"}').hexdigest()
        assert claims["sub"] == "chanjet" and claims["access_token"] == "test-login-token"
    assert received[0][1]["Authorization"] != received[1][1]["Authorization"]


def test_audit_http_request_contains_signed_authorization_and_logs_headers(signed_api, monkeypatch):
    from test_authorization import decode_verified
    requests = []
    class Connection:
        def __init__(self, host, port=None, timeout=None):
            assert host == "example.test" and timeout == 15
        def request(self, method, path, body, headers):
            requests.append(dict(headers))
            assert method == "POST"
            assert path == "/tplus/api/v2/SaleDeliveryOpenApi/Audit"
            assert set(headers) == {"Authorization", "Content-Type"}
            authorization = headers["Authorization"]
            assert authorization and not authorization.startswith("Bearer ")
            _, claims = decode_verified(authorization, signed_api.pem_path)
            assert claims["sub"] == "chanjet" and claims["access_token"] == "login-access-token"
            assert headers["Content-Type"] == "application/x-www-form-urlencoded; charset=utf-8"
            form = urllib.parse.parse_qs(body.decode("utf-8"), strict_parsing=True)
            assert json.loads(form["_args"][0]) == {"param": {"voucherCode": "SA2026102300001"}}
        def getresponse(self):
            response = BytesIO(b'{"code":"0","message":"ok"}')
            response.status = 200
            return response
        def close(self):
            pass
    monkeypatch.setattr("app.tplus_api.http.client.HTTPConnection", Connection)
    client = TPlusApiClient(signed_api)
    client.token = "login-access-token"
    client.log = Mock()
    assert client.audit_voucher("SA2026102300001", 1001)[0]
    assert len(requests) == 1
    logs = "\n".join(str(call) for call in client.log.mock_calls)
    assert "method=POST" in logs and "headers=" in logs
    assert "Authorization" in logs and requests[0]["Authorization"] in logs


def test_missing_password_returns_failure_for_breaker():
    cfg = TPlusApiConfig(password="", enabled=True)
    client = TPlusApiClient(cfg)
    ok, msg = client.get_token()
    assert ok is False
    assert "登录密码未配置" in msg


def test_network_connection_error_handled_cleanly(signed_api):
    def failing_requester(url, data, headers, timeout):
        raise urllib.error.URLError("Connection refused")
    ok, msg = TPlusApiClient(signed_api, requester=failing_requester).get_token()
    assert not ok and "连接失败" in msg


def test_token_fetch_uses_signed_real_name_endpoint(signed_api):
    from test_authorization import decode_verified
    def requester(url, data, headers, timeout):
        assert url.endswith("/tplus/api/v2/collaborationapp/GetRealNameTPlusToken?IsFree=1")
        assert signed_api.app_secret not in url
        _, payload = decode_verified(headers["Authorization"], signed_api.pem_path)
        assert payload["sub"] == "tester"
        assert b'name="_args"' in data
        return 200, json.dumps(dict(result=True, access_token="test-token-xyz"))
    client = TPlusApiClient(signed_api, requester=requester)
    assert client.get_token() == (True, "test-token-xyz")
    assert client.token == "test-token-xyz"


@pytest.mark.parametrize("code,message,success", [
    ("0", "审核成功", True), ("500", "存货现存量不足，审核失败", False)])
def test_audit_uses_token_in_signed_jwt(signed_api, code, message, success):
    from test_authorization import decode_verified
    calls = []
    def requester(url, data, headers, timeout):
        assert "?" not in url
        assert set(headers) == {"Authorization", "Content-Type"}
        assert url.endswith("/tplus/api/v2/SaleDeliveryOpenApi/Audit")
        assert headers["Content-Type"] == "application/x-www-form-urlencoded; charset=utf-8"
        form = urllib.parse.parse_qs(data.decode("utf-8"), strict_parsing=True)
        assert json.loads(form["_args"][0]) == {"param": {"voucherCode": "SA2026102200001"}}
        assert signed_api.app_secret.encode() not in data
        _, payload = decode_verified(headers["Authorization"], signed_api.pem_path)
        assert payload["sub"] == "chanjet" and payload["access_token"] == "valid-token"
        calls.append(headers["Authorization"])
        return 200, json.dumps(dict(code=code, message=message))
    client = TPlusApiClient(signed_api, requester=requester)
    client.token = "valid-token"
    assert client.audit_voucher("SA2026102200001", 1001) == (success, message if success else "T+ 审批拒绝：" + message)
    client.audit_voucher("SA2026102200001", 1001)
    assert len(calls) == 2 and calls[0] != calls[1]


def test_taskworker_login_action_skips_token_auth(monkeypatch):
    import app.gui as gui
    from app.database import PreflightError, SqlRepository
    from app.configuration import DatabaseConfig, TPlusApiConfig
    from app.login import LoginError

    monkeypatch.setattr(SqlRepository, "open", lambda self: "UFDATA_999_TEST")
    monkeypatch.setattr(SqlRepository, "close", lambda self: None)

    # API authentication is bypassed during the database-only test workflow.
    api_fail = TPlusApiConfig(password="", enabled=True)
    cfg_fail = DatabaseConfig("localhost", 1433, "UFDATA_999_TEST", "sa", "test-db-secret-long", api=api_fail)
    worker = gui.TaskWorker("login", config=cfg_fail)
    def failed_auth(self, config):
        raise LoginError("Token 接口认证未通过")
    monkeypatch.setattr(gui.LoginClient, "authenticate", failed_auth)

    failed_msgs = []
    completed = []
    worker.failed.connect(lambda msg: failed_msgs.append(msg))
    worker.completed.connect(completed.append)
    worker.run()
    assert failed_msgs == []
    assert completed == [dict(database="UFDATA_999_TEST", access_token=None)]

    # 2. API 认证成功情况
    api_succ = TPlusApiConfig(password="pass", enabled=True)
    cfg_succ = DatabaseConfig("localhost", 1433, "UFDATA_999_TEST", "sa", "test-db-secret-long", api=api_succ)
    worker2 = gui.TaskWorker("login", config=cfg_succ)
    monkeypatch.setattr(gui.LoginClient, "authenticate", lambda self, config: "mock-token")

    completed_results = []
    worker2.completed.connect(lambda res: completed_results.append(res))
    worker2.run()
    assert len(completed_results) == 1
    assert completed_results[0] == dict(database="UFDATA_999_TEST", access_token=None)
