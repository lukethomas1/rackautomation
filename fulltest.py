import config
import commands
import functions
import testsuite
import statsuite
from time import sleep

# Constants defined in config.py
NODE_PREFIX = config.NODE_PREFIX
SAVE_FILE = config.SAVE_FILE
IMAGE_NAME = config.IMAGE_NAME
IP_FILE = config.IP_FILE
IP_BLACK_LIST = config.IP_BLACK_LIST
JAR_FILE = config.JAR_FILE

save = None
json = None
subnets = None
nodes = None
iplist = None

def auto_test(max_tx_rate, num_iterations, msg_sizes_bytes, error_rates, msg_interval):
    update_variables()

    # Start nodes on Rackspace if there aren't any with the correct prefix
    if(functions.wait_until_nodes_ready(NODE_PREFIX, len(nodes), 1)):
        commands.initialize(SAVE_FILE, len(nodes))

    # Wait until nodes are ready on rackspace, then setup EMANE and Gvine
    fail_time = 1000
    if(functions.wait_until_nodes_ready(NODE_PREFIX, len(nodes), fail_time)):
        # This if statement will execute when the nodes are ready
        update_variables()
        commands.setup(SAVE_FILE, subnets, nodes, iplist)
    else:
        print("Nodes with prefix " + NODE_PREFIX + " aren't ready")
        return
    sleep(10)

    # Send a message on Gvine

    for file_size in msg_sizes_bytes:
        for src_node in range(len(nodes)):
            ip = iplist[src_node]
            for iteration in range(num_iterations):
                # Start EMANE and Gvine
                commands.start(SAVE_FILE, iplist)
                sleep(10)

                # Send Message
                msg_name = "autotestmsg_" + str(src_node + 1) + "_" + str(iteration + 1) + ".txt"
                testsuite.send_gvine_message(ip, msg_name, file_size, str(src_node + 1), "")

                # Wait for message to be sent
                wait_msg_time = 60
                sleep(wait_msg_time)
                commands.stop(SAVE_FILE)

                # Gather data from nodes
                statsuite.generate_event_dbs(iplist)
                sleep(3)

                path_to_db = "/home/emane-01/test/emane/gvine/node/dbs/eventsql_copy.db"
                statsuite.copy_event_dbs(iplist, path_to_db, "./stats/events/" + SAVE_FILE + "/nodedata/")
                sleep(3)

                functions.remote_delete_events(NODE_PREFIX)
                sleep(3)

                input_dir = "./stats/events/" + SAVE_FILE + "/nodedata/"
                output_dir = "./stats/events/" + SAVE_FILE + "/"
                path_to_sql_db = statsuite.combine_event_dbs(input_dir, output_dir)
                sleep(3)

                rows = statsuite.get_sql_delay_data(path_to_sql_db)
                dict = statsuite.parse_sql_db(rows)
                statsuite.plot_delays(dict)



def update_variables():
    global save
    global json
    global subnets
    global nodes
    global iplist
    functions.set_topology(SAVE_FILE, NODE_PREFIX)
    config_result = functions.load_data()
    save = config_result['save']
    json = config_result['json']
    subnets = config_result['subnets']
    nodes = config_result['nodes']
    iplist = config_result['iplist']
