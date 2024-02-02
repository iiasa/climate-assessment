import os.path
import shutil
import traceback

import pandas as pd
import pandas.testing as pdt
from click.testing import CliRunner

import climate_assessment.cli


def check_output(output_dir, expected_output_dir, update_expected_files, rtol=1e-2):
    filename = "ex2_harmonized_infilled_alloutput.xlsx"

    file_to_check = os.path.join(output_dir, filename)
    file_expected = os.path.join(expected_output_dir, filename)

    if update_expected_files:
        shutil.copyfile(file_to_check, file_expected)

    else:
        for sheet in ["data", "meta"]:
            res = pd.read_excel(file_to_check, sheet_name=sheet)
            exp = pd.read_excel(file_expected, sheet_name=sheet)
            exp = exp.rename(columns={col: str(col) for col in exp.columns})
            if "exclude" in exp:
                # TODO: update excel files in future MR
                exp = exp.drop("exclude", axis="columns")

            if sheet == "meta":
                drop_cols = [
                    "harmonization",
                    "infilling",
                    "climate-models",
                    "workflow",
                ]
                res = res.drop(drop_cols, axis="columns")
                exp = exp.drop(drop_cols, axis="columns")

            pdt.assert_frame_equal(
                res.T,
                exp.T,
                check_like=True,
                obj="{} {}".format(sheet, os.path.basename(file_to_check)),
                rtol=rtol,
            )


def test_postprocess(tmpdir, test_data_dir, update_expected_files):
    out_dir = str(tmpdir)
    out_file = "processed_output_meta.csv"
    inp_file = os.path.join(
        test_data_dir,
        "clim-fair",
        "ex2_harmonized_infilled_rawoutput.xlsx",
    )

    fair_version = "1.6.2"

    runner = CliRunner()
    result = runner.invoke(
        climate_assessment.cli.postprocess,
        [
            inp_file,
            out_dir,
            "--output-file",
            out_file,
            "--prefix",
            "AR6 climate diagnostics",
            "--n_workers",
            1,
            "--model",
            "fair",
            "--model-version",
            fair_version,
        ],
    )

    assert result.exit_code == 0, "{}\n\n{}".format(
        traceback.print_exception(*result.exc_info), result.stdout
    )

    # expected output is stored in same directory as climate output, similar
    # to how postprocess is used in practice
    check_output(
        out_dir,
        os.path.join(test_data_dir, "clim-fair"),
        update_expected_files,
    )

    if not update_expected_files:
        # output should be identical to what comes out of the workflow tests
        idx = ["Model", "Scenario", "Region", "Variable", "Unit"]

        here_filename = os.path.join(out_dir, "ex2_harmonized_infilled_alloutput.xlsx")
        here_res = pd.read_excel(here_filename).set_index(idx)

        workflow_res = pd.read_excel(
            os.path.join(
                test_data_dir,
                "workflow-fair",
                "ex2_alloutput.xlsx",
            )
        )
        workflow_res = workflow_res[
            ~workflow_res["Variable"].str.startswith("Emissions")
        ].set_index(idx)

        pdt.assert_frame_equal(
            here_res,
            workflow_res,
            check_like=True,
            obj="Comparison with workflow output",
        )
