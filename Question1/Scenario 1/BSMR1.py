import socket
import threading
import time
import json
import hashlib
import sys
import random
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.asymmetric import utils
from cryptography.hazmat.primitives import serialization
GREEN = "\033[92m"; RED = "\033[91m"; BLUE = "\033[34m"; RESET = "\033[0m"

max_faulty_nodes = 0

class Node:
    def __init__(self, node_id, nodes_num, node_port):
        self.node_id = node_id
        self.message_log = []
        self.state = "$"
        self.round = 0
        self.node_port = node_port
        self.is_primary = (self.round == self.node_id)
        self.peers = {}
        self.private_key, self.public_key = self.generate_rsa_keys()
        threading.Thread(target=self.check_if_is_primary, args=()).start()

    def check_if_is_primary(self):
        time.sleep(6) # wait a little to make sure all the nodes start to work
        operations = [1, 2, 3, 4]
        index = 0
        while index < len(operations):
            self.is_primary = (self.round == self.node_id)
            if self.is_primary: 
                self.consensus(operations[index])
                self.round += 1
            index = index + 1; time.sleep(3)

    def generate_rsa_keys(self):
        """generate the pair of public key and private key."""
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = private_key.public_key()
        return private_key, public_key

    def sign_message(self, string_message):
        """sign the message to ensure its validity."""
        byte_message = string_message.encode('utf-8')
        signature = self.private_key.sign(byte_message,
                padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
                hashes.SHA256()
        ); signature_base64 = base64.b64encode(signature).decode('utf-8')
        return signature_base64

    def verify_signature(self, public_key, string_message, signature_base64):
        """check the validity of the message by verifying its signature."""
        try:
            byte_message = string_message.encode('utf-8')
            signature = base64.b64decode(signature_base64.encode('utf-8'))
            public_key.verify(signature, byte_message,
                    padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
                    hashes.SHA256()
            ); return True
        except Exception as e: return False

    def get_string_public_key(self):
        """get the node's public key to send it to other nodes."""
        public_key_pem = self.public_key.public_bytes(
                                encoding=serialization.Encoding.PEM,
                                format=serialization.PublicFormat.SubjectPublicKeyInfo)
        public_key_pem_base64 = base64.b64encode(public_key_pem).decode('utf-8')
        return public_key_pem_base64
    
    def receive_public_key(self, conn):
        """receive the public key of each node."""
        message = conn.recv(1024).decode('utf-8')
        json_message = json.loads(message)
        print(f"{GREEN}Node {self.node_id} received the public key of the node conncted!{RESET}")
        public_key_pem = base64.b64decode(json_message["public-key"].encode('utf-8'))
        public_key = serialization.load_pem_public_key(public_key_pem)
        return public_key

    def start(self, host, port):
        """start the node and listen for incoming connections."""
        server_thread = threading.Thread(target=self.listen_for_connections, args=(host, port))
        server_thread.start()

    def listen_for_connections(self, host, port):
        """listen for incoming messages from other nodes."""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((host, port))
        server_socket.listen(10)
        print(f"Node {self.node_id} listening on port {port}")

        while True:
            conn, addr = server_socket.accept()
            ip_, port_ = addr
            public_key_pem = self.receive_public_key(conn)
            threading.Thread(target=self.handle_message, args=(conn, public_key_pem)).start()
    
    def handle_message(self, conn, public_key_pem):
        """receive the messages from other nodes."""
        while True:
            message = conn.recv(1024).decode('utf-8')
            message = json.loads(message)
            print(f"Node {self.node_id} received message: {message}")
            threading.Thread(target=self.process_message, args=(message, public_key_pem)).start()

    def connect_to_peer(self, peer_host, peer_port):
        """connect to a peer node and send the public key."""
        try:
            peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_socket.connect((peer_host, peer_port))
            self.peers[peer_port] = peer_socket
            print(f"Node {self.node_id} connected to peer {peer_port}")
            self.send_message(peer_port, {"public-key" : self.get_string_public_key()})
            print(f"{BLUE}Node {self.node_id} sent its public key to peer {peer_port}{RESET}")
        except Exception as e:
            print(f"{RED}Node {self.node_id} failed to connect to peer {peer_port}: {e}{RESET}")

    def send_message(self, peer_port, json_message):
        """send a message to a peer."""
        try:
            self.peers[peer_port].sendall(json.dumps(json_message).encode('utf-8'))
            print(f"{BLUE}Node {self.node_id} sent message to peer {peer_port}: {json_message}{RESET}")
        except Exception as e:
            print(f"{RED}Failed to send message to peer {peer_port}: {e}{RESET}")                   

    def send_reply_message(self, vi):
        """send a reply message to the primary after receiving the proposal."""
        json_reply = {"type": "REPLY", "message": vi, "id": self.node_id}
        string_reply = json.dumps(json_reply)
        signed_reply = self.sign_message(string_reply)
        json_message = {"signed_message": signed_reply, "message": string_reply}
        primary_port = self.round + (self.node_port - self.node_id)
        self.send_message(primary_port, json_message)
            
    def process_message(self, packet, public_key_pem):
        """process the message based on the type (proposal, reply, etc)."""
        json_message = json.loads(packet["message"])
        type = json_message["type"]

        if type == "RESULT":
            if self.accept_message(packet, public_key_pem):
                print(f"{GREEN}Node {self.node_id} accepted the RESULT message{RESET}")
                self.state += str(json_message["next_state"])
                self.round += 1
                print(f"{RED}The current state of node {self.node_id} is {self.state}{RESET}")
        elif type == "REPLY" and self.is_primary:
            if self.accept_message(packet, public_key_pem):
                print(f"{GREEN}Node {self.node_id} accepted the REPLY message{RESET}")
                self.message_log.append(json_message)
        elif type == "PROPOSAL":
            if self.accept_message(packet, public_key_pem):
                print(f"{GREEN}Node {self.node_id} accepted the PROPOSAL message{RESET}")
                self.send_reply_message(random.randint(5, 10))
        else: print(f"Invalid message! {json_message}")

    def accept_message(self, packet, replica_public_key):
        """accept a message if its signature is verified"""
        signed_message = packet["signed_message"]
        message = packet["message"]
        valid_msg = self.verify_signature(replica_public_key, message, signed_message)
        if valid_msg: return True
        else: return False

    def consensus(self, vi):
        """primary propose vi to all the otehr nodes and waits for f + 1 reply messages."""
        json_message = {"type": "PROPOSAL", "message": vi}
        string_message = json.dumps(json_message)
        signed_message = self.sign_message(string_message)
        self.message_log.append(json_message)
        for peer_port in self.peers:
            self.send_message(peer_port, {"signed_message": signed_message, "message": string_message})
        threading.Thread(target=self.check_for_next_state, args=()).start()
    
    def check_for_next_state(self):
        """continuously check if f + 1 reply messages has been received."""
        while True:
            unique_ids = set()
            for item in self.message_log:
                if item["type"] == "REPLY": unique_ids.add(item["id"])
            predicate = (len(unique_ids) >= max_faulty_nodes + 1)
            time.sleep(1)
            if predicate: 
                print(f"Primary received at least f + 1 reply messages")
                min_value = min([item["message"] for item in self.message_log])
                self.state += str(min_value)
                print(f"{RED}The current state of node {self.node_id} is {self.state}{RESET}")
                self.message_log = []; break
            else: continue
        self.broadcast_next_state(min_value)

    def broadcast_next_state(self, min_value):
        """broadcast the next state message to all peers."""
        print(f"{GREEN}Node {self.node_id} is going to broadcast RESULT message{RESET}")
        json_message1 = {"type": "RESULT", "next_state": min_value}
        string_message1 = json.dumps(json_message1)
        signed_message1 = self.sign_message(string_message1)

        if self.node_id != 0:
            for peer_port in self.peers:
                self.send_message(peer_port, {"signed_message": signed_message1, "message": string_message1})
            return
        # Node 1 is malicous and it tells 1 node the correct min_value, while it tells the other 2 nodes a wrong value (min_value + 1) as the next state.
        # It causes fork since the messages would not be broadcasted and each node only sends its reply to the primary. 
        # As a result, the other nodes don't know what is the actual min value.
        json_message2 = {"type": "RESULT", "next_state": min_value+1}
        string_message2 = json.dumps(json_message2)
        signed_message2 = self.sign_message(string_message2)
        counter = 0
        for peer_port in self.peers:
            if counter < max_faulty_nodes: self.send_message(peer_port, {"signed_message": signed_message1, "message": string_message1}) 
            else: self.send_message(peer_port, {"signed_message": signed_message2, "message": string_message2}) 
            counter = counter + 1
        print("equivocation is done!")

if __name__ == '__main__':
    nodes_num = int(sys.argv[1])
    base_port = int(sys.argv[2])
    node_id = int(sys.argv[3])
    max_faulty_nodes = int(sys.argv[4])
    
    node_port = base_port + node_id
    node = Node(node_id=node_id, nodes_num=nodes_num, node_port=node_port)
    node.start('localhost', node_port)
    time.sleep(3)
    
    # connect nodes to each other
    for i in range(nodes_num):
        if i != node_id:
            node.connect_to_peer('localhost', base_port + i)
