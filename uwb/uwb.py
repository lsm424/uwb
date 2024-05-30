#encoding=utf-8
import pickle
import queue
import threading
import multiprocessing
from itertools import groupby, chain
from gui.tof2011 import Tof2011Widght
from common.common import logger, config, pickle_file
from access.access import create_access
from time import time, sleep
from uwb.TLV import Tlv
import pydblite

from uwb.sensor_300d import Sensor300d



# Uwb整体逻辑
class Uwb:
    def __init__(self, sensor_queue: multiprocessing.Queue):
        self.sensor_queue = sensor_queue
        parase_queue = queue.Queue()
        out_csv_queue = queue.Queue()
        # for i in range(1):
        #     p = threading.Thread(target=self.parase_proc, args=(parase_queue, out_csv_queue, i,), daemon=True)
        #     p.start()
        self.access = create_access()
        self.lock = threading.Lock()
        self.cache = pydblite.Base(':memory:')
        self.cache.create('rolling', 'timestamp', 'tlv_list')
        self.cache.create_index('rolling', 'timestamp')

        # executor = ProcessPoolExecutor(max_workers=1)
        # self.r = list(map(lambda x: executor.submit(self.parase_proc, self.queue, self.out_csv_queue, x), range(2)))
        self.threads = [threading.Thread(target=self.save_file, args=(out_csv_queue,), daemon=True)]
        self.threads.append(threading.Thread(target=self.push_aggregate, args=(out_csv_queue, ), daemon=True))
        self.threads.append(threading.Thread(target=self.access_read_thread, args=(out_csv_queue, ), daemon=True))
        self.threads.append(threading.Thread(target=self.statistic, args=(parase_queue, out_csv_queue), daemon=True))
        list(map(lambda x: x.start(), self.threads))

    def join(self):
        list(map(lambda x: x.join(), self.threads))

    def statistic(self, inqueue, out_csv_queue):
        while True:
            logger.info(f'access_queue_size: {self.access.qsize()}, parase queue size: {inqueue.qsize()}, out_csv_queue: {out_csv_queue.qsize()} ')
            Sensor300d.delete_old_history_data(60)
            sleep(5)

    # 主流程
    def access_read_thread(self, out_csv_queue):
        logger.info(f'启动线程')
        while True:
            # 接收一帧数据
            data, addr, timestampe = self.access.get_data()
            tlv = Tlv(data, addr, timestampe)
            # tlv解析头部字段
            if not tlv.pre_parase():
                continue
            # tlv.parase()
            # logger.info(f'{tlv.result[0][0]} {tlv.result[0][1]} {tlv.result[0][2]}')
            # 汇聚
            with self.lock:
                ret = self.cache(rolling=tlv.rolling)
                if not ret or (time() - ret[0]['timestamp'] > 0.2):
                    if ret:
                        out_csv_queue.put(ret[0]['tlv_list'])
                        self.cache.delete(ret[0])
                    self.cache.insert(rolling=tlv.rolling, timestamp=time(), tlv_list=[tlv])
                else:
                    ret[0]['tlv_list'].append(tlv)
            # 汇聚
            # tlv_pkgs = self.rolling_converge.add(tlv)
            # if not tlv_pkgs:
            #     # sleep(0.2)
            #     continue
            # self.aggregate(tlv)
            # list(map(lambda x: queue.put(x), tlv_pkgs))
            # logger.info(f'handle one {tlv.rolling} {id(tlv)} {queue.qsize()}')

    # 周期推送汇聚结果
    def push_aggregate(self, out_csv_queue):
        logger.info(f'启动汇聚结果推送线程')
        while True:
            sleep(0.2)
            with self.lock:
                rows = self.cache('timestamp') < (time() - 0.2)
                list(map(lambda x: (out_csv_queue.put(x['tlv_list']), self.cache.delete(x)), rows))

    def parase_proc(self, parase_queue, out_csv_queue, i):
        logger.info(f'启动tlv解析子进程{i}')

        while True:
            tlv_pkgs = parase_queue.get()
            list(map(lambda x: x.parase(), tlv_pkgs))
            tlv_pkgs = list(filter(lambda x: x.result, tlv_pkgs))
            if not tlv_pkgs:
                continue
            # 并行解析测量值
            # Parallel(n_jobs=-1, backend='multiprocessing')(delayed(tlv.parase)() for tlv in tlv_pkgs)
            out_csv_queue.put(tlv_pkgs)

    def save_file(self, out_csv_queue):
        logger.info(f'启动保存文件子线程')
        while True:
            # 汇总一批汇聚后的包进行解析
            pkgs = out_csv_queue.get()
            while not out_csv_queue.empty() and len(pkgs) < 500:
                pkgs += out_csv_queue.get(block=False)
            pkgs = filter(lambda x: x.result, map(lambda x: x.parase(), pkgs))

            # 按照协议分别写入对应的csv文件
            pickle_data = []
            pkgs = sorted(pkgs, key=lambda x: x.proto_type)
            for proto_type, pkgs in groupby(pkgs, key=lambda x: x.proto_type):
                csv_data = list(chain(*chain(map(lambda x: x.result, pkgs))))
                Tlv.proto_handler[proto_type].save(csv_data)
                if proto_type == Sensor300d.PROTO_ID:
                    list(map(lambda x: self.sensor_queue.put(x), csv_data))
                    # logger.info(f'推送传感器数据{len(csv_data)}')
                pickle_data += list(map(lambda x: x.pickle_data, pkgs))

            # pickle写文件
            pickle_file.write(pickle.dumps(pickle_data))
            pickle_file.flush()
