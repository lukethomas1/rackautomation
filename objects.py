import json

class Edge:
    def __init__(self, fromNode, toNode):
        self.fromNode = fromNode
        self.toNode = toNode

class Node:
    def __init__(self, id, type, ip, mac, group, connections):
        self.id = id
        self.type = type
        self.ip = ip
        self.mac = mac
        self.group = group
        self.connections = connections


class Subnet:
    def __init__(self, name, ssid, addr, members):
        self.name = name
        self.ssid = ssid
        self.addr = addr
        self.members = members
