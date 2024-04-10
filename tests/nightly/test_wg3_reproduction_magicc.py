import os
import os.path
import traceback

import pytest
from click.testing import CliRunner

import climate_assessment.cli

pytestmark = pytest.mark.wg3


def test_wg3_magicc(
    tmpdir, test_data_dir, check_consistency_with_database, infiller_database_filepath
):
    out_dir = str(tmpdir)

    magicc_version = "v7.5.3"
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
            magicc_version,
            "--probabilistic-file",
            os.environ["MAGICC_PROBABILISTIC_FILE"],
            "--infilling-database",
            infiller_database_filepath,
            "--model",
            "magicc",
        ],
    )

    assert result.exit_code == 0, "{}\n\n{}".format(
        traceback.print_exception(*result.exc_info), result.stdout
    )

    check_consistency_with_database(
        output_file=(
            os.path.join(
                out_dir,
                "ar6_IPs_emissions_IAMC_climateassessment.xlsx",
            )
        ),
        expected_output_file=(
            os.path.join(
                test_data_dir, "expected-output-wg3/two_ips_climate_magicc.xlsx"
            )
        ),
        rtol=1e-3,
        atol=1e-3,
    )
