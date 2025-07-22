import numpy as np
import pandas as pd
import pyam
import pytest
from pyam import assert_iamframe_equal

from climate_assessment import utils

tdownscale_df = pyam.IamDataFrame(
    pd.DataFrame(
        [
            [
                "model_b",
                "scen_b",
                "World",
                "Emissions|HFC|C2F6",
                "Mt CO2-equiv/yr",
                1,
                2,
                3,
            ],
            [
                "model_b",
                "scen_c",
                "World",
                "Emissions|HFC|C2F6",
                "kt C2F6/yr",
                1,
                2,
                2,
            ],
        ],
        columns=[
            "model",
            "scenario",
            "region",
            "variable",
            "unit",
            2010,
            2015,
            2050,
        ],
    )
)


@pytest.mark.parametrize(
    "ARoption, expected", [("AR6GWP100", 12.4), ("AR5GWP100", 11.1)]
)
def test_convert_hfc_units(ARoption, expected):
    converted = utils.convert_co2_equiv_to_kt_gas(tdownscale_df, "*HFC*", ARoption)

    assert len(converted.variable) == 1
    assert all(
        converted.data[["variable", "unit"]].drop_duplicates()["unit"] == "kt C2F6/yr"
    )
    # We can numerically look up the values, this is 1 / the conversion factor for
    # C2F6 in AR6GWP100, divided by 1000 for the k -> G transform.
    assert np.isclose(converted.data["value"][0], 1 / expected)


def test_units_no_change():
    _msa = ["model_a", "scen_a"]
    tdb = pyam.IamDataFrame(
        pd.DataFrame(
            [
                _msa + ["World", "Emissions|CO2", "Mt CO2/yr", 1, 3.14],
                _msa + ["World", "Emissions|HFC|C2F6", "kt C2F6/yr", 1.2, 1.5],
            ],
            columns=["model", "scenario", "region", "variable", "unit", 2010, 2015],
        )
    )
    converted = utils.convert_co2_equiv_to_kt_gas(tdb, "*HFC*")
    # We expect this to be unchanged
    assert all(converted.data == tdb.data)


def test_units_multiple_values():
    _msa = ["model_a", "scen_a"]
    tdb = pyam.IamDataFrame(
        pd.DataFrame(
            [
                _msa + ["World", "Emissions|CO2", "Mt CO2-equiv/yr", 1, 3.14],
                _msa + ["World", "Emissions|HFC|C2F6", "Mt CO2-equiv/yr", 1.2, 1.5],
            ],
            columns=["model", "scenario", "region", "variable", "unit", 2010, 2015],
        )
    )
    converted = utils.convert_co2_equiv_to_kt_gas(tdb, "*HFC*")
    # We expect the first row to be unchanged
    assert all(converted.data.iloc[0] == tdb.data.iloc[0])
    assert all(
        converted.data[["variable", "unit"]].drop_duplicates().iloc[1]
        == ["Emissions|HFC|C2F6", "kt C2F6/yr"]
    )


@pytest.mark.parametrize(
    "ARoption,expected", [("AR5GWP100", 11.100), ("AR4GWP100", 12.200)]
)
def test_convert_units_to_MtCO2_equiv(ARoption, expected):
    converted_units = utils.convert_units_to_co2_equiv(tdownscale_df, ARoption)
    assert all(y[:6] == "Mt CO2" for y in converted_units.data["unit"].unique())
    # Data from scen_b is already in CO2
    assert_iamframe_equal(
        converted_units.filter(scenario="scen_b"),
        tdownscale_df.filter(scenario="scen_b"),
    )
    # Indexes after 3 are not
    assert np.allclose(
        converted_units.filter(scenario="scen_c").data["value"],
        tdownscale_df.filter(scenario="scen_c").data["value"] * expected,
    )
