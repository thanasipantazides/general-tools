import os, sys, time, datetime
import re, json
import pprint

"""
    Ingest a folder containing a GSE-FOXSI-4 uplink log file, and output a relabeled uplink log file in which:
    - timestamps are converted to absolute time (using folder name and offsets)
    - command codes are annotated with their system name and command name (as text)
"""

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
    print("\nbuilt command deck")
    return deck

def detect_datetime(name):
    """
    Tries to find datetime string in the format
    "DAY-MONTH-YEAR_HOUR-MINUTE-SECOND/" along the filepath in `self.name`.
    If found, store datetime value in `self.start`.
    """
    path = os.path.normpath(name)
    try:
        folders = re.findall("\d+\-\d+\-\d+\_\d+\-\d+\-\d+", path)
        if len(folders) > 0:
            candidate = folders[-1]
        else:
            raise ValueError

        date = datetime.datetime.strptime(candidate, "%d-%m-%Y_%H-%M-%S")
        start = date
    except:
        print("couldn't infer datetime")
        start = None
    return start



if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("\nrun like this:\n>\tpython relabel.py uplink/log/folder/28-8-2025_11-35-1 path/to/output/file.log")
    print("reading from:", sys.argv[1])
    print("writing to:", sys.argv[2])
    start = detect_datetime(sys.argv[1])
    deck = command_deck(os.path.join(os.path.dirname(__file__), '..', '..', 'external', 'foxsi4-commands'))

    times = []
    commands = []
    systems = []
    names = []

    ostream = ""

    print("start:", start)

    with open(os.path.join(sys.argv[1], 'uplink.log'), 'r') as uplink_file:
        for line in uplink_file.readlines():
            try:
                tstamp = re.search('\[(.+?)\]', line).group(1)
            except AttributeError:
                continue
            
            raw_time = datetime.datetime.strptime(tstamp, "%H:%M:%S.%f")
            delta = datetime.timedelta(days=0.0, hours=raw_time.hour, minutes=raw_time.minute, seconds=raw_time.second)
            # time_mv = datetime.datetime.combine(start, raw_time.time())
            time_mv = start + delta
            print(time_mv)
            times.append(time_mv)
            cmd_raw = line.split(' ', 1)[1].rstrip()
            commands.append(cmd_raw)
            cmd_raw_int = int(cmd_raw, base=16)
            sys_int = (cmd_raw_int >> 8) & 0xff
            cmd_int = (cmd_raw_int >> 0) & 0xff

            sys_name = deck[sys_int]["name"]
            cmd_name = deck[sys_int]["commands"][cmd_int]
            
            # optional offset to add to the recorded time:
            delta = datetime.timedelta(minutes=-25)
            time_mv += delta

            otime = datetime.datetime.strftime(time_mv, '%H:%M:%S')

            ostream = ostream + otime + ' - ' + sys_name + ' > ' + cmd_name + ' (' + cmd_raw + ')\n'

    with open(sys.argv[2], 'w') as output_file:
        output_file.write(ostream)

