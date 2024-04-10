import json
import logging

from openscm_runner.adapters import CICEROSCM

LOGGER = logging.getLogger(__name__)
DEFAULT_CICEROSCM_VERSION = "v2019vCH4"


def get_ciceroscm_configurations(
    ciceroscm_version,
    ciceroscm_probabilistic_file,
    num_cfgs,
):
    """
    Get configuration for CICERO-SCM
    """
    if CICEROSCM.get_version() != ciceroscm_version:
        # version strings for linux and windows might be different!
        raise AssertionError(CICEROSCM.get_version())

    with open(ciceroscm_probabilistic_file) as fh:
        cfgs_raw = json.load(fh)
    ciceroscm_cfgs = [c for c in cfgs_raw[:num_cfgs][:]]

    LOGGER.debug("%d total cfgs", len(ciceroscm_cfgs))

    return ciceroscm_cfgs


def ciceroscm_post_process(climate_output):
    LOGGER.info("Renaming variables")
    return climate_output
