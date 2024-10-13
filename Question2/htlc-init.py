import subprocess
import time

def open_replica_terminals(nodes_num, base_port, max_faulty_nodes):
    for i in range(1, nodes_num+1):
        command = f"python3 HTLC.py {nodes_num} {base_port} {i} {max_faulty_nodes}"
        #subprocess.Popen(["gnome-terminal", "--", "bash", "-c", command])
        subprocess.Popen(["osascript", "-e", f'tell application "Terminal" to do script "{command}"'])

max_faulty_nodes = 1
nodes_num = 3 * max_faulty_nodes + 1
base_port = 5050
open_replica_terminals(nodes_num, base_port, max_faulty_nodes)
