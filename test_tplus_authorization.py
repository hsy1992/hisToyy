"""T+ Authorization 本地生成、解码、验签及重复生成比较。

运行：python test_tplus_authorization.py
依赖：python -m pip install cryptography
填写下面的参数，或运行后按提示输入。本脚本不发送 HTTP 请求。
"""

import base64
import getpass
import hashlib
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa


# ===== 在这里填写参数；appKey / appSecret 留空则运行时输入 =====
APP_KEY = "8f442ec3-713e-4133-b64c-5d2d828c5426"
APP_SECRET = "jjy3uh"
ORG_ID = "90016346685"
PEM_PATH = r"C:\Users\Administrator\Desktop\T+单据导入程序\cjet_pri.pem"

# 获取 Token 时留空；业务接口调用时填写已取得的 access_token。
ACCESS_TOKEN = ""

# 对应原程序获取账套 Token 的请求头：外层 orgId 固定为空。
# 如果需要外层也携带 ORG_ID，设为 False。
OUTER_ORG_ID_EMPTY = True

# 可粘贴之前生成的完整 Authorization，比较是否完全相同。
PREVIOUS_AUTHORIZATION = ""
# ============================================================


def compact_json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def b64url_encode(value):
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def b64url_decode(value):
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def make_authorization(app_key, app_secret, org_id, private_key,
                       outer_org_id_empty=True, access_token=""):
    # 字段顺序和大小写与原程序保持一致，不添加空格。
    source = compact_json({
        "appkey": app_key,
        "orgid": org_id,
        "appsecret": app_secret,
    })
    payload = {
        "sub": "chanjet" if access_token else "tester",
        # T+ 此版本 SDK 使用 Unix 毫秒时间，有效期 30 秒。
        "exp": time.time() * 1000 + 30000,
        "datas": hashlib.md5(source).hexdigest(),
    }
    if access_token:
        payload["access_token"] = access_token
    signing_input = ".".join((
        b64url_encode(compact_json({"alg": "PS256", "typ": "JWT"})),
        b64url_encode(compact_json(payload)),
    ))
    signature = private_key.sign(
        signing_input.encode("ascii"),
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32),
        hashes.SHA256(),
    )
    envelope = {
        "appKey": app_key,
        "authInfo": signing_input + "." + b64url_encode(signature),
        "orgId": "" if outer_org_id_empty else org_id,
    }
    return base64.b64encode(compact_json(envelope)).decode("ascii")


def decode_and_verify(authorization, public_key):
    envelope = json.loads(base64.b64decode("".join(authorization.split()), validate=True))
    header_part, payload_part, signature_part = envelope["authInfo"].split(".")
    header = json.loads(b64url_decode(header_part))
    if header.get("alg") != "PS256":
        raise ValueError("JWT 算法不是 PS256")
    public_key.verify(
        b64url_decode(signature_part),
        (header_part + "." + payload_part).encode("ascii"),
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32),
        hashes.SHA256(),
    )
    return envelope, header, json.loads(b64url_decode(payload_part))


def compare_authorizations(first, second, public_key):
    """分别验签后比较各层，避免只看 Base64 的相同前缀。"""
    left, _, left_payload = decode_and_verify(first, public_key)
    right, _, right_payload = decode_and_verify(second, public_key)
    print("两份请求头均通过同一把密钥的签名校验")
    print("完整 Authorization 相同:", "".join(first.split()) == "".join(second.split()))
    for name in ("appKey", "orgId"):
        print(f"外层 {name} 相同:", left.get(name) == right.get(name))
    for name in ("sub", "datas", "exp", "access_token"):
        print(f"JWT {name} 相同:", left_payload.get(name) == right_payload.get(name))
    print("JWT 签名字节相同:",
          b64url_decode(left["authInfo"].split(".")[2]) ==
          b64url_decode(right["authInfo"].split(".")[2]))


def main():
    app_key = APP_KEY.strip() or input("appKey: ").strip()
    app_secret = APP_SECRET or getpass.getpass("appSecret（输入不显示）: ")
    if not app_key or not app_secret:
        raise ValueError("appKey 和 appSecret 不能为空")
    private_key = serialization.load_pem_private_key(
        Path(PEM_PATH).read_bytes(), password=None
    )
    if not isinstance(private_key, rsa.RSAPrivateKey):
        raise ValueError("PEM 必须是 RSA 私钥")

    first = make_authorization(
        app_key, app_secret, ORG_ID, private_key, OUTER_ORG_ID_EMPTY, ACCESS_TOKEN
    )
    second = make_authorization(
        app_key, app_secret, ORG_ID, private_key, OUTER_ORG_ID_EMPTY, ACCESS_TOKEN
    )
    envelope, header, payload = decode_and_verify(first, private_key.public_key())
    _, _, second_payload = decode_and_verify(second, private_key.public_key())

    print("\n本地验签：两次均通过（尚未验证 T+ 服务端是否接受）")
    print("JWT header:", json.dumps(header, ensure_ascii=False))
    visible_payload = dict(payload)
    if "access_token" in visible_payload:
        visible_payload["access_token"] = "******"
    print("签名模式:", "业务调用" if ACCESS_TOKEN else "获取 Token")
    print("JWT payload:", json.dumps(visible_payload, ensure_ascii=False))
    print("外层 orgId:", repr(envelope["orgId"]))
    expires_at = datetime.fromtimestamp(
        payload["exp"] / 1000, timezone(timedelta(hours=8))
    )
    print("SDK 写入的过期时间（北京时间）:", expires_at.isoformat(timespec="milliseconds"))
    print("两次 datas 是否相同:", payload["datas"] == second_payload["datas"])
    print("两次完整 Authorization 是否相同:", first == second)
    if PREVIOUS_AUTHORIZATION.strip():
        previous = "".join(PREVIOUS_AUTHORIZATION.split())
        # 支持从控制台复制带 Authorization: 标签的整行。
        if previous.lower().startswith("authorization:"):
            previous = previous[len("authorization:"):]
        print("\n与之前请求头逐项比较：")
        try:
            compare_authorizations(previous, first, private_key.public_key())
        except Exception as exc:
            print("旧请求头解析或验签失败：", type(exc).__name__)
            print("请检查是否复制完整，以及是否使用同一把私钥。")

    print("\n第一次生成，可复制到 HTTP 请求头（不加 Bearer）：")
    print("Authorization: " + first)
    print("\n第二次生成，用于比较：")
    print("Authorization: " + second)
    print("\nSDK 写入 30 秒有效期，发送前请重新运行生成。")
    print("本地验签只检查签名，服务端是否校验过期时间需用实际接口确认。")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # 不输出参数、私钥正文或包含敏感局部变量的 traceback。
        print("生成或验签失败：", type(exc).__name__)
        print("请检查参数、PEM 路径及密钥格式。")
        raise SystemExit(1)
