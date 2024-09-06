import logging
import queue
import struct
import threading
from time import time

import numpy as np
import csv
import os
from common.common import get_header, save
from common.cnt_queue import CntQueue as Queue


class Tof2011:
    PROTO_ID = 0x2011
    # NAME = os.path.join(out_file_dir, 'TOF距离集中上传')
    history_data = dict()
    lock = threading.Lock()
    fieldnames = ['rolling', 'AnchorId', 'TagID', 'Distance', 'RXL', 'FPL']
    # csv_file = open(f'{NAME}.csv', 'a', newline='', encoding='utf-8')
    # writer = csv.writer(csv_file)
    gui_data = []
    save_queue = Queue()
    # t = None

    @staticmethod
    def save(pkgs):
        return Tof2011.save_queue.put(pkgs)

    @staticmethod
    def init(out_file_dir):
        Tof2011.NAME = os.path.join(out_file_dir, 'TOF距离集中上传')
        Tof2011.csv_file = open(f'{Tof2011.NAME}.csv', 'a', newline='', encoding='utf-8')
        Tof2011.writer = csv.writer(Tof2011.csv_file)
        Tof2011.t = threading.Thread(target=save, args=(Tof2011.writer, Tof2011.save_queue, Tof2011.csv_file), daemon=True)
        Tof2011.t.start()
        header = get_header(f'{Tof2011.NAME}.csv')
        if not header:
            Tof2011.writer.writerow(Tof2011.fieldnames)

    @staticmethod
    def get_rolling(value):
        return struct.unpack("H", value[2:4])[0]

    # 去重
    @staticmethod
    def deduplication(rolling, tag_id, anchorid):
        # Tof2011.history_data = {rolling: value for rolling, value in Tof2011.history_data.items() if value['timestamp'] > (time() - 5)}
        # with Tof2011.lock:
        if rolling in Tof2011.history_data:
            if tag_id in Tof2011.history_data[rolling]:
                if anchorid in Tof2011.history_data[rolling][tag_id]:
                    return True
                else:
                    Tof2011.history_data[rolling][tag_id].add(anchorid)
            else:
                Tof2011.history_data[rolling][tag_id] = {anchorid}
        else:
            Tof2011.history_data[rolling] = {tag_id: {anchorid}}
        # Tof2011.history_data[rolling]['timestamp'] = time()
        return False

    # 删除过期的历史数据
    @staticmethod
    def delete_old_history_data(interval=60):
        with Tof2011.lock:
            Tof2011.history_data = {rolling: value for rolling, value in Tof2011.history_data.items(
            ) if value['timestamp'] > (time() - interval)}

    @staticmethod
    def parase(length, value):
        Source_ID, rolling, net_code, anchor = struct.unpack("4H", value[:8])
        N = (length - 8) // 6
        tag_id0_LO, tag_id0_HI, Distance_LO, Distance_HI, RXL, FPL = np.frombuffer(value[8:8 + 6 * N],
                                                                                   dtype=np.uint8).reshape((6, -1), order="F")
        tag_id0 = (tag_id0_HI * 256.0 + tag_id0_LO).astype(np.uint16)
        distance = (Distance_HI * 256.0 + Distance_LO).astype(np.uint32)
        distance2 = distance.copy()
        distance2[distance > 32768] = (distance[distance > 32768] - 32768) * 10
        distance2[distance > 49152] = (distance[distance > 49152] - 49152) * 100
        distance = distance2
        ret = [N * [rolling], N * [anchor],
               tag_id0.tolist(), distance.tolist(), RXL.tolist(), FPL.tolist()]

        ret = list(filter(lambda x: not Tof2011.deduplication(
            x[0], x[2], x[1]), zip(*ret)))
        return ret if ret else None
