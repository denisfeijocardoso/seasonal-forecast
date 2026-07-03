import argparse
from dataclasses import dataclass
import logging

from src.config.config_logging import setup_logging


@dataclass(frozen=True)
class CurvesRunConfig:
    base: str
    year: int
    month: int
    workers: int = 8
    skip_existing: bool = True

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "CurvesRunConfig":
        return cls(
            base=args.base,
            year=args.year,
            month=args.month,
            workers=args.workers,
            skip_existing=not args.overwrite,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rodar curvas sazonais em tempo-real para o multimodelo."
    )

    parser.add_argument("--base", type=str, default="nmme")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--month", type=int, required=True)
    parser.add_argument("--workers", type=int, default=8)
    existing_group = parser.add_mutually_exclusive_group()
    existing_group.add_argument(
        "--skip-existing",
        action="store_true",
        default=True,
        help="Pula figuras de curvas ja existentes (padrao).",
    )
    existing_group.add_argument(
        "--overwrite",
        action="store_true",
        help="Refaz curvas mesmo quando a figura ja existe.",
    )

    return parser.parse_args()


def run_curves(config: CurvesRunConfig) -> None:
    setup_logging(
        config.year,
        config.month,
    )

    logger = logging.getLogger(__name__)
    logger.info(
        "Gerando curvas em tempo-real: base=%s year=%s month=%s model=multimodel",
        config.base,
        config.year,
        config.month,
    )

    from src.curves.realtime_curves import run_realtime_curves

    run_realtime_curves(
        config.base,
        config.year,
        config.month,
        workers=config.workers,
        skip_existing=config.skip_existing,
    )


def main() -> None:
    run_curves(CurvesRunConfig.from_args(parse_args()))


if __name__ == "__main__":
    main()
