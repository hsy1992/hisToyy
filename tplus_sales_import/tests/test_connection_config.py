import logging
import pytest
from app.configuration import DatabaseConfig
from log_util import SafeFormatter, diagnostics


@pytest.mark.parametrize("host", ["127.0.0。1", "127.0.0．1", "127，0.0.1", "256.0.0.1"])
def test_host_address_typo_is_rejected_before_connection(tmp_path, host):
    path = tmp_path / "config.ini"
    path.write_text("[sqlserver]\nip=" + host + "\nport=1433\ndatabase=test\nuser=test\npassword=test-value\n", encoding="utf-8")
    with pytest.raises(ValueError, match="服务器地址"):
        DatabaseConfig.load(path)


def test_driver_label_is_visible_but_real_connection_string_is_hidden():
    formatter = SafeFormatter("%(message)s")
    label = logging.LogRecord("test", logging.INFO, __file__, 1, "连接SQL Server driver=SQL Server Native Client 10.0", (), None)
    assert "SQL Server Native Client 10.0" in formatter.format(label)
    connection = logging.LogRecord("test", logging.INFO, __file__, 1, "DRIVER={SQL Server};SERVER=local;PWD={secret};", (), None)
    assert "PWD" not in formatter.format(connection) and "secret" not in formatter.format(connection)


def test_connection_diagnostics_include_two_digit_native_error():
    assert "native=53" in diagnostics(Exception("08001", "SQL Server connection failed (53)"))


@pytest.mark.parametrize("drivers", [["SQL Server", "ODBC Driver 17 for SQL Server"], []])
def test_driver_inventory_is_logged_before_connection_failure(monkeypatch, drivers):
    import pyodbc
    from unittest.mock import Mock
    from app.database import SqlRepository
    monkeypatch.setattr(pyodbc, "drivers", lambda: drivers)
    log = Mock()

    def connect(*args, **kwargs):
        inventory = log.info.call_args_list[0].args
        assert inventory[0].startswith("ODBC驱动列表")
        assert inventory[1] in (32, 64)
        assert inventory[2:] == (len(drivers), drivers)
        raise RuntimeError("simulated IM002")

    repo = SqlRepository(DatabaseConfig("localhost", 1433, "test", "test", "test-secret"), connector=connect)
    repo.log = log
    with pytest.raises(RuntimeError, match="simulated IM002"):
        repo.open()


def test_driver_inventory_failure_does_not_prevent_connection_attempt(monkeypatch):
    import pyodbc
    from unittest.mock import Mock
    from app.database import SqlRepository

    def broken_inventory():
        raise RuntimeError("inventory unavailable")

    monkeypatch.setattr(pyodbc, "drivers", broken_inventory)
    connect = Mock(side_effect=RuntimeError("connection attempted"))
    repo = SqlRepository(DatabaseConfig("localhost", 1433, "test", "test", "test-secret"), connector=connect)
    repo.log = Mock()
    with pytest.raises(RuntimeError, match="connection attempted"):
        repo.open()
    connect.assert_called_once()
