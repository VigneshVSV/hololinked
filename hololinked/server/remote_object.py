import asyncio
import logging 
import inspect
import os
import threading
import time
import typing
import datetime
import zmq
from collections import deque
from enum import EnumMeta, Enum, StrEnum


from ..param.parameterized import Parameterized, ParameterizedMetaclass 
from .constants import (CallableType, LOGLEVEL, ZMQ_PROTOCOLS, HTTP_METHODS, ResourceOperations, ResourceTypes)
from .database import RemoteObjectDB, RemoteObjectInformation
from .stubs import ReactApp
from .serializers import *
from .exceptions import BreakInnerLoop
from .decorators import remote_method
from .http_methods import get, post
from .data_classes import (GUIResources, RemoteResource, HTTPResource, RPCResource, RemoteResourceInfoValidator,
                        ServerSentEvent)
from .utils import get_default_logger
from .api_platform_utils import *
from .remote_parameter import RemoteParameter, RemoteClassParameters
from .remote_parameters import (Integer, String, ClassSelector, TypedDict, Boolean, 
                                Selector, TypedKeyMappingsConstrainedDict )
from .zmq_message_brokers import RPCServer, ServerTypes, AsyncPollingZMQServer, EventPublisher
from .events import Event



class StateMachine:
    """
    A container class for state machine related logic, this is intended to be used by the 
    RemoteObject and its descendents.  
    	
    Parameters
    ----------
    initial_state: str 
        initial state of machine 
    states: Enum
        enumeration of states 
    on_enter: Dict[str, Callable | RemoteParameter] 
        callbacks to be invoked when a certain state is entered. It is to be specified 
        as a dictionary with the states being the keys
    on_exit: Dict[str, Callable | RemoteParameter]
        callbacks to be invoked when a certain state is exited. 
        It is to be specified as a dictionary with the states being the keys
    **machine:
        state name: List[Callable, RemoteParamater]
            directly pass the state name as an argument along with the methods/parameters which are allowed to execute 
            in that state
            
    Attributes
    ----------
    exists: bool
        internally computed, True if states and initial_states are valid 
    """
    initial_state = ClassSelector(default=None, allow_None=True, constant=True, class_=(Enum, str))
    exists = Boolean(default=False)
    states = ClassSelector(default=None, allow_None=True, constant=True, class_=(EnumMeta, tuple, list)) 
    on_enter = TypedDict(default=None, allow_None=True, key_type=str)
    on_exit = TypedDict(default=None, allow_None=True, key_type=str) 
    machine = TypedDict(default=None, allow_None=True, key_type=str, item_type=(list, tuple))

    def __init__(self, states : typing.Union[EnumMeta, typing.List[str], typing.Tuple[str]], *, 
            initial_state : typing.Union[StrEnum, str], 
            on_enter : typing.Dict[str, typing.Union[typing.List[typing.Callable], typing.Callable]] = {}, 
            on_exit  : typing.Dict[str, typing.Union[typing.List[typing.Callable], typing.Callable]] = {}, 
            push_state_change_event : bool = False,
            **machine : typing.Iterable[typing.Union[typing.Callable, RemoteParameter]]) -> None:
        self.on_enter = on_enter
        self.on_exit  = on_exit
        # None cannot be passed in, but constant is necessary. 
        self.states   = states
        self.initial_state = initial_state
        self.machine = machine
        self.push_state_change_event = push_state_change_event
        if push_state_change_event:
            pass
            # self.state_change_event = Event('state-change') 

    def _prepare(self, owner : 'RemoteObject') -> None:
        if self.states is None and self.initial_state is None:    
            self.exists = False 
            self._state = None
            return
        elif self.initial_state not in self.states: # type: ignore
            raise AttributeError("specified initial state {} not in Enum of states {}".format(self.initial_state, 
                                                                                              self.states))

        self._state = self.initial_state
        self.owner = owner
        owner_parameters = owner.parameters.descriptors.values()
        owner_methods = [obj[0] for obj in inspect.getmembers(owner, inspect.ismethod)]
        
        if isinstance(self.states, list):
            self.states = tuple(self.states)
        if hasattr(self, 'state_change_event'):
            self.state_change_event.publisher = owner.event_publisher

        # first validate machine
        for state, objects in self.machine.items():
            if state in self:
                for resource in objects:
                    if hasattr(resource, '_remote_info'):
                        assert isinstance(resource._remote_info, RemoteResourceInfoValidator)
                        if resource._remote_info.iscallable and resource._remote_info.obj_name not in owner_methods: # type: ignore
                            raise AttributeError("Given object {} for state machine does not belong to class {}".format(
                                                                                                resource, owner))
                        if resource._remote_info.isparameter and resource not in owner_parameters: # type: ignore
                            raise AttributeError("Given object {} - {} for state machine does not belong to class {}".format(
                                                                                                resource.name, resource, owner))
                        if resource._remote_info.state is None: # type: ignore
                            resource._remote_info.state = self._machine_compliant_state(state) # type: ignore
                        else: 
                            resource._remote_info.state = resource._remote_info.state + (self._machine_compliant_state(state), ) # type: ignore
                    else: 
                        raise AttributeError(f"Object {resource} not made remotely accessible,",
                                    " Use state machine with remote parameters and remote methods only")
            else:
                raise AttributeError("Given state {} not in states Enum {}".format(state, self.states.__members__))
            
        # then the callbacks 
        for state, objects in self.on_enter.items():
            if isinstance(objects, list):
                self.on_enter[state] = tuple(objects) # type: ignore
            elif not isinstance(objects, (list, tuple)):
                self.on_enter[state] = (objects, ) # type: ignore
            for obj in self.on_enter[state]: # type: ignore
                if not isinstance(obj, CallableType):
                    raise TypeError(f"on_enter accept only methods. Given type {type(obj)}.")

        for state, objects in self.on_exit.items():
            if isinstance(objects, list):
                self.on_exit[state] = tuple(objects) # type: ignore
            elif not isinstance(objects, (list, tuple)):
                self.on_exit[state] = (objects, ) # type: ignore
            for obj in self.on_exit[state]: # type: ignore
                if not isinstance(obj, CallableType):
                    raise TypeError(f"on_enter accept only methods. Given type {type(obj)}.")     
        self.exists = True
        
    def __contains__(self, state : typing.Union[str, StrEnum]):
        if isinstance(self.states, EnumMeta) and state not in self.states.__members__ and state not in self.states: # type: ignore
            return False 
        elif isinstance(self.states, tuple) and state not in self.states:
            return False 
        return True
        # TODO It might be better to return True's instead of False's and return False at the last, may take care of edge-cases better 
        
    def _machine_compliant_state(self, state) -> typing.Union[StrEnum, str]:
        if isinstance(self.states, EnumMeta):
            return self.states.__members__[state] # type: ignore
        return state 
    
    def get_state(self) -> typing.Union[str, StrEnum, None]:
        """
        return the current state. one can also access the property `current state`.
        
        Returns
        -------
        current state: str
        """
        return self._state
        
    def set_state(self, value, push_event : bool = True, skip_callbacks : bool = False) -> None:
        """ set state of state machine. Also triggers state change callbacks
        if any. One can also set using '=' operator of `current_state` property.
        """
        if value in self.states:
            previous_state = self._state
            self._state = value
            if push_event and self.push_state_change_event:
                self.state_change_event.push({self.owner.instance_name : value})
            if isinstance(previous_state, Enum):
                previous_state = previous_state.name
            if previous_state in self.on_exit:
                for func in self.on_exit[previous_state]: # type: ignore
                    func(self.owner)
            if isinstance(value, Enum):
                value = value.name  
            if value in self.on_enter:
                for func in self.on_enter[value]: # type: ignore
                    func(self.owner)
        else:   
            raise ValueError("given state '{}' not in set of allowed states : {}.".format(value, self.states))
                
    current_state = property(get_state, set_state, None, 
        doc = """read and write current state of the state machine""")

    def query(self, info : typing.Union[str, typing.List[str]] ) -> typing.Any:
        raise NotImplementedError("arbitrary quering of {} not possible".format(self.__class__.__name__))
    



class RemoteObjectMeta(ParameterizedMetaclass):
    """
    Metaclass for remote object, implements a ``__post_init__()`` call & ``RemoteClassParameters`` instantiation for 
    ``RemoteObject``. During instantiation of ``RemoteObject``, first the message brokers are created (``_prepare_message_brokers()``),
    then ``_prepare_logger()``, then ``_prepare_DB()`` & ``_prepare_state_machine()`` in the ``__init__()``. In the 
    ``__post_init__()``, the resources of the RemoteObject are segregated and database operations like writing parameter 
    values are carried out. Between ``__post_init__()`` and ``__init__()``, package user's ``__init__()`` will run where user can run 
    custom logic after preparation of message brokers and database engine and before using database operations. 
    """
    
    @classmethod
    def __prepare__(cls, name, bases):
        return TypedKeyMappingsConstrainedDict({},
            type_mapping = dict(
                state_machine = (StateMachine, type(None)),
                instance_name = String, 
                log_level = Selector,
                logger = ClassSelector,
                logfile = String,
                db_config_file = String,
                object_info = RemoteParameter, # it should not be set by the user
            ),
            allow_unspecified_keys = True
        )

    def __new__(cls, __name, __bases, __dict : TypedKeyMappingsConstrainedDict):
        return super().__new__(cls, __name, __bases, __dict._inner)
    
    def __call__(mcls, *args, **kwargs):
        instance = super().__call__(*args, **kwargs)
        instance.__post_init__()
        return instance
    
    def _create_param_container(mcs, mcs_members : dict) -> None:
        """
        creates ``RemoteClassParameters`` instead of ``param``'s own ``Parameters``
        as the default container for descriptors. See code of ``param``.
        """
        mcs._param_container = RemoteClassParameters(mcs, mcs_members)

    @property
    def parameters(mcs) -> RemoteClassParameters:
        """
        returns ``RemoteClassParameters`` instance instead of ``param``'s own 
        ``Parameters`` instance. See code of ``param``.
        """
        return mcs._param_container
    


class RemoteSubobject(Parameterized, metaclass=RemoteObjectMeta):

    # local parameters
    instance_name = String(default=None, regex=r'[A-Za-z]+[A-Za-z_0-9\-\/]*', constant=True, remote=False,
                        doc="""Unique string identifier of the instance. This value is used for many operations,
                        for example - creating zmq socket address, tables in databases, and to identify the instance 
                        in the HTTP Server & webdashboard clients - 
                        (http(s)://{domain and sub domain}/{instance name}). Instance names must be unique
                        in your entire system.""") # type: str
    expose = Boolean(default=True, doc="""set to False to use the object locally to avoid alloting network resources 
                        of your computer for this object""")
    
    # remote paramerters
    httpserver_resources = RemoteParameter(readonly=True, URL_path='/resources/http-server', 
                        doc="object's resources exposed to HTTP client (through ``hololinked.server.HTTPServer``)", 
                        fget=lambda self: self._httpserver_resources ) # type: typing.Dict[str, HTTPResource]
    rpc_resources = RemoteParameter(readonly=True, URL_path='/resources/object-proxy', 
                        doc="object's resources exposed to RPC client, similar to HTTP resources but differs in details.", 
                        fget=lambda self: self._rpc_resources) # type: typing.Dict[str, typing.Any]
    gui_resources = RemoteParameter(readonly=True, URL_path='/resources/gui', 
                        doc="""object's data read by hololinked-portal GUI client, similar to http_resources but differs 
                        in details.""",
                        fget=lambda self: GUIResources().build(self)) # type: typing.Dict[str, typing.Any]
    thing_description = RemoteParameter(readonly=True, URL_path='/resources/wot', 
                            doc="thing description schema of W3 Web of Things https://www.w3.org/TR/wot-thing-description11/",
                        )
    events = RemoteParameter(readonly=True, URL_path='/events', 
                        doc="returns a dictionary with two fields containing event name and event information") # type: typing.Dict[str, typing.Any]
    object_info = RemoteParameter(doc="contains information about this object like the class name, script location etc.",
                        readonly=True, URL_path='/info', fget = lambda self: self._object_info) # type: RemoteObjectDB.RemoteObjectInfo
    GUI = ClassSelector(class_=ReactApp, default=None, allow_None=True, 
                        doc="GUI specified here will become visible at GUI tab of hololinked-portal dashboard tool") # type: typing.Optional[ReactApp]
    

    def __new__(cls, *args, **kwargs):
        # defines some internal fixed attributes
        obj = super().__new__(cls)
        # objects created by us that require no validation but cannot be modified are called _internal_fixed_attributes
        obj._internal_fixed_attributes = ['_internal_fixed_attributes', 'instance_resources', '_owner']        
        # objects given by user which we need to validate (mostly descriptors)
        return obj


    def __init__(self, instance_name : str, **params):
        super().__init__(instance_name=instance_name, **params)
        # separates out instance name as a mandatory parameter so that the user forced to supply it.


    def __post_init__(self):
        self._internal_fixed_attributes : typing.List[str]
        self._owner : typing.Optional[RemoteObject]


    def __setattr__(self, __name: str, __value: typing.Any) -> None:
        if  __name == '_internal_fixed_attributes' or __name in self._internal_fixed_attributes: 
            # order of 'or' operation for above 'if' matters
            if not hasattr(self, __name):
                # allow setting of fixed attributes once
                super().__setattr__(__name, __value)
            else:
                raise AttributeError(
                    f"Attempted to set {__name} more than once. Cannot assign a value to this variable after creation.")
        else:
            super().__setattr__(__name, __value)


    def _prepare_resources(self):
        """
        this function analyses the members of the class which have 'scadapy' variable declared
        and extracts information 
        """
        # The following dict is to be given to the HTTP server
        httpserver_resources = dict() # type: typing.Dict[str, HTTPResource]
        # The following dict will be given to the object proxy client
        rpc_resources = dict() # type: typing.Dict[str, RPCResource]
        # The following dict will be used by the event loop
        instance_resources = dict() # type: typing.Dict[str, RemoteResource] 
        # create URL prefix
        self._full_URL_path_prefix = f'{self._owner._full_URL_path_prefix}/{self.instance_name}' if self._owner is not None else f'/{self.instance_name}'
        
        # First add methods and callables
        for name, resource in inspect.getmembers(self, inspect.ismethod):
            if hasattr(resource, '_remote_info'):
                if not isinstance(resource._remote_info, RemoteResourceInfoValidator):
                    raise TypeError("instance member {} has unknown sub-member '_remote_info' of type {}.".format(
                                resource, type(resource._remote_info))) 
                remote_info = resource._remote_info
                # methods are already bound
                fullpath = "{}{}".format(self._full_URL_path_prefix, remote_info.URL_path) 
                assert remote_info.iscallable, ("remote info from inspect.ismethod is not a callable",
                                    "logic error - visit https://github.com/VigneshVSV/hololinked/issues to report")
                if len(remote_info.http_method) > 1:
                    raise ValueError(f"methods support only one HTTP method at the moment. Given number of methods : {len(remote_info.http_method)}.")
                httpserver_resources[fullpath] = HTTPResource(
                                            what=ResourceTypes.CALLABLE,
                                            instance_name=self._owner.instance_name if self._owner is not None else self.instance_name,
                                            fullpath=fullpath,
                                            request_as_argument=remote_info.request_as_argument,
                                            argument_schema=remote_info.argument_schema,
                                            **{ remote_info.http_method[0] : fullpath },
                                        )
                rpc_resources[fullpath] = RPCResource(
                                                what=ResourceTypes.CALLABLE,
                                                instance_name=self._owner.instance_name if self._owner is not None else self.instance_name,
                                                instruction=fullpath,                                                                                                                                                                                        
                                                name=getattr(resource, '__name__'),
                                                qualname=getattr(resource, '__qualname__'), 
                                                doc=getattr(resource, '__doc__'),
                                                top_owner=self._owner is None,
                                                argument_schema=remote_info.argument_schema,
                                            )
                instance_resources[fullpath] = remote_info.to_dataclass(obj=resource, bound_obj=self) 
        # Other remote objects 
        for name, resource in inspect.getmembers(self, lambda o : isinstance(o, RemoteSubobject)):
            if name == '_owner':
                continue
            assert isinstance(resource, RemoteSubobject), ("remote object children query from inspect.ismethod is not a RemoteObject",
                                    "logic error - visit https://github.com/VigneshVSV/hololinked/issues to report")
            # above assertion is only a typing convenience
            resource._owner = self
            resource._prepare_resources()                 
            httpserver_resources.update(resource.httpserver_resources)
            rpc_resources.update(resource.rpc_resources)
            instance_resources.update(resource.instance_resources)
        # Events
        for name, resource in inspect.getmembers(self, lambda o : isinstance(o, Event)):
            assert isinstance(resource, Event), ("remote object event query from inspect.ismethod is not an Event",
                                    "logic error - visit https://github.com/VigneshVSV/hololinked/issues to report")
            # above assertion is only a typing convenience
            resource._owner = self
            resource._unique_identifier = bytes(f"{self._full_URL_path_prefix}{resource.URL_path}", encoding='utf-8')
            resource.publisher = self._event_publisher
            httpserver_resources['{}{}'.format(
                        self._full_URL_path_prefix, resource.URL_path)] = ServerSentEvent(
                                                            # event URL_path has '/' prefix
                                                            what=ResourceTypes.EVENT,
                                                            name=resource.name,
                                                            unique_identifier=f"{self._full_URL_path_prefix}{resource.URL_path}",
                                                            socket_address=self._event_publisher.socket_address
                                                        )
        # Parameters
        for parameter in self.parameters.descriptors.values():
            if hasattr(parameter, '_remote_info') and parameter._remote_info is not None: 
                if not isinstance(parameter._remote_info, RemoteResourceInfoValidator):  # type: ignore
                    raise TypeError("instance member {} has unknown sub-member 'scada_info' of type {}.".format(
                                parameter, type(parameter._remote_info))) # type: ignore
                    # above condition is just a gaurd in case user does some unpredictable patching activities
                remote_info = parameter._remote_info
                fullpath = "{}{}".format(self._full_URL_path_prefix, remote_info.URL_path) 
                assert remote_info.isparameter, ("remote object parameter query from inspect.ismethod is not a Parameter",
                                    "logic error - visit https://github.com/VigneshVSV/hololinked/issues to report")
                read_http_method, write_http_method = remote_info.http_method
                    
                httpserver_resources[fullpath] = HTTPResource(
                                                    what=ResourceTypes.PARAMETER, 
                                                    instance_name=self._owner.instance_name if self._owner is not None else self.instance_name,
                                                    fullpath=fullpath,
                                                    request_as_argument=False,
                                                    **{ 
                                                        read_http_method : f"{fullpath}/{ResourceOperations.PARAMETER_READ}",
                                                        write_http_method : f"{fullpath}/{ResourceOperations.PARAMETER_WRITE}"
                                                    },
                                                    argument_schema=remote_info.argument_schema,
                                                )
                rpc_resources[fullpath] = RPCResource(
                                what=ResourceTypes.PARAMETER, 
                                instance_name=self._owner.instance_name if self._owner is not None else self.instance_name, 
                                instruction=fullpath, 
                                doc=parameter.__doc__, 
                                name=remote_info.obj_name,
                                qualname=self.__class__.__name__ + '.' + remote_info.obj_name,
                                # qualname is not correct probably, does not respect inheritance
                                top_owner=self._owner is None,
                                argument_schema=remote_info.argument_schema,
                            ) 
                dclass = remote_info.to_dataclass(obj=parameter, bound_obj=self) 
                instance_resources[f"{fullpath}/{ResourceOperations.PARAMETER_READ}"] = dclass
                instance_resources[f"{fullpath}/{ResourceOperations.PARAMETER_WRITE}"] = dclass  
        # The above for-loops can be used only once, the division is only for readability
        # following are in _internal_fixed_attributes - allowed to set only once
        self._rpc_resources = rpc_resources       
        self._httpserver_resources = httpserver_resources 
        self.instance_resources = instance_resources    

    
    def _create_object_info(self, script_path : typing.Optional[str] = None):
        if not script_path:
            try:
                script_path = os.path.dirname(os.path.abspath(inspect.getfile(self.__class__)))
            except:
                script_path = ''
        return RemoteObjectInformation(
                    instance_name  = self.instance_name, 
                    class_name     = self.__class__.__name__,
                    script         = script_path,
                    http_server    = "USER_MANAGED", 
                    kwargs         = "USER_MANAGED",  
                    eventloop_instance_name = "USER_MANAGED", 
                    level          = "USER_MANAGED", 
                    level_type     = "USER_MANAGED"
                )  
    

    @property
    def _event_publisher(self) -> EventPublisher:
        try:
            return self.event_publisher 
        except AttributeError:
            top_owner = self._owner 
            while True:
                if isinstance(top_owner, RemoteObject):
                    self.event_publisher = top_owner.event_publisher
                    return self.event_publisher
                elif isinstance(top_owner, RemoteSubobject):
                    top_owner = top_owner._owner
                else:
                    raise RuntimeError("Error while finding owner of RemoteSubobject.", 
                        "RemoteSubobject must be composed only within RemoteObject or RemoteSubobject, ",  
                        "otherwise there can be problems.")
            

    @events.getter
    def _get_events(self) -> typing.Dict[str, typing.Any]:
        return {
            event._unique_identifier.decode() : dict(
                name = event.name,
                instruction = event._unique_identifier.decode(),
                owner = event.owner.__class__.__name__,
                owner_instance_name =  event.owner.instance_name,
                address = self.event_publisher.socket_address
            ) for event in self.event_publisher.events
        }
    
    @remote_method(http_method=HTTP_METHODS.GET, URL_path='/resources/postman-collection')
    def postman_collection(self, domain_prefix : str) -> postman_collection:
        return postman_collection.build(instance=self, domain_prefix=domain_prefix)
    
    @thing_description.getter 
    def get_thing_description(self):
        from ..wot import ThingDescription
        return ThingDescription().build(self)
    
       

class RemoteObject(RemoteSubobject): 
    """
    Expose your python classes for HTTP methods & RPC clients by subclassing from here. 
    """
    __server_type__ = ServerTypes.REMOTE_OBJECT 
    state_machine : StateMachine

    # local parameters
    logger = ClassSelector(class_=logging.Logger, default=None, allow_None=True, remote=False, 
                        doc = """Logger object to print log messages, should be instance of ``logging.Logger()``. Default 
                        logger is created if none supplied.""") # type: logging.Logger
    rpc_serializer = ClassSelector(class_=(BaseSerializer, str), 
                                allow_None=True, default='msgpack', remote=False,
                                doc="""Serializer used for exchanging messages with RPC clients. Subclass to implement
                                    your own serialization requirements.""") # type: BaseSerializer
    json_serializer = ClassSelector(class_=(JSONSerializer, str), default=None, allow_None=True, remote=False,
                                doc = """Serializer used for exchanging messages with a HTTP server,
                                subclass JSONSerializer to implement your own serialization requirements.""") # type: JSONSerializer
 
    
    def __init__(self, *, instance_name : str, logger : typing.Optional[logging.Logger] = None, 
                rpc_serializer : typing.Optional[BaseSerializer] = 'json', 
                json_serializer : typing.Optional[JSONSerializer] = 'json',
                server_protocols : typing.Optional[typing.Union[typing.List[ZMQ_PROTOCOLS], 
                        typing.Tuple[ZMQ_PROTOCOLS], ZMQ_PROTOCOLS]] = [ZMQ_PROTOCOLS.IPC, ZMQ_PROTOCOLS.TCP, ZMQ_PROTOCOLS.INPROC], 
                **params) -> None:
        
        super().__init__(instance_name=instance_name, logger=logger, rpc_serializer=rpc_serializer, 
                        json_serializer=json_serializer, **params)

        self._prepare_logger(log_file=params.get('log_file', None), log_level=params.get('log_level', None), 
                            remote_access=params.get('logger_remote_access', True))
        if self.expose: 
            self._prepare_message_brokers(protocols=server_protocols, 
                                tcp_socket_address=params.get('socket_address', None))
        self._prepare_DB(params.get('use_default_db', False), params.get('db_config_file', None))   
        self._prepare_state_machine()  

    
    def __post_init__(self):
        # Never create events before _prepare_instance(), no checks in place
        super().__post_init__()
        self._owner = None
        if self.expose:
            self._prepare_resources()
        self.write_parameters_from_DB()
        self.logger.info("initialialised RemoteObject class {} with instance name {}".format(
            self.__class__.__name__, self.instance_name))  
        

    def _prepare_logger(self, log_level : int, log_file : str, remote_access : bool = True):
        if self.logger is None:
            self.logger = get_default_logger(self.instance_name, 
                            logging.INFO if not log_level else log_level, 
                            None if not log_file else log_file)
        if remote_access:
            if not any(isinstance(handler, RemoteAccessHandler) 
                                                    for handler in self.logger.handlers):
                self._remote_access_loghandler = RemoteAccessHandler(instance_name='logger', maxlen=500, emit_interval=1)
                self.logger.addHandler(self._remote_access_loghandler)
            else:
                for handler in self.logger.handlers:
                    if isinstance(handler, RemoteAccessHandler):
                        self._remote_access_loghandler = handler        

        
    def _prepare_message_brokers(self, protocols : typing.Optional[typing.Union[typing.Iterable[ZMQ_PROTOCOLS], ZMQ_PROTOCOLS]], 
                                tcp_socket_address : typing.Optional[str] = None):
        context = zmq.asyncio.Context()
        self.message_broker = AsyncPollingZMQServer(
                                instance_name=f'{self.instance_name}/inner',  # hardcoded be very careful
                                server_type=self.__server_type__.value,
                                context=context,
                                protocol=ZMQ_PROTOCOLS.INPROC, 
                                json_serializer=self.json_serializer,
                                rpc_serializer=self.rpc_serializer,
                                log_level=self.logger.level
                            )
        self.json_serializer = self.message_broker.json_serializer
        self.rpc_serializer = self.message_broker.rpc_serializer
        self._rpc_server = RPCServer(instance_name=self.instance_name, server_type=self.__server_type__.value, 
                                    context=context, protocols=protocols, json_serializer=self.json_serializer, 
                                    rpc_serializer=self.rpc_serializer, socket_address=tcp_socket_address,
                                    log_level=self.logger.level) 
        self.event_publisher = EventPublisher(identity=self.instance_name, rpc_serializer=self.rpc_serializer,
                                              json_serializer=self.json_serializer)
     

    def _prepare_DB(self, default_db : bool = False, config_file : str = None):
        if not default_db and not config_file: 
            self._object_info = self._create_object_info()
            return 
        # 1. create engine 
        self.db_engine = RemoteObjectDB(instance=self, config_file=None if default_db else config_file, 
                                    serializer=self.rpc_serializer) # type: RemoteObjectDB 
        # 2. create an object metadata to be used by different types of clients
        object_info = self.db_engine.fetch_own_info()
        if object_info is None:
            object_info = self._create_object_info()
        self._object_info = object_info
        # 3. enter parameters to DB if not already present 
        if self.object_info.class_name != self.__class__.__name__:
            raise ValueError("Fetched instance name and class name from database not matching with the ", 
                " current RemoteObject class/subclass. You might be reusing an instance name of another subclass ", 
                "and did not remove the old data from database. Please clean the database using database tools to ", 
                "start fresh.")


    def _prepare_state_machine(self):
        if hasattr(self, 'state_machine'):
            self.state_machine._prepare(self)
            self.logger.debug("setup state machine")


    def write_parameters_from_DB(self):
        if not hasattr(self, 'db_engine'):
            return
        missing_parameters = self.db_engine.create_missing_parameters(self.__class__.parameters.db_init_objects,
                                                                    get_missing_parameters=True)
        # 4. read db_init and db_persist objects
        for db_param in self.db_engine.get_all_parameters():
            try:
                if db_param.name not in missing_parameters:
                    setattr(self, db_param.name, db_param.value) # type: ignore
            except Exception as E:
                self.logger.error(f"could not set attribute {db_param.name} due to error {E}")


    @remote_method(URL_path='/parameters', http_method=HTTP_METHODS.GET)
    def _parameters(self, **kwargs) -> typing.Dict[str, typing.Any]:
        if len(kwargs) == 0:
            return self.parameters.descriptors.keys()
        data = {}
        if 'filter_by' in kwargs:
            names = kwargs['filter_by']
            for requested_parameter in names.split(','):
                data[requested_parameter] = self.parameters[requested_parameter].__get__(self, type(self))
        elif len(kwargs.keys()) != 0:
            for rename, requested_parameter in kwargs.items():
                data[rename] = self.parameters[requested_parameter].__get__(self, type(self))              
        else:
            for parameter in self.parameters.descriptors.keys():
                data[parameter] = self.parameters[parameter].__get__(self, type(self))
        return data 

    @get('/state')    
    def state(self):
        if hasattr(self, 'state_machine'):
            return self.state_machine.current_state
        else:
            return None
    
    # Example of get and post decorator 
    @remote_method(URL_path='/exit', http_method=HTTP_METHODS.POST)                                                                                                                                          
    def exit(self) -> None:
        """
        Exit the object without killing the eventloop that runs this object. If RemoteObject was 
        started using the run() method, the eventloop is also killed. 
        """
        raise BreakInnerLoop

 
    def run(self, expose_eventloop : bool = False):
        """
        quick-start ``RemoteObject`` server by creating a default eventloop. 
        """
        from .eventloop import EventLoop
        e = EventLoop(instance_name=f'{self.instance_name}/eventloop', remote_objects=[self], log_level=self.logger.level,
                    rpc_serializer=self.rpc_serializer, json_serializer=self.json_serializer, expose=expose_eventloop)
        if not expose_eventloop:
            e.remote_objects = [self] # remote event loop from list of remote objects
        e.run()
       


class ListHandler(logging.Handler):

    def __init__(self, log_list : typing.Optional[typing.List] = None):
        super().__init__()
        self.log_list : typing.List[typing.Dict] = [] if not log_list else log_list
    
    def emit(self, record : logging.LogRecord):
        log_entry = self.format(record)
        self.log_list.insert(0, {
            'level' : record.levelname,
            'timestamp' : datetime.datetime.fromtimestamp(record.created).strftime("%Y-%m-%dT%H:%M:%S.%f"),
            'message' : record.msg
        })


class RemoteAccessHandler(logging.Handler, RemoteSubobject):

    def __init__(self, maxlen : int = 100, emit_interval : float = 1.0, **kwargs) -> None:
        logging.Handler.__init__(self)
        RemoteSubobject.__init__(self, **kwargs)
        # self._last_time = datetime.datetime.now()
        if not isinstance(emit_interval, (float, int)) or emit_interval < 1.0:
            raise TypeError("Specify log emit interval as number greater than 1.0") 
        else:
            self.emit_interval = emit_interval # datetime.timedelta(seconds=1.0) if not emit_interval else datetime.timedelta(seconds=emit_interval)
        self.event = Event('log-events')
        self.diff_logs = []
        self.maxlen = maxlen
        self._push_events = False
        self._events_thread = None
    
    def get_maxlen(self):
        return self._maxlen 
    
    def set_maxlen(self, value):
        self._maxlen = value
        self._debug_logs = deque(maxlen=value)
        self._info_logs = deque(maxlen=value)
        self._warn_logs = deque(maxlen=value)
        self._error_logs = deque(maxlen=value)
        self._critical_logs = deque(maxlen=value)
        self._execution_logs = deque(maxlen=value)

    maxlen = Integer(default=100, bounds=(1, None), crop_to_bounds=True, URL_path='/maxlen',
            fget=get_maxlen, fset=set_maxlen )


    @remote_method(http_method=HTTP_METHODS.POST, URL_path='/events/start')
    def push_events(self, type : str = 'threaded', interval : float = 1):
        self.emit_interval = interval # datetime.timedelta(seconds=interval)
        self._push_events = True 
        if type == 'asyncio':
            asyncio.get_event_loop().call_soon(lambda : asyncio.create_task(self.async_push_diff_logs()))
        elif self._events_thread is not None:
            self._events_thread = threading.Thread(target=self.push_diff_logs)
            self._events_thread.start()

    @remote_method(http_method=HTTP_METHODS.POST, URL_path='/events/stop')
    def stop_events(self):
        self._push_events = False 
        if self._events_thread: # No need to cancel asyncio event separately 
            self._events_thread.join()
            self._owner.logger.debug(f"joined logg event source with thread-id {self._events_thread.ident}")
            self._events_thread = None
    
    def emit(self, record : logging.LogRecord):
        log_entry = self.format(record)
        info = {
            'level' : record.levelname,
            'timestamp' : datetime.datetime.fromtimestamp(record.created).strftime("%Y-%m-%dT%H:%M:%S.%f"),
            'message' : record.msg
        }
        if record.levelno < logging.INFO:
            self._debug_logs.appendleft(info)
        elif record.levelno >= logging.INFO and record.levelno < logging.WARN:
            self._info_logs.appendleft(info)
        elif record.levelno >= logging.WARN and record.levelno < logging.ERROR:
            self._warn_logs.appendleft(info)
        elif record.levelno >= logging.ERROR and record.levelno < logging.CRITICAL:
            self._error_logs.appendleft(info)
        elif record.levelno >= logging.CRITICAL:
            self._critical_logs.appendleft(info)
        self._execution_logs.appendleft(info)

        if self._push_events: 
            self.diff_logs.insert(0, info)

    def push_diff_logs(self):
        while self._push_events:
            # if datetime.datetime.now() - self._last_time > self.emit_interval and len(self.diff_logs) > 0: 
            time.sleep(self.emit_interval)
            self.event.push(self.diff_logs) 
            self.diff_logs.clear()
        # give time to collect final logs with certainty
        self._owner.logger.info(f"ending log event source with thread-id {threading.get_ident()}")
        time.sleep(self.emit_interval)
        if self.diff_logs:
            self.event.push(self.diff_logs)
            self.diff_logs.clear()
            # self._last_time = datetime.datetime.now()

    async def async_push_diff_logs(self):
        while self._push_events:
            # if datetime.datetime.now() - self._last_time > self.emit_interval and len(self.diff_logs) > 0: 
            await asyncio.sleep(self.emit_interval)
            self.event.push(self.diff_logs) 
            self.diff_logs.clear()
        # give time to collect final logs with certainty
        await asyncio.sleep(self.emit_interval)
        if self.diff_logs:
            self.event.push(self.diff_logs)
            self.diff_logs.clear()
            # self._last_time = datetime.datetime.now()
     
    debug_logs = RemoteParameter(readonly=True, URL_path='/logs/debug', fget=lambda self: self._debug_logs,
                            doc="logs at logging.DEBUG level")
    
    warn_logs = RemoteParameter(readonly=True, URL_path='/logs/warn', fget=lambda self: self._warn_logs,
                            doc="logs at logging.WARN level")
    
    info_logs = RemoteParameter(readonly=True, URL_path='/logs/info', fget=lambda self: self._info_logs,
                            doc="logs at logging.INFO level")
       
    error_logs = RemoteParameter(readonly=True, URL_path='/logs/error', fget=lambda self: self._error_logs,
                            doc="logs at logging.ERROR level")
 
    critical_logs = RemoteParameter(readonly=True, URL_path='/logs/critical', fget=lambda self: self._critical_logs,
                            doc="logs at logging.CRITICAL level")
  
    execution_logs = RemoteParameter(readonly=True, URL_path='/logs/execution', fget=lambda self: self._execution_logs,
                            doc="logs at all levels accumulated in order of collection/execution")
  


__all__ = ['RemoteObject', 'StateMachine', 'ListHandler', 'RemoteAccessHandler']
