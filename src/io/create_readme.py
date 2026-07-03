from __future__ import annotations

import argparse
import logging
from pathlib import Path

from src.config.config_models import (
    build_model_dir_name,
    get_model_version,
    get_multimodel_version,
)
from src.config.loader import MODELS_CONFIG
from src.config.paths import PATH_POSPROC

logger = logging.getLogger(__name__)


def build_multimodel_readme(base: str) -> str:
    multimodel_version = get_multimodel_version(base)
    models = MODELS_CONFIG["bases"][base]["models"]
    base_title = _base_title(base)

    lines = [
        f"# {base_title} Multimodel {multimodel_version}",
        "",
        (
            "Este diretorio contem os arquivos NetCDF pos-processados da "
            f"previsao sazonal para a versao {multimodel_version} do "
            f"multimodelo {base_title}."
        ),
        "",
        "## Modelos incluidos",
        "",
        "| Modelo | Titulo | Versao | Diretorio |",
        "|---|---|---:|---|",
    ]

    for model in models:
        model_config = MODELS_CONFIG["models"][model]
        title = model_config["title"]
        version = get_model_version(model)
        directory = build_model_dir_name(model)
        lines.append(f"| {model} | {title} | {version} | {directory} |")

    lines.extend(
        [
            "",
            "## Configuracao de origem",
            "",
            "Gerado a partir de `src/config/models.yaml`.",
            "",
            "## Observacao",
            "",
            (
                "Mudancas na lista de modelos, nas versoes dos modelos ou na "
                "versao do multimodelo alteram o significado cientifico desta "
                "versao."
            ),
            "",
        ]
    )

    return "\n".join(lines)


def write_multimodel_readme(
    base: str,
    output_root: Path = PATH_POSPROC,
) -> Path:
    multimodel_version = get_multimodel_version(base)
    output_dir = output_root / base / multimodel_version
    output_dir.mkdir(parents=True, exist_ok=True)

    readme_path = output_dir / "README.md"
    readme_path.write_text(
        build_multimodel_readme(base),
        encoding="utf-8",
    )

    logger.info("README do multimodelo gerado: %s", readme_path)
    return readme_path


def _base_title(base: str) -> str:
    labels = {
        "nmme": "NMME",
        "copernicus": "C3S",
    }
    return labels.get(base, base.upper())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera README da versao do multimodelo."
    )
    parser.add_argument(
        "--base",
        default="all",
        help="Base a documentar: nmme, copernicus ou all.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    bases = MODELS_CONFIG["bases"].keys() if args.base == "all" else [args.base]

    for base in bases:
        write_multimodel_readme(base)


if __name__ == "__main__":
    main()
