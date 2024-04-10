import json
import logging

import numpy as np
from openscm_runner.adapters import FAIR

LOGGER = logging.getLogger(__name__)
DEFAULT_FAIR_VERSION = "1.6.2"


def get_fair_configurations(
    fair_version, fair_probabilistic_file, fair_extra_config, num_cfgs
):
    """
    Get configuration for FaIR
    """
    if FAIR.get_version() != fair_version:
        raise AssertionError(FAIR.get_version())

    with open(fair_probabilistic_file) as fh:
        cfgs_raw = json.load(fh)

    with open(fair_extra_config) as fh:
        cfgs_common = json.load(fh)

    e_pi = [0] * 40
    for idx in range(5, 12):
        e_pi[idx] = cfgs_common["E_pi"][idx - 5]

    fair_cfgs = []
    for i, c in enumerate(cfgs_raw[:num_cfgs]):
        scale = [1] * 45
        c_pi = [0] * 31
        c_pi[1] = cfgs_common["C_pi"][0]
        c_pi[2] = cfgs_common["C_pi"][1]
        c_pi[3] = cfgs_common["C_pi"][2]
        c_pi[20] = cfgs_common["C_pi"][3]
        c_pi[25] = cfgs_common["C_pi"][4]
        c_pi[29] = cfgs_common["C_pi"][5]
        c_pi[30] = cfgs_common["C_pi"][6]
        scale[1] = c["scale"][0]
        scale[2] = c["scale"][1]
        for idx in range(3, 31):
            scale[idx] = c["scale"][2]
        scale[15] = scale[15] * cfgs_common["cfc11_adj"]
        scale[16] = scale[16] * cfgs_common["cfc12_adj"]
        scale[33] = c["scale"][3]
        scale[34] = c["scale"][4]
        scale[41] = c["scale"][5]
        scale[42] = c["scale"][6]
        scale[43] = c["scale"][7]
        c_pi[0] = c["C_pi_CO2"]
        f_solar = np.zeros(361)
        f_solar[:270] = (
            np.linspace(0, c["trend_solar"], 270)
            + np.array(cfgs_common["default_solar"])[:270] * c["scale"][8]
        )
        f_solar[270:351] = (
            c["trend_solar"]
            + np.array(cfgs_common["default_solar"])[270:351] * c["scale"][8]
        )
        f_solar[351:361] = cfgs_common["default_solar"][351:]
        this_cfg = {
            "run_id": i,
            "F2x": c["F2x"],
            "r0": c["r0"],
            "rt": c["rt"],
            "rc": c["rc"],
            "lambda_global": c["lambda_global"],
            "ocean_heat_capacity": c["ocean_heat_capacity"],
            "ocean_heat_exchange": c["ocean_heat_exchange"],
            "deep_ocean_efficacy": c["deep_ocean_efficacy"],
            "b_aero": [
                c["b_aero"][0],
                0.0,
                0.0,
                0.0,
                c["b_aero"][1],
                c["b_aero"][2],
                c["b_aero"][3],
            ],
            "ghan_params": c["ghan_params"],
            "scale": scale,
            "F_solar": f_solar.tolist(),
            "F_volcanic": cfgs_common["default_volcanic"],
            "C_pi": c_pi,
            "b_tro3": c["b_tro3"],
            "ozone_feedback": c["ozone_feedback"],
            "E_pi": e_pi,
            "ghg_forcing": cfgs_common["ghg_forcing"],
            "aCO2land": cfgs_common["aCO2land"],
            "stwv_from_ch4": cfgs_common["stwv_from_ch4"],
            "F_ref_BC": cfgs_common["F_ref_BC"],
            "E_ref_BC": cfgs_common["E_ref_BC"],
            "tropO3_forcing": cfgs_common["tropO3_forcing"],
            "natural": cfgs_common["natural"],
        }
        fair_cfgs.append(this_cfg)

    return fair_cfgs


def fair_post_process(climate_output):
    # convert units to W/m^2
    climate_output = climate_output.convert_unit(
        "W/m^2", variable="Effective Radiative Forcing*"
    )

    return climate_output
