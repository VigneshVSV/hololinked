import logging
import functools 
import typing
from enum import Enum, StrEnum, IntEnum
from types import MethodType, FunctionType


# decorator constants 
# naming
USE_OBJECT_NAME : str = "USE_OBJECT_NAME"
# state machine
ANY_STATE   : str = "ANY_STATE"
UNSPECIFIED : str = "UNSPECIFIED"
# types
class ResourceType(StrEnum):
    FUNC  = "FUNC"
    ATTRIBUTE = "ATTRIBUTE"
    PARAMETER = "PARAMETER"
    IMAGE_STREAM = "IMAGE_STREAM"
    CALLABLE = "CALLABLE"
    FILE = "FILE"
    EVENT = "EVENT"


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
SERIALIZABLE_WRAPPER_ASSIGNMENTS = ('__name__', '__qualname__', '__doc__' )
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
class ZMQ_PROTOCOLS(Enum):
    TCP = "TCP"
    IPC = "IPC"
    INPROC = "INPROC"

class Instructions(StrEnum):
    RPC_RESOURCES = '/resources/object-proxy/read'
    HTTP_RESOURCES = '/resources/http-server/read'

class ClientMessage(IntEnum):
    ADDRESS = 0
    CLIENT_TYPE = 2
    MESSAGE_TYPE = 3
    MESSAGE_ID = 4
    TIMEOUT = 5
    INSTRUCTION = 6
    ARGUMENTS = 7
    EXECUTION_CONTEXT = 8

class ServerMessage(IntEnum):
    ADDRESS = 0
    SERVER_TYPE = 2
    MESSAGE_TYPE = 3
    MESSAGE_ID = 4
    DATA = 5

class ServerMessageData(StrEnum):
    RETURN_VALUE = "returnValue"

class ServerTypes(Enum):
    UNKNOWN_TYPE = b'UNKNOWN_TYPE'
    EVENTLOOP = b'EVENTLOOP'
    REMOTE_OBJECT = b'REMOTE_OBJECT'
    POOL = b'POOL'
       

