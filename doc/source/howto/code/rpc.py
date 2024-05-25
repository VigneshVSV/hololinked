import logging, os, ssl
from multiprocessing import Process
from hololinked.server import HTTPServer, Thing, Property, action, Event
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


def start_https_server():
    ssl_context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS)
    ssl_context.load_cert_chain(f'assets{os.sep}security{os.sep}certificate.pem',
                        keyfile = f'assets{os.sep}security{os.sep}key.pem')
    # You need to create a certificate on your own or use without one 
    # for quick-start but events will not be supported by browsers 
    # if there is no SSL

    HTTPServer(['spectrometer'], port=8083, ssl_context=ssl_context, 
                      log_level=logging.DEBUG).listen()


if __name__ == "__main__":
   
    Process(target=start_https_server).start()
    
    spectrometer = OceanOpticsSpectrometer(instance_name='spectrometer', 
                        serial_number=None, autoconnect=False)
    spectrometer.run(zmq_protocols="IPC")

    # example code, but will never reach here unless exit() is called by the client
    spectrometer = OceanOpticsSpectrometer(instance_name='spectrometer', 
                        serial_number=None, autoconnect=False)
    spectrometer.run(zmq_protocols=["TCP", "IPC"], 
                    tcp_socket_address="tcp://0.0.0.0:6539")