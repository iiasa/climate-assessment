import logging
import os.path
from concurrent.futures import ProcessPoolExecutor, as_completed

import click
import pandas as pd
import pyam
from tqdm import tqdm

from .checks import (
    infiller_vetting,
    perform_input_checks,
    sanity_check_bounds_kyoto_emissions,
    sanity_check_comparison_kyoto_gases,
)
from .climate import DEFAULT_MAGICC_VERSION, climate_assessment
from .climate.post_process import check_hist_warming_period
from .harmonization import run_harmonization
from .harmonization_and_infilling import harmonization_and_infilling
from .infilling import postprocess_infilled_for_climate, run_infilling
from .postprocess import do_postprocess
from .utils import (
    _add_variables,
    add_gwp100_kyoto_wrapper,
    columns_to_basic,
    extract_ips,
    init_logging,
    split_df,
    split_scenarios_into_batches,
)

LOGGER = logging.getLogger(__name__)

input_emissions_file_arg = click.argument(
    "input_emissions_file",
    required=True,
    type=click.Path(exists=True, dir_okay=False, readable=True, resolve_path=True),
)
outdir_arg = click.argument(
    "outdir",
    required=True,
    type=click.Path(exists=True, file_okay=False, writable=True, resolve_path=True),
)
output_files_arg = click.argument(
    "rawoutput_files",
    nargs=-1,
    type=click.Path(exists=True, file_okay=True, resolve_path=True),
)
harmonizedinfilledemissions_arg = click.argument(
    "harmonizedinfilledemissions",
    type=click.Path(exists=True, dir_okay=False, readable=True, resolve_path=True),
)
n_workers_option = click.option(
    "--n_workers",
    help="Number of workers",
    default=8,
    type=int,
)
output_file_option = click.option(
    "--output-file",
    help="Filename where the combined metadata is output",
    required=True,
)
input_check_option = click.option(
    "--inputcheck/--no-inputcheck",
    help="Check input before running the workflow",
    required=False,
    default=True,
    show_default=True,
)
infilling_database_option = click.option(
    "--infilling-database",
    help="File to use as the infilling database",
    required=False,  # defaults to infiller database used for ar6
    default=os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "infilling",
            "cmip6-ssps-workflow-emissions.csv",
        )
    ),
    type=click.Path(exists=True, file_okay=True, readable=True, resolve_path=True),
    show_default=True,
)
harmonization_instance_option = click.option(
    "--harmonization-instance",
    help="Harmonisation settings to use",
    required=False,  # defaults to rcmip historical data as used for ar6
    default="ar6",
    type=click.Choice(["ar6", "sr15"], case_sensitive=True),
    show_default=True,
)
model_option = click.option(
    "--model",
    help="Climate model to run scenarios with",
    required=False,
    default="magicc",
    type=str,
    show_default=True,
)
model_version_option = click.option(
    "--model-version",
    help="Expected model version (just used to check env is working as intended)",
    default=DEFAULT_MAGICC_VERSION,
    type=str,
    show_default=True,
)
probabilistic_file_option = click.option(
    "--probabilistic-file",
    help="json file containing climate model probabilistic config",
    required=True,  # currenlty no default here, users need to locate it
    type=click.Path(exists=True, dir_okay=False, readable=True, resolve_path=True),
)
magicc_extra_config_option = click.option(
    "--magicc-extra-config",
    help="File containing additional MAGICC config",
    required=False,
    type=click.Path(exists=True, dir_okay=False, readable=True, resolve_path=True),
)
fair_extra_config_option = click.option(
    "--fair-extra-config",
    help="File containing additional FaIR config",
    required=False,  # required when running FaIR
    type=click.Path(exists=True, dir_okay=False, readable=True, resolve_path=True),
)
hist_warming_option = click.option(
    "--historical-warming",
    help="Historical warming estimate in kelvin",
    required=False,  # defaults to WGI estimated historical warming
    default=0.85,
    type=float,
    show_default=True,
)
hist_warming_ref_period_option = click.option(
    "--historical-warming-reference-period",
    help="Reference period used when calculating historical warming",
    required=False,
    default="1850-1900",
    type=str,
    show_default=True,
)
hist_warming_eval_period_option = click.option(
    "--historical-warming-evaluation-period",
    help="Evaluation period used when calculating historical warming",
    required=False,
    default="1995-2014",
    type=str,
    show_default=True,
)
num_cfgs_option = click.option(
    "--num-cfgs",
    help="Number of climate model configs to run",
    default=600,
    type=int,
    show_default=True,
)
test_run_option = click.option(
    "--test-run/--no-test-run",
    help="Make this run a test run (doesn't check that historical warming"
    "from the climate models comes out consistently)",
    default=False,
    type=bool,
    show_default=True,
)
scenario_batch_size_option = click.option(
    "--scenario-batch-size",
    help="Number of scenarios to run at a time",
    required=False,
    default=20,
    type=int,
    show_default=True,
)
save_raw_climate_output_option = click.option(
    "--save-raw-climate-output/--dont-save-raw-climate-output",
    help="Save raw climate output to disk",
    required=False,
    default=False,
    type=bool,
    show_default=True,
)
categorisation_option = click.option(
    "--categorisation/--no-categorisation",
    help="Add temperature category to meta data",
    required=False,
    default=True,
    show_default=True,
)
report_completeness_option = click.option(
    "--reporting-completeness-categorisation/"
    "--no-reporting-completeness-categorisation",
    help="Add an emissions reporting completeness category to meta data",
    required=False,
    default=False,
    type=bool,
    show_default=True,
)
nonco2_warming_option = click.option(
    "--co2-and-non-co2-warming/--no-co2-and-non-co2-warming",
    help="Include CO2 and non-CO2 warming assessment",
    required=False,
    default=False,
    type=bool,
    show_default=True,
)
prefix_all_out_variables_option = click.option(
    "--prefix", help="Prefix for all output variables", required=True
)
prefix_option = click.option(
    "--prefix",
    help="Prefix for all variable names",
    required=False,
    default="AR6 climate diagnostics",
    type=str,
    show_default=True,
)
gwp_option = click.option(
    "--gwp/--no-gwp",
    help="Add Kyoto Gases in GWP100 to output",
    required=False,
    default=True,
    type=bool,
    show_default=True,
)
gwp_def_false_option = click.option(
    "--gwp/--no-gwp",
    help="Add Kyoto Gases in GWP100 to output",
    default=False,
    type=bool,
    show_default=True,
)
kyoto_ghgs_option = click.option(
    "--kyoto-ghgs", help="Add Kyoto GHGs to output", default=True
)
postprocess_option = click.option(
    "--postprocess/--no-postprocess",
    help="Run postprocessing steps",
    default=True,
    type=bool,
    show_default=True,
)
harmonize_option = click.option(
    "--harmonize/--dont-harmonize",
    help="Do harmonization",
    default=True,
    type=bool,
    show_default=True,
)
save_csv_combined_output_option = click.option(
    "--save-csv-combined-output",
    help="Write CSV output with combined climate output and emissions",
    is_flag=True,
    required=False,
    default=False,
    type=bool,
    show_default=True,
)


def _setup_logging(logger):
    """
    Set up logging preferences. This removes unnecessary logger warnings from
    packages that the workflow depends on, most notably pyam. It also sets the
    general logger level to INFO.

    Parameters
    ----------
    logger : :class:`logging.getLogger`
        Input Logger instance created by logging.getLogger(name).
    """
    init_logging(logger)

    logger.info("Silencing pyam loggers")
    logging.getLogger("pyam.core").setLevel(logging.CRITICAL)
    logging.getLogger("pyam.utils").setLevel(logging.CRITICAL)


def _get_key_string_and_log_outdir(input_emissions_file, outdir, logger):
    # TODO: remove need to parse in logger once we've cleaned things up
    logger.info("Outputs will be saved in: %s", outdir)
    key_string = os.path.splitext(os.path.basename(input_emissions_file))[0]
    logger.info("Outputs will be saved with the ID: %s", key_string)

    return key_string


def _load_emissions_convert_to_basic(input_emissions_file, logger):
    # TODO: remove need to parse in logger once we've cleaned things up
    logger.info("Loading %s", input_emissions_file)
    input_df = pyam.IamDataFrame(input_emissions_file)

    logger.info("Converting to basic columns i.e. removing any extra columns")
    input_df = columns_to_basic(input_df)

    return input_df


def _input_checks(input_df, inputcheck, key_string, outdir):
    """
    Simple wrapper to call climate assessment workflow native emissions input
    checks, for a chosen set of checks.

    Returns IAM dataframe with only model-scenario that will be  without emissions.
    Output also includes the input emissions. The output is interpolated
    onto an annual timestep.

    For more information, see the code description under
    :func:`climate_assessment.checks.perform_input_checks`.
    """
    if inputcheck:
        LOGGER.info("Performing input data checks")
        df = perform_input_checks(
            input_df,
            output_csv_files=True,
            output_filename=key_string,
            lead_variable_check=True,
            outdir=outdir,
        )

    else:
        df = input_df.copy()

    return df


def _harmonize_and_infill(
    input_df,
    inputcheck,
    key_string,
    outdir,
    infilling_database,
    harmonize,
    prefix,
    harmonization_instance,
):
    """
    Thin wrapper function for running both harmonization and infilling.

    Returns True if there are scenarios that can be run by a climate
    emulator. Those scenarios are not returned by this function, but rather
    written to the outdir. Returns False if there are no complete scenarios
    to be run.

    For more information, see the code description under
    :func:`climate_assessment.harmonization_and_infilling.harmonization_and_infilling`.
    """
    df = _input_checks(input_df, inputcheck, key_string, outdir)

    ##################################
    # run HARMONIZATION and INFILLING (writes out results, returns True or False, includes some post-infilling checks)
    ##################################
    # TODO: split harmonization and infilling steps
    # TODO: remove 'instance' and put config somewhere more sane
    # TODO: remove prefix when we change to the new aneris interface
    assessable = harmonization_and_infilling(
        df,
        key_string,
        infilling_database,
        outdir=outdir,
        do_harmonization=harmonize,
        prefix=prefix,
        instance=harmonization_instance,
    )

    return assessable


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@input_emissions_file_arg
@outdir_arg
@input_check_option
@magicc_extra_config_option
@fair_extra_config_option
@model_option
@model_version_option
@probabilistic_file_option
@num_cfgs_option
@hist_warming_option
@hist_warming_ref_period_option
@hist_warming_eval_period_option
@test_run_option
@scenario_batch_size_option
@infilling_database_option
@save_raw_climate_output_option
@postprocess_option
@categorisation_option
@report_completeness_option
@harmonize_option
@prefix_option
@gwp_option
@harmonization_instance_option
@nonco2_warming_option
def workflow(
    input_emissions_file,
    outdir,
    inputcheck,
    magicc_extra_config,
    fair_extra_config,
    model,
    model_version,
    probabilistic_file,
    num_cfgs,
    historical_warming,
    historical_warming_reference_period,
    historical_warming_evaluation_period,
    test_run,
    scenario_batch_size,
    infilling_database,
    save_raw_climate_output,
    postprocess,
    categorisation,
    reporting_completeness_categorisation,
    harmonize,
    prefix,
    harmonization_instance,
    co2_and_non_co2_warming,
    gwp,
):
    # TODO: remove "model_version" and `num_cfgs` as mandatory
    #  options for AR6 release, as there should only be one option per emulator.
    """
    Run the full IPCC AR6 climate asessment workflow.

    Example usage: ``python scripts/run_workflow.py tests/test-data/ex2.csv output --model "FaIR" --model-version "1.6.2" --num-cfgs 2237 --probabilistic-file tests/test-data/fair-1.6.2-wg3-params-slim.json --fair-extra-config tests/test-data/fair-1.6.2-wg3-params-common.json --infilling-database src/climate_assessment/infilling/cmip6-ssps-workflow-emissions.csv``

    See further documentation at :ref:`Description of the workflow <workflow>`.
    """
    LOGGER = logging.getLogger("workflow")
    _setup_logging(LOGGER)

    run_workflow(
        input_emissions_file,
        outdir,
        model,
        model_version,
        probabilistic_file,
        num_cfgs,
        inputcheck=inputcheck,
        magicc_extra_config=magicc_extra_config,
        fair_extra_config=fair_extra_config,
        historical_warming=historical_warming,
        historical_warming_reference_period=historical_warming_reference_period,
        historical_warming_evaluation_period=historical_warming_evaluation_period,
        test_run=test_run,
        scenario_batch_size=scenario_batch_size,
        infilling_database=infilling_database,
        save_raw_climate_output=save_raw_climate_output,
        postprocess=postprocess,
        categorisation=categorisation,
        reporting_completeness_categorisation=reporting_completeness_categorisation,
        harmonize=harmonize,
        prefix=prefix,
        harmonization_instance=harmonization_instance,
        co2_and_non_co2_warming=co2_and_non_co2_warming,
        gwp=gwp,
    )


# TODO: move to a new home (probably)
def run_workflow(
    input_emissions_file,
    outdir,
    model,
    model_version,
    probabilistic_file,
    num_cfgs,
    inputcheck=True,
    magicc_extra_config=None,
    fair_extra_config=None,
    historical_warming=0.85,
    historical_warming_reference_period="1850-1900",
    historical_warming_evaluation_period="1995-2014",
    test_run=False,
    scenario_batch_size=10,
    infilling_database=os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "infilling",
            "cmip6-ssps-workflow-emissions.csv",
        )
    ),
    save_raw_climate_output=False,
    postprocess=True,
    categorisation=True,
    reporting_completeness_categorisation=False,
    harmonize=True,
    prefix="AR6 climate diagnostics",
    harmonization_instance="ar6",
    co2_and_non_co2_warming=False,
    gwp=True,
):
    """
    Run the workflow

    Parameters
    ----------
    input_emissions_file : str
        Path to input emissions file. This must be read off disk because we use
        the filename to help name output files. PRs welcome to split off an interface
        which runs in memory.

    outdir : str
        Where to save the output

    model : str
        Climate model to run

    model_version : str
        Version of the climate model to run

    probabilistic_file : str
        File containing the probabilistic configuration of the climate model

    num_cfgs : int
        Number of climate model configurations to run

    inputcheck : bool
        Check input before running the workflow?

    magicc_extra_config : str
        File containing additional MAGICC config (only required if running MAGICC)

    fair_extra_config : str
        File containing additional FaIR config (only required if running FaIR)

    historical_warming : float
        Historical warming estimate

    historical_warming_reference_period : str
        Reference period when calculating historical warming

    historical_warming_evaluation_period : str
        Period over which historical warming is evaluated

    test_run : bool
        Are we doing a test run (if yes, we don't check that historical
        warming from the climate models comes out consistently)?

    scenario_batch_size : int
        How many scenarios to run at once (smaller number means less memory
        is needed)?

    infilling_database : str
        Path to file to use for infilling

    save_raw_climate_output : bool
        Should raw climate output be saved (warning, requires lots of disk space
        and time)?

    postprocess : bool
        Should postprocessing steps be run?

    categorisation : bool
        Should categorisation be applied to scenarios?

    reporting_completeness_categorisation : bool
        Should emissions reporting completeness be added to output?

    harmonize : bool
        Should scenarios be harmonised?

    prefix : str
        String to use as a prefix for output variables

    harmonization_instance : ["ar6", "sr15"]
        Which configuration should be used for harmonisation?

    co2_and_non_co2_warming : bool
        Calculate CO2 and non-CO2 warming too (requires 3 times as many
        climate model runs, available for MAGICC only)

    gwp : bool
        Calculate GWP equivalents too
    """
    key_string = _get_key_string_and_log_outdir(input_emissions_file, outdir, LOGGER)

    check_hist_warming_period(historical_warming_reference_period)
    check_hist_warming_period(historical_warming_evaluation_period)
    input_df = _load_emissions_convert_to_basic(input_emissions_file, LOGGER)

    assessable = _harmonize_and_infill(
        input_df,
        inputcheck,
        key_string,
        outdir,
        infilling_database,
        harmonize,
        prefix,
        harmonization_instance,
    )

    if not assessable:
        LOGGER.warning("No assessable scenarios")
        return

    # read in infilled database
    infilled_emissions = os.path.join(outdir, f"{key_string}_harmonized_infilled.csv")
    LOGGER.info("Reading in infilled scenarios from: %s", infilled_emissions)
    df_infilled = pyam.IamDataFrame(infilled_emissions)

    LOGGER.info(df_infilled.timeseries())

    ####################
    # run climate models
    ####################
    df_climate = climate_assessment(
        df_infilled,
        key_string,
        outdir,
        magicc_extra_config=magicc_extra_config,
        fair_extra_config=fair_extra_config,
        model=model,
        model_version=model_version,
        probabilistic_file=probabilistic_file,
        num_cfgs=num_cfgs,
        historical_warming=historical_warming,
        historical_warming_reference_period=historical_warming_reference_period,
        historical_warming_evaluation_period=historical_warming_evaluation_period,
        test_run=test_run,
        scenario_batch_size=scenario_batch_size,
        save_raw_output=save_raw_climate_output,
        co2_and_non_co2_warming=co2_and_non_co2_warming,
        prefix=prefix,
    )
    LOGGER.info(df_climate.timeseries())

    LOGGER.info("Concatenating infilled df, climate df and input df")
    results = pyam.concat([df_infilled, df_climate])
    output = pyam.concat(
        [input_df.filter(variable=results.variable, keep=False), results]
    )

    LOGGER.info("write out raw output")
    output.to_excel(os.path.join(outdir, str(key_string + "_" + "rawoutput.xlsx")))

    if postprocess:
        output_postprocess = do_postprocess(
            output,
            outdir=outdir,
            key_string=key_string,
            categorisation=categorisation,
            reporting_completeness_categorisation=reporting_completeness_categorisation,
            prefix=prefix,
            gwp=gwp,
            model_version=model_version,
            model=model,
        )

        # Sanity checks
        sanity_check_bounds_kyoto_emissions(
            output_postprocess,
            out_kyoto_infilled=f"{prefix}|Infilled|Emissions|Kyoto Gases",
        )
        sanity_check_comparison_kyoto_gases(
            output_postprocess,
            out_kyoto_harmonized=f"{prefix}|Harmonized|Emissions|Kyoto Gases",
            out_kyoto_infilled=f"{prefix}|Infilled|Emissions|Kyoto Gases",
        )


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@input_emissions_file_arg
@outdir_arg
@input_check_option
@infilling_database_option
@prefix_option
@harmonization_instance_option
def harmonize_and_infill(
    input_emissions_file,
    outdir,
    inputcheck,
    infilling_database,
    prefix,
    # gwp,
    harmonization_instance,
):
    """
    Harmonise and infill data in ``input_emissions_file``, saving output in ``outdir``

    ``input_emissions_file`` should be a path to a file of emissions

    ``outdir`` should be a path a directory which already exists
    """
    LOGGER = logging.getLogger("harmonize_and_infill")
    _setup_logging(LOGGER)

    key_string = _get_key_string_and_log_outdir(input_emissions_file, outdir, LOGGER)

    input_df = _load_emissions_convert_to_basic(input_emissions_file, LOGGER)

    _harmonize_and_infill(
        input_df=input_df,
        inputcheck=inputcheck,
        key_string=key_string,
        outdir=outdir,
        infilling_database=infilling_database,
        prefix=prefix,
        # gwp=gwp,  # TODO: implement downstream
        harmonization_instance=harmonization_instance,
        harmonize=True,
    )


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@input_emissions_file_arg
@outdir_arg
@input_check_option
@prefix_option
@gwp_option
@harmonization_instance_option
def harmonize(
    input_emissions_file,
    outdir,
    inputcheck,
    prefix,
    gwp,
    harmonization_instance,
):
    """
    Harmonise data in ``input_emissions_file``, saving output in ``outdir``

    ``input_emissions_file`` should be a path to a file of emissions

    ``outdir`` should be a path a directory which already exists
    """
    LOGGER = logging.getLogger("harmonize")
    _setup_logging(LOGGER)

    key_string = _get_key_string_and_log_outdir(input_emissions_file, outdir, LOGGER)

    input_df = _load_emissions_convert_to_basic(input_emissions_file, LOGGER)

    df = _input_checks(input_df, inputcheck, key_string, outdir)

    df_harmonized = run_harmonization(
        df, instance=harmonization_instance, prefix=prefix
    )

    if gwp:
        df_harmonized = add_gwp100_kyoto_wrapper(
            df_harmonized,
            gwps=["AR5GWP100", "AR6GWP100"],
            prefixes=[f"{prefix}|Harmonized|"],
        )

    df_harmonized.to_csv(os.path.join(outdir, f"{key_string}_harmonized.csv"))


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@input_emissions_file_arg
@outdir_arg
@input_check_option
@prefix_option
@gwp_def_false_option
@harmonization_instance_option
def create_infiller_database(
    input_emissions_file,
    outdir,
    inputcheck,
    prefix,
    gwp,
    harmonization_instance,
):
    """
    Creates infiller database by harmonizing data in ``input_emissions_file``
    which is followed by some common-sense vetting and then saved in ``outdir``

    ``input_emissions_file`` should be a path to a file of emissions

    ``outdir`` should be a path a directory which already exists
    """
    LOGGER = logging.getLogger("create_infiller_database")
    _setup_logging(LOGGER)

    key_string = _get_key_string_and_log_outdir(input_emissions_file, outdir, LOGGER)

    input_df = _load_emissions_convert_to_basic(input_emissions_file, LOGGER)

    df = _input_checks(input_df, inputcheck, key_string, outdir)

    df_harmonized = run_harmonization(
        df, instance=harmonization_instance, prefix=prefix
    )

    df_infiller_database = infiller_vetting(df_harmonized)

    if gwp:
        df_infiller_database = add_gwp100_kyoto_wrapper(
            df_infiller_database,
            gwps=["AR5GWP100", "AR6GWP100"],
            prefixes=[f"{prefix}|Harmonized|"],
        )

    # Calculate total emissions consistent with afolu and energy for the
    # infilling database to avoid losing scenarios which have total, energy
    # and afolu reported and total dropped in the checks stage. We could also
    # do this at end of harmonization too, depending on whether we want
    # the infilling to preference using total CO2 or only fossil CO2
    LOGGER.info("Calculating CO2 totals where missing")
    _, no_co2_totals = split_df(
        df_infiller_database.filter(variable="*Harmonized*CO2*"),
        variable=f"{prefix}|Harmonized|Emissions|CO2",
    )
    co2_totals = _add_variables(
        no_co2_totals,
        f"{prefix}|Harmonized|Emissions|CO2|Energy and Industrial Processes",
        f"{prefix}|Harmonized|Emissions|CO2|AFOLU",
        f"{prefix}|Harmonized|Emissions|CO2",
        raise_if_mismatch=False,
    )
    df_infiller_database = df_infiller_database.append(co2_totals, inplace=False)

    LOGGER.info("Saving output")
    df_infiller_database.to_csv(
        os.path.join(outdir, f"{key_string}_infillerdatabase.csv")
    )


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@input_emissions_file_arg
@outdir_arg
@infilling_database_option
@prefix_option
@gwp_option
def infill(
    input_emissions_file,
    outdir,
    infilling_database,
    prefix,
    gwp,
):
    """
    Infill harmonized data in ``input_emissions_file``, saving output in ``outdir``

    ``input_emissions_file`` should be a path to a file of harmonized emissions

    ``outdir`` should be a path a directory which already exists
    """
    LOGGER = logging.getLogger("infill")
    _setup_logging(LOGGER)

    LOGGER.info("Loading harmonized emissions from %s", input_emissions_file)
    LOGGER.info("Output will be saved in %s", outdir)
    harmonized = pyam.IamDataFrame(input_emissions_file)
    harmonized_start_year = min(harmonized.year)

    LOGGER.info("Calling infilling")
    infilled, _, _ = run_infilling(
        harmonized,
        prefix=prefix,
        database_filepath=infilling_database,
        start_year=harmonized_start_year,
    )

    LOGGER.info("Post-processing for the climate model step")
    infilled = postprocess_infilled_for_climate(
        infilled, prefix=prefix, start_year=harmonized_start_year
    )

    if gwp:
        infilled = add_gwp100_kyoto_wrapper(
            infilled,
            gwps=["AR5GWP100", "AR6GWP100"],
            prefixes=[f"{prefix}|Infilled|"],
        )

    outfile = os.path.join(outdir, "infilled.csv")
    LOGGER.info("Saving output to %s", outfile)
    infilled.to_csv(outfile)


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@harmonizedinfilledemissions_arg
@outdir_arg
@num_cfgs_option
@hist_warming_option
@hist_warming_ref_period_option
@hist_warming_eval_period_option
@test_run_option
@model_option
@model_version_option
@magicc_extra_config_option
@fair_extra_config_option
@probabilistic_file_option
@scenario_batch_size_option
@prefix_option
@gwp_def_false_option
@nonco2_warming_option
@save_raw_climate_output_option
@save_csv_combined_output_option
def clim_cli(
    harmonizedinfilledemissions,
    outdir,
    num_cfgs,
    historical_warming,
    historical_warming_reference_period,
    historical_warming_evaluation_period,
    test_run,
    model,
    model_version,
    magicc_extra_config,
    fair_extra_config,
    probabilistic_file,
    scenario_batch_size,
    prefix,
    gwp,
    co2_and_non_co2_warming,
    save_raw_climate_output,
    save_csv_combined_output,
):
    """
    Run the climate emulator step of the IPCC AR6 climate asessment workflow.

    Example usage: ``python scripts/run_clim.py tests/test-data/workflow-fair/ex2_harmonized_infilled.csv output --model "fair" --model-version "1.6.2" --num-cfgs 2237 --probabilistic-file tests/test-data/fair-1.6.2-wg3-params-slim.json --fair-extra-config tests/test-data/fair-1.6.2-wg3-params-common.json --scenario-batch-size 4``

    For more information, see the code description under
    :func:`climate_assessment.climate.climate_assessment`.
    """
    LOGGER = logging.getLogger("clim_cli")
    _setup_logging(LOGGER)

    # silence pyam loggers
    logging.getLogger("pyam.core").setLevel(logging.CRITICAL)
    logging.getLogger("pyam.utils").setLevel(logging.CRITICAL)

    LOGGER.info("Outputs will be saved in: %s", outdir)

    key_string = os.path.splitext(os.path.basename(harmonizedinfilledemissions))[0]
    LOGGER.info("Outputs will be saved with the ID: %s", key_string)

    check_hist_warming_period(historical_warming_reference_period)
    check_hist_warming_period(historical_warming_evaluation_period)

    LOGGER.info(
        "Loading harmonized, infilled scenarios: %s", harmonizedinfilledemissions
    )
    df_infilled = pyam.IamDataFrame(harmonizedinfilledemissions)
    df_climate = climate_assessment(
        df_infilled,
        key_string,
        outdir,
        magicc_extra_config=magicc_extra_config,
        fair_extra_config=fair_extra_config,
        model=model,
        model_version=model_version,
        probabilistic_file=probabilistic_file,
        num_cfgs=num_cfgs,
        historical_warming=historical_warming,
        historical_warming_reference_period=historical_warming_reference_period,
        historical_warming_evaluation_period=historical_warming_evaluation_period,
        test_run=test_run,
        scenario_batch_size=scenario_batch_size,
        save_raw_output=save_raw_climate_output,
        co2_and_non_co2_warming=co2_and_non_co2_warming,
        prefix=prefix,
    )
    if df_climate is None:
        LOGGER.error("Climate assessment failed, exiting")

        return

    LOGGER.info("Concatenating infilled df and climate df")
    results = pyam.concat([df_infilled, df_climate])

    if gwp:
        LOGGER.info("Adding extra Kyoto Gases variables in GWP100 for each scenario")
        results = add_gwp100_kyoto_wrapper(
            results,
            gwps=["AR5GWP100", "AR6GWP100"],
            prefixes=[
                "",
                "AR6 climate diagnostics|Harmonized|",
                "AR6 climate diagnostics|Infilled|",
            ],
        )

    LOGGER.info("write out raw output")
    results.to_excel(os.path.join(outdir, str(key_string + "_" + "rawoutput.xlsx")))

    if save_csv_combined_output:
        LOGGER.info("write out raw output in csv")
        results.to_csv(os.path.join(outdir, str(key_string + "_" + "rawoutput.csv")))

    LOGGER.info("COMPLETE")


def _postprocess_worker(fname, outdir, **kwargs):
    """
    Helper function which takes a file that ends with "_rawoutput.xlsx" and the output
    location, and then calls the function `do_postprocess(output, outdir, key_string, prefix)`.
    """
    if not fname.endswith("_rawoutput.xlsx"):
        raise AssertionError(fname)

    output = pyam.IamDataFrame(fname)

    key_string = os.path.basename(fname).replace("_rawoutput.xlsx", "")

    return do_postprocess(output, outdir=outdir, key_string=key_string, **kwargs)


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@output_files_arg
@outdir_arg
@n_workers_option
@output_file_option
@prefix_all_out_variables_option
@kyoto_ghgs_option
@model_option
@model_version_option
@categorisation_option
@report_completeness_option
def postprocess(
    rawoutput_files,
    outdir,
    output_file,
    prefix,
    kyoto_ghgs,
    n_workers,
    model,
    model_version,
    categorisation,
    reporting_completeness_categorisation,
):
    """
    Merge and postprocess a collection of rawoutput into a single set of output files

    This script should be run after run_workflow.py if --no-postprocess was supplied. This
    is particularly useful for a clusted run where a run_workflow is run multiple times with
    batches of scenario data.

    Each file is processed individually, but the metadata from all the runs is merged into a single
    output file.
    """
    LOGGER = logging.getLogger("clim_cli")
    _setup_logging(LOGGER)

    LOGGER.info(f"Merging {len(rawoutput_files)} files: {rawoutput_files}")
    LOGGER.info(f"Saving output as {os.path.join(outdir, output_file)}")

    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        futures = [
            executor.submit(
                _postprocess_worker,
                fname,
                outdir,
                model=model,
                model_version=model_version,
                categorisation=categorisation,
                reporting_completeness_categorisation=reporting_completeness_categorisation,
                gwp=kyoto_ghgs,
                prefix=prefix,
            )
            for fname in rawoutput_files
        ]

    results = []
    for r in tqdm(as_completed(futures), total=len(futures)):
        if r is not None:
            results.append(r.result().meta)

    out_fname = os.path.join(outdir, output_file)
    LOGGER.info(f"Saving merged meta to {out_fname}")
    pd.concat(results).to_csv(out_fname)


batch_size_option = click.option(
    "--batch-size",
    help="Maximum number of scenarios per batch",
    required=True,
    default=20,
    type=int,
    show_default=True,
)


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@input_emissions_file_arg
@outdir_arg
@batch_size_option
def _split_scenarios_into_batches(input_emissions_file, outdir, batch_size):
    """
    Split scenario data into multiple batch files with at maximum the number of
    scenarios specified in batch_size per file.
    """
    split_scenarios_into_batches(
        iamc_file=input_emissions_file, outdir=outdir, batch_size=batch_size
    )


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@input_emissions_file_arg
@outdir_arg
def _extract_ips(input_emissions_file, outdir):
    """
    Extract IP scenarios from a scenario file.
    """
    extract_ips(ar6_file=input_emissions_file, outdir=outdir)
