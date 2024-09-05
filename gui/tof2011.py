import random
import threading
import time
from functools import reduce
from multiprocessing import Queue
from PySide6.QtCore import QTimer, QTime, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QApplication, QTextEdit
import pyqtgraph as pg
import math
import numpy as np
import pandas as pd
from common.common import logger, config
from gui.common import CheckableComboBox


pg.setConfigOptions(leftButtonPan=True, antialias=True)  # 允许鼠标左键拖动画面，并启用抗锯齿
pg.setConfigOption('background', 'w')  # 初始的背景(白)


class Tof2011Widget(QWidget):

    gui_queue = Queue()
    update_combox_signal = Signal()

    def __init__(self):
        super().__init__()

        self.lock = threading.Lock()
        self.last_update_tagid_time = 0
        self.gui_data = []
        self.tagid2anchorid = {}
        self.cur_tag_id = None
        self.cur_anchor_id = set()
        self.x_range = 200
        self.x_rolling = np.array([])
        self.y_rxl = np.array([])
        self.y_fpl = np.array([])
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
        self.plot_distance = {}
        self.main_layout.addWidget(self.pw1, 2)
        # 创建一个图例
        self.legend = pg.LegendItem(offset=(70, 20))
        self.legend.setParentItem(self.pw1.graphicsItem())
        self.legend.setAutoFillBackground(True)

        self.pw2 = pg.PlotWidget(self)  # 图2
        self.pw2.setMouseEnabled(x=False, y=False)  # 失能x,y轴控制
        self.pw2.showGrid(x=True, y=True)  # 显示网格
        self.pw2.setLabel('left', "rxl/fpl")  # 设置Y轴标签
        self.pw2.setLabel('bottom', "rolling")  # 设置X轴标签
        self.plot_fpl = self.pw2.plot(self.x_rolling, self.y_fpl, pen=pg.mkPen(color=(100, 0, 0), width=3),
                                      symbol='o', symbolBrush='r', name='fpl', symbolSize=5)
        self.plot_rxl = self.pw2.plot(self.x_rolling, self.y_rxl, pen=pg.mkPen(color=(0, 0, 100), width=3),
                                      symbol='o', symbolBrush='b', name='rxl', symbolSize=5)
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

        self.statistic_textedit = QTextEdit()
        self.main_layout.addWidget(self.statistic_textedit, 1)

        self.t = threading.Thread(
            target=self.recive_gui_data_thread, daemon=True)
        self.t.start()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.timeout_plot)
        self.timer.start(300)

        self.update_combox_timer = QTimer(self)
        self.update_combox_timer.timeout.connect(self.update_combox)
        self.update_combox_timer.start(5000)

        self.update_combox_signal.connect(self.update_combox)

    def tagid_selection_changed(self, index):
        with self.lock:
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
            logger.info(f'tof tagid选择变动：{self.cur_tag_id}, tag数量：{self.tag_id_combox.count()}， 当前：{self.cur_anchor_id}')

        self.generate_distance_data_curve(self.gui_data, False)
        if not self.generate_distance_data_curve(self.gui_data, False):
            self.tag_id_combox.removeItem(index)
            self.tag_id_combox.setCurrentIndex(0)

    def anchorid_selection_changed(self, index):
        with self.lock:
            row_idx = index.row()
            item = self.anchor_id_combox.itemText(row_idx)
            self.cur_anchor_id = set(map(lambda x: int(x), self.anchor_id_combox.checkedItems()))
            # # 更新gui显示数据
            logger.info(f'tof anchorid选择变动：{"" if self.anchor_id_combox.ifChecked(row_idx) else "取消"}选择{item}， 当前anchorid：{self.cur_anchor_id}')
        self.generate_distance_data_curve(self.gui_data, False)

    def generate_distance_data_curve(self, pkgs, incr=True):
        with self.lock:
            if not self.cur_anchor_id:
                return False

            if len(self.plot_distance) == 0:
                incr = False

            for x in self.cur_anchor_id:
                show_pkgs = pkgs[np.logical_and(pkgs[:, 1] == x, pkgs[:, 2] == self.cur_tag_id)]
                if len(show_pkgs) == 0:
                    continue
                # 过滤anchorid、tagid的包
                x_rolling, y_distance, rxl, fpl = show_pkgs[:, 0], show_pkgs[:, 3], show_pkgs[:, 4], show_pkgs[:, 5]
                if incr:
                    ori_x_rolling, ori_y_distance = self.plot_distance.get(x, {}).get('x', []), self.plot_distance.get(x, {}).get('y', [])
                    x_rolling, y_distance = np.concatenate((ori_x_rolling, x_rolling)), np.concatenate((ori_y_distance, y_distance))
                    x_rolling_idx = np.argsort(x_rolling)
                    x_rolling, y_distance = x_rolling[x_rolling_idx][-self.x_range:], y_distance[x_rolling_idx][-self.x_range:]
                    if len(self.cur_anchor_id) == 1:  # 只有一个anchorid，则更新rxl、fpl
                        self.x_rolling, self.y_rxl, self.y_fpl = (x_rolling, np.concatenate((self.y_rxl, rxl))[x_rolling_idx][-self.x_range:],
                                                                  np.concatenate((self.y_fpl, fpl))[x_rolling_idx][-self.x_range:])
                else:
                    if len(self.cur_anchor_id) == 1:
                        self.x_rolling, self.y_rxl, self.y_fpl = x_rolling[-self.x_range:], rxl[-self.x_range:], fpl[-self.x_range:]
                    x_rolling, y_distance = (x_rolling[-self.x_range:], y_distance[-self.x_range:])

                if 'line' not in self.plot_distance.get(x, {}):
                    ploter = self.pw1.plot(x_rolling, y_distance, pen=pg.mkPen(color=random.randint(0, 0xffffff) | 0xff00, width=3),
                                           symbol='o', symbolBrush='b', name=str(x), symbolSize=5)
                    logger.warning(f'生成曲线 {x} {list(self.plot_distance.keys())} {incr}')
                else:
                    ploter = self.plot_distance[x]['line']

                self.plot_distance.update({x: {
                    'line': ploter,
                    'x': x_rolling,
                    'y': y_distance,
                }})
            self.plot_distance = {
                k: v for k, v in self.plot_distance.items() if k in self.cur_anchor_id}
            # 同步更新图例
            if not incr or not self.legend.items:
                self.legend.clear()
                for k, v in self.plot_distance.items():
                    self.legend.addItem(v['line'], name=str(k))

                for item in self.pw1.items():
                    if isinstance(item, pg.PlotDataItem) and int(item.opts['name']) not in self.plot_distance:
                        item.clear()
                        self.pw1.removeItem(item)
                        # legend.addItem(item, name=name)
                logger.warning(f'全量刷新tof，图例数量：{len(self.legend.items)} anchcor_id: {self.cur_anchor_id}, plot_distance: {self.plot_distance.keys()}')
            return len(self.plot_distance) != 0

    def update_combox(self):
        if not self.tagid2anchorid:
            return
        try:
            anchorid_set = set(self.tagid2anchorid[self.cur_tag_id]) | set(self.cur_anchor_id)
        except BaseException as e:
            return
        tag_id_list = list(map(lambda x: str(x), sorted(self.tag_id_set)))
        self.tag_id_combox.blockSignals(True)
        self.tag_id_combox.clear()
        self.tag_id_combox.addItems(tag_id_list)
        self.tag_id_combox.setCurrentText(str(self.cur_tag_id))
        self.tag_id_combox.blockSignals(False)

        self.anchor_id_combox.blockSignals(True)
        self.anchor_id_combox.clear()
        self.anchor_id_combox.addCheckableItems(anchorid_set)
        self.anchor_id_combox.select_items(self.cur_anchor_id)
        self.anchor_id_combox.blockSignals(False)

        # self.last_update_tagid_time = time.time()
        logger.info(
            f'tof显示数据队列积压：{Tof2011Widget.gui_queue.qsize()}, x轴最小值{self.x_rolling[0] if len(self.x_rolling) > 0 else None}，x轴长度：{len(self.x_rolling)}，tagid数量：{len(self.tag_id_set)}')

    def reset_check(self, pkgs):
        in_max_rolling = max(pkgs[:, 0])  # 收到待展示的一批数据的最大滚码
        with self.lock:
            if len(self.plot_distance) == 0:
                logger.warning(f'self.plot_distance=0')
                return False
            max_rolling = max(map(lambda x: max(x['x']), self.plot_distance.values()))
            # logger.info(f'in_max_rolling: {in_max_rolling}, max_rolling:{max_rolling}')
            if max_rolling - in_max_rolling < config['rolling_max_interval']:
                return False
            self.gui_data = []
            self.cur_tag_id = self.cur_anchor_id = None
            return True

    def recive_gui_data_thread(self):
        logger.info(f'处理tof gui数据线程启动')
        gui_queue = Tof2011Widget.gui_queue
        while True:
            pkgs = gui_queue.get()
            while not gui_queue.empty() and len(pkgs) < 1000:
                pkgs += gui_queue.get(block=False)
                QApplication.processEvents()
            pkgs = np.array(pkgs)
            if len(pkgs) == 0:
                continue
            incr = True
            if self.reset_check(pkgs):
                incr = False
                logger.warning(f'tof gui重新更新')
            else:
                # 剔除滚码小于当前x轴最小值的数据
                min_rolling = self.x_rolling[0] if len(self.x_rolling) > 0 else 0
                pkgs = pkgs[pkgs[:, 0] > min_rolling]
                if len(pkgs) == 0:
                    continue
            # QApplication.processEvents()
            # 处理突变
            # if len(self.gui_data) > 0:
            #     rolling_data = pkgs[:, 0]
            #     max_rolling = self.gui_data[:, 0][-1]
            #     less_than_1000_indices = np.where(rolling_data < (max_rolling - 1000))[0]
            #     if len(less_than_1000_indices) > 0:
            #         min_val = np.min(rolling_data[less_than_1000_indices])
            #         rolling_data[less_than_1000_indices] += (max_rolling - min_val + 1)
            # pkgs[:, 0] = rolling_data

            self.gui_data = np.vstack((self.gui_data, pkgs)) if len(self.gui_data) > 0 else pkgs
            self.gui_data = self.gui_data[np.argsort(self.gui_data[:, 0])][-5000:]  # 按照滚码排序

            # 每3秒更新下拉列表
            if self.cur_tag_id is None or time.time() - self.last_update_tagid_time > 3:
                with self.lock:
                    need_emit = self.cur_tag_id is None
                    if self.cur_tag_id is None:
                        self.cur_tag_id = pkgs[0][2]

                    self.tag_id_set = set(self.gui_data[:, 2])
                    if self.cur_tag_id:
                        self.tag_id_set.add(self.cur_tag_id)

                    # 关联每个tagid对应的anchorid列表
                    self.tagid2anchorid = {elem: np.take(self.gui_data[:, 1], np.where(self.gui_data[:, 2] == elem)[0].tolist()) for
                                           elem in self.tag_id_set}
                    if not self.cur_anchor_id:
                        self.cur_anchor_id = {self.tagid2anchorid[self.cur_tag_id][0]}

                    if need_emit:
                        self.update_combox_signal.emit()
                    self.last_update_tagid_time = time.time()
            self.generate_distance_data_curve(pkgs, incr)

    def timeout_plot(self):
        data = {'anchorid': [], '最小值': [], '最大值': [], '中位数': [], '5%': [], '95%': [], '成功率': []}
        for anchorid, distance_line in self.plot_distance.items():
            distance_line['line'].setData(distance_line['x'].tolist(), distance_line['y'].tolist())  # 重新绘制
            data['anchorid'].append(anchorid)
            data['最小值'].append(np.min(distance_line['y']))
            data['最大值'].append(np.max(distance_line['y']))
            data['中位数'].append(np.median(distance_line['y']))
            data['5%'].append(np.percentile(distance_line['y'], 5))
            data['95%'].append(np.percentile(distance_line['y'], 95))
            data['成功率'].append(str(round(len(distance_line['x']) / (max(distance_line['x']) - min(distance_line['x']) + 1) * 100, 2)) + '%')
        data = pd.DataFrame(data)
        self.statistic_textedit.setHtml(data.to_html(index=False))

        if len(self.plot_distance) == 1:  # anchordid选择数量为1时候才显示rxl、fpl
            self.plot_rxl.setData(self.x_rolling.tolist(), self.y_rxl.tolist())  # 重新绘制
            self.plot_fpl.setData(self.x_rolling.tolist(), self.y_fpl.tolist())  # 重新绘制
        else:
            self.plot_rxl.setData([], [])  # 重新绘制
            self.plot_fpl.setData([], [])  # 重新绘制
