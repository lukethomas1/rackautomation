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
    unicast_path = [loc for loc in dump_dirs if "20minutescpsequential" in loc][0]
    norm_path = [loc for loc in dump_dirs if "20minnorm165kb" in loc][0]
    gvine403_path = [loc for loc in dump_dirs if "403pro20min" in loc][0]
    gvine411_path = [loc for loc in dump_dirs if "411pro20min" in loc][0]
    gvine424_path = [loc for loc in dump_dirs if "424pro20min" in loc][0]
    # gvine424_path = [loc for loc in dump_dirs if "424pro_oldperiod20min" in loc][0]
    pi424_path = [loc for loc in dump_dirs if "424pipro20min" in loc][0]

    print("Unicast: " + unicast_path)
    print("Norm: " + norm_path)
    print("Gvine403: " + gvine403_path)
    print("Gvine411: " + gvine411_path)
    print("Gvine424: " + gvine424_path)
    print("Pi424: " + pi424_path)

    unicast_dict = packetsuite.make_basic_packets_dict(unicast_path)
    unicast_combined = packetsuite.make_basic_combined_dict(unicast_dict)
    norm_dict = packetsuite.make_basic_packets_dict(norm_path)
    norm_combined = packetsuite.make_basic_combined_dict(norm_dict)
    gvine403_dict = packetsuite.make_basic_packets_dict(gvine403_path)
    gvine403_combined = packetsuite.make_basic_combined_dict(gvine403_dict)
    gvine411_dict = packetsuite.make_basic_packets_dict(gvine411_path)
    gvine411_combined = packetsuite.make_basic_combined_dict(gvine411_dict)
    gvine424_dict = packetsuite.make_basic_packets_dict(gvine424_path)
    gvine424_combined = packetsuite.make_basic_combined_dict(gvine424_dict)
    pi424_dict = packetsuite.make_basic_packets_dict(pi424_path)
    pi424_combined = packetsuite.make_basic_combined_dict(pi424_dict)

    colors = {
        "unicast": "#e6194b",  # red
        "norm": "#3cb44b",  # green
        "gvine403": "#00ff00",
        "gvine411": "#ff00ff",
        "gvine424": "#000000",
        "pi424": "#035096"  # electric blue
    }

    traces = {
        "tx_average": {
            "unicast": make45(unicast_combined, "tx", False, "tx_average_unicast",
                              colors["unicast"]),
            "norm": make45(norm_combined, "tx", False, "tx_average_norm",
                                          colors["norm"]),
            "gvine403": make45(gvine403_combined, "tx", False, "tx_average_gvine403",
                               colors["gvine403"]),
            "gvine411": make45(gvine411_combined, "tx", False, "tx_average_gvine411",
                               colors["gvine411"]),
            "gvine424": make45(gvine424_combined, "tx", False, "tx_average_gvine424",
                               colors["gvine424"]),
            "pi424": make45(pi424_combined, "tx", False, "tx_average_pi424",
                               colors["pi424"])
        },
        "rx_average": {
            "unicast": make45(unicast_combined, "rx", False, "rx_average_unicast",
                              colors["unicast"]),
            "norm": make45(norm_combined, "rx", False, "rx_average_norm",
                           colors["norm"]),
            "gvine403": make45(gvine403_combined, "rx", False, "rx_average_gvine403",
                               colors["gvine403"]),
            "gvine411": make45(gvine411_combined, "rx", False, "rx_average_gvine411",
                               colors["gvine411"]),
            "gvine424": make45(gvine424_combined, "rx", False, "rx_average_gvine424",
                               colors["gvine424"]),
            "pi424": make45(pi424_combined, "rx", False, "rx_average_pi424",
                               colors["pi424"])
        },
        "tx_cumulative": {
            "unicast": make45(unicast_combined, "tx", True, "tx_cumulative_unicast",
                              colors["unicast"]),
            "norm": make45(norm_combined, "tx", True, "tx_cumulative_norm",
                           colors["norm"]),
            "gvine403": make45(gvine403_combined, "tx", True, "tx_cumulative_gvine403",
                               colors["gvine403"]),
            "gvine411": make45(gvine411_combined, "tx", True, "tx_cumulative_gvine411",
                               colors["gvine411"]),
            "gvine424": make45(gvine424_combined, "tx", True, "tx_cumulative_gvine424",
                               colors["gvine424"]),
            "pi424": make45(pi424_combined, "tx", True, "tx_cumulative_pi424",
                               colors["pi424"])
        },
        "rx_cumulative": {
            "unicast": make45(unicast_combined, "rx", True, "rx_cumulative_unicast",
                              colors["unicast"]),
            "norm": make45(norm_combined, "rx", True, "rx_cumulative_norm",
                           colors["norm"]),
            "gvine403": make45(gvine403_combined, "rx", True, "rx_cumulative_gvine403",
                               colors["gvine403"]),
            "gvine411": make45(gvine411_combined, "rx", True, "rx_cumulative_gvine411",
                               colors["gvine411"]),
            "gvine424": make45(gvine424_combined, "rx", True, "rx_cumulative_gvine424",
                               colors["gvine424"]),
            "pi424": make45(pi424_combined, "rx", True, "rx_cumulative_pi424",
                               colors["pi424"])
        }
    }

    for graph_type in traces.keys():
        figure = plotly.tools.make_subplots(rows=1, cols=1, print_grid=False)
        for test_case in traces[graph_type].keys():
            figure.append_trace(traces[graph_type][test_case], 1, 1)
        figure['layout'].update(height=300, width=800, title=graph_type)
        plotly.offline.iplot(figure)
