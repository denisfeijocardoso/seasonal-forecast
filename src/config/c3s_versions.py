import re
import pandas as pd

from pathlib import Path
from src.config.loader import MODELS_CONFIG

'''Esse script abre a página da ECMWF, acha a tabela dos sistemas operacionais C3S,
pega a primeira linha da tabela e transforma os valores de system em um dicionário.
Além disso também tem uma função para atualizar a versão dos modelos do C3S, com base
na tabela presente na página de Dados Disponíveis'''

C3S_SUMMARY_URL = (
    "https://confluence.ecmwf.int/spaces/CKB/pages/104239050/"
    "Summary+of+available+data"
)


MODEL_COLUMNS = {
    "ecmwf": "ECMWF",
    "meteofr": "Météo-France",
    "ukmo": "UK MetOffice",
    "dwd": "DWD",
    "cmcc": "CMCC",
    "ncep": "NCEP",
    "jma": "JMA",
    "eccc": "ECCC",
    "bom": "BOM",
}

MODELS_YAML_PATH = Path(__file__).with_name("models.yaml")


def clean_system(value):
    value = str(value).strip()
    value = re.sub(r"\.0$", "", value)
    value = re.sub(r"\s+", " ", value)
    return value


def find_operational_systems_table(tables):
    for table in tables:
        text = table.to_string()
        if (
            "Nominal Start Dates" in text
            and "ECMWF" in text
            and "UK MetOffice" in text
            and "BOM" in text
        ):
            return table

    raise RuntimeError("Tabela operacional de sistemas C3S nao encontrada.")


def flatten_columns(table):
    table = table.copy()

    if isinstance(table.columns, pd.MultiIndex):
        table.columns = [
            " ".join(str(part).strip() for part in col if str(part) != "nan")
            for col in table.columns
        ]
    else:
        table.columns = [str(col).strip() for col in table.columns]

    return table


def normalize_operational_systems_table(table):
    if "ECMWF" in table.columns and "BOM" in table.columns:
        return table

    header_index = None
    for index, row in table.iterrows():
        values = [str(value).strip() for value in row.tolist()]
        if "ECMWF" in values and "BOM" in values:
            header_index = index
            break

    if header_index is None:
        return table

    header = [
        str(value).strip()
        for value in table.iloc[header_index].tolist()
        if str(value).strip()
    ]

    columns = ["Nominal Start Dates", *header]
    data = table.iloc[header_index + 1 :].copy()
    data = data.iloc[:, : len(columns)]
    data.columns = columns
    data = data.dropna(how="all")

    return data.reset_index(drop=True)

def get_latest_c3s_systems(url=C3S_SUMMARY_URL):
    tables = pd.read_html(url)
    table = normalize_operational_systems_table(
        flatten_columns(find_operational_systems_table(tables))
    )
    latest = table.iloc[0]

    systems = {}
    for model, column in MODEL_COLUMNS.items():
        matches = [col for col in table.columns if column in col]
        if not matches:
            raise RuntimeError(f"Coluna nao encontrada na tabela C3S: {column}")

        systems[model] = clean_system(latest[matches[0]])

    if systems["eccc"] == "4 and 5":
        systems["eccc4"] = "4"
        systems["eccc5"] = "5"

    return systems, latest


def normalize_version(value):
    return clean_system(value)


def get_c3s_models(model_arg: str) -> list[str]:
    if model_arg == "all":
        return list(MODELS_CONFIG["bases"]["copernicus"]["models"])

    return [model_arg]


def update_version_model_c3s(model: str, versions_table: dict[str, str] | None = None):
    if versions_table is None:
        versions_table, _ = get_latest_c3s_systems()

    if model not in versions_table:
        return {
            "model": model,
            "updated": False,
            "skipped": True,
            "old": None,
            "new": None,
            "reason": "modelo nao encontrado na tabela C3S",
        }

    version_yaml = MODELS_CONFIG["models"][model]["version"]
    version_table = versions_table[model]

    if normalize_version(version_yaml) == normalize_version(version_table):
        return {
            "model": model,
            "updated": False,
            "skipped": False,
            "old": version_yaml,
            "new": version_table,
            "reason": None,
        }
        
    MODELS_CONFIG["models"][model]["version"] = version_table

    return {
        "model": model,
        "updated": True,
        "skipped": False,
        "old": version_yaml,
        "new": version_table,
        "reason": None,
    }


def write_model_versions_to_yaml(results: list[dict]) -> None:
    updates = {
        result["model"]: result["new"]
        for result in results
        if result["updated"]
    }

    if not updates:
        return

    lines = MODELS_YAML_PATH.read_text(encoding="utf-8").splitlines(
        keepends=True
    )
    current_model = None

    for index, line in enumerate(lines):
        model_match = re.match(r"^  ([A-Za-z0-9_]+):\s*$", line)
        if model_match:
            current_model = model_match.group(1)
            continue

        if current_model in updates and re.match(r"^    version:\s*", line):
            newline = "\n" if line.endswith("\n") else ""
            lines[index] = f"    version: {updates[current_model]}{newline}"
            current_model = None

    MODELS_YAML_PATH.write_text("".join(lines), encoding="utf-8")


def update_c3s_model_versions(model_arg: str, logger=None) -> list[dict]:
    versions_table, _ = get_latest_c3s_systems()
    results = [
        update_version_model_c3s(model, versions_table)
        for model in get_c3s_models(model_arg)
    ]

    write_model_versions_to_yaml(results)

    if logger is not None:
        for result in results:
            model = result["model"]

            if result["skipped"]:
                logger.warning(
                    "Versão dos modelos C3S não verificada: %s (%s)",
                    model,
                    result["reason"],
                )
            elif result["updated"]:
                logger.info(
                    "Versão dos modelos C3S atualizada: %s %s -> %s",
                    model,
                    result["old"],
                    result["new"],
                )
            else:
                logger.info(
                    "Versão dos modelos C3S se mantem: %s system=%s",
                    model,
                    result["new"],
                )

    return results

if __name__ == "__main__":
    systems, latest_row = get_latest_c3s_systems()

    print("Linha mais atual da tabela:")
    print(latest_row.to_string())
    print()
    print("Systems atuais:")
    for model, system in systems.items():
        print(f"{model}: {system}")
