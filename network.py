import socket
import json
from PySide6.QtCore import QObject, Slot, QTimer


class UDPSender(QObject):
    def __init__(self, rate=30):
        super().__init__()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.target = None  # (ip, port)

        self.latest_packet = None
        self.rate = rate
        self.interval = int(1000 / rate)

        self.timer = QTimer()
        self.timer.timeout.connect(self._flush)
        self.timer.start(self.interval)

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
        # queues the latest packet so to be sent. So if your camera runs at 60fps,
        # but you only send at 30 fps, you are always sending the most recent data
        self.latest_packet = packet


    def _flush(self):
        if not self.target or self.latest_packet is None:
            return

        try:
            data = json.dumps(self.latest_packet, separators=(',', ':')).encode("utf-8")
            self.sock.sendto(data, self.target)
        except Exception as e:
            print("UDP send failed:", e)

