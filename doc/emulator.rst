.. currentmodule:: climate_assessment

.. _emulators:

Climate emulators
*****************

In this section, we provide more information specifically on how the climate emulators used in IPCC AR6 WGIII can be used with this package, and where to find more information.

When you have a scenario with sufficient information on its emissions pathways (see {link-to-input-requirements-page}), you can run the climate assessment process with an emulator of choice, producing probabilistic output. Three emulators are available: MAGICCv7.5.3, FaIRv1.6.2, and CICERO-SCM.

Emulators are run using the functionality in the ``openscm-runner`` package (see `documentation <https://openscm-runner.readthedocs.io/en/latest/>`_), which is a wrapper that allows for running simple climate models with a unified interface.

In general, if you have a working setup on your computer and this package installed, you need two things to make everything work:

#. The climate emulator itself: for CICERO and FaIR this is provided through the package, for MAGICC the binary file should be downloaded.
#. Configuration file(s) for the climate emulator: this data is provided externally as much as possible to keep code and data separate (e.g. for MAGICC and FaIR), though for CICERO the data is for now made available through this package.

In the example notebook, ``notebooks/run-example-fair.ipynb``, we provide an example of how the configuration files can be downloaded for FaIR using `pooch <https://www.fatiando.org/pooch/latest/api/generated/pooch.retrieve.html>`_.

.. warning::
    In the examples below, the commands use the very simple and small infiller database "cmip6-ssps-workflow-emissions.csv", which will yield a warning.
    For most applications, it is strongly advised to use a larger infiller database, like the one based on AR6 WG3 scenarios.

    Please make sure you have followed the download instructions under :ref:`infiller-database` on how to use the full AR6 setup.


.. contents:: Table of Contents
   :local:

FaIR
====

Download instructions
---------------------
FaIR itself does not need to be downloaded. Upon installing this package, it is ready to go on any computer platform.

However, the configuration files for FaIR do need to be downloaded.
This can be done either manually from https://doi.org/10.5281/zenodo.5513022, or interactively using a tool such as `pooch <https://www.fatiando.org/pooch/latest/api/generated/pooch.retrieve.html>`_.
In the example notebook, ``notebooks/run-example-fair.ipynb``, we provide an example of how this can be done.


Setup instructions
------------------
FaIR is implemented in Python, and nothing has to be done to run it after you have installed this package; it is provided through ``openscm-runner``.
The only thing that is required, is running with the correct location for the FaIR probabilistic input files (after you have downloaded these).
FaIR uses two input files in this implementation, that need to be called as follows: ``--probabilistic-file path/to/fair-1.6.2-wg3-params-slim.json`` and ``--fair-extra-config path/to/fair-1.6.2-wg3-params-common.json``

Example run command
-------------------
 .. code-block:: console

    python scripts/run_workflow.py data/input_scenarios.csv output --model "FaIR" --model-version "1.6.2" --num-cfgs 2237 --probabilistic-file data/fair/fair-1.6.2-wg3-params-slim.json --fair-extra-config data/fair/fair-1.6.2-wg3-params-common.json --infilling-database src/climate_assessment/infilling/cmip6-ssps-workflow-emissions.csv


Emulator-specific functions
---------------------------
.. autofunction:: climate_assessment.climate.get_fair_configurations

References
----------
Please refer to this paper for more detailed use: Smith, C. J., Forster, P. M., Allen, M., Leach, N., Millar, R. J., Passerello, G. A., and Regayre, L. A.: FAIR v1.3: a simple emissions-based impulse response and carbon cycle model, 11, 2273–2297, https://doi.org/10.5194/gmd-11-2273-2018, 2018.

* Documentation: `FaIR ReadTheDocs <https://fair.readthedocs.io/en/latest/>`_
* Open-source code: `FaIR GitHub <https://github.com/OMS-NetZero/FAIR/>`_
* Calibrated and constrained parameter set (as one single file): https://doi.org/10.5281/zenodo.5513022


CICERO-SCM
==========

Download instructions
---------------------
CICERO-SCM does not need to be downloaded. Upon installing this package, it works on Linux.
It is not yet possible to run this version of CICERO-SCM on Windows or on MacOS.
For now, the configuration file for CICERO-SCM is also available with this package directly, under `data/cicero/subset_cscm_configfile.json`.

Setup instructions for a Linux computer
---------------------------------------
CICERO-SCM is provided through ``openscm-runner``.
The only thing that is required, is running with the correct location for the CICERO-SCM probabilistic input file, which needs to be called as follows: ``--probabilistic-file path/to/subset_cscm_configfile.json``

Setup instructions for a Windows or MacOS computer
--------------------------------------------------
Not yet available.

Example run command
-------------------
 .. code-block:: console

    python scripts/run_workflow.py data/input_scenarios.csv output --model "ciceroscm" --model-version "v2019vCH4" --num-cfgs 600 --probabilistic-file data/cicero/subset_cscm_configfile.json --infilling-database src/climate_assessment/infilling/cmip6-ssps-workflow-emissions.csv


Emulator-specific functions
---------------------------
.. autofunction:: climate_assessment.climate.get_ciceroscm_configurations

References
----------
Please refer to this paper for more detailed use: Skeie, R. B., Fuglestvedt, J., Berntsen, T., Peters, G. P., Andrew, R., Allen, M., and Kallbekken, S.: Perspective has a strong effect on the calculation of historical contributions to global warming, Environ. Res. Lett., 12, 024022, https://doi.org/10.1088/1748-9326/aa5b0a, 2017.

* Calibrated and constrained parameter set (as one single file): see ``data/cicero/subset_cscm_configfile.json``


MAGICC
======

Download instructions
---------------------
The MAGICC model is available at `magicc.org <https://magicc.org/>`_, where you can also download the parameter set used in AR6.
Please read the license and expectations carefully, we rely on users to act in a way which brings both new scientific outcomes but also acknowledges the work put into the MAGICC AR6 setup.

After you have downloaded the tar files, please extract it (we typically extract MAGICC and the probabilistic distribution into ``magicc-files``).
You then need to copy all the default files into the run folder (i.e. run a command like ``cp -r magicc-files/magicc-v7.5.3/run/defaults/* magicc-files/magicc-v7.5.3/run/``).

In one set of commands on Linux (PRs to add the Windows equivalent are welcome), this can be summarised as:

.. code-block:: console

    # MAGICC binary
    mkdir -p magicc-files/magicc-v7.5.3
    wget -O magicc-files/magicc-v7.5.3.tar.gz [magicc-link-from-magicc-dot-org]
    tar -xf magicc-files/magicc-v7.5.3.tar.gz -C magicc-files/magicc-v7.5.3
    cp -r magicc-files/magicc-v7.5.3/run/defaults/* magicc-files/magicc-v7.5.3/run/

    # Probabilistic distribution
    mkdir -p magicc-files/magicc-ar6-0fd0f62-f023edb-drawnset
    wget -O magicc-files/magicc-ar6-0fd0f62-f023edb-drawnset.tar.gz [magicc-prob-distribution-link-from-magicc-dot-org]
    tar -xf magicc-files/magicc-ar6-0fd0f62-f023edb-drawnset.tar.gz -C magicc-files/magicc-ar6-0fd0f62-f023edb-drawnset

Setup instructions for a Linux computer
---------------------------------------
For a Linux computer, these environment variables can be provided either via a ``.env`` file (see ``.env.sample`` in the root directory of this repository) or from the command line.

Setup instructions for a macOS computer
---------------------------------------
We don't currently have a compiled macOS binary in our distribution (we are working on it but mac runners have only recently become widely available).
If you need this for your use case, please email zebedee.nicholls@climate-energy-college.org.

Setup instructions for a Windows computer
-----------------------------------------
On Windows, environment variables cannot be set using an input file.
Rather, one must set the following system-wide environment variables, with the paths depending on where you put your MAGICC7 emulator files.
Below, we provide some examples with their functions.
Note that these are the same as in the ``.env.sample`` file.

.. code-block:: console

    # MAGICC executable.
    MAGICC_EXECUTABLE_7 = /path/to/climate-assessment/data/emulator/magicc/magicc-v7.5.3/bin/magicc.exe
    # MAGICC probabilistic input setup file.
    MAGICC_PROBABILISTIC_FILE = /path/to/climate-assessment/data/emulator/magicc/0fd0f62-derived-metrics-id-f023edb-drawnset.json
    # Number of (hyperthreaded) cores to run on.
    MAGICC_WORKER_NUMBER = 4
    # Folder for MAGICC parallel workers (make sure that this folder exists!):
    MAGICC_WORKER_ROOT_DIR = /path/to/climate-assessment/data/emulator/magicc/magicc-v7.5.3/workers

Example run command
-------------------
 .. code-block:: console

    python scripts/run_workflow.py data/input_scenarios.csv output --model "magicc" --model-version "v7.5.3" --num-cfgs 600 --probabilistic-file data/emulator/magicc/0fd0f62-derived-metrics-id-f023edb-drawnset.json --infilling-database src/climate_assessment/infilling/cmip6-ssps-workflow-emissions.csv --co2-and-non-co2-warming


Emulator-specific functions
---------------------------
.. autofunction:: climate_assessment.climate.get_magicc7_configurations

References
----------
Please refer to the following for more detailed use:

  | Nicholls, Z. R. J., Meinshausen, M., Lewis, J., Smith, C. J., Forster, P. M., Fuglestvedt, J. S., Rogelj, J., Kikstra, J. S., Riahi, K., and Byers, E.
  | "Changes in IPCC Scenario Assessment Emulators Between SR1.5 and AR6 Unraveled".
  | *Geophysical Research Letters*
  | https://doi.org/10.1029/2022GL099788
  | 2022

* More information, multiple references, and an interactive online tool: `magicc.org <https://magicc.org/>`_


Advanced functionality
======================
When running from the command line with CLI option ``--save-raw-climate-output``, an additional output folder will be created which writes out one large (~300-1000MB) file per scenario.

Notes for developers
====================
If you would like to get the MAGICC SR15 tests running, you will first need to run the command ``MAGICC_RUN_DIR=bin/magicc/magicc-v7.5.3/run/ python scripts/generate-magicc-sr15-input-files.py`` from your Anaconda prompt.
N.B. note that this way of running a command, with the environment variable provided before the python call, only works on Linux. On Windows, you need to set MAGICC_RUN_DIR as a system-wide environment variable and then only run ``python scripts/generate-magicc-sr15-input-files.py``.
