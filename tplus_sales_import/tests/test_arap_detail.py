from decimal import Decimal
from datetime import date
import threading
import pytest

from app.configuration import DatabaseConfig
from app.database import DocumentError, SqlRepository
from app.domain import build_payload, build_arap_payloads, key, validate_rows
from app.undo import UndoSession
from test_import import cache, config, source_row
from test_database_and_gui import TransactionRepository, documents
from test_undo import UndoRepository, session


def test_build_arap_payloads_keeps_links_and_uses_unaudited_flags():
    doc = documents()[0]
    header, details = build_payload(doc)
    header_id = 1581123
    detail_mapping = {(header_id, "0000"): 5561934}
    
    arap_records = build_arap_payloads(doc, header_id, detail_mapping)
    assert len(arap_records) == 1
    rec = arap_records[0]
    
    # 单据级关联
    assert rec["voucherCode"] == doc.code
    assert rec["businessCode"] == doc.code
    assert rec["voucherID"] == header_id
    assert rec["businessID"] == header_id
    
    # 明细级关联与存货信息
    assert rec["voucherDetailID"] == 5561934
    assert rec["detailtype"] == "inventory"
    assert rec["detailID"] == 30
    assert rec["detailCode"] == "0099"
    assert rec["detailName"] == "商品"
    
    # 核心标志与法定枚举
    assert rec["flag"] == -1
    assert rec["isArFlag"] == 1
    assert rec["auditFlag"] == 0
    assert rec["auditBussinessFlag"] == 0
    assert rec["BookFlag"] == 2212
    assert rec["bussinessFlag"] == "0"
    assert rec["idarapvouchertype"] == 104
    assert rec["idvouchertype"] == 104
    assert rec["DataSource"] == 2497
    assert rec["RefundDifferenceFlag"] == 51185
    assert rec["idcurrency"] == 4
    assert rec["IdMarketingOrgan"] == 1
    assert rec["idbusitype"] == 65
    
    # 源单号追溯
    assert rec["ExternalVoucherCode"] == doc.source
    assert rec["detailPriuserdefnvc2"] == doc.source


def test_write_batch_inserts_arap_detail():
    repo = TransactionRepository()
    mapping = repo.write_batch(documents())
    assert mapping == {"b": 101, "a": 100}
    
    # 验证 repo.received 中依次包含了 SA_SaleDelivery、SA_SaleDelivery_b、ARAP_Detail
    tables = [item[0] for item in repo.received]
    assert tables == ["SA_SaleDelivery", "SA_SaleDelivery_b", "ARAP_Detail"]
    
    arap_records = repo.received[2][1]
    assert len(arap_records) == 2
    assert {r["voucherID"] for r in arap_records} == {100, 101}
    assert {r["voucherDetailID"] for r in arap_records} == {200, 201}
    assert all(r["auditFlag"] == r["auditBussinessFlag"] == 0 for r in arap_records)
    assert all(h["voucherState"] == 181 for h in repo.received[0][1])
    assert repo.connection.commits == 1 and repo.connection.rollbacks == 0
    assert {r["detailtype"] for r in arap_records} == {"inventory"}
    assert {r["flag"] for r in arap_records} == {-1}
    assert {r["idarapvouchertype"] for r in arap_records} == {104}


def test_arap_insert_failure_rolls_back_entire_batch():
    class FailingRepository(TransactionRepository):
        def bulk_insert(self, cursor, table, records, output=False, output_cols=None):
            if table == "ARAP_Detail":
                raise DocumentError("ARAP insert failed")
            return super().bulk_insert(cursor, table, records, output, output_cols)

    repo = FailingRepository()
    with pytest.raises(DocumentError, match="ARAP insert failed"):
        repo.write_batch(documents())
    assert repo.connection.commits == 0
    assert repo.connection.rollbacks == 1
    assert repo.connection.autocommit is True


def test_undo_deletes_arap_detail_in_transaction():
    receipt = session()
    repo = UndoRepository(receipt)
    receipt.prepare(repo)
    counts = receipt.execute(repo)
    
    assert counts["ARAP_Detail"] == 2
    assert counts["SA_SaleDelivery_b"] == 2
    assert counts["SA_SaleDelivery"] == 2
    
    # 验证删除顺序严格遵循依赖关系：先删往来明细，再删存货明细，最后删表头
    deletes = [sql for sql, _ in repo.commands if sql.startswith("DELETE")]
    assert len(deletes) == 3
    assert "[ARAP_Detail]" in deletes[0]
    assert "[SA_SaleDelivery_b]" in deletes[1]
    assert "[SA_SaleDelivery]" in deletes[2]
