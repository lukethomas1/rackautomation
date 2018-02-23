from typing import List
from classes.racknode import RackNode
import threading
from time import sleep

import functions
import commands
import testsuite

def half_flat_dtn_block(node_objects):
    threads = []
    half = int(len(node_objects) / 2)
    for node_index in range(0, half):
        for other_index in range(half, half*2):
            a = node_objects[node_index]
            b = node_objects[other_index]
            new_thread_a = threading.Thread(target=a.block_node, args=(b,))
            new_thread_b = threading.Thread(target=b.block_node, args=(a,))
            threads.append(new_thread_a)
            threads.append(new_thread_b)
            new_thread_a.start()
            new_thread_b.start()
    for t in threads:
        t.join()
    print("Done.")

def disconnect_subnets(node_objects: List[RackNode]):
    choice = input("Disconnect all nodes (leave blank) or choose (c): ")
    if (choice == "c"):
        node_list = functions.get_node_list(len(node_objects))
        node_objects = [node_objects[index - 1] for index in node_list]

    for node in node_objects:
        # If the node is in more than one subnet, ie. it is a gateway node
        if len(node.member_subnets) > 1:
            subnets_to_disconnect = node.member_subnets[1:]
            for subnet in subnets_to_disconnect:
                node.block_subnet(subnet["name"])

def block_nodes(node_objects: List[RackNode]):
    node_list = functions.get_node_list(len(node_objects))

    for node_index in node_list:
        node_index = node_index - 1
        node = node_objects[node_index]
        for subnet in node.member_subnets:
            node.block_subnet(subnet["name"])

def dtn_test(save_file, node_objects, refactor=False):
    file_sizes = functions.get_input_list("Input another message size: ")
    file_sizes = [str(filesize) for filesize in file_sizes]
    print("File sizes: " + str(file_sizes))

    for file_size in file_sizes:
        print("Running dtntest for message size: " + str(file_size))
        if refactor:
            commands.start_refactor(save_file, node_objects)
        else:
            commands.start(save_file, node_objects)
        sleep(1)
        half_flat_dtn_block(node_objects)
        sleep(1)
        file_name = "test1"
        if refactor:
            commands.test_refactor_message(node_objects, message_name=file_name,
                                           file_size=file_size, wait=False)
        else:
            commands.test_message_no_wait(node_objects, message_name=file_name, file_size=file_size)
        sleep(1)
        sender_id = node_objects[0].id
        half = int(len(node_objects) / 2)
        # Wait for the first half to get it
        testsuite.wait_for_message_received(file_name, node_objects[:half], sender_id, 9999,
                                            sleep_time=2)
        sleep(1)
        commands.reset_iptables(node_objects)
        sleep(1)
        testsuite.wait_for_message_received(file_name, node_objects, sender_id, 9999, sleep_time=2)
        sleep(1)
        commands.stop(node_objects)
        sleep(1)
        commands.stats_tcpdump(node_objects)
        sleep(1)
        commands.clean(node_objects, 2)
        sleep(3)


