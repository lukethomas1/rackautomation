#!/usr/bin/env python3

# File: racknode.py
# Author: Luke Thomas
# Date: August 29, 2017
# Description: Subclass of node for Rackspace

# System Imports
from os import path
from subprocess import call, Popen, DEVNULL
from time import sleep

# Third Party Imports

# Local Imports
import functions
from classes.node import Node

class RackNode(Node):
    def __init__(self, name, user_name, id, ip, platform, gvine_path, member_subnets, topo_dir):
        self.topo_dir = topo_dir
        super().__init__(name, user_name, id, ip, platform, gvine_path)

    def start(self, jar_name, save=None):
        self.remote_emane(save, "emane_start.sh")
        self.start_tcpdump()
        super().start(jar_name)

    def setup_gvine(self, save=None):
        print("Setting up gvine for " + self.name)
        self.add_to_known_hosts()
        self.remote_create_dir(self.topo_dir + save)
        self.remote_copy_default_config(save)
        self.remote_copy_scenario(save)
        self.remote_copy_platform_xml(save)
        self.remote_copy_emane_scripts(save)

    # Copy default config to topology directory
    def remote_copy_default_config(self, save_folder):
        command = (
            "scp ./default_config/* " + self.user_name + "@" + self.ip +
            ":" + self.topo_dir + save_folder
        )
        call(command, shell=True, stdout=DEVNULL)

    # Copy emane_start.sh and emane_stop.sh to each rackspace node in iplist
    def remote_copy_emane_scripts(self, save_folder):
        start_dir = './topologies/' + save_folder + '/emane_start.sh'
        stop_dir = './topologies/' + save_folder + '/emane_stop.sh'
        to_dir = self.user_name + '@' + self.ip + ':' + self.topo_dir + save_folder + "/"
        Popen(['scp', start_dir, to_dir])
        Popen(['scp', stop_dir, to_dir])

    # Copy corresponding platform#.xml to corresponding rackspace node in iplist
    def remote_copy_platform_xml(self, save_folder):
        file_name = 'platform' + str(self.id) + '.xml'
        from_dir = './topologies/' + save_folder + '/' + file_name
        to_dir = self.user_name + "@" + self.ip + ':' + self.topo_dir + save_folder + \
                 "/platform.xml"
        Popen(['scp', from_dir, to_dir])

    # Copy scenario.eel to each rackspace node in iplist
    def remote_copy_scenario(self, save_folder):
        from_dir = './topologies/' + save_folder + '/scenario.eel'
        to_dir = self.user_name + "@" + self.ip + ':' + self.topo_dir + save_folder + "/"
        Popen(['scp', from_dir, to_dir])

    # Run file on each rackspace node in ip_file file
    def remote_emane(self, save_file, script_file):
        save_path = self.topo_dir + save_file
        command = "cd " + save_path + " && sudo ./" + script_file
        functions.remote_execute(command, self.ip, self.user_name)

    def clean_norm(self):
        command = "cd ~/norm/bin/ && rm *log* outbox/*"
        functions.remote_execute(command, self.ip, self.user_name)

    def stop_all(self, save=None):
        self.remote_emane(save, "emane_stop.sh")
        super().stop_all()

    def start_tcpdump(self):
        commands = []
        for index in range(len(self.member_subnets)):
            iface = "emane" + str(index)
            print("Starting tcpdump on " + self.name + " and iface " + iface)
            command = "sudo nohup tcpdump -i " + iface + " -n udp -w " + self.gvine_path + iface \
                      + ".pcap &>/dev/null &"
            commands.append(command)
        functions.remote_execute_commands(commands, self.ip, self.user_name)
