import json
import pytest
import urllib.error

from app.configuration import TPlusApiConfig
from app.tplus_api import TPlusApiClient


def test_missing_password_returns_failure_for_breaker():
    cfg = TPlusApiConfig(password="", enabled=True)
    client = TPlusApiClient(cfg)
    ok, msg = client.get_token()
    assert ok is False
    assert "登录密码未配置" in msg


def test_network_connection_error_handled_cleanly():
    def failing_requester(url, data, headers, timeout):
        raise urllib.error.URLError("Connection refused")

    cfg = TPlusApiConfig(password="secret123", enabled=True)
    client = TPlusApiClient(cfg, requester=failing_requester)
    ok, msg = client.get_token()
    assert ok is False
    assert "无法连接到 T+ 服务" in msg


def test_token_fetch_success():
    def mock_requester(url, data, headers, timeout):
        return 200, json.dumps({"code": "0", "token": "test-token-xyz"})

    cfg = TPlusApiConfig(password="secret123", enabled=True)
    client = TPlusApiClient(cfg, requester=mock_requester)
    ok, token = client.get_token()
    assert ok is True
    assert token == "test-token-xyz"
    assert client.token == "test-token-xyz"


def test_token_fetch_with_app_key_and_secret():
    recorded_calls = []

    def mock_requester(url, data, headers, timeout):
        recorded_calls.append({"url": url, "data": json.loads(data.decode("utf-8")), "headers": headers})
        return 200, json.dumps({"code": "0", "data": {"token": "appkey-token-abc"}})

    cfg = TPlusApiConfig(
        url="http://127.0.0.1:7777",
        password="secret",
        app_key="pos-key-123",
        app_secret="pos-secret-456",
        enabled=True,
    )
    client = TPlusApiClient(cfg, requester=mock_requester)
    ok, token = client.get_token()
    assert ok is True
    assert token == "appkey-token-abc"
    assert len(recorded_calls) >= 1
    call = recorded_calls[0]
    assert "pos-key-123" in call["headers"].values()
    assert call["data"]["appKey"] == "pos-key-123"
    assert call["data"]["appSecret"] == "pos-secret-456"


def test_audit_voucher_success():
    def mock_requester(url, data, headers, timeout):
        return 200, json.dumps({"code": "0", "message": "审核成功"})

    cfg = TPlusApiConfig(password="secret123", enabled=True)
    client = TPlusApiClient(cfg, requester=mock_requester)
    client.token = "valid-token"
    ok, msg = client.audit_voucher("SA2026102200001", 1001)
    assert ok is True
    assert "审核成功" in msg


def test_audit_voucher_rejected_with_reason():
    def mock_requester(url, data, headers, timeout):
        return 200, json.dumps({"code": "500", "message": "存货[C0086]在仓库[库房]现存量不足，审核失败"})

    cfg = TPlusApiConfig(password="secret123", enabled=True)
    client = TPlusApiClient(cfg, requester=mock_requester)
    client.token = "valid-token"
    ok, msg = client.audit_voucher("SA2026102200001", 1001)
    assert ok is False
    assert "现存量不足" in msg


def test_taskworker_test_action_checks_api_auth(monkeypatch):
    import app.gui as gui
    from app.database import PreflightError, SqlRepository
    from app.configuration import DatabaseConfig, TPlusApiConfig

    monkeypatch.setattr(SqlRepository, "open", lambda self: "UFDATA_999_TEST")
    monkeypatch.setattr(SqlRepository, "close", lambda self: None)

    # 1. API 认证失败情况
    api_fail = TPlusApiConfig(password="", enabled=True)
    cfg_fail = DatabaseConfig("localhost", 1433, "UFDATA_999_TEST", "sa", "test-db-secret-long", api=api_fail)
    worker = gui.TaskWorker("test", config=cfg_fail)

    failed_msgs = []
    worker.failed.connect(lambda msg: failed_msgs.append(msg))
    worker.run()
    assert len(failed_msgs) == 1
    assert "T+ API 认证查询失败" in failed_msgs[0]

    # 2. API 认证成功情况
    api_succ = TPlusApiConfig(password="pass", enabled=True)
    cfg_succ = DatabaseConfig("localhost", 1433, "UFDATA_999_TEST", "sa", "test-db-secret-long", api=api_succ)
    worker2 = gui.TaskWorker("test", config=cfg_succ)
    monkeypatch.setattr(TPlusApiClient, "get_token", lambda self: (True, "mock-token"))

    completed_results = []
    worker2.completed.connect(lambda res: completed_results.append(res))
    worker2.run()
    assert len(completed_results) == 1
    assert "UFDATA_999_TEST，T+ API认证通过" in completed_results[0]
