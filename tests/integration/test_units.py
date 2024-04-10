import os.path

import numpy.testing as npt
import pyam
import pytest
from openscm_units import unit_registry

from climate_assessment.checks import reclassify_waste_and_other_co2_ar6
from climate_assessment.utils import (
    convert_co2_equiv_to_kt_gas,
    convert_units_to_co2_equiv,
)

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "test-data")


@pytest.mark.parametrize(
    "start_unit,exp",
    (
        ("Mt CH4/yr", 28),
        ("Mt N2O/yr", 265),
        ("Mt C6F14/yr", 7910),
        ("Mt C7F16/yr", 7820),
    ),
)
def test_ar5gwp100(start_unit, exp):
    start = 1 * unit_registry(start_unit)
    with unit_registry.context("AR5GWP100"):
        res = start.to("Mt CO2/yr")

    npt.assert_equal(res.magnitude, exp)


@pytest.mark.parametrize(
    "start_unit,exp",
    (
        ("Mt CH4/yr", 27.9),
        ("Mt N2O/yr", 273),
        ("Mt C7F16/yr", 8410),
    ),
)
def test_ar6gwp100(start_unit, exp):
    start = 1 * unit_registry(start_unit)
    with unit_registry.context("AR6GWP100"):
        res = start.to("Mt CO2/yr")

    npt.assert_equal(res.magnitude, exp)


@pytest.fixture
def test_unit_conversion_df(test_starting_point_df):
    # check HFC4310 and CF4 too
    helper = test_starting_point_df.filter(variable="Emissions|HFC|HFC125").data
    helper["value"] *= 0.3
    helper["variable"] = "Emissions|HFC|HFC43-10"
    helper["unit"] = "kt HFC43-10/yr"

    helper_cf4 = test_starting_point_df.filter(variable="Emissions|PFC").data
    helper_cf4["value"] *= 0.5
    helper_cf4["variable"] = "Emissions|PFC|CF4"
    helper_cf4["unit"] = "kt CF4/yr"

    out = test_starting_point_df.append(helper).append(helper_cf4)

    return out


metric_conversion_checks = pytest.mark.parametrize(
    "metric,conversions",
    (
        (
            "AR6GWP100",
            {
                "*CH4": 27.9,
                # original units are kt N2O / yr
                "*N2O": 273 / 1000,
                # original units are kt SF6 / yr
                "*SF6": 25200 / 1000,
                # original units are kt HFC125 / yr
                "*HFC125": 3740 / 1000,
                # original units are kt HFC4310 / yr
                "*HFC43-10": 1600 / 1000,
                # original units are kt CF4 / yr
                "*CF4": 7380 / 1000,
            },
        ),
        (
            "AR5GWP100",
            {
                "*CH4": 28,
                # original units are kt N2O / yr
                "*N2O": 265 / 1000,
                # original units are kt SF6 / yr
                "*SF6": 23500 / 1000,
                # original units are kt HFC125 / yr
                "*HFC125": 3170 / 1000,
                # original units are kt HFC4310 / yr
                "*HFC43-10": 1650 / 1000,
                # original units are kt CF4 / yr
                "*CF4": 6630 / 1000,
            },
        ),
    ),
)


@metric_conversion_checks
def test_convert_scenarios(test_unit_conversion_df, metric, conversions):
    res = convert_units_to_co2_equiv(
        test_unit_conversion_df.filter(
            variable=[
                "Emissions|CO2",
                "Emissions|CH4",
                "Emissions|N2O",
                "Emissions|F-Gases",
                "Emissions|PFC|*",
                "Emissions|HFC*",
                "Emissions|SF6",
            ]
        ),
        metric,
    )

    for var_filter, conv_factor in conversions.items():
        npt.assert_allclose(
            res.filter(variable=var_filter).data["value"],
            test_unit_conversion_df.filter(variable=var_filter).data["value"]
            * conv_factor,
            err_msg=f"{metric} {var_filter}",
        )

    assert (res.data["unit"] == "Mt CO2-equiv/yr").all()


@metric_conversion_checks
@pytest.mark.parametrize(
    "var_filter",
    (
        "*HFC|*",
        "*PFC|*",
        ["*PFC|*"],
        ["*HFC|*", "*PFC|*"],
        ["*HFC|*", "*N2O"],
        ["*HFC|*", "*PFC|*", "*N2O"],
    ),
)
def test_convert_co2_equiv_to_kt_gas(
    test_unit_conversion_df, metric, var_filter, conversions
):
    co2_equiv = convert_units_to_co2_equiv(
        test_unit_conversion_df.filter(
            variable=[
                "Emissions|CO2",
                "Emissions|CH4",
                "Emissions|N2O",
                "Emissions|F-Gases",
                "Emissions|PFC|*",
                "Emissions|HFC*",
                "Emissions|SF6",
            ]
        ),
        metric,
    )

    res = convert_co2_equiv_to_kt_gas(co2_equiv, var_filter, metric=metric)

    not_converted = res.filter(variable=var_filter, keep=False)
    assert pyam.compare(
        not_converted, co2_equiv.filter(variable=var_filter, keep=False)
    ).empty

    converted = res.filter(variable=var_filter)
    for vf, conv_factor in conversions.items():
        converted_v = converted.filter(variable=vf)
        if converted_v.empty:
            # variable not in those which were converted
            continue

        npt.assert_allclose(
            res.filter(variable=vf).data["value"],
            co2_equiv.filter(variable=vf).data["value"] / conv_factor,
            err_msg=f"{metric} {vf}",
        )


def test_reclassify_co2_ar6():
    input_emissions_file = os.path.join(TEST_DATA_DIR, "ex2.csv")
    processed_input_emissions_file = os.path.join(
        TEST_DATA_DIR, "ex2_adjusted-waste-other.csv"
    )
    # import pdb
    # pdb.set_trace()
    # pyam.compare(reclassify_waste_and_other_co2_ar6(pyam.IamDataFrame(input_emissions_file)), pyam.IamDataFrame(processed_input_emissions_file), )
    assert reclassify_waste_and_other_co2_ar6(
        pyam.IamDataFrame(input_emissions_file)
    ).equals(pyam.IamDataFrame(processed_input_emissions_file))


def test_reclassify_co2_ar6_sum():
    input_emissions_file = pyam.IamDataFrame(os.path.join(TEST_DATA_DIR, "ex2.csv"))

    input_emissions_file_processed = reclassify_waste_and_other_co2_ar6(
        input_emissions_file
    )

    yrs_check = list(range(2020, 2101, 10))
    model_name = "model12"
    scenario_name = "1point5"
    for yr in yrs_check:
        original_eni_oth_waste = (
            input_emissions_file.filter(
                model=model_name,
                scenario=scenario_name,
                variable=[
                    "Emissions|CO2|Energy and Industrial Processes",
                    "Emissions|CO2|Waste",
                    "Emissions|CO2|Other",
                ],
                year=yr,
            )
            .as_pandas()
            .value.sum()
        )
        new_eni = (
            input_emissions_file_processed.filter(
                model=model_name,
                scenario=scenario_name,
                variable=["Emissions|CO2|Energy and Industrial Processes"],
                year=yr,
            )
            .as_pandas()
            .value.sum()
        )

        npt.assert_allclose(original_eni_oth_waste, new_eni)
