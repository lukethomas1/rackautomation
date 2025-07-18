# File: testsuite.py
# Author: Luke Thomas
# Date: March 31, 2017
# Description: Tests to run on topologies running on rackspace

# System Imports
from time import sleep, time
from os import path
import threading
import queue

# 3rd Party Imports
from paramiko import SSHClient, AutoAddPolicy, RSAKey

# Local Imports
from functions import create_dir, generate_rack_to_topo_dict, print_success_fail
from statsuite import get_trailing_number

SUCCESS = '\033[92m'
FAIL = '\033[91m'
ENDCOLOR = '\033[0m'
    
def ping_network(node_objects, username="emane-01"):
    network_file = open("./tests/pingtest/network", "r")
    connections = network_file.readlines()
    network_file.close()

    for connection in connections:
        # Get rid of newline at the end of the string
        connection = connection.rstrip()
        # Split string at spaces into list of strings
        derp = connection.split(" ")
        # Node to ssh to
        node_ip = derp[0]
        # Nodes to ping to from the sshed node
        ping_ips = derp[1:]

        print("---------- Pinging from " + node_ip + " ----------")

        loc = path.expanduser("~/.ssh/id_rsa")
        key = RSAKey.from_private_key_file(loc)
        ssh = SSHClient()
        ssh.set_missing_host_key_policy(AutoAddPolicy())
        ssh.connect(node_ip, username=username, pkey=key)

        for ip in ping_ips:
            command = "ping -c 1 " + ip
            stdin, stdout, stderr = ssh.exec_command(command)
            exit_status = stdout.channel.recv_exit_status()
            node_index = int(ip[-1]) - 1
            this_ip = node_objects[node_index].ip
            if(not exit_status):
                print(this_ip + " " + SUCCESS + ip + " SUCCESS" + ENDCOLOR)
            else:
                print(this_ip + " " + FAIL + ip + " FAILED" + ENDCOLOR)
        ssh.close()


def message_test_gvine(iplist, message_name, file_size, username):
    sender_ip = iplist[0]
    send_gvine_message(sender_ip, message_name, file_size, "1", "")


def check_network_receiving(iplist, sender_node):
    loc = path.expanduser("~/.ssh/id_rsa")
    key = RSAKey.from_private_key_file(loc)
    ssh = SSHClient()
    ssh.set_missing_host_key_policy(AutoAddPolicy())
    sender_index = sender_node - 1

    for ip_index in range(len(iplist)):
        ip = iplist[ip_index]
        if(ip_index != sender_index):
            check_message_receiving(ip, ssh, key)


def check_message_receiving(ip, ssh, key):
    ssh.connect(ip, username="emane-01", pkey=key)
    command = "tail -c 100000 ~/test/emane/gvine/node/log_* | grep -F 'Beacon\":[{'"
    stdin, stdout, stderr = ssh.exec_command(command)
    exit_status = stdout.channel.recv_exit_status()
    ssh.close()
    print_success_fail(not exit_status, ip)
    return not exit_status


def wait_for_message_received(file_name, node_objects, sender_id, wait_time, sleep_time=5,
                              do_print=True):
    start_time = time()
    received = False
    try:
        while(not received and (time() - start_time) < wait_time):
            sleep(sleep_time)
            elapsed_time = time() - start_time
            print("\nChecking if message was received: " + str(elapsed_time) + " seconds")
            received = check_network_received(file_name, node_objects, sender_id, do_print=do_print)
    except KeyboardInterrupt:
        pass
    return received


def check_network_received(file_name, node_objects, sender_id, do_print=True):
    threads = []
    return_queue = queue.Queue()
    for node in node_objects:
        if node.id != sender_id:
            new_thread = threading.Thread(target=lambda q: q.put(node.name + " " + str(
                node.check_msg_received(file_name))), args=(return_queue,))
            threads.append(new_thread)
            new_thread.start()
    for t in threads:
        t.join()

    received_dict = {}
    while not return_queue.empty():
        rtn_string = return_queue.get()
        node_name = rtn_string.split(" ")[0]
        not_received = rtn_string.split(" ")[1]
        received = not int(not_received)
        received_dict[node_name] = received

    return_value = True
    for node_name in sorted(received_dict.keys(), key=lambda n: get_trailing_number(n)):
        received = received_dict[node_name]
        if do_print:
            print_success_fail(received, node_name + " ")
        if not received:
            return_value = False
    return return_value


def check_message_received(file_name, ip, node_name, node_label, ssh, key):
    ssh.connect(ip, username="emane-01", pkey=key)
    command = "ls ~/test/emane/gvine/node/data/" + file_name
    stdin, stdout, stderr = ssh.exec_command(command)
    exit_status = stdout.channel.recv_exit_status()
    ssh.close()
    str = node_label + " (" + node_name + " on Rackspace): "
    print_success_fail(not exit_status, str)
    return not exit_status


def print_success_fail(success, string):
    if(success):
        print(SUCCESS + string + " SUCCESS" + ENDCOLOR)
    else:
        print(FAIL + string + " FAILED" + ENDCOLOR)


def send_gvine_message(sender_ip, message_name, file_size_kb, send_node_num, receive_node_num):
    print("Sending message on GrapeVine from " + sender_ip)
    loc = path.expanduser("~/.ssh/id_rsa")
    key = RSAKey.from_private_key_file(loc)
    ssh = SSHClient()
    ssh.set_missing_host_key_policy(AutoAddPolicy())
    ssh.connect(sender_ip, username="emane-01", pkey=key)

    # Make the text file to be sent
    command = "cd ~/test/emane/gvine/node/"
    command += " && dd if=/dev/urandom of=" + message_name + " bs=" + file_size_kb + "k count=1"
    stdin, stdout, stderr = ssh.exec_command(command)

    exit_status = 1
    while(exit_status == 1):
        print("Sleeping 5 seconds to wait for " + message_name + " to be created")
        sleep(5)
        check_exists_command = "ls ~/test/emane/gvine/node/" + message_name
        stdin, stdout, stderr = ssh.exec_command(check_exists_command)
        exit_status = stdout.channel.recv_exit_status()

    # Send the text file
    command = "cd ~/test/emane/gvine/node/"
    if(not receive_node_num):
      command += " && java -jar gvapp.jar file " + message_name + " " + send_node_num
    else:
      command += (" && java -jar gvapp.jar file " + message_name + " " +
                  send_node_num + " " + receive_node_num)
    stdin, stdout, stderr = ssh.exec_command(command)
    ssh.close()
    print("Message sent.\n")


def send_norm_message(sender_ip, message_name, file_size_kb):
    create_dir("./tests/")
    create_dir("./tests/norm_messages")
    print("Sending message on Norm from " + sender_ip)
    loc = path.expanduser("~/.ssh/id_rsa")
    key = RSAKey.from_private_key_file(loc)
    ssh = SSHClient()
    ssh.set_missing_host_key_policy(AutoAddPolicy())
    ssh.connect(sender_ip, username="emane-01", pkey=key)
    
    command = "cd ~/norm/bin/outbox/"
    command += " && dd if=/dev/urandom of=" + message_name + " bs=" + file_size_kb + "k count=1"
    stdin, stdout, stderr = ssh.exec_command(command)
    ssh.close()
    print("Message sent.\n")
    with open("./tests/norm_messages/start.txt", 'a') as file:
        file.write(str(time()) + "\n")


def norm_monitor(node_ip, file_name):
    loc = path.expanduser("~/.ssh/id_rsa")
    key = RSAKey.from_private_key_file(loc)
    ssh = SSHClient()
    ssh.set_missing_host_key_policy(AutoAddPolicy())
    ssh.connect(node_ip, username="emane-01", pkey=key)
    exit_status = 1

    while(exit_status):
        command = "ls ~/norm/bin/outbox/" + file_name
        stdin, stdout, stderr = ssh.exec_command(command)
        exit_status = stdout.channel.recv_exit_status()
        sleep(1)
    ssh.close()
    with open("./tests/norm_messages/start.txt", 'r') as file:
        start_time = file.readlines()[-1].rstrip('\n')
        print("Start time: " + start_time)
        start_time = float(start_time)
    with open("./tests/norm_messages/delay.txt", 'a') as file:
        delay = str(time() - start_time)
        file.write("Delay " + file_name + ": " + delay + "\n")
    print("Message " + file_name + " received on " + node_ip + " with delay " + delay)
