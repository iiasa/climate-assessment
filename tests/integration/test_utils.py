import collections
import logging

import numpy as np
import pyam
import pytest
import scmdata

from climate_assessment.utils import add_gwp100_kyoto_wrapper

LOGGER = logging.getLogger(__name__)

CH4_GWP100_AR5 = 28
CH4_GWP100_AR6 = 27.9

SCEN_A = {"total_co2": [36000, 39000], "ch4": [350, 400]}
SCEN_B = {
    "total_co2": [36000, 40000],
    "ch4": [340, 350],
    "afolu_co2": [3000, -1000],
    "fossil_co2": [33000, 41000],
}
SCEN_C = {
    "total_co2": [36000, 40500],
    "ch4": [350, 300],
    "afolu_co2": [3000, -500],
    "fossil_co2": [33000, 41000],
}

SCEN_D = {
    "total_co2": [36000, 40500],
    "ch4": [350, 300],
    "afolu_co2": [3000, -500],
    "fossil_co2": [33000, 41000],
    "bc": [10, 9],
    "co": [980, 1000],
    "n2o": [7600, 6400],
    "nh3": [50, 55],
    "oc": [31, 30],
    "pfc": [16, 3],
    "sf6": [8, 2],
    "sulfur": [90, 70],
    "voc": [240, 220],
    "hfc125": [80, 90],
    "hfc134a": [200, 210],
    "hfc143a": [30, 40],
    "hfc227ea": [3.6, 3.7],
    "hfc23": [14, 12],
    "hfc32": [38, 49],
    "hfc43-10": [1.1, 1.0],
    "c2f6": [1.5, 1.6],
    "c6f14": [3.5, 3.6],
    "cf4": [10.9, 10.8],
}

EMISSIONS = {
    "total_co2": ["Emissions|CO2", "Mt CO2 / yr"],
    "ch4": ["Emissions|CH4", "Mt CH4 / yr"],
    "afolu_co2": ["Emissions|CO2|AFOLU", "Mt CO2 / yr"],
    "fossil_co2": ["Emissions|CO2|Energy and Industrial Processes", "Mt CO2 / yr"],
    "bc": ["Emissions|BC", "Mt BC / yr"],
    "co": ["Emissions|CO", "Mt CO / yr"],
    "n2o": ["Emissions|N2O", "kt N2O / yr"],
    "nh3": ["Emissions|NH3", "Mt NH3 / yr"],
    "oc": ["Emissions|OC", "Mt OC / yr"],
    "pfc": ["Emissions|PFC", "kt CF4-equiv / yr"],
    "sf6": ["Emissions|SF6", "kt SF6 / yr"],
    "sulfur": ["Emissions|Sulfur", "Mt SO2 / yr"],
    "voc": ["Emissions|VOC", "Mt VOC / yr"],
    "hfc125": ["Emissions|HFC|HFC125", "kt HFC125/yr"],
    "hfc134a": ["Emissions|HFC|HFC134a", "kt HFC134a/yr"],
    "hfc143a": ["Emissions|HFC|HFC143a", "kt HFC143a/yr"],
    "hfc227ea": ["Emissions|HFC|HFC227ea", "kt HFC227ea/yr "],
    "hfc23": ["Emissions|HFC|HFC23", "kt HFC23/yr"],
    "hfc32": ["Emissions|HFC|HFC32", "kt HFC32/yr"],
    "hfc43-10": ["Emissions|HFC|HFC43-10", "kt HFC43-10/yr"],
    "c2f6": ["Emissions|PFC|C2F6", "kt C2F6/yr"],
    "c6f14": ["Emissions|PFC|C6F14", "kt C6F14/yr"],
    "cf4": ["Emissions|PFC|CF4", "kt CF4/yr"],
}

VAR_NAME = ["Emissions|CO2", "Emissions|CH4"]
UNIT_NAME = ["Mt CO2 / yr", "Mt CH4 / yr"]
SCEN_NAME = ["scenario", "scenario"]
INDEX = [2015, 2020]


def expected_scen(scenario, ch4_gwp):
    scen_expected = [
        scenario["total_co2"][0] + scenario["ch4"][0] * ch4_gwp,
        scenario["total_co2"][1] + scenario["ch4"][1] * ch4_gwp,
    ]

    return scen_expected


def create_dataframe_input(scens: list):
    help_lst = collections.defaultdict(list)
    for index, scen in enumerate(scens):
        for emission in scen:
            help_lst["scen_array"].append(scen[emission])
            help_lst["var_name"].append(EMISSIONS[emission][0])
            help_lst["unit_name"].append(EMISSIONS[emission][1])
            help_lst["scen_name"].append(f"scenario_{index}")
        help_lst["exp_scen_array"].append(expected_scen(scen, CH4_GWP100_AR6))
        help_lst["exp_scen_name"].append(f"scenario_{index}")

    return help_lst


def create_dataframe(
    scen_array, var_name=None, unit_name=None, scen_name=None, index=None
):
    if index is None:
        index = INDEX
    if scen_name is None:
        scen_name = SCEN_NAME
    if unit_name is None:
        unit_name = UNIT_NAME
    if var_name is None:
        var_name = VAR_NAME
    start = scmdata.ScmRun(
        data=np.array(scen_array).T,
        index=index,
        columns={
            "variable": var_name,
            "unit": unit_name,
            "region": "World",
            "scenario": scen_name,
            "model": "test",
        },
    )
    return pyam.IamDataFrame(start.timeseries(time_axis="year"))


@pytest.mark.parametrize(
    "inp_variables,inp_units,inp_values,exp_values",
    (
        (
            [
                "Emissions|CO2",
            ],
            [
                "MtCO2 / yr",
            ],
            [36000, 38000, 42000],
            [36000, 38000, 42000],
        ),
        (
            [
                "Emissions|CO2|AFOLU",
                "Emissions|CO2|Energy and Industrial Processes",
            ],
            [
                "MtCO2 / yr",
                "MtCO2 / yr",
            ],
            [
                [33000, 38000, 44000],
                [3000, 0, -2000],
            ],
            [36000, 38000, 42000],
        ),
        # ensure no double counting
        (
            [
                "Emissions|CO2",
                "Emissions|CO2|AFOLU",
                "Emissions|CO2|Energy and Industrial Processes",
            ],
            [
                "MtCO2 / yr",
                "MtCO2 / yr",
                "MtCO2 / yr",
            ],
            [
                [36000, 38000, 42000],
                [33000, 38000, 44000],
                [3000, 0, -2000],
            ],
            [36000, 38000, 42000],
        ),
        (
            [
                "Emissions|CO2",
                "Emissions|CH4",
            ],
            [
                "MtCO2 / yr",
                "Mt CH4 / yr",
            ],
            [[36000, 38000, 42000], [300, 300, 300]],
            [36000 + 300 * 27.9, 38000 + 300 * 27.9, 42000 + 300 * 27.9],
        ),
        (
            [
                "Emissions|CO2|AFOLU",
                "Emissions|CO2|Energy and Industrial Processes",
                "Emissions|CH4",
            ],
            [
                "MtCO2 / yr",
                "MtCO2 / yr",
                "Mt CH4 / yr",
            ],
            [[33000, 38000, 44000], [3000, 0, -2000], [300, 300, 300]],
            [36000 + 300 * 27.9, 38000 + 300 * 27.9, 42000 + 300 * 27.9],
        ),
    ),
)
@pytest.mark.parametrize(
    "prefix", ["a", "b", "", "Harmonized", "Harmonized|", "Infilled|"]
)
def test_add_gwp100_kyoto(inp_variables, inp_units, inp_values, exp_values, prefix):
    """Check that `add_gwp100_kyoto()` calculates the GWP100 only with
    emissions variables, which are in the Kyoto gases list"""

    start = create_dataframe(
        scen_array=inp_values,
        unit_name=inp_units,
        var_name=[f"{prefix}{v}" for v in inp_variables],
        index=[2015, 2020, 2040],
        scen_name="test",
    )

    res = add_gwp100_kyoto_wrapper(start, prefixes=[prefix], gwps=["AR6GWP100"])

    np.testing.assert_allclose(
        res.filter(variable=f"{prefix}Emissions|Kyoto Gases (AR6-GWP100)")
        .timeseries()
        .values.squeeze(),
        exp_values,
    )


def test_add_gwp100_kyoto_multi_scenario():
    """Check that `add_gwp100_kyoto()` calculates the GWP100 only with
    emissions variables in multiple scenarios, which are in the Kyoto
    gases list"""

    scen = [SCEN_A, SCEN_B, SCEN_C]
    prefix = ""

    helper = create_dataframe_input(scen)

    start = create_dataframe(
        var_name=[prefix + s for s in helper["var_name"]],
        unit_name=helper["unit_name"],
        scen_array=helper["scen_array"],
        scen_name=helper["scen_name"],
    )

    var_name = "Emissions|Kyoto Gases (AR6-GWP100)"
    unit_name = "Mt CO2-equiv/yr"
    exp = create_dataframe(
        var_name=[var_name] * len(scen),
        unit_name=[unit_name] * len(scen),
        scen_array=helper["exp_scen_array"],
        scen_name=helper["exp_scen_name"],
    )

    res = add_gwp100_kyoto_wrapper(start, prefixes=[""], gwps=["AR6GWP100"])

    assert exp.equals(res.filter(variable="Emissions|Kyoto Gases (AR6-GWP100)"))


def test_add_gwp100_kyoto_ar5():
    """Check that AR5-GWP100 give expected results"""

    res = add_gwp100_kyoto_wrapper(
        create_dataframe(scen_array=[SCEN_A["total_co2"], SCEN_A["ch4"]]),
        prefixes=[""],
        gwps=["AR5GWP100"],
    )

    exp = create_dataframe(
        var_name=["Emissions|Kyoto Gases (AR5-GWP100)"],
        unit_name=["Mt CO2-equiv/yr"],
        scen_array=expected_scen(SCEN_A, CH4_GWP100_AR5),
        scen_name="scenario",
    )

    assert exp.equals(res.filter(variable="Emissions|Kyoto Gases (AR5-GWP100)"))


def test_add_gwp100_kyoto_ar4():
    """Check that `add_gwp100_kyoto()` raises expected error when giving a
    not implemented GWP in `add_gwp100_kyoto_wrapper()`"""

    with pytest.raises(NotImplementedError, match="AR4GWP100"):
        add_gwp100_kyoto_wrapper(
            create_dataframe(scen_array=[SCEN_A["total_co2"], SCEN_A["ch4"]]),
            prefixes=[""],
            gwps=["AR4GWP100"],
        )


def test_add_gwp100_kyoto_infilled(caplog):
    """Check that `add_gwp100_kyoto()` ignores emissions variables,
    which are not in the Kyoto gases list to calculate GWP100"""

    caplog.set_level(logging.INFO)
    prefix = "AR6 climate diagnostics|Infilled|"
    scen = [SCEN_D]

    helper = create_dataframe_input(scen)

    start = create_dataframe(
        var_name=[prefix + s for s in helper["var_name"]],
        unit_name=helper["unit_name"],
        scen_array=helper["scen_array"],
        scen_name=helper["scen_name"],
    )
    add_gwp100_kyoto_wrapper(start, prefixes=[prefix], gwps=["AR6GWP100"])

    assert (
        "The variables %sEmissions|BC, %sEmissions|CO, %sEmissions|CO2|AFOLU, "
        "%sEmissions|CO2|Energy and Industrial Processes, %sEmissions|NH3, "
        "%sEmissions|OC, %sEmissions|PFC, %sEmissions|Sulfur, %sEmissions|VOC "
        "are being ignored for the calculation of the GWP100."
    ), prefix in caplog.text


def test_add_gwp100_kyoto_harmonize(caplog):
    """Check that `add_gwp100_kyoto()` uses only emissions variables,
    which are in the Kyoto gases list to calculate GWP100"""

    caplog.set_level(logging.INFO)
    prefix = "AR6 climate diagnostics|Harmonized|"
    scen = [SCEN_C]

    helper = create_dataframe_input(scen)

    start = create_dataframe(
        var_name=[prefix + s for s in helper["var_name"]],
        unit_name=helper["unit_name"],
        scen_array=helper["scen_array"],
        scen_name=helper["scen_name"],
    )
    add_gwp100_kyoto_wrapper(start, prefixes=[prefix], gwps=["AR6GWP100"])

    assert (
        "The input doesn't have all the variables listed in Kyoto gases."
        " Only the variables %sEmissions|CH4, %sEmissions|CH4, "
        "%sEmissions|CO2, %sEmissions|CO2 are included in the "
        "calculation of the GWP100"
    ), prefix in caplog.text


def test_add_gwp100_kyoto_empty(caplog):
    """Check that `add_gwp100_kyoto()` logs a warning if no GWP100 was calculated
    expected error when not giving emission variables which are in the list of
    Kyoto gases"""

    caplog.set_level(logging.WARNING)
    start = create_dataframe(
        scen_array=[SCEN_D["hfc125"], SCEN_D["hfc134a"]],
        var_name=[EMISSIONS["hfc125"][0], EMISSIONS["hfc134a"][0]],
        unit_name=[EMISSIONS["hfc125"][1], EMISSIONS["hfc134a"][1]],
    )
    res = add_gwp100_kyoto_wrapper(
        start,
        prefixes=["AR6 climate diagnostics|Harmonized|"],
        gwps=["AR6GWP100"],
    )

    assert res == start
    assert (
        "No Kyoto gases found with prefix AR6 climate "
        f"diagnostics|Harmonized| for {start}" in caplog.text
    )
