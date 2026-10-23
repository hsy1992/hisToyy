"""Standalone copy of the project's log_util interface and log format.

Keeps the original application untouched. Passwords/connection strings and raw
exception values are never needed for diagnostics. Does not configure root logging.
"""
import logging
import os
from pathlib import Path
import re
import sys
import threading
import traceback
from datetime import datetime

_LOCK = threading.Lock()
_SECRETS = set()


def register_secret(value):
    if value:
        with _LOCK:
            _SECRETS.add(str(value))
            _SECRETS.add(str(value).replace("}", "}}"))


def redact(value):
    text = str(value)
    text = re.sub(r"(?i)\bDRIVER\s*=[^\r\n]*;[^\r\n]*", "[连接串已隐藏]", text)
    text = re.sub(r"(?i)\b(?:PWD|password)\s*=\s*(\{(?:[^}]|}})*\}|[^;\r\n]*)", "PWD=******", text)
    with _LOCK:
        secrets = sorted(_SECRETS, key=len, reverse=True)
    for secret in secrets:
        text = text.replace(secret, "******")
    return text


class SafeFormatter(logging.Formatter):
    def format(self, record):
        if not hasattr(record, "task_id"):
            record.task_id = "-"
        text = super().format(record)
        return text if getattr(record, "unmasked", False) else redact(text)


class DailyFileHandler(logging.Handler):
    """Original appYYYY-MM-DD.log convention, switching at the next log event."""
    def __init__(self, directory):
        super().__init__()
        self.directory = Path(directory)
        self.day = None
        self.stream = None

    def emit(self, record):
        try:
            day = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d")
            if self.day != day or self.stream is None:
                if self.stream:
                    self.stream.close()
                self.directory.mkdir(parents=True, exist_ok=True)
                self.stream = (self.directory / ("app" + day + ".log")).open("a", encoding="utf-8")
                self.day = day
            self.stream.write(self.format(record) + "\n")
            self.stream.flush()
        except Exception:
            # Never feed an unsafe original record to logging.handleError's stderr dump.
            if sys.stderr is not None:
                sys.stderr.write("T+日志文件无法写入，请检查logs目录权限或磁盘空间。\n")

    def close(self):
        with self.lock:
            if self.stream is not None:
                self.stream.close()
                self.stream = None
            super().close()


def diagnostics(exc):
    """Exception category, SQLSTATE/native code and frames, without driver message/locals."""
    state = str(exc.args[0]) if getattr(exc, "args", None) else ""
    state = state if re.fullmatch(r"[A-Z0-9]{5}", state) else "-"
    native = sorted(set(re.findall(r"\((\d{1,10})\)", str(getattr(exc, "args", "")))))
    frames = " > ".join(f"{Path(frame.filename).name}:{frame.lineno}:{frame.name}"
                        for frame in traceback.extract_tb(exc.__traceback__))
    missing = getattr(exc, "name", None) if isinstance(exc, ImportError) else None
    module_info = " missing_module=" + str(missing) if missing else ""
    return f"type={type(exc).__name__}{module_info} SQLSTATE={state} native={','.join(native) or '-'} frames={frames or '-'}"


log_dir = (Path(sys.executable).resolve().parent if getattr(sys, "frozen", False)
           else Path(__file__).resolve().parent) / "logs"
logger = logging.getLogger("ImportTool.SaleDelivery")
logger.setLevel(logging.INFO)
logger.propagate = False
if not logger.handlers:
    formatter = SafeFormatter("%(asctime)s - %(levelname)s - %(module)s - [task=%(task_id)s] %(message)s")
    file_handler = DailyFileHandler(log_dir)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    if sys.stdout is not None:
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(formatter)
        logger.addHandler(console)
