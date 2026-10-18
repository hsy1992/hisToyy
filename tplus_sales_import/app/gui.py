import sys
import threading
import time
from log_util import logger, diagnostics
from collections import Counter
from pathlib import Path

from PyQt5.QtCore import (QAbstractTableModel, QModelIndex, QSortFilterProxyModel, QThread,
                          Qt, QUrl, pyqtSignal)
from PyQt5.QtGui import QDesktopServices, QCursor
from PyQt5.QtWidgets import (QApplication, QComboBox, QFileDialog, QHBoxLayout, QGridLayout, QLabel,
                            QLineEdit, QMainWindow, QMessageBox, QProgressBar, QPushButton,
                            QScrollArea, QTableView, QVBoxLayout, QWidget)

from .configuration import DatabaseConfig, application_dir
from .database import PreflightError, SqlRepository
from .engine import ImportEngine
from .files import TaskJournal, export_report, read_xls


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

    def __init__(self, action, config=None, source=None, rows=None, columns=None, runtime=None, report_args=None):
        super().__init__()
        self.action, self.config, self.source = action, config, source
        self.rows, self.columns, self.runtime = rows, columns, runtime
        self.stop = threading.Event()
        self.report_args = report_args

    def run(self):
        started = time.perf_counter()
        logger.info("后台操作开始 action=%s file=%s", self.action, self.source or "-")
        try:
            if self.action == "load":
                result = read_xls(self.source, self.stop, self.progress.emit)
            elif self.action == "test":
                repository = SqlRepository(self.config)
                try:
                    result = repository.open()
                finally:
                    repository.close()
            elif self.action == "export":
                result = str(export_report(**self.report_args))
            else:
                engine = ImportEngine(self.config, self.source, self.rows, self.columns,
                                      self.runtime, self.stop, self.progress.emit)
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
        except (ValueError, PreflightError) as exc:
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
        self.worker, self.result = None, None
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
        config_path_label = QLabel("配置文件（请手动修改后重新测试）：" + str(self.config_path))
        config_path_label.setWordWrap(True)
        layout.addWidget(config_path_label)
        layout.addWidget(self.config_label)
        self.connection_label = QLabel("连接状态：未测试（可选）；导入时自动连接账套")
        layout.addWidget(self.connection_label)
        toolbar = QGridLayout()
        self.test_button = QPushButton("测试连接 / 重新读取配置")
        self.choose_button = QPushButton("选择XLS文件")
        self.import_button = QPushButton("导入全部数据")
        self.stop_button = QPushButton("停止")
        self.retry_button = QPushButton("重试导出")
        self.save_button = QPushButton("结果另存为")
        self.folder_button = QPushButton("打开输出目录")
        self.restore_button = QPushButton("恢复任务结果")
        for index, button in enumerate((self.test_button, self.choose_button, self.import_button, self.stop_button,
                                        self.retry_button, self.save_button, self.folder_button, self.restore_button)):
            toolbar.addWidget(button, index // 4, index % 4)
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
        self.status.addItems(["全部", "待处理", "待写入", "导入成功", "重复跳过", "校验失败", "整单受阻", "写入失败", "待确认", "未处理"])
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
        self.phase_label = QLabel("请选择XLS文件，加载后即可导入；测试连接为可选操作")
        self.phase_label.setWordWrap(True)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.phase_label)
        self.progress = QProgressBar()
        layout.addWidget(self.progress)
        self.test_button.clicked.connect(self.test_connection)
        self.choose_button.clicked.connect(self.choose_file)
        self.import_button.clicked.connect(self.start_import)
        self.stop_button.clicked.connect(self.request_stop)
        self.retry_button.clicked.connect(lambda: self.start_export(False))
        self.save_button.clicked.connect(lambda: self.start_export(True))
        self.folder_button.clicked.connect(self.open_output)
        self.restore_button.clicked.connect(self.restore_result)
        self.search.textChanged.connect(self.apply_filter)
        self.status.currentTextChanged.connect(self.apply_filter)
        self.reload_config()
        self.update_buttons()
        self.apply_initial_geometry()

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
            detail = str(exc) if isinstance(exc, ValueError) else "无法读取配置文件，请检查权限"
            self.config_label.setText("配置文件无效：" + detail)
            return False

    def update_buttons(self):
        busy = self.worker is not None
        self.test_button.setEnabled(not busy)
        self.choose_button.setEnabled(not busy)
        can_import = not busy and bool(self.model.rows)
        self.import_button.setEnabled(can_import)
        if busy:
            reason = "正在执行任务，请等待结束后再导入"
        elif not self.model.rows:
            reason = "请先选择并成功加载XLS文件"
        else:
            reason = f"可以导入：已加载{len(self.model.rows)}行；点击后自动读取配置、连接账套并校验"
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

    def on_progress(self, phase, done, total):
        self.phase_label.setText(phase)
        self.progress.setRange(0, max(total, 0))
        if total:
            self.progress.setValue(done)
        self.model.refresh()
        self.update_summary()

    def on_error(self, message):
        if self.worker is not None and self.worker.action == "test":
            self.tested = None
            self.connection_label.setText("连接状态：测试失败；可检查配置后重新测试或直接发起导入")
        self.phase_label.setText(message)
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        if not self.closing:
            QMessageBox.warning(self, "任务未完成", message)

    def test_connection(self):
        self.tested = None
        self.connection_label.setText("连接状态：正在测试（测试结果不影响文件加载后的导入按钮）")
        if not self.reload_config():
            self.connection_label.setText("连接状态：配置无效，请修改配置文件")
            self.update_buttons()
            return
        config = self.config
        def complete(actual):
            self.tested = config
            self.connection_label.setText("连接成功：" + actual + "（可选测试）")
            self.phase_label.setText("连接成功，实际目标账套：" + actual)
            self.progress.setRange(0, 1)
            self.progress.setValue(1)
        self.start_worker(TaskWorker("test", config=config), complete)

    def choose_file(self):
        source, _ = QFileDialog.getOpenFileName(self, "选择销货单源文件", str(application_dir()), "Excel 97-2003 (*.xls)")
        if not source:
            return
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
        try:
            current = DatabaseConfig.load(self.config_path)
        except (ValueError, OSError) as exc:
            self.tested = None
            self.reload_config()
            self.connection_label.setText("连接状态：配置无效，未开始导入")
            self.update_buttons()
            self.on_error(str(exc) if isinstance(exc, ValueError) else "无法读取配置文件，请检查权限")
            return
        if current != self.tested:
            self.tested = None
        self.config = current
        self.config_label.setText(current.display())
        self.connection_label.setText("连接状态：导入任务将自动连接 " + current.database)
        self.result = None
        self.start_worker(TaskWorker("import", config=current, source=self.source, rows=self.model.rows,
                                     columns=self.model.source_columns, runtime=self.runtime), self.import_complete)

    def import_complete(self, result):
        self.result = result
        self.phase_label.setText((result["message"] or "处理完成") +
                                 ("；结果：" + result["report"] if result["report"] else "；请重试导出或另存为"))

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
