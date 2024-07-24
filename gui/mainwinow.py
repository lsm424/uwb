import sys
from PySide6.QtWidgets import QApplication, QTabWidget, QWidget, QVBoxLayout, QLabel, QMainWindow
from gui.config_Widget import ConfigWidget

from gui.sensor300d import Sensor300dWidget
from gui.tof2011 import Tof2011Widget
from gui.poa3012 import Poa3012Widget
from gui.pdoa_correct import PdoaCorrection
from gui.pdoa_raw import PdoaRawWidget
from gui.pdoa_angle import PdoaAngleWidget


class MainWindow(QMainWindow):
    def __init__(self, uwb):
        super().__init__()
        self.setWindowTitle("uwb")

        # 创建一个 QTabWidget 对象
        self.tab_widget = QTabWidget(self)

        # 添加标签页到 QTabWidget
        self.tab_widget.addTab(Tof2011Widget(), "测距值显示")
        self.tab_widget.addTab(Poa3012Widget(), "载波相位显示")
        self.tab_widget.addTab(Sensor300dWidget(), "传感器读数显示")
        self.tab_widget.addTab(ConfigWidget(uwb), "配置管理")
        self.tab_widget.addTab(PdoaCorrection(), "pdoa校准")
        self.tab_widget.addTab(PdoaRawWidget(), "pdoa原始数据")
        self.tab_widget.addTab(PdoaAngleWidget(), "pdoa角度数据")
        # 设置中心部件为 QTabWidget
        self.setCentralWidget(self.tab_widget)
        self.resize(1400, 600)
