#!/usr/bin/python3

# File: 
# Author: Luke Thomas
# Date: August 10, 2017

# System Imports
from os import path
from glob import glob

# Third Party Imports
from scapy.all import *

# Local Imports
import config
from statsuite import get_trailing_number

# Constants
SAVE_FILE = config.PCAP_SAVE_FILE
PACKET_BEACON = 1
PACKET_GVINE = 2
PACKET_HANDSHAKE = 3
PACKET_BABEL = 4

cap_paths = []
for run_path in glob("./stats/dumps/" + SAVE_FILE + "/*"):
    for node_path in glob(run_path + "/*"):
        cap_paths += glob(node_path + "/*")

# print(str(packets))
# for pkt in packets:
#     pkt_str = bytes(pkt)

packets = rdpcap(cap_paths[0])
pkt = packets[25]
print(dir(pkt))
# print()
# print(bytes(pkt))
# print()
# hexdump(pkt)
# print()
pkt.display()
# print(pkt.load[3])

node_dict = {}

for path in cap_paths:
    node_name = path.split("/")[-2]
    node_dict[node_name] = {}
    node_dict[node_name]["sent"] = {}
    node_dict[node_name]["received"] = {}
    for direction in node_dict[node_name].keys():
        node_dict[node_name][direction]["beacon"] = []
        node_dict[node_name][direction]["gvine"] = []
        node_dict[node_name][direction]["handshake"] = []
        node_dict[node_name][direction]["babel"] = []

for path in cap_paths:
    node_name = path.split("/")[-2]
    packets = rdpcap(path)
    for packet in packets:
        try:
            type = packet.load[3]
        except:
            continue
        direction = "received"
        if(packet[IP].src.split(".")[-1] == str(get_trailing_number(node_name))):
            direction = "sent"
        if(type == PACKET_BEACON):
            node_dict[node_name][direction]["beacon"].append(packet)
        elif(type == PACKET_GVINE):
            node_dict[node_name][direction]["gvine"].append(packet)
        elif(type == PACKET_HANDSHAKE):
            node_dict[node_name][direction]["handshake"].append(packet)
        elif(type == PACKET_BABEL):
            node_dict[node_name][direction]["babel"].append(packet)

for node_name in node_dict.keys():
    num_beacon = 0
    num_gvine = 0
    num_handshake = 0
    num_babel = 0
    num_sent = 0
    num_received = 0
    for type in node_dict[node_name]["sent"].keys():
        direction = "sent"
        num_sent += len(node_dict[node_name][direction][type])
        if(type == "beacon"):
            num_beacon += len(node_dict[node_name][direction][type])
        elif(type == "gvine"):
            num_gvine += len(node_dict[node_name][direction][type])
        elif(type == "handshake"):
            num_handshake += len(node_dict[node_name][direction][type])
        elif(type == "babel"):
            num_babel += len(node_dict[node_name][direction][type])
    for type in node_dict[node_name]["received"].keys():
        direction = "received"
        num_received += len(node_dict[node_name][direction][type])
        if(type == "beacon"):
            num_beacon += len(node_dict[node_name][direction][type])
        elif(type == "gvine"):
            num_gvine += len(node_dict[node_name][direction][type])
        elif(type == "handshake"):
            num_handshake += len(node_dict[node_name][direction][type])
        elif(type == "babel"):
            num_babel += len(node_dict[node_name][direction][type])
    num_packets = num_sent + num_received
    print()
    print("Node: " + node_name)
    print("Beacon: " + str(num_beacon))
    print("Gvine: " + str(num_gvine))
    print("Handshake: " + str(num_handshake))
    print("Babel: " + str(num_babel))
    print("Number of non-error sent packets: " + str(num_sent))
    print("Number of non-error received packets: " + str(num_received))
    print("Total: " + str(num_packets))
