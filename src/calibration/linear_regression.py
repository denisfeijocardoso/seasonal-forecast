import xarray as xr
import numpy as np
from scipy.stats import norm
from .statistics import compute_most_likely_terciles, compute_anomaly_correlation
from src.config.loader import get_periods_aggregation
from src.observation import Observation
from src.hindcast import Hindcast
from src.forecast import Forecast

''' Nesse método estão as funções responsáveis por gerar as previsões em tempo-real 
calibradas através do método de regressão linear. Para os modelos individuais,
e também para o multimodelo (para os diferentes períodos de agregação).'''

def compute_calibration(
    obs_stats: dict[str, xr.DataArray], 
    hcst_stats: dict[str, xr.DataArray], 
    correlation: xr.DataArray,
    realtime_forecast: xr.DataArray
) -> dict[str, xr.DataArray]:
    ''' Calibração das previsões em tempo-real através do método de regressão linear'''

    obs_std  = obs_stats["std"]
    obs_mean = obs_stats["mean"]

    hcst_mean = hcst_stats["mean"]
    hcst_std = hcst_stats["std"]
    
    rename_dims = {
        dim: name
        for dim, name in {"Y": "lat", "X": "lon"}.items()
        if dim in realtime_forecast.dims
    }

    if rename_dims:
        realtime_forecast = realtime_forecast.rename(rename_dims)
    
    forecast_anomaly = realtime_forecast - hcst_mean

    prediction_signal = forecast_anomaly / hcst_std
    forecast_mean_standardized = prediction_signal * correlation 
    forecast_std = (obs_std) * (np.sqrt( 1 - (correlation ** 2))) 

    forecast_anomaly_calibrated = (
        forecast_mean_standardized * obs_std
    )

    forecast_mean_calibrated = (
        (forecast_anomaly_calibrated) + (obs_mean)
    )

    return {
        "anomaly": forecast_anomaly_calibrated,
        "mean": forecast_mean_calibrated, 
        "stdev": forecast_std,  
    }
    
def norm_cdf(x, mu, sigma):
    return norm(mu, sigma).cdf(x)   

def compute_probabilities(
    calibration: dict[str, xr.DataArray],
    obs_stats: dict[str, xr.DataArray], 
) -> dict[str, xr.DataArray]:

    #--- Probabilidade acima/abaixo da média (calibrada)
    below_mean = xr.apply_ufunc(
        norm_cdf,
        obs_stats["mean"],
        calibration["mean"], 
        calibration["stdev"],
        vectorize=True
    )

    above_mean = 1 - (below_mean)

    #--- Probabilidade acima/abaixo dos tercis (calibrada)
    below_tinf = xr.apply_ufunc(
        norm_cdf,
        obs_stats["tinf"],
        calibration["mean"], 
        calibration["stdev"],
        vectorize=True
    ).drop_vars("quantile", errors="ignore")

    above_tinf =  1 - below_tinf 

    below_tsup = xr.apply_ufunc(
        norm_cdf,
        obs_stats["tsup"],
        calibration["mean"], 
        calibration["stdev"],
        vectorize=True
    ).drop_vars("quantile", errors="ignore")

    above_tsup = 1 - below_tsup

    prob_central = below_tsup - below_tinf

    return{
        "above_mean": above_mean,
        "below_tinf": below_tinf,
        "below_tsup": below_tsup,
        "above_tinf": above_tinf,
        "above_tsup": above_tsup,
        "prob_central": prob_central
    }  

def compute_precipitation_results(
    calibration: dict[str, xr.DataArray],
) -> dict[str, xr.DataArray]:
    """
    Calcula:

    - Valores de precipitação (mm) correspondentes aos percentis
      20%, 50% e 80%.

    - Probabilidade de exceder limiares de precipitação
      (10, 20, ..., 600 mm).
    """

    probability_values = [20, 50, 80]

    threshold_values = [
        10, 20, 40, 60, 80, 100,
        150, 200, 250, 300,
        400, 500, 600,
    ]

    probabilities = xr.DataArray(
        np.array(probability_values) / 100,
        dims="probability",
        coords={"probability": probability_values},
    )

    z = xr.apply_ufunc(
        norm.ppf,
        probabilities
    )

    mean_prob, z = xr.broadcast(
        calibration["mean"],
        z
    )

    std_prob, _ = xr.broadcast(
        calibration["stdev"],
        z
    )

    percentile_mm = mean_prob + std_prob * z

    thresholds_mm = xr.DataArray(
        threshold_values,
        dims="thresholds",
        coords={"thresholds": threshold_values},
    )

    mean_thr, thresholds = xr.broadcast(
        calibration["mean"],
        thresholds_mm,
    )

    std_thr, _ = xr.broadcast(
        calibration["stdev"],
        thresholds_mm,
    )

    prob_exceedance = xr.DataArray(
        1 - norm(mean_thr, std_thr).cdf(thresholds),
        coords=mean_thr.coords,
        dims=mean_thr.dims,
    )

    results = {
        f"percent{p}": percentile_mm.sel(
            probability=p,
            drop=True,
        )
        for p in probability_values
    }

    results.update({
        f"prob{t}mm": prob_exceedance.sel(
            thresholds=t,
            drop=True,
        )
        for t in threshold_values
    })

    return results

def get_linear_regression_calibr_results(
        obs_statistics: dict[str, dict[str, xr.DataArray]],
        hcst_statistics: dict[str, dict[str, xr.DataArray]],
        realtime_forecast: dict[str, xr.DataArray]      
) -> dict[str, dict[str, xr.DataArray]]:

    periods = get_periods_aggregation()

    results = {}

    for period in periods:
        obs = obs_statistics[period]
        hcst = hcst_statistics[period]
        fcst = realtime_forecast[period]

        correlation = compute_anomaly_correlation(
            obs["anom"],
            hcst["anom"]
        )

        calibration = compute_calibration(
            obs,
            hcst, 
            correlation,
            fcst,
        )

        probabilities = compute_probabilities(
            calibration,
            obs
        )

        most_likely_terciles = compute_most_likely_terciles(
            probabilities["below_tinf"],
            probabilities["prob_central"],
            probabilities["above_tsup"]
        )

        precipitation_results = compute_precipitation_results(calibration)

        results[period] = {
            "correlation": correlation,
            "total": calibration["mean"],
            "stdev": calibration["stdev"],
            "anomaly": calibration["anomaly"],
            "above_mean": probabilities["above_mean"],
            "below_tinf": probabilities["below_tinf"],
            "below_tsup": probabilities["below_tsup"],
            "above_tinf": probabilities["above_tinf"],
            "above_tsup": probabilities["above_tsup"],
            "mlterciles": most_likely_terciles,
            **precipitation_results
        }        

    return results
