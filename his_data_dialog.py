from PyQt5.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QTableWidget,
                             QTableWidgetItem, QHeaderView, QDateEdit, QCheckBox, QWidget, QMessageBox)
from PyQt5.QtCore import Qt, QDate, QDateTime, pyqtSignal
import sys
from decimal import Decimal

from log_util import logger
from sqlserver_db_connect import sqlserver_start_import

class PaymentRecordDialog(QDialog):
    # 导入完成信号
    import_finish_signal = pyqtSignal(str)
    def __init__(self, start_str, end_str, type, shoukuan_df, total_df, config_manager, full_path, shouyin_list, zz_code, parent=None):
        super().__init__(parent)
        self.setWindowTitle("缴款记录列表")
        self.resize(1000, 600)
        self.start_str = start_str
        self.end_str = end_str
        self.type = type
        self.shoukuan_df = shoukuan_df
        self.total_df = total_df
        self.config_manager = config_manager
        self.full_path = full_path
        self.shouyin_list = shouyin_list
        self.zz_code = zz_code
        self.record = {}
        self.setup_ui()
        self.init_data()

    def init_data(self):
        if self.type == 0:
            # 门诊数据展示
            self.build_men_zhen_data()
        elif self.type == 1:
            # 住院结算
            self.build_zhuyuan_js_data()
        elif self.type == 2:
            # 住院费用
            self.build_zhuyuan_fy_data()
        elif self.type == 3:
            # 门诊自助机
            self.build_menzhen_zizhuji_data()
        elif self.type == 4:
            # 门诊扫码
            self.build_menzhen_saoma_data()


    def setup_ui(self):
        layout = QVBoxLayout(self)

        # --- 1. 顶部筛选栏 (日期范围) ---
        filter_layout = QHBoxLayout()
        self.start_date = QDateEdit(QDateTime.fromString(self.start_str, "yyyy-MM-dd HH:mm:ss").date())
        self.start_date.setCalendarPopup(True)
        self.start_date.setEnabled(False)
        self.end_date = QDateEdit(QDateTime.fromString(self.end_str, "yyyy-MM-dd HH:mm:ss").date())
        self.end_date.setCalendarPopup(True)
        self.end_date.setEnabled(False)

        filter_layout.addWidget(QLabel("扎帐日期:"))
        filter_layout.addWidget(self.start_date)
        filter_layout.addWidget(QLabel(" 至 "))
        filter_layout.addWidget(self.end_date)
        filter_layout.addStretch()  # 弹簧，将控件推向左侧

        layout.addLayout(filter_layout)

        # --- 2. 全选控制栏 ---
        if self.type < 2:
            select_layout = QHBoxLayout()
            self.cb_all = QCheckBox("全选")
            select_layout.addWidget(self.cb_all)
            layout.addLayout(select_layout)
            # 绑定全选复选框的信号
            self.cb_all.stateChanged.connect(self.on_all_checked)

        # --- 3. 表格区域 ---
        self.table = QTableWidget()
        # 样式调整
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)  # 自动拉伸
        self.table.setAlternatingRowColors(True)  # 隔行变色
        self.table.setSelectionBehavior(QTableWidget.SelectRows)  # 按行选中

        layout.addWidget(self.table)

        # --- 4. 底部按钮 ---
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_cancel = QPushButton("关闭")
        self.btn_cancel.setFixedWidth(100)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_confirm = QPushButton("导入")
        self.btn_confirm.setFixedWidth(100)
        self.btn_confirm.clicked.connect(self.on_confirm_click)  # 点击确定关闭窗口
        btn_layout.addWidget(self.btn_confirm)

        layout.addLayout(btn_layout)

        # 修改表格列：增加一列用于放复选框
        if self.type == 0:
            headers = ["", "NO", "收款员", "扎帐时间", "门诊收费合计"]
        if self.type == 1:
            headers = ["", "NO", "收款员", "扎帐时间", "住院结算合计"]
        if self.type == 2:
            # 住院收入
            headers = ["收入项目", "金额合计"]
        if self.type == 3:
            # 门诊自助机
            headers = ["收入项目", "金额合计"]
        if self.type == 4:
            headers = ["收入项目", "金额合计"]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        if self.type < 2:
            # 第一列（勾选列）宽度设固定
            self.table.setColumnWidth(0, 40)
            # 如果希望第一列不被 Stretch 影响，可以单独指定：
            self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)

    def on_all_checked(self, state):
        """全选/取消全选逻辑"""
        # state 为 2 表示选中 (Qt.Checked)，0 表示未选中 (Qt.Unchecked)
        is_checked = (state == Qt.Checked)

        for row in range(self.table.rowCount()):
            # 找到每一行第一列的那个复选框控件
            cell_widget = self.table.cellWidget(row, 0)
            if cell_widget:
                checkbox = cell_widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(is_checked)

    def add_row_with_checkbox(self, data_list):
        """向表格添加一行，并带上复选框"""
        row_idx = self.table.rowCount()
        self.table.insertRow(row_idx)

        if self.type < 2:
            # --- 1. 创建居中的复选框容器 ---
            cb_widget = QWidget()
            cb_layout = QHBoxLayout(cb_widget)
            checkbox = QCheckBox()
            checkbox.setStyleSheet("""
            QCheckBox::indicator {
                width: 15px;   /* 宽度从默认的约13px加大到25px */
                height: 15px;  /* 高度同步加大 */
            }
        """)
            cb_layout.addWidget(checkbox)
            cb_layout.setAlignment(Qt.AlignCenter)  # 居中对齐
            cb_layout.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(row_idx, 0, cb_widget)

        # --- 2. 填充其余数据列 ---
        # 注意：data_list 中的数据从第二列 (索引 1) 开始填充
        for col_idx, value in enumerate(data_list):
            # 确保单号没有 .0 尾缀
            clean_val = str(value).replace('.0', '')
            item = QTableWidgetItem(clean_val)
            item.setTextAlignment(Qt.AlignCenter)
            if self.type < 2:
                self.table.setItem(row_idx, col_idx + 1, item)
            else:
                self.table.setItem(row_idx, col_idx, item)

    def get_checked_nos(self):
        """获取所有勾选行的单号(NO)"""
        checked_nos = []
        for row in range(self.table.rowCount()):
            cell_widget = self.table.cellWidget(row, 0)
            if cell_widget:
                checkbox = cell_widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    # 获取第二列的单号文本
                    no_text = self.table.item(row, 1).text()
                    checked_nos.append(no_text)
        return checked_nos

    def get_checked_rows_data(self):
        checked_nos = []
        for row in range(self.table.rowCount()):
            # 获取第一列的容器
            cell_widget = self.table.cellWidget(row, 0)
            if cell_widget:
                # 在容器中寻找 QCheckBox
                checkbox = cell_widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    # 获取第二列的“NO”文本
                    no_item = self.table.item(row, 1)
                    if no_item:
                        checked_nos.append(no_item.text())
        return checked_nos

    def build_men_zhen_data(self):
        """构建门诊数据"""
        for i, (zz_code, group) in enumerate(self.shoukuan_df.groupby('扎账单号', sort=True)):
            if not group.empty:
                group['金额'] = group['金额'].apply(lambda x: Decimal(str(x)) if x is not None else Decimal('0.00'))
                jine = group['金额'].sum()
                shouyin = group['收款员'].iloc[0]
                zz_time = group['扎帐时间'].iloc[0]
                self.add_row_with_checkbox([zz_code, shouyin, zz_time, str(jine)])

    def build_zhuyuan_js_data(self):
        """构建住院结算数据"""
        for i, (zz_code, group) in enumerate(self.shoukuan_df.groupby('扎账单号', sort=True)):
            if not group.empty:
                group['金额'] = group['金额'].apply(lambda x: Decimal(str(x)) if x is not None else Decimal('0.00'))
                jine = group['金额'].sum()
                shouyin = group['收款员'].iloc[0]
                zz_time = group['扎帐时间'].iloc[0]
                self.add_row_with_checkbox([zz_code, shouyin, zz_time, str(jine)])

    def build_zhuyuan_fy_data(self):
        """住院费用"""
        for i, (project, group) in enumerate(self.shoukuan_df.groupby('收入项目', sort=True)):
            if not group.empty:
                group['折扣后'] = group['折扣后'].apply(lambda x: Decimal(str(x)) if x is not None else Decimal('0.00'))
                jine = group['折扣后'].sum()
                self.add_row_with_checkbox([project, str(jine)])

    def build_menzhen_zizhuji_data(self):
        """门诊自助机"""
        for i, (project, group) in enumerate(self.shoukuan_df.groupby('项目', sort=True)):
            if not group.empty:
                group['金额'] = group['金额'].apply(lambda x: Decimal(str(x)) if x is not None else Decimal('0.00'))
                jine = group['金额'].sum()
                self.add_row_with_checkbox([project if project else "住院预交", str(jine)])

    def build_menzhen_saoma_data(self):
        """门诊扫码 """
        for i, (project, group) in enumerate(self.shoukuan_df.groupby('项目', sort=True)):
            if not group.empty:
                group['金额'] = group['金额'].apply(lambda x: Decimal(str(x)) if x is not None else Decimal('0.00'))
                jine = group['金额'].sum()
                self.add_row_with_checkbox([project if project else "住院预交", str(jine)])

    def on_confirm_click(self):
        if self.get_checked_rows_data() or self.type > 1:
            self._start_import_data_to_yy()
            logger.info(f"点击了导入按钮")
        else:
            QMessageBox.warning(self, "提示", "请选择要导入的数据")


    def _start_import_data_to_yy(self):
        """
        公共用友导入方法
        """
        logger.info(f"开始用友导入: {self.start_str}, {self.end_str}, {self.type}")
        if self.type < 2:
            checked_nos = self.get_checked_rows_data()
            self.shoukuan_df['扎账单号'] = self.shoukuan_df['扎账单号'].astype(str).str.replace('.0', '', regex=False).str.strip()
            self.total_df['扎账单号'] = self.total_df['扎账单号'].astype(str).str.replace('.0', '', regex=False).str.strip()
            checked_nos = [str(x).replace('.0', '').strip() for x in checked_nos]
            self.shoukuan_df = self.shoukuan_df[self.shoukuan_df['扎账单号'].isin(checked_nos)]
            self.total_df = self.total_df[self.total_df['扎账单号'].isin(checked_nos)]
        def on_complete(success, message, record):
            # 更新本地数据库状态
            if success:
                logger.info("导入成功，刷新列表")
                QMessageBox.information(self, "成功", "导入数据成功")
                self.accept()
            else:
                logger.info("导入失败，刷新列表")
                QMessageBox.critical(self, "失败", f"导入失败{message}")
        self.record = {
            "start_time": self.start_str,
            "end_time": self.end_str,
            "data_type": str(self.type),
            "export_file_path": self.full_path,
            "zz_code": self.zz_code,
            "shouyin_list": ",".join(self.shouyin_list),
        }
        sqlserver_start_import(self, self.config_manager.get_db_config('sqlserver'), self.shoukuan_df, self.total_df, self.record, self.type, on_complete)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 这里假设你已经贴入了之前完整的 PaymentRecordDialog 类
    main_win = PaymentRecordDialog()

    main_win.show()
    sys.exit(app.exec_())


