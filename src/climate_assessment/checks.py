import os
from logging import getLogger

import numpy as np
import pandas as pd
import pyam

from .climate import (
    DEFAULT_CICEROSCM_VERSION,
    DEFAULT_FAIR_VERSION,
    DEFAULT_MAGICC_VERSION,
)
from .utils import _diff_variables, require_var_allyears

# output file location
OUT_FOLDER_NAME = "output"
OUT_FOLDER = os.path.join(os.path.dirname(__file__), "..", "..", OUT_FOLDER_NAME)
LOGGER = getLogger(__name__)


def _write_file(outdir, df, filename, csv=True):
    if not os.path.isdir(outdir):
        os.mkdir(outdir)

    if not df.empty:
        if csv:
            df.to_csv(os.path.join(outdir, filename))


def filter_and_convert(df, variable):
    if not df.filter(variable=variable).empty:
        return (
            df.filter(variable=variable)
            .convert_unit("Mt CO2/yr", "Gt CO2/yr")
            .timeseries()
        )


def add_categorization(
    dfar6,
    peakc1=1.5,
    model_version=None,
    prefix="AR6 climate diagnostics",
    model="magicc",
    eoc_percentiles=(5, 10, 17, 25, 33, 50, 66, 67, 75, 83, 90, 95),
):
    meta_docs = {}
    specs = {}
    plotting_args = {"color": "category", "linewidth": 0.2}
    specs["plotting_args"] = plotting_args

    if model.lower() == "fair":
        if model_version is None:
            model_version = DEFAULT_FAIR_VERSION
        model_str = "FaIRv{}".format(model_version)
    elif model.lower() == "ciceroscm":
        if model_version is None:
            model_version = DEFAULT_CICEROSCM_VERSION
        model_str = "CICERO-SCM"  # TODO: Update this to include versioning?
    else:
        if model_version is None:
            model_version = DEFAULT_MAGICC_VERSION
        model_str = "MAGICC{}".format(model_version)

    # TODO: move this into the climate post-processing in future
    for p in eoc_percentiles:
        v = "{}|Surface Temperature (GSAT)|{}|{:.1f}th Percentile".format(
            prefix, model_str, p
        )
        p_temperature = dfar6.filter(variable=v).timeseries()
        p_name = "median" if p == 50 else "p{:.0f}".format(p)
        name = "{} warming in 2100 ({})".format(p_name, model_str)
        dfar6.set_meta(p_temperature[2100], name)
        meta_docs[
            name
        ] = "{} warming above in 2100 above pre-industrial temperature as computed by {}".format(
            p_name, model_str
        )

    # select columns used for categorization
    TmedEOC = "median warming in 2100 ({})".format(model_str)
    Tp33Peak = "p33 peak warming ({})".format(model_str)
    TmedPeak = "median peak warming ({})".format(model_str)
    Tp67Peak = "p67 peak warming ({})".format(model_str)

    # set default for if no climate assessment happened
    dfar6.meta["Category"] = "no-climate-assessment"
    dfar6.meta["Category_name"] = "no-climate-assessment"
    meta_docs["Category"] = "Climate assessment category (short)"
    meta_docs["Category_name"] = "Climate assessment category (long)"

    def create_alternative_categories(dfar6, c15_peak, c15_EOC):
        # C8 (above 4°C, >4 peak warming with 50%)
        dfar6.meta.loc[(dfar6.meta[TmedPeak] >= 4.0), ["Category", "Category_name"]] = [
            "C8",
            "C8: Above 4.0°C",
        ]

        # C7 (below 4°C, < 4 peak warming with 50%)
        dfar6.meta.loc[(dfar6.meta[TmedPeak] < 4.0), ["Category", "Category_name"]] = [
            "C7",
            "C7: Below 4.0°C",
        ]

        # C6 (below 3°C, < 3 peak warming with 50%)
        dfar6.meta.loc[(dfar6.meta[TmedPeak] < 3.0), ["Category", "Category_name"]] = [
            "C6",
            "C6: Below 3.0°C",
        ]

        # C5 (below 2.5°C, < 2.5 peak warming with 50%)
        dfar6.meta.loc[(dfar6.meta[TmedPeak] < 2.5), ["Category", "Category_name"]] = [
            "C5",
            "C5: Below 2.5°C",
        ]

        # C4 (below 2°C, < 2 peak warming with 50%) (upper 2C)
        dfar6.meta.loc[(dfar6.meta[TmedPeak] < 2.0), ["Category", "Category_name"]] = [
            "C4",
            "C4: Below 2°C",
        ]

        # C3 (likely below 2°C, likely < 2 peak warming) (lower 2C)
        dfar6.meta.loc[(dfar6.meta[Tp67Peak] < 2.0), ["Category", "Category_name"]] = [
            "C3",
            "C3: Likely below 2°C",
        ]

        # C2 (1.5°C with high OS, likely > 1.5 peak warming and < 1.5 end of
        # century warming with >50%)
        dfar6.meta.loc[
            (dfar6.meta[Tp33Peak] > c15_peak) & (dfar6.meta[c15_EOC] < 1.5),
            ["Category", "Category_name"],
        ] = ["C2", "C2: Below 1.5°C with high OS"]

        # C1b (1.5°C with low OS, lower than likely probability of >= 1.5 peak
        # warming and < 1.5 end of century warming with 50%)
        dfar6.meta.loc[
            (dfar6.meta[Tp33Peak] <= c15_peak) & (dfar6.meta[c15_EOC] < 1.5),
            ["Category", "Category_name"],
        ] = ["C1b", "C1b: Below 1.5°C with low OS"]

        # C1a (1.5°C more likely than not with no overshoot)
        dfar6.meta.loc[
            dfar6.meta[TmedPeak] < 1.5,
            ["Category", "Category_name"],
        ] = ["C1a", "C1a: Below 1.5°C with no OS"]

        return dfar6

    c15_peak = peakc1
    c15_EOC = TmedEOC

    # categorize
    df = create_alternative_categories(dfar6, c15_peak, c15_EOC)

    # save out number of categories
    def number_of_scenarios_in_categories(df):
        return df.meta.reset_index().groupby("Category").count()["scenario"]

    LOGGER.info(number_of_scenarios_in_categories(df))

    return df


def count_variables_very_high(
    df, vars, num=9, prefix="AR6 climate diagnostics|Harmonized|"
):
    """Auxiliary function for :func:`climate_assessment.checks.add_completeness_category`.
    Performs check of variables + number of variables"""
    required_years = [2015, 2020, 2030, 2040, 2050, 2060, 2070, 2080, 2090, 2100]
    # mark the scenarios that are not sufficiently infilled for climate assessment:
    for v in vars:
        for y in required_years:
            df.require_variable(v, year=y, exclude_on_fail=True)
    # filter out the marked scenarios
    df.filter(exclude=False, inplace=True)
    numvars = len(df.filter(variable=str(prefix + "Emissions|*"), level=0).variable)
    if numvars >= num:
        return True
    else:
        return False


def add_completeness_category(
    df,
    filename,
    delete_no_confidence=False,
    output_csv=False,
    outdir="output",
    prefix="AR6 climate diagnostics|Harmonized|",
):
    """Add a meta column that specified the reporting completeness based
    on qualitative categories."""
    # create empty dataframe for multiple models
    dfnew = pd.DataFrame(
        columns=[
            "Model",
            "Scenario",
            "Region",
            "Variable",
            "Unit",
            "2015",
            "2020",
            "2025",
            "2030",
            "2035",
            "2040",
            "2045",
            "2050",
            "2055",
            "2060",
            "2065",
            "2070",
            "2075",
            "2080",
            "2085",
            "2090",
            "2095",
            "2100",
        ]
    )
    dfnew = pyam.IamDataFrame(dfnew)
    df_noconfidence = dfnew

    # "low confidence"
    low_vars = [
        str(prefix + "Emissions|CO2"),
    ]
    # "medium confidence"
    med_vars = [
        # "AR6 climate diagnostics|Harmonized|Emissions|CO2",
        str(prefix + "Emissions|CO2|Energy and Industrial Processes"),
        str(prefix + "Emissions|CO2|AFOLU"),
    ]
    # "high confidence"
    hi_vars = [
        # "AR6 climate diagnostics|Harmonized|Emissions|CO2",
        str(prefix + "Emissions|CO2|Energy and Industrial Processes"),
        str(prefix + "Emissions|CO2|AFOLU"),
        str(prefix + "Emissions|CH4"),
        str(prefix + "Emissions|N2O"),
    ]
    # "very high confidence" -> now will have additional check beyond these vars
    very_hi_vars = [
        # "AR6 climate diagnostics|Harmonized|Emissions|CO2",
        str(prefix + "Emissions|CO2|Energy and Industrial Processes"),
        str(prefix + "Emissions|CO2|AFOLU"),
        str(prefix + "Emissions|CH4"),
        str(prefix + "Emissions|N2O"),
    ]

    # TODO: find better way than doing loop
    for model, scen in df.index:
        if not df.filter(scenario=scen, model=model).empty:
            confidence = True
            if count_variables_very_high(
                df.filter(scenario=scen, model=model), very_hi_vars, 9, prefix
            ):
                df_scen = df.filter(scenario=scen, model=model)
                df_scen.set_meta(meta="very high", name="reporting-completeness")

            elif require_var_allyears(df.filter(scenario=scen, model=model), hi_vars):
                df_scen = df.filter(scenario=scen, model=model)
                df_scen.set_meta(meta="high", name="reporting-completeness")

            elif require_var_allyears(df.filter(scenario=scen, model=model), med_vars):
                df_scen = df.filter(scenario=scen, model=model)
                df_scen.set_meta(meta="medium", name="reporting-completeness")

            elif require_var_allyears(df.filter(scenario=scen, model=model), low_vars):
                df_scen = df.filter(scenario=scen, model=model)
                df_scen.set_meta(meta="low", name="reporting-completeness")

            else:
                # this captures for instance the scenarios that report only E&IP but not AFOLU
                df_scen = df.filter(scenario=scen, model=model)
                df_scen.set_meta(meta="no-confidence", name="reporting-completeness")
                df_noconfidence = pyam.concat([df_noconfidence, df_scen])
                if delete_no_confidence:
                    confidence = False

            if confidence:
                dfnew = pyam.concat([dfnew, df_scen])
    if output_csv:
        LOGGER.info(
            "Writing out scenarios with no confidence due to reporting completeness issues"
        )
        _write_file(
            outdir,
            df_noconfidence,
            "{}_excluded_scenarios_noconfidence.csv".format(filename),
        )

    return dfnew


def co2_energyandindustrialprocesses(df):
    """Auxiliary function for :func:`climate_assessment.checks.check_reported_co2`.
    Check if either CO2|Energy and Industrial are reported.
    Add the aggregate Energy and Industrial, if only subcomponents reported"""
    co2_sector_detail = True
    df_variables = df.index.get_level_values("variable")
    if "Emissions|CO2|Energy and Industrial Processes" not in df_variables:
        for ghg in ["Emissions|CO2|Energy", "Emissions|CO2|Industrial Processes"]:
            if ghg not in df_variables:
                co2_sector_detail = False
                break

        if co2_sector_detail:
            df = pyam.IamDataFrame(df)
            df.aggregate(
                variable="Emissions|CO2|Energy and Industrial Processes",
                components=[
                    "Emissions|CO2|Energy",
                    "Emissions|CO2|Industrial Processes",
                ],
                append=True,
            )
            df = df.timeseries()

    return df, co2_sector_detail


def _check_difference(df_scen, co2_total, co2_other, scenario, model):
    difference = _diff_variables(df_scen, co2_total, co2_other, out_variable="not used")

    if (difference.timeseries() == 0).all().all():
        message = (
            "%s is the same as %s "
            "for scenario "
            "`%s` produced by `%s` hence is removed"
        )
        LOGGER.info(message, co2_total, co2_other, scenario, model)
        df_scen = df_scen.filter(variable=co2_total, keep=False)

    return df_scen


def check_reported_co2(df, filename, output_csv=False, outdir="output"):
    """
    Check CO2 reporting.
    """
    df_withco2 = []
    df_noco2 = []
    # TODO: find better way than doing loop
    for (model, scen), df_scen in df.timeseries().groupby(["model", "scenario"]):
        df_scen = pyam.IamDataFrame(df_scen)

        co2_total = "Emissions|CO2"
        has_co2_total = co2_total in df_scen.variable
        co2_energy = "Emissions|CO2|Energy and Industrial Processes"
        has_co2_energy = co2_energy in df_scen.variable
        co2_afolu = "Emissions|CO2|AFOLU"
        has_co2_afolu = co2_afolu in df_scen.variable

        if has_co2_total and has_co2_energy and has_co2_afolu:
            message = (
                "%s is provided in addition to "
                "%s and %s for scenario "
                "`%s` produced by `%s` hence is removed to "
                "avoid any potential inconsistencies being introduced "
                "during harmonization"
            )
            LOGGER.info(message, co2_total, co2_energy, co2_afolu, scen, model)
            df_scen = df_scen.filter(variable=co2_total, keep=False)
        elif has_co2_total and has_co2_energy:
            df_scen = _check_difference(df_scen, co2_total, co2_energy, scen, model)
        elif has_co2_total and has_co2_afolu:
            df_scen = _check_difference(df_scen, co2_total, co2_afolu, scen, model)

        if co2_energy not in df_scen.variable:
            # Check for Emissions|CO2 having the required years
            has_required_co2 = "Emissions|CO2" in df_scen.variable

            if has_required_co2:
                # further check that all the required years are there
                required_years = [
                    2020,
                    2030,
                    2040,
                    2050,
                    2060,
                    2070,
                    2080,
                    2090,
                    2100,
                ]
                df_scen_co2_ts = df_scen.filter(variable="Emissions|CO2").timeseries()
                has_all_years = all(y in df_scen_co2_ts for y in required_years)
                nans = df_scen_co2_ts[required_years].isnull().any().any()
                has_required_co2 = has_all_years and not nans

            if has_required_co2:
                df_withco2.append(df_scen)
            else:
                LOGGER.info(
                    "\n==================================\n"
                    + "No Emissions|CO2 or Emissions|CO2|Energy and Industrial Processes found in "
                    + "scenario "
                    + scen
                    + " produced by "
                    + model
                    + "!\n"
                    + "=================================="
                )
                df_noco2.append(df_scen)

        else:
            df_withco2.append(df_scen)

    if df_noco2 and output_csv:
        df_noco2 = pyam.concat(df_noco2)
        _write_file(
            outdir,
            df_noco2,
            "{}_excluded_scenarios_noCO2orCO2EnIPreported.csv".format(filename),
        )

    if not df_withco2:
        # return empty df for later processing
        return df.copy().filter(variable="*", keep=False)

    return pyam.concat(df_withco2)


def check_against_historical(df, filename, instance, output_csv=False, outdir="output"):
    """Check against historical data.
    Currently requires 2015 to already be in the dataframe."""
    HISTORY_FOLDER_name = "harmonization"
    HISTORY_FOLDER = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), HISTORY_FOLDER_name
    )
    history = os.path.join(HISTORY_FOLDER, str("history_" + instance + ".csv"))
    dfhist = pyam.IamDataFrame(history)

    strict_emissionscheck = [
        "Emissions|CO2",
        "Emissions|CO2|Energy and Industrial Processes",
    ]

    medium_emissionscheck = [
        "Emissions|CH4",
        "Emissions|N2O",
    ]

    afolu_emissionscheck = [
        "Emissions|CO2|AFOLU",
    ]

    loose_emissionscheck = [
        "Emissions|BC",
        "Emissions|PFC|C2F6",
        "Emissions|PFC|C6F14",
        "Emissions|PFC|CF4",
        "Emissions|CO",
        # "Emissions|CO2|Other",
        # "Emissions|CO2|Waste",
        "Emissions|F-Gases",
        "Emissions|HFC",
        "Emissions|HFC|HFC125",
        "Emissions|HFC|HFC134a",
        "Emissions|HFC|HFC143a",
        "Emissions|HFC|HFC227ea",
        "Emissions|HFC|HFC23",
        # 'Emissions|HFC|HFC245ca', # not in historical dataset (RCMIP)
        # "Emissions|HFC|HFC245fa", # not included in historical dataset (RCMIP)
        "Emissions|HFC|HFC32",
        "Emissions|HFC|HFC43-10",
        "Emissions|NH3",
        "Emissions|NOx",
        "Emissions|OC",
        "Emissions|PFC",
        "Emissions|SF6",
        "Emissions|Sulfur",
        "Emissions|VOC",
    ]

    # mark all scenarios with negative non-CO2 values
    df.reset_exclude()
    for y in [2015]:
        for e in strict_emissionscheck:
            hist = dfhist.filter(
                variable=str("AR6 climate diagnostics|" + e + "|Unharmonized"), year=y
            )["value"]
            low_hist = float(0.7 * hist)
            high_hist = float(1.3 * hist)
            df.validate(criteria={e: {"lo": low_hist, "year": y}}, exclude_on_fail=True)
            df.validate(
                criteria={e: {"up": high_hist, "year": y}}, exclude_on_fail=True
            )
        for e in medium_emissionscheck:
            hist = dfhist.filter(
                variable=str("AR6 climate diagnostics|" + e + "|Unharmonized"), year=y
            )["value"]
            low_hist = float(0.5 * hist)
            high_hist = float(1.5 * hist)
            df.validate(criteria={e: {"lo": low_hist, "year": y}}, exclude_on_fail=True)
            df.validate(
                criteria={e: {"up": high_hist, "year": y}}, exclude_on_fail=True
            )
        for e in afolu_emissionscheck:
            hist = dfhist.filter(
                variable=str("AR6 climate diagnostics|" + e + "|Unharmonized"), year=y
            )["value"]
            low_hist = float(0.3 * hist)
            high_hist = float(2.0 * hist)
            df.validate(criteria={e: {"lo": low_hist, "year": y}}, exclude_on_fail=True)
            df.validate(
                criteria={e: {"up": high_hist, "year": y}}, exclude_on_fail=True
            )
        for e in loose_emissionscheck:
            hist = dfhist.filter(
                variable=str("AR6 climate diagnostics|" + e + "|Unharmonized"), year=y
            )["value"]
            low_hist = float(0.2 * hist)
            high_hist = float(5.0 * hist)
            df.validate(criteria={e: {"lo": low_hist, "year": y}}, exclude_on_fail=True)
            df.validate(
                criteria={e: {"up": high_hist, "year": y}}, exclude_on_fail=True
            )

    df_nondivergent = df.filter(exclude=False)
    divergent = df.filter(exclude=True)

    if output_csv:
        _write_file(
            outdir,
            divergent,
            "{}_excluded_scenarios_toofarfromhistorical.csv".format(filename),
        )

    # the case of skipping the entire scenario - remove from df to be passed on to harmonization.
    for model, scen in divergent.index:
        LOGGER.info(
            "\n==================================\n"
            + "Unexpected historical (2015) emissions found in "
            + "scenario "
            + scen
            + " produced by "
            + model
            + "!\n"
            + "=================================="
        )
    return df_nondivergent


def check_negatives(
    df,
    filename=None,
    negativethreshold=-0.1,
    outdir="output",
    prefix="",
):
    """
    Check for negative emissions and remove any timeseries which has negative non-CO2 values.
    """
    # set small non-negative non-CO2 values to zero
    df_co2 = df.filter(variable=f"{prefix}Emissions|CO2*").timeseries()
    df_nonco2 = df.filter(variable=f"{prefix}Emissions|CO2*", keep=False).timeseries()
    df_nonco2 = df_nonco2.where(
        (df_nonco2 > 0) | (df_nonco2 < negativethreshold) | df_nonco2.isnull(), other=0
    )
    df = pyam.IamDataFrame(pd.concat([df_co2, df_nonco2]))

    # TODO: only checking for negatives in these variables, not in cfcs/minor gases
    emissions_noco2 = [
        "Emissions|BC",
        "Emissions|PFC|C2F6",
        "Emissions|PFC|C6F14",
        "Emissions|PFC|CF4",
        "Emissions|CO",
        "Emissions|CH4",
        "Emissions|F-Gases",
        "Emissions|HFC",
        "Emissions|HFC|HFC125",
        "Emissions|HFC|HFC134a",
        "Emissions|HFC|HFC143a",
        "Emissions|HFC|HFC227ea",
        "Emissions|HFC|HFC23",
        # 'Emissions|HFC|HFC245ca',  # not in historical dataset (RCMIP)
        # "Emissions|HFC|HFC245fa",  # all nan in historical dataset (RCMIP)
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
    df_nonco2 = df.filter(
        variable=[f"{prefix}{s}" for s in emissions_noco2]
    ).timeseries()

    # remove any timeseries which still have negative non-CO2 values
    negative_nonco2 = (df_nonco2 < 0).any(axis=1).groupby(["model", "scenario"]).sum()
    negative_nonco2.name = "negative_nonco2_count"
    # make the negative non CO2 count line up with meta and fill anything which
    # isn't there (i.e. provides CO2 only) with 0
    negative_nonco2 = negative_nonco2.align(df.meta)[0].fillna(0)

    df.set_meta(negative_nonco2)
    df_no_negatives = df.filter(negative_nonco2_count=0.0)
    df_negatives = df.filter(negative_nonco2_count=0.0, keep=False)

    if filename:
        _write_file(
            outdir,
            df_negatives,
            "{}_excluded_scenarios_unexpectednegatives.csv".format(filename),
        )

    # the case of skipping the entire scenario - remove from df to be passed on to harmonization.
    for model, scen in df_negatives.index:
        LOGGER.info(
            "\n==================================\n"
            + "Unexpected (non-CO2) negative emissions found in "
            + "scenario "
            + scen
            + " produced by "
            + model
            + "!\n"
            + "=================================="
        )

    return df_no_negatives


def remove_rows_with_zero_in_harmonization_year(
    df, filename=None, harmonization_year=2015, outdir="output"
):
    """
    Check for zeros in harmonization year emissions and remove rows.
    """
    dfp = df.timeseries()

    # do before offset hence leave nan alone
    zero_historical_rows = dfp[harmonization_year] == 0
    zero_historical = dfp[zero_historical_rows]
    dfp = dfp[~zero_historical_rows]
    df = pyam.IamDataFrame(dfp)

    if not zero_historical.empty:
        LOGGER.info(
            "\n=================================="
            + "\nSome timeseries are removed because "
            + "\nthey have zero in the year of "
            + "\nharmonization. We will later replace "
            + "\nthese timeseries by infilled timeseries."
            + "\n=================================="
            + "\n{}".format(zero_historical)
        )

    if filename and not zero_historical.empty:
        _write_file(
            outdir,
            zero_historical,
            "{}_excluded_timeseries_zero_harmonization_year.csv".format(filename),
        )

    return df


def remove_rows_with_only_zero(df, filename=None, outdir="output"):
    """
    Check and remove rows with zero emissions.
    """
    dfp = df.timeseries()

    zero_rows = ((dfp == 0) | dfp.isnull()).all(axis=1)
    zeros = dfp[zero_rows]
    df = pyam.IamDataFrame(dfp.loc[~zero_rows])

    if not zeros.empty:
        LOGGER.info(
            "\n=================================="
            + "\nRemoving the following timeseries"
            + "\nbecause they report zero in every"
            + "\ntimestep."
            + "\n=================================="
            + "\n{}".format(zeros)
        )

    if filename and not zeros.empty:
        _write_file(
            outdir,
            zeros,
            "{}_excluded_timeseries_all_zero.csv".format(filename),
        )

    return df


def require_allyears(
    df,
    filename="test",
    output_csv=False,
    outdir="output",
    required_years=[2020, 2030, 2040, 2050, 2060, 2070, 2080, 2090, 2100],
    base_yr=2015,
    low_yr=2010,
):
    """Check if some variables are reported for the required years (drops per variable)"""
    # translate to pandas to do the tests per row. NaN is not reported
    dft = df.timeseries().reset_index()
    dft_out = pd.DataFrame()

    for required_yr in [base_yr, low_yr] + required_years:
        if required_yr not in dft:
            dft[required_yr] = np.nan

    # check for baseyear
    if output_csv:
        dft_out = dft_out.append(dft[(dft[base_yr].isna()) & (dft[low_yr].isna())])
    dft = dft[~((dft[base_yr].isna()) & (dft[low_yr].isna()))]

    # check for model years
    # TODO: find better way than doing loop
    for yr in required_years:
        if output_csv:
            dft_out = dft_out.append(dft[(dft[yr].isna())])
        dft = dft[~(dft[yr].isna())]

    # write out if wanted
    if output_csv:
        dft_out = pyam.IamDataFrame(dft_out)
        _write_file(
            outdir, dft_out, "{}_excluded_variables_notallyears.csv".format(filename)
        )
    return pyam.IamDataFrame(dft)


def require_allyears_and_drop_scenarios(
    df,
    filename="test",
    output_csv=False,
    outdir="output",
    required_years=[2020, 2030, 2040, 2050, 2060, 2070, 2080, 2090, 2100],
):
    """Filters out full scenarios if some year is not reported (using pyam)"""
    df.reset_exclude()
    dfnew = df.copy().filter(exclude=True)
    dfout = df.copy().filter(exclude=True)
    for mod, scen in df.index:
        df_scen = df.filter(model=mod, scenario=scen)
        if not df_scen.empty:
            vars = df_scen.variables()
            # mark the scenarios that are not sufficiently infilled for climate assessment:
            for v in vars:
                for y in required_years:
                    df_scen.require_variable(v, year=y, exclude_on_fail=True)
            df_scen_out = df_scen.filter(exclude=True, inplace=False)
            df_scen.filter(exclude=False, inplace=True)
            if not df_scen.empty:
                dfnew = pyam.concat([dfnew, df_scen])
            else:
                dfout = pyam.concat([dfout, df_scen_out])
    if output_csv:
        _write_file(
            outdir, dfout, "{}_excluded_scenarios_notallyears.csv".format(filename)
        )
    return dfnew


def reclassify_waste_and_other_co2_ar6(df):
    """
    Reclassify waste and other CO2 into the energy and industrial processes category

    Reclassify CO2 emissions reported under Emissions|CO2|Other and
    Emissions|CO2|Waste, instead putting them under
    Emissions|CO2|Energy and Industrial Processes.

    Parameters
    ----------
    df : :class:`pyam.IamDataFrame`
        The original set of reported emissions

    Returns
    -------
    :class:`pyam.IamDataFrame`
        Reclassified set of emissions.
    """
    # filter out the scenarios that do not need changes
    df_nochange = df.copy()
    df_nochange.require_variable(
        variable=["Emissions|CO2|Other", "Emissions|CO2|Waste"], exclude_on_fail=True
    )
    df_nochange.filter(exclude=True, inplace=True)
    df_nochange.reset_exclude()

    # select the scenarios that do need changes
    df_change = df.copy()
    df_change.require_variable(
        variable=["Emissions|CO2|Other", "Emissions|CO2|Waste"], exclude_on_fail=True
    )
    df_change.filter(exclude=False, inplace=True)
    if df_change.empty:
        return df_nochange

    # rename old CO2|Energy and Industrial Processes, to be replaced
    df_change.rename(
        variable={
            "Emissions|CO2|Energy and Industrial Processes": "Emissions|CO2|Energy and Industrial Processes|Incomplete"
        },
        inplace=True,
    )

    # use pandas to create new CO2|Energy and Industrial Processes by adding CO2|Other and CO2|Waste
    df_change_pd = df_change.as_pandas()
    varsum = [
        "Emissions|CO2|Waste",
        "Emissions|CO2|Other",
        "Emissions|CO2|Energy and Industrial Processes|Incomplete",
    ]
    df_change_notaffected_pd = df_change_pd[~df_change_pd.variable.isin(varsum)]
    df_change_notaffected_pd = df_change_notaffected_pd.drop("exclude", axis=1)
    df_change_notaffected_pyam = pyam.IamDataFrame(df_change_notaffected_pd)
    df_change_pd = df_change_pd[df_change_pd.variable.isin(varsum)]
    df_change_pd = df_change_pd.groupby(
        by=["model", "scenario", "year"], as_index=False
    )
    df_change_pd = df_change_pd.sum()
    df_change_pd["variable"] = "Emissions|CO2|Energy and Industrial Processes"
    df_change_pd["unit"] = "Mt CO2/yr"
    df_change_pd["region"] = "World"
    df_change_pd.drop("exclude", axis=1, inplace=True)
    df_change_pyam = pyam.IamDataFrame(df_change_pd)
    df_change = pyam.concat([df_change_pyam, df_change_notaffected_pyam])

    # recombine dataframes
    df_new = pyam.concat([df_change, df_nochange])

    return df_new


def perform_input_checks(
    df,
    output_csv_files=True,
    output_filename="checks",
    lead_variable_check=False,
    historical_check=False,
    reporting_completeness_check=False,
    outdir="output",
):
    """
    Perform several selected checks on the native emissions input to the climate
    assessment workflow.

    Arguments
    ----------
    input_df : :class:`pyam.IamDataFrame`
        Input native emissions before checks.

    inputcheck : bool
        Perform checks to remove unsuitable emissisons pathways. [Default: True]

    key_string: str
        Identifier string for writing out results. By default derived from
        the input_emissions_file string in a CLI command.

    outdir: str
        Path to output folder.

    Returns
    ----------
    :class:`pyam.IamDataFrame`
        IAM dataframe with only model-scenario that will be  without emissions.
        Output also includes the input emissions. The output is interpolated
        onto an annual timestep.
    """
    typechecks = "minimal"

    LOGGER.info("CHECK: if no non-co2 negatives are reported.")
    df = check_negatives(df, output_filename, outdir=outdir)

    LOGGER.info("CHECK: report emissions for all minimally required years.")
    df = require_allyears(
        df, output_filename, output_csv=output_csv_files, outdir=outdir
    )

    LOGGER.info("CHECK: combine E&IP if reported separately.")
    # TODO: find better way than doing loop
    dfnew = []
    for _, df_scen in df.timeseries().groupby(["model", "scenario"]):
        df_scen, _ = co2_energyandindustrialprocesses(df_scen)
        dfnew.append(df_scen)

    df = pyam.IamDataFrame(pd.concat(dfnew))

    LOGGER.info("CHECK: reclassify Waste and Other CO2 under E&IP.")
    df.reset_exclude()
    df = reclassify_waste_and_other_co2_ar6(df)

    LOGGER.info("CHECK: delete rows only reporting zero for the entire timeframe.")
    df = remove_rows_with_only_zero(df)

    if lead_variable_check and historical_check:
        typechecks = "leadhist"
        LOGGER.info("CHECK: check CO2 reporting")
        df = check_reported_co2(
            df, output_filename, output_csv=output_csv_files, outdir=outdir
        )
        LOGGER.info("CHECK: reporting not too far from historical data in 2015.")
        df = check_against_historical(
            df,
            output_filename,
            instance="ar6",
            output_csv=output_csv_files,
            outdir=outdir,
        )

    else:
        if lead_variable_check:
            typechecks = "lead"
            LOGGER.info("CHECK: check if co2 lead variables are reported.")
            df = check_reported_co2(
                df, output_filename, output_csv=output_csv_files, outdir=outdir
            )

        if historical_check:
            typechecks = "hist"
            LOGGER.info("CHECK: reporting not too far from historical data in 2015.")
            df = check_against_historical(
                df,
                output_filename,
                instance="ar6",
                output_csv=output_csv_files,
                outdir=outdir,
            )

    if reporting_completeness_check:
        typechecks = typechecks + "completeness"
        # perform all checks
        LOGGER.info("CHECK: add reporting completeness category.")
        df = add_completeness_category(
            df, output_filename, output_csv=output_csv_files, prefix="", outdir=outdir
        )

    if output_csv_files:
        _write_file(
            outdir, df, "{}_checkedinput_{}.csv".format(output_filename, typechecks)
        )

    return df


def infiller_vetting(
    df,
    prefix="AR6 climate diagnostics",
):
    """
    Filters out a set of harmonized emissions pathways ``df`` to then return
    an infiller_database that does not have emissions pathways that might skew
    infilling due to what is likely a model reporting error.
    """
    prefix = prefix + "|Harmonized|"
    em_criteria = [
        {f"{prefix}Emissions|BC": {"up": 2000}},
        # {f"{prefix}Emissions|HFC": {"up": 100000}},
        {f"{prefix}Emissions|CO": {"up": 20000}},
        {f"{prefix}Emissions|CO2|Energy and Industrial Processes": {"up": 160000}},
        {f"{prefix}Emissions|CO2|Energy and Industrial Processes": {"lo": -100000}},
        {f"{prefix}Emissions|CO2|AFOLU": {"up": 1e12}},
        {f"{prefix}Emissions|CH4": {"up": 50000}},
        # {f"{prefix}Emissions|F-Gases": {"up": 25000}},
        {f"{prefix}Emissions|N2O": {"up": 1e6}},
        {f"{prefix}Emissions|NH3": {"up": 2000}},
        {f"{prefix}Emissions|NOx": {"up": 5000}},
        # {f"{prefix}Emissions|PFC": {"up": 2500}},
        {f"{prefix}Emissions|Sulfur": {"up": 5000}},
        {f"{prefix}Emissions|VOC": {"up": 50000}},
    ]

    df.reset_exclude()
    for criterion in em_criteria:
        df.validate(criteria=criterion, exclude_on_fail=True)
    # TODO: replace filter by something faster, working on the meta
    df.filter(exclude=False, inplace=True)

    return df


def sanity_check_bounds_kyoto_emissions(output_postprocess, out_kyoto_infilled):
    """Check that the calculated Kyoto gases of the infilled emissions data
    are within certain bounds"""

    # Use dataframe instead of IAM dataframe
    df_out = output_postprocess.data
    years_bound = {"2015": [50000, 60000], "2020": [45000, 65000]}
    # Filter dataframe for Kyoto gas variables
    kyoto_fit = df_out.loc[
        lambda df_out: df_out["variable"].str.startswith(out_kyoto_infilled)
    ]
    # Check sanity for upper and lower bounds of year 2015 and 2020
    for year_bound in years_bound:
        # Filter dataframe per year
        kyoto_gas_em = kyoto_fit.loc[
            lambda kyoto_fit: kyoto_fit["year"] == int(year_bound)
        ].set_index(keys=["model", "scenario", "region", "variable", "unit", "year"])
        # Raise error if the value is smaller than the set bound
        if (kyoto_gas_em.value < years_bound[year_bound][0]).any():
            kyoto_gas_san = kyoto_gas_em.loc[
                (kyoto_gas_em["value"] < years_bound[year_bound][0])
            ]
            raise ValueError(
                f"The Kyoto gases of the infilled emissions data of "
                f"{[ind for ind in kyoto_gas_san.index]} is/are too small."
            )
        # Raise error if the value is bigger than the set bound
        elif (kyoto_gas_em.value > years_bound[year_bound][1]).any():
            kyoto_gas_san = kyoto_gas_em.loc[
                (kyoto_gas_em["value"] > years_bound[year_bound][1])
            ]
            raise ValueError(
                f"The Kyoto gases of infilled emissions data of "
                f"{[ind for ind in kyoto_gas_san.index]} is/are too big."
            )


def sanity_check_comparison_kyoto_gases(
    output_postprocess, out_kyoto_harmonized, out_kyoto_infilled
):
    """Check that the calculated Kyoto gases of the infilled emissions data
    is in every year smaller than the calculated Kyoto gases of the harmonized
    emission data"""

    def _helper(out_kyoto):
        # Use dataframe instead of IAM dataframe
        df_out = output_postprocess.data
        kyoto_fit = df_out.loc[
            lambda df_out: df_out["variable"].str.startswith(out_kyoto)
        ].set_index(keys=["model", "scenario", "region", "variable", "unit", "year"])

        return kyoto_fit

    # Filter dataframe for Kyoto gas variables
    kyoto_fit_harmonized = _helper(out_kyoto_harmonized)
    kyoto_fit_infilled = _helper(out_kyoto_infilled)
    # Raise error if Kyoto gases of infilled emissions data
    # are smaller then the Kyoto gases of harmonized emissions
    if (kyoto_fit_infilled.values < kyoto_fit_harmonized.values).any():
        kyoto_wrong = kyoto_fit_infilled.loc[
            kyoto_fit_infilled.values < kyoto_fit_harmonized.values
        ]
        raise ValueError(
            f"The Kyoto gases of infilled emissions data of {[ind for ind in kyoto_wrong.index]} "
            f"are smaller then the Kyoto gases of harmonized emissions"
        )


def sanity_check_hierarchy(
    co2_inf_db,
    harmonized,
    infilled,
    out_afolu,
    out_fossil,
):
    """Check that hierarchy of variables is internally consistent (in this case
    check that Emissions|CO2 is the sum of AFOLU and Energy and Industrial
    Processes emissions)"""

    def _concat_df(iam_df, prefix):
        concat_iam_df = pyam.concat(
            [
                iam_df.filter(variable=prefix + out_afolu),
                iam_df.filter(variable=prefix + out_fossil),
            ]
        )
        return concat_iam_df

    def _create_pivot(iam_df):
        pivot_df = iam_df.data.pivot(
            index=["year", "model", "scenario", "region"],
            columns="variable",
            values="value",
        )
        return pivot_df

    infill_db_pivot = _create_pivot(co2_inf_db).values
    harmonized_pivot = (
        _create_pivot(_concat_df(harmonized, "*Harmonized|"))
        .aggregate("sum", axis="columns")
        .to_frame()
        .values
    )
    infilled_pivot = (
        _create_pivot(_concat_df(infilled, "*Infilled|"))
        .aggregate("sum", axis="columns")
        .to_frame()
        .values
    )

    if not (np.isclose(infill_db_pivot, harmonized_pivot)).all():
        raise ValueError(
            "The sum of AFOLU and Energy and Industrial Processes "
            "is not equal to Harmonized|Emissions|CO2"
        )

    if not (np.isclose(infill_db_pivot, infilled_pivot)).all():
        raise ValueError(
            "The sum of AFOLU and Energy and Industrial Processes "
            "is not equal to Infilled|Emissions|CO2"
        )
