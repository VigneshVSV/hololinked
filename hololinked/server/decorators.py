import functools
import typing
from enum import Enum
from types import FunctionType
from inspect import iscoroutinefunction, getfullargspec

from .data_classes import RemoteResourceInfoValidator
from .constants import (USE_OBJECT_NAME, UNSPECIFIED, HTTP_METHODS)
from .utils import wrap_text



WRAPPER_ASSIGNMENTS = functools.WRAPPER_ASSIGNMENTS + ('__kwdefaults__', '__defaults__', )

def wrap_method(method : FunctionType):
    """wraps a methods with useful operations before and after calling a method.
    Old : use case not decided.

    Args:
        method (FunctionType): function or callable

    Returns:
        method : returns a wrapped callable, preserving information regarding signature 
            as much as possible
    """
   
    @functools.wraps(method, WRAPPER_ASSIGNMENTS)
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

    
def remote_method(URL_path : str = USE_OBJECT_NAME, http_method : str = HTTP_METHODS.POST, 
            state : typing.Optional[typing.Union[str, Enum]] = None) -> typing.Callable:
    """Use this function to decorate your methods to be accessible remotely.  
    
    Parameters
    ----------
    URL_path: str, optional 
        The path of URL under which the object is accessible. defaults to name of the object.
    http_method: str, optional
        HTTP method (GET, POST, PUT etc.). defaults to POST.
    state: str | Tuple[str], optional 
        state under which the object can executed or written. When not provided,
        its accessible or can be executed under any state.

    Returns
    -------
    callable: Callable
        returns the callable object as it is or wrapped within loggers
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


def remote_parameter(default: typing.Any = None, *, doc : typing.Optional[str] = None, 
        constant : bool = False, readonly : bool = False, allow_None : bool = False, 
        URL_path : str = USE_OBJECT_NAME, remote : bool = True, 
        http_method : typing.Tuple[typing.Optional[str], typing.Optional[str]] = (HTTP_METHODS.GET, HTTP_METHODS.PUT), 
        state : typing.Optional[typing.Union[typing.List, typing.Tuple, str, Enum]] = None,
        db_persist : bool = False, db_init : bool = False, db_commit : bool = False, 
        class_member : bool = False, fget : typing.Optional[typing.Callable] = None, 
        fset : typing.Optional[typing.Callable] = None, fdel : typing.Optional[typing.Callable] = None, 
        deepcopy_default : bool = False, per_instance_descriptor : bool = False, 
        precedence : typing.Optional[float] = None, metadata : typing.Optional[typing.Dict] = None,
        parameter_type : typing.Optional["RemoteParameter"] = None, **kwargs
    ) -> "RemoteParameter":
    """
    use like python ``property`` without declaring a remote parameter explicity.       
    """
    if type is not None and not isinstance(type, RemoteParameter):
        raise TypeError(f"type argument must be a RemoteParameter if supplied, given type {parameter_type(type)}")
    else:
        parameter_type = RemoteParameter 
        # will raise import error when specified in argument

    return parameter_type(default=default, constant=constant, readonly=readonly,
            allow_None=allow_None, URL_path=URL_path, remote=remote, http_method=http_method,
            state=state, db_persist=db_persist, db_init=db_init, db_commit=db_commit,
            class_member=class_member, fget=fget, fset=fset, fdel=fdel, 
            deepcopy_default=deepcopy_default, per_instance_descriptor=per_instance_descriptor,
            precedence=precedence, metadata=metadata, **kwargs)



from .remote_parameter import RemoteParameter

__all__ = ['remote_method', 'remote_parameter']


