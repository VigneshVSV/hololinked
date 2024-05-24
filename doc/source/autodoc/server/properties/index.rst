properties
==========

.. toctree::
    :hidden:
    :maxdepth: 1
    
    types/index
    parameterized
    helpers

.. autoclass:: hololinked.server.property.Property()
    :members:
    :show-inheritance:

.. automethod:: hololinked.server.property.Property.validate_and_adapt

.. automethod:: hololinked.server.property.Property.getter

.. automethod:: hololinked.server.property.Property.setter

.. automethod:: hololinked.server.property.Property.deleter  
   

A few notes:

* The default value of ``Property`` (first argument to constructor) is owned by the Property instance and not the object where the property is attached.
* The value of a constant can still be changed in code by temporarily overriding the value of this attribute or ``edit_constant`` context manager.


