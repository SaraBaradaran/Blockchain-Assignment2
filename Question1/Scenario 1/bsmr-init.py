import subprocess
import time

def open_replica_terminals(nodes_num, base_port, max_faulty_nodes):
    for i in range(0, nodes_num):
        command = f"python3 BSMR1.py {nodes_num} {base_port} {i} {max_faulty_nodes}"
        subprocess.Popen(["gnome-terminal", "--", "bash", "-c", command])
        #subprocess.Popen(["osascript", "-e", f'tell application "Terminal" to do script "{command}"'])

max_faulty_nodes = 1
nodes_num = 3 * max_faulty_nodes + 1
base_port = 5070
open_replica_terminals(nodes_num, base_port, max_faulty_nodes)
