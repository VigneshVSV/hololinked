Properties In-Depth
===================

Properties expose python attributes to clients & support custom get-set(-delete) functions. 
``hololinked`` uses ``param`` under the hood to implement properties, which in turn uses the
descriptor protocol. Python's own ``property`` is not supported 
for remote access due to limitations in using foreign attributes within the ``property`` object. Said limitation 
causes redundancy with implementation of ``hololinked.server.Property``, nevertheless, the term ``Property`` 
(with capital 'P') is used to comply with the terminology of Web of Things. 

.. toctree::
    :hidden:
    :maxdepth: 1
    
    arguments
..     extending

Untyped/Custom typed Property 
-----------------------------

To make a property take any value, use the base class ``Property``:

.. literalinclude:: ../code/properties/untyped.py
    :language: python
    :linenos:
    :lines: 1-10, 35-37
  
The descriptor object (instance of ``Property``) that performs the get-set operations & auto-allocation 
of an internal instance variable for the property can be accessed by the instance under 
``self.properties.descriptors["<property name>"]``:

.. literalinclude:: ../code/properties/untyped.py
    :language: python
    :linenos:


Expectedly, the value of the property must be serializable to be read by the clients. Read the serializer 
section for further details & customization. 

Typed Properties
----------------

Certain typed properties are already available in ``hololinked.server.properties``, 
defined by ``param``:

.. list-table::

    *   - type 
        - Property class  
        - options 
    *   - str
        - ``String``
        - comply to regex
    *   - float, integer 
        - ``Number`` 
        - min & max bounds, inclusive bounds, crop to bounds, multiples 
    *   - integer 
        - ``Integer`` 
        - same as ``Number``
    *   - bool 
        - ``Boolean``
        - tristate if ``allow_None=True``
    *   - iterables 
        - ``Iterable``
        - length/bounds, item_type, dtype (allowed type of the iterable itself like list, tuple etc.)
    *   - tuple 
        - ``Tuple`` 
        - same as iterable 
    *   - list 
        - ``List`` 
        - same as iterable  
    *   - one of many objects 
        - ``Selector``
        - allowed list of objects 
    *   - one or more of many objects 
        - ``TupleSelector``
        - allowed list of objects 
    *   - class, subclass or instance of an object 
        - ``ClassSelector``
        - comply to instance only or class/subclass only 
    *   - path, filename & folder names 
        - ``Path``, ``Filename``, ``Foldername``
        - 
    *   - datetime 
        - ``Date``
        - format
    *   - typed list 
        - ``TypedList``
        - typed appends, extends 
    *   - typed dictionary
        - ``TypedDict``, ``TypedKeyMappingsDict``
        - typed updates, assignments    

More examples:

.. literalinclude:: ../code/properties/typed.py 
    :language: python
    :linenos:

For typed properties, before the setter is invoked, the value is internally validated. 
The return value of getter method is never validated and is left to the developer's caution. 