import queue
import struct
import threading
import os
import numpy as np
import csv
from common.common import get_header, save
import multiprocessing


class Slot2042:
    PROTO_ID = 0x2042
    # NAME = os.path.join(out_file_dir, '时隙占用表数据上传')
    gui_data = []
    # csv_file = open(f'{NAME}.csv', 'a', newline='', encoding='utf-8')
    fieldnames = ['rolling', 'TagID', 'AnchorIdx', 'AnchorId']
    # writer = csv.writer(csv_file)
    save_queue = multiprocessing.Queue()
    # t = threading.Thread(target=save, args=(writer, save_queue, csv_file), daemon=True)
    # t.start()

    @staticmethod
    def save(pkgs):
        Slot2042.gui_data += pkgs
        Slot2042.gui_data = Slot2042.gui_data[-1000:]  # 内存中最多保留1000条
        return Slot2042.save_queue.put(pkgs)

    @staticmethod
    def init(out_file_dir):
        Slot2042.NAME = os.path.join(out_file_dir, '时隙占用表数据上传')
        Slot2042.csv_file = open(
            f'{Slot2042.NAME}.csv', 'a', newline='', encoding='utf-8')
        Slot2042.writer = csv.writer(Slot2042.csv_file)
        Slot2042.t = threading.Thread(target=save, args=(
            Slot2042.writer, Slot2042.save_queue, Slot2042.csv_file), daemon=True)
        Slot2042.t.start()
        header = get_header(f'{Slot2042.NAME}.csv')
        if not header:
            Slot2042.writer.writerow(Slot2042.fieldnames)

    # def __del__(self):
    #     Slot2042.csv_file.close()

    @staticmethod
    def get_rolling(value):
        return struct.unpack("H", value[2:4])[0]

    @staticmethod
    def parase(length, value):
        Source_ID, rolling, Net_code, tag_id = struct.unpack("4H", value[:8])
        N = (length - 8) // 2
        Anchor_ID = np.frombuffer(value[8:8 + 2 * N], dtype=np.uint16)
        ret = [N * [rolling], N * [tag_id], list(range(N)), Anchor_ID.tolist()]
        ret = list(zip(*ret))
        # ret = {
        #     "rolling": N * [rolling],
        #     "TagID": N * [tag_id],
        #     "AnchorIdx": list(range(N)),
        #     "AnchorId": Anchor_ID.tolist(),
        # }
        return ret
