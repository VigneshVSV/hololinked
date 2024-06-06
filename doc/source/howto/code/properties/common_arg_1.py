from hololinked.server import RemoteObject
from hololinked.server.remote_parameters import String, Number, TypedList


class OceanOpticsSpectrometer(RemoteObject):
    """
    Spectrometer example object 
    """

    serial_number = String(default="USB2+H15897", allow_None=False, readonly=True, 
                        doc="serial number of the spectrometer (string)") # type: str

    integration_time_millisec = Number(default=1000, bounds=(0.001, None), 
                            crop_to_bounds=True, allow_None=False,
                            doc="integration time of measurement in milliseconds")
    
    model = String(default=None, allow_None=True, constant=True,
                        doc="model of the connected spectrometer")
    
    custom_background_intensity = TypedList(item_type=(float, int), default=None, 
                    allow_None=True,
                    doc="user provided background substraction intensity")
    
    def __init__(self, instance_name, serial_number, integration_time) -> None:
        super().__init__(instance_name=instance_name)
        # allow_None
        self.custom_background_intensity = None # OK 
        self.custom_background_intensity = [] # OK
        self.custom_background_intensity = None # OK
        # following raises TypeError because allow_None = False
        self.integration_time_millisec = None 
        # readonly - following raises ValueError because readonly = True
        self.serial_number = serial_number 
        # constant
        self.model = None # OK - constant accepts None 
        self.model = 'USB2000+' # OK - can be set once 
        self.model = None # raises TypeError