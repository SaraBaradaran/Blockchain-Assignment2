# PBFT vs BSMR
### Model Summary
This implementation assumes that given `N` distributed nodes, among which at most `f` ones are faulty, in the beginning, each node tries to connect to other nodes by calling the method `connect_to_peer`. Upon connecting with each peer, the two sides of the connection will exchange their public keys. Now, the system is ready to run the protocol. For simplicity, I assume the state of each node is shown by a string `state`. In this implementation, we have no client. Each time, the primary proposes a number, and the replicas try to reach a consensus on whether they should accept the proposal by executing PBFT. Accepting a proposal means appending the number at the end of the string `state`, which is kept and changed independently by each node.

### Scenario
I implemented a scenario where two protocols result in different outcomes. This scenario stands for equivocation, where the node with id 0 is malicious and intentionally tells different things to different nodes. In BSMR protocol, after calculating the minimum, it tells the `f` node the correct value min, while it tells `f+1` other non-faulty nodes a different value min + 1 as the next block that should be added into the state. This scenario causes fork and safety violations. However, in PBFT protocol, when a primary proposes different values to different nodes, non-faulty replicas will not receive enough commit messages to execute the operations proposed. As a result, after a timeout, they simply ignore the value proposed at that specific round and change their view. Here, I simply increment the current view of each node when a timeout happens, and I do not implement view-change messages. 

### How to run the protocol?
There are two files `bsmr-init.py` and `pbft-init.py` in this repository using which you can specify the total number of nodes and the maximum number of faulty nodes. To run the system PBFT protocol, run the following command:
```
python3 pbft-init.py
```
Also, to run the BSMR protocl, run the following command:
```
python3 bsmr-init.py
```
After executing each script, four terminals would be open where you can see how different messages are going to be exchanged between nodes. 
