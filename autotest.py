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

# Configuration variables
save = None
json = None
subnets = None
nodes = None
iplist = None

# Parameter variables
max_tx_rate = None
num_iterations = None
msg_sizes_bytes = None
error_rates = None
msg_interval = None

# Other global variables
msg_counter = 0

def update_config():
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


def initialize_parameters(max_tx, num_iter, msg_sizes, err_rates, msg_int):
    global max_tx_rate
    global num_iterations
    global msg_sizes_bytes
    global error_rates
    global msg_interval
    max_tx_rate = max_tx
    num_iterations = num_iter
    msg_sizes_bytes = msg_sizes
    error_rates = err_rates
    msg_interval = msg_int


def increment_parameters(current, max, length):
    increment_next = True
    for index in range(length):
        if(increment_next):
            current[index] += 1
            if(current[index] == max[index]):
                current[index] = 0
                increment_next = True
            else:
                increment_next = False
    # If this is true, we are done testing
    if(increment_next):
        return [0] * length
    return current

def run(need_setup):
    if(need_setup):
        update_config()
        initialize(fail_time=1000)
        update_config()
        setup()
    update_config()
    functions.change_gvine_tx_rate(max_tx_rate, "./autotestfiles/gvine.conf.json")
    # Parameters with indices: Iteration, Source Node, Message Size, Error Rate
    param_indices = [0, 0, 0, 0]
    max_indices = [num_iterations, len(nodes), len(msg_sizes_bytes), len(error_rates)]
    done = False
    while(not done):
        # Set up the parameters for this test
        iteration = param_indices[0]
        source_node = param_indices[1]
        message_size_kb = str(int(int(msg_sizes_bytes[param_indices[2]]) / 1024))
        error_rate = error_rates[param_indices[3]]
        source_ip = iplist[source_node]
        frag_size = 100 if int(message_size_kb) <= 100 else 500
        same = functions.change_gvine_frag_size(frag_size, "./autotestfiles/gvine.conf.json")
        if(not same):
            functions.push_gvine_conf(IP_FILE, "./autotestfiles/gvine.conf.json")

        # Run the test
        start()
        test(source_node, source_ip, message_size_kb)
        # Wait for message to be sent
        wait_msg_time = msg_interval
        print("Waiting " + str(wait_msg_time) + " seconds")
        sleep(wait_msg_time)
        stop()
        gather_data()
        cleanup()
        param_indices = increment_parameters(param_indices, max_indices, len(max_indices))

        # Check if we are done with all tests
        if(param_indices == [0] * len(param_indices)):
            done = True


##### TESTING METHODS #####

# Function Name: initialize()
#
# Description: initialize() first checks if there are enough available nodes on
# rackspace with the prefix NODE_PREFIX to run the test on. If there are, then
# this function will do nothing and return True. If there aren't, then
# len(nodes) nodes will be created on rackspace, and this function WILL WAIT
# fail_time seconds for the nodes to boot up. If the nodes boot up before
# fail_time seconds, return True. If not, return False.
def initialize(fail_time):
    # Start nodes on Rackspace if there aren't any with the correct prefix
    if(not functions.wait_until_nodes_ready(NODE_PREFIX, len(nodes), 1)):
        functions.create_rackspace_instances(len(nodes), IMAGE_NAME, SAVE_FILE, NODE_PREFIX)

    # Wait until nodes are ready on rackspace, then return True. If the nodes
    # aren't ready after fail_time seconds, return False
    return functions.wait_until_nodes_ready(NODE_PREFIX, len(nodes), fail_time)


# Function name: setup()
#
# Preconditions:
# 1) There are len(nodes) nodes ready on rackspace (from initialize())
#
# Goals:
# 1) Do everything nodes need to run GrapeVine that doesn't need to be repeated
# 2) Setup desired topology on each rackspace node
# TODO 3) Ensure correct GrapeVine jar file is on each node
# TODO 4) Setup GrapeVine certifications between nodes
def setup():
    # Configure the topology on this computer
    topo_path = "./topologies/" + SAVE_FILE + "/"
    functions.create_dir(topo_path)
    functions.write_platform_xmls(subnets, nodes, topo_path, IP_BLACK_LIST)
    functions.write_emane_start_stop_scripts(SAVE_FILE, len(nodes))
    functions.write_scenario(subnets, nodes, topo_path)

    print("Creating stats directories")
    functions.create_dir("./stats/")
    functions.create_dir("./stats/events")
    functions.create_dir("./stats/events/" + SAVE_FILE)
    functions.create_dir("./stats/events/" + SAVE_FILE + "/nodedata/")

    print("Editing ssh config")
    functions.edit_ssh_config()
    sleep(2)

    # Add all rackspace node ip addresses to this computer's known_hosts file
    functions.add_known_hosts(iplist)

    # Create topology directory on each rackspace node
    print("Creating remote directories with ipfile: " + IP_FILE)
    functions.remote_create_dirs(SAVE_FILE, IP_FILE)
    sleep(2)

    # Copy the default config to each rackspace node
    print("Copying default config")
    functions.remote_copy_default_config(SAVE_FILE, IP_FILE)
    sleep(2)

    # Copy the scenario.eel file to each rackspace node
    print("Copying scenario.eel")
    functions.remote_copy_scenario(SAVE_FILE, iplist)

    # Copy corresponding platform file to each rackspace node
    print("Copying platform xmls")
    functions.remote_copy_platform_xmls(SAVE_FILE, iplist)

    # Copy emane_start and emane_stop scripts to each rackspace node
    print("Copying emane scripts")
    functions.remote_copy_emane_scripts(SAVE_FILE, iplist)

    # Move grapevine files from trunk folder to test folder on each rack instance
    print("Preparing GrapeVine test")
    functions.setup_grapevine(SAVE_FILE, IP_FILE)


def start():
    functions.synchronize(IP_FILE)

    print("Starting emane")
    script_name = 'emane_start.sh'
    functions.remote_emane(SAVE_FILE, IP_FILE, script_name)
    sleep(2)

    print("Deleting previous gvine log files")
    functions.delete_gvine_log_files(IP_FILE)
    sleep(2)

    print("Starting GrapeVine jar: " + JAR_FILE)
    functions.remote_start_gvine(iplist, JAR_FILE)


def test(src_node, ip, file_size_kb):
    global msg_counter
    msg_counter += 1
    msg_name = "autotestmsg_" + str(src_node + 1) + "_" + str(msg_counter) + ".txt"
    testsuite.send_gvine_message(ip, msg_name, file_size_kb, str(src_node + 1), "")

    print("Sending message")
    print("Ip: " + ip)
    print("Message name: " + msg_name)
    print("Sender node: " + str(src_node + 1))
    print("File size(kb): " + file_size_kb)


def stop():
    # Stop GrapeVine
    functions.parallel_ssh(IP_FILE, "sudo pkill java")
    # Stop EMANE
    script_file = 'emane_stop.sh'
    functions.remote_emane(SAVE_FILE, IP_FILE, script_file)


def gather_data():
    # Gather data from nodes
    print("Converting LaJollaDb to Sqlite3 on each node")
    statsuite.generate_event_dbs(iplist)
    sleep(3)

    print("Copying Sqlite3 Event databases to this computer")
    path_to_db = "/home/emane-01/test/emane/gvine/node/dbs/eventsql_copy.db"
    statsuite.copy_event_dbs(iplist, path_to_db, "./stats/events/" + SAVE_FILE + "/nodedata/")
    sleep(3)

    print("Combining Sqlite3 Event databases")
    input_dir = "./stats/events/" + SAVE_FILE + "/nodedata/"
    output_dir = "./stats/events/" + SAVE_FILE + "/"
    path_to_sql_db = statsuite.combine_event_dbs(input_dir, output_dir)


def cleanup():
    functions.parallel_ssh(IP_FILE, "rm ~/test/emane/gvine/node/autotest*")
    functions.remote_delete_events(NODE_PREFIX)


def initialize_test(max_tx_rate, num_iterations, msg_sizes_bytes, error_rates, msg_interval):
    print("Running autotest on topology: " + SAVE_FILE + " and node_prefix: " + NODE_PREFIX)
    update_config()

    # Start nodes on Rackspace if there aren't any with the correct prefix
    if(not functions.wait_until_nodes_ready(NODE_PREFIX, len(nodes), 1)):
        commands.initialize(SAVE_FILE, len(nodes))

    # Wait until nodes are ready on rackspace, then setup EMANE and Gvine
    fail_time = 1000
    if(functions.wait_until_nodes_ready(NODE_PREFIX, len(nodes), fail_time)):
        # This if statement will execute when the nodes are ready
        update_config()
        commands.setup(SAVE_FILE, subnets, nodes, iplist)
        functions.parallel_ssh(IP_FILE, "rm ~/test/emane/gvine/node/autotest*")
    else:
        print("Nodes with prefix " + NODE_PREFIX + " aren't ready")
        return
    sleep(10)

    # Do the tests
    iterate(max_tx_rate, num_iterations, msg_sizes_bytes, error_rates, msg_interval)


def iterate(max_tx_rate, num_iterations, msg_sizes_bytes, error_rates, msg_interval):
    update_config()
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
