.. |module-highlighted| replace:: ``hololinked``

Installation & Examples
=======================

.. code:: shell 

    pip install hololinked

One may also clone it from github & install directly (in develop mode). 

.. code:: shell 

    git clone https://github.com/VigneshVSV/hololinked.git

Either install the dependencies in requirements file or one could setup a conda environment from the included ``hololinked.yml`` file 

.. code:: shell 

    conda env create -f hololinked.yml 
    

.. code:: shell 

    conda activate hololinked
    pip install -e .

Also check out:

.. list-table:: 
  
   * - hololinked-examples  
     - https://github.com/VigneshVSV/hololinked-examples.git 
     - repository containing example code discussed in this documentation
   * - hololinked-portal 
     - https://github.com/VigneshVSV/hololinked-portal.git
     - GUI to access ``Thing``s and interact with their properties, actions and events. 

To build & host docs locally, in top directory:

.. code:: shell 

    conda activate hololinked
    cd doc
    make clean 
    make html
    python -m http.server --directory build\html

To open the docs in the default browser, one can also issue the following instead of starting a python server 

.. code:: shell 

    make host-doc