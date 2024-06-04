import csv
import queue
import threading
import os
from common.common import get_header, save
import struct
import pandas
import numpy as np
import multiprocessing


class Cir2121:

    PROTO_ID = 0x2121
    # NAME = os.path.join(out_file_dir, 'CIR相位集中上传')
    # csv_file = open(f'{NAME}.csv', 'a', newline='', encoding='utf-8')
    fieldnames = ['rolling', 'TagID', 'AnchorIdx',
                  'IQ', 'sync_time', 'reply_time']
    # writer = csv.writer(csv_file)
    save_queue = multiprocessing.Queue()
    # t = threading.Thread(target=save, args=(writer, save_queue, csv_file), daemon=True)
    # t.start()

    @staticmethod
    def save(pkgs):
        return Cir2121.save_queue.put(pkgs)

    @staticmethod
    def init(out_file_dir):
        Cir2121.NAME = os.path.join(out_file_dir, 'CIR相位集中上传')
        Cir2121.csv_file = open(
            f'{Cir2121.NAME}.csv', 'a', newline='', encoding='utf-8')
        Cir2121.writer = csv.writer(Cir2121.csv_file)
        Cir2121.t = threading.Thread(target=save, args=(
            Cir2121.writer, Cir2121.save_queue, Cir2121.csv_file), daemon=True)
        Cir2121.t.start()
        header = get_header(f'{Cir2121.NAME}.csv')
        if not header:
            Cir2121.writer.writerow(Cir2121.fieldnames)

    # def __del__(self):
    #     Cir2121.csv_file.close()

    @staticmethod
    def get_rolling(value):
        return struct.unpack("H", value[2:4])[0]

    @staticmethod
    def parase(length, value):
        source_id, rolling, anchor_count, tag_id0 = struct.unpack(
            "4H", value[:8])
        M = anchor_count
        N = (length - 8 - M * 8) // 6
        if M != N:
            return None  # 没收齐的不管

        peakpos, I, Q = np.frombuffer(
            value[8:8 + 6 * N], dtype=np.int16).reshape((3, -1), order='F')
        IQ = I + 1j * Q
        # peakpos = peakpos.astype(np.uint16)
        sync_time, reply_time = np.frombuffer(
            value[8 + 6 * N:8 + 6 * N + 8 * M], dtype=np.uint32).reshape((2, -1), order='F')
        # preamble,totalLen,type,length = struct.unpack()
        ret = [M * [rolling],  M * [tag_id0],
               list(range(M)), IQ.tolist(), sync_time.tolist(), reply_time.tolist()]
        ret = list(zip(*ret))
        # ret = {
        #     "rolling": M * [rolling],
        #     "TagID": M * [tag_id0],
        #     "AnchorIdx": list(range(M)),
        #     "IQ": IQ.tolist(),
        #     "sync_time": sync_time.tolist(),
        #     "reply_time": reply_time.tolist()
        # }
        return ret
