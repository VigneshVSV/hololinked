from typing import Dict, List, Any, Union
from dataclasses import dataclass, field, asdict

from .constants import HTTP_METHODS
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
    
    def save_json_file(self, filename = 'collection.json'):
        with open(filename, 'w') as file: 
            JSONSerializer.generic_dump(self.json(), file)

    @classmethod
    def build(cls, instance, domain_prefix : str) -> Dict[str, Any]:
        from .thing import Thing
        from .dataklasses import HTTPResource, RemoteResource
        assert isinstance(instance, Thing) # type definition
        try:
            return instance._postman_collection
        except AttributeError:
            pass 
        properties_folder = postman_itemgroup(name='properties')
        methods_folder = postman_itemgroup(name='methods')
        events_folder = postman_itemgroup(name='events')

        collection = postman_collection(
            info = postman_collection_info(
                name = instance.__class__.__name__,
                description = "API endpoints available for Thing", 
            ),
            item = [ 
                properties_folder,
                methods_folder                
            ]
        )

        for http_method, resource in instance.httpserver_resources.items():
            # i.e. this information is generated only on the httpserver accessible resrouces...
            for URL_path, httpserver_data in resource.items():
                if isinstance(httpserver_data, HTTPResource):
                    scada_info : RemoteResource
                    try:
                        scada_info = instance.instance_resources[httpserver_data.instruction]
                    except KeyError:
                        property_path_without_RW = httpserver_data.instruction.rsplit('/', 1)[0]
                        scada_info = instance.instance_resources[property_path_without_RW]
                    item = postman_item(
                        name = scada_info.obj_name,
                        request = postman_http_request(
                            description=scada_info.obj.__doc__,
                            url=domain_prefix + URL_path, 
                            method=http_method,
                        )
                    )
                    if scada_info.isproperty:
                        properties_folder.add_item(item)
                    elif scada_info.iscallable:
                        methods_folder.add_item(item)
        
        instance._postman_collection = collection
        return collection


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
    method : str = field(default=HTTP_METHODS.POST) 
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