.. daqpy documentation master file, created by
   sphinx-quickstart on Sat Oct 28 22:19:33 2023.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to daqpy's documentation!
=================================

``daqpy`` is (supposed to be) a versatile and pythonic tool for building control and data acquisition systems. It is also supposed integrate well
with browser based GUI frameworks (like ReactJS). There are a number of packages to build such systems, however most of them lack at least some of the following features:

* not truly pythonic
* harder to understand than other python packages
* many steps to setup
* harder to debug or no line by line debugging as they run within a C/C++ environment
* harder to integrate with HTTP (as HTTP is primarily used for REST and not RPC) 
* not agnostic to system size 

``daqpy`` is a modest attempt to address these issues.  

The building block of ``daqpy`` is the  ``RemoteObject`` class. Your instrument class (i.e. that which controls the hardware) should inherit this class. Each such 
class provides remote methods (method decorated with ``daqpy.server.remote_method`` decorator) and remote attributes (also called parameters) which are type-checked and provide getter-setter method options.
These methods and attributes become available on the network through HTTP (through ``HTTPServer`` instance) or TCP or both. Optionally, there are events (``daqpy.server.Event``) which
allow to asynchronously push arbitrary data to clients.   

It is recommended to use such remote methods to run control and measurement operations on your instruments. Remote parameters must be used to modify settings for your instruments. 
Naturally, such methods and attributes can run arbitrary logic which may not always talk to your hardware. 

To explain the above, the documentation is separated into examples, tutorials (for beginners), how-to's and API reference.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   examples/index



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. note::
   This project is under development and is an idealogical state and should not be used for critical applications.
