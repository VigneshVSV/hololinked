# DAQPY

### Description

For beginners - `daqpy` is a pattern suited for instrument control and data acquisition over network using python.
<br/> 
For those familiar with RPC & web development - `daqpy` is a ZMQ-based RPC toolkit with customizable HTTP end-points. The intended application 
is, as stated before, instrument control/data acquisition or controlling generic python object(-instance)s. 
<br />
The main goal is to develop a pythonic (& pure python) modern package for instrument control through network (SCADA), 
along with native HTTP support for communication with browser clients for browser based UIs.  

##### NOTE - The package is rather incomplete and uploaded only for API showcase and active development. Even RPC logic is not complete. <br/>

- tutorial webpage - (will be filled)
- example repository - https://github.com/VigneshVSV/daqpy-examples
- helper GUI - https://github.com/VigneshVSV/daqpy-portal
- custom GUI examples - (will be filled)

### Already Existing Features

Support is already present for the following:

- decorate HTTP verbs directly on object's methods
- declare parameters (based on [`param`](https://param.holoviz.org/getting_started.html)) for validated object attributes on the network
- create named events (based on ZMQ) for asychronous communication with clients. These events are also tunneled as HTTP server-sent events
- control method execution and parameter(or attribute) write with finite state machine
- use serializer of your choice (except for HTTP) - Serpent, JSON, pickle etc. & extend serialization to suit your requirement (HTTP Server will support only JSON serializer)
- asyncio compatible - async RPC Server event-loop and async HTTP Server 
- have flexibility in process architecture - run HTTP Server & python object in separate processes or in the same process, combine multiple objects in same server etc. 

Again, please check examples for how-to & explanations of the above. 

### To Install

clone the repository and install in develop mode `pip install -e .` for convenience. The conda env daqpy.yml can also help. 

### In Development

- Object Proxy (Plain TCP Client- i.e. the RPC part is not fully developed yet)
- Multiple ZMQ Protocols - currently only IPC protocol is supported
- HTTP 2.0 
- Database support for storing and loading parameters (based on SQLAlchemy) when object dies and restarts




