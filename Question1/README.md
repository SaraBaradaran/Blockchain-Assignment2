# PBFT vs BSMR
### Model Summary
This implementation assumes that given `N` distributed nodes, among which at most `f` ones are faulty, in the beginning, each node tries to connect to other nodes by calling the method `connect_to_peer`. Upon connecting with each peer, the two sides of the connection will exchange their public keys. Now, the system is ready to run the protocol. For simplicity, I assume the state of each node is shown by a string `state`. In this implementation, we have no client. Each time, the primary proposes a number, and the replicas try to reach a consensus on whether they should accept the proposal. Accepting a proposal means appending the number at the end of the string `state`, which is kept and changed independently by each node.

### Scenario 1
This scenario stands for equivocation, where the node with id 0 is malicious and intentionally tells different things to different nodes. In BSMR protocol, the malicious primary proposes a value vi to all the nodes. After receiving replies and calculating the minimum, it tells the `f` node the correct value `min`, while it tells `f+1` other non-faulty nodes a different value `min+1` as the next block that should be added into the state. This scenario causes a fork and safety violations. 

### Scenario 2
This scenario also stands for equivocation, where the node with id 0 is malicious and intentionally tells different things to different nodes, but this time in a different phase of the protocol. In BSMR protocol, the malicious primary proposes the `f` node a value `vi`, while it proposes other non-faulty nodes a different `vi+1`. Now, if all the nodes propose values bigger than `vi+1`, then the actual min value sent for nodes in group 1 is `vi`, while the actual min value for nodes in group 2 is `vi+1`. This scenario also causes forks and safety violations.

### Why does PBFT act differently?
In PBFT protocol, when a primary proposes different values to different nodes or sends a commit message for different proposals, non-faulty replicas will not receive enough commit messages to execute the operations proposed. As a result, after a timeout, they simply ignore the value proposed at that specific round and change their view. Here, I simply increment the current view of each node when a timeout happens, and I do not implement view-change messages. 

Please find a detailed description of the two scenarios in the PDF file.

<b>Each protocol is executed for 4 different rounds, and there are little delays between the rounds. After finishing each round, the state of each node will be printed on the stdout in red. Since node 0 is malicious and tries to do equivocation, in PBFT, after the first round of  protocol execution, the nodes do not reach a consensus after a specific time period, causing a timeout and changing view and the primary for the next round. Thus, we have 3 state transitions in PBFT since in the first round of execution, no state transition will happen due to a lack of consensus between the nodes. By the way, the safety property would not be violated, and after 4 rounds of PBFT execution, the state of all nodes would be a string `$234`. In the BSMR protocol, since node 0 is malicious, it successfully does an equivocation in the first round of execution. Thus, half of the nodes will move to state `1`, and the remaining nodes will move to state `2` after the first round, causing a fork and safety property violations. After 4 rounds of execution, half of the nodes reach the state `$2234`, while the other half reach the state `$1234`.</b>

### How to run the protocol?
For each scenario, there is a file `bsmr-init.py` and for PBFT there is a file `pbft-init.py` in this repository using which you can specify the total number of nodes and the maximum number of faulty nodes. To run the system PBFT protocol, run the following command:
```
python3 pbft-init.py
```
Also, to run the each scenario of BSMR protocl, run the following command:
```
python3 bsmr-init.py
```
After executing each script, four terminals would be open where you can see how different messages are going to be exchanged between nodes. Please wait to see all the 4 rounds of protocol execution for each scenario.
