ZMQ Message Brokers
===================

``hololinked`` uses ZMQ under the hood to implement a RPC server. All requests, either coming through a HTTP 
Server (from a HTTP client/web browser) or an RPC client are routed via the RPC Server to queue them before execution. 

Since a RPC client is available in ``hololinked`` (or will be made available), it is suggested to use the HTTP 
server for web development practices (like REST-similar endpoints) and not for RPC purposes. The following picture
summarizes how messages are routed to the ``RemoteObject``.

.. image:: ../../../_static/architecture.drawio.light.svg
    :class: only-light

.. image:: ../../../_static/architecture.drawio.dark.svg
    :class: only-dark


The message brokers are divided to client and server types. Servers recieve a message before replying & clients 
initiate message requests.     

See documentation of ``RPCServer`` for details. 

.. toctree::
    :maxdepth: 1

    base_zmq
    zmq_server
    rpc_server
    zmq_client



