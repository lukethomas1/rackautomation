#!/usr/bin/python3

# File: racksuite.py
# Author: Luke Thomas
# Date: March 30, 2017
# Description: This is the driver file of the program, delegates to
# commands.py for actual logic

# Local imports
import commands
import functions
import testsuite

loop = True
while(loop):
    # Check config
    config_result = commands.update_config()
    save = config_result['save']
    json = config_result['json']
    subnets = config_result['subnets']
    nodes = config_result['nodes']
    iplist = config_result['iplist']
    ipdict = config_result['ipdict']

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
    elif(arg == "pushconfig"):
        commands.push_config()
    elif(arg == "txrate"):
        commands.change_tx_rate()
    elif(arg == "fragsize"):
        commands.change_frag_size()
    elif(arg == "gvpki"):
        commands.gvpki(iplist)
    elif(arg == "seterrorrate"):
        commands.set_error_rate(subnets, nodes, iplist)
    elif(arg == "removeerrorrate"):
        commands.remove_error_rate(subnets, nodes, iplist)

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
    elif(arg == "autotest"):
        commands.run_auto_test()
    elif(arg == "transferdelay"):
        commands.transfer_delay(len(nodes))
    elif(arg == "avghoptransferdelay"):
        commands.avg_hop_transfer_delay(iplist, ipdict, subnets, nodes)
    elif(arg == "nodedelay"):
        commands.node_delay()
    elif(arg == "message"):
        commands.message(iplist)
    elif(arg == "norm_message"):
        commands.norm_message(iplist)
    elif(arg == "testmessage"):
        commands.test_message(iplist)
    elif(arg == "checkreceiving"):
        sender_node = int(input("Sender node? : "))
        testsuite.check_network_receiving(iplist, sender_node)
    elif(arg == "checkreceived"):
        sender_node = int(input("Sender node? : "))
        file_name = input("File Name? : ")
        inv_ipdict = functions.invert_dict(ipdict)
        topodict = functions.generate_rack_to_topo_dict(iplist, inv_ipdict, nodes)
        testsuite.check_network_received(file_name, iplist, inv_ipdict, topodict, sender_node)


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
