import logging
import os.path

import numpy as np
import pandas.testing as pdt
import pyam
import pytest
import scmdata

from climate_assessment.checks import (
    add_completeness_category,
    check_reported_co2,
    perform_input_checks,
    sanity_check_bounds_kyoto_emissions,
    sanity_check_comparison_kyoto_gases,
    sanity_check_hierarchy,
)


def test_add_completeness_category():
    """Check that `add_completeness_category` does not remove any scenarios"""
    input_idf = pyam.IamDataFrame(
        os.path.join(os.path.dirname(__file__), "..", "test-data", "ex2.csv")
    )

    df_with_completeness_meta_column = add_completeness_category(df=input_idf)

    assert len(input_idf) == len(df_with_completeness_meta_column)


def test_perform_input_checks_negative_kyoto():
    start = scmdata.ScmRun(
        np.array(
            [
                [10, 15, 20, 10, 5, 0, 0, 0, 0, 0, 0],
                [1, 0, -1, -1.5, -1.8, -2, -2, -2.3, -2.4, -2.7, -3],
                [11, 15, 19, 8.5, 3.2, -2, -2, -2.3, -2.4, -2.7, -3],
                [240, 238, 236, 234, 232, 230, 228, 226, 224, 222, 220],
            ]
        ).T,
        index=[2010, 2015, 2020, 2030, 2040, 2050, 2060, 2070, 2080, 2090, 2100],
        columns={
            "model": "a_model",
            "scenario": "a_scenario",
            "variable": [
                "Emissions|CO2|Energy and Industrial",
                "Emissions|CO2|AFOLU",
                "Emissions|Kyoto Gases",
                "Emissions|VOC",
            ],
            "unit": ["GtC / yr", "GtC / yr", "GtC / yr", "Mt VOC/yr"],
            "region": "World",
        },
    ).convert_unit("Mt CO2/yr", variable=["*CO2*", "*Kyoto*"])
    start = pyam.IamDataFrame(start.timeseries(time_axis="year"))
    res = perform_input_checks(start)

    assert pyam.compare(res, start).empty


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


def _check_total_is_sum_of_energy_and_afolu(res):
    assert set(res.filter(variable=f"*Infilled*Emissions|{CO2_TOTAL}|*").variable) == {
        f"p|Infilled|Emissions|{CO2_ENERGY}",
        f"p|Infilled|Emissions|{CO2_AFOLU}",
    }

    co2_total_var = res.filter(variable=f"*Infilled*Emissions|{CO2_TOTAL}").variable[0]
    pdt.assert_frame_equal(
        res.aggregate(co2_total_var).data,
        res.filter(variable=f"*Infilled*Emissions|{CO2_TOTAL}").data,
        check_like=True,
    )


def _check_expected_log_message(
    exp_message, caplog, level=logging.INFO, name="climate_assessment.checks"
):
    found_msg = False
    for t in caplog.record_tuples:
        if exp_message in t[-1]:
            assert t[0] == name
            assert t[1] == level
            found_msg = True

    assert found_msg


def test_check_reported_co2_only_afolu(caplog):
    # only AFOLU reported --> fails vetting
    caplog.set_level(logging.INFO)
    start = _get_start(
        np.array(
            [
                [15, 20, 10, 5, 0, 0, 0, 0, 0, 0],
            ]
        ).T,
        [f"Emissions|{CO2_AFOLU}"],
    )

    res = check_reported_co2(start, "test")

    assert res.empty
    exp_message = (
        "No Emissions|CO2 or Emissions|CO2|Energy and Industrial Processes "
        "found in scenario a_scenario produced by a_model"
    )

    _check_expected_log_message(exp_message, caplog)


def test_check_reported_co2_only_energy(caplog):
    # only energy reported --> all fine
    caplog.set_level(logging.INFO)
    start = _get_start(
        np.array(
            [
                [15, 20, 10, 5, 0, 0, 0, 0, 0, 0],
            ]
        ).T,
        [f"Emissions|{CO2_ENERGY}"],
    )

    res = check_reported_co2(start, "test")

    pdt.assert_frame_equal(res.data, start.data, check_like=True)


def test_check_reported_co2_only_total(caplog):
    # only total reported --> all fine
    caplog.set_level(logging.INFO)
    start = _get_start(
        np.array(
            [
                [15, 20, 10, 5, 0, 0, 0, 0, 0, 0],
            ]
        ).T,
        [f"Emissions|{CO2_TOTAL}"],
    )

    res = check_reported_co2(start, "test")

    pdt.assert_frame_equal(res.data, start.data, check_like=True)


def test_check_reported_co2_total_and_energy(caplog):
    # CO2 total and energy reported with sensible difference -->
    # do nothing
    caplog.set_level(logging.INFO)

    start = _get_start(
        np.array(
            [
                [15, 20, 10, 5, 0, 0, 0, 0, 0, 0],
                [14, 19, 9, 5, 1, 1, 1, 1, 1, 1],
            ]
        ).T,
        [
            f"Emissions|{CO2_TOTAL}",
            f"Emissions|{CO2_ENERGY}",
        ],
    )

    res = check_reported_co2(start, "test")

    pdt.assert_frame_equal(res.data, start.data, check_like=True)


def test_check_reported_co2_total_and_energy_no_difference(caplog):
    # CO2 total and energy reported with no difference -->
    # get rid of total CO2
    caplog.set_level(logging.INFO)

    start = _get_start(
        np.array(
            [
                [15, 20, 10, 5, 0, 0, 0, 0, 0, 0],
                [15, 20, 10, 5, 0, 0, 0, 0, 0, 0],
            ]
        ).T,
        [
            f"Emissions|{CO2_TOTAL}",
            f"Emissions|{CO2_ENERGY}",
        ],
    )

    res = check_reported_co2(start, "test")

    assert res.variable == [f"Emissions|{CO2_ENERGY}"]
    assert res.filter(variable=f"Emissions|{CO2_TOTAL}").empty

    exp_message = (
        "Emissions|CO2 is the same as "
        "Emissions|CO2|Energy and Industrial Processes for scenario "
        "`a_scenario` produced by `a_model` hence is removed"
    )

    _check_expected_log_message(exp_message, caplog)


def test_check_reported_co2_total_and_afolu(caplog):
    # CO2 total and afolu reported with sensible difference -->
    # do nothing
    caplog.set_level(logging.INFO)

    start = _get_start(
        np.array(
            [
                [15, 20, 10, 5, 0, 0, 0, 0, 0, 0],
                [1, 1, 0.5, 0, -1, -1, -1, -1, -1, -1],
            ]
        ).T,
        [
            f"Emissions|{CO2_TOTAL}",
            f"Emissions|{CO2_AFOLU}",
        ],
    )

    res = check_reported_co2(start, "test")

    pdt.assert_frame_equal(res.data, start.data, check_like=True)


def test_check_reported_co2_total_and_afolu_no_difference(caplog):
    # CO2 total and afolu reported with no difference -->
    # get rid of total CO2
    caplog.set_level(logging.INFO)

    start = _get_start(
        np.array(
            [
                [1, 1, 0.5, 0, -1, -1, -1, -1, -1, -1],
                [1, 1, 0.5, 0, -1, -1, -1, -1, -1, -1],
            ]
        ).T,
        [
            f"Emissions|{CO2_TOTAL}",
            f"Emissions|{CO2_AFOLU}",
        ],
    )

    res = check_reported_co2(start, "test")

    # Only CO2 AFOLU is left so the scenario is removed entirely
    assert res.empty

    exp_message = (
        "Emissions|CO2 is the same as "
        "Emissions|CO2|AFOLU for scenario "
        "`a_scenario` produced by `a_model` hence is removed"
    )

    _check_expected_log_message(exp_message, caplog)


def test_check_reported_co2_total_energy_and_afolu(caplog):
    # CO2 total, energy and afolu reported -->
    # drop total to avoid possible inconsistency resulting from harmonizing
    # total, energy and afolu separately
    caplog.set_level(logging.INFO)

    start = _get_start(
        np.array(
            [
                [15, 20, 10, 5, 0, 0, 0, 0, 0, 0],
                [14, 19, 9, 5, 1, 1, 1, 1, 1, 1],
                [1, 1, 1, 0, -1, -1, -1, -1, -1, -1],
            ]
        ).T,
        [
            f"Emissions|{CO2_TOTAL}",
            f"Emissions|{CO2_ENERGY}",
            f"Emissions|{CO2_AFOLU}",
        ],
    )

    res = check_reported_co2(start, "test")

    assert res.filter(variable=f"Emissions|{CO2_TOTAL}").empty

    exp_message = (
        "Emissions|CO2 is provided in addition to "
        "Emissions|CO2|Energy and Industrial Processes and "
        "Emissions|CO2|AFOLU for scenario "
        "`a_scenario` produced by `a_model` hence is removed to "
        "avoid any potential inconsistencies being introduced "
        "during harmonization"
    )

    _check_expected_log_message(exp_message, caplog)

    pdt.assert_frame_equal(
        res.data,
        start.filter(variable=f"Emissions|{CO2_TOTAL}", keep=False).data,
        check_like=True,
    )


def test_sanity_check_bounds_kyoto_emissions():
    """Check that `sanity_check_bounds_kyoto_emissions` raises an error if the
    emissions are out of bound"""

    out_kyoto_infilled = (
        "AR6 climate diagnostics|Infilled|Emissions|Kyoto Gases (AR5-GWP100)"
    )
    # Let first bounds in year 2015 fail and afterwards in year 2020
    bound_values = {"fail_2015": [13, 17, 2015], "fail_2020": [14, 16, 2020]}
    for val in bound_values:
        # Check lower boundary
        start_lower = _get_start(
            np.array(
                [
                    [bound_values[val][0], 12, 15, 15, 15, 14, 15, 15, 15, 15],
                ]
            ).T,
            [
                out_kyoto_infilled,
            ],
        )
        match_lower = (
            r"The Kyoto gases of the infilled emissions data of "
            r"\[\('a_model', 'a_scenario', 'World', 'AR6 climate "
            r"diagnostics\|Infilled\|Emissions\|Kyoto Gases \(AR5-GWP100\)', "
            rf"'Mt CO2/yr', {bound_values[val][2]}\)\] is/are too small."
        )
        with pytest.raises(ValueError, match=match_lower):
            sanity_check_bounds_kyoto_emissions(
                start_lower, out_kyoto_infilled=out_kyoto_infilled
            )
        # Check upper boundary
        start_upper = _get_start(
            np.array(
                [
                    [bound_values[val][1], 20, 15, 15, 15, 14, 15, 15, 15, 15],
                ]
            ).T,
            [
                "AR6 climate diagnostics|Infilled|Emissions|Kyoto Gases (AR5-GWP100)",
            ],
        )
        match_upper = (
            r"The Kyoto gases of infilled emissions data of \[\('a_model', "
            r"'a_scenario', 'World', 'AR6 climate diagnostics\|Infilled\|"
            r"Emissions\|Kyoto Gases \(AR5-GWP100\)', 'Mt CO2/yr', "
            rf"{bound_values[val][2]}\)\] is/are too big."
        )
        with pytest.raises(ValueError, match=match_upper):
            sanity_check_bounds_kyoto_emissions(
                start_upper, out_kyoto_infilled=out_kyoto_infilled
            )


def test_sanity_check_bounds_kyoto_emissions_multi_fail():
    """Check that `sanity_check_bounds_kyoto_emissions` raises the correct error when the
    emissions of multiple scenarios are out of bound"""

    out_kyoto_infilled_ar5 = (
        "AR6 climate diagnostics|Infilled|Emissions|Kyoto Gases (AR5-GWP100)"
    )
    out_kyoto_infilled_ar6 = (
        "AR6 climate diagnostics|Infilled|Emissions|Kyoto Gases (AR6-GWP100)"
    )
    # Let first both models in year 2015 fail and afterwards only second model in year 2015
    bound_values = {"fail_fail": [13, 20, 13, 20], "pass_fail": [14, 16, 13, 20]}
    for val in bound_values:
        start_lower = _get_start(
            np.array(
                [
                    [bound_values[val][0], 12, 15, 15, 15, 14, 15, 15, 15, 15],
                    [bound_values[val][2], 12, 15, 15, 15, 14, 15, 15, 15, 15],
                ]
            ).T,
            [
                out_kyoto_infilled_ar5,
                out_kyoto_infilled_ar6,
            ],
        )
        match_lower = (
            r"The Kyoto gases of the infilled emissions data of \[\('a_model',"
            r" 'a_scenario', 'World', 'AR6 climate diagnostics\|Infilled\|Emissions\|"
            r"Kyoto Gases \(AR5-GWP100\)', 'Mt CO2/yr', 2015\), \('a_model', "
            r"'a_scenario', 'World', 'AR6 climate diagnostics\|Infilled\|Emissions\|"
            r"Kyoto Gases \(AR6-GWP100\)', 'Mt CO2/yr', 2015\)\] is/are too small."
        )
        if val == "pass_fail":
            match_lower = (
                r"The Kyoto gases of the infilled emissions data of \[\('a_model', "
                r"'a_scenario', 'World', 'AR6 climate diagnostics\|Infilled\|"
                r"Emissions|Kyoto Gases \(AR6-GWP100\)', 'Mt CO2/yr', 2015\)\] "
                r"is/are too small."
            )
        with pytest.raises(ValueError, match=match_lower):
            sanity_check_bounds_kyoto_emissions(
                start_lower,
                out_kyoto_infilled="AR6 climate diagnostics|Infilled|Emissions|Kyoto Gases",
            )
        start_upper = _get_start(
            np.array(
                [
                    [bound_values[val][1], 20, 15, 15, 15, 14, 15, 15, 15, 15],
                    [bound_values[val][3], 20, 15, 15, 15, 14, 15, 15, 15, 15],
                ]
            ).T,
            [
                out_kyoto_infilled_ar5,
                out_kyoto_infilled_ar6,
            ],
        )
        match_upper = (
            r"The Kyoto gases of infilled emissions data of \[\('a_model', "
            r"'a_scenario', 'World', 'AR6 climate diagnostics\|Infilled\|"
            r"Emissions\|Kyoto Gases \(AR5-GWP100\)', 'Mt CO2/yr', 2015\), "
            r"\('a_model', 'a_scenario', 'World', 'AR6 climate diagnostics\|"
            r"Infilled\|Emissions\|Kyoto Gases \(AR6-GWP100\)', 'Mt CO2/yr', "
            r"2015\)\] is/are too big."
        )
        if val == "pass_fail":
            match_upper = (
                r"The Kyoto gases of infilled emissions data of \[\('a_model', "
                r"'a_scenario', 'World', 'AR6 climate diagnostics\|Infilled\|"
                r"Emissions\|Kyoto Gases \(AR6-GWP100\)', 'Mt CO2/yr', 2015\)\] "
                r"is/are too big."
            )
        with pytest.raises(ValueError, match=match_upper):
            sanity_check_bounds_kyoto_emissions(
                start_upper,
                out_kyoto_infilled="AR6 climate diagnostics|Infilled|Emissions|Kyoto Gases",
            )


def test_sanity_check_comparison_kyoto_gases():
    """Check that `sanity_check_comparison_kyoto_gases` raises an error if the calculated
    Kyoto gases of the infilled emissions data is not in every year smaller
    than the calculated Kyoto gases of the harmonized emission data"""

    out_kyoto_harmonized = (
        "AR6 climate diagnostics|Harmonized|Emissions|Kyoto Gases (AR5-GWP100)"
    )
    out_kyoto_infilled = (
        "AR6 climate diagnostics|Infilled|Emissions|Kyoto Gases (AR5-GWP100)"
    )
    start = _get_start(
        np.array(
            [
                [15, 15, 15, 15, 15, 15, 15, 15, 15, 15],
                [10, 20, 20, 20, 20, 20, 20, 20, 20, 20],
            ]
        ).T,
        [
            out_kyoto_harmonized,
            out_kyoto_infilled,
        ],
    )
    match_upper = (
        r"The Kyoto gases of infilled emissions data of \[\('a_model', "
        r"'a_scenario', 'World', 'AR6 climate diagnostics\|Infilled\|"
        r"Emissions\|Kyoto Gases \(AR5-GWP100\)', 'Mt CO2/yr', 2015\)\] "
        r"are smaller then the Kyoto gases of harmonized emissions"
    )
    with pytest.raises(ValueError, match=match_upper):
        sanity_check_comparison_kyoto_gases(
            start,
            out_kyoto_harmonized=out_kyoto_harmonized,
            out_kyoto_infilled=out_kyoto_infilled,
        )


def test_sanity_check_hierarchy():
    """Check that `sanity_check_hierarchy` raises an error if the
    hierarchy of variables is internally inconsistent (If
    Emissions|CO2 is not the sum of AFOLU and Energy emissions)"""

    prefix = {"Harmonized": [2, 1], "Infilled": [1, 2]}
    out_afolu = "Emissions|CO2|AFOLU"
    out_fossil = "Emissions|CO2|Energy and Industrial Processes"
    co2_inf = "Emissions|CO2"
    co2_infilling = _get_start(
        np.array(
            [
                [3, 3, 3, 3, 3, 3, 3, 3, 3, 3],
            ]
        ).T,
        [
            co2_inf,
        ],
    )
    harm_inf = []
    for key, value in prefix.items():
        for val in value:
            _out_afolu = f"AR6 climate diagnostics|{key}|{out_afolu}"
            _out_fossil = f"AR6 climate diagnostics|{key}|{out_fossil}"
            start = _get_start(
                np.array(
                    [
                        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                        [2 * val, 2, 2, 2, 2, 2, 2, 2, 2, 2],
                    ]
                ).T,
                [
                    _out_afolu,
                    _out_fossil,
                ],
            )
            harm_inf.append(start)

    match = (
        r"The sum of AFOLU and Energy and Industrial "
        r"Processes is not equal to Harmonized\|Emissions\|CO2"
    )
    with pytest.raises(ValueError, match=match):
        sanity_check_hierarchy(
            co2_infilling,
            harm_inf[0],
            harm_inf[2],
            out_afolu=out_afolu,
            out_fossil=out_fossil,
        )

    match = (
        r"The sum of AFOLU and Energy and Industrial "
        r"Processes is not equal to Infilled\|Emissions\|CO2"
    )
    with pytest.raises(ValueError, match=match):
        sanity_check_hierarchy(
            co2_infilling,
            harm_inf[1],
            harm_inf[3],
            out_afolu=out_afolu,
            out_fossil=out_fossil,
        )
