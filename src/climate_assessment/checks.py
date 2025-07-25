import os
from logging import getLogger

import numpy as np
import pandas as pd
import pyam
from pyam import IamDataFrame

from .climate import (
    DEFAULT_CICEROSCM_VERSION,
    DEFAULT_FAIR_VERSION,
    DEFAULT_MAGICC_VERSION,
)
from .utils import _diff_variables

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
        model_str = f"FaIRv{model_version}"
    elif model.lower() == "ciceroscm":
        if model_version is None:
            model_version = DEFAULT_CICEROSCM_VERSION
        model_str = "CICERO-SCM"  # TODO: Update this to include versioning?
    else:
        if model_version is None:
            model_version = DEFAULT_MAGICC_VERSION
        model_str = f"MAGICC{model_version}"

    # TODO: move this into the climate post-processing in future
    for p in eoc_percentiles:
        v = f"{prefix}|Surface Temperature (GSAT)|{model_str}|{p:.1f}th Percentile"
        p_temperature = dfar6.filter(variable=v).timeseries()
        p_name = "median" if p == 50 else f"p{p:.0f}"
        name = f"{p_name} warming in 2100 ({model_str})"
        dfar6.set_meta(p_temperature[2100], name)
        meta_docs[name] = (
            f"{p_name} warming above in 2100 above pre-industrial temperature as computed by {model_str}"
        )

    # select columns used for categorization
    TmedEOC = f"median warming in 2100 ({model_str})"
    Tp33Peak = f"p33 peak warming ({model_str})"
    TmedPeak = f"median peak warming ({model_str})"
    Tp67Peak = f"p67 peak warming ({model_str})"

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


def add_completeness_category(
    df,
    filename=None,
    output_csv=False,
    outdir="output",
    prefix="AR6 climate diagnostics|Harmonized|",
):
    """Add a meta column that specified the reporting completeness based
    on qualitative categories.
    """
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
        str(prefix + "Emissions|Sulfur"),
    ]

    df_in = df.copy()

    required_years = [2020, 2030, 2040, 2050, 2060, 2070, 2080, 2090, 2100]
    required_years_very_hi = [
        2015,
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

    # mark the scenarios without sufficient timeseries data for climate assessment
    # very high confidence scenarios:
    df_in.require_data(
        variable=very_hi_vars, year=required_years_very_hi, exclude_on_fail=True
    )
    df_very_hi = df_in.filter(exclude=False, inplace=False)
    df_very_hi.set_meta(meta="very high", name="reporting-completeness")
    df_remaining = df_in.filter(exclude=True, inplace=False)
    if not df_remaining.empty:
        df_remaining.exclude = False
        # high confidence scenarios:
        df_remaining.require_data(
            variable=hi_vars, year=required_years, exclude_on_fail=True
        )
        df_high = df_remaining.filter(exclude=False, inplace=False)
        df_high.set_meta(meta="high", name="reporting-completeness")
        df_remaining = df_remaining.filter(exclude=True, inplace=False)
        if not df_remaining.empty:
            df_remaining.exclude = False
            # medium confidence scenarios:
            df_remaining.require_data(
                variable=med_vars, year=required_years, exclude_on_fail=True
            )
            df_med = df_remaining.filter(exclude=False, inplace=False)
            df_med.set_meta(meta="medium", name="reporting-completeness")
            df_remaining = df_remaining.filter(exclude=True, inplace=False)
            if not df_remaining.empty:
                df_remaining.exclude = False
                # low confidence scenarios:
                df_remaining.require_data(
                    variable=low_vars, year=required_years, exclude_on_fail=True
                )
                df_low = df_remaining.filter(exclude=False, inplace=False)
                df_low.set_meta(meta="low", name="reporting-completeness")
                df_remaining = df_remaining.filter(exclude=True, inplace=False)
                if not df_remaining.empty:
                    df_remaining.exclude = False
                    # no confidence scenarios:
                    df_remaining.set_meta(
                        meta="no-confidence", name="reporting-completeness"
                    )
                    if output_csv:
                        LOGGER.info(
                            "Writing out scenarios with no confidence due to reporting completeness issues"
                        )
                        _write_file(
                            outdir,
                            df_remaining,
                            f"{filename}_excluded_scenarios_noconfidence.csv",
                        )
                    # combine all the dataframes
                    df_confidence_column = pyam.concat(
                        [df_very_hi, df_high, df_med, df_low, df_remaining]
                    )
                else:
                    df_confidence_column = pyam.concat(
                        [df_very_hi, df_high, df_med, df_low]
                    )
            else:
                df_confidence_column = pyam.concat([df_very_hi, df_high, df_med])
        else:
            df_confidence_column = pyam.concat([df_very_hi, df_high])
    else:
        df_confidence_column = df_very_hi

    return df_confidence_column


def co2_energyandindustrialprocesses(df):
    """Auxiliary function for :func:`climate_assessment.checks.check_reported_co2`.
    Check if either CO2|Energy and Industrial are reported.
    Add the aggregate Energy and Industrial, if only subcomponents reported
    """
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
            "%s is the same as %s for scenario `%s` produced by `%s` hence is removed"
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
    for model, scenario in df.index:
        df_scen = df.filter(model=model, scenario=scenario)

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
            LOGGER.info(message, co2_total, co2_energy, co2_afolu, scenario, model)
            df_scen = df_scen.filter(variable=co2_total, keep=False)
        elif has_co2_total and has_co2_energy:
            df_scen = _check_difference(df_scen, co2_total, co2_energy, scenario, model)
        elif has_co2_total and has_co2_afolu:
            df_scen = _check_difference(df_scen, co2_total, co2_afolu, scenario, model)

        if co2_energy not in df_scen._data.index.get_level_values("variable").unique():
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
                    + scenario
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
            f"{filename}_excluded_scenarios_noCO2orCO2EnIPreported.csv",
        )

    if not df_withco2:
        # return empty df for later processing
        return df.copy().filter(variable="*", keep=False)

    return pyam.concat(df_withco2)


def check_against_historical(df, filename, instance, output_csv=False, outdir="output"):
    """Check against historical data.
    Currently requires 2015 to already be in the dataframe.
    """
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
    df.exclude = False
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
            f"{filename}_excluded_scenarios_toofarfromhistorical.csv",
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
            f"{filename}_excluded_scenarios_unexpectednegatives.csv",
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
            + f"\n{zero_historical}"
        )

    if filename and not zero_historical.empty:
        _write_file(
            outdir,
            zero_historical,
            f"{filename}_excluded_timeseries_zero_harmonization_year.csv",
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
            + f"\n{zeros}"
        )

    if filename and not zeros.empty:
        _write_file(
            outdir,
            zeros,
            f"{filename}_excluded_timeseries_all_zero.csv",
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
        dft_out = pd.concat(
            [
                dft_out,
                dft[(dft[base_yr].isna()) & (dft[low_yr].isna())],
            ]
        )

    dft = dft[~((dft[base_yr].isna()) & (dft[low_yr].isna()))]

    # check for model years
    # TODO: find better way than doing loop
    for yr in required_years:
        if output_csv:
            dft_out = pd.concat(
                [
                    dft_out,
                    dft[(dft[yr].isna())],
                ]
            )
        dft = dft[~(dft[yr].isna())]

    # write out if wanted
    if output_csv:
        dft_out = pyam.IamDataFrame(dft_out)
        _write_file(outdir, dft_out, f"{filename}_excluded_variables_notallyears.csv")
    return pyam.IamDataFrame(dft)


def reclassify_waste_and_other_co2_ar6(df: IamDataFrame) -> IamDataFrame:
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
    # 1. filter all scenarios that have either emissions variable by df.filter(variable=["Emissions|CO2|Other", "Emissions|CO2|Waste"])
    #     + get list of indices
    # 2. do df.filter(index=indices, exclude=False) and df.filter(index=indices, exclude=True)

    # list scenarios that do need changes (as they report variables that we reclassify under "Energy and Industrial Processes")
    df_change_scenarios = df.filter(
        variable=["Emissions|CO2|Other", "Emissions|CO2|Waste"]
    ).index
    # dataframe with scenarios that DO need changes
    df_change = df.filter(index=df_change_scenarios, keep=True)
    df_change.exclude = False
    # dataframe with scenarios that DO NOT need changes
    df_nochange = df.filter(index=df_change_scenarios, keep=False)
    df_nochange.exclude = False

    # if no change is necessary, just return the dataframe
    # - possible test: df == df_nochange
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
    # which variables to sum
    varsum = [
        "Emissions|CO2|Waste",
        "Emissions|CO2|Other",
        "Emissions|CO2|Energy and Industrial Processes|Incomplete",
    ]
    # not affected variables of the same scenario:
    df_change_notaffected_pd = df_change_pd[~df_change_pd.variable.isin(varsum)]
    try:
        df_change_notaffected_pd = df_change_notaffected_pd.drop(
            columns=["exclude"]
        )  # drop exclude column in this timeseries
    except KeyError:
        pass
    df_change_notaffected_pyam = pyam.IamDataFrame(df_change_notaffected_pd)

    # group and sum the variables that are affected
    df_change_pd = df_change_pd[df_change_pd.variable.isin(varsum)]
    try:
        df_change_pd = df_change_pd.drop(
            columns=["exclude"]
        )  # drop exclude column in this timeseries
    except KeyError:
        pass
    df_change_pd = df_change_pd.groupby(
        by=["model", "scenario", "region", "unit", "year"], as_index=False
    )
    df_change_pd = df_change_pd.sum(numeric_only=True)
    df_change_pd["variable"] = "Emissions|CO2|Energy and Industrial Processes"

    # recombine variables of the scenarios that were changed (and change back to pyam IamDataFrame)
    df_change_pyam = pyam.IamDataFrame(df_change_pd)
    df_change = pyam.concat([df_change_pyam, df_change_notaffected_pyam])

    # recombine scenarios with and without changes dataframes
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
    -------
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
    df.exclude = False
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
        _write_file(outdir, df, f"{output_filename}_checkedinput_{typechecks}.csv")

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

    df.exclude = False
    for criterion in em_criteria:
        df.validate(criteria=criterion, exclude_on_fail=True)
    # TODO: replace filter by something faster, working on the meta
    df.filter(exclude=False, inplace=True)

    return df


def sanity_check_bounds_kyoto_emissions(output_postprocess, out_kyoto_infilled):
    """Check that the calculated Kyoto gases of the infilled emissions data
    are within certain bounds
    """
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
    emission data
    """

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
    Processes emissions)
    """

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
