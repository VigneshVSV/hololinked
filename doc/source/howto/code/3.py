from hololinked.client import ObjectProxy

spectrometer_proxy = ObjectProxy(instance_name='spectrometer', 
                        protocol='IPC') 
spectrometer_proxy.serial_number = 'USB2+H15897'
spectrometer_proxy.connect()
spectrometer_proxy.capture()

"""
assumption - 
1. one didnt set the serial number and 
automatically connect on the server side.

2. Interprocess message transport (IPC) so that this script can be
independtly executed on the same computer. Use TCP for network calls. 
"""

from hololinked.client import ObjectProxy
from OceanOpticsSpectrometer import OceanOpticsSpectrometer

spectrometer_proxy = ObjectProxy(instance_name='spectrometer', 
                        protocol='IPC') # type: OceanOpticsSpectrometer
spectrometer_proxy.connect() # provides type definitions corresponding to server