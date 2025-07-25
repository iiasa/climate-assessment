import os.path
import shutil
import traceback

import pandas as pd
import pandas.testing as pdt
from click.testing import CliRunner

import climate_assessment.cli


def check_output(emms_id, output_dir, expected_output_dir, update_expected_files):
    suffixes = [
        "_checkedinput_lead.csv",
        "_excluded_scenarios_noCO2orCO2EnIPreported.csv",
        "_excluded_scenarios_unexpectednegatives.csv",
        "_excluded_variables_notallyears.csv",
        "_harmonized_infilled.csv",
    ]

    for suffix in suffixes:
        filename = f"{emms_id}{suffix}"

        file_to_check = os.path.join(output_dir, filename)
        file_expected = os.path.join(expected_output_dir, filename)

        if update_expected_files:
            shutil.copyfile(file_to_check, file_expected)

        else:
            idx = ["Model", "Scenario", "Region", "Variable", "Unit"]
            res = pd.read_csv(file_to_check).set_index(idx)
            exp = pd.read_csv(file_expected).set_index(idx)

            pdt.assert_frame_equal(
                res.T, exp.T, check_like=True, obj=os.path.basename(file_to_check)
            )


def test_workflow_harmonization_and_infilling(
    tmpdir, test_data_dir, update_expected_files
):
    out_dir = str(tmpdir)

    emissions_id = "ex2"

    runner = CliRunner()
    result = runner.invoke(
        climate_assessment.cli.harmonize_and_infill,
        [
            os.path.join(test_data_dir, f"{emissions_id}.csv"),
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
        emissions_id,
        out_dir,
        os.path.join(
            test_data_dir,
            "workflow-harmonization-and-infilling-slimmed",
        ),
        update_expected_files,
    )

    if not update_expected_files:
        # output should be identical to what comes out of the workflow tests
        idx = ["Model", "Scenario", "Region", "Variable", "Unit"]

        filename = f"{emissions_id}_harmonized_infilled.csv"
        workflow_res = pd.read_csv(
            os.path.join(
                test_data_dir,
                "workflow-fair-slimmed",
                filename,
            )
        ).set_index(idx)
        here_res = pd.read_csv(os.path.join(out_dir, filename)).set_index(idx)

        pdt.assert_frame_equal(
            here_res.T,
            workflow_res.T,
            check_like=True,
            obj="Comparison with workflow output",
        )
