from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
import os
import tempfile
import uuid
import logging
import time
from collections import Counter
from log_util import logger, diagnostics

from .database import CommitUnknown, DocumentError, PreflightError, SystemFailure, SqlRepository
from .domain import Document, SourceRow, build_payload, key, validate_rows, valid_source_code
from .files import TaskJournal, assert_output_writable, export_report


@contextmanager
def account_lock(config):
    identity = key(config.host) + ":" + str(config.port) + "/" + key(config.database)
    path = Path(tempfile.gettempdir()) / ("tplus-import-" + sha256(identity.encode()).hexdigest() + ".lock")
    stream = path.open("a+b")
    try:
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise PreflightError("此账套已有导入任务运行") from None
        yield
    finally:
        # Closing releases the OS lock, including after a process crash.
        stream.close()


def schema_contract():
    row = SourceRow(2, "schema", {"销售标识": ""})
    row.parsed = dict(date=date(2000, 1, 1), customers={"id": 1}, inventory={"id": 1},
                      project_id=None, business={"id": 65}, warehouse={"id": 1},
                      unit={"id": 1, "name": "个"}, quantity=Decimal(0), price=Decimal(0),
                      rate=Decimal(0), gross=Decimal(0), net=Decimal(0), tax=Decimal(0))
    header, details = build_payload(Document("schema", [row], "SA2000010100001"))
    return header, details[0]


class ImportEngine:
    def __init__(self, config, source, rows, columns, runtime_dir, stop, progress,
                 repository_factory=SqlRepository, batch_limit=5000, api_client=None):
        self.config, self.source, self.rows, self.columns = config, str(source), rows, columns
        self.stop, self.progress = stop, progress
        self.task_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
        self.journal = TaskJournal(runtime_dir, self.task_id, source, config.database)
        self.factory, self.batch_limit = repository_factory, batch_limit
        # 测试期间不创建 API 客户端；保留参数以便恢复审批逻辑。
        # if api_client is None:
        #     from .tplus_api import TPlusApiClient
        #     api_client = TPlusApiClient(getattr(config, "api", None) or getattr(config, "tplus_api", None))
        self.api_client = api_client
        self.repository = None
        self.message = ""
        self.report = None
        self.halt = False
        self.log = logging.LoggerAdapter(logger, {"task_id": self.task_id})
        self.batch_number = 0

    def checkpoint(self, phase):
        try:
            self.journal.save(self.rows, phase, self.message)
            return True
        except OSError as exc:
            self.log.error("任务快照保存失败 phase=%s %s", phase, diagnostics(exc))
            self.halt = True
            self.message = "任务日志保存失败，停止后续写入；已有提交状态保留，请保存当前结果"
            return False

    def run(self):
        # Preserve the previous result if prerequisites fail before a new task starts.
        started = time.perf_counter()
        self.log.info("导入任务开始 database=%s file=%s rows=%d", self.config.database, self.source, len(self.rows))
        try:
            assert_output_writable(self.source)
        except OSError as exc:
            self.log.error("输出目录检查失败，未开始写入 %s", diagnostics(exc))
            raise
        for row in self.rows:
            row.reset()
        self.checkpoint("任务开始")
        try:
            with account_lock(self.config):
                self.repository = self.factory(self.config)
                self.repository.log = self.log
                self.progress("连接目标账套", 0, 0)
                self.repository.open()
                self.log.info("目标账套连接成功 database=%s", self.config.database)
                cache = self.repository.load_cache(self.stop, self.progress)
                if cache is None or self.stop.is_set():
                    self.message = "用户停止：缓存阶段结束，未执行写入"
                else:
                    try:
                        self.repository.preflight(*schema_contract())
                        preflight_error = None
                    except PreflightError as exc:
                        preflight_error = str(exc)
                        self.log.error("运行预检未通过 reason=%s", preflight_error)
                    documents = validate_rows(self.rows, cache, self.stop, self.progress)
                    self.log.info("数据校验结束 documents=%d row_states=%s", len(documents), dict(Counter(row.status for row in self.rows)))
                    if not self.stop.is_set():
                        self.progress("按源单号去重", 0, 0)
                        existing = self.repository.find_existing([doc.source for doc in documents if valid_source_code(doc.source)])
                        for doc in documents:
                            matches = existing.get(key(doc.source), [])
                            if matches:
                                for row in doc.rows:
                                    row.status = "重复跳过"
                                    if len(matches) == 1:
                                        row.sa_code, row.header_id = matches[0]["code"], matches[0]["id"]
                                    else:
                                        row.notes.append("主表已有多条同源单号记录，未新增")
                        eligible = [doc for doc in documents if doc.ready]
                        self.log.info("源单号去重结束 duplicate_documents=%d ready_documents=%d", sum(bool(existing.get(key(doc.source))) for doc in documents), len(eligible))
                        if preflight_error:
                            self.message = "运行前置条件不满足：" + preflight_error
                            for doc in eligible:
                                for row in doc.rows:
                                    row.status = "未处理"
                                    row.reasons.append(self.message)
                        # 测试期间跳过导入前的 Token 校验，直接写入数据库。
                        # elif eligible and getattr(getattr(self.config, "api", None), "enabled", True):
                        #     # 前置获取 Token，若获取失败则直接阻断，不进行数据库插入
                        #     self.progress("获取 T+ 接口授权", 0, 0)
                        #     token_ok, token_msg = self.api_client.get_token()
                        #     if not token_ok:
                        #         self.log.error("T+ API认证失败，直接阻断写入 reason=%s", token_msg)
                        #         self.message = "T+ API认证失败，未写入数据库：" + token_msg
                        #         for doc in eligible:
                        #             for row in doc.rows:
                        #                 row.status = "未处理"
                        #                 row.reasons.append(self.message)
                        #     else:
                        #         eligible = self.allocate_codes(eligible)
                        #         self.checkpoint("已校验及去重")
                        #         self.write_documents(eligible)
                        else:
                            eligible = self.allocate_codes(eligible)
                            self.checkpoint("已校验及去重")
                            self.write_documents(eligible)
                    if self.stop.is_set() and not self.message:
                        self.message = "用户停止：已提交保留，未执行部分标记未处理"
        except (PreflightError, SystemFailure) as exc:
            self.log.error("任务停止 reason=%s %s", str(exc), diagnostics(exc))
            self.message = str(exc)
        except Exception as exc:
            self.log.error("导入任务异常 %s", diagnostics(exc))
            self.message = self.config.safe_error(exc)
        finally:
            if self.repository is not None:
                try:
                    self.repository.close()
                except Exception:
                    pass
            for row in self.rows:
                if row.status in ("待处理", "校验中", "已校验", "待写入"):
                    row.status = "未处理"
                    row.reasons.append(self.message or "任务已终止，未执行")
            # A batch marked 待确认 before a crash is never silently declared successful.
            self.checkpoint("处理结束，准备导出")
        self.progress("导出结果", 0, 0)
        try:
            self.report = export_report(self.rows, self.columns, self.source, self.config.database,
                                        self.task_id, message=self.message)
            self.checkpoint("完成")
        except Exception as exc:
            self.log.error("结果导出失败；已提交业务状态保留 %s", diagnostics(exc))
            self.message += "；异常结果导出失败，结果已保留，可重试导出（请检查目录权限、空间或文件占用）"
            self.checkpoint("导出失败")
        if self.stop.is_set():
            self.log.warning("任务已响应停止请求；已提交数据保留")
        self.log.info("导入任务结束 elapsed_seconds=%.3f row_states=%s report=%s message=%s",
                      time.perf_counter() - started, dict(Counter(row.status for row in self.rows)), self.report or "-", self.message or "完成")
        self.progress("任务结束", len(self.rows), len(self.rows))
        return dict(task_id=self.task_id, database=self.config.database, report=str(self.report) if self.report else "",
                    journal=str(self.journal.path), message=self.message, rows=self.rows)

    def allocate_codes(self, documents):
        sequences, blocked, valid = {}, {}, []
        for doc in documents:
            if self.stop.is_set():
                break
            day = doc.rows[0].parsed["date"]
            try:
                if day in blocked:
                    raise PreflightError(blocked[day])
                if day not in sequences:
                    sequences[day] = self.repository.max_sequence(day)
                    self.log.info("日期组编号起点 date=%s existing_max=%d", day, sequences[day])
                sequences[day] += 1
                if sequences[day] > 99999:
                    raise PreflightError("当日SA编号超过五位流水上限")
                doc.code = "SA" + day.strftime("%Y%m%d") + f"{sequences[day]:05d}"
                header, details = build_payload(doc)
                self.repository.validate_payload("SA_SaleDelivery", header)
                for item in details:
                    self.repository.validate_payload("SA_SaleDelivery_b", dict(item, idSaleDeliveryDTO=0))
                for row in doc.rows:
                    row.sa_code = doc.code
                valid.append(doc)
            except PreflightError as exc:
                self.log.warning("日期组编号失败 date=%s reason=%s", day, str(exc))
                blocked[day] = str(exc)
                for row in doc.rows:
                    row.status = "校验失败"
                    row.reasons.append("日期组编号失败：" + str(exc))
                # Earlier accepted docs of this date must also be excluded on overflow/abnormality.
                for prior in valid[:]:
                    if prior.rows[0].parsed["date"] == day:
                        valid.remove(prior)
                        for row in prior.rows:
                            row.status = "校验失败"
                            row.reasons.append("日期组编号失败：" + str(exc))
            except (DocumentError, UnicodeError, ArithmeticError) as exc:
                self.log.warning("待写字段校验失败 source=%s %s", doc.source, diagnostics(exc))
                for row in doc.rows:
                    row.status = "校验失败"
                    row.reasons.append("待写字段校验失败：" + str(exc))
        return valid

    def write_documents(self, documents):
        batch, size = [], 0
        for doc in documents:
            if self.stop.is_set() or self.halt:
                break
            if batch and size + len(doc.rows) > self.batch_limit:
                self.write_isolated(batch)
                batch, size = [], 0
                if self.stop.is_set() or self.halt:
                    break
            batch.append(doc)
            size += len(doc.rows)
        if batch and not self.stop.is_set() and not self.halt:
            self.write_isolated(batch)

    def write_isolated(self, batch, retry=0):
        if not batch or self.stop.is_set() or self.halt:
            return
        for doc in batch:
            for row in doc.rows:
                row.status = "待确认"
        # Persist intent BEFORE handing data to the database.
        if not self.checkpoint("本批写入中，提交结果尚待确认"):
            for doc in batch:
                for row in doc.rows:
                    row.status = "待写入"
            return
        self.batch_number += 1
        batch_id = self.batch_number
        batch_started = time.perf_counter()
        self.log.info("批次开始 batch=%d documents=%d rows=%d retry=%d", batch_id, len(batch), sum(len(doc.rows) for doc in batch), retry)
        self.progress("批量写入", sum(row.status == "导入成功" for row in self.rows), len(self.rows))
        try:
            mapping = self.repository.write_batch(batch)
        except CommitUnknown as exc:
            self.log.error("批次提交结果不明 batch=%d %s", batch_id, diagnostics(exc))
            self.recover_batch(batch)
            return
        except Exception as exc:
            category = self.repository.classify(exc)
            self.log.warning("批次回滚 batch=%d category=%s %s", batch_id, category, diagnostics(exc))
            for doc in batch:
                for row in doc.rows:
                    row.status = "待写入"
            if category == "temporary" and retry < 2 and not self.stop.is_set():
                self.log.warning("暂时故障重试 batch=%d next_retry=%d", batch_id, retry + 1)
                self.write_isolated(batch, retry + 1)
            elif category == "data":
                if self.stop.is_set():
                    return
                if len(batch) > 1:
                    middle = len(batch) // 2
                    self.log.warning("按完整单据拆分批次 batch=%d left=%d right=%d", batch_id, middle, len(batch) - middle)
                    self.write_isolated(batch[:middle])
                    self.write_isolated(batch[middle:])
                else:
                    reason = str(exc) if isinstance(exc, DocumentError) else self.config.safe_error(exc)
                    self.log.error("单据写入失败 source=%s sa_code=%s rows=%d reason=%s", batch[0].source, batch[0].code, len(batch[0].rows), reason)
                    for row in batch[0].rows:
                        row.status = "写入失败"
                        row.reasons.append(reason)
            else:
                self.halt = True
                self.message = "批次已回滚，停止后续写入：" + (str(exc) if isinstance(exc, SystemFailure) else self.config.safe_error(exc))
            self.checkpoint("本批回滚后处理")
            return
        for doc in batch:
            for row in doc.rows:
                row.status, row.header_id = "导入成功", mapping[key(doc.source)]
        self.log.info("批次提交成功 batch=%d documents=%d rows=%d elapsed_seconds=%.3f", batch_id, len(batch), sum(len(doc.rows) for doc in batch), time.perf_counter() - batch_started)
        self.checkpoint("本批提交成功")
        # 测试期间只插入数据，不调用审批，也不执行审批失败清理。
        # if getattr(getattr(self.config, "api", None), "enabled", True):
        #     self.approve_batch(batch, mapping)

    def recover_batch(self, batch):
        self.log.warning("开始核实断线提交结果 documents=%d", len(batch))
        try:
            self.repository.reconnect()
            existing = self.repository.find_existing([doc.source for doc in batch])
            absent = []
            uncertain = False
            for doc in batch:
                matches = existing.get(key(doc.source), [])
                if not matches:
                    absent.append(doc)
                    for row in doc.rows:
                        row.status = "待写入"
                elif len(matches) == 1 and self.repository.verify_document(doc, matches[0]["id"]):
                    for row in doc.rows:
                        row.status = "导入成功"
                        row.header_id = matches[0]["id"]
                else:
                    uncertain = True
                    for row in doc.rows:
                        row.reasons.append("提交结果核验不一致，未盲目重插")
            if uncertain:
                self.halt = True
                self.message = "提交结果存在待确认单据，停止后续写入"
            elif absent:
                # A single reconnect is allowed; repeated disconnections require manual retry.
                self.halt = True
                self.message = "连接已恢复：部分单据确认未提交，标记未处理，可重新导入源文件"
            self.log.warning("提交结果核验结束 absent_documents=%d uncertain=%s", len(absent), uncertain)
            self.checkpoint("已核实断线提交结果")
        except Exception as exc:
            self.log.error("断线提交结果核验失败 %s", diagnostics(exc))
            self.halt = True
            self.message = "无法核实提交结果，相关单据保持待确认；重新导入前须查询目标账套"

    def approve_batch(self, batch, mapping):
        """采用线程池并发数 3 审批单据；记录审批失败数据，最后批量删除草稿记录。"""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        doc_tasks = []
        for doc in batch:
            header_id = mapping.get(key(doc.source))
            if header_id is not None:
                doc_tasks.append((doc, header_id, doc.code))

        if not doc_tasks:
            return

        self.log.info("开始审批批次单据 documents=%d 并发数=3", len(doc_tasks))
        failed_docs = []
        done_count = 0

        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_doc = {
                executor.submit(self.api_client.audit_voucher, sa_code, header_id): (doc, header_id)
                for doc, header_id, sa_code in doc_tasks
            }
            for future in as_completed(future_to_doc):
                doc, header_id = future_to_doc[future]
                done_count += 1
                self.progress("API审批单据", done_count, len(doc_tasks))
                try:
                    success, msg = future.result()
                    if not success:
                        failed_docs.append((doc, header_id, msg))
                except Exception as exc:
                    failed_docs.append((doc, header_id, str(exc)))

        if failed_docs:
            failed_ids = [header_id for _, header_id, _ in failed_docs]
            self.log.warning("检测到审批失败单据 count=%d，从数据库中批量删除", len(failed_ids))
            try:
                self.repository.delete_failed_vouchers(failed_ids)
            except Exception as exc:
                self.log.error("批量删除失败单据异常 %s", diagnostics(exc))

            # 保持现有的失败数据导出逻辑：标记为审批失败并记录具体原因
            for doc, header_id, reason in failed_docs:
                for row in doc.rows:
                    row.status = "审批失败"
                    row.header_id = None  # 数据库记录已删除
                    row.reasons.append(f"T+ API审批失败：{reason}")
            self.checkpoint("审批失败单据已清理并标记")
