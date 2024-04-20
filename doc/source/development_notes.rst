.. |module-highlighted| replace:: ``hololinked``

.. |br| raw:: html

    <br />


.. _note:

Development Notes
=================

|module-highlighted| is fundamentally a Object Oriented ZeroMQ RPC with control over which attributes, methods 
and events are exposed on the network. Nevertheless, a non-trivial support for HTTP exists in an attempt to cast 
atleast certain aspects of instrumentation control & data-acquisition for web development practices, without having to 
explicitly implement a HTTP server. The following is possible with significantly lesser code:  

* |module-highlighted| gives the freedom to choose the HTTP request method & end-point URL desirable for
  each method, parameter/attribute and event
* All HTTP requests will be automatically queued and executed serially by the RPC server unless threaded or 
  made async by the developer
* JSON serialization-deserialization overheads while tunneling HTTP requests through the RPC server  
  are reduced to a minimum. 
* web request handlers may be modified to change headers, authentication etc. or add additional 
  endpoints which may cast resources to REST-like while leaving the RPC details to the package
* Events pushed by the object will be automatically tunneled as HTTP server sent events

One uses exposed object members as follows: 

* parameters can be used to model settings of instrumentation (both hardware and software-only), 
  general class/instance attributes, hold captured & computed data
* methods can be used to issue commands to instruments like start and stop acquisition, connect/disconnect etc.
* events can be used to push measured data, create alerts/alarms, inform availability of certain type of data etc.
* Verb like URLs may be used for methods (acts like HTTP-RPC although ZeroMQ mediates this) & noun-like URLs are 
  may be used for parameters and events. 

HTTP request methods may be mapped as follows:

.. list-table:: 
   :header-rows: 1

   * - HTTP request verb/method
     - remote parameter  
     - remote method 
     - event  
   * - GET
     - read parameter value |br| (read a setting's value, fetch measured data, physical quantities)
     - run method which gives a return value with useful data |br| (which may be difficult or illogical as a ``parameter``)
     - stream measured data immediately when available instead of fetching every time 
   * - POST 
     - add dynamic parameters with certain settings |br| (add a dynamic setting or data type etc. for which the logic is already factored in code)
     - run python logic, methods that connect/disconnect or issue commands to instruments (RPC)
     - not applicable 
   * - PUT 
     - write parameter value |br| (modify a setting and apply it onto the device)
     - change value of a resource which is difficult to factor into a parameter 
     - not applicable
   * - DELETE 
     - remove a dynamic parameter |br| (remove a setting or data type for which the logic is already factored into the code)
     - developer's interpretation 
     - not applicable
   * - PATCH
     - change settings of a parameter |br| (change the rules of how a setting can be modified and applied, how a measured data can be stored etc.)
     - change partial value of a resource which is difficult to factor into a parameter or change settings of a parameter with custom logic 
     - not applicable


Considering an example device like a spectrometer, the table above may dictate the following:

.. list-table:: 
   :header-rows: 1

   * - HTTP request verb/method
     - remote parameter  
     - remote method 
     - event  
   * - GET
     - get integration time
     - get accumulated dictionary of measurement settings
     - stream measured spectrum
   * - POST 
     - 
     - connect, disconnect, start and stop acquisition
     - 
   * - PUT 
     - set integration time onto device
     - 
     - 

If one wants further inspiration how to use this module, one may refer to W3C Web of Things 
`Architecture <https://www.w3.org/TR/wot-architecture/#sec-interaction-model>`_ and
`Thing Description <https://www.w3.org/TR/wot-thing-description11/>`_, where the ``Thing`` maps to base class ``RemoteObject``

Further, plain RPC calls directly through object proxy are possible without the details of HTTP.


