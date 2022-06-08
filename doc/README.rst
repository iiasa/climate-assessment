Auto-documentation of the climate-assessment
============================================

The documentation of climate-assessment is generated from rst files included in this folder.


Dependencies
------------

Install with the package. From the parent directory::

    $ pip install .[docs]


Writing in Restructured Text
----------------------------

There are a number of guides out there, e.g. on docutils_.


Building the docs on your local machine
---------------------------------------

From the command line, run::

    cd doc
    make html

You can then view the site by running::

    cd _build\html
    index.html

Alternatively, you can view the documentation `here <https://iiasa-energy-program-climate-assessment.readthedocs-hosted.com/en/latest/>` ([TODO update if moved]).

.. _docutils: http://docutils.sourceforge.net/docs/user/rst/quickref.html
