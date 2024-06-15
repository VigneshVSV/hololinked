import typing 
import threading
import jsonschema

from ..param.parameterized import Parameterized, ParameterizedMetaclass
from .constants import JSON 
from .config import global_config
from .zmq_message_brokers import EventPublisher
from .dataklasses import ServerSentEvent
from .security_definitions import BaseSecurityDefinition


class Event:
    """
    Asynchronously push arbitrary messages to clients. Apart from default events created by the package (like state
    change event, observable properties etc.), events are supposed to be created at class level or at ``__init__`` 
    as a instance attribute, otherwise their publishing socket is unbound and will lead to ``AttributeError``.  

    Parameters
    ----------
    name: str
        name of the event, specified name may contain dashes and can be used on client side to subscribe to this event.
    URL_path: str
        URL path of the event if a HTTP server is used. only GET HTTP methods are supported. 
    doc: str
        docstring for the event
    schema: JSON
        schema of the event, if the event is JSON complaint. HTTP clients can validate the data with this schema. There
        is no validation on server side.
    security: Any
        security necessary to access this event.
    """
    __slots__ = ['name', '_internal_name', '_remote_info', 'doc', 'schema', 'URL_path', 'security', 'label']


    def __init__(self, name : str, URL_path : typing.Optional[str] = None, doc : typing.Optional[str] = None, 
                schema : typing.Optional[JSON] = None, security : typing.Optional[BaseSecurityDefinition] = None,
                label : typing.Optional[str] = None) -> None:
        self.name = name 
        self.doc = doc 
        if global_config.validate_schemas and schema:
            jsonschema.Draft7Validator.check_schema(schema)
        self.schema = schema
        self.URL_path = URL_path
        self.security = security
        self.label = label
        self._internal_name = f"{self.name}-dispatcher"
        self._remote_info = ServerSentEvent(name=name)
      
    
    @typing.overload
    def __get__(self, obj : ParameterizedMetaclass, objtype : typing.Optional[type] = None) -> "EventDispatcher":
        ...

    def __get__(self, obj : ParameterizedMetaclass, objtype : typing.Optional[type] = None) -> "EventDispatcher":
        try:
            return obj.__dict__[self._internal_name]
        except KeyError:
            raise AttributeError("Event object not yet initialized, please dont access now." +
                                " Access after Thing is running")
        
    def __set__(self, obj : Parameterized, value : typing.Any) -> None:
        if isinstance(value, EventDispatcher):
            if not obj.__dict__.get(self._internal_name, None):
                obj.__dict__[self._internal_name] = value 
            else:
                raise AttributeError(f"Event object already assigned for {self.name}. Cannot reassign.") 
                # may be allowing to reassign is not a bad idea 
        else:
            raise TypeError(f"Supply EventDispatcher object to event {self.name}, not type {type(value)}.")


class EventDispatcher:
    """
    The actual worker which pushes the event. The separation is necessary between ``Event`` and 
    ``EventDispatcher`` to allow class level definitions of the ``Event`` 
    """
    def __init__(self, name : str, unique_identifier : str, owner_inst : Parameterized) -> None:
        self._name = name
        self._unique_identifier = bytes(unique_identifier, encoding='utf-8') 
        self._owner_inst = owner_inst
        self._publisher = None

    @property
    def publisher(self) -> "EventPublisher": 
        """
        Event publishing PUB socket owning object.
        """
        return self._publisher
    
    @publisher.setter
    def publisher(self, value : "EventPublisher") -> None:
        if not self._publisher:
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
        **kwargs:
            zmq_clients: bool, default True
                pushes event to RPC clients, irrelevant if ``Thing`` uses only one type of serializer (refer to 
                difference between zmq_serializer and http_serializer).
            http_clients: bool, default True
                pushed event to HTTP clients, irrelevant if ``Thing`` uses only one type of serializer (refer to 
                difference between zmq_serializer and http_serializer).
        """
        self.publisher.publish(self._unique_identifier, data, zmq_clients=kwargs.get('zmq_clients', True), 
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