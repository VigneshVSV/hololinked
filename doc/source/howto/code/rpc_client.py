from hololinked.client import ObjectProxy

spectrometer_proxy = ObjectProxy(instance_name='spectrometer', 
                        protocol='IPC') 
spectrometer_proxy.serial_number = 'USB2+H15897'
spectrometer_proxy.connect()
spectrometer_proxy.capture()

"""
assumption - 
1. one didnt set the serial number and 
automatically connect to the device on the server side.

2. Interprocess message transport (IPC) is used so that this script can be
independtly executed on the same computer. Use TCP for network calls. 

spectrometer_proxy = ObjectProxy(instance_name='spectrometer', 
                        protocol='TCP', socket_address="tcp://192.168.0.100:60000") 
                        # for example 
"""

from hololinked.client import ObjectProxy
from oceanoptics_spectrometer import OceanOpticsSpectrometer

spectrometer_proxy = ObjectProxy(instance_name='spectrometer', protocol='TCP', 
        socket_address="tcp://192.168.0.100:60000") # type: OceanOpticsSpectrometer
spectrometer_proxy.connect() # provides type definitions corresponding to server

def event_cb(event_data):
    print(event_data)

spectrometer_proxy.subscribe_event('intensity-measurement', event_cb)