import base64
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from app.authorization import AuthorizationError, create_authorization
from app.configuration import DatabaseConfig


def test_signing_logs_all_stages_without_dumping_private_key(signed_api):
    import io
    import logging
    from log_util import logger, SafeFormatter
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(SafeFormatter("%(message)s"))
    logger.addHandler(handler)
    try:
        value = create_authorization(signed_api, "debug-business-token")
    finally:
        logger.removeHandler(handler)
        handler.close()
    text = stream.getvalue()
    for stage in ("签名参数", "MD5", "JWT载荷", "签名输入", "签名结果", "外层JSON", "完成"):
        assert "stage=" + stage in text
    assert '"appsecret":"test-secret"' in text
    assert '"access_token":"debug-business-token"' in text
    assert '"sub":"chanjet"' in text
    assert "Authorization=" + value in text
    assert "pem_path=" in text and "salt_length=32" in text
    assert "PRIVATE KEY" not in text
    trace_ids = {line.split("trace=")[1].split()[0] for line in text.splitlines()}
    assert len(trace_ids) == 1


def decode_verified(value, pem_path):
    envelope = json.loads(base64.b64decode(value))
    header, payload, signature = envelope["authInfo"].split(".")
    def decode(part):
        return base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))
    key = serialization.load_pem_private_key(Path(pem_path).read_bytes(), None)
    key.public_key().verify(decode(signature), (header + "." + payload).encode("ascii"),
                            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32),
                            hashes.SHA256())
    assert json.loads(decode(header)) == {"alg": "PS256", "typ": "JWT"}
    return envelope, json.loads(decode(payload))


def test_sdk_digest_expiry_org_and_randomized_signature(signed_api, monkeypatch):
    monkeypatch.setattr("app.authorization.time.time", lambda: 1792755923.8807942)
    config = replace(signed_api, org_id="123")
    first = create_authorization(config)
    second = create_authorization(config)
    envelope, payload = decode_verified(first, config.pem_path)
    assert envelope["appKey"] == config.app_key and envelope["orgId"] == "123"
    source = b'{"appkey":"test-app","orgid":"123","appsecret":"test-secret"}'
    assert payload == dict(sub="tester", exp=1792755953880.7942,
                           datas=hashlib.md5(source).hexdigest())
    assert first != second
    assert decode_verified(second, config.pem_path)[1] == payload
    # SDK test vector independently checked via TokenManage.GetMd5.
    _, account_payload = decode_verified(create_authorization(signed_api), config.pem_path)
    assert account_payload["datas"] == "e171901bd32f4ffc4e18e1269037f5be"


def test_business_payload_and_tampering(signed_api):
    value = create_authorization(signed_api, "business-token")
    envelope, payload = decode_verified(value, signed_api.pem_path)
    assert payload["sub"] == "chanjet" and payload["access_token"] == "business-token"
    header, _, signature = envelope["authInfo"].split(".")
    altered = base64.urlsafe_b64encode(b'{"datas":"tampered"}').rstrip(b"=").decode()
    envelope["authInfo"] = ".".join((header, altered, signature))
    with pytest.raises(InvalidSignature):
        decode_verified(base64.b64encode(json.dumps(envelope).encode()), signed_api.pem_path)


def test_invalid_signing_config_fails_before_request(signed_api, tmp_path):
    from app.configuration import LoginConfig
    from app.login import LoginClient, LoginError
    from unittest.mock import Mock
    request = Mock()
    for config in (replace(signed_api, app_secret=""),
                   replace(signed_api, pem_path=str(tmp_path / "missing.pem"))):
        with pytest.raises(LoginError):
            LoginClient(request).authenticate(LoginConfig(
                "http://example.test/token", "user", "password", "001", api=config))
    request.assert_not_called()
    path = tmp_path / "invalid.pem"
    path.write_text("not-a-key", encoding="ascii")
    with pytest.raises(AuthorizationError, match="格式无效"):
        create_authorization(replace(signed_api, pem_path=str(path)))


def test_config_resolves_pem_beside_ini_independent_of_cwd(tmp_path, monkeypatch):
    directory = tmp_path / "app"
    directory.mkdir()
    ini = directory / "config.ini"
    ini.write_text('[sqlserver]\nip=localhost\nport=1433\ndatabase=test\nuser=test\npassword=\n'
                   '[tplus_api]\napp_key=key\napp_secret=secret\norg_id="123"\npem_path="cjet_pri.pem"\n'
                   '[login]\nurl=http://example.test/token\nuserName=user\npassword=hash\naccNum=001\n',
                   encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    config = DatabaseConfig.load(ini)
    assert config.api.org_id == "123"
    assert Path(config.api.pem_path) == directory / "cjet_pri.pem"
    assert config.login.api == config.api
    assert not hasattr(config.login, "authorization")


def test_frozen_default_key_path_is_beside_executable(tmp_path, monkeypatch):
    import app.configuration as configuration
    monkeypatch.setattr(configuration.sys, "frozen", True, raising=False)
    monkeypatch.setattr(configuration.sys, "executable", str(tmp_path / "TplusSalesImport.exe"))
    assert Path(configuration.TPlusApiConfig().pem_path) == tmp_path / "cjet_pri.pem"
