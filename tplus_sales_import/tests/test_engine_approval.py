import threading
from pathlib import Path
import pytest

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


def test_engine_breaks_before_db_insert_when_token_fails(tmp_path):
    rows = [source_row("DOC-001"), source_row("DOC-002")]
    api_cfg = TPlusApiConfig(password="", enabled=True)  # 空密码会导致 get_token 失败
    cfg = DatabaseConfig("localhost", 1433, "testdb", "sa", "123", api=api_cfg)

    client = TPlusApiClient(api_cfg)
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
    # 验证强熔断：没有往数据库写入任何单据！
    assert len(mock_repo.inserted) == 0
    assert "T+ API认证失败，未写入数据库" in engine.message
    assert all(r.status == "未处理" for r in rows)
    assert any("登录密码未配置" in "".join(r.reasons) for r in rows)


def test_engine_approval_concurrency_and_cleanup(tmp_path):
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

    # 1. 验证 3 笔单据均通过并发审批发起过审核
    assert len(api_client.audited) == 3

    # 2. 验证审批失败的那张单据（ID=101）被从数据库批量删除
    assert mock_repo.deleted_ids == [101]

    # 3. 验证成功的单据状态为导入成功
    ok_rows = [r for r in rows if r.voucher in ("DOC-OK1", "DOC-OK2")]
    assert all(r.status == "导入成功" for r in ok_rows)

    # 4. 验证失败的单据保持现有失败导出逻辑：标记为审批失败，且记录具体原因
    fail_rows = [r for r in rows if r.voucher == "DOC-FAIL"]
    assert len(fail_rows) == 1
    assert fail_rows[0].status == "审批失败"
    assert "T+ API审批失败：存货现存量不足" in fail_rows[0].reasons[0]

    # 5. 验证生成了结果报表，且导出路径有效
    assert Path(result["report"]).exists()
