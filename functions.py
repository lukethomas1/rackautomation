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


# Assigns each subnet an address that doesnt conflict with other subnets or blacklist
def assign_subnet_addresses(subnets, blacklist):
    taken_addresses = []
    for subnet in subnets:
        subaddr = subnet['addr']
        if(subaddr and subaddr not in taken_addresses and subaddr not in blacklist):
            taken_addresses.append(subaddr)
        else:
            counter = subnet['number']
            while(not subaddr or subaddr in taken_addresses or subaddr in blacklist):
                subaddr = "10.0." + str(counter)
                counter += 1
            subnet['addr'] = subaddr
            taken_addresses.append(subaddr)


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
def create_rackspace_instances(num_instances, image_name, save_file, node_prefix):
    print("Creating " + str(num_instances) + " Rackspace nodes with image '"
        + image_name + "'")
    for index in range(1, num_instances + 1):
        node_name = node_prefix + str(index)
        print("Creating " + node_name);
        # Long command, just a bunch of arguments, see 'rack -h' for more info
        subprocess.Popen(['rack', 'servers', 'instance',
            'create', '--name', node_name, '--image-name',
            image_name, '--flavor-name', '4 GB General Purpose v1',
            '--region', 'DFW', '--keypair', 'mykey', '--networks',
            '00000000-0000-0000-0000-000000000000,3a95350a-676c-4280-9f08-aeea40ffb32b'],
            stdout=subprocess.PIPE)


# Create directory at folder_path
def create_dir(folder_path):
    os.makedirs(folder_path, exist_ok=True)


def delete_gvine_log_files(ip_file):
    command = "cd /home/emane-01/test/emane/gvine/node/ && rm log_*"
    print("Removing log files")
    subprocess.Popen(['pssh', '-h', ip_file, '-l', 'emane-01', '-i', '-P', command],
        stdout=subprocess.DEVNULL)


# Edit this computer's ~/.ssh/config file for each sshing to rackspace nodes
def edit_ssh_config():
    fmt = 'Host {nodename}\nHostName {nodeaddress}\nUser emane-01\nIdentityFile ~/.ssh/id_rsa\n\n'
    file = open("/home/joins/.ssh/config", 'w')

    # Get pairs of node names with ip addresses from rackspace
    process = subprocess.Popen(['rack', 'servers', 'instance', 'list', '--fields',
        'name,publicipv4'], stdout=subprocess.PIPE)
    pairs = process.stdout.read().decode().splitlines()[1:]

    for p in pairs:
        pair = p.split('\t')
        name = pair[0]
        address = pair[1]
        writestring = fmt.format(nodename=name, nodeaddress=address)
        if(len(address) > 0):
            file.write(writestring)
    file.close()


# Run script at script_path, must be shell/bash script
def execute_bash_script(args):
    subprocess.call(args);


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


# Get the ips of the rackspace nodes and write to ip file and ~/.ssh/config
def generate_iplist(num_nodes, sort_term):
    create_dir("./iplists/")

    iplist = get_rack_pair_list()
    sortedlist = sort_iplist(iplist, sort_term)[:num_nodes]

    if(len(sortedlist) == 0):
        print("ERROR NO NODES IN SORTEDLIST from " + str(iplist) + " sort_term: " + sort_term)

    desired_ips = []
    for pair in sortedlist:
        ip = pair.split('\t')[1]
        desired_ips.append(ip)

    create_file_from_list("./iplists/" + sort_term + "hosts", desired_ips)
    return desired_ips


def generate_network_ping_list(subnets, nodes, ip_file):
    ip_process = open(ip_file, 'r')
    ip_list = ip_process.read().splitlines()

    file = open("./tests/pingtest/network", "w")
    for subnet in subnets:
        num_members = len(subnet['memberids'])
        if(num_members > 1):
            for x in range(num_members):
                ip = ip_list[subnet['memberids'][x] - 1]
                file.write(ip)
                for y in range(num_members):
                    if(x != y):
                        to_ip = subnet['addr'] + "." + str(subnet['memberids'][y])
                        file.write(" " + to_ip)
                file.write("\n")
    file.close()


def get_iplist(ip_file):
    ipfile = open(ip_file, 'r')
    iplist_with_newlines = ipfile.readlines()
    ipfile.close()

    iplist = []
    for line in iplist_with_newlines:
        iplist.append(line.strip("\n"))
    return iplist


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


# Get pairs of node names with ip addresses from rackspace
def get_rack_pair_list():
    process = subprocess.Popen(['rack', 'servers', 'instance', 'list', '--fields',
        'name,publicipv4'], stdout=subprocess.PIPE)
    pairs = process.stdout.read().decode().splitlines()[1:]
    return pairs


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
def remote_copy_default_config(save_folder, ip_file):
    os.system("pscp -h " + ip_file + " -l emane-01 ./default_config/* /home/emane-01/GrapeVine/topologies/" + save_folder)
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
        subprocess.Popen(['scp', from_dir, to_dir])
        time.sleep(1)


# Copy scenario.eel to each rackspace node in iplist
def remote_copy_scenario(save_folder, iplist):
    num_instances = len(iplist)
    for node_index in range(0, num_instances):
        node_ip = iplist[node_index]
        from_dir = './topologies/' + save_folder + '/scenario.eel'
        to_dir = 'root@' + node_ip + ':/home/emane-01/GrapeVine/topologies/' + save_folder + "/scenario.eel"
        subprocess.Popen(['scp', from_dir, to_dir])
        time.sleep(1)


# Create topologies directory and topologies/save_name/ on each rackspace node
def remote_create_dirs(save_folder, ip_file):
    # Make GrapeVine directory
    subprocess.Popen(['pssh', '-h', ip_file, '-l', 'emane-01', '-i', '-P',
    'cd ~ && mkdir GrapeVine'], stdout=subprocess.DEVNULL)
    time.sleep(1)

    # Make topologies directory
    subprocess.Popen(['pssh', '-h', ip_file, '-l', 'emane-01', '-i', '-P',
    'cd ~/GrapeVine && mkdir topologies'], stdout=subprocess.DEVNULL)
    time.sleep(1)

    # Make specific topology directory
    subprocess.Popen(['pssh', '-h', ip_file, '-l', 'emane-01', '-i', '-P',
    'cd ~/GrapeVine/topologies && mkdir ' + save_folder]) 
    time.sleep(1)


# Delete specific topology from each rackspace node
def remote_delete_topology(save_folder):
    ip_file = "./iplists/" + save_folder + "hosts"
    subprocess.Popen(['pssh', '-h', ip_file, '-l', 'emane-01', '-i', '-P',
    'rm -r ~/GrapeVine/topologies/' + save_folder])
    time.sleep(2)


# Run file on each rackspace node in ip_file file
def remote_start_emane(save_file, ip_file, script_file):
    save_path = '~/GrapeVine/topologies/' + save_file
    subprocess.Popen(['pssh', '-h', ip_file, '-l', 'emane-01', '-i', '-P',
    'cd ' + save_path + ' && sudo ./' + script_file], stdout=subprocess.DEVNULL)


# Start gvine on each rackspace node
def remote_start_gvine(iplist):
    key = paramiko.RSAKey.from_private_key_file("/home/joins/.ssh/id_rsa")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    for index in range(1, len(iplist) + 1):
        print("Starting on " + str(iplist[index - 1]))
        ssh.connect(iplist[index - 1], username="emane-01", pkey=key)
        command = "cd ~/test/emane/gvine/node/ && java -jar jvine.jar node" + str(index) + " 500 >> log_node" + str(index) + ".txt &"
        stdin, stdout, stderr = ssh.exec_command(command)
        ssh.close()


def remote_start_console(iplist, gvine_dir):
        user = "emane-01"
        terminal = ['gnome-terminal']
        jar = "jvine.jar"
        for i in range(1, len(iplist) + 1):
            path = gvine_dir
            terminal.extend(['--tab', '-e','''ssh -t %s@%s 'cd %s && java -jar %s node%s 250 2>&1|tee log.txt' ''' % (user, iplist[i-1], path, jar, i)])
        subprocess.call(terminal)


def remote_stop_gvine(ip_file):
    subprocess.Popen(['pssh', '-h', ip_file, '-l', 'emane-01', '-i', '-P',
    'sudo pkill java'])


def setup_grapevine(save_file, ip_file):
    command = "if [ ! -d /home/emane-01/test/emane/gvine/node/ ]\n then mkdir -p  /home/emane-01/test/emane/gvine/node\n fi"
    
    print("\nMaking /home/emane-01/test/emane/gvine/node/ directory")
    subprocess.Popen(['pssh', '-h', ip_file, '-l', 'emane-01', '-i', '-P', command ])
    time.sleep(2)

    command = "if [ ! -f /home/emane-01/test/emane/gvine/node/flushrt.sh ]\n then cp /home/emane-01/gvine/trunk/gvine/flushrt.sh /home/emane-01/test/emane/gvine/node/\n fi"
    
    print("\nCopying flushrt.sh")
    subprocess.Popen(['pssh', '-h', ip_file, '-l', 'emane-01', '-i', '-P', command ])
    time.sleep(2)

    command = "if [ ! -f /home/emane-01/test/emane/gvine/node/emane_data.db ]\n then cp /home/emane-01/gvine/trunk/gvine/emane_data.db /home/emane-01/test/emane/gvine/node/\n fi"
    
    print("\nCopying emane_data.db")
    subprocess.Popen(['pssh', '-h', ip_file, '-l', 'emane-01', '-i', '-P', command ])
    time.sleep(2)

    command = "if [ ! -f /home/emane-01/test/emane/gvine/node/ncfilerx.sh ]\n then cp /home/emane-01/gvine/trunk/gvine/ncfilerx.sh /home/emane-01/test/emane/gvine/node/\n fi"
    
    print("\nCopying ncfilerx.sh")
    subprocess.Popen(['pssh', '-h', ip_file, '-l', 'emane-01', '-i', '-P', command ])
    time.sleep(2)

    command = "if [ ! -f /home/emane-01/test/emane/gvine/node/ncfiletx.sh ]\n then cp /home/emane-01/gvine/trunk/gvine/ncfiletx.sh /home/emane-01/test/emane/gvine/node/\n fi"

    print("\nCopying ncfiletx.sh")
    subprocess.Popen(['pssh', '-h', ip_file, '-l', 'emane-01', '-i', '-P', command ])
    time.sleep(2)

    command = "if [ ! -f /home/emane-01/test/emane/gvine/node/gvine.conf.json ]\n then cp /home/emane-01/gvine/trunk/source_gvine/gvine.conf.json /home/emane-01/test/emane/gvine/node/\n fi"

    print("\nCopying gvine.conf.json")
    subprocess.Popen(['pssh', '-h', ip_file, '-l', 'emane-01', '-i', '-P', command ])
    time.sleep(2)

    command = "if [ ! -f /home/emane-01/test/emane/gvine/node/jvine.jar ]\n then cp /home/emane-01/gvine/trunk/source_gvine/jvine.jar /home/emane-01/test/emane/gvine/node/\n fi"

    print("\nCopying jvine.jar")
    subprocess.Popen(['pssh', '-h', ip_file, '-l', 'emane-01', '-i', '-P', command ])
    time.sleep(2)

    command = "if [ ! -f /home/emane-01/test/emane/gvine/node/gvapp.jar ]\n then cp /home/emane-01/gvine/trunk/source_gvine/gvapp.jar /home/emane-01/test/emane/gvine/node/\n fi"

    print("\nCopying gvapp.jar")
    subprocess.Popen(['pssh', '-h', ip_file, '-l', 'emane-01', '-i', '-P', command ])
    time.sleep(2)

    command = "cp /home/emane-01/gvine/trunk/source_gvine/emanelog.jar /home/emane-01/test/emane/gvine/node"

    print("\nCopying emanelog.jar")
    subprocess.Popen(['pssh', '-h', ip_file, '-l', 'emane-01', '-i', '-P', command ])
    time.sleep(2)

    command = "cd /home/emane-01/test/emane/gvine/node/ && rm -r data"

    print("\nRemoving data folder")
    subprocess.Popen(['pssh', '-h', ip_file, '-l', 'emane-01', '-i', '-P', command ])
    time.sleep(2)


# Sort iplist to have node 1 at beginning and the last node at the end
def sort_iplist(iplist, sort_term):
    sortlist = []
    for index in range(1, len(iplist) + 1):
        node_name = sort_term + str(index)
        for string in iplist:
            if(node_name + "\t" in string):
                sortlist.append(string)
    return sortlist


# Synchronize rackspace nodes, necessary for accurate stats gathering
def synchronize(ip_file):
    subprocess.Popen(['pssh', '-h', ip_file, '-l', 'emane-01', '-i', '-P',
        'sudo service ntp stop'], stdout=subprocess.DEVNULL)
    time.sleep(1)
    subprocess.Popen(['pssh', '-h', ip_file, '-l', 'emane-01', '-i', '-P',
        'sudo ntpd -gq'], stdout=subprocess.DEVNULL)
    time.sleep(1)
    subprocess.Popen(['pssh', '-h', ip_file, '-l', 'emane-01', '-i', '-P',
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
def write_platform_xmls(subnets, nodes, topo_path, blacklist):
    # Read templates
    platform_template_file = open("./templates/platform_template.xml", 'r')
    platform_template = platform_template_file.read()
    platform_template_file.close()
    nem_template_file = open("./templates/nem_template.xml", 'r')
    nem_template = nem_template_file.read()
    nem_template_file.close()

    assign_subnet_addresses(subnets, blacklist)

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
