import serial
from access.access import Access
from common.common import logger


class SerialServer(Access):
    def __init__(self, port, baudrate, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
                 stopbits=serial.STOPBITS_ONE):
        self.port = port
        self.serail = None
        try:
            self.serail = serial.Serial(port=port, baudrate=baudrate, bytesize=bytesize, parity=parity, stopbits=stopbits)
        except BaseException as e:
            pass
        super().__init__()

    def access_type(self):
        return f'串口 {self.port}'

    def _recive_data(self):
        try:
            data, addr = self.serail.read_all(), self.serail.port
            return data, addr
        except BaseException as e:
            return None, None

    def reset_port(self):
        pass

    def close(self):
        if self.serail:
            self.serail.close()
            logger.info(f'关闭串口{self.port}')
