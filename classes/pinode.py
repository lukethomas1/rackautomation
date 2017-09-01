from os import path
from subprocess import call, Popen, DEVNULL
from time import sleep

# Third Party Imports

# Local Imports
import functions
from classes.node import Node

class PiNode(Node):
    def __init__(self, name, user_name, id, ip, platform, gvine_path, member_subnets, topo_dir=None):
        super().__init__(name, user_name, id, ip, platform, gvine_path, member_subnets)

    def setup_gvine(self, save=None):

    	#do pi specific set up
    	return

    def start(self, jar_name, save=None):
        self.start_tcpdump()
        super().start(jar_name)


    def start_tcpdump(self):
        commands = []
        for index in range(len(self.member_subnets)):
            iface = "wlan1"# + str(index)
            print("Starting tcpdump on " + self.name + " and iface " + iface)
            command = "sudo nohup tcpdump -i " + iface + " -n udp -w " + self.gvine_path + iface \
                      + ".pcap &>/dev/null &"
            commands.append(command)
        functions.remote_execute_commands(commands, self.ip, self.user_name)