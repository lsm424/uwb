import serial
from access.access import Access


class SerialServer(Access):
    def __init__(self, port, baudrate, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
                 stopbits=serial.STOPBITS_ONE):
        self.serail = serial.Serial(port=port, baudrate=baudrate, bytesize=bytesize, parity=parity, stopbits=stopbits)
        super().__init__()

    def access_type(self):
        return 'serial'

    def _recive_data(self):
        data, addr = self.serail.readline(), self.serail.port
        return data, addr

    def reset_port(self):
        pass