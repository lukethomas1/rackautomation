

# System Imports
from os import path

# Local Imports
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
IP_BLACK_LIST = config.IP_BLACK_LIST
JAR_FILE = config.JAR_FILE
RACK_KEY = config.RACK_KEY

# Configuration variables
save = None
json = None
subnets = None
nodes = None
nodeipdict = None
node_objects = None

# Parameter variables
transmit_rate = None
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
    global node_objects
    functions.set_topology(SAVE_FILE, NODE_PREFIX)
    config_result = functions.load_data()
    save = config_result['save']
    json = config_result['json']
    subnets = config_result['subnets']
    nodes = config_result['nodes']
    nodeipdict = config_result['nodeipdict']
    node_objects = commands.get_assigned_nodes()


def initialize_parameters(max_tx, num_iter, msg_sizes, err_rates, msg_int, init_indices):
    global transmit_rate
    global num_iterations
    global msg_sizes_bytes
    global error_rates
    global msg_interval
    global initial_indices
    global IP_FILE
    transmit_rate = max_tx
    num_iterations = num_iter
    msg_sizes_bytes = msg_sizes
    error_rates = err_rates
    msg_interval = msg_int
    initial_indices = init_indices


def increment_parameters(current, maxx, length):
    increment_next = True
    for index in range(length):
        if(increment_next):
            current[index] += 1
            if(current[index] == maxx[index]):
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
        commands.clean(node_objects, 3)
        setup(need_configure)
    update_config()
    commands.stats_directories(SAVE_FILE)

    # Stop and clean in case we did a test before this
    stop()
    commands.clean(node_objects, 2)

    # Do the stuff that needs to be done before autotesting no matter what
    necessary_setup()

    # Print starting details
    print_start_finish(starting=True)

    # Parameters with indices: Iteration, Source Node, Message Size, Error Rate
    param_indices = initial_indices
    # max_indices = [num_iterations, len(nodes), len(msg_sizes_bytes), len(error_rates)]
    max_indices = [num_iterations, 1, len(msg_sizes_bytes), len(error_rates)]
    done = False
    errors_in_a_row = 0
    while(not done):
        try:
            print("Indices for this test: " + str(param_indices))
            # Set up the parameters for this test
            iteration = param_indices[0]
            source_node = param_indices[1]
            message_size_kb = str(int(int(msg_sizes_bytes[param_indices[2]]) / 1024))
            if(param_indices[3] > 0):
                global previous_error_rate
                previous_error_rate = error_rates[param_indices[3] - 1]
            error_rate = error_rates[param_indices[3]]
            frag_size = 500000
            prepare_test(error_rate, frag_size)
            sleep(2)

            # Run the test
            start_time = time()
            start()
            print("Sleeping 15 seconds for GrapeVine to initialize on nodes")
            sleep(15)
            file_name = "autotestmsg_" + str(source_node + 1) + "_" + str(msg_counter) + ".txt"
            test(source_node, message_size_kb, file_name)

            # Calculate the maximum wait time for this test
            estimated_hop_time = functions.estimate_hop_time(transmit_rate, int(message_size_kb) *
                                                             1024, frag_size)
            wait_msg_time = estimated_hop_time * (len(subnets) + 2) * (1 / (1 - error_rate))
            wait_msg_time = max([wait_msg_time, 25])
            print("Estimated hop time: " + str(estimated_hop_time))
            print("Maximum Wait Time: " + str(wait_msg_time))

            # Wait for message to be sent
            test_success = testsuite.wait_for_message_received(file_name, node_objects,
                                                               source_node + 1, wait_msg_time)

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
            setup()
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
"""
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
    """
def setup():
    commands.setup(SAVE_FILE, subnets, nodes, node_objects)


def necessary_setup():
    functions.change_gvine_tx_rate(transmit_rate, "./autotestfiles/gvine.conf.json")

    global error_rate_templates
    error_rate_templates = functions.generate_error_rate_commands(subnets, nodes)


def start():
    commands.start(SAVE_FILE, node_objects)


def prepare_test(error_rate, frag_size):
    global previous_error_rate
    global node_objects
    # Set the fragment size in the local gvine.conf.json, push to nodes if it changed
    config_file = "gvine.conf.json"
    config_path = "./autotestfiles/" + config_file
    same = functions.change_gvine_frag_size(frag_size, config_path)
    if(not same):
        commands.push_config(node_objects, file_name=config_file, dest_file_name=config_file)

    # Set the error rate
    if(error_rate != previous_error_rate):
        if(previous_error_rate != 0):
            for index in range(len(node_objects)):
                templates = error_rate_templates[index + 1]
                for template in templates:
                    command = template.format(action="-D", rate=str(error_rate))
                    for node in node_objects:
                        print("Removing error_rate " + str(previous_error_rate) + " from " +
                              node.name)
                        node.execute_command(command)
        if(error_rate != 0):
            for index in range(len(node_objects)):
                templates = error_rate_templates[index + 1]
                for template in templates:
                    command = template.format(action="-A", rate=str(error_rate))
                    for node in node_objects:
                        print("Setting error_rate " + str(error_rate) + " on " + node.name)
                        node.execute_command(command)
        previous_error_rate = error_rate


def test(src_index, file_size_kb, msg_name):
    global msg_counter
    msg_counter += 1
    commands.test_message(node_objects, node_index=src_index, message_name=msg_name,
                          file_size=file_size_kb, do_wait=False) #TODO

    print("Sending message")
    print("Message name: " + msg_name)
    print("Sender node: " + str(src_index + 1))
    print("File size(kb): " + file_size_kb)


def handle_test_failure():
    print("Handling test failure (currently does nothing)")


def stop():
    print("Stopping GrapeVine then EMANE")
    global node_objects
    commands.stop(node_objects)


def gather_data():
    commands.stats_tcpdump(node_objects, "autotest_" + SAVE_FILE)


def write_test_params(param_indices, folder_path):
    """Write test parameters to "params" file at folder_path

    :param param_indices: Indices of the current test parameters, in the format
    param_indices = [iteration_index, sender_node_index, msg_size_index, error_rate_index]
    :param folder_path: Folder path to write the "params" file to
    """
    iteration = param_indices[0] + 1
    sender_node = param_indices[1] + 1
    msg_size = msg_sizes_bytes[param_indices[2]]
    error_rate = error_rates[param_indices[3]]
    param_path = folder_path + "params" if folder_path[-1] == "/" else folder_path + "/params"
    param_description = [
        "Iteration: " + str(iteration),
        "Sender Node: " + str(sender_node),
        "Msg Size: " + str(msg_size),
        "Error Rate: " + str(error_rate),
        "Tx Rate: " + str(transmit_rate),
        "Topology: " + SAVE_FILE,
        "Rackspace Image: " + IMAGE_NAME
    ]
    with open(param_path, "w") as param_file:
        for line in param_description:
            param_file.write(line + "\n")


def cleanup():
    commands.clean(node_objects, 2)


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
    global transmit_rate
    print("Topology: " + save)
    print("Rackspace prefix: " + NODE_PREFIX)
    print("Number of iterations: " + str(num_iterations))
    print("Number of nodes: " + str(len(nodes)))
    print("Message sizes: " + str(msg_sizes_bytes))
    print("Error rates: " + str(error_rates))
    print("Max transmission rate: " + str(transmit_rate))
    print()
