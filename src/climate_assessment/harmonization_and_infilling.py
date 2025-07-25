import logging
import os.path

import aneris
import silicone

from .checks import sanity_check_hierarchy
from .harmonization import HARMONIZATION_VARIABLES, run_harmonization
from .infilling import postprocess_infilled_for_climate, run_infilling

LOGGER = logging.getLogger(__name__)


def harmonization_and_infilling(
    df,
    key_string,
    infilling_database,
    prefix="AR6 climate diagnostics",
    instance="ar6",
    outdir="output",
    do_harmonization=True,
    # TODO: here is the downstream for potentially implementing gwp100 kyoto
):
    """
    Arguments
    ----------
    input_df : :class:`pyam.IamDataFrame`
        Input native emissions to harmonize and infill.

    inputcheck : bool
        Perform checks to remove unsuitable emissisons pathways. [Default: True]

    key_string : str
        Identifier string for writing out results. By default derived from
        the input_emissions_file string in a CLI command.

    outdir : str
        Path to output folder.

    infilling_database : str
        Path to the infiller database emissions file.

    harmonize : bool
        Perform harmonization (with False, only infilling is run). [Default: True]

    prefix : str
        Prefix used to identify the new variable names of results
        produced by the workflow.

    harmonization_instance : str
        Config string required by aneris.

    Returns
    -------
    bool
        Returns True if there are scenarios that can be run by a climate
        emulator. Those scenarios are not returned by this function, but rather
        written to the outdir. Returns False if there are no complete scenarios
        to be run.
    """
    if instance == "ar6":
        infilled_start_year = 2015
    elif instance == "sr15":
        infilled_start_year = 2010
    else:
        raise ValueError("Unknown value for instance")

    if do_harmonization:
        harmonized = run_harmonization(df, instance=instance, prefix=prefix)
    else:
        LOGGER.info("Not performing harmonization")
        harmonized = df.filter(
            year=range(infilled_start_year, 2100 + 1),
            variable=HARMONIZATION_VARIABLES,
        )
        harmonized = harmonized.rename(
            {"variable": {v: f"{prefix}|Harmonized|{v}" for v in harmonized.variable}}
        )

    if harmonized.empty:
        LOGGER.warning("No harmonized scenarios passed the checks")
        return False

    infilled, co2_infill_db, _ = run_infilling(
        harmonized,
        prefix=prefix,
        database_filepath=infilling_database,
        start_year=infilled_start_year,
    )

    # do post-processing checks after infilling
    # make sure the scenario reports until 2100
    infilled = postprocess_infilled_for_climate(
        infilled, prefix=prefix, start_year=infilled_start_year
    )

    if infilled.filter(variable="*Infilled*").empty:
        LOGGER.error("YOUR EMISSION FILE IS EMPTY AFTER INFILLING")
        return False
    else:
        # add meta string to record aneris and silicone versions
        infilled.set_meta(
            meta=(
                f"aneris (version: {aneris.__version__}), silicone (version: {silicone.__version__})"
            ),
            name="assessment-tools",
        )

        #  write out combined results of harmonization and infilling
        # write out csv file with all data (no meta)
        out_file_infilled = os.path.join(
            outdir, f"{key_string}_harmonized_infilled.csv"
        )

        LOGGER.info("Writing infilled data as csv to: %s", out_file_infilled)
        infilled.to_csv(out_file_infilled)

        # write out excel file with all data as well as meta data
        out_file_infilled_xlsx = out_file_infilled.replace(".csv", ".xlsx")
        LOGGER.info("Writing infilled data as xlsx to: %s", out_file_infilled_xlsx)
        infilled.to_excel(out_file_infilled_xlsx)

        # Sanity check for a consistent hierarchy.
        # Checks that Emissions|CO2 is the sum of AFOLU and Energy emissions
        # N.B. generally in the AR6 application total co2 co2_infill_db is empty
        if not co2_infill_db.empty:
            sanity_check_hierarchy(
                co2_infill_db,
                harmonized,
                infilled,
                out_afolu="Emissions|CO2|AFOLU",
                out_fossil="Emissions|CO2|Energy and Industrial Processes",
            )

        return True
