# hololinked

### Description

For beginners - `hololinked` is a server side pythonic package suited for instrumentation control and data acquisition over network, especially with HTTP. If you have a requirement to control and capture data from your hardware/instrumentation remotely through your network, show the data in a web browser/dashboard, use IoT tools, provide a Qt-GUI or run automated scripts, hololinked can help. One can start small from a single device, and if interested, move ahead to build a bigger system made of individual components. 
<br/> <br/>
For those familiar with RPC & web development - `hololinked` is a ZeroMQ-based Object Oriented RPC toolkit with customizable HTTP end-points. 
The main goal is to develop a pythonic & pure python modern package for instrumentation control and data acquisition through network (SCADA), along with "reasonable" HTTP support for web development.  

[![Documentation Status](https://readthedocs.org/projects/hololinked/badge/?version=latest)](https://hololinked.readthedocs.io/en/latest/?badge=latest) [![Maintainability](https://api.codeclimate.com/v1/badges/913f4daa2960b711670a/maintainability)](https://codeclimate.com/github/VigneshVSV/hololinked/maintainability) ![PyPI](https://img.shields.io/pypi/v/hololinked?label=pypi%20package) ![PyPI - Downloads](https://img.shields.io/pypi/dm/hololinked)

### To Install

From pip - ``pip install hololinked``

Or, clone the repository and install in develop mode `pip install -e .` for convenience. The conda env hololinked.yml can also help. 


### Usage/Quickstart

`hololinked` is compatible with the [Web of Things](https://www.w3.org/WoT/) recommended pattern for developing hardware/instrumentation control software. Each device or thing can be controlled systematically when their design in software is segregated into properties, actions and events. In object oriented terms for data acquisition:
- properties are validated get-set attributes of the class which may be used to model device settings, hold captured/computed data etc.
- actions are methods which issue commands to the device or run arbitrary python logic. 
- events can asynchronously communicate/push data to a client, like alarm messages, streaming captured data etc. 

In `hololinked`, the base class which enables this classification is the `Thing` class. Any class that inherits the `Thing` class can instantiate properties, actions and events which become visible to a client in this segragated manner. For example, consider an optical spectrometer device, the following code is possible:

#### Import Statements

```python

from hololinked.server import Thing, Property, action, Event
from hololinked.server.properties import String, Integer, Number, List
```

#### Definition of one's own hardware controlling class

subclass from Thing class to "make a network accessible Thing":

```python 

class OceanOpticsSpectrometer(Thing):
    """
    OceanOptics spectrometers using seabreeze library. Device is identified by serial number. 
    """
    
```

#### Instantiating properties

Say, we wish to make device serial number, integration time and the captured intensity as properties. There are certain predefined properties available like `String`, `Number`, `Boolean` etc. 
or one may define one's own. To create properties:

```python

class OceanOpticsSpectrometer(Thing):
    """class doc"""
    
    serial_number = String(default=None, allow_None=True, URL_path='/serial-number', 
                        doc="serial number of the spectrometer to connect/or connected",
                        http_method=("GET", "PUT"))
    # GET and PUT is default for reading and writing the property respectively. 
    # Use other HTTP methods if necessary.  

    integration_time = Number(default=1000, bounds=(0.001, None), crop_to_bounds=True, 
                            URL_path='/integration-time', 
                            doc="integration time of measurement in milliseconds")

    intensity = List(default=None, allow_None=True, 
                    doc="captured intensity", readonly=True, 
                    fget=lambda self: self._intensity)     

    def __init__(self, instance_name, serial_number, **kwargs):
        super().__init__(instance_name=instance_name, serial_number=serial_number, **kwargs)

```

In non-expert terms, properties look like class attributes however their data containers are instantiated at object instance level by default.
For example, the `integratime_time` property defined above as `Number`, whenever set/written, will be validated as a float or int, cropped to bounds and assigned as an attribute to each instance of the `OceanOpticsSpectrometer` class with an internally generated name. It is not necessary to know this internally generated name as the property value can be accessed again in any python logic, say, `print(self.integration_time)`. 

To overload the get-set (or read-write) of properties, one may do the following:

```python
class OceanOpticsSpectrometer(Thing):

    integration_time = Number(default=1000, bounds=(0.001, None), crop_to_bounds=True, 
                            URL_path='/integration-time', 
                            doc="integration time of measurement in milliseconds")

    @integration_time.setter # by default called on http PUT method
    def apply_integration_time(self, value : float):
        self.device.integration_time_micros(int(value*1000))
        self._integration_time = int(value) 
      
    @integration_time.getter # by default called on http GET method
    def get_integration_time(self) -> float:
        try:
            return self._integration_time
        except AttributeError:
            return self.properties["integration_time"].default 

```

In this case, instead of generating a data container with an internal name, the setter method is called when `integration_time` property is set/written. One might add the hardware device driver (say, supplied by the manufacturer) logic here to apply the property onto the device. In the above example, there is not a way provided by lower level library to read the value from the device, so we store it in a variable after applying it and supply the variable back to the getter method. Normally, one would also want the getter to read from the device directly.
 
Those familiar with Web of Things (WoT) terminology may note that these properties generate the property affordance schema to become accessible by the [node-wot](https://github.com/eclipse-thingweb/node-wot) client. An example of autogenerated property affordance for `integration_time` is as follows:

```JSON
"integration_time": {
    "title": "integration_time",
    "description": "integration time of measurement in milliseconds",
    "constant": false,
    "readOnly": false,
    "writeOnly": false,
    "type": "number",
    "forms": [{
            "href": "https://example.com/spectrometer/integration-time",
            "op": "readproperty",
            "htv:methodName": "GET",
            "contentType": "application/json"
        },{
            "href": "https://example.com/spectrometer/integration-time",
            "op": "writeproperty",
            "htv:methodName": "PUT",
            "contentType": "application/json"
        }
    ],
    "observable": false,
    "minimum": 0.001
},
```
The URL path segment `../spectrometer/..` in href field is taken from the `instance_name` which was specified in the `__init__`. This is a mandatory key word argument to the parent class `Thing` to generate a unique name/id for the instance. One should use URI compatible strings.

#### Specify methods as actions

decorate with `action` decorator on a python method to claim it as a network accessible method:

```python

class OceanOpticsSpectrometer(Thing):

    @action(URL_path='/connect', http_method="POST") # POST is default for actions
    def connect(self, serial_number = None):
        """connect to spectrometer with given serial number"""
        if serial_number is not None:
            self.serial_number = serial_number
        self.device = Spectrometer.from_serial_number(self.serial_number)
        self._wavelengths = self.device.wavelengths().tolist()
```

Methods that are neither decorated with action decorator nor acting as getters-setters of properties remain as plain python methods and are **not** accessible on the network.

In WoT Terminology, again, such a method becomes specified as an action affordance:

```JSON
"connect": {
    "title": "connect",
    "description": "connect to spectrometer with given serial number",
    "forms": [
        {
            "href": "https://example.com/spectrometer/connect",
            "op": "invokeaction",
            "htv:methodName": "POST",
            "contentType": "application/json"
        }
    ],
    "safe": true,
    "idempotent": false,
    "synchronous": true
},

```

#### Defining and pushing events

create a named event using `Event` object that can push any arbitrary data:

```python

    def __init__(self, instance_name, serial_number, **kwargs):
        super().__init__(instance_name=instance_name, serial_number=serial_number, **kwargs)
        self.measurement_event = Event(name='intensity-measurement',
                    URL_path='/intensity/measurement-event')) # only GET HTTP method possible for events

    def capture(self): # not an action, but a plain python method
        self._run = True 
        while self._run:
            self._intensity = self.device.intensities(
                                        correct_dark_counts=True,
                                        correct_nonlinearity=True
                                    )
            self.measurement_event.push(self._intensity.tolist())

    @action(URL_path='/acquisition/start', http_method="POST")
    def start_acquisition(self):
        self._acquisition_thread = threading.Thread(target=self.capture) 
        self._acquisition_thread.start()

    @action(URL_path='/acquisition/stop', http_method="POST")
    def stop_acquisition(self):
        self._run = False 
```

In WoT Terminology, such an event becomes specified as an event affordance with subprotocol SSE:

```JSON
"intensity_measurement_event": {
    "forms": [
        {
            "href": "https://example.com/spectrometer/intensity/measurement-event",
            "subprotocol": "sse",
            "op": "subscribeevent",
            "htv:methodName": "GET",
            "contentType": "text/event-stream"
        }
    ]
}

```

Although the code is the very familiar & age-old RPC server style, one can directly specify HTTP methods and URL path for each property, action and event. A configurable HTTP Server is already available (from `hololinked.server.HTTPServer`) which redirects HTTP requests to the object according to the specified HTTP API on the properties, actions and events. To plug in a HTTP server: 

```python
import ssl, os, logging
from multiprocessing import Process
from hololinked.server import HTTPServer

def start_https_server():
    # You need to create a certificate on your own 
    ssl_context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS)
    ssl_context.load_cert_chain(f'assets{os.sep}security{os.sep}certificate.pem',
                        keyfile = f'assets{os.sep}security{os.sep}key.pem')

    HTTPServer(['spectrometer'], port=8083, ssl_context=ssl_context, 
                      log_level=logging.DEBUG).listen()


if __name__ == "__main__":
   
    Process(target=start_https_server).start()
  
    OceanOpticsSpectrometer(
        instance_name='spectrometer',
        serial_number='S14155',
        log_level=logging.DEBUG
    ).run()

```
Here one can see the use of `instance_name` and why it turns up in the URL path.

The intention behind specifying HTTP URL paths and methods directly on object's members is to 
- eliminate the need to implement a detailed HTTP server (& its API) which generally poses problems in queueing commands issued to instruments
- or, write an additional boiler-plate HTTP to RPC bridge
- or, find a reasonable HTTP-RPC implementation which supports all three of properties, actions and events, yet appeals deeply to the object oriented python world. 

See a list of currently supported features [below](#currently-supported). <br/> <br/>
Ultimately, as expected, the redirection from the HTTP side to the object is mediated by ZeroMQ which implements the fully fledged RPC server that queues all the HTTP requests to execute them one-by-one on the hardware/object. The HTTP server can also communicate with the RPC server over ZeroMQ's INPROC (for the non-expert = multithreaded applications, at least in python) or IPC (for the non-expert = multiprocess applications) transport methods. In the example above, IPC is used by default. There is no need for yet another TCP from HTTP to TCP to ZeroMQ transport athough this is also supported. <br/> <br/>
Serialization-Deserialization overheads are also already reduced. For example, when pushing an event from the object which gets automatically tunneled as a HTTP SSE or returning a reply for an action from the object, there is no JSON deserialization-serialization overhead when the message passes through the HTTP server. The message is serialized once on the object side but passes transparently through the HTTP server.     

One may use the HTTP API according to one's beliefs (including letting the package auto-generate it), although it is mainly intended for web development and cross platform clients like the interoperable [node-wot](https://github.com/eclipse-thingweb/node-wot) client. The node-wot client is the recommended Javascript client for this package as one can seamlessly plugin code developed from this package to the rest of the IoT tools, protocols & standardizations, or do scripting on the browser or nodeJS. Please check node-wot docs on how to consume [Thing Descriptions](https://www.w3.org/TR/wot-thing-description11) to call actions, read & write properties or subscribe to events. A Thing Description will be automatically generated if absent as shown in JSON examples above or can be supplied manually. 
To know more about client side scripting, please look into the documentation [How-To](https://hololinked.readthedocs.io/en/latest/howto/index.html) section.

##### NOTE - The package is under active development. Contributors welcome. 

- [example repository](https://github.com/VigneshVSV/hololinked-examples) - detailed examples for both clients and servers
- [helper GUI](https://github.com/VigneshVSV/hololinked-portal) - view & interact with your object's methods, properties and events. 

### Currently Supported

- indicate HTTP verb & URL path directly on object's methods, properties and events.
- control method execution and property write with a custom finite state machine.
- database (Postgres, MySQL, SQLite - based on SQLAlchemy) support for storing and loading properties  when object dies and restarts. 
- auto-generate Thing Description for Web of Things applications (inaccurate, continuously developed but usable). 
- use serializer of your choice (except for HTTP) - MessagePack, JSON, pickle etc. & extend serialization to suit your requirement. HTTP Server will support only JSON serializer to maintain compatibility with node-wot. Default is JSON serializer based on msgspec.
- asyncio compatible - async RPC server event-loop and async HTTP Server - write methods in async 
- have flexibility in process architecture - run HTTP Server & python object in separate processes or in the same process, serve multiple objects with same HTTP server etc. 
- choose from multiple ZeroMQ transport methods. 

Again, please check examples or the code for explanations. Documentation is being activety improved. 

### Currently being worked

- improving accuracy of Thing Descriptions 
- observable properties and read/write multiple properties through node-wot client
- argument schema validation for actions (you can specify one but its not used)
- credentials for authentication 

### Some Day In Future

- mongo DB support for DB operations
- HTTP 2.0 

### Contact

Contributors welcome for all my projects related to hololinked including web apps. Please write to my contact email available at my [website](https://hololinked.dev). The contributing file is currently only boilerplate and need not be adhered. 







