import zmq
import logging
import typing
from enum import StrEnum, IntEnum, Enum


# types
JSONSerializable = typing.Union[typing.Dict[str, typing.Any], list, str, int, float, None]
JSON = typing.Dict[str, JSONSerializable]

# decorator constants 
# naming
USE_OBJECT_NAME : str = "USE_OBJECT_NAME"
# state machine
ANY_STATE   : str = "ANY_STATE"
UNSPECIFIED : str = "UNSPECIFIED"
# types


class ResourceTypes(StrEnum):
    """
    Exposed resource types. This repository does not rely on python's internal getattr, setattr and type checking, 
    to expose RPC operations, but rather segrates resource types and operates on them in predefined ways. This is to allow
    addition or removal of resource types which may demand more integration with HTTP.  
    """
    PROPERTY = "PROPERTY"
    ACTION = "ACTION"
    EVENT = "EVENT"
    IMAGE_STREAM = "IMAGE_STREAM"
    FILE = "FILE"


class CommonRPC(StrEnum):
    """some common RPC and their associated instructions for quick access by lower level code"""

    ZMQ_RESOURCES = '/resources/zmq-object-proxy'
    HTTP_RESOURCES = '/resources/http-server'
    OBJECT_INFO = '/object-info'
    PING = '/ping'

    @classmethod
    def zmq_resource_read(cls, instance_name : str) -> str:
        return f"/{instance_name}{cls.ZMQ_RESOURCES}/read"

    @classmethod
    def http_resource_read(cls, instance_name : str) -> str:
        return f"/{instance_name}{cls.HTTP_RESOURCES}/read"
    
    @classmethod
    def object_info_read(cls, instance_name : str) -> str: 
        return f"/{instance_name}{cls.OBJECT_INFO}/read"
    
    @classmethod
    def object_info_write(cls, instance_name : str) -> str: 
        return f"/{instance_name}{cls.OBJECT_INFO}/write"


class REGEX(StrEnum):
    """common regexes"""

    states = '[A-Za-z_]+[A-Za-z_ 0-9]*'
    url = r'[\-a-zA-Z0-9@:%._\/\+~#=]{1,256}' 


class HTTP_METHODS(StrEnum):
    """currently supported HTTP request methods"""

    GET = 'GET'
    POST = 'POST'
    PUT = 'PUT'
    DELETE = 'DELETE'
    PATCH = 'PATCH'
    # OPTIONS = 'OPTIONS'

http_methods = [member for member in HTTP_METHODS._member_map_]


# Logging 
class LOGLEVEL(IntEnum):
    """``logging.Logger`` log levels"""
    DEBUG    = logging.DEBUG
    INFO     = logging.INFO
    CRITICAL = logging.CRITICAL
    ERROR    = logging.ERROR
    WARN     = logging.WARN
    FATAL    = logging.FATAL


# ZMQ
class ZMQ_PROTOCOLS(StrEnum):
    """
    supported ZMQ transport protocols - TCP, IPC, INPROC

    TCP - needs socket address additional specified like tcp://0.0.0.0:{port}
    IPC - within python, multiprocess applications, can be autogenerated
    INPROC - within python, multithreaded applications, can be autogenerated
    """
    TCP = "TCP"
    IPC = "IPC"
    INPROC = "INPROC"


class ClientMessage(IntEnum):
    """
    ZMQ client sent message indexing for accessing message indices with names 
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
    ENCODED_DATA = 6


class ServerTypes(Enum):
    "type of ZMQ servers"

    UNKNOWN_TYPE = b'UNKNOWN' 
    EVENTLOOP = b'EVENTLOOP'  
    THING = b'THING'
    POOL = b'POOL'
       
       
class ClientTypes(Enum):
    "type of ZMQ clients"

    HTTP_SERVER = b'HTTP_SERVER'
    PROXY = b'PROXY'
    TUNNELER = b'TUNNELER' # message passer from inproc client to inrproc server within RPC


class HTTPServerTypes(StrEnum):
    "types of HTTP server"

    SYSTEM_HOST = 'SYSTEM_HOST'
    THING_SERVER = 'THING_SERVER'


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


class ZMQSocketType(IntEnum):
    PAIR = zmq.PAIR
    PUB = zmq.PUB
    SUB = zmq.SUB
    REQ = zmq.REQ
    REP = zmq.REP
    DEALER = zmq.DEALER
    ROUTER = zmq.ROUTER
    PULL = zmq.PULL
    PUSH = zmq.PUSH
    XPUB = zmq.XPUB
    XSUB = zmq.XSUB
    STREAM = zmq.STREAM
    # Add more socket types as needed


ZMQ_EVENT_MAP = {}
for name in dir(zmq):
    if name.startswith('EVENT_'):
        value = getattr(zmq, name)
        ZMQ_EVENT_MAP[value] = name




__all__ = [
    Serializers.__name__, 
    HTTP_METHODS.__name__,
    ZMQ_PROTOCOLS.__name__
]