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

def auto_test():
    update_variables()

    # Start nodes on Rackspace
    initialize(SAVE_FILE, len(nodes))

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
    # Start EMANE and Gvine
    commands.start(SAVE_FILE, iplist)

    sleep(10)
    # Send a message on Gvine
    send_num = "1"
    ip = iplist[int(send_num) - 1]
    msg_name = "autotestmsg.txt"
    file_size = "100"
    testsuite.send_gvine_message(ip, msg_name, file_size, send_num, "")

    sleep(10)
    # Gather data from nodes
    statsuite.generate_event_dbs(iplist)
    sleep(3)
    path_to_db = "/home/emane-01/test/emane/gvine/node/dbs/eventsql_copy.db"
    statsuite.copy_event_dbs(iplist, path_to_db, "./stats/events/" + SAVE_FILE + "/nodedata/")
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
