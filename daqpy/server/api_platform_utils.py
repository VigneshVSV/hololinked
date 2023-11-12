from typing import Dict, List, Any, Union
from dataclasses import dataclass, field, asdict

from .constants import POST
from .serializers import JSONSerializer


@dataclass
class postman_collection:
    """
    Generate postman JSON of schema v2.1.0 (https://schema.postman.com/collection/json/v2.1.0/draft-04/collection.json)
    """
    info : "postman_collection_info"
    item : Union[List[Union["postman_item", "postman_itemgroup"]], Dict[str, Any]]

    def add_item(self, item : Union["postman_item", "postman_itemgroup"]) -> None:
        if isinstance(self.item, dict):
            raise ValueError("Please define item as a list before adding requests to item.")
        self.item.append(item)

    def json(self):
        return asdict(self)
    
    def json_file(self, filename = 'collection.json'):
        with open(filename, 'w') as file: 
            JSONSerializer.general_dump(self.json(), file)

@dataclass
class postman_collection_info:
    """
    info field of postman collection 
    """
    name : str 
    description : str
    version : str = field(default="v2.1.0")
    schema : str = field(default="https://schema.getpostman.com/json/collection/v2.1.0/")

    def json(self):
        return asdict(self)

@dataclass
class postman_item:
    """
    item field of postman collection 
    """
    name : str 
    request : "postman_http_request"    
    description : Union[str, None] = field(default=None)

    def json(self):
        return asdict(self)

@dataclass
class postman_http_request:
    """
    HTTP request item of postman collection
    """
    url : str 
    header : Union[List[Dict[str, Any]], None] = field(default=None)  
    body : Union[Dict[str, Any], None] = field(default=None)
    method : str = field(default=POST) 
    description : Union[str, None] = field(default=None)

    def json(self):
        json_dict = asdict(self)
        if self.header is None:
            json_dict.pop("header", None)
        if self.body is None:
            json_dict.pop("body", None)
        return json_dict

@dataclass
class postman_itemgroup:
    """
    item group of postman collection
    """
    name : str 
    item : Union[postman_item, "postman_itemgroup", 
                List[Union["postman_item", "postman_itemgroup"]]] = field(default_factory=list)
    description : Union[str, None] = field(default=None)

    def add_item(self, item : Union["postman_item", "postman_itemgroup"]) -> None:
        if isinstance(self.item, dict):
            raise ValueError("Please define item as a list before adding requests to item.")
        if isinstance(self.item, list):
            self.item.append(item)
        else: 
            raise ValueError(f"itemgroup must be list, not type {type(item)}")
        
    def json(self):
        return asdict(self)
    


__all__ = [
    'postman_collection',
    'postman_collection_info',
    'postman_item',
    'postman_http_request',
    'postman_itemgroup'
]