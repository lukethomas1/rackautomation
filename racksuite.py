#!/usr/bin/env python3

# File: racksuite.py
# Author: Luke Thomas
# Date: March 30, 2017
# Description: This is the driver file of the program, delegates to
# commands.py for actual logic

import functions
import commands
import objects
import sys

# Check for valid amount of arguments
if(len(sys.argv) != 2):
    commands.usage()
    exit()

arg = sys.argv[1]

if(arg == "init"):
    commands.initialize()
elif(arg == "iplist"):
    commands.make_iplist()
elif(arg == "configure"):
    commands.configure()
elif(arg == "setup"):
    commands.setup()
elif(arg == "start"):
    commands.start()
elif(arg == "ping"):
    commands.ping()
elif(arg == "msgtest"):
    commands.test_message()
elif(arg == "stats"):
    commands.stats()
elif(arg == "stop"):
    commands.stop()
elif(arg == "delete"):
    commands.delete()
elif(arg == "kill"):
    commands.kill()
else:
    commands.usage()
