import json
import typing
from pprint import pprint
from typing import Dict, Any, Union

from .baseprops import BooleanProp, ComponentName, TypedListProp, TypedList
from .basecomponents import BaseComponentWithChildren, Page



class ReactApp(BaseComponentWithChildren):
    """
    Main React App
    kwargs 
    URL : give the URL to access all the components
    """
    componentName = ComponentName(default="__App__")
    children : typing.List[Page] = TypedListProp(item_type=Page, 
                            doc="pages in the app, add multiple pages to quickly switch between UIs")
    showUtilitySpeedDial : bool = BooleanProp(default=True, allow_None=False)
    remoteObjects : list = TypedList(default=None, allow_None=True, item_type=str, 
                            doc="add rmeote object URLs to display connection status") # type: ignore

    def __init__(self):
        super().__init__(id='__App__')    
        
    def save_json(self, file_name : str, indent : int = 4, tree : Union[str, None] = None) -> None:
        if tree is None:
            with open(file_name, 'w') as file:
                json.dump(self.json(), file, ensure_ascii=False, allow_nan=True)
        else: 
            with open(file_name, 'w') as file:
               json.dump(self.get_component(self.json(), tree), file, ensure_ascii=False, allow_nan=True)
                 
    def print_json(self, tree : Union[str, None] = None) -> None:
        if tree is not None:         
            pprint(self.get_component(self.json(), tree))
        else: 
            pprint(self.json())

    def get_component(self, children : Dict[str, Any], tree : str):
        for component_json in children.values():
            if component_json["tree"] == tree:
                return component_json
        raise AttributeError("No component with tree {} found.".format(tree))        



__all__ = ['ReactApp']