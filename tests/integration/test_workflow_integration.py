import os.path
import traceback

import numpy.testing as npt
import pytest
import scmdata
from click.testing import CliRunner

import climate_assessment.cli
from climate_assessment.testing import _format_traceback_and_stdout_from_click_result


def test_workflow_no_valid(
    tmpdir, test_data_dir, fair_slim_configs_filepath, fair_common_configs_filepath
):
    out_dir = str(tmpdir)

    runner = CliRunner()
    result = runner.invoke(
        climate_assessment.cli.workflow,
        [
            os.path.join(test_data_dir, "ex2_broken_only.csv"),
            out_dir,
            "--probabilistic-file",
            fair_slim_configs_filepath,
            "--fair-extra-config",
            fair_common_configs_filepath,
        ],
    )

    assert result.exit_code == 0, "{}\n\n{}".format(
        traceback.print_exception(*result.exc_info), result.stdout
    )

    assert (
        "No Emissions|CO2 or Emissions|CO2|Energy and Industrial Processes "
        "found in scenario 1point5 produced by model10"
    ) in result.output

    assert (
        "No Emissions|CO2 or Emissions|CO2|Energy and Industrial Processes "
        "found in scenario 1point5 produced by model8"
    ) in result.output


@pytest.mark.parametrize(
    "hist_warming,hist_ref_period,hist_eval_period",
    (
        (0.85, "1850-1900", "2015-2015"),
        (0.92, "1900-1920", "2020-2020"),
    ),
)
def test_workflow_historical_warming(
    hist_warming,
    hist_ref_period,
    hist_eval_period,
    tmpdir,
    test_data_dir,
    fair_slim_configs_filepath,
    fair_common_configs_filepath,
):
    out_dir = str(tmpdir)

    fair_version = "1.6.2"
    emissions_id = "ex2"

    runner = CliRunner()
    result = runner.invoke(
        climate_assessment.cli.workflow,
        [
            os.path.join(test_data_dir, f"{emissions_id}.csv"),
            out_dir,
            "--num-cfgs",
            1,
            "--test-run",
            "--model-version",
            fair_version,
            "--probabilistic-file",
            fair_slim_configs_filepath,
            "--fair-extra-config",
            fair_common_configs_filepath,
            "--infilling-database",
            os.path.join(
                test_data_dir,
                "cmip6-ssps-workflow-emissions_infillerdatabase_until2100.csv",
            ),
            "--model",
            "fair",
            "--historical-warming",
            hist_warming,
            "--historical-warming-reference-period",
            hist_ref_period,
            "--historical-warming-evaluation-period",
            hist_eval_period,
            "--scenario-batch-size",
            40,
        ],
    )

    assert result.exit_code == 0, _format_traceback_and_stdout_from_click_result(result)
    assert (
        f"Adjusting median of {hist_eval_period[0:4]}-{hist_eval_period[5:9]} "
        f"warming (rel. to {hist_ref_period[0:4]}-{hist_ref_period[5:9]}) to {hist_warming}K"
    ) in result.stdout

    res = scmdata.ScmRun(
        os.path.join(out_dir, "ex2_IAMC_climateassessment.xlsx"), lowercase_cols=True
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

    fair_version = "1.6.2"
    emissions_id = "ex2"

    runner = CliRunner()
    result = runner.invoke(
        climate_assessment.cli.workflow,
        [
            os.path.join(test_data_dir, f"{emissions_id}.csv"),
            out_dir,
            "--num-cfgs",
            1,
            "--test-run",
            "--model-version",
            fair_version,
            "--probabilistic-file",
            fair_slim_configs_filepath,
            "--fair-extra-config",
            fair_common_configs_filepath,
            "--infilling-database",
            os.path.join(
                test_data_dir,
                "cmip6-ssps-workflow-emissions_infillerdatabase_until2100.csv",
            ),
            "--model",
            "fair",
            "--historical-warming",
            0.8,
            "--historical-warming-reference-period",
            "1900-1850",
            "--historical-warming-evaluation-period",
            "1995-2014",
            "--scenario-batch-size",
            40,
        ],
    )

    assert result.exit_code == 1, _format_traceback_and_stdout_from_click_result(result)

    assert isinstance(result.exception, ValueError)
    assert str(result.exception) == (
        "`period` must be a string of the form 'YYYY-YYYY' (with the first year being "
        "less than or equal to the second), we received 1900-1850"
    )


@pytest.mark.parametrize("hist_ref_period", ("1850--1900", "185-1900", "1850,1900"))
def test_historical_ref_period_badly_formed(
    hist_ref_period,
    tmpdir,
    test_data_dir,
    fair_slim_configs_filepath,
    fair_common_configs_filepath,
):
    out_dir = str(tmpdir)

    fair_version = "1.6.2"
    emissions_id = "ex2"

    runner = CliRunner()
    result = runner.invoke(
        climate_assessment.cli.workflow,
        [
            os.path.join(test_data_dir, f"{emissions_id}.csv"),
            out_dir,
            "--num-cfgs",
            1,
            "--test-run",
            "--model-version",
            fair_version,
            "--probabilistic-file",
            fair_slim_configs_filepath,
            "--fair-extra-config",
            fair_common_configs_filepath,
            "--infilling-database",
            os.path.join(
                test_data_dir,
                "cmip6-ssps-workflow-emissions_infillerdatabase_until2100.csv",
            ),
            "--model",
            "fair",
            "--historical-warming",
            0.8,
            "--historical-warming-reference-period",
            hist_ref_period,
            "--historical-warming-evaluation-period",
            "1995-2014",
            "--scenario-batch-size",
            40,
        ],
    )

    assert result.exit_code == 1, _format_traceback_and_stdout_from_click_result(result)

    assert isinstance(result.exception, ValueError)
    assert str(result.exception) == (
        f"`period` must be a string of the form 'YYYY-YYYY' (with the first year being "
        f"less than or equal to the second), we received {hist_ref_period}"
    )


def test_historical_eval_period_out_of_order(
    tmpdir, test_data_dir, fair_slim_configs_filepath, fair_common_configs_filepath
):
    out_dir = str(tmpdir)

    fair_version = "1.6.2"
    emissions_id = "ex2"

    runner = CliRunner()
    result = runner.invoke(
        climate_assessment.cli.workflow,
        [
            os.path.join(test_data_dir, f"{emissions_id}.csv"),
            out_dir,
            "--num-cfgs",
            1,
            "--test-run",
            "--model-version",
            fair_version,
            "--probabilistic-file",
            fair_slim_configs_filepath,
            "--fair-extra-config",
            fair_common_configs_filepath,
            "--infilling-database",
            os.path.join(
                test_data_dir,
                "cmip6-ssps-workflow-emissions_infillerdatabase_until2100.csv",
            ),
            "--model",
            "fair",
            "--historical-warming",
            0.8,
            "--historical-warming-reference-period",
            "1850-1900",
            "--historical-warming-evaluation-period",
            "2014-1995",
            "--scenario-batch-size",
            40,
        ],
    )

    assert result.exit_code == 1, _format_traceback_and_stdout_from_click_result(result)

    assert isinstance(result.exception, ValueError)
    assert str(result.exception) == (
        "`period` must be a string of the form 'YYYY-YYYY' (with the first year being "
        "less than or equal to the second), we received 2014-1995"
    )


@pytest.mark.parametrize("hist_eval_period", ("1995--2014", "199-2014", "1995,2014"))
def test_historical_eval_period_badly_formed(
    hist_eval_period,
    tmpdir,
    test_data_dir,
    fair_slim_configs_filepath,
    fair_common_configs_filepath,
):
    out_dir = str(tmpdir)

    fair_version = "1.6.2"
    emissions_id = "ex2"

    runner = CliRunner()
    result = runner.invoke(
        climate_assessment.cli.workflow,
        [
            os.path.join(test_data_dir, f"{emissions_id}.csv"),
            out_dir,
            "--num-cfgs",
            1,
            "--test-run",
            "--model-version",
            fair_version,
            "--probabilistic-file",
            fair_slim_configs_filepath,
            "--fair-extra-config",
            fair_common_configs_filepath,
            "--infilling-database",
            os.path.join(
                test_data_dir,
                "cmip6-ssps-workflow-emissions_infillerdatabase_until2100.csv",
            ),
            "--model",
            "fair",
            "--historical-warming",
            0.8,
            "--historical-warming-reference-period",
            "1850-1900",
            "--historical-warming-evaluation-period",
            hist_eval_period,
            "--scenario-batch-size",
            40,
        ],
    )

    assert result.exit_code == 1, _format_traceback_and_stdout_from_click_result(result)

    assert isinstance(result.exception, ValueError)
    assert str(result.exception) == (
        f"`period` must be a string of the form 'YYYY-YYYY' (with the first year being "
        f"less than or equal to the second), we received {hist_eval_period}"
    )
