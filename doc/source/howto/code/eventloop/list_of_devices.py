from oceanoptics_spectrometer import OceanOpticsSpectrometer
from IDSCamera import UEyeCamera
from hololinked.server import EventLoop, HTTPServer
from multiprocessing import Process


def start_http_server():
    server = HTTPServer(remote_objects=['spectrometer', 'eventloop', 'camera'])
    server.start()

if __name__ == '__main__()':
        
    Process(target=start_http_server).start()
        
    spectrometer = OceanOpticsSpectrometer(instance_name='spectrometer', 
                        serial_number='USB2+H15897')
    
    camera = UEyeCamera(instance_name='camera', camera_id=3)

    EventLoop(
        [spectrometer, camera],
        instance_name='eventloop',
    ).run()