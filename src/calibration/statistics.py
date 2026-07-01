import xarray as xr 
import numpy as np
from src.observation import Observation
from src.hindcast import Hindcast


def load_obs_statistics(
        base: str,
        variable: str,
        month_forecast: int
):
    return Observation(
        base,
        variable,
        month_forecast
    ).compute_statistics()


def load_hcst_statistics(
        base: str,
        variable: str,
        month_forecast: int,
        models_available: list[int],
        model: str
        
):
    return Hindcast(
        base,
        variable,
        month_forecast,
        models_available
    ).compute_statistics(model)

def compute_anomaly_correlation(
        obs_anomaly: xr.DataArray, 
        hcst_anomaly: xr.DataArray
) -> xr.DataArray:
    ''' Cálculo da correlação entre anomalia dos hindcasts e observações '''

    corr_period = (
        xr.corr(
            obs_anomaly, 
            hcst_anomaly, 
            dim="year"
        )
        .fillna(0)
        .clip(min = 0)
    )

    return corr_period

def compute_most_likely_terciles(
    prob_below: xr.DataArray,
    prob_central: xr.DataArray,
    prob_above: xr.DataArray
) -> xr.DataArray:

    probs = xr.concat(
        [prob_below, prob_central, prob_above],
        dim="tercile"
    )

    all_nan = probs.isnull().all(dim="tercile")

    probs_filled = probs.fillna(-np.inf)

    max_idx = probs_filled.argmax(dim="tercile")

    max_val = probs.max(
        dim="tercile",
        skipna=True
    )

    prob_tercile = xr.zeros_like(max_val)

    prob_tercile = xr.where(
        max_idx == 0,
        -max_val,
        prob_tercile
    )

    prob_tercile = xr.where(
        max_idx == 2,
        max_val,
        prob_tercile
    )

    prob_tercile = xr.where(
        all_nan,
        np.nan,
        prob_tercile
    )

    return prob_tercile
