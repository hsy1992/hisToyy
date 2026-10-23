import base64
import json
from io import BytesIO
from unittest.mock import Mock

import pytest

from app.authorization import create_authorization
from app.configuration import LoginConfig, TPlusApiConfig
from app.login import LoginClient
from app.tplus_api import TPlusApiClient


def sample_headers():
    return pytest.importorskip("app._authorization_samples")


def claims(value):
    outer = json.loads(base64.b64decode(value))
    encoded = outer["authInfo"].split(".")[1]
    return outer, json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))


def test_fixed_samples_do_not_read_config_or_pem(monkeypatch):
    samples = sample_headers()
    monkeypatch.setattr("app.authorization.USE_SAMPLE_AUTHORIZATION", True)
    monkeypatch.setattr("app.authorization.REFRESH_SAMPLE_AUTHORIZATION", False)
    read_key = Mock(side_effect=AssertionError("fixed samples must not read PEM"))
    monkeypatch.setattr("app.authorization.serialization.load_pem_private_key", read_key)
    # None deliberately has no application settings: the branch must not read any.
    login = create_authorization(None)
    business = create_authorization(None, "new-token-not-used-in-sample")
    assert login == samples.LOGIN_AUTHORIZATION
    assert business == samples.BUSINESS_AUTHORIZATION
    assert create_authorization(None, "another-token") == business
    read_key.assert_not_called()
    login_outer, login_claims = claims(login)
    business_outer, business_claims = claims(business)
    assert login_outer["orgId"] == business_outer["orgId"] == ""
    assert login_claims["sub"] == "tester"
    assert business_claims["sub"] == "chanjet"
    assert login_claims["datas"] == business_claims["datas"] == "5b84cec664cb79c916f890af185d27a9"
    assert login_claims["exp"] == 1792765236025.3765
    assert business_claims["exp"] == 1792765286763.7935
    assert business_claims["access_token"] != "new-token-not-used-in-sample"


def test_login_and_audit_send_exact_sample_headers(monkeypatch):
    samples = sample_headers()
    monkeypatch.setattr("app.authorization.USE_SAMPLE_AUTHORIZATION", True)
    monkeypatch.setattr("app.authorization.REFRESH_SAMPLE_AUTHORIZATION", False)
    config = TPlusApiConfig(url="http://example.test", enabled=True, pem_path="missing.pem")
    def login_request(request, timeout):
        assert request.get_header("Authorization") == samples.LOGIN_AUTHORIZATION
        response = BytesIO(b'{"result":true,"access_token":"new-login-token"}')
        response.status = 200
        return response
    token = LoginClient(login_request).authenticate(LoginConfig(
        "http://example.test/token", "test-user", "test-password", "001", api=config))
    def audit_request(url, data, headers, timeout):
        assert headers["Authorization"] == samples.BUSINESS_AUTHORIZATION
        return 200, '{"code":"0"}'
    client = TPlusApiClient(config, requester=audit_request)
    client.token = token
    assert client.audit_voucher("SA-TEST")[0]


def test_refresh_sample_fields_with_new_expiry_and_current_token(signed_api, monkeypatch):
    from dataclasses import replace
    from test_authorization import decode_verified
    samples = sample_headers()
    monkeypatch.setattr("app.authorization.USE_SAMPLE_AUTHORIZATION", True)
    monkeypatch.setattr("app.authorization.REFRESH_SAMPLE_AUTHORIZATION", True)
    monkeypatch.setattr("app.authorization.time.time", lambda: 1800000000.5)
    # Current application credentials can differ or be absent. Only its PEM is
    # used; the sample supplies the application identity and verified digest.
    config = replace(signed_api, app_key="", app_secret="", org_id="different-org")
    for token, original in ((None, samples.LOGIN_AUTHORIZATION),
                            ("fresh-login-token", samples.BUSINESS_AUTHORIZATION)):
        value = create_authorization(config, token)
        envelope, payload = decode_verified(value, config.pem_path)
        old_envelope, old_payload = claims(original)
        assert envelope["appKey"] == old_envelope["appKey"]
        assert envelope["orgId"] == old_envelope["orgId"]
        assert payload["datas"] == old_payload["datas"]
        assert payload["sub"] == old_payload["sub"]
        assert payload["exp"] == 1800000030500.0
        assert payload.get("access_token") == token
        assert value != original
        assert create_authorization(config, token) != value
