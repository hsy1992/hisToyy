"""Explicit T+ schema, parameterized bulk SQL and complete-document transactions."""
from collections import defaultdict
from decimal import Decimal
from datetime import date, datetime, time as datetime_time
import re
import time
import sys
from log_util import logger, diagnostics

from .domain import MasterCache, build_payload, key, valid_source_code


class PreflightError(Exception):
    pass


class DocumentError(Exception):
    pass


class CommitUnknown(Exception):
    pass


class SystemFailure(Exception):
    pass


def chunks(values, size):
    for start in range(0, len(values), size):
        yield values[start:start + size]


def quote(name):
    return "[" + str(name).replace("]", "]]") + "]"


def bind_value(value):
    # The legacy SQL Server ODBC driver rejects SQL_TYPE_DATE (HYC00).
    # Bind business dates as midnight timestamps without changing domain data.
    if isinstance(value, date) and not isinstance(value, datetime):
        return datetime.combine(value, datetime_time.min)
    return value


class SqlRepository:
    def __init__(self, config, connector=None):
        self.config = config
        if connector is None:
            import pyodbc
            connector = pyodbc.connect
        self.connector = connector
        self.connection = None
        self.schema = {}
        self.log = logger

    def open(self):
        started = time.perf_counter()
        try:
            import pyodbc
            drivers = pyodbc.drivers()
            self.log.info("ODBC驱动列表 process_bits=%d count=%d drivers=%s",
                          64 if sys.maxsize > 2**32 else 32, len(drivers), drivers)
            if self.config.driver.casefold() not in {name.casefold() for name in drivers}:
                self.log.warning("配置的ODBC驱动未安装或当前程序不可见 driver=%s，请核对驱动名称与程序位数", self.config.driver)
        except Exception as exc:
            self.log.warning("读取ODBC驱动列表失败，继续尝试连接 %s", diagnostics(exc))
        self.log.info("连接SQL Server server=%s port=%s database=%s driver=%s", self.config.host, self.config.port, self.config.database, self.config.driver)
        try:
            self.connection = self.connector(self.config.connection_string(), autocommit=True, timeout=6)
            self.connection.timeout = 30
            self.connection.execute("SET LOCK_TIMEOUT 5000; SET XACT_ABORT ON;")
            actual = self.connection.execute("SELECT DB_NAME()").fetchone()[0]
            if key(actual) != key(self.config.database):
                self.close()
                raise PreflightError("实际连接账套与配置不一致")
            self.log.info("连接成功 actual_database=%s elapsed_seconds=%.3f", actual, time.perf_counter() - started)
            return actual
        except Exception as exc:
            self.log.error("连接SQL Server失败 elapsed_seconds=%.3f %s", time.perf_counter() - started, diagnostics(exc))
            raise

    def close(self):
        if self.connection is not None:
            try:
                self.connection.close()
            finally:
                self.connection = None

    def query(self, sql, *params):
        cursor = self.connection.cursor()
        try:
            cursor.execute(sql, *params)
            names = [item[0] for item in cursor.description]
            return [dict(zip(names, row)) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def load_cache(self, stop, progress):
        tables = {}
        queries = {
            "customers": "SELECT id,code,name,disabled,taxRate FROM dbo.AA_PartnerEntity",
            "inventory": "SELECT id,code,name,disabled,idunit,isSingleUnit FROM dbo.AA_InventoryEntity",
            "warehouse": "SELECT id,code,name,disabled FROM dbo.AA_Warehouse",
            "unit": "SELECT id,code,name,disabled FROM dbo.AA_Unit",
            "business": "SELECT id,code,name,disabled FROM dbo.AA_BusiType",
            "project": "SELECT id,Code AS code,Name AS name,disabled FROM dbo.AA_Project",
            "tax": "SELECT DISTINCT e.ID AS id,e.Name AS name FROM dbo.eap_EnumItem e JOIN dbo.AA_PartnerEntity p ON p.taxRate=e.ID",
        }
        for number, (table, query) in enumerate(queries.items(), 1):
            if stop.is_set():
                return None
            started = time.perf_counter()
            tables[table] = self.query(query)
            self.log.info("档案缓存加载完成 table=%s records=%d elapsed_seconds=%.3f", table, len(tables[table]), time.perf_counter() - started)
            progress("缓存档案：" + table, number, len(queries))
        return MasterCache(tables)

    def preflight(self, header, detail):
        errors = []
        for table, payload in (("SA_SaleDelivery", header), ("SA_SaleDelivery_b", dict(detail, idSaleDeliveryDTO=0))):
            meta = self.query("""SELECT c.name,t.name AS type_name,c.max_length,c.precision,c.scale,
                       c.is_nullable,c.is_identity,c.is_computed,c.default_object_id
                       FROM sys.columns c JOIN sys.types t ON t.user_type_id=c.user_type_id
                       WHERE c.object_id=OBJECT_ID(?)""", "dbo." + table)
            columns = {key(c["name"]): c for c in meta}
            self.schema[table] = columns
            ident = columns.get("id", {})
            if not ident.get("is_identity"):
                errors.append(table + ".ID不是已确认的自增主键")
            for name in payload:
                col = columns.get(key(name))
                if not col:
                    errors.append(table + "缺少字段" + name)
                elif col["is_computed"] or col["is_identity"] or col["type_name"] in ("timestamp", "rowversion"):
                    errors.append(table + "." + name + "是系统生成字段")
            expected = {key(name) for name in payload}
            for col in meta:
                if (key(col["name"]) not in expected and not col["is_nullable"] and not col["is_identity"]
                        and not col["is_computed"] and col["type_name"] not in ("timestamp", "rowversion")
                        and not col["default_object_id"]):
                    errors.append(table + "." + col["name"] + "为未配置的必填列")
        for table, identifier in (("AA_Currency", 4), ("AA_MarketingOrgan", 1), ("AA_RDStyle", 24)):
            records = self.query(f"SELECT * FROM dbo.{table} WHERE id=?", identifier)
            if len(records) != 1:
                errors.append(f"固定配置档案缺失或不唯一：{table}.id={identifier}")
            else:
                record = {key(name): value for name, value in records[0].items()}
                for state in ("disabled", "isdisabled", "isstopped", "isstoped"):
                    if state in record and record[state] not in (0, False):
                        errors.append(f"固定配置已停用或状态未知：{table}.id={identifier}")
        triggers = self.query("SELECT name FROM sys.triggers WHERE parent_id IN (OBJECT_ID('dbo.SA_SaleDelivery'),OBJECT_ID('dbo.SA_SaleDelivery_b')) AND is_disabled=0")
        if triggers:
            errors.append("目标主明细表存在未经验证的触发器，暂不写入，以免生成额外业务单据")
        users = self.query("SELECT id,name,IsUsed,isStoped FROM dbo.EAP_User WHERE id=?", 51)
        if not users:
            errors.append("固定制单/审核人员档案缺失：EAP_User.id=51")
        elif users[0]["isStoped"] not in (0, False):
            errors.append("固定制单/审核人员已停用或状态未知")
        if errors:
            raise PreflightError("；".join(errors))

    def validate_payload(self, table, payload):
        for name, value in payload.items():
            col = self.schema[table][key(name)]
            if value is None:
                if not col["is_nullable"]:
                    raise DocumentError(table + "." + name + "不能为空")
                continue
            kind = col["type_name"]
            if kind in ("nvarchar", "nchar", "varchar", "char") and col["max_length"] != -1:
                size = len(str(value).encode("utf-16-le")) if kind.startswith("n") else len(str(value).encode("gbk", errors="strict"))
                if size > col["max_length"]:
                    raise DocumentError(table + "." + name + "超过字段长度")
            if kind in ("decimal", "numeric"):
                number = Decimal(value)
                with __import__("decimal").localcontext() as context:
                    context.prec = 60
                    scale = Decimal(1).scaleb(-int(col["scale"]))
                    if not number.is_finite() or abs(number) >= Decimal(10) ** (col["precision"] - col["scale"]):
                        raise DocumentError(table + "." + name + "数值溢出")
                    if number.quantize(scale) != number:
                        raise DocumentError(table + "." + name + "精度超出字段定义，未自动舍入")

    def find_existing(self, sources):
        unique = list(dict.fromkeys(source for source in sources if valid_source_code(source)))
        if not unique:
            return {}
        cursor = self.connection.cursor()
        try:
            cursor.execute("IF OBJECT_ID('tempdb..#TplusPending') IS NOT NULL DROP TABLE #TplusPending")
            # SELECT INTO preserves the target's type and collation, avoiding tempdb collation mismatch.
            cursor.execute("SELECT TOP (0) ExternalCode AS VoucherCode INTO #TplusPending FROM dbo.SA_SaleDelivery")
            for block in chunks(unique, 500):
                cursor.execute("INSERT INTO #TplusPending (VoucherCode) VALUES " + ",".join("(?)" for _ in block), *block)
            cursor.execute("""SELECT h.ID,h.code,h.ExternalCode FROM dbo.SA_SaleDelivery h
                            JOIN #TplusPending p ON p.VoucherCode=h.ExternalCode""")
            result = defaultdict(list)
            for identifier, code, source in cursor.fetchall():
                result[key(source)].append(dict(id=identifier, code=code))
            return result
        finally:
            original_error = sys.exc_info()[0] is not None
            try:
                cursor.execute("IF OBJECT_ID('tempdb..#TplusPending') IS NOT NULL DROP TABLE #TplusPending")
            except Exception as exc:
                self.log.warning("去重临时表清理失败 %s", diagnostics(exc))
                if not original_error:
                    raise
            finally:
                active_error = original_error or sys.exc_info()[0] is not None
                try:
                    cursor.close()
                except Exception as exc:
                    self.log.warning("去重游标关闭失败 %s", diagnostics(exc))
                    if not active_error:
                        raise

    def max_sequence(self, day):
        prefix = "SA" + day.strftime("%Y%m%d")
        rows = self.query("SELECT code FROM dbo.SA_SaleDelivery WHERE code LIKE ?", prefix + "%")
        maximum = 0
        for row in rows:
            code = str(row["code"])
            if not re.fullmatch(re.escape(prefix) + r"[0-9]{5}", code) or code.endswith("00000"):
                raise PreflightError("单据日期" + str(day) + "存在异常SA编号")
            maximum = max(maximum, int(code[-5:]))
        return maximum

    def bulk_insert(self, cursor, table, payloads, output=False):
        if not payloads:
            return []
        names = list(payloads[0])
        result = []
        for block in chunks(payloads, min(1000, 2000 // len(names))):
            values = []
            for item in block:
                self.validate_payload(table, item)
                values.extend(bind_value(item[name]) for name in names)
            sql = "INSERT INTO dbo." + quote(table) + " (" + ",".join(quote(name) for name in names) + ") "
            if output:
                sql += "OUTPUT INSERTED.ExternalCode,INSERTED.ID,INSERTED.code "
            sql += "VALUES " + ",".join("(" + ",".join("?" for _ in names) + ")" for _ in block)
            cursor.execute(sql, *values)
            if output:
                result.extend(cursor.fetchall())
        return result

    @staticmethod
    def classify(exc):
        if isinstance(exc, DocumentError):
            return "data"
        state = str(exc.args[0]) if getattr(exc, "args", None) else ""
        if state.startswith("08") or state in ("HYT00", "HYT01"):
            return "connection"
        text = str(getattr(exc, "args", ""))
        if "1205" in text or "1222" in text or state == "40001":
            return "temporary"
        native = {int(n) for n in re.findall(r"\((\d+)\)", text)}
        if state.startswith("22") or (state.startswith("23") and "permission" not in text.lower()) or native & {245, 515, 547, 2601, 2627, 8114, 8115, 8152, 2628}:
            return "data"
        return "system"

    def write_batch(self, documents):
        headers, detail_sets = [], []
        for doc in documents:
            header, details = build_payload(doc)
            headers.append(header)
            detail_sets.append(details)
        connection = self.connection
        connection.autocommit = False
        cursor = connection.cursor()
        committing = False
        transaction_ended = False
        try:
            # Recheck in the same transaction immediately before writes.
            existing = self.find_existing([doc.source for doc in documents])
            if existing:
                raise SystemFailure("写入前发现源单号已存在，已停止本批以避免重复")
            codes = [doc.code for doc in documents]
            for block in chunks(codes, 1000):
                marks = ",".join("?" for _ in block)
                if self.query("SELECT code FROM dbo.SA_SaleDelivery WHERE code IN (" + marks + ")", *block):
                    raise SystemFailure("分配的SA编号已被占用，未新增单据")
            returned = self.bulk_insert(cursor, "SA_SaleDelivery", headers, output=True)
            mapping = {key(source): (identifier, code) for source, identifier, code in returned}
            if len(mapping) != len(documents):
                raise SystemFailure("批量表头ID回收数量不一致")
            details = []
            for doc, items in zip(documents, detail_sets):
                identifier, code = mapping[key(doc.source)]
                if code != doc.code:
                    raise SystemFailure("表头ID与SA编号映射不一致")
                for item in items:
                    item["idSaleDeliveryDTO"] = identifier
                details.extend(items)
            self.bulk_insert(cursor, "SA_SaleDelivery_b", details)
            if not self.verify_batch(documents, mapping):
                raise SystemFailure("主明细逐单对账失败，整批回滚")
            committing = True
            connection.commit()
            transaction_ended = True
            return {source: value[0] for source, value in mapping.items()}
        except Exception as exc:
            self.log.warning("数据库批次异常 committing=%s %s", committing, diagnostics(exc))
            try:
                connection.rollback()
                transaction_ended = True
            except Exception as rollback_exc:
                self.log.error("事务回滚失败；不会切换自动提交 %s", diagnostics(rollback_exc))
                raise CommitUnknown("连接中断，需查询确认整批提交结果") from None
            if committing or self.classify(exc) == "connection":
                raise CommitUnknown("连接或提交应答异常，需重新查询确认结果") from None
            raise
        finally:
            try:
                cursor.close()
                if transaction_ended:
                    connection.autocommit = True
            except Exception:
                pass

    def verify_batch(self, documents, mapping):
        expected = {mapping[key(doc.source)][0]: build_payload(doc) for doc in documents}
        header_columns = [name for name in next(iter(expected.values()))[0] if name not in ("createdtime", "updated")]
        columns = [name for name in next(iter(expected.values()))[1][0] if name not in ("createdtime", "updated")]
        detail_groups, heads = defaultdict(list), {}
        for block in chunks(list(expected), 1000):
            marks = ",".join("?" for _ in block)
            records = self.query("SELECT idSaleDeliveryDTO," + ",".join(quote(name) for name in columns) +
                                 " FROM dbo.SA_SaleDelivery_b WHERE idSaleDeliveryDTO IN (" + marks + ")", *block)
            for record in records:
                detail_groups[record.pop("idSaleDeliveryDTO")].append(record)
            head_records = self.query("SELECT ID," + ",".join(quote(name) for name in header_columns) +
                                      " FROM dbo.SA_SaleDelivery WHERE ID IN (" + marks + ")", *block)
            for record in head_records:
                heads[record.pop("ID")] = record
        for identifier, (header, details) in expected.items():
            records = detail_groups[identifier]
            if len(records) != len(details):
                return False
            by_code = {item["code"]: item for item in records}
            if len(by_code) != len(details):
                return False
            for item in details:
                record = by_code.get(item["code"])
                if record is None or any(record[name] != item[name] for name in columns):
                    return False
            head = heads.get(identifier)
            if head is None or any(bind_value(head[name]) != bind_value(header[name]) for name in header_columns):
                return False
        return True

    def verify_document(self, document, identifier):
        return self.verify_batch([document], {key(document.source): (identifier, document.code)})

    def reconnect(self):
        try:
            self.close()
        except Exception:
            pass
        self.open()
