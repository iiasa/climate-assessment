import json
import logging

import scmdata
from openscm_runner.adapters import MAGICC7

LOGGER = logging.getLogger(__name__)
DEFAULT_MAGICC_VERSION = "v7.5.3"
DEFAULT_MAGICC_DRAWNSET = "data/magicc/0fd0f62-derived-metrics-id-f023edb-drawnset.json"


def get_magicc7_configurations(
    magicc_version,
    magicc_probabilistic_file,
    magicc_extra_config,
    num_cfgs,
    co2_and_non_co2_warming,
):
    """
    Get configuration for MAGICC7
    """
    if MAGICC7.get_version() != magicc_version:
        # version strings for linux and windows might be different!
        raise AssertionError(MAGICC7.get_version())

    with open(magicc_probabilistic_file) as fh:
        cfgs_raw = json.load(fh)

    if magicc_extra_config is not None:
        with open(magicc_extra_config) as fh:
            extra_cfgs = json.load(fh)
    else:
        extra_cfgs = {}

    common_cfgs = {
        "out_temperature": 1,
        "out_forcing": 1,
        "out_heatuptake": 1,
        "out_dynamic_vars": [
            "DAT_HEATUPTK_AGGREG",
            "DAT_CO2_CONC",
            "DAT_CH4_CONC",
            "DAT_N2O_CONC",
            "DAT_CO2_AIR2LAND_FLUX",
            "DAT_CO2_AIR2OCEAN_FLUX",
            "DAT_CO2PF_EMIS",
            "DAT_CH4PF_EMIS",
        ],
        "out_ascii_binary": "BINARY",
        "out_binary_format": 2,
        **extra_cfgs,
    }
    LOGGER.debug("Adding common_cfgs %s", common_cfgs)

    magicc7_cfgs = [
        {
            "startyear": 1750,
            "endyear": 2105,
            "run_id": c["paraset_id"],
            **c["nml_allcfgs"],
            **common_cfgs,
        }
        for c in cfgs_raw["configurations"][:num_cfgs]
    ]

    if co2_and_non_co2_warming:
        LOGGER.debug("Adding CO2 and non-CO2 warming diagnosis cfgs")
        magicc7_cfgs = [
            {**c, "rf_total_runmodus": v}
            for c in magicc7_cfgs
            for v in ["ALL", "CO2", "ANTHROPOGENIC"]
        ]
        magicc7_out_cfg = ("rf_total_runmodus",)
    else:
        magicc7_out_cfg = ()

    LOGGER.debug("%d total cfgs", len(magicc7_cfgs))

    return magicc7_cfgs, magicc7_out_cfg


def magicc7_post_process(climate_output):
    LOGGER.info("Starting MAGICC7 post-processing")

    LOGGER.info("Fixing flux variable units")
    climate_output = climate_output.convert_unit(
        "GtC/yr", variable="*Flux*CO2"
    ).convert_unit("MtCH4/yr", variable="*Flux*CH4")
    LOGGER.info("Renaming variables")
    replacements = (
        (
            "Net Land to Atmosphere Flux|CH4|Earth System Feedbacks|Permafrost",
            "Net Land to Atmosphere Flux due to Permafrost|CH4",
        ),
        (
            "Net Land to Atmosphere Flux|CO2|Earth System Feedbacks|Permafrost",
            "Net Land to Atmosphere Flux due to Permafrost|CO2",
        ),
    )
    for old, new in replacements:
        LOGGER.debug("Replacing %s with %s", old, new)
        climate_output["variable"] = climate_output["variable"].apply(
            lambda x: x.replace(old, new)
        )

    LOGGER.info("Finishing MAGICC7 post-processing")
    return climate_output


def calculate_co2_and_nonco2_warming_magicc(res):
    """
    Calculate non-CO2 warming
    """
    climate_model = res.get_unique_meta("climate_model", no_duplicates=True)
    if not climate_model.startswith("MAGICC"):
        raise AssertionError(
            "Should only have magicc results here, received "
            f"climate_model: {climate_model}"
        )

    LOGGER.debug("Removing everything except Raw Surface Temperature (GSAT)")
    res = res.filter(variable="Raw Surface Temperature (GSAT)")

    LOGGER.info("Calculating CO2 warming")
    co2_warming = res.filter(rf_total_runmodus="CO2").drop_meta("rf_total_runmodus")
    co2_warming["variable"] = co2_warming["variable"] + "|CO2"
    LOGGER.info("Calculating Non-CO2 warming")
    nonco2_warming = (
        res.filter(rf_total_runmodus="ANTHROPOGENIC")
        .subtract(
            res.filter(rf_total_runmodus="CO2"),
            op_cols={"rf_total_runmodus": "anth - co2"},
        )
        .drop_meta("rf_total_runmodus")
    )
    nonco2_warming["variable"] = nonco2_warming["variable"] + "|Non-CO2"
    LOGGER.info("Calculating Residual")
    residual_warming = (
        res.filter(rf_total_runmodus="ALL")
        .subtract(
            res.filter(rf_total_runmodus="ANTHROPOGENIC"),
            op_cols={"rf_total_runmodus": "anth - co2"},
        )
        .drop_meta("rf_total_runmodus")
    )
    residual_warming["variable"] = residual_warming["variable"] + "|Residual"

    out = scmdata.run_append(
        [co2_warming, nonco2_warming, residual_warming]
    ).convert_unit("K")

    return out
