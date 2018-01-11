def half_flat_dtn_block(node_objects):
    half = int(len(node_objects) / 2)
    for node_index in range(0, half):
        for other_index in range(half, half*2):
            node_objects[node_index].block_node(node_objects[other_index])
            node_objects[other_index].block_node(node_objects[node_index])
