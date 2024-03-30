import os 
import typing
from enum import Enum
from ..param.parameterized import Parameterized
from ..server.constants import USE_OBJECT_NAME, HTTP_METHODS
from ..server.remote_parameter import RemoteParameter
from ..server.events import Event

try: 
    import plotly.graph_objects as go
except:
    go = None 

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
        super().__init__(default=default_figure, doc=doc, constant=True, readonly=True, URL_path=URL_path)
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
            raise TypeError(f"figure arguments accepts only plotly.graph_objects.Figure, not type {type(value)}",
                            self)
        return value
        
    @classmethod
    def serialize(cls, value):
        return value.to_json()
    


class Image(VisualizationParameter):

    __slots__ = ['event', 'streamable', '_action_stub', 'data_sources']

    def __init__(self, default : typing.Any = None, *, streamable : bool = True, doc : typing.Optional[str] = None, 
                constant : bool = False, readonly : bool = False, allow_None : bool = False,  
                URL_path : str = USE_OBJECT_NAME, 
                http_method : typing.Tuple[typing.Optional[str], typing.Optional[str]] = (HTTP_METHODS.GET, HTTP_METHODS.PUT), 
                state : typing.Optional[typing.Union[typing.List, typing.Tuple, str, Enum]] = None,
                db_persist : bool = False, db_init : bool = False, db_commit : bool = False, 
                class_member : bool = False, fget : typing.Optional[typing.Callable] = None, 
                fset : typing.Optional[typing.Callable] = None, fdel : typing.Optional[typing.Callable] = None, 
                deepcopy_default : bool = False, per_instance_descriptor : bool = False, 
                precedence : typing.Optional[float] = None) -> None: 
        super().__init__(default, doc=doc, constant=constant, readonly=readonly, allow_None=allow_None, 
                URL_path=URL_path, http_method=http_method, state=state, 
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
            raise TypeError(f"FileServer parameter not a string, but type {type(value)}", self) 
        if not os.path.isdir(value):
            raise ValueError(f"FileServer parameter directory '{value}' not a valid directory", self)
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