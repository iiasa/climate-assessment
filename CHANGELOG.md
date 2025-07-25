# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and
this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

The changes listed in this file are categorised as follows:

* Added: new features
* Changed: changes in existing functionality
* Deprecated: soon-to-be removed features
* Removed: now removed features
* Fixed: any bug fixes
* Security: in case of vulnerabilities.

## main

### Added

* ([#74](https://github.com/iiasa/climate-assessment/pull/74)) Fix various issues
* ([#68](https://github.com/iiasa/climate-assessment/pull/68)) Update supported
  dependencies and python versions
* ([#58](https://github.com/iiasa/climate-assessment/pull/58)) Update requirements
* ([#50](https://github.com/iiasa/climate-assessment/pull/50)) Update scmdata and other
  dependencies and rewrite a few functions
* ([#43](https://github.com/iiasa/climate-assessment/pull/43)) Add combined CSV output
  option to `climate_assessment.cli.clim_cli`{.interpreted-text role="func"}
* ([#40](https://github.com/iiasa/climate-assessment/pull/40)) Update awscli to \>=
  1.29.4
* ([#36](https://github.com/iiasa/climate-assessment/pull/36)) Update pyam-iamc to
  \>=1.9.0
* ([#31](https://github.com/iiasa/climate-assessment/pull/31)) Update pyam-iamc to
  \>=1.7.0
* ([#15](https://github.com/iiasa/climate-assessment/pull/15)) Fix packaging issues and
  add installation instructions
* ([#6](https://github.com/iiasa/climate-assessment/pull/6)) Added example run notebooks
  and tests thereof
* ([#1](https://github.com/iiasa/climate-assessment/pull/1)) Added
  `climate_assessment.cli.run_workflow`{.interpreted-text role="func"}

### Changed

* ([#55](https://github.com/iiasa/climate-assessment/pull/55])) Switched to using poetry
  for environment management
* ([#55](https://github.com/iiasa/climate-assessment/pull/55])) Include a `poetry.lock`
    and `requirements.txt` in the repo for reproducible environments
* ([#55](https://github.com/iiasa/climate-assessment/pull/55])) Added pre-commit hook

### Fixed

* ([#55](https://github.com/iiasa/climate-assessment/pull/55])) Pinned requirements to
    make install more reproducible for users (and updated GitHub CI/CD accordingly)
* ([#55](https://github.com/iiasa/climate-assessment/pull/55])) Docs build
* ([#55](https://github.com/iiasa/climate-assessment/pull/55])) CI, with specific
    mention for now retrieving the infiller database using ixmp4
* ([#49](https://github.com/iiasa/climate-assessment/pull/49]) Fix if all emissions data
    starts in 2015, in `add_year_historical_percentage_offset`{.interpreted-text
    role="func"}

## v0.1.0 - 2022-06-08

Initial release
