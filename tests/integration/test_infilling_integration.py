import logging
import os.path

import numpy as np
import numpy.testing as npt
import pandas.testing as pdt
import pyam
import pytest
import scmdata

from climate_assessment.infilling import run_infilling

CO2_AFOLU = "CO2|AFOLU"
CO2_ENERGY = "CO2|Energy and Industrial Processes"
CO2_TOTAL = "CO2"


def _get_start(values, variables):
    start = scmdata.ScmRun(
        values,
        index=[2015, 2020, 2030, 2040, 2050, 2060, 2070, 2080, 2090, 2100],
        columns={
            "model": [
                "a_model",
            ],
            "variable": variables,
            "scenario": "a_scenario",
            "unit": "GtC / yr",
            "region": "World",
        },
    ).convert_unit("Mt CO2/yr")

    start = pyam.IamDataFrame(start.timeseries(time_axis="year"))

    return start


def _get_res(start, test_data_dir):
    return run_infilling(
        start,
        prefix="AR6 climate diagnostics",
        database_filepath=os.path.join(
            test_data_dir,
            "cmip6-ssps-workflow-emissions_infillerdatabase_until2100.csv",
        ),
    )


def _check_total_is_sum_of_energy_and_afolu(res):
    assert set(res.filter(variable=f"*Infilled*Emissions|{CO2_TOTAL}|*").variable) == {
        f"AR6 climate diagnostics|Infilled|Emissions|{CO2_ENERGY}",
        f"AR6 climate diagnostics|Infilled|Emissions|{CO2_AFOLU}",
    }

    co2_total_var = res.filter(variable=f"*Infilled*Emissions|{CO2_TOTAL}").variable[0]
    pdt.assert_frame_equal(
        res.aggregate(co2_total_var).data,
        res.filter(variable=f"*Infilled*Emissions|{CO2_TOTAL}").data,
        check_like=True,
    )


def _check_unchanged(res, variable):
    harmonized_val = res.filter(variable=f"*Harmonized*{variable}")
    infilled_val = res.filter(variable=f"*Infilled*{variable}")

    npt.assert_allclose(
        harmonized_val.data["value"].values,
        infilled_val.filter(year=harmonized_val.year).data["value"].values,
    )


def test_infilling_only_co2_energy(test_data_dir):
    # only CO2 energy reported --> infill AFOLU
    start = _get_start(
        np.array(
            [
                [9, 10, 10, 5, 0, 0, 0, 0, 0, 0],
            ]
        ).T,
        [f"AR6 climate diagnostics|Harmonized|Emissions|{CO2_ENERGY}"],
    )

    res, co2_inf_db, _ = _get_res(start, test_data_dir)

    assert not res.filter(variable=f"*Infilled*Emissions|{CO2_AFOLU}").empty
    assert not (
        res.filter(variable=f"*Infilled*Emissions|{CO2_AFOLU}").data["value"] == 0
    ).all()
    # total not there as not used by climate models i.e. not required
    assert res.filter(variable=f"*Infilled*Emissions|{CO2_TOTAL}").empty


def test_infilling_only_co2_afolu(test_data_dir):
    # only AFOLU reported --> should have already failed vetting, but check it explodes here
    start = _get_start(
        np.array(
            [
                [1, 2, 1, 0.5, 0, 0, 0, 0, 0, 0],
            ]
        ).T,
        [f"AR6 climate diagnostics|Harmonized|Emissions|{CO2_AFOLU}"],
    )

    with pytest.raises(ValueError, match="No infilling occured. Check input emissions"):
        _get_res(start, test_data_dir)


def test_infilling_only_co2_total(test_data_dir, caplog):
    caplog.set_level(logging.INFO)
    # only total CO2 reported --> infill CO2 energy then assume the rest is
    # AFOLU to preserve the total
    start = _get_start(
        np.array(
            [
                [9, 10, 10, 5, 0, 0, 0, 0, 0, 0],
            ]
        ).T,
        [f"AR6 climate diagnostics|Harmonized|Emissions|{CO2_TOTAL}"],
    )

    res, co2_inf_db, co2_total = _get_res(start, test_data_dir)

    assert not res.filter(variable=f"*Infilled*Emissions|{CO2_AFOLU}").empty
    assert not (
        res.filter(variable=f"*Infilled*Emissions|{CO2_AFOLU}").data["value"] == 0
    ).all()

    assert not res.filter(variable=f"*Infilled*Emissions|{CO2_ENERGY}").empty
    assert not (
        res.filter(variable=f"*Infilled*Emissions|{CO2_ENERGY}").data["value"] == 0
    ).all()

    # total dropped out because it's not used by climate models
    assert res.filter(variable=f"*Infilled*Emissions|{CO2_TOTAL}").empty

    _check_total_is_sum_of_energy_and_afolu(res.append(co2_total))


def test_infilling_co2_energy_and_afolu(test_data_dir, caplog):
    # CO2 energy and AFOLU reported --> no change
    start = _get_start(
        np.array(
            [
                [9, 10, 10, 5, 0, 0, 0, 0, 0, 0],
                [1, 1, 0.5, 0, -0.5, -1, -1, -1, -1, -1],
            ]
        ).T,
        [
            f"AR6 climate diagnostics|Harmonized|Emissions|{CO2_ENERGY}",
            f"AR6 climate diagnostics|Harmonized|Emissions|{CO2_AFOLU}",
        ],
    )

    res, co2_inf_db, _ = _get_res(start, test_data_dir)

    _check_unchanged(res, f"Emissions|{CO2_AFOLU}")
    _check_unchanged(res, f"Emissions|{CO2_ENERGY}")

    # Total not reported as not used by climate models and not in input
    assert res.filter(variable=f"*Infilled*Emissions|{CO2_TOTAL}").empty


def test_infilling_co2_energy_and_total(test_data_dir, caplog):
    # CO2 energy and total reported --> calculate AFOLU, no other change
    start = _get_start(
        np.array(
            [
                [9, 10, 10, 5, 0, 0, 0, 0, 0, 0],
                [10, 11, 11, 6, 1, 0.5, 0, 0, 0, 0],
            ]
        ).T,
        [
            f"AR6 climate diagnostics|Harmonized|Emissions|{CO2_ENERGY}",
            f"AR6 climate diagnostics|Harmonized|Emissions|{CO2_TOTAL}",
        ],
    )

    res, co2_inf_db, co2_total = _get_res(start, test_data_dir)

    _check_unchanged(res, f"Emissions|{CO2_ENERGY}")

    # Total not reported as not used by climate models and not in input
    assert res.filter(variable=f"*Infilled*Emissions|{CO2_TOTAL}").empty

    _check_total_is_sum_of_energy_and_afolu(res.append(co2_total))


def test_infilling_co2_afolu_and_total(test_data_dir, caplog):
    # CO2 afolu and total reported --> calculate energy, no other change
    start = _get_start(
        np.array(
            [
                [1, 1, 0.5, 0, -0.5, -1, -1, -1, -1, -1],
                [10, 11, 11, 6, 1, 0.5, 0, 0, 0, 0],
            ]
        ).T,
        [
            f"AR6 climate diagnostics|Harmonized|Emissions|{CO2_AFOLU}",
            f"AR6 climate diagnostics|Harmonized|Emissions|{CO2_TOTAL}",
        ],
    )

    res, co2_inf_db, co2_total = _get_res(start, test_data_dir)

    _check_unchanged(res, f"Emissions|{CO2_AFOLU}")

    # Total not reported as not used by climate models and not in input
    assert res.filter(variable=f"*Infilled*Emissions|{CO2_TOTAL}").empty

    _check_total_is_sum_of_energy_and_afolu(res.append(co2_total))


def test_infilling_multiple_timeseries(test_data_dir):
    # Scenario a is fine and nothing changes
    # We can infill afolu in scenario b
    # We can infill energy in scenario c
    co2 = f"AR6 climate diagnostics|Harmonized|Emissions|{CO2_TOTAL}"
    energy_ind = f"AR6 climate diagnostics|Harmonized|Emissions|{CO2_ENERGY}"
    afolu = f"AR6 climate diagnostics|Harmonized|Emissions|{CO2_AFOLU}"

    year = [2015, 2020, 2030, 2040, 2050, 2060, 2070, 2080, 2090, 2100]
    start = scmdata.ScmRun(
        np.array(
            [
                [15, 20, 10, 5, 0, 0, 0, 0, 0, 0],
                [0, -1, -1.5, -1.8, -2, -2, -2.3, -2.4, -2.7, -3],
                [15, 20, 10, 5, 0, 0, 0, 0, 0, 0],
                [15, 19, 8.5, 3.2, -2, -2, -2.3, -2.4, -2.7, -3],
                [0, -1, -1.5, -1.8, -2, -2, -2.3, -2.4, -2.7, -3],
                [15, 19, 8.5, 3.2, -2, -2, -2.3, -2.4, -2.7, -3],
            ]
        ).T,
        index=year,
        columns={
            "model": [
                "a_model",
                "a_model",
                "b_model",
                "b_model",
                "c_model",
                "c_model",
            ],
            "variable": [
                energy_ind,
                afolu,
                energy_ind,
                co2,
                afolu,
                co2,
            ],
            "scenario": "a_scenario",
            "unit": "Mt CO2/yr",
            "region": "World",
        },
    )

    start = pyam.IamDataFrame(start.timeseries(time_axis="year"))

    infilled, co2_inf_db, co2_total = _get_res(start, test_data_dir)

    _check_unchanged(infilled.filter(model=["a_model", "b_model"]), variable=CO2_ENERGY)
    _check_unchanged(infilled.filter(model=["a_model", "c_model"]), variable=CO2_AFOLU)
    _check_unchanged(
        infilled.append(co2_total).filter(model=["b_model", "c_model"]),
        variable=CO2_TOTAL,
    )

    npt.assert_allclose(
        infilled.filter(
            model="b_model", variable=afolu.replace("Harmonized", "Infilled"), year=year
        ).data["value"],
        [0, -1, -1.5, -1.8, -2, -2, -2.3, -2.4, -2.7, -3],
    )
    npt.assert_allclose(
        infilled.filter(
            model="c_model",
            variable=energy_ind.replace("Harmonized", "Infilled"),
            year=year,
        ).data["value"],
        [15, 20, 10, 5, 0, 0, 0, 0, 0, 0],
    )
