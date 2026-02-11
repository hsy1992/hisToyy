from PyQt5.QtWidgets import QTableView, QHeaderView, QAbstractItemView, QPushButton, QHBoxLayout, QAction, QMenu
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import Qt, pyqtSignal
from py_sqlite import SQLiteHelper
from log_util import logger
from path_util import open_with_default_app
from yongyou_coe import data_type

class SqlInfiniteTableWidget(QTableView):
    """
    通用数据库滑动加载表格组件
    """
    # 定义一个信号，当用户点击某行时，向外传递该行的数据字典
    rowClickedData = pyqtSignal(dict)

    def __init__(self, main_view, parent=None):
        super().__init__(parent)

        self.limit = 10  # 每次加载数量
        self.offset = 0  # 当前偏移
        self.is_loading = False
        # 是否有更多
        self.has_more_data = True

        self._init_db()
        self._init_ui()
        self.load_more_data()
        self.main_view = main_view

    def _init_db(self):
        # 建立数据库连接（使用唯一连接名防止冲突）
        self.db = SQLiteHelper()

        # 状态定义映射
        self.STATUS_MAP = {
            1: "初始状态",
            2: "导出成功",
            3: "导出失败",
            4: "用友导入成功",
            5: "用友导入失败"
        }

    def _init_ui(self):
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(("数据类型", "扎帐时间范围", "收银员", "扎账单号", "用友凭证号", "导入数量", "状态", "操作时间"))
        self.setModel(self.model)
        self.list_data = []

        # 样式设置
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.setWordWrap(True)
        # 必须设置此策略，否则右键不会触发信号
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        # 绑定滚动条
        self.verticalScrollBar().valueChanged.connect(self._handle_scroll)
        # 绑定点击事件
        self.clicked.connect(self._on_item_clicked)

    def _handle_scroll(self, value):
        if value > self.verticalScrollBar().maximum() * 0.9:
            if not self.is_loading:
                self.load_more_data()

    def load_more_data(self):
        if not self.has_more_data:
            return
        self.is_loading = True

        sql = f"SELECT * FROM sys_export_record  ORDER BY id DESC LIMIT {self.limit} OFFSET {self.offset}"

        connection = self.db.get_connection()
        try:
            cursor = connection.cursor()
            cursor.execute(sql)
            list = [dict(row) for row in cursor.fetchall()]
            logger.info(f"sql：{sql}，list：{len(list)}")
            if len(list) >= self.limit:
                self.offset += self.limit
            self.list_data.extend(list)
            # 直接通过字段名取值
            for item in list:
                row_items = [QStandardItem(data_type.get(item['data_type'], "")), QStandardItem(f"{item['start_time']}~\n{item['end_time']}"), QStandardItem(f"{item['shouyin_list'] if item['shouyin_list'] else '全部'}"),
                             QStandardItem(f"{item['zz_code'] if item['zz_code'] else '全部'}"), QStandardItem(item['import_yy_start']), QStandardItem(str(item['import_yy_num'])),
                             QStandardItem(self.STATUS_MAP[item['status']]), QStandardItem(item['create_time'])]
                self.model.appendRow(row_items)
            self.has_more_data = len(list) >= self.limit
        except Exception as e:
            print(e)
            logger.info(f"SQLite 查询错误: {e}")
            self.has_more_data = False
        self.is_loading = False


    def _on_item_clicked(self, index):
        # 获取当前点击行的数据并转为字典发出去
        row_data = {}
        self.model.item(index.row())
        print(self.model.item(index.row()))
        # for i, field in enumerate(self.fields):
        #     row_data[field] = self.model.item(index.row(), i).text()
        self.rowClickedData.emit(row_data)

    def refresh_data(self):
        """重新加载数据"""
        self.model.removeRows(0, self.model.rowCount())
        self.has_more_data = True
        self.offset = 0
        self.list_data.clear()
        self.load_more_data()

    def show_context_menu(self, pos):
        # 获取点击位置对应的模型索引
        index = self.indexAt(pos)
        if not index.isValid():
            return

        row = index.row()
        item = self.list_data[row]
        # 1. 创建菜单对象
        menu = QMenu(self)
        # 2. 定义各种动作
        action_open = QAction("打开文件", self)
        action_retry = QAction("导入用友", self)

        menu.addAction(action_open)
        menu.addSeparator()  # 分割线
        menu.addAction(action_retry)

        # 4. 展示菜单并捕捉点击的动作
        # mapToGlobal 是将相对于表格的坐标转为相对于屏幕的坐标
        action = menu.exec_(self.mapToGlobal(pos))

        # 5. 处理点击事件
        if action == action_open:
            open_with_default_app(item['export_file_path'])
        elif action == action_retry:
            self.main_view.start_yy_import(item)
