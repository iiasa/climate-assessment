# `climate-assessment` - Assessing the climate outcomes of future emissions scenarios

[![image](https://zenodo.org/badge/501176611.svg)](https://zenodo.org/badge/latestdoi/501176611)

------------------------------------------------------------------------

*Please note that `climate-assessment` is still in early developmental stages, thus*
*all interfaces are subject to change.*

The package `climate-assessment` provides the possibility to reproduce the climate
variable data for the working group III (WGIII or WG3) contribution to the IPCC Sixth
Assessment (AR6) report, using climate emulators that were used in the working group I
(WGI or WG1) contribution to AR6. It also allows for assessing new emissions pathways in
a way that is fully consistent with AR6.

## Installation

Note: the package's requirements are currently extremely strict. This is done to make it
more likely that installation will result in a valid environment. If you want a fully
specified environment, please use the `poetry.lock` or `requirements.txt` file provided
in this repository. We hope to make the package more libary-like, with looser
requirements, in future.

### Using `pip`

[pip](https://pip.pypa.io/en/stable/user_guide/) is Python's default package management
system.

> [!CAUTION]
> Due to the better dependency resolution installing with `pip>=22` is
> recommended.

If you install Anaconda, then `pip` is also usable. `pip` can also be used when Python
is installed directly, *without* using Anaconda.

1. Ensure `pip` is installed ---with Anaconda, or according to the pip documentation.
2. Open a command prompt and run:

```console
  pip install climate-assessment
```

### From source

(Optional) If you intend to contribute changes to `climate-assessment`, installing
directly from [source](https://github.com/iiasa/climate-assessment) is the way to go.

Detailed instructions on how to do this can be found in the
documentation under
<https://climate-assessment.readthedocs.io/en/latest/install.html>.

## Documentation

All documentation, including installation instructions, can be found at
<https://climate-assessment.readthedocs.io/>.

## License

Licensed under an MIT License. See the LICENSE file for more
information.

## Development

### Raising an issue

If you have a suggestion for development, or find a bug, please report
this under: <https://github.com/iiasa/climate-assessment/issues>.

### Running the tests

The tests can be run with `pytest`. On a Linux system, you should run something like
`MAGICC_PROBABILISTIC_FILE=path/to/probabilistic-file pytest tests`. Note that for the
tests to work properly, you must set up your `.env` file (see \"Environment\" section
above). On Windows, the environment variables (like
`MAGICC_PROBABILISTIC_FILE=path/to/probabilistic-file`) should be set system-wide, and
the command reads `pytest tests`.

### Formatting code

Before committing or merging code, the following lines should be run to
ensure that the formatting is consistent with what is expected by the
Continuous Integration setup (for users with `make` installed,
`make checks` will run these for you):

``` bash
black src scripts tests setup.py
isort src scripts tests setup.py
flake8 src scripts tests setup.py
```
