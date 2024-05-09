"""
The following is a list of all dataclasses used to store information on the exposed 
resources on the network. These classese are generally not for consumption by the package-end-user. 
"""
import typing
import platform
import inspect
from enum import Enum
from dataclasses import dataclass, asdict, field, fields
from types import FunctionType, MethodType

from ..param.parameters import (String, Boolean, Tuple, TupleSelector, 
                        TypedDict, ClassSelector, Parameter)
from .constants import (JSON, USE_OBJECT_NAME, UNSPECIFIED, 
                    HTTP_METHODS, REGEX, ResourceTypes, http_methods)
from .utils import get_signature, getattr_without_descriptor_read



class RemoteResourceInfoValidator:
    """
    A validator class for saving remote access related information on a resource. Currently callables (functions, 
    methods and those with__call__) and class/instance parameter store this information as their own attribute under 
    the variable ``_remote_info``. This is later split into information suitable for HTTP server, RPC client & ``EventLoop``. 
    
    Attributes
    ----------

    URL_path : str, default - extracted object name 
        the path in the URL under which the object is accesible.
        Must follow url-regex ('[\-a-zA-Z0-9@:%._\/\+~#=]{1,256}') requirement. 
        If not specified, the name of object will be used. Underscores will be converted to dashes 
        for PEP 8 names. 
    http_method : str, default POST
        HTTP request method under which the object is accessible. GET, POST, PUT, DELETE or PATCH are supported. 
    state : str, default None
        State machine state at which a callable will be executed or attribute/parameter can be 
        written. Does not apply to read-only attributes/parameters. 
    obj_name : str, default - extracted object name
        the name of the object which will be supplied to the ``ObjectProxy`` class to populate
        its own namespace. For HTTP clients, HTTP method and URL path is important and for 
        object proxies clients, the obj_name is important. 
    iscoroutine : bool, default False 
        whether the callable should be awaited
    iscallable : bool, default False 
        True for a method or function or callable
    isparameter : bool, default False
        True for a parameter
    request_as_argument : bool, default False
        if True, http/RPC request object will be passed as an argument to the callable. 
        The user is warned to not use this generally. 
    argument_schema: JSON, default None
        JSON schema validations for arguments of a callable. Assumption is therefore arguments will be JSON complaint. 
    return_value_schema: JSON, default None 
        schema for return value of a callable
    """

    URL_path = String(default=USE_OBJECT_NAME,
                    doc="the path in the URL under which the object is accesible.") # type: str
    http_method = TupleSelector(default=HTTP_METHODS.POST, objects=http_methods, accept_list=True,
                    doc="HTTP request method under which the object is accessible. GET, POST, PUT, DELETE or PATCH are supported.") # typing.Tuple[str]
    state = Tuple(default=None, item_type=(Enum, str), allow_None=True, accept_list=True, accept_item=True,
                    doc="State machine state at which a callable will be executed or attribute/parameter can be written.") # type: typing.Union[Enum, str]
    obj = ClassSelector(default=None, allow_None=True, class_=(FunctionType, classmethod, Parameter, MethodType),
                    doc="the unbound object like the unbound method")
    obj_name = String(default=USE_OBJECT_NAME, 
                    doc="the name of the object which will be supplied to the ``ObjectProxy`` class to populate its own namespace.") # type: str
    iscoroutine = Boolean(default=False,
                    doc="whether the callable should be awaited") # type: bool
    iscallable = Boolean(default=False,
                    doc="True for a method or function or callable") # type: bool
    isparameter = Boolean(default=False,
                    doc="True for a parameter") # type: bool
    request_as_argument = Boolean(default=False,
                    doc="if True, http/RPC request object will be passed as an argument to the callable.") # type: bool
    argument_schema = TypedDict(default=None, allow_None=True, key_type=str,
                    doc="JSON schema validations for arguments of a callable")
    return_value_schema = TypedDict(default=None, allow_None=True, key_type=str,
                    doc="schema for return value of a callable")
 
    def __init__(self, **kwargs) -> None:
        """   
        No full-scale checks for unknown keyword arguments as the class 
        is used by the developer, so please try to be error-proof
        """
        if kwargs.get('URL_path', None) is not None:
            if not isinstance(kwargs['URL_path'], str): 
                raise TypeError(f"URL path must be a string. Given type {type(kwargs['URL_path'])}")
            if kwargs["URL_path"] != USE_OBJECT_NAME and not kwargs["URL_path"].startswith('/'):
                raise ValueError(f"URL path must start with '/'. Given value {kwargs['URL_path']}")
        for key, value in kwargs.items(): 
            setattr(self, key, value)
    
    def to_dataclass(self, obj : typing.Any = None, bound_obj : typing.Any = None) -> "RemoteResource":
        """
        For a plain, faster and uncomplicated access, a dataclass in created & used by the
        event loop. 
        
        Parameters
        ----------
        obj : Union[RemoteParameter | Callable]  
            parameter or method

        bound_obj : owner instance
            ``RemoteObject`` instance
       
        Returns
        -------
        RemoteResource
            dataclass equivalent of this object
        """
        return RemoteResource(
                    state=tuple(self.state) if self.state is not None else None, 
                    obj_name=self.obj_name, iscallable=self.iscallable, iscoroutine=self.iscoroutine,
                    isparameter=self.isparameter, obj=obj, bound_obj=bound_obj
                ) 
        # http method is manually always stored as a tuple


class SerializableDataclass:
    """
    Presents uniform serialization for serializers using getstate and setstate and json 
    serialization.
    """

    def json(self):
        return asdict(self)

    def __getstate__(self):
        return self.json()
    
    def __setstate__(self, values : typing.Dict):
        for key, value in values.items():
            setattr(self, key, value)



__dataclass_kwargs = dict(frozen=True)
if float('.'.join(platform.python_version().split('.')[0:2])) >= 3.11:
    __dataclass_kwargs["slots"] = True

@dataclass(**__dataclass_kwargs)
class RemoteResource(SerializableDataclass):
    """
    This container class is used by the ``EventLoop`` methods (for example ``execute_once()``) to access resource 
    metadata instead of directly using ``RemoteResourceInfoValidator``. Instances of this dataclass is stored under 
    ``RemoteObject.instance_resources`` dictionary for each parameter & method. Events use similar dataclass with 
    metadata but with much less information. 

    Attributes
    ----------
    state : str
        State machine state at which a callable will be executed or attribute/parameter can be 
        written. Does not apply to read-only attributes/parameters. 
    obj_name : str, default - extracted object name
        the name of the object which will be supplied to the ``ObjectProxy`` class to populate
        its own namespace. For HTTP clients, HTTP method and URL path is important and for 
        object proxies clients, the obj_name is important. 
    iscoroutine : bool
        whether the callable should be awaited
    iscallable : bool
        True for a method or function or callable
    isparameter : bool
        True for a parameter
    obj : Union[RemoteParameter | Callable]  
            parameter or method
    bound_obj : owner instance
        ``RemoteObject`` instance
    """
    state : typing.Optional[typing.Union[typing.Tuple, str]] 
    obj_name : str 
    iscallable : bool 
    iscoroutine : bool
    isparameter : bool
    obj : typing.Any
    bound_obj : typing.Any
  
    def json(self):
        """
        return this object as a JSON serializable dictionary
        """
        # try:
        #     return self._json # accessing dynamic attr from frozen object
        # except AttributeError: # always causes attribute error when slots are True
        json_dict = {}
        for field in fields(self):
            if field.name != 'obj' and field.name != 'bound_obj':
                json_dict[field.name] = getattr(self, field.name)
        # object.__setattr__(self, '_json', json_dict) # because object is frozen - used to work, but not now 
        return json_dict                 
    

@dataclass
class HTTPMethodInstructions(SerializableDataclass):
    """
    contains a map of unique strings that identifies the resource operation for each HTTP method, thus acting as 
    instructions to be passed to the RPC server. The unique strings are generally made using the URL_path. 
    """
    GET :  typing.Optional[str] = field(default=None)
    POST :  typing.Optional[str] = field(default=None)
    PUT :  typing.Optional[str] = field(default=None)
    DELETE :  typing.Optional[str] = field(default=None)
    PATCH : typing.Optional[str] = field(default=None) 

    def __post_init__(self):
        self.supported_methods()

    def supported_methods(self): # can be a property
        try: 
            return self._supported_methods
        except: 
            self._supported_methods = []
            for method in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                if isinstance(self.__dict__[method], str):
                    self._supported_methods.append(method)
            return self._supported_methods
    
    def __contains__(self, value):
        return value in self._supported_methods


@dataclass
class HTTPResource(SerializableDataclass):
    """
    Representation of the resource used by HTTP server for routing and passing information to RPC server on
    "what to do with which resource belonging to which remote object? - read, write, execute?". 
    
    Attributes
    ----------

    what : str
        is it a parameter, method or event?
    instance_name : str
        The ``instance_name`` of the remote object which owns the resource. Used by HTTP server to inform 
        the message brokers to send the instruction to the correct recipient remote object.
    fullpath : str
        URL full path used for routing
    instructions : HTTPMethodInstructions
        unique string that identifies the resource operation for each HTTP method, generally made using the URL_path 
        (qualified URL path {instance name}/{URL path}).  
    argument_schema : JSON
        argument schema of the method for validation before passing over the instruction to the RPC server. 
    request_as_argument: bool
        pass the request as a argument to the callable. For HTTP server ``tornado.web.HTTPServerRequest`` will be passed. 
    """
    what : str 
    instance_name : str 
    obj_name : str
    fullpath : str
    instructions : HTTPMethodInstructions
    argument_schema : typing.Optional[JSON]
    return_value_schema : typing.Optional[JSON]
    request_as_argument : bool = field(default=False)
                                  
    def __init__(self, *, what : str, instance_name : str, obj_name : str, fullpath : str, 
                request_as_argument : bool = False, argument_schema : typing.Optional[JSON] = None, 
                return_value_schema : typing.Optional[JSON] = None, **instructions) -> None:
        self.what = what 
        self.instance_name = instance_name
        self.obj_name = obj_name
        self.fullpath = fullpath
        self.request_as_argument = request_as_argument
        self.argument_schema = argument_schema
        self.return_value_schema = return_value_schema
        if instructions.get('instructions', None):
            self.instructions = HTTPMethodInstructions(**instructions.get('instructions', None))
        else: 
            self.instructions = HTTPMethodInstructions(**instructions)
    

@dataclass
class RPCResource(SerializableDataclass): 
    """
    Representation of resource used by RPC clients for mapping client method calls, parameter read/writes & events
    to a server resource. Used to dynamically populate the ``ObjectProxy``

    Attributes
    ----------

    what : str
        is it a parameter, method or event?
    instance_name : str
        The ``instance_name`` of the remote object which owns the resource. Used by RPC client to inform 
        message brokers to send the message to the correct recipient.
    instruction : str
        unique string that identifies the resource, generally made using the URL_path. Although URL path is a HTTP
        concept, it is still used as a unique identifier. 
    name : str
        the name of the resource (__name__)
    qualname : str
        the qualified name of the resource (__qualname__) 
    doc : str
        the docstring of the resource
    argument_schema : JSON
        argument schema of the method for validation before passing over the instruction to the RPC server. 
    """
    what : str 
    instance_name : str 
    instruction : str
    obj_name : str
    qualname : str
    doc : typing.Optional[str]
    top_owner : bool 
    argument_schema : typing.Optional[JSON]
    return_value_schema : typing.Optional[JSON]
    request_as_argument : bool = field(default=False)

    def __init__(self, *, what : str, instance_name : str, instruction : str, obj_name : str,
                qualname : str, doc : str, top_owner : bool, argument_schema : typing.Optional[JSON] = None,
                return_value_schema : typing.Optional[JSON] = None, request_as_argument : bool = False) -> None:
        self.what = what 
        self.instance_name = instance_name
        self.instruction = instruction
        self.obj_name = obj_name 
        self.qualname = qualname
        self.doc = doc
        self.top_owner = top_owner
        self.argument_schema = argument_schema
        self.return_value_schema = return_value_schema
        self.request_as_argument = request_as_argument

    def get_dunder_attr(self, __dunder_name : str):
        name = __dunder_name.strip('_')
        name = 'obj_name' if name == 'name' else name
        return getattr(self, name)


@dataclass
class ServerSentEvent(SerializableDataclass):
    """
    event name and socket address of events to be consumed by clients. 
  
    Attributes
    ----------
    name : str
        name of the event, must be unique
    obj_name: str
        name of the event variable used to populate the RPC client
    socket_address : str
        address of the socket
    unique_identifier: str
        unique ZMQ identifier used in PUB-SUB model
    what: str, default EVENT
        is it a parameter, method or event?
    """
    name : str
    obj_name : str 
    unique_identifier : str
    socket_address : str = field(default=UNSPECIFIED)
    what : str = field(default=ResourceTypes.EVENT)


@dataclass
class GUIResources(SerializableDataclass):
    """
    Encapsulation of all information required to populate hololinked-portal GUI for a remote object.
   
    Attributes
    ----------
    instance_name : str
        instance name of the ``RemoteObject``
    inheritance : List[str]
        inheritance tree of the ``RemoteObject``
    classdoc : str
        class docstring
    parameters : nested JSON (dictionary)
        defined remote parameters and their metadata
    methods : nested JSON (dictionary)
        defined remote methods
    events : nested JSON (dictionary)
        defined events
    documentation : Dict[str, str]
        documentation files, name as key and path as value
    GUI : nested JSON (dictionary)
        generated from ``hololinked.webdashboard.ReactApp``, a GUI can be shown under 'default GUI' tab in the portal
    """
    instance_name : str
    inheritance : typing.List[str]
    classdoc : typing.Optional[typing.List[str]]
    parameters : typing.Dict[str, typing.Any] = field(default_factory=dict)
    methods : typing.Dict[str, typing.Any] = field(default_factory=dict)
    events : typing.Dict[str, typing.Any] = field(default_factory=dict)
    documentation : typing.Optional[typing.Dict[str, typing.Any]] = field(default=None) 
    GUI : typing.Optional[typing.Dict] = field(default=None)

    def __init__(self):
        """
        initialize first, then call build method.  
        """
        super(SerializableDataclass, self).__init__()

    def build(self, instance):
        from .remote_object import RemoteObject
        assert isinstance(instance, RemoteObject), f"got invalid type {type(instance)}"

        self.instance_name = instance.instance_name
        self.inheritance = [class_.__name__ for class_ in instance.__class__.mro()]
        self.classdoc = instance.__class__.__doc__.splitlines() if instance.__class__.__doc__ is not None else None
        self.GUI = instance.GUI
        self.events = {
            event._unique_identifier.decode() : dict(
                name = event.name,
                instruction = event._unique_identifier.decode(),
                owner = event.owner.__class__.__name__,
                owner_instance_name =  event.owner.instance_name,
                address = instance.event_publisher.socket_address
            ) for event in instance.event_publisher.events
        }
        self.methods = dict()
        self.parameters = dict()
    
        for instruction, remote_info in instance.instance_resources.items(): 
            if remote_info.iscallable:
                try:
                    self.methods[instruction] = instance.rpc_resources[instruction].json() 
                    self.methods[instruction]["remote_info"] = instance.httpserver_resources[instruction].json() 
                    self.methods[instruction]["remote_info"]["http_method"] = instance.httpserver_resources[instruction].instructions.supported_methods()
                    # to check - apparently the recursive json() calling does not reach inner depths of a dict, 
                    # therefore we call json ourselves
                    self.methods[instruction]["owner"] = instance.rpc_resources[instruction].qualname.split('.')[0]
                    self.methods[instruction]["owner_instance_name"] = remote_info.bound_obj.instance_name
                    self.methods[instruction]["type"] = 'classmethod' if isinstance(remote_info.obj, classmethod) else ''
                    self.methods[instruction]["signature"] = get_signature(remote_info.obj)[0]
                except KeyError:
                    pass
            elif remote_info.isparameter:
                path_without_RW = instruction.rsplit('/', 1)[0]
                if path_without_RW not in self.parameters:
                    self.parameters[path_without_RW] = instance.__class__.parameters.webgui_info(remote_info.obj)[remote_info.obj.name]
                    self.parameters[path_without_RW]["remote_info"] = self.parameters[path_without_RW]["remote_info"].json()
                    self.parameters[path_without_RW]["instruction"] = path_without_RW
                    self.parameters[path_without_RW]["remote_info"]["http_method"] = instance.httpserver_resources[path_without_RW].instructions.supported_methods()
                    """
                    The instruction part has to be cleaned up to be called as fullpath. Setting the full path back into 
                    remote_info is not correct because the unbound method is used by multiple instances. 
                    """
                    self.parameters[path_without_RW]["owner_instance_name"] = remote_info.bound_obj.instance_name
        return self
    


def get_organised_resources(instance):
    """
    organise the exposed attributes, methods and events into the dataclasses defined above
    so that the specific servers and event loop can use them. 
    """
    from .remote_object import RemoteObject
    from .events import Event
    from .remote_parameter import RemoteParameter

    assert isinstance(instance, RemoteObject), f"got invalid type {type(instance)}"

    httpserver_resources = dict() # type: typing.Dict[str, HTTPResource]
    # The following dict will be given to the object proxy client
    rpc_resources = dict() # type: typing.Dict[str, RPCResource]
    # The following dict will be used by the event loop
    instance_resources = dict() # type: typing.Dict[str, RemoteResource] 
    # create URL prefix
    if instance._owner is not None: 
        instance._full_URL_path_prefix = f'{instance._owner._full_URL_path_prefix}/{instance.instance_name}' 
    else:
        instance._full_URL_path_prefix = f'/{instance.instance_name}'
    
    # First add methods and callables
    # Parameters
    for parameter in instance.parameters.descriptors.values():
        if isinstance(parameter, RemoteParameter) and hasattr(parameter, '_remote_info') and parameter._remote_info is not None: 
            if not isinstance(parameter._remote_info, RemoteResourceInfoValidator): 
                raise TypeError("instance member {} has unknown sub-member 'scada_info' of type {}.".format(
                            parameter, type(parameter._remote_info))) 
                # above condition is just a gaurd in case somebody does some unpredictable patching activities
            remote_info = parameter._remote_info
            fullpath = f"{instance._full_URL_path_prefix}{remote_info.URL_path}"
            read_http_method, write_http_method = remote_info.http_method
                
            httpserver_resources[fullpath] = HTTPResource(
                                                what=ResourceTypes.PARAMETER, 
                                                instance_name=instance._owner.instance_name if instance._owner is not None else instance.instance_name,
                                                obj_name=remote_info.obj_name,
                                                fullpath=fullpath,
                                                request_as_argument=False,
                                                argument_schema=remote_info.argument_schema,
                                                return_value_schema=remote_info.return_value_schema,
                                                **{ 
                                                    read_http_method : f"{fullpath}/read",
                                                    write_http_method : f"{fullpath}/write"
                                                },
                                            )
            rpc_resources[fullpath] = RPCResource(
                            what=ResourceTypes.PARAMETER, 
                            instance_name=instance._owner.instance_name if instance._owner is not None else instance.instance_name, 
                            instruction=fullpath, 
                            doc=parameter.__doc__, 
                            obj_name=remote_info.obj_name,
                            qualname=instance.__class__.__name__ + '.' + remote_info.obj_name,
                            # qualname is not correct probably, does not respect inheritance
                            top_owner=instance._owner is None,
                            argument_schema=remote_info.argument_schema,
                            return_value_schema=remote_info.return_value_schema
                        ) 
            data_cls = remote_info.to_dataclass(obj=parameter, bound_obj=instance) 
            instance_resources[f"{fullpath}/read"] = data_cls
            instance_resources[f"{fullpath}/write"] = data_cls  
            # instance_resources[f"{fullpath}/delete"] = data_cls  
    # Methods
    for name, resource in inspect._getmembers(instance, inspect.ismethod, getattr_without_descriptor_read): 
        if hasattr(resource, '_remote_info'):
            if not isinstance(resource._remote_info, RemoteResourceInfoValidator):
                raise TypeError("instance member {} has unknown sub-member '_remote_info' of type {}.".format(
                            resource, type(resource._remote_info))) 
            remote_info = resource._remote_info
            # methods are already bound
            assert remote_info.iscallable, ("remote info from inspect.ismethod is not a callable",
                                "logic error - visit https://github.com/VigneshVSV/hololinked/issues to report")
            if len(remote_info.http_method) > 1:
                raise ValueError(f"methods support only one HTTP method at the moment. Given number of methods : {len(remote_info.http_method)}.")
            fullpath = f"{instance._full_URL_path_prefix}{remote_info.URL_path}" 
            instruction = f"{fullpath}/{remote_info.http_method[0]}"
            httpserver_resources[instruction] = HTTPResource(
                                        what=ResourceTypes.CALLABLE,
                                        instance_name=instance._owner.instance_name if instance._owner is not None else instance.instance_name,
                                        obj_name=remote_info.obj_name,
                                        fullpath=fullpath,
                                        request_as_argument=remote_info.request_as_argument,
                                        argument_schema=remote_info.argument_schema,
                                        return_value_schema=remote_info.return_value_schema,
                                        **{ remote_info.http_method[0] : instruction },
                                    )
            rpc_resources[instruction] = RPCResource(
                                            what=ResourceTypes.CALLABLE,
                                            instance_name=instance._owner.instance_name if instance._owner is not None else instance.instance_name,
                                            instruction=instruction,                                                                                                                                                                                        
                                            obj_name=getattr(resource, '__name__'),
                                            qualname=getattr(resource, '__qualname__'), 
                                            doc=getattr(resource, '__doc__'),
                                            top_owner=instance._owner is None,
                                            argument_schema=remote_info.argument_schema,
                                            return_value_schema=remote_info.return_value_schema,
                                            request_as_argument=remote_info.request_as_argument
                                        )
            instance_resources[instruction] = remote_info.to_dataclass(obj=resource, bound_obj=instance) 
    # Events
    for name, resource in inspect._getmembers(instance, lambda o : isinstance(o, Event), getattr_without_descriptor_read):
        assert isinstance(resource, Event), ("remote object event query from inspect.ismethod is not an Event",
                                    "logic error - visit https://github.com/VigneshVSV/hololinked/issues to report")
        # above assertion is only a typing convenience
        resource._owner = instance
        fullpath = f"{instance._full_URL_path_prefix}{resource.URL_path}"
        resource._unique_identifier = bytes(fullpath, encoding='utf-8')
        data_cls = ServerSentEvent(
                            name=resource.name,
                            obj_name=name,
                            what=ResourceTypes.EVENT,
                            unique_identifier=f"{instance._full_URL_path_prefix}{resource.URL_path}",
                        )
        resource._remote_info = data_cls
        httpserver_resources[fullpath] = data_cls
        rpc_resources[fullpath] = data_cls
    # Other objects
    for name, resource in inspect._getmembers(instance, lambda o : isinstance(o, RemoteObject), getattr_without_descriptor_read):
        if name == '_owner':
            continue
        assert isinstance(resource, RemoteObject), ("remote object children query from inspect.ismethod is not a RemoteObject",
                                    "logic error - visit https://github.com/VigneshVSV/hololinked/issues to report")
        # above assertion is only a typing convenience
        resource._owner = instance      
        httpserver_resources.update(resource.httpserver_resources)
        # rpc_resources.update(resource.rpc_resources)
        instance_resources.update(resource.instance_resources)
   
    # The above for-loops can be used only once, the division is only for readability
    # following are in _internal_fixed_attributes - allowed to set only once
    return rpc_resources, httpserver_resources, instance_resources    




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