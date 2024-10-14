import socket
import threading
import time
import json
import hashlib
import sys
import base64
import secrets
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.asymmetric import utils
from cryptography.hazmat.primitives import serialization
GREEN = "\033[92m"; RED = "\033[91m"; BLUE = "\033[34m"; RESET = "\033[0m"

class Node:
    def __init__(self, node_id, nodes_num, node_port):
        self.node_id = node_id
        self.node_port = node_port
        self.peers = {}
        self.bitcoin = 2
        self.payer = False
        self.last_timer = None
        self.next_timer = None
        self.last_pre_image = None
        self.last_HTLC_condition = None
        self.next_HTLC_condition = None
        self.deposit_value = 0

    def start(self, host, port):
        """start the node and listen for incoming connections."""
        server_thread = threading.Thread(target=self.listen_for_connections, args=(host, port))
        server_thread.start()

    def listen_for_connections(self, host, port):
        """listen for incoming messages from other nodes."""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((host, port))
        server_socket.listen(10)
        print(f"Node {self.node_id} is listening on port {port}")
        while True:
            conn, addr = server_socket.accept()
            ip_, port_ = addr
            threading.Thread(target=self.handle_message, args=(conn,)).start()
        print(f"Node {self.node_id} is no longer listening on port {port}")
    
    def handle_message(self, conn):
        """receive the messages from other nodes."""
        while True:
            message = conn.recv(1024).decode('utf-8')
            message = json.loads(message)
            print(f"Node {self.node_id} received message: {message}")
            # process each message based on its type and the state of the protocol
            threading.Thread(target=self.process_message, args=(message,)).start()
    
    def generate_HTLC_condition(self):
        """generate ZK HTLC condition such that y0 = H(x0), y1 = H(x0^x1), etc."""
        x = []; y = []
        for i in range(4):
            x.append(secrets.randbits(128))
            if i == 0: random_128_bit_number = x[i] 
            else: random_128_bit_number = x[i] ^ random_128_bit_number
            y.append(hashlib.sha256(random_128_bit_number.to_bytes(16, byteorder='big')).hexdigest())
        return x, y

    def verify_pre_image(self, pre_image, condition):
        """verify if the provided pre-image is correct for the condition such that H(pre-image) = condition."""
        random_128_bit_bytes = pre_image.to_bytes(16, byteorder='big')
        hash_object = hashlib.sha256(random_128_bit_bytes)
        if hash_object.hexdigest() == condition:
            return True
        else: return False
    
    def establish_HTLC(self, peer_port, condition, timeout, bt=1):
        """establish an HTLC by depositing money and sending an HTLC message to a peer."""
        json_message = {"type": "HTLC", "timeout": timeout, "condition": condition, "bitcoin": bt}
        if not self.deposit_for_HTLC(bt):   
            print("No enough liqidity to establish HTLC!"); return 
        self.deposit_value = bt
        self.next_timer = threading.Timer(timeout, self.take_back_money, args=(bt,)) 
        self.send_message(peer_port, json_message)
        self.next_timer.start()
        print(f"Node {self.node_id} will pay node {self.node_id+1} {bt} bitcoin iff it provide pre-image in {timeout} seconds")

    def deposit_for_HTLC(self, bt):
        """deposit money for an HTLC connection."""
        if self.bitcoin >= bt:
            self.bitcoin = self.bitcoin - bt
            return True
        else: return False

    def take_back_money(self, bt):
        """take back the money deposited when HTLC connection get expired."""
        print(f"HTLC between node {self.node_id} and {self.node_id + 1} got expired: I'm going to take back money!")
        self.bitcoin = self.bitcoin + bt
        self.next_timer = None

    def reedeem_deposite(self, bt):
        """reedeem the money deposited into the HTLC connection after providing a correct pre-image."""
        print(f"Node {self.node_id} reedeemed money by providing a correct pre-image!")
        self.bitcoin = self.bitcoin + bt
    
    def connection_expire(self):
        """make an HTLC connection expired."""
        self.last_timer = None

    def is_expired(self, timer):
        """"check if a the timer associated with an HTLC connection is valid."""
        if timer: return False
        return True

    def process_message(self, json_message):
        """process the message based on the message type."""
        type = json_message["type"]

        if type == "RELEASE":
            print(f"{GREEN}Node {self.node_id} received a RELEASE message{RESET}")
            pre_image = self.last_pre_image ^ json_message["pre-image"]
            if self.verify_pre_image(pre_image, self.last_HTLC_condition):
                self.next_timer.cancel()
                if not self.payer and not self.is_expired(self.last_timer):
                    self.reedeem_deposite(self.deposit_value)
                    json_message = {"type": "RELEASE", "pre-image": pre_image}
                    self.send_message(node_port - 1, json_message)
                    print(f"I released the pre-image to node {self.node_id - 1}")
            else: print("Verification of pre-image failed!")
            print(f"Current balance is {self.bitcoin}")
        elif type == "HTLC":
            print(f"{GREEN}Node {self.node_id} received an HTLC request{RESET}")
            condition = json_message["condition"]
            timeout = json_message["timeout"]
            bitcoin = json_message["bitcoin"]
            self.last_timer = threading.Timer(timeout, self.connection_expire, args=()) 
            self.last_timer.start()
            print(f"I need to provide the node {self.node_id - 1} with the pre-image before {timeout} seconds")
            # if self.node_id == 3: time.sleep(7)
            # if it already has pre-image, release it and reedeem money:
            if self.last_pre_image and self.verify_pre_image(self.last_pre_image, condition) and not self.is_expired(self.last_timer):
                self.reedeem_deposite(bitcoin)
                json_message = {"type": "RELEASE", "pre-image": self.last_pre_image}
                self.send_message(node_port - 1, json_message)
                print(f"I released the pre-image to node {self.node_id - 1}")
            else: self.establish_HTLC(node_port + 1, self.next_HTLC_condition, timeout-1, bt=bitcoin)
            print(f"Current balance is {self.bitcoin}")
        elif type == "HTLC-CONDITION":
            print(f"{GREEN}Node {self.node_id} received an HTLC-CONDITION{RESET}")
            self.last_HTLC_condition = json_message["yi"]
            self.last_pre_image = json_message["xi"]
            self.next_HTLC_condition = json_message["yi-1"]
        else: print("Invalid message!")
        
    def connect_to_peer(self, peer_host, peer_port):
        """connect to a peer node."""
        try:
            peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_socket.connect((peer_host, peer_port))
            self.peers[peer_port] = peer_socket
            print(f"Node {self.node_id} connected to peer {peer_port}")
        except Exception as e:
            print(f"{RED}Node {self.node_id} failed to connect to peer {peer_port}: {e}{RESET}")

    def send_message(self, peer_port, json_message):
        """send a message to a peer."""
        try:
            self.peers[peer_port].sendall(json.dumps(json_message).encode('utf-8'))
            print(f"{BLUE}Node {self.node_id} sent message to peer {peer_port}: {json_message}{RESET}")
        except Exception as e:
            print(f"{RED}Failed to send message to peer {peer_port}: {e}{RESET}")                    
    
    def pay_bitcoin(self, bitcoin):
        x, y = self.generate_HTLC_condition()
        for i in range(1, len(self.peers) + 1):
            json_message = {"type": "HTLC-CONDITION", "yi": y[nodes_num - 1 - i], 
                            "xi": x[nodes_num - 1 - i], "yi-1": y[nodes_num - i - 2]}
            print(f"{GREEN}Node {self.node_id} sent an HTLC condition{RESET}")
            self.send_message(self.node_port + i, json_message) 
        self.last_pre_image = x[-1]
        self.last_HTLC_condition = y[-1] 
        self.payer = True
        self.establish_HTLC(self.node_port + 1, y[-1], timeout=7, bt=bitcoin)

if __name__ == '__main__':
    nodes_num = int(sys.argv[1])
    base_port = int(sys.argv[2])
    node_id = int(sys.argv[3])
    
    node_port = base_port + node_id
    node = Node(node_id=node_id, nodes_num=nodes_num, node_port=node_port)
    node.start('localhost', node_port); time.sleep(3)   
    
    # connect nodes to each other
    for i in range(1, nodes_num + 1):
        if i != node_id:
            node.connect_to_peer('localhost', base_port + i)

    time.sleep(7)
    execution_time = []
    if node_id == 1: 
        for i in range(2):
            start_time = time.time()
            node.pay_bitcoin(1)
            end_time = time.time()
            execution_time.append(end_time - start_time)
            time.sleep(5)
        print(f"Average execution time for 2 rounds of payment with a ZK version of multi-hop HTLC: {sum(execution_time) / len(execution_time)} seconds")
