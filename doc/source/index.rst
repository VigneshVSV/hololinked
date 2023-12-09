.. hololinked documentation master file, created by
   sphinx-quickstart on Sat Oct 28 22:19:33 2023.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. |module| replace:: hololinked
 
.. |module-highlighted| replace:: ``hololinked``

Welcome to |module|'s documentation!
====================================

|module-highlighted| is (supposed to be) a versatile and pythonic tool for building custom control and data acquisition software systems. If you have a requirement 
to capture data from your hardware/instruments remotely in your local network, control them, show the data in a browser/dashboard, provide a Qt-GUI or run automated scripts, |module-highlighted| can help. Even if you wish to do 
data-acquisition/control locally in a single computer, one can still separate the concerns of GUI & device or integrate with web-browser for a modern interface. 
|module-highlighted| was created & is being designed with the following features in mind:  
 
* being truly pythonic - all code in python & all features of python
* easy to understand & setup
* reasonable integration with HTTP to take advantage of browser based GUI frameworks (like ReactJS)
* agnostic to system size & flexibility in topology
* 30FPS 1280*1080*3 image streaming over HTTP

In short - to use it in your home/hobby, in a lab or in a big research facility & industry.

|module-highlighted| is primarily object oriented & the building block is the ``RemoteObject`` class. Your instrument class (i.e. the python object that controls the hardware) should inherit this class. Each such 
class provides remote methods, remote attributes (also called remote parameters) & events which become accessible on the network through HTTP and/or TCP 
after implementation by the |module-highlighted| developer. Interprocess communication (ZMQ's IPC) is available for restriction to single-computer applications. 
Remote methods can be used to run control and measurement operations on your instruments or arbitrary python logic. 
Remote parameters are type-checked object attributes with getter-setter options (identical to python ``property`` with added network access). 
Events allow to asynchronously push arbitrary data to clients. Once such a ``RemoteObject`` is instantiated, it can be connected with the server of choice. 

.. note::
   web developers & software engineers, consider reading the :ref:`note <note>` section

Please follow the documentation for examples & tutorials, how-to's and API reference.

.. toctree::
   :maxdepth: 1
   :caption: Contents:

   installation
   examples/index
   benchmark/index
   autodoc/index
   note


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. note::
   This project is under development and is an idealogical state. Please use it only for playtesting or exploring.
