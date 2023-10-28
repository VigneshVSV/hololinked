import typing
import os 
from enum import Enum

from ..param.parameterized import Parameter, Parameterized, ClassParameters, raise_TypeError
from ..param.exceptions import raise_ValueError
from .decorators import ScadaInfoValidator
from .constants import GET, HTTP, PROXY, PUT, USE_OBJECT_NAME
from .zmq_message_brokers import Event

try: 
    import plotly.graph_objects as go
except:
    go = None 

__default_parameter_write_method__ = PUT 

__parameter_info__ = [
                'allow_None' , 'class_member', 'constant', 'db_commit', 
                'db_first_load', 'db_memorized', 'deepcopy_default', 'per_instance_descriptor', 
                'default', 'doc', 'metadata', 'name', 'readonly'
                # 'scada_info', 'parameter_type' # descriptor related info is also necessary
            ]



class RemoteParameter(Parameter):

    __slots__ = ['db_persist', 'db_init', 'db_commit', 'scada_info']

    def __init__(self, default: typing.Any = None, *, doc : typing.Optional[str] = None, constant : bool = False, 
                readonly : bool = False, allow_None : bool = False, 
                access_type : typing.Tuple[typing.Optional[str], typing.Optional[str]] = (HTTP, PROXY),
                URL_path : str = USE_OBJECT_NAME, 
                http_method : typing.Tuple[typing.Optional[str], typing.Optional[str]] = (GET, PUT), 
                state : typing.Optional[typing.Union[typing.List, typing.Tuple, str, Enum]] = None,
                db_persist : bool = False, db_init : bool = False, db_commit : bool = False, 
                class_member : bool = False, fget : typing.Optional[typing.Callable] = None, 
                fset : typing.Optional[typing.Callable] = None, fdel : typing.Optional[typing.Callable] = None, 
                deepcopy_default : bool = False, per_instance_descriptor : bool = False, 
                precedence : typing.Optional[float] = None,
            ) -> None:
        """Initialize a new Parameter object and store the supplied attributes:

        default: the owning class's value for the attribute represented
        by this Parameter, which can be overridden in an instance.

        doc: docstring explaining what this parameter represents.

        constant: if true, the Parameter value can be changed only at
        the class level or in a Parameterized constructor call. The
        value is otherwise constant on the Parameterized instance,
        once it has been constructed.

        readonly: if true, the Parameter value cannot ordinarily be
        changed by setting the attribute at the class or instance
        levels at all. The value can still be changed in code by
        temporarily overriding the value of this slot and then
        restoring it, which is useful for reporting values that the
        _user_ should never change but which do change during code
        execution.

        allow_None: if True, None is accepted as a valid value for
        this Parameter, in addition to any other values that are
        allowed. If the default value is defined as None, allow_None
        is set to True automatically.

        db_memorized: if True, every read and write is stored in database 
        and persists instance destruction and creation. 
        
        db_firstload: if True, only the first read is loaded from database.
        further reads and writes not written to database. if db_memorized 
        is True, this value is ignored. 

        optional: some doc 

        remote: set False to avoid exposing the variable for remote read 
        and write

        URL: resource locator under which the attribute is accessible through 
        HTTP. when remote is True and no value is supplied, the variable name 
        is used and underscores and replaced with dash

        read_method: HTTP method for attribute read, default is GET

        write_method: HTTP method for attribute read, default is PUT

        read_time    : some doc

        metadata: store your own JSON compatible metadata for the parameter 
        which gives useful (and modifiable) information about the parameter. 

        label: optional text label to be used when this Parameter is
        shown in a listing. If no label is supplied, the attribute name
        for this parameter in the owning Parameterized object is used.

        per_instance: whether a separate Parameter instance will be
        created for every Parameterized instance. True by default.
        If False, all instances of a Parameterized class will share
        the same Parameter object, including all validation
        attributes (bounds, etc.). See also deep_copy, which is
        conceptually similar but affects the Parameter value rather
        than the Parameter object.

        deep_copy: controls whether the value of this Parameter will
        be deepcopied when a Parameterized object is instantiated (if
        True), or if the single default value will be shared by all
        Parameterized instances (if False). For an immutable Parameter
        value, it is best to leave deep_copy at the default of
        False, so that a user can choose to change the value at the
        Parameterized instance level (affecting only that instance) or
        at the Parameterized class or superclass level (affecting all
        existing and future instances of that class or superclass). For
        a mutable Parameter value, the default of False is also appropriate
        if you want all instances to share the same value state, e.g. if
        they are each simply referring to a single global object like
        a singleton. If instead each Parameterized should have its own
        independently mutable value, deep_copy should be set to
        True, but note that there is then no simple way to change the
        value of this Parameter at the class or superclass level,
        because each instance, once created, will then have an
        independently deepcopied value.

        class_member : To make a ... 

        pickle_default_value: whether the default value should be
        pickled. Usually, you would want the default value to be pickled,
        but there are rare cases where that would not be the case (e.g.
        for file search paths that are specific to a certain system).

        precedence: a numeric value, usually in the range 0.0 to 1.0,
        which allows the order of Parameters in a class to be defined in
        a listing or e.g. in GUI menus. A negative precedence indicates
        a parameter that should be hidden in such listings.

        default, doc, and precedence all default to None, which allows
        inheritance of Parameter slots (attributes) from the owning-class'
        class hierarchy (see ParameterizedMetaclass).
        """

        super().__init__(default=default, doc=doc, constant=constant, readonly=readonly, allow_None=allow_None,
                    per_instance_descriptor=per_instance_descriptor, deepcopy_default=deepcopy_default,
                    class_member=class_member, fget=fget, fset=fset, precedence=precedence)
        self.db_persist = db_persist
        self.db_init    = db_init
        self.db_commit  = db_commit
        if URL_path is not USE_OBJECT_NAME:
            assert URL_path.startswith('/'), "URL path should start with a leading '/'"
        self.scada_info = ScadaInfoValidator(
            access_type = access_type,
            http_method = http_method,
            URL_path    = URL_path,
            state       = state,
            isparameter = True
        )
        
    def _post_slot_set(self, slot : str, old : typing.Any, value : typing.Any) -> None:
        if slot == 'owner' and self.owner is not None:
            if self.scada_info.URL_path == USE_OBJECT_NAME:
                self.scada_info.URL_path = '/' + self.name
            self.scada_info.obj_name = self.name
            # In principle the above could be done when setting name itself however to simplify
            # we do it with owner. So we should always remember order of __set_name__ -> 1) attrib_name, 
            # 2) name and then 3) owner
        super()._post_slot_set(slot, old, value)

    def _post_value_set(self, obj : Parameterized, value : typing.Any) -> None:
        if (self.db_persist or self.db_commit) and hasattr(obj, 'db_engine') and hasattr(obj.db_engine, 'edit_parameter'):
            obj.db_engine.edit_parameter(self, value)
        return super()._post_value_set(obj, value)

    def query(self, info : typing.Union[str, typing.List[str]]) -> typing.Any:
        if info == 'info':
            state = self.__getstate__()
            overloads = state.pop('overloads')
            state["overloads"] = {"custom fset" : repr(overloads["fset"]) , "custom fget" : repr(overloads["fget"])}
            owner_cls = state.pop('owner')
            state["owner"] = repr(owner_cls)
            return state
        elif info in self.__slots__ or info in self.__parent_slots__:
            if info == 'overloads':
                overloads = getattr(self, info)
                return {"custom fset" : repr(overloads["fset"]) , "custom fget" : repr(overloads["fget"])}
            elif info == 'owner':
               return repr(getattr(self, info))
            else:
                return getattr(self, info)
        elif isinstance(info, list):
            requested_info = {}
            for info_ in info: 
                if not isinstance(info_, str):
                    raise AttributeError("Invalid format for information : {} found in list of requested information. Only string is allowed".format(type(info_)))
                requested_info[info_] = getattr(self, info_)
            return requested_info
        else:
            raise AttributeError("requested information {} not found in parameter {}".format(info, self.name))


    
class VisualizationParameter(RemoteParameter):
    # type shield from RemoteParameter
    pass 



class PlotlyFigure(VisualizationParameter):

    __slots__ = ['data_sources', 'update_event_name', 'refresh_interval', 'polled',
                 '_action_stub']

    def __init__(self, default_figure, *, 
                data_sources : typing.Dict[str, typing.Union[RemoteParameter, typing.Any]],  
                polled : bool = False, refresh_interval : typing.Optional[int] = None, 
                update_event_name : typing.Optional[str] = None, doc: typing.Union[str, None] = None, 
                URL_path : str = USE_OBJECT_NAME) -> None:
        super().__init__(default=default_figure, doc=doc, constant=True, readonly=True, URL_path=URL_path, 
                        http_method=(GET, PUT))
        self.data_sources = data_sources    
        self.refresh_interval = refresh_interval
        self.update_event_name = update_event_name
        self.polled = polled

    def _post_slot_set(self, slot : str, old : typing.Any, value : typing.Any) -> None:
        if slot == 'owner' and self.owner is not None:
            from ..webdashboard import RepeatedRequests, AxiosRequestConfig, EventSource
            if self.polled:
                if self.refresh_interval is None:
                    raise ValueError(f'for PlotlyFigure {self.name}, set refresh interval (ms) since its polled')
                request = AxiosRequestConfig(
                    url=f'/parameters?{"&".join(f"{key}={value}" for key, value in self.data_sources.items())}',   
                    # Here is where graphQL is very useful
                    method='get'
                ) 
                self._action_stub = RepeatedRequests(
                    requests=request,
                    interval=self.refresh_interval, 
                )
            elif self.update_event_name: 
                if not isinstance(self.update_event_name, str):
                    raise ValueError(f'update_event_name for PlotlyFigure {self.name} must be a string')
                request = EventSource(f'/event/{self.update_event_name}')
                self._action_stub = request 
            else:
                pass 

            for field, source in self.data_sources.items():
                if isinstance(source, RemoteParameter):
                    if isinstance(source, EventSource):
                        raise RuntimeError("Parameter field not supported for event source, give str")
                    self.data_sources[field] = request.response[source.name]
                elif isinstance(source, str):
                    if isinstance(source, RepeatedRequests) and source not in self.owner.parameters: # should be in remote parameters, not just parameter
                        raise ValueError(f'data_sources must be a string or RemoteParameter, type {type(source)} has been found')     
                    self.data_sources[field] = request.response[source]
                else: 
                    raise ValueError(f'given source {source} invalid. Specify str for events or Parameter')
                              
        return super()._post_slot_set(slot, old, value)

    def validate_and_adapt(self, value : typing.Any) -> typing.Any:
        if self.allow_None and value is None:
            return
        if not go:
            raise ImportError("plotly was not found/imported, install plotly to suport PlotlyFigure paramater")
        if not isinstance(value, go.Figure):
            raise_TypeError(f"figure arguments accepts only plotly.graph_objects.Figure, not type {type(value)}",
                            self)
        return value
        
    @classmethod
    def serialize(cls, value):
        return value.to_json()
    


class Image(VisualizationParameter):

    __slots__ = ['event', 'streamable', '_action_stub', 'data_sources']

    def __init__(self, default : typing.Any = None, *, streamable : bool = True, doc : typing.Optional[str] = None, 
                constant : bool = False, readonly : bool = False, allow_None : bool = False,  
                access_type : typing.Tuple[typing.Optional[str], typing.Optional[str]] = (HTTP, PROXY),
                URL_path : str = USE_OBJECT_NAME, 
                http_method : typing.Tuple[typing.Optional[str], typing.Optional[str]] = (GET, PUT), 
                state : typing.Optional[typing.Union[typing.List, typing.Tuple, str, Enum]] = None,
                db_persist : bool = False, db_init : bool = False, db_commit : bool = False, 
                class_member : bool = False, fget : typing.Optional[typing.Callable] = None, 
                fset : typing.Optional[typing.Callable] = None, fdel : typing.Optional[typing.Callable] = None, 
                deepcopy_default : bool = False, per_instance_descriptor : bool = False, 
                precedence : typing.Optional[float] = None) -> None: 
        super().__init__(default, doc=doc, constant=constant, readonly=readonly, allow_None=allow_None, 
                access_type=access_type, URL_path=URL_path, http_method=http_method, state=state, 
                db_persist=db_persist, db_init=db_init, db_commit=db_commit, class_member=class_member, 
                fget=fget, fset=fset, fdel=fdel, deepcopy_default=deepcopy_default, 
                per_instance_descriptor=per_instance_descriptor, precedence=precedence)
        self.streamable = streamable
    
    def __set_name__(self, owner : typing.Any, attrib_name : str) -> None:
        super().__set_name__(owner, attrib_name)
        self.event = Event(attrib_name)
        
    def _post_value_set(self, obj : Parameterized, value : typing.Any) -> None:
        super()._post_value_set(obj, value)
        if value is not None:
            print(f"pushing event {value[0:100]}")
            self.event.push(value, serialize=False)

    def _post_slot_set(self, slot : str, old : typing.Any, value : typing.Any) -> None:
        if slot == 'owner' and self.owner is not None:
            from ..webdashboard import SSEVideoSource
            request = SSEVideoSource(f'/event/image')
            self._action_stub = request 
            self.data_sources = request.response
        return super()._post_slot_set(slot, old, value)
                



class FileServer(RemoteParameter):

    __slots__ = ['directory']

    def __init__(self, directory : str, *, doc : typing.Optional[str] = None, URL_path : str = USE_OBJECT_NAME, 
                class_member: bool = False, per_instance_descriptor: bool = False) -> None:
        self.directory = self.validate_and_adapt_directory(directory)
        super().__init__(default=self.load_files(self.directory), doc=doc, URL_path=URL_path, constant=True,
                        class_member=class_member, per_instance_descriptor=per_instance_descriptor)
    
    def validate_and_adapt_directory(self, value : str):
        if not isinstance(value, str):
            raise_TypeError(f"FileServer parameter not a string, but type {type(value)}", self) 
        if not os.path.isdir(value):
            raise_ValueError(f"FileServer parameter directory '{value}' not a valid directory", self)
        if not value.endswith('\\'):
            value += '\\'
        return value 

    def load_files(self, directory : str):
        return [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]

class DocumentationFolder(FileServer):

    def __init__(self, directory : str, *, doc : typing.Optional[str] = None, URL_path : str = '/documentation', 
                class_member: bool = False, per_instance_descriptor: bool = False) -> None:
        super().__init__(directory=directory, doc=doc, URL_path=URL_path,
                        class_member=class_member, per_instance_descriptor=per_instance_descriptor)



class RemoteClassParameters(ClassParameters):

    @property
    def db_persisting_objects(self):
        try:
            return getattr(self.owner_cls, f'_{self.owner_cls.__name__}_db_persisting_remote_params')
        except AttributeError: 
            paramdict = self.remote_objects
            db_persisting_remote_params = {}
            for name, desc in paramdict.items():
                if desc.db_persist:
                    db_persisting_remote_params[name] = desc
            setattr(self.owner_cls, f'_{self.owner_cls.__name__}_db_persisting_remote_params', db_persisting_remote_params)
        return getattr(self.owner_cls, f'_{self.owner_cls.__name__}_db_persisting_remote_params')

    @property
    def db_init_objects(self) -> typing.Dict[str, RemoteParameter]:
        try:
            return getattr(self.owner_cls, f'_{self.owner_cls.__name__}_db_init_remote_params')
        except AttributeError: 
            paramdict = self.remote_objects
            init_load_params = {}
            for name, desc in paramdict.items():
                if desc.db_init or desc.db_persist:
                    init_load_params[name] = desc
            setattr(self.owner_cls, f'_{self.owner_cls.__name__}_db_init_remote_params', init_load_params)
        return getattr(self.owner_cls, f'_{self.owner_cls.__name__}_db_init_remote_params')
        
    @property
    def remote_objects(self) -> typing.Dict[str, RemoteParameter]:
        try:
            return getattr(self.owner_cls, f'_{self.owner_cls.__name__}_remote_params')
        except AttributeError: 
            paramdict = super().descriptors
            remote_params = {}
            for name, desc in paramdict.items():
                if isinstance(desc, RemoteParameter):
                    remote_params[name] = desc
            setattr(self.owner_cls, f'_{self.owner_cls.__name__}_remote_params', remote_params)
        return getattr(self.owner_cls, f'_{self.owner_cls.__name__}_remote_params')

    def webgui_info(self, for_remote_params : typing.Union[RemoteParameter, typing.Dict[str, RemoteParameter], None] = None):
        info = {}
        if isinstance(for_remote_params, dict):
            objects = for_remote_params 
        elif isinstance(for_remote_params, RemoteParameter):
            objects = { for_remote_params.name : for_remote_params } 
        else:
            objects = self.remote_objects
        for param in objects.values():
            state = param.__getstate__()
            info[param.name] = dict(
                scada_info = state.get("scada_info", None).create_dataclass(),
                type = param.__class__.__name__,
                owner = param.owner.__name__
            )
            for field in __parameter_info__:
                info[param.name][field] = state.get(field, None) 
        return info 

    @property
    def visualization_parameters(self):
        try:
            return getattr(self.owner_cls, f'_{self.owner_cls.__name__}_visualization_params')
        except AttributeError: 
            paramdict = super().descriptors
            visual_params = {}
            for name, desc in paramdict.items():
                if isinstance(desc, VisualizationParameter):
                    visual_params[name] = desc
            setattr(self.owner_cls, f'_{self.owner_cls.__name__}_visualization_params', visual_params)
        return getattr(self.owner_cls, f'_{self.owner_cls.__name__}_visualization_params')




class batch_db_commit:

    def __enter__(self):
        pass 
        
    def __exit__(self):
        pass 


  
class ReactApp: 
    pass 



__all__ = ['RemoteParameter']