#!/usr/bin/env python3

# File: functions.py
# Author: Luke Thomas
# Date: March 30, 2017
# Description: This file contains functions to be called by commands.py, these
# functions do all of the dirty work in terms of raw logic, sshing to things,
# generating files, etc.

# System Imports
from json import loads
from math import asin, cos, sqrt
from os import listdir, makedirs, path, system
from shutil import copy
from subprocess import call, Popen, PIPE, DEVNULL
from time import sleep, time
from re import compile, match, split, sub
from glob import glob
import threading

# Third Party Imports
from paramiko import AutoAddPolicy, RSAKey, SSHClient
from pickle import load, dump
from pyrebase import initialize_app

# Local Imports
import config

SUCCESS = '\033[92m'
FAIL = '\033[91m'
ENDCOLOR = '\033[0m'

##### LOCAL DATA PERSISTENCE #####

def check_config(old_config):
    new_config_file = open("config.py", 'r')
    new_config = new_config_file.read()
    new_config_file.close()

    if(old_config != new_config):
        print("Config.py changed")
        return True
    return False


def check_rack_nodes(old_rack_nodes):
    racknodes = Popen(['rack', 'servers', 'instance', 'list', '--fields',
        'name,publicipv4'], stdout=PIPE).stdout.read().decode()
    if(old_rack_nodes != racknodes):
        print("Detected different nodes")
        return True
    return False


def check_timestamp(old_timestamp):
    new_timestamp = time()
    if(new_timestamp - 86400 > old_timestamp):
        print("Config is over a day old")
        return True
    return False


def load_data():
    with open('.data.pickle', 'rb') as file:
        data = load(file)
    return data


# Gets json from firebase and saves topology data for reuse
def set_topology(save_file, node_prefix):
    json_string = get_json_from_firebase(save_file)
    subnets, nodes = convert_json_to_object(json_string)
    iplist = generate_iplist(len(nodes), node_prefix)
    ipdict = generate_ipdict()
    timestamp = time()
    racknodes = Popen(['rack', 'servers', 'instance', 'list', '--fields',
        'name,publicipv4'], stdout=PIPE).stdout.read().decode()

    with open("config.py", "r") as config_file:
        config_contents = config_file.read()

    data = {
        'save': save_file,
        'json': json_string,
        'subnets': subnets,
        'nodes': nodes,
        'iplist': iplist,
        'nodeipdict': ipdict,
        'config': config_contents,
        'timestamp': timestamp,
        'racknodes': racknodes
    }

    with open('.data.pickle', 'wb') as file:
        dump(data, file)


def update_pickle(file_name, key, value):
    with open(file_name, "rb") as file:
        data = load(file)
    data[key] = value
    with open(file_name, "wb") as file:
        dump(data, file)

##### TOPOLOGY CONFIGURATION #####

def add_known_hosts(iplist):
    for host in iplist:
        loc = path.expanduser("~/.ssh/known_hosts")
        command = "ssh-keygen -R " + host
        call(command, shell=True, stdout=DEVNULL)
        command = "ssh-keyscan -H " + host + " >> " + loc
        call(command, shell=True, stdout=DEVNULL)
        sleep(1)


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
                subaddr = "11.0." + str(counter)
                counter += 1
            subnet['addr'] = subaddr
            taken_addresses.append(subaddr)


def choose_timestamp_path(paths, index=-1):
    paths.sort()
    paths.reverse()
    num = str(len(paths) - 1)

    if(index < 0):
        user_input = input("Choose path (0 newest, " + num + " oldest) : ")
        index = int(user_input)
    chosen_path = sub(r"[\\]", '', paths[index])
    return chosen_path


def choose_alphabetic_path(paths, index=-1):
    paths.sort()
    num = str(len(paths) - 1)

    if(index < 0):
        user_input = input("Choose path (alphabetic a-z 0-" + num + ") : ")
        index = int(user_input)
    chosen_path = sub(r"[\\]", '', paths[index])
    return chosen_path


def clean_node_data(ip_file, user_name):
    command = (
        "cd ~/test/emane/gvine/node/ && rm -rf gvine.msg* gvine.frag* " +
        "gvine.sub* delay.txt ack.txt *.cer SeqNbr.txt send.txt received.txt " +
        "statistic.db log* eventlogs/* dbs/* data/*"
    )
    print("Cleaning data on nodes")
    Popen(['parallel-ssh', '-h', ip_file, '-l', user_name, '-i', '-P', command], stdout=DEVNULL)
    sleep(1)


def clean_more(ip_file, user_name):
    command = (
        "cd ~/test/emane/gvine/node/ && rm -rf $(ls -I '*.jar' -I '*.json' -I '*.cer' -I '*pki.db*')"
    )
    print("Deleting all non .jar, .json files from nodes")
    Popen(['parallel-ssh', '-h', ip_file, '-l', user_name, '-i', '-P', command])
    sleep(1)


def clean_nodes(ip_file, user_name):
    command = "cd ~/test/emane/gvine/node/ && rm -rf $(ls -I '*.jar' -I '*.json')"
    print("Deleting all non .jar, .json files from nodes")
    Popen(['parallel-ssh', '-h', ip_file, '-l', user_name, '-i', '-P', command])
    sleep(1)


def copy_default_config(config_path, destination_path):
    # Get name of all files in default config directory
    config_files = listdir(config_path)
    for file_name in config_files:
        full_file_name = path.join(config_path, file_name)
        if(path.isfile(full_file_name)):
            shutil.copy(full_file_name, destination_path)


# Take in json_string from Firebase and parse into nodes and subnets
def convert_json_to_object(json_string):
    # If the string is empty, return empty lists
    if(not json_string):
        return [],[]

    # Parse the json string that we got from firebase
    load = loads(json_string)

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
    file.close() #/PUB


# Call rackspace API to create num_instances nodes with image_name image
def create_rackspace_instances(num_instances, image_name, ssh_key, save_file, node_prefix):
    node_status_list = get_rack_status_list()
    print(str(node_status_list))
    node_list = [pair[0] for pair in node_status_list]
    print("Creating " + str(num_instances) + " Rackspace nodes with image '"
        + image_name + "', ssh_key '" + ssh_key + "', and save file '" + save_file + "'")
    instances_made = 0
    index = 1
    while instances_made < num_instances:
        node_name = node_prefix + str(index)
        if node_name not in node_list:
            instances_made += 1
            print("Creating " + node_name)
            # Long command, just a bunch of arguments, see 'rack -h' for more info
            Popen(['rack', 'servers', 'instance',
                'create', '--name', node_name, '--image-name',
                image_name, '--flavor-name', '4 GB General Purpose v1',
                '--region', 'DFW', '--keypair', ssh_key, '--networks',
                '00000000-0000-0000-0000-000000000000,3a95350a-676c-4280-9f08-aeea40ffb32b'],
                stdout=PIPE)
        else:
            print(node_name + " already exists!")
        index += 1


# Create directory at folder_path
def create_dir(folder_path):
    makedirs(folder_path, exist_ok=True)


def delete_gvine_log_files(ip_file, user_name):
    dir_path = path.expanduser("~/gvinetest/")
    command = "cd " + dir_path + " && rm log_*"
    Popen(['parallel-ssh', '-h', ip_file, '-l', user_name, '-i', '-P', command],
        stdout=DEVNULL)


# Edit this computer's ~/.ssh/config file for each sshing to rackspace nodes
def edit_ssh_config():
    fmt = 'Host {nodename}\n\tHostName {nodeaddress}\n\tUser emane-01\n\tStrictHostKeyChecking no\n\tIdentityFile ~/.ssh/id_rsa\n\n'
    local_config = path.expanduser("~/.ssh/config")
    file = open(local_config, 'w')

    # Get pairs of node names with ip addresses from rackspace
    process = Popen(['rack', 'servers', 'instance', 'list', '--fields',
        'name,publicipv4'], stdout=PIPE)
    pairs = process.stdout.read().decode().splitlines()[1:]

    for p in pairs:
        pair = p.split('\t')
        name = pair[0]
        address = pair[-1]
        writestring = fmt.format(nodename=name, nodeaddress=address)
        if(len(address) > 0):
            file.write(writestring)
    file.close()


# Run script at script_path, must be shell/bash script
def execute_shell(command):
    system(command)


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

    desired_ips = []
    for pair in sortedlist:
        ip = pair.split('\t')[-1]
        desired_ips.append(ip)

    create_file_from_list("./iplists/" + sort_term + "hosts", desired_ips)
    return desired_ips


def generate_ipdict():
    ipdict = {}
    pairlist = get_rack_pair_list()
    for pair in pairlist:
        splitted = pair.split("\t")
        node_name = splitted[0]
        ip = splitted[-1]
        ipdict[node_name] = ip
    return ipdict


def generate_rack_to_topo_dict(iplist, ipdict, nodes):
    dict = {}
    for index in range(len(iplist)):
        ip = iplist[index]
        node = nodes[index]
        rack_name = ipdict[ip]
        dict[rack_name] = node['label']
    return dict


def invert_dict(curr_dict):
    inv_dict = {ip: node_name for node_name, ip in curr_dict.items()}
    return inv_dict


def generate_network_ping_list(subnets, ip_file, blacklist):
    ip_process = open(ip_file, 'r')
    ip_list = ip_process.read().splitlines()

    assign_subnet_addresses(subnets, blacklist)

    create_dir("./tests/")
    create_dir("./tests/pingtest/")
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
    saves = get_all_saves()

    # Return the save JSON from firebase
    returnval = ""
    try:
        returnval = saves[save_file]['string']
    except:
        print("Non-existant save file")
    return returnval


def get_all_saves():
    # Firebase Information, sensitive info if we care about what is on firebase
    config = {
        "apiKey": "AIzaSyBo7i1pJOOyTbMLwOvM4pabOqrGwTEzgCc",
        "authDomain": "gvdb-c4e0c.firebaseapp.com",
        "databaseURL": "https://gvdb-c4e0c.firebaseio.com",
        "storageBucket": "gvdb-c4e0c.appspot.com",
    }

    # Firebase variables
    firebase = initialize_app(config)
    db = firebase.database()
    saves = db.child("saves").get().val()
    return saves


# Returns a filled out nem template given the subnet, node, and device_num
# device_num represents how many subnets the node is in
# This method is run once for each subnet that the node is in
def get_nem_config(nem_template, subnet, node, device_num):
    nemid = str((subnet['number']) * 100 + node['number'])
    device_name = "emane" + device_num
    subaddr = subnet['addr']
    if(not subaddr):
        subaddr = config.SUBNET_GROUP + str(subnet['number'])
    node_num = str(node['number'])
    mask = "255.255.255.0"
    freq = ".4G"
    return fill_nem_template(nem_template, nemid, device_name, subaddr, node_num, mask, freq)


# Returns a list of ip addresses of rackspace nodes
def get_rack_ip_list():
    process = Popen(['rack', 'servers', 'instance', 'list', '--fields',
        'publicipv4'], stdout=PIPE)
    output = process.stdout.read().decode().splitlines()
    return output


# Returns a list of names of rackspace nodes
def get_rack_name_list():
    process = Popen(['rack', 'servers', 'instance', 'list', '--fields',
      'name'], stdout=PIPE)
    output = process.stdout.read().decode().splitlines()[1:]
    return output


# Get pairs of node names with ip addresses from rackspace
def get_rack_pair_list():
    process = Popen(['rack', 'servers', 'instance', 'list', '--fields',
        'name,publicipv4'], stdout=PIPE)
    pairs = process.stdout.read().decode().splitlines()[1:]
    return pairs


# Kill every node on rackspace
def kill_all_instances():
    names = get_rack_name_list()
    for name in names:
        process = Popen(['rack', 'servers', 'instance', 'delete',
            '--name', name], stdout=PIPE)


def parallel_ssh(ip_file, command, user_name):
    Popen(['parallel-ssh', '-h', ip_file, '-l', user_name, '-i', '-P', command], stdout=DEVNULL)


def push_file(ip_file, src_path, dest_path):
    print("Pushing file " + src_path + " to " + dest_path)
    command = (
        "parallel-scp -h " + ip_file + " -l emane-01 " + src_path + " " + dest_path
    )
    call(command, shell=True, stdout=DEVNULL)


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
def remote_copy_default_config(save_folder, ip_file, user_name):
    command = (
        "parallel-scp -h " + ip_file + " -l " + user_name + " ./default_config/* " +
        "/home/emane-01/GrapeVine/topologies/" + save_folder
    )
    call(command, shell=True, stdout=DEVNULL)
    print("Sleep 5 seconds")
    sleep(5)


# Copy emane_start.sh and emane_stop.sh to each rackspace node in iplist
def remote_copy_emane_scripts(save_folder, iplist):
    num_instances = len(iplist)
    for node_index in range(0, num_instances):
        node_ip = iplist[node_index]
        start_dir = './topologies/' + save_folder + '/emane_start.sh'
        stop_dir = './topologies/' + save_folder + '/emane_stop.sh'
        to_dir = 'emane-01@' + node_ip + ':/home/emane-01/GrapeVine/topologies/' + save_folder
        Popen(['scp', start_dir, to_dir])
        Popen(['scp', stop_dir, to_dir])
        sleep(1)
    

# Copy corresponding platform#.xml to corresponding rackspace node in iplist
def remote_copy_platform_xmls(save_folder, iplist):
    num_instances = len(iplist)
    for node_index in range(0, num_instances):
        file_name = 'platform' + str(node_index + 1) + '.xml'
        node_ip = iplist[node_index]
        from_dir = './topologies/' + save_folder + '/' + file_name
        to_dir = 'emane-01@' + node_ip + ':/home/emane-01/GrapeVine/topologies/' + save_folder + "/platform.xml"
        Popen(['scp', from_dir, to_dir])
        sleep(1)


# Copy scenario.eel to each rackspace node in iplist
def remote_copy_scenario(save_folder, iplist):
    num_instances = len(iplist)
    for node_index in range(0, num_instances):
        node_ip = iplist[node_index]
        from_dir = './topologies/' + save_folder + '/scenario.eel'
        to_dir = 'emane-01@' + node_ip + ':/home/emane-01/GrapeVine/topologies/' + save_folder + "/scenario.eel"
        Popen(['scp', from_dir, to_dir])
        sleep(1)


# Create topologies directory and topologies/save_name/ on each rackspace node
def remote_create_dirs(save_folder, ip_file, user_name):
    # Make GrapeVine directory
    Popen(['parallel-ssh', '-h', ip_file, '-l', user_name, '-i', '-P',
    'cd ~ && mkdir GrapeVine'], stdout=DEVNULL)
    sleep(1)

    # Make topologies directory
    Popen(['parallel-ssh', '-h', ip_file, '-l', user_name, '-i', '-P',
    'cd ~/GrapeVine && mkdir topologies'], stdout=DEVNULL)
    sleep(1)

    # Make specific topology directory
    Popen(['parallel-ssh', '-h', ip_file, '-l', user_name, '-i', '-P',
    'cd ~/GrapeVine/topologies && mkdir ' + save_folder]) 
    sleep(1)

    # Make norm output/input "outbox" directory
    Popen(['parallel-ssh', '-h', ip_file, '-l', user_name, '-i', '-P',
    'cd ~/norm/bin/ && mkdir outbox'], stdout=DEVNULL)
    sleep(1)


def remote_delete_events(ip_file, user_name):
    Popen(['parallel-ssh', '-h', ip_file, '-l', user_name, '-i', '-P',
    'rm ~/test/emane/gvine/node/dbs/*'], stdout=DEVNULL)
    sleep(2)

    
# Delete specific topology from each rackspace node
def remote_delete_topology(node_prefix, save_folder):
    ip_file = "./iplists/" + node_prefix + "hosts"
    Popen(['parallel-ssh', '-h', ip_file, '-l', 'emane-01', '-i', '-P',
    'rm -r ~/GrapeVine/topologies/' + save_folder])
    sleep(2)


# Run file on each rackspace node in ip_file file
def remote_emane(save_file, ip_file, script_file):
    save_path = '~/GrapeVine/topologies/' + save_file
    Popen(['parallel-ssh', '-h', ip_file, '-l', 'emane-01', '-i', '-P',
    'cd ' + save_path + ' && sudo ./' + script_file], stdout=DEVNULL)


# Start gvine on each rackspace node
def remote_start_gvine(iplist, jar_name, user_name):
    loc = path.expanduser("~/.ssh/id_rsa")
    key = RSAKey.from_private_key_file(loc)
    ssh = SSHClient()
    ssh.set_missing_host_key_policy(AutoAddPolicy())

    for index in range(1, len(iplist) + 1):
        print("Starting on " + str(iplist[index - 1]))
        try:
            ssh.connect(iplist[index - 1], username=user_name, pkey=key)
        except:
            print("Failed to connect to " + str(iplist[index - 1]))
            continue
        command = "cd ~/test/ && java -jar " + jar_name + " node" + str(index) + " 500 >> log_node" + str(index) + ".txt &"
        stdin, stdout, stderr = ssh.exec_command(command)
        ssh.close()


def remote_start_console(user, terminal, jar, iplist, gvine_dir):
        for i in range(1, len(iplist) + 1):
            path = gvine_dir
            terminal.extend(['--tab', '-e','''ssh -t %s@%s 'cd %s && java -jar %s node%s 250 2>&1|tee log.txt' ''' % (user, iplist[i-1], path, jar, i)])
        call(terminal)


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
def synchronize(node_objects):
    for node in node_objects:
        remote_execute("sudo service ntp stop", node.ip, node.user_name)
    sleep(2)
    for node in node_objects:
        remote_execute("sudo ntpd -gq", node.ip, node.user_name)
    sleep(2)
    for node in node_objects:
        remote_execute("sudo service ntp start", node.ip, node.user_name)


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
    Popen(["chmod", "+x", topo_path + "emane_start.sh", topo_path + "emane_stop.sh"])


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
        device_num = 1
        for subnet in subnets:
            if(node['number'] in subnet['memberids']):
                filled_nem += get_nem_config(nem_template, subnet, node, str(device_num))
                device_num += 1
        filled_platform = fill_platform_template(platform_template, filled_nem)
        file = open(topo_path + "platform" + str(node['number']) + ".xml", 'w')
        file.write(filled_platform)
        file.close()

##### EMANE SCENARIOS #####

# Write scenario.eel, currently sets pathloss from each node to all the others
def write_scenario(subnets, nodes, topo_path, pathloss_value):
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
                        scenario_file.write(" nem:" + str(to_nemid) + "," + str(pathloss_value))
                scenario_file.write("\n")
    scenario_file.close()


def coord_distance(lat1, lon1, lat2, lon2):
    KM_PER_MILE = 1.60934
    p = 0.017453292519943295     #Pi/180
    a = (0.5 - cos((lat2 - lat1) * p)/2 +
            cos(lat1 * p) * cos(lat2 * p) * (1 - cos((lon2 - lon1) * p)) / 2)
    return 12742 * asin(sqrt(a)) * KM_PER_MILE #2*R*asin...

##### NORM CONFIGURATION #####

def start_norm(iplist, subnets, nodes, send_bps, receive_bps):
    send_commands = get_norm_send_commands(iplist, subnets, nodes, send_bps)
    receive_commands = get_norm_receive_commands(iplist, subnets, nodes, receive_bps)
    loc = path.expanduser("~/.ssh/id_rsa")
    key = RSAKey.from_private_key_file(loc)
    ssh = SSHClient()
    ssh.set_missing_host_key_policy(AutoAddPolicy())

    for index in range(1, len(iplist) + 1):
        node_name = "node" + str(index)
        print("Starting norm protocol on " + node_name)
        ssh.connect(iplist[index - 1], username="emane-01", pkey=key)
        if(node_name in send_commands.keys()):
            for send_command in send_commands[node_name]:
                command = "cd ~/norm/bin/ && " + send_command
                stdin, stdout, stderr = ssh.exec_command(command)
        for receive_command in receive_commands[node_name]:
            command = "cd ~/norm/bin/ && " + str(receive_command)
            stdin, stdout, stderr = ssh.exec_command(command)
        ssh.close()


def get_norm_receive_commands(iplist, subnets, nodes, receive_bps):
    RECEIVE_COMMAND = "./norm addr 239.255.255.0/{0!s} interface {1} rxcachedir ./outbox trace on log rxlog.txt &"
    commands = {}
    for index in range(0, len(nodes)):
        node = nodes[index]
        node_name = 'node' + str(node['number'])
        commands[node_name] = []
        num_subnets = -1
        for ind in range(0, len(subnets)):
            subnet = subnets[ind]
            if(node['number'] in subnet['memberids']):
                num_subnets += 1
                for member_num in subnet['memberids']:
                    if(member_num != node['number']):
                        receive_port = 10000 + 1000 * subnet['number'] + member_num
                        interface_name = "emane" + str(num_subnets)
                        bits_per_second = receive_bps
                        receive = RECEIVE_COMMAND.format(receive_port, interface_name)
                        commands[node_name].append(receive)
    return commands


def get_norm_send_commands(iplist, subnets, nodes, send_bps):
    SEND_COMMAND = "./norm addr 239.255.255.0/{0!s} interface {1} rate {2!s} sendfile ./outbox " \
                   "repeat -1 updatesOnly trace on log txlog.txt &"
    commands = {}
    #for index in range(0, len(nodes)):
    for index in range(0, 1):
        node = nodes[index]
        node_name = 'node' + str(node['number'])
        commands[node_name] = []
        num_subnets = 0
        for ind in range(0, len(subnets)):
            subnet = subnets[ind]
            if(node['number'] in subnet['memberids']):
                send_port = 10000 + 1000 * subnet['number'] + node['number']
                interface_name = "emane" + str(num_subnets)
                num_subnets += 1
                bits_per_second = send_bps # 8 bits in a byte, 8000 is 1KB/s, 800,000 is 100KB/s
                send = SEND_COMMAND.format(send_port, interface_name, bits_per_second)
                commands[node_name].append(send)
    return commands


def clean_norm(iplist):
    loc = path.expanduser("~/.ssh/id_rsa")
    key = RSAKey.from_private_key_file(loc)
    ssh = SSHClient()
    ssh.set_missing_host_key_policy(AutoAddPolicy())

    for ip in iplist:
        ssh.connect(ip, username="emane-01", pkey=key)
        clean_outbox = "cd ~/norm/bin/outbox && rm *"
        ssh.exec_command(clean_outbox)
        clean_logs = "cd ~/norm/bin && rm *log*"
        ssh.exec_command(clean_logs)
        ssh.close()


def get_norm_delays(file_name, iplist):
    loc = path.expanduser("~/.ssh/id_rsa")
    key = RSAKey.from_private_key_file(loc)
    ssh = SSHClient()
    ssh.set_missing_host_key_policy(AutoAddPolicy())

    delays = []
    for ip in iplist:
        ssh.connect(ip, username="emane-01", pkey=key)
        command = "cd ~/norm/bin/outbox && stat -c%Y " + file_name
        stdin, stdout, stderr = ssh.exec_command(command)
        delays.append(stdout.read().decode().splitlines()[0])
        ssh.close()
    return delays


##### RACKSPACE API INTERACTION #####

def get_rack_status_list():
    racknodes = Popen(['rack', 'servers', 'instance', 'list', '--fields',
        'name,status'], stdout=PIPE).stdout.read().decode()
    returnArr = []
    for line in racknodes.splitlines()[1:]:
        splitted = line.split("\t")
        this_node = [splitted[0], splitted[-1]]
        returnArr.append(this_node)
    return returnArr


def are_nodes_ready(node_prefix, num_nodes, rack_status_list):
    pattern = compile("^" + node_prefix + "[0-9]+$")
    rack_list = [node for node in rack_status_list if pattern.match(node[0])]
    if(len(rack_list) < num_nodes):
        return False
    rack_list = natural_sort_tuple(rack_list, 0)
    all_are_ready = True
    for node_index in range(1, num_nodes + 1):
        node_name = node_prefix + str(node_index)
        node_name = rack_list[node_index - 1][0]
        if(not rack_list[node_index - 1][1] == "ACTIVE"):
            print(node_name + " is not ready")
            all_are_ready = False
    return all_are_ready


# Sort strings based on the numbers inside them, look up "natural sorting"
def natural_sort_tuple(list, sort_index):
    convert = lambda text: int(text) if text.isdigit() else text.lower() 
    alphanum_key = lambda key: [ convert(c) for c in split('([0-9]+)', key[sort_index]) ] 
    return sorted(list, key = alphanum_key)


def wait_until_nodes_ready(node_prefix, num_nodes, fail_time):
    sleep_time = 10
    failsafe = 0
    status_list = get_rack_status_list()
    ready = are_nodes_ready(node_prefix, num_nodes, status_list)
    while(not ready and failsafe < fail_time):
        failsafe += sleep_time
        sleep(sleep_time)
        status_list = get_rack_status_list()
        ready = are_nodes_ready(node_prefix, num_nodes, status_list)
    if(failsafe < fail_time):
        return True
    return False

##### GRAPEVINE GVPKI CERTS #####

# Use paramiko to generate the cert on each node
def generate_certs(iplist, path_to_jar):
    loc = path.expanduser("~/.ssh/id_rsa")
    key = RSAKey.from_private_key_file(loc)
    ssh = SSHClient()
    ssh.set_missing_host_key_policy(AutoAddPolicy())

    for index in range(1, len(iplist) + 1):
        ssh.connect(iplist[index - 1], username="emane-01", pkey=key)
        command = "cd " + path_to_jar + " && java -jar gvpki.jar generate node" + str(index)
        stdin, stdout, stderr = ssh.exec_command(command)
        ssh.close()

# Use scp to get the cert from each node
def pull_certs(iplist):
    create_dir("./keystore/")
    command = "cd ./keystore/ && rm *.cer"
    call(command, shell=True, stdout=DEVNULL)
    for index in range(1, len(iplist) + 1):
        ip = iplist[index - 1]
        from_path = "emane-01@" + ip + ":~/test/emane/gvine/node/node" + str(index) + ".cer"
        to_path = "./keystore/"
        Popen(['scp', from_path, to_path])
    

# Use parallel-scp to push certs in parallel
def push_certs(ip_file, path_to_certs, path_to_push):
    command = "parallel-scp -h " + ip_file + " -l emane-01 " + path_to_certs + " " + path_to_push
    #call(command, shell=True, stdout=DEVNULL)
    call(command, shell=True)


def load_certs(path_to_jar, iplist):
    loc = path.expanduser("~/.ssh/id_rsa")
    key = RSAKey.from_private_key_file(loc)
    ssh = SSHClient()
    ssh.set_missing_host_key_policy(AutoAddPolicy())

    for index in range(1, len(iplist) + 1):
        ssh.connect(iplist[index - 1], username="emane-01", pkey=key)
        command = (
            "cd {} && for((i=1; i<=7; i=i+1)); do java -jar gvpki.jar " +
            "node node{} load node$i; done"
        ).format(path_to_jar, index)
        stdin, stdout, stderr = ssh.exec_command(command)
        ssh.close()

##### PARAMETERS FOR AUTOTEST #####

def push_gvine_conf(ip_file, path_to_conf):
    command = (
        "parallel-scp -h " + ip_file + " -l emane-01 " + path_to_conf +
        " /home/emane-01/test/emane/gvine/node/"
    )
    call(command, shell=True, stdout=DEVNULL)


def change_gvine_tx_rate(tx_rate, path_to_conf):
    lines = []
    # Read file
    with open(path_to_conf, 'r') as file:
        lines = file.readlines()
    # Change tx rate
    for index in range(len(lines)):
        if("TargetTxRateBps" in lines[index]):
            reg = "(?<=    \"TargetTxRateBps\": ).*?(?=,)"
            r = compile(reg)
            lines[index] = r.sub(str(tx_rate), lines[index])
    # Write to file
    with open(path_to_conf, 'w') as file:
        file.writelines(lines)


def change_gvine_frag_size(frag_size, path_to_conf):
    lines = []
    # Read file
    with open(path_to_conf, 'r') as file:
        lines = file.readlines()
    # Change tx rate
    for index in range(len(lines)):
        if("FragmentSize" in lines[index]):
            goal = "    \"FragmentSize\": " + str(frag_size) + ","
            if(lines[index] == goal):
                return True
            reg = "(?<=    \"FragmentSize\": ).*?(?=,)"
            r = compile(reg)
            lines[index] = r.sub(str(frag_size), lines[index])
    # Write to file
    with open(path_to_conf, 'w') as file:
        file.writelines(lines)


def generate_error_rate_commands(subnets, nodes):
    template = (
        "sudo iptables {{action}} INPUT -i {interface} -m statistic --mode random --probability {{"
        "rate}} -j DROP"
    )
    # Determine the interfaces each node uses
    interfaces_dict = {}
    for subnet in subnets:
        for member in subnet['memberids']:
            if(member not in interfaces_dict.keys()):
                interfaces_dict[member] = []
            interfaces = interfaces_dict[member]
            interfaces_dict[member].append("emane" + str(len(interfaces)))

    # Format the template for each interface the node is in
    commands_dict = {}
    for node_index in range(1, len(nodes) + 1):
        commands_dict[node_index] = []
        for iface in interfaces_dict[node_index]:
            commands_dict[node_index].append(template.format(interface=iface))
    return commands_dict


def remote_set_error_rate(ip, error_rate, command_template):
    command = command_template.format(action="-A", rate=str(error_rate))
    remote_execute(command, ip, "emane-01", False, False)


def remote_remove_error_rate(ip, error_rate, command_template):
    command = command_template.format(action="-D", rate=str(error_rate))
    remote_execute(command, ip, "emane-01", False, False)


def remote_execute(command, ip, remote_username, print_stdout=False, print_stderr=False):
    loc = path.expanduser("~/.ssh/id_rsa")
    key = RSAKey.from_private_key_file(loc)
    ssh = SSHClient()
    ssh.set_missing_host_key_policy(AutoAddPolicy())
    ssh.connect(ip, username=remote_username, pkey=key)
    stdin, stdout, stderr = ssh.exec_command(command)
    if(print_stdout):
        print(stdout.read().decode())
    if(print_stderr):
        print(stderr.read().decode())
    exit_status = stdout.channel.recv_exit_status()
    ssh.close()
    return exit_status


def remote_execute_stdout(command, ip, username):
    loc = path.expanduser("~/.ssh/id_rsa")
    key = RSAKey.from_private_key_file(loc)
    ssh = SSHClient()
    ssh.set_missing_host_key_policy(AutoAddPolicy())
    ssh.connect(ip, username=username, pkey=key)
    stdin, stdout, stderr = ssh.exec_command(command)
    stdout_decoded = stdout.read().decode()
    ssh.close()
    return stdout_decoded


def remote_execute_commands(commands, ip, remote_username, print_stdout=False, print_stderr=False,
                            print_exit=False):
    loc = path.expanduser("~/.ssh/id_rsa")
    key = RSAKey.from_private_key_file(loc)
    ssh = SSHClient()
    ssh.set_missing_host_key_policy(AutoAddPolicy())
    ssh.connect(ip, username=remote_username, pkey=key)
    for command in commands:
        stdin, stdout, stderr = ssh.exec_command(command)
        if(print_stdout):
            print(stdout.read().decode())
        if(print_stderr):
            print(stderr.read().decode())
        if(print_exit):
            print(stdout.channel.recv_exit_status())
    ssh.close()

##### MESSAGE SEND TIME ESTIMATION #####

# Returns a dictionary of dictionaries
# hops_dict[sender_node]: [receiver_node] : num_hops
def get_hops_between_all_subnets(subnets):
    hops_dict = {}
    for sender in subnets:
        sender_hops = {}
        hops = 1
        done = False
        next_hop_nodes = []
        reached_nodes = sender['members']
        while(not done):
            reached_nodes = reached_nodes + next_hop_nodes
            done = True
            next_hop_nodes = []
            for receiver in subnets:
                if(receiver['name'] in sender_hops.keys()):
                    continue
                elif(set(reached_nodes).isdisjoint(set(receiver['members']))):
                    done = False
                else:
                    sender_hops[receiver['name']] = hops
                    newly_reached = set(receiver['members']) - set(reached_nodes) - set(next_hop_nodes)
                    next_hop_nodes = next_hop_nodes + list(newly_reached)
            hops += 1
            if(hops > len(subnets)):
                print("Subnet " + str(sender) + " is not connected to all subnets")
                break
        hops_dict[sender['name']] = sender_hops
    return hops_dict

# Returns dictionary of dictionaries
# hops_dict[sender_index]: [receiver_index]: hops
def get_hops_between_all_nodes(subnets, nodes, subnet_hops):
    ids = list(range(1, len(nodes) + 1))
    hops_dict = {}
    for sender in ids:
        sender_hops = {}
        for receiver in ids:
            hops = get_hops_between_nodes(sender, receiver, subnets, subnet_hops)
            sender_hops[receiver] = hops
        hops_dict[sender] = sender_hops
    return hops_dict


def get_hops_between_nodes(sender, receiver, subnets, subnet_hops):
    sender_subnets = [subnet['name'] for subnet in subnets if sender in subnet['memberids']]
    receiver_subnets = [subnet['name'] for subnet in subnets if receiver in subnet['memberids']]
    min_hops = len(subnet_hops)

    # Sender and receiver share a subnet
    if(not set(sender_subnets).isdisjoint(receiver_subnets)):
        return 0
    # Sender and receiver don't share a subnet
    else:
        for sender_subnet in sender_subnets:
            for receiver_subnet in receiver_subnets:
                curr_hops = subnet_hops[sender_subnet][receiver_subnet]
                if(curr_hops < min_hops):
                    min_hops = curr_hops
    return min_hops


def estimate_hop_time(txrate, msg_size_bytes, fragment_size):
    hop_time = 0
    # txrate of 500000 has a .99 correlation coefficient to msgSize, with 0.61 slope
    if(txrate > 450000 and txrate < 550000):
        hop_time = 0.061 * msg_size_bytes
    else:
        print("txrate is not a value that has a proven hop time")
        hop_time = (30500 / txrate) * msg_size_bytes
    # Slope * msg_size_bytes / 1000 to get hop_time in seconds
    return hop_time / 1000


def member_subnets(memberid, subnets):
    return [subnet['name'] for subnet in subnets if memberid in subnet['memberids']]

##### TCPDUMP #####

def subnet_tcpdump(nodes, subnets, node_prefix, node_to_ip_dict):
    for node_index in range(0, len(nodes)):
        node = nodes[node_index]
        node_name = node_prefix + str(node_index + 1)
        node_commands = []
        node_subnets = member_subnets(node['number'], subnets)
        for index in range(len(node_subnets)):
            interface = "emane" + str(index)
            print("Starting tcpdump on " + node_name + " and interface " + interface)
            command = "sudo nohup tcpdump -i " + interface + " -n udp -w " \
                      "~/test/emane/gvine/node/" + interface + ".pcap &>/dev/null &"
            node_commands.append(command)
        remote_execute_commands(node_commands, node_to_ip_dict[node_name], "emane-01", False,
                                False, False)

def print_success_fail(success, string):
    if(success):
        print(SUCCESS + string + " SUCCESS" + ENDCOLOR)
    else:
        print(FAIL + string + " FAILED" + ENDCOLOR)

##### MULTITHREADING #####

def wait_for_threads_finish(threads):
    done = False
    while not done:
        done = True
        for curr_thread in threads:
            if curr_thread.isAlive():
                done = False
            else:
                threads.remove(curr_thread)


##### PCAP #####

def get_single_node_pcap(save, prefix):
    dump_dirs = glob("./stats/dumps/" + save + "/*")
    chosen_dir = choose_alphabetic_path(dump_dirs)
    num_nodes = len(glob(chosen_dir + "/*")) - 1
    node_id = input("Packet stats for which node id (1-" + str(num_nodes) + "): ")
    pcap_paths = glob(chosen_dir + "/" + prefix + node_id + "_*")
    return pcap_paths[0]


def get_node_list(num_nodes):
    node_list = []
    try:
        user_input = input("Input node index(1-" + str(num_nodes) + "): ")
        while user_input != "":
            user_input = int(user_input)
            if 1 <= user_input <= num_nodes:
                node_list.append(user_input)
            else:
                print("index out of range, try again")
            user_input = input("Input another node index (1-" +
                               str(num_nodes) + ")(blank to continue): ")
    except KeyboardInterrupt:
        pass
    return node_list

