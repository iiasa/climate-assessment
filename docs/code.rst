.. currentmodule:: climate_assessment

Core configuration
******************

.. contents:: Table of Contents
   :local:

CLI
===

Infilling database
------------------

.. autofunction:: climate_assessment.cli.create_infiller_database

Infilling
---------

.. autofunction:: climate_assessment.cli.infill

Harmonisation
-------------

.. autofunction:: climate_assessment.cli.harmonize

Harmonisation and infilling
---------------------------

.. autofunction:: climate_assessment.cli._harmonize_and_infill

.. autofunction:: climate_assessment.cli.harmonize_and_infill

.. autofunction:: climate_assessment.cli.harmonization_and_infilling

Workflow
--------

.. autofunction:: climate_assessment.cli.workflow

Climate
-------

.. autofunction:: climate_assessment.cli.clim_cli

Postprocess
-----------

.. autofunction:: climate_assessment.cli._postprocess_worker

.. autofunction:: climate_assessment.cli.postprocess


Infilling
=========

.. autofunction:: climate_assessment.infilling.run_infilling

.. autofunction:: climate_assessment.infilling._infill_variables

.. autofunction:: climate_assessment.infilling._add_to_infilled

.. autofunction:: climate_assessment.infilling.load_csv_or_xlsx_for_one_region

.. autofunction:: climate_assessment.infilling.postprocess_infilled_for_climate

Harmonization
=============

.. autofunction:: climate_assessment.harmonization.postprocessing

.. autofunction:: climate_assessment.harmonization.add_year_historical_percentage_offset

.. autofunction:: climate_assessment.harmonization.run_harmonization

Harmonisation and infilling
===========================

.. autofunction:: climate_assessment.harmonization_and_infilling.harmonization_and_infilling


Climate
=======

.. autofunction:: climate_assessment.climate.climate_assessment

.. autofunction:: climate_assessment.climate.run_and_post_process

.. autofunction:: climate_assessment.climate._get_model_configs_and_out_configs

Postprocess
-----------

.. autofunction:: climate_assessment.climate.post_process.check_hist_warming_period

.. autofunction:: climate_assessment.climate.post_process.calculate_exceedance_probability_timeseries

.. autofunction:: climate_assessment.climate.post_process.calculate_co2_and_nonco2_warming_and_remove_extras

.. autofunction:: climate_assessment.climate.post_process.post_process

Postprocess
===========

.. autofunction:: climate_assessment.postprocess.do_postprocess

Checks on input and output scenario data
========================================

.. automodule:: climate_assessment.checks
   :members:
