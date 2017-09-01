from os import path
from subprocess import call, Popen, DEVNULL
from time import sleep

# Third Party Imports

# Local Imports
import functions
from classes.node import Node

class PiNode(Node):
    def __init__(self, name, user_name, id, ip, platform, gvine_path, topo_dir=None):
        self.name = name
        self.user_name = user_name
        self.id = id
        self.ip = ip
        self.platform = platform
        self.gvine_path = gvine_path
        self.topo_dir = topo_dir
        # super().__init__(name, user_name, id, ip, platform, gvine_path)

    def setup_gvine(self, save=None):

    	#do pi specific set up
    	return


