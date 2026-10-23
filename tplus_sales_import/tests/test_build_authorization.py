from pathlib import Path
import subprocess

import pytest

import build_app


@pytest.mark.parametrize("rebuild,fail", [(False, False), (True, False), (True, True)])
def test_build_places_and_preserves_key_beside_config(tmp_path, monkeypatch, rebuild, fail):
    root = tmp_path / "application"
    root.mkdir()
    config = ("[sqlserver]\nip=localhost\nport=1433\ndatabase=test\nuser=test\npassword=\n"
              "[tplus_api]\napp_key=key\napp_secret=secret\norg_id=\npem_path=cjet_pri.pem\n")
    (root / "config.ini").write_text(config, encoding="utf-8")
    (root / "config.ini.example").write_text(config, encoding="utf-8")
    (root / "README.md").write_text("readme", encoding="utf-8")
    (root / "cjet_pri.pem").write_bytes(b"source-key")
    target = root / "dist" / "TplusSalesImport"
    if rebuild:
        target.mkdir(parents=True)
        (target / "cjet_pri.pem").write_bytes(b"deployed-key")
        (target / "config.ini").write_text(config.replace("app_key=key", "app_key=deployed"), encoding="utf-8")
    monkeypatch.setattr(build_app, "__file__", str(root / "build_app.py"))

    def collect(command, **kwargs):
        assert "cryptography" in command
        assert "--add-data" not in command  # The key must remain external.
        target.mkdir(parents=True, exist_ok=True)
        # Simulate COLLECT replacing operational files, without recursive deletion.
        for name in ("config.ini", "cjet_pri.pem"):
            path = target / name
            if path.exists():
                path.unlink()
        if fail:
            raise subprocess.CalledProcessError(1, command)
    monkeypatch.setattr(build_app.subprocess, "run", collect)
    if fail:
        with pytest.raises(subprocess.CalledProcessError):
            build_app.main()
    else:
        build_app.main()
    assert (target / "cjet_pri.pem").read_bytes() == (b"deployed-key" if rebuild else b"source-key")
    deployed = (target / "config.ini").read_text(encoding="utf-8")
    assert ("app_key=deployed" if rebuild else "app_key=key") in deployed


def test_release_migrates_old_pem_path_without_replacing_credentials(tmp_path):
    content = ("[sqlserver]\nip=localhost\nport=1433\ndatabase=test\nuser=test\npassword=\n"
               "[tplus_api]\napp_key=local-key\napp_secret=local-secret\norg_id=123\npem_path=cjet_pri.pem\n")
    (tmp_path / "config.ini").write_text(content, encoding="utf-8")
    existing = tmp_path / "deployed.ini"
    existing.write_text(content.replace("local-key", "deployed-key").replace(
        "pem_path=cjet_pri.pem", r'pem_path="C:\old\cjet_pri.pem"') +
        "\n[login]\nAuthorization=obsolete-header\n", encoding="utf-8")
    import configparser
    parser = configparser.ConfigParser(interpolation=None)
    parser.read_string(build_app.release_config(tmp_path, existing).decode("utf-8"))
    assert parser["tplus_api"]["pem_path"] == "cjet_pri.pem"
    assert parser["tplus_api"]["app_key"] == "deployed-key"
    assert parser["tplus_api"]["app_secret"] == "local-secret"
    assert not parser.has_option("login", "Authorization")
