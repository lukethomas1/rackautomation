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
import pickle
import time

# Local Imports
import functions
import testsuite
import statsuite
import objects

NODE_PREFIX = "node"
IP_FILE = "./iplists/" + NODE_PREFIX + "hosts"

# Functions are ordered in usage order

# Gets json from firebase and saves topology data for reuse
def set_topology(save_file):
    json_string = functions.get_json_from_firebase(save_file)
    subnets, nodes = functions.convert_json_to_object(json_string)
    iplist = functions.generate_iplist(len(nodes), NODE_PREFIX)

    data = {
        'save': save_file,
        'json': json_string,
        'subnets': subnets,
        'nodes': nodes,
        'iplist': iplist
    }

    with open('.data.pickle', 'wb') as file:
        pickle.dump(data, file)


def load_data():
    with open('.data.pickle', 'rb') as file:
        data = pickle.load(file)
    return data


def print_data(data):
    print("\nSave Name:\n")
    print(data['save'])
    print("\nJson:\n")
    print(data['json'])
    print("\nSubnets:\n")
    print(data['subnets'])
    print("\nNodes:\n")
    print(data['nodes'])
    print("\nIplist:\n")
    print(data['iplist'])

    
# Creates # of nodes necessary for desired topology on rackspace
def initialize(save_file, num_nodes):
    img = "GvineV352"
    lastimg = "NewGvpki"
    functions.create_rackspace_instances(num_nodes, img, save_file, NODE_PREFIX)
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
    functions.write_platform_xmls(subnets, nodes, topo_path)
    functions.write_emane_start_stop_scripts(save_file, len(nodes))
    functions.write_scenario(subnets, nodes, topo_path)


# Runs configure() to create topology locally, 
# then distributes topology to rackspace nodes
def setup(save_file, subnets, nodes, iplist):
    # Write configuration files (configure() method) before sending to nodes
    configure(save_file, subnets, nodes)

    functions.generate_iplist(len(nodes), NODE_PREFIX)
    functions.edit_ssh_config()
    time.sleep(2)

    # Add all rackspace node ip addresses to this computer's known_hosts file
    functions.add_known_hosts(iplist)

    # Create topology directory on each rackspace node
    print("Creating remote directories with ipfile: " + IP_FILE)
    functions.remote_create_dirs(save_file, IP_FILE)
    time.sleep(2)

    # Copy the default config to each rackspace node
    print("Copying default config")
    functions.remote_copy_default_config(save_file, IP_FILE)
    time.sleep(2)

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
    functions.remote_start_emane(save_file, IP_FILE, script_name)
    time.sleep(2)

    functions.delete_gvine_log_files(IP_FILE)
    print("Starting GrapeVine")
    functions.remote_start_gvine(iplist)
    #functions.remote_start_console(iplist, "/home/emane-01/test/emane/gvine/node")
    print("Done.")


def start_gvine(iplist):
    functions.remote_start_gvine(iplist)


def ping(subnets, nodes):
    print("Setting up")
    functions.generate_network_ping_list(subnets, nodes, IP_FILE)
    testsuite.ping_network()
    print("Done.")


def message(iplist):
    message_name = input("Choose message file name: ")
    file_size = input("Choose file size (kilobytes): ")
    testsuite.send_message(iplist[0], message_name, file_size)


def test_message(iplist):
    message_name = input("Choose message file name: ")
    file_size = input("Choose file size (kilobytes): ")
    testsuite.message_test_gvine(iplist, message_name, file_size)


def stats(save_file, num_nodes, iplist):
    print("Creating stats directories")
    functions.create_dir("./stats/")
    functions.create_dir("./stats/delays")
    functions.create_dir("./stats/emane")
    functions.create_dir("./stats/delays/" + save_file)
    functions.create_dir("./stats/emane/" + save_file)

    print("Retrieving delay files")
    path_to_delay = "/home/emane-01/test/emane/gvine/node/delay.txt"
    statsuite.retrieve_delayfiles(iplist, path_to_delay, "./stats/delays/" + save_file)
    delays = statsuite.parse_delayfiles("./stats/delays/" + save_file, num_nodes)
    statsuite.plot_values(delays, "delay")

    print("\nGenerating EMANE statistics\n")
    statsuite.generate_emane_stats(NODE_PREFIX, save_file, num_nodes, iplist)
    print("\nCopying EMANE statistics to this computer\n")
    statsuite.copy_emane_stats(save_file, num_nodes, iplist)
    print("Done.")


def stats_emane(save_file, num_nodes, iplist):
    print("\nGenerating EMANE statistics\n")
    statsuite.generate_emane_stats(NODE_PREFIX, save_file, num_nodes, iplist)
    print("\nCopying EMANE statistics to this computer\n")
    statsuite.copy_emane_stats(save_file, num_nodes, iplist)
    print("Done.")


def stats_parse(save_file, num_nodes, parse_term):
    phys = statsuite.parse_emane_stats(save_file, num_nodes, parse_term)
    statsuite.sub_plot(phys)
    statsuite.plot_values(phys, "emane")



# Runs emane_stop.sh on each rackspace node in the topology
def stop(save_file):
    script_file = 'emane_stop.sh'
    functions.remote_start_emane(save_file, IP_FILE, script_file)
    functions.remote_stop_gvine(IP_FILE)
    time.sleep(2)
    print("Done.")


# Deletes the topologies/<topology-name>/ folder on each rackspace node
def delete(save_file):
    functions.remote_delete_topology(save_file)


# Kills EVERY rackspace node
def kill():
    functions.kill_all_instances()


def usage():
    usage = ""
    usage += "---------- USAGE ----------\n"
    usage += "python3 racksuite.py <command>\n\n"
    usage += "---------- COMMANDS ----------\n"
    usage += "init\t\t\t create rackspace cloud instances\n"
    usage += "iplist\t\t\t update iplist and pssh-hosts\n"
    usage += "configure\t\t\t write platform files, scenario.eel, emane scripts\n"
    usage += "setup\t\t\t configure command + send to nodes on rackspace\n"
    usage += "start\t\t\t start emane and grapevine\n"
    usage += "ping\t\t\t ping nodes to test if they are connected\n"
    usage += "stats\t\t\t save statistics\n"
    usage += "stop\t\t\t stop emane and grapevine\n"
    usage += "delete\t\t\t delete cloud topology folders\n"
    usage += "kill\t\t\t kill rackspace cloud instances\n"
    usage += "help\t\t\t show this help message"
    print(usage)
