import sys
from PySide6.QtWidgets import QApplication, QTabWidget, QWidget, QVBoxLayout, QLabel, QMainWindow
from gui.config_widght import ConfigWidght

from gui.sensor300d import Sensor300dWidght
from gui.tof2011 import Tof2011Widght
from gui.pdoa_correct import PdoaCorrecd
from gui.pdoa_raw import PdoaRawWidget


class MainWindow(QMainWindow):
    def __init__(self, uwb):
        super().__init__()
        self.setWindowTitle("uwb")

        # 创建一个 QTabWidget 对象
        self.tab_widget = QTabWidget(self)

        # 添加标签页到 QTabWidget
        self.tab_widget.addTab(Tof2011Widght(), "测距值显示")
        self.tab_widget.addTab(Sensor300dWidght(), "传感器读数显示")
        self.tab_widget.addTab(ConfigWidght(uwb), "配置管理")
        self.tab_widget.addTab(PdoaCorrecd(), "pdoa校准")
        self.tab_widget.addTab(PdoaRawWidget(), "pdoa原始数据")
        # 设置中心部件为 QTabWidget
        self.setCentralWidget(self.tab_widget)
        self.resize(1400, 600)
