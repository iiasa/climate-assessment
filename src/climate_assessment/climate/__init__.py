import logging
import os.path

import numpy as np
import openscm_runner.run
import pandas as pd
import pyam
import tqdm.autonotebook as tqdman

from .ciceroscm import DEFAULT_CICEROSCM_VERSION, get_ciceroscm_configurations
from .fair import DEFAULT_FAIR_VERSION, get_fair_configurations
from .magicc7 import (
    DEFAULT_MAGICC_DRAWNSET,
    DEFAULT_MAGICC_VERSION,
    get_magicc7_configurations,
)
from .post_process import post_process
from .wg3 import clean_wg3_scenarios

LOGGER = logging.getLogger(__name__)


class MissingVariableFilter(logging.Filter):
    def filter(self, record):
        return "not available from" not in record.getMessage()


def climate_assessment(
    df,
    key_string,
    outdir,
    model="magicc",
    model_version=None,
    num_cfgs=600,
    historical_warming=0.85,
    historical_warming_reference_period="1850-1900",
    historical_warming_evaluation_period="1995-2014",
    test_run=False,
    scenario_batch_size=20,
    save_raw_output=False,
    probabilistic_file=DEFAULT_MAGICC_DRAWNSET,
    magicc_extra_config=None,
    fair_extra_config=None,
    co2_and_non_co2_warming=False,
    prefix="AR6 climate diagnostics",
):
    """
    Run the climate assessment

    Parameters
    ----------
    df : :class:`pyam.IamDataFrame`
        :class:`pyam.IamDataFrame` with data to assess

    key_string : str
        String to use to identify output files and find input files

    outdir : str
        Directory in which to save the output

    model : str
        Reduced-complexity climate model to run assessment with

    model_version : str, None
        Version of the climate model. If None, use default

    num_cfgs : int
        Number of model configs to run. Multiply this number by the number of
        scenarios to get total runs. The full drawnset is 600 so if you're
        just testing it's probably worth using a smaller number unless you
        want to wait for 58 000 runs (of course by using a smaller subset the
        temperature numbers won't make sense but if all you're checking is
        that things run you also don't really care).

    historical_warming : float
        Historical warming to match the climate model output to

    historical_warming_reference_period : str
        Reference period to use for the historical warming (e.g. "1850-1900")

    historical_warming_evaluation_period : str
        Evaluation period to use for the historical warming (e.g. "1995-2014")

    test_run : bool
        Is this a test run? If it is, we won't raise an error if the historical
        temperatures don't match the assessment perfectly.

    scenario_batch_size : int
        How many scenarios do you want to run at once? This should be adjusted
        to balance the amount of RAM and number of cores available on your
        system. The limit depends mostly on the RAM available.

    save_raw_output : bool
        Should we also save the raw climate output (i.e. every ensemble member) to disk?

    probabilistic_file : str
        Path to file containing parameters to run climate model with (will be passed to
         `openscm-runner`). Currently, only json files are supported.

    co2_and_non_co2_warming : bool
        Include assessment of CO2 and non-CO2 warming (requires 3x as many runs)?

    prefix : str
        Prefix for all variable names

    Returns
    -------
    :class:`pyam.IamDataFrame`
        :class:`pyam.IamDataFrame` containing climate assessment
    """
    ## Setup bits and pieces
    datafile_output_name = f"{key_string}_IAMC_climateassessment.csv"
    datafile_output_meta_name = (
        f"{key_string}_exceedance_probabilities.csv".replace(" ", "")
        .replace("/", "-")
        .replace("%", "pc")
    )
    data_file_output = os.path.join(outdir, datafile_output_name)
    data_file_output_meta = os.path.join(outdir, datafile_output_meta_name)

    clean_scenarios = clean_wg3_scenarios(df)
    if clean_scenarios is None:
        return None

    climate_model_cfgs, climate_models_out_config = _get_model_configs_and_out_configs(
        model=model,
        model_version=model_version,
        probabilistic_file=probabilistic_file,
        magicc_extra_config=magicc_extra_config,
        fair_extra_config=fair_extra_config,
        num_cfgs=num_cfgs,
        co2_and_non_co2_warming=co2_and_non_co2_warming,
    )

    # define auxiliary functions to circumvent the big memory requirements
    #   for storing in pyam long format
    def add_batch_id_to_outpath(ipath):
        _, ext = os.path.splitext(ipath)

        return ipath.replace(ext, f"{batch_no:04d}{ext}")

    def save_pyam_style_csv(outpath, scmdf, meta=False):
        """
        Save pyam style without converting to long data first
        """
        df = scmdf.timeseries()
        if set(df.index.names) != set(pyam.IAMC_IDX):
            raise AssertionError(
                f"Only meta cols should be `{pyam.IAMC_IDX}` in order to keep everyone sane"
            )

        # convert columns to years
        df.columns = df.columns.map(lambda x: x.year)
        if df.columns.duplicated().any():
            raise AssertionError(
                "Somehow you've got more than one output for a single year..."
            )

        df = df.reset_index()

        df = df.rename(columns={c: str(c).title() for c in df.columns})
        df.to_csv(outpath, index=False)

    def save_pyam_style_meta_table(outpath, meta_table):
        """
        Save meta table without going through a :obj:`pyam.IamDataFrame`
        """
        # excel writing for meta can be used here instead if you want...
        meta_table.to_csv(outpath)

    # run script climate model in batches
    batch_no = 0
    batch_dfs = []
    total_mod_scens = clean_scenarios[["model", "scenario"]].drop_duplicates().shape[0]

    LOGGER.info(f"\n\n\nTotal mod_scens: {total_mod_scens}\n\n\n")

    for j, (_, model_scenario_df) in tqdman.tqdm(
        enumerate(clean_scenarios.groupby(["model", "scenario"])),
        desc=f"{total_mod_scens} model-scenario pairs (running in batches of {scenario_batch_size})",
        total=total_mod_scens,
    ):
        batch_dfs.append(model_scenario_df)
        if np.equal((j + 1) % scenario_batch_size, 0) or np.equal(
            (j + 1), total_mod_scens
        ):
            scenarios_to_run = pyam.IamDataFrame(pd.concat(batch_dfs))

            ##################################
            # run climate models
            ##################################
            _, res_percentiles, meta_table = run_and_post_process(
                scenarios_to_run,
                climate_model_cfgs,
                climate_models_out_config,
                historical_warming=historical_warming,
                historical_warming_reference_period=historical_warming_reference_period,
                historical_warming_evaluation_period=historical_warming_evaluation_period,
                save_raw_output=save_raw_output,
                outdir=outdir,
                test_run=test_run,
                co2_and_non_co2_warming=co2_and_non_co2_warming,
            )

            LOGGER.info(
                f"\n\n Batch run finished - now saving batch number {batch_no}."
                + "\n\n"
            )
            save_pyam_style_csv(
                add_batch_id_to_outpath(data_file_output),
                res_percentiles,
            )
            save_pyam_style_meta_table(
                add_batch_id_to_outpath(data_file_output_meta),
                meta_table,
            )

            #  batch count
            batch_dfs = []
            batch_no += 1

    LOGGER.info("All batches have been run. Let us combine them.")

    ## Join everything back together
    full_output = []
    meta = []

    for i in tqdman.tqdm(range(batch_no), desc="Reading batches"):
        # combine the IAMC dataframe
        _, ext = os.path.splitext(data_file_output)
        batch_df_string = data_file_output.replace(ext, f"{i:04d}{ext}")
        full_output.append(pd.read_csv(batch_df_string))

        # combine the meta file with exceedance probabilities
        _, ext = os.path.splitext(data_file_output_meta)
        batch_df_meta_string = data_file_output_meta.replace(ext, f"{i:04d}{ext}")
        meta.append(pd.read_csv(batch_df_meta_string))

    LOGGER.info("Joining meta using pandas")
    meta = pd.concat(meta, ignore_index=True)

    LOGGER.info("Writing meta to excel")
    meta["exclude"] = ""
    meta.to_excel(
        os.path.join(
            outdir,
            f"{key_string}_full_exceedance_probabilities.xlsx",
        )
    )

    LOGGER.info("Joining batches using pyam (slow as requires converting to long data)")
    full_output = pyam.IamDataFrame(pd.concat(full_output)).data
    # add prefix
    full_output["variable"] = prefix + "|" + full_output["variable"].astype(str)
    full_output = pyam.IamDataFrame(full_output)

    # include relevant meta in output
    meta_mod_scen = meta.set_index(["model", "scenario"])
    for c in meta_mod_scen:
        if c == "exclude":
            continue

        full_output.set_meta(meta_mod_scen[c])

    LOGGER.info("Writing output to excel")
    full_output.to_excel(
        os.path.join(outdir, f"{key_string}_IAMC_climateassessment.xlsx")
    )

    return full_output


def run_and_post_process(
    scenarios,
    climate_models_cfgs,
    climate_models_out_config,
    historical_warming,
    historical_warming_reference_period,
    historical_warming_evaluation_period,
    outdir,
    test_run,
    save_raw_output,
    co2_and_non_co2_warming,
):
    """
    Run the climate models probabilistically

    Uses ``openscm-runner`` to parallise the model runs. The results are then
    post processed to calculate exceedence probabilities

    Parameters
    ----------
    scenarios: [:obj:`scmdata.ScmRun`, :class:`pyam.IamDataFrame`]
        Emissions  for the scenarios of interest

    climate_models_cfgs : dict
        Configuration as expected by openscm-runner

    climate_models_out_config : dict
        Climate models output config as expected by OpenSCM-Runner

    historical_warming : float
        Historical warming to match the climate model output to

    historical_warming_reference_period : str
        Reference period to use for the historical warming (e.g. "1850-1900")

    historical_warming_evaluation_period : str
        Evaluation period to use for the historical warming (e.g. "1995-2014")

    outdir: str
        Output directory for the raw output

    test_run: bool
        If true, check model output

    save_raw_output: bool
        If True, save all the raw climate model output for later analysis.

    co2_and_non_co2_warming : bool
        Include assessment of CO2 and non-CO2 warming?

    Returns
    -------

    """
    output_variables = (
        # GSAT
        "Surface Air Temperature Change",
        # GMST
        "Surface Air Ocean Blended Temperature Change",
        # ERFs
        "Effective Radiative Forcing",
        "Effective Radiative Forcing|Anthropogenic",
        "Effective Radiative Forcing|Aerosols",
        "Effective Radiative Forcing|Aerosols|Direct Effect",
        "Effective Radiative Forcing|Aerosols|Direct Effect|BC",
        "Effective Radiative Forcing|Aerosols|Direct Effect|OC",
        "Effective Radiative Forcing|Aerosols|Direct Effect|SOx",
        "Effective Radiative Forcing|Aerosols|Indirect Effect",
        "Effective Radiative Forcing|Greenhouse Gases",
        "Effective Radiative Forcing|CO2",
        "Effective Radiative Forcing|CH4",
        "Effective Radiative Forcing|N2O",
        "Effective Radiative Forcing|F-Gases",
        "Effective Radiative Forcing|Montreal Protocol Halogen Gases",
        "Effective Radiative Forcing|CFC11",
        "Effective Radiative Forcing|CFC12",
        "Effective Radiative Forcing|HCFC22",
        "Effective Radiative Forcing|Ozone",
        "Effective Radiative Forcing|HFC125",
        "Effective Radiative Forcing|HFC134a",
        "Effective Radiative Forcing|HFC143a",
        "Effective Radiative Forcing|HFC227ea",
        "Effective Radiative Forcing|HFC23",
        "Effective Radiative Forcing|HFC245fa",
        "Effective Radiative Forcing|HFC32",
        "Effective Radiative Forcing|HFC4310mee",
        "Effective Radiative Forcing|CF4",
        "Effective Radiative Forcing|C6F14",
        "Effective Radiative Forcing|C2F6",
        "Effective Radiative Forcing|SF6",
        # Heat uptake
        "Heat Uptake",
        # "Heat Uptake|Ocean",
        # Atmospheric concentrations
        "Atmospheric Concentrations|CO2",
        "Atmospheric Concentrations|CH4",
        "Atmospheric Concentrations|N2O",
        # carbon cycle
        "Net Atmosphere to Land Flux|CO2",
        "Net Atmosphere to Ocean Flux|CO2",
        # permafrost
        "Net Land to Atmosphere Flux|CO2|Earth System Feedbacks|Permafrost",
        "Net Land to Atmosphere Flux|CH4|Earth System Feedbacks|Permafrost",
    )
    LOGGER.info("`output_variables`: %s", output_variables)

    LOGGER.debug("Adding custom filter to FaIR run logger")
    # Filter out missing variable warnings from FaIR logger,
    # hard-coded for now, maybe turned back on another day
    fair_run_logger = logging.getLogger(
        "openscm_runner.adapters.fair_adapter._run_fair"
    )
    fair_run_logger.addFilter(MissingVariableFilter(name="MissingVariableFilter"))

    res = openscm_runner.run(
        climate_models_cfgs=climate_models_cfgs,
        out_config=climate_models_out_config,
        scenarios=scenarios,
        output_variables=output_variables,
    )

    LOGGER.debug("Removing custom filters from run loggers")
    mvf = [
        i
        for i, v in enumerate(fair_run_logger.filters)
        if v.name == "MissingVariableFilter"
    ][0]
    fair_run_logger.filters.pop(mvf)

    LOGGER.info("Finished running climate models")
    return post_process(
        res,
        outdir,
        test_run=test_run,
        save_raw_output=save_raw_output,
        co2_and_non_co2_warming=co2_and_non_co2_warming,
        historical_warming=historical_warming,
        historical_warming_reference_period=historical_warming_reference_period,
        historical_warming_evaluation_period=historical_warming_evaluation_period,
    )


def _get_model_configs_and_out_configs(
    model,
    model_version,
    probabilistic_file,
    magicc_extra_config,
    fair_extra_config,
    num_cfgs,
    co2_and_non_co2_warming,
):
    # in #67, refactor so this can handle multiple models at once
    climate_model_cfgs = {}
    if model.lower() == "magicc":
        if model_version is None:
            model_version = DEFAULT_MAGICC_VERSION
        magicc7_cfgs, magicc7_out_config = get_magicc7_configurations(
            magicc_version=model_version,
            magicc_probabilistic_file=probabilistic_file,
            magicc_extra_config=magicc_extra_config,
            num_cfgs=num_cfgs,
            co2_and_non_co2_warming=co2_and_non_co2_warming,
        )
        climate_model_cfgs["MAGICC7"] = magicc7_cfgs
        climate_models_out_config = {"MAGICC7": magicc7_out_config}
        LOGGER.info(f"Running MAGICC7 {len(magicc7_cfgs)} configs")

    elif model.lower() == "fair":
        if model_version is None:
            model_version = DEFAULT_FAIR_VERSION
        fair_cfgs = get_fair_configurations(
            fair_version=model_version,
            fair_probabilistic_file=probabilistic_file,
            fair_extra_config=fair_extra_config,
            num_cfgs=num_cfgs,
        )
        climate_model_cfgs["FAIR"] = fair_cfgs
        climate_models_out_config = None
        LOGGER.info(f"Running FAIR {len(fair_cfgs)} configs")

    elif model.lower() == "ciceroscm":
        if model_version is None:
            model_version = DEFAULT_CICEROSCM_VERSION
        ciceroscm_cfgs = get_ciceroscm_configurations(
            ciceroscm_version=model_version,
            ciceroscm_probabilistic_file=probabilistic_file,
            num_cfgs=num_cfgs,
        )
        climate_model_cfgs["CICEROSCM"] = ciceroscm_cfgs
        climate_models_out_config = None
        LOGGER.info(f"Running CICEROSCM {len(ciceroscm_cfgs)} configs")

    return climate_model_cfgs, climate_models_out_config
