.. |module-highlighted| replace:: ``hololinked``

.. |br| raw:: html

    <br />


.. _note:

Development Notes
=================

|module-highlighted| is fundamentally a Object Oriented ZeroMQ RPC with control over the attributes, methods 
and events that are exposed on the network. Nevertheless, a non-trivial support for HTTP exists in an attempt to cast 
atleast certain aspects of instrumentation control & data-acquisition for web development practices, without having to 
explicitly implement a HTTP server. The following is possible with significantly lesser code:  

* |module-highlighted| gives the freedom to choose the HTTP request method & end-point URL desirable for
  property/attribute, method and event
* All HTTP requests will be automatically queued and executed serially by the RPC server unless threaded or 
  made async by the developer
* JSON serialization-deserialization overheads while tunneling HTTP requests through the RPC server  
  are reduced to a minimum. 
* Events pushed by the object will be automatically tunneled as HTTP server sent events

Further web request handlers may be modified to change headers, authentication etc. or add additional 
endpoints which may cast resources to REST-like while leaving the RPC details to the package. One uses exposed object 
members as follows: 

* properties can be used to model settings of instrumentation (both hardware and software-only), 
  general class/instance attributes, hold captured & computed data
* methods can be used to issue commands to instruments like start and stop acquisition, connect/disconnect etc.
* events can be used to push measured data, create alerts/alarms, inform availability of certain type of data etc.

Verb like URLs may be used for methods (acts like HTTP-RPC although ZeroMQ mediates this) & noun-like URLs may be used 
for properties and events. Further, HTTP request methods may be mapped as follows:

.. list-table:: 
   :header-rows: 1

   * - HTTP request verb/method
     - property
     - action/remote method 
     - event  
   * - GET
     - read property value |br| (read a setting's value, fetch measured data, physical quantities)
     - run method which gives a return value with useful data |br| (which may be difficult or illogical as a ``Property``)
     - stream measured data immediately when available instead of fetching every time 
   * - POST 
     - add dynamic properties with certain settings |br| (add a dynamic setting or data type etc. for which the logic is already factored in code)
     - run python logic, methods that connect/disconnect or issue commands to instruments (RPC)
     - not applicable 
   * - PUT 
     - write property value |br| (modify a setting and apply it onto the device)
     - change value of a resource which is difficult to factor into a property 
     - not applicable
   * - DELETE 
     - remove a dynamic property |br| (remove a setting or data type for which the logic is already factored into the code)
     - developer's interpretation 
     - not applicable
   * - PATCH
     - change settings of a property |br| (change the rules of how a setting can be modified and applied, how a measured data can be stored etc.)
     - change partial value of a resource which is difficult to factor into a property or change settings of a property with custom logic 
     - not applicable

If you dont agree with the table above, use `Thing Description <https://www.w3.org/TR/wot-thing-description11/#http-binding-assertions>`_ 
standard instead, which is pretty close. Considering an example device like a spectrometer, the table above may dictate the following:

.. list-table:: 
   :header-rows: 1

   * - HTTP request verb/method
     - property
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
   * - PATCH 
     - edit integration time bound values 
     - 
     - 


Further, plain RPC calls directly through object proxy are possible without the details of HTTP. This is directly mediated 
by ZeroMQ. 


