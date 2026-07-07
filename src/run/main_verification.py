import argparse
from dataclasses import dataclass
import logging
from src.config.config_logging import setup_logging
from src.config.config_models import get_list_models
from src.config.loader import PARAMETERS_RUN
from src.io.verification_writer import write_verification_netcdf
from src.verification.cross_validation import (
    build_cross_validation_context,
    run_cross_validation_for_calibration,
)
from src.verification.metrics import (
    build_diagram_fields,
    compute_verification_metrics,
)


@dataclass(frozen=True)
class VerificationRunConfig:
    base: str
    year: int
    month: int
    var: str | None = None
    model: str = "all"
    calibration: str = "all"
    include_multimodel: bool = False

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "VerificationRunConfig":
        return cls(
            base=args.base,
            year=args.year,
            month=args.month,
            var=args.var,
            model=args.model,
            calibration=args.calibration,
            include_multimodel=args.include_multimodel,
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

    run_verification(
        VerificationRunConfig.from_args(args)
    )


def run_verification(config: VerificationRunConfig) -> None:

    logger = logging.getLogger(__name__)

    variables = select_variables(config.var)
    calibrations = select_calibrations(config.calibration)
    models_available = get_models_available(config.base)
    models_to_run = select_models_to_run(
        config.model,
        models_available,
        config.include_multimodel,
    )

    logger.info(
        "Verificacao iniciada: base=%s year=%s month=%s variables=%s models=%s calibrations=%s",
        config.base,
        config.year,
        config.month,
        variables,
        models_to_run,
        calibrations,
    )

    for var in variables:
        for model in models_to_run:
            context = build_cross_validation_context(
                base=config.base,
                model=model,
                var=var,
                month_hcst=config.month,
                models_available=models_available,
                include_nocalib_members=("nocalib" in calibrations),
                include_regr_correlations=("regr" in calibrations),
            )

            for calibration in calibrations:

                logger.info(
                    "Verificacao: base=%s var=%s model=%s calibration=%s month=%s",
                    config.base,
                    var,
                    model,
                    calibration,
                    config.month,
                )

                cross_validation = run_cross_validation_for_calibration(
                    context,
                    calibration,
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
                    base=config.base,
                    model=model,
                    var=var,
                    type_calibration=calibration,
                    year_ref=config.year,
                    month_hcst=config.month,
                )

    logger.info(
        "Verificacao concluida: base=%s year=%s month=%s",
        config.base,
        config.year,
        config.month,
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


def get_models_available(base: str) -> list[str]:
    models_available = list(get_list_models(base))

    if "bam" not in models_available:
        models_available.append("bam")

    return models_available


def select_models_to_run(
    model_arg: str,
    models_available: list[str],
    include_multimodel: bool,
) -> list[str]:
    if model_arg == "all":
        models_to_run = list(models_available)
    elif model_arg == "multimodel":
        models_to_run = ["multimodel"]
    elif model_arg in models_available:
        models_to_run = [model_arg]
    else:
        raise ValueError(
            f"Modelo invalido para verificacao: {model_arg!r}. "
            f"Modelos disponiveis: {models_available + ['multimodel']}"
        )

    if include_multimodel and "multimodel" not in models_to_run:
        models_to_run = ["multimodel"] + models_to_run

    return models_to_run


if __name__ == "__main__":
    main()
