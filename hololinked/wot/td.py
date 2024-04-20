import typing 
from dataclasses import dataclass, asdict, field

from ..server.data_classes import RemoteResourceInfoValidator
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

    skip_keys = [] # override this to skip some dataclass attributes in the schema

    replacement_keys = {
        'context' : '@context',
        'htv_methodName' : 'htv:methodName'
    }

    def asdict(self):
        schema = dict()
        for field, value in self.__dataclass_fields__.items():    
            if getattr(self, field, NotImplemented) is NotImplemented or field in self.skip_keys:
                continue
            if field in self.replacement_keys: 
                schema[self.replacement_keys[field]] = getattr(self, field)
            else: 
                schema[field] = getattr(self, field)
        return schema
    
    @classmethod
    def format_doc(cls, doc : str):
        """
        strip tabs, newlines, whitespaces etc. 
        """
        doc_as_list = doc.split('\n')
        final_doc = []
        for line in doc_as_list:
            line = line.lstrip('\n').rstrip('\n')
            line = line.lstrip('\t').rstrip('\t')
            line = line.lstrip('\n').rstrip('\n')
            line = line.lstrip().rstrip()              
            final_doc.append(line)
        return ''.join(final_doc)


@dataclass
class InteractionAffordance(Schema):
    """
    implements schema common to all interaction affordances. 
    concepts - https://www.w3.org/TR/wot-thing-description11/#interactionaffordance
    """
    title : str 
    titles : typing.Optional[typing.Dict[str, str]]
    description : str
    descriptions : typing.Optional[typing.Dict[str, str]] 
    forms : typing.List["Form"]
  
    def __init__(self):
        super().__init__()


@dataclass
class DataSchema(Schema):
    """
    implementes Dataschema attributes.
    concepts - https://www.w3.org/TR/wot-thing-description11/#sec-data-schema-vocabulary-definition
    """
    title : str 
    titles : typing.Optional[typing.Dict[str, str]]
    description : str
    descriptions : typing.Optional[typing.Dict[str, str]] 
    constant : bool
    default : typing.Optional[typing.Any] 
    readOnly : bool
    writeOnly : bool
    format : typing.Optional[str]
    unit : typing.Optional[str]
    type : str
    oneOf : typing.Optional[typing.List[Schema]]
    enum : typing.Optional[typing.List[typing.Any]]

    def __init__(self):
        super().__init__()


class Link:
    pass 


@dataclass
class ExpectedResponse(Schema):
    """
    Form property. 
    schema - https://www.w3.org/TR/wot-thing-description11/#expectedresponse
    """
    contentType : str

    def __init__(self):
        super().__init__()

@dataclass
class AdditionalExpectedResponse(Schema):
    """
    Form property.
    schema - https://www.w3.org/TR/wot-thing-description11/#additionalexpectedresponse
    """
    success : bool 
    contentType : str 
    schema : typing.Optional[typing.Dict[str, typing.Any]]

    def __init__(self):
        super().__init__()


@dataclass
class Form(Schema):
    """
    Form hypermedia.
    schema - https://www.w3.org/TR/wot-thing-description11/#form
    """
    href : str 
    contentEncoding : typing.Optional[str]
    security : typing.Optional[str]
    scopes : typing.Optional[str]
    response : typing.Optional[ExpectedResponse]
    additionalResponses : typing.Optional[typing.List[AdditionalExpectedResponse]]
    subprotocol : typing.Optional[str]
    op : str 
    htv_methodName : str 
    contentType : typing.Optional[str] = field(default='application/json')
    
    def __init__(self):
        super().__init__()

    def build(self, object):
        return self.asdict()


@dataclass
class PropertyAffordance(InteractionAffordance, DataSchema):
    """
    creates property affordance schema from ``property`` descriptor object (or parameter)
    schema - https://www.w3.org/TR/wot-thing-description11/#propertyaffordance
    """
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
        TypedDict : 'object',
        RemoteParameter : 'null' # i.e. NullShema - nothing to add
    }

    def __init__(self):
        super(InteractionAffordance, self).__init__()
        super(DataSchema, self).__init__()

    def build(self, property : Property, instance : Thing) -> typing.Dict[str, typing.Any]:
        self.type = self.property_type[property.__class__]
        self.title = property.name
        self.readOnly = property.readonly
        self.writeOnly = False
        self.constant = property.constant
        self.observable = property.observable
        
        if property.doc:
            self.description = self.format_doc(property.doc)
        if property.overloads["fget"] is None:
            self.default = property.default
        if property.metadata and property.metadata.get("unit", None) is not None:
            self.unit = property.metadata["unit"]
        
        if self.type == 'string' and isinstance(property, String):
            if property.regex is not None:
                self.pattern = property.regex

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

        self.forms = []
        for index, method in enumerate(property._remote_info.http_method):
            form = Form()
            if index == 0:
                form.op = 'readproperty'
            elif index == 1:
                form.op = 'writeproperty'
            form.href = f"http://localhost:8083{instance._full_URL_path_prefix}{property._remote_info.URL_path}"
            form.htv_methodName = method.upper()
            self.forms.append(form.asdict())
        
        return self.asdict()
    

@dataclass
class ActionAffordance(InteractionAffordance):
    """
    creates action affordance schema from actions (or methods).
    schema - https://www.w3.org/TR/wot-thing-description11/#actionaffordance
    """
    input : object 
    output : object 
    safe : bool
    idempotent : bool 
    synchronous : bool 

    def __init__(self):
        super(InteractionAffordance, self).__init__()
    
    def build(self, action : typing.Callable, instance : Thing) -> typing.Dict[str, typing.Any]:
        if not hasattr(action, '_remote_info'):
            raise RuntimeError("This object is not an action")
        assert isinstance(action._remote_info, RemoteResourceInfoValidator)
        if action._remote_info.argument_schema: 
            self.input = action._remote_info.argument_schema 
        if action._remote_info.return_value_schema: 
            self.output = action._remote_info.return_value_schema 
        self.title = action.__name__
        if action.__doc__:
            self.description = self.format_doc(action.__doc__)
        self.safe = True 
        self.idempotent = False 
        self.synchronous = True 
        self.forms = []
        for method in action._remote_info.http_method:
            form = Form()
            form.op = 'invokeaction'
            form.href = f'http://localhost:8083{instance._full_URL_path_prefix}{action._remote_info.URL_path}'
            form.htv_methodName = method.upper()
            self.forms.append(form.asdict())
        return self.asdict()
    

@dataclass
class EventAffordance:
    """
    creates event affordance schema from events.
    schema - https://www.w3.org/TR/wot-thing-description11/#eventaffordance
    """
    subscription : str
    data : typing.Dict[str, JSONSerializable]

    def build(self, event):
        return asdict(self)


@dataclass
class VersionInfo:
    """
    create version info.
    schema - https://www.w3.org/TR/wot-thing-description11/#versioninfo
    """
    instance : str 
    model : str


@dataclass
class SecurityScheme(Schema):
    """
    create security scheme. 
    schema - https://www.w3.org/TR/wot-thing-description11/#sec-security-vocabulary-definition
    """
    scheme: str 
    description : str 
    descriptions : typing.Optional[typing.Dict[str, str]]
    proxy : typing.Optional[str]

    def __init__(self):
        super().__init__()

    def build(self, name : str, instance):
        self.scheme = 'nosec'
        self.description = 'currently no security scheme supported - use cookie auth directly on hololinked.server.HTTPServer object'
        return { name : self.asdict() }



@dataclass
class ThingDescription(Schema):
    """
    generate Thing Description schema of W3 Web of Things standard. 
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
    created : typing.Optional[str] 
    modified : typing.Optional[str]
    support : typing.Optional[str] 
    base : typing.Optional[str] 
    properties : typing.List[PropertyAffordance]
    actions : typing.List[ActionAffordance]
    events : typing.List[EventAffordance]
    links : typing.Optional[typing.List[Link]] 
    forms : typing.Optional[typing.List[Form]]
    security : typing.Union[str, typing.List[str]]
    securityDefinitions : SecurityScheme

    skip_parameters = ['expose', 'httpserver_resources', 'rpc_resources', 'gui_resources',
                    'events', 'debug_logs', 'warn_logs', 'info_logs', 'error_logs', 'critical_logs',  
                    'thing_description', 'maxlen', 'execution_logs', 'GUI', 'object_info'  ]

    skip_actions = ['_parameter_values', '_parameters', 'push_events', 'stop_events', 
                    'postman_collection']

    def __init__(self):
        super().__init__()
    
    def build(self, instance : Thing) -> typing.Dict[str, typing.Any]: 
        self.context = "https://www.w3.org/2022/wot/td/v1.1"
        self.id = "http://localhost:8083/" + instance.instance_name
        self.title = instance.__class__.__name__ 
        self.description = self.format_doc(instance.__doc__) if instance.__doc__ else "no classdoc provided" 
        self.properties = dict()
        self.actions = dict()
        self.events = dict()

        for resource in instance.instance_resources.values():
            if resource.isparameter and resource.obj_name not in self.properties and resource.obj_name not in self.skip_parameters: 
                self.properties[resource.obj_name] = PropertyAffordance().build(resource.obj, instance) 
            elif resource.iscallable and resource.obj_name not in self.actions and resource.obj_name not in self.skip_actions:
                self.actions[resource.obj_name] = ActionAffordance().build(resource.obj, instance)

        # events still need to standardized so not including for now - they only work, but not neatly
        # for event in instance.events:
        #     self.events[event["name"]] = EventAffordance().build(event)

        self.security = 'unimplemented'
        self.securityDefinitions = SecurityScheme().build('unimplemented', instance)

        return self.asdict()
    
        
        
__all__ = [
    ThingDescription.__name__
]