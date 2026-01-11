import sys, os, time, re, datetime
import json
import bisect
import argparse
import matplotlib as mpl
from matplotlib import pyplot as plt
import numpy as np

import pickle

import pprint

rtd_labels = {
    1: 'timepix',
    2: 'saas camera',
    3: 'formatter pi',
    4: '5.5 V regulator',
    5: 'focal position 5',
    6: 'focal position 4',
    7: 'focal position 3',
    8: 'focal position 2',
    9: 'ln2 inlet',
    20: 'optic plate',
    19: 'position 6 front',
    18: 'position 6 plate',
    17: 'position 2 plate',
    16: 'position 4 front',
    15: 'position 4 plate',
    14: 'position 0 collimator',
    13: 'position 0 front',
    12: 'position 0 plate'
}
pow_labels = {
    0: '28 V in',
    1: '5.5 V',
    2: '12 V',
    3: '5 V',
    4: 'regulator I',
    5: 'SAAS camera I',
    6: 'SAAS SBC I',
    7: 'Timepix FPGA I',
    8: 'Timepix SBC I',
    9: 'CdTe DE I',
    10: 'CdTe 1 I',
    11: 'CdTe 5 I',
    12: 'CdTe 3 I',
    13: 'CdTe 4 I',
    14: 'CMOS 1 I',
    15: 'CMOS 3 I',
}

def fragment_bytes(data:bytes, n:int):
    return [data[i:i+n] for i in range(0, len(data), n)]

def command_deck(path):
    deck = {}
    with open(os.path.join(path, "systems.json"), 'r') as sys_file:
        sys_config = json.load(sys_file)
        for sys in sys_config:
            if "commands" in sys:
                sys_hex = int(sys["hex"], base=16)
                deck[sys_hex] = {"name": sys["name"]}
                deck[sys_hex]["commands"] = {}
                with open(os.path.join(path, "..", sys["commands"]), 'r') as cmd_file:
                    cmd_config = json.load(cmd_file)
                    for cmd in cmd_config:
                        cmd_hex = int(cmd["hex"], base=16)
                        deck[sys_hex]["commands"][cmd_hex] = cmd["name"]
    return deck

def detect_datetime_folder(path):
    path = os.path.normpath(path)
    folders = re.findall("\d+\-\d+\-\d+\_\d+\-\d+\-\d+", path)
    if len(folders) > 0:
        candidate = folders[-1]
    else:
        raise ValueError

    date = datetime.datetime.strptime(candidate, "%d-%m-%Y_%H-%M-%S")
    return date

class Note:
    def __init__(self, 
                 notes:str|list[str]|None, 
                 readtimeformat='%H:%M:%S', 
                 readdatetimeformat='%d-%m-%Y_%H-%M-%S', 
                 maxlength=40, 
                 configpath=os.path.join(os.path.dirname(__file__), '..', '..', 'external', 'foxsi4-commands')):
        self.readtimeformat = readtimeformat
        self.readdatetimeformat = readdatetimeformat
        self.maxlength = maxlength

        if configpath is None:
            self.deckconversion = False
        else:
            try:
                self.deck = command_deck(configpath)
                self.deckconversion = True
            except:
                self.deck = None
                self.deckconversion = False

        self.data = {}

        if isinstance(notes, list):
            for note in notes:
                self.ingest_note(note)
        elif isinstance(notes, str):
            self.ingest_note(notes)
        
        # pprint.pprint(self.data)

    def ingest_note(self, note):
        start_datetime = detect_datetime_folder(note)
        self.date = datetime.datetime.combine(start_datetime, datetime.time.min)
        with open(note, 'r') as fnote:
            for line in fnote.readlines():
                stamp, text = self.expand_noteline(line, True)
                dtstamp = datetime.datetime.combine(self.date, stamp.time())
                self.data[dtstamp] = text

    def expand_noteline(self, noteline:str, deck_conversion=False):
        try:
            time = noteline.split("-",1)[0].lstrip().rstrip()
            text = noteline.split("-",1)[1].lstrip().rstrip()
        except IndexError:
            return None

        if self.deckconversion:
            hexes = re.findall(r'^0[xX][0-9a-fA-F]+', text)
            try:
                cmd_raw = hexes[0]
                cmd_raw_int = int(cmd_raw, base=16)
                sys_int = (cmd_raw_int >> 8) & 0xff
                cmd_int = (cmd_raw_int >> 0) & 0xff
                sys_name = self.deck[sys_int]["name"]
                cmd_name = self.deck[sys_int]["commands"][cmd_int]
            
                text =  sys_name + ' > ' + cmd_name #+ ' (' + cmd_raw + ')'
                
            except IndexError or KeyError:
                pass

        if len(text) > self.maxlength:
            text = text[:self.maxlength - 3] + '...'
        
        timed = datetime.datetime.strptime(time, self.readtimeformat)
        return timed, text

class Log:
    def __init__(self, 
                 log:str,
                 readtimeformat='%H:%M:%S', 
                 readdatetimeformat='%d-%m-%Y_%H-%M-%S', 
                 abstimeoffset=datetime.timedelta(seconds=0), # compensate for the fact that Formatter times are offset from the start of GSE time
                 configpath=os.path.join(os.path.dirname(__file__), '..', '..', 'external', 'foxsi4-commands')):
        
        self.readtimeformat = readtimeformat
        self.readdatetimeformat = readdatetimeformat
        self.abstimeoffset = abstimeoffset

        if configpath is not None:
            self.deck = command_deck(configpath)
        
        self.frame_size = 0
        self.data = {}
        self.ingest_log(log)
    
    def ingest_log(self, log):
        start_datetime = detect_datetime_folder(log)
        start_datetime += self.abstimeoffset

        with open(log, 'rb') as flog:
                raw = flog.read()
        
        fname = os.path.basename(log)
        
        if fname == 'housekeeping_rtd.log':
            # from external.telemetry_tools.parsers.RTDparser import rtdparser
            from ..rtd.rtd import Parser
            self.frame_size = 42
            parsed = Parser(log)

            chip_channel_offset = {1:1,2:12}
            for chip in [1,2]:
                unixtimes = np.array([int.from_bytes(field['unixtime'],'big') for field in parsed.rtd_data[chip]], dtype=np.uint32)
                reltimes = unixtimes - np.min(unixtimes)
                abstimes = [start_datetime + datetime.timedelta(seconds=time.item()) for time in reltimes]
                d = {}
                for t, data in zip(abstimes, parsed.rtd_data[chip]):
                    d[t] = {k + chip_channel_offset[chip]: data['data'][k] for k in data['data']}
                    if t in self.data.keys():
                        self.data[t].update(d[t])
                    else:
                        self.data[t] = d[t]

            # structure of self.data: keys are datetimes, values are dicts keyed by RTD sensor number (1-9, 12-20).
            #      self.data[t][7]['temp'] is the temperature
            #      self.data[t][7]['flag'] is the flag
                
        elif fname == 'housekeeping_pow.log':
            from external.telemetry_tools.parsers.Powerparser import adcparser
            self.frame_size = 38
            print('parsing ', log)
            parsed = []
            for d in fragment_bytes(raw, self.frame_size):
                res = adcparser(d)
                if res[1]:
                    continue
                else:
                    parsed.append(res)
            
            d = {}
            unixtime0 = 0
            for k,frame in enumerate(parsed):
                unixtime = frame[0]['unixtime']
                if k == 0:
                    unixtime0 = unixtime
                reltime = unixtime - unixtime0
                abstime = start_datetime + datetime.timedelta(seconds=reltime)
                d[abstime] = {k:frame[0][k] for k in frame[0].keys() if k != 'unixtime'}
                self.data[abstime] = d[abstime]

        else:
            raise NotImplementedError
        
class StripChart:
    def __init__(self, 
                 logfolder: str|list[str]|None, 
                 notes: str|list[str]|Note|list[Note]|None, 
                 config=os.path.join(os.path.dirname(__file__), '..', '..', 'external', 'foxsi4-commands'), 
                 displaydatetimeformat='%H:%M%:S', 
                 readdatetimeformat='%d-%m-%Y_%H-%M-%S', 
                 readtimeformat='%H:%M:%S.%f',
                 maxnotelength=40,
                 figpath=None,
                 annotateallplots=False):
        self.displaydatetimeformat = displaydatetimeformat
        self.readdatetimeformat = readdatetimeformat
        self.readtimeformat = readtimeformat
        self.maxnotelength = maxnotelength
        self.figpath = figpath
        self.annotateallplots = annotateallplots

        self.deck = None
        if config is not None:
            self.deck = command_deck(config)

        # merge the notes arg if needed:
        if isinstance(notes, list):
            if isinstance(notes[0], Note):
                self.notes = self.merge_notes(notes)
            elif isinstance(notes[0], str):
                self.notes = self.merge_notes([Note(note) for note in notes])
        elif isinstance(notes, Note):
            self.notes = notes.data
        elif isinstance(notes, str):
            self.notes = Note(notes).data

        self.notes = dict(sorted(self.notes.items()))

        # configure the offset in timestamping between the log data and notes:
        # log_to_note_offset = 100 # seconds
        # log_to_note_offset = 24*60 # seconds
        # log_to_note_offset = -1440 - 60*1.5
        log_to_note_offset = -1362 # seconds
        # log_to_note_offset = 0

        if isinstance(logfolder, list) and len(logfolder) > 0:
            print(logfolder)
            all_rtd_log = [Log(os.path.join(f, 'housekeeping_rtd.log'), abstimeoffset=datetime.timedelta(seconds=log_to_note_offset)) for f in logfolder]
            all_pow_log = [Log(os.path.join(f, 'housekeeping_pow.log'), abstimeoffset=datetime.timedelta(seconds=log_to_note_offset)) for f in logfolder]

            all_rtd_log = sorted(all_rtd_log, key=lambda l: list(l.data.keys())[0])
            all_pow_log = sorted(all_pow_log, key=lambda l: list(l.data.keys())[0])
            for k in range(0,len(logfolder)):
                if k == 0:
                    self.powlog = all_pow_log[k]
                    self.rtdlog = all_rtd_log[k]
                else:
                    self.powlog.data.update(all_pow_log[k].data)
                    self.rtdlog.data.update(all_rtd_log[k].data)

            # raise NotImplementedError
        elif isinstance(logfolder, str):
            # self.powlog = Log(os.path.join(logfolder, 'housekeeping_pow.log'), abstimeoffset=datetime.timedelta(minutes=24))
            # self.rtdlog = Log(os.path.join(logfolder, 'housekeeping_rtd.log'), abstimeoffset=datetime.timedelta(minutes=24))
            self.powlog = Log(os.path.join(logfolder, 'housekeeping_pow.log'), abstimeoffset=datetime.timedelta(seconds=log_to_note_offset))
            self.rtdlog = Log(os.path.join(logfolder, 'housekeeping_rtd.log'), abstimeoffset=datetime.timedelta(seconds=log_to_note_offset))

        # figure-tuning parameters:
        self.do_volt_rel = True     # display voltage as relative to mean for each channel, rather than absolute
        self.smooth_current_n = 2  # rolling average bin size for current values (which are very noisy)

        self.setup_plot()
        self.provision_data()
        # self.plot_incremental()
        self.plot_all()

    def merge_notes(self, notes: list[Note]):
        """ merge all notes documents into a single time list """
        # NB: all Note.data should use datetime keys, and so can be directly compared/sorted even if the time resolution of the source note is different.
        n = {}
        for note in notes:
            n.update(note.data)
        return n
    
    def setup_plot(self):
        cmap = mpl.colormaps.get_cmap('tab20') # Get a colormap

        # cmap = mpl.colormaps.get_cmap('Set3') # Get a colormap
        # cols = ['#66C5CCFF', '#F6CF71FF', '#F89C74FF', '#DCB0F2FF', '#87C55FFF', '#9EB9F3FF', '#FE88B1FF', '#C9DB74FF', '#8BE0A4FF', '#B497E7FF', '#D3B484FF', '#B3B3B3FF']
        # from matplotlib.colors import ListedColormap
        # cmap = ListedColormap(cols)
        colors = [cmap(i) for i in np.linspace(0, 1, 12)] 
        plt.rcParams['axes.prop_cycle'] = plt.cycler(color=colors)

        self.mosaic = [
            ['cold_data', 'cold_flag', 'hot_data', 'hot_flag', 'opt_data', 'opt_flag', 'curr', 'volt', 'notes'],
            ['cold_data_leg',  'BLANK', 'hot_data_leg',  'BLANK',    'opt_data_leg',  'BLANK',    'curr_leg', 'volt_leg', 'BLANK']
        ]
        self.fig, self.ax = plt.subplot_mosaic(self.mosaic, figsize=(14,8), sharey=True, width_ratios=[4,1,4,1,4,1,4,4,4], height_ratios=[4,1],empty_sentinel='BLANK')
        
        self.legendary_axis_names = [name for name in self.mosaic[0] if 'flag' not in name and 'notes' not in name]
        self.all_axes = (self.ax['cold_data'], self.ax['cold_flag'], self.ax['hot_data'], self.ax['hot_flag'], self.ax['opt_data'], self.ax['opt_flag'], self.ax['curr'], self.ax['volt'], self.ax['notes'])
        self.big_axes = (self.ax['cold_data'], self.ax['hot_data'], self.ax['opt_data'], self.ax['curr'], self.ax['volt'])
        self.flag_axes = (self.ax['cold_flag'], self.ax['hot_flag'], self.ax['opt_flag'])
        
        [ax.set_xlim([-1, 9]) for ax in self.flag_axes]

        self.ax['cold_data'].set_title('Cold focal plane\ntemperatures [ºC]', fontsize='medium')
        self.ax['hot_data'].set_title('Warm detector-end\ntemperatures [ºC]', fontsize='medium')
        self.ax['opt_data'].set_title('Optics-end\ntemperatures [ºC]', fontsize='medium')
        self.ax['curr'].set_title('Current [A]', fontsize='medium')
        self.ax['volt'].set_title('Mean-subtracted\nvoltage [V]' if self.do_volt_rel else 'Voltage [V]', fontsize='medium')
        self.ax['notes'].set_title('Notes', fontsize='medium')
        self.ax['hot_data'].set_yticklabels([])
        self.ax['opt_data'].set_yticklabels([])
        self.ax['curr'].set_yticklabels([])
        self.ax['volt'].set_yticklabels([])

        self.ax['cold_data'].yaxis.set_major_formatter(mpl.dates.DateFormatter('%H:%M:%S'))
        self.ax['cold_data'].set_ylabel('Time')
        
        [ax.grid(visible=True, which='both', axis='both') for ax in self.all_axes]
        [ax.tick_params(axis="x", bottom=True, top=True, labelbottom=True, labeltop=True) for ax in self.all_axes]

        self.ax['notes'].axis('off')

        plt.subplots_adjust(wspace=0.02, hspace=0)
        plt.tight_layout()
   
    def provision_data(self):
        
        self.rtd_times = list(self.rtdlog.data.keys())
        
        self.cold_sensors = [5, 6, 7, 8, 9]
        self.hot_sensors = [1, 2, 3, 4]
        self.opt_sensors = [12, 13, 14, 15, 16, 17, 18, 19, 20]
        self.cold_data = np.zeros((len(self.rtd_times), len(self.cold_sensors)), dtype=np.float32)
        self.cold_flag_data = np.zeros((len(self.rtd_times), 1), dtype=np.float32)
        self.hot_data = np.zeros((len(self.rtd_times), len(self.hot_sensors)), dtype=np.float32)
        self.hot_flag_data = np.zeros((len(self.rtd_times), 1), dtype=np.float32)
        self.opt_data = np.zeros((len(self.rtd_times), len(self.opt_sensors)), dtype=np.float32)
        self.opt_flag_data = np.zeros((len(self.rtd_times), 1), dtype=np.float32)
        for k,key in enumerate(self.rtd_times):
            for s,sensor in zip(range(len(self.cold_sensors)), self.cold_sensors):
                if sensor in self.rtdlog.data[key].keys():
                    if self.rtdlog.data[key][sensor]['flag'] == 1:
                        self.cold_data[k,s] = self.rtdlog.data[key][sensor]['temp']
                    else:
                        self.cold_flag_data[k] += 1
                        self.cold_data[k,s] = np.nan
            for s,sensor in zip(range(len(self.hot_sensors)), self.hot_sensors):
                if sensor in self.rtdlog.data[key].keys():
                    if self.rtdlog.data[key][sensor]['flag'] == 1:
                        self.hot_data[k,s] = self.rtdlog.data[key][sensor]['temp']
                    else:
                        self.hot_flag_data[k] += 1
                        self.hot_data[k,s] = np.nan
            for s,sensor in zip(range(len(self.opt_sensors)), self.opt_sensors):
                if sensor in self.rtdlog.data[key].keys():
                    if self.rtdlog.data[key][sensor]['flag'] == 1:
                        self.opt_data[k,s] = self.rtdlog.data[key][sensor]['temp']
                    else:
                        self.opt_flag_data[k] += 1
                        self.opt_data[k,s] = np.nan

        self.pow_times = list(self.powlog.data.keys())
        self.volt_sensors = [0, 1, 2, 3]
        self.curr_sensors = [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
        self.volt_data = np.zeros((len(self.pow_times), len(self.volt_sensors)), dtype=np.float32)
        self.curr_data = np.zeros((len(self.pow_times), len(self.curr_sensors)), dtype=np.float32)
        self.cmos_curr_data = "time (PDT), CMOS1 current (A), CMOS3 current (A)"
        for k,key in enumerate(self.pow_times):
            for s,sensor in zip(range(len(self.volt_sensors)), self.volt_sensors):
                self.volt_data[k,s] = self.powlog.data[key][sensor]
        for k,key in enumerate(self.pow_times):
            self.cmos_curr_data += '\n' + key.strftime('%b %d %Y %H:%M:%S.%f')
            for s,sensor in zip(range(len(self.curr_sensors)), self.curr_sensors):
                self.curr_data[k,s] = self.powlog.data[key][sensor]
                if 'CMOS' in pow_labels[sensor]:
                    self.cmos_curr_data += ', ' + str(self.curr_data[k,s])

        if self.smooth_current_n > 0:
            for s in range(len(self.curr_sensors)):
                self.curr_data[:,s] = np.convolve(self.curr_data[:,s], np.ones(self.smooth_current_n)/self.smooth_current_n, mode='same')
        
        if self.do_volt_rel:
            for m in range(len(self.volt_sensors)):
                self.volt_data[:,m] = self.volt_data[:,m] - np.mean(self.volt_data[:,m])

    def plot_all(self):
        self.ax['cold_data'].plot(self.cold_data, self.rtd_times, label=[rtd_labels[s] for s in self.cold_sensors])
        self.ax['cold_flag'].plot(self.cold_flag_data, self.rtd_times, color='black')
        self.ax['hot_data'].plot(self.hot_data, self.rtd_times, label=[rtd_labels[s] for s in self.hot_sensors])
        self.ax['hot_flag'].plot(self.hot_flag_data, self.rtd_times, color='black')
        # self.ax['opt_data'].plot(self.opt_data, self.rtd_times, marker='+', markersize=4, label=[rtd_labels[s] for s in self.opt_sensors])
        self.ax['opt_data'].plot(self.opt_data, self.rtd_times, label=[rtd_labels[s] for s in self.opt_sensors])
        self.ax['opt_flag'].plot(self.opt_flag_data, self.rtd_times, color='black')

        [ax.set_xlim([-1, 9]) for ax in self.flag_axes]

        self.ax['volt'].plot(self.volt_data, self.pow_times, label=[pow_labels[s] for s in self.volt_sensors])
        self.ax['curr'].plot(self.curr_data, self.pow_times, label=[pow_labels[s] for s in self.curr_sensors])

        for name in self.legendary_axis_names:
            h,l = self.ax[name].get_legend_handles_labels()
            laxis_name = name + '_leg'
            self.ax[laxis_name].legend(h,l, borderaxespad=0, fontsize='x-small', loc='upper center')
            self.ax[laxis_name].axis('off')

        for note_time in self.notes.keys():
            self.ax['notes'].annotate(
                self.notes[note_time],
                xy=(0,note_time),
                xytext=(0,note_time),
                fontsize='xx-small', ha='left', va='baseline'
            )
            if self.annotateallplots:
                [ax.axhline(note_time, color='black', linewidth=0.1) for ax in self.all_axes]
            else:
                self.ax['notes'].axhline(note_time, color='black', linewidth=0.1)

        self.ax['cold_data'].set_ylim([min(self.rtd_times), max(self.rtd_times)])
        
        startdate = min(self.rtd_times[0], self.pow_times[0])
        self.fig.suptitle(startdate.strftime('%b %d, %Y'), y=0.05)
        
        plt.tight_layout()
        plt.subplots_adjust(wspace=0.02, hspace=0.1)

        if self.figpath is not None:
            picklepath = os.path.splitext(self.figpath)[0] + '.pkl'
            with open(picklepath, 'wb') as file:
                pickle.dump(self.fig, file)

            self.fig.set_size_inches(11,17)
            plt.tight_layout()
            self.fig.savefig(self.figpath, transparent=True)
            self.fig.set_size_inches(14,8)
            plt.tight_layout()
            plt.subplots_adjust(wspace=0.02, hspace=0.1)

        plt.show()

    def plot_incremental(self):
        t = self.rtd_times[1]
        dt = datetime.timedelta(seconds=10)
        just_started = True
        while t < max(self.rtd_times[-1], self.pow_times[-1], list(self.notes.keys())[-1]):
            
            stop_rtd_k = next(x[0] for x in enumerate(self.rtd_times) if x[1] > t)
            stop_pow_k = next(x[0] for x in enumerate(self.pow_times) if x[1] > t)
            stop_note_k = next(x[0] for x in enumerate(list(self.notes.keys())) if x[1] > t)
            self.ax['cold_data'].plot(self.cold_data[:stop_rtd_k], self.rtd_times[:stop_rtd_k], label=[rtd_labels[s] for s in self.cold_sensors])
            self.ax['cold_flag'].plot(self.cold_flag_data[:stop_rtd_k], self.rtd_times[:stop_rtd_k], color='black')
            self.ax['hot_data'].plot(self.hot_data[:stop_rtd_k], self.rtd_times[:stop_rtd_k], label=[rtd_labels[s] for s in self.hot_sensors])
            self.ax['hot_flag'].plot(self.hot_flag_data[:stop_rtd_k], self.rtd_times[:stop_rtd_k], color='black')
            self.ax['opt_data'].plot(self.opt_data[:stop_rtd_k], self.rtd_times[:stop_rtd_k], label=[rtd_labels[s] for s in self.opt_sensors])
            self.ax['opt_flag'].plot(self.opt_flag_data[:stop_rtd_k], self.rtd_times[:stop_rtd_k], color='black')

            self.ax['volt'].plot(self.volt_data[:stop_pow_k], self.pow_times[:stop_pow_k], label=[pow_labels[s] for s in self.volt_sensors])
            self.ax['curr'].plot(self.curr_data[:stop_pow_k], self.pow_times[:stop_pow_k], label=[pow_labels[s] for s in self.curr_sensors])
            for note_time in self.notes.keys():
                if note_time < t:
                    self.ax['notes'].annotate(
                        self.notes[note_time],
                        xy=(0,note_time),
                        xytext=(0,note_time),
                        fontsize='xx-small', ha='left', va='baseline'
                    )
                    self.ax['notes'].axhline(note_time, color='black', linewidth='0.1')
                else:
                    break

            if just_started:
                for name in self.legendary_axis_names:
                    h,l = self.ax[name].get_legend_handles_labels()
                    laxis_name = name + '_leg'
                    self.ax[laxis_name].legend(h,l, borderaxespad=0, fontsize='x-small', loc='upper center')
                    self.ax[laxis_name].axis('off')
                
                just_started = False

            [ax.set_xlim([-1, 9]) for ax in self.flag_axes]
            # self.ax['cold_data'].set_ylim([min(self.rtd_times), max(self.rtd_times)])

            plt.tight_layout()
            t = t + dt
            plt.pause(0.01)

        self.ax['cold_data'].plot(self.cold_data, self.rtd_times, label=[rtd_labels[s] for s in self.cold_sensors])
        self.ax['cold_flag'].plot(self.cold_flag_data, self.rtd_times, color='black')
        self.ax['hot_data'].plot(self.hot_data, self.rtd_times, label=[rtd_labels[s] for s in self.hot_sensors])
        self.ax['hot_flag'].plot(self.hot_flag_data, self.rtd_times, color='black')
        self.ax['opt_data'].plot(self.opt_data, self.rtd_times, label=[rtd_labels[s] for s in self.opt_sensors])
        self.ax['opt_flag'].plot(self.opt_flag_data, self.rtd_times, color='black')

        self.ax['volt'].plot(self.volt_data, self.pow_times, label=[pow_labels[s] for s in self.volt_sensors])
        self.ax['curr'].plot(self.curr_data, self.pow_times, label=[pow_labels[s] for s in self.curr_sensors])

        for name in self.legendary_axis_names:
            h,l = self.ax[name].get_legend_handles_labels()
            laxis_name = name + '_leg'
            self.ax[laxis_name].legend(h,l, borderaxespad=0, fontsize='x-small', loc='upper center')
            self.ax[laxis_name].axis('off')

        for note_time in self.notes.keys():
            self.ax['notes'].annotate(
                self.notes[note_time],
                xy=(0,note_time),
                xytext=(0,note_time),
                fontsize='xx-small', ha='left', va='baseline'
            )
            self.ax['notes'].axhline(note_time, color='black', linewidth='0.1')

        [ax.set_xlim([-1, 9]) for ax in self.flag_axes]
        self.ax['cold_data'].set_ylim([min(self.rtd_times), max(self.rtd_times)])

        plt.tight_layout()

        if self.figpath is not None:
            self.fig.set_size_inches(14,36)
            self.fig.savefig(self.figpath, transparent=True)
            self.fig.set_size_inches(14,8)
            plt.subplots_adjust(wspace=0.02, hspace=0)
            plt.tight_layout()

        plt.show()

    def push(self, dataframe=bytes(), noteline=""):
        pass

if __name__ == "__main__":
    if len(sys.argv) > 1:
        logfolders = ''
        try:
            detect_datetime_folder(sys.argv[1])
            logfolders = sys.argv[1]
        except ValueError:
            all_candidates = os.listdir(sys.argv[1])
            all_paths = [os.path.join(sys.argv[1], c) for c in all_candidates]
            logfolders = [c for c in all_paths if os.path.isdir(c)]
    
    if len(sys.argv) == 3:
        s = StripChart(logfolder=logfolders, notes=sys.argv[2], annotateallplots=True)
    if len(sys.argv) == 4:
        s = StripChart(logfolder=logfolders, notes=sys.argv[2], figpath=sys.argv[3], annotateallplots=False)
    
    cmos_in_file = os.path.abspath(os.path.expanduser('~/Documents/FOXSI/Data/formatter/logs/2025/aug28/cmos_power.csv'))
    cmos_out_file = os.path.abspath(os.path.expanduser('~/Documents/FOXSI/Data/formatter/logs/2025/aug28/cmos_power_window.csv'))
    if cmos_in_file:
        with open(cmos_in_file, 'w') as f:
            f.write(s.cmos_curr_data)
        import csv
        with open(cmos_out_file, newline='') as f:
            reader = csv.reader(f, delimiter=',')
            times = []
            cmos1_current = []
            cmos3_current = []
            for k,row in enumerate(reader):
                if k == 0: continue
                times.append(datetime.datetime.strptime(row[0], '%b %d %Y %H:%M:%S.%f'))
                cmos1_current.append(float(row[1]))
                cmos3_current.append(float(row[2]))
            
            fig,ax = plt.subplots(1,1)
            c1p = ax.plot(times, cmos1_current, linewidth=0.5, label='CMOS 1', color='red')
            c2p = ax.plot(times, cmos3_current, linewidth=0.5, label='CMOS 3', color='blue')
            ax.xaxis.set_major_formatter(mpl.dates.DateFormatter('%H:%M'))
            ax.grid(visible=True, which='both', axis='both')
            ax.set_xlabel('Time (PDT, on Aug 28 2025)')
            ax.set_ylabel('Current [A]')
            ax.set_ylim([0, 1])
            ax.tick_params(axis='x', rotation=45)
            ax.legend()
            plt.tight_layout()
            figsavepath = os.path.join(os.path.dirname(cmos_out_file), 'cmos_power_plot.pdf')
            fig.savefig(figsavepath, transparent=True)