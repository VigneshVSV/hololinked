import typing 
from dataclasses import dataclass, asdict

from ..server.remote_parameters import *
from .thing import Thing
from .properties import Property



class PropertyDescription:
    type : str
    title : str 
    unit : str 
    readOnly : bool
    writeOnly : bool 
    observable : bool

    property_type = {
        String : 'string',
        IPAddress : 'string',
        Integer : 'integer',
        Number : 'number',
        Boolean : 'boolean',
        List : 'array',
        Tuple : 'array',
        Selector : 'object',
        TupleSelector : 'array',
        ClassSelector : 'object',
        Filename : 'string',
        Foldername : 'string',
        Path : 'string',
        TypedList : 'array',
        TypedDict : 'object'
    }

    def build(self, property : Property) -> typing.Dict[str, typing.Any]:
        self.type = self.property_type[property.__class__]
        self.title = property.name
        self.readOnly = property.readonly
        self.writeOnly = False
        self.description = property.doc 
        self.constant = property.constant
        self.default = property.default
        
        if self.type == 'string':
            assert isinstance(property, String)
            self.pattern = property.regex
        
        return asdict(self)



class ActionDescription:
    forms : typing.List[typing.Dict[str, str]]
    input : object 
    output : object 
    safe : bool
    idempotent : bool 
    synchronous : bool 

    def build(self, action : typing.Callable) -> typing.Dict[str, typing.Any]:
        self.safe = True 
        self.idempotent = False 
        self.synchronous = True 
        # self.input = action._remote_info.input_schema 
        return asdict(self)


class EventDescription:
    subscription : str

    def build(self, event):
        return asdict(self)



class VersionInfo:
    """
    https://www.w3.org/TR/wot-thing-description11/#versioninfo
    """
    instance : str 
    model : str


class Link:
    pass 

class Form:
    pass

class SecurityScheme:
    pass 



@dataclass
class ThingDescription:
    """
    This class can generate Thing Description of W3 Web of Things standard. 
    Refer standard - https://www.w3.org/TR/wot-thing-description11
    Refer schema - https://www.w3.org/TR/wot-thing-description11/#thing
    """
    context : typing.Union[typing.List[str], str, typing.Dict[str, str]] 
    type : typing.Optional[typing.Union[str, typing.List[str]]]
    id : str 
    title : str 
    titles : typing.Optional[typing.Dict[str, str]]
    description : str 
    descriptions : typing.Optional[typing.Dict[str, str]]
    version : typing.Optional[VersionInfo]
    created : str 
    modified : str
    support : str 
    base : str 
    properties : typing.List[PropertyDescription]
    actions : typing.List[ActionDescription]
    events : typing.List[EventDescription]
    links : typing.Optional[typing.List[Link]] 
    forms : typing.Optional[typing.List[Form]]
    security : typing.Union[str, typing.List[str]]
    securityDefinitions : SecurityScheme
    
    def build(self, instance : Thing) -> typing.Dict[str, typing.Any]: 
        self.context = "https://www.w3.org/2022/wot/td/v1.1"
        self.id = instance.instance_name
        self.title = instance.__class__.__name__
        self.description = instance.__doc__

        for resource in instance.instance_resources.values():
            if resource.isparameter:
                if resource.obj_name not in self.properties:
                    self.properties[resource.obj_name] = PropertyDescription.build(resource.obj) 
            elif resource.iscallable:
                if resource.obj_name not in self.actions:
                    self.actions[resource.obj_name] = ActionDescription.build(resource.obj)
    
        for event in instance.events:
            self.events[event["name"]] = EventDescription.build(event)
    
        
        
