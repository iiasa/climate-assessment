import numpy as np
import pandas as pd
import pyam
import pytest

from climate_assessment.checks import add_categorization

TEST_YEARS = [2015, 2050, 2100]
TEST_TIMESERIES = (
    # scenario name, expected category, expected category name,
    # p33 peak, p50 peak, p67 peak,
    # p33 timeseries, p50 timeseries, p67 timeseries
    (
        "Hot",
        "C8",
        "C8: Above 4.0°C",
        3.3,
        4.5,
        5.5,
        [1.0, 2.2, 3.1],
        [1.1, 3.0, 4.5],
        [1.2, 4.0, 5.6],
    ),
    (
        "Still hot",
        "C7",
        "C7: Below 4.0°C",
        2.3,
        3.5,
        4.5,
        [1.0, 1.7, 2.1],
        [1.1, 2.5, 3.5],
        [1.2, 3.5, 4.6],
    ),
    (
        "Yep still hot",
        "C6",
        "C6: Below 3.0°C",
        1.3,
        2.5,
        3.5,
        [1.0, 1.2, 1.1],
        [1.1, 2.0, 2.5],
        [1.2, 3.0, 3.6],
    ),
    (
        "Still too hot",
        "C5",
        "C5: Below 2.5°C",
        1.1,
        2.3,
        3.3,
        [1.0, 1.1, 1.1],
        [1.1, 1.8, 2.3],
        [1.2, 2.5, 3.3],
    ),
    (
        "Below 2 median",
        "C4",
        "C4: Below 2°C",
        1.2,
        1.98,
        2.6,
        [1.0, 1.3, 1.2],
        [1.1, 1.7, 1.8],
        [1.2, 2.2, 2.6],
    ),
    (
        "Below 2 2/3",
        "C3",
        "C3: Likely below 2°C",
        1.2,
        1.85,
        1.98,
        [1.0, 1.3, 1.2],
        [1.1, 1.7, 1.8],
        [1.15, 1.87, 1.93],
    ),
    (
        "Huge overshoot",
        "C2",
        "C2: Below 1.5°C with high OS",
        2.0,
        2.2,
        2.4,
        [1.0, 1.65, 1.2],
        [1.1, 1.85, 1.45],
        [1.15, 1.93, 1.55],
    ),
    (
        "1.5C high OS",
        "C2",
        "C2: Below 1.5°C with high OS",
        1.55,
        1.7,
        1.9,
        [1.0, 1.55, 1.2],
        [1.1, 1.7, 1.49],
        [1.15, 1.87, 1.61],
    ),
    (
        "1.5C low OS",
        "C1b",
        "C1b: Below 1.5°C with low OS",
        1.45,
        1.55,
        1.65,
        [1.0, 1.43, 1.2],
        [1.1, 1.54, 1.45],
        [1.15, 1.63, 1.48],
    ),
    (
        "Below 1.5C",
        "C1a",
        "C1a: Below 1.5°C with no OS",
        1.38,
        1.42,
        1.49,
        [1.0, 1.38, 1.2],
        [1.1, 1.42, 1.40],
        [1.15, 1.49, 1.47],
    ),
)


def _convert_test_input_to_input_for_add_categorization(test_input):
    (
        name,
        exp_category,
        exp_category_name,
        p33peak,
        p50peak,
        p67peak,
        p33ts,
        p50ts,
        p67ts,
    ) = test_input

    model_version = "1"
    prefix = "Prefix"
    climate_model = "MAGICC"

    df = pd.DataFrame(np.array([p33ts, p50ts, p67ts]), columns=TEST_YEARS)
    df["variable"] = [
        f"{prefix}|Surface Temperature (GSAT)|{climate_model}{model_version}|{p:.1f}th Percentile"
        for p in [33, 50, 67]
    ]

    # fake other variables
    for p in [5, 10, 17, 25]:
        copy = df.loc[df["variable"].str.contains("33.0"), :].copy()
        copy["variable"] = [
            f"{prefix}|Surface Temperature (GSAT)|{climate_model}{model_version}|{p:.1f}th Percentile"
        ]
        df = pd.concat([df, copy])

    for p in [66]:
        copy = df.loc[df["variable"].str.contains("50.0"), :].copy()
        copy["variable"] = [
            f"{prefix}|Surface Temperature (GSAT)|{climate_model}{model_version}|{p:.1f}th Percentile"
        ]
        df = pd.concat([df, copy])

    for p in [75, 83, 90, 95]:
        copy = df.loc[df["variable"].str.contains("67.0"), :].copy()
        copy["variable"] = [
            f"{prefix}|Surface Temperature (GSAT)|{climate_model}{model_version}|{p:.1f}th Percentile"
        ]
        df = pd.concat([df, copy])

    df["unit"] = "K"
    df["scenario"] = name
    df["model"] = "model"
    df["region"] = "World"

    df = pyam.IamDataFrame(df)
    df.set_meta(p33peak, f"p33 peak warming ({climate_model}{model_version})")
    df.set_meta(p50peak, f"median peak warming ({climate_model}{model_version})")
    df.set_meta(p67peak, f"p67 peak warming ({climate_model}{model_version})")

    return exp_category, exp_category_name, df, model_version, prefix, climate_model


def _check_single_res(res, exp_category, exp_category_name=None):
    assert res.meta.shape[0] == 1
    assert res.meta.loc[(res.model[0], res.scenario[0]), "Category"] == exp_category
    if exp_category_name is not None:
        assert (
            res.meta.loc[(res.model[0], res.scenario[0]), "Category_name"]
            == exp_category_name
        )


@pytest.mark.parametrize("test_input", TEST_TIMESERIES)
def test_categorisation(test_input):
    (
        exp_category,
        exp_category_name,
        inp,
        model_version,
        prefix,
        climate_model,
    ) = _convert_test_input_to_input_for_add_categorization(test_input)

    res = add_categorization(
        inp,
        model_version=model_version,
        prefix=prefix,
        model=climate_model,
    )

    _check_single_res(res, exp_category, exp_category_name)


@pytest.mark.parametrize(
    "boundary,equal_or_above_cat,below_cat",
    (
        (4.0, "C8", "C7"),
        (3.0, "C7", "C6"),
        (2.5, "C6", "C5"),
        (2.0, "C5", "C4"),
        # jumps straight to C4 because p67 warming is high and EoC warming
        # is high
        (1.5, "C4", "C1a"),
    ),
)
def test_boundaries(boundary, equal_or_above_cat, below_cat):
    for median_warming_val, exp_category in (
        (boundary + 0.01, equal_or_above_cat),
        (boundary, equal_or_above_cat),
        (boundary - 0.01, below_cat),
    ):
        test_input = (
            "Test input",
            exp_category,
            None,
            1.0,
            median_warming_val,  # only median peak warming is used
            10.0,  # set artifically high peak p67 to test median warming impact
            [1.0, 1.0, 1.0],
            [4.0, 4.0, median_warming_val],
            [10.0, 10.0, 10.0],
        )
        (
            exp_category,
            _,
            inp,
            model_version,
            prefix,
            climate_model,
        ) = _convert_test_input_to_input_for_add_categorization(test_input)

        res = add_categorization(
            inp,
            model_version=model_version,
            prefix=prefix,
            model=climate_model,
        )
        _check_single_res(res, exp_category)


def test_c4_c3_distinction():
    boundary = 2.0
    for p67_warming_val, exp_category in (
        (boundary + 0.01, "C4"),
        (boundary, "C4"),
        (boundary - 0.01, "C3"),
    ):
        test_input = (
            "Test input",
            exp_category,
            None,
            1.0,
            1.6,
            p67_warming_val,  # only p67 peak warming is used
            [1.0, 1.0, 1.0],
            [4.0, 4.0, 4.0],
            [10.0, 10.0, 10.0],
        )
        (
            exp_category,
            _,
            inp,
            model_version,
            prefix,
            climate_model,
        ) = _convert_test_input_to_input_for_add_categorization(test_input)

        res = add_categorization(
            inp,
            model_version=model_version,
            prefix=prefix,
            model=climate_model,
        )
        _check_single_res(res, exp_category)


@pytest.mark.parametrize(
    "test_input",
    (
        (
            "C2",
            "C2",
            "C2: Below 1.5°C with high OS",
            1.7,
            1.85,
            1.9,
            [1.0, 1.7, 1.3],
            [1.1, 1.85, 1.49],
            [1.2, 1.9, 1.6],
        ),
        (
            "C3 because end of century is equal to 1.5",
            "C3",
            "C3: Likely below 2°C",
            1.7,
            1.85,
            1.9,
            [1.0, 1.7, 1.3],
            [1.1, 1.85, 1.5],
            [1.2, 1.9, 1.6],
        ),
        (
            "C1b because p33 peak is less than 1.5",
            "C1b",
            "C1b: Below 1.5°C with low OS",
            1.49,
            1.85,
            1.9,
            [1.0, 1.7, 1.3],
            [1.1, 1.85, 1.49],
            [1.2, 1.9, 1.6],
        ),
        (
            "C3 because end of century is equal to 1.5 even though p33 peak is less than 1.5",
            "C3",
            "C3: Likely below 2°C",
            1.49,
            1.85,
            1.9,
            [1.0, 1.7, 1.3],
            [1.1, 1.85, 1.5],
            [1.2, 1.9, 1.6],
        ),
    ),
)
def test_c3_boundary(test_input):
    (
        exp_category,
        exp_category_name,
        inp,
        model_version,
        prefix,
        climate_model,
    ) = _convert_test_input_to_input_for_add_categorization(test_input)

    res = add_categorization(
        inp,
        model_version=model_version,
        prefix=prefix,
        model=climate_model,
    )

    _check_single_res(res, exp_category, exp_category_name)


@pytest.mark.parametrize(
    "test_input",
    (
        (
            "C1b",
            "C1b",
            "C1b: Below 1.5°C with low OS",
            1.5,
            1.55,
            1.65,
            [1.0, 1.48, 1.4],
            [1.1, 1.54, 1.49],
            [1.2, 1.6, 1.6],
        ),
        (
            "C1a because median peak < 1.5",
            "C1a",
            "C1a: Below 1.5°C with no OS",
            1.48,
            1.49,
            1.65,
            [1.0, 1.48, 1.4],
            [1.1, 1.49, 1.49],
            [1.2, 1.6, 1.6],
        ),
        (
            "C2 because p33 greater than 1.5",
            "C2",
            "C2: Below 1.5°C with high OS",
            1.51,
            1.55,
            1.65,
            [1.0, 1.48, 1.4],
            [1.1, 1.54, 1.49],
            [1.2, 1.6, 1.6],
        ),
        (
            "C3 because end of century median equals 1.5",
            "C3",
            "C3: Likely below 2°C",
            1.5,
            1.55,
            1.65,
            [1.0, 1.48, 1.4],
            [1.1, 1.54, 1.5],
            [1.2, 1.6, 1.6],
        ),
    ),
)
def test_c2_boundary(test_input):
    (
        exp_category,
        exp_category_name,
        inp,
        model_version,
        prefix,
        climate_model,
    ) = _convert_test_input_to_input_for_add_categorization(test_input)

    res = add_categorization(
        inp,
        model_version=model_version,
        prefix=prefix,
        model=climate_model,
    )

    _check_single_res(res, exp_category, exp_category_name)


def test_no_assessment():
    (
        _,
        _,
        inp,
        model_version,
        prefix,
        climate_model,
    ) = _convert_test_input_to_input_for_add_categorization(TEST_TIMESERIES[0])

    not_assessed_name = "Broke climate models"
    no_assessment = inp.timeseries().reset_index().iloc[:1, :]
    no_assessment["scenario"] = not_assessed_name
    no_assessment["variable"] = "Emissions|CO2|AFOLU"
    no_assessment["unit"] = "Mt CO2/yr"
    no_assessment = pyam.IamDataFrame(no_assessment)

    with pytest.raises(ValueError):
        # at the moment, this just explodes when we try to call timseeries on the empty dataframe
        add_categorization(
            no_assessment,
            model_version=model_version,
            prefix=prefix,
            model=climate_model,
        )

    # # check if we fix the error above
    # _check_single_res(res, "no-climate-assessment", "no-climate-assessment")


def test_multiple_categorisations():
    converted_inputs = [
        _convert_test_input_to_input_for_add_categorization(inp)
        for inp in TEST_TIMESERIES
    ]
    inp = pyam.concat([v[2] for v in converted_inputs])
    model_version = converted_inputs[0][-3]
    prefix = converted_inputs[0][-2]
    climate_model = converted_inputs[0][-1]

    not_assessed_name = "Broke climate models"
    no_assessment = inp.timeseries().reset_index().iloc[:1, :]
    no_assessment["scenario"] = not_assessed_name
    no_assessment["variable"] = "Emissions|CO2|AFOLU"
    no_assessment["unit"] = "Mt CO2/yr"
    inp = inp.append(no_assessment)

    res = add_categorization(
        inp,
        model_version=model_version,
        prefix=prefix,
        model=climate_model,
    )

    res_meta = res.meta.reset_index("model", drop=True)
    assert res_meta.shape[0] == len(converted_inputs) + 1

    assert res_meta.loc[not_assessed_name, "Category"] == "no-climate-assessment"
    assert res_meta.loc[not_assessed_name, "Category_name"] == "no-climate-assessment"
    for value in converted_inputs:
        scenario = value[2].scenario[0]
        exp_category = value[0]
        assert res_meta.loc[scenario, "Category"] == exp_category
        exp_category_name = value[1]
        assert res_meta.loc[scenario, "Category_name"] == exp_category_name
