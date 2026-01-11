import sys, time, os
import numpy as np
from matplotlib import pyplot as plt

def do_cdte(path):

    with open(path, 'r') as f:
        data = f.readlines()
        unix = np.zeros(len(data)-1, dtype=np.float64)
        for k, line in enumerate(data):
            if k == 0: # ignore the header
                continue
            cols = data[k].split()
            # if cols[2] == "1PPS" and int(cols[4]) != 0 and cols[1] == '3':
            if cols[2] == "1PPS" and cols[1] == '3':
                unix[k-1] = float(cols[3])
        unix = unix[unix != 0]
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12,6), sharex=True)
    fig.suptitle(os.path.basename(path))
    ax1.scatter(np.arange(0.0, len(unix), 1.0), unix, color='black')
    ax1.set_xlabel('PPS count')
    ax1.set_ylabel('Unixtime [s]')
    ax2.scatter(np.arange(0.0, len(unix) - 1, 1.0), np.diff(unix), color='black')
    ax2.set_xlabel('PPS count')
    ax2.set_ylabel('Unixtime differences, from PPS log [s]')
    ax2.set_ylim([0,3])
    plt.savefig(os.path.join(os.path.dirname(os.path.abspath(path)), 'cdte_pps.pdf'))
    plt.show()



def do_cmos(path):
    with open(path, 'rb') as f:
        data = f.read()
        framesize = 0x218
        length = len(data) // framesize
        offset = 0xa4
        linetimes = np.zeros(length, dtype = np.uint32)
        k = 0
        j = 0
        while k < len(data):
            linetimes[j] = int.from_bytes(data[k+offset:k+offset+4], byteorder='little')
            k = k+framesize
            j = j+1
        
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12,6), sharex=True)
    fig.suptitle(os.path.basename(path))
    ax1.scatter(np.arange(0.0, len(linetimes), 1.0), 20.52e-6 * linetimes, color='black')
    ax1.set_xlabel('PPS count')
    ax1.set_ylabel('Linetime [s]')
    ax2.scatter(np.arange(0.0, len(linetimes)-1, 1.0), 20.52e-6 * np.diff(linetimes), color='black')
    ax2.set_xlabel('PPS count')
    ax2.set_ylabel('PPS linetime differences, via telemetry [s]')
    ax2.set_ylim([0,6])
    ax2.set_xlim([50,130])
    plt.savefig(os.path.join(os.path.dirname(os.path.abspath(path)), 'cmos_pps.pdf'))
    plt.show()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("run like this\n\t> python pps.py cdte|cmos path/to/log/file.log")
        sys.exit(1)

    if sys.argv[1] == "cdte":
        do_cdte(sys.argv[2])
    elif sys.argv[1] == "cmos":
        do_cmos(sys.argv[2])
    else:
        print("you were supposed to say cdte or cmos")
        sys.exit(1)
