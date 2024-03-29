"""
The following is a list of all dataclasses used to store information on the exposed 
resources on the network
"""
import typing
import platform
from enum import Enum
from dataclasses import dataclass, asdict, field, fields

from hololinked.server.utils import get_signature

from ..param.parameters import String, Boolean, Tuple, TupleSelector, TypedDict
from .constants import (JSON, USE_OBJECT_NAME, HTTP_METHODS, REGEX, http_methods)
from .path_converter import compile_path



class RemoteResourceInfoValidator:
    """
    A validator class for saving remote access related information on a resource. Currently callables (functions, 
    methods and those with__call__ ) and class/instance parameter store this information as their own attribute under 
    the variable ``remote_info``. This class is generally not for consumption by the package-end-user. 
    The information (and the variable) may be deleted later (currently not done) from these objects under ``_prepare_instance()`` 
    in RemoteObject class. 

    Attributes
    ----------

    URL_path : str, default extracted object name 
        the path in the URL under which the object is accesible.
        Must follow url-regex ('[\-a-zA-Z0-9@:%._\/\+~#=]{1,256}') requirement. 
        If not specified, the name of object will be used. Underscores will be converted to dashes 
        for PEP 8 names and capitial letter converted to small letters with a leading dash(-) for camel case names. 
    http_method : str, default POST
        HTTP method under which the object is accessible. Normally GET, POST, PUT, DELETE or PATCH. 
    state : str, default None
        State machine state at which a callable will be executed or attribute/parameter can be 
        written. Does not apply to read-only attributes/parameters. 
    obj_name : str, default extracted object name
        the name of the object which will be supplied to the ``ObjectProxy`` class to populate
        its own namespace. For HTTP clients, HTTP method and URL is important and for object proxies clients, the 
        the obj_name is important. 
    iscoroutine : bool, default False 
        whether the callable should be executed as an async
    iscallable : bool, default False 
        True for a method or function or callable
    isparameter : bool, default False
        True for a parameter
    request_as_argument : bool, default False
        if True, http request object will be passed as a argument to a callable. The user is warned to not use this
        generally. 
    """
    URL_path = String(default=USE_OBJECT_NAME) #, regex=url_regex)
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
        obj : parameter or method
       
        Returns
        -------
        RemoteResource
            dataclass equivalent of this object
        """
        return RemoteResource(
                    state=tuple(self.state) if self.state is not None else None, 
                    obj_name=self.obj_name, iscallable=self.iscallable, iscoroutine=self.iscoroutine,
                    isparameter=self.isparameter, obj=obj, bound_obj=bound_obj) 
        # http method is manually always stored as a tuple


__dataclass_kwargs = dict(frozen=True)
if float('.'.join(platform.python_version().split('.')[0:2])) > 3.10:
    __dataclass_kwargs["slots"] = True


@dataclass(**__dataclass_kwargs)
class RemoteResource:
    """
    This container class is a mirror of ``RemoteResourceInfoValidator``. It is created by the RemoteObject instance and 
    used by the EventLoop methods (for example ``execute_once()``) to access resource metadata instead of directly using 
    ``RemoteResourceInfoValidator`` parameters/attributes. This is because descriptors (used by ``RemoteResourceInfoValidator``) 
    are generally slower. Instances of this dataclass is stored under ``RemoteObject.instance_resources`` dictionary 
    for each parameter & method. Events use similar dataclass with metadata but with much less information. 
    This class is generally not for consumption by the package-end-user. 
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
        Set use_json_method=True in ``serializers.JSONSerializer`` instance and pass the object to the 
        serializer directly to get the JSON.  
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
class HTTPMethodInstructions:
    GET :  typing.Optional[str] = field(default=None)
    POST :  typing.Optional[str] = field(default=None)
    PUT :  typing.Optional[str] = field(default=None)
    DELETE :  typing.Optional[str] = field(default=None)
    PATCH : typing.Optional[str] = field(default=None) 

    def __post_init__(self):
        self.supported_methods()

    def json(self):
        return asdict(self)
    
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
class HTTPResource:
    """
    Representation of the resource used by HTTP server for routing and passing information on
    what to do with which resource - read, write, execute etc. This class is generally not for 
    consumption by the package-end-user. 
    
    Attributes
    ----------

    what : str
        is it a parameter, method or event?
    instance_name : str
        The ``instance_name`` of the remote object which owns the resource. Used by HTTP server to inform 
        the message brokers to send the message to the correct recipient remote object.
    instruction : str
        unique string that identifies the resource, generally made using the URL_path or identical to the URL_path (
        qualified URL path {instance name}/{URL path}).  
        
    """
    what : str 
    instance_name : str 
    fullpath : str
    instructions : HTTPMethodInstructions
    argument_schema : typing.Optional[JSON]
    request_as_argument : bool = field(default=False)
   
    # 'what' can be an 'ATTRIBUTE' or 'CALLABLE' (based on isparameter or iscallable) and 'instruction' 
    # stores the instructions to be sent to the eventloop. 'instance_name' maps the instruction to a particular 
    # instance of RemoteObject
                                
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

    def __getstate__(self):
        return self.json()
    
    def __setstate__(self, values : typing.Dict):
        for key, value in values.items():
            setattr(self, key, value)
    
    def json(self):
        """
        Set use_json_method=True in ``serializers.JSONSerializer`` instance and pass the 
        object to the serializer directly to get the JSON.  
        """
        return  {
            "what" : self.what, 
            "instance_name" : self.instance_name,
            'fullpath' : self.fullpath,
            "instructions" : self.instructions,
            "request_as_argument" : self.request_as_argument
        }
    

    
@dataclass
class RPCResource: 
    """
    Representation of resource used by RPC clients for mapping client method calls, parameter read/writes & events
    to a server resource. This class is generally not for consumption by the package-end-user. 

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

    def json(self):
        """
        Set use_json_method=True in ``serializers.JSONSerializer`` instance and pass the object to the 
        serializer directly to get the JSON.  
        """
        return asdict(self) 

    def get_dunder_attr(self, __dunder_name : str):
        return getattr(self, __dunder_name.strip('_'))

    def __getstate__(self):
        return self.json()
    
    def __setstate__(self, values : typing.Dict):
        for key, value in values.items():
            setattr(self, key, value)


@dataclass
class ServerSentEvent:
    """
    event name and socket address of events to be consumed by clients. 
    This class is generally not for consumption by the package-end-user. 
    
    Attributes
    ----------
    event_name : str
        name of the event, must be unique
    socket_address : str
        address of the socket

    """
    name : str 
    unique_identifier : str
    socket_address : str 
    what : str = field(default="EVENT")

    def json(self):
        return asdict(self)

    def __getstate__(self):
        return self.json()
    
    def __setstate__(self, values : typing.Dict):
        for key, value in values.items():
            setattr(self, key, value)


@dataclass
class FileServerData: 
    what : str 
    directory : str   
    fullpath : str
    path_format : typing.Optional[str] = field( default=None ) 
    path_regex : typing.Optional[typing.Pattern] = field( default = None )
    param_convertors : typing.Optional[typing.Dict] = field( default = None )

    def json(self):
        return asdict(self)
    
    def compile_path(self):
        path_regex, self.path_format, param_convertors = compile_path(self.fullpath)
        if self.path_format == self.fullpath and len(param_convertors) == 0:
            self.path_regex = None 
            self.param_convertors = None
        elif self.path_format != self.fullpath and len(param_convertors) == 0:
            raise RuntimeError(f"Unknown path format found '{self.path_format}' for path '{self.fullpath}', no path converters were created.")
        else:
            self.path_regex = path_regex
            self.param_convertors = param_convertors
    


@dataclass
class GUIResources:
    """
    Encapsulation of all information required to populate hololinked-portal GUI for a remote object.
    This class is generally not for consumption by the package-end-user. 

    Attributes
    ----------
    instance_name : str
        instance name of the ``RemoteObject``
    inheritance : List[str]
        inheritance tree of the ``RemoteObject``
    classdoc : str
        class docstring
    parameters : nested JSON (dictionary)
        list of defined remote paramters and their metadata
    methods : nested JSON (dictionary)
        list of defined remote methods
    events : nested JSON (dictionary)
        list of defined events
    documentation : Dict[str, str]
        documentation files, name and path
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
        super().__init__()

    def json(self): 
        return asdict(self)
    
    def build(self, instance):
        self.instance_name = instance.instance_name,
        self.events = instance.events, 
        self.classdoc = instance.__class__.__doc__.splitlines() if instance.__class__.__doc__ is not None else None, 
        self.inheritance = [class_.__name__ for class_ in instance.__class__.mro()],
        self.GUI = instance.GUI,
    
        
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
                    # if isinstance(remote_info.obj, PlotlyFigure):
                    #     gui_resources.parameters[path_without_RW]['default'] = None
                    #     gui_resources.parameters[path_without_RW]['visualization'] = {
                    #             'type' : 'plotly',
                    #             'plot' : remote_info.obj.__get__(self, type(self)),
                    #             'sources' : remote_info.obj.data_sources,
                    #             'actions' : {
                    #                 remote_info.obj._action_stub.id : remote_info.obj._action_stub
                    #             },
                    #     }
                    # elif isinstance(remote_info.obj, Image):
                    #     gui_resources.parameters[path_without_RW]['default'] = None
                    #     gui_resources.parameters[path_without_RW]['visualization'] = {
                    #         'type' : 'sse-video',
                    #         'sources' : remote_info.obj.data_sources,
                    #         'actions' : {
                    #                 remote_info.obj._action_stub.id : remote_info.obj._action_stub
                    #             },
                    #     }
        return self