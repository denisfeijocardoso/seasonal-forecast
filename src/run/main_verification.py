import argparse
import logging
from src.config.config_logging import setup_logging
from src.config.config_models import get_list_models, check_models
from src.config.loader import PARAMETERS_RUN
from src.io.verification_writer import write_verification_netcdf
from src.verification.cross_validation import run_cross_validation
from src.verification.metrics import (
    build_diagram_fields,
    compute_verification_metrics,
)

def parse_args() -> argparse.Namespace:

    parser = argparse.ArgumentParser(
        description="Rodar verificação das previsões sazonais."
    )

    parser.add_argument("--base", type=str, required=True)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--month", type=int, required=True)
    parser.add_argument("--var", type=str, default=None)
    parser.add_argument("--model", type=str, default="all")
    parser.add_argument("--calibration", type=str, default="all")
    parser.add_argument(
        "--include-multimodel",
        action="store_true",
        help="Inclui o multimodelo na verificação.",
    )

    return parser.parse_args()


def main() -> None:

    args = parse_args()

    setup_logging(
        args.year,
        args.month,
    )

    logger = logging.getLogger(__name__)

    variables = (
        [args.var]
        if args.var
        else PARAMETERS_RUN["variables"]
    )

    calibrations = (
        PARAMETERS_RUN["calibrations"]
        if args.calibration == "all"
        else [args.calibration]
    )

    models_available = list(
        check_models(
            args.base,
            args.var,
            args.year,
            args.month
            )
    )

    models_to_run = (
        models_available
        if args.model == "all"
        else [args.model]
    )

    if args.include_multimodel:
        models_to_run = ["multimodel"] + models_to_run

    for var in variables:
        for model in models_to_run:
            for calibration in calibrations:

                logger.info(
                    "Verificação: base=%s var=%s model=%s calibration=%s month=%s",
                    args.base,
                    var,
                    model,
                    calibration,
                    args.month,
                )

                cross_validation = run_cross_validation(
                    base=args.base,
                    model=model,
                    var=var,
                    type_calibration=calibration,
                    month_hcst=args.month,
                    models_available=models_available,
                )

                metrics = compute_verification_metrics(
                    cross_validation,
                    calibration,
                )

                diagram_fields = build_diagram_fields(
                    cross_validation,
                    calibration,
                )

                write_verification_netcdf(
                    metrics=metrics,
                    diagram_fields=diagram_fields,
                    base=args.base,
                    model=model,
                    var=var,
                    type_calibration=calibration,
                    year_ref=args.year,
                    month_hcst=args.month,
                )


if __name__ == "__main__":
    main()
