Remote Methods In-Depth
=======================

Only methods decorated with ``remote_method()`` are exposed to clients. 

.. literalinclude:: ../code/4.py 
    :lines: 1-10, 26-36

Since python is loosely typed, the server may need to verify the argument types
supplied by the client call. This verification is left to the developer and there 
is no inbuilt support. One may consider using a ``ParameterizedFunction`` for 
this. 

To constrain method excecution for certain states of the StateMachine, one can 
set the state in the decorator. 