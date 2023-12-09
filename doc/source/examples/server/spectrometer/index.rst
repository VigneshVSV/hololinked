.. |module| replace:: hololinked
 
.. |module-highlighted| replace:: ``hololinked``

.. |remote-paramerter-import-highlighted| replace:: ``hololinked.server.remote_parameters``

.. |br| raw:: html

    <br />

Spectrometer
============

Consider you have an optical spectrometer & you need the following options to control it:

* connect & disconnect from the instrument
* capture spectrum data 
* change measurement settings like integration time, trigger mode etc. 

We start by creating an object class as a sublcass of ``RemoteObject``. 
In this example, OceanSight USB2000+ spectrometer is used, which has a python high level wrapper
called `seabreeze <https://python-seabreeze.readthedocs.io/en/latest/>`_.

.. code-block:: python 
    :caption: device.py 
    
    from hololinked.server import RemoteObject
    from seabreeze.spectrometers import Spectrometer


    class OceanOpticsSpectrometer(RemoteObject):
        """
        Connect to OceanOptics spectrometers using seabreeze library by specifying serial number. 
        """

The spectrometers are identified by a serial number, which needs to be a string. By default, lets allow this `serial_number` to be ``None`` when invalid, 
passed in via the constructor & autoconnect when the object is initialised with a valid serial number. To ensure that the serial number is complied to a string whenever accessed by a client 
on the network, we need to use a parameter type defined in |remote-paramerter-import-highlighted|. By default, |module-highlighted|
defines a few types of remote parameters/attributes like Number (float or int), String, Date etc. 
The exact meaning and definitions are found in the :ref:`API Reference <apiref>` and is copied from `param <https://param.holoviz.org/>`_. 


.. code-block:: python 
    :emphasize-lines: 2

    ...
    from hololinked.server.remote_parameters import String

    class OceanOpticsSpectrometer(RemoteObject):
        ... 

        serial_number = String(default=None, allow_None=True, URL_path='/serial-number',
                    doc='serial number of the spectrometer to connect/control')

        model = String(default=None, allow_None=True, URL_path='/model',
                    doc='the model of the connected spectrometer')

        def __init__(self, serial_number : str, **kwargs):
            super().__init__(serial_number=serial_number, **kwargs)
            if serial_number is not None:
                self.connect()
            self._acquisition_thread = None 
            self._running = False


Each such parameter (like String, Number etc.) have their own list of arguments as seen above (``default``, ``allow_None``, ``doc``). 
Here we state that the default value of `serial_number` is ``None``, i.e. it accepts ``None`` although defined as a String and the URL_path where it should 
be accessible when served by a HTTP Server is '/serial-number'. Normally, such a parameter, when having a valid (non-None) value, 
will be forced to contain a string only. Moreover, although these parameters are defined at class-level (looks like a class 
attribute), unless the ``class_member=True`` is set on the parameter, its an instance attribute. This is due to the 
python `descriptor <https://realpython.com/python-descriptors/>`_ protocol. The same explanation applies to the `model` parameter, which
will be set from within the object during connection. 

The `URL_path` is interpreted as follows: First and foremost, you need to spawn a ``HTTPServer``. Second, such a HTTP Server
must talk to the OceanOpticsSpectrometer instance. To achieve this, the ``RemoteObject`` is instantiated with a specific 
``instance_name`` and the HTTP server is spawn with an argument containing the instance_name. (We still did not implement 
any methods like connect/disconnect etc.). When the HTTPServer can talk with the ``RemoteObject`` instance, the parameter becomes available at the stated `URL_path` along
with the prefix of the HTTP Server domain name and object instance name. 

.. code-block:: python 
    :emphasize-lines: 2

    ...
    from hololinked.server import HTTPServer
    import logging


    class OceanOpticsSpectrometer(RemoteObject):
        ... 

        model = String(default=None, allow_None=True, URL_path='/model',
                    doc='the model of the connected spectrometer')

    if __name__ == '__main__':
        H = HTTPServer(consumers=['spectrometer/ocean-optics/USB2000-plus'], port=8083, log_level=logging.DEBUG)  
        H.start(block=False) # creates a new process

        O = OceanOpticsSpectrometer(
            instance_name='spectrometer/ocean-optics/USB2000-plus',
            # a name for the instance of the object, since the same object can be instantiated with
            # a different name to control a different spectrometer
            serial_number='USB2+H15897',
            log_level=logging.DEBUG,
        )
        O.run()
To construct the full `URL_path`, the format is |br| 
`https://{domain name}/{instance name}/{parameter URL path}`, which gives |br| 
`https://localhost:8083/spectrometer/ocean-optics/USB2000-plus/serial-number` |br| for the `serial_number`. 

If your PC has a domain name, you can also use the domain name instead of `localhost`. Since the `instance_name` partipates as a prefix in the `URL path`, 
it is recommended to use a slash separated ('/') name complying to URL standards. 
A name with 0 slashes are also accepted & a leading slash will always be inserted after the domain name. Therefore, its not necessary 
to start the `instance_name` with a slash unlike the `URL_path`. 

To access the `serial_number`, once the example starts without errors, type the URL in the web browser to get a reply like the following:

.. code-block:: JSON 

    {
        "responseStatusCode" : 200,
        "returnValue" : "USB2+H15897",
        "state" : null
    }
    
The `returnValue` field contains the value obtained by running the python method, in this case python attribute 
getter of `serial_number`. The `state` field refers to the current state of the ``StateMachine`` which will be discussed later.
The `responseStatusCode` is the HTTP response status code (which might be dropped in further updates). 

To set the parameter remotely from a HTTP client, one needs to use the PUT HTTP method. 
HTTP defines certain 'verbs' like GET, POST, PUT, DELETE etc. Each verb can be used to mean a certain action at a specified URL (or resource representation), 
a list of which can be found on Mozilla documentation `here <https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods>`_ . If you wish to 
retrieve the value of a parameter or run the getter method, you need to make a GET request at the specified URL. The browser search bar always executes a GET request which 
explains the JSON response obtained above with the value of the `serial_number`.  If you need to change the value of a parameter (`serial_number` here) or run its setter method,
you need to make a PUT request at the same URL. The http request method can be modified on a parameter by specifying a tuple at ``http_method`` argument, but its not generally necessary. 

Now, we would like to define methods. A `connect` and `disconnect` method may be implemented as follows:

.. code-block:: python 
    :emphasize-lines: 1

    from hololinked.server import RemoteObject, remote_method, post 
    from seabreeze.spectrometers import Spectrometer
    ...
    
    class OceanOpticsSpectrometer(RemoteObject):
        ... 

        model = String(default=None, allow_None=True, URL_path='/model',
                    doc='the model of the connected spectrometer')

        @remote_method(http_method='POST', URL_path='/connect')
        def connect(self, trigger_mode = None, integration_time = None):
            self.device = Spectrometer.from_serial_number(self.serial_number) 
            self.model = self.device.model
            self.logger.debug(f"opened device with serial number {self.serial_number} with model {self.model}")
        
        # the above remote_method() can be shortened as 
        @post('/disconnect') 
        def disconnect(self):
            self.device.close()
           

    if __name__ == '__main__':
        ... 
        H.start(block=False) # creates a new process
        ...
        O.run() 


Here we define methods connect & disconnect as remote methods, accessible under HTTP request method POST. The full 
URL path will be as follows:

.. list-table::

    *   - format  
        - `https://{domain name}/{instance name}/{method URL path}`
    *   - connect()
        - `https://localhost:8083/spectrometer/ocean-optics/USB2000-plus/connect`
    *   - disconnect()
        - `https://localhost:8083/spectrometer/ocean-optics/USB2000-plus/disconnect`

The paths '/connect' and '/disconnect' are called RPC-style end-points (or resource representation). We directly specify a name for the method in the URL, and generally 
use the POST HTTP request to execute it. For execution of methods with arbitrary python logic, it is suggested to use POST method. 
If there are python methods fetching data (say after some computations), GET request method may be more suitable (in which you can directly access the 
from the browser search bar). For `connect` and `disconnect`, since we do not fetch useful data after running the method, we use the POST method. 

Importantly, |module-highlighted| restricts method execution to one method at a time although HTTP Server handle multiple requests at once. 
This is due to how remote procedure calls are implemented. Even if you define both `connect` and `disconnect` methods for remote access,
when you execute `connect` method, disconnect cannot be executed even if you try to POST at that URL while `connect` is running & vice-versa. 
The request will be queued with a certain timeout (which can also be modified). 
The queuing can be overcome only if you execute the method by threading it with your own logic. 

Now we also define further options for the spectrometer, starting with the integration time. 

.. code-block:: python 
    :emphasize-lines: 15,20

    from hololinked.param import String, Number 
    ...
    
    class OceanOpticsSpectrometer(RemoteObject):
        ... 

        model = String(default=None, allow_None=True, URL_path='/model',
                    doc='the model of the connected spectrometer')

        integration_time_millisec = Number(default=1000, bounds=(0.001, None), crop_to_bounds=True, 
                            URL_path='/integration-time', 
                            doc="integration time of measurement in milliseconds")
        ...

        @integration_time_millisec.setter 
        def _set_integration_time_ms(self, value):
            self.device.integration_time_micros(int(value*1000))
            self._integration_time_ms = int(value) 
           
        @integration_time_millisec.getter 
        def _get_integration_time_ms(self):
            try:
                return self._integration_time_ms
            except:
                return self.parameters["integration_time_millisec"].default 

        # the above can be shortened as 
        @post('/disconnect') 
        def disconnect(self):
            self.device.close()
           

    if __name__ == '__main__':
        ... 

For this parameter, we will use a custom getter and setter method because `seabreeze` does not seem to memorize the value or return it from the device.
The setter method directly applies the value on the device and stores in an internal variable when successful. While retrieving the value, the stored value 
or default value is returned. Next, trigger modes:


.. code-block:: python 
    :emphasize-lines: 19

    from hololinked.param import String, Number, Selector
    ...
    
    class OceanOpticsSpectrometer(RemoteObject):

        def _set_trigger_mode(self, value):
            self.device.trigger_mode(value)
            self._trigger_mode = value 
            
        def _get_trigger_mode(self):
            try:
                return self._trigger_mode
            except:
                return self.parameters["trigger_mode"].default 

        ... 

        trigger_mode = Selector(objects=[0,1,2,3,4], default=1, URL_path='/trigger-mode', 
                    fget=_get_trigger_mode, fset=_set_trigger_mode,
                    doc="""0 = normal/free running, 1 = Software trigger, 2 = Ext. Trigger Level,
                        3 = Ext. Trigger Synchro/ Shutter mode, 4 = Ext. Trigger Edge""")
                # Option 2 for specifying getter and setter methods
        ...        



        # the above can be shortened as 
        @post('/disconnect') 
        def disconnect(self):
            self.device.close()
           

    if __name__ == '__main__':
        ... 

The ``Selector`` parameter allows one of several values to be chosen. The manufacturer allows only when the options specified 
in the ``doc`` argument, therefore we use the ``objects=[0,1,2,3,4]`` to restrict the values to one of the specified. 
The ``objects`` list can accept any python data type. Again, we will use a custom getter-setter method to directly apply 
the setting on the device. Further, the value is passed to the setter method is always verified internally prior to invoking it. 
The same verification also applies to `integration_time`, where the value will verified to be a float or int and be cropped to the 
bounds specified in ``crop_to_bounds`` argument before calling the setter method.

After we connect to the instrument, lets say, we would like to have some information about the supported wavelengths and 
pixels:

.. code-block:: python 
  
    from hololinked.param import String, Number, Selector, ClassSelector, Integer
    ...
    
    class OceanOpticsSpectrometer(RemoteObject):

        ... 

        wavelengths = ClassSelector(default=None, allow_None=True, class_=(numpy.ndarray, list), 
                URL_path='/wavelengths', doc="Wavelength bins of the spectrometer device")

        pixel_count = Integer(default=None, allow_None=True, URL_path='/pixel-count', 
                    doc="Number of points in wavelength" )

        @remote_method(http_method='POST', URL_path='/connect')  
        def connect(self, trigger_mode = None, integration_time = None):
            """
            connect to the spectrometer and retrieve information about it
            """
            self.device = Spectrometer.from_serial_number(self.serial_number) 
            self.wavelengths = self.device.wavelengths()
            self.model = self.device.model
            self.pixel_count = self.device.pixels   

        ... 

    if __name__ == '__main__':
        ...


To make some basic tests on the object, let us complete it by defining measurement methods 
`start_acquisition` and `stop_acquisition`. To collect the data, we also need a data container.
We define a data container called `Intensity` 

.. code-block:: python 
    :caption: data.py

    import datetime
    import numpy
    from dataclasses import dataclass, asdict


    @dataclass 
    class Intensity:
        value : numpy.ndarray
        timestamp : str  

        def json(self):
            return {
                'value' : self.value.tolist(),
                'timestamp' : self.timestamp
            }

        @property
        def not_completely_black(self):
            if any(self.value[i] > 0 for i in range(len(self.value))):  
                return True 
            return False


Within the OceanOpticsSpectrometer class,

.. code-block:: python 
  
    ...
    from .data import Intensity
    
    class OceanOpticsSpectrometer(RemoteObject):

        ...
        last_intensity = ClassSelector(default=None, allow_None=True, class_=Intensity, 
            URL_path='/intensity', doc="last measurement intensity (in arbitrary units)")

        ...

i.e. since intensity will be stored within an instance of `Intensity`, we need to use a ``ClassSelector`` parameter
which accepts values as an instance of classes specified under ``class_`` argument. Let us define the measurement loop:

.. code-block:: python 

    def measure(self, max_count = None):
        self._running = True
        self.logger.info(f'starting continuous acquisition loop with trigger mode {self.trigger_mode} & integration time {self.integration_time}')
        loop = 0
        while self._running:
            if max_count is not None and loop >= max_count:
                break 
            try:
                # Following is a blocking command - self.spec.intensities
                _current_intensity = self.device.intensities(
                                                    correct_dark_counts=True,
                                                    correct_nonlinearity=True 
                                                )
                timestamp = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
                self.logger.debug(f'measurement taken at {timestamp} - measurement count {loop+1}')
                if self._running:
                    # To stop the acquisition in hardware trigger mode, we set running to False in stop_acquisition() 
                    # and then change the trigger mode for self.spec.intensities to unblock. This exits this 
                    # infintie loop. Therefore, to know, whether self.spec.intensities finished, whether due to trigger 
                    # mode or due to actual completion of measurement, we check again if self._running is True. 
                    if any(_current_intensity [i] > 0 for i in range(len(_current_intensity))):   
                        self.last_intensity = Intensity(
                            value=_current_intensity, 
                            timestamp=timestamp
                        )
                        self.logger.debug(f'measurement taken at {self.last_intensity.timestamp} - measurement count {loop}')
                    else:
                        self.logger.warn('trigger delayed or no trigger or erroneous data - completely black')
                loop += 1
            except Exception as ex:
                self.logger.error(f'error during acquisition : {str(ex)}')
                
        self.logger.info("ending continuous acquisition") 


The measurement method is an infinite loop. Therefore, it will need to be threaded to not block further requests from clients or 
allow execution of other remote methods like stopping the measurement. When we start acquisition, we need to be able to stop acquisition 
while acquisition is still running and vice versa. 

.. code-block:: python 
  
    import threading
    ...
 
    class OceanOpticsSpectrometer(RemoteObject):

        ...

        @post('/acquisition/start')
        def start_acquisition(self):
            self.stop_acquisition() # Just a shield 
            self._acquisition_thread = threading.Thread(target=self.measure) 
            self._acquisition_thread.start()

        @post('/acquisition/stop')
        def stop_acquisition(self):
            if self._acquisition_thread is not None:
                self.logger.debug(f"stopping acquisition thread with thread-ID {self._acquisition_thread.ident}")
                self._running = False # break infinite loop
                # Reduce the measurement that will proceed in new trigger mode to 1ms
                self.device.integration_time_micros(1000)       
                # Change Trigger Mode if anything else other than 0, which will cause for the measurement loop to block permanently 
                self.device.trigger_mode(0)                    
                self._acquisition_thread.join()
                self._acquisition_thread = None 
                # re-apply old values
                self.trigger_mode = self.trigger_mode
                self.integration_time_millisec = self.integration_time_millisec 


Now, we need to be able to constrain the execution of methods & setting of parameters using a state machine. When the device is disconnected or running measurements,
it does not make sense to update measurement settings. Or, the connect method can be run only the device is disconnected and vice-versa. For this,
we use the ``StateMachine`` class. 

.. code-block:: python 
  
    from hololinked.server import RemoteObject, remote_method, post, StateMachine
    from enum import Enum
    ...
 
    class OceanOpticsSpectrometer(RemoteObject):

        states = Enum('states', 'DISCONNECTED ON MEASURING')

        ...

        @post('/acquisition/stop')
        def stop_acquisition(self):
            ...

        state_machine = StateMachine(
            states=states,
            initial_state=states.DISCONNECTED,
            DISCONNECTED=[connect],
            ON=[disconnect, start_acquisition, integration_time_millisec, trigger_mode],
            MEASURING=[stop_acquisition],
        )

We have three states `ON`, `DISCONNECTED`, `MEASURING` which will be specified as an Enum. We will pass this `states` to the ``StateMachine``
construtor to denote possible states in the state machine, while specifying the `initial_state` to be `DISCONNECTED`. Next, using the state names as keyword arguments, 
a list of methods and parameters whose setter can be executed in that state are specified. When the device is disconnected, we can only connect to the device. 
When the device is connected, it will go to `ON` state and allow measurement settings to be changed. During measurement, we are only allowed to stop measurement. 
We need to still trigger the state transitions manually: 

.. code-block:: python 
    :emphasize-lines: 13,19,23,26

    ...
    class OceanOpticsSpectrometer(RemoteObject):
        
        ...

        states = Enum('states', 'DISCONNECTED ON MEASURING')

        ...
              
        @remote_method(http_method='POST', URL_path='/connect')
        def connect(self, trigger_mode = None, integration_time = None):
            self.device = Spectrometer.from_serial_number(self.serial_number) 
            self.state_machine.current_state = self.states.ON
            ...

        @post('/disconnect')
        def disconnect(self):
            self.device.close()
            self.state_machine.current_state = self.states.DISCONNECTED
                      
        def measure(self, max_count = None):
            self._running = True
            self.state_machine.current_state = self.states.MEASURING
            while self._running:
                ...
            self.state_machine.current_state = self.states.ON
            self.logger.info("ending continuous acquisition") 
            self._running = False 
           
Finally, the clients need to be informed whenever a measurement has been made. This can be helpful, say, to plot a graph. Instead of 
making the clients repeatedly poll for the `intensity` to find out if a new value is available, its more efficient to inform the clients
whenever the measurement has completed without the clients asking. These are generally termed as server-sent-events. To create such an event,
the following recipe can be used 

.. code-block:: python 
    :emphasize-lines: 9,19

    from hololinked.server import RemoteObject, remote_method, post, StateMachine, Event
    ...
    class OceanOpticsSpectrometer(RemoteObject):
        ...

        def __init__(self, serial_number : str, **kwargs):
            super().__init__(serial_number=serial_number, **kwargs)
            ...
            self.intensity_measurement_event = Event(name='intensity-measurement-event', URL_path='/intensity/measurement-event')

        def measure(self, max_count = None):
            ...
                ...
                    if any(_current_intensity[i] > 0 for i in range(len(_current_intensity))):   
                        self.last_intensity = Intensity(
                            value=_current_intensity, 
                            timestamp=timestamp
                        )
                        self.intensity_measurement_event.push(self.last_intensity)
                ...
            ...

In the ``Intensity`` dataclass, a `json()` method was defined. This method informs the built-in JSON serializer of ``hololinked`` to serialize 
data to JSON compliant format whenever necessary. Once the event is pushed, its tunnelled as an HTTP server sent event by the HTTP Server using 
the JSON serializer. The event can be accessed at |br|
`https://{domain name}/{instance name}/{event URL path}`, which gives 
`https://localhost:8083/spectrometer/ocean-optics/USB2000-plus/intensity/measurement-event` 
for the intensity event. 

The browser will already display the event data when you type the URL in the search bar, but it will not be formatted nicely. 

.. warning::
    generally for event streaming, https is necessary

To update our ``HTTPServer`` to have SSL encryption, we can modify it as follows:

.. code-block:: python 
    :caption: executor.py 

    from multiprocessing import Process
    from hololinked.server import HTTPServer
    from device import OceanOpticsSpectrometer

    def start_http_server():
        ssl_context = ssl.SSLContext(protocol = ssl.PROTOCOL_TLS)
        ssl_context.load_cert_chain('assets\\security\\certificate.pem',
                            keyfile = 'assets\\security\\key.pem')

        H = HTTPServer(consumers=['spectrometer/ocean-optics/USB2000-plus'], port=8083, ssl_context=ssl_context, 
                        log_level=logging.DEBUG)  
        H.start()


    if __name__ == "__main__":
        # You need to create a certificate on your own 
        P = Process(target=start_http_server)
        P.start()

        O = OceanOpticsSpectrometer(
            instance_name='spectrometer/ocean-optics/USB2000-plus',
            serial_number='USB2+H15897',
            log_level=logging.DEBUG,
            trigger_mode=0
        )
        O.run()

The ``SSLContext`` contains a SSL certificate. A professionally recognised SSL certificate may be used, but in this example a self-created 
certificate will be used. This certificate is not generally recognised by the browser unless explicit permission is given. Further, the SSLContext
cannot be serialized by python's built-in ``multiprocessing.Process``, so we will fork the process manually and create a ``SSLContext`` in the new process. 

Let us summarize all the HTTP end-points of the parameters, methods and events:

.. list-table::

    *   - object 
        - URL path 
        - HTTP request method 
    *   - connect()
        - `https://localhost:8083/spectrometer/ocean-optics/USB2000-plus/connect`
        - POST
    *   - disconnect()
        - `https://localhost:8083/spectrometer/ocean-optics/USB2000-plus/disconnect`
        - POST
    *   - serial_number
        - `https://localhost:8083/spectrometer/ocean-optics/USB2000-plus/serial-number`
        - GET (read), PUT (write)
    *   - model
        - `https://localhost:8083/spectrometer/ocean-optics/USB2000-plus/model`
        - GET (read)
    *   - integration_time_millisec
        - `https://localhost:8083/spectrometer/ocean-optics/USB2000-plus/integration-time`
        - GET (read), PUT(write)
    *   - trigger_mode
        - `https://localhost:8083/spectrometer/ocean-optics/USB2000-plus/trigger-mode`
        - GET (read), PUT(write) 
    *   - pixel_count 
        - `https://localhost:8083/spectrometer/ocean-optics/USB2000-plus/pixel-count`
        - GET (read)
    *   - wavelengths
        - `https://localhost:8083/spectrometer/ocean-optics/USB2000-plus/wavelengths`
        - GET (read)
    *   - intensity
        - `https://localhost:8083/spectrometer/ocean-optics/USB2000-plus/intensity`
        - GET (read)
    *   - intensity_measurement_event
        - `https://localhost:8083/spectrometer/ocean-optics/USB2000-plus/intensity/measurement-event`
        - GET (SSE) 
    *   - start_acquisition
        - `https://localhost:8083/spectrometer/ocean-optics/USB2000-plus/acquisition/start`
        - POST 
    *   - stop_acquisition
        - `https://localhost:8083/spectrometer/ocean-optics/USB2000-plus/acquisition/stop`
        - POST 



.. warning::
    This example does not strictly comply to API design practices 

.. note::

    In order to see all your defined methods, parameters & events, you could also use ``hololinked-portal``. 
    There is a `RemoteObject client` feature which can load the HTTP exposed resources of your RemoteObject. 
    In the search bar, you can type `https://localhost:8083/spectrometer/ocean-optics/USB2000-plus` 
    To build a GUI in ReactJS, `this article <https://hololinked.dev/docs/category/spectrometer-gui>`_ can be a guide.   

One can already test this & continue to next article for improvements. 