import sys, socket, time

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

lept = ('192.168.1.8', 9998)
rept = ('224.1.1.118', 9999)

framesize = 42 # for RTDs

def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

if __name__ == '__main__':
    if len(sys.argv) == 2:
        fname = sys.argv[1]
    else:
        print("use like this:\n\t> python tx_hk.py path/to/raw/file.log")
        exit(-1)
    
    with open(fname, 'rb') as f:
        d = f.read()
        if len(d) % framesize != 0:
            raise FileError
    
    frames = list(chunks(d, framesize))
    
    sock.bind(lept)
    
    k = 0
    while True:
        sock.sendto(frames[k], rept)
        time.sleep(0.5)
        k = (k + 1) % len(frames)
        if k % 2 == 0:
            print(' o ', end='\r')
        else:
            print(' O ', end='\r')
            