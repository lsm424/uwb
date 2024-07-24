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
from gui.common import *
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas


# 画图
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
        # 在 Figure 上添加一个子图
        self.figure.subplots(1, 1, gridspec_kw={'hspace': 0.5})
        self.ax = self.figure.axes[0]
        self.ax.grid()
        self.ax.set_title('pdoa angle')
        self.lines = self.ax.plot([], [])[0]

        # 定时器，每隔一段时间更新图表
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(300)  # 每1000毫秒（1秒）更新一次

    def update_plot(self):
        # 模拟数据更新
        if len(self.x_data) == 0:
            return

        self.lines.set_xdata(self.x_data)
        self.lines.set_ydata(self.y_data)

        # 自动调整坐标轴范围
        self.ax.relim()
        self.ax.autoscale_view()

        # 刷新画布
        self.canvas.draw()

# pdoa角度数据


class PdoaAngleWidget(QWidget):

    gui_queue = Queue()
    update_combox_signal = Signal()

    def __init__(self):
        super().__init__()

        self.TDOALimit = config['pdoa_angle']['TDOALimit']
        self.filtwindow = config['pdoa_angle']['filtwindow']
        self.dispBufferSize = config['pdoa_angle']['dispBufferSize']
        self.Anchors = config['pdoa_angle']['Anchors']
        self.ElectLen = config['pdoa_angle']['ElectLen']
        self.ZeroPoint = config['pdoa_angle']['ZeroPoint']
        self.PhaseOffset = config['pdoa_angle']['PhaseOffset']
        self.Freq = config['pdoa_angle']['Freq']

        self.filtBufferLock = threading.Lock()
        self.filtBuffer = {}
        self.lock = threading.Lock()
        self.last_update_tagid_time = 0
        self.gui_data = []
        self.cur_tag_id = None
        self.rolling_all = np.array([])
        self.y_tdoa_all = np.array([])
        self.y_pdoa_all = np.array([])
        self.main_layout = QVBoxLayout(self)
        self.main_layout.addSpacing(10)
        # 顶部下拉框
        self.tag_id_combox = QComboBox()
        self.tag_id_combox.currentIndexChanged.connect(self.tagid_selection_changed)

        up_layout = QHBoxLayout()
        up_layout.addSpacing(100)
        up_layout.addWidget(QLabel('tagid选择：'))
        up_layout.addWidget(self.tag_id_combox)
        up_layout.addSpacing(400)
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
            self.cur_tag_id = int(cur_tag_id)

            # 更新gui显示数据
            logger.info(f'tof tagid选择变动：{self.cur_tag_id}, tag数量：{self.tag_id_combox.count()}')

        self.generate_distance_data_curve(self.gui_data, False)

    def generate_distance_data_curve(self, pkgs, incr=True):
        cur_anchorid = config['pdoa_angle']['Anchors']
        with self.lock:
            if not cur_anchorid or len(cur_anchorid) != 4:
                logger.info(f'pdoa角度 计算曲线 要4个anchorid，目前为：{cur_anchorid}')
                return False

            pkgs.to_csv('pdoa_agnle_test.csv', index=False)
            resu = pkgs.groupby(by='rolling').apply(lambda x: self.show(x))
            if len(resu.values) == 0: return False
            try:
                resu = np.concatenate(resu.values, 0)
            except BaseException as e:
                logger.error(f'err: {e}, resu: {resu.values}')
                return False
            resu = pd.DataFrame(resu, columns=['tag', 'rolling', 'aoa'])
            # logger.info(f'resu: {resu}')
            resu = resu.groupby(by='tag')
            min_rolling = 0
            for tag, v in resu:
                # logger.info(f'tag:{tag}，v: {v}')
                if tag == self.cur_tag_id:
                    v = v[-self.dispBufferSize:]
                    self.real_time_plot.x_data, self.real_time_plot.y_data = v['rolling'], v['aoa']
                    min_rolling = min(v['rolling'])

            logger.info(f'生成pdoa_angle曲线 x: {self.real_time_plot.x_data} y_all：{self.real_time_plot.y_data}')
            self.gui_data = self.gui_data[self.gui_data['rolling'] >= min_rolling]
            return True

    def update_combox(self):
        if not self.cur_tag_id:
            return
        tag_id_list = list(map(lambda x: str(x), sorted(self.tag_id_set)))
        self.tag_id_combox.blockSignals(True)
        self.tag_id_combox.clear()
        self.tag_id_combox.addItems(tag_id_list)
        self.tag_id_combox.setCurrentText(str(self.cur_tag_id))
        self.tag_id_combox.blockSignals(False)

        logger.info(
            f'pdoa角度显示数据队列积压：{PdoaAngleWidget.gui_queue.qsize()}, x轴最小值{self.rolling_all[0] if len(self.rolling_all) > 0 else None}，x轴长度：{len(self.rolling_all)}，tagid数量：{len(self.tag_id_set)}')

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
            self.cur_tag_id = None
            return True

    def show(self, dataBuffer):
        frame = np.array(dataBuffer)
        ret = []
        for tag in np.unique(frame[:, 2]):
            dataslice = np.zeros((len(self.Anchors), 6)) + np.nan
            for j in range(len(self.Anchors)):
                if np.any(np.logical_and(frame[:, 1] == self.Anchors[j], frame[:, 2] == tag)):
                    dataslice[j, :] = frame[np.logical_and(frame[:, 1] == self.Anchors[j], frame[:, 2] == tag), :]
            if(np.any(np.isfinite(dataslice))):
                POA_SYNC = dataslice[:, 4]
                POA_REPLY = dataslice[:, 5]
                POA_SYNC = np.exp(POA_SYNC*2j*np.pi/256)
                POA_REPLY = np.exp(POA_REPLY*2j*np.pi/256)

                PDOA_SYNC = POA_SYNC*np.conj(POA_SYNC[0])
                PDOA_REPLY = POA_REPLY*np.conj(POA_REPLY[0])
                PDOA = PDOA_SYNC+PDOA_REPLY
                PDOA = PDOA/np.abs(PDOA)

                PDOA_CAL = PDOA * np.exp(1j*np.pi/180 * np.array(self.PhaseOffset)[None, ...])
                pdoa = abs(np.fft.fft(PDOA_CAL, 1024, axis=1))

                with self.filtBufferLock:
                    if tag not in self.filtBuffer:
                        self.filtBuffer[tag] = []
                    self.filtBuffer[tag].append(pdoa[None, ...])
                    self.filtBuffer[tag] = self.filtBuffer[tag][-self.filtwindow:]
                pdoa = np.nanmean(np.concatenate(self.filtBuffer[tag], 0), 0)
                aoa = np.mod(0.5+np.argmax(pdoa, 1)/1024, 1)-0.5
                aoa = aoa / (self.ElectLen / (3e11/self.Freq))
                aoa[np.abs(aoa) > 1] = aoa[np.abs(aoa) > 1]/np.abs(aoa[np.abs(aoa) > 1])  # 限幅到-1~1
                aoa_cal = np.arcsin(aoa)*180/np.pi
                aoa_cal = np.arcsin(np.sin((aoa_cal + self.ZeroPoint)*np.pi/180))*180/np.pi
                # if tag not in self.dataBuffer:self.dataBuffer[tag]=[]
                ret.append([tag, frame[0, 0], aoa_cal[0]])
        return ret

    def run(self):
        gui_queue = self.gui_queue
        logger.info(f'处理pdoa角度数据 gui数据线程启动, {gui_queue.qsize()}')
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
                    if need_emit:
                        self.update_combox_signal.emit()
                    self.last_update_tagid_time = time.time()
                    logger.info(f'pdoa angle cur_tag_id：{self.cur_tag_id}')

            self.generate_distance_data_curve(pkgs, incr)
