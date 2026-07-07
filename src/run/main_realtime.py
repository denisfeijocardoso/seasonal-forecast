import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
import logging
import os

from .download import run_download_realtime_models
from .grads import run_grads_maps_realtime
from .interpolation import run_interpolation_forecast_models
from src.processing.realtime_products import build_realtime_products
from src.config.config_logging import setup_logging
from src.config.config_models import check_models, get_list_models
from src.io.realtime_writer import (
    write_observation_statistics_netcdf,
    write_results_netcdf,
)
from src.io.create_readme import write_multimodel_readme
from src.plotting import run_python_maps_realtime
from src.run.common import select_calibrations, select_variables, validate_month


NO_DOWNLOAD_MODELS = {
    "cansips",
    "bam",
    "echam",
}


@dataclass(frozen=True)
class MapTask:
    backend: str
    base: str
    model: str
    var: str
    calibration: str
    year_fcst: int
    month_fcst: int


@dataclass(frozen=True)
class RealtimeRunConfig:
    base: str
    year: int
    month: int
    var: str | None = None
    model: str = "all"
    calibration: str = "all"
    include_multimodel: bool = False
    skip_download: bool = False
    skip_interpolation: bool = False
    skip_products: bool = False
    maps: str = "python"
    map_workers: int = min(4, os.cpu_count() or 1)

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "RealtimeRunConfig":
        return cls(
            base=args.base,
            year=args.year,
            month=args.month,
            var=args.var,
            model=args.model,
            calibration=args.calibration,
            include_multimodel=args.include_multimodel,
            skip_download=args.skip_download,
            skip_interpolation=args.skip_interpolation,
            skip_products=args.skip_products,
            maps=args.maps,
            map_workers=args.map_workers,
        )


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

    parser.add_argument(
        "--map-workers",
        type=int,
        default=min(4, os.cpu_count() or 1),
        help=(
            "Numero de processos usados na geracao dos mapas Python. "
            "Use 1 para rodar a fila de mapas em serie."
        ),
    )

    return parser.parse_args()


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
) -> int:
    if backend == "none":
        return 0

    if backend == "grads":
        run_grads_maps_realtime(
            base,
            model,
            var,
            calibration,
            year_fcst,
            month_fcst,
        )
        return 0

    generated = run_python_maps_realtime(
        base,
        model,
        var,
        calibration,
        year_fcst,
        month_fcst,
    )
    return len(generated)


def run_map_task(task: MapTask) -> int:
    return generate_maps(
        task.backend,
        task.base,
        task.model,
        task.var,
        task.calibration,
        task.year_fcst,
        task.month_fcst,
    )


def run_map_queue(
    tasks: list[MapTask],
    workers: int,
) -> int:
    logger = logging.getLogger(__name__)

    if not tasks:
        return 0

    if tasks[0].backend != "python" or workers <= 1:
        generated = 0
        for task in tasks:
            generated += run_map_task(task)
        return generated

    logger.info(
        "Gerando mapas em paralelo: tasks=%s workers=%s",
        len(tasks),
        workers,
    )

    generated = 0
    with ProcessPoolExecutor(max_workers=workers) as executor:
        future_to_task = {
            executor.submit(run_map_task, task): task
            for task in tasks
        }

        for future in as_completed(future_to_task):
            task = future_to_task[future]
            try:
                generated += future.result()
            except Exception:
                logger.exception(
                    (
                        "Falha na geracao de mapas: base=%s var=%s "
                        "model=%s calibration=%s"
                    ),
                    task.base,
                    task.var,
                    task.model,
                    task.calibration,
                )
                raise

    return generated


def run_realtime(config: RealtimeRunConfig) -> None:
    validate_month(config.month)

    if config.map_workers < 1:
        raise ValueError("--map-workers precisa ser maior ou igual a 1.")

    setup_logging(
        config.year,
        config.month,
    )

    logger = logging.getLogger(__name__)

    variables = select_variables(config.var)
    calibrations = select_calibrations(config.calibration)
    configured_models = list(get_list_models(config.base))
    validate_model_arg(config.model, configured_models)
    models_to_download = select_models_to_download(
        config.model,
        configured_models,
        config.include_multimodel,
    )

    logger.info(
        "Processando previsão em tempo-real: base=%s year=%s month=%s vars=%s",
        config.base,
        config.year,
        config.month,
        variables,
    )

    map_tasks: list[MapTask] = []

    for var in variables:
        if config.skip_products:
            logger.info(
                "Modo apenas mapas ativo; pulando download/interpolação/produtos."
            )
        elif not config.skip_download:
            logger.info(
                "Baixando previsão: base=%s var=%s models=%s",
                config.base,
                var,
                models_to_download,
            )

            run_download_realtime_models(
                config.base,
                models_to_download,
                var,
                config.year,
                config.month,
            )

        models_available = check_models(
            config.base,
            var,
            config.year,
            config.month,
        )

        logger.info("Modelos disponíveis para %s: %s", var, models_available)

        models_to_interpolate = select_models_to_interpolate(
            config.model,
            models_available,
            config.include_multimodel,
        )

        if not config.skip_products and not config.skip_interpolation:
            logger.info(
                "Interpolando previsão: base=%s var=%s models=%s",
                config.base,
                var,
                models_to_interpolate,
            )

            run_interpolation_forecast_models(
                config.base,
                models_to_interpolate,
                var,
                config.year,
                config.month,
            )

        models_to_run = select_models_to_run(
            config.model,
            models_available,
            config.include_multimodel,
        )

        for model in models_to_run:
            if config.skip_products:
                logger.info(
                    (
                        "Pulando cálculo/escrita dos produtos; enfileirando mapas: "
                        "base=%s var=%s model=%s calibrations=%s"
                    ),
                    config.base,
                    var,
                    model,
                    calibrations,
                )
                results = None
                obs_statistics = None
            else:
                logger.info(
                    "Gerando produtos: base=%s var=%s model=%s calibrations=%s",
                    config.base,
                    var,
                    model,
                    calibrations,
                )

                results, obs_statistics = build_realtime_products(
                    config.base,
                    model,
                    var,
                    config.year,
                    config.month,
                    models_available,
                )

            for calibration in calibrations:
                if results is not None:
                    write_results_netcdf(
                        results[calibration],
                        config.base,
                        model,
                        var,
                        calibration,
                        config.year,
                        config.month,
                    )

                    write_observation_statistics_netcdf(
                        obs_statistics,
                        config.base,
                        model,
                        var,
                        calibration,
                        config.year,
                        config.month,
                    )

                map_tasks.append(
                    MapTask(
                        config.maps,
                        config.base,
                        model,
                        var,
                        calibration,
                        config.year,
                        config.month,
                    )
                )

    write_multimodel_readme(config.base)

    logger.info("Fila de mapas montada: %s tarefas.", len(map_tasks))
    generated_maps = run_map_queue(
        map_tasks,
        config.map_workers,
    )
    logger.info("Geracao de mapas concluida: %s novas figuras.", generated_maps)


def main() -> None:
    run_realtime(RealtimeRunConfig.from_args(parse_args()))


if __name__ == "__main__":
    main()
