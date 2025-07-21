Changelog
=========

All notable changes to this project will be documented in this file.

The format is based on `Keep a Changelog <https://keepachangelog.com/en/1.0.0/>`_, and this project adheres to `Semantic Versioning <https://semver.org/spec/v2.0.0.html>`_.

The changes listed in this file are categorised as follows:

    - Added: new features
    - Changed: changes in existing functionality
    - Deprecated: soon-to-be removed features
    - Removed: now removed features
    - Fixed: any bug fixes
    - Security: in case of vulnerabilities.

master
------

Added
~~~~~
- (`#68 https://github.com/iiasa/climate-assessment/pull/68`_) Update pyam and ixmp4
- (`#64 https://github.com/iiasa/climate-assessment/pull/64`_) Allow to python 3.12
- (`#58 https://github.com/iiasa/climate-assessment/pull/58`_) Update requirements
- (`#50 https://github.com/iiasa/climate-assessment/pull/50`_) Update scmdata and other dependencies and rewrite a few functions
- (`#43 https://github.com/iiasa/climate-assessment/pull/43`_) Add combined CSV output option to :func:`climate_assessment.cli.clim_cli`
- (`#40 https://github.com/iiasa/climate-assessment/pull/40`_) Update awscli to >= 1.29.4
- (`#36 https://github.com/iiasa/climate-assessment/pull/36`_) Update pyam-iamc to >=1.9.0
- (`#31 https://github.com/iiasa/climate-assessment/pull/31`_) Update pyam-iamc to >=1.7.0
- (`#15 <https://github.com/iiasa/climate-assessment/pull/15>`_) Fix packaging issues and add installation instructions
- (`#6 <https://github.com/iiasa/climate-assessment/pull/6>`_) Added example run notebooks and tests thereof
- (`#1 <https://github.com/iiasa/climate-assessment/pull/1>`_) Added :func:`climate_assessment.cli.run_workflow`


Changed
~~~~~~~

- (`#55 https://github.com/iiasa/climate-assessment/pull/55`_) Switched to using poetry for environment management
- (`#55 https://github.com/iiasa/climate-assessment/pull/55`_) Include a ``poetry.lock`` and ``requirements.txt`` in the repo for reproducible environments
- (`#55 https://github.com/iiasa/climate-assessment/pull/55`_) Added pre-commit hook

Fixed
~~~~~

- (`#55 https://github.com/iiasa/climate-assessment/pull/55`_) Pinned requirements to make install more reproducible for users (and updated GitHub CI/CD accordingly)
- (`#55 https://github.com/iiasa/climate-assessment/pull/55`_) Docs build
- (`#55 https://github.com/iiasa/climate-assessment/pull/55`_) CI, with specific mention for now retrieving the infiller database using ixmp4
- (`#49 https://github.com/iiasa/climate-assessment/pull/49`_) Fix if all emissions data starts in 2015, in :func:`add_year_historical_percentage_offset`


v0.1.0 - 2022-06-08
-------------------

Initial release
