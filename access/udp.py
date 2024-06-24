import socket
from access.access import Access
from common.common import logger


class UdpServer(Access):
    def __init__(self, port):
        self.port = 0
        self.reset_port(port)
        super().__init__()

    def access_type(self):
        return f'udp {self.port}'

    def _recive_data(self):
        try:
            data, addr = self.sock.recvfrom(65536)
            addr = f'{addr[0]}:{addr[1]}'
            return data, addr
        except BaseException as e:
            return None, None

    def reset_port(self, port):
        if self.port == port:
            return
        if self.port != 0:
            self.sock.close()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1000000)
        self.sock.bind(('', port))
        self.port = port

    def close(self):
        self.sock.close()
        logger.info(f'关闭udp端口{self.port}')
