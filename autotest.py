import config
import commands
import functions
import testsuite
import statsuite
from time import sleep,time

# Constants defined in config.py
NODE_PREFIX = config.NODE_PREFIX
SAVE_FILE = config.SAVE_FILE
IMAGE_NAME = config.IMAGE_NAME
IP_FILE = config.IP_FILE
IP_BLACK_LIST = config.IP_BLACK_LIST
JAR_FILE = config.JAR_FILE
RACK_KEY = config.RACK_KEY

# Configuration variables
save = None
json = None
subnets = None
nodes = None
iplist = None
nodeipdict = None

# Parameter variables
max_tx_rate = None
num_iterations = None
msg_sizes_bytes = None
error_rates = None
msg_interval = None
initial_indices = [0, 0, 0, 0]

# Other global variables
msg_counter = 0
previous_error_rate = 0
error_rate_templates = {}

def update_config():
    global save
    global json
    global subnets
    global nodes
    global iplist
    global nodeipdict
    functions.set_topology(SAVE_FILE, NODE_PREFIX)
    config_result = functions.load_data()
    save = config_result['save']
    json = config_result['json']
    subnets = config_result['subnets']
    nodes = config_result['nodes']
    iplist = config_result['iplist']
    nodeipdict = config_result['nodeipdict']


def initialize_parameters(max_tx, num_iter, msg_sizes, err_rates, msg_int, init_indices):
    global max_tx_rate
    global num_iterations
    global msg_sizes_bytes
    global error_rates
    global msg_interval
    global initial_indices
    max_tx_rate = max_tx
    num_iterations = num_iter
    msg_sizes_bytes = msg_sizes
    error_rates = err_rates
    msg_interval = msg_int
    initial_indices = init_indices


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


def run(need_setup, need_configure):
    if(need_setup):
        update_config()
        initialize(fail_time=9999)
        update_config()
        stop()
        functions.clean_nodes(IP_FILE)
        setup(need_configure)
    update_config()
    commands.stats_directories(SAVE_FILE)

    # Stop and clean in case we did a test before this
    stop()
    functions.clean_node_data(IP_FILE)

    # Do the stuff that needs to be done before autotesting no matter what
    necessary_setup()

    # Print starting details
    print_start_finish(starting=True)

    # Parameters with indices: Iteration, Source Node, Message Size, Error Rate
    param_indices = initial_indices
    max_indices = [num_iterations, len(nodes), len(msg_sizes_bytes), len(error_rates)]
    # max_indices = [num_iterations, 2, len(msg_sizes_bytes), len(error_rates)]
    done = False
    errors_in_a_row = 0
    while(not done):
        try:
            print("Indices for this test: " + str(param_indices))
            # Set up the parameters for this test
            iteration = param_indices[0]
            source_node = param_indices[1]
            message_size_kb = str(int(int(msg_sizes_bytes[param_indices[2]]) / 1000))
            error_rate = error_rates[param_indices[3]]
            source_ip = iplist[source_node]
            frag_size = 100 if int(message_size_kb) <= 100 else 500
            frag_size = 50000
            prepare_test(iteration, source_node, message_size_kb, error_rate, source_ip,
                         frag_size)
            sleep(2)

            # Run the test
            start_time = time()
            start(tcpdump=True)
            print("Sleeping 15 seconds for GrapeVine to initialize on nodes")
            sleep(15)
            file_name = "autotestmsg_" + str(source_node + 1) + "_" + str(msg_counter) + ".txt"
            test(source_node, source_ip, message_size_kb, file_name)

            # Calculate the maximum wait time for this test
            estimated_hop_time = functions.estimate_hop_time(max_tx_rate, int(message_size_kb) *
                                                             1000, frag_size)
            wait_msg_time = estimated_hop_time * len(subnets) * 2
            wait_msg_time = max([wait_msg_time, 25])
            print("Estimated hop time: " + str(estimated_hop_time))
            print("Maximum Wait Time: " + str(wait_msg_time))

            # Wait for message to be sent
            inv_ipdict = functions.invert_dict(nodeipdict)
            test_success = testsuite.wait_for_message_received(file_name, source_node + 1, iplist,
                                                     inv_ipdict, nodes, wait_msg_time)

            '''
            # Delay tolerant testing
            first_msg_time = time()
            print("Elapsed time: " + str(first_msg_time - start_time))
            sleep_time = 165 - (first_msg_time - start_time)
            print("Waiting " + str(sleep_time) + " seconds for nodes to disconnect")
            if(sleep_time > 0):
                sleep(sleep_time)

            file_name = "autotestmsg2_" + str(source_node + 1) + "_" + str(msg_counter) + ".txt"
            test(source_node, source_ip, message_size_kb, file_name)
            inv_ipdict = functions.invert_dict(nodeipdict)
            wait_msg_time = 500
            test_success = testsuite.wait_for_message_received(file_name, source_node + 1, iplist,
                                                               inv_ipdict, nodes, wait_msg_time)
            '''

            # Handle test failure
            if(not test_success):
                handle_test_failure()

            # Stop Gvine then EMANE
            stop()
            # Gather event data
            if(test_success):
                gather_data()
            # Remove test data from nodes
            cleanup()
            sleep(3)
            # Increment parameters
            if(test_success):
                param_indices = increment_parameters(param_indices, max_indices, len(max_indices))
                errors_in_a_row = 0
                # Check if we are done with all tests
                if(param_indices == [0] * len(param_indices)):
                    print_start_finish(starting=False)
                    done = True
            else:
                print("There was a failure during this test, retesting with the same parameters")
                errors_in_a_row += 1

        except KeyboardInterrupt:
            stop()
            exit()
        except Exception as err:
            print("BUG: " + str(err))
            errors_in_a_row += 1

        # Re-setup the nodes if there are multiple errors in a row
        if(errors_in_a_row == 5):
            print("There were 5 errors in a row, re-setting up the nodes")
            update_config()
            setup(False)
            update_config()
            errors_in_a_row = 0


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
        functions.create_rackspace_instances(len(nodes), IMAGE_NAME, RACK_KEY, SAVE_FILE,
                                             NODE_PREFIX)

    # Wait until nodes are ready on rackspace, then return True. If the nodes
    # aren't ready after fail_time seconds, return False
    return functions.wait_until_nodes_ready(NODE_PREFIX, len(nodes), fail_time)


# Configure the topology on this computer
def configure():
    topo_path = "./topologies/" + SAVE_FILE + "/"
    functions.create_dir(topo_path)
    functions.write_platform_xmls(subnets, nodes, topo_path, IP_BLACK_LIST)
    functions.write_emane_start_stop_scripts(SAVE_FILE, len(nodes))
    functions.write_scenario(subnets, nodes, topo_path)


# Function name: setup()
#
# Preconditions:
# 1) There are len(nodes) nodes ready on rackspace (from initialize())
#
# Goals:
# 1) Do everything nodes need to run GrapeVine that doesn't need to be repeated
# 2) Setup desired topology on each rackspace node
# 3) Setup GrapeVine certifications between nodes
def setup(need_configure):
    if(need_configure):
        configure()

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

    # Remove all non directory or .jar files
    functions.clean_nodes(IP_FILE)

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

    node_certs(iplist)


def necessary_setup():
    functions.change_gvine_tx_rate(max_tx_rate, "./autotestfiles/gvine.conf.json")

    #global error_rate_templates
    #error_rate_templates = functions.generate_error_rate_commands(subnets, nodes, error_rates)


def node_certs(iplist):
    # Generate cert on each node
    print("Generating certs")
    path_to_jar = "/home/emane-01/test/emane/gvine/node/"
    functions.generate_certs(iplist, path_to_jar)
    sleep(3)
    # Pull cert down from each node
    print("Pulling certs")
    functions.pull_certs(iplist)
    sleep(2)
    # Push all certs to each node
    print("Pushing certs")
    path_to_certs = "./keystore/*"
    functions.push_certs(IP_FILE, path_to_certs, path_to_jar)
    sleep(2)
    # Load all certs on each node
    print("Loading certs")
    functions.load_certs(path_to_jar, iplist)


def start(tcpdump):
    functions.synchronize(IP_FILE)

    print("Starting emane")
    script_name = 'emane_start.sh'
    functions.remote_emane(SAVE_FILE, IP_FILE, script_name)
    sleep(2)

    if(tcpdump):
        print("Logging subnet traffic with tcpdump")
        functions.subnet_tcpdump(nodes, subnets, NODE_PREFIX, nodeipdict)

    print("Deleting previous gvine log files")
    functions.delete_gvine_log_files(IP_FILE)
    sleep(2)

    print("Starting GrapeVine jar: " + JAR_FILE)
    functions.remote_start_gvine(iplist, JAR_FILE)


def prepare_test(iteration, source_node, message_size_kb, error_rate, source_ip, frag_size):
    # Set the fragment size in the local gvine.conf.json, push to nodes if it changed
    same = functions.change_gvine_frag_size(frag_size, "./autotestfiles/gvine.conf.json")
    if(not same):
        functions.push_gvine_conf(IP_FILE, "./autotestfiles/gvine.conf.json")

    # Set the error rate
    global previous_error_rate
    if(error_rate != previous_error_rate):
        if(previous_error_rate != 0):
            for index in range(len(iplist)):
                ip = iplist[index]
                templates = error_rate_templates[index + 1]
                for template in templates:
                    functions.remote_remove_error_rate(ip, previous_error_rate, template)
        previous_error_rate = error_rate


def test(src_index, ip, file_size_kb, msg_name):
    global msg_counter
    msg_counter += 1
    testsuite.send_gvine_message(ip, msg_name, file_size_kb, str(src_index + 1), "")

    print("Sending message")
    print("Ip: " + ip)
    print("Message name: " + msg_name)
    print("Sender node: " + str(src_index + 1))
    print("File size(kb): " + file_size_kb)


def handle_test_failure():
    print("Handling test failure (currently does nothing)")


def stop():
    print("Stopping GrapeVine then EMANE")
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
    statsuite.clear_node_event_data(SAVE_FILE)
    path_to_db = "/home/emane-01/test/emane/gvine/node/dbs/eventsql_copy.db"
    statsuite.copy_event_dbs(iplist, path_to_db, "./stats/events/" + SAVE_FILE + "/nodedata/")
    sleep(3)

    print("Combining Sqlite3 Event databases")
    input_dir = "./stats/events/" + SAVE_FILE + "/nodedata/"
    output_dir = "./stats/events/" + SAVE_FILE + "/"
    path_to_sql_db = statsuite.combine_event_dbs(input_dir, output_dir)

    commands.stats_tcpdump(iplist)


def cleanup():
    functions.parallel_ssh(IP_FILE, "rm ~/test/emane/gvine/node/autotest*")
    functions.remote_delete_events(IP_FILE, NODE_PREFIX)


def print_start_finish(starting):
    print()
    if(starting):
        print("Starting testing with parameters:")
    else:
        print("Finished testing with parameters:")
    print("---------------------------------")
    print_details()

def print_details():
    global save
    global num_iterations
    global nodes
    global msg_sizes_bytes
    global error_rates
    global max_tx_rate
    print("Topology: " + save)
    print("Rackspace prefix: " + NODE_PREFIX)
    print("Number of iterations: " + str(num_iterations))
    print("Number of nodes: " + str(len(nodes)))
    print("Message sizes: " + str(msg_sizes_bytes))
    print("Error rates: " + str(error_rates))
    print("Max transmission rate: " + str(max_tx_rate))
    print()
