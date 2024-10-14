# HTLC
### Model Summary
This implementation assumes that given `N` distributed nodes, the first node wants to pay the last node `b` bitcoin by establishing `N-1` HTLC connections. In the beginning, each node tries to connect to other nodes by calling the method `connect_to_peer`. For simplicity, I assume the balance of each node is initially `r` bitcoin and for each payment the first node pays the last node 1 bitcoin.

### Normal HTLC
Upon calling the function `pay_bitcoin` by the first node (sender), it sends a message `<PAYMENT, b>` to the last node (receiver). The receiver upon receiving the PAYMENT message, creates an HTLC condition `y` by creating a random 128 bit `x` such that `H(x) = y`. The receiver sends an HTLC-CONDITION message to the sender. This HTLC-CONDITION message is in form `<HTLC-CONDITION, condition, b>` Upon receiving HTLC-CONDITION message by sender, it establish an HTLC to the next node by sending an HTLC message in form `<HTLC, condition, timeout, b>`. For each node, when receiving an HTLC message, if it already has a pre-image corresponding to the HTLC condition, it reedeem the money deposited in the HTLC connection and release the pre-image to the previous node. Otherwise, it creates an HTLC to the next node by using the same condition and a timeout 1s less than the timeout of the incomming HTLC. When a node receives a RELEASE message in the form `<RELEASE, pre-image>`, it verifies the pre-image and if the verification is successfull, it release the smae pre-image to the previous node. In is worth noting that when a node establish an HTLC connection, it should have more than `b` bitcoin to deposite. Otherwise, the node fails to establish an HTLC.

### Zero-knowledge HTLC

### How to run the protocol?
There is a file `htlc-init.py` in this repository using which you can specify the total number of nodes and the maximum number of Byzantine nodes. To run the system and HTLC protocol, run the following command:
```
python3 init.py
```


