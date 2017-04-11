# File: testsuite.py
# Author: Luke Thomas
# Date: March 31, 2017
# Description: Tests to run on topologies running on rackspace

import paramiko
import time

SUCCESS = '\033[92m'
FAIL = '\033[91m'
ENDCOLOR = '\033[0m'
    
def ping_network():
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

        key = paramiko.RSAKey.from_private_key_file("/home/joins/.ssh/id_rsa")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(node_ip, username="emane-01", pkey=key)

        print("---------- Pinging from " + node_ip + " ----------")

        for ip in ping_ips:
            command = "ping -c 1 " + ip
            stdin, stdout, stderr = ssh.exec_command(command)
            exit_status = stdout.channel.recv_exit_status()
            if(not exit_status):
                print(SUCCESS + ip + " SUCCESS" + ENDCOLOR)
            else:
                print(FAIL + ip + " FAILED" + ENDCOLOR)
        ssh.close()


def message_test_gvine(iplist, message_name, file_size):
    sender_ip = iplist[0]
    send_message(sender_ip, message_name, file_size)
    time.sleep(1)

    key = paramiko.RSAKey.from_private_key_file("/home/joins/.ssh/id_rsa")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    for ip in iplist[1:]:
        ssh.connect(ip, username="emane-01", pkey=key)
        command = "tail -c 10000 ~/test/emane/gvine/node/log_* | grep -F 'Beacon\":[{'"
        stdin, stdout, stderr = ssh.exec_command(command)
        exit_status = stdout.channel.recv_exit_status()
        if(not exit_status):
            print(SUCCESS + ip + " SUCCESS" + ENDCOLOR)
        else:
            print(FAIL + ip + " FAILED" + ENDCOLOR)
        ssh.close()

def send_message(sender_ip, message_name, file_size_kb):
    print("Sending Message from " + sender_ip)
    key = paramiko.RSAKey.from_private_key_file("/home/joins/.ssh/id_rsa")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(sender_ip, username="emane-01", pkey=key)
    
    command = "cd ~/test/emane/gvine/node/"
    command += " && dd if=/dev/urandom of=" + message_name + " bs=" + file_size_kb + "k count=1"
    command += " && java -jar gvapp.jar file " + message_name + " 1"
    stdin, stdout, stderr = ssh.exec_command(command)
    ssh.close()
    print("Message sent.\n")
