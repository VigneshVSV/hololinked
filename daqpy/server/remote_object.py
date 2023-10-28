import asyncio
from collections import deque
import json
import logging 
import inspect
import os
import threading
import time
import typing
import datetime
from enum import EnumMeta, Enum
from dataclasses import asdict, dataclass
from sqlalchemy import (Integer as DBInteger, String as DBString, JSON as DB_JSON, LargeBinary as DBBinary)
from sqlalchemy import select
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase, MappedAsDataclass

from ..param.parameterized import Parameterized, ParameterizedMetaclass 
from ..param.parameters import (String, ClassSelector, TupleSelector, TypedDict, Boolean, 
                                Selector, TypedKeyMappingsConstrainedDict)

from .constants import (EVENT, GET, IMAGE_STREAM, JSONSerializable, instance_name_regex, CallableType, CALLABLE, 
                        HTTP, PROXY, ATTRIBUTE, READ, WRITE, log_levels, POST, ZMQ_PROTOCOLS, FILE)
from .serializers import *
from .exceptions import BreakInnerLoop
from .decorators import (GUIResources, HTTPServerEventData, HTTPServerResourceData, ProxyResourceData, 
                            HTTPServerResourceData, FileServerData, ScadaInfoData, get, post, remote_method, 
                            ScadaInfoValidator)
from .api_platform_utils import postman_item, postman_itemgroup
from .database import BaseAsyncDB, BaseSyncDB
from .utils import create_default_logger, get_signature, wrap_text
from .api_platform_utils import *
from .remote_parameter import FileServer, PlotlyFigure, ReactApp, RemoteParameter, RemoteClassParameters, Image
from .remote_parameters import (Boolean as RemoteBoolean, ClassSelector as RemoteClassSelector, 
                                Integer as RemoteInteger )
from .zmq_message_brokers import ServerTypes, EventPublisher, AsyncPollingZMQServer, Event



class StateMachine:
    """
    A container class for state machine related logic, this is intended to be used by the 
    RemoteObject and its descendents.  
    	
    Args:
        initial_state (str): initial state of machine 
        states (Enum): Enum type holding enumeration of states 
        on_enter (Dict[str, Union[Callable, RemoteParameter]]): callbacks to be invoked when a certain state is entered. 
            It is to be specified as a dictionary with the states being the keys
        on_exit  (Dict[str, Union[Callable, RemoteParameter]]): callbacks to be invoked when a certain state is exited. 
            It is to be specified as a dictionary with the states being the keys
        
    Attributes: 
        exists (bool): internally computed, True if states and initial_states are valid 
    """
    initial_state = RemoteClassSelector(default=None, allow_None=True, constant=True, class_=(Enum, str))
    exists = RemoteBoolean(default=False)
    states = RemoteClassSelector(default=None, allow_None=True, constant=True, class_=(EnumMeta, tuple, list)) 
    on_enter = TypedDict(default=None, allow_None=True, key_type=str)
    on_exit = TypedDict(default=None, allow_None=True, key_type=str) 
    machine = TypedDict(default=None, allow_None=True, key_type=str, item_type=(list, tuple))

    def __init__(self, states : typing.Union[EnumMeta, typing.List[str], typing.Tuple[str]], *, 
            initial_state : typing.Union[Enum, str], 
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
            self.state_change_event = Event('state-change') 

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
                    if hasattr(resource, 'scada_info'):
                        assert isinstance(resource.scada_info, ScadaInfoValidator) # type: ignore
                        if resource.scada_info.iscallable and resource.scada_info.obj_name not in owner_methods: # type: ignore
                            raise AttributeError("Given object {} for state machine does not belong to class {}".format(
                                                                                                resource, owner))
                        if resource.scada_info.isparameter and resource not in owner_parameters: # type: ignore
                            raise AttributeError("Given object {} - {} for state machine does not belong to class {}".format(
                                                                                                resource.name, resource, owner))
                        if resource.scada_info.state is None: # type: ignore
                            resource.scada_info.state = self._machine_compliant_state(state) # type: ignore
                        else: 
                            resource.scada_info.state = resource.scada_info.state + (self._machine_compliant_state(state), ) # type: ignore
                    else: 
                        raise AttributeError(wrap_text(f"""Object {resource} not made remotely accessible. 
                                    Use state machine with remote parameters and remote methods only"""))
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
        
    def __contains__(self, state : typing.Union[str, Enum]):
        if isinstance(self.states, EnumMeta) and state not in self.states.__members__ and state not in self.states: # type: ignore
            return False 
        elif isinstance(self.states, (tuple, list)) and state not in self.states:
            return False 
        return True
        
    def _machine_compliant_state(self, state) -> typing.Union[Enum, str]:
        if isinstance(self.states, EnumMeta):
            return self.states.__members__[state] # type: ignore
        return state 
    
    def get_state(self) -> typing.Union[str, Enum, None]:
        """return the current state. one can also access the property `current state`.
        Returns:
            str: current state
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
            raise ValueError(wrap_text("""given state '{}' not in set of allowed states : {}.
                    """.format(value, self.states)
            ))
    
    current_state = property(get_state, set_state, None, doc = """
        read and write current state of the state machine""")

    def query(self, info : typing.Union[str, typing.List[str]] ) -> typing.Any:
        raise NotImplementedError("arbitrary quering of {} not possible".format(self.__class__.__name__))
    


class RemoteObjectDB(BaseSyncDB):

    class TableBase(DeclarativeBase):
        pass 

    class RemoteObjectInfo(MappedAsDataclass, TableBase):
        __tablename__ = "remote_objects"

        instance_name  : Mapped[str] = mapped_column(DBString, primary_key = True)
        class_name     : Mapped[str] = mapped_column(DBString)
        http_server    : Mapped[str] = mapped_column(DBString)
        script         : Mapped[str] = mapped_column(DBString)
        args           : Mapped[JSONSerializable] = mapped_column(DB_JSON)
        kwargs         : Mapped[JSONSerializable] = mapped_column(DB_JSON)
        eventloop_name : Mapped[str] = mapped_column(DBString)
        level          : Mapped[int] = mapped_column(DBInteger)
        level_type     : Mapped[str] = mapped_column(DBString)

        def json(self):
            return asdict(self)
        
    class Parameter(TableBase):
        __tablename__ = "parameters"

        id : Mapped[int] = mapped_column(DBInteger, primary_key = True, autoincrement = True)
        instance_name  : Mapped[str] = mapped_column(DBString)
        name : Mapped[str] = mapped_column(DBString)
        serialized_value : Mapped[bytes] = mapped_column(DBBinary) 

    @dataclass 
    class ParameterData:
        name : str 
        value : typing.Any

    def __init__(self, instance_name : str, serializer : BaseSerializer,
                    config_file: typing.Union[str, None] = None ) -> None:
        super().__init__(database = 'scadapyserver', serializer = serializer, config_file = config_file)
        self.instance_name = instance_name
        
    def fetch_own_info(self) -> RemoteObjectInfo:
        with self.sync_session() as session:
            stmt = select(self.RemoteObjectInfo).filter_by(instance_name = self.instance_name)
            data = session.execute(stmt)
            data = data.scalars().all()
            if len(data) == 0:
                return None 
            return data[0]
            
    def read_all_parameters(self, deserialized : bool = True) -> typing.Sequence[typing.Union[Parameter,
                                                                                ParameterData]]:
        with self.sync_session() as session:
            stmt = select(self.Parameter).filter_by(instance_name = self.instance_name)
            data = session.execute(stmt)
            existing_params = data.scalars().all()
            if not deserialized:
                return existing_params
            else:
                params_data = []
                for param in existing_params:
                    params_data.append(self.ParameterData(
                        name = param.name, 
                        value = self.serializer.loads(param.serialized_value)
                    ))
                return params_data
          
    def edit_parameter(self, parameter : RemoteParameter, value : typing.Any) -> None:
        with self.sync_session() as session:
            stmt = select(self.Parameter).filter_by(instance_name = self.instance_name, name = parameter.name)
            data = session.execute(stmt)
            param = data.scalar()
            param.serialized_value = self.serializer.dumps(value)
            session.commit()

    def create_missing_db_parameters(self, parameters : typing.Dict[str, RemoteParameter]) -> None:
        with self.sync_session() as session:
            existing_params = self.read_all_parameters()
            existing_names = [p.name for p in existing_params]
            for name, new_param in parameters.items():
                if name not in existing_names: 
                    param = self.Parameter(
                        instance_name = self.instance_name, 
                        name = new_param.name, 
                        serialized_value = self.serializer.dumps(new_param.default)
                    )
                    session.add(param)
            session.commit()
                


ConfigInfo = Enum('LevelTypes','USER_MANAGED PRIMARY_HOST_WIDE PC_HOST_WIDE')


class RemoteObjectMetaclass(ParameterizedMetaclass):
    
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
        mcs._param_container = RemoteClassParameters(mcs, mcs_members)

    @property
    def parameters(mcs) -> RemoteClassParameters:
        return mcs._param_container
    


class RemoteSubobject(Parameterized, metaclass=RemoteObjectMetaclass):
    """
    Subclass from here for remote capable sub objects composed within remote object instance. Does not support 
    state machine, logger, serializers, dedicated message brokers etc. 
    """

    instance_name = String(default=None, regex=instance_name_regex, constant = True,
                        doc = """Unique string identifier of the instance used for many operations,
                        for example - creating zmq socket address, tables in databases, and to identify the instance 
                        in the HTTP Server & scadapy.webdashboard client - 
                        (http(s)://{domain and sub domain}/{instance name}). It is suggested to use  
                        the class name along with a unique name {class name}/{some name}. Instance names must be unique
                        in your entire system.""") # type: ignore
    events = RemoteParameter(readonly=True, URL_path='/events', 
                        doc="returns a dictionary with two fields " ) # type: ignore
    httpserver_resources = RemoteParameter(readonly=True, URL_path='/resources/http', 
                        doc="""""" ) # type: ignore
    proxy_resources = RemoteParameter(readonly=True, URL_path='/resources/proxy', 
                        doc= """object's resources exposed to ProxyClient, similar to http_resources but differs 
                        in details.""") # type: ignore
    
    
    def __new__(cls, **kwargs):
        """
        custom defined __new__ method to assign some important attributes at instance creation time directly instead of 
        super().__init__(instance_name = val1 , users_own_kw_argument1 = users_val1, ..., users_own_kw_argumentn = users_valn) 
        method. The lowest child's __init__ is always called first and  then the code reaches the __init__ of RemoteObject. 
        Therefore, when the user passes arguments to his own RemoteObject descendent, they have to again pass some required 
        information (like instance_name) to the __init__ of super() a second time with proper keywords.
        To avoid this hassle, we create this __new__. super().__init__() in a descendent is still not optional though. 
        """
        obj = super().__new__(cls)
        # objects created by us that require no validation but cannot be modified are called _internal_fixed_attributes
        obj._internal_fixed_attributes = ['_internal_fixed_attributes', 'instance_resources', '_owner']        
        # objects given by user which we need to validate (mostly descriptors)
        obj.instance_name = kwargs.get('instance_name', None)
        return obj
    
    def __post_init__(self):
        self.instance_name : str
        self.httpserver_resources : typing.Dict
        self.proxy_resources : typing.Dict
        self.events : typing.Dict
        self._owner : typing.Optional[typing.Union[RemoteSubobject, RemoteObject]]
        self._internal_fixed_attributes : typing.List[str]
           
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
                    raise RuntimeError(wrap_text("""Error while finding owner of RemoteSubobject, 
                        RemoteSubobject must be composed only within RemoteObject or RemoteSubobject, 
                        otherwise there can be problems."""))

    def __setattr__(self, __name: str, __value: typing.Any) -> None:
        if  __name == '_internal_fixed_attributes' or __name in self._internal_fixed_attributes: 
            # order of 'or' operation for above 'if' matters
            if not hasattr(self, __name):
                # allow setting of fixed attributes once
                super().__setattr__(__name, __value)
            else:
                raise AttributeError(
                    wrap_text(
                        f"""
                        Attempted to set {__name} more than once. cannot assign a value to this variable after creation. 
                        """
                ))
        else:
            super().__setattr__(__name, __value)


    def _prepare_resources(self):
        """
        this function analyses the members of the class which have 'scadapy' variable declared
        and extracts information 
        """
        # The following dict is to be given to the HTTP server
        httpserver_resources = dict(
            GET     = dict(),
            POST    = dict(),
            PUT     = dict(),
            DELETE  = dict(),
            OPTIONS = dict()
        )
        # The following dict will be given to the proxy client
        proxy_resources = dict()
        # The following dict will be used by the event loop
        instance_resources : typing.Dict[str, ScadaInfoData] = dict()
        # create URL prefix
        self.full_URL_path_prefix = f'{self._owner.full_URL_path_prefix}/{self.instance_name}' if self._owner is not None else f'/{self.instance_name}'
        
        # First add methods and callables
        for name, resource in inspect.getmembers(self, inspect.ismethod):
            if hasattr(resource, 'scada_info'):
                if not isinstance(resource.scada_info, ScadaInfoValidator): # type: ignore
                    raise TypeError("instance member {} has unknown sub-member 'scada_info' of type {}.".format(
                                resource, type(resource.scada_info))) # type: ignore 
                scada_info = resource.scada_info.create_dataclass(obj=resource, bound_obj=self) # type: ignore
                # methods are already bound though
                fullpath = "{}{}".format(self.full_URL_path_prefix, scada_info.URL_path) 
                if scada_info.iscallable:
                    if HTTP in scada_info.access_type:
                        for http_method in scada_info.http_method:
                            httpserver_resources[http_method][fullpath] = HTTPServerResourceData(
                                                        what=CALLABLE,
                                                        instance_name=self._owner.instance_name if self._owner is not None else self.instance_name,
                                                        fullpath=fullpath,
                                                        instruction=fullpath,
                                                        http_request_as_argument=scada_info.http_request_as_argument 
                                                    )
                    if PROXY in scada_info.access_type:
                        proxy_resources[fullpath] = ProxyResourceData(
                                                                    what=CALLABLE,
                                                                    instruction=fullpath,                                                                                                                                                                                        
                                                                    module=getattr(resource, '__module__'), 
                                                                    name=getattr(resource, '__name__'),
                                                                    qualname=getattr(resource, '__qualname__'), 
                                                                    doc=getattr(resource, '__doc__'),
                                                                    kwdefaults=getattr(resource, '__kwdefaults__'),
                                                                    defaults=getattr(resource, '__defaults__'),
                                                                )
                    instance_resources[fullpath] = scada_info 
        # Other remote objects 
        for name, resource in inspect.getmembers(self, lambda o : isinstance(o, RemoteSubobject)):
            if name == '_owner':
                continue
            elif isinstance(resource, RemoteSubobject):
                resource._owner = self 
                resource._prepare_instance()                    
                for http_method, resources in resource.httpserver_resources.items():
                    httpserver_resources[http_method].update(resources)
                proxy_resources.update(resource.proxy_resources)
                instance_resources.update(resource.instance_resources)
        # Events
        for name, resource in inspect.getmembers(self, lambda o : isinstance(o, Event)):
            assert isinstance(resource, Event)
            resource._owner = self
            resource.full_URL_path_prefix = self.full_URL_path_prefix
            resource.publisher = self._event_publisher                
            httpserver_resources[GET]['{}/event{}'.format(
                        self.full_URL_path_prefix, resource.URL_path)] = HTTPServerEventData(
                                                            # event URL_path has '/' prefix
                                                            what=EVENT,
                                                            event_name=resource.name,
                                                            socket_address=self._event_publisher.socket_address
                                                        )
        # Parameters
        for parameter in self.parameters.descriptors.values():
            if hasattr(parameter, 'scada_info'): 
                if not isinstance(parameter.scada_info, ScadaInfoValidator):  # type: ignore
                    raise TypeError("instance member {} has unknown sub-member 'scada_info' of type {}.".format(
                                parameter, type(parameter.scada_info))) # type: ignore
                    # above condition is just a gaurd in case user does some unpredictable patching activities
                scada_info = parameter.scada_info.create_dataclass(obj=parameter, bound_obj=self) # type: ignore
                fullpath = "{}{}".format(self.full_URL_path_prefix, scada_info.URL_path) 
                if scada_info.isparameter:
                    if HTTP in scada_info.access_type:
                        read_http_method, write_http_method = scada_info.http_method
                       
                        httpserver_resources[read_http_method][fullpath] = HTTPServerResourceData(
                                                        what=ATTRIBUTE, 
                                                        instance_name=self._owner.instance_name if self._owner is not None else self.instance_name,
                                                        fullpath=fullpath,
                                                        instruction=fullpath + '/' + READ
                                                    )
                        if isinstance(parameter, Image) and parameter.streamable:
                            parameter.event._owner = self 
                            parameter.event.full_URL_path_prefix = self.full_URL_path_prefix
                            parameter.event.publisher = self._event_publisher         
                            httpserver_resources[GET]['{}/event{}'.format(
                                            self.full_URL_path_prefix, parameter.event.URL_path)] = HTTPServerEventData(
                                                        what=EVENT, 
                                                        event_name=parameter.event.name,
                                                        socket_address=self._event_publisher.socket_address,
                                                    )
                        httpserver_resources[write_http_method][fullpath] = HTTPServerResourceData(
                                                        what=ATTRIBUTE, 
                                                        instance_name=self._owner.instance_name if self._owner is not None else self.instance_name,
                                                        fullpath=fullpath,
                                                        instruction=fullpath + '/' + WRITE
                                                    )
                        
                    if PROXY in scada_info.access_type:
                        proxy_resources[fullpath] = ProxyResourceData(
                                what=ATTRIBUTE, 
                                instruction=fullpath, 
                                module=__file__, 
                                doc=parameter.__doc__, 
                                name=scada_info.obj_name,
                                qualname=self.__class__.__name__ + '.' + scada_info.obj_name,
                                # qualname is not correct probably, does not respect inheritance
                                kwdefaults=None, 
                                defaults=None, 
                            ) 
                    if isinstance(parameter, FileServer):
                        read_http_method, _ = scada_info.http_method
                        fileserverpath = "{}/files{}".format(self.full_URL_path_prefix, scada_info.URL_path)
                        httpserver_resources[read_http_method][fileserverpath] = FileServerData(
                                                        what=FILE, 
                                                        directory=parameter.directory,
                                                        fullpath=fileserverpath
                                                    )
                    instance_resources[fullpath+'/'+READ] = scada_info
                    instance_resources[fullpath+'/'+WRITE] = scada_info      
        # The above for-loops can be used only once, the division is only for readability
        # _internal_fixed_attributes - allowed to set only once
        self._proxy_resources = proxy_resources       
        self._httpserver_resources = httpserver_resources 
        self.instance_resources = instance_resources


    def _prepare_instance(self):
        """
        iterates through the members of the Remote Object to identify the information that requires to be supplied 
        to the HTTPServer, ProxyClient and EventLoop. Called by default in the __init__ of RemoteObject.
        """
        self._prepare_resources()

    @httpserver_resources.getter 
    def _get_httpserver_resources(self) -> typing.Dict[str, typing.Dict[str, typing.Any]]:
        return self._httpserver_resources

    @proxy_resources.getter 
    def _get_proxy_resources(self) -> typing.Dict[str, typing.Dict[str, typing.Any]]:
        return self._proxy_resources
    


class RemoteObject(RemoteSubobject): 
    """
    Expose your python classes for HTTP methods by subclassing from here. 
    """
    __server_type__ = ServerTypes.USER_REMOTE_OBJECT 
    state_machine : StateMachine

    # objects given by user which we need to validate:
    eventloop_name  = String(default=None, constant=True, 
                        doc = """internally managed, this value is the instance name of the eventloop where the object
                        is running. Multiple objects can accept requests in a single event loop.""") # type: ignore
    log_level       = Selector(objects=[logging.DEBUG, logging.INFO, logging.ERROR, 
                                logging.CRITICAL, logging.ERROR], default = logging.INFO, allow_None = False, 
                        doc="""One can either supply a logger or simply set this parameter to to create an internal logger 
                        with specified level.""") # type: ignore
    logger          = ClassSelector(class_=logging.Logger, default=None, allow_None=True, 
                        doc = """Logger object to print log messages, should be instance of logging.Logger(). default 
                        logger is created if none is supplied.""") # type: ignore
    logfile     = String (default=None, allow_None=True, 
                        doc="""Logs can be also be stored in a file when a valid filename is passed.""") # type: ignore
    logger_remote_access = Boolean(default=False, 
                        doc="""Set it to true to add a default RemoteAccessHandler to the logger""" )
    db_config_file = String (default=None, allow_None=True, 
                        doc="""logs can be also be stored in a file when a valid filename is passed.""") # type: ignore
    server_protocols = TupleSelector(default=None, allow_None=True, accept_list=True, 
                                objects=[ZMQ_PROTOCOLS.IPC, ZMQ_PROTOCOLS.TCP], constant=True, 
                                doc="""Protocols to be supported by the ZMQ Server that accepts requests for the RemoteObject
                                instance. Options are TCP, IPC or both, represented by the Enum ZMQ_PROTOCOLS. 
                                Either pass one or both as list or tuple""") # type: ignore
    proxy_serializer = ClassSelector(class_=(SerpentSerializer, JSONSerializer, PickleSerializer, str), # DillSerializer, 
                                default='json',  
                                doc="""The serializer that will be used for passing messages in zmq. For custom data 
                                    types which have serialization problems, you can subclass the serializers and implement 
                                    your own serialization options. Recommended serializer for exchange messages between
                                    Proxy clients and server is Serpent and for HTTP serializer and server is JSON.""") # type: ignore
    json_serializer  = ClassSelector(class_=JSONSerializer, default=None, allow_None=True,
                                doc = """Serializer used for sending messages between HTTP server and remote object,
                                subclass JSONSerializer to implement undealt serialization options.""") # type: ignore
    
    # remote paramaters
    object_info = RemoteParameter(readonly=True, URL_path='/object-info',
                        doc="obtained information about this object like the class name, script location etc.") # type: ignore
    events : typing.Dict = RemoteParameter(readonly=True, URL_path='/events', 
                        doc="returns a dictionary with two fields " ) # type: ignore
    gui_resources : typing.Dict = RemoteParameter(readonly=True, URL_path='/resources/gui', 
                        doc= """object's data read by scadapy webdashboard GUI client, similar to http_resources but differs 
                        in details.""") # type: ignore
    GUI = RemoteClassSelector(class_=ReactApp, default=None, allow_None=True, 
                        doc= """GUI applied here will become visible at GUI tab of dashboard tool""")
    

    def __new__(cls, **kwargs):
        """
        custom defined __new__ method to assign some important attributes at instance creation time directly instead of 
        super().__init__(instance_name = val1 , users_own_kw_argument1 = users_val1, ..., users_own_kw_argumentn = users_valn) 
        method. The lowest child's __init__ is always called first and  then the code reaches the __init__ of RemoteObject. 
        Therefore, when the user passes arguments to his own RemoteObject descendent, they have to again pass some required 
        information (like instance_name) to the __init__ of super() a second time with proper keywords.
        To avoid this hassle, we create this __new__. super().__init__() in a descendent is still not optional though. 
        """
        obj = super().__new__(cls, **kwargs)
        # objects given by user which we need to validate (descriptors)
        obj.logfile       = kwargs.get('logfile', None)
        obj.log_level     = kwargs.get('log_level', logging.INFO)
        obj.logger_remote_access = obj.__class__.logger_remote_access if isinstance(obj.__class__.logger_remote_access, bool) else kwargs.get('logger_remote_access', False)
        obj.logger        = kwargs.get('logger', None)
        obj.db_config_file = kwargs.get('db_config_file', None)    
        obj.eventloop_name = kwargs.get('eventloop_name', None)  
        obj.server_protocols = kwargs.get('server_protocols', (ZMQ_PROTOCOLS.IPC, ZMQ_PROTOCOLS.TCP))
        obj.json_serializer  = kwargs.get('json_serializer', None)
        obj.proxy_serializer = kwargs.get('proxy_serializer', 'json')   
        return obj
    

    def __init__(self, **params) -> None:
        # Signature of __new__ and __init__ is generally the same, however one reaches this __init__ 
        # through the child class. Currently it is not expected to pass the instance_name, log_level etc. 
        # once through instantian and once again through child class __init__  
        for attr in ['instance_name', 'logger', 'log_level', 'logfile', 'db_config_file', 'eventloop_name', 
                    'server_protocols', 'json_serializer', 'proxy_serializer']:
            params.pop(attr, None)
        super().__init__(**params)

        # missing type definitions
        self.eventloop_name : str 
        self.logfile : str
        self.log_level  : int 
        self.logger : logging.Logger 
        self.db_engine : RemoteObjectDB
        self.server_protocols : typing.Tuple[Enum]
        self.json_serializer : JSONSerializer
        self.proxy_serializer : BaseSerializer
        self.object_info : RemoteObjectDB.RemoteObjectInfo

        self._prepare_message_brokers()
        self._prepare_state_machine()     

    def __post_init__(self):
        super().__post_init__()
        # Never create events before _prepare_instance(), no checks in place
        self._owner = None
        self._prepare_instance()
        self._prepare_DB()
        self.logger.info("initialialised RemoteObject of class {} with instance name {}".format(
            self.__class__.__name__, self.instance_name))  
      
    def _prepare_message_brokers(self):
        self.message_broker = AsyncPollingZMQServer(
                                instance_name=self.instance_name, 
                                server_type=self.__server_type__,
                                protocols=self.server_protocols, json_serializer=self.json_serializer,
                                proxy_serializer=self.proxy_serializer
                            )
        self.json_serializer = self.message_broker.json_serializer
        self.proxy_serializer = self.message_broker.proxy_serializer
        self.event_publisher = EventPublisher(identity=self.instance_name, proxy_serializer=self.proxy_serializer,
                                              json_serializer=self.json_serializer)
        
    def _create_object_info(self, script_path : typing.Optional[str] = None):
        if not script_path:
            try:
                script_path = os.path.dirname(os.path.abspath(inspect.getfile(self.__class__)))
            except:
                script_path = ''
        return RemoteObjectDB.RemoteObjectInfo(
                    instance_name  = self.instance_name, 
                    class_name     = self.__class__.__name__,
                    script         = script_path,
                    http_server    = ConfigInfo.USER_MANAGED.name, 
                    args           = ConfigInfo.USER_MANAGED.name, 
                    kwargs         = ConfigInfo.USER_MANAGED.name,  
                    eventloop_name = self.eventloop_name, 
                    level          = 0, 
                    level_type     = ConfigInfo.USER_MANAGED.name, 
                )  

    def _prepare_DB(self):
        if not self.db_config_file:
            self._object_info = self._create_object_info()
            return 
        # 1. create engine 
        self.db_engine = RemoteObjectDB(instance_name = self.instance_name, serializer = self.proxy_serializer,
                                        config_file = self.db_config_file)
        # 2. create an object metadata to be used by different types of clients
        object_info = self.db_engine.fetch_own_info()
        if object_info is None:
            object_info = self._create_object_info()
        self._object_info = object_info
        # 3. enter parameters to DB if not already present 
        if self.object_info.class_name != self.__class__.__name__:
            raise ValueError(wrap_text(f"""
                Fetched instance name and class name from database not matching with the current RemoteObject class/subclass.
                You might be reusing an instance name of another subclass and did not remove the old data from database. 
                Please clean the database using database tools to start fresh. 
                """))
        self.db_engine.create_missing_db_parameters(self.__class__.parameters.db_init_objects)
        # 4. read db_init and db_persist objects
        for db_param in  self.db_engine.read_all_parameters():
            try:
                setattr(self, db_param.name, self.proxy_serializer.loads(db_param.value)) # type: ignore
            except Exception as E:
                self.logger.error(f"could not set attribute {db_param.name} due to error {E}")

    def _prepare_state_machine(self):
        if hasattr(self, 'state_machine'):
            self.state_machine._prepare(self)
            self.logger.debug("setup state machine")
        
    @logger.getter
    def _get_logger(self) -> logging.Logger:
        return self._logger

    @logger.setter # type: ignore
    def _set_logger(self, value : logging.Logger):
        if value is None:
            self._logger = create_default_logger('{}|{}'.format(self.__class__.__name__, self.instance_name), 
                            self.log_level, self.logfile)
            if self.logger_remote_access and not any(isinstance(handler, RemoteAccessHandler) 
                                                        for handler in self.logger.handlers):
                self.remote_access_handler = RemoteAccessHandler(instance_name='logger', maxlen=500, emit_interval=1)
                self.logger.addHandler(self.remote_access_handler)
            else:
                for handler in self.logger.handlers:
                    if isinstance(handler, RemoteAccessHandler):
                        self.remote_access_handler = handler        
        else:
            self._logger = value

    @object_info.getter
    def _get_object_info(self): 
        try:
            return self._object_info
        except AttributeError:
            return None 
        
    @events.getter
    def _get_events(self) -> typing.Dict[str, typing.Any]:
        return {
            event._event_unique_str.decode() : dict(
                name = event.name,
                instruction = event._event_unique_str.decode(),
                owner = event.owner.__class__.__name__,
                owner_instance_name =  event.owner.instance_name,
                address = self.event_publisher.socket_address
            ) for event in self.event_publisher.events
        }
 
    @gui_resources.getter
    def _get_gui_resources(self):
        gui_resources = GUIResources(
            instance_name=self.instance_name,
            events = self.events, 
            classdoc = self.__class__.__doc__.splitlines() if self.__class__.__doc__ is not None else None, 
            inheritance = [class_.__name__ for class_ in self.__class__.mro()],
            GUI = self.GUI,
        )
        for instruction, scada_info in self.instance_resources.items(): 
            if scada_info.iscallable:
                gui_resources.methods[instruction] = self.proxy_resources[instruction].json() 
                gui_resources.methods[instruction]["scada_info"] = scada_info.json() 
                # to check - apparently the recursive json() calling does not reach inner depths of a dict, 
                # therefore we call json ourselves
                gui_resources.methods[instruction]["owner"] = self.proxy_resources[instruction].qualname.split('.')[0]
                gui_resources.methods[instruction]["owner_instance_name"] = scada_info.bound_obj.instance_name
                gui_resources.methods[instruction]["type"] = 'classmethod' if isinstance(scada_info.obj, classmethod) else ''
                gui_resources.methods[instruction]["signature"] = get_signature(scada_info.obj)[0]
            elif scada_info.isparameter:
                path_without_RW = instruction.rsplit('/', 1)[0]
                if path_without_RW not in gui_resources.parameters:
                    gui_resources.parameters[path_without_RW] = self.__class__.parameters.webgui_info(scada_info.obj)[scada_info.obj.name]
                    gui_resources.parameters[path_without_RW]["instruction"] = path_without_RW
                    """
                    The instruction part has to be cleaned up to be called as fullpath. Setting the full path back into 
                    scada_info is not correct because the unbound method is used by multiple instances. 
                    """
                    gui_resources.parameters[path_without_RW]["owner_instance_name"] = scada_info.bound_obj.instance_name
                    if isinstance(scada_info.obj, PlotlyFigure):
                        gui_resources.parameters[path_without_RW]['default'] = None
                        gui_resources.parameters[path_without_RW]['visualization'] = {
                                'type' : 'plotly',
                                'plot' : scada_info.obj.__get__(self, type(self)),
                                'sources' : scada_info.obj.data_sources,
                                'actions' : {
                                    scada_info.obj._action_stub.id : scada_info.obj._action_stub
                                },
                        }
                    elif isinstance(scada_info.obj, Image):
                        gui_resources.parameters[path_without_RW]['default'] = None
                        gui_resources.parameters[path_without_RW]['visualization'] = {
                            'type' : 'sse-video',
                            'sources' : scada_info.obj.data_sources,
                            'actions' : {
                                    scada_info.obj._action_stub.id : scada_info.obj._action_stub
                                },
                        }
        return gui_resources
   
    @get(URL_path='/resources/postman-collection')
    def postman_collection(self, domain_prefix : str = 'https://localhost:8080') -> postman_collection:
        try:
            return self._postman_collection
        except AttributeError:
            pass 
        parameters_folder = postman_itemgroup(name = 'parameters')
        methods_folder = postman_itemgroup(name = 'methods')
        events_folder = postman_itemgroup(name = 'events')

        collection = postman_collection(
            info = postman_collection_info(
                name = self.__class__.__name__,
                description = "API endpoints available for Remote Object", 
            ),
            item = [ 
                parameters_folder,
                methods_folder                
            ]
        )

        for http_method, resource in self.httpserver_resources.items():
            # i.e. this information is generated only on the httpserver accessible resrouces...
            for URL_path, httpserver_data in resource.items():
                if isinstance(httpserver_data, HTTPServerResourceData):
                    scada_info : ScadaInfoData
                    try:
                        scada_info = self.instance_resources[httpserver_data.instruction]
                    except KeyError:
                        parameter_path_without_RW = httpserver_data.instruction.rsplit('/', 1)[0]
                        scada_info = self.instance_resources[parameter_path_without_RW]
                    item = postman_item(
                        name = scada_info.obj_name,
                        request = postman_http_request(
                            description=scada_info.obj.__doc__,
                            url=domain_prefix + URL_path, 
                            method=http_method,
                        )
                    )
                    if scada_info.isparameter:
                        parameters_folder.add_item(item)
                    elif scada_info.iscallable:
                        methods_folder.add_item(item)
        
        self._postman_collection = collection
        return collection
    
    @post(URL_path='/resources/postman-collection/save')
    def save_postman_collection(self, filename : typing.Optional[str] = None) -> None:
        if filename is None: 
            filename = f'{self.__class__.__name__}_postman_collection.json'
        with open(filename, 'w') as file:
            json.dump(self.postman_collection().json(), file, indent = 4)
        
    @get('/parameters/names')
    def _parameters(self):
        return self.parameters.descriptors.keys()

    @get('/parameters/values')
    def parameter_values(self, **kwargs) -> typing.Dict[str, typing.Any]:
        """
        returns requested parameter values in a dict
        """
        data = {}
        for field, requested_parameter in kwargs.items():
            data[field] = self.parameters[requested_parameter].__get__(self, type(self))
        return data 

    @get('/state')    
    def state(self):
        if hasattr(self, 'state_machine'):
            return self.state_machine.current_state
        else:
            return None
    
    # Example of get and post decorator 
    @post('/exit')                                                                                                                                          
    def exit(self) -> None:
        raise BreakInnerLoop

    @get('/ping')
    def ping(self) -> bool:
        return True

    @get('/test/speed')    
    def _test_speed(self, value : typing.Any):
        """
        This method returns whatever you give allowing speed test of different data types. 
        The message sent is first serialized by the client, deserialized by the server and in return direction
        again serialized by server and deserialized by the client. oneway speed is twice the measured value.  
        """
        return value
    
    @get('/test/args/{int_arg:int}/{float_arg:float}/{str_arg:str}')
    def _test_path_arguments(self, int_arg, float_arg, str_arg):
        self.logger.info(f"passed arguments : int - {int_arg}, float - {float_arg}, str - {str_arg}")
          
    # example of remote_method decorator
    @remote_method(URL_path='/log/console', http_method = POST)
    def log_to_console(self, data : typing.Any = None, level : typing.Any = 'DEBUG') -> None:
        if level not in log_levels.keys():
            self.logger.error("log level {} invalid. logging with level INFO.".format(level))
        if data is None:
            self.logger.log(log_levels.get(level, logging.INFO), "{} is alive.".format(self.instance_name))
        else:
            self.logger.log(log_levels.get(level, logging.INFO), "{}".format(data))
       
    def query(self, info : typing.Union[str, typing.List[str]]) -> typing.Any:
        raise NotImplementedError("arbitrary quering of {} currently not possible".format(self.__class__.__name__))

    def run(self):
        from .eventloop import EventLoop
        _eventloop = asyncio.get_event_loop()
        _eventloop.run_until_complete(EventLoop.run_single_target(self))
       


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
        # self._last_time = datetime.datetime.now()
        if not isinstance(emit_interval, (float, int)) or emit_interval < 1.0:
            raise TypeError("Specify log emit interval as number greater than 1.0") 
        else:
            self.emit_interval = emit_interval # datetime.timedelta(seconds=1.0) if not emit_interval else datetime.timedelta(seconds=emit_interval)
        self.event = Event('log-events')
        self.diff_logs = []
        self.maxlen = maxlen
        self._push_events = False
    
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

    maxlen = RemoteInteger(default=100, bounds=(1, None), crop_to_bounds=True, URL_path='/maxlen',
            fget=get_maxlen, fset=set_maxlen )


    @post('/events/start/{type:str}')
    def push_events(self, type : str, interval : float):
        self.emit_interval = interval # datetime.timedelta(seconds=interval)
        self._push_events = True 
        print("log event type", type)
        if type == 'asyncio':
            asyncio.get_event_loop().call_soon(lambda : asyncio.create_task(self.async_push_diff_logs()))
        else:
            self._events_thread = threading.Thread(target=self.push_diff_logs)
            self._events_thread.start()

    @post('/events/stop')
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
     
    debug_logs = RemoteParameter(readonly=True, URL_path='/logs/debug')
    @debug_logs.getter 
    def get_debug_logs(self):
        return self._debug_logs
    
    warn_logs = RemoteParameter(readonly=True, URL_path='/logs/warn')
    @warn_logs.getter 
    def get_warn_logs(self):
        return self._warn_logs
    
    info_logs = RemoteParameter(readonly=True, URL_path='/logs/info')
    @info_logs.getter 
    def get_info_logs(self):
        return self._info_logs
    
    error_logs = RemoteParameter(readonly=True, URL_path='/logs/error')
    @error_logs.getter 
    def get_error_logs(self):
        return self._error_logs
    
    critical_logs = RemoteParameter(readonly=True, URL_path='/logs/critical')
    @critical_logs.getter 
    def get_critical_logs(self):
        return self._critical_logs
    
    execution_logs = RemoteParameter(readonly=True, URL_path='/logs/execution')
    @execution_logs.getter 
    def get_execution_logs(self):
        return self._execution_logs



__all__ = ['RemoteObject', 'StateMachine', 'RemoteObjectDB', 'RemoteSubobject', 'ListHandler', 'RemoteAccessHandler']
