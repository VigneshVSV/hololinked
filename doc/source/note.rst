DAQPY design 
============

In the interest of information to software engineers and web developers, the main difference of the above to a conventional RPC or REST(-like) paradigm in HTTP is that, 
``daqpy`` attempts to be a hybrid of both. For instrument control & data-acquisition, it is difficult to move away completely from RPC to REST. Besides, most instrument drivers/hardware 
allow only a single persistent connection instead of multiple clients or computers. Further, when such a client process talks to an instrument, only one instruction can be sent at a time. 
On the other hand, HTTP Servers are multi-threaded or asyncio oriented by design and REST(-like) API honestly does not seem to care how many simultaneous operations are run. To reconcile both, the following 
is proposed:

* ``daqpy`` gives the freedom to choose the HTTP request method & end-point URL desirable for each method, parameter and event
* All HTTP requests will be queued and executed serially unless threaded or made async manually by the programmer 
* Verb like URLs may be used for methods & noun-like URLs are suggested to be used for parameters and events 
* HTTP request method may be mapped as follows:

.. list-table:: 
   :header-rows: 1

   * - HTTP request verb/method
     - remote parameter  
     - remote method 
     - event  
   * - GET
     - read parameter value 
     - run method with a return value with useful data (which may be difficult or illogical as a `parameter`)
     - stream (measured-)data continuously 
   * - POST 
     - add dynamic parameters with certain settings      
     - run python logic, methods that connect/disconnect or issue commands to instruments  
     - not applicable 
   

* Despite the above, an object proxy can also directly access the methods, parameters and events without the details of HTTP like URL end-points and request methods 

Thus, methods executing instrument commands will look like RPC & data fetching from instruments will look *like* REST. On the other hand, an object proxy will purely live in a RPC domain.