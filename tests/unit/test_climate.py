import re

import pytest

from climate_assessment.climate.post_process import check_hist_warming_period


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
