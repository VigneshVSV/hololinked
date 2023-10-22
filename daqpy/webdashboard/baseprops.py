import typing

from ..param.parameters import (String, Integer, Number, Boolean, Selector, 
        ClassSelector, TupleSelector, Parameter, TypedList, TypedDict)
from ..param.exceptions import raise_ValueError
from .valuestub import ValueStub, StringStub, NumberStub, BooleanStub
from .exceptions import *


class Prop(Parameter):
    pass 


class StringProp(String):

    def validate_and_adapt(self : Parameter, value : typing.Any) -> typing.Union[typing.Any,
                                                                        ValueStub]:
        if isinstance(value, StringStub):
            return value
        return super().validate_and_adapt(value)    


class NumberProp(Number):

    def validate_and_adapt(self : Parameter, value : typing.Any) -> typing.Union[typing.Any,
                                                                        ValueStub]:
        if isinstance(value, NumberStub):
            return value
        return super().validate_and_adapt(value)     
    
      
class IntegerProp(Integer):

    def validate_and_adapt(self : Parameter, value : typing.Any) -> typing.Union[typing.Any,
                                                                        ValueStub]:
        if isinstance(value, NumberStub):
            return value
        return super().validate_and_adapt(value)     
          

class BooleanProp(Boolean):

    def validate_and_adapt(self : Parameter, value : typing.Any) -> typing.Union[typing.Any,
                                                                        ValueStub]:
        if isinstance(value, BooleanStub):
            return value
        return super().validate_and_adapt(value)     
       

class SelectorProp(Selector):

    def validate_and_adapt(self : Parameter, value : typing.Any) -> typing.Union[typing.Any,
                                                                        ValueStub]:
        if isinstance(value, ValueStub):
            return value
        return super().validate_and_adapt(value)    
    

class TupleSelectorProp(TupleSelector):

    def validate_and_adapt(self : Parameter, value : typing.Any) -> typing.Union[typing.Any,
                                                                        ValueStub]:
        if isinstance(value, ValueStub):
            return value
        return super().validate_and_adapt(value)   
    

class ObjectProp(TypedDict):

    def __init__(self, default : typing.Union[typing.Dict[typing.Any, typing.Any], None] = None, 
                item_type : typing.Any = None, bounds : tuple = (0, None), allow_None : bool = True, 
                **params):
        super().__init__(default, key_type=str, item_type=item_type, bounds=bounds, 
                        allow_None=allow_None, **params)
     

class NodeProp(ClassSelector):
    """
    For props which is supposed to accept only one child instead of multiple children
    """
    def validate_and_adapt(self : Parameter, value : typing.Any) -> typing.Union[typing.Any,
                                                                        ValueStub]:
        if isinstance(value, ValueStub):
            return value
        return super().validate_and_adapt(value)  
    

class TypedListProp(TypedList):
   
    def __init__(self, default: typing.Union[typing.List[typing.Any], None] = None, 
                    item_type: typing.Any = None, bounds: tuple = (0, None), **params):
        super().__init__(default, item_type=item_type, bounds=bounds, allow_None=True, 
                accept_nonlist_object=True, **params)


class ComponentName(String):

    def __init__(self, default = ""):
        super().__init__(default, regex=r"[A-Za-z_]+[A-Za-z]*", allow_None=False, readonly=True,
                        doc="Constant internal value for mapping ReactBaseComponent subclasses to renderable components in front-end")


class HTMLid(String):
   
    def __init__(self, default: typing.Union[str, None] = "") -> None:
        super().__init__(default, regex = r'[A-Za-z_]+[A-Za-z_0-9\-]*', allow_None = True, 
                         doc = "HTML id of the component, must be unique.") 

    def validate_and_adapat(self, value : typing.Any) -> str:
        if value == "App":
            raise_ValueError("HTML id 'App' is reserved for `ReactApp` instances. Please use another id value.", self)
        return super().validate_and_adapt(value)
    


class ActionID(String):
   
    def __init__(self, **kwargs) -> None:
        super().__init__(default = None, regex = r'[A-Za-z_]+[A-Za-z_0-9\-]*', allow_None = True, constant = True,
                         doc = "Action id of the component, must be unique. No need to set as its internally generated.", **kwargs) 

   
class dataGrid:
    __allowedKeys__ = ['x', 'y', 'w', 'h', 'minW', 'maxW', 'minH', 'maxH', 'static', 
                    'isDraggable', 'isResizable', 'isBounded', 'resizeHandles']
    
    x = NumberProp(default=0, bounds=(0, None), allow_None=False)
    y = NumberProp(default=0, bounds=(0, None), allow_None=False)
    w = NumberProp(default=0, bounds=(0, None), allow_None=False)
    h = NumberProp(default=0, bounds=(0, None), allow_None=False)
    minW = NumberProp(default=None, bounds=(0, None), allow_None=True)
    maxW = NumberProp(default=None, bounds=(0, None), allow_None=True)
    minH = NumberProp(default=None, bounds=(0, None), allow_None=True)
    maxH = NumberProp(default=None, bounds=(0, None), allow_None=True)
    static        = BooleanProp(default=True, allow_None=True)
    isDraggable   = BooleanProp(default=None, allow_None=True)
    isResizable   = BooleanProp(default=None, allow_None=True)
    isBounded     = BooleanProp(default=None, allow_None=True)
    resizeHandles = TupleSelector(default=['se'], objects=['s' , 'w' , 'e' , 'n' , 'sw' , 'nw' , 'se' , 'ne'])
    
    def __init__(self, **kwargs) -> None:
        for key in kwargs.keys():
            if key not in self.__allowedKeys__:
                raise AttributeError("unknown key `{}` for dataGrid prop.".format(key))
        for key, value in kwargs.items():
            setattr(self, key, value)

    def json(self):
        d = dict(
                x = self.x,
                y = self.y, 
                w = self.w,
                h = self.h, 
                minW = self.minW,
                maxW = self.maxW,
                minH = self.minH,
                maxH = self.maxH,
                static = self.static,
                isDraggable = self.isDraggable, 
                isResizable = self.isResizable,
                isBounded = self.isBounded,
                resizeHandles = self.resizeHandles
        )
        none_keys = []
        for key in self.__allowedKeys__:
            if d[key] is None:
                none_keys.append(key)
        for key in none_keys:
            d.pop(key, None)
        return d


class StubProp(ClassSelector):

    def __init__(self, default=None, **params):
        super().__init__(class_=ValueStub, default=default, constant=True, **params)

    
class UnsupportedProp(Parameter):

    def __init__(self, doc : typing.Union[str, None] = "This prop is not supported as it generally executes a client-side only function" ):
        super().__init__(None, doc=doc, constant=True, readonly=True, allow_None=True)
       

class ClassSelectorProp(ClassSelector):
    pass 

