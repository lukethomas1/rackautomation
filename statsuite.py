# File: statsuite.py
# Author: Luke Thomas
# Date: April 6, 2017
# Description: This file is used for stats from emane tests

# System Imports
from glob import glob
from os import path, system
from math import ceil
from re import search, split
from subprocess import Popen
from sqlite3 import connect, IntegrityError, DatabaseError
from time import gmtime, strftime, sleep

# 3rd Party Imports
from paramiko import AutoAddPolicy, RSAKey, SSHClient
import plotly
import pickle

# Local imports
from functions import create_dir
import packetsuite

# Global Constants
PACKETS_LIST = ["beacon", "gvine", "handshake", "babel"]
PACKET_BEACON = 1
PACKET_GVINE = 2
PACKET_HANDSHAKE = 3
PACKET_BABEL = 4


##### General SQLITE Functions #####

def get_sql_data(path_to_db, table_name):
    main_connection = connect(path_to_db)
    cursor = main_connection.cursor()
    select_stmt = "select * from " + table_name + ";"
    try:
        cursor.execute(select_stmt)
    except(Exception):
        print("There is no data for " + table_name + " at " + path_to_db)
    rows = cursor.fetchall()
    return rows


def queary_sql_db(path_to_db, query):
    main_connection = connect(path_to_db)
    cursor = main_connection.cursor()
    try:
        cursor.execute(query)
    except(Exception):
        print("There is no data for " + query + " at " + path_to_db)
    data = cursor.fetchall()
    return data


##### Delays from SQL #####

# Takes in the rows from get_sql_delay_data() and returns a dictionary of
# dictionaries, with the outer layer being a dictionary of file names and
# the inner layer being dictionaries of node_number and its corresponding delay
def parse_delay_rows(rows):
    dict = {}
    # Set comprehension
    files = {file[3] for file in rows}
    print(str(files))
    num_files = len(files)

    for index in range(num_files):
        file_name = files.pop()
        dict[file_name] = {}
        file_rows = [row for row in rows if row[3] == file_name]
        for row in file_rows:
            node_name = row[0]
            start_time = row[5]
            end_time = row[2]
            delay = end_time - start_time
            dict[file_name][node_name] = delay
            print("Adding " + str(delay) + " to " + node_name + " in " + file_name)
    return dict


def plot_delays(delays_dict):
    if(not delays_dict):
        return
    traces = []

    for file_name in delays_dict:
        x = []
        y = []
        file_dict = delays_dict[file_name]
        for node_name in file_dict:
            node_number = get_trailing_number(node_name)
            x.append(node_number)
            y.append(file_dict[node_name] / 1000)
        trace = plotly.graph_objs.Scatter(
            x=x,
            y=y,
            mode='markers',
            name=file_name
        )
        print("Trace: " + str(trace))
        traces.append(trace)

    num_columns = 2
    num_rows = ceil(len(traces) / 2)
    print("Num rows: " + str(num_rows))
    figure = plotly.tools.make_subplots(rows=num_rows, cols=num_columns)

    for index in range(1, len(traces) + 1):
        row_num = ceil(index / 2)
        column_num = (index - 1) % 2 + 1
        figure.append_trace(traces[index - 1], row_num, column_num)

    figure['layout'].update(title="testing title")
    plot_name = "testplot"
    print("Plotting " + plot_name)
    plotly.plotly.iplot(figure, filename=plot_name)


def get_trailing_number(str):
    m = search(r'\d+$', str)
    return int(m.group()) if m else None

##### Message Transfer Delay #####

# Time from message send to message received on each node
def extract_transfer_delays(path_to_input, path_to_output, save_file, num_nodes):
    # Get the data and make sure there is delay data
    data_rows = get_sql_data(path_to_input, "loggableeventmessagereceived")

    # Create the TRANSFERDELAYS table in the output database
    table_schema = (
        "CREATE TABLE IF NOT EXISTS TRANSFERDELAYS (receiverNumber TEXT, " +
        "senderNumber TEXT, delay INTEGER, messageSizeBytes INTEGER, " +
        "saveFile TEXT, messageId TEXT, timestamp TEXT, " +
        "unique(receiverNumber, messageId));"
    )
    main_connection = connect(path_to_output)
    main_connection.execute(table_schema)

    # Get the delay data for each test and insert into output database
    list_of_nodes = [node[0] for node in data_rows]

    # ERROR CHECKING BECAUSE SOMETIMES DATA IS INVALID (something went wrong during test)
    if(len(list_of_nodes) > num_nodes - 1):
        print("Invalid data at " + path_to_input)
        return

    for row in data_rows:
        node_name = row[0]
        sender_name = get_missing_node(list_of_nodes)
        delay = row[4]
        message_id = row[6]
        msg_size = row[7]
        #error_rate = input("Error rate? : ")
        #msg_interval = input("Message Interval? : ")
        timestamp = row[8]
        #gvine_version = input("Gvine version? : ")
        insert_stmt = (
            "INSERT INTO TRANSFERDELAYS (receiverNumber, senderNumber, " +
            "delay, messageSizeBytes, saveFile, messageId, timestamp) VALUES ('" +
            node_name + "', '" + sender_name + "', " + str(delay) + ", " +
            str(msg_size) + ", '" + save_file + "', '" + message_id + "', '" +
            str(timestamp) + "')"
        )
        try:
            main_connection.execute(insert_stmt)
        except(IntegrityError) as err:
            print("Duplicate receiverNumber: " + node_name + ", messageId: " + message_id)

    # Commit then close output database
    main_connection.commit()
    main_connection.close()


def calc_avg_hop_transfer_delay(path_to_input, node_hops_dict, nodes, rack_to_topo_names):
    data_rows = get_sql_data(path_to_input, "transferdelays")
    sum_avg_hop_delays_dict = {}
    num_data_points_dict = {}

    for row in data_rows:
        receiver = row[0]
        rec_ind = get_trailing_number(receiver)
        sender = row[1]
        send_ind = get_trailing_number(sender)
        delay = row[2]
        msg_size_bytes = row[3]
        save = row[4]
        msg_id = row[5]
        timestamp = row[6]

        if(msg_size_bytes not in sum_avg_hop_delays_dict.keys()):
            sum_avg_hop_delays_dict[msg_size_bytes] = 0
            num_data_points_dict[msg_size_bytes] = 0

        num_hops = node_hops_dict[send_ind][rec_ind]
        avg_hop_delay = delay / (num_hops + 1)
        sum_avg_hop_delays_dict[msg_size_bytes] += avg_hop_delay
        num_data_points_dict[msg_size_bytes] += 1

    avgs_dict = {}
    avgs_dict["delays"] = {}
    avgs_dict["counts"] = num_data_points_dict
    for msgSize in sum_avg_hop_delays_dict.keys():
        average = sum_avg_hop_delays_dict[msgSize] / num_data_points_dict[msgSize]
        avgs_dict["delays"][msgSize] = average
    return avgs_dict


##### Message Node Delay #####

# Time from first fragment received to last fragment received
def extract_node_delays(path_to_input, path_to_output, save_file):
    # Get the data and make sure there is fragment data
    frag_rows = get_sql_data(path_to_input, "loggableeventfragment")

    # Create the NODEDELAYS table in the output database
    table_schema = (
        "CREATE TABLE IF NOT EXISTS NODEDELAYS (nodeNumber TEXT, " +
        "delay INTEGER, messageSizeBytes INTEGER, saveFile TEXT, " +
        "messageId TEXT, timestamp TEXT, unique(nodeNumber, messageId));"
    )
    main_connection = connect(path_to_output)
    main_connection.execute(table_schema)

    # Get the delay data
    delays_dict = {}
    # Set comprehension to get unique node values
    nodes = {row[0] for row in frag_rows}
    for node in nodes:
        times_ms = [row[5] for row in frag_rows if row[0] == node]
        early = min(times_ms)
        late = max(times_ms)
        delay = late - early
        delays_dict[node] = delay

    # Get the message size data
    msg_sizes_dict = get_message_sizes(path_to_input)

    # Get a single row for each unique nodeNumber
    taken_nodes = []
    unique_rows = []
    for row in frag_rows:
        if(row[0] not in taken_nodes):
            taken_nodes.append(row[0])
            unique_rows.append(row)

    # Insert into database
    for row in unique_rows:
        node_number = row[0]
        delay = delays_dict[node_number]
        timestamp = row[7]
        message_id = row[6]
        message_size_bytes = msg_sizes_dict[message_id]
        insert_stmt = (
            "INSERT INTO NODEDELAYS " +
            "(nodeNumber, delay, messageSizeBytes, saveFile, messageId, timestamp) " +
            "VALUES ('" + node_number + "', " + str(delay) + ", " + str(message_size_bytes) +
            ", '" + save_file + "', '" + message_id + "', '" + timestamp + "')"
        )
        try:
            main_connection.execute(insert_stmt)
        except(IntegrityError) as err:
            print("Duplicate nodeNumber: " + node_number + ", messageId: " + message_id)

    # Commit then close output database
    main_connection.commit()
    main_connection.close()

##### Overhead #####

# Number of non-payload packets sent / Total packets sent
def extract_overheads():
    return

##### Effective Throughput per node #####

# Message size / Message Node Delay
def extract_throughputs():
    return

##### Link Load #####

# (Total packets sent / Measurement Time Interval) / Link Rate
def extract_link_loads():
    return

##### SENT PACKETS ANALYSIS #####

def make_packets_sent_buckets(path_to_input, bucket_increment_seconds):
    earliest_packet_time = get_earliest_of_all_packets(path_to_input)
    packet_rows = get_sql_data(path_to_input, "loggableeventpacketsent")

    buckets_dict = {}
    for row in packet_rows:
        sender_node = row[0]
        packet_id = row[3]
        num_bytes = row[4]
        time_stamp_millis = row[5]
        relative_time = int((time_stamp_millis - earliest_packet_time) / 1000)
        bucket_index = int(relative_time / bucket_increment_seconds)
        packet_type = get_packet_type(packet_id)

        if(packet_type not in buckets_dict.keys()):
            buckets_dict[packet_type] = {}
        if(sender_node not in buckets_dict[packet_type].keys()):
            buckets_dict[packet_type][sender_node] = {}
        if(not str(bucket_index) in buckets_dict[packet_type][sender_node].keys()):
            buckets_dict[packet_type][sender_node][str(bucket_index)] = {}
            buckets_dict[packet_type][sender_node][str(bucket_index)]['bytes'] = 0
            buckets_dict[packet_type][sender_node][str(bucket_index)]['packets'] = 0

        buckets_dict[packet_type][sender_node][str(bucket_index)]['bytes'] += int(num_bytes /
                                                                bucket_increment_seconds)
        buckets_dict[packet_type][sender_node][str(bucket_index)]['packets'] += 1
    return buckets_dict


def plot_packets_sent_data(buckets_dict, bucket_increment_seconds, last_second):
    #plotly.offline.init_notebook_mode(True)
    colors = ["#ff0000", "#00ff00", "#0000ff", "#660033"]
    colors_dict = {}
    for packet_type in buckets_dict.keys():
        colors_dict[packet_type] = colors.pop(0)
    traces = {}

    for packet_type in buckets_dict.keys():
        already_named = False
        traces[packet_type] = {}
        for node in buckets_dict[packet_type].keys():
            traces[packet_type][node] = None
            x = []
            y = []
            for second in range(last_second):
                x.append(second)
                if(str(second) in buckets_dict[packet_type][node].keys()):
                    y.append(buckets_dict[packet_type][node][str(second)]['bytes'])
                else:
                    y.append(0)
            if(not already_named):
                already_named = True
                trace = plotly.graph_objs.Scatter(
                    x=x,
                    y=y,
                    mode="lines",
                    name=packet_type,
                    line=dict(
                        color=colors_dict[packet_type],
                        width=2
                    )
                )
            else:
                trace = plotly.graph_objs.Scatter(
                    x=x,
                    y=y,
                    mode="lines",
                    name=packet_type,
                    showlegend=False,
                    line=dict(
                        color=colors_dict[packet_type],
                        width=2
                    )
                )
            traces[packet_type][node] = trace

    sorted_nodes = sorted(buckets_dict["handshake"].keys(), key=lambda n: get_trailing_number(n))
    num_columns = 2
    num_rows = ceil(len(sorted_nodes) / 2)
    subplot_titles = []
    for node in sorted_nodes:
        subplot_titles.append(node)
    figure = plotly.tools.make_subplots(rows=num_rows, cols=num_columns,
                                        subplot_titles=subplot_titles, print_grid=False)

    for packet_type in buckets_dict.keys():
        for node in sorted(buckets_dict[packet_type].keys()):
            index = int(node[-1])
            index = get_trailing_number(node)
            row_num = int((index - 1)/ 2) + 1
            col_num = 2 - index % 2
            figure.append_trace(traces[packet_type][node], row_num, col_num)
    return figure

##### Received Packets #####

def make_packets_received_buckets(path_to_input, bucket_size_seconds):
    earliest_packet_time = get_earliest_of_all_packets(path_to_input)
    packet_rows = get_sql_data(path_to_input, "loggableeventpacketreceived")

    buckets_dict = {}
    for row in packet_rows:
        receiver_node = row[0]
        sender_node = row[2]
        packet_id = row[4]
        num_bytes = row[5]
        time_stamp_millis = row[6]
        relative_time = int((time_stamp_millis - earliest_packet_time) / 1000)
        bucket_index = int(relative_time / bucket_size_seconds)
        packet_type = get_packet_type(packet_id)

        if(packet_type not in buckets_dict.keys()):
            buckets_dict[packet_type] = {}
        if(receiver_node not in buckets_dict[packet_type].keys()):
            buckets_dict[packet_type][receiver_node] = {}
        if(sender_node not in buckets_dict[packet_type][receiver_node].keys()):
            buckets_dict[packet_type][receiver_node][sender_node] = {}
        if(str(bucket_index) not in buckets_dict[packet_type][receiver_node][sender_node].keys()):
            buckets_dict[packet_type][receiver_node][sender_node][str(bucket_index)] = {}
            buckets_dict[packet_type][receiver_node][sender_node][str(bucket_index)]['bytes'] = 0
            buckets_dict[packet_type][receiver_node][sender_node][str(bucket_index)]['packets'] = 0

        buckets_dict[packet_type][receiver_node][sender_node][str(bucket_index)]['bytes'] += int(num_bytes /
                                                                           bucket_size_seconds)
        buckets_dict[packet_type][receiver_node][sender_node][str(bucket_index)]['packets'] += 1
    return buckets_dict


def plot_packets_received_data(buckets_dict, bucket_size_seconds, last_second):
    traces = {}
    colors = ["#ff0000", "#00ff00", "#0000ff", "#660033"]
    colors_dict = {}
    for packet_type in buckets_dict.keys():
        colors_dict[packet_type] = colors.pop(0)

    for packet_type in buckets_dict.keys():
        already_named = False
        traces[packet_type] = {}
        for receiverNode in buckets_dict[packet_type].keys():
            traces[packet_type][receiverNode] = None
            x = []
            y = []
            sums_dict = {}
            for senderNode in buckets_dict[packet_type][receiverNode]:
                for bucket_index in sorted(buckets_dict[packet_type][receiverNode][
                                               senderNode].keys(), key=int):
                    bucket_key = str(int(bucket_index) * bucket_size_seconds)
                    if(bucket_key not in sums_dict.keys()):
                        sums_dict[bucket_key] = 0
                    sums_dict[bucket_key] += buckets_dict[packet_type][receiverNode][senderNode][
                        bucket_index]['bytes']
            for second in range(last_second):
                x.append(second)
                if(str(second) in sums_dict.keys()):
                    y.append(sums_dict[str(second)])
                else:
                    y.append(0)
            if(not already_named):
                already_named = True
                trace = plotly.graph_objs.Scatter(
                    x=x,
                    y=y,
                    mode="lines",
                    name=packet_type,
                    line=dict(
                        color=colors_dict[packet_type],
                        width=2
                    )
                )
            else:
                trace = plotly.graph_objs.Scatter(
                    x=x,
                    y=y,
                    mode="lines",
                    name=packet_type,
                    showlegend=False,
                    line=dict(
                        color=colors_dict[packet_type],
                        width=2
                    )
                )
            traces[packet_type][receiverNode] = trace

    sorted_nodes = sorted(buckets_dict["handshake"].keys())
    num_columns = 2
    num_rows = ceil(len(sorted_nodes) / 2)
    sub_titles = []
    for node in sorted_nodes:
        sub_titles.append(node)
    figure = plotly.tools.make_subplots(rows=num_rows, cols=num_columns,
                                        subplot_titles=sub_titles, print_grid=False)

    for packet_type in buckets_dict.keys():
        for node in sorted(buckets_dict[packet_type].keys()):
            index = int(node[-1])
            index = get_trailing_number(node)
            row_num = int((index - 1) / 2) + 1
            col_num = 2 - index % 2
            figure.append_trace(traces[packet_type][node], row_num, col_num)
    return figure

##### Rank Progress Graph #####

def make_rank_buckets(path_to_input, bucket_size_seconds):
        earliest_packet_time = get_earliest_of_all_packets(path_to_input)
        rank_rows = get_sql_data(path_to_input, "loggableeventrankrx")

        buckets_dict = {}
        for row in rank_rows:
            receiver_node = row[0]
            event_id = row[1]
            current_rank = row[2]
            frag_index = row[3]
            message_id = row[4]
            max_rank = row[5]
            time_stamp_millis = row[6]
            relative_time = int((time_stamp_millis - earliest_packet_time) / 1000)
            bucket_index = int(relative_time / bucket_size_seconds)

            if(receiver_node not in buckets_dict.keys()):
                buckets_dict[receiver_node] = {}
            if(str(frag_index) not in buckets_dict[receiver_node].keys()):
                buckets_dict[receiver_node][str(frag_index)] = {}
            if(str(bucket_index) not in buckets_dict[receiver_node][str(frag_index)].keys()):
                buckets_dict[receiver_node][str(frag_index)][str(bucket_index)] = current_rank
            else:
                same_bucket = buckets_dict[receiver_node][str(frag_index)][str(bucket_index)]
                buckets_dict[receiver_node][str(frag_index)][str(bucket_index)] = max(same_bucket,
                                                                           current_rank)
        return buckets_dict


def plot_rank_data(buckets_dict, bucket_size_seconds, last_second):
        traces = {}
        seconds_dict = {}
        for receiverNode in buckets_dict.keys():
            traces[receiverNode] = {}
            seconds_dict[receiverNode] = {}
            for frag_index in buckets_dict[receiverNode].keys():
                seconds_dict[receiverNode][frag_index] = {}
                x = []
                y = []
                for bucket_index in sorted(buckets_dict[receiverNode][frag_index].keys(), key=int):
                    bucket_key = str(int(bucket_index) * bucket_size_seconds)
                    seconds_dict[receiverNode][frag_index][bucket_key] = buckets_dict[
                        receiverNode][frag_index][str(bucket_index)]
                for second in range(last_second):
                    x.append(second)
                    if(str(second) in seconds_dict[receiverNode][frag_index].keys()):
                        y.append(seconds_dict[receiverNode][frag_index][str(second)])
                    else:
                        y.append(0)
                trace = plotly.graph_objs.Scatter(
                    x=x,
                    y=y,
                    mode="lines",
                    name=receiverNode,
                    showlegend=True,
                    line=dict(
                        width=2
                    )
                )
                traces[receiverNode][frag_index] = trace

        sorted_nodes = sorted(buckets_dict.keys(), key=lambda n: get_trailing_number(n))
        num_columns = 2
        num_rows = ceil(len(sorted_nodes) / 2)
        sub_titles = []
        for node in sorted_nodes:
            sub_titles.append(node)
        figure = plotly.tools.make_subplots(rows=num_rows, cols=num_columns,
                                            subplot_titles=sub_titles, print_grid=False)

        start_index = get_trailing_number(sorted_nodes[0])
        for node in sorted_nodes:
            index = get_trailing_number(node) - start_index + 1
            row_num = int((index - 1) / 2) + 1
            col_num = 2 - index % 2
            for frag_index in traces[node].keys():
                figure.append_trace(traces[node][frag_index], row_num, col_num)
        return figure


def plot_figure(figure, file_name, offline):
    if(offline):
        plotly.offline.iplot(figure)
    else:
        plotly.plotly.iplot(figure, filename=file_name)


def get_packet_type(packet_id):
    if(packet_id == PACKET_BEACON):
        packet_type = "beacon"
    elif(packet_id == PACKET_HANDSHAKE):
        packet_type = "handshake"
    elif(packet_id == PACKET_BABEL):
        packet_type = "babel"
    elif(packet_id == PACKET_GVINE):
        packet_type = "gvine"
    else:
        packet_type = "unknown"
        print("UNKNOWN PACKET TYPE")
    return packet_type


def get_packet_type_data(path_to_input, table_name, type_index):
    packet_rows = get_sql_data(path_to_input, table_name)
    type_dict = {
        "beacon": [],
        "gvine": [],
        "babel": [],
        "handshake": []
    }
    for row in packet_rows:
        packet_type = get_packet_type(row[type_index])
        type_dict[packet_type].append(row)
    return type_dict


def print_type_data(type_dict, byte_index):
    for packet_type in type_dict.keys():
        sum_bytes = 0
        for row in type_dict[packet_type]:
            sum_bytes += row[byte_index]
        num_packets = len(type_dict[packet_type])
        average_size = sum_bytes / num_packets
        print()
        print("Packet type: " + packet_type)
        print("Number of packets: " + str(num_packets))
        print("Number of bytes: " + str(sum_bytes))
        print("Average packet size: {:<10.2f}".format(average_size))


def print_delay_data(path_to_input):
    delay_rows = get_sql_data(path_to_input, "loggableeventmessagereceived")
    files_dict = {}
    for row in delay_rows:
        if(row[3] not in files_dict.keys()):
            files_dict[row[3]] = []
        files_dict[row[3]].append(row)
    for key in files_dict.keys():
        print()
        for row in files_dict[key]:
            print(row[0] + " received " + key + " (" + str(row[7]) + " bytes) in " +
                  str(row[4]/1000) + " seconds")


def get_earliest_packet_time(packet_rows, index_of_timestamp):
    if(packet_rows):
        return min([row[index_of_timestamp] for row in packet_rows])


def get_earliest_of_all_packets(path_to_input):
    sent_packet_rows = get_sql_data(path_to_input, "loggableeventpacketsent")
    received_packet_rows = get_sql_data(path_to_input, "loggableeventpacketreceived")
    earliest_sent = get_earliest_packet_time(sent_packet_rows, 5)
    earliest_received = get_earliest_packet_time(received_packet_rows, 6)
    compare_arr = []
    if(earliest_sent):
        compare_arr.append(earliest_sent)
    if(earliest_received):
        compare_arr.append(earliest_received)
    if(not compare_arr):
        print("NO SENT OR RECEIVED PACKETS IN DATABASE")
    return min(compare_arr)


def get_latest_packet_time(packet_rows, index_of_timestamp):
    if(packet_rows):
        return max([row[index_of_timestamp] for row in packet_rows])


def get_latest_of_all_packets(path_to_input):
    sent_packet_rows = get_sql_data(path_to_input, "loggableeventpacketsent")
    received_packet_rows = get_sql_data(path_to_input, "loggableeventpacketreceived")
    latest_sent = get_latest_packet_time(sent_packet_rows, 5)
    latest_received = get_latest_packet_time(received_packet_rows, 6)
    compare_arr = []
    if(latest_sent):
        compare_arr.append(latest_sent)
    if(latest_received):
        compare_arr.append(latest_received)
    if(not compare_arr):
        print("NO SENT OR RECEIVED PACKETS IN DATABASE")
    return min(compare_arr)


def get_missing_node(list_of_nodes):
    list_of_nodes = natural_sort(list_of_nodes)
    for index in range(1, len(list_of_nodes) + 1):
        if(get_trailing_number(list_of_nodes[index - 1]) != index):
            return "node" + str(index)
    return "node" + str(len(list_of_nodes) + 1)


# Returns a dictionary of messageId:messageSize
def get_message_sizes(input_path):
    msg_rows = get_sql_data(input_path, "loggableeventmessagereceived")
    sizes_dict = {}
    messages = {row[6] for row in msg_rows}
    for message in messages:
        for row in msg_rows:
            if(row[6] == message):
                sizes_dict[message] = row[7]
                break
    return sizes_dict


##### Plotting #####


def plot_values(values, plot_name):
    print("Plot name: " + plot_name)
    data = get_plot_trace(values)
    print("Plotting " + str(len(data)) + " traces")
    plotly.plotly.iplot(data, filename=plot_name)


def get_plot_trace(values):
    x = list(range(1, len(values) + 1))
    y = []
    traces = []

    if(isinstance(values[0], list)):
        for j in range(len(values[0])):
            y = []
            for i in range(1, len(values) + 1):
                if(len(values[i - 1]) > j):
                    y.append(values[i - 1][j])
                else:
                    y.append(0)
            trace = plotly.graph_objs.Scatter(
                x=x,
                y=y,
                mode='lines',
                name='delay' + str(j)
            )
            traces.append(trace)

    else:
        for i in range(1, len(values) + 1):
            x.append(i)
            y.append(values[i - 1])
        trace = plotly.graph_objs.Scatter(
                x=x,
                y=y,
                mode='markers'
            )
        return [trace]
    return traces


def sub_plot(node_data):
    num_columns = 5
    num_rows = int(len(node_data) / 5 + 1)
    figure = plotly.tools.make_subplots(rows=num_rows, cols=num_columns)
    for index in range(1, len(node_data) + 1):
        row_num = int(index / 5) + 1
        col_num = index % 5 + 1
        figure.append_trace(get_plot_trace(node_data[index - 1]), row_num, col_num)
    plotly.plotly.iplot(figure, filename="test-subplot")


##### EMANE Statistics #####


def generate_emane_stats(node_prefix, save_folder, num_nodes, iplist):
    loc = path.expanduser("~/.ssh/id_rsa")
    key = RSAKey.from_private_key_file(loc)
    ssh = SSHClient()
    ssh.set_missing_host_key_policy(AutoAddPolicy())

    for index in range(1, num_nodes + 1):
        ssh.connect(iplist[index - 1], username="emane-01", pkey=key)

        # Make stats directory
        command = (
            "cd /home/emane-01/GrapeVine/topologies/" + save_folder +
            "/data/ && mkdir stats"
        )
        stdin, stdout, stderr = ssh.exec_command(command)

        # Generate emane 'show'
        command = (
            "emanesh " + node_prefix + str(index) + " show"
            " > /home/emane-01/GrapeVine/topologies/" + save_folder +
            "/data/stats/emane.show"
        )
        stdin, stdout, stderr = ssh.exec_command(command)

        # Generate emane 'stats'
        command = (
            "emanesh " + node_prefix + str(index) + " get stat '*' all"
            " > /home/emane-01/GrapeVine/topologies/" + save_folder +
            "/data/stats/emane.stats"
        )
        stdin, stdout, stderr = ssh.exec_command(command)

        # Generate emane 'tables'
        command = (
            "emanesh " + node_prefix + str(index) + " get table '*' all"
            " > /home/emane-01/GrapeVine/topologies/" + save_folder +
            "/data/stats/emane.tables"
        )
        stdin, stdout, stderr = ssh.exec_command(command)
        ssh.close()


def copy_emane_stats(save_folder, num_nodes, iplist):
    for index in range(0, num_nodes):
        node_ip = iplist[index]
        dest_dir = './stats/emane/' + save_folder + "/node" + str(index + 1)
        from_dir = (
            'root@' + node_ip + ':/home/emane-01/GrapeVine/topologies/'
            + save_folder + '/data/stats/.'
        )
        print("Copying from node" + str(index + 1))
        Popen(['scp', '-r', from_dir, dest_dir])
        sleep(1)


def parse_emane_stats(save_folder, num_nodes, parse_term):
    all_values = []
    for index in range(1, num_nodes + 1):
        file_path = (
                "./stats/emane/" + save_folder + "/node" +
                str(index) + "/emane.stats"
        )
        file = open(file_path, 'r')
        lines = file.readlines()
        values = []
        for line in lines:
            if(parse_term in line):
                print(line)
                value = line.split(" = ", 1)[1].strip("\n")
                values.append(value)
        all_values.append(values)
    print("All values: " + str(all_values))

    phys = []
    for derplist in all_values:
        sum = 0
        for index in range(int(len(derplist) / 3)):
            sum += int(derplist[index * 3 + 2])
        phys.append(sum)
    print("phys: " + str(phys))
    return phys


##### Event Statistics #####


def generate_event_dbs(iplist):
    loc = path.expanduser("~/.ssh/id_rsa")
    key = RSAKey.from_private_key_file(loc)
    ssh = SSHClient()
    ssh.set_missing_host_key_policy(AutoAddPolicy())

    for index in range(1, len(iplist) + 1):
        ssh.connect(iplist[index - 1], username="emane-01", pkey=key)

        command = (
            "cd /home/emane-01/test/emane/gvine/node/eventlogs/ && " +
            "ls -dlt */"
        )
        stdin, stdout, stderr = ssh.exec_command(command)
        target_dir = stdout.read().decode().splitlines()[0].split(" ")[-1]

        command = (
            "cd /home/emane-01/test/emane/gvine/node/ && " +
            "java -jar dbreader.jar eventlogs/" + target_dir + " LaJollaCove eventsql"
        )
        stdin, stdout, stderr = ssh.exec_command(command)
        ssh.close()


def clear_node_event_data(save_file):
    command = "rm -f ./stats/events/" + save_file + "/nodedata/*"
    system(command)


def copy_event_dbs(iplist, path_to_db, dest_path):
    for index in range(len(iplist)):
        ip = iplist[index]
        command = (
            "scp emane-01@" + ip + ":" + path_to_db + " " + dest_path +
            "/eventsql" + str(index + 1) + ".db"
        )
        system(command)


def combine_event_dbs(input_dir, output_dir):
    # Make a new database named by timestamp
    date_time = strftime("%Y-%m-%d_%H:%M:%S", gmtime())
    new_db_name = output_dir + "/" + date_time + ".db"
    print("Opening main connection to " + new_db_name)
    main_connection = connect(new_db_name)
    # Get the database names for each separate database we want to combine
    print("Getting db names")
    db_names = [name for name in glob(input_dir + "*.db") if "eventsql" in name]
    # Get the table names and schemas needed to create the new database
    print("Getting tables names and schemas")
    table_names, schemas = gather_table_schemas(input_dir, db_names)
    # Create the tables in the new database
    print("Creating db tables")
    create_db_tables(main_connection, schemas)
    # Insert data from all the databases into the new database
    print("Inserting db data")
    insert_db_data(main_connection, db_names, table_names)
    # Save the changes made to the new database
    print("Committing main connection")
    main_connection.commit()
    # Close the database connection
    print("Closing main connection")
    main_connection.close()
    return new_db_name


def gather_table_schemas(path_to_dbs, db_names):
    table_names = []
    schemas = []
    for db_name in db_names:
        conn = connect(db_name)
        cursor = conn.cursor()
        try:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
        except DatabaseError:
            print("""There was an error while querying the database, this is probably because
                you pulled the databases down from the nodes while grapevine was still running""")
            exit()

        tables = cursor.fetchall()

        # Loop through and add non-duplicate table names
        for table in tables:
            table = table[0]
            if table not in table_names:
                table_names.append(table)
            schema = conn.execute("SELECT sql FROM sqlite_master where type='table' and name='" +
                                  table + "'").fetchall()[0][0]
            if schema not in schemas:
                schemas.append(schema)
        conn.close()
    return table_names, schemas


def create_db_tables(main_connection, schemas):
    for schema in schemas:
        schema = schema.replace("CREATE TABLE", "CREATE TABLE IF NOT EXISTS")
        schema = schema.replace("eventId INTEGER PRIMARY KEY UNIQUE, ", "")
        index = schema.index(" (") + 2
        schema = schema[:index] + "nodeNumber TEXT, eventId INTEGER, " + schema[index:]
        schema = schema.replace(")", ", unique(nodeNumber, eventId));")
        cursor = main_connection.execute(schema)


def insert_db_data(main_connection, db_names, table_names):
    sorted_names = natural_sort(db_names)

    for index in range(1, len(sorted_names) + 1):
        db_name = sorted_names[index - 1]
        conn = connect(db_name)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        for table in tables:
            table_name = table[0]
            cursor = conn.execute("SELECT * FROM " + table_name + ";")
            table_data = cursor.fetchall()
            column_names = [description[0] for description in cursor.description]

            # Insert the data
            for row in table_data:
                insert_sql = create_insert_stmt(table_name, column_names, index, row)
                try:
                    main_connection.execute(insert_sql)
                except IntegrityError:
                    # This is caused by a duplicate input, ignore it and dont insert
                    pass
        conn.close()


# Sort strings based on the numbers inside them, look up "natural sorting"
def natural_sort(l): 
    convert = lambda text: int(text) if text.isdigit() else text.lower() 
    alphanum_key = lambda key: [convert(c) for c in split('([0-9]+)', key)]
    return sorted(l, key=alphanum_key)


def create_insert_stmt(table_name, column_names, node_index, row_data):
    insert_stmt = "INSERT INTO " + table_name + " (nodeNumber"
    for column_name in column_names:
        insert_stmt += ", " + column_name
    insert_stmt += ") VALUES ('node" + str(node_index) + "'"
    for data_value in row_data:
        # Insert it as a string or integer
        try:
            if(data_value is None):
                insert_stmt += ", NULL"
            else:
                insert_stmt += ", '" + data_value + "'"
        except TypeError:
            insert_stmt += ", " + str(data_value)
    insert_stmt += ")"
    return insert_stmt


##### TESTING FUNCTIONS #####


def check_packet_sent_timestamps(path_to_input):
    packet_rows = get_sql_data(path_to_input, "loggableeventpacketsent")

    nodes_dict = {}
    for row in packet_rows:
        sender_node = row[0]
        timestamp = row[4]
        if(sender_node not in nodes_dict.keys()):
            nodes_dict[sender_node] = 9999999999999
        if(timestamp < nodes_dict[sender_node]):
            nodes_dict[sender_node] = timestamp

    for sender_node in nodes_dict.keys():
        print("Earliest time for " + sender_node + ": " + str(nodes_dict[sender_node]))


def copy_dump_files(node_objects, output_dir):
    date_time = strftime("%Y-%m-%d_%H:%M:%S", gmtime())
    folder_name = output_dir + "/" + date_time + "/"
    create_dir(folder_name)

    for node in node_objects:
        node.retrieve_pcaps(folder_name)
    return folder_name


def make_ipmap(node_objects, map_path):
    ipmap = {}
    for node in node_objects:
        node_ipmap = node.get_ipmap()
        ipmap.update(node_ipmap)
    with open(map_path, "wb") as file:
        pickle.dump(ipmap, file)


def read_ipmap(map_path):
    with open(map_path, "rb") as file:
        ipmap = pickle.load(file)
    print(str(ipmap))
    return ipmap


def read_params(folder_path):
    params_path = folder_path + "params" if folder_path[-1] == "/" else folder_path + "/params"
    if(path.isfile(params_path)):
        with open(params_path, "r") as param_file:
            param_list = param_file.readlines()
    else:
        param_list = ["NO PARAMETER DATA"]
    return param_list

##### STOP BEACONS #####

def make_stop_beacon_dict(path_to_db):
    """Return dictionary stop_dict[direction][node_name] = list_of_stop_beacons

    :param path_to_db: Path to sql db to parse
    :return:
    """
    rows = get_sql_data(path_to_db, "loggableeventstopbeacon")
    earliest_time = get_earliest_of_all_packets(path_to_db)
    stop_dict = {
        "tx": {},
        "rx": {}
    }
    for row in rows:
        node_name = row[0]
        frag_index = row[2]
        direction = row[5]
        timestamp = row[6]
        if node_name not in stop_dict[direction].keys():
            stop_dict[direction][node_name] = {}
        if str(frag_index) not in stop_dict[direction][node_name].keys():
            stop_dict[direction][node_name][str(frag_index)] = 0
        stop_dict[direction][node_name][str(frag_index)] = int((timestamp - earliest_time) / 1000)
    return stop_dict


def print_stop_dict(stop_dict):
    for direction in stop_dict.keys():
        print("Direction: " + direction)
        for node_name in sorted(stop_dict[direction].keys(), key=get_trailing_number):
            print("Node: " + node_name)
            for frag_index in sorted(stop_dict[direction][node_name].keys(), key=int):
                print(frag_index + ": " + str(stop_dict[direction][node_name][frag_index]))
            print()
