RemoteObject In-Depth 
=====================

Change Protocols
----------------

``hololinked`` uses ZeroMQ under the hood to mediate messages between client and server. 
Any ``RemoteObject`` can be constrained to

* only intra-process communication for single process apps 
* inter-process communication for multi-process apps
* network communication using TCP and/or HTTP

simply by specify the requirement as an argument.  