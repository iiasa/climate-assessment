import os.path
import traceback
from pathlib import Path

import pooch
import pyam
import requests
import toml


def _format_traceback_and_stdout_from_click_result(result):
    return f"{traceback.print_exception(*result.exc_info)}\n\n{result.stdout}"


def _get_infiller_download_link(filename):
    """
    Get infiller download link, intended only for use in CI
    """

    credentials_file = Path.home() / ".local" / "share" / "ixmp4" / "credentials.toml"
    with open(credentials_file, "w") as f:
        toml.dump(
            {
                "default": {
                    "username": os.environ.get("SCENARIO_EXPLORER_USER"),
                    "password": os.environ.get("SCENARIO_EXPLORER_PASSWORD"),
                }
            },
            f,
        )

    try:
        conn = pyam.iiasa.Connection()
    finally:
        # remove the yaml cred file
        credentials_file.unlink()

    infiller_url = (
        "https://db1.ene.iiasa.ac.at/ar6-public-api/rest/v2.1/files/"
        f"{filename}?redirect=false"
    )

    return requests.get(
        infiller_url,
        headers={"Authorization": f"Bearer {conn.auth.access_token}"},
    ).json()["directLink"]


def _file_available_or_downloaded(filepath, hash_exp, url):
    """
    Check if file exists (and matches expected hash) or can be downloaded

    Only intended for use in testing, but might provide inspiration for
    how to do this for others

    Parameters
    ----------
    filepath : str
        Path to file

    hash_exp : str
        Expected md5 hash

    url : str
        URL from which to download the file if it doesn't exist

    Returns
    -------
    bool
        Is the file available (or has it been downloaded hence is now
        available)?
    """
    try:
        pooch.retrieve(
            url=url,
            known_hash=f"md5:{hash_exp}",
            path=os.path.dirname(filepath),
            fname=os.path.basename(filepath),
        )
    except Exception as exc:
        # probably better ways to do this, can iterate as we use
        print(str(exc))
        return False

    return True
