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
    print("Running autotest on topology: " + SAVE_FILE + " and node_prefix: " + NODE_PREFIX)
    update_variables()

    # Start nodes on Rackspace if there aren't any with the correct prefix
    if(not functions.wait_until_nodes_ready(NODE_PREFIX, len(nodes), 1)):
        commands.initialize(SAVE_FILE, len(nodes))

    # Wait until nodes are ready on rackspace, then setup EMANE and Gvine
    fail_time = 1000
    if(functions.wait_until_nodes_ready(NODE_PREFIX, len(nodes), fail_time)):
        # This if statement will execute when the nodes are ready
        update_variables()
        commands.setup(SAVE_FILE, subnets, nodes, iplist)
        functions.parallel_ssh(IP_FILE, "rm ~/test/emane/gvine/node/autotest*")
    else:
        print("Nodes with prefix " + NODE_PREFIX + " aren't ready")
        return
    sleep(10)

    # Do the tests
    iterate(max_tx_rate, num_iterations, msg_sizes_bytes, error_rates, msg_interval)


def iterate(max_tx_rate, num_iterations, msg_sizes_bytes, error_rates, msg_interval):
    update_variables()
    functions.change_gvine_tx_rate(max_tx_rate, "./autotestfiles/gvine.conf.json")

    # Loop through file sizes
    for file_size in msg_sizes_bytes:
        file_size_kb = str(int(int(file_size) / 1024))
        frag_size = 100 if int(file_size_kb) <= 100 else 500
        print("Changing fragment size to " + str(frag_size))
        functions.change_gvine_frag_size(frag_size, "./autotestfiles/gvine.conf.json")
        functions.push_gvine_conf(IP_FILE, "./autotestfiles/gvine.conf.json")

        # Loop through sender nodes
        for src_node in range(len(nodes)):
            ip = iplist[src_node]

            # Do num_iterations iterations of the same configuration
            for iteration in range(num_iterations):
                # Start EMANE and Gvine
                commands.start(SAVE_FILE, iplist)
                sleep(10)

                # Send Message
                msg_name = "autotestmsg_" + str(src_node + 1) + "_" + str(iteration + 1) + ".txt"
                print("Sending message")
                print("Ip: " + ip)
                print("Message name: " + msg_name)
                print("-----")
                print("Iteration: " + str(iteration))
                print("Sender node: " + str(src_node + 1))
                print("File size(bytes): " + file_size)
                print("Fragment size: " + str(frag_size))
                testsuite.send_gvine_message(ip, msg_name, file_size_kb, str(src_node + 1), "")
                sleep(3)
                testsuite.check_network_receiving(iplist, src_node + 1)

                # Wait for message to be sent
                wait_msg_time = 60
                print("Waiting " + str(wait_msg_time) + " seconds")
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
                if(rows):
                    print(str(rows))
                    #dict = statsuite.parse_delay_rows(rows)
                    #statsuite.plot_delays(dict)


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
