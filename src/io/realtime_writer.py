import xarray as xr
import calendar
import logging
from src.config.loader import get_periods_aggregation
from .path_builder import build_output_path
from src.config.config_models import build_model_dir_name

logger = logging.getLogger(__name__)

periods = get_periods_aggregation()

def write_results_netcdf(
        results: dict[str, dict[str, xr.DataArray]],      
        base: str,
        model: str,
        var: str,
        type_calibration: str,
        year_fcst: int,
        month_fcst: int,
):
    """
    Salva todos os resultados da calibração em NetCDF.
    """

    output_path = build_output_path(
        base=base,
        model=model,
        type_calibration=type_calibration,
        year_fcst=year_fcst,
        month_fcst=month_fcst,
    )

    output_path.mkdir(
        parents=True,
        exist_ok=True
    )    
    
    name_model_dir = build_model_dir_name(model)

    fcst_date = f"{year_fcst}{month_fcst:02d}0100"

    period_dates = compute_period_names(
        year_fcst,
        month_fcst
    ) 

    if type_calibration != "nocalib":
        calibration = f"calibrated_{type_calibration}_"
    else:
        calibration = "nocalib_"

    for period, period_results in results.items():

            for product_name, data in period_results.items():

                file_name = (
                    f"fcst_"
                    f"{var}_"
                    f"{product_name}_"
                    f"{period}_"
                    f"{name_model_dir}_"
                    f"{calibration}"
                    f"{fcst_date}.nc"
                ) 

                file_path = output_path / file_name

                print(period, product_name, type(data))

                ds = build_dataset(
                     data,
                     product_name
                )

                ds = add_global_attributes(
                    ds,
                    base,
                    model,
                    var,
                    type_calibration,
                    year_fcst,
                    month_fcst,
                )

                ds = add_products_attributes(ds)

                ds.attrs["description"] = (
                    f"{product_name} generated from "
                    f"{type_calibration} calibration"
                )

                ds.attrs["source"] = (
                    f"{name_model_dir} seasonal forecast"
                )

                ds.attrs["history"] = (
                    f"Issued: {period_dates['mnth00'].upper()} "
                    f"For: {period_dates[period].upper()}"
                )

                ds.to_netcdf(file_path)

                logging.info(f"Arquivo gerado - {year_fcst} {month_fcst}: {file_path}")


def write_observation_statistics_netcdf(
        obs_statistics: dict[str, dict[str, xr.DataArray]],
        base: str,
        model: str,
        var: str,
        type_calibration: str,
        year_fcst: int,
        month_fcst: int,
) -> None:
    """
    Salva estatísticas observacionais necessárias para as curvas do multimodelo.
    """

    if model != "multimodel":
        return

    if type_calibration not in {"regr", "cox"}:
        return

    output_path = build_output_path(
        base=base,
        model=model,
        type_calibration=type_calibration,
        year_fcst=year_fcst,
        month_fcst=month_fcst,
    )

    output_path.mkdir(
        parents=True,
        exist_ok=True
    )

    name_model_dir = build_model_dir_name(model)
    fcst_date = f"{year_fcst}{month_fcst:02d}0100"
    period_dates = compute_period_names(
        year_fcst,
        month_fcst
    )
    calibration = f"calibrated_{type_calibration}_"

    product_map = {
        "obsmean": "mean",
        "obsstd": "std",
        "obsmedian": "median",
        "obsiqr": "iqr",
        "obstotal": "total",
        "obstercinf": "tinf",
        "obstercsup": "tsup",
    }

    for period, period_statistics in obs_statistics.items():
        for product_name, statistic_name in product_map.items():
            if statistic_name not in period_statistics:
                continue

            data = period_statistics[statistic_name]
            file_name = (
                f"fcst_"
                f"{var}_"
                f"{product_name}_"
                f"{period}_"
                f"{name_model_dir}_"
                f"{calibration}"
                f"{fcst_date}.nc"
            )

            file_path = output_path / file_name

            ds = build_dataset(
                data,
                product_name
            )

            ds = add_global_attributes(
                ds,
                base,
                model,
                var,
                type_calibration,
                year_fcst,
                month_fcst,
            )

            ds = add_products_attributes(ds)

            ds.attrs["description"] = (
                f"{product_name} generated from observational climatology"
            )

            ds.attrs["source"] = "observational climatology"

            ds.attrs["history"] = (
                f"Issued: {period_dates['mnth00'].upper()} "
                f"For: {period_dates[period].upper()}"
            )

            ds.to_netcdf(file_path)

            logging.info(
                "Arquivo observacional gerado - %s %s: %s",
                year_fcst,
                month_fcst,
                file_path,
            )


def build_dataset(
    data: xr.DataArray,
    product_name: str,
) -> xr.Dataset:

    da = data.copy()

    da = add_coordinate_attributes(da)

    da.name = product_name

    ds = da.to_dataset()

    return ds

def add_coordinate_attributes(
    da: xr.DataArray,
) -> xr.DataArray:

    if "lon" in da.coords:
        da["lon"].attrs.update({
            "standard_name": "longitude",
            "units": "degrees_east",
            "axis": "X",
        })

    if "lat" in da.coords:
        da["lat"].attrs.update({
            "standard_name": "latitude",
            "units": "degrees_north",
            "axis": "Y",
        })

    return da

def add_global_attributes(
    ds: xr.Dataset,
    base: str,
    model: str,
    var: str,
    type_calibration: str,
    year_fcst: int,
    month_fcst: int,
) -> xr.Dataset:

    ds.attrs = {

        "base": base,

        "model": model,

        "variable": var,

        "calibration": type_calibration,

        "forecast_year": year_fcst,

        "forecast_month": month_fcst,

        "institution": "CPTEC/INPE",

    }

    return ds

def add_products_attributes(
    ds: xr.Dataset
) -> xr.Dataset:

    attrs = {

        # ------------------------
        # Produtos comuns
        # ------------------------

        "correlation": {
            "long_name": "Anomaly correlation",
            "units": "1"
        },

        "below_tinf": {
            "long_name": "Probability below lower tercile",
            "units": "1"
        },

        "below_tsup": {
            "long_name": "Probability below upper tercile",
            "units": "1"
        },

        "above_tinf": {
            "long_name": "Probability above lower tercile",
            "units": "1"
        },

        "above_tsup": {
            "long_name": "Probability above upper tercile",
            "units": "1"
        },

        "prob_central": {
            "long_name": "Probability within central tercile",
            "units": "1"
        },

        "mlterciles": {
            "long_name": "Most likely tercile"
        },

        "prob-exceedance": {
            "long_name": "Probability of exceedance",
            "units": "1"
        },

        "percentilemm": {
            "long_name": "Forecast precipitation percentile value",
            "units": "mm"
        },

        "obsmean": {
            "long_name": "Observed climatological mean"
        },

        "obsstd": {
            "long_name": "Observed climatological standard deviation"
        },

        "obsmedian": {
            "long_name": "Observed climatological median"
        },

        "obsiqr": {
            "long_name": "Observed climatological interquartile range"
        },

        "obstotal": {
            "long_name": "Observed climatological values"
        },

        "obstercinf": {
            "long_name": "Observed climatological lower tercile"
        },

        "obstercsup": {
            "long_name": "Observed climatological upper tercile"
        },

        # ------------------------
        # Verificação
        # ------------------------

        "corskill": {
            "long_name": "Anomaly correlation skill",
            "units": "1"
        },

        "mssskill": {
            "long_name": "Mean squared skill score",
            "units": "1"
        },

        "msssfase": {
            "long_name": "MSSS phase component",
            "units": "1"
        },

        "msssamplitude": {
            "long_name": "MSSS amplitude component",
            "units": "1"
        },

        "bias": {
            "long_name": "Forecast bias"
        },

        "arocmed": {
            "long_name": "Area under ROC curve for positive anomaly",
            "units": "1"
        },

        "aroctinf": {
            "long_name": "Area under ROC curve for lower tercile",
            "units": "1"
        },

        "aroctsup": {
            "long_name": "Area under ROC curve for upper tercile",
            "units": "1"
        },

        "probmed": {
            "long_name": "Forecast probability for positive anomaly",
            "units": "1"
        },

        "probtinf": {
            "long_name": "Forecast probability for lower tercile",
            "units": "1"
        },

        "probtsup": {
            "long_name": "Forecast probability for upper tercile",
            "units": "1"
        },

        "binobsmed": {
            "long_name": "Observed binary event for positive anomaly",
            "units": "1"
        },

        "binobstinf": {
            "long_name": "Observed binary event for lower tercile",
            "units": "1"
        },

        "binobstsup": {
            "long_name": "Observed binary event for upper tercile",
            "units": "1"
        },

        # ------------------------
        # Regressão linear
        # ------------------------

        "mean": {
            "long_name": "Calibrated forecast mean"
        },

        "total": {
            "long_name": "Calibrated forecast total"
        },

        "stdev": {
            "long_name": "Calibrated forecast standard deviation"
        },

        "anomaly": {
            "long_name": "Calibrated forecast anomaly"
        },

        "above_mean": {
            "long_name": "Probability above climatological mean",
            "units": "1"
        },

        # ------------------------
        # Cox
        # ------------------------

        "varx": {
            "long_name": "Cox transformed variable"
        },

        "proby_clim": {
            "long_name": "Climatological cumulative probability"
        },

        "proby_fcst": {
            "long_name": "Forecast cumulative probability"
        },

        "coef_beta": {
            "long_name": "Cox calibration beta coefficient"
        },

        "median": {
            "long_name": "Calibrated forecast median"
        },

        "anomaly": {
            "long_name": "Calibrated forecast anomaly"
        },

        "iqr": {
            "long_name": "Interquartile range"
        },

        "above_median": {
            "long_name": "Probability above median",
            "units": "1"
        }

    }

    for product_name in ds.data_vars:

        if product_name in attrs:

            ds[product_name].attrs.update(
                attrs[product_name]
            )

    return ds

def compute_period_names(
    year_fcst: int,
    month_fcst: int
) -> dict[str, str]:

    result = {}

    for period, (start, end) in periods.items():

        months = []

        for offset in range(start, end):

            month = month_fcst + offset
            year = year_fcst

            while month > 12:
                month -= 12
                year += 1

            months.append((month, year))

        if len(months) == 1:

            m, y = months[0]

            result[period] = (
                f"{calendar.month_abbr[m]} {y}"
            )

        else:

            season = "".join(
                calendar.month_abbr[m][0].upper()
                for m, _ in months
            )

            result[period] = (
                f"{season} {months[0][1]}"
            )

    return result
