from typing import List
from classes.racknode import RackNode

import functions

def half_flat_dtn_block(node_objects):
    half = int(len(node_objects) / 2)
    for node_index in range(0, half):
        for other_index in range(half, half*2):
            node_objects[node_index].block_node(node_objects[other_index])
            node_objects[other_index].block_node(node_objects[node_index])

def disconnect_subnets(node_objects: List[RackNode]):
    for node in node_objects:
        # If the node is in more than one subnet, ie. it is a gateway node
        if len(node.member_subnets) > 1:
            subnets_to_disconnect = node.member_subnets[1:]
            for subnet in subnets_to_disconnect:
                node.block_subnet(subnet["name"])

def block_nodes(node_objects: List[RackNode]):
    node_list = functions.get_node_list(len(node_objects))

    for node_index in node_list:
        node_index = str(node_index) - 1
        node = node_objects[node_index]
        for subnet in node.member_subnets:
            node.block_subnet(subnet["name"])
