import os.path
import shutil
import traceback

import pandas as pd
import pandas.testing as pdt
from click.testing import CliRunner

import climate_assessment.cli


def check_output(output_dir, expected_output_dir, update_expected_files, rtol=1e-2):
    files = [
        "infilled.csv",
    ]

    for file in files:
        file_to_check = os.path.join(output_dir, file)
        file_expected = os.path.join(expected_output_dir, file)

        if update_expected_files:
            shutil.copyfile(file_to_check, file_expected)

        else:
            idx = ["Model", "Scenario", "Region", "Variable", "Unit"]
            res = pd.read_csv(file_to_check).set_index(idx)
            exp = pd.read_csv(file_expected).set_index(idx)

            pdt.assert_frame_equal(
                res.T,
                exp.T,
                check_like=True,
                obj=os.path.basename(file_to_check),
                rtol=rtol,
            )


def test_infilling(tmpdir, test_data_dir, update_expected_files):
    out_dir = str(tmpdir)

    input_file = os.path.join(
        test_data_dir, "ex2_harmonized_for_infilling_regression.csv"
    )

    runner = CliRunner()
    result = runner.invoke(
        climate_assessment.cli.infill,
        [
            input_file,
            out_dir,
        ],
    )

    assert result.exit_code == 0, (
        f"{traceback.print_exception(*result.exc_info)}\n\n{result.stdout}"
    )

    check_output(
        out_dir,
        os.path.join(test_data_dir, "infilling"),
        update_expected_files,
    )


def test_workflow_infilling(tmpdir, test_data_dir, update_expected_files):
    out_dir = str(tmpdir)

    emissions_id = "ex2"

    runner = CliRunner()
    result = runner.invoke(
        climate_assessment.cli.infill,
        [
            os.path.join(
                test_data_dir,
                "workflow-harmonization",
                "ex2_harmonized.csv",
            ),
            out_dir,
            "--infilling-database",
            os.path.join(
                test_data_dir,
                "cmip6-ssps-workflow-emissions_infillerdatabase_until2100.csv",
            ),
        ],
    )

    assert result.exit_code == 0, (
        f"{traceback.print_exception(*result.exc_info)}\n\n{result.stdout}"
    )

    check_output(
        out_dir,
        os.path.join(test_data_dir, "workflow-infilling-slimmed"),
        update_expected_files,
    )

    if not update_expected_files:
        idx = ["Model", "Scenario", "Variable", "Region", "Unit"]
        # output should be identical to what comes out of the workflow tests
        filename = "infilled.csv"
        here_res = pd.read_csv(os.path.join(out_dir, filename))
        # workflow output does not contain Kyoto summary in _harmonized_infilled file
        here_res = here_res[~here_res["Variable"].str.contains("Kyoto")].set_index(idx)

        workflow_filename = f"{emissions_id}_harmonized_infilled.csv"
        workflow_res = pd.read_csv(
            os.path.join(
                test_data_dir,
                "workflow-fair-slimmed",
                workflow_filename,
            )
        )
        compare = workflow_res.set_index(idx)
        compare = compare.reindex(here_res.index)

        pdt.assert_frame_equal(
            here_res, compare, rtol=1e-3, obj="Comparison with workflow output"
        )
