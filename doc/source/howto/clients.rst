.. |br| raw:: html

    <br />

Connecting to Things with Clients
=================================

When using a HTTP server, it is possible to use any HTTP client including web browser provided clients like ``XMLHttpRequest`` 
and ``EventSource`` object. This is the intention of providing HTTP support. However, additional possibilities exist which are noteworthy:

Using ``hololinked.client``
---------------------------

To use ZMQ transport methods to connect to the server instead of HTTP, one can use an object proxy available in 
``hololinked.client``. For certain applications, for example, oscilloscope traces consisting of millions of data points, 
or, camera images or video streaming with raw pixel density & no compression, the ZMQ transport may significantly speed 
up the data transfer rate. Especially one may use a different serializer like MessagePack instead of JSON. 
JSON is the default, and currently the only supported serializer for HTTP applications and is still meant to be used 
to interface such data-heavy devices with HTTP clients. Nevertheless, ZMQ transport is simultaneously possible along 
with using HTTP. 
|br|
To use a ZMQ client from a different python process other than the ``Thing``'s running process, one needs to start the 
``Thing`` server using TCP or IPC (inter-process communication) transport methods and **not** with ``run_with_http_server()`` 
method (which allows only INPROC/intra-process communication). Use the ``run()`` method instead and specify the desired 
ZMQ transport layers:

.. literalinclude:: code/rpc.py
    :language: python
    :linenos: 
    :lines: 1-2, 9-13, 62-81

Then, import the ``ObjectProxy`` and specify the ZMQ transport method and ``instance_name`` to connect to the server and 
the object it serves: 

.. literalinclude:: code/rpc_client.py
    :language: python
    :linenos: 
    :lines: 1-9

The exposed properties, actions and events become available on the client. One can use get-set on properties, function 
calls on actions and subscribe to events with a callback which is executed once an event arrives:

.. literalinclude:: code/rpc_client.py 
    :language: python 
    :linenos: 
    :lines: 23-27

One would be making such remote procedure calls from a PyQt graphical interface, custom acquisition scripts or 
measurement scan routines which may be running in the same or a different computer on the network. Use TCP ZMQ transport 
to be accessible from network clients.

.. literalinclude:: code/rpc.py 
    :language: python
    :linenos: 
    :lines: 75, 84-87

Irrespective of client's request origin, whether TCP, IPC or INPROC, requests are always queued before executing. To repeat:

* TCP - raw TCP transport facilitated by ZMQ (therefore, without details of HTTP) for clients on the network. You might 
  need to open your firewall. Currently, neither encryption nor user authorization security is provided, use HTTP if you 
  need these features. 
* IPC - interprocess communication for accessing by other process within the same computer. One can use this instead of 
  using TCP with firewall or single computer applications.
* INPROC - only clients from the same python process can access the server. 

If one needs type definitions for the client because the client does not know the server to which it is connected, one 
can import the server script ``Thing`` and set it as the type of the client as a quick-hack. 

.. literalinclude:: code/rpc_client.py 
    :language: python 
    :linenos: 
    :lines: 15-20

Serializer customization is discussed further in :doc:`Serializer How-To <serializers>`.

Using ``node-wot`` client
-------------------------

``node-wot`` is an interoperable Javascript client provided by the `Web of Things Working Group <https://www.w3.org/WoT/>`_. 
The purpose of this client is to be able to interact with devices with a web standard compatible JSON specification called 
as the "`Thing Description <https://www.w3.org/TR/wot-thing-description11/>`_", which 
allows interoperability irrespective of protocol implementation and application domain. The said JSON specification 
describes the device's available properties, actions and events and provides human-readable documentation of the device 
within the specification itself, enhancing developer experience. |br| 
For example, consider the ``serial_number`` property defined previously, the following JSON schema can describe the property:

.. literalinclude:: code/node-wot/serial_number.json 
    :language: JSON
    :linenos:

Similarly, ``connect`` action and ``measurement_event`` event may be described as follows: 

.. literalinclude:: code/node-wot/actions_and_events.json 
    :language: JSON
    :linenos:

It might be already understandable that from such a JSON specification, it is clear how to interact with the specified property, 
action or event. The ``node-wot`` client consumes such a specification to provide these interactions for the developer. 
``node-wot`` already has protocol bindings like HTTP, CoAP, Modbus, MQTT etc. which can be used in nodeJS or in web browsers. 
Since ``hololinked`` offers the possibility of HTTP bindings for devices, such a JSON Thing description is auto generated by 
the class to be able to use by the node-wot client. To use the node-wot client on the browser:

.. literalinclude:: code/node-wot/intro.js
    :language: javascript
    :linenos: 

There are few reasons one might consider to use ``node-wot`` compared to traditional HTTP client, first and foremost being 
standardisation across different protocols. Irrespective of hardware protocol support, including HTTP bindings from 
``hololinked``, one can use the same API. For example, one can directly issue modbus calls to a modbus device while 
issuing HTTP calls to ``hololinked`` ``Thing``s. Further, node-wot offers validation of property types, action payloads and 
return values, and event data without additional programming effort.   

