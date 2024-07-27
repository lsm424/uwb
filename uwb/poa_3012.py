import csv
import queue
import threading
import os
from common.common import get_header, save
import struct
import time
import pandas
import numpy as np
import multiprocessing


class Poa3012:
    PROTO_ID = 0x3012
    fieldnames = ['rolling', 'AnchorId', 'TagID', 'Dist_mm', 'POA_deg', 'timestampe']
    save_queue = multiprocessing.Queue()

    @staticmethod
    def save(pkgs):
        return Poa3012.save_queue.put(pkgs)

    @staticmethod
    def init(out_file_dir):
        Poa3012.NAME = os.path.join(out_file_dir, '载波相位测距集中上传')
        Poa3012.csv_file = open(f'{Poa3012.NAME}.csv', 'a', newline='', encoding='utf-8')
        Poa3012.writer = csv.writer(Poa3012.csv_file)
        Poa3012.t = threading.Thread(target=save, args=(Poa3012.writer, Poa3012.save_queue, Poa3012.csv_file), daemon=True)
        Poa3012.t.start()
        header = get_header(f'{Poa3012.NAME}.csv')
        if not header:
            Poa3012.writer.writerow(Poa3012.fieldnames)

    # def __del__(self):
    #     Cir2121.csv_file.close()

    @staticmethod
    def get_rolling(value):
        return struct.unpack("H", value[2:4])[0]

    @staticmethod
    def parase(length, value):
        source_id, rolling, frequency, anc_id0 = struct.unpack(
            "4H", value[:8])
        N = (len(value)-8)//10
        data = np.frombuffer(
            value[8:8 + 10 * N], dtype=np.uint16).reshape((5, -1), order='F')
        data = data[:, data[3, :] < 360]
        tag_id0 = data[0, :]
        dist = np.reshape((1, 65536), (1, 2)) @ (data[1:3, :].astype(np.uint32))
        poa = data[3, :]
        rxlfpl = data[4, :]
        dist_mm = dist.astype(np.uint32)
        # preamble,totalLen,type,length = struct.unpack()
        ret = [N * [rolling],  N * [anc_id0], tag_id0.tolist(), dist_mm.flatten().tolist(), poa.tolist(), N * [time.time()]]
        ret = list(zip(*ret))
        return ret
