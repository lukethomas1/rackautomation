#!/usr/bin/env python3

# File: statsuite.py
# Author: Luke Thomas
# Date: April 6, 2017
# Description: This file is used for stats from emane tests

import time
import os
import math

def get_time():
    milliseconds = time.time()
    seconds = math.floor(milliseconds)
    return seconds


def retrieve_delayfiles(iplist, path_to_delay, dest_path):
    for index in range(len(iplist)):
        ip = iplist[index]
        command = "scp emane-01@" + ip + ":" + path_to_delay + " "
        command += dest_path + "/delay" + str(index + 1) + ".txt"
        os.system(command)
