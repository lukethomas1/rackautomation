#!/usr/bin/env python3

# File: commands.py
# Author: Luke Thomas
# Date: March 30, 2017
# Description: This file contains functions (commands) to be called by
# racksuite.py. These commands are composed of sequential calls to functions
# in functions.py. Each of these commands accomplishes a "task" from start to
# finish that a user would desire, such as initializing rackspace nodes, or
# configuring a topology.

import functions
import testsuite
import statsuite
import objects
import time

NODE_PREFIX = "node-"
IP_FILE = "./iplists/" + NODE_PREFIX + "hosts"

# Functions are ordered in usage order

# Creates # of nodes necessary for desired topology on rackspace
def initialize():
    # Get user input for which save file to pull down from firebase
    save_file = input("Input Save File Name: ")
    topo_path = "./topologies/" + save_file + "/"

    # Get the save from firebase
    json_string = functions.get_json_from_firebase(save_file)
    subnets, nodes = functions.convert_json_to_object(json_string)

    # Create rackspace instances
    num_instances = len(nodes)
    img = "NewGvpki"
    functions.create_rackspace_instances(num_instances, img, save_file, NODE_PREFIX)
    print("Done.")


def make_iplist():
    # Get user input for which save file to pull down from firebase
    save_file = input("Input Save File Name: ")
    topo_path = "./topologies/" + save_file + "/"

    # Get the save from firebase
    json_string = functions.get_json_from_firebase(save_file)
    subnets, nodes = functions.convert_json_to_object(json_string)

    functions.generate_iplist(len(nodes), NODE_PREFIX)
    functions.edit_ssh_config()


# Creates the configuration files for the desired topology on THIS COMPUTER
# Creates platform xmls, emane_start.sh, emane_stop.sh, scenario.eel
# The files are created in ./topologies/<topology-name>/
def configure():
    # Get user input for which save file to pull down from firebase
    save_file = input("Input Save File Name: ")
    topo_path = "./topologies/" + save_file + "/"

    # Get the save from firebase
    json_string = functions.get_json_from_firebase(save_file)
    subnets, nodes = functions.convert_json_to_object(json_string)

    # Generate and copy files to the local topology folder
    print("Configuring files")
    functions.create_dir(topo_path)
    functions.write_platform_xmls(subnets, nodes, topo_path)
    functions.write_emane_start_stop_scripts(save_file, len(nodes))
    functions.write_scenario(subnets, nodes, topo_path)
    return save_file, len(nodes)


# Runs configure() to create topology locally, 
# then distributes topology to rackspace nodes
def setup():
    # Write configuration files (configure() method) before sending to nodes
    save_file, num_nodes = configure()

    # Get list of ip addresses from rackspace
    iplist = functions.generate_iplist(num_nodes, NODE_PREFIX)
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
def start():
    save_file = input("Input Save File Name: ")
    json_string = functions.get_json_from_firebase(save_file)
    subnets, nodes = functions.convert_json_to_object(json_string)
    iplist = functions.get_iplist(IP_FILE)

    functions.synchronize(IP_FILE)

    print("Starting emane")
    script_file = 'emane_start.sh'
    functions.remote_start_emane(save_file, IP_FILE, script_file)
    time.sleep(2)

    print("Starting GrapeVine")
    functions.remote_start_gvine(iplist)
    print("Done.")


def ping():
    save_file = input("Input Save File Name: ")

    # Get the save from firebase
    json_string = functions.get_json_from_firebase(save_file)
    subnets, nodes = functions.convert_json_to_object(json_string)

    print("Setting up")
    functions.generate_network_ping_list(subnets, nodes, IP_FILE)
    testsuite.ping_network()
    print("Done.")


def test_message():
    save_file = input("Input Save File Name: ")
    message_name = input("Choose message file name: ")
    file_size = input("Choose file size (kilobytes): ")
    iplist = functions.get_iplist(IP_FILE)
    testsuite.message_test_gvine(iplist, message_name, file_size)


def stats():
    save_file = input("Input Save File Name: ")

    # Get the save from firebase
    json_string = functions.get_json_from_firebase(save_file)
    subnets, nodes = functions.convert_json_to_object(json_string)

    # Create dirs, append timestamp in seconds to delay folder
    seconds = statsuite.get_time()
    folder_name = save_file + "_" + str(seconds)
    folder_path = "./stats/delays/"
    functions.create_dir("./stats/")
    functions.create_dir(folder_path)
    functions.create_dir(folder_path + folder_name)

    iplist = functions.get_iplist(IP_FILE)
    path_to_delay = "/home/emane-01/test/emane/gvine/node/delay.txt"
    statsuite.retrieve_delayfiles(iplist, path_to_delay, folder_path + folder_name)
    print("Done.")


# Runs emane_stop.sh on each rackspace node in the topology
def stop():
    save_file = input("Input Save File Name: ")
    script_file = 'emane_stop.sh'
    functions.remote_start_emane(save_file, IP_FILE, script_file)
    functions.remote_stop_gvine(IP_FILE)
    time.sleep(2)
    print("Done.")


# Deletes the topologies/<topology-name>/ folder on each rackspace node
def delete():
    save_file = input("Input Save File Name: ")
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
