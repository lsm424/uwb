import sys

from PySide6.QtWidgets import QComboBox, QLineEdit, QApplication
from PySide6.QtCore import Qt, Signal, QThread


# 定义一个 QThread 子类
class WorkerThread(QThread):
    def __init__(self, pdoa_raw):
        super().__init__()
        self.pdoa_raw = pdoa_raw

    def run(self):
        self.pdoa_raw.run()


class CheckableComboBox(QComboBox):
    select_signal = Signal(list[str])

    def __init__(self, parent=None):
        super(CheckableComboBox, self).__init__(parent)
        # QToolTip.setFont(QFont('Times New Roman', 15))  # 设置提示框字体和字号
        self.setLineEdit(QLineEdit())
        self.lineEdit().setReadOnly(True)
        self.view = self.view()
        self.view.clicked.connect(self.selectItemAction)
        # self.addCheckableItem('全选')
        # self.SelectAllStatus = 1

    def addCheckableItem(self, text):
        super().addItem(text)
        item = self.model().item(self.count() - 1, 0)
        item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
        item.setCheckState(Qt.CheckState.Unchecked)
        item.setToolTip(text)

    def addCheckableItems(self, texts):
        for text in texts:
            self.addCheckableItem(str(text))

    def ifChecked(self, index):
        item = self.model().item(index, 0)
        if not item:
            return False
        return item.checkState() == Qt.CheckState.Checked

    def checkedItems(self):
        return [self.itemText(i) for i in range(self.count()) if self.ifChecked(i)]

    def checkedItemsStr(self):
        # items = self.checkedItems()
        # self.select_signal.emit(items)
        return ';'.join(self.checkedItems()).strip('全选').strip(';')

    def showPopup(self):
        self.view.setMinimumWidth(3 * self.width() // 2)  # 下拉列表宽度加大
        self.view.setMaximumHeight(200)  # 最大高度为200
        super().showPopup()

    def selectItemAction(self, index):
        # if index.row() == 0:
        #     for i in range(self.model().rowCount()):
        #         if self.SelectAllStatus:
        #             self.model().item(i).setCheckState(Qt.CheckState.Checked)
        #         else:
        #             self.model().item(i).setCheckState(Qt.CheckState.Unchecked)
        #     self.SelectAllStatus = (self.SelectAllStatus + 1) % 2
        #
        self.lineEdit().clear()
        self.lineEdit().setText(self.checkedItemsStr())

    def clear(self) -> None:
        super().clear()
        # self.addCheckableItem('全选')

    def select_all(self):
        for i in range(self.model().rowCount()):
            self.model().item(i).setCheckState(Qt.CheckState.Checked)
        self.lineEdit().setText(self.checkedItemsStr())

    def select_items(self, items):
        items = list(map(lambda x: str(x), items))
        for i in range(self.model().rowCount()):
            text = self.model().item(i).text()
            if text not in items:
                continue
            self.model().item(i).setCheckState(Qt.CheckState.Checked)
        self.lineEdit().setText(self.checkedItemsStr())


if __name__ == '__main__':
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    mainWindow = CheckableComboBox()
    mainWindow.addCheckableItems(['1', '2', '3'])
    mainWindow.select_items(['2', '1'])
    mainWindow.show()
    sys.exit(app.exec())
