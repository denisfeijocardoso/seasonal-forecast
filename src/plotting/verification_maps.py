from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from src.plotting.palettes import verification_palette
from src.plotting.seasonal_map_common import (
    BASE_PREFIX,
    CLIMATOLOGY_LABELS,
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
class VerificationProduct:
    product_name: str
    figure_name: str
    metric_title: str


VERIFICATION_PRODUCTS = (
    VerificationProduct("corskill", "corskill", "CORRELATION"),
    VerificationProduct("mssskill", "mssskill", "MSSS"),
    VerificationProduct("msssfase", "msssfase", "PHASE ERROR"),
    VerificationProduct("msssamplitude", "msssamplitude", "AMPLITUDE ERROR"),
    VerificationProduct("bias", "bias", "BIAS"),
    VerificationProduct("arocmed", "arocmed", "ROC AREA"),
    VerificationProduct("aroctinf", "aroctinf", "ROC AREA"),
    VerificationProduct("aroctsup", "aroctsup", "ROC AREA"),
)

VERIFICATION_PERIODS = (
    ("mnth", "mnth00"),
    ("mnth", "mnth01"),
    ("mnth", "mnth02"),
    ("mnth", "mnth03"),
    ("mnth", "mnth04"),
    ("seas", "seas00"),
    ("seas", "seas01"),
    ("seas", "seas02"),
)


def run_python_maps_verification(
    base: str,
    model: str,
    var: str,
    type_calibration: str,
    year_ref: int,
    month_hcst: int,
    *,
    skip_existing: bool = False,
) -> list[Path]:
    model_dir, model_title = build_model_labels(model)
    generated: list[Path] = []
    month_name = datetime(2000, month_hcst, 1).strftime("%b").upper()

    in_dir = input_dir(
        base,
        "verification",
        type_calibration,
        model_dir,
    )
    out_dir = output_dir(
        base,
        "verification",
        type_calibration,
        model_dir,
    )

    for product_type, period in VERIFICATION_PERIODS:
        for product in VERIFICATION_PRODUCTS:
            style = _verification_style(var, product.product_name, product_type)
            if style is None:
                continue
            palette = verification_palette(style.palette_files)

            nc_file = _verification_input_file(
                in_dir,
                var,
                product.product_name,
                period,
                model_dir,
                type_calibration,
                year_ref,
                month_hcst,
            )
            if not nc_file.exists():
                logger.warning("Arquivo nao encontrado, pulando: %s", nc_file)
                continue

            ds, da = open_product_data(nc_file, product.product_name)
            try:
                titles = (
                    _verification_title_line_1(
                        base,
                        model,
                        model_dir,
                        model_title,
                        type_calibration,
                        product.metric_title,
                        var,
                    ),
                    _verification_title_line_2(base, var, product.product_name),
                    history_title(ds, forecast=False),
                )

                for region in REGIONS:
                    png_file = out_dir / (
                        _verification_output_name(
                            base,
                            model,
                            model_dir,
                            product.figure_name,
                            var,
                            type_calibration,
                            period,
                            month_name,
                            region.name,
                        )
                        + ".png"
                    )
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


def _verification_style(
    var: str,
    product_name: str,
    product_type: str,
) -> MapStyle | None:
    if product_name == "corskill":
        return MapStyle(
            "CORRELATION",
            (0, 0.2, 0.4, 0.6, 0.8),
            (0, 115, 7, 8, 2, 114),
            palette_files=("crgb2.gs",),
        )

    if product_name == "mssskill":
        return MapStyle(
            "MSSS",
            (-0.1, 0, 0.1, 0.2, 0.4, 0.6, 0.8),
            (47, 48, 49, 50, 51, 52, 53, 54),
            palette_files=("cmrgb2.gs",),
        )

    if product_name in {"arocmed", "aroctinf", "aroctsup"}:
        return MapStyle(
            "ROC AREA",
            (0.5, 0.6, 0.7, 0.8, 0.9),
            (0, 50, 51, 52, 53, 54),
            palette_files=("cmrgb2.gs",),
        )

    if product_name == "msssamplitude":
        return MapStyle(
            "AMPLITUDE ERROR",
            (0.1, 0.2, 0.4, 0.6, 0.9, 1.1, 2),
            (39, 40, 41, 42, 43, 44, 45, 46),
            palette_files=("cmrgb2.gs",),
        )

    if product_name == "msssfase":
        return MapStyle(
            "PHASE ERROR",
            (0.3, 0.6, 0.9, 1.2, 1.5),
            (0, 82, 83, 84, 85, 86),
            palette_files=("crgb2.gs",),
        )

    if product_name == "bias":
        if var == "prec":
            if product_type == "mnth":
                levels = (-150, -130, -100, -70, -50, -30, -10, 10, 30, 50, 70, 100, 130, 150)
            else:
                levels = (-400, -300, -200, -160, -120, -80, -40, 40, 80, 120, 160, 200, 300, 400)
            return MapStyle(
                "BIAS",
                levels,
                (61, 60, 59, 58, 57, 56, 55, 54, 53, 52, 51, 50, 49, 48, 47),
                palette_files=("brgb.gs",),
            )

        if var == "t2mt":
            return MapStyle(
                "BIAS",
                (-10, -8, -6, -4, -3, -2, -1, 1, 2, 3, 4, 6, 8, 10),
                (47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61),
                palette_files=("brgb.gs",),
            )

    return None


def _verification_input_file(
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
        f"{var}_{product_name}_{period}_{model_dir}_"
        f"{calibration_file_suffix(calibration)}_{forecast_date(year, month)}.nc"
    )


def _verification_output_name(
    base: str,
    model: str,
    model_dir: str,
    figure_name: str,
    var: str,
    calibration: str,
    period: str,
    month_name: str,
    region: str,
) -> str:
    prefix_map = MULTIMODEL_BASE_PREFIX if model == "multimodel" else BASE_PREFIX
    prefix = prefix_map[base]
    return (
        f"{prefix}_{model_dir}_{calibration_output_suffix(calibration)}_"
        f"{figure_name}_{var}_{period}_{month_name}_{region}"
    )


def _verification_title_line_1(
    base: str,
    model: str,
    model_dir: str,
    model_title: str,
    calibration: str,
    metric_title: str,
    var: str,
) -> str:
    base_label = "NMME" if base == "nmme" else "C3S"
    base_part = "" if model_dir == "bam12" else f" ({base_label})"
    ref = "GPCP" if var == "prec" else "ERA5"

    if model == "multimodel":
        model_title = f"{base.upper()} Multimodel"
        base_part = ""

    if calibration == "nocalib":
        return f"{metric_title}: {model_title}{base_part}  REF: {ref}"
    if calibration == "regr":
        return f"{metric_title}: {model_title}{base_part} CALIBRATED (REGR.) REF: {ref}"
    if calibration == "cox":
        return f"{metric_title}: {model_title}{base_part} CALIBRATED (COX) REF: {ref}"
    return f"{metric_title}: {model_title}{base_part} CALIBRATED ({calibration.upper()}) REF: {ref}"


def _verification_title_line_2(
    base: str,
    var: str,
    product_name: str,
) -> str:
    years = CLIMATOLOGY_LABELS[base]

    if product_name == "bias":
        if var == "prec":
            return f"PRECIPITATION TOTAL ({years})"
        return f"2-METRE TEMPERATURE TOTAL ({years})"

    if product_name in {"corskill", "mssskill", "msssfase", "msssamplitude"}:
        if var == "prec":
            return f"PRECIPITATION ANOMALY ({years})"
        return f"2-METRE TEMPERATURE ANOMALY ({years})"

    if product_name == "arocmed":
        if var == "prec":
            return f"POS. OR NEG. PRECIPITATION ANOMALY ({years})"
        return f"POS. OR NEG. 2-METRE TEMPERATURE ANOMALY ({years})"

    if product_name == "aroctinf":
        if var == "prec":
            return f"PRECIPITATION IN LOWER TERCILE ({years})"
        return f"2-METRE TEMPERATURE IN LOWER TERCILE ({years})"

    if product_name == "aroctsup":
        if var == "prec":
            return f"PRECIPITATION IN UPPER TERCILE ({years})"
        return f"2-METRE TEMPERATURE IN UPPER TERCILE ({years})"

    return ""
