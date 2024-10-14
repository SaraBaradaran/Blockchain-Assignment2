# Multi-hop HTLC
### Model Summary
This implementation assumes that given `N` distributed nodes, the first node wants to pay the last node `b` bitcoin by establishing `N-1` HTLC connections. In the beginning, each node tries to connect to other nodes by calling the method `connect_to_peer`. Thus, we have a fully connected network topology in which every node is connected to all the other nodes. For simplicity, I assume the balance of each node is initially `r` bitcoin and for each payment the first node pays the last node 1 bitcoin.

### Normal HTLC
Upon calling the function `pay_bitcoin` by the first node (sender), it sends a message `<PAYMENT, b>` to the last node (receiver). Upon receiving the PAYMENT message, the receiver creates an HTLC condition `y` by creating a random 128-bit `x` such that `H(x) = y`. The receiver sends an HTLC-CONDITION message to the sender. This HTLC-CONDITION message is in the form `<HTLC-CONDITION, condition, b>`. Upon receiving the HTLC-CONDITION message by the sender, it establishes an HTLC to the next node by sending an HTLC message in form `<HTLC, condition, timeout, b>`. For each node, when receiving an HTLC message, if it already has a pre-image corresponding to the HTLC condition, it redeems the money deposited in the HTLC connection and releases the pre-image to the previous node. Otherwise, it creates an HTLC to the next node by using the same condition and a timeout 1s less than the timeout of the incoming HTLC. When a node receives a RELEASE message in the form `<RELEASE, pre-image>`, it verifies the pre-image, and if the verification is successful, it redeems the money deposited and releases the same pre-image to the previous node. It is worth noting that when a node establishes an HTLC connection, it should have more than `b` bitcoin to deposit. Otherwise, the node fails to establish an HTLC.

### Zero-knowledge HTLC
Upon calling the function `pay_bitcoin` by the first node (sender) creates several HTLC conditions `y0, y1, ..., yi` such that `H(x0) = y0, H(x0^x1) = y1, ..., H(x0^x1^...^xi) = yi`. Then, it sends to each node `i` an HTLC-CONDITION message containing `xi`, `yi`, and `yi-1`. Upon receiving the HTLC-CONDITION message by each node, it stores `xi`, `yi`, and `yi-1` and waits to receive an HTLC with the condition `yi`. Upon receiving such an HTLC message by a node, if it already has a pre-image corresponding to the HTLC condition, it redeems the money deposited in the HTLC connection and releases the pre-image to the previous node. Otherwise, it establishes an HTLC with the condition `yi-1` and a timeout 1s less than the timeout of the incoming HTLC to the next node. When a node receives a RELEASE message in the form `<RELEASE, pre-image>`, it verifies the pre-image by calculating `xi XOR pre-image`, and if the verification is successful, it redeems the money deposited and releases `xi XOR pre-image` to the previous node. Again, when a node establishes an HTLC connection, it should have more than `b` bitcoin to deposit. Otherwise, the node fails to establish an HTLC.

In both cases (normal or zk HTLC), the node that establishes an HTLC starts a timer upon sending an HTLC message to the next node. Similarly, the receiver also starts a timer with the same timeout as specified in the HTLC message upon receiving an HTLC message. In fact, here, I assume that we have a synchronous network where the messages have no delay.

### How to run the protocol?
There are two files `htlc-init.py` and `zk-htlc-init.py` in this repository using which you can specify the total number of nodes. To run the system and HTLC protocol for normal case or zero-knowledge version, run the following commands:
```
python3 htlc-init.py
python3 zk-htlc-init.py
```


