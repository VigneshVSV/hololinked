from hololinked.server import RemoteObject, RemoteParameter
from hololinked.server.remote_parameters import String

class OceanOpticsSpectrometer(RemoteObject):
    """
    Spectrometer example object 
    """

    my_untyped_serializable_attribute = RemoteParameter(default=[2, "foo"], 
                allow_None=False, doc="this parameter can hold any value")

    serial_number = String(default="USB2+H15897", allow_None=False, readonly=True, 
                        doc="serial number of the spectrometer (string)") # type: str
    
    @my_untyped_serializable_attribute.getter
    def get_param(self):
        try:
            return self._foo     
        except AttributeError:
            self.parameters.descriptors["my_untyped_serilizable_parameter"].default 

    @my_untyped_serializable_attribute.setter
    def set_param(self, value):
        if isinstance(value, (list, tuple)) and len(value) < 100:
            for val in value: 
                if not isinstance(val, (str, int, type(None))):
                    raise ValueError("not acceptable member type of",
                        f" my_untyped_serializable_attribute but type {type(val)}")
            self._foo = value
        else:
            raise TypeError(f"Given type is not list or tuple",
                f" for my_untyped_serializable_attribute but type {type(value)}")