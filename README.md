# hololinked

### Description

For beginners - `hololinked` is a pythonic package suited for instrument control and data acquisition over network using python.
<br/> 
For those familiar with RPC & web development - `hololinked` is a ZMQ-based RPC toolkit with customizable HTTP end-points. 
The main goal is to develop a pythonic (& pure python) modern package for instrument control through network (SCADA), 
along with native HTTP support for communication with browser clients for browser based UIs.  

##### NOTE - The package is rather incomplete and uploaded only for API showcase and active development. Even RPC logic is not complete. <br/>

- tutorial webpage - [readthedocs](https://hololinked.readthedocs.io/en/latest/examples/index.html)
- [example repository](https://github.com/VigneshVSV/hololinked-examples)
- [helper GUI](https://github.com/VigneshVSV/hololinked-portal) - viewer of object's methods, parameters and events. 
- [web development examples](https://hololinked.dev/docs/category/spectrometer-gui)

### Already Existing Features

Support is already present for the following:

- decorate HTTP verbs directly on object's methods
- declare parameters (based on [`param`](https://param.holoviz.org/getting_started.html)) for validated object attributes on the network
- create named events (based on ZMQ) for asychronous communication with clients. These events are also tunneled as HTTP server-sent events
- control method execution and parameter(or attribute) write with custom finite state machine
- use serializer of your choice (except for HTTP) - Serpent, JSON, pickle etc. & extend serialization to suit your requirement (HTTP Server will support only JSON serializer)
- asyncio compatible - async RPC Server event-loop and async HTTP Server 
- have flexibility in process architecture - run HTTP Server & python object in separate processes or in the same process, combine multiple objects in same server, use multiple
  HTTP servers for same object etc.. 

Again, please check examples or the code for explanations. Documentation is being activety improved. 

### To Install

clone the repository and install in develop mode `pip install -e .` for convenience. The conda env hololinked.yml can also help. 
There is no release to pip available right now.  

### In Development

- Object Proxy (Plain TCP Client- i.e. the RPC part is not fully developed yet)
- Multiple ZMQ Protocols
- HTTP 2.0 
- Database support for storing and loading parameters (based on SQLAlchemy) when object dies and restarts

### Contact

Contributors welcome for all my projects related to hololinked including web apps. Please write to my contact email available at [website](https://hololinked.dev).
