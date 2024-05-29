import threading
import time
import queue
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QSpacerItem
import pyqtgraph as pg
import math
import numpy as np

from common.common import logger
from gui.multicombox import CheckableComboBox
from uwb.tof_2011 import Tof2011

pg.setConfigOptions(leftButtonPan=True, antialias=True)  # 允许鼠标左键拖动画面，并启用抗锯齿
pg.setConfigOption('background', 'w')  # 初始的背景(白)

class Tof2011Widght(QWidget):

    gui_data_queue = queue.Queue()

    def __init__(self):
        super().__init__()

        self.tagid2anchorid = {}
        self.cur_tag_id = None
        self.cur_anchor_id = []
        self.xRange = 80
        self.x_polling = []
        self.y_distance = []
        self.y_rxl = []
        self.y_fpl = []
        self.main_layout = QVBoxLayout(self)

        # 顶部下拉框
        self.tag_id_combox = QComboBox()
        # self.tag_id_combox.currentIndexChanged.connect(self.tagid_selection_changed)
        self.anchor_id_combox = CheckableComboBox()
        # self.anchor_id_combox.view.clicked.connect(self.anchorid_selection_changed)
        up_layout = QHBoxLayout()
        up_layout.addSpacing(100)
        up_layout.addWidget(QLabel('tagid选择：'))
        up_layout.addWidget(self.tag_id_combox)
        up_layout.addSpacing(400)
        up_layout.addWidget(QLabel('anchorid选择：'))
        up_layout.addWidget(self.anchor_id_combox)
        up_layout.addSpacing(100)
        self.main_layout.addLayout(up_layout)

        self.pw1 = pg.PlotWidget(self)  # 图1
        self.pw1.setMouseEnabled(x=False, y=False)  # 失能x,y轴控制
        self.pw1.showGrid(x=True, y=True)  # 显示网格
        self.pw1.setLabel('left', "distance")  # 设置Y轴标签
        self.pw1.setLabel('bottom', "polling")  # 设置X轴标签
        self.plot_distance = self.pw1.plot(self.x_polling, self.y_distance, pen=pg.mkPen(color=(0, 0, 100), width=3),
                                      symbol='s', symbolBrush='r', name='distance')
        self.main_layout.addWidget(self.pw1, 2)

        self.pw2 = pg.PlotWidget(self)  # 图2
        self.pw2.setMouseEnabled(x=False, y=False)  # 失能x,y轴控制
        self.pw2.showGrid(x=True, y=True)  # 显示网格
        self.pw2.setLabel('left', "rxl/fpl")  # 设置Y轴标签
        self.pw2.setLabel('bottom', "polling")  # 设置X轴标签
        self.plot_fpl = self.pw2.plot(self.x_polling, self.y_fpl, pen=pg.mkPen(color=(0, 0, 100), width=3),
                                      symbol='s', symbolBrush='r', name='fpl')
        self.plot_rxl = self.pw2.plot(self.x_polling, self.y_rxl, pen=pg.mkPen(color=(0, 0, 100), width=3),
                                        symbol='s', symbolBrush='b', name='rxl')
        # 创建一个图例
        legend = pg.LegendItem(offset=(60, 20))
        legend.setParentItem(self.pw2.graphicsItem())
        legend.setAutoFillBackground(1)
        # 将图例项添加到图例中
        for item in self.pw2.items():
            if isinstance(item, pg.PlotDataItem):
                name = item.opts['name']
                # color = item.opts['pen'].color().name()
                legend.addItem(item, name=name)
        self.main_layout.addWidget(self.pw2, 1)

        # self.parase = threading.Thread(target=self.parase, daemon=True)
        # self.parase.start()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.timeout_plot)
        self.timer.start(100)

    def parase(self):
        while True:
            gui_data = Tof2011Widght.gui_data_queue.get()
            while not Tof2011Widght.gui_data_queue.empty() and len(gui_data) < 200:
                gui_data += Tof2011Widght.gui_data_queue.get(block=False)

    def tagid_selection_changed(self, index):
        cur_tag_id = self.tag_id_combox.currentText()
        if not cur_tag_id:
            return
        self.cur_tag_id = int(cur_tag_id)
        anchorid_list = self.tagid2anchorid.get(self.cur_tag_id, [])
        if len(anchorid_list) > 0:
            self.anchor_id_combox.blockSignals(True)
            self.anchor_id_combox.clear()
            self.anchor_id_combox.addCheckableItems(list(map(lambda x: str(x), anchorid_list)))
            if self.cur_anchor_id:
                self.anchor_id_combox.setCurrentText(str(self.cur_anchor_id))
            else:
                self.anchor_id_combox.setCurrentIndex(0)
                self.anchorid_selection_changed(0)

            self.anchor_id_combox.blockSignals(False)

    def anchorid_selection_changed(self, index):
        self.cur_anchor_id = list(map(lambda x: int(x), self.anchor_id_combox.checkedItems()))

    def timeout_plot(self):
        a = time.time()
        gui_data = Tof2011.gui_data
        if not gui_data:
            return
        # 转置，计算出当前有哪些tag_id、anchor_id，更新对应的下拉列表
        gui_data_zip = list(zip(*gui_data))
        tag_id_set = set(gui_data_zip[2])
        if self.cur_tag_id is not None:
            tag_id_set.add(self.cur_tag_id)
        self.tag_id_combox.clear()
        self.tag_id_combox.blockSignals(True)
        self.tag_id_combox.addItems(list(map(lambda x: str(x), sorted(tag_id_set))))
        self.tag_id_combox.blockSignals(False)
        input_array = np.array(gui_data_zip[2])
        self.tagid2anchorid = {elem: np.take(gui_data_zip[1], np.where(input_array == elem)[0].tolist()) for elem in tag_id_set}

        if self.cur_tag_id is None:
            self.tag_id_combox.setCurrentIndex(0)
            self.tagid_selection_changed(0)
        else:
            self.tag_id_combox.setCurrentText(str(self.cur_tag_id))
            # self.cur_tag_id = list(self.tagid2anchorid)[0]
            # self.cur_anchor_id = self.tagid2anchorid[self.cur_tag_id][0]
            # self.anchor_id_combox.clear()
            # self.anchor_id_combox.addItems(list(map(lambda x: str(x), self.tagid2anchorid[self.cur_tag_id])))

        gui_data = list(filter(lambda x: x[1] in self.cur_anchor_id and x[2] == self.cur_tag_id, gui_data))
        if not gui_data:
            return
        gui_data_zip = list(zip(*gui_data))
        self.x_polling= list(self.x_polling) + list(gui_data_zip[0])
        self.y_distance = list(self.y_distance) + list(gui_data_zip[3])
        self.y_rxl = list(self.y_rxl) + list(gui_data_zip[4])
        self.y_fpl = list(self.y_fpl) + list(gui_data_zip[5])
        # 按照滚码排序，取最新的300条
        self.x_polling, self.y_distance, self.y_rxl, self.y_fpl = list(zip(*sorted(zip(self.x_polling, self.y_distance, self.y_rxl, self.y_fpl), key=lambda x: x[0])))
        self.x_polling, self.y_distance, self.y_rxl, self.y_fpl = self.x_polling[-1000:], self.y_distance[-1000:], self.y_rxl[-1000:], self.y_fpl[-1000:]

        # self.x_polling.append(len(self.x_polling))  # +1
        # self.y_distance.append(math.sin(self.x_polling[-1] / 10))

        self.plot_distance.setData(self.x_polling, self.y_distance)  # 重新绘制
        self.plot_rxl.setData(self.x_polling, self.y_rxl)  # 重新绘制
        self.plot_fpl.setData(self.x_polling, self.y_fpl)  # 重新绘制
        # logger.info(f'{time.time() - a} ')
        # if (len(self.x_polling) > self.xRange):
        #     self.pw1.setXRange(len(self.x_polling) - self.xRange, len(self.x_polling))  # 固定x坐标轴宽度
        #     self.pw2.setXRange(len(self.x_polling) - self.xRange, len(self.x_polling))  # 固定x坐标轴宽度

        # 结束时使能鼠标控制
        # self.pw1.setMouseEnabled(x=True, y=False)  # 使能x轴控制，失能y轴控制
        # self.pw2.setMouseEnabled(x=True, y=False)  # 使能x轴控制，失能y轴控制
