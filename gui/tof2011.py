import threading
import time
from multiprocessing import Queue
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QSpacerItem
import pyqtgraph as pg
import math
import numpy as np

from common.common import logger
from gui.multicombox import CheckableComboBox


pg.setConfigOptions(leftButtonPan=True, antialias=True)  # 允许鼠标左键拖动画面，并启用抗锯齿
pg.setConfigOption('background', 'w')  # 初始的背景(白)

class Tof2011Widght(QWidget):

    gui_queue = Queue()

    def __init__(self):
        super().__init__()

        self.last_update_tagid_time = 0
        self.gui_data = []
        self.tagid2anchorid = {}
        self.cur_tag_id = None
        self.cur_anchor_id = set()
        self.x_range = 200
        self.x_rolling = []
        self.y_distance = []
        self.y_rxl = []
        self.y_fpl = []
        self.main_layout = QVBoxLayout(self)

        # 顶部下拉框
        self.tag_id_combox = QComboBox()
        self.tag_id_combox.currentIndexChanged.connect(self.tagid_selection_changed)
        self.anchor_id_combox = CheckableComboBox()
        self.anchor_id_combox.view.clicked.connect(self.anchorid_selection_changed)
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
        self.pw1.setLabel('bottom', "rolling")  # 设置X轴标签
        self.plot_distance = self.pw1.plot(self.x_rolling, self.y_distance, pen=pg.mkPen(color=(0, 100, 0), width=3),
                                      symbol='s', symbolBrush='g', name='distance')
        self.main_layout.addWidget(self.pw1, 2)

        self.pw2 = pg.PlotWidget(self)  # 图2
        self.pw2.setMouseEnabled(x=False, y=False)  # 失能x,y轴控制
        self.pw2.showGrid(x=True, y=True)  # 显示网格
        self.pw2.setLabel('left', "rxl/fpl")  # 设置Y轴标签
        self.pw2.setLabel('bottom', "rolling")  # 设置X轴标签
        self.plot_fpl = self.pw2.plot(self.x_rolling, self.y_fpl, pen=pg.mkPen(color=(100, 0, 0), width=3),
                                      symbol='s', symbolBrush='r', name='fpl')
        self.plot_rxl = self.pw2.plot(self.x_rolling, self.y_rxl, pen=pg.mkPen(color=(0, 0, 100), width=3),
                                        symbol='s', symbolBrush='b', name='rxl')
        # 创建一个图例
        legend = pg.LegendItem(offset=(60, 20))
        legend.setParentItem(self.pw2.graphicsItem())
        legend.setAutoFillBackground(True)
        # 将图例项添加到图例中
        for item in self.pw2.items():
            if isinstance(item, pg.PlotDataItem):
                name = item.opts['name']
                # color = item.opts['pen'].color().name()
                legend.addItem(item, name=name)
        self.main_layout.addWidget(self.pw2, 1)

        self.t = threading.Thread(target=self.recive_gui_data_thread, daemon=True)
        self.t.start()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.timeout_plot)
        self.timer.start(100)

    def tagid_selection_changed(self, index):
        try:
            # 确定当前tag_id
            cur_tag_id = self.tag_id_combox.currentText()
            if not cur_tag_id or int(cur_tag_id) == self.cur_tag_id:
                return
            cur_tag_id = int(cur_tag_id)
            # 找到关联的anchorid
            anchorid_list = self.tagid2anchorid.get(cur_tag_id, [])
            if len(anchorid_list) == 0:
                logger.warning(f'tof tagid切换{cur_tag_id}时，筛选不到anchorid，准备重新选择tagid')
                self.tag_id_combox.removeItem(index)
                self.tag_id_combox.setCurrentIndex(0)
                return
            self.cur_tag_id = cur_tag_id
            cur_anchor_id = set(anchorid_list) & self.cur_anchor_id
            self.cur_anchor_id = cur_anchor_id if cur_anchor_id else {anchorid_list[0]}
            self.anchor_id_combox.blockSignals(True)
            self.anchor_id_combox.clear()
            self.anchor_id_combox.addCheckableItems(list(map(lambda x: str(x), set(anchorid_list))))
            self.anchor_id_combox.select_items(list(map(lambda x: str(x), self.cur_anchor_id)))
            self.anchor_id_combox.blockSignals(False)

            # 更新gui显示数据
            show_pkgs = list(filter(lambda x: x[1] in self.cur_anchor_id and x[2] == self.cur_tag_id, self.gui_data))
            logger.info(f'tof tagid选择变动：{self.cur_tag_id}， 当前：{self.cur_anchor_id}， 过滤数据包：{len(show_pkgs)}')
            if show_pkgs:
                gui_data_zip = list(zip(*show_pkgs))
                self.x_rolling, _, _, self.y_distance, self.y_rxl, self.y_fpl = gui_data_zip
                self.x_rolling = self.x_rolling[-self.x_range:]
                self.y_distance = self.y_distance[-self.x_range:]
                self.y_rxl = self.y_rxl[-self.x_range:]
                self.y_fpl = self.y_fpl[-self.x_range:]
                self.gui_data = list(filter(lambda x: x[0] > self.x_rolling[0], self.gui_data))
            else:
                self.tag_id_combox.removeItem(index)
                self.tag_id_combox.setCurrentIndex(0)
        except BaseException as e:
            logger.error(f'er: {e}')

    def anchorid_selection_changed(self, index):
        row_idx = index.row()
        item = self.anchor_id_combox.itemText(row_idx)
        self.cur_anchor_id = set(map(lambda x: int(x), self.anchor_id_combox.checkedItems()))
        # 更新gui显示数据
        show_pkgs = list(filter(lambda x: x[1] in self.cur_anchor_id and x[2] == self.cur_tag_id, self.gui_data))
        logger.info(f'tof anchorid选择变动：{"" if self.anchor_id_combox.ifChecked(row_idx) else "取消"}选择{item}， 当前anchorid：{self.cur_anchor_id}， 过滤数据包：{len(show_pkgs)}')
        if show_pkgs:
            gui_data_zip = list(zip(*show_pkgs))
            self.x_rolling, _, _, self.y_distance, self.y_rxl, self.y_fpl = gui_data_zip
            self.x_rolling = self.x_rolling[-self.x_range:]
            self.y_distance = self.y_distance[-self.x_range:]
            self.y_rxl = self.y_rxl[-self.x_range:]
            self.y_fpl = self.y_fpl[-self.x_range:]
            self.gui_data = list(filter(lambda x: x[0] > self.x_rolling[0], self.gui_data))
        elif self.anchor_id_combox.ifChecked(row_idx):
            self.anchor_id_combox.removeItem(row_idx)
            self.cur_anchor_id.discard(int(item))

    def recive_gui_data_thread(self):
        logger.info(f'处理tof gui数据线程启动')
        gui_queue = Tof2011Widght.gui_queue
        while True:
            pkgs = gui_queue.get()
            while not gui_queue.empty():
                pkgs += gui_queue.get(block=True)
            # 剔除滚码小于当前x轴最小值的数据
            min_rolling = self.x_rolling[0] if self.x_rolling else 0
            pkgs = list(filter(lambda x: x[0] > min_rolling, pkgs))
            if not pkgs:
                continue

            self.gui_data += pkgs
            self.gui_data = sorted(self.gui_data, key=lambda x: x[0])[-5000:]

            c = time.time()
            # 每3秒更新下拉列表
            if self.cur_tag_id is None or time.time() - self.last_update_tagid_time > 5:
                if self.cur_tag_id is None:
                    self.cur_tag_id = pkgs[0][2]

                gui_data_zip = list(zip(*self.gui_data))
                tag_id_set = set(gui_data_zip[2])
                if self.cur_tag_id:
                    tag_id_set.add(self.cur_tag_id)

                # 关联anchorid列表
                input_array = np.array(gui_data_zip[2])
                self.tagid2anchorid = {elem: np.take(gui_data_zip[1], np.where(input_array == elem)[0].tolist()) for
                                       elem in tag_id_set}
                if not self.cur_anchor_id:
                    try:
                        self.cur_anchor_id = {self.tagid2anchorid[self.cur_tag_id][0]}
                    except BaseException as e:
                        pass
                cc = time.time()
                anchorid_set = set(self.tagid2anchorid[self.cur_tag_id]) | set(self.cur_anchor_id)

                self.tag_id_combox.blockSignals(True)
                self.tag_id_combox.clear()
                self.tag_id_combox.addItems(list(map(lambda x: str(x), sorted(tag_id_set))))
                self.tag_id_combox.setCurrentText(str(self.cur_tag_id))
                self.tag_id_combox.blockSignals(False)
                self.anchor_id_combox.blockSignals(True)
                self.anchor_id_combox.clear()
                self.anchor_id_combox.addCheckableItems(anchorid_set)
                self.anchor_id_combox.select_items(self.cur_anchor_id)
                self.anchor_id_combox.blockSignals(False)

                self.last_update_tagid_time = time.time()
                logger.info(f'tof显示数据队列积压：{gui_queue.empty()}, 积压全量gui数据：{len(self.gui_data)}，x轴最小值{self.x_rolling[0] if self.x_rolling else None}，x轴长度：{len(self.x_rolling)}，tagid数量：{len(tag_id_set)}')

            # 筛选当前tagid的数据用于显示
            show_pkgs = list(filter(lambda x: x[1] in self.cur_anchor_id and x[2] == self.cur_tag_id and x[0] not in self.x_rolling, pkgs))
            if show_pkgs:
                gui_data_zip = list(zip(*show_pkgs))
                x_rolling_show, _, _, distance_show, rxl, fpl = gui_data_zip

                x_rolling = list(self.x_rolling) + list(x_rolling_show)
                x_rolling_enumerated = sorted(enumerate(x_rolling), key=lambda x: x[1])
                x_rolling_idx, x_rolling = list(zip(*x_rolling_enumerated))
                x_rolling_idx, x_rolling = list(x_rolling_idx), list(x_rolling[-self.x_range:])
                distance_show = list(np.array(list(self.y_distance) + list(distance_show))[x_rolling_idx][-self.x_range:])
                rxl = list(np.array(list(self.y_rxl) + list(rxl))[x_rolling_idx][-self.x_range:])
                fpl = list(np.array(list(self.y_fpl) + list(fpl))[x_rolling_idx][-self.x_range:])
                self.x_rolling, self.y_distance, self.y_rxl, self.y_fpl = x_rolling, distance_show, rxl, fpl
                if self.gui_data[0][0] < self.x_rolling[0]:
                    self.gui_data = list(filter(lambda x: x[0] > self.x_rolling[0], self.gui_data))
            # logger.info(f'耗时：{c - b} {b - a} {time.time() - c} {time.time() - a}')

    def timeout_plot(self):
        try:
            self.plot_distance.setData(self.x_rolling, self.y_distance)  # 重新绘制
            self.plot_rxl.setData(self.x_rolling, self.y_rxl)  # 重新绘制
            self.plot_fpl.setData(self.x_rolling, self.y_fpl)  # 重新绘制
        except BaseException as e:
            logger.error(f'error: {e}')
