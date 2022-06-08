import os
import os.path
import traceback

import pyam
import pytest
from click.testing import CliRunner

import climate_assessment.cli
from climate_assessment.harmonization import HARMONIZATION_VARIABLES

pytestmark = pytest.mark.nightly


@pytest.mark.parametrize("harmonize", (True, False))
def test_workflow(
    harmonize,
    tmpdir,
    test_data_dir,
    data_dir,
    check_workflow_output,
    update_expected_files,
):
    out_dir = str(tmpdir)

    magicc_version = "v7.5.3"
    emissions_id = "sr15"

    runner = CliRunner()
    result = runner.invoke(
        climate_assessment.cli.workflow,
        [
            os.path.join(test_data_dir, "{}.csv".format(emissions_id)),
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
            "--co2-and-non-co2-warming",
            "--no-inputcheck",
            "--harmonization-instance",
            "sr15",
            "--magicc-extra-config",
            os.path.join(data_dir, "sr15-411", "sr15_magicc_conf.json"),
            "--prefix",
            "SR15 climate diagnostics",
            "--no-gwp",
            "--harmonize" if harmonize else "--dont-harmonize",
        ],
    )

    assert result.exit_code == 0, "{}\n\n{}".format(
        traceback.print_exception(*result.exc_info), result.stdout
    )

    out_dir_expected = (
        "workflow-magicc-sr15" if harmonize else "workflow-magicc-sr15-no-harmonization"
    )
    check_workflow_output(
        emissions_id,
        out_dir,
        os.path.join(test_data_dir, out_dir_expected),
        "magicc",
        magicc_version,
        update_expected_files,
        rtol=1e-3,
    )

    if not harmonize:
        # check that emissions were indeed not harmonized
        all_out = pyam.IamDataFrame(
            os.path.join(test_data_dir, out_dir, f"{emissions_id}_alloutput.xlsx")
        )
        all_out_raw = all_out.filter(variable="Emissions*")
        all_out_harmonized = all_out.filter(variable="*Harmonized*")
        all_out_infilled = all_out.filter(variable="*Infilled*")

        all_out_harmonized = all_out_harmonized.rename(
            {
                "variable": {
                    v: f"Emissions{v.split('Emissions')[-1]}"
                    for v in all_out_harmonized.variable
                }
            }
        )

        check_years = range(2010, 2100 + 1, 5)
        assert all_out_raw.filter(
            year=check_years, variable=HARMONIZATION_VARIABLES
        ).equals(
            all_out_harmonized.filter(
                year=check_years, variable=HARMONIZATION_VARIABLES
            )
        )

        # also that no infilling for key gases actually happened as they
        # were already supplied
        all_out_infilled = all_out_infilled.rename(
            {
                "variable": {
                    v: f"Emissions{v.split('Emissions')[-1]}"
                    for v in all_out_infilled.variable
                }
            }
        )
        check_vars = [
            "Emissions|BC",
            "Emissions|CH4",
            "Emissions|CO2|Energy and Industrial Processes",
            "Emissions|CO2|AFOLU",
            "Emissions|CO",
            "Emissions|N2O",
            "Emissions|NH3",
            "Emissions|NOx",
            "Emissions|OC",
            "Emissions|Sulfur",
            "Emissions|VOC",
        ]

        assert all_out_infilled.filter(
            year=all_out_harmonized.year, variable=check_vars
        ).equals(all_out_harmonized.filter(variable=check_vars))
