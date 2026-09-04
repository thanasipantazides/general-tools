import sys, time, os
import numpy as np
from matplotlib import pyplot as plt
import datetime

def do_cdte(path):

    with open(path, 'r') as f:
        data = f.readlines()
        unix = np.zeros(len(data)-1, dtype=np.float64)
        for k, line in enumerate(data):
            if k == 0: # ignore the header
                continue
            cols = data[k].split()
            if len(cols) < 12:
                continue
            # if cols[2] == "1PPS" and int(cols[4]) != 0 and cols[1] == '3':
            if cols[2] == "1PPS" and cols[1] == '3':
                unix[k-1] = float(cols[3])
        unix = unix[unix != 0]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12,6))
    fig.suptitle(os.path.basename(path))
    ax1.scatter(np.arange(0.0, len(unix), 1.0), unix, s=1, color='black')
    ax1.set_xlabel('PPS count')
    ax1.set_ylabel('Unixtime [s]')
    ax2.scatter(np.arange(0.0, len(unix) - 1, 1.0), np.diff(unix), s=1, color='black')
    ax2.set_xlabel('PPS count')
    ax2.set_ylabel('Unixtime differences, from PPS log [s]')
    plt.savefig(os.path.join(os.path.dirname(os.path.abspath(path)), 'cdte_pps.pdf'))
    plt.show()



def do_cmos(path):
    with open(path, 'rb') as f:
        data = f.read()
        cmosn = os.path.basename(path).split('_')[0]
        framesize = 0x218
        length = len(data) // framesize
        offset = 0xa4
        pps_linetimes = np.zeros(length, dtype = np.uint32)
        linetimes = np.zeros(length, dtype = np.uint32)
        datelinetime = []
        k = 0
        j = 0
        firstj = 0
        first = True
        linetime_at_first_pps = 0
        datetime_at_first_pps = None
        while k < len(data):
            pps_linetimes[j] = int.from_bytes(data[k+offset:k+offset+4], byteorder='little')
            linetimes[j] = int.from_bytes(data[k+0xa0:k+0xa0+4], byteorder='little')
            if not first:
                datelinetime.append(datetime_at_first_pps + datetime.timedelta(microseconds=20.52*(linetimes[j] - linetime_at_first_pps)))
            if first and pps_linetimes[j] != 0:
                linetime_at_first_pps = linetimes[j]
                datetime_at_first_pps = datetime.datetime(2026, 5, 14, 19, 2, 39, 479)
                datelinetime.append(datetime_at_first_pps)
                print(f"first nonzero linetime: {pps_linetimes[j]}")
                print(f"linetime at this point: {linetime_at_first_pps}")
                first = False
                firstj = j
            
            k = k+framesize
            j = j+1

    joindata = np.vstack(([np.asarray(datelinetime)], [linetimes[firstj::]])).T

    with open(os.path.join(os.path.dirname(os.path.abspath(path)), cmosn+'_pps.csv'), 'w') as wf:
        wf.write("time[UTC], linetime")
        for row in joindata:
            wf.write("\n" + row[0].strftime("%b %d %Y %H:%M:%S.%f") + ", " + str(row[1]))
            
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12,6))
    fig.suptitle(os.path.basename(path))
    ax1.scatter(np.arange(0.0, len(pps_linetimes), 1.0), 20.52e-6 * pps_linetimes, color='black', s=1)
    ax1.text(0, 20.52e-6 * 0.75*np.max(pps_linetimes), f"linetime @ first PPS: {linetime_at_first_pps}", ha='left', va='bottom')
    ax1.set_xlabel('PPS count')
    ax1.set_ylabel('Linetime [s]')
    ax2.scatter(np.arange(0.0, len(pps_linetimes)-1, 1.0), 20.52e-6 * np.diff(pps_linetimes), color='black', s=1)
    ax2.set_ylim([-1,8])
    ax2.set_xlabel('PPS count')
    ax2.set_ylabel('PPS linetime differences, via telemetry [s]')
    plt.savefig(os.path.join(os.path.dirname(os.path.abspath(path)), cmosn+'_pps.pdf'))
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