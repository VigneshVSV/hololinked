import logging 
import inspect
import os
import typing
import warnings
import zmq
from enum import EnumMeta, Enum, StrEnum


from ..param.parameterized import Parameterized, ParameterizedMetaclass 
from .constants import (CallableType, LOGLEVEL, ZMQ_PROTOCOLS, HTTP_METHODS)
from .database import RemoteObjectDB, RemoteObjectInformation
from .stubs import ReactApp
from .serializers import _get_serializer_from_user_given_options, BaseSerializer, JSONSerializer
from .exceptions import BreakInnerLoop
from .decorators import remote_method
from .data_classes import (GUIResources,  HTTPResource, RPCResource, RemoteResourceInfoValidator,
                        get_organised_resources)
from .utils import get_default_logger, getattr_without_descriptor_read

from .remote_parameter import RemoteParameter, RemoteClassParameters
from .remote_parameters import (String, ClassSelector, TypedDict, Boolean, 
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
    initial_state = ClassSelector(default=None, allow_None=True, constant=True, class_=(Enum, str), 
                        doc="initial state of the machine") # type: typing.Union[Enum, str]
    states = ClassSelector(default=None, allow_None=True, constant=True, class_=(EnumMeta, tuple, list),
                        doc="list/enum of allowed states") # type: typing.Union[EnumMeta, tuple, list]
    on_enter = TypedDict(default=None, allow_None=True, key_type=str,
                        doc="""callbacks to execute when a certain state is entered; 
                        specfied as map with state as keys and callbacks as list""") # typing.Dict[str, typing.List[typing.Callable]]
    on_exit = TypedDict(default=None, allow_None=True, key_type=str,
                        doc="""callbacks to execute when certain state is exited; 
                        specfied as map with state as keys and callbacks as list""") # typing.Dict[str, typing.List[typing.Callable]]
    machine = TypedDict(default=None, allow_None=True, key_type=str, item_type=(list, tuple),
                        doc="the machine specification with state as key and objects as list") # typing.Dict[str, typing.List[typing.Callable, RemoteParameter]]

    def __init__(self, 
            states : typing.Union[EnumMeta, typing.List[str], typing.Tuple[str]], *, 
            initial_state : typing.Union[StrEnum, str], 
            on_enter : typing.Dict[str, typing.Union[typing.List[typing.Callable], typing.Callable]] = {}, 
            on_exit  : typing.Dict[str, typing.Union[typing.List[typing.Callable], typing.Callable]] = {}, 
            push_state_change_event : bool = False,
            **machine : typing.Iterable[typing.Union[typing.Callable, RemoteParameter]]
        ) -> None:
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

    def has_object(self, object : typing.Union[RemoteParameter, typing.Callable]) -> bool:
        for state, objects in self.machine.items():
            if object in objects:
                return True 
        return False
    



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
    


class RemoteObject(Parameterized, metaclass=RemoteObjectMeta):

    __server_type__ = ServerTypes.REMOTE_OBJECT 
    state_machine : StateMachine

    # local parameters
    instance_name = String(default=None, regex=r'[A-Za-z]+[A-Za-z_0-9\-\/]*', constant=True, remote=False,
                        doc="""Unique string identifier of the instance. This value is used for many operations,
                        for example - creating zmq socket address, tables in databases, and to identify the instance 
                        in the HTTP Server & webdashboard clients - 
                        (http(s)://{domain and sub domain}/{instance name}). Instance names must be unique
                        in your entire system.""") # type: str
    logger = ClassSelector(class_=logging.Logger, default=None, allow_None=True, remote=False, 
                        doc="""Logger object to print log messages, should be instance of ``logging.Logger()``. Default 
                            logger is created if none supplied.""") # type: logging.Logger
    rpc_serializer = ClassSelector(class_=(BaseSerializer, str), 
                        allow_None=True, default='json', remote=False,
                        doc="""Serializer used for exchanging messages with RPC clients. Subclass to implement
                            your own serialization requirements.""") # type: BaseSerializer
    json_serializer = ClassSelector(class_=(JSONSerializer, str), default=None, allow_None=True, remote=False,
                        doc = """Serializer used for exchanging messages with a HTTP server,
                            subclass JSONSerializer to implement your own serialization requirements.""") # type: JSONSerializer
    
    # remote paramerters
    state = String(default=None, allow_None=True, URL_path='/state', readonly=True,
                fget= lambda self : self.state_machine.current_state if hasattr(self, 'state_machine') else None,  
                doc='current state machine state if state machine present') #type: type.Optional[str]
    
    httpserver_resources = RemoteParameter(readonly=True, URL_path='/resources/http-server', 
                        doc="object's resources exposed to HTTP client (through ``hololinked.server.HTTPServer``)", 
                        fget=lambda self: self._httpserver_resources ) # type: typing.Dict[str, HTTPResource]
    rpc_resources = RemoteParameter(readonly=True, URL_path='/resources/object-proxy', 
                        doc="object's resources exposed to RPC client, similar to HTTP resources but differs in details.", 
                        fget=lambda self: self._rpc_resources) # type: typing.Dict[str, RPCResource]
    gui_resources = RemoteParameter(readonly=True, URL_path='/resources/portal-app', 
                        doc="""object's data read by hololinked-portal GUI client, similar to http_resources but differs 
                        in details.""",
                        fget=lambda self: GUIResources().build(self)) # type: typing.Dict[str, typing.Any]
    GUI = ClassSelector(class_=ReactApp, default=None, allow_None=True, URL_path='/resources/web-gui',
                        doc="GUI specified here will become visible at GUI tab of hololinked-portal dashboard tool") # type: typing.Optional[ReactApp]
    
    object_info = RemoteParameter(doc="contains information about this object like the class name, script location etc.",
                        URL_path='/object-info') # type: RemoteObjectInformation
    events = RemoteParameter(readonly=True, URL_path='/events', 
                        doc="returns a dictionary with two fields containing event name and event information") # type: typing.Dict[str, typing.Any]
    

    def __new__(cls, *args, **kwargs):
        # defines some internal fixed attributes
        obj = super().__new__(cls)
        # objects created by us that require no validation but cannot be modified are called _internal_fixed_attributes
        obj._internal_fixed_attributes = ['_internal_fixed_attributes', 'instance_resources',
                                        '_httpserver_resources', '_rpc_resources', '_owner']        
        # objects given by user which we need to validate (mostly descriptors)
        return obj


    def __init__(self, *, instance_name : str, logger : typing.Optional[logging.Logger] = None, 
                rpc_serializer : typing.Optional[BaseSerializer] = 'json', 
                json_serializer : typing.Optional[JSONSerializer] = 'json',
                **params) -> None:
        if instance_name.startswith('/'):
            instance_name = instance_name[1:]
        rpc_serializer, json_serializer = _get_serializer_from_user_given_options(
                                                                    rpc_serializer=rpc_serializer,
                                                                    json_serializer=json_serializer
                                                                )
        
        super().__init__(instance_name=instance_name, logger=logger, 
                        rpc_serializer=rpc_serializer, json_serializer=json_serializer, **params)

        self._prepare_logger(log_level=params.get('log_level', None), log_file=params.get('log_file', None),
                    remote_access=params.get('logger_remote_access', self.__class__.logger_remote_access if hasattr(self.__class__, 
                                                                                'logger_remote_access') else False))
        self._prepare_state_machine()  
        self._prepare_DB(params.get('use_default_db', False), params.get('db_config_file', None))   


    def __post_init__(self):
        self._owner : typing.Optional[RemoteObject] = None 
        self._internal_fixed_attributes : typing.List[str]
        self._full_URL_path_prefix : str
        self.rpc_server : typing.Optional[RPCServer]
        self.message_broker : typing.Optional[AsyncPollingZMQServer]
        self._event_publisher : typing.Optional[EventPublisher]
        self._prepare_resources()
        self.logger.info("initialialised RemoteObject class {} with instance name {}".format(
            self.__class__.__name__, self.instance_name))  


    def __setattr__(self, __name: str, __value: typing.Any) -> None:
        if  __name == '_internal_fixed_attributes' or __name in self._internal_fixed_attributes: 
            # order of 'or' operation for above 'if' matters
            if not hasattr(self, __name) or getattr(self, __name, None) is None:
                # allow setting of fixed attributes once
                super().__setattr__(__name, __value)
            else:
                print(__name, getattr(self, __name, None))
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
        self._rpc_resources, self._httpserver_resources, self.instance_resources = get_organised_resources(self)


    def _prepare_logger(self, log_level : int, log_file : str, remote_access : bool = False):
        from .logger import RemoteAccessHandler
        if self.logger is None:
            self.logger = get_default_logger(self.instance_name, 
                                    logging.INFO if not log_level else log_level, 
                                    None if not log_file else log_file)
        if remote_access:
            if not any(isinstance(handler, RemoteAccessHandler) for handler in self.logger.handlers):
                self._remote_access_loghandler = RemoteAccessHandler(instance_name='logger', 
                                                    maxlen=500, emit_interval=1, logger=self.logger) 
                                                    # remote object has its own logger so we dont recreate one for
                                                    # remote access handler
                self.logger.addHandler(self._remote_access_loghandler)
        
        if not isinstance(self, logging.Logger):
            for handler in self.logger.handlers:
                # if remote access is True or not, if a default handler is found make a variable for it anyway
                if isinstance(handler, RemoteAccessHandler):
                    self._remote_access_loghandler = handler        


    def _prepare_state_machine(self):
        if hasattr(self, 'state_machine'):
            self.state_machine._prepare(self)
            self.logger.debug("setup state machine")

    
    def _prepare_DB(self, default_db : bool = False, config_file : str = None):
        if not default_db and not config_file: 
            self.object_info
            return 
        # 1. create engine 
        self.db_engine = RemoteObjectDB(instance=self, config_file=None if default_db else config_file, 
                                    serializer=self.rpc_serializer) # type: RemoteObjectDB 
        # 2. create an object metadata to be used by different types of clients
        object_info = self.db_engine.fetch_own_info()
        if object_info is not None:
            self._object_info = object_info
        # 3. enter parameters to DB if not already present 
        if self.object_info.class_name != self.__class__.__name__:
            raise ValueError("Fetched instance name and class name from database not matching with the ", 
                " current RemoteObject class/subclass. You might be reusing an instance name of another subclass ", 
                "and did not remove the old data from database. Please clean the database using database tools to ", 
                "start fresh.")


    @object_info.getter
    def _get_object_info(self):
        if not hasattr(self, '_object_info'):
            self._object_info = RemoteObjectInformation(
                    instance_name  = self.instance_name, 
                    class_name     = self.__class__.__name__,
                    script         = os.path.dirname(os.path.abspath(inspect.getfile(self.__class__))),
                    http_server    = "USER_MANAGED", 
                    kwargs         = "USER_MANAGED",  
                    eventloop_instance_name = "USER_MANAGED", 
                    level          = "USER_MANAGED", 
                    level_type     = "USER_MANAGED"
                )  
        return self._object_info
    
    @object_info.setter
    def _set_object_info(self, value):
        self._object_info = RemoteObjectInformation(**value)  
      
    
    @remote_method(URL_path='/parameters', http_method=HTTP_METHODS.GET)
    def _get_parameters(self, **kwargs) -> typing.Dict[str, typing.Any]:
        """
        """
        if len(kwargs) == 0:
            return self.parameters.descriptors.keys()
        data = {}
        if 'names' in kwargs:
            names = kwargs.get('names')
            if not isinstance(names, (list, tuple, str)):
                raise TypeError(f"Specify parameters to be fetched as a list, tuple or comma separated names. Givent type {type(names)}")
            if isinstance(names, str):
                names = names.split(',')
            for requested_parameter in names:
                if not isinstance(requested_parameter, str):
                    raise TypeError(f"parameter name must be a string. Given type {type(requested_parameter)}")
                data[requested_parameter] = self.parameters[requested_parameter].__get__(self, type(self))
        elif len(kwargs.keys()) != 0:
            for rename, requested_parameter in kwargs.items():
                data[rename] = self.parameters[requested_parameter].__get__(self, type(self))              
        else:
            for parameter in self.parameters.descriptors.keys():
                data[parameter] = self.parameters[parameter].__get__(self, type(self))
        return data 
    
    @remote_method(URL_path='/parameters', http_method=HTTP_METHODS.PATCH)
    def _set_parameters(self, values : typing.Dict[str, typing.Any]) -> None:
        """ 
        set parameters whose name is specified by keys of a dictionary
        
        Parameters
        ----------
        values: Dict[str, Any]
            dictionary of parameter names and its values
        """
        for name, value in values.items():
            setattr(self, name, value)


    @remote_method(URL_path='/parameters/db-reload', http_method=HTTP_METHODS.POST)
    def load_parameters_from_DB(self):
        if not hasattr(self, 'db_engine'):
            return
        
        def recursively_load_parameters_from_DB(obj : RemoteObject) -> None:
            nonlocal self
            for name, resource in inspect._getmembers(obj, lambda o : isinstance(o, RemoteObject), getattr_without_descriptor_read): 
                if name == '_owner':
                    continue
                recursively_load_parameters_from_DB(resource) # load from the lower up
            missing_parameters = self.db_engine.create_missing_parameters(obj.__class__.parameters.db_init_objects,
                                                                        get_missing_parameters=True)
            # 4. read db_init and db_persist objects
            for db_param in obj.db_engine.get_all_parameters():
                try:
                    if db_param.name not in missing_parameters:
                        setattr(obj, db_param.name, db_param.value) # type: ignore
                except Exception as ex:
                    obj.logger.error(f"could not set attribute {db_param.name} due to error {str(ex)}")

        recursively_load_parameters_from_DB(self)

   
    @remote_method(URL_path='/resources/postman-collection', http_method=HTTP_METHODS.GET)
    def _get_postman_collection(self, domain_prefix : str = None):
        """
        organised postman collection for this object
        """
        from .api_platform_utils import postman_collection
        return postman_collection.build(instance=self, 
                    domain_prefix=domain_prefix if domain_prefix is not None else self._object_info.http_server)
    
    @remote_method(URL_path='/resources/wot-td', http_method=HTTP_METHODS.GET)
    def _get_thing_description(self, authority : typing.Optional[str] = None, 
                            allow_loose_schema : typing.Optional[bool] = False): 
        """
        thing description schema of W3 Web of Things https://www.w3.org/TR/wot-thing-description11/, 
        one can use the node-wot client with the generated schema (https://github.com/eclipse-thingweb/node-wot)
        to as a client for the object. Other WoT related tools based on TD will be compatible. One can validate the 
        generated schema at https://playground.thingweb.io/.
        Composed RemoteObjects within the top level object is currently not supported.
        """
        from ..wot import ThingDescription
        return ThingDescription().build(self, authority or self._object_info.http_server,
                                            allow_loose_schema=allow_loose_schema)
    

    @property
    def event_publisher(self) -> EventPublisher:
        """
        event publishing PUB socket object
        """
        try:
            return self._event_publisher 
        except AttributeError:
            raise AttributeError("event publisher not yet created.") from None
                
    @event_publisher.setter
    def event_publisher(self, value : EventPublisher) -> None:
        if hasattr(self, '_event_publisher'):
            raise AttributeError("Can set event publisher only once.")
        
        def recusively_set_events_publisher(obj : RemoteObject, publisher : EventPublisher) -> None:
            for name, evt in inspect._getmembers(obj, lambda o: isinstance(o, Event), getattr_without_descriptor_read):
                assert isinstance(evt, Event), "object is not an event"
                # above is type definition
                evt.publisher = publisher 
                evt._remote_info.socket_address = publisher.socket_address
            for name, obj in inspect._getmembers(obj, lambda o: isinstance(o, RemoteObject), getattr_without_descriptor_read):
                if name == '_owner':
                    continue 
                recusively_set_events_publisher(obj, publisher)
            obj._event_publisher = publisher
            
        recusively_set_events_publisher(self, value)
    

    @remote_method(URL_path='/exit', http_method=HTTP_METHODS.POST)                                                                                                                                          
    def exit(self) -> None:
        """
        Exit the object without killing the eventloop that runs this object. If RemoteObject was 
        started using the run() method, the eventloop is also killed. 
        """
        if self._owner is None:
            raise BreakInnerLoop
        else:
            warnings.warn("call exit on the top object, composed objects cannot exit the loop.", RuntimeWarning)
 

    def run(self, 
            zmq_protocols : typing.Union[typing.List[ZMQ_PROTOCOLS], typing.Tuple[ZMQ_PROTOCOLS], 
                                         ZMQ_PROTOCOLS] = ZMQ_PROTOCOLS.IPC, 
            
            expose_eventloop : bool = False,
            **kwargs 
        ):
        """
        quick-start ``RemoteObject`` server by creating a default eventloop & servers. 
        """
        self.load_parameters_from_DB()

        context = zmq.asyncio.Context()
        self.message_broker = AsyncPollingZMQServer(
                                instance_name=f'{self.instance_name}/inner', # hardcoded be very careful
                                server_type=self.__server_type__.value,
                                context=context,
                                protocol=ZMQ_PROTOCOLS.INPROC, 
                                rpc_serializer=self.rpc_serializer,
                                json_serializer=self.json_serializer,
                                log_level=self.logger.level
                            )        
        self.rpc_server = RPCServer(
                                instance_name=self.instance_name, 
                                server_type=self.__server_type__.value, 
                                context=context, 
                                protocols=zmq_protocols, 
                                rpc_serializer=self.rpc_serializer, 
                                json_serializer=self.json_serializer, 
                                socket_address=kwargs.get('tcp_socket_address', None),
                                log_level=self.logger.level
                            ) 
        self.event_publisher = self.rpc_server.event_publisher 

        from .eventloop import EventLoop
        self.event_loop = EventLoop(
                    instance_name=f'{self.instance_name}/eventloop', 
                    remote_objects=[self], 
                    log_level=self.logger.level,
                    rpc_serializer=self.rpc_serializer, 
                    json_serializer=self.json_serializer, 
                    expose=expose_eventloop
                )
        self.event_loop.run()
       



__all__ = [
    RemoteObject.__name__, 
    StateMachine.__name__
]
