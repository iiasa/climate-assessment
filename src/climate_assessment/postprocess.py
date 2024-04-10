import os
from logging import getLogger

import aneris
import openscm_runner
import silicone

import climate_assessment
from climate_assessment import checks
from climate_assessment.climate import DEFAULT_MAGICC_VERSION
from climate_assessment.utils import add_gwp100_kyoto_wrapper

LOGGER = getLogger(__name__)


def do_postprocess(
    output,
    outdir,
    key_string,
    prefix,
    model_version=DEFAULT_MAGICC_VERSION,
    categorisation=True,
    reporting_completeness_categorisation=True,
    gwp=True,
    model="magicc",
):
    """
    Runs any required postprocessing steps

    Namely:
     * Categorisation
     * Completeness checks
     * Add GWP100 Kyoto Gases sums
     * Adding additional metadata
     * Plots
    """
    LOGGER.info("Add diagnostics and meta data")
    if categorisation:
        LOGGER.info("Adding a temperature category to meta data")
        output = checks.add_categorization(
            output,
            model_version=model_version,
            model=model,
            prefix=prefix,
        )
    if reporting_completeness_categorisation:
        LOGGER.info("Adding an emissions reporting completeness category to meta data")
        output = checks.add_completeness_category(output, key_string, prefix="")

    if gwp:
        LOGGER.info("Adding extra Kyoto Gases variables in GWP100 for each scenario")
        prefixes = [
            f"{prefix}|Infilled|",
        ]

        if any(["Harmonized" in v for v in output.variable]):
            prefixes.append(f"{prefix}|Harmonized|")

        if any([v.startswith("Emissions") for v in output.variable]):
            prefixes.append("")

        output = add_gwp100_kyoto_wrapper(
            output,
            gwps=["AR5GWP100", "AR6GWP100"],
            prefixes=prefixes,
        )

    output.set_meta(
        f"aneris (version: {aneris.__version__})",
        name="harmonization",
    )
    output.set_meta(
        f"silicone (version: {silicone.__version__})",
        name="infilling",
    )
    output.set_meta(
        f"openscm_runner (version: {openscm_runner.__version__})",
        name="climate-models",
    )
    output.set_meta(
        f"climate-assessment (version: {climate_assessment.__version__})",
        name="workflow",
    )

    outfile = os.path.join(outdir, f"{key_string}_alloutput.xlsx")
    LOGGER.info("Saving all output to: %s", outfile)
    output.to_excel(outfile)

    outfile = os.path.join(outdir, f"{key_string}_meta.xlsx")
    LOGGER.info("Saving all meta to: %s", outfile)
    output.export_meta(outfile)

    return output
