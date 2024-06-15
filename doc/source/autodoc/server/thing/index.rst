``Thing``
=========

.. autoclass:: hololinked.server.thing.Thing()
    :members: instance_name, logger, state, zmq_serializer, http_serializer, 
            event_publisher,  
    :show-inheritance:

.. automethod:: hololinked.server.thing.Thing.__init__

.. attribute:: Thing.state_machine 
    :type: Optional[hololinked.server.state_machine.StateMachine]

    initialize state machine for controlling method/action execution and property writes

.. attribute:: Thing.logger_remote_access
    :type: Optional[bool] 

    set False to prevent access of logs of logger remotely 

.. attribute:: Thing.use_default_db
    :type: Optional[bool] 

    set True to create a default SQLite database. Mainly used for storing properties and autoloading them when the object
    dies and restarts.

.. automethod:: hololinked.server.thing.Thing.get_thing_description

.. automethod:: hololinked.server.thing.Thing.run_with_http_server 
    
.. automethod:: hololinked.server.thing.Thing.run

.. automethod:: hololinked.server.thing.Thing.exit 

.. toctree::
    :maxdepth: 1
    :hidden:

    state_machine
    network_handler
    thing_meta