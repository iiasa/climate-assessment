import os.path
import traceback

import pandas.testing as pdt
import pyam
from click.testing import CliRunner

import climate_assessment.cli
from climate_assessment.checks import check_negatives


def test_example_small_infillerdatabase(tmpdir, test_data_dir):
    # TODO add bigger infillerdatabase that can be updated using GitHub Secrets

    out_dir = str(tmpdir)

    input_file = os.path.join(test_data_dir, "ex2.csv")

    runner = CliRunner()
    result = runner.invoke(
        climate_assessment.cli.create_infiller_database,
        [
            input_file,
            out_dir,
        ],
    )

    assert result.exit_code == 0, "{}\n\n{}".format(
        traceback.print_exception(*result.exc_info), result.stdout
    )

    df_infiller_database = pyam.IamDataFrame(
        os.path.join(out_dir, "ex2_infillerdatabase.csv")
    )

    # check whether vetting was successful and strict enough
    prefix = "AR6 climate diagnostics|Harmonized|"

    # no negatives in non-co2
    # TODO write test for check_negatives function
    df_infiller_database_checked = check_negatives(
        df=df_infiller_database, prefix=prefix
    )

    # co2 boundaries
    co2_criteria = [
        {f"{prefix}Emissions|CO2|Energy and Industrial Processes": {"up": 1.6e5}},
        {f"{prefix}Emissions|CO2|Energy and Industrial Processes": {"lo": -1e5}},
        {f"{prefix}Emissions|CO2|AFOLU": {"up": 1e6}},
        {f"{prefix}Emissions|CO2|AFOLU": {"lo": -1e5}},
    ]
    df_infiller_database_checked.exclude = False

    for criterion in co2_criteria:
        df_infiller_database_checked.validate(criteria=criterion, exclude_on_fail=True)
    # TODO: replace filter by something faster, working on the meta
    df_infiller_database_checked.filter(exclude=False, inplace=True)

    # other upper boundaries (loosely based on vetted AR6 scenarios)
    other_upperboundaries = [
        {f"{prefix}Emissions|BC": {"up": 1e2}},
        {f"{prefix}Emissions|CO": {"up": 5e3}},
        {f"{prefix}Emissions|CH4": {"up": 5e4}},
        # {f"{prefix}Emissions|F-Gases": {"up": 2.5e4}},
        # {f"{prefix}Emissions|HFC": {"up": 1e4}},
        {f"{prefix}Emissions|HFC|HFC125": {"up": 5e3}},
        {f"{prefix}Emissions|HFC|HFC134a": {"up": 5e3}},
        {f"{prefix}Emissions|HFC|HFC143a": {"up": 1e3}},
        {f"{prefix}Emissions|HFC|HFC227ea": {"up": 1e2}},
        {f"{prefix}Emissions|HFC|HFC23": {"up": 1e2}},
        {f"{prefix}Emissions|HFC|HFC32": {"up": 2e3}},
        {f"{prefix}Emissions|HFC|HFC43-10": {"up": 1e2}},
        {f"{prefix}Emissions|N2O": {"up": 1e5}},
        {f"{prefix}Emissions|NH3": {"up": 5e2}},
        {f"{prefix}Emissions|NOx": {"up": 5e2}},
        {f"{prefix}Emissions|OC": {"up": 1e2}},
        # {f"{prefix}Emissions|PFC": {"up": 5e2}},
        {f"{prefix}Emissions|PFC|C2F6": {"up": 1e2}},
        {f"{prefix}Emissions|PFC|C6F14": {"up": 1e1}},
        {f"{prefix}Emissions|PFC|CF4": {"up": 1e2}},
        {f"{prefix}Emissions|SF6": {"up": 1e2}},
        {f"{prefix}Emissions|Sulfur": {"up": 5e3}},
        {f"{prefix}Emissions|VOC": {"up": 5e4}},
    ]
    df_infiller_database_checked.exclude = False
    for criterion in other_upperboundaries:
        df_infiller_database_checked.validate(criteria=criterion, exclude_on_fail=True)
    # TODO: replace filter by something faster, working on the meta
    df_infiller_database_checked.filter(exclude=False, inplace=True)

    pdt.assert_frame_equal(
        df_infiller_database.timeseries(),
        df_infiller_database_checked.timeseries(),
        rtol=1e-3,
    )


# TODO write test that checks infilled GWP in base year
# TODO write test that checks whether infiller database has enough gases
