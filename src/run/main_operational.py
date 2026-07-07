from __future__ import annotations

import argparse
import logging

from src.config.config_logging import setup_logging
from src.run.common import validate_month
from src.run.main_operational_realtime import run_operational_realtime
from src.run.main_operational_verification import run_operational_verification


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
        help="Repassa --skip-download para main_operational_realtime.",
    )
    parser.add_argument(
        "--skip-interpolation",
        action="store_true",
        help="Repassa --skip-interpolation para main_operational_realtime.",
    )
    parser.add_argument(
        "--skip-products",
        action="store_true",
        help="Repassa --skip-products para main_operational_realtime.",
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
        help="Pula main_operational_realtime.",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Pula checagem minima dos NetCDFs do multimodelo no realtime.",
    )
    parser.add_argument(
        "--skip-curves",
        action="store_true",
        help="Pula main_curves no realtime.",
    )
    parser.add_argument(
        "--run-verification",
        action="store_true",
        help="Executa tambem main_operational_verification.",
    )
    parser.add_argument(
        "--skip-multimodel-verification",
        action="store_true",
        help="Nao inclui o multimodelo na verificacao operacional.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    validate_month(args.month)

    setup_logging(
        args.year,
        args.month,
    )

    logger = logging.getLogger(__name__)
    logger.info(
        "Iniciando pipeline operacional geral: base=%s year=%s month=%s",
        args.base,
        args.year,
        args.month,
    )

    if not args.skip_realtime:
        run_operational_realtime(args)

    if args.run_verification:
        verification_args = argparse.Namespace(
            base=args.base,
            year=args.year,
            month=args.month,
            var=args.var,
            model=args.model,
            calibration=args.calibration,
            skip_multimodel=args.skip_multimodel_verification,
        )
        run_operational_verification(verification_args)

    logger.info(
        "Pipeline operacional geral concluido: base=%s year=%s month=%s",
        args.base,
        args.year,
        args.month,
    )


if __name__ == "__main__":
    main()
