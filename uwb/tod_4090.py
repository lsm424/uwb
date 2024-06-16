import queue
import struct
import threading
import multiprocessing
import numpy as np
import csv
import os
from common.common import get_header, save


class Tod4090:
    PROTO_ID = 0x4090
    # NAME = os.path.join(out_file_dir, 'TDOA与PDOA集中上传')
    fieldnames = ['rolling', 'AnchorId',
                  'TagID', 'TOA', 'POA_SYNC', 'POA_REPLY']
    # csv_file = open(f'{NAME}.csv', 'a', newline='', encoding='utf-8')
    # writer = csv.writer(csv_file)
    save_queue = multiprocessing.Queue()
    # t = threading.Thread(target=save, args=(
    #     writer, save_queue, csv_file), daemon=True)
    # t.start()

    @staticmethod
    def save(pkgs):
        return Tod4090.save_queue.put(pkgs)

    @staticmethod
    def init(out_file_dir):
        Tod4090.NAME = os.path.join(out_file_dir, 'TDOA与PDOA集中上传')
        Tod4090.csv_file = open(f'{Tod4090.NAME}.csv', 'a', newline='', encoding='utf-8')
        Tod4090.writer = csv.writer(Tod4090.csv_file)
        Tod4090.t = threading.Thread(target=save, args=(Tod4090.writer, Tod4090.save_queue, Tod4090.csv_file), daemon=True)
        Tod4090.t.start()
        header = get_header(f'{Tod4090.NAME}.csv')
        if not header:
            Tod4090.writer.writerow(Tod4090.fieldnames)

    @staticmethod
    def save_gui_data(result):
        pass

    @staticmethod
    def get_rolling(value):
        return struct.unpack("H", value[2:4])[0]

    @staticmethod
    def parase(length, value):
        source_id, rolling, net_code, anchor = struct.unpack("4H", value[:8])
        N = (length - 8) // 6
        tag_id0_l0, tag_id0_hi, SYNC到达相位, REPLY到达相位, SYNC_REPLY到达时间平均值_LO, SYNC_REPLY到达时间平均值_HI = np.frombuffer(
            value[8:8 + 6 * N], dtype=np.uint8).reshape((6, -1), order="F")
        tag_id0 = (tag_id0_hi * 256.0 + tag_id0_l0).astype(np.uint16)
        SYNC_REPLY到达时间平均值 = (SYNC_REPLY到达时间平均值_HI * 256.0 +
                             SYNC_REPLY到达时间平均值_LO).astype(np.uint16)

        ret = [N * [rolling], N * [anchor], tag_id0.tolist(),
               SYNC_REPLY到达时间平均值.tolist(), SYNC到达相位.tolist(), REPLY到达相位.tolist()]
        ret = list(zip(*ret))
        # ret = {
        #     "rolling": N * [rolling],
        #     "AnchorId": N * [anchor],
        #     "TagID": tag_id0.tolist(),
        #     "TOA": SYNC_REPLY到达时间平均值.tolist(),
        #     "POA_SYNC": SYNC到达相位.tolist(),
        #     "POA_REPLY": REPLY到达相位.tolist(),
        # }
        return ret
