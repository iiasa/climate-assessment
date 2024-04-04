import logging
import os

import aneris.convenience
import pandas as pd
import pyam
import scmdata
import tqdm
from joblib import Parallel, delayed

from climate_assessment.checks import remove_rows_with_zero_in_harmonization_year

from ..utils import parallel_progress_bar

LOGGER = logging.getLogger(__name__)


here = os.path.dirname(os.path.realpath(__file__))


HARMONIZATION_VARIABLES = [
    "Emissions|BC",
    "Emissions|PFC|C2F6",
    "Emissions|PFC|C6F14",
    "Emissions|PFC|CF4",
    "Emissions|CO",
    "Emissions|CO2",
    "Emissions|CO2|AFOLU",
    "Emissions|CO2|Energy and Industrial Processes",
    "Emissions|CH4",
    "Emissions|F-Gases",
    "Emissions|HFC",
    "Emissions|HFC|HFC125",
    "Emissions|HFC|HFC134a",
    "Emissions|HFC|HFC143a",
    "Emissions|HFC|HFC227ea",
    "Emissions|HFC|HFC23",
    # 'Emissions|HFC|HFC245ca',  # all nan in historical dataset (RCMIP)
    # "Emissions|HFC|HFC245fa",  # not in historical dataset (RCMIP)
    "Emissions|HFC|HFC32",
    "Emissions|HFC|HFC43-10",
    "Emissions|N2O",
    "Emissions|NH3",
    "Emissions|NOx",
    "Emissions|OC",
    "Emissions|PFC",
    "Emissions|SF6",
    "Emissions|Sulfur",
    "Emissions|VOC",
]


# get path for data input folder
def getpath(f, data_folder=here):
    return os.path.join(here, f)


def postprocessing(harmonized_results, prefix):
    """
    Helper function that makes sure that the harmonization prefix is added.
    """
    # hotfix prefix|suffix for harmonized emissions output
    # strip suffix
    harmonized_results = harmonized_results.data
    harmonized_results["variable"] = harmonized_results["variable"].map(
        lambda x: x.replace("|Harmonized", "")
    )
    #    replace prefix
    harmonized_results["variable"] = (
        harmonized_results["variable"]
        .map(lambda x: x.replace(prefix, f"{prefix}|Harmonized"))
        .astype(str)
    )
    harmonized_results = pyam.IamDataFrame(harmonized_results)

    return harmonized_results


def add_year_historical_percentage_offset(df, dfhist, yr=2015, low_yr=2010):
    """
    In the case that the chosen harmonization year (yr, default=2015) is not reported,
    this function uses an earlier year (low_yr, default=2010) to derive the
    historical offset for harmonization.
    It takes the relative difference in `low_yr`, and assumes that this relative
    difference stays the same until `yr`.
    """
    if yr not in df.columns:
        df[yr] = None
        df[yr] = pd.to_numeric(df[yr])

    df2015 = df[~df[yr].isnull()]
    dfno2015 = df[df[yr].isnull()].copy()

    if low_yr in dfno2015.columns:
        dfhist_low = dfhist[low_yr].reset_index(["model", "scenario"], drop=True)
        dfhist_yr = dfhist[yr].reset_index(["model", "scenario"], drop=True)

        dfno2015_low = dfno2015[[low_yr]]

        relative_diff = (
            dfno2015_low.subtract(dfhist_low, axis=0)
            .divide(dfhist_low, axis=0)
            .dropna()
        )
        if relative_diff.shape[0] != dfno2015.shape[0]:
            raise AssertionError("Some data will not get adjusted properly")

        fill_values = (
            relative_diff.multiply(dfhist_yr, axis=0)
            .add(dfhist_yr, axis=0)
            .dropna()
            .rename({low_yr: yr}, axis="columns")
        )
        if fill_values.shape[0] != dfno2015.shape[0]:
            raise AssertionError("Some data will not get adjusted properly")

        dfno2015[yr] = fill_values[yr].reorder_levels(dfno2015.index.names)
        df = pd.concat([df2015, dfno2015])
    else:
        if not dfno2015.empty:
            raise KeyError(f"{low_yr} not in `dfno2015`")

    return df


def run_harmonization(df, instance, prefix):
    """
    Run harmonization.
    Hamronization method overrides by specific species are set within this function too.

    Parameters
    ----------
    df : :class:`pyam.IamDataFrame`
        Input native emisisons in IAMC format.
    instance : str
        String used to choose what historical data to use.
    prefix : str
        Prefix used for the variable names

    Returns
    -------
    :class:`pyam.IamDataFrame`
        Harmonized scenarios.
    """
    LOGGER.info(f"Using {instance} instance for harmonization")

    df_hist = scmdata.ScmRun(
        getpath("history_" + instance + ".csv"), lowercase_cols=True
    )

    LOGGER.debug("Emissions to harmonize %s", HARMONIZATION_VARIABLES)

    not_harmonize = set(df.variable) - set(HARMONIZATION_VARIABLES)
    LOGGER.info("Not harmonizing %s", not_harmonize)

    df = df.filter(variable=HARMONIZATION_VARIABLES)
    if df.empty:
        return df

    # TODO: remove this hard-coding
    if instance.startswith("sr15"):
        harmonization_year = 2010
    else:
        harmonization_year = 2015

    LOGGER.info("harmonization_year %s", harmonization_year)

    scmrun = scmdata.ScmRun(df)
    LOGGER.info("Stripping equivalent units for processing")
    scmrun["unit"] = scmrun["unit"].str.replace("-equiv", "").str.replace("-", "")

    scenarios = scmrun.copy()

    LOGGER.info("Creating pd.DataFrame's for aneris")
    scenarios = scenarios.timeseries(time_axis="year")

    df_hist["variable"] = df_hist["variable"].apply(
        lambda x: x.replace(f"{prefix}|", "").replace("|Unharmonized", "")
    )
    df_hist["unit"] = df_hist["unit"].str.replace("-equiv", "").str.replace("-", "")
    history = df_hist.filter(year=range(1990, 2020)).timeseries(time_axis="year")

    # TODO: remove hard-coding
    historical_offset_add_year = 2015
    historical_offset_base_year = 2010
    if harmonization_year == historical_offset_add_year:
        LOGGER.info(
            "Adding %s values based on historical percentage offset from %s",
            historical_offset_add_year,
            historical_offset_base_year,
        )
        scenarios = add_year_historical_percentage_offset(
            scenarios,
            history,
            yr=historical_offset_add_year,
            low_yr=historical_offset_base_year,
        )

    LOGGER.info("Interpolating onto output timesteps")
    # TODO: remove hard-coded end year
    output_timesteps = range(harmonization_year, 2100 + 1)
    LOGGER.debug("output_timesteps %s", output_timesteps)
    scenarios = pyam.IamDataFrame(scenarios).interpolate(output_timesteps)
    scenarios = remove_rows_with_zero_in_harmonization_year(
        scenarios,
        filename="dropped_rows",
        harmonization_year=harmonization_year,
    )  # note: this process is repeated after harmonization. Before is slightly nicer, but not enough.

    # TODO: remove hard-coding
    overrides = pd.DataFrame(
        [
            #     {'method': 'default_aneris_tree', 'variable': 'Emissions|BC'}, # depending on the decision tree in aneris/method.py
            {
                "method": "reduce_ratio_2150_cov",
                "variable": "Emissions|PFC",
            },  # high historical variance (cov=16.2)
            {
                "method": "reduce_ratio_2150_cov",
                "variable": "Emissions|PFC|C2F6",
            },  # high historical variance (cov=16.2)
            {
                "method": "reduce_ratio_2150_cov",
                "variable": "Emissions|PFC|C6F14",
            },  # high historical variance (cov=15.4)
            {
                "method": "reduce_ratio_2150_cov",
                "variable": "Emissions|PFC|CF4",
            },  # high historical variance (cov=11.2)
            {
                "method": "reduce_ratio_2150_cov",
                "variable": "Emissions|CO",
            },  # high historical variance (cov=15.4)
            {
                "method": "reduce_ratio_2080",
                "variable": "Emissions|CO2",
            },  # always ratio method by choice
            {
                "method": "reduce_offset_2150_cov",
                "variable": "Emissions|CO2|AFOLU",
            },  # high historical variance, but using offset method to prevent diff from increasing when going negative rapidly (cov=23.2)
            {
                "method": "reduce_ratio_2080",  # always ratio method by choice
                "variable": "Emissions|CO2|Energy and Industrial Processes",
            },
            #     {'method': 'default_aneris_tree', 'variable': 'Emissions|CH4'}, # depending on the decision tree in aneris/method.py
            {
                "method": "constant_ratio",
                "variable": "Emissions|F-Gases",
            },  # basket not used in infilling (sum of f-gases with low model reporting confidence)
            {
                "method": "constant_ratio",
                "variable": "Emissions|HFC",
            },  # basket not used in infilling (sum of subset of f-gases with low model reporting confidence)
            {
                "method": "constant_ratio",
                "variable": "Emissions|HFC|HFC125",
            },  # minor f-gas with low model reporting confidence
            {
                "method": "constant_ratio",
                "variable": "Emissions|HFC|HFC134a",
            },  # minor f-gas with low model reporting confidence
            {
                "method": "constant_ratio",
                "variable": "Emissions|HFC|HFC143a",
            },  # minor f-gas with low model reporting confidence
            {
                "method": "constant_ratio",
                "variable": "Emissions|HFC|HFC227ea",
            },  # minor f-gas with low model reporting confidence
            {
                "method": "constant_ratio",
                "variable": "Emissions|HFC|HFC23",
            },  # minor f-gas with low model reporting confidence
            {
                "method": "constant_ratio",
                "variable": "Emissions|HFC|HFC32",
            },  # minor f-gas with low model reporting confidence
            {
                "method": "constant_ratio",
                "variable": "Emissions|HFC|HFC43-10",
            },  # minor f-gas with low model reporting confidence
            #     {'method': 'default_aneris_tree', 'variable': 'Emissions|N2O'}, # depending on the decision tree in aneris/method.py
            #     {'method': 'default_aneris_tree', 'variable': 'Emissions|NH3'}, # depending on the decision tree in aneris/method.py
            #     {'method': 'default_aneris_tree', 'variable': 'Emissions|NOx'}, # depending on the decision tree in aneris/method.py
            {
                "method": "reduce_ratio_2150_cov",
                "variable": "Emissions|OC",
            },  # high historical variance (cov=18.5)
            {
                "method": "constant_ratio",
                "variable": "Emissions|SF6",
            },  # minor f-gas with low model reporting confidence
            #     {'method': 'default_aneris_tree', 'variable': 'Emissions|Sulfur'}, # depending on the decision tree in aneris/method.py
            {
                "method": "reduce_ratio_2150_cov",
                "variable": "Emissions|VOC",
            },  # high historical variance (cov=12.0)
        ]
    )
    LOGGER.info("Harmonisation overrides:\n%s", overrides)

    scenarios = scenarios.filter(year=output_timesteps).timeseries()
    with parallel_progress_bar(tqdm.tqdm(desc="Harmonisation")):
        LOGGER.info("Harmonising in parallel")
        # TODO: remove hard-coding of n_jobs
        scenarios_harmonized = Parallel(n_jobs=-1)(
            delayed(aneris.convenience.harmonise_all)(
                msdf,
                history=history,
                harmonisation_year=harmonization_year,
                overrides=overrides,
            )
            for _, msdf in scenarios.groupby(["model", "scenario"])
        )

    LOGGER.info("Hacking around some regression in aneris - pyam stack")

    def drop_broken_stuff(indf):
        out = indf.copy()
        idx_length = len(out.index.names)
        drop_levels = list(range(idx_length // 2, idx_length))
        out.index = out.index.droplevel(drop_levels)

        return out

    scenarios_harmonized = [drop_broken_stuff(s) for s in scenarios_harmonized]

    LOGGER.info("Combining results")
    scenarios_harmonized = pd.concat(scenarios_harmonized).reset_index()

    LOGGER.info("Putting equiv back in units")
    equiv_rows = scenarios_harmonized["variable"].isin(["Emissions|HFC"])
    scenarios_harmonized.loc[equiv_rows, "unit"] = scenarios_harmonized.loc[
        equiv_rows, "unit"
    ].str.replace("/yr", "-equiv/yr")

    scenarios_harmonized["variable"] = (
        f"{prefix}|Harmonized|" + scenarios_harmonized["variable"]
    )

    LOGGER.info("Converting to IamDataFrame")
    scenarios_harmonized = pyam.IamDataFrame(scenarios_harmonized)

    # TODO: perhaps move to checks, if this is possible before doing historical offset and then interpolation
    # NB: doing this here in the workflow will fail if there are scenarios being harmonized to historical zero emissions!
    LOGGER.info("CHECK: if some emissions are zero in the harmonization year.")
    scenarios_harmonized = remove_rows_with_zero_in_harmonization_year(
        scenarios_harmonized,
        filename="dropped_rows",
        harmonization_year=harmonization_year,
    )
    if ((scenarios_harmonized.filter(year=2015).as_pandas())["value"] == 0).any():
        raise AssertionError("Some scenarios have zero in the harmonization year!")

    # TODO: some logic to check that CO2 total was handled properly?

    return scenarios_harmonized
