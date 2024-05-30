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

        tagid_layout = QHBoxLayout()
        tagid_layout.addWidget(QLabel('tagid：'))
        self.tag_id_combox = QComboBox()
        self.tag_id_combox.currentIndexChanged.connect(self.tagid_selection_changed)
        self.cur_tag_id = None
        tagid_layout.addWidget(self.tag_id_combox)
        up_layout.addLayout(tagid_layout)
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
                                      symbol='s', symbolBrush='b', name='acc_x')
        self.plot_acc_y = self.pw1.plot(self.x_polling, self.acc_y, pen=pg.mkPen(color=(0, 100, 0), width=3),
                                      symbol='s', symbolBrush='g', name='acc_y')
        self.plot_acc_z = self.pw1.plot(self.x_polling, self.acc_z, pen=pg.mkPen(color=(100, 0, 0), width=3),
                                      symbol='s', symbolBrush='r', name='acc_z')
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
                                      symbol='s', symbolBrush='b', name='gyr_x')
        self.plot_gyr_y = self.pw2.plot(self.x_polling, self.gyr_y, pen=pg.mkPen(color=(0, 100, 0), width=3),
                                      symbol='s', symbolBrush='g', name='gyr_y')
        self.plot_gyr_z = self.pw2.plot(self.x_polling, self.gyr_z, pen=pg.mkPen(color=(100, 0, 0), width=3),
                                      symbol='s', symbolBrush='r', name='gyr_z')
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
                                        symbol='s', symbolBrush='b', name='mag_x')
        self.plot_mag_y = self.pw3.plot(self.x_polling, self.mag_y, pen=pg.mkPen(color=(0, 100, 0), width=3),
                                        symbol='s', symbolBrush='g', name='mag_y')
        self.plot_mag_z = self.pw3.plot(self.x_polling, self.mag_z, pen=pg.mkPen(color=(100, 0, 0), width=3),
                                        symbol='s', symbolBrush='r', name='mag_z')
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

        self.last_update_tagid_time = time.time()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.timeout_plot)
        self.timer.start(200)

    def tagid_selection_changed(self, index):
        self.cur_tag_id = int(self.tag_id_combox.currentText())

    def timeout_plot(self):
        a = time.time()
        min_x_polling = 0
        if self.x_polling:
            min_x_polling = self.x_polling[0]
            Sensor300d.gui_data = list(filter(lambda x: x[0] >= min_x_polling, Sensor300d.gui_data))
        # 根据tagid过滤，并且根据滚码排序
        gui_data = Sensor300d.gui_data if self.cur_tag_id is None else filter(lambda x: x[1] == self.cur_tag_id, Sensor300d.gui_data)
        gui_data = sorted(gui_data, key=lambda x: x[0])
        if not gui_data:
            return
        gui_data_zip = list(zip(*gui_data))

        if self.cur_tag_id is not None:
            # 温度压力电量显示
            self.temp_lineedit.setText(str(gui_data_zip[5][-1]))
            self.pres_lineedit.setText(str(gui_data_zip[4][-1]))
            self.batt_lineedit.setText(str(gui_data_zip[3][-1]))

            self.x_polling, _, _ ,_ , _, _, self.acc_x, self.acc_y, self.acc_z, self.gyr_x, self.gyr_y, self.gyr_z, self.mag_x, self.mag_y, self.mag_z = gui_data_zip
            max_len = 100
            self.x_polling = self.x_polling[-max_len:]
            self.acc_x = self.acc_x[-max_len:]
            self.acc_y = self.acc_y[-max_len:]
            self.acc_z = self.acc_z[-max_len:]
            self.gyr_x = self.gyr_x[-max_len:]
            self.gyr_y = self.gyr_y[-max_len:]
            self.gyr_z = self.gyr_z[-max_len:]
            self.mag_x = self.mag_x[-max_len:]
            self.mag_y = self.mag_y[-max_len:]
            self.mag_z = self.mag_z[-max_len:]
            self.plot_acc_x.setData(self.x_polling, self.acc_x)
            self.plot_acc_y.setData(self.x_polling, self.acc_y)
            self.plot_acc_z.setData(self.x_polling, self.acc_z)
            self.plot_gyr_x.setData(self.x_polling, self.gyr_x)
            self.plot_gyr_y.setData(self.x_polling, self.gyr_y)
            self.plot_gyr_z.setData(self.x_polling, self.gyr_z)
            self.plot_mag_x.setData(self.x_polling, self.mag_x)
            self.plot_mag_y.setData(self.x_polling, self.mag_y)
            self.plot_mag_z.setData(self.x_polling, self.mag_z)

        # 更新tagid列表
        if self.cur_tag_id is None or time.time() - self.last_update_tagid_time > 3:
            gui_data_zip = list(zip(*Sensor300d.gui_data))
            self.tag_id_combox.blockSignals(True)
            self.tag_id_combox.clear()
            tag_id_set = set(gui_data_zip[1])
            if self.cur_tag_id:
                tag_id_set.add(self.cur_tag_id)
            self.tag_id_combox.addItems(list(map(lambda x: str(x), sorted(tag_id_set))))
            if self.cur_tag_id:
                self.tag_id_combox.setCurrentText(str(self.cur_tag_id))
            else:
                self.tag_id_combox.setCurrentIndex(0)
            self.cur_tag_id = int(self.tag_id_combox.currentText())
            self.tag_id_combox.blockSignals(False)
            self.last_update_tagid_time = time.time()

        logger.info(f'{time.time() - a} {len(Sensor300d.gui_data)}, {min_x_polling} {len(self.x_polling)}')
        # if (len(self.x_polling) > self.xRange):
        #     self.pw1.setXRange(len(self.x_polling) - self.xRange, len(self.x_polling))  # 固定x坐标轴宽度
        #     self.pw2.setXRange(len(self.x_polling) - self.xRange, len(self.x_polling))  # 固定x坐标轴宽度

        # 结束时使能鼠标控制
        # self.pw1.setMouseEnabled(x=True, y=False)  # 使能x轴控制，失能y轴控制
        # self.pw2.setMouseEnabled(x=True, y=False)  # 使能x轴控制，失能y轴控制
