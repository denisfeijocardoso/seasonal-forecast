import xarray as xr
from src.config.loader import get_periods_aggregation

''' Nesse método estão as funções responsáveis por gerar as previsões em tempo-real 
sem aplicar nennhum método de calibração. '''

def get_no_calibration_results(
        hcst_statistics: dict[str, xr.DataArray],
        realtime_forecast: dict[str, xr.DataArray]
) -> dict[str, dict[str, xr.DataArray]]:
    
    periods = get_periods_aggregation()

    results = {}
    
    for period in periods:

        hcst_mean = hcst_statistics[period]["mean"]

        rename_dims = {
            dim: name
            for dim, name in {"Y": "lat", "X": "lon"}.items()
            if dim in realtime_forecast[period].dims
        }
        forecast = realtime_forecast[period].rename(rename_dims)
        
        forecast_anomaly = forecast - hcst_mean

        results[period] = {
            "anomaly": forecast_anomaly,
            "total": forecast
        }

    return results
