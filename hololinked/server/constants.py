import logging
import functools 
import typing
from enum import Enum
from types import MethodType, FunctionType


# decorator constants 
# naming
USE_OBJECT_NAME : str = "USE_OBJECT_NAME"
# state machine
ANY_STATE   : str = "ANY_STATE"
UNSPECIFIED : str = "UNSPECIFIED"
# types
FUNC  = "FUNC"
ATTRIBUTE = "ATTRIBUTE"
PARAMETER = "PARAMETER"
IMAGE_STREAM = "IMAGE_STREAM"
CALLABLE = "CALLABLE"
FILE = "FILE"
# operation
READ  = "read"
WRITE = "write"

# logic
WRAPPER_ASSIGNMENTS = functools.WRAPPER_ASSIGNMENTS + ('__kwdefaults__', '__defaults__', )
SERIALIZABLE_WRAPPER_ASSIGNMENTS = ('__module__', '__name__', '__qualname__', '__doc__', '__kwdefaults__', '__defaults__', )
# regex logic
states_regex : str = '[A-Za-z_]+[A-Za-z_ 0-9]*'
url_regex : str = r'[\-a-zA-Z0-9@:%._\/\+~#=]{1,256}' 


# HTTP request methods
GET : str = 'GET'
POST : str = 'POST'
PUT : str = 'PUT'
DELETE : str = 'DELETE'
PATCH : str = 'PATCH'
OPTIONS : str = 'OPTIONS'
http_methods = [GET, PUT, POST, DELETE, PATCH]
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

# ZMQ
ZMQ_PROTOCOLS = Enum('ZMQ_PROTOCOLS', 'TCP IPC INPROC')