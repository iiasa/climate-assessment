import datetime as dt
import re

import numpy as np
import pandas as pd
import pytest
import scmdata

from climate_assessment.climate.post_process import check_hist_warming_period, post_process


@pytest.mark.parametrize(
    "inp,exp_out",
    (
        ("1995-2014", range(1995, 2014 + 1)),
        ("1995-2016", range(1995, 2016 + 1)),
        ("1850-2016", range(1850, 2016 + 1)),
        ("1850-1900", range(1850, 1900 + 1)),
        ("1850-1850", range(1850, 1850 + 1)),
    ),
)
def test_check_hist_warming_period(inp, exp_out):
    assert check_hist_warming_period(inp) == exp_out


@pytest.mark.parametrize(
    "inp",
    (
        "1995--2014",
        "199-2014",
        "2014-1995",
    ),
)
def test_check_hist_warming_period_malformed(inp):
    error_msg = re.escape(
        f"`period` must be a string of the form 'YYYY-YYYY' (with the first year "
        f"being less than or equal to the second), we received {inp}"
    )
    with pytest.raises(ValueError, match=error_msg):
        check_hist_warming_period(inp)


def _build_synthetic_climate_output(run_ids=(0, 1)):
    """Build minimal synthetic ScmRun data that passes through post_process."""
    years = list(range(1850, 2101))
    n_years = len(years)
    time_cols = [dt.datetime(y, 1, 1) for y in years]

    variables = [
        ("Surface Air Temperature Change", "K"),
        ("Surface Air Ocean Blended Temperature Change", "K"),
        ("Effective Radiative Forcing|Greenhouse Gases", "W/m^2"),
        ("Effective Radiative Forcing|Anthropogenic", "W/m^2"),
        ("Effective Radiative Forcing|CO2", "W/m^2"),
        ("Effective Radiative Forcing", "W/m^2"),
    ]

    rows = []
    for run_id in run_ids:
        for var, unit in variables:
            row = {
                "model": "test_model",
                "scenario": "test_scenario",
                "variable": var,
                "unit": unit,
                "region": "World",
                "climate_model": "FaIRv1.6.2",
                "run_id": run_id,
            }
            if "Temperature" in var:
                data = np.linspace(0, 1.5, n_years) + run_id * 0.1
            else:
                data = np.linspace(0, 3.0, n_years) + run_id * 0.05

            for i, t in enumerate(time_cols):
                row[t] = data[i]

            rows.append(row)

    return scmdata.ScmRun(pd.DataFrame(rows))


def test_post_process_return_all_runs(tmp_path):
    res_input = _build_synthetic_climate_output(run_ids=(0, 1))

    result = post_process(
        res_input,
        outdir=str(tmp_path),
        test_run=True,
        return_all_runs=True,
    )

    assert isinstance(result, tuple)
    assert len(result) == 3

    res, res_all_runs, meta_table = result

    # res_all_runs should be an ScmRun
    assert isinstance(res_all_runs, scmdata.ScmRun)

    # model names should encode run_id
    models = res_all_runs.get_unique_meta("model")
    assert all("|run_" in m for m in models)

    # variable names should encode climate model
    variables = res_all_runs.get_unique_meta("variable")
    assert all("|FaIRv1.6.2" in v for v in variables)

    # meta_table structure
    assert isinstance(meta_table, pd.DataFrame)
    assert "model" in meta_table.columns
    assert "scenario" in meta_table.columns
    assert not meta_table.duplicated(subset=["model", "scenario"]).any()
