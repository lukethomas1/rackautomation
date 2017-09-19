# File: benchmark.py
# Author: Luke Thomas
# Date: August 24, 2017
# Description: Benchmark different versions of GrapeVine

# System Imports

# 3rd Party Imports
from plotly.offline import init_notebook_mode
import plotly
from glob import glob

# Local imports
import functions
import packetsuite
from graphsuite import make_45_combined_trace as make45

def forty_five_comparison():
    """ Compare multiple groups of PCAP files

    Current list of benchmarks:
    unicast: 20minutescpsequential
    norm: 20minnorm165kb
    gvine403: 403pro20min
    gvine411: 411pro20min
    gvine424: 424pro20min
    pi424: 424pipro20min
    gvine425pro: 425pro20min
    gvine425re: 425re50min
    :return:
    """
    init_notebook_mode(connected=True)
    dump_dirs = glob("./stats/dumps/45benchmark/*")

    # Get the tests to be included in the benchmark
    paths_dict = {}
    path_option = ""
    while path_option != "d" and path_option != "c":
        path_option = input("(d)efault or (c)ustom benchmarking? : ")

    if path_option == "d":
        paths_dict["unicast"] = [loc for loc in dump_dirs if "scpsequential" in loc][0]
        paths_dict["norm"] = [loc for loc in dump_dirs if "norm" in loc][0]
        paths_dict["gvine403"] = [loc for loc in dump_dirs if "403pro20min" in loc][0]
        paths_dict["gvine411"] = [loc for loc in dump_dirs if "411pro20min" in loc][0]
        paths_dict["gvine424"] = [loc for loc in dump_dirs if "424pro20min" in loc][0]
        paths_dict["pi424"] = [loc for loc in dump_dirs if "424pipro20min" in loc][0]
        paths_dict["gvine425pro"] = [loc for loc in dump_dirs if "425pro20min" in loc][0]
        paths_dict["gvine425re"] = [loc for loc in dump_dirs if "425re50min" in loc][0]
    elif path_option == "c":
        while(True):
            print("Paths to choose from:")
            for dump_dir in dump_dirs:
                print(dump_dir)
            print()
            trace_name = input("Enter name of trace ('done' to end): ")
            if trace_name == "done":
                break
            trace_path_term = input("Enter matching path substring for " + trace_name + ": ")
            paths_dict[trace_name] = [loc for loc in dump_dirs if trace_path_term in loc][0]
            dump_dirs = [dump_dir for dump_dir in dump_dirs if trace_path_term not in dump_dir]

    # Display test names and associated paths
    print()
    print("Chosen trace names and paths:")
    for trace_name in paths_dict.keys():
        print(trace_name + ": " + paths_dict[trace_name])

    colors_list = [
        "#e6194b",  # red
        "#3cb44b",  # green
        "#ffe119",  # yellow
        "#0082c8",  # blue
        "#f58231",  # orange
        "#911eb4",  # purple
        "#46f0f0",  # cyan
        "#f032e6",  # magenta
        "#d2f53c",  # lime
        "#fabebe",  # pink
        "#008080",  # teal
        "#e6beff",  # lavender
        "#aa6e28",  # brown
        "#fffac8",  # beige
        "#800000",  # maroon
        "#aaffc3",  # mint
        "#808000",  # olive
        "#ffd8b1",  # coral
        "#000080",  # navy
        "#808080",  # grey
        "#000000",  # black
    ]
    colors_dict = {}
    color_index = 0
    for trace_name in paths_dict.keys():
        colors_dict[trace_name] = colors_list[color_index]
        color_index += 1

    combined_dict = {}
    for trace_name in paths_dict.keys():
        basic_dict = packetsuite.make_basic_packets_dict(paths_dict[trace_name])
        combined_dict[trace_name] = packetsuite.make_basic_combined_dict(basic_dict)

    traces_dict = {
        "tx_average": {},
        "rx_average": {},
        "tx_cumulative": {},
        "rx_cumulative": {}
    }
    print(str(combined_dict.keys()))
    for graph_type in traces_dict.keys():
        for trace_name in combined_dict.keys():
            direction = graph_type.split("_")[0]
            plot_cumulative = True if "cumulative" in graph_type else False
            this_trace = make45(combined_dict[trace_name], direction, plot_cumulative, trace_name,
                                colors_dict[trace_name])
            traces_dict[graph_type][trace_name] = this_trace

    print(str(traces_dict["tx_average"].keys()))

    for graph_type in traces_dict.keys():
        figure = plotly.tools.make_subplots(rows=1, cols=1, print_grid=False)
        for trace_name in traces_dict[graph_type].keys():
            figure.append_trace(traces_dict[graph_type][trace_name], 1, 1)
        figure['layout'].update(height=600, width=1000, title=graph_type)
        plotly.offline.iplot(figure)
