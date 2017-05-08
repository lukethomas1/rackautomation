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
import time
import os

# Local Imports
import functions
import testsuite
import statsuite
import objects
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
    if(not os.path.isfile(".data.pickle")):
        print("No .data.pickle file detected, creating...")
        functions.set_topology(SAVE_FILE, NODE_PREFIX)
        return functions.load_data()

    data = functions.load_data()
    if(functions.check_config(data['config'])):
        print("Config changed, reconfiguring...")
        functions.set_topology(SAVE_FILE, NODE_PREFIX)
        return functions.load_data()
    elif(functions.check_timestamp(data['timestamp'])):
        print("Old config, reconfiguring...")
        functions.set_topology(SAVE_FILE, NODE_PREFIX)
        return functions.load_data()
    elif(len(data['iplist']) == 0):
        print("Iplist empty, attempting to populate")
        functions.set_topology(SAVE_FILE, NODE_PREFIX)
        return functions.load_data()

    # Return data if config.py hasn't been changed
    return data


def reset():
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
def setup(save_file, subnets, nodes):
    # Write configuration files (configure() method) before sending to nodes
    if(not os.path.isdir("./topologies/" + save_file)):
        configure(save_file, subnets, nodes)
    else:
        print(save_file + " already configured")

    print("Generating rackspace nodes ip list")
    iplist = functions.generate_iplist(len(nodes), NODE_PREFIX)
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
    functions.remote_start_emane(save_file, IP_FILE, script_name)
    time.sleep(2)

    functions.delete_gvine_log_files(IP_FILE)
    time.sleep(2)

    print("Starting GrapeVine")
    functions.remote_start_gvine(iplist, JAR_FILE)
    print("Done.")


def start_console(iplist):
    user = "emane-01"
    terminal = ['gnome-terminal']
    jar = "jvine.jar"
    gvine_dir = "~/test/emane/gvine/node"
    functions.remote_start_console(user, terminal, jar, iplist, gvine_dir)


def start_gvine(iplist):
    jar_name = input("Name of jar file(leave blank for jvine.jar): ")
    if(not jar_name):
        jar_name = "jvine.jar"
    functions.remote_start_gvine(iplist, jar_name)


def stop_gvine():
    functions.remote_stop_gvine(IP_FILE)


def ping(subnets, nodes):
    print("Setting up")
    functions.generate_network_ping_list(subnets, nodes, IP_FILE, IP_BLACK_LIST)
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


def stats_delays(save_file, num_nodes):
    delays = statsuite.parse_delayfiles("./stats/delays/" + save_file, num_nodes)
    statsuite.plot_values(delays, "delay")


# Runs emane_stop.sh on each rackspace node in the topology
def stop(save_file):
    script_file = 'emane_stop.sh'
    functions.remote_start_emane(save_file, IP_FILE, script_file)
    functions.remote_stop_gvine(IP_FILE)
    time.sleep(2)
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
    usage = ""
    usage += "---------- USAGE ----------\n"
    usage += "python3 racksuite.py <command>\n\n"
    usage += "---------- COMMANDS ----------\n"
    usage += "topology\t\t set the topology to use\n"
    usage += "init\t\t\t create rackspace cloud instances\n"
    usage += "iplist\t\t\t update iplist and pssh-hosts\n"
    usage += "configure\t\t write platform files, scenario.eel, emane scripts\n"
    usage += "setup\t\t\t configure command + send to nodes on rackspace\n"
    usage += "start\t\t\t start emane and grapevine\n"
    usage += "start_gvine\t\t start only grapevine\n"
    usage += "stop_gvine\t\t stop only grapevine\n"
    usage += "data\t\t\t print data\n"
    usage += "ping\t\t\t ping nodes to test if they are connected\n"
    usage += "message\t\t\t send a message on grapevine\n"
    usage += "testmessage\t\t send a message on grapevine and check if it sent correctly\n"
    usage += "stats\t\t\t save statistics\n"
    usage += "delays\t\t\t save grapevine delay statistics\n"
    usage += "emane_stats\t\t get emane statistics\n"
    usage += "parse\t\t\t parse emane statistics\n"
    usage += "stop\t\t\t stop emane and grapevine\n"
    usage += "clean\t\t\t remove all non .jar files from ~/test/emane/gvine/node/ on nodes\n"
    usage += "delete\t\t\t delete cloud topology folders\n"
    usage += "kill\t\t\t kill rackspace cloud instances\n"
    usage += "help\t\t\t show this help message"
    print(usage)
