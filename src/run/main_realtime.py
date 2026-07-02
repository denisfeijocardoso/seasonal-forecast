import argparse
import logging

from .download import run_download_realtime_models
from .grads import run_grads_maps_realtime
from .interpolation import run_interpolation_forecast_models
from .realtime import run_realtime_forecast
from src.config.config_logging import setup_logging
from src.config.config_models import check_models, get_list_models
from src.config.loader import PARAMETERS_RUN
from src.io.realtime_writer import (
    write_observation_statistics_netcdf,
    write_results_netcdf,
)
from src.plotting import run_python_maps_realtime


NO_DOWNLOAD_MODELS = {
    "cansips",
    "bam",
    "echam",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rodar geração das previsões sazonais em tempo-real."
    )

    parser.add_argument("--base", type=str, default="nmme")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--month", type=int, required=True)
    parser.add_argument("--var", type=str, default=None)
    parser.add_argument("--model", type=str, default="all")
    parser.add_argument("--calibration", type=str, default="all")

    parser.add_argument(
        "--include-multimodel",
        action="store_true",
        help="Inclui o multimodelo junto com os modelos individuais.",
    )

    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Pula o download dos arquivos de previsão.",
    )

    parser.add_argument(
        "--skip-interpolation",
        action="store_true",
        help="Pula a interpolação dos arquivos de previsão.",
    )

    parser.add_argument(
        "--skip-products",
        action="store_true",
        help=(
            "Pula o cálculo dos produtos e a escrita dos netCDFs, "
            "rodando apenas a geração dos mapas."
        ),
    )
    
    parser.add_argument(
        "--maps",
        choices=("python", "grads", "none"),
        default="python",
        help="Backend usado para gerar mapas.",
    )

    return parser.parse_args()


def select_variables(var: str | None) -> list[str]:
    if var is None:
        return list(PARAMETERS_RUN["variables"])

    if var not in PARAMETERS_RUN["variables"]:
        raise ValueError(f"Variável inválida: {var}")

    return [var]


def select_calibrations(calibration: str) -> list[str]:
    if calibration == "all":
        return list(PARAMETERS_RUN["calibrations"])

    if calibration not in PARAMETERS_RUN["calibrations"]:
        raise ValueError(f"Calibração inválida: {calibration}")

    return [calibration]


def validate_model_arg(
    model_arg: str,
    configured_models: list[str],
) -> None:
    if model_arg in {"all", "multimodel"}:
        return

    if model_arg not in configured_models:
        raise ValueError(
            f"Modelo inválido para esta base: {model_arg!r}. "
            f"Modelos configurados: {configured_models}"
        )


def select_models_to_download(
    model_arg: str,
    configured_models: list[str],
    include_multimodel: bool,
) -> list[str]:
    if model_arg in {"all", "multimodel"} or include_multimodel:
        return [
            model
            for model in configured_models
            if model not in NO_DOWNLOAD_MODELS
        ]

    if model_arg in NO_DOWNLOAD_MODELS:
        return []

    return [model_arg]


def select_models_to_interpolate(
    model_arg: str,
    models_available: list[str],
    include_multimodel: bool,
) -> list[str]:
    if model_arg in {"all", "multimodel"} or include_multimodel:
        return list(models_available)

    if model_arg not in models_available:
        raise ValueError(
            f"Modelo {model_arg!r} não está disponível para esta rodada. "
            f"Disponíveis: {models_available}"
        )

    return [model_arg]


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
            f"Modelo {model_arg!r} não está disponível para esta rodada. "
            f"Disponíveis: {models_available}"
        )

    if include_multimodel and "multimodel" not in models_to_run:
        models_to_run = ["multimodel"] + models_to_run

    return models_to_run


def generate_maps(
    backend: str,
    base: str,
    model: str,
    var: str,
    calibration: str,
    year_fcst: int,
    month_fcst: int,
) -> None:
    if backend == "none":
        return

    if backend == "grads":
        run_grads_maps_realtime(
            base,
            model,
            var,
            calibration,
            year_fcst,
            month_fcst,
        )
        return

    run_python_maps_realtime(
        base,
        model,
        var,
        calibration,
        year_fcst,
        month_fcst,
    )


def main() -> None:
    args = parse_args()

    setup_logging(
        args.year,
        args.month,
    )

    logger = logging.getLogger(__name__)

    variables = select_variables(args.var)
    calibrations = select_calibrations(args.calibration)
    configured_models = list(get_list_models(args.base))
    validate_model_arg(args.model, configured_models)
    models_to_download = select_models_to_download(
        args.model,
        configured_models,
        args.include_multimodel,
    )

    logger.info(
        "Processando previsão em tempo-real: base=%s year=%s month=%s vars=%s",
        args.base,
        args.year,
        args.month,
        variables,
    )

    for var in variables:
        if args.skip_products:
            logger.info(
                "Modo apenas mapas ativo; pulando download/interpolação/produtos."
            )
        elif not args.skip_download:
            logger.info(
                "Baixando previsão: base=%s var=%s models=%s",
                args.base,
                var,
                models_to_download,
            )

            run_download_realtime_models(
                args.base,
                models_to_download,
                var,
                args.year,
                args.month,
            )

        models_available = check_models(
            args.base,
            var,
            args.year,
            args.month,
        )

        logger.info("Modelos disponíveis para %s: %s", var, models_available)

        models_to_interpolate = select_models_to_interpolate(
            args.model,
            models_available,
            args.include_multimodel,
        )

        if not args.skip_products and not args.skip_interpolation:
            logger.info(
                "Interpolando previsão: base=%s var=%s models=%s",
                args.base,
                var,
                models_to_interpolate,
            )

            run_interpolation_forecast_models(
                args.base,
                models_to_interpolate,
                var,
                args.year,
                args.month,
            )

        models_to_run = select_models_to_run(
            args.model,
            models_available,
            args.include_multimodel,
        )

        for model in models_to_run:
            if args.skip_products:
                logger.info(
                    (
                        "Pulando cálculo/escrita dos produtos; gerando mapas: "
                        "base=%s var=%s model=%s calibrations=%s"
                    ),
                    args.base,
                    var,
                    model,
                    calibrations,
                )
                results = None
                obs_statistics = None
            else:
                logger.info(
                    "Gerando produtos: base=%s var=%s model=%s calibrations=%s",
                    args.base,
                    var,
                    model,
                    calibrations,
                )

                results, obs_statistics = run_realtime_forecast(
                    args.base,
                    model,
                    var,
                    args.year,
                    args.month,
                    models_available,
                )

            for calibration in calibrations:
                if results is not None:
                    write_results_netcdf(
                        results[calibration],
                        args.base,
                        model,
                        var,
                        calibration,
                        args.year,
                        args.month,
                    )

                    write_observation_statistics_netcdf(
                        obs_statistics,
                        args.base,
                        model,
                        var,
                        calibration,
                        args.year,
                        args.month,
                    )

                generate_maps(
                    args.maps,
                    args.base,
                    model,
                    var,
                    calibration,
                    args.year,
                    args.month,
                )


if __name__ == "__main__":
    main()
