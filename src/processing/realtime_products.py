
import xarray as xr
from src.observation import Observation
from src.hindcast import Hindcast
from src.forecast import Forecast
from src.calibration.cox import get_cox_calibration_results
from src.calibration.linear_regression import get_linear_regression_calibr_results
from src.calibration.no_calibration import get_no_calibration_results

"""Nesse módulo está a função que gera as previsões em tempo-real calibradas e não calibradas."""

def build_realtime_products(
    base: str,
    model_target: str,
    var: str,
    year_fcst: int, 
    month_fcst: int,
    models_available: list[str]
) -> tuple[
    dict[str, dict[str, dict[str, xr.DataArray]]],
    dict[str, dict[str, xr.DataArray]],
]:

    # ------------------
    # Read data
    # ------------------

    obs_statistics = Observation(
        base,
        var,
        month_fcst
    ).compute_statistics()

    hcst_statistics =  Hindcast(
        base,
        var,
        month_fcst,
        models_available
    ).compute_statistics(model_target)

    realtime_forecast = Forecast(
        base,
        var,
        year_fcst,
        month_fcst,
        models_available
    ).get_forecast(model_target)


    # ------------------
    # Calibrations
    # ------------------

    results_cox = get_cox_calibration_results(
            obs_statistics,
            hcst_statistics,
            realtime_forecast,
            compute_prec_products = var == "prec"
    )

    results_regression = get_linear_regression_calibr_results(
            obs_statistics,
            hcst_statistics,
            realtime_forecast,
            var
    )

    results_no_calibration = get_no_calibration_results(
        hcst_statistics,
        realtime_forecast
    )

    # ------------------
    # Group results
    # ------------------
    results = {
        "cox": results_cox,
        "regr": results_regression,
        "nocalib": results_no_calibration
    }

    return results, obs_statistics
