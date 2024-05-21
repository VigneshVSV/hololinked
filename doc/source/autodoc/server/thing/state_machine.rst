StateMachine
------------

.. autoclass:: hololinked.server.state_machine.StateMachine
    :members: 
    :show-inheritance:

.. note::
    The condition whether to execute a certain method or parameter write in a certain 
    state is checked by the ``EventLoop`` class and not this class. This class only provides 
    the information and handles set state logic.
