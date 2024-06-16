from hololinked.server import Thing
from hololinked.server.properties import String, Number, TypedList


class OceanOpticsSpectrometer(Thing):
    """
    Spectrometer example object 
    """

    serial_number = String(default="USB2+H15897", allow_None=False, readonly=True, 
                        doc="serial number of the spectrometer (string)",
                        label="serial number") # type: str

    integration_time = Number(default=1000, bounds=(0.001, None), 
                            crop_to_bounds=True, allow_None=False,
                            label="Integration Time (ms)",
                            doc="integration time of measurement in milliseconds")
    
    model = String(default=None, allow_None=True, constant=True, 
                label="device model", doc="model of the connected spectrometer")
    
    custom_background_intensity = TypedList(item_type=(float, int), default=None, 
                    allow_None=True, label="Custom Background Intensity",
                    doc="user provided background substraction intensity")
    
    def __init__(self, instance_name, serial_number, integration_time = 5):
        super().__init__(instance_name=instance_name)
        
        # allow_None
        self.custom_background_intensity = None # OK 
        self.custom_background_intensity = [] # OK
        self.custom_background_intensity = None # OK

        # allow_None = False
        self.integration_time = None # NOT OK, raises TypeError
        self.integration_time = integration_time # OK
        
        # readonly = True
        self.serial_number = serial_number # NOT OK - raises ValueError
        
        # constant = True, mandatorily needs allow_None = True
        self.model = None # OK - constant accepts None when initially None
        self.model = 'USB2000+' # OK - can be set once 
        self.model = None # NOT OK - raises ValueError


if __name__ == '__main__':
    spectrometer = OceanOpticsSpectrometer(instance_name='spectrometer1', 
                                    serial_number='S14155')