Prerequisite knowledge & skills
*******************************

**Code knowledge.**
This package is implemented in the programming language Python.
In order to use this properly, it is expected that you have a basic understanding
of Python, using an Anaconda command prompt, as well as an environment manager
like conda, or know how to install packages using ``pip``.
The workflow extensively uses the packages ``pyam``,`` openscm``, ``scmdata``, and pandas for
operations.
Examples are implemented using Jupyter Notebooks.

**Understanding emissions input files**
This workflow uses the IAMC format used also by pyam for emissions input.
The input emissions must follow the AR6 scenario submission template.
To see which emissions are accepted as input for the climate assessment workflow,
see the file "data/emissions_variable_list_climateruns.xlsx".

**Computing power.**
Running one scenario for all configurations of one simple climate model can easily
take up to one hour on a personal computer. For running scenario sets bigger than
about 10-20 scenarios, you require more computing power. While MAGICC7 and CICERO-SCM
mostly benefit from more cores, FaIR especially requires more RAM.

Tuning parallellisation settings for your specific setup currently requires
delving into the code, editing ``joblib`` settings, and re-installing (e.g. with
``pip install -e .``).

This workflow has been tested on Windows 10 and Linux (Ubuntu).

**Questions.**
For questions, feel free to contact kikstra@iiasa.ac.at or raise an issue at https://github.com/iiasa/climate-assessment/issues
