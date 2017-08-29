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
from node import Node

class RackNode(Node):
    def __init__(self, name, user_name, id, ip, platform, gvine_path):
        self.name = name
        self.user_name = user_name
        self.id = id
        self.ip = ip
        self.platform = platform
        self.gvine_path = gvine_path
        super().__init__(name, user_name, id, ip, platform, gvine_path)

    # Copy default config to topology directory
    def remote_copy_default_config(self, save_folder):
        command = (
            "scp ./default_config/* " + "/home/" + self.user_name + "/GrapeVine/topologies/" +
            save_folder
        )
        call(command, shell=True, stdout=DEVNULL)

    # Copy emane_start.sh and emane_stop.sh to each rackspace node in iplist
    def remote_copy_emane_scripts(self, save_folder):
        start_dir = './topologies/' + save_folder + '/emane_start.sh'
        stop_dir = './topologies/' + save_folder + '/emane_stop.sh'
        to_dir = self.user_name + '@' + self.ip + ':/home/' + \
                 self.user_name + '/GrapeVine/topologies/' + save_folder
        Popen(['scp', start_dir, to_dir])
        Popen(['scp', stop_dir, to_dir])

    # Copy corresponding platform#.xml to corresponding rackspace node in iplist
    def remote_copy_platform_xmls(self, save_folder):
        file_name = 'platform' + str(self.id) + '.xml'
        from_dir = './topologies/' + save_folder + '/' + file_name
        to_dir = self.user_name + "@" + self.ip + ':/home/' + self.user_name + \
                 '/GrapeVine/topologies/' + save_folder + "/platform.xml"
        Popen(['scp', from_dir, to_dir])

    # Copy scenario.eel to each rackspace node in iplist
    def remote_copy_scenario(self, save_folder):
        from_dir = './topologies/' + save_folder + '/scenario.eel'
        to_dir = self.user_name + "@" + self.ip + ':/home/' + \
                 self.user_name + '/GrapeVine/topologies/' + save_folder + "/"
        Popen(['scp', from_dir, to_dir])

    # Run file on each rackspace node in ip_file file
    def remote_emane(self, save_file, script_file):
        save_path = '~/GrapeVine/topologies/' + save_file
        command = "cd " + save_path + " && sudo ./" + script_file
        functions.remote_execute(command, self.ip, self.user_name)

    def clean_norm(self):
        commands = ["cd ~/norm/bin/outbox && rm *", "cd ~/norm/bin && rm *log*"]
        functions.remote_execute_commands(commands, self.ip, self.user_name)
