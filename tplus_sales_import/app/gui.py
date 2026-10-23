import sys
import threading
import time
import logging
from log_util import logger, diagnostics
from collections import Counter
from pathlib import Path

from PyQt5.QtCore import (QAbstractTableModel, QModelIndex, QSortFilterProxyModel, QThread,
                          Qt, QUrl, QTimer, pyqtSignal)
from PyQt5.QtGui import QDesktopServices, QCursor
from PyQt5.QtWidgets import (QApplication, QComboBox, QFileDialog, QHBoxLayout, QGridLayout, QLabel,
                            QLineEdit, QMainWindow, QMessageBox, QProgressBar, QPushButton,
                            QScrollArea, QTableView, QVBoxLayout, QWidget, QDialog,
                            QDialogButtonBox, QTableWidget, QTableWidgetItem, QAbstractItemView)

from .configuration import DatabaseConfig, application_dir
from .database import CommitUnknown, PreflightError, SqlRepository
from .engine import ImportEngine
from .files import TaskJournal, export_report, read_xls
from .undo import UndoSession
from .login import LoginClient


class UndoConfirmDialog(QDialog):
    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.setWindowTitle("二次确认：撤销本次导入")
        self.resize(850, 560)
        layout = QVBoxLayout(self)
        label = QLabel(
            f"服务器：{session.config.host}:{session.config.port}\n账套：{session.config.database}"
            f"\n任务：{session.task_id}\n文件：{session.source}\n\n"
            f"删除表 dbo.SA_SaleDelivery：{len(session.documents)} 条表头\n"
            f"删除表 dbo.SA_SaleDelivery_b：{sum(len(doc.rows) for doc in session.documents)} 条明细\n"
            f"删除表 dbo.ARAP_Detail：{sum(len(doc.rows) for doc in session.documents)} 条往来明细\n"
            "以下为本次新增单据；确认后先删往来明细、再删存货明细、最后删表头。重复跳过及失败数据不删除。")
        label.setWordWrap(True)
        layout.addWidget(label)
        table = QTableWidget(len(session.documents), 4)
        table.setHorizontalHeaderLabels(["表头ID", "SA单据编号", "用友单号", "明细条数"])
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        for index, doc in enumerate(session.documents):
            for column, value in enumerate((session.mapping[doc.source.strip().casefold()][0],
                                            doc.code, doc.source, len(doc.rows))):
                table.setItem(index, column, QTableWidgetItem(str(value)))
        table.horizontalHeader().setStretchLastSection(True)
        table.setColumnWidth(1, 190)
        table.setColumnWidth(2, 280)
        layout.addWidget(table)
        buttons = QDialogButtonBox(QDialogButtonBox.Yes | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Yes).setText("确认删除本次导入数据")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.button(QDialogButtonBox.Yes).setAutoDefault(False)
        buttons.button(QDialogButtonBox.Cancel).setDefault(True)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class RowModel(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows, self.source_columns = [], []

    @property
    def headers(self):
        leading = ["用友单号", "客户名称", "单据日期", "客户编码", "商品编码", "数量", "含税金额"]
        return ["结果状态"] + leading + ["全部原因", "说明", "SA编号", "表头ID", "工作表", "源行号"] + [name for name in self.source_columns if name not in leading]

    def set_rows(self, rows, columns):
        self.beginResetModel()
        self.rows, self.source_columns = rows, columns
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self.rows[index.row()]
        if role not in (Qt.DisplayRole, Qt.ToolTipRole):
            return None
        name = self.headers[index.column()]
        fixed = {"结果状态": row.status, "全部原因": "；".join(row.reasons), "说明": "；".join(row.notes),
                 "SA编号": row.sa_code, "表头ID": row.header_id or "", "工作表": row.sheet, "源行号": row.number}
        return str(fixed[name] if name in fixed else row.values.get(name, ""))

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            return self.headers[section] if orientation == Qt.Horizontal else section + 1
        return None

    def refresh(self):
        if self.rows:
            self.dataChanged.emit(self.index(0, 0), self.index(len(self.rows) - 1, 11))


class RowFilter(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.status, self.search = "全部", ""
        self.setDynamicSortFilter(False)

    def filterAcceptsRow(self, number, parent):
        row = self.sourceModel().rows[number]
        return (self.status == "全部" or row.status == self.status) and (not self.search or self.search in row.voucher.casefold())


class TaskWorker(QThread):
    progress = pyqtSignal(str, int, int)
    completed = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, action, config=None, source=None, rows=None, columns=None, runtime=None, report_args=None,
                 undo_session=None, access_token=None):
        super().__init__()
        self.action, self.config, self.source = action, config, source
        self.rows, self.columns, self.runtime = rows, columns, runtime
        self.stop = threading.Event()
        self.report_args = report_args
        self.undo_session = undo_session
        self.access_token = access_token

    def run(self):
        started = time.perf_counter()
        logger.info("后台操作开始 action=%s file=%s", self.action, self.source or "-")
        try:
            if self.action == "load":
                result = read_xls(self.source, self.stop, self.progress.emit)
            elif self.action == "login":
                repository = SqlRepository(self.config)
                try:
                    db_name = repository.open()
                finally:
                    repository.close()
                token = LoginClient().authenticate(self.config.login)
                result = dict(database=db_name, access_token=token)
            elif self.action == "export":
                result = str(export_report(**self.report_args))
            elif self.action in ("undo_prepare", "undo_delete"):
                session = self.undo_session
                self.task_id = session.task_id
                repository = SqlRepository(session.config)
                repository.log = logging.LoggerAdapter(logger, {"task_id": session.task_id})
                try:
                    repository.open()
                    if self.action == "undo_prepare":
                        result = session.prepare(repository)
                    else:
                        result = session.execute(repository)
                finally:
                    try:
                        repository.close()
                    except Exception as exc:
                        logger.warning("撤销连接关闭失败 %s", diagnostics(exc))
                if self.action == "undo_delete":
                    imported_ids = {value[0] for value in session.mapping.values()}
                    for row in self.rows:
                        if row.status == "导入成功" and row.header_id in imported_ids:
                            row.status = "已撤销"
                            row.notes.append("本次导入数据已撤销删除")
                    result = dict(result, message="本次导入已撤销", report="")
                    try:
                        TaskJournal(self.runtime, session.task_id, session.source, session.config.database).save(
                            self.rows, "已撤销", result["message"])
                        result["report"] = str(export_report(self.rows, self.columns, session.source,
                                                             session.config.database, session.task_id,
                                                             message=result["message"]))
                    except Exception as exc:
                        logger.error("撤销已提交，但结果保存失败 %s", diagnostics(exc))
                        result["message"] += "；结果保存失败，请重试导出，数据库删除已完成"
            else:
                if not self.access_token:
                    raise PreflightError("请先登录成功后再导入数据")
                from .tplus_api import TPlusApiClient
                client = TPlusApiClient(self.config.api)
                client.token = self.access_token
                engine = ImportEngine(self.config, self.source, self.rows, self.columns,
                                      self.runtime, self.stop, self.progress.emit, api_client=client)
                self.task_id = engine.task_id
                result = engine.run()
            logger.info("后台操作结束 action=%s elapsed_seconds=%.3f", self.action, time.perf_counter() - started)
            self.completed.emit(result)
        except ModuleNotFoundError as exc:
            module = exc.name or "未知模块"
            logger.error("运行依赖缺失 action=%s runtime=%s %s", self.action, sys.executable, diagnostics(exc))
            if getattr(sys, "frozen", False):
                message = f"程序缺少依赖模块：{module}。请使用完整的发布文件夹，或重新打包程序。"
            else:
                message = (f"当前Python环境缺少依赖：{module}。\n解释器：{sys.executable}"
                           f"\n请在该解释器中安装依赖后重试，依赖清单：{application_dir() / 'requirements.txt'}")
            self.failed.emit(message)
        except (ValueError, PreflightError, CommitUnknown) as exc:
            if self.action == "undo_delete" and isinstance(exc, CommitUnknown):
                for row in self.rows:
                    if row.status == "导入成功":
                        row.status = "撤销待确认"
                        row.notes.append(str(exc))
                try:
                    session = self.undo_session
                    TaskJournal(self.runtime, session.task_id, session.source, session.config.database).save(
                        self.rows, "撤销待确认", str(exc))
                except Exception as journal_exc:
                    logger.error("撤销待确认状态保存失败 %s", diagnostics(journal_exc))
            logger.warning("后台操作未完成 action=%s reason=%s %s", self.action, str(exc), diagnostics(exc))
            self.failed.emit(str(exc))
        except Exception as exc:
            logger.error("后台操作异常 action=%s %s", self.action, diagnostics(exc))
            if self.action == "load":
                message = "XLS读取失败，请检查文件格式、是否损坏及读取权限。"
            elif self.action == "export":
                message = "结果保存失败，请检查目录权限、磁盘空间或文件占用。"
            else:
                message = self.config.safe_error(exc) if self.config else "任务异常，未执行后续操作。"
            self.failed.emit(message)


class ImportWindow(QMainWindow):
    def __init__(self, config_path=None):
        super().__init__()
        logger.info("程序启动 runtime=%s python_version=%s frozen=%s", sys.executable, sys.version.split()[0], bool(getattr(sys, "frozen", False)))
        self.setWindowTitle("T+ 销货单导入")
        self.config_path = Path(config_path) if config_path else application_dir() / "config.ini"
        self.runtime = application_dir() / "runtime"
        self.config, self.tested, self.source = None, None, None
        self.access_token = None
        self.worker, self.result = None, None
        self.undo_session, self.pending_undo = None, None
        self.closing = False
        root = QWidget()
        layout = QVBoxLayout(root)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setWidget(root)
        self.setCentralWidget(scroll)
        self.config_label = QLabel()
        self.config_label.setWordWrap(True)
        config_path_label = QLabel("配置文件（请手动修改后重新登录）：" + str(self.config_path))
        config_path_label.setWordWrap(True)
        layout.addWidget(config_path_label)
        layout.addWidget(self.config_label)
        self.connection_label = QLabel("登录状态：未登录，请先登录")
        layout.addWidget(self.connection_label)
        toolbar = QGridLayout()
        self.test_button = QPushButton("登录 / 重新读取配置")
        self.choose_button = QPushButton("选择XLS文件")
        self.import_button = QPushButton("导入全部数据")
        self.stop_button = QPushButton("停止")
        self.retry_button = QPushButton("重试导出")
        self.save_button = QPushButton("结果另存为")
        self.folder_button = QPushButton("打开输出目录")
        self.restore_button = QPushButton("恢复任务结果")
        self.undo_button = QPushButton("撤销本次导入")
        self.online_token_button = QPushButton("在线获取 Token")
        for index, button in enumerate((self.test_button, self.choose_button, self.import_button, self.stop_button,
                                        self.retry_button, self.save_button, self.folder_button, self.restore_button,
                                        self.undo_button, self.online_token_button)):
            toolbar.addWidget(button, index // 4, index % 4)
        self.online_token_button.hide()
        layout.addLayout(toolbar)
        self.import_gate_label = QLabel()
        self.import_gate_label.setWordWrap(True)
        layout.addWidget(self.import_gate_label)
        self._last_import_gate = None
        self.source_label = QLabel("未加载文件")
        self.source_label.setWordWrap(True)
        layout.addWidget(self.source_label)
        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("按源用友单号筛选（不改变导入范围）")
        self.status = QComboBox()
        self.status.addItems(["全部", "待处理", "待写入", "导入成功", "已撤销", "撤销待确认", "重复跳过", "校验失败", "整单受阻", "写入失败", "待确认", "未处理"])
        filters.addWidget(self.search)
        filters.addWidget(self.status)
        layout.addLayout(filters)
        self.model = RowModel(self)
        self.proxy = RowFilter(self)
        self.proxy.setSourceModel(self.model)
        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(False)
        self.table.horizontalHeader().setDefaultSectionSize(130)
        widths = {"结果状态": 95, "用友单号": 300, "客户名称": 260, "单据日期": 140,
                  "客户编码": 100, "商品编码": 100, "数量": 75, "含税金额": 110,
                  "全部原因": 320, "说明": 240}
        for index, name in enumerate(self.model.headers):
            if name in widths:
                self.table.setColumnWidth(index, widths[name])
        layout.addWidget(self.table)
        self.summary_label = QLabel("尚无数据")
        self.summary_label.setWordWrap(True)
        self.phase_label = QLabel("请先登录，再选择XLS文件并导入")
        self.phase_label.setWordWrap(True)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.phase_label)
        self.progress = QProgressBar()
        layout.addWidget(self.progress)
        self.test_button.clicked.connect(self.login)
        self.choose_button.clicked.connect(self.choose_file)
        self.import_button.clicked.connect(self.start_import)
        self.stop_button.clicked.connect(self.request_stop)
        self.retry_button.clicked.connect(lambda: self.start_export(False))
        self.save_button.clicked.connect(lambda: self.start_export(True))
        self.folder_button.clicked.connect(self.open_output)
        self.restore_button.clicked.connect(self.restore_result)
        self.undo_button.clicked.connect(self.start_undo)
        self.online_token_button.clicked.connect(self.open_online_token)
        self.search.textChanged.connect(self.apply_filter)
        self.status.currentTextChanged.connect(self.apply_filter)
        self.reload_config()
        self.update_buttons()
        self.apply_initial_geometry()

    def open_online_token(self):
        from .online_token import OnlineTokenDialog
        dialog = OnlineTokenDialog(self)
        dialog.exec_()
        dialog.deleteLater()

    def apply_initial_geometry(self):
        screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        width, height = area.width() * 2 // 3, area.height() * 2 // 3
        self.resize(width, height)
        self.move(area.x() + (area.width() - width) // 2,
                  area.y() + (area.height() - height) // 2)
        logger.info("启动窗口大小 available_width=%d available_height=%d window_width=%d window_height=%d",
                    area.width(), area.height(), width, height)

    def reload_config(self):
        try:
            self.config = DatabaseConfig.load(self.config_path)
            self.config_label.setText(self.config.display())
            logger.info("配置加载完成 file=%s server=%s port=%s database=%s", self.config_path, self.config.host, self.config.port, self.config.database)
            return True
        except (ValueError, OSError) as exc:
            logger.warning("配置加载失败 file=%s %s", self.config_path, diagnostics(exc))
            self.config, self.tested = None, None
            self.access_token = None
            detail = str(exc) if isinstance(exc, ValueError) else "无法读取配置文件，请检查权限"
            self.config_label.setText("配置文件无效：" + detail)
            return False

    def update_buttons(self):
        busy = self.worker is not None
        self.online_token_button.setEnabled(not busy)
        self.test_button.setEnabled(not busy)
        self.choose_button.setEnabled(not busy and self.tested == self.config and bool(self.access_token))
        self.choose_button.setToolTip("选择XLS文件" if self.choose_button.isEnabled() else "请先登录成功，并等待当前任务结束")
        can_import = not busy and bool(self.model.rows) and self.tested == self.config and bool(self.access_token)
        self.import_button.setEnabled(can_import)
        if busy:
            reason = "正在执行任务，请等待结束后再导入"
        elif self.tested != self.config or not self.access_token:
            reason = "请先登录成功（数据库连接和Token认证均须通过）"
        elif not self.model.rows:
            reason = "请先选择并成功加载XLS文件"
        else:
            reason = f"可以导入：已加载{len(self.model.rows)}行；登录已通过，点击开始导入"
        self.import_gate_label.setText("导入状态：" + reason)
        self.import_button.setToolTip(reason)
        state = (can_import, reason)
        if state != self._last_import_gate:
            logger.info("导入按钮状态 enabled=%s rows=%d reason=%s", can_import, len(self.model.rows), reason)
            self._last_import_gate = state
        self.stop_button.setEnabled(busy and self.worker.action in ("import", "load"))
        self.retry_button.setEnabled(not busy and self.result is not None)
        self.save_button.setEnabled(not busy and self.result is not None)
        self.restore_button.setEnabled(not busy)
        self.folder_button.setEnabled(not busy and (self.source is not None or self.result is not None))
        self.undo_button.setEnabled(not busy and not self.closing and self.undo_session is not None
                                    and self.undo_session.state == "ready")

    def start_worker(self, worker, callback):
        self.worker = worker
        worker.progress.connect(self.on_progress)
        worker.completed.connect(callback)
        worker.failed.connect(self.on_error)
        worker.finished.connect(self.worker_finished)
        self.update_buttons()
        worker.start()

    def worker_finished(self):
        worker = self.worker
        self.worker = None
        if worker:
            worker.deleteLater()
        self.model.refresh()
        self.apply_filter()
        self.update_summary()
        self.update_buttons()
        if self.closing:
            self.close()
        elif self.pending_undo is not None:
            QTimer.singleShot(0, self.confirm_undo)

    def on_progress(self, phase, done, total):
        self.phase_label.setText(phase)
        self.progress.setRange(0, max(total, 0))
        if total:
            self.progress.setValue(done)
        self.model.refresh()
        self.update_summary()

    def on_error(self, message):
        if self.undo_session is not None and self.undo_session.state == "unknown" and self.result:
            self.result.update(message=message, report="")
        if self.worker is not None and self.worker.action == "login":
            self.tested, self.access_token = None, None
            self.connection_label.setText("登录状态：登录失败，请检查配置后重新登录")
        self.phase_label.setText(message)
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        if not self.closing:
            QMessageBox.warning(self, "任务未完成", message)

    def login(self):
        if self.worker is not None:
            return
        self.tested, self.access_token = None, None
        self.connection_label.setText("登录状态：正在验证数据库和Token接口…")
        if not self.reload_config():
            self.connection_label.setText("登录状态：配置无效，请修改配置文件")
            self.update_buttons()
            return
        config = self.config
        def complete(result):
            self.tested, self.access_token = config, result["access_token"]
            self.connection_label.setText("登录成功：" + result["database"] + "（数据库和Token认证均通过）")
            self.phase_label.setText("登录成功，请选择文件并导入数据")
            self.progress.setRange(0, 1)
            self.progress.setValue(1)
        self.start_worker(TaskWorker("login", config=config), complete)

    def choose_file(self):
        if self.worker is not None or self.tested != self.config or not self.access_token:
            self.update_buttons()
            return
        source, _ = QFileDialog.getOpenFileName(self, "选择销货单源文件", str(application_dir()), "Excel 97-2003 (*.xls)")
        if not source:
            return
        self.clear_undo()
        def complete(payload):
            rows, columns = payload
            self.source, self.result = source, None
            self.model.set_rows(rows, columns)
            self.source_label.setText("当前输入：" + source + "；结果保存到该文件所在文件夹")
            self.phase_label.setText("加载成功：预览只读，尚未校验或写入")
            self.progress.setRange(0, 1)
            self.progress.setValue(1)
        self.start_worker(TaskWorker("load", source=source), complete)

    def start_import(self):
        if self.worker is not None or not self.model.rows:
            self.update_buttons()
            return
        if self.tested != self.config or not self.access_token:
            self.phase_label.setText("请先登录成功后再导入数据")
            self.update_buttons()
            return
        try:
            current = DatabaseConfig.load(self.config_path)
        except (ValueError, OSError) as exc:
            self.tested, self.access_token = None, None
            self.reload_config()
            self.connection_label.setText("连接状态：配置无效，未开始导入")
            self.update_buttons()
            self.on_error(str(exc) if isinstance(exc, ValueError) else "无法读取配置文件，请检查权限")
            return
        if current != self.tested:
            self.tested, self.access_token = None, None
            self.config = current
            self.config_label.setText(current.display())
            self.connection_label.setText("登录状态：配置已变更，请重新登录")
            self.update_buttons()
            return
        self.config = current
        self.config_label.setText(current.display())
        self.connection_label.setText("登录状态：已登录，导入目标账套 " + current.database)
        self.result = None
        self.clear_undo()
        self.start_worker(TaskWorker("import", config=current, source=self.source, rows=self.model.rows,
                                     columns=self.model.source_columns, runtime=self.runtime,
                                     access_token=self.access_token), self.import_complete)

    def import_complete(self, result):
        self.result = result
        if not self.closing:
            self.undo_session = UndoSession.from_result(self.worker.config, self.source, result)
        self.phase_label.setText((result["message"] or "处理完成") +
                                 ("；结果：" + result["report"] if result["report"] else "；请重试导出或另存为"))

    def clear_undo(self):
        self.undo_session, self.pending_undo = None, None
        self.update_buttons()

    def start_undo(self):
        if self.worker is not None or self.undo_session is None or self.undo_session.state != "ready":
            return
        self.phase_label.setText("正在核对本次导入的主明细，核对后显示删除确认清单")
        def complete(session):
            self.pending_undo = session
        self.start_worker(TaskWorker("undo_prepare", config=self.undo_session.config,
                                     undo_session=self.undo_session), complete)

    def confirm_undo(self):
        session, self.pending_undo = self.pending_undo, None
        if self.closing or session is None or session is not self.undo_session or self.worker is not None:
            return
        if UndoConfirmDialog(session, self).exec_() != QDialog.Accepted:
            self.phase_label.setText("已取消撤销，本次导入数据保留")
            return
        logger.warning("用户确认撤销 task=%s database=%s headers=%d details=%d", session.task_id,
                       session.config.database, len(session.documents), sum(len(doc.rows) for doc in session.documents))
        self.start_worker(TaskWorker("undo_delete", config=session.config, undo_session=session,
                                     rows=self.model.rows, columns=self.model.source_columns,
                                     runtime=self.runtime), self.undo_complete)

    def undo_complete(self, result):
        self.result.update(message=result["message"], report=result["report"])
        self.phase_label.setText(result["message"] + ("；结果：" + result["report"] if result["report"] else ""))
        self.clear_undo()

    def request_stop(self):
        if self.worker:
            logger.warning("收到停止请求 action=%s；等待当前操作安全结束", self.worker.action, extra={"task_id": getattr(self.worker, "task_id", "-")})
            self.worker.stop.set()
            self.phase_label.setText("正在停止：等待当前操作安全结束并保存结果")
            self.stop_button.setEnabled(False)

    def start_export(self, choose_folder):
        if not self.result:
            return
        folder = None
        if choose_folder:
            folder = QFileDialog.getExistingDirectory(self, "选择结果另存目录", str(Path(self.source).parent))
            if not folder:
                return
        arguments = dict(rows=self.model.rows, columns=self.model.source_columns, source=self.source,
                         database=self.result.get("database", self.config.database if self.config else "unknown"),
                         task_id=self.result["task_id"], folder=folder, message=self.result.get("message", ""), include_all=choose_folder)
        def complete(path):
            self.result["report"] = path
            self.phase_label.setText("结果已保存：" + path)
            self.progress.setRange(0, 1)
            self.progress.setValue(1)
        self.start_worker(TaskWorker("export", report_args=arguments), complete)

    def restore_result(self):
        path, _ = QFileDialog.getOpenFileName(self, "恢复本机任务结果", str(self.runtime), "任务结果 (*.json)")
        if not path:
            return
        self.clear_undo()
        try:
            payload, rows = TaskJournal.load(path)
            logger.info("恢复任务结果 file=%s rows=%d", path, len(rows), extra={"task_id": payload["task_id"]})
            for row in rows:
                if row.status in ("待处理", "校验中", "已校验", "待写入"):
                    row.status = "未处理"
                    row.reasons.append("程序中断，尚未确认执行")
            columns = list(dict.fromkeys(name for row in rows for name in row.values))
            self.source = payload["source"]
            self.result = dict(task_id=payload["task_id"], database=payload["database"], report="", journal=path,
                               message="恢复任务结果；待确认单据未判定成功，重跑前将重新查询目标账套")
            self.model.set_rows(rows, columns)
            self.source_label.setText("恢复的输入：" + self.source)
            self.phase_label.setText(self.result["message"])
            self.apply_filter()
            self.update_summary()
            self.update_buttons()
        except (OSError, ValueError, KeyError, TypeError):
            QMessageBox.warning(self, "恢复失败", "任务结果文件无效或无法读取")

    def open_output(self):
        report = self.result.get("report") if self.result else ""
        path = Path(report).parent if report else Path(self.source).parent
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.resolve())))

    def apply_filter(self, *_):
        self.proxy.status = self.status.currentText()
        self.proxy.search = self.search.text().strip().casefold()
        self.proxy.invalidateFilter()

    def update_summary(self):
        counts = Counter(row.status for row in self.model.rows)
        self.summary_label.setText(f"共{len(self.model.rows)}行 / {len({row.voucher for row in self.model.rows if row.voucher})}单；" + "；".join(f"{name} {count}" for name, count in sorted(counts.items())))

    def closeEvent(self, event):
        self.clear_undo()
        if self.worker is not None:
            self.closing = True
            self.request_stop()
            event.ignore()
        else:
            event.accept()


def main():
    application = QApplication(sys.argv)
    application.setApplicationName("TplusSalesImport")
    window = ImportWindow()
    window.show()
    return application.exec_()
