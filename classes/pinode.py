from os import path
from subprocess import call, Popen, DEVNULL
from time import sleep
import subprocess
import os

# Third Party Imports

# Local Imports
import functions
from classes.node import Node

class PiNode(Node):
    def __init__(self, name, user_name, id, ip, platform, gvine_path, member_subnets,
                 iface_prefix, iface_index, jar_file, api_jar, topo_dir=None):
        self.topo_dir = topo_dir
        super().__init__(name, user_name, id, ip, platform, gvine_path, member_subnets,
                         iface_prefix, iface_index, jar_file, api_jar)

    def setup_gvine(self, save=None):
        self.add_to_known_hosts()
        self.synchronize_time()
        index = 0
        for subnet in self.member_subnets:
            subnet_num = 54 + subnet['number']
            adhoc_ip = "192.168." + str(subnet_num) + "." + str((200 + self.id) % 256)
            self.adhoc_config_start(self.iface_prefix + str(index), subnet['name'], adhoc_ip)
            index += 1

    def clean_setup(self):
        index = 0
        for subnet in self.member_subnets:
            subnet_num = 54 + subnet['number']
            adhoc_ip = "192.168." + str(subnet_num) + "." + str((200 + self.id) % 256)
            self.adhoc_config_stop(self.iface_prefix + str(index), subnet['name'], adhoc_ip)
            index += 1

    def start(self, save=None):
        self.start_tcpdump()
        super().start()

    def start_refactor(self, save=None):
        self.start_tcpdump()
        super().remote_start_refactor()

    def stop(self, save):
        super().stop_all(save)
        # adhoc_ip = "192.168.54." + str((200 + self.id) % 256)
        # self.adhoc_config_stop("wlan0", "subnet1", adhoc_ip)

    def synchronize_time(self):
        print("Synchronizing time on node " + self.name)
        date = subprocess.check_output('date', shell=True)
        command = "sudo date -s '%s'" % (date)
        functions.remote_execute_commands(command, self.ip, self.user_name)

    def adhoc_config_start(self, interface, subnet, ip, mask="255.255.255.0"):
        print("Starting adhoc")
        # Make the commands
        commands = [
            "sudo ip link set {iface} down",
            "sudo iwconfig {iface} mode ad-hoc",
            "sudo iwconfig {iface} essid {subnet}",
            "sudo ip link set {iface} up",
            "sudo ifconfig {iface} {ip} netmask {mask}"
        ]
        # Fill the strings with the parameters
        for index in range(len(commands)):
            commands[index] = commands[index].format(iface=interface, subnet=subnet, ip=ip,
                                                     mask=mask)
        # Execute the commands
        for command in commands:
            print(command)
            functions.remote_execute(command, self.ip, self.user_name)

    def adhoc_config_stop(self, interface, subnet, ip, mask="255.255.255.0"):
        print("Stopping adhoc")
        commands = [
            "sudo ip link set {iface} down",
            "sudo iwconfig {iface} mode managed",
            "sudo iwconfig {iface} essid off",
            "sudo ip addr flush dev {iface}",
            "sudo service networking start",
            "sudo ifup --force {iface}"
        ]
        # Fill the strings with the parameters
        for index in range(len(commands)):
            commands[index] = commands[index].format(iface=interface, subnet=subnet, ip=ip,
                                                     mask=mask)
        # Execute the commands
        for command in commands:
            print(command)
            functions.remote_execute(command, self.ip, self.user_name)

    def ex_command(self, command):
        functions.remote_execute(command, self.ip, self.user_name, True, True)

