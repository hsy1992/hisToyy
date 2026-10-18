"""Build in this folder only. Does not download software or connect to SQL Server."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main():
    root = Path(__file__).resolve().parent
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--windowed", "--onedir",
               "--name", "TplusSalesImport", "--distpath", str(root / "dist"),
               "--workpath", str(root / "build"), "--specpath", str(root),
               "--hidden-import", "xlrd", "--hidden-import", "openpyxl",
               "--hidden-import", "pyodbc", "--exclude-module", "numpy",
               "--exclude-module", "pandas", "--exclude-module", "PySide6",
               "--exclude-module", "PyQt6", str(root / "main.py")]
    target = root / "dist" / "TplusSalesImport"
    if root not in target.resolve().parents:
        raise RuntimeError("Build output must stay inside this application folder")
    existing_config = target / "config.ini"
    preserved_config = existing_config.read_bytes() if existing_config.exists() else None
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
            for name in preserved_dirs:
                shutil.copytree(backup / name, target / name, dirs_exist_ok=True)
    shutil.copy2(root / "config.ini.example", target / "config.ini.example")
    shutil.copy2(root / "README.md", target / "README.md")
    print("Build ready: " + str(target / "TplusSalesImport.exe"))
    print("Edit config.ini beside the executable before testing the connection.")


if __name__ == "__main__":
    main()
