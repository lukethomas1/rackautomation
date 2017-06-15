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
from sqlite3 import connect, IntegrityError
from time import gmtime, strftime, sleep

# 3rd Party Imports
from paramiko import AutoAddPolicy, RSAKey, SSHClient
import plotly

##### Delays from SQL #####

def get_sql_delay_data(path_to_db):
    main_connection = connect(path_to_db)
    cursor = main_connection.cursor()
    select_stmt = "select * from loggableeventmessagereceived;"
    try:
        cursor.execute(select_stmt)
    except(Exception):
        print("There is no delay data at " + path_to_db)
    rows = cursor.fetchall()
    return rows


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

##### Message Node Delay #####
# Time from first fragment received to last fragment received

##### Overhead #####
# Number of non-payload packets sent / Total packets sent

##### Effective Throughput per node #####
# Message size / Message Node Delay

##### Link Load #####
# (Total packets sent / Measurement Time Interval) / Link Rate

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
    print("Opening main connection")
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
    print("committing main connection")
    main_connection.commit()
    # Close the database connection
    print("closing main connection")
    main_connection.close()
    return new_db_name


def gather_table_schemas(path_to_dbs, db_names):
    table_names = []
    schemas = []
    for db_name in db_names:
        conn = connect(db_name)
        cursor = conn.cursor()
        derp = False
        counter = 0
        while(not derp):
            try:
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
                derp = True
            except Error:
                counter += 1
                print("messed up: " + str(counter))

                

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
