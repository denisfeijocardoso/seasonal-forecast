from __future__ import annotations

import argparse
import logging
from pathlib import Path

from src.config.config_logging import setup_logging
from src.config.config_models import get_multimodel_version
from src.config.loader import PARAMETERS_RUN
from src.config.paths import PATH_POSPROC
from src.run.main_curves import CurvesRunConfig, run_curves
from src.run.main_realtime import RealtimeRunConfig, run_realtime


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rodar pipeline operacional da previsao sazonal."
    )

    parser.add_argument("--base", type=str, default="nmme")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--month", type=int, required=True)
    parser.add_argument("--var", type=str, default=None)
    parser.add_argument("--model", type=str, default="all")
    parser.add_argument("--calibration", type=str, default="all")
    parser.add_argument("--map-workers", type=int, default=4)
    parser.add_argument("--curve-workers", type=int, default=8)

    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Repassa --skip-download para main_realtime.",
    )
    parser.add_argument(
        "--skip-interpolation",
        action="store_true",
        help="Repassa --skip-interpolation para main_realtime.",
    )
    parser.add_argument(
        "--skip-products",
        action="store_true",
        help="Repassa --skip-products para main_realtime.",
    )
    existing_curves_group = parser.add_mutually_exclusive_group()
    existing_curves_group.add_argument(
        "--skip-existing-curves",
        action="store_true",
        default=True,
        help="Pula curvas ja existentes (padrao).",
    )
    existing_curves_group.add_argument(
        "--overwrite-curves",
        action="store_true",
        help="Refaz curvas mesmo quando a figura ja existe.",
    )
    parser.add_argument(
        "--skip-realtime",
        action="store_true",
        help="Pula main_realtime e segue para validacao/curvas.",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Pula checagem minima dos NetCDFs do multimodelo.",
    )
    parser.add_argument(
        "--skip-curves",
        action="store_true",
        help="Pula main_curves.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.map_workers < 1:
        raise ValueError("--map-workers precisa ser maior ou igual a 1.")
    if args.curve_workers < 1:
        raise ValueError("--curve-workers precisa ser maior ou igual a 1.")

    setup_logging(args.year, args.month)
    logger = logging.getLogger(__name__)

    logger.info(
        "Iniciando pipeline operacional: base=%s year=%s month=%s",
        args.base,
        args.year,
        args.month,
    )

    if not args.skip_realtime:
        run_realtime_step(args)

    if not args.skip_validation:
        validate_multimodel_outputs(
            args.base,
            args.year,
            args.month,
            select_variables(args.var),
            select_calibrations(args.calibration),
        )

    if not args.skip_curves:
        run_curves_step(args)

    logger.info(
        "Pipeline operacional concluido: base=%s year=%s month=%s",
        args.base,
        args.year,
        args.month,
    )


def run_realtime_step(args: argparse.Namespace) -> None:
    logger = logging.getLogger(__name__)
    logger.info("Executando etapa: main_realtime")
    run_realtime(
        RealtimeRunConfig(
            base=args.base,
            year=args.year,
            month=args.month,
            var=args.var,
            model=args.model,
            calibration=args.calibration,
            include_multimodel=True,
            skip_download=args.skip_download,
            skip_interpolation=args.skip_interpolation,
            skip_products=args.skip_products,
            map_workers=args.map_workers,
        )
    )
    logger.info("Etapa concluida: main_realtime")


def run_curves_step(args: argparse.Namespace) -> None:
    logger = logging.getLogger(__name__)
    logger.info("Executando etapa: main_curves")
    run_curves(
        CurvesRunConfig(
            base=args.base,
            year=args.year,
            month=args.month,
            workers=args.curve_workers,
            skip_existing=not args.overwrite_curves,
        )
    )
    logger.info("Etapa concluida: main_curves")


def validate_multimodel_outputs(
    base: str,
    year: int,
    month: int,
    variables: list[str],
    calibrations: list[str],
) -> None:
    version = get_multimodel_version(base)
    forecast_date = f"{year}{month:02d}0100"
    root = PATH_POSPROC / base / version / "forecast"

    missing: list[Path] = []
    empty: list[Path] = []

    for calibration in calibrations:
        directory = root / calibration / "multimodel" / str(year) / forecast_date
        if not directory.is_dir():
            missing.append(directory)
            continue

        for var in variables:
            pattern = f"fcst_{var}_*_multimodel_*_{forecast_date}.nc"
            if not any(directory.glob(pattern)):
                empty.append(directory / pattern)

    if missing or empty:
        details = [*(str(path) for path in missing), *(str(path) for path in empty)]
        raise FileNotFoundError(
            "Saidas minimas do multimodelo nao encontradas:\n"
            + "\n".join(details)
        )

    logging.getLogger(__name__).info(
        "Validacao concluida: posproc=%s variables=%s calibrations=%s",
        root,
        variables,
        calibrations,
    )


def select_variables(var: str | None) -> list[str]:
    if var is None:
        return list(PARAMETERS_RUN["variables"])
    if var not in PARAMETERS_RUN["variables"]:
        raise ValueError(f"Variavel invalida: {var}")
    return [var]


def select_calibrations(calibration: str) -> list[str]:
    if calibration == "all":
        return list(PARAMETERS_RUN["calibrations"])
    if calibration not in PARAMETERS_RUN["calibrations"]:
        raise ValueError(f"Calibracao invalida: {calibration}")
    return [calibration]


if __name__ == "__main__":
    main()
