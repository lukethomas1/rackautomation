#!/usr/bin/env python3

# File: node.py
# Author: Luke Thomas
# Date: August 29, 2017
# Description: Superclass for each kind of node (rackspace node, pi node)

# System Imports
from os import path
from subprocess import call, Popen, DEVNULL
from time import sleep, time
from re import search

# Third Party Imports

# Local Imports
import functions
from config import IP_BLACK_LIST

class Node:
    def __init__(self, name, user_name, id, ip, platform, gvine_path, member_subnets, iface_prefix):
        """

        :param name: name of the node as it shows on rackspace, default node#
        :param user_name: username of the remote host
        :param id: index number of the node
        :param ip: ip of the remote host
        :param platform: which platform the node is, pi or rack
        :param gvine_path: path to the gvine test folder on the remote host, has "/" at the end
        :param member_subnets: list of subnets the node is in
        :param iface_prefix: prefix of the interfaces that gvine will run on, used when parsing
        pcap files
        """
        self.name = name
        self.user_name = user_name
        self.id = id
        self.ip = ip
        self.platform = platform
        self.gvine_path = gvine_path
        self.member_subnets = member_subnets
        self.iface_prefix = iface_prefix

    def add_to_known_hosts(self):
        loc = path.expanduser("~/.ssh/known_hosts")
        command = "ssh-keygen -R " + self.ip
        call(command, shell=True, stdout=DEVNULL)
        command = "ssh-keyscan -H " + self.ip + " >> " + loc
        call(command, shell=True, stdout=DEVNULL)
        sleep(1)

    def clean_gvine(self, amount):
        command = "cd " + self.gvine_path + " && rm -rf "
        if amount == 1:
            command += (
                "gvine.msg* gvine.frag* " +
                "gvine.sub* delay.txt ack.txt *.cer SeqNbr.txt send.txt received.txt " +
                "statistic.db log* eventlogs/* dbs/* data/*"
            )
        elif amount == 2:
            command += "$(ls -I '*.jar' -I '*.json' -I '*.cer' -I '*pki.db*')"
        elif amount == 3:
            command += "$(ls -I '*.jar' -I '*.json')"
        functions.remote_execute(command, self.ip, self.user_name)

    def delete_gvine_log_file(self):
        command = "cd " + self.gvine_path + " && rm log_*"
        functions.remote_execute(command, self.ip, self.user_name)

    def remote_delete_events(self):
        command = "cd " + self.gvine_path + " && rm ./dbs/*"
        functions.remote_execute(command, self.ip, self.user_name)

    def remote_start_gvine(self, jar_name):
        command = "cd " + self.gvine_path + " && java -jar " + jar_name + " node" + str(self.id) \
                  + " 500 >> log_node" + str(self.id) + ".txt &"
        functions.remote_execute(command, self.ip, self.user_name)

    def remote_start_refactor(self, jar_name, config_name):
        command = "cd " + self.gvine_path + " && java -jar " + jar_name + " node" + str(self.id) \
                  + " " + config_name + " &> log_node" + str(self.id) + ".txt &"
        functions.remote_execute(command, self.ip, self.user_name)

    ##### GRAPEVINE GVPKI CERTS #####

    def generate_cert(self):
        print("Generating cert on " + self.name)
        command = "cd " + self.gvine_path + " && java -jar gvpki.jar generate node" + str(self.id)
        functions.remote_execute(command, self.ip, self.user_name)

    def pull_cert(self):
        print("Pulling cert from " + self.name)
        from_path = self.user_name + "@" + self.ip + ":" + self.gvine_path + "node" + str(
            self.id) + ".cer"
        to_path = "./keystore/"
        Popen(['scp', from_path, to_path])

    def push_certs(self, path_to_certs):
        print("Pushing cert to " + self.name)
        command = "scp " + path_to_certs + " " + self.user_name + "@" + self.ip + ":" + \
                  self.gvine_path
        call(command, shell=True, stdout=DEVNULL)

    def load_certs(self, num_nodes):
        print("Loading certs on " + self.name)
        command = (
            "cd {} && for((i=1; i<={}; i=i+1)); do java -jar gvpki.jar " +
            "node node" + str(self.id) + " load node$i; done"
        ).format(self.gvine_path, num_nodes)
        functions.remote_execute(command, self.ip, self.user_name)

    ##### PARAMETERS FOR AUTOTEST #####

    def remote_set_error_rate(self, error_rate, command_template):
        command = command_template.format(action="-A", rate=str(error_rate))
        functions.remote_execute(command, self.ip, self.user_name)

    def remote_remove_error_rate(self, error_rate, command_template):
        command = command_template.format(action="-D", rate=str(error_rate))
        functions.remote_execute(command, self.ip, self.user_name)

    ##### BASIC FUNCTIONALITY #####

    def push_file(self, src_path, dest_path, dest_file_name=None):
        if dest_file_name:
            if dest_path[-1] == "/":
                dest_path = dest_path + dest_file_name
            else:
                dest_path = dest_path + "/" + dest_file_name
        print("Pushing " + src_path + " to " + self.name + " as " + dest_path)
        command = "scp " + src_path + " " + self.user_name + "@" + self.ip + ":" + dest_path
        call(command, shell=True, stdout=DEVNULL)

    def pull_file(self, remote_path, local_path):
        command = "scp " + self.user_name + "@" + self.ip + ":" + remote_path +\
                  " " + local_path
        call(command, shell=True)

    def remote_create_dir(self, path_to_folder):
        command = "mkdir " + path_to_folder
        functions.remote_execute(command, self.ip, self.user_name)

    def remote_delete_path(self, path_to_delete, is_dir=False):
        if not is_dir:
            command = "rm " + path_to_delete
        else:
            command = "rm -r " + path_to_delete
        functions.remote_execute(command, self.ip, self.user_name)

    ##### TESTING #####

    def make_test_file(self, msg_name, size_kb):
        command = (
            "cd " + self.gvine_path + " && dd if=/dev/urandom of=" + msg_name + " bs=" +
            size_kb + "k count=1"
        )
        functions.remote_execute(command, self.ip, self.user_name)

        exit_status = 1
        timer = time()
        while(exit_status == 1 and time() - timer < 25):
            print("Sleeping 5 seconds to wait for " + msg_name + " to be created")
            sleep(5)
            command = "ls " + self.gvine_path + msg_name
            exit_status = functions.remote_execute(command, self.ip, self.user_name)

    def send_gvine_file(self, msg_name, receive_node_num=None):
        print("Sending message on GrapeVine from " + self.name)
        command = "cd " + self.gvine_path
        if(not receive_node_num):
            command += " && java -jar gvapp.jar file " + msg_name + " " + str(self.id)
        else:
            command += (" && java -jar gvapp.jar file " + msg_name + " " +
                        str(self.id) + " " + receive_node_num)
        functions.remote_execute(command, self.ip, self.user_name)
        print("Message sent.\n")

    def send_refactor_file(self, msg_name, channel, port=22124):
        print("Sending message on GrapeVine from " + self.name)
        command = "cd " + self.gvine_path
        command += " && java -jar GvineApiClient.jar -p " + str(port) + " sendfile " + channel + \
                   " " + msg_name
        functions.remote_execute(command, self.ip, self.user_name)
        print("Message sent.\n")

    def check_msg_received(self, file_name):
        command = "ls " + self.gvine_path + "data/" + file_name
        exit_status = functions.remote_execute(command, self.ip, self.user_name)
        return exit_status

    def start(self, jar_name, save=None):
        self.remote_delete_path(self.gvine_path + "log*")
        self.remote_start_gvine(jar_name)

    def stop_all(self, save=None):
        self.stop_gvine()
        functions.remote_execute("sudo pkill norm && sudo pkill tcpdump",
                                 self.ip, self.user_name)

    def stop_gvine(self):
        jar_name = "gvapp.jar"
        command = "java -jar " + jar_name + " stop " + str(self.id)
        functions.remote_execute(command, self.ip, self.user_name)
        functions.remote_execute("sudo pkill java", self.ip, self.user_name)

    def refactor_api_command(self, api_command, client_jar, port=22124):
        command = "cd " + self.gvine_path + " && java -jar " + client_jar + " -p " + str(port) + \
                  " " + api_command
        exit_status = functions.remote_execute(command, self.ip, self.user_name)
        if (exit_status == 150):
            print(self.name + " " + api_command + ", False")
        elif (exit_status == 151):
            print(self.name + " " + api_command + ", True")
        elif (exit_status == 152):
            print(self.name + " " + api_command + ", Invalid Command")
        else:
            print("Exit status: " + str(exit_status))

    ##### LOGGABLE EVENTS #####

    def generate_event_db(self):
        command = "cd " + self.gvine_path + "eventlogs/ && ls -dlt */"
        stdout_read = functions.remote_execute_stdout(command, self.ip, self.user_name)
        target_dir = stdout_read.splitlines()[0].split(" ")[-1]

        command = "cd " + self.gvine_path + " && java -jar dbreader.jar eventlogs/" + target_dir \
                  + " LaJollaCove eventsql"
        functions.remote_execute(command, self.ip, self.user_name)

    def copy_event_db(self, save_file):
        src = self.user_name + "@" + self.ip + ":" + self.gvine_path + "dbs/eventsql_copy.db"
        dest = "./stats/events/" + save_file + "/nodedata/eventsql" + str(self.id) + ".db"
        functions.execute_shell("scp " + src + " " + dest)

    ##### TCPDUMP #####

    def start_tcpdump(self):
        commands = []
        for index in range(len(self.member_subnets)):
            iface = self.iface_prefix + str(index + 1)
            print("Starting tcpdump on " + self.name + " and iface " + iface)
            command = "sudo nohup tcpdump -i " + iface + " -n udp -w " + self.gvine_path + iface \
                      + ".pcap &>/dev/null &"
            commands.append(command)
        functions.remote_execute_commands(commands, self.ip, self.user_name)

    def retrieve_pcaps(self, pcap_folder):
        for index in range(1, len(self.member_subnets) + 1):
            iface = self.iface_prefix + str(index)
            command = "scp " + self.user_name + "@" + self.ip + ":" + self.gvine_path + \
                      iface + ".pcap " + pcap_folder + self.name + "_" + iface + ".pcap"
            functions.execute_shell(command)

    def get_ipmap(self):
        ipmap = {}
        for index in range(1, len(self.member_subnets) + 1):
            iface = self.iface_prefix + str(index)
            iface_ip = self.get_iface_ip(iface)
            if iface_ip == "" or iface_ip is None:
                number = self.member_subnets[index - 1]
                ip_guess = "11.0." + str(number) + "." + str(self.id)
                ipmap[ip_guess] = self.id
            else:
                ipmap[iface_ip] = self.id
        return ipmap

    def get_iface_ip(self, iface):
        command = "ifconfig " + iface + " | grep 'inet '"
        output = functions.remote_execute_stdout(command, self.ip, self.user_name)
        output = search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', output)
        if output is not None:
            output = output.group()
        return output

    def pull_log_file(self, folder_name):
        remote_path = self.gvine_path + "log_node" + str(self.id) + ".txt"
        self.pull_file(remote_path, folder_name)
