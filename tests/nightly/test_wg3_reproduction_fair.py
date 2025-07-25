import os
import os.path
import traceback

import pytest
from click.testing import CliRunner

import climate_assessment.cli

pytestmark = pytest.mark.wg3


def _check_ssp245_hack_missing_emissions_gone(stdout):
    assert (
        "Using hack solution to add missing emissions from ssp245, remove before proper run!!"
        not in stdout
    )


def test_wg3_fair(
    tmpdir,
    test_data_dir,
    check_consistency_with_database,
    infiller_database_filepath,
    fair_slim_configs_filepath,
    fair_common_configs_filepath,
):
    out_dir = str(tmpdir)

    fair_version = "1.6.2"
    emissions_id = "ar6_IPs_emissions"

    runner = CliRunner()
    result = runner.invoke(
        climate_assessment.cli.workflow,
        [
            os.path.join(test_data_dir, f"{emissions_id}.csv"),
            out_dir,
            "--num-cfgs",
            2237,
            "--model-version",
            fair_version,
            "--probabilistic-file",
            fair_slim_configs_filepath,
            "--fair-extra-config",
            fair_common_configs_filepath,
            "--infilling-database",
            infiller_database_filepath,
            "--model",
            "fair",
        ],
    )

    assert result.exit_code == 0, (
        f"{traceback.print_exception(*result.exc_info)}\n\n{result.stdout}"
    )
    _check_ssp245_hack_missing_emissions_gone(result.stdout)

    check_consistency_with_database(
        output_file=os.path.join(
            out_dir,
            "ar6_IPs_emissions_IAMC_climateassessment.xlsx",
        ),
        expected_output_file=(
            os.path.join(test_data_dir, "expected-output-wg3/two_ips_climate_fair.xlsx")
        ),
    )
