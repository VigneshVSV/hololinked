from hololinked.server import RemoteObject, RemoteParameter


class TestObject(RemoteObject):
    
    my_untyped_serializable_attribute = RemoteParameter(default=5, 
                allow_None=False, doc="this parameter can hold any value")
    
    my_custom_typed_serializable_attribute = RemoteParameter(default=[2, "foo"], 
                allow_None=False, doc="this parameter can hold any value")
    
    @my_custom_typed_serializable_attribute.getter
    def get_param(self):
        try:
            return self._foo     
        except AttributeError:
            return self.parameters.descriptors["my_custom_typed_serializable_attribute"].default 

    @my_custom_typed_serializable_attribute.setter
    def set_param(self, value):
        if isinstance(value, (list, tuple)) and len(value) < 100:
            for index, val in enumerate(value): 
                if not isinstance(val, (str, int, type(None))):
                    raise ValueError(f"Value at position {index} not acceptable member" 
                                " type of my_custom_typed_serializable_attribute",
                                f" but type {type(val)}")
            self._foo = value
        else:
            raise TypeError(f"Given type is not list or tuple",
                f" for my_custom_typed_serializable_attribute but type {type(value)}")
        

