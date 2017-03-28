import json
import objects
import os
import paramiko
import pyrebase
import shutil
import subprocess
import time

def copy_default_config(config_path, destination_path):
    # Get name of all files in default config directory
    config_files = os.listdir(config_path)
    for file_name in config_files:
        full_file_name = os.path.join(config_path, file_name)
        if(os.path.isfile(full_file_name)):
            shutil.copy(full_file_name, destination_path)

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


def create_file_from_list(file_path, contents):
  file = open(file_path, 'w')
  for line in contents:
    file.write(line + "\n")
  file.close()


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


def create_save_dir(folder_path):
    os.makedirs(folder_path, exist_ok=True)


def edit_ssh_config(iplist):
  size = len(iplist)
  fmt = 'Host {nodename}\nHostName {nodeaddress}\nUser emane-01\nIdentityFile ~/.ssh/id_rsa\n\n'
  file = open("/home/joins/.ssh/config", 'w')

  process = subprocess.Popen(['rack', 'servers', 'instance', 'list', '--fields',
  'name,publicipv4'], stdout=subprocess.PIPE)
  pairs = process.stdout.read().decode().splitlines()[1:]

  for index in range(0, size):
    pair = pairs[index].split('\t')
    name = pair[0]
    address = pair[1]
    writestring = fmt.format(nodename=name, nodeaddress=address)
    file.write(writestring)

def execute_bash_script(script_path):
    subprocess.call(script_path);

def fill_platform_template(xml_string, node_index):
    # Replace "NEMID" with the node index
    xml_string = xml_string.replace("NEMID", str(node_index))
    return xml_string

def get_json_from_firebase(save_file):
    # Firebase Information
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


# Returns a list
def get_rack_ip_list():
  process = subprocess.Popen(['rack', 'servers', 'instance', 'list', '--fields',
  'publicipv4'], stdout=subprocess.PIPE)
  output = process.stdout.read().decode().splitlines()
  return output


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
  subprocess.Popen(['pscp', '-r', '-h', 'pssh-hosts', '-l', 'emane-01', './default_config/',
    '/home/emane-01/GrapeVine/topologies/' + save_folder], stdout=subprocess.DEVNULL)
  print("Sleep 5 seconds")
  time.sleep(5)
  subprocess.Popen(['pssh', '-h', 'pssh-hosts', '-l', 'emane-01', '-i', '-P',
    'cd ~/GrapeVine/topologies/' + save_folder + ' && cp ./default_config/* .'],
    stdout=subprocess.DEVNULL)


def remote_copy_emane_scripts(save_folder, iplist):
  num_instances = len(iplist)
  for node_index in range(1, num_instances + 1):
    node_ip = iplist[num_instances - node_index]
    start_dir = './topologies/' + save_folder + '/emane_start.sh'
    stop_dir = './topologies/' + save_folder + '/emane_stop.sh'
    to_dir = 'root@' + node_ip + ':/home/emane-01/GrapeVine/topologies/' + save_folder
    subprocess.Popen(['scp', start_dir, to_dir])
    subprocess.Popen(['scp', stop_dir, to_dir])
    time.sleep(1)
    

def remote_copy_platform_xmls(save_folder, iplist):
  num_instances = len(iplist)
  for node_index in range(1, num_instances + 1):
    file_name = 'platform' + str(node_index) + '.xml'
    node_ip = iplist[num_instances - node_index]
    from_dir = './topologies/' + save_folder + '/' + file_name
    to_dir = 'root@' + node_ip + ':/home/emane-01/GrapeVine/topologies/' + save_folder + "/platform.xml"
    subprocess.Popen(['scp', from_dir, to_dir], stdout=subprocess.PIPE)
    time.sleep(1)


def remote_copy_scenario(save_folder, iplist):
  num_instances = len(iplist)
  for node_index in range(1, num_instances + 1):
    node_ip = iplist[num_instances - node_index]
    from_dir = './topologies/' + save_folder + '/scenario.eel'
    to_dir = 'root@' + node_ip + ':/home/emane-01/GrapeVine/topologies/' + save_folder + "/scenario.eel"
    subprocess.Popen(['scp', from_dir, to_dir], stdout=subprocess.PIPE)
    time.sleep(1)


def remote_create_dirs(save_folder):
  # Make topologies directory
  subprocess.Popen(['pssh', '-h', 'pssh-hosts', '-l', 'emane-01', '-i', '-P',
  'cd ~/GrapeVine && mkdir topologies'], stdout=subprocess.DEVNULL)

  # Make this topology directory
  subprocess.Popen(['pssh', '-h', 'pssh-hosts', '-l', 'emane-01', '-i', '-P',
  'cd ~/GrapeVine/topologies && mkdir ' + save_folder], stdout=subprocess.DEVNULL) 


def remote_delete_topology(save_folder):
  subprocess.Popen(['pssh', '-h', 'pssh-hosts', '-l', 'emane-01', '-i', '-P',
  'rm -r ~/GrapeVine/topologies/' + save_folder], stdout=subprocess.DEVNULL)


def remote_run_emane(save_path, file):
  subprocess.Popen(['pssh', '-h', 'pssh-hosts', '-l', 'emane-01', '-i', '-P',
  'cd ' + save_path + ' && sudo ./' + file],
  stdout=subprocess.DEVNULL)


def remote_start_gvine():
  command = "cd ~/test/emane/gvine/node/ && java -jar jvine.jar $i 500 >> log_node$i.txt"

  key = paramiko.RSAKey.from_private_key_file("/home/joins/.ssh/id_rsa")
  ssh = paramiko.SSHClient()
  ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
  ssh.connect('23.253.108.97', username="emane-01", pkey=key)

  stdin, stdout, stderr = ssh.exec_command(command)
  print(stdout.readlines())
  ssh.close()


def synchronize():
  subprocess.Popen(['pssh', '-h', 'pssh-hosts', '-l', 'emane-01', '-i', '-P',
  'sudo service ntp stop'], stdout=subprocess.DEVNULL)
  time.sleep(1)
  subprocess.Popen(['pssh', '-h', 'pssh-hosts', '-l', 'emane-01', '-i', '-P',
  'sudo ntpd -gq'], stdout=subprocess.DEVNULL)
  time.sleep(1)
  subprocess.Popen(['pssh', '-h', 'pssh-hosts', '-l', 'emane-01', '-i', '-P',
  'sudo service ntp start'], stdout=subprocess.DEVNULL)
    

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

def write_platform_xmls(subnets, nodes, topo_path):
    # Open the xml template and read its contents
    template = open("./templates/platform_template.xml")
    contents = template.read()
    template.close()

    # Replace appropriate information and write new xml files for each node
    for index in range(1, len(nodes) + 1):
        path = topo_path + "platform" + str(index) + ".xml"
        new_xml = open(path, "w")
        new_xml.write(fill_platform_template(contents, index))
        new_xml.close()
