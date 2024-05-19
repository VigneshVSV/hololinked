# hololinked

### Description

For beginners - `hololinked` is a server side pythonic package suited for instrumentation control and data acquisition over network.
<br/>
For those familiar with RPC & web development - `hololinked` is a ZeroMQ-based Object Oriented RPC toolkit with customizable HTTP end-points. 
The main goal is to develop a pythonic & pure python modern package for instrumentation control through network (SCADA), along with "reasonable" HTTP support for web development.  

This package can also be used for general RPC for other applications.  

### Usage

`hololinked` is compatible with the [Web of Things](https://www.w3.org/WoT/) recommended pattern for developing hardware/instrumentation control software. Each device or thing can be controlled systematically when their design in software is segregated into properties, actions and events. In object oriented terms for data acquisition:
- properties are validated get-set attributes of the class which may be used be used to model device settings, hold captured/computed data etc.
- actions are methods which issue commands to the device or run arbitrary python logic. 
- events can asynchronously communicate/push data to a client, like alarm messages, streaming captured data etc. 

In `hololinked`, the base class which enables this classification is the `RemoteObject` class, or the `Thing` class if one prefers to use terminology according to the Web of Things. Both classes are identical and differentiated only in the naming according to the application domain one may be using. In future one of the names may be dropped. Nevertheless, any class that inherits the base class can instantiate properties, actions and events which become visible to a client in this segragated manner. For example, consider an optical spectrometer device, the following code is possible:

##### Import Statements

```python
from hololinked.wot import Thing
from hololinked.wot.actions import action
from hololinked.wot.properties import String, Integer, Number, List
from hololinked.wot.events import Event
```
##### Definition of one's own hardware controlling class

subclass from Thing class to "make a Thing":

```python 

class OceanOpticsSpectrometer(Thing):
    """
    OceanOptics spectrometers using seabreeze library. Device is identified with specifying serial number. 
    """
    
```

##### Instantiating properties

There are certain predefined properties available like `String`, `Number`, `Boolean` etc. 
(or one may define one's own). To create properties:

```python

class OceanOpticsSpectrometer(Thing):
    """class doc"""
    
    serial_number = String(default=None, allow_None=True, URL_path='/serial-number', 
                        doc="serial number of the spectrometer to connect/or connected",
                        http_method=("GET", "PUT"))
    # GET and PUT is for read and write the property respectively & default. Use other HTTP methods if necessary.  

    integration_time = Number(default=1000, bounds=(0.001, None), crop_to_bounds=True, 
                            URL_path='/integration-time', 
                            doc="integration time of measurement in milliseconds")

    intensity = List(default=None, allow_None=True, 
                    doc="captured intensity", readonly=True, 
                    fget=lambda self: self._intensity)     

    def __init__(self, instance_name, serial_number, **kwargs):
        super().__init__(instance_name=instance_name, serial_number=serial_number, **kwargs)

```

For those unfamiliar with the above syntax, Properties look like class attributes however their data containers are instantiated at object instance level by default.
For example, the `integratime_time` property defined above as `Number`, whenever set, will be validated as a float or int, cropped to bounds and assigned as an attribute to each instance of the `OceanOpticsSpectrometer` class with an internally generated name. It is not necessary to know this internally generated name, as the property value can be accessed again by `self.integration_time` in any python logic. This is facilitated by the python descriptor protocol. Please do not confuse this with the `property` from python's own namespace although the functionality and purpose are identical. Python's built-in `property` are not given network access unlike the properties imported from `hololinked`. 

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
        except:
            return self.properties["integration_time"].default 

```

In this case, instead of generating an internal container, the setter method is called when `integration_time` property is set. One might add the hardware commanding logic to apply the property onto the device here. 

Further, those familiar with Web of Things (WoT) terminology may note that these properties generate the property affordance schema to become accessible by the [node-wot](https://github.com/eclipse-thingweb/node-wot) client. It is recommended to strictly use JSON compliant types for most non-speed critical applications, or register type replacements for converting non-JSON to JSON. These possibilities are discussed in the docs. An example of generated property affordance for `integration_time` is as follows:

```JSON
"integration_time": {
    "title": "integration_time",
    "description": "integration time of measurement in milliseconds",
    "constant": false,
    "readOnly": false,
    "writeOnly": false,
    "type": "number",
    "forms": [{
            "href": "https://LAPTOP-F60CU35D:8083/spectrometer/integration-time",
            "op": "readproperty",
            "htv:methodName": "GET",
            "contentType": "application/json"
        },{
            "href": "https://LAPTOP-F60CU35D:8083/spectrometer/integration-time",
            "op": "writeproperty",
            "htv:methodName": "PUT",
            "contentType": "application/json"
        }
    ],
    "observable": false,
    "minimum": 0.001
},
```
The usage for Web of Things applications will be more systematically discussed in How-Tos for the beginner. The URL path 'spectrometer' in href field is taken from the `instance_name` which was specified in the `__init__`. This is a mandatory key word argument to the parent class `Thing` to generate a unique name for the instance. 
One should use URI compatible strings. 

##### Specify methods as actions

decorate with `action` decorator on a python method to claim it as a network accessible method or action:

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

Methods that are neither get-set of properties nor decorated with action decorator remain as plain python methods and are not accessible on the network.

In WoT Terminology, again, such a method becomes specified as an action affordance:

```JSON
"connect": {
    "title": "connect",
    "description": "connect to spectrometer with given serial number",
    "forms": [
        {
            "href": "https://LAPTOP-F60CU35D:8083/spectrometer/connect",
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

###### Defining and pushing events

create a named using `Event` object that can push any arbitrary data:

```python

    def __init__(self, instance_name, serial_number, **kwargs):
        super().__init__(instance_name=instance_name, serial_number=serial_number, **kwargs)
        self.measurement_event = Event(name='intensity-measurement', URL_path='/intensity/measurement-event')) # only GET HTTP method possible for events

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

in WoT Terminology, such an event becomes specified as an event affordance with subprotocol 'SSE':

```JSON
"intensity_measurement_event": {
    "forms": [
        {
            "href": "https://LAPTOP-F60CU35D:8083/spectrometer/intensity/measurement-event",
            "subprotocol": "sse",
            "op": "subscribeevent",
            "htv:methodName": "GET",
            "contentType": "text/event-stream"
        }
    ]
}

```

Although the very familiar & age-old RPC server style code, one can directly specify HTTP methods and URL path for each property, action and event. A configurable HTTP Server is already available (from `hololinked.server.HTTPServer`) which redirects HTTP requests to the object according to the specified HTTP API on the properties, actions and events. To plug in a HTTP server: 

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
Here one can see the use of ``instance_name``.

The intention of this feature is to eliminate the need to implement a detailed HTTP server (& its API) which generally poses problems in serializing commands issued to instruments, or write an additional bioler-plate HTTP to RPC bridge, or find a reasonable HTTP-RPC implementation which supports all three of properties, actions and events, yet appeals deeply to the object oriented python world. See a list of currently supported features [below](#currently-supported). <br/>
Ultimately, as expected, the redirection from the HTTP side to the object is mediated by ZeroMQ which implements the fully fledged RPC that queues all the HTTP requests to execute them one-by-one on the hardware/object. The HTTP server can also communicate with the RPC server over ZeroMQ's INPROC (intra-process) or IPC (inter-process) transport methods (which is used by default for the example above). There is no need for yet another TCP from HTTP to TCP to ZeroMQ transport athough this is also supported. <br/>
Serialization-Deserilization overheads are already reduced. For example, when pushing an event from the object which gets automatically tunneled as a HTTP SSE or returning a reply for an action from the object, there is no JSON deserilization-serilization overhead when the message passes through the HTTP server. The message is serialized once on the object side but passes transparently through the HTTP server.     

One may use the HTTP API according to one's beliefs (including letting the package auto-generate it as one may not care), although it is mainly intended for web development and cross platform clients like the interoperable [node-wot](https://github.com/eclipse-thingweb/node-wot) client. The node-wot client is the recommended Javascript client for this package as one can seamlessly plugin code developed from this package to the rest of the IoT tools, protocols & standardizations, or do scripting on the browser or nodeJS. Please check node-wot docs on how to consume [Thing Descriptions](https://www.w3.org/TR/wot-thing-description11) to call actions, read & write properties or subscribe to events. A Thing Description will be automatically generated if absent as shown in JSON examples above or can be supplied manually. 
To know more about client side scripting, please look into the documentation [How-To](https://hololinked.readthedocs.io/en/latest/howto/index.html) section.

##### NOTE - The package is under development. Contributors welcome. 


[![Documentation Status](https://readthedocs.org/projects/hololinked/badge/?version=latest)](https://hololinked.readthedocs.io/en/latest/?badge=latest)

[![Maintainability](https://api.codeclimate.com/v1/badges/913f4daa2960b711670a/maintainability)](https://codeclimate.com/github/VigneshVSV/hololinked/maintainability)

- [example repository](https://github.com/VigneshVSV/hololinked-examples)
- [helper GUI](https://github.com/VigneshVSV/hololinked-portal) - view & interact with your object's methods, properties and events. 
- [web development examples](https://hololinked.dev/docs/category/spectrometer-gui)

### Currently Supported

- indicate HTTP verb & URL path directly on object's methods, properties and events.
- control method execution and property write with a custom finite state machine.
- database (Postgres, MySQL, SQLite - based on SQLAlchemy) support for storing and loading properties  when object dies and restarts. 
- auto-generate Thing Description for Web of Things applications (inaccurate, continuously developed but usable). 
- use serializer of your choice (except for HTTP) - MessagePack, JSON, pickle etc. & extend serialization to suit your requirement. HTTP Server will support only JSON serializer to maintain compatibility with node-wot. Default is JSON serializer based on msgspec.
- asyncio compatible - async RPC server event-loop and async HTTP Server - write methods in async 
- have flexibility in process architecture - run HTTP Server & python object in separate processes or in the same process, serve multiple objects with same HTTP server etc. 
- choose from multiple ZeroMQ transport methods - TCP for direct network access (apart from HTTP), IPC for multi-process same-PC applications (like shown in example above), INPROC for multi-threaded applications. 

Again, please check examples or the code for explanations. Documentation is being activety improved. 

### To Install

clone the repository and install in develop mode `pip install -e .` for convenience. The conda env hololinked.yml can also help. 
There is no release to pip available right now.  

### Currently being worked

- observable properties and read/write multiple properties through node-wot client
- argument schema validation for actions (you can specify one but its not used)
- credentials for authentication 
- improving accuracy of Thing Descriptions 

### Some Day In Future

- mongo DB support for DB operations
- HTTP 2.0 

### Contact

Contributors welcome for all my projects related to hololinked including web apps. Please write to my contact email available at [website](https://hololinked.dev).







