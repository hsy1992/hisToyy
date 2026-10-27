import threading
from pathlib import Path
import pytest
from unittest.mock import Mock

from app.configuration import DatabaseConfig, TPlusApiConfig
from app.domain import SourceRow, validate_rows
from app.engine import ImportEngine
from app.tplus_api import TPlusApiClient
from test_import import cache, config, source_row


class MockRepository:
    def __init__(self, cfg):
        self.config = cfg
        self.deleted_ids = []
        self.inserted = []

    def open(self):
        pass

    def close(self):
        pass

    def load_cache(self, stop, progress):
        return cache()

    def preflight(self, *args):
        pass

    def find_existing(self, sources):
        return {}

    def max_sequence(self, day):
        return 0

    def validate_payload(self, table, payload):
        pass

    def write_batch(self, batch):
        mapping = {}
        for index, doc in enumerate(batch):
            header_id = index + 100
            mapping[doc.source.lower()] = header_id
            self.inserted.append((header_id, doc.code))
        return mapping

    def delete_failed_vouchers(self, ids):
        self.deleted_ids.extend(ids)

    def classify(self, exc):
        return "data"


def test_engine_inserts_without_token_authentication(tmp_path):
    rows = [source_row("DOC-001"), source_row("DOC-002")]
    api_cfg = TPlusApiConfig(password="", enabled=True)  # 空密码会导致 get_token 失败
    cfg = DatabaseConfig("localhost", 1433, "testdb", "sa", "123", api=api_cfg)

    client = TPlusApiClient(api_cfg)
    client.get_token = Mock(side_effect=AssertionError("Token API must not be called"))
    client.audit_voucher = Mock(side_effect=AssertionError("Approval API must not be called"))
    mock_repo = MockRepository(cfg)

    engine = ImportEngine(
        cfg,
        tmp_path / "source.xls",
        rows,
        list(rows[0].values),
        tmp_path,
        threading.Event(),
        lambda *args: None,
        repository_factory=lambda _: mock_repo,
        api_client=client,
    )

    result = engine.run()
    assert len(mock_repo.inserted) == 2
    assert all(r.status == "导入成功" for r in rows)
    assert mock_repo.deleted_ids == []
    client.get_token.assert_not_called()
    client.audit_voucher.assert_not_called()
    assert Path(result["report"]).exists()


def test_engine_keeps_inserted_documents_without_approval_or_cleanup(tmp_path):
    rows = [source_row("DOC-OK1"), source_row("DOC-FAIL"), source_row("DOC-OK2")]
    api_cfg = TPlusApiConfig(password="pass123", enabled=True)
    cfg = DatabaseConfig("localhost", 1433, "testdb", "sa", "123", api=api_cfg)

    mock_repo = MockRepository(cfg)

    class MockApiClient:
        def __init__(self):
            self.audited = []

        def get_token(self):
            return True, "valid-token"

        def audit_voucher(self, sa_code, voucher_id):
            self.audited.append((sa_code, voucher_id))
            if sa_code == "SA2026101200002":  # 第二张单据模拟失败（如现存量不足）
                return False, "存货现存量不足"
            return True, "审核成功"

    api_client = MockApiClient()

    engine = ImportEngine(
        cfg,
        tmp_path / "source.xls",
        rows,
        list(rows[0].values),
        tmp_path,
        threading.Event(),
        lambda *args: None,
        repository_factory=lambda _: mock_repo,
        api_client=api_client,
    )

    result = engine.run()

    assert api_client.audited == []
    assert len(mock_repo.inserted) == 3
    assert mock_repo.deleted_ids == []
    assert all(r.status == "导入成功" for r in rows)
    assert Path(result["report"]).exists()
