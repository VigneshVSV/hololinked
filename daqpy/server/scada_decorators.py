from types import FunctionType
from inspect import iscoroutinefunction, getfullargspec
from typing import Any, Optional, Union, Callable
import typing
from enum import Enum
from functools import wraps
from dataclasses import dataclass, asdict, field, fields

from ..param.parameters import String, Selector, Boolean, Tuple, TupleSelector

from .constants import (USE_OBJECT_NAME, UNSPECIFIED, HTTP, PROXY, GET, POST, PUT, DELETE,
    states_regex, url_regex, http_methods, WRAPPER_ASSIGNMENTS)
from .utils import wrap_text
from .path_converter import compile_path



class ScadaInfoValidator:
    """
    A validator class for saving remote access related information, this is not for 
    direct usage by the package-end-user. Both callables (functions, methods and those will
    __call__ ) and class/instance attributes store this information as their own attribute
    under the name `scada_info`. The information (and the variable) may be deleted later (currently not) from these 
    objects under _prepare_instance in RemoteObject class. 

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
    access_type  = TupleSelector( default=(HTTP, PROXY), objects=[HTTP, PROXY, None], accept_list=True)
    URL_path     = String  ( default=USE_OBJECT_NAME )#, regex = url_regex)
    http_method  = TupleSelector( default=POST, objects=http_methods, accept_list=True)
    state        = Tuple ( default=None, item_type=(Enum, str), allow_None=True, accept_list=True, accept_item=True )
    obj_name     = String  ( default=USE_OBJECT_NAME)
    iscoroutine = Boolean ( default=False )
    iscallable  = Boolean ( default=False )
    isparameter  = Boolean ( default=False )
    http_request_as_argument = Boolean ( default=False )
 
    def __init__(self, **kwargs) -> None:
        for key, value in kwargs.items(): 
            setattr(self, key, value)
        # No full-scale checks for unknown keyword arguments as the class 
        # is used by the developer, also dont
    
    def create_dataclass(self, obj : typing.Optional[Any] = None, 
                            bound_obj : typing.Optional[typing.Any] = None) -> "ScadaInfoData":
        """
        For a plain, faster and uncomplicated access, a dataclass in created
        """
        return ScadaInfoData(access_type = self.access_type, URL_path = self.URL_path, 
                    http_method = self.http_method, state = tuple(self.state) if self.state is not None else None, 
                    obj_name = self.obj_name, iscallable = self.iscallable, iscoroutine = self.iscoroutine,
                    isparameter = self.isparameter, http_request_as_argument = self.http_request_as_argument, 
                    obj=obj, bound_obj=bound_obj ) 
        # http method is manually always stored as a tuple


@dataclass(frozen = True) # slots = True for newer versions very desirable
class ScadaInfoData:
    """
    This container class is created by the RemoteObject instance because descriptors (used by ScadaInfoValidator) 
    are generally slower. It is used by the eventloop methods while executing the remote object and is stored under 
    RemoteObject.instance_resources dictionary.
    """
    access_type : str
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
        try:
            return self._json # accessing dynamic attr from frozen object
        except AttributeError:
            json_dict = {}
            for field in fields(self):
                if field.name != 'obj' and field.name != 'bound_obj':
                    json_dict[field.name] = getattr(self, field.name)
            object.__setattr__(self, '_json', json_dict) # because object is frozen 
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
    http_request_as_argument : bool = field( default = False )
    path_format : typing.Optional[str] = field( default=None ) 
    path_regex : typing.Optional[typing.Pattern] = field( default = None )
    param_convertors : typing.Optional[typing.Dict] = field( default = None )
    
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
    

@dataclass(frozen = True)
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
    
   


@dataclass(frozen = True)
class ProxyResourceData:
    """
    Used by Proxy objects to fill attributes & methods in a proxy class.   
    """
    what : str 
    instruction : str 
    module  : Union[str, None]
    name : str
    qualname : str
    doc : Union[str, None]
    kwdefaults : Any 
    defaults  : Any

    def json(self):
        return asdict(self)
    

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
    

def wrap_method(method : FunctionType):
    """wraps a methods with useful operations before and after calling a method.
    Old : use case not decided.

    Args:
        method (FunctionType): function or callable

    Returns:
        method : returns a wrapped callable, preserving information regarding signature 
            as much as possible
    """
   
    @wraps(method, WRAPPER_ASSIGNMENTS)
    def wrapped_method(*args, **kwargs) -> Any:
        self = args[0]
        self.logger.debug("called {} of instance {}".format(method.__qualname__, self.instance_name))
        return method(*args, **kwargs)
    return wrapped_method


def is_private_attribute(attr_name: str) -> bool:
    """returns if the attribute name is to be considered private or not
    Args:
        attr_name (str): name of the attribute

    Returns:
        bool: return True when attribute does not start with '_' or (dunder '__'
            are therefore included)
    """
    if attr_name.startswith('_'):
        return True
    return False

    
def remote_method(access_type = (HTTP, PROXY) , 
            URL_path : str = USE_OBJECT_NAME, http_method : str = POST, 
            state : Optional[Union[str, Enum]] = None) -> Callable:
    """Use this function to decorate your methods to be accessible remotely.  
    
    Args:
        access_type (str, tuple): whether the object should be accessible to HTTP methods, ProxyClient, both or neither 
            (enter None).
        URL_path (str, optional): The path of URL under which the object is accessible. defaults to name of the object.
        http_method (str, optional)  : HTTP method (GET, POST, PUT etc.). defaults to POST.
        state (Union[str, Tuple[str]], optional): state under which the object can executed or written. When not provided,
            its accessible or can be executed under any state.

    Returns:
        Callable: returns the callable object as it is or wrapped within loggers
    """
    
    def inner(obj):
        original = obj
        if isinstance(obj, classmethod):
            obj = obj.__func__
        if callable(obj):
            if hasattr(obj, 'scada_info') and not isinstance(obj.scada_info, ScadaInfoValidator): 
                raise NameError(
wrap_text(
                    """
                    variable name 'scada_info' reserved for scadapy library. 
                    Please do not assign this variable to any other object except scadapy.server.scada_info.ScadaInfoValidator.
                    """
                    )
                )             
            else:
                obj.scada_info = ScadaInfoValidator() 
            obj.scada_info.access_type = access_type
            obj_name = obj.__qualname__.split('.')
            if len(obj_name) > 1: # i.e. its a bound method, used by RemoteObject
                if URL_path == USE_OBJECT_NAME: 
                    obj.scada_info.URL_path = f'/{obj_name[1]}'
                else:
                    assert URL_path.startswith('/'), f"URL_path should start with '/', please add '/' before '{URL_path}'"
                    obj.scada_info.URL_path = URL_path
                obj.scada_info.obj_name = obj_name[1] 
            elif len(obj_name) == 1 and isinstance(obj, FunctionType):  # normal unbound function - used by HTTPServer instance
                if URL_path is USE_OBJECT_NAME:
                    obj.scada_info.URL_path = '/{}'.format(obj_name[0])
                else:
                    assert URL_path.startswith('/'), f"URL_path should start with '/', please add '/' before '{URL_path}'"
                    obj.scada_info.URL_path = URL_path
                obj.scada_info.obj_name = obj_name[0] 
            else:
                raise RuntimeError(f"Undealt option for decorating {obj} or decorators wrongly used")
            if http_method is not UNSPECIFIED:  
                if isinstance(http_method, str):
                    obj.scada_info.http_method = (http_method,)
                else:
                    obj.scada_info.http_method = http_method 
            if state is not None:
                if isinstance(state, (Enum, str)):
                    obj.scada_info.state = (state,)
                else:
                    obj.scada_info.state = state     
            if 'request' in getfullargspec(obj).kwonlyargs:
                obj.scada_info.http_request_as_argument = True
            obj.scada_info.iscallable = True
            obj.scada_info.iscoroutine = iscoroutinefunction(obj)
            return original
        else:
            raise TypeError(
                wrap_text(
                f"""
                target for get()/post()/remote_method() or http method decorator is not a function/method.
                Given type {type(obj)}
                """
                )
            )
    return inner 



def get(URL_path = USE_OBJECT_NAME):
    """
    use it on RemoteObject subclass methods to be available with GET HTTP request. 
    method is also by default accessible to proxy clients. 
    """
    return remote_method(access_type=(HTTP, PROXY), URL_path=URL_path, http_method=GET)
    
def post(URL_path = USE_OBJECT_NAME):
    """
    use it on RemoteObject subclass methods to be available with POST HTTP request. 
    method is also by default accessible to proxy clients. 
    """
    return remote_method(access_type=(HTTP, PROXY), URL_path=URL_path, http_method=POST)

def put(URL_path = USE_OBJECT_NAME):
    """
    use it on RemoteObject subclass methods to be available with PUT HTTP request. 
    method is also by default accessible to proxy clients. 
    """
    return remote_method(access_type=(HTTP, PROXY), URL_path=URL_path, http_method=PUT)
    
def delete(URL_path = USE_OBJECT_NAME):
    """
    use it on RemoteObject subclass methods to be available with DELETE HTTP request. 
    method is also by default accessible to proxy clients. 
    """
    return remote_method(access_type=(HTTP, PROXY), URL_path=URL_path, http_method=DELETE)


@dataclass 
class FuncInfo:
    module : str
    name : str
    qualname : str
    doc : str
    kwdefaults : Any
    defaults : Any 
    scadapy : ScadaInfoData

    def json(self):
        return asdict(self)
    
    
# @dataclass
# class DB_registration_info:
#     script : str 
#     instance_name : str
#     http_server   : str = field(default = '')
#     args          : Tuple[Any] = field(default = tuple())
#     kwargs        : Dict[str, Any] = field(default = dict()) 
#     eventloop     : str = field(default = '')
#     level         : int = field(default = 1)
#     level_type    : str = field(default = '')


def parse_request_args(*args, method : str):   
    arg_len = len(args)
    if arg_len > 2 or arg_len == 0: 
        raise ValueError(
            """
            method {}() accepts only two argument, URL and/or a function/method.
            Given length of arguments : {}.
            """.format(method.lower(), arg_len)
        )
    if isinstance(args[0], FunctionType):
        target = args[0] 
    elif len(args) > 1 and isinstance(args[1], FunctionType):
        target = args[1]
    else:
        target = None         
    if isinstance(args[0], str):
        URL = args[0]
    elif len(args) > 1 and isinstance(args[1], str):
        URL = args[1]
    else:   
        URL = USE_OBJECT_NAME 
    return target, URL
    



__all__ = ['get', 'put', 'post', 'delete', 'remote_method']


