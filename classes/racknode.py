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
    def __init__(self, name, user_name, id, ip, platform, gvine_path, member_subnets, iface_prefix,
                 topo_dir=None):
        self.topo_dir = topo_dir
        super().__init__(name, user_name, id, ip, platform, gvine_path, member_subnets, iface_prefix)

    def start(self, jar_name, save=None):
        self.remote_emane(save, "emane_start.sh")
        self.start_tcpdump()
        super().start(jar_name)

    def start_refactor(self, jar_name, save=None):
        self.remote_emane(save, "emane_start.sh")
        self.start_tcpdump()
        config = "good.json"
        super().remote_start_refactor(jar_name, config)

    def start_partial(self, jar_name, save=None):
        self.remote_emane(save, "emane_start.sh")
        super().remote_start_gvine(jar_name)

    def stop_partial(self, save=None):
        self.remote_emane(save, "emane_stop.sh")
        super().stop_gvine()

    def setup_gvine(self, save=None):
        print("Setting up gvine for " + self.name)
        self.add_to_known_hosts()
        self.remote_create_dir(self.topo_dir)
        self.remote_create_dir(self.topo_dir + save)
        self.remote_copy_default_config(save)
        self.remote_copy_scenario(save)
        self.remote_copy_platform_xml(save)
        self.remote_copy_emane_scripts(save)

    def setup_emane(self, save):
        self.remote_copy_default_config(save)
        self.remote_copy_scenario(save)
        self.remote_copy_platform_xml(save)

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

    def generate_emane_stats(self, save):
        command = (
            "cd /home/emane-01/emane/topologies/" + save +
            "/data/ && mkdir stats"
        )
        functions.remote_execute(command, self.ip, self.user_name)

        command = (
            "emanesh " + self.name +
            " show > /home/emane-01/emane/topologies/" + save +
            "/data/stats/emane.show"
        )
        functions.remote_execute(command, self.ip, self.user_name)

        command = (
            "emanesh " + self.name + " get stat '*' all"
            " > /home/emane-01/emane/topologies/" + save +
            "/data/stats/emane.stats"
        )
        functions.remote_execute(command, self.ip, self.user_name)

        command = (
            "emanesh " + self.name + " get table '*' all"
            " > /home/emane-01/emane/topologies/" + save +
            "/data/stats/emane.tables"
        )
        functions.remote_execute(command, self.ip, self.user_name)

    def copy_emane_stats(self, save):
        dest_dir = './stats/emane/' + save + "/" + self.name
        from_dir = (
            self.user_name + '@' + self.ip + ':/home/emane-01/emane/topologies/'
            + save + '/data/stats/*'
        )
        Popen(['scp', '-r', from_dir, dest_dir])

    ##### IPTABLES #####

    def get_interface_name(self, subnet_name):
        index = 0
        for subnet in self.member_subnets:
            index += 1
            if (subnet["name"] == subnet_name):
                return "emane" + str(index)

    def get_block_subnet_command(self, subnet_name, block_input):
        interface_name = self.get_interface_name(subnet_name)
        if interface_name is None:
            print("Failed to find subnet with name: " + subnet_name)
            return
        if block_input:
            command = "sudo iptables -I INPUT -i {} -j DROP".format(interface_name)
        else:
            command = "sudo iptables -I OUTPUT -o {} -j DROP".format(interface_name)
        return command

    # Important note: we can't block output to this node because GrapeVine sends multicast,
    # therefore must block input on both nodes
    def get_block_node_input_commands(self, other_node_object):
        commands = []
        for subnet in self.member_subnets:
            for other_subnet in other_node_object.member_subnets:
                if subnet["number"] == other_subnet["number"]:
                        interface_name = self.get_interface_name(subnet["name"])
                        node_ip = subnet["addr"] + "." + str(other_node_object.id)
                        command = "sudo iptables -I INPUT -i {} -s {} -j DROP".format(interface_name, node_ip)
                        commands.append(command)
        return commands

    def block_node(self, other_node_object):
        commands = self.get_block_node_input_commands(other_node_object)
        for command in commands:
            print(self.name + ": " + command)
            functions.remote_execute(command, self.ip, self.user_name)

    def block_subnet(self, subnet_name):
        input_command = self.get_block_subnet_command(subnet_name, True)
        output_command = self.get_block_subnet_command(subnet_name, False)
        print(self.name + ": " + input_command)
        print(self.name + ": " + output_command)
        functions.remote_execute(input_command, self.ip, self.user_name)
        functions.remote_execute(output_command, self.ip, self.user_name)

    def reset_iptables(self):
        command = "sudo iptables -F"
        functions.remote_execute(command, self.ip, self.user_name)