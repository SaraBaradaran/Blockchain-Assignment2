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

HTLC_EXPIRE = False

class Node:
    def __init__(self, node_id, nodes_num):
        self.node_id = node_id
        self.next_peer = None
        self.next_peer_public_key = None
        self.bitcoin = 1
        self.last_pre_image = None
        self.private_key, self.public_key = self.generate_rsa_keys()

    def generate_rsa_keys(self):
        """generate the pair of public key and private key"""
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
        """receive the public key of each node or client."""
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
        """listen for incoming messages from other nodes or client."""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((host, port))
        server_socket.listen(10)
        print(f"Node {self.node_id} listening on port {port}")

        while True:
            conn, addr = server_socket.accept()
            ip_, port_ = addr
            public_key_pem = self.receive_public_key(conn)
            self.send_message(conn, {"public-key" : self.get_string_public_key()})
            threading.Thread(target=self.handle_message, args=(conn, public_key_pem)).start()
    
    def handle_message(self, conn, public_key_pem):
        """receive the messages from other nodes or client."""
        while True:
            message = conn.recv(1024).decode('utf-8')
            message = json.loads(message)
            print(f"Node {self.node_id} received message: {message}")
            # process each message based on its type and the state of the protocol
            threading.Thread(target=self.process_message, args=(conn, message, public_key_pem)).start()
    
    def generate_HTLC_condition(self):
        random_128_bit_number = secrets.randbits(128)
        random_128_bit_bytes = random_128_bit_number.to_bytes(16, byteorder='big')
        hash_object = hashlib.sha256(random_128_bit_bytes)
        condition = hash_object.hexdigest()
        return random_128_bit_number, condition

    def verify_pre_image(self, pre_image, condition):
        random_128_bit_bytes = pre_image.to_bytes(16, byteorder='big')
        hash_object = hashlib.sha256(random_128_bit_bytes)
        if hash_object.hexdigest() == condition:
            return True
        else: return False
    
    def establish_HTLC(self, conn, condition, timeout, bt=1):
        json_message = {"type": "HTLC", "timeout": timeout, "condition": condition, "bitcoin": bt}
        if not self.deposit_for_HTLC(bt):   
            print("No enough liqidity to establish HTLC!"); return 
        global HTLC_EXPIRE
        HTLC_EXPIRE = False  
        self.send_message(self.next_peer, json_message)
        timer = threading.Timer(timeout, self.take_back_money, args=(bt,)); timer.start()
        print(f"I started the timer with timeout {timeout}")

        while not HTLC_EXPIRE:
            print("I established an HTLC and now waiting to get the pre-image")
            message = self.next_peer.recv(1024).decode('utf-8')
            json_message = json.loads(message)
            type = json_message["type"]
            if type != "RELEASE": continue
            print(f"{GREEN}Node {self.node_id} received a RELEASE message{RESET}")
            self.last_pre_image = json_message["pre-image"]
            if self.verify_pre_image(self.last_pre_image, condition):
                self.reedeem_deposite(bt)
                HTLC_EXPIRE = True; timer.cancel()
                json_message = {"type": "RELEASE", "pre-image": self.last_pre_image}
                self.send_message(conn, json_message)
        print("End of the HTLC connection!")

    def deposit_for_HTLC(self, bt):
        if self.bitcoin >= bt:
            self.bitcoin = self.bitcoin - bt
            return True
        else: return False

    def take_back_money(self, bt):
        print("I'm going to take back money")
        self.bitcoin = self.bitcoin + bt
        global HTLC_EXPIRE; HTLC_EXPIRE = True

    def reedeem_deposite(self, bt):
        print(f"Node reedeemed money by providing a correct pre-image!")
        self.bitcoin = self.bitcoin + bt

    def process_message(self, conn, json_message, public_key_pem):
        """process the PBFT message based on the phase."""
        type = json_message["type"]

        if type == "RELEASE" and self.last_pre_image == json_message["pre-image"]:
            print("Receiver is provided with the proof")
        if type == "HTLC":
            print(f"{GREEN}Node {self.node_id} received an HTLC request{RESET}")
            condition = json_message["condition"]
            timeout = json_message["timeout"]
            bitcoin = json_message["bitcoin"]
            # if it already has pre-image, send it back and reedeem money and otherwise:
            if self.last_pre_image and self.verify_pre_image(self.last_pre_image, condition):
                self.reedeem_deposite(bitcoin)
                json_message = {"type": "RELEASE", "pre-image": self.last_pre_image}
                self.send_message(conn, json_message)
            else:
                self.establish_HTLC(conn, condition, timeout-1, bt=bitcoin)
        elif type == "PAYMENT":
            print(f"{GREEN}Node {self.node_id} received a PAYMENT request{RESET}")
            self.last_pre_image, condition = self.generate_HTLC_condition()
            bitcoin = json_message["bitcoin"]
            json_message = {"type": "HTLC-CONDITION", "condition": condition, "bitcoin": bitcoin}
            print(f"{GREEN}Node {self.node_id} sent an HTLC condition{RESET}")
            self.send_message(conn, json_message)
        elif type == "HTLC-CONDITION":
            print(f"{GREEN}Node {self.node_id} received an HTLC-CONDITION{RESET}")
            condition = json_message["condition"]
            bitcoin = json_message["bitcoin"]
            self.establish_HTLC(conn, condition, timeout=7, bt=bitcoin)
        
    def connect_to_next_peer(self, peer_host, peer_port):
        """connect to a peer node and send the public key."""
        try:
            peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_socket.connect((peer_host, peer_port))
            self.next_peer = peer_socket
            print(f"Node {self.node_id} connected to peer {peer_port}")
            self.send_message(peer_socket, {"public-key" : self.get_string_public_key()})
            print(f"{BLUE}Node {self.node_id} sent its public key to peer {peer_port}{RESET}")
            self.next_peer_public_key = self.receive_public_key(peer_socket)
        except Exception as e:
            print(f"{RED}Node {self.node_id} failed to connect to peer {peer_port}: {e}{RESET}")
    
    def send_payment_request(self, host, port, json_payment_request):
        try:
            peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_socket.connect((host, port))
            print(f"Node {self.node_id} connected to node {port}")
            self.send_message(peer_socket, {"public-key" : self.get_string_public_key()})
            print(f"{BLUE}Node {self.node_id} sent its public key to peer {port}{RESET}")
            receiver_public_key = self.receive_public_key(peer_socket)
            self.send_message(peer_socket, json_payment_request)
            print(f"{BLUE}Node {self.node_id} sent a payment request to peer {port}{RESET}")
        except Exception as e:
            print(f"{RED}Node {self.node_id} failed to send payment request to {port}: {e}{RESET}")
        return (peer_socket, receiver_public_key)

    def send_message(self, conn, json_message):
        """send a message to a peer."""
        try:
            conn.sendall(json.dumps(json_message).encode('utf-8'))
            print(f"{BLUE}Node {self.node_id} sent message to the peer: {json_message}{RESET}")
        except Exception as e:
            print(f"{RED}Failed to send message to the peer: {e}{RESET}")

if __name__ == '__main__':
    nodes_num = int(sys.argv[1])
    base_port = int(sys.argv[2])
    node_id = int(sys.argv[3])
    max_faulty_nodes = int(sys.argv[4])
    
    node_port = base_port + node_id
    node = Node(node_id=node_id, nodes_num=nodes_num)
    node.start('localhost', node_port); time.sleep(3)
    
    # connect node to the next node
    node.connect_to_next_peer('localhost', (node_id % nodes_num) + base_port + 1)
    print(node.next_peer)

    if node_id == 1:
        time.sleep(3); json_payment_request = {"type": "PAYMENT", "bitcoin": 1}
        conn, receiver_public_key = node.send_payment_request('localhost', base_port + nodes_num, json_payment_request)
        threading.Thread(target=node.handle_message, args=(conn, receiver_public_key)).start()
        


