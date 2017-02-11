#!/usr/bin/env python3
import json
import objects
import pyrebase


config = {
    "apiKey": "AIzaSyBo7i1pJOOyTbMLwOvM4pabOqrGwTEzgCc",
    "authDomain": "gvdb-c4e0c.firebaseapp.com",
    "databaseURL": "https://gvdb-c4e0c.firebaseio.com",
    "storageBucket": "gvdb-c4e0c.appspot.com",
}
firebase = pyrebase.initialize_app(config);
db = firebase.database()
saves = db.child("saves").get().val()

save_file = input("Input Save File Name: ")

json_string = saves[save_file]['string']

load = json.loads(json_string)

subnets = []
nodes = []

for index in range(len(load)):
    if('name' in load[0]):
        subnets.append(load.pop(0))
    else:
        nodes.append(load.pop(0))
print()
print("---------------------")

print()
print("Subnet Names:")
for subnet in subnets:
    print(str(subnet['name']))

print()
print("Node Names:")
for node in nodes:
    print(str(node['id']))

print()
print("Thats all folks")
