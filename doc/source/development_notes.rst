.. |module-highlighted| replace:: ``hololinked``

.. |br| raw:: html

    <br />


.. _note:

Development Notes
=================

|module-highlighted| is fundamentally a Object Oriented ZeroMQ RPC with control over which attributes, methods 
and events are exposed on the network. Nevertheless, a non-trivial support for HTTP exists in an attempt to cast 
atleast certain aspects of instrumentation control & data-acquisition for web development practices, without having to 
explicitly implement a HTTP server. The following is possible with this package with significantly lesser code:  

* |module-highlighted| gives the freedom to choose the HTTP request method & end-point URL desirable for
  each method, parameter and event
* All HTTP requests will be queued and executed serially by the RPC server unless threaded or made async manually by 
  the programmer
* Verb like URLs may be used for methods (acts like HTTP-RPC although ZeroMQ mediates this) & noun-like URLs are 
  may be used for parameters and events. 
* web request handlers may be modified to change headers, authentication etc. or add additional 
  endpoints which may cast all resources to REST-like while leaving the RPC details to the package.
* Events pushed by the object will be automatically tunneled as HTTP server sent events.
* JSON serialization-deserialization overheads while tunneling HTTP requests through the RPC server  
  are controlloable and kept to a minimum. 

One uses exposed object members as follows: 

* parameters can be used to model settings of instrumentation (both hardware and software-only), 
  general class/instance attributes, hold captured & computed data.
* methods can be used to issue commands to instruments like start and stop acquisition, connect/disconnect etc.
* events can be used to push measured data, create alerts/alarms, inform availability of certain type of data etc.

HTTP request methods may be mapped as follows:

.. list-table:: 
   :header-rows: 1

   * - HTTP request verb/method
     - remote parameter  
     - remote method 
     - event  
   * - GET
     - read parameter value |br| (read a setting's value, fetch measured data - for example, measured physical quantities)
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

Despite the above, an object proxy can also directly access the methods, parameters and events without the details of HTTP.


