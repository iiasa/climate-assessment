import json
import os
import tempfile

import f90nml
import pymagicc

MAGICC_RUN_DIR = os.environ["MAGICC_RUN_DIR"]
END_YEAR = 2010

OUT_DIR = os.path.join(MAGICC_RUN_DIR, "sr15")
if not os.path.exists(os.path.join(MAGICC_RUN_DIR, "sr15")):
    os.makedirs(OUT_DIR)


file_list = [
    "HISTSSP_BCB_OT.IN",
    "HISTSSP_OCB_OT.IN",
    "HISTSSP_OCN_OT.IN",
    "HISTSSP_SOXNB_OT.IN",
    "HISTSSP_BCI_OT.IN",
    "HISTSSP_OCI_OT.IN",
    "HISTSSP_SOXI_OT.IN",
    "HISTSSP_SS_OT.IN",
    "HISTSSP_BCB_RF.IN",
    "HISTSSP_BCI_RF.IN",
    "HISTSSP_BCSNOW_RF.IN",
    "GISS_LANDUSE_RF.IN",
    "HISTSSP_OCB_RF.IN",
    "HISTSSP_OCI_RF.IN",
    "HISTSSP_SOXI_RF.IN",
    "HISTSSP_SOXB_RF.IN",
    "HISTSSP_SOXN_EMIS.IN",
    "HISTORICAL_BCB_EMIS.IN",
    "HISTORICAL_BCI_EMIS.IN",
    "HISTORICAL_COB_EMIS.IN",
    "HISTORICAL_COI_EMIS.IN",
    "HISTORICAL_NH3B_EMIS.IN",
    "HISTORICAL_NH3I_EMIS.IN",
    "HISTORICAL_NMVOCB_EMIS.IN",
    "HISTORICAL_NMVOCI_EMIS.IN",
    "HISTORICAL_NOXB_EMIS.IN",
    "HISTORICAL_NOXI_EMIS.IN",
    "HISTORICAL_OCB_EMIS.IN",
    "HISTORICAL_OCI_EMIS.IN",
    "HISTORICAL_SOXB_EMIS.IN",
    "HISTORICAL_SOXI_EMIS.IN",
]


def get_sr15_name(f):
    return (
        f.replace("HISTORICAL", "HISTSR15")
        .replace("HISTSSP", "HISTSR15")
        .replace("GISS", "HISTSR15")
    )


for f in file_list:
    with open(os.path.join(MAGICC_RUN_DIR, f), "r") as fh:
        contents = fh.read()

    with tempfile.TemporaryDirectory() as td:
        tf = os.path.join(td, f)
        with open(tf, "w") as fh:
            fh.write(contents.replace("FORC-", "     "))

        in_file = pymagicc.MAGICCData(tf)

    in_file = in_file.filter(year=range(0, END_YEAR + 1))
    out_fname = os.path.join(OUT_DIR, get_sr15_name(f))
    print(out_fname)
    in_file.write(out_fname, 7)

magicc_default_cfg = f90nml.read(os.path.join(MAGICC_RUN_DIR, "MAGCFG_DEFAULTALL.CFG"))[
    "nml_allcfgs"
]

updated_cfgs = {}
for k in magicc_default_cfg:
    if magicc_default_cfg[k] in file_list:
        updated_cfgs[k] = "sr15/" + get_sr15_name(magicc_default_cfg[k])

print(json.dumps(updated_cfgs, indent=2))
