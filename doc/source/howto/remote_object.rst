.. |module| replace:: hololinked
 
.. |module-highlighted| replace:: ``hololinked``
    
Expose Python Classes
=====================

Since ``hololinked`` is object oriented, one can start by creating a class to encapsulate 
instrumentation properties and the desirable commands to be issued. Python objects visible
on the network or to other processes are made by subclassing from ``RemoteObject``: 


.. literalinclude:: code/1.py
    :language: python
    :linenos:

``instance_name`` is a unique name recognising the instantiated object. It allows multiple 
instruments of same type to be connected to the same computer without overlapping the exposed interface. 
This is mandatory to be supplied to the ``RemoteObject`` parent.  

For attributes like serial number, if one requires them to be exposed on the network, one should 
use "parameters" defined in ``hololinked.server.remote_parameters`` to "parameterize" the object. 

.. literalinclude:: code/2.py
    :language: python
    :linenos:
    :lines: 2-18

Only parameters can be exposed to the network, not normal python attributes.

For methods to be exposed on the network, one can use the ``remote_method`` decorator. 

.. literalinclude:: code/2.py
    :language: python
    :linenos:
    :lines: 3-12, 19-23
    

To start a RemoteObject server, one can call the ``run()`` method 

.. literalinclude:: code/2.py
    :language: python
    :linenos:
    :lines: 1-9, 39-


By default, this starts a server which listens at three levels - a TCP socket, 
interprocess communication & intra-process communication. Because the speed of message 
passing is different for each transport method, these three possibilities are available.   
One can also choose which transport method needs to be used (discussed later). 

To also use a HTTP server which takes benefit of specifed URL paths & HTTP request methods, 
pass an instance of ``HTTPServer`` to the ``run()``. When passed to the ``run()``, 
the ``HTTPServer`` will communicate with the ``RemoteObject`` through the fastest means 
possible - intra-process communication. 

.. literalinclude:: code/2.py
    :language: python
    :linenos:
    :lines: 1, 40-

The ``HTTPServer`` and ``RemoteObject`` will run in different threads and the python global 
interpreter lock will still allow only one thread at a time. 

One can store captured data in parameters & push events to supply clients with the measured 
data: 

.. literalinclude:: code/2.py
    :language: python
    :linenos:
    :lines: 1-9, 15-21, 27-38

When using HTTP server, events will also be tunneled as HTTP server sent events at the specifed URL 
path. 

Endpoints available to HTTP server are constructed as follows: 

.. list-table::

    *   - remote resource 
        - default HTTP request method 
        - URL construction
    *   - parameter read
        - GET
        - `http(s)://{domain name}/{instance name}/{parameter URL path}`
    *   - parameter write 
        - PUT 
        - `http(s)://{domain name}/{instance name}/{parameter URL path}`
    *   - method execution 
        - POST
        - `http(s)://{domain name}/{instance name}/{method URL path}`
    *   - Event 
        - GET
        - `http(s)://{domain name}/{instance name}/{event URL path}`


Of course, plain calls to the parameter, event or method is possible through 
non-HTTP RPC clients. 

.. literalinclude:: code/3.py
    :language: python
    :linenos: 
    :lines: 1-16

If one needs type definitions for the client because the client does not know 
which server to which its connected, one can import the server script and set 
it as the type of the client. 

.. literalinclude:: code/3.py 
    :language: python
    :linenos: 
    :lines: 18-