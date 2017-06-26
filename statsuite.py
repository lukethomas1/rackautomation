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

##### General SQLITE Functions #####

def get_sql_data(path_to_db, loggable_event):
    main_connection = connect(path_to_db)
    cursor = main_connection.cursor()
    select_stmt = "select * from " + loggable_event + ";"
    try:
        cursor.execute(select_stmt)
    except(Exception):
        print("There is no data for " + loggable_event + " at " + path_to_db)
    rows = cursor.fetchall()
    return rows


##### Delays from SQL #####

# Takes in the rows from get_sql_delay_data() and returns a dictionary of
# dictionaries, with the outer layer being a dictionary of file names and
# the inner layer being dictionaries of node_number and its corresponding delay
def parse_delay_rows(rows):
    if(not rows):
        return
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
            x = x,
            y = y,
            mode = 'markers',
            name = file_name
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
def extract_transfer_delays(path_to_input, path_to_output, save_file):
    # Get the data and make sure there is delay data
    data_rows = get_sql_data(path_to_input, "loggableeventmessagereceived")
    if(not data_rows):
        return

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
    for row in data_rows:
        node_name = row[0]
        sender_name = get_missing_node(list_of_nodes)
        delay = row[4]
        messageId = row[6]
        msg_size = row[7]
        #error_rate = input("Error rate? : ")
        #msg_interval = input("Message Interval? : ")
        timestamp = row[8]
        #gvine_version = input("Gvine version? : ")
        insert_stmt = (
            "INSERT INTO TRANSFERDELAYS (receiverNumber, senderNumber, " +
            "delay, messageSizeBytes, saveFile, messageId, timestamp) VALUES ('" +
            node_name + "', '" + sender_name + "', " + str(delay) + ", " +
            str(msg_size) + ", '" + save_file + "', '" + messageId + "', '" +
            timestamp + "')"
        )
        try:
            main_connection.execute(insert_stmt)
        except(IntegrityError) as err:
            print("Duplicate receiverNumber: " + node_name + ", messageId: " + messageId)

    # Commit then close output database
    main_connection.commit()
    main_connection.close()


##### Message Node Delay #####
# Time from first fragment received to last fragment received
def extract_node_delays(path_to_input, path_to_output, save_file):
    # Get the data and make sure there is fragment data
    frag_rows = get_sql_data(path_to_input, "loggableeventfragment")
    if(not frag_rows):
        return

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
        nodeNumber = row[0]
        delay = delays_dict[nodeNumber]
        timestamp = row[7]
        messageId = row[6]
        messageSizeBytes = msg_sizes_dict[messageId]
        insert_stmt = (
            "INSERT INTO NODEDELAYS " +
            "(nodeNumber, delay, messageSizeBytes, saveFile, messageId, timestamp) " +
            "VALUES ('" + nodeNumber + "', " + str(delay) + ", " + str(messageSizeBytes) +
            ", '" + save_file + "', '" + messageId + "', '" + timestamp + "')"
        )
        try:
            main_connection.execute(insert_stmt)
        except(IntegrityError) as err:
            print("Duplicate nodeNumber: " + nodeNumber + ", messageId: " + messageId)

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
                x = x,
                y = y,
                mode = 'lines',
                name = 'delay' + str(j)
            )
            traces.append(trace)

    else:
        for i in range(1, len(values) + 1):
            x.append(i)
            y.append(values[i - 1])
        trace = plotly.graph_objs.Scatter(
                x = x,
                y = y,
                mode = 'markers'
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
    figure['layout'].update(title=str(len(node_data)) + " Nodes")
    plotly.plotly.iplot(figure, filename="test-subplot")


##### EMANE Statistics #####


def generate_emane_stats(node_prefix, save_folder, num_nodes, iplist):
    key = RSAKey.from_private_key_file("/home/joins/.ssh/id_rsa")
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
    key = RSAKey.from_private_key_file("/home/joins/.ssh/id_rsa")
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
            schema = conn.execute("SELECT sql FROM sqlite_master where type='table' and name='" + table + "'").fetchall()[0][0]
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
    alphanum_key = lambda key: [ convert(c) for c in split('([0-9]+)', key) ] 
    return sorted(l, key = alphanum_key)


def create_insert_stmt(table_name, column_names, node_index, row_data):
    insert_stmt = "INSERT INTO " + table_name + " (nodeNumber"
    for column_name in column_names:
        insert_stmt += ", " + column_name
    insert_stmt += ") VALUES ('node" + str(node_index) + "'"
    for data_value in row_data:
        # Insert it as a string or integer
        try:
            insert_stmt += ", '" + data_value + "'"
        except TypeError:
            insert_stmt += ", " + str(data_value)
    insert_stmt += ")"
    return insert_stmt
