# Used for rackspace node naming and some other naming, will break things if changed
NODE_PREFIX = "node"

SAVE_FILE = "threenodes"
JUPYTER_SAVE_FILE = "threenodes"
PCAP_SAVE_FILE = "threenodes"

IMAGE_NAME = "laptop"

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
MSG_SIZES_BYTES = ["100000", "300000", "500000", "700000", "900000"]
ERROR_RATES = [1]
MSG_INTERVAL = 9999
