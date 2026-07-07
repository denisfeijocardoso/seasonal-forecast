from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
import logging
import os

from src.config.config_logging import setup_logging
from src.config.config_models import get_list_models
from src.run.common import validate_month
from src.run.common import select_calibrations, select_variables
from src.run.download import run_download_hindcast_models
from src.run.interpolation import run_interpolation_hindcast_models
from src.plotting import run_python_maps_verification
from src.run.verification import (
    VerificationRunConfig,
    exclude_models,
    get_models_available,
    run_verification,
    select_models_to_run,
)


NO_DOWNLOAD_HINDCAST_MODELS = {
    "bam",
    "echam",
}


@dataclass(frozen=True)
class VerificationMapTask:
    base: str
    model: str
    var: str
    calibration: str
    year_ref: int
    month_hcst: int
    skip_existing: bool


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
        "--map-workers",
        type=int,
        default=min(4, os.cpu_count() or 1),
        help=(
            "Numero de processos usados na geracao dos mapas Python. "
            "Use 1 para rodar a fila de mapas em serie."
        ),
    )
    parser.add_argument(
        "--skip-multimodel",
        action="store_true",
        help="Nao inclui o multimodelo na verificacao operacional.",
    )
    parser.add_argument(
        "--exclude-model",
        action="append",
        default=[],
        help=(
            "Remove um modelo da rodada de verificacao. "
            "Pode ser usado mais de uma vez."
        ),
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Pula o download dos hindcasts.",
    )
    parser.add_argument(
        "--skip-interpolation",
        action="store_true",
        help="Pula a interpolacao dos hindcasts.",
    )
    parser.add_argument(
        "--skip-verification",
        action="store_true",
        help="Pula o calculo/escrita das metricas de verificacao.",
    )
    parser.add_argument(
        "--skip-maps",
        action="store_true",
        help="Pula a geracao dos mapas de verificacao.",
    )
    parser.add_argument(
        "--only-maps",
        action="store_true",
        help="Roda apenas os mapas a partir dos NetCDFs ja existentes.",
    )
    parser.add_argument(
        "--overwrite-maps",
        action="store_true",
        help="Refaz mapas mesmo quando a figura ja existe.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    run_operational_verification(args)


def run_operational_verification(args: argparse.Namespace) -> None:
    validate_month(args.month)

    if args.map_workers < 1:
        raise ValueError("--map-workers precisa ser maior ou igual a 1.")

    args.exclude_model = getattr(args, "exclude_model", []) or []

    setup_logging(
        args.year,
        args.month,
    )

    logger = logging.getLogger(__name__)
    include_multimodel = should_include_multimodel(args)

    logger.info(
        "Iniciando verificacao operacional: base=%s year=%s month=%s var=%s model=%s calibration=%s include_multimodel=%s excluded_models=%s",
        args.base,
        args.year,
        args.month,
        args.var or "all",
        args.model,
        args.calibration,
        include_multimodel,
        args.exclude_model,
    )

    if args.only_maps:
        logger.info(
            "Modo apenas mapas ativo; pulando download/interpolacao/verificacao."
        )
    else:
        if not args.skip_download:
            run_download_step(args, include_multimodel)

        if not args.skip_interpolation:
            run_interpolation_step(args, include_multimodel)

        if not args.skip_verification:
            run_verification(
                VerificationRunConfig(
                    base=args.base,
                    year=args.year,
                    month=args.month,
                    var=args.var,
                    model=args.model,
                    calibration=args.calibration,
                    include_multimodel=include_multimodel,
                    exclude_models=tuple(args.exclude_model),
                )
            )

    if args.skip_maps:
        logger.info("Pulando mapas de verificacao.")
    else:
        map_tasks = build_map_tasks(args, include_multimodel)
        logger.info("Fila de mapas de verificacao montada: %s tarefas.", len(map_tasks))
        generated_maps = run_map_queue(map_tasks, args.map_workers)
        logger.info(
            "Geracao de mapas de verificacao concluida: %s novas figuras.",
            generated_maps,
        )

    logger.info(
        "Verificacao operacional concluida: base=%s year=%s month=%s",
        args.base,
        args.year,
        args.month,
    )


def should_include_multimodel(args: argparse.Namespace) -> bool:
    return not args.skip_multimodel


def run_download_step(
    args: argparse.Namespace,
    include_multimodel: bool,
) -> None:
    logger = logging.getLogger(__name__)
    variables = select_variables(args.var)
    models = select_hindcast_models(
        args.base,
        args.model,
        include_multimodel,
        args.exclude_model,
    )

    if not models:
        logger.info("Nenhum modelo requer download de hindcast.")
        return

    for var in variables:
        logger.info(
            "Baixando hindcasts: base=%s var=%s models=%s month=%s",
            args.base,
            var,
            models,
            args.month,
        )
        run_download_hindcast_models(
            args.base,
            models,
            var,
            args.month,
        )


def run_interpolation_step(
    args: argparse.Namespace,
    include_multimodel: bool,
) -> None:
    logger = logging.getLogger(__name__)
    variables = select_variables(args.var)
    models = select_hindcast_models(
        args.base,
        args.model,
        include_multimodel,
        args.exclude_model,
    )

    if not models:
        logger.info("Nenhum modelo requer interpolacao de hindcast.")
        return

    for var in variables:
        logger.info(
            "Interpolando hindcasts: base=%s var=%s models=%s month=%s",
            args.base,
            var,
            models,
            args.month,
        )
        run_interpolation_hindcast_models(
            args.base,
            models,
            var,
            args.month,
        )


def select_hindcast_models(
    base: str,
    model_arg: str,
    include_multimodel: bool,
    excluded_models: tuple[str, ...] | list[str] = (),
) -> list[str]:
    configured_models = exclude_models(
        list(get_list_models(base)),
        excluded_models,
    )

    if model_arg in {"all", "multimodel"} or include_multimodel:
        models = configured_models
    elif model_arg in configured_models:
        models = [model_arg]
    elif model_arg in NO_DOWNLOAD_HINDCAST_MODELS:
        models = []
    else:
        raise ValueError(
            f"Modelo invalido para download/interpolacao de hindcast: {model_arg!r}. "
            f"Modelos disponiveis: {configured_models + ['multimodel']}"
        )

    return [
        model
        for model in models
        if model not in NO_DOWNLOAD_HINDCAST_MODELS
    ]


def build_map_tasks(
    args: argparse.Namespace,
    include_multimodel: bool,
) -> list[VerificationMapTask]:
    variables = select_variables(args.var)
    calibrations = select_calibrations(args.calibration)
    models_available = exclude_models(
        get_models_available(args.base),
        args.exclude_model,
    )
    models_to_run = select_models_to_run(
        args.model,
        models_available,
        include_multimodel,
    )

    return [
        VerificationMapTask(
            base=args.base,
            model=model,
            var=var,
            calibration=calibration,
            year_ref=args.year,
            month_hcst=args.month,
            skip_existing=not args.overwrite_maps,
        )
        for var in variables
        for model in models_to_run
        for calibration in calibrations
    ]


def generate_maps(
    base: str,
    model: str,
    var: str,
    calibration: str,
    year_ref: int,
    month_hcst: int,
    skip_existing: bool,
) -> int:
    generated = run_python_maps_verification(
        base,
        model,
        var,
        calibration,
        year_ref,
        month_hcst,
        skip_existing=skip_existing,
    )
    return len(generated)


def run_map_task(task: VerificationMapTask) -> int:
    return generate_maps(
        task.base,
        task.model,
        task.var,
        task.calibration,
        task.year_ref,
        task.month_hcst,
        task.skip_existing,
    )


def run_map_queue(
    tasks: list[VerificationMapTask],
    workers: int,
) -> int:
    logger = logging.getLogger(__name__)

    if not tasks:
        return 0

    if workers <= 1:
        generated = 0
        for task in tasks:
            generated += run_map_task(task)
        return generated

    logger.info(
        "Gerando mapas de verificacao em paralelo: tasks=%s workers=%s",
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
                        "Falha na geracao de mapas de verificacao: "
                        "base=%s var=%s model=%s calibration=%s"
                    ),
                    task.base,
                    task.var,
                    task.model,
                    task.calibration,
                )
                raise

    return generated


if __name__ == "__main__":
    main()
