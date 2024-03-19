import typing
from hololinked.client import ObjectProxy
from oceanoptics_spectrometer import OceanOpticsSpectrometer

spectrometer_proxy = ObjectProxy(instance_name='spectrometer', protocol='TCP', 
        socket_address="tcp://192.168.0.100:60000") # type: OceanOpticsSpectrometer
spectrometer_proxy.connect() # provides type definitions corresponding to server

def event_cb(event_data):
    print(event_data)

spectrometer_proxy.subscribe_event('intensity-measurement', event_cb)