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
import packetsuite
import config

PI_IP_LIST = config.PI_IP_LIST
PLATFORM = config.DEFAULT_PLATFORM

loop = True
while(loop):
    # Check config
    config_result = commands.update_config()
    save = config_result['save']
    json = config_result['json']
    subnets = config_result['subnets']
    nodes = config_result['nodes']
    rack_iplist = config_result['iplist']
    nodeipdict = config_result['nodeipdict']
    racknodes = config_result['racknodes']

    node_objects = commands.get_assigned_nodes()
    print(str(len(node_objects)) + " assigned")

    arg = input("Command: ")

    ##### SETUP COMMANDS #####

    if(arg == "assign"):
        node_objects = commands.assign_nodes(subnets, nodes)
        functions.update_pickle(".data.nodes", "nodes", node_objects)
    elif(arg == "unassign"):
        functions.update_pickle(".data.nodes", "nodes", [])
    elif(arg == "init"):
        commands.initialize(save, len(nodes))
    elif(arg == "iplist"and PLATFORM == "rack"):
        commands.make_iplist(len(nodes), iplist)
    elif(arg == "ipfile"and PLATFORM == "rack"):
        commands.make_ipfile(len(nodes))
    elif(arg == "editssh"):
        commands.edit_ssh()
    elif(arg == "reset"):
        commands.reset_topology()
    elif(arg == "configure"):
        commands.configure(save, subnets, nodes)
    elif(arg == "setup"):
        commands.setup(save, subnets, nodes, node_objects)
    elif(arg == "update_emane"):
        commands.update_emane(save, subnets, nodes, node_objects)
    elif(arg == "push_scenario"):
        functions.remote_copy_scenario(save, iplist)
    elif(arg == "pushconfig"):
        commands.push_config(node_objects)
    elif(arg == "pushfile"):
        commands.push_file(node_objects)
    elif(arg == "txrate"):
        commands.change_tx_rate()
    elif(arg == "fragsize"):
        commands.change_frag_size()
    elif(arg == "gvpki"):
        commands.gvpki(node_objects)
    elif(arg == "gvpkipushload"):
        commands.gvpki_push_load(node_objects)
    elif(arg == "gvpkiload"):
        for node in node_objects:
            node.load_certs(len(node_objects))
    elif(arg == "seterrorrate"):
        commands.set_error_rate(subnets, nodes, iplist)
    elif(arg == "removeerrorrate"):
        commands.remove_error_rate(subnets, nodes, iplist)
    elif(arg == "are_nodes_ready"):
        commands.wait_for_nodes_init(len(nodes))

    ##### START COMMANDS #####

    elif(arg == "start"):
        commands.start(save, node_objects)
    elif(arg == "startchoose"):
        commands.start_choose(save, node_objects)
    elif(arg == "start_debug"):
        commands.start_debug(save, iplist, nodes, subnets, nodeipdict)
    elif(arg == "start_console"):
        commands.start_console(iplist)
    elif(arg == "start_emane"):
        commands.start_emane(save, node_objects)
    elif(arg == "start_gvine"):
        commands.start_gvine(iplist)
    elif(arg == "restart_gvine"):
        commands.restart_gvine(node_objects)
    elif(arg == "start_norm"):
        commands.start_norm(iplist, subnets, nodes)
    elif(arg == "startlogpackets"):
        commands.start_basic_tcpdump(nodes, subnets, nodeipdict)

    ##### TEST COMMANDS #####

    elif(arg == "rackping"):
        commands.rack_ping(subnets)
    elif(arg == "autotest"):
        commands.run_auto_test()
    elif(arg == "transferdelay"):
        commands.transfer_delay(len(nodes))
    elif(arg == "avghoptransferdelay"):
        commands.avg_hop_transfer_delay(iplist, nodeipdict, subnets, nodes)
    elif(arg == "nodedelay"):
        commands.node_delay()
    elif(arg == "norm_delay"):
        commands.norm_delay(iplist)
    elif(arg == "message"):
        commands.message(iplist)
    elif(arg == "norm_message"):
        commands.norm_message(iplist)
    elif(arg == "testmessage"):
        inv_ipdict = functions.invert_dict(nodeipdict)
        commands.test_message(node_objects)
    elif(arg == "testmultiple"):
        commands.test_multiple_messages(node_objects)
    elif(arg == "checkreceiving"):
        sender_node = int(input("Sender node? : "))
        testsuite.check_network_receiving(iplist, sender_node)
    elif(arg == "checkreceived"):
        sender_node = int(input("Sender node? : "))
        file_name = input("File Name? : ")
        inv_ipdict = functions.invert_dict(nodeipdict)
        topodict = functions.generate_rack_to_topo_dict(iplist, inv_ipdict, nodes)
        testsuite.check_network_received(file_name, iplist, inv_ipdict, topodict, sender_node)
    elif(arg == "waitreceived"):
        sender_node = int(input("Sender node? : "))
        file_name = input("File Name? : ")
        wait_time = int(input("Wait time? : "))
        testsuite.wait_for_message_received(file_name, node_objects, sender_node, wait_time)
    elif(arg == "scapytest"):
        dump_dirs = packetsuite.get_dump_timestamp_dirs()
        node_dict = packetsuite.get_pcap_node_dict(dump_dirs[0], len(nodes))
        pkt = node_dict["node1"]["tx"]["gvine"][10]
        packetsuite.useful_functions(pkt)

    ##### DATA COMMANDS #####

    elif(arg == "data"):
        commands.print_data(data)
    elif(arg == "stats"):
        commands.stats(save, len(nodes), iplist)
    elif(arg == "stats_events"):
        commands.stats_events(save, node_objects)
    elif(arg == "stats_tcpdump"):
        commands.stats_tcpdump(node_objects)
    elif arg == "pull_logs":
        commands.pull_logfiles(node_objects)
    elif arg == "stats_packet_statistics":
        commands.stats_packet_statistics(save)
    elif arg == "stats_packet_node":
        commands.stats_packet_node(save)
    elif arg == "single_graph":
        commands.stats_single_graph(save)
    elif arg == "pcap_to_sql":
        commands.pcap_to_sql(save)
    elif(arg == "txpackets"):
        commands.stats_sent_packets()
    elif(arg == "rxpackets"):
        commands.stats_received_packets()
    elif(arg == "rxrank"):
        commands.stats_received_rank()
    elif(arg == "basic_packets_graph"):
        commands.stats_basic_packets()
    elif(arg == "stop_beacon"):
        commands.stats_stop_beacons()
    elif(arg == "counts"):
        packetsuite.compare_all_sql_tcpdump(len(nodes))
    elif(arg == "delays"):
        commands.stats_delays(save, len(nodes))
    elif(arg == "emane_stats"):
        commands.stats_emane(save, node_objects)
    elif(arg == "parse"):
        parse_term = input("Enter parse term: ")
        commands.stats_parse(save, len(nodes), parse_term)
    elif(arg == "norm_monitor"):
        commands.norm_monitor(iplist)

    ##### STOP COMMANDS #####

    elif(arg == "stop"):
        commands.stop(node_objects)
    elif(arg == "stop_nodes"):
        commands.stop_nodes(node_objects)
    elif(arg == "stop_gvine"):
        commands.stop_gvine()
    elif(arg == "stop_norm"):
        commands.stop_norm()
    elif(arg == "stoplogpackets"):
        commands.stop_all_tcpdump()

    ##### EXTRA COMMANDS #####

    elif(arg == "clean"):
        commands.clean(node_objects)
    elif(arg == "clean_norm"):
        functions.clean_norm(iplist)
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
