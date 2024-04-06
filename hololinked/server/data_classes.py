"""
The following is a list of all dataclasses used to store information on the exposed 
resources on the network. These classese are generally not for consumption by the package-end-user. 
"""
import typing
import platform
from enum import Enum
from dataclasses import dataclass, asdict, field, fields

from ..param.parameters import String, Boolean, Tuple, TupleSelector, TypedDict
from .constants import (JSON, USE_OBJECT_NAME, HTTP_METHODS, REGEX, http_methods)
from .utils import get_signature



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
        if True, http request object will be passed as an argument to the callable. 
        The user is warned to not use this generally. 
    argument_schema: JSON, default None
        JSON schema validations for arguments of a callable. Assumption is therefore arguments will be
        JSON complaint. 
    return_value_schema: JSON, default None 
        schema for return value of a callable
    """

    URL_path = String(default=USE_OBJECT_NAME)
    http_method = TupleSelector(default=HTTP_METHODS.POST, objects=http_methods, accept_list=True)
    state = Tuple(default=None, item_type=(Enum, str), allow_None=True, accept_list=True, accept_item=True)
    obj_name = String(default=USE_OBJECT_NAME)
    iscoroutine = Boolean(default=False)
    iscallable = Boolean(default=False)
    isparameter = Boolean(default=False)
    request_as_argument = Boolean(default=False)
    argument_schema = TypedDict(default=None, allow_None=True, key_type=str)
    return_value_schema = TypedDict(default=None, allow_None=True, key_type=str)
 
    def __init__(self, **kwargs) -> None:
        """   
        No full-scale checks for unknown keyword arguments as the class 
        is used by the developer, so please try to be error-proof
        """
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

    def supported_methods(self):
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
    fullpath : str
    instructions : HTTPMethodInstructions
    argument_schema : typing.Optional[JSON]
    request_as_argument : bool = field(default=False)
                                  
    def __init__(self, *, what : str, instance_name : str, fullpath : str, request_as_argument : bool = False,
                argument_schema : typing.Optional[JSON] = None, **instructions) -> None:
        self.what = what 
        self.instance_name = instance_name
        self.fullpath = fullpath
        self.request_as_argument = request_as_argument
        self.argument_schema = argument_schema
        if instructions.get('instructions', None):
            self.instructions = HTTPMethodInstructions(**instructions.get('instructions', None))
        else: 
            self.instructions = HTTPMethodInstructions(**instructions)
    

@dataclass
class RPCResource(SerializableDataclass): 
    """
    Representation of resource used by RPC clients for mapping client method calls, parameter read/writes & events
    to a server resource.

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
    name : str
    qualname : str
    doc : typing.Optional[str]
    top_owner : bool 
    argument_schema : typing.Optional[JSON]

    def __init__(self, *, what : str, instance_name : str, instruction : str, name : str,
                qualname : str, doc : str, top_owner : bool, argument_schema : typing.Optional[JSON] = None) -> None:
        self.what = what 
        self.instance_name = instance_name
        self.instruction = instruction
        self.name = name 
        self.qualname = qualname
        self.doc = doc
        self.top_owner = top_owner
        self.argument_schema = argument_schema

    def get_dunder_attr(self, __dunder_name : str):
        return getattr(self, __dunder_name.strip('_'))


@dataclass
class ServerSentEvent(SerializableDataclass):
    """
    event name and socket address of events to be consumed by clients. 
  
    Attributes
    ----------
    name : str
        name of the event, must be unique
    socket_address : str
        address of the socket
    unique_identifier: str
        unique ZMQ identifier used in PUB-SUB model
    """
    name : str 
    unique_identifier : str
    socket_address : str 
    what : str = field(default="EVENT")


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
        from .remote_object import RemoteSubobject
        assert isinstance(instance, RemoteSubobject), f"got invalid type {type(instance)}"

        self.instance_name = instance.instance_name
        self.inheritance = [class_.__name__ for class_ in instance.__class__.mro()]
        self.classdoc = instance.__class__.__doc__.splitlines() if instance.__class__.__doc__ is not None else None
        self.GUI = instance.GUI
        self.events = instance.events
    
        for instruction, remote_info in instance.instance_resources.items(): 
            if remote_info.iscallable:
                self.methods[instruction] = instance.rpc_resources[instruction].json() 
                self.methods[instruction]["remote_info"] = instance.httpserver_resources[instruction].json() 
                self.methods[instruction]["remote_info"]["http_method"] = list(instance.httpserver_resources[instruction].json()["instructions"].supported_methods())[0]
                # to check - apparently the recursive json() calling does not reach inner depths of a dict, 
                # therefore we call json ourselves
                self.methods[instruction]["owner"] = instance.rpc_resources[instruction].qualname.split('.')[0]
                self.methods[instruction]["owner_instance_name"] = remote_info.bound_obj.instance_name
                self.methods[instruction]["type"] = 'classmethod' if isinstance(remote_info.obj, classmethod) else ''
                self.methods[instruction]["signature"] = get_signature(remote_info.obj)[0]
            elif remote_info.isparameter:
                path_without_RW = instruction.rsplit('/', 1)[0]
                if path_without_RW not in self.parameters:
                    self.parameters[path_without_RW] = self.__class__.parameters.webgui_info(remote_info.obj)[remote_info.obj.name]
                    self.parameters[path_without_RW]["remote_info"] = self.parameters[path_without_RW]["remote_info"].json()
                    self.parameters[path_without_RW]["instruction"] = path_without_RW
                    self.parameters[path_without_RW]["remote_info"]["http_method"] = list(self.httpserver_resources[path_without_RW].json()["instructions"].supported_methods())
                    """
                    The instruction part has to be cleaned up to be called as fullpath. Setting the full path back into 
                    remote_info is not correct because the unbound method is used by multiple instances. 
                    """
                    self.parameters[path_without_RW]["owner_instance_name"] = remote_info.bound_obj.instance_name
        return self