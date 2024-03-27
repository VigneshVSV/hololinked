.. |module-highlighted| replace:: ``hololinked``

.. |br| raw:: html

    <br />


.. _note:

Development Notes
=================

In the interest of information to software engineers and web developers, the main difference of |module-highlighted| to a conventional 
RPC or REST(-like) paradigm with HTTP is that, |module-highlighted| attempts to be a hybrid of both. For instrument control
& data-acquisition, it is difficult to move away completely from RPC to REST. Besides, most instrument drivers/hardware 
allow only a single persistent connection with a single process instead of multiple clients or processes. Further, when 
such a process talks to an instrument, only one instruction can be sent at a time, which needs to be completed before 
the next instruction. On the other hand, HTTP Servers are multi-threaded or asyncio oriented by design and REST(-like) API 
does not care how many simultaneous operations are run. To reconcile both, the following is proposed:

* |module-highlighted| gives the freedom to choose the HTTP request method & end-point URL desirable for each method, parameter and event
* All HTTP requests will be queued and executed serially unless threaded or made async manually by the programmer
* parameters can be used to model settings of instrumentation (both hardware and software-only), general class/instance attributes, 
  hold captured & computed data.
* events can be used to push measured data, create alerts/alarms, inform availability of certain type of data etc.
* methods can be used to issue commands to instruments like start and stop acquisition, connect/disconnect etc.
* Verb like URLs may be used for methods & noun-like URLs are suggested to be used for parameters and events.
* Finally, freedom is given to modify web request handler to change headers, authentication etc. or add additional endpoints 
which may cast all resources to REST(-like) while leaving the remote object execution details to the package.

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

