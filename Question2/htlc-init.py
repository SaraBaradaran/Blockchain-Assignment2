import subprocess
import time

def open_replica_terminals(nodes_num, base_port):
    for i in range(1, nodes_num+1):
        command = f"python3 HTLC.py {nodes_num} {base_port} {i}"
        #subprocess.Popen(["gnome-terminal", "--", "bash", "-c", command])
        subprocess.Popen(["osascript", "-e", f'tell application "Terminal" to do script "{command}"'])

nodes_num = 4
base_port = 5050
open_replica_terminals(nodes_num, base_port)
