Example 1 - Spectrometer & Array Data 
=====================================

Consider you have an optical spectrometer & you need to have following options to control it:

* connect & disconnect from the instrument
* capture spectrum data 
* change integration time, trigger mode etc. 

First, we create the object class as a sublcass of ``RemoteObject``. 
This example is based on OceanSight USB2000+ spectrometer, which has a python high level implementation
called `seabreeze <https://python-seabreeze.readthedocs.io/en/latest/>`_

.. code-block:: python 

    from daqpy.server import RemoteObject
    from seabreeze.spectrometers import Spectrometer


    class OceanOpticsSpectrometer(RemoteObject):
        """
        Connect to OceanOptics spectrometers using seabreeze library by specifying serial number. 
        For supported spectrometers visit : <a href="https://python-seabreeze.readthedocs.io/en/latest/">Seabreeze Pypi</a>.
        """

The spectrometers are identified by a serial number, which needs to be a string. Let us allow this serial number 
to be changed whenever necessary. To make sure that serial number is complied to a string when accessed from a client 
on your network, we need to use a parameter type defined in `daqpy.server.remote_parameters`. By default, `daqpy`
defines remote parameters/attributes like Number (float or int), String, Selector (allows one object among many). 
The exact meaning and definitions are found in the `API Reference` and is derived from ``param``. 


.. code-block:: python 
    :emphasize-lines: 2

    ...
    from daqpy.param import String, Number, Selector 
    # Number and Selector will be used later

    class OceanOpticsSpectrometer(RemoteObject):
        ... 

        serial_number = String(default=None, allow_None=True, URL_path='/serial-number',
                    doc='serial number of the spectrometer to connect/control')

        model = String(default=None, allow_None=True, URL_path='/model',
                    doc='the model of the connected spectrometer')


Each such parameter (like String, Number etc.) have their own list of arguments, nevertheless, here we state that 
the default value of serial_number is ``None``, it accepts ``None`` although defined as a String and the URL_path where it should 
be accessible when served by a HTTP Server is '/serial-number'. Normally, such a parameter, when having a valid value 
will be forced to contain a string only. Moreover, although these parameters are defined at class-level (looks like a class 
attribute), unless the ``class_member = True`` is set on the parameter, its an instance attribute. This is due to the 
python descriptor protocol. The same explanation applies to the `model` parameter. 

The function of the `URL_path` is as follows. First and foremost, you need to spawn a HTTPServer. Second, such a HTTP Server
must talk to the OceanOpticsSpectrometer instance. With `daqpy`, to achieve this, the class is instantiated with a specific 
``instance_name`` and the HTTP server is spawn with an argument containing the instance_name. (We still did not implement 
any methods like connect/disconnect etc.). When this happens, the parameter becomes available at the stated `URL_path` along
with the prefix of the HTTP Server domain name and object instance name. 

The above explanation is re-iterated after the following example:

.. code-block:: python 
    :emphasize-lines: 2

    ...
    from daqpy.server import HTTPServer
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
            serial_number='USB2+H15897',
            log_level=logging.DEBUG,
        )
        O.run()

Again, the ``instance_name`` refers to what it exactly means - a name for the instance of the object, since the same object can be instantiated with
a different name to control a different spectrometer. The same `instance_name` is given to both the HTTPServer and the OceanOpticsSpectrometer 
instance. The `HTTPServer.start()` will create a new process where the server lives and looks for a ``RemoteObject`` s with names 
contained in the consumers parameter. The port of the HTTPServer is 8083 here. To construct the full `URL_path`, say, for the serial_number 
parameter, the format is as follows : `https://localhost:8083/spectrometer/ocean-optics/USB2000-plus/serial-number`. 

Since the instance name partipates as a prefix in the URL path, it is recommended to use a slash separated ('/') name complying to URL 
standards (name with 0 slashes are also accepted). If your PC has a domain name, you can also use the domain name instead of `localhost`. 

HTTP defines certain verbs like GET, POST, PUT, DELETE etc. Each verb can be used to mean a certain action, a list of which can be found 
on mozilla documentation `here <https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods>`_ . In case of serial_number, if you wish to 
retrieve a serial number, you need to make a GET request at the specified link. If you need to change the value of serial_number,
you need to make a PUT request. Examples of these will be discussed later, but if you type the link in your browser address bar, 
a GET request will be made and you will obtain the following output:

.. code-block:: JSON 

    {
        "responseStatusCode" : 200,
        "returnValue" : "USB2+H15897",
        "state" : null
    }
    
The returnValue is the most important as it is the value obtained by running the python method, in this case python attribute 
access of serial_number. 

Now, we would like to define methods. A `connect` and `disconnect` method may be implemented as follows:

.. code-block:: python 
    :emphasize-lines: 1

    from daqpy.server import RemoteObject, remote_method, post 
    from seabreeze.spectrometers import Spectrometer
    ...
    
    class OceanOpticsSpectrometer(RemoteObject):
        ... 

        model = String(default=None, allow_None=True, URL_path='/model',
                    doc='the model of the connected spectrometer')

        @remote_method(http_method='POST', URL_path='/connect')
        def connect(self, trigger_mode = None, integration_time = None):
            self.device = Spectrometer.from_serial_number(self.serial_number) 
        
        # the above can be shortened as 
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
    
    * - connect
      - `https://localhost:8083/spectrometer/ocean-optics/USB2000-plus/connect`
    * - disconnect
      - `https://localhost:8083/spectrometer/ocean-optics/USB2000-plus/disconnect`

The paths '/connect' and '/disconnect' are called RPC-style end-points. We directly specify a name for the method in the URL, and generally 
use the POST HTTP request to execute it. If you have python methods fetching data (say after some computations), feel free to use GET request. 

Importantly, ``daqpy`` restricts method execution to one method at a time. Even if you define both connect and disconnect methods for remote access,
when you execute connect, disconnect cannot be executed & vice-versa. This can be overcome only if you execute the method in your own thread. 

Now we also define further options for the spectrometer, starting with the integration time. 

.. code-block:: python 
   
    ...
    
    class OceanOpticsSpectrometer(RemoteObject):
        ... 

        model = String(default=None, allow_None=True, URL_path='/model',
                    doc='the model of the connected spectrometer')

        integration_time = Number(default=1000, bounds=(0.01, None), crop_to_bounds=True, 
                            URL_path='/integration-time/milliseconds', # allow_None=False,
                            doc="integration time of measurement in milliseconds")
        ...

        # the above can be shortened as 
        @post('/disconnect') 
        def disconnect(self):
            self.device.close()
           

    if __name__ == '__main__':
        ... 

Next, trigger modes:


.. code-block:: python 
  
    ...
    
    class OceanOpticsSpectrometer(RemoteObject):
        ... 

        integration_time = Number(default=1000, bounds=(0.01, None), crop_to_bounds=True, 
                            URL_path='/integration-time/milliseconds', # allow_None=False,
                            doc="integration time of measurement in milliseconds")

        trigger_mode = Selector(objects=[0,1,2,3,4], default=1, URL_path='/trigger-mode', 
                    doc="""0 = normal/free running, 1 = Software trigger, 2 = Ext. Trigger Level,
                        3 = Ext. Trigger Synchro/ Shutter mode, 4 = Ext. Trigger Edge""")
        ...        
        
        # the above can be shortened as 
        @post('/disconnect') 
        def disconnect(self):
            self.device.close()
           

    if __name__ == '__main__':
        ... 

The ``Selector`` parameter type allows one of several values to chosen. The manufacturer allows only the options specified 
in the ``doc`` argument, therefore we use the ``objects=[0,1,2,3,4]`` to restrict the values to one of the specified. 
The ``objects`` list can accept any python datatype.

After we connect to the instrument, lets say, we would like to have some information about the supported wavelengths and 
pixels:

.. code-block:: python 
  
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
We define the data container called Intensity 

.. code-block:: python 
  
    import typing
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
        last_intensity : Intensity = ClassSelector(default=None, allow_None=True, class_=Intensity, 
            URL_path='/intensity/last', doc="last measurement intensity (in arbitrary units)") # type: ignore

        max_intensity = Number(readonly=True, URL_path='/intensity/last/max', 
                            doc="max intensity of the last measurement")
        ...


The acquisition methods are infinite loops, and therefore will be threaded as follows:

.. code-block:: python 
  
    ...
 
    class OceanOpticsSpectrometer(RemoteObject):

        ...

        def __init__(self, serial_number : str, **kwargs):
            super().__init__(serial_number=serial_number)
            self.connect(kwargs.get('trigger_mode', 1), kwargs.get('integration_time', 1000))
            self._acquisition_thread = None 
            self._running = False

        @post('/acquisition/start')
        def start_acquisition(self):
            if self._acquisition_thread is not None:
                # Just a shield 
                self.stop_acquisition()
            self._acquisition_thread = threading.Thread(target=self.measure) 
            self._acquisition_thread.start()

        @post('/acquisition/stop')
        def stop_acquisition(self):
            self._running = False   
            # Reduce the measurement that will proceed in new trigger mode to 1ms
            self.device.integration_time_micros(1000)         
            # Change Trigger Mode if anything else other than 0, which will cause for the measurement loop to block permanently 
            self.device.trigger_mode(0)                    
            self._acquisition_thread.join()
            self._acquisition_thread = None 
            # re-apply old values
            self.trigger_mode = self.trigger_mode
            self.integration_time = self.integration_time 
            
        def measure(self):
            self._running = True
            self.state_machine.current_state = self.states.MEASURING
            self.logger.info(f'starting continuous acquisition loop with trigger mode {self.trigger_mode} & integration time {self.integration_time}')
            loop = 0
            while self._running:
                try:
                    # Following is a blocking command - self.spec.intensities
                    _current_intensity = self.device.intensities(
                                                        correct_dark_counts=True,
                                                        correct_nonlinearity=True 
                                                    )
                    
                    if self._running:
                        # To stop the acquisition in hardware trigger mode, we set running to False in stop_acquisition() 
                        # and then change the trigger mode for self.spec.intensities to unblock. This exits this 
                        # infintie loop. Therefore, to know, whether self.spec.intensities finished, whether due to trigger 
                        # mode or due to actual completion of measurement, we check again if self._running is True. 
                        if any(_current_intensity [i] > 0 for i in range(len(_current_intensity))):   
                            self.last_intensity = Intensity(
                                value=_current_intensity, 
                                timestamp=datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
                            )
                            self.logger.debug(f'measurement taken at {self.last_intensity.timestamp} - measurement count {loop}')
                            loop += 1
                            self.data_measured_event.push(self.last_intensity)
                            self.state_machine.current_state = self.states.MEASURING
                        else:
                            self.logger.warn('trigger delayed or no trigger or erroneous data - completely black')
                except Exception as ex:
                    self.logger.error(f'error during acquisition : {str(ex)}')
                    self.state_machine.current_state = self.states.FAULT
                    
            self.state_machine.current_state = self.states.ON
            self.logger.info("ending continuous acquisition") 

        ...


.. note::

    In order to see all your defined methods, parameters & events, you could use ``daqpy-portal``. There is `RemoteObject client`
    feature which can load the HTTP exposed resources of your RemoteObject. In the search bar, you can type 
    `https://localhost:8083/spectrometer/ocean-optics/USB2000-plus` 

To build a GUI in ReactJS, the following article can be a guide.   