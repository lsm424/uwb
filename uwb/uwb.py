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
from gui.sensor300d import Sensor300dWidght
from gui.tof2011 import Tof2011Widght
from uwb.sensor_300d import Sensor300d
from uwb.tof_2011 import Tof2011
from uwb.cir_2121 import Cir2121
from uwb.tod_4090 import Tod4090
from uwb.slot_2042 import Slot2042

# Uwb整体逻辑


class Uwb:
    def __init__(self):

        self._save_queue = multiprocessing.Queue()
        self.parase_queue = [multiprocessing.Queue()
                             for i in range(config['parase_worker_cnt'])]
        self.p = []
        for i in range(config['parase_worker_cnt']):
            p = multiprocessing.Process(target=Uwb.parase_tlv_proc, args=(
                self.parase_queue[i], self._save_queue, Sensor300dWidght.gui_queue, Tof2011Widght.gui_queue, Sensor300d.save_queue, Tof2011.save_queue, Cir2121.save_queue, Slot2042.save_queue, Tod4090.save_queue, i))
            p.start()
            self.p.append(p)

        out_file_dir = os.path.join('out_file', datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S'))
        if not os.path.exists(out_file_dir):
            os.makedirs(out_file_dir)
        logger.info(f'文件输出路径：{out_file_dir}, 进程号：{os.getpid()}')
        open('uwb.dat', 'w+').write(str(os.getpid()))
        self.pickle_file = open(os.path.join(out_file_dir, 'pickle_file.dat'), 'ab')
        Tof2011.init(out_file_dir)
        Sensor300d.init(out_file_dir)
        Cir2121.init(out_file_dir)
        Tod4090.init(out_file_dir)
        Slot2042.init(out_file_dir)

        self.pickle_cnt = 0
        self.access = create_access()
        self.lock = threading.Lock()
        self.cache = pydblite.Base(':memory:')
        self.cache.create('rolling', 'timestamp', 'tlv_list')
        self.cache.create_index('rolling', 'timestamp')

        self.threads = []
        # self.threads.append(threading.Thread(
        #     target=self.delete_aggregate, daemon=True))
        self.threads.append(threading.Thread(target=self.access_read_thread, daemon=True))
        self.threads.append(threading.Thread(target=self.statistic, daemon=True))
        self.threads.append(threading.Thread(target=self.save_tlv_thread, daemon=True))
        list(map(lambda x: x.start(), self.threads))

    def join(self):
        list(map(lambda x: x.join(), self.threads))

    def exit(self):
        list(map(lambda x: os.kill(x.pid,  signal.SIGTERM), self.p))
        os.kill(os.getpid(), signal.SIGTERM)

    def reset_access(self):
        self.access.close()
        self.access = create_access()

    def statistic(self):
        while True:
            logger.info(f'解析tlv速度：{int(self.access.cnt / 3)}/s, 待汇聚队列积压: {self.access.qsize()}, 解析测量值队列积压: {sum(map(lambda x: x.qsize(), self.parase_queue))}, 待序列化文件队列积压: {self._save_queue.qsize()}，已写入pickle_data：{self.pickle_cnt}条, sensor队列积压：{Sensor300d.save_queue.qsize()}, tof队列积压：{Tof2011.save_queue.qsize()}, cir队列积压：{Cir2121.save_queue.qsize()}, slot队列积压：{Slot2042.save_queue.qsize()}, Tod队列积压：{Tod4090.save_queue.qsize()}, dbsize: {len(self.cache)}')
            self.access.cnt = 0
            # Sensor300d.delete_old_history_data(60)
            # Tof2011.delete_old_history_data(60)
            self.pickle_file.flush()
            Tof2011.csv_file.flush()
            Sensor300d.csv_file.flush()
            Cir2121.csv_file.flush()
            Slot2042.csv_file.flush()
            Tod4090.csv_file.flush()
            sleep(3)

    # 主流程
    def access_read_thread(self):
        logger.info(f'启动线程')
        while True:
            # 接收一帧数据
            tlv = self.access.get_data()
            # if tlv.proto_type == Cir2121.PROTO_ID:
            #     tlv = tlv
            # 汇聚
            ret = self.cache(rolling=tlv.rolling)
            if not ret:
                self.cache.insert(rolling=tlv.rolling, timestamp=time(), tlv_list=[tlv])
            elif time() - ret[0]['timestamp'] > 0.2:
                idx = tlv.rolling % config['parase_worker_cnt']
                self.parase_queue[idx].put(ret[0]['tlv_list'])
                self.cache.delete(ret[0])
                # logger.warning(f'完成汇聚滚码{tlv.rolling}，往{idx}号分析进程推送{len(ret[0]["tlv_list"])}包')
            else:
                ret[0]['tlv_list'].append(tlv)

            rows = self.cache('timestamp') < (time() - 0.5)
            list(map(lambda x: (self.parase_queue[x['rolling'] % config['parase_worker_cnt']].put(x['tlv_list']),
                                self.cache.delete(x)), rows))
            # logger.warning(f'汇聚1包tlv {tlv.rolling}，已经积累{len(ret[0]["tlv_list"])}包')

    @staticmethod
    def parase_tlv_proc(parase_queue, save_queue, sensor_gui_queue, tof_gui_queue, sensor_queue, tof_queue, cir_queue, slot_queue, tod_queue, i):
        logger.info(f'启动解析tlv测量值进程{i}, pid:{os.getpid()}')
        while True:
            tlv_list = parase_queue.get()
            # logger.warning(f'{i} 处理{len(tlv_list)}包tlv')
            tlv_list = list(filter(lambda x: x.result, map(lambda x: x.parase(), tlv_list)))

            tof_csv_data, sensor_csv_data, cir_csv_data, slot_csv_data, tod_csv_data, pickle_data = [], [], [], [], [], []
            for tlv in tlv_list:
                if tlv.proto_type == Sensor300d.PROTO_ID:
                    sensor_csv_data += tlv.result
                elif tlv.proto_type == Tof2011.PROTO_ID:
                    tof_csv_data += tlv.result
                elif tlv.proto_type == Cir2121.PROTO_ID:
                    cir_csv_data += tlv.result
                elif tlv.proto_type == Slot2042.PROTO_ID:
                    slot_csv_data += tlv.result
                elif tlv.proto_type == Tod4090.PROTO_ID:
                    slot_csv_data += tlv.result

                pickle_data.append(tlv.pickle_data)

            if config['gui']:
                sensor_gui_queue.put(sensor_csv_data)
                tof_gui_queue.put(tof_csv_data)
            sensor_queue.put(sensor_csv_data)
            tof_queue.put(tof_csv_data)
            cir_queue.put(cir_csv_data)
            slot_queue.put(slot_csv_data)
            tod_queue.put(tod_csv_data)
            save_queue.put(pickle_data)

    def save_tlv_thread(self):
        logger.info(f'启动pickle数据保存线程')
        while True:
            pkgs = self._save_queue.get()
            while not self._save_queue.empty() and len(pkgs) < 2000:
                pkgs += self._save_queue.get(block=False)
            list(map(lambda x: self.pickle_file.write(pickle.dumps(x)), pkgs))
            self.pickle_cnt += len(pkgs)
