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

# Local Imports
import functions
import testsuite
import statsuite
import autotest
import config

# Constants defined in config.py
NODE_PREFIX = config.NODE_PREFIX
SAVE_FILE = config.SAVE_FILE
IMAGE_NAME = config.IMAGE_NAME
IP_FILE = config.IP_FILE
IP_BLACK_LIST = config.IP_BLACK_LIST
JAR_FILE = config.JAR_FILE

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


# Creates # of nodes necessary for desired topology on rackspace
def initialize(save_file, num_nodes):
    functions.create_rackspace_instances(num_nodes, IMAGE_NAME, save_file, NODE_PREFIX)
    print("Done.")


def make_iplist(num_nodes):
    functions.generate_iplist(num_nodes, NODE_PREFIX)
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
    print("Done.")


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
    send_bps = 800000
    receive_bps = 800000
    functions.start_norm(iplist, subnets, nodes, send_bps, receive_bps)


def stop_gvine():
    print("Stopping gvine")
    functions.parallel_ssh(IP_FILE, "sudo pkill java")


def stop_norm():
    print("Stopping norm")
    functions.parallel_ssh(IP_FILE, "sudo pkill norm")


def ping(subnets, nodes):
    print("Setting up")
    functions.generate_network_ping_list(subnets, nodes, IP_FILE, IP_BLACK_LIST)
    testsuite.ping_network()
    print("Done.")


def run_auto_test(need_setup):
    max_tx_rate = 50000
    num_iterations = 1
    msg_sizes_bytes = ["100000", "500000", "1000000", "10000000"]
    error_rates = [0, 10, 25, 50, 75]
    msg_interval = 1
    if(need_setup):
        autotest.auto_test(max_tx_rate, num_iterations, msg_sizes_bytes,
                error_rates, msg_interval)
    else:
        autotest.iterate(max_tx_rate, num_iterations, msg_sizes_bytes,
                error_rates, msg_interval)


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
    

def test_message(iplist):
    message_name = input("Choose message file name: ")
    file_size = input("Choose file size (kilobytes): ")
    testsuite.message_test_gvine(iplist, message_name, file_size)


def stats(save_file, num_nodes, iplist):
    print("Creating stats directories")
    functions.create_dir("./stats/")
    functions.create_dir("./stats/delays")
    functions.create_dir("./stats/emane")
    functions.create_dir("./stats/events")
    functions.create_dir("./stats/delays/" + save_file)
    functions.create_dir("./stats/emane/" + save_file)
    functions.create_dir("./stats/events/" + save_file)
    functions.create_dir("./stats/events/" + save_file + "/nodedata/")

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
    rows = statsuite.get_sql_delay_data(path_to_sql_db)
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
    path_to_db = "/home/emane-01/test/emane/gvine/node/dbs/eventsql_copy.db"
    statsuite.copy_event_dbs(iplist, path_to_db, "./stats/events/" + save_file + "/nodedata/")

    print("\nCombining Event data")
    input_dir = "./stats/events/" + save_file + "/nodedata/"
    output_dir = "./stats/events/" + save_file + "/"
    statsuite.combine_event_dbs(input_dir, output_dir)


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


# Runs emane_stop.sh on each rackspace node in the topology
def stop(save_file):
    script_file = 'emane_stop.sh'
    functions.remote_emane(save_file, IP_FILE, script_file)
    functions.parallel_ssh(IP_FILE, "sudo pkill java")
    functions.parallel_ssh(IP_FILE, "sudo pkill norm")
    sleep(2)
    print("Done.")
    

def clean():
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
    usage["topology"] = "set the topology to use"
    usage["init"] = "create rackspace cloud instances"
    usage["iplist"] = "update iplist and pssh-hosts"
    usage["configure"] = "write platform files, scenario.eel, emane scripts"
    usage["setup"] = "configure command + send to nodes on rackspace"
    usage["start"] = "start emane and grapevine"
    usage["start_gvine"] = "start only grapevine"
    usage["stop_gvine"] = "stop only grapevine"
    usage["data"] = "print data"
    usage["ping"] = "ping nodes to test if they are conencted"
    usage["autotest"] = "setup, then test all permutations of parameters"
    usage["iterate"] = "autotest without setup"
    usage["message"] = "send a message on grapevine"
    usage["testmessage"] = "send a message on grapvine and check if it sent correctly"
    usage["stats"] = "save statistics"
    usage["stats_events"] = "get events from nodes and combine into single sqlite db"
    usage["delays"] = "save grapevine delay statistics"
    usage["emane_stats"] = "get emane statistics"
    usage["parse"] = "parse emane statistics"
    usage["stop"] = "stop emane and grapevine"
    usage["clean"] = "remove all non .jar files from ~/test/emane/gvine/node/ on nodes"
    usage["delete"] = "delete cloud topography folders"
    usage["kill"] = "kill rackspace cloud instances"
    usage["h"] = "show this help message"
    usage["help"] = "show this help message"
    usage["usage"] = "show this help message"

    # Print the usage header
    header = "---------- USAGE ----------\n"
    header += "python3 racksuite.py ~OR~ ./racksuite.py\n\n"
    header += "---------- COMMANDS ----------\n"
    print(header)

    # Print the usage for each command
    command_len = str(len(max(usage, key=len)))
    for command, description in usage.items():
        string_to_format = "{:>" + command_len + "}\t{}"
        print(string_to_format.format(command, description))
