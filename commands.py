#!/usr/bin/env python3

# File: commands.py
# Author: Luke Thomas
# Date: March 30, 2017
# Description: This file contains functions (commands) to be called by
# racksuite.py. These commands are composed of sequential calls to functions
# in functions.py. Each of these commands accomplishes a "task" from start to
# finish that a user would desire, such as initializing rackspace nodes, or
# configuring a topology.

# System Imports
from time import sleep
from os import path
from collections import OrderedDict

# Third Party Imports
from glob import glob
from re import sub
from plotly.offline import init_notebook_mode
import plotly

# Local Imports
import functions
import testsuite
import statsuite
import autotest
import packetsuite
import graphsuite
import config

# Constants defined in config.py
NODE_PREFIX = config.NODE_PREFIX
SAVE_FILE = config.SAVE_FILE
JUPYTER_SAVE_FILE = config.JUPYTER_SAVE_FILE
IMAGE_NAME = config.IMAGE_NAME
IP_FILE = config.IP_FILE
IP_BLACK_LIST = config.IP_BLACK_LIST
JAR_FILE = config.JAR_FILE
RACK_KEY = config.RACK_KEY

NUM_INDICES = config.NUM_INDICES
MAX_TX_RATE = config.MAX_TX_RATE
NUM_ITERATIONS = config.NUM_ITERATIONS
MSG_SIZES_BYTES = config.MSG_SIZES_BYTES
ERROR_RATES = config.ERROR_RATES
MSG_INTERVAL = config.MSG_INTERVAL

# Functions are ordered in usage order


def update_config():
    # There is no saved data, possibly first time user
    if(not path.isfile(".data.pickle")):
        print("No .data.pickle file detected, creating...")
        functions.set_topology(SAVE_FILE, NODE_PREFIX)
        return functions.load_data()

    data = functions.load_data()
    if(functions.check_config(data['config'])
        or functions.check_timestamp(data['timestamp'])
        or len(data['iplist']) == 0
        or functions.check_rack_nodes(data['racknodes'])):
        print("Updating configuration...")
        functions.set_topology(SAVE_FILE, NODE_PREFIX)
        return functions.load_data()
    return data


def reset_topology():
    functions.set_topology(SAVE_FILE, NODE_PREFIX)
    print("Topology reset, config updated")


# Creates # of nodes necessary for desired topology on rackspace
def initialize(save_file, num_nodes):
    functions.create_rackspace_instances(num_nodes, IMAGE_NAME, RACK_KEY, save_file, NODE_PREFIX)
    print("Done.")


def make_iplist(num_nodes, iplist):
    functions.generate_iplist(num_nodes, NODE_PREFIX)
    functions.edit_ssh_config()
    functions.add_known_hosts(iplist)


# Creates the configuration files for the desired topology on THIS COMPUTER
# Creates platform xmls, emane_start.sh, emane_stop.sh, scenario.eel
# The files are created in ./topologies/<topology-name>/
def configure(save_file, subnets, nodes):
    topo_path = "./topologies/" + save_file + "/"
    # Generate and copy files to the local topology folder
    print("Configuring files")
    functions.create_dir(topo_path)
    functions.write_platform_xmls(subnets, nodes, topo_path, IP_BLACK_LIST)
    functions.write_emane_start_stop_scripts(save_file, len(nodes))
    functions.write_scenario(subnets, nodes, topo_path)


# Runs configure() to create topology locally, 
# then distributes topology to rackspace nodes
def setup(save_file, subnets, nodes, iplist):
    # Write configuration files (configure() method) before sending to nodes
    if(not path.isdir("./topologies/" + save_file)):
        configure(save_file, subnets, nodes)
    else:
        print(save_file + " already configured")

    print("Editing ssh config")
    functions.edit_ssh_config()
    sleep(2)

    # Add all rackspace node ip addresses to this computer's known_hosts file
    functions.add_known_hosts(iplist)

    # Create topology directory on each rackspace node
    print("Creating remote directories with ipfile: " + IP_FILE)
    functions.remote_create_dirs(save_file, IP_FILE)
    sleep(2)

    # Copy the default config to each rackspace node
    print("Copying default config")
    functions.remote_copy_default_config(save_file, IP_FILE)
    sleep(2)

    if(len(iplist) == 0):
        print("IPLIST IS EMPTY")

    # Copy the scenario.eel file to each rackspace node
    print("Copying scenario.eel")
    functions.remote_copy_scenario(save_file, iplist)

    # Copy corresponding platform file to each rackspace node
    print("Copying platform xmls")
    functions.remote_copy_platform_xmls(save_file, iplist)

    # Copy emane_start and emane_stop scripts to each rackspace node
    print("Copying emane scripts")
    functions.remote_copy_emane_scripts(save_file, iplist)

    # Move grapevine files from svn folder to test folder on each rack instance
    print("Preparing GrapeVine test")
    functions.setup_grapevine(save_file, IP_FILE)

    # Do node certifications
    gvpki(iplist)
    print("Done.")


def change_tx_rate():
    tx_rate = input("New TargetTxRateBps? : ")
    path_to_conf = "./autotestfiles/gvine.conf.json"
    functions.change_gvine_tx_rate(tx_rate, path_to_conf)


def change_frag_size():
    frag_size = input("New FragmentSize? : ")
    path_to_conf = "./autotestfiles/gvine.conf.json"
    functions.change_gvine_frag_size(frag_size, path_to_conf)


def push_config():
    path_to_conf = "./autotestfiles/gvine.conf.json"
    functions.push_gvine_conf(IP_FILE, path_to_conf)


def push_file():
    src_path = input("Input source file path: ")
    dest_path = input("Input destination file path (1: default gvine 2: default emane): ")
    file_name = input("Input file name (blank for unchanged): ")
    if(dest_path == "1"):
        dest_path = "/home/emane-01/test/emane/gvine/node/" + file_name
    elif(dest_path == "2"):
        dest_path = "/home/emane-01/GrapeVine/topologies/" + SAVE_FILE + "/" + file_name
    else:
        dest_path = path.expanduser(dest_path)
    src_path = path.expanduser(src_path)
    functions.push_file(IP_FILE, src_path, dest_path)


def gvpki(iplist):
    # Generate cert on each node
    print("Generating certs")
    path_to_jar = "/home/emane-01/test/emane/gvine/node/"
    functions.generate_certs(iplist, path_to_jar)
    sleep(3)
    # Pull cert down from each node
    print("Pulling certs")
    functions.pull_certs(iplist)
    sleep(2)
    # Push all certs to each node
    print("Pushing certs")
    path_to_certs = "./keystore/*"
    functions.push_certs(IP_FILE, path_to_certs, path_to_jar)
    sleep(2)
    # Load all certs on each node
    print("Loading certs")
    functions.load_certs(path_to_jar, iplist)


def set_error_rate(subnets, nodes, iplist):
    error_rate = input("Error rate to set? : ")
    error_rate = float(error_rate)
    error_commands = functions.generate_error_rate_commands(subnets, nodes)
    for node_index in range(len(iplist)):
        ip = iplist[node_index]
        templates = error_commands[node_index + 1]
        for template in templates:
            functions.remote_set_error_rate(ip, error_rate, template)


def remove_error_rate(subnets, nodes, iplist):
    error_rate = input("Error rate to remove? : ")
    error_rate = float(error_rate)
    error_commands = functions.generate_error_rate_commands(subnets, nodes)
    for node_index in range(len(iplist)):
        ip = iplist[node_index]
        templates = error_commands[node_index + 1]
        for template in templates:
            functions.remote_remove_error_rate(ip, error_rate, template)


# Synchronizes rackspace nodes (not sure what it does, soroush had it),
# then runs emane_start.sh on each rackspace node in the topology
def start(save_file, iplist):
    functions.synchronize(IP_FILE)

    print("Starting emane")
    script_name = 'emane_start.sh'
    functions.remote_emane(save_file, IP_FILE, script_name)
    sleep(2)

    print("Deleting previous gvine log files")
    functions.delete_gvine_log_files(IP_FILE)
    sleep(2)

    print("Starting GrapeVine jar: " + JAR_FILE)
    functions.remote_start_gvine(iplist, JAR_FILE)
    print("Done.")


def start_debug(save_file, iplist, nodes, subnets, nodeipdict):
    functions.synchronize(IP_FILE)

    print("Starting emane")
    script_name = 'emane_start.sh'
    functions.remote_emane(save_file, IP_FILE, script_name)
    sleep(2)

    print("Logging subnet traffic with tcpdump")
    functions.subnet_tcpdump(nodes, subnets, NODE_PREFIX, nodeipdict)

    print("Deleting previous gvine log files")
    functions.delete_gvine_log_files(IP_FILE)
    sleep(2)

    print("Starting GrapeVine jar: " + JAR_FILE)
    functions.remote_start_gvine(iplist, JAR_FILE)
    print("Done.")


def start_console(iplist):
    user = "emane-01"
    terminal = ['gnome-terminal']
    jar = "jvine.jar"
    gvine_dir = "~/test/emane/gvine/node"
    functions.remote_start_console(user, terminal, jar, iplist, gvine_dir)


def start_emane(save_file):
    print("Starting emane")
    script_name = 'emane_start.sh'
    functions.remote_emane(save_file, IP_FILE, script_name)


def start_gvine(iplist):
    jar_name = input("Name of jar file(leave blank for default): ")
    if(not jar_name):
        jar_name = JAR_FILE
    functions.remote_start_gvine(iplist, jar_name)


def start_norm(iplist, subnets, nodes):
    send_bps = 50000
    receive_bps = 100000
    functions.start_norm(iplist, subnets, nodes, send_bps, receive_bps)


# Runs emane_stop.sh on each rackspace node in the topology
def stop(save_file):
    # Stop GrapeVine
    functions.parallel_ssh(IP_FILE, "sudo pkill java")
    # Stop Norm
    functions.parallel_ssh(IP_FILE, "sudo pkill norm")
    # Stop tcpdump
    functions.parallel_ssh(IP_FILE, "sudo pkill tcpdump")
    # Stop EMANE
    script_file = 'emane_stop.sh'
    functions.remote_emane(save_file, IP_FILE, script_file)
    sleep(2)
    print("Done.")


def stop_gvine():
    print("Stopping gvine")
    functions.parallel_ssh(IP_FILE, "sudo pkill java")


def stop_norm():
    print("Stopping norm")
    functions.parallel_ssh(IP_FILE, "sudo pkill norm")


def start_basic_tcpdump(nodes, subnets, nodeipdict):
    print("Logging subnet traffic with tcpdump")
    functions.subnet_tcpdump(nodes, subnets, NODE_PREFIX, nodeipdict)


def stop_all_tcpdump():
    functions.parallel_ssh(IP_FILE, "sudo pkill tcpdump")


def ping(subnets, nodes):
    print("Setting up")
    functions.generate_network_ping_list(subnets, nodes, IP_FILE, IP_BLACK_LIST)
    testsuite.ping_network()
    print("Done.")


def run_auto_test():
    # Set the test parameters and variables
    num_indices = NUM_INDICES
    max_tx_rate = MAX_TX_RATE
    num_iterations = NUM_ITERATIONS
    msg_sizes_bytes = MSG_SIZES_BYTES
    error_rates = ERROR_RATES
    msg_interval = MSG_INTERVAL

    # Prepare the initial indices for the test
    print("Indices: [iteration, source_node, message_size, error_rate]")
    initial_indices = input("Input 4 initial indices (ex. [0,0,0,0])(blank for default): ")[1:-1]
    if(initial_indices):
        initial_indices = [int(x) for x in initial_indices.split(",")]
        try:
            if(len(initial_indices) != num_indices):
                print("Invalid number of indices: " + str(len(initial_indices)))
                exit()
        except:
            print("Invalid indices input, syntax incorrect")
            exit()
    else:
        initial_indices = [0, 0, 0, 0]

    # Initialize the test and start running test
    autotest.initialize_parameters(max_tx_rate, num_iterations, msg_sizes_bytes, error_rates,
                                   msg_interval, initial_indices)
    need_setup = bool(input("Need Setup? (Leave blank for no): "))
    need_configure = False
    if(need_setup):
        need_configure = bool(input("Need Topology Configuration? (Leave blank for no): "))
    autotest.run(need_setup, need_configure)


def transfer_delay(num_nodes):
    paths = glob("./stats/events/" + SAVE_FILE + "/*.db")
    paths.sort()
    paths.reverse()
    num = str(len(paths) - 1)
    functions.create_dir("./stats/measurements/")
    functions.create_dir("./stats/measurements/" + SAVE_FILE)
    path_to_output = "./stats/measurements/" + SAVE_FILE + "/transferdelay.db"

    user_input = input("Index of sqlite3 db? (0 newest, " + num + " oldest, X-X for range, "
                                                                  "blank for all): ")

    # Blank input, parse all indices
    if(not user_input):
        for ind in range(len(paths)):
            path_to_input = sub(r"[\\]", '', paths[ind])
            print("Extracting from " + path_to_input)
            statsuite.extract_transfer_delays(path_to_input, path_to_output, SAVE_FILE, num_nodes)
    # Input contains "-", parse indices in the range provided, inclusive
    elif("-" in user_input):
        indices = user_input.split("-")
        start = int(indices[0])
        end = int(indices[1])
        for ind in range(start, end + 1):
            path_to_input = sub(r"[\\]", '', paths[ind])
            print("Extracting from " + path_to_input)
            statsuite.extract_transfer_delays(path_to_input, path_to_output, SAVE_FILE, num_nodes)
    else:
        index = int(user_input)
        path_to_input = sub(r"[\\]", '', paths[index])
        statsuite.extract_transfer_delays(path_to_input, path_to_output, SAVE_FILE, num_nodes)
    print("Success")


def avg_hop_transfer_delay(iplist, ipdict, subnets, nodes):
    path_to_input = "./stats/measurements/" + SAVE_FILE + "/transferdelay.db"
    subnet_hops_dict = functions.get_hops_between_all_subnets(subnets)
    node_hops_dict = functions.get_hops_between_all_nodes(subnets, nodes, subnet_hops_dict)
    rack_to_topo_names = functions.generate_rack_to_topo_dict(iplist, functions.invert_dict(
        ipdict), nodes)
    avgs_dict = statsuite.calc_avg_hop_transfer_delay(path_to_input, node_hops_dict, nodes,
                                                      rack_to_topo_names)
    sortedMsgSizes = sorted(avgs_dict["delays"].keys(), key=int)
    for msgSize in sortedMsgSizes:
        print("Average Hop Delay for messageSize " + str(msgSize) + " bytes:" +
              "{:10.2f}".format(avgs_dict["delays"][msgSize]))
        print("Number of data points for messageSize " + str(msgSize) + " bytes:" + str(avgs_dict[
            "counts"][msgSize]))


def node_delay():
    paths = glob("./stats/events/" + SAVE_FILE + "/*.db")
    paths.sort()
    paths.reverse()
    num = str(len(paths) - 1)
    functions.create_dir("./stats/measurements/")
    functions.create_dir("./stats/measurements/" + SAVE_FILE)
    path_to_output = "./stats/measurements/" + SAVE_FILE + "/nodedelay.db"
    check_again = False
    try:
        index = int(input("Index of sqlite3 db? (0 for newest, " + num +
                          " for oldest, blank for all): "))
    except:
        print("Extracting all databases")
        check_again = True

    if(check_again):
        for ind in range(len(paths)):
            path_to_input = sub(r"[\\]", '', paths[ind])
            print("Extracting from " + path_to_input)
            statsuite.extract_node_delays(path_to_input, path_to_output, SAVE_FILE)
    else:
        path_to_input = sub(r"[\\]", '', paths[index])
        statsuite.extract_node_delays(path_to_input, path_to_output, SAVE_FILE)
    print("Success")


def norm_delay(iplist):
    message_name = input("Choose message file name: ")
    sender_node = int(input("Sender node: "))
    norm_delays = functions.get_norm_delays(message_name, iplist)
    sender_time = int(norm_delays[sender_node - 1])
    for index in range(len(norm_delays)):
        if index != sender_node - 1:
            print(NODE_PREFIX + str(index + 1) + ": " + str(int(norm_delays[index]) - sender_time))


def message(iplist):
    message_name = input("Choose message file name: ")
    file_size = input("Choose file size (kilobytes): ")
    send_num = input("Node number to send from? : ")
    testsuite.send_gvine_message(iplist[node_num - 1], message_name, file_size, send_num, "")


def message_gvine_unicast(iplist):
    message_name = input("Choose message file name: ")
    file_size = input("Choose file size (kilobytes): ")
    send_num = input("Node number to send from? : ")
    rec_num = input("Node number to receive on? : ")
    testsuite.send_gvine_message(iplist[int(send_num) - 1], message_name, file_size, send_num, rec_num)


def norm_message(iplist):
    message_name = input("Choose message file name: ")
    file_size = input("Choose file size (kilobytes): ")
    testsuite.send_norm_message(iplist[0], message_name, file_size)
    

def test_message(iplist, inv_ipdict, nodes):
    message_name = input("Choose message file name: ")
    file_size = input("Choose file size (kilobytes): ")
    testsuite.message_test_gvine(iplist, message_name, file_size)
    testsuite.wait_for_message_received(message_name, 1, iplist, inv_ipdict, nodes, 9999)


def stats_directories(save_file):
    print("Creating stats directories")
    functions.create_dir("./stats/")
    functions.create_dir("./stats/delays")
    functions.create_dir("./stats/dumps")
    functions.create_dir("./stats/emane")
    functions.create_dir("./stats/events")
    functions.create_dir("./stats/delays/" + save_file)
    functions.create_dir("./stats/dumps/" + save_file)
    functions.create_dir("./stats/emane/" + save_file)
    functions.create_dir("./stats/events/" + save_file)
    functions.create_dir("./stats/events/" + save_file + "/nodedata/")

def stats(save_file, num_nodes, iplist):
    stats_directories(save_file)

    #print("\nRetrieving delay files")
    #path_to_delay = "/home/emane-01/test/emane/gvine/node/delay.txt"
    #statsuite.retrieve_delayfiles(iplist, path_to_delay, "./stats/delays/" + save_file)

    print("\nGenerating EMANE statistics")
    statsuite.generate_emane_stats(NODE_PREFIX, save_file, num_nodes, iplist)
    print("\nCopying EMANE statistics to this computer")
    statsuite.copy_emane_stats(save_file, num_nodes, iplist)
    print("Done.")

    print("\nGenerating Event data")
    statsuite.generate_event_dbs(iplist)
    sleep(2)

    print("\nCopying Event data")
    path_to_db = "/home/emane-01/test/emane/gvine/node/dbs/eventsql_copy.db"
    statsuite.copy_event_dbs(iplist, path_to_db, "./stats/events/" + save_file + "/nodedata/")

    print("\nCombining Event data")
    input_dir = "./stats/events/" + save_file + "/nodedata/"
    output_dir = "./stats/events/" + save_file + "/"
    path_to_sql_db = statsuite.combine_event_dbs(input_dir, output_dir)

    print("\nPlotting message delays at plot.ly/~sunjaun2/")
    rows = statsuite.get_sql_data(path_to_sql_db, "loggableeventmessagereceived")
    dict = statsuite.parse_delay_rows(rows)
    statsuite.plot_delays(dict)


def stats_emane(save_file, num_nodes, iplist):
    print("\nGenerating EMANE statistics")
    statsuite.generate_emane_stats(NODE_PREFIX, save_file, num_nodes, iplist)
    print("\nCopying EMANE statistics to this computer")
    statsuite.copy_emane_stats(save_file, num_nodes, iplist)
    print("Done.")


def stats_events(save_file, iplist):
    print("Creating stats directories")
    functions.create_dir("./stats/")
    functions.create_dir("./stats/events")
    functions.create_dir("./stats/events/" + save_file)
    functions.create_dir("./stats/events/" + save_file + "/nodedata/")

    print("\nGathering Event data")
    statsuite.generate_event_dbs(iplist)
    sleep(2)

    print("\nCopying Event data")
    statsuite.clear_node_event_data(save_file)
    path_to_db = "/home/emane-01/test/emane/gvine/node/dbs/eventsql_copy.db"
    statsuite.copy_event_dbs(iplist, path_to_db, "./stats/events/" + save_file + "/nodedata/")

    print("\nCombining Event data")
    input_dir = "./stats/events/" + save_file + "/nodedata/"
    output_dir = "./stats/events/" + save_file + "/"
    statsuite.combine_event_dbs(input_dir, output_dir)


def stats_tcpdump(iplist):
    functions.create_dir("./stats/")
    functions.create_dir("./stats/dumps/")
    functions.create_dir("./stats/dumps/" + SAVE_FILE)
    dump_folder = statsuite.copy_dump_files(iplist, "./stats/dumps/" + SAVE_FILE + "/")
    return dump_folder


def jupyter_sql_graphs():
    init_notebook_mode(connected=True)
    paths = glob("./stats/events/" + JUPYTER_SAVE_FILE + "/*.db")
    paths.sort()
    for index in range(len(paths)):
        print("Filename: " + paths[index].split("/")[-1])
        path_to_input = sub(r"[\\]", '', paths[index])
        bucket_size_seconds = 1
        latest_packet_time = statsuite.get_latest_of_all_packets(path_to_input)
        earliest_packet_time = statsuite.get_earliest_of_all_packets(path_to_input)
        last_second = int((latest_packet_time - earliest_packet_time) / 1000)
        statsuite.print_delay_data(path_to_input)

        file_name = "SentPackets" + str(index + 1)
        buckets_dict = statsuite.make_packets_sent_buckets(path_to_input, bucket_size_seconds)
        figure = statsuite.plot_packets_sent_data(buckets_dict, bucket_size_seconds, last_second)
        figure['layout'].update(title=file_name)
        statsuite.plot_figure(figure, file_name, offline=True)
        print("Sent packet data:")
        type_data = statsuite.get_packet_type_data(path_to_input, "loggableeventpacketsent", 3)
        statsuite.print_type_data(type_data, 4)

        file_name = "ReceivedPackets" + str(index + 1)
        buckets_dict = statsuite.make_packets_received_buckets(path_to_input, bucket_size_seconds)
        figure = statsuite.plot_packets_received_data(buckets_dict, bucket_size_seconds, last_second)
        figure['layout'].update(title=file_name)
        statsuite.plot_figure(figure, file_name, offline=True)
        print("Received packet data:")
        type_data = statsuite.get_packet_type_data(path_to_input, "loggableeventpacketreceived", 4)
        statsuite.print_type_data(type_data, 5)

        file_name = "RankRx" + str(index + 1)
        buckets_dict = statsuite.make_rank_buckets(path_to_input, bucket_size_seconds)
        figure = statsuite.plot_rank_data(buckets_dict, bucket_size_seconds, last_second)
        figure['layout'].update(title=file_name)
        statsuite.plot_figure(figure, file_name, offline=True)


def jupyter_pcap_graphs():
    init_notebook_mode(connected=True)
    paths = glob("./stats/dumps/" + JUPYTER_SAVE_FILE + "/*")
    paths.sort()
    bucket_size = 1
    for index in range(len(paths)):
        folder_path = paths[index]
        print("PCAP folder path: " + folder_path)
        print("\n".join(statsuite.read_params(folder_path)))
        seconds_dict = packetsuite.make_type_packets_dict(chosen_dir=folder_path)
        graphsuite.plot_type_direction(seconds_dict, "sent", bucket_size, False, "tx_each_second")
        graphsuite.plot_type_direction(seconds_dict, "received", bucket_size, False,
                                       "rx_each_second")
        graphsuite.plot_type_direction(seconds_dict, "sent", bucket_size, True, "tx_cumulative")
        graphsuite.plot_type_direction(seconds_dict, "received", bucket_size, True, "rx_cumulative")


def stats_basic_packets():
    init_notebook_mode(connected=True)
    seconds_dict = packetsuite.make_basic_packets_dict()
    graphsuite.plot_basic_direction(seconds_dict, "sent", False, "Sent Cumulative")
    graphsuite.plot_basic_direction(seconds_dict, "received", False, "Received Cumulative")
    graphsuite.plot_basic_direction(seconds_dict, "sent", True, "Sent Average")
    graphsuite.plot_basic_direction(seconds_dict, "received", True, "Received Average")


def stats_basic_packets_combined():
    init_notebook_mode(connected=True)
    seconds_dict = packetsuite.make_basic_packets_dict()
    combined_dict = packetsuite.make_basic_combined_dict(seconds_dict)
    graphsuite.plot_basic_combined_direction(combined_dict, "sent", True, False, "Unicast")
    graphsuite.plot_basic_combined_direction(combined_dict, "sent", False, True, "Tx Cumulative")
    # graphsuite.plot_basic_combined_direction(combined_dict, "sent", False, False, "Tx Per Second")
    graphsuite.plot_basic_combined_direction(combined_dict, "received", True, False, "Rx Average")
    graphsuite.plot_basic_combined_direction(combined_dict, "received", False, True, "Rx Cumulative")
    # graphsuite.plot_basic_combined_direction(combined_dict, "received", False, False, "Rx Per Second")


def stats_type_packets():
    init_notebook_mode(connected=True)
    bucket_size = int(input("Bucket Size? : "))
    seconds_dict = packetsuite.make_type_packets_dict()
    graphsuite.plot_type_direction(seconds_dict, "sent", bucket_size, False, "tx_each_second")
    graphsuite.plot_type_direction(seconds_dict, "received", bucket_size, False, "rx_each_second")
    graphsuite.plot_type_direction(seconds_dict, "sent", bucket_size, True, "tx_cumulative")
    graphsuite.plot_type_direction(seconds_dict, "received", bucket_size, True, "rx_cumulative")


def stats_stop_beacons():
    paths = packetsuite.get_sql_timestamp_dbs()
    chosen_path = functions.choose_timestamp_path(paths)
    stop_dict = statsuite.make_stop_beacon_dict(chosen_path)
    init_notebook_mode(connected=True)
    graphsuite.plot_stop_dict(stop_dict, "tx", "tx_stop_beacons")


def stats_sent_packets():
    paths = glob("./stats/events/" + SAVE_FILE + "/*.db")
    paths.sort()
    paths.reverse()
    num = str(len(paths) - 1)

    user_input = input("Index of sqlite3 db? (0 newest, " + num + " oldest) : ")
    index = int(user_input)
    path_to_input = sub(r"[\\]", '', paths[index])
    bucket_size_seconds = int(input("Bucket size? (seconds) : "))
    buckets_dict = statsuite.make_packets_sent_buckets(path_to_input, bucket_size_seconds)

    should_plot = input("Plot this data (yes or no)? : ")
    if(should_plot.lower() == "yes"):
        latest_packet_time = statsuite.get_latest_of_all_packets(path_to_input)
        earliest_packet_time = statsuite.get_earliest_of_all_packets(path_to_input)
        last_second = int((latest_packet_time - earliest_packet_time) / 1000)
        statsuite.plot_packets_sent_data(buckets_dict, bucket_size_seconds, last_second)
    print("Success")


def stats_received_packets():
    paths = glob("./stats/events/" + SAVE_FILE + "/*.db")
    paths.sort()
    paths.reverse()
    num = str(len(paths) - 1)

    user_input = input("Index of sqlite3 db? (0 newest, " + num + " oldest) : ")
    index = int(user_input)
    path_to_input = sub(r"[\\]", '', paths[index])
    bucket_size_seconds = int(input("Bucket size? (seconds) : "))
    buckets_dict = statsuite.make_packets_received_buckets(path_to_input, bucket_size_seconds)

    should_plot = input("Plot this data (yes or no)? : ")
    if(should_plot.lower() == "yes"):
        latest_packet_time = statsuite.get_latest_of_all_packets(path_to_input)
        earliest_packet_time = statsuite.get_earliest_of_all_packets(path_to_input)
        last_second = int((latest_packet_time - earliest_packet_time) / 1000)
        statsuite.plot_packets_received_data(buckets_dict, bucket_size_seconds, last_second)
    print("Success")


def stats_received_rank():
    paths = glob("./stats/events/" + SAVE_FILE + "/*.db")
    paths.sort()
    paths.reverse()
    num = str(len(paths) - 1)

    user_input = input("Index of sqlite3 db? (0 newest, " + num + " oldest) : ")
    index = int(user_input)
    path_to_input = sub(r"[\\]", '', paths[index])
    bucket_size_seconds = int(input("Bucket size? (seconds) : "))
    buckets_dict = statsuite.make_rank_buckets(path_to_input, bucket_size_seconds)

    should_plot = input("Plot this data (yes or no)? : ")
    if(should_plot.lower() == "yes"):
        latest_packet_time = statsuite.get_latest_of_all_packets(path_to_input)
        earliest_packet_time = statsuite.get_earliest_of_all_packets(path_to_input)
        last_second = int((latest_packet_time - earliest_packet_time) / 1000)
        print("latest: " + str(latest_packet_time))
        print("earliest: " + str(earliest_packet_time))
        print("last_second: " + str(last_second))
        statsuite.plot_rank_data(buckets_dict, bucket_size_seconds, last_second)
    print("Success")


def stats_parse(save_file, num_nodes, parse_term):
    phys = statsuite.parse_emane_stats(save_file, num_nodes, parse_term)
    statsuite.sub_plot(phys)
    statsuite.plot_values(phys, "emane")


def norm_monitor(iplist):
    num_nodes = len(iplist)
    try:
        node_num = int(input("Monitor which node? (1-" + str(num_nodes) + "): "))
    except ValueError:
        print("Error: Must be a numerical value")
        return

    if(node_num < 1 or node_num > num_nodes):
        print("Error: Must be a number between 1 and " + str(num_nodes))
        return

    ip_to_monitor = iplist[node_num - 1]
    file_to_monitor = input("Monitor which file? : ")
    testsuite.norm_monitor(ip_to_monitor, file_to_monitor)


def stats_delays(save_file, num_nodes):
    delays = statsuite.parse_delayfiles("./stats/delays/" + save_file, num_nodes)
    statsuite.plot_values(delays, "delay")


def clean():
    clean_amount = input("Clean 1) Data 2) Non certs 3) All non .jar : ")
    if(clean_amount == "1"):
        functions.clean_node_data(IP_FILE)
    elif(clean_amount == "2"):
        functions.clean_more(IP_FILE)
    elif(clean_amount == "3"):
        functions.clean_nodes(IP_FILE)


# Deletes the topologies/<topology-name>/ folder on each rackspace node
def delete(save_file):
    functions.remote_delete_topology(NODE_PREFIX, SAVE_FILE)


# Kills EVERY rackspace node
def kill():
    functions.kill_all_instances()


def usage():
    # Write the command and its description
    usage = OrderedDict()
    usage["h"] = "show this help message"
    usage["help"] = "show this help message"
    usage["usage"] = "show this help message"

    setup = OrderedDict()
    setup["init"] = "create rackspace cloud instances"
    setup["iplist"] = "update iplist and pssh-hosts"
    setup["reset"] = "reset the topology"
    setup["configure"] = "write platform files, scenario.eel, emane scripts"
    setup["setup"] = "configure command + send to nodes on rackspace"
    setup["push_scenario"] = "push the scenario.eel files to the nodes"
    setup["pushconfig"] = "push gvine.conf.json in ./autotestfiles to nodes"
    setup["txrate"] = "Change gvine.conf.json TargetTxRateBps"
    setup["fragsize"] = "Change gvine.conf.json FragmentSize"
    setup["gvpki"] = "reload node certifications"
    setup["seterrorrate"] = "set error rate for nodes"
    setup["removeerrorrate"] = "remove error rate for nodes"

    start = OrderedDict()
    start["start"] = "start emane and grapevine"
    start["start_console"] = "start and show output in popup terminal"
    start["start_emane"] = "start only emane on nodes"
    start["start_gvine"] = "start only grapevine on nodes"
    start["start_norm"] = "start only norm on nodes"

    test = OrderedDict()
    test["ping"] = "ping nodes to test if they are conencted"
    test["autotest"] = "setup, then test all permutations of parameters"
    test["transferdelay"] = "calculate message transfer delays for dbs in stats/<topo_name>/"
    test["avghoptransferdelay"] = "calculate average hop transfer delay from transferdelay.db"
    test["nodedelay"] = "calculate node delays for dbs in stats/<topo_name>/"
    test["message"] = "send a message on grapevine"
    test["norm_message"] = "send a message on norm"
    test["testmessage"] = "send a message on grapvine and check if it sent correctly"
    test["checkreceiving"] = "Check to see if the network is receiving any file"
    test["checkreceived"] = "Check to see if the network has received a file"

    data = OrderedDict()
    data["data"] = "print data"
    data["stats"] = "save statistics"
    data["stats_events"] = "get events from nodes and combine into single sqlite db"
    data["delays"] = "save grapevine delay statistics"
    data["txpackets"] = "graph sent packets"
    data["rxpackets"] = "graph received packets"
    data["rxrank"] = "graph received rank"
    data["emane_stats"] = "get emane statistics"
    data["parse"] = "parse emane statistics"
    data["norm_monitor"] = "monitor norm"

    stop = OrderedDict()
    stop["stop"] = "stop emane and grapevine"
    stop["stop_gvine"] = "stop only grapevine"
    stop["stop_norm"] = "stop only norm"

    finished = OrderedDict()
    finished["clean"] = "remove all non .jar files from ~/test/emane/gvine/node/ on nodes"
    finished["delete"] = "delete cloud topography folders"
    finished["kill"] = "kill rackspace cloud instances"

    header = []
    header.append("---------- USAGE ----------\npython3 racksuite.py ~OR~ ./racksuite.py\n")
    header.append("---------- SETUP COMMANDS ----------")
    header.append("---------- START COMMANDS ----------")
    header.append("---------- TEST COMMANDS ----------")
    header.append("---------- DATA COMMANDS ----------")
    header.append("---------- STOP COMMANDS ----------")
    header.append("---------- FINISHED COMMANDS ----------")

    # Print the usage for each command
    commands_list = [setup, start, test, data, stop, finished]
    commands = []
    for command_list in commands_list:
        commands += [item for item in list(command_list.items())]
    commands = [command for command, description in commands]
    max_command_len = str(len(max(commands, key=len)))

    print(header.pop(0))
    for command_list in commands_list:
        print()
        print(header.pop(0))
        print()
        for command, description in command_list.items():
            string_to_format = "{:>" + max_command_len + "}\t{}"
            print(string_to_format.format(command, description))
