import numpy as np
import pytest
import scmdata
import scmdata.testing

from climate_assessment.harmonization_and_infilling import run_harmonization
from climate_assessment.utils import columns_to_basic


@pytest.fixture(scope="module")
def ar6_harmonized(ar6_emissions):
    emissions = columns_to_basic(ar6_emissions)
    res = run_harmonization(emissions, instance="ar6", prefix="AR6 climate diagnostics")

    return scmdata.ScmRun(res.timeseries())


@pytest.fixture(scope="module")
def sr15_harmonized(sr15_emissions):
    emissions = columns_to_basic(sr15_emissions)
    res = run_harmonization(
        emissions, instance="sr15", prefix="SR15 climate diagnostics"
    )

    return scmdata.ScmRun(res.timeseries())


@pytest.mark.parametrize(
    "variable",
    [
        "Emissions|BC",
        "Emissions|CH4",
        "Emissions|CO",
        "Emissions|CO2",
        "Emissions|CO2|AFOLU",
        "Emissions|CO2|Energy and Industrial Processes",
        "Emissions|N2O",
        "Emissions|NH3",
        "Emissions|OC",
        "Emissions|SF6",
        "Emissions|Sulfur",
        # "Emissions|NOx",  # no NOx emissions in the input data
        "Emissions|VOC",
    ],
)
def test_harmonization_ar6(ar6_harmonized, rcmip_emissions, variable):
    harmonization_year = 2015
    harmonized_var = "AR6 climate diagnostics|Harmonized|" + variable

    assert harmonized_var in ar6_harmonized.get_unique_meta("variable")

    res_v = ar6_harmonized.filter(variable=harmonized_var, year=harmonization_year)
    rcmip_v = rcmip_emissions.filter(
        variable=variable, year=harmonization_year
    ).convert_unit(res_v.get_unique_meta("unit", True), context="NOx_conversions")

    np.testing.assert_allclose(rcmip_v.values, res_v.values, rtol=1e-3)


@pytest.mark.parametrize(
    "variable",
    [
        "Emissions|BC",
        "Emissions|CH4",
        "Emissions|CO",
        # "Emissions|CO2",  not reported for SR15
        "Emissions|CO2|AFOLU",
        "Emissions|CO2|Energy and Industrial Processes",
        "Emissions|N2O",
        "Emissions|NH3",
        "Emissions|OC",
        "Emissions|SF6",
        "Emissions|Sulfur",
        "Emissions|NOx",
        "Emissions|VOC",
    ],
)
def test_harmonization_sr15(sr15_harmonized, rcmip_emissions, variable):
    harmonization_year = 2010
    harmonized_var = "SR15 climate diagnostics|Harmonized|" + variable

    assert harmonized_var in sr15_harmonized.get_unique_meta("variable")

    res_v = sr15_harmonized.filter(variable=harmonized_var, year=harmonization_year)
    rcmip_v = rcmip_emissions.filter(
        variable=variable, year=harmonization_year
    ).convert_unit(res_v.get_unique_meta("unit", True), context="NOx_conversions")

    np.testing.assert_allclose(rcmip_v.values, res_v.values, rtol=1e-3)


def test_harmonization_ar6_no_2010(ar6_emissions, ar6_harmonized):
    # Test harmonisation works even if 2010 isn't in the inputs
    emissions = columns_to_basic(ar6_emissions.filter(year=2010, keep=False))
    res = run_harmonization(emissions, instance="ar6", prefix="AR6 climate diagnostics")

    scmdata.testing.assert_scmdf_almost_equal(res, ar6_harmonized, allow_unordered=True, check_ts_names=False)
