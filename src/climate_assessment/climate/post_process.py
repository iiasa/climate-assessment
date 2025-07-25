import json
import logging
import os.path
from functools import lru_cache

import numpy as np
import numpy.testing as npt
import pandas as pd
import scmdata
import scmdata.database
import scmdata.processing
from pint.errors import DimensionalityError

from .ciceroscm import ciceroscm_post_process
from .fair import fair_post_process
from .magicc7 import calculate_co2_and_nonco2_warming_magicc, magicc7_post_process

LOGGER = logging.getLogger(__name__)
_CLIMATE_VARIABLE_DEFINITION_CSV = os.path.join(
    os.path.dirname(__file__), "variable_definitions.csv"
)


@lru_cache
def _get_climate_variable_definitions(fname):
    return pd.read_csv(fname)


def convert_openscm_runner_variables_to_ar6_wg3_variables(in_var):
    mapping = {
        "Surface Air Temperature Change": "Raw Surface Temperature (GSAT)",
        "Surface Air Ocean Blended Temperature Change": "Raw Surface Temperature (GMST)",
        "Heat Uptake|Ocean": "Ocean Heat Uptake",
        "Effective Radiative Forcing|Aerosols|Direct Effect|SOx": "Effective Radiative Forcing|Aerosols|Direct Effect|Sulfur",
    }

    try:
        return mapping[in_var]
    except KeyError:
        return in_var


def check_hist_warming_period(period):
    """
    Check period for historical warming calculations

    Parameters
    ----------
    period : str
        Input period, must be formatted as "YYYY-YYYY" where the first year is
        less than or equal to the last year. The last year is included in the
        period.

    Returns
    -------
    range
        All years in the period

    Raises
    ------
    ValueError
        ``period`` is formatted incorrectly
    """

    def _raise_error():
        raise ValueError(
            f"`period` must be a string of the form 'YYYY-YYYY' (with the first year "
            f"being less than or equal to the second), we received {period}"
        )

    if len(period) != 9:
        _raise_error()

    try:
        split = period.split("-")
    except TypeError:
        _raise_error()

    if len(split) != 2:
        _raise_error()

    try:
        start_year = int(split[0])
        end_year = int(split[1])
    except TypeError:
        _raise_error()

    if start_year > end_year:
        _raise_error()

    return range(start_year, end_year + 1)


def calculate_exceedance_probability_timeseries(
    res,
    exceedance_probability_calculation_var,
    test_run=False,
    historical_warming=0.85,
    historical_warming_reference_period="1850-1900",
    historical_warming_evaluation_period="1995-2014",
):
    """
    Calculate the timeseries with which we should determine exceedance probabilities.

    Please note that calculating the statistical properties like the exceedance probability is done on the count of the raw, full ensemble data.
    It  cannot be derived from from the time series of the final statistical indicator afterwards.
    """
    hist_temp_ref_period = check_hist_warming_period(
        historical_warming_reference_period
    )
    hist_temp_evaluation_period = check_hist_warming_period(
        historical_warming_evaluation_period
    )
    historical_warming_unit = "K"

    LOGGER.info(
        "Adjusting median of %s-%s warming (rel. to %s-%s) to %s%s",
        hist_temp_evaluation_period[0],
        hist_temp_evaluation_period[-1],
        hist_temp_ref_period[0],
        hist_temp_ref_period[-1],
        historical_warming,
        historical_warming_unit,
    )

    exceedance_probability_timeseries_raw = res.filter(
        variable=f"Raw {exceedance_probability_calculation_var}",
        unit=historical_warming_unit,
    )
    exceedance_probability_timeseries_rel_ref_period = (
        exceedance_probability_timeseries_raw.relative_to_ref_period_mean(
            year=hist_temp_ref_period
        ).drop_meta(["reference_period_start_year", "reference_period_end_year"])
    )
    exceedance_probability_timeseries = (
        exceedance_probability_timeseries_rel_ref_period.adjust_median_to_target(
            historical_warming,
            hist_temp_evaluation_period,
            process_over=("run_id",),
        )
    )

    # output checks
    hist_temp_grouper_cols = exceedance_probability_timeseries.get_meta_columns_except(
        "run_id"
    )

    def _get_median_hist_warming(inp):
        return (
            inp.filter(year=hist_temp_evaluation_period)
            .timeseries()
            .mean(axis="columns")
            .groupby(hist_temp_grouper_cols)
            .median()
        )

    inp_vals = _get_median_hist_warming(exceedance_probability_timeseries_raw)
    check_vals = _get_median_hist_warming(exceedance_probability_timeseries)
    shifts = check_vals - inp_vals
    shifts_after_rebase = check_vals - _get_median_hist_warming(
        exceedance_probability_timeseries_rel_ref_period
    )

    if not np.isclose(shifts, shifts[0], atol=5 * 1e-3).all():
        LOGGER.exception(
            "Careful of scenarios which break match with history! `shifts`: %s",
            shifts,
        )
    else:
        LOGGER.info("`shifts`: %s", shifts)
        LOGGER.info("`shifts_after_rebase`: %s", shifts_after_rebase)

    if not test_run:
        try:
            npt.assert_allclose(
                check_vals,
                historical_warming,
                rtol=1e-2,  # to within 1%
                err_msg=f"{check_vals}",
            )
        except AssertionError:
            LOGGER.exception("Careful of scenarios which break match with history!")

    exceedance_probability_timeseries["variable"] = (
        exceedance_probability_calculation_var
    )
    return exceedance_probability_timeseries


def calculate_co2_and_nonco2_warming_and_remove_extras(res):
    """
    Calculate non-CO2 warming. Currently only implemented for MAGICC, which can
    be run twice to allow for this calculation, using (the CLI option)
    `co2_and_non_co2_warming`.
    """
    out = []
    for cmrun in res.groupby("climate_model"):
        climate_model = cmrun.get_unique_meta("climate_model", no_duplicates=True)
        if climate_model.startswith("MAGICC"):
            all_forcers_run = cmrun.filter(rf_total_runmodus="ALL").drop_meta(
                "rf_total_runmodus"
            )
            out.append(all_forcers_run)
            out.append(calculate_co2_and_nonco2_warming_magicc(cmrun))
        else:
            raise NotImplementedError(climate_model)

    return scmdata.run_append(out)


def post_process(
    res,
    outdir,
    test_run=False,
    save_raw_output=False,
    co2_and_non_co2_warming=False,
    # for exceedance probability calculations
    temp_thresholds=(1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0),
    peak_percentiles=(5, 10, 17, 25, 33, 50, 66, 67, 75, 83, 90, 95),
    percentiles=(
        5,
        10,
        1 / 6 * 100,
        17,
        25,
        33,
        50,
        66,
        67,
        75,
        83,
        5 / 6 * 100,
        90,
        95,
    ),
    historical_warming=0.85,
    historical_warming_reference_period="1850-1900",
    historical_warming_evaluation_period="1995-2014",
):
    LOGGER.info("Beginning climate post-processing")
    LOGGER.info("Removing unknown units and keeping only World data")
    res = res.filter(unit="unknown", keep=False).filter(region="World")

    LOGGER.info(
        "Renaming variables from OpenSCM-Runner conventions to AR6 WG3 conventions"
    )
    res["variable"] = res["variable"].apply(
        convert_openscm_runner_variables_to_ar6_wg3_variables
    )

    LOGGER.info("Performing climate model specific fixes")
    all_res = []
    for res_cm in res.groupby("climate_model"):
        climate_model = res_cm.get_unique_meta("climate_model", no_duplicates=True)
        LOGGER.info("Processing %s data", climate_model)

        if climate_model.startswith("MAGICCv7"):
            res_cm = magicc7_post_process(res_cm)

        if climate_model.startswith("FaIRv1.6"):
            res_cm = fair_post_process(res_cm)

        if climate_model.startswith("CICERO-SCM"):
            res_cm = ciceroscm_post_process(res_cm)

        all_res.append(res_cm)

    LOGGER.info("Recombining post-processed data")
    res = scmdata.run_append(all_res)

    def _rename_vars(v):
        mapping = {
            "Effective Radiative Forcing|Greenhouse Gases": "Effective Radiative Forcing|Basket|Greenhouse Gases",
            "Effective Radiative Forcing|Anthropogenic": "Effective Radiative Forcing|Basket|Anthropogenic",
        }

        try:
            out = mapping[v]
            LOGGER.debug("Renaming %s to %s", v, out)
            return out
        except KeyError:
            LOGGER.debug("Not renaming %s", v)
            return v

    LOGGER.info("Performing further variable renaming")
    res["variable"] = res["variable"].apply(_rename_vars)

    if save_raw_output:
        LOGGER.info("Saving raw output (with renamed variables) to disk")
        if "parameters" in res.metadata:
            res.metadata["parameters"] = json.dumps(res.metadata["parameters"])

        database = scmdata.database.ScmDatabase(
            os.path.join(outdir, "raw_climate_output"),
            levels=["climate_model", "model", "scenario"],
        )
        for c in [
            "climate_model",
            "model",
            "scenario",
            "variable",
            "region",
            "unit",
            "rf_total_runmodus",
        ]:
            if c in res.meta:
                res[c] = res[c].apply(str)

        # TODO: add test for save raw output with non-CO2 on
        database.save(res)

    if co2_and_non_co2_warming:
        LOGGER.info("Calculating non-CO2 warming")
        res = calculate_co2_and_nonco2_warming_and_remove_extras(res)

    LOGGER.info("Calculating exceedance probability timeseries")
    exceedance_probability_calculation_var = "Surface Temperature (GSAT)"
    exceedance_probability_timeseries = calculate_exceedance_probability_timeseries(
        res,
        exceedance_probability_calculation_var,
        test_run=test_run,
        historical_warming=historical_warming,
        historical_warming_reference_period=historical_warming_reference_period,
        historical_warming_evaluation_period=historical_warming_evaluation_period,
    )
    res = res.append(exceedance_probability_timeseries)

    year_filter = range(1995, 2101)
    LOGGER.info("Keeping only data from %s", year_filter)
    res = res.filter(year=year_filter)

    LOGGER.info("Calculating Non-CO2 GHG ERF")
    helper = res.filter(variable="Effective Radiative Forcing*")
    res = [res]

    erf_nonco2_ghg = helper.filter(
        variable="Effective Radiative Forcing|Basket|Greenhouse Gases"
    ).subtract(
        helper.filter(variable="Effective Radiative Forcing|CO2"),
        op_cols={
            "variable": "Effective Radiative Forcing|Basket|Non-CO2 Greenhouse Gases"
        },
    )

    if (
        erf_nonco2_ghg.get_unique_meta("unit", no_duplicates=True)
        != "watt / meter ** 2"
    ):
        raise AssertionError("Unexpected forcing unit")

    erf_nonco2_ghg["unit"] = "W/m^2"
    res.append(erf_nonco2_ghg)

    LOGGER.info("Calculating Non-CO2 Anthropogenic ERF")
    erf_nonco2_anthropogenic = helper.filter(
        variable="Effective Radiative Forcing|Basket|Anthropogenic"
    ).subtract(
        helper.filter(variable="Effective Radiative Forcing|CO2"),
        op_cols={
            "variable": "Effective Radiative Forcing|Basket|Non-CO2 Anthropogenic"
        },
    )
    if (
        erf_nonco2_anthropogenic.get_unique_meta("unit", no_duplicates=True)
        != "watt / meter ** 2"
    ):
        raise AssertionError("Unexpected forcing unit")

    erf_nonco2_anthropogenic["unit"] = "W/m^2"
    res.append(erf_nonco2_anthropogenic)

    LOGGER.info("Joining derived variables and data back together")
    res = scmdata.run_append(res)

    # check all variable names
    LOGGER.info("Converting all variable names and units to standard definitions")

    def _convert_to_standard_name_and_unit(vdf):
        climate_variable_definitions = _get_climate_variable_definitions(
            _CLIMATE_VARIABLE_DEFINITION_CSV
        )
        variable = vdf.get_unique_meta("variable", True)

        try:
            standard_unit = climate_variable_definitions.set_index("Variable").loc[
                variable
            ]["Unit"]
        except KeyError as exc:
            raise ValueError(
                f"{variable} not in {_CLIMATE_VARIABLE_DEFINITION_CSV}"
            ) from exc
        try:
            return vdf.convert_unit(standard_unit)
        except DimensionalityError as exc:
            raise ValueError(
                "Cannot convert {} units of {} to {}".format(
                    variable, vdf.get_unique_meta("unit", True), standard_unit
                )
            ) from exc

    res = res.groupby("variable").map(_convert_to_standard_name_and_unit)

    LOGGER.info("Calculating percentiles")
    res_percentiles = res.quantiles_over(
        "run_id", np.array(percentiles) / 100
    ).reset_index()
    res_percentiles["percentile"] = res_percentiles["quantile"] * 100
    res_percentiles = res_percentiles.drop("quantile", axis="columns")

    LOGGER.info("Mangling variable name with climate model and percentile")
    res_percentiles["variable"] = (
        res_percentiles["variable"].astype(str)
        + "|"
        + res_percentiles["climate_model"].astype(str)
        + "|"
        + res_percentiles["percentile"].astype(float).round(1).astype(str)
        + "th Percentile"
    )
    res_percentiles = scmdata.ScmRun(
        res_percentiles.drop(["climate_model", "percentile"], axis="columns")
    )

    LOGGER.info(
        "Calculating exceedance probabilities and exceedance probability timeseries"
    )
    res_exceedance_probs_var = res.filter(
        variable=exceedance_probability_calculation_var
    )
    exceedance_probs_by_temp_threshold = []
    exceedance_probs_tss = []
    for threshold in temp_thresholds:
        LOGGER.info("Calculating %s exceedance probabilities", threshold)
        for store, func, output_name in (
            (
                exceedance_probs_by_temp_threshold,
                scmdata.processing.calculate_exceedance_probabilities,
                f"Exceedance Probability {threshold}C",
            ),
            (
                exceedance_probs_tss,
                scmdata.processing.calculate_exceedance_probabilities_over_time,
                f"Exceedance Probability {threshold}C",
            ),
        ):
            store.append(
                func(
                    res_exceedance_probs_var,
                    threshold,
                    process_over_cols=("run_id",),
                    output_name=output_name,
                )
            )

    exceedance_probs_tss = pd.concat(exceedance_probs_tss).reset_index()
    exceedance_probs_tss["variable"] = (
        exceedance_probs_tss["variable"].astype(str)
        + "|"
        + exceedance_probs_tss["climate_model"].astype(str)
    )
    exceedance_probs_tss = exceedance_probs_tss.drop("climate_model", axis="columns")
    res_percentiles = res_percentiles.append(exceedance_probs_tss)

    reporting_groups = ["climate_model", "model", "scenario"]
    exceedance_probs_by_temp_threshold = pd.concat(
        exceedance_probs_by_temp_threshold, axis=1
    )
    exceedance_probs_by_temp_threshold = exceedance_probs_by_temp_threshold.reset_index(
        list(
            set(exceedance_probs_by_temp_threshold.index.names) - set(reporting_groups)
        ),
        drop=True,
    )

    LOGGER.info("Calculating peak warming and peak warming year")
    peaks = scmdata.processing.calculate_peak(res_exceedance_probs_var)
    peak_years = scmdata.processing.calculate_peak_time(res_exceedance_probs_var)

    def _get_quantiles(idf):
        return (
            idf.groupby(reporting_groups)
            .quantile(np.array(peak_percentiles) / 100)
            .unstack()
        )

    peaks_quantiles = _get_quantiles(peaks)
    peak_years_quantiles = _get_quantiles(peak_years).astype(int)

    def rename_quantiles(quantile):
        percentile = int(quantile * 100)
        if np.isclose(percentile, 50):
            plabel = "median"
        else:
            plabel = f"p{percentile}"

        return plabel

    peaks_quantiles.columns = (
        peaks_quantiles.columns.map(rename_quantiles).astype(str) + " peak warming"
    )
    peak_years_quantiles.columns = (
        peak_years_quantiles.columns.map(rename_quantiles).astype(str)
        + " year of peak warming"
    )

    LOGGER.info("Creating meta table")
    meta_table = pd.concat(
        [
            exceedance_probs_by_temp_threshold,
            peaks_quantiles,
            peak_years_quantiles,
        ],
        axis=1,
    )

    def mangle_meta_table_climate_model(idf):
        out = idf.copy()
        climate_model = idf.name
        out.columns = out.columns + f" ({climate_model})"

        return out

    meta_table = (
        meta_table.groupby("climate_model", group_keys=False)
        .apply(mangle_meta_table_climate_model)
        .reset_index("climate_model", drop=True)
    )

    LOGGER.info("Exiting post-processing")
    return res, res_percentiles, meta_table
