#!/usr/bin/env python3

# File: functions.py
# Author: Luke Thomas
# Date: March 30, 2017
# Description: This file contains functions to be called by commands.py, these
# functions do all of the dirty work in terms of raw logic, sshing to things,
# generating files, etc.

import json
import objects
import os
import paramiko
import pyrebase
import shutil
import subprocess
import time

def add_known_hosts(iplist):
    for host in iplist:
        os.system("ssh-keygen -f /home/joins/.ssh/known_hosts -R " + host + " > /dev/null 2>&1")
        time.sleep(1)


def copy_default_config(config_path, destination_path):
    # Get name of all files in default config directory
    config_files = os.listdir(config_path)
    for file_name in config_files:
        full_file_name = os.path.join(config_path, file_name)
        if(os.path.isfile(full_file_name)):
            shutil.copy(full_file_name, destination_path)


# Take in json_string from Firebase and parse into nodes and subnets
def convert_json_to_object(json_string):
    # If the string is empty, return empty lists
    if(not json_string):
        return [],[]

    # Parse the json string that we got from firebase
    load = json.loads(json_string)

    # Initialize subnets and nodes arrays
    subnets = []
    nodes = []

    # Iterate through the parsed JSON object and sort into subnets or nodes
    for index in range(len(load)):
        # Only subnets have the field 'name'
        if('name' in load[0]):
            subnets.append(load.pop(0))
        else:
            nodes.append(load.pop(0))
    return subnets, nodes


# Creates file_path with each element in "contents" on its own line
def create_file_from_list(file_path, contents):
    file = open(file_path, 'w')
    for line in contents:
        file.write(line + "\n")
    file.close()


# Call rackspace API to create num_instances nodes with image_name image
def create_rackspace_instances(num_instances, image_name):
    print("Creating " + str(num_instances) + " Rackspace nodes with image '"
        + image_name + "'")
    for index in range(1, num_instances + 1):
        node_name = 'node-' + str(index)
        print("Creating " + node_name);
        # Long command, just a bunch of arguments, see 'rack -h' for more info
        subprocess.Popen(['rack', 'servers', 'instance',
            'create', '--name', node_name, '--image-name',
            image_name, '--flavor-name', '4 GB General Purpose v1',
            '--region', 'DFW', '--keypair', 'mykey', '--networks',
            '00000000-0000-0000-0000-000000000000,3a95350a-676c-4280-9f08-aeea40ffb32b'], stdout=subprocess.PIPE)


# Create directory at folder_path
def create_save_dir(folder_path):
    os.makedirs(folder_path, exist_ok=True)


# Edit this computer's ~/.ssh/config file for each sshing to rackspace nodes
def edit_ssh_config(num_nodes):
    fmt = 'Host {nodename}\nHostName {nodeaddress}\nUser emane-01\nIdentityFile ~/.ssh/id_rsa\n\n'
    file = open("/home/joins/.ssh/config", 'w')

    # Get pairs of node names with ip addresses from rackspace
    process = subprocess.Popen(['rack', 'servers', 'instance', 'list', '--fields',
        'name,publicipv4'], stdout=subprocess.PIPE)
    pairs = process.stdout.read().decode().splitlines()[1:]

    for index in range(0, num_nodes):
        pair = pairs[index].split('\t')
        name = pair[0]
        address = pair[1]
        writestring = fmt.format(nodename=name, nodeaddress=address)
        file.write(writestring)


# Run script at script_path, must be shell/bash script
def execute_bash_script(script_path):
    subprocess.call(script_path);


# Replace placeholders in xml_string with the configuration details provided
def fill_nem_template(xml_string, nem_id, device_name, subnet_addr, node_addr, ipmask, freq):
    xml_string = xml_string.replace("NEMID", nem_id)
    xml_string = xml_string.replace("DEVICENAME", device_name)
    xml_string = xml_string.replace("SUBNET", subnet_addr)
    xml_string = xml_string.replace("NODE", node_addr)
    xml_string = xml_string.replace("IPMASK", ipmask)
    xml_string = xml_string.replace("FREQ", freq)
    return xml_string


# Insert nem_string into xml_string where "NEMSGOHERE" is located
def fill_platform_template(xml_string, nem_string):
    xml_string = xml_string.replace("NEMSGOHERE", nem_string)
    return xml_string


def generate_network_ping_list(subnets, nodes):
    file = open("network", "w")
    for subnet in subnets:
        num_members = len(subnet['memberids'])
        if(num_members > 1):
            for x in range(num_members):
                ip = subnet['addr'] + "." + str(subnet['memberids'][x])
                file.write(ip)
                for y in range(num_members):
                    if(x != y):
                        to_ip = subnet['addr'] + "." + str(subnet['memberids'][y])
                        file.write(" " + to_ip)
                file.write("\n")
    file.close()


# Get json topology under save name save_file from firebase
def get_json_from_firebase(save_file):
    # Firebase Information, sensitive info if we care about what is on firebase
    config = {
        "apiKey": "AIzaSyBo7i1pJOOyTbMLwOvM4pabOqrGwTEzgCc",
        "authDomain": "gvdb-c4e0c.firebaseapp.com",
        "databaseURL": "https://gvdb-c4e0c.firebaseio.com",
        "storageBucket": "gvdb-c4e0c.appspot.com",
    }

    # Firebase variables
    firebase = pyrebase.initialize_app(config);
    db = firebase.database()
    saves = db.child("saves").get().val()

    # Return the save JSON from firebase
    returnval = "";
    try:
        returnval = saves[save_file]['string']
    except:
        print("Non-existant save file")
    return returnval


# Returns a filled out nem template given the subnet, node, and device_num
# device_num represents how many subnets the node is in
# This method is run once for each subnet that the node is in
def get_nem_config(nem_template, subnet, node, device_num):
    nemid = str((subnet['number']) * 100 + node['number'])
    device_name = "emane" + device_num
    subaddr = subnet['addr']
    if(not subaddr):
        subaddr = "10.0." + str(subnet['number'])
    node_num = str(node['number'])
    mask = "255.255.255.0"
    freq = ".4G"
    return fill_nem_template(nem_template, nemid, device_name, subaddr, node_num, mask, freq)


# Returns a list of ip addresses of rackspace nodes
def get_rack_ip_list():
    process = subprocess.Popen(['rack', 'servers', 'instance', 'list', '--fields',
        'publicipv4'], stdout=subprocess.PIPE)
    output = process.stdout.read().decode().splitlines()
    return output


# Returns a list of names of rackspace nodes
def get_rack_name_list():
  process = subprocess.Popen(['rack', 'servers', 'instance', 'list', '--fields',
    'name'], stdout=subprocess.PIPE)
  output = process.stdout.read().decode().splitlines()[1:]
  return output


# Kill every node on rackspace
def kill_all_instances():
    names = get_rack_name_list()
    for name in names:
        process = subprocess.Popen(['rack', 'servers', 'instance', 'delete',
            '--name', name], stdout=subprocess.PIPE)


# Debugging method, prints node and subnet names
def print_subnets_and_nodes(subnets, nodes):
  print("Subnet Names:")
  for subnet in subnets:
      print(str(subnet['name']))
  print()
  print("Node Names:")
  for node in nodes:
      print(str(node['id']))
  print()


# Copy default config to topology directory
def remote_copy_default_config(save_folder):
    os.system("pscp -h pssh-hosts -l emane-01 ./default_config/* /home/emane-01/GrapeVine/topologies/" + save_folder)
    print("Sleep 5 seconds")
    time.sleep(5)


# Copy emane_start.sh and emane_stop.sh to each rackspace node in iplist
def remote_copy_emane_scripts(save_folder, iplist):
    num_instances = len(iplist)
    for node_index in range(0, num_instances):
        node_ip = iplist[node_index]
        start_dir = './topologies/' + save_folder + '/emane_start.sh'
        stop_dir = './topologies/' + save_folder + '/emane_stop.sh'
        to_dir = 'root@' + node_ip + ':/home/emane-01/GrapeVine/topologies/' + save_folder
        subprocess.Popen(['scp', start_dir, to_dir])
        subprocess.Popen(['scp', stop_dir, to_dir])
        time.sleep(1)
    

# Copy corresponding platform#.xml to corresponding rackspace node in iplist
def remote_copy_platform_xmls(save_folder, iplist):
    num_instances = len(iplist)
    for node_index in range(0, num_instances):
        file_name = 'platform' + str(node_index + 1) + '.xml'
        node_ip = iplist[node_index]
        from_dir = './topologies/' + save_folder + '/' + file_name
        to_dir = 'root@' + node_ip + ':/home/emane-01/GrapeVine/topologies/' + save_folder + "/platform.xml"
        subprocess.Popen(['scp', from_dir, to_dir], stdout=subprocess.PIPE)
        time.sleep(1)


# Copy scenario.eel to each rackspace node in iplist
def remote_copy_scenario(save_folder, iplist):
    num_instances = len(iplist)
    for node_index in range(0, num_instances):
        node_ip = iplist[node_index]
        from_dir = './topologies/' + save_folder + '/scenario.eel'
        to_dir = 'root@' + node_ip + ':/home/emane-01/GrapeVine/topologies/' + save_folder + "/scenario.eel"
        subprocess.Popen(['scp', from_dir, to_dir], stdout=subprocess.PIPE)
        time.sleep(1)


# Create topologies directory and topologies/save_name/ on each rackspace node
def remote_create_dirs(save_folder):
    # Make topologies directory
    subprocess.Popen(['pssh', '-h', 'pssh-hosts', '-l', 'emane-01', '-i', '-P',
    'cd ~/GrapeVine && mkdir topologies'], stdout=subprocess.DEVNULL)

    # Make specific topology directory
    subprocess.Popen(['pssh', '-h', 'pssh-hosts', '-l', 'emane-01', '-i', '-P',
    'cd ~/GrapeVine/topologies && mkdir ' + save_folder], stdout=subprocess.DEVNULL) 


# Delete specific topology from each rackspace node
def remote_delete_topology(save_folder):
    subprocess.Popen(['pssh', '-h', 'pssh-hosts', '-l', 'emane-01', '-i', '-P',
        'rm -r ~/GrapeVine/topologies/' + save_folder], stdout=subprocess.DEVNULL)


# Run file on each rackspace node in pssh-hosts file
def remote_run_emane(save_path, file):
    subprocess.Popen(['pssh', '-h', 'pssh-hosts', '-l', 'emane-01', '-i', '-P',
        'cd ' + save_path + ' && sudo ./' + file], stdout=subprocess.DEVNULL)


# Start gvine on each rackspace node
def remote_start_gvine():
    command = "cd ~/test/emane/gvine/node/ && java -jar jvine.jar $i 500 >> log_node$i.txt"

    key = paramiko.RSAKey.from_private_key_file("/home/joins/.ssh/id_rsa")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('23.253.108.97', username="emane-01", pkey=key)

    stdin, stdout, stderr = ssh.exec_command(command)
    print(stdout.readlines())
    ssh.close()


# Sort iplist to have node 1 at beginning and the last node at the end
def sort_iplist(iplist):
    sortlist = []
    process = subprocess.Popen(['rack', 'servers', 'instance', 'list', '--fields',
        'name'], stdout=subprocess.PIPE)
    output = process.stdout.read().decode().splitlines()[1:]

    for index in range(1, len(iplist) + 1):
        item_index = output.index("node-" + str(index))
        sortlist.append(iplist[item_index])
    return sortlist


# Synchronize rackspace nodes, not sure what it does
def synchronize():
    subprocess.Popen(['pssh', '-h', 'pssh-hosts', '-l', 'emane-01', '-i', '-P',
        'sudo service ntp stop'], stdout=subprocess.DEVNULL)
    time.sleep(1)
    subprocess.Popen(['pssh', '-h', 'pssh-hosts', '-l', 'emane-01', '-i', '-P',
        'sudo ntpd -gq'], stdout=subprocess.DEVNULL)
    time.sleep(1)
    subprocess.Popen(['pssh', '-h', 'pssh-hosts', '-l', 'emane-01', '-i', '-P',
        'sudo service ntp start'], stdout=subprocess.DEVNULL)
    

# Write emane_start.sh and emane_stop.sh on this computer
def write_emane_start_stop_scripts(save_folder, num_instances):
    header = '#!/bin/bash\n'
    fmtstart = './democtl-host start "$@" ' + '"~/GrapeVine/topologies/"' + " " + save_folder + " " + str(num_instances)
    fmtstop = './democtl-host stop "$@" ' + '"~/GrapeVine/topologies/"' + " " + save_folder + " " + str(num_instances)
    topo_path = "./topologies/" + save_folder + "/"

    start = open(topo_path + "emane_start.sh", "w")
    start.write(header)
    start.write(fmtstart)
    start.close()
    
    stop = open(topo_path + "emane_stop.sh", "w")
    stop.write(header)
    stop.write(fmtstop)
    stop.close()

    # Change permission to executable
    subprocess.Popen(["chmod", "+x", topo_path + "emane_start.sh", topo_path + "emane_stop.sh"])


# Write platform.xml for each node, lots of configuration logic involved
def write_platform_xmls(subnets, nodes, topo_path):
    # Read templates
    platform_template_file = open("./templates/platform_template.xml", 'r')
    platform_template = platform_template_file.read()
    platform_template_file.close()
    nem_template_file = open("./templates/nem_template.xml", 'r')
    nem_template = nem_template_file.read()
    nem_template_file.close()

    for node in nodes:
        filled_nem = ""
        device_num = 0
        for subnet in subnets:
            if(node['number'] in subnet['memberids']):
                filled_nem += get_nem_config(nem_template, subnet, node, str(device_num))
                device_num += 1
        filled_platform = fill_platform_template(platform_template, filled_nem)
        file = open(topo_path + "platform" + str(node['number']) + ".xml", 'w')
        file.write(filled_platform)
        file.close()


# Write scenario.eel, currently sets pathloss from each node to all the others
def write_scenario(subnets, nodes, topo_path):
    scenario_file = open(topo_path + "scenario.eel", 'w')
    for subnet in subnets:
        num_members = len(subnet['memberids'])
        if(num_members > 1):
            for x in range(num_members):
                nemid = str(subnet['number'] * 100 + subnet['memberids'][x])
                scenario_file.write("0.0 nem:" + str(nemid) + " pathloss")
                for y in range(num_members):
                    if(x != y):
                        to_nemid = str(subnet['number'] * 100 + subnet['memberids'][y])
                        pathloss_value = 89
                        scenario_file.write(" nem:" + str(to_nemid) + "," + str(pathloss_value))
                scenario_file.write("\n")
    scenario_file.close()
