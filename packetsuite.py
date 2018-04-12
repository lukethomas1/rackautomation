#!/usr/bin/python3

# File:
# Author: Luke Thomas
# Date: August 10, 2017

# System Imports
from os import path
import logging
from glob import glob
from sqlite3 import connect, IntegrityError, DatabaseError
from time import sleep

# Third Party Imports
from re import sub
import pickle

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
REFACTOR_PACKET_TYPES = constants.REFACTOR_PACKET_TYPES
derpderpderp = False

##### TCPDUMP ANALYSIS #####

def get_dump_timestamp_dirs():
    return glob("./stats/dumps/" + SAVE_FILE + "/*")


def get_pcap_node_dict(dump_dir, num_nodes):
    cap_paths = glob(dump_dir + "/*.cap") + glob(dump_dir + "/*.pcap")
    node_dict = make_empty_node_dict(num_nodes)
    for path in cap_paths:
        node_name = path.split("/")[-1].split(".")[0]
        node_dict[node_name] = read_pcap(path)
    return node_dict


def read_pcap(pcap_path):
    """Read GrapeVine pcap file and parse packets by direction and packet type

    :param pcap_path: Path to the pcap file to be parsed
    :return: node_dict[direction][packet_type] = packets
    """
    ipmap = statsuite.read_ipmap(chosen_dir + "/ipmap")
    node_name = pcap_path.split("/")[-1].split(".")[0]
    node_dict = {}
    node_dict["tx"] = {}
    node_dict["rx"] = {}
    for direction in node_dict.keys():
        for packet_type in PACKET_TYPES:
            node_dict[direction][packet_type] = []
    # Fill dictionary
    packets = rdpcap(pcap_path)
    for packet in packets:
        try:
            type = get_gvine_packet_type(packet)
        except:
            print("ERROR: PACKET WITHOUT A PAYLOAD")
            continue
        direction = "rx"
        if is_packet_sender(packet, statsuite.get_trailing_number(node_name), ipmap):
            direction = "tx"
        node_dict[direction][type].append(packet)
    return node_dict


def make_packets_database(dump_dir):
    db_path = dump_dir + "/packets.db"
    if path.exists(db_path):
        #print(db_path + " already exists, returning")
        return
    connection = connect(db_path)

    table_cmd = "CREATE TABLE IF NOT EXISTS packets (senderid TEXT, receiverid TEXT, " \
                   "packettype INTEGER NOT NULL, bytesize INTEGER NOT NULL, timestamp INTEGER NOT NULL);"
    connection.execute(table_cmd)
    insert_template = "INSERT INTO packets (senderid, receiverid, packettype, bytesize, " \
                      "timestamp) VALUES ("

    ipmap = statsuite.read_ipmap(dump_dir + "/ipmap")
    for pcap_path in glob(dump_dir + "/*.cap") + glob(dump_dir + "/*.pcap"):
        node_name = pcap_path.split("/")[-1].split(".")[0].split("_")[0]
        print("working on " + node_name)
        node_number = statsuite.get_trailing_number(node_name)
        packets = rdpcap(pcap_path)
        for packet in packets:
            is_sender = is_packet_sender(packet, node_number, ipmap)
            senderid = "'" + node_name + "'" if is_sender else "NULL"
            # TODO the lines below were duplicating sent packets
            # if senderid == "NULL":
            #     sender_ip = packet.getlayer(IP).src
            #     senderid = "'" + get_sender_name(sender_ip, ipmap) + "'"
            receiverid = "'" + node_name + "'" if not is_sender else "NULL"
            if packet.haslayer(DHCP):
                continue
            try:
                packettype = packet.load[3]
            except AttributeError as err:
                print(str(err))
                print(str(packet.display()))
                continue

            if packettype < 0 or packettype > len(PACKET_TYPES) + 5:
                continue  # not a correct packet
            bytesize = len(packet)
            timestamp = int(packet.time)
            insert_values = senderid + ", " + receiverid + ", " + str(packettype) +\
                            ", " + str(bytesize) + ", " + str(timestamp)
            insert_stmt = insert_template + insert_values + ");"
            try:
                connection.execute(insert_stmt)
            except IntegrityError as error:
                print(str(error))
                pass
    connection.commit()
    connection.close()


def get_sender_name(ip_address, ipmap):
    return config.NODE_PREFIX + str(ipmap[ip_address])


def read_pcap_bytes(pcap_path):
    node_name = pcap_path.split("/")[-1].split(".")[0]
    node_dict = {}
    node_dict["tx"] = {}
    node_dict["rx"] = {}
    for direction in node_dict.keys():
        for packet_type in PACKET_TYPES:
            node_dict[direction][packet_type] = 0
    # Fill dictionary
    packets = rdpcap(pcap_path)
    for packet in packets:
        try:
            type = get_gvine_packet_type(packet)
        except:
            print("ERROR: PACKET WITHOUT A PAYLOAD")
            continue
        direction = "rx"
        if(packet[IP].src.split(".")[-1] == str(statsuite.get_trailing_number(node_name))):
            direction = "tx"
        node_dict[direction][type].append(packet)


def get_pcap_packets(path):
    return rdpcap(path)


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


def test_packet_functions(pkt):
    print(str(pkt.haslayer(UDP)))
    print(str(pkt.haslayer(DNS)))

def test_list_of_packets(packet_list):
    for pkt in packet_list:
        if pkt.haslayer(DNS):
            print("DNS")
        if pkt.haslayer(NTP):
            print("NTP")
        # if pkt.haslayer(UDP):
        #     print("UDP")

##### SQLITE ANALYSIS #####

def make_empty_node_dict(num_nodes):
    node_dict = {}
    for index in range(num_nodes):
        name = "node" + str(index + 1)
        node_dict[name] = {}
        for direction in ("tx", "rx"):
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


def make_basic_packets_dict(chosen_dir=""):
    if not chosen_dir:
        dump_dirs = get_dump_timestamp_dirs()
        chosen_dir = choose_timestamp_path(dump_dirs)
    pcap_files = glob(chosen_dir + "/*.pcap")
    ipmap = statsuite.read_ipmap(chosen_dir + "/ipmap")
    packets_dict = {}

    for pcap_path in pcap_files:
        node_name = pcap_path.split("/")[-1].split("_")[0]
        if "." in node_name:
            node_name = node_name.split(".")[0]
        if node_name not in packets_dict.keys():
            packets_dict[node_name] = rdpcap(pcap_path)
        else:
            packets_dict[node_name] += rdpcap(pcap_path)
    earliest_time, latest_time = get_earliest_latest_packet(packets_dict)
    seconds_dict = {}
    for node_name in packets_dict.keys():
        seconds_dict[node_name] = {}
        seconds_dict[node_name]["tx"] = {}
        seconds_dict[node_name]["rx"] = {}
        for second in range(latest_time - earliest_time + 1):
            seconds_dict[node_name]["tx"][str(int(second))] = 0
            seconds_dict[node_name]["rx"][str(int(second))] = 0
        for packet in packets_dict[node_name]:
            second = int(packet.time - earliest_time)
            if(second < latest_time - earliest_time):
                is_sender = is_packet_sender(packet, statsuite.get_trailing_number(node_name), ipmap)
                if is_sender == "NOTVALID":
                    continue
                # elif not packet.haslayer(UDP):
                #     print("passing non-UDP packet")
                #     continue
                direction = "tx" if is_sender else "rx"
                seconds_dict[node_name][direction][str(second)] += len(packet)
    return seconds_dict


def make_basic_combined_dict(seconds_dict):
    """

    :param seconds_dict: seconds_dict[node_name][direction][second] = bytes_sent_that_second
    """
    combined_dict = {
        "tx": {},
        "rx": {}
    }
    for node_name in seconds_dict.keys():
        for direction in seconds_dict[node_name].keys():
            for second in seconds_dict[node_name][direction].keys():
                if second not in combined_dict[direction].keys():
                    combined_dict[direction][second] = 0
                combined_dict[direction][second] += seconds_dict[node_name][direction][second]
    return combined_dict


def make_type_packets_dict(chosen_dir=None):
    if(chosen_dir is None):
        dump_dirs = get_dump_timestamp_dirs()
        chosen_dir = choose_timestamp_path(dump_dirs)
    pcap_files = glob(chosen_dir + "/*.pcap")
    ipmap = statsuite.read_ipmap(chosen_dir + "/ipmap")
    packets_dict = {}

    for pcap_path in pcap_files:
        node_name = pcap_path.split("/")[-1].split("_")[0]
        if node_name not in packets_dict.keys():
            packets_dict[node_name] = rdpcap(pcap_path)
        else:
            packets_dict[node_name] += rdpcap(pcap_path)
    earliest_time, latest_time = get_earliest_latest_packet(packets_dict)
    seconds_dict = make_bucket_template(packets_dict.keys(), earliest_time, latest_time)
    for node_name in packets_dict.keys():
        for packet in packets_dict[node_name]:
            is_sender = is_packet_sender(packet, statsuite.get_trailing_number(node_name), ipmap)
            if is_sender == "NOTVALID":
                continue
            elif not packet.haslayer(UDP):
                print("passing non-UDP packet")
                continue
            direction = "tx" if is_sender else "rx"
            try:
                packet_type = get_gvine_packet_type(packet)
            except IndexError:
                continue
            except AttributeError:
                print("pass on bad packet")
                continue
            second = int(packet.time - earliest_time)
            seconds_dict[direction][packet_type][node_name][str(second)] += len(packet)
    return seconds_dict


def make_single_dict(node_name, db_path, refactor=False):
    conn = connect(db_path)
    query = "SELECT * from packets where senderid='" + node_name + \
            "' or receiverid='" + node_name + "';"
    cursor = conn.execute(query)
    table_data = cursor.fetchall()
    earliest_time = conn.execute("select min(timestamp) from packets;").fetchall()[0][0]
    latest_time = conn.execute("select max(timestamp) from packets;").fetchall()[0][0]

    seconds_dict = make_bucket_template([node_name], earliest_time, latest_time, refactor)
    for row in table_data:
        senderid = row[0]
        receiverid = row[1]
        if not refactor:
            packet_type = PACKET_TYPES[row[2] - 1]
        else:
            packet_type = REFACTOR_PACKET_TYPES[row[2]]
        bytesize = row[3]
        timestamp = row[4]

        direction = "tx" if senderid == node_name else "rx"
        second = int(timestamp - earliest_time)
        seconds_dict[direction][packet_type][node_name][str(second)] += bytesize
    return seconds_dict


def count_total_tx(db_path):
    conn = connect(db_path)
    query = "SELECT * from packets where senderid is not null;"
    cursor = conn.execute(query)
    table_data = cursor.fetchall()

    sum = 0
    for row in table_data:
        bytesize = row[3]
        sum += bytesize
    return sum


def make_bucket_template(node_names, earliest_time, latest_time, refactor=False):
    if refactor:
        type_list = REFACTOR_PACKET_TYPES
    else:
        type_list = PACKET_TYPES
    bucket_template = {}
    for direction in ("tx", "rx"):
        bucket_template[direction] = {}
        for packet_type in type_list:
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
    

def is_packet_sender(packet, node_number, ipmap):
    if ipmap is None:
        if(str(packet[IP].src.split(".")[-1]) == str(node_number)):
            return True
    elif packet.haslayer(IP):
        if str(packet[IP].src) in ipmap.keys():
            if(str(ipmap[str(packet[IP].src)]) == str(node_number)):
                return True
        else:
            return "NOTVALID"
    else:
        print("No IP layer")
        return "NOTVALID"
    return False
