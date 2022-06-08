from pathlib import Path

import pyam
from setuptools_scm import get_version

try:
    from importlib.metadata import version
except ImportError:
    # no recourse if the fallback isn't there either...
    from importlib_metadata import version

# get version number either from git (preferred) or metadata
try:
    __version__ = get_version(Path(__file__).parents[1])
except LookupError:
    __version__ = version("climate-assessment")


# auxiliary pyam-based function for downloading IAMC data
def retrieve_data(variable_list, region_list, db, username, pw):
    conn = pyam.iiasa.Connection(db, creds=(username, pw))
    valid_scenarios = ["*"]
    data = conn.query(
        scenario=valid_scenarios, variable=variable_list, region=region_list
    ).drop("meta", axis=1)
    data = data.drop("subannual", axis=1)
    return pyam.IamDataFrame(data)
