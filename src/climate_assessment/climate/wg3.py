import datetime as dt
import logging

import scmdata

LOGGER = logging.getLogger(__name__)


def clean_wg3_scenarios(inp):
    inp.filter(
        variable=[
            "*Infilled|Emissions|CO2",
            "*Infilled|Emissions|F-Gases",
            "*Infilled|Emissions|HFC",
            "*Infilled|Emissions|PFC",
            "*Infilled|Emissions|Kyoto Gases (AR5-GWP100)",
            "*Infilled|Emissions|Kyoto Gases (AR6-GWP100)",
        ],
        keep=False,
        inplace=True,
    )

    infilled_emms_filter = "*Infilled*"
    df_clean = inp.filter(variable=infilled_emms_filter).data.copy()

    if df_clean.empty:
        LOGGER.error("No '%s' data available", infilled_emms_filter)

        return None

    replacements_variables = {
        r".*\|Infilled\|": "",
        "AFOLU": "MAGICC AFOLU",
        "Energy and Industrial Processes": "MAGICC Fossil and Industrial",
        "HFC43-10": "HFC4310mee",
        # "Sulfur": "SOx",
        # "VOC": "NMVOC",
        r"HFC\|": "",
        r"PFC\|": "",
        "HFC245ca": "HFC245fa",  # still needed?
    }
    for old, new in replacements_variables.items():
        df_clean["variable"] = df_clean["variable"].str.replace(old, new, regex=True)

    replacements_units = {
        "HFC43-10": "HFC4310mee",
    }
    for old, new in replacements_units.items():
        df_clean["unit"] = df_clean["unit"].str.replace(old, new)

    # avoid MAGICC's weird end year effects by ensuring scenarios go just beyond
    # the years we're interested in
    scens_scmrun = scmdata.ScmRun(df_clean)
    output_times = [
        dt.datetime(y, 1, 1) for y in scens_scmrun["year"].tolist() + [2110]
    ]
    scens_scmrun = scens_scmrun.interpolate(
        output_times,
        extrapolation_type="constant",
    )
    clean_scenarios = scens_scmrun.timeseries().reset_index()

    def fix_hfc_unit(variable):
        if "HFC" not in variable:
            raise NotImplementedError(variable)

        return "kt {}/yr".format(variable.split("|")[-1])

    hfc_rows = clean_scenarios["variable"].str.contains("HFC")
    clean_scenarios.loc[hfc_rows, "unit"] = clean_scenarios.loc[
        hfc_rows, "variable"
    ].apply(fix_hfc_unit)

    try:
        # if extra col is floating around, remove it
        clean_scenarios = clean_scenarios.drop("unnamed: 0", axis="columns")
    except KeyError:
        pass

    return clean_scenarios
