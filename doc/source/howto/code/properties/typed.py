from hololinked.server import Thing
from hololinked.server.properties import String, Number, Selector, Boolean, List


class OceanOpticsSpectrometer(Thing):
    """
    Spectrometer example object 
    """

    serial_number = String(default="USB2+H15897", allow_None=False, 
                        doc="serial number of the spectrometer") # type: str

  
    def __init__(self, instance_name, serial_number, integration_time) -> None:
        super().__init__(instance_name=instance_name, serial_number=serial_number)
        self.connect() # connect first before setting integration time
        self.integration_time = integration_time      
  
    integration_time = Number(default=1000, 
                    bounds=(0.001, None), crop_to_bounds=True, 
                    doc="integration time of measurement in millisec") # type: int

    @integration_time.setter 
    def set_integration_time(self, value):
        # value is already validated as a float or int 
        # & cropped to specified bounds when this setter invoked 
        self.device.integration_time_micros(int(value*1000))
        self._integration_time_ms = int(value) 

    @integration_time.getter 
    def get_integration_time(self):
        try:
            return self._integration_time_ms
        except:
            return self.parameters["integration_time"].default 
        
    nonlinearity_correction = Boolean(default=False, 
                                URL_path='/nonlinearity-correction', 
                                doc="""set True for auto CCD nonlinearity 
                                    correction. Not supported by all models,
                                    like STS.""") # type: bool
        
    trigger_mode = Selector(objects=[0, 1, 2, 3, 4], 
                        default=0, URL_path='/trigger-mode', 
                        doc="""0 = normal/free running, 
                            1 = Software trigger, 2 = Ext. Trigger Level,
                            3 = Ext. Trigger Synchro/ Shutter mode,
                            4 = Ext. Trigger Edge""") # type: int
    
    @trigger_mode.setter 
    def apply_trigger_mode(self, value : int):
        self.device.trigger_mode(value)
        self._trigger_mode = value 
        
    @trigger_mode.getter 
    def get_trigger_mode(self):
        try:
            return self._trigger_mode
        except:
            return self.parameters["trigger_mode"].default 
        
    intensity = List(default=None, allow_None=True, doc="captured intensity", 
                    URL_path='/intensity', readonly=True,
                    fget=lambda self: self._intensity.tolist())      
        
    