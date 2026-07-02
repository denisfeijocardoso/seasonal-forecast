import argparse
import logging

from src.config.config_logging import setup_logging


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rodar curvas sazonais em tempo-real para o multimodelo."
    )

    parser.add_argument("--base", type=str, default="nmme")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--month", type=int, required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Pula figuras de curvas ja existentes.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    setup_logging(
        args.year,
        args.month,
    )

    logger = logging.getLogger(__name__)
    logger.info(
        "Gerando curvas em tempo-real: base=%s year=%s month=%s model=multimodel",
        args.base,
        args.year,
        args.month,
    )

    from src.curves.realtime_curves import run_realtime_curves

    run_realtime_curves(
        args.base,
        args.year,
        args.month,
        workers=args.workers,
        skip_existing=args.skip_existing,
    )


if __name__ == "__main__":
    main()
