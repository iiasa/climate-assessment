import os.path

import numpy as np
import pyam
import pytest
import scmdata

from climate_assessment.harmonization_and_infilling import harmonization_and_infilling

pytestmark = pytest.mark.nightly


def test_harmonize_and_infill_negative_co2_afolu_in_input(test_data_dir, tmpdir):
    # the trick is that there is a negative CO2 AFOLU in the input which is
    # less than the negativethreshold used in check_negatives, this value
    # shouldn't be rounded when checking for negatives in the infilled output
    # https://github.com/iiasa/climate-assessment/pull/200
    start = scmdata.ScmRun(
        np.array(
            [
                [10, 15, 20, 10, 5, 0, 0, 0, 0, 0, 0],
                [3500, 3517.44, 1600, 0.2, 0.1, 0, -0.1, -0.2, -0.3, -0.4, -0.5],
            ]
        ).T,
        index=[2010, 2015, 2020, 2030, 2040, 2050, 2060, 2070, 2080, 2090, 2100],
        columns={
            "model": "a_model",
            "scenario": "a_scenario",
            "variable": [
                "Emissions|CO2|Energy and Industrial Processes",
                "Emissions|CO2|AFOLU",
            ],
            "unit": ["GtC / yr", "MtCO2 / yr"],
            "region": "World",
        },
    ).convert_unit("Mt CO2/yr")
    start = pyam.IamDataFrame(start.timeseries(time_axis="year"))
    res = harmonization_and_infilling(
        start,
        key_string="test",
        infilling_database=os.path.join(
            test_data_dir,
            "cmip6-ssps-workflow-emissions.csv",
        ),
        prefix="AR6 climate diagnostics",
        instance="ar6",
        outdir=str(tmpdir),
        do_harmonization=True,
    )

    assert res, "Harmonization and infilling failed"

    res = scmdata.ScmRun(
        os.path.join(tmpdir, "test_harmonized_infilled.csv"), lowercase_cols=True
    )
    assert (
        res.filter(variable="*Harmonized*AFOLU", year=range(2051, 2060)).values < 0
    ).all(), "Some AFOLU values were rounded to zero"
