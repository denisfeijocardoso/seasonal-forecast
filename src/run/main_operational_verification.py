from __future__ import annotations

import argparse
import logging

from src.config.config_logging import setup_logging
from src.run.common import validate_month
from src.run.main_verification import VerificationRunConfig, run_verification


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rodar pipeline operacional das metricas de verificacao."
    )

    parser.add_argument("--base", type=str, default="nmme")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--month", type=int, required=True)
    parser.add_argument("--var", type=str, default=None)
    parser.add_argument("--model", type=str, default="all")
    parser.add_argument("--calibration", type=str, default="all")

    parser.add_argument(
        "--skip-multimodel",
        action="store_true",
        help="Nao inclui o multimodelo na verificacao operacional.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    run_operational_verification(args)


def run_operational_verification(args: argparse.Namespace) -> None:
    validate_month(args.month)

    setup_logging(
        args.year,
        args.month,
    )

    logger = logging.getLogger(__name__)
    include_multimodel = should_include_multimodel(args)

    logger.info(
        "Iniciando verificacao operacional: base=%s year=%s month=%s var=%s model=%s calibration=%s include_multimodel=%s",
        args.base,
        args.year,
        args.month,
        args.var or "all",
        args.model,
        args.calibration,
        include_multimodel,
    )

    run_verification(
        VerificationRunConfig(
            base=args.base,
            year=args.year,
            month=args.month,
            var=args.var,
            model=args.model,
            calibration=args.calibration,
            include_multimodel=include_multimodel,
        )
    )

    logger.info(
        "Verificacao operacional concluida: base=%s year=%s month=%s",
        args.base,
        args.year,
        args.month,
    )


def should_include_multimodel(args: argparse.Namespace) -> bool:
    return not args.skip_multimodel


if __name__ == "__main__":
    main()
