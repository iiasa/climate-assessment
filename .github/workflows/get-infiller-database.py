import os.path
import requests

import pooch
import pyam


def get_infiller_download_link(filename):
    pyam.iiasa.set_config(
        os.environ.get("SCENARIO_EXPLORER_USER"),
        os.environ.get("SCENARIO_EXPLORER_PASSWORD"),
        "iiasa_creds.yaml",
    )
    try:
        conn = pyam.iiasa.Connection(
            creds="iiasa_creds.yaml",
            auth_url="https://db1.ene.iiasa.ac.at/EneAuth/config/v1",
        )
    finally:
        # remove the yaml cred file
        os.remove("iiasa_creds.yaml")

    infiller_url = (
        "https://db1.ene.iiasa.ac.at/ar6-public-api/rest/v2.1/files/"
        f"{filename}?redirect=false"
    )
    return requests.get(
        infiller_url,
        headers={"Authorization": f"Bearer {conn._token}"},
    ).json()["directLink"]


INFILLER_DATABASE_NAME = (
    "1652361598937-ar6_emissions_vetted_infillerdatabase_10.5281-zenodo.6390768.csv"
)
INFILLER_HASH = "30fae0530d76cbcb144f134e9ed0051f"
INFILLER_DATABASE_FILEPATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "data",
    INFILLER_DATABASE_NAME,
)
os.makedirs(os.path.dirname(INFILLER_DATABASE_FILEPATH), exist_ok=True)

INFILLER_DATABASE_DOWNLOAD_URL = get_infiller_download_link(
    INFILLER_DATABASE_NAME
)

pooch.retrieve(
    url=INFILLER_DATABASE_DOWNLOAD_URL,
    known_hash=f"md5:{INFILLER_HASH}",
    path=os.path.dirname(INFILLER_DATABASE_FILEPATH),
    fname=os.path.basename(INFILLER_DATABASE_FILEPATH),
)
