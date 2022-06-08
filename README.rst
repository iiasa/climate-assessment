WG3 Climate assessment
======================
`ar6climate` provides the possibility to reproduce the climate variable data for the working group III (WGIII or WG3) contribution to the IPCC Sixth Assessment (AR6) report, using climate emulators that were used in the working group I (WGI or WG1) contribution to AR6.
It also allows for assessing new emissions pathways in a way that is fully consistent with AR6.

For the documentation of this package, please go to: [TODO move to public read the docs e.g. climate-assessment.readthedocs.io] https://iiasa-energy-program-climate-assessment.readthedocs-hosted.com/en/latest/.

.. sec-begin-license

License
-------

The WG3 climate assessment workflow license is currently under discussion.
Please do not distribute or use until then.

.. sec-end-license


Development
-----------

Raising an issue
~~~~~~~~~~~~~~~~
If you have a suggestion for development, or find a bug, please report this under: https://github.com/iiasa/climate-assessment/issues.

Running the tests
~~~~~~~~~~~~~~~~~

The tests can be run with ``pytest``. On a Linux system, you should run something like ``MAGICC_PROBABILISTIC_FILE=path/to/probabilistic-file pytest tests``.
Note that for the tests to work properly, you must set up your ``.env`` file (see "Environment" section above).
On Windows, the environment variables (like ``MAGICC_PROBABILISTIC_FILE=path/to/probabilistic-file``) should be set system-wide, and the command reads ``pytest tests``.

Formatting code
~~~~~~~~~~~~~~~

Before committing or merging code, the following lines should be run to ensure that the formatting is consistent with what is expected by the Continuous Integration setup (for users with ``make`` installed, ``make checks`` will run these for you):

.. highlight:: bash

    black src scripts tests setup.py
    isort src scripts tests setup.py
    flake8 src scripts tests setup.py
