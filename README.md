# hololinked

### Description

For beginners - `hololinked` is a server side pythonic package suited for instrumentation control and data acquisition over network.
For those familiar with RPC & web development - `hololinked` is a ZeroMQ-based Object Oriented RPC toolkit with customizable HTTP end-points. 
The main goal is to develop a pythonic & pure python modern package for instrumentation control through network (SCADA), along with "reasonable" HTTP support for web development.  

This package can also be used for general RPC for other applications.  

### Usage

`hololinked` is compatible with the [Web of Things](https://www.w3.org/WoT/) recommended pattern for developing hardware/instrumentation control software. Each device or thing can be controlled systematically when their design in software is segregated into properties, actions and events. In object oriented terms:
- properties are get-set attributes of the class which may be used be used to model device settings, hold captured data etc.
- actions are methods which issue commands to the device or run arbitrary python logic. 
- events can asynchronously communicate/push data to a client, like alarm messages, streaming captured data etc. 

The base class which enables this classification is the ``RemoteObject`` class in native ``hololinked`` terms, or the ``Thing`` class if one prefers to use terminology according to the Web of Things. Both classes are identical and differentiated only in the naming according the application domain one may be using. If one deploys a pure RPC application, one may chose the name ``RemoteObject``, and if one writes classes to control instrumentation (which is the main purpose of this package), one may use the ``Thing`` class (in future one of names may be dropped).

Any class that inherits the base class can instantiate properties, actions and events which become visible to a client in this segragated manner. For example, consider a spectrometer device, the following code is possible:

###### Import Statements

```python
from hololinked.wot import Thing
from hololinked.wot.actions import action
from hololinked.wot.properties import String, Integer, Number, List
from hololinked.wot.events import Event
```
###### Definition of one's own hardware controlling class

```python 

class OceanOpticsSpectrometer(Thing):
    """
    OceanOptics spectrometers using seabreeze library. Device is identified with specifying serial number. 
    """
    
```

###### Instantiating properties

```python

class OceanOpticsSpectrometer(Thing):

    def __init__(self, instance_name, serial_number, **kwargs):
        super().__init__(instance_name=instance_name, serial_number=serial_number, **kwargs)

    serial_number = String(default=None, allow_None=True, URL_path='/serial-number', 
                        doc="serial number of the spectrometer to connect/or connected",
                        http_method=("GET", "PUT"))
    # GET and PUT is for read and write respectively & default

    integration_time = Number(default=1000, bounds=(0.001, None), crop_to_bounds=True, 
                            URL_path='/integration-time', 
                            doc="integration time of measurement in milliseconds")

    intensity = List(default=None, allow_None=True, 
                    doc="captured intensity", readonly=True, 
                    fget=lambda self: self._intensity)     

```

###### Specify methods as actions & overload property get-set if necessary

```python

class OceanOpticsSpectrometer(Thing):

    @action(URL_path='/connect', http_method="POST") # POST is default for actions
    def connect(self, serial_number = None):
        if serial_number is not None:
            self.serial_number = serial_number
        self.device = Spectrometer.from_serial_number(self.serial_number)
        self._wavelengths = self.device.wavelengths().tolist()

    @integration_time.setter 
    def apply_integration_time(self, value : float):
        self.device.integration_time_micros(int(value*1000))
        self._integration_time = int(value) 
      
    @integration_time.getter 
    def get_integration_time(self) -> float:
        try:
            return self._integration_time
        except:
            return self.properties["integration_time"].default 

```
###### Defining and pushing events

```python

    def __init__(self, instance_name, serial_number, **kwargs):
        super().__init__(instance_name=instance_name, serial_number=serial_number, **kwargs)
        self.measurement_event = Event(name='intensity-measurement', URL_path='/intensity/measurement-event')) # only GET possible for events

    def capture(self):
        self._run = True 
        while self._run:
            self._intensity = self.device.intensities(
                                        correct_dark_counts=True,
                                        correct_nonlinearity=True
                                    )
            self.measurement_event.push(self._intensity.tolist())

    @action(URL_path='/acquisition/start', http_method="POST")
    def start_acquisition(self):
        self._acquisition_thread = threading.Thread(target=self.measure) 
        self._acquisition_thread.start()

    @action(URL_path='/acquisition/stop', http_method="POST")
    def stop_acquisition(self):
        self._run = False 
```

``hololinked``, although the very familiar & age-old RPC server, affords to directly specify HTTP methods and URL path for each property, action and event. A configurable HTTP Server is already available which redirects HTTP requests according to the specified HTTP API on the properties, actions and events to the object. The intention is to eliminate the need to implement a detailed HTTP server (& its API) which could interact with a hardware and stick to object oriented coding.
The redirection is mediated by ZeroMQ which also implements a fully fledged RPC that serializes all the HTTP requests to execute them one-by-one on the hardware. Obviously, this is useful for hardware which demands that only one command be issued at a time. For other types hardware that may exist which supports multiple requests, one may not benefit from this.  

To plug in a HTTP server: 

```python
from multiprocessing import Process
from hololinked.server import HTTPServer

def start_http_server():
    HTTPServer(
        remote_objects=['spectrometer'], 
        port=8083,
        log_level=logging.DEBUG
    ).listen()


if __name__ == "__main__":
   
    Process(target=start_https_server).start()
  
    OceanOpticsSpectrometer(
        instance_name='spectrometer',
        serial_number='S14155',
        log_level=logging.DEBUG
    ).run()

```

One may use the HTTP API according to one's beliefs although it is mainly intended for web development and cross platform clients like the interoperable [node-wot](https://github.com/eclipse-thingweb/node-wot) client.    
To know more about client side scripting, please look into the documentation [How-To](https://hololinked.readthedocs.io/en/latest/howto/index.html) section.

##### NOTE - The package is under development. Contributors welcome. 


[![Documentation Status](https://readthedocs.org/projects/hololinked/badge/?version=latest)](https://hololinked.readthedocs.io/en/latest/?badge=latest)

[![Maintainability](https://api.codeclimate.com/v1/badges/913f4daa2960b711670a/maintainability)](https://codeclimate.com/github/VigneshVSV/hololinked/maintainability)

- [example repository](https://github.com/VigneshVSV/hololinked-examples)
- [helper GUI](https://github.com/VigneshVSV/hololinked-portal) - view & interact with your object's methods, properties and events. 
- [web development examples](https://hololinked.dev/docs/category/spectrometer-gui)

### Currently Supported

- indicate HTTP verb & URL path directly on object's methods, properties and events.
- auto-generate Thing Description for Web of Things applications (inaccurate, being continuously developed but usable). 
- control method execution and property write with a custom finite state machine.
- database (Postgres, MySQL, SQLite - based on SQLAlchemy) support for storing and loading properties  when object dies and restarts. 
- use serializer of your choice (except for HTTP) - MessagePack, JSON, pickle etc. & extend serialization to suit your requirement (HTTP Server will support only JSON serializer). Default is JSON serializer based on msgspec.
- asyncio compatible - async RPC server event-loop and async HTTP Server - write methods in async 
- have flexibility in process architecture - run HTTP Server & python object in separate processes or in the same process, combine multiple objects in same server etc. 
- choose from multiple ZeroMQ Transport methods - TCP for direct network access (apart from HTTP), IPC for multi-process same-PC applications, INPROC for multi-threaded applications. 

Again, please check examples or the code for explanations. Documentation is being activety improved. 

### To Install

clone the repository and install in develop mode `pip install -e .` for convenience. The conda env hololinked.yml can also help. 
There is no release to pip available right now.  

### Some Day In Future

- HTTP 2.0 


### Contact

Contributors welcome for all my projects related to hololinked including web apps. Please write to my contact email available at [website](https://hololinked.dev).

### Disclaimer

This package is in no way endorsed by Web of Things Community and is also not a reference implementation or intends to be one.


