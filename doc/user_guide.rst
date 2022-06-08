How to use
**********

Preparation steps before running from Command Line Interface (CLI)
------------------------------------------------------------------

1. Put input emissions csv files in desired folder (suggested: "data")

2. Download the required configuration files for the climate emulator you want to use (see :ref:`emulators`)

3. (optional, but recommended) Download an infiller database like the one used for AR6 (see :ref:`infiller-database`)

4. Open up an anaconda prompt, load the right environment, go to the climate-assessment folder

5. Run ``python scripts/run_workflow.py`` with appropriate arguments

Example usage:
``python scripts/run_workflow.py tests/test-data/ex2.csv output --model "fair" --model-version "1.6.2" --num-cfgs 2237 --probabilistic-file data/emulator/fair/fair-1.6.2-wg3-params-slim.json --fair-extra-config data/emulator/fair/fair-1.6.2-wg3-params-common.json --infilling-database src/climate_assessment/infilling/cmip6-ssps-workflow-emissions.csv``

.. warning::
    The above example uses the very simple and small infiller database "cmip6-ssps-workflow-emissions.csv", which will yield a warning.
    For most applications, it is strongly advised to use a larger infiller database, like the one based on AR6 scenarios.

    Please make sure you have followed the download instructions under :ref:`infiller-database` on how to use the full AR6 setup.

Further examples
----------------
We also provide one worked example as a Jupyter Notebook, namely under ``notebooks/run-example-fair.ipynb``
