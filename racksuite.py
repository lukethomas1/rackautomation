#!/usr/bin/python3

# File: racksuite.py
# Author: Luke Thomas
# Date: March 30, 2017
# Description: This is the driver file of the program, delegates to
# commands.py for actual logic

# Local imports
import commands
import functions
import objects
import testsuite

loop = True
while(loop):
    # Check config
    config_result = commands.update_config()
    if(config_result):
        save = config_result['save']
        json = config_result['json']
        subnets = config_result['subnets']
        nodes = config_result['nodes']
        iplist = config_result['iplist']

    arg = input("Command: ")

    ##### SETUP COMMANDS #####

    if(arg == "init"):
        commands.initialize(save, len(nodes))
    elif(arg == "iplist"):
        commands.make_iplist(len(nodes))
    elif(arg == "reset"):
        commands.reset_topology()
    elif(arg == "configure"):
        commands.configure(save, subnets, nodes)
    elif(arg == "setup"):
        commands.setup(save, subnets, nodes, iplist)
    elif(arg == "push_scenario"):
        functions.remote_copy_scenario(save, iplist)

    ##### START COMMANDS #####

    elif(arg == "start"):
        commands.start(save, iplist)
    elif(arg == "start_console"):
        commands.start_console(iplist)
    elif(arg == "start_emane"):
        commands.start_emane(save)
    elif(arg == "start_gvine"):
        commands.start_gvine(iplist)
    elif(arg == "start_norm"):
        commands.start_norm(iplist, subnets, nodes)

    ##### TEST COMMANDS #####

    elif(arg == "ping"):
        commands.ping(subnets, nodes)
    elif(arg == "message"):
        commands.message(iplist)
    elif(arg == "norm_message"):
        commands.norm_message(iplist)
    elif(arg == "testmessage"):
        commands.test_message(iplist)

    ##### DATA COMMANDS #####

    elif(arg == "data"):
        commands.print_data(data)
    elif(arg == "stats"):
        commands.stats(save, len(nodes), iplist)
    elif(arg == "stats_events"):
        commands.stats_events(save, iplist)
    elif(arg == "delays"):
        commands.stats_delays(save, len(nodes))
    elif(arg == "emane_stats"):
        commands.stats_emane(save, len(nodes), iplist)
    elif(arg == "parse"):
        parse_term = input("Enter parse term: ")
        commands.stats_parse(save, len(nodes), parse_term)
    elif(arg == "norm_monitor"):
        commands.norm_monitor(iplist)

    ##### STOP COMMANDS #####

    elif(arg == "stop"):
        commands.stop(save)
    elif(arg == "stop_gvine"):
        commands.stop_gvine()
    elif(arg == "stop_norm"):
        commands.stop_norm()

    ##### EXTRA COMMANDS #####

    elif(arg == "clean"):
        commands.clean()
    elif(arg == "delete"):
        commands.delete(save)
    elif(arg == "kill"):
        commands.kill()

    ##### QUIT #####
    
    elif(arg == "q" or arg == "quit" or arg == "exit"):
        loop = False

    ##### USAGE #####
    else:
        commands.usage()
