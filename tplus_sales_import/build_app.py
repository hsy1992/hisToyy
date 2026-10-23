"""Build in this folder only. Does not download software or connect to SQL Server."""
import configparser
import io
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def release_config(root, existing_config):
    source = root / "config.ini"
    if not source.exists():
        source = root / "config.ini.example"
    if not existing_config.exists():
        return source.read_bytes()
    # Preserve deployed credentials; add missing sections/keys on upgrades.
    deployed = configparser.ConfigParser(interpolation=None)
    defaults = configparser.ConfigParser(interpolation=None)
    from app.configuration import DatabaseConfig
    DatabaseConfig.load(existing_config)
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            deployed.read(existing_config, encoding=encoding)
            break
        except UnicodeDecodeError:
            continue
    defaults.read(source, encoding="utf-8-sig")
    changed = False
    if not deployed.has_section("login") and defaults.has_section("login"):
        deployed["login"] = dict(defaults["login"])
        changed = True
    if deployed.has_section("login") and deployed.remove_option("login", "Authorization"):
        changed = True
    if defaults.has_section("tplus_api"):
        if not deployed.has_section("tplus_api"):
            deployed["tplus_api"] = dict(defaults["tplus_api"])
            changed = True
        else:
            for key in ("app_key", "app_secret", "org_id"):
                if key not in deployed["tplus_api"] and key in defaults["tplus_api"]:
                    deployed["tplus_api"][key] = defaults["tplus_api"][key]
                    changed = True
        if deployed["tplus_api"].get("pem_path") != "cjet_pri.pem":
            deployed["tplus_api"]["pem_path"] = "cjet_pri.pem"
            changed = True
    if not changed:
        return existing_config.read_bytes()
    output = io.StringIO()
    deployed.write(output)
    return output.getvalue().encode("utf-8")


def main():
    root = Path(__file__).resolve().parent
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--windowed", "--onedir",
               "--name", "TplusSalesImport", "--distpath", str(root / "dist"),
               "--workpath", str(root / "build"), "--specpath", str(root),
               "--hidden-import", "xlrd", "--hidden-import", "openpyxl",
               "--hidden-import", "pyodbc", "--exclude-module", "numpy",
               "--collect-all", "cryptography",
               "--exclude-module", "pandas", "--exclude-module", "PySide6",
               "--exclude-module", "PyQt6", str(root / "main.py")]
    target = root / "dist" / "TplusSalesImport"
    if root not in target.resolve().parents:
        raise RuntimeError("Build output must stay inside this application folder")
    existing_config = target / "config.ini"
    preserved_config = release_config(root, existing_config)
    # Keep the private key external, beside the deployed config (not in _internal).
    # On rebuild, preserve the key paired with the deployed application settings.
    pem_source = target / "cjet_pri.pem"
    if not pem_source.is_file():
        pem_source = root / "cjet_pri.pem"
    if not pem_source.is_file():
        raise FileNotFoundError("请先将 cjet_pri.pem 放在源码 config.ini 同目录，再执行打包。")
    preserved_pem = pem_source.read_bytes()
    # PyInstaller replaces COLLECT's destination. Preserve operational data as
    # well as the user's config before allowing that replacement.
    with tempfile.TemporaryDirectory(prefix=".build-preserve-", dir=str(root)) as directory:
        backup = Path(directory).resolve()
        if backup.parent != root:
            raise RuntimeError("Unexpected backup directory")
        preserved_dirs = []
        for name in ("logs", "runtime"):
            source = target / name
            if source.is_dir():
                shutil.copytree(source, backup / name)
                preserved_dirs.append(name)
        try:
            subprocess.run(command, cwd=str(root), check=True)
        finally:
            target.mkdir(parents=True, exist_ok=True)
            if preserved_config is not None:
                existing_config.write_bytes(preserved_config)
            elif not existing_config.exists():
                shutil.copy2(root / "config.ini.example", existing_config)
            (target / "cjet_pri.pem").write_bytes(preserved_pem)
            for name in preserved_dirs:
                shutil.copytree(backup / name, target / name, dirs_exist_ok=True)
    shutil.copy2(root / "config.ini.example", target / "config.ini.example")
    shutil.copy2(root / "README.md", target / "README.md")
    print("Build ready: " + str(target / "TplusSalesImport.exe"))
    print("config.ini and cjet_pri.pem are beside the executable. Authorization is signed per request.")


if __name__ == "__main__":
    main()
