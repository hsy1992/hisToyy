import json
import threading
import urllib.error
import urllib.request

import pytest

from callback_probe import ProbeServer


@pytest.fixture
def probe():
    server = ProbeServer(("127.0.0.1", 0))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield "http://127.0.0.1:" + str(server.server_port)
    server.shutdown()
    server.server_close()
    thread.join(2)


def post(base, path, payload):
    request = urllib.request.Request(base + path, json.dumps(payload).encode(),
                                     {"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=3) as response:
        return response.status, json.load(response)


def test_page_and_health_are_accessible(probe):
    with urllib.request.urlopen(probe, timeout=3) as response:
        page = response.read().decode("utf-8")
    assert "/chanjet/messages" in page
    assert "尚未解密" in page
    with urllib.request.urlopen(probe + "/health", timeout=3) as response:
        assert json.load(response) == {"status": "ok", "mode": "connectivity_only"}


def test_synthetic_test_and_callback_have_separate_counts(probe):
    assert post(probe, "/probe", {"test": "connectivity"})[0] == 200
    assert post(probe, "/chanjet/messages", {"encryptMsg": "private-encrypted-body"}) == (
        200, {"result": "success"})
    with urllib.request.urlopen(probe + "/api/status", timeout=3) as response:
        raw = response.read().decode()
    status = json.loads(raw)
    assert status["probe_count"] == 1
    assert status["callback_count"] == 1
    assert status["ticket_verified"] is False
    assert "private-encrypted-body" not in raw
    assert status["events"][0]["kind"] == "callback"


@pytest.mark.parametrize("path,payload,code", [
    ("/chanjet/messages", {}, 400),
    ("/chanjet/messages", {"encryptMsg": ""}, 400),
    ("/chanjet/messages", {"encryptMsg": 1}, 400),
    ("/probe", [], 400),
    ("/unknown", {}, 404),
])
def test_invalid_callback_is_not_counted(probe, path, payload, code):
    with pytest.raises(urllib.error.HTTPError) as error:
        post(probe, path, payload)
    assert error.value.code == code
    with urllib.request.urlopen(probe + "/api/status", timeout=3) as response:
        assert json.load(response)["callback_count"] == 0


def test_callback_body_is_not_written_to_console(probe, capsys):
    post(probe, "/chanjet/messages", {"encryptMsg": "do-not-log-this"})
    assert "do-not-log-this" not in capsys.readouterr().out


def test_request_size_is_limited(probe):
    with pytest.raises(urllib.error.HTTPError) as error:
        post(probe, "/probe", {"test": "x" * 70000})
    assert error.value.code == 413
