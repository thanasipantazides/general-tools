import socket, os, sys, struct, time
from datetime import datetime

import numpy as np
from matplotlib import pyplot as plt

default_local_ip = "192.168.1.180"
default_local_port = 9999

mcast_group = "224.1.1.118"
mcast_port = 9999

# timestamping for display and logfile:
default_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
default_filename = os.path.join("log", "log_cooling_" + default_time + ".log")

nperchip = 9
nchip = 2
nsensor = nperchip*nchip

def parse_rtd(id:int,data:bytes):
    blob = data[14:]
    channels = np.zeros(nperchip, dtype=np.uint8)
    errors = np.zeros(nperchip, dtype=np.uint8)
    values = np.zeros(nperchip, dtype=np.float32)

    ch = 0
    sign_bit = 1<<24
    for k in range(0, len(blob), 4):
        ch = int(k/4)
        channels[ch] = ch
        errors[ch] = blob[k]
        temp_raw = int.from_bytes(blob[k+1:k+4], byteorder='big')
        if temp_raw & sign_bit:
            temp_raw = temp_raw & ~sign_bit # clear the sign bit
            temp_raw = -temp_raw            # negate the value
        values[ch] = temp_raw / 1024.0      # move decimal 10 places left

    return channels, errors, values


if __name__ == "__main__":
    # join multicast group
    local_recv_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    local_recv_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

    local_recv_socket.bind((mcast_group, default_local_port))
    mreq = struct.pack('4s4s', socket.inet_aton(mcast_group), socket.inet_aton(default_local_ip))
    local_recv_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    print("joined!")

    while True:
        try:
            # read socket:
            data = local_recv_socket.recv(2048)
            if data[0] == 0x02 and data[5] == 0x12:
                # print(data.hex())
                sd = parse_rtd(data[8], data)
                print("chip", data[8])
                print("\terrors:", sd[1])
                print("\tvalues:", sd[2])
        except KeyboardInterrupt:
            break

    # time-tag and save the data
    # read the save file and liveplot