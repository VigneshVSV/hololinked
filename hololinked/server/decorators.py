import typing
from types import FunctionType
from inspect import iscoroutinefunction, getfullargspec
from enum import Enum
from functools import wraps
from dataclasses import dataclass, asdict, field, fields


from .data_classes import RemoteResourceInfoValidator, RemoteResource
from .constants import (USE_OBJECT_NAME, UNSPECIFIED, GET, POST, PUT, DELETE, PATCH, WRAPPER_ASSIGNMENTS)
from .utils import wrap_text
from .path_converter import compile_path



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
    def wrapped_method(*args, **kwargs) -> typing.Any:
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

    
def remote_method(URL_path : str = USE_OBJECT_NAME, http_method : str = POST, 
            state : typing.Optional[typing.Union[str, Enum]] = None) -> typing.Callable:
    """Use this function to decorate your methods to be accessible remotely.  
    
    Args:
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
            if hasattr(obj, '_remote_info') and not isinstance(obj._remote_info, RemoteResourceInfoValidator): 
                raise NameError(
                    wrap_text(
                    """
                    variable name '_remote_info' reserved for scadapy library. 
                    Please do not assign this variable to any other object except scadapy.server.data_classes.RemoteResourceInfoValidator.
                    """
                    )
                )             
            else:
                obj._remote_info = RemoteResourceInfoValidator() 
            obj_name = obj.__qualname__.split('.')
            if len(obj_name) > 1: # i.e. its a bound method, used by RemoteObject
                if URL_path == USE_OBJECT_NAME: 
                    obj._remote_info.URL_path = f'/{obj_name[1]}'
                else:
                    assert URL_path.startswith('/'), f"URL_path should start with '/', please add '/' before '{URL_path}'"
                    obj._remote_info.URL_path = URL_path
                obj._remote_info.obj_name = obj_name[1] 
            elif len(obj_name) == 1 and isinstance(obj, FunctionType):  # normal unbound function - used by HTTPServer instance
                if URL_path is USE_OBJECT_NAME:
                    obj._remote_info.URL_path = '/{}'.format(obj_name[0])
                else:
                    assert URL_path.startswith('/'), f"URL_path should start with '/', please add '/' before '{URL_path}'"
                    obj._remote_info.URL_path = URL_path
                obj._remote_info.obj_name = obj_name[0] 
            else:
                raise RuntimeError(f"Undealt option for decorating {obj} or decorators wrongly used")
            if http_method is not UNSPECIFIED:  
                if isinstance(http_method, str):
                    obj._remote_info.http_method = (http_method,)
                else:
                    obj._remote_info.http_method = http_method 
            if state is not None:
                if isinstance(state, (Enum, str)):
                    obj._remote_info.state = (state,)
                else:
                    obj._remote_info.state = state     
            if 'request' in getfullargspec(obj).kwonlyargs:
                obj._remote_info.http_request_as_argument = True
            obj._remote_info.iscallable = True
            obj._remote_info.iscoroutine = iscoroutinefunction(obj)
            return original
        else:
            raise TypeError(
                "target for get()/post()/remote_method() or http method decorator is not a function/method.",
                f"Given type {type(obj)}"
            )
            
    return inner 


def remote_parameter(**kwargs):
    from .remote_parameter import RemoteParameter
    return RemoteParameter(*kwargs)


@dataclass 
class FuncInfo:
    module : str
    name : str
    qualname : str
    doc : str
    kwdefaults : typing.Any
    defaults : typing.Any 
    scadapy : RemoteResource

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


# def parse_request_args(*args, method : str):  
#     """
#     This method is useful when linters figure out conditional returns on decorators
#     """ 
#     arg_len = len(args)
#     if arg_len > 2 or arg_len == 0: 
#         raise ValueError(
#             """
#             method {}() accepts only two argument, URL and/or a function/method.
#             Given length of arguments : {}.
#             """.format(method.lower(), arg_len)
#         )
#     if isinstance(args[0], FunctionType):
#         target = args[0] 
#     elif len(args) > 1 and isinstance(args[1], FunctionType):
#         target = args[1]
#     else:
#         target = None         
#     if isinstance(args[0], str):
#         URL = args[0]
#     elif len(args) > 1 and isinstance(args[1], str):
#         URL = args[1]
#     else:   
#         URL = USE_OBJECT_NAME 
#     return target, URL
    



__all__ = ['remote_method', 'remote_parameter']


