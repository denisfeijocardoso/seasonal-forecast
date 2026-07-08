from __future__ import annotations

import argparse
import logging
import os
from dataclasses import dataclass
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from sklearn.calibration import calibration_curve
from sklearn.metrics import roc_auc_score, roc_curve

from src.config.config_models import build_model_dir_name, build_model_title
from src.config.loader import get_periods_aggregation
from src.io.realtime_writer import compute_period_names
from src.plotting.seasonal_map_common import (
    BASE_PREFIX,
    calibration_file_suffix,
    calibration_output_suffix,
    forecast_date,
    input_dir,
    output_dir,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DiagramProduct:
    product_name: str
    binobs_product: str
    prob_product: str


DIAGRAM_PRODUCTS = (
    DiagramProduct("lowertercile", "binobstinf", "probtinf"),
    DiagramProduct("uppertercile", "binobstsup", "probtsup"),
    DiagramProduct("positiveanom", "binobsmed", "probmed"),
)

DIAGRAM_PERIODS = tuple(get_periods_aggregation().keys())

REGIONS = {
    "gl": {"lat": (9, 64), "lon": (1, 144)},
    "af": {"lat": (21, 52), "lon": (24, 132)},
    "aa": {"lat": (33, 68), "lon": (27, 72)},
    "au": {"lat": (17, 46), "lon": (45, 76)},
    "eu": {"lat": (49, 68), "lon": (24, 132)},
    "an": {"lat": (33, 64), "lon": (77, 124)},
    "pa": {"lat": (25, 48), "lon": (42, 114)},
    "as": {"lat": (13, 42), "lon": (109, 132)},
    "ne": {"lat": (45, 68), "lon": (1, 144)},
    "se": {"lat": (5, 29), "lon": (1, 144)},
    "tr": {"lat": (29, 44), "lon": (1, 144)},
    "am": {"lat": (28, 39), "lon": (112, 125)},
}

MODEL_LABELS = {
    "nmme": {
        "canesm": "CanESM5 (NMME)",
        "cfs": "CFSv2 (NMME)",
        "gemnemo": "GEM5.2_NEMO (NMME)",
        "ccsm": "NCAR_CCSM4 (NMME)",
        "cesm": "NCAR_CESM1 (NMME)",
        "geos": "NASA_GEOSS2S (NMME)",
        "spear": "GFDL_SPEAR (NMME)",
        "bam": "CPTEC_BAM1.2",
        "echam": "ECHAM4.6",
    },
    "copernicus": {
        "ecmwf": "ECMWFs5.1 (C3S)",
        "ukmo": "UKMetOffice_s610 (C3S)",
        "meteofr": "Meteo-France_s9 (C3S)",
        "dwd": "DWD_s22 (C3S)",
        "cmcc": "CMCC_s4 (C3S)",
        "ncep": "NCEP_s2 (C3S)",
        "jma": "JMA_s4 (C3S)",
        "eccc4": "ECCC_s4 (C3S)",
        "eccc5": "ECCC_s5 (C3S)",
        "bom": "BOM_s2 (C3S)",
        "bam": "CPTEC_BAM1.2",
    },
}


def run_python_diagrams_verification(
    base: str,
    model: str,
    var: str,
    type_calibration: str,
    year_ref: int,
    month_hcst: int,
    *,
    skip_existing: bool = False,
) -> list[Path]:
    model_dir = build_model_dir_name(model)
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
    out_dir.mkdir(parents=True, exist_ok=True)

    period_names = compute_period_names(
        year_ref,
        month_hcst,
    )
    issued_label = _period_label(period_names, "mnth00")
    generated: list[Path] = []

    for period in DIAGRAM_PERIODS:
        if period not in period_names:
            logger.warning("Periodo sem nome calculado, pulando: %s", period)
            continue

        valid_label = _period_label(period_names, period)

        for product in DIAGRAM_PRODUCTS:
            paths = _diagram_input_files(
                in_dir,
                var,
                product,
                period,
                model_dir,
                type_calibration,
                year_ref,
                month_hcst,
            )

            if not paths["binobs"].exists() or not paths["prob"].exists():
                logger.warning(
                    "Arquivos de diagrama nao encontrados, pulando: %s %s",
                    paths["binobs"],
                    paths["prob"],
                )
                continue

            binobs_data, prob_data = _open_diagram_data(paths, product)
            try:
                title1, title2 = get_titles(
                    var,
                    product.product_name,
                    base,
                    model,
                    type_calibration,
                )

                for region_name, coords in REGIONS.items():
                    outputs = _diagram_output_files(
                        out_dir,
                        base,
                        model_dir,
                        type_calibration,
                        product.product_name,
                        var,
                        period,
                        issued_label,
                        region_name,
                    )

                    if skip_existing and all(path.exists() for path in outputs.values()):
                        logger.debug(
                            "Diagramas ja existem, pulando: %s %s",
                            outputs["roc"],
                            outputs["reliability"],
                        )
                        continue

                    obs, prob = _region_samples(
                        binobs_data,
                        prob_data,
                        coords,
                    )
                    if obs.size == 0:
                        logger.warning(
                            "Sem amostras validas para diagrama: %s %s %s %s %s",
                            base,
                            model,
                            var,
                            period,
                            region_name,
                        )
                        continue

                    if np.unique(obs).size < 2:
                        logger.warning(
                            "Observacao com uma unica classe, pulando ROC/reliability: "
                            "%s %s %s %s %s",
                            base,
                            model,
                            var,
                            period,
                            region_name,
                        )
                        continue

                    if _plot_roc_diagram(
                        obs,
                        prob,
                        outputs["roc"],
                        title1,
                        title2,
                        issued_label,
                        valid_label,
                        skip_existing=skip_existing,
                    ):
                        generated.append(outputs["roc"])

                    if _plot_reliability_diagram(
                        obs,
                        prob,
                        outputs["reliability"],
                        title1,
                        title2,
                        issued_label,
                        valid_label,
                        type_calibration,
                        product.product_name,
                        skip_existing=skip_existing,
                    ):
                        generated.append(outputs["reliability"])
            finally:
                binobs_data.close()
                prob_data.close()

    return generated


def get_titles(
    var: str,
    product: str,
    base: str,
    model: str,
    calib: str,
) -> tuple[str, str]:
    var_names = {
        "prec": "PRECIPITATION",
        "t2mt": "2-METRE TEMPERATURE",
    }
    product_suffix = {
        "lowertercile": "IN LOWER TERCILE",
        "uppertercile": "IN UPPER TERCILE",
        "positiveanom": "POS. OR NEG. {var} ANOMALY",
    }
    base_years = {
        "nmme": "(1991 - 2020)",
        "copernicus": "(1993 - 2016)",
    }
    base_labels = {
        "nmme": "MULTIMODEL NMME + CPTEC",
        "copernicus": "MULTIMODEL CS3 + CPTEC",
    }
    calib_labels = {
        "regr": "REGR.",
        "cox": "COX",
        "nocalib": " ",
    }
    ref_labels = {
        "prec": "GPCP",
        "t2mt": "ERA5",
    }

    if product == "positiveanom":
        title2 = (
            f"{product_suffix[product].format(var=var_names[var])} "
            f"{base_years[base]}"
        )
    else:
        title2 = f"{var_names[var]} {product_suffix[product]} {base_years[base]}"

    if model == "multimodel":
        if calib == "nocalib":
            title1 = f"{base_labels[base]} REF:{ref_labels[var]}"
        else:
            title1 = (
                f"{base_labels[base]} ({calib_labels[calib]}) "
                f"REF:{ref_labels[var]}"
            )
    else:
        model_label = MODEL_LABELS.get(base, {}).get(model, build_model_title(model))
        if calib == "nocalib":
            title1 = f"{model_label} REF:{ref_labels[var]}"
        else:
            title1 = (
                f"{model_label} ({calib_labels[calib]}) "
                f"REF:{ref_labels[var]}"
            )

    return title1, title2


def _diagram_input_files(
    in_dir: Path,
    var: str,
    product: DiagramProduct,
    period: str,
    model_dir: str,
    calibration: str,
    year: int,
    month: int,
) -> dict[str, Path]:
    return {
        "binobs": _verification_input_file(
            in_dir,
            var,
            product.binobs_product,
            period,
            model_dir,
            calibration,
            year,
            month,
        ),
        "prob": _verification_input_file(
            in_dir,
            var,
            product.prob_product,
            period,
            model_dir,
            calibration,
            year,
            month,
        ),
    }


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


def _open_diagram_data(
    paths: dict[str, Path],
    product: DiagramProduct,
) -> tuple[xr.DataArray, xr.DataArray]:
    binobs_ds = xr.open_dataset(paths["binobs"], decode_times=False)
    prob_ds = xr.open_dataset(paths["prob"], decode_times=False)

    return (
        _get_dataarray(binobs_ds, product.binobs_product),
        _get_dataarray(prob_ds, product.prob_product),
    )


def _get_dataarray(
    ds: xr.Dataset,
    name: str,
) -> xr.DataArray:
    if name in ds.data_vars:
        return ds[name]
    if len(ds.data_vars) == 1:
        return ds[next(iter(ds.data_vars))]
    raise ValueError(f"Variavel {name!r} nao encontrada em dataset")


def _region_samples(
    binobs_data: xr.DataArray,
    prob_data: xr.DataArray,
    coords: dict[str, tuple[int, int]],
) -> tuple[np.ndarray, np.ndarray]:
    lat_start, lat_end = coords["lat"]
    lon_start, lon_end = coords["lon"]

    binobs_region = binobs_data.values[:, lat_start:lat_end + 1, lon_start:lon_end + 1]
    prob_region = prob_data.values[:, lat_start:lat_end + 1, lon_start:lon_end + 1]

    obs = binobs_region.ravel()
    prob = prob_region.ravel()

    mask = ~np.isnan(obs) & ~np.isnan(prob)
    obs = obs[mask].astype(int)
    prob = prob[mask]

    return obs, prob


def _diagram_output_files(
    out_dir: Path,
    base: str,
    model_dir: str,
    calibration: str,
    product: str,
    var: str,
    period: str,
    issued_label: str,
    region_name: str,
) -> dict[str, Path]:
    prefix = BASE_PREFIX[base]
    calib_suffix = calibration_output_suffix(calibration)
    stem = (
        f"{prefix}_{model_dir}_{calib_suffix}_"
        f"{{diagram}}_{product}_{var}_{period}_{issued_label}_{region_name}.png"
    )

    return {
        "roc": out_dir / stem.format(diagram="rocdiagram"),
        "reliability": out_dir / stem.format(diagram="reliabilitydiagram"),
    }


def _plot_roc_diagram(
    obs: np.ndarray,
    prob: np.ndarray,
    output_file: Path,
    title1: str,
    title2: str,
    issued_label: str,
    valid_label: str,
    *,
    skip_existing: bool,
) -> bool:
    if skip_existing and output_file.exists():
        return False

    roc_auc = roc_auc_score(obs, prob)
    fpr, tpr, _ = roc_curve(obs, prob)

    plt.figure(figsize=(4, 4))
    plt.plot(fpr, tpr, color="black", lw=1.5)
    plt.plot([-0.08, 1.08], [-0.08, 1.08], color="grey", lw=1)
    plt.xlim([-0.08, 1.08])
    plt.ylim([-0.08, 1.08])
    plt.xlabel("FALSE ALARM RATE", fontsize=8)
    plt.ylabel("HIT RATE", fontsize=8)
    plt.title(
        f"{title1}"
        f"\n{title2}\n"
        f"ISSUED: {issued_label} VALID FOR {valid_label}",
        fontsize=9,
    )
    plt.text(0.5, 0.2, f"ROC AREA = {roc_auc:.2f}", fontsize=8)
    plt.grid(False)
    plt.savefig(output_file, dpi=120, bbox_inches="tight")
    plt.close()

    logger.info("ROC salvo: %s", output_file)
    return True


def _plot_reliability_diagram(
    obs: np.ndarray,
    prob: np.ndarray,
    output_file: Path,
    title1: str,
    title2: str,
    issued_label: str,
    valid_label: str,
    calibration: str,
    product: str,
    *,
    skip_existing: bool,
) -> bool:
    if skip_existing and output_file.exists():
        return False

    prob = np.clip(prob, 0, 1)
    prob_true, prob_pred = calibration_curve(obs, prob, n_bins=10)

    plt.figure(figsize=(4, 4))

    if calibration == "cox" and product == "positiveanom":
        bin_counts, _ = np.histogram(1 - prob, bins=np.linspace(0, 1, 11))
    else:
        bin_counts, _ = np.histogram(prob, bins=np.linspace(0, 1, 11))

    total = bin_counts.sum()
    if total == 0:
        plt.close()
        logger.warning("Sem bins validos para reliability: %s", output_file)
        return False

    bin_width = 0.0008
    ax = plt.gca()
    for x, h in zip(prob_pred, bin_counts / total):
        bar = patches.FancyBboxPatch(
            (x - bin_width / 2, 0),
            bin_width,
            h,
            boxstyle="round,pad=0.02,rounding_size=0.015",
            linewidth=0,
            facecolor="gray",
            alpha=0.6,
        )
        ax.add_patch(bar)

    plt.plot(prob_pred, prob_true, color="black", linewidth=2)
    plt.plot(
        [-0.03, 1.03],
        [-0.03, 1.03],
        color="black",
        linestyle="-",
        linewidth=1,
    )
    plt.xlabel("FORECAST PROBABILITY", fontsize=8)
    plt.ylabel("OBSERVED RELATIVE FREQUENCY", fontsize=8)
    plt.title(
        f"RELIABILITY DIAGRAM: {title1}\n"
        f"{title2}\n"
        f"ISSUED: {issued_label}  VALID FOR {valid_label}",
        fontsize=9,
    )
    plt.xlim(-0.03, 1.03)
    plt.ylim(-0.03, 1.03)
    plt.grid(False)
    plt.tight_layout()
    plt.savefig(output_file, dpi=120, bbox_inches="tight")
    plt.close()

    logger.info("RELIABILITY salvo: %s", output_file)
    return True


def _period_label(
    period_names: dict[str, str],
    period: str,
) -> str:
    return period_names[period].split()[0].upper()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gerar diagramas ROC e reliability da verificacao sazonal."
    )
    parser.add_argument("--base", type=str, required=True)
    parser.add_argument("--model", type=str, required=True)
    parser.add_argument("--var", type=str, required=True)
    parser.add_argument("--calibration", type=str, required=True)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--month", type=int, required=True)
    parser.add_argument("--skip-existing", action="store_true")

    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    args = parse_args()
    generated = run_python_diagrams_verification(
        args.base,
        args.model,
        args.var,
        args.calibration,
        args.year,
        args.month,
        skip_existing=args.skip_existing,
    )
    logger.info("Diagramas gerados: %s", len(generated))


if __name__ == "__main__":
    main()
