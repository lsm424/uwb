#encoding=utf-8
import os
import pickle
import queue
import signal
import sys
import threading
import multiprocessing
from itertools import groupby, chain
from common.common import logger, config
from access.access import create_access, Package
from time import time, sleep

# from joblib import Parallel, delayed
from uwb.TLV import Tlv
import pydblite

from uwb.sensor_300d import Sensor300d
from uwb.tof_2011 import Tof2011



# Uwb整体逻辑
class Uwb:
    def __init__(self, sensor_gui_queue: multiprocessing.Queue, tof_gui_queue: multiprocessing.Queue):

        self._save_queue = multiprocessing.Queue()
        parase_queue = multiprocessing.Queue()
        self.p = []
        # from concurrent.futures import ALL_COMPLETED, ProcessPoolExecutor, FIRST_COMPLETED, wait
        # self.executor = ProcessPoolExecutor(max_workers=2)
        # self.p = list(map(lambda x: self.executor.submit(self.parase_tlv_proc, parase_queue, self._save_queue, x), range(2)))
        for i in range(config['parase_worker_cnt']):
            p = multiprocessing.Process(target=Uwb.parase_tlv_proc, args=(parase_queue, self._save_queue, sensor_gui_queue, tof_gui_queue, Sensor300d.save_queue, Tof2011.save_queue , i))
            p.start()
            self.p.append(p)

        self.sensor_queue = sensor_gui_queue
        self.tof_queue = tof_gui_queue
        self.pickle_cnt = 0
        self.access = create_access()
        self.lock = threading.Lock()
        self.cache = pydblite.Base(':memory:')
        self.cache.create('rolling', 'timestamp', 'tlv_list')
        self.cache.create_index('rolling', 'timestamp')


        self.threads = []
        self.threads.append(threading.Thread(target=self.push_aggregate, args=(parase_queue, ), daemon=True))
        self.threads.append(threading.Thread(target=self.access_read_thread, args=(parase_queue, ), daemon=True))
        self.threads.append(threading.Thread(target=self.statistic, args=(parase_queue, ), daemon=True))
        self.threads.append(threading.Thread(target=self.save_tlv_thread, daemon=True))
        list(map(lambda x: x.start(), self.threads))

    def join(self):
        list(map(lambda x: x.join(), self.threads))

    def exit(self):
        list(map(lambda x: os.kill(x.pid,  signal.SIGTERM), self.p))
        os.kill(os.getpid(), signal.SIGTERM)

    def statistic(self, parase_queue):
        from common.common import pickle_file
        while True:
            logger.info(f'解析tlv速度：{self.access.cnt}/s, 待汇聚队列积压: {self.access.qsize()}, 解析测量值队列积压: {parase_queue.qsize()}, 待序列化文件队列积压: {self._save_queue.qsize()}，已写入pickle_data：{self.pickle_cnt}条, sensor写csv队列积压：{Sensor300d.save_queue.qsize()}, tof写csv队列积压：{Tof2011.save_queue.qsize()} dbsize:{sys.getsizeof(self.cache)},{len(self.cache)}')
            self.access.cnt = 0
            Sensor300d.delete_old_history_data(60)
            Tof2011.delete_old_history_data(60)
            pickle_file.flush()
            Tof2011.csv_file.flush()
            Sensor300d.csv_file.flush()
            sleep(1)

    # 主流程
    def access_read_thread(self, parase_queue):
        logger.info(f'启动线程')
        while True:
            # 接收一帧数据
            tlv = self.access.get_data()
            # 汇聚
            with self.lock:
                ret = self.cache(rolling=tlv.rolling)
                if not ret or (time() - ret[0]['timestamp'] > 0.2):
                    if ret:
                        parase_queue.put(ret[0]['tlv_list'])
                        self.cache.delete(ret[0])
                    self.cache.insert(rolling=tlv.rolling, timestamp=time(), tlv_list=[tlv])
                else:
                    ret[0]['tlv_list'].append(tlv)

    # 周期推送汇聚结果
    def push_aggregate(self, parase_queue):
        logger.info(f'启动汇聚结果推送线程')
        while True:
            sleep(0.2)
            with self.lock:
                rows = self.cache('timestamp') < (time() - 0.2)
                list(map(lambda x: (parase_queue.put(x['tlv_list']), self.cache.delete(x)), rows))

    @staticmethod
    def parase_tlv_proc(parase_queue, save_queue, sensor_gui_queue, tof_gui_queue, sensor_queue, tof_queue, i):
        logger.info(f'启动解析tlv测量值进程, {i}')
        while True:
            tlv_list = parase_queue.get()
            tlv_list = filter(lambda x: x.result, map(lambda x: x.parase(), tlv_list))

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

            # pickle_data = list(map(lambda x: x.pickle_data, tlv_list))
            save_queue.put(pickle_data)
            sensor_queue.put(sensor_csv_data)
            tof_queue.put(tof_csv_data)

    def save_tlv_thread(self):
        from common.common import pickle_file
        logger.info(f'启动pickle数据保存线程')
        while True:
            pkgs = self._save_queue.get()
            while not self._save_queue.empty() and len(pkgs) < 2000:
                pkgs += self._save_queue.get(block=False)
            list(map(lambda x: pickle_file.write(pickle.dumps(x)), pkgs))
            self.pickle_cnt += len(pkgs)
