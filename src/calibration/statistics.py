import xarray as xr 
from src.config.loader import PARAMETERS_RUN
from src.observation.observation_seasonal import Observation
from src.hindcast.hindcast_seasonal import Hindcast


def load_obs_statistics(
        base: str,
        variable: str,
        month_forecast: int
):
    return Observation(
        base,
        variable,
        month_forecast
    ).calculate_observation_statistics()


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
    ).calculate_hindcast_statistics(model)


def correlation_model(
        obs_anomaly_dict: dict[str, xr.DataArray], 
        hcst_anomaly_dict: dict[str, xr.DataArray]
) -> dict[str, xr.DataArray]:
    ''' Cálculo da correlação entre anomalia dos hindcasts e observações '''

    periods = PARAMETERS_RUN["periods"]

    corr_periods = {}

    for period in periods:
        corr_periods[period] = xr.corr(
            obs_anomaly_dict[period], 
            hcst_anomaly_dict[period], 
            dim="year"
        ).clip(min = 0)

    return corr_periods