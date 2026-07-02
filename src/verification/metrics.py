import numpy as np
import xarray as xr
from sklearn.metrics import roc_auc_score


def compute_verification_metrics(
    cross_validation: dict[str, dict[str, dict[str, xr.DataArray]]],
    type_calibration: str,
) -> dict[str, dict[str, xr.DataArray]]:

    forecast = cross_validation["forecast"]
    obs = cross_validation["obs"]

    metrics = {}

    for period in forecast:

        forecast_period = forecast[period]
        obs_period = obs[period]

        positive_product, positive_threshold = get_positive_event_names(
            type_calibration
        )

        bin_positive = obs_period["total"] >= obs_period[positive_threshold]
        bin_lower = obs_period["total"] <= obs_period["tinf"]
        bin_upper = obs_period["total"] >= obs_period["tsup"]

        correlation = compute_correlation_skill(
            obs_period["anomaly"],
            forecast_period["anomaly"],
        )

        phase, amplitude = compute_msss_phase_amplitude(
            forecast_period["anomaly"],
            obs_period["anomaly"],
            correlation,
        )

        metrics[period] = {
            "corskill": correlation,
            "arocmed": compute_auroc(
                bin_positive,
                forecast_period[positive_product],
            ),
            "aroctinf": compute_auroc(
                bin_lower,
                forecast_period["below_tinf"],
            ),
            "aroctsup": compute_auroc(
                bin_upper,
                forecast_period["above_tsup"],
            ),
            "mssskill": compute_msss(
                forecast_period["anomaly"],
                obs_period["anomaly"],
            ),
            "msssfase": phase,
            "msssamplitude": amplitude,
            "bias": compute_bias(
                forecast_period["total"],
                obs_period["total"],
            ),
        }

    return metrics


def get_positive_event_names(
    type_calibration: str,
) -> tuple[str, str]:

    if type_calibration == "cox":
        return "above_median", "median"

    return "above_mean", "mean"


def compute_correlation_skill(
    obs_anomaly: xr.DataArray,
    forecast_anomaly: xr.DataArray,
) -> xr.DataArray:

    corr = xr.corr(
        forecast_anomaly,
        obs_anomaly,
        dim="year",
    )

    return corr.clip(min=0)


def compute_auroc(
    binary_obs: xr.DataArray,
    probability: xr.DataArray,
) -> xr.DataArray:

    return xr.apply_ufunc(
        _roc_auc_1d,
        binary_obs,
        probability,
        input_core_dims=[["year"], ["year"]],
        output_core_dims=[[]],
        vectorize=True,
        dask="parallelized",
        output_dtypes=[float],
    )


def _roc_auc_1d(
    binary_obs: np.ndarray,
    probability: np.ndarray,
) -> float:

    valid = np.isfinite(binary_obs) & np.isfinite(probability)

    if valid.sum() < 3:
        return np.nan

    binary = binary_obs[valid].astype(int)
    probs = probability[valid]

    if np.unique(binary).size < 2:
        return np.nan

    try:
        return float(
            roc_auc_score(
                binary,
                probs,
            )
        )

    except ValueError:
        return np.nan


def compute_msss(
    forecast_anomaly: xr.DataArray,
    obs_anomaly: xr.DataArray,
) -> xr.DataArray:

    forecast_mse = (
        (forecast_anomaly - obs_anomaly) ** 2
    ).mean("year")

    reference_mse = (
        obs_anomaly ** 2
    ).mean("year")

    return 1 - (forecast_mse / reference_mse)


def compute_bias(
    forecast_total: xr.DataArray,
    obs_total: xr.DataArray,
) -> xr.DataArray:

    return (
        forecast_total - obs_total
    ).mean("year")


def compute_msss_phase_amplitude(
    forecast_anomaly: xr.DataArray,
    obs_anomaly: xr.DataArray,
    correlation: xr.DataArray,
) -> tuple[xr.DataArray, xr.DataArray]:

    forecast_std = forecast_anomaly.std("year")
    obs_std = obs_anomaly.std("year")

    ratio = forecast_std / obs_std

    phase = 2 * ratio * correlation
    amplitude = ratio ** 2

    return phase, amplitude


def build_diagram_fields(
    cross_validation: dict[str, dict[str, dict[str, xr.DataArray]]],
    type_calibration: str,
) -> dict[str, dict[str, xr.DataArray]]:

    forecast = cross_validation["forecast"]
    obs = cross_validation["obs"]

    diagram_fields = {}

    for period in forecast:

        positive_product, positive_threshold = get_positive_event_names(
            type_calibration
        )

        diagram_fields[period] = {
            "probmed": forecast[period][positive_product],
            "probtinf": forecast[period]["below_tinf"],
            "probtsup": forecast[period]["above_tsup"],
            "binobsmed": (
                obs[period]["total"] >= obs[period][positive_threshold]
            ).astype(int),
            "binobstinf": (
                obs[period]["total"] <= obs[period]["tinf"]
            ).astype(int),
            "binobstsup": (
                obs[period]["total"] >= obs[period]["tsup"]
            ).astype(int),
        }

    return diagram_fields
