.. |module| replace:: hololinked
 
.. |module-highlighted| replace:: ``hololinked``

.. toctree::
    :hidden:
    :maxdepth: 2
    
    Expose Python Classes <self>
    clients
    properties/index
    methods/index
    serializers
    eventloop

    
Expose Python Classes
=====================

Since |module-highlighted| is object oriented, one can start by creating a class to encapsulate 
instrumentation properties and the desirable commands to be issued. Python objects visible
on the network or to other processes are made by subclassing from ``Thing``: 

.. literalinclude:: code/remote_object_inheritance.py
    :language: python
    :linenos:

``instance_name`` is a unique name recognising the instantiated object. It allows multiple 
instruments of same type to be connected to the same computer without overlapping the exposed interface and is therefore a 
mandatory argument to be supplied to the ``Thing`` parent. When maintained unique within the network, it allows 
identification of the hardware itself. Non-experts may use strings composed of 
characters, numbers, dashes and forward slashes, which looks like part of a browser URL, but the general definition is 
that ``instance_name`` should be a URI compatible string.

For attributes (like serial number above), if one requires them to be exposed on the network, one should 
use "properties" defined in ``hololinked.server.properties`` to "parameterize" the object. 

.. literalinclude:: code/thing_with_http_server.py
    :language: python
    :linenos:
    :lines: 2, 5-19

Only properties defined in ``hololinked.server.properties`` or subclass of ``Property`` object (note the captial 'P') 
can be exposed to the network, not normal python attributes or python's own ``property``.

For methods to be exposed on the network, one can use the ``action`` decorator: 

.. literalinclude:: code/thing_with_http_server.py
    :language: python
    :linenos:
    :lines: 3-9, 15-19, 21-28

Arbitrary signature is permitted. Arguments are loosely typed and may need to be constrained with a schema, based 
on the robustness the developer is expecting in their application. However, a schema is optional and it only matters that 
the method signature is matching when requested from a client. 

To start a HTTP server for the ``Thing``, one can call the ``run_with_http_server()`` method after instantiating the 
``Thing``. The supplied ``URL_path`` to the actions and properties are used by this HTTP server: 

.. literalinclude:: code/thing_with_http_server.py
    :language: python
    :linenos:
    :lines: 6-9, 42-47


By default, this starts a server a HTTP server and an INPROC zmq socket (GIL constrained intra-process as far as python is
concerned) for the HTTP server to direct the requests to the ``Thing`` object. All requests are queued by default as the
domain of operation under the hood is remote procedure calls (RPC).  

One can store captured data in properties & push events to supply clients with the measured data:

.. literalinclude:: code/thing_with_http_server.py 
    :language: python   
    :linenos:
    :lines: 6-10, 15-20, 29-41

Events can be defined as class or instance attributes and will be tunnelled as HTTP server sent events without any additional 
serialization overhead. Events are to be used to asynchronously push data to clients.

It can be summarized that the three main building blocks of a network exposed object, or a hardware ``Thing`` are:

* properties - use them to model settings of instrumentation (both hardware and software-only),
  expose general class/instance attributes, captured & computed data
* actions - use them to issue commands to instruments like start and stop acquisition, connect/disconnect etc.
* events - push measured data, create alerts/alarms, inform availability of certain type of data etc.

Each are separately discussed in depth in their respective sections within the doc found on the section navigation.

