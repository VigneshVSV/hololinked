RemoteObject
============

.. autoclass:: hololinked.server.remote_object.RemoteObject
    :members: instance_name, logger, state, rpc_serializer, json_serializer, 
            event_publisher,  
    :show-inheritance:

.. automethod:: hololinked.server.remote_object.RemoteObject.__init__

.. attribute:: RemoteObject.logger_remote_access
    :type: Optional[bool] 

    set True to access logs of logger remotely 

.. attribute:: RemoteObject.state_machine 
    :type: Optional[hololinked.server.state_machine.StateMachine]

    initialize state machine for controlling method execution and parameter writes

.. automethod:: hololinked.server.remote_object.RemoteObject.get_thing_description

.. automethod:: hololinked.server.remote_object.RemoteObject.run
    
.. automethod:: hololinked.server.remote_object.RemoteObject.run_with_http_server 
    
.. automethod:: hololinked.server.remote_object.RemoteObject.exit 

.. toctree::
    :maxdepth: 1
    :hidden:

    state_machine
    remote_object_meta