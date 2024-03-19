from hololinked.server import RemoteObject, RemoteParameter
from hololinked.server.remote_parameters import String

class OceanOpticsSpectrometer(RemoteObject):
    """
    Spectrometer example object 
    """

    my_untyped_serializable_attribute = RemoteParameter(default=None, 
                allow_None=True, doc="this parameter can hold any value")

    serial_number = String(default="USB2+H15897", allow_None=False, readonly=True, 
                        doc="serial number of the spectrometer (string)") # type: str