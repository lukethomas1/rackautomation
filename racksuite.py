import functions
import commands
import objects
import sys

if(len(sys.argv) != 2):
    commands.usage()
    exit()

arg = sys.argv[1]
if(arg == "initialize"):
    commands.initialize()
elif(arg == "setup"):
    commands.setup()
elif(arg == "run"):
    commands.run()
elif(arg == "stats"):
    commands.stats()
elif(arg == "stop"):
    commands.stop()
elif(arg == "delete"):
    commands.delete()
else:
    commands.usage()
