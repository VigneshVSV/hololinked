.. |module| replace:: hololinked
 
.. |module-highlighted| replace:: ``hololinked``

.. |remote-paramerter-import-highlighted| replace:: ``hololinked.server.remote_parameters``

Spectrometer
============

Consider you have an optical spectrometer & you need the following options to control it:

* connect & disconnect from the instrument
* capture spectrum data 
* change integration time, trigger mode etc. 

We start by creating the object class as a sublcass of ``RemoteObject``. 
In this example, OceanSight USB2000+ spectrometer is used, which has a python high level wrapper
called `seabreeze <https://python-seabreeze.readthedocs.io/en/latest/>`_

.. code-block:: python 

    from hololinked.server import RemoteObject
    from seabreeze.spectrometers import Spectrometer


    class OceanOpticsSpectrometer(RemoteObject):
        """
        Connect to OceanOptics spectrometers using seabreeze library by specifying serial number. 
        For supported spectrometers visit : <a href="https://python-seabreeze.readthedocs.io/en/latest/">Seabreeze Pypi</a>.
        """

The spectrometers are identified by a serial number, which needs to be a string. Let us allow this serial number 
to be changed whenever necessary. To ensure that the serial number is complied to a string whenever accessed by a client 
on the network, we need to use a parameter type defined in |remote-paramerter-import-highlighted|. By default, |module-highlighted|
defines remote parameters/attributes like Number (float or int), String, Date etc. 
The exact meaning and definitions are found in the :ref:`API Reference <apiref>` and is derived from ``param``. 


.. code-block:: python 
    :emphasize-lines: 2

    ...
    from hololinked.param import String, Number, Selector 
    # Number and Selector will be used later

    class OceanOpticsSpectrometer(RemoteObject):
        ... 

        serial_number = String(default=None, allow_None=True, URL_path='/serial-number',
                    doc='serial number of the spectrometer to connect/control')

        model = String(default=None, allow_None=True, URL_path='/model',
                    doc='the model of the connected spectrometer')


Each such parameter (like String, Number etc.) have their own list of arguments as seen above (``default``, ``allow_None``, ``doc``). 
Here we state that the default value of serial_number is ``None``, i.e. it accepts ``None`` although defined as a String and the URL_path where it should 
be accessible when served by a HTTP Server is '/serial-number'. Normally, such a parameter, when having a valid (non-None) value 
will be forced to contain a string only. Moreover, although these parameters are defined at class-level (looks like a class 
attribute), unless the ``class_member=True`` is set on the parameter, its an instance attribute. This is due to the 
python `descriptor <https://realpython.com/python-descriptors/>`_ protocol. The same explanation applies to the `model` parameter. 

The `URL_path` is interpreted as follows: First and foremost, you need to spawn a ``HTTPServer``. Second, such a HTTP Server
must talk to the OceanOpticsSpectrometer instance. To achieve this, the ``RemoteObject`` is instantiated with a specific 
``instance_name`` and the HTTP server is spawn with an argument containing the instance_name. (We still did not implement 
any methods like connect/disconnect etc.). When this happens, the parameter becomes available at the stated `URL_path` along
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
To construct the full `URL_path`, the format is 
`https://{domain name}/{instance name}/{parameter URL path}` which gives 
`https://localhost:8083/spectrometer/ocean-optics/USB2000-plus/serial-number` for the `serial_number`. 

Since the `instance_name` partipates as a prefix in the `URL path`, it is recommended to use a slash separated ('/') name complying to URL 
standards (name with 0 slashes are also accepted). If your PC has a domain name, you can also use the domain name instead of `localhost`. 

To access the `serial_number`, once the example starts without errors, type the URL in the web browser to get a reply like the following:

.. code-block:: JSON 

    {
        "responseStatusCode" : 200,
        "returnValue" : "USB2+H15897",
        "state" : null
    }
    
The returnValue field contains the value obtained by running the python method, in this case python attribute 
getter of `serial_number`. 

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
use the POST HTTP request to execute it. 

HTTP defines certain 'verbs' like GET, POST, PUT, DELETE etc. Each verb can be used to mean a certain action at a specified URL (or resource representation), 
a list of which can be found on Mozilla documentation `here <https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods>`_ . In case of `serial_number`, if you wish to 
retrieve its value, you need to make a GET request at the specified link. The browser search bar always executes a GET request which 
explains the JSON response obtained above with the value of the `serial_number`.  If you need to change the value of serial_number,
you need to make a PUT request at the same URL. For execution of methods with arbitrary python logic, it is suggested to use POST method. 
If there are python methods fetching data (say after some computations), feel free to use GET request method. For connect and disconnect,
since we do not fetch useful data after running the method, we use the POST method. 

Importantly, |module-highlighted| restricts method execution to one method at a time although HTTP Server handle multiple requests at once. 
Even if you define both connect and disconnect methods for remote access,
when you execute connect, disconnect cannot be executed even if you try to POST at that URL & vice-versa. 
The request will be queued with a certain timeout (which can also be modified). 
The queuing can be overcome only if you execute the method by threading it with your own logic. 

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

The ``Selector`` parameter allows one of several values to be chosen. The manufacturer allows only the options specified 
in the ``doc`` argument, therefore we use the ``objects=[0,1,2,3,4]`` to restrict the values to one of the specified. 
The ``objects`` list can accept any python data type.

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
We define the data container called `Intensity` 

.. code-block:: python 
  
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
            URL_path='/intensity/last', doc="last measurement intensity (in arbitrary units)")

        max_intensity = Number(readonly=True, URL_path='/intensity/last/max', 
                            doc="max intensity of the last measurement")
        ...

i.e. since intensity will be stored within an instance of `Intensity`, we need to use a ``ClassSelector`` parameter
which accepts values as an instance of classes specified under `class_` argument. The acquisition methods are infinite loops, 
and therefore will need to be threaded. This is required to allow execution without blocking the execution of other remote methods.
When we start_acquisition, we need to be able to stop_acquisition while acquisition is still running and vice versa. 

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

The `measure` method is defined as follows: 

.. code-block:: python 
            
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

    In order to see all your defined methods, parameters & events, you could use ``hololinked-portal``. There is `RemoteObject client`
    feature which can load the HTTP exposed resources of your RemoteObject. In the search bar, you can type 
    `https://localhost:8083/spectrometer/ocean-optics/USB2000-plus` 

To build a GUI in ReactJS, the following article can be a guide.   