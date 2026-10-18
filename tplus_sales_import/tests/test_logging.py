import io
import logging
from datetime import datetime, timedelta

from log_util import DailyFileHandler, SafeFormatter, diagnostics, logger, register_secret
from test_import import FakeRepository, run_engine, source_row


def test_log_formatter_masks_passwords_connection_strings_and_tracebacks():
    secret = "test-secret-987"
    register_secret(secret)
    formatter = SafeFormatter("[task=%(task_id)s] %(message)s")
    record = logging.LogRecord("test", logging.ERROR, __file__, 1,
                               "password=%s; copied=%s\nDRIVER={SQL Server};SERVER=host;PWD={%s};", (secret, secret, secret), None)
    text = formatter.format(record)
    assert secret not in text and "DRIVER=" not in text
    assert "[task=-]" in text and "******" in text


def test_exception_diagnostics_preserve_codes_but_not_driver_values():
    try:
        raise Exception("08S01", "connection password=must-not-appear (207)")
    except Exception as exc:
        text = diagnostics(exc)
    assert "08S01" in text and "207" in text and "test_logging.py" in text
    assert "must-not-appear" not in text and "password=" not in text


def test_daily_handler_writes_next_day_to_new_utf8_file(tmp_path):
    handler = DailyFileHandler(tmp_path)
    handler.setFormatter(SafeFormatter("%(message)s"))
    try:
        base = datetime(2026, 10, 17, 12)
        for offset in (0, 1):
            record = logging.LogRecord("test", logging.INFO, __file__, 1, "测试日志", (), None)
            record.created = (base + timedelta(days=offset)).timestamp()
            handler.handle(record)
    finally:
        handler.close()
    assert (tmp_path / "app2026-10-17.log").read_text(encoding="utf-8").strip() == "测试日志"
    assert (tmp_path / "app2026-10-18.log").exists()


def test_task_logging_traces_whole_document_isolation_without_password(tmp_path):
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(SafeFormatter("[task=%(task_id)s] %(message)s"))
    logger.addHandler(handler)
    try:
        repository = FakeRepository()
        repository.fail_source = "BAD"
        result, _ = run_engine(tmp_path, [source_row("GOOD"), source_row("BAD")], repository)
    finally:
        logger.removeHandler(handler)
        handler.close()
    output = stream.getvalue()
    assert result["task_id"] in output
    for message in ("导入任务开始", "数据校验结束", "源单号去重结束", "批次回滚", "按完整单据拆分批次", "单据写入失败", "批次提交成功", "结果文件导出成功", "导入任务结束"):
        assert message in output
    assert "do-not-log-me" not in output and "PWD=" not in output


def test_missing_dependency_diagnostics_include_module_name():
    exc = ModuleNotFoundError("No module named xlrd", name="xlrd")
    assert "missing_module=xlrd" in diagnostics(exc)
