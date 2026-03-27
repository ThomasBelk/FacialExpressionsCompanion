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

    for size in [100, 512, 1024, 2048, 4096, 8192, 16384, 65507]:
        data = b"A" * size
        sock.sendto(data, target)
        print(f"Sent packet of size {size}")