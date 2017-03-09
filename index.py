#!/usr/bin/env python3

# Local imports
import objects
import functions

functions.remote_start_gvine()

# Get user input for which save file to pull down from firebase
save_file = input("Input Save File Name: ")
topo_path = "./topologies/" + save_file + "/"

# Get the save from firebase
json_string = functions.get_json_from_firebase(save_file)
subnets, nodes = functions.convert_json_to_object(json_string)

val = functions.create_save_dir(topo_path)
#functions.write_platform_xmls(subnets, nodes, topo_path)
#functions.copy_default_config("./default_config", topo_path)

functions.write_emane_start_stop_scripts(save_file, 2)

#print("Calling bash script..")
#functions.execute_bash_script("./testscript.sh")
