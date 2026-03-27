import socket
import sys

DEFAULT_PORT = 25590

if __name__ == '__main__':
    if len(sys.argv) == 2:
        port = int(sys.argv[1])
    else:
        port = DEFAULT_PORT
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    target = ("127.0.0.1", port)

    for i in range(10000):
        sock.sendto(b"spam", target)