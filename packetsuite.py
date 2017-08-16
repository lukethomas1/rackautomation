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
import graphsuite
import constants
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
PACKET_TYPES = constants.PACKET_TYPES

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


def read_pcap(path):
    """Read GrapeVine pcap file and parse packets by direction and packet type

    :param path: Path to the pcap file to be parsed
    :return: node_dict[direction][packet_type] = packets
    """
    node_name = path.split("/")[-1].split(".")[0]
    node_dict = {}
    node_dict["sent"] = {}
    node_dict["received"] = {}
    for direction in node_dict.keys():
        for packet_type in PACKET_TYPES:
            node_dict[packet_type] = []
    # Fill dictionary
    packets = rdpcap(path)
    for packet in packets:
        try:
            type = get_gvine_packet_type(packet)
        except:
            print("ERROR: PACKET WITHOUT A PAYLOAD")
            continue
        direction = "received"
        if(packet[IP].src.split(".")[-1] == str(statsuite.get_trailing_number(node_name))):
            direction = "sent"
        node_dict[direction][type].append(packet)
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
            packet = node_dict[direction][type]
            packet_type = get_gvine_packet_type(packet)
            num_packets_dict[direction] += len(packet)
            num_packets_dict[packet_type] += len(packet)
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


def make_basic_packets_dict():
    dump_dirs = get_dump_timestamp_dirs()
    chosen_dir = choose_timestamp_path(dump_dirs)
    pcap_files = glob(chosen_dir + "/*")
    packets_dict = {}
    for pcap_path in pcap_files:
        node_name = pcap_path.split("/")[-1].split(".")[0]
        packets_dict[node_name] = rdpcap(pcap_path)
    earliest_time, latest_time = get_earliest_latest_packet(packets_dict)
    seconds_dict = {}
    for node_name in packets_dict.keys():
        seconds_dict[node_name] = {}
        seconds_dict[node_name]["sent"] = {}
        seconds_dict[node_name]["received"] = {}
        for second in range(latest_time - earliest_time + 1):
            seconds_dict[node_name]["sent"][str(int(second))] = 0
            seconds_dict[node_name]["received"][str(int(second))] = 0
        for packet in packets_dict[node_name]:
            second = int(packet.time - earliest_time)
            if(is_packet_sender(packet, statsuite.get_trailing_number(node_name))):
                seconds_dict[node_name]["sent"][str(second)] += len(packet)
            else:
                seconds_dict[node_name]["received"][str(second)] += len(packet)
    return seconds_dict


def make_type_packets_dict():
    dump_dirs = get_dump_timestamp_dirs()
    chosen_dir = choose_timestamp_path(dump_dirs)
    pcap_files = glob(chosen_dir + "/*")
    packets_dict = {}
    for pcap_path in pcap_files:
        node_name = pcap_path.split("/")[-1].split(".")[0]
        packets_dict[node_name] = rdpcap(pcap_path)
    earliest_time, latest_time = get_earliest_latest_packet(packets_dict)
    seconds_dict = make_bucket_template(packets_dict.keys(), earliest_time, latest_time)
    for node_name in packets_dict.keys():
        for packet in packets_dict[node_name]:
            is_sender = is_packet_sender(packet, statsuite.get_trailing_number(node_name))
            direction = "sent" if is_sender else "received"
            try:
                packet_type = get_gvine_packet_type(packet)
            except IndexError:
                continue
            second = int(packet.time - earliest_time)
            seconds_dict[direction][packet_type][node_name][str(second)] += len(packet)
    return seconds_dict


def make_bucket_template(node_names, earliest_time, latest_time):
    bucket_template = {}
    for direction in ("sent", "received"):
        bucket_template[direction] = {}
        for packet_type in PACKET_TYPES:
            bucket_template[direction][packet_type] = {}
            for node_name in node_names:
                bucket_template[direction][packet_type][node_name] = {}
                for second in range(latest_time - earliest_time + 1):
                    bucket_template[direction][packet_type][node_name][str(second)] = 0
    return bucket_template


def get_earliest_latest_packet(packets_dict):
    """Return the earliest and latest timestamp (in seconds since 1970) of the lists in packets_dict

    :param packets_dict: packets_dict[node] = pcap_packets_list
    :return: earliest_time, latest_time
    """
    earliest_time = 99999999999999
    latest_time = -1
    earliest_latest = {key: (value[0].time, value[-1].time) for key, value in packets_dict.items()}
    for node in earliest_latest.keys():
        early_late_tuple = earliest_latest[node]
        earliest_time = min(earliest_time, int(early_late_tuple[0]))
        latest_time = max(latest_time, int(early_late_tuple[1]))
    return earliest_time, latest_time


def get_gvine_packet_type(packet):
    return PACKET_TYPES[packet.load[3] - 1]


def is_packet_sender(packet, node_index):
    if(str(packet[IP].src.split(".")[-1]) == str(node_index)):
        return True
    return False


if __name__ == "__main__":
    print("main")