import os, sys
import numpy as np
from matplotlib import pyplot as plt

import pprint

from ..rtd.rtd import Parser
from external.telemetry_tools.parsers.RTDparser import rtdparser

if __name__ == "__main__":
    f = sys.argv[1]
    print('reading from ', f)
    with open(f, 'rb') as d:
        strdata = d.read().hex()
    gse_parse = rtdparser(strdata)
    loc_parse = Parser(f)

    pprint.pprint(gse_parse[0])
    pprint.pprint(loc_parse.rtd_data[1][5]['unixtime'].hex())