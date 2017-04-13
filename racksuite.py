#!/usr/bin/python3

# File: racksuite.py
# Author: Luke Thomas
# Date: March 30, 2017
# Description: This is the driver file of the program, delegates to
# commands.py for actual logic

# System Imports
import sys
import os

# Local imports
import commands
import functions
import objects
import testsuite

# Check for valid amount of arguments
if(len(sys.argv) != 2):
    commands.usage()
    exit()

arg = sys.argv[1]

if(arg == "topology"):
    save_file = input("Input Save File Name: ")
    commands.set_topology(save_file)
    print("Done.")
    exit()
elif(os.path.isfile(".data.pickle")):
    data = commands.load_data()
    save = data['save']
    json = data['json']
    subnets = data['subnets']
    nodes = data['nodes']
    iplist = data['iplist']
else:
    print("Use ./racksuite.py topology to set data")
    exit()

if(arg == "init"):
    commands.initialize(save, len(nodes))
elif(arg == "iplist"):
    commands.make_iplist(len(nodes))
elif(arg == "configure"):
    commands.configure(save, subnets, nodes)
elif(arg == "setup"):
    # Update the ip list
    commands.set_topology(save)
    iplist = commands.load_data()['iplist']
    commands.setup(save, subnets, nodes, iplist)
elif(arg == "start"):
    commands.start(save, iplist)
elif(arg == "start_gvine"):
    commands.start_gvine(iplist)
elif(arg == "data"):
    commands.print_data(data)
elif(arg == "ping"):
    commands.ping(subnets, nodes)
elif(arg == "message"):
    commands.message(iplist)
elif(arg == "testmessage"):
    commands.test_message(iplist)
elif(arg == "stats"):
    commands.stats(save, len(nodes), iplist)
elif(arg == "emane_stats"):
    commands.stats_emane(save, len(nodes), iplist)
elif(arg == "parse"):
    parse_term = input("Enter parse term: ")
    commands.stats_parse(save, len(nodes), parse_term)
elif(arg == "stop"):
    commands.stop(save)
elif(arg == "delete"):
    commands.delete(save)
elif(arg == "kill"):
    commands.kill()
else:
    commands.usage()
