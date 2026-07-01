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

        realtime_forecast[period] = realtime_forecast[period].rename({
            "Y": "lat",
            "X": "lon"
        })
        
        forecast_anomaly = realtime_forecast[period] - hcst_mean

        results[period] = {
            "anomaly": forecast_anomaly,
            "total": realtime_forecast[period]
        }

    return results