import typing 
import zmq 
import logging 
from uuid import uuid4 

from ..param import Parameterized
from .zmq_message_brokers import BaseZMQServer, EventPublisher
from .constants import ServerTypes
from .utils import get_default_logger


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
            self._publisher.register(self)
        else:
            raise AttributeError("cannot reassign publisher attribute of event {}".format(self.name)) 

    def push(self, data : typing.Any = None, *, rpc_clients : bool = True, http_clients : bool = True, 
                serialize : bool = True) -> None:
        """
        publish the event. 

        Parameters
        ----------
        data: Any
            payload of the event
        serialize: bool, default True
            serialize the payload before pushing, set to False when supplying raw bytes
        rpc_clients: bool, default True
            pushes event to RPC clients
        http_clients: bool, default True
            pushed event to HTTP clients
        """
        self.publisher.publish(self._unique_identifier, data, rpc_clients=rpc_clients, http_clients=http_clients,
                                serialize=serialize)


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

