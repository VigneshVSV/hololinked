import logging
import typing
from types import FunctionType, MethodType
from enum import StrEnum, IntEnum, Enum


# types
JSONSerializable = typing.Union[typing.Dict[str, typing.Any], list, str, int, float, None]
JSON = typing.Dict[str, JSONSerializable]
CallableType = (FunctionType, MethodType)

# decorator constants 
# naming
USE_OBJECT_NAME : str = "USE_OBJECT_NAME"
# state machine
ANY_STATE   : str = "ANY_STATE"
UNSPECIFIED : str = "UNSPECIFIED"
# types


class ResourceTypes(StrEnum):
    "Exposed resource types"

    FUNC  = "FUNC"
    ATTRIBUTE = "ATTRIBUTE"
    PARAMETER = "PARAMETER"
    IMAGE_STREAM = "IMAGE_STREAM"
    CALLABLE = "CALLABLE"
    FILE = "FILE"
    EVENT = "EVENT"


class ResourceOperations(StrEnum):
    "some common eventloop side operations"

    PARAMETER_READ = "read"
    PARAMETER_WRITE = "write"
    PARAMETER_DELETE = "delete"


class CommonRPC(StrEnum):
    "some common RPC instructions"

    RPC_RESOURCES = '/resources/object-proxy/read'
    HTTP_RESOURCES = '/resources/http-server/read'

    @classmethod
    def rpc_resource_read(cls, instance_name : str) -> str:
        return f"/{instance_name}{cls.RPC_RESOURCES}"

    @classmethod
    def http_resource_read(cls, instance_name : str) -> str:
        return f"/{instance_name}{cls.HTTP_RESOURCES}"


class REGEX(StrEnum):
    "common regexes"

    states = '[A-Za-z_]+[A-Za-z_ 0-9]*'
    url = r'[\-a-zA-Z0-9@:%._\/\+~#=]{1,256}' 


class HTTP_METHODS(StrEnum):
    "currently supported HTTP request methods"
    
    GET = 'GET'
    POST = 'POST'
    PUT = 'PUT'
    DELETE = 'DELETE'
    PATCH = 'PATCH'
    OPTIONS = 'OPTIONS'

http_methods = [member for member in HTTP_METHODS._member_map_]

# Logging 
class LOGLEVEL(IntEnum):
    "``logging.Logger`` log levels"

    DEBUG    = logging.DEBUG
    INFO     = logging.INFO
    CRITICAL = logging.CRITICAL
    ERROR    = logging.ERROR
    WARN     = logging.WARN
    FATAL    = logging.FATAL

# ZMQ
class ZMQ_PROTOCOLS(StrEnum):
    "supported ZMQ protocols"

    TCP = "TCP"
    IPC = "IPC"
    INPROC = "INPROC"


class ClientMessage(IntEnum):
    """
    ZNQ client sent message indexing for accessing message indices with names 
    instead of numbers
    """
    ADDRESS = 0
    CLIENT_TYPE = 2
    MESSAGE_TYPE = 3
    MESSAGE_ID = 4
    TIMEOUT = 5
    INSTRUCTION = 6
    ARGUMENTS = 7
    EXECUTION_CONTEXT = 8


class ServerMessage(IntEnum):
    """
    ZMQ server sent message indexing for accessing message indices with names 
    instead of numbers
    """
    ADDRESS = 0
    SERVER_TYPE = 2
    MESSAGE_TYPE = 3
    MESSAGE_ID = 4
    DATA = 5


class ServerMessageData(StrEnum):
    RETURN_VALUE = "returnValue"


class ServerTypes(Enum):
    "type of ZMQ servers"

    UNKNOWN_TYPE = b'UNKNOWN' 
    EVENTLOOP = b'EVENTLOOP'  
    REMOTE_OBJECT = b'REMOTE_OBJECT'
    POOL = b'POOL'
       
       
class ClientTypes(Enum):
    "type of ZMQ clients"

    HTTP_SERVER = b'HTTP_SERVER'
    PROXY = b'PROXY'
    TUNNELER = b'TUNNELER' # message passer from inproc client to inrproc server within RPC


class HTTPServerTypes(StrEnum):
    "types of HTTP server"

    SYSTEM_HOST = 'SYSTEM_HOST'
    REMOTE_OBJECT_SERVER = 'REMOTE_OBJECT_SERVER'


class Serializers(StrEnum):
    """
    allowed serializers

    - PICKLE : pickle
    - JSON : msgspec.json
    - SERPENT : serpent
    - MSGPACK : msgspec.msgpack
    """
    PICKLE = 'pickle'
    JSON = 'json'
    SERPENT = 'serpent'
    MSGPACK = 'msgpack'


