import logging
import os.path

import pandas as pd
import pandas.testing as pdt
import pyam
import scmdata
import silicone.database_crunchers
from silicone.multiple_infillers import infill_all_required_variables

from ..checks import check_negatives
from ..utils import _diff_variables, convert_co2_equiv_to_kt_gas, split_df

LOGGER = logging.getLogger(__name__)


def run_infilling(
    harmonised_df, prefix, database_filepath=None, start_year=2015, end_year=2100
):
    """
    Run infilling

    Parameters
    ----------
    harmonised_df : :class:`pyam.IamDataFrame`
        Input harmonised emissions to infill

    prefix : str
        Prefix used for the variable names

    database_filepath : str
        Path to the file which contains the infilling database

    start_year : int
        First year which should be reported in output

    end_ear : int
        Last year which should be reported in output

    Returns
    -------
    :class:`pyam.IamDataFrame`
        Infilled emissions. Output also includes the input emissions. The
        output is interpolated onto an annual timestep.
    """
    LOGGER.info("Infilling database: %s", database_filepath)
    if database_filepath is None:
        database_filepath = os.path.join(
            os.path.dirname(__file__),
            "cmip6-ssps-workflow-emissions.csv",
        )
        LOGGER.warning(
            "You are using a very simple infiller database. For any research application, it is strongly recommended to use a larger infiller database such as the AR6 infiller database instead. Please make sure to check out the documentation of this package, under 'Installation', section 'Infiller database' ."
        )

    database_filepath_cfcs = os.path.join(
        os.path.dirname(__file__), "cmip6-ssps-workflow-emissions.csv"
    )
    LOGGER.info("CFC infilling database: %s", database_filepath_cfcs)

    # We can prefix a string to the beginning of some variables to show they are infilled
    # TODO: remove hard-coding of string here
    infilled_data_prefix = f"{prefix}|Infilled"
    harmonized_prefix = f"{prefix}|Harmonized"

    # Here we specify the types of cruncher, choosing from silicone package modules.
    # This is a list of cruncher types, of the same length as the leader and required
    # variable lists
    types_of_cruncher = [
        silicone.database_crunchers.QuantileRollingWindows,
        silicone.database_crunchers.QuantileRollingWindows,
    ]

    # When infilling, what emissions data will we always have? A list of lists, the same
    # length as types_of_cruncher and qrw_variables_list
    leader_lists = [
        ["Emissions|CO2"],
        ["Emissions|CO2|Energy and Industrial Processes"],
    ]

    # What emissions data do we (sometimes) miss, or are unsure about?
    qrw_variables_list = [
        "Emissions|BC",
        "Emissions|CH4",
        "Emissions|CO2|AFOLU",
        "Emissions|CO",
        "Emissions|N2O",
        "Emissions|NH3",
        "Emissions|NOx",
        "Emissions|OC",
        "Emissions|Sulfur",
        "Emissions|VOC",
    ]

    fgas_cfc_cruncher = silicone.database_crunchers.RMSClosest
    fgas_cfc_variables_list = [
        "Emissions|HFC|HFC134a",
        "Emissions|HFC|HFC143a",
        "Emissions|HFC|HFC227ea",
        "Emissions|HFC|HFC23",
        "Emissions|HFC|HFC32",
        "Emissions|HFC|HFC43-10",
        "Emissions|HFC|HFC245ca",
        "Emissions|HFC|HFC125",
        "Emissions|SF6",
        "Emissions|PFC|CF4",
        "Emissions|PFC|C2F6",
        "Emissions|PFC|C6F14",
    ]

    cfcs_and_other_variables_cruncher = silicone.database_crunchers.RMSClosest
    cfcs_and_other_variables_list = [
        "Emissions|CCl4",
        "Emissions|CFC11",
        "Emissions|CFC113",
        "Emissions|CFC114",
        "Emissions|CFC115",
        "Emissions|CFC12",
        "Emissions|CH2Cl2",
        "Emissions|CH3Br",
        "Emissions|CH3CCl3",
        "Emissions|CH3Cl",
        "Emissions|CHCl3",
        "Emissions|HCFC141b",
        "Emissions|HCFC142b",
        "Emissions|HCFC22",
        "Emissions|HFC|HFC152a",
        "Emissions|HFC|HFC236fa",
        # 'Emissions|HFC|HFC245fa',
        "Emissions|HFC|HFC365mfc",
        "Emissions|Halon1202",
        "Emissions|Halon1211",
        "Emissions|Halon1301",
        "Emissions|Halon2402",
        "Emissions|NF3",
        "Emissions|PFC|C3F8",
        "Emissions|PFC|C4F10",
        "Emissions|PFC|C5F12",
        "Emissions|PFC|C7F16",
        "Emissions|PFC|C8F18",
        "Emissions|PFC|cC4F8",
        "Emissions|SO2F2",
    ]
    # Timesteps to report data on
    output_timesteps = list(range(start_year, end_year + 1, 1))

    # Convert the hfc/pfc units from CO2 equiv to mass of gas
    convert_hfc_units = True
    convert_pfc_units = True

    # Check that options make sense
    if len(leader_lists) != len(types_of_cruncher):
        raise AssertionError(
            "Number of lead variables doesn't match number of crunchers"
        )

    LOGGER.info("Loading infilling database")
    database = scmdata.ScmRun(database_filepath, lowercase_cols=True)

    LOGGER.info("Loading infilling database cfcs")
    database_cfcs = scmdata.ScmRun(database_filepath_cfcs, lowercase_cols=True)

    if len(database["region"].unique()) > 1:
        raise AssertionError(
            "Different regions should be "
            f"infilled separately. Your database has regions {database.regions()}"
        )

    to_fill_orig = harmonised_df.copy()
    if len(to_fill_orig.region) > 1:
        raise AssertionError(
            f"Different regions should be infilled separately. You are infilling {to_fill_orig.regions()}"
        )

    if to_fill_orig["region"][0] != database["region"][0]:
        raise AssertionError(
            "The cruncher data and the infilled data have different regions."
        )

    # Perform situation-specific data cleansing on variable names
    # ___________________________________________________________
    LOGGER.info("Preparing infilling databases")
    database["variable"] = database["variable"].apply(
        lambda x: f"Emissions{x.split('Emissions')[-1]}"
    )
    if not database["variable"].str.startswith("Emissions").all():
        raise AssertionError("Something fishy going on with prefix handling")

    for db, name in ((database, "database"), (database_cfcs, "database_cfcs")):
        late_start = min(db["year"]) > min(output_timesteps)
        early_finish = max(db["year"]) < max(output_timesteps)
        if late_start or early_finish:
            raise AssertionError(
                f"Database {name} does not extend far enough to be used for infilling"
            )

    database = pyam.IamDataFrame(database.timeseries(time_axis="year")).interpolate(
        output_timesteps, inplace=False
    )

    database_cfcs = pyam.IamDataFrame(
        database_cfcs.filter(year=output_timesteps).timeseries(time_axis="year")
    ).interpolate(output_timesteps, inplace=False)

    # Handle CO2 reporting
    # ____________________
    co2_total = "Emissions|CO2"
    co2_energy = "Emissions|CO2|Energy and Industrial Processes"
    co2_afolu = "Emissions|CO2|AFOLU"

    # if anything has total CO2 and energy, calculate AFOLU CO2 as difference
    # if anything has total CO2 and AFOLU, calculate energy CO2 as difference
    for has, missing in ((co2_energy, co2_afolu), (co2_afolu, co2_energy)):
        _, missing_sector = split_df(
            harmonised_df, variable=f"{harmonized_prefix}|{missing}"
        )

        if not missing_sector.empty:
            sector_inferred = _diff_variables(
                missing_sector,
                f"{harmonized_prefix}|{co2_total}",
                f"{harmonized_prefix}|{has}",
                f"{harmonized_prefix}|{missing}",
                raise_if_mismatch=False,
            )

            if not sector_inferred.empty:
                harmonised_df = harmonised_df.append(sector_inferred, inplace=False)

    # The remainder of the program should be fairly standardised
    # __________________________________________________________
    still_to_infill = harmonised_df
    infilled = None
    for ind, lead in enumerate(leader_lists):
        LOGGER.info("Infilling using %s as the lead variable", lead)
        to_infill, still_to_infill = split_df(
            still_to_infill, variable=harmonized_prefix + "|" + lead[0]
        )

        if not to_infill:
            LOGGER.info("Nothing to infill")
            continue

        LOGGER.info("Interpolating data to infill")
        to_infill = to_infill.interpolate(output_timesteps, inplace=False)

        if lead == ["Emissions|CO2"]:
            _, missing_energy = split_df(
                to_infill, variable=f"{harmonized_prefix}|{co2_energy}"
            )
            if not missing_energy.empty:
                # infill CO2 energy for scenarios that have CO2 total but no energy

                if co2_afolu in missing_energy.variable:
                    # We have somehow ended up with CO2 total and AFOLU but
                    # not energy, even though we should have calculated energy
                    # from total and AFOLU above
                    raise AssertionError(
                        "CO2 energy should have been calculated earlier"
                    )

                infilled_energy = _infill_variables(
                    types_of_cruncher[ind],
                    [co2_energy],
                    missing_energy,
                    database,
                    lead,
                    output_timesteps,
                    old_prefix=harmonized_prefix,
                )

                # calculate CO2 AFOLU as difference between energy and total
                # to preserve total and harmonisation
                afolu_inferred = _diff_variables(
                    infilled_energy,
                    co2_total,
                    co2_energy,
                    co2_afolu,
                )

                infilled = _add_to_infilled(infilled, infilled_energy)
                infilled = _add_to_infilled(infilled, afolu_inferred)

        for cruncherh, variables, database_here in (
            (types_of_cruncher[ind], qrw_variables_list, database),
            (fgas_cfc_cruncher, fgas_cfc_variables_list, database),
            (
                cfcs_and_other_variables_cruncher,
                cfcs_and_other_variables_list,
                database_cfcs,
            ),
        ):
            infilled_variables = _infill_variables(
                cruncherh,
                variables,
                to_infill,
                database_here,
                lead,
                output_timesteps,
                old_prefix=harmonized_prefix,
            )
            infilled = _add_to_infilled(infilled, infilled_variables)

    if infilled is None:
        raise ValueError("No infilling occured. Check input emissions")

    LOGGER.info("Converting HFC/PFC units back from CO2-equivalent")
    if convert_hfc_units:
        infilled = convert_co2_equiv_to_kt_gas(infilled, "*|HFC|*")
    if convert_pfc_units:
        infilled = convert_co2_equiv_to_kt_gas(infilled, "*|PFC|*")

    # We want to ensure that the original data is preserved as it was entered and that a
    # complete copy of the completed data is tagged as such.
    if infilled_data_prefix:
        infilled = infilled.data
        infilled["variable"] = infilled_data_prefix + "|" + infilled["variable"]
        infilled = pyam.IamDataFrame(infilled)

    # We also want a clone of the original preserved data, unless nothing changed
    if not pyam.compare(infilled, to_fill_orig).empty:
        infilled = infilled.append(to_fill_orig)
    else:
        LOGGER.warning(
            "The data was already complete and in the correct format. It has not changed"
        )

    out = infilled.filter(
        variable="*Kyoto*", keep=False
    )  # ad-hoc fix to ensure no Kytoto GWP100 coming in the infilling process

    # remove any infilled CO2 total but return so we can use it in the tests (
    # this is a hack which should be removed in future but is important now
    # while our functions are still pretty big)
    co2_total = out.filter(variable="*Infilled*Emissions|CO2")
    # Get "Emissions|CO2" of the infiller database of the used models, scenarios and regions
    co2_infiller_db = database.filter(
        variable="Emissions|CO2",
        model=list(set(out["model"])),
        scenario=list(set(out["scenario"])),
        region=list(set(out["region"])),
    )
    out = out.filter(variable="*Infilled*Emissions|CO2", keep=False)

    return out, co2_infiller_db, co2_total


def _infill_variables(
    cruncher, variables, to_infill, db, lead, output_timesteps, old_prefix
):
    """
    Start core infilling run, using silicone.multiple_infillers.infill_all_required_variables

    Parameters
    ----------
    cruncher : str
        Infilling method

    variables : list
        List of required variables to infill

    to_infill : :class:`pyam.IamDataFrame`
        Emissions data to be infilled

    db : :class:`pyam.IamDataFrame`
        The infilling database

    lead : str
        Lead infiller variable

    output_timesteps : list
        List of required output timesteps

    old_prefix : str
        The prefix of harmonized emissions, which will be replaced by a prefix
        for the infilled emissions variables.

    Returns
    -------
    :class:`pyam.IamDataFrame`
        Infilled emissions.
    """
    LOGGER.info("Infilling using cruncher %s", cruncher)
    LOGGER.info("Infilling %s", variables)
    infilled_variables = infill_all_required_variables(
        to_infill.copy(),
        db,
        lead,
        required_variables_list=variables,
        cruncher=cruncher,
        output_timesteps=output_timesteps,
        to_fill_old_prefix=old_prefix,
        check_data_returned=True,
    )
    del infilled_variables.meta["already_filled"]

    return infilled_variables


def _add_to_infilled(infilled, infilled_variables):
    """
    Helper function which takes two dataframes, and binds them together.

    Parameters
    ----------
    infilled : :class:`pyam.IamDataFrame`
        An IamDataFrame.
    infilled_variables : str, None
        An IamDataFrame.

    Returns
    -------
    :class:`pyam.IamDataFrame`
        An IamDataFrame.
    """
    if infilled is not None:
        infilled = infilled.timeseries()
        infilled_variables = infilled_variables.timeseries()
        keep_idx = infilled_variables.index.difference(infilled.index)
        if keep_idx.empty:
            LOGGER.debug("No timeseries infilled")
            return infilled

        infilled = pyam.IamDataFrame(
            pd.concat([infilled, infilled_variables.loc[keep_idx]])
        )

    else:
        infilled = infilled_variables

    return infilled


def load_csv_or_xlsx_for_one_region(file, sheet):
    """
    This loads data from either a csv or an xls(x) file and checks that it has only a
    single region.

    Parameters
    ----------
    file : str, None
        The (relative or absolute) file address of the file to load
    sheet : str, None
        If file is a csv, use None. Otherwise, the sheet name to read from the file.

    Returns
    -------
    :class:`pyam.IamDataFrame`
        The information in the file.
    """
    # TODO: loading databases with pyam is slow because of reshaping
    if sheet:
        my_df = pyam.IamDataFrame(file, sheet_name=sheet).data
    else:
        my_df = pyam.IamDataFrame(file).data

    if my_df["region"].nunique() > 1:
        raise AssertionError("Multiple regions must be infilled separately")

    return my_df


def postprocess_infilled_for_climate(df_infilled, prefix, start_year=2015):
    """
    Helper function that takes a set of infilled emissions data, adds a provided
    prefix, and filters out the scenarios that are appropriately infilled by checking
    both for a minimum set of years of data and checking that there are no non-co2
    negative emissions caused by the infilling method.

    Parameters
    ----------
    df_infilled : :class:`pyam.IamDataFrame`
        Infilled data.
    prefix : str
        Prefix used for the variable names

    Returns
    -------
    :class:`pyam.IamDataFrame`
        Checked and reformatted infilled data.
    """
    LOGGER.info("Post-processing for climate models")

    def _infilled_name(v):
        return "|".join([prefix, "Infilled", v])

    required_vars = {
        _infilled_name("Emissions|BC"),
        _infilled_name("Emissions|CH4"),
        # _infilled_name("Emissions|CO2"),
        # _infilled_name("Emissions|CO2|Other"),
        # _infilled_name("Emissions|CO2|Waste"),
        _infilled_name("Emissions|CH4"),
        _infilled_name("Emissions|CO"),
        _infilled_name("Emissions|CO2|AFOLU"),
        _infilled_name("Emissions|CO2|Energy and Industrial Processes"),
        # _infilled_name("Emissions|F-Gases"),
        # _infilled_name("Emissions|HFC"),
        _infilled_name("Emissions|HFC|HFC125"),
        _infilled_name("Emissions|HFC|HFC134a"),
        _infilled_name("Emissions|HFC|HFC143a"),
        _infilled_name("Emissions|HFC|HFC227ea"),
        _infilled_name("Emissions|HFC|HFC23"),
        _infilled_name("Emissions|HFC|HFC245ca"),  # not in historical dataset (RCMIP)
        # _infilled_name("Emissions|HFC|HFC245fa"),
        _infilled_name("Emissions|HFC|HFC32"),
        _infilled_name("Emissions|HFC|HFC43-10"),
        _infilled_name("Emissions|N2O"),
        _infilled_name("Emissions|NH3"),
        _infilled_name("Emissions|NOx"),
        _infilled_name("Emissions|OC"),
        # _infilled_name("Emissions|PFC"),
        _infilled_name("Emissions|PFC|C2F6"),
        _infilled_name("Emissions|PFC|C6F14"),
        _infilled_name("Emissions|PFC|CF4"),
        _infilled_name("Emissions|SF6"),
        _infilled_name("Emissions|Sulfur"),
        _infilled_name("Emissions|VOC"),
    }
    # mark the scenarios that are not sufficiently infilled for climate assessment, and filter scenarios
    required_years = list(range(start_year, 2100 + 1))
    LOGGER.info("Checking infilled results have required years and variables")
    for (model, scenario), msdf in (
        df_infilled.filter(year=required_years)
        .timeseries()
        .groupby(["model", "scenario"])
    ):
        has_all_years = set(msdf.columns) == set(required_years)
        has_all_variables = not required_vars - set(
            msdf.index.get_level_values("variable")
        )
        if not (has_all_years and has_all_variables):
            LOGGER.info("Removing %s %s", model, scenario)
            df_infilled = df_infilled.filter(model=model, scenario=scenario, keep=False)

    # in case non-CO2 negatives have been introduced here, we want to know!
    LOGGER.info("Check that there are no non-CO2 negatives introduced by infilling")
    df_infilled_negatives_checked = check_negatives(df_infilled, prefix=f"{prefix}*")
    pdt.assert_frame_equal(
        df_infilled.timeseries().T,
        df_infilled_negatives_checked.timeseries().T,
        check_like=True,
    )

    return df_infilled
