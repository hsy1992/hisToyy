"""Populate the explicitly approved local performance fixture; never imports XLS."""
import argparse
import gzip
import hashlib
import json
import shutil
import sys
import threading
import time
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pyodbc
from app.configuration import DatabaseConfig
from app.database import SqlRepository, bind_value, quote
from app.domain import build_payload, validate_rows
from app.engine import account_lock
from app.files import atomic_json, read_xls
from log_util import logger

PREFIX = "PERF20261018H"
CODE_PREFIX = "LT20261018H"
HEADERS = 1_000_000
DETAILS = 5_000_000
BATCH = 5_000
STATE = ROOT / ".validation/performance_dataset_progress.json"


def query(conn, sql, *params):
    cursor = conn.cursor()
    try:
        cursor.execute(sql, *params)
        names = [c[0] for c in cursor.description]
        return [dict(zip(names, row)) for row in cursor.fetchall()]
    finally:
        cursor.close()


def value(row, name):
    return next(v for k, v in row.items() if k.casefold() == name.casefold())


def serialize(v):
    if isinstance(v, bytes):
        return {"type": "bytes", "hex": v.hex()}
    if isinstance(v, Decimal):
        return {"type": "decimal", "value": str(v)}
    if isinstance(v, (date, datetime)):
        return {"type": "datetime", "value": v.isoformat()}
    raise TypeError(type(v).__name__)


def digest(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True, ensure_ascii=False, default=serialize).encode("utf-8")).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true", help="Execute the approved local fixture creation")
    args = parser.parse_args()
    if not args.run:
        print("Use --run only for the approved local test account; target 1,000,000 headers / 5,000,000 details.")
        return
    cfg = DatabaseConfig.load(ROOT / "config.ini")
    if cfg.host != "127.0.0.1" or cfg.database != "UFDATA_999_1015":
        raise RuntimeError("This maintenance fixture is restricted to the approved local test account")
    pointer = json.loads((ROOT / ".validation/reimport_backup_pointer.json").read_text(encoding="utf-8"))
    with gzip.open(pointer["backup"], "rt", encoding="utf-8") as f:
        original = json.load(f)
    old_ids = set(original["preserve_ids"])
    assert len(old_ids) == 77
    original_task = json.loads((ROOT / "runtime/20261018_122910_2020f552.json").read_text(encoding="utf-8"))
    rows, _ = read_xls(original_task["source"], threading.Event(), lambda *a: None)
    repo = SqlRepository(cfg)
    repo.open()
    growth_settings = []
    status = {"prefix": PREFIX, "code_prefix": CODE_PREFIX, "database": cfg.database,
              "target_headers": HEADERS, "target_details": DETAILS, "phase": "preflight",
              "started": datetime.now().isoformat(), "indexes_changed": False,
              "source_cleanup": str(ROOT / ".validation/scale_seed_cleanup_result.json")}
    started = time.perf_counter()
    try:
        conn = repo.connection
        if query(conn, "SELECT DB_NAME() AS account")[0]["account"] != cfg.database:
            raise RuntimeError("Account mismatch")
        assert not query(conn, "SELECT name FROM sys.triggers WHERE parent_id IN (OBJECT_ID('dbo.SA_SaleDelivery'),OBJECT_ID('dbo.SA_SaleDelivery_b')) AND is_disabled=0")
        current_h = query(conn, "SELECT * FROM dbo.SA_SaleDelivery WHERE ExternalCode NOT LIKE ? OR ExternalCode IS NULL ORDER BY id", PREFIX + "%")
        current_d = query(conn, "SELECT d.* FROM dbo.SA_SaleDelivery_b d JOIN dbo.SA_SaleDelivery h ON h.id=d.idSaleDeliveryDTO WHERE h.ExternalCode NOT LIKE ? OR h.ExternalCode IS NULL ORDER BY d.id", PREFIX + "%")
        assert {int(value(h, "id")) for h in current_h} == old_ids
        assert len(current_d) == 373
        assert digest(current_h) == original["preserve_header_hash"]
        assert digest(current_d) == original["preserve_detail_hash"]
        synthetic_headers = HEADERS - len(current_h)
        synthetic_details = DETAILS - len(current_d)
        extra = synthetic_details - synthetic_headers * 5
        assert synthetic_headers == 999923 and synthetic_details == 4999627 and extra == 12
        cache = repo.load_cache(threading.Event(), lambda *a: None)
        docs = validate_rows(rows, cache, threading.Event(), lambda *a: None)
        doc = next(d for d in docs if d.ready and d.rows[0].parsed["business"]["id"] == 65 and d.rows[0].parsed["rate"] == Decimal("0.13"))
        doc.code = CODE_PREFIX + "0000000001"
        template_h, template_ds = build_payload(doc)
        h = dict(template_h)
        d = dict(template_ds[0], idSaleDeliveryDTO=1)
        h.update(ExternalCode=PREFIX + "0000000001", ExternalVoucherCode=PREFIX + "0000000001", origAmount=Decimal("53.10"), amount=Decimal("53.10"), origTaxAmount=Decimal(60), taxAmount=Decimal(60))
        unit = doc.rows[0].parsed["unit"]["name"]
        d.update(quantity=Decimal(1), baseQuantity=Decimal(1), compositionQuantity="1" + str(unit),
                 origTaxPrice=Decimal(10), taxPrice=Decimal(10), origDiscountPrice=Decimal("8.84955752"), discountPrice=Decimal("8.84955752"),
                 origDiscountAmount=Decimal("8.85"), discountAmount=Decimal("8.85"), origTax=Decimal("1.15"), tax=Decimal("1.15"),
                 origTaxAmount=Decimal(10), taxAmount=Decimal(10), priuserdefnvc2=h["ExternalCode"], priuserdefnvc3=h["ExternalCode"] + "-L0000")
        repo.preflight(h, d)
        repo.validate_payload("SA_SaleDelivery", h)
        repo.validate_payload("SA_SaleDelivery_b", d)
        files = query(conn, "SELECT name,physical_name,growth,is_percent_growth FROM sys.database_files")
        for file in files:
            if shutil.disk_usage(Path(file["physical_name"]).anchor).free < 15 * 1024**3:
                raise RuntimeError("Insufficient free space for the approved dataset")
        existing = query(conn, "SELECT COUNT_BIG(*) AS records,MAX(CONVERT(int,RIGHT(ExternalCode,10))) AS last_n FROM dbo.SA_SaleDelivery WHERE ExternalCode LIKE ?", PREFIX + "%")[0]
        start_n = int(existing["last_n"] or 0)
        assert int(existing["records"]) == start_n and 0 <= start_n <= synthetic_headers
        present_d = query(conn, "SELECT COUNT_BIG(*) AS records FROM dbo.SA_SaleDelivery_b WHERE priuserdefnvc2 LIKE ?", PREFIX + "%")[0]["records"]
        assert present_d == start_n * 5 + min(start_n, extra)
        status.update(simulated_headers=synthetic_headers, simulated_details=synthetic_details,
                      template_customer=h["idcustomer"], template_inventory=d["idinventory"],
                      committed_headers=start_n, committed_details=present_d,
                      original_file_growth=files)
        atomic_json(STATE, status)
        # Existing indexes and FULL recovery remain unchanged. Temporarily use
        # larger growth increments for fixture creation, restoring exact settings.
        for file in files:
            name = file["name"].replace("'", "''")
            conn.execute("ALTER DATABASE " + quote(cfg.database) + " MODIFY FILE (NAME=N'" + name + "', FILEGROWTH=128MB)")
            growth_settings.append(file)
        conn.execute("SET NOCOUNT ON; SET XACT_ABORT ON; SET LOCK_TIMEOUT 5000")
        conn.execute("CREATE TABLE #PerfSeed(n int NOT NULL PRIMARY KEY)")
        conn.execute(";WITH D(n) AS (SELECT n FROM (VALUES(0),(1),(2),(3),(4),(5),(6),(7),(8),(9)) x(n)) INSERT #PerfSeed(n) SELECT TOP (5000) CONVERT(int,ROW_NUMBER() OVER(ORDER BY a.n,b.n,c.n,d.n)) FROM D a CROSS JOIN D b CROSS JOIN D c CROSS JOIN D d")
        conn.execute("CREATE TABLE #PerfMap(id int NOT NULL PRIMARY KEY,n int NOT NULL)")
        pad = "RIGHT('0000000000'+CONVERT(varchar(10),g.n),10)"
        header_expr = []
        header_params = []
        for name, v in h.items():
            if name == "code":
                header_expr.append("?+" + pad); header_params.append(CODE_PREFIX)
            elif name in ("ExternalCode", "ExternalVoucherCode"):
                header_expr.append("?+" + pad); header_params.append(PREFIX)
            elif name in ("voucherdate", "madedate", "auditeddate"):
                header_expr.append("DATEADD(day,-((g.n-1)%365),CAST(? AS datetime))"); header_params.append(datetime(2026, 10, 11))
            elif name in ("origAmount", "amount"):
                header_expr.append("CASE WHEN g.n<=12 THEN 53.10 ELSE 44.25 END")
            elif name in ("origTaxAmount", "taxAmount"):
                header_expr.append("CASE WHEN g.n<=12 THEN 60.00 ELSE 50.00 END")
            else:
                header_expr.append("?"); header_params.append(bind_value(v))
        header_sql = ("INSERT dbo.SA_SaleDelivery (" + ",".join(quote(x) for x in h) + ") OUTPUT INSERTED.ID,CONVERT(int,RIGHT(INSERTED.ExternalCode,10)) INTO #PerfMap(id,n) SELECT " + ",".join(header_expr) + " FROM (SELECT n+? AS n FROM #PerfSeed WHERE n<=?) g")
        detail_expr = []
        detail_params = []
        for name, v in d.items():
            if name == "code":
                detail_expr.append("RIGHT('0000'+CONVERT(varchar(4),lines.line),4)")
            elif name == "idSaleDeliveryDTO":
                detail_expr.append("m.id")
            elif name in ("priuserdefnvc2", "priuserdefnvc3"):
                expr = "?+RIGHT('0000000000'+CONVERT(varchar(10),m.n),10)"
                if name == "priuserdefnvc3":
                    expr += "+'-L'+RIGHT('0000'+CONVERT(varchar(4),lines.line),4)"
                detail_expr.append(expr); detail_params.append(PREFIX)
            else:
                detail_expr.append("?"); detail_params.append(bind_value(v))
        detail_sql = ("INSERT dbo.SA_SaleDelivery_b (" + ",".join(quote(x) for x in d) + ") SELECT " + ",".join(detail_expr) + " FROM #PerfMap m CROSS JOIN (VALUES(0),(1),(2),(3),(4),(5)) lines(line) WHERE lines.line<5 OR m.n<=12")
        conn.autocommit = False
        status["phase"] = "generating"
        for offset in range(start_n, synthetic_headers, BATCH):
            count = min(BATCH, synthetic_headers-offset)
            detail_count = count*5 + max(0, min(extra, offset+count)-min(extra, offset))
            tick = time.perf_counter()
            cursor = conn.cursor()
            try:
                cursor.execute("DELETE FROM #PerfMap")
                cursor.execute(header_sql, *(header_params + [offset, count]))
                cursor.execute("SELECT COUNT_BIG(*) FROM #PerfMap")
                assert cursor.fetchone()[0] == count
                cursor.execute(detail_sql, *detail_params)
                cursor.execute("SELECT @@ROWCOUNT")
                assert cursor.fetchone()[0] == detail_count
                conn.commit()
            except BaseException:
                conn.rollback()
                raise
            finally:
                cursor.close()
            status.update(committed_headers=offset+count, committed_details=(offset+count)*5+min(offset+count,extra),
                          elapsed_seconds=round(time.perf_counter()-started,3), updated=datetime.now().isoformat())
            atomic_json(STATE,status)
            logger.info("模拟数据批次完成 headers=%d/%d details=%d/%d batch_seconds=%.3f",offset+count,synthetic_headers,status["committed_details"],synthetic_details,time.perf_counter()-tick)
            print(json.dumps({"headers":offset+count,"details":status["committed_details"],"elapsed_seconds":status["elapsed_seconds"]}),flush=True)
        conn.autocommit = True
        status["phase"] = "verifying"
        atomic_json(STATE,status)
        final_h=query(conn,"SELECT COUNT_BIG(*) AS records,SUM(origAmount) AS net,SUM(origTaxAmount) AS gross FROM dbo.SA_SaleDelivery WHERE ExternalCode LIKE ?",PREFIX+"%")[0]
        final_d=query(conn,"SELECT COUNT_BIG(*) AS records,SUM(origDiscountAmount) AS net,SUM(origTaxAmount) AS gross,SUM(origTax) AS tax FROM dbo.SA_SaleDelivery_b WHERE priuserdefnvc2 LIKE ?",PREFIX+"%")[0]
        assert final_h["records"] == synthetic_headers and final_d["records"] == synthetic_details
        assert final_h["gross"] == final_d["gross"] == Decimal(10)*synthetic_details
        assert final_h["net"] == final_d["net"] == Decimal("8.85")*synthetic_details
        assert final_d["gross"] == final_d["net"]+final_d["tax"]
        assert not query(conn,"SELECT TOP (1) d.ID FROM dbo.SA_SaleDelivery_b d LEFT JOIN dbo.SA_SaleDelivery h ON h.ID=d.idSaleDeliveryDTO WHERE h.ID IS NULL")
        marks=",".join("?" for _ in old_ids)
        preserved_h=query(conn,"SELECT * FROM dbo.SA_SaleDelivery WHERE id IN ("+marks+") ORDER BY id",*sorted(old_ids))
        preserved_d=query(conn,"SELECT * FROM dbo.SA_SaleDelivery_b WHERE idSaleDeliveryDTO IN ("+marks+") ORDER BY id",*sorted(old_ids))
        assert digest(preserved_h)==original["preserve_header_hash"] and digest(preserved_d)==original["preserve_detail_hash"]
        all_counts=query(conn,"SELECT (SELECT COUNT_BIG(*) FROM dbo.SA_SaleDelivery) AS headers,(SELECT COUNT_BIG(*) FROM dbo.SA_SaleDelivery_b) AS details")[0]
        assert all_counts=={"headers":HEADERS,"details":DETAILS}
        status.update(phase="complete",final_counts=all_counts,original_headers_preserved=77,original_details_preserved=373,
                      preserved_unchanged=True,orphan_details=0,header_gross=str(final_h["gross"]),detail_gross=str(final_d["gross"]),
                      elapsed_seconds=round(time.perf_counter()-started,3),completed=datetime.now().isoformat())
    except BaseException as exc:
        status.update(phase="failed",error_type=type(exc).__name__)
        raise
    finally:
        conn=repo.connection
        if conn is not None:
            try:
                conn.rollback()
                conn.autocommit=True
                for file in growth_settings:
                    growth=str(file["growth"])+"%" if file["is_percent_growth"] else str(file["growth"]*8)+"KB"
                    name=file["name"].replace("'","''")
                    conn.execute("ALTER DATABASE "+quote(cfg.database)+" MODIFY FILE (NAME=N'"+name+"', FILEGROWTH="+growth+")")
                status["file_growth_restored"]=True
            finally:
                repo.close()
        atomic_json(STATE,status)
    print(json.dumps(status,ensure_ascii=True,default=str,indent=2),flush=True)


if __name__ == "__main__":
    cfg=DatabaseConfig.load(ROOT/"config.ini")
    with account_lock(cfg):
        main()
