#!/usr/bin/env python3

# Local imports
import functions
import objects
import time

# Functions are ordered in usage order
def generate_iplist():
  # Get the ips of the nodes and write to pssh-hosts for pssh command
  iplist = functions.get_rack_ip_list()[1:]
  functions.create_file_from_list("./pssh-hosts", iplist)
  return iplist


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


def setup():
  iplist = generate_iplist()

  # Get user input for which save file to pull down from firebase
  save_file = input("Input Save File Name: ")
  topo_path = "./topologies/" + save_file + "/"

  # Get the save from firebase
  json_string = functions.get_json_from_firebase(save_file)
  subnets, nodes = functions.convert_json_to_object(json_string)

  # Generate and copy files to the local topology folder
  functions.create_save_dir(topo_path)
  functions.write_platform_xmls(subnets, nodes, topo_path)
  functions.write_emane_start_stop_scripts(save_file, len(nodes))

  # Use parallel ssh to modify each node on the cloud
  print("Creating remote directories")
  functions.remote_create_dirs(save_file)
  time.sleep(2)
  print("Copying default config")
  functions.remote_copy_default_config(save_file)
  time.sleep(2)
  print("Copying scenario.eel")
  functions.remote_copy_scenario(save_file, iplist)
  print("Copying platform xmls")
  functions.remote_copy_platform_xmls(save_file, iplist)
  print("Copying emane scripts")
  functions.remote_copy_emane_scripts(save_file, iplist)


def start():
  save_file = input("Input Save File Name: ")
  save_path = '~/GrapeVine/topologies/' + save_file
  file = 'emane_start.sh'
  functions.synchronize()
  functions.remote_run_emane(save_path, file)
  #functions.remote_start_gvine()


def stats():
  print("stats command not implemented yet")


def stop():
  save_file = input("Input Save File Name: ")
  save_path = '~/GrapeVine/topologies/' + save_file
  file = 'emane_stop.sh'
  functions.remote_run_emane(save_path, file)


def delete():
  save_file = input("Input Save File Name: ")
  functions.remote_delete_topology(save_file)


def usage():
  usage = ""
  usage += "---------- USAGE ----------\n"
  usage += "python3 racksuite.py <command>\n\n"
  usage += "---------- COMMANDS ----------\n"
  usage += "init\t\t\t create rackspace cloud instances\n"
  usage += "iplist\t\t\t update iplist and pssh-hosts"
  usage += "setup\t\t\t prepare XMLs, radio models, etc\n"
  usage += "run\t\t\t start emane and grapevine\n"
  usage += "stats\t\t\t save statistics\n"
  usage += "stop\t\t\t stop emane and grapevine\n"
  usage += "delete\t\t\t delete rackspace cloud instances\n"
  usage += "help\t\t\t show this help message"
  print(usage)
