"""Offline isolated environment copied from installed distribution RECORDs.

This is optional for Anaconda hosts with conflicting backports. It does not
install, remove or patch any package in the host environment.
"""
from importlib.metadata import distribution
from pathlib import Path
import shutil
import sys
import venv

PACKAGES = ("pyinstaller", "pyinstaller-hooks-contrib", "altgraph", "pefile", "pywin32-ctypes",
            "setuptools", "packaging", "PyQt5", "PyQt5-sip", "xlrd", "openpyxl", "et-xmlfile", "pyodbc")


def main():
    root = Path(__file__).resolve().parent
    target = root / ".build_env"
    venv.EnvBuilder(with_pip=False).create(str(target))
    site = target / "Lib" / "site-packages"
    site.mkdir(parents=True, exist_ok=True)
    for name in PACKAGES:
        dist = distribution(name)
        metadata_path = Path(dist._path)
        if metadata_path.is_dir():
            shutil.copytree(metadata_path, site / metadata_path.name, dirs_exist_ok=True)
        for record in dist.files or []:
            source = Path(dist.locate_file(record)).resolve()
            destination = (site / str(record)).resolve()
            # RECORD entries can point to Scripts or data directories. Only copy
            # ordinary site-packages files, never escape the isolated environment.
            if site.resolve() not in destination.parents or not source.is_file():
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        print("Copied " + name + " " + dist.version, flush=True)
    print("Build using: " + str(target / "Scripts" / "python.exe") + " build_app.py")


if __name__ == "__main__":
    main()
