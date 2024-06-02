import logging
import queue
import struct
import threading
from time import time

import numpy as np
import csv
from common.common import get_header, save



class Tof2011:
    PROTO_ID = 0x2011
    NAME = 'out_file/TOF距离集中上传'
    history_data = dict()
    lock = threading.Lock()
    fieldnames = ['rolling', 'AnchorId', 'TagID', 'Distance', 'RXL', 'FPL']
    csv_file = open(f'{NAME}.csv', 'a', newline='', encoding='utf-8')
    writer = csv.writer(csv_file)
    gui_data = []
    save_queue = queue.Queue()
    t = threading.Thread(target=save, args=(writer, save_queue, csv_file), daemon=True)
    t.start()

    @staticmethod
    def save(pkgs):
        return Tof2011.save_queue.put(pkgs)

    def __init__(self):
        header = get_header(f'{self.NAME}.csv')
        if not header:
            Tof2011.writer.writerow(self.fieldnames)

    @staticmethod
    def get_rolling(value):
        return struct.unpack("H", value[2:4])[0]

    # 去重
    @staticmethod
    def deduplication(rolling, tag_id, anchorid):
        with Tof2011.lock:
            if rolling in Tof2011.history_data:
                if tag_id in Tof2011.history_data[rolling]:
                    if anchorid in Tof2011.history_data[rolling][tag_id]:

                        return True
                    else:
                        Tof2011.history_data[rolling][tag_id].add(anchorid)
                else:
                    Tof2011.history_data[rolling][tag_id] = set()
            else:
                Tof2011.history_data[rolling] = {tag_id: set()}
            Tof2011.history_data[rolling]['timestamp'] = time()
            return False

    # 删除过期的历史数据
    @staticmethod
    def delete_old_history_data(interval=60):
        with Tof2011.lock:
            Tof2011.history_data = {rolling: value for rolling, value in Tof2011.history_data.items() if value['timestamp'] > (time() - interval)}


    @staticmethod
    def parase(length, value):
        Source_ID, rolling, net_code, anchor = struct.unpack("4H", value[:8])
        N = (length - 8) // 6
        tag_id0_LO, tag_id0_HI, Distance_LO, Distance_HI, RXL, FPL = np.frombuffer(value[8:8 + 6 * N],
                                                                                   dtype=np.uint8).reshape((6, -1), order="F")
        tag_id0 = (tag_id0_HI * 256.0 + tag_id0_LO).astype(np.uint16)
        distance = (Distance_HI * 256.0 + Distance_LO).astype(np.uint16)
        ret = [N * [rolling], N * [anchor], tag_id0.tolist(), distance.tolist(), RXL.tolist(), FPL.tolist()]

        ret = list(filter(lambda x: not Tof2011.deduplication(x[0], x[2], x[1]), zip(*ret)))
        return ret if ret else None
        # ret = {
        #     "rolling": N * [rolling],
        #     "AnchorId": N * [anchor],
        #     "TagID": tag_id0.tolist(),
        #     "Distance": Distance.tolist(),
        #     "RXL": RXL.tolist(),
        #     "FPL": FPL.tolist(),
        # }
