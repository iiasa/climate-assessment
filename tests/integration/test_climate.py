from climate_assessment.climate import climate_assessment


def test_climate_assessment_percentiles(
    fair_slim_configs_filepath,
    fair_common_configs_filepath,
    tmpdir,
    test_data_dir,
):
    temp_thresholds_1 = (1.5, 2.0)
    temp_thresholds_2 = (1.5, 1.6, 1.7)

    peak_percentiles_1 = (5, 10)
    peak_percentiles_2 = (5, 50, 95)

    percentiles_1 = (17, 83)
    percentiles_2 = (25, 50, 75)

    df = pyam.IamDataFrame(os.path.join(
        test_data_dir,
        "workflow-fair",
        "ex2_harmonized_infilled.csv",
    ))

    common_kwargs = dict(
        df=df,
        key_string="test_climate_assessment_percentiles",
        outdir=tmpdir,
        model="fair",
        num_cfgs=30,
        probabilistic_file=fair_slim_configs_filepath,
        fair_extra_config=fair_common_configs_filepath,
        test_run=True,
    )

    res_1 = climate_assessment(
        **common_kwargs,
        temp_thresholds=temp_thresholds_1,
        peak_percentiles=peak_percentiles_1,
        percentiles=percentiles_1,
    )

    res_2 = climate_assessment(
        **common_kwargs,
        temp_thresholds=temp_thresholds_2,
        peak_percentiles=peak_percentiles_2,
        percentiles=percentiles_2,
    )

    assert False, "Test different quantiles actually calculated"
