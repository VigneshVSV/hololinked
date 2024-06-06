from oceanoptics_spectrometer import OceanOpticsSpectrometer
from IDSCamera import UEyeCamera
from hololinked.server import EventLoop, HTTPServer
from multiprocessing import Process


def start_http_server():
    server = HTTPServer(remote_objects=['spectrometer', 'eventloop'])
    server.start()

if __name__ == '__main__()':
        
    Process(target=start_http_server).start()
    
    EventLoop(
        OceanOpticsSpectrometer(instance_name='spectrometer', 
                        serial_number='USB2+H15897'),
        instance_name='eventloop',
    ).run()