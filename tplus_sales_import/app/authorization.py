"""T+ OpenAPI v2 signed Authorization matching the verified request samples."""
import base64
import hashlib
import json
from pathlib import Path
import time
import uuid

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from log_util import logger, register_secret


# 临时测试：使用成功样例的应用参数。恢复配置参数签名时改为 False。
USE_SAMPLE_AUTHORIZATION = False
# True: 保留样例 appKey/orgId/datas，每次更新 exp 和本次业务 Token 后签名。
# False: 原样重放两段固定 Authorization，仅用于对照测试。
REFRESH_SAMPLE_AUTHORIZATION = True


class AuthorizationError(ValueError):
    pass


def create_authorization(config, access_token=None, *, use_sample=None):
    sample_mode = USE_SAMPLE_AUTHORIZATION if use_sample is None else use_sample
    trace_id = uuid.uuid4().hex[:12]
    mode = "business" if access_token else "login"

    def trace(stage, message, *args):
        logger.info("【Authorization生成】 trace=%s mode=%s stage=%s " + message,
                    trace_id, mode, stage, *args, extra={"unmasked": True})

    sample_envelope = None
    sample_payload = None
    if sample_mode:
        from ._authorization_samples import LOGIN_AUTHORIZATION, BUSINESS_AUTHORIZATION
        authorization = BUSINESS_AUTHORIZATION if access_token else LOGIN_AUTHORIZATION
        if not REFRESH_SAMPLE_AUTHORIZATION:
            register_secret(authorization)
            trace("固定样例", "Authorization=%s", authorization)
            return authorization
        sample_envelope = json.loads(base64.b64decode(authorization))
        encoded_payload = sample_envelope["authInfo"].split(".")[1]
        sample_payload = json.loads(base64.urlsafe_b64decode(
            encoded_payload + "=" * (-len(encoded_payload) % 4)))
    elif not config.app_key or not config.app_secret:
        raise AuthorizationError("请在 config.ini 的 [tplus_api] 中配置 app_key、app_secret。")
    try:
        private_key = serialization.load_pem_private_key(
            Path(config.pem_path).read_bytes(), password=None)
    except OSError:
        raise AuthorizationError("无法读取 cjet_pri.pem，请将私钥放在 config.ini 同目录并检查 pem_path。") from None
    except (ValueError, TypeError):
        raise AuthorizationError("cjet_pri.pem 格式无效，请使用未加密的 RSA PEM 私钥。") from None
    if not isinstance(private_key, rsa.RSAPrivateKey):
        raise AuthorizationError("cjet_pri.pem 必须是 RSA 私钥。")
    trace("签名参数", "source=%s pem_path=%s key_bits=%d alg=PS256 "
          "hash=SHA256 mgf=MGF1-SHA256 salt_length=32",
          "sample" if sample_mode else "config", str(Path(config.pem_path).resolve()), private_key.key_size)

    def compact(value):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    def b64url(value):
        return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")

    if sample_mode:
        # The verified datas digest is reusable for the exact sample application
        # parameters; it does not recover or reveal the original appSecret.
        app_key, org_id = sample_envelope["appKey"], sample_envelope["orgId"]
        digest = sample_payload["datas"]
        trace("MD5", "source=sample datas=%s", digest)
    else:
        app_key, org_id = config.app_key, config.org_id
        source = compact(dict(appkey=app_key, orgid=org_id,
                              appsecret=config.app_secret))
        digest = hashlib.md5(source).hexdigest()
        trace("MD5", "source_json=%s utf8_length=%d datas=%s",
              source.decode("utf-8"), len(source), digest)
    payload = dict(sub="chanjet" if access_token else "tester",
                   exp=time.time() * 1000 + 30000,
                   datas=digest)
    if access_token:
        payload["access_token"] = access_token
    header = dict(alg="PS256", typ="JWT")
    trace("JWT载荷", "header_json=%s payload_json=%s",
          compact(header).decode("utf-8"), compact(payload).decode("utf-8"))
    message = b64url(compact(header)) + "." + b64url(compact(payload))
    trace("签名输入", "signing_input=%s", message)
    signature = private_key.sign(message.encode("ascii"),
                                 padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32),
                                 hashes.SHA256())
    envelope = dict(appKey=app_key, authInfo=message + "." + b64url(signature),
                    orgId=org_id)
    trace("签名结果", "signature_base64url=%s jwt=%s", b64url(signature), envelope["authInfo"])
    trace("外层JSON", "envelope_json=%s", compact(envelope).decode("utf-8"))
    authorization = base64.b64encode(compact(envelope)).decode("ascii")
    register_secret(authorization)
    trace("完成", "Authorization=%s", authorization)
    return authorization
