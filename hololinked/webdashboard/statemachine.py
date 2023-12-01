import typing

from ..param import Parameterized
from ..param.parameters import ClassSelector, TypedDict, Parameter, Boolean, String
from ..param.exceptions import wrap_error_text

from .baseprops import StringProp
from .axios import AxiosRequestConfig
from .exceptions import raise_PropError



class RemoteFSM:

    machineType  = String        ( default = "RemoteFSM", readonly = True) 
    defaultState = String        ( default = None, allow_None = True )
    subscription = ClassSelector ( default = '', class_ = (AxiosRequestConfig, str))
    states       = TypedDict     ( default = None, key_type = str, item_type = dict, allow_None = True )
    
    def __init__(self, subscription : str, defaultState : str, **states : typing.Dict[str, typing.Any]) -> None:
        self.subscription = subscription
        self.defaultState = defaultState
        if len(states) > 0:
            self.states = states
        else:
            raise ValueError(wrap_error_text("""state machine not complete, please specify key-value pairs 
                of state name vs. props for a valid state machine"""))

    def json(self):
        return {
            'type' : self.machineType,
            'defaultState' : self.defaultState,
            'subscription' : self.subscription,
            'states' : self.states
        }
    


class SimpleFSM:

    machineType  = String        ( default = "SimpleFSM", readonly = True) 
    defaultState = String        ( default = None, allow_None = True )
    states       = TypedDict     ( default = None, key_type = str, item_type = dict, allow_None = True )

    def __init__(self, defaultState, **states : typing.Dict[str, typing.Any]) -> None:
        self.defaultState = defaultState 
        self.states = states
    
    def json(self):
        return {
            'type' : self.machineType,
            'defaultState' : self.defaultState,
            'states' : self.states
        }
    
    
stateMachineKW = frozenset(['onEntry', 'onExit', 'target', 'when'])     

class StateMachineProp(Parameter):

    def __init__(self, default: typing.Any = None, allow_None: bool = False, **kwargs):
        kwargs['doc'] = """apply state machine to a component. 
                    Different props can be applied in different states and only the 
                    state needs to be set to automatically apply the props"""
        super().__init__(default, constant = True, allow_None = allow_None, **kwargs)

    # @instance_descriptor - all descriptors apply only to instance __dict__
    def __set__(self, obj : Parameterized, value : typing.Any) -> None:
        """
        Set the value for this Parameter.

        If called for a Parameterized class, set that class's
        value (i.e. set this Parameter object's 'default' attribute).

        If called for a Parameterized instance, set the value of
        this Parameter on that instance (i.e. in the instance's
        __dict__, under the parameter's internal_name).

        If the Parameter's constant attribute is True, only allows
        the value to be set for a Parameterized class or on
        uninitialized Parameterized instances.

        If the Parameter's readonly attribute is True, only allows the
        value to be specified in the Parameter declaration inside the
        Parameterized source code. A read-only parameter also
        cannot be set on a Parameterized class.

        Note that until we support some form of read-only
        object, it is still possible to change the attributes of the
        object stored in a constant or read-only Parameter (e.g. one
        item in a list).
        """   
        if isinstance(value, (RemoteFSM, SimpleFSM)):
            obj_params = obj.parameters.descriptors
            if value.states is not None: 
                for key, props_dict in value.states.items():
                    to_update = {}
                    if not len(props_dict) > 0:
                        raise_PropError(ValueError("state machine props dictionary empty, please enter few props".format(key)), 
                                        self.owner, "stateMachine")
                    for prop_name, prop_value in props_dict.items(): 
                        if prop_name in stateMachineKW:
                            continue
                        if obj_params.get(prop_name, None) is None:
                            raise_PropError(ValueError("prop name {} is not a valid prop of {}".format(prop_name, self.__class__.__name__)), 
                                            self.owner, "stateMachine")
                        to_update[prop_name] = obj_params[prop_name].validate_and_adapt(prop_value)
                    props_dict.update(to_update) # validators also adapt value so we need to reset it,
                    # may be there is a more efficient way to do this  
        elif not(value is None and self.allow_None):
            raise_PropError(TypeError("stateMachine prop is of invalid type, expected type : StateMachine, given Type : {}".format(
                type(value))), self.owner, "stateMachine")
        
        obj.__dict__[self._internal_name] = value
       


#     key = String()
#     initial = String()
#     type = ClassSelector(objects = ['atomic', 'compound', 'parallel', 'final', 'history'])
#     states = ClassSelector()
#     invoke = ClassSelector()
#     on = ClassSelector()
#     entry = ClassSelector()
#     exit()
#     after 
#     always
#     parent 
#     struct
#     meta 



    


__all__ = ['RemoteFSM', 'SimpleFSM']