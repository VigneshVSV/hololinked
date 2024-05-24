properties
==========

.. toctree::
    :hidden:
    :maxdepth: 1
    
    string 
    number
    integer
    selector 
    class_selector
    boolean
    tuple 
    list


Property
--------

.. autoclass:: hololinked.server.property.Property()
    :members:
    :show-inheritance:


Notes 
=====

* The default value of ``Property`` is owned by the Property instance and not the object where the property is attached.
* The value can still be changed in code by temporarily overriding the value of this slot and then restoring it, which is useful 
for reporting values that the  _user_ should never change but which do change during code execution.


