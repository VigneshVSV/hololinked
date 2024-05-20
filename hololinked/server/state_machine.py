import typing 
import inspect
from types import FunctionType, MethodType
from enum import EnumMeta, Enum, StrEnum

from ..param.parameterized import ParameterizedMetaclass
from .remote_parameters import ClassSelector, TypedDict, Boolean
from .remote_parameter import RemoteParameter
from .utils import getattr_without_descriptor_read
from .data_classes import RemoteResourceInfoValidator



class StateMachine:
    """
    A container class for state machine related information.  

    Parameters
    ----------
    states: Enum
        enumeration of states 
    initial_state: str 
        initial state of machine 
    on_enter: Dict[str, Callable | RemoteParameter] 
        callbacks to be invoked when a certain state is entered. It is to be specified 
        as a dictionary with the states being the keys
    on_exit: Dict[str, Callable | RemoteParameter]
        callbacks to be invoked when a certain state is exited. 
        It is to be specified as a dictionary with the states being the keys
    **machine:
        state name: List[Callable, RemoteParameter]
            directly pass the state name as an argument along with the methods/parameters which are allowed to execute 
            in that state
    """
    initial_state = ClassSelector(default=None, allow_None=True, constant=True, class_=(Enum, str), 
                        doc="initial state of the machine") # type: typing.Union[Enum, str]
    states = ClassSelector(default=None, allow_None=True, constant=True, class_=(EnumMeta, tuple, list),
                        doc="list/enum of allowed states") # type: typing.Union[EnumMeta, tuple, list]
    on_enter = TypedDict(default=None, allow_None=True, key_type=str,
                        doc="""callbacks to execute when a certain state is entered; 
                        specfied as map with state as keys and callbacks as list""") # typing.Dict[str, typing.List[typing.Callable]]
    on_exit = TypedDict(default=None, allow_None=True, key_type=str,
                        doc="""callbacks to execute when certain state is exited; 
                        specfied as map with state as keys and callbacks as list""") # typing.Dict[str, typing.List[typing.Callable]]
    machine = TypedDict(default=None, allow_None=True, key_type=str, item_type=(list, tuple),
                        doc="the machine specification with state as key and objects as list") # typing.Dict[str, typing.List[typing.Callable, RemoteParameter]]
    exists = Boolean(default=False, readonly=True, fget=lambda self: self._exists, 
                        doc="internally computed, True if states, initial_states and the machine is valid")
    
    def __init__(self, 
            states : typing.Union[EnumMeta, typing.List[str], typing.Tuple[str]], *, 
            initial_state : typing.Union[StrEnum, str], 
            on_enter : typing.Dict[str, typing.Union[typing.List[typing.Callable], typing.Callable]] = {}, 
            on_exit  : typing.Dict[str, typing.Union[typing.List[typing.Callable], typing.Callable]] = {}, 
            # push_state_change_event : bool = False,
            **machine : typing.Dict[str, typing.Union[typing.Callable, RemoteParameter]]
        ) -> None:
        self._exists = False
        self.on_enter = on_enter
        self.on_exit  = on_exit
        # None cannot be passed in, but constant is necessary. 
        self.states   = states
        self.initial_state = initial_state
        self.machine = machine
        # self.push_state_change_event = push_state_change_event
        # if push_state_change_event:
            # self.state_change_event = Event('state-change') 

    # dont think ParameterizedMetaclass is the correct type, should be Parameterized
    def _prepare(self, owner : ParameterizedMetaclass) -> None:
        if self.states is None and self.initial_state is None:    
            self._exists = False 
            self._state = None
            return
        elif self.initial_state not in self.states:
            raise AttributeError(f"specified initial state {self.initial_state} not in Enum of states {self.states}.")

        self._state = self._get_machine_compliant_state(self.initial_state)
        self.owner = owner
        owner_parameters = owner.parameters.descriptors.values()
        owner_methods = [obj[0] for obj in inspect._getmembers(owner, inspect.ismethod, getattr_without_descriptor_read)]
        
        if isinstance(self.states, list):
            self.states = tuple(self.states) # freeze the list of states
        # if hasattr(self, 'state_change_event'):
            # This has to be fixed with "observable" option for properties 
            # self.state_change_event.publisher = owner.event_publisher

        # first validate machine
        for state, objects in self.machine.items():
            if state in self:
                for resource in objects:
                    if hasattr(resource, '_remote_info'):
                        assert isinstance(resource._remote_info, RemoteResourceInfoValidator) # type definition
                        if resource._remote_info.iscallable and resource._remote_info.obj_name not in owner_methods: 
                            raise AttributeError("Given object {} for state machine does not belong to class {}".format(
                                                                                                resource, owner))
                        if resource._remote_info.isparameter and resource not in owner_parameters: 
                            raise AttributeError("Given object {} - {} for state machine does not belong to class {}".format(
                                                                                                resource.name, resource, owner))
                        if resource._remote_info.state is None: 
                            resource._remote_info.state = self._get_machine_compliant_state(state)
                        else: 
                            resource._remote_info.state = resource._remote_info.state + (self._get_machine_compliant_state(state), ) 
                    else: 
                        raise AttributeError(f"Object {resource} was not made remotely accessible," + 
                                    " use state machine with remote parameters and remote methods only.")
            else:
                raise AttributeError("Given state {} not in states Enum {}".format(state, self.states.__members__))
            
        # then the callbacks 
        for state, objects in self.on_enter.items():
            if isinstance(objects, list):
                self.on_enter[state] = tuple(objects) 
            elif not isinstance(objects, (list, tuple)):
                self.on_enter[state] = (objects, )
            for obj in self.on_enter[state]: # type: ignore
                if not isinstance(obj, (FunctionType, MethodType)):
                    raise TypeError(f"on_enter accept only methods. Given type {type(obj)}.")

        for state, objects in self.on_exit.items():
            if isinstance(objects, list):
                self.on_exit[state] = tuple(objects) # type: ignore
            elif not isinstance(objects, (list, tuple)):
                self.on_exit[state] = (objects, ) # type: ignore
            for obj in self.on_exit[state]: # type: ignore
                if not isinstance(obj, (FunctionType, MethodType)):
                    raise TypeError(f"on_enter accept only methods. Given type {type(obj)}.")     
        self._exists = True
        
    def __contains__(self, state : typing.Union[str, StrEnum]):
        if isinstance(self.states, EnumMeta) and state in self.states.__members__:
            return True
        elif isinstance(self.states, tuple) and state in self.states:
            return True
        return False
        
    def _get_machine_compliant_state(self, state) -> typing.Union[StrEnum, str]:
        """
        In case of not using StrEnum or iterable of str, 
        this maps the enum of state to the state name.
        """
        if isinstance(state, str):
            return state 
        if isinstance(state, Enum):
            return state.name
        raise TypeError(f"cannot comply state to a string : {state} which is of type {type(state)}.")
    

    def get_state(self) -> typing.Union[str, StrEnum, None]:
        """
        return the current state. one can also access the property `current state`.
        
        Returns
        -------
        current state: str
        """
        return self._state
        
    def set_state(self, value : typing.Union[str, StrEnum, Enum], 
                #  push_event : bool = True, 
                skip_callbacks : bool = False) -> None:
        """ 
        set state of state machine. Also triggers state change callbacks if skip_callbacks=False. 
        One can also set state using '=' operator of `current_state` property in which case 
        callbacks will be called. If originally an enumeration for the list of allowed states was supplied, 
        then an enumeration member must be used to set state. If a list of strings were supplied, then a string is accepted. 

        Raises
        ------
        ValueError: 
            if the state is not found in the allowed states
        """
        # and pushes a state change event when push_event=True. 
        # and state change event will be pushed.
        # when state change event works, add above in docs.
        if value in self.states:
            previous_state = self._state
            self._state = self._get_machine_compliant_state(value)
            # if push_event and self.push_state_change_event:
            #     self.state_change_event.push({self.owner.instance_name : value})
            if skip_callbacks:
                return 
            if previous_state in self.on_exit:
                for func in self.on_exit[previous_state]:
                    func(self.owner)
            if self._state in self.on_enter:
                for func in self.on_enter[self._state]: 
                    func(self.owner)
        else:   
            raise ValueError("given state '{}' not in set of allowed states : {}.".format(value, self.states))
                
    current_state = property(get_state, set_state, None, 
        doc = """read and write current state of the state machine""")

    def has_object(self, object : typing.Union[RemoteParameter, typing.Callable]) -> bool:
        """
        returns True if specified object is found in any of the states of state machine. 
        Supply unbound method for checking methods as state machine is specified at class level
        when the methods are unbound. 
        """
        for state, objects in self.machine.items():
            if object in objects:
                return True 
        return False
    

