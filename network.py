import socket
import json
from PySide6.QtCore import QObject, Slot

class UDPSender(QObject):
    def __init__(self):
        super().__init__()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.target = None  # (ip, port)

    @Slot(str, int)
    def set_target(self, ip, port):
        try:
            # resolve ONCE
            addr = socket.getaddrinfo(ip, port, socket.AF_INET, socket.SOCK_DGRAM)[0][4]
            self.target = addr
            print("UDP target set:", addr)
        except Exception as e:
            self.target = None
            print("Invalid target:", e)

    @Slot(dict)
    def send_packet(self, packet):
        if not self.target:
            return

        try:
            data = json.dumps(packet).encode("utf-8")
            self.sock.sendto(data, self.target)
        except Exception as e:
            print("UDP send failed:", e)


