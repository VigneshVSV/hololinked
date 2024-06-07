import threading, logging
from hololinked.server import Thing, Property, action, Event
from hololinked.server.properties import Number, Selector, String, List
from hololinked.server.constants import HTTP_METHODS
from seabreeze.spectrometers import Spectrometer


class OceanOpticsSpectrometer(Thing):
    """
    Spectrometer example object 
    """

    serial_number = String(default=None, allow_None=True, constant=True, 
                        URL_path='/serial-number',
                        doc="serial number of the spectrometer") # type: str

    def __init__(self, instance_name, serial_number, autoconnect, **kwargs):
        super().__init__(instance_name=instance_name, serial_number=serial_number,
                        **kwargs) 
        # you can also pass properties to init to auto-set (optional)
        if autoconnect and self.serial_number is not None:
            self.connect(trigger_mode=0, integration_time=int(1e6)) # let's say, by default
        self._acquisition_thread = None
        self.measurement_event = Event(name='intensity-measurement', 
                                URL_path='/intensity/measurement-event')

    @action(URL_path='/connect')
    def connect(self, trigger_mode, integration_time):
        self.device = Spectrometer.from_serial_number(self.serial_number)
        if trigger_mode:
            self.device.trigger_mode(trigger_mode)
        if integration_time:
            self.device.integration_time_micros(integration_time)

    integration_time = Number(default=1000, bounds=(0.001, 1e6), crop_to_bounds=True, 
                            doc="""integration time of measurement in milliseconds,
                                1μs (min) or 1s (max) """)
    
    @integration_time.setter 
    def apply_integration_time(self, value : float):
        self.device.integration_time_micros(int(value*1000))
        self._integration_time = int(value) 
      
    @integration_time.getter 
    def get_integration_time(self) -> float:
        try:
            return self._integration_time
        except:
            return self.parameters["integration_time"].default 
        
    trigger_mode = Selector(objects=[0, 1, 2, 3, 4], default=0, URL_path='/trigger-mode', 
                    doc="""0 = normal/free running, 1 = Software trigger, 2 = Ext. Trigger Level,
                        3 = Ext. Trigger Synchro/ Shutter mode, 4 = Ext. Trigger Edge""")
    
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
                    URL_path='/intensity',
                    readonly=True, fget=lambda self: self._intensity.tolist())       

    def capture(self):
        self._run = True 
        while self._run:
            self._intensity = self.device.intensities(
                                        correct_dark_counts=False,
                                        correct_nonlinearity=False
                                    )
            self.measurement_event.push(self._intensity.tolist())
            self.logger.debug(f"pushed measurement event")

    @action(URL_path='/acquisition/start', http_method="POST")
    def start_acquisition(self):
        if self._acquisition_thread is None:
            self._acquisition_thread = threading.Thread(target=self.capture) 
            self._acquisition_thread.start()
        
    @action()
    def stop_acquisition(self):
        if self._acquisition_thread is not None:
            self.logger.debug(f"""stopping acquisition thread with 
                            thread-ID {self._acquisition_thread.ident}""")
            self._run = False # break infinite loop
            self._acquisition_thread.join()
            self._acquisition_thread = None 

if __name__ == '__main__':
    spectrometer = OceanOpticsSpectrometer(instance_name='spectrometer', 
                        serial_number='S14155', autoconnect=True, 
                        log_level=logging.DEBUG)
    spectrometer.run_with_http_server(port=3569)
