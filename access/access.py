import abc
import pickle
import queue
import threading
import time
import numpy as np

from common.common import logger, config
from uwb.TLV import Tlv


def rolling_offset(type):
    if type == 0x300d:
        return 12
    else:
        return 10


class Access:

    def __init__(self):
        self._cache = {}
        self.cnt = 0
        self._out_queue = queue.Queue()

        self._t_access = threading.Thread(target=self._run, daemon=True)
        self._t_access.start()

    @abc.abstractmethod
    def _recive_data(self) -> (bytes, str):
        pass

    @abc.abstractmethod
    def access_type(self):
        pass

    # 接收数据线程
    def _run(self):
        logger.info(f'启动{self.access_type()}接收')
        buffer = {}
        while True:
            data, src = self._recive_data()
            if src not in buffer:
                buffer[src] = np.zeros((0,), np.uint8)
            d = np.concatenate([buffer[src], np.frombuffer(data, np.uint8)])
            # 找帧头
            headerPos = np.where(np.logical_and(d[:-5] == 0xF5, d[1:-4] == 0x5a))[0]
            lengths = d[headerPos + 2] + (d[headerPos + 3].astype(np.uint16) << 8)
            tailPos = headerPos + lengths + 4
            types = d[headerPos + 4] + (d[headerPos + 5].astype(np.uint16) << 8)
            validFrames = np.logical_and(np.logical_and(tailPos < len(d), lengths < 4096), np.isin(types, Tlv.TYPES))
            headerPos = headerPos[validFrames]
            if len(headerPos) == 0:
                buffer[src] = d
                continue
            tailPos = tailPos[validFrames]
            types = types[validFrames]
            lengths = d[headerPos + 6] + (d[headerPos + 7].astype(np.uint16) << 8)

            offset = headerPos + np.array([rolling_offset(i) for i in types])
            rollings = d[offset] + (d[offset + 1].astype(np.uint16) << 8)

            [self._out_queue.put(Tlv(src, bytes(d[headerPos[i]:tailPos[i]].tobytes(
            )), lengths[i], types[i], rollings[i])) for i in range(len(types))]
            buffer[src] = d[tailPos[-1]:]
            self.cnt += len(types)

    def get_data(self):
        return self._out_queue.get()

    def qsize(self):
        return self._out_queue.qsize()

    def raw_queue_size(self):
        return self._raw_queue.qsize()


def create_access():
    if config['access_type'] == 'udp':
        from access.udp import UdpServer
        access = UdpServer(config['udp_port'])
    elif config['access_type'] == 'serial':
        from access.serial_com import SerialServer
        access = SerialServer(config['serial']['port'], config['serial']['baudrate'], config['serial']
                              ['bytesize'], config['serial']['parity'], config['serial']['stopbits'])
    return access
