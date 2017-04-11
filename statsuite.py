#!/usr/bin/env python3

# File: statsuite.py
# Author: Luke Thomas
# Date: April 6, 2017
# Description: This file is used for stats from emane tests

import time
import os
import math
import plotly

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


def parse_delayfiles(folder_path, num_nodes):
    delays = []
    for index in range(1, num_nodes + 1):
        path = folder_path + "/delay" + str(index) + ".txt"
        print(path)
        if(os.path.isfile(path)):
            delay_file = open(path)
            delay_text = delay_file.read()
            delay_file.close()
            delay_list = delay_text.split(" ")
            curr_node_list = []
            for index in range(len(delay_list) + 1):
                # Every 5th element is the actual value
                if(index % 5 == 4):
                    curr_node_list.append(delay_list[index])
            delays.append(curr_node_list)
    return delays


def scatter_plot(delays):
    x = []
    y = []

    for i in range(1, len(delays) + 1):
        for j in range(len(delays[i - 1])):
            x.append(i)
            y.append(delays[i - 1][j])

    trace = plotly.graph_objs.Scatter(
            x = x,
            y = y,
            mode = 'markers'
        )

    data = [trace]

    plotly.plotly.iplot(data, filename='basic-scatter')
