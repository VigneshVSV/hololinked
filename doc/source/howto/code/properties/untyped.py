from logging import Logger
from hololinked.server import Thing, Property
from hololinked.server.serializers import JSONSerializer


class TestObject(Thing):
    
    my_untyped_serializable_attribute = Property(default=5, 
                allow_None=True, doc="this property can hold any value")
    
    my_custom_typed_serializable_attribute = Property(default=[2, "foo"], 
                allow_None=False, doc="""this property can hold some 
                                        values based on get-set overload""")
    
    @my_custom_typed_serializable_attribute.getter
    def get_prop(self):
        try:
            return self._foo     
        except AttributeError:
            return self.properties.descriptors[
                    "my_custom_typed_serializable_attribute"].default 

    @my_custom_typed_serializable_attribute.setter
    def set_prop(self, value):
        if isinstance(value, (list, tuple)) and len(value) < 100:
            for index, val in enumerate(value): 
                if not isinstance(val, (str, int, type(None))):
                    raise ValueError(f"Value at position {index} not " + 
                            "acceptable member type of " +
                            "my_custom_typed_serializable_attribute " +
                            f"but type {type(val)}")
            self._foo = value
        else:
            raise TypeError(f"Given type is not list or tuple for " +
                    f"my_custom_typed_serializable_attribute but type {type(value)}")
        
    def __init__(self, *, instance_name: str, **kwargs) -> None:
        super().__init__(instance_name=instance_name, **kwargs)
        self.my_untyped_serializable_attribute = kwargs.get('some_prop', None)
        self.my_custom_typed_serializable_attribute = [1, 2, 3, ""]
