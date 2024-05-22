import typing 
import threading 

from ..param import Parameterized
from .zmq_message_brokers import EventPublisher
from .data_classes import ServerSentEvent



class Event:
    """
    Asynchronously push arbitrary messages to clients. 

    Parameters
    ----------
    name: str
        name of the event. specified name may contain dashes and can be used on client side to subscribe to this event.
    URL_path: str
        url path of the event if a HTTP server is used. only GET HTTP methods are supported. 
    """

    def __init__(self, name : str, URL_path : typing.Optional[str] = None) -> None:
        self.name = name 
        # self.name_bytes = bytes(name, encoding = 'utf-8')
        self.URL_path = URL_path or '/' + name
        self._unique_identifier = None # type: typing.Optional[str]
        self._owner = None  # type: typing.Optional[Parameterized]
        self._remote_info = None # type: typing.Optional[ServerSentEvent]
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

    def push(self, data : typing.Any = None, *, serialize : bool = True, **kwargs) -> None:
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
        self.publisher.publish(self._unique_identifier, data, rpc_clients=kwargs.get('rpc_clients', True), 
                                    http_clients=kwargs.get('http_clients', True), serialize=serialize)


class CriticalEvent(Event):
    """
    Push events to client and get acknowledgement for that
    """

    def __init__(self, name : str, URL_path : typing.Optional[str] = None) -> None:
        super().__init__(name, URL_path)
        self._synchronize_event = threading.Event()

    def receive_acknowledgement(self, timeout : typing.Union[float, int, None]) -> bool:
        """
        Receive acknowlegement for event receive. When the timeout argument is present and not None, 
        it should be a floating point number specifying a timeout for the operation in seconds (or fractions thereof).
        """
        return self._synchronize_event.wait(timeout=timeout)

    def _set_acknowledgement(self):
        """
        Method to be called by RPC server when an acknowledgement is received. Not for user to be set.
        """
        self._synchronize_event.set()


__all__ = [
    Event.__name__,
]