from __future__ import annotations

import argparse
import logging

from src.config.config_logging import setup_logging
from src.run.common import validate_month
from src.run.operational_realtime import run_operational_realtime
from src.run.operational_verification import run_operational_verification


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
        "--overwrite-maps",
        action="store_true",
        help="Refaz mapas de previsao mesmo quando a figura ja existe.",
    )

    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Repassa --skip-download para operational_realtime.",
    )
    parser.add_argument(
        "--skip-interpolation",
        action="store_true",
        help="Repassa --skip-interpolation para operational_realtime.",
    )
    parser.add_argument(
        "--skip-products",
        action="store_true",
        help="Repassa --skip-products para operational_realtime.",
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
        help="Pula operational_realtime.",
    )
    parser.add_argument(
        "--only-curves",
        action="store_true",
        help=(
            "Gera somente as curvas a partir dos NetCDFs existentes, sem executar "
            "download, interpolacao, produtos, mapas ou verificacao."
        ),
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Pula checagem minima dos NetCDFs do multimodelo no realtime.",
    )
    parser.add_argument(
        "--skip-curves",
        action="store_true",
        help="Pula curves no realtime.",
    )
    parser.add_argument(
        "--run-verification",
        action="store_true",
        help="Executa tambem operational_verification.",
    )
    parser.add_argument(
        "--skip-multimodel-verification",
        action="store_true",
        help="Nao inclui o multimodelo na verificacao operacional.",
    )
    parser.add_argument(
        "--exclude-verification-model",
        action="append",
        default=[],
        help=(
            "Remove um modelo apenas da verificacao operacional. "
            "Pode ser usado mais de uma vez."
        ),
    )
    parser.add_argument(
        "--overwrite-verification-maps",
        action="store_true",
        help="Refaz mapas de verificacao mesmo quando a figura ja existe.",
    )
    parser.add_argument(
        "--skip-verification-download",
        action="store_true",
        help="Pula o download dos hindcasts em operational_verification.",
    )
    parser.add_argument(
        "--skip-verification-interpolation",
        action="store_true",
        help="Pula a interpolacao dos hindcasts em operational_verification.",
    )
    parser.add_argument(
        "--skip-verification-products",
        action="store_true",
        help="Pula o calculo/escrita das metricas em operational_verification.",
    )
    parser.add_argument(
        "--skip-verification-maps",
        action="store_true",
        help="Pula mapas em operational_verification.",
    )
    parser.add_argument(
        "--verification-only-maps",
        action="store_true",
        help="Roda apenas os mapas em operational_verification.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    validate_month(args.month)

    if args.only_curves and args.skip_curves:
        raise ValueError("--only-curves e --skip-curves nao podem ser usados juntos.")
    if args.only_curves and args.run_verification:
        raise ValueError("--only-curves e --run-verification nao podem ser usados juntos.")

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

    if args.only_curves:
        # Em operational_realtime, skip_realtime pula apenas o processamento
        # principal e preserva a validacao dos NetCDFs e a etapa de curvas.
        args.skip_realtime = True
        run_operational_realtime(args)
    elif not args.skip_realtime:
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
            map_workers=args.map_workers,
            overwrite_maps=args.overwrite_verification_maps,
            skip_download=args.skip_verification_download,
            skip_interpolation=args.skip_verification_interpolation,
            skip_verification=args.skip_verification_products,
            skip_maps=args.skip_verification_maps,
            only_maps=args.verification_only_maps,
            exclude_model=args.exclude_verification_model,
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
