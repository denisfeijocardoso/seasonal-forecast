from pathlib import Path
from typing import Any
import yaml

CONFIG_DIR = Path(__file__).parent

def load_yaml(file_name) -> dict[str, Any]:
    with open(CONFIG_DIR / file_name) as f:
        return yaml.safe_load(f)

PARAMETERS_RUN = load_yaml("parameters_run.yaml")

MODELS_CONFIG = load_yaml("models.yaml")

VARIABLES_CONFIG = load_yaml("variables_download.yaml")

def get_periods_aggregation() -> list[str]:
    return PARAMETERS_RUN["periods"]

def get_climatology_period(
        base: str
) -> tuple[int, int]:
    
    climatology = PARAMETERS_RUN["bases"][base]["climatology"]

    return climatology["start_year"], climatology["end_year"]


