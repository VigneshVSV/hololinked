.. daqpy documentation master file, created by
   sphinx-quickstart on Sat Oct 28 22:19:33 2023.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to daqpy's documentation!
=================================

``daqpy`` is (supposed to be) a versatile and pythonic tool for building control and data acquisition software systems. It integrates well
with browser based GUI frameworks (like ReactJS). ``daqpy`` was created & is being designed with the following features in mind:  

* being truly pythonic - all code in python & all features of python
* easy to understand & setup
* agnostic to system size - use it for 1, 10-100 or 1000 instruments
* integrate with HTTP
.. use it in your home, or in a lab or a big facility or industry

The building block of ``daqpy`` is the  ``RemoteObject`` class. Your instrument class (i.e. that which controls the hardware) should inherit this class. Each such 
class provides remote methods, remote attributes (also called remote parameters) & events which become accessible on the network through HTTP and/or TCP
after being implemented by the ``daqpy`` developer. Remote methods can be used to run control and measurement operations on your instruments or arbitrary python logic. 
Remote parameters are type-checked attributes of class which provide getter-setter options (identical to python ``property`` except its exposed to network access). 
Events allow to asynchronously push arbitrary data to clients. Once such a ``RemoteObject`` is instantiated, it can be connected with a HTTP server to be accessible  
by browser clients, among others. 

.. note::
   Web developers & software engineers, consider reading this note 

Please follow the documentation for examples & tutorials, how-to's and API reference.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   examples/index
   autodoc/index
   software-note



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. note::
   This project is under development and is an idealogical state. It should not be used for critical applications, or for that matter in any real world system under operation.
