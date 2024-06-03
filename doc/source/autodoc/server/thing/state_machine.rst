``StateMachine``
================

.. autoclass:: hololinked.server.state_machine.StateMachine()
    :members: valid, on_enter, on_exit, states, initial_state, machine, current_state
    :show-inheritance:

.. automethod:: hololinked.server.state_machine.StateMachine.__init__

.. automethod:: hololinked.server.state_machine.StateMachine.set_state

.. automethod:: hololinked.server.state_machine.StateMachine.get_state

.. automethod:: hololinked.server.state_machine.StateMachine.has_object

.. note::
    The condition whether to execute a certain method or parameter write in a certain 
    state is checked by the ``EventLoop`` class and not this class. This class only provides 
    the information and handles set state logic.
