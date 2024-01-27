import typing
import platform
from enum import Enum
from dataclasses import dataclass, asdict, field, fields

from ..param.parameters import String, Boolean, Tuple, TupleSelector
from .constants import (USE_OBJECT_NAME, POST, states_regex, url_regex, http_methods)
from .path_converter import compile_path





class ScadaInfoValidator:
    """
    A validator class for saving remote access related information, this is not for 
    direct usage by the package-end-user. Both callables (functions, methods and those with
    __call__ ) and class/instance attributes store this information as their own attribute
    under the name `scada_info`. The information (and the variable) may be deleted later (currently not) 
    from these objects under _prepare_instance in RemoteObject class. 

    Args:
        URL_path (str): the path in the URL under which the object is accesible for remote-operations.
            Must follow url-regex requirement. If not specified, the name of object
            has to be extracted and used. 
        http_method (str): HTTP method under which the object is accessible. Must be any of specified in 
            decorator methods. 
        state (str): State machine state at which the callable will be executed or attribute can be 
            written (does not apply to read-only attributes). 
        obj_name (str): the name of the object which will be supplied to the ProxyClient class to populate
            its own namespace. For HTTP clients, HTTP method and URL is important and for Proxy clients 
            (based on ZMQ), the obj_name is important. 
        iscoroutine (bool): whether the callable should be executed with async requirements
        is_method  (bool): True when the callable is a function or method and not an arbitrary object with 
            __call__ method. This is required to decide how the callable is bound/unbound.
        is_dunder_callable (bool): Not a function or method, but a callable. Same use case as the previous attribute. 
                    Standard definition of callable is not used in the above two attributes  
    """
    URL_path = String(default=USE_OBJECT_NAME) #, regex=url_regex)
    http_method = TupleSelector(default=POST, objects=http_methods, accept_list=True)
    state = Tuple(default=None, item_type=(Enum, str), allow_None=True, accept_list=True, accept_item=True)
    obj_name = String(default=USE_OBJECT_NAME)
    iscoroutine = Boolean(default=False)
    iscallable = Boolean(default=False)
    isparameter = Boolean(default=False)
    http_request_as_argument = Boolean(default=False)
 
    def __init__(self, **kwargs) -> None:
        for key, value in kwargs.items(): 
            setattr(self, key, value)
        # No full-scale checks for unknown keyword arguments as the class 
        # is used by the developer, so please try to be error-proof
    
    def create_dataclass(self, obj : typing.Optional[typing.Any] = None, 
                            bound_obj : typing.Optional[typing.Any] = None) -> "ScadaInfoData":
        """
        For a plain, faster and uncomplicated access, a dataclass in created
        """
        return ScadaInfoData(URL_path=self.URL_path, http_method=self.http_method, 
                    state=tuple(self.state) if self.state is not None else None, 
                    obj_name=self.obj_name, iscallable=self.iscallable, iscoroutine=self.iscoroutine,
                    isparameter=self.isparameter, http_request_as_argument=self.http_request_as_argument, 
                    obj=obj, bound_obj=bound_obj) 
        # http method is manually always stored as a tuple


__use_slots_for_dataclass = False
if float('.'.join(platform.python_version().split('.')[0:2])) > 3.10:
    __use_slots_for_dataclass = True


@dataclass# (frozen=True, slots=__use_slots_for_dataclass)
class ScadaInfoData:
    """
    This container class is created by the RemoteObject instance because descriptors (used by ScadaInfoValidator) 
    are generally slower. It is used by the eventloop methods while executing the remote object and is stored under 
    RemoteObject.instance_resources dictionary.
    """
    URL_path : str 
    http_method : str
    state : typing.Optional[typing.Union[typing.Tuple, str]] 
    obj_name : str 
    iscallable : bool 
    iscoroutine : bool
    isparameter : bool
    http_request_as_argument : bool
    obj : typing.Any
    bound_obj : typing.Any 

    def json(self):
        """
        Serilization method to access the container for HTTP clients. Set use_json_method = True 
        in serializers.JSONSerializer instance and pass the object to the serializer directly. 
        """
        # try:
        #     return self._json # accessing dynamic attr from frozen object
        # except AttributeError: # always causes attribute error when slots are True
        json_dict = {}
        for field in fields(self):
            if field.name != 'obj' and field.name != 'bound_obj':
                json_dict[field.name] = getattr(self, field.name)
        # object.__setattr__(self, '_json', json_dict) # because object is frozen 
        return json_dict                 
    

@dataclass
class HTTPServerResourceData:
    """
    Used by HTTPServer instance to decide where to route which instruction

    'what' can be an 'ATTRIBUTE' or 'CALLABLE' (based on isparameter or iscallable) and 'instruction' 
    stores the instructions to be sent to the eventloop. 'instance_name' maps the instruction to a particular 
    instance of RemoteObject
    """
    what : str 
    instance_name : str 
    instruction : str
    http_request_as_argument : bool = field(default=False)
    path_format : typing.Optional[str] = field(default=None) 
    path_regex : typing.Optional[typing.Pattern] = field(default=None)
    param_convertors : typing.Optional[typing.Dict] = field( default=None)
    
    def __init__(self, *, what : str, instance_name : str, fullpath : str, instruction : str, 
                    http_request_as_argument : bool = False) -> None:
        self.what = what 
        self.instance_name = instance_name
        self.fullpath = fullpath
        self.instruction = instruction
        self.http_request_as_argument = http_request_as_argument
       
    def compile_path(self):
        path_regex, self.path_format, param_convertors = compile_path(self.fullpath)
        if self.path_format == self.fullpath and len(param_convertors) == 0:
            self.path_regex = None 
            self.param_convertors = None
        elif self.path_format != self.fullpath and len(param_convertors) == 0:
            raise RuntimeError(f"Unknown path format found '{self.path_format}' for path '{self.fullpath}', no path converters were created.")
        else:
            self.path_regex = path_regex
            self.param_convertors = param_convertors

    def json(self):
        return {
            "what" : self.what, 
            "instance_name" : self.instance_name,
            'fullpath' : self.fullpath,
            "instruction" : self.instruction,
            "http_request_as_argument" : self.http_request_as_argument
        }


@dataclass
class FileServerData: 
    what : str 
    directory : str   
    fullpath : str
    path_format : typing.Optional[str] = field( default=None ) 
    path_regex : typing.Optional[typing.Pattern] = field( default = None )
    param_convertors : typing.Optional[typing.Dict] = field( default = None )

    def json(self):
        return asdict(self)
    
    def compile_path(self):
        path_regex, self.path_format, param_convertors = compile_path(self.fullpath)
        if self.path_format == self.fullpath and len(param_convertors) == 0:
            self.path_regex = None 
            self.param_convertors = None
        elif self.path_format != self.fullpath and len(param_convertors) == 0:
            raise RuntimeError(f"Unknown path format found '{self.path_format}' for path '{self.fullpath}', no path converters were created.")
        else:
            self.path_regex = path_regex
            self.param_convertors = param_convertors
    

@dataclass
class HTTPServerEventData:
    """
    Used by the HTTPServer instance to subscribe to events published by RemoteObject at a certain address. 
    The events are sent to the HTTP clients using server-sent-events. 
    """
    what : str 
    event_name : str 
    socket_address : str 

    def json(self):
        return asdict(self)
    
   


@dataclass
class RPCResourceData:
    """
    Used by Proxy objects to fill attributes & methods in a proxy class.   
    """
    what : str 
    instruction : str
    # below are all dunders, when something else is added, be careful to remember to edit ObjectProxy logic when necessary
    module : typing.Union[str, None]
    name : str
    qualname : str
    doc : typing.Union[str, None]
    kwdefaults : typing.Any 
    defaults  : typing.Any

    def json(self):
        return asdict(self)
    
    def get_dunder_attr(self, __dunder_name : str):
        return getattr(self, __dunder_name.strip('_'))

    def __getstate__(self):
        return self.json()
    
    def __setstate__(self, values):
        for key, value in values.items():
            setattr(self, key, value)

@dataclass
class GUIResources:
    instance_name : str
    events : typing.Dict[str, typing.Any] 
    classdoc : typing.Optional[typing.List[str]]
    inheritance : typing.List
    GUI : typing.Optional[typing.Dict] = field( default=None )
    methods : typing.Dict[str, typing.Any] = field( default_factory=dict )
    parameters : typing.Dict[str, typing.Any] = field( default_factory=dict )
    documentation : typing.Optional[typing.Dict[str, typing.Any]] = field( default=None ) 

    def json(self): 
        return asdict(self)