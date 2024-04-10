"""
Climate assesssment workflow
"""

from __future__ import annotations

import importlib.metadata

import pyam

try:
    __version__ = importlib.metadata.version("climate_assessment")
except Exception:  # pylint: disable=broad-except  # pragma: no cover
    # Local copy, not installed with setuptools
    __version__ = "unknown"


def retrieve_data(variable_list, region_list, db, username, pw):
    """
    Auxiliary pyam-based function for downloading IAMC data

    Should be removed, or at least moved, in future
    """
    conn = pyam.iiasa.Connection(db, creds=(username, pw))
    valid_scenarios = ["*"]
    data = conn.query(
        scenario=valid_scenarios, variable=variable_list, region=region_list
    ).drop("meta", axis=1)
    data = data.drop("subannual", axis=1)

    return pyam.IamDataFrame(data)
