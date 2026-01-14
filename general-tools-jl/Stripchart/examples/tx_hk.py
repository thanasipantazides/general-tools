import sys, os, socket, time

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# lept = ('192.168.1.8', 9998)
# rept = ('224.1.1.118', 9999)
lept = ('127.0.0.1', 9998)
rept = ('127.0.0.1', 9999)

framesize_rtd = 42 # for RTDs
framesize_pow = 38 # for power

def worm(k, w):
    s = 'o'*(w - 1)
    out = s[:k] + 'O' + s[k:]
    return out

def packetize(data, type=0x12):
    head = bytearray([0x02, 0x00, 0x01, 0x00, 0x01, type, 0x00, 0x00])
    head.extend(data)
    return head

def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def get_frames(argv):
    framesize = 0
    key = ""
    res = {}
    for arg in argv:
        if not os.path.isfile(arg):
            continue
        if 'housekeeping_pow' in arg:
            framesize = framesize_pow
            key = 'pow'
            type = 0x11
        elif 'housekeeping_rtd' in arg:
            framesize = framesize_rtd
            key = 'rtd'
            type = 0x12
        else:
            print('got unknown file arg, skipping')
            continue
        
        with open(arg, 'rb') as f:
            d = f.read()
            if len(d) % framesize != 0:
                raise FileError
        
        frames = list(chunks(d, framesize))
        res[key] = {"frames": frames, "k":0, "size":framesize, "type":type}
    return res

if __name__ == '__main__':
    if not len(sys.argv) >= 2:
        print("use like this:\n\t> python tx_hk.py path/to/raw/file.log [--packetize]")
        exit(-1)
    
    frames_data = get_frames(sys.argv)
    
    # with open(fname, 'rb') as f:
    #     d = f.read()
    #     if len(d) % framesize_rtd != 0:
    #         raise FileError
    
    # frames = list(chunks(d, framesize_rtd))
    
    sock.bind(lept)
    
    k = 0
    pwidth = 12
    while True:
        
        for key in frames_data.keys():
            if key == "rtd":
                pair_k = (frames_data[key]["k"] + 1) % len(frames_data[key]["frames"])
                next_k = (frames_data[key]["k"] + 2) % len(frames_data[key]["frames"])
                to_send = [frames_data[key]["frames"][k] for k in (frames_data[key]["k"], pair_k)]
                frames_data[key]["k"] = next_k
            else:
                k = frames_data[key]["k"]
                to_send = [frames_data[key]["frames"][k]]
                next_k = (frames_data[key]["k"] + 1) % len(frames_data[key]["frames"])
                frames_data[key]["k"] = next_k
        
            if '--packetize' in sys.argv:
                [sock.sendto(packetize(frame, type=frames_data[key]["type"]), rept) for frame in to_send]
            else:
                [sock.sendto(frame, rept) for frame in to_send]
            
        print(' ' + worm(k % pwidth, pwidth) + ' ', end='\r')
        time.sleep(0.1)
        
            