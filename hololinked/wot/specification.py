import typing 
from dataclasses import dataclass


from .thing import Thing


class PropertyDescription:
    type : str
    observable : bool

class ActionDescription:
    forms : typing.List[typing.Dict[str, str]]


class EventDescription:
    subscription : str


class VersionInfo:
    """
    https://www.w3.org/TR/wot-thing-description11/#versioninfo
    """
    instance : str 
    model : str


class Link:
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
    securityDefinitions : typing.Dict[str, typing.Dict]

