import os
import sys
from pathlib import Path
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from app.configuration import TPlusApiConfig


@pytest.fixture(autouse=True)
def use_generated_authorization_in_tests(monkeypatch):
    # Tests normally exercise fresh signing; fixed-sample tests opt in explicitly.
    monkeypatch.setattr("app.authorization.USE_SAMPLE_AUTHORIZATION", False)


@pytest.fixture
def signed_api(tmp_path):
    key = rsa.generate_private_key(public_exponent=65537, key_size=1024)
    path = tmp_path / "cjet_pri.pem"
    path.write_bytes(key.private_bytes(serialization.Encoding.PEM,
                                      serialization.PrivateFormat.TraditionalOpenSSL,
                                      serialization.NoEncryption()))
    return TPlusApiConfig(url="http://example.test", account="300216", user="login-user",
                          password="login-password", app_key="test-app", app_secret="test-secret",
                          pem_path=str(path), enabled=True)
