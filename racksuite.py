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

# Check config
config_result = commands.update_config()
save = config_result['save']
json = config_result['json']
subnets = config_result['subnets']
nodes = config_result['nodes']
iplist = config_result['iplist']

if(arg == "init"):
    commands.initialize(save, len(nodes))
elif(arg == "iplist"):
    commands.make_iplist(len(nodes))
elif(arg == "reset"):
    commands.reset()
elif(arg == "configure"):
    commands.configure(save, subnets, nodes)
elif(arg == "setup"):
    commands.setup(save, subnets, nodes)
elif(arg == "start"):
    commands.start(save, iplist)
elif(arg == "start_console"):
    commands.start_console(iplist)
elif(arg == "start_gvine"):
    commands.start_gvine(iplist)
elif(arg == "stop_gvine"):
    commands.stop_gvine()
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
elif(arg == "delays"):
    commands.stats_delays(save, len(nodes))
elif(arg == "emane_stats"):
    commands.stats_emane(save, len(nodes), iplist)
elif(arg == "parse"):
    parse_term = input("Enter parse term: ")
    commands.stats_parse(save, len(nodes), parse_term)
elif(arg == "stop"):
    commands.stop(save)
elif(arg == "clean"):
    commands.clean()
elif(arg == "delete"):
    commands.delete(save)
elif(arg == "kill"):
    commands.kill()
else:
    commands.usage()
