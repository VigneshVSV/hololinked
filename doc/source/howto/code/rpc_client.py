from hololinked.client import ObjectProxy

spectrometer_proxy = ObjectProxy(instance_name='spectrometer', protocol='IPC') 
# setting and getting property
spectrometer_proxy.serial_number = 'USB2+H15897'
print(spectrometer_proxy.serial_number)
# calling actions
spectrometer_proxy.connect()
spectrometer_proxy.capture()

exit(0)

# TCP and event example
from hololinked.client import ObjectProxy
from oceanoptics_spectrometer import OceanOpticsSpectrometer

spectrometer_proxy = ObjectProxy(instance_name='spectrometer', protocol='TCP', 
        socket_address="tcp://192.168.0.100:6539") # type: OceanOpticsSpectrometer
spectrometer_proxy.serial_number = 'USB2+H15897'
spectrometer_proxy.connect() # provides type definitions corresponding to server

def event_cb(event_data):
    print(event_data)

spectrometer_proxy.subscribe_event(name='intensity-measurement', callbacks=event_cb)
# name can be the value for name given to the event in the server side or the 
# python attribute where the Event was assigned.
