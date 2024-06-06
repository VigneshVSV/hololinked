from hololinked.server import RemoteObject
from hololinked.server.remote_parameters import String, Number


class OceanOpticsSpectrometer(RemoteObject):
    """
    Spectrometer example object 
    """

    serial_number = String(default="USB2+H15897", allow_None=False, readonly=True, 
                        doc="serial number of the spectrometer (string)") # type: str

    integration_time_millisec = Number(default=1000, bounds=(0.001, None), 
                            crop_to_bounds=True, 
                            doc="integration time of measurement in milliseconds")
    
    def __init__(self, instance_name, serial_number, integration_time) -> None:
        super().__init__(instance_name=instance_name)
        self.serial_number = serial_number # raises ValueError because readonly=True

    @integration_time_millisec.setter 
    def set_integration_time(self, value):
        # value is already validated as a float or int 
        # & cropped to specified bounds when this setter invoked 
        self.device.integration_time_micros(int(value*1000))
        self._integration_time_ms = int(value) 

    @integration_time_millisec.getter 
    def get_integration_time(self):
        try:
            return self._integration_time_ms
        except:
            return self.parameters["integration_time_millisec"].default 