#!/usr/bin/env python3

# File: statsuite.py
# Author: Luke Thomas
# Date: April 6, 2017
# Description: This file is used for stats from emane tests

# System Imports
import time
import os
import math
import subprocess

# 3rd Party Imports
import plotly
import paramiko

def get_time():
    milliseconds = time.time()
    seconds = math.floor(milliseconds)
    return seconds

##### Delay Statistics #####

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

##### EMANE Statistics #####

def generate_emane_stats(node_prefix, save_folder, num_nodes, iplist):
    key = paramiko.RSAKey.from_private_key_file("/home/joins/.ssh/id_rsa")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    for index in range(1, num_nodes + 1):
        ssh.connect(iplist[index - 1], username="emane-01", pkey=key)

        # Make stats directory
        command = (
            "cd /home/emane-01/GrapeVine/topologies/" + save_folder +
            "/data/ && mkdir stats"
        )
        stdin, stdout, stderr = ssh.exec_command(command)

        # Generate emane 'show'
        command = (
            "emanesh " + node_prefix + str(index) + " show"
            " > /home/emane-01/GrapeVine/topologies/" + save_folder +
            "/data/stats/emane.show"
        )
        stdin, stdout, stderr = ssh.exec_command(command)

        # Generate emane 'stats'
        command = (
            "emanesh " + node_prefix + str(index) + " get stats '*' all"
            " > /home/emane-01/GrapeVine/topologies/" + save_folder +
            "/data/stats/emane.stats"
        )
        stdin, stdout, stderr = ssh.exec_command(command)

        # Generate emane 'tables'
        command = (
            "emanesh " + node_prefix + str(index) + " get tables '*' all"
            " > /home/emane-01/GrapeVine/topologies/" + save_folder +
            "/data/stats/emane.tables"
        )
        stdin, stdout, stderr = ssh.exec_command(command)
        ssh.close()


def copy_emane_stats(node_prefix, save_folder, num_nodes, iplist):
    for index in range(0, num_nodes):
        node_ip = iplist[index]
        dest_dir = './stats/emane/' + save_folder + "/" + node_prefix + str(index + 1)
        from_dir = (
            'root@' + node_ip + ':/home/emane-01/GrapeVine/topologies/'
            + save_folder + '/data/stats/'
        )
        print("Copying from node" + str(index + 1))
        subprocess.Popen(['scp', '-r', from_dir, dest_dir])
        time.sleep(1)
