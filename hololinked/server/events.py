import typing 
import zmq 
import logging 
from uuid import uuid4 

from ..param import Parameterized
from .zmq_message_brokers import BaseZMQServer, BaseZMQClient
from .constants import ServerTypes
from .utils import create_default_logger


class Event:
    """
    Asynchronously push arbitrary messages to clients. 
    """

    def __init__(self, name : str, URL_path : typing.Optional[str] = None) -> None:
        self.name = name 
        # self.name_bytes = bytes(name, encoding = 'utf-8')
        self.URL_path = URL_path or '/' + name
        self._unique_identifier = None # type: typing.Optional[str]
        self._owner = None  # type: typing.Optional[Parameterized]
        # above two attributes are not really optional, they are set later. 

    @property
    def owner(self):
        return self._owner        
        
    @property
    def publisher(self) -> "EventPublisher": 
        return self._publisher
    
    @publisher.setter
    def publisher(self, value : "EventPublisher") -> None:
        if not hasattr(self, '_publisher'):
            self._publisher = value
            self._publisher.register_event(self)
        else:
            raise AttributeError("cannot reassign publisher attribute of event {}".format(self.name)) 

    def push(self, data : typing.Any = None, serialize : bool = True):
        self.publisher.publish_event(self._unique_identifier, data, serialize)


class CriticalEvent(Event):

    def __init__(self, name : str, message_broker : BaseZMQServer, timeout : float = 3, 
                incoming_data_schema : typing.Any = None, URL_path : typing.Optional[str] = None) -> None:
        super().__init__(name, URL_path)
        self.message_broker = message_broker
        self.timeout = timeout
        self.incoming_data_schema = incoming_data_schema

    def push(self, data : typing.Any = None):
        super().push(data)
        self.message_broker.receive_acknowledgement()



class EventPublisher(BaseZMQServer):

    def __init__(self,  identity : str, context : typing.Union[zmq.Context, None] = None, **serializer) -> None:
        super().__init__(server_type=ServerTypes.UNKNOWN_TYPE, **serializer)
        self.context = context or zmq.Context()
        self.identity = identity
        self.socket = self.context.socket(zmq.PUB)
        for i in range(1000, 65535):
            try:
                self.socket_address = "tcp://127.0.0.1:{}".format(i)
                self.socket.bind(self.socket_address)
            except zmq.error.ZMQError as ex:
                if ex.strerror.startswith('Address in use'):
                    pass 
                else:
                    print("Following error while atttempting to bind to socket address : {}".format(self.socket_address))
                    raise ex from None
            else:
                self.logger = self.get_logger(identity, "PUB", "TCP", logging.DEBUG)
                self.logger.info("created event publishing socket at {}".format(self.socket_address))
                break
        self.events = set() # type: typing.Set[Event] 
        self.event_ids = set() # type: typing.Set[bytes]

    def register_event(self, event : Event) -> None:
        # unique_str_bytes = bytes(unique_str, encoding = 'utf-8') 
        if event._unique_identifier in self.events:
            raise AttributeError(
                "event {} already found in list of events, please use another name.".format(event.name),
                "Also, Remotesubobject and RemoteObject cannot share event names."
            )
        self.event_ids.add(event._unique_identifier)
        self.events.add(event) 
        self.logger.info("registered event '{}' serving at PUB socket with address : {}".format(event.name, self.socket_address))
               
    def publish_event(self, unique_str : bytes, data : typing.Any, serialize : bool = True) -> None: 
        if unique_str in self.event_ids:
            if serialize:
                self.socket.send_multipart([unique_str, self.json_serializer.dumps(data)])
            else:
                self.socket.send_multipart([unique_str, data])
        else:
            raise AttributeError("event name {} not yet registered with socket {}".format(unique_str, self.socket_address))
        
    def exit(self):
        if not hasattr(self, 'logger'):
            self.logger = create_default_logger('{}|{}'.format(self.__class__.__name__, uuid4()))
        try:
            self.socket.close(0)
            self.logger.info("terminated event publishing socket with address '{}'".format(self.socket_address))
        except Exception as E:
            self.logger.warn("could not properly terminate context or attempted to terminate an already terminated context at address '{}'. Exception message : {}".format(
                self.socket_address, str(E)))
        try:
            self.context.term()
            self.logger.info("terminated context of event publishing socket with address '{}'".format(self.socket_address)) 
        except Exception as E: 
            self.logger.warn("could not properly terminate socket or attempted to terminate an already terminated socket of event publishing socket at address '{}'. Exception message : {}".format(
                self.socket_address, str(E)))
      

class EventConsumer(BaseZMQClient):

    def __init__(self, event_URL : str, socket_address : str, identity : str, client_type = b'HTTP_SERVER', **kwargs) -> None:
        super().__init__(server_address=b'unknown', server_instance_name='unkown', client_type=client_type, **kwargs)
        # Prepare our context and publisher
        self.event_URL = bytes(event_URL, encoding='utf-8')
        self.socket_address = socket_address
        self.identity = identity
        self.context = zmq.asyncio.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect(socket_address)
        self.socket.setsockopt(zmq.SUBSCRIBE, self.event_URL)
        self.logger = self.get_logger(identity, self.socket_address, logging.DEBUG, self.__class__.__name__)
        self.logger.info("connected event consuming socket to address {}".format(self.socket_address))
      
    async def receive_event(self, deserialize = False):
        _, contents = await self.socket.recv_multipart()
        if not deserialize: 
            return contents
        return self.json_serializer.loads(contents)
    
    def exit(self):
        if not hasattr(self, 'logger'):
            self.logger = create_default_logger('{}|{}'.format(self.__class__.__name__, uuid4()))
        try:
            self.socket.close(0)
            self.logger.info("terminated event consuming socket with address '{}'".format(self.socket_address))
        except Exception as E:
            self.logger.warn("could not properly terminate context or attempted to terminate an already terminated context at address '{}'. Exception message : {}".format(
                self.socket_address, str(E)))
        try:
            self.context.term()
            self.logger.info("terminated context of event consuming socket with address '{}'".format(self.socket_address)) 
        except Exception as E: 
            self.logger.warn("could not properly terminate socket or attempted to terminate an already terminated socket of event consuming socket at address '{}'. Exception message : {}".format(
                self.socket_address, str(E)))
            
