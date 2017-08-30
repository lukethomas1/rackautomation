#!/usr/bin/env python3

# File: node.py
# Author: Luke Thomas
# Date: August 29, 2017
# Description: Superclass for each kind of node (rackspace node, pi node)

# System Imports
from os import path
from subprocess import call, Popen, DEVNULL
from time import sleep

# Third Party Imports

# Local Imports
import functions

class Node:
    def __init__(self, name, user_name, id, ip, platform, gvine_path):
        self.name = name
        self.user_name = user_name
        self.id = id
        self.ip = ip
        self.platform = platform
        self.gvine_path = gvine_path

    def add_to_known_hosts(self):
        loc = path.expanduser("~/.ssh/known_hosts")
        command = "ssh-keygen -R " + self.ip
        call(command, shell=True, stdout=DEVNULL)
        command = "ssh-keyscan -H " + self.ip + " >> " + loc
        call(command, shell=True, stdout=DEVNULL)
        sleep(1)

    def clean_gvine(self, amount):
        command = "cd " + self.gvine_path + " && rm -rf "
        if amount == 1:
            command += (
                "gvine.msg* gvine.frag* " +
                "gvine.sub* delay.txt ack.txt *.cer SeqNbr.txt send.txt received.txt " +
                "statistic.db log* eventlogs/* dbs/* data/*"
            )
        elif amount == 2:
            command += "$(ls -I '*.jar' -I '*.json' -I '*.cer' -I '*pki.db*')"
        elif amount == 3:
            command += "$(ls -I '*.jar' -I '*.json')"
        functions.remote_execute(command, self.ip, self.user_name)

    def delete_gvine_log_file(self):
        command = "cd " + self.gvine_path + " && rm log_*"
        functions.remote_execute(command, self.ip, self.user_name)

    def push_file(self, src_path, dest_path):
        command = "scp " + src_path + " " + self.user_name + "@" + self.ip + ":" + dest_path
        call(command, shell=True, stdout=DEVNULL)

    def remote_delete_events(self):
        command = "cd " + self.gvine_path + " && rm ./dbs/*"
        functions.remote_execute(command, self.ip, self.user_name)

    def remote_start_gvine(self, jar_name):
        command = "cd " + self.gvine_path + " && java -jar " + jar_name + " node" + str(self.id) \
                  + " 500 >> log_node" + str(self.id) + ".txt &"
        functions.remote_execute(command, self.ip, self.user_name)

    ##### GRAPEVINE GVPKI CERTS #####

    # Use paramiko to generate the cert on each node
    def generate_cert(self):
        command = "cd " + self.gvine_path + " && java -jar gvpki.jar generate node" + str(self.id)
        functions.remote_execute(command, self.ip, self.user_name)

    # Use scp to get the cert from each node
    def pull_cert(self):
        from_path = self.user_name + "@" + self.ip + ":" + self.gvine_path + "node" + str(
            self.id) + ".cer"
        to_path = "./keystore/"
        Popen(['scp', from_path, to_path])

    # Use parallel-scp to push certs in parallel
    def push_certs(self, path_to_certs):
        command = "scp " + path_to_certs + " " + self.user_name + "@" + self.ip + ":" + \
                  self.gvine_path
        call(command, shell=True, stdout=DEVNULL)

    def load_certs(self, num_nodes):
        command = (
            "cd {} && for((i=1; i<={}; i=i+1)); do java -jar gvpki.jar " +
            "node node$i load node$i; done"
        ).format(self.gvine_path, num_nodes)
        functions.remote_execute(command, self.ip, self.user_name)

    ##### PARAMETERS FOR AUTOTEST #####

    def remote_set_error_rate(self, error_rate, command_template):
        command = command_template.format(action="-A", rate=str(error_rate))
        functions.remote_execute(command, self.ip, self.user_name)

    def remote_remove_error_rate(self, error_rate, command_template):
        command = command_template.format(action="-D", rate=str(error_rate))
        functions.remote_execute(command, self.ip, self.user_name)
