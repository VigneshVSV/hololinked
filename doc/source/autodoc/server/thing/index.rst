Thing
=====

.. autoclass:: hololinked.server.thing.Thing
    :members: instance_name, logger, state, rpc_serializer, json_serializer, 
            event_publisher,  
    :show-inheritance:

.. automethod:: hololinked.server.thing.Thing.__init__

.. attribute:: Thing.logger_remote_access
    :type: Optional[bool] 

    set True to access logs of logger remotely 

.. attribute:: Thing.state_machine 
    :type: Optional[hololinked.server.state_machine.StateMachine]

    initialize state machine for controlling method execution and parameter writes

.. automethod:: hololinked.server.thing.Thing.get_thing_description

.. automethod:: hololinked.server.thing.Thing.run
    
.. automethod:: hololinked.server.thing.Thing.run_with_http_server 

.. automethod:: hololinked.server.thing.Thing.exit 

.. toctree::
    :maxdepth: 1
    :hidden:

    state_machine
    thing_meta