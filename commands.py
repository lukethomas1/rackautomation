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
from time import sleep, time
from os import path
from collections import OrderedDict
import logging
import threading
from subprocess import call

# Third Party Imports
from glob import glob
from re import sub
from plotly.offline import init_notebook_mode
from pickle import load, dump
import plotly
import img2pdf

# Local Imports
import functions
import testsuite
import statsuite
import autotest
import packetsuite
import graphsuite
import config
import constants
from classes.racknode import RackNode
from classes.pinode import PiNode

# This suppresses warning messages produced by scapy on module load
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)
from scapy.all import rdpcap

# Constants defined in config.py
NODE_PREFIX = config.NODE_PREFIX
SAVE_FILE = config.SAVE_FILE
JUPYTER_SAVE_FILE = config.JUPYTER_SAVE_FILE
IMAGE_NAME = config.IMAGE_NAME
RACK_USERNAME = config.RACK_USERNAME
PI_USERNAME = config.PI_USERNAME
RACK_IP_FILE = config.RACK_IP_FILE
PI_IP_FILE = config.PI_IP_FILE
PI_IP_LIST = config.PI_IP_LIST
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


def get_assigned_nodes():
    if not path.isfile(".data.nodes"):
        with open(".data.nodes", "wb") as file:
            data = {"nodes": []}
            dump(data, file)
        return []
    else:
        with open(".data.nodes", "rb") as file:
            return load(file)["nodes"]


def reset_topology():
    functions.set_topology(SAVE_FILE, NODE_PREFIX)
    print("Topology reset, config updated")


# Creates # of nodes necessary for desired topology on rackspace
def initialize(save_file, num_nodes):
    functions.create_rackspace_instances(num_nodes, IMAGE_NAME, RACK_KEY, save_file, NODE_PREFIX)
    print("Done.")


def wait_for_nodes_init(num_nodes):
    print("Checking if nodes are ready")
    nodes_ready = functions.wait_until_nodes_ready(NODE_PREFIX, num_nodes, 9999)
    if nodes_ready:
        print(str(num_nodes) + " nodes are ready!")


def assign_nodes(subnets, nodes):
    platform = input("Input Platform : ")
    node_objects = []

    # Get the list of ips
    if platform == "rack":
        status_list = functions.get_rack_status_list()
        active_node_list = [pair[0] for pair in status_list if pair[1] == "ACTIVE"]
        functions.set_topology(SAVE_FILE, NODE_PREFIX)
        configuration = functions.load_data()
        ip_dict = configuration['nodeipdict']
    elif platform == "pi":
        ips = PI_IP_LIST

    index = 0
    added_nodes = 0
    while added_nodes < len(nodes):
        node_name = NODE_PREFIX + str(index + 1)
        member_subnets = [subnets.index(subnet) + 1 for subnet in subnets if index + 1 in subnet[
            'memberids']]
        if platform == "rack" and node_name in active_node_list:
            this_node = RackNode(node_name, "emane-01", index + 1, ip_dict[node_name],
                                 platform, "/home/emane-01/gvinetest/", member_subnets, "emane",
                                 "/home/emane-01/emane/topologies/")
            print("Adding rackspace node: " + node_name)
            node_objects.append(this_node)
            added_nodes += 1
        else:
            print(node_name + " is not active")

        if platform == "pi":
            this_node = PiNode(node_name, "pi", index+1, ips[index], platform,
                               "/home/pi/test/", member_subnets, "wlan")
            node_objects.append(this_node)
            added_nodes += 1
        elif platform != "rack" and platform != "pi":
            print("Unknown platform: " + platform + ", exiting")
            exit(-1)
        index += 1
    return node_objects


def make_iplist(num_nodes, iplist):
    functions.generate_iplist(num_nodes, NODE_PREFIX)
    functions.edit_ssh_config()
    functions.add_known_hosts(iplist)


def make_ipfile(num_nodes):
    functions.generate_iplist(num_nodes, NODE_PREFIX)
    functions.edit_ssh_config()


def edit_ssh():
    functions.edit_ssh_config()

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
    # pathloss_value = int(input("Input pathloss value : "))
    # functions.write_scenario(subnets, nodes, topo_path, pathloss_value)
    functions.write_scenario(subnets, nodes, topo_path, 0)


# Runs configure() to create topology locally, 
# then distributes topology to rackspace nodes
def setup(save_file, subnets, nodes, node_objects):
    # Write configuration files (configure() method) before sending to nodes
    if(not path.isdir("./topologies/" + save_file)):
        configure(save_file, subnets, nodes)
    else:
        print(save_file + " already configured")

    # Multithreaded setup
    threads = []
    for node in node_objects:
        new_thread = threading.Thread(target=node.setup_gvine, args=(save_file,))
        threads.append(new_thread)
        new_thread.start()
    for t in threads:
        t.join()

    # Do node certifications
    gvpki(node_objects)
    print("Done.")


def update_emane(save_file, subnets, nodes, node_objects):
    configure(save_file, subnets, nodes)
    threads = []
    for node in node_objects:
        new_thread = threading.Thread(target=node.setup_emane, args=(save_file,))
        threads.append(new_thread)
        new_thread.start()
    for t in threads:
        t.join()


def change_tx_rate():
    tx_rate = input("New TargetTxRateBps? : ")
    path_to_conf = "./autotestfiles/gvine.conf.json"
    functions.change_gvine_tx_rate(tx_rate, path_to_conf)


def change_frag_size():
    frag_size = input("New FragmentSize? : ")
    path_to_conf = "./autotestfiles/gvine.conf.json"
    functions.change_gvine_frag_size(frag_size, path_to_conf)


def push_config(node_objects):
    file_name = input("Enter filename to push (blank for gvine.conf.json): ")
    if not file_name:
        file_name = "gvine.conf.json"
    if path.isfile("./autotestfiles/" + file_name):
        path_to_conf = path.expanduser("./autotestfiles/" + file_name)
    else:
        print("ERROR: Nonexistant config file")
        return
    dest_file_name = input("Enter filename to save as (blank for gvine.conf.json): ")
    dest_file_name = dest_file_name if dest_file_name else "gvine.conf.json"
    print("Pushing ./autotestfiles/" + file_name + " to nodes as ~/gvinetest/gvine.conf.json")
    threads = []
    for node in node_objects:
        new_thread = threading.Thread(target=node.push_file, args=(path_to_conf, node.gvine_path,
                                                                   dest_file_name))
        threads.append(new_thread)
        new_thread.start()
    for t in threads:
        t.join()


def push_file(node_objects):
    src_path = input("Input source file path: ")
    dest_path = input("Input destination file path (1: default gvine 2: default emane): ")
    file_name = input("Input file name (blank for unchanged): ")
    src_path = path.expanduser(src_path)

    threads = []
    for node in node_objects:
        if(dest_path == "1"):
            dest_path = node.gvine_path + file_name
        elif(dest_path == "2"):
            dest_path = node.topo_dir + file_name
        else:
            dest_path = path.expanduser(dest_path)
        new_thread = threading.Thread(target=node.push_file, args=(src_path, dest_path,))
        threads.append(new_thread)
        new_thread.start()
    for t in threads:
        t.join()


def gvpki(node_objects):
    # Generate cert on each node
    print("Generating certs")
    gen_threads = []
    for node in node_objects:
        new_thread = threading.Thread(target=node.generate_cert)
        gen_threads.append(new_thread)
        new_thread.start()
    for t in gen_threads:
        t.join()

    # Clear out old certs
    functions.execute_shell("rm ./keystore/*")

    pull_threads = []
    print("Pulling certs")
    for node in node_objects:
        new_thread = threading.Thread(target=node.pull_cert)
        pull_threads.append(new_thread)
        new_thread.start()
    for t in pull_threads:
        t.join()
    sleep(3)

    push_threads = []
    print("Pushing certs")
    for node in node_objects:
        new_thread = threading.Thread(target=node.push_certs, args=("./keystore/*",))
        push_threads.append(new_thread)
        new_thread.start()
    for t in push_threads:
        t.join()
    sleep(3)

    load_threads = []
    print("Loading certs")
    for node in node_objects:
        new_thread = threading.Thread(target=node.load_certs, args=(len(node_objects),))
        load_threads.append(new_thread)
        new_thread.start()
    for t in load_threads:
        t.join()
    print("Certs completed")


def gvpki_push_load(node_objects):
    print("Pushing certs")
    for node in node_objects:
        node.push_certs("./keystore/*")
    sleep(2)
    print("Loading certs")
    for node in node_objects:
        node.load_certs(len(node_objects))


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
def start(save_file, node_objects):
    threads = []
    for node in node_objects:
        new_thread = threading.Thread(target=node.start, args=(JAR_FILE, save_file,))
        threads.append(new_thread)
        new_thread.start()
    for t in threads:
        t.join()
    print("Done.")


def start_choose(save_file, node_objects):
    node_input = input("Enter node number or range of numbers (e.g 13 or 13-23): ")
    start_nodes = []
    if "-" in node_input:
        range = node_input.split("-")
        start_range = int(range[0])
        end_range = int(range[-1])
        for index in range(start_range, end_range + 1):
            start_nodes.append(node_objects[index])
    else:
        start_nodes.append(node_objects[int(node_input)])

    for node in start_nodes:
        print("Starting on " + node.name)
        node.start(JAR_FILE, save_file)
    print("Done.")



def start_debug(save_file, iplist, nodes, subnets, nodeipdict):
    functions.synchronize(RACK_IP_FILE)

    print("Starting emane")
    script_name = 'emane_start.sh'
    functions.remote_emane(save_file, RACK_IP_FILE, script_name)
    sleep(2)

    print("Logging subnet traffic with tcpdump")
    functions.subnet_tcpdump(nodes, subnets, NODE_PREFIX, nodeipdict)

    print("Deleting previous gvine log files")
    functions.delete_gvine_log_files(RACK_IP_FILE)
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


def start_emane(save_file, node_objects):
    print("Starting emane")
    script_name = 'emane_start.sh'
    for node in node_objects:
        if isinstance(node, RackNode):
            node.remote_emane(save_file, script_name)
        else:
            print("Trying to start EMANE on non-RackNode")


def start_gvine(iplist):
    jar_name = input("Name of jar file(leave blank for default): ")
    if(not jar_name):
        jar_name = JAR_FILE
    functions.remote_start_gvine(iplist, jar_name)


def restart_gvine(node_objects):
    node_input = input("Enter a node index or range of indices to restart (e.g 13 or 13-23): ")
    chosen_nodes = []
    if "-" in node_input:
        node_range = node_input.split("-")
        start_range = int(node_range[0])
        end_range = int(node_range[-1])
        for index in range(start_range, end_range + 1):
            chosen_nodes.append(node_objects[index])
    else:
        chosen_nodes.append(node_objects[int(node_input)])

    for node in chosen_nodes:
        node.stop_gvine()
        node.remote_start_gvine(JAR_FILE)



def start_norm(iplist, subnets, nodes):
    send_bps = 50000
    receive_bps = 100000
    functions.start_norm(iplist, subnets, nodes, send_bps, receive_bps)


# Runs emane_stop.sh on each rackspace node in the topology
def stop(node_objects):
    threads = []
    for node in node_objects:
        new_thread = threading.Thread(target=node.stop_all, args=(SAVE_FILE,))
        threads.append(new_thread)
        new_thread.start()
    for t in threads:
        t.join()
    print("Done.")


def start_partial(node_objects):
    node_list = functions.get_node_list(len(node_objects))

    threads = []
    for node_index in node_list:
        index = node_index - 1
        node = node_objects[index]
        new_thread = threading.Thread(target=node.start_partial, args=(config.JAR_FILE,SAVE_FILE,))
        threads.append(new_thread)
        new_thread.start()
    for t in threads:
        t.join()
    print("Done.")


def stop_partial(node_objects):
    node_list = functions.get_node_list(len(node_objects))

    threads = []
    for node_index in node_list:
        index = node_index - 1
        node = node_objects[index]
        new_thread = threading.Thread(target=node.stop_partial, args=(SAVE_FILE,))
        threads.append(new_thread)
        new_thread.start()
    for t in threads:
        t.join()
    print("Done.")


def stop_gvine(node_objects):
    for node in node_objects:
        functions.remote_execute("sudo pkill java", node.ip, node.user_name)


def stop_norm(node_objects):
    for node in node_objects:
        functions.remote_execute("sudo pkill norm", node.ip, node.user_name)


def start_basic_tcpdump(nodes, subnets, nodeipdict):
    print("Logging subnet traffic with tcpdump")
    functions.subnet_tcpdump(nodes, subnets, NODE_PREFIX, nodeipdict)


def stop_all_tcpdump():
    functions.parallel_ssh(RACK_IP_FILE, "sudo pkill tcpdump")


def rack_ping(subnets):
    print("Setting up")
    functions.generate_network_ping_list(subnets, RACK_IP_FILE, IP_BLACK_LIST)
    testsuite.ping_network()
    print("Done.")


def run_auto_test(platform):
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
    if platform == "rack":
        autotest.initialize_parameters(max_tx_rate, num_iterations, msg_sizes_bytes, error_rates,
                                       msg_interval, initial_indices, RACK_IP_FILE)
    elif platform == "pi":
        autotest.initialize_parameters(max_tx_rate, num_iterations, msg_sizes_bytes, error_rates,
                                       msg_interval, initial_indices, PI_IP_FILE)

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
        start_index = int(indices[0])
        end = int(indices[1])
        for ind in range(start_index, end + 1):
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
    

def test_message(node_objects):
    message_name = input("Choose message file name: ")
    file_size = input("Choose file size (kilobytes): ")
    node_objects[0].make_test_file(message_name, file_size)
    node_objects[0].send_gvine_file(message_name)
    testsuite.wait_for_message_received(message_name, node_objects, 1, 9999)


def test_multiple_messages(node_objects):
    num_msgs = int(input("Number of messages: "))
    msg_name = input("Input message prefix: ")
    msg_size = input("Choose file size (kilobytes): ")
    msg_sender_dict = {}
    for msg_index in range(num_msgs):
        sender_id = int(input("Input id of sender node for message #" +
                              str(msg_index) + " (1-" + str(len(node_objects)) + "): "))
        msg_sender_dict[msg_index] = sender_id
    msg_interval = int(input("Interval between messages: "))

    num_sent = 0
    for msg_index in msg_sender_dict.keys():
        num_sent += 1
        sender_id = msg_sender_dict[msg_index]
        curr_msg = msg_name + str(msg_index)
        node_objects[sender_id - 1].make_test_file(curr_msg, msg_size)
        last_time = time()
        node_objects[sender_id - 1].send_gvine_file(curr_msg)
        if num_sent != len(msg_sender_dict):
            sleep(msg_interval - (time() - last_time))

    for msg_index in range(num_msgs):
        curr_msg = msg_name + str(msg_index)
        sender_id = msg_sender_dict[msg_index]
        testsuite.wait_for_message_received(curr_msg, node_objects, sender_id, 9999)


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


def stats_emane(save_file, node_objects):
    # Create directory for stats to go in
    functions.create_dir("./stats/emane/" + save_file)

    print("\nGenerating EMANE statistics")
    threads = []
    for node in node_objects:
        if isinstance(node, RackNode):
            new_thread = threading.Thread(target=node.generate_emane_stats, args=(save_file,))
            threads.append(new_thread)
            new_thread.start()
    for t in threads:
        t.join()

    print("\nCopying EMANE statistics to this computer")
    threads = []
    for node in node_objects:
        if isinstance(node, RackNode):
            new_thread = threading.Thread(target=node.copy_emane_stats, args=(save_file,))
            threads.append(new_thread)
            new_thread.start()
    for t in threads:
        t.join()
    print("Done.")


def stats_events(save_file, node_objects):
    print("Creating stats directories")
    functions.create_dir("./stats/")
    functions.create_dir("./stats/events")
    functions.create_dir("./stats/events/" + save_file)
    functions.create_dir("./stats/events/" + save_file + "/nodedata/")

    print("\nGathering Event data")
    for node in node_objects:
        node.generate_event_db()
    sleep(2)

    print("\nCopying Event data")
    statsuite.clear_node_event_data(save_file)
    for node in node_objects:
        node.copy_event_db(save_file)

    print("\nCombining Event data")
    input_dir = "./stats/events/" + save_file + "/nodedata/"
    output_dir = "./stats/events/" + save_file + "/"
    statsuite.combine_event_dbs(input_dir, output_dir)


def stats_tcpdump(node_objects):
    functions.create_dir("./stats/")
    functions.create_dir("./stats/dumps/")
    functions.create_dir("./stats/dumps/" + SAVE_FILE)
    output_dir = "./stats/dumps/" + SAVE_FILE + "/"
    dump_folder = statsuite.copy_dump_files(node_objects, output_dir)
    map_path = dump_folder + "ipmap"
    statsuite.make_ipmap(node_objects, map_path)
    return dump_folder


def pull_logfiles(node_objects):
    node_list = []
    try:
        user_input = input("Input node index to pull logs from (1-" + str(len(node_objects)) +
                               "): ")
        while user_input != "":
            user_input = int(user_input)
            if 1 <= user_input <= len(node_objects):
                node_list.append(user_input)
            else:
                print("index out of range, try again")
            user_input = input("Input another node index (1-" +
                                   str(len(node_objects)) + ") to pull logs from (blank to "
                                                            "continue): ")
    except KeyboardInterrupt:
        return

    # Make a new log file folder for each run
    folder_name = "./logfiles/logs_"
    num_folders = glob(folder_name + "*")
    folder_name = folder_name + str(len(num_folders)) + "/"
    functions.create_dir(folder_name)

    # Include the config used with the log files
    config_input = input("Config file to include: ")
    config_path = "./autotestfiles/" + config_input
    exists = path.exists(config_path)
    while not exists:
        config_input = input("Doesn't exist, try again. Config file to include: ")
        config_path = "./autotestfiles/" + config_input
        exists = path.exists(config_path)
    command = "cp " + config_path + " " + folder_name
    call(command, shell=True)

    threads = []
    for node_index in node_list:
        node = node_objects[node_index - 1]
        new_thread = threading.Thread(target=node.pull_log_file, args=[folder_name,])
        threads.append(new_thread)
        new_thread.start()
    for t in threads:
        t.join()


def print_scapy_packet(chosen_save):
    dump_dirs = glob("./stats/dumps/" + chosen_save + "/*")
    chosen_dir = functions.choose_alphabetic_path(dump_dirs)
    pcap_files = glob(chosen_dir + "/*.pcap")
    chosen_pcap = pcap_files[0]
    packets = rdpcap(chosen_pcap)
    chosen_packet = packets[0]
    packetsuite.useful_functions(chosen_packet)
    packetsuite.test_packet_functions(chosen_packet)
    for pcap in pcap_files:
        packet_list = rdpcap(pcap)
        packetsuite.test_list_of_packets(packet_list)


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


def stats_basic_packets(chosen_save=None):
    chosen_dir = ""
    if(chosen_save is not None):
        dump_dirs = glob("./stats/dumps/" + chosen_save + "/*")
        chosen_dir = functions.choose_alphabetic_path(dump_dirs)

    init_notebook_mode(connected=True)
    seconds_dict = packetsuite.make_basic_packets_dict(chosen_dir)
    graphsuite.plot_basic_direction(seconds_dict, "tx", False, "Sent Cumulative")
    graphsuite.plot_basic_direction(seconds_dict, "rx", False, "Received Cumulative")
    graphsuite.plot_basic_direction(seconds_dict, "tx", True, "Sent Average")
    graphsuite.plot_basic_direction(seconds_dict, "rx", True, "Received Average")


def stats_basic_packets_combined(chosen_save=None):
    chosen_dir = ""
    if(chosen_save is not None):
        dump_dirs = glob("./stats/dumps/" + chosen_save + "/*")
        chosen_dir = functions.choose_alphabetic_path(dump_dirs)

    init_notebook_mode(connected=True)
    seconds_dict = packetsuite.make_basic_packets_dict(chosen_dir)
    combined_dict = packetsuite.make_basic_combined_dict(seconds_dict)
    graphsuite.plot_basic_combined_direction(combined_dict, "tx", True, False, "Unicast")
    graphsuite.plot_basic_combined_direction(combined_dict, "tx", False, True, "Tx Cumulative")
    # graphsuite.plot_basic_combined_direction(combined_dict, "sent", False, False, "Tx Per Second")
    graphsuite.plot_basic_combined_direction(combined_dict, "rx", True, False, "Rx Average")
    graphsuite.plot_basic_combined_direction(combined_dict, "rx", False, True, "Rx Cumulative")
    # graphsuite.plot_basic_combined_direction(combined_dict, "received", False, False, "Rx Per Second")


def stats_type_packets(chosen_save=None):
    chosen_dir = None
    if(chosen_save is not None):
        dump_dirs = glob("./stats/dumps/" + chosen_save + "/*")
        chosen_dir = functions.choose_alphabetic_path(dump_dirs)

    init_notebook_mode(connected=True)
    bucket_size = int(input("Bucket Size? : "))
    seconds_dict = packetsuite.make_type_packets_dict(chosen_dir)
    graphsuite.plot_type_direction(seconds_dict, "tx", bucket_size, False, False, "tx_each_second")
    graphsuite.plot_type_direction(seconds_dict, "rx", bucket_size, False, False, "rx_each_second")
    graphsuite.plot_type_direction(seconds_dict, "tx", bucket_size, True, False, "tx_cumulative")
    graphsuite.plot_type_direction(seconds_dict, "rx", bucket_size, True, False, "rx_cumulative")
    graphsuite.plot_type_direction(seconds_dict, "tx", bucket_size, False, True, "tx_average")
    graphsuite.plot_type_direction(seconds_dict, "rx", bucket_size, False, True, "rx_average")


def pcap_to_sql(save):
    dump_dirs = glob("./stats/dumps/" + save + "/*")
    chosen_dir = functions.choose_alphabetic_path(dump_dirs)
    packetsuite.make_packets_database(chosen_dir)


def stats_single_graph(save, download=False):
    dump_dirs = glob("./stats/dumps/" + save + "/*")
    chosen_dir = functions.choose_alphabetic_path(dump_dirs)
    num_nodes = len(glob(chosen_dir + "/*.cap") + glob(chosen_dir + "/*.pcap"))
    node_number = input("Graph for which node id (1-" + str(num_nodes) + "): ")
    bucket_size = int(input("Bucket Size? : "))
    db_path = chosen_dir + "/" + "packets.db"
    node_name = NODE_PREFIX + node_number

    packetsuite.make_packets_database(chosen_dir)

    # Setup to download graphs
    functions.create_dir("./graphs")

    graph_configs = [
        ("tx", 0, "tx_each_second"),
        ("rx", 0, "rx_each_second"),
        ("tx", 1, "tx_cumulative"),
        ("rx", 1, "rx_cumulative"),
        ("tx", 2, "tx_average"),
        ("rx", 2, "rx_average")
    ]

    init_notebook_mode(connected=True)
    seconds_dict = packetsuite.make_single_dict(node_name, db_path)
    for cnfg in graph_configs:
        graphsuite.plot_type_direction(seconds_dict, cnfg[0], bucket_size, cnfg[1], cnfg[2], download)

    if not download:
        return

    # Move graphs to ~/GrapeVine/testwebsite/rackpython/graphs
    sleep(1)
    graph_folder = "~/GrapeVine/testwebsite/rackpython/graphs/"
    for cnfg in graph_configs:
        file_location = "~/Downloads/" + cnfg[2] + ".png"
        move_location = graph_folder + cnfg[2] + ".png"
        command = "mv " + file_location + " " + move_location
        call(command, shell=True)

    # Make pdf from graphs
    sleep(1)
    pdf_location = "./graphs/node" + str(node_number) + ".pdf"
    img_graphs = []
    for cnfg in graph_configs:
        img_graphs.append("./graphs/" + cnfg[2] + ".png")
    pdf_file = open(pdf_location, "wb")
    print(str(img_graphs))
    pdf_file.write(img2pdf.convert([i for i in img_graphs]))
    pdf_file.close()


def stats_multiple_graphs(save, download=False):
    dump_dirs = glob("./stats/dumps/" + save + "/*")
    chosen_dir = functions.choose_alphabetic_path(dump_dirs)
    num_nodes = len(glob(chosen_dir + "/*.cap") + glob(chosen_dir + "/*.pcap"))
    node_list = functions.get_node_list(num_nodes)
    bucket_size = int(input("Bucket Size? : "))
    db_path = chosen_dir + "/" + "packets.db"

    packetsuite.make_packets_database(chosen_dir)

    # Setup to download graphs
    functions.create_dir("./graphs")

    graph_configs = [
        ("tx", 0, "tx_each_second"),
        ("rx", 0, "rx_each_second"),
        ("tx", 1, "tx_cumulative"),
        ("rx", 1, "rx_cumulative"),
        ("tx", 2, "tx_average"),
        ("rx", 2, "rx_average")
    ]

    init_notebook_mode(connected=True)

    for node_number in node_list:
        node_name = NODE_PREFIX + str(node_number)
        seconds_dict = packetsuite.make_single_dict(node_name, db_path)
        for cnfg in graph_configs:
            graphsuite.plot_type_direction(seconds_dict, cnfg[0], bucket_size, cnfg[1], cnfg[2], download)

        if not download:
            return

        # Move graphs to ~/GrapeVine/testwebsite/rackpython/graphs
        sleep(1)
        graph_folder = "~/GrapeVine/testwebsite/rackpython/graphs/"
        for cnfg in graph_configs:
            file_location = "~/Downloads/" + cnfg[2] + ".png"
            move_location = graph_folder + cnfg[2] + ".png"
            command = "mv " + file_location + " " + move_location
            call(command, shell=True)

        # Make pdf from graphs
        sleep(1)
        pdf_location = "./graphs/node" + str(node_number) + ".pdf"
        img_graphs = []
        for cnfg in graph_configs:
            img_graphs.append("./graphs/" + cnfg[2] + ".png")
        pdf_file = open(pdf_location, "wb")
        print(str(img_graphs))
        pdf_file.write(img2pdf.convert([i for i in img_graphs]))
        pdf_file.close()


def stats_type_comparison(save, download=False):
    dump_dirs = glob("./stats/dumps/" + save + "/*")
    dump_dirs.sort()
    chosen_dirs = []
    trace_names_dict = {}

    num = str(len(dump_dirs) - 1)
    user_input = input("Choose path (alphabetic a-z 0-" + num + ") : ")
    while user_input != "":
        index = int(user_input)
        if 0 < index < len(dump_dirs):
            chosen_path = sub(r"[\\]", '', dump_dirs[index])
        if chosen_path not in chosen_dirs:
            chosen_dirs.append(chosen_path)
            trace_name = input("Give this path a trace_name : ")
            trace_names_dict[chosen_path] = trace_name
        user_input = input("Choose path (alphabetic a-z 0-" + num + ") (blank to end) : ")

    num_nodes = len(glob(chosen_dirs[0] + "/*.cap") + glob(chosen_dirs[0] + "/*.pcap"))
    node_number = input("Graph for which node id (1-" + str(num_nodes) + "): ")
    bucket_size = int(input("Bucket Size? : "))
    db_paths = [chosen_dir + "/packets.db" for chosen_dir in chosen_dirs]
    trace_names_dict = {chosen_dir + "/packets.db": trace_name for chosen_dir, trace_name in
                        trace_names_dict.items()}
    node_name = NODE_PREFIX + node_number

    for chosen_dir in chosen_dirs:
        packetsuite.make_packets_database(chosen_dir)

    # Setup to download graphs
    functions.create_dir("./graphs")

    graph_configs = [
        ("tx", 0, "tx_each_second"),
        ("rx", 0, "rx_each_second"),
        ("tx", 1, "tx_cumulative"),
        ("rx", 1, "rx_cumulative"),
        ("tx", 2, "tx_average"),
        ("rx", 2, "rx_average")
    ]

    init_notebook_mode(connected=True)

    traces = {}
    for packet_type in constants.PACKET_TYPES:
        traces[packet_type] = {}
        for cnfg in graph_configs:
            traces[packet_type][cnfg[2]] = {}

    color_index = -1
    for db_path in db_paths:
        color_index += 1
        color_index = color_index % len(constants.GRAPH_COLORS)
        graph_color = constants.GRAPH_COLORS[color_index]
        seconds_dict = packetsuite.make_single_dict(node_name, db_path)
        for packet_type in constants.PACKET_TYPES:
            for cnfg in graph_configs:
                traces[packet_type][cnfg[2]][db_path] = \
                    graphsuite.make_type_trace(seconds_dict, cnfg[0], packet_type, node_name,
                                               bucket_size, cnfg[1], graph_color, trace_names_dict[
                                                   db_path])
    graphsuite.plot_type_comparison(traces, graph_configs)

def stats_packet_node(save):
    pcap_path = functions.get_single_node_pcap(save, NODE_PREFIX)
    node_dict = packetsuite.read_pcap(pcap_path)
    print(pcap_path)
    for direction in node_dict.keys():
        print("  " + direction + ": ")
        for packet_type in node_dict[direction].keys():
            packet_list = node_dict[direction][packet_type]
            sum = 0
            for packet in packet_list:
                num_bytes = len(packet)
                sum += num_bytes
            print("    " + packet_type + ": " + str(sum))


def stats_packet_statistics(chosen_save=None):
    if(chosen_save is not None):
        dump_dirs = glob("./stats/dumps/" + chosen_save + "/*")
        chosen_dir = functions.choose_alphabetic_path(dump_dirs)
    else:
        dump_dirs = packetsuite.get_dump_timestamp_dirs()
        chosen_dir = functions.choose_timestamp_path(dump_dirs)
    num_nodes = len(glob(chosen_dir))
    node_dict = packetsuite.get_pcap_node_dict(chosen_dir, num_nodes)

    totals_dict = {
        "tx": {
            "beacon": 0,
            "handshake": 0,
            "babel": 0,
            "payload": 0
        },
        "rx": {
            "beacon": 0,
            "handshake": 0,
            "babel": 0,
            "payload": 0
        }
    }

    # individual byte amounts
    for node_name in node_dict.keys():
        print(node_name + ": ")
        for direction in node_dict[node_name].keys():
            print("  " + direction + ": ")
            for packet_type in node_dict[node_name][direction].keys():
                packet_list = node_dict[node_name][direction][packet_type]
                sum = 0
                for packet in packet_list:
                    num_bytes = len(packet)
                    sum += num_bytes
                    totals_dict[node_name][direction][packet_type] += num_bytes
                print("    " + packet_type + ": " + str(sum))

    # total bytes amounts
    for direction in totals_dict.keys():
        for packet_type in totals_dict[direction].keys():
            total_bytes = totals_dict[direction][packet_type]
            print("Total " + direction + " " + packet_type + ": " + str(total_bytes))


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


def clean(node_objects):
    clean_amount = int(input("Clean 1) Data 2) Non certs 3) All non .jar : "))
    threads = []
    for node in node_objects:
        new_thread = threading.Thread(target=node.clean_gvine, args=(clean_amount,))
        threads.append(new_thread)
        new_thread.start()
    for t in threads:
        t.join()
    print("Cleaned.")


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
