# File: graphsuite.py
# Author: Luke Thomas
# Date: August 14, 2017
# Description: Tests to run on topologies running on rackspace

# System Imports

# 3rd Party Imports
import plotly

# Local imports
import statsuite
from constants import PACKET_COLORS

def make_trace(x_list, y_list, trace_mode, trace_name, show_legend=True, line_width=2,
               line_color="#000000"):
    """Return a trace with attributes corresponding to arguments

    :param x_list: List of x-values to graph
    :param y_list: List of y-values to graph
    :param trace_mode: "line" or "dotted" etc.
    :param trace_name: Name of trace in legend or when hovered
    :param show_legend: (Default=True) Show legend on right side of plotly graph
    :param line_width: (Default=2) Width of line on graph
    :param line_color: (Default="#000000"/black) Color of line on graph
    :return: Trace with passed in attributes
    """
    trace = plotly.graph_objs.Scatter(
        x=x_list,
        y=y_list,
        mode=trace_mode,
        name=trace_name,
        showlegend=show_legend,
        line=dict(
            width=line_width,
            color=line_color
        )
    )
    return trace

def plot_basic_direction(packets_dict, direction, plot_average, graph_title):
    """Graph cumulative packets sent over time.

    Keyword Arguments:
        packets_dict: packets_dict[node_name][direction][second] = bytes_sent_during_that_second
    Returns None.
    """
    traces = {}
    for node_name in packets_dict.keys():
        x = []
        y = []
        sum_packets = 0
        for second in sorted(packets_dict[node_name][direction].keys(), key=int):
            sum_packets += packets_dict[node_name][direction][second]
            x.append(int(second))
            if(plot_average):
                y.append(int(sum_packets/(int(second) + 1)))
            else:
                y.append(sum_packets)
        traces[node_name] = make_trace(x, y, "lines+markers", node_name)
    ordered_nodes = sorted(packets_dict.keys(), key=lambda n: statsuite.get_trailing_number(n))
    num_columns = 1
    num_rows = len(ordered_nodes)
    subplot_titles = []
    for node in ordered_nodes:
        subplot_titles.append(graph_title + "_" + node)
    figure = plotly.tools.make_subplots(rows=num_rows, cols=num_columns,
                                        subplot_titles=subplot_titles, print_grid=False)
    for index in range(len(ordered_nodes)):
        row_num = index + 1
        col_num = 1
        figure.append_trace(traces[ordered_nodes[index]], row_num, col_num)
    figure['layout'].update(height=300*num_rows, width=800, title=graph_title)
    plotly.offline.iplot(figure)


def plot_basic_combined_direction(combined_dict, direction, plot_average, plot_cumulative,
                                  graph_title):
    """

    :param combined_dict: combined_dict[direction][second] = bytes_sent_that_second
    :param direction:
    :param plot_average:
    :param plot_cumulative:
    :param graph_title:
    """
    x = []
    y = []
    sum_packets = 0
    for second in sorted(combined_dict[direction].keys(), key=int):
        sum_packets += combined_dict[direction][second]
        x.append(int(second))
        if(plot_average):
            y.append(sum_packets / (int(second)))
        elif(plot_cumulative):
            y.append(sum_packets)
        else:
            y.append(combined_dict[direction][second])
    trace = make_trace(x, y, "lines", graph_title)
    figure = plotly.tools.make_subplots(rows=1, cols=1, print_grid=False)
    figure.append_trace(trace, 1, 1)
    figure['layout'].update(height=300, width=800, title=graph_title)
    plotly.offline.iplot(figure)


def plot_type_direction(buckets_dict, direction, bucket_size, is_cumulative, graph_title):
    """Graph packets sent by type each second.

    :param buckets_dict: buckets_dict[direction][packet_type][node][second] = bytes_sent
    :param direction: "sent" or "received"
    :param bucket_size: size of bucket
    :param is_cumulative: Graph cumulative packets sent or not
    :param graph_title: Title of graph
    """
    traces = {}
    packets_dict = buckets_dict[direction]
    for packet_type in packets_dict.keys():
        traces[packet_type] = {}
        for node_name in packets_dict[packet_type].keys():
            x = []
            y = []
            sum_packets = 0
            for second in sorted(packets_dict[packet_type][node_name].keys(), key=int):
                sum_packets += packets_dict[packet_type][node_name][second]
                if int(second) % bucket_size == 0:
                    x.append(int(second) / bucket_size)
                    if(is_cumulative):
                        y.append(sum_packets)
                    else:
                        if(int(second) == 0):
                            y.append(sum_packets)
                        else:
                            y.append(sum_packets / (int(second) / bucket_size))
            traces[packet_type][node_name] = make_trace(x, y, "line", node_name + "_" +
                                                        packet_type, line_color=PACKET_COLORS[packet_type])
    ordered_nodes = sorted(packets_dict["beacon"].keys(), key=lambda n: statsuite.get_trailing_number(n))
    num_columns = 1
    num_rows = len(ordered_nodes)
    subplot_titles = []
    for node in ordered_nodes:
        subplot_titles.append(graph_title + "_" + node)
    figure = plotly.tools.make_subplots(rows=num_rows, cols=num_columns,
                                        subplot_titles=subplot_titles, print_grid=False)
    for index in range(len(ordered_nodes)):
        row_num = index + 1
        col_num = 1
        for packet_type in packets_dict.keys():
            figure.append_trace(traces[packet_type][ordered_nodes[index]], row_num, col_num)
    figure['layout'].update(height=300*num_rows, width=800, title=graph_title)
    plotly.offline.iplot(figure)


def make_figure_same_graph(figure, row, col, traces_dict):
    for key in traces_dict.keys():
        figure.append_trace(traces_dict[key], row, col)
    return figure
