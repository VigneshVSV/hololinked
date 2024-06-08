.. hololinked documentation master file, created by
   sphinx-quickstart on Sat Oct 28 22:19:33 2023.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. |module| replace:: hololinked
 
.. |module-highlighted| replace:: ``hololinked``

.. |base-class-highlighted| replace:: ``Thing``

|module| - Pythonic Supervisory Control & Data Acquisition / Internet of Things
===============================================================================

|module-highlighted| is a versatile and pythonic tool for building custom control and data acquisition 
software systems. If you have a requirement to control and capture data from your hardware/instrumentation remotely through your 
domain network, show the data in a browser/dashboard, provide a Qt-GUI or run automated scripts, 
|module-highlighted| can help. Even if you wish to do data-acquisition/control locally in a single computer, one can still 
separate the concerns of GUI & device or integrate the device with the web-browser for a modern interface or use modern web development 
based tools. The following are the goals:  
 
* being truly pythonic - all code in python & all features of python
* reasonable integration with HTTP to take advantage of modern web practices
* easy to understand & setup
* agnostic to system size & flexibility in topology

In short - to use it in your home/hobby, in a lab or in a research facility & industry.

|module-highlighted| is object oriented and development using it is compatible with the 
`Web of Things <https://www.w3.org/WoT/>`_ recommended pattern for hardware/instrumentation control software. 
Each device or thing can be controlled systematically when their design in software is segregated into properties, 
actions and events. In object orientied case:

* the device is represented by a class
* properties are validated get-set attributes of the class which may be used to model device settings, hold captured/computed data etc.
* actions are methods which issue commands to the device like connect/disconnect, start/stop measurement, or, 
  run arbitrary python logic. 
* events can asynchronously communicate/push data to a client, like alarm messages, measured data etc., 
  say, to refresh a GUI or update a graph. 

The base class which enables this classification is the ``Thing`` class. Any class that inherits the ``Thing`` class can 
instantiate properties, actions and events which become visible to a client in this segragated manner. 

Please follow the documentation for examples, how-to's and API reference to understand the usage.

.. note::
   web developers & software engineers, consider reading the :ref:`note <note>` section

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Contents:
   

   Installation & Examples <installation>
   How Tos <howto/index>
   autodoc/index
   development_notes


:ref:`genindex`

last build : |today| UTC