import os
import os.path
import traceback

from click.testing import CliRunner

import climate_assessment.cli


def _check_ssp245_hack_missing_emissions_gone(stdout):
    assert (
        "Using hack solution to add missing emissions from ssp245, remove before proper run!!"
        not in stdout
    )


# ToDo use smaller infiller data base and smaller configuration size
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
            os.path.join(test_data_dir, "{}.csv".format(emissions_id)),
            out_dir,
            "--num-cfgs",
            6,
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
        os.path.join(test_data_dir, "workflow-ciceroscm-slimmed"),
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

    climate_assessment.cli.run_workflow(
        os.path.join(test_data_dir, "{}.csv".format(emissions_id)),
        out_dir,
        inputcheck=True,
        model="fair",
        model_version=fair_version,
        probabilistic_file=fair_common_configs_filepath,
        num_cfgs=6,
        fair_extra_config=fair_slim_configs_filepath,
        scenario_batch_size=40,
        infilling_database=os.path.join(
                test_data_dir,
                "cmip6-ssps-workflow-emissions_infillerdatabase_until2100.csv",
            ),
    )

    check_workflow_output(
        emissions_id,
        out_dir,
        os.path.join(test_data_dir, "workflow-fair-slimmed"),
        "FaIR",
        fair_version,
        update_expected_files,
    )
