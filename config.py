# Used for rackspace node naming and some other naming, will break things if changed
NODE_PREFIX = "node-"

SAVE_FILE = "pi-net"

IMAGE_NAME = "MessageId"

JAR_FILE = "gvine-java.jar"

# Where to find the ip file for all the rackspace nodes
IP_FILE = "./iplists/" + NODE_PREFIX + "hosts"

# Subnet Ip Blacklist
IP_BLACK_LIST = [
    "10.0.3",
    "23.253.107",
    "192.168.3",
    "127.0.0"
]
