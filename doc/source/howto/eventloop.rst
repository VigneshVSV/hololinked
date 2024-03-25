Customizing Eventloop
=====================

EventLoop object is a server side object that runs both the ZMQ message listeners & executes the operations 
of the ``RemoteObject``. Operations only include parameter read-write & method execution, events are pushed synchronously
wherever they are called. 
EventLoop is also a ``RemoteObject`` by itself. A default eventloop is created by ``RemoteObject.run()`` method to 
simplify the usage, however, one may benefit from using it directly.

To start a ``RemoteObject`` using the ``EventLoop``, pass the instantiated object to the ``__init__()``:

.. literalinclude:: code/eventloop/run_eq.py 
    :language: python 
    :linenos: 

Exposing the EventLoop allows to add new ``RemoteObject``'s on the fly whenever necessary. To run multiple objects 
in the same eventloop, pass the objects as a list. 

.. literalinclude:: code/eventloop/list_of_devices.py 
    :language: python 
    :linenos: 
    :lines: 7-

Setting threaded to True calls each RemoteObject in its own thread. 

.. literalinclude:: code/eventloop/threaded.py 
    :language: python 
    :linenos: 
    :lines: 20-