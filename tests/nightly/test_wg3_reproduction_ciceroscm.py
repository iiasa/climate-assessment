import os
import os.path

import pytest
from click.testing import CliRunner

import climate_assessment.cli

pytestmark = pytest.mark.wg3


def test_wg3_ciceroscm(
    tmpdir,
    test_data_dir,
    data_dir,
    check_consistency_with_database,
    infiller_database_filepath,
):
    out_dir = str(tmpdir)
    ciceroscm_version = "v2019vCH4"
    emissions_id = "ar6_IPs_emissions"
    runner = CliRunner()
    result = runner.invoke(
        climate_assessment.cli.workflow,
        [
            os.path.join(test_data_dir, f"{emissions_id}.csv"),
            out_dir,
            "--num-cfgs",
            600,
            "--model-version",
            ciceroscm_version,
            "--probabilistic-file",
            os.path.join(data_dir, "cicero", "subset_cscm_configfile.json"),
            "--infilling-database",
            infiller_database_filepath,
            "--model",
            "ciceroscm",
        ],
    )

    assert result.exit_code == 0, result.exception

    check_consistency_with_database(
        output_file=(
            os.path.join(
                out_dir,
                "ar6_IPs_emissions_IAMC_climateassessment.xlsx",
            )
        ),
        expected_output_file=(
            os.path.join(
                test_data_dir, "expected-output-wg3/two_ips_climate_cicero.xlsx"
            )
        ),
    )
