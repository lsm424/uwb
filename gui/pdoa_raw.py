import random
import threading
import time
from multiprocessing import Queue
from PySide6.QtCore import QTimer, QTime, Signal, QThread
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QApplication
import pyqtgraph as pg
import math
import pandas as pd
import numpy as np

from common.common import logger, config
from gui.multicombox import CheckableComboBox
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

# pdoa原始数据


# 定义一个 QThread 子类
class WorkerThread(QThread):
    def __init__(self, pdoa_raw):
        super().__init__()
        self.pdoa_raw = pdoa_raw

    def run(self):
        self.pdoa_raw.run()


class RealTimePlot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout(self)

        # 创建一个 Figure 对象
        self.figure = Figure()

        # 创建一个 FigureCanvas 用于显示 Figure
        self.canvas = FigureCanvas(self.figure)
        self.layout.addWidget(self.canvas)

        # 初始化数据
        self.x_data = []
        self.y_data = []
        self.y2_data = []
        # 在 Figure 上添加一个子图
        self.figure.subplots(2, 1, gridspec_kw={'hspace': 0.5})
        # 获取两个子图对象
        self.ax = self.figure.axes[0]
        self.ax.grid()
        self.ax.set_title('tdoa')

        self.lines = list(map(lambda x: self.ax.plot([], [])[0], range(4)))
        # self.ax2 = self.figure.add_subplot(211)
        self.ax2 = self.figure.axes[1]
        self.ax2.grid()
        self.ax2.set_title('pdoa')
        self.lines2 = list(map(lambda x: self.ax2.plot([], [])[0], range(4)))

        # 定时器，每隔一段时间更新图表
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(300)  # 每1000毫秒（1秒）更新一次

    def update_plot(self):
        # 模拟数据更新
        if not self.x_data:
            return
        # self.x_data.append(len(self.x_data) + 1)
        # self.y_data.append([random.randint(0, 10), random.randint(0, 10), random.randint(0, 10), random.randint(0, 10)])
        # self.y2_data.append([random.randint(0, 10), random.randint(0, 10), random.randint(0, 10), random.randint(0, 10)])
        # for i in range(len(self.y_data)):
        #     self.y_data[i].append(random.randint(0, 10))

        y_data = list(zip(*self.y_data))
        # 更新每条曲线的数据
        for i, y in enumerate(y_data):
            self.lines[i].set_xdata(self.x_data)
            self.lines[i].set_ydata(y)

        y_data = list(zip(*self.y2_data))
        for i, y in enumerate(y_data):
            self.lines2[i].set_xdata(self.x_data)
            self.lines2[i].set_ydata(y)

        # 自动调整坐标轴范围
        self.ax.relim()
        self.ax.autoscale_view()

        self.ax2.relim()
        self.ax2.autoscale_view()
        # 刷新画布
        self.canvas.draw()


class PdoaRawWidget(QWidget):

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
        self.x_data = []
        self.y_data = []
        self.rolling_all = np.array([])
        self.y_tdoa_all = np.array([])
        self.y_pdoa_all = np.array([])
        self.main_layout = QVBoxLayout(self)
        self.main_layout.addSpacing(10)
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

        self.real_time_plot = RealTimePlot()
        self.main_layout.addWidget(self.real_time_plot)

        self.work_thread = WorkerThread(self)
        self.work_thread.start()

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
            # cur_anchor_id = set(anchorid_list) & self.cur_anchor_id
            self.cur_anchor_id = anchorid_list[:4]
            self.anchor_id_combox.blockSignals(True)
            self.anchor_id_combox.clear()
            self.anchor_id_combox.addCheckableItems(list(map(lambda x: str(x), set(anchorid_list))))
            self.anchor_id_combox.select_items(list(map(lambda x: str(x), self.cur_anchor_id)))
            self.anchor_id_combox.blockSignals(False)

            # 更新gui显示数据
            logger.info(f'tof tagid选择变动：{self.cur_tag_id}, tag数量：{self.tag_id_combox.count()}， 当前：{self.cur_anchor_id}')

        self.generate_distance_data_curve(self.gui_data, False)

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
            if not self.cur_anchor_id or len(self.cur_anchor_id) != 4:
                logger.info(f'pdoa 计算曲线 要4个anchorid，目前为：{self.cur_anchor_id}')
                return False

            pkgs.to_csv('test.csv', index=False)
            resu = pkgs.groupby(by='rolling').apply(lambda x: self.show(x)).sort_index()[-config['pdoa_raw']['dispBufferSize']:]
            y_pdoa_all, y_tdoa_all = list(zip(*resu.values))
            y_tdoa_all = np.concatenate(y_tdoa_all, 0)
            y_pdoa_all = np.concatenate(y_pdoa_all, 0)
            PDOA_ang_all = np.zeros(y_pdoa_all.shape) + np.nan
            for i in range(1, len(self.cur_anchor_id)):
                PDOA_ang_all[np.isfinite(y_pdoa_all[:, i]), i] = np.unwrap(np.angle(y_pdoa_all[np.isfinite(y_pdoa_all[:, i]), i]), axis=0)
            self.rolling_all, self.y_tdoa_all, self.y_pdoa_all = resu.keys(), y_tdoa_all, PDOA_ang_all
            self.real_time_plot.x_data, self.real_time_plot.y_data, self.real_time_plot.y2_data = self.rolling_all.to_list(), self.y_tdoa_all, self.y_pdoa_all
            logger.info(f'生成pdoa_raw曲线 x: {self.rolling_all} y_tdoa_all：{self.y_tdoa_all} y_pdoa_all：{self.y_pdoa_all}')
            self.gui_data = self.gui_data[self.gui_data['rolling'] >= resu.index[0]]
            return True

    def update_combox(self):
        if not self.tagid2anchorid:
            return
        try:
            anchorid_set = sorted(set(self.tagid2anchorid[self.cur_tag_id]) | set(self.cur_anchor_id))
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

        logger.info(
            f'pdoa原始显示数据队列积压：{PdoaRawWidget.gui_queue.qsize()}, x轴最小值{self.rolling_all[0] if len(self.rolling_all) > 0 else None}，x轴长度：{len(self.rolling_all)}，tagid数量：{len(self.tag_id_set)}')

    def reset_check(self, pkgs):
        in_max_rolling = max(pkgs['rolling'])  # 收到待展示的一批数据的最大滚码
        with self.lock:
            if len(self.rolling_all) == 0:
                logger.warning(f'self.plot_distance=0')
                return False
            max_rolling = self.rolling_all[-1]
            # logger.info(f'in_max_rolling: {in_max_rolling}, max_rolling:{max_rolling}')
            if max_rolling - in_max_rolling < config['rolling_max_interval']:
                return False
            self.gui_data = []
            self.cur_tag_id = self.cur_anchor_id = None
            return True

    def show(self, dataBuffer):
        TDOALimit = config['pdoa_raw']['TDOALimit']
        i = np.array(dataBuffer)
        cur_anchor_id = list(self.cur_anchor_id)
        dataslice = np.zeros((len(cur_anchor_id), 6)) + np.nan
        for j in range(len(cur_anchor_id)):
            if np.any(np.logical_and(i[:, 1] == cur_anchor_id[j], i[:, 2] == self.cur_tag_id)):
                dataslice[j, :] = i[np.logical_and(i[:, 1] == cur_anchor_id[j], i[:, 2] == self.cur_tag_id), :]
        if(np.all(np.logical_not(np.isfinite(dataslice)))):
            return None, None
        TOA = dataslice[:, 3]
        POA_SYNC = dataslice[:, 4]
        POA_REPLY = dataslice[:, 5]
        POA_SYNC = np.exp(POA_SYNC*2j*np.pi/256)
        POA_REPLY = np.exp(POA_REPLY*2j*np.pi/256)
        TDOA = np.mod(32768 + TOA-TOA[0], 65536)-32768
        TDOA = TDOA * 3e8/(499.2e6*128)
        TDOA[abs(TDOA) > TDOALimit] = TDOA[abs(TDOA) > TDOALimit] * TDOALimit/abs(TDOA[abs(TDOA) > TDOALimit])  # 限幅
        PDOA_SYNC = POA_SYNC*np.conj(POA_SYNC[0])
        PDOA_REPLY = POA_REPLY*np.conj(POA_REPLY[0])
        PDOA = PDOA_SYNC+PDOA_REPLY
        PDOA = PDOA/np.abs(PDOA)
        return PDOA[None, :], TDOA[None, :]

    def run(self):
        gui_queue = self.gui_queue
        logger.info(f'处理pdoa原始数据 gui数据线程启动, {gui_queue.qsize()}')
        while True:
            pkgs = gui_queue.get()
            while not gui_queue.empty() and len(pkgs) < 10000:
                pkgs += gui_queue.get(block=False)
                QApplication.processEvents()
            pkgs = pd.DataFrame(pkgs, columns=['rolling', 'AnchorId', 'TagID', 'TOA', 'POA_SYNC', 'POA_REPLY'])
            if len(pkgs) == 0:
                continue

            incr = True
            if self.reset_check(pkgs):
                incr = False
                logger.warning(f'pdoa raw gui重新更新')
            else:
                # 剔除滚码小于当前x轴最小值的数据
                min_rolling = self.rolling_all[0] if len(self.rolling_all) > 0 else 0
                pkgs = pkgs[pkgs['rolling'] > min_rolling]
                if len(pkgs) == 0:
                    continue

            self.gui_data = pd.concat([self.gui_data, pkgs], axis=0) if len(self.gui_data) > 0 else pkgs

            # 每3秒更新下拉列表
            if self.cur_tag_id is None or time.time() - self.last_update_tagid_time > 5:
                with self.lock:
                    need_emit = self.cur_tag_id is None
                    if self.cur_tag_id is None:
                        self.cur_tag_id = self.gui_data['TagID'][0]

                    self.tag_id_set = set(self.gui_data['TagID'])
                    if self.cur_tag_id:
                        self.tag_id_set.add(self.cur_tag_id)

                    # 关联每个tagid对应的anchorid列表
                    self.tagid2anchorid = {elem: list(set(self.gui_data[self.gui_data['TagID'] == elem]['AnchorId'])) for elem in self.tag_id_set}
                    if not self.cur_anchor_id:
                        self.cur_anchor_id = set(self.tagid2anchorid[self.cur_tag_id][:4])
                    logger.info(f'self.tagid2anchorid={self.tagid2anchorid}')
                    if need_emit:
                        self.update_combox_signal.emit()
                    self.last_update_tagid_time = time.time()
            self.generate_distance_data_curve(pkgs, incr)
