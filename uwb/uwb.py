# encoding=utf-8
import os
import pickle
import queue
import signal
import sys
import threading
import multiprocessing
import datetime
from itertools import groupby, chain
from common.common import logger, config
from access.access import create_access
from time import time, sleep
from uwb.TLV import Tlv
import pydblite

from uwb.sensor_300d import Sensor300d
from uwb.tof_2011 import Tof2011
from uwb.cir_2121 import Cir2121
from uwb.tod_4090 import Tod4090
from uwb.slot_2042 import Slot2042

# Uwb整体逻辑


class Uwb:
    def __init__(self, sensor_gui_queue: multiprocessing.Queue, tof_gui_queue: multiprocessing.Queue):

        self._save_queue = multiprocessing.Queue()
        self.parase_queue = [multiprocessing.Queue()
                             for i in range(config['parase_worker_cnt'])]
        self.p = []
        for i in range(config['parase_worker_cnt']):
            p = multiprocessing.Process(target=Uwb.parase_tlv_proc, args=(
                self.parase_queue[i], self._save_queue, sensor_gui_queue, tof_gui_queue, Sensor300d.save_queue, Tof2011.save_queue, i))
            p.start()
            self.p.append(p)

        out_file_dir = os.path.join(
            'out_file', datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S'))
        if not os.path.exists(out_file_dir):
            os.makedirs(out_file_dir)
        logger.info(f'文件输出路径：{out_file_dir}')
        self.pickle_file = open(os.path.join(
            out_file_dir, 'pickle_file.dat'), 'ab')
        Tof2011.init(out_file_dir)
        Sensor300d.init(out_file_dir)
        Cir2121.init(out_file_dir)
        Tod4090.init(out_file_dir)
        Slot2042.init(out_file_dir)

        self.sensor_queue = sensor_gui_queue
        self.tof_queue = tof_gui_queue
        self.pickle_cnt = 0
        self.access = create_access()
        self.lock = threading.Lock()
        self.cache = pydblite.Base(':memory:')
        self.cache.create('rolling', 'timestamp', 'tlv_list')
        self.cache.create_index('rolling', 'timestamp')

        self.threads = []
        self.threads.append(threading.Thread(
            target=self.delete_aggregate, daemon=True))
        self.threads.append(threading.Thread(
            target=self.access_read_thread, daemon=True))
        self.threads.append(threading.Thread(
            target=self.statistic, daemon=True))
        self.threads.append(threading.Thread(
            target=self.save_tlv_thread, daemon=True))
        list(map(lambda x: x.start(), self.threads))

    def join(self):
        list(map(lambda x: x.join(), self.threads))

    def exit(self):
        list(map(lambda x: os.kill(x.pid,  signal.SIGTERM), self.p))
        os.kill(os.getpid(), signal.SIGTERM)

    def statistic(self):
        while True:
            logger.info(f'解析tlv速度：{self.access.cnt}/s, 待汇聚队列积压: {self.access.qsize()}, 解析测量值队列积压: {sum(map(lambda x: x.qsize(), self.parase_queue))}, 待序列化文件队列积压: {self._save_queue.qsize()}，已写入pickle_data：{self.pickle_cnt}条, sensor写csv队列积压：{Sensor300d.save_queue.qsize()}, tof写csv队列积压：{Tof2011.save_queue.qsize()} dbsize:{sys.getsizeof(self.cache)},{len(self.cache)}')
            self.access.cnt = 0
            # Sensor300d.delete_old_history_data(60)
            # Tof2011.delete_old_history_data(60)
            self.pickle_file.flush()
            Tof2011.csv_file.flush()
            Sensor300d.csv_file.flush()
            sleep(1)

    # 主流程
    def access_read_thread(self):
        logger.info(f'启动线程')
        while True:
            # 接收一帧数据
            tlv = self.access.get_data()
            # 汇聚
            with self.lock:
                ret = self.cache(rolling=tlv.rolling)
                if not ret or (time() - ret[0]['timestamp'] > 0.2):
                    if ret:
                        self.parase_queue[tlv.rolling % config['parase_worker_cnt']].put(
                            ret[0]['tlv_list'])
                        self.cache.delete(ret[0])
                    self.cache.insert(rolling=tlv.rolling,
                                      timestamp=time(), tlv_list=[tlv])
                else:
                    ret[0]['tlv_list'].append(tlv)

    # 周期删除汇聚结果
    def delete_aggregate(self):
        logger.info(f'启动汇聚结果过期删除线程')
        while True:
            sleep(0.2)
            with self.lock:
                rows = self.cache('timestamp') < (time() - 0.3)
                list(map(lambda x: self.cache.delete(x), rows))

    @staticmethod
    def parase_tlv_proc(parase_queue, save_queue, sensor_gui_queue, tof_gui_queue, sensor_queue, tof_queue, i):
        logger.info(f'启动解析tlv测量值进程, {i}')
        while True:
            tlv_list = parase_queue.get()
            tlv_list = filter(lambda x: x.result, map(
                lambda x: x.parase(), tlv_list))

            

            tof_csv_data, sensor_csv_data, pickle_data = [], [], []
            for tlv in tlv_list:
                if tlv.proto_type == Sensor300d.PROTO_ID:
                    if config['gui']:
                        sensor_gui_queue.put(tlv.result)
                    sensor_csv_data += tlv.result
                elif tlv.proto_type == Tof2011.PROTO_ID:
                    if config['gui']:
                        tof_gui_queue.put(tlv.result)
                    tof_csv_data += tlv.result
                pickle_data.append(tlv.pickle_data)

            save_queue.put(pickle_data)
            sensor_queue.put(sensor_csv_data)
            tof_queue.put(tof_csv_data)

    def save_tlv_thread(self):
        logger.info(f'启动pickle数据保存线程')
        while True:
            pkgs = self._save_queue.get()
            while not self._save_queue.empty() and len(pkgs) < 2000:
                pkgs += self._save_queue.get(block=False)
            list(map(lambda x: self.pickle_file.write(pickle.dumps(x)), pkgs))
            self.pickle_cnt += len(pkgs)
