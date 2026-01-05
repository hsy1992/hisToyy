# 自定义弹窗
import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLineEdit, QLabel, QDialog, QFormLayout, QGroupBox, QMessageBox)
from config import ConfigManager

# 1. 自定义弹窗类
class ConfigDialog(QDialog):
    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setWindowTitle("系统配置")
        # 适当调大尺寸以容纳更多输入框
        self.resize(400, 500)

        main_layout = QVBoxLayout()

        # --- 1. HIS 配置分组 ---
        self.his_group = QGroupBox("HIS Orcale 配置")
        his_layout = QFormLayout()
        self.his_server = QLineEdit()
        self.his_port = QLineEdit()
        self.his_server_name = QLineEdit()
        self.his_user = QLineEdit()
        self.his_pwd = QLineEdit()

        # 初始化赋值
        his_oracle = config_manager.get_db_config("oracle")
        self.his_server.setText(his_oracle.get("ip"))
        self.his_port.setText(his_oracle.get("port"))
        self.his_server_name.setText(his_oracle.get("service_name"))
        self.his_user.setText(his_oracle.get("user"))
        self.his_pwd.setText(his_oracle.get("password"))

        his_layout.addRow("服务器 (IP):", self.his_server)
        his_layout.addRow("端口:", self.his_port)
        his_layout.addRow("ServiceName:", self.his_server_name)
        his_layout.addRow("用户名 (User):", self.his_user)
        his_layout.addRow("密码 (Password):", self.his_pwd)
        self.his_group.setLayout(his_layout)

        # --- 2. 数据库配置分组 ---
        self.sql_group = QGroupBox("用友SQL Server 配置")
        sql_layout = QFormLayout()
        self.sql_server = QLineEdit()
        self.sql_port = QLineEdit()
        self.sql_db = QLineEdit()
        self.sql_user = QLineEdit()
        self.sql_pwd = QLineEdit()

        # 初始化赋值
        yy_sqlserver = config_manager.get_db_config("sqlserver")
        self.sql_server.setText(yy_sqlserver.get("ip"))
        self.sql_port.setText(yy_sqlserver.get("port"))
        self.sql_db.setText(yy_sqlserver.get("database"))
        self.sql_user.setText(yy_sqlserver.get("user"))
        self.sql_pwd.setText(yy_sqlserver.get("password"))

        sql_layout.addRow("服务器 (IP):", self.sql_server)
        sql_layout.addRow("端口:", self.sql_port)
        sql_layout.addRow("数据库 (Database):", self.sql_db)
        sql_layout.addRow("用户名 (User):", self.sql_user)
        sql_layout.addRow("密码 (Password):", self.sql_pwd)
        self.sql_group.setLayout(sql_layout)

        # --- 3. 底部按钮 ---
        btn_layout = QHBoxLayout()
        self.btn_confirm = QPushButton("保存配置")
        self.btn_confirm.setFixedHeight(40)
        self.btn_confirm.clicked.connect(self.handle_save)
        btn_layout.addStretch()  # 将按钮推向右侧
        btn_layout.addWidget(self.btn_confirm)

        # 将各部分添加到主布局
        main_layout.addWidget(self.his_group)
        main_layout.addWidget(self.sql_group)
        main_layout.addLayout(btn_layout)
        self.setLayout(main_layout)

        # 设置默认提示文字 (Placeholder)
        self.his_server.setPlaceholderText("例如: 192.168.1.100")
        self.sql_server.setPlaceholderText("例如: 192.168.1.100")

    def get_all_configs(self):
        """返回两个字典，包含所有输入的数据"""
        his_data = {
            "ip": self.his_server.text(),
            "port": self.his_port.text(),
            "serverName": self.his_server_name.text(),
            "username": self.his_user.text(),
            "password": self.his_pwd.text()
        }
        sql_data = {
            "ip": self.sql_server.text(),
            "port": self.sql_port.text(),
            "database": self.sql_db.text(),
            "username": self.sql_user.text(),
            "password": self.sql_pwd.text()
        }
        return his_data, sql_data

    def handle_save(self):
        """点击保存时，调用 ConfigManager 的写入方法"""
        if (
                not self.his_server.text().strip() or not self.his_port.text().strip() or
                not self.his_server_name.text().strip() or not self.his_user.text().strip() or not self.his_pwd.text().strip()
        ):
            QMessageBox.warning(self, "错误", "请完整填写所有必填信息！")
            return  # 拦截，不执行保存

        if not self.sql_server.text().strip() or not self.sql_port.text().strip() or\
                not self.sql_db.text().strip() or not self.sql_user.text().strip() or not self.sql_pwd.text().strip():
            QMessageBox.warning(self, "错误", "请完整填写所有必填信息！")
            return  # 拦截，不执行保存

        try:
            # 调用封装好的写入功能
            self.config_manager.update_config("oracle", ip=self.his_server.text().strip(),
                                              port=self.his_port.text().strip(),
                                              service_name=self.his_server_name.text().strip(),
                                              user=self.his_user.text().strip(),
                                              password=self.his_pwd.text().strip())

            self.config_manager.update_config("sqlserver", ip=self.sql_server.text().strip(),
                                              port=self.sql_port.text().strip(),
                                              database=self.sql_db.text().strip(), user=self.sql_user.text().strip(),
                                              password=self.sql_pwd.text().strip())
            QMessageBox.information(self, "成功", "配置已更新到文件！")
            self.accept()  # 关闭弹窗
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {e}")


    def show_message(self, title, content):
        # QMessageBox.warning (警告图标) / .critical (错误图标) / .information (信息图标)
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle(title)
        msg_box.setText(content)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()
