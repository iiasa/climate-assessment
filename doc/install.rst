.. _installation:

Installation
************


.. contents::
   :local:

This package is tested using python 3.9, and has also been used with python 3.7, though continuous integration tests are not run for 3.7.


.. attention:: Due to the better dependency resolution installing with ``pip>=22`` is recommended.


Using :mod:`pip`
================

`pip`_ is Python's default package management system.
If you install Anaconda, then :mod:`pip` is also usable.
:mod:`pip` can also be used when Python is installed directly, *without* using Anaconda.

1. Ensure :mod:`pip` is installed—with Anaconda, or according to the pip documentation.

2. Open a command prompt and run::

    $ pip install climate-assessment


From source
===========

1. (Optional) If you intend to contribute changes to :mod:`climate-assessment`, first register a Github account, and fork the `climate-assessment <https://github.com/iiasa/climate-assessment>`_-repository.
   This will create a new repository :mod:`<user>/climate-assessment`.

2. Clone either the main repository, or your fork; using the `Github Desktop`_ client, or the command line::

    $ git clone git@github.com:iiasa/climate-assessment.git

    # or:
    $ git clone git@github.com:USER/climate-assessment.git

3. Open a command prompt in the :mod:`climate-assessment` directory and type::

    $ pip install --editable .[docs,tests,deploy,linter,notebooks]

   The ``--editable`` flag ensures that changes to the source code are picked up every time :code:`import climate-assessment` is used in Python code.
   The ``[docs,tests,deploy,linter,notebooks]`` extra requirements ensure additional dependencies are installed.


4. (Optional) If installed from source, run the built-in test suite to check that :mod:`climate-assessment` functions correctly on your system::

    $ pytest tests/integration -m "not nightly and not wg3"


.. admonition:: Credits

   The :mod:`message_ix` `documentation <https://iiasa-energy-program-message-ix.readthedocs-hosted.com/en/stable/install.html#installation>`_ was the main source of the text in this :ref:`installation guide <installation>`.


.. _infiller-database:

Infiller database
=================

To reproduce the results from the Sixth Assessment Report Working Group III, one must
download the AR6 infiller database from the AR6 Scenario Explorer. Go to
https://data.ene.iiasa.ac.at/ar6/, log in, and under "Downloads" you will find "Infiller
database for silicone: IPCC AR6 WGIII version (DOI: 10.5281/zenodo.6390768)". Download
that file, and place it in your folder of choice (we suggest
``climate-assessment/data``). After that, you can use the following option
``--infilling-database
data/1652361598937-ar6_emissions_vetted_infillerdatabase_10.5281-zenodo.6390768.csv``
when using the command-line interface.

Climate emulator configuration files
====================================

To reproduce the results from the Sixth Assessment Report Working Group III, one must
download the relevant specific configuration files for the climate emulator you
want to use. See (see :ref:`emulators`) for more information.


.. _pip: https://pip.pypa.io/en/stable/user_guide/
.. _`Github Desktop`: https://desktop.github.com
