from copy import deepcopy
import threading

import pytest
from PyQt5.QtWidgets import QApplication, QDialog

from app.database import CommitUnknown, PreflightError, SqlRepository, SystemFailure, bind_value
from app.domain import build_payload, key, validate_rows
from app.gui import ImportWindow, UndoConfirmDialog
from app.undo import UndoSession
from test_import import cache, config, source_row


def imported_result():
    rows = [source_row("NEW-A"), source_row("NEW-B"), source_row("OLD-C"), source_row("BAD-D")]
    docs = validate_rows(rows, cache(), threading.Event(), lambda *args: None)
    for index, doc in enumerate(docs):
        doc.code = f"SA20261012{index+1:05d}"
        for row in doc.rows:
            row.status = "导入成功" if index < 2 else ("重复跳过" if index == 2 else "校验失败")
            row.header_id, row.sa_code = index + 101, doc.code
    return dict(task_id="undo-test", rows=rows, message="", report="", database=config().database)


def session():
    return UndoSession.from_result(config(), "source.xls", imported_result())


class UndoRepository(SqlRepository):
    """Transactional in-memory store, including independent historical data."""
    def __init__(self, receipt):
        super().__init__(config(), connector=lambda *args: None)
        self.store = {"ARAP_Detail": [], "SA_SaleDelivery_b": [], "SA_SaleDelivery": []}
        self.commands = []
        self.failure = None
        self.triggers, self.cascades = False, False
        for doc in receipt.documents:
            header, details = build_payload(doc)
            identifier = receipt.mapping[key(doc.source)][0]
            self.store["SA_SaleDelivery"].append(dict(header, ID=identifier, ts=b"version1"))
            for index, detail in enumerate(details):
                detail_id = identifier * 10 + index
                self.store["SA_SaleDelivery_b"].append(dict(detail, ID=detail_id,
                                                           idSaleDeliveryDTO=identifier))
                self.store["ARAP_Detail"].append(dict(ID=identifier * 100 + index, voucherID=identifier,
                                                      voucherDetailID=detail_id))
        self.store["SA_SaleDelivery"].append(dict(ID=999, ExternalCode="ORIGINAL"))
        self.store["SA_SaleDelivery_b"].append(dict(ID=9990, idSaleDeliveryDTO=999))
        self.store["ARAP_Detail"].append(dict(ID=99900, voucherID=999))
        owner = self

        class Connection:
            commits, rollbacks = 0, 0
            _autocommit = True

            @property
            def autocommit(self):
                return self._autocommit

            @autocommit.setter
            def autocommit(self, value):
                if not value:
                    self.before = deepcopy(owner.store)
                self._autocommit = value

            def rollback(self):
                if owner.failure == "rollback":
                    raise OSError("lost rollback")
                self.rollbacks += 1
                owner.store = deepcopy(self.before)

            def commit(self):
                if owner.failure == "commit":
                    raise OSError("lost commit reply")
                self.commits += 1

        self.connection = Connection()

    def query(self, sql, *params):
        self.commands.append((sql, params))
        if "sys.triggers" in sql:
            return [dict(name="trigger")] if self.triggers else []
        if "sys.foreign_keys" in sql:
            return [dict(name="cascade")] if self.cascades else []
        if "ARAP_Detail" in sql:
            table, column = "ARAP_Detail", "voucherID"
        elif "SA_SaleDelivery_b" in sql:
            table, column = "SA_SaleDelivery_b", "idSaleDeliveryDTO"
        else:
            table, column = "SA_SaleDelivery", "ID"
        selected = [row for row in self.store[table] if row[column] in params]
        if sql.startswith("DELETE"):
            if table == "SA_SaleDelivery" and self.failure in ("header", "rollback"):
                raise RuntimeError("header delete failed")
            self.store[table] = [row for row in self.store[table] if row[column] not in params]
            if self.failure == "count":
                return []
            return [dict(id=row["ID"]) for row in selected]
        if sql.startswith("SELECT *"):
            return deepcopy(selected)
        columns = [name.strip("[]") for name in sql.split(" FROM ")[0][len("SELECT "):].split(",")]
        return [{name: bind_value(row[name]) for name in columns} for row in selected]


def test_receipt_only_includes_current_successes_and_is_frozen():
    result = imported_result()
    receipt = UndoSession.from_result(config(), "source.xls", result)
    assert [doc.source for doc in receipt.documents] == ["NEW-A", "NEW-B"]
    result["rows"][0].parsed["quantity"] = 999
    assert receipt.documents[0].rows[0].parsed["quantity"] != 999
    result["rows"][3].status = "待确认"
    assert UndoSession.from_result(config(), "source.xls", result) is None
    assert UndoSession.from_result(config(), "source.xls", dict(task_id="empty", rows=[])) is None


def test_prepare_never_deletes_and_confirmed_undo_preserves_historical_rows():
    receipt = session()
    repo = UndoRepository(receipt)
    before = deepcopy(repo.store)
    receipt.prepare(repo)
    assert repo.store == before and repo.connection.commits == 0
    assert not any(sql.startswith("DELETE") for sql, _ in repo.commands)
    counts = receipt.execute(repo)
    assert counts == {"SA_SaleDelivery": 2, "SA_SaleDelivery_b": 2, "ARAP_Detail": 2}
    assert repo.store == {"SA_SaleDelivery": [dict(ID=999, ExternalCode="ORIGINAL")],
                          "SA_SaleDelivery_b": [dict(ID=9990, idSaleDeliveryDTO=999)],
                          "ARAP_Detail": [dict(ID=99900, voucherID=999)]}
    deletes = [sql for sql, _ in repo.commands if sql.startswith("DELETE")]
    assert "[ARAP_Detail]" in deletes[0] and "[SA_SaleDelivery_b]" in deletes[1] and "[SA_SaleDelivery]" in deletes[2]
    assert receipt.state == "done" and repo.connection.commits == 1
    with pytest.raises(PreflightError):
        receipt.execute(repo)


@pytest.mark.parametrize("mutation", ["content", "version", "extra_detail", "missing_header"])
def test_undo_refuses_changed_data_without_deleting_anything(mutation):
    receipt = session()
    repo = UndoRepository(receipt)
    receipt.prepare(repo)
    if mutation == "content":
        repo.store["SA_SaleDelivery"][0]["ExternalCode"] = "SOMEONE-ELSE"
    elif mutation == "version":
        repo.store["SA_SaleDelivery"][0]["ts"] = b"version2"
    elif mutation == "extra_detail":
        repo.store["SA_SaleDelivery_b"].append(dict(repo.store["SA_SaleDelivery_b"][0], ID=888))
    else:
        repo.store["SA_SaleDelivery"].pop(0)
    before = deepcopy(repo.store)
    with pytest.raises(PreflightError):
        receipt.execute(repo)
    assert repo.store == before and repo.connection.commits == 0
    assert not any(sql.startswith("DELETE") for sql, _ in repo.commands)


@pytest.mark.parametrize("failure", ["header", "count", "commit", "rollback"])
def test_failed_undo_rolls_back_both_tables_and_uncertain_results_disable_retry(failure):
    receipt = session()
    repo = UndoRepository(receipt)
    receipt.prepare(repo)
    before = deepcopy(repo.store)
    repo.failure = failure
    expected = CommitUnknown if failure in ("commit", "rollback") else (RuntimeError, SystemFailure)
    with pytest.raises(expected):
        receipt.execute(repo)
    if failure != "rollback":
        assert repo.store == before
    assert repo.connection.commits == 0
    assert receipt.state == ("unknown" if failure in ("commit", "rollback") else "ready")
    if failure == "rollback":
        assert repo.connection.autocommit is False


@pytest.mark.parametrize("guard", ["triggers", "cascades"])
def test_undo_blocks_unverified_database_side_effects(guard):
    receipt = session()
    repo = UndoRepository(receipt)
    setattr(repo, guard, True)
    with pytest.raises(PreflightError):
        receipt.prepare(repo)
    assert not any(sql.startswith("DELETE") for sql, _ in repo.commands)


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def window_with_receipt(tmp_path):
    path = tmp_path / "config.ini"
    path.write_text("[sqlserver]\nip=localhost\nport=1433\ndatabase=test_db\nuser=test\npassword=test\n", encoding="utf-8")
    window = ImportWindow(path)
    window.source = "source.xls"
    window.result = imported_result()
    window.model.set_rows(window.result["rows"], list(window.result["rows"][0].values))
    window.undo_session = session()
    window.update_buttons()
    return window


def test_undo_button_is_session_only_and_disabled_while_busy_or_after_close(qapp, tmp_path):
    window = window_with_receipt(tmp_path)
    assert window.undo_button.isEnabled()
    class Worker:
        action = "undo_prepare"
    window.worker = Worker()
    window.update_buttons()
    assert not window.undo_button.isEnabled()
    window.worker = None
    window.close()
    assert window.undo_session is None and not window.undo_button.isEnabled()
    fresh = ImportWindow(window.config_path)
    assert not fresh.undo_button.isEnabled()
    fresh.close()


def test_selecting_new_file_invalidates_receipt_even_if_loading_fails(qapp, tmp_path, monkeypatch):
    import app.gui as gui
    window = window_with_receipt(tmp_path)
    monkeypatch.setattr(gui.QFileDialog, "getOpenFileName", lambda *args: ("new.xls", ""))
    tasks = []
    monkeypatch.setattr(window, "start_worker", lambda worker, callback: tasks.append(worker))
    window.choose_file()
    assert window.undo_session is None and not window.undo_button.isEnabled()
    assert tasks[0].action == "load"
    window.close()


def test_cancelled_confirmation_keeps_data_and_acceptance_starts_delete(qapp, tmp_path, monkeypatch):
    window = window_with_receipt(tmp_path)
    tasks = []
    monkeypatch.setattr(window, "start_worker", lambda worker, callback: tasks.append(worker))
    monkeypatch.setattr(UndoConfirmDialog, "exec_", lambda self: QDialog.Rejected)
    window.pending_undo = window.undo_session
    window.confirm_undo()
    assert tasks == [] and window.undo_button.isEnabled()
    monkeypatch.setattr(UndoConfirmDialog, "exec_", lambda self: QDialog.Accepted)
    window.pending_undo = window.undo_session
    window.confirm_undo()
    assert tasks[0].action == "undo_delete"
    assert tasks[0].config == window.undo_session.config
    window.close()


@pytest.mark.parametrize("mode", ["success", "report_failure", "unknown"])
def test_undo_worker_preserves_committed_result_when_reporting_fails(qapp, tmp_path, monkeypatch, mode):
    import app.gui as gui
    from app.files import TaskJournal
    result = imported_result()
    receipt = UndoSession.from_result(config(), "source.xls", result)
    repo = UndoRepository(receipt)
    receipt.prepare(repo)
    repo.open = lambda: config().database
    repo.close = lambda: None
    if mode == "unknown":
        repo.failure = "commit"
    monkeypatch.setattr(gui, "SqlRepository", lambda config: repo)
    def export(**kwargs):
        raise OSError("output blocked")
    if mode == "report_failure":
        monkeypatch.setattr(gui, "export_report", lambda *args, **kwargs: export())
    else:
        monkeypatch.setattr(gui, "export_report", lambda *args, **kwargs: "undo-result.xlsx")
    worker = gui.TaskWorker("undo_delete", config=receipt.config, undo_session=receipt,
                            rows=result["rows"], columns=[], runtime=tmp_path)
    completed, failed = [], []
    worker.completed.connect(completed.append)
    worker.failed.connect(failed.append)
    worker.run()
    payload, saved = TaskJournal.load(tmp_path / "undo-test.json")
    assert [row.status for row in saved[2:]] == ["重复跳过", "校验失败"]
    if mode == "unknown":
        assert completed == [] and "待确认" in failed[0]
        assert receipt.state == "unknown" and saved[0].status == "撤销待确认"
    else:
        assert not failed and receipt.state == "done"
        assert saved[0].status == "已撤销"
        assert "已撤销" in completed[0]["message"]
        if mode == "report_failure":
            assert "数据库删除已完成" in completed[0]["message"]


def test_restoring_results_does_not_restore_delete_permission(qapp, tmp_path, monkeypatch):
    import app.gui as gui
    from app.files import TaskJournal
    window = window_with_receipt(tmp_path)
    journal = TaskJournal(tmp_path, "restored", "other.xls", config().database)
    journal.save(imported_result()["rows"], "完成")
    monkeypatch.setattr(gui.QFileDialog, "getOpenFileName", lambda *args: (str(journal.path), ""))
    window.restore_result()
    assert window.undo_session is None and not window.undo_button.isEnabled()
    window.close()
