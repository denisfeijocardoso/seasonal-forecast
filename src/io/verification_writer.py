import logging
from pathlib import Path
import xarray as xr
from src.config.config_models import build_model_dir_name, get_multimodel_version
from src.config.paths import PATH_POSPROC
from src.io.realtime_writer import add_products_attributes, compute_period_names

logger = logging.getLogger(__name__)


MAP_PRODUCTS = [
    "corskill",
    "mssskill",
    "msssfase",
    "msssamplitude",
    "bias",
    "arocmed",
    "aroctinf",
    "aroctsup",
]

DIAGRAM_PRODUCTS = [
    "probmed",
    "probtinf",
    "probtsup",
    "binobsmed",
    "binobstinf",
    "binobstsup",
]


def write_verification_netcdf(
    metrics: dict[str, dict[str, xr.DataArray]],
    diagram_fields: dict[str, dict[str, xr.DataArray]],
    base: str,
    model: str,
    var: str,
    type_calibration: str,
    year_ref: int,
    month_hcst: int,
) -> None:

    output_path = build_verification_output_path(
        base,
        model,
        type_calibration,
    )

    output_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    period_dates = compute_period_names(
        year_ref,
        month_hcst,
    )

    for period, period_metrics in metrics.items():

        for product_name in MAP_PRODUCTS:
            write_product_dataset(
                period_metrics[product_name],
                output_path,
                product_name,
                period,
                base,
                model,
                var,
                type_calibration,
                year_ref,
                month_hcst,
                period_dates,
            )

        for product_name in DIAGRAM_PRODUCTS:
            write_product_dataset(
                diagram_fields[period][product_name],
                output_path,
                product_name,
                period,
                base,
                model,
                var,
                type_calibration,
                year_ref,
                month_hcst,
                period_dates,
            )


def build_verification_output_path(
    base: str,
    model: str,
    type_calibration: str,
) -> Path:

    version_multimodel = get_multimodel_version(base)
    name_model_dir = build_model_dir_name(model)

    return (
        PATH_POSPROC /
        base /
        f"v{version_multimodel}" /
        "verification" /
        type_calibration /
        name_model_dir
    )


def write_product_dataset(
    data: xr.DataArray,
    output_path: Path,
    product_name: str,
    period: str,
    base: str,
    model: str,
    var: str,
    type_calibration: str,
    year_ref: int,
    month_hcst: int,
    period_dates: dict[str, str],
) -> None:

    name_model_dir = build_model_dir_name(model)
    fcst_date = f"{year_ref}{month_hcst:02d}0100"

    if type_calibration == "nocalib":
        calibration_suffix = "nocalib"
    else:
        calibration_suffix = f"calibrated_{type_calibration}"

    file_name = (
        f"{var}_"
        f"{product_name}_"
        f"{period}_"
        f"{name_model_dir}_"
        f"{calibration_suffix}_"
        f"{fcst_date}.nc"
    )

    file_path = output_path / file_name

    da = prepare_dataarray(
        data,
        product_name,
    )

    ds = da.to_dataset()

    ds = add_products_attributes(ds)

    ds.attrs.update({
        "base": base,
        "model": model,
        "variable": var,
        "calibration": type_calibration,
        "verification_year_reference": year_ref,
        "forecast_month": month_hcst,
        "institution": "MMClima",
        "description": (
            f"{product_name} verification product for {type_calibration}"
        ),
        "source": f"{name_model_dir} seasonal hindcast cross-validation",
        "history": (
            f"Issued: {period_dates['mnth00'].upper()} "
            f"For: {period_dates[period].upper()}"
        ),
    })

    ds.to_netcdf(file_path)

    logger.info("Arquivo gerado: %s", file_path)


def prepare_dataarray(
    data: xr.DataArray,
    product_name: str,
) -> xr.DataArray:

    da = data.copy()

    if "year" in da.dims:
        da = da.rename({"year": "time"})
        da["time"].attrs.update({
            "long_name": "cross-validation target year",
            "units": "years",
        })

    if "lat" in da.coords:
        da["lat"].attrs.update({
            "standard_name": "latitude",
            "units": "degrees_north",
            "axis": "Y",
        })

    if "lon" in da.coords:
        da["lon"].attrs.update({
            "standard_name": "longitude",
            "units": "degrees_east",
            "axis": "X",
        })

    da.name = product_name

    return da
