import pickle
import threading
from struct import unpack
import time
from collections import defaultdict

from common.common import logger, pickle_file
from uwb.cir_2121 import Cir2121
from uwb.sensor_300d import Sensor300d
from uwb.slot_2042 import Slot2042
from uwb.tod_4090 import Tod4090
from uwb.tof_2011 import Tof2011

# tlv解析处理
class Tlv:
    proto_handler = {
        Cir2121.PROTO_ID: Cir2121(),
        Slot2042.PROTO_ID: Slot2042(),
        Tod4090.PROTO_ID: Tod4090(),
        Sensor300d.PROTO_ID: Sensor300d(),
        Tof2011.PROTO_ID: Tof2011(),
    }

    def __init__(self, data, addr, timestampe):
        self.data = data
        self.addr = addr
        self.timestampe = timestampe
        self.result = None
        self.pickle_data = {'raw_data': self.data, 'addr': self.addr, 'timestampe': self.timestampe}

    @staticmethod
    def save():
        while True:
            pass

    # 预处理，解析头部字段
    def pre_parase(self):
        header, length = unpack("2H", self.data[:4])
        if length > 4096:
            logger.error(f'data length more than 4096, length: {length}')
            return False
        body = self.data[4: length + 2]
        # crc = self.data[length + 2: length + 4]

        self.proto_type, self.length = unpack("2H", body[:4])
        self.proto_handler = self.proto_handler.get(self.proto_type, None)
        if not self.proto_handler:
            logger.error(f'unsupport proto {hex(self.proto_type)}')
            return False
        self.value = body[4:]
        self.rolling = self.proto_handler.get_rolling(self.value)
        return True

    # 解析测量值
    def parase(self):
        self.result = self.proto_handler.parase(self.length, self.value)
        return self

    # # 写文件
    # def save_file(self):
    #     self.proto_handler.save(self.result)
    #     pickle_file.write(pickle.dumps())