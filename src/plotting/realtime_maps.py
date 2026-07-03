from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from src.plotting.palettes import forecast_palette
from src.plotting.seasonal_map_common import (
    BASE_PREFIX,
    MULTIMODEL_BASE_PREFIX,
    REGIONS,
    MapStyle,
    build_model_labels,
    calibration_file_suffix,
    calibration_output_suffix,
    forecast_date,
    history_title,
    input_dir,
    open_product_data,
    output_dir,
    render_map,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ForecastProduct:
    product_name: str
    figure_name: str


EXCEEDANCE_PRODUCTS = (
    "prob10mm",
    "prob20mm",
    "prob40mm",
    "prob60mm",
    "prob80mm",
    "prob100mm",
    "prob150mm",
    "prob200mm",
    "prob250mm",
    "prob300mm",
    "prob400mm",
    "prob500mm",
    "prob600mm",
)

FORECAST_PERIODS = (
    ("mnth", "mnth00"),
    ("mnth", "mnth01"),
    ("mnth", "mnth02"),
    ("mnth", "mnth03"),
    ("mnth", "mnth04"),
    ("seas", "seas00"),
    ("seas", "seas01"),
    ("seas", "seas02"),
)


def run_python_maps_realtime(
    base: str,
    model: str,
    var: str,
    type_calibration: str,
    year_fcst: int,
    month_fcst: int,
    *,
    skip_existing: bool = True,
) -> list[Path]:
    model_dir, model_title = build_model_labels(model)
    palette = forecast_palette()
    generated: list[Path] = []

    in_dir = input_dir(
        base,
        "forecast",
        type_calibration,
        model_dir,
        year_fcst,
        month_fcst,
    )
    out_dir = output_dir(
        base,
        "forecast",
        type_calibration,
        model_dir,
        year_fcst,
        month_fcst,
    )

    for product_type, period in FORECAST_PERIODS:
        for product in _forecast_products(var, type_calibration):
            style = _forecast_style(var, product.product_name, product_type)
            if style is None:
                continue

            nc_file = _forecast_input_file(
                in_dir,
                var,
                product.product_name,
                period,
                model_dir,
                type_calibration,
                year_fcst,
                month_fcst,
            )
            if not nc_file.exists():
                logger.warning("Arquivo nao encontrado, pulando: %s", nc_file)
                continue

            png_files = [
                out_dir / (
                    _forecast_output_name(
                        base,
                        model,
                        model_dir,
                        var,
                        product.figure_name,
                        type_calibration,
                        year_fcst,
                        month_fcst,
                        period,
                        region.name,
                    )
                    + ".png"
                )
                for region in REGIONS
            ]
            if skip_existing and all(png_file.exists() for png_file in png_files):
                logger.info(
                    "Todos os mapas ja existem, pulando arquivo: %s",
                    nc_file,
                )
                continue

            ds, da = open_product_data(nc_file, product.product_name)
            try:
                titles = (
                    _forecast_title_line_1(
                        base,
                        model_dir,
                        model_title,
                        type_calibration,
                    ),
                    style.title,
                    history_title(ds, forecast=True),
                )

                for region, png_file in zip(REGIONS, png_files):
                    if render_map(
                        da,
                        region,
                        style,
                        png_file,
                        titles,
                        palette,
                        skip_existing=skip_existing,
                    ):
                        generated.append(png_file)
            finally:
                ds.close()

    return generated


def _forecast_products(var: str, calibration: str) -> tuple[ForecastProduct, ...]:
    if calibration == "nocalib":
        return (ForecastProduct("anomaly", "anomaly"),)

    if var == "prec":
        positive_name = "above_mean" if calibration == "regr" else "above_median"
        return (
            ForecastProduct("anomaly", "anomaly"),
            ForecastProduct("total", "total"),
            ForecastProduct("mlterciles", "probability_tercile"),
            ForecastProduct(positive_name, "probability_positive"),
            *(ForecastProduct(name, name) for name in EXCEEDANCE_PRODUCTS),
            ForecastProduct("percent20", "percent20"),
            ForecastProduct("percent50", "percent50"),
            ForecastProduct("percent80", "percent80"),
        )

    if var == "t2mt":
        positive_name = "above_mean" if calibration == "regr" else "above_median"
        return (
            ForecastProduct("anomaly", "anomaly"),
            ForecastProduct("total", "total"),
            ForecastProduct("mlterciles", "probability_tercile"),
            ForecastProduct(positive_name, "probability_positive"),
        )

    return ()


def _forecast_style(
    var: str,
    product_name: str,
    product_type: str,
) -> MapStyle | None:
    if var == "prec":
        if product_name == "anomaly":
            if product_type == "seas":
                return MapStyle(
                    "PRECIPITATION ANOMALY (mm)",
                    (-500, -300, -200, -150, -100, -50, -25, 25, 50, 100, 150, 200, 300, 500),
                    (34, 33, 32, 31, 30, 29, 28, 27, 26, 25, 24, 23, 22, 21, 20),
                    factor=1.0,
                )
            return MapStyle(
                "PRECIPITATION ANOMALY (mm)",
                (-180, -130, -90, -60, -30, -10, -5, 5, 10, 30, 60, 90, 130, 180),
                (34, 33, 32, 31, 30, 29, 28, 27, 26, 25, 24, 23, 22, 21, 20),
                factor=1.0,
            )

        if product_name == "total":
            if product_type == "seas":
                return MapStyle(
                    "PRECIPITATION (mm)",
                    (50, 100, 150, 200, 250, 300, 400, 550, 700, 900),
                    (27, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83),
                )
            return MapStyle(
                "PRECIPITATION (mm)",
                (0, 10, 20, 40, 60, 100, 140, 200, 300, 400),
                (27, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83),
            )

        if product_name == "mlterciles":
            return MapStyle(
                "PROB. MOST LIKELY PRECIP. TERCILE (%)",
                (-100, -90, -80, -70, -60, -50, -40, 40, 50, 60, 70, 80, 90, 100),
                (34, 33, 32, 31, 30, 29, 27, 26, 25, 24, 23, 22, 20),
                factor=100.0,
                tercile_colorbar_labels=True,
                colorbar_extend="neither",
            )

        if product_name in {"above_mean", "above_median"}:
            return MapStyle(
                "PROB. PRECIP. ABOVE NORMAL (%)",
                (0, 10, 20, 30, 40, 45, 55, 60, 70, 80, 90, 100),
                (34, 33, 32, 30, 29, 27, 26, 25, 24, 22, 20),
                factor=100.0,
                colorbar_extend="neither",
            )

        if product_name.startswith("prob") and product_name.endswith("mm"):
            amount = product_name.removeprefix("prob").removesuffix("mm")
            return MapStyle(
                f"PROBABILITY (%) OF EXCEEDING {amount} mm",
                (0, 10, 25, 50, 75, 90, 100),
                (28, 26, 25, 24, 23, 20),
                factor=100.0,
                colorbar_extend="neither",
            )

        if product_name.startswith("percent"):
            percentile = product_name.removeprefix("percent")
            if product_type == "seas":
                levels = (1, 25, 50, 100, 200, 300, 400, 500, 700, 800, 1000)
            else:
                levels = (1, 5, 10, 25, 50, 100, 200, 300, 400, 600, 800)
            return MapStyle(
                f"PRECIP. THAT HAVE {percentile}% CHANCE OF OCCURRENCE",
                levels,
                (27, 33, 32, 31, 30, 29, 26, 25, 24, 23, 22, 20),
            )

    if var == "t2mt":
        if product_name == "anomaly":
            return MapStyle(
                "2-METRE TEMPERATURE ANOMALY (degC)",
                (-3, -2.5, -2, -1.5, -1, -0.5, -0.25, 0.25, 0.5, 1, 1.5, 2, 2.5, 3),
                (47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61),
            )
        if product_name == "total":
            return MapStyle(
                "2-METRE TEMPERATURE (degC)",
                (-30, -27, -24, -21, -18, -15, -12, -8, -4, 4, 8, 12, 15, 18, 21, 24, 27, 30),
                (100, 83, 82, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99),
                draw_contours=True,
            )
        if product_name == "mlterciles":
            return MapStyle(
                "PROB. MOST LIKELY TEMP. TERCILE (%)",
                (-100, -90, -80, -70, -60, -50, -40, 40, 50, 60, 70, 80, 90, 100),
                (20, 22, 23, 24, 25, 26, 27, 29, 30, 31, 32, 33, 34),
                factor=100.0,
                tercile_colorbar_labels=True,
                colorbar_extend="neither",
            )
        if product_name in {"above_mean", "above_median"}:
            return MapStyle(
                "PROB. TEMPERATURE ABOVE NORMAL (%)",
                (0, 10, 20, 30, 40, 45, 55, 60, 70, 80, 90, 100),
                (20, 22, 24, 25, 26, 27, 30, 30, 32, 33, 34),
                factor=100.0,
                colorbar_extend="neither",
            )

    return None


def _forecast_input_file(
    in_dir: Path,
    var: str,
    product_name: str,
    period: str,
    model_dir: str,
    calibration: str,
    year: int,
    month: int,
) -> Path:
    return in_dir / (
        f"fcst_{var}_{product_name}_{period}_{model_dir}_"
        f"{calibration_file_suffix(calibration)}_{forecast_date(year, month)}.nc"
    )


def _forecast_output_name(
    base: str,
    model: str,
    model_dir: str,
    var: str,
    figure_name: str,
    calibration: str,
    year: int,
    month: int,
    period: str,
    region: str,
) -> str:
    prefix_map = MULTIMODEL_BASE_PREFIX if model == "multimodel" else BASE_PREFIX
    prefix = prefix_map[base]
    return (
        f"{prefix}_{model_dir}_{calibration_output_suffix(calibration)}_"
        f"{var}_{figure_name}_{forecast_date(year, month)}_{period}_{region}"
    )


def _forecast_title_line_1(
    base: str,
    model_dir: str,
    model_title: str,
    calibration: str,
) -> str:
    base_label = "NMME" if base == "nmme" else "C3S"
    base_part = "" if model_dir == "bam12" else f" ({base_label})"

    if calibration == "nocalib":
        return f"{model_title}{base_part}"
    if calibration == "regr":
        return f"{model_title}{base_part} CALIBRATED (REGR.)"
    if calibration == "cox":
        return f"{model_title}{base_part} CALIBRATED (COX)"
    return f"{model_title}{base_part} CALIBRATED ({calibration.upper()})"
