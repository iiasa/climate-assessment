import contextlib
import logging
import os

import joblib
import numpy as np
import pandas as pd
import pyam
import scmdata
import tqdm.autonotebook as tqdman

LOGGER = logging.getLogger(__name__)


def init_logging(logger):
    # TODO: remove hard-coded level
    logger.setLevel(logging.INFO)

    # set root logger too
    logging.getLogger().setLevel(logging.INFO)
    logFormatter = logging.Formatter(
        "%(asctime)s %(name)s %(threadName)s - %(levelname)s:  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    stdoutHandler = logging.StreamHandler()
    stdoutHandler.setFormatter(logFormatter)

    logging.getLogger().addHandler(stdoutHandler)


# drop some columns that are not required
def columns_to_basic(df):
    """
    Takes a pyam.IamDataFrame and only keeps the basic columns ["model", "scenario", "region", "variable", "unit", "year", "value"],
    discarding potential other input columns (["exclude", "meta", "subannual", "version"]).

    Parameters
    ----------
    df : :class:`pyam.IamDataFrame`
        The input data to be formatted.

    Return
    ------
    :class:`pyam.IamDataFrame`
        The input data with only the remaining basic columns.
    """
    basic_cols = ["model", "scenario", "region", "variable", "unit", "year", "value"]
    cols = df.as_pandas().columns.to_list()

    col_list = [
        ["exclude"],
        ["meta"],
        ["subannual"],
        ["version"],
        ["subannual", "version"],
        ["meta", "version"],
        ["exclude", "version"],
        ["meta", "exclude"],
        ["meta", "subannual"],
        ["meta", "version"],
        ["meta", "subannual", "version"],
        ["meta", "exclude", "version"],
        ["exclude", "meta", "subannual", "version"],
    ]

    for extra_cols in col_list:
        if sorted(cols) == sorted(basic_cols + extra_cols):
            try:
                df = pyam.IamDataFrame(df.as_pandas().drop(extra_cols, axis=1))
            except KeyError:
                raise KeyError(
                    "There are columns in the data that are unaccounted for."
                )
        else:
            # print("did not find extra columns in a common setting")
            pass

    return df


def _remove_equiv_and_hyphens_from_unit(inscmrun):
    # equiv and hyphens in units don't place nice with pint
    out = inscmrun.copy()
    out["unit"] = out["unit"].str.replace("-", "").str.replace("equiv", "")

    return out


def _add_hyphen_to_hfc4310(inscmrun):
    out = inscmrun.copy()
    out["unit"] = out["unit"].str.replace("HFC4310", "HFC43-10")

    return out


def convert_units_to_co2_equiv(df, metric):
    """
    Converts the units of gases reported in kt into Mt CO2 equivalent per year

    Uses GWP100 values from either (by default) AR5 or AR4 IPCC reports.

    Parameters
    ----------
    df : :class:`pyam.IamDataFrame`
        The input dataframe whose units need to be converted.

    metric : str
        The name of the conversion metric to use. This will usually be AR<4/5/6>GWP100.

    Return
    ------
    :class:`pyam.IamDataFrame`
        The input data with units converted.
    """
    # probably possible to do this directly with pyam too somehow, but
    # here's the scmdata version
    scmrun = scmdata.ScmRun(df.timeseries())

    # strip hyphens and equiv from inputs
    scmrun = _remove_equiv_and_hyphens_from_unit(scmrun)

    res = scmrun.convert_unit("Mt CO2/yr", context=metric).drop_meta("unit_context")

    # put back the equiv (even though it breaks pint)
    res["unit"] = "Mt CO2-equiv/yr"
    res = pyam.IamDataFrame(res.timeseries(time_axis="year"))

    return res


def convert_co2_equiv_to_kt_gas(df, var_filter, metric="AR6GWP100"):
    """
    Convert units from CO2 equivalent to kt of gas.

    Parameters
    ----------
    df : :class:`pyam.IamDataFrame`
        The input data to be converted.

    var_filter : list[str], str
        Filter to use to pick the variables to convert

    metric : str
        The name of the conversion metric to use. This will usually be AR<4/5/6>GWP100.

    Return
    ------
    :class:`pyam.IamDataFrame`
        The input data with units converted.
    """
    keep = df.filter(variable=var_filter, keep=False)
    convert = scmdata.ScmRun(df.filter(variable=var_filter))

    # strip hyphens and equiv from inputs
    convert = _remove_equiv_and_hyphens_from_unit(convert)

    converted = []
    for vdf in convert.groupby("variable"):
        variable = vdf.get_unique_meta("variable", True)
        gas = variable.split("|")[-1].replace("-", "")
        converted.append(
            vdf.convert_unit(f"kt {gas}/yr", context=metric).drop_meta("unit_context")
        )

    out = keep.append(
        _add_hyphen_to_hfc4310(scmdata.run_append(converted)).timeseries(
            time_axis="year"
        )
    )

    return out


def add_gwp100_kyoto(
    df,
    kyoto_gases=(
        "Emissions|PFC|C2F6",
        "Emissions|PFC|C6F14",
        "Emissions|PFC|CF4",
        "Emissions|CO2",
        "Emissions|CH4",
        "Emissions|HFC|HFC125",
        "Emissions|HFC|HFC134a",
        "Emissions|HFC|HFC143a",
        "Emissions|HFC|HFC227ea",
        "Emissions|HFC|HFC23",
        "Emissions|HFC|HFC32",
        "Emissions|HFC|HFC43-10",
        "Emissions|N2O",
        "Emissions|SF6",
    ),
    gwp_instance="AR6GWP100",
    prefix="",
):
    total_co2_var = f"{prefix}Emissions|CO2"

    tmp = df.copy()
    tmp.require_data(variable=total_co2_var, exclude_on_fail=True)
    calc_df = tmp.filter(exclude=False)

    # aggregate CO2 before moving on
    tmp_no_total_co2 = tmp.filter(exclude=True)
    if not tmp_no_total_co2.empty:
        LOGGER.info("Aggregating total CO2 emissions")
        tmp_no_total_co2.aggregate(total_co2_var, append=True)
        calc_df = calc_df.append(tmp_no_total_co2)

    dfp = calc_df.filter(variable=[prefix + s for s in kyoto_gases])

    if dfp.empty:
        LOGGER.warning("No Kyoto gases found with prefix %s for %s", prefix, df)
        return df

    if len(set(dfp.data["variable"])) < len(kyoto_gases):
        LOGGER.info(
            f"The input doesn't have all the variables listed in Kyoto gases. "
            f"Only the variables "
            f"{', '.join(sorted([s for s in dfp.data['variable']]))} "
            f"are included in the calculation of the GWP100."
        )

    diff = list(set(df.data["variable"]) - set(dfp.data["variable"]))
    LOGGER.info(
        f"The variables {', '.join(sorted([s for s in diff]))} "
        f"are being ignored for the calculation of the GWP100."
    )

    kyoto = (
        convert_units_to_co2_equiv(
            dfp,
            gwp_instance,
        )
        .timeseries()
        .groupby(["model", "scenario", "region", "unit"])
        .sum(min_count=1)
    )

    if gwp_instance == "AR5GWP100":
        kyoto["variable"] = prefix + "Emissions|Kyoto Gases (AR5-GWP100)"
    elif gwp_instance == "AR6GWP100":
        kyoto["variable"] = prefix + "Emissions|Kyoto Gases (AR6-GWP100)"
    else:
        raise NotImplementedError(gwp_instance)

    return pyam.IamDataFrame(pyam.concat([df, kyoto]))


def add_gwp100_kyoto_wrapper(
    df,
    prefixes=[
        "",
        "AR6 climate diagnostics|Harmonized|",
        "AR6 climate diagnostics|Infilled|",
    ],
    gwps=["AR5GWP100", "AR6GWP100"],
):
    """
    Add Kyoto GWP100 emissions

    Parameters
    ----------
    df : :class:`pyam.IamDataFrame`
        :class:`pyam.IamDataFrame` containing emissions from which the GWP sum
        should be created

    prefixes : list[str]
        List of prefixes to use for the aggregation

    gwps : list[str]
        GWPs to use for aggregation

    Returns
    -------
    :class:`pyam.IamDataFrame`
        Input emissions plus the Kyoto GWP100 equivalents
    """
    for prefix in prefixes:
        for gwp in gwps:
            LOGGER.info("Calculating %s for prefix %s", gwp, prefix)
            df = add_gwp100_kyoto(df, gwp_instance=gwp, prefix=prefix)

    return df


@contextlib.contextmanager
def parallel_progress_bar(tqdm_bar):
    """
    Context manage to patch joblib so it shows a progress bar with tqdm

    Shoutout to https://stackoverflow.com/a/58936697 for the original
    implementation of this code
    """

    class TqdmBatchCompletionCallback(joblib.parallel.BatchCompletionCallBack):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

        def __call__(self, *args, **kwargs):
            tqdm_bar.update(n=self.batch_size)
            return super().__call__(*args, **kwargs)

    old_batch_callback = joblib.parallel.BatchCompletionCallBack
    joblib.parallel.BatchCompletionCallBack = TqdmBatchCompletionCallback
    try:
        yield tqdm_bar
    finally:
        joblib.parallel.BatchCompletionCallBack = old_batch_callback
        tqdm_bar.close()


def split_df(df, **filter_options):
    """
    This function splits the dataframe into model/scenario sets that fulfill
    the filter condition and those that don't.

    Parameters
    ----------
    df : :class:`pyam.IamDataFrame`
        Input scenario data

    Returns
    -------
    to_return_1 : :class:`pyam.IamDataFrame`
        Scenarios that fulfill the condition.

    to_return_2 : :class:`pyam.IamDataFrame`
        Scenarios that do not fulfill the condition.
    """
    df.set_meta("split_2", name="Split")
    mod_scens_have_lead = (
        df.filter(**filter_options)
        .data[["model", "scenario", "region"]]
        .drop_duplicates()
    )
    df.set_meta("split_1", name="Split", index=mod_scens_have_lead)
    to_return_1 = df.filter(Split="split_1")
    del to_return_1.meta["Split"]
    to_return_2 = df.filter(Split="split_1", keep=False)
    del to_return_2.meta["Split"]
    del df.meta["Split"]
    return (to_return_1, to_return_2)


def split_scenarios_into_batches(iamc_file, outdir, batch_size):
    """
    This function takes in a path to a IAMC formatted file `iamc_file` with
    scenario data, splits that into batches of size batch_size, and then saves
    those batches as CSV files in the folder `outdir`.

    Parameters
    ----------
    iamc_file : str
        Path to file that holds the scenario data that should be split.

    outdir : str
        Path to folder that will hold the produced batches.

    batch_size : int
        Up to how many scenarios should be in one batch?

    """
    init_logging(LOGGER)
    runs = pyam.IamDataFrame(iamc_file)

    model_scenario_combos = runs.meta.reset_index()[
        ["model", "scenario"]
    ].drop_duplicates()
    batches = np.array_split(
        model_scenario_combos, int(np.ceil(len(model_scenario_combos) / batch_size))
    )

    LOGGER.info(
        f"{len(model_scenario_combos)} model-scenario pairs split into {len(batches)} of size {batch_size}"
    )

    ts = runs.timeseries()

    for j, batch in tqdman.tqdm(
        enumerate(batches),
        desc="batch",
        total=len(batches),
    ):
        batch_df = pd.concat(
            [
                ts.xs(
                    (c.model, c.scenario), level=("model", "scenario"), drop_level=False
                )
                for _, c in batch.iterrows()
            ]
        )
        batch_df.to_csv(
            os.path.join(outdir, f"emissions_batch_{j + 1}.csv")
        )  # Note 1-based output files (easier for scripting)

    LOGGER.info(f"Created {len(batches)} batches")


def extract_ips(ar6_file, outdir):
    """
    This function takes an IAMC formatted file with AR6 data `iamc_file` and
    writes out only the Illustrative Pathways (IPs) in the folder `outdir`, as
    CSV.

    Parameters
    ----------
    ar6_file : str
        Path to file that holds the scenario data (e.g. full AR6 database).
        Can be either CSV or excel file.

    outdir : str
        Path to folder that will hold the output CSV file with the IPs.

    """
    IPS = (
        ("AIM/CGE 2.2", "EN_NPi2020_900f"),
        ("COFFEE 1.1", "EN_NPi2020_400f"),
        ("GCAM 5.3", "NGFS2_Current Policies"),
        ("IMAGE 3.0", "EN_INDCi2030_3000f"),
        ("MESSAGEix-GLOBIOM 1.0", "LowEnergyDemand_1.3_IPCC "),
        ("MESSAGEix-GLOBIOM_GEI 1.0", "SSP2_openres_lc_50"),
        ("REMIND-MAgPIE 2.1-4.3", "DeepElec_SSP2_ HighRE_Budg900"),
        ("REMIND-MAgPIE 2.1-4.2", "SusDev_SDP-PkBudg1000"),
        ("WITCH 5.0", "CO_Bridge"),
    )
    raw = scmdata.ScmRun(ar6_file, lowercase_cols=True)

    out = []
    for model, scenario in IPS:
        out.append(raw.filter(model=model, scenario=scenario))

    out = scmdata.run_append(out)

    out = pyam.IamDataFrame(out.timeseries(time_axis="year"))
    out.to_csv(os.path.join(outdir, "ar6_ip_data.csv"))


def _perform_operation(df, var_1, var_2, out_variable, op, raise_if_mismatch=True):
    """
    Helper function that is called in ``_diff_variables()`` and ``_add_variables()``,
    instead of silicone.multiple_infillers.infill_composite_values, because
    silicone.multiple_infillers.infill_composite_values does not check whether
    all components are included.
    """

    def _get_ts(v):
        out = df.filter(variable=v)
        if out.empty:
            return None

        return out.timeseries().reset_index("variable", drop=True)

    base = _get_ts(var_1)
    other = _get_ts(var_2)
    if base is None or other is None:
        empty = df.filter(variable="*", keep=False)
        return empty

    base, other = base.align(other)

    if op == "subtract":
        res = base - other
    elif op == "add":
        res = base + other
    else:
        raise NotImplementedError(op)

    all_nan_rows = res.isnull().all(axis=1)
    if all_nan_rows.any():
        if raise_if_mismatch:
            raise ValueError(f"Mismatched inputs: {res[all_nan_rows]}")

        res = res.loc[~all_nan_rows, :].copy()

    res["variable"] = out_variable

    return pyam.IamDataFrame(res)


def _diff_variables(df, var_1, var_2, out_variable, raise_if_mismatch=True):
    """
    Calculates the difference between two variables, and adds this new variable
    to the dataframe.

    Parameters
    ----------
    df : :class:`pyam.IamDataFrame`
        Input scenario data

    var_1 : str
        First variable in operation

    var_2 : str
        Second variable in operation

    out_variable : str
        What to call the new variable

    Returns
    -------
    :class:`pyam.IamDataFrame`
        Dataframe with added difference variable
    """
    return _perform_operation(
        df,
        var_1,
        var_2,
        out_variable,
        op="subtract",
        raise_if_mismatch=raise_if_mismatch,
    )


def _add_variables(df, var_1, var_2, out_variable, raise_if_mismatch=True):
    """
    Calculates the sum of two variables, and adds this as a new variable to the
    dataframe.

    Parameters
    ----------
    df : :class:`pyam.IamDataFrame`
        Input scenario data

    var_1 : str
        First variable in operation

    var_2 : str
        Second variable in operation

    out_variable : str
        What to call the new variable

    Returns
    -------
    :class:`pyam.IamDataFrame`
        Dataframe with added sum variable
    """
    return _perform_operation(
        df, var_1, var_2, out_variable, op="add", raise_if_mismatch=raise_if_mismatch
    )
