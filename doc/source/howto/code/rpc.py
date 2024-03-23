from hololinked.server import RemoteObject, remote_method, Event
from hololinked.server.remote_parameters import String, ClassSelector
from seabreeze.spectrometers import Spectrometer
import numpy 

class OceanOpticsSpectrometer(RemoteObject):
    """
    Spectrometer example object 
    """

    serial_number = String(default=None, allow_None=True, constant=True, 
                        doc="serial number of the spectrometer") # type: str

    def __init__(self, instance_name, serial_number, connect, **kwargs):
        super().__init__(instance_name=instance_name, **kwargs)
        self.serial_number = serial_number
        if connect and self.serial_number is not None:
            self.connect()
        self.measurement_event = Event(name='intensity-measurement')

    @remote_method()
    def connect(self, trigger_mode = None, integration_time = None):
        self.device = Spectrometer.from_serial_number(self.serial_number)
        if trigger_mode:
            self.device.trigger_mode(trigger_mode)
        if integration_time:
            self.device.integration_time_micros(integration_time)
              
    intensity = ClassSelector(class_=(numpy.ndarray, list), default=[], 
                    doc="captured intensity", readonly=True, 
                    fget=lambda self: self._intensity)       

    def capture(self):
        self._run = True 
        while self._run:
            self._intensity = self.device.intensities(
                                        correct_dark_counts=True,
                                        correct_nonlinearity=True
                                    )
            self.measurement_event.push(self._intensity)

    
if __name__ == '__main__':
    spectrometer = OceanOpticsSpectrometer(instance_name='spectrometer', 
                        serial_number='USB2+H15897', connect=True)
    spectrometer.run()
