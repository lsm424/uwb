import abc
import queue
import threading
import time

from common.common import logger, config

HEADER = 0x5af5.to_bytes((0x5af5.bit_length() + 7) // 8, 'little')


class Package:
    HEADER = 0x5af5.to_bytes((0x5af5.bit_length() + 7) // 8, 'little')

    def __init__(self):
        self.bytes = b''  # 以0x5af5开头的buf

    def add(self, data: bytes):
        self.bytes += data
        idx = self.bytes.find(self.HEADER)
        if idx == -1:  # 这一包没有开头标记位
            self.bytes = b''
            return None
        self.bytes = self.bytes[idx:]
        length = int.from_bytes(self.bytes[2:4], 'little')
        if length + 4 > len(self.bytes):  # 长度不够完整
            return None
        data = self.bytes[:length+4]
        self.bytes = self.bytes[length+4:]
        return data

class Access:

    def __init__(self):
        self._cache = {}
        self._raw_queue = queue.Queue()
        self._out_queue = queue.Queue()
        self._t_access = threading.Thread(target=self._run)
        self._t_access.setDaemon(True)
        self._t_access.start()
        self._t_tlv = threading.Thread(target=self._split_tlv)
        self._t_tlv.setDaemon(True)
        self._t_tlv.start()

    @abc.abstractmethod
    def _recive_data(self) -> (bytes, str):
        pass

    @abc.abstractmethod
    def access_type(self):
        pass

    # 接收数据线程
    def _run(self):
        logger.info(f'启动{self.access_type()}接收')
        while True:
            data, addr = self._recive_data()
            self._raw_queue.put((data, addr))

    # 抽取tlv线程
    def _split_tlv(self):
        while True:
            data, addr = self._raw_queue.get()
            pkg = self._cache.get(addr, Package())
            tlv = pkg.add(data)
            if not tlv:
                continue
            self._cache[addr] = pkg
            self._out_queue.put((tlv, addr, time.time()))

    def get_data(self):
        return self._out_queue.get()

    def qsize(self):
        return self._out_queue.qsize()


def create_access():
    if config['access_type'] == 'udp':
        from access.udp import UdpServer
        access = UdpServer(config['udp_port'])
    elif config['access_type'] == 'serial':
        from access.serial_com import SerialServer
        access = SerialServer(config['serial']['port'], config['serial']['baudrate'], config['serial']['bytesize'], config['serial']['parity'], config['serial']['stopbits'])
    return access