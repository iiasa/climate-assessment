import os.path
import shutil
import traceback

import pandas as pd
import pandas.testing as pdt
from click.testing import CliRunner

import climate_assessment.cli


def check_output(output_dir, expected_output_dir, update_expected_files, rtol=1e-2):
    files = ["ex2_harmonized_infilled_rawoutput.xlsx"]

    for filename in files:
        file_to_check = os.path.join(output_dir, filename)
        file_expected = os.path.join(expected_output_dir, filename)

        if update_expected_files:
            shutil.copyfile(file_to_check, file_expected)

        else:
            for sheet in ["data", "meta"]:
                res = pd.read_excel(file_to_check, sheet_name=sheet)
                exp = pd.read_excel(file_expected, sheet_name=sheet)
                if "exclude" in exp:
                    # TODO: update excel files in future MR
                    exp = exp.drop("exclude", axis="columns")

                pdt.assert_frame_equal(
                    res.T,
                    exp.T,
                    check_like=True,
                    obj=f"{sheet} {os.path.basename(file_to_check)}",
                    rtol=rtol,
                )


def test_clim(
    tmpdir,
    test_data_dir,
    update_expected_files,
    fair_slim_configs_filepath,
    fair_common_configs_filepath,
):
    out_dir = str(tmpdir)
    inp_file = os.path.join(
        test_data_dir,
        "workflow-fair-slimmed",
        "ex2_harmonized_infilled.csv",
    )

    fair_version = "1.6.2"

    runner = CliRunner()
    result = runner.invoke(
        climate_assessment.cli.clim_cli,
        [
            inp_file,
            out_dir,
            "--num-cfgs",
            6,
            "--test-run",
            "--model",
            "fair",
            "--model-version",
            fair_version,
            "--probabilistic-file",
            fair_slim_configs_filepath,
            "--fair-extra-config",
            fair_common_configs_filepath,
            "--scenario-batch-size",
            40,
        ],
    )

    assert result.exit_code == 0, "{}\n\n{}".format(
        traceback.print_exception(*result.exc_info), result.stdout
    )

    check_output(
        out_dir,
        os.path.join(test_data_dir, "clim-fair-6cfg"),
        update_expected_files,
    )

    if not update_expected_files:
        # output should be identical to what comes out of the workflow tests
        idx = ["Model", "Scenario", "Region", "Variable", "Unit"]

        filename = "ex2_harmonized_infilled_rawoutput.xlsx"
        here_res = pd.read_excel(os.path.join(out_dir, filename))
        here_res = here_res[~here_res["Variable"].str.contains("Emissions")].set_index(
            idx
        )

        workflow_res = pd.read_excel(
            os.path.join(
                test_data_dir,
                "workflow-fair-slimmed",
                "ex2_IAMC_climateassessment.xlsx",
            )
        ).set_index(idx)

        pdt.assert_frame_equal(
            here_res,
            workflow_res,
            check_like=True,
            obj="Comparison with workflow output",
        )
