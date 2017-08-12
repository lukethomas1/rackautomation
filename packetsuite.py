#!/usr/bin/python3

# File:
# Author: Luke Thomas
# Date: August 10, 2017

# System Imports
from os import path
from glob import glob
import logging

# Third Party Imports
from re import sub

# Local Imports
import config
import statsuite
from functions import choose_timestamp_path

# This suppresses warning messages produced by scapy on module load
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)
from scapy.all import *

# Constants
SAVE_FILE = config.PCAP_SAVE_FILE
PACKET_BEACON = 1
PACKET_GVINE = 2
PACKET_HANDSHAKE = 3
PACKET_BABEL = 4

##### TCPDUMP ANALYSIS #####

def get_dump_timestamp_dirs():
    return glob("./stats/dumps/" + SAVE_FILE + "/*")


def get_pcap_node_dict(dump_dir, num_nodes):
    cap_paths = glob(dump_dir + "/*")
    node_dict = make_empty_node_dict(num_nodes)
    for path in cap_paths:
        node_name = path.split("/")[-1].split(".")[0]
        node_dict[node_name] = read_pcap(path)
    return node_dict


# return dictionary of sent/received packets and beacon/gvine/handshake/babel below it
def read_pcap(path):
    node_name = path.split("/")[-1].split(".")[0]

    # Initialize dictionary
    node_dict = {}
    node_dict["sent"] = {}
    node_dict["received"] = {}
    for direction in node_dict.keys():
        node_dict[direction]["beacon"] = []
        node_dict[direction]["gvine"] = []
        node_dict[direction]["handshake"] = []
        node_dict[direction]["babel"] = []

    # Fill dictionary
    packets = rdpcap(path)
    for packet in packets:
        try:
            type = packet.load[3]
        except:
            print("ERROR: PACKET WITHOUT A PAYLOAD")
            continue
        direction = "received"
        if(packet[IP].src.split(".")[-1] == str(statsuite.get_trailing_number(node_name))):
            direction = "sent"
        if(type == PACKET_BEACON):
            node_dict[direction]["beacon"].append(packet)
        elif(type == PACKET_GVINE):
            node_dict[direction]["gvine"].append(packet)
        elif(type == PACKET_HANDSHAKE):
            node_dict[direction]["handshake"].append(packet)
        elif(type == PACKET_BABEL):
            node_dict[direction]["babel"].append(packet)
        else:
            # print("PACKET WITH UNKNOWN TYPE")
            continue
    return node_dict


def get_packet_counts(node_dict):
    num_packets_dict = {}
    num_packets_dict["beacon"] = 0
    num_packets_dict["gvine"] = 0
    num_packets_dict["handshake"] = 0
    num_packets_dict["babel"] = 0
    num_packets_dict["sent"] = 0
    num_packets_dict["received"] = 0
    for direction in ("sent", "received"):
        for type in node_dict[direction].keys():
            num_packets_dict[direction] += len(node_dict[direction][type])
            if(type == "beacon"):
                num_packets_dict["beacon"] += len(node_dict[direction][type])
            elif(type == "gvine"):
                num_packets_dict["gvine"] += len(node_dict[direction][type])
            elif(type == "handshake"):
                num_packets_dict["handshake"] += len(node_dict[direction][type])
            elif(type == "babel"):
                num_packets_dict["babel"] += len(node_dict[direction][type])
    return num_packets_dict


def print_packet_counts(num_packets_dict):
    print("Beacon: " + str(num_packets_dict["beacon"]))
    print("Gvine: " + str(num_packets_dict["gvine"]))
    print("Handshake: " + str(num_packets_dict["handshake"]))
    print("Babel: " + str(num_packets_dict["babel"]))
    print("Number of non-error sent packets: " + str(num_packets_dict["sent"]))
    print("Number of non-error received packets: " + str(num_packets_dict["received"]))
    print("Total: " + str(num_packets_dict["sent"] + num_packets_dict["received"]))


def useful_functions(pkt):
    print(dir(pkt))
    print()
    print(bytes(pkt))
    print()
    hexdump(pkt)
    print()
    pkt.display()
    print()
    print("Time: " + str(pkt.time))

##### SQLITE ANALYSIS #####

def make_empty_node_dict(num_nodes):
    node_dict = {}
    for index in range(num_nodes):
        name = "node" + str(index + 1)
        node_dict[name] = {}
        for direction in ("sent", "received"):
            node_dict[name][direction] = {}
            for type in ("beacon", "gvine", "handshake", "babel"):
                node_dict[name][direction][type] = []
    return node_dict

def get_sql_node_dict(path_to_input, num_nodes):
    SENT_TYPE_INDEX = 3
    RECEIVED_TYPE_INDEX = 4
    sent_dict = statsuite.get_packet_type_data(path_to_input, "loggableeventpacketsent",
                                            SENT_TYPE_INDEX)
    received_dict = statsuite.get_packet_type_data(path_to_input, "loggableeventpacketreceived",
                                                   RECEIVED_TYPE_INDEX)

    node_dict = make_empty_node_dict(num_nodes)
    for type in received_dict.keys():
        for row in received_dict[type]:
            node_dict[row[0]]["received"][type].append(row)
    for type in sent_dict.keys():
        for row in sent_dict[type]:
            node_dict[row[0]]["sent"][type].append(row)
    return node_dict


def get_sql_timestamp_dbs():
    return glob("./stats/events/" + SAVE_FILE + "/*.db")

def compare_all_sql_tcpdump(num_nodes):
    sql_dbs = get_sql_timestamp_dbs()
    dump_dirs = get_dump_timestamp_dirs()
    num_dirs = min(len(sql_dbs), len(dump_dirs))
    for dir_index in range(num_dirs):
        sql_path = choose_timestamp_path(sql_dbs, dir_index)
        dump_path = choose_timestamp_path(dump_dirs, dir_index)
        print()
        print("Sql path: " + sql_path)
        print("Dump path: " + dump_path)
        compare_sql_tcpdump(sql_path, dump_path, num_nodes)


def compare_sql_tcpdump(sql_path, dump_path, num_nodes):
    sql_dict = get_sql_node_dict(sql_path, num_nodes)
    dump_dict = get_pcap_node_dict(dump_path, num_nodes)
    for index in range(num_nodes):
        node_name = "node" + str(index + 1)
        sql_counts = get_packet_counts(sql_dict[node_name])
        dump_counts = get_packet_counts(dump_dict[node_name])
        print()
        print("Node: " + node_name)
        compare_num_packets_dicts(sql_counts, dump_counts)

def compare_num_packets_dicts(sql_dict, dump_dict):
    for category in sql_dict.keys():
        num_sql = sql_dict[category]
        num_dump = dump_dict[category]
        if(num_sql == num_dump):
            print(category + " MATCHES with " + str(num_sql) + " each")
        else:
            print(category + " DOESNT MATCH, sql: " + str(num_sql) + " dump: "
                  + str(num_dump))

if __name__ == "__main__":
    print("main")