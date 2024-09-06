import csv
import queue
import threading
import time
import os
from common.common import get_header, logger, save
import struct
from common.cnt_queue import CntQueue as Queue


class Sensor300d:
    PROTO_ID = 0x300d
    # NAME = os.path.join(out_file_dir, '传感器数据输出')
    history_data = {}
    lock = threading.Lock()
    fieldnames = ['rolling', 'TagID', 'time', 'batt', 'pres', 'temp', 'acc_x', 'acc_y', 'acc_z', 'gyr_x', 'gyr_y',
                  'gyr_z', 'mag_x', 'mag_y', 'mag_z']
    # csv_file = open(f'{NAME}.csv', 'a', newline='', encoding='utf-8')
    gui_data = []
    # writer = csv.writer(csv_file)
    save_queue = Queue()
    # t = threading.Thread(target=save, args=(writer, save_queue, csv_file), daemon=True)
    # t.start()

    @staticmethod
    def save(pkgs):
        return Sensor300d.save_queue.put(pkgs)

    @staticmethod
    def init(out_file_dir):
        Sensor300d.NAME = os.path.join(out_file_dir, '传感器数据输出')
        Sensor300d.csv_file = open(f'{Sensor300d.NAME}.csv', 'a', newline='', encoding='utf-8')
        Sensor300d.writer = csv.writer(Sensor300d.csv_file)
        Sensor300d.t = threading.Thread(target=save, args=(Sensor300d.writer, Sensor300d.save_queue, Sensor300d.csv_file), daemon=True)
        Sensor300d.t.start()
        header = get_header(f'{Sensor300d.NAME}.csv')
        if not header:
            Sensor300d.writer.writerow(Sensor300d.fieldnames)

    # 保存gui需要的数据
    @staticmethod
    def save_gui_data(result):
        pass

    # def __del__(self):
    #     Sensor300d.csv_file.close()

    @staticmethod
    def get_rolling(value):
        return struct.unpack("<H", value[4:6])[0]

    # 去重
    @staticmethod
    def deduplication(rolling, tag_id):
        # Sensor300d.history_data = {rolling: value for rolling, value in Sensor300d.history_data.items() if value['timestampe'] > (time.time() - 5)}
        # with Sensor300d.lock:
        if rolling not in Sensor300d.history_data:
            Sensor300d.history_data[rolling] = {tag_id}
        elif tag_id in Sensor300d.history_data[rolling]:
            return True
        else:
            Sensor300d.history_data[rolling].add(tag_id)
        # Sensor300d.history_data[rolling]['timestampe'] = time.time()
        return False

    # 删除过期的历史数据
    @staticmethod
    def delete_old_history_data(interval=60):
        with Sensor300d.lock:
            Sensor300d.history_data = {rolling: value for rolling, value in Sensor300d.history_data.items(
            ) if value['timestampe'] > (time.time() - interval)}
            # for rolling, value in Sensor300d.history_data.items():
            #     if value['timestampe'] < time.time() - interval:
            #         del Sensor300d.history_data[rolling]

    @staticmethod
    def parase(length, value):
        source_id, tag_id, rolling, time, batt, pres, temp = struct.unpack(
            "<3HL3f", value[:22])
        # if len(value[22:]) < 38:
        #     logger.error(f'error len {value[22:]}')
        #     return None
        if Sensor300d.deduplication(rolling, tag_id):  # 重复数据
            return None

        acc_x, acc_y, acc_z, gyr_x, gyr_y, gyr_z, mag_x, mag_y, mag_z, heart_rate = struct.unpack(
            "9fH", value[22:])
        ret = [[rolling], [tag_id], [time], [batt], [pres], [temp], [acc_x], [
            acc_y], [acc_z], [gyr_x], [gyr_y], [gyr_z], [mag_x], [mag_y], [mag_z]]
        ret = list(zip(*ret))
        # ret = {
        #     "rolling": [rolling],
        #     "TagID": [tag_id],
        #     "time": [time],
        #     "batt": [batt],
        #     "pres": [pres],
        #     "temp": [temp],
        #     "acc_x": [acc_x],
        #     "acc_y": [acc_y],
        #     "acc_z": [acc_z],
        #     "gyr_x": [gyr_x],
        #     "gyr_y": [gyr_y],
        #     "gyr_z": [gyr_z],
        #     "mag_x": [mag_x],
        #     "mag_y": [mag_y],
        #     "mag_z": [mag_z],
        # }
        return ret
