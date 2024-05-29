import threading
import time
import queue
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QLineEdit
import pyqtgraph as pg
import math
import numpy as np

from common.common import logger
from uwb.tof_2011 import Tof2011
from uwb.sensor_300d import Sensor300d


class Sensor300dWidght(QWidget):

    def __init__(self):
        super().__init__()

        self.main_layout = QVBoxLayout(self)
        up_layout = QHBoxLayout()

        pres_layout = QHBoxLayout()
        pres_layout.addWidget(QLabel('气压：'))
        self.pres_lineedit = QLineEdit()
        self.pres_lineedit.setReadOnly(True)
        pres_layout.addWidget(self.pres_lineedit)
        up_layout.addLayout(pres_layout)

        temp_layout = QHBoxLayout()
        temp_layout.addWidget(QLabel('温度：'))
        self.temp_lineedit = QLineEdit()
        self.temp_lineedit.setReadOnly(True)
        temp_layout.addWidget(self.temp_lineedit)
        up_layout.addLayout(temp_layout)

        batt_layout = QHBoxLayout()
        batt_layout.addWidget(QLabel('电量：'))
        self.batt_lineedit = QLineEdit()
        self.batt_lineedit.setReadOnly(True)
        batt_layout.addWidget(self.batt_lineedit)
        up_layout.addLayout(batt_layout)
        self.main_layout.addLayout(up_layout)

        down_layout = QHBoxLayout()
        self.x_polling = []
        self.pw1 = pg.PlotWidget(self)  # 图1
        self.pw1.setMouseEnabled(x=False, y=False)  # 失能x,y轴控制
        self.pw1.showGrid(x=True, y=True)  # 显示网格
        self.pw1.setLabel('left', "acc")  # 设置Y轴标签
        self.pw1.setLabel('bottom', "polling")  # 设置X轴标签
        self.acc_x, self.acc_y, self.acc_z = [], [], []
        self.plot_acc_x = self.pw1.plot(self.x_polling, self.acc_x, pen=pg.mkPen(color=(0, 0, 100), width=3),
                                      symbol='s', symbolBrush='r', name='acc_x')
        self.plot_acc_y = self.pw1.plot(self.x_polling, self.acc_y, pen=pg.mkPen(color=(0, 0, 100), width=3),
                                      symbol='s', symbolBrush='g', name='acc_y')
        self.plot_acc_z = self.pw1.plot(self.x_polling, self.acc_z, pen=pg.mkPen(color=(0, 0, 100), width=3),
                                      symbol='s', symbolBrush='b', name='acc_z')
        down_layout.addWidget(self.pw1)
        # 创建一个图例
        legend = pg.LegendItem(offset=(60, 20))
        legend.setParentItem(self.pw1.graphicsItem())
        legend.setAutoFillBackground(True)
        # 将图例项添加到图例中
        for item in self.pw1.items():
            if isinstance(item, pg.PlotDataItem):
                name = item.opts['name']
                # color = item.opts['pen'].color().name()
                legend.addItem(item, name=name)

        self.pw2 = pg.PlotWidget(self)  # 图2
        self.pw2.setMouseEnabled(x=False, y=False)  # 失能x,y轴控制
        self.pw2.showGrid(x=True, y=True)  # 显示网格
        self.pw2.setLabel('left', "gyr")  # 设置Y轴标签
        self.pw2.setLabel('bottom', "polling")  # 设置X轴标签
        self.gyr_x, self.gyr_y, self.gyr_z = [], [], []
        self.plot_gyr_x = self.pw2.plot(self.x_polling, self.gyr_x, pen=pg.mkPen(color=(0, 0, 100), width=3),
                                      symbol='s', symbolBrush='r', name='gyr_x')
        self.plot_gyr_y = self.pw2.plot(self.x_polling, self.gyr_y, pen=pg.mkPen(color=(0, 0, 100), width=3),
                                      symbol='s', symbolBrush='g', name='gyr_y')
        self.plot_gyr_z = self.pw2.plot(self.x_polling, self.gyr_z, pen=pg.mkPen(color=(0, 0, 100), width=3),
                                      symbol='s', symbolBrush='b', name='gyr_z')
        down_layout.addWidget(self.pw2)
        legend = pg.LegendItem(offset=(60, 20))
        legend.setParentItem(self.pw2.graphicsItem())
        legend.setAutoFillBackground(True)
        # 将图例项添加到图例中
        for item in self.pw2.items():
            if isinstance(item, pg.PlotDataItem):
                name = item.opts['name']
                # color = item.opts['pen'].color().name()
                legend.addItem(item, name=name)

        self.pw3 = pg.PlotWidget(self)  # 图2
        self.pw3.setMouseEnabled(x=False, y=False)  # 失能x,y轴控制
        self.pw3.showGrid(x=True, y=True)  # 显示网格
        self.pw3.setLabel('left', "mag")  # 设置Y轴标签
        self.pw3.setLabel('bottom', "polling")  # 设置X轴标签
        self.mag_x, self.mag_y, self.mag_z = [], [], []
        self.plot_mag_x = self.pw3.plot(self.x_polling, self.mag_x, pen=pg.mkPen(color=(0, 0, 100), width=3),
                                        symbol='s', symbolBrush='r', name='mag_x')
        self.plot_mag_y = self.pw3.plot(self.x_polling, self.mag_y, pen=pg.mkPen(color=(0, 0, 100), width=3),
                                        symbol='s', symbolBrush='g', name='mag_y')
        self.plot_mag_z = self.pw3.plot(self.x_polling, self.mag_z, pen=pg.mkPen(color=(0, 0, 100), width=3),
                                        symbol='s', symbolBrush='b', name='mag_z')
        down_layout.addWidget(self.pw3)
        legend = pg.LegendItem(offset=(60, 20))
        legend.setParentItem(self.pw3.graphicsItem())
        legend.setAutoFillBackground(True)
        # 将图例项添加到图例中
        for item in self.pw3.items():
            if isinstance(item, pg.PlotDataItem):
                name = item.opts['name']
                # color = item.opts['pen'].color().name()
                legend.addItem(item, name=name)

        self.main_layout.addLayout(down_layout)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.timeout_plot)
        self.timer.start(100)

    def timeout_plot(self):
        a = time.time()
        gui_data = sorted(Sensor300d.gui_data, key=lambda x: x[0])
        if not gui_data:
            return
        gui_data_zip = list(zip(*gui_data))

        # 温度压力电量显示
        self.temp_lineedit.setText(str(gui_data_zip[5][-1]))
        self.pres_lineedit.setText(str(gui_data_zip[4][-1]))
        self.batt_lineedit.setText(str(gui_data_zip[3][-1]))

        self.x_polling, _, _ ,_ , _, _, self.acc_x, self.acc_y, self.acc_z, self.gyr_x, self.gyr_y, self.gyr_z, self.mag_x, self.mag_y, self.mag_z = gui_data_zip

        self.plot_acc_x.setData(self.x_polling, self.acc_x)
        self.plot_acc_y.setData(self.x_polling, self.acc_y)
        self.plot_acc_z.setData(self.x_polling, self.acc_z)
        self.plot_gyr_x.setData(self.x_polling, self.gyr_x)
        self.plot_gyr_y.setData(self.x_polling, self.gyr_y)
        self.plot_gyr_z.setData(self.x_polling, self.gyr_z)
        self.plot_mag_x.setData(self.x_polling, self.mag_x)
        self.plot_mag_y.setData(self.x_polling, self.mag_y)
        self.plot_mag_z.setData(self.x_polling, self.mag_z)
        # logger.info(f'{time.time() - a} ')
        # if (len(self.x_polling) > self.xRange):
        #     self.pw1.setXRange(len(self.x_polling) - self.xRange, len(self.x_polling))  # 固定x坐标轴宽度
        #     self.pw2.setXRange(len(self.x_polling) - self.xRange, len(self.x_polling))  # 固定x坐标轴宽度

        # 结束时使能鼠标控制
        # self.pw1.setMouseEnabled(x=True, y=False)  # 使能x轴控制，失能y轴控制
        # self.pw2.setMouseEnabled(x=True, y=False)  # 使能x轴控制，失能y轴控制
