Common arguments to all parameters 
==================================

``allow_None``, ``constant`` & ``readonly`` 
+++++++++++++++++++++++++++++++++++++++++++

* if ``allow_None`` is ``True``, parameter supports ``None`` apart from its own type
* ``readonly`` (being ``True``) makes the parameter read-only or execute the getter method
* ``constant`` (being ``True``), again makes the parameter read-only but can be set once if ``allow_None`` is ``True``. 
  This is useful the set the parameter once at ``__init__()`` but remain constant after that.

.. literalinclude:: ../code/parameters/common_arg_1.py
    :language: python
    :linenos:

``default``, ``class_member``, ``fget``, ``fset`` & ``fdel``
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

To provide a getter-setter (& deleter) method is optional. If none given, value is stored inside 
the instance's ``__dict__`` under the name `<parameter name given>_param_value`. If no such 
value was stored originally because a value assignment was never called on the parameter, say during 
``__init__``, ``default`` is returned.  

If a setter/deleter is given, getter is mandatory. In this case, ``default`` is also ignored & the getter is 
always executed. If default is desirable, one has to return it manually in the getter method by 
accessing the parameter descriptor object directly. 

If ``class_member`` is True, the value is set in the class' ``__dict__`` instead of instance's ``__dict__``. 
Custom getter-setter-deleter are not compatible with this option currently. ``class_member`` takes precedence over fget-fset-fdel, 
which in turn has precedence over ``default``.

.. literalinclude:: ../code/parameters/common_arg_2.py
    :language: python
    :linenos:
    :lines: 5-28

``doc`` and ``label``
++++++++++++++++++++++

``doc`` allows clients to fetch a docstring for the parameter. ``label`` can be used to show the parameter 
in a GUI for example. hololinked-portal uses these two values in the same fashion. 

``remote``
++++++++++

setting remote to False makes the parameter local, this is still useful to type-restrict python attributes to 
provide an interface to other developers using your class, for example, when someone else inherits your ``RemoteObject``. 

``URL_path`` and ``http_method``
++++++++++++++++++++++++++++++++

This setting is applicable only to the ``HTTPServer``. ``URL_path`` makes the parameter available for 
getter-setter-deleter methods at the specified URL. The default http request verb/method for getter is GET, 
setter is PUT and deleter is DELETE. If one wants to change the setter to POST method instead of PUT, 
one can set ``http_method = ("GET", "POST", "DELETE")``. Even without the custom getter-setter 
(which generates the above stated internal name for the parameter), one can modify the ``http_method``. 
Setting any of the request methods to ``None`` makes the parameter in-accessible for that respective operation.

``state``
+++++++++

When ``state`` is specifed, the parameter is writeable only when the RemoteObject's StateMachine is in that state (or 
in the list of allowed states). This is also currently applicable only when set operations are called by clients.
Local set operations are always executed irrespective of the state machine state. A get operation is always executed as 
well even from the clients irrespective of the state. 

``metadata``
++++++++++++

This dictionary allows storing arbitrary metadata in a dictionary. For example, one can store units of the physical 
quantity. 

``db_init``, ``db_commit`` & ``db_persist``
+++++++++++++++++++++++++++++++++++++++++++

Parameters can be stored & loaded in a database if necessary when the ``RemoteObject`` is stopped and restarted. 

* ``db_init`` only loads a parameter from database, when the value is changed, its not written back to the database. 
  For this option, the value has to be pre-created in the database in some other fashion. hololinked-portal can help here.  

* ``db_commit`` only writes the value into the database when an assignment is called. 

* ``db_persist`` both stores and loads the parameter from the database. 

Supported databases are MySQL, Postgres & SQLite currently. Look at database how-to for supply database configuration. 

