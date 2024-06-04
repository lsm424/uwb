import socket
from access.access import Access


class UdpServer(Access):
    def __init__(self, port):
        self.reset_port(port)
        super().__init__()

    def access_type(self):
        return 'udp'

    def _recive_data(self):
        data, addr = self.sock.recvfrom(4096)
        addr = f'{addr[0]}:{addr[1]}'
        return data, addr

    def reset_port(self, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('', port))