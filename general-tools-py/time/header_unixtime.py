import sys, os
import numpy as np
from datetime import datetime
import matplotlib as mpl
import matplotlib.ticker as ticker

from matplotlib import pyplot as plt

"""
In FOXSI telemetry, Timepix, HK RTD, HK power, HK ping, and Timepix TPX data all report Formatter unixtime in their headers. This is a script for plotting those together.
"""

rtd_framesize = 0x2a
pow_framesize = 0x26
png_framesize = 0x2e
tpx_framesize = 0x26

def fragment_bytes(data:bytes, n:int):
    return [data[i:i+n] for i in range(0, len(data), n)]

def read_frames(path:str, n:int):
    with open(path, 'rb') as p:
        data = p.read()
    return fragment_bytes(data, n)
    
def get_unixtimes_rtd1(path:str):
    unixt = []
    for frame in read_frames(path, rtd_framesize):
        if frame[0] == 0x01:
            unixt.append(int.from_bytes(frame[2:6],'big', signed=False))
    return unixt
    
def get_unixtimes_rtd2(path:str):
    unixt = []
    for frame in read_frames(path, rtd_framesize):
        if frame[0] == 0x02:
            unixt.append(int.from_bytes(frame[2:6],'big', signed=False))
    return unixt
    
def get_unixtimes_pow(path:str):
    unixt = []
    for frame in read_frames(path, pow_framesize):
        unixt.append(int.from_bytes(frame[2:6],'big', signed=False))
    return unixt
    
def get_unixtimes_tpx(path:str):
    unixt = []
    for frame in read_frames(path, tpx_framesize):
        unixt.append(int.from_bytes(frame[2:6],'big'))
    return unixt
    
if __name__ == "__main__":
    
    path = sys.argv[1]
    
    fig, (axr, axd) = mpl.pyplot.subplots(1,2)
    
    cmap = mpl.colormaps.get_cmap('tab20') 
    colors = [cmap(i) for i in np.linspace(0, 1, 12)] 
    plt.rcParams['axes.prop_cycle'] = plt.cycler(color=colors)
    
    # ax.yaxis.set_major_formatter(mpl.dates.DateFormatter('%H:%M:%S'))
    rtdpath = os.path.join(path, "housekeeping_rtd.log")
    powpath = os.path.join(path, "housekeeping_pow.log")
    tpxpath = os.path.join(path, "timepix_tpx.log")
    
    rtd1 = get_unixtimes_rtd1(rtdpath)
    rtd2 = get_unixtimes_rtd2(rtdpath)
    pow = get_unixtimes_pow(powpath)
    tpx = get_unixtimes_tpx(tpxpath)
    
    # rtd1_d = [datetime.fromtimestamp(t).strftime('%H:%M:%S') for t in rtd1]
    # rtd2_d = [datetime.fromtimestamp(t).strftime('%H:%M:%S') for t in rtd2]
    # pow_d = [datetime.fromtimestamp(t).strftime('%H:%M:%S') for t in pow]
    # tpx_d = [datetime.fromtimestamp(t).strftime('%H:%M:%S') for t in tpx]
    
    
    axr.scatter(range(len(rtd1)), rtd1, s=2, label="rtd 1")
    axr.scatter(range(len(rtd2)), rtd2, s=2, label="rtd 2")
    axr.scatter(range(len(pow)), pow, s=2, label="power")
    # axr.scatter(range(len(tpx)), tpx, s=2, label="timepix")
    axr.set_xlabel('Frame index')
    axr.set_ylabel('Formatter unixtime')
    
    axd.scatter(range(len(rtd1) - 1), np.diff(rtd1), s=2, label="rtd 1")
    axd.scatter(range(len(rtd2) - 1), np.diff(rtd2), s=2, label="rtd 2")
    axd.scatter(range(len(pow) - 1), np.diff(pow), s=2, label="power")
    # axd.scatter(range(len(tpx) - 1), np.diff(tpx), s=2, label="timepix")
    axd.set_xlabel('Frame index')
    axd.set_ylabel('Formatter unixtime differences')
    # ax.get_xaxis().set_major_locator(ticker.MultipleLocator(1))
    # ax.get_xaxis().set_major_formatter(ticker.FormatStrFormatter("%x"))
    plt.legend()
    plt.show()