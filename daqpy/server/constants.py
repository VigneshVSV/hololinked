import logging
import functools 
import typing
from enum import Enum
from types import MethodType, FunctionType


# decorator constants 
ANY_STATE   : str = "ANY_STATE"
UNSPECIFIED : str = "UNSPECIFIED"
USE_OBJECT_NAME : str = "USE_OBJECT_NAME"
HTTP  = "HTTP"
PROXY = "PROXY"
HTTP_AND_PROXY = "HTTP_AND_PROXY"
FUNC  = "FUNC"
ATTRIBUTE = "ATTRIBUTE"
IMAGE_STREAM = "IMAGE_STREAM"
CALLABLE = "CALLABLE"
FILE = "FILE"
VARIABLE  = "VARIABLE"
READ  = "read"
WRITE = "write"
WRAPPER_ASSIGNMENTS = functools.WRAPPER_ASSIGNMENTS + ('__kwdefaults__', '__defaults__', )
SERIALIZABLE_WRAPPER_ASSIGNMENTS = ('__module__', '__name__', '__qualname__', '__doc__', '__kwdefaults__', '__defaults__', )
states_regex : str = '[A-Za-z_]+[A-Za-z_ 0-9]*'
url_regex : str    = r'[\-a-zA-Z0-9@:%._\/\+~#=]{1,256}' 
instance_name_regex = r'[A-Za-z]+[A-Za-z_0-9\-\/]*'

# Following list and function taken from Pyro5 
private_dunder_methods = frozenset([
    "__init__", "__init_subclass__", "__class__", "__module__", "__weakref__",
    "__call__", "__new__", "__del__", "__repr__",
    "__str__", "__format__", "__nonzero__", "__bool__", "__coerce__",
    "__cmp__", "__eq__", "__ne__", "__hash__", "__ge__", "__gt__", "__le__", "__lt__",
    "__dir__", "__enter__", "__exit__", "__copy__", "__deepcopy__", "__sizeof__",
    "__getattr__", "__setattr__", "__hasattr__", "__getattribute__", "__delattr__",
    "__instancecheck__", "__subclasscheck__", "__getinitargs__", "__getnewargs__",
    "__getstate__", "__setstate__", "__reduce__", "__reduce_ex__", "__subclasshook__"
])

# HTTP related
POST : str = 'POST'
GET  : str = 'GET'
PUT  : str = 'PUT'
OPTIONS : str = 'OPTIONS'
DELETE : str  = 'DELETE'
http_methods = [GET, PUT, POST, OPTIONS, DELETE]

# HTTP Handler related 
EVENT : str = 'event'
INSTRUCTION : str = 'INSTRUCTION'

# Logging 
log_levels = dict(
    DEBUG    = logging.DEBUG,
    INFO     = logging.INFO,
    CRITICAL = logging.CRITICAL,
    ERROR    = logging.ERROR,
    WARN     = logging.WARN,
    FATAL    = logging.FATAL
)

# types
CallableType = (FunctionType, MethodType)
JSONSerializable = typing.Union[typing.Dict[str, typing.Any], list, str, int, float, None]

ZMQ_PROTOCOLS = Enum('ZMQ_PROTOCOLS', 'TCP IPC')