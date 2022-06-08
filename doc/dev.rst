Notes for developers
********************

Installation
------------
For developers, we recommend using the following command for installation, which needs to be run from the root of the folder after cloning the GitHub repository:

.. code-block:: console

    pip install --editable .[docs,tests,deploy,linter,notebooks]



Formatting code
---------------

Before committing or merging code, the following lines should be run to ensure that the formatting is consistent with what is expected by the continuous integration setup (for users with make installed, ``make checks`` will run these for you):

.. code-block:: console

    black --check src scripts tests setup.py
    isort --check-only --quiet src scripts tests setup.py
    flake8 src scripts tests setup.py


Tips and tricks
---------------

Looking at changes in output
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`git diff --word-diff-regex="[^\",]+"` will show you differences in csv files on the output level (quote and delimter) (see `https://resonantecho.net/software/git/2018/03/29/git-word-diff.html#:~:text=It%20does%20this%20by%20having,word%2Ddiff%2Dregex%3D <https://resonantecho.net/software/git/2018/03/29/git-word-diff.html#:~:text=It%20does%20this%20by%20having,word%2Ddiff%2Dregex%3D>`_.) for more details)
