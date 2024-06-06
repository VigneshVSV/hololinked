Connect HTTP server to RemoteObject
===================================

To also use a HTTP server, one needs to specify URL paths and HTTP request verb for the parameters and methods. 

one needs to start a instance of ``HTTPServer`` before ``run()``. When passed to the ``run()``, 
the ``HTTPServer`` will communicate with the ``RemoteObject`` through the fastest means 
possible - intra-process communication. 

.. literalinclude:: code/thing_with_http_server.py
    :language: python
    :linenos:

The ``HTTPServer`` and ``RemoteObject`` will run in different threads and the python global 
interpreter lock will still allow only one thread at a time. 

One can store captured data in parameters & push events to supply clients with the measured 
data: 

.. literalinclude:: code/thing_with_http_server.py
    :language: python
    :linenos:

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
