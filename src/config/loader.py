from pathlib import Path
import yaml

CONFIG_DIR = Path(__file__).parent

def load_yaml(file_name):

    with open(CONFIG_DIR / file_name) as f:
        return yaml.safe_load(f)

PARAMETERS_RUN = load_yaml("parameters_run.yaml")
MODELS_CONFIG = load_yaml("models.yaml")
VARIABLES_CONFIG = load_yaml("variables_download.yaml")