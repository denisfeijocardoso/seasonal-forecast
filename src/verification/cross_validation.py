import xarray as xr
import numpy as np

def leave_one_year_out(
    data: xr.DataArray,
    years: np.ndarray
):
    
    for year in years:

        climatology = data.drop_sel(
            year=years != year
        )

        target_year = data.sel(
            year=year
        )

        yield year, climatology, target_year

#Aí sua verificação inteira vira:
for year, hcst_climatology, hcst_target in leave_one_year_out(hcst):

    obs_statistics = ...

    hcst_statistics = ...

    forecast = hcst_test

    results = get_linear_regression_calibr_results(
        obs_statistics,
        hcst_statistics,
        forecast
    )