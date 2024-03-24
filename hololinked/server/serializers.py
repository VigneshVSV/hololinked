# adopted from pyro - https://github.com/irmen/Pyro5 - see following license
"""
MIT License

Copyright (c) Irmen de Jong

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from collections import deque
import json
import pickle
import traceback 
import serpent
from msgspec import json, msgpack 
import json as pythonjson
import inspect
import array
import datetime
import uuid
import decimal
import typing
from enum import Enum, StrEnum

from ..param.parameters import TypeConstrainedList, TypeConstrainedDict, TypedKeyMappingsConstrainedDict


dict_keys = type(dict().keys())



class BaseSerializer(object):
    """Base class for (de)serializer implementations (which must be thread safe)"""
    
    def loads(self, data):
        raise NotImplementedError("implement in subclass")

    def dumps(self, data):
        raise NotImplementedError("implement in subclass")
    
    @classmethod
    def convert_to_bytes(self, data):
        if type(data) is bytearray:
            return bytes(data)
        if type(data) is memoryview:
            return data.tobytes()
        return data

    @classmethod
    def register_class_to_dict(cls, clazz, converter, serpent_too=True):
        """Registers a custom function that returns a dict representation of objects of the given class.
        The function is called with a single parameter; the object to be converted to a dict."""
        raise NotImplementedError("Function register_class_to_dict has to be implemented")

    @classmethod
    def unregister_class_to_dict(cls, clazz):
        """Removes the to-dict conversion function registered for the given class. Objects of the class
        will be serialized by the default mechanism again."""
        raise NotImplementedError("Function unregister_class_to_dict has to be implemented")

    @classmethod
    def register_dict_to_class(cls, classname, converter):
        """
        Registers a custom converter function that creates objects from a dict with the given classname tag in it.
        The function is called with two parameters: the classname and the dictionary to convert to an instance of the class.
        """
        raise NotImplementedError("Function register_dict_to_class has to be implemented")

    @classmethod
    def unregister_dict_to_class(cls, classname):
        """
        Removes the converter registered for the given classname. Dicts with that classname tag
        will be deserialized by the default mechanism again.
        """
        raise NotImplementedError("Function unregister_dict_to_class has to be implemented")

    @classmethod
    def class_to_dict(cls, obj):
        """
        Convert a non-serializable object to a dict. Partly borrowed from serpent.
        """
        raise NotImplementedError("Function class_to_dict has to be implemented")

    @classmethod
    def dict_to_class(cls, data):
        """
        Recreate an object out of a dict containing the class name and the attributes.
        Only a fixed set of classes are recognized.
        """
        raise NotImplementedError("Function dict_to_class has to be implemented")

    def recreate_classes(self, literal):
        raise NotImplementedError("Function class_to_dict has to be implemented")



class JSONSerializer(BaseSerializer):
    """(de)serializer that wraps the json serialization protocol."""
    _type_replacements = {}

    def __init__(self) -> None:
        super().__init__()

    def dumps(self, data) -> bytes:
        return json.encode(data, enc_hook=self.default)

    def dump(self, data : typing.Dict[str, typing.Any], file_desc) -> None:
        raise NotImplementedError("dump is not implemented")
        # return json.dump(data, file_desc, ensure_ascii=False, allow_nan=True, default=self.default)

    def loads(self, data : typing.Union[bytearray, memoryview, bytes]) -> typing.Any:
        data : str = self.convert_to_bytes(data).decode("utf-8") 
        try:
            return json.decode(data)
        except Exception as ex:
            if len(data) == 0:
                raise ex from None 
            elif data[0].isalpha():
                return data 
            else:
                raise ex from None

    def load(cls, file_desc) -> typing.Dict[str, typing.Any]:
        raise NotImplementedError("load is not implemented")

    @classmethod
    def default(cls, obj):
        if hasattr(obj, 'json'):
            # alternative to type replacement
            return obj.json()
        if isinstance(obj, Enum):
            return obj.name
        if isinstance(obj, (set, dict_keys, deque, tuple)):
            # json module can't deal with sets so we make a tuple out of it
            return list(obj)  
        if isinstance(obj, (TypeConstrainedDict, TypeConstrainedList, TypedKeyMappingsConstrainedDict)):
            return obj._inner # copy has been implemented with same signature for both types 
        replacer = cls._type_replacements.get(type(obj), None)
        if replacer:
            return replacer(obj)
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        if isinstance(obj, decimal.Decimal):
            return str(obj)
        if isinstance(obj, Exception):
            return {
                "message" : str(obj),
                "type"    : repr(obj).split('(', 1)[0],
                "traceback" : traceback.format_exc().splitlines(),
                "notes"   : obj.__notes__ if hasattr(obj, "__notes__") else None
            }, 
        if isinstance(obj, array.array):
            if obj.typecode == 'c':
                return obj.tostring()
            if obj.typecode == 'u':
                return obj.tounicode()
            return obj.tolist()
        raise TypeError("Given type cannot be converted to JSON : {}".format(type(obj)))
        # return self.class_to_dict(obj)

    @classmethod
    def register_type_replacement(cls, object_type, replacement_function):
        if object_type is type or not inspect.isclass(object_type):
            raise ValueError("refusing to register replacement for a non-type or the type 'type' itself")
        cls._type_replacements[object_type] = replacement_function



class PythonBuiltinJSONSerializer(JSONSerializer):

    def dumps(self, data) -> bytes:
        data = pythonjson.dumps(data, ensure_ascii=False, allow_nan=True, default=self.default)
        return data.encode("utf-8")
       
    def dump(self, data : typing.Dict[str, typing.Any], file_desc) -> None:
        pythonjson.dump(data, file_desc, ensure_ascii=False, allow_nan=True, default=self.default)

    def loads(self, data : typing.Union[bytearray, memoryview, bytes]) -> typing.Any:
        data : str = self.convert_to_bytes(data).decode("utf-8") 
        try:
            return pythonjson.loads(data)
        except Exception as ex:
            if len(data) == 0:
                raise ex from None 
            elif data[0].isalpha():
                return data 
            else:
                raise ex from None



class PickleSerializer(BaseSerializer):

    serializer_id = 2  # never change this

    def dumps(self, data):
        return pickle.dumps(data)
    
    def loads(self, data):
        return pickle.loads(data)
    

class SerpentSerializer(BaseSerializer):
    """(de)serializer that wraps the serpent serialization protocol."""
    serializer_id = 3  # never change this

    def dumps(self, data):
        return serpent.dumps(data, module_in_classname=True)

    def loads(self, data):
        return serpent.loads(data)

    @classmethod
    def register_type_replacement(cls, object_type, replacement_function):
        def custom_serializer(obj, serpent_serializer, outputstream, indentlevel):
            replaced = replacement_function(obj)
            if replaced is obj:
                serpent_serializer.ser_default_class(replaced, outputstream, indentlevel)
            else:
                serpent_serializer._serialize(replaced, outputstream, indentlevel)

        if object_type is type or not inspect.isclass(object_type):
            raise ValueError("refusing to register replacement for a non-type or the type 'type' itself")
        serpent.register_class(object_type, custom_serializer)



class MsgpackSerializer(BaseSerializer):

    def __init__(self) -> None:
        super().__init__()

    def dumps(self, value) -> bytes:
        return msgpack.encode(value)

    def loads(self, value) -> typing.Any:
        return msgpack.decode(value)
    


serializers = {
    'pickle'  : PickleSerializer,
    'json'    : JSONSerializer, 
    'serpent' : SerpentSerializer,
    None      : MsgpackSerializer,
    'msgpack' : MsgpackSerializer,
}

class Serializers(StrEnum):
    PICKLE = 'pickle'
    JSON = 'json'
    SERPENT = 'serpent'
    MSGSPEC_MSGPACK = 'msgpack'


__all__ = ['JSONSerializer', 'SerpentSerializer', 'PickleSerializer', 'MsgpackSerializer', 
        'serializers', 'BaseSerializer']