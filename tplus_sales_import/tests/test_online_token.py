import json
import urllib.error
from urllib.parse import parse_qs, urlsplit

import pytest
from PyQt5.QtWidgets import QApplication

from app.online_token import OnlineTokenClient, OnlineTokenDialog, OnlineTokenError


def test_exchange_uses_official_get_endpoint_and_headers():
    calls = []

    def requester(request, timeout):
        calls.append((request, timeout))
        return json.dumps({"code": 200, "result": {
            "access_token": "access-value", "refresh_token": "refresh-value",
            "expires_in": 7200, "org_id": "org-1"}})

    result = OnlineTokenClient(requester).exchange("app-key", "app-secret", "https://example.com/cb", "a+b&c")
    request, timeout = calls[0]
    assert request.get_method() == "GET"
    assert urlsplit(request.full_url).netloc == "openapi.chanjet.com"
    assert urlsplit(request.full_url).path == "/auth/getToken"
    assert parse_qs(urlsplit(request.full_url).query) == {
        "grantType": ["authorization_code"], "appKey": ["app-key"],
        "redirectUri": ["https://example.com/cb"], "code": ["a+b&c"]}
    assert request.get_header("Appkey") == "app-key"
    assert request.get_header("Appsecret") == "app-secret"
    assert "app-secret" not in request.full_url
    assert timeout == 15
    assert result["access_token"] == "access-value"
    assert result["refresh_token"] == "refresh-value"
    assert result["expires_in"] == 7200


@pytest.mark.parametrize("values", [
    ("", "secret", "https://example.com/cb", "code"),
    ("key", "", "https://example.com/cb", "code"),
    ("key", "secret", "", "code"),
    ("key", "secret", "https://example.com/cb", ""),
    ("key", "secret", "not-a-url", "code"),
])
def test_missing_or_invalid_input_does_not_send_request(values):
    calls = []
    with pytest.raises(OnlineTokenError):
        OnlineTokenClient(lambda *args, **kwargs: calls.append(args)).exchange(*values)
    assert not calls


@pytest.mark.parametrize("body", ["<html>login</html>", "[]", "{}",
    '{"code": 200, "result": {}}',
    '{"code": 200, "result": {"access_token": {"bad": true}}}',
    '{"code": 500, "result": {"access_token": "wrong"}}'])
def test_malformed_or_unsuccessful_response_is_not_a_token(body):
    with pytest.raises(OnlineTokenError):
        OnlineTokenClient(lambda *args, **kwargs: body).exchange("key", "secret", "https://example.com/cb", "code")


def test_error_response_redacts_credentials_and_tokens():
    body = json.dumps({"code": 400, "message": "bad secret-value code-value leaked-token",
                       "result": {"access_token": "leaked-token"}})
    with pytest.raises(OnlineTokenError) as failure:
        OnlineTokenClient(lambda *args, **kwargs: body).exchange(
            "key", "secret-value", "https://example.com/cb", "code-value")
    assert "400" in str(failure.value)
    assert not any(secret in str(failure.value) for secret in ("secret-value", "code-value", "leaked-token"))


def test_network_error_does_not_expose_request_or_secrets():
    def requester(*args, **kwargs):
        raise urllib.error.URLError("request containing secret-value")
    with pytest.raises(OnlineTokenError) as failure:
        OnlineTokenClient(requester).exchange("key", "secret-value", "https://example.com/cb", "code")
    assert "secret-value" not in str(failure.value)
    assert "网络" in str(failure.value)


def test_default_client_never_transmits_credentials():
    with pytest.raises(OnlineTokenError, match="在线请求尚未启用"):
        OnlineTokenClient().exchange("key", "secret", "https://example.com/cb", "code")


def test_dialog_exchanges_in_worker_and_clears_stale_result():
    app = QApplication.instance() or QApplication([])
    calls = []

    class Client:
        def exchange(self, *args):
            calls.append(args)
            return {"access_token": "access-value", "refresh_token": "refresh-value", "expires_in": 7200}

    dialog = OnlineTokenDialog(client=Client())
    dialog.app_key.setText("key")
    dialog.app_secret.setText("secret")
    dialog.redirect_uri.setText("https://example.com/cb")
    dialog.code.setText("code")
    dialog.fetch_button.click()
    assert not dialog.fetch_button.isEnabled()
    assert dialog.worker.wait(5000)
    app.processEvents()
    assert dialog.access_token.text() == "access-value"
    assert dialog.refresh_token.text() == "refresh-value"
    assert calls == [("key", "secret", "https://example.com/cb", "code")]
    dialog.app_key.setText("changed")
    assert dialog.access_token.text() == ""
    assert not dialog.copy_button.isEnabled()
    dialog.close()


def test_new_button_opens_independent_dialog_without_database(monkeypatch, tmp_path):
    import app.gui as gui
    import app.online_token as online
    app = QApplication.instance() or QApplication([])
    opened = []
    monkeypatch.setattr(online.OnlineTokenDialog, "exec_", lambda self: opened.append(self))
    window = gui.ImportWindow(tmp_path / "missing.ini")
    window.online_token_button.click()
    assert len(opened) == 1
    assert window.config is None
    assert window.worker is None
    assert window.result is None
    window.close()
