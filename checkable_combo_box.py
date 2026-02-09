from PyQt5.QtWidgets import QComboBox, QStyledItemDelegate
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QStandardItemModel, QStandardItem


class CheckableComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        # 1. 设置可编辑，这样我们才能控制显示的文字内容
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)  # 设为只读，不允许用户手动输入
        # 允许通过点击选项来勾选，而不关闭下拉菜单
        self.view().viewport().installEventFilter(self)
        self.model = QStandardItemModel()
        self.setModel(self.model)
        self._is_all_selected = True  # 记录全选状态
        # 4. 监听模型数据变化，实时更新显示的文字
        self.model.dataChanged.connect(self.update_display_text)

    def add_all_option(self):
        """在列表顶部添加全选选项"""
        item = QStandardItem("--- 全选 / 取消全选 ---")
        item.setCheckState(Qt.Unchecked)
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
        # 我们用 UserRole 来标记这是一个特殊的“全选”项
        item.setData("ALL_OPTION", Qt.UserRole)
        self.model.appendRow(item)

    def addItem(self, list, data=None):
        for text in list:
            item = QStandardItem(text)
            item.setData(data if data else text, Qt.UserRole)
            item.setCheckState(Qt.Unchecked)  # 初始为未选中
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            self.model.appendRow(item)

    def eventFilter(self, widget, event):
        if widget == self.view().viewport() and event.type() == QEvent.MouseButtonRelease:
            index = self.view().indexAt(event.pos())
            item = self.model.itemFromIndex(index)

            # 处理全选逻辑
            if item.data(Qt.UserRole) == "ALL_OPTION":
                new_state = Qt.Unchecked if item.checkState() == Qt.Checked else Qt.Checked
                for i in range(self.model.rowCount()):
                    self.model.item(i).setCheckState(new_state)
            else:
                # 切换当前项状态
                new_state = Qt.Unchecked if item.checkState() == Qt.Checked else Qt.Checked
                item.setCheckState(new_state)
            return True
        return super().eventFilter(widget, event)

    def checked_items(self):
        """获取已选内容（排除全选选项本身）"""
        checked = []
        for i in range(self.model.rowCount()):
            item = self.model.item(i)
            if item.checkState() == Qt.Checked and item.data(Qt.UserRole) != "ALL_OPTION":
                checked.append(item.text())
        return checked

    def update_display_text(self):
        """核心回显逻辑：根据选中项更新文本框内容"""
        checked_items = self.checked_items()

        if not checked_items:
            self.setEditText("--- 请选择 ---")
        elif len(checked_items) == (self.model.rowCount() - (1 if self.has_all_option() else 0)):
            self.setEditText("已选择全部项")
        else:
            # 拼接已选中的文本，用逗号隔开
            text = ",".join(checked_items)
            self.setEditText(text)

    def has_all_option(self):
        return self.model.item(0).data(Qt.UserRole) == "ALL_OPTION" if self.model.rowCount() > 0 else False

# --- 使用示例 ---
# combo = CheckableComboBox()
# combo.addItem("耳鼻喉科")
# combo.addItem("眼科")
# combo.addItem("内科")
# print(combo.checked_items())