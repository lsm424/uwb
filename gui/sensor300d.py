import threading
import time
import queue
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QLineEdit
import pyqtgraph as pg
import math
import numpy as np
from multiprocessing import Queue
from common.common import logger
from uwb.tof_2011 import Tof2011


class Sensor300dWidght(QWidget):

    gui_queue = Queue()

    def __init__(self):
        super().__init__()
        self.gui_data = []
        self.x_range = 100

        self.main_layout = QVBoxLayout(self)
        up_layout = QHBoxLayout()

        pres_layout = QHBoxLayout()
        pres_layout.addWidget(QLabel('气压：'))
        self.pres = ''
        self.pres_lineedit = QLineEdit()
        self.pres_lineedit.setReadOnly(True)
        pres_layout.addWidget(self.pres_lineedit)
        up_layout.addLayout(pres_layout)

        temp_layout = QHBoxLayout()
        temp_layout.addWidget(QLabel('温度：'))
        self.temp = ''
        self.temp_lineedit = QLineEdit()
        self.temp_lineedit.setReadOnly(True)
        temp_layout.addWidget(self.temp_lineedit)
        up_layout.addLayout(temp_layout)

        batt_layout = QHBoxLayout()
        batt_layout.addWidget(QLabel('电量：'))
        self.batt = ''
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

        self.t = threading.Thread(target=self.recive_gui_data_thread, daemon=True)
        self.t.start()
        self.last_update_tagid_time = time.time()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.timeout_plot)
        self.timer.start(200)


    def tagid_selection_changed(self, index):
        cur_tag_id = self.tag_id_combox.currentText()
        if not cur_tag_id:
            return
        self.cur_tag_id = int(cur_tag_id)

        show_pkgs = list(filter(lambda x: x[1] == self.cur_tag_id, self.gui_data))
        if show_pkgs:
            self.batt, self.pres, self.temp = show_pkgs[-1][3:6]

            gui_data_zip = list(zip(*show_pkgs))
            self.x_polling, _, _ ,_ , _, _, self.acc_x, self.acc_y, self.acc_z, self.gyr_x, self.gyr_y, self.gyr_z, self.mag_x, self.mag_y, self.mag_z = gui_data_zip
            self.x_polling = self.x_polling[-self.x_range:]
            self.acc_x = self.acc_x[-self.x_range:]
            self.acc_y = self.acc_y[-self.x_range:]
            self.acc_z = self.acc_z[-self.x_range:]
            self.gyr_x = self.gyr_x[-self.x_range:]
            self.gyr_y = self.gyr_y[-self.x_range:]
            self.gyr_z = self.gyr_z[-self.x_range:]
            self.mag_x = self.mag_x[-self.x_range:]
            self.mag_y = self.mag_y[-self.x_range:]
            self.mag_z = self.mag_z[-self.x_range:]
            self.gui_data = list(filter(lambda x: x[0] > self.x_polling[0], self.gui_data))
        else:
            self.tag_id_combox.removeItem(index)


    def recive_gui_data_thread(self):
        logger.info(f'处理传感器gui数据线程启动')
        gui_queue = Sensor300dWidght.gui_queue
        while True:
            pkgs = [gui_queue.get()]
            # logger.info(f'处理传感器gui数据线程启动-收到数据')
            while not gui_queue.empty() and len(pkgs) < 500:
                pkgs.append(gui_queue.get(block=False))

            # 剔除滚码小于当前x轴最小值的数据
            min_rolling = self.x_polling[0] if self.x_polling else 0
            pkgs = list(filter(lambda x: x[0] > min_rolling, pkgs))
            if not pkgs:
                continue

            self.gui_data += pkgs
            self.gui_data = sorted(self.gui_data, key=lambda x: x[0])[-1000:]

            # 每3秒更新下拉列表
            if self.cur_tag_id is None or time.time() - self.last_update_tagid_time > 5:
                if self.cur_tag_id is None:
                    self.cur_tag_id = pkgs[0][1]

                gui_data_zip = list(zip(*self.gui_data))
                self.tag_id_combox.blockSignals(True)
                self.tag_id_combox.clear()
                tag_id_set = set(gui_data_zip[1])
                if self.cur_tag_id:
                    tag_id_set.add(self.cur_tag_id)
                self.tag_id_combox.addItems(list(map(lambda x: str(x), sorted(tag_id_set))))
                self.tag_id_combox.setCurrentText(str(self.cur_tag_id))
                self.tag_id_combox.blockSignals(False)
                self.last_update_tagid_time = time.time()
                logger.info(
                    f'传感器显示数据队列积压：{gui_queue.qsize()}, 积压全量gui数据：{len(self.gui_data)}，x轴最小值{self.x_polling[0] if self.x_polling else None}，x轴长度：{len(self.x_polling)}，tagid数量：{len(tag_id_set)}')

            # 筛选当前tagid的数据用于显示
            show_pkgs = list(filter(lambda x: x[1] == self.cur_tag_id and x[0] not in self.x_polling, pkgs))
            if show_pkgs:
                gui_data_zip = list(zip(*show_pkgs))
                x_polling_show, _, _, _, _, _, acc_x_show, acc_y_show, acc_z_show, gyr_x_show, gyr_y_show, gyr_z_show, mag_x_show, mag_y_show, mag_z_show = gui_data_zip

                x_polling = list(self.x_polling) + list(x_polling_show)
                x_polling_enumerated = sorted(enumerate(x_polling), key=lambda x: x[1])
                x_polling_idx, x_polling = list(zip(*x_polling_enumerated))
                x_polling_idx = list(x_polling_idx)
                x_polling = list(x_polling[-self.x_range:])
                acc_x_show = list(np.array(list(self.acc_x) + list(acc_x_show))[x_polling_idx][-self.x_range:])
                acc_y_show = list(np.array(list(self.acc_y) + list(acc_y_show))[x_polling_idx][-self.x_range:])
                acc_z_show = list(np.array(list(self.acc_z) + list(acc_z_show))[x_polling_idx][-self.x_range:])
                gyr_x_show = list(np.array(list(self.gyr_x) + list(gyr_x_show))[x_polling_idx][-self.x_range:])
                gyr_y_show = list(np.array(list(self.gyr_y) + list(gyr_y_show))[x_polling_idx][-self.x_range:])
                gyr_z_show = list(np.array(list(self.gyr_z) + list(gyr_z_show))[x_polling_idx][-self.x_range:])
                mag_x_show = list(np.array(list(self.mag_x) + list(mag_x_show))[x_polling_idx][-self.x_range:])
                mag_y_show = list(np.array(list(self.mag_y) + list(mag_y_show))[x_polling_idx][-self.x_range:])
                mag_z_show = list(np.array(list(self.mag_z) + list(mag_z_show))[x_polling_idx][-self.x_range:])

                self.x_polling, self.acc_x, self.acc_y, self.acc_z, self.gyr_x, self.gyr_y, self.gyr_z, self.mag_x, self.mag_y, self.mag_z = x_polling, acc_x_show, acc_y_show, acc_z_show, gyr_x_show, gyr_y_show, gyr_z_show, mag_x_show, mag_y_show, mag_z_show
                if self.gui_data[0][0] < self.x_polling[0]:
                    self.gui_data = list(filter(lambda x: x[0] > self.x_polling[0], self.gui_data))

                # 温度压力电量更新
                try:
                    idx = list(gui_data_zip[0]).index(self.x_polling[-1])
                    if idx >= 0:
                        self.batt, self.pres, self.temp = pkgs[idx][3:6]
                except BaseException as e:
                    pass

    def timeout_plot(self):
        # a = time.time()
        self.plot_acc_x.setData(self.x_polling, self.acc_x)
        self.plot_acc_y.setData(self.x_polling, self.acc_y)
        self.plot_acc_z.setData(self.x_polling, self.acc_z)
        self.plot_gyr_x.setData(self.x_polling, self.gyr_x)
        self.plot_gyr_y.setData(self.x_polling, self.gyr_y)
        self.plot_gyr_z.setData(self.x_polling, self.gyr_z)
        self.plot_mag_x.setData(self.x_polling, self.mag_x)
        self.plot_mag_y.setData(self.x_polling, self.mag_y)
        self.plot_mag_z.setData(self.x_polling, self.mag_z)
        self.batt_lineedit.setText(str(self.batt))
        self.temp_lineedit.setText(str(self.temp))
        self.pres_lineedit.setText(str(self.pres))
        # logger.info(f'{time.time() - a} {Sensor300dWidght.gui_queue.qsize()}, {len(self.gui_data)} {self.x_polling[0] if self.x_polling else None} {len(self.x_polling)}')
        # if (len(self.x_polling) > self.xRange):
        #     self.pw1.setXRange(len(self.x_polling) - self.xRange, len(self.x_polling))  # 固定x坐标轴宽度
        #     self.pw2.setXRange(len(self.x_polling) - self.xRange, len(self.x_polling))  # 固定x坐标轴宽度

        # 结束时使能鼠标控制
        # self.pw1.setMouseEnabled(x=True, y=False)  # 使能x轴控制，失能y轴控制
        # self.pw2.setMouseEnabled(x=True, y=False)  # 使能x轴控制，失能y轴控制
