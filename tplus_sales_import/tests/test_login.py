import json
from email import policy
from email.parser import BytesParser
from io import BytesIO
from unittest.mock import Mock
import urllib.error

import pytest

from app.configuration import DatabaseConfig, LoginConfig
from app.login import LoginClient, LoginError
from app.gui import TaskWorker


def settings(signed_api):
    return LoginConfig("http://example.test/token?IsFree=1", "login-user", "login-password",
                       "300216", api=signed_api)


def response(payload):
    stream = BytesIO(json.dumps(payload).encode())
    stream.status = 200
    return stream


def test_login_posts_multipart_args_and_exact_authorization(signed_api):
    def request(req, timeout):
        assert req.method == "POST" and req.full_url == settings(signed_api).url
        import base64
        header = json.loads(base64.b64decode(req.get_header("Authorization")))
        assert header["appKey"] == signed_api.app_key
        # Verify the actual outgoing signature with the independently loaded key.
        from test_authorization import decode_verified
        _, payload = decode_verified(req.get_header("Authorization"), signed_api.pem_path)
        assert payload["sub"] == "tester" and "access_token" not in payload
        assert timeout == 15
        message = BytesParser(policy=policy.default).parsebytes(
            ("Content-Type: " + req.get_header("Content-type") + "\r\n\r\n").encode() + req.data)
        parts = list(message.iter_parts())
        assert len(parts) == 1
        assert parts[0].get_param("name", header="content-disposition") == "_args"
        assert json.loads(parts[0].get_payload(decode=True)) == dict(
            userName="login-user", password="login-password", accNum="300216")
        return response(dict(result=True, access_token="valid-token", sid=""))
    assert LoginClient(request).authenticate(settings(signed_api)) == "valid-token"


@pytest.mark.parametrize("payload", [dict(result=False, access_token="x"),
    dict(result="true", access_token="x"), dict(result=1, access_token="x"),
    dict(result=True), dict(result=True, access_token=" "), dict(result=True, access_token=123), []])
def test_login_rejects_unsuccessful_or_incomplete_response(payload, signed_api):
    with pytest.raises(LoginError):
        LoginClient(lambda *a, **k: response(payload)).authenticate(settings(signed_api))


@pytest.mark.parametrize("error", [TimeoutError(), urllib.error.URLError("login-password"),
    urllib.error.HTTPError("http://example.test/token", 401, "test-authorization", {}, None)],
    ids=["timeout", "network", "http-401"])
def test_login_network_errors_do_not_expose_credentials(error, signed_api):
    with pytest.raises(LoginError) as caught:
        LoginClient(Mock(side_effect=error)).authenticate(settings(signed_api))
    assert settings(signed_api).password not in str(caught.value)


def test_login_rejects_invalid_json_and_missing_config(signed_api):
    stream = BytesIO(b"not json")
    stream.status = 200
    with pytest.raises(LoginError, match="JSON"):
        LoginClient(lambda *a, **k: stream).authenticate(settings(signed_api))
    request = Mock()
    with pytest.raises(LoginError, match="config.ini"):
        LoginClient(request).authenticate(LoginConfig())
    request.assert_not_called()


@pytest.mark.parametrize("db_ok,token_ok", [(True, True), (False, True), (True, False)])
def test_login_worker_only_checks_database_and_closes_connection(monkeypatch, db_ok, token_ok, signed_api):
    import app.gui as gui
    repo = Mock()
    repo.open.side_effect = None if db_ok else ValueError("数据库失败")
    repo.open.return_value = "test-db"
    monkeypatch.setattr(gui, "SqlRepository", Mock(return_value=repo))
    auth = Mock(return_value="valid-token", side_effect=None if token_ok else LoginError("认证失败"))
    monkeypatch.setattr(gui.LoginClient, "authenticate", auth)
    cfg = DatabaseConfig("localhost", 1433, "test-db", "test", "db-secret", login=settings(signed_api))
    worker = TaskWorker("login", config=cfg)
    completed, failed = [], []
    worker.completed.connect(completed.append)
    worker.failed.connect(failed.append)
    worker.run()
    assert bool(completed) == db_ok
    if completed:
        assert completed[0] == dict(database="test-db", access_token=None)
    assert bool(failed) != bool(completed)
    repo.close.assert_called_once()
    auth.assert_not_called()


def test_config_and_build_include_separate_login_fields(tmp_path, signed_api):
    from build_app import release_config
    content = ("[sqlserver]\nip=localhost\nport=1433\ndatabase=test\nuser=test\npassword=db-secret\n"
               "[login]\nurl=http://example.test/token\nuserName=user\npassword=hash\naccNum=300216\n")
    source = tmp_path / "config.ini"
    source.write_text(content, encoding="utf-8")
    cfg = DatabaseConfig.load(source)
    assert (cfg.login.user_name, cfg.login.password, cfg.login.acc_num) == (
        "user", "hash", "300216")
    target = tmp_path / "deployed.ini"
    assert release_config(tmp_path, target) == source.read_bytes()
    target.write_text(content.split("[login]")[0], encoding="utf-8")
    target.write_bytes(release_config(tmp_path, target))
    assert DatabaseConfig.load(target) == cfg
    previous = target.read_bytes()
    assert release_config(tmp_path, target) == previous


def test_approval_reuses_token_without_legacy_login(signed_api):
    from app.configuration import TPlusApiConfig
    from app.tplus_api import TPlusApiClient
    request = Mock(side_effect=AssertionError("must reuse token"))
    client = TPlusApiClient(TPlusApiConfig(enabled=True), requester=request)
    client.token = "login-token"
    assert client.get_token()[0] is True
    request.assert_not_called()


@pytest.mark.parametrize("success", [True, False])
def test_token_request_and_result_are_logged_in_full(success, signed_api):
    payload = dict(result=success, access_token="private-response-token", sid="private-session")
    client = LoginClient(lambda *a, **k: response(payload))
    client.log = Mock()
    if success:
        client.authenticate(settings(signed_api))
    else:
        with pytest.raises(LoginError):
            client.authenticate(settings(signed_api))
    messages = [str(call) for call in client.log.mock_calls]
    text = "\n".join(messages)
    assert "Token请求" in text and "POST" in text and settings(signed_api).url in text
    assert "_args" in text and "userName" in text and "accNum" in text
    assert settings(signed_api).user_name in text and settings(signed_api).acc_num in text
    assert "Token响应" in text and "200" in text
    assert ("Token认证成功" if success else "Token认证失败") in text
    for secret in (settings(signed_api).password, "private-response-token", "private-session"):
        assert secret in text
