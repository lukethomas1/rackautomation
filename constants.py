EMANE_FREQS = ["2.412", "2.417", "2.422", "2.427", "2.432", "2.437", "2.442", "2.447", "2.452",
               "2.457", "2.462"]

REFACTOR_PACKET_TYPES = ["gvine", "beacon", "babel", "update", "summary", "msgquery", "unicast",
                         "msgack"]
PACKET_TYPES = ["beacon", "gvine", "handshake", "babel"]

PACKET_COLORS = {
    "beacon": "0000ff",
    "gvine": "000000",
    "handshake": "ff0000",
    "update": "ffff00",
    "summary": "00ff00",
    "babel": "00ffff",
    "msgquery": "999999", # not currently used
    "unicast": "999999", # not currently used
    "msgack": "ff00ff"
}

GRAPH_COLORS = [
    "0000ff",
    "000000",
    "ff0000",
    "00ff00"
]