# Used for rackspace node naming and some other naming, will break things if changed
NODE_PREFIX = "node-"

SAVE_FILE = "8flat"
JUPYTER_SAVE_FILE = "8flat"
PCAP_SAVE_FILE = "8flat"

IMAGE_NAME = "v411"

RACK_KEY = "mykey"

JAR_FILE = "gvine-fast.jar"

# Where to find the ip file for all the rackspace nodes
IP_FILE = "./iplists/" + NODE_PREFIX + "hosts"

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
