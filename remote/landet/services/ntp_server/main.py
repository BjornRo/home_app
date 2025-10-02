from socket import socket, AF_INET, SOCK_DGRAM
from time import time


def s2n():
    t = time() + 2208988800.0
    return (int(t) << 32) + int(abs(t - int(t)) * (1 << 32))


s = socket(AF_INET, SOCK_DGRAM)
s.bind(("", 123))

recv_buf = bytearray(48)
send_buf = bytearray(48)
send_buf[1] = 1
send_buf[3] = 227
while True:
    n, addr = s.recvfrom_into(recv_buf)
    send_buf[16:24] = send_buf[32:40] = s2n().to_bytes(8)
    if n == 48:
        start_byte = recv_buf[0]
        version = start_byte >> 3 & 7

        if version < 4 and start_byte & 7 == 3:
            send_buf[0] = version << 3 | 4
            send_buf[24:32] = recv_buf[40:48]
            send_buf[40:48] = s2n().to_bytes(8)
            s.sendto(send_buf, addr)
