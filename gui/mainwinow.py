import sys
from PySide6.QtWidgets import QApplication, QTabWidget, QWidget, QVBoxLayout, QLabel, QMainWindow

from gui.sensor300d import Sensor300dWidght
from gui.tof2011 import Tof2011Widght


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("uwb")

        # 创建一个 QTabWidget 对象
        self.tab_widget = QTabWidget(self)

        # 添加标签页到 QTabWidget
        self.tab_widget.addTab(Tof2011Widght(), "测距值显示")
        self.tab_widget.addTab(Sensor300dWidght(), "传感器读数显示")

        # 设置中心部件为 QTabWidget
        self.setCentralWidget(self.tab_widget)
        self.resize(1400, 600)


