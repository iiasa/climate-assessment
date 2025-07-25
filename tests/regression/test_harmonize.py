import os.path
import shutil
import traceback

import pandas as pd
import pandas.testing as pdt
import pyam
from click.testing import CliRunner

import climate_assessment.cli
from climate_assessment.checks import check_negatives


def check_output(
    emms_id, output_dir, expected_output_dir, update_expected_files, rtol=1e-2
):
    suffixes = [
        "_checkedinput_lead.csv",
        "_excluded_scenarios_noCO2orCO2EnIPreported.csv",
        "_excluded_scenarios_unexpectednegatives.csv",
        "_excluded_variables_notallyears.csv",
        "_harmonized.csv",
    ]

    for suffix in suffixes:
        filename = f"{emms_id}{suffix}"

        file_to_check = os.path.join(output_dir, filename)
        file_expected = os.path.join(expected_output_dir, filename)

        if update_expected_files:
            shutil.copyfile(file_to_check, file_expected)

        else:
            res = pd.read_csv(file_to_check)
            exp = pd.read_csv(file_expected)

            pdt.assert_frame_equal(
                res,
                exp,
                check_like=True,
                obj=os.path.basename(file_to_check),
                rtol=rtol,
            )


def test_workflow_harmonization(tmpdir, test_data_dir, update_expected_files):
    out_dir = str(tmpdir)

    # standard test emissions scenarios file
    emissions_id = "ex2"

    runner = CliRunner()
    result = runner.invoke(
        climate_assessment.cli.harmonize,
        [
            os.path.join(test_data_dir, f"{emissions_id}.csv"),
            out_dir,
        ],
    )

    assert result.exit_code == 0, (
        f"{traceback.print_exception(*result.exc_info)}\n\n{result.stdout}"
    )

    check_output(
        emissions_id,
        out_dir,
        os.path.join(test_data_dir, "workflow-harmonization"),
        update_expected_files,
    )

    if not update_expected_files:
        # output should be identical to what comes out of the workflow tests
        idx = ["Model", "Scenario", "Region", "Variable", "Unit"]

        filename = f"{emissions_id}_harmonized.csv"
        here_res = pd.read_csv(os.path.join(out_dir, filename))
        # workflow output does not contain Kyoto summary in _harmonized file
        here_res = here_res[~here_res["Variable"].str.contains("Kyoto")].set_index(idx)

        workflow_filename = f"{emissions_id}_harmonized_infilled.csv"
        workflow_res = pd.read_csv(
            os.path.join(test_data_dir, "workflow-magicc", workflow_filename)
        )
        compare = workflow_res[
            workflow_res["Variable"].str.contains("Harmonized")
        ].set_index(idx)
        compare = compare.reindex(here_res.index)

        # general check
        pdt.assert_frame_equal(
            here_res, compare, obj="Comparison with workflow output", check_like=True
        )

        harmonization_year = "2015"
        assert not (here_res[harmonization_year] == 0).any()

        prefix = "AR6 climate diagnostics|Harmonized|"
        df_harmonized_checked = check_negatives(
            df=pyam.IamDataFrame(here_res.reset_index()), prefix=prefix
        )
        df_harmonized_checked = df_harmonized_checked.timeseries()
        df_harmonized_checked.index.names = [
            n.title() for n in df_harmonized_checked.index.names
        ]
        df_harmonized_checked.columns = df_harmonized_checked.columns.astype(str)

        pdt.assert_frame_equal(
            df_harmonized_checked,
            compare,
            obj="Comparison with workflow output after checking for negatives",
        )

    # also test with test data that only has data starting in 2015
    emissions_id_2015 = "ex2_starting2015"

    runner_2015 = CliRunner()
    result_2015 = runner_2015.invoke(
        climate_assessment.cli.harmonize,
        [
            os.path.join(test_data_dir, f"{emissions_id_2015}.csv"),
            out_dir,
        ],
    )

    assert result_2015.exit_code == 0, (
        f"{traceback.print_exception(*result_2015.exc_info)}\n\n{result_2015.stdout}"
    )


def test_workflow_harmonization_noinputchecks(
    tmpdir,
    test_data_dir,
):
    out_dir = str(tmpdir)

    emissions_id = "ex2"

    runner = CliRunner()
    result = runner.invoke(
        climate_assessment.cli.harmonize,
        [
            os.path.join(test_data_dir, f"{emissions_id}.csv"),
            out_dir,
            "--no-inputcheck",
        ],
    )

    assert result.exit_code == 0, (
        f"{traceback.print_exception(*result.exc_info)}\n\n{result.stdout}"
    )
