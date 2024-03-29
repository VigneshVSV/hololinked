import typing 
from dataclasses import dataclass, asdict

from ..server.remote_parameters import *
from ..server.constants import JSONSerializable
from .thing import Thing
from .properties import Property


@dataclass
class Schema:
    """
    Base dataclass for all WoT schema; Implements a custom asdict method which replaces dataclasses' asdict 
    utility function
    """

    def asdict(self):
        self_dict = dict()
        for field, value in self.__dataclass_fields__.items():    
            if getattr(self, field, NotImplemented) is NotImplemented:
                continue
            self_dict[field] = getattr(self, field)
        return self_dict
    

@dataclass
class InteractionAffordance(Schema):
    title : str 
    titles : typing.Optional[typing.Dict[str, str]]
    description : str
    descriptions : typing.Optional[typing.Dict[str, str]] 
  
    def __init__(self):
        super().__init__()


@dataclass
class PropertyAffordance(InteractionAffordance):
    type : str
    readOnly : bool
    writeOnly : bool
    constant : bool
    default : typing.Optional[typing.Any] 
    observable : typing.Optional[bool]
    unit : typing.Optional[str]

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

    def __init__(self):
        super().__init__()

    def build(self, property : Property) -> typing.Dict[str, typing.Any]:
        self.type = self.property_type[property.__class__]
        self.title = property.name
        self.readOnly = property.readonly
        self.writeOnly = False
        self.description = property.doc 
        self.constant = property.constant
        if property.overloads["fget"] is None:
            self.default = property.default
        if property.metadata and property.metadata.get("unit", None) is not None:
            self.unit = property.metadata["unit"]
        
        if self.type == 'string':
            if isinstance(property, String):
                self.pattern = property.regex
            # elif isinstance(property, Image)
            #     self.contentEncoding = ''
            #     self.contentMediaType = ''

        elif self.type == 'number':
            assert isinstance(property, (Number, Integer))
            if isinstance(property.bounds[0], (int, float)):
                self.minimum = property.bounds[0]
            if isinstance(property.bounds[1], (int, float)):
                self.maximum = property.bounds[1]
            self.exclusiveMinimum = not property.inclusive_bounds[0]
            self.exclusiveMaximum = not property.inclusive_bounds[1]
            if property.step:
                self.multipleOf = property.step
        
        elif self.type == 'boolean':
            pass 
        
        return self.asdict()
    

@dataclass
class ActionAffordance(InteractionAffordance):
    forms : typing.List[typing.Dict[str, str]]
    input : object 
    output : object 
    safe : bool
    idempotent : bool 
    synchronous : bool 

    def __init__(self):
        super().__init__()

    def build(self, action : typing.Callable) -> typing.Dict[str, typing.Any]:
        if not hasattr(action, '_remote_info'):
            raise RuntimeError("This object is not an action")
        if action._remote_info.argument_schema: 
            self.input = action._remote_info.argument_schema 
        if action._remote_info.return_value_schema: 
            self.output = action._remote_info.return_value_schema 
        self.title = action.__qualname__
        self.description = action.__doc__
        self.safe = True 
        self.idempotent = False 
        self.synchronous = True 
        return self.asdict()
    


@dataclass
class EventAffordance:
    subscription : str
    data : typing.Dict[str, JSONSerializable]

    def build(self, event):
        return asdict(self)


@dataclass
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
    properties : typing.List[PropertyAffordance]
    actions : typing.List[ActionAffordance]
    events : typing.List[EventAffordance]
    links : typing.Optional[typing.List[Link]] 
    forms : typing.Optional[typing.List[Form]]
    security : typing.Union[str, typing.List[str]]
    securityDefinitions : SecurityScheme
    
    def build(self, instance : Thing) -> typing.Dict[str, typing.Any]: 
        self.context = "https://www.w3.org/2022/wot/td/v1.1"
        self.id = instance.instance_name
        self.title = instance.__class__.__name__
        self.description = instance.__doc__
        self.properties = dict()
        self.actions = dict()
        self.events = dict()

        for resource in instance.instance_resources.values():
            if resource.isparameter:
                if resource.obj_name not in self.properties:
                    self.properties[resource.obj_name] = PropertyDescription().build(resource.obj) 
            elif resource.iscallable:
                if resource.obj_name not in self.actions:
                    self.actions[resource.obj_name] = ActionDescription().build(resource.obj)
    
        for event in instance.events:
            self.events[event["name"]] = EventDescription.build(event)
    
        
        
