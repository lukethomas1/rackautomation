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
        traces[node_name] = make_trace(x, y, "lines", node_name)
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
    figure['layout'].update(height=600*num_rows, width=1000, title=graph_title)
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
            y.append(sum_packets / (int(second) + 1))
        elif(plot_cumulative):
            y.append(sum_packets)
        else:
            y.append(combined_dict[direction][second])
    trace = make_trace(x, y, "lines", graph_title)
    figure = plotly.tools.make_subplots(rows=1, cols=1, print_grid=False)
    figure.append_trace(trace, 1, 1)
    figure['layout'].update(height=600, width=1000, title=graph_title)
    plotly.offline.iplot(figure)


def plot_type_direction(buckets_dict, direction, bucket_size, graph_type, graph_title,
                                                                        download=False):
    """Graph packets sent by type each second.

    :param buckets_dict: buckets_dict[direction][packet_type][node][second] = bytes_sent
    :param direction: "sent" or "received"
    :param bucket_size: size of bucket
    :param graph_type: 0 = each_second, 1 = cumulative, 2 = average
    :param is_cumulative: Graph cumulative packets sent or not
    :param is_average: Graph average if not cumulative
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
                    if graph_type == 1:
                        y.append(sum_packets)
                    elif graph_type == 2:
                        y.append(sum_packets / ((int(second) / bucket_size) + 1))
                    elif graph_type == 0:
                        y.append(packets_dict[packet_type][node_name][second])
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
    figure['layout'].update(height=600*num_rows, width=1000, title=graph_title)
    if download:
        plotly.offline.iplot(figure, image="png", filename=graph_title)
    else:
        plotly.offline.iplot(figure)


def make_figure_same_graph(figure, row, col, traces_dict):
    for key in traces_dict.keys():
        figure.append_trace(traces_dict[key], row, col)
    return figure


def plot_stop_dict(stop_dict, direction, graph_title):
    traces = {}
    dir_dict = stop_dict[direction]
    for node_name in dir_dict.keys():
        x = []
        y = []
        for frag_index in sorted(dir_dict[node_name].keys(), key=int):
            x.append(dir_dict[node_name][frag_index])
            y.append(int(frag_index))
        traces[node_name] = make_trace(x, y, "markers", node_name)

    ordered_nodes = sorted(dir_dict.keys(), key=lambda n: statsuite.get_trailing_number(n))
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


def make_45_combined_trace(combined_dict, direction, plot_cumulative, trace_title, color):
    """

    :param combined_dict: combined_dict[direction][second] = bytes_sent_that_second
    :param direction: tx or rx
    :param plot_cumulative: Should this plot be cumulative or average
    :param trace_title: Title of the trace
    :param color: Color of the line trace
    """
    x = []
    y = []
    bucket_size = 45
    num_buckets = 26
    last_second = bucket_size * num_buckets
    sum_packets = 0
    for second in range(last_second + 1):
        if str(second) in combined_dict[direction].keys():
            sum_packets += combined_dict[direction][str(second)]
        if second % bucket_size == 0:
            x.append(second / bucket_size)
            if plot_cumulative:
                y.append(sum_packets)
            else:  # plot average
                bucket_index = second / bucket_size
                if bucket_index != 0:
                    y.append(int(sum_packets / bucket_index))
                else:
                    y.append(sum_packets)
    return make_trace(x, y, "lines", trace_title, line_color=color)

def make_type_trace(seconds_dict, direction, packet_type, node_name, bucket_size, graph_type,
                    color, trace_name, download=False):
    """
    Make a trace for packets sent in a direction of a certain type

    :param seconds_dict:  seconds_dict[direction][packet_type][node][second] = bytes
    :param direction: "tx" or "rx"
    :param bucket_size: size of bucket
    :param graph_type: 0 = each_second, 1 = cumulative, 2 = average
    :param trace_name: label of trace in graph legend
    :return:
    """

    packet_type_dict = seconds_dict[direction][packet_type][node_name]

    x = []
    y = []
    sum_packets = 0
    for second in sorted(packet_type_dict.keys(), key=int):
        sum_packets += packet_type_dict[second]
        if int(second) % bucket_size == 0:
            x.append(int(second) / bucket_size)
            if graph_type == 0:
                y.append(packet_type_dict[second])
            elif graph_type == 1:
                y.append(sum_packets)
            elif graph_type == 2:
                y.append(sum_packets / ((int(second) / bucket_size) + 1))
    trace = make_trace(x, y, "line", trace_name, line_color=color)
    return trace

def plot_type_comparison(trace_dict, graph_configs):
    for packet_type in trace_dict.keys():
        for cnfg in graph_configs:
            graph_type = cnfg[2]
            traces = []
            for db_path in trace_dict[packet_type][graph_type].keys():
                traces.append(trace_dict[packet_type][graph_type][db_path])
            layout = dict(
                title=packet_type + "-" + graph_type,
                xaxis=dict(title="Time (Seconds)"),
                yaxis=dict(title="Bytes"),
                height=600,
                width=1000
            )
            figure = dict(data=traces, layout=layout)
            plotly.offline.iplot(figure)
