Properties In-Depth
===================

Properties expose python attributes to clients & support custom get-set(-delete) functions. 
``hololinked`` uses ``param`` under the hood to implement properties. 

.. toctree::
    :hidden:
    :maxdepth: 1
    
    arguments
    extending

Untyped Property 
-----------------

To make a property take any value, use the base class ``Property``

.. literalinclude:: ../code/properties/untyped.py
    :language: python
    :linenos:
    :lines: 1-11
  
The descriptor object (instance of ``Property``) that performs the get-set operations & auto-allocation 
of an internal instance variable for the property can be accessed by the instance under 
``self.properties.descriptors["<property name>"]``. Expectedly, the value of the property must 
be serializable to be read by the clients. Read the serializer section for further details & customization. 

Custom Typed
------------

To support custom get & set methods so that an internal instance variable is not created automatically, 
use the getter & setter decorator or pass a method to the fget & fset arguments of the property:

.. literalinclude:: ../code/properties/untyped.py
    :language: python
    :linenos:
    :lines: 1-30


Typed Properties
----------------

Certain typed properties are already available in ``hololinked.server.properties``, 
defined by ``param``. 

.. list-table::

    *   - type 
        - property class  
        - options 
    *   - str
        - ``String``
        - comply to regex
    *   - integer 
        - ``Integer`` 
        - min & max bounds, inclusive bounds, crop to bounds, multiples 
    *   - float, integer 
        - ``Number`` 
        - min & max bounds, inclusive bounds, multiples 
    *   - bool 
        - ``Boolean``
        - 
    *   - iterables 
        - ``Iterable``
        - length/bounds, item_type, dtype (allowed type of iterable like list, tuple)
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
        - ``TupleSelector```
        - allowed list of objects 
    *   - class, subclass or instance of an object 
        - ``ClassSelector``
        - instance only or class only 
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

As an example:

.. literalinclude:: ../code/properties/typed.py 
    :language: python
    :linenos:

When providing a custom setter for typed properties, the value is internally validated before 
passing to the setter method. The return value of getter method is never validated and 
is left to the programmer's choice. 