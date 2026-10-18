from decimal import Decimal
from datetime import date, datetime
import threading

import pytest
from PyQt5.QtWidgets import QApplication

from app.database import DocumentError, SqlRepository, SystemFailure, bind_value
from app.domain import key, validate_rows, build_payload
from app.gui import ImportWindow, RowModel
from test_import import cache, config, source_row


class Cursor:
    def __init__(self):
        self.commands = []
    def execute(self, sql, *params):
        self.commands.append((sql, params))
        return self
    def close(self): pass


class Connection:
    def __init__(self):
        self.autocommit, self.commits, self.rollbacks = True, 0, 0
        self.cursor_object = Cursor()
    def cursor(self): return self.cursor_object
    def commit(self): self.commits += 1
    def rollback(self): self.rollbacks += 1


@pytest.mark.parametrize("failure", [None, "create", "insert", "select", "fetch", "cleanup", "fetch_and_cleanup", "fetch_and_close"])
def test_dedup_drops_temporary_table_and_preserves_original_error(failure):
    class PendingCursor(Cursor):
        def __init__(self):
            super().__init__()
            self.drops = 0
            self.closed = False

        def execute(self, sql, *params):
            super().execute(sql, *params)
            if sql.startswith("IF OBJECT_ID"):
                self.drops += 1
                if self.drops == 2 and failure in ("cleanup", "fetch_and_cleanup"):
                    raise RuntimeError("cleanup failure")
            if failure == "create" and "INTO #TplusPending" in sql:
                raise RuntimeError("create failure")
            if failure == "insert" and sql.startswith("INSERT INTO #TplusPending"):
                raise RuntimeError("insert failure")
            if failure == "select" and sql.startswith("SELECT h.ID"):
                raise RuntimeError("select failure")
            return self

        def fetchall(self):
            if failure in ("fetch", "fetch_and_cleanup", "fetch_and_close"):
                raise RuntimeError("fetch failure")
            return [(42, "SA2026101200001", "SOURCE")]

        def close(self):
            self.closed = True
            if failure == "fetch_and_close":
                raise RuntimeError("close failure")

    repo = SqlRepository(config(), connector=lambda *args: None)
    repo.connection = Connection()
    cursor = PendingCursor()
    repo.connection.cursor_object = cursor
    if failure:
        expected = "fetch" if failure.startswith("fetch") else failure
        with pytest.raises(RuntimeError, match=expected + " failure"):
            repo.find_existing(["SOURCE"])
    else:
        assert repo.find_existing(["SOURCE"]) == {"source": [dict(id=42, code="SA2026101200001")]}
    assert cursor.drops == 2
    assert cursor.closed
    assert repo.connection.commits == repo.connection.rollbacks == 0


class TransactionRepository(SqlRepository):
    def __init__(self):
        super().__init__(config(), connector=lambda *args: None)
        self.connection = Connection()
        self.received = []
        self.verified = True
        self.fail_details = False
    def query(self, *args): return []
    def find_existing(self, *args): return {}
    def verify_batch(self, docs, mapping): return self.verified
    def bulk_insert(self, cursor, table, records, output=False):
        self.received.append((table, records))
        if output:
            # Deliberately reverse OUTPUT order.
            return [(item["ExternalCode"], 100 + n, item["code"]) for n, item in reversed(list(enumerate(records)))]
        if self.fail_details: raise DocumentError("detail failed")
        return []


def documents():
    docs = validate_rows([source_row("A"), source_row("B")], cache(), threading.Event(), lambda *args: None)
    for n, doc in enumerate(docs): doc.code = f"SA20261012{n+1:05d}"
    return docs


@pytest.mark.parametrize("field", [None, "voucherState", "makerid", "auditorid", "agencyid", "isCarriedForwardOut", "voucherdate", "pubuserdefnvc1", "detail_pubuserdefnvc1", "detail_pubuserdefnvc2"])
def test_header_verification_covers_all_configured_business_fields(field):
    doc = documents()[0]
    header, details = build_payload(doc)
    stored_header = {name: bind_value(value) for name, value in header.items()}
    stored_header["ID"] = 42
    if field and not field.startswith("detail_"):
        stored_header[field] = datetime(2001, 1, 1) if field == "voucherdate" else 999
    stored_details = [dict(row, idSaleDeliveryDTO=42) for row in details]
    if field and field.startswith("detail_"):
        stored_details[0][field[len("detail_"):]] = "WRONG-SOURCE"
    repo = SqlRepository(config(), connector=lambda *args: None)

    def query(sql, *params):
        selected = [name.strip("[]") for name in sql.split(" FROM ")[0][len("SELECT "):].split(",")]
        records = stored_details if "FROM dbo.SA_SaleDelivery_b" in sql else [stored_header]
        return [{name: row[name] for name in selected} for row in records]

    repo.query = query
    assert repo.verify_batch([doc], {key(doc.source): (42, doc.code)}) is (field is None)


def test_output_id_mapping_is_by_source_not_result_order():
    repo = TransactionRepository()
    mapping = repo.write_batch(documents())
    assert mapping == {"b": 101, "a": 100}
    details = repo.received[1][1]
    assert [r["idSaleDeliveryDTO"] for r in details] == [100, 101]
    assert repo.connection.commits == 1 and repo.connection.rollbacks == 0


@pytest.mark.parametrize("failure", ["details", "verification"])
def test_entire_batch_rolls_back_on_detail_or_verification_failure(failure):
    repo = TransactionRepository()
    repo.fail_details = failure == "details"
    repo.verified = failure != "verification"
    with pytest.raises((DocumentError, SystemFailure)):
        repo.write_batch(documents())
    assert repo.connection.commits == 0 and repo.connection.rollbacks == 1
    assert repo.connection.autocommit is True


def test_bulk_parameters_stay_under_server_limits_and_do_not_interpolate_source():
    repo = SqlRepository(config(), connector=lambda *args: None)
    repo.validate_payload = lambda *args: None
    cursor = Cursor()
    dangerous = "x'); DROP TABLE anything;--"
    records = [{f"col{n}": dangerous if n == 0 else Decimal("1.00") for n in range(40)} for _ in range(121)]
    repo.bulk_insert(cursor, "SA_SaleDelivery_b", records)
    assert len(cursor.commands) == 3
    for sql, params in cursor.commands:
        assert dangerous not in sql and dangerous in params and len(params) <= 2000


def test_bulk_date_binding_supports_legacy_sql_server_driver():
    class LegacyCursor(Cursor):
        def execute(self, sql, *params):
            if any(type(value) is date for value in params):
                raise RuntimeError("HYC00 SQLBindParameter: date unsupported")
            return super().execute(sql, *params)

    repo = SqlRepository(config(), connector=lambda *args: None)
    repo.validate_payload = lambda *args: None
    cursor = LegacyCursor()
    timestamp = datetime(2026, 10, 18, 12, 0, 0, 123456)
    payload = dict(voucherdate=date(2026, 10, 12), madedate=date(2026, 10, 12),
                   auditeddate=date(2026, 10, 12), createdtime=timestamp)
    repo.bulk_insert(cursor, "SA_SaleDelivery", [payload])
    assert cursor.commands[0][1] == (datetime(2026, 10, 12),) * 3 + (timestamp,)
    assert type(payload["voucherdate"]) is date


@pytest.fixture(scope="module")
def qapp():
    application = QApplication.instance() or QApplication([])
    yield application


@pytest.mark.parametrize("area", [(0, 0, 1920, 1040), (1920, 0, 2560, 1400), (-1366, 0, 1366, 728)])
def test_window_starts_at_two_thirds_of_current_available_screen(qapp, tmp_path, monkeypatch, area):
    from PyQt5.QtCore import QRect
    from types import SimpleNamespace
    rectangle = QRect(*area)
    screen = SimpleNamespace(availableGeometry=lambda: rectangle)
    monkeypatch.setattr(QApplication, "screenAt", lambda position: screen)
    window = ImportWindow(tmp_path / "missing.ini")
    assert window.width() == area[2] * 2 // 3
    assert window.height() == area[3] * 2 // 3
    assert window.x() == area[0] + (area[2] - window.width()) // 2
    assert window.y() == area[1] + (area[3] - window.height()) // 2
    assert not window.isMaximized() and not window.isFullScreen()
    window.close()


def test_small_screen_layout_does_not_expand_window_after_show(qapp, tmp_path):
    window = ImportWindow(tmp_path / "missing.ini")
    expected = window.size()
    window.show()
    qapp.processEvents()
    assert window.size() == expected
    assert not window.isMaximized() and not window.isFullScreen()
    window.close()


def test_window_is_read_only_and_does_not_connect_on_launch(qapp, tmp_path, monkeypatch):
    ini = tmp_path / "config.ini"
    ini.write_text("[sqlserver]\nip=localhost\nport=1433\ndatabase=test_db\nuser=test\npassword=private-value\n", encoding="utf-8")
    window = ImportWindow(ini)
    assert window.worker is None and window.tested is None
    assert not window.import_button.isEnabled()
    assert "private-value" not in window.config_label.text()
    window.model.set_rows([source_row()], list(source_row().values))
    window.tested = window.config
    window.update_buttons()
    assert window.import_button.isEnabled()
    ini.write_text(ini.read_text(encoding="utf-8").replace("test_db", "changed_db"), encoding="utf-8")
    started = []
    monkeypatch.setattr(window, "start_worker", lambda worker, callback: started.append(worker))
    window.start_import()
    assert len(started) == 1 and started[0].action == "import"
    assert started[0].config.database == "changed_db"
    assert window.worker is None and window.tested is None
    assert "changed_db" in window.config_label.text()
    window.close()


def test_model_handles_100k_rows_without_cell_widgets(qapp):
    model = RowModel()
    rows = [source_row(str(n), number=n + 2) for n in range(100000)]
    model.set_rows(rows, ["用友单号", "数量"])
    assert model.rowCount() == 100000
    assert model.data(model.index(99999, 1)) == "99999"
    assert not (model.flags(model.index(0, 0)) & 2)  # Qt.ItemIsEditable


def test_failed_rollback_never_enables_autocommit():
    from app.database import CommitUnknown
    repo = TransactionRepository()
    repo.fail_details = True
    def failed_rollback():
        raise OSError("connection lost")
    repo.connection.rollback = failed_rollback
    with pytest.raises(CommitUnknown):
        repo.write_batch(documents())
    assert repo.connection.autocommit is False


def test_missing_dependency_error_names_actual_interpreter(qapp, monkeypatch):
    import sys
    import app.gui as gui
    def missing(*args):
        raise ModuleNotFoundError("No module named xlrd", name="xlrd")
    monkeypatch.setattr(gui, "read_xls", missing)
    worker = gui.TaskWorker("load", source="test.xls")
    failures = []
    worker.failed.connect(failures.append)
    worker.run()
    assert len(failures) == 1
    assert "xlrd" in failures[0] and sys.executable in failures[0]


def test_review_bad_ini_does_not_prevent_window_or_reload(qapp, tmp_path):
    path = tmp_path / "config.ini"
    path.write_text("password=must-not-appear\n", encoding="utf-8")
    window = ImportWindow(path)
    assert "配置文件语法错误" in window.config_label.text()
    assert "must-not-appear" not in window.config_label.text()
    assert window.config is None and not window.import_button.isEnabled()
    assert window.reload_config() is False
    window.close()


def test_import_gate_requires_loaded_file_only(qapp, tmp_path):
    path = tmp_path / "config.ini"
    path.write_text("[sqlserver]\nip=localhost\nport=1433\ndatabase=test_db\nuser=test\npassword=test-value\n", encoding="utf-8")
    window = ImportWindow(path)
    window.model.set_rows([source_row()], list(source_row().values))
    window.update_buttons()
    assert window.import_button.isEnabled()
    assert window.tested is None
    assert "可以导入" in window.import_gate_label.text()
    window.tested = window.config
    window.update_buttons()
    assert window.import_button.isEnabled()
    assert "可以导入" in window.import_gate_label.text()
    window.close()


def test_async_test_then_file_load_enables_import(qapp, tmp_path, monkeypatch):
    import time
    import app.gui as gui
    from PyQt5.QtTest import QTest
    path = tmp_path / "config.ini"
    path.write_text("[sqlserver]\nip=localhost\nport=1433\ndatabase=test_db\nuser=test\npassword=test-value\n", encoding="utf-8")
    class Repository:
        def __init__(self, config): self.config = config
        def open(self): return self.config.database
        def close(self): pass
    monkeypatch.setattr(gui, "SqlRepository", Repository)
    row = source_row()
    monkeypatch.setattr(gui, "read_xls", lambda *args: ([row], list(row.values)))
    monkeypatch.setattr(gui.QFileDialog, "getOpenFileName", lambda *args: ("fixture.xls", ""))
    window = ImportWindow(path)
    def wait_for_completion():
        deadline = time.monotonic() + 3
        while window.worker is not None and time.monotonic() < deadline:
            qapp.processEvents()
            QTest.qWait(5)
        assert window.worker is None
    window.test_connection()
    wait_for_completion()
    window.choose_file()
    wait_for_completion()
    assert window.import_button.isEnabled()
    assert "连接成功" in window.connection_label.text()
    assert "可以导入" in window.import_gate_label.text()
    window.close()


def test_import_without_connection_test_creates_automatic_connect_task(qapp, tmp_path, monkeypatch):
    path = tmp_path / "config.ini"
    path.write_text("[sqlserver]\nip=localhost\nport=1433\ndatabase=test_db\nuser=test\npassword=test-value\n", encoding="utf-8")
    window = ImportWindow(path)
    window.source = "source.xls"
    window.model.set_rows([source_row()], list(source_row().values))
    window.update_buttons()
    assert window.tested is None and window.import_button.isEnabled()
    tasks = []
    monkeypatch.setattr(window, "start_worker", lambda worker, callback: tasks.append(worker))
    window.start_import()
    assert len(tasks) == 1 and tasks[0].action == "import"
    assert tasks[0].config.database == "test_db"
    window.close()
