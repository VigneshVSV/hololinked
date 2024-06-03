from hololinked.server import Thing, Property, action, Event
from hololinked.server.properties import String, List
from seabreeze.spectrometers import Spectrometer


class OceanOpticsSpectrometer(Thing):
    """
    Spectrometer example object 
    """

    serial_number = String(default=None, allow_None=True, constant=True, 
                        URL_path='/serial-number',
                        doc="serial number of the spectrometer") # type: str

    def __init__(self, instance_name, serial_number, autoconnect, **kwargs):
        super().__init__(instance_name=instance_name, **kwargs)
        self.serial_number = serial_number
        if autoconnect and self.serial_number is not None:
            self.connect()
        self.measurement_event = Event(name='intensity-measurement')

    @action(URL_path='/connect')
    def connect(self, trigger_mode = None, integration_time = None):
        self.device = Spectrometer.from_serial_number(self.serial_number)
        if trigger_mode:
            self.device.trigger_mode(trigger_mode)
        if integration_time:
            self.device.integration_time_micros(integration_time)
              
    intensity = List(default=None, allow_None=True, doc="captured intensity", 
                    readonly=True, fget=lambda self: self._intensity.tolist())       

    @action(URL_path='/capture')
    def capture(self):
        self._run = True 
        while self._run:
            self._intensity = self.device.intensities(
                                        correct_dark_counts=True,
                                        correct_nonlinearity=True
                                    )
            self.measurement_event.push(self._intensity.tolist())

    
if __name__ == '__main__':
    spectrometer = OceanOpticsSpectrometer(instance_name='spectrometer', 
                        serial_number='USB2+H15897', autoconnect=True)
    spectrometer.run_with_http_server(port=3569)
