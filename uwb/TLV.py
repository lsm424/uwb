import pickle
import threading
from struct import unpack
from time import time
from collections import defaultdict


from common.common import logger
# from uwb.cir_2121 import Cir2121
from uwb.poa_3012 import Poa3012
from uwb.sensor_300d import Sensor300d
from uwb.slot_2042 import Slot2042
from uwb.tod_4090 import Tod4090
from uwb.tof_2011 import Tof2011

# tlv解析处理
# class Tlv:
#     proto_handler = {
#         Cir2121.PROTO_ID: Cir2121(),
#         Slot2042.PROTO_ID: Slot2042(),
#         Tod4090.PROTO_ID: Tod4090(),
#         Sensor300d.PROTO_ID: Sensor300d(),
#         Tof2011.PROTO_ID: Tof2011(),
#     }
#
#     def __init__(self, data, addr, timestampe):
#         self.data = data
#         self.addr = addr
#         self.timestampe = timestampe
#         self.result = None
#         self.pickle_data = {'raw_data': self.data, 'addr': self.addr, 'timestampe': self.timestampe}
#
#     @staticmethod
#     def save():
#         while True:
#             pass
#
#     # 预处理，解析头部字段
#     def pre_parase(self):
#         header, length = unpack("2H", self.data[:4])
#         if length > 4096:
#             logger.error(f'data length more than 4096, length: {length}')
#             return False
#         body = self.data[4: length + 2]
#         # crc = self.data[length + 2: length + 4]
#
#         self.proto_type, self.length = unpack("2H", body[:4])
#         self.proto_handler = self.proto_handler.get(self.proto_type, None)
#         if not self.proto_handler:
#             logger.error(f'unsupport proto {hex(self.proto_type)}')
#             return False
#         self.value = body[4:]
#         self.rolling = self.proto_handler.get_rolling(self.value)
#         return True
#
#     # 解析测量值
#     def parase(self):
#         self.result = self.proto_handler.parase(self.length, self.value)
#         return self


class Tlv:
    PROTO_HANDLER = {
        Poa3012.PROTO_ID: Poa3012(),
        Slot2042.PROTO_ID: Slot2042(),
        Tod4090.PROTO_ID: Tod4090(),
        Sensor300d.PROTO_ID: Sensor300d(),
        Tof2011.PROTO_ID: Tof2011(),
    }
    TYPES = list(PROTO_HANDLER.keys())

    def __init__(self, addr, raw_data, body_len, proto_type, rolling):
        self.addr = addr
        self.raw_data = raw_data
        self.body_data = raw_data[8:-2]
        self.body_len = body_len
        self.rolling = rolling
        self.proto_type = proto_type
        self.handler = Tlv.PROTO_HANDLER.get(self.proto_type, None) # Tlv.PROTO_HANDLER[proto_type]
        self.result = None
        self.pickle_data = {'raw_data': self.raw_data,
                            'addr': self.addr, 'timestampe': time()}

    def parase(self):
        if self.handler is not None:
            self.result = self.handler.parase(self.body_len, self.body_data)
        # if not self.result:
        #     self.pre_parase()
        return self

    def pre_parase(self):
        header, length = unpack("2H", self.raw_data[:4])
        if length > 4096:
            logger.error(f'data length more than 4096, length: {length}')
            return False
        body = self.raw_data[4: length + 2]
        # crc = self.data[length + 2: length + 4]

        self.proto_type, self.length = unpack("2H", body[:4])
        self.protoHandler = self.PROTO_HANDLER.get(self.proto_type, None)
        if not self.protoHandler:
            logger.error(f'unsupport proto {hex(self.proto_type)}')
            return False
        self.value = body[4:]
        self.rolling = self.protoHandler.get_rolling(self.value)
        return True
