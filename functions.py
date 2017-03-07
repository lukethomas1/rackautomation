import json
import pyrebase
import objects
import os
import shutil
import paramiko

def testparamiko():
    key = paramiko.RSAKey.from_private_key_file("/home/joins/.ssh/id_rsa")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print("connecting")
    ssh.connect('23.253.108.97', username="emane-01", pkey=key)
    print("connected")

    stdin, stdout, stderr = ssh.exec_command("uptime")
    print(stdout.readlines())
    ssh.close()

def copy_default_config(config_path, destination_path):
    # Get name of all files in default config directory
    config_files = os.listdir(config_path)
    for file_name in config_files:
        full_file_name = os.path.join(config_path, file_name)
        if(os.path.isfile(full_file_name)):
            shutil.copy(full_file_name, destination_path)

def convert_json_to_object(json_string):
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

def create_save_dir(folder_path):
    os.makedirs(folder_path, exist_ok=True)

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
    return saves[save_file]['string']

def print_subnets_and_nodes(subnets, nodes):
    print("Subnet Names:")
    for subnet in subnets:
        print(str(subnet['name']))

    print()
    print("Node Names:")
    for node in nodes:
        print(str(node['id']))
    print()

def write_platform_xmls(subnets, nodes, topo_path):
    # Open the xml template and read its contents
    template = open("platform_template.xml")
    contents = template.read()
    template.close()

    # Replace appropriate information and write new xml files for each node
    for index in range(1, len(nodes) + 1):
        path = topo_path + "platform" + str(index) + ".xml"
        new_xml = open(path, "w")
        new_xml.write(fill_platform_template(contents, index))
        new_xml.close()
