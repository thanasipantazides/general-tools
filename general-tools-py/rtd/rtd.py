import sys, os, datetime, re
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

labels = {
    1: {
        0: 'timepix',
        1: 'saas camera',
        2: 'formatter pi',
        3: '5.5 V regulator',
        4: 'focal position 5',
        5: 'focal position 4',
        6: 'focal position 3',
        7: 'focal position 2',
        8: 'ln2 inlet',
    },
    2: {
        8: 'optic plate',
        7: 'optic position 6 front',
        6: 'optic position 6 plate',
        5: 'optic position 2 plate',
        4: 'optic position 4 front',
        3: 'optic position 4 plate',
        2: 'optic position 0 collimator',
        1: 'optic position 0 front',
        0: 'optic position 0 plate'
    }
}

flag_values = {
    1 << 0: "valid",
    1 << 1: "ADC out of range",
    1 << 2: "under range",
    1 << 3: "over range",
    1 << 4: "CJ soft fault",
    1 << 5: "CJ hard fault",
    1 << 6: "ADC hard fault",
    1 << 7: "sensor hard fault"
}

ranges = {
    1: (-30,60),
    2: (21, 24)
}

class Parser:
    def __init__(self, file: str):
        """
        Parse RTD data from the provided `file`.

        Parameters
        ----------
        `file`: a path to the file that should be parsed.

        Populates a field called `self.rtd_data`, which is
        a poorly-designed nested `dict`. `self.rtd_data` has
        two top-level keys, one per RTD chip on the Housekeeping
        board. These are `1` and `2`. The value for each top-
        level key is a `list` of `dict`s for each measurement.
        A measurement is a `dict` with two keys: `'unixtime'` and
        `'data'`.

        Looks like this:
        {
            1: [{
                    'unixtime': b'\x01\x23\x45\x67',
                    'data': {
                        0: {'flag': 0, 'temp': 15361.0},
                        1: {'flag': 240, 'temp': 256.0},
                        2: {'flag': 4, 'temp': 0.234375},
                        3: {'flag': 0, 'temp': 60.00390625},
                        4: {'flag': 0, 'temp': 15361.0},
                        5: {'flag': 240, 'temp': 256.0},
                        6: {'flag': 4, 'temp': 0.234375},
                        7: {'flag': 0, 'temp': 60.09765625},
                        8: {'flag': 0, 'temp': 15385.0}
                    }
                },
                {
                    'unixtime': b'\x01\x23\x45\x67',
                    'data': {
                        0: {'flag': 0, 'temp': 15361.0},
                        1: {'flag': 240, 'temp': 256.0},
                        2: {'flag': 4, 'temp': 0.234375},
                        3: {'flag': 0, 'temp': 60.00390625},
                        4: {'flag': 0, 'temp': 15361.0},
                        5: {'flag': 240, 'temp': 256.0},
                        6: {'flag': 4, 'temp': 0.234375},
                        7: {'flag': 0, 'temp': 60.09765625},
                        8: {'flag': 0, 'temp': 15385.0}
                    }
                },
            ]
            2: ...
        }
        """

        frame_size = 42
        self.name = file
        self.start = None

        print("parsing", file, "...")

        with open(file, 'rb') as source:
            data = source.read()

            # a key for each RTD chip on the Housekeeping board
            output = {1:[], 2:[]}

            for block in range(len(data) // frame_size):
                # an index back into source `data`:
                global_index = block*frame_size

                # each frame will have an associated `unixtime` and `data`
                # (`data` stores the error and raw data from the measurement)
                inner_structure = {
                    'unixtime': data[global_index+2:global_index+6],
                    'data': {}
                }
                # actual data (not `unixtime`) starts 6 bytes into the frame
                local_offset = 6
                
                for local_index in range(9):
                    this_index = global_index + local_offset + local_index*4
                    # a flag value != 1 is cause to suspect the measurement
                    this_flag = data[this_index]
                    # convert the temperature from raw to º Celsius
                    this_temp_raw = int.from_bytes(data[this_index + 1:this_index + 4], 'big')
                    if this_temp_raw & (1 << 23):
                        this_temp_raw = (~this_temp_raw & 0xffffff)
                        this_temp_raw = -this_temp_raw + 1
                    this_temp = this_temp_raw / 1024
                    # store the flag and temperature data:
                    inner_structure['data'][local_index] = {'flag': this_flag, 'temp': this_temp}
                output[data[global_index]].append(inner_structure)

            self.rtd_data = output
            self.detect_datetime()

    def detect_datetime(self):
        """
        Tries to find datetime string in the format
        "DAY-MONTH-YEAR_HOUR-MINUTE-SECOND/" along the filepath in `self.name`.
        If found, store datetime value in `self.start`.
        """
        path = os.path.normpath(self.name)
        try:
            folders = re.findall("\d+\-\d+\-\d+\_\d+\-\d+\-\d+", path)
            if len(folders) > 0:
                candidate = folders[-1]
            else:
                raise ValueError

            print(candidate)
            date = datetime.datetime.strptime(candidate, "%d-%m-%Y_%H-%M-%S")
            self.start = date
        except:
            print("couldn't infer datetime")
            self.start = None

class Plotter:
    def __init__(self, root_folder: str, notes=None):
        """
        Recursively search for all files named `housekeeping_rtd.log` under the provided `root_folder`, and plot temperature histories and difference histograms for each.
        """
        self.root_folder = root_folder
        files = self.find("housekeeping_rtd.log")
        # print("found files:")
        # [print(file) for file in files]
        if len(files) == 0:
            print("Found no housekeeping_rtd.log files under the prefix. Exiting.")

        self.data = [Parser(file) for file in files]
        self.data = sorted(self.data, key=lambda s: s.start)
        self.notes = notes
        self.fig = []
        self.ax = []
        self.plot()
        # if notes is not None:
        #     self.annotate_log(notes)
        plt.show()

    def find(self, name: str):
        result = []
        for root, dirs, files in os.walk(self.root_folder):
            if name in files:
                result.append(os.path.join(root, name))
        return result
    
    def annotate_log(self, notes: str, fig, ax, chip):
        max_note_length = 40
        
        mdy = self.data[0].start
        mdy_start = datetime.datetime.combine(mdy.date(), datetime.time.min)
        with open(notes, 'r') as fnote:
            ylim = ax.get_ylim()
            new_ylim = (ylim[1] - (ylim[1] - ylim[0])*4/3, ylim[1])
            offset = (new_ylim[1] - new_ylim[0])*0.01

            for line in fnote.readlines():
                if line.isspace():
                    continue
                time = line.split("-",1)[0].lstrip().rstrip()
                text = line.split("-",1)[1].lstrip().rstrip()
                if len(text) > max_note_length:
                    text = text[:max_note_length - 3] + '...'
                
                timed = datetime.datetime.strptime(time, "%H:%M:%S")
                time_mv = datetime.datetime.combine(mdy_start, timed.time())

                ax.set_ylim(new_ylim)
                ax.axvline(time_mv, color='black', linewidth='0.1')
                ax.text(time_mv, new_ylim[0] + offset, text, fontsize='xx-small', rotation=90, ha='left', va='baseline')
            
            fig.set_size_inches(100, 6)
            fig.savefig(os.path.join(os.path.dirname(os.path.abspath(self.root_folder)), 'rtd_cs'+str(chip)+'_notes.pdf'), transparent=True)


    def plot(self, aggregate_plot=True, save_plot=True, diff_plot=False):
        total_time = [[],[]]
        total_flag = [np.zeros([0,8,9], dtype=np.uint32), 
                      np.zeros([0,8,9], dtype=np.uint32)]
        total_temp = [np.empty([0,9], dtype=np.float32),
                       np.empty([0,9], dtype=np.float32)] # time by channel by chip
        for chip in [1,2]:
            chip_index = chip - 1
            for pack in self.data:
                rtd_src = pack.rtd_data[chip]

                unixtimes = np.array([int.from_bytes(field['unixtime'],'big') for field in rtd_src], dtype=np.uint32)
                if unixtimes.size == 0:
                    continue

                times = unixtimes - np.min(unixtimes)
                if pack.start is not None:
                    times = [pack.start + datetime.timedelta(seconds=time.item()) for time in times]
                    title_text = pack.start.strftime("%B %d %Y %H:%M:%S")
                else:
                    title_text = pack.name

                total_time[chip_index].extend(times)

                temps = np.zeros([len(rtd_src), 9], dtype=np.float32)
                flags = np.zeros([len(rtd_src), 9], dtype=np.uint8)
                diffs = np.zeros([len(rtd_src), 9], dtype=np.float32)

                # total_flag[chip_index].resize([len(rtd_src), 8, 9])

                ch_slice_flag = np.zeros([1,8,9], dtype=np.uint32)
                for i,record in enumerate(rtd_src):
                    for j,sensor in enumerate(record['data'].keys()):
                        # record sensor value and error flag for each sensor at each time.
                        temps[i][j] = record['data'][sensor]['temp']
                        flags[i][j] = record['data'][sensor]['flag']

                        if i > 0:
                            # record change in each sensor value from one index to the next
                            diffs[i - 1][j] = temps[i][j] - temps[i - 1][j]

                        if flags[i][j] != 1:
                            temps[i][j] = np.nan

                        for k, key in enumerate(flag_values.keys()):
                            ch_slice_flag[0,k,j] = ((key & flags[i][j]) != 0)
                            # total_flag[chip_index][k, j] += ((key & flags[i][j]) != 0)
                        
                    # total_flag[chip_index][i] = ch_slice_flag
                    # total_flag[chip_index].extend(ch_slice_flag)
                    total_flag[chip_index] = np.concatenate((total_flag[chip_index], ch_slice_flag), axis=0)
                        # if (flags[i][j] & 1) != 1:
                        #     temps[i][j] = np.nan

                # pad with nans before going on to next pack of data (for plot breaks where there is a data jump)
                total_temp[chip_index] = np.append(total_temp[chip_index], temps, axis=0)
                total_time[chip_index].append(total_time[chip_index][-1])
                temp_nans = np.empty([1,9])
                temp_nans.fill(np.nan)
                total_temp[chip_index] = np.append(total_temp[chip_index], temp_nans, axis=0)
                flag_nans = np.zeros([1,8,9])
                # flag_nans.fill(np.nan)
                total_flag[chip_index] = np.append(total_flag[chip_index], flag_nans, axis=0)

                print("flag", np.shape(total_flag[chip_index]))
                print("time", np.shape(total_time[chip_index]))
                print("temp", np.shape(total_temp[chip_index]))

                # plt.rcParams['text.usetex'] = True
                if not aggregate_plot:
                    fig, ax = plt.subplots(figsize=(12,6))

                    ax.plot(times, temps)
                    ax.set(
                        xlabel="Time",
                        ylabel="Temperature (ºC)",
                        ylim=(-30,60)
                    )
                    plt.title(title_text + ", chip " + str(chip), fontsize=10)
                    plt.xlabel(r"$\text{Time}$")
                    plt.ylabel("Temperature (ºC)")
                    plt.xticks(rotation=45)
                    plt.grid(which='major', axis='y')
                    plt.legend(labels[chip].values())

                    if diff_plot:
                        figh, axh = plt.subplots()
                        axh.hist(diffs)
                        plt.title(title_text + ", chip " + str(chip), fontsize=10)
                        plt.xlabel(r"$T[i] - T[i - 1] \ \text{(ºC)}$")
                        plt.ylabel("Counts")
                        plt.legend(labels[chip].values())
                    
                    if save_plot:
                        plt.savefig(os.path.join(os.path.dirname(os.path.abspath(self.root_folder)), 'rtd_cs'+str(chip)+'.pdf'))
        
        if aggregate_plot:
            for chip in self.data[0].rtd_data:
                fig, (eax, ax) = plt.subplots(2,1,figsize=(12,6), sharex=1, height_ratios=[1,3])
                ax_label_font_size = 'medium'
                ax.plot(total_time[chip-1], total_temp[chip-1])
                ax.set(
                    xlabel="Time",
                    ylabel="Temperature (ºC)",
                    ylim=ranges[chip]
                )
                # plt.title(title_text + ", chip " + str(chip), fontsize=10)
                # title_prefix = self.data[chip - 1].start.strftime("%B %d %Y - chip ")
                # plt.title(title_prefix + str(chip), fontsize=10)
                plt.xlabel(r"$\text{Time}$", fontsize=ax_label_font_size)
                plt.ylabel("Temperature (ºC)", fontsize=ax_label_font_size)
                plt.xticks(rotation=45)
                plt.grid(which='major', axis='y')
                startx = int(round(len(total_time[chip-1])*7/16))
                # startx=0
                ax.set_xlim(total_time[chip-1][startx], total_time[chip-1][len(total_time[chip-1]) - 1])
                ax.xaxis.set_major_formatter(mpl.dates.DateFormatter('%H:%M:%S'))
                plt.legend(labels[chip].values(), loc='lower left', fontsize='x-small')

                # error rate plots
                rect_flag = np.nan_to_num(total_flag[chip-1])
                time_d = [td.total_seconds() for td in np.diff(total_time[chip-1])]
                error_rate = np.diff(np.cumsum(np.sum(rect_flag[:,1::,:], axis=(1,2)), axis=0)) / time_d

                eax.plot(total_time[chip-1][1::], error_rate, color='black')
                eax.set_ylabel(r'$\text{Total error rate} \ [s^{-1}]$', fontsize=ax_label_font_size)
                title_prefix = self.data[chip - 1].start.strftime("%B %d %Y - chip ")
                eax.set_title(title_prefix + str(chip), fontsize='medium')
                eax.grid(visible=True, which='major', axis='y')
                fig.align_ylabels([eax,ax])

                plt.tight_layout()

                hfig, haxs = plt.subplots(9,1,figsize=(5,8))
                for p,hax in enumerate(haxs.reshape(-1)):
                    
                    bin_values = [flag_values[k] for k in flag_values.keys()]
                    if p < len(haxs) - 1:
                        hax.axes.get_xaxis().set_visible(False)
                    
                    agg_flag = np.sum(total_flag[chip-1][startx::,:,p], axis=0)
                    # hax.bar(bin_values, total_flag[chip-1][:,p])
                    hax.bar(bin_values, agg_flag, color='black')
                    hax.set_ylabel('Counts')
                    hax.set_title(labels[chip][p], size='small')
                    # plt.setp( hax. yaxis.get_label(), rotation=0, ha='right' )
                    plt.setp(hax.xaxis.get_ticklabels(), size='x-small')
                    plt.setp(hax.yaxis.get_ticklabels(), size='x-small')
                    plt.setp(hax.xaxis.get_label(), size='small')
                    plt.setp(hax.yaxis.get_label(), size='small')
                plt.xticks(rotation=90)
                # plt.grid(which='major', axis='y')
                hfig.tight_layout()

                

                if save_plot:
                    fig.savefig(os.path.join(os.path.dirname(os.path.abspath(self.root_folder)), 'rtd_cs'+str(chip)+'.pdf'), transparent=True)
                    hfig.savefig(os.path.join(os.path.dirname(os.path.abspath(self.root_folder)), 'rtd_cs'+str(chip)+'_flaghist.pdf'), transparent=True)
                
                if self.notes is not None:
                    self.annotate_log(self.notes, fig, ax, chip)



if __name__ == "__main__":
    if len(sys.argv) > 1:
        print("Digging under prefix", sys.argv[1])
        if len(sys.argv) > 2:
            p = Plotter(sys.argv[1], sys.argv[2])
        else:
            p = Plotter(sys.argv[1])
