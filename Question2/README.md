# HTLC
### Model Summary
This implementation assumes that given `N` distributed nodes, the first node wants to pay the last node `b` bitcoin by establishing `N-1` HTLC connections. In the beginning, each node tries to connect to other nodes by calling the method `connect_to_peer`. For simplicity, I assume the balance of each node is initially `r` bitcoin and for each payment the first node pays the last node 1 bitcoin.

Upon calling the function `pay_bitcoin` by the first node (sender), it sends a message (`<PAYMENT, b>`) to the last node (receiver). The receiver upon receiving the PAYMENT message, creates an HTLC condition `y` by creating a random 128 bit `x` such that `H(x) = y`. The receiver sends an HTLC-CONDITION message to the sender. 


### How to run the protocol?
There is a file `htlc-init.py` in this repository using which you can specify the total number of nodes and the maximum number of Byzantine nodes. To run the system and HTLC protocol, run the following command:
```
python3 init.py
```


