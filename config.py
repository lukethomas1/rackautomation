# Used for rackspace node naming and some other naming, will break things if changed
DEFAULT_PLATFORM = "rack"
NODE_PREFIX = "node"

SAVE_FILE = "58flat"
JUPYTER_SAVE_FILE = "threenodes"
PCAP_SAVE_FILE = "threenodes"

IMAGE_NAME = "10KbpsPCR"

# User input variable
PI_USERNAME = "pi"
RACK_USERNAME = "emane-01"

REMOTE_GVINE_DIR = "~/test/emane/gvine/node/"
REMOTE_EMANE_DIR = "~/GrapeVine/topologies/" + SAVE_FILE + "/"

RACK_KEY = "mykey"

JAR_FILE = "gvine-fast.jar"

# Where to find the ip file for all the rackspace nodes
RACK_IP_FILE = "./iplists/" + NODE_PREFIX + "hosts"
PI_IP_FILE = "./iplists/pi-ipfile"

PI_IP_LIST = ["192.168.1.31", "192.168.1.32", "192.168.1.33", "192.168.1.34", "192.168.1.35",
              "192.168.1.36", "192.168.1.37", "192.168.1.38", "192.168.1.39", "192.168.1.40",
              "192.168.1.41", "192.168.1.42", "192.168.1.43"]

# Subnet Ip Blacklist
IP_BLACK_LIST = [
    "10.0.3",
    "23.253.107",
    "192.168.3",
    "127.0.0"
]

##### AUTOMATIC TESTING #####

NUM_INDICES = 4
MAX_TX_RATE = 50000
NUM_ITERATIONS = 1
MSG_SIZES_BYTES = ["146000"]
ERROR_RATES = [0, .1, .2, .3, .4, .5, .6, .7, .8, .9]
MSG_INTERVAL = 9999
