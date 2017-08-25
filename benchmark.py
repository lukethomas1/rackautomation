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
    init_notebook_mode(connected=True)
    dump_dirs = glob("./stats/dumps/45benchmark/*")
    print("Unicast:")
    unicast_path = functions.choose_alphabetic_path(dump_dirs)
    print("Norm:")
    norm_path = functions.choose_alphabetic_path(dump_dirs)
    print("Gvine-v403")
    gvine403_path = functions.choose_alphabetic_path(dump_dirs)
    print("Gvine-v411")
    gvine411_path = functions.choose_alphabetic_path(dump_dirs)
    unicast_dict = packetsuite.make_basic_packets_dict(unicast_path)
    unicast_combined = packetsuite.make_basic_combined_dict(unicast_dict)
    norm_dict = packetsuite.make_basic_packets_dict(norm_path)
    norm_combined = packetsuite.make_basic_combined_dict(norm_dict)
    gvine403_dict = packetsuite.make_basic_packets_dict(gvine403_path)
    gvine403_combined = packetsuite.make_basic_combined_dict(gvine403_dict)
    gvine411_dict = packetsuite.make_basic_packets_dict(gvine411_path)
    gvine411_combined = packetsuite.make_basic_combined_dict(gvine411_dict)

    colors = {
        "unicast": "#ff0000",
        "norm": "#00ff00",
        "gvine403": "#0000ff",
        "gvine411": "#000000"
    }

    traces = {}
    traces["tx_average"] = {}
    traces["rx_average"] = {}
    traces["tx_cumulative"] = {}
    traces["rx_cumulative"] = {}
    traces["tx_average"]["unicast"] = make45(unicast_combined, "tx", False, "tx_average_unicast",
                                             colors["unicast"])
    traces["tx_average"]["norm"] = make45(norm_combined, "tx", False, "tx_average_norm",
                                          colors["norm"])
    traces["tx_average"]["gvine403"] = make45(gvine403_combined, "tx", False,
                                              "tx_average_gvine403", colors["gvine403"])
    traces["tx_average"]["gvine411"] = make45(gvine411_combined, "tx", False,
                                              "tx_average_gvine411", colors["gvine411"])
    traces["rx_average"]["unicast"] = make45(unicast_combined, "rx", False, "rx_average_unicast",
                                             colors["unicast"])
    traces["rx_average"]["norm"] = make45(norm_combined, "rx", False, "rx_average_norm",
                                          colors["norm"])
    traces["rx_average"]["gvine403"] = make45(gvine403_combined, "rx", False,
                                              "rx_average_gvine403", colors["gvine403"])
    traces["rx_average"]["gvine411"] = make45(gvine411_combined, "rx", False,
                                              "rx_average_gvine411", colors["gvine411"])
    traces["tx_cumulative"]["unicast"] = make45(unicast_combined, "tx", True, "tx_cumulative_unicast",
                                             colors["unicast"])
    traces["tx_cumulative"]["norm"] = make45(norm_combined, "tx", True, "tx_cumulative_norm",
                                          colors["norm"])
    traces["tx_cumulative"]["gvine403"] = make45(gvine403_combined, "tx", True,
                                              "tx_cumulative_gvine403", colors["gvine403"])
    traces["tx_cumulative"]["gvine411"] = make45(gvine411_combined, "tx", True,
                                              "tx_cumulative_gvine411", colors["gvine411"])
    traces["rx_cumulative"]["unicast"] = make45(unicast_combined, "rx", True, "rx_cumulative_unicast",
                                                colors["unicast"])
    traces["rx_cumulative"]["norm"] = make45(norm_combined, "rx", True, "rx_cumulative_norm",
                                             colors["norm"])
    traces["rx_cumulative"]["gvine403"] = make45(gvine403_combined, "rx", True,
                                                 "rx_cumulative_gvine403", colors["gvine403"])
    traces["rx_cumulative"]["gvine411"] = make45(gvine411_combined, "rx", True,
                                                 "rx_cumulative_gvine411", colors["gvine411"])

    for graph_type in traces.keys():
        figure = plotly.tools.make_subplots(rows=1, cols=1, print_grid=False)
        for test_case in traces[graph_type].keys():
            figure.append_trace(traces[graph_type][test_case], 1, 1)
        figure['layout'].update(height=300, width=800, title=graph_type)
        plotly.offline.iplot(figure)
