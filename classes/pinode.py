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
                 iface_prefix, topo_dir=None):
        self.topo_dir = topo_dir
        super().__init__(name, user_name, id, ip, platform, gvine_path, member_subnets, iface_prefix)
        self.setup_gvine()

    def setup_gvine(self, save=None):
        self.add_to_known_hosts()
        self.synchronize_time()

    def start(self, jar_name, save=None):
        self.start_tcpdump()
        super().start(jar_name)

    def synchronize_time(self):
        print("Synchronzing time on node " + self.name)
        date = subprocess.check_output('date', shell=True)
        command = "sudo date -s '%s'" % (date)
        functions.remote_execute_commands(command, self.ip, self.user_name)
