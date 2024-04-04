import os
import os.path
import traceback

import pytest
from click.testing import CliRunner

import climate_assessment.cli

pytestmark = pytest.mark.nightly


def _check_ssp245_hack_missing_emissions_gone(stdout):
    assert (
        "Using hack solution to add missing emissions from ssp245, remove before proper run!!"
        not in stdout
    )


def test_workflow_ciceroscm(
    tmpdir, test_data_dir, data_dir, check_workflow_output, update_expected_files
):
    out_dir = str(tmpdir)

    ciceroscm_version = "v2019vCH4"
    emissions_id = "ex2"
    runner = CliRunner()
    result = runner.invoke(
        climate_assessment.cli.workflow,
        [
            os.path.join(test_data_dir, f"{emissions_id}.csv"),
            out_dir,
            "--num-cfgs",
            10,
            "--test-run",
            "--model-version",
            ciceroscm_version,
            "--probabilistic-file",
            os.path.join(data_dir, "cicero", "subset_cscm_configfile.json"),
            "--infilling-database",
            os.path.join(
                test_data_dir,
                "cmip6-ssps-workflow-emissions.csv",
            ),
            "--model",
            "ciceroscm",
        ],
    )

    assert result.exit_code == 0, result.exception

    check_workflow_output(
        emissions_id,
        out_dir,
        os.path.join(test_data_dir, "workflow-ciceroscm"),
        "CICERO-SCM",
        ciceroscm_version,
        update_expected_files,
    )


def test_workflow_fair(
    tmpdir,
    test_data_dir,
    check_workflow_output,
    update_expected_files,
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
            10,
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
                "cmip6-ssps-workflow-emissions.csv",
            ),
            "--model",
            "fair",
        ],
    )

    assert result.exit_code == 0, "{}\n\n{}".format(
        traceback.print_exception(*result.exc_info), result.stdout
    )
    _check_ssp245_hack_missing_emissions_gone(result.stdout)

    check_workflow_output(
        emissions_id,
        out_dir,
        os.path.join(test_data_dir, "workflow-fair"),
        "FaIR",
        fair_version,
        update_expected_files,
    )


def test_workflow_magicc(
    tmpdir, test_data_dir, check_workflow_output, update_expected_files
):
    out_dir = str(tmpdir)

    magicc_version = "v7.5.3"
    emissions_id = "ex2"

    runner = CliRunner()
    result = runner.invoke(
        climate_assessment.cli.workflow,
        [
            os.path.join(test_data_dir, f"{emissions_id}.csv"),
            out_dir,
            "--num-cfgs",
            10,
            "--test-run",
            "--model-version",
            magicc_version,
            "--probabilistic-file",
            os.environ["MAGICC_PROBABILISTIC_FILE"],
            "--infilling-database",
            os.path.join(
                test_data_dir,
                "cmip6-ssps-workflow-emissions.csv",
            ),
            "--model",
            "magicc",
        ],
    )

    assert result.exit_code == 0, "{}\n\n{}".format(
        traceback.print_exception(*result.exc_info), result.stdout
    )

    check_workflow_output(
        emissions_id,
        out_dir,
        os.path.join(test_data_dir, "workflow-magicc"),
        "MAGICC",
        magicc_version,
        update_expected_files,
        rtol=3 * 1e-4,
    )
