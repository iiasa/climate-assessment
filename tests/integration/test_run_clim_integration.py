import os.path

import numpy.testing as npt
import pytest
import scmdata
from click.testing import CliRunner

import climate_assessment.cli
from climate_assessment.testing import _format_traceback_and_stdout_from_click_result


def test_climate_only_no_valid(
    tmpdir, test_data_dir, fair_slim_configs_filepath, fair_common_configs_filepath
):
    out_dir = str(tmpdir)

    runner = CliRunner()
    result = runner.invoke(
        climate_assessment.cli.clim_cli,
        [
            os.path.join(test_data_dir, "ex2_broken_only.csv"),
            out_dir,
            "--probabilistic-file",
            fair_slim_configs_filepath,
            "--fair-extra-config",
            fair_common_configs_filepath,
        ],
    )

    assert result.exit_code == 0, result.exception

    assert "ERROR:  No '*Infilled*' data available" in result.output
    assert "ERROR:  Climate assessment failed, exiting" in result.output


@pytest.mark.parametrize(
    "hist_warming,hist_ref_period,hist_eval_period",
    (
        (0.85, "1850-1900", "2015-2015"),
        (0.92, "1900-1920", "2020-2020"),
    ),
)
def test_clim_historical_warming(
    hist_warming,
    hist_ref_period,
    hist_eval_period,
    tmpdir,
    test_data_dir,
    fair_slim_configs_filepath,
    fair_common_configs_filepath,
):
    out_dir = str(tmpdir)
    inp_file = os.path.join(
        test_data_dir,
        "workflow-fair",
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
            1,
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
            4,
            "--historical-warming",
            hist_warming,
            "--historical-warming-reference-period",
            hist_ref_period,
            "--historical-warming-evaluation-period",
            hist_eval_period,
        ],
    )

    assert result.exit_code == 0, _format_traceback_and_stdout_from_click_result(result)
    assert (
        f"Adjusting median of {hist_eval_period[0:4]}-{hist_eval_period[5:9]} "
        f"warming (rel. to {hist_ref_period[0:4]}-{hist_ref_period[5:9]}) to {hist_warming}K"
    ) in result.stdout

    res = scmdata.ScmRun(
        os.path.join(out_dir, "ex2_harmonized_infilled_IAMC_climateassessment.xlsx"),
        lowercase_cols=True,
    )
    npt.assert_allclose(
        res.filter(
            year=int(hist_eval_period.split("-")[0]),
            variable="*|Surface Temperature (GSAT)*50.0th Percentile",
        ).timeseries(),
        hist_warming,
    )


def test_historical_ref_period_out_of_order(
    tmpdir, test_data_dir, fair_slim_configs_filepath, fair_common_configs_filepath
):
    out_dir = str(tmpdir)
    inp_file = os.path.join(
        test_data_dir,
        "workflow-fair",
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
            1,
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
            4,
            "--historical-warming",
            0.8,
            "--historical-warming-reference-period",
            "1900-1850",
            "--historical-warming-evaluation-period",
            "1995-2014",
        ],
    )

    assert result.exit_code == 1, _format_traceback_and_stdout_from_click_result(result)

    assert isinstance(result.exception, ValueError)
    assert str(result.exception) == (
        "`period` must be a string of the form 'YYYY-YYYY' (with the first year being "
        "less than or equal to the second), we received 1900-1850"
    )


def test_historical_eval_period_out_of_order(
    tmpdir, test_data_dir, fair_slim_configs_filepath, fair_common_configs_filepath
):
    out_dir = str(tmpdir)
    inp_file = os.path.join(
        test_data_dir,
        "workflow-fair",
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
            1,
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
            4,
            "--historical-warming",
            0.8,
            "--historical-warming-reference-period",
            "1850-1900",
            "--historical-warming-evaluation-period",
            "2014-1995",
        ],
    )

    assert result.exit_code == 1, _format_traceback_and_stdout_from_click_result(result)

    assert isinstance(result.exception, ValueError)
    assert str(result.exception) == (
        "`period` must be a string of the form 'YYYY-YYYY' (with the first year being "
        "less than or equal to the second), we received 2014-1995"
    )

def test_output_written(
    tmpdir, test_data_dir, fair_slim_configs_filepath, fair_common_configs_filepath
):
    out_dir = str(tmpdir)
    inp_file = os.path.join(
        test_data_dir,
        "workflow-fair",
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
            1,
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
            4,
            "--historical-warming",
            0.8,
            "--save-csv-combined-output"
        ],
    )

    out_csv_fname = os.path.join(out_dir, "ex2_harmonized_infilled_rawoutput.csv")
    out_xls_fname = os.path.join(out_dir, "ex2_harmonized_infilled_rawoutput.xlsx")

    assert os.path.isfile(out_xls_fname), f"XLS output not written:"
    assert os.path.isfile(out_csv_fname), f"--save-csv-combined-output was set but CSV output not written:"