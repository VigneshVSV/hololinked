.. hololinked documentation master file, created by
   sphinx-quickstart on Sat Oct 28 22:19:33 2023.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. |module| replace:: hololinked
 
.. |module-highlighted| replace:: ``hololinked``

|module| - Pythonic Supervisory Control & Data Acquisition / Internet of Things
===============================================================================

|module-highlighted| is (supposed to be) a versatile and pythonic tool for building custom control and data acquisition 
software systems. If you have a requirement to capture data from your hardware/instrumentation remotely through your 
domain network, control them, show the data in a browser/dashboard, provide a Qt-GUI or run automated scripts, 
|module-highlighted| can help. Even if you wish to do data-acquisition/control locally in a single computer, one can still 
separate the concerns of GUI & device or integrate with web-browser for a modern interface or use modern web development 
based tools. |module-highlighted| is being developed with the following features in mind:  
 
* being truly pythonic - all code in python & all features of python
* reasonable integration with HTTP to take advantage of modern web practices
* easy to understand & setup
* agnostic to system size & flexibility in topology
* 30FPS 1280*1080*3 (8 bit) image streaming over HTTP

In short - to use it in your home/hobby, in a lab or in a research facility & industry.

|module-highlighted| is primarily object oriented & the building block is the ``RemoteObject`` class. Your instrument 
class (i.e. the python object that controls the hardware) should inherit this class. Each such class provides remote 
methods, remote attributes (also called remote parameters) & events which become accessible on the network through HTTP 
and/or TCP after implementation by the |module-highlighted| developer. Interprocess communication (ZMQ's IPC) is 
available for restriction to single-computer applications. Remote methods can be used to run control and measurement 
operations on your instruments or arbitrary python logic. Remote parameters are type-checked object attributes with 
getter-setter options (identical to python ``property`` with added network access). Events allow to asynchronously push 
arbitrary data to clients. Once such a ``RemoteObject`` is instantiated, it can be connected with a server of choice (one or many). 

Please follow the documentation for examples & tutorials, how-to's and API reference.

.. warning::
   This project is under development and is an idealogical state. Please use it only for playtesting or exploring.

.. note::
   web developers & software engineers, consider reading the :ref:`note <note>` section

.. toctree::
   :maxdepth: 1
   :caption: Contents:

   installation
   examples/index
   How Tos <howto/index>
   autodoc/index
   development_notes


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


last build : |today| UTC