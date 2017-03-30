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
import objects
import time

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
    image_name = "crypto"
    img2 = "Encryptionupdate"
    functions.create_rackspace_instances(num_instances, img2)


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
    functions.create_save_dir(topo_path)
    functions.write_platform_xmls(subnets, nodes, topo_path)
    functions.write_emane_start_stop_scripts(save_file, len(nodes))
    functions.write_scenario(subnets, nodes, topo_path)
    return save_file


# Get the ips of the rackspace nodes and write to pssh-hosts and ~/.ssh/config
def generate_iplist():
    # Remove first entry (the header entry) with [1:]
    iplist = functions.get_rack_ip_list()[1:]
    functions.edit_ssh_config(len(iplist))
    sortedlist = functions.sort_iplist(iplist)
    functions.create_file_from_list("./pssh-hosts", sortedlist)
    return sortedlist


# Runs configure() to create topology locally, 
# then distributes topology to rackspace nodes
def setup():
    # Write configuration files (configure() method) before sending to nodes
    save_file = configure()

    # Get list of ip addresses from rackspace
    iplist = generate_iplist()
    time.sleep(2)

    # Add all rackspace node ip addresses to this computer's known_hosts file
    functions.add_known_hosts(iplist)

    # Create topology directory on each rackspace node
    print("Creating remote directories")
    functions.remote_create_dirs(save_file)
    time.sleep(2)

    # Copy the default config to each rackspace node
    print("Copying default config")
    functions.remote_copy_default_config(save_file)
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


# Synchronizes rackspace nodes (not sure what it does, soroush had it),
# then runs emane_start.sh on each rackspace node in the topology
def start():
    save_file = input("Input Save File Name: ")
    save_path = '~/GrapeVine/topologies/' + save_file
    file = 'emane_start.sh'
    functions.synchronize()
    functions.remote_run_emane(save_path, file)
    #functions.remote_start_gvine()


def stats():
    print("stats command not implemented yet")


# Runs emane_stop.sh on each rackspace node in the topology
def stop():
    save_file = input("Input Save File Name: ")
    save_path = '~/GrapeVine/topologies/' + save_file
    file = 'emane_stop.sh'
    functions.remote_run_emane(save_path, file)


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
    usage += "stats\t\t\t save statistics\n"
    usage += "stop\t\t\t stop emane and grapevine\n"
    usage += "delete\t\t\t delete cloud topology folders\n"
    usage += "kill\t\t\t kill rackspace cloud instances\n"
    usage += "help\t\t\t show this help message"
    print(usage)
